# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-007 / SC-007: budgets, stopping rules and --resume for APO and GEPA (fake optimizer, no model)."""
import hashlib
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_apo as apo
from agent_braid import lightning_config as config
from agent_braid import lightning_gepa as gepa
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store

HOSTS = ['claude-code', 'opencode']
CASES = [f'DEV-{i:02d}' for i in range(1, 11)]


def profile(name, **algo):
    return config.build({'rollout': {'repetitions': 3, 'hosts': HOSTS},
                         'algorithm': {'name': name, 'beamWidth': 2, 'branchFactor': 2, 'rounds': 3, 'minibatch': 5,
                                       **algo}})


class Evaluator:
    """Synthetic rewards: `PASS:<ids>` passes D4 on those cases; can raise a quota stop after N evaluations."""

    def __init__(self, quota_after=None):
        self.count, self.quota_after = 0, quota_after

    def __call__(self, body, case_ids, reps):
        self.count += 1
        if self.quota_after is not None and self.count > self.quota_after:
            raise runner.RunnerError('quota', 'weekly-stop')
        passing = set(body.split('PASS:', 1)[1].split()[0].split(',')) if 'PASS:' in body else set()
        return [{'caseId': c, 'host': h, 'd4FirstAttempt': c in passing, 'schemaValid': True, 'reasons': [],
                 'refusal': None} for c in case_ids for h in HOSTS for _ in range(reps)]


class Optimizer:
    """Critiques for APO gradient prompts; otherwise a `PASS:` body determined by the input text."""

    def __init__(self, fixed=None):
        self.inputs, self.fixed = [], fixed

    def __call__(self, text):
        self.inputs.append(text)
        if text.startswith('You optimize a prompt template.'):
            return '- be explicit'
        if self.fixed is not None:
            return self.fixed(len(self.inputs))
        digest = hashlib.sha256(text.encode()).hexdigest()  # a pure function of the input, so replays agree
        return f'PASS:{",".join(CASES[:4 + int(digest, 16) % 7])}\nvariant {digest[:12]}\n'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.seed = Evaluator()('PASS:DEV-01,DEV-02,DEV-03', CASES, 3)

    def tearDown(self):
        self.tmp.cleanup()

    def run_algo(self, kind, cfg, *, optimizer=None, evaluator=None, run_id='run', resume=False, rng_seed=0):
        optimizer = optimizer or Optimizer()
        channel = runner.OptimizerChannel('claude-code', transport=optimizer, fake=True)
        options = {'evaluator': evaluator or Evaluator(), 'optimizer': channel, 'seed_vectors': self.seed}
        algo = apo.APO(**options) if kind == 'apo' else gepa.GEPA(**options, rng_seed=rng_seed)
        return algo.run(self.home, cfg, run_id=run_id, resume=resume), optimizer

    def assert_within(self, summary, cfg):
        self.assertLessEqual(summary['rollouts'], cfg['budget']['maxRollouts'])
        self.assertLessEqual(summary['optimizerCalls'], cfg['budget']['maxOptimizerCalls'])

    def recorded_stop(self, run_id='run'):
        return [e for e in store.RunStore(self.home, run_id).read_journal() if e['kind'] == 'stop'][-1]


