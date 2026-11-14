# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-006 / SC-006 (T007): triplets and messages from rollout records and the Loom stream."""
from contextlib import redirect_stdout
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_adapter as adapter
from agent_braid import lightning_redact as redact
from agent_braid import lightning_store as store
from agent_braid.cli import main
from agent_braid.lightning_schema import EVENT_SCHEMA, Event

ROOT = Path(__file__).resolve().parents[1]
LOOM = ROOT / 'tests/fixtures/view/loom/valid-corpus.jsonl'
DIGEST = 'c' * 64
T0 = 1_800_000_000.0
TOKEN = 'sk-' + 'A1b2C3d4' * 3  # synthetic canary
EMAIL = 'owner@example.org'
SALT = b's' * 16


def cli(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


def event(sequence, event_type, data):
    return Event.parse({'schema': EVENT_SCHEMA, 'rolloutId': 'ro-1', 'attemptId': 'at-1', 'sequence': sequence,
                        'eventType': event_type, 'timestamp': T0 + sequence, 'data': data})


def request(sequence):
    return event(sequence, 'model_request', {'requestSha256': DIGEST, 'responseSha256': DIGEST, 'latencyMs': 5,
                                             'status': 'ok', 'retryCount': 0, 'finishReason': None})


def reward(sequence, value):
    return event(sequence, 'reward', {'reward': {'value': value, 'components': {}, 'source': 'verifier',
                                                 'reason': None}})


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def consent(self, sources='rollout,loom'):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', sources]
        _, out, _ = cli(*flags)
        code, _, err = cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
        self.assertEqual(code, 0, err)

    def attempt(self, *, content=True):
        run = store.RunStore(self.home, 'run-1', content_consent='redacted' if content else None)
        run.create(config_digest=DIGEST, now=T0)
        for item in (request(1), reward(2, 0.25), request(3), request(4), reward(5, 1.0)):
            run.append('event', item)
        if content:
            run.append('trace', {'attemptId': 'at-1', 'sequence': 1, 'prompt': f'mail {EMAIL}',
                                 'response': f'key {TOKEN}', 'toolCalls': [{'name': 'Edit'}]}, now=T0 + 1)
            run.append('trace', {'attemptId': 'at-1', 'sequence': 3, 'prompt': 'plain', 'response': None}, now=T0 + 3)
        return run

    def assert_clean(self, value):
        text = json.dumps(value)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn(EMAIL, text)
        self.assertEqual(redact.Redactor(SALT).scan(text), [])

    def test_rollout_triplets_are_redacted_with_rewards_and_losses(self):
        self.consent()
        self.attempt()
        triplets = adapter.rollout_triplets(self.home, 'run-1', 'at-1')
        self.assert_clean(triplets)
        self.assertEqual([t['reward'] for t in triplets], [0.25, None, 1.0])
        first, second, third = triplets
        self.assertEqual(first['schema'], adapter.TRIPLET_SCHEMA)
        self.assertEqual((first['source'], first['rolloutId'], first['attemptId']), ('rollout', 'ro-1', 'at-1'))
        self.assertRegex(first['prompt']['text'], r'^mail \[REDACTED:email:[0-9a-f]{8}\]$')
        self.assertEqual(first['response'], {'text': 'key [REDACTED:token]', 'toolCalls': [{'name': 'Edit'}]})
        self.assertEqual(first['redaction'], {'classes': {'email': 1, 'token': 1}, 'scanClean': True})
        self.assertEqual((first['losses'], first['createdAt']), ([], T0 + 1))
        self.assertEqual((second['response'], second['losses']), (None, ['response-missing', 'reward-unmatched']))
        self.assertEqual(third['losses'], ['content-missing'])
        self.assertEqual(len({t['sourceSha256'] for t in triplets}), 1)

    def test_first_sibling_gives_the_first_reward_to_the_first_request(self):
        self.consent()
        self.attempt()
        triplets = adapter.rollout_triplets(self.home, 'run-1', 'at-1', reward_match='first-sibling')
        self.assertEqual([t['reward'] for t in triplets], [0.25, None, None])
        self.assertEqual({t['rewardMatch'] for t in triplets}, {'first-sibling'})
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.rollout_triplets(self.home, 'run-1', 'at-1', reward_match='last')
        self.assertEqual(caught.exception.code, 'reward-match')

    def test_outputs_are_deterministic(self):
        self.consent()
        self.attempt()
        self.assertEqual(adapter.rollout_triplets(self.home, 'run-1', 'at-1'),
                         adapter.rollout_triplets(self.home, 'run-1', 'at-1'))
        data = LOOM.read_bytes()
        self.assertEqual(adapter.loom_triplets(self.home, data, SALT), adapter.loom_triplets(self.home, data, SALT))

    def test_rollout_messages_follow_the_turns(self):
        self.consent()
        self.attempt()
        record = adapter.rollout_messages(self.home, 'run-1', 'at-1')
        self.assert_clean(record)
        self.assertEqual(record['schema'], adapter.MESSAGES_SCHEMA)
        self.assertEqual([m['role'] for m in record['messages']], ['user', 'assistant', 'user'])
        self.assertEqual(record['messages'][1]['toolCalls'], [{'name': 'Edit'}])
        self.assertEqual(record['losses'], ['content-missing', 'response-missing'])

    def test_without_consent_outputs_are_content_free(self):
        self.attempt(content=False)
        triplets = adapter.rollout_triplets(self.home, 'run-1', 'at-1')
        self.assertTrue(all(t['prompt'] is None and t['response'] is None for t in triplets))
        self.assertTrue(all('content-consent-required' in t['losses'] for t in triplets))
        self.assertEqual([t['reward'] for t in triplets], [0.25, None, 1.0])
        messages = adapter.loom_messages(self.home, LOOM.read_bytes(), SALT)
        self.assertEqual((messages['messages'], messages['losses']), ([], ['content-consent-required']))

    def test_unlisted_source_reads_as_no_content(self):
        self.consent('rollout')
        record = adapter.loom_messages(self.home, LOOM.read_bytes(), SALT)
        self.assertEqual(record['messages'], [])
        self.assertIn('content-consent-required', record['losses'])

    def test_loom_messages_and_triplets(self):
        self.consent()
        data = LOOM.read_bytes()
        record = adapter.loom_messages(self.home, data, SALT)
        self.assert_clean(record)
        self.assertEqual(record['sourceSha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(len(record['messages']), len(data.splitlines()))
        self.assertEqual({m['role'] for m in record['messages']}, {'system'})
        triplets = {t['attemptId']: t for t in adapter.loom_triplets(self.home, data, SALT)}
        strand = triplets['op-a']
        self.assertEqual(strand['prompt'], {'text': 'Review é ✓'})
        self.assertEqual(strand['response'], {'text': 'cancelled', 'toolCalls': ['Edit']})
        self.assertEqual(strand['losses'], ['model-text-unavailable', 'reward-unavailable'])
        self.assertIn('outcome-missing', next(t for k, t in triplets.items() if k != 'op-a')['losses'])

    def test_loom_text_is_redacted(self):
        self.consent()
        line = json.loads(LOOM.read_bytes().splitlines()[2])
        line['data']['label'] = f'ask {EMAIL} with {TOKEN}'
        data = json.dumps(line, separators=(',', ':')).encode()
        self.assertIn(TOKEN.encode(), data)  # negative control: the canary is in the source
        [triplet] = adapter.loom_triplets(self.home, data, SALT)
        self.assert_clean(triplet)
        self.assertEqual(triplet['redaction']['classes'], {'email': 1, 'token': 1})
        self.assert_clean(adapter.loom_messages(self.home, data, SALT))

    def test_unredacted_output_is_detected(self):
        """Negative control: with redaction switched off the canary reaches the output, and the check fails."""
        self.consent()
        data = LOOM.read_bytes().splitlines()[2].replace(b'Review', TOKEN.encode())
        with patch.object(redact.Redactor, 'clean', lambda self, value: value):
            with self.assertRaises(AssertionError):
                self.assert_clean(adapter.loom_triplets(self.home, data, SALT))

    def test_a_duplicate_content_record_keeps_the_first(self):
        self.consent()
        run = self.attempt()
        run.append('trace', {'attemptId': 'at-1', 'sequence': 1, 'prompt': 'second', 'response': 'x'}, now=T0 + 9)
        first = adapter.rollout_triplets(self.home, 'run-1', 'at-1')[0]
        self.assertTrue(first['prompt']['text'].startswith('mail '))
        self.assertIn('content-duplicate', first['losses'])

    def test_invalid_sources_are_refused(self):
        self.consent()
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.loom_messages(self.home, b'{"seq":1}\n', SALT)
        self.assertEqual(caught.exception.code, 'source-invalid')
        self.attempt()
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.rollout_triplets(self.home, 'run-1', 'at-missing')
        self.assertEqual(caught.exception.code, 'source-invalid')


if __name__ == '__main__':
    unittest.main()
