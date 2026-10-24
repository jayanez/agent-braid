# SPDX-License-Identifier: AGPL-3.0-only
"""Pure offline trajectory/artifact observation with loss and privacy accounting.

Normalizes fixture or host events and before/after artifact bytes into a private,
versioned, hash-bound record. No filesystem, process or network access and no
authority: a record is evidence, never a grant. Raw provider transcripts are not
exported; only an independently verified inventory's allowed fields leave, redacted.
Missing, duplicated, malformed or transport-failed events are counted, and a loss can
never leave a ``completed`` terminal. Unobserved outcomes stay ``unobserved``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any

from .system_one import InvalidDecision, canonical, freeze, parse_json, thaw

FORMAT = "braid-harness-observation/v0.1"
INVENTORY_FORMAT = "braid-harness-export-inventory/v0.1"
MAX_EVENTS = 256
MAX_SEQ = 1023
MAX_ARTIFACTS = 32
MAX_ARTIFACT_BYTES = 262_144
MAX_FIELD_BYTES = 4096
MAX_TRANSPORT_ERRORS = 16
MAX_SECRETS = 64
MAX_TIME = 1 << 40
REDACTED = "[REDACTED]"
TERMINALS = ("completed", "failed", "interrupted", "refused")
_ALL_TERMINALS = (*TERMINALS, "unobserved")
_KINDS = frozenset({"start", "message", "tool", "effect", "terminal", "error"})
_EFFECTS = frozenset({"create", "write", "delete", "process", "network"})
_RESERVED = frozenset({"seq", "kind"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_FIELD = re.compile(r"[a-z][A-Za-z0-9_]{0,31}\Z")
_TOP = {"format", "attemptId", "manifestSha256", "source", "state", "terminal",
        "rawEventsSha256", "normalizedEventsSha256", "events", "artifactsObserved",
        "artifacts", "effects", "loss", "redaction", "observedAt", "retainUntil",
        "purgedPayloadSha256", "executionAuthorization"}


class ObservationError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-observation"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-observation") -> None:
    if not condition:
        raise ObservationError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _hash(value: Any, reason: str = "invalid-observation") -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, reason)


def _text(value: Any) -> bool:
    return (type(value) is str and len(value.encode("utf-8", "surrogatepass")) <= MAX_FIELD_BYTES
            and not any(0xD800 <= ord(c) <= 0xDFFF for c in value))


def _strings(value: Any):
    """Yield every string (keys and values) of a JSON-like tree."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, child in value.items():
            yield from _strings(key)
            yield from _strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _strings(child)


def _relative(path: Any) -> None:
    _require(_text(path) and path != "" and not path.startswith("/") and "\\" not in path
             and "\x00" not in path and all(p not in ("", ".", "..") for p in path.split("/"))
             and len(path.split("/")) <= 8 and len(path) <= 200, "invalid-path")


# --- export inventory -------------------------------------------------------------


@dataclass(frozen=True)
class ExportInventory:
    """Immutable parsed inventory; construction is not independent verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def secrets(self) -> tuple[str, ...]:
        return self.data["secrets"]


def verify_inventory(raw: bytes, *, expected_sha256: str) -> ExportInventory:
    """Parse a strict inventory and compare it with a trusted external hash.

    The inventory lists the only event fields that may leave, the secret literals to
    redact and the maximum retention. Matching hashes prove byte identity only.
    """
    _hash(expected_sha256, "invalid-expected-hash")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise ObservationError("invalid-inventory") from None
    ok = (type(value) is dict
          and set(value) == {"format", "allowedEventFields", "secrets", "maxRetentionSeconds"}
          and value["format"] == INVENTORY_FORMAT)
    _require(ok, "invalid-inventory")
    fields, secrets = value["allowedEventFields"], value["secrets"]
    _require(type(fields) is list and len(fields) <= 32 and len(set(fields)) == len(fields)
             and all(type(f) is str and _FIELD.fullmatch(f) and f not in _RESERVED for f in fields),
             "invalid-inventory")
    _require(type(secrets) is list and len(secrets) <= MAX_SECRETS and len(set(secrets)) == len(secrets)
             and all(_text(s) and len(s) >= 8 for s in secrets), "invalid-inventory")
    _require(_int(value["maxRetentionSeconds"], 1, MAX_TIME), "invalid-inventory")
    inventory = ExportInventory(freeze(value), canonical(value))
    _require(inventory.sha256 == expected_sha256, "inventory-drift")
    return inventory


def _redact(value: str, secrets: Sequence[str]) -> tuple[str, int]:
    count = 0
    for secret in sorted(secrets, key=len, reverse=True):
        count += value.count(secret)
        value = value.replace(secret, REDACTED)
    return value, count


def _identity(value: str, secrets: Sequence[str]) -> str:
    _require(not any(s in value for s in secrets), "secret-in-identity")
    return value


# --- record -----------------------------------------------------------------------


@dataclass(frozen=True)
class Observation:
    """Immutable observation record; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return thaw(self.data)


