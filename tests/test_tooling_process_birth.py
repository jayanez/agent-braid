# SPDX-License-Identifier: AGPL-3.0-only
"""Native process birth observations against only test-owned processes."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_process_birth as birth


class ProcessBirthTests(unittest.TestCase):
    def test_darwin_rusage_v0_layout_matches_public_sdk_header(self):
        self.assertEqual(birth.ctypes.sizeof(birth._RusageInfoV0), 96)
        offsets = {name: getattr(birth._RusageInfoV0, name).offset
                   for name, _kind in birth._RusageInfoV0._fields_}
        self.assertEqual(offsets["ri_resident_size"], 64)
        self.assertEqual(offsets["ri_proc_start_abstime"], 80)

    def test_linux_stat_parser_handles_parentheses_and_rejects_truncation(self):
        fields = ["S"] + ["0"] * 18 + ["123456", "0", "7"]
        raw = f"42 (test ) comm) {' '.join(fields)}\n".encode("ascii")
        self.assertEqual(birth._linux_parse_stat(raw), (123456, 7, "S"))
        with self.assertRaisesRegex(birth.ProcessBirthError, "malformed"):
            birth._linux_parse_stat(b"42 (broken) S 1 2\n")

    def test_owned_live_process_birth_and_sample_match_without_signalling(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        identity = None
        try:
            try:
                identity = birth.capture_process_birth(process.pid)
            except birth.ProcessBirthError as exc:
                self.skipTest(f"native process birth source unavailable: {exc}")
            sample = birth.sample_process_birth(identity)
            self.assertTrue(birth.matches_process_birth(identity, sample))
            self.assertEqual(sample.pid, process.pid)
            self.assertGreater(sample.resident_size_bytes, 0)
            self.assertIsNone(process.poll(), "birth source must not signal or reap its subject")
            reused = birth.ProcessBirthSample(
                sample.pid, sample.platform, sample.source, sample.token + ":changed",
                sample.resident_size_bytes,
            )
            self.assertFalse(birth.matches_process_birth(identity, reused))
            process.terminate()
            process.wait(timeout=3)
            with self.assertRaisesRegex(birth.ProcessBirthError, "exited|failed"):
                birth.sample_process_birth(identity)
        finally:
            birth.close_process_birth(identity)
            if process.poll() is None:
                process.terminate()  # Only the test-created process PID.
                process.wait(timeout=3)

    def test_unavailable_or_invalid_native_source_fails_explicitly(self):
        with self.assertRaisesRegex(birth.ProcessBirthError, "signed 32-bit"):
            birth.capture_process_birth(0)
        with patch.object(birth, "_darwin_read") as native:
            with patch.object(birth.sys, "platform", "darwin"):
                with self.assertRaisesRegex(birth.ProcessBirthError, "signed 32-bit"):
                    birth.capture_process_birth((1 << 32) + os.getpid())
            native.assert_not_called()
        with patch.object(birth.sys, "platform", "freebsd"):
            with self.assertRaisesRegex(birth.ProcessBirthError, "unsupported"):
                birth.capture_process_birth(12345)

    def test_malformed_sample_borrows_handles_and_duplicate_owner_close_is_safe(self):
        pidfd, pidfd_peer = os.pipe()
        procfd, procfd_peer = os.pipe()
        lease = birth._HandleLease(pidfd, procfd)
        identity = birth.ProcessBirthIdentity(
            42, "linux", "pidfd + /proc/<pid>/stat + boot_id", "boot:1", 1,
            "2026-01-01T00:00:00Z", pidfd, procfd, lease,
        )
        malformed = birth.ProcessBirthSample(42, "linux", "wrong-source", "boot:1", 2,
                                             "2026-01-01T00:00:01Z")
        replacement = None
        try:
            with patch.object(birth, "_linux_read_pinned", return_value=malformed):
                with self.assertRaisesRegex(birth.ProcessBirthError, "malformed"):
                    birth.sample_process_birth(identity)
            # Sampling borrows descriptors; only the supervisor owns cleanup.
            for descriptor in (pidfd, procfd):
                os.fstat(descriptor)
            birth.close_process_birth(identity)
            for descriptor in (pidfd, procfd):
                with self.assertRaises(OSError):
                    os.fstat(descriptor)
            replacement = os.open(os.devnull, os.O_RDONLY)
            birth.close_process_birth(identity)
            os.fstat(replacement)
            with self.assertRaisesRegex(birth.ProcessBirthError, "handles are closed"):
                birth.sample_process_birth(identity)
        finally:
            birth.close_process_birth(identity)
            if replacement is not None:
                os.close(replacement)
            os.close(pidfd_peer)
            os.close(procfd_peer)

    def test_owner_close_never_waits_for_blocked_borrow_and_defers_descriptor_close(self):
        pidfd, pidfd_peer = os.pipe()
        procfd, procfd_peer = os.pipe()
        lease = birth._HandleLease(pidfd, procfd)
        entered = threading.Event()
        release = threading.Event()
        close_done = threading.Event()
        worker_errors = []

        def borrower():
            try:
                with lease.borrow():
                    entered.set()
                    if not release.wait(3):
                        raise AssertionError("test borrower was not released")
            except BaseException as exc:
                worker_errors.append(exc)

        def owner_close():
            lease.close()
            close_done.set()

        borrower_thread = threading.Thread(target=borrower, daemon=True)
        closer_thread = threading.Thread(target=owner_close, daemon=True)
        borrower_thread.start()
        try:
            self.assertTrue(entered.wait(2), "borrow did not begin")
            closer_thread.start()
            self.assertTrue(close_done.wait(0.5), "owner close waited for native sampling")
            for descriptor in (pidfd, procfd):
                os.fstat(descriptor)
            with self.assertRaisesRegex(birth.ProcessBirthError, "handles are closed"):
                with lease.borrow():
                    self.fail("close must reject new borrows immediately")
        finally:
            release.set()
            borrower_thread.join(timeout=3)
            if closer_thread.ident is not None:
                closer_thread.join(timeout=3)
            lease.close()
            os.close(pidfd_peer)
            os.close(procfd_peer)
        self.assertFalse(borrower_thread.is_alive())
        self.assertFalse(closer_thread.is_alive())
        self.assertEqual(worker_errors, [])
        for descriptor in (pidfd, procfd):
            with self.assertRaises(OSError):
                os.fstat(descriptor)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux native handle cleanup")
    def test_failed_birth_capture_closes_every_descriptor_before_returning(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        opened = []
        real_open = os.open
        real_pidfd_open = getattr(os, "pidfd_open", None)

        def capture_open(path, *args, **kwargs):
            descriptor = real_open(path, *args, **kwargs)
            if path == f"/proc/{process.pid}":
                opened.append(descriptor)
            return descriptor

        def capture_pidfd(pid, flags):
            descriptor = real_pidfd_open(pid, flags)
            opened.append(descriptor)
            return descriptor

        try:
            with patch.object(birth, "_linux_read_pinned",
                              side_effect=birth.ProcessBirthError("synthetic native failure")):
                with patch.object(birth.os, "open", side_effect=capture_open):
                    if real_pidfd_open is None:
                        with self.assertRaisesRegex(birth.ProcessBirthError, "synthetic native"):
                            birth.capture_process_birth(process.pid)
                    else:
                        with patch.object(birth.os, "pidfd_open", side_effect=capture_pidfd):
                            with self.assertRaisesRegex(birth.ProcessBirthError, "synthetic native"):
                                birth.capture_process_birth(process.pid)
            self.assertGreaterEqual(len(opened), 1)
            for descriptor in opened:
                with self.assertRaises(OSError):
                    os.fstat(descriptor)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux pidfd backend test")
    def test_linux_captured_process_binding_and_proc_directory_are_closed(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        identity = None
        try:
            try:
                identity = birth.capture_process_birth(process.pid)
            except birth.ProcessBirthError as exc:
                self.skipTest(f"pidfd unavailable in runtime: {exc}")
            self.assertIn(identity.source, {
                "pidfd + /proc/<pid>/stat + boot_id",
                "pinned /proc directory fd + stat + boot_id",
            })
            self.assertEqual(identity.pidfd is None,
                             identity.source.startswith("pinned /proc directory"))
            self.assertIsNotNone(identity.proc_directory_fd)
            sample = birth.sample_process_birth(identity)
            self.assertTrue(birth.matches_process_birth(identity, sample))
        finally:
            birth.close_process_birth(identity)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux pinned procfd fallback")
    def test_enosys_pidfd_uses_pinned_proc_directory_and_never_reopens_pid_path(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        identity = None
        real_open = os.open
        try:
            with patch.object(birth.os, "pidfd_open", side_effect=OSError(birth.errno.ENOSYS, "unsupported")):
                identity = birth.capture_process_birth(process.pid)
            self.assertIsNone(identity.pidfd)
            self.assertEqual(identity.source, "pinned /proc directory fd + stat + boot_id")

            def deny_numeric_proc_reopen(path, *args, **kwargs):
                if isinstance(path, str) and path == f"/proc/{process.pid}":
                    raise AssertionError("sampling must use the pinned proc directory fd")
                return real_open(path, *args, **kwargs)

            with patch.object(birth.os, "open", side_effect=deny_numeric_proc_reopen):
                sample = birth.sample_process_birth(identity)
            self.assertTrue(birth.matches_process_birth(identity, sample))
            self.assertGreater(sample.resident_size_bytes, 0)
            process.terminate()
            process.wait(timeout=3)
            with self.assertRaises(birth.ProcessBirthError):
                birth.sample_process_birth(identity)
        finally:
            birth.close_process_birth(identity)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)

    @unittest.skipUnless(sys.platform.startswith("linux"), "Linux procfs backend test")
    def test_linux_procfs_birth_and_resident_pages_reader(self):
        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(10)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        read_fd, write_fd = os.pipe()
        proc_fd = None
        try:
            proc_fd = os.open(f"/proc/{process.pid}", os.O_RDONLY | os.O_DIRECTORY)
            sample = birth._linux_read_pinned(process.pid, read_fd, proc_fd)
            self.assertEqual(sample.pid, process.pid)
            self.assertEqual(sample.platform, "linux")
            self.assertIn("boot_id", sample.source)
            self.assertGreater(sample.resident_size_bytes, 0)
        finally:
            os.close(read_fd)
            os.close(write_fd)
            if proc_fd is not None:
                os.close(proc_fd)
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)


if __name__ == "__main__":
    unittest.main()
