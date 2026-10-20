# SPDX-License-Identifier: AGPL-3.0-only
"""Software fixtures and real optional-SDK transport; no model/native-host call."""
import asyncio
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from agent_braid import system_one_verified_mcp as endpoint
from agent_braid import system_one_verified_ir as ir
from agent_braid.system_one import CancellationToken, canonical, digest, thaw
import test_system_one_verified_selection as selection_fixtures


class _Fixtures:
    @classmethod
    def setUpClass(cls):
        cls.builder = selection_fixtures.VerifiedSelectionTests
        cls.builder.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.builder.tearDownClass()

    def request(self, language='en', kind='answered'):
        builder = self.builder()
        builder.setUp()
        request = builder.request(language)
        program = deepcopy(builder.program)
        if kind == 'semantic-defer':
            options = {'k0': ['a', 'a'], 'k1': [], 'k2': ['b'], 'wait': None}
            request['source']['task']['options'] = options
            program['plans'] = options
        elif kind == 'k0-invalid':
            request['source']['task']['options']['k0'] = ['a', 'a']
            program['plans']['k0'] = ['a', 'a']
        request['interpretation'] = thaw(ir.render(program, language, 'controlled', checkpoint=lambda *_: None))
        if kind == 'refused':
            request['source']['declaredEffects']['a'][0]['after'] = '1' * 40
        return request

    @property
    def root(self):
        return self.builder.fixture.owned

    def verify_bundle(self, body, status):
        self.assertEqual(body['format'], endpoint.FORMAT)
        self.assertEqual(body['status'], status)
        self.assertIs(body['executionAuthorization'], False)
        self.assertEqual(set(body['bodies']), set(endpoint._BODY_KEYS))
        for name, value in body['bodies'].items():
            self.assertEqual(body['bodyDigests'][name], digest(value) if value is not None else None)
        bodies = body['bodies']
        result = bodies['consumerResult']
        self.assertEqual(result['status'], status)
        self.assertIs(result['executionAuthorization'], False)
        self.assertEqual(result['usage']['cleanup'], 'removed' if result['usage']['gitCommands'] else 'not-allocated')
        self.assertEqual(result['usage']['termination'], 'stopped')
        for name in ('executeCalls', 'recoverCalls', 'grantWrites', 'persistentRunAllocations'):
            self.assertEqual(result['counters'][name], 0)
        if bodies['proposal'] is not None:
            proposal = bodies['proposal']
            self.assertEqual(proposal['decision'], bodies['producerDecision'])
            self.assertEqual(result['decisionDigest'], digest(bodies['producerDecision']))
            self.assertEqual(result['proposalDigest'], proposal['proposalDigest'])
            self.assertEqual(proposal['proposalDigest'], digest({k: v for k, v in proposal.items()
                                                               if k != 'proposalDigest'}))
            evidence = bodies['producerEvidence']
            self.assertEqual(proposal['snapshot'], evidence['snapshot'])
            for ref in bodies['producerDecision']['evidenceRefs']:
                actual = {'snapshot': evidence['snapshot'], 'interpretation': evidence['interpretation'],
                          'verifier-result': evidence['verifierResult']}[ref['kind']]
                self.assertEqual(ref['digest'], digest(actual))
        if status == 'answered':
            self.assertEqual(result['preparedDigest'], digest(bodies['prepared']))
            self.assertTrue(result['evidence']['preparedBodyChecked'])
        else:
            self.assertIsNone(bodies['prepared'])


