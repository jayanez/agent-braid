# SPDX-License-Identifier: AGPL-3.0-only
"""Native process birth binding and resident-size samples.

The supported backends are Darwin libproc and Linux pidfd or pinned procfs.
Unsupported platforms and unavailable kernel observations fail explicitly.
"""
from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass, field
from datetime import datetime, timezone
import errno
import os
import select
import sys
import threading
from contextlib import contextmanager
from typing import Iterator

MAX_PID = (1 << 31) - 1
MAX_NATIVE_SOURCE_CHARS = 128
MAX_BIRTH_TOKEN_CHARS = 256
MAX_TIMESTAMP_CHARS = 64


class ProcessBirthError(RuntimeError):
    """The native process identity or resource sample is unavailable."""


class _HandleLease:
    """Single owner for Linux descriptors, safe against duplicate close calls."""

    def __init__(self, pidfd: int | None, proc_directory_fd: int):
        self.pidfd = pidfd
        self.proc_directory_fd = proc_directory_fd
        self._lock = threading.Lock()
        self._close_requested = False
        self._active_borrows = 0
        self._descriptors_closed = False

    @contextmanager
    def borrow(self) -> Iterator[tuple[int | None, int]]:
        with self._lock:
            if self._close_requested:
                raise ProcessBirthError("Linux process birth handles are closed")
            self._active_borrows += 1
        try:
            yield self.pidfd, self.proc_directory_fd
        finally:
            descriptors = None
            with self._lock:
                self._active_borrows -= 1
                if self._close_requested and self._active_borrows == 0 \
                        and not self._descriptors_closed:
                    self._descriptors_closed = True
                    descriptors = (self.pidfd, self.proc_directory_fd)
            if descriptors is not None:
                _close_descriptors(*descriptors)

    def close(self) -> None:
        descriptors = None
        with self._lock:
            if self._close_requested:
                return
            self._close_requested = True
            if self._active_borrows == 0 and not self._descriptors_closed:
                self._descriptors_closed = True
                descriptors = (self.pidfd, self.proc_directory_fd)
        if descriptors is not None:
            _close_descriptors(*descriptors)


@dataclass(frozen=True)
class ProcessBirthIdentity:
    """Kernel-reported process-start binding captured immediately after launch."""

    pid: int
    platform: str
    source: str
    token: str
    resident_size_bytes: int
    observed_at: str = ""
    pidfd: int | None = field(default=None, repr=False, compare=False)
    proc_directory_fd: int | None = field(default=None, repr=False, compare=False)
    _handle_lease: _HandleLease | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class ProcessBirthSample:
    """One native sample containing process-start binding and resident size."""

    pid: int
    platform: str
    source: str
    token: str
    resident_size_bytes: int
    observed_at: str = ""


class _RusageInfoV0(ctypes.Structure):
    # Mirrors Apple's public sys/resource.h rusage_info_v0 declaration.
    _fields_ = [("ri_uuid", ctypes.c_uint8 * 16)] + [
        (name, ctypes.c_uint64)
        for name in (
            "ri_user_time", "ri_system_time", "ri_pkg_idle_wkups",
            "ri_interrupt_wkups", "ri_pageins", "ri_wired_size",
            "ri_resident_size", "ri_phys_footprint",
            "ri_proc_start_abstime", "ri_proc_exit_abstime",
        )
    ]


def _darwin_read(pid: int) -> ProcessBirthSample:
    """Read RUSAGE_INFO_V0 with the exact public Darwin struct layout."""
    library = ctypes.util.find_library("proc") or "/usr/lib/libproc.dylib"
    try:
        libproc = ctypes.CDLL(library, use_errno=True)
        function = libproc.proc_pid_rusage
    except (OSError, AttributeError) as exc:
        raise ProcessBirthError("Darwin libproc proc_pid_rusage is unavailable") from exc
    function.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
    function.restype = ctypes.c_int
    usage = _RusageInfoV0()
    result = function(pid, 0, ctypes.cast(ctypes.byref(usage), ctypes.POINTER(ctypes.c_void_p)))
    if result != 0:
        error = ctypes.get_errno()
        raise ProcessBirthError(f"proc_pid_rusage failed with errno {error}")
    if usage.ri_proc_start_abstime <= 0:
        raise ProcessBirthError("kernel process start identity is missing")
    if usage.ri_proc_exit_abstime != 0:
        raise ProcessBirthError("owned process has exited")
    # Apple documents this field as the process resident size; XNU populates it
    # from the task physical-memory ledger. Keep the kernel field in bytes.
    return ProcessBirthSample(
        pid=pid,
        platform="darwin",
        source="libproc.proc_pid_rusage:RUSAGE_INFO_V0",
        token=f"{bytes(usage.ri_uuid).hex()}:{usage.ri_proc_start_abstime}",
        resident_size_bytes=int(usage.ri_resident_size),
        observed_at=_utc_now(),
    )


