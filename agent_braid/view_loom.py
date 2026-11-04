# SPDX-License-Identifier: AGPL-3.0-only
"""The agent-braid-loom event contract (v0.1 and v0.2): constants, strict parsing and validation.

One Loom event is one JSON line. This module implements the rules of
specs/061-activity-viewer/contracts/loom-event.schema.json (v0.1, frozen) and
loom-event.v0.2.schema.json without a schema library; tests/test_view_loom.py keeps
them in sync. Both versions are accepted. v0.2 only adds optional `strand.update`
members (`toolDurationMs`, `waitingOn`, `waitingBasis`); a v0.1 event that carries one is
refused, so a stale consumer fails closed. Producers in this package still emit v0.1.
It is deliberately stricter than the schemas in three places: integer fields refuse
floats such as 1.0, text that is not encodable as UTF-8 (lone surrogates) is refused,
and a v0.2 strand never waits on itself. Every event is read-only:
`executionAuthorization` is the constant false and nothing here can grant, run or
schedule anything. A refused line carries a stable reason and a refused stream is
refused as a whole, never as an accepted prefix.
"""
from __future__ import annotations

import json
import math
import re
from typing import Any

SCHEMA_VERSION = "agent-braid-loom/v0.1"  # what this package's adapters emit
SCHEMA_VERSION_V02 = "agent-braid-loom/v0.2"
SCHEMA_VERSIONS = (SCHEMA_VERSION, SCHEMA_VERSION_V02)
TOOL_DURATION_MAX_MS = 86_400_000
WAITING_BASES = ("declared", "observed")
EXECUTION_AUTHORIZATION = False
MAX_LINE_BYTES = 16 * 1024
MAX_EVENTS = 50_000
MAX_SEQ = 9_007_199_254_740_991
TEXT_MAX_LENGTH = 256
EVIDENCE_PATH_MAX_LENGTH = 512

KINDS = (
    "session.origin", "analysis.report", "strand.open", "strand.update", "strand.close",
    "crossing.classified", "wave.planned", "wave.started", "wave.finished",
    "grant.issued", "grant.consumed", "grant.expired", "grant.refused",
    "hazard.noticed", "gate.phase", "gate.result", "runtime.phase", "effort.sample",
    "observation.gap",
)
GAP_REASONS = (
    "subagent-usage-unattributed", "stream-truncated", "shape-unpinned", "source-unsupported",
    "ring-evicted", "host-unverified", "not-observed",
)
AT_BASES = ("viewer-monotonic", "artifact-relative", "sequence-only")
ADAPTERS = (
    "analysis-report", "git-replay-plan", "scheduler-preparation", "runtime-grant", "runtime-state",
    "ownership-notice", "ownership-receipt", "workflow-gate", "host-stream", "otlp-logs",
    "otlp-metrics", "claude-hook", "codex-notify", "codex-hook", "viewer",
)
HOSTS = ("braid", "claude", "codex", "other")
VERIFICATIONS = ("rehashed", "unverified", "derived")

IDENTIFIER_PATTERN = r"^(?:sha256:[0-9a-f]{64}|[A-Za-z0-9][A-Za-z0-9_.:-]{0,63})$"
TEXT_PATTERN = r"^[^\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]*$"
EVIDENCE_PATH_PATTERN = (
    r"^(?![A-Za-z]:)(?!(?:.*/)?\.\.(?:/|$))"
    r"[^/\\\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]"
    r"[^\\\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]*$"
)
SHA256_PATTERN = r"^[0-9a-f]{64}$"

_IDENTIFIER = re.compile(IDENTIFIER_PATTERN)
_TEXT = re.compile(TEXT_PATTERN)
_EVIDENCE_PATH = re.compile(EVIDENCE_PATH_PATTERN)
_SHA256 = re.compile(SHA256_PATTERN)

