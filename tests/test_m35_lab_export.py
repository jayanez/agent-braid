# SPDX-License-Identifier: AGPL-3.0-only
"""Filtered lab snapshots reject changing or unreviewed source bytes."""

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from scripts.m35_lab_export import export_snapshot, validate_manifest
from scripts.m35_lab_publish import publish_snapshot


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


class M35LabExportTests(unittest.TestCase):
    def _source(self, root: Path) -> tuple[Path, Path]:
        source = root / "source"
        source.mkdir()
        git(source, "init", "-b", "develop")
        git(source, "config", "user.email", "lab@example.invalid")
        git(source, "config", "user.name", "Lab Test")
        (source / "docs" / "adr").mkdir(parents=True)
        (source / "docs" / "adr" / "decision.md").write_text("Approved context\n", encoding="utf-8")
        (source / "private.txt").write_text("Never export this\n", encoding="utf-8")
        git(source, "add", ".")
        git(source, "commit", "-m", "source")
        blob = git(source, "rev-parse", "HEAD:docs/adr/decision.md")
        manifest = root / "allowlist.json"
        manifest.write_text(json.dumps({"format": "m35-lab-export-v1",
                                        "sourceRepo": "owner/source",
                                        "branches": {branch: {"files": {"docs/adr/decision.md": blob}}
                                                     for branch in ("main", "develop")}}), encoding="utf-8")
        return source, manifest

    def test_filtered_snapshot_contains_only_approved_file_and_provenance(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, manifest = self._source(root)
            output = root / "snapshot"
            result = export_snapshot(source, manifest, "develop", output, expected_repo="owner/source")
            self.assertEqual(result["sourceSha"], git(source, "rev-parse", "HEAD"))
            self.assertEqual((output / "docs/adr/decision.md").read_text(), "Approved context\n")
            self.assertFalse((output / "private.txt").exists())
            self.assertEqual(set(result["files"]), {"docs/adr/decision.md"})

    def test_source_change_blocks_sync_until_new_blob_is_reviewed(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, manifest = self._source(root)
            (source / "docs/adr/decision.md").write_text("New unreviewed context\n", encoding="utf-8")
            git(source, "add", ".")
            git(source, "commit", "-m", "change approved path")
            with self.assertRaisesRegex(ValueError, "approved content changed"):
                export_snapshot(source, manifest, "develop", root / "blocked")
            self.assertFalse((root / "blocked").exists())

    def test_path_escape_and_unlisted_branch_are_rejected(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            _, path = self._source(root)
            value = json.loads(path.read_text())
            value["branches"]["main"]["files"] = {"../private.txt": "a" * 40}
            with self.assertRaisesRegex(ValueError, "escapes"):
                validate_manifest(value)
            value["branches"]["main"]["files"] = {"docs/adr/decision.md": "a" * 40}
            value["branches"]["feature"] = value["branches"]["main"]
            with self.assertRaisesRegex(ValueError, "both main and develop"):
                validate_manifest(value)

    def test_publish_creates_disposable_branch_without_source_history(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, manifest = self._source(root)
            snapshot = root / "snapshot"
            export_snapshot(source, manifest, "develop", snapshot)
            bare = root / "lab.git"
            subprocess.run(["git", "init", "--bare", str(bare)], check=True,
                           capture_output=True, text=True)
            control = root / "control"
            control.mkdir()
            git(control, "init", "-b", "control")
            git(control, "config", "user.email", "lab@example.invalid")
            git(control, "config", "user.name", "Lab Test")
            (control / "README.md").write_text("Control only\n")
            git(control, "add", ".")
            git(control, "commit", "-m", "control")
            git(control, "remote", "add", "origin", str(bare))
            git(control, "push", "-u", "origin", "control")
            first = publish_snapshot(control, snapshot, "develop")
            self.assertTrue(first["changed"])
            self.assertEqual(git(control, "ls-tree", "-r", "--name-only", first["labCommit"]),
                             "docs/adr/decision.md\nlab-snapshot.json")
            self.assertNotEqual(first["labCommit"], git(source, "rev-parse", "HEAD"))
            second = publish_snapshot(control, snapshot, "develop")
            self.assertFalse(second["changed"])

    def test_symlink_in_snapshot_is_rejected_before_publication(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, manifest = self._source(root)
            snapshot = root / "snapshot"
            export_snapshot(source, manifest, "develop", snapshot)
            (snapshot / "extra.md").symlink_to(root / "outside.md")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                publish_snapshot(root, snapshot, "develop")
