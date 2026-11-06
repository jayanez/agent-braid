# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T007 (procedure_007): field-specific refusals through the analyze-work service."""

from __future__ import annotations

import copy
import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from agent_braid.analysis import key_token
from scripts import spec069_divergence_inventory as inv
from tests.spec069_differential import Harness, load_corpus

TOKENIZED = re.compile(r"^(?P<head>.*/readVersions)/(?P<key>[^/]+)$")


def expected_pointer(case: dict) -> str:
    """The corpus pointer with request-defined keys (readVersions) replaced by their token."""
    match = TOKENIZED.match(case["pointer"])
    if match:
        key = match["key"].replace("~1", "/").replace("~0", "~")
        return f"{match['head']}/{key_token(key)}"
    return case["pointer"]


class RefusalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = Harness()

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def refusal(self, kind: str, request) -> str:
        ok, summary = self.harness.prober.service_verdict(kind, request)
        self.assertFalse(ok, summary)
        return summary

    def test_structural_refusals_name_pointer_and_expected_form(self):
        checked = 0
        for kind in ("aim", "git"):
            for case in load_corpus(kind):
                if case["layer"] != "structural" or case["expect"]["service"] != "refuses":
                    continue
                request = copy.deepcopy(case["request"])
                if kind == "git":
                    request = json.loads(json.dumps(request))
                summary = self.refusal(kind, request)
                pointer = expected_pointer(case)
                with self.subTest(case["id"], label=case["label"]):
                    self.assertIn(f" at {pointer or '/'}", summary)
                    self.assertIn("expected", summary)
                    self.assertLessEqual(len(summary.encode()), 1100)
                checked += 1
        self.assertGreater(checked, 150)

    def test_semantic_refusals_carry_fixed_codes(self):
        expected = {
            "duplicate instanceId": "duplicate-instance-id", "duplicate attemptId": "duplicate-attempt-id",
            "unknown dependency": "unknown-dependency", "self dependency": "self-dependency",
            "cyclic dependencies": "cyclic-dependencies",
        }
        for case in load_corpus("aim"):
            if case["layer"] == "batch":
                summary = self.refusal("aim", case["request"])
                if case["label"] in expected:
                    self.assertIn(f"[{expected[case['label']]}]", summary, case["label"])
                else:
                    self.assertRegex(summary, r"\[[a-z-]+\]$", case["label"])

    def test_negative_control_unknown_secret_shaped_key_is_not_echoed(self):
        a, b = inv.aim_pair()
        secret = "sk-live-ABCDEF0123456789"
        a[secret] = "value-that-must-not-leak"
        summary = self.refusal("aim", [a, b])
        self.assertNotIn(secret, summary)
        self.assertNotIn("value-that-must-not-leak", summary)
        self.assertIn(key_token(secret), summary)
        a, b = inv.aim_pair()
        a["readVersions"] = {secret: -1}
        summary = self.refusal("aim", [a, b])
        self.assertNotIn(secret, summary)
        self.assertIn(key_token(secret), summary)

    def test_negative_control_values_are_never_echoed(self):
        a, b = inv.aim_pair()
        a["instanceId"] = 12345678901234567890
        self.assertNotIn("12345678901234567890", self.refusal("aim", [a, b]))
        a, b = inv.aim_pair()
        a["effects"]["coverage"]["status"] = "super-secret-status"
        self.assertNotIn("super-secret-status", self.refusal("aim", [a, b]))

    def test_negative_control_git_output_stays_masked(self):
        request = inv.git_base()
        request["baseRevision"] = "refs/heads/does-not-exist-secret-branch"
        summary = self.refusal("git", request)
        self.assertNotIn("does-not-exist-secret-branch", summary)
        self.assertNotIn(str(self.harness.repo), summary)

    def test_negative_control_missing_and_outside_paths_are_indistinguishable(self):
        missing = inv.git_base()
        missing["repository"] = str(self.harness.repo / "no-such-directory")
        outside = inv.git_base()
        outside["repository"] = str(Path(self.harness.temp.name).resolve())
        first = self.refusal("git", json.loads(json.dumps(missing).replace(inv.REPO_PLACEHOLDER, str(self.harness.repo))))
        second = self.refusal("git", json.loads(json.dumps(outside).replace(inv.REPO_PLACEHOLDER, str(self.harness.repo))))
        self.assertEqual(self.strip_paths(first), self.strip_paths(second))
        worktree_missing = inv.git_base()
        worktree_missing["repository"] = str(self.harness.repo)
        worktree_missing["operations"][1]["source"] = {"kind": "worktree", "path": str(self.harness.repo / "nope")}
        worktree_outside = copy.deepcopy(worktree_missing)
        worktree_outside["operations"][1]["source"]["path"] = str(Path(self.harness.temp.name).resolve())
        self.assertEqual(self.refusal("git", worktree_missing), self.refusal("git", worktree_outside))
        self.assertEqual(self.strip_paths(first), self.refusal("git", worktree_missing))

    def strip_paths(self, text: str) -> str:
        return text.replace(str(self.harness.repo), "<repo>")

    def test_every_message_is_bounded(self):
        a, b = inv.aim_pair()
        a["readVersions"] = {"k" * 5000: -1}
        self.assertLessEqual(len(self.refusal("aim", [a, b]).encode()), 1100)


if __name__ == "__main__":
    unittest.main()
