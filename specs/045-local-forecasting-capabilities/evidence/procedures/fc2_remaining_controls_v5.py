#!/usr/bin/env python3
"""Owner-approved synthetic model reproduction and owned failure controls.
No provisioning, retries, shared-daemon interruption or cap changes.
"""
from pathlib import Path
from copy import deepcopy
import argparse,hashlib,json,os,selectors,signal,subprocess,sys,tempfile,time,uuid,zipfile
import agent_braid
import sysconfig
from agent_braid.forecast_store import open_directory
from agent_braid.forecast_data import pin
from agent_braid.forecast_advice import ForecastSession
from agent_braid.forecast_authority import DeploymentArtifactVerifier,_private_record
from agent_braid.forecast_cli import read_input
from agent_braid.forecast_data import canonical,digest,parse_record,require,MAX_BYTES
from agent_braid.forecast_lab import signal_episode
from agent_braid.forecast_mcp import PROTOCOL
from agent_braid.forecast_outputs import validate_forecast

OOM_PROGRAM="""import pathlib,json,os
p=pathlib.Path('/proc/1');status=(p/'status').read_text();cmd=(p/'cmdline').read_bytes()
assert b'agent_braid.forecast_worker_entry' in cmd
uid=next(x.split()[1:] for x in status.splitlines() if x.startswith('Uid:'))
assert all(int(x)==os.getuid() for x in uid)
cg=pathlib.Path('/sys/fs/cgroup')
assert (cg/'memory.max').read_text().strip()=='2147483648'
assert (cg/'memory.swap.max').read_text().strip()=='0'
assert (cg/'cpu.max').read_text().strip()=='100000 100000'
mem=pathlib.Path('/proc/meminfo').read_text().splitlines()
available=int(next(x.split()[1] for x in mem if x.startswith('MemAvailable:')))*1024
current=int((cg/'memory.current').read_text())
assert available>=max(0,2147483648-current)+536870912
print(json.dumps({'pid':1,'uid':os.getuid(),'commandConfirmed':True,'kernelMemAvailableBytesBefore':available,'cgroupMemoryBytesBefore':current,'headroomSafetyMarginBytes':536870912,'oomScoreBefore':(p/'oom_score_adj').read_text().strip(),'memoryEventsBefore':(cg/'memory.events').read_text()}),flush=True)
(p/'oom_score_adj').write_text('1000')
assert (p/'oom_score_adj').read_text().strip()=='1000'
print(json.dumps({'oomScoreApplied':(p/'oom_score_adj').read_text().strip()}),flush=True)
a=[]
for i in range(48):
 a.append(bytearray(64*1024*1024))
 print(json.dumps({'allocatedBytes':len(a)*64*1024*1024,'memoryEvents':(cg/'memory.events').read_text()}),flush=True)
"""

def claim_run(directory,record_sha,manifest_digest):
    pin(record_sha);pin(manifest_digest);parent=open_directory(directory,private=True)
    try:fd=os.open('fc2-run-'+record_sha+'.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent)
    finally:os.close(parent)
    with os.fdopen(fd,'wb') as stream:
        stream.write(canonical({'recordSha256':record_sha,'manifestDigest':manifest_digest,'claimedByPid':os.getpid(),'claimedUnixNs':time.time_ns(),'oneRun':True}));stream.flush();os.fsync(stream.fileno())

def bounded_process(argv,env,deadline,observation):
    require(time.monotonic()<deadline,'control-budget-exhausted')
    observation.update(stdout='',stderrBytes=0,completed=False)
    p=subprocess.Popen(argv,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    sel=selectors.DefaultSelector();buffers={p.stdout:bytearray(),p.stderr:bytearray()}
    for stream in buffers:sel.register(stream,selectors.EVENT_READ)
    try:
        while sel.get_map():
            require(time.monotonic()<deadline,'control-deadline-exceeded')
            for key,_ in sel.select(.02):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:sel.unregister(key.fileobj);continue
                require(len(buffers[key.fileobj])+len(chunk)<=MAX_BYTES,'control-output-budget')
                buffers[key.fileobj].extend(chunk)
        code=p.wait(timeout=max(.01,deadline-time.monotonic()));observation['completed']=True
        return subprocess.CompletedProcess(argv,code,bytes(buffers[p.stdout]),bytes(buffers[p.stderr]))
    finally:
        observation['stdout']=bytes(buffers[p.stdout]).decode('utf8',errors='replace');observation['stderrBytes']=len(buffers[p.stderr]);observation['ownedPid']=p.pid
        sel.close()
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGTERM)
            try:p.wait(timeout=2)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=1)
        observation['processExited']=p.poll() is not None
        p.stdout.close();p.stderr.close()

