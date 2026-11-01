# SPDX-License-Identifier: AGPL-3.0-only
"""Claude host adapter behind the laboratory contract; doubles only, native refused.

Turns a trusted context package and a typed Claude request into a launch plan, hands
it to a transport, and normalizes Claude ``stream-json`` output into a T012
observation. Everything here is Claude-specific (session id, permission mode,
tool allow-list, ``init``/``result`` events, version window) and nothing is inherited
from or shared with another host adapter.

Only the scripted ``ClaudeHostDouble`` runs. Any other transport is ``native`` and
refuses unless it carries a hash-verified Claude-only qualification that matches the
manifest; one host's qualification can never admit the other. The profile
manifest is still offline-only, so native dispatch stays refused until a separate
T008 decision. Results are evidence, never authorization; no process, network or
paid route is started here, and an observed non-subscription key source is refused.
Small bounds and the qualification shape deliberately mirror ``harness_lab`` but raise
``ClaudeHostError``; nothing is shared with another host adapter.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from hashlib import sha256
import re
import threading
from typing import Any

from .harness_context import ContextPackage
from .harness_lab import ENFORCED_EFFECTS, MAX_WALL_SECONDS
from .harness_manifest import HarnessManifest
from .harness_observation import (
    MAX_EVENTS, MAX_FIELD_BYTES, ExportInventory, Observation, ObservationError, observe)
from .system_one import InvalidDecision, canonical, parse_json

HOST = "claude"
QUALIFICATION_FORMAT = "braid-harness-host-qualification/v0.1"
PERMISSION_MODES = ("default", "plan")  # never acceptEdits/bypassPermissions/dontAsk
ALLOWED_TOOLS = ("Glob", "Grep", "Read")  # read-only; mutation needs its own decision
DENIED_TOOLS = ("Bash", "Edit", "MultiEdit", "NotebookEdit", "Task", "WebFetch", "WebSearch", "Write")
MAX_TURNS = 8
# K3: native sessions may run up to the NC-8 wall (F3, 30 minutes); fixtures, the double
# and every other host keep the shared ``MAX_WALL_SECONDS`` bound.
NATIVE_MAX_WALL_SECONDS = 1800
MAX_PROMPT_BYTES = 131_072
# Fixture-level assumption about ``init.apiKeySource``; anything else is a possible
# paid route and is refused until T008 observes the real values.
SUBSCRIPTION_KEY_SOURCES = frozenset({"none", "oauth"})
# Typed policy for the future T008 native launcher; the double ignores it. HOME-derived
# configuration stays reachable for authentication, so the launcher must contain it.
ENV_ALLOW = ("HOME", "PATH")  # existing authentication lives under HOME
ENV_DENY = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL",
            "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_SESSION = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
RESERVED_EVENTS = 8  # terminal plus every error kind _terminal can add
_MODEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_VERSION = re.compile(r"(\d{1,4})\.(\d{1,4})\.(\d{1,4})(?: \(Claude Code\))?\Z")


class ClaudeHostError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-host-request"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-host-request") -> None:
    if not condition:
        raise ClaudeHostError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


# --- version handling ---------------------------------------------------------------


def parse_version(text: Any) -> tuple[int, int, int]:
    """Strict ``X.Y.Z`` (optionally ``(Claude Code)``); anything else is unknown."""
    match = _VERSION.fullmatch(text) if type(text) is str else None
    _require(match is not None, "invalid-version")
    return tuple(int(part) for part in match.groups())  # type: ignore[return-value]


@dataclass(frozen=True)
class CompatibilityWindow:
    """Trusted caller-supplied half-open range ``[minimum, below)`` of host builds."""

    minimum: tuple[int, int, int]
    below: tuple[int, int, int]

    def __post_init__(self) -> None:
        for bound in (self.minimum, self.below):
            _require(type(bound) is tuple and len(bound) == 3 and all(_int(p, 0, 9999) for p in bound),
                     "invalid-compatibility")
        _require(self.minimum < self.below, "invalid-compatibility")

    def admits(self, version: tuple[int, int, int]) -> bool:
        return self.minimum <= version < self.below


# --- request, permissions and launch plan -------------------------------------------


@dataclass(frozen=True)
class ClaudeRequest:
    """Claude session and permission choices; fresh session only, never resumed."""

    session_id: str
    permission_mode: str = "plan"
    allowed_tools: tuple[str, ...] = ("Read",)
    model: str | None = None
    max_turns: int = 4

    def __post_init__(self) -> None:
        _require(type(self.session_id) is str and _SESSION.fullmatch(self.session_id) is not None,
                 "invalid-session")
        _require(self.permission_mode in PERMISSION_MODES, "permission-refused")
        tools = self.allowed_tools
        _require(type(tools) is tuple and len(tools) == len(set(tools))
                 and all(t in ALLOWED_TOOLS for t in tools), "permission-refused")
        _require(self.model is None or (type(self.model) is str and _MODEL.fullmatch(self.model) is not None),
                 "invalid-model")
        _require(_int(self.max_turns, 1, MAX_TURNS), "invalid-limits")


@dataclass(frozen=True)
class HostLimits:
    """Trusted wall-clock and output bounds; ``run_claude`` applies the double's tighter wall."""

    wall_seconds: int = 10
    max_output_bytes: int = 65_536

    def __post_init__(self) -> None:
        _require(_int(self.wall_seconds, 1, NATIVE_MAX_WALL_SECONDS)
                 and _int(self.max_output_bytes, 1, 1_048_576), "invalid-limits")


