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
        "outcome_note": "T002 part: schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json is a valid JSON Schema 2020-12 document (check_schema) and accepts a valid rollout manifest at both levels, a supervised manifest and a host-model manifest with a terms decision. It refuses a manifest missing a record sha256 or redactionVersion (or with an empty one), missing any top-level or record field, with an unknown key, version, kind, level, ordering key, canary result, exclusion reason or negative count, source, outcome, limit, consent level other than redacted, a raw (non-pseudonym) attempt id, a malformed digest, record id, turn range or timestamp, no records, retention outside 1-90 days or an unsafe run id, a supervised export that is balanced or carries a balance report, and host-model records without a terms decision.",
        "limits": "Schema structure only: hand-written manifests, no export ran (the builder and its byte checks are T006, which extends this procedure). The schema cannot check that hashes match the bytes they cover or that limits are sorted; the builder does. jsonschema is a development dependency; the runtime stays standard-library only.",
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
