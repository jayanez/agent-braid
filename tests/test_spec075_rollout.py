# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T005 (REQ-004 / SC-004): the rollout writer at the transition and trajectory levels."""
import hashlib
import json
from pathlib import Path
import random
import tempfile
import unittest

from agent_braid import lightning_export as export
from agent_braid import trace_adapter
from tests.spec075_fixtures import consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())
REWARD = {'value': 1.0, 'components': {'schema': 1.0, 'd4': 1.0, 'canary': 1.0}, 'source': 'verifier', 'reason': None}
RAW = ('raw-three', 'raw-other')


def with_tokens(item, prompt, response):
    triplet = item['triplet']
    return dict(item, triplet={**triplet, 'prompt': {**triplet['prompt'], 'tokenIds': prompt},
                               'response': {**triplet['response'], 'tokenIds': response}})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        consent(self.home)
        run = new_run(self.home)
        rollout(run, 'ro-1', 'raw-three', [('ask one héllo', 'answer one', [{'name': 'Edit'}]),
                                           ('ask two', 'answer two'), ('ask three', 'answer three')],
                status='succeeded')
        rollout(run, 'ro-2', 'raw-other', [('try', 'wrong')], task='task-b', d4=False, status='failed')
        self.items, _ = export.select(export.read_runs(self.home, ['run-1']))
        self.three = [i for i in self.items if i['rolloutId'] == 'ro-1']

    def tearDown(self):
        self.tmp.cleanup()

    def assert_contract(self, lines, entries):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - development dependency
            self.skipTest('jsonschema is a development dependency')
        entry_schema = jsonschema.Draft202012Validator(SCHEMA['properties']['records']['items'])
        self.assertEqual(len(lines), len(entries))
        for line, entry in zip(lines, entries):
            record = json.loads(line)
            self.assertEqual(line, trace_adapter.canonical_bytes(record) + b'\n')
            export.check_rollout(record)
            self.assertEqual(set(record), {'recordId', 'rolloutId', 'attemptId', 'turns', 'reward', 'status'})
            self.assertEqual((record['recordId'], record['rolloutId'], record['attemptId']),
                             (entry['recordId'], entry['rolloutId'], entry['attemptId']))
            self.assertEqual(entry['sha256'], hashlib.sha256(line).hexdigest())
            self.assertEqual(list(entry_schema.iter_errors(entry)), [])
            for raw in RAW:
                self.assertNotIn(raw.encode(), line)
                self.assertNotIn(raw, json.dumps(entry))


class LevelTests(Base):
    def test_transition_yields_one_record_per_model_call(self):
        lines, entries = export.rollout_records(self.three, level='transition')
        self.assert_contract(lines, entries)
        self.assertEqual(len(lines), 3)
        records = [json.loads(line) for line in lines]
        self.assertEqual([r['turns'] for r in records], [
            [{'prompt': 'ask one héllo', 'response': 'answer one', 'toolCalls': [{'name': 'Edit'}]}],
            [{'prompt': 'ask two', 'response': 'answer two', 'toolCalls': []}],
            [{'prompt': 'ask three', 'response': 'answer three', 'toolCalls': []}]])
        self.assertEqual({(json.dumps(r['reward'], sort_keys=True), r['status']) for r in records},
                         {(json.dumps(REWARD, sort_keys=True), 'succeeded')})  # the SPEC-071 vector, unchanged
        self.assertEqual([(e['turnRange'], e['limits']) for e in entries],
                         [([0, 0], []), ([1, 1], []), ([2, 2], [])])

    def test_trajectory_merges_a_rollout_and_declares_the_text_level_limit(self):
        lines, entries = export.rollout_records(self.three, level='trajectory')
        self.assert_contract(lines, entries)
        self.assertEqual(len(lines), 1)
        self.assertEqual(len(json.loads(lines[0])['turns']), 3)
        self.assertEqual((entries[0]['turnRange'], entries[0]['limits'], entries[0]['outcome']),
                         ([0, 2], ['text-level-merge'], 'success'))

    def test_token_ids_merge_only_when_every_turn_carries_a_prefix_chain(self):
        first, second, third = self.three
        chained = [with_tokens(first, [1, 2], [3]), with_tokens(second, [1, 2, 3, 4], [5]),
                   with_tokens(third, [1, 2, 3, 4, 5, 6], [7])]
        _, entries = export.rollout_records(chained, level='trajectory')
        self.assertEqual(entries[0]['limits'], [])
        broken = [chained[0], with_tokens(second, [9, 9], [5]), chained[2]]
        partial = [chained[0], second, chained[2]]  # one turn without token ids: never a token-ID merge
        malformed = [chained[0], with_tokens(second, [1, 2, 3, 'x'], [5]), chained[2]]
        for name, items in (('not a prefix', broken), ('partial', partial), ('malformed', malformed)):
            with self.subTest(name=name):
                self.assertEqual(export.rollout_records(items, level='trajectory')[1][0]['limits'],
                                 ['text-level-merge'])
        self.assertNotIn(b'tokenIds', b''.join(export.rollout_records(chained, level='trajectory')[0]))

    def test_one_call_trajectory_merges_nothing(self):
        other = [i for i in self.items if i['rolloutId'] == 'ro-2']
        lines, entries = export.rollout_records(other, level='trajectory')
        self.assertEqual((entries[0]['limits'], entries[0]['outcome']), ([], 'failure'))
        self.assertEqual(json.loads(lines[0])['status'], 'failed')

    def test_order_is_e3_and_independent_of_input(self):
        result = export.rollout_records(self.items, level='transition')
        shuffled = list(self.items)
        random.Random(3).shuffle(shuffled)
        self.assertEqual(export.rollout_records(shuffled, level='transition'), result)
        self.assertEqual([e['rolloutId'] for e in result[1]], ['ro-1'] * 3 + ['ro-2'])


