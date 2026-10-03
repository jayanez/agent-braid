# SPDX-License-Identifier: AGPL-3.0-only
"""M4 owned-child execution variant of the frozen M2 process runner.

The M2 module's bytes are bound by approved historical evidence. Keep it intact;
this separately reviewed variant additionally inherits the coordinator lock FD.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from .git_process import (
    GitCommandBudget, GitCommandFailure, GitCommandResult, GitExecutionCancelled,
    GitExecutionTimeout, GitInfrastructureFailure, GitOutputLimitExceeded,
    GitProcessStartFailure, GitResourceLimitUnavailable, GitScratchLimitExceeded,
    _kill,
)

def run_owned_git(
    cwd: Path,
    args: tuple[str, ...],
    *,
    env: dict[str, str],
    budget: GitCommandBudget,
    input_bytes: bytes | None = None,
    allow_failure: bool = False,
    command_timeout: float = 30.0,
    poll_interval: float = 0.01,
    ownership_fd: int | None = None,
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
            pass_fds=(ownership_fd,) if ownership_fd is not None else (),
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
