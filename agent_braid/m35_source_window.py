# SPDX-License-Identifier: AGPL-3.0-only
"""Local, opt-in source capture for the bounded M3.5 feasibility pilot.

The writer controls its own admission boundary. A hash chain detects changes
after a recorded commitment, but does not authenticate actors or prove that
work outside this interface did not occur.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import fcntl
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import re
from typing import Any, Iterator
from uuid import uuid4

from agent_braid.structured_exchange import InvalidExchange, VERSION, validate_request


WINDOW_FORMAT = "m35-source-window-v1"
EVENT_FORMAT = "m35-source-event-v1"
REPORT_FORMAT = "m35-source-feasibility-report-v2"
LAB_REF = re.compile(r"^[0-9a-f]{40}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def utc(value: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("timestamps must use UTC with a Z suffix")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    if result.utcoffset() != timedelta(0):
        raise ValueError("timestamp is not UTC")
    return result


def timestamp(moment: datetime | None = None) -> str:
    moment = moment or datetime.now(timezone.utc)
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_window(value: Any) -> dict:
    required = {"format", "sourceKind", "windowId", "familyId", "startUtc", "endUtc",
                "registrationRunId", "protocolCommit"}
    if type(value) is not dict or set(value) != required or value.get("format") != WINDOW_FORMAT:
        raise ValueError("invalid source window manifest")
    if value["sourceKind"] not in ("synthetic", "prospective"):
        raise ValueError("invalid source kind")
    if any(type(value[key]) is not str or SAFE_ID.fullmatch(value[key]) is None
           for key in ("windowId", "familyId")):
        raise ValueError("invalid window or family ID")
    start, end = utc(value["startUtc"]), utc(value["endUtc"])
    if start.hour or start.minute or start.second or start.microsecond or end - start != timedelta(days=14):
        raise ValueError("window must start at 00:00 UTC and last exactly 14 days")
    if type(value["protocolCommit"]) is not str or LAB_REF.fullmatch(value["protocolCommit"]) is None:
        raise ValueError("protocolCommit must be a full Git commit SHA")
    run = value["registrationRunId"]
    if value["sourceKind"] == "prospective":
        if type(run) is not int or run <= 0:
            raise ValueError("prospective capture needs an executed registration run")
    elif run is not None:
        raise ValueError("synthetic windows have no registration run")
    return value


def _private_file(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def create_window(directory: Path, manifest: dict, *, registration_verified: bool = False,
                  permission_reviewed: bool = False) -> None:
    """Create a private source directory; prospective gates are explicit."""
    validate_window(manifest)
    if manifest["sourceKind"] == "prospective" and not (registration_verified and permission_reviewed):
        raise ValueError("prospective capture requires remote registration and local permission review")
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    try:
        _private_file(directory / "window.json", canonical(manifest) + b"\n")
        _private_file(directory / "events.jsonl", b"")
        _private_file(directory / "admissions.jsonl", b"")
        _private_file(directory / "secret", os.urandom(32))
        _private_file(directory / "capture.lock", b"")
    except BaseException:
        # An incomplete directory is conspicuous and must be inspected, not reused.
        raise


@contextmanager
def locked(directory: Path, *, shared: bool = False) -> Iterator[None]:
    descriptor = os.open(directory / "capture.lock", os.O_RDONLY)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_SH if shared else fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _lines(path: Path) -> list[dict]:
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise ValueError(f"{path.name} ends with an incomplete record")
    records = []
    for line in raw.splitlines():
        try:
            record = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name} contains malformed JSON") from exc
        if type(record) is not dict or canonical(record) != line:
            raise ValueError(f"{path.name} contains a noncanonical record")
        records.append(record)
    return records


def _append(path: Path, record: dict) -> None:
    raw = canonical(record) + b"\n"
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        raise


def _load(directory: Path) -> tuple[dict, list[dict], list[dict]]:
    manifest_raw = (directory / "window.json").read_bytes()
    if not manifest_raw.endswith(b"\n") or manifest_raw.count(b"\n") != 1:
        raise ValueError("window manifest is malformed")
    manifest = json.loads(manifest_raw)
    if canonical(manifest) + b"\n" != manifest_raw:
        raise ValueError("window manifest is not canonical")
    validate_window(manifest)
    events = _lines(directory / "events.jsonl")
    admissions = _lines(directory / "admissions.jsonl")
    previous = None
    seen_events: set[str] = set()
    allowed_kinds = {"session-open", "base-seen", "proposal", "external-observation",
                     "proposals-seen", "session-close"}
    last_when: datetime | None = None
    for index, event in enumerate(events):
        required = {"format", "sequence", "eventId", "timestampUtc", "kind", "sessionId",
                    "data", "previousHash", "eventHash"}
        if type(event) is not dict or set(event) != required or event["format"] != EVENT_FORMAT:
            raise ValueError("invalid event shape")
        if type(event["sequence"]) is not int or event["sequence"] != index:
            raise ValueError("event sequence gap or reordering")
        if type(event["eventId"]) is not str or event["eventId"] in seen_events:
            raise ValueError("duplicate or missing event ID")
        seen_events.add(event["eventId"])
        if event["kind"] not in allowed_kinds:
            raise ValueError("unknown event kind")
        when = utc(event["timestampUtc"])
        if not utc(manifest["startUtc"]) <= when < utc(manifest["endUtc"]):
            raise ValueError("event falls outside the frozen window")
        if last_when is not None and when < last_when:
            raise ValueError("event timestamps are not monotonic")
        last_when = when
        if type(event["sessionId"]) is not str or not event["sessionId"] or type(event["data"]) is not dict:
            raise ValueError("invalid event identity or data")
        body = {key: val for key, val in event.items() if key != "eventHash"}
        if event["previousHash"] != previous or event["eventHash"] != digest(body):
            raise ValueError("event hash chain is broken")
        previous = event["eventHash"]
    opens = [event for event in events if event["kind"] == "session-open"]
    if len(opens) != len(admissions):
        raise ValueError("admission ledger and session opens disagree")
    for admission, opened in zip(admissions, opens):
        if set(admission) != {"sessionId", "eventId", "timestampUtc"} or admission != {
            "sessionId": opened["sessionId"], "eventId": opened["eventId"],
            "timestampUtc": opened["timestampUtc"]}:
            raise ValueError("admission ledger and session opens disagree")
    if len({item["sessionId"] for item in admissions}) != len(admissions):
        raise ValueError("duplicate admitted session")
    admitted_ids = {item["sessionId"] for item in admissions}
    if any(event["sessionId"] not in admitted_ids for event in events):
        raise ValueError("event for a session outside the admission register")
    return manifest, events, admissions


def _record(directory: Path, kind: str, session_id: str, data: dict,
            now: datetime | None = None) -> dict:
    manifest, events, _ = _load(directory)
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None or moment.utcoffset() != timedelta(0):
        raise ValueError("capture clock must be UTC aware")
    if not utc(manifest["startUtc"]) <= moment < utc(manifest["endUtc"]):
        raise ValueError("capture is outside the frozen window")
    if events and moment < utc(events[-1]["timestampUtc"]):
        raise ValueError("capture clock moved behind the last event")
    body = {"format": EVENT_FORMAT, "sequence": len(events), "eventId": uuid4().hex,
            "timestampUtc": timestamp(moment), "kind": kind, "sessionId": session_id,
            "data": data, "previousHash": events[-1]["eventHash"] if events else None}
    record = {**body, "eventHash": digest(body)}
    if kind == "session-open":
        _append(directory / "admissions.jsonl", {"sessionId": session_id, "eventId": record["eventId"],
                                                     "timestampUtc": record["timestampUtc"]})
    _append(directory / "events.jsonl", record)
    return record


def _session(events: list[dict], session_id: str) -> list[dict]:
    records = [event for event in events if event["sessionId"] == session_id]
    if not records or records[0]["kind"] != "session-open":
        raise ValueError("unknown session")
    if any(event["kind"] == "session-close" for event in records):
        raise ValueError("session is already closed")
    return records


def open_session(directory: Path, session_id: str, participants: list[str], base: Any,
                 context_sha: str, source_ref: str, *, now: datetime | None = None) -> dict:
    with locked(directory):
        _, events, _ = _load(directory)
        if type(session_id) is not str or SAFE_ID.fullmatch(session_id) is None:
            raise ValueError("invalid session ID")
        if any(event["sessionId"] == session_id for event in events):
            raise ValueError("duplicate session ID")
        if (type(participants) is not list or len(participants) < 1 or
                any(type(actor) is not str or SAFE_ID.fullmatch(actor) is None for actor in participants) or
                len(set(participants)) != len(participants)):
            raise ValueError("participants must be distinct pseudonyms")
        if type(context_sha) is not str or LAB_REF.fullmatch(context_sha) is None:
            raise ValueError("context SHA must identify a lab snapshot")
        return _record(directory, "session-open", session_id,
                       {"participants": participants, "base": base, "contextSha": context_sha,
                        "sourceRef": source_ref}, now)


def view_base(directory: Path, session_id: str, actor_id: str,
              *, now: datetime | None = None) -> dict:
    with locked(directory):
        _, events, _ = _load(directory)
        records = _session(events, session_id)
        opened = records[0]
        if actor_id not in opened["data"].get("participants", []):
            raise ValueError("actor is not registered for the session")
        if any(item["kind"] == "proposal" and item["data"].get("actorId") == actor_id for item in records):
            raise ValueError("actor has already submitted a proposal")
        receipt = _record(directory, "base-seen", session_id,
                          {"actorId": actor_id, "baseEventId": opened["eventId"]}, now)
        return {"receiptId": receipt["eventId"], "baseEventId": opened["eventId"],
                "base": opened["data"]["base"]}


def propose(directory: Path, session_id: str, actor_id: str, operation: Any,
            source_ref: str, *, now: datetime | None = None) -> dict:
    with locked(directory):
        _, events, _ = _load(directory)
        records = _session(events, session_id)
        opened = records[0]
        if actor_id not in opened["data"].get("participants", []):
            raise ValueError("actor is not registered for the session")
        if any(item["kind"] == "proposal" and item["data"].get("actorId") == actor_id for item in records):
            raise ValueError("actor already submitted an action")
        if not any(item["kind"] == "base-seen" and item["data"].get("actorId") == actor_id
                   and item["data"].get("baseEventId") == opened["eventId"] for item in records):
            raise ValueError("actor must view the base through the interface first")
        if type(operation) is not dict:
            raise ValueError("operation must be an object")
        return _record(directory, "proposal", session_id,
                       {"actorId": actor_id, "baseEventId": opened["eventId"],
                        "operation": operation, "sourceRef": source_ref}, now)


def mark_external_observation(directory: Path, session_id: str, actor_id: str,
                              *, now: datetime | None = None) -> dict:
    """Record that the actor may have seen another proposal outside the wrapper."""
    with locked(directory):
        _, events, _ = _load(directory)
        records = _session(events, session_id)
        if actor_id not in records[0]["data"].get("participants", []):
            raise ValueError("actor is not registered for the session")
        return _record(directory, "external-observation", session_id, {"actorId": actor_id}, now)


def reveal(directory: Path, session_id: str, actor_id: str,
           *, now: datetime | None = None) -> list[dict]:
    with locked(directory):
        _, events, _ = _load(directory)
        records = _session(events, session_id)
        participants = records[0]["data"].get("participants", [])
        if actor_id not in participants:
            raise ValueError("actor is not registered for the session")
        proposals = [item for item in records if item["kind"] == "proposal"]
        if len(proposals) != len(participants):
            raise ValueError("proposals stay hidden until every participant submits")
        _record(directory, "proposals-seen", session_id, {"actorId": actor_id}, now)
        return [{"actorId": item["data"]["actorId"], "operation": item["data"]["operation"]}
                for item in proposals]


def close_session(directory: Path, session_id: str, outcome: str,
                  *, now: datetime | None = None) -> dict:
    with locked(directory):
        _, events, _ = _load(directory)
        _session(events, session_id)
        if type(outcome) is not str or outcome not in {"accepted", "rejected", "cancelled", "unresolved"}:
            raise ValueError("invalid session outcome")
        return _record(directory, "session-close", session_id, {"outcome": outcome}, now)


def _pair_reason(opened: dict, first: dict, second: dict, records: list[dict]) -> str | None:
    if first["data"].get("actorId") == second["data"].get("actorId"):
        return "same-actor"
    if (first["data"].get("baseEventId") != opened["eventId"] or
            second["data"].get("baseEventId") != opened["eventId"]):
        return "base-mismatch"
    for proposal in (first, second):
        actor = proposal["data"]["actorId"]
        if any(item["kind"] in {"external-observation", "proposals-seen"}
               and item["data"].get("actorId") == actor
               and item["sequence"] < proposal["sequence"] for item in records):
            return "dependent-observation"
        if not any(item["kind"] == "base-seen" and item["data"].get("actorId") == actor
                   and item["data"].get("baseEventId") == opened["eventId"]
                   and item["sequence"] < proposal["sequence"] for item in records):
            return "missing-receipt"
    if any(type(value) is not str or not value for value in (
            opened["data"].get("sourceRef"), opened["data"].get("contextSha"),
            first["data"].get("sourceRef"), second["data"].get("sourceRef"))):
        return "missing-provenance"
    base = opened["data"].get("base")
    if type(base) is not list or len(base) > 3:
        return "invalid-base"
    operations = [first["data"].get("operation"), second["data"].get("operation")]
    if any(type(op) is not dict or op.get("kind") != "insert" for op in operations):
        return "unsupported-operation"
    try:
        validate_request({"model": VERSION, "base": base, "operations": operations})
    except InvalidExchange as exc:
        return "invalid-anchor" if "anchor" in str(exc) else "outside-model-contract"
    return None


def audit_window(directory: Path) -> dict:
    with locked(directory, shared=True):
        manifest, events, admissions = _load(directory)
        grouped: dict[str, list[dict]] = defaultdict(list)
        for event in events:
            grouped[event["sessionId"]].append(event)
        session_reasons: Counter[str] = Counter()
        pair_reasons: Counter[str] = Counter()
        sessions_admitted = pairs_examined = pairs_structural = 0
        for session_id in [entry["sessionId"] for entry in admissions]:
            records = grouped[session_id]
            opened = records[0]
            if opened["kind"] != "session-open" or sum(item["kind"] == "session-open" for item in records) != 1:
                raise ValueError("invalid session-open ordering")
            if (sum(item["kind"] == "session-close" for item in records) > 1 or
                    any(item["kind"] == "session-close" for item in records[:-1])):
                raise ValueError("invalid session-close ordering")
            proposals = [item for item in records if item["kind"] == "proposal"]
            actors = [item["data"].get("actorId") for item in proposals]
            if len(set(actors)) != len(actors):
                raise ValueError("actor submitted multiple proposals")
            if len(proposals) < 2:
                session_reasons["insufficient-proposals"] += 1
                continue
            admitted = 0
            reasons = []
            for left in range(len(proposals)):
                for right in range(left + 1, len(proposals)):
                    pairs_examined += 1
                    reason = _pair_reason(opened, proposals[left], proposals[right], records)
                    if reason is None:
                        admitted += 1
                        pairs_structural += 1
                    else:
                        pair_reasons[reason] += 1
                        reasons.append(reason)
            if admitted:
                sessions_admitted += 1
            else:
                session_reasons[sorted(reasons)[0] if reasons else "no-candidate-pair"] += 1
        raw_events = (directory / "events.jsonl").read_bytes()
        raw_admissions = (directory / "admissions.jsonl").read_bytes()
        return {"format": REPORT_FORMAT, "sourceKind": manifest["sourceKind"],
                "evidenceClass": "synthetic-rehearsal" if manifest["sourceKind"] == "synthetic"
                else "prospective-provisional",
                "windowId": manifest["windowId"], "familyId": manifest["familyId"],
                "window": {"startUtc": manifest["startUtc"], "endUtc": manifest["endUtc"]},
                "journalSha256": sha256(raw_events).hexdigest(),
                "admissionSha256": sha256(raw_admissions).hexdigest(),
                "eventsObserved": len(events), "sessionsExamined": len(admissions),
                "sessionsAdmitted": sessions_admitted,
                "sessionsExcludedByReason": dict(sorted(session_reasons.items())),
                "pairsExamined": pairs_examined, "pairsStructurallyAdmitted": pairs_structural,
                "pairsExcludedByReason": dict(sorted(pair_reasons.items())),
                "realPairsAdmitted": 0, "executionAuthorization": False}


def seal_payload(directory: Path, day_index: int, *, now: datetime | None = None) -> dict:
    """Return only an opaque prefix commitment and aggregate counters."""
    if type(day_index) is not int or not 1 <= day_index <= 14:
        raise ValueError("day index must be 1..14")
    with locked(directory, shared=True):
        manifest, events, admissions = _load(directory)
        cutoff = utc(manifest["startUtc"]) + timedelta(days=day_index)
        if manifest["sourceKind"] == "prospective" and (now or datetime.now(timezone.utc)) < cutoff:
            raise ValueError("cannot seal a prospective day before it ends")
        prefix_events = [event for event in events if utc(event["timestampUtc"]) < cutoff]
        prefix_admissions = [item for item in admissions if utc(item["timestampUtc"]) < cutoff]
        payload = (canonical(manifest) + b"\n" + b"".join(canonical(item) + b"\n" for item in prefix_events)
                   + b"\0" + b"".join(canonical(item) + b"\n" for item in prefix_admissions))
        commitment = hmac.new((directory / "secret").read_bytes(), payload, sha256).hexdigest()
        return {"format": "m35-seal-v1", "mode": "daily", "windowId": manifest["windowId"],
                "familyId": manifest["familyId"], "registrationRunId": manifest["registrationRunId"],
                "startUtc": manifest["startUtc"], "endUtc": manifest["endUtc"],
                "protocolCommit": manifest["protocolCommit"],
                "dayIndex": day_index, "eventCount": len(prefix_events),
                "sessionCount": len(prefix_admissions), "journalCommitment": commitment}


def final_seal_payload(directory: Path, *, now: datetime | None = None) -> dict:
    """Commit to the final private report without publishing its source text."""
    with locked(directory, shared=True):
        manifest, _, _ = _load(directory)
        if manifest["sourceKind"] == "prospective" and (now or datetime.now(timezone.utc)) < utc(manifest["endUtc"]):
            raise ValueError("cannot finalize an unfinished prospective window")
    report = audit_window(directory)
    daily = seal_payload(directory, 14, now=now)
    report_commitment = hmac.new((directory / "secret").read_bytes(), canonical(report), sha256).hexdigest()
    return {"format": "m35-seal-v1", "mode": "final", "windowId": manifest["windowId"],
            "familyId": manifest["familyId"], "registrationRunId": manifest["registrationRunId"],
            "startUtc": manifest["startUtc"], "endUtc": manifest["endUtc"],
            "protocolCommit": manifest["protocolCommit"],
            "dayIndex": 14, "eventCount": report["eventsObserved"],
            "sessionCount": report["sessionsExamined"],
            "pairsExamined": report["pairsExamined"],
            "pairsStructurallyAdmitted": report["pairsStructurallyAdmitted"],
            "sessionsExcludedByReason": report["sessionsExcludedByReason"],
            "pairsExcludedByReason": report["pairsExcludedByReason"],
            "journalCommitment": daily["journalCommitment"],
            "reportCommitment": report_commitment}
