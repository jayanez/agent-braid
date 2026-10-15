# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import agent_braid
from scripts import reproduce_forecast_cost_supervised as supervisor
from scripts.reproduce_forecast_cost import reproduce


class SupervisedCostTests(unittest.TestCase):
    def child(self, args, **kwargs):
        self.assertEqual('-I', args[1])
        self.assertEqual('reproduce_forecast_cost.py', Path(args[2]).name)
        self.assertTrue(kwargs['start_new_session'])
        directory = Path(args[4])
        directory.mkdir(mode=0o700)
        with patch('scripts.reproduce_forecast_cost.sysconfig.get_path',
                   return_value=str(Path(agent_braid.__file__).resolve().parent.parent)):
            self.assertEqual(0, reproduce(directory))
        return Mock(wait=Mock(return_value=0), poll=Mock(return_value=0), returncode=0)

    def test_parent_covers_inner_publication_and_preserves_remaining_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'new'
            with patch.object(supervisor.subprocess, 'Popen', side_effect=self.child):
                self.assertEqual(0, supervisor.supervise(output))
            record = json.loads((output / 'supervisor.json').read_bytes())
            self.assertTrue(record['cleanupConfirmed'])
            self.assertGreater(record['wallNsThroughInnerPublicationReadback'], 0)
            self.assertIn('overlap-inner-do-not-add', record['cpuScope'])
            self.assertIn('this-terminal-receipt-publication-after-boundary', record['gaps'])
            self.assertFalse(record['fullDeploymentCostAccepted'])
            for name, digest in record['innerReceiptSha256'].items():
                self.assertEqual(digest, hashlib.sha256((output / 'inner' / name).read_bytes()).hexdigest())

    def test_existing_output_cannot_dispatch_or_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(supervisor.subprocess, 'Popen') as child:
            with self.assertRaises(FileExistsError):
                supervisor.supervise(tmp)
            child.assert_not_called()
            self.assertEqual([], list(Path(tmp).iterdir()))

    def test_missing_receipts_are_retained_as_failure_with_unconfirmed_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'failed'
            child = Mock(wait=Mock(return_value=2), poll=Mock(return_value=2), returncode=2)
            with patch.object(supervisor.subprocess, 'Popen', return_value=child):
                self.assertEqual(2, supervisor.supervise(output))
            record = json.loads((output / 'supervisor.json').read_bytes())
            self.assertFalse(record['cleanupConfirmed'])
            self.assertEqual({}, record['innerReceiptSha256'])
            self.assertFalse(record['modelLoaded'])

    def test_failed_launch_preserves_terminal_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'failed'
            with patch.object(supervisor.subprocess, 'Popen', side_effect=OSError('synthetic launch failure')):
                self.assertEqual(2, supervisor.supervise(output))
            self.assertEqual('OSError', json.loads((output / 'supervisor.json').read_bytes())['error'])

    def test_unreapable_child_keeps_failure_and_does_not_confirm_cleanup(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'timeout'
            child = Mock(pid=123456, poll=Mock(return_value=None), returncode=None,
                         wait=Mock(side_effect=subprocess.TimeoutExpired('synthetic-owned-child', 1)))
            with patch.object(supervisor.subprocess, 'Popen', return_value=child), patch.object(supervisor.os, 'killpg') as kill:
                self.assertEqual(2, supervisor.supervise(output))
            self.assertEqual(3, kill.call_count)
            record = json.loads((output / 'supervisor.json').read_bytes())
            self.assertFalse(record['cleanupConfirmed'])
            self.assertEqual('synthetic-child-timeout', record['error'])
            self.assertEqual('owned-child-reap-unconfirmed', record['cleanupError'])
