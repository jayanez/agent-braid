# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T004 (REQ-006 / SC-009): the held-out v4 split is fresh, follows from its facts and its class plan."""

from __future__ import annotations

import copy
import json
import unittest

from scripts import spec078_build_set as v2set
from scripts import spec079_build_v4 as v4


class V4SetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(v4.OUT.read_text("utf-8"))
        cls.earlier = v4._earlier_sets()
        cls.protected = v4.protected_texts()

    def check(self, data):
        v4.check(data, earlier=self.earlier, protected=self.protected)

    def test_committed_split_equals_a_fresh_build(self):
        self.assertEqual(v4.OUT.read_text("utf-8"), v4.render(v4.build()))
        self.assertEqual(v4.main(["--check"]), 0)

    def test_class_plan(self):
        counts = {c: sum(x["class"] == c for x in self.data["cases"]) for c in v4.PLAN}
        self.assertEqual(counts, {"disjoint-parallel": 20, "overlap-write": 15, "dependency-order": 15,
                                  "read-only-shared": 10, "kind-choice-probe": 20, "analyze-tempting": 10,
                                  "git-branch": 10})
        self.assertEqual(self.data["generator"]["seed"], 4079)

    def test_no_leakage(self):
        """SC-009: zero window, normalized-text or fact-pattern collisions with every earlier set."""
        self.check(self.data)
        found = set().union(*(v2set.windows(c["prompt"]) for c in self.data["cases"]))
        for name, texts in self.protected.items():
            self.assertFalse(found & set().union(*(v2set.windows(t) for t in texts)), name)
        old = {v4._pattern(c["facts"]) for c in self.earlier}
        self.assertFalse(old & {v4._pattern(c["facts"]) for c in self.data["cases"]})

    def test_negative_control_an_earlier_window_is_refused(self):
        data = copy.deepcopy(self.data)
        case = data["cases"][0]
        protected = dict(self.protected, planted=[case["prompt"]])
        with self.assertRaisesRegex(v2set.SetError, "8-word window with planted"):
            v4.check(data, earlier=self.earlier, protected=protected)

    def test_negative_control_an_earlier_fact_pattern_is_refused(self):
        data = copy.deepcopy(self.data)
        earlier = self.earlier + [{"facts": data["cases"][5]["facts"], "prompt": ""}]
        with self.assertRaisesRegex(v2set.SetError, "already used by a SPEC-078 split"):
            v4.check(data, earlier=earlier, protected=self.protected)

    def test_negative_control_prompt_and_expectation_drift_are_refused(self):
        data = copy.deepcopy(self.data)
        data["cases"][3]["prompt"] += " Also touch CHANGELOG.md."
        with self.assertRaisesRegex(v2set.SetError, "prompt does not follow"):
            self.check(data)
        data = copy.deepcopy(self.data)
        data["cases"][3]["expect"]["pairs"][0]["classification"] = "conflicting"
        with self.assertRaisesRegex(v2set.SetError, "expectation does not follow"):
            self.check(data)

    def test_aim_prompts_do_not_read_as_git_or_units(self):
        from scripts import spec078_gate0
        for case in self.data["cases"]:
            self.assertEqual(spec078_gate0.kind_from_prompt(case["prompt"]), case["facts"]["kind"], case["id"])


if __name__ == "__main__":
    unittest.main()
