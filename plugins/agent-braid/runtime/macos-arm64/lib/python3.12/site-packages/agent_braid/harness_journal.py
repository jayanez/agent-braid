# SPDX-License-Identifier: AGPL-3.0-only
"""Durable attempt journal, checkpoint chain and conservative recovery (SPEC-048 T007).

One private, pre-created directory holds append-only, hash-chained, ``O_EXCL`` records per
attempt: ``<id>.start.json`` (written and fsynced *before* dispatch), ``<id>.cpNN.json``
checkpoints and a single ``<id>.end.json`` that is either a ``terminal`` copied from an
observed ``LabResult`` or a ``reconciled`` record written by recovery. A start consumes the
reservation it names: an interruption never refunds it, recovery never renews it, and the next
attempt needs a new, separately admitted reservation after the previous attempt is reconciled.

Recovery only ever records what was durably written. An attempt with no terminal record is
reconciled to ``interrupted`` with unknown outcome and cost, never to ``completed``, even when
the fixture happened to finish. A supplied manifest that differs from the one bound at start
refuses as drift. Records are evidence, never authorization: ``executionAuthorization`` is
false everywhere. Hashes are not signatures; same-UID tampering that rewrites a whole chain is
excluded, as is fsync loss on storage that ignores it.

Publication is atomic: a record is written and fsynced under a ``.tmp-<hex>`` name and renamed
to its final name while the journal lock is held, so a kill leaves either no record or a whole
one. Leftover temp files are ignored by readers (and counted against the entry budget) and swept
by the next locked write. A damaged *published* record still refuses; nothing is repaired.

Coupling: the storage and predicate helpers are the underscore-private ones of `harness_admission`
(`_directory`, `_read_record`, `_file_info`, `_validate_receipt`) and `harness_observation`
(`_ALL_TERMINALS`, `_is_relative`), shared on purpose so the private-store rules stay defined in one
place. Promoting them to public names would invalidate the pinned hashes in earlier evidence files,
so that rename is left to a change that refreshes them.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import fcntl
from functools import wraps
from hashlib import sha256
import os
from pathlib import Path
import re
from typing import Any

from .harness_admission import (
    MAX_RECORD_BYTES, AdmissionError, Reservation, _directory, _file_info, _read_record,
    _validate_receipt)
from .harness_lab import ContainmentBackend, FixtureLimits, LabResult, run_fixture
from .harness_manifest import HarnessManifest
from .harness_observation import (
    _ALL_TERMINALS, MAX_ARTIFACTS, MAX_TIME, ExportInventory, _is_relative)
from .system_one import InvalidDecision, canonical

FORMAT = "braid-harness-journal/v0.1"
MAX_CHECKPOINTS = 8
MAX_ATTEMPTS = 16
MAX_WORK_ITEMS = 16
MAX_ENTRIES = 1 + MAX_ATTEMPTS * (MAX_CHECKPOINTS + 2)
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_TEMP = re.compile(r"\.tmp-[0-9a-f]{16}\Z")
_NAME = re.compile(r"([a-z0-9][a-z0-9-]{0,63})\.(start|cp[0-9]{2}|end)\.json\Z")
_FILE_KINDS = {"start": ("start",), "cp": ("checkpoint",), "end": ("terminal", "reconciled")}
_COMMON = {"format", "kind", "attemptId", "manifestSha256", "at", "prevSha256",
           "executionAuthorization"}
_EXTRA = {
    "start": {"fixtureSha256", "admissionSha256", "reservationId", "expiresAt", "budgetBytes"},
    "checkpoint": {"seq", "completed", "pending", "artifacts", "permissionRenewed"},
    "terminal": {"state", "observationSha256", "containment", "settled", "cleaned"},
    "reconciled": {"state", "outcome", "cost"},
}


class JournalError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-journal"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-journal") -> None:
    if not condition:
        raise JournalError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _domain(func: Callable) -> Callable:
    """Keep every failure inside the module's error class."""
    @wraps(func)
    def guarded(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (OSError, InvalidDecision, AdmissionError):
            raise JournalError("journal-io-failed") from None
    return guarded


# --- status -----------------------------------------------------------------------


@dataclass(frozen=True)
class AttemptStatus:
    """What the journal durably says about one attempt; never an authorization."""

    attempt_id: str
    manifest_sha256: str
    phase: str            # started | checkpointed | ended
    state: str | None     # terminal state once ended; ``interrupted`` for a reconciled attempt
    outcome: str          # pending | recorded | unknown
    source: str | None    # terminal | recovery
    completed: tuple[str, ...]
    pending: tuple[str, ...]
    records: int

    @property
    def executionAuthorization(self) -> bool:
        return False

    @property
    def redispatch_allowed(self) -> bool:
        return False

    @property
    def permission_renewed(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return {"attemptId": self.attempt_id, "manifestSha256": self.manifest_sha256,
                "phase": self.phase, "state": self.state, "outcome": self.outcome,
                "source": self.source, "completed": list(self.completed),
                "pending": list(self.pending), "records": self.records,
                "redispatchAllowed": False, "permissionRenewed": False,
                "executionAuthorization": False}


# --- storage ------------------------------------------------------------------------


def _open_root(root: Any) -> int:
    _require(isinstance(root, Path), "unsafe-root")
    try:
        return _directory(root, private=True)
    except (OSError, AdmissionError):
        raise JournalError("unsafe-root") from None


class _Locked:
    """Open the journal directory and hold its non-blocking exclusive lock."""

    def __init__(self, root: Any):
        self.root, self.directory, self.lock = root, -1, -1

    def __enter__(self) -> int:
        self.directory = _open_root(self.root)
        try:
            self.lock = self._open_lock()
            _file_info(self.lock)
            _require(os.fstat(self.lock).st_size == 0, "corrupt-journal")
            try:
                fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise JournalError("journal-busy") from None
        except AdmissionError:
            self.__exit__()
            raise JournalError("corrupt-journal") from None
        except BaseException:
            self.__exit__()
            raise
        return self.directory

    def _open_lock(self) -> int:
        # Concurrent O_CREAT of one name can transiently report ENOENT on some filesystems
        # (observed on APFS); the file is never removed, so a few retries are safe.
        for _ in range(3):
            try:
                return self._create_lock()
            except FileNotFoundError:
                continue
        return self._create_lock()

    def _create_lock(self) -> int:
        return os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                       0o600, dir_fd=self.directory)

    def __exit__(self, *exc: Any) -> None:
        for fd in (self.lock, self.directory):
            if fd >= 0:
                os.close(fd)
        self.lock = self.directory = -1


def _validate_record(kind_name: str, record: Any, attempt_id: str) -> None:
    ok = type(record) is dict and type(record.get("kind")) is str and record["kind"] in _EXTRA
    _require(ok, "corrupt-journal")
    kind = record["kind"]
    _require(set(record) == _COMMON | _EXTRA[kind] and record["format"] == FORMAT
             and record["attemptId"] == attempt_id and _hash(record["manifestSha256"])
             and record["executionAuthorization"] is False and _int(record["at"], 0, MAX_TIME)
             and kind in _FILE_KINDS[kind_name[:2] if kind_name.startswith("cp") else kind_name]
             and (record["prevSha256"] is None) == (kind == "start")
             and (kind == "start" or _hash(record["prevSha256"])), "corrupt-journal")
    if kind == "start":
        _require(all(_hash(record[k]) for k in ("fixtureSha256", "admissionSha256"))
                 and type(record["reservationId"]) is str
                 and _ID.fullmatch(record["reservationId"]) is not None
                 and _int(record["expiresAt"], record["at"] + 1, MAX_TIME)
                 and _int(record["budgetBytes"], 1, 1 << 40), "corrupt-journal")
    elif kind == "checkpoint":
        _require(_int(record["seq"], 1, MAX_CHECKPOINTS) and kind_name == f"cp{record['seq']:02d}"
                 and record["permissionRenewed"] is False
                 and _work(record["completed"]) and _work(record["pending"])
                 and not set(record["completed"]) & set(record["pending"])
                 and _artifacts(record["artifacts"]), "corrupt-journal")
    elif kind == "terminal":
        _require(record["state"] in _ALL_TERMINALS and _hash(record["observationSha256"])
                 and record["containment"] in ("simulated", "native")
                 and type(record["settled"]) is bool and type(record["cleaned"]) is bool,
                 "corrupt-journal")
    else:
        _require(record["state"] == "interrupted" and record["outcome"] == "unknown"
                 and record["cost"] == "unknown", "corrupt-journal")


def _work(value: Any) -> bool:
    return (type(value) is list and len(value) <= MAX_WORK_ITEMS and len(set(value)) == len(value)
            and all(type(i) is str and _ID.fullmatch(i) is not None for i in value))


def _artifacts(value: Any) -> bool:
    return (type(value) is dict and len(value) <= MAX_ARTIFACTS
            and all(_is_relative(k) and _hash(v) for k, v in value.items()))


@dataclass(frozen=True)
class _Attempt:
    records: tuple[dict, ...]
    raws: tuple[bytes, ...]

    @property
    def start(self) -> dict:
        return self.records[0]

    @property
    def end(self) -> dict | None:
        last = self.records[-1]
        return last if last["kind"] in ("terminal", "reconciled") else None

    def extended(self, record: dict, raw: bytes) -> "_Attempt":
        return _Attempt(self.records + (record,), self.raws + (raw,))

    @property
    def last_sha256(self) -> str:
        return sha256(self.raws[-1]).hexdigest()

    @property
    def last_at(self) -> int:
        return self.records[-1]["at"]

    def status(self) -> AttemptStatus:
        checkpoints = [r for r in self.records if r["kind"] == "checkpoint"]
        done, todo = (tuple(checkpoints[-1]["completed"]), tuple(checkpoints[-1]["pending"])) \
            if checkpoints else ((), ())
        end = self.end
        if end is None:
            phase, state, outcome, source = ("checkpointed" if checkpoints else "started",
                                             None, "pending", None)
        else:
            phase, state = "ended", end["state"]
            outcome, source = ("recorded", "terminal") if end["kind"] == "terminal" \
                else ("unknown", "recovery")
        return AttemptStatus(self.start["attemptId"], self.start["manifestSha256"], phase, state,
                             outcome, source, done, todo, len(self.records))


def _load(directory: int) -> dict[str, _Attempt]:
    """Read and verify every record; any irregularity refuses, nothing is repaired."""
    names: dict[str, dict[str, str]] = {}
    with os.scandir(directory) as entries:
        for index, entry in enumerate(entries):
            _require(index < MAX_ENTRIES, "journal-budget-exhausted")
            if entry.name == ".lock" or _TEMP.fullmatch(entry.name):
                continue
            match = _NAME.fullmatch(entry.name)
            _require(match is not None, "corrupt-journal")
            names.setdefault(match[1], {})[match[2]] = entry.name
    _require(len(names) <= MAX_ATTEMPTS, "journal-budget-exhausted")
    attempts: dict[str, _Attempt] = {}
    for attempt_id, group in names.items():
        order = ["start"] + sorted(k for k in group if k.startswith("cp")) + (
            ["end"] if "end" in group else [])
        _require("start" in group and set(order) == set(group) and
                 [k for k in order if k.startswith("cp")] ==
                 [f"cp{n:02d}" for n in range(1, len(order) - ("end" in group))],
                 "corrupt-journal")
        records, raws = [], []
        for key in order:
            try:
                record, raw = _read_record(directory, group[key])
            except (OSError, InvalidDecision, AdmissionError):
                raise JournalError("corrupt-journal") from None
            _validate_record(key, record, attempt_id)
            if records:
                _require(record["prevSha256"] == sha256(raws[-1]).hexdigest()
                         and record["manifestSha256"] == records[0]["manifestSha256"]
                         and record["at"] >= records[-1]["at"], "corrupt-journal")
            records.append(record)
            raws.append(raw)
        attempts[attempt_id] = _Attempt(tuple(records), tuple(raws))
    return attempts


def _sweep_temp(directory: int) -> None:
    """Remove temp files of killed writers; the caller holds the lock, so none is live."""
    with os.scandir(directory) as entries:
        stale = [e.name for e in entries if _TEMP.fullmatch(e.name)]
    for name in stale:
        os.unlink(name, dir_fd=directory)


def _append(directory: int, attempts: Mapping[str, _Attempt], name: str, record: dict,
            budget: int) -> bytes:
    """Publish ``record`` atomically as ``name`` and return its canonical bytes."""
    raw = canonical(record)
    used = sum(len(r) for a in attempts.values() for r in a.raws)
    _require(len(raw) <= MAX_RECORD_BYTES and used + len(raw) <= budget, "journal-budget-exhausted")
    _sweep_temp(directory)
    try:
        os.stat(name, dir_fd=directory, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise JournalError("record-exists")
    temp = f".tmp-{os.urandom(8).hex()}"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                 dir_fd=directory)
    try:
        _file_info(fd)
        remaining = memoryview(raw)
        while remaining:
            written = os.write(fd, remaining)
            _require(written > 0, "journal-io-failed")
            remaining = remaining[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.rename(temp, name, src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    return raw


def _record(kind: str, attempt: _Attempt | None, attempt_id: str, manifest_sha256: str, now: int,
            **fields: Any) -> dict:
    return {"format": FORMAT, "kind": kind, "attemptId": attempt_id,
            "manifestSha256": manifest_sha256, "at": now,
            "prevSha256": attempt.last_sha256 if attempt else None,
            "executionAuthorization": False, **fields}


# --- argument checks ----------------------------------------------------------------


def _args(manifest: Any, attempt_id: Any, now: Any) -> None:
    _require(isinstance(manifest, HarnessManifest), "invalid-manifest")
    _require(type(attempt_id) is str and _ID.fullmatch(attempt_id) is not None, "invalid-attempt")
    _require(_int(now, 0, MAX_TIME), "invalid-time")


def _bound(attempts: Mapping[str, _Attempt], manifest: HarnessManifest, attempt_id: str,
           now: int) -> _Attempt:
    """The named attempt, refused as drift unless it is bound to this exact manifest."""
    attempt = attempts.get(attempt_id)
    _require(attempt is not None, "unknown-attempt")
    start = attempt.start
    _require(start["manifestSha256"] == manifest.sha256, "manifest-drift")
    _require(start["fixtureSha256"] == manifest.bindings["fixture"], "fixture-drift")
    _require(now >= attempt.last_at, "clock-regression")
    return attempt


def _reservation(reservation: Any) -> dict:
    _require(isinstance(reservation, Reservation), "invalid-reservation")
    try:
        value = reservation.to_dict()
        _validate_receipt(value, f"{value.get('id')}.json")
    except (InvalidDecision, AdmissionError):
        raise JournalError("invalid-reservation") from None
    return value


# --- public operations --------------------------------------------------------------


@_domain
def begin_attempt(root: Path, manifest: HarnessManifest, *, attempt_id: str,
                  reservation: Reservation, now: int) -> AttemptStatus:
    """Durably mark an attempt as started *before* dispatch, consuming ``reservation``.

    Refuses a reservation already used by any attempt, one for another manifest or outside its
    window, and any new attempt while an earlier one has no end record (reconcile it first).
    """
    _args(manifest, attempt_id, now)
    receipt = _reservation(reservation)
    _require(receipt["manifestSha256"] == manifest.sha256, "admission-mismatch")
    _require(receipt["reservedAt"] <= now < receipt["expiresAt"], "admission-expired")
    with _Locked(root) as directory:
        attempts = _load(directory)
        _require(attempt_id not in attempts, "attempt-exists")
        _require(all(a.end for a in attempts.values()), "unreconciled-attempt")
        _require(all(a.start["admissionSha256"] != reservation.sha256 and
                     a.start["reservationId"] != receipt["id"] for a in attempts.values()),
                 "admission-consumed")
        _require(all(now >= a.last_at for a in attempts.values()), "clock-regression")
        record = _record("start", None, attempt_id, manifest.sha256, now,
                         fixtureSha256=manifest.bindings["fixture"],
                         admissionSha256=reservation.sha256, reservationId=receipt["id"],
                         expiresAt=receipt["expiresAt"], budgetBytes=receipt["reservedJournalBytes"])
        raw = _append(directory, attempts, f"{attempt_id}.start.json", record,
                      receipt["reservedJournalBytes"])
        return _Attempt((record,), (raw,)).status()


@_domain
def checkpoint(root: Path, manifest: HarnessManifest, *, attempt_id: str, completed: Sequence[str],
               pending: Sequence[str], artifacts: Mapping[str, str], now: int) -> AttemptStatus:
    """Append a handoff checkpoint of exact completed/pending work; renews nothing."""
    _args(manifest, attempt_id, now)
    done, todo = list(completed) if type(completed) in (list, tuple) else None, \
        list(pending) if type(pending) in (list, tuple) else None
    files = dict(artifacts) if isinstance(artifacts, Mapping) else None
    _require(_work(done) and _work(todo) and not set(done) & set(todo) and _artifacts(files),
             "invalid-checkpoint")
    with _Locked(root) as directory:
        attempts = _load(directory)
        attempt = _bound(attempts, manifest, attempt_id, now)
        _require(attempt.end is None, "attempt-ended")
        seq = len(attempt.records)  # start + n checkpoints => next sequence number
        _require(seq <= MAX_CHECKPOINTS, "checkpoint-budget-exhausted")
        record = _record("checkpoint", attempt, attempt_id, manifest.sha256, now, seq=seq,
                         completed=done, pending=todo, artifacts=files, permissionRenewed=False)
        raw = _append(directory, attempts, f"{attempt_id}.cp{seq:02d}.json", record,
                      attempt.start["budgetBytes"])
        return attempt.extended(record, raw).status()


@_domain
def finish_attempt(root: Path, manifest: HarnessManifest, *, attempt_id: str, result: LabResult,
                   now: int) -> AttemptStatus:
    """Record the terminal state of an observed run; the state is copied, never upgraded."""
    _args(manifest, attempt_id, now)
    _require(isinstance(result, LabResult), "invalid-result")
    data = result.observation.data
    _require(data["attemptId"] == attempt_id and data["manifestSha256"] == manifest.sha256,
             "result-mismatch")
    with _Locked(root) as directory:
        attempts = _load(directory)
        attempt = _bound(attempts, manifest, attempt_id, now)
        _require(attempt.end is None, "attempt-ended")
        record = _record("terminal", attempt, attempt_id, manifest.sha256, now,
                         state=data["terminal"], observationSha256=result.observation.sha256,
                         containment=result.containment, settled=result.settled,
                         cleaned=result.cleaned)
        _validate_record("end", record, attempt_id)
        raw = _append(directory, attempts, f"{attempt_id}.end.json", record,
                      attempt.start["budgetBytes"])
        return attempt.extended(record, raw).status()


@_domain
def inspect_attempt(root: Path, manifest: HarnessManifest, *, attempt_id: str,
                    now: int) -> AttemptStatus:
    """Read-only recovery view; an attempt with no end record reports ``pending``."""
    _args(manifest, attempt_id, now)
    directory = _open_root(root)
    try:
        return _bound(_load(directory), manifest, attempt_id, now).status()
    finally:
        os.close(directory)


@_domain
def reconcile_attempt(root: Path, manifest: HarnessManifest, *, attempt_id: str,
                      now: int) -> AttemptStatus:
    """Close an attempt that has no end record as ``interrupted`` with unknown outcome and cost.

    Idempotent: an already ended attempt is reported unchanged. Completed work survives only
    as the checkpoints and terminal record that were durably written.
    """
    _args(manifest, attempt_id, now)
    with _Locked(root) as directory:
        attempts = _load(directory)
        attempt = _bound(attempts, manifest, attempt_id, now)
        if attempt.end is not None:
            return attempt.status()
        record = _record("reconciled", attempt, attempt_id, manifest.sha256, now,
                         state="interrupted", outcome="unknown", cost="unknown")
        raw = _append(directory, attempts, f"{attempt_id}.end.json", record,
                      attempt.start["budgetBytes"])
        return attempt.extended(record, raw).status()


def run_journaled(root: Path, manifest: HarnessManifest, fixture: bytes, *, attempt_id: str,
                  reservation: Reservation, backend: ContainmentBackend, inventory: ExportInventory,
                  now: int, retention_seconds: int, inputs: Mapping[str, bytes] | None = None,
                  limits: FixtureLimits | None = None) -> AttemptStatus:
    """Start, checkpoint, dispatch and finish one attempt; a crash leaves it unreconciled.

    If the runner refuses after the durable start the attempt stays open (it may have run),
    so the next attempt must reconcile it first.
    """
    begin_attempt(root, manifest, attempt_id=attempt_id, reservation=reservation, now=now)
    checkpoint(root, manifest, attempt_id=attempt_id, completed=[], pending=["dispatch"],
               artifacts={}, now=now)
    result = run_fixture(manifest, fixture, backend=backend, attempt_id=attempt_id,
                         inventory=inventory, now=now, retention_seconds=retention_seconds,
                         inputs=inputs, limits=limits)
    return finish_attempt(root, manifest, attempt_id=attempt_id, result=result, now=now)