def _build(value: dict) -> Observation:
    raw = canonical(value)
    _require(len(raw) <= 1_048_576, "observation-too-large")
    return Observation(freeze(value), raw)


def _normalize_events(events: Any, expected: int | None, inventory: ExportInventory):
    _require(type(events) in (list, tuple) and len(events) <= MAX_EVENTS, "invalid-events")
    allowed, secrets = inventory.data["allowedEventFields"], inventory.secrets
    accepted: dict[int, dict] = {}
    duplicates: set[int] = set()
    malformed = replaced = dropped = 0
    for event in events:
        seq = event.get("seq") if type(event) is dict else None
        kind = event.get("kind") if type(event) is dict else None
        valid = _int(seq, 0, MAX_SEQ) and kind in _KINDS
        valid = valid and all(type(v) is int or _text(v)
                              for k, v in event.items() if k in allowed)
        if valid and kind == "terminal":
            valid = event.get("state") in TERMINALS
        if valid and kind == "effect":
            valid = (event.get("effect") in _EFFECTS
                     and ("path" not in event or (_relative(event["path"]) is None)))
        if not valid:
            malformed += 1
        elif seq in accepted:
            duplicates.add(seq)
        else:
            accepted[seq] = event
    top = max(accepted, default=-1)
    if expected is not None:
        top = max(top, expected - 1)
    missing = [i for i in range(top + 1) if i not in accepted]
    exported = []
    for seq in sorted(accepted):
        event, out = accepted[seq], {"seq": seq, "kind": accepted[seq]["kind"]}
        for key, item in event.items():
            if key in _RESERVED:
                continue
            if key not in allowed:
                dropped += 1
            elif type(item) is str:
                out[key], n = _redact(item, secrets)
                replaced += n
            else:
                out[key] = item
        exported.append(out)
    return accepted, exported, sorted(duplicates), missing, malformed, replaced, dropped


def _snapshot(files: Any) -> dict[str, bytes]:
    _require(isinstance(files, Mapping) and len(files) <= MAX_ARTIFACTS, "invalid-artifacts")
    for path, content in files.items():
        _relative(path)
        _require(type(content) is bytes and len(content) <= MAX_ARTIFACT_BYTES, "invalid-artifacts")
    return dict(files)


def _diff(before: dict[str, bytes], after: dict[str, bytes], secrets: Sequence[str]):
    artifacts = []
    for path in sorted(before.keys() | after.keys()):
        old, new = before.get(path), after.get(path)
        if old == new:
            continue
        _identity(path, secrets)
        artifacts.append({
            "path": path,
            "change": "created" if old is None else "deleted" if new is None else "modified",
            "beforeSha256": None if old is None else sha256(old).hexdigest(),
            "afterSha256": None if new is None else sha256(new).hexdigest(),
            "sizeBytes": len(new if new is not None else old)})
    return artifacts


_EFFECT_FOR = {"created": "create", "modified": "write", "deleted": "delete"}


