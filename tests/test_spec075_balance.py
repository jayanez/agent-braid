# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T007 (REQ-007 / SC-007): seeded equal 1:1 balance per task for rollout exports only (E4, OD-2)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_export as export
from unittest.mock import patch

from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())


def build_task_d(run):
    """task-d: more failures (5) than successes (2), so the cap is the success count."""
    for n in range(2):
        rollout(run, f'ro-d{n}', f'raw-d{n}', [(f'd ok {n}', 'yes')], task='task-d', d4=True, status='succeeded')
    for n in range(5):
        rollout(run, f'ro-e{n}', f'raw-e{n}', [(f'd bad {n}', 'no')], task='task-d', d4=False, status='failed')


# Kept rollouts per task for seed 0 (S2/S4 golden): a change to the draw key or order shows here.
GOLDEN_SEED_0 = {'task-a': ['ro-a0', 'ro-a4', 'ro-f0', 'ro-f1'], 'task-d': ['ro-d0', 'ro-d1', 'ro-e2', 'ro-e4']}
RANK_GOLDEN = '3c49066a6ffd99f30bc4f5f8b62e010d8f3900c33d97dd3ac2e0e6ca64dad7d3'  # sha256 of [0,"task-a","run-1","ro-a0"]


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
        build_task_d(run)
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
        self.assertEqual([r['taskId'] for r in report], ['task-a', 'task-b', 'task-c', 'task-d'])

    def test_more_failures_than_successes_caps_at_the_successes(self):
        kept, report, _ = export.balance_equal(self.items, seed=0)
        task_d = sorted(o for t, o, _ in self.kept(kept) if t == 'task-d')
        self.assertEqual(task_d, ['failure', 'failure', 'success', 'success'])
        self.assertEqual({r['taskId']: r for r in report}['task-d'], {
            'taskId': 'task-d', 'successes': 2, 'failures': 5, 'unknown': 0, 'keptPerOutcome': 2, 'dropped': 3,
            'singleOutcome': False})

    def kept_rollouts(self, items, seed=0):
        kept = export.balance_equal(items, seed=seed)[0]
        return {task: sorted({i['rolloutId'] for i in kept if i['taskId'] == task}) for task in ('task-a', 'task-d')}

    def test_the_draw_is_pinned(self):
        self.assertEqual(self.kept_rollouts(self.items), GOLDEN_SEED_0)
        self.assertEqual(export._rank(0, 'task-a', {'runId': 'run-1', 'rolloutId': 'ro-a0', 'attemptId': 'x'}),
                         export._rank(0, 'task-a', {'runId': 'run-1', 'rolloutId': 'ro-a0', 'attemptId': 'y'}))
        self.assertEqual(export._rank(0, 'task-a', {'runId': 'run-1', 'rolloutId': 'ro-a0'}), RANK_GOLDEN)

    def test_a_re_ingest_with_a_new_salt_selects_the_same_attempts(self):
        other = self.base / 'home-2'
        consent(other)
        run = new_run(other)
        for n in range(5):
            turns = [(f'a ok {n}', 'yes')] + ([('a ok 0 again', 'yes')] if n == 0 else [])
            rollout(run, f'ro-a{n}', f'raw-a{n}', turns, task='task-a', d4=True, status='succeeded')
        for n in range(2):
            rollout(run, f'ro-f{n}', f'raw-f{n}', [(f'a bad {n}', 'no')], task='task-a', d4=False, status='failed')
        build_task_d(run)
        items, _ = export.select(export.read_runs(other, ['run-1']))
        self.assertTrue({i['attemptId'] for i in items}.isdisjoint({i['attemptId'] for i in self.items}))
        self.assertEqual(self.kept_rollouts(items), self.kept_rollouts(self.items))

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
                self.assertEqual([r['taskId'] for r in manifest['balanceReport']],
                                 ['task-a', 'task-b', 'task-c', 'task-d'])
                if level == 'trajectory':
                    outcomes = sorted((e['taskId'], e['outcome']) for e in manifest['records'])
                    self.assertEqual(outcomes, [('task-a', 'failure')] * 2 + [('task-a', 'success')] * 2
                                     + [('task-c', 'failure'), ('task-c', 'success')]
                                     + [('task-d', 'failure')] * 2 + [('task-d', 'success')] * 2)
                calls = sum(e['turnRange'][1] - e['turnRange'][0] + 1 for e in manifest['records'])
                self.assertEqual(manifest['exclusions']['balance'] + calls, len(self.items))

    def test_dropped_attempts_leave_no_trace(self):
        manifest = self.export('trace')
        data = (self.base / 'trace' / 'records.jsonl').read_bytes() + (self.base / 'trace' / 'manifest.json').read_bytes()
        kept = {e['rolloutId'] for e in manifest['records']}
        dropped = [i for i in self.items if i['rolloutId'] not in kept]
        self.assertTrue(dropped)
        for item in dropped:
            self.assertNotIn(item['attemptId'].encode(), data)
            self.assertNotIn(f'"{item["rolloutId"]}"'.encode(), data)

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
        for value in ('ratio', '2:1', 1, True):
            with self.subTest(value=value), self.assertRaises(export.ExportError) as caught:
                self.export('x', balance=value)
            self.assertEqual(caught.exception.code, 'invalid-argument')
        self.assertFalse((self.base / 'x').exists())

    def test_an_invalid_seed_is_refused(self):
        for seed in (-1, True, 1.5, '0'):
            with self.subTest(seed=seed):
                for call in (lambda: export.balance_equal(self.items, seed=seed), lambda: self.export('y', seed=seed)):
                    with self.assertRaises(export.ExportError) as caught:
                        call()
                    self.assertEqual(caught.exception.code, 'invalid-argument')
        self.assertFalse((self.base / 'y').exists())

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


