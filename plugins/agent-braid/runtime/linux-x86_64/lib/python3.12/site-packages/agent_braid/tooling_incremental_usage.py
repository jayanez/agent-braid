# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded incremental observations of caller-supplied native host JSONL.

The observer never launches a host, authenticates events, or infers usage that
the selected source fields do not report. Claude partial-message events expose
per-main-session-message counters; only a terminal result exposes terminal
session usage. Codex exposes usage only on ``turn.completed``.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import signal
from typing import Any, Literal, Union

from .tooling_host_events import (
    MAX_COUNTER,
    MAX_DEPTH,
    MAX_EVENTS,
    MAX_LINE_BYTES,
    MAX_STREAM_BYTES,
)

Host = Literal["claude", "codex"]
SourceTimestamp = Union[str, int, float, None]
_CLAUDE_TERMINAL = {
    "success", "error_max_turns", "error_during_execution", "error_max_budget_usd",
}


class IncrementalUsageError(ValueError):
    """A host-event stream exceeded bounds or violated its observed contract."""


@dataclass(frozen=True)
class MessageUsage:
    """Latest selected counters observed for one Claude main-session message."""

    host: Literal["claude"]
    scope: Literal["main_session_message"]
    message_id: str
    source_timestamp: SourceTimestamp
    input_tokens: int | None
    cache_read_input_tokens: int | None
    cache_creation_input_tokens: int | None
    output_tokens: int | None
    message_stopped: bool


@dataclass(frozen=True)
class TerminalUsage:
    """Selected fields from one host terminal event, successful or not."""

    host: Host
    scope: Literal["host_reported_session", "host_reported_turn"]
    source_timestamp: SourceTimestamp
    input_tokens: int | None
    cache_read_input_tokens: int | None
    cache_creation_input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    reasoning_output_tokens: int | None
    estimated_cost_usd: float | None


@dataclass(frozen=True)
class IncrementalUsageReport:
    """Immutable snapshot; ``complete_cost_eligible`` requires a successful
    Claude terminal receipt with a reported host estimate, and is not an
    authenticity, invoice, or attribution claim.
    """

    host: Host
    state: Literal["streaming", "completed", "incomplete", "cancelled", "failed"]
    messages: tuple[MessageUsage, ...]
    terminal_usage: TerminalUsage | None
    terminal_received: bool
    whole_run_usage_known: bool
    subagent_usage_known: bool
    retry_usage_known: bool
    complete_cost_eligible: bool
    event_count: int
    error: str | None
    limits: tuple[str, ...]


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for key, value in pairs:
        if key in parsed:
            raise IncrementalUsageError(f"duplicate JSON key: {key}")
        parsed[key] = value
    return parsed


def _constant(value: str) -> None:
    raise IncrementalUsageError(f"non-finite JSON number: {value}")


def _check_depth(raw: bytes, line_number: int) -> None:
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_DEPTH:
                raise IncrementalUsageError(f"JSON nesting limit exceeded at line {line_number}")
        elif byte in (0x7D, 0x5D):
            depth -= 1


