# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded transport ownership, wire-size and deterministic cancellation controls."""
from dataclasses import replace
from copy import deepcopy
import io
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from agent_braid.system_one import CancellationToken, canonical, digest, thaw
from agent_braid import mcp_advice as m
from agent_braid import system_one_advisors as advisors
from agent_braid._advice_scope import (_TransportScopeRegistry, _Ingress,
    InvalidAdviceScope, validate_for_stage, _scope_checkpoint)

ROOT=Path(__file__).resolve().parents[1]


def manifest():
    # A source-consistency test fixture, not an installed capability claim.
    return {'version':'s1-stage-registry-v1','stages':list(advisors.STAGES),
        'rules':[{'stage':s,'ruleId':r,'implementationSourceDigest':'0'*64}
                 for s,r in zip(advisors.STAGES,advisors.RULES)],
        'inventory':{'entries':[],'sources':[]}}


def stage_request(stage='triage',payload=None):
    context={'sourceKind':'synthetic','generation':4,
             'operations':json.loads((ROOT/'examples/analysis/file-edits.json').read_text())['operations']}
    return {'contractVersion':'s1-stage-advice-v1','requestId':'original-stage',
        'context':context,'contextDigest':digest(context),'registryDigest':digest(manifest()),
        'stage':stage,'payload':payload or {'caseIds':['x'],
            'categories':[{'caseId':'x','category':'unknown'}]},
        'budgets':{'maxInputBytes':1048576,'maxCandidates':64,'deadlineMs':5000}}


def invoke(value):
    return advisors.advise_stage(canonical(value),expected_context_digest=value['contextDigest'],
        expected_registry_digest=value['registryDigest'])


class SystemOneScopeTests(unittest.TestCase):
    def setUp(self):
        self.now=[100]
        self.registry=_TransportScopeRegistry(clock=lambda:self.now[0])
        self.value=stage_request()
    def scope(self,identifier=1):
        return self.registry.admit(self.registry.begin_ingress(),identifier,canonical(self.value),
            expected_context_digest=self.value['contextDigest'],expected_registry_digest=self.value['registryDigest'])
    def test_original_digest_token_single_claim_frozen_and_exact_release(self):
        scope=self.scope(); view=validate_for_stage(scope)
        self.assertEqual(view.request_bytes,canonical(self.value));self.assertEqual(view.request_digest,digest(self.value))
        self.assertEqual(view.deadline_ns,100+5_000_000_000)
        with self.assertRaises(ValueError): scope.cancellation.claim()
        with self.assertRaises(Exception): scope.deadline_ns=1
        self.assertTrue(self.registry.complete(scope));self.assertFalse(self.registry.complete(scope))
        self.assertFalse(scope.cancellation._in_use)
        with self.assertRaises(InvalidAdviceScope):validate_for_stage(scope)
    def test_forged_copied_owner_digest_future_reuse_scopes_no_dispatch(self):
        scope=self.scope()
        for forged in [replace(scope),replace(scope,owner=object()),replace(scope,request_digest='0'*64),
                       replace(scope,ingress_started_ns=10**20),object()]:
            with self.assertRaises(InvalidAdviceScope):validate_for_stage(forged)
            self.assertEqual(_scope_checkpoint(forged),'invalid-scope')
            self.assertFalse(self.registry.publish(forged,lambda:self.fail('forged writer')))
        self.assertFalse(self.registry.complete(replace(scope)))
        with self.assertRaises(InvalidAdviceScope):
            self.registry.admit(_Ingress(self.registry,10**20),2,canonical(self.value),
                expected_context_digest=self.value['contextDigest'],expected_registry_digest=self.value['registryDigest'])
        self.registry.complete(scope)
        self.assertFalse(self.registry.publish(scope,lambda:self.fail('reused writer')))
    def test_typed_ids_cancel_is_request_local_and_completed_id_reuse(self):
        one=self.scope(1); text=self.scope('1')
        self.registry.cancel(1);self.assertEqual(_scope_checkpoint(one),'cancelled')
        self.assertEqual(_scope_checkpoint(text),'live');self.registry.complete(one)
        replacement=self.scope(1);self.assertEqual(_scope_checkpoint(replacement),'live')
        self.registry.complete(replacement);self.registry.complete(text)
    def test_queue_deadline_original_shortening_and_both_publication_sides(self):
        self.value['budgets']['deadlineMs']=1;scope=self.scope()
        self.now[0]+=1_000_000
        self.assertEqual(_scope_checkpoint(scope),'deadline-exceeded')
        self.assertFalse(self.registry.publish(scope,lambda:self.fail('expired writer')))
        self.registry.complete(scope);self.now[0]=100
        before=self.scope();before.cancellation.cancel()
        self.assertFalse(self.registry.publish(before,lambda:self.fail('cancelled writer')))
        self.registry.complete(before);after=self.scope();written=[]
        self.assertTrue(self.registry.publish(after,lambda:(written.append('one'),after.cancellation.cancel())))
        self.assertEqual(written,['one']);self.assertFalse(self.registry.publish(after,lambda:written.append('two')))
        self.assertTrue(self.registry.complete(after));self.assertFalse(self.registry.complete(after))
    def test_write_failure_releases_scope_once_by_transport_cleanup(self):
        scope=self.scope()
        def broken():raise BrokenPipeError()
        try:
            with self.assertRaises(BrokenPipeError):self.registry.publish(scope,broken)
        finally:self.assertTrue(self.registry.complete(scope))
        self.assertFalse(scope.cancellation._in_use)


class SystemOneMcpTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(advisors,'_installed_manifest',return_value=manifest());self.patch.start();self.addCleanup(self.patch.stop)
        self.output=io.BytesIO();self.server=m.AdviceStdioServer(self.output);self.addCleanup(self.server.close)
    def send(self,method,identifier=None,params=None,notification=False):
        frame={'jsonrpc':'2.0','method':method,'params':{} if params is None else params}
        if not notification:frame['id']=identifier
        self.server.receive(canonical(frame))
    def initialize(self):
        self.send('initialize',0,{'protocolVersion':m.PROTOCOL,'capabilities':{},'clientInfo':{'name':'test','version':'1'}})
        self.send('notifications/initialized',notification=True)
        self.output.seek(0);self.output.truncate()
    def call(self,identifier,value=None):
        value=stage_request() if value is None else value
        self.send('tools/call',identifier,{'name':'s1_advise_stage','arguments':{
            'request':value,'expectedContextDigest':value['contextDigest'],
            'expectedRegistryDigest':value['registryDigest']}})
    def frames(self):
        return [json.loads(line) for line in self.output.getvalue().splitlines()]
    def test_initialize_protocol_catalog_and_no_execution_aliases(self):
        self.send('initialize',0,{'protocolVersion':'old','capabilities':{},'clientInfo':{'name':'x','version':'1'}})
        self.assertEqual(self.frames()[0]['error']['code'],-32602)
        self.output.seek(0);self.output.truncate();self.initialize();self.send('tools/list',1)
        tools=self.frames()[0]['result']['tools'];self.assertEqual([x['name'] for x in tools],list(m.TOOLS))
        for tool in tools:
            self.assertTrue(tool['annotations']['readOnlyHint']);self.assertFalse(tool['inputSchema']['additionalProperties']);self.assertFalse(tool['outputSchema']['additionalProperties'])
        for name in ['execute','prepare','recover','grant','s1_advise_stage_alias']:
            self.send('tools/call',name,{'name':name,'arguments':{}})
        self.send('ping',8);self.assertEqual(self.frames()[-1]['error']['code'],-32601)
        from agent_braid import mcp_runtime
        self.assertEqual(mcp_runtime.TOOLS,('analyze','prepare','status','execute','recover','verify'))
    def test_valid_stage_original_binding_text_structured_and_capabilities(self):
        self.initialize();value=stage_request();self.call(1,value);self.assertTrue(self.server.wait_idle())
        frame=self.frames()[0];result=frame['result'];packet=result['structuredContent']
        self.assertEqual(json.loads(result['content'][0]['text']),packet)
        self.assertEqual(packet['requestDigest'],digest(value));self.assertEqual(packet['status'],'advised')
        self.assertFalse(packet['executionAuthorization']);self.assertFalse(result['isError'])
        self.send('tools/call',2,{'name':'s1_advice_capabilities','arguments':{}});self.server.wait_idle()
        self.assertFalse(self.frames()[-1]['result']['structuredContent']['executionAuthorization'])
    def test_invalid_json_envelope_ids_extra_params_sanitized(self):
        self.initialize()
        for raw in [b'{"jsonrpc":"2.0","jsonrpc":"2.0"}',b'{"x":NaN}',b'private-sentinel',b' '*1048577]:
            self.server.receive(raw);self.assertEqual(self.frames()[-1]['error']['code'],-32700)
        for identifier in [True,None,'x'*65,1.5]:
            self.send('tools/list',identifier);self.assertEqual(self.frames()[-1]['error']['code'],-32600)
        self.send('tools/call',1,{'name':'s1_advice_capabilities','arguments':{},'private':'SENTINEL'})
        self.assertEqual(self.frames()[-1]['error']['code'],-32602)
        self.assertNotIn('SENTINEL',self.output.getvalue().decode())
    def test_full_jsonrpc_duplication_overflow_is_complete_refusal(self):
        self.initialize();value={'status':'advised','large':'a'*600000}
        raw=self.server._encoded(1,value);self.assertLessEqual(len(raw)-1,1048576)
        result=json.loads(raw)['result'];self.assertTrue(result['isError'])
        self.assertEqual(result['structuredContent']['reasonCodes'],['stage-budget-exceeded'])
        self.assertEqual(json.loads(result['content'][0]['text']),result['structuredContent'])
    def test_queue_max8_duplicate_ids_and_cancelled_waiter_never_runs(self):
        self.initialize();started=threading.Event();release=threading.Event();calls=[]
        original=self.server.tools.advise
        def held(scope):
            calls.append(scope.request_id[1])
            if scope.request_id[1]==1:started.set();self.assertTrue(release.wait(5))
            return original(scope)
        self.server.tools.advise=held
        self.call(1);self.assertTrue(started.wait(5))
        for number in range(2,10):self.call(number)
        self.call(10);overflow=self.frames()[-1]['result']['structuredContent'];self.assertEqual(overflow['reasonCodes'],['overloaded'])
        self.assertEqual(overflow['requestDigest'],digest(stage_request()))
        advisors.validate_stage_packet(overflow,request_bytes=canonical(stage_request()),expected_context_digest=stage_request()['contextDigest'],expected_registry_digest=stage_request()['registryDigest'])
        self.call(1);self.assertEqual(self.frames()[-1]['error']['code'],-32600)
        self.send('tools/list',1);self.assertEqual(self.frames()[-1]['error']['code'],-32600)
        self.send('notifications/cancelled',notification=True,params={'requestId':2,'reason':'PRIVATE-REASON'})
        release.set();self.assertTrue(self.server.wait_idle())
        self.assertNotIn(2,calls);self.assertNotIn(2,[f['id'] for f in self.frames()]);self.assertNotIn('PRIVATE-REASON',self.output.getvalue().decode())
    def test_output_lock_wait_expiry_and_cancel_prevent_late_write(self):
        self.initialize();now=[0];self.server.close();self.output=io.BytesIO()
        self.server=m.AdviceStdioServer(self.output,_clock=lambda:now[0]);self.initialize()
        entered=threading.Event();original=self.server._encoded
        def serialized(*args):entered.set();return original(*args)
        self.server._encoded=serialized;self.server._output_lock.acquire()
        self.call(1);self.assertTrue(entered.wait(5));now[0]=5_000_000_000
        self.server._registry.cancel(1);self.server._output_lock.release()
        self.assertTrue(self.server.wait_idle());self.assertEqual(self.output.getvalue(),b'')
    def test_publication_wins_before_later_cancel_exactly_one_result(self):
        self.initialize()
        original=self.server._write_bytes
        def after_boundary(raw):
            self.server._registry.cancel(1)
            original(raw)
        self.server._write_bytes=after_boundary
        self.call(1);self.assertTrue(self.server.wait_idle())
        self.assertEqual(len(self.frames()),1)
        self.assertEqual(self.frames()[0]['result']['structuredContent']['status'],'advised')
        self.assertEqual(self.server._registry._records,{})
    def test_shutdown_write_failure_cleanup_and_no_external_dispatch(self):
        self.initialize();value=stage_request()
        with patch('subprocess.run',side_effect=AssertionError('external')),patch('socket.create_connection',side_effect=AssertionError('external')):
            self.call(1,value);self.assertTrue(self.server.wait_idle())
        self.output.seek(0);self.output.truncate()
        def broken(_raw):raise BrokenPipeError()
        self.server._write_bytes=broken
        self.call(2,value);self.assertTrue(self.server.wait_idle())
        self.assertTrue(self.server.closed);self.assertEqual(self.server._registry._records,{})
        self.assertEqual(self.output.getvalue(),b'')
    def test_advertised_schemas_validate_packets_and_reject_payload_extensions(self):
        import jsonschema
        tool=m.advice_tool_catalog()[1]
        value=stage_request();arguments={'request':value,'expectedContextDigest':value['contextDigest'],'expectedRegistryDigest':value['registryDigest']}
        jsonschema.Draft202012Validator(tool['inputSchema']).validate(arguments)
        jsonschema.Draft202012Validator(tool['outputSchema']).validate(thaw(invoke(value)))
        arguments['request']['payload']['private']='SENTINEL'
        with self.assertRaises(jsonschema.ValidationError):jsonschema.Draft202012Validator(tool['inputSchema']).validate(arguments)
    def test_reader_bounded_line_admission_and_following_frame(self):
        self.initialize();source=io.BytesIO(b'a'*(1048576+2)+b'\n'+canonical({'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}})+b'\n')
        self.server.serve(source);self.assertEqual(self.frames()[0]['error']['code'],-32700)
        self.assertEqual(len(self.frames()[1]['result']['tools']),2)

if __name__=='__main__':unittest.main()
