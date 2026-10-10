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
    def test_versioned_local_inference_and_tamper(self) -> None:
        def row(pair: str, family: str, session: str, partition: str,
                label: int | None, offset: float) -> dict:
            return {"pairId": pair, "familyId": family, "sessionId": session,
                    "duplicateGroupId": f"duplicate-{pair}",
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

    def test_held_out_evaluation_and_negative_outcome(self) -> None:
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
            label = {0: 1, 1: 0, 2: None, 3: 1}[index]
            inventory.append({"pairId": f"p{index}", "familyId": family,
                              "sessionId": f"session-p{index}",
                              "duplicateGroupId": f"duplicate-p{index}",
                              "partition": "holdout", "request": candidate,
                              "annotation1": label, "annotation2": label,
                              "adjudicatedLabel": None,
                              "annotation1Attempted": True,
                              "annotation1ReviewerId": "synthetic-reviewer-a",
                              "annotation1UnknownReason": None if label is not None else "insufficient-context",
                              "annotation2Attempted": True,
                              "annotation2ReviewerId": "synthetic-reviewer-b",
                              "annotation2UnknownReason": None if label is not None else "insufficient-context",
                              "adjudicationAttempted": False, "adjudicatorId": None,
                              "adjudicationRationale": None, "adjudicationUnknownReason": None})

        seen_scorer_rows = []

        def baseline_equivalent_ranker(vector):
            seen_scorer_rows.append(vector)
            return vector["features"]["sameAnchor"]

        report = evaluate(inventory, {"p0": 1, "p1": 0, "p2": None, "p3": 1},
                          scorer=baseline_equivalent_ranker, dataset_kind="synthetic")
        self.assertEqual(report["status"], "synthetic-descriptive-only")
        self.assertEqual(report["protocolApproval"],
                         "not-approved; founder-selected call unit and status mapping recorded; remaining protocol review is pending")
        self.assertTrue(seen_scorer_rows)
        self.assertTrue(all(set(row) == {"version", "features"} for row in seen_scorer_rows))
        self.assertTrue(all(set(row["features"]) == set(LEARNED_FEATURES)
                            for row in seen_scorer_rows))
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
        requests = [synthetic_request(), synthetic_request()]
        requests[1]["operations"][1]["anchorId"] = "$root"
        artifacts = []
        for bias in (-1_000_000, 1_000_000):
            artifact = synthetic_artifact()
            artifact["bias"] = bias
            artifacts.append((artifact, digest(artifact)))

        # Even an extreme score cannot invoke deterministic evidence production or
        # verification as a side effect of prediction.
        with patch("agent_braid.structured_exchange.produce", side_effect=AssertionError("predictor invoked verifier producer")), \
             patch("agent_braid.structured_exchange.verify", side_effect=AssertionError("predictor invoked verifier")):
            predictions = [[propose(
                extract_features(request, source_kind="synthetic"), artifact,
                expected_hash=commitment, expected_input_hash=digest(request),
                expected_model_id="contract-double")
                for artifact, commitment in artifacts] for request in requests]

        self.assertEqual([row["score"] for row in predictions[0]], [-1_000_000, 1_000_000])
        self.assertEqual([row["score"] for row in predictions[1]], [-1_000_000, 1_000_000])
        self.assertTrue(all(row["status"] == "proposal" for pair in predictions for row in pair))
        self.assertTrue(all("verdict" not in row and row["certificate"] is None
                            and row["executionAuthorization"] is False
                            for pair in predictions for row in pair))

        # Distinct deterministic proposal states remain functions of request
        # content alone, regardless of either extreme predictor score.
        outputs = []
        for request, pair_predictions in zip(requests, predictions):
            evidence = produce(request)
            verdict = verify(evidence)
            outputs.append((evidence["proposal"], verdict["status"], verdict["proposal"],
                            verdict["executionAuthorization"]))
            for prediction in pair_predictions:
                self.assertEqual(prediction["status"], "proposal")
                self.assertIsNone(prediction["certificate"])
                self.assertFalse(prediction["executionAuthorization"])
        self.assertEqual(outputs[0][:3], ("keep-order", "verified-bounded", "keep-order"))
        self.assertEqual(outputs[1][:3], ("propose-swap", "verified-bounded", "propose-swap"))
        self.assertTrue(all(output[3] is False for output in outputs))

        # The high-score prediction remains advisory when an independent
        # verifier receives tampered evidence; no combined result is exposed.
        tampered_evidence = produce(requests[0])
        tampered_evidence["proposal"] = "verified-bounded"
        rejected = verify(tampered_evidence)
        self.assertEqual(rejected["status"], "inconclusive")
        self.assertFalse(rejected["executionAuthorization"])
        self.assertEqual(predictions[0][1]["score"], 1_000_000)
        self.assertEqual(predictions[0][1]["status"], "proposal")
        self.assertIsNone(predictions[0][1]["certificate"])

    def test_learned_score_remains_outside_verifier_and_authorization_boundary(self) -> None:
        def training_row(pair: str, family: str, session: str, partition: str,
                         label: int | None, offset: float) -> dict:
            return {"pairId": pair, "familyId": family, "sessionId": session,
                    "duplicateGroupId": f"duplicate-{pair}",
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
