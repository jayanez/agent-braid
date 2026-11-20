# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T002 (REQ-002 / SC-002 / procedure_002): the held-out set v2 and its build checks."""

from __future__ import annotations

import copy
import json
import unittest

from scripts import spec078_build_set as builder


class SetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sets = builder.build()

    def mutated(self, split: str, index: int, change) -> dict:
        sets = copy.deepcopy(self.sets)
        change(sets[split]["cases"][index])
        return sets

    def assertRefused(self, sets: dict, pattern: str) -> None:
        with self.assertRaisesRegex(builder.SetError, pattern):
            builder.check(sets)

    def test_the_committed_files_equal_a_fresh_build(self):
        self.assertEqual(builder.main(["--check"]), 0)
        for split, data in self.sets.items():
            committed = (builder.OUT / f"{split}.json").read_text("utf-8")
            self.assertEqual(committed, builder.render(data), split)

    def test_split_sizes_and_class_coverage(self):
        self.assertEqual({s: len(d["cases"]) for s, d in self.sets.items()}, builder.SPLITS)
        for data in self.sets.values():
            self.assertEqual({c["class"] for c in data["cases"]}, set(builder.CLASSES))

    def test_every_class_but_partial_and_git_keeps_an_independent_pair(self):
        # what makes the partial-coverage null baseline fail (REQ-005)
        for data in self.sets.values():
            for case in data["cases"]:
                labels = {p["classification"] for p in case["expect"]["pairs"]}
                if case["class"] not in ("partial", "git"):
                    self.assertIn("independent-candidate", labels, case["id"])
                if case["class"] == "partial":
                    self.assertNotIn("independent-candidate", labels, case["id"])

    def test_chains_without_content_use_expect_no_read(self):
        for data in self.sets.values():
            for case in data["cases"]:
                kinds = {e["kind"] for u in case["expect"]["units"] for e in u.get("effects", [])}
                if case["class"] == "chain-plain":
                    self.assertNotIn("read", kinds, case["id"])
                if case["class"] == "chain-read":
                    self.assertIn("read", kinds, case["id"])
                for unit in case["expect"]["units"]:
                    self.assertFalse(any(e.get("optional") for e in unit.get("effects", [])), case["id"])

    def test_ids_do_not_look_like_spec069_held_out_ids(self):
        for data in self.sets.values():
            for case in data["cases"]:
                self.assertNotRegex(case["id"], r"HELD-\d+")

    # negative controls: each build rule refuses a set that breaks it
    def test_a_copied_spec069_prompt_is_refused(self):
        v1 = json.loads(builder.V1_SETS[1].read_text("utf-8"))["cases"][0]["prompt"]
        self.assertRefused(self.mutated("test", 0, lambda c: c.update(prompt=c["prompt"] + " " + v1)), "SPEC-069")

    def test_a_split_missing_a_class_is_refused(self):
        def drop(case):
            case["class"] = "disjoint"
        sets = copy.deepcopy(self.sets)
        for case in sets["feedback"]["cases"]:
            if case["class"] == "git":
                drop(case)
        self.assertRefused(sets, "misses classes")

    def test_a_window_shared_across_splits_is_refused(self):
        leaked = self.sets["test"]["cases"][0]["prompt"]
        self.assertRefused(self.mutated("feedback", 0, lambda c: c.update(prompt=c["prompt"] + " " + leaked)),
                           "share an 8-word window")

    def test_a_window_shared_with_the_skill_is_refused(self):
        prompt = self.sets["validation"]["cases"][0]["prompt"]
        with self.assertRaisesRegex(builder.SetError, "analyze skill"):
            builder.check(self.sets, skill_text=prompt)

    def test_a_path_absent_from_the_prompt_is_refused(self):
        case = self.sets["test"]["cases"][0]
        path = case["facts"]["units"][0]["effects"][0]["path"]
        self.assertRefused(self.mutated("test", 0, lambda c: c.update(prompt=c["prompt"].replace(path, "a file"))),
                           "not a fixture file named")

    def test_a_unit_without_a_fixture_effect_is_refused(self):
        def outside(case):
            case["facts"]["units"][0]["effects"][0]["path"] = "src/missing.py"
            case["expect"] = builder.expectation(case["facts"])
        self.assertRefused(self.mutated("test", 0, outside), "no effect on a fixture file")

    def test_content_use_wording_must_match_the_facts(self):
        index = next(i for i, c in enumerate(self.sets["test"]["cases"]) if c["class"] == "chain-plain")
        self.assertRefused(self.mutated("test", index, lambda c: c.update(prompt=c["prompt"] + " It uses what it needs.")),
                           "content-use wording")

    def test_an_expectation_that_does_not_follow_from_the_facts_is_refused(self):
        def wrong(case):
            case["expect"]["pairs"][0]["classification"] = "unknown"
        self.assertRefused(self.mutated("validation", 0, wrong), "does not follow")

    def test_a_duplicated_prompt_is_refused(self):
        other = self.sets["test"]["cases"][1]
        self.assertRefused(self.mutated("test", 0, lambda c: c.update({**copy.deepcopy(other), "id": c["id"]})),
                           "duplicate prompt")


if __name__ == "__main__":
    unittest.main()
