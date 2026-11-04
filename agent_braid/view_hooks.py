# SPDX-License-Identifier: AGPL-3.0-only
"""Observational Claude Code HTTP hooks for the read-only activity viewer (SPEC-061 T019).

`HookIngest.handle` is the ingest handler registered for `/hook/claude` (`ViewServer(ingest_handlers=...)`),
and `HookIngest.dropped_names` is the matching `names_inventory`. The server already answers every hook
route with an empty body; this module decides what a payload may become.

Contract (specs/061-activity-viewer/contracts/ui-security-privacy.md):
* Only the observational events `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop` and
  `PostToolUse` are accepted. Every other event name, decision events included, is refused with 403.
* Only the names in `ALLOWED_FIELDS` are read. Identifiers are replaced by a per-instance salted HMAC; no
  other value is read, stored or echoed. The names (never the values) of every other field go to a bounded
  inventory for host verification.
* The viewer never answers a decision: it returns nothing, and a refusal stores nothing.
* A strand that was closed stays closed (REQ-003, T047): a later event that would continue it is not shown
  as activity; one `shape-unpinned` gap naming the strand says so, so the silence never looks clean. A
  repeated `SessionEnd` or `SubagentStop` is a no-op. At most `MAX_TRACKED_STRANDS` strands are tracked;
  beyond that nothing new is opened and one `stream-truncated` gap says so.

Mapping, from the host verification receipt (evidence/hv-t030-20261101.json): OpenTelemetry carries no
agent id, so a subagent strand comes from the hook `agent_id`; no HTTP `SessionStart` was delivered under
`claude -p`, so a session or subagent strand opens on the first event that mentions it. The hook payload
carries no outcome, so a strand closes as `unknown`.

Tool duration (T062, contract v0.2): `PostToolUse.duration_ms` is pinned from the T030 receipt by owner decision
(T053 closed on that evidence). Only a JSON integer from 0 to 86,400,000 ms is kept, as `toolDurationMs` on a v0.2
`strand.update`; any other shape (a bool, a float, a string, a negative or an oversize value) is dropped and one
`shape-unpinned` gap says so. The name is read only on `PostToolUse`: on any other event it is inventoried as
dropped, and no duration is assumed for `SubagentStop`. The value lives in the store's memory only (OD-V4 (a));
a replay drops it (`view_serve.replay_events`). Hooks carry no waiting signal, so this module never emits
`waitingOn`.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from typing import Any, Callable, Iterator

from agent_braid.view_ingest import MAX_INVENTORY_NAME_LENGTH, MAX_INVENTORY_NAMES, IngestRefusal
from agent_braid.view_loom import (
    SCHEMA_VERSION, SCHEMA_VERSION_V02, TEXT_MAX_LENGTH, TEXT_PATTERN, TOOL_DURATION_MAX_MS,
)
from agent_braid.view_store import LoomStore

OBSERVATIONAL_EVENTS = ("SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "PostToolUse")
# The only payload names whose values are read, pinned from the T030 receipt. `tool_use_id` is allowlisted
# (its name is not inventoried as dropped) but no Loom field carries it, so it is not stored.
ALLOWED_FIELDS = ("hook_event_name", "session_id", "agent_id", "agent_type", "tool_name", "tool_use_id",
                  "duration_ms")
# `duration_ms` is read only on this event (T062); on any other event its name is inventoried as dropped.
DURATION_EVENT = "PostToolUse"
MAX_IDENTIFIER_LENGTH = 256
MAX_TRACKED_STRANDS = 1024  # the store's own strand cap is 256; this bounds the ids remembered beyond it
_TEXT = re.compile(TEXT_PATTERN)
_NAME_SEGMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")  # a schema-like name; a data-like key is not inventoried
_MAX_NAME_WALK = 20_000  # payload nodes inspected for the inventory; the body limit is 256 KiB


def _encodable(value: str) -> bool:
    """False for a string UTF-8 cannot encode (a lone surrogate): it is treated as absent, never an error."""
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _text(value: Any) -> str | None:
    """A kept free-text value, or None when absent, not a string, too long, unencodable or carrying control characters."""
    if isinstance(value, str) and 0 < len(value) <= TEXT_MAX_LENGTH and _TEXT.fullmatch(value) and _encodable(value):
        return value
    return None


def _identifier(value: Any) -> str | None:
    if isinstance(value, str) and 0 < len(value) <= MAX_IDENTIFIER_LENGTH and _encodable(value):
        return value
    return None


def _field_names(payload: dict[str, Any]) -> Iterator[str]:
    """Dotted names of every member, lists as `name[]`; iterative, bounded. Data-like keys are skipped."""
    stack: list[tuple[str, Any]] = [("", payload)]
    walked = 0
    while stack and walked < _MAX_NAME_WALK:
        prefix, node = stack.pop()
        walked += 1
        if isinstance(node, list):
            stack.extend((f"{prefix}[]", item) for item in node if isinstance(item, (dict, list)))
        elif isinstance(node, dict):
            for key, child in node.items():
                if not _NAME_SEGMENT.fullmatch(key):
                    continue
                path = f"{prefix}.{key}" if prefix else key
                yield path
                if isinstance(child, (dict, list)):
                    stack.append((path, child))


class HookIngest:
    """Turns observational Claude Code hook payloads into Loom strand events in `store`."""

    def __init__(self, store: LoomStore, *, clock: Callable[[], int] = time.monotonic_ns,
                 salt: bytes | None = None, max_strands: int = MAX_TRACKED_STRANDS) -> None:
        if max_strands < 1:
            raise ValueError("max_strands is at least 1")
        self.store = store
        self._max_strands = max_strands
        self._clock = clock
        self._origin = clock()
        self._salt = salt if salt is not None else secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._strands: dict[str, str] = {}  # strandId -> "open" | "closed" | "refused" (store cap)
        self._children: dict[str, list[str]] = {}  # session strandId -> open subagent strandIds
        self._names: set[str] = set()
        self._gaps: set[str] = set()  # gaps already stored: an event name, a closed strand id or "tracking"

    def dropped_names(self) -> list[str]:
        """Names of the payload fields that were dropped, sorted; never their values."""
        with self._lock:
            return sorted(self._names)

    def handle(self, payload: Any) -> None:
        """The ingest handler. Raises IngestRefusal(400) or IngestRefusal(403); returns nothing."""
        if not isinstance(payload, dict):
            raise IngestRefusal(400)
        event = payload.get("hook_event_name")
        if not isinstance(event, str):
            raise IngestRefusal(400)
        if event not in OBSERVATIONAL_EVENTS:
            raise IngestRefusal(403)
        with self._lock:
            self._remember_names(payload, event)
            session = _identifier(payload.get("session_id"))
            agent = _identifier(payload.get("agent_id"))
            if session is None or (agent is None and event in ("SubagentStart", "SubagentStop")):
                self._gap(event, "shape-unpinned")
                return
            session_strand = self._hash("session", session)
            agent_strand = self._hash("agent", agent) if agent is not None else None
            if event == "SessionEnd":
                self._end_session(session_strand)
                return
            if event == "SubagentStop" and self._strands.get(agent_strand) == "closed":
                return  # a repeated stop: already shown as closed
            if not self._ensure_session(session_strand):
                return
            if agent_strand is None:
                target = session_strand
            else:
                target = agent_strand
                if not self._ensure_subagent(session_strand, agent_strand, _text(payload.get("agent_type"))):
                    return
            if event == "SubagentStop":
                self._close(agent_strand)
            elif event == "PostToolUse":
                self._update(target, _text(payload.get("tool_name")), self._duration(payload))

    # -- internals (callers hold the lock) ---------------------------------------------------

    def _hash(self, kind: str, value: str) -> str:
        return hmac.new(self._salt, f"{kind}\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    def _remember_names(self, payload: dict[str, Any], event: str) -> None:
        def kept(key: str) -> bool:
            return key in ALLOWED_FIELDS and (key != "duration_ms" or event == DURATION_EVENT)
        for name in _field_names({key: value for key, value in payload.items() if not kept(key)}):
            if len(self._names) >= MAX_INVENTORY_NAMES:
                return
            if len(name) <= MAX_INVENTORY_NAME_LENGTH and name.isprintable():
                self._names.add(name)

    def _duration(self, payload: dict[str, Any]) -> int | None:
        """`duration_ms` when it is a JSON integer in range; otherwise None, with one gap when it was present."""
        if "duration_ms" not in payload:
            return None
        value = payload["duration_ms"]
        if type(value) is int and 0 <= value <= TOOL_DURATION_MAX_MS:
            return value
        self._gap("duration_ms", "shape-unpinned")
        return None

    def _append(self, kind: str, data: dict[str, Any], version: str = SCHEMA_VERSION) -> bool:
        event = {
            "schemaVersion": version, "seq": 1, "kind": kind,
            "at": {"relMs": (self._clock() - self._origin) // 1_000_000, "basis": "viewer-monotonic"},
            "source": {"adapter": "claude-hook", "evidenceRef": None, "host": "claude",
                       "verification": "unverified"},
            "assurance": {"compatibilityClass": None, "notAGuarantee": True},
            "executionAuthorization": False, "data": data,
        }
        return self.store.append(event) is not None

    def _gap(self, key: str, reason: str, strand: str | None = None) -> None:
        """One gap per `key` (an event name, a closed strand id or "tracking"), so a flood stores one."""
        if key not in self._gaps:
            self._gaps.add(key)
            self._append("observation.gap", {"reason": reason, "strandId": strand, "fromSeq": None, "toSeq": None})

    def _open(self, strand: str, role: str, label: str, parent: str | None) -> bool:
        state = self._strands.get(strand)
        if state == "closed":
            self._gap(strand, "shape-unpinned", strand)  # an event for a strand already shown as closed
        if state is not None:
            return state == "open"
        if len(self._strands) >= self._max_strands:
            self._gap("tracking", "stream-truncated")  # too many ids remembered: nothing new is opened
            return False
        stored = self._append("strand.open", {"strandId": strand, "host": "claude", "role": role,
                                              "label": label, "parentStrandId": parent})
        self._strands[strand] = "open" if stored else "refused"  # a cap refusal: store nothing further
        return stored

    def _ensure_session(self, session_strand: str) -> bool:
        return self._open(session_strand, "agent", "Claude session", None)

    def _ensure_subagent(self, session_strand: str, agent_strand: str, agent_type: str | None) -> bool:
        known = agent_strand in self._strands
        opened = self._open(agent_strand, "subagent", agent_type or "Claude subagent", session_strand)
        if opened and not known:
            self._children.setdefault(session_strand, []).append(agent_strand)
        return opened

    def _update(self, strand: str, tool_name: str | None, duration: int | None = None) -> None:
        data: dict[str, Any] = {"strandId": strand, "state": "running", "toolName": tool_name}
        if duration is None:
            self._append("strand.update", data)
        else:  # contract v0.2: the only member this adapter adds
            self._append("strand.update", {**data, "toolDurationMs": duration}, SCHEMA_VERSION_V02)

    def now_ms(self) -> int:
        """The viewer clock in ms on the same monotonic basis as the events this ingest stamps (T060)."""
        return (self._clock() - self._origin) // 1_000_000

    def _close(self, strand: str | None) -> None:
        if strand is not None and self._strands.get(strand) == "open":
            self._strands[strand] = "closed"
            self._append("strand.close", {"strandId": strand, "outcome": "unknown"})

    def _end_session(self, session_strand: str) -> None:
        if self._strands.get(session_strand) == "closed":
            return  # a repeated end: already shown as closed
        if not self._ensure_session(session_strand):
            return
        for child in self._children.pop(session_strand, []):
            self._close(child)
        self._close(session_strand)
