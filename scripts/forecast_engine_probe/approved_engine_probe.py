# SPDX-License-Identifier: AGPL-3.0-only
"""Plan only by default; fixed actual-owner pins precede owned VM qualification."""
from pathlib import Path
import argparse,base64,fcntl,hashlib,json,os,resource,selectors,signal,stat,subprocess,time

ROOT=Path(__file__).resolve().parent
import sys
sys.path.insert(0,str(ROOT))
STATE=Path.home()/'.config/agent-braid/forecast'
SCOPE='local-owned-empty-engine-shell-qualification-v8'

def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):result.update(block)
    return result.hexdigest()

def record(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>65536:
            raise ValueError('unsafe-private-record')
        raw=stream.read(65537)
    return json.loads(raw),hashlib.sha256(raw).hexdigest()

def write(path,value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def replace_pins(pins):
    tmp=STATE/('engine-v8-pins-'+str(os.getpid())+'.tmp');write(tmp,pins);os.replace(tmp,STATE/'owner-engine-shell-probe-v8-pins.json')

def capture(child,deadline):
    selector=selectors.DefaultSelector();buffers={child.stdout:bytearray(),child.stderr:bytearray()}
    for stream in buffers:selector.register(stream,selectors.EVENT_READ)
    failure=None
    try:
        while selector.get_map():
            if time.monotonic()>=deadline:raise TimeoutError('probe-deadline')
            for key,_ in selector.select(.02):
                data=os.read(key.fileobj.fileno(),65536)
                if not data:selector.unregister(key.fileobj);continue
                if len(buffers[key.fileobj])+len(data)>1048576:raise ValueError('output-budget')
                buffers[key.fileobj].extend(data)
        child.wait(timeout=max(.01,deadline-time.monotonic()))
    except (TimeoutError,ValueError,subprocess.TimeoutExpired,OSError):
        failure='probe-stream-incomplete'
    finally:
        selector.close()
        for stream in buffers:stream.close()
    return bytes(buffers[child.stdout]),bytes(buffers[child.stderr]),failure

def qualified(result):
    expected={'version':'agent-braid-owned-engine-shell-vm-probe-v2','status':'stopped',
        'enginePreflightValidated':True,'guestCompletionSeen':True,'vmCreated':True,'vmStarted':True,'vmStopped':True,'cleanupConfirmed':True,
        'consoleBudgetExceeded':False,'guestCpus':1,'guestMemoryBytes':4294967296,
        'networkDevices':0,'sharedDirectories':0,'checkpointExposed':False,
        'forecastCalls':0,'daemonState':'not-inspected','executionAuthorization':False}
    return (isinstance(result,dict) and all(type(result.get(k)) is type(v) and result[k]==v for k,v in expected.items())
        and type(result.get('wallNs')) is int and 0<=result['wallNs']<=135000000000
        and type(result.get('consoleBytes')) is int and 0<=result['consoleBytes']<=1048576)

def identities_match(value):
    if not isinstance(value,dict):return False
    states=[value.get('launchedIdentity'),value.get('preCrashIdentity')]
    for state in states:
        if not isinstance(state,dict) or state.get('scope')!='daemon-process-only-before-crash':return False
        for key,minimum in [('pid',2),('birthTicks',1),('cpuTicks',0)]:
            if type(state.get(key)) is not int or state[key]<minimum:return False
    return (states[0]['pid']==states[1]['pid'] and states[0]['birthTicks']==states[1]['birthTicks']
        and states[1]['cpuTicks']>=states[0]['cpuTicks'])

def engine_qualified(value):
    expected={'version':'agent-braid-owned-engine-shell-qualification-v2','status':'engine-ready-and-owned-daemon-crashed',
        'engineReady':True,'ownedDaemonCrash':True,'containersCreated':0,'forecastCalls':0,
        'workerConformanceAccepted':False,'fullDeploymentCostAccepted':False,'executionAuthorization':False,
        'daemonSignalSent':True,'imagesCreated':0,'imagesObserved':0,'containersObserved':0,'shellWaitStatus':137,'namespace':'fc2-engine-qualification','dataRoot':'/mnt/fc2-engine/docker',
        'socket':'/run/fc2-engine/docker.sock','cleanupConfirmed':False}
    return (isinstance(value,dict) and all(type(value.get(k)) is type(v) and value[k]==v for k,v in expected.items())
        and identities_match(value) and type(value.get('wallNs')) is int and 0<=value['wallNs']<=55000000000
        and type(value.get('readinessProbes')) is int and 1<=value['readinessProbes']<=200)

def guest_receipt(path):
    from engine_protocol import parse_console, parse_events
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>1048576:raise ValueError('unsafe-guest-console')
        text=stream.read(1048577).decode('utf-8',errors='replace')
        try:
            return parse_console(text)
        except (KeyError,ValueError,UnicodeDecodeError):
            events=parse_events(text)
            if events.get('status')!=b'incomplete' or events.get('daemonLogAvailable')!=b'yes':raise
            log=events.get('daemonLogBase64',b'')
            reported=int(events['daemonLogBytes'])
            truncated=events.get('daemonLogTruncated')==b'yes'
            decoded=base64.b64decode(log,validate=True)
            if len(decoded)>32768 or reported<0 or len(decoded)!=min(reported,32768) or truncated!=(reported>32768):
                raise ValueError('daemon-diagnostic-integrity')
            return {'version':'agent-braid-owned-engine-shell-diagnostic-v1','status':'incomplete',
                'diagnosticOnly':True,'engineReady':False,'ownedDaemonCrash':False,'executionAuthorization':False,
                'daemonExecIdentity':events.get('daemonExecIdentity')==b'yes','daemonLogAvailable':True,
                'daemonLogDrainComplete':events.get('daemonLogDrainComplete')==b'yes',
                'daemonLogBytes':reported,'daemonLogTruncated':truncated,'daemonLogBase64':log.decode('ascii'),
                'daemonLogText':decoded.decode('utf-8',errors='replace'),'readinessProbes':int(events.get('readinessProbes',b'0')),
                'signal':int(events.get('signal',b'0')),'shellWaitStatus':int(events.get('waitStatus',b'0'))}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    proposal=ROOT/'engine-shell-approval-request-v8.json';request,proposal_sha=record(proposal)
    if not args.execute:
        print(json.dumps({'status':'pending-owner-decision','proposalSha256':proposal_sha,'executionAuthorization':False}));return 0
    started=time.monotonic_ns();deadline=time.monotonic()+145
    cpu_started=resource.getrusage(resource.RUSAGE_SELF);children_started=resource.getrusage(resource.RUSAGE_CHILDREN)
    pins,_=record(STATE/'owner-engine-shell-probe-v8-pins.json');decision,decision_sha=record(STATE/'owner-engine-shell-probe-v8-decision.json')
    expected={'proposalSha256':proposal_sha,'decisionSha256':decision_sha,'scope':SCOPE}
    if set(pins)!={'version','approvals'} or pins['version']!='agent-braid-owned-engine-shell-pins-v2' or expected not in pins['approvals']:
        raise ValueError('owner-pin-absent')
    if (decision['proposalSha256']!=proposal_sha or decision['scope']!=SCOPE or decision['decision']!='admitted'
        or not decision['issuedAtUnixNs']<=time.time_ns()<decision['expiresAtUnixNs']):raise ValueError('owner-decision-not-current')
    claim=STATE/('engine-probe-v8-'+proposal_sha+'.json');output=ROOT/('execution-'+proposal_sha[:16])
    if claim.exists() or output.exists():raise ValueError('procedure-already-claimed')
    child=None;lease=None;result=None;cleaned=False;error=None;pin_removed=False;claimed=False;qualification=False;guest=None
    queued={'signal':None}
    def terminate(number,frame):
        queued['signal']=number
        if child is not None and child.poll() is None:
            try:os.killpg(child.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    handlers={number:signal.signal(number,terminate) for number in (signal.SIGINT,signal.SIGTERM)}
    try:
        for asset in request['assets']:
            path=Path(asset['path'])
            if path.is_symlink() or not path.is_file() or sha(path)!=asset['sha256']:raise ValueError('asset-identity-drift')
        subprocess.run(['codesign','--verify','--strict',str(ROOT/'owned-engine-probe')],check=True,capture_output=True,timeout=3)
        if queued['signal'] or time.monotonic()>deadline-140:raise ValueError('preflight-budget-or-interruption')
        lease=os.open(STATE/'engine-probe.lease',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        info=os.fstat(lease)
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600 or info.st_size>4096:raise ValueError('unsafe-vm-lease')
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);old=os.read(lease,4096)
        if old and json.loads(old).get('cleanupConfirmed') is not True:raise ValueError('vm-cleanup-pending')
        write(claim,{'proposalSha256':proposal_sha,'startedUnixNs':time.time_ns(),'scope':SCOPE});claimed=True
        output.mkdir(mode=0o700,exist_ok=False)
        write(output/'start.json',{'proposalSha256':proposal_sha,'decisionSha256':decision_sha,'startedUnixNs':time.time_ns()})
        os.lseek(lease,0,os.SEEK_SET);marker=b'{"cleanupConfirmed":false}';os.write(lease,marker);os.ftruncate(lease,len(marker));os.fsync(lease)
        fd=os.open(output/'guest-data.raw',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:os.ftruncate(fd,21474836480)
        finally:os.close(fd)
        if queued['signal'] or time.monotonic()>deadline-140:raise ValueError('interrupted-or-insufficient-launch-budget')
        child=subprocess.Popen([str(ROOT/'owned-engine-probe'),str(output),'--execute'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout,stderr,stream_error=capture(child,deadline-5)
        write(output/'captured.json',{'stdout':stdout.decode('utf-8',errors='replace'),'stderr':stderr.decode('utf-8',errors='replace'),'streamError':stream_error})
        if stream_error:raise ValueError(stream_error)
        result=json.loads(stdout) if stdout else None
        cleaned=bool(isinstance(result,dict) and result.get('cleanupConfirmed') is True and result.get('vmStopped') is True)
        guest=guest_receipt(output/'guest-console.txt')
        qualification=qualified(result) and engine_qualified(guest) and child.returncode==0
        if not qualification:error='qualification-incomplete'
    except BaseException:
        error='owned-engine-probe-incomplete'
    finally:
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=max(.01,min(2,deadline-time.monotonic())))
            except (ProcessLookupError,subprocess.TimeoutExpired):
                cleaned=False;error='owned-child-reap-unconfirmed'
        if claimed and child is None:cleaned=True
        try:
            if lease is not None and claimed:
                os.lseek(lease,0,os.SEEK_SET);marker=json.dumps({'cleanupConfirmed':cleaned}).encode();os.write(lease,marker);os.ftruncate(lease,len(marker));os.fsync(lease)
        except OSError:
            cleaned=False;error='lease-finalization-unconfirmed'
        finally:
            if lease is not None:
                try:fcntl.flock(lease,fcntl.LOCK_UN);os.close(lease)
                except OSError:error='lease-release-unconfirmed'
        if queued['signal']:error='interrupted'
        if time.monotonic()>deadline:error='total-budget-exceeded';qualification=False
        try:
            now,_=record(STATE/'owner-engine-shell-probe-v8-pins.json');now['approvals']=[p for p in now['approvals'] if p!=expected];replace_pins(now);pin_removed=True
        except (OSError,ValueError):error='pin-removal-unconfirmed'
        if output.exists():
            write(output/'result.json',{'proposalSha256':proposal_sha,'decisionSha256':decision_sha,'result':result,'guestResult':guest,'error':error,
                'qualified':qualification and error is None,'interruptedSignal':queued['signal'],
                'exit':None if child is None else child.returncode,'wallNs':time.monotonic_ns()-started,'cleanupConfirmed':cleaned,
                'checkpointExposed':False,'forecastCalls':0,'containersCreated':0,'claimPreserved':claimed,'pinRemoved':pin_removed,'executionAuthorization':False})
        if output.exists():
            cpu_finished=resource.getrusage(resource.RUSAGE_SELF);children_finished=resource.getrusage(resource.RUSAGE_CHILDREN)
            # After durable result publication/readback; the following parent
            # receipt's own publication remains explicitly outside its boundary.
            bound={name:sha(output/name) for name in ('start.json','captured.json','result.json') if (output/name).is_file()}
            write(output/'cost-publication.json',{'version':'agent-braid-owned-engine-publication-cost-v1',
                'proposalSha256':proposal_sha,'provenance':'authentic-local-empty-engine',
                'wallNsThroughResultReadback':time.monotonic_ns()-started,'receiptSha256':bound,
                'coordinatorCpuNs':round((cpu_finished.ru_utime+cpu_finished.ru_stime-cpu_started.ru_utime-cpu_started.ru_stime)*1e9),
                'waitedNativeHelperCpuNs':round((children_finished.ru_utime+children_finished.ru_stime-children_started.ru_utime-children_started.ru_stime)*1e9),
                'helperCpuScope':'native-host-helper-only-excludes-guest-vCPU',
                'coordinatorProcessLifetimePeakRssBytes':int(cpu_finished.ru_maxrss)*(1 if sys.platform=='darwin' else 1024),
                'gaps':['prior-artifact-provisioning-unallocated','host-virtualization-service-cpu','guest-containerd-cpu','no-worker-or-model','this-receipt-publication'],
                'workerCpuNs':None,'modelLoaded':False,'fullDeploymentCostAccepted':False,'executionAuthorization':False})
        for number,handler in handlers.items():signal.signal(number,handler)
    return 0 if qualification and cleaned and error is None and not queued['signal'] and time.monotonic()<=deadline else 2

if __name__=='__main__':raise SystemExit(main())
