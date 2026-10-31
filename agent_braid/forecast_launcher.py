# SPDX-License-Identifier: AGPL-3.0-only
"""Private launcher/root-broker wiring. Import never forks, installs or activates.

Every native entry remains blocked by the immutable profile readiness gate.
Transport/claimed filter hashes do not create authority: the root actor's native
verifier must bind the exact launcher/source/task before accepting its listener.
"""
import array
import json
import os
from pathlib import Path
import select
import secrets
import socket
import signal
import struct
import sys
import time

from .forecast_data import pin,require
from .forecast_exec_gate import ExecPermitLedger,NativeExecBroker,filter_sha256,install_on_current_task
from .forecast_operator_bridge import peer,send,receive

MAX_HANDOFF=2048
VERSION='fc1-exec-listener-v1'


def send_frame(sock,value,fd=None,*,account_io=None):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    require(len(raw)<=MAX_HANDOFF,'launcher-frame-cap')
    ancillary=[] if fd is None else [(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))]
    require(sock.sendmsg([raw],ancillary)==len(raw),'launcher-short-send')
    if account_io:account_io(len(raw))


def receive_frame(sock,*,with_fd=False,account_io=None):
    """Close every received descriptor on any malformed/truncated handoff."""
    values=array.array('i');fds=[]
    try:
        raw,ancillary,flags,_=sock.recvmsg(MAX_HANDOFF+1,socket.CMSG_SPACE(values.itemsize*8),
                                        getattr(socket,'MSG_CMSG_CLOEXEC',0))
        unsupported=False
        for level,kind,data in ancillary:
            if level!=socket.SOL_SOCKET or kind!=socket.SCM_RIGHTS:
                unsupported=True;continue
            values=array.array('i')
            values.frombytes(data[:len(data)-len(data)%values.itemsize]);fds.extend(values)
            if len(data)%values.itemsize:unsupported=True
        if account_io:account_io(len(raw)+sum(len(data) for _,_,data in ancillary))
        for fd in fds:os.set_inheritable(fd,False)
        require(raw and len(raw)<=MAX_HANDOFF and not unsupported and
                not flags&(socket.MSG_TRUNC|socket.MSG_CTRUNC) and len(fds)==int(with_fd),
                'launcher-truncated-or-descriptors')
        from research.lab.model import loads
        value=loads(raw.decode());require(type(value) is dict,'launcher-object')
        fd=fds[0] if with_fd else None
        fds=[]
        return value,fd
    finally:
        for fd in fds:os.close(fd)


def handoff_current_task(profile,phase,*,role='worker',channel=None):
    """Install/transfer before the trusted worker dispatches any Git or forks.

    Worker uses only the root-mounted socket. Operator supplies its private
    inherited control socket to the separately supervised root actor.
    """
    require(profile.manifest()['execAdmissionEnforced'] is True,'launcher-native-readiness-pending')
    require(sys.platform=='linux' and role in ('worker','operator'),'launcher-platform-role')
    own=channel is None
    require(own and role=='worker' or not own and role=='operator','launcher-channel-role')
    sock=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET) if own else channel
    fd=None
    try:
        sock.settimeout(1);sock.set_inheritable(False)
        if own:sock.connect('/exec-gate.sock')
        peer(sock,uid=0)
        hello={'version':VERSION,'profileIdentity':profile.identity,'phase':phase,
               'role':role,'pid':os.getpid(),'filterSha256':filter_sha256()}
        send_frame(sock,hello)
        challenge,_=receive_frame(sock)
        require(set(challenge)=={'challenge','profileIdentity'} and
                challenge['profileIdentity']==profile.identity,'launcher-challenge-binding')
        pin(challenge['challenge'])
        fd=install_on_current_task()
        send_frame(sock,{**hello,'challenge':challenge['challenge']},fd)
        os.close(fd);fd=None
        # Root independently checks closure; this message alone is not proof.
        send_frame(sock,{'released':challenge['challenge']})
        ack,_=receive_frame(sock)
        require(set(ack)=={'accepted','profileIdentity'} and ack['accepted'] is True
                and ack['profileIdentity']==profile.identity,'launcher-not-accepted')
    finally:
        if fd is not None:os.close(fd)
        if own:sock.close()


