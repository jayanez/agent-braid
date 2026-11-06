# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T015 (procedure_015): declared-not-observed label on independent-candidate pairs."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

import jsonschema

from agent_braid import analysis
from scripts import spec069_divergence_inventory as inv

ROOT = Path(__file__).resolve().parents[1]
REPORT_SCHEMA = json.loads((ROOT / "schemas/0.1.0-alpha/analysis-report.schema.json").read_text())


def disjoint(method_left: str = "declared", method_right: str = "declared"):
    a = inv.base_record("lbl-a", "lbl-a-1", [], "repo://w/a.txt")
    b = inv.base_record("lbl-b", "lbl-b-1", [], "repo://w/b.txt")
    for record, method in ((a, method_left), (b, method_right)):
        record["evidence"][0]["method"] = method
        record["effects"]["declared"] = [{"kind": "read", "resource": record["effects"]["declared"][0]["resource"]}]
        record["effects"]["inferred"] = []
        record["effects"]["observed"] = []
    return [a, b]


class DeclaredLabelTests(unittest.TestCase):
    def interaction(self, records):
        report = analysis.analyze(records)
        jsonschema.Draft202012Validator(REPORT_SCHEMA).validate(report)
        return report["interactions"][0]

    def test_declared_only_independent_candidate_carries_the_label(self):
        item = self.interaction(disjoint())
        self.assertEqual(item["classification"], "independent-candidate")
        self.assertEqual(item["completenessBasis"], "declared-not-observed")

    def test_replay_evidence_on_both_records_removes_the_label(self):
        item = self.interaction(disjoint("replay", "replay"))
        self.assertEqual(item["classification"], "independent-candidate")
        self.assertNotIn("completenessBasis", item)

    def test_one_replay_record_removes_the_label(self):
        self.assertNotIn("completenessBasis", self.interaction(disjoint("declared", "replay")))

    def test_a_record_with_a_declared_and_a_replay_item_is_not_declared_only(self):
        records = disjoint()
        records[0]["evidence"].append(dict(records[0]["evidence"][0], method="replay"))
        self.assertNotIn("completenessBasis", self.interaction(records))

    def test_other_classifications_are_never_labelled(self):
        conflicting = disjoint()
        for record in conflicting:
            record["effects"]["declared"] = [{"kind": "write", "resource": "repo://w/same"}]
        ordered = disjoint()
        ordered[1]["dependencies"] = ["lbl-a"]
        unknown = disjoint()
        unknown[0]["effects"]["coverage"]["status"] = "partial"
        for name, records in (("conflicting", conflicting), ("ordered", ordered), ("unknown", unknown)):
            item = self.interaction(records)
            self.assertEqual(item["classification"], name)
            self.assertNotIn("completenessBasis", item)

    def test_classification_constraints_and_evidence_are_unchanged_by_the_label(self):
        labelled = self.interaction(disjoint())
        plain = self.interaction(disjoint("replay", "replay"))
        for key in ("classification", "sharedResources", "reasons", "constraints", "evidence"):
            self.assertEqual(labelled[key], plain[key], key)

    def test_schema_accepts_only_the_declared_not_observed_value(self):
        report = analysis.analyze(disjoint())
        validator = jsonschema.Draft202012Validator(REPORT_SCHEMA)
        self.assertTrue(validator.is_valid(report))
        bad = copy.deepcopy(report)
        bad["interactions"][0]["completenessBasis"] = "observed"
        self.assertFalse(validator.is_valid(bad))

    def test_report_is_deterministic_and_digest_covers_the_label(self):
        first, second = analysis.analyze(disjoint()), analysis.analyze(disjoint())
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        stripped = copy.deepcopy(first)
        del stripped["interactions"][0]["completenessBasis"]
        stripped["analysisId"] = None
        self.assertNotEqual(analysis._digest(stripped), first["analysisId"])


if __name__ == "__main__":
    unittest.main()
