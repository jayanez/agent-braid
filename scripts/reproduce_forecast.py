#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce installed synthetic forecasting without downloading or loading ML."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--paired-git',action='store_true',help='Run owned synthetic fixtures with independent operator grants')
    args=parser.parse_args();started=time.monotonic_ns()
    # Deliberately resolve installed package; do not insert repository sys.path.
    from agent_braid.forecast_lab import FAMILIES,signal_episode,git_fixture
    from agent_braid.forecast_advice import ForecastSession,capabilities
    from agent_braid.forecast_data import canonical,digest
    from agent_braid.forecast_evaluation import rolling_origin_baselines
    from agent_braid.forecast_experiment import paired_synthetic_episode,summarize_pairs
    from agent_braid.forecast_mcp import PROTOCOL
    import agent_braid
    episodes=[signal_episode(f,seed=20261014+j*len(FAMILIES)+i,partition=p) for j,p in enumerate(('development','calibration','holdout')) for i,f in enumerate(FAMILIES)]
    predictions=[]
    with_session=ForecastSession()
    try:
        for episode in episodes:
            for backend in ('persistence','ewma','chronos2'):
                for horizon in (1,5,10):
                    result=with_session.predict({'version':'agent-braid-forecast-request-v1','backend':backend,'window':episode['window'],'horizon':horizon,'alpha':.3})
                    assert result['executionAuthorization'] is False
                    assert result['status']==('unavailable' if backend=='chronos2' else 'forecast')
                    predictions.append({'recipe':episode['recipe'],'backend':backend,'horizon':horizon,'receipt':result})
    finally:with_session.close()
    request={'version':'agent-braid-forecast-request-v1','backend':'persistence','window':episodes[0]['window'],'horizon':1,'alpha':.3}
    cli=subprocess.run([sys.executable,'-m','agent_braid','forecast','capabilities'],capture_output=True,check=True,timeout=5)
    assert json.loads(cli.stdout)==capabilities()
    frames=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'installed-reproduction','version':'1'}}},
            {'jsonrpc':'2.0','method':'notifications/initialized','params':{}},
            {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'forecast_predict','arguments':{'request':request,'deadlineMs':1000}}}]
    # Communicate one tool request while keeping stdin open until its response.
    mcp=subprocess.Popen([sys.executable,'-m','agent_braid.forecast_mcp'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in frames:mcp.stdin.write(canonical(frame)+b'\n')
        mcp.stdin.flush()
        import selectors
        selector=selectors.DefaultSelector();selector.register(mcp.stdout,selectors.EVENT_READ)
        responses=[];buffer=bytearray();deadline=time.monotonic()+5
        while len(responses)<2:
            if time.monotonic()>=deadline:raise TimeoutError('installed MCP deadline')
            for key,_ in selector.select(.05):
                import os
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:raise RuntimeError('installed MCP exited')
                buffer.extend(chunk)
                while b'\n' in buffer:
                    line,_,remaining=buffer.partition(b'\n');buffer=bytearray(remaining);responses.append(json.loads(line))
        selector.close();assert responses[1]['result']['structuredContent']['median']==[[4.0]]
        mcp.stdin.close();assert mcp.wait(timeout=8)==0
    finally:
        if mcp.poll() is None:mcp.kill();mcp.wait(timeout=2)
        for stream in (mcp.stdin,mcp.stdout,mcp.stderr):stream.close()
    pairs=[]
    if args.paired_git:
        from agent_braid.runtime_policy import issue_operator_grant
        def operator(plan,root):return issue_operator_grant(plan,root,acknowledge=plan['planDigest'])
        for chain in (False,True):
            with git_fixture(seed=20261014+int(chain),dependency_chain=chain) as fixture:
                pairs.append(paired_synthetic_episode(fixture,signal_episode('dependency-chain' if chain else 'constant',seed=20261014+int(chain)),operator=operator))
        assert all(all(arm['status']=='completed' for arm in pair['arms']) for pair in pairs)
    packet={'version':'agent-braid-installed-synthetic-reproduction-v1','python':platform.python_version(),'packageLocation':str(Path(agent_braid.__file__).resolve()),
            'scope':'installed synthetic simulation and authentic owned Git runs; no model load or real workload',
            'recipesDigest':digest([e['recipe'] for e in episodes]),'predictions':predictions,'evaluation':rolling_origin_baselines(episodes),
            'apiCliMcpParity':True,'pairedEpisodes':pairs,'pairedSummary':summarize_pairs(pairs) if pairs else None,
            'wallNsThroughOwnedCleanup':time.monotonic_ns()-started,'modelLoaded':False,'utilityAccepted':False}
    raw=json.dumps(packet,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
    with args.output.open('xb') as stream:stream.write(raw)
    print(json.dumps({'output':str(args.output),'sha256':hashlib.sha256(raw).hexdigest(),'predictions':len(predictions),'pairedEpisodes':len(pairs)}))
    return 0

if __name__=='__main__':raise SystemExit(main())
