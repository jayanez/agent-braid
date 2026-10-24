# SPDX-License-Identifier: AGPL-3.0-only
"""Comparison coverage, bounded additive recovery and full cost accounting."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from research.workload_lab.analysis import (
    METHODS, STAGES, additive_candidate, control_result, matched_coverage,
    measure, median_upper_bound, run_experiment, validate_manifest,
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
        orders = {s["orderOffset"] for method in METHODS for s in fixture["samples"][method]}
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

    def test_unstable_deterministic_field_prevents_matched_coverage(self):
        manifest, registration = corpus()
        manifest["fixtures"] = [next(f for f in manifest["fixtures"] if f["id"] == "h2-shared-additions")]
        registration.update(manifestHash=digest(manifest), fixtureCount=1)
        actual_measure = measure
        calls = 0
        def drift(request, method):
            nonlocal calls
            calls += 1
            result = actual_measure(request, method)
            if calls == 30:
                result["observation"] = {**result["observation"], "terminalValuesMatch": not result["observation"]["terminalValuesMatch"]}
            return result
        with patch("research.workload_lab.analysis.measure", side_effect=drift):
            report = run_experiment(manifest, registration)
        self.assertFalse(report["fixtures"][0]["matchedCompleteCoverage"])
        self.assertEqual(report["feasibility"]["status"], "inconclusive")

    def run_with_costs(self, rule_stage, rule_total, oracle_total):
        manifest, registration = corpus()
        manifest["fixtures"] = [next(f for f in manifest["fixtures"] if f["id"] == "h2-shared-additions")]
        registration.update(manifestHash=digest(manifest), fixtureCount=1)
        actual_measure = measure
        def fake(request, method):
            result = actual_measure(request, method)
            costs = dict(result["costNanoseconds"])
            if method == "additive-terminal":
                costs.update(rule=rule_stage, totalWall=rule_total)
            elif method == "exhaustive-replay":
                costs.update(totalWall=oracle_total)
            result["costNanoseconds"] = costs
            return result
        with patch("research.workload_lab.analysis.measure", side_effect=fake):
            return run_experiment(manifest, registration)

    def test_rule_incremental_cost_margin_is_inclusive(self):
        # Registered margin: 50,000 ppm of the paired exhaustive-replay total.
        for rule_stage, status in ((50_000, "positive"), (50_001, "negative")):
            with self.subTest(rule_stage=rule_stage):
                report = self.run_with_costs(rule_stage, 1_050_000, 1_000_000)
                cost = report["feasibility"]["ruleIncrementalCostPpm"]
                self.assertEqual((cost["samples"], cost["marginAtMost"]), (20, 50_000))
                self.assertEqual(cost["upper95"], rule_stage)
                self.assertEqual(report["feasibility"]["costThresholdMet"], status == "positive")
                self.assertEqual(report["feasibility"]["status"], status)

    def test_whole_cost_noise_no_longer_decides_the_verdict(self):
        # A rule run slower overall than the oracle (timer noise, shared replay)
        # does not flip the verdict; only the rule's own paired stage counts.
        for rule_total in (900_000, 1_000_000, 1_200_000):
            with self.subTest(rule_total=rule_total):
                report = self.run_with_costs(1_000, rule_total, 1_000_000)
                self.assertEqual(report["feasibility"]["status"], "positive")

    def test_median_upper_bound_is_an_exact_order_statistic(self):
        self.assertEqual(median_upper_bound(range(20, 0, -1)), 15)
        self.assertEqual(median_upper_bound([7] * 200), 7)
        self.assertIsNone(median_upper_bound([1, 2, 3, 4]))
        self.assertIsNone(median_upper_bound([]))


EVIDENCE = ROOT / "specs/024-effectful-workload-lab/evidence/comparison-20261024.json"


def evidence_problems(evidence, manifest, registration):
    """List deterministic ways a captured experiment departs from the frozen corpus."""
    problems = []
    if evidence["registration"] != registration or evidence["protocol"] != manifest["protocol"]:
        problems.append("registration")
    if [r["id"] for r in evidence["fixtures"]] != [f["id"] for f in manifest["fixtures"]]:
        problems.append("fixtures")
    for result, fixture in zip(evidence["fixtures"], manifest["fixtures"]):
        if result["requestHash"] != fixture["requestHash"] or result["oracleDigest"] != digest(explore(fixture["request"])):
            problems.append("oracle " + fixture["id"])
        if not result["matchedCompleteCoverage"] or result["failures"] or result["control"]["status"] != "pass":
            problems.append("coverage " + fixture["id"])
        if any(not shared["coverage"]["complete"] or shared["requestHash"] != fixture["requestHash"]
               for shared in result["deterministicByMethod"].values()):
            problems.append("deterministic " + fixture["id"])
        if any(len(result["samples"][m]) != 20 or result["warmupsCompleted"][m] != 3 for m in METHODS):
            problems.append("repetitions " + fixture["id"])
    accounting = evidence["accounting"]
    if accounting["falseTerminalCandidates"] or accounting["recoveredTerminalCandidates"] != sum(
            bool(r["h2"] and r["h2"].get("recoveredFromExactResourceOverlap")) for r in evidence["fixtures"]):
        problems.append("accounting")
    if evidence["feasibility"]["ruleIncrementalCostPpm"]["samples"] != 200:
        problems.append("samples")
    if evidence["executionAuthorization"] is not False or evidence["scientificReview"] != "pending":
        problems.append("authority")
    return problems


class WorkloadCapturedEvidenceTests(unittest.TestCase):
    def test_committed_comparison_matches_frozen_corpus_and_detects_tampering(self):
        manifest, registration = corpus()
        evidence = json.loads(EVIDENCE.read_text())
        self.assertEqual(evidence_problems(evidence, manifest, registration), [])
        self.assertEqual(evidence["accounting"]["registeredFixtures"], 17)
        for mutate in (
            lambda e: e["fixtures"][0].__setitem__("oracleDigest", "0" * 64),
            lambda e: e["fixtures"][0]["deterministicByMethod"]["declared-effects"]["coverage"].update(complete=False),
            lambda e: e["fixtures"][0]["samples"]["declared-effects"].pop(),
            lambda e: e["accounting"].__setitem__("falseTerminalCandidates", 1),
            lambda e: e.__setitem__("executionAuthorization", True),
            lambda e: e["registration"].__setitem__("fixtureCount", 16),
        ):
            changed = copy.deepcopy(evidence)
            mutate(changed)
            self.assertNotEqual(evidence_problems(changed, manifest, registration), [])


if __name__ == "__main__":
    unittest.main()
