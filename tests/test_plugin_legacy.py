# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
import tempfile
import unittest
from agent_braid import plugin_legacy
from agent_braid.tooling_install import Selection, plan, apply


class PluginLegacyTests(unittest.TestCase):
    def test_migration_uses_old_receipt_and_preserves_modified_skills(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'repo'; source.mkdir()
            results = root / 'results'; results.mkdir()
            destination = root / 'legacy'
            selected = Selection(host='claude', scope='user', source_root=source, result_root=results, destination=destination)
            transaction = plan(selected, source_checkout=True)
            apply(transaction, preview_digest=transaction.preview()['previewDigest'])
            skill = destination / 'skills/agent-braid-analyze/SKILL.md'
            skill.write_text('user modified instructions')
            receipt = destination / 'receipts/agent-braid.json'
            found = plugin_legacy.inventory('claude', destination)
            self.assertEqual(len(found['receipts']), 1)
            preview = plugin_legacy.migrate('claude', receipt, destination=destination, source_checkout=True)
            plugin_legacy.migrate('claude', receipt, destination=destination, source_checkout=True,
                                  do_apply=True, digest=preview['previewDigest'])
            self.assertEqual(skill.read_text(), 'user modified instructions')
            self.assertTrue(source.exists() and results.exists())
            self.assertEqual(json.loads(receipt.read_text())['state'], 'residual')
