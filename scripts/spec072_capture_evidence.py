# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 (BL.2): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. Procedure 001 binds the owner review and protocol freeze; procedure 008 binds the owner-approved T010
held-out run (evidence/heldout-arms.json) together with its pipeline tests. Converged at T012 (2026-11-13).

    python -m scripts.spec072_capture_evidence [procedure_NNN ...]

Naming procedures re-runs only those; the default re-runs every procedure.
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
    'procedure_001': {
        "scenario": 'SC-001',
        "modules": ["tests.test_lightning_freeze"],
        "inputs": ["specs/072-lightning-prompt-optimization/evaluation-protocol.md",
                   "specs/072-lightning-prompt-optimization/evidence/protocol-freeze.json",
                   "specs/072-lightning-prompt-optimization/evidence/development-arms.json",
                   "agent_braid/lightning_runner.py", "tests/test_lightning_freeze.py"],
        "outcome_note": "The owner reviewed and approved protocol Amendment 1 (items 1-6) on 2026-11-13 before any development rollout; the development phase ran (A0 27/30 first attempt; best GEPA 0.967, best APO 0.233 on the full development set; claude-code, model claude-sonnet-5-5, subscription route; evidence/development-arms.json). evidence/protocol-freeze.json records the sha256 of evaluation-protocol.md and of the development evidence, with the held-out set unopened. The committed freeze matches the protocol. Negative controls: a held-out run with an edited protocol is refused before anything is read or launched (protocol-hash-mismatch), and a missing freeze record is refused (protocol-not-frozen).",
        "limits": "The freeze binds the protocol bytes, not reviewer intent; approval is the owner's merge of the freeze pull request. One required host (claude-code); opencode is a declared limit per Amendment 1. Development scores are descriptive; H1 is decided on held-out (T010).",
    },
    'procedure_002': {
        "scenario": 'SC-002',
        "modules": ["tests.test_lightning_resources"],
        "inputs": ["agent_braid/lightning_resources.py", "agent_braid/lightning_store.py", "agent_braid/lightning_schema.py",
                   "tests/test_lightning_resources.py", "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"],
        "outcome_note": "The seed is the analyze skill body below its fixed front matter; seed and child records round-trip canonically byte for byte; the child names the seed as parent; text whose hash differs, unknown keys, foreign origins, refused contamination checks and broken lineage are refused with codes; the store keeps text beside the record privately and refuses a record without matching text; later records may change only scores and Pareto membership.",
        "limits": "Record and store only. Runs journal their source commit and seed skill; a resume at another commit is refused and replay rebuilds the seed from the journaled source (review fixes, #1348); this procedure does not test that.",
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
        "limits": "Fake optimizer and synthetic body-dependent rewards; no model contacted. The full pre-call scan and the sandboxed optimizer host are evidenced by procedure_006. Real candidate bodies were evaluated through Claude Code rollouts in T009 (evidence/development-arms.json, bound by procedure_001), not by this procedure.",
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
        "limits": "Fake optimizer and synthetic rewards; no model contacted. Resume is exercised through the algorithm API; the real T009 development runs and the T010 held-out run ended without a stop, so no stop rule other than the round cap was observed on a real host.",
    },
    'procedure_008': {
        "scenario": 'SC-008',
        "modules": ["tests.test_spec072_heldout"],
        "inputs": ["scripts/spec072_heldout.py", "scripts/spec072_development_arms.py",
                   "agent_braid/lightning_runner.py", "agent_braid/lightning_evaluation.py",
                   "agent_braid/lightning_store.py", "agent_braid/lightning_reward.py",
                   "agent_braid/lightning_arm.py", "agent_braid/lightning_resources.py",
                   "agent_braid/lightning_config.py", "scripts/spec069_scoring.py",
                   "scripts/spec069_native_runs.py", "specs/069-aim-request-authoring/prompts/held-out.json",
                   "specs/072-lightning-prompt-optimization/evaluation-protocol.md",
                   "specs/072-lightning-prompt-optimization/evidence/protocol-freeze.json",
                   "specs/072-lightning-prompt-optimization/evidence/development-arms.json",
                   "tests/test_spec072_heldout.py",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-arms.json",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-registration.json",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-evaluation-record.json"],
        "outcome_note": "OBTAINED (owner-approved held-out run, 2026-11-13; claude-code 2.1.311, model claude-sonnet-5-5, subscription route, 90 rollouts, no stop, no refusal, 0 canary hits, clean teardown; evidence/heldout-arms.json): A0 (current guidance) 25/30 first attempt, 8/10 prompts (misses HELD-04, HELD-06), Wilson 0.66-0.93, D4 misses; A1 APO 23/30, 7/10 prompts, D4 misses; A2 GEPA 24/30, 7/10 prompts (misses HELD-02, HELD-04, HELD-06), Wilson 0.63-0.90, D4 misses, schema-valid 28/30. Paired per prompt against A0: A2 1 improved, 8 unchanged, 1 worsened (sign test p = 1.0); A1 1 improved, 7 unchanged, 2 worsened (p = 1.0). H1 by the preregistered rule: A0 misses D4 and A2 misses D4 in the required host, so H1 is NOT SUPPORTED (a negative result, reported as observed). The SPEC-049 pair (A = A0, C = A2) records the same outcome. Pipeline check on fake hosts: the command checks the protocol freeze first (an edited protocol is refused before arms are resolved or anything launches) and that the development evidence is the one the freeze binds; it resolves A0 (the final guidance, required to be the seed both arms optimized), A1 and A2 (best APO and GEPA bodies read by sha256 from the laboratory run stores and verified; missing or tampered text refused; E1/E2 excluded); a model other than the development arms' pinned model is refused; the dry run prints 10 cases x 3 repetitions = 30 rollouts per arm, 90 in total, about 35 minutes, with each arm's candidate hash and the freeze result. Each arm runs once with its run id recorded before it starts; a stopped arm resumes and a complete arm is never run again; a run that evaluated another candidate is refused before it resumes; each rollout is scored from its first attempt result that is not a quota stop, so a refused rollout scores as a failed attempt even if a resume retried it; a safety refusal (route-unverified, credential-leak) stops the arm and is never resumed or analysed; a recorded run with rollouts but no store is refused instead of run again; a canary count above one replays to its stored reward hash. The analysis gives per arm the summarize D4 verdict, Wilson intervals, schema validity and canary hits, paired per-prompt counts of A1 and A2 against A0 with an exact two-sided sign test, and H1 by the protocol rule (truth table incl. not-assessable and canary invalidation); the SPEC-049 pair (A = A0, C = A2) agrees with it; the evidence is checked free of credentials, attempt payloads and skill text.",
        "limits": "One required host (claude-code; opencode a declared limit per Amendment 1), one model, one held-out pass per arm (10 prompts x 3 repetitions): low power, so the descriptive sign test cannot detect small effects. The result describes these host and model versions and prompt sets only. The pipeline tests use fake hosts.",
    },
    'procedure_009': {
        "scenario": 'SC-009',
        "modules": ["tests.test_lightning_cli.BL2BoundaryTests"],
        "inputs": ["tests/test_lightning_cli.py", "pyproject.toml",
                   "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md",
                   *sorted(str(p.relative_to(ROOT)) for pattern in ("agent_braid/lightning_*.py",
                                                                     "scripts/spec072_*.py", "agent_braid/*mcp*.py",
                                                                     "integrations/**/*.json")
                           for p in ROOT.glob(pattern))],
        "outcome_note": "A complete fake optimization run (baseline seed run, then a GEPA arm on fake hosts) leaves the repository analyze skill file byte- and mtime-identical and reports the best candidate as a 64-hex bestSha256 with no skill text in the summary. Every agent_braid/lightning_*.py module and scripts/spec072_*.py script imports only the standard library, other lightning modules and an explicit allowlist (plugin_registry, harness_host_claude, the T013 format-only harness_evaluation and system_one, the SPEC-069 scoring, native-run, fixture and plugin-build scripts, and the BL.2 development-arms script the T010 held-out script reuses); no lightning module names decide, begin, execute, recover, harness_promotion, import_module, __import__ or any grant identifier; importing all of them in a fresh interpreter loads no promotion, lifecycle, runtime-policy, git-execution, scheduler or MCP module; no MCP server module or integration JSON manifest mentions lightning; pyproject has no runtime dependency and no lightning extra. Negative control: adding `from .harness_promotion import decide` to a lightning module fails the allowlist, name and import-closure checks.",
        "limits": "Static and import-closure checks cover the modules present at this commit; a fake-host run cannot show what a real host process writes outside the sandbox (SPEC-071 OS sandbox evidence covers that). Unchanged skill bytes are asserted for the repository copy only.",
    },
    'procedure_010': {
        "scenario": 'SC-010',
        "modules": ["tests.test_lightning_replay"],
        "inputs": ["agent_braid/lightning_algorithm.py", "agent_braid/lightning_apo.py", "agent_braid/lightning_gepa.py",
                   "agent_braid/lightning_store.py", "agent_braid/lightning_reward.py", "tests/test_lightning_replay.py",
                   "tests/lightning_fakes.py"],
        "outcome_note": "Each APO and GEPA run journals a start entry with its algorithm and seed, every optimizer call with its input hash and output, and every evaluation as the ids and sha256 of the SPEC-071 attempt-result records it stored; the run manifest holds the configuration digest and candidate records keep parent links and optimizer call ids. Vectors are always re-scored from the stored content-free parsed attempts. Replaying a finished APO or GEPA run from its journal and stored records makes no optimizer or evaluator call, writes nothing and reproduces every candidate record (lineage, minibatch and full scores, Pareto membership) and the best candidate. Negative controls: altering one stored attempt-result record is detected by hash and changes a selection; a journal that ends early is refused (replay-incomplete); the default scorer refuses held-out records (holdout-contamination) and scores a refusal as a failed D4 attempt.",
        "limits": "Fake optimizer; synthetic vectors carried in fake attempt-result records and read back by a test scorer; the default scorer is exercised on one development case only. The real T009 runs recorded no altered results and replayed nothing (evidence/development-arms.json); a full replay of those private run stores is not part of the committed evidence.",
    },
    'procedure_011': {
        "scenario": 'SC-011',
        "modules": ["tests.test_lightning_evaluation"],
        "inputs": ["agent_braid/lightning_evaluation.py", "agent_braid/harness_evaluation.py",
                   "agent_braid/harness_promotion.py", "tests/test_lightning_evaluation.py",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-arms.json",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-registration.json",
                   "specs/072-lightning-prompt-optimization/evidence/heldout-evaluation-record.json"],
        "outcome_note": "From synthetic held-out results, spec049_pair writes a SPEC-049 Registration and EvaluationRecord in REGISTRATION_FORMAT and REPORT_FORMAT with arm A = A0 and arm C = A2 (GEPA) by candidate hash, the H1 outcome per required host (claude-code) under the protocol rule (supported, not-supported, not-assessable; a canary hit invalidates the arm) and executionAuthorization false; both records load through the harness_promotion verifiers and a pending decide() call in the test accepts the pair with the C-vs-A regression descriptive-only. The writer never names decide, begin or harness_promotion. Negative controls: arm C set to A1 is refused (arm-c-not-a2), arm A not A0 is refused (arm-a-not-a0), a report edited after recording fails the byte check, and a report bound to another registration is refused (registration-mismatch). The committed T010 pair (evidence/heldout-registration.json, evidence/heldout-evaluation-record.json) matches the sha256 recorded in evidence/heldout-arms.json, loads through the harness_promotion verifiers, binds A = A0 and C = A2 by candidate hash, and records H1 not-supported for claude-code, equal to the held-out analysis.",
        "limits": "The writer is tested over synthetic held-out summaries; the committed T010 pair is checked by bytes, formats, arms and H1 against evidence/heldout-arms.json, and records H1 not supported. BL.2 never calls decide(). The SPEC-049 noninferiority test is not part of the frozen protocol and is reported descriptive-only, so an approved SPEC-073 promotion over this pair is refused (regression-not-covered) unless SPEC-073 decides otherwise.",
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


def main(argv: list[str] | None = None) -> int:
    selected = (sys.argv[1:] if argv is None else argv) or list(PROCEDURES)
    unknown = set(selected) - set(PROCEDURES)
    if unknown:
        print("unknown procedure: " + ", ".join(sorted(unknown)), file=sys.stderr)
        return 2
    EVIDENCE.mkdir(exist_ok=True)
    assurance_path = SPEC / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    scenarios = {s["id"]: s for r in assurance["requirements"] for s in r["scenarios"]}
    status = 0
    for name in selected:
        spec = PROCEDURES[name]
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
        if spec.get("planned"):
            record["status"] = "planned"
            record["outcome"] = ("planned pipeline check passed: " if passed else "FAILED: ") + spec["outcome_note"]
        path = EVIDENCE / f"{name}.json"
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"{name}: {result['result']} ({result['testsRun']} tests){' [planned]' if spec.get('planned') else ''}")
        status |= 0 if passed else 1
        if spec.get("planned"):
            continue  # not obtained evidence: the scenario stays unbound until the real run
        relative = path.relative_to(ROOT).as_posix()
        scenarios[spec["scenario"]]["obtained_evidence"] = [{
            "command": result["command"], "limits": spec["limits"], "outcome": record["outcome"],
            "path": relative, "sha256": sha(relative)}]
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
