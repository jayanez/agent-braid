# SPDX-License-Identifier: AGPL-3.0-only
"""Local in-memory bridge from validated M3.5 events to SPEC-019 inputs.

This adapter does not read journals or sources. Its caller supplies event
records that were already validated. Returned request text is a private,
in-memory value for downstream use; callers must not publish or persist it.
SHA-256 IDs and commitments are deterministic and linkable, not confidential.
A sourceKind value and all ReviewedLocalGate declarations are caller claims.
Manifest agreement binds metadata but does not prove provenance, permission,
completeness, or authorization. Only the validated base and proposal values
are projected into model requests; surrounding event context, actor IDs,
source references, outcomes and labels are not emitted. Audit-only full-session
commitments may cover events after a pair cutoff and must never be shown to
annotators or treated as cutoff evidence.
"""
from __future__ import annotations

from hashlib import sha256
import itertools
import json
import re
import unicodedata
from datetime import datetime, timedelta
from typing import Any

from agent_braid.native_predictor_training import FEATURE_VERSION, prepare_request
from agent_braid.m35_source_window import EVENT_FORMAT, validate_window
from agent_braid.structured_exchange import InvalidExchange, VERSION, validate_request


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


def _normalize_duplicate_value(value: Any) -> Any:
    """Normalize textual values for a provisional synthetic duplicate key."""
    if type(value) is str:
        return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value).casefold()).strip()
    if type(value) is list:
        return [_normalize_duplicate_value(item) for item in value]
    if type(value) is dict:
        return {key: _normalize_duplicate_value(item) for key, item in value.items()}
    if value is None or type(value) in (bool, int, float):
        return value
    _fail()


def _duplicate_fingerprint(request: Any) -> str:
    """Fingerprint semantic synthetic operations, omitting ephemeral IDs."""
    if (type(request) is not dict or set(request) != {"model", "base", "operations"}
            or request.get("model") != "anchored-sequence-v1"
            or type(request.get("base")) is not list
            or type(request.get("operations")) is not list
            or len(request["operations"]) != 2):
        _fail()
    base = request["base"]
    positions: dict[str, int] = {}
    normalized_base = []
    for index, node in enumerate(base):
        if (type(node) is not dict or set(node) != {"id", "value"}
                or type(node.get("id")) is not str or not node["id"]):
            _fail()
        if node["id"] in positions:
            _fail()
        positions[node["id"]] = index
        normalized_base.append(_normalize_duplicate_value(node.get("value")))
    operations = []
    for operation in request["operations"]:
        if (type(operation) is not dict
                or set(operation) != {"id", "kind", "anchorId", "newId", "value"}
                or operation.get("kind") != "insert"):
            _fail()
        anchor = operation.get("anchorId")
        if anchor == "$root":
            anchor_position = -1
        elif type(anchor) is str and anchor in positions:
            anchor_position = positions[anchor]
        else:
            _fail()
        operations.append({"kind": operation["kind"], "anchorPosition": anchor_position,
                           "value": _normalize_duplicate_value(operation.get("value"))})
    operations.sort(key=_canonical)
    return _digest({"base": normalized_base, "operations": operations})


