# SPDX-License-Identifier: AGPL-3.0-only
"""Local, bounded measurement primitives for a future tooling capture.

Only explicitly supplied process IDs and private artifact roots are observed.
The module does not launch hosts/providers and cannot measure provider billing,
tokens, or human time. Missing or unstable observations remain ``None``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import time
from typing import Callable, Iterable, Mapping

from .tooling_capture import MeasuredCosts

MAX_PHASES = 1024
MAX_EXPLICIT_PIDS = 256
MAX_RSS_SAMPLES = 100_000
MAX_DISK_ROOTS = 16
MAX_DISK_FILES = 100_000
MAX_DISK_DIRECTORIES = 20_000


class MeasurementError(ValueError):
    """A measurement cannot be treated as complete or trustworthy."""


@dataclass(frozen=True)
class Observation:
    """A value and provenance, with explicit incompleteness when unavailable."""

    value: int | float | None
    status: str
    source: str
    started_at: str
    observed_at: str
    reason: str | None = None
    details: Mapping[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "status": self.status,
            "source": self.source,
            "startedAt": self.started_at,
            "observedAt": self.observed_at,
            "reason": self.reason,
            "details": dict(self.details or {}),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class PhaseInterval:
    name: str
    start_ns: int
    end_ns: int

    @property
    def seconds(self) -> float:
        return (self.end_ns - self.start_ns) / 1_000_000_000


class WallClock:
    """Capture monotonic total duration and non-additive named phase intervals.

    Phase durations are descriptive and may overlap. ``phase_union_seconds``
    merges overlapping intervals; it must not be added to total wall time.
    The total is measured once from construction to ``finish`` and includes gaps.
    """

    def __init__(self, *, clock_ns: Callable[[], int] = time.monotonic_ns,
                 wall_clock: Callable[[], str] = _utc_now):
        self._clock_ns = clock_ns
        self._wall_clock = wall_clock
        self._start_ns = clock_ns()
        self._started_at = wall_clock()
        self._active: dict[str, int] = {}
        self._phases: list[PhaseInterval] = []
        self._finished: Observation | None = None

    def start_phase(self, name: str) -> None:
        self._ensure_open()
        _validate_name(name)
        if len(self._phases) + len(self._active) >= MAX_PHASES:
            raise MeasurementError("phase inventory limit exceeded")
        if name in self._active:
            raise MeasurementError(f"phase already active: {name}")
        self._active[name] = self._clock_ns()

    def end_phase(self, name: str) -> PhaseInterval:
        self._ensure_open()
        if name not in self._active:
            raise MeasurementError(f"phase is not active: {name}")
        end = self._clock_ns()
        start = self._active.pop(name)
        if end < start:
            raise MeasurementError("monotonic clock moved backwards")
        interval = PhaseInterval(name, start, end)
        self._phases.append(interval)
        return interval

    def finish(self) -> Observation:
        if self._finished is not None:
            return self._finished
        end = self._clock_ns()
        observed = self._wall_clock()
        if end < self._start_ns:
            raise MeasurementError("monotonic clock moved backwards")
        if self._active:
            self._finished = Observation(None, "unknown", "time.monotonic_ns",
                                         self._started_at, observed,
                                         "active phases were not closed",
                                         {"activePhases": sorted(self._active)})
        else:
            self._finished = Observation((end - self._start_ns) / 1_000_000_000,
                                         "observed", "time.monotonic_ns",
                                         self._started_at, observed)
        return self._finished

    @property
    def phases(self) -> tuple[PhaseInterval, ...]:
        return tuple(self._phases)

    @property
    def phase_union_seconds(self) -> float | None:
        if self._active:
            return None
        spans = sorted((phase.start_ns, phase.end_ns) for phase in self._phases)
        if not spans:
            return 0.0
        total = 0
        start, end = spans[0]
        for next_start, next_end in spans[1:]:
            if next_start <= end:
                end = max(end, next_end)
            else:
                total += end - start
                start, end = next_start, next_end
        total += end - start
        return total / 1_000_000_000

    def _ensure_open(self) -> None:
        if self._finished is not None:
            raise MeasurementError("wall clock has already been finished")


def _validate_name(name: str) -> None:
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", name):
        raise MeasurementError("phase name must be a lowercase identifier")


@dataclass(frozen=True)
class ProcessRssSample:
    observation: Observation
    pids: tuple[int, ...]
    process_starts: Mapping[int, str]


class ProcessRssSampler:
    """Sample maximum RSS observed across fixed explicit PIDs, not continuously."""

    def __init__(self, pids: Iterable[int], *, reader: Callable[[tuple[int, ...]], Mapping[int, tuple[int, str]]] | None = None):
        values_list: list[int] = []
        for pid in pids:
            if len(values_list) >= MAX_EXPLICIT_PIDS:
                raise MeasurementError("explicit process PID limit exceeded")
            values_list.append(pid)
        values = tuple(values_list)
        if not values or any(type(pid) is not int or pid <= 0 for pid in values):
            raise MeasurementError("provide a non-empty list of positive observed PIDs")
        if len(set(values)) != len(values):
            raise MeasurementError("process PID list contains duplicates")
        self.pids = tuple(sorted(values))
        self._reader = reader or _read_processes
        self._first_starts: dict[int, str] | None = None
        self._peak = 0
        self._samples = 0

    def sample(self) -> ProcessRssSample:
        if self._samples >= MAX_RSS_SAMPLES:
            now = _utc_now()
            observation = Observation(None, "unknown", _rss_source(), now, now,
                                      "RSS sample limit exceeded",
                                      {"pids": list(self.pids), "scope": "listed processes only"})
            return ProcessRssSample(observation, self.pids, {})
        self._samples += 1
        started = _utc_now()
        try:
            observed = self._reader(self.pids)
            if len(observed) > MAX_EXPLICIT_PIDS:
                raise MeasurementError("process reader exceeded the explicit PID limit")
            if set(observed) != set(self.pids):
                raise MeasurementError("one or more explicitly listed processes are absent")
            if any(type(rss) is not int or rss < 0 or not isinstance(identity, str) or not identity
                   for rss, identity in observed.values()):
                raise MeasurementError("process RSS observation is malformed")
            starts = {pid: identity for pid, (_, identity) in observed.items()}
            if self._first_starts is None:
                self._first_starts = starts
            elif starts != self._first_starts:
                raise MeasurementError("process identity changed between RSS samples")
            total = sum(rss for rss, _ in observed.values())
            self._peak = max(self._peak, total)
            result = Observation(self._peak, "observed", _rss_source(), started, _utc_now(),
                                 details={"pids": list(self.pids), "sampleBytes": total,
                                          "peakObservedBytes": self._peak,
                                          "scope": "listed processes only"})
            return ProcessRssSample(result, self.pids, starts)
        except (MeasurementError, OSError, subprocess.SubprocessError, ValueError) as exc:
            result = Observation(None, "unknown", _rss_source(), started, _utc_now(),
                                 str(exc) if isinstance(exc, MeasurementError) else type(exc).__name__,
                                 {"pids": list(self.pids),
                                                      "scope": "listed processes only"})
            return ProcessRssSample(result, self.pids, {})


def _rss_source() -> str:
    return "/proc/<pid>/statm" if Path("/proc/self/statm").exists() else "ps(1) explicit PID query"


def _file_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid)


def _directory_identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns,
            info.st_mode, info.st_uid)


def _read_processes(pids: tuple[int, ...]) -> Mapping[int, tuple[int, str]]:
    if Path("/proc/self/statm").exists():
        page_size = os.sysconf("SC_PAGE_SIZE")
        output: dict[int, tuple[int, str]] = {}
        for pid in pids:
            # Parse statm RSS plus stat starttime to detect PID reuse between samples.
            fields = Path(f"/proc/{pid}/statm").read_text(encoding="ascii").split()
            stat_text = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
            close = stat_text.rfind(")")
            if close < 0:
                raise MeasurementError("process stat record is malformed")
            tail = stat_text[close + 2:].split()
            if len(fields) < 2 or len(tail) <= 19:
                raise MeasurementError("process stat record is incomplete")
            output[pid] = (int(fields[1]) * page_size, tail[19])
        return output
    if os.name == "posix":
        completed = subprocess.run(["ps", "-o", "pid=", "-o", "rss=", "-o", "lstart=", "-p",
                                    ",".join(str(pid) for pid in pids)],
                                   check=True, capture_output=True, text=True, timeout=2)
        output = {}
        for line in completed.stdout.splitlines():
            fields = line.strip().split(None, 2)
            if len(fields) != 3:
                raise MeasurementError("ps returned an incomplete process record")
            pid, rss_kib = int(fields[0]), int(fields[1])
            output[pid] = (rss_kib * 1024, fields[2])
        return output
    raise MeasurementError("no supported process RSS source on this platform")


@dataclass(frozen=True)
class DiskFootprint:
    observation: Observation
    roots: tuple[str, ...]
    manifest_sha256: str | None


def measure_private_disk(roots: Iterable[str | os.PathLike[str]], *, uid: int | None = None) -> DiskFootprint:
    """Sum logical bytes under explicit private roots without following links.

    Every root must be owned by the current account and inaccessible to group or
    other users. Symlinks, special files, unreadable entries, or metadata drift
    make the whole observation unknown. This measures logical file lengths, not
    allocated blocks or unlisted filesystem/process data.
    """

    started = _utc_now()
    expected_uid = os.getuid() if uid is None and hasattr(os, "getuid") else uid
    try:
        requested_list: list[str | os.PathLike[str]] = []
        for root in roots:
            if len(requested_list) >= MAX_DISK_ROOTS:
                raise MeasurementError("private disk root limit exceeded")
            requested_list.append(root)
        requested_roots = tuple(requested_list)
        raw_roots = tuple(Path(root).expanduser().absolute() for root in requested_roots)
        if any(stat.S_ISLNK(root.lstat().st_mode) for root in raw_roots):
            raise MeasurementError("disk root must not be a symlink")
        canonical = tuple(sorted({root.resolve(strict=True) for root in raw_roots}))
        if not canonical:
            raise MeasurementError("at least one private root is required")
        if len(canonical) > MAX_DISK_ROOTS:
            raise MeasurementError("private disk root limit exceeded")
        if len(canonical) != len(requested_roots):
            raise MeasurementError("disk roots must be unique")
        for index, root in enumerate(canonical):
            if any(root == other or root in other.parents or other in root.parents
                   for other in canonical[index + 1:]):
                raise MeasurementError("disk roots must not overlap")
        manifest_records: list[dict[str, object]] = []
        files_to_recheck: list[tuple[Path, tuple[int, int, int, int, int, int, int]]] = []
        directories_to_recheck: list[tuple[Path, tuple[int, int, int, int, int, int], str, str]] = []
        total = 0
        directories_seen = 0
        files_seen = 0
        for root in canonical:
            pending = [root]
            discovered_directories = 1
            while pending:
                directory = pending.pop()
                directory_info = directory.lstat()
                if not stat.S_ISDIR(directory_info.st_mode):
                    raise MeasurementError("symlink or non-directory encountered in private root")
                if expected_uid is not None and directory_info.st_uid != expected_uid:
                    raise MeasurementError("directory in private root has a different owner")
                if stat.S_IMODE(directory_info.st_mode) & 0o077:
                    raise MeasurementError("directory in private root is not private")
                directory_identity = _directory_identity(directory_info)
                relative_directory = directory.relative_to(root).as_posix()
                directories_seen += 1
                if directories_seen > MAX_DISK_DIRECTORIES:
                    raise MeasurementError("private disk directory limit exceeded")
                directories_to_recheck.append((directory, directory_identity,
                                               str(root), relative_directory))
                manifest_records.append({"kind": "directory", "root": str(root),
                                         "path": relative_directory,
                                         "identity": directory_identity})
                # scandir yields one entry at a time; unlike os.walk, it does not
                # build an unbounded names list for a single wide directory.
                with os.scandir(directory) as iterator:
                    for entry in iterator:
                        path = Path(entry.path)
                        info = entry.stat(follow_symlinks=False)
                        if stat.S_ISDIR(info.st_mode):
                            if expected_uid is not None and info.st_uid != expected_uid:
                                raise MeasurementError("directory in private root has a different owner")
                            if stat.S_IMODE(info.st_mode) & 0o077:
                                raise MeasurementError("directory in private root is not private")
                            discovered_directories += 1
                            if discovered_directories > MAX_DISK_DIRECTORIES:
                                raise MeasurementError("private disk directory limit exceeded")
                            pending.append(path)
                        elif stat.S_ISREG(info.st_mode):
                            if expected_uid is not None and info.st_uid != expected_uid:
                                raise MeasurementError("file in private root has a different owner")
                            if stat.S_IMODE(info.st_mode) & 0o077:
                                raise MeasurementError("file in private root is not private")
                            files_seen += 1
                            if files_seen > MAX_DISK_FILES:
                                raise MeasurementError("private disk file limit exceeded")
                            identity = _file_identity(info)
                            relative = path.relative_to(root).as_posix()
                            files_to_recheck.append((path, identity))
                            manifest_records.append({"kind": "file", "root": str(root),
                                                     "path": relative, "identity": identity})
                            total += info.st_size
                        else:
                            raise MeasurementError("symlink or special file encountered in private root")

        # Final checks narrow the observation window; they do not make the walk
        # an atomic filesystem snapshot (semantics of ctime are platform-specific).
        for path, identity in files_to_recheck:
            final = path.lstat()
            if not stat.S_ISREG(final.st_mode) or _file_identity(final) != identity:
                raise MeasurementError("private file changed during disk measurement")
        for directory, identity, _root, _relative in directories_to_recheck:
            final = directory.lstat()
            if not stat.S_ISDIR(final.st_mode) or _directory_identity(final) != identity:
                raise MeasurementError("private directory changed during disk measurement")
        manifest = _digest(sorted(manifest_records, key=lambda item: (item["root"], item["path"], item["kind"])))
        result = Observation(total, "observed", "os.scandir+lstat logical file lengths",
                             started, _utc_now(), details={"roots": [str(root) for root in canonical],
                                                            "manifestSha256": manifest,
                                                            "unit": "logical bytes"})
        return DiskFootprint(result, tuple(str(root) for root in canonical), manifest)
    except (MeasurementError, OSError, RuntimeError) as exc:
        result = Observation(None, "unknown", "os.scandir+lstat logical file lengths",
                             started, _utc_now(), type(exc).__name__)
        return DiskFootprint(result, (), None)


def measured_costs(*, wall: Observation, rss: Observation, disk: Observation,
                   source_ref: str) -> MeasuredCosts:
    """Adapt local observations to the capture cost contract; external costs stay unknown."""

    if not isinstance(source_ref, str) or not source_ref.strip():
        raise MeasurementError("source_ref is required")
    timestamps: list[datetime] = []
    for name, observation in (("wall", wall), ("RSS", rss), ("disk", disk)):
        if not isinstance(observation, Observation):
            raise MeasurementError(f"{name} must be an Observation")
        if not isinstance(observation.source, str) or not observation.source.strip():
            raise MeasurementError(f"{name} source is required")
        parsed_times: list[datetime] = []
        for timestamp_name, timestamp in (("started_at", observation.started_at),
                                          ("observed_at", observation.observed_at)):
            try:
                parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError) as exc:
                raise MeasurementError(f"{name} {timestamp_name} must be an ISO timestamp") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise MeasurementError(f"{name} {timestamp_name} must include a timezone")
            parsed_times.append(parsed.astimezone(timezone.utc))
        if parsed_times[1] < parsed_times[0]:
            raise MeasurementError(f"{name} observed_at precedes started_at")
        timestamps.extend(parsed_times)
        if observation.status not in {"observed", "unknown"}:
            raise MeasurementError(f"{name} status is invalid")
        if observation.status == "observed" and observation.value is None:
            raise MeasurementError(f"observed {name} value cannot be null")
        if observation.status == "unknown" and observation.value is not None:
            raise MeasurementError(f"unknown {name} value must be null")
        if observation.status == "unknown" and (not isinstance(observation.reason, str) or not observation.reason):
            raise MeasurementError(f"unknown {name} observation needs a bounded reason")
        if observation.value is not None and (type(observation.value) not in {int, float}
                                               or not math.isfinite(observation.value)
                                               or observation.value < 0):
            raise MeasurementError(f"{name} value must be finite and nonnegative")
    values = {
        "eur": None,
        "tokens": None,
        "input_tokens": None,
        "output_tokens": None,
        "retry_tokens": None,
        "wall_seconds": wall.value,
        "rss_bytes": rss.value,
        "disk_bytes": disk.value,
    }
    for label, observation in (("RSS", rss), ("disk", disk)):
        if observation.value is not None and (type(observation.value) is not int or observation.value < 0):
            raise MeasurementError(f"{label} must be a nonnegative integer byte count")
    record = {"sourceRef": source_ref, "wall": wall.as_dict(), "rss": rss.as_dict(),
              "disk": disk.as_dict(), "costs": values}
    observed_at = max(timestamps).isoformat(timespec="microseconds").replace("+00:00", "Z")
    return MeasuredCosts(values=values, source_ref=source_ref,
                         source_sha256=_digest(record), observed_at=observed_at)


__all__ = [
    "DiskFootprint", "MeasurementError", "Observation", "PhaseInterval",
    "ProcessRssSample", "ProcessRssSampler", "WallClock", "measured_costs",
    "measure_private_disk",
]
