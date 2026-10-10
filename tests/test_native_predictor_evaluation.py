# SPDX-License-Identifier: AGPL-3.0-only
"""Hand-authored synthetic tests for the SPEC-019 evaluation candidate."""
import copy
import unittest

from agent_braid.native_predictor_evaluation import (
    _default_verifier,
    _metrics,
    evaluate,
    permute_training_labels,
)
from agent_braid.native_predictor import FEATURES
from agent_braid.native_predictor_training import digest, fit, prepare_request, score
from agent_braid.structured_exchange import ROOT, VERSION


def _row(pair, family, a, b):
    return {"pairId": pair, "familyId": family, "sessionId": f"{pair}-session",
            "duplicateGroupId": f"duplicate-{pair}",
            "partition": "holdout",
            "request": {"model": VERSION, "base": [{"id": "x", "value": "X"},
                                                      {"id": "y", "value": "Y"}], "operations": [
                {"id": f"{pair}-op-a", "kind": "insert", "anchorId": a, "newId": f"{pair}-new-a", "value": "alpha"},
                {"id": f"{pair}-op-b", "kind": "insert", "anchorId": b, "newId": f"{pair}-new-b", "value": "beta"},
            ]}}


class NativePredictorEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.inventory = [_row("p0", "f1", ROOT, ROOT), _row("p1", "f1", ROOT, "x"),
                          _row("p2", "f2", ROOT, ROOT), _row("p3", "f2", "x", "y")]
        self.labels = {"p0": 1, "p1": 0, "p2": None, "p3": 1}
        for row in self.inventory:
            label = self.labels[row["pairId"]]
            row.update(annotation1=label, annotation2=label, adjudicatedLabel=None,
                       annotation1Attempted=True, annotation1ReviewerId="synthetic-reviewer-a",
                       annotation1UnknownReason=None if label is not None else "insufficient-context",
                       annotation2Attempted=True, annotation2ReviewerId="synthetic-reviewer-b",
                       annotation2UnknownReason=None if label is not None else "insufficient-context",
                       adjudicationAttempted=False, adjudicatorId=None,
                       adjudicationRationale=None, adjudicationUnknownReason=None)

    def run_eval(self, scorer, **kwargs):
        return evaluate(self.inventory, self.labels, scorer=scorer, dataset_kind="synthetic", **kwargs)

    def test_floor_budget_ties_and_verified_usefulness_bounds(self):
        # A tied scorer preserves inventory order; floor(.25 * 4) calls one.
        report = self.run_eval(lambda _vector: 0.0)
        baseline = report["budgets"]["baseline"]["25"]
        self.assertEqual(baseline["budgetCeiling"], 1)
        self.assertEqual(baseline["actualVerifierCalls"], 1)
        self.assertEqual(baseline["verifiedBoundedUsefulYield"], 1)
        self.assertEqual(baseline["verifiedBoundedSelectedLabels"]["knownUseful"], 1)
        self.assertEqual(baseline["verifiedUsefulYieldBounds"], {"lower": 1, "upper": 1,
                         "uncertainty": "missing-label identification bounds, not confidence intervals"})
        half = report["budgets"]["baseline"]["50"]
        self.assertEqual(half["verifiedUsefulYieldBounds"]["lower"], 1)
        self.assertEqual(half["verifiedUsefulYieldBounds"]["upper"], 2)
        for policy in ("baseline", "predictor"):
            result = report["budgets"][policy]["25"]
            self.assertEqual(result["actualVerifierCalls"], result["budgetCeiling"])
            self.assertEqual(result["verifierWork"]["submittedEvidenceProductionCount"],
                             result["actualVerifierCalls"])
            self.assertEqual(result["verifierWork"]["verifierInvocationCount"],
                             result["actualVerifierCalls"])
            self.assertEqual(result["verifierWork"]["verifierEvidenceRegenerationCount"],
                             result["actualVerifierCalls"])
            self.assertEqual(result["abstentionsSelected"], 0)

    def test_abstentions_use_no_calls_and_continue_down_ranking(self):
        calls = []
        def scorer(_vector):
            index = len(calls) % len(self.inventory)
            calls.append(index)
            return None if index == 0 else {"status": "proposal", "score": 10 if index == 1 else 0}
        report = self.run_eval(scorer)
        result = report["budgets"]["predictor"]["25"]
        self.assertEqual(result["abstentions"], 1)
        self.assertEqual(result["actualVerifierCalls"], 1)
        self.assertEqual(result["unusedCalls"], 0)
        self.assertEqual(result["verifierWork"]["submittedEvidenceProductionCount"], 1)
        self.assertEqual(result["verifierWork"]["verifierInvocationCount"], 1)
        self.assertEqual(result["verifierWork"]["verifierEvidenceRegenerationCount"], 1)
        self.assertEqual(result["abstentionsSelected"], 0)

    def test_label_and_family_fields_are_not_passed_to_scorer_or_preparer(self):
        seen = []
        def scorer(vector):
            self.assertEqual(set(vector), {"version", "features"})
            self.assertEqual(set(vector["features"]), set(FEATURES))
            self.assertNotIn("request", vector)
            self.assertNotIn("inputHash", vector)
            seen.append(vector)
            return 1
        def preparation(row):
            self.assertEqual(set(row), {"request"})
            self.assertNotIn("annotation1", row)
            self.assertNotIn("label", row)
            return prepare_request(row["request"], source_kind="synthetic")
        report = self.run_eval(scorer, preparation=preparation)
        self.assertTrue(seen)
        self.assertEqual(report["sourceKind"], "synthetic")
        self.assertFalse(report["executionAuthorization"])
        self.assertEqual(report["preparationMeasurement"]["sourceExtraction"],
                         "not measured; evaluator input is already an in-memory validated request")
        self.assertEqual(report["completeCostStatus"], "incomplete-source-extraction")

    def test_source_extraction_is_measured_symmetrically_and_report_serialization_is_allocated(self):
        inventory = [{**row, "sourceInput": copy.deepcopy(row["request"])}
                     for row in self.inventory]
        calls = []

        def extractor(source_input):
            calls.append(source_input)
            return copy.deepcopy(source_input)

        def scorer(vector):
            self.assertEqual(set(vector), {"version", "features"})
            return 1

        report = evaluate(inventory, self.labels, scorer=scorer, dataset_kind="synthetic",
                          source_extractor=extractor)
        self.assertTrue(calls)
        self.assertEqual(report["completeCostStatus"], "synthetic-callback-boundary-measured")
        self.assertEqual(report["preparationMeasurement"]["sourceExtraction"],
                         "measured per policy/budget/repetition from sourceInput")
        for policy in ("baseline", "predictor"):
            timing = report["budgets"][policy]["50"]["timing"]
            self.assertGreater(timing["phaseMedianSeconds"]["sourceExtractionSeconds"], 0)
            self.assertTrue(timing["fullCostIncludesSourceExtraction"])
            self.assertEqual(timing["fullCostMedianSeconds"],
                             timing["medianTotalSeconds"] + report["reportSerializationSeconds"] / 2)
        self.assertTrue(report["finalReportSerializationIncludedInPolicyTotals"])

    def test_source_extraction_refuses_drift_and_missing_input(self):
        inventory = [{**row, "sourceInput": copy.deepcopy(row["request"])}
                     for row in self.inventory]
        changed = copy.deepcopy(inventory)
        changed[0]["sourceInput"]["base"][0]["value"] = "drift"
        with self.assertRaisesRegex(ValueError, "differs from the frozen request commitment"):
            evaluate(changed, self.labels, scorer=lambda *_: 1, dataset_kind="synthetic",
                     source_extractor=lambda source: source)
        with self.assertRaisesRegex(ValueError, "sourceInput on every inventory row"):
            evaluate(self.inventory, self.labels, scorer=lambda *_: 1, dataset_kind="synthetic",
                     source_extractor=lambda source: source)

    def test_callbacks_cannot_mutate_inventory_or_verified_requests(self):
        original = self.inventory[0]["request"]["base"][0]["value"]
        def preparation(row):
            before = copy.deepcopy(row["request"])
            vector = prepare_request(before, source_kind="synthetic")
            row["request"]["base"][0]["value"] = "prep mutation"
            return vector
        def scorer(vector):
            self.assertNotIn("request", vector)
            vector["features"]["baseSize"] = 3
            return 1
        report = self.run_eval(scorer, preparation=preparation)
        self.assertEqual(self.inventory[0]["request"]["base"][0]["value"], original)
        self.assertEqual(report["budgets"]["baseline"]["100"]["verifierStatuses"]["verified-bounded"], 4)
        self.assertEqual(report["budgets"]["predictor"]["100"]["verifierStatuses"]["verified-bounded"], 4)

    def test_scorer_and_preparation_allowlist_drops_unexpected_label_like_metadata(self):
        hostile_rows = [dict(row, label=1, target=1, predictionScore=999,
                             annotationHidden=0, reviewerNote="private") for row in self.inventory]
        def assert_blind(row):
            self.assertEqual(set(row), {"request"})
        def scorer(vector):
            self.assertEqual(set(vector), {"version", "features"})
            self.assertEqual(set(vector["features"]), set(FEATURES))
            return 1
        def preparation(row):
            assert_blind(row)
            return prepare_request(row["request"], source_kind="synthetic")
        evaluate(hostile_rows, self.labels, scorer=scorer, preparation=preparation,
                 dataset_kind="synthetic")

    def test_annotation_agreement_and_calibration_are_descriptive(self):
        inventory = [dict(row, annotation1=1, annotation2=0, adjudicatedLabel=None,
                          annotation1UnknownReason=None, annotation2UnknownReason=None,
                          adjudicationAttempted=True, adjudicatorId="synthetic-reviewer-c",
                          adjudicationUnknownReason="synthetic insufficient context")
                     for row in self.inventory]
        unknown_labels = {pair_id: None for pair_id in self.labels}
        report = evaluate(inventory, unknown_labels, scorer=lambda _vector: 0.1,
                          dataset_kind="synthetic")
        self.assertEqual(report["annotationAgreementByFamily"]["f1"]["rawDisagreements"], 2)
        metric = report["budgets"]["predictor"]["50"]["calibration"]
        self.assertIsNone(metric["brier"])
        self.assertIn("reason", metric)

    def test_metric_labels_must_match_consensus_or_adjudication(self):
        conflict = [dict(row, annotation1=0, annotation2=1, adjudicatedLabel=None,
                         annotation1UnknownReason=None, annotation2UnknownReason=None,
                         adjudicationAttempted=True, adjudicatorId="synthetic-reviewer-c",
                         adjudicationUnknownReason="synthetic unresolved disagreement")
                    for row in self.inventory]
        with self.assertRaisesRegex(ValueError, "metric label differs"):
            evaluate(conflict, self.labels, scorer=lambda _vector: 0.1,
                     dataset_kind="synthetic")
        adjudicated = [dict(row, annotation1=0, annotation2=1, adjudicatedLabel=1,
                            annotation1UnknownReason=None, annotation2UnknownReason=None,
                            adjudicationAttempted=True, adjudicatorId="synthetic-reviewer-c",
                            adjudicationRationale="synthetic recorded rationale")
                       for row in self.inventory]
        adjudicated_labels = {pair_id: 1 for pair_id in self.labels}
        evaluate(adjudicated, adjudicated_labels, scorer=lambda _vector: 0.1,
                 dataset_kind="synthetic")
        with self.assertRaisesRegex(ValueError, "metric label differs"):
            evaluate(adjudicated, {pair_id: 0 for pair_id in self.labels},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")
        contradictory_adjudication = [dict(row, adjudicationUnknownReason="contradictory")
                                      for row in adjudicated]
        with self.assertRaisesRegex(ValueError, "cannot carry an unknown-label reason"):
            evaluate(contradictory_adjudication, adjudicated_labels,
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")
        fabricated_adjudicator = [dict(row, annotation1=0, annotation2=1,
                                      annotation1UnknownReason=None, annotation2UnknownReason=None,
                                      adjudicationAttempted=True, adjudicatorId=None,
                                      adjudicatedLabel=0, adjudicationRationale="declared")
                                 for row in self.inventory]
        with self.assertRaisesRegex(ValueError, "recorded third reviewer"):
            evaluate(fabricated_adjudicator, {pair_id: 0 for pair_id in self.labels},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")
        incomplete = [dict(row, annotation1=0, annotation2=None,
                           annotation1UnknownReason=None,
                           annotation2UnknownReason="insufficient-context",
                           adjudicationAttempted=True, adjudicatorId="synthetic-reviewer-c",
                           adjudicationRationale="synthetic rationale", adjudicatedLabel=0)
                      for row in self.inventory]
        with self.assertRaisesRegex(ValueError, "requires a recorded third reviewer for disagreement"):
            evaluate(incomplete, {pair_id: 0 for pair_id in self.labels},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")

    def test_unknown_labels_cannot_imply_annotation_attempts(self):
        inventory = copy.deepcopy(self.inventory)
        for row in inventory:
            row.pop("annotation1Attempted")
            row.pop("annotation2Attempted")
        with self.assertRaisesRegex(ValueError, "attempt flags must be booleans"):
            evaluate(inventory, {pair_id: None for pair_id in self.labels},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")
        incomplete = copy.deepcopy(self.inventory)
        incomplete[0].update(annotation1Attempted=False, annotation1ReviewerId=None,
                             annotation1=None, annotation1UnknownReason="not attempted")
        with self.assertRaisesRegex(ValueError, "requires two independent reviewer attempts"):
            evaluate(incomplete, self.labels, scorer=lambda _vector: 0.1,
                     dataset_kind="synthetic")
        empty_failure = copy.deepcopy(self.inventory)
        empty_failure[0].update(annotation1=None, annotation1Failure="",
                                annotation1UnknownReason=None, annotation2=None,
                                annotation2UnknownReason="insufficient-context")
        with self.assertRaisesRegex(ValueError, "failure must be nonempty"):
            evaluate(empty_failure, {**self.labels, "p0": None},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")

    def test_reviewer_and_adjudicator_ids_must_be_independent(self):
        same_reviewers = [dict(row, annotation1ReviewerId="same-reviewer",
                               annotation2ReviewerId="same-reviewer")
                          for row in self.inventory]
        with self.assertRaisesRegex(ValueError, "reviewers must have distinct"):
            evaluate(same_reviewers, self.labels, scorer=lambda _vector: 0.1,
                     dataset_kind="synthetic")
        same_reviewer_and_adjudicator = [dict(
            row, annotation1=0, annotation2=1, annotation1UnknownReason=None,
            annotation2UnknownReason=None, adjudicationAttempted=True,
            adjudicatorId="synthetic-reviewer-a", adjudicatedLabel=0,
            adjudicationRationale="synthetic rationale") for row in self.inventory]
        with self.assertRaisesRegex(ValueError, "adjudicator ID must differ"):
            evaluate(same_reviewer_and_adjudicator, {pair_id: 0 for pair_id in self.labels},
                     scorer=lambda _vector: 0.1, dataset_kind="synthetic")

    def test_calibrated_probabilities_get_brier_and_sparse_bins(self):
        report = self.run_eval(lambda _vector: {"status": "proposal", "score": 0.5, "probability": 0.7})
        metric = report["budgets"]["predictor"]["100"]["calibration"]
        self.assertIsNotNone(metric["brier"])
        self.assertEqual(len(metric["reliabilityBins"]), 5)
        self.assertTrue(all(item["status"] == "too-sparse" for item in metric["reliabilityBins"]))
        self.assertEqual(metric["probabilityClaimStatus"], "unvalidated-scorer-supplied")
        self.assertFalse(metric["probabilityProvenanceValidated"])

    def test_rejects_nonholdout_duplicate_or_mismatched_label_inventory(self):
        with self.assertRaises(ValueError):
            evaluate([dict(self.inventory[0], partition="train")], {"p0": 1},
                     scorer=lambda *_: 1, dataset_kind="synthetic")
        with self.assertRaises(ValueError):
            evaluate(self.inventory + [self.inventory[0]], self.labels,
                     scorer=lambda *_: 1, dataset_kind="synthetic")
        reversed_duplicate = dict(self.inventory[0], pairId="another-id",
                                  request={**self.inventory[0]["request"],
                                           "operations": list(reversed(self.inventory[0]["request"]["operations"]))})
        with self.assertRaises(ValueError):
            evaluate(self.inventory + [reversed_duplicate], {**self.labels, "another-id": 0},
                     scorer=lambda *_: 1, dataset_kind="synthetic")
        with self.assertRaises(ValueError):
            evaluate(self.inventory, {"p0": 1}, scorer=lambda *_: 1, dataset_kind="synthetic")

    def test_rejects_real_source_claim(self):
        with self.assertRaises(ValueError):
            evaluate(self.inventory, self.labels, scorer=lambda *_: 1, dataset_kind="prospective")

    def test_divergent_and_inconclusive_mapping_is_tested_without_a_verifier_seam(self):
        selected = self.inventory[:2]
        verdicts = {"p0": {"status": "divergent"}, "p1": {"status": "inconclusive"}}
        metrics = _metrics(selected, self.labels, selected, verdicts, ["f1"])
        self.assertEqual(metrics["actualVerifierCalls"], 2)
        self.assertEqual(metrics["verifierStatuses"]["divergent"], 1)
        self.assertEqual(metrics["verifierStatuses"]["inconclusive"], 1)
        self.assertEqual(metrics["verifiedBoundedUsefulYield"], 0)
        with self.assertRaises(TypeError):
            evaluate(self.inventory, self.labels, scorer=lambda *_: 1,
                     dataset_kind="synthetic", verifier=lambda _request: {"status": "verified-bounded"})
        default = _default_verifier(self.inventory[0]["request"])
        self.assertIs(default["executionAuthorization"], False)

    def test_permuted_label_control_uses_canonical_train_only_refit(self):
        training = [{"pairId": f"t{i}", "familyId": "train-family", "sessionId": f"s{i}",
                     "duplicateGroupId": f"duplicate-t{i}",
                     "partition": "train", "features": {
                         "baseSize": i, "sameAnchor": i % 2, "anchorDistance": i,
                         "firstLength": i + 1, "secondLength": i + 2, "lexicalOverlap": i / 5,
                     }}
                    for i in range(5)]
        train_labels = {"t0": 1, "t1": 0, "t2": 1, "t3": 0, "t4": None}
        permuted = permute_training_labels(training, train_labels)
        self.assertEqual(permuted, permute_training_labels(training, train_labels))
        reordered = permute_training_labels(list(reversed(training)), train_labels)
        self.assertEqual({row["pairId"]: row["label"] for row in permuted},
                         {row["pairId"]: row["label"] for row in reordered})
        self.assertEqual([row["pairId"] for row in reordered], sorted(row["pairId"] for row in training))
        self.assertEqual([r["label"] for r in permuted].count(None), 1)
        calibration = [{"pairId": f"c{i}", "familyId": "calibration-family",
                        "sessionId": f"cs{i}", "duplicateGroupId": f"duplicate-c{i}",
                        "partition": "calibration",
                        "features": {"baseSize": i + 5, "sameAnchor": i % 2,
                                     "anchorDistance": i + 5, "firstLength": i + 6,
                                     "secondLength": i + 7, "lexicalOverlap": (i + 1) / 5}}
                       for i in range(2)]
        report = evaluate(self.inventory, self.labels, scorer=lambda *_: 1,
                          dataset_kind="synthetic", training_inventory=training,
                          training_labels=train_labels, calibration_inventory=calibration,
                          calibration_labels={"c0": 1, "c1": 0})
        control = report["permutedLabelNegativeControl"]
        self.assertEqual(control["status"], "available")
        self.assertEqual(control["seed"], 0)
        self.assertTrue(control["fitInputCommitmentsVerified"])
        self.assertTrue(control["trainingLabelPermutationVerified"])
        self.assertNotIn("fitProvenanceVerified", control)
        self.assertTrue(control["trainingAssignmentChanged"])
        self.assertTrue(control["classCountsPreserved"])
        self.assertFalse(control["holdoutLabelsPermuted"])
        self.assertFalse(control["holdoutRowsOrLabelsUsedForFit"])
        self.assertFalse(control["factoryUsed"])
        self.assertEqual(set(control["metricsByBudget"]), {"25", "50", "100"})
        self.assertEqual(control["metricsByBudget"]["50"]["budgetCeiling"], 2)
        self.assertEqual(control["metricsByBudget"]["50"]["actualVerifierCalls"], 2)
        self.assertEqual(control["metricsByBudget"]["50"]["verifierWork"], {
            "submittedEvidenceProductionCount": 2,
            "verifierInvocationCount": 2,
            "verifierEvidenceRegenerationCount": 2,
        })
        self.assertIn("not a policy-arm cost comparison", control["costAccounting"])
        self.assertEqual(len(control["artifactHash"]), 64)
        self.assertEqual(control["trainingInputCommitment"], digest(permuted))
        expected_calibration = [{**row, "label": {"c0": 1, "c1": 0}[row["pairId"]]}
                                for row in calibration]
        self.assertEqual(control["calibrationInputCommitment"], digest(expected_calibration))
        self.assertGreaterEqual(control["fitSeconds"], 0)
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        binary_train = [{"pairId": "left", "familyId": "f", "sessionId": "s1",
                         "duplicateGroupId": "duplicate-left",
                         "partition": "train", "features": features},
                        {"pairId": "right", "familyId": "f", "sessionId": "s2",
                         "duplicateGroupId": "duplicate-right",
                         "partition": "train", "features": features}]
        binary = permute_training_labels(binary_train, {"left": 0, "right": 1})
        self.assertEqual({row["label"] for row in binary}, {0, 1})
        self.assertNotEqual([row["label"] for row in binary], [0, 1])

    def test_negative_control_is_unavailable_without_separate_fit_inputs(self):
        report = self.run_eval(lambda *_: 1)
        self.assertEqual(report["permutedLabelNegativeControl"]["status"], "unavailable")
        self.assertFalse(report["permutedLabelNegativeControl"]["holdoutLabelsPermuted"])

    def test_negative_control_is_unavailable_when_no_class_preserving_change_exists(self):
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        training = [{"pairId": "t0", "familyId": "f", "sessionId": "s0",
                     "duplicateGroupId": "duplicate-t0",
                     "partition": "train", "features": features},
                    {"pairId": "t1", "familyId": "f", "sessionId": "s1",
                     "duplicateGroupId": "duplicate-t1",
                     "partition": "train", "features": features}]
        calibration = [{"pairId": "c0", "familyId": "cal", "sessionId": "cs0",
                        "duplicateGroupId": "duplicate-c0",
                        "partition": "calibration", "features": features},
                       {"pairId": "c1", "familyId": "cal", "sessionId": "cs1",
                        "duplicateGroupId": "duplicate-c1",
                        "partition": "calibration", "features": features}]
        report = evaluate(self.inventory, self.labels, scorer=lambda *_: 1,
                          dataset_kind="synthetic", training_inventory=training,
                          training_labels={"t0": 1, "t1": 1},
                          calibration_inventory=calibration,
                          calibration_labels={"c0": 1, "c1": 0})
        control = report["permutedLabelNegativeControl"]
        self.assertEqual(control["status"], "unavailable")
        self.assertFalse(control["fitInputCommitmentsVerified"])
        self.assertFalse(control["trainingLabelPermutationVerified"])
        self.assertNotIn("fitProvenanceVerified", control)

    def test_permuted_control_rejects_train_holdout_family_leakage(self):
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        training = [{"pairId": "t0", "familyId": "f1", "sessionId": "ts0",
                     "duplicateGroupId": "duplicate-t0",
                     "partition": "train", "features": features},
                    {"pairId": "t1", "familyId": "train", "sessionId": "ts1",
                     "duplicateGroupId": "duplicate-t1",
                     "partition": "train", "features": features}]
        calibration = [{"pairId": "c0", "familyId": "cal", "sessionId": "cs0",
                        "duplicateGroupId": "duplicate-c0",
                        "partition": "calibration", "features": features},
                       {"pairId": "c1", "familyId": "cal", "sessionId": "cs1",
                        "duplicateGroupId": "duplicate-c1",
                        "partition": "calibration", "features": features}]
        with self.assertRaisesRegex(ValueError, "families/sessions/duplicate groups must be disjoint"):
            self.run_eval(lambda *_: 1, training_inventory=training,
                          training_labels={"t0": 1, "t1": 0},
                          calibration_inventory=calibration,
                          calibration_labels={"c0": 1, "c1": 0})

    def test_permuted_control_rejects_duplicate_group_leakage(self):
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        training = [{"pairId": "t0", "familyId": "train", "sessionId": "ts0",
                     "duplicateGroupId": "shared-group",
                     "partition": "train", "features": features},
                    {"pairId": "t1", "familyId": "train", "sessionId": "ts1",
                     "duplicateGroupId": "duplicate-t1",
                     "partition": "train", "features": features}]
        calibration = [{"pairId": "c0", "familyId": "cal", "sessionId": "cs0",
                        "duplicateGroupId": "duplicate-c0",
                        "partition": "calibration", "features": features},
                       {"pairId": "c1", "familyId": "cal", "sessionId": "cs1",
                        "duplicateGroupId": "duplicate-c1",
                        "partition": "calibration", "features": features}]
        holdout = copy.deepcopy(self.inventory)
        holdout[0]["duplicateGroupId"] = "shared-group"
        with self.assertRaisesRegex(ValueError, "families/sessions/duplicate groups must be disjoint"):
            evaluate(holdout, self.labels, scorer=lambda *_: 1, dataset_kind="synthetic",
                     training_inventory=training, training_labels={"t0": 1, "t1": 0},
                     calibration_inventory=calibration,
                     calibration_labels={"c0": 1, "c1": 0})

    def test_permuted_control_aborts_when_calibration_lacks_both_classes(self):
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        training = [{"pairId": "t0", "familyId": "train", "sessionId": "ts0",
                     "duplicateGroupId": "duplicate-t0",
                     "partition": "train", "features": features},
                    {"pairId": "t1", "familyId": "train", "sessionId": "ts1",
                     "duplicateGroupId": "duplicate-t1",
                     "partition": "train", "features": features}]
        calibration = [{"pairId": "c0", "familyId": "cal", "sessionId": "cs0",
                        "duplicateGroupId": "duplicate-c0",
                        "partition": "calibration", "features": features},
                       {"pairId": "c1", "familyId": "cal", "sessionId": "cs1",
                        "duplicateGroupId": "duplicate-c1",
                        "partition": "calibration", "features": features}]
        with self.assertRaisesRegex(ValueError, "calibration partition requires both known classes"):
            self.run_eval(lambda *_: 1, training_inventory=training,
                          training_labels={"t0": 1, "t1": 0},
                          calibration_inventory=calibration,
                          calibration_labels={"c0": 1, "c1": 1})

    def test_label_permutation_rejects_extra_label_or_holdout_fields(self):
        valid_features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                               "firstLength", "secondLength", "lexicalOverlap")}
        base_row = {"pairId": "t", "familyId": "f", "sessionId": "s",
                    "duplicateGroupId": "duplicate-t",
                    "partition": "train", "features": valid_features}
        with self.assertRaises(ValueError):
            permute_training_labels([{**base_row, "futureLabel": 1}], {"t": 1})
        with self.assertRaises(ValueError):
            permute_training_labels([{**base_row, "partition": "holdout"}], {"t": 1})

    def test_inference_and_scoring_are_separate_timing_phases(self):
        report = self.run_eval(lambda *_: 1)
        baseline = report["budgets"]["baseline"]["50"]["timing"]["phaseMedianSeconds"]
        predictor = report["budgets"]["predictor"]["50"]["timing"]["phaseMedianSeconds"]
        self.assertEqual(baseline["inferenceSeconds"], 0)
        self.assertEqual(baseline["preparationSeconds"], 0)
        self.assertGreater(predictor["inferenceSeconds"], 0)
        self.assertGreater(predictor["preparationSeconds"], 0)
        self.assertGreater(predictor["scoringSeconds"], 0)
        self.assertGreater(baseline["submittedEvidenceProductionSeconds"], 0)
        self.assertGreater(baseline["verifierInvocationSeconds"], 0)
        self.assertAlmostEqual(
            baseline["verificationSeconds"],
            baseline["submittedEvidenceProductionSeconds"] + baseline["verifierInvocationSeconds"],
            places=5)
        result = report["budgets"]["baseline"]["50"]
        self.assertEqual(result["verifierWork"]["submittedEvidenceProductionCount"],
                         result["actualVerifierCalls"])
        self.assertEqual(result["verifierWork"]["verifierInvocationCount"],
                         result["actualVerifierCalls"])
        self.assertEqual(result["verifierWork"]["verifierEvidenceRegenerationCount"],
                         result["actualVerifierCalls"])

    def test_fitted_artifact_runs_end_to_end_through_request_preparation_and_evaluation(self):
        def training_row(pair_id, family, session, partition, label, offset):
            return {"pairId": pair_id, "familyId": family, "sessionId": session,
                    "duplicateGroupId": f"duplicate-{pair_id}",
                    "partition": partition, "label": label,
                    "features": {name: float(index + offset) for index, name in enumerate(FEATURES)}}
        rows = [training_row("t0", "train", "s0", "train", 0, 0),
                training_row("t1", "train", "s1", "train", 1, 2),
                training_row("c0", "calibration", "s2", "calibration", 0, 3),
                training_row("c1", "calibration", "s3", "calibration", 1, 4),
                training_row("h0", "holdout-train-fixture", "s4", "holdout", None, 5),
                training_row("h1", "holdout-train-fixture", "s5", "holdout", None, 6),
                training_row("h2", "holdout-train-fixture", "s6", "holdout", None, 7)]
        artifact = fit(rows, model_id="evaluation-model", dataset_kind="synthetic")
        artifact_hash = digest(artifact)

        def scorer(vector):
            return score(vector, artifact, expected_hash=artifact_hash,
                         expected_model_id="evaluation-model")

        report = evaluate(self.inventory, self.labels, scorer=scorer, dataset_kind="synthetic")
        result = report["budgets"]["predictor"]["50"]
        phases = result["timing"]["phaseMedianSeconds"]
        self.assertEqual(report["sourceKind"], "synthetic")
        self.assertGreater(phases["inferenceSeconds"], 0)
        self.assertEqual(result["actualVerifierCalls"], 2)
        self.assertEqual(result["verifierWork"]["verifierEvidenceRegenerationCount"], 2)
        self.assertFalse(report["executionAuthorization"])
        self.assertIn("unvalidated-scorer-supplied",
                      result["calibration"]["probabilityClaimStatus"])
        self.assertIn("source-to-request extraction is outside", report["preparationMeasurement"]["limitation"])

    def test_holdout_feature_bait_is_never_forwarded_to_scorer_or_preparer(self):
        bait = copy.deepcopy(self.inventory)
        for row in bait:
            row["features"] = {"hiddenLabel": self.labels[row["pairId"]]}
            row["featureVector"] = {"hiddenLabel": self.labels[row["pairId"]]}
            row["inputHash"] = str(self.labels[row["pairId"]])
            row["requestHash"] = "useful" if self.labels[row["pairId"]] == 1 else "not-useful"
            row["sourceKind"] = str(self.labels[row["pairId"]])
        seen = []

        def prepare(row):
            seen.append(("prepare", set(row)))
            self.assertEqual(set(row), {"request"})
            self.assertNotIn("features", row)
            self.assertNotIn("featureVector", row)
            return prepare_request(row["request"], source_kind="synthetic")

        def scorer(vector):
            seen.append(("score", set(vector)))
            self.assertEqual(set(vector), {"version", "features"})
            self.assertNotIn("request", vector)
            self.assertNotIn("inputHash", vector)
            return 0.5

        evaluate(bait, self.labels, scorer=scorer, preparation=prepare,
                 dataset_kind="synthetic")
        self.assertTrue(seen)

    def test_preparer_cannot_inject_noncanonical_or_extra_features(self):
        scorer_calls = []

        def scorer(vector):
            scorer_calls.append(vector)
            return 0.5

        def wrong_value(row):
            prepared = prepare_request(row["request"], source_kind="synthetic")
            prepared["features"]["baseSize"] = 3
            return prepared

        with self.assertRaisesRegex(ValueError, "differ from the canonical"):
            self.run_eval(scorer, preparation=wrong_value)
        self.assertEqual(scorer_calls, [])

        def unexpected_field(row):
            prepared = prepare_request(row["request"], source_kind="synthetic")
            prepared["unexpected"] = "label-derived"
            return prepared

        with self.assertRaisesRegex(ValueError, "request-bound versioned"):
            self.run_eval(scorer, preparation=unexpected_field)
        self.assertEqual(scorer_calls, [])

    def test_family_prevalence_differences_annotation_failures_and_complete_serialization(self):
        inventory = [
            *self.inventory[:2],
            dict(self.inventory[2], annotation1=None, annotation2=None, adjudicatedLabel=None,
                 annotation1Attempted=True, annotation1Failure="timeout",
                 annotation1UnknownReason="review timed out", annotation2Attempted=True,
                 annotation2UnknownReason="no sufficient context"),
            self.inventory[3],
        ]
        report = evaluate(inventory, self.labels,
                          scorer=lambda vector: vector["features"]["sameAnchor"],
                          dataset_kind="synthetic")
        f1 = report["holdoutInventoryByFamily"]["f1"]
        self.assertEqual(f1["inventoryPairs"], 2)
        self.assertEqual(f1["inventoryLabels"], {"knownUseful": 1, "knownNotUseful": 1, "unknown": 0})
        self.assertEqual(f1["knownClassPrevalence"]["useful"], 0.5)
        annotations = report["annotationAgreementByFamily"]["f2"]
        self.assertEqual(annotations["reviewers"]["annotation1"]["failed"], 1)
        self.assertEqual(annotations["reviewers"]["annotation2"]["missingField"], 1)
        self.assertEqual(annotations["reviewers"]["annotation1"]["failureRateAmongAttempts"], 0.5)
        self.assertEqual(annotations["reviewers"]["annotation1"]["missingFieldRateAmongAttempts"], 0.0)
        self.assertEqual(annotations["reviewers"]["annotation2"]["missingFieldRateAmongAttempts"], 0.5)
        self.assertEqual(annotations["unresolvedOrMissing"], 1)
        difference = report["policyDifferencesByFamilyAndBudget"]["50"]["f1"]
        self.assertIn("verifiedBoundedUsefulYieldDifferencePredictorMinusBaseline", difference)
        policy = report["budgets"]["predictor"]["50"]
        self.assertGreater(policy["timing"]["phaseMedianSeconds"]["serializationSeconds"], 0)
        self.assertIn("serializationTimingNote", policy)
        self.assertTrue(report["finalReportSerializationIncludedInPolicyTotals"])
        self.assertGreaterEqual(report["reportSerializationSeconds"], 0)


if __name__ == "__main__":
    unittest.main()
