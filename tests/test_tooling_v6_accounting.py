# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic v6 accounting regressions; no cash, reviewer or provider observations."""
import copy
import hashlib
import json
import unittest
from decimal import Decimal

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_full_cost as full_cost
from agent_braid import tooling_money as money
from agent_braid import tooling_subscription_estimate as estimate
from tests.test_tooling_registration_v6 import registration_v6, validated_v6
from tests.test_tooling_full_cost import (
    _registration_v5, _roster, _SourceVerifier, _ScopeVerifier, _TimeVerifier,
    _WallVerifier, _time_receipts, _wall_receipts,
)
from tests.test_tooling_evaluation import _known_costs, _sha
from tests.test_tooling_money import _receipt


def registration():
    data = registration_v6()
    data["fullCostScope"] = copy.deepcopy(_registration_v5().data["fullCostScope"])
    return validated_v6(data)


class V6AccountingTests(unittest.TestCase):
    def test_unknown_reviewer_fees_are_a_technical_scope_without_actual_allocation(self):
        reg = registration()
        scope = full_cost.FullCostScope.from_registration(reg)
        self.assertIsNotNone(scope)
        self.assertTrue(scope.technical_only)
        self.assertEqual({"unknown"}, {fee for _, fee in scope.reviewer_fee_applicability})
        data = copy.deepcopy(reg.data)
        data["fullCostScope"]["reviewerFees"][0]["applicability"] = "unpaid"
        with self.assertRaises(full_cost.FullCostError):
            full_cost.FullCostScope.from_registration(validated_v6(data))

    def test_missing_money_stays_unknown_and_lists_every_setup_and_attempt_measure(self):
        roster = _roster(registration())
        result = money.MoneyLedger(roster, source_verifier=_SourceVerifier()).summarize()
        self.assertEqual(218, len(result.missing_technical_required))
        self.assertEqual({"setup", *(slot.slot_id for slot in evaluation.generate_slots(roster.registration))},
                         {activity for activity, _ in result.missing_technical_required})
        self.assertIsNone(result.actual_additional_spend_eur)
        self.assertIsNone(result.allocated_subscription_cost_eur)
        self.assertIsNone(result.provider_accounting_cost_eur)
        self.assertIsNone(result.stop_required)
        self.assertIsNone(result.technical_stop_required)
        self.assertIsNone(result.technical_required_measures_complete)

    def test_roster_policy_digest_keeps_source_schema_and_rejects_mutation(self):
        reg = registration()
        roster = _roster(reg)
        expected = hashlib.sha256(json.dumps(reg.data["billingPolicy"], sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(expected, roster.as_dict()["billingPolicySha256"])
        reg.data["billingPolicy"]["scope"] = "different-scope"
        with self.assertRaises(money.MoneyAccountingError):
            roster.as_dict()

    def test_abstract_reviewer_time_requires_identity_addendum(self):
        reg = registration()
        roster = _roster(reg)
        monetary = money.MoneyLedger(roster, source_verifier=_SourceVerifier())
        role = evaluation.expected_reviewer_participants(reg)[0]
        receipt = full_cost.HumanTimeReceipt(role, (evaluation.generate_slots(reg)[0].slot_id,),
            "2026-10-09T10:00:00Z", "2026-10-09T10:01:00Z", "synthetic-time", _sha("time"))
        with self.assertRaisesRegex(full_cost.FullCostError, "identity-bound human-rating addendum"):
            full_cost.complete_full_cost(reg, evaluation.new_ledger(reg), roster, monetary,
                monetary.summarize(), setup_costs=None, human_time_receipts=(receipt,),
                scope_verifier=None, time_verifier=None)

    def test_known_positive_cash_stops_even_with_incomplete_cohort(self):
        roster = _roster(registration())
        ledger = money.MoneyLedger(roster, source_verifier=_SourceVerifier())
        setup = roster.activity_by_id["setup"]
        ledger.add(_receipt(roster, setup, "actualAdditionalSpendEur", amount=Decimal("0.01")))
        result = ledger.summarize()
        self.assertIsNone(result.actual_additional_spend_eur)
        self.assertEqual(Decimal("0.01"), result.observed_additional_spend_subtotal_eur)
        self.assertTrue(result.cap_violation)
        self.assertTrue(result.technical_cap_violation)
        self.assertTrue(result.stop_required)
        self.assertTrue(result.technical_stop_required)

    def test_reviewer_money_requires_real_identity_addendum_before_verifier_call(self):
        roster = _roster(registration())
        verifier = _SourceVerifier()
        ledger = money.MoneyLedger(roster, source_verifier=verifier)
        reviewer = next(row for row in roster.activities if row.kind == "reviewer")
        receipt = _receipt(roster, reviewer, "actualAdditionalSpendEur", amount=Decimal("0"))
        with self.assertRaisesRegex(money.MoneyAccountingError, "identity-bound human-rating addendum"):
            ledger.add(receipt)
        self.assertEqual((), ledger.history)

    def test_estimate_completion_keeps_cash_and_human_totals_unknown(self):
        reg = registration()
        roster = _roster(reg)
        monetary = money.MoneyLedger(roster, source_verifier=_SourceVerifier())
        ledger = evaluation.new_ledger(reg)
        ledger_sha = hashlib.sha256(json.dumps(ledger.as_dict(), sort_keys=True,
            separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        evidence = estimate.ActiveTimeEvidence(reg.sha256, ledger_sha, "synthetic-active-time",
            _sha("active-time"), "2026-10-09T16:00:00Z", {"codex": 57600, "claude-code": 57600})

        class Verifier:
            def verify_active_time(self, *, registration_sha256, ledger_sha256, evidence):
                return registration_sha256 == reg.sha256 and ledger_sha256 == ledger_sha

        result = full_cost.complete_full_cost(reg, ledger, roster, monetary, monetary.summarize(),
            setup_costs=_known_costs(), human_time_receipts=tuple(row for row in _time_receipts(roster)
                if row.participant_id == "operator-1"),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            subscription_estimate_evidence=evidence, subscription_estimate_verifier=Verifier())
        self.assertEqual("pending-cash-verification", result.full_economic_cost_status)
        self.assertEqual(Decimal("5.045"), result.subscription_allocation_upper_bound_eur)
        self.assertFalse(result.full_economic_cost_complete)
        self.assertIsNone(result.actual_additional_spend_eur)
        self.assertIsNone(result.actual_provider_spend_eur)
        self.assertIsNone(result.allocated_subscription_cost_eur)
        self.assertIsNone(result.provider_accounting_cost_eur)
        self.assertIsNone(result.reviewer_time_seconds)
        self.assertIsNone(result.human_time_seconds)
        self.assertIsNone(result.stop_required)
        self.assertIsNone(result.technical_stop_required)
        with self.assertRaises(evaluation.EvaluationError):
            evaluation.assess_utility_eligibility(reg, ledger, setup_costs=None, human_ratings={})
