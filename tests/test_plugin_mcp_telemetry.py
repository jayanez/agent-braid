# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-047 T011: plugin-level refusals, bootstrap calls and serve-start in local telemetry."""
import json
from pathlib import Path
import shutil
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_telemetry as telemetry
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import MigrationRequired, RegistryError, RegistryStale, apply, load, plan_setup
from tests import test_plugin_mcp as mcp_tests
from tests import test_plugin_registry as registry_tests

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples/analysis/file-edits.json').read_text())


class PluginTelemetryTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install
    second_repo = registry_tests.PluginRegistryTests.second_repo
    rewrite = mcp_tests.PluginRouterTests.rewrite

    def consent(self, mode='local'):
        preview = plan_setup(self.home, [], telemetry=mode)
        apply(self.home, preview, preview['previewDigest'])

    def start(self, mode='local', roots=None):
        """Install, give consent and return a router reading a throwaway telemetry store."""
        self.install(roots)
        self.consent(mode)
        self.store = self.base / 'telemetry'
        patcher = patch.object(telemetry, 'default_directory', return_value=self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        return PluginRouter(self.home)

    def cells(self):
        return {(r['surface'], r['operation'], r['outcome'], r['metric'], r['bucket']): r['count']
                for r in telemetry.Store().report()['rows']}

    def reasons(self, surface='mcp', operation='analyze-work'):
        return {k[4]: v for k, v in self.cells().items() if k[:2] == (surface, operation) and k[3] == 'refusal-reason'}

    def call(self, router, name='analyze-work', args=None):
        return router.invoke(name, args, threading.Event())

    def identifier(self):
        return load(self.home)['workspaces'][0]['workspaceId']

    def test_each_router_refusal_lands_in_its_bucket(self):
        router = self.start()
        wid = self.identifier()
        sample = {'workspaceId': wid, 'kind': 'aim', 'request': {}}
        self.call(router, args={'workspaceId': 'not-registered'})              # workspace-unregistered
        self.call(router, args={'kind': 'aim'})                                 # workspaceId missing: arguments-invalid
        self.call(router, args=['not', 'an', 'object'])                         # arguments-invalid
        with router.admission:
            self.call(router, args=sample)                                      # admission-busy
        with patch('agent_braid.tooling_mcp.MAX_INVENTORY_ARTIFACTS', 0):
            self.call(router, args=sample)                                      # inventory-full
        self.call(router, args={'workspaceId': wid})                            # service: arguments-invalid
        self.call(router, 'execute', {'workspaceId': wid, 'plan': {}, 'grantId': 'x'})  # service: grant-missing
        self.call(router, 'no-such-tool', {'workspaceId': wid})                 # service: arguments-invalid, operation other
        self.rewrite(lambda v: dict(v, workspaces=[]))
        self.call(router, args={'workspaceId': wid})                            # reconnect-required
        self.assertEqual(self.reasons(), {'workspace-unregistered': 1, 'arguments-invalid': 3, 'admission-busy': 1,
                                          'inventory-full': 1, 'reconnect-required': 1})
        self.assertEqual(self.reasons(operation='execute'), {'grant-missing': 1})
        self.assertEqual(self.reasons(operation='other'), {'arguments-invalid': 1})

    def test_calls_are_counted_once_with_a_duration_and_a_matching_reason(self):
        router = self.start()
        wid = self.identifier()
        self.assertEqual(self.call(router, args={'workspaceId': wid, 'kind': 'aim', 'request': SAMPLE})['status'], 'ok')
        self.assertEqual(self.call(router, args={'workspaceId': wid})['status'], 'refused')
        cells = self.cells()
        self.assertEqual(sum(v for k, v in cells.items() if k[1:4] == ('analyze-work', 'ok', 'calls')), 1)
        self.assertEqual(sum(v for k, v in cells.items() if k[1:4] == ('analyze-work', 'refused', 'calls')), 1)
        self.assertEqual(sum(v for k, v in cells.items() if k[1:4] == ('analyze-work', 'refused', 'duration')), 1)
        self.assertEqual(sum(v for k, v in cells.items() if k[3] == 'refusal-reason'), 1)
        self.assertGreater(sum(v for k, v in cells.items() if k[3] == 'classification'), 0)

    def test_bootstrap_tools_count_calls_only(self):
        router = self.start()
        self.assertEqual(self.call(router, 'plugin-status', {})['status'], 'ok')
        self.assertEqual(self.call(router, 'workspaces', {})['status'], 'ok')
        self.assertEqual(self.call(router, 'workspaces', {'x': 1})['status'], 'refused')
        mine = {k: v for k, v in self.cells().items() if k[1] in {'plugin-status', 'workspaces'}}
        self.assertEqual(mine, {('mcp', 'plugin-status', 'ok', 'calls', 'all'): 1,
                                ('mcp', 'workspaces', 'ok', 'calls', 'all'): 1,
                                ('mcp', 'workspaces', 'refused', 'calls', 'all'): 1})

    def test_consent_off_writes_nothing_for_any_plugin_event(self):
        router = self.start('off')
        wid = self.identifier()
        self.call(router, 'plugin-status', {})
        self.call(router, args={'workspaceId': wid})
        self.call(router, args={'workspaceId': 'nope'})
        router.record_start()
        self.assertFalse(self.store.exists())

    def test_the_router_is_the_only_measurement_owner(self):
        router = self.start()
        wid = self.identifier()
        with patch.object(telemetry, 'observe', wraps=telemetry.observe) as observed:
            self.call(router, args={'workspaceId': wid, 'kind': 'aim', 'request': SAMPLE})
        self.assertEqual(observed.call_count, 1)

    def test_vanished_and_unsafe_workspaces_report_their_bucket_when_called(self):
        other = self.second_repo()
        self.start(roots=[self.repo, other])
        rows = {r['sourceRoot']: r['workspaceId'] for r in load(self.home)['workspaces']}
        shutil.rmtree(self.repo)

        def poison(value):
            for row in value['workspaces']:
                if row['sourceRoot'] == str(other):
                    row['worktreeRoots'] = [str(self.home)]
            return value
        self.rewrite(poison)
        router = PluginRouter(self.home)
        self.call(router, args={'workspaceId': rows[str(self.repo)]})
        self.call(router, args={'workspaceId': rows[str(other)]})
        self.assertEqual(self.reasons(), {'registry-root-missing': 1, 'registry-unsafe-path': 1})

    def test_registry_damaged_mid_session_reports_its_shape_bucket(self):
        router = self.start()
        wid = self.identifier()
        (self.home / 'registry.json').write_text('{"schema":"nope"}')
        self.assertEqual(self.call(router, args={'workspaceId': wid})['status'], 'refused')
        self.assertEqual(self.reasons(), {'registry-shape': 1})

    def test_reason_comes_from_the_code_never_from_the_message(self):
        router = self.start()
        wid = self.identifier()
        cases = [(RegistryError('Plugin admission is busy; inventory is full', code='registry-shape'), 'registry-shape'),
                 (RegistryError('reconnect-required arguments-invalid'), 'other'),
                 (RegistryError('x', code='free text from a bug'), 'other'),
                 (RegistryStale('Registry changed'), 'reconnect-required'),
                 (MigrationRequired('v0.1'), 'migration-required'),
                 (OSError('workspace-unregistered'), 'other'),
                 (ValueError('grant-missing'), 'other')]
        for error, bucket in cases:
            with self.subTest(error=repr(error)), patch.object(router, '_require_current', side_effect=error):
                before = self.reasons().get(bucket, 0)
                self.call(router, args={'workspaceId': wid})
                self.assertEqual(self.reasons().get(bucket, 0), before + 1)

    def test_closed_vocabulary(self):
        self.assertEqual(telemetry.BUCKETS['refusal-reason'], (
            'registry-root-missing', 'registry-unsafe-path', 'registry-shape', 'migration-required',
            'reconnect-required', 'workspace-unregistered', 'admission-busy', 'inventory-full',
            'grant-missing', 'arguments-invalid', 'other'))
        self.assertEqual(RegistryError().code, 'other')

    def test_serve_start_is_counted_ok_and_only_by_record_start(self):
        router = self.start()
        self.assertFalse(self.store.exists(), 'constructing a router (doctor, status) must not count a start')
        router.record_start()
        self.assertEqual(self.cells(), {('lifecycle', 'serve-start', 'ok', 'calls', 'all'): 1})

    def test_serve_start_with_an_unserved_workspace_is_refused_with_its_bucket(self):
        other = self.second_repo()
        self.start(roots=[self.repo, other])
        shutil.rmtree(self.repo)
        PluginRouter(self.home).record_start()
        self.assertEqual(self.cells(), {('lifecycle', 'serve-start', 'refused', 'calls', 'all'): 1,
                                        ('lifecycle', 'serve-start', 'refused', 'refusal-reason', 'registry-root-missing'): 1})

    def test_serve_start_with_a_quarantined_row_is_refused_with_its_bucket(self):
        self.start()
        self.rewrite(lambda v: dict(v, workspaces=[dict(v['workspaces'][0], worktreeRoots=[str(self.home)])]))
        PluginRouter(self.home).record_start()
        self.assertEqual(self.reasons('lifecycle', 'serve-start'), {'registry-unsafe-path': 1})

    def test_serve_start_writes_nothing_when_the_registry_fails_validation(self):
        self.start()
        (self.home / 'registry.json').write_text('{"schema":"nope"}')
        with self.assertRaises(RegistryError):
            PluginRouter(self.home)
        (self.home / 'registry.json').chmod(0o644)  # private-state failure
        with self.assertRaises(RegistryError):
            PluginRouter(self.home)
        self.assertFalse(self.store.exists())

    def test_serve_start_writes_nothing_for_a_legacy_registry(self):
        registry_tests.PluginRegistryTests.legacy_registry(self)
        self.store = self.base / 'telemetry'
        with patch.object(telemetry, 'default_directory', return_value=self.store):
            PluginRouter(self.home).record_start()
        self.assertFalse(self.store.exists())

    def test_serve_counts_a_start_only_once_the_server_exists(self):
        import asyncio
        import sys
        import types
        from agent_braid import plugin_mcp
        self.start()

        def stop(**_kwargs):
            raise RuntimeError('stop')
        # Stub the SDK modules serve() imports, so the wiring is checked even where `mcp` is not installed.
        stdio = types.ModuleType('mcp.server.stdio')
        stdio.stdio_server = stop
        fakes = {'mcp': types.ModuleType('mcp'), 'mcp.server': types.ModuleType('mcp.server'), 'mcp.server.stdio': stdio}
        with patch.dict(sys.modules, fakes):
            with patch.object(plugin_mcp, 'create_server', side_effect=RuntimeError('sdk mismatch')):
                with self.assertRaises(RuntimeError):
                    asyncio.run(plugin_mcp.serve(self.home))
            self.assertFalse(self.store.exists())
            with patch.object(plugin_mcp, 'create_server'):
                with self.assertRaises(RuntimeError):
                    asyncio.run(plugin_mcp.serve(self.home))
        self.assertEqual(self.cells(), {('lifecycle', 'serve-start', 'ok', 'calls', 'all'): 1})

    def test_grant_store_overlap_is_unsafe_path_and_a_missing_one_is_grant_missing(self):
        from agent_braid.plugin_registry import inspect_registry
        self.start()
        row = load(self.home)['workspaces'][0]
        for grant, code in ((str(self.repo), 'registry-unsafe-path'), (str(self.base / 'absent-grants'), 'grant-missing')):
            self.rewrite(lambda v: dict(v, workspaces=[dict(row, runtimeEnabled=True, grantStore=grant)]))
            self.assertEqual(inspect_registry(self.home)['quarantinedCodes'], [code])

    def test_cancelled_refusal_records_no_reason(self):
        router = self.start()
        event = threading.Event()
        event.set()
        router.invoke('analyze-work', {'workspaceId': self.identifier(), 'kind': 'aim', 'request': SAMPLE}, event)
        cells = self.cells()
        self.assertEqual([k for k in cells if k[3] == 'refusal-reason'], [])
        self.assertIn(('mcp', 'analyze-work', 'cancelled', 'calls', 'all'), cells)

    def test_standalone_service_records_its_own_reasons(self):
        from agent_braid import tooling_mcp as core
        self.start()
        (self.base / 'results').mkdir()
        service = core.ToolingService(core.ToolingConfig(self.repo, self.base / 'results', telemetry='local'))
        service.invoke('analyze-work', {'kind': 'aim'}, threading.Event())
        self.assertEqual(self.reasons(), {'arguments-invalid': 1})


if __name__ == '__main__':
    unittest.main()
