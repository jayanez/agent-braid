# SPDX-License-Identifier: AGPL-3.0-only
"""Local in-memory bridge from validated M3.5 events to SPEC-019 inputs.

This adapter does not read journals or sources. Its caller supplies event
records that were already validated. Returned request text is a private,
in-memory value for downstream use; callers must not publish or persist it.
SHA-256 IDs and commitments are deterministic and linkable, not confidential.
A sourceKind value and all ReviewedLocalGate declarations are caller claims.
Manifest agreement binds metadata but does not prove provenance, permission,
completeness, or authorization. No verifier, predictor, filesystem, network,
labels, outcomes, actors, source references, or context is emitted.
"""
from __future__ import annotations

from hashlib import sha256
import itertools
import json
from datetime import datetime, timedelta
from typing import Any

from agent_braid.native_predictor_training import FEATURE_VERSION, feature_vector
from agent_braid.m35_source_window import EVENT_FORMAT, validate_window
from agent_braid.structured_exchange import InvalidExchange, ROOT, VERSION, validate_request


class ReviewedLocalGate:
    """Caller declarations, not proof, permission, completeness, or authorization."""
    __slots__ = ("reviewed", "completeness_declared", "protocol_review_declared")

    def __init__(self, *, reviewed: bool = False, completeness_declared: bool = False,
                 protocol_review_declared: bool = False):
        self.reviewed = reviewed is True
        self.completeness_declared = completeness_declared is True
        self.protocol_review_declared = protocol_review_declared is True


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _fail() -> None:
    # Deliberately exclude raw source IDs and values from exception text.
    raise ValueError("invalid event records or adapter input")


def _feature_values(request: dict) -> dict:
    first, second = request["operations"]
    indices = {ROOT: -1} | {item["id"]: i for i, item in enumerate(request["base"])}
    left, right = set(first["value"].casefold().split()), set(second["value"].casefold().split())
    union = left | right
    values = {"baseSize": len(request["base"]),
              "sameAnchor": int(first["anchorId"] == second["anchorId"]),
              "anchorDistance": abs(indices[first["anchorId"]] - indices[second["anchorId"]]),
              "firstLength": len(first["value"]), "secondLength": len(second["value"]),
              "lexicalOverlap": len(left & right) / len(union) if union else 0.0}
    return values


