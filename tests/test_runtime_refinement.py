# SPDX-License-Identifier: AGPL-3.0-only
"""Owned disposable controls for proposals, never actual source promotion."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_runtime_refinement import (VERSION, InvalidRefinement, assess_promotion,
                                              inventory_isolation, main, simulate_external)


class RuntimeRefinementTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.repo = self.root / 'repo'
        self.git('init', '-q', str(self.repo), cwd=self.root)
        self.git('config', 'user.name', 'Synthetic')
        self.git('config', 'user.email', 'synthetic@example.invalid')
        (self.repo / 'a.txt').write_text('base\n')
        self.git('add', 'a.txt')
        self.git('commit', '-qm', 'base')
        self.old = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.git('branch', 'target')
        self.input = {'version': VERSION, 'capability': 'promotion', 'repository': str(self.repo),
                      'targetRef': 'refs/heads/target', 'expectedOld': self.old,
                      'resultTree': self.tree, 'grant': None, 'fault': 'none'}

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-C', str(cwd or self.repo), *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def snapshot(self):
        return (self.git('show-ref'), self.git('status', '--porcelain'),
                (self.repo / 'a.txt').read_bytes(), (self.repo / '.git/index').read_bytes())

    def test_proposal_preserves_source_and_never_verifies(self):
        before = self.snapshot()
        report = assess_promotion(self.input)
        self.assertEqual(report['status'], 'proposal-only')
        self.assertEqual(report['consumerVerification'], 'not-performed')
        self.assertFalse(report['executionAuthorization'])
        self.assertFalse(report['sourcePromotion'])
        self.assertEqual(self.snapshot(), before)

    def test_stale_dirty_attached_and_unknown_ref(self):
        candidate = copy.deepcopy(self.input)
        candidate['expectedOld'] = '0' * 40
        self.assertIn('stale-target', assess_promotion(candidate)['reasons'])
        (self.repo / 'untracked').write_text('dirty')
        before = self.snapshot()
        self.assertIn('dirty-worktree', assess_promotion(self.input)['reasons'])
        self.assertEqual(self.snapshot(), before)
        self.git('checkout', '-q', 'target')
        self.assertIn('attached-target', assess_promotion(self.input)['reasons'])
        candidate = copy.deepcopy(self.input)
        candidate['targetRef'] = 'refs/heads/missing'
        self.assertIn('unknown-repository-state', assess_promotion(candidate)['reasons'])

    def test_other_worktree_dirty_and_target_attachment(self):
        self.git('worktree', 'add', '-q', str(self.root / 'linked'), 'target')
        (self.root / 'linked/a.txt').write_text('changed')
        report = assess_promotion(self.input)
        self.assertIn('attached-target', report['reasons'])
        self.assertIn('dirty-worktree', report['reasons'])

    def test_existing_grants_unknown_fields_and_objects_rejected(self):
        for grant in ({'scope': 'private-run-only'}, {'scope': 'promotion'}, True):
            value = {**self.input, 'grant': grant}
            with self.assertRaises(InvalidRefinement):
                assess_promotion(value)
        with self.assertRaises(InvalidRefinement):
            assess_promotion({**self.input, 'executionAuthorization': True})
        value = {**self.input, 'resultTree': self.old}
        self.assertIn('result-is-not-tree', assess_promotion(value)['reasons'])
        for ref in ('--help', 'refs/heads/../target', 'refs/tags/target'):
            with self.assertRaises(InvalidRefinement):
                assess_promotion({**self.input, 'targetRef': ref})

    def test_faults_classify_without_cas_or_retry(self):
        before = self.snapshot()
        for fault, expected in (('before-cas', 'no-publication-proposed'),
                                ('after-cas', 'published-effect-would-require-reconciliation'),
                                ('unknown', 'ambiguous-do-not-retry')):
            report = assess_promotion({**self.input, 'fault': fault})
            self.assertEqual(report['recoveryDisposition'], expected)
        self.assertEqual(self.snapshot(), before)

    def test_isolation_inventory_launches_nothing(self):
        with patch('subprocess.run', side_effect=AssertionError('must not launch')):
            report = inventory_isolation()
        self.assertEqual(report['status'], 'NO-GO')
        self.assertEqual(report['probesExecuted'], 0)
        self.assertEqual(report['enforcement'], 'not-verified')
        self.assertFalse(report['executionAuthorization'])

    def test_external_retains_partial_effect_and_every_attempt(self):
        attempts = [{'attemptId': 'a1', 'operationId': 'op', 'idempotencyKey': 'k',
                     'outcome': 'failure-after-effect', 'effect': True},
                    {'attemptId': 'a2', 'operationId': 'op', 'idempotencyKey': 'k',
                     'outcome': 'ambiguous-timeout', 'effect': False}]
        before = copy.deepcopy(attempts)
        report = simulate_external(attempts)
        self.assertEqual(report['attempts'], before)
        self.assertEqual(report['visibleEffects'], 1)
        self.assertEqual(report['status'], 'unresolved')
        self.assertFalse(report['automaticRetry'])
        self.assertFalse(report['compensationIsInverse'])
        self.assertEqual(attempts, before)
        with self.assertRaises(InvalidRefinement):
            simulate_external([attempts[0], attempts[0]])
        with self.assertRaises(InvalidRefinement):
            simulate_external([{**attempts[0], 'effect': False}])

    def test_cli_explicit_output_collision_and_fifo_controls(self):
        fixture = self.root / 'input.json'
        fixture.write_text(json.dumps(self.input))
        output = self.root / 'assessment.json'
        with patch('builtins.print'):
            self.assertEqual(main(['--capability', 'promotion', '--input', str(fixture), '--output', str(output)]), 0)
            before = output.read_bytes()
            self.assertEqual(main(['--capability', 'promotion', '--input', str(fixture), '--output', str(output)]), 2)
            self.assertEqual(output.read_bytes(), before)
            import os
            fifo = self.root / 'fifo'
            os.mkfifo(fifo)
            self.assertEqual(main(['--capability', 'promotion', '--input', str(fifo)]), 2)
        self.assertFalse(json.loads(before)['executionAuthorization'])

    def test_cli_duplicate_member_and_sensitive_error_sanitized(self):
        fixture = self.root / 'input.json'
        fixture.write_text('{"private-secret":"SENTINEL", "private-secret":"SENTINEL"}')
        with patch('builtins.print') as output:
            self.assertEqual(main(['--capability', 'promotion', '--input', str(fixture)]), 2)
        self.assertNotIn('SENTINEL', str(output.call_args_list))


if __name__ == '__main__':
    unittest.main()
