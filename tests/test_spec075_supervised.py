# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T004 (REQ-003 / SC-003): the supervised writer (d4FirstAttempt true only, or an explicit outcome)."""
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from agent_braid import lightning_export as export
from agent_braid import trace_adapter
from tests.spec075_fixtures import consent, new_run, result, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())
ROLES = {'system', 'user', 'assistant', 'tool'}
RAW = ('raw-win', 'raw-lose', 'raw-none', 'raw-late', 'raw-group', 'raw-empty')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        consent(self.home)
        run = new_run(self.home)
        # rollout ids sort against task and group ids, so a wrong ordering key shows (E3)
        rollout(run, 'ro-1', 'raw-win', [('first ask h\u00e9llo', 'first answer', [{'name': 'Edit'}]),
                                         ('second ask', 'done')], d4=True)
        rollout(run, 'ro-2', 'raw-lose', [('try', 'wrong')], task='task-b', d4=False)
        rollout(run, 'ro-3', 'raw-none', [('ask', 'reply')], task='task-c', d4=None)
        rollout(run, 'ro-0', 'raw-late', [('z ask', 'z answer')], task='task-z', d4=True)
        rollout(run, 'ro-8', 'raw-group', [('g ask', 'g answer')], group='group-a', d4=True)
        rollout(run, 'ro-4', 'raw-empty', [None], task='task-d', d4=True)  # no content: excluded by select
        self.items, self.exclusions = export.select(export.read_runs(self.home, ['run-1']))

    def tearDown(self):
        self.tmp.cleanup()

    def assert_contract(self, lines, entries, *, outcome):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - development dependency
            self.skipTest('jsonschema is a development dependency')
        entry_schema = jsonschema.Draft202012Validator(SCHEMA['properties']['records']['items'])
        self.assertEqual(len(lines), len(entries))
        for line, entry in zip(lines, entries):
            self.assertTrue(line.endswith(b'\n'))
            record = json.loads(line)
            self.assertEqual(line, trace_adapter.canonical_bytes(record) + b'\n')
            self.assertTrue(line.isascii())
            self.assertEqual(set(record), {'recordId', 'messages', 'outcome'} if outcome else {'recordId', 'messages'})
            for message in record['messages']:
                self.assertIn(message['role'], ROLES)
                self.assertIsInstance(message['content'], str)
                self.assertLessEqual(set(message), {'role', 'content', 'toolCalls', 'toolCallId'})
            self.assertEqual(entry['sha256'], hashlib.sha256(line).hexdigest())
            self.assertEqual(entry['recordId'], record['recordId'])
            self.assertEqual(list(entry_schema.iter_errors(entry)), [])
            self.assertEqual(entry['consentLevel'], 'redacted')
            if outcome:
                self.assertEqual(record['outcome'], entry['outcome'])
            for raw in RAW:
                self.assertNotIn(raw.encode(), line)
                self.assertNotIn(raw, json.dumps(entry))


