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
import time

from agent_braid.forecast_authority import DeploymentArtifactVerifier

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
    started=time.monotonic_ns();worker=None;rows=[];cleanup={'confirmed':False};budget=time.monotonic()+300
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
                                 'cold':cold,'provenance':'authentic-on-synthetic','receipt':result})
                    # Retain the first failed load/inference and stop; no hidden retries or changed caps.
                    if result['status']!='forecast':raise ForecastError('conformance-refusal')
        cancel=threading.Event();cancel.set()
        negative=worker.forecast(signal_episode('constant',seed=17)['window'],1,cancellation=cancel)
        rows.append({'family':'constant','horizon':1,'cycle':0,'role':'cancel-control','cold':False,
                     'provenance':'authentic-on-synthetic','receipt':negative})
        status='conformant' if negative['status']=='cancelled' else 'inconclusive'
    except (ForecastError,OSError,ValueError):status='inconclusive'
    finally:
        cleanup_started=time.monotonic_ns()
        if worker is not None:
            try:worker.close();cleanup['confirmed']=True
            except (ForecastError,OSError):cleanup['reason']='owned-worker-cleanup-pending';status='inconclusive'
        cleanup['wallNs']=time.monotonic_ns()-cleanup_started
        packet={'version':'agent-braid-actual-cpu-conformance-v1','manifestDigest':digest(manifest),
                'approvalRecordDigest':attestation.source_record_digest,'status':status,'rows':rows,'cleanup':cleanup,
                'wallNsThroughCleanup':time.monotonic_ns()-started,'provenance':'authentic-on-synthetic',
                'utilityAccepted':False,'realWorkloadEvidence':False,'profileChanged':False,
                'pendingProcedures':['engine-crash','OOM-control','in-flight-cancellation','clean-room-model-reproduction','scientific-utility-acceptance']}
        raw=json.dumps(packet,sort_keys=True,indent=2,allow_nan=False).encode()+b'\n'
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
    print(json.dumps({'status':status,'attempts':len(rows),'output':str(args.output),'sha256':hashlib.sha256(raw).hexdigest()}))
    return 0 if status=='conformant' else 2

if __name__=='__main__':raise SystemExit(main())
