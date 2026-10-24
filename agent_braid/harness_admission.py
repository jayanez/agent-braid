# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy at https://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
# Agent Braid modifications Copyright 2026 Juan Antonio Yáñez García.
# Adapted unique-entry accounting from harness2/core/ledger.py at
# 1cfe254e8d25b15f37048c3730134686abe60335. Changes: independent durable,
# operator-scoped pre-dispatch reservation; no upstream execution or cash route.
"""Verify externally sealed offline admissions and consume them once.

The caller supplies OperatorScope and the expected full manifest SHA from trusted
operator configuration, never from candidate/model input. This module issues no
admissions and dispatches nothing. Read/operator/reservation roots must be pre-created; a new lab leaf may be absent.
The operator and
reservation roots must be private, separate from every import and lab root.
Clock values and the observation snapshot are supplied by that trusted caller.
A reservation is accounting only, including after interruption or recovery.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import stat
from typing import Any

from .harness_manifest import BINDING_NAMES, ManifestError, verify_manifest
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

FORMAT = "braid-harness-admission/v0.1"
RECEIPT_FORMAT = "braid-harness-reservation/v0.1"
MAX_RECORD_BYTES = 65_536
MAX_JOURNAL_BYTES = 8_388_608
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_ROOTS = ("operator_root", "reservation_root", "source_root", "base_root",
          "candidate_root", "context_root", "lab_root")
_ADMISSION_KEYS = {"format", "id", "issuer", "adoptedProfileSha256", "envelopeSha256",
                   "manifestSha256", "bindings", "issuedAt", "expiresAt",
                   "reservedJournalBytes", "executionAuthorization"}
_RECEIPT_KEYS = {"format", "id", "admissionSha256", "manifestSha256", "envelopeSha256",
                 "reservedAt", "expiresAt", "reservedJournalBytes", "executionAuthorization"}


class AdmissionError(ValueError):
    """Sanitized refusal; no recovery path renews consumed authority."""

    def __init__(self, reason: str = "invalid-admission"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-admission") -> None:
    if not condition:
        raise AdmissionError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _integer(value: Any, minimum: int, maximum: int) -> bool:
    return type(value) is int and minimum <= value <= maximum


def open_directory(path: Path, *, private: bool,
               lineage: list[tuple[int, int]] | None = None) -> int:
    """Open without symlinks, recording actual dev/inode ancestry when requested."""
    _require(path.is_absolute() and path == Path(os.path.normpath(path)), "unsafe-root")
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        if lineage is not None:
            info = os.fstat(fd)
            lineage.append((info.st_dev, info.st_ino))
        for part in path.parts[1:]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            if lineage is not None:
                info = os.fstat(fd)
                lineage.append((info.st_dev, info.st_ino))
        info = os.fstat(fd)
        _require(stat.S_ISDIR(info.st_mode), "unsafe-root")
        if private:
            _require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
                     "unsafe-root")
        return fd
    except BaseException:
        os.close(fd)
        raise


def check_record_file(fd: int) -> os.stat_result:
    info = os.fstat(fd)
    _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and
             stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1,
             "unsafe-record")
    return info


def read_record(directory: int, name: str) -> tuple[dict, bytes]:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = check_record_file(fd)
        _require(0 < info.st_size <= MAX_RECORD_BYTES, "record-budget-exceeded")
        raw = os.read(fd, MAX_RECORD_BYTES + 1)
        _require(len(raw) == info.st_size and len(raw) <= MAX_RECORD_BYTES,
                 "record-budget-exceeded")
        value = parse_json(raw)
        _require(type(value) is dict)
        return value, raw
    finally:
        os.close(fd)


@dataclass(frozen=True)
class OperatorScope:
    """Trusted configuration; never construct this object from admission JSON.

    expected_bindings contains exactly the twelve non-envelope identities. Their
    snapshot and these roots/limits define sha256; the final manifest then binds
    that digest as envelopeSha256, avoiding a self-referential full SHA.
    """

    issuer: str
    adopted_profile_sha256: str
    operator_root: Path
    reservation_root: Path
    source_root: Path
    base_root: Path
    candidate_root: Path
    context_root: Path
    lab_root: Path
    expected_bindings: Mapping[str, str]
    observed_at: int
    max_reservations: int = 1
    max_reserved_journal_bytes: int = MAX_JOURNAL_BYTES

    def __post_init__(self) -> None:
        _require(type(self.issuer) is str and _ID.fullmatch(self.issuer) is not None)
        _require(_hash(self.adopted_profile_sha256))
        _require(isinstance(self.expected_bindings, Mapping) and
                 set(self.expected_bindings) == BINDING_NAMES - {"envelope"} and
                 all(_hash(v) for v in self.expected_bindings.values()), "invalid-bindings")
        _require(_integer(self.observed_at, 0, 2**63 - 1), "invalid-clock")
        _require(type(self.max_reservations) is int and self.max_reservations == 1,
                 "invalid-budget")
        _require(_integer(self.max_reserved_journal_bytes, 1, MAX_JOURNAL_BYTES),
                 "invalid-budget")
        for name in _ROOTS:
            path = Path(getattr(self, name))
            _require(path.is_absolute() and path == Path(os.path.normpath(path)), "unsafe-root")
            object.__setattr__(self, name, path)
        object.__setattr__(self, "expected_bindings", freeze(dict(self.expected_bindings)))

    @property
    def sha256(self) -> str:
        return digest({"format": "braid-harness-operator-scope/v0.1", "issuer": self.issuer,
                       "adoptedProfileSha256": self.adopted_profile_sha256,
                       "roots": {n: getattr(self, n).as_posix() for n in _ROOTS},
                       "bindings": thaw(self.expected_bindings), "observedAt": self.observed_at,
                       "maxReservations": self.max_reservations,
                       "maxReservedJournalBytes": self.max_reserved_journal_bytes})


@dataclass(frozen=True)
class Reservation:
    """Immutable accounting receipt, never an execution authorization."""

    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return parse_json(self.canonical_bytes)


def _roots(scope: OperatorScope) -> dict[str, int]:
    opened: dict[str, int] = {}
    lineages: dict[str, list[tuple[int, int]]] = {}
    missing_lab = False
    try:
        for name in _ROOTS:
            path = getattr(scope, name)
            lineage: list[tuple[int, int]] = []
            lineages[name] = lineage
            if name == "lab_root":
                # Reservation precedes import: inspect a missing final destination
                # through its no-follow existing parent without creating it.
                parent = open_directory(path.parent, private=False, lineage=lineage)
                try:
                    try:
                        os.stat(path.name, dir_fd=parent, follow_symlinks=False)
                    except FileNotFoundError:
                        opened[name] = parent
                        missing_lab = True
                        parent = -1
                    else:
                        lineage.clear()
                        opened[name] = open_directory(path, private=False, lineage=lineage)
                finally:
                    if parent >= 0:
                        os.close(parent)
            else:
                opened[name] = open_directory(
                    path, private=name in {"operator_root", "reservation_root"}, lineage=lineage)
        # Lexical checks alone miss case/Unicode aliases on case-insensitive filesystems.
        # Compare actual leaf identities against every other's entire opened lineage.
        # A missing lab has ancestors but no leaf: its parent is not the destination.
        for name in ("operator_root", "reservation_root"):
            path = getattr(scope, name)
            for other in _ROOTS:
                if other == name:
                    continue
                target = getattr(scope, other)
                _require(path != target and path not in target.parents and
                         target not in path.parents and
                         lineages[name][-1] not in lineages[other] and
                         ((other == "lab_root" and missing_lab) or
                          lineages[other][-1] not in lineages[name]),
                         "overlapping-roots")
        return opened
    except BaseException:
        for fd in opened.values():
            os.close(fd)
        raise


def validate_receipt(value: dict, name: str) -> None:
    _require(set(value) == _RECEIPT_KEYS and value["format"] == RECEIPT_FORMAT and
             type(value["id"]) is str and _ID.fullmatch(value["id"]) is not None and
             name == value["id"] + ".json" and value["executionAuthorization"] is False,
             "corrupt-reservation-store")
    _require(all(_hash(value[k]) for k in ("admissionSha256", "manifestSha256", "envelopeSha256")) and
             _integer(value["reservedAt"], 0, 2**63 - 1) and
             _integer(value["expiresAt"], value["reservedAt"] + 1, value["reservedAt"] + 300) and
             _integer(value["reservedJournalBytes"], 1, MAX_JOURNAL_BYTES),
             "corrupt-reservation-store")


def _check_store(directory: int, scope: OperatorScope, record: dict) -> None:
    count, reserved, actual = 0, 0, 0
    # Consume at most maxReservations + lock + one refusal entry.
    with os.scandir(directory) as entries:
        for index, entry in enumerate(entries):
            _require(index <= scope.max_reservations + 1, "reservation-budget-exhausted")
            if entry.name == ".lock":
                continue
            _require(entry.name.endswith(".json") and
                     _ID.fullmatch(entry.name[:-5]) is not None,
                     "corrupt-reservation-store")
            previous, raw = read_record(directory, entry.name)
            validate_receipt(previous, entry.name)
            count += 1
            reserved += previous["reservedJournalBytes"]
            actual += len(raw)
    _require(count < scope.max_reservations and
             reserved + record["reservedJournalBytes"] <= scope.max_reserved_journal_bytes and
             actual + len(canonical(record)) <= scope.max_reserved_journal_bytes,
             "reservation-budget-exhausted")


def _reserve(directory: int, scope: OperatorScope, record: dict) -> Reservation:
    # Read-only preflight ensures malformed/exhausted stores create no new lock.
    # Repeat under lock to close concurrent reservation races.
    _check_store(directory, scope, record)
    lock = os.open(".lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK,
                   0o600, dir_fd=directory)
    try:
        check_record_file(lock)
        _require(os.fstat(lock).st_size == 0, "corrupt-reservation-store")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise AdmissionError("reservation-busy") from exc
        _check_store(directory, scope, record)
        # A partial marker is left consumed on failure; no retry clears it.
        raw = canonical(record)
        fd = os.open(record["id"] + ".json", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=directory)
        try:
            check_record_file(fd)
            remaining = memoryview(raw)
            while remaining:
                written = os.write(fd, remaining)
                _require(written > 0, "reservation-write-failed")
                remaining = remaining[written:]
            os.fsync(fd)
            os.fsync(directory)
        finally:
            os.close(fd)
        return Reservation(raw)
    finally:
        os.close(lock)


def reserve_admission(raw_manifest: bytes, *, expected_manifest_sha256: str,
                      scope: OperatorScope, admission_id: str, now: int) -> Reservation:
    """Consume an externally issued file using current trusted bindings and clock.

    All thirteen manifest identities are checked: the twelve frozen identities
    from scope plus its computed envelope hash. Source files are not imported or
    dispatched here; reservations never establish native or economic acceptance.
    """
    opened: dict[str, int] = {}
    try:
        _require(type(scope) is OperatorScope, "invalid-operator-scope")
        _require(type(admission_id) is str and _ID.fullmatch(admission_id) is not None)
        _require(_integer(now, 0, 2**63 - 1) and
                 scope.observed_at <= now < scope.observed_at + 300, "stale-observation")
        bindings = dict(scope.expected_bindings, envelope=scope.sha256)
        manifest = verify_manifest(raw_manifest, expected_sha256=expected_manifest_sha256,
                                   expected_bindings=bindings)
        limits = manifest.data["limits"]
        _require(now - scope.observed_at < limits["maxAdmissionSeconds"], "stale-observation")
        _require(manifest.data["environment"]["outputDestinationSha256"] ==
                 sha256(scope.lab_root.as_posix().encode("utf-8")).hexdigest(),
                 "destination-drift")
        _require(limits["maxJournalBytes"] <= scope.max_reserved_journal_bytes,
                 "reservation-budget-exhausted")
        opened = _roots(scope)
        admission, raw = read_record(opened["operator_root"], admission_id + ".json")
        _require(set(admission) == _ADMISSION_KEYS and admission["format"] == FORMAT and
                 admission["id"] == admission_id and admission["issuer"] == scope.issuer and
                 admission["adoptedProfileSha256"] == scope.adopted_profile_sha256 and
                 admission["envelopeSha256"] == scope.sha256 and
                 admission["manifestSha256"] == manifest.sha256 and
                 admission["bindings"] == bindings and
                 admission["executionAuthorization"] is False, "authority-drift")
        issued, expires = admission["issuedAt"], admission["expiresAt"]
        _require(_integer(issued, 0, now) and
                 _integer(expires, now + 1, issued + limits["maxAdmissionSeconds"]) and
                 issued >= scope.observed_at, "expired-or-invalid-authority")
        _require(type(admission["reservedJournalBytes"]) is int and
                 admission["reservedJournalBytes"] == limits["maxJournalBytes"], "invalid-budget")
        record = {"format": RECEIPT_FORMAT, "id": admission_id,
                  "admissionSha256": sha256(raw).hexdigest(), "manifestSha256": manifest.sha256,
                  "envelopeSha256": scope.sha256, "reservedAt": now, "expiresAt": expires,
                  "reservedJournalBytes": admission["reservedJournalBytes"],
                  "executionAuthorization": False}
        _require(len(canonical(record)) <= min(MAX_RECORD_BYTES, limits["maxStageOutputBytes"],
                                               scope.max_reserved_journal_bytes),
                 "record-budget-exceeded")
        return _reserve(opened["reservation_root"], scope, record)
    except (OSError, InvalidDecision, ManifestError) as exc:
        raise AdmissionError("admission-refused") from exc
    finally:
        for fd in opened.values():
            os.close(fd)
