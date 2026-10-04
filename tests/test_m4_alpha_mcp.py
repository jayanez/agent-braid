# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned stdio transport controls and real owned Git policy round trips."""
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from agent_braid import mcp_runtime as mcp, runtime_policy as policy, git_runtime
from tests import test_git_runtime as fixtures

ROOT=Path(__file__).resolve().parents[1]


class Peer:
    def __init__(self, source, results, grants, code=None):
        command=([sys.executable,'-c',code] if code else [sys.executable,'-m','agent_braid.mcp_runtime'])
        command += ['--source-root',str(source),'--result-parent',str(results),'--grant-store',str(grants)]
        self.process=subprocess.Popen(command,cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,start_new_session=True)
        self.responses=queue.Queue();self.identifier=0
        def read():
            for line in self.process.stdout:
                self.responses.put(json.loads(line))
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
    def send(self, value):
        self.process.stdin.write((json.dumps(value)+'\n').encode());self.process.stdin.flush()
    def rpc(self, method, params=None, timeout=180):
        self.identifier+=1;identifier=self.identifier
        self.send({'jsonrpc':'2.0','id':identifier,'method':method,'params':params or {}})
        result=self.responses.get(timeout=timeout)
        if result.get('id') != identifier: raise AssertionError(result)
        return result
    def initialize(self):
        result=self.rpc('initialize',{'protocolVersion':mcp.PROTOCOL,'capabilities':{},
                                    'clientInfo':{'name':'owned-test-peer','version':'1'}})
        self.send({'jsonrpc':'2.0','method':'notifications/initialized'})
        return result
    def tool(self, name, args):
        return self.rpc('tools/call',{'name':name,'arguments':args})['result']
    def close(self):
        if self.process.stdin and not self.process.stdin.closed:self.process.stdin.close()
        try:self.process.wait(timeout=130)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid,9);self.process.wait(timeout=5)
        self.process.stdout.close();self.reader.join(timeout=5)


