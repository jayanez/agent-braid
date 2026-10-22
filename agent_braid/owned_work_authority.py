# SPDX-License-Identifier: AGPL-3.0-only
"""Pure SPEC-051 authority comparison; never a registry loader or grant issuer.

The operator supplies registry snapshots through trusted Python code. Nothing here
reads roots, authenticates consent, issues execution grants or admits real capture.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from typing import Any

MAX_BYTES = 65536
MAX_DEPTH = 16


class OwnedWorkError(ValueError):
    """Fixed refusal code/path, without echoing untrusted content."""

    def __init__(self, code: str, path: str = "$") -> None:
        self.code, self.path = code, path
        super().__init__(f"{code}: {path}")


def _require(condition: bool, code: str, path: str = "$") -> None:
    if not condition:
        raise OwnedWorkError(code, path)


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON bytes; this encoding does not validate a contract."""
    try:
        return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True,
                          separators=(",", ":")).encode("ascii")
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise OwnedWorkError("invalid-json") from None


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def utc(value: str) -> datetime:
    _require(type(value) is str and bool(re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value)), "invalid-utc")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise OwnedWorkError("invalid-utc") from None


def parse_json(raw: bytes, *, limit: int = MAX_BYTES) -> dict:
    """Bounded strict raw admission, including duplicate keys and Unicode."""
    _require(type(raw) is bytes and 0 < len(raw) <= min(limit, MAX_BYTES), "raw-limit")

    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate-key")
            result[key] = value
        return result

    def number(text):
        value = float(text)
        _require(math.isfinite(value), "nonfinite")
        return value

    def constant(_):
        raise OwnedWorkError("nonfinite")

    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                            parse_float=number, parse_constant=constant)
    except (UnicodeError, ValueError, RecursionError) as error:
        if isinstance(error, OwnedWorkError):
            raise
        raise OwnedWorkError("invalid-json") from None

    def walk(value, depth):
        _require(depth <= MAX_DEPTH, "depth-limit")
        if type(value) is str:
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeError:
                raise OwnedWorkError("invalid-unicode") from None
        elif type(value) is dict:
            for key, child in value.items():
                walk(key, depth + 1)
                walk(child, depth + 1)
        elif type(value) is list:
            for child in value:
                walk(child, depth + 1)
    walk(result, 1)
    _require(type(result) is dict, "object-required")
    return result


def _equal(left, right):
    return type(left) is type(right) and left == right


def _matches(value, schema, root, path):
    try:
        _check(value, schema, root, path)
        return True
    except OwnedWorkError:
        return False


def _check(value, schema, root, path="$"):
    """Interpreter for this fixed embedded schema subset, not arbitrary schemas."""
    if "$ref" in schema:
        ref = schema["$ref"]
        _require(ref.startswith("#/$defs/") and ref.count("/") == 2, "schema-ref")
        _check(value, root["$defs"][ref.split("/")[-1]], root, path)
    if "const" in schema:
        _require(_equal(value, schema["const"]), "schema-const", path)
    if "enum" in schema:
        _require(any(_equal(value, x) for x in schema["enum"]), "schema-enum", path)
    if "type" in schema:
        types = {"object": dict, "array": list, "string": str, "integer": int,
                 "null": type(None)}
        _require(type(value) is types[schema["type"]], "schema-type", path)
    if type(value) is dict:
        _require(set(schema.get("required", ())) <= value.keys(), "schema-required", path)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            _require(value.keys() <= properties.keys(), "schema-extra", path)
        for key, definition in properties.items():
            if key in value:
                _check(value[key], definition, root, path + "." + key)
    if type(value) is list:
        _require(len(value) <= schema.get("maxItems", MAX_BYTES), "schema-items", path)
        if schema.get("uniqueItems"):
            _require(len({canonical_bytes(x) for x in value}) == len(value), "schema-unique", path)
        for child in value:
            _check(child, schema.get("items", {}), root, path + "[]")
    if type(value) is str:
        if "pattern" in schema:
            _require(re.search(schema["pattern"], value) is not None and
                     not value.endswith("\n"), "schema-pattern", path)
        if schema.get("format") == "date-time":
            utc(value)
    if type(value) is int:
        _require(schema.get("minimum", value) <= value <= schema.get("maximum", value),
                 "schema-range", path)
    for child in schema.get("allOf", ()):
        _check(value, child, root, path)
    for keyword in ("anyOf", "oneOf"):
        if keyword in schema:
            count = sum(_matches(value, s, root, path) for s in schema[keyword])
            _require(count == 1 if keyword == "oneOf" else count >= 1,
                     "schema-" + keyword, path)
    if "if" in schema:
        branch = "then" if _matches(value, schema["if"], root, path) else "else"
        _check(value, schema.get(branch, {}), root, path)


