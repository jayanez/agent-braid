# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded subprocess support shared by replay and Git provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

try:
    import resource
except ImportError:  # Windows; bounded prototype rejects this platform.
    resource = None


class GitInfrastructureFailure(RuntimeError):
    """A replay stopped because its bounded Git execution environment failed."""

    category = "git-infrastructure-failure"


class GitExecutionTimeout(GitInfrastructureFailure):
    category = "timeout"


class GitOutputLimitExceeded(GitInfrastructureFailure):
    category = "output-limit"


class GitScratchLimitExceeded(GitInfrastructureFailure):
    category = "scratch-limit"


class GitCommandLimitExceeded(GitInfrastructureFailure):
    category = "command-limit"


class GitProcessStartFailure(GitInfrastructureFailure):
    category = "process-start-failure"


class GitResourceLimitUnavailable(GitInfrastructureFailure):
    category = "resource-limit-unavailable"


class GitExecutionCancelled(GitInfrastructureFailure):
    category = "cancelled"


class GitCommandFailure(RuntimeError):
    """A started Git command returned a non-zero exit status."""


@dataclass
class GitCommandBudget:
    """Wall-clock, command-count, captured-output and sampled scratch budgets."""

    temp_root: Path
    wall_seconds: float = 120.0
    max_commands: int = 512
    max_output_bytes: int = 16 * 1024 * 1024
    max_command_output_bytes: int = 8 * 1024 * 1024
    max_scratch_bytes: int = 64 * 1024 * 1024
    max_process_address_space_bytes: int | None = None
    cancel_event: threading.Event | None = None
    started_at: float = field(default_factory=time.monotonic)
    commands: int = 0
    output_bytes: int = 0
    child_user_cpu_seconds: float = 0.0
    child_system_cpu_seconds: float = 0.0
    peak_child_rss_bytes: int = 0
    peak_scratch_bytes: int = 0
    _last_child_user_cpu: float = field(default=0.0, repr=False)
    _last_child_system_cpu: float = field(default=0.0, repr=False)
    lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.max_process_address_space_bytes is not None:
            if (resource is None or os.name != "posix"
                    or not hasattr(resource, "RLIMIT_AS")):
                raise GitResourceLimitUnavailable(
                    "hard Git child address-space limits are unavailable on this platform"
                )
        self._initialize_child_usage()

    def _initialize_child_usage(self) -> None:
        if resource is None or not hasattr(resource, "RUSAGE_CHILDREN"):
            return
        usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        self._last_child_user_cpu = usage.ru_utime
        self._last_child_system_cpu = usage.ru_stime
        rss = int(usage.ru_maxrss)
        if sys.platform != "darwin":
            rss *= 1024
        self.peak_child_rss_bytes = rss

    def _sample_child_usage(self) -> None:
        if resource is None or not hasattr(resource, "RUSAGE_CHILDREN"):
            return
        with self.lock:
            usage = resource.getrusage(resource.RUSAGE_CHILDREN)
            self.child_user_cpu_seconds += max(0.0, usage.ru_utime - self._last_child_user_cpu)
            self.child_system_cpu_seconds += max(0.0, usage.ru_stime - self._last_child_system_cpu)
            self._last_child_user_cpu = usage.ru_utime
            self._last_child_system_cpu = usage.ru_stime
            rss = int(usage.ru_maxrss)
            if sys.platform != "darwin":
                rss *= 1024
            self.peak_child_rss_bytes = max(self.peak_child_rss_bytes, rss)

    def begin_command(self, command_timeout: float) -> float:
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise GitExecutionCancelled("Git execution was cancelled")
        with self.lock:
            self.commands += 1
            if self.commands > self.max_commands:
                raise GitCommandLimitExceeded(
                    f"Git command budget exceeded ({self.max_commands})"
                )
        remaining = self.wall_seconds - (time.monotonic() - self.started_at)
        if remaining <= 0:
            raise GitExecutionTimeout(
                f"end-to-end Git budget exceeded ({self.wall_seconds:g} seconds)"
            )
        if self.scratch_exceeds_limit():
            raise GitScratchLimitExceeded(
                f"temporary Git data exceeded {self.max_scratch_bytes} bytes"
            )
        return min(command_timeout, remaining)

    def record_output(self, byte_count: int) -> bool:
        with self.lock:
            if self.output_bytes + byte_count > self.max_output_bytes:
                return False
            self.output_bytes += byte_count
            return True

    def scratch_exceeds_limit(self) -> bool:
        total = 0
        try:
            for directory, _, filenames in os.walk(self.temp_root):
                for filename in filenames:
                    try:
                        total += (Path(directory) / filename).stat().st_size
                    except FileNotFoundError:
                        continue
        except OSError:
            # An unreadable scratch tree is not evidence that it is within budget.
            return True
        with self.lock:
            self.peak_scratch_bytes = max(self.peak_scratch_bytes, total)
        return total > self.max_scratch_bytes


