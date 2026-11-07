# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T021: the overhead script measures only inside a temporary HOME and emits a receipt."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import analysis, system_one_shadow as shadow
from scripts import spec066_shadow_overhead as overhead


class OverheadScriptTests(unittest.TestCase):
    def test_fixtures_cover_the_sizes_and_every_pair_class(self):
        for size in overhead.SIZES:
            report = analysis.analyze(overhead.request(size))
            self.assertEqual(report['summary']['operationCount'], size)
        classes = analysis.analyze(overhead.request(12))['summary']['classifications']
        self.assertTrue(all(classes[name] > 0 for name in shadow.CLASSIFICATIONS), classes)

    def test_receipt_shape_and_home_restored(self):
        home = os.environ.get('HOME')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'receipt.json'
            self.assertEqual(overhead.main(['--samples', '2', '--warmup', '0', '--output', str(output)]), 0)
            receipt = json.loads(output.read_text())
        self.assertEqual(os.environ.get('HOME'), home)
        self.assertEqual(receipt['schema'], overhead.RECEIPT_SCHEMA)
        self.assertIs(receipt['executionAuthorization'], False)
        self.assertEqual(receipt['budgetReferenceMs'], 50.0)
        self.assertEqual({(c['operations'], c['store']) for c in receipt['cells']},
                         {(size, store) for size in overhead.SIZES for store in overhead.STORES})
        for cell in receipt['cells']:
            self.assertEqual(cell['worker']['samples'], 2)
            self.assertEqual(sum(cell['workerStatuses'].values()), 2)
            self.assertNotIn('not-stored', cell['workerStatuses'])
        self.assertEqual(receipt['refusalsDuringMeasurement'], {})

    def test_refuses_when_the_store_would_leave_the_temporary_root(self):
        outside = Path(tempfile.gettempdir()).resolve() / 'agent-braid-s1-overhead-outside-never-created'
        with patch.object(shadow, 'default_directory', return_value=outside):
            with self.assertRaises(SystemExit) as caught:
                overhead.measure(2, 0)
        self.assertIn('refused', str(caught.exception))
        self.assertFalse(outside.exists())


if __name__ == '__main__':
    unittest.main()
