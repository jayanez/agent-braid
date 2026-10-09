# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded local resource-source controls use only owned synthetic paths/processes."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_braid.tooling_supervisor import Clock, ProcessIdentity
from agent_braid import tooling_resources as resources
from agent_braid.tooling_process_birth import (
    ProcessBirthError, ProcessBirthIdentity, ProcessBirthSample,
    capture_process_birth, close_process_birth,
)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class FakeClock:
    def __init__(self, values: list[float] | None = None):
        self.values = values or [100.0]
        self.index = 0
        self.fixed_utc = iso_now()

    def monotonic(self) -> float:
        if self.index < len(self.values):
            value = self.values[self.index]
            self.index += 1
            return value
        value = self.values[-1] + 0.25
        self.values.append(value)
        self.index += 1
        return value

    def utc(self) -> str:
        return self.fixed_utc

    def as_clock(self) -> Clock:
        return Clock(monotonic=self.monotonic, utc_now=self.utc)


class ResourceFixture(unittest.TestCase):
    def setUp(self):
        safe_tmp = Path("/private/tmp") if Path("/private/tmp").is_dir() else Path(tempfile.gettempdir())
        self.temporary = tempfile.TemporaryDirectory(prefix="m45-local-resources-", dir=safe_tmp)
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.registration = "a" * 64
        self.cohort = self.base / "caller-bound-cohort"
        self.cohort.mkdir(mode=0o700)
        self.results_parent = self.cohort
        self.results = self.cohort / f"{self.registration}-test-activity-01"
        self.results.mkdir(mode=0o700)
        self.source = self.base / "source"
        self.grants = self.base / "grants"
        self.source.mkdir(mode=0o700)
        self.grants.mkdir(mode=0o700)

    def collector(self, *, clock: Clock | None = None, source_roots=None, grant_roots=None,
                  results_root: Path | None = None) -> resources.LocalResourceCollector:
        return resources.LocalResourceCollector(
            activity_ref="test-activity-01", registration_sha256=self.registration,
            results_root=results_root or self.results,
            source_roots=source_roots if source_roots is not None else (self.source,),
            grant_roots=grant_roots if grant_roots is not None else (self.grants,),
            clock=clock or Clock(),
        )

    @staticmethod
    def identity(pid=424242, *, started_at=None, pgid=None, birth=True) -> ProcessIdentity:
        process_birth = (ProcessBirthIdentity(
            pid, "darwin", "libproc.proc_pid_rusage:RUSAGE_INFO_V0", "birth-token", 0, iso_now())
                         if birth else None)
        return ProcessIdentity(pid, pid if pgid is None else pgid,
                                started_at or iso_now(), "b" * 64, process_birth)

    def test_prestart_identity_is_unknown_then_owned_synthetic_process_is_sampled(self):
        collector = self.collector()
        before = collector.sample(None)
        self.assertEqual(before.rss.status, "unknown")
        self.assertIsNone(before.rss.value)
        self.assertIn("does not establish zero RSS", before.rss.reason)

        process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        birth = None
        try:
            try:
                birth = capture_process_birth(process.pid)
            except ProcessBirthError as exc:
                self.skipTest(f"native process birth source unavailable: {exc}")
            identity = ProcessIdentity(process.pid, process.pid, iso_now(), "b" * 64, birth)
            after = collector.sample(identity)
            self.assertEqual(after.rss.status, "observed")
            self.assertGreater(after.rss.value, 0)
            self.assertIn("birth-bound", after.rss.source)
            self.assertGreaterEqual(after.wall.value, before.wall.value)
            self.assertEqual(after.identity_fingerprint, resources._identity_fingerprint(identity))
            self.assertTrue(verify_source_integrity(after))
            self.assertIsNone(process.poll(), "collector must not signal the owned synthetic process")
        finally:
            close_process_birth(birth)
            if process.poll() is None:
                process.terminate()  # Only this test-owned PID, never its process group.
                process.wait(timeout=3)

    def test_fixed_cohort_root_scan_is_private_hashed_and_non_mutating(self):
        payload = self.results / "attempt.json"
        payload.write_bytes(b"owned synthetic result")
        payload.chmod(0o600)
        before = set(self.results.iterdir())
        report = self.collector().sample(None)
        self.assertEqual(report.disk.status, "observed")
        self.assertEqual(report.disk.value, len(b"owned synthetic result"))
        self.assertTrue(report.disk.source_sha256)
        self.assertEqual(set(self.results.iterdir()), before)
        self.assertTrue(verify_source_integrity(report))
        self.assertFalse(report.authenticity_verified)
        self.assertFalse(report.complete_telemetry_snapshot)
        self.assertFalse(report.disk.usable_for_caps)

        tampered = resources.replace(report, observed_at=iso_now())
        self.assertFalse(verify_source_integrity(tampered))

    def test_private_results_walk_rejects_symlinks_specials_and_overlaps(self):
        target = self.source / "source.txt"
        target.write_text("source", encoding="ascii")
        target.chmod(0o600)
        link = self.results / "linked-source"
        link.symlink_to(target)
        report = self.collector().sample(None)
        self.assertEqual(report.disk.status, "unknown")
        self.assertIn("symlink or special", report.disk.reason)
        link.unlink()

        overlapping = self.collector(source_roots=(self.results_parent,)).sample(None)
        self.assertEqual(overlapping.disk.status, "unknown")
        self.assertIn("overlaps", overlapping.disk.reason)

    def test_disk_entry_count_and_depth_bounds_fail_closed(self):
        for index in range(2):
            item = self.results / f"file-{index}"
            item.write_bytes(b"x")
            item.chmod(0o600)
        with patch.object(resources, "MAX_DISK_FILES", 1):
            report = self.collector().sample(None)
        self.assertEqual(report.disk.status, "unknown")
        self.assertIn("file limit", report.disk.reason)

        for item in self.results.iterdir():
            item.unlink()
        nested = self.results / "one" / "two"
        nested.mkdir(mode=0o700, parents=True)
        (self.results / "one").chmod(0o700)
        nested.chmod(0o700)
        with patch.object(resources, "MAX_DISK_DEPTH", 1):
            report = self.collector().sample(None)
        self.assertEqual(report.disk.status, "unknown")
        self.assertIn("depth limit", report.disk.reason)

    def test_missing_malformed_and_reused_kernel_birth_bindings_remain_unknown(self):
        identity = self.identity(birth=False)
        missing = self.collector().sample(identity)
        self.assertEqual(missing.rss.status, "unknown")
        self.assertIn("could not capture kernel", missing.rss.reason)

        identity = self.identity()
        malformed = self.collector()
        with patch.object(resources, "sample_process_birth", side_effect=ProcessBirthError("malformed kernel data")):
            report = malformed.sample(identity)
        self.assertEqual(report.rss.status, "partial")
        self.assertEqual(report.rss.value, identity.birth.resident_size_bytes)
        self.assertIn("malformed kernel data", report.rss.reason)

        reused = self.collector()
        other = ProcessBirthSample(identity.pid, "darwin", "libproc.proc_pid_rusage:RUSAGE_INFO_V0",
                                   "different-token", 999, iso_now())
        with patch.object(resources, "sample_process_birth", return_value=other):
            report = reused.sample(identity)
        self.assertEqual(report.rss.status, "partial")
        self.assertEqual(report.rss.value, identity.birth.resident_size_bytes)
        self.assertIn("possible PID reuse", report.rss.reason)

    def test_kernel_resident_sample_is_bound_to_identity_and_peak_is_monotonic(self):
        identity = self.identity()
        collector = self.collector()
        rows = [
            ProcessBirthSample(identity.pid, "darwin", "libproc.proc_pid_rusage:RUSAGE_INFO_V0",
                               "birth-token", 120, iso_now()),
            ProcessBirthSample(identity.pid, "darwin", "libproc.proc_pid_rusage:RUSAGE_INFO_V0",
                               "birth-token", 45, iso_now()),
        ]
        with patch.object(resources, "sample_process_birth", side_effect=rows):
            first = collector.sample(identity)
            second = collector.sample(identity)
        self.assertEqual(first.wall.status, "observed")
        self.assertEqual(first.disk.status, "observed")
        self.assertEqual(first.rss.status, "observed")
        self.assertEqual(first.rss.value, 120)
        self.assertEqual(first.rss.started_at, identity.birth.observed_at)
        self.assertEqual(first.rss.observed_at, rows[0].observed_at)
        self.assertEqual(second.rss.status, "observed")
        self.assertEqual(second.rss.value, 120)
        self.assertEqual(second.rss.sample_count, 3)
        self.assertIn("not descendants", second.rss.coverage[1])

        changed = self.identity(pid=identity.pid + 1)
        after_change = collector.sample(changed)
        self.assertEqual(after_change.rss.status, "partial")
        self.assertEqual(after_change.rss.value, 120)
        self.assertIn("identity changed", after_change.rss.reason)

    def test_process_group_must_match_supervisor_created_session_leader(self):
        invalid = self.identity(pid=404040, pgid=404041)
        report = self.collector().sample(invalid)
        self.assertEqual(report.rss.status, "unknown")
        self.assertIn("session leader PID", report.rss.reason)

    def test_monotonic_regression_poisoned_wall_and_rss_without_zeroing_prior_scope(self):
        fake = FakeClock([100.0, 99.0, 99.0])
        collector = self.collector(clock=fake.as_clock())
        report = collector.sample(self.identity())
        self.assertEqual(report.wall.status, "unknown")
        self.assertIsNone(report.wall.value)
        self.assertEqual(report.rss.status, "unknown")
        self.assertIsNone(report.rss.value)
        self.assertIn("monotonic clock moved backwards", report.wall.reason)

def verify_source_integrity(snapshot: resources.LocalResourceSnapshot) -> bool:
    return resources.verify_resource_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
