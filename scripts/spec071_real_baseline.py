# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-071 T012 (REQ-014 / SC-014): one command that runs the Braid Lightning real baseline.

It runs the SPEC-069 T010 baseline guidance (arm ``baseline``: alpha.7 plus #1099, model pinned to the T010 one)
on the development set, three repetitions, in Claude Code on the owner's subscription route, through
``agent_braid.lightning_runner``. OpenCode is excluded (OD-2: no subscription credential source is reported).

Before anything runs it checks, by name only, that no model-provider key (``ANTHROPIC_API_KEY`` and the other
``lightning_runner.PROVIDER_KEYS``), ``ANTHROPIC_AUTH_TOKEN``, ``ANTHROPIC_BASE_URL`` or Bedrock/Vertex switch is set and that ``CLAUDE_CODE_OAUTH_TOKEN`` is present. It uses a
dedicated private laboratory home (never the plugin registry you use day to day), records the setup consent and
the profile there through their preview/apply digests, runs, and writes a redacted evidence record:

    read -rs CLAUDE_CODE_OAUTH_TOKEN && export CLAUDE_CODE_OAUTH_TOKEN
    .venv-speckit/bin/python -m scripts.spec071_real_baseline

The report compares the first-attempt proportion with the T010 one and labels it ``route-changed comparison``
(T010 used an API key). Inside or outside the T010 interval is a finding, not a pass condition (owner, 2026-11-10).
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import lightning_config as config  # noqa: E402
from agent_braid import lightning_runner as runner  # noqa: E402
from agent_braid import plugin_registry as registry  # noqa: E402
from agent_braid.lightning_hosts import Secrets, utc_now  # noqa: E402

T010 = ROOT / "specs/069-aim-request-authoring/evidence/native-runs-baseline-anthropic.json"
OUT = ROOT / "specs/071-lightning-rollouts-reward/evidence/native-baseline.json"
T010_MODEL = "claude-sonnet-5-5"
DEFAULT_HOME = Path.home() / ".local/state/agent-braid/lightning-lab"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME, help="dedicated private laboratory home")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model", default=T010_MODEL, help="pinned Claude Code model (default: the T010 model)")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args(argv)

    try:
        runner.parent_gate(dict(os.environ))
    except runner.RunnerError as exc:
        print(f"refused ({exc.code}): {exc}. Run it from a terminal without those variables.", file=sys.stderr)
        return 2
    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("refused: CLAUDE_CODE_OAUTH_TOKEN is not set. Create it with `claude setup-token`, then "
              "`read -rs CLAUDE_CODE_OAUTH_TOKEN && export CLAUDE_CODE_OAUTH_TOKEN`.", file=sys.stderr)
        return 2

    home = args.home.expanduser().absolute()
    home.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    preview = registry.plan_setup(home, [], lightning="lab")
    registry.apply(home, preview, preview["previewDigest"])
    answers = {"rollout": {"hosts": ["claude-code"], "repetitions": args.repetitions},
               "budget": {"maxRollouts": 10 * args.repetitions}}
    init = config.plan_init(home, answers)
    config.apply_init(home, init, init["previewDigest"])
    profile = config.load(home)

    status = runner.run(home, profile, arm="baseline", models={"claude-code": args.model})
    report = runner.report(home, status["runId"]) if status.get("runId") else {}
    t010 = json.loads(T010.read_text())
    t010_host = t010["summary"]["hosts"]["claude-code"]
    mine = report.get("hosts", {}).get("claude-code")
    comparison = None
    if mine:
        low, high = t010_host["firstAttemptInterval"]
        share = mine["firstAttempt"] / mine["trials"] if mine["trials"] else None
        comparison = {
            "label": "route-changed comparison",
            "t010": {"route": "api-key (env-key)", "version": t010["hosts"]["claude-code"].get("version"),
                     "models": t010["hosts"]["claude-code"].get("modelsObserved"),
                     "firstAttemptTrials": t010_host["firstAttemptTrials"], "trials": t010_host["trials"],
                     "firstAttemptInterval": t010_host["firstAttemptInterval"]},
            "lightning": {"route": "subscription", "firstAttempt": mine["firstAttempt"], "trials": mine["trials"],
                          "firstAttemptInterval": mine["firstAttemptInterval"],
                          "withinRetry": mine["withinRetry"], "withinRetryInterval": mine["withinRetryInterval"]},
            "insideT010Interval": None if share is None else low <= share <= high,
            "note": "A finding, not a pass condition: route, host version and possibly model differ from T010.",
        }
    from agent_braid import lightning_store as store
    results = [r.value for r in store.RunStore(home, status["runId"]).read("result")] if status.get("runId") else []
    evidence = {
        "evidenceVersion": 1, "task": "SPEC-071 T012 (REQ-014 / SC-014)", "generatedAt": utc_now(),
        "label": "host-run", "arm": "baseline", "pinnedModel": args.model, "promptSet": "development",
        "repetitions": args.repetitions, "status": status, "report": report, "comparison": comparison,
        "keySourcesObserved": sorted({r["keySource"] or "missing" for r in results}),
        "hostVersions": sorted({r["hostVersion"] or "unknown" for r in results}),
        "modelsObserved": sorted({r["model"] or "unknown" for r in results}),
        "paidRouteObservations": sum(1 for r in results if r["keySource"] not in (None, "oauth", "none")),
        "executionAuthorization": False,
    }
    secrets = Secrets([os.environ["CLAUDE_CODE_OAUTH_TOKEN"]])
    text = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    secrets.assert_clean(args.output.name, text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(json.dumps({"evidence": str(args.output), "runId": status.get("runId"), "completed": status.get("completed"),
                      "stop": status.get("stop"), "refusal": status.get("refusal"), "comparison": comparison}, indent=2))
    return 0 if status.get("refusal") is None else 1


if __name__ == "__main__":
    sys.exit(main())
