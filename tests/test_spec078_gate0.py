# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T004 (REQ-003, REQ-004, REQ-005 / SC-003 to SC-005 / procedures 003-005): Gate 0."""

from __future__ import annotations

import copy
import unittest

from scripts import spec078_gate0 as gate0
from scripts.spec078_build_set import SKILL


class Gate0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = gate0.load_sets()
        cls.skill = SKILL.read_text("utf-8")
        cls.report = gate0.run(cls.sets, cls.skill)

    def small(self, *ids: str) -> dict[str, list[dict]]:
        """A copy of the set restricted to the named cases (other splits empty)."""
        return {split: [copy.deepcopy(c) for c in cases if c["id"] in ids] for split, cases in self.sets.items()}

    def first(self, cls: str, split: str = "test") -> dict:
        return next(c for c in self.sets[split] if c["class"] == cls)

    # REQ-003
    def test_every_reference_is_accepted_and_valid(self):
        self.assertEqual(self.report["references"], [])
        self.assertEqual(self.report["partialControls"], [])

    def test_a_wrong_reference_blocks_gate0(self):
        case = self.first("disjoint")
        sets = self.small(case["id"])
        sets["test"][0]["expect"]["pairs"][0]["classification"] = "conflicting"
        sets["test"][0]["expect"]["pairs"][0]["constraints"] = ["serialize-or-isolate"]
        report = gate0.run(sets, self.skill)
        self.assertFalse(report["passed"])
        self.assertEqual([r["id"] for r in report["references"]], [case["id"]])

    def test_the_complete_variant_of_a_partial_case_is_invalid(self):
        case = self.first("partial")
        analyzer = gate0.Analyzer()
        try:
            ok, _ = analyzer.valid(case, *gate0.reference_request(case, str(analyzer.repository), honour_partial=False))
        finally:
            analyzer.close()
        self.assertFalse(ok)

    # REQ-004
    def test_following_the_skill_literally_is_valid_on_every_case(self):
        self.assertEqual(self.report["pins"], [])
        self.assertEqual(self.report["follower"], [])

    def test_a_skill_edit_that_drops_a_pinned_rule_fails_the_pin_check(self):
        for name, sentence in gate0.RULES.items():
            problems = gate0.pin_problems(self.skill.replace(sentence, "(removed)"))
            self.assertTrue(any(repr(name) in p for p in problems), name)

    def test_the_old_read_rule_breaks_the_pins_and_chain_plain_cases(self):
        new = ("`dependencies`; the dependency alone orders the two units. Declare a `read`\n"
               "  of a file the other unit writes only when the user says this unit uses that\n"
               "  file's content, for example code that reads a setting the other unit adds.\n"
               "  Waiting for the other unit is not a read.")
        self.assertIn(new, self.skill)
        old = self.skill.replace(new, "`dependencies` and declares a `read` of the file the other unit writes.")
        self.assertIn("rule 'read-only-for-content': sentence not found in the skill", gate0.pin_problems(old))
        case = self.first("chain-plain")
        sets = self.small(case["id"])
        nulls = gate0.run(sets, self.skill)["nulls"]["over-declaration"]
        self.assertEqual(nulls["splits"]["test"]["passing"], 0)  # the old rule's answer fails the case

    def test_the_follower_copies_the_skill_example(self):
        case = self.first("chain-read")
        kind, request = gate0.follower_request(case, self.skill, "<repo>")
        example = gate0.examples(self.skill)["aim"]
        self.assertEqual(kind, "aim")
        self.assertEqual(request["analysisInputVersion"], example["analysisInputVersion"])
        self.assertEqual(request["operations"][0]["evidence"], example["operations"][0]["evidence"])
        reads = [e for op in request["operations"] for e in op["effects"]["declared"] if e["kind"] == "read"]
        self.assertEqual(len(reads), 1)

    # REQ-005
    def test_null_baselines_fail_their_classes_and_never_meet_the_threshold(self):
        self.assertEqual(set(self.report["nulls"]), set(gate0.NULLS))
        for name, result in self.report["nulls"].items():
            self.assertEqual(result["unexpectedPasses"], [], name)
            for split, row in result["splits"].items():
                self.assertFalse(row["meetsThreshold"], f"{name} {split}")
        self.assertTrue(self.report["passed"])

    def test_a_null_that_passes_a_case_it_must_fail_is_reported(self):
        case = self.first("disjoint")
        sets = self.small(case["id"])
        for pair in sets["test"][0]["expect"]["pairs"]:  # make "always partial" the right answer
            pair.update(classification="unknown", constraints=["serialize-unless-stronger-evidence"])
        report = gate0.run(sets, self.skill)
        self.assertIn(case["id"], report["nulls"]["partial-coverage"]["unexpectedPasses"])
        self.assertFalse(report["passed"])


if __name__ == "__main__":
    unittest.main()
