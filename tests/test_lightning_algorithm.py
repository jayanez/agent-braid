# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-003 / SC-003: algorithm base and Baseline (fake hosts only; no model is contacted)."""
import os
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_algorithm as algorithm
from agent_braid import lightning_config as config
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.harness_host_claude import ENV_DENY
from agent_braid.lightning_resources import split_skill

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}


def profile():
    return config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code']}})


class Modified(algorithm.Baseline):
    def skill_text(self, cfg):
        return super().skill_text(cfg) + '\nExtra line.\n'


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def test_baseline_reproduces_spec071_fake_summary_and_records_seed(self):
        direct = runner.run(self.home, profile(), fake_hosts=True, environ=CLEAN_ENV, run_id='direct')
        expected = runner.report(self.home, direct['runId'])
        summary = algorithm.Baseline().run(self.home, profile(), fake_hosts=True, environ=CLEAN_ENV, run_id='base')
        self.assertEqual(summary['report']['hosts'], expected['hosts'])
        self.assertTrue(summary['report']['replayMatches'])
        self.assertEqual(summary['status']['completed'], direct['completed'])
        self.assertFalse(summary['executionAuthorization'])
        found = algorithm.candidates(self.home, 'base')
        record = found[summary['candidateSha256']]
        self.assertEqual(record.value['algorithm'], 'baseline')
        self.assertEqual(record.value['round'], 0)
        self.assertEqual(record.value['optimizerCalls'], [])
        full = record.value['devScore']['full']
        self.assertEqual(full['rollouts'], direct['completed'])
        host = expected['hosts']['claude-code']
        self.assertAlmostEqual(full['d4FirstAttempt'], host['firstAttempt'] / host['trials'], places=6)
        body = split_skill(algorithm.Baseline().skill_text(profile()))[1]
        self.assertEqual(store.RunStore(self.home, 'base').candidate_text(record.sha256), body)

    def test_modified_seed_changes_the_summary(self):
        plain = algorithm.Baseline().run(self.home, profile(), fake_hosts=True, environ=CLEAN_ENV, run_id='a')
        changed = Modified().run(self.home, profile(), fake_hosts=True, environ=CLEAN_ENV, run_id='b')
        self.assertNotEqual(plain['candidateSha256'], changed['candidateSha256'])

    def test_base_interface_is_abstract_and_registry_names_baseline(self):
        with self.assertRaises(NotImplementedError):
            algorithm.Algorithm().run(self.home, profile())
        self.assertIs(algorithm.ALGORITHMS['baseline'], algorithm.Baseline)


if __name__ == '__main__':
    unittest.main()
