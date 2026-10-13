# SPDX-License-Identifier: AGPL-3.0-only
"""One owned offline local Docker CPU worker; no implicit provisioning or queue."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import stat
import subprocess
import threading
import time
import uuid
from .forecast_data import ForecastError,MAX_BYTES,canonical,parse_record,keys,require,pin,digest,validate_window
from .forecast_chronos_inputs import translate_inputs
from .forecast_chronos import normalize_output
from .forecast_outputs import envelope
from .forecast_authority import require_artifact_approval
from .forecast_lease import WorkerLease

PROFILE={'memoryBytes':2147483648,'cpus':1,'threads':1,'scratchBytes':67108864,'pids':64,
         'coldDeadlineMs':30000,'residentDeadlineMs':1000,'activeRequests':1,'queuedRequests':0}
SOURCE_REVISION='0aba28e9360b6355d5a919596c90b16c25939f02'
CHECKPOINT_REVISION='29ec3766d36d6f73f0696f85560a422f50e8498c'

def validate_manifest(raw,*,artifact_verifier):
    manifest=parse_record(canonical(raw));keys(manifest,('version','imageId','checkpointDirectory','files','engineSocket',
                                                      'dependencyLockDigest','libraryVersion','sourceRevision','checkpointRevision','profile'))
    require_artifact_approval(manifest,artifact_verifier)
    require(manifest['version']=='agent-braid-chronos-cpu-manifest-v1','unsupported-model-manifest')
    require(manifest['imageId'].startswith('sha256:') and pin(manifest['imageId'][7:]),'mutable-image-reference')
    require(manifest['libraryVersion']=='2.3.2' and manifest['sourceRevision']==SOURCE_REVISION
            and manifest['checkpointRevision']==CHECKPOINT_REVISION,'unsupported-model-revision')
    pin(manifest['dependencyLockDigest']);require(canonical(manifest['profile'])==canonical(PROFILE),'unreviewed-worker-profile')
    keys(manifest['files'],('config.json','model.safetensors'))
    for value in manifest['files'].values():pin(value)
    for field in ('checkpointDirectory','engineSocket'):
        require(type(manifest[field]) is str and Path(manifest[field]).is_absolute()
                and not any(char in manifest[field] for char in ('\x00','\n',',')),'invalid-local-path')
    return deepcopy(manifest)

class DockerCPUWorker:
    def __init__(self,manifest,*,artifact_verifier):
        self.manifest=validate_manifest(manifest,artifact_verifier=artifact_verifier)
        self.artifact_verifier=artifact_verifier
        self.model_digest=digest(self.manifest);self.owner=uuid.uuid4().hex;self.container=None;self.process=None
        self.loaded=False;self.closed=False;self.lock=threading.Lock();self.stdout=bytearray();self.stderr_bytes=0
        self.create_unconfirmed=False
        self.engine=None;self.private_config=None
        self.lease=WorkerLease(self.owner,self.model_digest)

    def _checkpoint(self,deadline,cancellation):
        root=Path(self.manifest['checkpointDirectory']);require(root.is_dir() and not root.is_symlink(),'unsafe-checkpoint-directory')
        require(root.resolve()==root and root.stat().st_uid==os.getuid() and stat.S_IMODE(root.stat().st_mode)==0o700,'checkpoint-not-private')
        require({p.name for p in root.iterdir()}==set(self.manifest['files']),'unexpected-checkpoint-file')
        for name,expected in self.manifest['files'].items():
            path=root/name;info=path.lstat()
            require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o600
                    and info.st_size<=600*1024*1024,'unsafe-checkpoint-file')
            sha=hashlib.sha256()
            with path.open('rb') as stream:
                for chunk in iter(lambda:stream.read(1024*1024),b''):
                    self._checkpoint_deadline(deadline,cancellation);sha.update(chunk)
            require(sha.hexdigest()==expected,'checkpoint-hash-drift')
        socket=Path(self.manifest['engineSocket']);require(socket.is_socket(),'local-engine-unavailable')
        self.engine=shutil.which('docker');require(self.engine is not None,'docker-unavailable')

    def _argv(self,*args):
        # Explicit local socket overrides DOCKER_HOST/context; no daemon is pulled/provisioned.
        return [self.engine,'--host','unix://'+self.manifest['engineSocket'],*args]

    @staticmethod
    def _checkpoint_deadline(deadline,cancellation):
        if cancellation is not None and cancellation.is_set():raise ForecastError('cancelled')
        require(time.monotonic()<deadline,'deadline-exceeded')

    def _env(self):
        return {'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':os.environ.get('HOME','/tmp'),
                'LANG':'C.UTF-8','DOCKER_CONFIG':str(self.private_config)}

    def _docker(self,*args,timeout=5,deadline=None,cancellation=None):
        process=None;selector=selectors.DefaultSelector()
        try:
            if deadline is not None:self._checkpoint_deadline(deadline,cancellation)
            process=subprocess.Popen(self._argv(*args),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self._env())
            end=min(time.monotonic()+timeout,deadline or float('inf'));stdout=bytearray();stderr_size=0
            for stream in (process.stdout,process.stderr):selector.register(stream,selectors.EVENT_READ)
            while selector.get_map():
                self._checkpoint_deadline(end,cancellation)
                for key,_ in selector.select(min(.02,max(0,end-time.monotonic()))):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:selector.unregister(key.fileobj);continue
                    if key.fileobj is process.stdout:
                        require(len(stdout)+len(chunk)<=MAX_BYTES,'docker-output-budget');stdout.extend(chunk)
                    else:
                        stderr_size+=len(chunk);require(stderr_size<=MAX_BYTES,'docker-stderr-budget')
            self._checkpoint_deadline(end,cancellation)
            process.wait(timeout=max(.001,end-time.monotonic()))
            require(process.returncode==0,'docker-command-failed');return bytes(stdout)
        except (OSError,subprocess.TimeoutExpired):raise ForecastError('local-engine-unavailable') from None
        finally:
            selector.close()
            if process is not None:
                if process.poll() is None:process.kill();process.wait(timeout=2)
                for stream in (process.stdout,process.stderr):stream.close()

    def _inspect(self,*,deadline=None,cancellation=None):
        require(self.container is not None,'worker-not-created')
        raw=self._docker('container','inspect',self.container,'--format','{{json .}}',deadline=deadline,cancellation=cancellation)
        result=parse_record(raw.strip());labels=result.get('Config',{}).get('Labels',{})
        require(result.get('Id')==self.container and labels.get('agent-braid.forecast-owner')==self.owner
                and labels.get('agent-braid.forecast-manifest')==self.model_digest,'container-ownership-drift')
        return result

    def _read(self,deadline,cancellation):
        selector=selectors.DefaultSelector()
        for stream in (self.process.stdout,self.process.stderr):selector.register(stream,selectors.EVENT_READ)
        try:
            while True:
                if cancellation is not None and cancellation.is_set():raise ForecastError('cancelled')
                if time.monotonic()>=deadline:raise ForecastError('deadline-exceeded')
                if b'\n' in self.stdout:
                    line,_,remaining=self.stdout.partition(b'\n');self.stdout=bytearray(remaining)
                    return parse_record(bytes(line))
                require(len(self.stdout)<=MAX_BYTES,'worker-output-budget')
                for key,_ in selector.select(min(.02,max(0,deadline-time.monotonic()))):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        if key.fileobj is self.process.stdout:raise ForecastError('worker-exited')
                        continue
                    if key.fileobj is self.process.stdout:self.stdout.extend(chunk)
                    else:
                        self.stderr_bytes+=len(chunk);require(self.stderr_bytes<=MAX_BYTES,'worker-stderr-budget')
        finally:selector.close()

    def _write(self,payload,deadline,cancellation):
        data=memoryview(canonical(payload)+b'\n');fd=self.process.stdin.fileno()
        os.set_blocking(fd,False);selector=selectors.DefaultSelector();selector.register(fd,selectors.EVENT_WRITE)
        try:
            while data:
                self._checkpoint_deadline(deadline,cancellation)
                if not selector.select(min(.02,max(0,deadline-time.monotonic()))):continue
                try:data=data[os.write(fd,data):]
                except BlockingIOError:continue
        except (BrokenPipeError,OSError):raise ForecastError('worker-exited') from None
        finally:selector.close()

    def _start(self,deadline,cancellation):
        import tempfile
        require_artifact_approval(self.manifest,self.artifact_verifier)
        self.lease.acquire()
        self._checkpoint_deadline(deadline,cancellation);self._checkpoint(deadline,cancellation)
        self.config_scope=tempfile.TemporaryDirectory(prefix='agent-braid-forecast-docker-')
        self.private_config=Path(self.config_scope.name)
        require(self._docker('image','inspect',self.manifest['imageId'],'--format','{{.Id}}',deadline=deadline,cancellation=cancellation).strip().decode()==self.manifest['imageId'],'image-identity-drift')
        remaining=max(.01,min(5,deadline-time.monotonic()))
        require(os.getuid()!=0,'worker-requires-nonroot-owner')
        self.create_unconfirmed=True
        raw=self._docker('container','create','--name=agent-braid-forecast-'+self.owner,'--pull=never','--network=none','--read-only','--user='+str(os.getuid())+':'+str(os.getgid()),
             '--cap-drop=ALL','--security-opt=no-new-privileges','--memory=2147483648','--memory-swap=2147483648',
             '--cpus=1','--pids-limit=64','--tmpfs=/tmp:rw,nosuid,nodev,size=67108864',
             '--mount','type=bind,src='+self.manifest['checkpointDirectory']+',dst=/model,readonly',
             '--label','agent-braid.forecast-owner='+self.owner,'--label','agent-braid.forecast-manifest='+self.model_digest,
             '--env','OMP_NUM_THREADS=1','--env','MKL_NUM_THREADS=1','--env','HF_HUB_OFFLINE=1',
             '--env','TRANSFORMERS_OFFLINE=1','--env','HF_HOME=/tmp/hf','--env','TOKENIZERS_PARALLELISM=false',
             '--env','CUDA_VISIBLE_DEVICES=',self.manifest['imageId'],timeout=remaining,deadline=deadline,cancellation=cancellation)
        cid=raw.strip().decode('ascii');pin(cid);self.container=cid;self.create_unconfirmed=False
        inspected=self._inspect(deadline=deadline,cancellation=cancellation);config=inspected['HostConfig']
        require(config.get('Memory')==2147483648 and config.get('MemorySwap')==2147483648
                and config.get('NanoCpus')==1000000000 and config.get('PidsLimit')==64
                and config.get('NetworkMode')=='none' and config.get('ReadonlyRootfs') is True
                and inspected['Config'].get('User')==str(os.getuid())+':'+str(os.getgid())
                and 'ALL' in config.get('CapDrop',[]) and 'no-new-privileges' in config.get('SecurityOpt',[])
                and inspected.get('Image')==self.manifest['imageId'],'worker-enforcement-unavailable')
        mounts=inspected.get('Mounts',[])
        require(config.get('Tmpfs')=={'/tmp':'rw,nosuid,nodev,size=67108864'}
                and len(mounts)==1 and mounts[0].get('Type')=='bind'
                and mounts[0].get('Source')==self.manifest['checkpointDirectory']
                and mounts[0].get('Destination')=='/model' and mounts[0].get('RW') is False,'worker-mount-enforcement-unavailable')
        self._checkpoint_deadline(deadline,cancellation)
        self.process=subprocess.Popen(self._argv('container','start','--attach','--interactive',cid),
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=self._env(),start_new_session=True)
        readiness=self._read(deadline,cancellation)
        require(readiness=={'version':'agent-braid-worker-ready-v1','memoryMax':2147483648,'swapMax':0,
                            'cpuQuota':100000,'cpuPeriod':100000,'pidsMax':64},'worker-enforcement-unavailable')
        self._write({'command':'load','files':self.manifest['files'],'dependencyLockDigest':self.manifest['dependencyLockDigest']},deadline,cancellation)
        loaded=self._read(deadline,cancellation)
        require(loaded.get('status')=='loaded' and loaded.get('libraryVersion')=='2.3.2','worker-load-failed')
        self.loaded=True

    def forecast(self,window,horizon,*,deadline=None,cancellation=None):
        started=time.monotonic_ns();window=validate_window(window)
        if not self.lock.acquire(blocking=False):
            return envelope(window,horizon,model_digest=self.model_digest,status='unavailable',reasons=('worker-busy',),started_ns=started)
        try:
            require(not self.closed,'worker-closed')
            if cancellation is not None and cancellation.is_set():raise ForecastError('cancelled')
            cold=not self.loaded
            if cold:self._start(min(deadline or float('inf'),time.monotonic()+30),cancellation)
            resident_deadline=min(deadline or float('inf'),time.monotonic()+1)
            require_artifact_approval(self.manifest,self.artifact_verifier)
            self._write({'command':'predict','inputs':translate_inputs(window,horizon),'horizon':horizon},resident_deadline,cancellation)
            result=self._read(resident_deadline,cancellation)
            require(result.get('status')=='forecast','worker-prediction-failed')
            output=normalize_output(window,horizon,result['quantiles'],result['median'],model_digest=self.model_digest,started_ns=started)
            output['costs']['rssBytes']=result['rssBytes'];output['costs']['rssReason']=None
            output['costs']['rssScope']='process-lifetime-peak-linux'
            output['costs']['containerMemoryBytes']=result['containerMemoryBytes'];output['costs']['containerMemoryReason']=None
            output['costs']['modelCpuNs']=result['modelCpuNs'];output['costs']['modelCpuReason']=None
            output['packetDigest']=digest({k:v for k,v in output.items() if k!='packetDigest'})
            from .forecast_outputs import validate_forecast
            return validate_forecast(output,window,horizon)
        except (ForecastError,OSError,ValueError,KeyError,TypeError,IndexError) as exc:
            reason=str(exc) if isinstance(exc,ForecastError) else 'worker-failed'
            if reason not in ('cancelled','deadline-exceeded','worker-busy','worker-closed','checkpoint-hash-drift',
                              'local-engine-unavailable','worker-enforcement-unavailable','worker-exited'):
                reason='worker-failed'
            status='cancelled' if reason=='cancelled' else 'timed-out' if reason=='deadline-exceeded' else 'refused'
            try:self._close_owned()
            except (ForecastError,OSError,subprocess.TimeoutExpired):reason='owned-container-cleanup-pending';status='refused'
            return envelope(window,horizon,model_digest=self.model_digest,status=status,reasons=(reason,),started_ns=started)
        finally:self.lock.release()

    def _close_owned(self):
        try:
            require(not self.create_unconfirmed,'owned-container-cleanup-pending')
            if self.container is not None:
                self._inspect();self._docker('container','rm','--force',self.container)
                self.container=None
        finally:
            self.loaded=False
            if self.process is not None:
                try:self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=2)
                for stream in (self.process.stdin,self.process.stdout,self.process.stderr):stream.close()
                self.process=None
            if hasattr(self,'config_scope'):self.config_scope.cleanup()
            self.lease.release(cleanup_confirmed=self.container is None and not self.create_unconfirmed)

    def close(self):
        require(self.lock.acquire(blocking=False),'worker-in-use')
        try:self._close_owned();self.closed=True
        finally:self.lock.release()
