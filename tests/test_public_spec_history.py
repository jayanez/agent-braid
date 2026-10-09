# SPDX-License-Identifier: AGPL-3.0-only
"""Negative and replay controls for restoring already-public reviewed tags."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import restore_public_spec_history as history


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args],
                                   stderr=subprocess.PIPE, text=True).strip()


class PublicSpecHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "source"
        self.source.mkdir()
        git(self.source, "init", "-b", "main")
        git(self.source, "config", "user.name", "Fixture")
        git(self.source, "config", "user.email", "fixture@example.invalid")
        (self.source / "file").write_text("root\n")
        git(self.source, "add", "file")
        git(self.source, "commit", "-m", "public root")
        self.public_root = git(self.source, "rev-parse", "HEAD")
        (self.source / "file").write_text("candidate\n")
        git(self.source, "commit", "-am", "reviewed candidate")
        self.candidate = git(self.source, "rev-parse", "HEAD")
        self.feature = "016-example"
        self.ref = f"refs/tags/spec-016-reviewed-{self.candidate[:7]}"
        git(self.source, "tag", "-a", self.ref.removeprefix("refs/tags/"),
            "-m", "already-public reviewed candidate")
        self.tag_object = git(self.source, "rev-parse", self.ref)
        self.root = Path(self.tmp.name) / "clone"
        git(self.source, "clone", "--no-tags", str(self.source), str(self.root))
        record = self.root / "specs" / self.feature / "assurance.json"
        record.parent.mkdir(parents=True)
        self.record = record
        record.write_text(json.dumps({
            "human_review": "approved",
            "review_record": f"specs/{self.feature}/review.json",
            "authority_snapshot": {"mode": "historical", "commit": self.candidate},
            "evidence_snapshot": {"mode": "historical", "commit": self.candidate},
        }))
        (record.parent / "review.json").write_text(json.dumps({"reviewedCommit": self.candidate}))
        self.override = patch.object(history, "ROOT", self.root)
        self.override.start()
        self.addCleanup(self.override.stop)

    def restore(self, tag_object=None, public_root=None):
        return history.restore_reviewed_tag(
            self.feature, self.candidate, tag_object or self.tag_object,
            public_root or self.public_root,
        )

    def test_restores_exact_annotated_tag_idempotently_without_worktree_changes(self):
        before = git(self.root, "status", "--porcelain")
        self.assertEqual(self.restore(), self.ref)
        self.assertEqual(self.restore(), self.ref)
        self.assertEqual(git(self.root, "rev-parse", self.ref), self.tag_object)
        self.assertEqual(git(self.root, "status", "--porcelain"), before)

    def test_rejects_wrong_public_identity_before_fetch(self):
        with self.assertRaisesRegex(ValueError, "public identity"):
            self.restore(tag_object="0" * 40)
        self.assertEqual(git(self.root, "tag", "-l"), "")

    def test_rejects_conflicting_local_tag_without_overwrite(self):
        git(self.root, "tag", self.ref.removeprefix("refs/tags/"), self.public_root)
        with self.assertRaisesRegex(ValueError, "local identity"):
            self.restore()
        self.assertEqual(git(self.root, "rev-parse", self.ref), self.public_root)

    def test_rejects_lightweight_tag_even_when_remote_identity_matches(self):
        git(self.source, "tag", "-d", self.ref.removeprefix("refs/tags/"))
        git(self.source, "tag", self.ref.removeprefix("refs/tags/"), self.candidate)
        with self.assertRaisesRegex(ValueError, "public identity|annotated tag"):
            self.restore(tag_object=self.candidate)

    def test_rejects_record_drift_and_different_root(self):
        original = self.record.read_text()
        self.record.write_text(original.replace('"approved"', '"pending"'))
        with self.assertRaisesRegex(ValueError, "pinned reviewed candidate"):
            self.restore()
        self.assertEqual(git(self.root, "tag", "-l"), "")
        self.record.write_text(original)
        with self.assertRaisesRegex(ValueError, "public root"):
            self.restore(public_root="f" * 40)

    def main_with(self, tags, advertisement=None):
        assurance = self.root / "spec-012-fixture.json"
        assurance.write_text(json.dumps({
            "authority_snapshot": {"mode": "historical", "commit": self.candidate},
            "evidence_snapshot": {"mode": "historical", "commit": self.candidate},
        }))
        original_git = history.git
        def public_origin(*args, **kwargs):
            if args == ("remote", "get-url", "origin"):
                return "https://github.com/jayanez/agent-braid.git"
            if advertisement and args[:3] == ("ls-remote", "--tags", "origin") \
                    and args[3] == advertisement[0]:
                return advertisement[1]
            return original_git(*args, **kwargs)
        with patch.object(history, "ASSURANCE", assurance), \
                patch.object(history, "REVIEWED_TAGS", tags), \
                patch.object(history, "git", side_effect=public_origin):
            return history.main()

    def test_late_preflight_failure_does_not_mutate_any_refs(self):
        before = git(self.root, "show-ref")
        tags = ((self.feature, self.candidate, self.tag_object),
                (self.feature, self.public_root, self.tag_object))
        with self.assertRaisesRegex(ValueError, "pinned reviewed candidate"):
            self.main_with(tags)
        self.assertEqual(git(self.root, "show-ref"), before)

    def test_main_restores_refs_atomically_and_rejects_existing_candidate_conflict(self):
        tags = ((self.feature, self.candidate, self.tag_object),)
        self.assertEqual(self.main_with(tags), 0)
        self.assertEqual(git(self.root, "rev-parse", history.REF), self.candidate)
        git(self.root, "update-ref", history.REF, self.public_root)
        before = git(self.root, "show-ref")
        with self.assertRaisesRegex(ValueError, "not overwritten"):
            self.main_with(tags)
        self.assertEqual(git(self.root, "show-ref"), before)

    def test_failed_batch_fetch_installs_no_earlier_refs(self):
        feature, candidate, tag_object = "018-missing", "b" * 40, "a" * 40
        record = self.root / "specs" / feature / "assurance.json"
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps({
            "human_review": "approved", "review_record": f"specs/{feature}/review.json",
            "authority_snapshot": {"mode": "historical", "commit": candidate},
            "evidence_snapshot": {"mode": "historical", "commit": candidate},
        }))
        (record.parent / "review.json").write_text(json.dumps({"reviewedCommit": candidate}))
        ref = f"refs/tags/spec-018-reviewed-{candidate[:7]}"
        advertised = f"{tag_object}\t{ref}\n{candidate}\t{ref}^{{}}"
        before = git(self.root, "show-ref")
        tags = ((self.feature, self.candidate, self.tag_object),
                (feature, candidate, tag_object))
        with self.assertRaisesRegex(ValueError, "fetch"):
            self.main_with(tags, advertisement=(ref, advertised))
        self.assertEqual(git(self.root, "show-ref"), before)


if __name__ == "__main__":
    unittest.main()
