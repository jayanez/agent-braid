# SPDX-License-Identifier: AGPL-3.0-only
"""Comparison coverage, bounded additive recovery and full cost accounting."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from research.workload_lab.analysis import (
    METHODS, STAGES, additive_candidate, control_result, matched_coverage,
    measure, run_experiment, validate_manifest,
)
from research.workload_lab.evidence import explore, verify
from research.workload_lab.model import digest

ROOT = Path(__file__).resolve().parents[1]


def corpus():
    manifest = json.loads((ROOT / "examples/workload-lab/manifest.json").read_text())
    registration = json.loads((ROOT / "examples/workload-lab/registration.json").read_text())
    validate_manifest(manifest, registration)
    return manifest, registration


class WorkloadH2Tests(unittest.TestCase):
    def test_terminal_rule_preserves_raw_differences_and_denies_runtime(self):
        manifest, _ = corpus()
        recovered = 0
        for fixture in manifest["fixtures"]:
            if not fixture["h2"]:
                continue
            with self.subTest(fixture=fixture["id"]):
                report = explore(fixture["request"])
                result = additive_candidate(fixture["request"], report)
                self.assertEqual(control_result(fixture, report)["status"], "pass")
                self.assertEqual(result["terminalCandidate"], fixture["invariant"]["expected"])
                self.assertIs(result["executionAuthorization"], False)
                self.assertEqual(result["runtimeSafety"], "unknown")
                self.assertEqual(result["contextualEquivalence"], "unknown")
                if fixture["id"] == "h2-event-exclusion":
                    self.assertIn("events", result["rawMismatchDimensions"])
                    self.assertTrue(report["traceSafety"]["eventOrderMismatch"])
                if result["terminalCandidate"]:
                    self.assertEqual(report["comparison"]["verdict"], "terminal-projection-match")
                    recovered += int("results" in result["rawMismatchDimensions"])
        self.assertGreaterEqual(recovered, 1)

    def test_missing_oracle_and_changed_observation_abstain(self):
        manifest, _ = corpus()
        request = copy.deepcopy(next(f for f in manifest["fixtures"] if f["id"] == "h2-shared-additions")["request"])
        request["caps"]["paths"] = 1
        self.assertEqual(additive_candidate(request, explore(request))["exclusion"], "incomplete-oracle")
        request["caps"]["paths"] = 20000
        request["observation"] = {"mode": "exact"}
        self.assertEqual(additive_candidate(request, explore(request))["exclusion"], "observation-outside-class")


class WorkloadComparisonTests(unittest.TestCase):
    def test_tamper_coverage_and_cost_accounting(self):
        manifest, _ = corpus()
        request = next(f for f in manifest["fixtures"] if f["id"] == "h2-shared-additions")["request"]
        runs = [measure(request, method) for method in METHODS]
        self.assertTrue(matched_coverage(runs))
        for run in runs:
            costs = run["costNanoseconds"]
            self.assertEqual(set(costs), {*STAGES, "totalWall"})
            self.assertGreaterEqual(costs["totalWall"], sum(costs[name] for name in STAGES))
            self.assertTrue(all(type(value) is int and value >= 0 for value in costs.values()))
            self.assertGreater(run["peakRetainedObjects"], len(run["report"]["paths"]))
            self.assertEqual(run["verification"]["status"], "verified")
        altered = copy.deepcopy(runs)
        altered[0]["coverage"]["completedPaths"] -= 1
        self.assertFalse(matched_coverage(altered))
        altered = copy.deepcopy(runs)
        altered[0]["requestHash"] = "0" * 64
        self.assertFalse(matched_coverage(altered))
        for mutate in (lambda r: r["paths"].pop(), lambda r: r["paths"][0]["branches"].__setitem__(0, "error"), lambda r: r["paths"][0]["steps"].pop(), lambda r: r.update(requestHash="0" * 64)):
            report = copy.deepcopy(runs[0]["report"])
            mutate(report)
            self.assertEqual(verify(report)["status"], "rejected")

    def test_registered_repetitions_and_failures_remain_accounted(self):
        manifest, registration = corpus()
        manifest["fixtures"] = [next(f for f in manifest["fixtures"] if f["id"] == "h2-shared-additions")]
        registration.update(manifestHash=digest(manifest), fixtureCount=1)
        report = run_experiment(manifest, registration, command=["unit-test-local"])
        fixture = report["fixtures"][0]
        self.assertTrue(fixture["matchedCompleteCoverage"])
        self.assertEqual(fixture["warmupsCompleted"], {m: 3 for m in METHODS})
        self.assertTrue(all(len(fixture["samples"][m]) == 20 for m in METHODS))
        orders = {tuple(s["methodOrder"]) for method in METHODS for s in fixture["samples"][method]}
        self.assertEqual(len(orders), len(METHODS))
        self.assertEqual(report["accounting"]["recoveredTerminalCandidates"], 1)
        self.assertIn(report["feasibility"]["status"], ("positive", "negative"))
        self.assertEqual(report["scientificReview"], "pending")
        self.assertIs(report["executionAuthorization"], False)
        actual_measure = measure
        calls = 0
        def fail_once(request, method):
            nonlocal calls
            calls += 1
            if calls == 5:
                raise ValueError("registered failure retained")
            return actual_measure(request, method)
        with patch("research.workload_lab.analysis.measure", side_effect=fail_once):
            failed = run_experiment(manifest, registration)
        self.assertEqual(calls, 92)
        self.assertEqual(failed["accounting"]["failedRepetitions"], 1)
        self.assertEqual(failed["feasibility"]["status"], "inconclusive")
        self.assertFalse(failed["fixtures"][0]["matchedCompleteCoverage"])


if __name__ == "__main__":
    unittest.main()
