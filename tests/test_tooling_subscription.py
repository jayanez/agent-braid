# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic offline policy and observation controls."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
import unittest

from agent_braid import tooling_subscription as subscription


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _policy():
    return {"schema": subscription.POLICY_SCHEMA, "mode": "included-subscription-only",
            "additionalSpendCapEur": 0, "paidApiAllowed": False, "overageAllowed": False,
            "creditsAllowed": False, "autoRechargeAllowed": False,
            "hosts": [{"host": "codex", "authMethod": "chatgpt", "accountSha256": _sha("a")},
                      {"host": "claude-code", "authMethod": "claude.ai", "accountSha256": _sha("b")}]}


def _native_policy():
    return {"schema": subscription.NATIVE_PROCESS_POLICY_SCHEMA,
            "mode": "included-subscription-only", "scope": "registered-native-process-only",
            "accountWideApiBilling": "unknown-out-of-scope", "additionalSpendCapEur": 0,
            "maxAgeSeconds": 30, "paidApiAllowed": False, "overageAllowed": False,
            "creditsAllowed": False, "autoRechargeAllowed": False,
            "hosts": [{"host": "codex", "authMethod": "chatgpt", "accountSha256": _sha("a"),
                       "accountNamespaceSha256": _sha("a-ns")},
                      {"host": "claude-code", "authMethod": "claude.ai", "accountSha256": _sha("b"),
                       "accountNamespaceSha256": _sha("b-ns")}],
            "processContracts": {"slot-1": {"host": "codex", "hostBuildSha256": _sha("build"),
                "candidateArtifactSha256": _sha("artifact"), "executableSha256": _sha("exe"),
                "configSha256": _sha("config"), "argvSha256": _sha("argv"),
                "modelIdentitySha256": _sha("model")}},
            "observer": {"sourceRef": "observer", "sourceSha256": _sha("observer"),
                "verifierRef": "observer-verifier", "verifierSha256": _sha("observer-verifier"),
                "continuousPerOperationControlRequired": True},
            "cashSource": {"sourceRef": "cash-ledger", "sourceSha256": _sha("cash"),
                "verifierRef": "cash-verifier", "verifierSha256": _sha("cash-verifier"),
                "cohortBindingRequired": True}}


def _native_observation(binding, now, phase="prelaunch"):
    cash = subscription.CohortCashObservation(binding.registration_sha256, 0, True,
        ("slot-1",) if phase != "prelaunch" else (), phase == "completed",
        binding.cash_source_ref, binding.cash_source_sha256, binding.cash_verifier_ref,
        binding.cash_verifier_sha256, now)
    return subscription.NativeProcessRouteObservation(binding, phase, "chatgpt",
        "included-subscription-quota", "unknown-out-of-scope", True, True, False, False, False,
        False, False, False, True, True, True,
        1234 if phase != "prelaunch" else None,
        _sha("process-birth") if phase != "prelaunch" else None, 0,
        binding.observer_source_ref, binding.observer_source_sha256,
        binding.observer_verifier_ref, binding.observer_verifier_sha256, now, cash)


