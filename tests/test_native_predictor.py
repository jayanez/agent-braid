# SPDX-License-Identifier: AGPL-3.0-only
"""Hand-authored synthetic predictor doubles; no fitting or benefit evidence."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from agent_braid.native_predictor import (ARTIFACT_VERSION, FEATURE_VERSION, FEATURES, MAX_CANDIDATES,
    digest, extract_features, propose, rank, serialize_artifact, validate_artifact)
from agent_braid.structured_exchange import VERSION


def request() -> dict:
    return {"model": VERSION, "base": [{"id": "base", "value": "unused"}],
            "operations": [{"id": "first", "kind": "insert", "anchorId": "$root", "newId": "a", "value": "A b"},
                           {"id": "second", "kind": "insert", "anchorId": "base", "newId": "b", "value": "b C"}]}


def artifact() -> dict:
    return {"version": ARTIFACT_VERSION, "featureVersion": FEATURE_VERSION,
            "modelId": "synthetic-double", "weights": {key: 0 for key in FEATURES},
            "bias": 2, "provenance": {"kind": "synthetic-hand-authored", "fixtureId": "fixture-1"}}


class NativePredictorTests(unittest.TestCase):
    def propose(self, vector=None, model=None, **kwargs):
        model = artifact() if model is None else model
        vector = extract_features(request(), source_kind="synthetic") if vector is None else vector
        return propose(vector, model, expected_hash=kwargs["expected_hash"] if "expected_hash" in kwargs else digest(model),
                       expected_input_hash=kwargs.get("expected_input_hash", digest(request())),
                       expected_model_id=kwargs.get("expected_model_id", "synthetic-double"))

    def test_feature_values_are_prediction_time_only(self):
        value = request()
        before = deepcopy(value)
        vector = extract_features(value, source_kind="synthetic")
        self.assertEqual(vector["features"], {"baseSize": 1, "sameAnchor": 0, "anchorDistance": 1,
                         "firstLength": 3, "secondLength": 3, "lexicalOverlap": 1 / 3})
        self.assertEqual(vector["inputHash"], digest(value))
        self.assertEqual(value, before)
        with self.assertRaisesRegex(ValueError, "synthetic"):
            extract_features(value, source_kind="prospective")
        value["operations"].append({"id": "third", "kind": "insert", "anchorId": "$root", "newId": "c", "value": ""})
        with self.assertRaisesRegex(ValueError, "exactly two"):
            extract_features(value, source_kind="synthetic")

    def test_serialization_is_deterministic_and_pinned(self):
        model = artifact()
        before = deepcopy(model)
        payload = serialize_artifact(model, expected_hash=digest(model))
        self.assertEqual(json.loads(payload), model)
        self.assertEqual(payload, serialize_artifact(dict(reversed(list(model.items()))), expected_hash=digest(model)))
        self.assertEqual(model, before)
        model["bias"] = 3
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            serialize_artifact(model, expected_hash=digest(before))

    def test_unknown_missing_and_unavailable_features_abstain(self):
        for mutate in (lambda value: value["features"].pop("sameAnchor"),
                       lambda value: value["features"].update(verifierOutcome=1),
                       lambda value: value["features"].update(firstLength=None),
                       lambda value: value["features"].update(lexicalOverlap=float("nan")),
                       lambda value: value["features"].update(baseSize=True),
                       lambda value: value.update(version="obsolete"),
                       lambda value: value.update(sourceKind="real")):
            vector = extract_features(request(), source_kind="synthetic")
            mutate(vector)
            result = self.propose(vector)
            self.assertEqual(result["status"], "abstain")
            self.assertIsNone(result["score"])
            self.assertIsNone(result["certificate"])
            self.assertFalse(result["executionAuthorization"])

    def test_artifact_versions_provenance_and_identity_abstain(self):
        for mutate in (lambda value: value.update(version="old"),
                       lambda value: value.update(featureVersion="old"),
                       lambda value: value.pop("provenance"),
                       lambda value: value["provenance"].update(kind="trained"),
                       lambda value: value.update(modelId="other"),
                       lambda value: value["weights"].update(baseSize=float("inf"))):
            model = artifact()
            mutate(model)
            # A separate valid pin cannot rescue unsupported provenance/versions.
            pin = digest(model) if model.get("weights", {}).get("baseSize") != float("inf") else "a" * 64
            self.assertEqual(self.propose(model=model, expected_hash=pin)["status"], "abstain")
        self.assertEqual(self.propose(expected_input_hash="a" * 64)["status"], "abstain")
        self.assertEqual(self.propose(expected_hash="a" * 64)["status"], "abstain")
        with self.assertRaises(ValueError):
            validate_artifact(artifact(), expected_hash=None)

    def test_high_score_never_calls_verifier_or_grants_certificate(self):
        model = artifact()
        model["bias"] = 1000000
        with patch("agent_braid.structured_exchange.produce", side_effect=AssertionError("must stay independent")):
            result = self.propose(model=model)
        self.assertEqual(result["score"], 1000000)
        self.assertEqual(result["status"], "proposal")
        self.assertEqual(result["modelId"], "synthetic-double")
        self.assertEqual(result["artifactHash"], digest(model))
        self.assertIsNone(result["certificate"])
        self.assertFalse(result["executionAuthorization"])

    def test_ranking_descending_ties_and_abstentions_preserve_inventory(self):
        model = artifact()
        model["weights"]["firstLength"] = 1
        vector = extract_features(request(), source_kind="synthetic")
        longer_request = request()
        longer_request["operations"][0]["value"] = "longer"
        longer = extract_features(longer_request, source_kind="synthetic")
        invalid = deepcopy(vector)
        invalid["features"]["firstLength"] = None
        candidates = [{"pairId": key, "inputHash": vec["inputHash"], "vector": vec}
                      for key, vec in (("z-first", vector), ("invalid", invalid),
                                       ("a-tied", vector), ("longer", longer))]
        before = deepcopy(candidates)
        results = rank(candidates, model, expected_hash=digest(model), expected_model_id="synthetic-double")
        self.assertEqual([value["pairId"] for value in results], ["longer", "z-first", "a-tied", "invalid"])
        self.assertEqual([value["score"] for value in results], [8, 5, 5, None])
        self.assertEqual(candidates, before)
        candidates.append(candidates[0])
        with self.assertRaisesRegex(ValueError, "duplicate pair"):
            rank(candidates, model, expected_hash=digest(model), expected_model_id="synthetic-double")

    def test_empty_root_tokens_and_same_anchor_features(self):
        value = request()
        value["base"] = []
        for operation in value["operations"]:
            operation.update(anchorId="$root", value="")
        self.assertEqual(extract_features(value, source_kind="synthetic")["features"],
                         {"baseSize": 0, "sameAnchor": 1, "anchorDistance": 0,
                          "firstLength": 0, "secondLength": 0, "lexicalOverlap": 0.0})

    def test_score_overflow_and_boolean_weight_abstain(self):
        model = artifact()
        model["weights"]["firstLength"] = 1e308
        result = self.propose(model=model)
        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["score"])
        model["weights"]["firstLength"] = True
        self.assertEqual(self.propose(model=model)["status"], "abstain")


    def test_huge_integer_weight_and_inventory_limit_fail_closed(self):
        model = artifact()
        model["bias"] = 10 ** 400
        with self.assertRaisesRegex(ValueError, "finite"):
            validate_artifact(model, expected_hash="a" * 64)
        self.assertEqual(self.propose(model=model)["status"], "abstain")
        with self.assertRaises(ValueError):
            rank([{}] * (MAX_CANDIDATES + 1), artifact(), expected_hash=digest(artifact()),
                 expected_model_id="synthetic-double")
