# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-002 / SC-002 (T003): content is refused without consent, and invalid configuration fails closed."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_adapter as adapter
from agent_braid import lightning_config as c
from agent_braid import lightning_store as store
from agent_braid.cli import main

DIGEST = 'b' * 64


def run(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def consent(self, level, sources='rollout'):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive',
                 '--trace-consent', level, '--trace-sources', sources]
        code, out, err = run(*flags)
        self.assertEqual(code, 0, err)
        code, _, err = run(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
        self.assertEqual(code, 0, err)

    def corrupt(self, raw: bytes):
        path = c.config_path(self.home)
        path.chmod(0o600)
        path.write_bytes(raw)

    def store_refusal(self, run_id='r1', **kwargs):
        run_store = store.RunStore(self.home, run_id, **kwargs)
        run_store.create(config_digest=DIGEST)
        with self.assertRaises(store.StoreError) as caught:
            run_store.append('trace', {'text': 'secret prompt'})
        self.assertFalse((run_store.root / 'trace.jsonl').exists())
        self.assertNotIn(b'secret prompt', b''.join(p.read_bytes() for p in run_store.root.iterdir() if p.is_file()))
        return caught.exception.code

    def test_without_a_profile_the_store_and_adapter_refuse(self):
        self.assertEqual(store.content_consent(self.home), 'none')
        self.assertEqual(self.store_refusal(), 'store-consent')
        self.assertEqual(adapter.gate(self.home, 'rollout'),
                         {'contentConsent': 'none', 'source': 'rollout', 'content': False,
                          'refusal': 'content-consent-required'})
        with self.assertRaises(adapter.AdapterError) as caught:
            adapter.require_content(self.home, 'rollout')
        self.assertEqual(caught.exception.code, 'content-consent-required')

    def test_consent_none_refuses(self):
        self.consent('none')
        self.assertEqual(self.store_refusal(), 'store-consent')
        self.assertEqual(adapter.gate(self.home)['refusal'], 'content-consent-required')

    def test_invalid_configuration_fails_closed(self):
        self.consent('redacted')
        valid = c.config_path(self.home).read_bytes()
        broken = json.loads(valid)
        broken['traces']['consentPreviewDigest'] = None  # redacted without its record: config-consent
        for raw in (b'{not json', json.dumps(broken).encode(), valid.replace(b'"redacted"', b'"raw"')):
            with self.subTest(raw=raw[:40]):
                self.corrupt(raw)
                self.assertEqual(store.content_consent(self.home), 'none')
                self.assertEqual(self.store_refusal(run_id=f'r{len(raw)}'), 'store-consent')
                self.assertEqual(adapter.gate(self.home, 'rollout')['refusal'], 'content-consent-required')
                code, _, err = run('lightning', 'status', '--home', str(self.home))
                self.assertEqual(code, 2)
                self.assertIn('lightning refused (config-', err)

    def test_an_explicit_none_overrides_a_redacted_profile(self):
        self.consent('redacted')
        self.assertEqual(self.store_refusal(content_consent='none'), 'store-consent')
        with self.assertRaises(store.StoreError) as caught:
            store.RunStore(self.home, 'r2', content_consent='raw')
        self.assertEqual(caught.exception.code, 'store-consent')

    def test_with_consent_a_record_that_stays_unclean_is_refused(self):
        self.consent('redacted', 'rollout,loom')
        run_store = store.RunStore(self.home, 'r1')
        run_store.create(config_digest=DIGEST)
        with self.assertRaises(store.StoreError) as caught:
            run_store.append('trace', {'a': 'sk-ant-api0', 'b': '3' + 'Q' * 20})  # hidden split
        self.assertEqual(caught.exception.code, 'redaction-incomplete')
        self.assertEqual([set(r) for r in run_store.read_content()], [{'createdAt', 'refused'}])
        self.assertEqual(adapter.gate(self.home, 'loom')['content'], True)
        adapter.require_content(self.home, 'rollout')

    def test_unlisted_sources_are_refused(self):
        self.consent('redacted')
        for source in ('host-transcript', 'system-one', 'loom'):
            with self.subTest(source=source), self.assertRaises(adapter.AdapterError) as caught:
                adapter.require_content(self.home, source)
            self.assertEqual(caught.exception.code, 'source-not-consented')

    def test_status_reports_the_gate(self):
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['traceContent']['refusal'], 'content-consent-required')
        self.consent('redacted')
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(json.loads(out)['traceContent'],
                         {'contentConsent': 'redacted', 'source': None, 'content': True, 'refusal': None})

    def test_content_free_records_are_unaffected(self):
        run_store = store.RunStore(self.home, 'r1')
        run_store.create(config_digest=DIGEST)
        with self.assertRaises(store.StoreError) as caught:
            run_store.append('nonsense', {})
        self.assertEqual(caught.exception.code, 'store-kind')


if __name__ == '__main__':
    unittest.main()