def child_frames(process,wanted,timeout,observation,*,budget=float('inf')):
    sel=selectors.DefaultSelector();buffers={process.stdout:bytearray(),process.stderr:bytearray()};stdout=bytearray();frames=[];deadline=min(budget,time.monotonic()+timeout)
    for stream in buffers:sel.register(stream,selectors.EVENT_READ)
    try:
        while len(frames)<wanted:
            require(time.monotonic()<deadline,'child-response-timeout')
            for key,_ in sel.select(.02):
                chunk=os.read(key.fileobj.fileno(),65536)
                if not chunk:
                    sel.unregister(key.fileobj)
                    require(key.fileobj is not process.stdout or len(frames)>=wanted,'child-eof')
                    continue
                require(len(buffers[key.fileobj])+len(chunk)<=MAX_BYTES,'child-output-budget')
                if key.fileobj is process.stdout:
                    require(len(stdout)+len(chunk)<=MAX_BYTES,'child-output-budget');stdout.extend(chunk)
                buffers[key.fileobj].extend(chunk)
                if key.fileobj is process.stdout:
                    while b'\n' in buffers[key.fileobj]:
                        line,_,remaining=buffers[key.fileobj].partition(b'\n');buffers[key.fileobj]=bytearray(remaining);frames.append(parse_record(bytes(line)))
        return frames
    finally:
        observation['stdout']=bytes(stdout).decode('utf8',errors='replace');observation['partialStdout']=bytes(buffers[process.stdout]).decode('utf8',errors='replace');observation['parsedFrames']=frames;observation['stderrBytes']=len(buffers[process.stderr]);sel.close()