def derive_duplicate_group_ids(inventories: Any) -> dict[str, str]:
    """Derive provisional caller-declared groups for synthetic inventories.

    Identical normalized operation pairs and every pair from one session are
    joined into connected components. This is a deterministic grouping aid,
    not authenticated lineage, provenance, rights, or authority; it does not
    make any real-data use eligible.
    """
    if type(inventories) is not list or not inventories:
        _fail()
    parents: dict[str, str] = {}
    partitions: dict[str, str] = {}
    session_owner: dict[str, str] = {}
    fingerprint_owner: dict[str, str] = {}

    def find(pair_id: str) -> str:
        while parents[pair_id] != pair_id:
            parents[pair_id] = parents[parents[pair_id]]
            pair_id = parents[pair_id]
        return pair_id

    def union(left: str, right: str) -> None:
        a, b = find(left), find(right)
        if a != b:
            parents[max(a, b)] = min(a, b)

    for inventory in inventories:
        if (type(inventory) is not dict or inventory.get("format") != "m35-native-inventory-v1"
                or inventory.get("sourceKind") != "synthetic"
                or type(inventory.get("pairs")) is not list):
            _fail()
        for pair in inventory["pairs"]:
            if type(pair) is not dict or "excludedReason" in pair:
                continue
            pair_id, session_id, partition = (pair.get("pairId"), pair.get("sessionId"),
                                               pair.get("partition"))
            if (type(pair_id) is not str or not pair_id or pair_id in parents
                    or type(session_id) is not str or not session_id
                    or type(partition) is not str
                    or partition not in {"train", "calibration", "holdout"}):
                _fail()
            parents[pair_id] = pair_id
            partitions[pair_id] = partition
            fingerprint = _duplicate_fingerprint(pair.get("request"))
            for key, owners in ((session_id, session_owner), (fingerprint, fingerprint_owner)):
                prior = owners.get(key)
                if prior is not None:
                    union(pair_id, prior)
                else:
                    owners[key] = pair_id
    components: dict[str, list[str]] = {}
    for pair_id in parents:
        components.setdefault(find(pair_id), []).append(pair_id)
    result = {}
    for members in components.values():
        if len({partitions[item] for item in members}) != 1:
            raise ValueError("duplicate group crosses partitions")
        group_id = "dg-" + _digest({"members": sorted(members)})
        for pair_id in members:
            result[pair_id] = group_id
    return result


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
    feature values. Pair orientation and its annotation cutoff follow the
    validated proposal event sequence. Cutoff/prefix commitments cover only
    this synthetic input and are not a source-completeness proof.
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
        proposals = sorted((e for e in records if e["kind"] == "proposal"),
                           key=lambda event: event["sequence"])
        actors = [e["data"].get("actorId") for e in proposals]
        if len(set(actors)) != len(actors):
            _fail()
        # A closed session missing a registered participant's proposal is not
        # treated as a complete candidate-pair census.
        if set(actors) != participant_set:
            _fail()
        receipts = [e for e in records if e["kind"] == "base-seen"]
        # Keep the opaque session identity stable when one family is observed
        # in overlapping windows; window scope belongs to pair IDs/commitments.
        session_digest = _digest({"familyId": family_id, "sessionId": session})
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
            if any(prop["data"].get("baseEventId") != opened["eventId"]
                   for prop in (first, second)):
                reason = "base-mismatch"
            for prop in (first, second):
                if reason is not None:
                    break
                actor = prop["data"].get("actorId")
                if any(e["kind"] in {"external-observation", "proposals-seen"}
                       and e["data"].get("actorId") == actor
                       and e["sequence"] < prop["sequence"] for e in records):
                    reason = "dependent-observation"
                    break
                if not any(r["data"].get("actorId") == actor
                           and r["data"].get("baseEventId") == opened["eventId"]
                           and r["sequence"] < prop["sequence"] for r in receipts):
                    reason = "missing-receipt"
                    break
            # Match the canonical source-window audit. A valid request and
            # hash chain do not establish source provenance.
            if reason is None and any(
                    type(value) is not str or not value
                    for value in (opened["data"].get("sourceRef"),
                                  opened["data"].get("contextSha"),
                                  first["data"].get("sourceRef"),
                                  second["data"].get("sourceRef"))):
                reason = "missing-provenance"
            if reason is None and (type(base) is not list or len(base) > 3):
                reason = "invalid-base"
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
            cutoff_event = max((first, second), key=lambda event: event["sequence"])
            source_prefix = [event for event in checked
                             if event["sequence"] <= cutoff_event["sequence"]]
            cutoff = {
                "sequence": cutoff_event["sequence"],
                "eventCommitment": _digest(cutoff_event["eventHash"]),
                "sourcePrefixEventCount": len(source_prefix),
                "sourcePrefixCommitment": _digest(
                    [event["eventHash"] for event in source_prefix]),
                "annotatorVisible": False,
            }
            pair_id = _digest({"windowId": window_metadata["windowId"],
                               "familyId": family_id, "session": session_digest,
                               "events": [first["eventId"], second["eventId"]]})
            orientation = {
                "method": "source-event-sequence-provisional-v1",
                "firstSequence": first["sequence"],
                "secondSequence": second["sequence"],
                "sameEventTie": first["sequence"] == second["sequence"],
                "sameTimestamp": first["timestampUtc"] == second["timestampUtc"],
                "annotatorVisible": False,
            }
            if reason:
                items.append({"pairId": pair_id, "familyId": family_id, "sessionId": session_digest,
                              "partition": partition, "sourceCommitment": commitment,
                              "orientation": orientation, "cutoff": cutoff,
                              "excludedReason": reason})
                continue
            request_hash = _digest(req)
            # Use the trainer's request-bound canonical extractor so the
            # adapter cannot drift into emitting a different feature mapping.
            learned_vector = prepare_request(req, source_kind="synthetic")
            items.append({"pairId": pair_id, "familyId": family_id, "sessionId": session_digest,
                          "partition": partition, "sourceCommitment": commitment,
                          "orientation": orientation, "cutoff": cutoff,
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
            "auditOnlySessionCommitments": sorted(session_hashes),
            "callerDeclarations": {"completenessDeclared": bool(gate and gate.completeness_declared),
                                   "protocolReviewDeclared": bool(gate and gate.protocol_review_declared)},
            "pairs": items}


def project_trainer_rows(inventories: Any, *, training_labels: Any,
                         calibration_labels: Any,
                         duplicate_group_ids: Any = None) -> list[dict]:
    """Project synthetic adapter inventories into the trainer's strict schema.

    Duplicate groups are derived by the provisional synthetic grouping rule.
    Optional caller-supplied IDs are accepted only when they exactly match the
    derivation; they cannot override it. The derivation is caller-declared and
    unauthenticated, and does not establish lineage or authorize real data.
    Holdout labels are not an input and are always projected as unknown.
    """
    if type(inventories) is not list or not inventories:
        _fail()
    if type(training_labels) is not dict or type(calibration_labels) is not dict:
        _fail()
    derived_group_ids = derive_duplicate_group_ids(inventories)
    if duplicate_group_ids is not None and (type(duplicate_group_ids) is not dict
                                            or duplicate_group_ids != derived_group_ids):
        _fail()
    eligible: list[dict] = []
    seen: set[str] = set()
    expected_training: set[str] = set()
    expected_calibration: set[str] = set()
    for inventory in inventories:
        if (type(inventory) is not dict
                or inventory.get("format") != "m35-native-inventory-v1"
                or inventory.get("featureVersion") != FEATURE_VERSION
                or inventory.get("sourceKind") != "synthetic"
                or type(inventory.get("familyId")) is not str
                or not inventory["familyId"]
                or type(inventory.get("pairs")) is not list):
            _fail()
        for item in inventory["pairs"]:
            if type(item) is not dict or type(item.get("pairId")) is not str:
                _fail()
            pair_id = item["pairId"]
            if not pair_id or pair_id in seen:
                _fail()
            seen.add(pair_id)
            # Bind pair-level metadata to its containing inventory. Otherwise
            # a rewritten pair family could hide cross-partition family leakage
            # from the trainer while leaving the envelope unchanged.
            if item.get("familyId") != inventory["familyId"]:
                _fail()
            if "excludedReason" in item:
                if set(item) != {"pairId", "familyId", "sessionId", "partition",
                                 "sourceCommitment", "orientation", "cutoff", "excludedReason"}:
                    _fail()
                continue
            if set(item) != {"pairId", "familyId", "sessionId", "partition",
                             "sourceCommitment", "orientation", "cutoff", "request", "requestHash",
                             "featureVector", "label"} or item["label"] is not None:
                _fail()
            if item["partition"] == "train":
                expected_training.add(pair_id)
            elif item["partition"] == "calibration":
                expected_calibration.add(pair_id)
            elif item["partition"] != "holdout":
                _fail()
            try:
                validate_request(item["request"])
                if (item["request"].get("model") != "anchored-sequence-v1"
                        or len(item["request"].get("operations", [])) != 2
                        or any(operation.get("kind") != "insert"
                               for operation in item["request"]["operations"])):
                    _fail()
                if _digest(item["request"]) != item["requestHash"]:
                    _fail()
                expected_vector = prepare_request(item["request"], source_kind="synthetic")
            except (InvalidExchange, TypeError, ValueError, KeyError):
                _fail()
            if item["featureVector"] != expected_vector:
                _fail()
            eligible.append(item)
    if (set(training_labels) != expected_training
            or set(calibration_labels) != expected_calibration
            or set(derived_group_ids) != {item["pairId"] for item in eligible}):
        _fail()
    result = []
    for item in eligible:
        pair_id = item["pairId"]
        partition = item["partition"]
        label = (training_labels[pair_id] if partition == "train" else
                 calibration_labels[pair_id] if partition == "calibration" else None)
        if label is not None and (type(label) is not int or label not in (0, 1)):
            _fail()
        group_id = derived_group_ids[pair_id]
        if type(group_id) is not str or not group_id:
            _fail()
        result.append({"pairId": pair_id, "familyId": item["familyId"],
                       "sessionId": item["sessionId"], "duplicateGroupId": group_id,
                       "partition": partition, "features": item["featureVector"]["features"],
                       "label": label})
    return result
