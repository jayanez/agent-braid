# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T009 (protocol Amendment 1): one command for the development phase of the APO and GEPA arms.

In the dedicated laboratory home it runs, in order and on the Claude Code subscription route, model pinned:

1. the new A0 baseline: the current ``develop`` analyze guidance in the current plugin build (arm ``final``),
   development set, ``claude-code``, 3 repetitions;
2. the APO arm (A1) with the preregistered profile (beam 2, branch 2, 2 rounds, minibatch 5), seeded by run 1;
3. the GEPA arm (A2) with the preregistered profile (3 rounds, minibatch 5), seeded by run 1.

Without ``--execute`` it only prints the cost summary (rollouts and optimizer calls from
``lightning_arm.estimate``) and launches nothing. With ``--execute`` it prints the same summary first, then runs.
It never touches the held-out set and does not freeze the protocol.

The credential is ``CLAUDE_CODE_OAUTH_TOKEN`` from the environment or, if absent, the macOS Keychain generic
password of service ``agent-braid-claude-oauth``; it is never printed. It refuses when neither is present and when
any paid-route variable is set (``lightning_runner.parent_gate``)::

    .venv-speckit/bin/python -m scripts.spec072_development_arms            # cost summary only
    .venv-speckit/bin/python -m scripts.spec072_development_arms --execute  # runs (owner yes required)

With ``--exploratory`` it runs instead the exploratory arms E1 (APO) and E2 (GEPA) of Amendment 1 item 6: the
T010 guidance at the SPEC-069 BASELINE_COMMIT (``--source baseline``), seeded by the SPEC-071 T012 run, development
only, descriptive, after A1 and A2. It writes a separate evidence file.

After a quota stop, rerun with ``--baseline-run <id>`` to reuse a finished A0 run and ``--resume-apo``/
``--resume-gepa <run id>`` to continue a stopped arm.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import lightning_arm as arm  # noqa: E402
from agent_braid import lightning_config as config  # noqa: E402
from agent_braid import lightning_runner as runner  # noqa: E402
from agent_braid import plugin_registry as registry  # noqa: E402
from agent_braid.lightning_hosts import Secrets, utc_now  # noqa: E402

DEFAULT_HOME = Path.home() / ".local/state/agent-braid/lightning-lab"
OUT = ROOT / "specs/072-lightning-prompt-optimization/evidence/development-arms.json"
EXPLORATORY_OUT = ROOT / "specs/072-lightning-prompt-optimization/evidence/development-arms-exploratory.json"
T012_SEED_RUN = "run-20261111T085405Z-a14514"  # SPEC-071 T012: T010 guidance, claude-code, 16/30
KEYCHAIN_SERVICE = "agent-braid-claude-oauth"
TOKEN = "CLAUDE_CODE_OAUTH_TOKEN"
SECONDS_PER_ROLLOUT = 23  # SPEC-071 T012: 30 rollouts in about 11.5 minutes
SECONDS_PER_CALL = 60
HOST = "claude-code"
REPETITIONS = 3
# Preregistered profile (evaluation-protocol.md, feasibility table).
PROFILES = {
    "baseline": {"algorithm": {"name": "baseline"}, "budget": {"maxRollouts": 10 * REPETITIONS}},
    "apo": {"algorithm": {"name": "apo", "beamWidth": 2, "branchFactor": 2, "rounds": 2, "minibatch": 5},
            "budget": {"maxRollouts": 120, "maxOptimizerCalls": 40}},
    "gepa": {"algorithm": {"name": "gepa", "rounds": 3, "minibatch": 5},
             "budget": {"maxRollouts": 120, "maxOptimizerCalls": 40}},
}


def answers(name: str) -> dict:
    value = {"rollout": {"hosts": [HOST], "repetitions": REPETITIONS}, "optimizer": {"host": HOST}}
    value.update(json.loads(json.dumps(PROFILES[name])))
    return value


def cost_summary(exploratory: bool = False) -> dict:
    """Upper bounds per run and in total; nothing is launched."""
    rows = {} if exploratory else {"baseline": {"rollouts": 10 * REPETITIONS, "optimizerCalls": 0}}
    for name in ("apo", "gepa"):
        rows[name] = arm.estimate(config.build(answers(name)), ROOT)["atMost"]
    total = {key: sum(row[key] for row in rows.values()) for key in ("rollouts", "optimizerCalls")}
    minutes = round((total["rollouts"] * SECONDS_PER_ROLLOUT + total["optimizerCalls"] * SECONDS_PER_CALL) / 60)
    return {"host": HOST, "repetitions": REPETITIONS, "runs": rows, "atMost": total,
            "roughMinutesAtMost": minutes, "route": "subscription (no extra cash)",
            "note": "upper bounds; GEPA uses 45 rollouts if one child is accepted, up to 105 if all three are"}


