import copy
import unittest
from unittest.mock import patch

from agent_braid.native_predictor import ARTIFACT_VERSION as SYNTHETIC_ARTIFACT_VERSION
from agent_braid.native_predictor import FEATURE_VERSION as SYNTHETIC_FEATURE_VERSION
from agent_braid.native_predictor import FEATURES
from agent_braid.native_predictor_training import (
    ARTIFACT_VERSION, FEATURE_VERSION, _fit_calibration, digest, feature_vector, fit,
    prepare_request, score, score_request, serialize_artifact,
)
from agent_braid.native_predictor import extract_features
from agent_braid.structured_exchange import ROOT, VERSION


def row(pair, family, session, partition, label, offset=0):
    values = {name: float(index + offset) for index, name in enumerate(FEATURES)}
    return {"pairId": pair, "familyId": family, "sessionId": session,
            "duplicateGroupId": f"duplicate-{pair}",
            "partition": partition, "features": values, "label": label}


def dataset():
    return [row("t0", "train-family", "train-session", "train", 0, 0),
            row("t1", "train-family", "train-session", "train", 1, 2),
            row("c0", "cal-family", "cal-session", "calibration", 0, 3),
            row("c1", "cal-family", "cal-session", "calibration", 1, 4),
            row("h0", "hold-family-0", "hold-session-0", "holdout", None, 7),
            row("h1", "hold-family-1", "hold-session-1", "holdout", None, 8),
            row("h2", "hold-family-2", "hold-session-2", "holdout", None, 9)]


def receipt():
    return {"familyCounts": {"train": 1, "calibration": 1, "holdout": 3},
            "knownTotal": 100, "holdoutPositive": 20, "holdoutNegative": 20}


def fitted(rows=None, coverage=None):
    return fit(dataset() if rows is None else rows, model_id="m",
               dataset_kind="synthetic", coverage_receipt=coverage)


def request():
    return {"model": VERSION, "base": [{"id": "base", "value": "anchor"}],
            "operations": [
                {"id": "op-a", "kind": "insert", "anchorId": ROOT,
                 "newId": "new-a", "value": "shared proposal"},
                {"id": "op-b", "kind": "insert", "anchorId": "base",
                 "newId": "new-b", "value": "second proposal"},
            ]}


