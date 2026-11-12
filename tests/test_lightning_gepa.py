# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-005 / SC-005: GEPA with a fake optimizer and synthetic reward vectors (no model contacted)."""
from pathlib import Path
import random
import tempfile
import unittest

from tests import lightning_fakes as fakes

from agent_braid import lightning_algorithm as algorithm
from agent_braid import lightning_config as config
from agent_braid import lightning_gepa as gepa
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store

HOSTS = ['claude-code', 'opencode']
CASES = [f'DEV-{i:02d}' for i in range(1, 11)]
ALL = ','.join(CASES)


def profile(**algo):
    return config.build({'rollout': {'repetitions': 3, 'hosts': HOSTS},
                         'algorithm': {'name': 'gepa', 'rounds': 3, 'minibatch': 5, **algo}})


def vectors(body, case_ids, reps):
    """Synthetic rewards: a body `PASS:<ids>` passes D4 exactly on those cases."""
    passing = set(body.split('PASS:', 1)[1].split()[0].split(',')) if 'PASS:' in body else set()
    return [{'caseId': c, 'host': h, 'd4FirstAttempt': c in passing, 'schemaValid': True,
             'reasons': [] if c in passing else ['missing-dependency'], 'refusal': None}
            for c in case_ids for h in HOSTS for _ in range(reps)]


class Optimizer:
    def __init__(self, bodies):
        self.bodies, self.inputs = list(bodies), []

    def __call__(self, text):
        self.inputs.append(text)
        return self.bodies.pop(0)


class FrontTests(unittest.TestCase):
    def test_front_excludes_dominated_and_duplicate_vectors(self):
        cases = ['a', 'b', 'c']
        scores = {'A': {'a': 1, 'b': 0, 'c': .5}, 'B': {'a': 0, 'b': 1, 'c': .5}, 'C': {'a': .5, 'b': .5, 'c': .4},
                  'D': {'a': .5, 'b': 0, 'c': .5}, 'E': {'a': 1, 'b': 0, 'c': .5}}
        self.assertEqual(gepa.pareto_front(scores, cases), ['A', 'B', 'C'])  # D dominated by A; E equals A
        self.assertEqual(gepa.weights(['A', 'B', 'C'], scores, cases), {'A': 2, 'B': 2, 'C': 0})

    def test_parent_sampling_follows_best_prompt_counts(self):
        cases = ['a', 'b', 'c', 'd']
        scores = {'A': {'a': 1, 'b': 1, 'c': 1, 'd': 0}, 'B': {'a': 0, 'b': 0, 'c': 0, 'd': 1}}
        rng = random.Random(7)
        picks = [gepa.select_parent(['A', 'B'], scores, cases, rng) for _ in range(4000)]
        self.assertAlmostEqual(picks.count('A') / len(picks), 0.75, delta=0.03)


class GEPATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.seed = vectors('PASS:DEV-01,DEV-02,DEV-03', CASES, 3)

    def tearDown(self):
        self.tmp.cleanup()

    def run_gepa(self, bodies, cfg=None, run_id='gepa', rng_seed=0):
        fake = Optimizer(bodies)
        channel = runner.OptimizerChannel('claude-code', transport=fake, fake=True)
        algo = gepa.GEPA(evaluator=fakes.results(vectors), scorer=fakes.scorer, optimizer=channel, seed_vectors=self.seed, rng_seed=rng_seed)
        return algo.run(self.home, cfg or profile(), run_id=run_id), fake

    def test_better_child_is_accepted_evaluated_and_dominates_the_seed(self):
        summary, fake = self.run_gepa([f'PASS:{ALL}\n', 'PASS:DEV-01\n', 'PASS:DEV-02\n'])
        first = summary['rounds'][0]
        self.assertTrue(first['accepted'])
        self.assertEqual(summary['front'], [first['child']])  # the seed is dominated and leaves the front
        self.assertEqual(summary['bestSha256'], first['child'])
        self.assertEqual(summary['bestFull']['d4FirstAttempt'], 1.0)
        self.assertEqual([r['accepted'] for r in summary['rounds'][1:]], [False, False])
        self.assertEqual(summary['rollouts'], 30 + 60)  # 3 minibatches of 10 and one full evaluation
        self.assertEqual(summary['optimizerCalls'], 3)
        found = algorithm.candidates(self.home, 'gepa')
        child = found[first['child']]
        self.assertTrue(child.value['paretoMember'])
        self.assertEqual(child.value['devScore']['full']['rollouts'], 60)
        self.assertEqual(child.value['optimizerTemplateSha256'], gepa.template_sha256())
        self.assertFalse(found[summary['seedSha256']].value['paretoMember'])
        for rnd in summary['rounds'][1:]:
            self.assertIsNone(found[rnd['child']].value['devScore']['full'])
            self.assertFalse(found[rnd['child']].value['paretoMember'])

    def test_child_not_improving_on_the_minibatch_is_rejected_without_full_evaluation(self):
        summary, _ = self.run_gepa(['PASS:DEV-01,DEV-02,DEV-03\nreworded\n', 'PASS:none\n', 'PASS:DEV-01\n'])
        self.assertEqual([r['accepted'] for r in summary['rounds']], [False, False])
        self.assertEqual((summary['stop'], summary['rollouts']), ('no-improvement', 20))  # 2 flat rounds
        self.assertEqual(summary['bestSha256'], summary['seedSha256'])
        self.assertEqual(summary['front'], [summary['seedSha256']])

    def test_second_accepted_child_beyond_the_budget_is_not_evaluated(self):
        bodies = [f'PASS:{",".join(CASES[:6])}\n', f'PASS:{",".join(CASES[:8])}\n', f'PASS:{ALL}\n']
        summary, _ = self.run_gepa(bodies, profile(rounds=3))
        self.assertEqual(summary['stop'], 'unit-cap')
        self.assertLessEqual(summary['rollouts'], 120)
        evaluated = [sha for sha, r in algorithm.candidates(self.home, 'gepa').items()
                     if r.value['devScore'] and r.value['devScore']['full']]
        self.assertEqual(len(evaluated), 2)  # the seed and the first accepted child

    def test_reflection_sees_only_the_parent_minibatch_and_text(self):
        summary, fake = self.run_gepa(['PASS:none\n', 'PASS:none a\n', 'PASS:none b\n'])
        seed_body = store.RunStore(self.home, 'gepa').candidate_text(summary['seedSha256'])
        for rnd, text in zip(summary['rounds'], fake.inputs):
            self.assertIn(seed_body, text)
            mentioned = {c for c in CASES if c + ' on ' in text}
            self.assertEqual(mentioned, set(rnd['minibatch']))
            self.assertNotIn('HELD-', text)

    def test_same_seed_repeats_choices(self):
        bodies = ['PASS:DEV-04\n', 'PASS:DEV-05\n', 'PASS:DEV-06\n']
        first, _ = self.run_gepa(list(bodies), run_id='one', rng_seed=3)
        second, _ = self.run_gepa(list(bodies), run_id='two', rng_seed=3)
        self.assertEqual([r['minibatch'] for r in first['rounds']], [r['minibatch'] for r in second['rounds']])
        self.assertEqual(first['front'], second['front'])

    def test_unusable_reflection_is_a_failed_call(self):
        summary, _ = self.run_gepa(['  ', 'PASS:none\n', 'PASS:none c\n'])
        self.assertEqual((summary['failedCalls'], summary['rounds'][0]['child']), (1, None))

    def test_optimizer_outside_the_runner_is_refused(self):
        with self.assertRaises(runner.RunnerError) as caught:
            gepa.GEPA(evaluator=fakes.results(vectors), scorer=fakes.scorer, optimizer=Optimizer([]), seed_vectors=self.seed)
        self.assertEqual(caught.exception.code, 'optimizer-bypass')


if __name__ == '__main__':
    unittest.main()
