# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded parsers for already captured Codex and Claude Code JSONL.

These functions inspect caller-supplied bytes only. They never launch a host,
open a session, authenticate, or imply that a parsed stream is a genuine receipt.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
import re
import signal
from typing import Any, Literal

Host = Literal["codex", "claude"]
MAX_STREAM_BYTES = 2 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_DEPTH = 32
MAX_EVENTS = 20_000
MAX_COUNTER = (1 << 63) - 1


class HostEventError(ValueError):
    """The supplied stream cannot support a trustworthy bounded observation."""


@dataclass(frozen=True)
class HostObservation:
    host: Host
    state: str
    initialized: bool | None
    observed_tools: tuple[str, ...]
    model: str | None
    input_tokens: int | None
    cached_input_tokens: int | None
    output_tokens: int | None
    reasoning_tokens: int | None
    estimated_cost_usd: float | None
    cost_basis: str | None
    error: str | None
    event_count: int
    limits: tuple[str, ...]


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HostEventError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise HostEventError(f"non-finite JSON number: {value}")


def _depth(value: Any, level: int = 0) -> None:
    if level > MAX_DEPTH:
        raise HostEventError("JSON nesting limit exceeded")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise HostEventError("JSON object key is not text")
            _depth(child, level + 1)
    elif isinstance(value, list):
        for child in value:
            _depth(child, level + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise HostEventError("non-finite JSON number")


def _check_raw_depth(line: bytes, line_number: int) -> None:
    """Enforce nesting before json.loads can recurse on attacker-controlled input."""
    depth = 0
    in_string = False
    escaped = False
    for byte in line:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:  # backslash
                escaped = True
            elif byte == 0x22:  # quote
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):  # { [
            depth += 1
            if depth > MAX_DEPTH:
                raise HostEventError(f"JSON nesting limit exceeded at line {line_number}")
        elif byte in (0x7D, 0x5D):  # } ]
            depth -= 1


def _number(value: Any, field: str) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0 or value > MAX_COUNTER:
        raise HostEventError(f"{field} must be an integer between 0 and {MAX_COUNTER}")
    return value


