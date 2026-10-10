# SPDX-License-Identifier: AGPL-3.0-only
"""Offline, in-memory linear logistic training for SPEC-019.

This module accepts already-extracted numeric features only. It never opens a
source, captures data, contacts a network, or reads a dataset. The fit caller
must declare its rows synthetic, but this module cannot authenticate that
claim; artifacts record provenance as caller-declared and unverified. No
real-data admission receipt exists. Weights use training rows alone and the frozen
sigmoid calibration grid uses calibration rows only. Holdout labels are
prohibited at the API boundary.

The fixed optimizer settings are an implementation candidate pending protocol
review: full-batch gradient descent, 2,000 steps, learning rate 0.1, and L2
weight penalty 0.01. They do not authorize or imply a real-data fit.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Any

from agent_braid.native_predictor import FEATURES, extract_features

FEATURE_VERSION = "m35-learned-features-v1"
ARTIFACT_VERSION = "m35-learned-logistic-v1"
ITERATIONS = 2000
LEARNING_RATE = 0.1
L2 = 0.01
CALIBRATION_GRID_VERSION = "m35-fixed-sigmoid-grid-v1"
CALIBRATION_STEP = 0.02
PARTITIONS = frozenset({"train", "calibration", "holdout"})
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ROW_FIELDS = {"pairId", "familyId", "sessionId", "duplicateGroupId",
               "partition", "features", "label"}


def _keys(value: Any, expected: set[str]) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError("missing or unknown fields")


def _id(value: Any, name: str) -> str:
    if type(value) is not str or _ID.fullmatch(value) is None:
        raise ValueError(f"invalid {name}")
    return value


def _number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def _validate_rows(rows: Any) -> list[dict]:
    if type(rows) is not list or not rows:
        raise ValueError("rows must be a nonempty list")
    checked: list[dict] = []
    pairs: set[str] = set()
    family_partitions: dict[str, str] = {}
    session_partitions: dict[str, str] = {}
    duplicate_group_partitions: dict[str, str] = {}
    classes = {partition: set() for partition in PARTITIONS}
    for row in rows:
        _keys(row, _ROW_FIELDS)
        pair = _id(row["pairId"], "pair identity")
        family = _id(row["familyId"], "family identity")
        session = _id(row["sessionId"], "session identity")
        duplicate_group = _id(row["duplicateGroupId"], "duplicate-group identity")
        if pair in pairs:
            raise ValueError("duplicate pair identity")
        pairs.add(pair)
        partition = row["partition"]
        if type(partition) is not str or partition not in PARTITIONS:
            raise ValueError("invalid partition")
        for identity, mapping, label in ((family, family_partitions, "family"),
                                         (session, session_partitions, "session"),
                                         (duplicate_group, duplicate_group_partitions,
                                          "duplicate group")):
            previous = mapping.setdefault(identity, partition)
            if previous != partition:
                raise ValueError(f"{label} crosses partitions")
        _keys(row["features"], set(FEATURES))
        features = dict(row["features"])
        if any(not _number(features[key]) for key in FEATURES):
            raise ValueError("features must be finite numbers")
        label = row["label"]
        if partition == "holdout" and label is not None:
            raise ValueError("holdout labels must remain sealed")
        if label is not None:
            if type(label) is not int or label not in (0, 1):
                raise ValueError("label must be 0, 1, or None")
            classes[partition].add(label)
        checked.append({"pairId": pair, "familyId": family, "sessionId": session,
                        "duplicateGroupId": duplicate_group,
                        "partition": partition, "features": features, "label": label})
    for partition in ("train", "calibration"):
        if classes[partition] != {0, 1}:
            raise ValueError(f"{partition} partition requires both known classes")
    if "train" not in {row["partition"] for row in checked}:
        raise ValueError("training partition is required")
    if "calibration" not in {row["partition"] for row in checked}:
        raise ValueError("calibration partition is required")
    calibration_families = {row["familyId"] for row in checked
                            if row["partition"] == "calibration"}
    if len(calibration_families) != 1:
        raise ValueError("candidate calibration requires exactly one family")
    return checked


def _descriptive_coverage(rows: list[dict]) -> dict:
    """Report counts from caller-declared rows without authenticating origin."""
    family_counts = {partition: len({row["familyId"] for row in rows
                                     if row["partition"] == partition})
                     for partition in PARTITIONS}
    known = [row for row in rows if row["label"] is not None]
    return {"kind": "caller-declared-descriptive-only", "familyCounts": family_counts,
            "knownTotal": len(known), "holdoutPositive": 0, "holdoutNegative": 0,
            "satisfiesRealReadiness": False}


def feature_vector(features: Any, *, input_hash: str | None = None) -> dict:
    """Wrap numeric features, optionally binding them to their source request.

    The unbound form is retained for hand-authored synthetic training fixtures.
    Request-bound scoring must use ``score_request``, which derives features
    internally instead of trusting a caller-supplied vector/hash pairing.
    """
    _keys(features, set(FEATURES))
    values = dict(features)
    if any(not _number(values[name]) for name in FEATURES):
        raise ValueError("features must be finite numbers")
    if input_hash is None:
        return {"version": FEATURE_VERSION, "features": values}
    if type(input_hash) is not str or _HASH.fullmatch(input_hash) is None:
        raise ValueError("input hash must be a lowercase SHA-256 digest")
    return {"version": FEATURE_VERSION, "sourceKind": "synthetic",
            "inputHash": input_hash, "features": values}


def prepare_request(request: Any, *, source_kind: str) -> dict:
    """Extract the versioned learned feature vector from a synthetic request.

    This is the request-to-feature preparation phase. The legacy synthetic
    feature/artifact interface remains separate; prospective inputs are
    rejected until the source, orientation and protocol gates are implemented.
    """
    extracted = extract_features(request, source_kind=source_kind)
    return feature_vector(extracted["features"], input_hash=extracted["inputHash"])


def fit(rows: Any, *, model_id: str, dataset_kind: str,
        coverage_receipt: Any = None) -> dict:
    """Fit train weights and calibration-only sigmoid parameters.

    The caller must designate the input as synthetic. This function cannot
    authenticate that designation, and its artifact records provenance as
    caller-declared and unverified. Caller receipts cannot authorize or
    establish real-data readiness.
    Holdout rows may be present only with label=None. No calibration or
    holdout feature or label is used for training weights. Calibration inputs
    affect only the protocol's fixed-grid calibration. Caller-supplied
    coverage receipts are rejected; descriptive counts come from the visible
    caller-declared rows and never satisfy real-data readiness.
    """
    model_id = _id(model_id, "model identity")
    if dataset_kind != "synthetic":
        raise ValueError("caller must declare a synthetic dataset")
    if coverage_receipt is not None:
        raise ValueError("caller-supplied coverage receipts cannot authorize fitting")
    data = _validate_rows(rows)
    receipt = _descriptive_coverage(data)
    training = [row for row in data if row["partition"] == "train" and row["label"] is not None]
    calibration_rows = [row for row in data if row["partition"] == "calibration" and row["label"] is not None]
    if not training:
        raise ValueError("known training labels are required")
    # Stable ordering makes floating point accumulation independent of input order.
    training.sort(key=lambda row: row["pairId"])
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    try:
        for name in FEATURES:
            values = [float(row["features"][name]) for row in training]
            mean = math.fsum(values) / len(values)
            variance = math.fsum((value - mean) ** 2 for value in values) / len(values)
            scale = math.sqrt(variance)
            if not math.isfinite(mean) or not math.isfinite(scale):
                raise ValueError("nonfinite training normalization")
            means[name] = mean
            scales[name] = scale
    except (OverflowError, ValueError) as exc:
        raise ValueError("training normalization overflow or nonfinite result") from exc

    normalized: list[list[float]] = []
    labels: list[float] = []
    for row in training:
        vector = []
        for name in FEATURES:
            value = float(row["features"][name])
            scale = scales[name]
            z = 0.0 if scale == 0.0 else (value - means[name]) / scale
            if not math.isfinite(z):
                raise ValueError("nonfinite normalized training feature")
            vector.append(z)
        normalized.append(vector)
        labels.append(float(row["label"]))

    weights = [0.0] * len(FEATURES)
    bias = 0.0
    for _ in range(ITERATIONS):
        grad_w = [0.0] * len(FEATURES)
        grad_b = 0.0
        for vector, label in zip(normalized, labels):
            linear = bias + math.fsum(w * x for w, x in zip(weights, vector))
            if not math.isfinite(linear):
                raise ValueError("nonfinite training linear score")
            probability = _sigmoid(linear)
            error = probability - label
            grad_b += error / len(labels)
            for index, value in enumerate(vector):
                grad_w[index] += error * value / len(labels)
        for index in range(len(weights)):
            grad_w[index] += L2 * weights[index]
            weights[index] -= LEARNING_RATE * grad_w[index]
        bias -= LEARNING_RATE * grad_b
        if not math.isfinite(bias) or any(not math.isfinite(w) for w in weights):
            raise ValueError("nonfinite learned parameter")

    try:
        calibration_scores = [_raw_score(row["features"], means, scales, weights, bias)
                              for row in calibration_rows]
        calibration = _fit_calibration(calibration_scores, [row["label"] for row in calibration_rows])
    except (OverflowError, ValueError, ZeroDivisionError):
        calibration = {"gridVersion": CALIBRATION_GRID_VERSION, "scoreMean": 0.0,
                       "scorePopulationStd": 0.0, "intercept": None, "slope": None,
                       "status": "unavailable", "reason": "calibration-fit-failed"}
    train_inputs = sorted((row for row in data if row["partition"] == "train"),
                          key=lambda row: row["pairId"])
    calibration_inputs = sorted((row for row in data if row["partition"] == "calibration"),
                                key=lambda row: row["pairId"])

    artifact = {
        "version": ARTIFACT_VERSION,
        "featureVersion": FEATURE_VERSION,
        "datasetKind": "caller-declared-synthetic",
        "provenance": {"kind": "caller-declared-unverified", "realDataEligible": False},
        "modelId": model_id,
        "normalization": {"means": means, "scales": scales, "scaleConvention": "population",
                          "constantFeatureValue": 0.0},
        "weights": dict(zip(FEATURES, weights)),
        "bias": bias,
        "optimizer": {"kind": "full-batch-logistic-gradient-descent", "iterations": ITERATIONS,
                      "learningRate": LEARNING_RATE, "l2": L2, "initialization": "zeros",
                      "regularizedParameters": "weights-only"},
        "inputCommitments": {"kind": "sha256-canonical-json-v1",
                             "train": digest(train_inputs),
                             "calibration": digest(calibration_inputs)},
        "calibrationFamilyWeighting": "single-family-rows-provisional",
        "calibration": calibration,
        "coverageReceipt": receipt,
    }
    # Ensure the result itself is canonicalizable and finite before returning.
    canonical(artifact)
    return artifact


def validate_artifact(artifact: Any, *, expected_hash: str, expected_model_id: str) -> dict:
    _keys(artifact, {"version", "featureVersion", "datasetKind", "provenance", "modelId", "normalization", "weights", "bias",
                     "optimizer", "inputCommitments", "calibrationFamilyWeighting",
                     "calibration", "coverageReceipt"})
    if artifact["version"] != ARTIFACT_VERSION or artifact["featureVersion"] != FEATURE_VERSION:
        raise ValueError("unsupported learned artifact or feature version")
    if artifact["datasetKind"] != "caller-declared-synthetic":
        raise ValueError("only caller-declared synthetic artifacts are supported")
    if artifact["provenance"] != {"kind": "caller-declared-unverified", "realDataEligible": False}:
        raise ValueError("invalid caller-declared provenance")
    if artifact["modelId"] != _id(expected_model_id, "model identity"):
        raise ValueError("model identity mismatch")
    if type(expected_hash) is not str or _HASH.fullmatch(expected_hash) is None or digest(artifact) != expected_hash:
        raise ValueError("artifact commitment mismatch")
    _keys(artifact["normalization"], {"means", "scales", "scaleConvention", "constantFeatureValue"})
    _keys(artifact["normalization"]["means"], set(FEATURES))
    _keys(artifact["normalization"]["scales"], set(FEATURES))
    if artifact["normalization"]["scaleConvention"] != "population" or artifact["normalization"]["constantFeatureValue"] != 0.0:
        raise ValueError("unsupported normalization convention")
    if any(not _number(v) for v in artifact["normalization"]["means"].values()):
        raise ValueError("nonfinite normalization mean")
    if any(not _number(v) or v < 0 for v in artifact["normalization"]["scales"].values()):
        raise ValueError("invalid normalization scale")
    _keys(artifact["weights"], set(FEATURES))
    if not _number(artifact["bias"]) or any(not _number(v) for v in artifact["weights"].values()):
        raise ValueError("nonfinite model parameter")
    expected_optimizer = {"kind": "full-batch-logistic-gradient-descent", "iterations": ITERATIONS,
                          "learningRate": LEARNING_RATE, "l2": L2, "initialization": "zeros",
                          "regularizedParameters": "weights-only"}
    if artifact["optimizer"] != expected_optimizer:
        raise ValueError("unsupported optimizer settings")
    _keys(artifact["inputCommitments"], {"kind", "train", "calibration"})
    commitments = artifact["inputCommitments"]
    if (commitments["kind"] != "sha256-canonical-json-v1"
            or any(type(commitments[name]) is not str or _HASH.fullmatch(commitments[name]) is None
                   for name in ("train", "calibration"))):
        raise ValueError("invalid sorted-input commitments")
    _validate_calibration_artifact(artifact["calibration"])
    if artifact["calibrationFamilyWeighting"] != "single-family-rows-provisional":
        raise ValueError("unsupported provisional calibration-family weighting")
    receipt = artifact["coverageReceipt"]
    _keys(receipt, {"kind", "familyCounts", "knownTotal", "holdoutPositive", "holdoutNegative",
                    "satisfiesRealReadiness"})
    if receipt["kind"] != "caller-declared-descriptive-only" or receipt["satisfiesRealReadiness"] is not False:
        raise ValueError("invalid caller-declared descriptive coverage record")
    _keys(receipt["familyCounts"], {"train", "calibration", "holdout"})
    if any(type(value) is not int or value < 0 for value in receipt["familyCounts"].values()):
        raise ValueError("invalid coverage receipt family counts")
    if (type(receipt["knownTotal"]) is not int or receipt["knownTotal"] < 0
            or receipt["holdoutPositive"] != 0 or receipt["holdoutNegative"] != 0):
        raise ValueError("invalid caller-declared descriptive coverage counts")
    return artifact


def serialize_artifact(artifact: Any, *, expected_hash: str, expected_model_id: str) -> bytes:
    validate_artifact(artifact, expected_hash=expected_hash, expected_model_id=expected_model_id)
    return canonical(artifact) + b"\n"


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)


def _raw_score(features: dict, means: dict, scales: dict, weights: list[float], bias: float) -> float:
    terms = []
    for index, name in enumerate(FEATURES):
        scale = scales[name]
        z = 0.0 if scale == 0.0 else (float(features[name]) - means[name]) / scale
        if not math.isfinite(z):
            raise ValueError("nonfinite normalized score feature")
        terms.append(weights[index] * z)
    value = bias + math.fsum(terms)
    if not math.isfinite(value):
        raise ValueError("nonfinite raw score")
    return value


def _logistic_loss(linear: float, label: int) -> float:
    # Stable log(1 + exp(x)) - y*x.
    if linear > 0:
        return linear * (1 - label) + math.log1p(math.exp(-linear))
    return -linear * label + math.log1p(math.exp(linear))


def _fit_calibration(scores: list[float], labels: list[int]) -> dict:
    try:
        mean = math.fsum(scores) / len(scores)
        variance = math.fsum((value - mean) ** 2 for value in scores) / len(scores)
        std = math.sqrt(variance)
    except (OverflowError, ValueError, ZeroDivisionError):
        mean, std = 0.0, 0.0
        return {"gridVersion": CALIBRATION_GRID_VERSION, "scoreMean": mean,
                "scorePopulationStd": std, "intercept": None, "slope": None,
                "status": "unavailable", "reason": "calibration-fit-failed"}
    base = {"gridVersion": CALIBRATION_GRID_VERSION, "scoreMean": mean,
            "scorePopulationStd": std, "intercept": None, "slope": None}
    if not math.isfinite(std) or std == 0.0:
        return {**base, "status": "unavailable", "reason": "zero-score-variance"}
    if set(labels) != {0, 1}:
        return {**base, "status": "unavailable", "reason": "missing-calibration-class"}
    standardized = [(value - mean) / std for value in scores]
    if any(not math.isfinite(value) for value in standardized):
        return {**base, "status": "unavailable", "reason": "nonfinite-calibration-score"}
    # Inclusive grids: a=-8..8 and b=0..8, each in 0.02 increments.
    best: tuple[float, float, float] | None = None
    best_a = best_b = 0.0
    for b_index in range(401):
        b = b_index * CALIBRATION_STEP
        penalty = 0.01 * b * b
        for a_index in range(801):
            a = -8.0 + a_index * CALIBRATION_STEP
            objective = math.fsum(_logistic_loss(a + b * z, label)
                                  for z, label in zip(standardized, labels)) / len(labels) + penalty
            candidate = (objective, b, a)
            if best is None or candidate < best:
                best = candidate
                best_a, best_b = a, b
    if best is None or not math.isfinite(best[0]):
        return {**base, "status": "unavailable", "reason": "calibration-fit-failed"}
    return {**base, "status": "calibrated", "reason": None,
            "intercept": best_a, "slope": best_b,
            "objective": best[0],
            "grid": {"interceptMin": -8.0, "interceptMax": 8.0,
                     "slopeMin": 0.0, "slopeMax": 8.0, "step": CALIBRATION_STEP,
                     "tieBreak": ["smaller-slope", "smaller-intercept"],
                     "loss": "mean-logistic-loss-plus-0.01-slope-squared"}}


def _validate_calibration_artifact(calibration: Any) -> None:
    if type(calibration) is not dict or calibration.get("gridVersion") != CALIBRATION_GRID_VERSION:
        raise ValueError("unsupported calibration version")
    common = {"gridVersion", "scoreMean", "scorePopulationStd", "intercept", "slope", "status", "reason"}
    if calibration.get("status") == "calibrated":
        _keys(calibration, common | {"objective", "grid"})
        if (not _number(calibration["scoreMean"]) or not _number(calibration["scorePopulationStd"])
                or calibration["scorePopulationStd"] <= 0
                or not _number(calibration["intercept"]) or not -8 <= calibration["intercept"] <= 8
                or not _number(calibration["slope"]) or not 0 <= calibration["slope"] <= 8
                or not _number(calibration["objective"])
                or not _on_grid(calibration["intercept"], -8.0, 801)
                or not _on_grid(calibration["slope"], 0.0, 401)):
            raise ValueError("invalid calibrated parameters")
        _keys(calibration["grid"], {"interceptMin", "interceptMax", "slopeMin", "slopeMax", "step", "tieBreak", "loss"})
        if calibration["grid"] != {"interceptMin": -8.0, "interceptMax": 8.0,
                                    "slopeMin": 0.0, "slopeMax": 8.0, "step": CALIBRATION_STEP,
                                    "tieBreak": ["smaller-slope", "smaller-intercept"],
                                    "loss": "mean-logistic-loss-plus-0.01-slope-squared"}:
            raise ValueError("unsupported calibration grid")
    elif calibration.get("status") == "unavailable":
        _keys(calibration, common)
        if (calibration["reason"] not in {"zero-score-variance", "missing-calibration-class",
                                          "nonfinite-calibration-score", "calibration-fit-failed"}
                or not _number(calibration["scoreMean"]) or not _number(calibration["scorePopulationStd"])
                or calibration["intercept"] is not None or calibration["slope"] is not None):
            raise ValueError("invalid unavailable calibration record")
    else:
        raise ValueError("invalid calibration status")


def _on_grid(value: float, minimum: float, count: int) -> bool:
    """Match a value produced by the exact inclusive calibration grid."""
    index = round((value - minimum) / CALIBRATION_STEP)
    return 0 <= index < count and value == minimum + index * CALIBRATION_STEP


def score(vector: Any, artifact: Any, *, expected_hash: str, expected_model_id: str,
          expected_input_hash: str | None = None) -> dict:
    """Score a hand-authored synthetic feature fixture.

    Request-bound vectors are intentionally rejected: a caller-provided hash
    cannot prove that the accompanying feature values came from that request.
    Use ``score_request`` at the inference boundary instead.
    """
    result = {"status": "abstain", "score": None, "certificate": None,
              "executionAuthorization": False, "modelId": expected_model_id,
              "artifactHash": expected_hash, "featureVersion": FEATURE_VERSION,
              "brierEligible": False}
    try:
        validate_artifact(artifact, expected_hash=expected_hash, expected_model_id=expected_model_id)
        vector_keys = set(vector) if type(vector) is dict else set()
        unbound_keys = {"version", "features"}
        if vector_keys != unbound_keys:
            raise ValueError("feature vector has missing or unknown identity fields")
        if vector["version"] != FEATURE_VERSION:
            raise ValueError("unsupported feature version")
        if expected_input_hash is not None:
            raise ValueError("request-bound scoring requires score_request")
        _keys(vector["features"], set(FEATURES))
        values = vector["features"]
        if any(not _number(values[name]) for name in FEATURES):
            raise ValueError("features must be finite numbers")
        norm = artifact["normalization"]
        raw = _raw_score(values, norm["means"], norm["scales"],
                         [artifact["weights"][name] for name in FEATURES], artifact["bias"])
        result.update(status="proposal", score=raw, reason=None)
        calibration = artifact["calibration"]
        if calibration["status"] == "calibrated":
            z = (raw - calibration["scoreMean"]) / calibration["scorePopulationStd"]
            probability = _sigmoid(calibration["intercept"] + calibration["slope"] * z)
            if not math.isfinite(probability):
                raise ValueError("nonfinite calibrated probability")
            result["probability"] = probability
            result["brierEligible"] = True
    except (ValueError, TypeError, OverflowError, KeyError) as exc:
        result["reason"] = str(exc)
    return result


def score_request(request: Any, artifact: Any, *, source_kind: str,
                  expected_hash: str, expected_model_id: str,
                  expected_input_hash: str | None = None) -> dict:
    """Derive features from the request inside the scoring trust boundary."""
    try:
        vector = prepare_request(request, source_kind=source_kind)
        actual_input_hash = vector["inputHash"]
        if expected_input_hash is not None and actual_input_hash != expected_input_hash:
            raise ValueError("request commitment does not match expected input hash")
        result = score(feature_vector(vector["features"]), artifact,
                       expected_hash=expected_hash, expected_model_id=expected_model_id)
        if result["status"] == "proposal":
            result["inputHash"] = actual_input_hash
        return result
    except (ValueError, TypeError, OverflowError, KeyError) as exc:
        return {"status": "abstain", "score": None, "certificate": None,
                "executionAuthorization": False, "modelId": expected_model_id,
                "artifactHash": expected_hash, "featureVersion": FEATURE_VERSION,
                "brierEligible": False, "reason": str(exc)}
