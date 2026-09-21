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
        self.assertEqual(failures, [])
