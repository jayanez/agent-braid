# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 (BL.5): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. procedure_001 is the T001 owner review record, not a test run, so it is not captured here.
Procedures are added as their tasks land (T002: procedure_005, schema part; T003: procedure_002).

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
        "outcome_note": "T003: lightning_export.read_runs reads each attempt of the named runs through the SPEC-074 adapter (rollout_triplets), joins task and group ids from the content-free rollout records, and yields one item per model call with its turn index and the adapter's attempt-<hmac16> pseudonym; select keeps the exportable items in order and counts every other one under exactly one reason. In a temporary store with one rollout of three model calls (full content, prompt only, no content) and consent redacted for rollout, one record is kept and two are counted content-missing; after lowering consent to none all three are consent-none; with consent redacted but only loom listed all three are no-consent. Kept plus excluded equals the model calls. Unit cases: a record that is not a triplet, has no redaction object, or has scanClean false or not true is unredacted; a missing prompt or response is content-missing; consent reasons win over content reasons; a gate refusal maps to its reason and an unknown one fails closed to no-consent. The raw attempt id never appears in items or selections; a missing run refuses with store-missing and a rollout without a rollout record with source-invalid, with fixed texts naming neither id and no chained cause. Negative control: classifying from the triplet's losses alone (without the gate refusal) reports an unlisted source as consent-none, which the no-consent test catches.",
        "limits": "Temporary homes and synthetic content; rollout source only (the export input is the run store; Loom, host transcript and System One adapters are not export inputs). Consent is profile-wide, so the mix of consent states is exercised across successive profiles on one store and by unit cases, not within one read. Retention, balance, overlong and the terms gate are later tasks (T007, T008, T013); no dataset or manifest is written yet (T004-T006).",
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
