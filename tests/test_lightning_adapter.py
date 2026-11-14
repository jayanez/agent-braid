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

from agent_braid import analysis
from agent_braid import lightning_adapter as adapter
from agent_braid import system_one_shadow as shadow
from agent_braid import trace_adapter
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
TRACE = ROOT / 'specs/023-recorded-trace-adapters/fixtures/generic.json'
SAMPLE = json.loads((ROOT / 'examples/analysis/file-edits.json').read_text())


def trace_bytes(tool=None, attempt=None, reverse=False):
    value = json.loads(TRACE.read_text())
    if tool:
        value['operations'][0]['definition']['id'] = tool
    if attempt:
        value['operations'][0]['attemptId'] = attempt
    if reverse:  # source order differs from the projection's instanceId order
        value['operations'].reverse()
    value['source']['contentDigest'] = trace_adapter.digest_bytes(trace_adapter.canonical_bytes(
        {'operations': value['operations'], 'events': value['events']}))
    return trace_adapter.canonical_bytes(value)


def episode_line():
    episode = shadow.build_episode(analysis.analyze(SAMPLE), 'analyze-work', 'aim', request=SAMPLE)
    return json.dumps(episode, sort_keys=True).encode() + b'\n'


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
        self.assertEqual((first['source'], first['rolloutId'], first['attemptId']),
                         ('rollout', 'ro-1', adapter._pseudonym(store.RunStore(self.home, 'run-1')._salt(), 'at-1',
                                                                 'attempt')))
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
        self.assertEqual((record['messages'], record['losses']), ([], ['source-not-consented']))
        path = self.write('ok.jsonl', episode_line())
        self.assertEqual(adapter.system_one_messages(self.home, path, SALT)['losses'], ['source-not-consented'])
        self.assertIn('source-not-consented', adapter.transcript_triplets(self.home, self.write(
            'trace.json', trace_bytes()), SALT)[0]['losses'])

    def test_loom_messages_and_triplets(self):
        self.consent()
        data = LOOM.read_bytes()
        record = adapter.loom_messages(self.home, data, SALT)
        self.assert_clean(record)
        self.assertEqual(record['sourceSha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(len(record['messages']), len(data.splitlines()))
        self.assertEqual({m['role'] for m in record['messages']}, {'system'})
        triplets = {t['attemptId']: t for t in adapter.loom_triplets(self.home, data, SALT)}
        strand = triplets[adapter._pseudonym(SALT, 'op-a', 'strand')]
        self.assertEqual(strand['prompt'], {'text': 'Review é ✓'})
        self.assertEqual(strand['response'], {'text': 'cancelled', 'toolCalls': ['Edit']})
        self.assertEqual(strand['losses'], ['model-text-unavailable', 'reward-unavailable'])
        self.assertIn('outcome-missing', next(t for t in triplets.values() if t is not strand)['losses'])

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

    def test_loom_strand_ids_are_pseudonyms(self):
        """Strand and operation ids are free text (a key or a name is a valid id), so no output carries one; each
        is named once per stream, at its schema position only, and the triplet and the messages agree."""
        self.consent()
        events = [json.loads(line) for line in LOOM.read_bytes().splitlines()]
        child = events[3]['data']['strandId']
        ids = {'op-a': TOKEN, 'op-b': 'owner.example.org',  # op-b is only in waves
               'unit-1': 'nia.example.com'}  # unit-1 is only in hazard units; the child keeps its sha256 id, which
        # is also the reportId, planId, scheduleId and manifestDigest: those must keep it while the strand is renamed

        def swap(value):
            return ids.get(value, value)
        for event in events:
            data = event['data']
            for key in ('strandId', 'parentStrandId', 'left', 'right'):
                if key in data:
                    data[key] = swap(data[key])
            for key in ('strands', 'units'):
                if key in data:
                    data[key] = [swap(item) for item in data[key]]
            if 'waves' in data:
                data['waves'] = [[swap(item) for item in wave] for wave in data['waves']]
        waiting = json.loads(json.dumps(events[4]))  # a v0.2 update of the child, waiting on a name-shaped target
        waiting.update(seq=events[-1]['seq'] + 1, schemaVersion='agent-braid-loom/v0.2')
        waiting['data'].update(strandId=child, state='waiting', toolName=None,
                               waitingOn='mira.lopez', waitingBasis='declared')
        events.append(waiting)
        data = b''.join(json.dumps(e, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode() + b'\n'
                        for e in events)
        secrets = ('owner.example.org', 'mira.lopez', 'nia.example.com')  # not redactable: only renaming hides them
        for secret in (TOKEN, *secrets):
            self.assertIn(secret.encode(), data)  # negative control: every id is in the source
        triplets = adapter.loom_triplets(self.home, data, SALT)
        messages = adapter.loom_messages(self.home, data, SALT)
        text = json.dumps([triplets, messages])
        for secret in (TOKEN, *secrets):
            self.assertNotIn(secret, text)
        out = [json.loads(m['content']) for m in messages['messages']]
        name = adapter._pseudonym(SALT, TOKEN, 'strand')
        self.assertRegex(name, r'^strand-[0-9a-f]{16}$')
        self.assertNotEqual(name.split('-', 1)[1], adapter._pseudonym(SALT, TOKEN).split('-', 1)[1])  # own domain
        opened = next(m['data'] for m in out if m['kind'] == 'strand.open' and m['data']['label'] == 'Review é ✓')
        self.assertEqual(opened['strandId'], name)
        self.assertIn(name, {t['attemptId'] for t in triplets})  # the triplet uses the message's name
        self.assertEqual(out[-1]['data']['waitingOn'], adapter._pseudonym(SALT, 'mira.lopez', 'strand'))
        planned = next(m['data'] for m in out if m['kind'] == 'wave.planned')
        self.assertIn(adapter._pseudonym(SALT, 'owner.example.org', 'strand'), planned['waves'][1])
        for kind, key in (('analysis.report', 'reportId'), ('wave.planned', 'planId'),
                          ('runtime.phase', 'manifestDigest'), ('crossing.classified', 'reportId')):
            source = next(e['data'][key] for e in events if e['kind'] == kind)
            self.assertEqual(next(m['data'][key] for m in out if m['kind'] == kind), source, key)  # not renamed
        self.assertEqual({e['data'][key] for e in events for key in ('reportId', 'planId', 'manifestDigest')
                          if key in e['data']}, {child})  # negative control: the child's id is in those fields
        self.assertEqual(out[-1]['data']['strandId'], adapter._pseudonym(SALT, child, 'strand'))  # same value renamed
        self.assertEqual(triplets, adapter.loom_triplets(self.home, data, SALT))  # deterministic for one salt
        self.assertNotIn(name, json.dumps(adapter.loom_triplets(self.home, data, b't' * 16)))
        with patch.object(adapter, '_pseudonym', lambda salt, value, kind='turn': 'strand-0'):
            with self.assertRaises(adapter.AdapterError) as caught:  # names must be injective
                adapter.loom_messages(self.home, data, SALT)
        self.assertEqual((caught.exception.code, str(caught.exception)),
                         ('source-invalid', 'Loom strand pseudonyms collide'))

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

    def write(self, name, data):
        path = Path(self.tmp.name).resolve() / 'sources' / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
        return path

    def test_host_transcript_turns(self):
        self.consent('rollout,host-transcript')
        path = self.write('trace.json', trace_bytes())
        triplets = adapter.transcript_triplets(self.home, path, SALT)
        self.assertEqual([t['response']['toolCalls'] for t in triplets], [['edit-left'], ['edit-right']])
        self.assertTrue(all(t['attemptId'].startswith('turn-') for t in triplets))
        first = triplets[0]
        self.assertEqual((first['source'], first['prompt'], first['reward']), ('host-transcript', None, None))
        self.assertEqual(first['response'], {'text': '', 'toolCalls': ['edit-left']})
        self.assertEqual(first['losses'], ['model-text-unavailable', 'prompt-missing', 'reward-unavailable'])
        self.assertEqual(first['sourceSha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        record = adapter.transcript_messages(self.home, path, SALT)
        self.assertEqual(len(record['messages']), 2)
        self.assertIn('edit-left', record['messages'][0]['content'])
        self.assertIn(first['attemptId'], record['messages'][0]['content'])
        self.assertFalse(record['messages'][0]['content'].endswith('\n'))
        self.assertEqual(record['losses'], ['model-text-unavailable', 'prompt-missing'])

    def test_host_transcript_keeps_source_order(self):
        self.consent('rollout,host-transcript')
        path = self.write('trace.json', trace_bytes(reverse=True))
        triplets = adapter.transcript_triplets(self.home, path, SALT)
        self.assertEqual([t['response']['toolCalls'] for t in triplets], [['edit-right'], ['edit-left']])

    def test_host_transcript_attempt_id_is_pseudonymised(self):
        path = self.write('trace.json', trace_bytes(attempt=EMAIL))
        self.assertIn(EMAIL.encode(), path.read_bytes())  # negative control
        for consent in ('rollout', 'rollout,host-transcript'):
            self.consent(consent)
            triplets = adapter.transcript_triplets(self.home, path, SALT)
            record = adapter.transcript_messages(self.home, path, SALT)
            self.assert_clean(triplets)
            self.assert_clean(record)
            self.assertNotIn(EMAIL, json.dumps([triplets, record]))

    def test_host_transcript_is_redacted_gated_and_validated(self):
        self.consent('rollout,host-transcript')
        path = self.write('trace.json', trace_bytes(tool=f'tool:{EMAIL}'))
        self.assertIn(EMAIL.encode(), path.read_bytes())  # negative control
        self.assert_clean(adapter.transcript_triplets(self.home, path, SALT))
        self.assert_clean(adapter.transcript_messages(self.home, path, SALT))
        bad = self.write('bad.json', b'{}')
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.transcript_triplets(self.home, bad, SALT)
        self.assertEqual(caught.exception.code, 'source-invalid')
        self.consent('rollout')
        self.assertTrue(all(t['response'] is None and 'source-not-consented' in t['losses']
                            for t in adapter.transcript_triplets(self.home, path, SALT)))

    def test_system_one_episodes_are_read_only(self):
        self.consent('rollout,system-one')
        path = self.write('episodes-2026-11-14.jsonl', episode_line() * 2)
        path.chmod(0o400)
        before = (path.read_bytes(), path.stat().st_mtime_ns, sorted(path.parent.iterdir()))
        triplets = adapter.system_one_triplets(self.home, path, SALT)
        record = adapter.system_one_messages(self.home, path, SALT)
        self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns, sorted(path.parent.iterdir())), before)
        self.assertEqual(len(triplets), 2)
        self.assertEqual(triplets[0]['losses'], ['reward-unavailable'])
        self.assertIn('independent-candidate', triplets[0]['prompt']['text'])
        self.assertIn('status', triplets[0]['response']['text'])
        self.assertEqual([m['role'] for m in record['messages']], ['user', 'assistant'] * 2)
        self.assert_clean(record)

    def test_system_one_refusals(self):
        self.consent('rollout,system-one')
        for bad in (None, self.write('dir', b'').parent, Path(self.tmp.name) / 'missing.jsonl'):
            with self.assertRaises(adapter.AdapterError) as caught:
                adapter.system_one_triplets(self.home, bad, SALT)
            self.assertEqual(caught.exception.code, 'source-invalid')


    def test_system_one_invalid_and_torn_lines_are_skipped_like_the_report(self):
        self.consent('rollout,system-one')
        torn = episode_line() + b'{"schemaVersion":"x"}\n' + episode_line()[:-9]
        path = self.write('episodes-2026-11-14.jsonl', torn)
        triplets = adapter.system_one_triplets(self.home, path, SALT)
        self.assertEqual([t['losses'] for t in triplets], [['episode-invalid', 'reward-unavailable']])
        self.assertEqual(adapter.system_one_messages(self.home, path, SALT)['losses'], ['episode-invalid'])
        _, episodes, invalid = shadow.read_day(path)  # the report's reader agrees
        self.assertEqual((len(episodes), invalid), (1, 2))


if __name__ == '__main__':
    unittest.main()
