# SPDX-License-Identifier: AGPL-3.0-only
"""Offline private-archive controls; no native collector or account is invoked."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_claude_observer as observer

NOW = datetime(2026, 10, 14, 12, tzinfo=timezone.utc)


def sha(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode()).hexdigest()


def receipt():
    route = lambda kind: {"schema": "claude-bounded-native-read-receipt/v3", "route": kind,
        "method": "GET", "status": 200, "observed_at_utc": NOW.isoformat(),
        "response_sha256": sha(kind), "response_body_capture": "captured", "identity_sha256": {},
        "controls_status": "present", "controls": {"extra_usage_enabled": False}}
    profile, usage = route("profile"), route("usage")
    profile["identity_sha256"] = {"account": sha("fake-account"), "organization": sha("fake-organization")}
    profile["identity_hmac_sha256"] = {"account_email": sha("fake-keyed-email")}
    profile["identity_key_fingerprint"] = "0123456789abcdef"
    usage["controls"]["quota_windows"] = {kind: {"quota_used_pct": 5,
        "resets_at_utc": (NOW + timedelta(hours=1)).isoformat()} for kind in ("five_hour", "seven_day")}
    return {"schema": observer.RECEIPT_SCHEMA,
        "candidate": {"version": observer.NATIVE_VERSION, "binary_sha256": observer.NATIVE_BINARY_SHA256,
                      "routes_manifest_sha256": observer.ROUTES_SHA256},
        "adapter_sha256": observer.COLLECTOR_SHA256,
        "credential_acquisition": "keychain-existing-oauth", "provider_inference_requests": 0,
        "collection_status": "bounded_observation", "started_at_utc": NOW.isoformat(),
        "finished_at_utc": NOW.isoformat(), "routes": [profile, usage],
        "process_store_binding": {"mode": "isolated-config-dir", "keychain_service_suffix": "0123abcd",
            "global_config_file": ".config.json", "config_account_present": True,
            "config_organization_present": True, "config_account_matches_profile": True,
            "config_organization_matches_profile": True, "status": "bound"}}


def project(value=None, **kwargs):
    return observer.project_quota_receipt(value or receipt(),
        expected_account_sha256=sha("fake-account"), expected_organization_sha256=sha("fake-organization"),
        expected_namespace_sha256=sha("fake-private-namespace"), expected_keychain_suffix="0123abcd",
        expected_key_fingerprint="0123456789abcdef", namespace_verifier=lambda *args: None,
        now=NOW, **kwargs)


class ClaudeQuotaProjectionTests(unittest.TestCase):
    def test_private_projection_retains_original_times_and_native_hmac_method(self):
        value = receipt()
        sample = project(value)
        self.assertEqual(sample.observed_at, NOW)
        self.assertEqual(sample.valid_until, NOW + timedelta(seconds=60))
        self.assertFalse(sample.extra_usage_enabled)
        self.assertFalse(sample.evidence_claims()["nativeProcessObserved"])
        self.assertEqual(sample.email_binding_method, observer.ARCHIVED_EMAIL_METHOD)
        self.assertEqual(sample.key_fingerprint, "0123456789abcdef")
        self.assertEqual(sample.as_quota_payload()["quotaWindows"]["fiveHour"]["usedPct"], 5)
        self.assertNotIn(sha("fake-account"), repr(sample))
        self.assertNotIn(sha("fake-keyed-email"), repr(sample))
        witness = sample.as_native_profile_witness()
        self.assertEqual(witness.email_binding_method, "claude-account-email-v1")
        self.assertEqual(witness.key_fingerprint_sha256, sha("0123456789abcdef"))
        self.assertEqual(witness.email_binding_sha256, sample.email_binding_sha256)
        value["routes"][1]["controls"]["quota_windows"]["five_hour"]["quota_used_pct"] = 100
        self.assertEqual(sample.as_quota_payload()["quotaWindows"]["fiveHour"]["usedPct"], 5)

    def test_each_explicit_extra_usage_control_and_unknown_identity_refuse(self):
        for index in (0, 1):
            for bad in (True, None, 0, "false", "missing"):
                with self.subTest(index=index, bad=bad):
                    value = receipt()
                    if bad == "missing":
                        del value["routes"][index]["controls"]["extra_usage_enabled"]
                    else:
                        value["routes"][index]["controls"]["extra_usage_enabled"] = bad
                    with self.assertRaises(observer.ClaudeObserverError):
                        project(value)
        for mutation in ("account", "organization", "hmac", "fingerprint", "status", "store"):
            with self.subTest(mutation=mutation):
                value = receipt()
                profile = value["routes"][0]
                if mutation in ("account", "organization"):
                    profile["identity_sha256"][mutation] = sha("different")
                elif mutation == "hmac":
                    del profile["identity_hmac_sha256"]
                elif mutation == "fingerprint":
                    profile["identity_key_fingerprint"] = "f" * 16
                elif mutation == "status":
                    profile["identity_hmac_status"] = "email_unavailable"
                else:
                    value["process_store_binding"]["config_account_matches_profile"] = None
                with self.assertRaises(observer.ClaudeObserverError):
                    project(value)

    def test_quota_expiry_freshness_sequence_and_namespace_verification_refuse(self):
        for mutation in ("stale", "future", "reset", "exhausted", "order", "candidate", "suffix", "routes"):
            with self.subTest(mutation=mutation):
                value = receipt()
                if mutation in ("stale", "future"):
                    value["routes"][1]["observed_at_utc"] = (
                        NOW + timedelta(seconds=1 if mutation == "future" else -61)).isoformat()
                elif mutation == "reset":
                    value["routes"][1]["controls"]["quota_windows"]["five_hour"]["resets_at_utc"] = NOW.isoformat()
                elif mutation == "exhausted":
                    value["routes"][1]["controls"]["quota_windows"]["five_hour"]["quota_used_pct"] = 100
                elif mutation == "order":
                    value["started_at_utc"] = (NOW + timedelta(seconds=1)).isoformat()
                elif mutation == "candidate":
                    value["candidate"]["binary_sha256"] = sha("drift")
                elif mutation == "suffix":
                    value["process_store_binding"]["keychain_service_suffix"] = "abcd0123"
                else:
                    value["routes"].append(deepcopy(value["routes"][0]))
                with self.assertRaises(observer.ClaudeObserverError):
                    project(value)
        with self.assertRaises(observer.ClaudeObserverError):
            observer.project_quota_receipt(receipt(), expected_account_sha256=sha("fake-account"),
                expected_organization_sha256=sha("fake-organization"), expected_namespace_sha256=sha("namespace"),
                expected_keychain_suffix="0123abcd", expected_key_fingerprint="0123456789abcdef",
                namespace_verifier=lambda *args: False, now=NOW)


class ClaudeArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.archive = self.root / "archive"
        (self.archive / "claude").mkdir(parents=True, mode=0o700)
        self.review = self.root / "review"
        (self.review / "candidate").mkdir(parents=True, mode=0o700)
        self.collector = b"OFFLINE_ONLY = True\n"
        routes = json.dumps({"candidate": {"version": observer.NATIVE_VERSION,
                                          "binary_sha256": observer.NATIVE_BINARY_SHA256}}).encode()
        for root in (self.archive / "claude", self.review / "candidate"):
            (root / "collector.py").write_bytes(self.collector)
            (root / "routes.json").write_bytes(routes)
        context = json.dumps({"collectorSha256": sha(self.collector), "routesSha256": sha(routes),
                              "exitCode": 0, "retry": False, "receiptPresent": True}).encode()
        (self.archive / "run-record.private.json").write_bytes(context)
        manifest = json.dumps({"files": [{"path": "candidate/collector.py", "bytes": len(self.collector),
                                           "sha256": sha(self.collector)},
                                        {"path": "candidate/routes.json", "bytes": len(routes), "sha256": sha(routes)}]}).encode()
        (self.review / "MANIFEST.private.json").write_bytes(manifest)
        for path in self.root.rglob("*"):
            if path.is_file():
                path.chmod(0o600)
            elif path.is_dir():
                path.chmod(0o700)
        for name, value in {"COLLECTOR_SHA256": sha(self.collector), "ROUTES_SHA256": sha(routes),
                            "CONTEXT_SHA256": sha(context), "REVIEW_MANIFEST_SHA256": sha(manifest)}.items():
            patcher = patch.object(observer, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_frozen_private_archive_load_is_inert_and_refuses_all_drift(self):
        verified = observer.verify_private_archive(self.archive, self.review)
        self.assertEqual(verified.collector_sha256, sha(self.collector))
        module = observer.load_collector_for_offline_checks(self.archive, self.review)
        self.assertTrue(module.OFFLINE_ONLY)
        for path in (self.archive / "claude/collector.py", self.archive / "claude/routes.json",
                     self.archive / "run-record.private.json", self.review / "MANIFEST.private.json"):
            original = path.read_bytes()
            path.write_bytes(original + b"drift")
            with self.assertRaises(observer.ClaudeObserverError):
                observer.verify_private_archive(self.archive, self.review)
            path.write_bytes(original)
        path = self.archive / "claude/collector.py"
        path.chmod(0o644)
        with self.assertRaises(observer.ClaudeObserverError):
            observer.verify_private_archive(self.archive, self.review)

    def test_symlink_and_missing_context_refuse_before_any_collection(self):
        path = self.archive / "claude/collector.py"
        path.unlink()
        path.symlink_to(self.review / "candidate/collector.py")
        with self.assertRaises(observer.ClaudeObserverError):
            observer.verify_private_archive(self.archive, self.review)


class ClaudeLifecycleTests(unittest.TestCase):
    def test_installation_drift_before_spawn_or_during_collection_never_returns_sample(self):
        real_environment = observer.collection_environment
        for phase in ("before-spawn", "during-collection"):
            for changed in ("reference", "python", "key", "config"):
                with self.subTest(phase=phase, changed=changed), tempfile.TemporaryDirectory() as directory:
                    root = Path(directory).resolve()
                    config = root / "config"
                    config.mkdir(mode=0o700)
                    reference, python, key = (root / name for name in ("reference", "python", "key"))
                    reference.write_bytes(b"synthetic static inspected build")
                    python.write_bytes(b"synthetic interpreter never executed")
                    key.write_bytes(b"12" * 32 + b"\n")
                    for path in (reference, python, key):
                        path.chmod(0o600)
                    reference_pin = sha(reference.read_bytes())
                    collector = root / "archive/claude/collector.py"
                    collector.parent.mkdir(parents=True, mode=0o700)
                    output = collector.parent / "new.json"
                    with patch.object(observer, "NATIVE_BINARY_SHA256", reference_pin):
                        instance = observer.ClaudeQuotaObserver(root / "archive", root / "review",
                            native_reference_artifact=reference, python_executable=python,
                            expected_python_sha256=sha(python.read_bytes()), canonical_config_dir=config,
                            expected_keychain_suffix=sha(str(config))[:8], expected_account_sha256=sha("fake-account"),
                            expected_organization_sha256=sha("fake-organization"), expected_namespace_sha256=sha("fake-private-namespace"),
                            identity_key_path=key, expected_identity_key_sha256=sha(key.read_bytes()),
                            expected_key_fingerprint="0123456789abcdef", namespace_verifier=lambda *args: None)
                        value = receipt()
                        stamp = datetime.now(timezone.utc)
                        value["started_at_utc"] = value["finished_at_utc"] = stamp.isoformat()
                        value["process_store_binding"]["keychain_service_suffix"] = sha(str(config))[:8]
                        for route in value["routes"]:
                            route["observed_at_utc"] = stamp.isoformat()
                        for window in value["routes"][1]["controls"]["quota_windows"].values():
                            window["resets_at_utc"] = (stamp + timedelta(hours=1)).isoformat()
                        archive = observer.VerifiedClaudeArchive(collector, observer.COLLECTOR_SHA256,
                            observer.ROUTES_SHA256, observer.REVIEW_MANIFEST_SHA256, observer.CONTEXT_SHA256)
                        def mutate():
                            if changed == "config":
                                config.chmod(0o777)
                            else:
                                {"reference": reference, "python": python, "key": key}[changed].write_bytes(b"drift")
                        def environment(path):
                            result = real_environment(path)
                            if phase == "before-spawn":
                                mutate()
                            return result
                        class FakeProcess:
                            pid = 4321
                            returncode = 0
                            def poll(self):
                                return 0
                        def start(*args, **kwargs):
                            if phase == "during-collection":
                                mutate()
                            output.write_text(json.dumps(value))
                            output.chmod(0o600)
                            return FakeProcess()
                        with patch.object(observer, "verify_private_archive", return_value=archive), patch.object(
                                observer, "collection_environment", side_effect=environment), patch.object(
                                observer.subprocess, "Popen", side_effect=start) as popen, patch.object(
                                observer, "stop_owned_collector") as stop:
                            with self.assertRaises(observer.ClaudeObserverError):
                                instance.read(output, serialized_read_only=True)
                            if phase == "before-spawn":
                                popen.assert_not_called()
                            else:
                                stop.assert_called_once()

    def test_child_loader_checks_exact_opened_key_before_offline_diagnostic(self):
        import subprocess
        import sys
        fake_collector = b"""import hashlib,json,re
