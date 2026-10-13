#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Measure owned Docker limit controls on synthetic processes; never import ML."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--image-id',required=True)
    p.add_argument('--engine-socket',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    from agent_braid.forecast_data import pin,require,digest
    from agent_braid.forecast_lease import WorkerLease
    require(a.image_id.startswith('sha256:'),'mutable-image');pin(a.image_id[7:]);require(a.engine_socket.is_socket(),'nonlocal-engine')
    owner=uuid.uuid4().hex;recipe={'imageId':a.image_id,'scope':'synthetic-container-controls-no-model','memoryBytes':2147483648,'cpus':1}
    lease=WorkerLease(owner,digest(recipe));lease.acquire();rows=[];current=None;uncertain=False;started=time.monotonic_ns()
    output=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    scope=tempfile.TemporaryDirectory(prefix='forecast-control-')
    try:
        directory=scope.name
        if directory:
            env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'DOCKER_CONFIG':directory,'HOME':directory}
            def docker(*args,timeout=30):
                r=subprocess.run(['docker','--host','unix://'+str(a.engine_socket),*args],env=env,capture_output=True,timeout=timeout)
                require(len(r.stdout)<=1048576 and len(r.stderr)<=1048576,'control-output-budget');return r
            image=docker('image','inspect',a.image_id,'--format','{{.Id}}');require(image.returncode==0 and image.stdout.decode().strip()==a.image_id,'image-drift')
            programs={
                'effective-limits':"import json,pathlib; p=pathlib.Path('/sys/fs/cgroup'); print(json.dumps({n:(p/n).read_text().strip() for n in ['memory.max','memory.swap.max','cpu.max','pids.max']}))",
                'oom':"a=[bytearray(64*1024*1024) for _ in range(64)]; print(len(a))",
                'owned-crash':"import os; os._exit(17)",
            }
            for name,program in programs.items():
                begin=time.monotonic_ns();uncertain=True
                created=docker('container','create','--name=agent-braid-forecast-control-'+owner+'-'+name,
                    '--pull=never','--network=none','--read-only','--user='+str(os.getuid())+':'+str(os.getgid()),
                    '--cap-drop=ALL','--security-opt=no-new-privileges','--memory=2147483648','--memory-swap=2147483648',
                    '--cpus=1','--pids-limit=64','--tmpfs=/tmp:rw,nosuid,nodev,size=67108864',
                    '--label','agent-braid.forecast-owner='+owner,'--label','agent-braid.forecast-manifest='+digest(recipe),
                    '--entrypoint','python',a.image_id,'-I','-c',program)
                require(created.returncode==0,'container-create-failed');current=created.stdout.decode().strip();pin(current);uncertain=False
                before=json.loads(docker('container','inspect',current,'--format','{{json .}}').stdout)
                require(before['Id']==current and before['Config']['Labels']['agent-braid.forecast-owner']==owner,'control-owner-drift')
                timed_out=False
                try:r=docker('container','start','--attach',current)
                except subprocess.TimeoutExpired:
                    timed_out=True;r=None
                after=json.loads(docker('container','inspect',current,'--format','{{json .State}}').stdout)
                if timed_out:pass
                elif name=='effective-limits':
                    require(r.returncode==0,'control-failed');limits=json.loads(r.stdout)
                    require(limits=={'memory.max':'2147483648','memory.swap.max':'0','cpu.max':'100000 100000','pids.max':'64'},'effective-limit-drift')
                elif name=='oom':require(after['OOMKilled'] is True and after['ExitCode']==137,'oom-not-enforced')
                else:require(after['ExitCode']==17 and after['OOMKilled'] is False,'crash-not-observed')
                row={'control':name,'status':'timed-out' if timed_out else 'observed','state':after,'limits':json.loads(r.stdout) if name=='effective-limits' and r else None,
                     'wallNs':time.monotonic_ns()-begin,'provenance':'authentic-on-synthetic','modelLoaded':False}
                require(docker('container','rm','--force',current).returncode==0,'cleanup-pending');current=None
                rows.append(row)
    finally:
        if current is not None:
            try:
                inspected=json.loads(docker('container','inspect',current,'--format','{{json .}}').stdout)
                require(inspected['Config']['Labels']['agent-braid.forecast-owner']==owner,'cleanup-owner-drift')
                require(docker('container','rm','--force',current).returncode==0,'cleanup-pending');current=None
            except Exception:pass
        confirmed=current is None and not uncertain;lease.release(cleanup_confirmed=confirmed);scope.cleanup()
        packet={'version':'agent-braid-synthetic-container-controls-v1','recipe':recipe,'rows':rows,'cleanupConfirmed':confirmed,
                'wallNsThroughCleanup':time.monotonic_ns()-started,'modelLoaded':False,'modelArtifactApproved':False,'utilityAccepted':False,'status':'observed' if len(rows)==3 and all(r['status']=='observed' for r in rows) else 'inconclusive'}
        with os.fdopen(output,'w') as stream:json.dump(packet,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps({'controls':len(rows),'cleanupConfirmed':confirmed,'modelLoaded':False}))
    return 0 if len(rows)==3 and confirmed and all(r['status']=='observed' for r in rows) else 2

if __name__=='__main__':raise SystemExit(main())