# Stable refusal reasons. Callers and tests may rely on these names.
REASONS = (
    "not-an-object", "missing-field", "unknown-field", "wrong-type", "out-of-range",
    "too-many-items", "invalid-value", "identifier", "free-text", "evidence-path",
    "evidence-hash", "schema-version", "unknown-kind", "execution-authorization",
    "compatibility-class", "invalid-json", "duplicate-key", "non-finite-number",
    "encoding", "line-too-long", "blank-line", "seq-order", "too-many-events",
)

# Field specs, interpreted by _check: ("ident",), ("text",), ("enum", values),
# ("const", value), ("bool",), ("int", min, max-or-None), ("number", min, max),
# ("null", spec), ("list", item spec, max items), ("object", {field: spec}),
# ("evpath",), ("sha256",) and ("optional", spec). Objects are closed and every field is
# required unless its spec is ("optional", spec), which may be absent but is never null.
IDENT = ("ident",)
TEXT = ("text",)
_HOST = ("enum", HOSTS)
_GRANT = {"grantId": IDENT, "action": ("enum", ("execute", "resume", "abort")), "derived": ("bool",)}
_WAVE = {"scheduleId": IDENT, "wave": ("int", 0, 63), "strands": ("list", IDENT, 256)}
_COUNT = ("int", 0, None)
_TOKENS = ("null", ("int", 0, 1_000_000_000_000))

EVENT_SPEC: dict[str, Any] = {
    "schemaVersion": ("enum", SCHEMA_VERSIONS),
    "seq": ("int", 1, MAX_SEQ),
    "kind": ("enum", KINDS),
    "at": ("object", {"relMs": ("int", 0, MAX_SEQ), "basis": ("enum", AT_BASES)}),
    "source": ("object", {
        "adapter": ("enum", ADAPTERS),
        "evidenceRef": ("null", ("object", {"path": ("evpath",), "sha256": ("sha256",)})),
        "host": _HOST,
        "verification": ("enum", VERIFICATIONS),
    }),
    "assurance": ("object", {"compatibilityClass": ("null", ("int", 0, 5)), "notAGuarantee": ("const", True)}),
    "executionAuthorization": ("const", EXECUTION_AUTHORIZATION),
    "data": ("object", None),
}
EVENT_FIELDS = tuple(EVENT_SPEC)

# The Article 13 class: required for a crossing, fixed for a gate result, null otherwise.
CLASS_REQUIRED_KINDS = ("crossing.classified",)
CLASS_FIXED = {"gate.result": 0}

