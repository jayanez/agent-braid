# SPDX-License-Identifier: AGPL-3.0-only
"""Codex host adapter behind the laboratory contract, deterministic doubles only.

Typed launch specification, Codex JSONL stream normalization into T012 events,
cancellation and wall-clock timeout with child settlement, build/model/route/auth
discovery with freshness, and a handoff to an independent outcome verifier. The
adapter drives a ``CodexHost`` interface. The only host that can run is the exact
``ScriptedCodexHost`` double; ``NativeCodexHost`` and any other host refuse. Real
Codex dispatch stays refused until a separately obtained T008 qualification exists,
and no value in this module can stand in for one (``NATIVE_DISPATCH_QUALIFIED`` is
a constant, not a parameter).

Existing authentication is preserved by never touching it: the launch passes no
credentials, accepts only an allow-listed environment and refuses any API-key,
base-URL or token variable, any non-subscription route and any discovered API-key
authentication, so there is no paid fallback. Flags and event shapes follow the
documented ``codex exec --json`` surface but are unverified against a native build.
A result is evidence, never authorization: ``executionAuthorization`` stays false.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import re
from typing import Any

from .harness_lab import MAX_WALL_SECONDS
from .harness_manifest import HarnessManifest
from .harness_observation import (
    MAX_ARTIFACT_BYTES, MAX_ARTIFACTS, MAX_EVENTS, ExportInventory, ObservationError,
    Observation, _is_relative, observe)
from .system_one import InvalidDecision, canonical, parse_json

LAUNCH_FORMAT = "braid-harness-codex-launch/v0.1"
NATIVE_DISPATCH_QUALIFIED = False  # flips only with a separately obtained T008 record
MAX_DISCOVERY_AGE_SECONDS = 300
MAX_LINE_BYTES = 32_768
MAX_TEXT_BYTES = 4000
READ_SIZE = 4096
MAX_READS = 20_000
ROUTE = "subscription"
AUTH = "existing-login"
EFFORTS = ("minimal", "low", "medium", "high")
SANDBOXES = ("read-only", "workspace-write")
ENV_ALLOWED = frozenset({"HOME", "PATH", "CODEX_HOME", "LANG", "LC_ALL", "TMPDIR"})
_PAID_ENV = re.compile(r"(?i)(API_KEY|_TOKEN|SECRET|BASE_URL|ORG|^OPENAI_|^CODEX_API|^AZURE_)")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_BUILD = re.compile(r"codex-cli [0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.]{1,32})?\Z")
_DISCOVERY_KEYS = {"build", "model", "route", "auth", "provider"}
PROVIDERS = frozenset({"openai"})  # the only provider behind the subscription route


class CodexHostError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-codex-request"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-codex-request") -> None:
    if not condition:
        raise CodexHostError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


# --- typed launch -------------------------------------------------------------------


@dataclass(frozen=True)
class CodexLaunch:
    """Typed, validated launch request. The prompt travels by stdin as a hash only."""

    manifest_sha256: str
    executable: str
    executable_sha256: str
    build: str
    model: str
    effort: str
    prompt_sha256: str
    sandbox: str = "workspace-write"
    env: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require(_hash(self.manifest_sha256) and _hash(self.executable_sha256)
                 and _hash(self.prompt_sha256), "invalid-launch")
        _require(type(self.executable) is str and self.executable.startswith("/")
                 and "\x00" not in self.executable and len(self.executable) <= 512,
                 "invalid-launch")
        _require(type(self.build) is str and _BUILD.fullmatch(self.build) is not None,
                 "invalid-launch")
        _require(type(self.model) is str and _ID.fullmatch(self.model) is not None,
                 "invalid-launch")
        _require(self.effort in EFFORTS and self.sandbox in SANDBOXES, "invalid-launch")
        _require(type(self.env) is tuple and len(self.env) <= len(ENV_ALLOWED)
                 and all(type(p) is tuple and len(p) == 2 and type(p[0]) is str
                         and type(p[1]) is str and "\x00" not in p[1] and len(p[1]) <= 1024
                         for p in self.env), "invalid-launch")
        names = [name for name, _ in self.env]
        _require(len(set(names)) == len(names), "invalid-launch")
        for name in names:  # paid-capable variables are named before the allow-list
            _require(_PAID_ENV.search(name) is None, "paid-fallback-refused")
            _require(name in ENV_ALLOWED, "env-not-allowed")

    @property
    def argv(self) -> tuple[str, ...]:
        return (self.executable, "exec", "--json", "--model", self.model,
                "-c", f"model_reasoning_effort={self.effort}", "--sandbox", self.sandbox, "-")

    def to_dict(self) -> dict:
        return {"format": LAUNCH_FORMAT, "manifestSha256": self.manifest_sha256,
                "argv": list(self.argv), "executableSha256": self.executable_sha256,
                "build": self.build, "model": self.model, "effort": self.effort,
                "route": ROUTE, "auth": AUTH, "promptSha256": self.prompt_sha256,
                "env": sorted(name for name, _ in self.env), "executionAuthorization": False}

    @property
    def sha256(self) -> str:
        return sha256(canonical(self.to_dict())).hexdigest()


@dataclass(frozen=True)
class HostLimits:
    """Trusted supervisor bounds; never read from host output."""

    wall_seconds: int = 10
    max_output_bytes: int = 65_536

    def __post_init__(self) -> None:
        _require(_int(self.wall_seconds, 1, MAX_WALL_SECONDS)
                 and _int(self.max_output_bytes, 1, 1_048_576), "invalid-limits")


class CancelToken:
    """Caller-held cancellation flag polled by the supervisor between reads."""

    def __init__(self) -> None:
        self._set = False

    def set(self) -> None:
        self._set = True

    def is_set(self) -> bool:
        return self._set


# --- discovery ----------------------------------------------------------------------


@dataclass(frozen=True)
class HostDiscovery:
    """Fresh, strictly parsed build/model/route/auth observation; unknown stays None."""

    build: str | None
    model: str | None
    route: str | None
    auth: str | None
    provider: str | None
    observed_at: int

    def to_dict(self) -> dict:
        return {"build": self.build, "model": self.model, "route": self.route,
                "auth": self.auth, "provider": self.provider, "observedAt": self.observed_at}


def parse_discovery(raw: Any, *, now: int) -> HostDiscovery:
    """Parse a host-reported discovery record; malformed or unknown fields refuse."""
    _require(type(raw) is dict and set(raw) - {"observedAt"} == _DISCOVERY_KEYS
             and _DISCOVERY_KEYS <= set(raw), "invalid-discovery")
    _require(_int(now, 0, 1 << 40), "invalid-time")
    observed = raw.get("observedAt", now)  # the host's own observation time, else supervisor now
    _require(_int(observed, 0, 1 << 40), "invalid-discovery")
    build = raw["build"]
    _require(build is None or (type(build) is str and _BUILD.fullmatch(build) is not None),
             "invalid-discovery")
    for key in ("model", "provider"):
        _require(raw[key] is None or (type(raw[key]) is str and _ID.fullmatch(raw[key])),
                 "invalid-discovery")
    _require(raw["route"] in (None, "subscription", "api"), "invalid-discovery")
    _require(raw["auth"] in (None, "existing-login", "api-key"), "invalid-discovery")
    return HostDiscovery(build, raw["model"], raw["route"], raw["auth"], raw["provider"], observed)


def verify_discovery(spec: CodexLaunch, discovery: HostDiscovery, *, now: int) -> None:
    """Refuse stale, unknown, drifted or paid-capable discovery before any launch."""
    _require(isinstance(discovery, HostDiscovery), "invalid-discovery")
    _require(0 <= now - discovery.observed_at <= MAX_DISCOVERY_AGE_SECONDS, "discovery-stale")
    _require(discovery.auth != "api-key" and discovery.route != "api", "paid-fallback-refused")
    _require(discovery.route == ROUTE and discovery.auth == AUTH, "route-unobserved")
    _require(discovery.build == spec.build and discovery.model == spec.model, "discovery-drift")
    _require(discovery.provider in PROVIDERS, "provider-not-allowed")


# --- host interface and doubles -----------------------------------------------------


class HostSession:
    """Interface: one supervised Codex process. ``read`` returns bytes, ``b""`` when
    nothing is ready yet, or ``None`` at end of stream."""

    def read(self, size: int) -> bytes | None:
        raise NotImplementedError

    def elapsed(self) -> float:
        raise NotImplementedError

    def cancel(self) -> None:
        raise NotImplementedError

    def exit_code(self) -> int | None:
        raise NotImplementedError

    def kill_children(self) -> None:
        raise NotImplementedError

    def live_children(self) -> int:
        raise NotImplementedError

    def files(self) -> Mapping[str, bytes]:
        raise NotImplementedError

    def close(self) -> bool:
        raise NotImplementedError


class CodexHost:
    """Interface: a Codex host. Only the exact scripted double runs."""

    def discover(self) -> Any:
        raise NotImplementedError

    def post_discover(self) -> Any:
        """Re-observe build/model/route/auth after the run for the route-drift check."""
        raise NotImplementedError

    def open(self, spec: CodexLaunch, inputs: Mapping[str, bytes]) -> HostSession:
        raise NotImplementedError


class NativeCodexHost(CodexHost):
    """Placeholder for real dispatch: refuses until T008 qualifies it separately."""

    def discover(self) -> Any:
        raise CodexHostError("native-dispatch-unqualified")

    def post_discover(self) -> Any:
        raise CodexHostError("native-dispatch-unqualified")

    def open(self, spec: CodexLaunch, inputs: Mapping[str, bytes]) -> HostSession:
        raise CodexHostError("native-dispatch-unqualified")


@dataclass(frozen=True)
class Script:
    """Deterministic behaviour of one double session.

    ``chunks`` entries are delivered one per read; the string ``"hang"`` makes every
    later read return nothing while the virtual clock advances by ``tick``.
    """

    discovery: Mapping[str, Any]
    chunks: tuple[bytes | str, ...] = ()
    exit_code: int | None = 0
    children: int = 0
    unkillable: bool = False
    tick: float = 0.0
    files: Mapping[str, bytes] = field(default_factory=dict)
    post_discovery: Mapping[str, Any] | None = None
    read_error_at: int | None = None
    open_error: bool = False
    on_read: Callable[[int], None] | None = None


class _ScriptedSession(HostSession):
    def __init__(self, script: Script):
        self._s, self._reads, self._cancelled = script, 0, False
        self._children, self._hung = script.children, False

    def read(self, size: int) -> bytes | None:
        index, self._reads = self._reads, self._reads + 1
        if self._s.on_read is not None:
            self._s.on_read(index)
        if self._s.read_error_at == index:
            raise OSError("scripted transport failure")
        if self._cancelled or (index >= len(self._s.chunks) and not self._hung):
            return None
        chunk = self._s.chunks[index] if index < len(self._s.chunks) else "hang"
        self._hung = self._hung or chunk == "hang"
        return b"" if self._hung else chunk

    def elapsed(self) -> float:
        return self._reads * self._s.tick

    def cancel(self) -> None:
        self._cancelled = True

    def exit_code(self) -> int | None:
        if self._hung:
            return -15 if self._cancelled else None  # terminated by the supervisor
        return self._s.exit_code

    def kill_children(self) -> None:
        if not self._s.unkillable:
            self._children = 0

    def live_children(self) -> int:
        return self._children

    def files(self) -> Mapping[str, bytes]:
        return dict(self._s.files)

    def close(self) -> bool:
        return True


class ScriptedCodexHost(CodexHost):
    """The only runnable host: replays a ``Script``; no process, network or credential."""

    def __init__(self, script: Script):
        self._script, self.opened = script, 0

    def discover(self) -> Any:
        return dict(self._script.discovery)

    def post_discover(self) -> Any:
        post = self._script.post_discovery
        return dict(self._script.discovery if post is None else post)

    def open(self, spec: CodexLaunch, inputs: Mapping[str, bytes]) -> HostSession:
        if self._script.open_error:
            raise OSError("scripted launch failure")
        self.opened += 1
        return _ScriptedSession(self._script)


# --- stream normalization -----------------------------------------------------------

_IGNORED_TYPES = frozenset({"turn.started", "item.started", "item.updated"})
_IGNORED_ITEMS = frozenset({"reasoning", "todo_list"})
_CHANGE_EFFECT = {"add": "create", "update": "write", "delete": "delete"}


def _clip(text: str) -> tuple[str, int]:
    data = text.encode("utf-8", "replace")
    if len(data) <= MAX_TEXT_BYTES:
        return text, len(data)
    return data[:MAX_TEXT_BYTES].decode("utf-8", "ignore"), len(data)


class _Normalizer:
    """Maps Codex JSONL lines to T012 events; unknown shapes become malformed events."""

    def __init__(self) -> None:
        self.events: list[dict] = []
        self.errors: list[str] = []
        self.ignored = 0
        self.usage: dict[str, int] = {}
        self.host_terminal: str | None = None
        self.started = False
        self.overflow = False

    def _emit(self, kind: str, **fields: Any) -> None:
        if len(self.events) >= MAX_EVENTS:
            if not self.overflow:
                self.overflow = True
                self.errors.append("event-overflow")
            return
        self.events.append({"seq": len(self.events), "kind": kind, **fields})

    def _bad(self) -> None:
        self._emit("unknown")  # not a T012 kind: counted as malformed, forbids completion

    def line(self, line: bytes) -> None:
        try:
            raw = parse_json(line)
        except InvalidDecision:
            self.errors.append("malformed-line")
            return
        kind = raw.get("type") if type(raw) is dict else None
        if kind is None or type(kind) is not str:
            self._bad()
        elif kind == "thread.started" and not self.started:
            self.started = True
            self._emit("start")
        elif kind in _IGNORED_TYPES:
            self.ignored += 1
        elif kind == "item.completed":
            self._item(raw.get("item"))
        elif kind == "turn.completed":
            self._complete(raw.get("usage"))
        elif kind == "turn.failed":
            self._fail(raw.get("error"))
        elif kind == "error":
            self._error(raw.get("message"))
        else:
            self._bad()

    def _item(self, item: Any) -> None:
        kind = item.get("type") if type(item) is dict and type(item.get("type")) is str else None
        if kind in _IGNORED_ITEMS:
            self.ignored += 1
        elif kind == "agent_message" and type(item.get("text")) is str:
            text, size = _clip(item["text"])
            self._emit("message", text=text, textBytes=size)
        elif kind == "command_execution":
            code = item.get("exit_code")
            extra = {"exitCode": code} if _int(code, -255, 255) else {}
            self._emit("tool", tool="command_execution", **extra)
            self._emit("effect", effect="process")
        elif kind == "mcp_tool_call" and type(item.get("server")) is str \
                and type(item.get("tool")) is str:
            self._emit("tool", tool=("mcp:" + item["server"] + "." + item["tool"])[:200])
        elif kind == "web_search":
            self._emit("effect", effect="network")
        elif kind == "file_change" and type(item.get("changes")) is list and item["changes"]:
            for change in item["changes"]:
                effect = (_CHANGE_EFFECT.get(change.get("kind"))
                          if type(change) is dict and type(change.get("kind")) is str else None)
                path = change.get("path") if type(change) is dict else None
                if effect is None or type(path) is not str:
                    self._bad()
                else:
                    self._emit("effect", effect=effect, path=path)
        else:
            self._bad()

    def _terminal(self, state: str) -> None:
        self.host_terminal = self.host_terminal or state
        self._emit("terminal", state=state)

    def _complete(self, usage: Any) -> None:
        if type(usage) is dict:
            self.usage = {k: v for k, v in usage.items()
                          if type(k) is str and _int(v, 0, 1 << 40) and re.fullmatch(r"[a-z_]{1,40}", k)}
        self._terminal("completed")

    def _fail(self, error: Any) -> None:
        self._error(error.get("message") if type(error) is dict else None)
        self._terminal("failed")

    def _error(self, message: Any) -> None:
        text, size = _clip(message if type(message) is str else "")
        self._emit("error", text=text, textBytes=size)


def _split(buffer: bytes) -> tuple[list[bytes], bytes]:
    *lines, rest = buffer.split(b"\n")
    return [line for line in lines if line], rest


@dataclass
class _Stream:
    cancelled: bool = False
    timed_out: bool = False
    truncated: bool = False
    clean_eof: bool = False


def _stream(session: HostSession, limits: HostLimits, cancel: CancelToken,
            norm: _Normalizer) -> _Stream:
    out, buffer, total = _Stream(), b"", 0
    for _ in range(MAX_READS):
        if cancel.is_set():
            out.cancelled = True
            break
        try:
            if session.elapsed() >= limits.wall_seconds:
                out.timed_out = True
                break
            chunk = session.read(READ_SIZE)
        except Exception:  # untrusted host: surface a fixed reason only
            norm.errors.append("transport-error")
            break
        if chunk is None:
            out.clean_eof = True
            break
        if type(chunk) is not bytes:
            norm.errors.append("transport-error")
            break
        if total + len(chunk) > limits.max_output_bytes:
            chunk = chunk[:limits.max_output_bytes - total]
            out.truncated = True
        total += len(chunk)
        lines, buffer = _split(buffer + chunk)
        for line in lines:
            if len(line) > MAX_LINE_BYTES:
                norm.errors.append("line-overflow")
            else:
                norm.line(line)
        if out.truncated or norm.overflow or len(buffer) > MAX_LINE_BYTES:
            if len(buffer) > MAX_LINE_BYTES:
                norm.errors.append("line-overflow")
            break
    else:
        out.timed_out = True  # read budget exhausted without progress
    if out.clean_eof and buffer:
        norm.errors.append("truncated-final-line")
    if out.truncated:
        norm.errors.append("output-truncated")
    return out


# --- outcome verifier handoff -------------------------------------------------------


@dataclass(frozen=True)
class VerifierRequest:
    """What the independent verifier sees: hashes and artifacts, no host claim."""

    attempt_id: str
    manifest_sha256: str
    observation_sha256: str
    artifacts: Mapping[str, bytes]


class OutcomeVerifier:
    """Interface: oracle independent of the host, bound to the manifest verifier hash."""

    sha256 = ""

    def verify(self, request: VerifierRequest) -> str:
        raise NotImplementedError


# --- run ----------------------------------------------------------------------------


@dataclass(frozen=True)
class CodexRunResult:
    """Evidence about one double run; never an authorization."""

    observation: Observation
    launch_sha256: str
    discovery: HostDiscovery
    host: str
    exit_code: int | None
    cancelled: bool
    timed_out: bool
    settled: bool
    cleaned: bool
    usage: Mapping[str, int]
    ignored_events: int
    outcome: str

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {"observationSha256": self.observation.sha256, "launchSha256": self.launch_sha256,
                "discovery": self.discovery.to_dict(), "host": self.host,
                "exitCode": self.exit_code, "cancelled": self.cancelled,
                "timedOut": self.timed_out, "settled": self.settled, "cleaned": self.cleaned,
                "usage": dict(self.usage), "cashMicros": None, "route": ROUTE,
                "ignoredEvents": self.ignored_events, "outcome": self.outcome,
                "executionAuthorization": False}


def _settle(session: HostSession) -> bool:
    try:
        session.kill_children()
        return session.live_children() == 0
    except Exception:
        return False


def _supervisor_terminal(norm: _Normalizer, stream: _Stream, exit_code: int | None) -> None:
    """Record a termination the supervisor itself observed; never a completion."""
    if norm.host_terminal is not None:
        return
    interrupted = stream.cancelled or stream.timed_out or stream.truncated
    state = "interrupted" if interrupted else "failed" if exit_code else None
    if state:
        norm._emit("terminal", state=state)


def _artifacts(files: Any) -> dict[str, bytes] | None:
    try:
        ok = isinstance(files, Mapping) and len(files) <= MAX_ARTIFACTS and all(
            _is_relative(p) and type(c) is bytes and len(c) <= MAX_ARTIFACT_BYTES
            for p, c in files.items())
    except Exception:
        ok = False
    return dict(files) if ok else None


def _handoff(verifier: OutcomeVerifier | None, observation: Observation, settled: bool,
             after: dict[str, bytes] | None, attempt_id: str, manifest_sha256: str) -> str:
    """Host success is a claim; only an independent verifier pass makes it verified."""
    if observation.to_dict()["terminal"] != "completed" or not settled or after is None:
        return "unverified"
    if verifier is None:
        return "unverified-no-verifier"
    try:
        verdict = verifier.verify(VerifierRequest(attempt_id, manifest_sha256,
                                                  observation.sha256, dict(after)))
    except Exception:
        return "inconclusive"
    if type(verdict) is not str:
        return "inconclusive"
    return {"pass": "verified", "fail": "rejected"}.get(verdict, "inconclusive")


def run_codex(spec: CodexLaunch, host: CodexHost, *, manifest: HarnessManifest,
              attempt_id: str, inventory: ExportInventory, now: int, retention_seconds: int,
              inputs: Mapping[str, bytes] | None = None, limits: HostLimits | None = None,
              cancel: CancelToken | None = None,
              verifier: OutcomeVerifier | None = None) -> CodexRunResult:
    """Drive the scripted Codex double and observe it; refuse, never repair."""
    _require(isinstance(spec, CodexLaunch) and isinstance(manifest, HarnessManifest))
    # Exact type: no subclass, native host or caller-set ``kind`` can ride the double path.
    if type(host) is not ScriptedCodexHost:
        raise CodexHostError("native-dispatch-unqualified")
    limits = limits or HostLimits()
    cancel = cancel or CancelToken()
    inputs = {} if inputs is None else inputs
    _require(isinstance(limits, HostLimits) and isinstance(cancel, CancelToken))
    _require(spec.manifest_sha256 == manifest.sha256, "manifest-drift")
    _require(limits.max_output_bytes <= manifest.data["limits"]["maxStageOutputBytes"],
             "invalid-limits")
    _require(isinstance(inputs, Mapping) and _artifacts(inputs) is not None, "invalid-inputs")
    if verifier is not None:
        _require(not isinstance(verifier, (CodexHost, HostSession)), "verifier-not-independent")
        _require(verifier.sha256 == manifest.data["verifier"]["sha256"], "verifier-drift")
    observe_args = dict(manifest_sha256=manifest.sha256, attempt_id=attempt_id, source="fixture",
                        inventory=inventory, now=now, retention_seconds=retention_seconds)
    try:
        observe([], **observe_args)  # validate arguments before anything is launched
    except ObservationError as exc:
        raise CodexHostError(exc.reason) from None

    try:
        discovery = parse_discovery(host.discover(), now=now)
    except CodexHostError:
        raise
    except Exception:
        raise CodexHostError("discovery-failed") from None
    verify_discovery(spec, discovery, now=now)
    try:
        session = host.open(spec, dict(inputs))
    except Exception:
        raise CodexHostError("launch-failed") from None

    norm = _Normalizer()
    try:
        stream = _stream(session, limits, cancel, norm)
        if stream.cancelled or stream.timed_out or stream.truncated or norm.overflow \
                or not stream.clean_eof:
            try:
                session.cancel()
            except Exception:
                norm.errors.append("cancel-failed")
        settled = _settle(session)
        if not settled:
            norm.errors.append("unsettled-child")
        try:
            exit_code = session.exit_code()
            after = _artifacts(session.files())
        except Exception:
            exit_code, after = None, None
        if (stream.cancelled or stream.timed_out) and norm.host_terminal == "completed":
            norm.errors.append("completion-contradicts-supervisor")
        if norm.host_terminal == "completed" and exit_code:
            norm.errors.append("exit-contradicts-completion")
        try:
            post = parse_discovery(host.post_discover(), now=now)
            if (post.build, post.model, post.route, post.auth, post.provider) != (
                    discovery.build, discovery.model, discovery.route, discovery.auth,
                    discovery.provider):
                norm.errors.append("route-drift")
        except Exception:
            norm.errors.append("route-drift")
        if after is None:
            norm.errors.append("artifact-unobservable")
        _supervisor_terminal(norm, stream, exit_code)
        try:
            observation = observe(
                norm.events, before=dict(inputs) if after is not None else None, after=after,
                transport_errors=list(dict.fromkeys(norm.errors)), **observe_args)
        except ObservationError as exc:
            raise CodexHostError(exc.reason) from None
        outcome = _handoff(verifier, observation, settled, after, attempt_id, manifest.sha256)
    finally:
        try:
            cleaned = session.close() is True
        except Exception:
            cleaned = False
    return CodexRunResult(observation, spec.sha256, discovery, "double", exit_code,
                          stream.cancelled, stream.timed_out, settled, cleaned,
                          dict(norm.usage), norm.ignored, outcome)