class RootBrokerActor:
    """One root process owns the permit ledger/listeners; no worker authority API.

    verifier is the operator's native fact provider, not a callable selected in
    frames. A socket/listener is already prepared by the authorized supervisor.
    This actor does not start systemd units, accept source consent, or load BPF.
    """
    def __init__(self,profile,origin_ns,*,verifier,clock=time.monotonic_ns,
                 bootstrap_receipt=None,bootstrap_authority=None):
        self.profile=profile;self.verifier=verifier;self.clock=clock
        self.ledger=ExecPermitLedger(profile,origin_ns)
        self.bootstrap_binding=None;self.bootstrap_authority=bootstrap_authority
        if bootstrap_receipt is not None or bootstrap_authority is not None:
            from .forecast_bootstrap import adopt_bootstrap
            self.bootstrap_binding=adopt_bootstrap(profile,self.ledger,bootstrap_receipt,
                authority=bootstrap_authority,now_ns=clock())
            self.bootstrap_operator_pid=bootstrap_receipt['records'][-1]['pid']
            self.bootstrap_operator_start=bootstrap_receipt['records'][-1]['processStartTicks']
            verifier.phase_budget(0)  # Include bootstrap reads; never reset prepare.
        self.broker=NativeExecBroker(self.ledger,validate_task=verifier.validate_task,clock=clock,account_io=verifier.account)
        self.sequence=0;self.tokens=[];self.entries={};self.worker_tokens={};self.stopped=False

    def accept_launcher(self,sock,*,role):
        NativeExecBroker.guard()
        received=None
        try:
            sock.settimeout(1)
            hello,extra=receive_frame(sock,account_io=self.verifier.account)
            expected={'version','profileIdentity','phase','role','pid','filterSha256'}
            require(set(hello)==expected and hello['version']==VERSION and
                    hello['profileIdentity']==self.profile.identity and hello['role']==role
                    and hello['filterSha256']==filter_sha256(),'launcher-hello')
            if role=='operator':
                require(self.bootstrap_binding is not None and hello['pid']==self.bootstrap_operator_pid,
                        'launcher-operator-bootstrap-unbound')
            uid=self.profile.uid if role=='worker' else 0
            peer(sock,uid=uid,pid=hello['pid'])
            # Identity comes from the native verifier's kernel/source readback.
            if role=='worker':
                entry=self.entries.get(hello['phase'])
                require(entry is not None and entry['pid'] is None,'launcher-start-permit-required')
            identity=self.verifier.launcher_identity(hello['pid'],role,hello['phase'])
            if role=='operator':
                require(identity['start']==self.bootstrap_operator_start,'launcher-bootstrap-pid-reused')
            if role=='worker':
                entry['pid']=identity['pid']
                self.ledger.records[entry['ticket']]['pid']=identity['pid']
            nonce=secrets.token_hex(32)
            send_frame(sock,{'challenge':nonce,'profileIdentity':self.profile.identity},account_io=self.verifier.account)
            frame,received=receive_frame(sock,with_fd=True,account_io=self.verifier.account)
            require(frame=={**hello,'challenge':nonce},'launcher-handoff-binding')
            token=self.broker.register(received,identity=identity,
                                       verify_listener=self.verifier.verify_listener)
            released,_=receive_frame(sock,account_io=self.verifier.account)
            require(released=={'released':nonce} and self.verifier.listener_released(identity) is True,
                    'launcher-listener-not-exclusive')
            self.tokens.append(token)
            if role=='worker':self.worker_tokens[token]=identity
            send_frame(sock,{'accepted':True,'profileIdentity':self.profile.identity},account_io=self.verifier.account)
            return token
        except BaseException:
            self.stop();raise
        finally:
            if received is not None:os.close(received)

    def command(self,frame):
        try:
            require(not self.stopped and type(frame) is dict and
                    frame.get('profileIdentity')==self.profile.identity and
                    type(frame.get('sequence')) is int and frame['sequence']==self.sequence+1,
                    'root-gate-command-binding')
            self.sequence+=1
            event=frame.get('event')
            base={'profileIdentity','sequence','event'}
            if event=='workerStart':
                require(set(frame)==base|{'phase'} and frame['phase'] in ('prepare','verify','terminal'),
                        'root-gate-command-fields')
                phase=frame['phase'];index={'prepare':0,'verify':3,'terminal':4}[phase]
                require(self.ledger.phase==index and phase not in self.entries,'root-gate-start-phase')
                ticket=self.ledger.reserve('manager-entry',index,None,now_ns=self.clock(),
                                           worker_entry=True,expected_phase=index)
                self.ledger.finish(ticket,continued=True)
                self.entries[phase]={'ticket':ticket,'pid':None}
                result={'workerStartReserved':phase,'ticket':ticket}
            elif event=='phase':
                require(set(frame)==base|{'index','deadlineNs'},'root-gate-command-fields')
                self.retire_empty()
                if frame['index']==self.ledger.phase:
                    require(frame['deadlineNs']==self.ledger.deadline,'root-gate-deadline-reset')
                else:
                    self.broker.transition(frame['index'],frame['deadlineNs'],
                                           verify_quiescent=self.verifier.quiescent)
                    self.verifier.phase_budget(frame['index'])
                result={'phaseIndex':self.ledger.phase,'deadlineNs':self.ledger.deadline}
            elif event=='summary':
                require(set(frame)==base,'root-gate-command-fields')
                result={'attemptsConsumed':len(self.ledger.records),'failed':self.ledger.failed,
                        'nativeCoverageAccepted':False,'provider':self.verifier.metrics()}
            elif event=='page':
                require(set(frame)==base|{'offset'},'root-gate-command-fields')
                offset=frame['offset'];require(type(offset) is int and 0<=offset<=len(self.ledger.records),
                                               'root-gate-page')
                result={'offset':offset,'records':[dict(r) for r in self.ledger.records[offset:offset+64]]}
            elif event=='stop':
                require(set(frame)==base,'root-gate-command-fields')
                self.stop();result={'stopped':True}
            else:require(False,'root-gate-command-event')
            response={'profileIdentity':self.profile.identity,'sequence':self.sequence,**result}
            self.verifier.account(len(json.dumps(frame).encode())+len(json.dumps(response).encode()))
            return response
        except BaseException:
            self.stop();raise

    def serve(self,control,launcher_listener):
        """Run only in a dedicated root child; handles one inherited controller."""
        NativeExecBroker.guard()
        require(self.profile.manifest()['execAdmissionEnforced'] is True,'root-gate-native-readiness-pending')
        require(self.bootstrap_binding is not None,'root-gate-prior-bootstrap-required')
        control.settimeout(1);launcher_listener.settimeout(1)
        try:
            self.accept_launcher(control,role='operator')
            while not self.stopped:
                require(not self.ledger.failed and self.clock()<min(self.ledger.whole_deadline,
                        self.ledger.deadline if self.ledger.phase>=0 else self.ledger.whole_deadline),
                        'root-gate-supervision-expired')
                ready,_,_=select.select([control,launcher_listener],[],[],.01)
                if control in ready:
                    peer(control,uid=0,pid=self.verifier.controller_pid)
                    frame=receive(control);send(control,self.command(frame))
                if launcher_listener in ready:
                    sock,_=launcher_listener.accept()
                    with sock:self.accept_launcher(sock,role='worker')
                self.retire_empty()
                for token in list(self.tokens):
                    if self.ledger.phase>=0:self.broker.serve_one(token)
        finally:self.stop()

    def retire_empty(self):
        for token,identity in list(self.worker_tokens.items()):
            if self.verifier.empty(identity):
                self.broker.retire(token,verify_empty=self.verifier.empty)
                del self.worker_tokens[token];self.tokens.remove(token)

    def stop(self):
        self.stopped=True;self.ledger.failed=True;self.broker.close()
        if self.bootstrap_authority is not None:self.bootstrap_authority.channel.close()


