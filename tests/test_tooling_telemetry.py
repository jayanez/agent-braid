# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-047 synthetic privacy, storage and incremental exchange controls."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import timedelta
import io
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import tooling_telemetry as telemetry


class TelemetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / 'metrics'
        self.store = telemetry.Store(self.directory)

    def record(self, **kwargs):
        self.store.record('cli', 'analyze', 'ok', 12, {'ordered': 2}, **kwargs)

    def test_disabled_has_no_files_and_accepts_no_payload(self):
        with telemetry.observe('off', 'cli', 'analyze', directory=self.directory):
            pass
        self.assertFalse(self.directory.exists())
        self.assertEqual(self.store.report()['rows'], [])
        self.assertFalse(self.directory.exists())
        with self.assertRaises(ValueError):
            self.store.record('cli', 'repo-secret', 'ok', 1)
        self.assertFalse(self.directory.exists())

    def test_fixed_aggregation_and_private_permissions(self):
        self.record()
        self.record()
        rows = self.store.report()['rows']
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'calls'), 2)
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'classification'), 4)
        self.assertEqual([r['bucket'] for r in rows if r['metric'] == 'duration'], ['le-100ms'])
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)
        self.assertEqual((self.directory / 'metrics.sqlite3').stat().st_mode & 0o777, 0o600)
        self.assertLessEqual(sum(p.stat().st_size for p in self.directory.iterdir()), telemetry.MAX_BYTES)

    def test_privacy_rejects_free_fields_and_nonfinite_numbers(self):
        for payload in ({'repo-secret': 1}, {'ordered': True}, {'ordered': -1}, {'ordered': 'secret'}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.store.record('cli', 'analyze', 'ok', 1, payload)
        for duration in (float('nan'), float('inf'), -1, True):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                self.store.record('cli', 'analyze', 'ok', duration)
        self.assertFalse(self.directory.exists())
        with telemetry.observe('local', 'cli', 'analyze', directory=self.directory) as observation:
            observation.summary({'summary': {'classifications': {'ordered': 2, 'independent-candidate': 0, 'conflicting': 0, 'unknown': 0, 'repo-secret': 'credential'}}, 'path': 'SECRET'})
            observation.outcome = 'ok'
        raw = b''.join(p.read_bytes() for p in self.directory.iterdir())
        self.assertNotIn(b'SECRET', raw)
        self.assertNotIn(b'credential', raw)
        self.assertNotIn(b'repo-secret', raw)

    def test_retention_and_secure_purge(self):
        old = telemetry.today() - timedelta(days=30)
        with patch.object(telemetry, 'today', return_value=old):
            self.record()
        self.assertEqual(self.store.report()['rows'], [])
        self.record()
        self.store.purge()
        self.assertEqual(self.store.report()['rows'], [])
        connection = sqlite3.connect(self.directory / 'metrics.sqlite3')
        try:
            self.assertEqual(connection.execute('select count(*) from batches').fetchone()[0], 0)
        finally:
            connection.close()

    def test_concurrent_writes_are_transactional(self):
        # Correctness of concurrent writes, not the fail-closed policy: wait long enough that a loaded CI
        # runner does not turn contention into a refusal (the short production waits stay under test elsewhere).
        with patch.object(telemetry, 'LOCK_WAIT_SECONDS', 30), patch.object(telemetry, 'SQLITE_TIMEOUT_SECONDS', 30):
            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(lambda _: self.record(), range(24)))
        self.assertEqual(sum(r['count'] for r in self.store.report()['rows'] if r['metric'] == 'calls'), 24)

    def test_incremental_export_merge_and_replay(self):
        self.record()
        first = self.root / 'first.json'
        self.store.export(first)
        self.record()
        second = self.root / 'second.json'
        self.store.export(second)
        target = telemetry.Store(self.root / 'target')
        self.assertEqual(target.merge(first)['status'], 'merged')
        self.assertEqual(target.merge(first)['status'], 'duplicate')
        self.assertEqual(target.merge(second)['status'], 'merged')
        self.assertEqual(sum(r['count'] for r in target.report()['rows'] if r['metric'] == 'calls'), 2)
        self.assertEqual(self.store.merge(first)['status'], 'duplicate')
        self.assertEqual(target.export(self.root / 'no-relay.json')['status'], 'empty')
        changed = json.loads(first.read_text())
        changed['rows'][0]['count'] += 1
        (self.root / 'changed.json').write_text(json.dumps(changed))
        with self.assertRaises(ValueError):
            target.merge(self.root / 'changed.json')

    def test_exchange_validation_and_failed_export_recovery(self):
        self.record()
        directory = self.root / 'not-a-file'
        directory.mkdir()
        with self.assertRaises((ValueError, OSError)):
            self.store.export(directory)
        exported = self.root / 'recovered.json'
        self.store.export(exported)
        self.assertEqual(sum(r['count'] for r in json.loads(exported.read_text())['rows'] if r['metric'] == 'calls'), 1)
        target = telemetry.Store(self.root / 'target')
        bad = json.loads(exported.read_text())
        bad['repository'] = 'SECRET'
        (self.root / 'bad.json').write_text(json.dumps(bad))
        with self.assertRaises(ValueError):
            target.merge(self.root / 'bad.json')
        self.assertFalse((self.root / 'target').exists())

    def test_unsafe_locations_and_collector_failure_preserve_results(self):
        repo = self.root / 'repo'
        repo.mkdir()
        (repo / '.git').mkdir()
        with self.assertRaises(ValueError):
            telemetry.Store(repo / 'metrics').record('cli', 'analyze', 'ok', 1)
        self.directory.symlink_to(repo, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.record()
        output = io.StringIO()
        with redirect_stdout(output), telemetry.observe('local', 'cli', 'analyze', directory=self.directory):
            print('original-output')
        self.assertEqual(output.getvalue(), 'original-output\n')
        with self.assertRaises(KeyboardInterrupt):
            with telemetry.observe('local', 'cli', 'analyze', directory=self.root / 'cancelled'):
                raise KeyboardInterrupt()
        rows = telemetry.Store(self.root / 'cancelled').report()['rows']
        self.assertEqual([r['outcome'] for r in rows if r['metric'] == 'calls'], ['cancelled'])

class TelemetryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.directory = self.root / 'metrics'
        self.lookup = patch.object(telemetry, 'default_directory', return_value=self.directory)
        self.lookup.start()
        self.addCleanup(self.lookup.stop)

    def cli(self, arguments):
        from agent_braid.cli import main
        out = io.StringIO()
        with redirect_stdout(out):
            code = main(arguments)
        return code, out.getvalue()

    def test_cli_plugin_forecast_and_telemetry_commands_coexist_without_collection(self):
        home = self.root / 'plugin-home'
        plugin = self.cli(['plugin', 'workspaces', '--home', str(home)])
        self.assertEqual(plugin[0], 0)
        self.assertEqual(json.loads(plugin[1]), {
            'schema': 'agent-braid-plugin-registry/v0.2', 'telemetry': 'off', 'workspaces': []})
        self.assertFalse(home.exists())
        forecast = self.cli(['forecast', 'capabilities'])
        self.assertEqual(forecast[0], 0)
        capabilities = json.loads(forecast[1])
        self.assertEqual(capabilities['version'], 'agent-braid-forecast-capabilities-v1')
        self.assertEqual(capabilities['defaultMode'], 'off')
        self.assertFalse(capabilities['executionAuthorization'])
        status = self.cli(['telemetry', 'status', '--format', 'json'])
        self.assertEqual(status[0], 0)
        telemetry_status = json.loads(status[1])
        self.assertEqual(telemetry_status['schema'], 'agent-braid-local-telemetry-status/v1')
        self.assertEqual(telemetry_status['defaultMode'], 'off')
        self.assertFalse(telemetry_status['storePresent'])
        self.assertEqual(telemetry_status['aggregateCells'], 0)
        self.assertFalse(self.directory.exists())

    def test_cli_equivalence_success_refusal_and_management(self):
        fixture = str(Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json')
        off = self.cli(['analyze', fixture])
        self.assertFalse(self.directory.exists())
        on = self.cli(['analyze', fixture, '--telemetry', 'local'])
        self.assertEqual(on, off)
        failed = self.cli(['analyze', str(self.root / 'absent'), '--telemetry', 'local'])
        self.assertEqual(failed[0], 2)
        rows = telemetry.Store().report()['rows']
        calls = [r for r in rows if r['metric'] == 'calls']
        self.assertEqual({r['outcome']: r['count'] for r in calls}, {'ok': 1, 'refused': 1})
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'classification'), 1)
        report = self.cli(['telemetry', 'report', '--format', 'json'])
        self.assertEqual(report[0], 0)
        self.assertEqual(len(json.loads(report[1])['rows']), len(rows))
        self.assertEqual(self.cli(['telemetry', 'status'])[0], 0)
        self.assertEqual(self.cli(['telemetry', 'purge'])[0], 0)
        self.assertEqual(telemetry.Store().report()['rows'], [])

    def test_mcp_counts_boundary_once_and_preserves_envelope(self):
        import threading
        from agent_braid.tooling_mcp import ToolingConfig, ToolingService
        source, results = self.root / 'source', self.root / 'results'
        source.mkdir()
        results.mkdir()
        service = ToolingService(ToolingConfig(source, results, telemetry='local'))
        request = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        result = service.invoke('analyze-work', {'kind': 'aim', 'request': request}, threading.Event())
        self.assertEqual(result['status'], 'ok')
        event = threading.Event()
        event.set()
        cancelled = service.invoke('analyze-work', {'kind': 'aim', 'request': request}, event)
        self.assertEqual(cancelled['status'], 'refused')
        service.invoke('SECRET', {}, threading.Event())
        rows = telemetry.Store().report()['rows']
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'calls'), 3)
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'classification'), 1)
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'calls' and r['outcome'] == 'cancelled'), 1)
        self.assertNotIn('SECRET', json.dumps(rows))

    def test_installation_preview_receipt_doctor_and_uninstall(self):
        from dataclasses import replace
        from agent_braid.tooling_install import Selection, plan, apply, doctor
        source, results = self.root / 'source', self.root / 'results'
        source.mkdir()
        results.mkdir()
        selection = Selection('codex', 'user', source, results, destination=self.root / 'host', telemetry='local')
        transaction = plan(selection, source_checkout=True)
        preview = transaction.preview()
        self.assertEqual(preview['telemetry']['mode'], 'local')
        self.assertFalse(selection.destination.exists())
        self.assertFalse(self.directory.exists())
        apply(transaction, preview_digest=preview['previewDigest'])
        args = selection.server()['args']
        self.assertEqual(args[-2:], ['--telemetry', 'local'])
        receipt = json.loads(selection.paths()[2].read_text())
        self.assertEqual(receipt['telemetry']['mode'], 'local')
        self.assertEqual(doctor(selection, source_checkout=True)['checks']['telemetry']['configuredMode'], 'local')
        telemetry.Store().record('cli', 'analyze', 'ok', 1)
        uninstall = plan(selection, operation='uninstall', source_checkout=True)
        apply(uninstall, preview_digest=uninstall.preview()['previewDigest'])
        self.assertTrue(telemetry.Store().report()['rows'])
        disabled = replace(selection, telemetry='off')
        self.assertNotIn('--telemetry', disabled.server()['args'])