def _validate_tree(value: Any, level: int = 0) -> None:
    if level > MAX_DEPTH:
        raise IncrementalUsageError("JSON nesting limit exceeded")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise IncrementalUsageError("JSON object key is not text")
            _validate_tree(child, level + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_tree(child, level + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise IncrementalUsageError("non-finite JSON number")


def _counter(value: Any, name: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise IncrementalUsageError(f"{name} must be an integer between 0 and {MAX_COUNTER}")
    return value


def _cost(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise IncrementalUsageError("total_cost_usd must be a finite non-negative number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise IncrementalUsageError("total_cost_usd must be a finite non-negative number") from exc
    if not math.isfinite(result) or result < 0:
        raise IncrementalUsageError("total_cost_usd must be a finite non-negative number")
    return result


def _timestamp(event: dict[str, Any]) -> SourceTimestamp:
    value = event.get("timestamp")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise IncrementalUsageError("source timestamp must be text or a finite number")
    if isinstance(value, float) and not math.isfinite(value):
        raise IncrementalUsageError("source timestamp must be text or a finite number")
    return value


class IncrementalUsageObserver:
    """Consume bounded UTF-8 JSONL chunks and retain source-scoped usage.

    ``feed`` returns immutable message snapshots created by complete lines in
    this chunk. If a later line is invalid, snapshots from earlier lines remain
    available through :meth:`finish`; the observer then stays failed closed.
    A terminal event may report whole-session/turn usage, but partial message
    counters are never summed into a run total.
    """

    def __init__(self, host: Host) -> None:
        if host not in ("claude", "codex"):
            raise IncrementalUsageError("unsupported host")
        self.host = host
        self._buffer = bytearray()
        self._bytes = 0
        self._event_count = 0
        self._line_number = 0
        self._messages: dict[str, MessageUsage] = {}
        self._event_uuids: set[str] = set()
        self._current_message: str | None = None
        self._seen_message_ids: set[str] = set()
        self._terminal: TerminalUsage | None = None
        self._terminal_ok = False
        self._terminal_received = False
        self._terminal_usage_present = False
        self._initialized = False
        self._codex_turn_started = False
        self._codex_thread_started = False
        self._error: str | None = None
        self._closed = False

    def feed(self, chunk: bytes | bytearray | memoryview | str) -> tuple[MessageUsage, ...]:
        """Accept one stream fragment; an unterminated JSONL record stays buffered."""
        if self._closed:
            raise IncrementalUsageError("observer is already finalized")
        if self._error is not None:
            raise IncrementalUsageError(self._error)
        if isinstance(chunk, str):
            try:
                raw = chunk.encode("utf-8")
            except UnicodeEncodeError as exc:
                self._fail("stream is not valid UTF-8")
                raise IncrementalUsageError(self._error) from exc
        elif isinstance(chunk, (bytes, bytearray, memoryview)):
            raw = bytes(chunk)
        else:
            self._fail("chunk must be UTF-8 text or bytes")
            raise IncrementalUsageError(self._error)
        if not raw:
            return ()
        room = MAX_STREAM_BYTES - self._bytes
        accepted = raw[:room]
        self._bytes += len(accepted)
        emitted: list[MessageUsage] = []
        try:
            self._consume(accepted, emitted)
            if len(accepted) != len(raw):
                raise IncrementalUsageError("stream byte limit exceeded")
        except IncrementalUsageError as exc:
            self._fail(str(exc))
            raise
        return tuple(emitted)

    def _consume(self, raw: bytes, emitted: list[MessageUsage]) -> None:
        start = 0
        while True:
            newline = raw.find(b"\n", start)
            if newline < 0:
                segment = raw[start:]
                if len(self._buffer) + len(segment) > MAX_LINE_BYTES:
                    raise IncrementalUsageError("JSONL line limit exceeded")
                self._buffer.extend(segment)
                return
            segment = raw[start:newline]
            if len(self._buffer) + len(segment) > MAX_LINE_BYTES:
                raise IncrementalUsageError("JSONL line limit exceeded")
            self._buffer.extend(segment)
            line = bytes(self._buffer)
            self._buffer.clear()
            self._line_number += 1
            if not line:
                raise IncrementalUsageError(f"blank JSONL line at {self._line_number}")
            _check_depth(line, self._line_number)
            try:
                event = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
            except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, OverflowError, ValueError) as exc:
                raise IncrementalUsageError(f"invalid JSONL event at line {self._line_number}") from exc
            _validate_tree(event)
            if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                raise IncrementalUsageError(f"event at line {self._line_number} has no string type")
            self._event_count += 1
            if self._event_count > MAX_EVENTS:
                raise IncrementalUsageError("event count limit exceeded")
            observed = self._process(event)
            if observed is not None:
                emitted.append(observed)
            start = newline + 1
            if start >= len(raw):
                return

    def _process(self, event: dict[str, Any]) -> MessageUsage | None:
        if self._terminal_received:
            raise IncrementalUsageError("event appears after terminal event")
        event_uuid = event.get("uuid")
        if event_uuid is not None:
            if not isinstance(event_uuid, str) or not event_uuid:
                raise IncrementalUsageError("event uuid must be non-empty text")
            if event_uuid in self._event_uuids:
                raise IncrementalUsageError("duplicate event uuid")
            self._event_uuids.add(event_uuid)
        if self.host == "claude":
            return self._process_claude(event)
        else:
            self._process_codex(event)
            return None

    def _process_claude(self, event: dict[str, Any]) -> MessageUsage | None:
        kind = event["type"]
        if not self._initialized:
            if kind != "system" or event.get("subtype") != "init":
                raise IncrementalUsageError("Claude stream must start with system/init")
            self._initialized = True
            return None
        if kind == "system":
            raise IncrementalUsageError("Claude system event is not one unique init event")
        if kind == "assistant":
            # Assistant message usage.output_tokens can be an API-start placeholder.
            return None
        if kind == "user":
            return None
        if kind == "stream_event":
            parent = event.get("parent_tool_use_id")
            if parent is not None:
                # The source documents only main-session partial events. Do not
                # attribute a nested stream event to the main session.
                return None
            raw = event.get("event")
            if not isinstance(raw, dict) or not isinstance(raw.get("type"), str):
                raise IncrementalUsageError("Claude stream_event lacks a raw typed event")
            timestamp = _timestamp(event)
            return self._process_claude_partial(raw, timestamp if timestamp is not None else _timestamp(raw))
        if kind == "result":
            if self._current_message is not None:
                raise IncrementalUsageError("Claude result arrived before message_stop")
            subtype = event.get("subtype")
            if subtype not in _CLAUDE_TERMINAL:
                raise IncrementalUsageError("Claude result subtype is absent or unrecognized")
            usage = event.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise IncrementalUsageError("Claude result usage must be an object")
            self._terminal_usage_present = isinstance(usage, dict)
            usage = usage or {}
            self._terminal = TerminalUsage(
                host="claude", scope="host_reported_session",
                source_timestamp=_timestamp(event),
                input_tokens=_counter(usage.get("input_tokens"), "input_tokens"),
                cache_read_input_tokens=_counter(usage.get("cache_read_input_tokens"), "cache_read_input_tokens"),
                cache_creation_input_tokens=_counter(usage.get("cache_creation_input_tokens"), "cache_creation_input_tokens"),
                cached_input_tokens=None,
                output_tokens=_counter(usage.get("output_tokens"), "output_tokens"),
                reasoning_output_tokens=None,
                estimated_cost_usd=_cost(event.get("total_cost_usd")),
            )
            self._terminal_received = True
            self._terminal_ok = subtype == "success"
            return None
        raise IncrementalUsageError(f"unknown Claude event type: {kind}")

    def _process_claude_partial(self, event: dict[str, Any], source_timestamp: SourceTimestamp) -> MessageUsage | None:
        kind = event["type"]
        if kind in {"content_block_start", "content_block_delta", "content_block_stop", "ping"}:
            return None
        if kind == "message_start":
            if self._current_message is not None:
                raise IncrementalUsageError("Claude message_start arrived before previous message_stop")
            message = event.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("id"), str) or not message["id"]:
                raise IncrementalUsageError("Claude message_start lacks a message id")
            message_id = message["id"]
            if message_id in self._seen_message_ids:
                raise IncrementalUsageError("duplicate Claude message id")
            usage = message.get("usage", {})
            if not isinstance(usage, dict):
                raise IncrementalUsageError("Claude message_start usage must be an object")
            self._seen_message_ids.add(message_id)
            self._current_message = message_id
            self._messages[message_id] = MessageUsage(
                host="claude", scope="main_session_message", message_id=message_id,
                source_timestamp=source_timestamp,
                input_tokens=_counter(usage.get("input_tokens"), "input_tokens"),
                cache_read_input_tokens=_counter(usage.get("cache_read_input_tokens"), "cache_read_input_tokens"),
                cache_creation_input_tokens=_counter(usage.get("cache_creation_input_tokens"), "cache_creation_input_tokens"),
                output_tokens=None,
                message_stopped=False,
            )
            return self._messages[message_id]
        if kind == "message_delta":
            if self._current_message is None:
                raise IncrementalUsageError("stale Claude message_delta without an open message")
            usage = event.get("usage", {})
            if not isinstance(usage, dict):
                raise IncrementalUsageError("Claude message_delta usage must be an object")
            prior = self._messages[self._current_message]
            output = _counter(usage.get("output_tokens"), "output_tokens")
            if output is not None and prior.output_tokens is not None and output < prior.output_tokens:
                raise IncrementalUsageError("stale Claude output usage regressed")
            if output is not None:
                self._messages[self._current_message] = MessageUsage(
                    **{
                        **prior.__dict__,
                        "output_tokens": output,
                        "source_timestamp": source_timestamp if source_timestamp is not None else prior.source_timestamp,
                    }
                )
                return self._messages[self._current_message]
            return None
        if kind == "message_stop":
            if self._current_message is None:
                raise IncrementalUsageError("stale Claude message_stop without an open message")
            prior = self._messages[self._current_message]
            self._messages[self._current_message] = MessageUsage(
                **{
                    **prior.__dict__,
                    "message_stopped": True,
                    "source_timestamp": source_timestamp if source_timestamp is not None else prior.source_timestamp,
                }
            )
            stopped = self._messages[self._current_message]
            self._current_message = None
            return stopped
        raise IncrementalUsageError(f"unknown Claude partial event type: {kind}")

    def _process_codex(self, event: dict[str, Any]) -> None:
        kind = event["type"]
        if not self._codex_thread_started:
            if kind != "thread.started":
                raise IncrementalUsageError("Codex stream must start with thread.started")
            self._codex_thread_started = True
            return
        if not self._codex_turn_started:
            if kind != "turn.started":
                raise IncrementalUsageError("Codex stream must contain turn.started after thread.started")
            self._codex_turn_started = True
            return
        if kind in {"item.started", "item.updated", "item.completed"}:
            return
        if kind == "turn.completed":
            usage = event.get("usage")
            if usage is not None and not isinstance(usage, dict):
                raise IncrementalUsageError("Codex turn usage must be an object")
            self._terminal_usage_present = isinstance(usage, dict)
            usage = usage or {}
            self._terminal = TerminalUsage(
                host="codex", scope="host_reported_turn",
                source_timestamp=_timestamp(event),
                input_tokens=_counter(usage.get("input_tokens"), "input_tokens"),
                cache_read_input_tokens=None,
                cache_creation_input_tokens=None,
                cached_input_tokens=_counter(usage.get("cached_input_tokens"), "cached_input_tokens"),
                output_tokens=_counter(usage.get("output_tokens"), "output_tokens"),
                reasoning_output_tokens=_counter(usage.get("reasoning_output_tokens"), "reasoning_output_tokens"),
                estimated_cost_usd=None,
            )
            self._terminal_received = True
            self._terminal_ok = True
            return
        if kind in {"turn.failed", "error"}:
            self._terminal_received = True
            self._terminal_ok = False
            return
        raise IncrementalUsageError(f"unknown Codex event type: {kind}")

    def _fail(self, reason: str) -> None:
        if self._error is None:
            self._error = reason

    def finish(self, *, exit_code: int = 0) -> IncrementalUsageReport:
        """Close the stream, retaining scoped partial data on every failure."""
        if type(exit_code) is not int:
            self._fail("exit_code must be an integer process status")
        if not self._closed:
            self._closed = True
            if self._buffer and self._error is None:
                self._fail("stream is truncated or lacks its final newline")
            if self._event_count == 0 and self._error is None:
                self._fail("empty stream")
        return self._report(exit_code if type(exit_code) is int else 1)

    def snapshot(self) -> IncrementalUsageReport:
        """Return current immutable observations without closing the stream."""
        return self._report(0)

    def _report(self, exit_code: int) -> IncrementalUsageReport:
        interrupted = exit_code in (130, 143) or exit_code < 0 and -exit_code in {signal.SIGINT, signal.SIGTERM}
        if self._error:
            state: Literal["streaming", "completed", "incomplete", "cancelled", "failed"] = "failed"
        elif interrupted:
            state = "cancelled"
        elif exit_code != 0:
            state = "failed"
        elif self._closed and self._terminal_received and self._terminal_ok:
            state = "completed"
        elif self._terminal_received:
            state = "failed"
        elif self._closed:
            state = "incomplete"
        else:
            state = "streaming"
        whole_run_known = (
            state == "completed" and self._terminal is not None and self._terminal_usage_present
        )
        eligible = (
            whole_run_known and self.host == "claude"
            and self._terminal is not None and self._terminal.estimated_cost_usd is not None
        )
        limits = [
            "Caller-supplied JSONL was parsed; host identity, execution, and event authenticity are unverified.",
            "Claude partial counters are main-session per-message snapshots; assistant message output placeholders are ignored.",
            "Per-message output updates replace the latest snapshot; they are never summed across repeated deltas.",
            "Subagent and retry inclusion or attribution cannot be established by this observer, even when terminal usage is present.",
        ]
        if not self._terminal_received:
            limits.append("Whole-run usage and complete cost are unknown until a terminal event is observed.")
        elif not whole_run_known:
            limits.append("A terminal event was observed, but process/stream completion did not establish a successful whole-run scope.")
        if self.host == "codex":
            limits.append("Codex usage is observed only from turn.completed; no monetary cost is inferred.")
        elif eligible:
            limits.append("Cost eligibility reflects only the successful result's host estimate; it is not an invoice or independent accounting proof.")
        elif whole_run_known:
            limits.append("Claude terminal usage completed without a host total_cost_usd estimate; complete cost remains unknown.")
        return IncrementalUsageReport(
            host=self.host, state=state, messages=tuple(self._messages.values()),
            terminal_usage=self._terminal, terminal_received=self._terminal_received,
            whole_run_usage_known=whole_run_known,
            subagent_usage_known=False,
            retry_usage_known=False,
            complete_cost_eligible=eligible,
            event_count=self._event_count, error=self._error,
            limits=tuple(limits),
        )