def authority_schema() -> dict:
    """A detached copy for compatibility checking; never a schema input."""
    return json.loads(_AUTHORITY_SCHEMA_BYTES)


def parse_authority(raw: bytes) -> dict:
    result = parse_json(raw)
    _check(result, _AUTHORITY_SCHEMA, _AUTHORITY_SCHEMA)
    _require(utc(result["validFromUTC"]) < utc(result["validUntilUTC"]), "invalid-validity")
    return result


@dataclass(frozen=True, slots=True)
class OperatorRegistry:
    """Out-of-wire snapshot supplied by trusted host code, not authenticated here.

    Approved receipts/root digests must come from a separately admitted operator
    path. Constructing this class is not source admission. No callback or JSON
    adapter is supplied. Refresh revocations before every validation call.
    """

    descriptors: tuple[bytes, ...]
    consent_receipts: frozenset[str]
    review_receipts: frozenset[str]
    canonical_roots: frozenset[str]
    revoked_ids: frozenset[str]
    revision: str

    def __post_init__(self):
        object.__setattr__(self, "descriptors", tuple(canonical_bytes(parse_authority(x))
                                                   for x in self.descriptors))
        for name in ("consent_receipts", "review_receipts", "canonical_roots", "revoked_ids"):
            # A bare string would silently become a set of its characters.
            _require(not isinstance(getattr(self, name), (str, bytes)), "registry-type")
            object.__setattr__(self, name, frozenset(getattr(self, name)))
            _require(all(type(x) is str for x in getattr(self, name)), "registry-type")
        _require(type(self.revision) is str and
                 re.fullmatch(r"[0-9a-f]{64}", self.revision) is not None, "registry-revision")
        ids = [parse_authority(x)["authorityId"] for x in self.descriptors]
        _require(len(set(ids)) == len(ids), "registry-conflict")


_CONTEXT_SEAL = object()


@dataclass(frozen=True, slots=True)
class AuthorityContext:
    """Immutable validation context; no execution or capture authorization."""

    descriptor_bytes: bytes
    registry_revision: str
    checked_at_utc: str
    actions: tuple[str, ...]
    _seal: object

    @property
    def descriptor(self) -> dict:
        return json.loads(self.descriptor_bytes)

    @property
    def authority_digest(self) -> str:
        return hashlib.sha256(self.descriptor_bytes).hexdigest()


def resolve_authority(raw: bytes, registry: OperatorRegistry | None, *,
                      source_root_digest: str, scope_digest: str,
                      expected_pins: dict, actions: tuple[str, ...],
                      now_utc: str) -> AuthorityContext:
    """Compare current trusted snapshot and caller-owned binding, fail closed.

    This pure function cannot verify filesystem roots, signature authenticity or
    revocation freshness; the trusted operator adapter must establish those facts.
    It accepts no permissive verifier callback, model registry or implicit fallback.
    """
    _require(type(registry) is OperatorRegistry, "missing-trusted-registry")
    body = parse_authority(raw)
    _require(body["authorityId"] not in registry.revoked_ids, "authority-revoked")
    _require(body["decision"] == "admitted", "authority-not-admitted")
    encoded = canonical_bytes(body)
    _require(encoded in registry.descriptors, "authority-not-registered")
    _require(body["sourceRootDigest"] == source_root_digest and
             source_root_digest in registry.canonical_roots and
             body["scopeDigest"] == scope_digest, "authority-scope")
    _require(set(expected_pins) == {"featureAllowlistDigest", "oracleContractDigest",
                                  "splitProtocolDigest"}, "authority-pins")
    _require(all(body[k] == v for k, v in expected_pins.items()), "authority-pins")
    _require(body["consentReferenceDigest"] in registry.consent_receipts and
             body["reviewRecordDigest"] in registry.review_receipts, "authority-receipts")
    now = utc(now_utc)
    _require(utc(body["validFromUTC"]) <= now < utc(body["validUntilUTC"]), "authority-expired")
    _require(type(actions) is tuple and bool(actions) and len(set(actions)) == len(actions)
             and set(actions) <= set(body["allowedActions"]), "authority-actions")
    return AuthorityContext(encoded, registry.revision, now_utc, actions, _CONTEXT_SEAL)


