# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned container-only numeric worker; imports ML only after verified limits."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
from .forecast_data import MAX_BYTES,parse_record,canonical,require,digest,pin

def _send(value):sys.stdout.buffer.write(canonical(value)+b'\n');sys.stdout.buffer.flush()

def _read():
    raw=sys.stdin.buffer.readline(MAX_BYTES+2)
    require(raw.endswith(b'\n') and len(raw)<=MAX_BYTES+1,'worker-input-budget')
    return parse_record(raw[:-1])

def _cg(name):return Path('/sys/fs/cgroup',name).read_text().strip()

def main():
    memory=int(_cg('memory.max'));swap=int(_cg('memory.swap.max'));quota,period=map(int,_cg('cpu.max').split());pids=int(_cg('pids.max'))
    require(memory==2147483648 and swap==0 and quota==period==100000 and pids==64,'worker-enforcement-unavailable')
    _send({'version':'agent-braid-worker-ready-v1','memoryMax':memory,'swapMax':swap,'cpuQuota':quota,'cpuPeriod':period,'pidsMax':pids})
    load=_read();require(load.get('command')=='load','invalid-load-command')
    remaining=load['coldRemainingSeconds']
    require(type(remaining) in (float,int) and 0<remaining<=30,'invalid-cold-budget')
    def timed_out(_signal,_frame):raise TimeoutError('worker-deadline')
    signal.signal(signal.SIGALRM,timed_out);signal.setitimer(signal.ITIMER_REAL,remaining)
    require(hashlib.sha256(Path('/opt/agent-braid/requirements-cpu.lock').read_bytes()).hexdigest()==load['dependencyLockDigest'],'dependency-lock-drift')
    for name in ('config.json','model.safetensors'):
        expected=load['files'][name];sha=hashlib.sha256()
        with Path('/model',name).open('rb') as stream:
            for chunk in iter(lambda:stream.read(1024*1024),b''):sha.update(chunk)
        require(sha.hexdigest()==expected,'checkpoint-hash-drift')
    import importlib.metadata
    require(importlib.metadata.version('chronos-forecasting')=='2.3.2','library-version-drift')
    require(importlib.metadata.version('torch')=='2.14.1+cpu','cpu-library-version-drift')
    import torch
    require(torch.version.cuda is None and not torch.backends.cuda.is_built(),'non-cpu-library-build')
    from chronos import Chronos2Pipeline
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    pipeline=Chronos2Pipeline.from_pretrained('/model',device_map='cpu',torch_dtype=torch.float32,local_files_only=True,trust_remote_code=False)
    first=_predict(pipeline,torch,load['firstRequest'])
    first['libraryVersion']='2.3.2'
    signal.setitimer(signal.ITIMER_REAL,0)
    _send(first)
    while True:
        if not sys.stdin.buffer.peek(1):return 0
        request=_read()
        signal.setitimer(signal.ITIMER_REAL,1)
        try:result=_predict(pipeline,torch,request)
        finally:signal.setitimer(signal.ITIMER_REAL,0)
        _send(result)

def _predict(pipeline,torch,request):
    require(request.get('command')=='predict','unsupported-worker-command')
    pin(request['inputDigest']);pin(request['bindingDigest'])
    require(digest({k:v for k,v in request.items() if k!='bindingDigest'})==request['bindingDigest'],'worker-input-binding')
    horizon=request['horizon'];require(type(horizon) is int and horizon in (1,5,10),'unsupported-horizon')
    inputs=[]
    for raw in request['inputs']:
        item={'target':torch.tensor([[float('nan') if value is None else value for value in row] for row in raw['target']],dtype=torch.float32)}
        for role in ('past_covariates','future_covariates'):
            item[role]={name:torch.tensor([float('nan') if value is None else value for value in values],dtype=torch.float32) for name,values in raw[role].items()}
        inputs.append(item)
    cpu_started=time.process_time_ns()
    quantiles,median=pipeline.predict_quantiles(inputs,prediction_length=horizon,quantile_levels=[.1,.5,.9],
                 context_length=128,batch_size=1,cross_learning=False,limit_prediction_length=True)
    # Linux ru_maxrss is process-lifetime peak KiB, not instantaneous group memory.
    return {'status':'forecast','bindingDigest':request['bindingDigest'],'quantiles':[q.tolist() for q in quantiles],'median':[m.tolist() for m in median],
           'rssBytes':int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024,
           'containerMemoryBytes':int(_cg('memory.current')),'modelCpuNs':time.process_time_ns()-cpu_started}


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        _send({'status':'refused','reason':'worker-failed'});raise SystemExit(1)
