# SPDX-License-Identifier: AGPL-3.0-only
import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

HAVE_MCP = importlib.util.find_spec('mcp') is not None

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'reproduce_native_plugin.py'
spec = importlib.util.spec_from_file_location('reproduce_native_plugin', SCRIPT)
script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(script)


class StubClient:
    def __init__(self, prompts, error=None):
        self.server_capabilities = SimpleNamespace(prompts=prompts)
        self.error = error

    async def list_prompts(self):
        if self.error:
            raise self.error
        return SimpleNamespace(prompts=[])


@unittest.skipUnless(HAVE_MCP, 'optional mcp==2.3.0 SDK is unavailable')
class PromptsAbsentTests(unittest.TestCase):
    def test_absent_capability_with_method_not_found_passes(self):
        from mcp.shared.exceptions import MCPError
        client = StubClient(None, MCPError(-32601, 'Method not found'))
        self.assertEqual(asyncio.run(script.assert_prompts_absent(client)), 'absent')

    def test_advertised_prompts_fail(self):
        with self.assertRaises(AssertionError):
            asyncio.run(script.assert_prompts_absent(StubClient(SimpleNamespace(listChanged=False))))

    def test_list_prompts_succeeding_without_capability_fails(self):
        with self.assertRaises(AssertionError):
            asyncio.run(script.assert_prompts_absent(StubClient(None)))

    def test_other_errors_fail(self):
        from mcp.shared.exceptions import MCPError
        with self.assertRaises(AssertionError):
            asyncio.run(script.assert_prompts_absent(StubClient(None, MCPError(-32603, 'boom'))))


if __name__ == '__main__':
    unittest.main()
