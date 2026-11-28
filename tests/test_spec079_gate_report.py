# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T008 (REQ-009): the v4 gate report counts invocation steps and matches its committed evidence.

No model is contacted. The reproduction test reads the owner's local lab run when it exists.
"""
import json
from pathlib import Path
import unittest

from agent_braid import lightning_store as store
from scripts import spec079_gate_report as gate
from tests.test_spec079_runner import V4Root

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'specs/079-kind-choice-tool-fix/evidence/gate-v4-report.json'
PREFIX = 'mcp__plugin_agent-braid_agent-braid__'


class InvocationCountTests(unittest.TestCase):
    def test_each_step_is_counted_once_per_rollout(self):
        counts = gate.invocation([
            [],
            ['ToolSearch'],
            ['ToolSearch', 'Skill', PREFIX + 'analyze-work', PREFIX + 'analyze-work'],
            ['Skill', PREFIX + 'analyze'],
        ])
        self.assertEqual(counts, {'tracedRollouts': 4, 'noToolCall': 1, 'toolSearch': 2, 'skill': 2,
                                  'analyzeWork': 1})

    def test_analyze_is_not_counted_as_analyze_work(self):
        self.assertEqual(gate.invocation([[PREFIX + 'analyze']])['analyzeWork'], 0)


class CommittedReportTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(EVIDENCE.read_text())

    def test_the_counts_are_consistent(self):
        record = self.record
        self.assertEqual(record['rollouts'], 300)
        self.assertEqual(record['missingResults'], [])
        self.assertEqual(sum(record['firstRequestKind'].values()), 300)
        steps = record['invocation']
        self.assertEqual(steps['tracedRollouts'], 300)
        self.assertEqual(steps['analyzeWork'], 300 - record['firstRequestKind']['none'])
        self.assertLessEqual(steps['noToolCall'], record['firstRequestKind']['none'])
        self.assertEqual(len(record['configDigest']), 64)
        self.assertEqual(sorted(record['zeroPrompts']), sorted(record['analysis']['zeroPrompts']))

    def test_failures_carry_only_ids_classes_and_bounded_scorer_reasons(self):
        for failure in self.record['failures']:
            self.assertEqual(set(failure), {'rolloutId', 'class', 'reason'})
            self.assertLessEqual(len(failure['reason']), 400)

    def test_the_report_reproduces_from_the_lab_run(self):
        if not (gate.LAB / 'lightning/runs' / self.record['runId']).is_dir():
            self.skipTest('the lab run is local to the owner machine')
        review = self.record['analysis']['review'] or None
        self.assertEqual(gate.report(gate.LAB, self.record['runId'], review), self.record)


class FakeRunReportTests(V4Root):
    def test_a_fake_run_is_reported_whole_and_a_wrong_review_is_refused(self):
        status = self.run_fake()
        record = gate.report(self.home, status['runId'])
        self.assertEqual(record['rollouts'], 300)
        self.assertEqual(record['missingResults'], [])
        self.assertEqual(sum(record['firstRequestKind'].values()), 300)
        self.assertEqual(record['configDigest'], store.RunStore(self.home, status['runId']).manifest()['configDigest'])
        self.assertEqual(len(record['failures']), 300 - round(record['analysis']['trialRate'] * 300))
        self.assertLessEqual(record['invocation']['tracedRollouts'], 300)
        with self.assertRaises(SystemExit):
            gate.report(self.home, status['runId'], {'V4T-000': {'classification': 'model'}})

    def test_a_run_without_results_is_refused(self):
        store.RunStore(self.home, 'run-empty').create(config_digest='0' * 64)
        with self.assertRaises(SystemExit) as caught:
            gate.report(self.home, 'run-empty')
        self.assertIn('no results', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