class SupervisedTests(Base):
    def keys(self, entries):
        return [(e['taskId'], e['groupId'], e['rolloutId'], e['turnRange'][0]) for e in entries]

    def test_transition_keeps_only_first_attempt_successes(self):
        self.assertEqual(self.exclusions['content-missing'], 1)
        lines, entries, left_out = export.supervised(self.items, level='transition')
        self.assert_contract(lines, entries, outcome=False)
        self.assertEqual(self.keys(entries), [('task-a', 'group-a', 'ro-8', 0), ('task-a', 'group-g', 'ro-1', 0),
                                              ('task-a', 'group-g', 'ro-1', 1), ('task-z', 'group-g', 'ro-0', 0)])
        self.assertEqual([json.loads(line)['messages'] for line in lines[1:3]], [
            [{'role': 'user', 'content': 'first ask h\u00e9llo'},
             {'role': 'assistant', 'content': 'first answer', 'toolCalls': [{'name': 'Edit'}]}],
            [{'role': 'user', 'content': 'second ask'}, {'role': 'assistant', 'content': 'done'}]])
        self.assertIn(b'h\\u00e9llo', lines[1])  # ensure_ascii, as the contract's serializer writes it
        self.assertEqual({(e['outcome'], tuple(e['limits'])) for e in entries}, {('success', ())})
        self.assertEqual(left_out, 2)  # the failure and the unknown outcome

    def test_outcome_field_keeps_every_record_with_its_outcome(self):
        lines, entries, left_out = export.supervised(self.items, level='transition', outcome_field=True)
        self.assert_contract(lines, entries, outcome=True)
        self.assertEqual([(e['taskId'], json.loads(line)['outcome']) for line, e in zip(lines, entries)],
                         [('task-a', 'success')] * 3 + [('task-b', 'failure'), ('task-c', 'unknown'),
                                                        ('task-z', 'success')])
        self.assertEqual(left_out, 0)

    def test_trajectory_merges_an_attempt_at_text_level(self):
        lines, entries, _ = export.supervised(self.items, level='trajectory')
        self.assert_contract(lines, entries, outcome=False)
        self.assertEqual([e['rolloutId'] for e in entries], ['ro-8', 'ro-1', 'ro-0'])
        self.assertEqual([m['role'] for m in json.loads(lines[1])['messages']], ['user', 'assistant'] * 2)
        self.assertEqual([(e['turnRange'], e['limits']) for e in entries],
                         [([0, 0], []), ([0, 1], ['text-level-merge']), ([0, 0], [])])  # one turn: nothing merged

    def test_output_is_sorted_and_independent_of_input_order(self):
        first = export.supervised(self.items, level='transition', outcome_field=True)
        shuffled = list(self.items)
        random.Random(7).shuffle(shuffled)
        self.assertEqual(export.supervised(shuffled, level='transition', outcome_field=True), first)
        keys = [(e['taskId'], e['groupId'], e['rolloutId'], e['attemptId'], e['turnRange'][0]) for e in first[1]]
        self.assertEqual(keys, sorted(keys))
        self.assertNotEqual([k[2] for k in keys], sorted(k[2] for k in keys))  # rollout order alone would differ

    def test_record_ids_are_unique_for_identical_content(self):
        run = new_run(self.home, 'run-2')
        rollout(run, 'ro-a', 'raw-a', [('same', 'same')])
        rollout(run, 'ro-b', 'raw-b', [('same', 'same')])
        items, _ = export.select(export.read_runs(self.home, ['run-2']))
        lines, entries, _ = export.supervised(items, level='transition')
        self.assertEqual(len({e['recordId'] for e in entries}), 2)
        self.assertEqual(len(set(lines)), 2)

    def test_host_model_output_is_refused_until_an_owner_terms_decision(self):
        run = new_run(self.home, 'run-host')
        rollout(run, 'ro-h', 'raw-host', [('host prompt', 'host answer')], label='host-run')
        rollout(run, 'ro-n', 'raw-nolabel', [('p', 'a')], label=None)  # no result: host-model too
        rollout(run, 'ro-m', 'raw-mixed', [('p2', 'a2')])
        run.append('result', result('run-host', 'ro-m', 'raw-mixed', 'host-run'))  # conflicting results
        items, _ = export.select(export.read_runs(self.home, ['run-host']))
        self.assertEqual([i['source'] for i in items], ['host-model'] * 3)
        for level in export.LEVELS:
            for outcome_field in (False, True):
                with self.subTest(level=level, outcome_field=outcome_field), \
                        self.assertRaises(export.ExportError) as caught:
                    export.supervised(self.items + items[:1], level=level, outcome_field=outcome_field)
                self.assertEqual(caught.exception.code, 'terms-gate-missing')
                self.assertNotIn('host', str(caught.exception).replace('Host-model', ''))

    def test_conflicting_results_are_host_model(self):
        run = new_run(self.home, 'run-mix')
        rollout(run, 'ro-m', 'raw-mixed', [('p', 'a')], label='host-run')
        run.append('result', result('run-mix', 'ro-m', 'raw-mixed', 'pipeline-only'))  # last one says fixture
        items, _ = export.select(export.read_runs(self.home, ['run-mix']))
        self.assertEqual([i['source'] for i in items], ['host-model'])

    def test_only_selected_items_are_written(self):
        unredacted = dict(self.items[0], triplet={**self.items[0]['triplet'],
                                                 'redaction': {'classes': {}, 'scanClean': False}})
        unfiltered = export.read_runs(self.home, ['run-1'])  # still holds the content-missing call
        for name, items in (('unredacted', [unredacted]), ('unfiltered', unfiltered), ('not items', [1]),
                            ('missing keys', [{'triplet': self.items[0]['triplet']}]), ('not a list', None)):
            with self.subTest(name=name), self.assertRaises(export.ExportError) as caught:
                export.supervised(items, level='transition', outcome_field=True)
            self.assertEqual(caught.exception.code, 'invalid-argument')

    def test_written_records_are_checked(self):
        broken = dict(self.items[0], triplet={**self.items[0]['triplet'],
                                             'response': {'text': 'x', 'toolCalls': 'Edit'}})
        with self.assertRaises(export.ExportError) as caught:
            export.supervised([broken], level='transition')
        self.assertEqual(caught.exception.code, 'invalid-record')

    def test_run_id_is_the_last_tiebreaker(self):
        item = self.items[0]
        self.assertEqual(export._sort_key(item), (item['taskId'], item['groupId'], item['rolloutId'],
                                                  item['attemptId'], item['turnIndex'], item['runId']))

    def test_invalid_arguments_are_refused(self):
        for kwargs in ({'level': 'step'}, {'level': 'transition', 'outcome_field': 'yes'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(export.ExportError) as caught:
                export.supervised(self.items, **kwargs)
            self.assertEqual(caught.exception.code, 'invalid-argument')


class RecordShapeTests(unittest.TestCase):
    def good(self, **overrides):
        value = {'recordId': 'r-0123456789abcdef', 'messages': [{'role': 'user', 'content': 'a'},
                                                                 {'role': 'assistant', 'content': 'b'}]}
        value.update(overrides)
        return value

    def test_check_accepts_the_contract_shape(self):
        export.check_supervised(self.good())
        export.check_supervised(self.good(outcome='failure'), outcome_field=True)
        export.check_supervised(self.good(messages=[{'role': 'tool', 'content': 'x', 'toolCallId': 'c1'}]))

    def test_check_refuses_other_shapes(self):
        cases = {
            'unknown role': self.good(messages=[{'role': 'critic', 'content': 'x'}]),
            'non-text content': self.good(messages=[{'role': 'user', 'content': {'text': 'x'}}]),
            'unknown message key': self.good(messages=[{'role': 'user', 'content': 'x', 'name': 'n'}]),
            'tool without id': self.good(messages=[{'role': 'tool', 'content': 'x'}]),
            'no messages': self.good(messages=[]),
            'unknown key': self.good(extra=1),
            'outcome without the flag': self.good(outcome='success'),
            'bad record id': self.good(recordId='record-1'),
            'tool calls not a list': self.good(messages=[{'role': 'assistant', 'content': 'x', 'toolCalls': 'Edit'}]),
            'tool calls on a user message': self.good(messages=[{'role': 'user', 'content': 'x', 'toolCalls': []}]),
        }
        for name, value in cases.items():
            with self.subTest(name=name), self.assertRaises(export.ExportError) as caught:
                export.check_supervised(value)
            self.assertEqual(caught.exception.code, 'invalid-record')
        for missing in (self.good(), self.good(outcome='partial')):
            with self.assertRaises(export.ExportError):  # failed record without an explicit outcome field
                export.check_supervised(missing, outcome_field=True)


if __name__ == '__main__':
    unittest.main()
