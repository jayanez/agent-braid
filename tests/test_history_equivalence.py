# SPDX-License-Identifier: AGPL-3.0-only
"""ADR 0022 equivalence is closed, tree-verified and never needs original objects."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import closure_anchors, history_equivalence as equivalence, publication
from scripts import validate_spec_kit as gates


class HistoryEquivalenceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="braid-equivalence-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        shutil.copytree(gates.ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", ".venv", ".venv-speckit", "__pycache__"))
        shutil.copytree(gates.ROOT / ".git", self.root / ".git")
        self.path = self.root / equivalence.EQUIVALENCE
        self.data = json.loads(self.path.read_text())
        self.entries = {item["old"]: item for item in self.data["entries"]}
        self.anchor = json.loads(
            (self.root / closure_anchors.ANCHORS).read_text())["milestones"]["M2"]
        equivalence._validated.cache_clear()
        self.addCleanup(equivalence._validated.cache_clear)

    def git(self, *args):
        return subprocess.check_output(
            ["git", "-C", str(self.root), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", *args],
            text=True, stderr=subprocess.PIPE).strip()

    def tag_entry(self):
        for item in self.data["tags"]:
            entry = self.entries.get(item["oldCommit"])
            if entry and subprocess.run(
                    ["git", "-C", str(self.root), "merge-base", "--is-ancestor",
                     entry["new"], "HEAD"], capture_output=True).returncode:
                return item, entry
        self.fail("no tag-only equivalence entry")

    def test_listed_identity_resolves_and_unlisted_is_unchanged(self):
        closure = self.anchor["closureCommit"]
        self.assertIn(closure, self.entries)
        self.assertEqual(
            equivalence.resolve_public_commit(self.root, closure, self.anchor["closureTree"]),
            self.entries[closure]["new"])
        root_commit = self.git("rev-list", "--max-parents=0", "HEAD")
        self.assertEqual(equivalence.resolve_public_commit(self.root, root_commit), root_commit)
        self.assertEqual(equivalence.resolve_public_commit(self.root, "f" * 40), "f" * 40)

    def test_m2_anchor_addenda_and_assurance_records_pass(self):
        closure_anchors.validate_closure_anchor(self.root, "M2")
        publication.validate_addenda(self.root)
        for spec in sorted((self.root / "specs").glob("*/spec.md")):
            with self.subTest(feature=spec.parent.name):
                gates.validate_portable_record(self.root, spec.parent / "assurance.json")

    def test_tree_mismatch_fails_closed(self):
        closure = self.anchor["closureCommit"]
        with self.assertRaisesRegex(ValueError, "tree does not match"):
            equivalence.resolve_public_commit(self.root, closure, "0" * 40)

    def test_record_bytes_cannot_change_after_introduction(self):
        original = self.path.read_bytes()
        for altered in (original + b"\n", original.replace(b"  ", b"   ", 1),
                        json.dumps({**self.data, "limits": ["changed"]},
                                   indent=2, sort_keys=True).encode() + b"\n"):
            with self.subTest(size=len(altered)):
                self.path.write_bytes(altered)
                equivalence._validated.cache_clear()
                with self.assertRaises(ValueError):
                    equivalence.load_equivalence(self.root)
        self.path.write_bytes(original)

    def test_missing_record_after_introduction_fails(self):
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "missing after introduction"):
            equivalence.resolve_public_commit(self.root, self.anchor["closureCommit"])

    def test_tag_only_target_requires_the_exact_annotated_tag(self):
        item, entry = self.tag_entry()
        ref = f"refs/tags/{item['newName']}"
        self.assertEqual(equivalence.resolve_public_commit(self.root, entry["old"]), entry["new"])
        for replacement in ("absent", "lightweight", "recreated"):
            with self.subTest(replacement=replacement):
                self.git("update-ref", "-d", ref)
                if replacement == "lightweight":
                    self.git("update-ref", ref, item["newCommit"])
                elif replacement == "recreated":
                    self.git("tag", "-a", item["newName"], item["newCommit"], "-m", "Counterfeit")
                with self.assertRaisesRegex(ValueError, "not in public ancestry"):
                    equivalence.resolve_public_commit(self.root, entry["old"])
                self.git("update-ref", ref, item["newTagObject"])

    def test_local_original_object_or_replacement_cannot_change_the_route(self):
        closure = self.anchor["closureCommit"]
        expected = self.entries[closure]["new"]
        head = self.git("rev-parse", "HEAD")
        self.git("replace", expected, head)
        self.assertEqual(equivalence.resolve_public_commit(self.root, closure), expected)
        with patch.object(equivalence, "_git", wraps=equivalence._git) as calls:
            equivalence.resolve_public_commit(self.root, closure)
        self.assertFalse(any(closure in " ".join(call.args[1:]) for call in calls.call_args_list),
                         "the original identity must never be dereferenced")


if __name__ == "__main__":
    unittest.main()
