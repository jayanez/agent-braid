# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T007 (REQ-008 / SC-011, REQ-011 / SC-014): the v4 freeze holds and no frozen SPEC-069/078 path changed."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import spec079_freeze as freeze

ROOT = freeze.ROOT


def _copy(paths, target: Path) -> None:
    for path in paths:
        (target / path).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target / path)


class FreezeTests(unittest.TestCase):
    """REQ-008 / SC-011: every bound hash matches the tree, and the freeze names the pinned plugin commit."""

    def setUp(self):
        self.record = freeze.load(ROOT)

    def test_freeze_matches(self):
        self.assertEqual(freeze.main(["--check"]), 0)
        self.assertEqual(set(self.record["files"]), set(freeze.BOUND))
        for path, digest in self.record["files"].items():
            self.assertEqual(freeze.sha256(ROOT, path), digest, path)
        self.assertRegex(self.record["commit"], r"^[0-9a-f]{40}$")
        self.assertEqual(self.record["pluginCommit"], self.record["commit"])
        for path in ("specs/079-kind-choice-tool-fix/evaluation-protocol.md", freeze.SPLIT, freeze.GATE0,
                     "scripts/spec079_build_v4.py", freeze.SKILL, "agent_braid/tooling_mcp.py"):
            self.assertIn(path, self.record["files"])

    def test_the_bound_gate0_report_passes(self):
        self.assertTrue(json.loads((ROOT / freeze.GATE0).read_text("utf-8"))["passed"])

    def test_negative_control_an_edited_bound_file_breaks_the_freeze(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _copy((*freeze.BOUND, *freeze.RECORDS, *freeze.frozen_paths(ROOT), freeze.FREEZE), root)
            self.assertEqual(freeze.check_freeze(root)["commit"], self.record["commit"])
            with (root / freeze.SPLIT).open("a", encoding="utf-8") as handle:
                handle.write(" ")
            with self.assertRaisesRegex(freeze.FreezeError, "v4-test.json differs from the v4 freeze"):
                freeze.check_freeze(root)

    def test_a_missing_or_unknown_freeze_refuses(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(freeze.FreezeError, "not frozen"):
                freeze.load(root)
            (root / freeze.FREEZE).parent.mkdir(parents=True)
            (root / freeze.FREEZE).write_text(json.dumps({**self.record, "pluginCommit": "0" * 40}), "utf-8")
            with self.assertRaisesRegex(freeze.FreezeError, "unknown v4 freeze record"):
                freeze.load(root)


class BoundaryTests(unittest.TestCase):
    """REQ-011 / SC-014: the closed SPEC-069 and SPEC-078 freeze records and every path they bind are unchanged."""

    def setUp(self):
        self.closed = freeze.load(ROOT)["closedRecords"]

    def test_frozen_paths_untouched(self):
        self.assertEqual(freeze.boundary_problems(ROOT, self.closed), [])
        paths = freeze.frozen_paths(ROOT)
        for path in ("scripts/spec069_scoring.py", "specs/069-aim-request-authoring/prompts/held-out.json",
                     "specs/078-lightning-heldout-v2/prompts/test.json",
                     "specs/078-lightning-heldout-v2/prompts/v3-test.json", "scripts/spec078_gate0.py"):
            self.assertIn(path, paths)

    def test_only_the_v3_rebound_skill_departs_from_the_v2_freeze(self):
        """The v2 freeze's skill hash was superseded by SPEC-078 T012 and re-frozen in v3, before SPEC-079."""
        v2 = json.loads((ROOT / freeze.SPEC078_FREEZE).read_text("utf-8"))["files"]
        v3 = json.loads((ROOT / freeze.SPEC078_FREEZE_V3).read_text("utf-8"))["files"]
        departed = {path for path, digest in v2.items() if freeze.sha256(ROOT, path) != digest}
        self.assertEqual(departed, {freeze.SKILL})
        self.assertIn(freeze.SKILL, v3)

    def test_negative_control_an_edited_frozen_path_or_record_is_reported(self):
        frozen = freeze.frozen_paths(ROOT)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _copy((*freeze.RECORDS, *frozen), root)
            self.assertEqual(freeze.boundary_problems(root, self.closed), [])
            held_out = "specs/069-aim-request-authoring/prompts/held-out.json"
            with (root / held_out).open("a", encoding="utf-8") as handle:
                handle.write(" ")
            self.assertEqual(freeze.boundary_problems(root, self.closed),
                             [f"{held_out} differs from its SPEC-069/078 freeze"])
            shutil.copyfile(ROOT / held_out, root / held_out)
            with (root / freeze.SPEC078_FREEZE_V3).open("a", encoding="utf-8") as handle:
                handle.write(" ")
            self.assertIn(f"{freeze.SPEC078_FREEZE_V3} changed after the SPEC-079 freeze",
                          freeze.boundary_problems(root, self.closed))


if __name__ == "__main__":
    unittest.main()
