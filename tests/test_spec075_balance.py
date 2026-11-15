# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T007 (REQ-007 / SC-007): seeded equal 1:1 balance per task for rollout exports only (E4, OD-2)."""
import json
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_export as export
from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        run = new_run(self.home)
        # task-a: 5 successes (the first with two calls), 2 failures and 1 attempt without a reward
        for n in range(5):
            turns = [(f'a ok {n}', 'yes')] + ([('a ok 0 again', 'yes')] if n == 0 else [])
            rollout(run, f'ro-a{n}', f'raw-a{n}', turns, task='task-a', d4=True, status='succeeded')
        for n in range(2):
            rollout(run, f'ro-f{n}', f'raw-f{n}', [(f'a bad {n}', 'no')], task='task-a', d4=False, status='failed')
        rollout(run, 'ro-u', 'raw-u', [('a unknown', '?')], task='task-a', d4=None, status='succeeded')
        for n in range(3):  # task-b: only successes
            rollout(run, f'ro-b{n}', f'raw-b{n}', [(f'b ok {n}', 'yes')], task='task-b', d4=True, status='succeeded')
        rollout(run, 'ro-c0', 'raw-c0', [('c ok', 'yes')], task='task-c', d4=True, status='succeeded')
        rollout(run, 'ro-c1', 'raw-c1', [('c bad', 'no')], task='task-c', d4=False, status='failed')
        self.items, _ = export.select(export.read_runs(self.home, ['run-1']))

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, name, **kwargs):
        options = {'kind': 'rollout', 'level': 'trajectory', 'now': T0 + 60, **kwargs}
        return export.export_dataset(self.home, ['run-1'], out=self.base / name, **options)

    def kept(self, items):
        return {(i['taskId'], i['outcome'], i['rolloutId']) for i in items}


