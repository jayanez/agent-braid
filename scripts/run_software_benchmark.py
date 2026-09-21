#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the synthetic M1 classifier benchmark; no tools or agents are executed."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.analysis import analyze


BENCHMARK = ROOT / "examples/analysis/software-benchmark.json"


def _aim(identifier, definition, effects, coverage, dependencies=(), read_version=None):
    reads = {} if read_version is None else {effects[0][1]: read_version}
    return {
        "aimVersion": "0.2.0-draft",
        "instanceId": identifier,
        "attemptId": identifier + "-attempt-1",
        "definition": {
            "id": definition,
            "digest": "sha256:" + ("1" if identifier == "left" else "2") * 64,
        },
        "inputDigest": "sha256:" + ("a" if identifier == "left" else "b") * 64,
        "dependencies": list(dependencies),
        "readVersions": reads,
        "effects": {
            "declared": [{"kind": kind, "resource": resource} for kind, resource in effects],
            "inferred": [],
            "observed": [],
            "coverage": {
                "status": coverage,
                "domain": "synthetic software benchmark",
                "method": "fixture declaration",
            },
        },
        "evidence": [{
            "property": "independence",
            "method": "declared",
            "domain": "synthetic software benchmark",
            "assumptions": [],
            "observationContract": "fixture-specific",
            "executionContract": "no execution; analysis only",
            "assuranceClass": 0,
        }],
    }


def run(path=BENCHMARK):
    benchmark = json.loads(path.read_text(encoding="utf-8"))
    results = []
    false_safe = 0
    for scenario in benchmark["scenarios"]:
        left, right = scenario["left"], scenario["right"]
        records = [
            _aim("left", scenario["family"] + "-left", left["effects"], left["coverage"],
                 read_version=left.get("readVersion")),
            _aim("right", scenario["family"] + "-right", right["effects"], right["coverage"],
                 dependencies=("left",) if right.get("dependsOnLeft") else (),
                 read_version=right.get("readVersion")),
        ]
        interaction = analyze(records)["interactions"][0]
        actual = interaction["classification"]
        if actual == "independent-candidate" and scenario["expected"] != actual:
            false_safe += 1
        if actual != scenario["expected"]:
            raise AssertionError(f"{scenario['id']}: expected {scenario['expected']}, got {actual}")
        required = scenario.get("requiredConstraint")
        if required and required not in interaction["constraints"]:
            raise AssertionError(f"{scenario['id']}: missing constraint {required}")
        result = {"id": scenario["id"], "family": scenario["family"],
                  "expected": scenario["expected"], "actual": actual}
        if required:
            result["requiredConstraint"] = required
            result["conditionEnforcement"] = "required-at-use"
        results.append(result)
    total = len(results)
    unknown = sum(item["actual"] == "unknown" for item in results)
    independent = sum(item["actual"] == "independent-candidate" for item in results)
    expected_independent = sum(item["expected"] == "independent-candidate" for item in results)
    return {
        "benchmarkVersion": benchmark["benchmarkVersion"],
        "scenarioCount": total,
        "falseSafeCount": false_safe,
        "classificationAgreement": total,
        "unknownRate": unknown / total,
        "candidateRate": independent / total,
        "classificationCoverage": len(results) / total,
        "falseSerializationCount": expected_independent - independent,
        "conditionBoundScenarioCount": sum(
            item.get("conditionEnforcement") == "required-at-use" for item in results
        ),
        "analysisCost": {"unit": "pair evaluations", "value": total},
        "baselineComparisons": benchmark["baselineComparisons"],
        "results": results,
        "limits": benchmark["limits"],
    }


def main():
    print(json.dumps(run(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
