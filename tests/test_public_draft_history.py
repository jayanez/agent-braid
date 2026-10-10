# SPDX-License-Identifier: AGPL-3.0-only
"""Exact public draft retention is historical validation, never approval."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import validate_spec_kit as gates
from scripts import publication, closure_anchors
from scripts import restore_public_spec_history as history
from scripts.restore_public_spec_history import PRESERVED_DRAFT_TAGS


class PublicDraftHistoryTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="braid-public-draft-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "repo"
        shutil.copytree(gates.ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", ".venv", ".venv-speckit", "__pycache__"))
        shutil.copytree(gates.ROOT / ".git", self.root / ".git")
        self.relative, self.ref, self.candidate, self.tag_object = PRESERVED_DRAFT_TAGS[0]
        self.path = self.root / self.relative
        self.record = json.loads(self.path.read_text())

    def git(self, *args, input_text=None):
        return subprocess.check_output(
            ["git", "-C", str(self.root), "-c", "user.name=Fixture",
             "-c", "user.email=fixture@example.invalid", *args],
            input=input_text, text=True, stderr=subprocess.PIPE).strip()

    def matches(self, relative=None, path=None, record=None):
        return gates._matches_preserved_draft_tag(
            self.root, relative or self.relative, path or self.path,
            record if record is not None else json.loads(self.path.read_text()))

    def test_exact_public_squashed_candidate_uses_strict_validation_without_approval(self):
        frozen = self.record["evidence_snapshot"]["commit"]
        result = subprocess.run(
            ["git", "-C", str(self.root), "merge-base", "--is-ancestor", frozen, "HEAD"],
            capture_output=True, check=False)
        self.assertNotEqual(result.returncode, 0)
        original = self.path.read_bytes()
        self.assertTrue(self.matches())
        with patch.object(gates, "validate_record", wraps=gates.validate_record) as strict:
            gates.validate_portable_record(self.root, self.path)
        strict.assert_called_once_with(self.root.resolve(), self.path)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.record["stage"], "draft")
        self.assertEqual(self.record["human_review"], "pending")

    def test_absent_lightweight_and_recreated_annotated_tags_fail_closed(self):
        for replacement in ("absent", "lightweight", "recreated"):
            with self.subTest(replacement=replacement):
                self.git("update-ref", "-d", self.ref)
                if replacement == "lightweight":
                    self.git("update-ref", self.ref, self.candidate)
                elif replacement == "recreated":
                    self.git("tag", "-a", self.ref.removeprefix("refs/tags/"),
                             self.candidate, "-m", "Different annotated object, same candidate")
                    self.assertNotEqual(self.git("rev-parse", self.ref), self.tag_object)
                self.assertFalse(self.matches())
                with self.assertRaises(ValueError):
                    gates.validate_portable_record(self.root, self.path)
                self.git("update-ref", self.ref, self.tag_object)

    def test_one_byte_drift_and_invented_approval_cannot_use_the_pin(self):
        original = self.path.read_bytes()
        self.path.write_bytes(original + b"\n")
        self.assertFalse(self.matches())
        for field, value in (("human_review", "approved"), ("stage", "validated")):
            with self.subTest(field=field):
                altered = dict(self.record)
                altered[field] = value
                self.path.write_text(json.dumps(altered))
                self.assertFalse(self.matches())
                with self.assertRaises(ValueError):
                    gates.validate_portable_record(self.root, self.path)
                self.assertEqual(json.loads(self.path.read_text())[field], value)
        self.path.write_bytes(original)

    def test_another_feature_and_nonhistorical_snapshots_are_not_allowlisted(self):
        self.assertFalse(self.matches(relative="specs/999-other/assurance.json"))
        for field in ("authority_snapshot", "evidence_snapshot"):
            altered = json.loads(self.path.read_text())
            altered[field] = {"mode": "current", "commit": None}
            self.assertFalse(self.matches(record=altered))

    def test_local_counterfeit_review_cannot_promote_the_pending_draft(self):
        altered = dict(self.record)
        altered["human_review"] = "approved"
        altered["review_record"] = "specs/019-native-predictor/local-review.json"
        frozen = altered["authority_snapshot"]["commit"]
        (self.root / altered["review_record"]).write_text(json.dumps({"reviewedCommit": frozen}))
        self.path.write_text(json.dumps(altered))
        ref = f"refs/tags/spec-019-reviewed-{frozen[:7]}"
        self.git("tag", "-a", ref.removeprefix("refs/tags/"), frozen,
                 "-m", "Local counterfeit approval")
        with self.assertRaises(ValueError):
            gates.validate_portable_record(self.root, self.path)
        self.assertFalse(self.matches())

    def test_recreated_reviewed_tag_cannot_inherit_public_approval(self):
        feature, frozen, tag_object = history.REVIEWED_TAGS[0]
        ref = f"refs/tags/spec-{feature[:3]}-reviewed-{frozen[:7]}"
        path = self.root / f"specs/{feature}/assurance.json"
        gates.validate_portable_record(self.root, path)
        self.git("update-ref", "-d", ref)
        self.git("tag", "-a", ref.removeprefix("refs/tags/"), frozen,
                 "-m", "Same candidate, counterfeit public approval tag")
        self.assertNotEqual(self.git("rev-parse", ref), tag_object)
        with self.assertRaises(ValueError):
            gates.validate_portable_record(self.root, path)

    def test_reviewed_assurance_and_review_bytes_cannot_inherit_public_approval(self):
        for feature, _, _ in history.REVIEWED_TAGS:
            path = self.root / f"specs/{feature}/assurance.json"
            review = self.root / json.loads(path.read_text())["review_record"]
            gates.validate_portable_record(self.root, path)
            for target in (path, review):
                with self.subTest(feature=feature, target=target.name):
                    original = target.read_bytes()
                    target.write_bytes(original + b"\n")
                    with self.assertRaises(ValueError):
                        gates.validate_portable_record(self.root, path)
                    target.write_bytes(original)
            gates.validate_portable_record(self.root, path)

    def test_missing_and_nonancestor_snapshot_commits_fail_closed(self):
        for field in ("authority_snapshot", "evidence_snapshot"):
            for commit in ("f" * 40, self.git("rev-parse", "HEAD")):
                with self.subTest(field=field, commit=commit):
                    altered = json.loads(self.path.read_text())
                    altered[field]["commit"] = commit
                    self.assertFalse(self.matches(record=altered))

    def test_reviewed_byte_drift_is_terminal_before_ancestry_or_fallback(self):
        feature, frozen, _ = history.REVIEWED_TAGS[0]
        path = self.root / f"specs/{feature}/assurance.json"
        path.write_bytes(path.read_bytes() + b"\n")
        # Even making the actual reviewed commit a real HEAD ancestor must not
        # let changed retained approval metadata use a different validation route.
        self.git("update-ref", "HEAD", frozen)
        with patch.object(gates, "validate_record") as strict, \
                patch.object(gates, "_matches_reviewed_candidate_tag") as reviewed:
            with self.assertRaisesRegex(ValueError, "Published reviewed metadata changed"):
                gates.validate_portable_record(self.root, path)
        strict.assert_not_called()
        reviewed.assert_not_called()

    def test_additional_root_cannot_use_the_public_pin(self):
        tree = self.git("mktree", input_text="")
        commit = self.git("commit-tree", tree, "-m", "Disconnected fixture root")
        self.git("update-ref", "refs/heads/disconnected-fixture", commit)
        self.assertFalse(self.matches())
        with self.assertRaisesRegex(ValueError, "exactly one clean root"):
            gates.check(self.root)

    def test_strict_evidence_failure_propagates_without_portable_fallback(self):
        with patch.object(gates, "validate_record", side_effect=ValueError("corrupt bound evidence")):
            with self.assertRaisesRegex(ValueError, "corrupt bound evidence"):
                gates.validate_portable_record(self.root, self.path)

    def test_replaced_head_cannot_bypass_missing_pinned_tag(self):
        self.git("update-ref", "-d", self.ref)
        self.git("replace", self.git("rev-parse", "HEAD"), self.candidate)
        with self.assertRaises(ValueError):
            gates.validate_portable_record(self.root, self.path)
        self.assertEqual(json.loads(self.path.read_text())["human_review"], "pending")

    def test_grafted_head_cannot_bypass_missing_pinned_tag(self):
        self.git("update-ref", "-d", self.ref)
        graft = self.root / ".git/info/grafts"
        graft.write_text(f"{self.git('rev-parse', 'HEAD')} {self.candidate}\n")
        with self.assertRaises(ValueError):
            gates.validate_portable_record(self.root, self.path)
        frozen = self.record["evidence_snapshot"]["commit"]
        self.assertNotEqual(publication._git(
            self.root, "merge-base", "--is-ancestor", frozen, "HEAD",
            allow_failure=True).returncode, 0)

    def test_all_public_history_helpers_use_the_canonical_graph(self):
        canonical = self.git("rev-list", "--parents", "-n", "1", "HEAD")
        head = self.git("rev-parse", "HEAD")
        self.git("replace", head, self.candidate)
        (self.root / ".git/info/grafts").write_text(f"{head} {self.candidate}\n")
        args = ("rev-list", "--parents", "-n", "1", "HEAD")
        self.assertEqual(gates.git(self.root, *args).decode().strip(), canonical)
        self.assertEqual(publication._git(self.root, *args).stdout.decode().strip(), canonical)
        self.assertEqual(closure_anchors._git(self.root, *args).decode().strip(), canonical)
        with patch.object(history, "ROOT", self.root):
            self.assertEqual(history.git(*args), canonical)

    def test_replacement_objects_cannot_rewrite_frozen_evidence(self):
        frozen = self.record["evidence_snapshot"]["commit"]
        public_root = self.git("rev-list", "--max-parents=0", "HEAD")
        self.git("replace", frozen, public_root)
        self.assertTrue(self.matches())
        gates.validate_portable_record(self.root, self.path)
        self.assertEqual(json.loads(self.path.read_text())["human_review"], "pending")


if __name__ == "__main__":
    unittest.main()