class TelemetryBoundaryTests(unittest.TestCase):
    setUp = TelemetryTests.setUp
    record = TelemetryTests.record

    def test_capacity_rollback_and_oversized_store(self):
        self.record()
        before = self.store.report()['rows']
        with patch.object(telemetry, 'MAX_ROWS', 1):
            with self.assertRaises(ValueError):
                self.record()
        self.assertEqual(self.store.report()['rows'], before)
        with (self.directory / 'metrics.sqlite3').open('ab') as stream:
            stream.truncate(telemetry.MAX_DATABASE_BYTES + 1)
        with self.assertRaises(ValueError):
            self.record()
        before_failures = telemetry._known_failures
        with telemetry.observe('local', 'cli', 'analyze', directory=self.directory):
            pass
        self.assertEqual(telemetry._known_failures, before_failures + 1)

    def test_multiple_processes_and_lock_failure(self):
        import subprocess
        import sys
        # The children exercise cross-process correctness with long waits; the busy refusal below uses the short defaults.
        code = ("from pathlib import Path; import sys; import agent_braid.tooling_telemetry as t; "
                "t.LOCK_WAIT_SECONDS = t.SQLITE_TIMEOUT_SECONDS = 30; s=t.Store(Path(sys.argv[1])); "
                "[s.record('cli','analyze','ok',1) for _ in range(10)]")
        children = [subprocess.Popen([sys.executable, '-c', code, str(self.directory)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(3)]
        for child in children:
            out, error = child.communicate(timeout=60)
            self.assertEqual(child.returncode, 0, error.decode())
            self.assertEqual(out, b'')
        self.assertEqual(sum(r['count'] for r in self.store.report()['rows'] if r['metric'] == 'calls'), 30)
        import fcntl
        with (self.directory / 'store.lock').open('rb') as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            with self.assertRaisesRegex(ValueError, 'busy'):
                self.record()
        self.assertEqual(sum(r['count'] for r in self.store.report()['rows'] if r['metric'] == 'calls'), 30)

    def test_corrupt_public_and_linked_files_refuse(self):
        self.record()
        database = self.directory / 'metrics.sqlite3'
        database.chmod(0o644)
        with self.assertRaises(ValueError):
            self.record()
        database.chmod(0o600)
        os.link(database, self.root / 'alias')
        with self.assertRaises(ValueError):
            self.record()
        (self.root / 'alias').unlink()
        database.write_bytes(b'CORRUPT')
        with self.assertRaises(ValueError):
            self.record()

    def test_strict_exchange_duplicate_fields_dates_counts_and_no_disk_on_refusal(self):
        import uuid
        row = dict(day=telemetry.today().isoformat(), surface='cli', operation='analyze', outcome='ok', metric='calls', bucket='all', count=1)
        batch = dict(schema=telemetry.SCHEMA, batchId=str(uuid.uuid4()), rows=[row])
        for key, bad in [('count', True), ('count', -1), ('count', 1.5), ('count', telemetry.MAX_COUNT + 1), ('day', '2000-01-01'), ('bucket', 'SECRET'), ('operation', ['SECRET'])]:
            value = dict(batch, rows=[dict(row, **{key: bad})])
            path = self.root / 'input.json'
            path.write_text(json.dumps(value))
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                self.store.merge(path)
            self.assertFalse(self.directory.exists())
        path.write_text('{"schema":1,"schema":2}')
        with self.assertRaises(ValueError):
            self.store.merge(path)
        path.write_bytes(b' ' * (telemetry.MAX_BATCH_BYTES + 1))
        with self.assertRaises(ValueError):
            self.store.merge(path)

    def test_export_write_failure_retries_identical_batch(self):
        self.record()
        destination = self.root / 'out.json'
        def fail_export(fd):
            raise OSError('SENSITIVE_WRITE_FAILURE')
        with patch.object(telemetry.os, 'fsync', side_effect=fail_export), self.assertRaises(OSError):
            self.store.export(destination)
        self.assertFalse(destination.exists())
        connection = sqlite3.connect(self.directory / 'metrics.sqlite3')
        try:
            expected = connection.execute('SELECT payload FROM pending').fetchone()[0]
        finally:
            connection.close()
        opened = []
        original_open = os.open
        def track_export_open(path, *args, **kwargs):
            descriptor = original_open(path, *args, **kwargs)
            if Path(path) == destination:
                opened.append(descriptor)
            return descriptor
        with patch.object(telemetry.os, 'open', side_effect=track_export_open), \
             patch.object(telemetry.os, 'fdopen', side_effect=OSError('SENSITIVE_WRAPPER_FAILURE')):
            with self.assertRaises(OSError):
                self.store.export(destination)
        self.assertFalse(destination.exists())
        self.assertEqual(len(opened), 1)
        try:
            with self.assertRaises(OSError):
                os.fstat(opened[0])
        finally:
            # A failing regression must not leak its descriptor into later tests.
            try:
                os.close(opened[0])
            except OSError:
                pass
        self.store.export(destination)
        self.assertEqual(destination.read_bytes(), expected)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)

    def test_pending_retention_reports_known_export_loss(self):
        now = telemetry.today()
        with patch.object(telemetry, 'today', return_value=now - timedelta(days=29)):
            self.record()
            blocked = self.root / 'blocked'
            blocked.mkdir()
            with self.assertRaises(ValueError):
                self.store.export(blocked)
        with patch.object(telemetry, 'today', return_value=now + timedelta(days=1)):
            report = self.store.report()
        self.assertEqual(report['rows'], [])
        self.assertEqual(report['knownPendingExportCallsDiscarded'], 1)

class TelemetryRegressionTests(unittest.TestCase):
    def test_management_refuses_missing_secure_open_flags_without_traceback(self):
        from agent_braid.cli import main
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sender = telemetry.Store(root / 'sender')
            sender.record('cli', 'analyze', 'ok', 1)
            source = root / 'input.json'
            sender.export(source)
            sender.record('cli', 'analyze', 'ok', 1)
            cases = (
                ('O_NOFOLLOW', ['merge', str(source)], root / 'target'),
                ('O_NONBLOCK', ['merge', str(source)], root / 'target'),
                ('O_NOFOLLOW', ['report'], sender.directory),
                ('O_NOFOLLOW', ['export', str(root / 'output.json')], sender.directory),
                ('O_DIRECTORY', ['export', str(root / 'output.json')], sender.directory),
            )
            for flag, command, directory in cases:
                out, error = io.StringIO(), io.StringIO()
                with self.subTest(flag=flag, command=command[0]), patch.object(telemetry.os, flag), \
                     patch.object(telemetry, 'default_directory', return_value=directory):
                    delattr(telemetry.os, flag)
                    with redirect_stdout(out), redirect_stderr(error):
                        code = main(['telemetry', *command])
                    self.assertEqual(code, 2)
                    self.assertEqual(out.getvalue(), '')
                    self.assertEqual(error.getvalue(), 'local telemetry refused: invalid batch, unsafe/unavailable storage or local capacity limit\n')
                    self.assertFalse((root / 'target').exists())
                    self.assertFalse((root / 'output.json').exists())

    def test_existing_export_must_be_synced_before_pending_acknowledgement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            store = telemetry.Store(root / 'store')
            store.record('cli', 'analyze', 'ok', 1)
            destination = root / 'batch.json'
            destination.mkdir()
            with self.assertRaises(ValueError):
                store.export(destination)
            with closing(sqlite3.connect(store.directory / 'metrics.sqlite3')) as db:
                pending = db.execute('SELECT payload FROM pending').fetchone()[0]
            destination.rmdir()
            destination.write_bytes(pending)
            destination.chmod(0o600)
            original_fsync = os.fsync
            def fail_file_sync(fd):
                if stat.S_ISREG(os.fstat(fd).st_mode):
                    raise OSError('synthetic unsynced existing export')
                original_fsync(fd)
            with patch.object(telemetry.os, 'fsync', side_effect=fail_file_sync):
                with self.assertRaises(OSError):
                    store.export(destination)
            self.assertEqual(destination.read_bytes(), pending)
            with closing(sqlite3.connect(store.directory / 'metrics.sqlite3')) as db:
                self.assertEqual(db.execute('SELECT payload FROM pending').fetchone()[0], pending)
            self.assertEqual(store.export(destination), {'status': 'exported', 'batchId': json.loads(pending)['batchId']})
            self.assertEqual(store.export(root / 'next.json'), {'status': 'empty'})

    def test_import_replaced_with_symlink_between_check_and_open_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            sender = telemetry.Store(root / 'sender')
            sender.record('cli', 'analyze', 'ok', 1)
            original = root / 'original.json'
            sender.export(original)
            source = root / 'incoming.json'
            source.write_bytes(original.read_bytes())
            target = telemetry.Store(root / 'target')
            original_is_symlink = Path.is_symlink
            swaps = []
            def replace_after_check(path):
                if path == source and not swaps:
                    path.unlink()
                    path.symlink_to(original)
                    swaps.append(True)
                    return False
                return original_is_symlink(path)
            with patch.object(Path, 'is_symlink', replace_after_check):
                with self.assertRaises((OSError, ValueError)):
                    target.merge(source)
            self.assertEqual(swaps, [True])
            self.assertFalse(target.directory.exists())

    def test_management_does_not_create_absent_database_or_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp).resolve() / 'existing'
            directory.mkdir(mode=0o700)
            self.assertEqual(telemetry.Store(directory).report()['rows'], [])
            self.assertEqual(list(directory.iterdir()), [])

    def test_single_kind_bound_rolls_back_before_export_becomes_impossible(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = telemetry.Store(Path(tmp).resolve() / 'store')
            with patch.object(telemetry, 'MAX_ROWS', 2), self.assertRaises(ValueError):
                store.record('cli', 'analyze', 'ok', 1)
            self.assertEqual(store.report()['rows'], [])

class TelemetryFinalControls(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.store = telemetry.Store(self.root / 'metrics')

    def test_sqlite_full_and_transaction_rollback_preserve_totals(self):
        completed = 0
        hit_limit = False
        with patch.object(telemetry, 'MAX_DATABASE_BYTES', 32768):
            for operation in telemetry.OPERATIONS['mcp']:
                for outcome in telemetry.OUTCOMES:
                    for duration in (0, 2, 20, 200, 2000, 20000):
                        try:
                            self.store.record('mcp', operation, outcome, duration)
                            completed += 1
                        except ValueError:
                            hit_limit = True
                            break
                    if hit_limit:
                        break
                if hit_limit:
                    break
            rows = self.store.report()['rows']
        self.assertTrue(hit_limit)
        self.assertGreater(completed, 0)
        self.assertEqual(sum(r['count'] for r in rows if r['metric'] == 'calls'), completed)
        self.assertLessEqual((self.store.directory / 'metrics.sqlite3').stat().st_size, 32768)

    def test_private_store_header_and_free_pages_are_controlled(self):
        self.store.record('cli', 'analyze', 'ok', 1)
        connection = sqlite3.connect(self.store.directory / 'metrics.sqlite3')
        try:
            self.assertEqual(connection.execute('PRAGMA auto_vacuum').fetchone()[0], 1)
            self.assertEqual(connection.execute('PRAGMA user_version').fetchone()[0], 1)
            self.assertEqual(connection.execute('PRAGMA application_id').fetchone()[0], telemetry.APPLICATION_ID)
        finally:
            connection.close()
        self.store.purge()
        connection = sqlite3.connect(self.store.directory / 'metrics.sqlite3')
        try:
            self.assertEqual(connection.execute('PRAGMA freelist_count').fetchone()[0], 0)
        finally:
            connection.close()
        foreign = self.root / 'foreign'
        foreign.mkdir(mode=0o700)
        database = foreign / 'metrics.sqlite3'
        connection = sqlite3.connect(database)
        connection.execute('CREATE TABLE foreign_data (value TEXT)')
        connection.commit()
        connection.close()
        database.chmod(0o600)
        before = database.read_bytes()
        with self.assertRaises(ValueError):
            telemetry.Store(foreign).record('cli', 'analyze', 'ok', 1)
        self.assertEqual(database.read_bytes(), before)

    def test_bare_repositories_are_refused(self):
        repository = self.root / 'bare'
        repository.mkdir()
        (repository / 'objects').mkdir()
        (repository / 'refs').mkdir()
        (repository / 'HEAD').write_text('ref: refs/heads/main\n')
        with self.assertRaises(ValueError):
            telemetry.Store(repository / 'metrics').record('cli', 'analyze', 'ok', 1)
        self.assertFalse((repository / 'metrics').exists())

    def test_doctor_recognizes_equal_form_and_does_not_collect(self):
        from agent_braid.tooling_install import Selection, doctor
        source, results, host = self.root / 'source', self.root / 'results', self.root / 'host'
        source.mkdir(); results.mkdir(); host.mkdir()
        selection = Selection('claude', 'user', source, results, destination=host)
        config, _, _ = selection.paths()
        config.write_text(json.dumps({'mcpServers': {'agent-braid': {'command': 'python', 'args': ['-m','agent_braid','tooling','serve','--telemetry=local']}}}))
        self.assertEqual(doctor(selection, source_checkout=True)['checks']['telemetry']['configuredMode'], 'local')
        self.assertFalse(self.store.directory.exists())

    def test_core_and_opt_in_survive_unavailable_sqlite(self):
        import subprocess
        import sys
        script = '''import builtins, io, json, sys
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
original = builtins.__import__
def blocked(name,*args,**kwargs):
    if name == 'sqlite3': raise ImportError('synthetic missing sqlite')
    return original(name,*args,**kwargs)
with patch.object(builtins,'__import__',side_effect=blocked), patch.object(Path,'home',return_value=Path(sys.argv[2])):
    from agent_braid.cli import main
    results=[]
    for mode in ('off','local'):
        output=io.StringIO()
        with redirect_stdout(output): code=main(['analyze',sys.argv[1],'--telemetry',mode])
        results.append((code,output.getvalue()))
    assert results[0] == results[1] and results[0][0] == 0
    assert not (Path(sys.argv[2])/'.local').exists()
print('preserved')
'''
        fixture = Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json'
        result = subprocess.run([sys.executable, '-c', script, str(fixture), str(self.root)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'preserved\n')

    def test_analyze_git_matches_outputs_and_provenance(self):
        from agent_braid.cli import main
        from tests.test_git_adapter import GitAdapterTests
        fixture = GitAdapterTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        request = self.root / 'request.json'
        request.write_text(json.dumps(fixture.request()))
        provenance = self.root / 'provenance.json'
        outputs = []
        with patch.object(telemetry, 'default_directory', return_value=self.store.directory):
            for mode in ('off', 'local'):
                output = io.StringIO()
                with redirect_stdout(output):
                    code = main(['analyze-git', str(request), '--provenance-output', str(provenance), '--telemetry', mode])
                outputs.append((code, output.getvalue(), provenance.read_bytes()))
        self.assertEqual(outputs[0], outputs[1])
        self.assertEqual(outputs[0][0], 0)
        self.assertEqual(sum(r['count'] for r in self.store.report()['rows'] if r['metric'] == 'calls'), 1)

    def test_mcp_envelope_is_identical_with_collector_write_failure(self):
        from dataclasses import replace
        import threading
        import uuid
        from agent_braid.tooling_mcp import ToolingConfig, ToolingService
        source, results = self.root / 'source', self.root / 'results'
        source.mkdir(); results.mkdir()
        config = ToolingConfig(source, results)
        request = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        fixed = uuid.UUID('12345678-1234-4234-8234-123456789abc')
        with patch('agent_braid.tooling_mcp.uuid.uuid4', return_value=fixed):
            baseline = ToolingService(config).invoke('analyze-work', {'kind':'aim','request':request}, threading.Event())
            with patch.object(telemetry.Store, 'record', side_effect=OSError('SENSITIVE_FAILURE')):
                actual = ToolingService(replace(config, telemetry='local')).invoke('analyze-work', {'kind':'aim','request':request}, threading.Event())
        self.assertEqual(actual, baseline)
        self.assertEqual(actual['status'], 'ok')
        self.assertNotIn('SENSITIVE_FAILURE', json.dumps(actual))

    def test_documentation_tracking_and_technical_dependencies_are_consistent(self):
        from scripts.sync_github_tracking import source_inventory
        root = Path(__file__).resolve().parents[1]
        config, inventory = source_inventory(root, root / 'docs/development/github-tracking.json')
        alignment = json.loads((root / 'specs/047-local-technical-telemetry/alignment.json').read_text())
        # M4.5 work may be parked in Deferred, so select by the aligned spec set, not the current milestone.
        aligned = {x['id'] for x in alignment['specs']}
        selected = [x for x in inventory if x['key'].split('/')[0] in aligned]
        tasks = [x for x in selected if x['kind'] == 'task']
        self.assertEqual(alignment['sourceCounts']['tasks'], len(tasks))
        self.assertEqual(alignment['sourceCounts']['tasksChecked'], sum(x['state']=='closed' for x in tasks))
        self.assertEqual({x['id'] for x in alignment['specs']}, {'SPEC-039','SPEC-040','SPEC-041','SPEC-042','SPEC-043','SPEC-044','SPEC-046','SPEC-047','SPEC-054','SPEC-060'})
        states = {x['key']:x['state'] for x in selected}
        self.assertEqual(states['SPEC-044/T004'], 'closed')
        self.assertEqual(states['SPEC-044/T017'], 'open')
        self.assertEqual(states['SPEC-044/T018'], 'open')
        self.assertEqual(states['SPEC-047/T010'], 'closed')
        graph = {}
        for edge in alignment['dependencies']:
            if edge['kind'] == 'technical':
                graph.setdefault(edge['successor'], []).append(edge['predecessor'])
        def visit(node, active):
            self.assertNotIn(node, active, 'technical dependency cycle')
            for parent in graph.get(node, []): visit(parent, active|{node})
        for node in graph: visit(node,set())
        self.assertIn('SPEC-047', graph['SPEC-044'])
        self.assertNotIn('SPEC-044', graph['SPEC-047'])
        drafts = json.loads((root / 'specs/047-local-technical-telemetry/tracking-drafts.json').read_text())
        self.assertEqual(len(drafts['newRecordKeys']), 13)
        self.assertEqual(len(set(drafts['newRecordKeys'])), 13)
        for record in drafts['records']:
            self.assertEqual(record['state'], states[record['key']])

class TelemetryStandaloneTests(unittest.TestCase):
    def test_standalone_server_parser_threads_explicit_consent(self):
        from unittest.mock import AsyncMock
        from agent_braid import tooling_mcp
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, results = root / 'source', root / 'results'
            source.mkdir(); results.mkdir()
            with patch.object(tooling_mcp, 'serve_stdio', new_callable=AsyncMock) as serve:
                self.assertEqual(tooling_mcp.main(['--source-root',str(source),'--result-parent',str(results),'--telemetry','local']), 0)
                self.assertEqual(serve.await_args.args[0].telemetry, 'local')

@unittest.skipUnless(importlib.util.find_spec('mcp'), 'optional pinned mcp SDK absent; direct boundary controls remain separate')
class TelemetrySdkTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_sdk_stdio_counts_calls_but_not_discovery_for_both_modes(self):
        import asyncio
        import sys
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        root = Path(__file__).resolve().parents[1]
        request = json.loads((root / 'examples/analysis/file-edits.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            source, results = base / 'source', base / 'results'
            source.mkdir(); results.mkdir()
            directory = base / 'home/.local/share/agent-braid/telemetry'
            script = "from pathlib import Path; from unittest.mock import patch; import sys; from agent_braid.tooling_mcp import main; selected=Path(sys.argv[1]); arguments=sys.argv[2:]; context=patch.object(Path,'home',return_value=selected); context.start(); raise SystemExit(main(arguments))"
            for mode in ('auto', 'legacy'):
                parameters = StdioServerParameters(command=sys.executable,
                    args=['-c',script,str(base/'home'),'--source-root',str(source),'--result-parent',str(results),'--telemetry','local'], cwd=str(root))
                async with Client(parameters, mode=mode) as client:
                    before = telemetry.Store(directory).report()['rows']
                    self.assertEqual({t.name for t in (await client.list_tools()).tools}, {'analyze-work','analyze','prepare'})
                    await client.list_resources()
                    await client.list_prompts()
                    self.assertEqual(telemetry.Store(directory).report()['rows'], before)
                    for _ in range(2):
                        response = await asyncio.wait_for(client.call_tool('analyze-work', {'kind':'aim','request':request}), timeout=15)
                        self.assertEqual(response.structured_content['status'], 'ok')
            rows = telemetry.Store(directory).report()['rows']
            self.assertEqual(sum(r['count'] for r in rows if r['metric']=='calls'), 4)
            self.assertEqual(sum(r['count'] for r in rows if r['metric']=='classification'), 4)
            raw = b''.join(p.read_bytes() for p in directory.iterdir())
            self.assertNotIn(str(source).encode(), raw)
            self.assertNotIn(b'edit-readme', raw)

class TelemetryExportBoundTests(unittest.TestCase):
    def test_allowed_large_classification_totals_remain_exportable(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            store = telemetry.Store(root / 'store')
            store.record('cli', 'analyze', 'ok', 1, {key:telemetry.MAX_COUNT for key in telemetry.CATEGORIES})
            self.assertEqual(store.export(root / 'batch.json')['status'], 'exported')
            value = json.loads((root / 'batch.json').read_text())
            self.assertEqual(sum(r['count'] for r in value['rows'] if r['metric']=='classification'), 4*telemetry.MAX_COUNT)
