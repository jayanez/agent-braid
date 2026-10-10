# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic-only offline evaluation candidate for SPEC-019.

This is descriptive software, not an approved protocol or real-data evaluator.
Labels and annotations are supplied separately and are never passed to a
scorer or preparation hook. The status-to-usefulness mapping is deliberately
named/versioned because P019-04 remains under review.
"""
from __future__ import annotations

import json
import math
import random
import statistics
import time
from copy import deepcopy
from typing import Any, Callable

from agent_braid.native_predictor import FEATURES
from agent_braid.native_predictor_training import (
    FEATURES as LEARNED_FEATURES,
    FEATURE_VERSION as LEARNED_FEATURE_VERSION,
    digest as _request_digest,
    fit as _fit_ranker,
    prepare_request,
    score as _score_ranker,
)
from agent_braid.structured_exchange import produce, verify

POLICY_VERSION = "verified-bounded-usefulness-v1"
POLICY = {
    "name": "VerifiedBoundedUsefulnessPolicy",
    "version": POLICY_VERSION,
    "mapping": "one unordered pair per produce+verify call; only verified-bounded can contribute useful yield; divergent and inconclusive consume one call and contribute no yield; abstention consumes zero calls",
    "precisionRecall": "known labels among selected verified-bounded pairs; recall denominator is every known-positive inventory pair",
    "approval": "provisional; P019-04 not approved",
}


class NegativeControlUnavailable(ValueError):
    """No nonidentity, class-preserving train-label permutation is possible."""


def _finite_number(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def permute_training_labels(training_inventory: Any, training_labels: Any, *, seed: int = 0) -> list[dict]:
    """Return train-only rows with the complete label assignment permuted.

    Pair rows are sorted by pairId before applying the fixed seed, so caller
    inventory order cannot change the assignment. Known/unknown and class
    counts are preserved; when possible, the assignment differs from identity.
    """
    if seed != 0:
        raise ValueError("the candidate negative-control seed is fixed at 0")
    if type(training_inventory) is not list or not training_inventory or type(training_labels) is not dict:
        raise ValueError("training inventory and separate labels are required")
    pairs = set()
    checked = []
    expected_row_fields = {"pairId", "familyId", "sessionId", "duplicateGroupId",
                           "partition", "features"}
    # Bind seed-0 assignment to opaque pair identity rather than caller list
    # order, so the same frozen cohort yields the same control after harmless
    # inventory reordering.
    for row in training_inventory:
        if type(row) is not dict or set(row) != expected_row_fields or row.get("partition") != "train":
            raise ValueError("permutation input rows must match the strict train feature schema")
        pair_id = row.get("pairId")
        if (type(pair_id) is not str or not pair_id or type(row["familyId"]) is not str
                or not row["familyId"] or type(row["sessionId"]) is not str
                or not row["sessionId"] or type(row["duplicateGroupId"]) is not str
                or not row["duplicateGroupId"] or pair_id in pairs):
            raise ValueError("invalid or duplicate training pair identity")
        if type(row["features"]) is not dict or set(row["features"]) != set(FEATURES):
            raise ValueError("training feature row does not match the fixed feature schema")
        if any(not _finite_number(row["features"][name]) for name in FEATURES):
            raise ValueError("training features must be finite numbers")
        pairs.add(pair_id)
        if pair_id not in training_labels:
            raise ValueError("training label inventory mismatch")
        label = training_labels[pair_id]
        if label is not None and (type(label) is not int or label not in (0, 1)):
            raise ValueError("training labels must be 0, 1, or None")
        checked.append((deepcopy(row), label))
    if set(training_labels) != pairs:
        raise ValueError("training label inventory mismatch")
    checked.sort(key=lambda item: item[0]["pairId"])
    values = [label for _row, label in checked]
    if set(values) & {0, 1} != {0, 1}:
        raise NegativeControlUnavailable("permuted-label control requires both known training classes")
    permuted = list(values)
    random.Random(0).shuffle(permuted)
    if permuted == values:
        different = next(((i, j) for i in range(len(values)) for j in range(i + 1, len(values))
                          if values[i] != values[j]), None)
        if different is None:
            raise NegativeControlUnavailable("no nonidentity label permutation preserves class counts")
        i, j = different
        permuted[i], permuted[j] = permuted[j], permuted[i]
    if permuted == values:
        raise NegativeControlUnavailable("nonidentity label permutation could not be produced")
    return [{**row, "label": label} for (row, _), label in zip(checked, permuted)]


def _blind_row(row: dict) -> dict:
    # Only the trusted feature preparer and deterministic baseline/verifier may
    # see the request. The learned scorer receives a versioned numeric vector.
    allowed = {"request"}
    return {key: value for key, value in row.items() if key in allowed}


def _scorer_vector(prepared: Any, request: dict) -> dict:
    """Validate preparation output and remove request identity before scoring."""
    expected = {"version", "sourceKind", "inputHash", "features"}
    if type(prepared) is not dict or set(prepared) != expected:
        raise ValueError("preparer must return a request-bound versioned feature vector")
    if (prepared["version"] != LEARNED_FEATURE_VERSION
            or prepared["sourceKind"] != "synthetic"
            or prepared["inputHash"] != _request_digest(request)):
        raise ValueError("prepared feature vector has a version, source or request mismatch")
    features = prepared["features"]
    if type(features) is not dict or set(features) != set(LEARNED_FEATURES):
        raise ValueError("prepared feature vector does not match the fixed feature schema")
    bounds = {"baseSize": 3, "sameAnchor": 1, "anchorDistance": 3,
              "firstLength": 256, "secondLength": 256, "lexicalOverlap": 1}
    if any(not _finite_number(features[name]) or not 0 <= features[name] <= bounds[name]
           for name in LEARNED_FEATURES):
        raise ValueError("prepared feature is nonfinite or outside its declared bounds")
    if any(type(features[name]) is not int
           for name in LEARNED_FEATURES if name != "lexicalOverlap"):
        raise ValueError("structural prepared features must be integers")
    return {"version": LEARNED_FEATURE_VERSION,
            "features": {name: features[name] for name in LEARNED_FEATURES}}


def _default_verifier(request: dict) -> dict:
    """Use the unchanged deterministic evidence producer and verifier."""
    verdict = verify(produce(deepcopy(request)))
    return _checked_verdict(verdict)


def _checked_verdict(verdict: Any) -> dict:
    if type(verdict) is not dict or verdict.get("status") not in {
            "verified-bounded", "divergent", "inconclusive"}:
        raise ValueError("deterministic verifier returned an unrecognized M3 status")
    if verdict.get("executionAuthorization") is not False:
        raise ValueError("deterministic verifier must keep executionAuthorization false")
    return verdict


def _timed_default_verifier(request: dict) -> tuple[dict, dict[str, float | int]]:
    """Measure submitted evidence production separately from verifier regeneration."""
    start = time.perf_counter()
    evidence = produce(deepcopy(request))
    evidence_seconds = time.perf_counter() - start
    start = time.perf_counter()
    verdict = _checked_verdict(verify(evidence))
    verifier_seconds = time.perf_counter() - start
    return verdict, {
        "submittedEvidenceProductionCount": 1,
        "verifierInvocationCount": 1,
        # structured_exchange.verify regenerates evidence internally and compares
        # it with the submitted bundle before returning a bounded verdict.
        "verifierEvidenceRegenerationCount": 1,
        "submittedEvidenceProductionSeconds": evidence_seconds,
        "verifierInvocationSeconds": verifier_seconds,
    }


def _validate(inventory: Any, labels: Any, source_kind: str) -> tuple[list[dict], dict[str, int | None]]:
    if source_kind != "synthetic":
        raise ValueError("only explicitly synthetic inventories are supported")
    if type(inventory) is not list or not inventory:
        raise ValueError("inventory must be a nonempty ordered list")
    if type(labels) is not dict:
        raise ValueError("labels must be a separate pairId mapping")
    rows = []
    seen: set[str] = set()
    seen_unordered_pairs: set[str] = set()
    for row in inventory:
        if type(row) is not dict or not {
                "pairId", "familyId", "sessionId", "duplicateGroupId",
                "partition", "request"} <= set(row):
            raise ValueError(
                "inventory row requires pair, family, session, duplicate group, partition and request")
        if row["partition"] != "holdout":
            raise ValueError("evaluation inventory must contain holdout rows only")
        pair_id, family_id = row["pairId"], row["familyId"]
        if type(pair_id) is not str or not pair_id or type(family_id) is not str or not family_id:
            raise ValueError("invalid pair or family identity")
        for key in ("sessionId", "duplicateGroupId"):
            if type(row[key]) is not str or not row[key]:
                raise ValueError(f"invalid {key}")
        if pair_id in seen:
            raise ValueError("duplicate pair identity")
        seen.add(pair_id)
        for field in ("annotation1", "annotation2", "adjudicatedLabel"):
            if field not in row:
                raise ValueError("every evaluation row requires both reviewer records and adjudication field")
            if field in row and row[field] is not None and (type(row[field]) is not int or row[field] not in (0, 1)):
                raise ValueError("annotation values must be 0, 1, or None")
        for reviewer in ("annotation1", "annotation2"):
            attempted_field = reviewer + "Attempted"
            failure_field = reviewer + "Failure"
            reviewer_id_field = reviewer + "ReviewerId"
            reason_field = reviewer + "UnknownReason"
            if attempted_field not in row or type(row[attempted_field]) is not bool:
                raise ValueError("annotation attempt flags must be booleans")
            if failure_field in row and row[failure_field] is not None and (
                    type(row[failure_field]) is not str or not row[failure_field]):
                raise ValueError("annotation failure must be nonempty text or None")
            if reviewer_id_field not in row or (row[reviewer_id_field] is not None and
                                                  (type(row[reviewer_id_field]) is not str or not row[reviewer_id_field])):
                raise ValueError("reviewer identity must be an opaque ID or None")
            if reason_field not in row or (row[reason_field] is not None and
                                            (type(row[reason_field]) is not str or not row[reason_field])):
                raise ValueError("unknown-label reason must be nonempty text or None")
            value = row[reviewer]
            attempted = row[attempted_field]
            failure = row.get(failure_field)
            if attempted and row[reviewer_id_field] is None:
                raise ValueError("attempted reviewer record requires an opaque reviewer ID")
            if not attempted and (row[reviewer_id_field] is not None or value is not None or failure is not None):
                raise ValueError("unattempted reviewer record cannot contain identity, label or failure")
            if value in (0, 1) and (failure is not None or row[reason_field] is not None):
                raise ValueError("known reviewer label cannot carry failure or unknown reason")
            if attempted and value is None and failure is None and row[reason_field] is None:
                raise ValueError("attempted unknown reviewer label requires a reason")
        if (row["annotation1Attempted"] and row["annotation2Attempted"]
                and row["annotation1ReviewerId"] == row["annotation2ReviewerId"]):
            raise ValueError("independent reviewers must have distinct opaque IDs")
        if not row["annotation1Attempted"] or not row["annotation2Attempted"]:
            raise ValueError("every evaluated pair requires two independent reviewer attempts")
        adjudication_fields = ("adjudicationAttempted", "adjudicatorId",
                              "adjudicationRationale", "adjudicationUnknownReason")
        if any(field not in row for field in adjudication_fields):
            raise ValueError("every evaluation row requires an explicit adjudication record")
        if type(row["adjudicationAttempted"]) is not bool:
            raise ValueError("adjudication attempt flag must be boolean")
        for field in ("adjudicatorId", "adjudicationRationale", "adjudicationUnknownReason"):
            value = row[field]
            if value is not None and (type(value) is not str or not value):
                raise ValueError(f"{field} must be nonempty text or None")
        disagreement = (row["annotation1"] in (0, 1) and row["annotation2"] in (0, 1)
                        and row["annotation1"] != row["annotation2"])
        if disagreement and not row["adjudicationAttempted"]:
            raise ValueError("reviewer disagreement requires a third-reviewer adjudication attempt")
        if row["adjudicationAttempted"]:
            if not disagreement or row["adjudicatorId"] is None:
                raise ValueError("adjudication requires a recorded third reviewer for disagreement")
            if row["adjudicatorId"] in {row["annotation1ReviewerId"], row["annotation2ReviewerId"]}:
                raise ValueError("adjudicator ID must differ from both independent reviewers")
            if row["adjudicatedLabel"] is None and row["adjudicationUnknownReason"] is None:
                raise ValueError("unknown adjudication requires a reason")
            if row["adjudicatedLabel"] in (0, 1) and row["adjudicationRationale"] is None:
                raise ValueError("known adjudication requires a rationale")
            if row["adjudicatedLabel"] is None and row["adjudicationRationale"] is not None:
                raise ValueError("unknown adjudication cannot carry a known-label rationale")
            if row["adjudicatedLabel"] in (0, 1) and row["adjudicationUnknownReason"] is not None:
                raise ValueError("known adjudication cannot carry an unknown-label reason")
        elif any(row[field] is not None for field in ("adjudicatorId", "adjudicationRationale",
                                                      "adjudicationUnknownReason", "adjudicatedLabel")):
            raise ValueError("unattempted adjudication cannot contain outcome metadata")
        request = row["request"]
        # Validate request without deriving or altering its semantics.
        from agent_braid.structured_exchange import validate_request
        validate_request(request)
        if len(request["operations"]) != 2:
            raise ValueError("holdout inventory must consist of unordered pairs")
        if any(operation["kind"] != "insert" for operation in request["operations"]):
            raise ValueError("holdout inventory must contain pure insert pairs")
        canonical_pair = json.dumps({"base": request["base"],
                                     "operations": sorted(request["operations"], key=lambda op: op["id"])},
                                    sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if canonical_pair in seen_unordered_pairs:
            raise ValueError("duplicate unordered pair request")
        seen_unordered_pairs.add(canonical_pair)
        rows.append(deepcopy(row))
    if set(labels) != seen:
        raise ValueError("label inventory must exactly match pair inventory")
    checked_labels: dict[str, int | None] = {}
    rows_by_id = {row["pairId"]: row for row in rows}
    for pair_id, value in labels.items():
        if value is not None and (type(value) is not int or value not in (0, 1)):
            raise ValueError("labels must be 0, 1, or None")
        row = rows_by_id[pair_id]
        first, second, adjudicated = (row["annotation1"], row["annotation2"],
                                      row["adjudicatedLabel"])
        if first in (0, 1) and second in (0, 1):
            if first == second:
                if adjudicated is not None and adjudicated != first:
                    raise ValueError("adjudication conflicts with reviewer consensus")
                derived = first
            else:
                derived = adjudicated
        else:
            if adjudicated is not None:
                raise ValueError("adjudication requires two completed independent reviewer labels")
            derived = None
        if value != derived:
            raise ValueError("metric label differs from reviewer consensus/adjudication")
        checked_labels[pair_id] = value
    return rows, deepcopy(checked_labels)


def _prediction(value: Any) -> tuple[float | None, float | None]:
    """Normalize score callback output. None or abstain status means abstain."""
    if value is None:
        return None, None
    if type(value) is dict:
        if value.get("status") != "proposal":
            return None, None
        score, probability = value.get("score"), value.get("probability")
    else:
        score, probability = value, None
    if not _finite_number(score):
        return None, None
    if probability is not None and (not _finite_number(probability) or not 0 <= probability <= 1):
        raise ValueError("calibrated probability must be finite and in [0, 1]")
    return float(score), None if probability is None else float(probability)


def _select(rows: list[dict], scores: dict[str, float | None], n_calls: int) -> list[dict]:
    # Stable sorting preserves the frozen inventory sequence on exact ties.
    ranked = sorted(rows, key=lambda row: (scores[row["pairId"]] is None,
                                           -(scores[row["pairId"]] or 0.0)))
    return [row for row in ranked if scores[row["pairId"]] is not None][:n_calls]


def _metrics(rows: list[dict], labels: dict[str, int | None], selected: list[dict],
             verdicts: dict[str, dict], family_ids: list[str]) -> dict:
    categories = {"knownUseful": 0, "knownNotUseful": 0, "unknown": 0}
    verified_categories = {"knownUseful": 0, "knownNotUseful": 0, "unknown": 0}
    verified_useful = verified_known = verified_unknown = 0
    status_counts = {"verified-bounded": 0, "divergent": 0, "inconclusive": 0}
    selected_by_family: dict[str, list[dict]] = {family: [] for family in family_ids}
    for row in selected:
        selected_by_family[row["familyId"]].append(row)
    for row in selected:
        pair = row["pairId"]
        label = labels[pair]
        status = verdicts[pair]["status"]
        if status not in status_counts:
            status = "inconclusive"
        status_counts[status] += 1
        valid = status == "verified-bounded"
        if valid:
            verified_categories[{1: "knownUseful", 0: "knownNotUseful", None: "unknown"}[label]] += 1
        if label == 1:
            categories["knownUseful"] += 1
        elif label == 0:
            categories["knownNotUseful"] += 1
        else:
            categories["unknown"] += 1
        if valid and label is not None:
            verified_known += 1
            verified_useful += int(label == 1)
        elif valid:
            verified_unknown += 1
    known_total_useful = sum(value == 1 for value in labels.values())
    denominator = verified_known
    per_family = {}
    for family in family_ids:
        family_rows = [r for r in rows if r["familyId"] == family]
        family_labels = [labels[r["pairId"]] for r in family_rows]
        family_selected = selected_by_family[family]
        family_verified = [r for r in family_selected
                           if verdicts[r["pairId"]]["status"] == "verified-bounded"]
        family_verified_labels = [labels[r["pairId"]] for r in family_verified]
        family_known_useful = sum(label == 1 for label in family_labels)
        family_known_not = sum(label == 0 for label in family_labels)
        family_unknown = sum(label is None for label in family_labels)
        family_verified_useful = sum(label == 1 for label in family_verified_labels)
        family_verified_unknown = sum(label is None for label in family_verified_labels)
        known_count = family_known_useful + family_known_not
        per_family[family] = {
            "inventoryPairs": len(family_rows),
            "inventoryLabels": {"knownUseful": family_known_useful,
                                "knownNotUseful": family_known_not, "unknown": family_unknown},
            "knownClassPrevalence": {"useful": family_known_useful / known_count if known_count else None,
                                     "notUseful": family_known_not / known_count if known_count else None,
                                     "knownCoverage": known_count / len(family_rows)},
            "selectedPairs": len(family_selected),
            "actualVerifierCalls": len(family_selected),
            "verifiedBoundedCalls": len(family_verified),
            "verifiedBoundedUsefulYield": family_verified_useful,
            "verifiedUsefulYieldBounds": {"lower": family_verified_useful,
                                          "upper": family_verified_useful + family_verified_unknown,
                                          "uncertainty": "missing-label identification bounds, not confidence intervals"},
            "selectedVerifiedLabels": {
                "knownUseful": family_verified_useful,
                "knownNotUseful": sum(label == 0 for label in family_verified_labels),
                "unknown": family_verified_unknown,
            },
        }
    return {
        "actualVerifierCalls": len(selected),
        "selectedLabels": categories,
        "verifiedBoundedSelectedLabels": verified_categories,
        "verifierStatuses": status_counts,
        "knownLabelPrecision": verified_useful / denominator if denominator else None,
        "knownLabelRecall": verified_useful / known_total_useful if known_total_useful else None,
        "knownUsefulInventory": known_total_useful,
        "verifiedBoundedUsefulYield": verified_useful,
        "verifiedUsefulYieldBounds": {"lower": verified_useful,
                                      "upper": verified_useful + verified_unknown,
                                      "uncertainty": "missing-label identification bounds, not confidence intervals"},
        "perFamily": per_family,
    }


def _negative_control(rows: list[dict], labels: dict[str, int | None], *,
                      training_inventory: Any, training_labels: Any,
                      calibration_inventory: Any, calibration_labels: Any) -> dict:
    """Fit a synthetic permuted-label control and verify its input commitments."""
    if any(value is None for value in (training_inventory, training_labels,
                                       calibration_inventory, calibration_labels)):
        raise ValueError("negative-control fit requires separate train and calibration inputs")
    if type(calibration_inventory) is not list or not calibration_inventory:
        raise ValueError("negative-control calibration inventory must be nonempty")
    if type(calibration_labels) is not dict:
        raise ValueError("negative-control calibration labels must be a separate mapping")

    permuted_training = permute_training_labels(training_inventory, training_labels, seed=0)
    training_ids = {row["pairId"] for row in permuted_training}
    calibration_ids = set()
    calibration_rows = []
    for row in calibration_inventory:
        if type(row) is not dict or set(row) != {
                "pairId", "familyId", "sessionId", "duplicateGroupId",
                "partition", "features"}:
            raise ValueError("calibration inventory does not match the fixed feature-row schema")
        if row["partition"] != "calibration" or row["pairId"] in calibration_ids:
            raise ValueError("calibration inventory has an invalid partition or duplicate pair")
        calibration_ids.add(row["pairId"])
        calibration_rows.append({**deepcopy(row), "label": calibration_labels.get(row["pairId"])})
    if set(calibration_labels) != calibration_ids:
        raise ValueError("calibration label inventory mismatch")

    holdout_pairs = {row["pairId"] for row in rows}
    if training_ids & calibration_ids or (training_ids | calibration_ids) & holdout_pairs:
        raise ValueError("train, calibration and holdout pair identities must be disjoint")
    training_families = {row["familyId"] for row in permuted_training}
    calibration_families = {row["familyId"] for row in calibration_rows}
    holdout_families = {row["familyId"] for row in rows}
    training_sessions = {row["sessionId"] for row in permuted_training}
    calibration_sessions = {row["sessionId"] for row in calibration_rows}
    training_duplicate_groups = {row["duplicateGroupId"] for row in permuted_training}
    calibration_duplicate_groups = {row["duplicateGroupId"] for row in calibration_rows}
    if any(type(row.get("sessionId")) is not str or not row["sessionId"] for row in rows):
        raise ValueError("permuted-label control requires holdout session identities")
    if any(type(row.get("duplicateGroupId")) is not str or not row["duplicateGroupId"]
           for row in rows):
        raise ValueError("permuted-label control requires holdout duplicate-group identities")
    holdout_sessions = {row["sessionId"] for row in rows}
    holdout_duplicate_groups = {row["duplicateGroupId"] for row in rows}
    if (training_families & calibration_families or (training_families | calibration_families) & holdout_families
            or training_sessions & calibration_sessions
            or (training_sessions | calibration_sessions) & holdout_sessions
            or training_duplicate_groups & calibration_duplicate_groups
            or (training_duplicate_groups | calibration_duplicate_groups) & holdout_duplicate_groups):
        raise ValueError(
            "train, calibration and holdout families/sessions/duplicate groups must be disjoint")

    fit_rows = permuted_training + calibration_rows
    fit_started = time.perf_counter()
    artifact = _fit_ranker(fit_rows, model_id="m35-permuted-label-control-v1",
                           dataset_kind="synthetic")
    fit_seconds = time.perf_counter() - fit_started
    model_hash = _request_digest(artifact)
    expected_train_hash = _request_digest(sorted(permuted_training, key=lambda row: row["pairId"]))
    expected_calibration_hash = _request_digest(sorted(calibration_rows, key=lambda row: row["pairId"]))
    commitments = artifact["inputCommitments"]
    if commitments["train"] != expected_train_hash or commitments["calibration"] != expected_calibration_hash:
        raise ValueError("negative-control artifact commitments do not match the frozen fit inputs")

    scores: dict[str, float | None] = {}
    probabilities: dict[str, float | None] = {}
    for row in rows:
        prepared = prepare_request(row["request"], source_kind="synthetic")
        vector = {"version": prepared["version"], "features": prepared["features"]}
        prediction = _score_ranker(vector, artifact, expected_hash=model_hash,
                                   expected_model_id="m35-permuted-label-control-v1")
        score, probability = _prediction(prediction)
        scores[row["pairId"]] = score
        probabilities[row["pairId"]] = probability

    metrics_by_budget = {}
    families = sorted({row["familyId"] for row in rows})
    for fraction in (0.25, 0.5, 1.0):
        ceiling = math.floor(fraction * len(rows))
        selected = _select(rows, scores, ceiling)
        verdicts = {}
        verifier_work = {"submittedEvidenceProductionCount": 0,
                         "verifierInvocationCount": 0,
                         "verifierEvidenceRegenerationCount": 0}
        for row in selected:
            verdict, work = _timed_default_verifier(row["request"])
            verdicts[row["pairId"]] = verdict
            for name in verifier_work:
                verifier_work[name] += work[name]
        metrics = _metrics(rows, labels, selected, verdicts, families)
        metrics.update({"budgetCeiling": ceiling,
                        "inventoryPairs": len(rows),
                        "abstentions": sum(value is None for value in scores.values()),
                        "unusedCalls": max(0, ceiling - len(selected)),
                        "calibration": _calibration_metrics(rows, labels, probabilities),
                        "verifierWork": verifier_work})
        metrics_by_budget[str(int(fraction * 100))] = metrics

    return {
        "status": "available", "seed": 0,
        "fitMethod": "native_predictor_training.fit",
        "fitInputCommitmentsVerified": True,
        "trainingLabelPermutationVerified": True,
        "trainingAssignmentChanged": True,
        "classCountsPreserved": True,
        "holdoutLabelsPermuted": False,
        "factoryUsed": False,
        "holdoutRowsOrLabelsUsedForFit": False,
        "trainingLabelCounts": {str(label): sum(row["label"] == label for row in permuted_training)
                                for label in (0, 1, None)},
        "trainingInputCommitment": expected_train_hash,
        "calibrationInputCommitment": expected_calibration_hash,
        "artifactHash": model_hash,
        "fitSeconds": fit_seconds,
        "costAccounting": (
            "fitSeconds covers trainer fit (weight fitting, calibration and in-memory artifact construction); "
            "verifier work is counted per selected pair; "
            "negative-control inference, ranking, verification and serialization timings "
            "are not a policy-arm cost comparison"
        ),
        "metricsByBudget": metrics_by_budget,
        "interpretation": "synthetic permuted-label control; descriptive only",
    }


def _label_agreement(rows: list[dict], family_ids: list[str]) -> dict:
    result = {}
    for family in family_ids:
        family_rows = [r for r in rows if r["familyId"] == family]
        reviewer_stats = {}
        for reviewer in ("annotation1", "annotation2"):
            attempted_rows = [r for r in family_rows if r[reviewer + "Attempted"]]
            failed_rows = [r for r in attempted_rows if r.get(reviewer + "Failure")]
            missing_rows = [r for r in attempted_rows
                            if r.get(reviewer) is None and not r.get(reviewer + "Failure")]
            reviewer_stats[reviewer] = {
                "attempted": len(attempted_rows),
                "failed": len(failed_rows),
                "missingField": len(missing_rows),
                "attemptRate": len(attempted_rows) / len(family_rows) if family_rows else None,
                "failureRateAmongAttempts": len(failed_rows) / len(attempted_rows) if attempted_rows else None,
                "missingFieldRateAmongAttempts": len(missing_rows) / len(attempted_rows) if attempted_rows else None,
            }
        pair_attempts = [r for r in family_rows
                         if r["annotation1Attempted"] and r["annotation2Attempted"]]
        disagreements = [r for r in pair_attempts if r.get("annotation1") in (0, 1)
                         and r.get("annotation2") in (0, 1) and r["annotation1"] != r["annotation2"]]
        resolved = sum((r.get("annotation1") == r.get("annotation2") and r.get("annotation1") in (0, 1))
                       or (r["adjudicationAttempted"] and r.get("adjudicatedLabel") in (0, 1))
                       for r in pair_attempts)
        unresolved = len(pair_attempts) - resolved
        labeled_pairs = sum(r.get("annotation1") in (0, 1) and r.get("annotation2") in (0, 1)
                            for r in pair_attempts)
        result[family] = {
            "inventoryPairs": len(family_rows), "reviewers": reviewer_stats,
            "pairAttempts": len(pair_attempts), "resolved": resolved,
            "unresolvedOrMissing": unresolved,
            "unresolvedRateAmongPairAttempts": unresolved / len(pair_attempts) if pair_attempts else None,
            "rawDisagreements": len(disagreements),
            "disagreementRateAmongDoubleKnown": len(disagreements) / labeled_pairs if labeled_pairs else None,
            "adjudicatedDisagreements": sum(r["adjudicationAttempted"] and
                                             r.get("adjudicatedLabel") in (0, 1)
                                             for r in disagreements),
        }
    return result


def _calibration_metrics(rows: list[dict], labels: dict[str, int | None],
                         probabilities: dict[str, float | None]) -> dict:
    known = [(probabilities[r["pairId"]], labels[r["pairId"]]) for r in rows
             if probabilities[r["pairId"]] is not None and labels[r["pairId"]] is not None]
    if not known:
        return {"brier": None, "coverage": 0,
                "reason": "no scorer-supplied probability claims with known labels",
                "probabilityClaimStatus": "unvalidated-scorer-supplied",
                "probabilityProvenanceValidated": False}
    ordered = sorted(known, key=lambda item: item[0])
    bins = []
    for i in range(5):
        lo, hi = i * len(ordered) // 5, (i + 1) * len(ordered) // 5
        chunk = ordered[lo:hi]
        bins.append({"count": len(chunk), "meanProbability": statistics.mean(p for p, _ in chunk) if chunk else None,
                     "observedRate": statistics.mean(y for _, y in chunk) if chunk else None,
                     "status": "too-sparse" if len(chunk) < 10 else "descriptive"})
    return {"brier": statistics.mean((p - y) ** 2 for p, y in known),
            "coverage": len(known), "knownLabelCoverage": len(known), "reliabilityBins": bins,
            "interpretation": "descriptive only",
            "probabilityClaimStatus": "unvalidated-scorer-supplied",
            "probabilityProvenanceValidated": False,
            "probabilitySource": "scorer callback response; artifact and calibration provenance are not checked"}


def _run_policy(rows: list[dict], labels: dict[str, int | None], *, scorer: Callable,
                preparation: Callable | None, fraction: float,
                inference_policy: bool,
                source_extractor: Callable | None) -> tuple[dict, dict]:
    n = len(rows)
    ceiling = math.floor(fraction * n)
    phase = {"sourceExtractionSeconds": 0.0, "preparationSeconds": 0.0,
             "scoringSeconds": 0.0, "inferenceSeconds": 0.0,
             "rankingSeconds": 0.0, "verificationSeconds": 0.0,
             "submittedEvidenceProductionSeconds": 0.0,
             "verifierInvocationSeconds": 0.0, "serializationSeconds": 0.0}
    t0 = time.perf_counter()
    scores: dict[str, float | None] = {}
    probabilities: dict[str, float | None] = {}
    prepared: dict[str, Any] = {}
    measured_rows = []
    from agent_braid.structured_exchange import validate_request
    for row in rows:
        request = deepcopy(row["request"])
        if source_extractor is not None:
            start = time.perf_counter()
            extracted = source_extractor(deepcopy(row["sourceInput"]))
            validate_request(extracted)
            if _request_digest(extracted) != _request_digest(row["request"]):
                raise ValueError("source extractor output differs from the frozen request commitment")
            phase["sourceExtractionSeconds"] += time.perf_counter() - start
            request = deepcopy(extracted)
        measured_rows.append({**{key: value for key, value in row.items()
                                 if key != "sourceInput"}, "request": request})
    rows = measured_rows
    for row in rows:
        candidate = _blind_row(row)
        if inference_policy:
            start = time.perf_counter()
            raw_prepared = (preparation(deepcopy(candidate)) if preparation is not None
                            else prepare_request(candidate["request"], source_kind="synthetic"))
            checked_vector = _scorer_vector(raw_prepared, candidate["request"])
            phase["preparationSeconds"] += time.perf_counter() - start
            if preparation is not None:
                # A hook may adapt/measure preparation, but cannot replace the
                # frozen extractor with label- or identity-encoded feature data.
                # Keep this correctness check outside the hook's measured cost.
                canonical_vector = _scorer_vector(
                    prepare_request(candidate["request"], source_kind="synthetic"),
                    candidate["request"])
                if checked_vector != canonical_vector:
                    raise ValueError("preparer features differ from the canonical request extractor")
            prepared[row["pairId"]] = checked_vector
        else:
            # The rule baseline ranks directly from the request; do not charge
            # predictor-only feature preparation to its measured cost.
            prepared[row["pairId"]] = deepcopy(candidate["request"])
        start = time.perf_counter()
        if inference_policy:
            raw = scorer(deepcopy(prepared[row["pairId"]]))
        else:
            raw = scorer(candidate, deepcopy(prepared[row["pairId"]]))
        elapsed = time.perf_counter() - start
        phase["inferenceSeconds" if inference_policy else "scoringSeconds"] += elapsed
        start = time.perf_counter()
        scores[row["pairId"]], probabilities[row["pairId"]] = _prediction(raw)
        phase["scoringSeconds"] += time.perf_counter() - start
    start = time.perf_counter()
    selected = _select(rows, scores, ceiling)
    phase["rankingSeconds"] += time.perf_counter() - start
    verdicts = {}
    verifier_work = {"submittedEvidenceProductionCount": 0,
                     "verifierInvocationCount": 0,
                     "verifierEvidenceRegenerationCount": 0}
    for row in selected:
        # One call unit per selected pair; expose its producer and verifier paths.
        verdict, work = _timed_default_verifier(row["request"])
        for name in verifier_work:
            verifier_work[name] += work[name]
        phase["submittedEvidenceProductionSeconds"] += work["submittedEvidenceProductionSeconds"]
        phase["verifierInvocationSeconds"] += work["verifierInvocationSeconds"]
        verdicts[row["pairId"]] = verdict
    phase["verificationSeconds"] = (phase["submittedEvidenceProductionSeconds"]
                                     + phase["verifierInvocationSeconds"])
    result = _metrics(rows, labels, selected, verdicts, sorted({r["familyId"] for r in rows}))
    abstentions = sum(score is None for score in scores.values())
    result["abstentions"] = abstentions
    result["unusedCalls"] = max(0, ceiling - len(selected))
    result["verifierWork"] = verifier_work
    result["budgetCeiling"] = ceiling
    result["inventoryPairs"] = n
    result["abstentionsSelected"] = 0
    result["calibration"] = _calibration_metrics(rows, labels, probabilities)
    result["phaseSeconds"] = dict(phase)
    result["totalAnalysisSeconds"] = 0.0
    result["serializationTimingNote"] = (
        "complete policy schema serialized with zero placeholders for self-referential timing fields; "
        "measured serialization duration and total are filled immediately afterward"
    )
    start = time.perf_counter()
    json.dumps(result, sort_keys=True, separators=(",", ":"), allow_nan=False)
    phase["serializationSeconds"] = time.perf_counter() - start
    result["phaseSeconds"] = dict(phase)
    result["totalAnalysisSeconds"] = time.perf_counter() - t0
    return result, scores


def evaluate(inventory: Any, labels: Any, *, scorer: Callable[[dict], Any],
             dataset_kind: str, preparation: Callable[[dict], Any] | None = None,
             source_extractor: Callable[[Any], dict] | None = None,
             training_inventory: Any = None, training_labels: Any = None,
             calibration_inventory: Any = None, calibration_labels: Any = None,
             warmups: int = 3, repetitions: int = 20) -> dict:
    """Compare the baseline and supplied ranker on one synthetic holdout.

    The predictor ``scorer(vector)`` receives directly only a versioned
    six-feature vector. This in-process Python callback is trusted code, not a
    sandbox: closures or process-global state are outside this argument-level
    boundary. The deterministic baseline and verifier retain access to the
    validated request. ``source_extractor(sourceInput)`` is a trusted synthetic
    callback; it receives no labels, runs identically for each policy, and its
    canonical request output is checked against the frozen request. When set,
    each row must provide ``sourceInput``. The payload is never passed to the
    predictor scorer. ``preparation(row)`` is also trusted code; it receives
    ``{"request": ...}``, is timed, and its result must match the canonical
    extractor. Without a hook, the canonical synthetic extractor is used and
    timed. This hook does not prove or authorize real journal extraction.
    The permuted-label control, when supplied, is fit internally with the
    canonical offline trainer from train-only permuted labels plus separate
    calibration rows. Holdout labels never enter fit or scoring callbacks.
    """
    rows, checked_labels = _validate(inventory, labels, dataset_kind)
    if source_extractor is not None and any("sourceInput" not in row for row in rows):
        raise ValueError("source extraction requires sourceInput on every inventory row")
    if type(warmups) is not int or warmups != 3 or type(repetitions) is not int or repetitions != 20:
        raise ValueError("candidate protocol uses exactly three warmups and twenty repetitions")
    families = sorted({r["familyId"] for r in rows})

    def baseline_scorer(row: dict, _prepared: Any) -> int:
        operations = row["request"]["operations"]
        return int(operations[0]["anchorId"] == operations[1]["anchorId"])

    policies = [("baseline", baseline_scorer), ("predictor", scorer)]
    for i in range(warmups):
        order = policies if i % 2 == 0 else policies[::-1]
        for name, policy_scorer in order:
            for fraction in (0.25, 0.5, 1.0):
                _run_policy(rows, checked_labels, scorer=policy_scorer,
                            preparation=preparation, fraction=fraction,
                            inference_policy=(name != "baseline"),
                            source_extractor=source_extractor)
    samples: dict[str, dict[float, list[dict]]] = {
        name: {fraction: [] for fraction in (0.25, 0.5, 1.0)} for name, _ in policies}
    for rep in range(repetitions):
        order = policies if rep % 2 == 0 else policies[::-1]
        for name, policy_scorer in order:
            for fraction in (0.25, 0.5, 1.0):
                measured, _ = _run_policy(rows, checked_labels, scorer=policy_scorer,
                                          preparation=preparation, fraction=fraction,
                                          inference_policy=(name != "baseline"),
                                          source_extractor=source_extractor)
                samples[name][fraction].append(measured)
    summaries = {}
    for name, by_budget in samples.items():
        summaries[name] = {}
        for fraction, values in by_budget.items():
            first = values[0]
            totals = [v["totalAnalysisSeconds"] for v in values]
            summaries[name][str(int(fraction * 100))] = {
                **{k: v for k, v in first.items() if k not in {"phaseSeconds", "totalAnalysisSeconds", "calibration"}},
                "calibration": first["calibration"],
                "timing": {"repetitions": repetitions, "medianTotalSeconds": statistics.median(totals),
                           "rangeTotalSeconds": [min(totals), max(totals)],
                           "phaseMedianSeconds": {key: statistics.median(v["phaseSeconds"][key] for v in values)
                                                   for key in values[0]["phaseSeconds"]},
                           "clock": "time.perf_counter monotonic", "trainingAndAnnotationIncluded": False},
            }

    policy_differences: dict[str, dict] = {}
    for budget in ("25", "50", "100"):
        baseline_family = summaries["baseline"][budget]["perFamily"]
        predictor_family = summaries["predictor"][budget]["perFamily"]
        policy_differences[budget] = {}
        for family in families:
            baseline_metrics = baseline_family[family]
            predictor_metrics = predictor_family[family]
            policy_differences[budget][family] = {
                "verifiedBoundedUsefulYieldDifferencePredictorMinusBaseline":
                    predictor_metrics["verifiedBoundedUsefulYield"] - baseline_metrics["verifiedBoundedUsefulYield"],
                "verifiedUsefulYieldLowerBoundDifferencePredictorMinusBaseline":
                    predictor_metrics["verifiedUsefulYieldBounds"]["lower"] - baseline_metrics["verifiedUsefulYieldBounds"]["lower"],
                "verifiedUsefulYieldUpperBoundDifferencePredictorMinusBaseline":
                    predictor_metrics["verifiedUsefulYieldBounds"]["upper"] - baseline_metrics["verifiedUsefulYieldBounds"]["upper"],
                "verifierCallDifferencePredictorMinusBaseline":
                    predictor_metrics["actualVerifierCalls"] - baseline_metrics["actualVerifierCalls"],
            }

    control_inputs = (training_inventory, training_labels,
                      calibration_inventory, calibration_labels)
    if all(value is None for value in control_inputs):
        negative_control = {"status": "unavailable",
                            "reason": "separate train and calibration inputs were not supplied",
                            "holdoutLabelsPermuted": False}
    elif any(value is None for value in control_inputs):
        raise ValueError("permuted-label control requires separate train and calibration inputs")
    else:
        try:
            negative_control = _negative_control(
                rows, checked_labels, training_inventory=training_inventory,
                training_labels=training_labels, calibration_inventory=calibration_inventory,
                calibration_labels=calibration_labels)
        except NegativeControlUnavailable as exc:
            negative_control = {"status": "unavailable", "reason": str(exc),
                                "seed": 0, "holdoutLabelsPermuted": False,
                                "fitInputCommitmentsVerified": False,
                                "trainingLabelPermutationVerified": False}
    report = {
        "format": "m35-evaluation-report-v1", "sourceKind": "synthetic",
        "status": "synthetic-descriptive-only",
        "protocolApproval": "not-approved; founder-selected call unit and status mapping recorded; remaining protocol review is pending",
        "policy": POLICY, "inventoryOrder": "caller-supplied stable order; tie breaks preserve it",
        "labelIsolation": "labels and annotations are separate and never passed directly to scorer or preparation callbacks",
        "scorerInputBoundary": "direct scorer argument contains only the learned feature version and six canonical numeric features; callbacks are trusted in-process code, not isolated from closures or process-global state",
        "repetitions": {"warmupsPerPolicy": warmups, "measuredPerPolicy": repetitions,
                        "policyOrder": "alternating baseline/predictor and predictor/baseline"},
            "families": families,
            "annotationAgreementByFamily": _label_agreement(rows, families),
            "budgets": summaries,
            "policyDifferencesByFamilyAndBudget": policy_differences,
            "holdoutInventoryByFamily": {
                family: {key: value for key, value in summaries["baseline"]["100"]["perFamily"][family].items()
                         if key in {"inventoryPairs", "inventoryLabels", "knownClassPrevalence"}}
                for family in families
            },
        "permutedLabelNegativeControl": negative_control,
        "preparationMeasurement": {
            "hookProvided": preparation is not None,
            "status": "trusted request-to-feature hook measured per repetition" if preparation is not None
                     else "canonical synthetic request-to-feature extraction measured per repetition",
            "sourceExtraction": "measured per policy/budget/repetition from sourceInput"
                               if source_extractor is not None else
                               "not measured; evaluator input is already an in-memory validated request",
            "limitation": "without the hook, source-to-request extraction is outside this evaluator; the hook is synthetic-only and does not implement or authorize admitted-journal extraction",
        },
        "timingPhaseDefinitions": {
            "inferenceSeconds": "predictor scorer callback duration only",
            "scoringSeconds": "baseline priority callback plus score response normalization/validation; predictor callback time is excluded",
            "sourceExtraction": "included per policy/budget/repetition only when a source_extractor is supplied",
        },
        "probabilityNote": "A probability is an unvalidated scorer-supplied claim; no artifact/calibration provenance is checked. Brier and reliability are descriptive only.",
        "executionAuthorization": False,
    }
    report["reportSerializationSeconds"] = 0.0
    report["finalReportSerializationIncludedInPolicyTotals"] = True
    report["reportSerializationAllocation"] = "one-half shared report serialization per policy arm"
    report["completeCostStatus"] = ("synthetic-callback-boundary-measured" if source_extractor is not None
                                    else "incomplete-source-extraction")
    for policy in ("baseline", "predictor"):
        for summary in report["budgets"][policy].values():
            summary["timing"]["sharedReportSerializationShareSeconds"] = 0.0
            summary["timing"]["fullCostMedianSeconds"] = 0.0
            summary["timing"]["fullCostRangeSeconds"] = [0.0, 0.0]
            summary["timing"]["fullCostIncludesSourceExtraction"] = source_extractor is not None
    report["reportSerializationTimingNote"] = (
        "comparison report serialized with zero placeholders for self-referential timing; "
        "the measured shared duration is allocated equally across the two policy arms"
    )
    start = time.perf_counter()
    json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["reportSerializationSeconds"] = time.perf_counter() - start
    shared_half = report["reportSerializationSeconds"] / 2
    for policy in ("baseline", "predictor"):
        for summary in report["budgets"][policy].values():
            timing = summary["timing"]
            timing["sharedReportSerializationShareSeconds"] = shared_half
            timing["fullCostMedianSeconds"] = timing["medianTotalSeconds"] + shared_half
            timing["fullCostRangeSeconds"] = [value + shared_half
                                               for value in timing["rangeTotalSeconds"]]
    return report