class RootGateClient:
    """Source-bound root controller over its private inherited channel."""
    def __init__(self,profile,channel,*,child_pidfd=None,child_pid=None,deadline_ns=None):
        self.identity=profile.identity;self.channel=channel;self.sequence=0;self.child_pidfd=child_pidfd;self.child_pid=child_pid
        self.deadline_ns=deadline_ns;self.cleanup_confirmed=False;self.exit_status=None;self.account_io=None
        self.closed=False;self.stop_succeeded=False
        channel.settimeout(1);channel.set_inheritable(False)

    def call(self,event,**fields):
        require(self.child_pidfd is not None and not select.select([self.child_pidfd],[],[],0)[0],
                'root-gate-child-not-live')
        peer(self.channel,uid=0)
        self.sequence+=1
        request={'profileIdentity':self.identity,'sequence':self.sequence,'event':event,**fields}
        send(self.channel,request)
        result=receive(self.channel)
        require(result.get('profileIdentity')==self.identity and result.get('sequence')==self.sequence,
                'root-gate-response-binding')
        if self.account_io:self.account_io(len(json.dumps(request).encode())+len(json.dumps(result).encode()))
        return result

    def phase(self,index,deadline_ns):
        result=self.call('phase',index=index,deadlineNs=deadline_ns)
        self.deadline_ns=result['deadlineNs']
        return result
    def summary(self):return self.call('summary')
    def reserve_worker_start(self,phase):return self.call('workerStart',phase=phase)
    def page(self,offset):return self.call('page',offset=offset)
    def phase_receipt(self,index):
        summary=self.summary();count=summary['attemptsConsumed']
        require(type(count) is int and 0<=count<=65536,'root-gate-receipt-cap')
        rows=[]
        for offset in range(0,count,64):
            page=self.page(offset)
            require(page['offset']==offset and len(page['records'])==min(64,count-offset),'root-gate-receipt-page')
            rows.extend(r for r in page['records'] if r['phaseIndex']==index)
        return {'summary':summary,'records':rows}

    def stop(self):
        if self.closed:
            require(self.stop_succeeded and self.cleanup_confirmed and self.exit_status==0,
                    'root-gate-cleanup-unconfirmed')
            return {'stopped':True}
        try:
            result=self.call('stop')
        finally:
            self.closed=True
            descriptor=self.child_pidfd
            channel_error=None
            try:self.channel.close()
            except BaseException as error:channel_error=error
            try:
                if self.child_pid is not None and descriptor is not None:
                    # Cleanup grace consumes the current phase, never extends it.
                    deadline=min(time.monotonic_ns()+10**9,self.deadline_ns or time.monotonic_ns())
                    status=_reap_owned_child(self.child_pid,deadline)
                    if status is None:
                        try:signal.pidfd_send_signal(descriptor,signal.SIGKILL)
                        except ProcessLookupError:pass
                        status=_reap_owned_child(self.child_pid,deadline)
                    self.cleanup_confirmed=status is not None
                    if self.cleanup_confirmed:self.exit_status=os.waitstatus_to_exitcode(status)
                    require(self.cleanup_confirmed,'root-gate-cleanup-unconfirmed')
                    require(self.exit_status==0,'root-gate-child-failed')
            finally:
                if descriptor is not None:os.close(descriptor)
                self.child_pidfd=None
            if channel_error is not None:raise channel_error
        self.stop_succeeded=True
        return result


