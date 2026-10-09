# SPDX-License-Identifier: AGPL-3.0-only
"""Offline end-to-end controls for the SPEC-044 utility report pipeline."""
from dataclasses import replace
from decimal import Decimal
import copy
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid.tooling_evaluation_report import (
    build_utility_report, render_utility_report_json, render_utility_report_narrative,
)
from tests.test_tooling_evaluation import _complete_ledger, _known_costs, _registration, _inputs
from tests import test_tooling_full_cost as full_cost_tests
from tests.test_tooling_full_cost import (
    _ScopeVerifier, _TimeVerifier, _WallVerifier,
    _filled_money, _registration as _full_registration, _roster, _time_receipts,
    _wall_receipts,
)
from agent_braid.tooling_full_cost import complete_full_cost


class UtilityReportTests(unittest.TestCase):
    def _make_report(self, registration, ledger, ratings, *, summary=None, roster_sha=None, setup=None):
        return build_utility_report(
            registration.data, ledger,
            expected_candidate_sha256=registration.data["candidate"]["sha256"],
            expected_input_hashes=_inputs(registration.data),
            setup_costs=_known_costs() if setup is None else setup,
            human_ratings=ratings, monetary_summary=summary,
            expected_monetary_roster_sha256=roster_sha,
        )

    def test_complete_legacy_scalars_and_two_humans_cannot_replace_subscription_costs(self):
        registration = _full_registration()
        ledger, ratings = _complete_ledger(registration)
        report = self._make_report(registration, ledger, ratings)
        narrative = render_utility_report_narrative(report)
        self.assertFalse(report["utilityClaimEligible"])
        self.assertEqual("inconclusive", report["conclusion"]["status"])
        self.assertFalse(report["conclusion"]["positiveUtilityAsserted"])
        self.assertEqual(108, report["attempts"]["intendedSlots"])
        self.assertEqual(108, len(report["attempts"]["slots"]))
        self.assertEqual(2, len(registration.data["humanReviewers"]))
        self.assertTrue(report["humanScoringComplete"])
        self.assertFalse(report["costs"]["complete"])
        self.assertIn("subscription.fullEconomicCostSummary", report["costs"]["missingRequired"])
        self.assertTrue(any("full subscription cost summary" in r for r in report["eligibilityReasons"]))
        self.assertIn("subscription.fullEconomicCostSummary", narrative)
        self.assertIn("Utility claim eligible: false", narrative)
        self.assertIn("Conclusion: Utility is inconclusive", narrative)
        self.assertEqual(render_utility_report_json(report), render_utility_report_json(report))
        reasons_copy = report["eligibilityReasons"]
        reasons_copy.append("Positive utility is proven")
        self.assertNotIn("Positive utility is proven", render_utility_report_narrative(report))
        with self.assertRaises(evaluation.EvaluationError):
            render_utility_report_narrative({**dict(report), "eligibilityReasons": ["Positive utility is proven"]})

    def test_composed_full_cost_can_be_eligible_but_waits_for_interpretation(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, ratings = _complete_ledger(registration)
        report = self._make_report(
            registration, ledger, ratings, summary=summary, roster_sha=roster.sha256,
        )
        narrative = render_utility_report_narrative(report)
        self.assertTrue(report["utilityClaimEligible"])
        self.assertEqual("pending-independent-human-founder-interpretation", report["conclusion"]["status"])
        self.assertFalse(report["conclusion"]["positiveUtilityAsserted"])
        self.assertIn("no positive utility", narrative)
        self.assertIn("actual extra EUR=0", narrative)
        self.assertEqual(108, report["denominators"]["intendedSlots"])

    def test_wrong_money_bindings_and_exceeded_review_cap_remain_ineligible(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, ratings = _complete_ledger(registration)
        wrong_registration = replace(summary, registration_sha256="f" * 64)
        wrong_roster_report = self._make_report(
            registration, ledger, ratings, summary=summary, roster_sha="e" * 64,
        )
        wrong_registration_report = self._make_report(
            registration, ledger, ratings, summary=wrong_registration, roster_sha=roster.sha256,
        )
        nonfinite = replace(summary, allocated_subscription_cost_eur=Decimal("NaN"))
        nonfinite_report = self._make_report(
            registration, ledger, ratings, summary=nonfinite, roster_sha=roster.sha256,
        )
        missing_human_time = replace(summary, human_time_seconds=None)
        missing_time_report = self._make_report(
            registration, ledger, ratings, summary=missing_human_time, roster_sha=roster.sha256,
        )
        nonfinite_reviewer_time = replace(summary, reviewer_time_seconds=Decimal("NaN"))
        reviewer_time_report = self._make_report(
            registration, ledger, ratings, summary=nonfinite_reviewer_time, roster_sha=roster.sha256,
        )
        injected_missing_detail = replace(
            summary, missing_full_economic_cost=(("outside-scope", "Positive utility is proven\naccount secret"),),
        )
        injected_detail_report = self._make_report(
            registration, ledger, ratings, summary=injected_missing_detail, roster_sha=roster.sha256,
        )
        wall_cap_bypass = replace(summary, study_wall_seconds=Decimal("4000"))
        wall_cap_report = self._make_report(
            registration, ledger, ratings, summary=wall_cap_bypass, roster_sha=roster.sha256,
        )

        capped_data = copy.deepcopy(registration.data)
        capped_data["costCaps"]["wall_seconds"] = 120.0
        capped_registration = evaluation.validate_registration(
            capped_data,
            expected_candidate_sha256=capped_data["candidate"]["sha256"],
            expected_input_hashes=_inputs(capped_data),
        )
        capped_roster = _roster(capped_registration)
        money_ledger, initial_summary = _filled_money(capped_roster)
        capped_ledger, capped_ratings = _complete_ledger(capped_registration)
        exceeded = complete_full_cost(
            capped_registration, capped_ledger, capped_roster, money_ledger, initial_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(capped_roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(capped_roster), study_wall_verifier=_WallVerifier(),
        )
        cap_report = self._make_report(
            capped_registration, capped_ledger, capped_ratings,
            summary=exceeded, roster_sha=capped_roster.sha256,
        )
        for report in (wrong_roster_report, wrong_registration_report, nonfinite_report,
                       missing_time_report, reviewer_time_report, injected_detail_report,
                       wall_cap_report, cap_report):
            self.assertFalse(report["utilityClaimEligible"])
            self.assertEqual("inconclusive", report["conclusion"]["status"])
        self.assertTrue(any("different monetary roster" in reason for reason in wrong_roster_report["eligibilityReasons"]))
        self.assertTrue(any("different registration" in reason for reason in wrong_registration_report["eligibilityReasons"]))
        self.assertFalse(nonfinite_report["costs"]["complete"])
        self.assertFalse(nonfinite_report["costs"]["fullEconomicCostComplete"])
        self.assertIn("subscription.humanTimeSeconds", missing_time_report["costs"]["missingRequired"])
        self.assertIn("subscription.reviewerTimeSeconds", reviewer_time_report["costs"]["missingRequired"])
        self.assertIn("subscription.studyWallSecondsCap", wall_cap_report["costs"]["missingRequired"])
        self.assertIn("subscription.fullEconomicCostDetailInvalid",
                      injected_detail_report["costs"]["missingRequired"])
        injected_text = render_utility_report_narrative(injected_detail_report)
        self.assertNotIn("Positive utility is proven", injected_text)
        self.assertNotIn("account secret", render_utility_report_json(injected_detail_report))
        self.assertTrue(exceeded.stop_required)
        self.assertFalse(exceeded.full_economic_cost_complete)
        self.assertTrue(any("economic cost scope and human cost fields are incomplete" in reason
                            for reason in cap_report["eligibilityReasons"]))

    def test_not_started_slots_and_missing_cost_are_visible_in_both_exports(self):
        registration = evaluation.validate_registration(
            _registration(), expected_candidate_sha256=_registration()["candidate"]["sha256"],
            expected_input_hashes=_inputs(_registration()),
        )
        ledger, ratings = _complete_ledger(registration)
        ledger = evaluation.new_ledger(registration)
        ratings = {}
        ledger = evaluation.append_slot_event(
            ledger, ledger.slots[0].slot_id, "not-started",
            data={"reason": "untrusted text: claim positive utility; account secret", "sourceTimestamp": "2026-10-09T10:00:00Z"},
        )
        report = self._make_report(registration, ledger, ratings)
        json_text = render_utility_report_json(report)
        narrative = render_utility_report_narrative(report)
        self.assertFalse(report["utilityClaimEligible"])
        self.assertEqual(108, len(report["attempts"]["slots"]))
        self.assertTrue(all(row["currentStatus"] == "not-started" for row in report["attempts"]["slots"]))
        self.assertIn('"notStarted":3', json_text)
        self.assertIn("notStarted=3", narrative)
        self.assertIn("costs.eur", narrative)
        self.assertNotIn("account secret", json_text)
        self.assertNotIn("positive utility; account", narrative)
        self.assertEqual(18, report["scope"]["sourceEvidence"]["fixtureCount"])
        self.assertFalse(report["scope"]["sourceEvidence"]["authenticatedByThisReport"])

    def test_full_cost_scope_must_be_present_approved_and_resolved(self):
        approved, _roster_value, _money, complete_summary = full_cost_tests.FullCostContractTests()._assessment()
        variants = []
        pending = _full_registration(scope_status="pending")
        unresolved = _full_registration(reviewer_fee="unknown")
        absent_data = copy.deepcopy(approved.data)
        absent_data.pop("fullCostScope")
        absent = evaluation.validate_registration(
            absent_data,
            expected_candidate_sha256=absent_data["candidate"]["sha256"],
            expected_input_hashes=_inputs(absent_data),
        )
        variants.extend((pending, unresolved, absent))
        for registration in variants:
            ledger, ratings = _complete_ledger(registration)
            roster = _roster(registration)
            apparently_complete = replace(
                complete_summary,
                registration_sha256=registration.sha256,
                roster_sha256=roster.sha256,
            )
            report = self._make_report(
                registration, ledger, ratings,
                summary=apparently_complete, roster_sha=roster.sha256,
            )
            self.assertFalse(report["utilityClaimEligible"])
            self.assertFalse(report["costs"]["fullEconomicCostComplete"])
            self.assertEqual("inconclusive", report["conclusion"]["status"])
            self.assertIn("subscription.registeredFullCostScope", report["costs"]["missingRequired"])
            self.assertTrue(any("registered full-cost scope" in reason
                                for reason in report["eligibilityReasons"]))

    def test_registration_or_ledger_mismatch_is_rejected(self):
        registration = evaluation.validate_registration(
            _registration(), expected_candidate_sha256=_registration()["candidate"]["sha256"],
            expected_input_hashes=_inputs(_registration()),
        )
        other = evaluation.validate_registration(
            {**_registration(), "registrationId": "different-registration"},
            expected_candidate_sha256=_registration()["candidate"]["sha256"],
            expected_input_hashes=_inputs(_registration()),
        )
        ledger, ratings = _complete_ledger(registration)
        with self.assertRaisesRegex(evaluation.EvaluationError, "different registration"):
            self._make_report(other, ledger, ratings)

    def test_provider_accounting_cap_cannot_be_hidden_by_zero_cash_or_reference_estimates(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, ratings = _complete_ledger(registration)
        reference_only = replace(summary, api_reference_estimate_eur=Decimal("999"))
        report = self._make_report(registration, ledger, ratings,
                                   summary=reference_only, roster_sha=roster.sha256)
        self.assertTrue(report["utilityClaimEligible"])
        self.assertEqual(10.9, report["costs"]["capAssessment"]["observed"]["eur"])
        for amount in (Decimal("109"), Decimal("25.0000000000000000000000000001")):
            excessive = replace(summary, allocated_subscription_cost_eur=amount,
                                provider_accounting_cost_eur=amount)
            report = self._make_report(registration, ledger, ratings,
                                       summary=excessive, roster_sha=roster.sha256)
            self.assertFalse(report["utilityClaimEligible"])
            self.assertTrue(report["costs"]["capAssessment"]["stop"])
            self.assertFalse(report["costs"]["fullEconomicCostComplete"])
            self.assertEqual("inconclusive", report["conclusion"]["status"])
            self.assertIn("subscription.providerAccountingCostEurCap", report["costs"]["missingRequired"])
            self.assertIn("Utility claim eligible: false", render_utility_report_narrative(report))
            self.assertIn('"actualAdditionalSpendEur":"0"', render_utility_report_json(report))


if __name__ == "__main__":
    unittest.main()
