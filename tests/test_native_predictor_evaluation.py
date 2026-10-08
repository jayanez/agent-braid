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
from agent_braid.native_predictor_training import digest, fit, score_request
from agent_braid.structured_exchange import ROOT, VERSION


def _row(pair, family, a, b):
    return {"pairId": pair, "familyId": family, "partition": "holdout",
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

    def run_eval(self, scorer, **kwargs):
        return evaluate(self.inventory, self.labels, scorer=scorer, dataset_kind="synthetic", **kwargs)

    def test_floor_budget_ties_and_verified_usefulness_bounds(self):
        # A tied scorer preserves inventory order; floor(.25 * 4) calls one.
        report = self.run_eval(lambda _row, _prepared: 0.0)
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

    def test_abstentions_use_no_calls_and_continue_down_ranking(self):
        calls = []
        def scorer(row, _prepared):
            index = len(calls) % len(self.inventory)
            calls.append(index)
            return None if index == 0 else {"status": "proposal", "score": 10 if index == 1 else 0}
        report = self.run_eval(scorer)
        result = report["budgets"]["predictor"]["25"]
        self.assertEqual(result["abstentions"], 1)
        self.assertEqual(result["actualVerifierCalls"], 1)
        self.assertEqual(result["unusedCalls"], 0)

    def test_label_and_family_fields_are_not_passed_to_scorer_or_preparer(self):
        seen = []
        def scorer(row, prepared):
            self.assertEqual(set(row), {"request"})
            self.assertNotIn("familyId", row)
            self.assertNotIn("annotation1", row)
            self.assertNotIn("label", row)
            self.assertEqual(prepared, "prepared")
            seen.append(row["request"])
            return 1
        def preparation(row):
            self.assertEqual(set(row), {"request"})
            self.assertNotIn("annotation1", row)
            self.assertNotIn("label", row)
            return "prepared"
        report = self.run_eval(scorer, preparation=preparation)
        self.assertTrue(seen)
        self.assertEqual(report["sourceKind"], "synthetic")
        self.assertFalse(report["executionAuthorization"])
        self.assertEqual(report["preparationMeasurement"]["sourceExtraction"],
                         "not measured; evaluator input is already an in-memory validated request")

    def test_callbacks_cannot_mutate_inventory_or_verified_requests(self):
        original = self.inventory[0]["request"]["base"][0]["value"]
        def preparation(row):
            row["request"]["base"][0]["value"] = "prep mutation"
            return row["request"]
        def scorer(row, prepared):
            self.assertEqual(row["request"]["base"][0]["value"], original)
            prepared["base"][0]["value"] = "scorer mutation"
            row["request"]["operations"][0]["value"] = "scorer mutation"
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
        def scorer(row, _prepared):
            assert_blind(row)
            return 1
        def preparation(row):
            assert_blind(row)
            return row["request"]
        evaluate(hostile_rows, self.labels, scorer=scorer, preparation=preparation,
                 dataset_kind="synthetic")

    def test_annotations_and_calibration_are_descriptive_and_optional(self):
        inventory = [dict(row, annotation1=1, annotation2=0, adjudicatedLabel=None) for row in self.inventory]
        report = evaluate(inventory, self.labels, scorer=lambda _r, _p: 0.1,
                          dataset_kind="synthetic")
        self.assertEqual(report["annotationAgreementByFamily"]["f1"]["rawDisagreements"], 2)
        metric = report["budgets"]["predictor"]["50"]["calibration"]
        self.assertIsNone(metric["brier"])
        self.assertIn("reason", metric)

    def test_calibrated_probabilities_get_brier_and_sparse_bins(self):
        report = self.run_eval(lambda _r, _p: {"status": "proposal", "score": 0.5, "probability": 0.7})
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

    def test_negative_control_refits_from_seed_zero_permuted_train_labels_only(self):
        training = [{"pairId": f"t{i}", "familyId": "train-family", "sessionId": f"s{i}",
                     "partition": "train", "features": {
                         "baseSize": i, "sameAnchor": i % 2, "anchorDistance": i,
                         "firstLength": i + 1, "secondLength": i + 2, "lexicalOverlap": i / 5,
                     }}
                    for i in range(5)]
        train_labels = {"t0": 1, "t1": 0, "t2": 1, "t3": 0, "t4": None}
        permuted = permute_training_labels(training, train_labels)
        self.assertEqual(permuted, permute_training_labels(training, train_labels))
        self.assertEqual([r["label"] for r in permuted].count(None), 1)
        received = []
        def factory(rows):
            received.extend(rows)
            self.assertTrue(all(row["partition"] == "train" for row in rows))
            self.assertFalse(any(row["pairId"].startswith("p") for row in rows))
            return lambda _row, _prepared: 0.5
        report = evaluate(self.inventory, self.labels, scorer=lambda *_: 1,
                          dataset_kind="synthetic", training_inventory=training,
                          training_labels=train_labels, negative_control_scorer_factory=factory)
        control = report["permutedLabelNegativeControl"]
        self.assertEqual(control["status"], "available-synthetic-descriptive-only")
        self.assertEqual(control["seed"], 0)
        self.assertFalse(control["factoryReceivedHoldoutRowsOrLabels"])
        self.assertTrue(received)
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        binary_train = [{"pairId": "left", "familyId": "f", "sessionId": "s1",
                         "partition": "train", "features": features},
                        {"pairId": "right", "familyId": "f", "sessionId": "s2",
                         "partition": "train", "features": features}]
        binary = permute_training_labels(binary_train, {"left": 0, "right": 1})
        self.assertEqual({row["label"] for row in binary}, {0, 1})
        self.assertNotEqual([row["label"] for row in binary], [0, 1])

    def test_negative_control_is_unavailable_without_a_refit_factory(self):
        report = self.run_eval(lambda *_: 1)
        self.assertEqual(report["permutedLabelNegativeControl"]["status"], "unavailable")
        self.assertFalse(report["permutedLabelNegativeControl"]["holdoutLabelsPermuted"])

    def test_negative_control_is_unavailable_when_no_class_preserving_change_exists(self):
        features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                         "firstLength", "secondLength", "lexicalOverlap")}
        training = [{"pairId": "t0", "familyId": "f", "sessionId": "s0",
                     "partition": "train", "features": features},
                    {"pairId": "t1", "familyId": "f", "sessionId": "s1",
                     "partition": "train", "features": features}]
        factory_calls = []
        def factory(rows):
            factory_calls.append(rows)
            return lambda *_: 1
        report = evaluate(self.inventory, self.labels, scorer=lambda *_: 1,
                          dataset_kind="synthetic", training_inventory=training,
                          training_labels={"t0": 1, "t1": 1},
                          negative_control_scorer_factory=factory)
        control = report["permutedLabelNegativeControl"]
        self.assertEqual(control["status"], "unavailable")
        self.assertFalse(control["factoryRun"])
        self.assertEqual(factory_calls, [])

    def test_negative_control_factory_rejects_extra_label_or_holdout_fields(self):
        valid_features = {name: 0 for name in ("baseSize", "sameAnchor", "anchorDistance",
                                               "firstLength", "secondLength", "lexicalOverlap")}
        base_row = {"pairId": "t", "familyId": "f", "sessionId": "s",
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
        self.assertEqual(predictor["preparationSeconds"], 0)
        self.assertGreater(predictor["scoringSeconds"], 0)

    def test_fitted_artifact_runs_end_to_end_through_request_preparation_and_evaluation(self):
        def training_row(pair_id, family, session, partition, label, offset):
            return {"pairId": pair_id, "familyId": family, "sessionId": session,
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

        def scorer(row, _prepared):
            return score_request(row["request"], artifact, source_kind="synthetic",
                                 expected_hash=artifact_hash,
                                 expected_model_id="evaluation-model",
                                 expected_input_hash=digest(row["request"]))

        report = evaluate(self.inventory, self.labels, scorer=scorer, dataset_kind="synthetic")
        result = report["budgets"]["predictor"]["50"]
        phases = result["timing"]["phaseMedianSeconds"]
        self.assertEqual(report["sourceKind"], "synthetic")
        self.assertGreater(phases["inferenceSeconds"], 0)
        self.assertEqual(result["actualVerifierCalls"], 2)
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
            return None

        def scorer(row, _prepared):
            seen.append(("score", set(row)))
            self.assertEqual(set(row), {"request"})
            self.assertNotIn("features", row)
            self.assertNotIn("featureVector", row)
            return 0.5

        evaluate(bait, self.labels, scorer=scorer, preparation=prepare,
                 dataset_kind="synthetic")
        self.assertTrue(seen)

    def test_family_prevalence_differences_annotation_failures_and_complete_serialization(self):
        inventory = [
            dict(self.inventory[0], annotation1Attempted=True, annotation1Failure="timeout",
                 annotation2Attempted=True),
            dict(self.inventory[1], annotation1Attempted=True, annotation1=None,
                 annotation2Attempted=True, annotation2=0),
            *self.inventory[2:],
        ]
        report = evaluate(inventory, self.labels, scorer=lambda row, _p: 1 if row["request"]["operations"][0]["id"].startswith("p0") else 0,
                          dataset_kind="synthetic")
        f1 = report["holdoutInventoryByFamily"]["f1"]
        self.assertEqual(f1["inventoryPairs"], 2)
        self.assertEqual(f1["inventoryLabels"], {"knownUseful": 1, "knownNotUseful": 1, "unknown": 0})
        self.assertEqual(f1["knownClassPrevalence"]["useful"], 0.5)
        annotations = report["annotationAgreementByFamily"]["f1"]
        self.assertEqual(annotations["reviewers"]["annotation1"]["failed"], 1)
        self.assertEqual(annotations["reviewers"]["annotation2"]["missingField"], 1)
        self.assertEqual(annotations["reviewers"]["annotation1"]["failureRateAmongAttempts"], 0.5)
        self.assertEqual(annotations["reviewers"]["annotation1"]["missingFieldRateAmongAttempts"], 0.5)
        self.assertEqual(annotations["unresolvedOrMissing"], 2)
        difference = report["policyDifferencesByFamilyAndBudget"]["50"]["f1"]
        self.assertIn("verifiedBoundedUsefulYieldDifferencePredictorMinusBaseline", difference)
        policy = report["budgets"]["predictor"]["50"]
        self.assertGreater(policy["timing"]["phaseMedianSeconds"]["serializationSeconds"], 0)
        self.assertIn("serializationTimingNote", policy)
        self.assertFalse(report["finalReportSerializationIncludedInPolicyTotals"])
        self.assertGreaterEqual(report["reportSerializationSeconds"], 0)


if __name__ == "__main__":
    unittest.main()