@dataclass(frozen=True)
class GitCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int


def _kill(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, OSError):
        pass


def run_git(
    cwd: Path,
    args: tuple[str, ...],
    *,
    env: dict[str, str],
    budget: GitCommandBudget,
    input_bytes: bytes | None = None,
    allow_failure: bool = False,
    command_timeout: float = 30.0,
    poll_interval: float = 0.01,
) -> GitCommandResult:
    """Run Git with bounded streamed output and shared end-to-end limits."""
    timeout = budget.begin_command(command_timeout)
    command = ["git", "-C", str(cwd), *args]
    if budget.max_process_address_space_bytes is not None:
        command = [
            sys.executable,
            str(Path(__file__).with_name("git_exec.py")),
            str(budget.max_process_address_space_bytes),
            *command,
        ]
    try:
        process = subprocess.Popen(
            command,
            cwd=None,
            env=env,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=(os.name == "posix"),
        )
    except OSError as exc:
        raise GitProcessStartFailure(
            f"Git could not start ({type(exc).__name__})"
        ) from exc

    outputs = {"stdout": bytearray(), "stderr": bytearray()}
    output_lock = threading.Lock()
    overflow: list[bool] = []

    def drain(name: str, stream) -> None:
        while True:
            chunk = stream.read(64 * 1024)
            if not chunk:
                return
            should_kill = False
            with output_lock:
                combined = len(outputs["stdout"]) + len(outputs["stderr"])
                if (combined + len(chunk) > budget.max_command_output_bytes
                        or not budget.record_output(len(chunk))):
                    if not overflow:
                        overflow.append(True)
                    should_kill = True
                elif not overflow:
                    outputs[name].extend(chunk)
            if should_kill:
                _kill(process)

    readers = [
        threading.Thread(target=drain, args=("stdout", process.stdout), daemon=True),
        threading.Thread(target=drain, args=("stderr", process.stderr), daemon=True),
    ]
    for thread in readers:
        thread.start()

    def write_input() -> None:
        if process.stdin is None:
            return
        try:
            if input_bytes:
                process.stdin.write(input_bytes)
                process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    writer = None
    if input_bytes is not None:
        writer = threading.Thread(target=write_input, daemon=True)
        writer.start()

    failure: GitInfrastructureFailure | None = None
    deadline = time.monotonic() + timeout
    next_scratch_check = time.monotonic() + 0.05
    while process.poll() is None:
        if budget.cancel_event is not None and budget.cancel_event.is_set():
            failure = GitExecutionCancelled("Git execution was cancelled")
            _kill(process)
            break
        if time.monotonic() >= deadline:
            failure = GitExecutionTimeout(
                f"Git command exceeded its {timeout:g}-second/end-to-end limit"
            )
            _kill(process)
            break
        if time.monotonic() >= next_scratch_check:
            if budget.scratch_exceeds_limit():
                failure = GitScratchLimitExceeded(
                    f"temporary Git data exceeded {budget.max_scratch_bytes} bytes"
                )
                _kill(process)
                break
            next_scratch_check = time.monotonic() + 0.05
        if overflow:
            break
        time.sleep(poll_interval)

    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        _kill(process)
        process.wait()
    for thread in readers:
        thread.join(timeout=1.0)
    for stream in (process.stdout, process.stderr):
        try:
            stream.close()
        except OSError:
            pass
    if writer is not None:
        writer.join(timeout=1.0)
    budget._sample_child_usage()

    if failure is None and budget.cancel_event is not None and budget.cancel_event.is_set():
        failure = GitExecutionCancelled("Git execution was cancelled")
    if failure is not None:
        raise failure
    if overflow:
        raise GitOutputLimitExceeded(
            "Git stdout/stderr exceeded the bounded output budget"
        )
    if budget.scratch_exceeds_limit():
        raise GitScratchLimitExceeded(
            f"temporary Git data exceeded {budget.max_scratch_bytes} bytes"
        )
    result = GitCommandResult(bytes(outputs["stdout"]), bytes(outputs["stderr"]),
                              process.returncode)
    if result.stderr.startswith(b"agent-braid-git-limit-setup-failed:"):
        raise GitResourceLimitUnavailable(
            "Git child resource limit could not be enforced"
        )
    if result.returncode and not allow_failure:
        raise GitCommandFailure(args[0] if args else "unknown Git command")
    return result
