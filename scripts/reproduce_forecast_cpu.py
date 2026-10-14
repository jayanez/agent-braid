#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture approved actual local CPU forecasts on owned synthetic signals.

The owner approval is pinned in a separately installed private deployment
registry. A request or command argument cannot grant or pin its own authority.
This script never provisions artifacts, downloads weights or changes limits.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import threading
import subprocess
import time
from copy import deepcopy

from agent_braid.forecast_authority import DeploymentArtifactVerifier

def additional_cases():
    """Frozen multivariate and past/known-future covariate synthetic probes."""
    from agent_braid.forecast_lab import signal_episode
    from agent_braid.forecast_data import validate_window
    base=signal_episode('constant',seed=20261014)['window'];multi=deepcopy(base)
    multi['targetIds'].append('secondary');multi['units'].append('count')
    for field in ('values','observedMask','availableAtNs','missingReasons'):multi[field].append(deepcopy(multi[field][0]))
    multi['values'][1]=[2*value for value in multi['values'][1]]
    past=deepcopy(base);past['pastCovariates']['calendar']={'unit':'count','values':[i%7 for i in range(128)],
        'availableAtNs':[past['gridStartNs']+i*past['stepNs'] for i in range(128)],'missingReasons':[None]*128}
    future=deepcopy(past);future['knownFutureCovariates']['calendar']={'unit':'count','values':[(128+i)%7 for i in range(5)],
        'availableAtNs':[future['cutoffNs']]*5,'missingReasons':[None]*5,
        'eventTimesNs':[future['cutoffNs']+(i+1)*future['stepNs'] for i in range(5)]}
    return [(name,validate_window(window),5) for name,window in [('multivariate',multi),('past-covariate',past),('known-future-covariate',future)]]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    from agent_braid.forecast_data import parse_record,digest,ForecastError
    from agent_braid.forecast_lab import FAMILIES,signal_episode
    from agent_braid.forecast_worker import DockerCPUWorker
    verifier=DeploymentArtifactVerifier()
    from agent_braid.forecast_cli import read_input
    manifest=read_input(args.manifest);attestation=verifier.verify(manifest)
    # Exclusively reserve output before model work; never overwrite previous evidence.
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    started=time.monotonic_ns();worker=None;rows=[];cleanup={'confirmed':False};total_deadline=time.monotonic()+300;budget=total_deadline-30
    active_cancellation=False
    status='inconclusive'
    try:
        worker=DockerCPUWorker(manifest,artifact_verifier=verifier)
        for family in FAMILIES:
            episode=signal_episode(family,seed=20261014)
            for horizon in (1,5,10):
                for cycle in range(7):
                    if time.monotonic()>=budget:raise ForecastError('conformance-total-budget')
                    cold=not worker.loaded
                    result=worker.forecast(episode['window'],horizon,deadline=min(budget,time.monotonic()+(31 if cold else 1)))
                    rows.append({'family':family,'horizon':horizon,'cycle':cycle,'role':'warmup' if cycle<2 else 'measured',
                                 'cold':cold,'provenance':'authentic-on-synthetic','receipt':result,'containerDiagnostics':deepcopy(worker.last_diagnostics)})
                    # Retain the first failed load/inference and stop; no hidden retries or changed caps.
                    if result['status']!='forecast':raise ForecastError('conformance-refusal')
        for name,window,horizon in additional_cases():
            result=worker.forecast(window,horizon,deadline=min(budget,time.monotonic()+1))
            rows.append({'family':name,'horizon':horizon,'cycle':0,'role':'shape-conformance','cold':False,
                         'provenance':'authentic-on-synthetic','receipt':result,'containerDiagnostics':deepcopy(worker.last_diagnostics)})
            if result['status']!='forecast':raise ForecastError('conformance-refusal')
        cancel=threading.Event();box=[]
        def predict_active():box.append(worker.forecast(signal_episode('constant',seed=17)['window'],10,
                                                      deadline=min(budget,time.monotonic()+1),cancellation=cancel))
        thread=threading.Thread(target=predict_active,daemon=True);thread.start();observe_until=min(budget,time.monotonic()+.2)
        while thread.is_alive() and time.monotonic()<observe_until:
            if worker.lock.locked():active_cancellation=True;break
            time.sleep(.001)
        cancel.set();thread.join(timeout=max(0,min(20,total_deadline-time.monotonic())))
        if thread.is_alive():raise ForecastError('active-cancellation-cleanup-pending')
        if box:
            rows.append({'family':'constant','horizon':10,'cycle':0,'role':'active-request-cancellation',
                         'cold':False,'activeRequestObserved':active_cancellation,'provenance':'authentic-on-synthetic',
                         'receipt':box[0],'containerDiagnostics':deepcopy(worker.last_diagnostics)})
            active_cancellation=active_cancellation and box[0]['status']=='cancelled' and worker.container is None
        else:active_cancellation=False
        cancel=threading.Event();cancel.set()
        negative=worker.forecast(signal_episode('constant',seed=17)['window'],1,cancellation=cancel)
        rows.append({'family':'constant','horizon':1,'cycle':0,'role':'cancel-control','cold':False,
                     'provenance':'authentic-on-synthetic','receipt':negative,'containerDiagnostics':deepcopy(worker.last_diagnostics)})
        status='conformant' if negative['status']=='cancelled' and active_cancellation else 'inconclusive'
    except (ForecastError,OSError,ValueError,subprocess.TimeoutExpired):status='inconclusive'
    finally:
        cleanup_started=time.monotonic_ns()
        if worker is not None:
            try:worker.close();cleanup['confirmed']=True
            except (ForecastError,OSError,subprocess.TimeoutExpired):cleanup['reason']='owned-worker-cleanup-pending';status='inconclusive'
        cleanup['wallNs']=time.monotonic_ns()-cleanup_started
        budget_exceeded=time.monotonic()>total_deadline
        if budget_exceeded:status='inconclusive'
        packet={'version':'agent-braid-actual-cpu-conformance-v1','manifestDigest':digest(manifest),
                'approvalRecordDigest':attestation.source_record_digest,'status':status,'rows':rows,'cleanup':cleanup,
                'wallNsThroughCleanup':time.monotonic_ns()-started,'provenance':'authentic-on-synthetic',
                'utilityAccepted':False,'realWorkloadEvidence':False,'profileChanged':False,
                'intendedForecasts':171,'activeRequestCancellationObserved':active_cancellation,
                'budgetSeconds':300,'requestBudgetSeconds':270,'cleanupReserveSeconds':30,'budgetExceeded':budget_exceeded,
                'pendingProcedures':['engine-crash','model-OOM-control','clean-room-model-reproduction','scientific-utility-acceptance']
                    +([] if active_cancellation else ['active-request-cancellation'])}
        raw=json.dumps(packet,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
    print(json.dumps({'status':status,'attempts':len(rows),'output':str(args.output),'sha256':hashlib.sha256(raw).hexdigest()}))
    return 0 if status=='conformant' else 2

if __name__=='__main__':raise SystemExit(main())