def _cost(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise HostEventError("total_cost_usd must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise HostEventError("total_cost_usd must be a finite non-negative number") from exc
    if not math.isfinite(result) or result < 0:
        raise HostEventError("total_cost_usd must be a finite non-negative number")
    return result


def _version(value: str, host: Host) -> tuple[int, ...]:
    if not isinstance(value, str):
        raise HostEventError("host version is required")
    match = re.fullmatch(r"(?:v)?(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?", value)
    if not match:
        raise HostEventError("host version is not a supported semantic version")
    version = tuple(int(part) for part in match.groups())
    if host == "claude" and version < (2, 1, 286):
        raise HostEventError("Claude Code before 2.1.286 is refused: --bare isolation is not comparable")
    if host == "codex" and version < (0, 162, 0):
        raise HostEventError("Codex CLI version predates the observed JSONL baseline")
    return version


def _decode_stream(stream: str | bytes) -> list[dict[str, Any]]:
    if isinstance(stream, str):
        try:
            raw = stream.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise HostEventError("stream is not valid UTF-8") from exc
    elif isinstance(stream, bytes):
        raw = stream
    else:
        raise HostEventError("stream must be UTF-8 text or bytes")
    if len(raw) > MAX_STREAM_BYTES:
        raise HostEventError("stream byte limit exceeded")
    if not raw:
        raise HostEventError("empty stream")
    if not raw.endswith(b"\n"):
        raise HostEventError("stream is truncated or lacks its final newline")
    events: list[dict[str, Any]] = []
    for number, line in enumerate(raw.splitlines(), start=1):
        if not line:
            raise HostEventError(f"blank JSONL line at {number}")
        if len(line) > MAX_LINE_BYTES:
            raise HostEventError(f"JSONL line limit exceeded at {number}")
        _check_raw_depth(line, number)
        try:
            item = json.loads(line, object_pairs_hook=_pairs, parse_constant=_constant)
        except (json.JSONDecodeError, UnicodeDecodeError, RecursionError, OverflowError, ValueError) as exc:
            raise HostEventError(f"invalid JSONL event at line {number}") from exc
        _depth(item)
        if not isinstance(item, dict) or not isinstance(item.get("type"), str):
            raise HostEventError(f"event at line {number} has no string type")
        events.append(item)
        if len(events) > MAX_EVENTS:
            raise HostEventError("event count limit exceeded")
    return events


def parse_host_events(
    host: Host,
    stream: str | bytes,
    *,
    version: str,
    expected_model: str | None = None,
    expected_mcp_servers: tuple[str, ...] | None = None,
    exit_code: int = 0,
) -> HostObservation:
    """Summarize a completed JSONL stream; no cost is inferred from missing data.

    Claude callers must pass a version new enough for isolated ``--bare`` use
    and should supply expected model/server names from the capture plan.
    """
    if host not in ("codex", "claude"):
        raise HostEventError("unsupported host")
    parsed_version = _version(version, host)
    if type(exit_code) is not int:
        raise HostEventError("exit_code must be an integer process status")
    if expected_mcp_servers is not None and (
            not isinstance(expected_mcp_servers, tuple)
            or any(not isinstance(name, str) or not name for name in expected_mcp_servers)
            or len(set(expected_mcp_servers)) != len(expected_mcp_servers)):
        raise HostEventError("expected_mcp_servers must be None or a tuple of unique non-empty names")
    events = _decode_stream(stream)
    tools: set[str] = set()
    limits: list[str] = ["Parsed caller-supplied JSONL only; authenticity and host execution are unverified."]
    baseline = (0, 162, 0) if host == "codex" else (2, 1, 286)
    if parsed_version > baseline:
        limits.append("Host version is newer than the parser's documented baseline; forward compatibility is unverified.")
    state = "incomplete"
    initialized: bool | None = None
    model: str | None = None
    input_tokens = cached_tokens = output_tokens = reasoning_tokens = None
    estimated_cost: float | None = None
    cost_basis: str | None = None
    error: str | None = None
    terminal_count = 0

    if host == "codex":
        if len(events) < 2 or events[0]["type"] != "thread.started" \
                or events[1]["type"] != "turn.started":
            raise HostEventError("Codex stream must start with thread.started then turn.started")
        if sum(event["type"] == "thread.started" for event in events) != 1 \
                or sum(event["type"] == "turn.started" for event in events) != 1:
            raise HostEventError("Codex stream must contain one thread and one turn start")
        terminal_types = {"turn.completed", "turn.failed", "error"}
        terminal_positions = [i for i, event in enumerate(events) if event["type"] in terminal_types]
        if terminal_positions and terminal_positions != [len(events) - 1]:
            raise HostEventError("Codex terminal event must be the final event")
        if not terminal_positions:
            state = "incomplete"
        if any(event["type"] not in {"thread.started", "turn.started", "item.started",
                                      "item.updated", "item.completed", *terminal_types}
               for event in events):
            raise HostEventError("Codex stream contains an unsupported event")
        allowed = {"thread.started", "turn.started", "turn.completed", "turn.failed",
                   "item.started", "item.updated", "item.completed", "error"}
        for event in events:
            kind = event["type"]
            if kind not in allowed:
                raise HostEventError(f"unknown Codex event type: {kind}")
            if kind == "thread.started":
                if initialized is not None:
                    raise HostEventError("duplicate Codex initialization event")
                initialized = True
            elif kind == "turn.completed":
                terminal_count += 1
                usage = event.get("usage")
                if usage is not None:
                    if not isinstance(usage, dict):
                        raise HostEventError("Codex usage must be an object")
                    input_tokens = _number(usage.get("input_tokens"), "input_tokens")
                    cached_tokens = _number(usage.get("cached_input_tokens"), "cached_input_tokens")
                    output_tokens = _number(usage.get("output_tokens"), "output_tokens")
                    reasoning_tokens = _number(usage.get("reasoning_output_tokens"), "reasoning_output_tokens")
            elif kind in {"turn.failed", "error"}:
                terminal_count += 1
                # Host-controlled diagnostic text may contain prompts, paths or
                # secrets; retain the failure class, not the supplied payload.
                error = "Codex reported a terminal error event"
            elif kind in {"item.started", "item.updated", "item.completed"}:
                item = event.get("item")
                if item is not None:
                    if not isinstance(item, dict) or not isinstance(item.get("type"), str):
                        raise HostEventError("Codex item must carry a string type")
                    if item["type"] == "mcp_tool_call":
                        server, tool = item.get("server"), item.get("tool")
                        if not isinstance(server, str) or not isinstance(tool, str):
                            raise HostEventError("Codex MCP tool evidence lacks server/tool")
                        if expected_mcp_servers is not None and server not in expected_mcp_servers:
                            raise HostEventError("Codex observed an MCP server outside the expected set")
                        tools.add(f"{server}/{tool}")
        if terminal_count > 1:
            raise HostEventError("multiple Codex terminal events are ambiguous")
        if terminal_count == 1 and error is None and any(e["type"] == "turn.completed" for e in events):
            state = "completed" if exit_code == 0 else "failed"
        elif error is not None:
            state = "cancelled" if "cancel" in error.lower() or "interrupt" in error.lower() else "failed"
        elif exit_code != 0:
            state, error = "failed", f"host exited with status {exit_code}"
    else:
        if events[0]["type"] != "system" or events[0].get("subtype") != "init":
            raise HostEventError("Claude stream must start with system/init")
        terminal_positions = [i for i, event in enumerate(events) if event["type"] == "result"]
        if terminal_positions and terminal_positions != [len(events) - 1]:
            raise HostEventError("Claude result event must be the final event")
        if not terminal_positions:
            state = "incomplete"
        allowed = {"system", "assistant", "user", "result"}
        for event in events:
            kind = event["type"]
            if kind not in allowed:
                raise HostEventError(f"unknown Claude event type: {kind}")
            if kind == "system":
                if event.get("subtype") != "init" or initialized is not None:
                    raise HostEventError("Claude system event is not one unique init event")
                initialized = True
                model = event.get("model") if isinstance(event.get("model"), str) else None
                if expected_mcp_servers is not None and (
                        "mcp_server_errors" not in event or "mcp_servers" not in event):
                    raise HostEventError("Claude init lacks MCP error or inventory fields required by the capture plan")
                errors = event.get("mcp_server_errors")
                if errors is not None and not isinstance(errors, list):
                    raise HostEventError("mcp_server_errors must be a list")
                if errors:
                    error = "MCP server initialization error"
                configured = event.get("mcp_servers")
                if configured is not None and not isinstance(configured, list):
                    raise HostEventError("mcp_servers must be a list")
                names = set()
                for server in configured or []:
                    if not isinstance(server, dict) or not isinstance(server.get("name"), str):
                        raise HostEventError("MCP server entry lacks a name")
                    names.add(server["name"])
                    if expected_mcp_servers is not None and server.get("status") != "connected":
                        error = error or "expected MCP server is not connected"
                if expected_mcp_servers is not None and names != set(expected_mcp_servers):
                    error = error or "MCP server initialization set differs from capture plan"
            elif kind == "assistant":
                message = event.get("message")
                if message is not None:
                    if not isinstance(message, dict):
                        raise HostEventError("Claude assistant message must be an object")
                    for block in message.get("content", []):
                        if not isinstance(block, dict):
                            raise HostEventError("Claude content block must be an object")
                        if block.get("type") == "tool_use" and isinstance(block.get("name"), str):
                            tools.add(block["name"])
            elif kind == "result":
                terminal_count += 1
                status = event.get("subtype")
                if status not in {"success", "error_max_turns", "error_during_execution", "error_max_budget_usd"}:
                    raise HostEventError("Claude result subtype is absent or unrecognized")
                usage = event.get("usage", {})
                if not isinstance(usage, dict):
                    raise HostEventError("Claude usage must be an object")
                input_tokens = _number(usage.get("input_tokens"), "input_tokens")
                cached_tokens = _number(usage.get("cache_read_input_tokens"), "cache_read_input_tokens")
                output_tokens = _number(usage.get("output_tokens"), "output_tokens")
                estimated_cost = _cost(event.get("total_cost_usd"))
                if estimated_cost is not None:
                    cost_basis = "Claude result total_cost_usd; host estimate, not invoice"
                if status == "error_during_execution":
                    # Crash results may zero every usage/cost field despite prior
                    # consumption. The result cannot establish complete totals.
                    input_tokens = cached_tokens = output_tokens = None
                    estimated_cost = None
                    cost_basis = None
                    limits.append("Claude execution-error totals may be reset after a crash; complete usage and cost are unknown.")
                elif status == "error_max_budget_usd":
                    # Result usage omits the response crossing the budget. The
                    # reported total_cost_usd remains only a host estimate.
                    input_tokens = cached_tokens = output_tokens = None
                    limits.append("Claude budget-error usage omits the budget-crossing response; complete token totals are unknown.")
                if status != "success":
                    error = f"Claude result subtype: {status}"
                    state = "cancelled" if "interrupt" in status or "cancel" in status else "failed"
                else:
                    state = "completed"
        if terminal_count > 1:
            raise HostEventError("multiple Claude result events are ambiguous")
        if initialized is None:
            raise HostEventError("Claude stream lacks initialization event")
        if expected_model and model != expected_model:
            error = error or "initialized model differs from capture plan"
        if error and state == "completed":
            state = "failed"
        if terminal_count == 0:
            state = "cancelled" if exit_code in (130, 143) else "incomplete"
    if initialized is None:
        state = "incomplete" if state == "incomplete" else state
    if exit_code < 0:
        signum = -exit_code
        state = "cancelled" if signum in {signal.SIGINT, signal.SIGTERM} else "failed"
        error = f"host process terminated by signal {signum}"
        input_tokens = cached_tokens = output_tokens = reasoning_tokens = None
        estimated_cost = None
        cost_basis = None
        limits.append("Host process ended by signal; token usage and cost are unknown and any partial terminal totals were discarded.")
    elif exit_code in (130, 143):
        state, error = "cancelled", "host process was interrupted"
    elif exit_code != 0 and state in {"completed", "incomplete"}:
        state, error = "failed", f"host exited with status {exit_code}"
    if host == "codex" and estimated_cost is None:
        limits.append("Codex token usage is reported when present; no monetary cost is inferred and remote budget enforcement is unknown.")
    if host == "claude":
        limits.append("Claude total_cost_usd is an estimate; resumed sessions can include prior history, so comparative captures require a new session.")
        limits.append("Comparable isolated capture requires Claude Code >=2.1.286 and --bare; this parser does not launch or enforce flags.")
    if expected_model and host == "codex":
        limits.append("Codex JSONL does not expose a verified model identity in the parsed event contract.")
    if expected_mcp_servers is None:
        limits.append("Expected MCP server inventory was omitted; whether observed/configured servers match the capture plan is unknown.")
    elif host == "codex":
        limits.append("Codex exec JSONL does not expose configured MCP inventory; observed MCP calls are checked against the expected set, but configured unused servers remain unknown.")
    return HostObservation(host, state, initialized, tuple(sorted(tools)), model,
                           input_tokens, cached_tokens, output_tokens, reasoning_tokens,
                           estimated_cost, cost_basis, error, len(events), tuple(limits))
