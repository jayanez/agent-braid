#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Development-only structural and semantic contract corpus checks."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from jsonschema import Draft202012Validator
from research.lab.certificates import validate_aim_batch, verify
from research.lab.model import loads
from agent_braid.analysis import analyze


def check():
    validators = {}
    for path in sorted((ROOT / "schemas").rglob("*.json")):
        schema = loads(path.read_text())
        Draft202012Validator.check_schema(schema)
        validators[str(path.relative_to(ROOT / "schemas"))] = Draft202012Validator(schema)
    validators["agent-interaction-metadata.schema.json"].validate(
        loads((ROOT / "examples/aim/file-edits.json").read_text()))
    corpus = ROOT / "examples/contracts/0.2.0-draft"
    aim = loads((corpus / "aim.json").read_text())
    validators["0.2.0-draft/agent-interaction-metadata.schema.json"].validate(aim)
    validate_aim_batch([aim])
    for path in sorted((ROOT / "examples/workloads").glob("*.json")):
        operations = loads(path.read_text())
        for operation in operations:
            validators["0.2.0-draft/agent-interaction-metadata.schema.json"].validate(operation)
        validate_aim_batch(operations)
    report = analyze(loads((ROOT / "examples/analysis/file-edits.json").read_text()))
    validators["0.1.0-alpha/analysis-report.schema.json"].validate(report)
    expected = {"exhaustive": (True, "verified"), "replay": (True, "verified"),
                "proof-unverified": (True, "unverified"),
                "duplicate-schedule": (False, "rejected"),
                "level-five-replay": (False, "rejected")}
    validator = validators["0.2.0-draft/confluence-certificate.schema.json"]
    for path in sorted(corpus.glob("*.json")):
        if path.stem == "aim":
            continue
        bundle = loads(path.read_text())
        structural, semantic = expected.get(path.stem, (True, "rejected"))
        valid = not list(validator.iter_errors(bundle["certificate"]))
        if valid != structural:
            raise AssertionError(f"{path.name}: unexpected structural result {valid}")
        result = verify(bundle)
        if result["status"] != semantic:
            raise AssertionError(f"{path.name}: {result}")
    print("Contract corpus passed: legacy, 0.2 structure and finite semantic checks.")


if __name__ == "__main__":
    check()