DATA_SPECS: dict[str, dict[str, Any]] = {
    "session.origin": {
        "mode": ("enum", ("live", "replay")),
        "hosts": ("list", _HOST, 8),
        "limits": ("object", {name: ("int", 1, None)
                              for name in ("strands", "crossings", "waves", "grants", "events")}),
    },
    "analysis.report": {
        "reportId": IDENT,
        "operationCount": ("int", 0, 4096),
        "pairCount": ("int", 0, 8_386_560),
        "summary": ("object", {name: _COUNT
                               for name in ("independentCandidate", "ordered", "conflicting", "unknown")}),
        "uncertainty": ("list", TEXT, 16),
        "limits": ("list", TEXT, 16),
    },
    "strand.open": {
        "strandId": IDENT,
        "host": _HOST,
        "role": ("enum", ("agent", "subagent", "operation", "worker", "unit")),
        "label": TEXT,
        "parentStrandId": ("null", IDENT),
    },
    "strand.update": {
        "strandId": IDENT,
        "state": ("enum", ("running", "waiting", "idle")),
        "toolName": ("null", TEXT),
    },
    "strand.close": {"strandId": IDENT, "outcome": ("enum", ("ok", "failed", "cancelled", "unknown"))},
    "crossing.classified": {
        "reportId": IDENT,
        "left": IDENT,
        "right": IDENT,
        "classification": ("enum", ("ordered", "conflicting", "unknown", "independent-candidate")),
        "sharedResources": ("list", TEXT, 16),
        "reasons": ("list", TEXT, 8),
        "constraints": ("list", TEXT, 8),
        "evidence": ("object", {
            "method": TEXT,
            "coverage": ("list", ("enum", ("complete", "partial", "unknown")), 3),
            "ruleSet": TEXT,
        }),
    },
    "wave.planned": {
        "planId": IDENT,
        "mode": ("enum", ("candidate-preparation-waves", "serial-fallback", "manual-review")),
        "waves": ("list", ("list", IDENT, 256), 64),
        "serialSlots": ("int", 0, 4096),
    },
    "wave.started": dict(_WAVE),
    "wave.finished": dict(_WAVE),
    "grant.issued": dict(_GRANT),
    "grant.consumed": dict(_GRANT),
    "grant.expired": dict(_GRANT),
    "grant.refused": dict(_GRANT),
    "hazard.noticed": {
        "units": ("list", IDENT, 128),
        "hazardKind": ("enum", (
            "read-write", "write-write", "create-collision", "undeclared-write", "sibling-area-write",
            "partial-coverage", "shared-resource", "base-mismatch", "not-observed", "unattributed-writer",
        )),
        "stage": ("enum", ("preflight", "receipt")),
    },
    "gate.phase": {
        "gateId": IDENT,
        "phase": ("enum", ("validate", "analyze", "baseline", "finalize", "report")),
        "status": ("enum", ("ok", "skipped", "refused", "busy", "failed", "inconclusive", "not-run")),
    },
    "gate.result": {
        "gateId": IDENT,
        "status": ("enum", ("refused", "busy", "inconclusive", "hazards-found", "ok-analyzed", "ok-certified")),
        "operationCount": ("int", 0, 4096),
    },
    "runtime.phase": {
        "manifestDigest": IDENT,
        "phase": ("enum", ("initializing", "ready", "applying", "completed", "aborting", "aborted")),
    },
    "effort.sample": {
        "strandId": IDENT,
        "basis": ("const", "host-estimate"),
        "model": ("null", TEXT),
        "inputTokens": _TOKENS,
        "outputTokens": _TOKENS,
        "cacheReadTokens": _TOKENS,
        "cacheCreationTokens": _TOKENS,
        "cachedInputTokens": _TOKENS,
        "reasoningTokens": _TOKENS,
        "costUsd": ("null", ("number", 0, 1_000_000.0)),
        "durationMs": _TOKENS,
    },
    "observation.gap": {
        "reason": ("enum", GAP_REASONS),
        "strandId": ("null", IDENT),
        "fromSeq": ("null", ("int", 1, MAX_SEQ)),
        "toSeq": ("null", ("int", 1, MAX_SEQ)),
    },
}


# v0.2 (contract amendment T052): additive optional members only; every other kind is v0.1.
DATA_SPECS_V02: dict[str, dict[str, Any]] = {
    **DATA_SPECS,
    "strand.update": {
        **DATA_SPECS["strand.update"],
        "toolDurationMs": ("optional", ("int", 0, TOOL_DURATION_MAX_MS)),
        "waitingOn": ("optional", IDENT),
        "waitingBasis": ("optional", ("enum", WAITING_BASES)),
    },
}
DATA_SPECS_BY_VERSION = {SCHEMA_VERSION: DATA_SPECS, SCHEMA_VERSION_V02: DATA_SPECS_V02}


class LoomError(ValueError):
    """A line, event or stream was refused; `reason` is one of REASONS."""

    def __init__(self, reason: str, detail: str, line: int | None = None) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail
        self.line = line


def _fail(reason: str, path: str, message: str) -> LoomError:
    return LoomError(reason, f"{path or 'event'}: {message}")