# Byte-exact semantic copy of the adopted closed schema; no runtime I/O.
_AUTHORITY_SCHEMA_BYTES = (
    '{"type":"object","additionalProperties":false,"required":["schema","decision","authorityId'
    '","sourceKind","sourceRootDigest","scopeDigest","consentReferenceDigest","reviewRecordDige'
    'st","featureAllowlistDigest","oracleContractDigest","splitProtocolDigest","validFromUTC","'
    'validUntilUTC","allowedActions","caps","executionAuthorization","trainingAdmission","colle'
    'ctor047Enabled"],"properties":{"schema":{"const":"agent-braid-owned-work-authority/v1"},"d'
    'ecision":{"enum":["proposed","admitted","denied","revoked"]},"authorityId":{"type":"string'
    '","pattern":"^[0-9a-f]{32}$"},"sourceKind":{"const":"owned-deterministic-development"},"so'
    'urceRootDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"scopeDigest":{"type":"string'
    '","pattern":"^[0-9a-f]{64}$"},"consentReferenceDigest":{"type":"string","pattern":"^[0-9a-'
    'f]{64}$"},"reviewRecordDigest":{"anyOf":[{"type":"string","pattern":"^[0-9a-f]{64}$"},{"ty'
    'pe":"null"}]},"featureAllowlistDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"oracl'
    'eContractDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"},"splitProtocolDigest":{"type'
    '":"string","pattern":"^[0-9a-f]{64}$"},"validFromUTC":{"type":"string","format":"date-time'
    '","pattern":"Z$"},"validUntilUTC":{"type":"string","format":"date-time","pattern":"Z$"},"a'
    'llowedActions":{"type":"array","maxItems":5,"uniqueItems":true,"items":{"enum":["read-meta'
    'data","record-origin","append-outcome","purge","manual-export"]}},"caps":{"type":"object",'
    '"additionalProperties":false,"required":["maxAttempts","maxRecords","maxRecordBytes","maxS'
    'toreBytes","retentionUTCDates"],"properties":{"maxAttempts":{"type":"integer","minimum":1,'
    '"maximum":1000},"maxRecords":{"type":"integer","minimum":1,"maximum":4096},"maxRecordBytes'
    '":{"type":"integer","minimum":1,"maximum":65536},"maxStoreBytes":{"type":"integer","minimu'
    'm":1,"maximum":10485760},"retentionUTCDates":{"type":"integer","minimum":1,"maximum":30}}}'
    ',"executionAuthorization":{"const":false},"trainingAdmission":{"const":false},"collector04'
    '7Enabled":{"const":false}},"allOf":[{"if":{"properties":{"decision":{"const":"admitted"}}}'
    ',"then":{"properties":{"reviewRecordDigest":{"type":"string","pattern":"^[0-9a-f]{64}$"}}}'
    '}],"$schema":"https://json-schema.org/draft/2020-12/schema","$id":"urn:agent-braid:propose'
    'd:owned-work-authority:v1","title":"PROPOSED authority descriptor; bytes never mint '
    'consent"}'
)
_AUTHORITY_SCHEMA = json.loads(_AUTHORITY_SCHEMA_BYTES)
