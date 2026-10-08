# SPDX-License-Identifier: AGPL-3.0-only
"""Real local subprocess controls; no host, provider, or network invocation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

from agent_braid import tooling_capture as capture
from agent_braid.tooling_supervisor import (
    BudgetCaps,
    ProcessRequest,
    SupervisorError,
    TelemetrySnapshot,
    run_supervised,
)


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _utc(delta_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat().replace("+00:00", "Z")


def _snapshot(*, eur=0.0, tokens=0, wall=0.1, rss=0, disk=0, observed_at=None,
              incident=False, unrecoverable=False, failures=0):
    values = {"eur": eur, "tokens": tokens, "input_tokens": tokens, "output_tokens": 0,
              "retry_tokens": 0, "wall_seconds": wall, "rss_bytes": rss, "disk_bytes": disk}
    costs = capture.MeasuredCosts(values, "synthetic measurement", _sha(json.dumps(values)),
                                 observed_at or _utc())
    stop = capture.StopState(incident, unrecoverable, failures, "synthetic stop source",
                             _sha("stop"), observed_at or _utc())
    return TelemetrySnapshot(costs, stop)


class ToolingSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m45-supervisor-")
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / "source"
        self.grant = base / "grant-store"
        self.cwd = base / "private-cwd"
        self.source.mkdir(mode=0o700)
        self.grant.mkdir(mode=0o700)
        self.cwd.mkdir(mode=0o700)
        self.caps = BudgetCaps(25.0, 4_000_000, 57_600.0, 4 * 1024**3, 5 * 1024**3)
        self.python = Path(sys.executable).resolve(strict=True)
        self.python_sha = _sha(self.python.read_bytes())
        self.output_counter = 0

    def request(self, code, *, stdin=None, max_output=1024 * 1024, timeout=2.0,
                executable=None, executable_sha=None, output_root=None):
        self.output_counter += 1
        if output_root is None:
            output_root = Path(self.temp.name) / f"private-output-{self.output_counter}"
            output_root.mkdir(mode=0o700)
        binary = executable or self.python
        return ProcessRequest(
            executable=binary, executable_sha256=executable_sha or _sha(binary.read_bytes()),
            argv=("-c", code), cwd=self.cwd, output_root=output_root,
            source_roots=(self.source,), grant_root=self.grant,
            env={"PYTHONUNBUFFERED": "1"}, stdin=stdin, max_output_bytes=max_output,
            timeout_seconds=timeout, observation_max_age_seconds=2.0,
            poll_interval_seconds=0.02, term_grace_seconds=0.05, kill_grace_seconds=0.2)

    def observer(self, *, change=None):
        calls = {"count": 0}

        def observe(identity, elapsed):
            calls["count"] += 1
            if change is not None:
                return change(calls["count"], identity, elapsed)
            return _snapshot(wall=0.1 + elapsed)

        return observe, calls

    def test_noisy_stdout_and_stderr_are_drained_concurrently_and_private(self):
        code = "import os; os.write(1,b'o'*180000); os.write(2,b'e'*190000)"
        result = run_supervised(self.request(code, max_output=500_000), self.caps, self.observer()[0])
        self.assertTrue(result.completed, result)
        self.assertEqual(180_000, result.stdout_bytes)
        self.assertEqual(190_000, result.stderr_bytes)
        self.assertEqual(_sha(b"o" * 180_000), result.stdout_sha256)
        self.assertEqual(_sha(b"e" * 190_000), result.stderr_sha256)
        self.assertEqual(0o600, result.stdout_path.stat().st_mode & 0o777)
        receipt = json.loads(result.receipt_path.read_text())
        self.assertNotIn("env", receipt)
        self.assertNotIn("PYTHONUNBUFFERED", result.receipt_path.read_text())

    def test_output_overflow_preserves_bounded_partial_and_stops_group(self):
        request = self.request("import os,time; [os.write(1,b'x'*8192) for _ in range(1000)]; time.sleep(5)",
                               max_output=4096)
        result = run_supervised(request, self.caps, self.observer()[0])
        self.assertEqual("output-limit", result.status)
        self.assertLessEqual(result.stdout_bytes + result.stderr_bytes, 4096)
        self.assertGreater(result.stdout_bytes_observed, result.stdout_bytes)
        self.assertTrue(result.stdout_path.is_file())
        self.assertTrue(result.receipt_path.is_file())

    def test_timeout_and_cancellation_stop_new_process_groups(self):
        timed = run_supervised(self.request("import time; time.sleep(10)", timeout=0.15),
                               self.caps, self.observer()[0])
        self.assertEqual("timed-out", timed.status)
        self.assertIsNotNone(timed.returncode)

        cancel = threading.Event()
        observer, calls = self.observer()
        def request_cancel(identity, elapsed):
            value = observer(identity, elapsed)
            if identity is not None and calls["count"] >= 2:
                cancel.set()
            return value
        cancelled = run_supervised(self.request("import time; time.sleep(10)", timeout=2),
                                   self.caps, request_cancel, cancel_event=cancel)
        self.assertEqual("cancelled", cancelled.status)
        self.assertIsNotNone(cancelled.returncode)

    def test_ignoring_term_child_and_parent_exit_pipe_holder_are_bounded(self):
        ignore = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)"
        ignored = run_supervised(self.request(ignore, timeout=0.15), self.caps, self.observer()[0])
        self.assertEqual("timed-out", ignored.status)
        self.assertEqual(9, ignored.signal)

        child = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
                 "'import time; time.sleep(10)'],stdout=sys.stdout,stderr=sys.stderr)")
        held = run_supervised(self.request(child, timeout=0.25), self.caps, self.observer()[0])
        self.assertIn(held.status, {"timed-out", "cleanup-unknown"})
        self.assertTrue(held.launched)
        self.assertNotEqual("completed", held.status)

    def test_parent_exit_with_background_descendant_is_never_completed(self):
        child = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',"
                 "'import time; time.sleep(10)'],stdin=subprocess.DEVNULL,"
                 "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)")
        result = run_supervised(self.request(child), self.caps, self.observer()[0])
        self.assertTrue(result.launched)
        self.assertNotEqual("completed", result.status)
        self.assertIn(result.group_cleanup, {"descendants-terminated", "cleanup-unknown"})

    def test_large_stdin_does_not_block_pipe_draining_or_timeout(self):
        result = run_supervised(self.request("import time; time.sleep(10)", stdin=b"p" * (2 * 1024 * 1024),
                                             timeout=0.15), self.caps, self.observer()[0])
        self.assertEqual("timed-out", result.status)
        self.assertLessEqual(result.wall_elapsed_seconds, 2.0)
        receipt = result.receipt_path.read_text()
        self.assertNotIn("p" * 64, receipt)

    def test_prelaunch_caps_staleness_incident_and_unknown_refuse_without_start(self):
        cases = (
            ("at-cap", _snapshot(eur=25.0), "refused"),
            ("incident", _snapshot(incident=True), "refused"),
            ("stale", _snapshot(observed_at=_utc(-10)), "measurement-unknown"),
            ("unknown", _snapshot().costs, "measurement-unknown"),
        )
        for name, value, status in cases:
            with self.subTest(name=name):
                root = Path(self.temp.name) / f"output-{name}"
                root.mkdir(mode=0o700)
                req = self.request("raise SystemExit(0)", output_root=root)
                observation = (lambda _id, _elapsed, value=value: value) if name != "unknown" else \
                    (lambda _id, _elapsed: value)
                result = run_supervised(req, self.caps, observation)
                self.assertEqual(status, result.status)
                self.assertFalse(result.launched)
                self.assertFalse((root / "started.json").exists())

    def test_measurement_failure_during_run_stops_and_keeps_partial_outcome(self):
        calls = {"count": 0}
        def observer(identity, elapsed):
            calls["count"] += 1
            if identity is not None:
                raise RuntimeError("private collector detail")
            return _snapshot(wall=0.1 + elapsed)
        result = run_supervised(self.request("import time; time.sleep(10)"), self.caps, observer)
        self.assertEqual("measurement-unknown", result.status)
        self.assertTrue(result.launched)
        self.assertIsNotNone(result.receipt_path)
        self.assertNotIn("private collector detail", result.receipt_path.read_text())
        self.assertGreaterEqual(calls["count"], 2)

    def test_live_cap_reached_stops_without_claiming_success(self):
        def observer(identity, elapsed):
            return _snapshot(tokens=4_000_000 if identity is not None else 0,
                             wall=0.1 + elapsed)
        result = run_supervised(self.request("import time; time.sleep(10)"), self.caps, observer)
        self.assertEqual("budget-exceeded", result.status)
        self.assertFalse(result.completed)

    def test_executable_pin_mismatch_and_observer_start_drift_never_launch(self):
        wrong = run_supervised(self.request("pass", executable_sha="0" * 64),
                               self.caps, self.observer()[0])
        self.assertEqual("start-drift", wrong.status)
        self.assertFalse(wrong.launched)

        script = Path(self.temp.name) / "pinned-script"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o700)
        original_sha = _sha(script.read_bytes())
        req = self.request("unused", executable=script, executable_sha=original_sha)
        def drift(_identity, _elapsed):
            script.write_text("#!/bin/sh\nexit 1\n")
            script.chmod(0o700)
            return _snapshot()
        result = run_supervised(req, self.caps, drift)
        self.assertEqual("start-drift", result.status)
        self.assertFalse(result.launched)
        self.assertFalse((req.output_root / "started.json").exists())

    def test_one_shot_receipts_prevent_silent_retry(self):
        request = self.request("raise SystemExit(0)")
        result = run_supervised(request, self.caps, self.observer()[0])
        self.assertTrue(result.completed)
        with self.assertRaisesRegex(SupervisorError, "already contains"):
            run_supervised(request, self.caps, self.observer()[0])

    def test_working_and_output_paths_must_stay_outside_source_and_grants(self):
        request = self.request("pass")
        unsafe = ProcessRequest(**{**request.__dict__, "output_root": self.source})
        with self.assertRaisesRegex(SupervisorError, "disjoint from all source and grant roots"):
            run_supervised(unsafe, self.caps, self.observer()[0])


if __name__ == "__main__":
    unittest.main()