class ProtocolTests(unittest.TestCase):
    def serve(self, frames):
        output=io.BytesIO();server=mcp.StdioServer(None,output)
        server.serve(io.BytesIO(frames))
        return [json.loads(line) for line in output.getvalue().splitlines()]
    def frame(self, value):return (json.dumps(value)+'\n').encode()
    def init(self, identifier=1, version=mcp.PROTOCOL):
        return {'jsonrpc':'2.0','id':identifier,'method':'initialize',
                'params':{'protocolVersion':version,'capabilities':{},'clientInfo':{'name':'peer','version':'1'}}}
    def test_pinned_lifecycle_catalog_and_no_authorization_tool(self):
        frames=[self.init(),{'jsonrpc':'2.0','method':'notifications/initialized'},
                {'jsonrpc':'2.0','id':'list','method':'tools/list'}]
        responses=self.serve(b''.join(map(self.frame,frames)))
        self.assertEqual(mcp.PROTOCOL,responses[0]['result']['protocolVersion'])
        names=[t['name'] for t in responses[1]['result']['tools']]
        self.assertEqual(list(mcp.TOOLS),names);self.assertNotIn('authorize',names)
        self.assertEqual({'tools':{}},responses[0]['result']['capabilities'])
    def test_version_fallback_and_discovery_method_not_found(self):
        responses=self.serve(self.frame({'jsonrpc':'2.0','id':0,'method':'server/discover'})+
                             self.frame(self.init(version='unsupported')))
        self.assertEqual(-32601,responses[0]['error']['code'])
        self.assertEqual(mcp.PROTOCOL,responses[1]['result']['protocolVersion'])
    def test_parse_envelope_parameter_and_unknown_tool_errors_are_distinct(self):
        frames=b'{broken\n'+b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}\n'
        frames+=self.frame([])+self.frame({'jsonrpc':'2.0','id':True,'method':'ping'})
        frames+=self.frame({'jsonrpc':'2.0','id':3,'method':'tools/list'})
        frames+=self.frame(self.init())+self.frame({'jsonrpc':'2.0','method':'notifications/initialized'})
        frames+=self.frame({'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':'authorize','arguments':{}}})
        frames+=self.frame({'jsonrpc':'2.0','id':5,'method':'tools/call','params':{'name':'execute','arguments':[]}})
        responses=self.serve(frames)
        self.assertEqual([-32700,-32700,-32600,-32600,-32602],
                         [r['error']['code'] for r in responses[:5]])
        self.assertEqual(-32602,responses[-2]['error']['code'])
        self.assertEqual(-32602,responses[-1]['error']['code'])
    def test_bad_notifications_never_receive_responses(self):
        frames=[{'jsonrpc':'2.0','method':'notifications/initialized'},
                {'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':True}},
                {'jsonrpc':'2.0','method':'notifications/cancelled','params':[]}]
        self.assertEqual([],self.serve(b''.join(map(self.frame,frames))))
    def test_frame_and_result_caps_fail_explicitly(self):
        self.assertEqual(-32600,self.serve(b'x'*(mcp.MAX_FRAME+1))[0]['error']['code'])
        output=io.BytesIO();server=mcp.StdioServer(None,output)
        try:server.result(7,{'large':'x'*mcp.MAX_FRAME})
        finally:server.cancel_all();server.pool.shutdown()
        response=json.loads(output.getvalue());self.assertEqual(7,response['id'])
        self.assertEqual(-32603,response['error']['code'])
    def test_jsonrpc_metadata_numbers_do_not_change_integer_domain_contract(self):
        self.assertEqual({'v':1.5},mcp._parse_frame(b'{"v":1.5}'))
        with self.assertRaises(ValueError):mcp._parse_frame(b'{"v":NaN}')
        with self.assertRaises(ValueError):mcp._parse_frame(b'{"v":1e999}')
    def test_cancel_busy_duplicate_and_deadline_never_dispatch_a_second_tool(self):
        class Runtime:
            def __init__(self):self.calls=0;self.started=threading.Event()
            def invoke(self,name,args,event):
                self.calls+=1;self.started.set();event.wait(5);return {'cancelled':event.is_set()}
        runtime=Runtime();output=io.BytesIO();server=mcp.StdioServer(runtime,output)
        server.receive(self.init());server.receive({'jsonrpc':'2.0','method':'notifications/initialized'})
        def call(identifier):return {'jsonrpc':'2.0','id':identifier,'method':'tools/call',
                                     'params':{'name':'analyze','arguments':{}}}
        with patch.object(mcp,'TOOL_TIMEOUT_SECONDS',.1):
            server.receive(call(2));self.assertTrue(runtime.started.wait(2))
            server.receive(call(2))
            with self.assertRaises(mcp.InvalidMcpRuntime):server.receive(call(3))
            server.receive({'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':2}})
            server.pool.shutdown(wait=True)
        server.cancel_all()
        responses=[json.loads(l) for l in output.getvalue().splitlines()]
        self.assertEqual(1,runtime.calls)
        self.assertEqual(-32600,responses[1]['error']['code'])
        self.assertTrue(responses[-1]['result']['isError'])
        self.assertIn('cancelled',responses[-1]['result']['content'][0]['text'])


    def test_deadline_cancels_an_active_tool_without_a_false_success(self):
        class Runtime:
            def invoke(self,name,args,event):
                event.wait(2);return {'returnedAfterDeadline':True}
        output=io.BytesIO();server=mcp.StdioServer(Runtime(),output)
        server.receive(self.init());server.receive({'jsonrpc':'2.0','method':'notifications/initialized'})
        with patch.object(mcp,'TOOL_TIMEOUT_SECONDS',.02):
            server.receive({'jsonrpc':'2.0','id':2,'method':'tools/call',
                            'params':{'name':'analyze','arguments':{}}})
            server.pool.shutdown(wait=True)
        server.cancel_all()
        response=json.loads(output.getvalue().splitlines()[-1])
        self.assertTrue(response['result']['isError'])
        self.assertIn('cancelled',response['result']['content'][0]['text'])

class OwnedMcpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=fixtures.GitRuntimeTests();cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=self.fixture.root);self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.dest=self.root/'result';self.store=self.root/'grants'
        self.peer=Peer(self.fixture.repo,self.root,self.store);self.addCleanup(self.peer.close)
        self.peer.initialize()
    def prepare(self):
        result=self.peer.tool('prepare',{'request':self.fixture.request,'runDirectory':str(self.dest),'mode':'parallel'})
        self.assertFalse(result['isError'],result)
        return result['structuredContent']
    def test_owned_roundtrip_refusal_separate_grant_and_independent_verifier(self):
        plan=self.prepare();self.assertFalse(self.dest.exists())
        inspected=self.peer.tool('status',{'plan':plan})
        self.assertEqual('no-private-run',inspected['structuredContent']['status'])
        self.assertIs(False,inspected['structuredContent']['executionAuthorization'])
        result=self.peer.tool('execute',{'plan':plan,'grantId':'00000000-0000-0000-0000-000000000001'})
        self.assertTrue(result['isError']);self.assertFalse(self.dest.exists())
        grant=policy.issue_operator_grant(plan,self.store,acknowledge=plan['planDigest'])
        result=self.peer.tool('execute',{'plan':plan,'grantId':grant['grantId']})
        self.assertFalse(result['isError'],result)
        self.assertEqual('verified-completed',result['structuredContent']['runtime']['status'])
        self.assertEqual('verified-completed',git_runtime.verify_run(self.fixture.request,self.dest)['status'])
        retry=self.peer.tool('execute',{'plan':plan,'grantId':grant['grantId']})
        self.assertEqual('not-repeated',retry['structuredContent']['dispatch'])
        verified=self.peer.tool('verify',{'plan':plan});self.assertFalse(verified['isError'])
        self.assertEqual('verified-completed',verified['structuredContent']['runtime']['status'])
        self.assertEqual('verified-worker-trees-and-effects',verified['structuredContent']['preparationVerification']['status'])
        self.assertIs(False,verified['structuredContent']['executionAuthorization'])
        file=self.root/'plan.json';file.write_text(json.dumps(plan))
        inspected=subprocess.run([sys.executable,'-m','agent_braid','inspect-policy-run',str(file),
                                  '--grant-store',str(self.store)],cwd=ROOT,capture_output=True,text=True,timeout=180)
        self.assertEqual(0,inspected.returncode,inspected.stderr)
        view=json.loads(inspected.stdout)
        self.assertIs(False,view['executionAuthorization']);self.assertNotIn('grantId',view)
        self.assertEqual('verified-completed',view['runtime']['status'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))
    def test_source_destination_and_store_cannot_be_expanded_by_tool_arguments(self):
        request=dict(self.fixture.request);request['repository']=str(self.root/'unregistered-source')
        for args in ({'request':request,'runDirectory':str(self.dest)},
                     {'request':self.fixture.request,'runDirectory':str(self.root/'nested'/'result')},
                     {'request':self.fixture.request,'runDirectory':str(self.dest),'grantStore':'any'},
                     {'request':self.fixture.request,'runDirectory':str(self.dest),'mode':[]}):
            result=self.peer.tool('prepare',args);self.assertTrue(result['isError'],result)
        self.assertFalse(self.dest.exists());self.assertFalse(self.store.exists())

    def test_disconnect_after_checkpoint_and_recover_with_fresh_purpose_grant(self):
        self.peer.close()
        marker=self.root/'checkpoint-marker'
        code = """
import sys,time
from pathlib import Path
from agent_braid import git_runtime as runtime,mcp_runtime as mcp
marker=Path(MARKER)
original=runtime._atomic_json
def checkpoint(root,name,value):
    original(root,name,value)
    if name=='state.json' and value.get('nextIndex')==1 and value.get('phase')=='ready':
        marker.write_text('owned checkpoint pause')
        time.sleep(2)
runtime._atomic_json=checkpoint
raise SystemExit(mcp.main())
""".replace('MARKER',repr(str(marker)))
        self.peer=Peer(self.fixture.repo,self.root,self.store,code=code);self.addCleanup(self.peer.close)
        self.peer.initialize();plan=self.prepare()
        grant=policy.issue_operator_grant(plan,self.store,acknowledge=plan['planDigest'])
        self.peer.identifier+=1
        self.peer.send({'jsonrpc':'2.0','id':self.peer.identifier,'method':'tools/call',
                        'params':{'name':'execute','arguments':{'plan':plan,'grantId':grant['grantId']}}})
        deadline=time.monotonic()+90
        while time.monotonic()<deadline and not marker.exists():time.sleep(.02)
        self.assertTrue(marker.exists(),'checkpoint was not reached')
        self.peer.close()
        prefix=git_runtime.verify_run(self.fixture.request,self.dest)
        self.assertEqual('verified-prefix',prefix['status'])
        self.assertEqual(['a'],prefix['completedOperations'])
        resume=policy.issue_operator_grant(plan,self.store,acknowledge=plan['planDigest'],action='resume')
        self.peer=Peer(self.fixture.repo,self.root,self.store);self.addCleanup(self.peer.close)
        self.peer.initialize()
        report=self.peer.tool('recover',{'plan':plan,'grantId':resume['grantId'],'action':'resume'})
        self.assertFalse(report['isError'],report)
        self.assertEqual(['a','b'],report['structuredContent']['runtime']['completedOperations'])
        self.assertEqual('verified-completed',report['structuredContent']['runtime']['status'])
        verified=self.peer.tool('verify',{'plan':plan});self.assertFalse(verified['isError'])
        self.assertEqual('verified-completed',verified['structuredContent']['runtime']['status'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))

if __name__=='__main__':unittest.main()