@dataclass(frozen=True)
class LaunchPlan:
    """Typed argv and environment policy; building it never starts anything."""

    argv: tuple[str, ...]
    prompt_sha256: str
    env_allow: tuple[str, ...] = ENV_ALLOW
    env_deny: tuple[str, ...] = ENV_DENY


def build_plan(request: ClaudeRequest, prompt: bytes) -> LaunchPlan:
    argv = ["claude", "-p", "--output-format", "stream-json", "--verbose",
            "--session-id", request.session_id, "--permission-mode", request.permission_mode,
            "--max-turns", str(request.max_turns),
            # isolation: only the listed built-in tools, no settings/hooks, no MCP servers
            "--tools", ",".join(request.allowed_tools),
            "--disallowedTools", ",".join(DENIED_TOOLS),
            "--setting-sources", "", "--strict-mcp-config"]
    if request.allowed_tools:
        argv += ["--allowedTools", ",".join(request.allowed_tools)]
    if request.model is not None:
        argv += ["--model", request.model]
    return LaunchPlan(tuple(argv), sha256(prompt).hexdigest())


# --- transports ---------------------------------------------------------------------


@dataclass(frozen=True)
class HostRun:
    """What a transport reports about one supervised host child."""

    stdout: bytes
    exit_code: int | None
    timed_out: bool = False
    cancelled: bool = False
    output_truncated: bool = False
    settled: bool = True


class ClaudeTransport:
    """Interface for a real host launcher. Subclass kind is ``native`` and refuses."""

    kind = "native"

    def version(self) -> str:
        raise NotImplementedError

    def run(self, plan: LaunchPlan, prompt: bytes, limits: HostLimits,
            cancel: threading.Event) -> HostRun:
        raise NotImplementedError

    def verify_containment(self, manifest: HarnessManifest, qualification: Any, now: int) -> None:
        """K2: raise ``ClaudeHostError`` unless the transport's backend is verified.

        A native transport must override this; the default refuses.
        """
        raise ClaudeHostError("native-host-unqualified")


