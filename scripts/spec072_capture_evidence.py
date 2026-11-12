# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 (BL.2): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. Procedure 001 (owner review and protocol freeze) and 008 (held-out runs) are not test procedures;
later procedures are added as their tasks land.

    python -m scripts.spec072_capture_evidence
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/072-lightning-prompt-optimization"
EVIDENCE = SPEC / "evidence"
PROCEDURES = {
    'procedure_002': {
        "scenario": 'SC-002',
        "modules": ["tests.test_lightning_resources"],
        "inputs": ["agent_braid/lightning_resources.py", "agent_braid/lightning_store.py", "agent_braid/lightning_schema.py",
                   "tests/test_lightning_resources.py", "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"],
        "outcome_note": "The seed is the analyze skill body below its fixed front matter; seed and child records round-trip canonically byte for byte; the child names the seed as parent; text whose hash differs, unknown keys, foreign origins, refused contamination checks and broken lineage are refused with codes; the store keeps text beside the record privately and refuses a record without matching text; later records may change only scores and Pareto membership.",
        "limits": "Record and store only; the seed check against the run's recorded commit is applied when runs record a commit (T003).",
    },
    'procedure_003': {
        "scenario": 'SC-003',
        "modules": ["tests.test_lightning_algorithm"],
        "inputs": ["agent_braid/lightning_algorithm.py", "agent_braid/lightning_runner.py", "agent_braid/lightning_resources.py",
                   "agent_braid/lightning_store.py", "tests/test_lightning_algorithm.py",
                   "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"],
        "outcome_note": "Baseline on fake hosts yields per-host trials, first-attempt and within-retry counts and Wilson intervals identical to a direct SPEC-071 fake-host run, with stored rewards replaying; it records the round-0 seed candidate with its text and a full-set devScore equal to the report's first-attempt rate; a modified seed changes the candidate sha256 in the summary (negative control); the base Algorithm.run is abstract.",
        "limits": "Fake hosts only (pipeline-only label); no model contacted. Fake-host outcomes do not depend on the skill text, so equality shows pipeline identity, not prompt quality.",
    },
    'procedure_004': {
        "scenario": 'SC-004',
        "modules": ["tests.test_lightning_apo"],
        "inputs": ["agent_braid/lightning_apo.py", "agent_braid/lightning_runner.py", "agent_braid/lightning_algorithm.py",
                   "agent_braid/lightning_resources.py", "agent_braid/lightning_prompts/apo_text_gradient.md",
                   "agent_braid/lightning_prompts/apo_apply_edit.md", "tests/test_lightning_apo.py"],
        "outcome_note": "With the preregistered parameters (beam 2, branch 2, 2 rounds, minibatch 5, 2 hosts, 3 repetitions) APO runs 1 then 2 parents with 2 then 4 children, 9 optimizer calls and 120 rollouts (20 + 40 search, 60 full evaluation of the best), as in the feasibility table; every APO candidate records its parent, round, two call ids, both passed contamination checks and the hash of the critique and edit templates; configuration defaults stop at the 120-rollout cap (unit-cap), configured rounds above 3 are capped at 3, the optimizer-call cap stops the run, and unusable edits are failed calls without candidates. Negative controls: an optimizer outside the runner channel is refused (optimizer-bypass), a non-fake channel is refused until the sandboxed host path exists (isolation-failed), and inputs with a held-out case id or the rollout canary are refused before any call (holdout-contamination).",
        "limits": "Fake optimizer and synthetic body-dependent rewards; no model contacted. The pre-call scan covers held-out case ids and the rollout canary only; held-out prompt text, the sandboxed optimizer host call and its read restrictions are T006. Evaluating a real candidate body through host rollouts is T009 work.",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_lightning_gepa"],
        "inputs": ["agent_braid/lightning_gepa.py", "agent_braid/lightning_algorithm.py", "agent_braid/lightning_runner.py",
                   "agent_braid/lightning_resources.py", "agent_braid/lightning_prompts/gepa_reflection.md",
                   "tests/test_lightning_gepa.py"],
        "outcome_note": "The Pareto front over per-prompt D4 scores keeps exactly the non-dominated candidates (a dominated candidate and an equal score vector are excluded) and parent sampling follows the number of prompts each front member scores best on (0.75 observed for 3 of 4 prompts); a child whose minibatch score beats its parent's is accepted, fully evaluated (60 rollouts) and replaces the dominated seed on the front, while children that do not improve are recorded with a minibatch score only and never fully evaluated; with the preregistered settings a run costs 3 minibatches of 10 plus one full evaluation, and a second accepted child whose full evaluation would exceed 120 rollouts is not evaluated (unit-cap); the reflection input holds only the parent text and the parent's minibatch vectors; the same seed repeats parent and minibatch choices; an unusable reflection is a failed call. Negative control: an optimizer outside the runner channel is refused (optimizer-bypass).",
        "limits": "Fake optimizer and synthetic rewards; no model contacted. Implemented from the paper's description; no GEPA or DSPy code. Pre-call scan limits as in procedure_004 (T006). No-improvement stopping is T007.",
    },
}


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(modules: list[str]) -> dict:
    command = [sys.executable, "-m", "unittest", *modules]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    tail = process.stderr.strip().splitlines()[-3:]
    ran = re.search(r"Ran (\d+) tests?", process.stderr)
    return {"command": "python -m unittest " + " ".join(modules), "returncode": process.returncode,
            "testsRun": int(ran.group(1)) if ran else None, "result": tail[-1] if tail else ""}


def main() -> int:
    EVIDENCE.mkdir(exist_ok=True)
    assurance_path = SPEC / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    scenarios = {s["id"]: s for r in assurance["requirements"] for s in r["scenarios"]}
    status = 0
    for name, spec in PROCEDURES.items():
        result = run(spec["modules"])
        passed = result["returncode"] == 0 and result["result"].startswith("OK")
        record = {
            "procedure": name, "scenario": spec["scenario"], "specification": "SPEC-072 BL.2",
            "command": result["command"], "testsRun": result["testsRun"], "result": result["result"],
            "outcome": ("passed: " if passed else "FAILED: ") + spec["outcome_note"],
            "limits": spec["limits"],
            "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
            "inputs": {path: sha(path) for path in sorted(set(spec["inputs"]))},
        }
        path = EVIDENCE / f"{name}.json"
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        relative = path.relative_to(ROOT).as_posix()
        scenarios[spec["scenario"]]["obtained_evidence"] = [{
            "command": result["command"], "limits": spec["limits"], "outcome": record["outcome"],
            "path": relative, "sha256": sha(relative)}]
        print(f"{name}: {result['result']} ({result['testsRun']} tests)")
        status |= 0 if passed else 1
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
