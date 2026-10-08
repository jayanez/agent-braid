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

    The returned rows are intended only for a negative-control fit factory.
    They contain no holdout or calibration records. The known/unknown and
    class counts are preserved. If any nonidentity assignment is possible,
    the returned assignment is guaranteed to differ from the original.
    """
    if seed != 0:
        raise ValueError("the candidate negative-control seed is fixed at 0")
    if type(training_inventory) is not list or not training_inventory or type(training_labels) is not dict:
        raise ValueError("training inventory and separate labels are required")
    pairs = set()
    values = []
    checked = []
    expected_row_fields = {"pairId", "familyId", "sessionId", "partition", "features"}
    for row in training_inventory:
        if type(row) is not dict or set(row) != expected_row_fields or row.get("partition") != "train":
            raise ValueError("permutation input rows must match the strict train feature schema")
        pair_id = row.get("pairId")
        if (type(pair_id) is not str or not pair_id or type(row["familyId"]) is not str
                or not row["familyId"] or type(row["sessionId"]) is not str
                or not row["sessionId"] or pair_id in pairs):
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
        values.append(label)
    if set(training_labels) != pairs:
        raise ValueError("training label inventory mismatch")
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
    # Feature payloads are derived only from the validated request. Never pass
    # inventory-supplied feature fields across the scorer/preparer boundary.
    allowed = {"request"}
    return {key: value for key, value in row.items() if key in allowed}


def _default_verifier(request: dict) -> dict:
    """Use the unchanged deterministic evidence producer and verifier."""
    verdict = verify(produce(deepcopy(request)))
    if type(verdict) is not dict or verdict.get("status") not in {
            "verified-bounded", "divergent", "inconclusive"}:
        raise ValueError("deterministic verifier returned an unrecognized M3 status")
    if verdict.get("executionAuthorization") is not False:
        raise ValueError("deterministic verifier must keep executionAuthorization false")
    return verdict


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
        if type(row) is not dict or not {"pairId", "familyId", "partition", "request"} <= set(row):
            raise ValueError("inventory row requires pairId, familyId, partition and request")
        if row["partition"] != "holdout":
            raise ValueError("evaluation inventory must contain holdout rows only")
        pair_id, family_id = row["pairId"], row["familyId"]
        if type(pair_id) is not str or not pair_id or type(family_id) is not str or not family_id:
            raise ValueError("invalid pair or family identity")
        if pair_id in seen:
            raise ValueError("duplicate pair identity")
        seen.add(pair_id)
        for field in ("annotation1", "annotation2", "adjudicatedLabel"):
            if field in row and row[field] is not None and (type(row[field]) is not int or row[field] not in (0, 1)):
                raise ValueError("annotation values must be 0, 1, or None")
        for reviewer in ("annotation1", "annotation2"):
            attempted_field = reviewer + "Attempted"
            failure_field = reviewer + "Failure"
            if attempted_field in row and type(row[attempted_field]) is not bool:
                raise ValueError("annotation attempt flags must be booleans")
            if failure_field in row and row[failure_field] is not None and type(row[failure_field]) is not str:
                raise ValueError("annotation failure must be text or None")
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
    for pair_id, value in labels.items():
        if value is not None and (type(value) is not int or value not in (0, 1)):
            raise ValueError("labels must be 0, 1, or None")
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


def _label_agreement(rows: list[dict], family_ids: list[str]) -> dict:
    result = {}
    for family in family_ids:
        family_rows = [r for r in rows if r["familyId"] == family]
        reviewer_stats = {}
        for reviewer in ("annotation1", "annotation2"):
            attempted_rows = [r for r in family_rows if r.get(reviewer + "Attempted", reviewer in r or reviewer + "Failure" in r)]
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
                         if r.get("annotation1Attempted", "annotation1" in r or "annotation1Failure" in r)
                         and r.get("annotation2Attempted", "annotation2" in r or "annotation2Failure" in r)]
        disagreements = [r for r in pair_attempts if r.get("annotation1") in (0, 1)
                         and r.get("annotation2") in (0, 1) and r["annotation1"] != r["annotation2"]]
        resolved = sum((r.get("annotation1") == r.get("annotation2") and r.get("annotation1") in (0, 1))
                       or r.get("adjudicatedLabel") in (0, 1) for r in pair_attempts)
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
            "adjudicatedDisagreements": sum(r.get("adjudicatedLabel") in (0, 1) for r in disagreements),
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
                inference_policy: bool) -> tuple[dict, dict]:
    n = len(rows)
    ceiling = math.floor(fraction * n)
    phase = {"preparationSeconds": 0.0, "scoringSeconds": 0.0, "inferenceSeconds": 0.0,
             "rankingSeconds": 0.0, "verificationSeconds": 0.0,
             "serializationSeconds": 0.0}
    t0 = time.perf_counter()
    scores: dict[str, float | None] = {}
    probabilities: dict[str, float | None] = {}
    prepared: dict[str, Any] = {}
    for row in rows:
        candidate = _blind_row(row)
        if preparation is not None and inference_policy:
            start = time.perf_counter()
            prepared[row["pairId"]] = preparation(deepcopy(candidate))
            phase["preparationSeconds"] += time.perf_counter() - start
        else:
            # The rule baseline ranks directly from the request; do not charge
            # predictor-only feature preparation to its measured cost.
            prepared[row["pairId"]] = deepcopy(candidate["request"])
        scorer_candidate = deepcopy(candidate)
        scorer_prepared = deepcopy(prepared[row["pairId"]])
        start = time.perf_counter()
        raw = scorer(scorer_candidate, scorer_prepared)
        elapsed = time.perf_counter() - start
        phase["inferenceSeconds" if inference_policy else "scoringSeconds"] += elapsed
        start = time.perf_counter()
        scores[row["pairId"]], probabilities[row["pairId"]] = _prediction(raw)
        phase["scoringSeconds"] += time.perf_counter() - start
    start = time.perf_counter()
    selected = _select(rows, scores, ceiling)
    phase["rankingSeconds"] += time.perf_counter() - start
    verdicts = {}
    start = time.perf_counter()
    for row in selected:
        # Exactly one unchanged produce+verify call per selected pair.
        verdict = _default_verifier(row["request"])
        verdicts[row["pairId"]] = verdict
    phase["verificationSeconds"] += time.perf_counter() - start
    result = _metrics(rows, labels, selected, verdicts, sorted({r["familyId"] for r in rows}))
    abstentions = sum(score is None for score in scores.values())
    result["abstentions"] = abstentions
    result["unusedCalls"] = max(0, ceiling - len(selected))
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


def evaluate(inventory: Any, labels: Any, *, scorer: Callable[[dict, Any], Any],
             dataset_kind: str, preparation: Callable[[dict], Any] | None = None,
             training_inventory: Any = None, training_labels: Any = None,
             negative_control_scorer_factory: Callable[[list[dict]], Callable] | None = None,
             warmups: int = 3, repetitions: int = 20) -> dict:
    """Compare the baseline and supplied ranker on one synthetic holdout.

    ``scorer(row, prepared)`` sees only a sanitized pair identity and request,
    no label, family identity, partition, or annotation. It returns a raw
    numeric priority, ``None``/abstain, or ``{status, score, probability?}``.
    ``preparation(row)`` is timed each run and gets the same sanitized row.
    Without a preparation hook the inventory already contains requests, so
    source extraction is not measured. A valid negative control requires a
    factory fitted from seed-zero permuted train labels; holdout labels never
    enter the factory.
    """
    rows, checked_labels = _validate(inventory, labels, dataset_kind)
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
                            inference_policy=(name != "baseline"))
    samples: dict[str, dict[float, list[dict]]] = {
        name: {fraction: [] for fraction in (0.25, 0.5, 1.0)} for name, _ in policies}
    for rep in range(repetitions):
        order = policies if rep % 2 == 0 else policies[::-1]
        for name, policy_scorer in order:
            for fraction in (0.25, 0.5, 1.0):
                measured, _ = _run_policy(rows, checked_labels, scorer=policy_scorer,
                                          preparation=preparation, fraction=fraction,
                                          inference_policy=(name != "baseline"))
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

    negative_control: dict[str, Any]
    if negative_control_scorer_factory is None:
        negative_control = {"status": "unavailable",
                            "reason": "no scorer factory supplied to refit from permuted training labels",
                            "holdoutLabelsPermuted": False}
    else:
        if training_inventory is None or training_labels is None:
            raise ValueError("negative-control factory requires separate training inventory and labels")
        try:
            permuted_training = permute_training_labels(training_inventory, training_labels, seed=0)
        except NegativeControlUnavailable as exc:
            negative_control = {"status": "unavailable", "reason": str(exc),
                                "factoryRun": False, "holdoutLabelsPermuted": False}
        else:
            original_assignment = [training_labels[row["pairId"]] for row in training_inventory]
            permuted_assignment = [row["label"] for row in permuted_training]
            if original_assignment == permuted_assignment:
                raise NegativeControlUnavailable("permutation helper returned the unchanged training assignment")
            control_scorer = negative_control_scorer_factory(permuted_training)
            if not callable(control_scorer):
                raise ValueError("negative-control factory must return a scorer")
            control_run, _ = _run_policy(rows, checked_labels, scorer=control_scorer,
                                         preparation=preparation, fraction=0.5,
                                         inference_policy=True)
            negative_control = {
                "status": "available-synthetic-descriptive-only", "seed": 0,
                "method": "refit scorer via caller factory using train-only known utility labels permuted with seed 0",
                "budget": "50", "holdoutLabelsPermuted": False,
                "factoryReceivedHoldoutRowsOrLabels": False,
                "trainingAssignmentChanged": True,
                "classCountsPreserved": True,
                "trainingLabelCounts": {str(label): permuted_assignment.count(label)
                                        for label in (0, 1, None)},
                "metricsOnUnpermutedHoldoutLabels": control_run,
                "interpretation": "permuted-training-label negative-control candidate; synthetic only",
            }
    report = {
        "format": "m35-evaluation-report-v1", "sourceKind": "synthetic",
        "status": "synthetic-descriptive-only", "protocolApproval": "not-approved; P019-04 call/status mapping remains provisional",
        "policy": POLICY, "inventoryOrder": "caller-supplied stable order; tie breaks preserve it",
        "labelIsolation": "labels and annotations are separate and scorer/preparation hooks never receive them",
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
            "status": "predictor-only request-to-feature hook measured per repetition" if preparation is not None
                     else "not measured; inventory already contains a validated request",
            "sourceExtraction": "not measured; evaluator input is already an in-memory validated request",
            "limitation": "the hook can measure request-to-feature preparation, but source-to-request extraction is outside this evaluator",
        },
        "timingPhaseDefinitions": {
            "inferenceSeconds": "predictor scorer callback duration only",
            "scoringSeconds": "baseline priority callback plus score response normalization/validation; predictor callback time is excluded",
            "sourceExtraction": "excluded; evaluation begins with in-memory validated requests",
        },
        "probabilityNote": "A probability is an unvalidated scorer-supplied claim; no artifact/calibration provenance is checked. Brier and reliability are descriptive only.",
        "executionAuthorization": False,
    }
    report["reportSerializationSeconds"] = 0.0
    report["finalReportSerializationIncludedInPolicyTotals"] = False
    report["reportSerializationTimingNote"] = (
        "final report serialized with a zero placeholder for this self-referential duration; "
        "measured duration is filled afterward and excluded from policy timing"
    )
    start = time.perf_counter()
    json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False)
    report["reportSerializationSeconds"] = time.perf_counter() - start
    return report
