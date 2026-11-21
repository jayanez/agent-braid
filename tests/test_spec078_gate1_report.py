# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T006 (REQ-008 / SC-008): the Gate 1 report re-scores a v2-test run and refuses a partial one.

Fake hosts only; no model is contacted. The reproduction test reads the owner's local lab run when it exists.
"""
import json
from pathlib import Path
import unittest

from agent_braid import lightning_config as config
from agent_braid import lightning_runner as runner
from scripts import spec078_gate1_report as gate1
from tests import test_spec078_heldout_v2 as base

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'specs/078-lightning-heldout-v2/evidence/gate1-a0.json'
REVIEW = ROOT / 'specs/078-lightning-heldout-v2/reviews/gate1-a0-zero-prompts.json'
CAUSES = ROOT / 'specs/078-lightning-heldout-v2/reviews/gate1-a0-causes.json'
DIAGNOSIS = ROOT / 'specs/078-lightning-heldout-v2/evidence/gate1-diagnosis.json'


class Gate1ReportTests(unittest.TestCase):
    def test_a_partial_run_is_refused(self):
        with base.tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / 'home'
            cfg = config.build({'rollout': {'repetitions': 3, 'hosts': ['claude-code']}, 'budget': {'maxRollouts': 3}})
            status = runner.run(home, cfg, fake_hosts=True, prompt_set='v2-test', environ=base.CLEAN_ENV)
            with self.assertRaises(SystemExit) as caught:
                gate1.report(home, status['runId'])
            self.assertIn('every prompt three times', str(caught.exception))

    def test_the_committed_report_matches_the_review_and_the_verdict_rule(self):
        record = json.loads(EVIDENCE.read_text())
        analysis = record['analysis']
        review = json.loads(REVIEW.read_text())
        self.assertEqual(set(review), set(analysis['zeroPrompts']))
        self.assertEqual(record['rollouts'], 300)
        self.assertEqual(analysis['od1'], 'misses' if analysis['zeroPrompts'] else 'meets')
        self.assertNotIn('prompt', json.dumps(record['failures']).replace('promptSet', ''))  # no prompt text

    def test_the_report_reproduces_from_the_lab_run(self):
        record = json.loads(EVIDENCE.read_text())
        if not (gate1.LAB / 'lightning/runs' / record['runId']).is_dir():
            self.skipTest('the lab run is local to the owner machine')
        self.assertEqual(gate1.report(gate1.LAB, record['runId'], json.loads(REVIEW.read_text())), record)


    def test_the_diagnosis_reproduces_and_refuses_an_unknown_cause(self):
        record = json.loads(EVIDENCE.read_text())
        if not (gate1.LAB / 'lightning/runs' / record['runId']).is_dir():
            self.skipTest('the lab run is local to the owner machine')
        causes = json.loads(CAUSES.read_text())
        self.assertEqual(gate1.diagnose(gate1.LAB, record['runId'], causes), json.loads(DIAGNOSIS.read_text()))
        with self.assertRaises(SystemExit):
            gate1.diagnose(gate1.LAB, record['runId'], {k: {**v, 'cause': 'other'} for k, v in causes.items()})

    def test_the_committed_diagnosis_covers_the_zero_prompts(self):
        diagnosis = json.loads(DIAGNOSIS.read_text())
        self.assertEqual(set(diagnosis['zeroPrompts']), set(json.loads(EVIDENCE.read_text())['analysis']['zeroPrompts']))
        self.assertEqual(sum(r['attempts'] for r in diagnosis['attemptsByRequestKind']), 300)


if __name__ == '__main__':
    unittest.main()
