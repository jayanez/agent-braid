#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture actual Codex stdio tool exercise through its no-model app-server bridge."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent_braid import runtime_policy,git_runtime
from tests import test_git_runtime as fixtures

WRAPPER='''import json,sys,time
from pathlib import Path
sys.path.insert(0,LIBRARY)
from agent_braid import mcp_runtime as mcp,git_runtime as runtime
log=Path(LOG);marker=Path(MARKER)
original=runtime._atomic_json
def checkpoint(root,name,value):
 original(root,name,value)
 if name=='state.json' and value.get('nextIndex')==1 and value.get('phase')=='ready' and not marker.exists():
  marker.write_text('owned-fixture controlled checkpoint pause')
  time.sleep(2)
runtime._atomic_json=checkpoint
class Input:
 def readline(self,limit=-1):
  raw=sys.__stdin__.buffer.readline(limit)
  if raw:
   with log.open('ab') as stream:stream.write(b'IN '+raw)
  return raw
class Output:
 def write(self,raw):
  with log.open('ab') as stream:stream.write(b'OUT '+raw)
  return sys.__stdout__.buffer.write(raw)
 def flush(self):return sys.__stdout__.buffer.flush()
sys.stdin=type('Stdin',(),{'buffer':Input()})()
sys.stdout=type('Stdout',(),{'buffer':Output()})()
raise SystemExit(mcp.main())
'''


class Bridge:
    def __init__(self,codex,root,server,args,observations):
        config='mcp_servers={m4_alpha={command='+json.dumps(sys.executable)+',args='+json.dumps([str(server),*args])+',startup_timeout_sec=20,tool_timeout_sec=360}}'
        self.process=subprocess.Popen([str(codex),'app-server','-c',config],cwd=root,
                                      stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                                      start_new_session=True)
        self.selector=selectors.DefaultSelector();self.selector.register(self.process.stdout,selectors.EVENT_READ)
        self.buffer=b'';self.pending=[];self.counter=0;self.observations=observations
        try:
            self.rpc('initialize',{'clientInfo':{'name':'m4_owned_no_model_capture','version':'1'}})
            self.process.stdin.write(b'{"method":"initialized"}\n');self.process.stdin.flush()
            thread=self.rpc('thread/start',{'cwd':str(root),'ephemeral':True,'approvalPolicy':'never',
                                           'sandbox':'read-only','baseInstructions':'Owned no-model MCP bridge exercise. No turn may be started.'})
            self.thread=thread['thread']['id']
            self.rpc('mcpServerStatus/list',{'threadId':self.thread,'serverName':'m4_alpha','detail':'toolsAndAuthOnly'})
        except Exception:
            self.close();raise
    def send(self,method,params):
        if method not in {'initialize','thread/start','mcpServerStatus/list','mcpServer/tool/call'}:
            raise ValueError('bridge method outside no-model exercise')
        self.counter+=1;identifier=self.counter
        self.process.stdin.write((json.dumps({'id':identifier,'method':method,'params':params})+'\n').encode())
        self.process.stdin.flush()
        self.observations.append({'method':method,'tool':params.get('tool'),'requestId':identifier})
        return identifier
    def wait(self,identifier):
        deadline=time.monotonic()+360
        while time.monotonic()<deadline:
            for index,item in enumerate(self.pending):
                if item.get('id')==identifier:
                    result=self.pending.pop(index)
                    if 'error' in result:raise RuntimeError(str(result['error']))
                    return result['result']
            if not self.selector.select(max(0,deadline-time.monotonic())):break
            raw=os.read(self.process.stdout.fileno(),65536)
            if not raw:break
            self.buffer+=raw
            while b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1)
                if line:self.pending.append(json.loads(line))
        raise RuntimeError('bounded app-server RPC timeout; inspect owned state')
    def rpc(self,method,params):return self.wait(self.send(method,params))
    def tool(self,name,args,wait=True):
        identifier=self.send('mcpServer/tool/call',{'threadId':self.thread,'server':'m4_alpha','tool':name,'arguments':args})
        return self.wait(identifier) if wait else identifier
    def close(self):
        if self.process.poll() is None:
            os.killpg(self.process.pid,signal.SIGTERM)
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
        self.selector.close();self.process.stdin.close();self.process.stdout.close()