class SubscriptionPolicyTests(unittest.TestCase):
    def test_policy_hash_and_binding_are_stable_and_account_specific(self):
        policy = _policy()
        registration = {"billingPolicy": policy}
        bound = subscription.binding_from_registration(registration, "slot-1", "codex")
        self.assertEqual(subscription.policy_sha256(policy), bound.policy_sha256)
        self.assertEqual(bound.account_sha256, _sha("a"))
        self.assertEqual(subscription.binding_from_dict(bound.as_dict()), bound)
        self.assertIsNone(subscription.binding_from_registration({}, "slot-1", "codex"))

    def test_valid_observation_and_freshness(self):
        now = datetime.now(timezone.utc)
        policy = _policy()
        registration = {"billingPolicy": policy}
        binding = subscription.binding_from_registration(registration, "slot-1", "codex")
        observed = subscription.SubscriptionObservation(binding, "chatgpt", True, False, False,
            False, False, True, 0, "local-account-settings", _sha("source"), now)
        self.assertTrue(subscription.check_observation(observed, binding, now))
        self.assertEqual(subscription.observation_from_dict(observed.as_dict()), observed)
        self.assertTrue(subscription.check_observation(replace(observed, observed_at=now - timedelta(seconds=60)), binding, now))

    def test_rejects_paid_unknown_inactive_stale_and_cross_slot_states(self):
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _policy()}, "slot-1", "codex")
        base = subscription.SubscriptionObservation(binding, "chatgpt", True, False, False,
            False, False, True, 0, "settings", _sha("source"), now)
        unsafe = [replace(base, extra_usage_enabled=True), replace(base, api_billing_enabled=True),
                  replace(base, api_billing_enabled=None),
                  replace(base, credits_enabled=True), replace(base, auto_recharge_enabled=True),
                  replace(base, subscription_active=False), replace(base, quota_available=None),
                  replace(base, additional_spend_eur=0.01),
                  replace(base, observed_at=now + timedelta(seconds=1)),
                  replace(base, observed_at=now - timedelta(seconds=61)),
                  replace(base, binding=replace(binding, slot_id="slot-2"))]
        for observation in unsafe:
            with self.subTest(observation=observation):
                with self.assertRaises(subscription.SubscriptionError):
                    subscription.check_observation(observation, binding, now)

    def test_rejects_malformed_source_and_auth_method(self):
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _policy()}, "slot-1", "codex")
        base = subscription.SubscriptionObservation(binding, "chatgpt", True, False, False,
            False, False, True, 0, "settings", _sha("source"), now)
        for observation in (replace(base, source_sha256="bad"), replace(base, source_ref=" "),
                            replace(base, auth_method="api")):
            with self.assertRaises(subscription.SubscriptionError):
                subscription.check_observation(observation, binding, now)

    def test_malformed_shapes_timestamps_and_unknown_serializer_fields_raise_domain_error(self):
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _policy()}, "slot-1", "codex")
        base = subscription.SubscriptionObservation(binding, "chatgpt", True, False, False,
            False, False, True, 0, "settings", _sha("source"), now)
        for host_value in ({"host": "codex"}, ["codex"], 2):
            malformed = _policy()
            malformed["hosts"][0]["host"] = host_value
            with self.subTest(host=host_value), self.assertRaises(subscription.SubscriptionError):
                subscription.policy_sha256(malformed)
        for malformed_binding in (None, "invalid", {"host": "codex"}):
            with self.subTest(binding=malformed_binding), self.assertRaises(subscription.SubscriptionError):
                subscription.check_observation(replace(base, binding=malformed_binding), binding, now)
        for bad_now in ("now", datetime.now()):
            with self.subTest(now=bad_now), self.assertRaises(subscription.SubscriptionError):
                subscription.check_observation(base, binding, bad_now)
        invalid_times = ("not-a-date", "2026-01-01T00:00:00")
        for stamp in invalid_times:
            serialized = base.as_dict()
            serialized["observedAt"] = stamp
            with self.subTest(timestamp=stamp), self.assertRaises(subscription.SubscriptionError):
                subscription.observation_from_dict(serialized)
        serialized = base.as_dict()
        serialized["unexpected"] = "field"
        with self.assertRaises(subscription.SubscriptionError):
            subscription.observation_from_dict(serialized)
        serialized_binding = binding.as_dict()
        serialized_binding["unexpected"] = "field"
        with self.assertRaises(subscription.SubscriptionError):
            subscription.binding_from_dict(serialized_binding)

    def test_native_v2_binding_fresh_observation_and_strict_round_trip(self):
        now = datetime.now(timezone.utc)
        registration = {"billingPolicy": _native_policy()}
        binding = subscription.binding_from_registration(registration, "slot-1", "codex")
        self.assertIsInstance(binding, subscription.NativeProcessRouteBinding)
        self.assertEqual(binding.account_namespace_sha256, _sha("a-ns"))
        observation = _native_observation(binding, now)
        self.assertTrue(subscription.check_observation(observation, binding, now))
        self.assertEqual(subscription.binding_from_dict(binding.as_dict()), binding)
        self.assertEqual(subscription.observation_from_dict(observation.as_dict()), observation)
        self.assertEqual(subscription.policy_sha256(_native_policy()), binding.policy_sha256)

    def test_native_v2_running_and_completed_lifecycle_with_fresh_cash(self):
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _native_policy()}, "slot-1", "codex")
        running = _native_observation(binding, now, "running")
        completed = _native_observation(binding, now, "completed")
        self.assertTrue(subscription.check_observation(running, binding, now))
        self.assertTrue(subscription.check_observation(completed, binding, now))
        stale_cash = replace(running.cash, observed_at=now - timedelta(seconds=31))
        with self.assertRaises(subscription.SubscriptionError):
            subscription.check_cash_observation(stale_cash, binding, "running", now, 60)
        for invalid in (None, {"bad": "cash"}):
            with self.subTest(cash=invalid), self.assertRaises(subscription.SubscriptionError):
                subscription.check_observation(replace(running, cash=invalid), binding, now)
        with self.assertRaises(subscription.SubscriptionError):
            replace(running, cash=None).as_dict()

    def test_native_v2_refuses_unknowns_provenance_cash_drift_and_bad_lifecycle(self):
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _native_policy()}, "slot-1", "codex")
        base = _native_observation(binding, now)
        unsafe = [replace(base, account_wide_api_billing="false"),
                  replace(base, api_credential_available=True),
                  replace(base, provider_override_available=True),
                  replace(base, fallback_available=True),
                  replace(base, per_operation_gate_active=False),
                  replace(base, observer_connected=False),
                  replace(base, verifier_sha256=_sha("forged")),
                  replace(base, observed_at=now - timedelta(seconds=31)),
                  replace(base, observed_at=now + timedelta(seconds=1)),
                  replace(base, cash=replace(base.cash, additional_cash_eur=0.01)),
                  replace(base, cash=replace(base.cash, source_ref="route-selected")),
                  replace(base, phase="running", process_id=None, process_birth_sha256=None)]
        for observation in unsafe:
            with self.subTest(observation=observation), self.assertRaises(subscription.SubscriptionError):
                subscription.check_observation(observation, binding, now)

    def test_native_v2_policy_slot_binding_and_serializers_fail_closed(self):
        malformed = _native_policy()
        malformed["accountWideApiBilling"] = False
        with self.assertRaises(subscription.SubscriptionError):
            subscription.policy_sha256(malformed)
        malformed = _native_policy()
        malformed["observer"]["continuousPerOperationControlRequired"] = False
        with self.assertRaises(subscription.SubscriptionError):
            subscription.policy_sha256(malformed)
        malformed = _native_policy()
        malformed["cashSource"]["sourceRef"] = malformed["observer"]["sourceRef"]
        malformed["cashSource"]["sourceSha256"] = malformed["observer"]["sourceSha256"]
        with self.assertRaises(subscription.SubscriptionError):
            subscription.policy_sha256(malformed)
        malformed = _native_policy()
        malformed["hosts"][0]["host"] = []
        with self.assertRaises(subscription.SubscriptionError):
            subscription.policy_sha256(malformed)
        malformed = _native_policy()
        malformed["processContracts"]["slot-1"]["host"] = []
        with self.assertRaises(subscription.SubscriptionError):
            subscription.policy_sha256(malformed)
        with self.assertRaises(subscription.SubscriptionError):
            subscription.binding_from_registration({"billingPolicy": _native_policy()}, "missing", "codex")
        now = datetime.now(timezone.utc)
        binding = subscription.binding_from_registration({"billingPolicy": _native_policy()}, "slot-1", "codex")
        serialized = _native_observation(binding, now).as_dict()
        serialized["unexpected"] = 1
        with self.assertRaises(subscription.SubscriptionError):
            subscription.observation_from_dict(serialized)
        malformed_binding = binding.as_dict()
        malformed_binding["host"] = []
        with self.assertRaises(subscription.SubscriptionError):
            subscription.native_binding_from_dict(malformed_binding)


if __name__ == "__main__":
    unittest.main()
