# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-019 contract anchors; real-model and eligible-holdout gates remain deferred."""

import copy
import json
import unittest
from unittest.mock import patch

from agent_braid.native_predictor import (
    ARTIFACT_VERSION,
    FEATURE_VERSION,
    FEATURES,
    digest,
    extract_features,
    propose,
)
from agent_braid.native_predictor_training import (
    FEATURES as LEARNED_FEATURES,
    digest as learned_digest,
    feature_vector as learned_feature_vector,
    fit as fit_learned,
    score as learned_score,
    serialize_artifact,
    score_request,
)
from agent_braid.native_predictor_evaluation import evaluate
from agent_braid.structured_exchange import VERSION, produce, verify


def synthetic_request() -> dict:
    return {
        "model": VERSION,
        "base": [{"id": "base", "value": "unused"}],
        "operations": [
            {"id": "first", "kind": "insert", "anchorId": "$root", "newId": "a", "value": "A"},
            {"id": "second", "kind": "insert", "anchorId": "base", "newId": "b", "value": "B"},
        ],
    }


def synthetic_artifact() -> dict:
    return {
        "version": ARTIFACT_VERSION,
        "featureVersion": FEATURE_VERSION,
        "modelId": "contract-double",
        "weights": {feature: 0 for feature in FEATURES},
        "bias": 1_000_000,
        "provenance": {"kind": "synthetic-hand-authored", "fixtureId": "contract-fixture"},
    }


