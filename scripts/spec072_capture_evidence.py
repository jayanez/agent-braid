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
                   "agent_braid/lightning_prompts/apo_apply_edit.md", "tests/test_lightning_apo.py", "tests/lightning_fakes.py"],
        "outcome_note": "With the preregistered parameters (beam 2, branch 2, 2 rounds, minibatch 5, 2 hosts, 3 repetitions) APO runs 1 then 2 parents with 2 then 4 children, 9 optimizer calls and 120 rollouts (20 + 40 search, 60 full evaluation of the best), as in the feasibility table; every APO candidate records its parent, round, two call ids, both passed contamination checks and the hash of the critique and edit templates; configuration defaults stop at the 120-rollout cap (unit-cap), configured rounds above 3 are capped at 3, the optimizer-call cap stops the run, and unusable edits are failed calls without candidates. Negative controls: an optimizer outside the runner channel is refused (optimizer-bypass), a non-fake channel is refused until the sandboxed host path exists (isolation-failed), and inputs with a held-out case id or the rollout canary are refused before any call (holdout-contamination).",
        "limits": "Fake optimizer and synthetic body-dependent rewards; no model contacted. The full pre-call scan and the sandboxed optimizer host are evidenced by procedure_006. Evaluating a real candidate body through host rollouts is T009 work.",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_lightning_gepa"],
        "inputs": ["agent_braid/lightning_gepa.py", "agent_braid/lightning_algorithm.py", "agent_braid/lightning_runner.py",
                   "agent_braid/lightning_resources.py", "agent_braid/lightning_prompts/gepa_reflection.md",
                   "tests/test_lightning_gepa.py", "tests/lightning_fakes.py"],
        "outcome_note": "The Pareto front over per-prompt D4 scores keeps exactly the non-dominated candidates (a dominated candidate and an equal score vector are excluded) and parent sampling follows the number of prompts each front member scores best on (0.75 observed for 3 of 4 prompts); a child whose minibatch score beats its parent's is accepted, fully evaluated (60 rollouts) and replaces the dominated seed on the front, while children that do not improve are recorded with a minibatch score only and never fully evaluated; with the preregistered settings a run costs 3 minibatches of 10 plus one full evaluation, and a second accepted child whose full evaluation would exceed 120 rollouts is not evaluated (unit-cap); the reflection input holds only the parent text and the parent's minibatch vectors; the same seed repeats parent and minibatch choices; an unusable reflection is a failed call. Negative control: an optimizer outside the runner channel is refused (optimizer-bypass).",
        "limits": "Fake optimizer and synthetic rewards; no model contacted. Implemented from the paper's description; no GEPA or DSPy code. The pre-call scan and sandboxed host are evidenced by procedure_006.",
    },
    'procedure_006': {
        "scenario": 'SC-006',
        "modules": ["tests.test_lightning_contamination"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "scripts/spec072_holdout_fingerprints.py",
                   "specs/072-lightning-prompt-optimization/holdout-fingerprints.json",
                   "specs/069-aim-request-authoring/prompts/FREEZE.json", "tests/test_lightning_contamination.py",
                   "tests/fixtures/lightning-fake-hosts/claude"],
        "outcome_note": "The committed held-out fingerprints (sha256 of held-out case ids and of every 8-word normalized window of the held-out prompts not shared with a development prompt) are reproducible and bound to the FREEZE hash of held-out.json; the analyze skill body and every development prompt pass the scan; a held-out 8-word excerpt in different case and spacing, a held-out case id (by pattern and by hash), the held-out canary planted only in held-out rollout workspaces, and the rollout canary are refused (holdout-contamination); stale fingerprints are refused (holdout-fingerprint-stale); the channel checks before every call and a refused input never reaches the host. The sandboxed optimizer host runs Claude Code with no tools, no plugin and an empty working directory in a disposable profile without API keys; its protected paths include held-out.json, the SPEC-069 scoring and fixture sources and .git, and on macOS the isolation probe is enforced and a read of held-out.json under the sandbox fails; teardown is clean. Negative controls: an unverified credential source (route-unverified), a paid key in the parent environment (paid-route-refused), OpenCode as optimizer host (route-unverified) and a non-fake in-process transport (isolation-failed) are refused.",
        "limits": "Fake Claude Code host; no model contacted. The scan matches exact 8-word windows after normalization: paraphrased held-out content is not detected. Windows shared with development prompts are not fingerprinted (held-out prompts keep 11 to 45 windows each). Sandbox denial is asserted only on macOS (sandbox-exec); elsewhere real optimizer calls are refused.",
    },
    'procedure_007': {
        "scenario": 'SC-007',
        "modules": ["tests.test_lightning_stopping"],
        "inputs": ["agent_braid/lightning_algorithm.py", "agent_braid/lightning_apo.py", "agent_braid/lightning_gepa.py",
                   "agent_braid/lightning_store.py", "agent_braid/lightning_runner.py", "tests/test_lightning_stopping.py", "tests/lightning_fakes.py"],
        "outcome_note": "With budgets set low in fake runs each algorithm stops at the first applicable rule and records it in the run journal: unit-cap (APO at configuration defaults), optimizer-cap, no-improvement after 2 consecutive flat rounds, and a weekly-stop quota stop that carries the explicit `agent-braid lightning run --resume <run-id>` command; a refused optimizer input (holdout-contamination) stops the run with the refusal recorded and no call made; APO never runs more than 3 rounds; no run exceeds its rollout or optimizer-call cap (negative control). Resuming a quota-stopped APO or GEPA run with the same seed replays the journaled optimizer outputs and evaluations in order and reaches the same rounds, best candidate, rollouts and calls as an uninterrupted run without repeating any optimizer call; resuming with another seed or configuration is refused (resume-diverged). The journal is private and refuses unknown entry shapes.",
        "limits": "Fake optimizer and synthetic rewards; no model contacted. Resume is exercised through the algorithm API; wiring the algorithms into `agent-braid lightning run` with real candidate evaluation is T009 work.",
    },
    'procedure_010': {
        "scenario": 'SC-010',
        "modules": ["tests.test_lightning_replay"],
        "inputs": ["agent_braid/lightning_algorithm.py", "agent_braid/lightning_apo.py", "agent_braid/lightning_gepa.py",
                   "agent_braid/lightning_store.py", "agent_braid/lightning_reward.py", "tests/test_lightning_replay.py",
                   "tests/lightning_fakes.py"],
        "outcome_note": "Each APO and GEPA run journals a start entry with its algorithm and seed, every optimizer call with its input hash and output, and every evaluation as the ids and sha256 of the SPEC-071 attempt-result records it stored; the run manifest holds the configuration digest and candidate records keep parent links and optimizer call ids. Vectors are always re-scored from the stored content-free parsed attempts. Replaying a finished APO or GEPA run from its journal and stored records makes no optimizer or evaluator call, writes nothing and reproduces every candidate record (lineage, minibatch and full scores, Pareto membership) and the best candidate. Negative controls: altering one stored attempt-result record is detected by hash and changes a selection; a journal that ends early is refused (replay-incomplete); the default scorer refuses held-out records (holdout-contamination) and scores a refusal as a failed D4 attempt.",
        "limits": "Fake optimizer; synthetic vectors carried in fake attempt-result records and read back by a test scorer; the default scorer is exercised on one development case only. Real runs that produce these records through `agent-braid lightning run` are T009 work.",
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
