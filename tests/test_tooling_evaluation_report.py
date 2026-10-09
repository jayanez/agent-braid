# SPDX-License-Identifier: AGPL-3.0-only
"""Offline end-to-end controls for the SPEC-044 utility report pipeline."""
from dataclasses import replace
from decimal import Decimal
import copy
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid.tooling_money import MoneySummary
from agent_braid.tooling_full_cost import (
    FullCostScope, TechnicalCostSummaryAttestation, technical_summary_sha256,
)
from agent_braid.tooling_evaluation_report import (
    build_utility_report, render_utility_report_json, render_utility_report_narrative,
)
from tests.test_tooling_evaluation import _adjudication, _complete_ledger, _known_costs, _registration, _registration_v3, _inputs
from tests import test_tooling_full_cost as full_cost_tests
from tests.test_tooling_full_cost import (
    _ScopeVerifier, _TimeVerifier, _WallVerifier,
    _filled_money, _registration as _full_registration, _roster, _time_receipts,
    _wall_receipts,
)
from agent_braid.tooling_full_cost import complete_full_cost


class UtilityReportTests(unittest.TestCase):
    def _make_report(self, registration, ledger, ratings, *, summary=None, roster_sha=None, setup=None,
                     technical_cost_verifier=None):
        return build_utility_report(
            registration.data, ledger,
            expected_candidate_sha256=registration.data["candidate"]["sha256"],
            expected_input_hashes=_inputs(registration.data),
            setup_costs=_known_costs() if setup is None else setup,
            human_ratings=ratings, monetary_summary=summary,
            expected_monetary_roster_sha256=roster_sha,
            technical_cost_verifier=technical_cost_verifier,
        )

    def _technical_verifier(self, registration, *, mismatch=None):
        expected_ids = tuple(sorted({"setup", *(
            slot.slot_id for slot in evaluation.generate_slots(registration)
        )}))
        class Verifier:
            def verify_technical_summary(self, *, registration_sha256, roster_sha256, scope_sha256, summary):
                values = {
                    "verifier_id": "synthetic-technical-summary-verifier",
                    "summary_sha256": technical_summary_sha256(summary),
                    "registration_sha256": registration_sha256,
                    "roster_sha256": roster_sha256,
                    "scope_sha256": scope_sha256,
                    "receipt_sha256s": summary.receipt_sha256s,
                    "human_time_receipt_sha256s": summary.human_time_receipt_sha256s,
                    "study_wall_receipt_sha256s": summary.study_wall_receipt_sha256s,
                    "technical_activity_ids": expected_ids,
                    "actual_spend_activity_ids": expected_ids,
                    "allocated_activity_ids": expected_ids,
                    "user_time_activity_ids": expected_ids,
                    "study_wall_activity_ids": expected_ids,
                    "verified_at": "2026-10-09T16:00:00Z",
                }
                if mismatch:
                    values.update(mismatch)
                return TechnicalCostSummaryAttestation(**values)
        return Verifier()

    def test_v3_report_marks_human_evaluation_and_cost_pending_while_retaining_108(self):
        data = _registration_v3()
        registration = evaluation.validate_registration(
            data, expected_candidate_sha256=data["candidate"]["sha256"],
            expected_input_hashes=_inputs(data),
        )
        ledger, ratings = _complete_ledger(registration)
        report = self._make_report(registration, ledger, ratings)
        narrative = render_utility_report_narrative(report)
        self.assertFalse(report["utilityClaimEligible"])
        self.assertFalse(report["conclusion"]["positiveUtilityAsserted"])
        self.assertEqual("human-evaluation-deferred", report["conclusion"]["status"])
        self.assertEqual({"status": "deferred", "identifiedReviewers": 0,
                          "adjudication": "pending", "humanCostStatus": "missing",
                          "humanAcceptanceAsserted": False}, report["humanEvaluation"])
        self.assertEqual(108, report["attempts"]["intendedSlots"])
        self.assertIn("formal closure remains pending", report["conclusion"]["text"])
        self.assertIn("Human evaluation: deferred", narrative)
        self.assertIn("human cost=missing", narrative)
        self.assertIn("formal closure", narrative)

    def test_v3_report_refuses_a_spoofed_complete_human_inclusive_cost_summary(self):
        registration = _full_registration(technical_capture=True, reviewer_fee="unknown")
        roster = _roster(registration)
        ledger, ratings = _complete_ledger(registration)
        zero = Decimal("0")
        forged = MoneySummary(
            actual_additional_spend_eur=zero, observed_additional_spend_subtotal_eur=zero,
            actual_additional_spend_cap_eur=zero, cap_violation=False, stop_required=False,
            allocated_subscription_cost_eur=zero, api_reference_estimate_eur=None,
            required_measures_complete=True, full_economic_cost_complete=True,
            full_economic_cost_status="complete", missing_required=(), missing_full_economic_cost=(),
            registration_sha256=registration.sha256, roster_sha256=roster.sha256, receipt_sha256s=(),
            human_time_seconds=zero, user_time_seconds=zero, reviewer_time_seconds=zero,
            study_wall_seconds=zero, actual_provider_spend_eur=zero, provider_accounting_cost_eur=zero,
        )
        report = self._make_report(registration, ledger, ratings, summary=forged,
                                   roster_sha=roster.sha256)
        self.assertFalse(report["costs"]["fullEconomicCostComplete"])
        self.assertFalse(report["costs"]["complete"])
        self.assertEqual("missing", report["humanEvaluation"]["humanCostStatus"])
        self.assertFalse(report["utilityClaimEligible"])
        self.assertIsNone(report["costs"]["fullEconomic"]["humanTimeSeconds"])
        self.assertIsNone(report["costs"]["fullEconomic"]["reviewerTimeSeconds"])
        narrative = render_utility_report_narrative(report)
        self.assertIn("active human seconds=unknown", narrative)
        self.assertIn("reviewer seconds=unknown", narrative)
        self.assertNotIn("active human seconds=0", narrative)
        self.assertNotIn("reviewer seconds=0", narrative)

    def test_v3_report_retains_only_reconciled_technical_cost_and_wall_values(self):
        registration = _full_registration(technical_capture=True, reviewer_fee="unknown")
        roster = _roster(registration)
        money_ledger, money_summary = _filled_money(roster)
        ledger, ratings = _complete_ledger(registration)
        summary = complete_full_cost(
            registration, ledger, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        report = self._make_report(registration, ledger, ratings, summary=summary,
                                   roster_sha=roster.sha256,
                                   technical_cost_verifier=self._technical_verifier(registration))
        costs = report["costs"]["fullEconomic"]
        self.assertTrue(report["costs"]["technicalMeasuresAttested"])
        self.assertFalse(report["costs"]["fullEconomicCostComplete"])
        self.assertIsNotNone(costs["actualProviderSpendEur"])
        self.assertIsNotNone(costs["allocatedSubscriptionCostEur"])
        self.assertEqual("0", costs["technicalAdditionalSpendEur"])
        self.assertEqual("60.000000", costs["userTimeSeconds"])
        self.assertEqual("300.000000", costs["studyWallSeconds"])
        self.assertIsNone(costs["humanTimeSeconds"])
        self.assertIsNone(costs["reviewerTimeSeconds"])
        self.assertEqual(109, len(costs["studyWallReceiptSha256s"]))
        narrative = render_utility_report_narrative(report)
        self.assertIn("verified user seconds=60.000000", narrative)
        self.assertIn("study wall seconds=300.000000", narrative)
        self.assertIn("active human seconds=unknown", narrative)
        self.assertIn("reviewer seconds=unknown", narrative)

    def test_v3_attestation_mismatch_and_fake_repeated_hashes_fail_closed(self):
        registration = _full_registration(technical_capture=True, reviewer_fee="unknown")
        roster = _roster(registration)
        money_ledger, money_summary = _filled_money(roster)
        ledger, ratings = _complete_ledger(registration)
        valid_summary = complete_full_cost(
            registration, ledger, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        fake = replace(
            valid_summary, technical_additional_spend_eur=Decimal("0"),
            technical_required_measures_complete=True, missing_technical_required=(),
            technical_cap_violation=False, technical_stop_required=False,
            actual_provider_spend_eur=Decimal("0"), allocated_subscription_cost_eur=Decimal("0"),
            provider_accounting_cost_eur=Decimal("0"), user_time_seconds=Decimal("0"),
            study_wall_seconds=Decimal("0"),
            actual_additional_spend_cap_eur=Decimal("0.5"),
            receipt_sha256s=("a" * 64, "a" * 64),
            human_time_receipt_sha256s=("b" * 64, "b" * 64),
            study_wall_receipt_sha256s=("c" * 64, "c" * 64),
        )
        fake_report = self._make_report(registration, ledger, ratings, summary=fake,
                                        roster_sha=roster.sha256,
                                        technical_cost_verifier=self._technical_verifier(registration))
        self.assertFalse(fake_report["costs"]["technicalMeasuresAttested"])
        for field in ("actualAdditionalSpendCapEur", "technicalAdditionalSpendEur", "actualProviderSpendEur",
                      "allocatedSubscriptionCostEur", "userTimeSeconds", "studyWallSeconds"):
            self.assertIsNone(fake_report["costs"]["fullEconomic"][field])

        expected_ids = tuple(sorted({"setup", *(slot.slot_id for slot in evaluation.generate_slots(registration))}))
        mismatch_cases = (
            {"summary_sha256": "f" * 64},
            {"registration_sha256": "f" * 64},
            {"roster_sha256": "f" * 64},
            {"scope_sha256": "f" * 64},
            {"receipt_sha256s": ("d" * 64,)},
            {"actual_spend_activity_ids": expected_ids[:-1]},
        )
        for mismatch in mismatch_cases:
            with self.subTest(mismatch=mismatch):
                verifier = self._technical_verifier(registration, mismatch=mismatch)
                bound_report = self._make_report(registration, ledger, ratings, summary=valid_summary,
                                                 roster_sha=roster.sha256,
                                                 technical_cost_verifier=verifier)
                self.assertFalse(bound_report["costs"]["technicalMeasuresAttested"])
                self.assertIsNone(bound_report["costs"]["fullEconomic"]["studyWallSeconds"])
                self.assertIsNone(bound_report["costs"]["fullEconomic"]["actualAdditionalSpendCapEur"])

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

    def test_safe_report_preserves_actual_attempt_ids_separately_from_slot_ids(self):
        registration, _roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, ratings = _complete_ledger(registration)
        report = self._make_report(registration, ledger, ratings, summary=summary,
                                   roster_sha=_roster.sha256)

        first_slot = ledger.slots[0]
        first_attempt = ledger.current_event(first_slot.slot_id).attempt_id
        reported_slot = next(row for row in report["attempts"]["slots"]
                             if row["slotId"] == first_slot.slot_id)
        self.assertEqual(first_slot.slot_id, reported_slot["slotId"])
        self.assertEqual(first_attempt, reported_slot["currentAttemptId"])
        self.assertNotEqual(first_slot.slot_id, reported_slot["currentAttemptId"])
        slot_events = [event for event in report["attempts"]["events"]
                       if event["slotId"] == first_slot.slot_id]
        self.assertEqual(["attempted", "valid"], [event["status"] for event in slot_events])
        self.assertEqual([first_attempt, first_attempt], [event["attemptId"] for event in slot_events])
        self.assertIn(f'"attemptId":"{first_attempt}"', render_utility_report_json(report))

    def test_missing_cost_attribution_maps_attempt_setup_and_cohort_scopes(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        all_slots = evaluation.generate_slots(registration)

        target = all_slots[4]
        per_slot_ledger, per_slot_ratings = _complete_ledger(
            registration, missing_cost_slot=target.slot_id,
        )
        per_slot = self._make_report(registration, per_slot_ledger, per_slot_ratings,
                                     summary=summary, roster_sha=roster.sha256)
        attempt_row = next(item for item in per_slot["costs"]["missingRequiredByScope"]
                           if item["scope"] == "attempt" and item["activityId"] == target.slot_id)
        expected_attempt_id = per_slot_ledger.current_event(target.slot_id).attempt_id
        self.assertEqual([{"slotId": target.slot_id, "attemptId": expected_attempt_id}],
                         attempt_row["affectedAttempts"])
        self.assertEqual({"costs.tokens", "costs.input_tokens"}, set(attempt_row["fields"]))
        self.assertIn(f"{target.slot_id}={expected_attempt_id}",
                      render_utility_report_narrative(per_slot))

        complete_ledger, complete_ratings = _complete_ledger(registration)
        setup = self._make_report(registration, complete_ledger, complete_ratings,
                                  summary=summary, roster_sha=roster.sha256,
                                  setup=_known_costs(eur=None))
        setup_row = next(item for item in setup["costs"]["missingRequiredByScope"]
                         if item["scope"] == "setup")
        self.assertEqual("setup", setup_row["activityId"])
        self.assertEqual(["setupCosts.eur"], setup_row["fields"])
        self.assertEqual(108, len(setup_row["affectedAttempts"]))
        self.assertTrue(all(row["attemptId"] is not None for row in setup_row["affectedAttempts"]))
        self.assertIn("setup: fields=setupCosts.eur", render_utility_report_narrative(setup))

        global_gap = replace(
            summary,
            full_economic_cost_complete=False,
            full_economic_cost_status="incomplete",
            missing_full_economic_cost=summary.missing_full_economic_cost +
                (("registration-costs", "eur"),),
        )
        cohort = self._make_report(registration, complete_ledger, complete_ratings,
                                   summary=global_gap, roster_sha=roster.sha256)
        cohort_row = next(item for item in cohort["costs"]["missingRequiredByScope"]
                          if item["scope"] == "cohort")
        self.assertEqual(["subscription.registrationCosts.eur"], cohort_row["fields"])
        self.assertEqual(108, len(cohort_row["affectedAttempts"]))
        self.assertEqual(
            {slot.slot_id: complete_ledger.current_event(slot.slot_id).attempt_id
             for slot in all_slots},
            {row["slotId"]: row["attemptId"] for row in cohort_row["affectedAttempts"]},
        )
        self.assertIn("cohort: fields=subscription.registrationCosts.eur",
                      render_utility_report_narrative(cohort))

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

    def test_complete_registered_threshold_failures_are_descriptive_in_legacy_and_subscription(self):
        legacy = evaluation.validate_registration(
            _registration(), expected_candidate_sha256=_registration()["candidate"]["sha256"],
            expected_input_hashes=_inputs(_registration()),
        )
        failures = {slot.slot_id for slot in evaluation.generate_slots(legacy)
                    if slot.arm == "mcp-plus-skills" and slot.host == "codex" and
                    slot.order_position == 1}
        ledger, ratings = _complete_ledger(legacy, successful_slots=failures)
        arm_c_slot = next(slot for slot in ledger.slots if slot.arm == "mcp-plus-skills")
        ratings[arm_c_slot.slot_id][0]["fidelity"] = False
        ratings[arm_c_slot.slot_id][1]["fidelity"] = False
        legacy_report = self._make_report(legacy, ledger, ratings)

        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger2, ratings2 = _complete_ledger(registration, successful_slots=failures)
        arm_c_slot2 = next(slot for slot in ledger2.slots if slot.arm == "mcp-plus-skills")
        for rating in ratings2[arm_c_slot2.slot_id]:
            rating["authority_correct"] = False
        subscription_report = self._make_report(
            registration, ledger2, ratings2, summary=summary, roster_sha=roster.sha256,
        )
        for report in (legacy_report, subscription_report):
            self.assertFalse(report["utilityClaimEligible"])
            self.assertEqual("registered-threshold-not-met", report["conclusion"]["status"])
            self.assertFalse(report["conclusion"]["positiveUtilityAsserted"])
            self.assertEqual(108, report["denominators"]["intendedSlots"])
            self.assertIn("registered-threshold-not-met", render_utility_report_narrative(report))
            self.assertIn("registered outcome and safety criteria", report["conclusion"]["text"])
            self.assertIn('"status":"registered-threshold-not-met"', render_utility_report_json(report))
            self.assertTrue(report["armC"]["labelResolution"]["totals"]["fidelity"]["resolved"] > 0)
        self.assertFalse(legacy_report["armC"]["fidelityByHost"][arm_c_slot.host])
        self.assertFalse(subscription_report["armC"]["authorityCorrectByHost"][arm_c_slot2.host] == 18)
        described = legacy_report["descriptiveByHostArmClass"][0]
        self.assertEqual(36, len(legacy_report["descriptiveByHostArmClass"]))
        self.assertEqual(3, described["totalWallSeconds"]["observedSlots"])
        self.assertFalse(described["interventions"]["complete"])
        self.assertIsNone(described["interventions"]["total"])

    def test_unknown_cost_or_human_labels_remain_inconclusive_and_true_pass_stays_pending(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, ratings = _complete_ledger(registration, missing_cost_slot=None)
        first_c = next(slot for slot in ledger.slots if slot.arm == "mcp-plus-skills")
        ratings[first_c.slot_id][1]["fidelity"] = None
        unknown_label_report = self._make_report(
            registration, ledger, ratings, summary=summary, roster_sha=roster.sha256,
        )
        self.assertEqual("inconclusive", unknown_label_report["conclusion"]["status"])
        self.assertIsNone(unknown_label_report["armC"]["fidelityByHost"][first_c.host])
        self.assertGreater(
            unknown_label_report["armC"]["labelResolution"]["totals"]["fidelity"]["missing"]
            + unknown_label_report["armC"]["labelResolution"]["totals"]["fidelity"]["disagreement"], 0,
        )

        ledger2, ratings2 = _complete_ledger(registration)
        missing_slot = ledger2.slots[-1].slot_id
        ledger2, ratings2 = _complete_ledger(registration, missing_cost_slot=missing_slot)
        missing_cost_report = self._make_report(
            registration, ledger2, ratings2, summary=summary, roster_sha=roster.sha256,
        )
        self.assertEqual("inconclusive", missing_cost_report["conclusion"]["status"])

        disagree_ledger, disagree_ratings = _complete_ledger(registration)
        disputed = next(slot for slot in disagree_ledger.slots if slot.arm == "mcp-plus-skills")
        disagree_ratings[disputed.slot_id][1]["fidelity"] = False
        bad_adjudication = _adjudication("rater-one", fidelity=True)
        bad_adjudication["sha256"] = "0" * 64
        unresolved_report = build_utility_report(
            registration.data, disagree_ledger,
            expected_candidate_sha256=registration.data["candidate"]["sha256"],
            expected_input_hashes=_inputs(registration.data), setup_costs=_known_costs(),
            human_ratings=disagree_ratings, adjudications={disputed.slot_id: bad_adjudication},
            monetary_summary=summary, expected_monetary_roster_sha256=roster.sha256,
        )
        self.assertEqual("inconclusive", unresolved_report["conclusion"]["status"])
        self.assertEqual("disagreement", unresolved_report["armC"]["labelResolution"]["bySlot"][disputed.slot_id]["fidelity"])

        pass_report = self._make_report(
            registration, _complete_ledger(registration)[0], _complete_ledger(registration)[1],
            summary=summary, roster_sha=roster.sha256,
        )
        self.assertEqual("pending-independent-human-founder-interpretation", pass_report["conclusion"]["status"])

    def test_invalid_rating_identity_and_missing_ratings_preserve_all_label_denominators(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        ledger, original_ratings = _complete_ledger(registration)
        test_slot = ledger.slots[0].slot_id
        variants = []
        non_mapping = copy.deepcopy(original_ratings)
        non_mapping[test_slot][1] = "not a rating object"
        variants.append(non_mapping)
        invalid_id = copy.deepcopy(original_ratings)
        invalid_id[test_slot][1]["reviewerId"] = "unregistered-rater"
        variants.append(invalid_id)
        invalid_type = copy.deepcopy(original_ratings)
        invalid_type[test_slot][1]["reviewerType"] = "model"
        variants.append(invalid_type)
        invalid_independence = copy.deepcopy(original_ratings)
        invalid_independence[test_slot][1]["independent"] = False
        variants.append(invalid_independence)

        for ratings in variants:
            report = self._make_report(
                registration, ledger, ratings, summary=summary, roster_sha=roster.sha256,
            )
            self.assertEqual("inconclusive", report["conclusion"]["status"])
            totals = report["armC"]["labelResolution"]["totals"]
            for field_counts in totals.values():
                self.assertEqual(108, sum(field_counts.values()))
                self.assertGreater(field_counts["missing"], 0)
            self.assertEqual("missing", report["armC"]["labelResolution"]["bySlot"][test_slot]["success"])

    def test_threshold_failure_with_complete_costs_but_unstarted_cohort_is_inconclusive(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        _, ratings = _complete_ledger(registration, successful_slots={
            slot.slot_id for slot in evaluation.generate_slots(registration)
            if slot.host == "codex" and slot.arm == "mcp-plus-skills" and slot.order_position == 1
        })
        ledger = evaluation.new_ledger(registration)
        for slot in ledger.slots:
            ledger = evaluation.append_slot_event(
                ledger, slot.slot_id, "not-started",
                data={"reason": "synthetic pre-start measurement control",
                      "sourceTimestamp": "2026-10-09T10:00:00Z", "costs": _known_costs()},
            )
        report = self._make_report(
            registration, ledger, ratings, summary=summary, roster_sha=roster.sha256,
        )
        self.assertTrue(report["costs"]["complete"])
        self.assertEqual("inconclusive", report["conclusion"]["status"])
        self.assertTrue(report["armC"]["thresholdReasons"])
        self.assertEqual(108, report["denominators"]["intendedSlots"])
        narrative = render_utility_report_narrative(report)
        self.assertIn("success=", narrative)
        self.assertIn("intended=3", narrative)

    def test_positive_report_with_all_true_labels_still_needs_terminal_measured_cohort(self):
        registration, roster, _money, summary = full_cost_tests.FullCostContractTests()._assessment()
        _complete, ratings = _complete_ledger(registration)
        for open_status in ("not-started", "attempted"):
            ledger = evaluation.new_ledger(registration)
            for index, slot in enumerate(ledger.slots):
                if open_status == "not-started":
                    ledger = evaluation.append_slot_event(
                        ledger, slot.slot_id, "not-started",
                        data={"reason": "synthetic open-cohort control",
                              "sourceTimestamp": "2026-10-09T10:00:00Z",
                              "costs": _known_costs()},
                    )
                else:
                    ledger = evaluation.append_slot_event(
                        ledger, slot.slot_id, "attempted", attempt_id=f"report-open-{index:03d}",
                        data={"sourceTimestamp": "2026-10-09T10:00:00Z",
                              "costs": _known_costs()},
                    )
            report = self._make_report(
                registration, ledger, ratings, summary=summary, roster_sha=roster.sha256,
            )
            self.assertFalse(report["utilityClaimEligible"])
            self.assertEqual("inconclusive", report["conclusion"]["status"])
            self.assertEqual(108, report["denominators"]["intendedSlots"])
            self.assertTrue(any("not-started or open attempts" in reason
                                for reason in report["eligibilityReasons"]))

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
        not_started_slot = ledger.slots[0].slot_id
        self.assertFalse(report["utilityClaimEligible"])
        self.assertEqual(108, len(report["attempts"]["slots"]))
        self.assertTrue(all(row["currentStatus"] == "not-started" for row in report["attempts"]["slots"]))
        self.assertTrue(all(row["currentAttemptId"] is None for row in report["attempts"]["slots"]))
        self.assertEqual([None], [event["attemptId"] for event in report["attempts"]["events"]])
        not_started_mapping = next(
            item for item in report["costs"]["missingRequiredByScope"]
            if item["scope"] == "attempt" and item["activityId"] == not_started_slot
        )
        self.assertEqual([{"slotId": not_started_slot, "attemptId": None}],
                         not_started_mapping["affectedAttempts"])
        self.assertIn('"notStarted":3', json_text)
        self.assertIn("notStarted=3", narrative)
        self.assertIn(f"{not_started_slot}=null", narrative)
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