class ClaudeHostDouble(ClaudeTransport):
    """Deterministic scripted host: replays fixed output, records every launch."""

    kind = "double"

    def __init__(self, lines: Sequence[Mapping[str, Any] | bytes | str] = (), *,
                 version: str = "2.1.0 (Claude Code)", exit_code: int | None = 0,
                 timed_out: bool = False, settled: bool = True,
                 output_truncated: bool = False, cancel_mid_run: bool = False):
        self._lines = tuple(lines)
        self._version = version
        self._script = dict(exit_code=exit_code, timed_out=timed_out, settled=settled,
                            output_truncated=output_truncated)
        self._cancel_mid_run = cancel_mid_run
        self.launches: list[tuple[LaunchPlan, bytes]] = []

    def version(self) -> str:
        return self._version

    def run(self, plan: LaunchPlan, prompt: bytes, limits: HostLimits,
            cancel: threading.Event) -> HostRun:
        self.launches.append((plan, prompt))
        encoded = [line if isinstance(line, bytes) else line.encode() if isinstance(line, str)
                   else canonical(dict(line)) for line in self._lines]
        stdout = b"\n".join(encoded)
        if self._cancel_mid_run or cancel.is_set():
            return HostRun(stdout, None, cancelled=True, settled=self._script["settled"])
        return HostRun(stdout, **self._script)


# --- native refusal: Claude-only qualification --------------------------------------


@dataclass(frozen=True)
class HostQualification:
    """Parsed Claude qualification; construction is not verification."""

    environment_sha256: str
    expires_at: int
    evidence_sha256: str
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()


def verify_host_qualification(raw: bytes, *, expected_sha256: str) -> HostQualification:
    """Strictly parse a Claude-only qualification against a trusted external hash.

    A record naming any other host is refused as ``host-mismatch``: one host cannot
    qualify the other. The trusted hash is of the canonical record, so only canonical
    input can match; it proves identity, while the evidence behind it is judged by the
    T008 decision records, not here.
    """
    _require(type(expected_sha256) is str and _HASH.fullmatch(expected_sha256) is not None,
             "invalid-expected-hash")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise ClaudeHostError("invalid-qualification") from None
    _require(type(value) is dict and "host" in value, "invalid-qualification")
    _require(value["host"] == HOST, "host-mismatch")
    ok = (set(value) == {"format", "host", "environmentSha256", "enforced", "expiresAt", "evidenceSha256"}
          and value["format"] == QUALIFICATION_FORMAT
          and value["enforced"] == list(ENFORCED_EFFECTS) and _int(value["expiresAt"], 0, 1 << 40)
          and all(type(value[k]) is str and _HASH.fullmatch(value[k]) is not None
                  for k in ("environmentSha256", "evidenceSha256")))
    _require(ok, "invalid-qualification")
    qualification = HostQualification(value["environmentSha256"], value["expiresAt"],
                                      value["evidenceSha256"], canonical(value))
    _require(qualification.sha256 == expected_sha256, "qualification-drift")
    return qualification


def _check_transport(transport: Any, manifest: HarnessManifest, qualification: Any, now: int) -> str:
    if type(transport) is ClaudeHostDouble:
        return "double"
    _require(isinstance(transport, ClaudeTransport) and transport.kind == "native", "invalid-transport")
    _require(isinstance(qualification, HostQualification)
             and manifest.data["host"]["kind"] == HOST
             and qualification.environment_sha256 == manifest.data["environment"]["sha256"]
             and now < qualification.expires_at, "native-host-unqualified")
    transport.verify_containment(manifest, qualification, now)
    return "native"


# --- stream-json normalization ------------------------------------------------------


@dataclass
class _Stream:
    events: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    secrets: tuple = ()
    init_seen: bool = False
    session: str | None = None
    version: str | None = None
    model: str | None = None
    key_source: str | None = None
    result: dict | None = None

    def add(self, kind: str, **fields: Any) -> None:
        if len(self.events) >= MAX_EVENTS - RESERVED_EVENTS:
            if "event-overflow" not in self.errors:
                self.errors.append("event-overflow")
            return
        self.append(kind, **fields)

    def append(self, kind: str, **fields: Any) -> None:
        """Terminal and error events use the slots ``add`` never fills."""
        if len(self.events) < MAX_EVENTS:
            self.events.append({"seq": len(self.events), "kind": kind, **fields})

    def text(self, value: Any) -> str:
        data = str(value)
        for secret in self.secrets:  # redact before slicing so no secret prefix survives
            data = data.replace(secret, "[redacted]")
        data = data.encode("utf-8", "replace")
        if len(data) > MAX_FIELD_BYTES:
            self.errors.append("field-truncated")
            data = data[:MAX_FIELD_BYTES]
        return data.decode("utf-8", "ignore")


