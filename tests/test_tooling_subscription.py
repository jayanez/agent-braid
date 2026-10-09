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


if __name__ == "__main__":
    unittest.main()
