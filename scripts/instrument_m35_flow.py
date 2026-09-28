# SPDX-License-Identifier: AGPL-3.0-only
"""Capture and audit a synthetic anchored-sequence editing flow.

This is a source-feasibility instrument, not a real-workload dataset or predictor.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from agent_braid.structured_exchange import InvalidExchange, VERSION, validate_request


FORMAT = "m35-capture-event-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def capture_synthetic(source: Path, output: Path) -> dict:
    """Write a new event log exclusively; never overwrite an earlier capture."""
    sessions = json.loads(source.read_text(encoding="utf-8"))
    if type(sessions) is not list:
        raise ValueError("source must be a list of synthetic sessions")
    events: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for session in sessions:
        if type(session) is not dict or session.get("sourceKind") != "synthetic":
            raise ValueError("capture accepts synthetic sessions only")
        required = {"sourceKind", "familyId", "sessionId", "baseEventId", "base", "events", "sourceRef"}
        if set(session) != required or type(session["events"]) is not list:
            raise ValueError("session envelope is incomplete")
        common = {"format": FORMAT, "sourceKind": "synthetic",
                  "familyId": session["familyId"], "sessionId": session["sessionId"]}
        base = {**common, "eventType": "base", "eventId": session["baseEventId"],
                "sourceRef": session["sourceRef"], "base": session["base"]}
        records = [base]
        for item in session["events"]:
            if type(item) is not dict or set(item) != {"eventId", "sourceRef", "operation"}:
                raise ValueError("operation event envelope is incomplete")
            records.append({**common, "eventType": "operation", "eventId": item["eventId"],
                            "baseEventId": session["baseEventId"], "sourceRef": item["sourceRef"],
                            "operation": item["operation"]})
        for record in records:
            key = (str(record["sessionId"]), str(record["eventId"]))
            if key in seen:
                raise ValueError("duplicate event id within session")
            seen.add(key)
        events.extend(records)
    payload = "".join(_canonical(event) + "\n" for event in events)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return {"format": FORMAT, "sourceKind": "synthetic", "eventsWritten": len(events),
            "sha256": sha256(payload.encode("utf-8")).hexdigest()}


def _reason(base: dict, operations: list[dict]) -> str | None:
    if any(type(record.get("sourceRef")) is not str or not record["sourceRef"] for record in [base, *operations]):
        return "missing-provenance"
    if type(base.get("base")) is not list or len(base["base"]) > 3:
        return "invalid-base"
    if any(type(record.get("operation")) is not dict or record["operation"].get("kind") != "insert"
           for record in operations):
        return "unsupported-operation"
    request = {"model": VERSION, "base": base["base"],
               "operations": [record["operation"] for record in operations]}
    try:
        validate_request(request)
    except InvalidExchange as exc:
        return "invalid-anchor" if "anchor" in str(exc) else "outside-model-contract"
    return None


def audit_capture(path: Path) -> dict:
    payload = path.read_bytes()
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for line in payload.decode("utf-8").splitlines():
        record = json.loads(line)
        if type(record) is not dict or record.get("format") != FORMAT or record.get("sourceKind") != "synthetic":
            raise ValueError("invalid synthetic capture record")
        family, session, event = record.get("familyId"), record.get("sessionId"), record.get("eventId")
        if not all(type(value) is str and value for value in (family, session, event)):
            raise ValueError("missing capture identity")
        key = (session, event)
        if key in seen:
            raise ValueError("duplicate event id within session")
        seen.add(key)
        grouped[(family, session)].append(record)

    session_reasons: Counter[str] = Counter()
    pair_reasons: Counter[str] = Counter()
    sessions_admitted = pairs_admitted = pairs_examined = 0
    for records in grouped.values():
        bases = [record for record in records if record.get("eventType") == "base"]
        operations = [record for record in records if record.get("eventType") == "operation"]
        if len(bases) != 1 or len(operations) != 2 or len(records) != 3:
            session_reasons["incomplete-session"] += 1
            continue
        base = bases[0]
        pairs_examined += 1
        if any(record.get("baseEventId") != base["eventId"] for record in operations):
            reason = "base-mismatch"
        else:
            reason = _reason(base, operations)
        if reason:
            session_reasons[reason] += 1
            pair_reasons[reason] += 1
        else:
            sessions_admitted += 1
            pairs_admitted += 1
    return {"format": "m35-source-feasibility-report-v1", "sourceKind": "synthetic",
            "evidenceClass": "synthetic-adapter-demonstration",
            "captureSha256": sha256(payload).hexdigest(),
            "sessionsExamined": len(grouped), "sessionsAdmitted": sessions_admitted,
            "sessionsExcludedByReason": dict(sorted(session_reasons.items())),
            "pairsExamined": pairs_examined, "pairsAdmitted": pairs_admitted,
            "pairsExcludedByReason": dict(sorted(pair_reasons.items())),
            "realPairsAdmitted": 0, "executionAuthorization": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("source", type=Path)
    capture.add_argument("output", type=Path)
    audit = commands.add_parser("audit")
    audit.add_argument("capture", type=Path)
    audit.add_argument("--output", type=Path, help="write a new report without overwriting")
    args = parser.parse_args()
    result = (capture_synthetic(args.source, args.output) if args.command == "capture"
              else audit_capture(args.capture))
    if args.command == "audit" and args.output is not None:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(_canonical(result))


if __name__ == "__main__":
    main()
