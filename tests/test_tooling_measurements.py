# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic local measurement controls; no hosts or providers are started."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import tooling_measurements as measurements


class _Clock:
    def __init__(self, *ticks: int):
        self._ticks = iter(ticks)

    def __call__(self) -> int:
        return next(self._ticks)


class _CountingScandir:
    def __init__(self, iterator):
        self.iterator = iterator
        self.consumed = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.iterator.close()

    def __iter__(self):
        return self

    def __next__(self):
        entry = next(self.iterator)
        self.consumed += 1
        return entry


class WallClockTests(unittest.TestCase):
    def test_total_wall_is_measured_once_and_overlapping_phases_are_unioned(self):
        clock = measurements.WallClock(
            clock_ns=_Clock(0, 1_000_000_000, 2_000_000_000,
                            3_000_000_000, 4_000_000_000, 5_000_000_000),
            wall_clock=lambda: "2026-10-08T10:00:00Z",
        )
        clock.start_phase("setup")
        clock.start_phase("capture")
        self.assertEqual(clock.end_phase("setup").seconds, 2.0)
        self.assertEqual(clock.end_phase("capture").seconds, 2.0)
        total = clock.finish()
        self.assertEqual(total.value, 5.0)
        self.assertEqual(clock.phase_union_seconds, 3.0)
        self.assertEqual(total.status, "observed")
        self.assertIs(clock.finish(), total)

    def test_unclosed_phase_makes_wall_time_unknown_and_blocks_further_phases(self):
        clock = measurements.WallClock(clock_ns=_Clock(10, 20, 30),
                                       wall_clock=lambda: "2026-10-08T10:00:00Z")
        clock.start_phase("session")
        result = clock.finish()
        self.assertIsNone(result.value)
        self.assertEqual(result.status, "unknown")
        self.assertIn("active", result.reason)
        with self.assertRaisesRegex(measurements.MeasurementError, "finished"):
            clock.end_phase("session")

    def test_unknown_or_duplicate_phase_names_are_rejected(self):
        clock = measurements.WallClock(clock_ns=_Clock(0, 1, 2),
                                       wall_clock=lambda: "2026-10-08T10:00:00Z")
        with self.assertRaises(measurements.MeasurementError):
            clock.start_phase("Bad name")
        clock.start_phase("capture")
        with self.assertRaisesRegex(measurements.MeasurementError, "already active"):
            clock.start_phase("capture")

    def test_phase_inventory_is_bounded(self):
        clock = measurements.WallClock(clock_ns=lambda: 1,
                                       wall_clock=lambda: "2026-10-08T10:00:00Z")
        clock._phases = [measurements.PhaseInterval(f"phase-{index}", 1, 1)
                         for index in range(measurements.MAX_PHASES)]
        with self.assertRaisesRegex(measurements.MeasurementError, "limit"):
            clock.start_phase("final-phase")


class ProcessRssTests(unittest.TestCase):
    def test_aggregates_only_explicit_pids_and_tracks_peak_observed(self):
        reads = iter([
            {101: (1000, "start-a"), 202: (2000, "start-b")},
            {101: (1600, "start-a"), 202: (1900, "start-b")},
        ])
        sampler = measurements.ProcessRssSampler(
            [202, 101], reader=lambda requested: next(reads))
        first = sampler.sample()
        second = sampler.sample()
        self.assertEqual(first.observation.value, 3000)
        self.assertEqual(second.observation.value, 3500)
        self.assertEqual(second.observation.details["pids"], [101, 202])
        self.assertEqual(second.observation.details["scope"], "listed processes only")

    def test_missing_process_and_pid_reuse_are_unknown_not_zero(self):
        missing = measurements.ProcessRssSampler([7], reader=lambda _: {}).sample()
        self.assertIsNone(missing.observation.value)
        self.assertEqual(missing.observation.status, "unknown")
        changing = iter([{7: (100, "first")}, {7: (200, "replacement")}])
        sampler = measurements.ProcessRssSampler([7], reader=lambda _: next(changing))
        self.assertEqual(sampler.sample().observation.value, 100)
        drift = sampler.sample().observation
        self.assertIsNone(drift.value)
        self.assertIn("identity changed", drift.reason)

    def test_reader_exceeding_pid_bound_is_unknown(self):
        sampler = measurements.ProcessRssSampler(
            [1], reader=lambda _: {1: (1, "start"), 2: (2, "extra")})
        result = sampler.sample().observation
        self.assertIsNone(result.value)
        self.assertEqual(result.status, "unknown")
        self.assertIn("absent", result.reason)

    def test_sample_count_limit_fails_closed(self):
        sampler = measurements.ProcessRssSampler([1], reader=lambda _: {1: (10, "start")})
        with patch.object(measurements, "MAX_RSS_SAMPLES", 1):
            self.assertEqual(sampler.sample().observation.value, 10)
            stopped = sampler.sample().observation
        self.assertIsNone(stopped.value)
        self.assertEqual(stopped.status, "unknown")

    def test_invalid_explicit_process_lists_fail_before_sampling(self):
        for pids in ([], [0], [-2], [3, 3], [True], list(range(1, measurements.MAX_EXPLICIT_PIDS + 2))):
            with self.subTest(pids=pids), self.assertRaises(measurements.MeasurementError):
                measurements.ProcessRssSampler(pids)


class DiskFootprintTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m45-measure-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.private = self.root / "private"
        self.private.mkdir(mode=0o700)

    def test_sums_logical_bytes_and_emits_manifest_provenance(self):
        (self.private / "a.txt").write_bytes(b"abc")
        (self.private / "a.txt").chmod(0o600)
        nested = self.private / "nested"
        nested.mkdir(mode=0o700)
        (nested / "b.bin").write_bytes(b"12345")
        (nested / "b.bin").chmod(0o600)
        sample = measurements.measure_private_disk([self.private])
        self.assertEqual(sample.observation.value, 8)
        self.assertEqual(sample.observation.status, "observed")
        self.assertEqual(sample.observation.details["unit"], "logical bytes")
        self.assertRegex(sample.manifest_sha256, r"^[0-9a-f]{64}$")
        (self.private / "a.txt").rename(self.private / "renamed.txt")
        renamed = measurements.measure_private_disk([self.private])
        self.assertNotEqual(sample.manifest_sha256, renamed.manifest_sha256)

    def test_symlink_broad_permissions_overlap_and_empty_roots_are_unknown(self):
        outside = self.root / "outside"
        outside.write_bytes(b"not counted")
        (self.private / "link").symlink_to(outside)
        symlink_result = measurements.measure_private_disk([self.private])
        self.assertIsNone(symlink_result.observation.value)

        (self.private / "link").unlink()
        root_link = self.root / "root-link"
        root_link.symlink_to(self.private, target_is_directory=True)
        self.assertIsNone(measurements.measure_private_disk([root_link]).observation.value)
        with patch.object(measurements.stat, "S_IMODE", return_value=0o755):
            broad = measurements.measure_private_disk([self.private])
        self.assertIsNone(broad.observation.value)

        self.assertIsNone(measurements.measure_private_disk([]).observation.value)
        self.assertIsNone(measurements.measure_private_disk([self.private, self.private]).observation.value)
        child = self.private / "child"
        child.mkdir(mode=0o700)
        self.assertIsNone(measurements.measure_private_disk([self.private, child]).observation.value)

    def test_file_and_directory_inventory_limits_fail_closed(self):
        for index in range(2):
            item = self.private / f"{index}.dat"
            item.write_bytes(b"x")
            item.chmod(0o600)
        with patch.object(measurements, "MAX_DISK_FILES", 1):
            self.assertIsNone(measurements.measure_private_disk([self.private]).observation.value)
        nested = self.private / "nested"
        nested.mkdir(mode=0o700)
        with patch.object(measurements, "MAX_DISK_DIRECTORIES", 1):
            self.assertIsNone(measurements.measure_private_disk([self.private]).observation.value)
        with patch.object(measurements, "MAX_DISK_ROOTS", 1):
            other = self.root / "other"
            other.mkdir(mode=0o700)
            self.assertIsNone(measurements.measure_private_disk([self.private, other]).observation.value)
        with patch.object(measurements, "MAX_DISK_ROOTS", 1):
            generated = (self.private for _ in range(100))
            self.assertIsNone(measurements.measure_private_disk(generated).observation.value)

    def test_public_nested_directory_or_file_and_scan_errors_are_unknown(self):
        child = self.private / "child"
        child.mkdir(mode=0o755)
        # Keep the refusal precondition independent of the caller's umask.
        child.chmod(0o755)
        self.assertEqual(child.stat().st_mode & 0o777, 0o755)
        self.assertIsNone(measurements.measure_private_disk([self.private]).observation.value)
        child.chmod(0o700)
        item = child / "public"
        item.write_bytes(b"x")
        item.chmod(0o644)
        self.assertEqual(item.stat().st_mode & 0o777, 0o644)
        self.assertIsNone(measurements.measure_private_disk([self.private]).observation.value)
        item.chmod(0o600)
        with patch.object(measurements.os, "scandir", side_effect=PermissionError("denied")):
            sample = measurements.measure_private_disk([self.private])
        self.assertIsNone(sample.observation.value)
        self.assertEqual(sample.observation.status, "unknown")

    def test_file_metadata_restored_after_scan_is_detected_by_ctime(self):
        item = self.private / "mutable"
        item.write_bytes(b"before")
        item.chmod(0o600)
        original_lstat = Path.lstat
        original_stat = item.stat()
        changed = False

        def restore_metadata_before_final_check(path):
            nonlocal changed
            if path.name == item.name and not changed:
                changed = True
                item.chmod(0o400)
                item.chmod(0o600)
                os.utime(item, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            return original_lstat(path)

        with patch.object(Path, "lstat", restore_metadata_before_final_check):
            result = measurements.measure_private_disk([self.private])
        self.assertTrue(changed)
        self.assertIsNone(result.observation.value)

    def test_flat_directory_is_consumed_incrementally_and_stops_at_file_limit(self):
        for index in range(100):
            item = self.private / f"{index:03}.dat"
            item.write_bytes(b"x")
            item.chmod(0o600)
        real_scandir = os.scandir
        counted = []

        def counting_scandir(path):
            result = _CountingScandir(real_scandir(path))
            counted.append(result)
            return result

        with patch.object(measurements, "MAX_DISK_FILES", 1), \
                patch.object(measurements.os, "scandir", side_effect=counting_scandir):
            result = measurements.measure_private_disk([self.private])
        self.assertIsNone(result.observation.value)
        self.assertEqual(counted[0].consumed, 2)

    def test_unreadable_or_nonowned_root_is_unknown(self):
        with patch.object(measurements.os, "getuid", return_value=-1):
            sample = measurements.measure_private_disk([self.private])
        self.assertIsNone(sample.observation.value)
        self.assertEqual(sample.observation.status, "unknown")


class CostAdapterTests(unittest.TestCase):
    def test_only_measured_local_fields_are_populated(self):
        def observed(value, source):
            return measurements.Observation(value, "observed", source,
                                            "2026-10-08T10:00:00Z", "2026-10-08T10:00:01Z")

        costs = measurements.measured_costs(
            wall=observed(1.5, "time.monotonic_ns"),
            rss=observed(4096, "ps explicit PIDs"),
            disk=observed(8192, "private roots"),
            source_ref="synthetic-local-measurement",
        )
        self.assertEqual(costs.values["wall_seconds"], 1.5)
        self.assertEqual(costs.values["rss_bytes"], 4096)
        self.assertEqual(costs.values["disk_bytes"], 8192)
        for field in ("eur", "tokens", "input_tokens", "output_tokens", "retry_tokens"):
            self.assertIsNone(costs.values[field], field)
        self.assertRegex(costs.source_sha256, r"^[0-9a-f]{64}$")

    def test_incomplete_observations_preserve_unknown_and_bad_shapes_refuse(self):
        unknown = measurements.Observation(None, "unknown", "ps", "2026-10-08T10:00:00Z",
                                           "2026-10-08T10:00:01Z", "process absent")
        observed = measurements.Observation(1, "observed", "clock", "2026-10-08T10:00:00Z",
                                            "2026-10-08T10:00:01Z")
        costs = measurements.measured_costs(wall=observed, rss=unknown, disk=unknown,
                                             source_ref="incomplete-source")
        self.assertIsNone(costs.values["rss_bytes"])
        self.assertIsNone(costs.values["disk_bytes"])
        with self.assertRaisesRegex(measurements.MeasurementError, "observed RSS"):
            measurements.measured_costs(
                wall=observed,
                rss=measurements.Observation(None, "observed", "bad", "2026-10-08T10:00:00Z",
                                             "2026-10-08T10:00:01Z"),
                disk=unknown, source_ref="bad-shape")
        with self.assertRaises(measurements.MeasurementError):
            measurements.measured_costs(wall=observed, rss=unknown, disk=unknown, source_ref=" ")
        earlier = measurements.Observation(1, "observed", "clock", "2026-10-08T10:00:02Z",
                                           "2026-10-08T10:00:01Z")
        with self.assertRaisesRegex(measurements.MeasurementError, "precedes"):
            measurements.measured_costs(wall=earlier, rss=unknown, disk=unknown,
                                         source_ref="reversed-time")


if __name__ == "__main__":
    unittest.main()
