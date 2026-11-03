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

Mapping, from the host verification receipt (evidence/hv-t030-20261101.json): OpenTelemetry carries no
agent id, so a subagent strand comes from the hook `agent_id`; no HTTP `SessionStart` was delivered under
`claude -p`, so a session or subagent strand opens on the first event that mentions it. The hook payload
carries no outcome, so a strand closes as `unknown`.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import threading
import time
from typing import Any, Callable, Iterator

from agent_braid.view_loom import SCHEMA_VERSION, TEXT_MAX_LENGTH, TEXT_PATTERN
from agent_braid.view_serve import IngestRefusal, MAX_INVENTORY_NAME_LENGTH, MAX_INVENTORY_NAMES
from agent_braid.view_store import LoomStore

OBSERVATIONAL_EVENTS = ("SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "PostToolUse")
# The only payload names whose values are read, pinned from the T030 receipt. `tool_use_id` is allowlisted
# (its name is not inventoried as dropped) but no Loom field carries it, so it is not stored.
ALLOWED_FIELDS = ("hook_event_name", "session_id", "agent_id", "agent_type", "tool_name", "tool_use_id")
MAX_IDENTIFIER_LENGTH = 256
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
                 salt: bytes | None = None) -> None:
        self.store = store
        self._clock = clock
        self._origin = clock()
        self._salt = salt if salt is not None else secrets.token_bytes(32)
        self._lock = threading.Lock()
        self._strands: dict[str, str] = {}  # strandId -> "open" | "closed" | "refused" (store cap)
        self._children: dict[str, list[str]] = {}  # session strandId -> open subagent strandIds
        self._names: set[str] = set()
        self._gaps: set[str] = set()

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
            self._remember_names(payload)
            session = _identifier(payload.get("session_id"))
            agent = _identifier(payload.get("agent_id"))
            if session is None or (agent is None and event in ("SubagentStart", "SubagentStop")):
                self._gap(event)
                return
            session_strand = self._hash("session", session)
            agent_strand = self._hash("agent", agent) if agent is not None else None
            if event == "SessionEnd":
                self._end_session(session_strand)
                return
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
                self._update(target, _text(payload.get("tool_name")))

    # -- internals (callers hold the lock) ---------------------------------------------------

    def _hash(self, kind: str, value: str) -> str:
        return hmac.new(self._salt, f"{kind}\0{value}".encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    def _remember_names(self, payload: dict[str, Any]) -> None:
        for name in _field_names({key: value for key, value in payload.items() if key not in ALLOWED_FIELDS}):
            if len(self._names) >= MAX_INVENTORY_NAMES:
                return
            if len(name) <= MAX_INVENTORY_NAME_LENGTH and name.isprintable():
                self._names.add(name)

    def _append(self, kind: str, data: dict[str, Any]) -> bool:
        event = {
            "schemaVersion": SCHEMA_VERSION, "seq": 1, "kind": kind,
            "at": {"relMs": (self._clock() - self._origin) // 1_000_000, "basis": "viewer-monotonic"},
            "source": {"adapter": "claude-hook", "evidenceRef": None, "host": "claude",
                       "verification": "unverified"},
            "assurance": {"compatibilityClass": None, "notAGuarantee": True},
            "executionAuthorization": False, "data": data,
        }
        return self.store.append(event) is not None

    def _gap(self, event: str) -> None:
        """An observational event without the identifiers this mapping needs: one gap per event name."""
        if event not in self._gaps:
            self._gaps.add(event)
            self._append("observation.gap", {"reason": "shape-unpinned", "strandId": None,
                                             "fromSeq": None, "toSeq": None})

    def _open(self, strand: str, role: str, label: str, parent: str | None) -> bool:
        if strand in self._strands:
            return self._strands[strand] == "open"
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

    def _update(self, strand: str, tool_name: str | None) -> None:
        self._append("strand.update", {"strandId": strand, "state": "running", "toolName": tool_name})

    def _close(self, strand: str | None) -> None:
        if strand is not None and self._strands.get(strand) == "open":
            self._strands[strand] = "closed"
            self._append("strand.close", {"strandId": strand, "outcome": "unknown"})

    def _end_session(self, session_strand: str) -> None:
        if not self._ensure_session(session_strand):
            return
        for child in self._children.pop(session_strand, []):
            self._close(child)
        self._close(session_strand)
