# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only local resource observations for one registered tooling activity.

This source observes only the exact process identity supplied by the
supervisor, the caller-bound private results root, and monotonic
time. It is not a provider, token, authorization, or complete telemetry source.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Literal

from .tooling_process_birth import (
    ProcessBirthError,
    ProcessBirthIdentity,
    matches_process_birth,
    sample_process_birth,
    validate_process_birth_identity,
)
from .tooling_supervisor import Clock, ProcessIdentity

MAX_DISK_FILES = 100_000
MAX_DISK_DIRECTORIES = 20_000
MAX_DISK_DEPTH = 32
MAX_PATH_ROOTS = 32
MAX_PROCESS_SAMPLES = 100_000
MAX_PATH_COMPONENT_BYTES = 1024
MAX_RSS_BYTES = (1 << 63) - 1
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ACTIVITY_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")


class ResourceObservationError(ValueError):
    """A local resource source is missing, malformed, or outside its scope."""


@dataclass(frozen=True)
class ResourceMetric:
    """One local metric with explicit completeness, provenance, and coverage."""

    name: Literal["wall_seconds", "rss_bytes", "disk_bytes"]
    value: int | float | None
    status: Literal["observed", "partial", "unknown"]
    source: str
    scope: str
    source_ref: str
    source_sha256: str | None
    started_at: str
    observed_at: str
    coverage_start_at: str | None
    coverage_end_at: str | None
    sample_count: int
    coverage: tuple[str, ...]
    reason: str | None
    usable_for_caps: bool = False


@dataclass(frozen=True)
class LocalResourceSnapshot:
    """Immutable receipt of local-only observations; it does not authorize a run."""

    activity_ref: str
    registration_sha256: str
    sample_index: int
    identity_fingerprint: str | None
    observed_at: str
    wall: ResourceMetric
    rss: ResourceMetric
    disk: ResourceMetric
    source_sha256: str
    authenticity_verified: bool = False
    complete_telemetry_snapshot: bool = False


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(value: object) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ResourceObservationError(f"{field} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ResourceObservationError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ResourceObservationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _metric_payload(metric: ResourceMetric) -> dict[str, object]:
    return {
        "name": metric.name, "value": metric.value, "status": metric.status,
        "source": metric.source, "scope": metric.scope,
        "sourceRef": metric.source_ref, "sourceSha256": metric.source_sha256,
        "startedAt": metric.started_at, "observedAt": metric.observed_at,
        "coverageStartAt": metric.coverage_start_at,
        "coverageEndAt": metric.coverage_end_at, "sampleCount": metric.sample_count,
        "coverage": list(metric.coverage), "reason": metric.reason,
        "usableForCaps": metric.usable_for_caps,
    }


def _snapshot_payload(snapshot: LocalResourceSnapshot) -> dict[str, object]:
    return {
        "schemaVersion": "agent-braid-local-resources-v1",
        "activityRef": snapshot.activity_ref,
        "registrationSha256": snapshot.registration_sha256,
        "sampleIndex": snapshot.sample_index,
        "identityFingerprint": snapshot.identity_fingerprint,
        "observedAt": snapshot.observed_at,
        "wall": _metric_payload(snapshot.wall),
        "rss": _metric_payload(snapshot.rss),
        "disk": _metric_payload(snapshot.disk),
        "authenticityVerified": snapshot.authenticity_verified,
        "completeTelemetrySnapshot": snapshot.complete_telemetry_snapshot,
    }


def verify_resource_snapshot(snapshot: LocalResourceSnapshot) -> bool:
    """Check accidental receipt drift; a matching hash is not authentication."""
    if type(snapshot) is not LocalResourceSnapshot or not _SHA256.fullmatch(snapshot.source_sha256):
        return False
    return _sha(_snapshot_payload(snapshot)) == snapshot.source_sha256


def _identity_fingerprint(identity: ProcessIdentity | None) -> str | None:
    if identity is None:
        return None
    if type(identity) is not ProcessIdentity:
        return None
    return _sha({"pid": identity.pid, "processGroupId": identity.process_group_id,
                 "startedAt": identity.started_at,
                 "executableSha256": identity.executable_sha256,
                 "birthSource": identity.birth.source if identity.birth else None,
                 "birthToken": identity.birth.token if identity.birth else None})


def _validate_identity(identity: ProcessIdentity) -> datetime:
    if type(identity) is not ProcessIdentity:
        raise ResourceObservationError("process identity must be an exact supervisor ProcessIdentity")
    if type(identity.pid) is not int or identity.pid <= 0 or identity.pid > (1 << 31) - 1:
        raise ResourceObservationError("owned process PID is invalid")
    if type(identity.process_group_id) is not int or identity.process_group_id != identity.pid:
        raise ResourceObservationError("owned process group must equal the supervisor-created session leader PID")
    if not isinstance(identity.executable_sha256, str) or not _SHA256.fullmatch(identity.executable_sha256):
        raise ResourceObservationError("owned executable identity hash is malformed")
    if identity.birth is not None:
        try:
            validate_process_birth_identity(identity.birth)
        except ProcessBirthError as exc:
            raise ResourceObservationError("owned kernel birth identity is malformed") from exc
        if identity.birth.pid != identity.pid:
            raise ResourceObservationError("owned kernel birth PID differs from supervisor PID")
    return _parse_timestamp(identity.started_at, "owned process started_at")


def _is_relative_to(path: Path, root: Path) -> bool:
    return path == root or path.is_relative_to(root)


def _canonical_directory(path: str | os.PathLike[str], *, private: bool,
                         expected_uid: int) -> Path:
    raw = Path(path).expanduser().absolute()
    current = Path(raw.anchor)
    for part in raw.parts[1:]:
        current = current / part
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ResourceObservationError("resource root path contains a symlink")
    resolved = raw.resolve(strict=True)
    info = resolved.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise ResourceObservationError("resource root is not a directory")
    if private and (info.st_uid != expected_uid or stat.S_IMODE(info.st_mode) & 0o077):
        raise ResourceObservationError("cohort results root must be user-owned and private")
    return resolved


def _directory_chain_fd(path: Path) -> int:
    """Open every component with directory/no-follow flags; return final fd."""
    if os.name != "posix" or not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ResourceObservationError("no-follow directory descriptors are unavailable")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(path.anchor, flags)
    try:
        for part in path.parts[1:]:
            next_fd = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _directory_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_uid)


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid)