def _reap_owned_child(pid,deadline_ns):
    """One final nonblocking reap even at expiry; unknown cleanup never succeeds."""
    while True:
        found,status=os.waitpid(pid,os.WNOHANG)
        if found==pid:return status
        if time.monotonic_ns()>=deadline_ns:return None
        time.sleep(min(.001,max(0,(deadline_ns-time.monotonic_ns())/10**9)))


def _close_channels(*channels):
    failure=None
    for channel in channels:
        try:channel.close()
        except BaseException as error:
            if failure is None:failure=error
    if failure is not None:raise failure


class NativeLauncherVerifier:
    """Root-owned kernel/source readback for only four explicitly owned peers.

    This verifies source/entry/FD custody, not arbitrary seccomp bytecode or native
    inheritance. The immutable profile still cannot claim enforced admission.
    """
    def __init__(self,profile,*,controller_pid,view):
        self.profile=profile;self.controller_pid=controller_pid;self.view=view
        self.identities={};self.helpers=set();self.phase=-1;self.read_origin=view.bytes_read
        self.view.remaining=1024**3;self.cpu_origin=time.process_time_ns();self.phase_reads=[]

    def account(self,count):self.view.account(count)

    def phase_budget(self,index):
        require(index==self.phase+1,'launcher-read-budget-phase')
        if index>0:
            self.phase_reads.append({'phaseIndex':self.phase,'bytes':self.view.bytes_read-self.read_origin})
            self.read_origin=self.view.bytes_read;self.view.remaining=1024**3
        # Bootstrap readback remains charged to prepare; no first-phase reset.
        self.phase=index

    def metrics(self):
        return {'processCpuNs':time.process_time_ns()-self.cpu_origin,
                'instrumentedReadBytes':self.view.bytes_read,
                'completedReadPhases':[dict(r) for r in self.phase_reads],
                'currentPhaseReadBytes':self.view.bytes_read-self.read_origin,
                'phaseReadCapBytes':1024**3,'nativeCoverageAccepted':False}

    def launcher_identity(self,pid,role,phase):
        from .forecast_native import mount_rows
        from .forecast_admission import source_digest
        self.view.guard();require(role in ('operator','worker'),'launcher-role')
        require(phase in ('prepare','verify','terminal'),'launcher-phase')
        before=self.view.state(pid)
        stem='fc1'+self.profile.identity
        worker=role=='worker'
        unit=stem+'-'+(phase if worker else 'operator')+'.service'
        expected='/'+stem+'.slice/'+((stem+'-workers.slice/') if worker else (stem+'-root.slice/'))+unit
        require(self.view.read(f'/proc/{pid}/cgroup').decode().strip()=='0::'+expected,
                'launcher-cgroup')
        status=self.view.read(f'/proc/{pid}/status').decode()
        uid=self.profile.uid if worker else 0
        import re
        values=re.findall(r'^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)$',status,re.M)
        require(len(values)==1 and all(int(v)==uid for v in values[0]),'launcher-kernel-uid')
        prefix='/opt/agent-braid/source' if worker else '/opt/agent-braid/operator/source'
        interpreter='/opt/agent-braid/bin/python3' if worker else '/opt/agent-braid/operator/python'
        script=prefix+'/scripts/fc1_admission_worker.py' if worker else '/opt/agent-braid/operator/admission.py'
        argv=[interpreter,'-I','-S',script,self.profile.identity]+([phase] if worker else ['operator'])
        require(self.view.read(f'/proc/{pid}/cmdline')==b'\0'.join(x.encode() for x in argv)+b'\0',
                'launcher-command')
        self.view.executable(pid,self.profile.worker_sha256 if worker else self.profile.operator_sha256)
        root=Path(f'/proc/{pid}/root');source=root/prefix.lstrip('/')
        mounts=mount_rows(self.view.read(f'/proc/{pid}/mountinfo'))
        covering=[(p,r) for p,r in mounts.items() if prefix==p or prefix.startswith(p.rstrip('/')+'/')]
        require(covering and 'ro' in max(covering,key=lambda x:len(x[0]))[1]['mount'],'launcher-source-not-readonly')
        def read(path):
            current=root
            anchor=source if path.is_relative_to(source) else root/'opt/agent-braid/operator'
            device=anchor.stat().st_dev
            for part in path.relative_to(root).parts:
                current=current/part
                require(not current.is_symlink(),'launcher-source-path')
                if current.is_relative_to(anchor):
                    require(current.stat().st_dev==device,'launcher-source-device')
            return self.view.read(path,4*1024**2)
        require(source_digest(source,reader=read)==self.profile.source_digest,'launcher-source-pin')
        if not worker:
            import hashlib
            covering=[(p,r) for p,r in mounts.items() if script==p or script.startswith(p.rstrip('/')+'/')]
            require(covering and 'ro' in max(covering,key=lambda x:len(x[0]))[1]['mount'],
                    'launcher-operator-entry-not-readonly')
            raw=read(root/script.lstrip('/'))
            require(hashlib.sha256(raw).hexdigest()==self.profile.operator_entry_sha256,'launcher-operator-entry-pin')
        after=self.view.state(pid)
        require(before['start']==after['start'],'launcher-pid-reused')
        identity={'pid':pid,'start':after['start'],'role':role,'phase':phase,'cgroup':expected}
        require(len(self.identities)<4 and pid not in self.identities,'launcher-registration-count')
        self.identities[pid]=identity
        return dict(identity)

    def _same(self,identity):
        pid=identity['pid']
        require(self.identities.get(pid)==identity and self.view.state(pid)['start']==identity['start'],
                'launcher-stale-identity')
        return pid

    def verify_listener(self,fd,identity,filter_digest):
        self.view.guard();pid=self._same(identity)
        require(filter_digest==filter_sha256() and os.readlink(f'/proc/self/fd/{fd}')=='anon_inode:seccomp notify',
                'launcher-listener-kind')
        status=self.view.read(f'/proc/{pid}/status').decode()
        import re
        require(re.findall(r'^Seccomp:\s+(\d+)$',status,re.M)==['2'] and
                re.findall(r'^NoNewPrivs:\s+(\d+)$',status,re.M)==['1'],'launcher-filter-status')
        return True

    def listener_released(self,identity):
        self.view.guard();pid=self._same(identity)
        import itertools
        descriptors=list(itertools.islice(Path(f'/proc/{pid}/fd').iterdir(),129))
        require(len(descriptors)<=128,'launcher-fd-cap')
        require(all(os.readlink(path)!='anon_inode:seccomp notify' for path in descriptors),
                'launcher-original-listener-open')
        tasks=list(itertools.islice(Path(f'/proc/{pid}/task').iterdir(),2))
        require(len(tasks)==1,'launcher-threads-before-handoff')
        children=self.view.read(f'/proc/{pid}/task/{pid}/children').decode().split()
        require(not children if identity['role']=='worker' else set(map(int,children))<=self.helpers,
                'launcher-unregistered-child')
        self._same(identity)
        return True

    def validate_task(self,pid,identity):
        self.view.guard();self._same(identity)
        return self.view.read(f'/proc/{pid}/cgroup').decode().strip()=='0::'+identity['cgroup']

    def empty(self,identity):
        self.view.guard()
        require(identity['role']=='worker','launcher-operator-not-retirable')
        path=Path('/sys/fs/cgroup')/identity['cgroup'].lstrip('/')
        rows=dict(line.split() for line in self.view.read(path/'cgroup.events').decode().splitlines())
        return rows.get('populated')=='0'

    def quiescent(self):
        self.view.guard()
        for identity in self.identities.values():
            if identity['role']=='operator':continue
            path=Path('/sys/fs/cgroup')/identity['cgroup'].lstrip('/')
            rows=dict(line.split() for line in self.view.read(path/'cgroup.events').decode().splitlines())
            require(rows.get('populated')=='0' or rows.get('frozen')=='1','launcher-not-quiescent')
        return True


