# SPDX-License-Identifier: AGPL-3.0-only
"""Validate metadata-only M3.5 registration and chained remote seals."""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess


FORMAT = "m35-seal-v1"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REASONS = {"insufficient-proposals", "session-not-closed", "dependent-observation", "missing-receipt",
           "missing-provenance", "invalid-base", "unsupported-operation", "invalid-anchor",
           "outside-model-contract", "base-mismatch", "same-actor", "no-candidate-pair"}


def _utc(value: object) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("seal timestamps must use UTC Z format")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid seal timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("seal timestamp is not UTC")
    return parsed


def _number(value: object) -> bool:
    return type(value) is int and value >= 0


def _reasons(value: object) -> bool:
    return (type(value) is dict and set(value) <= REASONS
            and all(_number(count) for count in value.values()))


def validate_payload(value: object) -> dict:
    if type(value) is not dict or value.get("format") != FORMAT or value.get("mode") not in {
            "register", "daily", "final"}:
        raise ValueError("invalid seal format or mode")
    common = {"format", "mode", "windowId", "familyId", "startUtc", "endUtc", "protocolCommit"}
    if any(type(value.get(key)) is not str or SAFE_ID.fullmatch(value[key]) is None
           for key in ("windowId", "familyId")):
        raise ValueError("invalid seal identity")
    start, end = _utc(value.get("startUtc")), _utc(value.get("endUtc"))
    if start.hour or start.minute or start.second or start.microsecond or end - start != timedelta(days=14):
        raise ValueError("seal window must be exactly 14 UTC days")
    if type(value.get("protocolCommit")) is not str or HEX40.fullmatch(value["protocolCommit"]) is None:
        raise ValueError("invalid protocol commit")
    mode = value["mode"]
    if mode == "register":
        if set(value) != common:
            raise ValueError("invalid registration fields")
    else:
        required = common | {"registrationRunId", "previousRunId", "dayIndex", "eventCount",
                             "sessionCount", "journalCommitment"}
        if mode == "final":
            required |= {"pairsExamined", "pairsStructurallyAdmitted",
                         "sessionsExcludedByReason", "pairsExcludedByReason", "reportCommitment"}
        if set(value) != required:
            raise ValueError("invalid checkpoint fields")
        if (type(value["registrationRunId"]) is not int or value["registrationRunId"] <= 0
                or type(value["previousRunId"]) is not int or value["previousRunId"] <= 0
                or type(value["dayIndex"]) is not int or not 1 <= value["dayIndex"] <= 14
                or any(not _number(value[key]) for key in ("eventCount", "sessionCount"))
                or type(value["journalCommitment"]) is not str
                or HEX64.fullmatch(value["journalCommitment"]) is None):
            raise ValueError("invalid checkpoint counts or commitment")
        if mode == "final":
            if (value["dayIndex"] != 14
                    or any(not _number(value[key]) for key in (
                        "pairsExamined", "pairsStructurallyAdmitted"))
                    or value["pairsStructurallyAdmitted"] > value["pairsExamined"]
                    or not _reasons(value["sessionsExcludedByReason"])
                    or not _reasons(value["pairsExcludedByReason"])
                    or sum(value["pairsExcludedByReason"].values()) != (
                        value["pairsExamined"] - value["pairsStructurallyAdmitted"])
                    or type(value["reportCommitment"]) is not str
                    or HEX64.fullmatch(value["reportCommitment"]) is None):
                raise ValueError("invalid final aggregate or commitment")
    return value


def validate_link(current: dict, previous: dict | None, previous_run_id: int | None,
                  *, now: datetime | None = None) -> None:
    validate_payload(current)
    if current["mode"] == "register":
        if previous is not None:
            raise ValueError("registration cannot link to an earlier seal")
        if _utc(current["startUtc"]) < (now or datetime.now(timezone.utc)) + timedelta(hours=24):
            raise ValueError("registration must precede capture by at least 24 hours")
        return
    if previous is None or previous_run_id != current["previousRunId"]:
        raise ValueError("missing or mismatched predecessor")
    validate_payload(previous)
    if any(current[key] != previous[key] for key in (
            "windowId", "familyId", "startUtc", "endUtc", "protocolCommit")):
        raise ValueError("checkpoint changed the frozen source identity")
    instant = now or datetime.now(timezone.utc)
    cutoff = _utc(current["startUtc"]) + timedelta(days=current["dayIndex"])
    if instant < cutoff:
        raise ValueError("checkpoint was submitted before the completed UTC day")
    if current["mode"] == "daily" and current["dayIndex"] == 1:
        if previous["mode"] != "register" or current["registrationRunId"] != previous_run_id:
            raise ValueError("first daily seal must link to its registration")
    elif current["mode"] == "daily":
        if (previous["mode"] != "daily" or previous["dayIndex"] != current["dayIndex"] - 1
                or current["registrationRunId"] != previous["registrationRunId"]):
            raise ValueError("daily seal skips or changes its predecessor")
    elif (previous["mode"] != "daily" or previous["dayIndex"] != 14
          or current["registrationRunId"] != previous["registrationRunId"]
          or current["journalCommitment"] != previous["journalCommitment"]):
        raise ValueError("final seal does not close day 14")
    if previous["mode"] != "register":
        if (current["eventCount"] < previous["eventCount"]
                or current["sessionCount"] < previous["sessionCount"]):
            raise ValueError("cumulative counts decreased")
        if current["mode"] == "final" and (
                current["eventCount"] != previous["eventCount"]
                or current["sessionCount"] != previous["sessionCount"]):
            raise ValueError("final counts differ from the last daily seal")


def verify_previous_run(repository: str, run_id: int) -> None:
    """Check that the previous artifact came from an executed successful job."""
    for endpoint in (f"repos/{repository}/actions/runs/{run_id}",
                     f"repos/{repository}/actions/runs/{run_id}/jobs"):
        result = subprocess.run(["gh", "api", endpoint], check=True,
                                capture_output=True, text=True)
        data = json.loads(result.stdout)
        if endpoint.endswith("/jobs"):
            if not any(job.get("conclusion") == "success" and job.get("runner_name")
                       and job.get("steps") for job in data.get("jobs", [])):
                raise ValueError("predecessor had no executed successful job")
        elif (data.get("status") != "completed" or data.get("conclusion") != "success"
              or data.get("event") != "workflow_dispatch"
              or not str(data.get("path", "")).split("@", 1)[0].endswith(".github/workflows/m35-seal.yml")
              or data.get("head_branch") != "main"
              or data.get("head_repository", {}).get("full_name") != repository):
            raise ValueError("predecessor workflow is not a successful seal")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = os.environ.get("M35_SEAL_PAYLOAD", "")
    if not raw or len(raw) > 4096:
        raise ValueError("seal payload is missing or too large")
    current = json.loads(raw)
    previous = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous else None
    run_id = current.get("previousRunId") if type(current) is dict else None
    validate_link(current, previous, run_id)
    if run_id is not None:
        repository = os.environ.get("GITHUB_REPOSITORY", "")
        if not repository:
            raise ValueError("GitHub repository identity is missing")
        verify_previous_run(repository, run_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(current, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"mode": current["mode"], "windowId": current["windowId"],
                      "dayIndex": current.get("dayIndex")}, sort_keys=True))


if __name__ == "__main__":
    main()
