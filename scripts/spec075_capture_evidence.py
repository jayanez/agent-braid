# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 (BL.5): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. procedure_001 is the T001 owner review record, not a test run, so it is not captured here.
Procedures are added as their tasks land (T002: procedure_005, schema part; T003: procedure_002; T004: procedure_003; T005: procedure_004).

    python -m scripts.spec075_capture_evidence [procedure_NNN ...]

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
SPEC = ROOT / "specs/075-lightning-dataset-export"
EVIDENCE = SPEC / "evidence"
PROCEDURES = {
    'procedure_002': {
        "scenario": 'SC-002',
        "modules": ["tests.test_spec075_export_filter"],
        "inputs": ["agent_braid/lightning_export.py", "agent_braid/lightning_adapter.py", "agent_braid/lightning_store.py",
                   "tests/test_spec075_export_filter.py"],
        "outcome_note": "T003 (filter part; the recorded redaction version lands with T006): lightning_export.read_runs reads each attempt of the named runs through the SPEC-074 adapter (rollout_triplets), joins task and group ids from the content-free rollout records, and yields one item per model call with its turn index and the adapter's attempt-<hmac16> pseudonym; select keeps the exportable items in order and counts every other one under exactly one reason. In a temporary store with one rollout of three model calls (full content, prompt only, no content) and consent redacted for rollout, one record is kept and two are counted content-missing; after lowering consent to none all three are consent-none; with consent redacted but only loom listed all three are no-consent. Kept plus excluded equals the model calls, also for a unit mix of every reason (unredacted included). The exclusion reasons equal the manifest schema's exclusions.required. Unit cases: a record that is not a triplet, has no redaction object, or has scanClean false or not true is unredacted; a missing prompt or response is content-missing; consent reasons win over content reasons; a gate refusal maps to its reason and an unknown one fails closed to no-consent. The raw attempt id never appears in items or selections. Refusals: a missing run (store-missing), a rollout without a rollout record and an attempt id shared by two rollouts (source-invalid), a run named twice (invalid-argument), and an unreadable events file, a malformed JSON line, a non-object content line, a symlinked events file and a malformed salt (each Run refused with a lowercase code) are all ExportError with a fixed text naming no id or path, no chained cause and suppressed context; an adapter refusal is Adapter refused a source with its code, or source-invalid when its code is not a lowercase code. Negative controls: classifying from the triplet's losses alone fails the no-consent test; the T003 module before the review fixes fails the shared-attempt, run-twice, adapter-refusal and four of the five damaged-store cases.",
        "limits": "Temporary homes and synthetic content; rollout source only (the export input is the run store; Loom, host transcript and System One adapters are not export inputs). Consent is profile-wide, so the mix of consent states is exercised across successive profiles on one store and by unit cases, not within one read. The store fixture never yields unredacted (the adapter always redacts); only unit cases do. No redaction version is checked yet: SPEC-074 records carry none and T006 defines it. The unreadable-file case is skipped when running as root. Retention, balance, overlong and the terms gate are later tasks (T007, T008, T013); no dataset or manifest is written yet (T004-T006).",
    },
    'procedure_003': {
        "scenario": 'SC-003',
        "modules": ["tests.test_spec075_supervised"],
        "inputs": ["agent_braid/lightning_export.py", "agent_braid/lightning_adapter.py", "tests/spec075_fixtures.py",
                   "tests/test_spec075_supervised.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T004: lightning_export.supervised writes one JSONL line per unit, trace_adapter.canonical_bytes(record) plus a newline (ASCII, a non-ASCII turn escaped), {recordId, messages} (plus outcome with outcome_field), and a manifest record entry whose sha256 is the line's SHA-256 and which validates against the manifest schema's record item. Temporary store: a D4 success with two calls (one non-ASCII, one with a tool call), a D4 failure, an attempt without a reward, two more successes whose rollout ids sort against their task and group ids (two groups in one task), and an attempt without content (excluded by select as content-missing). Transition without outcome_field writes the four success calls in E3 order (task, group, rollout, attempt, turn; run id breaks ties) and leaves out two units; with outcome_field it writes all six with their outcomes; trajectory merges the two-call attempt into one record with turnRange [0, 1] and limit text-level-merge, and one-call units carry no limit. Output is identical for shuffled input; identical texts from two attempts get distinct record ids; no raw attempt id reaches a line or entry. Fail closed: a host-run result, no result, or a host-run result next to a pipeline-only one makes the attempt host-model, and any host-model unit makes the writer refuse with terms-gate-missing before writing (OD-1 deferred). Items that did not pass select (unredacted, content-missing, malformed) are refused with invalid-argument; a written record outside the contract shape (tool calls not a list) is refused with invalid-record. check_supervised refuses an unknown role, non-text content, unknown keys, a tool message without toolCallId, tool calls that are not a list or on a non-assistant message, no messages, an outcome without the flag, a missing or invalid outcome with it, and a malformed record id. Negative controls (mutants, each fails a test): source hard-coded to fixture, the check_supervised call removed, a source rule that accepts any pipeline-only result, a non-ASCII serializer, and the selected-item check removed.",
        "limits": "Temporary homes and synthetic rollout content. SC-003's manifest-hash half (lines against a written manifest) lands with T006; units left out by the d4FirstAttempt filter are returned as a count but not recorded in the manifest. Rollout content holds no tool results, so the tool role is checked only by check_supervised unit cases. Trajectory records keep only the attempt's exported calls, so an excluded middle call leaves a gap inside turnRange. No canary scan applies yet (T010): content that the SPEC-074 redactor lets through, such as another user's /Users/<name>/ path or a planted canary of unknown shape, is written as is. The terms gate is the fixed OD-1 refusal; the owner-record check is T008.",
    },
    'procedure_004': {
        "scenario": 'SC-004',
        "modules": ["tests.test_spec075_rollout"],
        "inputs": ["agent_braid/lightning_export.py", "agent_braid/lightning_adapter.py", "tests/spec075_fixtures.py",
                   "tests/test_spec075_rollout.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T005: lightning_export.rollout_records writes {recordId, rolloutId, attemptId (pseudonym), turns [{prompt, response, toolCalls}], reward, status} as trace_adapter.canonical_bytes plus a newline, with a manifest record entry whose sha256 is the line's SHA-256 and which validates against the schema's record item. A three-call succeeded rollout (one non-ASCII call, one with a tool call) yields three transition records with turnRange [0,0], [1,1], [2,2] and no limits, each carrying the attempt's SPEC-071 reward vector unchanged and status succeeded, and one trajectory record with three turns, turnRange [0, 2], outcome success and limit text-level-merge (adapter triplets carry no token IDs). With token IDs on every turn forming a prefix chain the trajectory declares no limit; a broken chain, a turn without token IDs or a non-integer token ID gives text-level-merge; token IDs never enter a record. A one-call failed rollout merges nothing and carries status failed. Order is E3 and independent of input order. The T004 checks apply: host-model items refuse with terms-gate-missing at both levels, unselected items with invalid-argument, an unknown level with invalid-argument, and a written record outside the shape (tool calls not a list) with invalid-record. check_rollout refuses an unknown key, a raw attempt id, no turns, an unknown turn key, non-text turn text, tool calls that are not a list, a non-object reward or one with other keys, an unknown status and a malformed record id. No raw attempt id reaches a line or entry. Negative controls (mutants, each fails a test): token-ID merge ignored, the limit never declared, the prefix check dropped, check_rollout removed, the input and terms check removed, the reward dropped.",
        "limits": "Temporary homes and synthetic rollout content. The token-ID path is exercised only with token IDs added to items in the test: no SPEC-074 triplet carries them. The comparison of lines with a written manifest is T006, balance is T007, and no canary scan applies yet (T010). Transition records carry the attempt's reward vector, not a per-call reward. The terms gate is the fixed OD-1 refusal until T008.",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_spec075_manifest_schema"],
        "inputs": ["schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json",
                   "tests/test_spec075_manifest_schema.py"],
        "outcome_note": "T002 part: the schema passes Draft 2020-12 check_schema. Accepted: a rollout manifest at both levels, a supervised manifest (balance none, empty balance report), a host-model manifest with a terms decision, local-model records without one, attempt ids of the four SPEC-074 pseudonym kinds, retentionDays 1 and 90 and relative terms paths. Refused: a missing record sha256 or redactionVersion or an empty redactionVersion; any missing top-level, record, exclusion, balance-report, retention-entry or terms-decision field and an unknown key in each of those objects; a negative exclusion, balance-report or turn-range counter; retentionDays 0, 91 or 1.5; an expiry that is not a valid YYYY-MM-DD date and a generatedAt that is not a valid UTC second; an absolute, dotted, whitespace, home, drive, empty or 257-character terms path and an uppercase terms sha256; an attempt id of wrong length, case or kind or a raw id; malformed run, task, group and rollout ids; unknown version, kind, level, balance (ratio included: OD-2), ordering key, canary result, exclusion reason, source, outcome or limit; a duplicate limit; a consent level other than redacted; a malformed digest, record hash, record id or turn range; no records; balance none or a supervised export with a non-empty balance report; a balanced supervised export; host-model records without a terms decision.",
        "limits": "Schema structure only: hand-written manifests; no export ran (the builder is T006, which extends this procedure). The checks the schema description lists as builder checks (hashes against bytes, turnRange order, sorted limits, a retention key per runId, unique balance-report tasks, singleOutcome with keptPerOutcome 0, supervised balance exclusions 0, host-model never labelled fixture) are not tested here. jsonschema is a development dependency; the runtime stays standard-library only.",
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
            "procedure": name, "scenario": spec["scenario"], "specification": "SPEC-075 BL.5",
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