def spawn_root_actor(profile,origin_ns,launcher_listener,*,bootstrap_receipt=None,bootstrap_authority=None):
    """Future explicit root bootstrap before threads/children; never invoked here.

    Takes ownership of the prepared listener after a successful fork; the parent
    closes its copy before handoff. Units come from the authorized supervisor. No image,
    systemd unit or probe is created/activated by this function.
    """
    require(profile.manifest()['execAdmissionEnforced'] is True,'root-gate-native-readiness-pending')
    NativeExecBroker.guard()
    from .forecast_bootstrap import RootBootstrapAuthority
    require(type(bootstrap_authority) is RootBootstrapAuthority and
            bootstrap_authority.identity==profile.identity and bootstrap_receipt is not None,
            'root-gate-prior-bootstrap-required')
    require(len(list(Path('/proc/self/task').iterdir()))==1 and
            not Path(f'/proc/self/task/{os.getpid()}/children').read_text().strip(),
            'root-gate-pristine-launcher-required')
    parent,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET)
    for sock in (parent,child):sock.set_inheritable(False)
    # Retain only stdio, the private controller and the prepared listener in root.
    try:
        inherited=[int(name) for name in os.listdir('/proc/self/fd')]
        require(len(inherited)<=128,'root-gate-inherited-fd-cap')
        controller=os.getpid();pid=os.fork()
    except BaseException:
        _close_channels(parent,child);raise
    if pid==0:
        parent.close()
        exit_code=1
        try:
            import errno
            keep={0,1,2,child.fileno(),launcher_listener.fileno(),bootstrap_authority.channel.fileno()}
            for descriptor in inherited:
                if descriptor not in keep:
                    try:os.close(descriptor)
                    except OSError as error:
                        if error.errno!=errno.EBADF:raise
            from .forecast_native import KernelView
            view=KernelView()
            verifier=NativeLauncherVerifier(profile,controller_pid=controller,view=view)
            verifier.helpers.add(os.getpid())
            bootstrap_authority.view=view
            actor=RootBrokerActor(profile,origin_ns,verifier=verifier,
                                  bootstrap_receipt=bootstrap_receipt,bootstrap_authority=bootstrap_authority)
            actor.serve(child,launcher_listener)
            exit_code=0
        finally:os._exit(exit_code)
    pidfd=None
    try:
        # Ownership transfers to the actor, including the accepting socket.
        _close_channels(child,launcher_listener,bootstrap_authority.channel)
        pidfd=os.pidfd_open(pid)
        handoff_current_task(profile,'prepare',role='operator',channel=parent)
        return RootGateClient(profile,parent,child_pidfd=pidfd,child_pid=pid,
                              deadline_ns=origin_ns+sum(p.wall_seconds for p in profile.limits)*10**9),pid
    except BaseException as failure:
        try:parent.close()
        except BaseException as error:failure.add_note('Controller close failed: '+type(error).__name__)
        # SIGKILL is delivered to this still-owned, unreaped child only.
        try:
            try:os.kill(pid,9)
            except ProcessLookupError:pass
            deadline=min(time.monotonic_ns()+10**9,origin_ns+profile.limits[0].wall_seconds*10**9)
            require(_reap_owned_child(pid,deadline) is not None,'root-gate-bootstrap-cleanup-unconfirmed')
        finally:
            if pidfd is not None:os.close(pidfd)
        raise