def run(codex,output):
    from scripts.reproduce_m4_alpha import inputs
    before=inputs();before['scripts/capture_m4_codex.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    output=output.expanduser().resolve()
    if output.is_relative_to(ROOT):raise ValueError('host output must be outside candidate checkout')
    git=lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args],timeout=30).decode().strip()
    if git('status','--porcelain'):raise ValueError('host capture requires a clean frozen candidate')
    candidate=git('rev-parse','HEAD');version=subprocess.check_output([str(codex),'--version'],timeout=15).decode().strip()
    if version!='codex-cli 0.159.0-alpha.12.1':raise ValueError('host version differs from G1 pin')
    fixture=fixtures.GitRuntimeTests()
    with patch.dict(os.environ,{'GIT_AUTHOR_DATE':'2000-01-01T00:00:00+00:00','GIT_COMMITTER_DATE':'2000-01-01T00:00:00+00:00'}):fixture.setUp()
    observations=[];records={};trace=[];bridge=None;failure=None;source_unchanged=False;log=None;owned=None
    try:
        owned=tempfile.TemporaryDirectory(prefix='agent-braid-owned-codex-',dir=fixture.root)
        directory=owned.name
        root=Path(directory);server=root/'server.py';log=root/'stdio.log';marker=root/'checkpoint-marker'
        server.write_text(WRAPPER.replace('LIBRARY',repr(str(ROOT))).replace('LOG',repr(str(log))).replace('MARKER',repr(str(marker))))
        args=['--source-root',str(fixture.repo),'--result-parent',str(root),'--grant-store',str(root/'grants')]
        bridge=Bridge(codex,root,server,args,observations)
        def checked(name,args):
            result=bridge.tool(name,args)
            if result.get('isError'):raise RuntimeError(str(result))
            records[name]=result['structuredContent'];return result['structuredContent']
        analyzed=checked('analyze',{'request':fixture.request})
        if analyzed['executionAuthorization'] is not False:raise RuntimeError('analysis granted authority')
        plan=checked('prepare',{'request':fixture.request,'runDirectory':str(root/'result'),'mode':'parallel'})
        checked('verify',{'plan':plan})
        refusal=bridge.tool('execute',{'plan':plan,'grantId':'00000000-0000-0000-0000-000000000001'})
        if not refusal.get('isError') or (root/'result').exists():raise RuntimeError('missing-grant refusal failed')
        records['missingGrantRefusal']=refusal
        grant=runtime_policy.issue_operator_grant(plan,root/'grants',acknowledge=plan['planDigest'],ttl_seconds=900)
        bridge.tool('execute',{'plan':plan,'grantId':grant['grantId']},wait=False)
        deadline=time.monotonic()+180
        while time.monotonic()<deadline and not marker.exists():time.sleep(.02)
        if not marker.exists():raise RuntimeError('controlled checkpoint not reached')
        bridge.close();bridge=None
        # The server's bounded checkpoint pause permits cancellation to drain.
        time.sleep(2.1)
        prefix=git_runtime.verify_run(fixture.request,root/'result')
        if prefix['status']!='verified-prefix' or prefix['completedOperations']!=['a']:
            raise RuntimeError('disconnect did not preserve the verified first prefix')
        records['independentPrefix']=prefix
        resume=runtime_policy.issue_operator_grant(plan,root/'grants',acknowledge=plan['planDigest'],action='resume',ttl_seconds=900)
        bridge=Bridge(codex,root,server,args,observations)
        checked('status',{'plan':plan})
        recovered=checked('recover',{'plan':plan,'grantId':resume['grantId'],'action':'resume'})
        if recovered['runtime']['status']!='verified-completed':raise RuntimeError('host recovery incomplete')
        checked('verify',{'plan':plan})
        retry=checked('execute',{'plan':plan,'grantId':grant['grantId']})
        if retry['dispatch']!='not-repeated':raise RuntimeError('duplicate dispatch repeated')
        records['independentCompleted']=git_runtime.verify_run(fixture.request,root/'result')
        abort=runtime_policy.issue_operator_grant(plan,root/'grants',acknowledge=plan['planDigest'],action='abort',ttl_seconds=900)
        records['abort']=checked('recover',{'plan':plan,'grantId':abort['grantId'],'action':'abort'})
        if records['abort']['runtime']['status']!='verified-aborted':raise RuntimeError('host abort incomplete')
        bridge.close();bridge=None
        trace=[{'direction':line.split(' ',1)[0],'message':json.loads(line.split(' ',1)[1])} for line in log.read_text().splitlines()]
        if fixture.snapshot(fixture.repo)!=fixture.before:raise RuntimeError('source changed')
    except Exception as exc:
        failure=str(exc)[:2048]
    finally:
        if bridge is not None:bridge.close()
        if log is not None and log.exists():
            trace=[{'direction':line.split(' ',1)[0],'message':json.loads(line.split(' ',1)[1])}
                   for line in log.read_text().splitlines()]
        source_unchanged=fixture.snapshot(fixture.repo)==fixture.before
        if owned is not None:owned.cleanup()
        fixture.doCleanups()
    after=inputs();after['scripts/capture_m4_codex.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    changed=before!=after or bool(git('status','--porcelain'))
    record={'m4ActualHostEvidenceVersion':'0.1.0-alpha','candidateCommit':candidate,'inputs':before,
            'host':'Codex','hostVersion':version,'protocol':'2025-11-25','modelCalls':0,
            'persistentHostConfigChanges':False,'operatorGrantOrigin':'Owned-fixture engineering harness under G0; never model issued.',
            'environment':{'python':platform.python_version(),'platform':platform.system(),'machine':platform.machine()},
            'bridgeRequests':observations,'records':records,'stdioTranscript':trace,
            'candidateChangedDuringRun':changed,'sourceUnchanged':source_unchanged,'failure':failure,
            'status':'invalidated' if changed else ('failed' if failure or not source_unchanged else 'passed'),
            'limits':['Actual Codex client through its no-model direct tool bridge; no model reasoning or live user-agent workload claim.',
                      'Owned fixed corpus and a controlled two-second checkpoint pause for disconnect/recovery.',
                      'No persistent host registration, arbitrary code in admitted operation language, source promotion or paid-model calls.',
                      'This one-host observation does not discharge Claude, Linux, independent review or founder whole-M4 acceptance.']}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':record['status'],'output':str(output),'modelCalls':0}))
    return 0 if record['status']=='passed' else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex-path',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();raise SystemExit(run(args.codex_path,args.output))