class BalanceTests(Base):
    def test_five_successes_and_two_failures_keep_two_of_each(self):  # SC-007
        kept, report, dropped = export.balance_equal(self.items, seed=0)
        task_a = [k for k in self.kept(kept) if k[0] == 'task-a']
        self.assertEqual(sorted(o for _, o, _ in task_a), ['failure', 'failure', 'success', 'success'])
        self.assertEqual({r['taskId']: r for r in report}['task-a'], {
            'taskId': 'task-a', 'successes': 5, 'failures': 2, 'unknown': 1, 'keptPerOutcome': 2, 'dropped': 4,
            'singleOutcome': False})

    def test_single_outcome_tasks_are_reported_not_padded(self):
        kept, report, _ = export.balance_equal(self.items, seed=0)
        self.assertNotIn('task-b', {i['taskId'] for i in kept})
        self.assertEqual({r['taskId']: r for r in report}['task-b'], {
            'taskId': 'task-b', 'successes': 3, 'failures': 0, 'unknown': 0, 'keptPerOutcome': 0, 'dropped': 3,
            'singleOutcome': True})
        self.assertEqual({r['taskId']: r for r in report}['task-c']['keptPerOutcome'], 1)
        self.assertEqual([r['taskId'] for r in report], ['task-a', 'task-b', 'task-c'])

    def test_dropped_model_calls_are_counted(self):
        kept, report, dropped = export.balance_equal(self.items, seed=0)
        self.assertEqual(len(kept) + dropped, len(self.items))
        whole = {(i['rolloutId']) for i in kept}
        self.assertEqual(sum(1 for i in self.items if i['rolloutId'] in whole), len(kept))  # attempts kept whole

    def test_the_choice_is_seeded_and_stable(self):
        first = self.kept(export.balance_equal(self.items, seed=0)[0])
        self.assertEqual(self.kept(export.balance_equal(list(reversed(self.items)), seed=0)[0]), first)
        others = {frozenset(self.kept(export.balance_equal(self.items, seed=seed)[0])) for seed in range(12)}
        self.assertGreater(len(others), 1)  # the seed changes which successes are kept

    def test_supervised_exports_are_never_balanced(self):
        for kwargs in ({'kind': 'supervised', 'balance': 'equal'},
                       {'kind': 'supervised', 'balance': 'equal', 'outcome_field': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(export.ExportError) as caught:
                self.export('s', **kwargs)
            self.assertEqual(caught.exception.code, 'invalid-argument')
        manifest = self.export('s2', kind='supervised', outcome_field=True)  # the default for supervised
        self.assertEqual((manifest['balance'], manifest['balanceReport'], manifest['exclusions']['balance']),
                         ('none', [], 0))
        self.assertEqual(len(manifest['records']), len({i['rolloutId'] for i in self.items}))


class ExportTests(Base):
    def validate(self, manifest):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - development dependency
            return
        self.assertEqual([e.message for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(manifest)], [])

    def test_rollout_exports_balance_by_default_and_report(self):
        for level in export.LEVELS:
            with self.subTest(level=level):
                manifest = self.export(level, level=level)
                self.validate(manifest)
                self.assertEqual((manifest['balance'], manifest['seed']), ('equal', 0))
                self.assertEqual([r['taskId'] for r in manifest['balanceReport']], ['task-a', 'task-b', 'task-c'])
                outcomes = sorted((e['taskId'], e['outcome']) for e in manifest['records'])
                if level == 'trajectory':
                    self.assertEqual(outcomes, [('task-a', 'failure')] * 2 + [('task-a', 'success')] * 2
                                     + [('task-c', 'failure'), ('task-c', 'success')])
                kept_calls = len(manifest['records'])
                self.assertEqual(manifest['exclusions']['balance'] + kept_calls if level == 'transition'
                                 else manifest['exclusions']['balance'] + sum(
                                     e['turnRange'][1] - e['turnRange'][0] + 1 for e in manifest['records']),
                                 len(self.items))

    def test_reruns_are_identical_and_the_seed_is_recorded(self):
        first = self.export('r1', seed=7)
        second = self.export('r2', seed=7)
        self.assertEqual(first['digest'], second['digest'])
        self.assertEqual((self.base / 'r1' / 'records.jsonl').read_bytes(),
                         (self.base / 'r2' / 'records.jsonl').read_bytes())
        self.assertEqual(first['seed'], 7)
        digests = {self.export(f'd{seed}', seed=seed)['recordsSha256'] for seed in range(8)}
        self.assertGreater(len(digests), 1)

    def test_balance_none_exports_everything(self):
        manifest = self.export('n', balance='none')
        self.assertEqual((manifest['balanceReport'], manifest['exclusions']['balance']), ([], 0))
        self.assertEqual(len(manifest['records']), len({i['rolloutId'] for i in self.items}))

    def test_a_ratio_or_unknown_balance_is_refused(self):  # OD-2: no ratio parameter
        for value in ('ratio', '2:1', None, 1):
            with self.subTest(value=value), self.assertRaises(export.ExportError) as caught:
                self.export('x', balance=value) if value is not None else export.balance_equal(self.items, seed=-1)
            self.assertEqual(caught.exception.code, 'invalid-argument')
        self.assertFalse((self.base / 'x').exists())

    def test_everything_balanced_away_is_no_records(self):
        run = new_run(self.home, 'run-single')
        rollout(run, 'ro-s', 'raw-s', [('only', 'ok')], task='task-s', d4=True)
        with self.assertRaises(export.ExportError) as caught:
            export.export_dataset(self.home, ['run-single'], kind='rollout', level='trajectory',
                                  out=self.base / 'empty', now=T0)
        self.assertEqual(caught.exception.code, 'no-records')
        self.assertFalse((self.base / 'empty').exists())

    def test_the_terms_gate_stays_closed(self):
        run = new_run(self.home, 'run-host')
        rollout(run, 'ro-h0', 'raw-h0', [('h', 'ok')], task='task-h', d4=True, label='host-run')
        rollout(run, 'ro-h1', 'raw-h1', [('h', 'no')], task='task-h', d4=False, label='host-run')
        with self.assertRaises(export.ExportError) as caught:
            export.export_dataset(self.home, ['run-1', 'run-host'], kind='rollout', level='trajectory',
                                  out=self.base / 'host', now=T0)
        self.assertEqual(caught.exception.code, 'terms-gate-missing')
        self.assertFalse((self.base / 'host').exists())

    def test_host_output_that_balance_would_drop_is_still_refused(self):
        run = new_run(self.home, 'run-host-single')
        rollout(run, 'ro-hs', 'raw-hs', [('h', 'ok')], task='task-h', d4=True, label='host-run')  # single outcome
        with self.assertRaises(export.ExportError) as caught:
            export.export_dataset(self.home, ['run-1', 'run-host-single'], kind='rollout', level='trajectory',
                                  out=self.base / 'host-single', now=T0)
        self.assertEqual(caught.exception.code, 'terms-gate-missing')
        self.assertFalse((self.base / 'host-single').exists())


if __name__ == '__main__':
    unittest.main()
