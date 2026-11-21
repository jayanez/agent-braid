# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T005 (REQ-006, REQ-007, REQ-008, REQ-012 / SC-006, SC-007, SC-012): v2 freeze, runner and analysis.

Fake hosts only; no model is contacted.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid import lightning_heldout_v2 as v2
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.harness_host_claude import ENV_DENY

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import spec069_scoring as scoring  # noqa: E402

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}
COMMIT = '0' * 40


def cases(name: str) -> list[dict]:
    return json.loads((ROOT / v2.PROMPT_FILES[name]).read_text())['cases']


class TempRoot(unittest.TestCase):
    """A copy of the bound files in a temporary root, frozen there."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for path in v2.BOUND:
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, target)

    def tearDown(self):
        self.tmp.cleanup()

    def freeze(self):
        (self.root / v2.FREEZE).write_text(json.dumps(v2.freeze_record(self.root, COMMIT)))
        (self.root / v2.FINGERPRINTS).write_text(json.dumps(v2.fingerprints(self.root)))


class FreezeTests(TempRoot):
    def test_without_a_freeze_every_v2_set_is_refused(self):
        for name in v2.PROMPT_FILES:
            with self.assertRaises(v2.FreezeError) as caught:
                v2.check_freeze(self.root, name)
            self.assertEqual(caught.exception.code, 'protocol-not-frozen')

    def test_a_matching_freeze_returns_the_split_hash(self):
        self.freeze()
        for name, path in v2.PROMPT_FILES.items():
            self.assertEqual(v2.check_freeze(self.root, name), v2.sha256(self.root / path))

    def test_any_edited_bound_file_is_refused(self):
        self.freeze()
        expected = {v2.PROTOCOL: 'protocol-hash-mismatch', v2.GATE0: 'protocol-hash-mismatch'}
        for path in v2.BOUND:
            original = (self.root / path).read_bytes()
            (self.root / path).write_bytes(original + b'\n')
            with self.assertRaises(v2.FreezeError, msg=path) as caught:
                v2.check_freeze(self.root, 'v2-feedback')
            self.assertEqual(caught.exception.code, expected.get(path, 'holdout-hash-mismatch'), path)
            (self.root / path).write_bytes(original)

    def test_a_record_missing_a_bound_file_is_refused(self):
        record = v2.freeze_record(self.root, COMMIT)
        del record['files'][v2.GATE0]
        (self.root / v2.FREEZE).write_text(json.dumps(record))
        with self.assertRaisesRegex(v2.FreezeError, 'Unknown SPEC-078 freeze record'):
            v2.check_freeze(self.root, 'v2-test')

    def test_the_freeze_names_a_full_commit(self):
        with self.assertRaises(v2.FreezeError):
            v2.freeze_record(self.root, 'develop')

    def test_the_a0_skill_must_be_the_frozen_bytes(self):
        self.freeze()
        skill = (self.root / v2.SKILL).read_bytes()
        v2.check_skill(self.root, skill)
        with self.assertRaises(v2.FreezeError):
            v2.check_skill(self.root, skill + b'edited')

    def test_fingerprints_cover_validation_and_test_only_and_go_stale(self):
        self.freeze()
        prints = v2.load_fingerprints(self.root)
        ids = {hashlib.sha256(c['id'].encode()).hexdigest() for n in v2.PROTECTED for c in cases(n)}
        self.assertEqual(set(prints['idSha256']), ids)
        feedback_ids = {hashlib.sha256(c['id'].encode()).hexdigest() for c in cases('v2-feedback')}
        self.assertFalse(feedback_ids & set(prints['idSha256']))
        record = json.loads((self.root / v2.FINGERPRINTS).read_text())
        record['sources'][v2.PROMPT_FILES['v2-test']] = '0' * 64
        (self.root / v2.FINGERPRINTS).write_text(json.dumps(record))
        with self.assertRaises(v2.FreezeError) as caught:
            v2.load_fingerprints(self.root)
        self.assertEqual(caught.exception.code, 'holdout-fingerprint-stale')

    def test_contamination_scan_refuses_a_v2_test_prompt(self):
        self.freeze()
        prompt = cases('v2-test')[5]['prompt']
        feedback = cases('v2-feedback')[5]['prompt']
        base = {'idSha256': [], 'windowSha256': []}
        with patch.object(runner, 'checkout_root', return_value=self.root), \
                patch.object(runner, 'load_fingerprints', return_value=base):
            self.assertFalse(runner.contamination_passed('Rewrite this: ' + prompt))
            self.assertTrue(runner.contamination_passed('Rewrite this: ' + feedback))


class RunnerTests(TempRoot):
    def run_fake(self, prompt_set, **kwargs):
        cfg = config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code']}})
        home = Path(self.tmp.name).resolve() / 'home'
        with patch.object(v2, 'FREEZE', str(self.root / v2.FREEZE)):
            return home, runner.run(home, cfg, fake_hosts=True, prompt_set=prompt_set, environ=CLEAN_ENV, **kwargs)

    def test_a_v2_run_without_a_freeze_is_refused_before_anything(self):
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake('v2-test')
        self.assertEqual(caught.exception.code, 'protocol-not-frozen')

    def test_a_v2_run_with_another_arm_is_refused(self):
        self.freeze()
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake('v2-feedback', arm='baseline')
        self.assertEqual(caught.exception.code, 'config-enum')

    def test_fake_pipeline_on_v2_feedback_scores_every_reference(self):
        self.freeze()
        home, status = self.run_fake('v2-feedback')
        self.assertEqual(status['promptSet'], 'v2-feedback')
        self.assertEqual(status['hosts']['claude-code']['rollouts'], len(cases('v2-feedback')))
        run = store.RunStore(home, status['runId'])
        results = [r.value for r in run.read('result')]
        by_id = {c['id']: c for c in cases('v2-feedback')}
        valid = [scoring.score_case(by_id[r['rolloutId'].split('.')[1]], r['parsedAttempts'])['validFirstAttempt']
                 for r in results]
        self.assertTrue(all(valid))  # partial-coverage references included
        self.assertTrue(all(r.is_train for r in run.read('rollout')))

    def test_validation_and_test_carry_the_held_out_canary_and_are_not_train(self):
        self.assertIn(runner.HOLDOUT_CANARY, runner.canary_note('v2-test'))
        self.assertIn(runner.HOLDOUT_CANARY, runner.canary_note('v2-validation'))
        self.assertNotIn(runner.HOLDOUT_CANARY, runner.canary_note('v2-feedback'))
        for name in v2.PROTECTED:
            self.assertIn(v2.PROMPT_FILES[name], runner.OPTIMIZER_DENIED)
        self.assertNotIn(v2.PROMPT_FILES['v2-feedback'], runner.OPTIMIZER_DENIED)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.cases = cases('v2-test')

    def trials(self, fail_ids=(), zero_ids=()):
        return {c['id']: ([False] * 3 if c['id'] in zero_ids else [True, False, False] if c['id'] in fail_ids
                          else [True] * 3) for c in self.cases}

    def test_wilson_matches_the_spec069_scorer(self):
        for k, n in ((88, 100), (87, 100), (16, 16), (0, 5)):
            self.assertEqual(v2.wilson_interval(k, n), scoring.wilson_interval(k, n))

    def test_all_passing_meets_od1(self):
        report = v2.analyse(self.cases, self.trials())
        self.assertEqual(report['od1'], 'meets')
        self.assertEqual(report['passing'], 100)
        self.assertEqual(report['allRepetitionsValid'], 100)

    def test_the_threshold_is_88_of_100(self):
        by_class = {}
        for c in self.cases:
            by_class.setdefault(c['class'], []).append(c['id'])
        spread = [ids[i] for i in range(2) for ids in by_class.values()]  # two per class: no class below half
        self.assertEqual(v2.analyse(self.cases, self.trials(fail_ids=spread[:12]))['od1'], 'meets')
        self.assertEqual(v2.analyse(self.cases, self.trials(fail_ids=spread[:13]))['od1'], 'misses')

    def test_a_class_below_half_misses_despite_the_share(self):
        chain = [c['id'] for c in self.cases if c['class'] == 'chain-plain']
        report = v2.analyse(self.cases, self.trials(fail_ids=chain[:6]))
        self.assertGreaterEqual(report['wilson95'][0], 0.80)
        self.assertEqual(report['od1'], 'misses')

    def test_a_zero_prompt_is_held_then_counted_or_invalidating(self):
        zero = self.cases[0]['id']
        self.assertEqual(v2.analyse(self.cases, self.trials(zero_ids=[zero]))['od1'], 'held')
        self.assertEqual(v2.analyse(self.cases, self.trials(zero_ids=[zero]), {zero: 'model'})['od1'], 'misses')
        self.assertEqual(v2.analyse(self.cases, self.trials(zero_ids=[zero]), {zero: 'instrument'})['od1'],
                         'invalidated')
        with self.assertRaises(ValueError):
            v2.analyse(self.cases, self.trials(), {zero: 'model'})  # not a zero prompt

    def test_the_sign_test_and_comparison(self):
        self.assertAlmostEqual(v2.sign_test_one_sided(8, 1), 10 / 512)
        self.assertEqual(v2.sign_test_one_sided(0, 0), 1.0)
        ids = [c['id'] for c in self.cases]
        base = v2.analyse(self.cases, self.trials(fail_ids=ids[:10]))
        better = v2.analyse(self.cases, self.trials(fail_ids=ids[:1]))
        result = v2.compare(base, better)
        self.assertEqual((result['better'], result['worse']), (9, 0))
        self.assertTrue(result['supported'])
        self.assertFalse(v2.compare(better, base)['supported'])

    def test_clustered_se(self):
        self.assertEqual(v2.clustered_se([1.0, 1.0, 1.0]), 0.0)
        self.assertAlmostEqual(v2.clustered_se([0.0, 1.0]), 0.5)


class BoundaryTests(unittest.TestCase):
    def test_the_v2_module_imports_only_the_standard_library(self):
        tree = ast.parse((ROOT / 'agent_braid/lightning_heldout_v2.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name.split('.')[0], sys.stdlib_module_names)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module.split('.')[0], sys.stdlib_module_names | {'__future__'})

    def test_nothing_writes_the_scorer_the_sets_or_the_skill(self):
        for path in ('agent_braid/lightning_heldout_v2.py', 'scripts/spec078_freeze.py'):
            text = (ROOT / path).read_text()
            for protected in ('spec069_scoring.py', 'SKILL.md', 'held-out.json'):
                self.assertFalse(any(protected in line and 'write' in line for line in text.splitlines()), path)


if __name__ == '__main__':
    unittest.main()
