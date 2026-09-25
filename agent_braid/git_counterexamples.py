# SPDX-License-Identifier: AGPL-3.0-only
"""Private bounded reducer over verified divergent Git replay evidence.

Consumes the existing ``git_replay`` evidence and verifier only. It never
modifies the replay engine, executes project code, promotes a ref, or
authorizes execution. A supervisor runs the search in a private worker
process group under one monotonic 120-second deadline; timeout, tampering,
missing Git objects, incomplete search, or infrastructure failure always
produce an explicit ``rejected``, ``unverified``, or ``inconclusive`` status,
never a minimality claim. See specs/015-m2-counterexample-reducer/spec.md.
"""

from __future__ import annotations

import ctypes
import itertools
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from . import git_process
from . import git_replay


REDUCER_VERSION = "0.1.0-alpha"
MIN_SUBSET_SIZE = 2
MAX_SUBSET_SIZE = 4
MAX_CANDIDATE_ATTEMPTS = 10
DEADLINE_SECONDS = 120.0
SUPERVISOR_GRACE_SECONDS = 5.0
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024
_SYSTEM_POPEN = subprocess.Popen

POSITIVE_STATUSES = frozenset({"reduced", "unchanged"})

REDUCTION_LIMITS = [
    "Minimality is only over enumerated 2-4 operation subsets in the fixed-patch, "
    "tracked-tree-v1 domain; it does not minimize patch hunks or infer hidden effects.",
    "A single monotonic 120-second deadline covers input verification and all "
    "candidate subset attempts, enforced by terminating a private worker process group.",
    "At most ten dependency-closed candidate subsets are independently replayed and "
    "verified; dependency-incomplete subsets are discarded before replay and do not count.",
    "Each candidate subset replay keeps its own existing per-call Git budgets; this "
    "reducer does not claim a shared aggregate Git-command, output, or scratch quota.",
    "No workload code or tests are invoked, no ref is promoted, and no "
    "execution is authorized. The worker receives no inherited credentials "
    "and issues no network commands.",
]


def _base_result(evidence: object) -> dict:
    digest = None
    ids: list[str] = []
    if isinstance(evidence, dict):
        raw_digest = evidence.get("evidenceDigest")
        if isinstance(raw_digest, str):
            digest = raw_digest
        operations = evidence.get("operations")
        if isinstance(operations, list):
            ids = sorted(
                operation["instanceId"]
                for operation in operations
                if isinstance(operation, dict) and isinstance(operation.get("instanceId"), str)
            )
    return {"originalEvidenceDigest": digest, "originalOperationIds": ids}


def _finalize(
    base: dict,
    status: str,
    reason: str,
    elapsed_seconds: float,
    deadline_seconds: float,
    max_attempts: int,
    *,
    selected: list[str] | None = None,
    witness_digest: str | None = None,
    witness: dict | None = None,
    attempts: list[dict] | None = None,
    attempt_count: int = 0,
    skipped: int = 0,
) -> dict:
    positive = status in POSITIVE_STATUSES
    return {
        "reducerVersion": REDUCER_VERSION,
        "status": status,
        "reason": reason,
        "originalEvidenceDigest": base["originalEvidenceDigest"],
        "originalOperationIds": base["originalOperationIds"],
        "selectedOperationIds": selected if positive else None,
        "witnessEvidenceDigest": witness_digest if positive else None,
        "witnessEvidence": witness if positive else None,
        "attempts": attempts or [],
        "attemptCount": attempt_count,
        "skippedDependencyIncompleteSubsets": skipped,
        "elapsedSeconds": round(elapsed_seconds, 6),
        "deadlineSeconds": deadline_seconds,
        "maxCandidateAttempts": max_attempts,
        "executionAuthorization": False,
        "limits": REDUCTION_LIMITS,
    }


def _subset_request(evidence: dict, repository: str, combo: tuple[str, ...]) -> dict:
    by_id = {operation["instanceId"]: operation for operation in evidence["operations"]}
    return {
        "gitAnalysisRequestVersion": "0.1.0-alpha",
        "repository": repository,
        "baseRevision": evidence["baseCommit"],
        "operations": [
            {
                "instanceId": identifier,
                "attemptId": by_id[identifier]["attemptId"],
                "source": {"kind": "commit", "revision": by_id[identifier]["sourceCommit"]},
                "dependencies": sorted(by_id[identifier]["dependencies"]),
                "uncertainPaths": sorted(by_id[identifier]["uncertainPaths"]),
            }
            for identifier in combo
        ],
    }


