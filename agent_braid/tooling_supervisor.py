# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded one-shot POSIX process supervision for future tooling capture.

This module launches only an explicit local executable. It does not authorize a
host/provider call, inspect or issue grants, or authenticate measurements. The
caller must inject a trusted observer for cumulative costs and stop state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import threading
import time
from typing import Callable, Mapping

from . import tooling_capture as capture


MAX_OUTPUT_BYTES = 64 * 1024 * 1024
MAX_STDIN_BYTES = 4 * 1024 * 1024
MAX_ARGUMENTS = 256
MAX_ARGUMENT_BYTES = 64 * 1024
MAX_ENV_ENTRIES = 256
MAX_ENV_BYTES = 64 * 1024
READ_CHUNK_BYTES = 64 * 1024
MAX_RETAINED_SNAPSHOTS = 512
MAX_RECEIPT_BYTES = 256 * 1024
APPROVED_CAPS = {
    "eur": 25.0,
    "tokens": 4_000_000,
    "wall_seconds": 57_600.0,
    "rss_bytes": 4 * 1024**3,
    "disk_bytes": 5 * 1024**3,
}
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_COST_FIELDS = ("eur", "tokens", "input_tokens", "output_tokens", "retry_tokens",
                "wall_seconds", "rss_bytes", "disk_bytes")


class SupervisorError(ValueError):
    """A process request is malformed, unsafe, reused, or unsupported."""


@dataclass(frozen=True)
class BudgetCaps:
    """Frozen per-cohort maxima; no defaults imply permission to spend."""

    eur: float
    tokens: int
    wall_seconds: float
    rss_bytes: int
    disk_bytes: int

    def __post_init__(self) -> None:
        values = self.as_dict()
        for name, value in values.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise SupervisorError(f"{name} cap must be a finite number")
            if not math.isfinite(value) or value <= 0 or value > APPROVED_CAPS[name]:
                raise SupervisorError(f"{name} cap is outside the approved maximum")
        if type(self.tokens) is not int or type(self.rss_bytes) is not int or type(self.disk_bytes) is not int:
            raise SupervisorError("token, RSS, and disk caps must be integers")

    @classmethod
    def from_registration(cls, registration) -> "BudgetCaps":
        """Read the registered caps after a caller has authenticated registration."""
        try:
            values = registration.data["costCaps"]
            result = cls(values["eur"], values["tokens"], values["wall_seconds"],
                         values["rss_bytes"], values["disk_bytes"])
        except (AttributeError, KeyError, TypeError) as exc:
            raise SupervisorError("registration does not contain exact cost caps") from exc
        return result

    def as_dict(self) -> dict[str, int | float]:
        return {"eur": self.eur, "tokens": self.tokens,
                "wall_seconds": self.wall_seconds, "rss_bytes": self.rss_bytes,
                "disk_bytes": self.disk_bytes}


@dataclass(frozen=True)
class ProcessRequest:
    executable: Path
    executable_sha256: str
    argv: tuple[str, ...]
    cwd: Path
    output_root: Path
    source_roots: tuple[Path, ...]
    grant_root: Path | None
    env: Mapping[str, str]
    stdin: bytes | None
    max_output_bytes: int
    timeout_seconds: float
    observation_max_age_seconds: float
    poll_interval_seconds: float
    term_grace_seconds: float
    kill_grace_seconds: float


@dataclass(frozen=True)
class TelemetrySnapshot:
    """One externally collected cumulative observation; unknowns are not zero."""

    costs: capture.MeasuredCosts
    stop_state: capture.StopState


@dataclass(frozen=True)
class ProcessIdentity:
    pid: int
    process_group_id: int
    started_at: str
    executable_sha256: str


