#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate release validation records without inferring scientific approval."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "docs" / "releases" / "records"
STATUSES = {"pending", "completed", "not_applicable"}
MATURITIES = {"research-preview", "alpha", "beta", "stable"}
PROHIBITED_PENDING_PHRASES = (
    "independently validated",
    "independently reproduced",
    "external validation completed",
)


def _repository_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe repository file: {relative}")
    return path


def validate_record(record: dict, root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    required = {
        "recordVersion", "release", "softwareMaturity", "independent_validation",
        "internalEvidence", "limits",
    }
    if set(record) - (required | {"scientificOrBenchmarkClaims"}):
        failures.append("release record contains unexpected fields")
    if not required.issubset(record):
        failures.append("release record omits required fields")
        return failures
    if record["recordVersion"] != "0.2.0":
        failures.append("recordVersion must be 0.2.0")
    if not isinstance(record["release"], str) or not record["release"].strip():
        failures.append("release identifier is required")
    if record["softwareMaturity"] not in MATURITIES:
        failures.append("softwareMaturity is invalid")
    if not isinstance(record["internalEvidence"], list) or not record["internalEvidence"]:
        failures.append("internal evidence references are required")
    else:
        for relative in record["internalEvidence"]:
            try:
                _repository_file(root, relative)
            except (TypeError, ValueError) as exc:
                failures.append(str(exc))
    if not isinstance(record["limits"], list) or not record["limits"]:
        failures.append("release limits are required")

    validation = record["independent_validation"]
    if not isinstance(validation, dict) or validation.get("status") not in STATUSES:
        failures.append("independent_validation status is invalid or missing")
        return failures
    status = validation["status"]
    if status == "pending":
        for field in ("conflictOfInterest", "reproductionProtocol", "invitation"):
            if not isinstance(validation.get(field), str) or not validation[field].strip():
                failures.append(f"pending validation requires {field}")
        protocol = validation.get("reproductionProtocol")
        if isinstance(protocol, str) and protocol:
            try:
                _repository_file(root, protocol)
            except ValueError as exc:
                failures.append(str(exc))
        searchable = json.dumps(record).lower()
        for phrase in PROHIBITED_PENDING_PHRASES:
            if phrase in searchable:
                failures.append(f"pending record claims {phrase}")
    elif status == "completed":
        reviewer = validation.get("reviewer")
        reviewer_fields = {"name", "affiliation", "external", "conflictOfInterest"}
        if not isinstance(reviewer, dict) or set(reviewer) != reviewer_fields:
            failures.append("completed validation requires an identified external reviewer")
        else:
            for field in reviewer_fields - {"external"}:
                if not isinstance(reviewer[field], str) or not reviewer[field].strip():
                    failures.append(f"completed validation reviewer requires {field}")
            if reviewer["external"] is not True:
                failures.append("completed validation reviewer must be external")
        if not isinstance(validation.get("evidence"), str) \
                or not validation["evidence"].strip():
            failures.append("completed validation requires evidence")
        evidence = validation.get("evidence")
        if isinstance(evidence, str) and evidence:
            try:
                _repository_file(root, evidence)
            except ValueError as exc:
                failures.append(str(exc))
    elif status == "not_applicable":
        if record.get("scientificOrBenchmarkClaims") is not False:
            failures.append("not_applicable requires scientificOrBenchmarkClaims false")
        if not isinstance(validation.get("rationale"), str) or not validation["rationale"].strip():
            failures.append("not_applicable requires a rationale")
    return failures


def validate_all(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    records = root / "docs" / "releases" / "records"
    if not records.exists():
        return failures
    for path in sorted(records.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            failures.extend(f"{path.name}: {item}" for item in validate_record(record, root))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"{path.name}: invalid JSON: {exc}")
    return failures


def main() -> int:
    failures = validate_all()
    if failures:
        print("Release validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Release records passed structural validation; no scientific approval inferred.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
