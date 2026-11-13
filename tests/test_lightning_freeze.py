# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-001 / SC-001: the evaluation protocol is frozen by hash before any held-out rollout."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from agent_braid import lightning_config as config
from agent_braid import lightning_runner as runner

ROOT = runner.checkout_root()


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for relative in (runner.PROTOCOL, runner.PROTOCOL_FREEZE):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, self.root / relative)

    def tearDown(self):
        self.tmp.cleanup()

    def test_committed_freeze_matches_the_protocol_and_the_development_evidence(self):
        freeze = json.loads((ROOT / runner.PROTOCOL_FREEZE).read_text())
        self.assertEqual(runner.check_protocol_freeze(ROOT), freeze['protocolSha256'])
        evidence = freeze['developmentEvidence']
        self.assertEqual(hashlib.sha256((ROOT / evidence['path']).read_bytes()).hexdigest(), evidence['sha256'])
        self.assertFalse(freeze['heldOutOpened'])
        self.assertFalse(freeze['executionAuthorization'])

    def test_an_edited_protocol_is_refused(self):
        path = self.root / runner.PROTOCOL
        path.write_text(path.read_text() + '\nA late change.\n')
        with self.assertRaises(runner.RunnerError) as caught:
            runner.check_protocol_freeze(self.root)
        self.assertEqual(caught.exception.code, 'protocol-hash-mismatch')

    def test_a_missing_freeze_is_refused(self):
        (self.root / runner.PROTOCOL_FREEZE).unlink()
        with self.assertRaises(runner.RunnerError) as caught:
            runner.check_protocol_freeze(self.root)
        self.assertEqual(caught.exception.code, 'protocol-not-frozen')

    def test_a_held_out_run_with_an_edited_protocol_is_refused_before_launch(self):
        path = self.root / runner.PROTOCOL
        path.write_text(path.read_text() + '\nA late change.\n')
        home = self.root / 'home'
        with mock.patch.object(runner, 'checkout_root', return_value=self.root), \
                mock.patch.object(runner, 'parent_gate', side_effect=AssertionError('launched')):
            with self.assertRaises(runner.RunnerError) as caught:
                runner.run(home, config.build({'algorithm': {'name': 'baseline'}}), prompt_set='held-out',
                           fake_hosts=True, environ={})
        self.assertEqual(caught.exception.code, 'protocol-hash-mismatch')
        self.assertFalse(home.exists())


if __name__ == '__main__':
    unittest.main()
