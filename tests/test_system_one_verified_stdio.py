# SPDX-License-Identifier: AGPL-3.0-only
"""Real subprocess MCP client controls; parent native work retains one budget."""
from copy import deepcopy
from pathlib import Path
import os
import sys
import tempfile
import shutil
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_system_one_verified_selection as fixtures
from agent_braid import git_runtime, tooling_mcp
from agent_braid import system_one_verified_stdio as transport
from agent_braid.system_one import canonical, digest, thaw, CancellationToken


class VerifiedStdioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VerifiedSelectionTests.setUpClass()
        cls.fixture = fixtures.VerifiedSelectionTests.fixture
        cls.observations = []

    @classmethod
    def tearDownClass(cls):
        fixtures.VerifiedSelectionTests.tearDownClass()

    def setUp(self):
        self.builder = fixtures.VerifiedSelectionTests()
        self.builder.setUp()

    def context(self, lang='en', rep='controlled', request=None, **kw):
        return transport.StdioRequestContext(canonical(request or self.builder.request(lang, rep)),
                                             self.fixture.owned, **kw)

    @unittest.skipUnless(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file(),
                         'native network-denied stdio peer requires macOS sandbox-exec')
    def test_four_views_actual_stdio_full_body_and_shared_parent_budget(self):
        before = self.fixture.inventory()
        for lang in ('en', 'es'):
            for rep in ('controlled', 'symbolic'):
                with self.subTest(lang=lang, rep=rep), self.context(lang, rep) as context:
                    proposal = context.propose()
                    budget = context.context.git_budget
                    original_start = budget.started_at
                    actual = git_runtime.prepare_run
                    calls = []
                    def native(*args, **kw):
                        calls.append((os.getpid(), kw['budget']))
                        return actual(*args, **kw)
                    with patch.object(git_runtime, 'prepare_run', native):
                        result = context.consume(canonical(proposal))
                    self.assertEqual(result['status'], 'answered', thaw(result))
                    self.assertEqual(calls, [(os.getpid(), budget)])
                    self.assertEqual(result['consumerId'], 'mcp-stdio')
                    self.assertEqual(result['preparedDigest'], digest(context.prepared))
                    self.assertEqual(context.prepared['request'], proposal['runtimeRequest'])
                    self.assertEqual(budget.started_at, original_start)
                    self.assertEqual(result['usage']['gitCommands'], budget.commands)
                    receipt = context.transport_receipt
                    self.assertEqual(receipt['exitCode'], 0)
                    self.assertEqual(receipt['termination'], 'stopped')
                    self.assertTrue(receipt['networkDeniedByOS'])
                    self.assertTrue(receipt['completeBodyVerified'])
                    self.assertNotEqual(receipt['pid'], os.getpid())
                    self.assertEqual(receipt['childGitCommands'], 0)
                    self.assertGreaterEqual(receipt['resourceReads'], 2)
                    self.assertGreater(receipt['wireBytes'], 0)
                    self.assertEqual(result['counters']['consumerCalls'], 1)
                    self.assertEqual(result['usage']['termination'], 'stopped')
                    self.assertEqual(result['usage']['cleanup'], 'removed')
                    self.assertFalse(Path(context.prepared['runDirectory']).exists())
                    self.assertFalse(result['executionAuthorization'])
                    type(self).observations.append({'consumer': 'mcp-stdio', 'case': 'positive',
                        'language': lang, 'representation': rep, 'expected': 'answered',
                        'result': thaw(result), 'transport': deepcopy(receipt)})
        self.assertEqual(self.fixture.inventory(), before)

    def test_unsupported_platform_refuses_before_child_without_claiming_containment(self):
        with self.context() as context:
            proposal = context.propose()
            budget = context.context.git_budget
            before = budget.commands
            with tempfile.TemporaryDirectory(dir=budget.temp_root) as directory:
                dest = Path(directory) / 'unallocated'
                with patch.object(transport.sys, 'platform', 'linux'), context.context.phase('transportEvidence'):
                    with self.assertRaisesRegex(ValueError, 'transport-failure'):
                        transport.stdio_prepare(context.context, proposal['runtimeRequest'], dest)
                receipt = context.context._transport_receipt
                self.assertEqual(receipt['termination'], 'not-started')
                self.assertIsNone(receipt['exitCode'])
                self.assertNotIn('pid', receipt)
                self.assertFalse(receipt['networkDeniedByOS'])
                self.assertEqual(budget.commands, before)
                self.assertFalse(dest.exists())

    def test_defer_and_rehashed_cross_consumer_proposals_before_child(self):
        from agent_braid import system_one_verified_ir as ir
        for lang in ('en', 'es'):
            request = self.builder.request(lang)
            request['source']['task']['options'] = {'k0': [], 'k1': ['a', 'a'], 'k2': ['b'], 'wait': None}
            program = deepcopy(self.builder.program)
            program['plans'] = deepcopy(request['source']['task']['options'])
            request['interpretation'] = thaw(ir.render(program, lang, 'controlled', checkpoint=lambda *_: None))
            with self.context(request=request) as context, patch.object(transport, '_command', side_effect=AssertionError('child')):
                result = context.consume(canonical(context.propose()))
                self.assertEqual(result['status'], 'semantic-defer')
                self.assertEqual(result['counters']['nativeCalls'], 0)
                self.assertEqual(result['counters']['consumerCalls'], 0)
                type(self).observations.append({'consumer': 'mcp-stdio', 'case': 'defer', 'language': lang,
                    'representation': 'controlled', 'expected': 'semantic-defer', 'result': thaw(result)})
            with self.context(lang) as context:
                proposal = thaw(context.propose())
                proposal['consumerId'] = 'mcp-service'
                proposal['proposalDigest'] = digest({k: v for k, v in proposal.items() if k != 'proposalDigest'})
                with patch.object(transport, '_command', side_effect=AssertionError('child')):
                    result = context.consume(canonical(proposal))
                self.assertEqual(result['reasonCodes'], ('consumer-mismatch',))
                self.assertEqual(result['counters']['consumerCalls'], 0)
                type(self).observations.append({'consumer': 'mcp-stdio', 'case': 'wrong-recipient', 'language': lang,
                    'representation': 'controlled', 'expected': 'refused', 'result': thaw(result)})

    def test_real_child_malformed_frames_and_unexpected_calls_are_reaped(self):
        bad = [b'{"jsonrpc":"2.0","jsonrpc":"2.0"}\n',
               b'{"x":NaN}\n', b'{}\n', b'{"x":', b'x' * (1048576 + 1) + b'\n',
               canonical({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {}}) + b'\n',
               canonical({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'execute'}}) + b'\n']
        for index, raw in enumerate(bad):
            with self.subTest(index=index), self.context() as context:
                proposal = context.propose()
                budget = context.context.git_budget
                with tempfile.TemporaryDirectory(dir=budget.temp_root) as directory:
                    dest = Path(directory) / 'unallocated'
                    expression = "b'x' * 1048577 + b'\\n'" if len(raw) > 1048576 else repr(raw)
                    command = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write(' + expression + ');sys.stdout.flush()']
                    before = budget.commands
                    with patch.object(transport, '_command', return_value=command), context.context.phase('transportEvidence'):
                        with self.assertRaises(Exception):
                            transport.stdio_prepare(context.context, proposal['runtimeRequest'], dest)
                    self.assertEqual(budget.commands, before)
                    receipt = context.context._transport_receipt
                    self.assertEqual(receipt['termination'], 'stopped')
                    self.assertIsNotNone(receipt['exitCode'])
                    self.assertFalse(receipt['networkDeniedByOS'])
                    self.assertFalse(dest.exists())

    def test_stalled_child_cancelled_and_reaped_without_budget_reset(self):
        token = CancellationToken()
        with self.context(cancellation=token) as context:
            proposal = context.propose()
            budget = context.context.git_budget
            real_checkpoint = context.context.checkpoint
            def cancelled(stage, units):
                if getattr(context.context, '_transport_receipt', {}).get('pid'):
                    token.cancel()
                return real_checkpoint(stage, units)
            command = [sys.executable, '-c', 'import time;time.sleep(60)']
            before = budget.commands
            with tempfile.TemporaryDirectory(dir=budget.temp_root) as directory:
                with patch.object(transport, '_command', return_value=command), patch.object(context.context, 'checkpoint', cancelled):
                    with self.assertRaisesRegex(ValueError, 'cancelled'):
                        transport.stdio_prepare(context.context, proposal['runtimeRequest'], Path(directory) / 'dest')
            self.assertEqual(budget.commands, before)
            self.assertEqual(context.context._transport_receipt['termination'], 'stopped')

    def test_child_nonzero_exit_refuses_and_no_prepared_body(self):
        command = [sys.executable, '-c', 'raise SystemExit(7)']
        with self.context() as context, patch.object(transport, '_command', return_value=command):
            result = context.consume(canonical(context.propose()))
            self.assertEqual(result['status'], 'refused')
            self.assertIn('transport-failure', result['reasonCodes'])
            self.assertIsNone(context.prepared)
            self.assertEqual(context.transport_receipt['exitCode'], 7)
            self.assertEqual(context.transport_receipt['termination'], 'stopped')
            self.assertEqual(result['usage']['cleanup'], 'removed')

    def test_child_cannot_skip_chunk_protocol_even_with_valid_inline_body(self):
        # A real adversarial peer computes a matching digest from complete inline
        # evidence, but omits the required manifest/chunk exchange entirely.
        script = '''import json,sys
config=json.load(open(sys.argv[1]));identifier=0
def send(value):
 print(json.dumps(value,separators=(',',':')),flush=True)
def rpc(method,params):
 global identifier
 identifier+=1;send({'jsonrpc':'2.0','id':identifier,'method':method,'params':params})
 return json.loads(sys.stdin.readline())['result']
rpc('initialize',{'protocolVersion':'2025-11-25','capabilities':{},'clientInfo':{'name':'braid-verified-peer','version':'1'}})
send({'jsonrpc':'2.0','method':'notifications/initialized','params':{}})
rpc('tools/list',{})
reply=rpc('tools/call',{'name':'prepare','arguments':config['arguments']})['structuredContent']
ref=reply['evidenceRefs'][0]
send({'jsonrpc':'2.0','method':'notifications/verified-result','params':{'prepared':reply['result'],'requests':identifier,'resourceReads':0,'artifact':{'artifactSha256':ref['sha256'],'bytes':ref['sizeBytes'],'chunks':1},'gitCommands':0}})
'''
        def command(path, _sha):
            return [sys.executable, '-c', script, str(path)]
        with self.context() as context, patch.object(transport, '_command', command):
            result = context.consume(canonical(context.propose()))
            self.assertEqual(result['status'], 'refused')
            self.assertIn('transport-failure', result['reasonCodes'])
            self.assertIsNone(context.prepared)
            self.assertEqual(context.transport_receipt['resourceReads'], 0)
            self.assertEqual(context.transport_receipt['termination'], 'stopped')

    @unittest.skipUnless(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file(),
                         'native network-denied stdio peer requires macOS sandbox-exec')
    def test_native_cancel_late_result_suppressed_and_child_reaped(self):
        token = CancellationToken()
        actual = git_runtime.prepare_run
        def cancelled(*args, **kw):
            value = actual(*args, **kw)
            token.cancel()
            return value
        with self.context(cancellation=token) as context, patch.object(git_runtime, 'prepare_run', cancelled):
            result = context.consume(canonical(context.propose()))
            self.assertEqual(result['status'], 'refused')
            self.assertIn('cancelled', result['reasonCodes'])
            self.assertIsNone(context.prepared)
            self.assertEqual(context.transport_receipt['termination'], 'stopped')
            self.assertEqual(result['usage']['cleanup'], 'removed')

    def test_transport_frame_encoder_limits_and_no_default_catalog_change(self):
        from agent_braid import mcp_runtime
        self.assertEqual(mcp_runtime.TOOLS, ('analyze', 'prepare', 'status', 'execute', 'recover', 'verify'))
        self.assertEqual(transport._frame({'a': 'español'}), canonical({'a': 'español'}) + b'\n')
        with self.assertRaises(ValueError):
            transport._frame({'a': 'x' * 1048576})
        with self.assertRaises(ValueError):
            transport._frame({'a': float('inf')})

    def test_unknown_owned_worker_preserves_scratch_and_admission(self):
        token = CancellationToken()
        with self.context(cancellation=token) as context:
            context.propose()
            scratch = context.context.git_budget.temp_root
            # A controlled unknown-resource state; no actual child is abandoned.
            context.context._owned_processes.append(SimpleNamespace(poll=lambda: None))
            context.context._transport_receipt = {'termination': 'unknown'}
            context._failure = 'transport-failure'
            context.context._fail('internal-failure')
            result = context.context.seal(context._record)
            self.assertEqual(result['status'], 'refused')
            self.assertEqual(result['usage']['termination'], 'unknown')
            self.assertIn('termination-unknown', result['reasonCodes'])
            self.assertIn('cleanup-failed', result['reasonCodes'])
            self.assertEqual([row['outcome'] for row in result['usage']['stages'] if row['name'] == 'cleanup'], ['refused'])
            self.assertTrue(scratch.exists())
            with self.assertRaises(ValueError):
                token.claim()
            # The fixture has no worker. Explicitly dispose its retained resources;
            # the immutable unknown result is not retroactively promoted to success.
            context.context._owned_processes.clear()
            shutil.rmtree(scratch)
            context.context._remove_waker()
            context.context._remove_waker = None
            token.release()
            context.context._claimed = False


if __name__ == '__main__':
    unittest.main()
