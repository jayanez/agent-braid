# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 (BL.5): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. procedure_001 is the T001 owner review record, not a test run, so it is not captured here.
Procedures are added as their tasks land (T002: procedure_005, schema part; T003: procedure_002; T004: procedure_003; T005: procedure_004; T006: procedure_005 builder part, procedure_006; T007: procedure_007; T008: procedure_008).

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
        "limits": "Temporary homes and synthetic content; rollout source only (the export input is the run store; Loom, host transcript and System One adapters are not export inputs). Consent is profile-wide, so the mix of consent states is exercised across successive profiles on one store and by unit cases, not within one read. The store fixture never yields unredacted (the adapter always redacts); only unit cases do. SPEC-074 records carry no redaction version, so the filter checks scanClean only; the dataset's redactionVersion is set by the T006 builder (procedure_005). The unreadable-file case is skipped when running as root. Overlong records are never produced (no length bound is applied); balance is procedure_007, the terms gate procedure_008, retention refusals T013; writing the dataset is procedure_003 to procedure_006.",
    },
    'procedure_003': {
        "scenario": 'SC-003',
        "modules": ["tests.test_spec075_supervised", "tests.test_spec075_manifest"],
        "inputs": ["agent_braid/lightning_export.py", "agent_braid/lightning_adapter.py", "tests/spec075_fixtures.py",
                   "tests/test_spec075_supervised.py", "tests/test_spec075_manifest.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T004: lightning_export.supervised writes one JSONL line per unit, trace_adapter.canonical_bytes(record) plus a newline (ASCII, a non-ASCII turn escaped), {recordId, messages} (plus outcome with outcome_field), and a manifest record entry whose sha256 is the line's SHA-256 and which validates against the manifest schema's record item. Temporary store: a D4 success with two calls (one non-ASCII, one with a tool call), a D4 failure, an attempt without a reward, two more successes whose rollout ids sort against their task and group ids (two groups in one task), and an attempt without content (excluded by select as content-missing). Transition without outcome_field writes the four success calls in E3 order (task, group, rollout, attempt, turn; run id breaks ties) and leaves out two units; with outcome_field it writes all six with their outcomes; trajectory merges the two-call attempt into one record with turnRange [0, 1] and limit text-level-merge, and one-call units carry no limit. Output is identical for shuffled input; identical texts from two attempts get distinct record ids; no raw attempt id reaches a line or entry. Fail closed: a host-run result, no result, or a host-run result next to a pipeline-only one makes the attempt host-model, and any host-model unit makes the writer refuse with terms-gate-missing before writing (OD-1 deferred). Items that did not pass select (unredacted, content-missing, malformed) are refused with invalid-argument; a written record outside the contract shape (tool calls not a list) is refused with invalid-record. check_supervised refuses an unknown role, non-text content, unknown keys, a tool message without toolCallId, tool calls that are not a list or on a non-assistant message, no messages, an outcome without the flag, a missing or invalid outcome with it, and a malformed record id. Negative controls (mutants, each fails a test): source hard-coded to fixture, the check_supervised call removed, a source rule that accepts any pipeline-only result, a non-ASCII serializer, and the selected-item check removed.",
        "limits": "Temporary homes and synthetic rollout content. SC-003's manifest-hash half runs in tests.test_spec075_manifest (T006): each written line's SHA-256 and record id match its manifest entry; units left out by the d4FirstAttempt filter are returned as a count but not recorded in the manifest. Rollout content holds no tool results, so the tool role is checked only by check_supervised unit cases. Trajectory records keep only the attempt's exported calls, so an excluded middle call leaves a gap inside turnRange. No canary scan applies yet (T010): content that the SPEC-074 redactor lets through, such as another user's /Users/<name>/ path or a planted canary of unknown shape, is written as is. The terms gate refuses host-model output without an owner record (procedure_008).",
    },
    'procedure_004': {
        "scenario": 'SC-004',
        "modules": ["tests.test_spec075_rollout"],
        "inputs": ["agent_braid/lightning_export.py", "agent_braid/lightning_adapter.py", "tests/spec075_fixtures.py",
                   "tests/test_spec075_rollout.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T005: lightning_export.rollout_records writes {recordId, rolloutId, attemptId (pseudonym), turns [{prompt, response, toolCalls}], reward, status} as trace_adapter.canonical_bytes plus a newline, with a manifest record entry whose sha256 is the line's SHA-256 and which validates against the schema's record item. A three-call succeeded rollout (one non-ASCII call, one with a tool call) yields three transition records with turnRange [0,0], [1,1], [2,2] and no limits, each carrying the attempt's SPEC-071 reward vector unchanged and status succeeded, and one trajectory record with three turns, turnRange [0, 2], outcome success and limit text-level-merge (adapter triplets carry no token IDs). With token IDs on every turn of consecutive calls forming a prefix chain the trajectory declares no limit; a broken chain, a turn without token IDs, a non-integer token ID, or a chain whose middle call was excluded (turnRange [0, 2] with two turns) gives text-level-merge; token IDs never enter a record. A one-call failed rollout merges nothing and carries status failed. A rollout with two attempts is refused by read_runs with source-invalid and a fixed text. Order is E3 (task before rollout: a rollout id that sorts first but belongs to a later task comes last) and independent of input order. The T004 checks apply: host-model items refuse with terms-gate-missing at both levels, unselected items with invalid-argument, an unknown level with invalid-argument, and a written record outside the shape (tool calls not a list) with invalid-record. check_rollout refuses an unknown key, a raw attempt id, no turns, an unknown turn key, non-text turn text, tool calls that are not a list, a non-object reward or one with other keys, an unknown status and a malformed record id. No raw attempt id reaches a line or entry. Negative controls (mutants, each fails a test): token-ID merge ignored, the limit never declared, the prefix check dropped, the consecutive-call check dropped, the one-attempt check dropped, check_rollout removed, the input and terms check removed, the reward dropped.",
        "limits": "Temporary homes and synthetic rollout content. The token-ID path is exercised only with token IDs added to items in the test: no SPEC-074 triplet carries them. The comparison of lines with a written manifest is procedure_005 and procedure_006, balance procedure_007, and the canary corpus is T010 (the export already runs the SPEC-074 post-redaction scan). Transition records carry the attempt's reward vector, not a per-call reward. Trajectory records keep only the attempt's exported calls, so an excluded middle call leaves a gap inside turnRange (declared text-level-merge, never a token-ID merge). The writers share one loop (_write) with the supervised writer, whose limits follow the same rule. The terms gate refuses host-model output without an owner record (procedure_008).",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_spec075_manifest_schema", "tests.test_spec075_manifest"],
        "inputs": ["schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json",
                   "tests/test_spec075_manifest_schema.py", "agent_braid/lightning_export.py",
                   "agent_braid/lightning_redact.py", "tests/spec075_fixtures.py", "tests/test_spec075_manifest.py"],
        "outcome_note": "T006 part: export_dataset writes exactly records.jsonl and manifest.json for both kinds at both levels (supervised with and without the outcome field), the manifest file is the canonical manifest bytes plus a newline and every manifest validates against the schema; recordsSha256 is the SHA-256 of records.jsonl and each record entry's sha256 and recordId match its line (SC-003's manifest half); redactionVersion is spec074-redact/<16 hex> of the SPEC-074 redactor's pattern sources and salt size, stable across calls and different when a token pattern or the salt size changes; termsDecision is null, canaryScan clean, balance none with an empty report, exclusions count the content-free call, retention gives each cited run its retentionDays and expiry date, and digest is the SHA-256 of the canonical manifest without generatedAt and digest. Each check inside check_manifest refuses (invalid-manifest) when tested directly: a wrong records or record hash, a record id not in its line, an unordered turn range, unsorted limits, retention missing a cited run or citing another, a duplicate balance-report task, a single-outcome task that keeps records, a supervised export with balance exclusions or balance equal, a host-model record labelled fixture, a host-model record without a terms decision, an unscanned manifest, an extra line and a stale digest; through export_dataset, a retention map missing a cited run and a writer entry with a wrong hash are refused with invalid-manifest and nothing is written. Negative controls (mutants, each fails a test): generatedAt inside the digest, the scan removed, each builder check removed, the check_manifest call unhooked from the builder, a fixed redaction version. T002 part: the schema passes Draft 2020-12 check_schema. Accepted: a rollout manifest at both levels, a supervised manifest (balance none, empty balance report), a host-model manifest with a terms decision, local-model records without one, attempt ids of the four SPEC-074 pseudonym kinds, retentionDays 1 and 90 and relative terms paths. Refused: a missing record sha256 or redactionVersion or an empty redactionVersion; any missing top-level, record, exclusion, balance-report, retention-entry or terms-decision field and an unknown key in each of those objects; a negative exclusion, balance-report or turn-range counter; retentionDays 0, 91 or 1.5; an expiry that is not a valid YYYY-MM-DD date and a generatedAt that is not a valid UTC second; an absolute, dotted, whitespace, home, drive, empty or 257-character terms path and an uppercase terms sha256; an attempt id of wrong length, case or kind or a raw id; malformed run, task, group and rollout ids; unknown version, kind, level, balance (ratio included: OD-2), ordering key, canary result, exclusion reason, source, outcome or limit; a duplicate limit; a consent level other than redacted; a malformed digest, record hash, record id or turn range; no records; balance none or a supervised export with a non-empty balance report; a balanced supervised export; host-model records without a terms decision.",
        "limits": "Temporary homes and synthetic fixture content; the schema half uses hand-written manifests. Here the balance-report checks run on hand-made rows; the balancer and its report checks through export_dataset are procedure_007. The terms-decision branch is exercised only as a refusal (OD-1 deferred). The scan is the SPEC-074 post-redaction scan; canary corpus coverage is T010. redactionVersion covers only the redactor's pattern sources and salt size, not its code. jsonschema is a development dependency; the runtime stays standard-library only.",
    },
    'procedure_006': {
        "scenario": 'SC-006',
        "modules": ["tests.test_spec075_manifest"],
        "inputs": ["agent_braid/lightning_export.py", "tests/spec075_fixtures.py", "tests/test_spec075_manifest.py"],
        "outcome_note": "T006: two exports of one fixture store (two runs, a non-ASCII turn, a content-free call), the second with the runs named in the other order, the items shuffled before the filter, another working directory and a different clock, write byte-identical records.jsonl and a manifest equal except generatedAt, with the same digest. The dataset and manifest bytes hold no temporary or home path, no raw attempt id and no store timestamp (records carry no createdAt). An existing non-empty output directory is refused with output-not-empty and left as it was; an empty one is filled. Nothing is written into the output itself: it does not exist while the files are written, and it appears only by renaming a private .export-* directory beside it holding exactly the two files; the directory is 0700 and the files 0600. A write failure after records.jsonl (patched os.fdopen) is refused with path-refused, no chained cause, and a KeyboardInterrupt there propagates, both leaving neither the output nor a temporary directory; a symlinked output or output parent is refused with path-refused; canary-detected (a planted token shape), invalid-argument (balance ratio, an unknown kind or level, a negative or boolean seed, a balanced supervised export, an outcome field on a rollout export) no-records (consent none) and terms-gate-missing (a run whose attempt has no result, so host-model) write nothing. Negative controls (mutants, each fails a test): the temporary-directory cleanup removed, the interrupt cleanup removed, writing straight into the output, the symlink check removed.",
        "limits": "Temporary homes and synthetic content; determinism is shown for one store, two orders, two working directories and two clocks in one process and one Python version, not across platforms or locales. SC-006 assumes the same $HOME at ingest and at export: the SPEC-074 adapter redacts the current $HOME to ~ when it reads content, so a different $HOME changes the bytes (and a $HOME that is a prefix of a path in the content can make the read refuse with redaction-incomplete); SPEC-074 is not changed here. A crash between the temporary directory and the rename can leave a .export-* directory (documented, not swept). The planted canary is injected after the writer (the store content is already redacted); T010 adds the corpus. These tests export with balance none (the balanced export is procedure_007); the terms decision (procedure_008), the CLI (T009) and retention refusals (T013) are not exercised.",
    },
    'procedure_007': {
        "scenario": 'SC-007',
        "modules": ["tests.test_spec075_balance"],
        "inputs": ["agent_braid/lightning_export.py", "tests/spec075_fixtures.py", "tests/test_spec075_balance.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T007: lightning_export.balance_equal keeps, per task, min(successes, failures) attempts of each outcome by the lowest SHA-256 of [seed, taskId, runId, rolloutId] (no attempt pseudonym, so a re-ingest with a new salt selects the same attempts). Fixture store: task-a with 5 successes (one of two calls), 2 failures and 1 attempt without a reward; task-b with 3 successes only; task-c with one of each; task-d with 2 successes and 5 failures. With seed 0 task-a keeps 2 + 2, reported as successes 5, failures 2, unknown 1, keptPerOutcome 2, dropped 4; task-d keeps 2 + 2, reported successes 2, failures 5, keptPerOutcome 2, dropped 3; task-b keeps nothing and is reported singleOutcome true, keptPerOutcome 0, dropped 3, not padded; task-c keeps one of each. The kept rollouts for seed 0 are pinned (task-a ro-a0, ro-a4, ro-f0, ro-f1; task-d ro-d0, ro-d1, ro-e2, ro-e4) and the rank of one key is pinned to its hex; a second store with the same data and another salt (disjoint attempt pseudonyms) selects the same rollouts. Attempts are kept whole and kept plus dropped model calls equal the input. The choice is the same for reversed input and reruns with the same seed (identical records bytes and digest), changes with the seed, and the manifest records the seed. Rollout exports balance by default at both levels and validate against the schema; dropped attempts leave neither their pseudonym nor their rollout id in records.jsonl or manifest.json; balance none exports every attempt with an empty report. check_manifest, through export_dataset with a tampered balancer, refuses (invalid-manifest, nothing written) a 1-vs-1 task claiming keptPerOutcome 5 and dropped 0, a cap below the minimum, a wrong singleOutcome, a wrong dropped count, an extra or a missing kept attempt, an empty report under balance equal, a report under balance none, a duplicate task and a kept task missing from the report. Supervised exports are never balanced: balance equal is refused (invalid-argument) with or without the outcome field, and the default supervised export has balance none, an empty report and no balance exclusions. A ratio, unknown or boolean balance and a negative, boolean, fractional or text seed are refused (OD-2: no ratio parameter); an export that balance empties refuses with no-records. The terms gate stays closed: host-model runs refuse with terms-gate-missing, also when balance would drop them. Negative controls (mutants, each fails a test): max or the failure count instead of min, a reversed rank, a rank without the task or with the attempt pseudonym, an unseeded rank, the terms check after balance, unknown attempts kept, dropped calls not counted, a none default, the supervised guard removed, singleOutcome never set, and each report check removed.",
        "limits": "Temporary homes and synthetic fixture content; one seed per assertion plus a range of seeds to show the seed matters, not a statistical test of the choice. Same data and seed give the same selection (the key holds no salt-dependent pseudonym; a rollout has one attempt, which read_runs enforces). The balance unit is the attempt, so a long attempt and a short one weigh the same. No claim is made that balance benefits a model (E4). The terms gate refuses host-model output without an owner record (procedure_008).",
    },
    'procedure_008': {
        "scenario": 'SC-008',
        "modules": ["tests.test_spec075_terms"],
        "inputs": ["agent_braid/lightning_export.py", "tests/spec075_fixtures.py", "tests/test_spec075_terms.py",
                   "schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json"],
        "outcome_note": "T008: load_terms_decision reads terms/<name>.json under the plugin home's lightning directory and the export refuses every non-fixture unit not covered by it with terms-gate-missing before writing anything, with a text naming no path or field value and no chained cause. All records are SYNTHETIC, written to temporary homes, naming a fictional provider and model; none is committed, and a repository scan finds no file with the record schema. Without a record (or naming a missing file) a fixture plus host-run export refuses, while a fixture-only export succeeds and cites no record. With a permitting synthetic record covering the host and model, the host units export and the manifest cites the record's relative path and SHA-256 and validates against the schema; a fixture-only export with the same record cites none. Per-unit binding: a record for another host or another model, a unit outside the record next to covered ones, a unit with no attempt_start model, and a unit of another host with the same model id all refuse. Outcomes forbids-training, undecided and unknown values refuse, through the export and through the loader alone. Dates: a review after the export day, a validUntil before it, inverted dates, an impossible date, a timestamp and a missing review date refuse; both bounds are inclusive. Malformed records refuse: missing, empty or doubled terms, an http URL, no or control-character provider, empty, non-list or duplicate models, an unknown host, an unknown key, another schema, a non-object, invalid JSON, a duplicate key and more than 16 KiB; an https URL record is accepted. Unsafe paths refuse: absolute, dotted, other directories, subdirectories, other extensions or names with spaces (also when such files exist), a record readable by others and a symlinked record. The supervised and rollout writers apply the same gate. check_manifest refuses host-model records without termsDecision. Negative controls (mutants, each fails a test): the gate skipped, the per-unit check ignoring the outcome, the loader accepting any outcome, any host, any model, the review date ignored, validUntil ignored, the terms version or URL ignored, http URLs accepted, any path accepted, the privacy check removed, the export clock ignored, and a record cited for a fixture-only export.",
        "limits": "Synthetic records only: no real provider's terms were reviewed (OD-1 deferred) and nothing here says any provider permits training; host-run units come from synthetic fixtures. Coverage is by exact model id from the attempt_start event; units without one cannot be covered. The record's provider name is recorded, not checked against the host. One record per export. Expiry is the owner's validUntil date compared with the export's UTC day; no review period is set by Agent Braid.",
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
