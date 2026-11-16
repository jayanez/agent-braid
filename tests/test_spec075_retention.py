# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T013 (REQ-013 / SC-013): source retention in the manifest, retention-expired, and purge listing the
datasets that cite a purged run. Every patch and environment change is undone with addCleanup."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid import lightning_export as export
from agent_braid.cli import main
from tests.spec075_fixtures import T0, consent, new_run, rollout

DAY = 86400
EXPIRY = T0 + 30 * DAY  # run-1 is created at T0 (2027-01-15T08:00Z) with the default 30-day retention


def cli(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        fresh = new_run(self.home, 'run-1')
        rollout(fresh, 'ro-1', 'raw-1', [('fresh', 'ok')], task='task-a', d4=True)
        old = new_run(self.home, 'run-old', created=T0 - 40 * DAY)
        rollout(old, 'ro-o', 'raw-o', [('old', 'ok')], task='task-b', d4=True, created=T0 - 40 * DAY)

    def export(self, runs=('run-1',), name='out', now=T0 + 60, **kwargs):
        options = {'kind': 'rollout', 'level': 'trajectory', 'balance': 'none', **kwargs}
        return export.export_dataset(self.home, list(runs), out=self.base / name, now=now, **options)

    def refused(self, code, **kwargs):
        before = self.index()
        with self.assertRaises(export.ExportError) as caught:
            self.export(**kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertIsNone(caught.exception.__cause__)
        self.assertFalse((self.base / kwargs.get('name', 'out')).exists())
        self.assertEqual(self.index(), before)  # no index entry for a refused export
        return caught.exception

    def index(self):
        directory = self.home / 'lightning' / 'exports'
        return sorted(p.name for p in directory.iterdir()) if directory.exists() else []


class RetentionTests(Base):
    def test_manifest_records_retention_per_cited_run(self):
        manifest = self.export()
        self.assertEqual(manifest['retention'], {'run-1': {'retentionDays': 30, 'expiresAt': '2027-02-14'}})
        self.assertEqual(manifest['exclusions']['retention-expired'], 0)

    def test_a_record_past_retention_is_refused_and_counted(self):  # SC-013
        manifest = self.export(runs=('run-1', 'run-old'))
        self.assertEqual(manifest['exclusions']['retention-expired'], 1)
        self.assertEqual(sorted(manifest['retention']), ['run-1'])
        self.assertEqual([e['runId'] for e in manifest['records']], ['run-1'])
        self.assertNotIn(b'old', (self.base / 'out' / 'records.jsonl').read_bytes())

    def test_only_expired_records_refuse_the_export(self):
        self.refused('retention-expired', runs=('run-old',))

    def test_the_expiry_boundary(self):
        # Stricter than the SPEC-074 sweep, which keeps the run at the exact instant and removes it one later.
        cases = {'tomorrow': (EXPIRY - DAY, True), 'today, before the instant': (EXPIRY - 1, True),
                 'today, at the instant (the sweep still keeps it)': (EXPIRY, False),
                 'one second after': (EXPIRY + 1, False), 'yesterday': (EXPIRY + DAY, False)}
        for name, (now, kept) in cases.items():
            with self.subTest(name=name):
                if kept:
                    manifest = self.export(name=name.replace(' ', '-').replace(',', ''), now=now)
                    self.assertEqual(manifest['retention']['run-1']['expiresAt'], '2027-02-14')
                else:
                    self.refused('retention-expired', now=now)

    def test_creation_near_utc_midnight(self):
        # 2027-01-15T23:59:59Z and 2027-01-16T00:00:00Z with a 1-day bound: the date shown is the UTC day of the
        # instant, and the refusal follows the instant, not the date.
        self.reprofile(retention_days=1)
        late, early = 1800057599.0, 1800057600.0
        for run_id, created, expires in (('run-late', late, '2027-01-16'), ('run-early', early, '2027-01-17')):
            with self.subTest(run=run_id):
                run = new_run(self.home, run_id, created=created)
                rollout(run, f'ro-{run_id}', f'raw-{run_id}', [('near midnight', 'ok')], task='task-m', d4=True,
                        created=created)
                manifest = self.export(runs=(run_id,), name=f'{run_id}-before', now=created + DAY - 1)
                self.assertEqual(manifest['retention'][run_id]['expiresAt'], expires)
                self.refused('retention-expired', runs=(run_id,), name=f'{run_id}-at', now=created + DAY)

    def test_the_retention_bound_comes_from_the_profile(self):
        self.reprofile(retention_days=1)
        self.refused('retention-expired', now=T0 + DAY)
        self.export(now=T0 + DAY - 1)

    def test_no_retention_bound_refuses(self):
        path = config.config_path(self.home)
        value = json.loads(path.read_bytes())
        value['traces']['retentionDays'] = 0  # outside 1-90: the profile no longer validates
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        self.refused('retention-expired')
        with patch.object(export.config, 'load', return_value=None):
            self.refused('retention-expired')

    def test_the_host_time_zone_does_not_matter(self):
        previous = os.environ.get('TZ')

        def restore():
            if previous is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = previous
            time.tzset()
        self.addCleanup(restore)
        results = []
        for zone in ('UTC', 'Pacific/Kiritimati', 'Pacific/Pago_Pago', 'Asia/Kolkata'):
            os.environ['TZ'] = zone
            time.tzset()
            out = []
            for n, now in enumerate((EXPIRY - 1, EXPIRY)):
                try:
                    out.append(self.export(name=f'{zone.replace("/", "-")}-{n}', now=now)['retention'])
                except export.ExportError as exc:
                    out.append(exc.code)
            results.append(out)
        self.assertEqual(results, [[{'run-1': {'retentionDays': 30, 'expiresAt': '2027-02-14'}},
                                    'retention-expired']] * 4)

    def reprofile(self, *, retention_days):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', 'rollout', '--retention-days', str(retention_days)]
        _, out, _ = cli(*flags)
        self.assertEqual(cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])[0], 0)


