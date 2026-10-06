# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, synthetic-only recorded metadata projection into existing AIM.

The pure byte importer never reads files, writes artifacts or dispatches work.
The optional local reader and destination validator admit owned POSIX paths;
hostile same-UID mutation of ancestor directories is outside this boundary.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat

from agent_braid.analysis import EFFECT_KINDS, InvalidAnalysis, analyze

VERSION = "0.1.0-experimental"
MAPPER = "generic-metadata-v1"
MAX_BYTES = 1024 * 1024
MAX_OPERATIONS = 64
MAX_EVENTS = 512
MAX_DEPTH = 16
MAX_STRING = 256
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,255}$")
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
STATUSES = {"completed", "started", "approved", "rejected", "paused", "resumed", "deferred", "unknown"}


class InvalidTrace(ValueError):
    """Input or local artifact destination violates the import contract."""


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise InvalidTrace(code)


def canonical_bytes(value: object) -> bytes:
    """Serialize artifacts deterministically, without clocks or local paths."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


@dataclass(frozen=True)
class TraceArtifacts:
    """Independent AIM projection, existing report, and import provenance."""
    projection: list[dict]
    report: dict
    provenance: dict

    @property
    def report_bytes(self) -> bytes:
        return canonical_bytes(self.report)

    @property
    def provenance_bytes(self) -> bytes:
        return canonical_bytes(self.provenance)

    @property
    def projection_bytes(self) -> bytes:
        return canonical_bytes(self.projection)


def _object(value: object, required: set[str], optional: set[str] | None = None) -> dict:
    _require(isinstance(value, dict), "expected-object")
    _require(required <= set(value) <= required | (optional or set()), "invalid-fields")
    return value


def _token(value: object) -> str:
    _require(isinstance(value, str) and TOKEN.fullmatch(value) is not None,
             "invalid-metadata-token")
    return value


def _digest(value: object) -> str:
    _require(isinstance(value, str) and DIGEST.fullmatch(value) is not None, "invalid-source-digest")
    return value


def _members(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate-json-member")
        result[key] = value
    return result


def _bounds(value: object, depth: int = 1) -> None:
    _require(depth <= MAX_DEPTH, "nesting-limit")
    if isinstance(value, str):
        _require(len(value) <= MAX_STRING, "metadata-string-limit")
    elif isinstance(value, dict):
        for key, item in value.items():
            _bounds(key, depth + 1)
            _bounds(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _bounds(item, depth + 1)


def _reject_constant(_: str) -> None:
    raise InvalidTrace("nonfinite-json-number")


def _parse(data: bytes) -> dict:
    _require(isinstance(data, bytes), "expected-utf8-bytes")
    _require(len(data) <= MAX_BYTES, "input-byte-limit")
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_members,
                           parse_constant=_reject_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, InvalidTrace):
            raise
        raise InvalidTrace("invalid-json") from None
    _bounds(value)
    return _object(value, {"traceImportVersion", "source", "mapper", "admission", "operations", "events"})


def _effects(value: object, losses: list[str]) -> dict:
    if value is None:
        losses.append("missing-effect-footprint")
        return {"declared": [], "inferred": [], "observed": [],
                "coverage": {"status": "unknown", "domain": "recorded-metadata", "method": "missing"}}
    effects = _object(value, set(), {"declared", "inferred", "observed", "coverage"})
    result = {}
    for channel in ("declared", "inferred", "observed"):
        records = effects.get(channel, [])
        _require(isinstance(records, list), "invalid-effect-channel")
        if channel not in effects:
            losses.append("missing-" + channel + "-channel")
        result[channel] = []
        for item in records:
            item = _object(item, {"kind", "resource"})
            _require(isinstance(item["kind"], str) and item["kind"] in EFFECT_KINDS,
                     "invalid-effect-kind")
            result[channel].append({"kind": item["kind"], "resource": _token(item["resource"])})
    coverage = effects.get("coverage")
    if coverage is None:
        _require("coverage" not in effects, "invalid-coverage")
        losses.append("missing-effect-coverage")
        coverage = {"status": "unknown", "domain": "recorded-metadata", "method": "missing"}
    else:
        coverage = _object(coverage, {"status", "domain", "method"})
        _require(isinstance(coverage["status"], str) and
                 coverage["status"] in {"complete", "partial", "unknown"}, "invalid-coverage")
        coverage = {"status": coverage["status"], "domain": _token(coverage["domain"]),
                    "method": _token(coverage["method"])}
    if losses:
        coverage = {**coverage, "status": "unknown"}
    result["coverage"] = coverage
    return result


def import_trace(data: bytes, *, mapper: str) -> TraceArtifacts:
    """Admit bounded synthetic metadata and analyze its conservative AIM projection.

    Diagnostics are fixed codes: rejected values, field names and paths are never
    included. Source content digests bind recorded metadata, not missing original
    prompt/argument bodies. No caller-owned objects are mutated.
    """
    _require(mapper == MAPPER, "unsupported-mapper")
    value = _parse(data)
    _require(value["traceImportVersion"] == VERSION, "unsupported-import-version")
    _require(value["mapper"] == MAPPER, "mapper-mismatch")
    _require(value["admission"] == {"kind": "synthetic"}, "source-not-admitted")
    source = _object(value["source"], {"kind", "schemaVersion", "contentDigest"})
    _require(source["kind"] == "generic-metadata" and source["schemaVersion"] == VERSION,
             "unsupported-source-version")
    operations, events = value["operations"], value["events"]
    _require(isinstance(operations, list) and 1 <= len(operations) <= MAX_OPERATIONS,
             "operation-limit")
    _require(isinstance(events, list) and len(events) <= MAX_EVENTS, "event-limit")
    content_digest = _digest(source["contentDigest"])
    _require(content_digest == digest_bytes(canonical_bytes({"operations": operations, "events": events})),
             "source-content-digest-mismatch")
    projection, mappings = [], []
    instances, attempts, definitions = set(), set(), {}
    for operation in operations:
        op = _object(operation, {"instanceId", "attemptId", "definition", "inputDigest"},
                     {"dependencies", "readVersions", "effects"})
        instance, attempt = _token(op["instanceId"]), _token(op["attemptId"])
        _require(instance not in instances and attempt not in attempts, "duplicate-instance-or-attempt")
        instances.add(instance)
        attempts.add(attempt)
        definition = _object(op["definition"], {"id", "digest"})
        definition = {"id": _token(definition["id"]), "digest": _digest(definition["digest"])}
        _require(definition["id"] not in definitions or definitions[definition["id"]] == definition["digest"],
                 "inconsistent-definition-digest")
        definitions[definition["id"]] = definition["digest"]
        losses = []
        dependencies = op.get("dependencies", [])
        _require(isinstance(dependencies, list), "invalid-dependencies")
        dependencies = [_token(item) for item in dependencies]
        if "dependencies" not in op:
            losses.append("missing-dependency-coverage")
        versions = op.get("readVersions", {})
        _require(isinstance(versions, dict), "invalid-read-versions")
        versions = {_token(key): version for key, version in versions.items()}
        _require(all(type(version) is int and version >= 0 for version in versions.values()),
                 "invalid-read-version")
        if "readVersions" not in op:
            losses.append("missing-read-version-coverage")
        if "effects" in op:
            _require(isinstance(op["effects"], dict), "invalid-effects")
        effects = _effects(op.get("effects"), losses)
        if not any(effects[channel] for channel in ("declared", "inferred", "observed")):
            losses.append("no-known-effect")
        for channel in ("declared", "inferred", "observed"):
            if any(item["kind"] == "read" and item["resource"] not in versions for item in effects[channel]):
                losses.append("missing-read-resource-version")
        if losses:
            effects["coverage"] = {**effects["coverage"], "status": "unknown"}
        projection.append({"aimVersion": "0.2.0-draft", "instanceId": instance,
                           "attemptId": attempt, "definition": definition,
                           "inputDigest": _digest(op["inputDigest"]),
                           "dependencies": dependencies, "readVersions": versions,
                           "effects": effects,
                           "evidence": [{"property": "independence", "method": "declared",
                                         "domain": "synthetic-recorded-metadata",
                                         "assumptions": ["source-metadata-is-declared-not-verified"],
                                         "observationContract": "exact-resource-footprints-v1",
                                         "executionContract": "read-only-no-execution",
                                         "assuranceClass": 0}]})
        mappings.append({"instanceId": instance, "attemptId": attempt,
                         "definitionId": definition["id"], "definitionDigest": definition["digest"],
                         "inputDigest": op["inputDigest"], "losses": losses})
    by_instance = {op["instanceId"]: op for op in projection}
    by_mapping = {item["instanceId"]: item for item in mappings}
    event_ids, retained_events = set(), []
    for event in events:
        event = _object(event, {"eventId", "instanceId", "attemptId", "status"}, {"timestamp"})
        event_id, instance, attempt = (_token(event[key]) for key in ("eventId", "instanceId", "attemptId"))
        _require(event_id not in event_ids, "duplicate-event-id")
        event_ids.add(event_id)
        _require(instance in by_instance and by_instance[instance]["attemptId"] == attempt,
                 "event-identity-mismatch")
        _require(isinstance(event["status"], str) and event["status"] in STATUSES,
                 "unsupported-event-status")
        if "timestamp" in event:
            _token(event["timestamp"])
        retained_events.append(dict(event))
        # Lifecycle is not a completion/effect certificate. Unsupported timeline
        # projection remains explicit even if other events claim completion.
        if event["status"] != "completed" or not any(
                by_instance[instance]["effects"][channel] for channel in ("declared", "inferred", "observed")):
            by_mapping[instance]["losses"].append("lifecycle-not-an-effect-certificate")
            by_instance[instance]["effects"]["coverage"]["status"] = "unknown"
    projection.sort(key=lambda op: op["instanceId"])
    for item in mappings:
        item["losses"] = sorted(set(item["losses"]))
        item["coverage"] = by_instance[item["instanceId"]]["effects"]["coverage"]["status"]
    try:
        report = analyze(projection)
    except InvalidAnalysis:
        raise InvalidTrace("invalid-aim-projection") from None
    provenance = {
        "traceProvenanceVersion": VERSION, "mapper": MAPPER, "source": dict(source),
        "admission": {"kind": "synthetic"},
        "sourceFileDigest": digest_bytes(data),
        "sourceFileDigestMethod": "local-sha256-raw-file",
        "sourceContentDigestMethod": "source-declared-sha256-canonical-recorded-metadata-verified-locally",
        "projectionDigest": digest_bytes(canonical_bytes(projection)),
        "reportDigest": digest_bytes(canonical_bytes(report)),
        "reportInputDigest": report["inputDigest"],
        "mappings": sorted(mappings, key=lambda item: item["instanceId"]),
        "events": retained_events,
        "limits": {"maxBytes": MAX_BYTES, "maxOperations": MAX_OPERATIONS,
                   "maxEvents": MAX_EVENTS, "maxDepth": MAX_DEPTH, "maxString": MAX_STRING,
                   "attemptsPerInstance": 1, "realSourceAdmission": False},
        "executionAuthorization": False,
        "scientificLimits": ["Synthetic declared metadata only; no verified real effects or provider conformance.",
                             "No execution authorization, general confluence or Yang-Baxter claim."]}
    return TraceArtifacts(projection, report, provenance)


def _local_path(path: str | Path) -> Path:
    raw = str(path)
    _require(bool(raw) and "://" not in raw and "\x00" not in raw, "invalid-local-path")
    absolute = Path(os.path.abspath(raw))
    for component in (*reversed(absolute.parents), absolute):
        _require(not component.is_symlink(), "symlink-path-refused")
    return absolute


def read_trace(path: str | Path) -> bytes:
    """Read one bounded regular local file, rejecting symlinks and special files."""
    path = _local_path(path)
    descriptor = None
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        metadata = os.fstat(descriptor)
        _require(stat.S_ISREG(metadata.st_mode), "source-not-regular-file")
        _require(metadata.st_size <= MAX_BYTES, "input-byte-limit")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = None
            data = handle.read(MAX_BYTES + 1)
        _require(len(data) <= MAX_BYTES, "input-byte-limit")
        return data
    except OSError:
        raise InvalidTrace("source-read-failed") from None
    finally:
        if descriptor is not None:
            os.close(descriptor)


def validate_destination(source: str | Path, destination: str | Path) -> Path:
    """Check a new owned local output path; the CLI must create it exclusively."""
    source, destination = _local_path(source), _local_path(destination)
    _require(source != destination, "output-source-collision")
    _require(not destination.exists(), "output-already-exists")
    _require(destination.parent.is_dir(), "output-parent-missing")
    return destination