def main():
    start=time.monotonic_ns();end=start/1e9+480;budget=end-30
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--execute',action='store_true');ap.add_argument('--host-wheel',type=Path);a=ap.parse_args()
    if not a.execute:
        print(json.dumps({'plannedOnly':True,'maxForecastRequests':9,'faultControls':2,'totalSeconds':480,'requestSeconds':450,'cleanupReserveSeconds':30,'wholeDaemonCrash':'pending; shared daemon never stopped'}));return 0
    manifest=read_input(a.manifest);verifier=DeploymentArtifactVerifier();attestation=verifier.verify(manifest);require(attestation is not None,'artifact-not-approved')
    output=os.open(a.output,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
    rows=[];sessions=[];children=[];known={};calls=0;clean=True;request_overrun=False;last_docker=None;package_binding=None;pin_revoked=False;claimed=False;outcome='inconclusive';previous_term=None
    env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':str(Path.home()),'LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
    request={'version':'agent-braid-forecast-request-v1','backend':'chronos2','window':signal_episode('constant',seed=20261014)['window'],'horizon':1,'alpha':.3}
    def admission(seconds=0):require(time.monotonic()+seconds<budget,'procedure-request-budget')
    def request_check():
        nonlocal request_overrun
        if time.monotonic()>budget:request_overrun=True
        require(not request_overrun,'procedure-request-budget')
    def register_call():
        nonlocal calls
        admission();calls+=1;require(calls<=9,'procedure-attempt-budget')
    def checked_forecast(value,horizon):
        validate_forecast(value,request['window'],horizon)
        require(all(type(value['costs'].get(k)) is int and value['costs'][k]>0 for k in ('wallNs','modelCpuNs','rssBytes','containerMemoryBytes')),'required-model-cost-not-observed')
        require(value['modelDigest']==digest(manifest),'model-binding-drift')
        return value
    def model_call(session,horizon,role,expected='forecast'):
        admission(27 if session.adapter.worker is not None and session.adapter.worker.loaded else 55)
        register_call();row={'role':role,'status':'attempted'};rows.append(row);r=deepcopy(request);r['horizon']=horizon
        value=session.predict(r,deadline=budget);worker=session.adapter.worker
        if worker is not None and worker.container is not None:known[worker.container]=(worker.owner,worker.model_digest)
        row.update(receipt=value,diagnostics=deepcopy(getattr(worker,'last_diagnostics',None)),status='returned');request_check()
        require(value['status']==expected,'unexpected-public-forecast-status');checked_forecast(value,horizon);return value
    def docker(*args,timeout=3,cleanup=False):
        nonlocal last_docker
        deadline=min(end if cleanup else budget,time.monotonic()+timeout)
        last_docker={'operation':args[0:2]}
        with tempfile.TemporaryDirectory(prefix='fc2-owned-docker-') as directory:
            e={'PATH':env['PATH'],'HOME':directory,'DOCKER_CONFIG':directory}
            return bounded_process(['docker','--host','unix://'+manifest['engineSocket'],*args],e,deadline,last_docker)
    def owned_state(worker):
        raw=docker('container','inspect',worker.container,'--format','{{json .}}');require(raw.returncode==0,'owned-inspect-failed');v=parse_record(raw.stdout.strip())
        require(v['Id']==worker.container and v['Config']['Labels'].get('agent-braid.forecast-owner')==worker.owner and v['Config']['Labels'].get('agent-braid.forecast-manifest')==worker.model_digest,'ownership-drift');return v
    try:
        require(a.host_wheel is not None,'host-wheel-required')
        wheel_sha=hashlib.sha256(a.host_wheel.read_bytes()).hexdigest();require(wheel_sha=='0faea2370d5a8da15d613373e9d2414805fd17b79a00ee66c3ef0516900238df','host-wheel-drift')
        package_root=Path(agent_braid.__file__).resolve().parent;require(package_root.parent==Path(sysconfig.get_paths()['purelib']).resolve(),'not-an-installed-package')
        with zipfile.ZipFile(a.host_wheel) as archive:
            for name in archive.namelist():
                if name.startswith('agent_braid/') and name.endswith('.py'):require(archive.read(name)==(package_root/Path(name).relative_to('agent_braid')).read_bytes(),'installed-source-drift')
        package_binding={'hostWheelSha256':wheel_sha,'packageOrigin':str(package_root),'python':sys.version,'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'softwareCandidate':'e6d1e6ee870611e41b83f5239544061f7e58de86'}
        require(time.monotonic()+446<budget,'complete-procedure-reservation-unavailable')
        claim_run(Path.home()/'.config/agent-braid/forecast',attestation.source_record_digest,digest(manifest));claimed=True
        def terminated(_signal,_frame):raise KeyboardInterrupt('termination-requested')
        previous_term=signal.signal(signal.SIGTERM,terminated)
        s=ForecastSession(manifest,artifact_verifier=verifier);sessions.append(s)
        require(time.monotonic()+442<budget,'post-claim-setup-budget')
        api=[]
        for h in (1,5,10):api.append(model_call(s,h,'independent-api'))
        admission(24);s.close();sessions.remove(s);request_check()
        with tempfile.TemporaryDirectory(prefix='fc2-independent-input-') as directory:
            inp=Path(directory)/'request.json';inp.write_bytes(canonical(request))
            admission(55);register_call();child_row={'role':'independent-cli','status':'attempted'};rows.append(child_row);p=subprocess.Popen([sys.executable,'-I','-m','agent_braid','forecast','predict',str(inp),'--cpu-manifest',str(a.manifest)],stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=tempfile.gettempdir(),start_new_session=True);children.append(p)
            value=child_frames(p,1,35,child_row,budget=budget)[0];require(p.wait(timeout=20)==0 and value['status']=='forecast','cli-reproduction-failed');checked_forecast(value,1);require(value['quantiles']==api[0]['quantiles'] and value['median']==api[0]['median'],'cli-api-output-mismatch');child_row.update(receipt=value,status='returned');request_check()
        admission(55);register_call();child_row={'role':'independent-mcp','status':'attempted'};rows.append(child_row);p=subprocess.Popen([sys.executable,'-I','-m','agent_braid','forecast','serve-mcp','--cpu-manifest',str(a.manifest)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=tempfile.gettempdir(),start_new_session=True);children.append(p)
        frames=[{'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':PROTOCOL,'capabilities':{},'clientInfo':{'name':'fc2-independent-reproduction','version':'1'}}},{'jsonrpc':'2.0','method':'notifications/initialized','params':{}},{'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'forecast_predict','arguments':{'request':request,'deadlineMs':30000}}}]
        for f in frames:p.stdin.write(canonical(f)+b'\n')
        p.stdin.flush();responses=child_frames(p,2,35,child_row,budget=budget);value=next(r for r in responses if r.get('id')==2)['result']['structuredContent'];require(value['status']=='forecast','mcp-reproduction-failed');p.stdin.close();require(p.wait(timeout=20)==0,'mcp-cleanup-failed');checked_forecast(value,1);require(value['quantiles']==api[0]['quantiles'] and value['median']==api[0]['median'],'mcp-api-output-mismatch');child_row.update(receipt=value,status='returned');request_check()
        # Interrupt only the owned attach client. The daemon remains available.
        s=ForecastSession(manifest,artifact_verifier=verifier);sessions.append(s);model_call(s,1,'transport-setup');w=s.adapter.worker;admission(35);before=owned_state(w);require(before['State']['Running'] is True and w.process.poll() is None,'attach-fault-precondition-unobserved')
        w.process.terminate();w.process.wait(timeout=2);daemon_probe=docker('info','--format','{{json .OSType}}');require(daemon_probe.returncode==0 and json.loads(daemon_probe.stdout)=='linux','daemon-availability-unobserved');rows.append({'role':'owned-attach-transport-fault','containerId':w.container,'owner':w.owner,'manifestDigest':w.model_digest,'daemonStopRequested':False,'daemonAvailableAfterFault':True,'stateBefore':before['State']})
        register_call();attempt={'role':'transport-public-refusal','status':'attempted'};rows.append(attempt);r=deepcopy(request);r['horizon']=5;value=s.predict(r,deadline=budget);attempt.update(receipt=value,diagnostics=deepcopy(w.last_diagnostics),status='returned');request_check();require(value['status']=='refused' and 'worker-exited' in value['reasonCodes'],'transport-did-not-fail-closed');require(w.container is None and w.last_diagnostics['cleanupConfirmed'],'transport-cleanup-pending');s.close();sessions.remove(s)
        # Resident model is deliberately made a possible OOM victim; no retry.
        s=ForecastSession(manifest,artifact_verifier=verifier);sessions.append(s);model_call(s,1,'oom-setup');w=s.adapter.worker;admission(54);before=owned_state(w)
        fault={'role':'resident-worker-oom','status':'attempted','containerId':w.container,'owner':w.owner,'manifestDigest':w.model_digest};rows.append(fault)
        host_memory=docker('info','--format','{{json .MemTotal}}');require(host_memory.returncode==0 and type(json.loads(host_memory.stdout)) is int and json.loads(host_memory.stdout)>2147483648,'host-memory-condition-unavailable');allocation=docker('container','exec',w.container,'python','-I','-c',OOM_PROGRAM,timeout=15);after=owned_state(w)
        fault.update({'role':'resident-worker-oom','containerId':w.container,'owner':w.owner,'manifestDigest':w.model_digest,'hostMemoryBytes':json.loads(host_memory.stdout),'allocatorExit':allocation.returncode,'allocatorObservations':[parse_record(line) for line in allocation.stdout.splitlines()],'stateBefore':before['State'],'stateAfter':after['State'],'postDeathMemoryEvents':'not-observed; namespace may already be gone'})
        require(after['State']['OOMKilled'] is True and after['State']['ExitCode']==137 and after['State']['Running'] is False,'worker-oom-inconclusive');fault['status']='observed'
        register_call();attempt={'role':'oom-public-refusal','status':'attempted'};rows.append(attempt);r=deepcopy(request);r['horizon']=5;value=s.predict(r,deadline=budget);attempt.update(receipt=value,diagnostics=deepcopy(w.last_diagnostics),status='returned');request_check();require(value['status']=='refused' and 'worker-oom' in value['reasonCodes'],'oom-did-not-fail-closed');require(w.container is None and w.last_diagnostics['cleanupConfirmed'],'oom-cleanup-pending');s.close();sessions.remove(s)
        request_check();outcome='observed'
    except BaseException as exc:
        outcome='inconclusive';rows.append({'role':'procedure-failure','exceptionType':type(exc).__name__,'reason':str(exc) if type(exc).__name__=='ForecastError' else 'procedure-failed','lastDockerObservation':last_docker})
    finally:
        prior_int=signal.signal(signal.SIGINT,signal.SIG_IGN);prior_term=signal.signal(signal.SIGTERM,signal.SIG_IGN)
        for p in children:
            if p.poll() is None:
                try:
                    if p.stdin and not p.stdin.closed:p.stdin.close()
                    p.wait(timeout=8)
                except Exception:
                    p.terminate()
                    try:p.wait(timeout=3)
                    except subprocess.TimeoutExpired:p.kill();p.wait(timeout=2)
                    # Unknown child-owned container is not guessed or broadly removed.
                    clean=False
        for s in sessions:
            try:s.close()
            except Exception:clean=False
        for cid,(owner,md) in known.items():
            try:
                result=docker('container','inspect',cid,'--format','{{json .}}',cleanup=True)
                if result.returncode==0:
                    v=parse_record(result.stdout.strip());require(v['Id']==cid and v['Config']['Labels'].get('agent-braid.forecast-owner')==owner and v['Config']['Labels'].get('agent-braid.forecast-manifest')==md,'recovery-owner-drift');require(docker('container','rm','--force',cid,cleanup=True).returncode==0,'cleanup-pending')
            except Exception:clean=False
        lease_state=None
        try:
            lease_path=Path.home()/'.local/state/agent-braid/forecast/cpu-worker.lease'
            fd=os.open(lease_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            with os.fdopen(fd,'rb') as stream:
                info=os.fstat(stream.fileno());require(info.st_uid==os.getuid() and info.st_size<=4096,'unsafe-cleanup-lease')
                lease_state=parse_record(stream.read(4097))
            if lease_state.get('manifestDigest')==digest(manifest) and lease_state.get('cleanupConfirmed') is not True:clean=False
        except Exception:clean=False
        try:
            require(claimed,'run-not-claimed')
            registry=Path.home()/'.config/agent-braid/forecast/owner-approval-pins.json'
            data=read_input(registry);kept=[];removed=0
            for pin_record in data['approvals']:
                if pin_record['manifestDigest']==digest(manifest):
                    source=Path(pin_record['recordPath']);require(source.parent==registry.parent and not source.is_symlink(),'approval-revoke-path')
                    record,observed=_private_record(source)
                    if observed==attestation.source_record_digest and observed==pin_record['recordSha256']:removed+=1;continue
                kept.append(pin_record)
            require(removed==1,'one-run-pin-not-found');data['approvals']=kept
            temporary=registry.parent/('completed-fc2-'+uuid.uuid4().hex+'.tmp')
            fd=os.open(temporary,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream:stream.write(canonical(data));stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,registry);pin_revoked=True
        except Exception:outcome='inconclusive'
        exceeded=time.monotonic()>end
        if exceeded:outcome='inconclusive'
        packet={'version':'agent-braid-fc2-remaining-controls-v1','manifestDigest':digest(manifest),'approvalRecordDigest':attestation.source_record_digest,'forecastRequests':calls,'rows':rows,'status':outcome,'cleanupConfirmed':clean,'wallNsThroughCleanup':time.monotonic_ns()-start,'budgetSeconds':480,'budgetExceeded':exceeded,'requestBudgetExceeded':request_overrun,'requestBudgetSeconds':450,'aggregateStageReservationSeconds':442,'claimAndSessionSetupMarginSeconds':4,'cleanupLease':lease_state,'packageBinding':package_binding,'oneRunPinRevoked':pin_revoked,'runClaimed':claimed,'scope':'authentic-on-synthetic','daemonCrash':'pending; shared daemon never stopped','scientificUtilityAccepted':False}
        with os.fdopen(output,'w') as f:json.dump(packet,f,indent=2,sort_keys=True);f.write('\n')
        signal.signal(signal.SIGINT,prior_int);signal.signal(signal.SIGTERM,previous_term if previous_term is not None else prior_term)
    print(json.dumps({'status':outcome,'forecastRequests':calls,'cleanupConfirmed':clean}));return 0 if outcome=='observed' and clean else 2

if __name__=='__main__':raise SystemExit(main())