def prepare_initial_worker(profile,origin_ns,gate_client):
    """Reserve the fixed manager entry BEFORE the supervisor starts that unit.

    Returns an intent/consumed permit only. It does not call a manager, issue a
    runtime grant, activate units or assert that the manager honoured the intent.
    """
    require(profile.manifest()['execAdmissionEnforced'] is True,'launcher-native-readiness-pending')
    require(type(gate_client) is RootGateClient and gate_client.identity==profile.identity,
            'launcher-root-gate-required')
    deadline=origin_ns+profile.limits[0].wall_seconds*10**9
    gate_client.phase(0,deadline)
    permit=gate_client.reserve_worker_start('prepare')
    return {'unit':'fc1'+profile.identity+'-prepare.service','permit':permit,'deadlineNs':deadline}


def reconcile_exec_permits(events,receipt):
    """Every observed exec needs a preceding distinct root permission.

    Unused/failed exec syscalls keep their consumed denominator. A census cannot
    create a permission retrospectively. Initial manager entries need their own
    prior permit/verified task binding, including the outer operator bootstrap.
    """
    require(receipt['summary']['failed'] is False,'launcher-permit-ledger-failed')
    available=[dict(r) for r in receipt['records']]
    matched=0
    for event in events:
        if event['kind']!=2:continue
        candidates=[i for i,r in enumerate(available) if r['pid']==event['pid']
                    and r['status']=='continued-not-launch-proof' and r['admittedAtNs']<=event['ns']]
        require(candidates,'launcher-unpermitted-observed-exec')
        available.pop(candidates[0]);matched+=1
    return {'observedExecsMatched':matched,'unusedConsumedPermits':len(available),
            'nativeCoverageAccepted':False}


