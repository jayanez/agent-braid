# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-001 / SC-001 (T002): the trace consent record in the Braid Lightning profile."""
from contextlib import redirect_stdout
import copy
from datetime import date
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_config as c
from agent_braid import lightning_store as store
from agent_braid.cli import main
from agent_braid.plugin_registry import apply as apply_setup, plan_setup

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas/0.3.0-experimental/lightning-config.schema.json'
DIGEST = 'a' * 64


def traces(**fields):
    doc = c.defaults()
    doc['traces'].update(fields)
    return doc


VALID = [
    c.defaults(),
    traces(contentConsent='redacted', consentedAt='2026-11-13', consentPreviewDigest=DIGEST),
    traces(contentConsent='redacted', sources=['rollout', 'host-transcript'], consentedAt='2026-11-13',
           consentPreviewDigest=DIGEST),
]
INVALID = [
    (traces(consentedAt='2026-11-13'), 'config-consent'),
    (traces(consentPreviewDigest=DIGEST), 'config-consent'),
    (traces(contentConsent='redacted'), 'config-consent'),
    (traces(contentConsent='redacted', consentedAt='2026-11-13'), 'config-consent'),
    (traces(contentConsent='redacted', consentPreviewDigest=DIGEST), 'config-consent'),
    (traces(contentConsent='raw'), 'config-enum'),
    (traces(contentConsent='redacted', consentedAt='13/11/2026', consentPreviewDigest=DIGEST), 'config-type'),
    (traces(contentConsent='redacted', consentedAt='2026-11-13', consentPreviewDigest='ABC'), 'config-type'),
    (traces(sources=['rollout', 'email']), 'config-enum'),
]