def _blocks(stream: _Stream, message: Any) -> None:
    content = message.get("content") if type(message) is dict else None
    if type(content) is not list:
        stream.errors.append("malformed-line")
        return
    for block in content:
        kind = block.get("type") if type(block) is dict else None
        if kind == "text" and type(block.get("text")) is str:
            stream.add("message", text=stream.text(block["text"]))
        elif kind == "tool_use" and type(block.get("name")) is str:
            stream.add("tool", text=stream.text(block["name"]))
        elif kind not in ("tool_result", "thinking"):
            stream.errors.append("malformed-line")


def _clean(stream: _Stream, value: Any, pattern: re.Pattern, code: str | None = None) -> str | None:
    """Keep an untrusted init string only when it is well-formed and secret-free."""
    if type(value) is str and pattern.fullmatch(value) is not None \
            and not any(secret in value for secret in stream.secrets):
        return value
    if code is not None:  # version and key source already surface as drift/route events
        stream.errors.append(code)
    return None


_KEY_SOURCE = re.compile(r"[A-Za-z0-9_.:-]{1,64}\Z")


def _read_stream(stdout: bytes, secrets: tuple = ()) -> _Stream:
    stream = _Stream(secrets=secrets)
    for line in stdout.split(b"\n"):
        if not line:
            continue
        try:
            event = parse_json(line)
        except InvalidDecision:
            stream.errors.append("malformed-line")
            continue
        kind = event.get("type") if type(event) is dict else None
        if kind == "system" and event.get("subtype") == "init":
            if stream.init_seen:
                stream.errors.append("duplicate-init")
                continue
            stream.init_seen = True
            session = event.get("session_id")
            stream.session = session if type(session) is str else None
            stream.version = _clean(stream, event.get("claude_code_version"), _VERSION)
            stream.model = _clean(stream, event.get("model"), _MODEL, "model-invalid")
            stream.key_source = _clean(stream, event.get("apiKeySource"), _KEY_SOURCE)
            stream.add("start")
        elif kind == "assistant":
            _blocks(stream, event.get("message"))
        elif kind == "user":
            pass  # tool results echo workspace content; never exported
        elif kind == "result":
            if stream.result is not None:
                stream.errors.append("duplicate-result")
            else:
                stream.result = event
        else:
            stream.errors.append("unknown-event-type")
    return stream


def _terminal(stream: _Stream, run: HostRun, request: ClaudeRequest, discovered: str) -> str | None:
    """Choose the terminal state; completion needs every consistency check to pass."""
    result = stream.result
    unsafe = bool(type(result) is dict and result.get("permission_denials"))
    unverified = stream.init_seen and stream.key_source not in SUBSCRIPTION_KEY_SOURCES
    if run.cancelled or run.timed_out:
        if unsafe or unverified:  # refusal outranks interruption
            if unsafe:
                stream.append("error", text="permission-denied")
            if unverified:
                stream.append("error", text="route-unverified")
            return "refused"
        return "interrupted"
    if result is None:
        stream.errors.append("missing-result")
        return "failed" if run.exit_code else None
    state = "completed" if result.get("subtype") == "success" and result.get("is_error") is False \
        else "failed"
    if unsafe:
        stream.append("error", text="permission-denied")
        state = "refused"
    if stream.session != request.session_id or result.get("session_id") != request.session_id:
        stream.append("error", text="session-mismatch")
        state = "failed" if state == "completed" else state
    if stream.version != discovered:
        stream.append("error", text="version-drift")
        state = "failed" if state == "completed" else state
    if request.model is not None and stream.model != request.model:
        stream.append("error", text="model-drift")
        state = "failed" if state == "completed" else state
    if stream.key_source not in SUBSCRIPTION_KEY_SOURCES:
        stream.append("error", text="route-unverified")
        state = "refused"
    if state == "completed" and run.exit_code != 0:
        stream.append("error", text="exit-mismatch")
        state = "failed"
    return state


