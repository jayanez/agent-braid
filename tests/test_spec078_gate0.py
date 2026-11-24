# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T004 (REQ-003, REQ-004, REQ-005 / SC-003 to SC-005 / procedures 003-005): Gate 0."""

from __future__ import annotations

import copy
import unittest
from unittest import mock

from agent_braid import tooling_mcp
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

    def test_the_old_read_rule_breaks_the_pins_and_its_answer_fails_chain_plain(self):
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
        kind, request = gate0.follower_request(case, gate0.examples(self.skill), "<repo>")
        example = gate0.examples(self.skill)["aim"]
        self.assertEqual(kind, "aim")
        self.assertEqual(request["analysisInputVersion"], example["analysisInputVersion"])
        self.assertEqual(request["operations"][0]["evidence"], example["operations"][0]["evidence"])
        reads = [e for op in request["operations"] for e in op["effects"]["declared"] if e["kind"] == "read"]
        self.assertEqual(len(reads), 1)

    def test_the_kind_comes_from_the_prompt_wording(self):
        self.assertEqual(gate0.kind_from_prompt(self.first("git")["prompt"]), "git")
        self.assertEqual(gate0.kind_from_prompt(self.first("disjoint")["prompt"]), "aim")
        self.assertEqual(gate0.kind_from_prompt("Give me a quick conflict check by path."), "units")
        case = copy.deepcopy(self.first("disjoint"))
        case["prompt"] += " Each change lives on its own branch."
        with self.assertRaisesRegex(gate0.Gate0Error, "reads as kind 'git'"):
            gate0.follower_request(case, gate0.examples(self.skill), "<repo>")

    # REQ-005
    def test_null_baselines_fail_their_classes_and_never_meet_the_threshold(self):
        self.assertEqual(set(self.report["nulls"]), set(gate0.NULLS))
        for name, result in self.report["nulls"].items():
            self.assertEqual(result["unexpectedPasses"], [], name)
            for split, row in result["splits"].items():
                self.assertFalse(row["meetsThreshold"], f"{name} {split}")
        self.assertTrue(self.report["passed"])

    def test_the_units_null_agrees_with_partial_coverage(self):
        # SPEC-078 is closed and measured this on the pre-SPEC-079 tool, where disjoint `units` requests
        # returned ok/unknown. Only this test depends on that path, so only it pins `_units_disjoint` off;
        # the SPEC-079 refusal itself is covered by tests/test_tooling_mcp_units_redirect.py.
        with mock.patch.object(tooling_mcp, "_units_disjoint", lambda records: False):
            report = gate0.run(self.sets, self.skill)
        for split, rows in report["nulls"]["units-kind"]["splits"].items():
            self.assertEqual(rows, report["nulls"]["partial-coverage"]["splits"][split], split)

    def test_the_units_null_is_refused_on_the_shipped_tool(self):
        """SPEC-079 REQ-001: on the shipped tool the `units` null passes no case it scores."""
        for split, rows in self.report["nulls"]["units-kind"]["splits"].items():
            self.assertEqual(rows["passing"], 0, split)
            self.assertGreater(rows["of"], 0, split)

    def test_a_null_that_meets_the_threshold_fails_gate0(self):
        # over-declaration is right on chain-read cases; alone they push its Wilson bound over 0.80
        reads = [copy.deepcopy(c) for cases in self.sets.values() for c in cases if c["class"] == "chain-read"]
        self.assertGreaterEqual(len(reads), 16)  # 16/16 gives a Wilson lower bound of 0.806
        report = gate0.run({"feedback": [], "validation": [], "test": reads}, self.skill)
        row = report["nulls"]["over-declaration"]["splits"]["test"]
        self.assertEqual(report["nulls"]["over-declaration"]["unexpectedPasses"], [])
        self.assertTrue(row["meetsThreshold"], row)
        self.assertFalse(report["passed"])

    def test_the_old_read_rule_strategy_never_meets_od1(self):
        rows = self.report["oldReadRuleStrategy"]
        self.assertEqual(set(rows), {"feedback", "validation", "test"})
        self.assertGreaterEqual(rows["test"]["wilsonLower"], 0.80)  # the share alone would pass ...
        self.assertFalse(rows["test"]["meetsThreshold"])           # ... the per-class clause does not

    def test_od1_needs_the_share_and_every_class(self):
        self.assertTrue(gate0.meets_od1([("a", True)] * 18 + [("b", True)] * 2)[0])
        self.assertFalse(gate0.meets_od1([("a", True)] * 18 + [("b", False)] * 2)[0])  # class b below half
        self.assertFalse(gate0.meets_od1([("a", True)] * 7 + [("a", False)] * 3)[0])   # share too low
        self.assertFalse(gate0.meets_od1([])[0])

    def test_a_null_that_passes_a_case_it_must_fail_is_reported(self):
        case = self.first("chain-plain")
        sets = self.small(case["id"])
        unit = sets["test"][0]["expect"]["units"][1]  # make the old rule's read part of the expectation
        first = sets["test"][0]["expect"]["units"][0]["effects"][0]["resource"]
        unit["effects"].append({"kind": "read", "resource": first})
        report = gate0.run(sets, self.skill)
        self.assertIn(case["id"], report["nulls"]["over-declaration"]["unexpectedPasses"])
        self.assertFalse(report["passed"])

if __name__ == "__main__":
    unittest.main()
