# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic native-transport controls; no credentials, native reads or admission."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import io
import os
from pathlib import Path
import signal
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agent_braid import tooling_codex_observer as observer

NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)
NAMESPACE = observer._digest("synthetic-account")


def inputs():
    return ({"account": {"type": "chatgpt", "accountId": "synthetic-account"},
             "requiresOpenaiAuth": True,
             "workspaceRouting": {"chatgptAccountId": "synthetic-account"}},
            {"accountId": "synthetic-account", "ordinaryUsageAllowed": True,
             "rateLimits": {"spendControlReached": False,
                            "credits": {"hasCredits": False, "unlimited": False}}})


class CodexQuotaProjectionTests(unittest.TestCase):
    def project(self, account, quota, **kwargs):
        return observer._project(account, quota, expected_namespace=NAMESPACE,
                                 observed=NOW, completed=NOW + timedelta(seconds=1),
                                 max_age_seconds=60, **kwargs)

    def test_account_level_projection_omits_raw_identity_and_financial_fields(self):
        account, quota = inputs()
        quota["rateLimits"]["credits"]["balance"] = "private-financial-value"
        sample = self.project(account, quota)
        self.assertTrue(sample.ordinary_usage_allowed)
        self.assertFalse(sample.has_credits)
        self.assertEqual(sample.account_namespace_sha256, NAMESPACE)
        self.assertEqual(sample.valid_until, NOW + timedelta(seconds=60))
        self.assertNotIn("synthetic-account", repr(sample))
        self.assertNotIn("private-financial-value", repr(sample))
        self.assertFalse(hasattr(sample, "process_id"))
        self.assertFalse(hasattr(sample, "auto_recharge_enabled"))

    def test_optional_private_profile_witness_uses_original_email_without_retaining_it(self):
        from agent_braid import tooling_interface_observer as ui
        account, quota = inputs()
        account["account"]["email"] = "Owner@Example.test"
        key = b"synthetic-codex-private-key-32bytes"
        sample = self.project(account, quota, private_hmac_key=key)
        self.assertEqual(ui.private_email_binding("owner@example.test", key), sample.email_binding_sha256)
        self.assertEqual(ui.key_fingerprint(key), sample.key_fingerprint_sha256)
        self.assertNotIn("Owner@Example.test", repr(sample))
        from tests.test_tooling_codex_sources import fixture
        from agent_braid.tooling_subscription import operational_binding_from_dict
        from dataclasses import replace
        contract, _, _ = fixture()
        binding = replace(operational_binding_from_dict(contract["binding"]),
                          account_sha256=sample.account_object_sha256,
                          account_namespace_sha256=sample.account_namespace_sha256)
        witness = sample.native_profile_witness(binding)
        self.assertEqual(sample.observed_at, witness.observed_at)
        self.assertEqual(sample.email_binding_sha256, witness.email_binding_sha256)
        with self.assertRaises(observer.CodexObserverError):
            sample.native_profile_witness(replace(binding, account_sha256="f" * 64))

    def test_missing_profile_email_cannot_supply_account_bound_interface_witness(self):
        account, quota = inputs()
        sample = self.project(account, quota, private_hmac_key=b"synthetic-codex-private-key-32bytes")
        self.assertIsNone(sample.email_binding_sha256)
        from tests.test_tooling_codex_sources import fixture
        from agent_braid.tooling_subscription import operational_binding_from_dict
        from dataclasses import replace
        contract, _, _ = fixture()
        binding = replace(operational_binding_from_dict(contract["binding"]),
                          account_sha256=sample.account_object_sha256,
                          account_namespace_sha256=sample.account_namespace_sha256)
        with self.assertRaises(observer.CodexObserverError):
            sample.native_profile_witness(binding)

    def test_missing_null_and_non_boolean_controls_remain_unknown(self):
        for value in (None, 0, 1, "false", {}, []):
            account, quota = inputs()
            quota["ordinaryUsageAllowed"] = value
            quota["rateLimits"]["spendControlReached"] = value
            quota["rateLimits"]["credits"] = {"hasCredits": value, "unlimited": value}
            sample = self.project(account, quota)
            self.assertIsNone(sample.ordinary_usage_allowed)
            self.assertIsNone(sample.spend_control_reached)
            self.assertIsNone(sample.has_credits)
            self.assertIsNone(sample.unlimited_credits)
        account, quota = inputs()
        del quota["rateLimits"]
        self.assertIsNone(self.project(account, quota).has_credits)

    def test_unsafe_credit_flags_are_observed_without_becoming_a_permit(self):
        account, quota = inputs()
        quota["rateLimits"]["credits"]["hasCredits"] = True
        self.assertTrue(self.project(account, quota).has_credits)

    def test_identity_drift_and_conflicts_refuse(self):
        account, quota = inputs()
        variants = []
        for field, value in (("accountId", "other"), ("accountId", None)):
            changed = deepcopy(quota)
            changed[field] = value
            variants.append((account, changed))
        changed = deepcopy(account)
        changed["workspaceRouting"]["chatgptAccountId"] = "other"
        variants.append((changed, quota))
        changed = deepcopy(account)
        changed["account"]["type"] = "apiKey"
        variants.append((changed, quota))
        changed = deepcopy(account)
        changed["requiresOpenaiAuth"] = 1
        variants.append((changed, quota))
        # Routing still matches the quota; only the account fallback disagrees.
        changed = deepcopy(account)
        changed["account"]["accountId"] = "other"
        variants.append((changed, quota))
        for left, right in variants:
            with self.assertRaises(observer.CodexObserverError):
                self.project(left, right)

    def test_expiry_and_clock_regression_refuse(self):
        account, quota = inputs()
        for seconds in (-1, 60, 61):
            with self.assertRaises(observer.CodexObserverError):
                observer._project(account, quota, expected_namespace=NAMESPACE, observed=NOW,
                                  completed=NOW + timedelta(seconds=seconds), max_age_seconds=60)