from pathlib import Path
_KEY_FILE_RE=re.compile(r'[0-9a-f]{64,128}')
def load_identity_key(path):
 raise AssertionError('the key must not be reopened after its pin check')
def run_personal_diagnostic(output,config_dir=None,identity_key_file=None):
 key=load_identity_key(identity_key_file)
 output.write_text(json.dumps({'offlineOnly':True,'keyDigest':hashlib.sha256(key).hexdigest()}))
"""
        for drift in (False, True):
            with self.subTest(drift=drift), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                collector, routes, key, output = (root / name for name in ("collector.py", "routes.json", "key", "output.json"))
                collector.write_bytes(fake_collector)
                routes.write_bytes(b"{}")
                key.write_bytes(b"12" * 32 + b"\n")
                pin = sha(key.read_bytes())
                if drift:
                    key.write_bytes(b"34" * 32 + b"\n")
                for path in (collector, routes, key):
                    path.chmod(0o600)
                process = subprocess.run([sys.executable, "-I", "-S", "-c", observer._CHILD_LOADER,
                    str(collector), str(output), str(root), str(key), sha(fake_collector), sha(b"{}"), pin],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
                if drift:
                    self.assertNotEqual(0, process.returncode)
                    self.assertFalse(output.exists())
                else:
                    self.assertEqual(0, process.returncode)
                    self.assertEqual(sha(bytes.fromhex("12" * 32)), json.loads(output.read_text())["keyDigest"])

    def test_unserialized_read_and_native_build_drift_refuse_before_process_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            config = root / "config"
            config.mkdir(mode=0o700)
            native = root / "native"
            native.write_bytes(b"explicitly fake unsupported build")
            collector = root / "archive/claude/collector.py"
            instance = observer.ClaudeQuotaObserver(root / "archive", root / "review", native_reference_artifact=native,
                python_executable=root / "python", expected_python_sha256=sha("python"), canonical_config_dir=config,
                expected_keychain_suffix=sha(str(config))[:8], expected_account_sha256=sha("account"),
                expected_organization_sha256=sha("org"), expected_namespace_sha256=sha("namespace"),
                identity_key_path=root / "key", expected_identity_key_sha256=sha("key"),
                expected_key_fingerprint="0123456789abcdef", namespace_verifier=lambda *args: None)
            archive = observer.VerifiedClaudeArchive(collector, observer.COLLECTOR_SHA256,
                observer.ROUTES_SHA256, observer.REVIEW_MANIFEST_SHA256, observer.CONTEXT_SHA256)
            with patch.object(observer, "verify_private_archive", return_value=archive), patch.object(
                    observer.subprocess, "Popen") as popen:
                with self.assertRaises(observer.ClaudeObserverError):
                    instance.read(collector.parent / "new.json")
                with self.assertRaises(observer.ClaudeObserverError):
                    instance.read(collector.parent / "new.json", serialized_read_only=True)
                popen.assert_not_called()

    def test_mocked_private_subprocess_preserves_pins_and_completion_cancellation_refuses(self):
        for cancel_at_completion in (False, True):
            with self.subTest(cancel_at_completion=cancel_at_completion), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                config = root / "canonical-config"
                config.mkdir(mode=0o700)
                suffix = sha(str(config))[:8]
                collector = root / "archive/claude/collector.py"
                output = collector.parent / "fresh-private.json"
                cancel = threading.Event()
                instance = observer.ClaudeQuotaObserver(root / "archive", root / "review",
                    native_reference_artifact=root / "native", python_executable=root / "python",
                    expected_python_sha256=sha("python"), canonical_config_dir=config,
                    expected_keychain_suffix=suffix, expected_account_sha256=sha("fake-account"),
                    expected_organization_sha256=sha("fake-organization"), expected_namespace_sha256=sha("fake-private-namespace"),
                    identity_key_path=root / "private-key", expected_identity_key_sha256=sha("key-file"),
                    expected_key_fingerprint="0123456789abcdef", namespace_verifier=lambda *args: None)
                value = receipt()
                stamp = datetime.now(timezone.utc)
                value["started_at_utc"] = value["finished_at_utc"] = stamp.isoformat()
                value["process_store_binding"]["keychain_service_suffix"] = suffix
                for route in value["routes"]:
                    route["observed_at_utc"] = stamp.isoformat()
                for window in value["routes"][1]["controls"]["quota_windows"].values():
                    window["resets_at_utc"] = (stamp + timedelta(hours=1)).isoformat()
                class FakeProcess:
                    pid = 4321
                    returncode = 0
                    def poll(self):
                        if cancel_at_completion:
                            cancel.set()
                        return 0
                archive = observer.VerifiedClaudeArchive(collector, observer.COLLECTOR_SHA256,
                    observer.ROUTES_SHA256, observer.REVIEW_MANIFEST_SHA256, observer.CONTEXT_SHA256)
                def read_file(path, expected, **kwargs):
                    return json.dumps(value).encode() if path == output else b"explicitly synthetic pin fixture"
                with patch.object(observer, "verify_private_archive", return_value=archive), patch.object(
                        observer, "_read_file", side_effect=read_file) as reader, patch.object(
                        observer.subprocess, "Popen", return_value=FakeProcess()) as popen, patch.object(
                        observer, "stop_owned_collector") as stop:
                    if cancel_at_completion:
                        with self.assertRaises(observer.ClaudeObserverError):
                            instance.read(output, serialized_read_only=True, cancel_event=cancel)
                    else:
                        self.assertEqual(instance.read(output, serialized_read_only=True).observed_at, stamp)
                    stop.assert_called_once()
                    command = popen.call_args.args[0]
                    self.assertEqual(command[1:4], ["-I", "-S", "-c"])
                    self.assertIn(observer.COLLECTOR_SHA256, command)
                    self.assertIn(observer.ROUTES_SHA256, command)
                    self.assertNotIn(str(root / "native"), command)
                    self.assertEqual(popen.call_args.kwargs["stdout"], observer.subprocess.DEVNULL)
                    self.assertEqual(popen.call_args.kwargs["stderr"], observer.subprocess.DEVNULL)
                    self.assertTrue(popen.call_args.kwargs["start_new_session"])
                    self.assertTrue(any(call.args[:2] == (root / "native", observer.NATIVE_BINARY_SHA256)
                                        for call in reader.call_args_list))
                self.assertTrue(instance._lock.acquire(blocking=False))
                instance._lock.release()

    def test_cleanup_waits_for_descendants_and_defers_interrupt_during_poll_sleep(self):
        class Process:
            pid = 4321
            waits = 0
            def wait(self, timeout=None):
                self.waits += 1
                return 0
        process = Process()
        checks = []
        def signal_group(pid, sig):
            if sig == 0:
                checks.append(sig)
                if len(checks) >= 3:
                    raise ProcessLookupError()
        with patch.object(observer.os, "killpg", side_effect=signal_group), patch.object(
                observer.time, "sleep", side_effect=[KeyboardInterrupt(), None]):
            with self.assertRaises(KeyboardInterrupt):
                observer.stop_owned_collector(process)
        self.assertEqual(3, len(checks))
        self.assertGreaterEqual(process.waits, 3)

    def test_cleanup_interrupt_propagates_only_after_owned_process_is_reaped(self):
        class InterruptedProcess:
            pid = 4321
            reaped = False
            calls = 0
            def wait(self, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    raise KeyboardInterrupt()
                self.reaped = True
                return 0
        process = InterruptedProcess()
        def signal_group(pid, sig):
            if sig == 0 and process.reaped:
                raise ProcessLookupError()
        with patch.object(observer.os, "killpg", side_effect=signal_group):
            with self.assertRaises(KeyboardInterrupt):
                observer.stop_owned_collector(process)
        self.assertTrue(process.reaped)

    def test_environment_has_fixed_home_and_no_ambient_provider_or_proxy_configuration(self):
        import pwd
        home = pwd.getpwuid(os.getuid()).pw_dir
        with patch.dict(os.environ, {"HOME": home, "ANTHROPIC_API_KEY": "fake-secret",
                                    "HTTPS_PROXY": "http://fake-proxy", "PYTHONPATH": "fake-loader"}):
            env = observer.collection_environment(Path("/private/fake-config"))
        self.assertEqual(env["HOME"], home)
        self.assertEqual(env["CLAUDE_CONFIG_DIR"], "/private/fake-config")
        self.assertNotIn("ANTHROPIC_API_KEY", env)
        self.assertNotIn("HTTPS_PROXY", env)
        self.assertNotIn("PYTHONPATH", env)
        with patch.dict(os.environ, {"HOME": "/other"}):
            with self.assertRaises(observer.ClaudeObserverError):
                observer.collection_environment(Path("/private/fake-config"))

    def test_process_cancellation_terminates_and_reaps_before_return(self):
        class FakeProcess:
            pid = 4321
            reaped = False
            def wait(self, timeout=None):
                self.reaped = True
                return 0
        process = FakeProcess()
        def signal_group(pid, sig):
            if sig == 0 and process.reaped:
                raise ProcessLookupError()
        with patch.object(observer.os, "killpg", side_effect=signal_group) as kill:
            observer.stop_owned_collector(process)
        self.assertTrue(process.reaped)
        self.assertTrue(any(call.args[1] == observer.signal.SIGTERM for call in kill.call_args_list))


if __name__ == "__main__":
    unittest.main()
