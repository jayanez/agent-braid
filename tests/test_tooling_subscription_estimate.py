# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from agent_braid import tooling_subscription_estimate as estimate


def _policy() -> dict:
    return {
        "schema": estimate.SCHEMA,
        "methodId": estimate.METHOD_ID,
        "nominalPeriodSeconds": estimate.PERIOD_SECONDS,
        "pricesEurPerMonth": {"codex": "100.00", "claude-code": "111.89"},
        "maxActiveSecondsPerHost": estimate.MAX_ACTIVE_SECONDS_PER_HOST,
        "reservationEur": "5.045",
        "budgetCeilingEur": "25.00",
        "decisionSha256": "a" * 64,
        "codexPriceSourceSha256": "b" * 64,
        "claudeCodePriceSourceSha256": "c" * 64,
    }


def _evidence(seconds: dict[str, int] | None = None) -> estimate.ActiveTimeEvidence:
    return estimate.ActiveTimeEvidence(
        registration_sha256="d" * 64, ledger_sha256="e" * 64,
        source_ref="trusted-active-time-snapshot", source_sha256="f" * 64,
        observed_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        seconds_by_host=seconds or {"codex": 57_600, "claude-code": 57_600},
    )


class SubscriptionEstimateTests(unittest.TestCase):
    def test_timestamp_must_be_valid_utc(self) -> None:
        evidence = _evidence()
        for stamp in ("not-a-timestamp", "2026-10-11T10:00:00", "2026-10-11T10:00:00+01:00"):
            with self.subTest(stamp=stamp):
                malformed = estimate.ActiveTimeEvidence(
                    evidence.registration_sha256, evidence.ledger_sha256, evidence.source_ref,
                    evidence.source_sha256, stamp, evidence.seconds_by_host)
                with self.assertRaises(estimate.EstimateError):
                    estimate.validate_active_time_evidence(malformed)

    def test_freshness_contract_rejects_stale_and_future_observations(self) -> None:
        now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)
        with self.assertRaisesRegex(estimate.EstimateError, "stale"):
            estimate.validate_observation_freshness("2026-10-11T11:00:00Z", now=now)
        with self.assertRaisesRegex(estimate.EstimateError, "future"):
            estimate.validate_observation_freshness("2026-10-11T12:01:00Z", now=now)
    def test_full_registered_time_reserves_exactly_owner_bound_amount(self) -> None:
        result = estimate.assess(_policy(), _evidence(), registration_sha256="d" * 64,
                                 ledger_sha256="e" * 64)
        self.assertEqual(result.reservation_eur, estimate.RESERVATION_EUR)
        self.assertEqual(result.allocated_upper_bound_eur, estimate.RESERVATION_EUR)
        self.assertEqual(result.remaining_reservation_eur, 0)
        report = result.as_dict()
        self.assertIsNone(report["allocatedSubscriptionCostEur"])
        self.assertIsNone(report["providerAccountingCostEur"])
        self.assertFalse(report["utilityClaimEligible"])

    def test_unknown_or_overrun_active_time_fails_closed(self) -> None:
        with self.assertRaises(estimate.EstimateError):
            estimate.assess(_policy(), _evidence({"codex": 1}), registration_sha256="d" * 64,
                            ledger_sha256="e" * 64)
        with self.assertRaises(estimate.EstimateError):
            estimate.assess(_policy(), _evidence({"codex": 57_601, "claude-code": 0}),
                            registration_sha256="d" * 64, ledger_sha256="e" * 64)

    def test_stale_registration_or_ledger_binding_fails_closed(self) -> None:
        with self.assertRaises(estimate.EstimateError):
            estimate.assess(_policy(), _evidence(), registration_sha256="1" * 64,
                            ledger_sha256="e" * 64)
        with self.assertRaises(estimate.EstimateError):
            estimate.assess(_policy(), _evidence(), registration_sha256="d" * 64,
                            ledger_sha256="1" * 64)

    def test_changed_convention_fails_closed(self) -> None:
        policy = _policy()
        policy["nominalPeriodSeconds"] += 1
        with self.assertRaises(estimate.EstimateError):
            estimate.validate_policy(policy)


if __name__ == "__main__":
    unittest.main()
