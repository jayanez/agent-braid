# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-019 contract anchors; real-model and eligible-holdout gates remain deferred."""

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
)
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
    @unittest.skip("requires a real trained M3.5 artifact and a validated versioned inference interface")
    def test_versioned_local_inference_and_tamper(self) -> None:
        self.fail("deferred")

    @unittest.skip("requires eligible, human-reviewed holdout pairs and a frozen evaluation inventory")
    def test_held_out_evaluation_and_negative_outcome(self) -> None:
        self.fail("deferred")

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