class CodexQuotaAcquisitionTests(unittest.TestCase):
    def test_source_bytes_modes_symlinks_and_digest_checked_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transport.py"
            data = b"raise RuntimeError('must never execute')\n"
            path.write_bytes(data)
            path.chmod(0o600)
            digest = hashlib.sha256(data).hexdigest()
            self.assertEqual(observer._verified_bytes(path, digest, private=True), data)
            with self.assertRaises(observer.CodexObserverError):
                observer._load_transport(path)
            path.chmod(0o640)
            with self.assertRaises(observer.CodexObserverError):
                observer._verified_bytes(path, digest, private=True)
            link = Path(directory) / "link"
            link.symlink_to(path)
            with self.assertRaises(OSError):
                observer._verified_bytes(link, digest, private=True)

    def test_loaded_transport_must_pin_the_reviewed_executable(self):
        for exe, digest in ((observer.EXECUTABLE, observer.EXECUTABLE_SHA256),
                            (Path("/other/codex"), observer.EXECUTABLE_SHA256),
                            (observer.EXECUTABLE, "0" * 64)):
            with self.subTest(exe=str(exe), digest=digest[:8]), \
                    tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "transport.py"
                data = (f"from pathlib import Path\nEXE = Path({str(exe)!r})\n"
                        f"EXPECTED_EXE_SHA256 = {digest!r}\n").encode()
                path.write_bytes(data)
                path.chmod(0o600)
                with patch.object(observer, "TRANSPORT_SHA256", hashlib.sha256(data).hexdigest()):
                    if (exe, digest) == (observer.EXECUTABLE, observer.EXECUTABLE_SHA256):
                        self.assertEqual(observer._load_transport(path).EXE, exe)
                    else:
                        with self.assertRaises(observer.CodexObserverError):
                            observer._load_transport(path)

    def test_context_environment_omits_credentials_and_refuses_custom_home(self):
        with patch.dict(os.environ, {"CODEX_HOME": "", "OPENAI_API_KEY": "synthetic-secret"}):
            self.assertNotIn("OPENAI_API_KEY", observer._environment())
        with patch.dict(os.environ, {"CODEX_HOME": "/custom"}):
            with self.assertRaises(observer.CodexObserverError):
                observer._environment()

    def harness(self, fail=False):
        account, quota = inputs()
        calls = []
        rpc = SimpleNamespace(close=lambda: calls.append("close"))
        def call(client, method, params, **kwargs):
            calls.append((method, params, kwargs))
            if fail and method == "account/read":
                raise RuntimeError("SYNTHETIC_SECRET_PROVIDER_BODY")
            return {"account/read": account, "account/rateLimits/read": quota}.get(method, {})
        transport = SimpleNamespace(RpcClient=lambda process: rpc, require_rpc_success=call)
        process = SimpleNamespace(pid=12345, stdin=io.BytesIO(), stdout=io.BytesIO(),
                                  wait=lambda **kwargs: calls.append("wait"))
        return calls, transport, process

    def test_only_native_metadata_methods_no_refresh_and_owned_process_cleanup(self):
        calls, transport, process = self.harness()
        with (patch.object(observer, "_environment", return_value={"HOME": "/synthetic"}),
              patch.object(observer, "_load_transport", return_value=transport),
              patch.object(observer, "_verified_bytes"),
              patch.object(observer.subprocess, "Popen", return_value=process) as launch,
              patch.object(observer.os, "killpg") as kill):
            sample = observer.CodexQuotaObserver(Path("/synthetic/collector.py"),
                            expected_namespace_sha256=NAMESPACE).read(serialized_read_only=True)
        self.assertEqual([item[0] for item in calls if isinstance(item, tuple)],
                         ["initialize", "initialized", "account/read", "account/rateLimits/read"])
        self.assertEqual(calls[2][1], {"refreshToken": False})
        self.assertEqual(calls[3][1], {"supportsLunaReserve": False,
                                      "excludeResetCreditDetails": True})
        self.assertTrue(launch.call_args.kwargs["start_new_session"])
        self.assertEqual(launch.call_args.args[0][1:], ["app-server", "--listen", "stdio://"])
        kill.assert_called_once_with(12345, signal.SIGTERM)
        self.assertTrue(process.stdout.closed)
        self.assertIn("close", calls)
        self.assertEqual(sample.account_namespace_sha256, NAMESPACE)

    def test_partial_rpc_refuses_redacts_and_releases_resources(self):
        calls, transport, process = self.harness(fail=True)
        instance = observer.CodexQuotaObserver(Path("/synthetic/collector.py"),
                                             expected_namespace_sha256=NAMESPACE)
        with (patch.object(observer, "_environment", return_value={}),
              patch.object(observer, "_load_transport", return_value=transport),
              patch.object(observer, "_verified_bytes"),
              patch.object(observer.subprocess, "Popen", return_value=process),
              patch.object(observer.os, "killpg")):
            with self.assertRaises(observer.CodexObserverError) as raised:
                instance.read(serialized_read_only=True)
        self.assertNotIn("SYNTHETIC_SECRET", str(raised.exception))
        self.assertNotIn("account/rateLimits/read", [c[0] for c in calls if isinstance(c, tuple)])
        self.assertTrue(process.stdin.closed)
        self.assertFalse(instance._lock.locked())

    def test_unserialized_or_overlapping_read_never_launches(self):
        _, transport, process = self.harness()
        instance = observer.CodexQuotaObserver(Path("/synthetic"), expected_namespace_sha256=NAMESPACE)
        # Every other step would succeed, so only the serialization gate can refuse.
        with (patch.object(observer, "_environment", return_value={}),
              patch.object(observer, "_load_transport", return_value=transport),
              patch.object(observer, "_verified_bytes"),
              patch.object(observer.os, "killpg"),
              patch.object(observer.subprocess, "Popen", return_value=process) as launch):
            with self.assertRaises(observer.CodexObserverError):
                instance.read()
            instance._lock.acquire()
            try:
                with self.assertRaises(observer.CodexObserverError):
                    instance.read(serialized_read_only=True)
            finally:
                instance._lock.release()
        launch.assert_not_called()

    def test_cleanup_escalates_after_timeout(self):
        process = SimpleNamespace(pid=12345, stdin=io.BytesIO(), stdout=io.BytesIO())
        with (patch.object(observer.os, "killpg") as kill,
              patch.object(observer.subprocess, "Popen") as unused):
            process.wait = unittest.mock.Mock(side_effect=[subprocess.TimeoutExpired("native", 3), 0])
            observer._stop(process)
        self.assertEqual([call.args[1] for call in kill.call_args_list], [signal.SIGTERM, signal.SIGKILL])
        unused.assert_not_called()
        self.assertTrue(process.stdout.closed)


if __name__ == "__main__":
    unittest.main()