def capture_process_birth(pid: int) -> ProcessBirthIdentity:
    """Capture a process birth token and resident size immediately after Popen."""
    _validate_pid(pid)
    pidfd = proc_directory_fd = None
    try:
        if sys.platform == "darwin":
            sample = _darwin_read(pid)
        elif sys.platform.startswith("linux"):
            if hasattr(os, "pidfd_open"):
                try:
                    pidfd = os.pidfd_open(pid, 0)
                except OSError as exc:
                    if exc.errno != errno.ENOSYS:
                        raise ProcessBirthError(f"Linux pidfd_open failed: {exc.errno}") from exc
            proc_directory_fd = os.open(f"/proc/{pid}", os.O_RDONLY | os.O_DIRECTORY)
            sample = _linux_read_pinned(pid, pidfd, proc_directory_fd)
        else:
            raise ProcessBirthError(f"native process birth/RSS source unsupported on {sys.platform}")
        _validate_sample(sample, pid)
    except OSError as exc:
        _close_descriptors(pidfd, proc_directory_fd)
        raise ProcessBirthError(f"native process birth capture failed: {exc.errno}") from exc
    except BaseException:
        _close_descriptors(pidfd, proc_directory_fd)
        raise
    return ProcessBirthIdentity(
        pid=sample.pid, platform=sample.platform, source=sample.source,
        token=sample.token, resident_size_bytes=sample.resident_size_bytes,
        observed_at=sample.observed_at,
        pidfd=pidfd, proc_directory_fd=proc_directory_fd,
        _handle_lease=(_HandleLease(pidfd, proc_directory_fd)
                       if sample.platform == "linux" and proc_directory_fd is not None else None),
    )


def sample_process_birth(identity: ProcessBirthIdentity) -> ProcessBirthSample:
    """Read a new native sample through the captured process binding."""
    validate_process_birth_identity(identity)
    if identity.platform == "darwin":
        sample = _darwin_read(identity.pid)
    elif identity.platform == "linux":
        if identity._handle_lease is None:
            raise ProcessBirthError("Linux process birth handles are unavailable")
        with identity._handle_lease.borrow() as (pidfd, proc_directory_fd):
            sample = _linux_read_pinned(identity.pid, pidfd, proc_directory_fd)
    else:
        raise ProcessBirthError("process birth source platform is unsupported")
    _validate_sample(sample, identity.pid)
    return sample


def close_process_birth(identity: ProcessBirthIdentity | None) -> None:
    """Close Linux identity handles after the registered supervisor finishes."""
    if type(identity) is ProcessBirthIdentity:
        if type(identity._handle_lease) is _HandleLease:
            identity._handle_lease.close()


def _close_descriptors(*descriptors: int | None) -> None:
    for descriptor in descriptors:
        if type(descriptor) is not int or descriptor < 0:
            continue
        try:
            os.close(descriptor)
        except OSError:
            pass


