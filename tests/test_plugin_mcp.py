# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
import threading
import unittest
import importlib.util
from tests import test_plugin_registry as registry_tests
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import RegistryStale, load, plan_setup, apply


class PluginRouterTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    def test_two_workspaces_keep_core_results_and_resource_ownership(self):
        self.install()
        other = self.base / 'another'
        other.mkdir()
        import subprocess
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        self.install([other])
        router = PluginRouter(self.home)
        ids = [x['workspaceId'] for x in load(self.home)['workspaces']]
        sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        result = router.invoke('analyze-work', {'workspaceId': ids[0], 'kind': 'aim', 'request': sample}, threading.Event())
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['result']['report']['interactions'][0]['classification'], 'independent-candidate')
        uri = result['evidenceRefs'][0]['uri']
        self.assertTrue(uri.startswith('agent-braid-plugin://' + ids[0] + '/'))
        manifest = json.loads(router.read_resource(uri)[1])
        chunk = json.loads(router.read_resource(manifest['firstChunkUri'])[1])
        self.assertEqual(chunk['artifactSha256'], manifest['sha256'])
        with self.assertRaises(ValueError):
            router.read_resource(uri.replace(ids[0], ids[1]))
        self.assertEqual(router.invoke('execute', {'workspaceId': ids[0]}, threading.Event())['status'], 'refused')
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': 'not-registered'}, threading.Event())['status'], 'refused')

    def test_registry_change_requires_reconnect_and_no_root_override(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        result = router.invoke('analyze-work', {'workspaceId': identifier, 'sourceRoot': str(self.repo)}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        preview = plan_setup(self.home, [], remove=[identifier])
        apply(self.home, preview, preview['previewDigest'])
        self.assertTrue(router.status()['reconnectRequired'])
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())['status'], 'refused')

    def rewrite(self, transform):
        path = self.home / 'registry.json'
        value = transform(json.loads(path.read_text()))
        path.write_text(json.dumps(value, separators=(',', ':')))

    def make_repo(self, name):
        import subprocess
        path = self.base / name
        path.mkdir()
        subprocess.run(['git', 'init', '-q', str(path)], check=True)
        return path

    def two_workspaces(self):
        second = self.make_repo('another')
        self.install([self.repo, second])
        return [x['workspaceId'] for x in load(self.home)['workspaces']]

    def assert_not_reconnect_refusal(self, result):
        self.assertNotIn('reconnect', result['summary'])
        self.assertNotEqual(result['result'], {'code': RegistryStale.code})

    def test_noop_and_reordered_rewrites_do_not_require_reconnect(self):
        ids = self.two_workspaces()
        router = PluginRouter(self.home)
        baseline = router.status()['baselineDigest']
        self.rewrite(lambda v: v)
        self.rewrite(lambda v: dict(v, workspaces=list(reversed(v['workspaces']))))
        status = router.status()
        self.assertFalse(status['reconnectRequired'])
        self.assertEqual((status['baselineDigest'], status['currentDigest']), (baseline, baseline))
        sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        result = router.invoke('analyze-work', {'workspaceId': ids[0], 'kind': 'aim', 'request': sample}, threading.Event())
        self.assertEqual(result['status'], 'ok')
        self.assert_not_reconnect_refusal(result)

    def test_raw_byte_differences_alone_do_not_require_reconnect(self):
        self.two_workspaces()
        router = PluginRouter(self.home)
        path = self.home / 'registry.json'
        before = path.read_bytes()
        value = json.loads(before)
        path.write_text(json.dumps(dict(reversed(list(value.items()))), indent=4, sort_keys=False) + '\n\n')
        self.assertNotEqual(path.read_bytes(), before)
        status = router.status()
        self.assertFalse(status['reconnectRequired'])
        self.assertEqual(status['baselineDigest'], status['currentDigest'])

    def test_idempotent_setup_apply_does_not_require_reconnect(self):
        self.install()
        router = PluginRouter(self.home)
        self.install()
        self.assertFalse(router.status()['reconnectRequired'])

    def test_each_effective_change_requires_reconnect_and_changes_the_digest(self):
        extra = self.make_repo('third')
        second = self.make_repo('another')
        worktree = self.make_repo('worktree')
        grants = self.base / 'grants'
        grants.mkdir()
        first = lambda v, **change: dict(v, workspaces=[dict(v['workspaces'][0], **change)] + v['workspaces'][1:])
        changes = {
            'removed': lambda v: dict(v, workspaces=v['workspaces'][:1]),
            'consent': lambda v: dict(v, telemetry='local'),
            'worktree-root': lambda v: first(v, worktreeRoots=[str(worktree)]),
            'grant': lambda v: first(v, runtimeEnabled=True, grantStore=str(grants)),
        }
        for name, change in changes.items():
            with self.subTest(name):
                self.home = self.base / f'state-{name}'
                self.install([self.repo, second])
                router = PluginRouter(self.home)
                self.rewrite(change)
                status = router.status()
                self.assertTrue(status['reconnectRequired'])
                self.assertNotEqual(status['baselineDigest'], status['currentDigest'])
        with self.subTest('added'):
            self.home = self.base / 'state-added'
            self.install([self.repo])
            router = PluginRouter(self.home)
            self.install([extra])
            status = router.status()
            self.assertTrue(status['reconnectRequired'])
            self.assertNotEqual(status['baselineDigest'], status['currentDigest'])

    def test_digests_are_path_free(self):
        self.install()
        router = PluginRouter(self.home)
        status = router.status()
        for key in ('baselineDigest', 'currentDigest'):
            self.assertRegex(status[key], r'^[0-9a-f]{64}$')
        self.assertNotIn(str(self.base), json.dumps({k: status[k] for k in ('baselineDigest', 'currentDigest')}))

    def test_stale_refusal_names_reconnect_and_keeps_registered_workspace_id(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.rewrite(lambda v: dict(v, telemetry='local'))
        result = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['workspaceId'], identifier)
        self.assertEqual(result['result'], {'code': RegistryStale.code})
        self.assertIn('reconnect', result['summary'])
        self.assertIn('plugin-status', result['summary'])
        self.assertNotIn('check workspace, arguments', result['summary'])
        self.assertFalse(result['provenance']['executionAuthorization'])

    def test_stale_refusal_for_unregistered_workspace_does_not_echo_it(self):
        self.install()
        router = PluginRouter(self.home)
        self.rewrite(lambda v: dict(v, telemetry='local'))
        result = router.invoke('analyze-work', {'workspaceId': 'not-registered'}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        self.assertIsNone(result['workspaceId'])

    def test_stale_read_resource_raises_registry_stale(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.rewrite(lambda v: dict(v, telemetry='local'))
        with self.assertRaises(RegistryStale) as caught:
            router.read_resource(f'agent-braid-plugin://{identifier}/capabilities')
        self.assertIn('plugin-status', str(caught.exception))

    def test_bootstrap_tools_still_answer_when_stale(self):
        self.install()
        router = PluginRouter(self.home)
        self.rewrite(lambda v: dict(v, telemetry='local'))
        for name in ('plugin-status', 'workspaces'):
            result = router.invoke(name, {}, threading.Event())
            self.assertEqual(result['status'], 'ok')
            self.assertTrue(result['result']['reconnectRequired'])

    def test_stale_connection_keeps_its_snapshotted_roots_and_grants(self):
        self.install()
        router = PluginRouter(self.home)
        before = router.status()['workspaces']
        self.rewrite(lambda v: dict(v, workspaces=[]))
        self.assertEqual(router.status()['workspaces'], before)
        self.assertEqual(len(router.services), 1)

    def test_snapshotted_telemetry_consent_reaches_every_workspace_and_requires_reconnect(self):
        self.install()
        router = PluginRouter(self.home)
        self.assertEqual({s.config.telemetry for s in router.services.values()}, {'off'})
        self.assertEqual(router.status()['telemetry'], {'configuredMode': 'off', 'activeMode': 'off',
            'retentionDays': 30, 'automaticUpload': False})
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        status = router.status()
        self.assertTrue(status['reconnectRequired'])
        self.assertEqual((status['telemetry']['configuredMode'], status['telemetry']['activeMode']), ('local', 'off'))
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())['status'], 'refused')
        reconnected = PluginRouter(self.home)
        self.assertEqual({s.config.telemetry for s in reconnected.services.values()}, {'local'})
        self.assertEqual(reconnected.status()['telemetry']['activeMode'], 'local')

    def test_local_consent_records_plugin_calls_as_mcp_surface(self):
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        store = self.base / 'telemetry'
        with patch.object(telemetry, 'default_directory', return_value=store):
            router = PluginRouter(self.home)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
            result = router.invoke('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': sample}, threading.Event())
            self.assertEqual(result['status'], 'ok')
            report = telemetry.Store().report()
        self.assertIn('mcp', json.dumps(report))
        self.assertIn('analyze-work', json.dumps(report))

    def router_refusals(self, router, identifier):
        """Every router-level refusal path; each must refuse before the service telemetry boundary."""
        from unittest.mock import patch
        from agent_braid import tooling_mcp as core
        sample = {'workspaceId': identifier, 'kind': 'aim', 'request': {}}
        out = {'unknown-workspace': router.invoke('analyze-work', dict(sample, workspaceId='not-registered'), threading.Event()),
               'malformed-arguments': router.invoke('analyze-work', ['not', 'an', 'object'], threading.Event()),
               'bootstrap-arguments': router.invoke('workspaces', {'x': 1}, threading.Event())}
        with router.admission:
            out['busy-admission'] = router.invoke('analyze-work', sample, threading.Event())
        with patch.object(core, 'MAX_INVENTORY_ARTIFACTS', 0):
            out['full-inventory'] = router.invoke('analyze-work', sample, threading.Event())
        return out

    def assert_router_refusals_write_no_telemetry(self, consent, stale):
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        if consent == 'local':
            preview = plan_setup(self.home, [], telemetry='local')
            apply(self.home, preview, preview['previewDigest'])
        store = self.base / 'telemetry'
        with patch.object(telemetry, 'default_directory', return_value=store):
            router = PluginRouter(self.home)
            self.assertEqual(router.status()['telemetry']['activeMode'], consent)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            refusals = self.router_refusals(router, identifier)
            if stale:
                self.rewrite(lambda v: dict(v, workspaces=[]))
                refusals['reconnect-required'] = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
                self.assertEqual(refusals['reconnect-required']['result'], {'code': RegistryStale.code})
            for cause, result in refusals.items():
                self.assertEqual(result['status'], 'refused', cause)
            self.assertFalse(store.exists(), 'a refusal created the telemetry store')
            self.assertEqual(telemetry.Store().report()['rows'], [])

    def test_router_refusals_write_no_telemetry_cell_with_consent_local(self):
        self.assert_router_refusals_write_no_telemetry('local', stale=True)

    def test_router_refusals_write_no_telemetry_with_consent_off(self):
        self.assert_router_refusals_write_no_telemetry('off', stale=True)

    def test_refusal_pin_can_fail_because_service_calls_are_counted(self):
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        with patch.object(telemetry, 'default_directory', return_value=self.base / 'telemetry'):
            router = PluginRouter(self.home)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            # A refusal that does reach the service boundary is counted, so the pin above is not vacuous.
            result = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
            self.assertEqual(result['status'], 'refused')
            rows = telemetry.Store().report()['rows']
        self.assertIn(('mcp', 'analyze-work', 'refused', 'calls', 1),
                      [(r['surface'], r['operation'], r['outcome'], r['metric'], r['count']) for r in rows])

    def test_v01_registry_serves_migration_status_without_workspaces(self):
        registry_tests.PluginRegistryTests.legacy_registry(self)
        router = PluginRouter(self.home)
        status = router.status()
        self.assertEqual(status['status'], 'migration-required')
        self.assertEqual(status['workspaces'], [])
        self.assertEqual(router.services, {})
        self.assertEqual(status['telemetry']['activeMode'], 'off')


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional mcp==2.3.0 SDK is unavailable")
class PluginSdkTests(unittest.IsolatedAsyncioTestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    async def test_actual_sdk_connection_preserves_both_protocols_and_workspace_resources(self):
        import sys
        from mcp import Client
        from mcp.shared.exceptions import MCPError
        from mcp.client.stdio import StdioServerParameters
        self.install()
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        root = Path(__file__).resolve().parents[1]
        sample = json.loads((root / 'examples/analysis/file-edits.json').read_text())
        for mode in ('auto', 'legacy'):
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'agent_braid', 'plugin', 'serve', '--home', str(self.home)], cwd=str(root))
            async with Client(params, mode=mode) as client:
                definitions = {tool.name: tool for tool in (await client.list_tools()).tools}
                names = set(definitions)
                self.assertEqual(names, {'plugin-status', 'workspaces', 'analyze-work', 'analyze', 'prepare'})
                response = await client.call_tool('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': sample})
                value = response.structured_content
                self.assertEqual(value['status'], 'ok')
                self.assertEqual(json.loads(response.content[0].text), value)
                import jsonschema
                jsonschema.validate(value, definitions['analyze-work'].output_schema)
                refused = await client.call_tool('analyze-work', {'workspaceId': 'unknown'})
                self.assertEqual(refused.structured_content['status'], 'refused')
                jsonschema.validate(refused.structured_content, definitions['analyze-work'].output_schema)
                uri = value['evidenceRefs'][0]['uri']
                data = await client.read_resource(uri)
                self.assertTrue(json.loads(data.contents[0].text)['firstChunkUri'].startswith('agent-braid-plugin://'))
                self.assertEqual((await client.list_resource_templates()).resource_templates, [])
                self.assertEqual(value['schemaVersion'], 'agent-braid-plugin/v0.2')
                self.assertEqual(refused.structured_content['schemaVersion'], 'agent-braid-plugin/v0.2')
                self.assertEqual(definitions['analyze-work'].output_schema['properties']['schemaVersion'], {'const': 'agent-braid-plugin/v0.2'})
                self.assertIsNone(client.server_capabilities.prompts)
                with self.assertRaisesRegex(MCPError, 'Method not found'):
                    await client.list_prompts()
                before = sorted(str(r.uri) for r in (await client.list_resources()).resources)
                with self.assertRaisesRegex(MCPError, 'Method not found'):
                    await client.get_prompt('agent-braid-analyze')
                after = sorted(str(r.uri) for r in (await client.list_resources()).resources)
                self.assertEqual(before, after)
                capabilities = json.loads((await client.read_resource(f'agent-braid-plugin://{identifier}/capabilities')).contents[0].text)
                self.assertNotIn('prompts', capabilities)
                self.assertTrue(capabilities['resources'])


class PluginPromptNegativeControlTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    def test_negative_control_shared_core_still_advertises_prompts_but_plugin_drops_them(self):
        from agent_braid import tooling_mcp as core
        self.install()
        service = next(iter(PluginRouter(self.home).services.values()))
        shared = core.ToolingService.capabilities(service)
        self.assertEqual(len(shared['prompts']), 3)  # the old v0.1 plugin behaviour: would fail the new assertion
        self.assertNotIn('prompts', service.capabilities())
        self.assertEqual(len(core._PROMPT_TEXT), 3)  # portable server keeps its prompts