def observe(events: Sequence[Mapping[str, Any]], *, manifest_sha256: str, attempt_id: str,
            source: str, inventory: ExportInventory, now: int, retention_seconds: int,
            before: Mapping[str, bytes] | None = None, after: Mapping[str, bytes] | None = None,
            expected_events: int | None = None,
            transport_errors: Sequence[str] = ()) -> Observation:
    """Create a private observation; refuse malformed arguments, never repair them."""
    _require(isinstance(inventory, ExportInventory), "invalid-inventory")
    _hash(manifest_sha256, "invalid-manifest-hash")
    secrets = inventory.secrets
    _require(type(attempt_id) is str and _ID.fullmatch(attempt_id) is not None, "invalid-attempt")
    _identity(attempt_id, secrets)
    _require(source in ("fixture", "host"), "invalid-source")
    _require(_int(now, 0, MAX_TIME), "invalid-time")
    _require(_int(retention_seconds, 1, inventory.data["maxRetentionSeconds"]), "invalid-retention")
    _require(expected_events is None or _int(expected_events, 0, MAX_EVENTS), "invalid-expected-events")
    _require(isinstance(transport_errors, (list, tuple)) and len(transport_errors) <= MAX_TRANSPORT_ERRORS
             and all(type(e) is str and _ID.fullmatch(e) for e in transport_errors), "invalid-transport-errors")
    _require((before is None) == (after is None), "invalid-artifacts")

    accepted, exported, duplicates, missing, malformed, replaced, dropped = _normalize_events(
        events, expected_events, inventory)
    for event in accepted.values():
        if event["kind"] == "effect" and "path" in event:
            _identity(event["path"], secrets)

    artifacts, effects = [], {}
    if before is not None:
        artifacts = _diff(_snapshot(before), _snapshot(after), secrets)
        for item in artifacts:
            effects[(_EFFECT_FOR[item["change"]], item["path"])] = "observed"
    for event in accepted.values():
        if event["kind"] == "effect":
            effects.setdefault((event["effect"], event.get("path")), "inferred")

    terminals = [accepted[s]["state"] for s in sorted(accepted) if accepted[s]["kind"] == "terminal"]
    lossy = bool(missing or duplicates or malformed or transport_errors)
    terminal = terminals[0] if len(terminals) == 1 and not lossy else "unobserved"
    if len(terminals) > 1:
        terminal = "unobserved"

    rawdigest = sha256(canonical(list(events))).hexdigest()
    record = {
        "format": FORMAT, "attemptId": attempt_id, "manifestSha256": manifest_sha256,
        "source": source, "state": "retained", "terminal": terminal,
        "rawEventsSha256": rawdigest, "normalizedEventsSha256": sha256(canonical(exported)).hexdigest(),
        "events": exported, "artifactsObserved": before is not None, "artifacts": artifacts,
        "effects": [{"kind": k, "path": p, "evidence": e} for (k, p), e in sorted(
            effects.items(), key=lambda i: (i[0][0], i[0][1] or ""))],
        "loss": {"missingSeq": missing, "duplicateSeq": duplicates, "malformedEvents": malformed,
                 "transportErrors": list(transport_errors), "terminalEvents": len(terminals)},
        "redaction": {"inventorySha256": inventory.sha256, "replacements": replaced,
                      "droppedFields": dropped},
        "observedAt": now, "retainUntil": now + retention_seconds, "purgedPayloadSha256": None,
        "executionAuthorization": False}
    _require(not any(s in text for text in _strings(record) for s in secrets), "redaction-failed")
    return _build(record)


# --- verification, reuse and purge -----------------------------------------------