def _check_str(value: Any, path: str) -> None:
    if not isinstance(value, str):
        raise _fail("wrong-type", path, "expected text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise _fail("encoding", path, "lone surrogate is not UTF-8") from None


def _is_int(value: Any) -> bool:
    return type(value) is int


def _check(spec: tuple, value: Any, path: str) -> None:
    tag = spec[0]
    if tag in ("ident", "text", "evpath"):
        _check_str(value, path)
    if tag == "ident":
        if not _IDENTIFIER.fullmatch(value):
            raise _fail("identifier", path, "neither a short ID nor a sha256: digest")
    elif tag == "text":
        if len(value) > TEXT_MAX_LENGTH or not _TEXT.fullmatch(value):
            raise _fail("free-text", path, "too long or holds a control or bidirectional character")
    elif tag == "enum":
        if not isinstance(value, str) or value not in spec[1]:
            raise _fail("invalid-value", path, "not one of the closed values")
    elif tag == "const":
        if type(value) is not type(spec[1]) or value != spec[1]:
            raise _fail("invalid-value", path, f"must be {spec[1]!r}")
    elif tag == "bool":
        if type(value) is not bool:
            raise _fail("wrong-type", path, "expected a boolean")
    elif tag == "int":
        if not _is_int(value):
            raise _fail("wrong-type", path, "expected an integer")
        if value < spec[1] or (spec[2] is not None and value > spec[2]):
            raise _fail("out-of-range", path, "integer outside its bounds")
    elif tag == "number":
        if not _is_int(value) and type(value) is not float:
            raise _fail("wrong-type", path, "expected a number")
        if (type(value) is float and not math.isfinite(value)) or value < spec[1] or value > spec[2]:
            raise _fail("out-of-range", path, "number outside its bounds or not finite")
    elif tag == "null":
        if value is not None:
            _check(spec[1], value, path)
    elif tag == "list":
        if not isinstance(value, list):
            raise _fail("wrong-type", path, "expected an array")
        if len(value) > spec[2]:
            raise _fail("too-many-items", path, f"more than {spec[2]} items")
        for index, item in enumerate(value):
            _check(spec[1], item, f"{path}[{index}]")
    elif tag == "object":
        _check_object(spec[1], value, path)
    elif tag == "optional":
        _check(spec[1], value, path)
    elif tag == "evpath":
        if len(value) > EVIDENCE_PATH_MAX_LENGTH or not _EVIDENCE_PATH.fullmatch(value):
            raise _fail("evidence-path", path, "not a relative path without '..', backslash or control characters")
    elif tag == "sha256":
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise _fail("evidence-hash", path, "not 64 lowercase hexadecimal digits")
    else:  # pragma: no cover - a spec typo is a programming error
        raise AssertionError(tag)


def _check_object(fields: dict[str, Any] | None, value: Any, path: str) -> None:
    if not isinstance(value, dict):
        raise _fail("wrong-type", path, "expected an object")
    if fields is None:
        return
    missing = [name for name, spec in fields.items() if name not in value and spec[0] != "optional"]
    if missing:
        raise _fail("missing-field", path, f"missing {', '.join(missing)}")
    extra = sorted(str(name) for name in value if name not in fields)
    if extra:
        raise _fail("unknown-field", path, f"unknown {', '.join(extra)}")
    for name, spec in fields.items():
        if name in value:
            _check(spec, value[name], f"{path}.{name}" if path else name)


def validate_event(event: Any) -> Any:
    """Return `event` when it follows the contract; raise LoomError otherwise."""
    if not isinstance(event, dict):
        raise LoomError("not-an-object", "an event is a JSON object")
    if event.get("executionAuthorization") is not False:
        raise _fail("execution-authorization", "executionAuthorization", "must be present and false")
    version = event.get("schemaVersion")
    if not isinstance(version, str) or version not in DATA_SPECS_BY_VERSION:
        raise _fail("schema-version", "schemaVersion", f"must be one of {', '.join(SCHEMA_VERSIONS)}")
    specs = DATA_SPECS_BY_VERSION[version]
    kind = event.get("kind")
    if not isinstance(kind, str) or kind not in specs:
        raise _fail("unknown-kind", "kind", "not one of the closed event kinds")
    _check_object(EVENT_SPEC, event, "")
    _check_class(kind, event["assurance"]["compatibilityClass"])
    _check_object(specs[kind], event["data"], "data")
    if kind == "strand.update":
        _check_waiting(event["data"])
    return event


def _check_waiting(data: dict[str, Any]) -> None:
    """v0.2: `waitingOn` names a target only while waiting and always comes with its basis."""
    if ("waitingOn" in data) != ("waitingBasis" in data):
        raise _fail("missing-field", "data", "waitingOn and waitingBasis come together")
    if "waitingOn" in data and data["state"] != "waiting":
        raise _fail("invalid-value", "data.waitingOn", "allowed only when state is waiting")
    if data.get("waitingOn") == data["strandId"]:
        raise _fail("invalid-value", "data.waitingOn", "a strand does not wait on itself")


def _check_class(kind: str, value: Any) -> None:
    if kind in CLASS_REQUIRED_KINDS:
        if value is None:
            raise _fail("compatibility-class", "assurance.compatibilityClass", f"{kind} carries an integer class 0 to 5")
    elif kind in CLASS_FIXED:
        if value != CLASS_FIXED[kind] or not _is_int(value):
            raise _fail("compatibility-class", "assurance.compatibilityClass", f"{kind} carries class {CLASS_FIXED[kind]}")
    elif value is not None:
        raise _fail("compatibility-class", "assurance.compatibilityClass", f"{kind} carries no class")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LoomError("duplicate-key", f"duplicate JSON member: {key}")
        result[key] = value
    return result


def _constant(token: str) -> None:
    raise LoomError("non-finite-number", f"non-finite JSON number: {token}")


def _float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise LoomError("non-finite-number", f"non-finite JSON number: {token}")
    return value


def _decode(line: bytes | str) -> Any:
    if isinstance(line, str):
        try:
            line = line.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise LoomError("encoding", "text is not encodable as UTF-8") from exc
    if line.endswith(b"\n"):
        line = line[:-1]
    if len(line) > MAX_LINE_BYTES:
        raise LoomError("line-too-long", f"a line is at most {MAX_LINE_BYTES} bytes")
    if b"\n" in line or b"\r" in line:
        raise LoomError("invalid-json", "an event is exactly one line")
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LoomError("encoding", "line is not UTF-8") from exc
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
    except LoomError:
        raise
    except (ValueError, RecursionError) as exc:
        raise LoomError("invalid-json", "line is not a single JSON value") from exc


def parse_event(line: bytes | str) -> dict[str, Any]:
    """Parse one line strictly (no duplicate members, no non-finite numbers) and validate it."""
    event = _decode(line)
    validate_event(event)
    return event


def parse_stream(data: bytes) -> list[dict[str, Any]]:
    """Parse a whole JSON Lines stream, or raise: no prefix of a refused stream is returned."""
    events: list[dict[str, Any]] = []
    last_seq = 0
    start = 0
    number = 0
    while start < len(data):
        end = data.find(b"\n", start)
        end = len(data) if end < 0 else end
        number += 1
        line = data[start:end]
        start = end + 1
        try:
            if not line:
                raise LoomError("blank-line", "blank lines are not events")
            if len(events) >= MAX_EVENTS:
                raise LoomError("too-many-events", f"a stream holds at most {MAX_EVENTS} events")
            event = parse_event(line)
            if event["seq"] <= last_seq:
                raise LoomError("seq-order", f"seq {event['seq']} does not exceed {last_seq}")
        except LoomError as exc:
            exc.line = number
            raise
        last_seq = event["seq"]
        events.append(event)
    return events


def canonical_bytes(event: dict[str, Any]) -> bytes:
    """The one serialisation of a valid event: sorted compact JSON, UTF-8, newline-terminated."""
    validate_event(event)
    try:
        body = json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LoomError("encoding", "text is not encodable as UTF-8") from exc
    if len(body) > MAX_LINE_BYTES:
        raise LoomError("line-too-long", f"a line is at most {MAX_LINE_BYTES} bytes")
    return body + b"\n"
