# SPDX-License-Identifier: AGPL-3.0-only

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import validate_repository as validator


class LinkTests(unittest.TestCase):
    def test_anchors(self):
        anchors = validator.markdown_anchors("# Example!\n## Example!\n```\n# Hidden\n```\n## A — B\n")
        self.assertEqual(anchors, {"example", "example-1", "a--b"})

    def test_valid_and_missing_local_anchors(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "one.md").write_text("# One\n[valid](two.md#two)\n[bad](two.md#missing)\n[self](#one)\n")
            (root / "two.md").write_text("# Two\n")
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_markdown_links(failures)
            self.assertEqual(len(failures), 1)
            self.assertIn("broken anchor", failures[0])

    def test_repository_invariants(self):
        failures = []
        validator.validate_required_files(failures)
        validator.validate_constitution(failures)
        validator.validate_ownership(failures)
        validator.validate_markdown_links(failures)
        validator.validate_licensing(failures)
        validator.validate_vendored_skills(failures)
        self.assertEqual(failures, [])


class VendoredSkillTests(unittest.TestCase):
    @staticmethod
    def make_skills(root: Path) -> None:
        for agent in (".agents", ".claude"):
            manifest = root / agent / "skills" / "VENDORED-SKILLS.md"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("# Vendored skills\n", encoding="utf-8")
            for folder, name in validator.VENDORED_SKILLS.items():
                directory = root / agent / "skills" / folder
                directory.mkdir(parents=True)
                (directory / "SKILL.md").write_text(
                    f"---\nname: {name}\ndescription: Test {name}.\n---\n\n"
                    "Read [reference](REFERENCE.md).\n", encoding="utf-8"
                )
                (directory / "REFERENCE.md").write_text("# Reference\n", encoding="utf-8")

    def test_complete_mirrors_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_skills(root)
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertEqual(failures, [])

    def test_changed_or_missing_mirror_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_skills(root)
            codex = root / ".agents/skills/api-design/SKILL.md"
            codex.write_text(codex.read_text(encoding="utf-8") + "Extra text.\n",
                             encoding="utf-8")
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertTrue(any("mirror differs: api-design/SKILL.md" in item
                                for item in failures), failures)
            (root / ".claude/skills/api-design/REFERENCE.md").unlink()
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertTrue(any("mirror differs: api-design/REFERENCE.md" in item
                                for item in failures), failures)

    def test_changed_or_missing_manifest_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_skills(root)
            claude_manifest = root / ".claude/skills/VENDORED-SKILLS.md"
            claude_manifest.write_text("# Different provenance\n", encoding="utf-8")
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertTrue(any("manifest mirror differs" in item for item in failures), failures)
            claude_manifest.unlink()
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertTrue(any("missing vendored skill manifest" in item for item in failures), failures)

    def test_bad_metadata_and_broken_link_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.make_skills(root)
            for agent in (".agents", ".claude"):
                directory = root / agent / "skills" / "api-design"
                entry = directory / "SKILL.md"
                entry.write_text(entry.read_text(encoding="utf-8").replace(
                    "name: designing-python-apis", "name: wrong-name"
                ), encoding="utf-8")
                (directory / "REFERENCE.md").unlink()
            failures = []
            with patch.object(validator, "ROOT", root):
                validator.validate_vendored_skills(failures)
            self.assertTrue(any("invalid vendored skill metadata" in item
                                for item in failures), failures)
            self.assertTrue(any("broken vendored skill link" in item
                                for item in failures), failures)