def _run_worker(
    payload: object,
    *,
    deadline_seconds: float = DEADLINE_SECONDS,
    max_attempts: int = MAX_CANDIDATE_ATTEMPTS,
) -> dict:
    """Verify input evidence, then bound-search for a smaller divergent witness."""
    start = time.monotonic()

    def elapsed() -> float:
        return time.monotonic() - start

    def remaining() -> float:
        return deadline_seconds - elapsed()

    evidence = payload.get("evidence") if isinstance(payload, dict) else None
    repository = payload.get("repository") if isinstance(payload, dict) else None
    base = _base_result(evidence)

    if not isinstance(repository, str) or not repository.strip():
        return _finalize(base, "rejected", "invalid repository path",
                          elapsed(), deadline_seconds, max_attempts)

    try:
        verification = git_replay.verify(evidence, repository)
    except Exception as exc:  # defensive: verify() already handles its own exceptions
        return _finalize(base, "inconclusive",
                          f"input verification failed unexpectedly ({type(exc).__name__}: {exc})",
                          elapsed(), deadline_seconds, max_attempts)

    status = verification.get("status")
    if status == "rejected":
        return _finalize(base, "rejected",
                          "verification rejected the input evidence: "
                          + str(verification.get("reason", "unknown")),
                          elapsed(), deadline_seconds, max_attempts)
    if status != "verified":
        return _finalize(base, "unverified",
                          "input evidence did not verify: " + str(verification.get("reason", "unknown")),
                          elapsed(), deadline_seconds, max_attempts)

    if evidence.get("result") != "divergent":
        return _finalize(base, "rejected",
                          "verified evidence is not eligible as a positive counterexample source "
                          f"(result={evidence.get('result')!r})",
                          elapsed(), deadline_seconds, max_attempts)

    operations = evidence["operations"]
    by_id = {operation["instanceId"]: operation for operation in operations}
    ids = sorted(by_id)
    operation_count = len(ids)

    if operation_count <= MIN_SUBSET_SIZE:
        return _finalize(base, "unchanged",
                          "the original operation count is already at the minimum subset size (2)",
                          elapsed(), deadline_seconds, max_attempts,
                          selected=ids, witness_digest=evidence["evidenceDigest"], witness=evidence)

    attempts: list[dict] = []
    attempt_count = 0
    skipped = 0
    exhausted = False

    for size in range(MIN_SUBSET_SIZE, operation_count):
        if exhausted:
            break
        for combo in itertools.combinations(ids, size):
            subset = set(combo)
            if not all(set(by_id[identifier]["dependencies"]) <= subset for identifier in combo):
                skipped += 1
                continue
            if attempt_count >= max_attempts or remaining() <= 0:
                exhausted = True
                break

            attempt_count += 1
            request = _subset_request(evidence, repository, combo)
            try:
                candidate_bundle, _candidate_plan = git_replay.produce(request)
                outcome = candidate_bundle["result"]
                candidate_verification = git_replay.verify(candidate_bundle, repository)
                verification_status = candidate_verification.get("status")
                attempts.append({
                    "operationIds": list(combo), "size": size, "outcome": outcome,
                    "verificationStatus": verification_status,
                    "reason": None if verification_status == "verified"
                    else str(candidate_verification.get("reason", "candidate did not verify")),
                })
                if verification_status != "verified":
                    return _finalize(
                        base, "inconclusive",
                        "candidate subset could not be independently verified; "
                        "no minimality claim is available",
                        elapsed(), deadline_seconds, max_attempts,
                        attempts=attempts, attempt_count=attempt_count, skipped=skipped,
                    )
                if outcome == "inconclusive":
                    return _finalize(
                        base, "inconclusive",
                        "a verified candidate subset has incomplete replay schedules; "
                        "no minimality claim is available",
                        elapsed(), deadline_seconds, max_attempts,
                        attempts=attempts, attempt_count=attempt_count, skipped=skipped,
                    )
                if outcome != "divergent" and outcome != "equivalent-observed":
                    return _finalize(
                        base, "inconclusive",
                        "candidate subset has an unsupported replay result",
                        elapsed(), deadline_seconds, max_attempts,
                        attempts=attempts, attempt_count=attempt_count, skipped=skipped,
                    )
                if outcome == "divergent":
                    return _finalize(
                        base, "reduced",
                        f"a smaller {size}-operation divergent subset was independently verified",
                        elapsed(), deadline_seconds, max_attempts,
                        selected=list(combo), witness_digest=candidate_bundle["evidenceDigest"],
                        witness=candidate_bundle, attempts=attempts,
                        attempt_count=attempt_count, skipped=skipped,
                    )
            except git_replay.InvalidGitReplay as exc:
                attempts.append({
                    "operationIds": list(combo), "size": size, "outcome": "rejected",
                    "verificationStatus": "rejected", "reason": str(exc),
                })
            except git_process.GitInfrastructureFailure as exc:
                attempts.append({
                    "operationIds": list(combo), "size": size, "outcome": "infrastructure-failure",
                    "verificationStatus": "unverified", "reason": str(exc),
                })
            except Exception as exc:  # never let one candidate crash the whole search
                attempts.append({
                    "operationIds": list(combo), "size": size, "outcome": "unexpected-error",
                    "verificationStatus": "rejected", "reason": f"{type(exc).__name__}: {exc}",
                })
            if attempts[-1]["verificationStatus"] != "verified":
                return _finalize(
                    base, "inconclusive",
                    "candidate subset replay failed; no minimality claim is available",
                    elapsed(), deadline_seconds, max_attempts,
                    attempts=attempts, attempt_count=attempt_count, skipped=skipped,
                )
        if remaining() <= 0:
            exhausted = True

    if exhausted:
        return _finalize(
            base, "inconclusive",
            "the 120-second reduction deadline or ten-candidate-subset budget was exhausted "
            "before the search completed; no minimality claim is available",
            elapsed(), deadline_seconds, max_attempts,
            attempts=attempts, attempt_count=attempt_count, skipped=skipped,
        )

    return _finalize(
        base, "unchanged",
        "no smaller dependency-closed divergent subset exists in the enumerated "
        f"2–{operation_count - 1} operation domain",
        elapsed(), deadline_seconds, max_attempts,
        selected=ids, witness_digest=evidence["evidenceDigest"], witness=evidence,
        attempts=attempts, attempt_count=attempt_count, skipped=skipped,
    )


