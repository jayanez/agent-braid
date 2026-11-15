# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T009 (REQ-009 / SC-009): `agent-braid lightning export` and its refusals.

Terms decision records here are SYNTHETIC, in temporary homes, and name a fictional provider (OD-1 is deferred).
"""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid.cli import main
from tests.spec075_fixtures import consent, new_run, rollout

SYNTHETIC = {'schema': 'braid-lightning-terms-decision/v0.1', 'provider': 'SYNTHETIC test provider (not real)',
             'host': 'claude-code', 'models': ['synthetic-model-1'], 'terms': {'version': 'synthetic-terms-0'},
             'reviewedOn': '2020-01-01', 'validUntil': '2999-12-31', 'outcome': 'permits-training'}
RAW = ('raw-a0', 'raw-a1', 'raw-h0', 'raw-h1', 'host yes', 'fixture ok')


def cli(*args):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        run = new_run(self.home)
        rollout(run, 'ro-a0', 'raw-a0', [('fixture ok', 'yes')], task='task-a', d4=True)
        rollout(run, 'ro-a1', 'raw-a1', [('fixture bad', 'no')], task='task-a', d4=False)

    def tearDown(self):
        self.tmp.cleanup()

    def enable(self, enabled=True):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', 'rollout', '--export' if enabled else '--no-export']
        _, out, _ = cli(*flags)
        code, _, err = cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])
        self.assertEqual(code, 0, err)

    def export(self, *extra, out='out', kind='rollout', level='trajectory', runs=('--run', 'run-1')):
        args = ['lightning', 'export', '--home', str(self.home), *runs, '--kind', kind, '--level', level,
                '--out', str(self.base / out), *extra]
        return cli(*args)

    def assert_refused(self, result, code, out='out'):
        status, stdout, stderr = result
        self.assertEqual((status, stdout), (2, ''))
        self.assertRegex(stderr, rf'^lightning refused \({code}\): [^\n]*\n$')
        for value in (str(self.base), *RAW, 'SYNTHETIC test provider', 'Traceback'):
            self.assertNotIn(value, stderr)
        self.assertFalse((self.base / out).exists() and any((self.base / out).iterdir()))


class DisabledTests(Base):
    def test_export_is_disabled_by_default(self):
        self.assert_refused(self.export(), 'export-disabled')  # consent given, export never enabled
        self.enable(False)
        self.assert_refused(self.export(), 'export-disabled')

    def test_no_or_invalid_profile_is_disabled(self):
        config.config_path(self.home).unlink()
        self.assert_refused(self.export(), 'export-disabled')
        config.config_path(self.home).write_text('{not json')
        config.config_path(self.home).chmod(0o600)
        self.assert_refused(self.export(), 'export-disabled')
        self.assertFalse((self.home / 'lightning' / 'terms').exists())


class ExportTests(Base):
    def setUp(self):
        super().setUp()
        self.enable()

    def test_exports_and_prints_only_counts_and_hashes(self):
        code, out, err = self.export()
        self.assertEqual((code, err), (0, ''))
        summary = json.loads(out)
        self.assertEqual((summary['status'], summary['records'], summary['balance'], summary['termsDecision'],
                          summary['files'], summary['executionAuthorization']),
                         ('exported', 2, 'equal', None, ['manifest.json', 'records.jsonl'], False))
        manifest = json.loads((self.base / 'out' / 'manifest.json').read_bytes())
        self.assertEqual((summary['digest'], summary['recordsSha256']), (manifest['digest'], manifest['recordsSha256']))
        for value in (str(self.base), *RAW, 'ro-a0', 'attempt-'):
            self.assertNotIn(value, out)
        self.assertEqual(set(summary), {'status', 'kind', 'level', 'balance', 'seed', 'records', 'exclusions',
                                        'balanceReport', 'termsDecision', 'redactionVersion', 'recordsSha256',
                                        'digest', 'files', 'executionAuthorization'})
        self.assertFalse((self.home / 'lightning' / 'terms').exists())  # never created

    def test_unexpected_errors_print_a_fixed_text(self):
        from agent_braid import lightning_export as export
        for error in (OSError(f'cannot open {self.base}/secret raw-a0'), ValueError('raw-a0 at /Users/someone'),
                      export.ExportError('x', 'Not A Code /tmp')):
            with self.subTest(error=type(error).__name__), patch.object(export, 'export_dataset', side_effect=error):
                status, stdout, stderr = self.export()
            self.assertEqual((status, stdout), (2, ''))
            self.assertNotIn('raw-a0', stderr)
            self.assertNotIn('/', stderr.split(':', 1)[1] if type(error) is not export.ExportError else '')
            self.assertIn('(other)', stderr)

    def test_all_and_options(self):
        code, out, _ = self.export('--outcome-field', kind='supervised', level='transition', runs=('--all',))
        self.assertEqual(code, 0)
        self.assertEqual((json.loads(out)['balance'], json.loads(out)['records']), ('none', 2))
        code, out, _ = self.export('--balance', 'none', '--seed', '3', out='o2')
        self.assertEqual((code, json.loads(out)['seed'], json.loads(out)['balance']), (0, 3, 'none'))

    def test_dry_run_writes_nothing_and_checks_the_output(self):
        code, out, _ = self.export('--dry-run')
        self.assertEqual((code, json.loads(out)['status'], json.loads(out)['files']), (0, 'planned', []))
        self.assertFalse((self.base / 'out').exists())
        (self.base / 'busy').mkdir()
        (self.base / 'busy' / 'x').write_text('x')
        self.assert_refused(self.export('--dry-run', out='busy'), 'output-not-empty', out='nothing')
        self.assertEqual([p.name for p in (self.base / 'busy').iterdir()], ['x'])
        _, real, _ = self.export(out='real')
        self.assertEqual(json.loads(out)['digest'], json.loads(real)['digest'])

    def test_output_path_refusals(self):
        (self.base / 'busy').mkdir()
        (self.base / 'busy' / 'x').write_text('x')
        self.assert_refused(self.export(out='busy'), 'output-not-empty', out='nothing')
        (self.base / 'file').write_text('x')
        self.assert_refused(self.export(out='file'), 'output-not-empty', out='nothing')
        target = self.base / 'target'
        target.mkdir()
        (self.base / 'link').symlink_to(target)
        (self.base / 'dirlink').symlink_to(self.base, target_is_directory=True)
        for out in ('link', 'dirlink/inner', 'missing/inner', '../escape', 'busy/../out2'):
            with self.subTest(out=out):
                self.assert_refused(self.export(out=out), 'path-refused', out='nothing')
        self.assertEqual(list(target.iterdir()), [])
        self.assertFalse((self.base / 'out2').exists())

    def test_invalid_arguments(self):
        cases = {
            'balanced supervised': ('--balance', 'equal'),
            'outcome on rollout': ('--outcome-field',),
            'negative seed': ('--seed', '-1'),
        }
        for name, extra in cases.items():
            kind = 'supervised' if name == 'balanced supervised' else 'rollout'
            with self.subTest(name=name):
                self.assert_refused(self.export(*extra, kind=kind), 'invalid-argument')
        self.assert_refused(self.export(runs=('--run', 'run-1', '--run', 'run-1')), 'invalid-argument')
        for argv in (['--kind', 'other'], ['--level', 'step'], ['--balance', 'ratio']):
            with self.subTest(argv=argv), patch('sys.stderr', StringIO()), self.assertRaises(SystemExit):
                main(['lightning', 'export', '--home', str(self.home), '--run', 'run-1', '--kind', 'rollout',
                      '--level', 'trajectory', '--out', str(self.base / 'o'), *argv])
        with patch('sys.stderr', StringIO()), self.assertRaises(SystemExit):  # neither --run nor --all
            main(['lightning', 'export', '--home', str(self.home), '--kind', 'rollout', '--level', 'trajectory',
                  '--out', str(self.base / 'o')])

    def test_store_refusals_name_no_value(self):
        self.assert_refused(self.export(runs=('--run', 'missing-run-name')), 'store-missing')
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'none',
                 '--export']
        _, preview, _ = cli(*flags)
        self.assertEqual(cli(*flags, '--apply', '--preview-digest', json.loads(preview)['previewDigest'])[0], 0)
        self.assertIs(config.load(self.home)['export']['enabled'], True)
        self.assert_refused(self.export(), 'no-records')  # export on, consent none: every call excluded

    def test_terms_gate_through_the_cli(self):
        host = new_run(self.home, 'run-host')
        rollout(host, 'ro-h0', 'raw-h0', [('host ok', 'host yes')], task='task-h', d4=True, label='host-run',
                model='synthetic-model-1')
        rollout(host, 'ro-h1', 'raw-h1', [('host bad', 'host no')], task='task-h', d4=False, label='host-run',
                model='synthetic-model-1')
        self.assert_refused(self.export(runs=('--all',)), 'terms-gate-missing')
        self.assertFalse((self.home / 'lightning' / 'terms').exists())
        self.assert_refused(self.export('--terms-decision', 'terms/synthetic.json', runs=('--all',)),
                            'terms-gate-missing')
        self.assertFalse((self.home / 'lightning' / 'terms').exists())  # the CLI never creates it
        terms = self.home / 'lightning' / 'terms'
        terms.mkdir(mode=0o700)
        record = terms / 'synthetic.json'
        record.write_text(json.dumps(SYNTHETIC))
        record.chmod(0o600)
        before = (record.read_bytes(), record.stat().st_mtime_ns, sorted(p.name for p in terms.iterdir()))
        code, out, err = self.export('--terms-decision', 'terms/synthetic.json', runs=('--all',))
        self.assertEqual((code, err), (0, ''))
        self.assertEqual(json.loads(out)['termsDecision']['path'], 'terms/synthetic.json')
        for value in ('SYNTHETIC test provider', 'synthetic-terms-0', 'synthetic-model-1', 'permits-training'):
            self.assertNotIn(value, out)  # the record's contents are never printed
        self.assertEqual((record.read_bytes(), record.stat().st_mtime_ns, sorted(p.name for p in terms.iterdir())),
                         before)


class BoundaryTests(Base):
    def test_export_runs_offline_and_launches_nothing(self):
        self.enable()

        def refuse(*args, **kwargs):
            raise AssertionError('network or process use')

        import socket
        import subprocess
        with patch.object(socket, 'socket', refuse), patch.object(socket, 'create_connection', refuse), \
                patch.object(subprocess, 'Popen', refuse), patch.object(os, 'system', refuse):
            code, out, err = self.export()
        self.assertEqual((code, err), (0, ''))


if __name__ == '__main__':
    unittest.main()