def _validate_record(v: Any) -> None:
    _require(type(v) is dict and set(v) == _TOP and v["format"] == FORMAT, "invalid-observation")
    _require(type(v["attemptId"]) is str and _ID.fullmatch(v["attemptId"]), "invalid-observation")
    for name in ("manifestSha256", "rawEventsSha256", "normalizedEventsSha256"):
        _hash(v[name])
    _require(v["source"] in ("fixture", "host") and v["state"] in ("retained", "purged")
             and v["terminal"] in _ALL_TERMINALS and v["executionAuthorization"] is False
             and type(v["artifactsObserved"]) is bool, "invalid-observation")
    _require(_int(v["observedAt"], 0, MAX_TIME) and _int(v["retainUntil"], 1, MAX_TIME)
             and v["retainUntil"] > v["observedAt"], "invalid-observation")
    purged = v["purgedPayloadSha256"]
    _require((purged is None) == (v["state"] == "retained"), "invalid-observation")
    if purged is not None:
        _hash(purged)
    for name in ("events", "artifacts", "effects"):
        _require(type(v[name]) is list and len(v[name]) <= MAX_EVENTS
                 and (v["state"] == "retained" or v[name] == []), "invalid-observation")
    _require(sha256(canonical(v["events"])).hexdigest() == v["normalizedEventsSha256"]
             or v["state"] == "purged", "invalid-observation")
    for e in v["events"]:
        _require(type(e) is dict and _int(e.get("seq"), 0, MAX_SEQ) and e.get("kind") in _KINDS,
                 "invalid-observation")
    for a in v["artifacts"]:
        _require(type(a) is dict and set(a) == {"path", "change", "beforeSha256", "afterSha256", "sizeBytes"}
                 and a["change"] in _EFFECT_FOR and _int(a["sizeBytes"], 0, MAX_ARTIFACT_BYTES),
                 "invalid-observation")
        _relative(a["path"])
        for name in ("beforeSha256", "afterSha256"):
            if a[name] is not None:
                _hash(a[name])
    for f in v["effects"]:
        _require(type(f) is dict and set(f) == {"kind", "path", "evidence"} and f["kind"] in _EFFECTS
                 and f["evidence"] in ("observed", "inferred"), "invalid-observation")
        if f["path"] is not None:
            _relative(f["path"])
    loss = v["loss"]
    _require(type(loss) is dict and set(loss) == {"missingSeq", "duplicateSeq", "malformedEvents",
                                                  "transportErrors", "terminalEvents"}
             and all(type(loss[k]) is list and all(_int(i, 0, MAX_SEQ) for i in loss[k])
                     for k in ("missingSeq", "duplicateSeq"))
             and _int(loss["malformedEvents"], 0, MAX_EVENTS) and _int(loss["terminalEvents"], 0, MAX_EVENTS)
             and type(loss["transportErrors"]) is list
             and all(type(e) is str and _ID.fullmatch(e) for e in loss["transportErrors"]),
             "invalid-observation")
    red = v["redaction"]
    _require(type(red) is dict and set(red) == {"inventorySha256", "replacements", "droppedFields"}
             and _int(red["replacements"], 0, MAX_TIME) and _int(red["droppedFields"], 0, MAX_TIME),
             "invalid-observation")
    _hash(red["inventorySha256"])
    lossy = (loss["missingSeq"] or loss["duplicateSeq"] or loss["malformedEvents"]
             or loss["transportErrors"] or loss["terminalEvents"] != 1)
    _require(not (lossy and v["terminal"] != "unobserved"), "invalid-observation")


def verify_observation(raw: bytes, *, expected_sha256: str, now: int,
                       inventory: ExportInventory | None = None) -> Observation:
    """Reparse raw bytes against a trusted hash; expired or purged evidence is not reusable."""
    _hash(expected_sha256, "invalid-expected-hash")
    _require(_int(now, 0, MAX_TIME), "invalid-time")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise ObservationError("invalid-observation") from None
    _validate_record(value)
    record = _build(value)
    _require(record.sha256 == expected_sha256, "observation-drift")
    _require(value["state"] == "retained", "observation-purged")
    _require(now < value["retainUntil"], "observation-expired")
    if inventory is not None:
        _require(inventory.sha256 == value["redaction"]["inventorySha256"], "inventory-drift")
        _require(not any(s in text for text in _strings(value) for s in inventory.secrets),
                 "secret-in-export")
    return record


def purge_expired(observations: Sequence[Observation], *, now: int):
    """Drop expired payloads; keep a hash-bound tombstone so failed attempts stay visible.

    Returns the full replacement sequence and a receipt of identifiers and hashes only.
    """
    _require(_int(now, 0, MAX_TIME) and isinstance(observations, (list, tuple))
             and all(isinstance(o, Observation) for o in observations), "invalid-purge")
    kept, purged = [], []
    for item in observations:
        value = item.to_dict()
        if value["state"] == "purged" or now < value["retainUntil"]:
            kept.append(item)
            continue
        value.update(state="purged", events=[], artifacts=[], effects=[], purgedPayloadSha256=item.sha256)
        kept.append(_build(value))
        purged.append({"attemptId": value["attemptId"], "terminal": value["terminal"],
                       "payloadSha256": item.sha256})
    return tuple(kept), {"purged": purged}
