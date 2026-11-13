# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T009 (REQ-001 / SC-001): one command that runs the APO then the GEPA arm in the Braid Lightning lab.

Both arms start from A0, the SPEC-069 T010 baseline guidance (``--source baseline``: commit ``8f63c606``), with the
preregistered parameters of ``specs/072-lightning-prompt-optimization/evaluation-protocol.md`` on Claude Code only
(proposed amendment A-1), the model pinned to the T010 one, and the seed scored from the SPEC-071 baseline run.

Without ``--yes`` it only prints the dry-run cost (rollouts and optimizer calls, each one Claude Code call on the
subscription) and exits. With ``--yes`` it checks, by name only, that no paid-route variable is set and that a
``CLAUDE_CODE_OAUTH_TOKEN`` exists in the environment or in the Keychain service ``agent-braid-claude-oauth`` (the
value is never printed), then runs APO and, if APO did not stop, GEPA, and writes a redacted evidence record:

    .venv-speckit/bin/python -m scripts.spec072_lab_arms           # cost only
    .venv-speckit/bin/python -m scripts.spec072_lab_arms --yes     # runs both arms

A quota stop ends the script; continue the stopped arm with
``agent-braid lightning run --home <lab> --resume <run-id> --seed-run <seed> --source baseline``.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import lightning_arm as arm  # noqa: E402
from agent_braid import lightning_config as config  # noqa: E402
from agent_braid import lightning_runner as runner  # noqa: E402
from agent_braid import plugin_registry as registry  # noqa: E402
from agent_braid.lightning_hosts import Secrets, utc_now  # noqa: E402

SEED_RUN = "run-20261111T085405Z-a14514"
DEFAULT_HOME = Path.home() / ".local/state/agent-braid/lightning-lab"
KEYCHAIN_SERVICE = "agent-braid-claude-oauth"
TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
OUT = ROOT / "specs/072-lightning-prompt-optimization/evidence/t009-arms.json"
# Preregistered (evaluation protocol): APO beam 2, branch 2, 2 rounds; GEPA 3 rounds; minibatch 5; 10 x 3.
ARMS = {"apo": {"beamWidth": 2, "branchFactor": 2, "rounds": 2, "minibatch": 5},
        "gepa": {"rounds": 3, "minibatch": 5}}


def answers(name: str, repetitions: int) -> dict:
    return {"rollout": {"hosts": ["claude-code"], "repetitions": repetitions},
            "algorithm": {"name": name, **ARMS[name]},
            "budget": {"maxRollouts": 120, "maxOptimizerCalls": 40},
            "optimizer": {"host": "claude-code"}}


def keychain_token() -> str | None:
    done = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                          capture_output=True, text=True)
    return (done.stdout.strip() or None) if done.returncode == 0 else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME, help="dedicated private laboratory home")
    parser.add_argument("--seed-run", default=SEED_RUN, help="finished SPEC-071 development baseline run (A0 seed)")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--model", default=arm.DEFAULT_MODEL, help="pinned Claude Code model (default: the T010 one)")
    parser.add_argument("--rng-seed", type=int, default=0)
    parser.add_argument("--output", type=Path, default=OUT)
    parser.add_argument("--yes", action="store_true", help="run the arms (spends subscription quota)")
    args = parser.parse_args(argv)

    plans = {name: arm.estimate(config.build(answers(name, args.repetitions)), ROOT) for name in ARMS}
    cost = {"arms": {name: {"rollouts": p["atMost"]["rollouts"], "optimizerCalls": p["atMost"]["optimizerCalls"]}
                     for name, p in plans.items()},
            "totalClaudeCodeCalls": sum(p["atMost"]["rollouts"] + p["atMost"]["optimizerCalls"] for p in plans.values()),
            "host": "claude-code", "model": args.model, "source": "baseline (8f63c606)", "seedRun": args.seed_run,
            "note": "upper bounds; each is one Claude Code call on the subscription route, EUR 0 extra"}
    print(json.dumps({"dryRun": cost}, indent=2))
    if not args.yes:
        print("Nothing run. Re-run with --yes to spend this quota.", file=sys.stderr)
        return 0

    try:
        runner.parent_gate(dict(os.environ))
    except runner.RunnerError as exc:
        print(f"refused ({exc.code}): {exc}. Run it from a terminal without those variables.", file=sys.stderr)
        return 2
    token = os.environ.get(TOKEN) or keychain_token()
    if not token:
        print(f"refused: {TOKEN} is not set and the Keychain service {KEYCHAIN_SERVICE} has no item. Create it with "
              "`claude setup-token`, then store it with "
              f"`security add-generic-password -a \"$USER\" -s {KEYCHAIN_SERVICE} -w` (prompted, not echoed).",
              file=sys.stderr)
        return 2
    environ = dict(os.environ, **{TOKEN: token})
    secrets = Secrets([token])

    home = args.home.expanduser().absolute()
    home.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    preview = registry.plan_setup(home, [], lightning="lab")
    registry.apply(home, preview, preview["previewDigest"])
    arm.seed_vectors(home, args.seed_run, ROOT)  # refuses before any call if the seed misses a development case

    results = {}
    for name in ARMS:
        init = config.plan_init(home, answers(name, args.repetitions))
        config.apply_init(home, init, init["previewDigest"])
        profile = config.load(home)
        try:
            summary = arm.run_arm(home, profile, seed_run=args.seed_run, environ=environ, source="baseline",
                                  models={"claude-code": args.model}, rng_seed=args.rng_seed)
        except runner.RunnerError as exc:
            results[name] = {"refusal": exc.code}
            break
        results[name] = summary
        if summary.get("stop") or summary.get("refusal"):
            break  # a quota stop or refusal ends the script; resume explicitly

    evidence = {"evidenceVersion": 1, "task": "SPEC-072 T009 (REQ-001 / SC-001)", "generatedAt": utc_now(),
                "label": "host-run", "dryRun": cost, "arms": results, "protocolAmendment": "A-1 (hosts), proposed",
                "executionAuthorization": False}
    text = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    secrets.assert_clean(args.output.name, text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(json.dumps({"evidence": str(args.output),
                      "arms": {n: {k: r.get(k) for k in ("runId", "stop", "refusal")} for n, r in results.items()}},
                     indent=2))
    return 0 if all(not r.get("refusal") for r in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
