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
from unittest.mock import patch

from agent_braid import tooling_capture as capture
from agent_braid import tooling_supervisor as supervisor
from agent_braid.tooling_process_birth import ProcessBirthIdentity
from agent_braid.tooling_supervisor import (
    BudgetCaps,
    Clock,
    FilePin,
    ProcessRequest,
    SupervisorError,
    TelemetrySnapshot,
    run_supervised,
)
from agent_braid.tooling_subscription import SubscriptionBinding, SubscriptionObservation


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _utc(delta_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat().replace("+00:00", "Z")


def _snapshot(*, eur=0.0, tokens=0, wall=0.1, rss=0, disk=0, observed_at=None,
              incident=False, unrecoverable=False, failures=0, subscription=None):
    values = {"eur": eur, "tokens": tokens, "input_tokens": tokens, "output_tokens": 0,
              "retry_tokens": 0, "wall_seconds": wall, "rss_bytes": rss, "disk_bytes": disk}
    costs = capture.MeasuredCosts(values, "synthetic measurement", _sha(json.dumps(values)),
                                 observed_at or _utc())
    stop = capture.StopState(incident, unrecoverable, failures, "synthetic stop source",
                             _sha("stop"), observed_at or _utc())
    return TelemetrySnapshot(costs, stop, subscription)


def _subscription(binding, *, auth="chatgpt", quota=True, extra=False, credits=False,
                  recharge=False, api=False, observed_at=None):
    return SubscriptionObservation(binding, auth, True, extra, credits, recharge, api,
                                   quota, 0, "authenticated-account-settings",
                                   _sha("subscription-proof"),
                                   datetime.fromisoformat((observed_at or _utc()).replace("Z", "+00:00")))


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
        self.subscription_binding = SubscriptionBinding(
            "codex", _sha("registration"), "slot-001", _sha("policy"), _sha("account"))

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

    def test_kernel_birth_is_captured_after_popen_before_live_observation(self):
        events = []

        def capture_birth(pid):
            value = ProcessBirthIdentity(pid, "test", "synthetic-birth-source", "birth-token", 0)
            events.append(("birth", pid, value.token))
            return value

        def observer(identity, elapsed):
            if identity is not None:
                events.append(("observer", identity.pid, identity.birth.token if identity.birth else None))
                self.assertIsNotNone(identity.birth)
            return _snapshot(wall=0.1 + elapsed)

        with patch.object(supervisor, "capture_process_birth", side_effect=capture_birth):
            result = run_supervised(self.request("import time; time.sleep(0.2)"), self.caps, observer)
        self.assertTrue(result.launched)
        birth_index = next(i for i, event in enumerate(events) if event[0] == "birth")
        observer_index = next(i for i, event in enumerate(events) if event[0] == "observer")
        self.assertLess(birth_index, observer_index)
        self.assertEqual(events[birth_index][1], events[observer_index][1])
        self.assertEqual(events[birth_index][2], events[observer_index][2])

    def test_subscription_only_preflight_and_periodic_stop(self):
        binding = self.subscription_binding

        # A valid live observer can run a short local process, and the receipt
        # retains the policy binding and bounded source proof without a raw ref.
        req = ProcessRequest(**{**self.request("raise SystemExit(0)").__dict__,
                               "subscription_binding": binding})
        result = run_supervised(req, self.caps,
                                lambda _identity, _elapsed: _snapshot(
                                    subscription=_subscription(binding)),)
        self.assertTrue(result.completed, result)
        receipt = json.loads(result.receipt_path.read_text())
        self.assertEqual(binding.as_dict(), receipt["subscriptionBinding"])
        proof = receipt["lastSnapshot"]["subscription"]
        self.assertEqual(_sha("authenticated-account-settings"), proof["sourceRefSha256"])
        self.assertNotIn("sourceRef", proof)

        # Invalid initial state refuses before Popen.
        for label, value in (
            ("missing", None),
            ("auth", _subscription(binding, auth="unknown")),
            ("paid", _subscription(binding, extra=True)),
        ):
            with self.subTest(stage="preflight", label=label):
                req = ProcessRequest(**{**self.request("raise SystemExit(0)").__dict__,
                                       "subscription_binding": binding})
                result = run_supervised(req, self.caps,
                                        lambda _identity, _elapsed, value=value: _snapshot(subscription=value))
                self.assertEqual("refused", result.status)
                self.assertFalse(result.launched)

        # A fresh but depleted or paid-enabled periodic observation terminates
        # the owned process group and cannot produce a completed result.
        for label, value in (
            ("quota", _subscription(binding, quota=False)),
            ("auth", _subscription(binding, auth="unknown")),
            ("paid", _subscription(binding, api=True)),
        ):
            with self.subTest(stage="periodic", label=label):
                calls = {"count": 0}
                def observer(identity, elapsed, value=value):
                    calls["count"] += 1
                    sub = _subscription(binding) if identity is None else value
                    return _snapshot(wall=0.1 + elapsed, subscription=sub)
                req = ProcessRequest(**{**self.request("import time; time.sleep(10)").__dict__,
                                       "subscription_binding": binding})
                result = run_supervised(req, self.caps, observer)
                self.assertTrue(result.launched)
                self.assertEqual("subscription-policy-violation", result.status)
                self.assertIsNotNone(result.returncode)
                self.assertGreaterEqual(calls["count"], 2)

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
        ignore = ("import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                  "print('TERM_IGNORED_READY',flush=True); time.sleep(10)")
        cancel = threading.Event()
        ready = threading.Event()
        request = self.request(ignore, timeout=1.5)

        def cancel_after_signal_handler_is_installed(identity, elapsed):
            if identity is not None:
                try:
                    with (request.output_root / "stdout.partial").open("rb") as output:
                        marker = output.read(64)
                except OSError:
                    marker = b""
                if marker.startswith(b"TERM_IGNORED_READY\n"):
                    ready.set()
                    cancel.set()
            return _snapshot(wall=0.1 + elapsed)

        ignored = run_supervised(request, self.caps, cancel_after_signal_handler_is_installed,
                                 cancel_event=cancel)
        self.assertTrue(ready.is_set(), "child never confirmed its SIGTERM handler was installed")
        self.assertEqual("cancelled", ignored.status)
        self.assertEqual(9, ignored.signal)
        self.assertLess(ignored.wall_elapsed_seconds, 2.0)

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

    def test_blocked_prelaunch_observer_times_out_without_start_marker(self):
        entered = threading.Event()
        release = threading.Event()
        callback_done = threading.Event()

        def observer(identity, elapsed):
            entered.set()
            release.wait(2)
            callback_done.set()
            return _snapshot()

        request = self.request("raise SystemExit(0)")
        request = ProcessRequest(**{**request.__dict__, "observation_max_age_seconds": 0.08,
                                    "observer_timeout_seconds": 0.08})
        began = time.monotonic()
        result = run_supervised(request, self.caps, observer)
        self.assertTrue(entered.is_set())
        self.assertLess(time.monotonic() - began, 0.8)
        self.assertEqual("measurement-unknown", result.status)
        self.assertFalse(result.launched)
        self.assertFalse((request.output_root / "started.json").exists())
        self.assertFalse(callback_done.is_set())
        release.set()
        self.assertTrue(callback_done.wait(0.5))

    def test_blocked_live_observer_stops_child_and_is_not_retried(self):
        entered = threading.Event()
        release = threading.Event()
        callback_done = threading.Event()
        identities = []

        def observer(identity, elapsed):
            identities.append(identity)
            if identity is not None:
                entered.set()
                release.wait(2)
                callback_done.set()
            return _snapshot(wall=0.1 + elapsed)

        request = self.request("import time; time.sleep(10)", timeout=5)
        request = ProcessRequest(**{**request.__dict__, "observation_max_age_seconds": 0.08,
                                    "poll_interval_seconds": 0.02,
                                    "observer_timeout_seconds": 0.08})
        began = time.monotonic()
        result = run_supervised(request, self.caps, observer)
        self.assertTrue(entered.is_set())
        self.assertLess(time.monotonic() - began, 1.5)
        self.assertEqual("measurement-unknown", result.status)
        self.assertTrue(result.launched)
        self.assertIsNotNone(result.returncode)
        self.assertEqual(2, len(identities))
        self.assertFalse(callback_done.is_set())
        release.set()
        self.assertTrue(callback_done.wait(0.5))

    def test_blocked_final_observer_leaves_completed_process_unverified(self):
        entered = threading.Event()
        release = threading.Event()
        callback_done = threading.Event()
        calls = {"count": 0}

        def observer(identity, elapsed):
            calls["count"] += 1
            if calls["count"] == 2:
                entered.set()
                release.wait(2)
                callback_done.set()
            return _snapshot(wall=0.1 + elapsed)

        request = self.request("import time; time.sleep(0.03)", timeout=2)
        request = ProcessRequest(**{**request.__dict__, "observation_max_age_seconds": 0.15,
                                    "poll_interval_seconds": 0.1,
                                    "observer_timeout_seconds": 0.15})
        began = time.monotonic()
        result = run_supervised(request, self.caps, observer)
        self.assertTrue(entered.is_set())
        self.assertLess(time.monotonic() - began, 1.5)
        self.assertEqual("measurement-unknown", result.status)
        self.assertNotEqual("completed", result.status)
        self.assertEqual(2, calls["count"])
        self.assertFalse(callback_done.is_set())
        release.set()
        self.assertTrue(callback_done.wait(0.5))

    def test_request_wait_bounds_reject_excessive_values_before_observation(self):
        invalid = (
            {"observation_max_age_seconds": 61.0},
            {"observer_timeout_seconds": 1.01},
            {"poll_interval_seconds": 0.26},
            {"term_grace_seconds": 1.01},
            {"kill_grace_seconds": 1.01},
        )
        for changes in invalid:
            with self.subTest(changes=changes):
                request = self.request("pass")
                request = ProcessRequest(**{**request.__dict__, **changes})
                calls = {"count": 0}

                def observer(_identity, _elapsed):
                    calls["count"] += 1
                    return _snapshot()

                with self.assertRaises(SupervisorError):
                    run_supervised(request, self.caps, observer)
                self.assertEqual(0, calls["count"])

    def test_maximum_grace_terminates_term_ignoring_process_group_boundedly(self):
        child = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)"
        parent = ("import signal,subprocess,sys,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                  f"subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)")
        request = self.request(parent, timeout=0.1)
        request = ProcessRequest(**{**request.__dict__, "term_grace_seconds": 1.0,
                                    "kill_grace_seconds": 1.0})
        began = time.monotonic()
        result = run_supervised(request, self.caps, self.observer()[0])
        self.assertEqual("timed-out", result.status)
        self.assertNotEqual("completed", result.status)
        self.assertLess(time.monotonic() - began, 3.5)

    def test_final_observer_failure_is_recorded_even_after_budget_stop(self):
        calls = {"count": 0}

        def observer(identity, elapsed):
            calls["count"] += 1
            if calls["count"] == 2:
                return _snapshot(tokens=4_000_000, wall=0.1 + elapsed)
            if calls["count"] >= 3:
                raise RuntimeError("secret collector details must not be retained")
            return _snapshot(wall=0.1 + elapsed)

        result = run_supervised(self.request("import time; time.sleep(10)"), self.caps,
                                observer)
        self.assertEqual("budget-exceeded", result.status)
        receipt = json.loads(result.receipt_path.read_text())
        self.assertTrue(receipt["observerFailure"].startswith("RuntimeError:"))
        self.assertNotIn("secret collector details", result.receipt_path.read_text())

    def test_cumulative_wall_snapshot_is_not_double_counted_with_local_elapsed(self):
        calls = {"count": 0}
        live_owned_ready = threading.Event()
        request = self.request(
            "import time; print('CUMULATIVE_WALL_CHILD_READY',flush=True); time.sleep(0.5)",
            timeout=2)

        def observer(identity, elapsed):
            calls["count"] += 1
            if identity is not None:
                try:
                    with (request.output_root / "stdout.partial").open("rb") as output:
                        marker = output.read(64)
                except OSError:
                    marker = b""
                if marker.startswith(b"CUMULATIVE_WALL_CHILD_READY\n"):
                    live_owned_ready.set()
            wall = 9.8 if calls["count"] == 1 else 9.99
            return _snapshot(wall=wall)

        caps = BudgetCaps(25.0, 4_000_000, 10.0, 4 * 1024**3, 5 * 1024**3)
        real_monotonic = time.monotonic
        clock_calls = {"count": 0, "post_live_origin": None}

        def controlled_monotonic():
            # Script the first live polling opportunity independently of child
            # startup latency, then advance at a slower real-monotonic rate.
            # This stays monotonic and keeps timeout/cleanup clocks moving.
            clock_calls["count"] += 1
            if clock_calls["count"] <= 2:
                return 0.0
            if clock_calls["count"] == 3:
                return 0.02
            if clock_calls["count"] == 4:
                clock_calls["post_live_origin"] = real_monotonic()
                return 0.1
            return 0.1 + (real_monotonic() - clock_calls["post_live_origin"]) * 0.1

        result = run_supervised(request, caps, observer, clock=Clock(monotonic=controlled_monotonic))
        self.assertTrue(result.completed, result)
        self.assertTrue(live_owned_ready.is_set(), "owned child did not reach its readiness marker")
        self.assertGreaterEqual(calls["count"], 3)
        self.assertGreater(result.wall_elapsed_seconds, 0.01)
        self.assertLess(result.wall_elapsed_seconds, 0.2)
        self.assertLess(max(9.8 + result.wall_elapsed_seconds, 9.99), caps.wall_seconds)
        self.assertGreater(9.99 + result.wall_elapsed_seconds, caps.wall_seconds)
        self.assertEqual(9.99, result.last_snapshot.costs.values["wall_seconds"])

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

    def test_configuration_pin_drift_during_observer_refuses_before_launch(self):
        config = self.source / "host-config.json"
        config.write_text('{"mode":"synthetic"}')
        expected = _sha(config.read_bytes())
        request = self.request("raise SystemExit(0)")
        request = ProcessRequest(**{**request.__dict__,
                                    "file_pins": (FilePin(config, expected),)})

        def mutate_config(_identity, _elapsed):
            config.write_text('{"mode":"changed"}')
            return _snapshot()

        result = run_supervised(request, self.caps, mutate_config)
        self.assertEqual("start-drift", result.status)
        self.assertFalse(result.launched)
        self.assertFalse((request.output_root / "started.json").exists())

    def test_sparse_oversized_executable_and_config_pins_refuse_before_observer(self):
        calls = {"count": 0}

        def observer(_identity, _elapsed):
            calls["count"] += 1
            return _snapshot()

        oversized_binary = Path(self.temp.name) / "oversized-executable"
        with oversized_binary.open("wb") as stream:
            stream.truncate(512 * 1024 * 1024 + 1)
        oversized_binary.chmod(0o700)
        binary_request = self.request("unused", executable=oversized_binary,
                                      executable_sha="0" * 64)
        binary_result = run_supervised(binary_request, self.caps, observer)
        self.assertEqual("start-drift", binary_result.status)
        self.assertFalse(binary_result.launched)

        large_pin = self.source / "large-sparse-config"
        with large_pin.open("wb") as stream:
            stream.truncate(1024 * 1024 + 1)
        pin_request = self.request("pass")
        pin_request = ProcessRequest(**{**pin_request.__dict__,
                                       "file_pins": (FilePin(large_pin, "0" * 64),)})
        pin_result = run_supervised(pin_request, self.caps, observer)
        self.assertEqual("start-drift", pin_result.status)
        self.assertFalse(pin_result.launched)
        self.assertEqual(0, calls["count"])

    def test_file_pin_symlink_or_fifo_replacement_refuses_without_blocking(self):
        for replacement in ("symlink", "fifo"):
            with self.subTest(replacement=replacement):
                config = self.source / f"config-{replacement}"
                config.write_text("synthetic")
                request = self.request("raise SystemExit(0)")
                request = ProcessRequest(**{**request.__dict__,
                    "file_pins": (FilePin(config, _sha(config.read_bytes())),)})

                def replace(_identity, _elapsed):
                    config.unlink()
                    if replacement == "fifo":
                        os.mkfifo(config)
                    else:
                        config.symlink_to(self.source / "missing-target")
                    return _snapshot()

                began = time.monotonic()
                result = run_supervised(request, self.caps, replace)
                self.assertLess(time.monotonic() - began, 0.5)
                self.assertEqual("start-drift", result.status)
                self.assertFalse(result.launched)
                self.assertFalse((request.output_root / "started.json").exists())

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
