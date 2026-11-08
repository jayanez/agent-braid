# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 REQ-003: Braid Lightning record model."""
import json
import unittest

from agent_braid import lightning_schema as s

SHA = 'a' * 64


def rollout(**changes):
    value = s.new_rollout('r-1', 'task-1', 'group-1', SHA, 'b' * 64, 'claude-code', at=10.0).to_dict()
    value.update(changes)
    return value


def event(event_type='reward', data=None, **changes):
    data = data if data is not None else {'reward': {'value': 0.5, 'components': {'schema': 1.0, 'd4': 0.0},
                                                    'source': 'verifier', 'reason': None}}
    value = {'schema': s.EVENT_SCHEMA, 'rolloutId': 'r-1', 'attemptId': '0', 'sequence': 0,
             'eventType': event_type, 'timestamp': 11.0, 'data': data}
    value.update(changes)
    return value


class RecordTests(unittest.TestCase):
    def test_rollout_round_trips_canonically(self):
        parsed = s.Rollout.parse(rollout())
        raw = s.canonical_bytes(parsed.to_dict())
        self.assertEqual(s.canonical_bytes(s.Rollout.parse(s.loads(raw)).to_dict()), raw)
        self.assertTrue(raw.endswith(b'\n') and b' ' not in raw)

    def test_unknown_and_missing_keys_are_refused(self):
        with self.assertRaises(s.LightningSchemaError) as caught:
            s.Rollout.parse(rollout(prompt='hello'))
        self.assertEqual(caught.exception.code, 'record-unknown-key')
        value = rollout()
        del value['groupId']
        with self.assertRaises(s.LightningSchemaError) as caught:
            s.Rollout.parse(value)
        self.assertEqual(caught.exception.code, 'record-missing-key')

    def test_types_identifiers_and_digests_are_checked(self):
        for changes, code in (({'rolloutId': '../x'}, 'record-identifier'), ({'candidateSha256': 'A' * 64}, 'record-digest'),
                              ({'host': 'codex'}, 'record-enum'), ({'isTrain': 1}, 'record-type'),
                              ({'timeoutSeconds': 0}, 'record-range'), ({'schema': 'other'}, 'record-schema')):
            with self.subTest(changes=changes), self.assertRaises(s.LightningSchemaError) as caught:
                s.Rollout.parse(rollout(**changes))
            self.assertEqual(caught.exception.code, code)

    def test_duplicate_keys_and_nonfinite_numbers_are_refused(self):
        with self.assertRaises(s.LightningSchemaError):
            s.loads('{"a": 1, "a": 2}')
        with self.assertRaises(s.LightningSchemaError):
            s.loads('{"a": NaN}')
        with self.assertRaises(s.LightningSchemaError):
            s.Event.parse(event(timestamp=float('inf')))

    def test_state_machine_follows_upstream_transitions(self):
        value = s.Rollout.parse(rollout())
        running = value.transition(s.RUNNING, 12.0, attempt_id='0')
        done = running.transition(s.SUCCEEDED, 13.0)
        self.assertEqual((done.status.state, done.status.version, done.status.last_attempt_id), ('succeeded', 3, '0'))
        for start, target in ((value, s.SUCCEEDED), (done, s.RUNNING), (done, s.FAILED)):
            with self.subTest(target=target), self.assertRaises(s.LightningSchemaError) as caught:
                start.transition(target, 20.0)
            self.assertEqual(caught.exception.code, 'record-transition')
        failed = value.transition(s.FAILED, 12.0, error_code='timeout')
        self.assertEqual(failed.status.error_code, 'timeout')
        with self.assertRaises(s.LightningSchemaError):
            value.transition(s.RUNNING, 12.0, error_code='timeout')
        with self.assertRaises(s.LightningSchemaError):
            value.transition(s.RUNNING, 5.0)  # time cannot go backwards

    def test_events_have_closed_types_and_payloads(self):
        self.assertEqual(s.Event.parse(event()).data['reward']['components'], {'d4': 0.0, 'schema': 1.0})
        request = {'requestSha256': SHA, 'responseSha256': None, 'latencyMs': 3, 'status': 'ok',
                   'retryCount': 0, 'finishReason': 'stop'}
        self.assertEqual(s.Event.parse(event('model_request', request)).event_type, 'model_request')
        for kind, data in (('model_request', dict(request, messages=[])), ('note', {}),
                           ('reward', {'reward': {'value': 2, 'components': {}, 'source': 'verifier', 'reason': None}}),
                           ('reward', {'reward': {'value': 1, 'components': {}, 'source': 'judge', 'reason': None}})):
            with self.subTest(kind=kind), self.assertRaises(s.LightningSchemaError):
                s.Event.parse(event(kind, data))

    def test_parse_record_dispatches_on_schema_only(self):
        self.assertIsInstance(s.parse_record(rollout()), s.Rollout)
        self.assertIsInstance(s.parse_record(event()), s.Event)
        with self.assertRaises(s.LightningSchemaError):
            s.parse_record({'schema': 'braid-lightning-trace/v0.1'})

    def test_records_carry_no_free_text_fields(self):
        text = json.dumps([rollout(), event()])
        for word in ('prompt', 'response', 'messages', 'content'):
            self.assertNotIn(f'"{word}"', text)


if __name__ == '__main__':
    unittest.main()
