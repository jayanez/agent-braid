# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T013 (REQ-014 / SC-014): the fresh v3 test split, its build checks, Gate 0 and the runner's v3-test set.

Fake hosts only; no model is contacted.
"""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid import lightning_heldout_v3 as v3
from agent_braid import lightning_runner as runner
from scripts import spec078_build_set as v2set
from scripts import spec078_build_v3 as build
from tests import test_spec078_heldout_v2 as base

ROOT = Path(__file__).resolve().parents[1]
COMMIT = '0' * 40


def committed() -> dict:
    return json.loads((ROOT / v3.PROMPT_FILES['v3-test']).read_text())


class BuildTests(unittest.TestCase):
    def test_the_committed_split_is_a_fresh_build(self):
        self.assertEqual((ROOT / v3.PROMPT_FILES['v3-test']).read_text(), build.render(build.build()))

    def test_the_split_has_the_ten_classes_and_its_provenance(self):
        data = committed()
        self.assertEqual(len(data['cases']), 100)
        self.assertEqual({c['class'] for c in data['cases']}, set(v2set.CLASSES))
        self.assertEqual(data['generator'], {'script': build.GENERATOR, 'seed': build.SEED,
                                             'classPlan': 'spec078_build_set._plan, ten classes'})

    def test_a_case_copied_from_v2_is_refused(self):
        data = committed()
        v2_case = json.loads((v2set.OUT / 'test.json').read_text())['cases'][0]
        data['cases'][0] = {**v2_case, 'id': 'V3T-001', 'prompt': v2set.prompt(v2_case['facts'], build.STYLE)}
        with self.assertRaisesRegex(v2set.SetError, 'already used by a v2 split'):
            build.check(data)

    def test_a_prompt_sharing_a_window_with_v2_is_refused(self):
        data = committed()
        fake_v2 = {'test': [{'prompt': data['cases'][5]['prompt'], 'facts': {'kind': 'git', 'base': 'x', 'units': []}}]}
        with self.assertRaisesRegex(v2set.SetError, 'shares an 8-word window with a v2 split'):
            build.check(data, v2=fake_v2)

    def test_a_prompt_sharing_a_window_with_spec069_or_the_skill_is_refused(self):
        data = committed()
        sample = data['cases'][7]['prompt']
        with self.assertRaisesRegex(v2set.SetError, 'a SPEC-069 prompt'):
            build.check(data, v1=[sample])
        with self.assertRaisesRegex(v2set.SetError, 'the analyze skill'):
            build.check(data, v1=[], skill_text=sample)

    def test_a_prompt_that_does_not_follow_from_its_facts_is_refused(self):
        data = committed()
        data['cases'][0] = copy.deepcopy(data['cases'][0])
        data['cases'][0]['prompt'] += ' Extra.'
        with self.assertRaisesRegex(v2set.SetError, 'does not follow from the facts'):
            build.check(data)

    def test_gate0_passes_on_the_committed_split(self):
        report = json.loads((ROOT / 'specs/078-lightning-heldout-v2/evidence/gate0-v3-report.json').read_text())
        self.assertTrue(report['passed'])
        self.assertEqual(report['references'], [])
        self.assertEqual(report['follower'], [])


class V3Root(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for path in v3.BOUND:
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, self.root / path)
        self.home = self.root / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        (self.root / v3.FREEZE).write_text(json.dumps(v3.freeze_record(self.root, COMMIT)))
        (self.root / v3.FINGERPRINTS).write_text(json.dumps(v3.fingerprints(self.root)))

    def run_fake(self, repetitions=3, max_rollouts=2, **kwargs):
        cfg = config.build({'rollout': {'repetitions': repetitions, 'hosts': ['claude-code']},
                            'budget': {'maxRollouts': max_rollouts}})
        with patch.object(v3, 'FREEZE', str(self.root / v3.FREEZE)):
            return runner.run(self.home, cfg, fake_hosts=True, prompt_set='v3-test', environ=base.CLEAN_ENV, **kwargs)


class FreezeAndRunnerTests(V3Root):
    def test_without_a_freeze_a_v3_run_is_refused_before_anything(self):
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake()
        self.assertEqual(caught.exception.code, 'protocol-not-frozen')
        self.assertFalse(self.home.exists())

    def test_an_edited_bound_file_is_refused(self):
        self.freeze()
        for path, code in ((v3.SKILL, 'skill-hash-mismatch'), (v3.PROMPT_FILES['v3-test'], 'holdout-hash-mismatch'),
                           (v3.PROTOCOL, 'protocol-hash-mismatch')):
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b'\n')
            with self.assertRaises(v3.FreezeError) as caught:
                v3.check_freeze(self.root, 'v3-test')
            self.assertEqual(caught.exception.code, code)
            (self.root / path).write_bytes(original)

    def test_wrong_repetitions_and_a_prebuilt_plugin_are_refused(self):
        self.freeze()
        for kwargs, code in (({'repetitions': 1}, 'config-enum'), ({'plugin_dir': self.root}, 'skill-hash-mismatch')):
            with self.assertRaises(runner.RunnerError) as caught:
                self.run_fake(**kwargs)
            self.assertEqual(caught.exception.code, code)

    def test_the_split_is_scored_once_per_candidate_and_may_resume(self):
        self.freeze()
        status = self.run_fake()
        self.assertEqual(status['hosts']['claude-code']['rollouts'], 2)
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake()
        self.assertEqual(caught.exception.code, 'test-already-scored')
        self.assertEqual(self.run_fake(max_rollouts=3, run_id=status['runId'], resume=True)['runId'], status['runId'])

    def test_another_arm_or_a_case_subset_is_refused(self):
        self.freeze()
        for kwargs in ({'arm': 'baseline'}, {'case_ids': ['V3T-001']}):
            with self.assertRaises(runner.RunnerError) as caught:
                self.run_fake(**kwargs)
            self.assertEqual(caught.exception.code, 'config-enum')

    def test_the_contamination_scan_includes_the_v3_fingerprints(self):
        self.freeze()
        with patch.object(v3, 'FINGERPRINTS', str(self.root / v3.FINGERPRINTS)), \
                patch.object(v3, 'FREEZE', str(self.root / v3.FREEZE)), \
                patch.object(runner, 'load_fingerprints', lambda root: {'idSha256': [], 'windowSha256': []}):
            prints = runner.scan_fingerprints(self.root)
        self.assertTrue(set(v3.fingerprints(self.root)['windowSha256']) <= set(prints['windowSha256']))

    def test_v3_is_protected_from_the_optimizer(self):
        self.assertIn(v3.PROMPT_FILES['v3-test'], runner.OPTIMIZER_DENIED)
        self.assertIn(runner.HOLDOUT_CANARY, runner.canary_note('v3-test'))
        self.freeze()
        prints = v3.load_fingerprints(self.root)
        case = committed()['cases'][0]
        self.assertFalse(runner.contamination_passed(case['prompt'], prints))
        self.assertFalse(runner.contamination_passed(f"see {case['id']}", prints))


if __name__ == '__main__':
    unittest.main()
