# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T005 per-host hook and plugin adapters (offline, blocked, doubles only).

Validates task-local hook (C6) and plugin (C7) component sets
(``braid-harness-hooks/v0.1``) against independent per-host event matrices and
dispatches synthetic events to caller-supplied deterministic doubles, under the
frozen capability profile contract (specs/050-braid-harness-adaptation/contracts/
interface.md). The module reads no file, starts no process, opens no network
connection, writes no host setting and issues no grant. Every record keeps
``executionAuthorization`` false and every receipt keeps ``nativeExecution`` false.

Admission is not decided here: ``harness_components.derive_admission`` makes C6 and
C7 ``blocked`` (no containment qualification), so no hook set is ever ``implemented``,
``qualified`` or ``enabled``. Dispatch exercises the adapter logic against doubles
only; a double is not a host, and nothing here qualifies either host.

The event matrices are *modeled, not observed*: the contract (section 4, open
question 3) says event schemas per host build are not yet inventoried, and no host
was run for this task. The Claude matrix lists a small modeled subset of events;
the Codex matrix is empty (not installed, refused). The two matrices are separate
records, a hook set binds to one host, and a forged or edited matrix refuses by
exact comparison with the built-in record. Events outside a host's modeled set
stay ``unavailable`` (meaning not modeled here, not that the host lacks them) and
cannot be declared or dispatched. C7 models only a multi-event hook bundle: plugin
tool-loop changes have no field and refuse as unknown keys. The ceilings below
(entries, emits, ledger, note, payload) are module-local provisional bounds, not
owner-approved limits.

A hook or plugin double receives an immutable event view and a context that can
only request a follow-up event and read the cancellation flag. Its result is exactly
``{"decision": "allow"|"deny", "note": str}``; ``allow`` carries no authority, a
``deny`` only tightens, and any other key or decision is an escalation attempt that
fails that hook without being applied. Failures and timeouts are isolated per hook;
a per-hook ``onFailure`` of ``deny`` fails closed for that event only, also when
the hook was skipped by the dispatch budget. A deny outranks a cancellation.
The replay ledger records an event only after its dispatch completed without
cancellation, so a cancelled event can be retried. Timeouts are checked after a
double returns; nothing is preempted.
Only a row whose ``decision`` is ``allow`` means allow: duplicate, rejected and
cancelled rows carry ``None`` and must not be read as allow. Follow-up
events are bounded by depth and a recursion check on the active hook chain.
In-process doubles are trusted test code: they can still reach Python facilities
directly, and enforced containment is a later qualification, not this module.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from time import monotonic_ns
from typing import Any, NoReturn

from .harness_components import (
    HOST_SUPPORT, HOSTS, ProfileError, _ID, _hash, _keys, _parse, _provenance, _require,
    derive_admission)
from .harness_tools import MAX_INT, MAX_STRING
from .system_one import canonical, digest, freeze, thaw

FORMAT = "braid-harness-hooks/v0.1"
SPEC_FORMAT = "braid-harness-hooks-spec/v0.1"
MATRIX_FORMAT = "braid-harness-hook-matrix/v0.1"
POLICIES = {"event": "host-matrix-v1", "result": "deny-only-v1", "failure": "isolated-v1"}
EVENT_VOCAB = ("PermissionRequest", "PostToolUse", "PreCompact", "PreToolUse",
               "SessionStart", "Stop")
_MODELED = {"claude": ["PostToolUse", "PreToolUse", "SessionStart", "Stop"], "codex": []}
CEILINGS = {"maxEvents": 64, "maxDispatches": 128, "maxDepth": 2, "timeoutMs": 1000,
            "maxPayloadBytes": 2048}
MAX_ENTRIES = 16
MAX_PLUGIN_EVENTS = 4
MAX_PRIORITY = 1000
MAX_EMITS = 4
MAX_LEDGER = 256
MAX_NOTE = 256
MAX_PAYLOAD_KEYS = 8
DECISIONS = ("allow", "deny")
FAILURE_POLICIES = ("ignore", "deny")
_SPEC_KEYS = {"format", "hooksetId", "version", "componentClass", "host", "effectClass",
              "entries", "limits", "provenance", "executionAuthorization"}
_CONTRACT_KEYS = _SPEC_KEYS | {"hostSupport", "matrixSha256", "inputSha256", "policies",
                               "admission"}
_ENTRY_KEYS = {"id", "events", "priority", "onFailure"}
_EVENT_KEYS = {"eventId", "seq", "event", "payload"}
_RESULT_KEYS = {"decision", "note"}