def _validate_sample(sample: ProcessBirthSample, pid: int) -> None:
    linux_sources = {"pidfd + /proc/<pid>/stat + boot_id",
                     "pinned /proc directory fd + stat + boot_id"}
    if type(sample) is not ProcessBirthSample:
        raise ProcessBirthError("native process sample is malformed")
    if (type(sample.pid) is not int or sample.pid != pid
            or not isinstance(sample.platform, str)
            or sample.platform not in {"darwin", "linux"}
            or not isinstance(sample.source, str)
            or (sample.source != "libproc.proc_pid_rusage:RUSAGE_INFO_V0" if sample.platform == "darwin"
                else sample.source not in linux_sources)
            or not isinstance(sample.token, str) or not sample.token
            or len(sample.token) > MAX_BIRTH_TOKEN_CHARS or not sample.token.isascii()
            or len(sample.source) > MAX_NATIVE_SOURCE_CHARS or not sample.source.isascii()
            or type(sample.resident_size_bytes) is not int
            or sample.resident_size_bytes < 0 or sample.resident_size_bytes > ((1 << 63) - 1)
            or not isinstance(sample.observed_at, str) or not sample.observed_at
            or len(sample.observed_at) > MAX_TIMESTAMP_CHARS):
        raise ProcessBirthError("native process sample is malformed")
    _validate_timestamp(sample.observed_at)


def validate_process_birth_identity(identity: ProcessBirthIdentity) -> None:
    if type(identity) is not ProcessBirthIdentity:
        raise ProcessBirthError("process birth identity is malformed")
    _validate_pid(identity.pid)
    if not isinstance(identity.platform, str) or not isinstance(identity.source, str):
        raise ProcessBirthError("process birth identity is malformed")
    linux_sources = {"pidfd + /proc/<pid>/stat + boot_id",
                     "pinned /proc directory fd + stat + boot_id"}
    source_valid = (identity.platform == "darwin"
                    and identity.source == "libproc.proc_pid_rusage:RUSAGE_INFO_V0") or (
                    identity.platform == "linux" and identity.source in linux_sources)
    if (not source_valid or not isinstance(identity.source, str)
            or len(identity.source) > MAX_NATIVE_SOURCE_CHARS
            or not identity.source.isascii()
            or not isinstance(identity.token, str)
            or not identity.token or not identity.token.isascii()
            or len(identity.token) > MAX_BIRTH_TOKEN_CHARS
            or type(identity.resident_size_bytes) is not int
            or identity.resident_size_bytes < 0 or identity.resident_size_bytes > ((1 << 63) - 1)):
        raise ProcessBirthError("process birth identity is malformed")
    if identity.platform == "linux" and (type(identity.proc_directory_fd) is not int
                                           or identity.proc_directory_fd < 0):
        raise ProcessBirthError("Linux process birth handles are unavailable")
    if identity.platform == "linux" and type(identity._handle_lease) is not _HandleLease:
        raise ProcessBirthError("Linux process birth handle lease is unavailable")
    if identity.platform == "linux" and (
            identity._handle_lease.pidfd != identity.pidfd
            or identity._handle_lease.proc_directory_fd != identity.proc_directory_fd):
        raise ProcessBirthError("Linux process birth handles differ from their lease")
    if identity.platform == "linux" and identity.pidfd is not None \
            and (type(identity.pidfd) is not int or identity.pidfd < 0):
        raise ProcessBirthError("Linux pidfd is malformed")
    if identity.platform == "darwin" and (identity.pidfd is not None
                                            or identity.proc_directory_fd is not None):
        raise ProcessBirthError("Darwin process birth identity contains foreign handles")
    if identity.platform == "linux" and identity.pidfd is None \
            and identity.source != "pinned /proc directory fd + stat + boot_id":
        raise ProcessBirthError("Linux source does not match open process handles")
    if identity.platform == "linux" and identity.pidfd is not None \
            and identity.source != "pidfd + /proc/<pid>/stat + boot_id":
        raise ProcessBirthError("Linux source does not match open process handles")
    if not isinstance(identity.observed_at, str) or not identity.observed_at \
            or len(identity.observed_at) > MAX_TIMESTAMP_CHARS:
        raise ProcessBirthError("process birth observation timestamp is missing or oversized")
    _validate_timestamp(identity.observed_at)


def _validate_timestamp(value: str) -> None:
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProcessBirthError("process observation timestamp is malformed") from exc
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ProcessBirthError("process observation timestamp must include timezone")


