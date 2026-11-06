# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T002 / procedure_002: the divergence inventory is current and complete."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts import spec069_divergence_inventory as inventory

ROOT = Path(__file__).resolve().parents[1]


class DivergenceInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fresh = inventory.build(inventory.BASELINE_REV)
        cls.committed = json.loads(inventory.OUTPUT.read_text())
        cls.after = inventory.build()

    def test_committed_inventory_is_current(self):
        fresh = copy.deepcopy(self.fresh)
        committed = copy.deepcopy(self.committed)
        fresh.pop("environment"), committed.pop("environment")
        self.assertEqual(fresh, committed)

    def test_after_decisions_inventory_is_current_and_resolves_blank_strings(self):
        committed = json.loads(inventory.OUTPUT_AFTER.read_text())
        after = copy.deepcopy(self.after)
        after.pop("environment"), committed.pop("environment")
        self.assertEqual(after, committed)
        causes = {item["rootCause"].split(":")[0] for item in self.after["summary"]["rootCauses"]}
        self.assertNotIn("RC-blank", causes)
        self.assertFalse(self.after["summary"]["observedOn2026-11-05"]["blank instanceId accepted by schema, refused by runtime"])

    def test_the_three_divergences_observed_on_2026_11_05_are_present(self):
        self.assertTrue(all(self.fresh["summary"]["observedOn2026-11-05"].values()),
                        self.fresh["summary"]["observedOn2026-11-05"])

    def test_adapter_bounds_whitespace_and_envelope_have_rows(self):
        labels = " | ".join(row["label"] for row in self.fresh["rows"])
        for expected in ("33 operations", "257 bytes", "nesting depth 34", "larger than 1 MiB",
                         "U+001C only", "U+FEFF only", "valid envelope"):
            self.assertIn(expected, labels)
        self.assertIn("pythonOnlyBlank", self.fresh["whitespaceSemantics"])

    def test_every_divergence_has_input_both_verdicts_and_a_proposed_decision(self):
        for row in self.fresh["rows"]:
            if row["relation"] == "equal":
                continue
            self.assertIn("input", row)
            self.assertIn(row["verdicts"]["schema"], {"accepts", "refuses"})
            self.assertIn(row["verdicts"]["service"], {"accepts", "refuses"})
            self.assertEqual(row["decision"]["status"], "proposed")

    def test_every_schema_keyword_probed_and_every_check_covered(self):
        for schema in self.fresh["schemas"][:2]:
            self.assertTrue(schema["keywordsProbed"], schema["path"])
        self.assertEqual([c["id"] for c in self.fresh["runtimeChecks"] if not c["probedBy"]], [])

    def test_threshold_is_judged_on_root_causes(self):
        summary = self.fresh["summary"]
        self.assertEqual(summary["thresholdExceeded"], summary["rootCauseCount"] > inventory.THRESHOLD)

    def test_negative_control_a_missing_row_is_detected(self):
        committed = copy.deepcopy(self.committed)
        committed["rows"] = committed["rows"][1:]
        fresh = copy.deepcopy(self.fresh)
        fresh.pop("environment"), committed.pop("environment")
        self.assertNotEqual(fresh, committed)

    def test_schema_hashes_match_the_inspected_revisions(self):
        for doc, rev in ((self.fresh, inventory.BASELINE_REV), (self.after, None)):
            for schema in doc["schemas"][:2]:
                text = inventory.schema_text(ROOT / schema["path"], rev)
                self.assertEqual(schema["sha256"], inventory.text_sha256(text))


if __name__ == "__main__":
    unittest.main()