class ReportCheckTests(Base):
    """S3: check_manifest refuses a report that does not match the dataset, through export_dataset."""

    def tampered(self, name, change):
        real = export.balance_equal

        def balance(items, *, seed):
            kept, report, dropped = real(items, seed=seed)
            report = copy.deepcopy(report)
            kept = change(kept, report)
            return kept, report, dropped

        with patch.object(export, 'balance_equal', balance), self.assertRaises(export.ExportError) as caught:
            self.export(name)
        self.assertEqual(caught.exception.code, 'invalid-manifest')
        self.assertFalse((self.base / name).exists())

    def row(self, report, task):
        return next(r for r in report if r['taskId'] == task)

    def test_each_report_check(self):
        def claims_more(kept, report):  # a 1-vs-1 task claiming keptPerOutcome 5, dropped 0
            self.row(report, 'task-c').update(keptPerOutcome=5, dropped=0)
            return kept

        def wrong_single(kept, report):
            self.row(report, 'task-c')['singleOutcome'] = True
            return kept

        def wrong_dropped(kept, report):
            self.row(report, 'task-a')['dropped'] += 1
            return kept

        def extra_attempt(kept, report):  # one more task-a success than the report says
            more = [i for i in self.items if i['taskId'] == 'task-a' and i['outcome'] == 'success'
                    and i['rolloutId'] not in {k['rolloutId'] for k in kept}][:1]
            return kept + more

        def missing_attempt(kept, report):
            first = next(i for i in kept if i['taskId'] == 'task-c')
            return [i for i in kept if i['rolloutId'] != first['rolloutId']]

        def empty_report(kept, report):
            report.clear()
            return kept

        def duplicate_task(kept, report):
            report.append(dict(report[0]))
            return kept

        def unreported_task(kept, report):
            report[:] = [r for r in report if r['taskId'] != 'task-c']
            return kept

        def lower_cap(kept, report):  # under the minimum is not the E4 cap either
            self.row(report, 'task-a').update(keptPerOutcome=1, dropped=6)
            return kept

        for change in (claims_more, wrong_single, wrong_dropped, extra_attempt, missing_attempt, empty_report,
                       duplicate_task, unreported_task, lower_cap):
            with self.subTest(change=change.__name__):
                self.tampered(change.__name__, change)

    def test_balance_none_with_a_report_is_refused(self):
        real = export.build_manifest

        def with_report(entries, records, **kwargs):
            row = {'taskId': 'task-a', 'successes': 1, 'failures': 1, 'unknown': 0, 'keptPerOutcome': 1,
                   'dropped': 0, 'singleOutcome': False}
            return real(entries, records, **{**kwargs, 'balance_report': [row]})

        with patch.object(export, 'build_manifest', with_report), self.assertRaises(export.ExportError) as caught:
            self.export('none-report', balance='none')
        self.assertEqual(caught.exception.code, 'invalid-manifest')
        self.assertFalse((self.base / 'none-report').exists())


if __name__ == '__main__':
    unittest.main()