class GateTests(Base):
    def test_host_model_and_unselected_items_are_refused(self):
        run = new_run(self.home, 'run-host')
        rollout(run, 'ro-h', 'raw-host', [('host prompt', 'host answer')], label='host-run')
        host, _ = export.select(export.read_runs(self.home, ['run-host']))
        for level in export.LEVELS:
            with self.subTest(level=level), self.assertRaises(export.ExportError) as caught:
                export.rollout_records(self.items + host, level=level)
            self.assertEqual(caught.exception.code, 'terms-gate-missing')
        unfiltered = export.read_runs(self.home, ['run-1']) + [dict(self.items[0], triplet={
            **self.items[0]['triplet'], 'redaction': {'classes': {}, 'scanClean': False}})]
        with self.assertRaises(export.ExportError) as caught:
            export.rollout_records(unfiltered, level='transition')
        self.assertEqual(caught.exception.code, 'invalid-argument')
        with self.assertRaises(export.ExportError) as caught:
            export.rollout_records(self.items, level='step')
        self.assertEqual(caught.exception.code, 'invalid-argument')

    def test_written_records_are_checked(self):
        broken = dict(self.items[0], triplet={**self.items[0]['triplet'],
                                             'response': {'text': 'x', 'toolCalls': 'Edit'}})
        with self.assertRaises(export.ExportError) as caught:
            export.rollout_records([broken], level='transition')
        self.assertEqual(caught.exception.code, 'invalid-record')


class RecordShapeTests(unittest.TestCase):
    def good(self, **overrides):
        value = {'recordId': 'r-0123456789abcdef', 'rolloutId': 'ro-1', 'attemptId': 'attempt-0123456789abcdef',
                 'turns': [{'prompt': 'p', 'response': 'r', 'toolCalls': []}], 'reward': REWARD,
                 'status': 'succeeded'}
        value.update(overrides)
        return value

    def test_check_refuses_other_shapes(self):
        export.check_rollout(self.good())
        export.check_rollout(self.good(reward=None, status='running'))
        cases = {
            'unknown key': self.good(extra=1),
            'raw attempt id': self.good(attemptId='raw-three'),
            'no turns': self.good(turns=[]),
            'turn key': self.good(turns=[{'prompt': 'p', 'response': 'r', 'toolCalls': [], 'tokenIds': [1]}]),
            'turn text': self.good(turns=[{'prompt': None, 'response': 'r', 'toolCalls': []}]),
            'tool calls': self.good(turns=[{'prompt': 'p', 'response': 'r', 'toolCalls': 'Edit'}]),
            'reward': self.good(reward=0.5),
            'reward keys': self.good(reward={'value': 1.0}),
            'status': self.good(status='done'),
            'record id': self.good(recordId='r-1'),
        }
        for name, value in cases.items():
            with self.subTest(name=name), self.assertRaises(export.ExportError) as caught:
                export.check_rollout(value)
            self.assertEqual(caught.exception.code, 'invalid-record')


if __name__ == '__main__':
    unittest.main()
