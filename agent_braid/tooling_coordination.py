# SPDX-License-Identifier: AGPL-3.0-only
"""Private, durable M4.5 task claims; never grants capture or execution authority.

This is a local coordinator register, not a scheduler. It records explicit caller
actions, serializes competing writers, and retains ambiguous native starts. The
capture/session verifiers remain responsible for authentication, admission,
process termination, and the truth of evidence referenced here.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat
import tempfile
from typing import Any, Iterator, Sequence


SCHEMA = "agent-braid-m45-coordination-v1"
MAX_REGISTRY_BYTES = 1024 * 1024
M45_PENDING_TASK_IDS = frozenset(
    [f"SPEC-041/T{number:03}" for number in range(1, 11)]
    + [f"SPEC-043/T{number:03}" for number in (1, 3, 8, 9, 10)]
    + [f"SPEC-044/T{number:03}" for number in (1, 2, 4, 5, 6, 7, 8, 9, 10)]
    + [f"SPEC-044/OP{number:03}" for number in range(1, 7)]
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_CANDIDATE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
_OWNER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_TOKEN = re.compile(r"^[0-9a-f]{32}$")
_ACTIVE = frozenset(("claimed", "started", "interrupted"))
_STATUSES = _ACTIVE | {"pending", "blocked", "complete", "failed"}


class CoordinationError(ValueError):
    """A task action is stale, duplicate, unsafe, or ambiguous."""


@dataclass(frozen=True)
class EvidenceRef:
    reference: str
    sha256: str


@dataclass(frozen=True)
class TaskSpec:
    task_id: str
    dependencies: tuple[str, ...] = ()
    owner: str = "coordinator"
    native: bool = False


@dataclass(frozen=True)
class TaskClaim:
    task_id: str
    owner: str
    token: str
    candidate_sha256: str
    native: bool


class CoordinationRegistry:
    """Single private register shared by the coordinating local processes.

    ``root`` must be outside publication/evidence export directories. Existing
    private files are never reset. On restart ``inspect`` reveals unresolved
    claims; there is no automatic reclaim, retry, dispatch, or issue closure.
    """

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).absolute()
        self.path = self.root / "registry.json"

    def initialize(self, tasks: Sequence[TaskSpec], *, candidate_sha256: str) -> None:
        _candidate(candidate_sha256)
        records = _task_records(tasks, candidate_sha256)
        with self._lock():
            if self.path.exists() or self.path.is_symlink():
                raise CoordinationError("registry already exists; preserve its history")
            data = {"schemaVersion": SCHEMA, "candidateSha256": candidate_sha256,
                    "revision": 0, "tasks": records, "history": []}
            self._record(data, "initialize", None)
            self._write(data)

    def inspect(self) -> dict[str, Any]:
        """Return a detached validated snapshot; do not repair or dispatch."""
        with self._lock():
            return self._read()

    def sanitized_handoff(self) -> dict[str, Any]:
        """Provide coordination facts without claim tokens or private free text."""
        data = self.inspect()
        return {"schemaVersion": SCHEMA, "candidateSha256": data["candidateSha256"],
                "revision": data["revision"], "registrySha256": data["recordSha256"],
                "tasks": {task_id: {"dependencies": list(task["dependencies"]),
                                    "procedureStatus": task["status"], "native": task["native"],
                                    "blocked": task["blockReason"] is not None,
                                    "evidenceRefCount": len(task["evidenceRefs"])}
                          for task_id, task in data["tasks"].items()},
                "limits": ["Coordination facts only; no capture, grant, human acceptance or issue closure authority."]}

    def claim(self, task_id: str, *, owner: str, candidate_sha256: str) -> TaskClaim:
        with self._lock():
            data, task = self._task(task_id, candidate_sha256)
            if task["owner"] != owner:
                raise CoordinationError("task owner differs from the frozen assignment")
            if task["status"] != "pending":
                raise CoordinationError("task already claimed, started, blocked or terminal; never replay")
            if any(data["tasks"][dep]["status"] != "complete" for dep in task["dependencies"]):
                raise CoordinationError("task dependencies are incomplete")
            if task["native"] and any(item["native"] and item["status"] in _ACTIVE
                                       for item in data["tasks"].values()):
                raise CoordinationError("native executor has an active or interrupted reservation")
            task["status"], task["claimToken"] = "claimed", secrets.token_hex(16)
            self._record(data, "claim", task_id)
            self._write(data)
            return TaskClaim(task_id, owner, task["claimToken"], candidate_sha256, task["native"])

    def start(self, claim: TaskClaim, *, candidate_sha256: str) -> None:
        """Persist the irreversible start before the caller performs work."""
        with self._lock():
            data, task = self._claimed(claim, candidate_sha256)
            if task["status"] != "claimed":
                raise CoordinationError("only an unstarted claim can start; never replay")
            task["status"], task["startedAt"] = "started", _now()
            self._record(data, "start", claim.task_id)
            self._write(data)

    def release(self, claim: TaskClaim, *, candidate_sha256: str, reason: str) -> None:
        """Cancel an explicit pre-start reservation; started work cannot release."""
        _text(reason, "release reason")
        with self._lock():
            data, task = self._claimed(claim, candidate_sha256)
            if task["status"] != "claimed":
                raise CoordinationError("started or interrupted tasks cannot be released")
            task["status"], task["claimToken"] = "pending", None
            self._record(data, "release", claim.task_id, reason)
            self._write(data)

    def interrupt(self, claim: TaskClaim, *, candidate_sha256: str, reason: str) -> None:
        _text(reason, "interruption reason")
        with self._lock():
            data, task = self._claimed(claim, candidate_sha256)
            if task["status"] != "started":
                raise CoordinationError("interruption requires an unresolved durable start")
            task["status"], task["blockReason"] = "interrupted", reason
            self._record(data, "interrupt", claim.task_id, reason)
            self._write(data)

    def finish(self, claim: TaskClaim, *, candidate_sha256: str,
               evidence_refs: Sequence[EvidenceRef], status: str = "complete",
               native_stop_ref: EvidenceRef | None = None) -> None:
        """Explicitly reconcile started work using previously verified receipts.

        A native terminal record additionally requires a referenced stop receipt.
        This register validates references, not their factual truth; the native
        controller must independently verify termination before calling this.
        ``complete`` describes the local procedure, not acceptance or issue closure.
        """
        if status not in ("complete", "failed"):
            raise CoordinationError("terminal task status must be complete or failed")
        refs = _refs(evidence_refs)
        if not refs:
            raise CoordinationError("terminal task requires immutable evidence references")
        stop = None if native_stop_ref is None else _ref(native_stop_ref)
        with self._lock():
            data, task = self._claimed(claim, candidate_sha256)
            if task["status"] not in ("started", "interrupted"):
                raise CoordinationError("terminal reconciliation requires a durable start")
            if task["native"] and stop is None:
                raise CoordinationError("native terminal reconciliation requires a verified stop receipt")
            if not task["native"] and stop is not None:
                raise CoordinationError("offline task cannot claim a native stop receipt")
            task.update(status=status, evidenceRefs=refs, nativeStopRef=stop, blockReason=None)
            self._record(data, "finish", claim.task_id)
            self._write(data)

    def block(self, task_id: str, *, candidate_sha256: str, reason: str) -> None:
        _text(reason, "block reason")
        with self._lock():
            data, task = self._task(task_id, candidate_sha256)
            if task["status"] != "pending":
                raise CoordinationError("only pending tasks can be blocked")
            task["status"], task["blockReason"] = "blocked", reason
            self._record(data, "block", task_id, reason)
            self._write(data)

    def unblock(self, task_id: str, *, candidate_sha256: str, reason: str) -> None:
        _text(reason, "unblock reason")
        with self._lock():
            data, task = self._task(task_id, candidate_sha256)
            if task["status"] != "blocked":
                raise CoordinationError("only explicitly blocked, unstarted tasks can unblock")
            task["status"], task["blockReason"] = "pending", None
            self._record(data, "unblock", task_id, reason)
            self._write(data)

    def _task(self, task_id, candidate_sha256):
        _candidate(candidate_sha256)
        if not isinstance(task_id, str):
            raise CoordinationError("task ID must be a stable string identifier")
        data = self._read()
        if data["candidateSha256"] != candidate_sha256:
            raise CoordinationError("candidate drift; use the exact frozen candidate")
        if task_id not in data["tasks"]:
            raise CoordinationError("task is absent from the frozen registry")
        return data, data["tasks"][task_id]

    def _claimed(self, claim, candidate_sha256):
        if not isinstance(claim, TaskClaim) or type(claim.native) is not bool:
            raise CoordinationError("typed task claim required")
        data, task = self._task(claim.task_id, candidate_sha256)
        if (claim.owner != task["owner"] or claim.token != task["claimToken"]
                or claim.candidate_sha256 != candidate_sha256 or claim.native != task["native"]):
            raise CoordinationError("claim differs from the durable owner, token or candidate")
        return data, task

    @staticmethod
    def _record(data, action, task_id, reason=None):
        data["revision"] += 1
        data["history"].append({"sequence": data["revision"], "action": action,
                                "taskId": task_id, "reason": reason, "recordedAt": _now()})

    @contextmanager
    def _lock(self) -> Iterator[None]:
        try:
            import fcntl
        except ImportError as exc:
            raise CoordinationError("private coordination requires POSIX file locking") from exc
        if any(path.is_symlink() for path in (self.root, *self.root.parents)):
            raise CoordinationError("registry path cannot contain symbolic links")
        try:
            self.root.mkdir(mode=0o700, parents=False, exist_ok=True)
            _private(self.root.stat(), directory=True)
            descriptor = os.open(self.root / "registry.lock",
                                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                _private(os.fstat(descriptor))
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise CoordinationError("registry is busy; no task action occurred") from exc
                yield
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise CoordinationError("private registry store is unavailable or unsafe") from exc

    def _read(self):
        try:
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(descriptor, "rb") as stream:
                _private(os.fstat(stream.fileno()))
                raw = stream.read(MAX_REGISTRY_BYTES + 1)
            if len(raw) > MAX_REGISTRY_BYTES:
                raise CoordinationError("registry exceeds its bounded read limit")
            data = json.loads(raw, object_pairs_hook=_unique_pairs)
            _validate_snapshot(data)
            return data
        except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise CoordinationError("registry is unavailable or invalid bounded JSON") from exc

    def _write(self, data):
        data.pop("recordSha256", None)
        data["recordSha256"] = hashlib.sha256(_json(data)).hexdigest()
        _validate_snapshot(data)
        raw = _json(data)
        if len(raw) > MAX_REGISTRY_BYTES:
            raise CoordinationError("registry exceeds its bounded write limit")
        descriptor, name = tempfile.mkstemp(prefix=".registry-", dir=self.root)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(name).unlink(missing_ok=True)


def _task_records(tasks, candidate):
    if not isinstance(tasks, (tuple, list)) or not 1 <= len(tasks) <= len(M45_PENDING_TASK_IDS):
        raise CoordinationError("a nonempty bounded M4.5 task plan is required")
    records = {}
    for task in tasks:
        if (not isinstance(task, TaskSpec) or not isinstance(task.task_id, str)
                or task.task_id not in M45_PENDING_TASK_IDS):
            raise CoordinationError("task ID is not a pending stable M4.5 obligation")
        if task.task_id in records:
            raise CoordinationError("duplicate task ID")
        if not isinstance(task.owner, str) or not _OWNER.fullmatch(task.owner) or type(task.native) is not bool:
            raise CoordinationError("task owner and native flag must be explicit")
        if (type(task.dependencies) is not tuple
                or any(not isinstance(dep, str) or dep not in M45_PENDING_TASK_IDS for dep in task.dependencies)
                or len(set(task.dependencies)) != len(task.dependencies)):
            raise CoordinationError("task dependencies must be unique stable IDs")
        records[task.task_id] = {
            "dependencies": list(task.dependencies), "owner": task.owner,
            "candidateSha256": candidate, "native": task.native, "status": "pending",
            "claimToken": None, "startedAt": None, "evidenceRefs": [],
            "nativeStopRef": None, "blockReason": None,
        }
    _dependencies(records)
    return records


def _dependencies(tasks):
    visited, active = set(), set()
    def visit(task_id):
        if task_id in active:
            raise CoordinationError("task dependencies contain a cycle")
        if task_id in visited:
            return
        if task_id not in tasks:
            raise CoordinationError("task dependencies are absent from the frozen plan")
        active.add(task_id)
        for dependency in tasks[task_id]["dependencies"]:
            visit(dependency)
        active.remove(task_id)
        visited.add(task_id)
    for task_id in tasks:
        visit(task_id)


def _validate_snapshot(data):
    keys = {"schemaVersion", "candidateSha256", "revision", "tasks", "history", "recordSha256"}
    if not isinstance(data, dict) or set(data) != keys or data["schemaVersion"] != SCHEMA:
        raise CoordinationError("registry schema is invalid")
    payload = {key: value for key, value in data.items() if key != "recordSha256"}
    if data["recordSha256"] != hashlib.sha256(_json(payload)).hexdigest():
        raise CoordinationError("registry snapshot hash mismatch")
    _candidate(data["candidateSha256"])
    tasks, history = data["tasks"], data["history"]
    if not isinstance(tasks, dict) or not tasks or set(tasks) - M45_PENDING_TASK_IDS:
        raise CoordinationError("registry task inventory is invalid")
    if (not isinstance(history, list) or not 1 <= len(history) <= 4096
            or type(data["revision"]) is not int or data["revision"] != len(history)):
        raise CoordinationError("registry history is incomplete or exceeds its bound")
    for index, event in enumerate(history, 1):
        if (not isinstance(event, dict)
                or set(event) != {"sequence", "action", "taskId", "reason", "recordedAt"}
                or type(event["sequence"]) is not int or event["sequence"] != index
                or not isinstance(event["action"], str)
                or event["action"] not in {"initialize", "claim", "start", "release", "interrupt", "finish", "block", "unblock"}
                or (event["taskId"] is not None and (not isinstance(event["taskId"], str) or event["taskId"] not in tasks))
                or (event["action"] == "initialize") != (index == 1)
                or (event["taskId"] is None) != (event["action"] == "initialize")):
            raise CoordinationError("registry history event is invalid")
        _timestamp(event["recordedAt"])
        if event["reason"] is not None:
            _text(event["reason"], "history reason")
    specs = []
    for task_id, task in tasks.items():
        if (not isinstance(task, dict) or set(task) != {
                "dependencies", "owner", "candidateSha256", "native", "status", "claimToken",
                "startedAt", "evidenceRefs", "nativeStopRef", "blockReason"}
                or not isinstance(task["dependencies"], list)
                or task["candidateSha256"] != data["candidateSha256"]
                or not isinstance(task["status"], str) or task["status"] not in _STATUSES):
            raise CoordinationError("registry task record is invalid")
        specs.append(TaskSpec(task_id, tuple(task["dependencies"]), task["owner"], task["native"]))
        status = task["status"]
        claimed = status in _ACTIVE or status in {"complete", "failed"}
        if (claimed and (not isinstance(task["claimToken"], str) or not _TOKEN.fullmatch(task["claimToken"]))
                or not claimed and task["claimToken"] is not None):
            raise CoordinationError("registry claim state is inconsistent")
        started = status in {"started", "interrupted", "complete", "failed"}
        if started != (task["startedAt"] is not None):
            raise CoordinationError("registry durable start is inconsistent")
        if started:
            _timestamp(task["startedAt"])
        blocked = status in {"blocked", "interrupted"}
        if blocked != (task["blockReason"] is not None):
            raise CoordinationError("registry block reason is inconsistent")
        if blocked:
            _text(task["blockReason"], "block reason")
        refs = _stored_refs(task["evidenceRefs"])
        terminal = status in {"complete", "failed"}
        if terminal != bool(refs):
            raise CoordinationError("registry terminal evidence is inconsistent")
        stop = task["nativeStopRef"]
        if (terminal and task["native"]) != (stop is not None):
            raise CoordinationError("registry native stop receipt is inconsistent")
        if stop is not None:
            _stored_refs([stop])
    _task_records(specs, data["candidateSha256"])
    if any(task["status"] in _ACTIVE | {"complete", "failed"}
           and any(tasks[dep]["status"] != "complete" for dep in task["dependencies"])
           for task in tasks.values()):
        raise CoordinationError("registry claimed task dependencies are incomplete")
    if sum(task["native"] and task["status"] in _ACTIVE for task in tasks.values()) > 1:
        raise CoordinationError("registry has duplicate native executor reservations")


def _ref(ref):
    if not isinstance(ref, EvidenceRef):
        raise CoordinationError("typed immutable evidence reference required")
    _text(ref.reference, "evidence reference")
    if not isinstance(ref.sha256, str) or not _SHA256.fullmatch(ref.sha256):
        raise CoordinationError("evidence reference SHA-256 is invalid")
    return {"reference": ref.reference, "sha256": ref.sha256}


def _refs(refs):
    if not isinstance(refs, (list, tuple)) or len(refs) > 64:
        raise CoordinationError("evidence reference collection is unbounded")
    values = [_ref(ref) for ref in refs]
    if len({(ref["reference"], ref["sha256"]) for ref in values}) != len(values):
        raise CoordinationError("evidence references contain duplicates")
    return values


def _stored_refs(refs):
    if not isinstance(refs, list) or any(not isinstance(ref, dict) or set(ref) != {"reference", "sha256"} for ref in refs):
        raise CoordinationError("stored evidence references are invalid")
    return _refs([EvidenceRef(ref["reference"], ref["sha256"]) for ref in refs])


def _candidate(value):
    if not isinstance(value, str) or not _CANDIDATE.fullmatch(value):
        raise CoordinationError("candidate must be an exact Git SHA")


def _text(value, label):
    try:
        valid = isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= 2048
    except UnicodeError as exc:
        raise CoordinationError(f"{label} must be valid UTF-8") from exc
    if not valid:
        raise CoordinationError(f"{label} must be bounded nonempty text")


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise CoordinationError("registry timestamp is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise CoordinationError("registry timestamp must be UTC")


def _private(info, directory=False):
    valid_kind = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (not valid_kind or info.st_uid != os.getuid() or info.st_mode & 0o077
            or (not directory and info.st_nlink != 1)):
        raise CoordinationError("registry must be user-owned, private and free of file aliases")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CoordinationError("registry JSON has duplicate keys")
        result[key] = value
    return result


def _json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise CoordinationError("registry values must be bounded JSON") from exc


def _now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["CoordinationError", "CoordinationRegistry", "EvidenceRef", "M45_PENDING_TASK_IDS",
           "TaskClaim", "TaskSpec"]