def _validate_pid(pid: int) -> None:
    if type(pid) is not int or pid <= 0 or pid > MAX_PID:
        raise ProcessBirthError("PID must be a positive signed 32-bit integer")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _read_proc_file(directory_fd: int, name: str, limit: int = 64 * 1024) -> bytes:
    descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=directory_fd)
    try:
        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(descriptor, min(4096, limit + 1 - len(data)))
            if not chunk:
                return bytes(data)
            data.extend(chunk)
        raise ProcessBirthError("Linux proc metadata byte limit exceeded")
    finally:
        os.close(descriptor)


def _linux_parse_stat(raw: bytes, expected_pid: int | None = None) -> tuple[int, int, str]:
    try:
        text = raw.decode("ascii")
        pid_text = text.split(" ", 1)[0]
        parsed_pid = int(pid_text)
        closing = text.rfind(")")
        if closing < 0:
            raise ValueError
        fields = text[closing + 1:].strip().split()
        # Tail begins at field 3 (state); starttime is field 22, RSS field 24.
        state = fields[0]
        start_ticks = int(fields[19])
        resident_pages = int(fields[21])
    except (UnicodeDecodeError, ValueError, IndexError) as exc:
        raise ProcessBirthError("Linux proc stat metadata is malformed") from exc
    if parsed_pid <= 0 or (expected_pid is not None and parsed_pid != expected_pid):
        raise ProcessBirthError("Linux proc stat PID differs from the pinned process")
    if start_ticks <= 0 or resident_pages < 0:
        raise ProcessBirthError("Linux proc stat metadata is out of range")
    if state in {"Z", "X", "x"}:
        raise ProcessBirthError("Linux owned process has exited")
    return start_ticks, resident_pages, state


def _linux_read_pinned(pid: int, pidfd: int | None, proc_directory_fd: int) -> ProcessBirthSample:
    try:
        return _linux_read_pinned_impl(pid, pidfd, proc_directory_fd)
    except OSError as exc:
        raise ProcessBirthError(f"Linux pinned process observation failed: {exc.errno}") from exc


def _linux_read_pinned_impl(pid: int, pidfd: int | None, proc_directory_fd: int) -> ProcessBirthSample:
    poller = select.poll()
    if pidfd is not None:
        poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
        if poller.poll(0):
            raise ProcessBirthError("Linux owned process has exited")
    start_ticks, resident_pages, _state = _linux_parse_stat(
        _read_proc_file(proc_directory_fd, "stat"), expected_pid=pid)
    page_size = os.sysconf("SC_PAGE_SIZE")
    if type(page_size) is not int or page_size <= 0 or resident_pages > ((1 << 63) - 1) // page_size:
        raise ProcessBirthError("Linux resident byte count is out of range")
    boot_descriptor = os.open("/proc/sys/kernel/random/boot_id", os.O_RDONLY)
    try:
        boot_id = os.read(boot_descriptor, 128).decode("ascii").strip()
    finally:
        os.close(boot_descriptor)
    if not boot_id or len(boot_id) > 64:
        raise ProcessBirthError("Linux boot identity is malformed")
    if pidfd is not None and poller.poll(0):
        raise ProcessBirthError("Linux owned process exited during resource sampling")
    if pidfd is None:
        final_ticks, final_pages, _final_state = _linux_parse_stat(
            _read_proc_file(proc_directory_fd, "stat"), expected_pid=pid)
        if final_ticks != start_ticks:
            raise ProcessBirthError("Linux pinned proc birth identity changed")
        resident_pages = final_pages
    source = ("pidfd + /proc/<pid>/stat + boot_id" if pidfd is not None
              else "pinned /proc directory fd + stat + boot_id")
    return ProcessBirthSample(
        pid, "linux", source,
        f"{boot_id}:{start_ticks}", resident_pages * page_size,
        _utc_now(),
    )


def matches_process_birth(identity: ProcessBirthIdentity, sample: ProcessBirthSample) -> bool:
    """Compare the same kernel-observed process token across two observations."""
    return (type(identity) is ProcessBirthIdentity and type(sample) is ProcessBirthSample
            and identity.pid == sample.pid and identity.platform == sample.platform
            and identity.source == sample.source and identity.token == sample.token)


__all__ = [
    "ProcessBirthError", "ProcessBirthIdentity", "ProcessBirthSample",
    "capture_process_birth", "close_process_birth", "matches_process_birth",
    "sample_process_birth", "validate_process_birth_identity",
]