def _process_identity(pid: int) -> str | None:
    """Bind a PID to its OS-reported birth, not just its reusable number."""
    proc_stat = Path(f"/proc/{pid}/stat")
    if Path("/proc").is_dir():
        try:
            # The second field is parenthesized and may contain spaces or ')'.
            fields = proc_stat.read_text().rsplit(") ", 1)[1].split()
            return f"linux:{fields[19]}"  # starttime, field 22
        except (OSError, IndexError):
            return None
    if sys.platform != "darwin":
        return None

    class BSDInfo(ctypes.Structure):
        _fields_ = [
            ("flags", ctypes.c_uint32), ("status", ctypes.c_uint32),
            ("xstatus", ctypes.c_uint32), ("pid", ctypes.c_uint32),
            ("ppid", ctypes.c_uint32),
            *[(name, ctypes.c_uint32) for name in
              ("uid", "gid", "ruid", "rgid", "svuid", "svgid", "reserved")],
            ("comm", ctypes.c_char * 16), ("name", ctypes.c_char * 32),
            *[(name, ctypes.c_uint32) for name in
              ("nfiles", "pgid", "pjobc", "tdev", "tpgid")],
            ("nice", ctypes.c_int32),
            ("start_sec", ctypes.c_uint64), ("start_usec", ctypes.c_uint64),
        ]

    try:
        function = ctypes.CDLL("libproc.dylib").proc_pidinfo
        function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64,
                             ctypes.c_void_p, ctypes.c_int]
        function.restype = ctypes.c_int
        info = BSDInfo()
        returned = function(pid, 3, 0, ctypes.byref(info), ctypes.sizeof(info))
        if returned != ctypes.sizeof(info) or info.pid != pid:
            return None
        return f"darwin:{info.start_sec}:{info.start_usec}"
    except (OSError, AttributeError):
        return None


def _registered_child_groups(registry_path: Path | None) -> set[int]:
    """Resolve child sessions even after their worker has exited."""
    if registry_path is None:
        return set()
    try:
        lines = registry_path.read_text().splitlines()
    except OSError:
        return set()
    groups = set()
    for line in lines:
        try:
            pid_text, identity = line.split(" ", 1)
            pid = int(pid_text)
            if _process_identity(pid) != identity:
                continue
            group = os.getpgid(pid)
        except (OSError, ValueError):
            continue
        # Git children create new sessions, so their PGID must equal their PID.
        # A reused PID in an unrelated group must not be targeted.
        if group == pid and group != os.getpgrp():
            groups.add(group)
    return groups


