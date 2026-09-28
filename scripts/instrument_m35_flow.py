# SPDX-License-Identifier: AGPL-3.0-only
"""Capture and audit a synthetic anchored-sequence editing flow.

The event hash chain detects accidental changes and omissions. It is not a
digital signature: an editor able to rewrite the capture can recompute it.
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
MANIFEST_FORMAT = "m35-capture-manifest-v1"
SOURCE_FORMAT = "m35-synthetic-window-v1"


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Any) -> str:
    return sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sequence(value: Any) -> bool:
    return type(value) is int and value >= 0


def capture_synthetic(source: Path, output: Path) -> dict:
    """Write a new synthetic window capture exclusively, never overwrite."""
    envelope = json.loads(source.read_text(encoding="utf-8"))
    if (type(envelope) is not dict or set(envelope) != {"format", "window", "sessions"}
            or envelope.get("format") != SOURCE_FORMAT):
        raise ValueError("source must be an m35-synthetic-window-v1 envelope")
    window = envelope["window"]
    if (type(window) is not dict or set(window) != {"startSequence", "endSequence"}
            or not _sequence(window.get("startSequence")) or not _sequence(window.get("endSequence"))
            or window["endSequence"] < window["startSequence"]):
        raise ValueError("source window bounds are malformed")
    if type(envelope["sessions"]) is not list:
        raise ValueError("source sessions must be a list")

    events: list[dict] = []
    seen_ids: set[str] = set()
    seen_sessions: set[str] = set()
    source_sequences: list[int] = []
    for session in envelope["sessions"]:
        if type(session) is not dict or session.get("sourceKind") != "synthetic":
            raise ValueError("capture accepts synthetic sessions only")
        required = {"sourceKind", "familyId", "sessionId", "baseEventId", "baseSequence",
                    "base", "events", "sourceRef"}
        if set(session) != required or type(session["events"]) is not list:
            raise ValueError("session envelope is incomplete")
        family, session_id = session["familyId"], session["sessionId"]
        if (type(family) is not str or not family or type(session_id) is not str or not session_id
                or session_id in seen_sessions):
            raise ValueError("missing or duplicate session identity")
        seen_sessions.add(session_id)
        if not _sequence(session["baseSequence"]):
            raise ValueError("baseSequence must be a nonnegative integer")
        common = {"format": FORMAT, "sourceKind": "synthetic", "familyId": family,
                  "sessionId": session_id}
        base = {**common, "eventType": "base", "eventId": session["baseEventId"],
                "sourceSequence": session["baseSequence"], "sourceRef": session["sourceRef"],
                "base": session["base"]}
        records = [base]
        for item in session["events"]:
            if (type(item) is not dict or set(item) != {
                    "eventId", "sourceRef", "sourceSequence", "baseEventId", "operation"}):
                raise ValueError("operation event envelope is incomplete")
            record = {**common, "eventType": "operation", "eventId": item["eventId"],
                      "sourceSequence": item["sourceSequence"],
                      "baseEventId": item["baseEventId"],
                      "sourceRef": item["sourceRef"], "operation": item["operation"]}
            records.append(record)
        for record in records:
            event_id = record["eventId"]
            if type(event_id) is not str or not event_id or event_id in seen_ids:
                raise ValueError("missing or duplicate event id")
            seen_ids.add(event_id)
            seq = record["sourceSequence"]
            if not _sequence(seq):
                raise ValueError("sourceSequence must be a nonnegative integer")
            source_sequences.append(seq)
        events.extend(records)

    start, end = window["startSequence"], window["endSequence"]
    expected = end - start + 1
    if len(events) != expected or source_sequences != list(range(start, end + 1)):
        raise ValueError("source events do not exactly cover the declared contiguous window in order")
    manifest = {"format": MANIFEST_FORMAT, "sourceKind": "synthetic",
                "windowStartSequence": start, "windowEndSequence": end,
                "expectedEventCount": expected}
    previous_hash: str | None = None
    lines = [_canonical(manifest)]
    for record in events:
        record["previousHash"] = previous_hash
        record["eventHash"] = _digest(record)
        previous_hash = record["eventHash"]
        lines.append(_canonical(record))
    payload = "\n".join(lines) + "\n"
    with output.open("x", encoding="utf-8") as stream:
        stream.write(payload)
    return {"format": MANIFEST_FORMAT, "sourceKind": "synthetic", "eventsWritten": len(events),
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
    """Fail closed on any manifest, sequence, identity, byte, or chain defect."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
        lines = text.splitlines()
        if not lines or not text.endswith("\n"):
            raise ValueError("capture must be nonempty newline-terminated JSONL")
        manifest = json.loads(lines[0])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("capture contains malformed UTF-8 or JSON") from exc
    if (type(manifest) is not dict or set(manifest) != {"format", "sourceKind", "windowStartSequence",
                                                        "windowEndSequence", "expectedEventCount"}
            or manifest.get("format") != MANIFEST_FORMAT or manifest.get("sourceKind") != "synthetic"):
        raise ValueError("invalid capture manifest")
    start, end = manifest["windowStartSequence"], manifest["windowEndSequence"]
    if not _sequence(start) or not _sequence(end) or end < start:
        raise ValueError("invalid manifest window")
    expected = end - start + 1
    if type(manifest["expectedEventCount"]) is not int or manifest["expectedEventCount"] != expected:
        raise ValueError("manifest expected event count does not match its window")
    event_lines = lines[1:]
    if len(event_lines) != expected:
        raise ValueError("capture dropped or added events relative to manifest")

    grouped: dict[str, list[dict]] = defaultdict(list)
    session_families: dict[str, str] = {}
    seen_ids: set[str] = set()
    previous_hash: str | None = None
    records: list[dict] = []
    required = {"format", "sourceKind", "familyId", "sessionId", "eventType", "eventId",
                "sourceSequence", "sourceRef", "previousHash", "eventHash"}
    for offset, line in enumerate(event_lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("capture contains malformed event JSON") from exc
        if type(record) is not dict or set(record) not in (required | {"base"}, required | {"operation", "baseEventId"}):
            raise ValueError("invalid capture event shape")
        expected_type = "base" if "base" in record else "operation"
        if record.get("eventType") != expected_type:
            raise ValueError("capture event type does not match its payload")
        if _canonical(record) != line:
            raise ValueError("capture event bytes are not canonical")
        if record.get("format") != FORMAT or record.get("sourceKind") != "synthetic":
            raise ValueError("capture accepts synthetic events only")
        family, session, event = record.get("familyId"), record.get("sessionId"), record.get("eventId")
        if not all(type(value) is str and value for value in (family, session, event)):
            raise ValueError("missing capture identity")
        if event in seen_ids:
            raise ValueError("duplicate event id")
        seen_ids.add(event)
        old_family = session_families.setdefault(session, family)
        if old_family != family:
            raise ValueError("inconsistent family for session")
        sequence = record.get("sourceSequence")
        if not _sequence(sequence) or sequence != start + offset:
            raise ValueError("sourceSequence is missing, out of order, or non-contiguous")
        event_hash = record.get("eventHash")
        body = {key: value for key, value in record.items() if key != "eventHash"}
        if record.get("previousHash") != previous_hash or type(event_hash) is not str or event_hash != _digest(body):
            raise ValueError("event hash chain is broken or event bytes changed")
        previous_hash = event_hash
        records.append(record)
        grouped[session].append(record)

    session_reasons: Counter[str] = Counter()
    pair_reasons: Counter[str] = Counter()
    sessions_admitted = pairs_admitted = pairs_examined = 0
    for session_records in grouped.values():
        bases = [record for record in session_records if record.get("eventType") == "base"]
        operations = [record for record in session_records if record.get("eventType") == "operation"]
        if len(bases) != 1 or len(operations) != 2 or len(session_records) != 3:
            raise ValueError("capture window contains an incomplete or duplicate session")
        base = bases[0]
        pairs_examined += 1
        if any(record["sourceSequence"] <= base["sourceSequence"] for record in operations):
            raise ValueError("base event must precede its operation events")
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
            "captureSha256": sha256(raw).hexdigest(),
            "window": {"startSequence": start, "endSequence": end},
            "expectedEvents": expected, "eventsObserved": len(records),
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