@dataclass(frozen=True)
class Clock:
    monotonic: Callable[[], float] = time.monotonic
    utc_now: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat(
        timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class ProcessOutcome:
    status: str
    launched: bool
    returncode: int | None
    signal: int | None
    started_at: str | None
    ended_at: str
    wall_elapsed_seconds: float
    stdout_bytes: int
    stderr_bytes: int
    stdout_bytes_observed: int
    stderr_bytes_observed: int
    stdout_sha256: str | None
    stderr_sha256: str | None
    stdout_path: Path | None
    stderr_path: Path | None
    receipt_path: Path | None
    receipt_sha256: str | None
    last_snapshot: TelemetrySnapshot | None
    limits: tuple[str, ...]
    reason: str | None
    group_cleanup: str
    snapshots: tuple[TelemetrySnapshot, ...] = field(default_factory=tuple)

    @property
    def completed(self) -> bool:
        return self.status == "completed" and self.returncode == 0 and self.group_cleanup == "clean"


Observer = Callable[[ProcessIdentity | None, float], TelemetrySnapshot]


def run_supervised(
    request: ProcessRequest,
    caps: BudgetCaps,
    observer: Observer,
    *,
    cancel_event: threading.Event | None = None,
    clock: Clock = Clock(),
) -> ProcessOutcome:
    """Validate, start once, multiplex pipes, observe budgets, and reap the process.

    A returned non-``completed`` status is never a successful host observation.
    Calls to the observer are trusted external measurement boundaries.
    """
    if os.name != "posix":
        raise SupervisorError("the process supervisor requires POSIX process groups")
    _validate_request(request, caps, observer, clock)
    executable, cwd, output_root, source_roots, grant_root, env = _resolve_paths(request)
    _ensure_fresh_output_root(output_root)
    expected_executable = _hash_executable(executable)
    if expected_executable != request.executable_sha256:
        return _not_launched("start-drift", "executable SHA-256 differs from the pinned value", clock)
    started_at = _utc(clock)

    try:
        initial = observer(None, 0.0)
        _validate_snapshot(initial, caps, request, None, clock, None)
    except Exception as exc:
        return _not_launched("measurement-unknown", _safe_reason(exc), clock)
    activity_start_mono = clock.monotonic()
    if cancel_event is not None and cancel_event.is_set():
        return _not_launched("cancelled", "cancelled before process launch", clock, initial)
    stop = _stop_reason(initial, caps)
    if stop is not None:
        return _not_launched("refused", stop, clock, initial)
    wall_remaining = caps.wall_seconds - float(initial.costs.values["wall_seconds"])
    runtime_deadline = min(request.timeout_seconds, wall_remaining)
    if runtime_deadline <= 0:
        return _not_launched("refused", "registered cumulative wall cap is already reached", clock, initial)

    # The observer is external code and may take time; recheck the executable
    # immediately before creating any process or durable start record.
    if _hash_executable(executable) != request.executable_sha256:
        return _not_launched("start-drift", "executable changed during pre-dispatch observation", clock, initial)

    stdout_path = output_root / "stdout.partial"
    stderr_path = output_root / "stderr.partial"
    started_path = output_root / "started.json"
    receipt_path = output_root / "outcome.json"
    for path in (stdout_path, stderr_path, started_path, receipt_path):
        if path.exists() or path.is_symlink():
            raise SupervisorError("one-shot output root already contains a supervisor artifact")
    started_record = {
        "schemaVersion": "agent-braid-process-supervisor-v1", "status": "launch-reserved",
        "executableSha256": request.executable_sha256,
        "argvSha256": _sha(_json_bytes(list(request.argv))),
        "stdinBytes": len(request.stdin or b""),
        "environmentEntryCount": len(env), "preDispatchSnapshot": _snapshot_dict(initial),
        "preDispatchAt": started_at,
    }
    start_recorded = False
    out_fd = err_fd = None
    try:
        out_fd = _open_exclusive(stdout_path)
        err_fd = _open_exclusive(stderr_path)
        _write_exclusive(started_path, _json_bytes(started_record))
        start_recorded = True
    except OSError as exc:
        for fd in (out_fd, err_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
        for path in (stdout_path, stderr_path):
            try:
                path.unlink()
            except OSError:
                pass
        raise SupervisorError("could not reserve private one-shot output artifacts") from exc

    process: subprocess.Popen[bytes] | None = None
    selector = selectors.DefaultSelector()
    out_hash, err_hash = hashlib.sha256(), hashlib.sha256()
    out_written = err_written = out_seen = err_seen = 0
    input_written = 0
    snapshots = [initial]
    last_snapshot = initial
    identity: ProcessIdentity | None = None
    stop_reason: str | None = None
    stop_status: str | None = None
    term_sent_at: float | None = None
    kill_sent_at: float | None = None
    group_cleanup = "pending"
    returncode: int | None = None
    launched = False
    start_time_mono = activity_start_mono
    reason: str | None = None
    status = "start-failed"
    input_stream = None
    output_streams = {}
    try:
        process = subprocess.Popen(
            [str(executable), *request.argv], cwd=cwd, env=env, stdin=subprocess.PIPE if request.stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False, close_fds=True,
            start_new_session=True, bufsize=0,
        )
        launched = True
        start_time_mono = clock.monotonic()
        identity = ProcessIdentity(process.pid, process.pid, _utc(clock), request.executable_sha256)
        if _hash_executable(executable) != request.executable_sha256:
            stop_reason, stop_status = "executable changed at process start", "start-drift"
        if process.stdout is None or process.stderr is None:
            raise SupervisorError("subprocess pipes were not created")
        output_streams[process.stdout.fileno()] = (process.stdout, out_fd, out_hash, "stdout")
        output_streams[process.stderr.fileno()] = (process.stderr, err_fd, err_hash, "stderr")
        for fd, (stream, _write_fd, _digest, _name) in output_streams.items():
            os.set_blocking(fd, False)
            selector.register(stream, selectors.EVENT_READ, ("read", fd))
        if process.stdin is not None:
            input_stream = process.stdin
            if request.stdin:
                os.set_blocking(input_stream.fileno(), False)
                selector.register(input_stream, selectors.EVENT_WRITE, ("write", input_stream.fileno()))
            else:
                input_stream.close()
                input_stream = None
        next_observation_at = start_time_mono + request.poll_interval_seconds
        while selector.get_map() or process.poll() is None:
            now_mono = clock.monotonic()
            elapsed = max(0.0, now_mono - activity_start_mono)
            process_elapsed = max(0.0, now_mono - start_time_mono)
            if stop_reason is None:
                if cancel_event is not None and cancel_event.is_set():
                    stop_reason, stop_status = "operator cancellation requested", "cancelled"
                elif process_elapsed >= request.timeout_seconds:
                    if request.timeout_seconds <= wall_remaining:
                        stop_reason, stop_status = "process deadline reached", "timed-out"
                    else:
                        stop_reason, stop_status = "registered wall-time cap reached", "budget-exceeded"
                elif float(initial.costs.values["wall_seconds"]) + elapsed >= caps.wall_seconds:
                    stop_reason, stop_status = "registered wall-time cap reached", "budget-exceeded"
                elif now_mono >= next_observation_at:
                    try:
                        observed = observer(identity, elapsed)
                        _validate_snapshot(observed, caps, request, last_snapshot, clock, identity)
                        last_snapshot = observed
                        if len(snapshots) < MAX_RETAINED_SNAPSHOTS:
                            snapshots.append(observed)
                        elif len(snapshots) == MAX_RETAINED_SNAPSHOTS:
                            stop_reason, stop_status = "telemetry snapshot retention limit exceeded", "measurement-unknown"
                        if stop_reason is None:
                            stop = _stop_reason(observed, caps, elapsed)
                            if stop is not None:
                                stop_reason, stop_status = stop, "budget-exceeded"
                    except Exception as exc:
                        stop_reason, stop_status = _safe_reason(exc), "measurement-unknown"
                    next_observation_at = now_mono + request.poll_interval_seconds
            if stop_reason is not None and term_sent_at is None:
                _signal_group(process.pid, signal.SIGTERM)
                term_sent_at = now_mono
            if term_sent_at is not None and kill_sent_at is None \
                    and now_mono - term_sent_at >= request.term_grace_seconds:
                _signal_group(process.pid, signal.SIGKILL)
                kill_sent_at = now_mono
            if kill_sent_at is not None and now_mono - kill_sent_at >= request.kill_grace_seconds:
                if selector.get_map():
                    group_cleanup = "unknown: pipes remained open after SIGKILL grace"
                    _close_selector_streams(selector, output_streams)
                    _close_all_selector_streams(selector)
                    break
                if process.poll() is None:
                    _signal_group(process.pid, signal.SIGKILL)
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        group_cleanup = "unknown: root process was not reaped after SIGKILL"
                        break
            timeout = request.poll_interval_seconds
            if stop_reason is None:
                timeout = min(timeout, max(0.001, request.timeout_seconds - process_elapsed),
                              max(0.001, caps.wall_seconds - float(initial.costs.values["wall_seconds"]) - elapsed),
                              max(0.001, next_observation_at - now_mono))
            elif term_sent_at is not None and kill_sent_at is None:
                timeout = min(timeout, max(0.001, request.term_grace_seconds - (now_mono - term_sent_at)))
            elif kill_sent_at is not None:
                timeout = min(timeout, max(0.001, request.kill_grace_seconds - (now_mono - kill_sent_at)))
            for key, _mask in selector.select(timeout):
                mode, fd = key.data
                if mode == "write":
                    payload = request.stdin or b""
                    try:
                        count = os.write(fd, payload[input_written:input_written + READ_CHUNK_BYTES])
                        input_written += count
                        if input_written >= len(payload):
                            _unregister_close(selector, input_stream)
                            input_stream = None
                    except (BrokenPipeError, OSError):
                        _unregister_close(selector, input_stream)
                        input_stream = None
                else:
                    stream, write_fd, digest, name = output_streams[fd]
                    try:
                        chunk = os.read(fd, READ_CHUNK_BYTES)
                    except BlockingIOError:
                        continue
                    if not chunk:
                        _unregister_close(selector, stream)
                        output_streams.pop(fd, None)
                        continue
                    if name == "stdout":
                        out_seen += len(chunk)
                    else:
                        err_seen += len(chunk)
                    total_written = out_written + err_written
                    capacity = max(0, request.max_output_bytes - total_written)
                    keep = chunk[:capacity]
                    if keep:
                        _write_all(write_fd, keep)
                        digest.update(keep)
                        if name == "stdout":
                            out_written += len(keep)
                        else:
                            err_written += len(keep)
                    if len(keep) < len(chunk) and stop_reason is None:
                        stop_reason, stop_status = "combined stdout/stderr output limit reached", "output-limit"
            if process.poll() is not None and not selector.get_map():
                break

        returncode = process.poll()
        if process is not None and returncode is None:
            try:
                returncode = process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                _signal_group(process.pid, signal.SIGKILL)
                try:
                    returncode = process.wait(timeout=0.5)
                except subprocess.TimeoutExpired:
                    group_cleanup = "unknown: root process could not be reaped"
        if term_sent_at is not None:
            group_cleanup = _cleanup_stopped_group(process.pid, request, group_cleanup)
        else:
            group_cleanup = _clean_or_stop_descendants(process.pid, request)

        elapsed = max(0.0, clock.monotonic() - activity_start_mono)
        try:
            final_snapshot = observer(identity, elapsed)
            _validate_snapshot(final_snapshot, caps, request, last_snapshot, clock, identity)
            last_snapshot = final_snapshot
            if len(snapshots) < MAX_RETAINED_SNAPSHOTS:
                snapshots.append(final_snapshot)
            final_stop = _stop_reason(final_snapshot, caps, elapsed)
            if final_stop is not None and stop_reason is None:
                stop_reason, stop_status = final_stop, "budget-exceeded"
        except Exception as exc:
            if stop_reason is None:
                stop_reason, stop_status = _safe_reason(exc), "measurement-unknown"
        if stop_reason is not None:
            status = stop_status or "measurement-unknown"
            reason = stop_reason
        elif group_cleanup != "clean":
            status = "cleanup-unknown"
            reason = "process group or descendants may remain after root exit"
        elif returncode == 0:
            status = "completed"
        else:
            status = "failed"
            reason = "process exited nonzero or by signal"
    except OSError as exc:
        reason = f"{type(exc).__name__}: process launch or pipe operation failed"
        status = "start-failed" if not launched else "measurement-unknown"
    except Exception as exc:
        reason = _safe_reason(exc)
        status = "measurement-unknown"
    finally:
        if process is not None and process.poll() is None:
            _signal_group(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=request.term_grace_seconds)
            except subprocess.TimeoutExpired:
                _signal_group(process.pid, signal.SIGKILL)
                try:
                    process.wait(timeout=request.kill_grace_seconds)
                except subprocess.TimeoutExpired:
                    group_cleanup = "unknown: root process could not be reaped"
        try:
            selector.close()
        except OSError:
            pass
        for fd in (out_fd, err_fd):
            if fd is None:
                continue
            try:
                os.fsync(fd)
                os.close(fd)
            except OSError:
                pass

    ended_at = _utc(clock)
    wall_elapsed = max(0.0, clock.monotonic() - activity_start_mono) if start_recorded else 0.0
    result_data = {
        "schemaVersion": "agent-braid-process-supervisor-v1", "status": status,
        "launched": launched, "executableSha256": request.executable_sha256,
        "argvSha256": _sha(_json_bytes(list(request.argv))),
        "returncode": returncode, "signal": -returncode if returncode is not None and returncode < 0 else None,
        "startedAt": identity.started_at if identity else None, "endedAt": ended_at,
        "wallElapsedSeconds": wall_elapsed, "stdoutBytesStored": out_written,
        "stderrBytesStored": err_written, "stdoutBytesObserved": out_seen,
        "stderrBytesObserved": err_seen, "stdoutSha256": out_hash.hexdigest(),
        "stderrSha256": err_hash.hexdigest(), "lastSnapshot": _snapshot_dict(last_snapshot),
        "stdoutArtifact": stdout_path.name, "stderrArtifact": stderr_path.name,
        "reason": reason, "groupCleanup": group_cleanup,
        "limits": list(_LIMITS),
    }
    receipt_sha = None
    receipt_result_path: Path | None = None
    if start_recorded:
        try:
            encoded = _json_bytes(result_data)
            if len(encoded) > MAX_RECEIPT_BYTES:
                raise SupervisorError("process outcome receipt exceeds its fixed limit")
            _write_exclusive(receipt_path, encoded)
            receipt_sha = _sha(encoded)
            receipt_result_path = receipt_path
        except (OSError, SupervisorError):
            status = "measurement-unknown"
            reason = "private process outcome receipt could not be persisted"
    return ProcessOutcome(
        status=status, launched=launched, returncode=returncode,
        signal=-returncode if returncode is not None and returncode < 0 else None,
        started_at=identity.started_at if identity else None, ended_at=ended_at,
        wall_elapsed_seconds=wall_elapsed, stdout_bytes=out_written, stderr_bytes=err_written,
        stdout_bytes_observed=out_seen, stderr_bytes_observed=err_seen,
        stdout_sha256=out_hash.hexdigest() if launched else None,
        stderr_sha256=err_hash.hexdigest() if launched else None,
        stdout_path=stdout_path if start_recorded else None, stderr_path=stderr_path if start_recorded else None,
        receipt_path=receipt_result_path, receipt_sha256=receipt_sha, last_snapshot=last_snapshot,
        limits=_LIMITS, reason=reason, group_cleanup=group_cleanup,
        snapshots=tuple(snapshots[:MAX_RETAINED_SNAPSHOTS]),
    )


_LIMITS = (
    "Process RSS is sampled only through the injected observer; sampling is not a continuous peak.",
    "A child may escape the process group; process-group signaling does not prove provider cancellation.",
    "Provider billing, tokens, host success, grants, and human time require independent authenticated sources.",
    "No output text is interpreted as cost, token usage, authority, or successful completion.",
)


def _validate_request(request, caps, observer, clock):
    if not isinstance(request, ProcessRequest) or not isinstance(caps, BudgetCaps):
        raise SupervisorError("typed process request and frozen budget caps are required")
    if not callable(observer) or not callable(clock.monotonic) or not callable(clock.utc_now):
        raise SupervisorError("observer and clock callables are required")
    if not isinstance(request.executable, Path) or not request.executable.is_absolute():
        raise SupervisorError("executable must be an absolute pinned path")
    if not _SHA256.fullmatch(request.executable_sha256):
        raise SupervisorError("executable SHA-256 is malformed")
    if not isinstance(request.argv, tuple) or len(request.argv) > MAX_ARGUMENTS:
        raise SupervisorError("argv must be a bounded tuple")
    if any(not isinstance(arg, str) or "\0" in arg for arg in request.argv):
        raise SupervisorError("argv values must be NUL-free strings")
    if sum(len(arg.encode("utf-8")) for arg in request.argv) > MAX_ARGUMENT_BYTES:
        raise SupervisorError("argv exceeds its fixed byte limit")
    if not isinstance(request.env, Mapping) or len(request.env) > MAX_ENV_ENTRIES:
        raise SupervisorError("an explicit bounded environment mapping is required")
    if any(not isinstance(key, str) or not _ENV_KEY.fullmatch(key)
           or not isinstance(value, str) or "\0" in value for key, value in request.env.items()):
        raise SupervisorError("environment keys and values must be explicit NUL-free strings")
    if sum(len(key.encode()) + len(value.encode()) for key, value in request.env.items()) > MAX_ENV_BYTES:
        raise SupervisorError("environment exceeds its fixed byte limit")
    if request.stdin is not None and (not isinstance(request.stdin, bytes) or len(request.stdin) > MAX_STDIN_BYTES):
        raise SupervisorError("stdin must be absent or bounded bytes")
    if type(request.max_output_bytes) is not int or not 1 <= request.max_output_bytes <= MAX_OUTPUT_BYTES:
        raise SupervisorError("max_output_bytes is outside the independent output bound")
    for field_name in ("timeout_seconds", "observation_max_age_seconds", "poll_interval_seconds",
                       "term_grace_seconds", "kill_grace_seconds"):
        value = getattr(request, field_name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value <= 0:
            raise SupervisorError(f"{field_name} must be finite and positive")
    if request.timeout_seconds > APPROVED_CAPS["wall_seconds"]:
        raise SupervisorError("process timeout exceeds the approved wall-time maximum")
    if request.poll_interval_seconds > request.observation_max_age_seconds:
        raise SupervisorError("poll interval cannot exceed observation freshness bound")
    if not request.source_roots or not isinstance(request.source_roots, tuple):
        raise SupervisorError("explicit read/source roots are required")


def _resolve_paths(request):
    executable = request.executable.resolve(strict=True)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise SupervisorError("pinned executable must be an executable regular file")
    cwd = _private_directory(request.cwd, "working directory")
    output_root = _private_directory(request.output_root, "output root")
    source_roots = tuple(Path(root).expanduser().resolve(strict=True) for root in request.source_roots)
    if any(not root.is_dir() for root in source_roots):
        raise SupervisorError("every source root must be an existing directory")
    grant_root = Path(request.grant_root).expanduser().resolve(strict=False) if request.grant_root is not None else None
    protected = (*source_roots, *((grant_root,) if grant_root is not None else ()))
    for target in (cwd, output_root):
        if any(_overlap(target, root) for root in protected):
            raise SupervisorError("working and output roots must be disjoint from all source and grant roots")
    if _overlap(cwd, output_root):
        raise SupervisorError("working and output roots must be disjoint")
    return executable, cwd, output_root, source_roots, grant_root, dict(request.env)


def _private_directory(path, label):
    resolved = Path(path).expanduser().resolve(strict=True)
    info = resolved.stat()
    if (not resolved.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077):
        raise SupervisorError(f"{label} must be an existing user-owned private directory")
    return resolved


def _overlap(left, right):
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _ensure_fresh_output_root(root):
    if any(root.iterdir()):
        raise SupervisorError("one-shot output root already contains a supervisor artifact")


def _validate_snapshot(snapshot, caps, request, prior, clock, identity):
    if not isinstance(snapshot, TelemetrySnapshot):
        raise SupervisorError("observer returned no typed cumulative telemetry snapshot")
    try:
        capture._validate_costs(snapshot.costs)
        capture._validate_stop_state(snapshot.stop_state)
    except capture.CaptureAdmissionError as exc:
        raise SupervisorError(f"observer supplied unknown or invalid telemetry: {exc}") from exc
    now = _parse_time(_utc(clock))
    for observed_at, label in ((snapshot.costs.observed_at, "cost"),
                               (snapshot.stop_state.observed_at, "stop state")):
        observed = _parse_time(observed_at)
        age = (now - observed).total_seconds()
        if age < 0 or age > request.observation_max_age_seconds:
            raise SupervisorError(f"{label} observation is stale or from the future")
    if prior is not None:
        for field in _COST_FIELDS:
            old = prior.costs.values[field]
            new = snapshot.costs.values[field]
            if field in {"rss_bytes", "disk_bytes"}:
                regressed = new < old
            else:
                regressed = new < old
            if regressed:
                raise SupervisorError(f"cumulative {field} observation regressed")
        if _parse_time(snapshot.costs.observed_at) < _parse_time(prior.costs.observed_at):
            raise SupervisorError("cost observation timestamp moved backward")
        if _parse_time(snapshot.stop_state.observed_at) < _parse_time(prior.stop_state.observed_at):
            raise SupervisorError("stop-state observation timestamp moved backward")
    if identity is not None:
        minimum_wall = float(prior.costs.values["wall_seconds"]) if prior is not None else 0.0
        if snapshot.costs.values["wall_seconds"] < minimum_wall:
            raise SupervisorError("cumulative wall-time measurement regressed")


def _stop_reason(snapshot, caps, elapsed_seconds=0.0):
    state = snapshot.stop_state
    if state.incident_open:
        return "authority/privacy incident is open"
    if state.unrecoverable_run:
        return "observer reports an unrecoverable run"
    if state.consecutive_infrastructure_failures >= 2:
        return "two consecutive infrastructure failures"
    for name, cap in caps.as_dict().items():
        observed = snapshot.costs.values[name]
        if name == "wall_seconds":
            observed += elapsed_seconds
        if observed >= cap:
            return f"registered {name} cap reached"
    return None


def _not_launched(status, reason, clock, snapshot=None):
    return ProcessOutcome(status, False, None, None, None, _utc(clock), 0.0, 0, 0, 0, 0,
                          None, None, None, None, None, None, snapshot, _LIMITS,
                          reason, "not-started", (snapshot,) if snapshot is not None else ())


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass
    except PermissionError:
        pass


def _group_state(pgid, previous):
    if previous.startswith("unknown"):
        return previous
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "clean"
    except PermissionError:
        return "unknown: process group could not be inspected"
    return "unknown: process group still exists after stop"


def _cleanup_stopped_group(pgid, request, previous):
    state = _group_state(pgid, previous)
    if state == "clean":
        return state
    _signal_group(pgid, signal.SIGTERM)
    time.sleep(request.term_grace_seconds)
    _signal_group(pgid, signal.SIGKILL)
    time.sleep(request.kill_grace_seconds)
    return _group_state(pgid, state)


def _clean_or_stop_descendants(pgid, request):
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "clean"
    except PermissionError:
        return "unknown: process group could not be inspected after root exit"
    _signal_group(pgid, signal.SIGTERM)
    time.sleep(request.term_grace_seconds)
    _signal_group(pgid, signal.SIGKILL)
    time.sleep(request.kill_grace_seconds)
    state = _group_state(pgid, "pending")
    # A root process that exits while descendants remain has not completed a
    # clean one-shot run, even when our cleanup signals later remove them.
    # Preserve that fact instead of upgrading the outcome to success.
    return "descendants-terminated" if state == "clean" else state


def _close_selector_streams(selector, streams):
    for stream, _write_fd, _digest, _name in list(streams.values()):
        _unregister_close(selector, stream)
    streams.clear()


def _close_all_selector_streams(selector):
    for key in list(selector.get_map().values()):
        _unregister_close(selector, key.fileobj)


def _write_all(fd, raw):
    offset = 0
    while offset < len(raw):
        count = os.write(fd, raw[offset:])
        if count <= 0:
            raise OSError("private output write made no progress")
        offset += count


def _unregister_close(selector, stream):
    if stream is None:
        return
    try:
        selector.unregister(stream)
    except (KeyError, ValueError):
        pass
    try:
        stream.close()
    except OSError:
        pass


def _open_exclusive(path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return os.open(path, flags, 0o600)


def _write_exclusive(path, raw):
    fd = _open_exclusive(path)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(Path(path).parent)
    except BaseException:
        try:
            Path(path).unlink()
        except OSError:
            pass
        raise


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _snapshot_dict(snapshot):
    if snapshot is None:
        return None
    costs = snapshot.costs
    stop = snapshot.stop_state
    return {
        "costs": {"values": dict(costs.values), "sourceRefSha256": _sha(costs.source_ref.encode("utf-8")),
                  "sourceSha256": costs.source_sha256, "observedAt": costs.observed_at},
        "stopState": {"incidentOpen": stop.incident_open,
                      "unrecoverableRun": stop.unrecoverable_run,
                      "consecutiveInfrastructureFailures": stop.consecutive_infrastructure_failures,
                      "sourceRefSha256": _sha(stop.source_ref.encode("utf-8")),
                      "sourceSha256": stop.source_sha256,
                      "observedAt": stop.observed_at},
    }


def _hash_executable(path):
    digest = hashlib.sha256()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            raise SupervisorError("pinned executable is not a regular executable file")
        while True:
            chunk = os.read(fd, READ_CHUNK_BYTES)
            if not chunk:
                break
            digest.update(chunk)
        after = os.fstat(fd)
        if _stat_identity(before) != _stat_identity(after):
            raise SupervisorError("pinned executable changed while hashing")
    finally:
        os.close(fd)
    return digest.hexdigest()


def _stat_identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_mode)


def _parse_time(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SupervisorError("observer timestamp must be timezone-aware ISO-8601") from exc
    if result.tzinfo is None:
        raise SupervisorError("observer timestamp must be timezone-aware ISO-8601")
    return result.astimezone(timezone.utc)


def _utc(clock):
    value = clock.utc_now()
    _parse_time(value)
    return value


def _safe_reason(exc):
    # Exceptions can contain command arguments or external telemetry; retain only type.
    return f"{type(exc).__name__}: trusted measurement or process control unavailable"


def _json_bytes(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise SupervisorError("receipt is not bounded canonical JSON") from exc


def _sha(value):
    return hashlib.sha256(value).hexdigest()


__all__ = ["BudgetCaps", "Clock", "ProcessIdentity", "ProcessOutcome", "ProcessRequest",
           "SupervisorError", "TelemetrySnapshot", "run_supervised"]
