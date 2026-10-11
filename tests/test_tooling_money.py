# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for additive v2 monetary accounting; no provider access."""
from dataclasses import replace
from decimal import Decimal, localcontext
import hashlib
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid.tooling_money import (
    AllocationMethodBinding,
    AllocationPolicyAttestation,
    AllocationShare,
    MoneyAccountingError,
    MoneyActivity,
    MoneyEvidence,
    MoneyLedger,
    MoneyReceipt,
    MoneyRoster,
    SourceAttestation,
    provider_accounting_total,
)
from tests.test_tooling_evaluation import _complete_ledger, _inputs, _known_costs, _registration, _registration_v3


_COVERAGE_START = "2026-10-09T10:00:00Z"
_COVERAGE_END = "2026-10-09T15:00:00Z"
_BILLING_START = "2026-10-01T00:00:00Z"
_BILLING_END = "2026-11-01T00:00:00Z"
_OBSERVED = "2026-11-02T00:00:00Z"


def _sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validated_registration(data=None):
    data = data or _registration()
    account_by_host = {
        host["name"]: host["modelIdentity"]["providerRoute"]["accountSha256"]
        if "modelIdentity" in host else _sha(f"{host['name']}-account")
        for host in data["hosts"]
    }
    data["billingPolicy"] = {
        "schema": "agent-braid-m45-subscription-policy-v1",
        "mode": "included-subscription-only",
        "additionalSpendCapEur": 0,
        "paidApiAllowed": False,
        "overageAllowed": False,
        "creditsAllowed": False,
        "autoRechargeAllowed": False,
        "hosts": [
            {"host": "codex", "authMethod": "chatgpt", "accountSha256": account_by_host["codex"]},
            {"host": "claude-code", "authMethod": "claude.ai", "accountSha256": account_by_host["claude-code"]},
        ],
    }
    return evaluation.validate_registration(
        data, expected_candidate_sha256=data["candidate"]["sha256"],
        expected_input_hashes=_inputs(data),
    )


def _roster(data=None):
    registration = _validated_registration(data)
    account_by_host = {
        item["host"]: item["accountSha256"]
        for item in registration.data["billingPolicy"]["hosts"]
    }
    activities = [MoneyActivity(
        "setup", "setup", "setup-cost-account", _sha("setup-cost-account"),
        started_at=_COVERAGE_START, ended_at=_COVERAGE_END,
    )]
    activities.extend(
        MoneyActivity(
            slot.slot_id, "attempt", f"account-{slot.host}", account_by_host[slot.host],
            host=slot.host, started_at=_COVERAGE_START, ended_at=_COVERAGE_END,
        )
        for slot in evaluation.generate_slots(registration)
    )
    activities.extend(
        MoneyActivity(
            f"reviewer:{reviewer_id}", "reviewer",
            f"reviewer-account-{reviewer_id}", _sha(f"reviewer-account:{reviewer_id}"),
            reviewer_id=reviewer_id, started_at=_COVERAGE_START, ended_at=_COVERAGE_END,
        )
        for reviewer_id in evaluation.expected_reviewer_participants(registration)
    )
    return MoneyRoster(registration, "cohort-2026-10", _COVERAGE_START, _COVERAGE_END,
                       tuple(activities))


def _allocation_method(roster):
    return AllocationMethodBinding(
        roster.registration_ref, roster.registration_sha256,
        "registered-method-identity", "method-document", _sha("method"),
        "cohort-usage-denominator", "registered-usage-unit",
    )


