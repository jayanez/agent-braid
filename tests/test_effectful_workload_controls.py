# SPDX-License-Identifier: AGPL-3.0-only
"""Independent authored race witnesses and finite prevention controls."""
import copy
import json
import unittest
from pathlib import Path

from research.workload_lab.analysis import classify, control_result, validate_manifest
from research.workload_lab.controls import control_evidence
from research.workload_lab.evidence import explore

ROOT = Path(__file__).resolve().parents[1]


def corpus():
    manifest = json.loads((ROOT / "examples/workload-lab/manifest.json").read_text())
    registration = json.loads((ROOT / "examples/workload-lab/registration.json").read_text())
    validate_manifest(manifest, registration)
    return manifest, registration


class WorkloadControlsTests(unittest.TestCase):
    def test_named_races_and_hidden_effects(self):
        manifest, _ = corpus()
        found = set()
        for fixture in manifest["fixtures"]:
            if fixture["h2"]:
                continue
            with self.subTest(fixture=fixture["id"]):
                report = explore(fixture["request"])
                self.assertTrue(report["coverage"]["complete"])
                self.assertEqual(control_result(fixture, report)["status"], "pass")
                self.assertIs(report["executionAuthorization"], False)
                found.add(fixture["id"])
        self.assertEqual(found, {"lost-update", "write-skew", "configuration-stale-read", "duplicate-events", "idempotent-events", "alias-hidden-effects", "disjoint-positive"})

    def test_expected_invariants_are_frozen_independently(self):
        manifest, registration = corpus()
        changed = copy.deepcopy(manifest)
        changed["fixtures"][0]["invariant"]["value"] = 100
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_manifest(changed, registration)
        changed = copy.deepcopy(manifest)
        changed["fixtures"][0]["request"]["caps"]["paths"] = 1
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_manifest(changed, registration)
        changed = copy.deepcopy(manifest)
        changed["protocol"]["repetitions"] = 1
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_manifest(changed, registration)

    def test_event_order_and_hidden_alias_cannot_be_independent(self):
        manifest, _ = corpus()
        hidden = next(f for f in manifest["fixtures"] if f["id"] == "alias-hidden-effects")
        for method in ("conservative-all-orders", "declared-effects"):
            result = classify(hidden["request"], method)
            self.assertEqual(result["pairs"][0]["classification"], "unknown-effects")
            self.assertEqual(result["unknownOperations"], ["b"])
        known_alias = copy.deepcopy(hidden["request"])
        known_alias["operations"][1]["effects"] = {"complete": True, "reads": ["x"], "writes": ["x"], "emits": []}
        self.assertEqual(classify(known_alias, "declared-effects")["pairs"][0]["classification"], "resource-conflict")
        events = copy.deepcopy(next(f for f in manifest["fixtures"] if f["id"] == "duplicate-events")["request"])
        events["initial"]["state"]["y"] = 1
        events["initial"]["versions"]["y"] = 0
        events["operations"][1]["resource"] = "y"
        events["operations"][1]["effects"] = {"complete": True, "reads": ["y"], "writes": [], "emits": ["y"]}
        for method in ("conservative-all-orders", "declared-effects"):
            self.assertEqual(classify(events, method)["pairs"][0]["classification"], "event-order-sensitive")

    def test_capped_control_cannot_pass_its_expected_invariant(self):
        manifest, _ = corpus()
        fixture = copy.deepcopy(manifest["fixtures"][0])
        fixture["request"]["caps"]["paths"] = 1
        report = explore(fixture["request"])
        self.assertEqual(control_result(fixture, report)["status"], "inconclusive")


    def test_removing_each_witness_or_prevention_fails_the_control(self):
        manifest, _ = corpus()
        by_id = {f["id"]: copy.deepcopy(f) for f in manifest["fixtures"] if not f["h2"]}

        def status(fixture):
            report = explore(fixture["request"])
            self.assertTrue(report["coverage"]["complete"])
            return control_result(fixture, report)["status"]

        for name in by_id:
            self.assertEqual(status(by_id[name]), "pass", name)
        # Unsatisfiable authored invariants: a control must be able to fail.
        for name, patch in {"lost-update": {"value": 0}, "write-skew": {"value": 0},
                            "configuration-stale-read": {"rightValue": 99},
                            "duplicate-events": {"count": 1}, "idempotent-events": {"count": 2},
                            "disjoint-positive": {"values": {"x": 1, "y": 3}}}.items():
            mutated = copy.deepcopy(by_id[name])
            mutated["invariant"].update(patch)
            with self.subTest(invariant=name):
                self.assertEqual(status(mutated), "fail")
        # Removing the modeled prevention / adding the modeled prevention flips the event controls.
        dup = copy.deepcopy(by_id["duplicate-events"])
        for op in dup["request"]["operations"]:
            op["idempotencyKey"] = "retry"
        self.assertEqual(status(dup), "fail")
        idem = copy.deepcopy(by_id["idempotent-events"])
        for op in idem["request"]["operations"]:
            del op["idempotencyKey"]
        self.assertEqual(status(idem), "fail")
        # Completing the hidden effect declaration removes the uncertainty witness.
        hidden = copy.deepcopy(by_id["alias-hidden-effects"])
        hidden["request"]["operations"][1]["effects"] = {"complete": True, "reads": ["x"], "writes": ["x"], "emits": []}
        self.assertEqual(status(hidden), "fail")

    def test_control_evidence_accounts_every_fixture_without_timing(self):
        manifest, registration = corpus()
        evidence = control_evidence(manifest, registration)
        self.assertEqual(evidence, control_evidence(manifest, registration))
        self.assertEqual([entry["id"] for entry in evidence["fixtures"]],
                         [fixture["id"] for fixture in manifest["fixtures"]])
        accounting = evidence["accounting"]
        self.assertEqual((accounting["registeredFixtures"], accounting["controlFixtures"],
                          accounting["h2Fixtures"], accounting["completeCoverage"]), (17, 7, 10, 17))
        self.assertEqual(accounting["controlStatus"], {"pass": 17})
        self.assertEqual(accounting["h2EligibleTerminalCandidates"]
                         + sum(accounting["h2Exclusions"].values()), accounting["h2Fixtures"])
        self.assertNotIn("feasibility", evidence)
        self.assertFalse(any("costNanoseconds" in entry for entry in evidence["fixtures"]))
        self.assertIs(evidence["executionAuthorization"], False)
        self.assertEqual(evidence["scientificReview"], "pending")
        changed = copy.deepcopy(manifest)
        changed["fixtures"][0]["invariant"]["value"] = 100
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            control_evidence(changed, registration)

if __name__ == "__main__":
    unittest.main()
