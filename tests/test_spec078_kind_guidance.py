# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T012 (REQ-013 / SC-013): the kind-selection fix of Amendment 1 and the analyzer behaviour it states.

The first test pins the fix (it fails on the skill before it); the analyzer tests pin the behaviour the sentences
describe and pass with or without them.

Gate 1 failed only when the model answered a parallel question with `units` (17 attempts) or skipped the call
because it believed `aim` needs real digests (3 attempts); `evidence/gate1-diagnosis.json`.
"""
from __future__ import annotations

import re
import unittest

from tests.test_spec069_guidance import SKILL, GuidanceCase, documented_examples

NO_UNITS = "Never use `units` to answer whether work can run in parallel, even when only paths are known."
PLACEHOLDERS = ("`aim` does not need real digests: placeholder `sha256:` values like the ones in the example below are "
                "expected, so never skip the call because you cannot compute digests, and say the input is synthetic.")


def kind_section(text: str) -> str:
    start = text.index("## Build an analyze-work request")
    return " ".join(text[start:text.index("### `aim`", start)].split())


class KindSelectionTests(GuidanceCase):
    def test_the_sentences_are_in_the_kind_section(self):
        section = kind_section(SKILL.read_text("utf-8"))
        self.assertIn(NO_UNITS, section)
        self.assertIn(PLACEHOLDERS, section)

    def test_units_cannot_report_disjoint_work_as_parallel(self):
        units = next(e for e in documented_examples(SKILL.read_text("utf-8")) if e["kind"] == "units")
        request = {"unitsRequestVersion": units["request"]["unitsRequestVersion"],
                   "units": [{"id": "a", "coverage": "complete", "effects": [{"kind": "write", "resource": "src/a.py"}]},
                             {"id": "b", "coverage": "complete", "effects": [{"kind": "write", "resource": "src/b.py"}]}]}
        pairs = self.send("units", request)["result"]["report"]["interactions"]
        self.assertEqual([p["classification"] for p in pairs], ["unknown"])

    def test_aim_with_the_placeholder_digests_reports_independent_candidate(self):
        aim = next(e for e in documented_examples(SKILL.read_text("utf-8")) if e["kind"] == "aim")
        self.assertTrue(re.search(r"sha256:(1{64}|a{64})", str(aim["request"])))  # the documented placeholders
        self.assertEqual(self.problems(aim), [])
        self.assertEqual(aim["result"], "independent-candidate")

    def test_each_sentence_appears_once(self):
        section = kind_section(SKILL.read_text("utf-8"))
        for sentence in (NO_UNITS, PLACEHOLDERS):
            self.assertEqual(section.count(sentence), 1)


if __name__ == "__main__":
    unittest.main()
