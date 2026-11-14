# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-005 / SC-005 (T006): content retention with an injected clock, sweep, and purge with a preview."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_store as store
from agent_braid.cli import main

DIGEST = 'c' * 64
DAY = 86400.0
T0 = 1_800_000_000.0


def run(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class RetentionPurgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted']
        _, out, _ = run(*flags)
        code, _, err = run(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
        self.assertEqual(code, 0, err)

    def tearDown(self):
        self.tmp.cleanup()

    def content_run(self, run_id, created):
        run_store = store.RunStore(self.home, run_id)
        run_store.create(config_digest=DIGEST, now=created)
        run_store.append('trace', {'text': 'contact owner@example.org'}, now=created)
        return run_store

    def all_bytes(self) -> bytes:
        root = store.runs_root(self.home)
        return b''.join(p.read_bytes() for p in root.rglob('*') if p.is_file()) if root.exists() else b''

    def test_content_records_carry_a_creation_date_and_a_per_run_salt(self):
        run_store = self.content_run('r1', T0)
        [line] = run_store.read_content()
        self.assertEqual(line['createdAt'], T0)
        self.assertNotIn(b'owner@example.org', self.all_bytes())
        salt = run_store.root / store.SALT_FILE
        self.assertEqual((len(salt.read_bytes()), salt.stat().st_mode & 0o777), (16, 0o600))

    def test_sweep_removes_expired_content_and_expired_runs(self):
        kept = store.RunStore(self.home, 'r-new')
        kept.create(config_digest=DIGEST, now=T0 + 42 * DAY)
        kept.append('trace', {'text': 'stale'}, now=T0 + 20 * DAY)  # injected clock: older than the cutoff
        kept.append('trace', {'text': 'fresh'}, now=T0 + 44 * DAY)
        self.content_run('r-old', T0)
        result = store.sweep(self.home, 30, now=T0 + 71 * DAY)  # cutoff T0 + 41 days
        self.assertEqual((result['removed'], result['contentRecordsRemoved']), (['r-old'], 1))
        self.assertEqual([r['record']['text'] for r in kept.read_content()], ['fresh'])
        self.assertEqual([r['runId'] for r in store.list_runs(self.home)], ['r-new'])

    def test_appending_content_sweeps_its_own_run(self):
        run_store = self.content_run('r1', T0)
        run_store.append('trace', {'text': 'later'}, now=T0 + 31 * DAY)
        self.assertEqual([r['createdAt'] for r in run_store.read_content()], [T0 + 31 * DAY])

    def test_retention_outside_1_90_is_refused(self):
        for days in (0, 91, '30'):
            with self.subTest(days=days), self.assertRaises(store.StoreError) as caught:
                store.sweep(self.home, days)
            self.assertEqual(caught.exception.code, 'retention-out-of-range')

    def test_skipping_the_sweep_leaves_expired_content(self):
        """Negative control: with the content sweep disabled the expired record survives, so these tests fail."""
        run_store = store.RunStore(self.home, 'r1')
        run_store.create(config_digest=DIGEST, now=T0 + 50 * DAY)
        with patch.object(store.RunStore, '_sweep_content', lambda self, cutoff: 0):
            run_store.append('trace', {'text': 'old'}, now=T0 + 10 * DAY)
            run_store.append('trace', {'text': 'new'}, now=T0 + 50 * DAY)
            store.sweep(self.home, 30, now=T0 + 60 * DAY)
            self.assertEqual(len(run_store.read_content()), 2)
        store.sweep(self.home, 30, now=T0 + 60 * DAY)
        self.assertEqual([r['record']['text'] for r in run_store.read_content()], ['new'])

    def test_purge_previews_then_needs_the_matching_digest(self):
        self.content_run('r1', T0)
        self.content_run('r2', T0)
        code, out, _ = run('lightning', 'purge', '--home', str(self.home), '--all')
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertEqual([r['runId'] for r in preview['runs']], ['r1', 'r2'])
        self.assertTrue(all(r['contentBytes'] > 0 for r in preview['runs']))
        self.assertTrue(store.list_runs(self.home))  # the preview deletes nothing
        code, _, err = run('lightning', 'purge', '--home', str(self.home), '--all', '--apply', '--preview-digest', 'f' * 64)
        self.assertEqual(code, 2)
        self.assertIn('preview-stale', err)
        self.content_run('r3', T0)  # the store changed since the preview
        code, _, err = run('lightning', 'purge', '--home', str(self.home), *preview['applyWith'])
        self.assertIn('preview-stale', err)
        _, out, _ = run('lightning', 'purge', '--home', str(self.home), '--all')
        code, out, _ = run('lightning', 'purge', '--home', str(self.home), *json.loads(out)['applyWith'])
        self.assertEqual((code, json.loads(out)['removed']), (0, ['r1', 'r2', 'r3']))
        self.assertEqual(self.all_bytes(), b'')
        self.assertEqual(list(store.runs_root(self.home).iterdir()), [])

    def test_purge_one_run_removes_its_content_and_salt_only(self):
        self.content_run('r1', T0)
        other = self.content_run('r2', T0)
        _, out, _ = run('lightning', 'purge', '--home', str(self.home), '--run-id', 'r1')
        code, _, err = run('lightning', 'purge', '--home', str(self.home), *json.loads(out)['applyWith'])
        self.assertEqual(code, 0, err)
        self.assertFalse((store.runs_root(self.home) / 'r1').exists())
        self.assertTrue((other.root / store.SALT_FILE).exists())

    def test_lightning_sweep_uses_the_profile_retention(self):
        self.content_run('r1', 1000.0)
        code, out, err = run('lightning', 'sweep', '--home', str(self.home))
        self.assertEqual(code, 0, err)
        self.assertEqual((json.loads(out)['removed'], json.loads(out)['retentionDays']), (['r1'], 30))

    def test_purge_never_touches_files_outside_the_run_store(self):
        outside = self.home / 'lightning' / 'keep.txt'
        outside.write_text('host transcript stand-in')
        self.content_run('r1', T0)
        _, out, _ = run('lightning', 'purge', '--home', str(self.home), '--all')
        run('lightning', 'purge', '--home', str(self.home), *json.loads(out)['applyWith'])
        self.assertEqual(outside.read_text(), 'host transcript stand-in')


if __name__ == '__main__':
    unittest.main()