class NativePredictorContractTests(unittest.TestCase):
    def test_synthetic_versioned_local_inference_and_tamper(self) -> None:
        def row(pair: str, family: str, session: str, partition: str,
                label: int | None, offset: float) -> dict:
            return {"pairId": pair, "familyId": family, "sessionId": session,
                    "partition": partition,
                    "features": {name: float(index + offset)
                                 for index, name in enumerate(LEARNED_FEATURES)},
                    "label": label}

        rows = [row("t0", "train", "ts0", "train", 0, 0),
                row("t1", "train", "ts1", "train", 1, 2),
                row("c0", "cal", "cs0", "calibration", 0, 3),
                row("c1", "cal", "cs1", "calibration", 1, 4),
                row("h0", "hold0", "hs0", "holdout", None, 5),
                row("h1", "hold1", "hs1", "holdout", None, 6),
                row("h2", "hold2", "hs2", "holdout", None, 7)]
        artifact = fit_learned(rows, model_id="contract-synthetic", dataset_kind="synthetic")
        commitment = learned_digest(artifact)
        serialized = serialize_artifact(artifact, expected_hash=commitment,
                                       expected_model_id="contract-synthetic")
        self.assertEqual(learned_digest(json.loads(serialized)), commitment)

        request = synthetic_request()
        prediction = score_request(
            request, artifact, source_kind="synthetic", expected_hash=commitment,
            expected_model_id="contract-synthetic", expected_input_hash=learned_digest(request))
        self.assertEqual(prediction["status"], "proposal")
        self.assertEqual(prediction["inputHash"], learned_digest(request))
        self.assertEqual(prediction["artifactHash"], commitment)
        self.assertIsNone(prediction["certificate"])
        self.assertFalse(prediction["executionAuthorization"])

        tampered = copy.deepcopy(artifact)
        tampered["bias"] += 1
        self.assertEqual(score_request(
            request, tampered, source_kind="synthetic", expected_hash=commitment,
            expected_model_id="contract-synthetic")["status"], "abstain")
        with self.assertRaisesRegex(ValueError, "commitment"):
            serialize_artifact(tampered, expected_hash=commitment,
                               expected_model_id="contract-synthetic")

    def test_synthetic_holdout_evaluation_records_no_gain_with_sanitized_scorer(self) -> None:
        inventory = []
        for index, (family, anchor1, anchor2) in enumerate(
                [("f1", "$root", "$root"), ("f1", "$root", "base"),
                 ("f2", "base", "base"), ("f2", "$root", "base")]):
            candidate = synthetic_request()
            candidate["operations"][0]["id"] = f"first-{index}"
            candidate["operations"][0]["newId"] = f"a-{index}"
            candidate["operations"][0]["anchorId"] = anchor1
            candidate["operations"][0]["value"] = f"proposal-A-{index}"
            candidate["operations"][1]["id"] = f"second-{index}"
            candidate["operations"][1]["newId"] = f"b-{index}"
            candidate["operations"][1]["anchorId"] = anchor2
            candidate["operations"][1]["value"] = f"proposal-B-{index}"
            inventory.append({"pairId": f"p{index}", "familyId": family,
                              "partition": "holdout", "request": candidate})

        seen_scorer_rows = []

        def baseline_equivalent_ranker(candidate, _prepared):
            seen_scorer_rows.append(candidate)
            operations = candidate["request"]["operations"]
            return int(operations[0]["anchorId"] == operations[1]["anchorId"])

        report = evaluate(inventory, {"p0": 1, "p1": 0, "p2": None, "p3": 1},
                          scorer=baseline_equivalent_ranker, dataset_kind="synthetic")
        self.assertEqual(report["status"], "synthetic-descriptive-only")
        self.assertEqual(report["protocolApproval"],
                         "not-approved; P019-04 call/status mapping remains provisional")
        self.assertTrue(seen_scorer_rows)
        self.assertTrue(all(set(row) == {"request"} for row in seen_scorer_rows))
        predictor = report["budgets"]["predictor"]["50"]
        baseline = report["budgets"]["baseline"]["50"]
        self.assertEqual(predictor["actualVerifierCalls"], 2)
        self.assertEqual(predictor["actualVerifierCalls"], baseline["actualVerifierCalls"])
        self.assertEqual(predictor["verifiedUsefulYieldBounds"],
                         baseline["verifiedUsefulYieldBounds"])
        self.assertEqual(report["policyDifferencesByFamilyAndBudget"]["50"]["f1"]
                         ["verifiedUsefulYieldLowerBoundDifferencePredictorMinusBaseline"], 0)
        self.assertFalse(report["permutedLabelNegativeControl"]["holdoutLabelsPermuted"])

    def test_verifier_remains_sole_certificate_source(self) -> None:
        request = synthetic_request()
        artifact = synthetic_artifact()
        artifact_hash = digest(artifact)
        vector = extract_features(request, source_kind="synthetic")

        # Even an extreme score cannot invoke deterministic evidence production or
        # verification as a side effect of prediction.
        with patch("agent_braid.structured_exchange.produce", side_effect=AssertionError("predictor invoked verifier producer")), \
             patch("agent_braid.structured_exchange.verify", side_effect=AssertionError("predictor invoked verifier")):
            prediction = propose(
                vector,
                artifact,
                expected_hash=artifact_hash,
                expected_input_hash=digest(request),
                expected_model_id="contract-double",
            )

        self.assertEqual(prediction["status"], "proposal")
        self.assertEqual(prediction["score"], 1_000_000)
        self.assertNotIn("verdict", prediction)
        self.assertIsNone(prediction["certificate"])
        self.assertFalse(prediction["executionAuthorization"])

        # Tampered verifier evidence cannot be rescued by the extreme score.
        tampered_evidence = produce(request)
        tampered_evidence["proposal"] = "verified-bounded"
        rejected = verify(tampered_evidence)
        self.assertEqual(rejected["status"], "inconclusive")
        self.assertFalse(rejected["executionAuthorization"])
        self.assertEqual(prediction["status"], "proposal")
        self.assertIsNone(prediction["certificate"])
        self.assertFalse(prediction["executionAuthorization"])

        # A bounded verdict is available only from the separately invoked
        # deterministic path; the predictor's score is not an input to it.
        evidence = produce(request)
        verdict = verify(evidence)
        self.assertEqual(verdict["status"], "verified-bounded")
        self.assertNotIn("certificate", verdict)
        self.assertFalse(verdict["executionAuthorization"])

    def test_learned_score_remains_outside_verifier_and_authorization_boundary(self) -> None:
        def training_row(pair: str, family: str, session: str, partition: str,
                         label: int | None, offset: float) -> dict:
            return {"pairId": pair, "familyId": family, "sessionId": session,
                    "partition": partition,
                    "features": {name: float(index + offset)
                                 for index, name in enumerate(LEARNED_FEATURES)},
                    "label": label}

        rows = [training_row("t0", "train-family", "train-session", "train", 0, 0),
                training_row("t1", "train-family", "train-session", "train", 1, 2),
                training_row("c0", "cal-family", "cal-session", "calibration", 0, 3),
                training_row("c1", "cal-family", "cal-session", "calibration", 1, 4),
                training_row("h0", "hold-family-0", "hold-session-0", "holdout", None, 5),
                training_row("h1", "hold-family-1", "hold-session-1", "holdout", None, 6),
                training_row("h2", "hold-family-2", "hold-session-2", "holdout", None, 7)]
        artifact = fit_learned(rows, model_id="learned-contract-double", dataset_kind="synthetic")
        artifact["weights"] = {name: 0.0 for name in LEARNED_FEATURES}
        artifact["bias"] = 1_000_000
        artifact_hash = learned_digest(artifact)
        vector = learned_feature_vector(rows[0]["features"])

        with patch("agent_braid.structured_exchange.produce",
                   side_effect=AssertionError("learned scorer invoked verifier producer")), \
             patch("agent_braid.structured_exchange.verify",
                   side_effect=AssertionError("learned scorer invoked verifier")):
            prediction = learned_score(
                vector, artifact, expected_hash=artifact_hash,
                expected_model_id="learned-contract-double")

        self.assertEqual(prediction["status"], "proposal")
        self.assertEqual(prediction["score"], 1_000_000)
        self.assertNotIn("verdict", prediction)
        self.assertIsNone(prediction["certificate"])
        self.assertFalse(prediction["executionAuthorization"])
