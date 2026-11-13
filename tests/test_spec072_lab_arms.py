# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T009 lab script: cost first, nothing runs without --yes, refuses without a subscription token."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import spec072_lab_arms as lab


class LabArmsTests(unittest.TestCase):
    def call(self, *argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env or {'PATH': os.environ['PATH']}, clear=True), \
                mock.patch.object(lab, 'keychain_token', return_value=None), \
                mock.patch.object(lab.arm, 'run_arm', side_effect=AssertionError('must not run')), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lab.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_cost_only_without_yes(self):
        home = Path(tempfile.mkdtemp())
        code, out, err = self.call('--home', str(home / 'lab'))
        self.assertEqual(code, 0)
        cost = json.loads(out)['dryRun']
        self.assertEqual(cost['arms'], {'apo': {'rollouts': 60, 'optimizerCalls': 9},
                                        'gepa': {'rollouts': 105, 'optimizerCalls': 3}})
        self.assertEqual(cost['totalClaudeCodeCalls'], 177)
        self.assertEqual(cost['model'], 'claude-sonnet-5-5')
        self.assertIn('--yes', err)
        self.assertFalse((home / 'lab').exists())

    def test_refuses_without_token_or_with_a_paid_route(self):
        home = Path(tempfile.mkdtemp())
        code, _, err = self.call('--yes', '--home', str(home / 'lab'))
        self.assertEqual(code, 2)
        self.assertIn('CLAUDE_CODE_OAUTH_TOKEN', err)
        code, _, err = self.call('--yes', '--home', str(home / 'lab'),
                                 env={'PATH': os.environ['PATH'], 'ANTHROPIC_API_KEY': 'sk-ant-planted'})
        self.assertEqual(code, 2)
        self.assertNotIn('sk-ant-planted', err)
        self.assertFalse((home / 'lab').exists())


if __name__ == '__main__':
    unittest.main()