def run(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class ConsentRecordTests(unittest.TestCase):
    def test_default_is_none_without_a_record(self):
        value = c.validate(c.defaults())
        self.assertEqual(value['traces'], {'sources': ['rollout'], 'contentConsent': 'none', 'retentionDays': 30,
                                           'consentedAt': None, 'consentPreviewDigest': None})

    def test_a_bl0_profile_without_the_record_still_reads_as_none(self):
        legacy = c.defaults()
        for key in c.CONSENT_RECORD:
            del legacy['traces'][key]
        self.assertEqual(c.parse(c.to_bytes(legacy)), c.validate(c.defaults()))
        legacy['traces']['contentConsent'] = 'redacted'
        with self.assertRaises(c.ConfigError) as caught:
            c.validate(legacy)
        self.assertEqual(caught.exception.code, 'config-consent')

    def test_invalid_records_are_refused_with_codes(self):
        for doc in VALID:
            c.validate(doc)
        for doc, code in INVALID:
            with self.subTest(code=code, traces=doc['traces']), self.assertRaises(c.ConfigError) as caught:
                c.validate(doc)
            self.assertEqual(caught.exception.code, code)
        with self.assertRaises(c.ConfigError):
            c.validate(traces(contentConsent='redacted', consentedAt='2026-02-30', consentPreviewDigest=DIGEST))

    def test_the_record_cannot_be_answered(self):
        for key in c.CONSENT_RECORD:
            with self.subTest(key=key), self.assertRaises(c.ConfigError) as caught:
                c.build({'traces': {'contentConsent': 'redacted', key: DIGEST}})
            self.assertEqual(caught.exception.code, 'config-consent')

    def test_published_schema_agrees_with_the_validator(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is a development dependency')
        validator = jsonschema.Draft202012Validator(json.loads(SCHEMA_PATH.read_text()))
        for doc in VALID:
            self.assertEqual(list(validator.iter_errors(doc)), [])
        for doc, code in INVALID:
            with self.subTest(code=code, traces=doc['traces']):
                self.assertTrue(list(validator.iter_errors(doc)))
        legacy = c.defaults()
        for key in c.CONSENT_RECORD:
            del legacy['traces'][key]
        self.assertEqual(list(validator.iter_errors(legacy)), [])


class InitPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def init(self, *flags):
        code, out, err = run('lightning', 'init', '--home', str(self.home), '--non-interactive', *flags)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def apply(self, *flags):
        preview = self.init(*flags)
        applied = self.init(*flags, '--apply', '--preview-digest', preview['previewDigest'])
        return preview, applied

    def test_preview_shows_level_date_sources_and_effects(self):
        preview = c.plan_init(self.home, {'traces': {'contentConsent': 'redacted',
                                                     'sources': ['host-transcript', 'rollout']}},
                              today=date(2026, 11, 13))
        self.assertEqual(preview['consent'], {'contentConsent': 'redacted', 'consentedAt': '2026-11-13',
                                              'sources': ['rollout', 'host-transcript'], 'retentionDays': 30,
                                              'expires': None})
        self.assertIsNone(preview['config']['traces']['consentPreviewDigest'])
        text = '\n'.join(preview['effects'])
        for needle in ('since 2026-11-13', 'does not expire', 'rollout, host-transcript', 'never modified',
                       'email (per-run salted hash)', 'Residual risk', 'never uploaded', 'still refuses'):
            self.assertIn(needle, text)
        self.assertFalse(preview['executionAuthorization'])

    def test_host_transcripts_are_read_only_when_listed(self):
        preview = self.init('--trace-consent', 'redacted')
        self.assertEqual(preview['consent']['sources'], ['rollout'])
        self.assertNotIn('host-transcript', '\n'.join(preview['effects']))

    def test_apply_records_the_date_and_the_applied_preview_digest(self):
        preview, applied = self.apply('--trace-consent', 'redacted', '--trace-sources', 'rollout,host-transcript')
        stored = c.load(self.home)['traces']
        self.assertEqual(stored['consentedAt'], date.today().isoformat())
        self.assertEqual(stored['consentPreviewDigest'], preview['previewDigest'])
        self.assertEqual(applied['consent']['consentedAt'], stored['consentedAt'])
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['traceConsent'], {
            'contentConsent': 'redacted', 'consentedAt': stored['consentedAt'],
            'sources': ['rollout', 'host-transcript'], 'retentionDays': 30, 'expires': None})

    def test_unrelated_changes_keep_the_consent_and_new_sources_renew_it(self):
        first, _ = self.apply('--trace-consent', 'redacted')
        self.apply('--trace-consent', 'redacted', '--repetitions', '2')
        self.assertEqual(c.load(self.home)['traces']['consentPreviewDigest'], first['previewDigest'])
        second, _ = self.apply('--trace-consent', 'redacted', '--trace-sources', 'rollout,loom')
        self.assertEqual(c.load(self.home)['traces']['consentPreviewDigest'], second['previewDigest'])

    def test_lowering_to_none_clears_the_record(self):
        self.apply('--trace-consent', 'redacted')
        preview, _ = self.apply('--trace-consent', 'none')
        self.assertIn('purge', '\n'.join(preview['effects']))
        stored = c.load(self.home)['traces']
        self.assertEqual((stored['contentConsent'], stored['consentedAt'], stored['consentPreviewDigest']),
                         ('none', None, None))

    def test_a_stale_or_forged_digest_writes_nothing(self):
        preview = self.init('--trace-consent', 'redacted')
        code, _, err = run('lightning', 'init', '--home', str(self.home), '--non-interactive',
                           '--trace-consent', 'redacted', '--trace-sources', 'rollout,loom',
                           '--apply', '--preview-digest', preview['previewDigest'])
        self.assertEqual(code, 2)
        self.assertIn('config-digest', err)
        self.assertIsNone(c.load(self.home))

    def test_plugin_setup_never_changes_the_consent(self):
        self.apply('--trace-consent', 'redacted')
        before = c.config_path(self.home).read_bytes()
        for level in ('lab', 'off'):
            preview = plan_setup(self.home, [], lightning=level)
            self.assertNotIn('contentConsent', json.dumps(preview))
            apply_setup(self.home, preview, preview['previewDigest'])
            self.assertEqual(c.config_path(self.home).read_bytes(), before)

    def test_status_without_a_profile_reports_none(self):
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['traceConsent']['contentConsent'], 'none')

    def test_content_stays_refused_by_the_store_until_t003(self):
        self.apply('--trace-consent', 'redacted')
        run_store = store.RunStore(self.home, 'r1', content_consent='redacted')
        run_store.create(config_digest=DIGEST)
        with self.assertRaises(store.StoreError) as caught:
            run_store.append('trace', {'text': 'x'})
        self.assertEqual(caught.exception.code, 'store-consent')


if __name__ == '__main__':
    unittest.main()
