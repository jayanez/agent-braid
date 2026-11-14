# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 (BL.5): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. procedure_001 is the T001 owner review record, not a test run, so it is not captured here.
Procedures are added as their tasks land (T002: procedure_005, schema part).

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