def _terminate_process_group(
    process: "subprocess.Popen[bytes]", registry_path: Path | None = None,
) -> None:
    child_groups: set[int] = set()
    if os.name == "posix" and process.poll() is None:
        try:
            # Freeze the Python worker before listing its descendants. Existing
            # Git commands create their own sessions in git_process.run_git.
            os.killpg(process.pid, signal.SIGSTOP)
            child_groups = _descendant_process_groups(process.pid)
        except (ProcessLookupError, OSError):
            pass
    child_groups.update(_registered_child_groups(registry_path))
    child_groups.discard(process.pid)
    for group in sorted(child_groups):
        try:
            os.killpg(group, signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass
    try:
        if os.name == "posix":
            # The worker may have exited while a descendant still holds a pipe.
            # Its process group must be killed even after the leader exits.
            os.killpg(process.pid, signal.SIGKILL)
        elif process.poll() is None:
            process.kill()
    except (ProcessLookupError, OSError):
        pass


def _descendant_process_groups(root_pid: int) -> set[int]:
    """Find Git child sessions of a frozen worker using local process metadata."""
    parent_by_pid: dict[int, int] = {}
    proc_root = Path("/proc")
    if proc_root.is_dir():
        for entry in proc_root.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                lines = (entry / "status").read_text().splitlines()
                parent = next(int(line.split()[1]) for line in lines
                              if line.startswith("PPid:"))
                parent_by_pid[int(entry.name)] = parent
            except (OSError, StopIteration, ValueError, IndexError):
                continue
    else:
        try:
            table = subprocess.run(
                ["/bin/ps", "-axo", "pid=,ppid="],
                check=True, capture_output=True, timeout=2,
                env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"},
            ).stdout.decode("ascii", "strict")
            for line in table.splitlines():
                pid, parent = (int(value) for value in line.split())
                parent_by_pid[pid] = parent
        except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
            return set()
    descendants: set[int] = set()
    frontier = {root_pid}
    while frontier:
        children = {pid for pid, parent in parent_by_pid.items() if parent in frontier}
        children -= descendants
        if not children:
            break
        descendants.update(children)
        frontier = children
    groups = set()
    for pid in descendants:
        try:
            group = os.getpgid(pid)
        except OSError:
            continue
        if group not in {root_pid, os.getpgrp()}:
            groups.add(group)
    return groups


def _run_supervised(command: list[str], payload_bytes: bytes, deadline_seconds: float) -> dict:
    """Run ``command`` as a private process group and kill it on timeout."""
    worker_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.devnull,
        "LC_ALL": "C",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    with tempfile.TemporaryDirectory(prefix="agent-braid-reducer-worker-") as directory:
        registry_path = Path(directory) / "child-pids"
        registry_path.touch(mode=0o600)
        worker_env["AGENT_BRAID_REDUCER_CHILD_REGISTRY"] = str(registry_path)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                start_new_session=(os.name == "posix"),
                env=worker_env,
            )
        except OSError as exc:
            return {"started": False, "timed_out": False, "returncode": None,
                    "stdout": b"", "stderr": str(exc).encode("utf-8"), "elapsedSeconds": 0.0}
        return _communicate_supervised(process, payload_bytes, deadline_seconds, registry_path)