def adapt(events: Any, *, source_kind: str, family_id: str, partition: str,
          gate: ReviewedLocalGate | None = None, window_metadata: Any = None,
          admissions: Any = None) -> dict:
    """Enumerate every unordered pair; eligible pairs carry validated requests.

    ``events`` must be the complete, already validated global event sequence
    for a window. Hashes are rechecked as defense in depth, not authentication.
    Every input requires a matching validated window manifest and exact
    admission census. Prospective adaptation is currently unavailable: there
    is no independently verifiable registration receipt or rights,
    completeness, and admission pipeline. Caller declarations, including a
    registration run ID and matching census, cannot satisfy that gate.
    ``partition`` is caller-supplied inventory metadata and must be one of the
    trainer partitions. Output contains opaque pair/session identities,
    family/partition, request hashes, event commitments, and label-free
    feature values. Pair orientation follows proposal event order.
    """
    if source_kind not in {"synthetic", "prospective"}:
        _fail()
    if source_kind == "prospective":
        raise ValueError(
            "prospective adaptation unavailable: no independently verified registration, "
            "rights, completeness, and admission gate exists"
        )
    if (type(family_id) is not str or not family_id or type(partition) is not str
            or partition not in {"train", "calibration", "holdout"}
            or type(events) is not list or not events):
        _fail()

    if window_metadata is None or type(admissions) is not list:
        _fail()
    try:
        validate_window(window_metadata)
    except (ValueError, TypeError, KeyError):
        _fail()
    if (window_metadata["sourceKind"] != source_kind
            or window_metadata["familyId"] != family_id):
        _fail()
    expected_previous = None
    checked = []
    grouped: dict[str, list[dict]] = {}
    seen_event_ids: set[str] = set()
    previous_moment = None
    required = {"format", "sequence", "eventId", "timestampUtc", "kind", "sessionId",
                "data", "previousHash", "eventHash"}
    for sequence, event in enumerate(events):
        if type(event) is not dict or set(event) != required:
            _fail()
        body = {key: value for key, value in event.items() if key != "eventHash"}
        if (event["format"] != EVENT_FORMAT or type(event["sequence"]) is not int
                or event["sequence"] != sequence or type(event["eventId"]) is not str
                or not event["eventId"] or event["eventId"] in seen_event_ids
                or type(event["kind"]) is not str
                or event["previousHash"] != expected_previous
                or event["eventHash"] != _digest(body) or type(event["data"]) is not dict
                or type(event["sessionId"]) is not str or not event["sessionId"]):
            _fail()
        try:
            timestamp = event["timestampUtc"]
            if type(timestamp) is not str or not timestamp.endswith("Z"):
                _fail()
            moment = datetime.fromisoformat(timestamp[:-1] + "+00:00")
            canonical_timestamp = moment.isoformat(timespec="seconds").replace("+00:00", "Z")
            if (moment.utcoffset() != timedelta(0) or timestamp != canonical_timestamp
                    or (previous_moment and moment < previous_moment)):
                _fail()
            start = datetime.fromisoformat(window_metadata["startUtc"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(window_metadata["endUtc"].replace("Z", "+00:00"))
            if not start <= moment < end:
                _fail()
        except (ValueError, TypeError):
            _fail()
        previous_moment = moment
        seen_event_ids.add(event["eventId"])
        expected_previous = event["eventHash"]
        checked.append(event)
    items = []
    allowed_kinds = {"session-open", "base-seen", "proposal", "external-observation",
                     "proposals-seen", "session-close"}
    for event in checked:
        if event["kind"] not in allowed_kinds:
            _fail()
        grouped.setdefault(event["sessionId"], []).append(event)
    session_hashes = set()
    open_admissions = {}
    for session, records in grouped.items():
        if records[0]["kind"] != "session-open" or records[-1]["kind"] != "session-close":
            _fail()
        if sum(e["kind"] == "session-open" for e in records) != 1 or sum(
                e["kind"] == "session-close" for e in records) != 1:
            _fail()
        opened = records[0]
        closed = records[-1]
        open_admissions[session] = {"sessionId": session, "eventId": opened["eventId"],
                                    "timestampUtc": opened["timestampUtc"]}
        participants = opened["data"].get("participants")
        base = opened["data"].get("base")
        if (type(participants) is not list or not participants
                or any(type(actor) is not str or not actor for actor in participants)
                or len(set(participants)) != len(participants) or type(base) is not list):
            _fail()
        participant_set = set(participants)
        for record in records[1:]:
            if record["kind"] == "session-close":
                continue
            actor = record["data"].get("actorId")
            if type(actor) is not str or actor not in participant_set:
                _fail()
        proposals = [e for e in records if e["kind"] == "proposal"]
        actors = [e["data"].get("actorId") for e in proposals]
        if len(set(actors)) != len(actors):
            _fail()
        # A closed session missing a registered participant's proposal is not
        # treated as a complete candidate-pair census.
        if set(actors) != participant_set:
            _fail()
        receipts = [e for e in records if e["kind"] == "base-seen"]
        session_digest = _digest(session)
        if session_digest in session_hashes:
            _fail()
        session_hashes.add(_digest({"windowId": window_metadata["windowId"],
                                    "sessionId": session, "openEventId": opened["eventId"],
                                    "openTimestampUtc": opened["timestampUtc"],
                                    "closeEventId": closed["eventId"],
                                    "closeTimestampUtc": closed["timestampUtc"],
                                    "openHash": opened["eventHash"], "closeHash": closed["eventHash"]}))
        for first, second in itertools.combinations(proposals, 2):
            reason = None
            ops = [first["data"].get("operation"), second["data"].get("operation")]
            for prop in (first, second):
                actor = prop["data"].get("actorId")
                if not any(r["data"].get("actorId") == actor
                           and r["data"].get("baseEventId") == opened["eventId"]
                           and r["sequence"] < prop["sequence"] for r in receipts):
                    reason = "missing-receipt"
                if any(e["kind"] in {"external-observation", "proposals-seen"}
                       and e["data"].get("actorId") == actor
                       and e["sequence"] < prop["sequence"] for e in records):
                    reason = "dependent-observation"
            if reason is None and any(prop["data"].get("baseEventId") != opened["eventId"]
                                      for prop in (first, second)):
                reason = "base-mismatch"
            if reason is None and any(type(op) is not dict or op.get("kind") != "insert" for op in ops):
                reason = "unsupported-operation"
            req = None
            if reason is None:
                req = {"model": VERSION, "base": base,
                       "operations": [{key: op[key] for key in ("id", "kind", "anchorId", "newId", "value")}
                                      for op in ops]}
                try:
                    validate_request(req)
                except (InvalidExchange, KeyError, TypeError):
                    reason = "outside-model-contract"
                    req = None
            commitment = _digest({"first": first["eventHash"], "second": second["eventHash"]})
            pair_id = _digest({"session": session_digest,
                               "events": [first["eventId"], second["eventId"]]})
            if reason:
                items.append({"pairId": pair_id, "familyId": family_id, "sessionId": session_digest,
                              "partition": partition, "sourceCommitment": commitment,
                              "excludedReason": reason})
                continue
            request_hash = _digest(req)
            features = _feature_values(req)
            learned_vector = feature_vector(features)
            items.append({"pairId": pair_id, "familyId": family_id, "sessionId": session_digest,
                          "partition": partition, "sourceCommitment": commitment,
                          "request": req, "requestHash": request_hash,
                          "featureVector": learned_vector,
                          "label": None})
    try:
        if len(admissions) != len(open_admissions):
            _fail()
        census = {}
        for entry in admissions:
            if type(entry) is not dict or set(entry) != {"sessionId", "eventId", "timestampUtc"}:
                _fail()
            if type(entry["sessionId"]) is not str or entry["sessionId"] in census:
                _fail()
            census[entry["sessionId"]] = entry
        if census != open_admissions:
            _fail()
    except (TypeError, ValueError):
        _fail()
    if len({item["pairId"] for item in items}) != len(items):
        _fail()
    return {"format": "m35-native-inventory-v1", "featureVersion": FEATURE_VERSION,
            "sourceKind": source_kind, "familyId": family_id,
            "sessionCommitments": sorted(session_hashes),
            "callerDeclarations": {"completenessDeclared": bool(gate and gate.completeness_declared),
                                   "protocolReviewDeclared": bool(gate and gate.protocol_review_declared)},
            "pairs": items}