def _open_relative_directory(root: Path, relative: str) -> int:
    descriptor = _directory_chain_fd(root)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        for part in Path(relative).parts:
            if part == ".":
                continue
            next_fd = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = next_fd
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _scan_private_results(root: Path, expected_uid: int) -> tuple[int, str, int, int]:
    """Hash a bounded private logical-size inventory without following links."""
    records = hashlib.sha256()
    file_rechecks: list[tuple[str, str, tuple[int, int, int, int, int, int, int]]] = []
    directory_rechecks: list[tuple[str, tuple[int, int, int, int, int, int]]] = []
    total = files = directories = entries_seen = 0
    pending: list[tuple[str, int, tuple[int, int, int, int, int, int] | None]] = [("", 0, None)]
    while pending:
        relative, depth, expected_identity = pending.pop()
        directory_fd = _open_relative_directory(root, relative)
        try:
            info = os.fstat(directory_fd)
            if not stat.S_ISDIR(info.st_mode):
                raise ResourceObservationError("private results traversal reached a non-directory")
            if info.st_uid != expected_uid or stat.S_IMODE(info.st_mode) & 0o077:
                raise ResourceObservationError("directory in cohort results is not user-owned and private")
            identity = _directory_identity(info)
            if expected_identity is not None and identity != expected_identity:
                raise ResourceObservationError("directory changed before it could be scanned")
            directory_rechecks.append((relative, identity))
            directories += 1
            if directories > MAX_DISK_DIRECTORIES:
                raise ResourceObservationError("cohort results directory limit exceeded")
            record = {"kind": "directory", "path": relative, "identity": identity}
            records.update(_canonical_json(record) + b"\n")
            child_directories: list[tuple[str, int, tuple[int, int, int, int, int, int]]] = []
            children: list[tuple[str, os.stat_result, str]] = []
            with os.scandir(directory_fd) as iterator:
                for entry in iterator:
                    entries_seen += 1
                    if entries_seen > MAX_DISK_FILES + MAX_DISK_DIRECTORIES:
                        raise ResourceObservationError("cohort results entry limit exceeded")
                    if len(entry.name.encode("utf-8", errors="surrogateescape")) > MAX_PATH_COMPONENT_BYTES:
                        raise ResourceObservationError("cohort results path component limit exceeded")
                    child_info = entry.stat(follow_symlinks=False)
                    child_relative = f"{relative}/{entry.name}" if relative else entry.name
                    children.append((child_relative, child_info, entry.name))
            for child_relative, child_info, _name in sorted(children, key=lambda row: row[0], reverse=True):
                if stat.S_ISDIR(child_info.st_mode):
                    if depth + 1 > MAX_DISK_DEPTH:
                        raise ResourceObservationError("cohort results depth limit exceeded")
                    if child_info.st_uid != expected_uid or stat.S_IMODE(child_info.st_mode) & 0o077:
                        raise ResourceObservationError("nested results directory is not user-owned and private")
                    child_directories.append((child_relative, depth + 1, _directory_identity(child_info)))
                elif stat.S_ISREG(child_info.st_mode):
                    if child_info.st_uid != expected_uid or stat.S_IMODE(child_info.st_mode) & 0o077:
                        raise ResourceObservationError("retained result file is not user-owned and private")
                    files += 1
                    if files > MAX_DISK_FILES:
                        raise ResourceObservationError("cohort results file limit exceeded")
                    total += child_info.st_size
                    if total > MAX_RSS_BYTES:
                        raise ResourceObservationError("cohort results logical byte total overflowed")
                    file_id = _file_identity(child_info)
                    file_rechecks.append((relative, Path(child_relative).name, file_id))
                    records.update(_canonical_json({"kind": "file", "path": child_relative,
                                                    "identity": file_id}) + b"\n")
                else:
                    raise ResourceObservationError("symlink or special file encountered in cohort results")
            pending.extend(child_directories)
        finally:
            os.close(directory_fd)

    for parent_relative, name, expected_identity in file_rechecks:
        parent_fd = _open_relative_directory(root, parent_relative)
        try:
            final = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        finally:
            os.close(parent_fd)
        if not stat.S_ISREG(final.st_mode) or _file_identity(final) != expected_identity:
            raise ResourceObservationError("retained result file changed during measurement")
    for relative, expected_identity in directory_rechecks:
        directory_fd = _open_relative_directory(root, relative)
        try:
            final = os.fstat(directory_fd)
        finally:
            os.close(directory_fd)
        if not stat.S_ISDIR(final.st_mode) or _directory_identity(final) != expected_identity:
            raise ResourceObservationError("cohort results directory changed during measurement")
    return total, records.hexdigest(), files, directories


