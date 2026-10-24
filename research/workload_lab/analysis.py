# SPDX-License-Identifier: AGPL-3.0-only
"""Frozen synthetic controls and whole-cost advisory comparisons for SPEC-024.

Every method retains the complete oracle domain. No classification grants an
execution right or promotes terminal values to contextual equivalence.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
import statistics
import time
from itertools import combinations
from math import comb
from pathlib import Path

from .model import canonical, declared_effects, digest, footprint, validate

METHODS = ("conservative-all-orders", "declared-effects", "additive-terminal", "exhaustive-replay")
STAGES = ("setup", "footprintValidation", "classification", "replay", "observation", "comparison", "rule", "serialization")
# Registered H2 cost criterion: the additive rule's own stage, paired with the
# exhaustive-replay total of the same fixture and repetition, as parts per million.
RULE_INCREMENTAL_COST = {
    "numerator": "additive-terminal rule stage", "denominator": "exhaustive-replay totalWall",
    "pairing": "same-fixture-same-repetition", "population": "matched-complete-h2-fixtures",
    "unit": "ppm", "bound": "order-statistic-one-sided-95-upper-median", "marginAtMostPpm": 50000,
}


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def validate_manifest(manifest, registration):
    """Check the independently frozen manifest/protocol before any measurement."""
    if set(manifest) != {"format", "protocol", "fixtures"} or manifest["format"] != "effectful-workload-manifest-v1":
        raise ValueError("invalid manifest")
    if set(registration) != {"format", "manifestHash", "protocolHash", "fixtureCount", "executionAuthorization"}:
        raise ValueError("invalid registration")
    if registration["format"] != "effectful-workload-registration-v1" or registration["executionAuthorization"] is not False:
        raise ValueError("invalid registration authority")
    protocol = manifest["protocol"]
    expected = {
        "format": "effectful-workload-protocol-v2", "methods": list(METHODS),
        "warmups": 3, "repetitions": 20,
        "order": "rotate-methods-by-fixture-and-repetition",
        "threshold": {"minimumRecoveredTerminalCandidates": 1, "ruleIncrementalCost": RULE_INCREMENTAL_COST},
        "coverage": "identical-complete-or-inconclusive", "costBoundary": [*STAGES, "totalWall"],
        "claims": {"contextualEquivalence": "unknown", "runtimeSafety": "unknown", "executionAuthorization": False},
    }
    if protocol != expected or registration["protocolHash"] != digest(protocol) or registration["manifestHash"] != digest(manifest):
        raise ValueError("frozen manifest/protocol hash mismatch")
    fixtures = manifest["fixtures"]
    if not isinstance(fixtures, list) or not fixtures or registration["fixtureCount"] != len(fixtures):
        raise ValueError("invalid frozen fixture count")
    names = set()
    for fixture in fixtures:
        if set(fixture) != {"id", "request", "requestHash", "invariant", "h2"} or not isinstance(fixture["id"], str) or fixture["id"] in names or type(fixture["h2"]) is not bool:
            raise ValueError("invalid fixture identity")
        names.add(fixture["id"])
        validate(fixture["request"])
        if fixture["requestHash"] != digest(fixture["request"]):
            raise ValueError("frozen request hash mismatch")
        _validate_invariant(fixture["invariant"])
    return manifest


def _validate_invariant(invariant):
    fields = {
        "state-below": {"kind", "resource", "value"},
        "sum-below": {"kind", "resources", "value"},
        "state-pair": {"kind", "left", "leftValue", "right", "rightValue"},
        "event-count": {"kind", "count", "duplicate"},
        "unknown-shared-resource": {"kind", "resource"},
        "all-state": {"kind", "values"},
        "terminal-candidate": {"kind", "expected", "returnedValuesDiffer"},
    }
    if not isinstance(invariant, dict):
        raise ValueError("invalid expected invariant")
    kind = invariant.get("kind")
    if kind == "terminal-candidate" and invariant.get("expected") is False:
        expected = {"kind", "expected", "reason"}
    else:
        expected = fields.get(kind)
    if expected is None or set(invariant) != expected:
        raise ValueError("unknown expected invariant")


def _closure(operations, name):
    by_id = {op["id"]: op for op in operations}
    result = set()
    def visit(current):
        for dependency in by_id[current]["dependencies"]:
            if dependency not in result:
                result.add(dependency)
                visit(dependency)
    visit(name)
    return result


def classify(request, method, declarations=None):
    """Classify pairs conservatively, preserving unknowns and dependencies."""
    if method not in METHODS:
        raise ValueError("unknown method")
    declarations = declarations or [declared_effects(request, op) for op in request["operations"]]
    operations = request["operations"]
    declared = dict(zip((op["id"] for op in operations), declarations))
    closures = {op["id"]: _closure(operations, op["id"]) for op in operations}
    pairs = []
    for a, b in combinations(operations, 2):
        aid, bid = a["id"], b["id"]
        da, db = declared[aid], declared[bid]
        if aid in closures[bid] or bid in closures[aid]:
            verdict = "dependency-ordered"
        elif not da["known"] or not db["known"]:
            verdict = "unknown-effects"
        else:
            fa, fb = footprint(request, a), footprint(request, b)
            if method == "declared-effects":
                fa = {key: set(da[key]) for key in ("reads", "writes", "emits")}
                fb = {key: set(db[key]) for key in ("reads", "writes", "emits")}
                overlap = bool(fa["writes"] & (fb["reads"] | fb["writes"]) or fb["writes"] & fa["reads"])
            else:
                overlap = bool(set.union(*fa.values()) & set.union(*fb.values()))
            # Chronological events can differ even on different resources.
            if fa["emits"] or fb["emits"]:
                verdict = "event-order-sensitive"
            else:
                verdict = "resource-conflict" if overlap else "disjoint-candidate"
        pairs.append({"operations": [aid, bid], "classification": verdict})
    return {"pairs": pairs, "unknownOperations": [op["id"] for op in operations if not declared[op["id"]]["known"]], "executionAuthorization": False}


def terminal_values(report):
    """Determine full terminal value agreement, never dropping raw dimensions."""
    paths = report["paths"]
    complete = report["coverage"]["complete"] and bool(paths)
    success = complete and all(path["configuration"]["outcome"] == "success" for path in paths)
    states = [path["configuration"]["state"] for path in paths]
    match = success and all(state == states[0] for state in states)
    return {"complete": complete, "allSuccessful": success, "terminalValuesMatch": match,
            "rawMismatchDimensions": list(report["comparison"]["mismatches"]),
            "contextualEquivalence": "unknown", "runtimeSafety": "unknown", "executionAuthorization": False}


def additive_candidate(request, report, declarations=None):
    """Apply the registered bounded rule, then check every oracle intermediate."""
    ops = request["operations"]
    declarations = declarations or [declared_effects(request, op) for op in ops]
    reason = None
    if not 2 <= len(ops) <= 4 or any(op["kind"] != "add-constant" for op in ops):
        reason = "outside-additive-class"
    elif any("requiredVersion" in op for op in ops):
        reason = "version-precondition"
    elif any(not declaration["known"] for declaration in declarations):
        reason = "unknown-effects"
    elif any(op["outcomes"] != ["success"] for op in ops):
        reason = "failure-branches"
    elif request["observation"] != {"mode": "selected-values", "resources": sorted(request["initial"]["state"])}:
        reason = "observation-outside-class"
    elif not report["coverage"]["complete"]:
        reason = "incomplete-oracle"
    elif any(path["configuration"]["outcome"] != "success" for path in report["paths"]):
        reason = "non-success-path"
    elif not terminal_values(report)["terminalValuesMatch"]:
        reason = "terminal-values-diverge"
    # The complete oracle must retain all intermediate values; checking it is
    # charged to each rule run, and no overflow path can become a candidate.
    # Defensive: `step` turns overflow into an error path, already excluded as
    # non-success above. Kept so the registered rule cost is unchanged.
    elif any(abs(value) > 2**63 - 1 for path in report["paths"] for step in path["steps"] for side in ("before", "after") for value in step[side]["state"].values()):
        reason = "intermediate-overflow"
    return {"terminalCandidate": reason is None, "exclusion": reason,
            "rawMismatchDimensions": list(report["comparison"]["mismatches"]),
            "claim": "finite-terminal-values-only", "contextualEquivalence": "unknown",
            "runtimeSafety": "unknown", "executionAuthorization": False}


def control_result(fixture, report):
    """Evaluate authored invariants rather than deriving expectations from replay."""
    expected = fixture["invariant"]
    kind = expected["kind"]
    configs = [path["configuration"] for path in report["paths"]]
    complete = report["coverage"]["complete"]
    details = {}
    if kind == "state-below":
        witnessed = any(c["state"][expected["resource"]] < expected["value"] for c in configs)
    elif kind == "sum-below":
        witnessed = any(sum(c["state"][name] for name in expected["resources"]) < expected["value"] for c in configs)
    elif kind == "state-pair":
        witnessed = any(c["state"][expected["left"]] == expected["leftValue"] and c["state"][expected["right"]] == expected["rightValue"] for c in configs)
    elif kind == "event-count":
        duplicate = any(len({(e["resource"], e["name"], e["idempotencyKey"]) for e in c["events"]}) < len(c["events"]) for c in configs)
        witnessed = bool(configs) and all(len(c["events"]) == expected["count"] for c in configs) and duplicate == expected["duplicate"]
    elif kind == "unknown-shared-resource":
        classification = classify(fixture["request"], "conservative-all-orders")
        footprints = [footprint(fixture["request"], op) for op in fixture["request"]["operations"]]
        witnessed = bool(classification["unknownOperations"]) and all(expected["resource"] in set.union(*f.values()) for f in footprints)
    elif kind == "all-state":
        witnessed = bool(configs) and all(c["state"] == expected["values"] for c in configs)
    else:
        details = additive_candidate(fixture["request"], report)
        witnessed = details["terminalCandidate"] == expected["expected"]
        if expected["expected"]:
            witnessed &= ("results" in details["rawMismatchDimensions"]) == expected["returnedValuesDiffer"]
        else:
            witnessed &= details["exclusion"] == expected["reason"]
    return {"status": "pass" if complete and witnessed else "inconclusive" if not complete else "fail",
            "expected": expected, "details": details, "executionAuthorization": False}


def _retained_objects(*roots):
    seen = set()
    def visit(value):
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, dict):
            for key, item in value.items():
                visit(key)
                visit(item)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                visit(item)
    for root in roots:
        visit(root)
    return len(seen)


def measure(request, method):
    """Measure every required stage, including complete replay for every method."""
    from .evidence import explore, verify
    start = time.perf_counter_ns()
    stages = {}
    checkpoint = start
    def stage(name):
        nonlocal checkpoint
        now = time.perf_counter_ns()
        stages[name] = now - checkpoint
        checkpoint = now
    encoded = canonical(request)
    parsed = json.loads(encoded)
    validate(parsed)
    stage("setup")
    declarations = [declared_effects(parsed, op) for op in parsed["operations"]]
    stage("footprintValidation")
    classification = classify(parsed, method, declarations)
    stage("classification")
    report = explore(parsed)
    stage("replay")
    observed = terminal_values(report)
    stage("observation")
    # Independent replay verification and candidate checking are never excluded
    # from a favorable method's cost boundary.
    verification = verify(report)
    if verification.get("status") != "verified":
        raise ValueError("oracle replay verification rejected")
    stage("comparison")
    rule = additive_candidate(parsed, report, declarations) if method == "additive-terminal" else None
    stage("rule")
    comparison = {"classification": classification, "observation": observed, "rule": rule, "verification": verification}
    serialized = _json({"request": parsed, "report": report, "comparison": comparison})
    retained = _retained_objects(parsed, encoded, declarations, classification, report, observed, verification, rule, comparison, serialized)
    stage("serialization")
    total = time.perf_counter_ns() - start
    return {"costNanoseconds": {**stages, "totalWall": total}, "peakRetainedObjects": retained,
            "retainedObjectMeasurement": "peak retained analysis-report graph at serialization; excludes transient verifier and allocator/RSS peaks",
            "serializedBytes": len(serialized), "coverage": report["coverage"],
            "requestHash": report["requestHash"], "sourceBindings": report["sourceBindings"],
            "observation": observed, "classification": classification, "rule": rule,
            "verification": verification, "report": report, "executionAuthorization": False}


def matched_coverage(runs):
    """Fail closed on any domain, observation, source or coverage difference."""
    if not runs:
        return False
    first = runs[0]
    keys = ("requestHash", "sourceBindings", "coverage")
    return all(run["coverage"]["complete"] and all(run[key] == first[key] for key in keys) for run in runs)


def median_upper_bound(values):
    """Distribution-free one-sided 95% upper bound for the median, or None.

    Returns the k-th order statistic for the smallest k with
    P(Binomial(n, 1/2) <= k - 1) >= 0.95, in exact integer arithmetic.
    """
    ordered = sorted(values)
    n = len(ordered)
    cumulative = 0
    for k in range(1, n + 1):
        cumulative += comb(n, k - 1)
        if 20 * cumulative >= 19 * 2**n:
            return ordered[k - 1]
    return None


SAMPLE_KEYS = ("repetition", "orderOffset", "peakRetainedObjects", "serializedBytes")
COST_ORDER = [*STAGES, "totalWall"]
# "orderOffset" rotates METHODS: order = METHODS[offset:] + METHODS[:offset].
DETERMINISTIC_KEYS = ("requestHash", "sourceBindings", "coverage", "observation", "classification", "rule", "verification",
                      "retainedObjectMeasurement")


def _compact(samples):
    """Keep per-sample costs; store each deterministic field once if every sample agrees."""
    shared, stable = {}, True
    for method, entries in samples.items():
        if entries:
            first = {key: entries[0][key] for key in DETERMINISTIC_KEYS}
            stable &= all(all(entry[key] == first[key] for key in DETERMINISTIC_KEYS) for entry in entries)
            shared[method] = first
    return shared, stable


def run_experiment(manifest, registration, command=None):
    """Run the preregistered local protocol; negative outcomes are valid results."""
    validate_manifest(manifest, registration)
    results = []
    recovered = false_candidates = exclusions = 0
    rule_costs, oracle_costs, paired_ppm = [], [], []
    for index, fixture in enumerate(manifest["fixtures"]):
        samples = {method: [] for method in METHODS}
        warmups = {method: 0 for method in METHODS}
        failures = []
        all_runs = []
        oracle = None
        for repetition in range(-3, 20):
            offset = (index + repetition + 3) % len(METHODS)
            order = METHODS[offset:] + METHODS[:offset]
            for method in order:
                attempt_start = time.perf_counter_ns()
                try:
                    measured = measure(fixture["request"], method)
                    all_runs.append({key: measured[key] for key in ("requestHash", "sourceBindings", "coverage")})
                    oracle = measured["report"]
                    entry = {key: value for key, value in measured.items() if key != "report"}
                    entry["repetition"] = repetition
                    entry["orderOffset"] = offset
                    if repetition < 0:
                        warmups[method] += 1
                    else:
                        samples[method].append(entry)
                except (ValueError, TypeError, KeyError, OverflowError, OSError, RecursionError) as exc:
                    # Preserve failed method/repetition in accounting; no retries,
                    # reselection or removal from the feasibility assessment.
                    failures.append({"method": method, "repetition": repetition, "error": str(exc), "type": type(exc).__name__,
                                     "totalWallNanoseconds": time.perf_counter_ns() - attempt_start,
                                     "stageAccounting": "incomplete-failed-attempt", "methodOrder": list(order)})
        shared, stable = _compact(samples)
        matched = (not failures and stable and matched_coverage(all_runs)
                   and all(len(samples[m]) == 20 and warmups[m] == 3 for m in METHODS))
        control = control_result(fixture, oracle) if oracle is not None else {"status": "inconclusive", "executionAuthorization": False}
        h2 = None
        if fixture["h2"] and oracle is not None:
            h2 = additive_candidate(fixture["request"], oracle)
            baseline = classify(fixture["request"], "conservative-all-orders")
            baseline_conflict = any(pair["classification"] == "resource-conflict" for pair in baseline["pairs"])
            recovered_here = matched and h2["terminalCandidate"] and baseline_conflict
            recovered += int(recovered_here)
            false_candidates += int(h2["terminalCandidate"] and not terminal_values(oracle)["terminalValuesMatch"])
            exclusions += int(not h2["terminalCandidate"])
            h2["recoveredFromExactResourceOverlap"] = recovered_here
            if matched:
                rule_costs.extend(s["costNanoseconds"]["totalWall"] for s in samples["additive-terminal"])
                oracle_costs.extend(s["costNanoseconds"]["totalWall"] for s in samples["exhaustive-replay"])
                oracle_by_repetition = {s["repetition"]: s["costNanoseconds"]["totalWall"]
                                        for s in samples["exhaustive-replay"]}
                paired_ppm.extend(s["costNanoseconds"]["rule"] * 1_000_000 // max(oracle_by_repetition[s["repetition"]], 1)
                                  for s in samples["additive-terminal"])
        results.append({"id": fixture["id"], "requestHash": fixture["requestHash"], "matchedCompleteCoverage": matched,
                        "warmupsCompleted": warmups, "deterministicByMethod": shared,
                        "samples": {m: [{**{key: entry[key] for key in SAMPLE_KEYS}, "costs": [entry["costNanoseconds"][name] for name in COST_ORDER]}
                                        for entry in entries] for m, entries in samples.items()},
                        "failures": failures, "control": control, "h2": h2,
                        "oracleDigest": digest(oracle) if oracle is not None else None, "executionAuthorization": False})
    complete = all(result["matchedCompleteCoverage"] and result["control"]["status"] == "pass" for result in results)
    rule_median = statistics.median(rule_costs) if rule_costs else None
    oracle_median = statistics.median(oracle_costs) if oracle_costs else None
    upper = median_upper_bound(paired_ppm)
    threshold = upper is not None and upper <= RULE_INCREMENTAL_COST["marginAtMostPpm"]
    feasibility = "inconclusive" if not complete or false_candidates else "positive" if recovered >= 1 and threshold else "negative"
    source_files = (Path(__file__), Path(__file__).parents[2] / "scripts/run_effectful_workload_experiment.py")
    return {"format": "effectful-workload-experiment-v1", "registration": registration, "protocol": manifest["protocol"],
            "environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                            "platform": sys.platform, "machine": platform.machine(), "command": command},
            "toolBindings": {str(path.relative_to(Path(__file__).parents[2])): hashlib.sha256(path.read_bytes()).hexdigest() for path in source_files},
            "fixtures": results, "accounting": {"registeredFixtures": len(results), "registeredH2Fixtures": sum(f["h2"] for f in manifest["fixtures"]),
                "eligibleH2Fixtures": sum(bool(r["h2"] and r["h2"]["terminalCandidate"]) for r in results),
                "excludedH2Fixtures": exclusions, "recoveredTerminalCandidates": recovered, "falseTerminalCandidates": false_candidates,
                "matchedCompleteFixtures": sum(r["matchedCompleteCoverage"] for r in results),
                "failedRepetitions": sum(len(r["failures"]) for r in results)},
            "feasibility": {"status": feasibility, "medianRuleWholeCostNanoseconds": rule_median,
                            "medianOracleWholeCostNanoseconds": oracle_median,
                            "ruleIncrementalCostPpm": {"samples": len(paired_ppm),
                                                       "median": statistics.median(paired_ppm) if paired_ppm else None,
                                                       "upper95": upper,
                                                       "marginAtMost": RULE_INCREMENTAL_COST["marginAtMostPpm"]},
                            "costThresholdMet": threshold,
                            "scope": "descriptive frozen synthetic corpus only"},
            "interpretation": {"registeredRuns": 1, "costOrder": COST_ORDER, "costUnit": "nanoseconds", "timings": "machine-bound; see environment",
                               "feasibilityIsUtilityOrGeneralClaim": False,
                               "oracle": "per-fixture report omitted; oracleDigest is the canonical digest of explore(request), recomputable"},
            "contextualEquivalence": "unknown", "runtimeSafety": "unknown", "scientificReview": "pending", "executionAuthorization": False}