def _receipt(roster, activity, measure, *, amount=Decimal("0"), scope=None,
             method=None, share=None, source_amount=None, rate_card=None,
             source_identity=None):
    source_kind = {
        "actualAdditionalSpendEur": "invoice",
        "allocatedSubscriptionCostEur": "subscription-statement",
        "apiReferenceEstimateEur": "reference-rate-card",
    }[measure]
    scope_id = scope or f"{measure}-{activity.activity_id}"
    invoice = measure == "actualAdditionalSpendEur"
    estimate = measure == "apiReferenceEstimateEur"
    currency = "USD" if estimate else "EUR"
    native_amount = source_amount if source_amount is not None else (Decimal("2") if estimate else amount)
    registered_rate = roster.rate_cards_by_host.get(activity.host) if estimate else None
    if rate_card is not None:
        registered_rate = rate_card
    evidence = MoneyEvidence(
        source_kind=source_kind,
        source_ref=(source_identity or f"source-{_sha(f'{measure}:{activity.activity_id}')[:32]}"),
        source_sha256=_sha(source_identity or f"source-{measure}-{activity.activity_id}"),
        source_scope_id=scope_id,
        account_ref=activity.account_ref,
        account_sha256=activity.account_sha256,
        source_period_id="billing-month-2026-10",
        source_period_started_at=_BILLING_START,
        source_period_ended_at=_BILLING_END,
        coverage_period_id=roster.period_id,
        coverage_period_started_at=roster.period_started_at,
        coverage_period_ended_at=roster.period_ended_at,
        currency=currency,
        source_amount=native_amount,
        invoice_ref=f"invoice-{activity.activity_id}" if invoice else None,
        invoice_sha256=_sha(f"invoice-{activity.activity_id}") if invoice else None,
        fx_rate_to_eur=Decimal("0.9") if estimate else Decimal("1"),
        fx_source_ref="fx-eur-rate" if estimate else None,
        fx_source_sha256=_sha("fx rate") if estimate else None,
        rate_card_ref=registered_rate[0] if estimate and registered_rate else None,
        rate_card_sha256=registered_rate[1] if estimate and registered_rate else None,
        calculation_inputs_sha256=_sha(f"inputs-{measure}-{activity.activity_id}")
        if estimate or method is not None else None,
    )
    return MoneyReceipt(
        activity.activity_id, measure, amount, _OBSERVED, evidence,
        allocation_method=method, allocation_share=share,
    )


class _SourceVerifier:
    def __init__(self, *, wrong_digest=False):
        self.wrong_digest = wrong_digest
        self.calls = 0

    def verify_source(self, receipt):
        self.calls += 1
        digest = "0" * 64 if self.wrong_digest else receipt.sha256
        return SourceAttestation("synthetic-source-verifier", digest, _OBSERVED)


class _PolicyVerifier:
    def __init__(self, *, wrong_digest=False):
        self.wrong_digest = wrong_digest
        self.calls = 0

    def verify_registered_method(self, binding):
        self.calls += 1
        digest = "0" * 64 if self.wrong_digest else binding.sha256
        return AllocationPolicyAttestation("synthetic-policy-verifier", digest, _OBSERVED)