class LocalResourceCollector:
    """Collect local time, sampled owned-process RSS, and retained disk.

    Instantiate at the start of the registered activity. Every ``sample`` call
    returns an immutable receipt. Unknown or partial source data never becomes
    zero, a ``TelemetrySnapshot``, or cap authorization.
    """

    def __init__(self, *, activity_ref: str, registration_sha256: str,
                 results_root: str | os.PathLike[str],
                 source_roots: tuple[str | os.PathLike[str], ...],
                 grant_roots: tuple[str | os.PathLike[str], ...],
                 clock: Clock = Clock()):
        if not isinstance(activity_ref, str) or not _ACTIVITY_REF.fullmatch(activity_ref):
            raise ResourceObservationError("activity_ref must be a short opaque identifier")
        if not isinstance(registration_sha256, str) or not _SHA256.fullmatch(registration_sha256):
            raise ResourceObservationError("registration_sha256 must be lowercase SHA-256")
        if (not isinstance(source_roots, tuple) or not source_roots
                or not isinstance(grant_roots, tuple) or not grant_roots):
            raise ResourceObservationError("non-empty source_roots and grant_roots tuples are required")
        if len(source_roots) + len(grant_roots) > MAX_PATH_ROOTS:
            raise ResourceObservationError("protected path root limit exceeded")
        self.activity_ref = activity_ref
        self.registration_sha256 = registration_sha256
        # The caller binds this exact root to the registration/activity. Do not
        # guess a host layout or relocate retained results inside the collector.
        self._results_root = Path(results_root).expanduser().absolute()
        self.source_roots = source_roots
        self.grant_roots = grant_roots
        self.clock = clock
        self._activity_started_mono = clock.monotonic()
        self._activity_started_at = clock.utc_now()
        if isinstance(self._activity_started_mono, bool) or not isinstance(self._activity_started_mono, (int, float)) \
                or not math.isfinite(self._activity_started_mono):
            raise ResourceObservationError("monotonic activity start must be finite")
        _parse_timestamp(self._activity_started_at, "activity start time")
        self._last_mono = self._activity_started_mono
        self._last_utc = _parse_timestamp(self._activity_started_at, "activity start time")
        self._sample_index = 0
        self._identity: ProcessIdentity | None = None
        self._identity_started_at: datetime | None = None
        self._identity_error: str | None = None
        self._rss_peak: int | None = None
        self._rss_samples = 0
        self._rss_started_at: str | None = None
        self._rss_observed_at: str | None = None
        self._rss_gap_reason: str | None = None
        self._rss_source_sha256: str | None = None
        self._poison_reason: str | None = None

    def sample(self, identity: ProcessIdentity | None) -> LocalResourceSnapshot:
        """Take one bounded local sample; never signals the owned process."""
        self._sample_index += 1
        sample_started_mono = self.clock.monotonic()
        sample_started_at = self.clock.utc_now()
        try:
            sample_started_utc = _parse_timestamp(sample_started_at, "sample start time")
            if (isinstance(sample_started_mono, bool) or not isinstance(sample_started_mono, (int, float))
                    or not math.isfinite(sample_started_mono) or sample_started_mono < self._last_mono):
                raise ResourceObservationError("monotonic clock moved backwards or became invalid")
            if sample_started_utc < self._last_utc:
                raise ResourceObservationError("UTC observation clock moved backwards")
        except ResourceObservationError as exc:
            self._poison_reason = self._poison_reason or str(exc)
        if (isinstance(sample_started_mono, (int, float)) and not isinstance(sample_started_mono, bool)
                and math.isfinite(sample_started_mono)):
            self._last_mono = sample_started_mono
        if "sample_started_utc" in locals():
            self._last_utc = sample_started_utc

        identity_fingerprint = _identity_fingerprint(identity or self._identity)
        if self._poison_reason is None:
            self._accept_identity(identity)
        identity_fingerprint = _identity_fingerprint(self._identity)
        rss_started = sample_started_at
        if self._poison_reason is not None:
            self._mark_rss_gap(self._poison_reason)
        elif self._identity_error is not None:
            self._mark_rss_gap(self._identity_error)
        elif identity is None and self._identity is None:
            # Pre-start is explicitly unknown, not a zero sample or a missing
            # sample inside the process-scoped RSS interval.
            pass
        elif identity is None:
            self._mark_rss_gap("owned process identity is unavailable for this sample")
        elif self._identity is None:
            self._mark_rss_gap("owned process identity was not accepted")
        elif self._rss_samples >= MAX_PROCESS_SAMPLES:
            self._mark_rss_gap("process RSS sample limit exceeded")
        else:
            try:
                if self._identity.birth is None:
                    raise ResourceObservationError("supervisor could not capture kernel process birth identity")
                native = sample_process_birth(self._identity.birth)
                if not matches_process_birth(self._identity.birth, native):
                    raise ResourceObservationError("kernel process birth identity changed; possible PID reuse")
                observed = native.resident_size_bytes
                digest = _sha({"source": native.source, "token": native.token,
                               "residentSizeBytes": observed})
                self._rss_peak = max(self._rss_peak or 0, observed)
                self._rss_samples += 1
                if self._rss_started_at is None:
                    self._rss_started_at = rss_started
                self._rss_observed_at = native.observed_at
                previous = self._rss_source_sha256 or ("0" * 64)
                self._rss_source_sha256 = hashlib.sha256(
                    f"{previous}:{digest}:{observed}:{native.observed_at}".encode("ascii")
                ).hexdigest()
            except (OSError, ProcessBirthError, ResourceObservationError, ValueError) as exc:
                self._mark_rss_gap(str(exc) if isinstance(exc, (ResourceObservationError, ProcessBirthError))
                                   else type(exc).__name__)

        disk_started = self.clock.utc_now()
        try:
            disk_started_utc = _parse_timestamp(disk_started, "disk scan start time")
            disk_total, disk_sha, file_count, directory_count = self._measure_disk()
            disk_observed_at = self.clock.utc_now()
            if _parse_timestamp(disk_observed_at, "disk scan completion time") < disk_started_utc:
                raise ResourceObservationError("UTC observation clock moved backwards during disk scan")
            disk = self._metric(
                "disk_bytes", disk_total, "observed", "bounded no-follow private results walk",
                "caller-bound registration/activity cohort results root; logical retained file lengths",
            f"cohort-results:{self.activity_ref}:{self.registration_sha256}", disk_sha,
                disk_started, disk_observed_at, self._sample_index,
                ("complete bounded inventory of this root at the scan instant",
                 "no symlink or special file was followed", "allocated blocks and out-of-root files are excluded",
                 "directory traversal and metadata rechecks are not an atomic snapshot"), None,
            )
            # Include inventory counts only in the digest, not private names.
            disk = replace(disk, source_sha256=_sha({"manifest": disk_sha, "files": file_count,
                                                       "directories": directory_count}))
        except (OSError, ResourceObservationError, RuntimeError) as exc:
            disk_observed_at = self.clock.utc_now()
            disk = self._metric(
                "disk_bytes", None, "unknown", "bounded no-follow private results walk",
                "caller-bound registration/activity cohort results root",
                f"cohort-results:{self.activity_ref}:{self.registration_sha256}",
                None, disk_started, disk_observed_at, 0,
                ("filesystem metadata calls are synchronous and kernel I/O timing is not guaranteed"),
                str(exc) if isinstance(exc, ResourceObservationError) else type(exc).__name__,
            )

        sample_end_mono = self.clock.monotonic()
        sample_end_at = self.clock.utc_now()
        try:
            sample_end_utc = _parse_timestamp(sample_end_at, "sample completion time")
            if (isinstance(sample_end_mono, bool) or not isinstance(sample_end_mono, (int, float))
                    or not math.isfinite(sample_end_mono) or sample_end_mono < sample_started_mono):
                raise ResourceObservationError("monotonic clock moved backwards during sample")
            if sample_end_utc < sample_started_utc:
                raise ResourceObservationError("UTC observation clock moved backwards during sample")
        except ResourceObservationError as exc:
            self._poison_reason = self._poison_reason or str(exc)
        elapsed = None if self._poison_reason else sample_end_mono - self._activity_started_mono
        wall = self._metric(
            "wall_seconds", elapsed, "observed" if elapsed is not None else "unknown",
            "time.monotonic from collector construction", "registered activity elapsed through this sample",
            f"activity:{self.activity_ref}", None, self._activity_started_at, sample_end_at,
            0, ("monotonic elapsed includes gaps and local setup after collector construction",
                "not provider execution time or human time"), self._poison_reason,
        )
        rss_status: Literal["observed", "partial", "unknown"]
        if self._rss_peak is None:
            rss_status = "unknown"
        elif self._rss_gap_reason is not None or self._poison_reason is not None:
            rss_status = "partial"
        else:
            rss_status = "observed"
        rss_reason = (self._poison_reason or self._identity_error or self._rss_gap_reason)
        if rss_reason is None and identity is None and self._identity is None:
            rss_reason = "no owned process identity is available yet; this does not establish zero RSS"
        rss = self._metric(
            "rss_bytes", self._rss_peak, rss_status, "kernel birth-bound resident-size samples",
            "exact supervisor-owned session leader process only; descendants are not included",
            f"process:{identity_fingerprint or 'unknown'}",
            self._rss_source_sha256, self._rss_started_at or sample_started_at,
            self._rss_observed_at or sample_end_at, self._rss_samples,
            ("monotonic maximum of successful sampled resident sizes; not a continuous peak",
             "covers only the supervisor-owned root process, not descendants or a process tree",
             "native kernel values are tied to the captured process birth token"),
            rss_reason,
        )
        if self._sample_index <= 0:
            raise AssertionError("sample index must be positive")
        snapshot = LocalResourceSnapshot(
            activity_ref=self.activity_ref,
            registration_sha256=self.registration_sha256,
            sample_index=self._sample_index,
            identity_fingerprint=identity_fingerprint,
            observed_at=sample_end_at,
            wall=wall, rss=rss, disk=disk,
            source_sha256="",
        )
        return replace(snapshot, source_sha256=_sha(_snapshot_payload(snapshot)))

    def _accept_identity(self, identity: ProcessIdentity | None) -> None:
        if identity is None:
            return
        try:
            started_at = _validate_identity(identity)
        except ResourceObservationError as exc:
            self._identity_error = self._identity_error or str(exc)
            return
        if self._identity is None:
            self._identity = identity
            self._identity_started_at = started_at
            if identity.birth is not None:
                self._rss_peak = identity.birth.resident_size_bytes
                self._rss_samples = 1
                self._rss_started_at = identity.birth.observed_at
                self._rss_observed_at = identity.birth.observed_at
                self._rss_source_sha256 = _sha({
                    "source": identity.birth.source,
                    "token": identity.birth.token,
                    "residentSizeBytes": identity.birth.resident_size_bytes,
                    "observedAt": identity.birth.observed_at,
                })
        elif identity != self._identity:
            self._identity_error = "owned process identity changed during registered activity"

    def _mark_rss_gap(self, reason: str) -> None:
        if self._rss_gap_reason is None:
            self._rss_gap_reason = reason

    def _metric(self, name, value, status, source, scope, source_ref, source_sha256,
                started_at, observed_at, sample_count, coverage, reason) -> ResourceMetric:
        return ResourceMetric(
            name=name, value=value, status=status, source=source, scope=scope,
            source_ref=source_ref, source_sha256=source_sha256,
            started_at=started_at, observed_at=observed_at,
            coverage_start_at=started_at if status != "unknown" else None,
            coverage_end_at=observed_at if status != "unknown" else None,
            sample_count=sample_count, coverage=tuple(coverage), reason=reason,
            usable_for_caps=False,
        )

    def _measure_disk(self) -> tuple[int, str, int, int]:
        uid = os.getuid()
        results = _canonical_directory(self._results_root, private=True, expected_uid=uid)
        protected: list[Path] = []
        for raw in (*self.source_roots, *self.grant_roots):
            canonical = _canonical_directory(raw, private=False, expected_uid=uid)
            protected.append(canonical)
        if any(_is_relative_to(results, root) or _is_relative_to(root, results) for root in protected):
            raise ResourceObservationError("cohort results root overlaps a source or grant root")
        for ancestor in (results.parent, results.parent.parent):
            info = ancestor.stat()
            if info.st_uid != uid or stat.S_IMODE(info.st_mode) & 0o077:
                raise ResourceObservationError("cohort results parent must be user-owned and private")
        return _scan_private_results(results, uid)


__all__ = [
    "LocalResourceCollector", "LocalResourceSnapshot", "ResourceMetric",
    "ResourceObservationError", "verify_resource_snapshot",
]
