# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T008 (REQ-009): the v4 gate report counts invocation steps and matches its committed evidence.

No model is contacted. The reproduction test reads the owner's local lab run when it exists.
"""
import json
from pathlib import Path
import unittest

from scripts import spec079_gate_report as gate

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

    def test_no_prompt_or_model_text_is_recorded(self):
        text = json.dumps(self.record)
        for key in ('"prompt"', '"response"', '"transcript"'):
            self.assertNotIn(key, text)

    def test_the_report_reproduces_from_the_lab_run(self):
        if not (gate.LAB / 'lightning/runs' / self.record['runId']).is_dir():
            self.skipTest('the lab run is local to the owner machine')
        self.assertEqual(gate.report(gate.LAB, self.record['runId']), self.record)


if __name__ == '__main__':
    unittest.main()
