# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-010 / SC-010: lineage, seeds and replay of selection decisions from stored parsed attempts."""
import json
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_algorithm as algorithm
from agent_braid import lightning_apo as apo
from agent_braid import lightning_gepa as gepa
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.lightning_schema import canonical_bytes
from tests import lightning_fakes as fakes
from tests.test_lightning_stopping import CASES, Evaluator, Optimizer, profile


def refuse(_text):
    raise AssertionError('replay must not call the optimizer')


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.seed = Evaluator()('PASS:DEV-01,DEV-02,DEV-03', CASES, 3)

    def tearDown(self):
        self.tmp.cleanup()

    def algo(self, kind, transport, evaluator=None, rng_seed=7):
        channel = runner.OptimizerChannel('claude-code', transport=transport, fake=True)
        options = {'evaluator': evaluator or fakes.results(Evaluator()), 'optimizer': channel,
                   'seed_vectors': self.seed, 'scorer': fakes.scorer}
        return apo.APO(**options) if kind == 'apo' else gepa.GEPA(**options, rng_seed=rng_seed)

    def finished(self, kind, run_id):
        cfg = profile(kind, rounds=3)
        summary = self.algo(kind, Optimizer()).run(self.home, cfg, run_id=run_id)
        return cfg, summary, store.RunStore(self.home, run_id)

    def files(self, run):
        return {p.name: p.read_bytes() for p in run.root.iterdir() if p.is_file()}

    def test_replay_reproduces_every_selection_without_calls_or_writes(self):
        for kind in ('apo', 'gepa'):
            with self.subTest(kind=kind):
                cfg, summary, run = self.finished(kind, kind)
                before = self.files(run)
                result = algorithm.replay(self.home, kind, self.algo(kind, refuse, evaluator=refuse), cfg)
                self.assertEqual((result['selectionsMatch'], result['resultsMatch']), (True, True))
                self.assertEqual(result['bestSha256'], summary['bestSha256'])
                self.assertEqual(self.files(run), before)

    def test_an_altered_attempt_result_record_changes_a_selection(self):
        for kind in ('apo', 'gepa'):
            with self.subTest(kind=kind):
                cfg, _, run = self.finished(kind, f'{kind}-alt')
                first_eval = next(e for e in run.read_journal() if e['kind'] == 'eval')
                target = first_eval['results'][0][0]
                path = run.root / store.KINDS['result']
                lines = []
                for line in path.read_bytes().splitlines():
                    value = json.loads(line)
                    if value['attemptId'] == target:
                        report = value['parsedAttempts'][0]['report']
                        report['d4FirstAttempt'] = not report['d4FirstAttempt']
                        line = canonical_bytes(value).rstrip(b'\n')
                    lines.append(line)
                path.write_bytes(b'\n'.join(lines) + b'\n')
                result = algorithm.replay(self.home, f'{kind}-alt', self.algo(kind, refuse, evaluator=refuse), cfg)
                self.assertEqual(result['alteredResults'], [target])
                self.assertFalse(result['selectionsMatch'])
                self.assertTrue(result['changedCandidates'])

    def test_run_records_seed_lineage_call_and_result_hashes(self):
        cfg, summary, run = self.finished('gepa', 'lineage')
        journal = run.read_journal()
        self.assertEqual(journal[0], {'kind': 'start', 'algorithm': 'gepa', 'rngSeed': 7})
        self.assertEqual(run.manifest()['configDigest'], algorithm.digest(cfg))
        records = algorithm.candidates(self.home, 'lineage')
        calls = {e['callId'] for e in journal if e['kind'] == 'call'}
        results = {r.value['attemptId']: algorithm.result_sha256(r.value) for r in run.read('result')}
        for record in records.values():
            value = record.value
            self.assertTrue(value['parentSha256'] is None or value['parentSha256'] in records)
            self.assertLessEqual(set(value['optimizerCalls']), calls)
        for entry in (e for e in journal if e['kind'] == 'eval'):
            for attempt_id, sha in entry['results']:
                self.assertEqual(results[attempt_id], sha)

    def test_replay_of_a_journal_that_ends_early_is_refused(self):
        cfg, _, run = self.finished('apo', 'short')
        path = run.root / store.JOURNAL
        lines = path.read_bytes().splitlines()
        path.write_bytes(b'\n'.join(lines[:3]) + b'\n')
        with self.assertRaises(runner.RunnerError) as caught:
            algorithm.replay(self.home, 'short', self.algo('apo', refuse, evaluator=refuse), cfg)
        self.assertEqual(caught.exception.code, 'replay-incomplete')


class RescoreTests(unittest.TestCase):
    def record(self, **changes):
        value = fakes.results(lambda *_: [{'caseId': 'DEV-01', 'host': 'claude-code', 'd4FirstAttempt': True,
                                           'schemaValid': True, 'reasons': [], 'refusal': None}])('b', ['DEV-01'], 1)[0]
        value['parsedAttempts'][0].update(accepted=False, report=None)
        return {**value, **changes}

    def test_default_scorer_rescores_parsed_attempts_with_spec069_scoring(self):
        vector = algorithm.rescore(self.record())
        self.assertEqual((vector['caseId'], vector['host']), ('DEV-01', 'claude-code'))
        self.assertEqual((vector['d4FirstAttempt'], vector['schemaValid']), (False, False))
        self.assertEqual(set(vector), algorithm.VECTOR_KEYS)

    def test_a_refusal_scores_zero_and_held_out_records_are_refused(self):
        self.assertEqual(algorithm.rescore(self.record(refusal='canary-hit'))['refusal'], 'canary-hit')
        with self.assertRaises(runner.RunnerError) as caught:
            algorithm.rescore(self.record(promptSet='held-out'))
        self.assertEqual(caught.exception.code, 'holdout-contamination')

    def test_an_unknown_case_is_refused_by_code(self):
        record = self.record()
        record['rolloutId'] = record['rolloutId'].replace('DEV-01', 'DEV-99')
        with self.assertRaises(runner.RunnerError) as caught:
            algorithm.rescore(record)
        self.assertEqual(caught.exception.code, 'reward-shape')


if __name__ == '__main__':
    unittest.main()