class NativePredictorTrainingTests(unittest.TestCase):
    def test_request_preparation_connects_frozen_synthetic_features_to_trained_inference(self):
        candidate = request()
        legacy = extract_features(candidate, source_kind="synthetic")
        vector = prepare_request(candidate, source_kind="synthetic")
        self.assertNotEqual(vector["version"], SYNTHETIC_FEATURE_VERSION)
        self.assertEqual(vector["version"], FEATURE_VERSION)
        self.assertEqual(vector["features"], legacy["features"])
        self.assertEqual(vector["inputHash"], digest(candidate))
        artifact = fitted()
        result = score_request(candidate, artifact, source_kind="synthetic",
                               expected_hash=digest(artifact), expected_model_id="m",
                               expected_input_hash=digest(candidate))
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["inputHash"], digest(candidate))
        self.assertEqual(result["featureVersion"], FEATURE_VERSION)
        self.assertEqual(result["artifactHash"], digest(artifact))
        self.assertFalse(result["executionAuthorization"])

    def test_request_bound_inference_rejects_drift_and_non_synthetic_inputs(self):
        candidate = request()
        vector = prepare_request(candidate, source_kind="synthetic")
        artifact = fitted()
        kwargs = {"expected_hash": digest(artifact), "expected_model_id": "m"}
        drifted = copy.deepcopy(vector)
        drifted["features"][FEATURES[0]] += 1
        # A caller cannot smuggle a request identity into the fixture API,
        # even when the request hash is intact.
        self.assertEqual(score(drifted, artifact, **kwargs,
                               expected_input_hash=digest(candidate))["status"], "abstain")
        forged_bound = copy.deepcopy(vector)
        forged_bound["features"][FEATURES[0]] += 1000
        self.assertEqual(score(forged_bound, artifact, **kwargs)["status"], "abstain")
        self.assertEqual(score_request(candidate, artifact, source_kind="synthetic",
                                        **kwargs, expected_input_hash="0" * 64)["status"], "abstain")
        with self.assertRaisesRegex(ValueError, "only explicitly synthetic"):
            prepare_request(candidate, source_kind="prospective")

    def test_extreme_request_bound_score_never_calls_verifier_or_authorizes_execution(self):
        artifact = fitted()
        artifact["weights"] = {name: 0.0 for name in FEATURES}
        artifact["bias"] = 1_000_000.0
        with patch("agent_braid.structured_exchange.produce",
                   side_effect=AssertionError("predictor called producer")) as producer, \
             patch("agent_braid.structured_exchange.verify",
                   side_effect=AssertionError("predictor called verifier")) as verifier:
            result = score_request(request(), artifact, source_kind="synthetic",
                                   expected_hash=digest(artifact), expected_model_id="m")
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["score"], 1_000_000.0)
        self.assertNotIn("verdict", result)
        self.assertIsNone(result["certificate"])
        self.assertFalse(result["executionAuthorization"])
        producer.assert_not_called()
        verifier.assert_not_called()

    def test_fit_is_deterministic_and_versions_are_separate(self):
        first = fit(dataset(), model_id="model-1", dataset_kind="synthetic")
        second = fit(list(reversed(dataset())), model_id="model-1", dataset_kind="synthetic")
        self.assertEqual(first, second)
        self.assertEqual(first["calibrationFamilyWeighting"],
                         "single-family-rows-founder-selected-pending-review")
        self.assertNotEqual(FEATURE_VERSION, SYNTHETIC_FEATURE_VERSION)
        self.assertNotEqual(ARTIFACT_VERSION, SYNTHETIC_ARTIFACT_VERSION)

    def test_family_and_session_cannot_cross_partitions(self):
        rows = dataset()
        rows[-1]["familyId"] = "train-family"
        with self.assertRaisesRegex(ValueError, "family crosses"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        rows = dataset()
        rows[-1]["sessionId"] = "train-session"
        with self.assertRaisesRegex(ValueError, "session crosses"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_calibration_partition_requires_one_predeclared_family(self):
        rows = dataset()
        rows[3]["familyId"] = "second-calibration-family"
        with self.assertRaisesRegex(ValueError, "calibration requires exactly one family"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_duplicate_groups_cannot_cross_partitions_or_be_omitted(self):
        rows = dataset()
        rows[-1]["duplicateGroupId"] = rows[0]["duplicateGroupId"]
        with self.assertRaisesRegex(ValueError, "duplicate group crosses"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        rows = dataset()
        del rows[0]["duplicateGroupId"]
        with self.assertRaisesRegex(ValueError, "missing or unknown fields"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_duplicate_and_malformed_ids_rejected(self):
        rows = dataset()
        rows[1]["pairId"] = rows[0]["pairId"]
        with self.assertRaisesRegex(ValueError, "duplicate pair"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        rows = dataset()
        rows[0]["familyId"] = ""
        with self.assertRaisesRegex(ValueError, "family identity"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_missing_train_or_calibration_class_rejected(self):
        rows = dataset()
        rows[1]["label"] = 0
        with self.assertRaisesRegex(ValueError, "train partition"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        rows = dataset()
        rows[3]["label"] = 0
        with self.assertRaisesRegex(ValueError, "calibration partition"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_holdout_label_is_rejected_and_none_unknown_allowed(self):
        rows = dataset()
        rows[-1]["label"] = 1
        with self.assertRaisesRegex(ValueError, "holdout labels"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        rows = dataset()
        rows[0]["label"] = None
        with self.assertRaisesRegex(ValueError, "train partition"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_constant_feature_has_zero_normalized_value(self):
        rows = dataset()
        for item in rows:
            item["features"][FEATURES[0]] = 9.0
        artifact = fit(rows, model_id="m", dataset_kind="synthetic")
        self.assertEqual(artifact["normalization"]["scales"][FEATURES[0]], 0.0)
        self.assertEqual(artifact["weights"][FEATURES[0]], 0.0)
        self.assertEqual(score(feature_vector({**rows[0]["features"], FEATURES[0]: 100.0}), artifact,
                              expected_hash=digest(artifact), expected_model_id="m")["status"], "proposal")

    def test_nonfinite_features_fail_closed(self):
        rows = dataset()
        rows[0]["features"][FEATURES[0]] = float("nan")
        with self.assertRaisesRegex(ValueError, "finite"):
            fit(rows, model_id="m", dataset_kind="synthetic")
        values = {name: 1.0 for name in FEATURES}
        values[FEATURES[0]] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            feature_vector(values)

    def test_fit_is_synthetic_only_and_caller_receipts_cannot_authorize(self):
        for kind in ("prospective", "real", "admitted"):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "only explicitly designated synthetic"):
                fit(dataset(), model_id="m", dataset_kind=kind, coverage_receipt=receipt())
        with self.assertRaisesRegex(ValueError, "caller-supplied coverage receipts"):
            fit(dataset(), model_id="m", dataset_kind="synthetic", coverage_receipt=receipt())
        artifact = fitted()
        self.assertEqual(artifact["datasetKind"], "synthetic")
        self.assertEqual(artifact["provenance"],
                         {"kind": "synthetic-fixture-only", "realDataEligible": False})
        self.assertEqual(artifact["coverageReceipt"]["kind"], "synthetic-descriptive-only")
        self.assertFalse(artifact["coverageReceipt"]["satisfiesRealReadiness"])
        self.assertEqual(artifact["coverageReceipt"]["knownTotal"], 4)

    def test_artifact_validation_rejects_non_synthetic_provenance(self):
        artifact = fitted()
        artifact["datasetKind"] = "prospective"
        with self.assertRaisesRegex(ValueError, "only synthetic artifacts"):
            # Rebind the commitment to exercise the dataset-kind check.
            from agent_braid.native_predictor_training import validate_artifact
            validate_artifact(artifact, expected_hash=digest(artifact), expected_model_id="m")

    def test_artifact_commits_selected_calibration_family_weighting(self):
        artifact = fitted()
        artifact["calibrationFamilyWeighting"] = "pooled-rows-provisional"
        with self.assertRaisesRegex(ValueError, "unsupported calibration-family weighting"):
            from agent_braid.native_predictor_training import validate_artifact
            validate_artifact(artifact, expected_hash=digest(artifact), expected_model_id="m")


    def test_calibration_uses_its_partition_and_holdout_features_are_isolated(self):
        baseline_rows = dataset()
        baseline = fit(baseline_rows, model_id="m", dataset_kind="synthetic")
        changed_rows = copy.deepcopy(baseline_rows)
        changed_rows[2]["label"], changed_rows[3]["label"] = 1, 0
        changed_rows[2]["features"] = {key: value + 100 for key, value in changed_rows[2]["features"].items()}
        changed_rows[3]["features"] = {key: value - 100 for key, value in changed_rows[3]["features"].items()}
        calibration_changed = fit(changed_rows, model_id="m", dataset_kind="synthetic")
        for field in ("weights", "bias", "normalization"):
            self.assertEqual(baseline[field], calibration_changed[field])
        self.assertNotEqual(baseline["inputCommitments"]["calibration"],
                            calibration_changed["inputCommitments"]["calibration"])

        changed_rows = copy.deepcopy(baseline_rows)
        changed_rows[-1]["features"] = {key: value + 1000 for key, value in changed_rows[-1]["features"].items()}
        holdout_changed = fit(changed_rows, model_id="m", dataset_kind="synthetic")
        self.assertEqual(baseline, holdout_changed)

    def test_sorted_train_and_calibration_commitments_bind_exact_inputs(self):
        rows = dataset()
        artifact = fit(rows, model_id="m", dataset_kind="synthetic")
        train = sorted([entry for entry in rows if entry["partition"] == "train"],
                       key=lambda entry: entry["pairId"])
        calibration = sorted([entry for entry in rows if entry["partition"] == "calibration"],
                             key=lambda entry: entry["pairId"])
        self.assertEqual(artifact["inputCommitments"]["train"], digest(train))
        self.assertEqual(artifact["inputCommitments"]["calibration"], digest(calibration))
        changed = copy.deepcopy(rows)
        changed[0]["features"][FEATURES[0]] += 1
        retrained = fit(changed, model_id="m", dataset_kind="synthetic")
        self.assertNotEqual(artifact["inputCommitments"]["train"],
                            retrained["inputCommitments"]["train"])

    def test_zero_calibration_variance_omits_probability(self):
        rows = dataset()
        for item in rows:
            item["features"] = {name: 3.0 for name in FEATURES}
        artifact = fit(rows, model_id="m", dataset_kind="synthetic")
        self.assertEqual(artifact["calibration"]["status"], "unavailable")
        self.assertEqual(artifact["calibration"]["reason"], "zero-score-variance")
        prediction = score(feature_vector(rows[0]["features"]), artifact,
                           expected_hash=digest(artifact), expected_model_id="m")
        self.assertNotIn("probability", prediction)
        self.assertFalse(prediction["brierEligible"])

    def test_fixed_grid_tie_break_prefers_smaller_slope_then_intercept(self):
        calibration = _fit_calibration([-1.0, 1.0], [1, 0])
        self.assertEqual(calibration["status"], "calibrated")
        self.assertEqual(calibration["slope"], 0.0)
        self.assertEqual(calibration["intercept"], 0.0)

    def test_overflow_from_finite_features_is_a_controlled_fit_failure(self):
        rows = dataset()
        rows[0]["features"][FEATURES[0]] = 1e308
        rows[1]["features"][FEATURES[0]] = -1e308
        with self.assertRaisesRegex(ValueError, "normalization overflow"):
            fit(rows, model_id="m", dataset_kind="synthetic")

    def test_commitment_tampering_abstains_and_serialization_checks(self):
        artifact = fitted()
        commitment = digest(artifact)
        self.assertTrue(serialize_artifact(artifact, expected_hash=commitment,
                                           expected_model_id="m").endswith(b"\n"))
        changed = copy.deepcopy(artifact)
        changed["bias"] += 1
        result = score(feature_vector(dataset()[0]["features"]), changed,
                       expected_hash=commitment, expected_model_id="m")
        self.assertEqual(result["status"], "abstain")
        with self.assertRaisesRegex(ValueError, "commitment"):
            serialize_artifact(changed, expected_hash=commitment, expected_model_id="m")
        changed = copy.deepcopy(artifact)
        changed["inputCommitments"]["train"] = "0" * 64
        self.assertEqual(score(feature_vector(dataset()[0]["features"]), changed,
                               expected_hash=commitment, expected_model_id="m")["status"], "abstain")
        off_grid = copy.deepcopy(artifact)
        off_grid["calibration"]["intercept"] += 0.001
        with self.assertRaisesRegex(ValueError, "calibrated parameters"):
            serialize_artifact(off_grid, expected_hash=digest(off_grid), expected_model_id="m")

    def test_invalid_feature_version_abstains_and_boundary_is_advisory(self):
        artifact = fitted()
        vector = feature_vector(dataset()[0]["features"])
        vector["version"] = SYNTHETIC_FEATURE_VERSION
        result = score(vector, artifact, expected_hash=digest(artifact), expected_model_id="m")
        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["certificate"])
        self.assertFalse(result["executionAuthorization"])
        self.assertNotIn("verdict", result)

    def test_valid_calibration_returns_descriptive_probability(self):
        artifact = fitted()
        vector = feature_vector(dataset()[0]["features"])
        result = score(vector, artifact, expected_hash=digest(artifact), expected_model_id="m")
        self.assertEqual(result["status"], "proposal")
        self.assertIn("probability", result)
        self.assertGreaterEqual(result["probability"], 0.0)
        self.assertLessEqual(result["probability"], 1.0)


if __name__ == "__main__":
    unittest.main()