class PurgeListingTests(Base):
    def enable(self):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', 'rollout', '--export']
        _, out, _ = cli(*flags)
        self.assertEqual(cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])[0], 0)

    def purge(self, *target):
        code, out, err = cli('lightning', 'purge', '--home', str(self.home), *target)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_purge_lists_the_datasets_that_cite_the_run(self):
        manifest = self.export()
        preview = self.purge('--run-id', 'run-1')
        self.assertEqual(preview['citingDatasets'], [{'manifest': str(self.base / 'out' / 'manifest.json'),
                                                      'digest': manifest['digest'], 'citesRuns': ['run-1']}])
        self.assertIn('not deleted by purge', preview['datasetsNote'])
        self.assertEqual(self.purge('--run-id', 'run-old')['citingDatasets'], [])
        self.assertEqual(len(self.purge('--all')['citingDatasets']), 1)
        applied = self.purge(*preview['applyWith'])
        self.assertEqual((applied['removed'], len(applied['citingDatasets'])), (['run-1'], 1))
        self.assertTrue((self.base / 'out' / 'records.jsonl').exists())  # datasets are outside purge

    def test_an_export_between_preview_and_apply_does_not_stale_the_preview(self):
        preview = self.purge('--run-id', 'run-1')
        self.assertEqual(preview['citingDatasets'], [])
        self.export()
        applied = self.purge(*preview['applyWith'])
        self.assertEqual(len(applied['citingDatasets']), 1)

    def test_deleted_moved_or_changed_datasets_are_not_listed(self):
        self.export(name='a')
        self.export(name='b')
        self.export(name='c')
        shutil.rmtree(self.base / 'a')
        manifest = self.base / 'b' / 'manifest.json'
        value = json.loads(manifest.read_bytes())
        value['seed'] = 9
        manifest.write_text(json.dumps(value))
        self.assertEqual([d['manifest'] for d in self.purge('--run-id', 'run-1')['citingDatasets']],
                         [str(self.base / 'c' / 'manifest.json')])

    def test_the_index_is_private_and_written_only_for_real_exports(self):
        self.export(name='dry', dry_run=True)
        self.assertEqual(self.index(), [])
        self.export()
        directory = self.home / 'lightning' / 'exports'
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
        (entry,) = directory.iterdir()
        self.assertEqual(entry.stat().st_mode & 0o777, 0o600)
        value = json.loads(entry.read_bytes())
        self.assertEqual(set(value), {'schema', 'out', 'digest', 'runIds'})
        self.assertNotIn('fresh', entry.read_text())

    def snapshot(self, root):
        return {str(p.relative_to(root)): (p.read_bytes() if p.is_file() else None) for p in sorted(root.rglob('*'))}

    def test_purge_never_writes_into_a_dataset(self):
        self.export()
        before = self.snapshot(self.base / 'out')
        preview = self.purge('--run-id', 'run-1')
        self.purge(*preview['applyWith'])
        self.assertEqual(self.snapshot(self.base / 'out'), before)

    def test_apply_prunes_entries_of_gone_or_changed_datasets_only(self):
        self.export(name='keep')
        self.export(name='gone')
        self.export(name='changed')
        shutil.rmtree(self.base / 'gone')
        manifest = self.base / 'changed' / 'manifest.json'
        value = json.loads(manifest.read_bytes())
        value['seed'] = 9
        manifest.write_text(json.dumps(value))
        self.assertEqual(len(self.index()), 3)
        preview = self.purge('--run-id', 'run-old')
        self.assertEqual(len(self.index()), 3)  # a preview deletes nothing, index entries included
        self.purge(*preview['applyWith'])
        self.assertEqual(len(self.index()), 1)
        self.assertTrue(manifest.exists())  # the changed dataset's files stay: only its index entry went
        self.assertEqual([d['manifest'] for d in self.purge('--all')['citingDatasets']],
                         [str(self.base / 'keep' / 'manifest.json')])

    def test_forged_or_relative_entries_are_ignored(self):
        self.export()
        directory = self.home / 'lightning' / 'exports'
        (entry,) = directory.iterdir()
        value = json.loads(entry.read_bytes())
        link = self.base / 'link'
        link.symlink_to(self.base / 'out', target_is_directory=True)
        for n, out in enumerate(('out', str(link), str(self.base / 'x' / '..' / 'out'), str(self.base / 'out') + '/',
                                 str(self.base), 7)):
            forged = directory / f'forged-{n}.json'
            forged.write_text(json.dumps({**value, 'out': out}))
            forged.chmod(0o600)
        self.assertEqual([d['manifest'] for d in self.purge('--run-id', 'run-1')['citingDatasets']],
                         [str(self.base / 'out' / 'manifest.json')])

    def test_an_interrupted_index_write_leaves_no_entry(self):
        real = export.os.replace

        def crash(source, target):
            if str(target).endswith('.json') and 'exports' in str(target):
                raise KeyboardInterrupt
            return real(source, target)

        patcher = patch.object(export.os, 'replace', crash)
        patcher.start()
        self.addCleanup(patcher.stop)
        with self.assertRaises(KeyboardInterrupt):
            self.export()
        patcher.stop()
        self.assertEqual(self.index(), [])  # neither the entry nor its temporary file
        self.assertFalse((self.base / 'out').exists())

    def test_a_leftover_temporary_entry_is_not_listed(self):
        self.export()
        directory = self.home / 'lightning' / 'exports'
        (entry,) = directory.iterdir()
        leftover = directory / '.entry-crash.tmp'
        leftover.write_bytes(entry.read_bytes()[:20])
        self.assertEqual(len(self.purge('--run-id', 'run-1')['citingDatasets']), 1)

    def test_a_failed_write_leaves_no_index_entry(self):
        with patch.object(export, 'write_export', side_effect=export.ExportError('x', 'path-refused')):
            self.refused('path-refused')

    def test_the_cli_help_says_datasets_are_outside_purge(self):
        code, out, _ = cli('lightning', 'export', '--home', str(self.home), '--help')
        text = ' '.join(out.split())
        self.assertEqual(code, 0)
        for phrase in ('outside lightning purge', 'delete them yourself', 'retention-expired'):
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