class StopTests(Base):
    def test_each_stop_reason_is_the_first_applicable_rule_and_is_recorded(self):
        cases = {
            'unit-cap': ('apo', profile('apo', beamWidth=4, branchFactor=4),
                         {'fixed': lambda n: f'PASS:DEV-01,DEV-04\nv{n}\n'}),
            'optimizer-cap': ('gepa', profile('gepa'), {'cap_calls': 1}),
            'no-improvement': ('gepa', profile('gepa', rounds=5), {'fixed': lambda n: f'PASS:none {n}\n'}),
            'weekly-stop': ('gepa', profile('gepa'), {'quota_after': 1}),
        }
        for reason, (kind, cfg, extra) in cases.items():
            with self.subTest(reason=reason):
                if 'cap_calls' in extra:
                    cfg['budget']['maxOptimizerCalls'] = extra['cap_calls']
                summary, _ = self.run_algo(kind, cfg, run_id=reason,
                                           optimizer=Optimizer(extra.get('fixed')),
                                           evaluator=Evaluator(extra.get('quota_after')))
                self.assertEqual(summary['stop'], reason)
                self.assertEqual(self.recorded_stop(reason)['reason'], reason)
                self.assert_within(summary, cfg)
                self.assertEqual(summary['resume'] is not None, reason == 'weekly-stop')

    def test_apo_never_runs_more_than_three_rounds(self):
        cfg = profile('apo', beamWidth=1, branchFactor=1, rounds=10)
        cfg['budget']['maxRollouts'] = 2000
        summary, _ = self.run_algo('apo', cfg)
        self.assertLessEqual(len(summary['rounds']), apo.MAX_ROUNDS)

    def test_a_refused_optimizer_input_stops_the_run(self):
        cfg = profile('gepa')
        channel = runner.OptimizerChannel('claude-code', transport=Optimizer(), fake=True)
        algo = gepa.GEPA(evaluator=Evaluator(), optimizer=channel, seed_vectors=self.seed)
        algo.skill_text = lambda _cfg: '---\nname: x\n---\nGuidance mentioning HELD-04.\n'
        summary = algo.run(self.home, cfg, run_id='refused')
        self.assertEqual((summary['stop'], summary['refusal']), ('refused', 'holdout-contamination'))
        self.assertEqual(summary['optimizerCalls'], 0)


class ResumeTests(Base):
    def test_resume_after_a_quota_stop_reaches_the_uninterrupted_result_without_repeating_calls(self):
        for kind in ('apo', 'gepa'):
            with self.subTest(kind=kind):
                cfg = profile(kind, rounds=2)
                whole, _ = self.run_algo(kind, cfg, run_id=f'{kind}-whole')
                stopped, first = self.run_algo(kind, cfg, run_id=f'{kind}-cut', evaluator=Evaluator(quota_after=1))
                self.assertEqual(stopped['stop'], 'weekly-stop')
                self.assertIn(f'--resume {kind}-cut', stopped['resume'])
                resumed, second = self.run_algo(kind, cfg, run_id=f'{kind}-cut', resume=True)
                self.assertEqual(resumed['bestSha256'], whole['bestSha256'])
                self.assertEqual(resumed['rounds'], whole['rounds'])
                self.assertEqual((resumed['rollouts'], resumed['optimizerCalls']),
                                 (whole['rollouts'], whole['optimizerCalls']))
                self.assertGreater(resumed['replayed'], 0)
                self.assertEqual(len(first.inputs) + len(second.inputs), len(_inputs(self, kind, cfg)))

    def test_resume_with_another_seed_or_configuration_is_refused(self):
        cfg = profile('gepa', rounds=2)
        self.run_algo('gepa', cfg, evaluator=Evaluator(quota_after=2))
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_algo('gepa', cfg, resume=True, rng_seed=99)
        self.assertEqual(caught.exception.code, 'resume-diverged')
        changed = profile('gepa', rounds=3)
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_algo('gepa', changed, resume=True)
        self.assertEqual(caught.exception.code, 'resume-diverged')


class JournalTests(Base):
    def test_journal_is_private_and_refuses_unknown_shapes(self):
        self.run_algo('gepa', profile('gepa', rounds=1))
        run = store.RunStore(self.home, 'run')
        self.assertEqual((run.root / store.JOURNAL).stat().st_mode & 0o777, 0o600)
        self.assertEqual([e['kind'] for e in run.read_journal()][-1], 'stop')
        for bad in ({'kind': 'note'}, {'kind': 'stop', 'reason': None}, {'kind': 'eval', 'key': 'x', 'vectors': []}):
            with self.subTest(bad=bad), self.assertRaises(store.StoreError) as caught:
                run.append_journal(bad)
            self.assertEqual(caught.exception.code, 'store-shape')

def _inputs(case, kind, cfg):
    """Optimizer inputs of an uninterrupted run in a fresh home."""
    with tempfile.TemporaryDirectory() as tmp:
        home, case.home = case.home, Path(tmp).resolve() / 'home'
        try:
            return case.run_algo(kind, cfg, run_id='count')[1].inputs
        finally:
            case.home = home


if __name__ == '__main__':
    unittest.main()