class MoneyAccountingTests(unittest.TestCase):
    def test_v3_unknown_reference_rates_reject_estimates_and_missing_receipts_remain_incomplete(self):
        data = _registration_v3()
        for item in data["costRates"]["byHost"]:
            item.update(inputEurPerMillionTokens=None, outputEurPerMillionTokens=None,
                        recordId=None, sha256=None)
        roster = _roster(data)
        self.assertEqual(roster.rate_cards_by_host, {})
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        attempt = next(item for item in roster.activities if item.kind == "attempt")
        fabricated = _receipt(
            roster, attempt, "apiReferenceEstimateEur", amount=Decimal("2"),
            rate_card=("fabricated-rate-card", _sha("fabricated-rate-card")),
        )
        with self.assertRaisesRegex(MoneyAccountingError, "no registered token rates"):
            ledger.add(fabricated)
        self.assertEqual(ledger.history, ())

        summary = ledger.summarize()
        self.assertFalse(summary.required_measures_complete)
        self.assertFalse(summary.technical_required_measures_complete)
        self.assertIsNone(summary.actual_provider_spend_eur)
        self.assertIsNone(summary.api_reference_estimate_eur)
        self.assertTrue(summary.stop_required)
        attempt_ledger, ratings = _complete_ledger(roster.registration)
        eligibility = evaluation.assess_utility_eligibility(
            roster.registration, attempt_ledger, setup_costs=_known_costs(),
            human_ratings=ratings, monetary_summary=summary,
            expected_monetary_roster_sha256=roster.sha256,
        )
        self.assertFalse(eligibility.positive_claim_eligible)
        self.assertTrue(any("subscription economic cost amounts are unavailable" in reason
                            for reason in eligibility.reasons))

    def test_v3_unknown_rates_preserve_complete_technical_cash_and_allocation_but_not_human_economics(self):
        # Reuse the full-cost registration, roster, and synthetic source attestations
        # so this isolates missing reference pricing from required actual measures.
        from tests.test_tooling_full_cost import (
            _ScopeVerifier, _TimeVerifier, _WallVerifier, _filled_money,
            _registration as full_cost_registration, _roster as full_cost_roster,
            _time_receipts, _wall_receipts,
        )
        from agent_braid.tooling_full_cost import complete_full_cost

        prepared = full_cost_registration(technical_capture=True, reviewer_fee="unknown")
        for item in prepared.data["costRates"]["byHost"]:
            item.update(inputEurPerMillionTokens=None, outputEurPerMillionTokens=None,
                        recordId=None, sha256=None)
        registration_data = prepared.data
        registration = evaluation.validate_registration(
            registration_data,
            expected_candidate_sha256=registration_data["candidate"]["sha256"],
            expected_input_hashes=_inputs(registration_data),
        )
        roster = full_cost_roster(registration)
        self.assertEqual(roster.rate_cards_by_host, {})
        money_ledger, money_summary = _filled_money(roster)
        self.assertEqual(218, len(money_ledger.history))
        self.assertTrue(money_summary.technical_required_measures_complete)
        self.assertFalse(money_summary.technical_stop_required)
        self.assertIsNotNone(money_summary.actual_provider_spend_eur)
        self.assertIsNotNone(money_summary.allocated_subscription_cost_eur)
        self.assertIsNone(money_summary.api_reference_estimate_eur)

        attempt = next(item for item in roster.activities if item.kind == "attempt")
        fabricated = _receipt(
            roster, attempt, "apiReferenceEstimateEur", amount=Decimal("2"),
            rate_card=("fabricated-rate-card", _sha("fabricated-rate-card")),
        )
        with self.assertRaisesRegex(MoneyAccountingError, "no registered token rates"):
            money_ledger.add(fabricated)
        self.assertEqual(218, len(money_ledger.history))

        attempts, ratings = _complete_ledger(registration)
        completed = complete_full_cost(
            registration, attempts, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertTrue(completed.technical_required_measures_complete)
        self.assertFalse(completed.technical_stop_required)
        self.assertFalse(completed.full_economic_cost_complete)
        self.assertIsNotNone(completed.actual_provider_spend_eur)
        self.assertIsNotNone(completed.allocated_subscription_cost_eur)
        self.assertIsNone(completed.api_reference_estimate_eur)
        eligibility = evaluation.assess_utility_eligibility(
            registration, attempts, setup_costs=_known_costs(), human_ratings=ratings,
            monetary_summary=completed, expected_monetary_roster_sha256=roster.sha256,
        )
        self.assertFalse(eligibility.positive_claim_eligible)
        self.assertTrue(any("human evaluation is deferred" in reason
                            for reason in eligibility.reasons))

    def test_provider_cash_excludes_reviewer_fees_and_unknown_provider_coverage(self):
        roster = _roster()
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        for activity in roster.activities:
            amount = Decimal("7") if activity.kind == "reviewer" else Decimal("0.01")
            ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=amount))
        summary = ledger.summarize()
        self.assertEqual(Decimal("15.09"), summary.actual_additional_spend_eur)
        self.assertEqual(Decimal("1.09"), summary.actual_provider_spend_eur)
        self.assertIsNone(summary.provider_accounting_cost_eur)
        self.assertEqual("1.09", summary.as_dict()["actualProviderSpendEur"])
        incomplete = MoneyLedger(roster, source_verifier=_SourceVerifier())
        for activity in roster.activities[1:]:
            incomplete.add(_receipt(roster, activity, "actualAdditionalSpendEur"))
        self.assertIsNone(incomplete.summarize().actual_provider_spend_eur)

    def test_exact_provider_total_preserves_tiny_cap_excess_under_low_precision(self):
        with localcontext() as context:
            context.prec = 2
            total = provider_accounting_total(Decimal("25"), Decimal("0.0000000000000000000000000001"))
        self.assertEqual(Decimal("25.0000000000000000000000000001"), total)
        self.assertIsNone(provider_accounting_total(None, Decimal("25")))
        for value in (Decimal("NaN"), Decimal("-1"), Decimal("1e100")):
            with self.assertRaises(MoneyAccountingError):
                provider_accounting_total(Decimal("0"), value)

    def test_actual_estimate_and_allocation_measures_stay_separate(self):
        roster = _roster()
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        for activity in roster.activities:
            ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=Decimal("0")))
        for activity in roster.activities:
            if activity.kind == "attempt":
                ledger.add(_receipt(roster, activity, "apiReferenceEstimateEur", amount=Decimal("2")))

        summary = ledger.summarize()
        self.assertTrue(summary.required_measures_complete)
        self.assertFalse(summary.full_economic_cost_complete)
        self.assertEqual(
            summary.full_economic_cost_status,
            "pending-registered-cost-scope-and-human-cost-fields",
        )
        self.assertEqual(summary.actual_additional_spend_eur, Decimal("0"))
        self.assertEqual(summary.actual_additional_spend_cap_eur, Decimal("0"))
        self.assertIn("paid-review", roster.as_dict()["actualAdditionalSpendCapScope"])
        self.assertFalse(summary.cap_violation)
        self.assertFalse(summary.stop_required)
        self.assertIsNone(summary.allocated_subscription_cost_eur)
        self.assertEqual(summary.api_reference_estimate_eur, Decimal("216"))
        self.assertEqual(summary.as_dict()["actualAdditionalSpendEur"], "0")
        self.assertEqual(len(summary.receipt_sha256s), 219)

    def test_missing_registered_cost_component_is_unknown_and_stops(self):
        roster = _roster()
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        for activity in roster.activities[:-1]:
            ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=Decimal("0")))

        summary = ledger.summarize()
        self.assertFalse(summary.required_measures_complete)
        self.assertFalse(summary.full_economic_cost_complete)
        self.assertIsNone(summary.actual_additional_spend_eur)
        self.assertEqual(summary.observed_additional_spend_subtotal_eur, Decimal("0"))
        self.assertIsNone(summary.cap_violation)
        self.assertTrue(summary.stop_required)
        self.assertEqual(summary.missing_required,
                         (("reviewer:rater-two", "actualAdditionalSpendEur"),))

    def test_positive_actual_charge_is_retained_and_violates_registered_zero_cap(self):
        roster = _roster()
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        ledger.add(_receipt(roster, roster.activities[1], "actualAdditionalSpendEur",
                            amount=Decimal("0.01")))

        summary = ledger.summarize()
        self.assertIsNone(summary.actual_additional_spend_eur)
        self.assertEqual(summary.observed_additional_spend_subtotal_eur, Decimal("0.01"))
        self.assertIs(summary.cap_violation, True)
        self.assertTrue(summary.stop_required)
        self.assertEqual(len(ledger.history), 1)

    def test_source_attestation_must_bind_exact_receipt_before_publication(self):
        roster = _roster()
        verifier = _SourceVerifier(wrong_digest=True)
        ledger = MoneyLedger(roster, source_verifier=verifier)
        with self.assertRaisesRegex(MoneyAccountingError, "exact monetary receipt"):
            ledger.add(_receipt(roster, roster.activities[0], "actualAdditionalSpendEur"))
        self.assertEqual(ledger.history, ())

    def test_source_scope_cannot_be_reused_to_double_count(self):
        roster = _roster()
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        first = _receipt(roster, roster.activities[0], "actualAdditionalSpendEur", scope="same-invoice-line")
        second = _receipt(roster, roster.activities[1], "actualAdditionalSpendEur", scope="same-invoice-line")
        ledger.add(first)
        with self.assertRaisesRegex(MoneyAccountingError, "source scope"):
            ledger.add(second)
        self.assertEqual(len(ledger.history), 1)

    def test_allocation_registration_binding_and_policy_verification_are_separate(self):
        roster = _roster()
        activity = next(item for item in roster.activities if item.kind == "attempt")
        method = _allocation_method(roster)
        receipt = _receipt(
            roster, activity, "allocatedSubscriptionCostEur", amount=Decimal("0.5"),
            method=method, share=AllocationShare(Decimal("1"), Decimal("108")),
        )
        source_verifier = _SourceVerifier()
        no_policy = MoneyLedger(roster, source_verifier=source_verifier)
        with self.assertRaisesRegex(MoneyAccountingError, "separate verifier"):
            no_policy.add(receipt)
        self.assertEqual(no_policy.history, ())
        self.assertEqual(source_verifier.calls, 0)

        drifted_method = replace(method, registration_sha256=_sha("different registration"))
        drifted_receipt = replace(receipt, allocation_method=drifted_method)
        policy_verifier = _PolicyVerifier()
        ledger = MoneyLedger(roster, source_verifier=source_verifier,
                             allocation_policy_verifier=policy_verifier)
        with self.assertRaisesRegex(MoneyAccountingError, "frozen cohort registration"):
            ledger.add(drifted_receipt)
        self.assertEqual(policy_verifier.calls, 0)
        self.assertEqual(ledger.history, ())

    def test_allocation_denominator_is_capped_without_partial_publication(self):
        roster = _roster()
        attempts = [item for item in roster.activities if item.kind == "attempt"]
        setup = replace(roster.activities[0], account_ref=attempts[0].account_ref,
                        account_sha256=attempts[0].account_sha256)
        roster = replace(roster, activities=(setup, *roster.activities[1:]))
        method = _allocation_method(roster)
        source_verifier, policy_verifier = _SourceVerifier(), _PolicyVerifier()
        ledger = MoneyLedger(roster, source_verifier=source_verifier,
                             allocation_policy_verifier=policy_verifier)
        attempts = [item for item in roster.activities if item.kind == "attempt"]
        for activity in attempts:
            ledger.add(_receipt(
                roster, activity, "allocatedSubscriptionCostEur", amount=Decimal("0.5"),
                method=method, share=AllocationShare(Decimal("1"), Decimal("54")),
                source_identity="one-registered-subscription-statement",
            ))
        before = len(ledger.history)
        with self.assertRaisesRegex(MoneyAccountingError, "exceed their registered denominator"):
            ledger.add(_receipt(
                roster, roster.activities[0], "allocatedSubscriptionCostEur", amount=Decimal("0.5"),
                method=method, share=AllocationShare(Decimal("1"), Decimal("54")),
                source_identity="one-registered-subscription-statement",
            ))
        self.assertEqual(len(ledger.history), before)
        self.assertEqual(policy_verifier.calls, 1)
        self.assertEqual(source_verifier.calls, 108)

    def test_independent_accounts_and_source_bills_have_independent_denominators(self):
        roster = _roster()
        method = _allocation_method(roster)
        ledger = MoneyLedger(
            roster, source_verifier=_SourceVerifier(),
            allocation_policy_verifier=_PolicyVerifier(),
        )
        attempts = [item for item in roster.activities if item.kind == "attempt"]
        first, second = attempts[0], attempts[1]
        for activity, bill in ((first, "codex-subscription"), (second, "claude-subscription")):
            ledger.add(_receipt(
                roster, activity, "allocatedSubscriptionCostEur", amount=Decimal("0.5"),
                method=method, share=AllocationShare(Decimal("1"), Decimal("1")),
                source_identity=bill,
            ))
        self.assertEqual(len(ledger.history), 2)

    def test_wrong_method_attestation_does_not_publish_allocation(self):
        roster = _roster()
        method = _allocation_method(roster)
        ledger = MoneyLedger(
            roster, source_verifier=_SourceVerifier(),
            allocation_policy_verifier=_PolicyVerifier(wrong_digest=True),
        )
        receipt = _receipt(
            roster, roster.activities[0], "allocatedSubscriptionCostEur", amount=Decimal("1"),
            method=method, share=AllocationShare(Decimal("1"), Decimal("111")),
        )
        with self.assertRaisesRegex(MoneyAccountingError, "exact registered method"):
            ledger.add(receipt)
        self.assertEqual(ledger.history, ())

    def test_monthly_source_period_is_separate_from_exact_cohort_coverage(self):
        roster = _roster()
        verifier = _SourceVerifier()
        ledger = MoneyLedger(roster, source_verifier=verifier)
        receipt = _receipt(roster, roster.activities[0], "actualAdditionalSpendEur")
        ledger.add(receipt)
        self.assertEqual(receipt.evidence.source_period_started_at, _BILLING_START)
        self.assertEqual(receipt.evidence.coverage_period_started_at, _COVERAGE_START)
        self.assertEqual(verifier.calls, 1)
        second = _receipt(roster, roster.activities[1], "actualAdditionalSpendEur")
        outside_coverage = replace(second.evidence, coverage_period_id="another-period")
        with self.assertRaisesRegex(MoneyAccountingError, "coverage differs"):
            ledger.add(replace(second, evidence=outside_coverage))

    def test_api_estimates_bind_registered_rate_card_and_fx_inputs(self):
        roster = _roster()
        activity = next(item for item in roster.activities if item.kind == "attempt")
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        receipt = _receipt(roster, activity, "apiReferenceEstimateEur", amount=Decimal("2"))
        wrong_rate = ("unregistered-rate", _sha("unregistered-rate"))
        drifted = _receipt(roster, activity, "apiReferenceEstimateEur", amount=Decimal("2"),
                           scope="different-estimate-inputs", rate_card=wrong_rate)
        with self.assertRaisesRegex(MoneyAccountingError, "registered host rate"):
            ledger.add(drifted)
        ledger.add(receipt)
        self.assertEqual(len(ledger.history), 1)

    def test_roster_requires_exact_registered_slots_reviewer_ids_and_registration_integrity(self):
        roster = _roster()
        with self.assertRaisesRegex(MoneyAccountingError, "exact 108 registered slots"):
            replace(roster, activities=roster.activities[:-3])
        reviewer = roster.activities[-1]
        with self.assertRaisesRegex(MoneyAccountingError, "exact frozen reviewer IDs"):
            replace(roster, activities=(*roster.activities[:-1],
                                        replace(reviewer, reviewer_id="unregistered-reviewer",
                                                activity_id="reviewer:unregistered-reviewer")))
        roster.registration.data["registrationId"] = "tampered-registration"
        with self.assertRaisesRegex(MoneyAccountingError, "drifted"):
            roster.validate()

    def test_source_period_and_allocation_share_inputs_are_bounded(self):
        roster = _roster()
        activity = roster.activities[0]
        with self.assertRaisesRegex(MoneyAccountingError, "contain the cohort coverage"):
            replace(_receipt(roster, activity, "actualAdditionalSpendEur").evidence,
                    source_period_started_at="2026-10-10T00:00:00Z")
        with self.assertRaisesRegex(MoneyAccountingError, "exceeds denominator"):
            AllocationShare(Decimal("2"), Decimal("1"))

    def test_decimal_precision_exponents_and_exact_totals_are_bounded(self):
        roster = _roster()
        with self.assertRaisesRegex(MoneyAccountingError, "precision or exponent"):
            _receipt(roster, roster.activities[0], "actualAdditionalSpendEur",
                     amount=Decimal("1e1000000"))
        with self.assertRaisesRegex(MoneyAccountingError, "precision or exponent"):
            AllocationShare(Decimal("1e-1000000"), Decimal("1"))

        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier())
        amount = Decimal("0.123456789012345678901234567")
        with localcontext() as context:
            context.prec = 3
            for activity in roster.activities:
                ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=amount))
            self.assertEqual(
                str(ledger.summarize().actual_additional_spend_eur),
                "13.703703580370370358037036937",
            )

    def test_verifier_reentrancy_and_concurrent_duplicate_are_serialized(self):
        roster = _roster()
        receipt = _receipt(roster, roster.activities[0], "actualAdditionalSpendEur")
        # Event-like synchronization uses threading primitives without provider work.
        import threading
        entered = threading.Event()
        release = threading.Event()
        outcomes = []

        class WaitingVerifier(_SourceVerifier):
            def verify_source(self, value):
                self.calls += 1
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("synthetic verifier release timed out")
                return SourceAttestation("synthetic-source-verifier", value.sha256, _OBSERVED)

        verifier = WaitingVerifier()
        ledger = MoneyLedger(roster, source_verifier=verifier)
        def add():
            try:
                ledger.add(receipt)
                outcomes.append("accepted")
            except MoneyAccountingError:
                outcomes.append("rejected")
        first = threading.Thread(target=add)
        second = threading.Thread(target=add)
        first.start()
        self.assertTrue(entered.wait(5))
        second.start()
        release.set()
        first.join(5)
        second.join(5)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertCountEqual(outcomes, ["accepted", "rejected"])
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(len(ledger.history), 1)

    def test_reentrant_verifier_cannot_publish_nested_receipt(self):
        roster = _roster()
        receipt = _receipt(roster, roster.activities[0], "actualAdditionalSpendEur")
        class Reentrant:
            def verify_source(self, value):
                ledger.add(value)
        ledger = MoneyLedger(roster, source_verifier=Reentrant())
        with self.assertRaisesRegex(MoneyAccountingError, "cannot reenter"):
            ledger.add(receipt)
        self.assertEqual(ledger.history, ())


if __name__ == "__main__":
    unittest.main()