@dataclass(frozen=True)
class ClaudeHostResult:
    """Evidence about one host run; never an authorization."""

    observation: Observation
    transport: str
    session_id: str
    host_version: str | None
    host_model: str | None
    exit_code: int | None
    timed_out: bool
    cancelled: bool
    settled: bool
    output_truncated: bool

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {"observationSha256": self.observation.sha256, "host": HOST,
                "transport": self.transport, "sessionId": self.session_id,
                "hostVersion": self.host_version, "hostModel": self.host_model,
                "exitCode": self.exit_code, "timedOut": self.timed_out,
                "cancelled": self.cancelled, "settled": self.settled,
                "outputTruncated": self.output_truncated, "executionAuthorization": False}


def run_claude(manifest: HarnessManifest, context: ContextPackage, *, transport: ClaudeTransport,
               request: ClaudeRequest, compatibility: CompatibilityWindow, attempt_id: str,
               inventory: ExportInventory, now: int, retention_seconds: int,
               limits: HostLimits | None = None, cancel: threading.Event | None = None,
               qualification: HostQualification | None = None) -> ClaudeHostResult:
    """Dispatch one Claude run through ``transport`` and observe it; refuse, never repair."""
    limits = limits or HostLimits()
    cancel = cancel or threading.Event()
    _require(isinstance(manifest, HarnessManifest) and isinstance(context, ContextPackage)
             and isinstance(request, ClaudeRequest) and isinstance(limits, HostLimits)
             and isinstance(compatibility, CompatibilityWindow)
             and isinstance(cancel, threading.Event))
    label = _check_transport(transport, manifest, qualification, now)
    _require(label == "native" or limits.wall_seconds <= MAX_WALL_SECONDS, "invalid-limits")
    prompt = context.render().encode("utf-8")
    _require(0 < len(prompt) <= MAX_PROMPT_BYTES, "invalid-context")
    plan = build_plan(request, prompt)
    observe_args = dict(manifest_sha256=manifest.sha256, attempt_id=attempt_id,
                        source="fixture" if label == "double" else "host", inventory=inventory,
                        now=now, retention_seconds=retention_seconds)
    try:
        observe([], **observe_args)  # validate arguments before anything launches
    except ObservationError as exc:
        raise ClaudeHostError(exc.reason) from None
    _require(not cancel.is_set(), "cancelled-before-launch")
    try:
        discovered = transport.version()
        _require(compatibility.admits(parse_version(discovered)), "unsupported-version")
        run = transport.run(plan, prompt, limits, cancel)
    except ClaudeHostError:
        raise
    except Exception:  # untrusted transport: fixed reason only
        raise ClaudeHostError("transport-failed") from None
    _require(isinstance(run, HostRun) and type(run.stdout) is bytes, "invalid-transport-result")
    stream = _read_stream(run.stdout[:limits.max_output_bytes], inventory.secrets)
    state = _terminal(stream, run, request, discovered)
    if state is not None:
        stream.append("terminal", state=state)
    if run.output_truncated or len(run.stdout) > limits.max_output_bytes:
        stream.errors.append("output-truncated")
    if not run.settled:
        stream.errors.append("unsettled-child")
    try:
        observation = observe(stream.events, transport_errors=list(dict.fromkeys(stream.errors)),
                              **observe_args)
    except ObservationError as exc:
        raise ClaudeHostError(exc.reason) from None
    return ClaudeHostResult(observation, label, request.session_id, stream.version, stream.model,
                            run.exit_code, run.timed_out, run.cancelled, run.settled,
                            run.output_truncated)
