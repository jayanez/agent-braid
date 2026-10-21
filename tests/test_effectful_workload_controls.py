# SPDX-License-Identifier: AGPL-3.0-only
"""Independent authored race witnesses and finite prevention controls."""
import copy
import json
import unittest
from pathlib import Path

from research.workload_lab.analysis import classify, control_result, validate_manifest
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


if __name__ == "__main__":
    unittest.main()
