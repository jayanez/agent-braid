# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-004 / SC-004: APO beam search with a fake optimizer and synthetic rewards (no model contacted)."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from tests import lightning_fakes as fakes

from agent_braid import lightning_algorithm as algorithm
from agent_braid import lightning_apo as apo
from agent_braid import lightning_config as config
from agent_braid import lightning_runner as runner

HOSTS = ['claude-code', 'opencode']
CASES = [f'DEV-{i:02d}' for i in range(1, 11)]


def profile(**algo):
    params = {'name': 'apo', 'beamWidth': 2, 'branchFactor': 2, 'rounds': 2, 'minibatch': 5, **algo}
    return config.build({'rollout': {'repetitions': 3, 'hosts': HOSTS}, 'algorithm': params})


def vectors(body, case_ids, reps):
    rate = int(hashlib.sha256(body.encode()).hexdigest(), 16) % 5  # synthetic, body-dependent reward
    return [{'caseId': c, 'host': h, 'd4FirstAttempt': (i + r) % 5 < rate, 'schemaValid': True,
             'reasons': ['missing-dependency'], 'refusal': None}
            for i, c in enumerate(case_ids) for h in HOSTS for r in range(reps)]


class FakeOptimizer:
    def __init__(self, edit=None):
        self.inputs = []
        self.edit = edit

    def __call__(self, text):
        self.inputs.append(text)
        if text.startswith('You optimize a prompt template.'):
            return '- State dependencies explicitly.'
        if self.edit is not None:
            return self.edit(len(self.inputs))
        return f'Revised guidance {len(self.inputs)}.\n'


class APOTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.seed = vectors('seed', CASES, 3)

    def tearDown(self):
        self.tmp.cleanup()

    def run_apo(self, cfg, fake=None, run_id='apo'):
        fake = fake or FakeOptimizer()
        channel = runner.OptimizerChannel('claude-code', transport=fake, fake=True)
        algo = apo.APO(evaluator=fakes.results(vectors), scorer=fakes.scorer, optimizer=channel, seed_vectors=self.seed)
        return algo.run(self.home, cfg, run_id=run_id), fake

    def test_preregistered_beam_matches_feasibility_table_and_records_lineage(self):
        summary, fake = self.run_apo(profile())
        self.assertEqual([(r['parents'], len(r['children'])) for r in summary['rounds']], [(1, 2), (2, 4)])
        self.assertTrue(all(len(r['beam']) <= 2 for r in summary['rounds']))
        self.assertEqual(summary['optimizerCalls'], 9)  # round 1: 1 critique + 2 edits; round 2: 2 + 4
        self.assertEqual(summary['rollouts'], 120)  # 20 + 40 search, 60 full evaluation of the best
        self.assertIsNone(summary['stop'])
        self.assertEqual(summary['templates'], apo.template_hashes())
        found = algorithm.candidates(self.home, 'apo')
        self.assertEqual(len(found), 7)
        best = found[summary['bestSha256']]
        self.assertEqual(best.value['devScore']['full']['rollouts'], 60)
        for record in found.values():
            if record.sha256 != summary['seedSha256']:
                self.assertEqual(record.value['algorithm'], 'apo')
                self.assertEqual(record.value['optimizerTemplateSha256'], summary['templateSetSha256'])
                self.assertEqual(len(record.value['optimizerCalls']), 2)
                self.assertTrue(all(c['passed'] for c in record.value['contaminationCheck']))
        self.assertTrue(all('HELD-' not in text for text in fake.inputs))

    def test_configuration_defaults_stop_at_the_rollout_cap(self):
        summary, _ = self.run_apo(profile(beamWidth=4, branchFactor=4, rounds=3))
        self.assertEqual(summary['stop'], 'unit-cap')
        self.assertLessEqual(summary['rollouts'], 120)

    def test_rounds_are_capped_at_three(self):
        cfg = profile(beamWidth=1, branchFactor=1, rounds=5)
        cfg['budget']['maxRollouts'] = 2000
        summary, _ = self.run_apo(cfg)
        self.assertEqual(len(summary['rounds']), apo.MAX_ROUNDS)

    def test_optimizer_call_cap_stops_the_run(self):
        cfg = profile()
        cfg['budget']['maxOptimizerCalls'] = 2
        summary, _ = self.run_apo(cfg)
        self.assertEqual((summary['stop'], summary['optimizerCalls']), ('optimizer-cap', 2))

    def test_unusable_edits_are_failed_calls_without_candidates(self):
        summary, _ = self.run_apo(profile(rounds=1), FakeOptimizer(edit=lambda n: '   '))
        self.assertEqual(summary['failedCalls'], 2)
        self.assertIsNone(summary['bestSha256'])
        self.assertEqual(len(algorithm.candidates(self.home, 'apo')), 1)

    def test_optimizer_calls_outside_the_runner_are_refused(self):
        with self.assertRaises(runner.RunnerError) as caught:
            apo.APO(evaluator=fakes.results(vectors), scorer=fakes.scorer, optimizer=FakeOptimizer(), seed_vectors=self.seed)
        self.assertEqual(caught.exception.code, 'optimizer-bypass')
        with self.assertRaises(runner.RunnerError) as caught:
            runner.OptimizerChannel('claude-code', transport=FakeOptimizer())
        self.assertEqual(caught.exception.code, 'isolation-failed')

    def test_contaminated_input_is_refused_before_the_call(self):
        fake = FakeOptimizer()
        channel = runner.OptimizerChannel('claude-code', transport=fake, fake=True)
        for text in ('see HELD-03 first', 'note ' + runner.LIGHTNING_CANARY):
            with self.subTest(text=text[:10]), self.assertRaises(runner.RunnerError) as caught:
                channel.call(text)
            self.assertEqual(caught.exception.code, 'holdout-contamination')
        self.assertEqual((fake.inputs, channel.calls), ([], []))

    def test_render_fills_placeholders_once(self):
        text = apo.render(apo.TEMPLATES['edit'], prompt_template='keep {critique} literal', critique='C')
        self.assertIn('keep {critique} literal', text)
        self.assertNotIn('<!--', text)


if __name__ == '__main__':
    unittest.main()