def matrix_record(host: str) -> dict:
    """Return the built-in event matrix of one host (modeled, never observed)."""
    _require(host in HOSTS, "unknown-host")
    modeled = _MODELED[host]
    return {"format": MATRIX_FORMAT, "host": host,
            "observedBuild": HOST_SUPPORT[host]["observedBuild"],
            "observation": "modeled-not-observed", "modeled": list(modeled),
            "unavailable": [e for e in EVENT_VOCAB if e not in modeled],
            "qualification": "unqualified", "executionAuthorization": False}


def matrix_sha256(host: str) -> str:
    """Return the SHA-256 of the canonical built-in matrix of one host."""
    return sha256(canonical(matrix_record(host))).hexdigest()


def event_status(host: str, event: str) -> str:
    """Return ``modeled``, ``unavailable`` or ``unknown`` for this host only."""
    _require(host in HOSTS, "unknown-host")
    if event not in EVENT_VOCAB:
        return "unknown"
    return "modeled" if event in _MODELED[host] else "unavailable"


def _known_event(host: str, event: Any) -> None:
    status = event_status(host, event) if type(event) is str else "unknown"
    _require(status != "unknown", "event-unknown")
    _require(status == "modeled", "event-unavailable")


def verify_matrix(raw: bytes, *, expected_sha256: str) -> dict:
    """Reparse a matrix and compare it with its trusted hash and the built-in record."""
    _hash(expected_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _require(sha256(canonical(value)).hexdigest() == expected_sha256, "matrix-drift")
    host = value.get("host")
    _require(host in HOSTS and canonical(value) == canonical(matrix_record(host)),
             "matrix-forged")
    return value


def _entries(value: Any, component_class: str, host: str) -> None:
    _require(type(value) is list and value, "invalid-entry")
    _require(len(value) <= MAX_ENTRIES, "inventory-budget-exceeded")
    limit = 1 if component_class == "C6" else MAX_PLUGIN_EVENTS
    for row in value:
        _keys(row, _ENTRY_KEYS, "invalid-entry")
        events = row["events"]
        _require(type(row["id"]) is str and _ID.fullmatch(row["id"]) is not None
                 and type(row["priority"]) is int and 0 <= row["priority"] <= MAX_PRIORITY
                 and row["onFailure"] in FAILURE_POLICIES
                 and type(events) is list and 1 <= len(events) <= limit
                 and all(type(e) is str for e in events)
                 and events == sorted(events) and len(set(events)) == len(events),
                 "invalid-entry")
        for event in events:
            _known_event(host, event)
    ids = [row["id"] for row in value]
    _require(ids == sorted(ids) and len(set(ids)) == len(ids),
             "duplicate-or-unordered-inventory")
    _require(len({i.casefold() for i in ids}) == len(ids), "path-alias")


def _limits(value: Any) -> None:
    _keys(value, set(CEILINGS), "invalid-limits")
    for name, ceiling in CEILINGS.items():
        low = 0 if name == "maxDepth" else 1
        _require(type(value[name]) is int and low <= value[name] <= ceiling,
                 "limits-exceed-ceiling")


def _admission(component_class: str, effect_class: str) -> dict:
    state, blocker = derive_admission(component_class, effect_class)
    return {"state": state, "blocker": blocker}


def _body(value: dict) -> None:
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    _require(type(value["hooksetId"]) is str and _ID.fullmatch(value["hooksetId"]) is not None,
             "invalid-id")
    _require(type(value["version"]) is int and value["version"] == 1, "invalid-version")
    _require(value["componentClass"] in ("C6", "C7"), "unknown-class")
    _require(value["host"] in HOSTS, "unknown-host")
    _require(value["host"] == "claude", "host-refused")
    _admission(value["componentClass"], value["effectClass"])
    _entries(value["entries"], value["componentClass"], value["host"])
    _limits(value["limits"])
    _provenance(value["provenance"])


@dataclass(frozen=True)
class HookSet:
    """Immutable parsed hook or plugin set; construction is not verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return thaw(self.data)


def parse_hookset(raw: bytes) -> HookSet:
    """Parse strict bounded JSON and revalidate every hook set invariant."""
    value = _parse(raw)
    _keys(value, _CONTRACT_KEYS)
    _require(value["format"] == FORMAT, "unsupported-version")
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    _require(canonical(value["hostSupport"]) == canonical(HOST_SUPPORT), "host-build-drift")
    _body(value)
    _require(value["matrixSha256"] == matrix_sha256(value["host"]), "matrix-forged")
    _hash(value["inputSha256"])
    _require(canonical(value["policies"]) == canonical(POLICIES), "unsupported-profile")
    _require(canonical(value["admission"]) ==
             canonical(_admission(value["componentClass"], value["effectClass"])),
             "admission-mismatch")
    return HookSet(freeze(value), canonical(value))


def verify_hookset(raw: bytes, *, expected_sha256: str) -> HookSet:
    """Reparse and compare a trusted full identity; equality is not authority."""
    _hash(expected_sha256, "invalid-expected-hash")
    hookset = parse_hookset(raw)
    _require(hookset.sha256 == expected_sha256, "hookset-drift")
    return hookset


def compile_hookset(raw: bytes, *, expected_input_sha256: str) -> HookSet:
    """Compile one trusted spec into an immutable, blocked, non-enabled hook set."""
    _hash(expected_input_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _require(sha256(canonical(value)).hexdigest() == expected_input_sha256, "input-drift")
    _keys(value, _SPEC_KEYS)
    _require(value["format"] == SPEC_FORMAT, "unsupported-version")
    _body(value)
    contract = {**value, "format": FORMAT, "hostSupport": thaw(HOST_SUPPORT),
                "matrixSha256": matrix_sha256(value["host"]),
                "inputSha256": expected_input_sha256, "policies": dict(POLICIES),
                "admission": _admission(value["componentClass"], value["effectClass"])}
    return parse_hookset(canonical(contract))


class ReplayLedger:
    """Record of dispatched event ids shared across runs (bounded by ``run_events``)."""

    def __init__(self) -> None:
        self._seen: dict[str, str] = {}
        self._next_seq = 0
        self._busy = False

    @property
    def size(self) -> int:
        return len(self._seen)

    @property
    def next_seq(self) -> int:
        return self._next_seq

    @property
    def sha256(self) -> str:
        return digest({"seen": sorted(self._seen.items()), "nextSeq": self._next_seq})

    def _recall(self, event_id: str) -> str | None:
        return self._seen.get(event_id)

    def _remember(self, event_id: str, identity: str) -> None:
        self._seen[event_id] = identity
        self._next_seq += 1


def _no_surrogates(text: str) -> bool:
    return not any(0xD800 <= ord(c) <= 0xDFFF for c in text)


def _payload(value: Any) -> dict:
    _require(type(value) is dict and len(value) <= MAX_PAYLOAD_KEYS, "invalid-event")
    for key, item in value.items():
        _require(type(key) is str and _ID.fullmatch(key) is not None
                 and type(item) in (str, int, bool), "invalid-event")
        if type(item) is str:
            _require(len(item) <= MAX_STRING and
                     _no_surrogates(item), "invalid-event")
        elif type(item) is int:
            _require(abs(item) <= MAX_INT, "invalid-event")
    return value


def _event(value: Any) -> None:
    _keys(value, _EVENT_KEYS, "invalid-event")
    _require(type(value["eventId"]) is str and _ID.fullmatch(value["eventId"]) is not None
             and type(value["event"]) is str and _ID.fullmatch(value["event"]) is not None
             and type(value["seq"]) is int and 0 <= value["seq"] <= MAX_INT, "invalid-event")
    _payload(value["payload"])


def _result_note(value: Any) -> str:
    """Validate a hook result; anything beyond allow/deny plus a note is refused."""
    _require(type(value) is dict, "invalid-result")
    keys = set(value)
    _require(not keys - _RESULT_KEYS, "escalation-attempt")
    _require(keys == _RESULT_KEYS and type(value["decision"]) is str
             and type(value["note"]) is str, "invalid-result")
    _require(value["decision"] in DECISIONS, "escalation-attempt")
    note = value["note"]
    _require(len(note) <= MAX_NOTE and _no_surrogates(note), "invalid-result")
    return note


class HookContext:
    """Per-hook handle: may request a follow-up event and read the cancellation flag.

    Closed when the hook returns. Trusted doubles can still reach private state.
    """

    def __init__(self, run: _Run):
        self._run = run
        self._start = run.clock()
        self._emitted: list[tuple[str, dict]] = []
        self._closed = False
        self._violation: str | None = None

    def _refuse(self, reason: str) -> NoReturn:
        if self._violation is None:
            self._violation = reason
        raise ProfileError(reason)

    def emit(self, event: str, payload: Mapping[str, Any]) -> None:
        if self._closed:
            raise ProfileError("context-closed")
        if self._run.clock() - self._start > self._run.timeout_ns:
            self._refuse("timeout")
        if len(self._emitted) >= MAX_EMITS:
            self._refuse("emit-budget-exceeded")
        try:
            _require(type(event) is str and _ID.fullmatch(event) is not None, "invalid-event")
            _known_event(self._run.host, event)
            body = _payload(thaw(payload))
            _require(len(canonical(body)) <= self._run.limits["maxPayloadBytes"],
                     "payload-budget-exceeded")
        except ProfileError as exc:
            self._refuse(exc.reason)
        self._emitted.append((event, body))

    def cancelled(self) -> bool:
        if self._closed:
            raise ProfileError("context-closed")
        return self._run.is_cancelled()


def _fail(hook: dict, reason: str) -> None:
    hook["status"], hook["reason"] = "failed", reason


class _Run:
    """Mutable state of one dispatch run; never escapes this module."""

    def __init__(self, hookset: HookSet, handlers: Mapping[str, Callable],
                 cancel: Callable[[], bool] | None, clock: Callable[[], int]):
        data = hookset.data
        self.host = data["host"]
        self.limits = data["limits"]
        self.entries = sorted(data["entries"], key=lambda e: (e["priority"], e["id"]))
        self.handlers = handlers
        self.clock = clock
        self.timeout_ns = self.limits["timeoutMs"] * 1_000_000
        self._cancel = cancel
        self._cancelled = False
        self.dispatches = 0
        self.contexts = 0

    def is_cancelled(self) -> bool:
        if not self._cancelled and self._cancel is not None:
            try:
                self._cancelled = bool(self._cancel())
            except Exception:
                self._cancelled = True  # an unreadable probe fails closed
        return self._cancelled

    @staticmethod
    def row(event_id: str, event: str, seq: int | None, status: str,
            reason: str | None = None, depth: int = 0) -> dict:
        return {"eventId": event_id, "event": event, "seq": seq, "status": status,
                "reason": reason, "decision": None, "depth": depth, "hooks": [],
                "emitted": []}

    def dispatch(self, event_id: str, event: str, seq: int | None, payload: Mapping[str, Any],
                 depth: int, chain: tuple[str, ...]) -> dict:
        row = self.row(event_id, event, seq, "accepted", depth=depth)
        view = freeze({"eventId": event_id, "event": event, "seq": seq, "depth": depth,
                       "payload": payload})
        denied = cancelled = False
        for entry in (e for e in self.entries if event in e["events"]):
            hook = {"hookId": entry["id"], "status": "ok", "reason": None, "decision": None,
                    "noteSha256": None}
            row["hooks"].append(hook)
            if self.is_cancelled():
                hook["status"] = "cancelled"
                cancelled = True
            elif entry["id"] in chain:
                _fail(hook, "recursion-loop")
            elif self.dispatches >= self.limits["maxDispatches"]:
                hook["status"], hook["reason"] = "skipped", "dispatch-budget-exceeded"
                denied = denied or entry["onFailure"] == "deny"
            else:
                self.dispatches += 1
                for name, body in self._invoke(entry, view, hook):
                    row["emitted"].append(self._follow_up(
                        f"{event_id}.{len(row['emitted']) + 1}", name, body, depth,
                        chain + (entry["id"],)))
            if hook["status"] == "failed":
                denied = denied or entry["onFailure"] == "deny"
            denied = denied or hook["decision"] == "deny"
        for child in row["emitted"]:
            denied = denied or child["decision"] == "deny"
            cancelled = cancelled or child["decision"] == "cancelled"
        row["decision"] = "deny" if denied else "cancelled" if cancelled else "allow"
        return row

    def _follow_up(self, event_id: str, name: str, body: dict, depth: int,
                   chain: tuple[str, ...]) -> dict:
        if depth + 1 > self.limits["maxDepth"]:
            return self.row(event_id, name, None, "rejected", "recursion-depth", depth + 1)
        return self.dispatch(event_id, name, None, body, depth + 1, chain)

    def _invoke(self, entry: dict, view: Mapping[str, Any], hook: dict) -> list:
        """Run one double; any failure is recorded on its row and never propagates."""
        handler = self.handlers.get(entry["id"])
        if handler is None:
            _fail(hook, "handler-missing")
            return []
        context = HookContext(self)
        self.contexts += 1
        try:
            try:
                result = handler(context, view)
            except ProfileError as exc:
                # A handler may not choose its own reason; only the context's latch counts.
                raise ProfileError(context._violation if exc.reason == context._violation
                                   else "hook-failed") from None
            if self.clock() - context._start > self.timeout_ns:
                context._violation = context._violation or "timeout"
            if context._violation is not None:
                raise ProfileError(context._violation)
            note = _result_note(result)
        except ProfileError as exc:
            _fail(hook, exc.reason)
            return []
        except Exception:
            _fail(hook, "hook-failed")
            return []
        finally:
            context._closed = True
        hook["decision"] = result["decision"]
        hook["noteSha256"] = sha256(note.encode("utf-8")).hexdigest()
        return context._emitted


@dataclass(frozen=True)
class HookRunResult:
    """Immutable run receipt for doubles-only dispatch; carries no authority."""

    hookset_sha256: str
    matrix_sha256: str
    ledger_sha256: str
    events_sha256: str
    events: tuple
    dispatches: int
    cancelled: bool
    teardown: Mapping[str, Any]
    admission: Mapping[str, Any]
    execution_authorization: bool = False
    native_execution: bool = False

    def to_dict(self) -> dict:
        return {"hooksetSha256": self.hookset_sha256, "matrixSha256": self.matrix_sha256,
                "ledgerSha256": self.ledger_sha256, "eventsSha256": self.events_sha256,
                "events": thaw(self.events), "dispatches": self.dispatches,
                "cancelled": self.cancelled, "teardown": thaw(self.teardown),
                "admission": thaw(self.admission),
                "executionAuthorization": self.execution_authorization,
                "nativeExecution": self.native_execution}


def _top_level(run: _Run, ledger: ReplayLedger, item: Mapping[str, Any]) -> dict:
    event_id, name, seq, payload = item["eventId"], item["event"], item["seq"], item["payload"]
    if run.is_cancelled():
        return run.row(event_id, name, seq, "cancelled")
    identity = digest({"event": name, "payload": payload})
    known = ledger._recall(event_id)
    if known is not None:
        if known == identity:
            return run.row(event_id, name, seq, "duplicate")
        return run.row(event_id, name, seq, "rejected", "replay-conflict")
    if seq != ledger.next_seq:
        return run.row(event_id, name, seq, "rejected", "event-order")
    status = event_status(run.host, name)
    if status != "modeled":
        return run.row(event_id, name, seq, "rejected", f"event-{status}")
    if len(canonical(payload)) > run.limits["maxPayloadBytes"]:
        return run.row(event_id, name, seq, "rejected", "payload-budget-exceeded")
    row = run.dispatch(event_id, name, seq, payload, 0, ())
    if row["decision"] != "cancelled":
        ledger._remember(event_id, identity)
    return row


def run_events(hookset: HookSet, events: Sequence[Mapping[str, Any]], *,
               handlers: Mapping[str, Callable], ledger: ReplayLedger,
               cancel: Callable[[], bool] | None = None,
               clock: Callable[[], int] = monotonic_ns) -> HookRunResult:
    """Dispatch synthetic events to caller-supplied doubles; nothing runs natively.

    Handlers are called as ``handler(context, event)`` and must return exactly
    ``{"decision": "allow"|"deny", "note": str}``. ``ledger`` carries replay state
    across calls. ``cancel`` is polled before every event and hook.
    """
    _require(isinstance(hookset, HookSet), "invalid-hookset")
    _require(isinstance(handlers, Mapping) and isinstance(ledger, ReplayLedger) and
             (cancel is None or callable(cancel)) and callable(clock) and
             all(callable(h) for h in handlers.values()), "invalid-input")
    _require(canonical(hookset.data) == hookset.canonical_bytes, "contract-drift")
    hookset = parse_hookset(hookset.canonical_bytes)
    data = hookset.data
    _require(data["effectClass"] == "E0", "effect-blocked")
    _require(set(handlers) <= {e["id"] for e in data["entries"]}, "handler-not-declared")
    _require(type(events) in (list, tuple), "invalid-event")
    _require(len(events) <= data["limits"]["maxEvents"], "event-budget-exceeded")
    for item in events:
        _event(item)
    _require(ledger.size + len(events) <= MAX_LEDGER, "ledger-full")
    _require(not ledger._busy, "ledger-busy")
    run = _Run(hookset, handlers, cancel, clock)
    ledger._busy = True
    try:
        rows = [_top_level(run, ledger, item) for item in events]
    finally:
        ledger._busy = False
    return HookRunResult(
        hookset_sha256=hookset.sha256, matrix_sha256=data["matrixSha256"],
        ledger_sha256=ledger.sha256, events_sha256=digest(rows), events=freeze(rows),
        dispatches=run.dispatches, cancelled=run.is_cancelled(),
        teardown=freeze({"closed": True, "contextsClosed": run.contexts}),
        admission=freeze(thaw(data["admission"])))