class VerifiedEndpointCoreTests(_Fixtures, unittest.TestCase):
    def test_complete_bound_bodies_en_es_and_same_immutable_producer(self):
        before = self.builder.fixture.inventory()
        for language in ('en', 'es'):
            response = endpoint.prepare_bundle(canonical(self.request(language)), self.root)
            self.verify_bundle(response, 'answered')
            self.assertEqual(response['bodies']['producerDecision']['selectedOptionId'], 'k0')
            self.assertGreater(response['bodies']['consumerResult']['usage']['gitCommands'], 0)
            with self.assertRaises(TypeError):
                response['bodies']['producerDecision']['status'] = 'refused'
        self.assertEqual(self.builder.fixture.inventory(), before)

    def test_correct_defer_and_k0_invalid_en_es(self):
        for language in ('en', 'es'):
            response = endpoint.prepare_bundle(canonical(self.request(language, 'semantic-defer')), self.root)
            self.verify_bundle(response, 'semantic-defer')
            self.assertEqual(response['reasonCodes'], ('no-goal-reaching-plan',))
            self.assertEqual(response['bodies']['consumerResult']['counters']['nativeCalls'], 0)
            response = endpoint.prepare_bundle(canonical(self.request(language, 'k0-invalid')), self.root)
            self.verify_bundle(response, 'answered')
            self.assertEqual(response['bodies']['producerDecision']['selectedOptionId'], 'k1')

    def test_raw_rejection_preserves_exact_reason_without_allocating(self):
        good = canonical(self.request())
        cases = [b'{}', b'{"format":"duplicate",' + good[1:],
                 good[:-1] + b',"extra":0}', b'{"format":NaN}', b'x' * (1024 * 1024 + 1)]
        for raw in cases:
            response = endpoint.prepare_bundle(raw, self.root)
            self.assertEqual(response['status'], 'refused')
            self.assertIsNone(response['bodies']['proposal'])
            self.assertIsNone(response['bodies']['consumerResult']['usage']['gitCommands'])
            self.assertEqual(response['bodies']['consumerResult']['usage']['cleanup'], 'not-allocated')
            self.assertEqual(response['reasonCodes'], response['bodies']['producerDecision']['reasonCodes'])
        response = endpoint.prepare_bundle(canonical(self.request(kind='refused')), self.root)
        self.assertEqual(response['reasonCodes'], ('declaration-mismatch',))

    def test_cancelled_token_and_response_cap_never_expose_success(self):
        token = CancellationToken()
        token.cancel()
        response = endpoint.prepare_bundle(canonical(self.request()), self.root, cancellation=token)
        self.assertEqual(response['status'], 'refused')
        self.assertEqual(response['reasonCodes'], ('cancelled',))
        with patch.object(endpoint, 'MAX_RESPONSE_BYTES', 4096):
            response = endpoint.prepare_bundle(canonical(self.request()), self.root)
        self.assertEqual(response['reasonCodes'], ('response-budget-exceeded',))
        self.assertTrue(all(v is None for v in response['bodies'].values()))

    def test_untrusted_root_and_arguments_are_not_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            alias = Path(directory) / 'alias'
            alias.symlink_to(self.root)
            for root in (alias, Path('relative'), Path(directory) / 'missing'):
                with self.assertRaisesRegex(ValueError, '^invalid-owned-root$'):
                    endpoint.prepare_bundle(b'{}', root)
        for value in ({}, {'requestJson': '{}', 'ownedRoot': str(self.root)}, {'requestJson': {}},
                      {'requestJson': '\ud800'}):
            with self.assertRaises(ValueError):
                endpoint._arguments(value)

    def test_import_is_lazy_without_sdk_or_neural_imports(self):
        result = subprocess.run([sys.executable, '-c',
            "import sys;from agent_braid import system_one_verified_mcp;"
            "assert not any(n=='mcp' or n.startswith('mcp.') or n=='torch' or n.startswith('torch.') "
            "or n=='transformers' or n.startswith('transformers.') for n in sys.modules)"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(importlib.util.find_spec('mcp') is not None, 'optional pinned MCP SDK unavailable')
class VerifiedEndpointSDKTests(_Fixtures, unittest.TestCase):
    def test_real_sdk_stdio_en_es_complete_results_and_repeat_calls(self):
        from mcp.client.session import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        async def run():
            import mcp.client.stdio as stdio_module
            source = Path(__file__).resolve().parents[1]
            env = {'PATH': os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1',
                   'GIT_ALLOW_PROTOCOL': 'file'}
            # Source lane during development; installed capture overrides this
            # module's external-controller root through the trusted environment.
            package_path = os.environ.get('VERIFIED_ENDPOINT_PACKAGE_PATH', str(source))
            if package_path:
                env['PYTHONPATH'] = package_path
            params = StdioServerParameters(command='/usr/bin/sandbox-exec',
                args=['-p', '(version 1)(allow default)(deny network*)', sys.executable,
                      '-m', 'agent_braid.system_one_verified_mcp', '--owned-root', str(self.root)],
                env=env, cwd=os.environ.get('VERIFIED_ENDPOINT_CWD', str(source)))
            records = []
            processes = []
            spawn = stdio_module._create_platform_compatible_process
            async def capture_spawn(**kwargs):
                process = await spawn(**kwargs)
                processes.append(process)
                return process
            patcher = patch.object(stdio_module, '_create_platform_compatible_process', capture_spawn)
            patcher.start()
            self.addCleanup(patcher.stop)
            async with stdio_client(params) as streams:
                async with ClientSession(*streams) as session:
                    initialized = await session.initialize()
                    tools = await session.list_tools()
                    self.assertEqual([t.name for t in tools.tools], [endpoint.TOOL_NAME])
                    for language in ('en', 'es'):
                        for kind in ('answered', 'semantic-defer', 'refused', 'k0-invalid'):
                            raw = canonical(self.request(language, kind)).decode()
                            result = await session.call_tool(endpoint.TOOL_NAME, {'requestJson': raw})
                            body = result.model_dump(by_alias=True)['structuredContent']
                            status = 'answered' if kind == 'k0-invalid' else kind
                            self.verify_bundle(body, status)
                            self.assertEqual(json.loads(result.content[0].text), body)
                            if kind == 'k0-invalid':
                                self.assertEqual(body['bodies']['producerDecision']['selectedOptionId'], 'k1')
                            records.append({'language': language, 'kind': kind, 'requestJson': raw,
                                            'result': result.model_dump(by_alias=True)})
                    for raw in ('{}', '{"a":1,"a":2}', '{"a":NaN}'):
                        result = await session.call_tool(endpoint.TOOL_NAME, {'requestJson': raw})
                        body = result.model_dump(by_alias=True)['structuredContent']
                        self.assertEqual(body['status'], 'refused')
                        self.assertIsNone(body['bodies']['consumerResult']['usage']['gitCommands'])
            self.assertEqual(len(processes), 1)
            self.assertEqual(processes[0].returncode, 0)
            if os.environ.get('VERIFIED_ENDPOINT_CAPTURE'):
                Path(os.environ['VERIFIED_ENDPOINT_CAPTURE']).write_text(json.dumps({
                    'initialize': initialized.model_dump(by_alias=True),
                    'tools': tools.model_dump(by_alias=True), 'controls': records,
                    'serverChild': {'pid': processes[0].pid, 'returnCode': processes[0].returncode,
                                    'reaped': True}}, indent=2) + '\n')
        before = self.builder.fixture.inventory()
        asyncio.run(run())
        self.assertEqual(self.builder.fixture.inventory(), before)

    def test_registered_handler_cancellation_timeout_and_busy_wait_for_worker(self):
        import mcp.types as types

        async def run(timeout):
            started, cancelled, release, finished = (threading.Event() for _ in range(4))
            def worker(raw, root, *, cancellation):
                started.set()
                while not cancellation.cancelled:
                    release.wait(0.002)
                cancelled.set()
                release.wait(5)
                finished.set()
                return endpoint._envelope('refused', ['cancelled'])
            server = endpoint.create_server(self.root)
            handler = server.get_request_handler('tools/call').handler
            params = types.CallToolRequestParams(name=endpoint.TOOL_NAME, arguments={'requestJson': '{}'})
            with patch.object(endpoint, 'prepare_bundle', worker), patch.object(
                    endpoint, 'CALL_TIMEOUT_SECONDS', 0.02 if timeout else 5):
                task = asyncio.create_task(handler(None, params))
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                other = await handler(None, params)
                self.assertEqual(other.model_dump(by_alias=True)['structuredContent']['reasonCodes'],
                                 ['concurrent-request'])
                if not timeout:
                    task.cancel()
                self.assertTrue(await asyncio.to_thread(cancelled.wait, 2))
                self.assertFalse(task.done())
                self.assertFalse(finished.is_set())
                release.set()
                if timeout:
                    body = (await task).model_dump(by_alias=True)['structuredContent']
                    self.assertEqual(body['reasonCodes'], ['endpoint-deadline-exceeded'])
                else:
                    with self.assertRaises(asyncio.CancelledError):
                        await task
                self.assertTrue(finished.is_set())
            # The same server accepts a later independent request after cleanup.
            result = await handler(None, params)
            self.assertEqual(result.model_dump(by_alias=True)['structuredContent']['status'], 'refused')
        asyncio.run(run(False))
        asyncio.run(run(True))

    def test_outer_wire_validation_rejects_duplicate_nonfinite_and_depth(self):
        from agent_braid.tooling_mcp import _BoundedInput
        import io
        async def run():
            for raw in (b'{"id":1,"id":2}\n', b'{"id":NaN}\n',
                        b'[' * 100 + b'0' + b']' * 100 + b'\n'):
                bounded = _BoundedInput(io.BytesIO(raw))
                self.assertEqual(await anext(bounded), '{\n')
        asyncio.run(run())

    def test_encoding_cannot_publish_a_result_after_sdk_deadline(self):
        import mcp.types as types
        async def run():
            handler = endpoint.create_server(self.root).get_request_handler('tools/call').handler
            original = endpoint.canonical
            def slow(value):
                time.sleep(0.03)
                return original(value)
            with patch.object(endpoint, 'prepare_bundle', return_value=endpoint._envelope('refused', ['test-marker'])), \
                    patch.object(endpoint, 'CALL_TIMEOUT_SECONDS', 0.01), patch.object(endpoint, 'canonical', slow):
                result = await handler(None, types.CallToolRequestParams(
                    name=endpoint.TOOL_NAME, arguments={'requestJson': '{}'}))
            self.assertEqual(result.model_dump(by_alias=True)['structuredContent']['reasonCodes'],
                             ['endpoint-deadline-exceeded'])
        asyncio.run(run())