def _communicate_supervised(
    process: "subprocess.Popen[bytes]", payload_bytes: bytes,
    deadline_seconds: float, registry_path: Path,
) -> dict:
    started = time.monotonic()
    try:
        stdout, stderr = process.communicate(input=payload_bytes, timeout=deadline_seconds)
        timed_out = False
    except subprocess.TimeoutExpired:
        _terminate_process_group(process, registry_path)
        try:
            stdout, stderr = process.communicate(timeout=SUPERVISOR_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            _terminate_process_group(process, registry_path)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            try:
                process.wait(timeout=SUPERVISOR_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                _terminate_process_group(process, registry_path)
            stdout, stderr = b"", b"worker descendants retained output pipes after termination"
        timed_out = True
    elapsed = time.monotonic() - started
    return {"started": True, "timed_out": timed_out, "returncode": process.returncode,
            "stdout": stdout, "stderr": stderr, "elapsedSeconds": elapsed}


def reduce_counterexample(bundle: object, repository: object) -> dict:
    """Reduce verified divergent Git replay evidence under one supervised deadline."""
    base = _base_result(bundle)
    if not isinstance(repository, str) or not repository.strip():
        return _finalize(base, "rejected", "invalid repository path",
                          0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    if os.name != "posix":
        return _finalize(base, "inconclusive", "process-group supervision is unavailable",
                          0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    try:
        payload_bytes = json.dumps({"evidence": bundle, "repository": repository}).encode("utf-8")
    except (TypeError, ValueError) as exc:
        return _finalize(base, "rejected", f"evidence is not JSON-serializable ({exc})",
                          0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    if len(payload_bytes) > MAX_PAYLOAD_BYTES:
        return _finalize(base, "rejected", "reduction input exceeds 8 MiB",
                          0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)

    command = [sys.executable, "-m", "agent_braid.git_counterexamples", "--worker"]
    outcome = _run_supervised(command, payload_bytes, DEADLINE_SECONDS)

    if not outcome["started"]:
        return _finalize(base, "inconclusive",
                          "reduction worker process could not start: "
                          + outcome["stderr"].decode("utf-8", "replace"),
                          0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    if outcome["timed_out"]:
        return _finalize(base, "inconclusive",
                          f"the {DEADLINE_SECONDS:g}-second reduction deadline was exceeded; "
                          "the private worker process group was terminated and awaited",
                          outcome["elapsedSeconds"], DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    if outcome["returncode"] != 0:
        return _finalize(base, "inconclusive",
                          f"reduction worker exited with status {outcome['returncode']}: "
                          + outcome["stderr"].decode("utf-8", "replace")[-2000:],
                          outcome["elapsedSeconds"], DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    try:
        result = json.loads(outcome["stdout"].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return _finalize(base, "inconclusive", f"reduction worker produced invalid output ({exc})",
                          outcome["elapsedSeconds"], DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    if not isinstance(result, dict) or result.get("reducerVersion") != REDUCER_VERSION:
        return _finalize(base, "inconclusive", "reduction worker output failed shape validation",
                          outcome["elapsedSeconds"], DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    return result


def _register_worker_children() -> None:
    """Record every child PID before replay can await it or exit unexpectedly."""
    registry = os.environ.get("AGENT_BRAID_REDUCER_CHILD_REGISTRY")
    if not registry:
        raise OSError("reduction worker has no child-process registry")
    original_popen = _SYSTEM_POPEN

    def registered_popen(*args, **kwargs):
        child = original_popen(*args, **kwargs)
        try:
            identity = _process_identity(child.pid)
            if identity is None:
                if child.poll() is None:
                    raise OSError("cannot identify a running Git child")
                return child
            with open(registry, "a", encoding="ascii") as stream:
                stream.write(f"{child.pid} {identity}\n")
                stream.flush()
        except OSError:
            try:
                if os.name == "posix" and kwargs.get("start_new_session"):
                    os.killpg(child.pid, signal.SIGKILL)
                else:
                    child.kill()
            except (ProcessLookupError, OSError):
                pass
            child.wait()
            raise
        return child

    subprocess.Popen = registered_popen


def _main_worker() -> int:
    try:
        _register_worker_children()
    except OSError as exc:
        result = _finalize(_base_result(None), "inconclusive",
                           f"worker cannot register Git children ({exc})",
                           0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
        sys.stdout.write(json.dumps(result))
        return 0
    try:
        raw = sys.stdin.buffer.read()
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = _finalize(_base_result(None), "inconclusive",
                            f"worker could not parse its input ({exc})",
                            0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
        sys.stdout.write(json.dumps(result))
        return 0
    try:
        result = _run_worker(payload)
    except Exception as exc:  # the worker must always emit an explicit result, never crash silently
        evidence = payload.get("evidence") if isinstance(payload, dict) else None
        result = _finalize(_base_result(evidence), "inconclusive",
                            f"reduction worker failed unexpectedly ({type(exc).__name__}: {exc})",
                            0.0, DEADLINE_SECONDS, MAX_CANDIDATE_ATTEMPTS)
    sys.stdout.write(json.dumps(result))
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        raise SystemExit(_main_worker())
    raise SystemExit("usage: python -m agent_braid.git_counterexamples --worker")
