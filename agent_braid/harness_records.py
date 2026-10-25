# SPDX-License-Identifier: AGPL-3.0-only
"""Strict versioned codecs for laboratory records; no filesystem, host or execution authority.

``decode`` accepts only the exact canonical bytes that ``encode`` would produce, so every
record round-trips byte for byte and a hash taken over the bytes identifies the record.
Unknown formats, future versions, unknown or missing fields and non-canonical spellings
refuse with fixed reason codes. Decoding proves shape and internal consistency, never
authenticity: a consumer still compares a trusted hash from outside the record.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any

from .harness_manifest import BINDING_NAMES, FORMAT as MANIFEST_FORMAT, ManifestError, parse_manifest
from .harness_refinement import DECISION_FORMAT, MAX_PROBES, MAX_SCORE, UPSTREAM_REVISION
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

MAX_RECORD_BYTES = 1_048_576
FORMATS = {
    "manifest": MANIFEST_FORMAT,
    "decision": DECISION_FORMAT,
    "attempt-status": "braid-harness-attempt-status/v0.1",
    "comparison": "braid-harness-comparison/v0.1",
}
MAX_DIFFERENCES = 64
MAX_TEXT = 512
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_FIELD = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
_FAMILY = re.compile(r"(braid-harness-[a-z-]+)/v([0-9]+\.[0-9]+)\Z")
_SCOPES = ("base", "general", "task", "composed")
_ATTEMPT_STATUSES = frozenset({"scored", "unscored", "missing", "invalid", "failed",
                               "interrupted", "refused", "not-probed", "abstained", "rejected"})
_DECISIONS = ("candidate", "keep-base", "inconclusive", "refused")
_TERMINALS = ("completed", "failed", "interrupted", "refused")


class RecordError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-record"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-record") -> None:
    if not condition:
        raise RecordError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _optional(value: Any, check) -> bool:
    return value is None or check(value)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _ids(value: Any, limit: int) -> bool:
    return type(value) is list and len(value) <= limit and all(_id(i) for i in value)


def _exact(value: Any, keys: set[str]) -> None:
    _require(type(value) is dict and set(value) == keys)


# --- per-kind validators ---------------------------------------------------------------

_DECISION_KEYS = {"format", "manifestSha256", "policySha256", "baseSha256", "marginMicros",
                  "decision", "reasons", "chosenCandidateSha256", "attempts", "counts",
                  "losses", "provenance", "executionAuthorization"}
_ATTEMPT_KEYS = {"scope", "candidateSha256", "status", "reason", "score", "deltaMicros",
                 "regressed", "observationSha256", "id"}


def _validate_attempt(row: Any) -> None:
    _exact(row, _ATTEMPT_KEYS)
    _require(row["scope"] in _SCOPES and row["status"] in _ATTEMPT_STATUSES
             and _id(row["id"]) and _optional(row["candidateSha256"], _hash)
             and _optional(row["observationSha256"], _hash) and _optional(row["reason"], _id)
             and _optional(row["score"], lambda v: _int(v, 0, MAX_SCORE))
             and _optional(row["deltaMicros"], lambda v: _int(v, -MAX_SCORE, MAX_SCORE))
             and _optional(row["regressed"], lambda v: type(v) is bool))


def _validate_decision(value: dict) -> None:
    _exact(value, _DECISION_KEYS)
    _require(value["executionAuthorization"] is False)
    for name in ("manifestSha256", "policySha256", "baseSha256"):
        _require(_hash(value[name]))
    _require(_int(value["marginMicros"], 0, MAX_SCORE) and value["decision"] in _DECISIONS
             and _ids(value["reasons"], 4) and _ids(value["losses"], 16)
             and _optional(value["chosenCandidateSha256"], _hash))
    attempts = value["attempts"]
    _require(type(attempts) is list and len(attempts) <= MAX_PROBES + 2)
    for row in attempts:
        _validate_attempt(row)
    _require(len({a["id"] for a in attempts}) == len(attempts)
             and len({a["scope"] for a in attempts}) == len(attempts))
    scored = {a["candidateSha256"] for a in attempts if a["status"] == "scored"}
    chosen = value["chosenCandidateSha256"]
    _require((value["decision"] == "candidate") == (chosen is not None)
             and (chosen is None or chosen in scored))
    counts = value["counts"]
    _exact(counts, {"probes", "maxProbes", "abstentions", "rejections"})
    _require(_int(counts["maxProbes"], 1, MAX_PROBES) and _int(counts["probes"], 0, counts["maxProbes"])
             and _int(counts["abstentions"], 0, 2) and _int(counts["rejections"], 0, 2))
    provenance = value["provenance"]
    _exact(provenance, {"upstreamRevision", "adapted", "changes"})
    _require(provenance["upstreamRevision"] == UPSTREAM_REVISION
             and type(provenance["adapted"]) is list and len(provenance["adapted"]) <= 8
             and all(type(t) is str and len(t) <= 512 for t in provenance["adapted"])
             and type(provenance["changes"]) is str and len(provenance["changes"]) <= 512)


_STATUS_KEYS = {"format", "attemptId", "manifestSha256", "phase", "state", "outcome", "source",
                "completed", "pending", "records", "redispatchAllowed", "permissionRenewed",
                "executionAuthorization"}


def _validate_status(value: dict) -> None:
    _exact(value, _STATUS_KEYS)
    _require(value["redispatchAllowed"] is False and value["permissionRenewed"] is False
             and value["executionAuthorization"] is False)
    _require(_id(value["attemptId"]) and _hash(value["manifestSha256"])
             and value["phase"] in ("started", "checkpointed", "ended")
             and value["outcome"] in ("pending", "recorded", "unknown")
             and value["state"] in (None, *_TERMINALS, "unobserved") and value["source"] in (None, "terminal", "recovery")
             and _ids(value["completed"], 16) and _ids(value["pending"], 16)
             and _int(value["records"], 1, 1024))
    ended = value["phase"] == "ended"
    _require(ended == (value["state"] is not None) and ended == (value["source"] is not None)
             and ended == (value["outcome"] != "pending"))


def _scalar(value: Any) -> bool:
    return value is None or type(value) is bool or _int(value, -(1 << 63), (1 << 63) - 1) or (
        type(value) is str and len(value) <= MAX_TEXT and value.isprintable())


def _validate_comparison(value: dict) -> None:
    _exact(value, {"format", "recordKind", "leftSha256", "rightSha256", "identical",
                   "differences", "executionAuthorization"})
    rows = value["differences"]
    _require(value["executionAuthorization"] is False and value["recordKind"] in ("manifest", "decision", "attempt-status")
             and _hash(value["leftSha256"]) and _hash(value["rightSha256"])
             and type(value["identical"]) is bool and type(rows) is list and len(rows) <= MAX_DIFFERENCES)
    for row in rows:
        _exact(row, {"field", "left", "right"})
        _require(type(row["field"]) is str and _FIELD.fullmatch(row["field"]) is not None
                 and _scalar(row["left"]) and _scalar(row["right"]) and row["left"] != row["right"])
    _require(value["identical"] == (value["leftSha256"] == value["rightSha256"]))
    _require(value["identical"] <= (rows == []))


def _validate_manifest(value: dict) -> None:
    try:
        parse_manifest(canonical(value))
    except ManifestError as exc:
        raise RecordError(exc.reason) from None


_VALIDATORS = {"decision": _validate_decision, "attempt-status": _validate_status,
               "comparison": _validate_comparison, "manifest": _validate_manifest}
_KIND_OF = {format_: kind for kind, format_ in FORMATS.items()}


# --- record ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Record:
    """Immutable validated record; ``sha256`` binds its canonical bytes."""

    kind: str
    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


def encode(kind: str, value: Any) -> Record:
    """Validate ``value`` as ``kind`` and return its canonical record."""
    _require(type(kind) is str and kind in FORMATS, "unknown-kind")
    _require(type(value) is dict and value.get("format") == FORMATS[kind], "wrong-format")
    try:
        raw = canonical(value)
    except (TypeError, ValueError, RecursionError):
        raise RecordError("invalid-record") from None
    _require(len(raw) <= MAX_RECORD_BYTES, "record-too-large")
    try:
        _VALIDATORS[kind](parse_json(raw))
    except InvalidDecision:
        raise RecordError("invalid-record") from None
    return Record(kind, freeze(parse_json(raw)), raw)


def decode(raw: bytes) -> Record:
    """Parse exact canonical bytes of a known version; refuse everything else."""
    _require(type(raw) is bytes, "invalid-record")
    _require(len(raw) <= MAX_RECORD_BYTES, "record-too-large")
    try:
        value = parse_json(raw)
    except InvalidDecision as exc:
        raise RecordError("record-too-large" if exc.reason == "input-budget-exceeded"
                          else "invalid-json") from None
    declared = value.get("format") if type(value) is dict else None
    if declared not in _KIND_OF:
        family = _FAMILY.fullmatch(declared) if type(declared) is str else None
        _require(family is not None and any(f.startswith(family.group(1) + "/") for f in _KIND_OF),
                 "unknown-format")
        raise RecordError("unsupported-version")
    record = encode(_KIND_OF[declared], value)
    _require(record.canonical_bytes == raw, "non-canonical")
    return record


# --- comparison -----------------------------------------------------------------------


def _join(values: list) -> str:
    return ",".join(values)


def _fields(record: Record) -> dict[str, Any]:
    data = record.data
    if record.kind == "manifest":
        return {"sha256": record.sha256, **{name: _binding(data, name) for name in sorted(BINDING_NAMES)}}
    if record.kind == "decision":
        fields = {name: data[name] for name in ("decision", "chosenCandidateSha256", "policySha256",
                                                 "baseSha256", "marginMicros")}
        fields.update(reasons=_join(data["reasons"]), losses=_join(data["losses"]),
                      probes=data["counts"]["probes"])
        for row in data["attempts"]:
            fields[f"attempt.{row['scope']}.status"] = row["status"]
            fields[f"attempt.{row['scope']}.score"] = row["score"]
        return fields
    return {name: data[name] for name in ("manifestSha256", "phase", "state", "outcome", "source",
                                           "records")} | {"completed": _join(data["completed"]),
                                                          "pending": _join(data["pending"])}


def _binding(data: Mapping[str, Any], name: str) -> str:
    """Identity of one named manifest binding, derived the way the manifest derives it."""
    if name == "fixture":
        return data["task"]["fixtureSha256"]
    if name == "envelope":
        return data["envelopeSha256"]
    return digest(data[name])


def compare(left: Record, right: Record) -> Record:
    """Describe field-level differences between two records of the same kind."""
    _require(isinstance(left, Record) and isinstance(right, Record), "invalid-record")
    _require(left.kind == right.kind and left.kind != "comparison", "kind-mismatch")
    before, after = _fields(left), _fields(right)
    rows = [{"field": name, "left": before.get(name), "right": after.get(name)}
            for name in sorted(set(before) | set(after)) if before.get(name) != after.get(name)]
    return encode("comparison", {
        "format": FORMATS["comparison"], "recordKind": left.kind, "leftSha256": left.sha256,
        "rightSha256": right.sha256, "identical": left.sha256 == right.sha256,
        "differences": rows, "executionAuthorization": False})


def attempt_status_record(status: Any) -> Record:
    """Encode a journal ``AttemptStatus`` view as an attempt-status record."""
    _require(hasattr(status, "to_dict"), "invalid-record")
    return encode("attempt-status", {"format": FORMATS["attempt-status"], **status.to_dict()})
