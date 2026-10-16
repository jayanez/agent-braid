# SPDX-License-Identifier: AGPL-3.0-only
import json
from pathlib import Path
import threading
import unittest
import importlib.util
from tests import test_plugin_registry as registry_tests
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import load, plan_setup, apply


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


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional mcp==2.3.0 SDK is unavailable")
class PluginSdkTests(unittest.IsolatedAsyncioTestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    async def test_actual_sdk_connection_preserves_both_protocols_and_workspace_resources(self):
        import sys
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        self.install()
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        root = Path(__file__).resolve().parents[1]
        sample = json.loads((root / 'examples/analysis/file-edits.json').read_text())
        for mode in ('auto', 'legacy'):
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'agent_braid', 'plugin', 'serve', '--home', str(self.home)], cwd=str(root))
            async with Client(params, mode=mode) as client:
                names = {x.name for x in (await client.list_tools()).tools}
                self.assertEqual(names, {'plugin-status', 'workspaces', 'analyze-work', 'analyze', 'prepare'})
                response = await client.call_tool('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': sample})
                value = response.structured_content
                self.assertEqual(value['status'], 'ok')
                self.assertEqual(json.loads(response.content[0].text), value)
                uri = value['evidenceRefs'][0]['uri']
                data = await client.read_resource(uri)
                self.assertTrue(json.loads(data.contents[0].text)['firstChunkUri'].startswith('agent-braid-plugin://'))
                self.assertEqual((await client.list_resource_templates()).resource_templates, [])
                self.assertEqual(len((await client.list_prompts()).prompts), 3)
                prompt = await client.get_prompt('agent-braid-evidence')
                self.assertIn('workspaceId', prompt.messages[0].content.text)