def keychain_token() -> str | None:
    if sys.platform != "darwin" or not shutil.which("security"):
        return None
    done = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def apply_profile(home: Path, name: str) -> dict:
    preview = config.plan_init(home, answers(name))
    config.apply_init(home, preview, preview["previewDigest"])
    return config.load(home)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--home", type=Path, default=DEFAULT_HOME, help="dedicated private laboratory home")
    parser.add_argument("--model", default=arm.DEFAULT_MODEL, help="pinned Claude Code model")
    parser.add_argument("--execute", action="store_true", help="run on the subscription (spends quota)")
    parser.add_argument("--baseline-run", help="reuse a finished A0 development run instead of starting one")
    parser.add_argument("--resume-apo", metavar="RUN_ID")
    parser.add_argument("--resume-gepa", metavar="RUN_ID")
    parser.add_argument("--exploratory", action="store_true",
                        help="run E1/E2 from the T010 guidance seeded by the T012 run (Amendment 1 item 6)")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.exploratory and args.baseline_run:
        parser.error("--exploratory is seeded by the SPEC-071 T012 run; --baseline-run does not apply")
    args.output = args.output or (EXPLORATORY_OUT if args.exploratory else OUT)
    source = "baseline" if args.exploratory else "final"

    summary = cost_summary(args.exploratory)
    print(json.dumps({"costSummary": summary, "model": args.model, "execute": args.execute,
                      "arms": "E1/E2 exploratory (T010 guidance)" if args.exploratory else "A0, A1, A2"}, indent=2))
    if not args.execute:
        print("dry run: nothing launched. Add --execute to run.", file=sys.stderr)
        return 0

    try:
        runner.parent_gate(dict(os.environ))
    except runner.RunnerError as exc:
        print(f"refused ({exc.code}): {exc}. Run it from a terminal without those variables.", file=sys.stderr)
        return 2
    token = os.environ.get(TOKEN) or keychain_token()
    if not token:
        print(f"refused: {TOKEN} is not set and the Keychain has no '{KEYCHAIN_SERVICE}' item. Create it with "
              f"`claude setup-token`, then `read -rs {TOKEN} && export {TOKEN}`.", file=sys.stderr)
        return 2
    environ = dict(os.environ, **{TOKEN: token})
    models = {HOST: args.model}

    home = args.home.expanduser().absolute()
    home.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    preview = registry.plan_setup(home, [], lightning="lab")
    registry.apply(home, preview, preview["previewDigest"])

    task = ("SPEC-072 exploratory arms E1/E2 (Amendment 1 item 6, descriptive)" if args.exploratory
            else "SPEC-072 T009 development phase (protocol Amendment 1)")
    record: dict = {"evidenceVersion": 1, "task": task, "exploratory": args.exploratory, "source": source,
                    "generatedAt": utc_now(), "label": "host-run", "pinnedModel": args.model, "host": HOST,
                    "costSummary": summary, "runs": {}, "executionAuthorization": False}
    exit_code = 0
    seed = T012_SEED_RUN if args.exploratory else args.baseline_run
    if seed is None:
        status = runner.run(home, apply_profile(home, "baseline"), arm="final", models=models, environ=environ)
        record["runs"]["baseline"] = status
        if status.get("stop") or status.get("refusal"):
            exit_code = 1
        else:
            seed = status["runId"]
    if seed is not None:
        record["seedRun"] = seed
        for name, resume in (("apo", args.resume_apo), ("gepa", args.resume_gepa)):
            try:
                result = arm.run_arm(home, apply_profile(home, name), seed_run=seed, run_id=resume,
                                     resume=bool(resume), environ=environ, models=models, source=source)
            except runner.RunnerError as exc:
                result = {"refusal": exc.code, "message": str(exc)}
            record["runs"][name] = result
            if result.get("stop") or result.get("refusal"):
                exit_code = 1
                break  # a quota stop ends the phase; resume explicitly

    text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n"
    Secrets([token]).assert_clean(args.output.name, text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(json.dumps({"evidence": str(args.output), "seedRun": seed,
                      "runs": {k: {"runId": v.get("runId"), "stop": v.get("stop"), "refusal": v.get("refusal")}
                               for k, v in record["runs"].items()}}, indent=2))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
