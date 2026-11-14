# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T003 (REQ-002 / SC-002): only consented, redacted adapter output is exported; every drop is counted."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_export as export
from agent_braid import lightning_store as store
from agent_braid.cli import main
from agent_braid.lightning_schema import EVENT_SCHEMA, Event, new_rollout

DIGEST = 'c' * 64
T0 = 1_800_000_000.0
RAW_ATTEMPT = 'raw-attempt.name-7'  # never reaches an output


def cli(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


def event(sequence, event_type, data, attempt=RAW_ATTEMPT, rollout='ro-1'):
    return Event.parse({'schema': EVENT_SCHEMA, 'rolloutId': rollout, 'attemptId': attempt, 'sequence': sequence,
                        'eventType': event_type, 'timestamp': T0 + sequence, 'data': data})


def request(sequence, **kw):
    return event(sequence, 'model_request', {'requestSha256': DIGEST, 'responseSha256': DIGEST, 'latencyMs': 5,
                                             'status': 'ok', 'retryCount': 0, 'finishReason': None}, **kw)


def triplet(**overrides):
    value = {'schema': 'braid-lightning-triplet/v0.1', 'rolloutId': 'ro-1', 'attemptId': 'attempt-0123456789abcdef',
             'source': 'rollout', 'sourceSha256': DIGEST, 'prompt': {'text': 'p'},
             'response': {'text': 'r', 'toolCalls': []}, 'reward': None, 'rewardMatch': 'first-occurrence',
             'redaction': {'classes': {}, 'scanClean': True}, 'losses': [], 'createdAt': T0}
    value.update(overrides)
    return value


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def init(self, consent, sources='rollout'):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', consent]
        if consent == 'redacted':
            flags += ['--trace-sources', sources]
        _, out, _ = cli(*flags)
        code, _, err = cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
        self.assertEqual(code, 0, err)

    def store_run(self):
        """One rollout (task-a, group-g), three model calls: full content, prompt only, no content."""
        self.init('redacted')
        run = store.RunStore(self.home, 'run-1', content_consent='redacted')
        run.create(config_digest=DIGEST, now=T0)
        run.append('rollout', new_rollout('ro-1', 'task-a', 'group-g', DIGEST, DIGEST, 'claude-code', at=T0))
        for sequence in (1, 3, 4):
            run.append('event', request(sequence))
        run.append('trace', {'attemptId': RAW_ATTEMPT, 'sequence': 1, 'prompt': 'hello', 'response': 'world'},
                   now=T0 + 1)
        run.append('trace', {'attemptId': RAW_ATTEMPT, 'sequence': 3, 'prompt': 'only a prompt', 'response': None},
                   now=T0 + 3)
        return run


class StoreFilterTests(Base):
    def test_consented_redacted_records_are_kept_and_every_drop_is_counted(self):
        self.store_run()
        kept, exclusions = export.select(export.read_runs(self.home, ['run-1']))
        self.assertEqual(len(kept), 1)
        item = kept[0]
        self.assertEqual((item['runId'], item['taskId'], item['groupId'], item['rolloutId'], item['turnIndex']),
                         ('run-1', 'task-a', 'group-g', 'ro-1', 0))
        self.assertRegex(item['attemptId'], r'^attempt-[0-9a-f]{16}$')
        self.assertEqual(item['triplet']['prompt']['text'], 'hello')
        self.assertEqual(exclusions, {**export.empty_exclusions(), 'content-missing': 2})
        self.assertEqual(len(kept) + sum(exclusions.values()), 3)  # nothing is dropped silently

    def test_consent_none_yields_no_record_and_is_counted(self):
        self.store_run()
        self.init('none')
        kept, exclusions = export.select(export.read_runs(self.home, ['run-1']))
        self.assertEqual(kept, [])
        self.assertEqual(exclusions, {**export.empty_exclusions(), 'consent-none': 3})

    def test_unconsented_source_is_counted_as_no_consent(self):
        self.store_run()
        self.init('redacted', sources='loom')  # consent redacted, but rollout content is not a listed source
        kept, exclusions = export.select(export.read_runs(self.home, ['run-1']))
        self.assertEqual(kept, [])
        self.assertEqual(exclusions, {**export.empty_exclusions(), 'no-consent': 3})

    def test_no_raw_attempt_id_reaches_selected_records(self):
        self.store_run()
        items = export.read_runs(self.home, ['run-1'])
        self.assertNotIn(RAW_ATTEMPT, json.dumps(items))
        self.assertNotIn(RAW_ATTEMPT, json.dumps(export.select(items)))

    def test_turn_index_follows_the_model_calls_of_an_attempt(self):
        self.store_run()
        self.assertEqual([i['turnIndex'] for i in export.read_runs(self.home, ['run-1'])], [0, 1, 2])

    def test_refusals_are_fixed_codes_without_values_or_causes(self):
        self.init('redacted')
        with self.assertRaises(export.ExportError) as caught:
            export.read_runs(self.home, ['missing-run'])
        self.assertEqual(caught.exception.code, 'store-missing')
        self.assertNotIn('missing-run', str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        self.assertTrue(caught.exception.__suppress_context__)
        run = store.RunStore(self.home, 'run-2', content_consent='redacted')
        run.create(config_digest=DIGEST, now=T0)
        run.append('event', request(1, rollout='ro-orphan'))  # no rollout record names its task
        with self.assertRaises(export.ExportError) as caught:
            export.read_runs(self.home, ['run-2'])
        self.assertEqual(caught.exception.code, 'source-invalid')
        self.assertNotIn('ro-orphan', str(caught.exception))
        self.assertNotIn(RAW_ATTEMPT, str(caught.exception))


class ClassifyTests(unittest.TestCase):
    def test_reasons(self):
        cases = {
            None: triplet(),
            'consent-none': triplet(prompt=None, response=None, losses=['content-consent-required']),
            'no-consent': triplet(prompt=None, response=None, losses=['source-not-consented']),
            'unredacted': triplet(redaction={'classes': {}, 'scanClean': False}),
            'content-missing': triplet(prompt=None, losses=['content-missing']),
        }
        for reason, value in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual(export.exclusion_reason(value), reason)
        for broken in (triplet(redaction=None), triplet(redaction={'classes': {}}), triplet(schema='other/v0'),
                       triplet(redaction={'classes': {}, 'scanClean': 'yes'}), {}):
            with self.subTest(broken=broken):
                self.assertEqual(export.exclusion_reason(broken), 'unredacted')
        for missing in (triplet(prompt=None, losses=['prompt-missing']),
                        triplet(response=None, losses=['response-missing'])):
            self.assertEqual(export.exclusion_reason(missing), 'content-missing')

    def test_gate_refusal_names_the_reason(self):
        value = triplet(prompt=None, response=None, losses=['content-consent-required'])
        self.assertEqual(export.exclusion_reason(value, 'source-not-consented'), 'no-consent')
        self.assertEqual(export.exclusion_reason(value, 'content-consent-required'), 'consent-none')
        self.assertEqual(export.exclusion_reason(triplet(), 'source-not-consented'), 'no-consent')  # fail closed

    def test_consent_reasons_win_over_content_reasons(self):
        value = triplet(prompt=None, response=None, losses=['content-consent-required', 'content-missing'],
                        redaction={'classes': {}, 'scanClean': False})
        self.assertEqual(export.exclusion_reason(value), 'consent-none')

    def test_select_counts_every_reason_and_keeps_order(self):
        items = [{'triplet': triplet(prompt={'text': str(n)})} for n in range(3)]
        items.insert(1, {'triplet': triplet(prompt=None, response=None, losses=['content-consent-required'])})
        kept, exclusions = export.select(items)
        self.assertEqual([i['triplet']['prompt']['text'] for i in kept], ['0', '1', '2'])
        self.assertEqual(set(exclusions), set(export.EXCLUSION_REASONS))
        self.assertEqual(exclusions['consent-none'], 1)


if __name__ == '__main__':
    unittest.main()
