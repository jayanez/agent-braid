# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic-only SPEC-019 proposal interfaces; no fitting or calibration.

Hand-authored test doubles exercise boundaries. Scores are heuristic, never
probabilities, certificates, verifier verdicts or execution authorization.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Any

from agent_braid.structured_exchange import ROOT, validate_request

FEATURE_VERSION = "m35-synthetic-features-v1"
ARTIFACT_VERSION = "m35-synthetic-ranker-v1"
MAX_CANDIDATES = 4096
FEATURES = ("baseSize", "sameAnchor", "anchorDistance", "firstLength", "secondLength", "lexicalOverlap")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")


def canonical(value: Any) -> bytes:
    """Serialize finite JSON deterministically without modifying its input."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical(value)).hexdigest()


def _keys(value: Any, expected: set[str]) -> None:
    if type(value) is not dict or set(value) != expected:
        raise ValueError("missing or unknown fields")


def _number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def extract_features(request: Any, *, source_kind: str) -> dict:
    """Extract prediction-time features from an explicitly synthetic M3 pair."""
    if source_kind != "synthetic":
        raise ValueError("only explicitly synthetic inputs are supported")
    validate_request(request)
    if len(request["operations"]) != 2:
        raise ValueError("predictor features require exactly two inserts")
    first, second = request["operations"]
    indices = {ROOT: -1} | {item["id"]: i for i, item in enumerate(request["base"])}
    left, right = set(first["value"].casefold().split()), set(second["value"].casefold().split())
    union = left | right
    return {"version": FEATURE_VERSION, "sourceKind": "synthetic", "inputHash": digest(request),
            "features": {"baseSize": len(request["base"]),
                         "sameAnchor": int(first["anchorId"] == second["anchorId"]),
                         "anchorDistance": abs(indices[first["anchorId"]] - indices[second["anchorId"]]),
                         "firstLength": len(first["value"]), "secondLength": len(second["value"]),
                         "lexicalOverlap": len(left & right) / len(union) if union else 0.0}}


def validate_artifact(artifact: Any, *, expected_hash: str) -> dict:
    """Validate a hand-authored artifact against a separately supplied commitment.

    Hashes detect drift relative to the caller's pin; they are not signatures.
    No file or source is opened and no trained artifact is accepted.
    """
    _keys(artifact, {"version", "featureVersion", "modelId", "weights", "bias", "provenance"})
    if artifact["version"] != ARTIFACT_VERSION or artifact["featureVersion"] != FEATURE_VERSION:
        raise ValueError("unsupported artifact or feature version")
    if type(artifact["modelId"]) is not str or ID.fullmatch(artifact["modelId"]) is None:
        raise ValueError("invalid model identity")
    _keys(artifact["weights"], set(FEATURES))
    if not _number(artifact["bias"]) or any(not _number(value) for value in artifact["weights"].values()):
        raise ValueError("weights and bias must be finite numbers")
    _keys(artifact["provenance"], {"kind", "fixtureId"})
    if (artifact["provenance"]["kind"] != "synthetic-hand-authored"
            or type(artifact["provenance"]["fixtureId"]) is not str
            or ID.fullmatch(artifact["provenance"]["fixtureId"]) is None):
        raise ValueError("synthetic hand-authored provenance required")
    if type(expected_hash) is not str or HASH.fullmatch(expected_hash) is None or digest(artifact) != expected_hash:
        raise ValueError("artifact hash mismatch")
    return artifact


def serialize_artifact(artifact: Any, *, expected_hash: str) -> bytes:
    """Serialize a validated test double; does not fit or write weights."""
    validate_artifact(artifact, expected_hash=expected_hash)
    return canonical(artifact) + b"\n"


def propose(vector: Any, artifact: Any, *, expected_hash: str, expected_input_hash: str,
            expected_model_id: str) -> dict:
    """Return a synthetic heuristic score or explicit fail-closed abstention."""
    result = {"status": "abstain", "score": None, "certificate": None,
              "executionAuthorization": False, "sourceKind": "synthetic",
              "modelId": expected_model_id, "artifactHash": expected_hash,
              "featureVersion": FEATURE_VERSION}
    try:
        validate_artifact(artifact, expected_hash=expected_hash)
        if artifact["modelId"] != expected_model_id:
            raise ValueError("model identity mismatch")
        _keys(vector, {"version", "sourceKind", "inputHash", "features"})
        if vector["version"] != FEATURE_VERSION or vector["sourceKind"] != "synthetic":
            raise ValueError("unsupported vector version or source")
        if (type(expected_input_hash) is not str or HASH.fullmatch(expected_input_hash) is None
                or vector["inputHash"] != expected_input_hash):
            raise ValueError("input identity mismatch")
        features = vector["features"]
        _keys(features, set(FEATURES))
        bounds = {"baseSize": 3, "sameAnchor": 1, "anchorDistance": 3,
                  "firstLength": 256, "secondLength": 256, "lexicalOverlap": 1}
        if any(not _number(features[key]) or not 0 <= features[key] <= bounds[key] for key in FEATURES):
            raise ValueError("invalid feature range or number")
        if any(type(features[key]) is not int for key in FEATURES[:-1]):
            raise ValueError("structural features must be integers")
        score = artifact["bias"] + sum(artifact["weights"][key] * features[key] for key in FEATURES)
        if not math.isfinite(score):
            raise ValueError("nonfinite score")
        result.update(status="proposal", score=score, reason=None)
    except (ValueError, TypeError, OverflowError) as exc:
        result["reason"] = str(exc)
    return result


def rank(candidates: list[dict], artifact: Any, *, expected_hash: str,
         expected_model_id: str) -> list[dict]:
    """Rank by decreasing raw score; ties preserve supplied frozen inventory.

    Abstentions remain visible after scored candidates and consume no verifier
    call. The caller supplies inventory order before labels; this cannot prove
    that the inventory was frozen. No verifier is invoked by this function.
    """
    if type(candidates) is not list or len(candidates) > MAX_CANDIDATES:
        raise ValueError("candidate inventory must be a list")
    results = []
    seen: set[str] = set()
    for candidate in candidates:
        _keys(candidate, {"pairId", "inputHash", "vector"})
        pair_id = candidate["pairId"]
        if type(pair_id) is not str or ID.fullmatch(pair_id) is None or pair_id in seen:
            raise ValueError("invalid or duplicate pair identity")
        seen.add(pair_id)
        results.append({"pairId": pair_id, **propose(candidate["vector"], artifact,
                        expected_hash=expected_hash, expected_input_hash=candidate["inputHash"],
                        expected_model_id=expected_model_id)})
    return sorted(results, key=lambda value: (value["status"] != "proposal",
                                             -value["score"] if value["score"] is not None else 0))