class OfflineBrokerV2:
    """Finite launcher accounting over a driver's existing broker partition.

    Explicit fake/recorded facts only: no listener, task verification, syscall,
    bootstrap adoption or native dispatch. A binding here is never accreditation.
    """
    def __init__(self, driver, integration_identity):
        from .forecast_v9_driver import V9Driver
        require(type(driver) is V9Driver, 'broker-v2-driver-type')
        pin(integration_identity)
        with driver.escrow.lock:
            require(not getattr(driver, '_offline_broker_attached', False),
                    'broker-v2-already-attached')
            driver._offline_broker_attached = True
        self.driver = driver
        self.integration_identity = integration_identity
        self.launchers = {}
        self.notifications = set()

    def bind_launcher(self, role, pid, start_ticks, *, now_ns):
        from .forecast_data import integer
        with self.driver.escrow.lock:
            try:
                self.driver._check(now_ns)
                integer(pid, 2); integer(start_ticks, 1)
                phase = self.driver.broker.phase
                expected = {'operator': (0, 2), 'prepare': (0, 3),
                            'verify': (3, 4), 'terminal': (4, 5)}
                require(role in expected and role not in self.launchers,
                        'broker-v2-launcher-role-or-replay')
                phase_index, pair = expected[role]
                require(phase == phase_index and pair in self.driver.escrow.completed,
                        'broker-v2-launcher-before-escrow')
                require(all(row['pid'] != pid for row in self.launchers.values()),
                        'broker-v2-launcher-pid-reuse')
                self.launchers[role] = {'pid': pid, 'startTicks': start_ticks,
                                        'phase': phase_index}
            except BaseException:
                self.driver.fail(); raise

    def reserve(self, role, pid, start_ticks, notification, *, now_ns):
        from .forecast_data import integer
        with self.driver.escrow.lock:
            try:
                self.driver._check(now_ns)
                integer(notification, 1, 2**64-1)
                row = self.launchers.get(role)
                phase = self.driver.broker.phase
                require(row is not None and type(pid) is int and type(start_ticks) is int
                        and (pid, start_ticks) == (row['pid'], row['startTicks']) and
                        (role == 'operator' or row['phase'] == phase or
                         role == 'prepare' and phase in (1, 2)),
                        'broker-v2-launcher-binding')
                require((role, notification) not in self.notifications,
                        'broker-v2-notification-replay')
                self.notifications.add((role, notification))
                # Includes role/phase through the ledger key; never charges a
                # second startup allowance and never accepts a caller ticket.
                return self.driver.reserve_broker(role+':'+str(notification), pid, now_ns=now_ns)
            except BaseException:
                self.driver.fail(); raise

    def delivered(self, ticket, *, continued, now_ns):
        self.driver.finish_broker(ticket, continued=continued, now_ns=now_ns)

    def receipt(self):
        from copy import deepcopy
        with self.driver.escrow.lock:
            return {'version': 'fc1-offline-broker-launcher-v2',
                    'integrationIdentity': self.integration_identity,
                    'launchers': deepcopy(self.launchers),
                    'partition': self.driver.broker.receipt(),
                    'launcherIdentityVerified': False, 'nativeQualification': False,
                    'executionAuthorization': False}
