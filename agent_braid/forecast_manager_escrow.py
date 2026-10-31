# SPDX-License-Identifier: AGPL-3.0-only
"""Private systemd gate receiver; no socket, kernel read or launch on import.

The pure state machine is accounting, never authority. The native adapter obtains
credentials and process facts itself; it accepts no model-selected verifier. All
native entrypoints retain the immutable pending bootstrap gate.
"""
from dataclasses import dataclass
from functools import wraps
from threading import RLock
import array
import os
import re
import socket
import stat
import struct
import time

from .forecast_bootstrap import bootstrap_ready
from .forecast_data import integer, pin, require
from .forecast_exec_budget import ExecAllocation, PartitionLedger, ROLES, ROLE_PHASE
from .forecast_native import proc_stat

MAGIC = 0x31434641
REQUEST = struct.Struct('<IIII96s33s7s')
REPLY = struct.Struct('<IIIIQQ')
SUFFIXES = ('-supervisor.service','.service','-operator.service','-prepare.service',
            '-verify.service','-terminal.service')
OWNER_READ_CAP = 256*1024**2
EXECUTABLE_READ_CAP = 16*1024**2


def serialized(method):
    """Serialize a state method or the complete bounded transport transaction."""
    @wraps(method)
    def call(self,*args,**kwargs):
        state=self.state if type(self) is RootManagerEscrow else self
        with state.lock:return method(self,*args,**kwargs)
    return call


@dataclass(frozen=True)
class GateBinding:
    identity: str
    manager_sha256: str
    executor_sha256: str
    manager_start_ticks: int
    worker_uid: int
    allocation: ExecAllocation

    def __post_init__(self):
        for value in (self.identity,self.manager_sha256,self.executor_sha256): pin(value)
        integer(self.manager_start_ticks,1);integer(self.worker_uid,61000,64999)
        require(type(self.allocation) is ExecAllocation and self.allocation.profile_identity == self.identity,
                'manager-gate-allocation-binding')

    def unit(self,role): return 'fc1'+self.identity+SUFFIXES[role]

    def cgroup(self,role):
        stem='fc1'+self.identity
        return '/'+stem+'.slice/'+stem+('-root.slice/' if role<3 else '-workers.slice/')+self.unit(role)


def decode_request(raw,binding):
    require(type(raw) is bytes and len(raw) == REQUEST.size,'manager-gate-frame-size')
    magic,version,site,reserved,unit,invocation,padding=REQUEST.unpack(raw)
    require((magic,version,reserved,padding)==(MAGIC,1,0,b'\0'*7) and site in (0,1),
            'manager-gate-frame-header')
    require(b'\0' in unit,'manager-gate-unit-encoding')
    name,tail=unit.split(b'\0',1)
    require(not any(tail) and invocation[-1:]==b'\0' and
            re.fullmatch(b'[0-9a-f]{32}',invocation[:32]),'manager-gate-frame-padding')
    names=[binding.unit(r).encode('ascii') for r in range(6)]
    require(name in names,'manager-gate-unit-binding')
    return (names.index(name),site,invocation[:32].decode('ascii'))


@dataclass(frozen=True)
class ProcessFacts:
    pid: int
    uid: int
    gid: int
    ppid: int
    start_ticks: int
    executable_sha256: str
    cgroup: str


class ManagerEscrowState:
    """Pure two-site accounting against the original clock; no launch methods."""
    def __init__(self,binding,origin_ns):
        require(type(binding) is GateBinding,'manager-gate-binding-type')
        self.lock=RLock()
        self.binding=binding;self.ledger=PartitionLedger(binding.allocation,'escrow',origin_ns)
        self.origin_ns=origin_ns;self.last_ns=origin_ns;self.completed=[];self.pending=None
        self.failed=False;self.started=False;self.outstanding=None

    def _now(self,now):
        integer(now,self.last_ns,self.ledger.whole_deadline-1);self.last_ns=now
        require(not self.failed,'manager-gate-failed')
        if self.ledger.phase>=0:require(now<self.ledger.deadline,'manager-gate-phase-expired')

    @serialized
    def fail(self): self.failed=True;self.ledger.failed=True

    @serialized
    def begin(self,pid,*,now_ns):
        try:
            self._now(now_ns);require(not self.started,'manager-gate-owner-replay')
            deadline=min(now_ns+self.binding.allocation.seconds[0]*10**9,
                         self.ledger.whole_deadline-sum(self.binding.allocation.seconds[1:])*10**9)
            self.ledger.enter(0,deadline,now_ns=now_ns)
            ticket=self.ledger.reserve('external-owner-entry',pid,now_ns=now_ns)
            self.ledger.finish(ticket,continued=True);self.started=True
        except BaseException:self.fail();raise

    @serialized
    def advance(self,phase,*,now_ns):
        try:
            self._now(now_ns)
            required=[i for i,p in enumerate(ROLE_PHASE) if p <= self.ledger.phase]
            require(self.started and self.pending is None and self.outstanding is None and
                    self.completed==required,'manager-gate-unfinished-phase')
            integer(phase,0,4)
            deadline=min(now_ns+self.binding.allocation.seconds[phase]*10**9,
                         self.ledger.whole_deadline-sum(self.binding.allocation.seconds[phase+1:])*10**9)
            self.ledger.enter(phase,deadline,now_ns=now_ns)
        except BaseException:self.fail();raise

    @serialized
    def precheck(self,request):
        require(self.started and not self.failed and self.outstanding is None,'manager-gate-state')
        role,site,invocation=request
        integer(role,0,5);integer(site,0,1)
        require(ROLE_PHASE[role]==self.ledger.phase and role==len(self.completed),
                'manager-gate-role-phase-or-replay')
        require((site==0 and self.pending is None) or
                (site==1 and self.pending==(role,invocation)), 'manager-gate-site-or-invocation')

    @serialized
    def reserve(self,request,facts,*,now_ns):
        try:
            self._now(now_ns);self.precheck(request)
            require(type(facts) is ProcessFacts,'manager-gate-facts-type')
            integer(facts.pid,1);integer(facts.start_ticks,1)
            role,site,invocation=request
            if site==0:
                require((facts.pid,facts.uid,facts.gid,facts.ppid,facts.start_ticks,facts.executable_sha256)
                        ==(1,0,0,0,self.binding.manager_start_ticks,self.binding.manager_sha256),
                        'manager-gate-pid1-identity')
            else:
                uid=0 if role<3 else self.binding.worker_uid
                require(facts.pid>1 and facts.ppid==1 and facts.uid==facts.gid==uid and
                        facts.executable_sha256==self.binding.executor_sha256 and
                        facts.cgroup==self.binding.cgroup(role),'manager-gate-executor-identity')
            ticket=self.ledger.reserve(ROLES[role]+':'+str(site),facts.pid,now_ns=now_ns)
            self.outstanding=(ticket,role,site,invocation)
            deadline=min(self.ledger.deadline,self.ledger.whole_deadline)
            return ticket,REPLY.pack(MAGIC,1,site,1,ticket+1,deadline)
        except BaseException:self.fail();raise

    @serialized
    def delivered(self,ticket,*,sent):
        try:
            require(self.outstanding is not None and self.outstanding[0]==ticket,
                    'manager-gate-delivery-ticket')
            _,role,site,invocation=self.outstanding
            self.ledger.finish(ticket,continued=sent);self.outstanding=None
            require(sent,'manager-gate-delivery-unknown')
            if site==0:self.pending=(role,invocation)
            else:self.completed.append(role);self.pending=None
        except BaseException:self.fail();raise

    @serialized
    def receipt(self):
        return {'version':'fc1-manager-escrow-v1','profileIdentity':self.binding.identity,
                'originalOriginNs':self.origin_ns,'originalCloseByNs':self.ledger.whole_deadline,
                'completedPermitPairs':list(self.completed),'failed':self.failed,'ledger':self.ledger.receipt(),
                'externalOwnerPreExecVerified':False,'targetExecSuccessVerified':False,
                'nativeQualification':False,'executionAuthorization':False}


def receive_kernel_frame(channel):
    """Only the kernel's per-message credentials; never trust creator credentials.

    Even on invalid/truncated traffic, close every delivered SCM_RIGHTS descriptor.
    Test callers provide fake sockets; this function is never called on import.
    """
    flags=getattr(socket,'MSG_CMSG_CLOEXEC',0)
    raw,ancillary,msg_flags,_=channel.recvmsg(REQUEST.size+1,socket.CMSG_SPACE(12)+socket.CMSG_SPACE(256),flags)
    credentials=[];unexpected=False
    for level,kind,data in ancillary:
        if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
            values=array.array('i');values.frombytes(data[:len(data)//values.itemsize*values.itemsize])
            for fd in values:
                try:os.close(fd)
                except OSError:pass
            unexpected=True
        elif level==socket.SOL_SOCKET and kind==socket.SCM_CREDENTIALS and len(data)==12:
            credentials.append(struct.unpack('=iii',data))
        else:unexpected=True
    require(not unexpected and not msg_flags&(socket.MSG_TRUNC|socket.MSG_CTRUNC) and
            len(credentials)==1,'manager-gate-kernel-credentials')
    pid,uid,gid=credentials[0];integer(pid,1);integer(uid);integer(gid)
    return raw,(pid,uid,gid)


class RootManagerEscrow:
    """Native root adapter, deliberately inaccessible through current false gates.

    An independent outer guard, qualified owner entry and host/ELF provenance are
    still prerequisites. This transport never starts services or arms that guard.
    """
    def __init__(self,profile,state,mount_owner,*,view=None,clock=time.monotonic_ns):
        from .forecast_linux_profile import LinuxAdmissionProfile
        from .forecast_mounts import RootMountOwner
        require(type(profile) is LinuxAdmissionProfile and type(state) is ManagerEscrowState and
                type(mount_owner) is RootMountOwner and state.binding.identity==profile.identity and
                mount_owner.profile.identity==profile.identity,'manager-gate-owner-binding')
        self.profile=profile;self.state=state;self.owner=mount_owner;self.clock=clock
        self.view=mount_owner.view if view is None else view
        self.channel=None;self.socket_identity=None;self.closed=False;self.cleanup_uncertain=False

    @serialized
    def open(self):
        bootstrap_ready(self.profile)  # Before directory reads, socket or listener.
        self.owner._ready();self.view.guard()
        require(self.state.started and not self.state.failed and not self.closed and
                self.channel is None and self.owner.fd is not None,'manager-gate-open-state')
        limit=max(0,OWNER_READ_CAP-self.view.bytes_read)
        self.view.remaining=limit if self.view.remaining is None else min(limit,self.view.remaining)
        path='/proc/self/fd/'+str(self.owner.fd)+'/manager-gate.sock'
        require(not os.path.lexists(path),'manager-gate-existing-socket')
        channel=socket.socket(socket.AF_UNIX,socket.SOCK_SEQPACKET|socket.SOCK_CLOEXEC)
        try:
            channel.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
            channel.bind(path);self.cleanup_uncertain=True
            info=os.stat(path,follow_symlinks=False)
            self.socket_identity=(info.st_dev,info.st_ino)
            os.chmod(path,0o600);info=os.stat(path,follow_symlinks=False)
            require(stat.S_ISSOCK(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600,
                    'manager-gate-socket-mode')
            require((info.st_dev,info.st_ino)==self.socket_identity,'manager-gate-socket-replaced')
            channel.listen(1);self.channel=channel
        except BaseException:channel.close();self.state.fail();raise
        return self

    def _facts(self,request,credentials):
        pid,uid,gid=credentials;role,site,_=request
        before=proc_stat(self.view.read(f'/proc/{pid}/stat').decode(),allow_init=pid==1)
        status=self.view.read(f'/proc/{pid}/status').decode()
        for field,value in (('Uid',uid),('Gid',gid)):
            matches=re.findall(r'^'+field+r':\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)$',status,re.M)
            require(len(matches)==1 and all(int(v)==value for v in matches[0]),'manager-gate-credentials-drift')
        expected=self.state.binding.manager_sha256 if site==0 else self.state.binding.executor_sha256
        sha=self.view.hash_file(f'/proc/{pid}/exe',EXECUTABLE_READ_CAP)
        require(sha==expected,'manager-gate-executable-pin')
        cgroup=self.view.read(f'/proc/{pid}/cgroup').decode()
        require(cgroup.startswith('0::/') and cgroup.count('\n')==1,'manager-gate-cgroup-format')
        after=proc_stat(self.view.read(f'/proc/{pid}/stat').decode(),allow_init=pid==1)
        require(all(before[k]==after[k] for k in ('pid','ppid','start')) and
                before['pid']==pid and all(v['state'] not in ('Z','X') for v in (before,after)),
                'manager-gate-task-reused')
        return ProcessFacts(pid,uid,gid,before['ppid'],before['start'],sha,cgroup[3:].strip())

    @serialized
    def serve_connection(self,connection):
        bootstrap_ready(self.profile);self.view.guard()
        ticket=None
        try:
            now=self.clock();self.state._now(now)
            require(now<self.state.ledger.deadline,'manager-gate-deadline')
            connection.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
            connection.settimeout(min(1,(self.state.ledger.deadline-now)/10**9))
            raw,credentials=receive_kernel_frame(connection);self.view.account(len(raw)+512)
            request=decode_request(raw,self.state.binding);self.state.precheck(request)
            facts=self._facts(request,credentials)
            ticket,reply=self.state.reserve(request,facts,now_ns=self.clock())
            now=self.clock();self.state._now(now)
            require(now<self.state.ledger.deadline,'manager-gate-deadline')
            connection.settimeout(min(1,(self.state.ledger.deadline-now)/10**9))
            require(connection.send(reply)==len(reply),'manager-gate-reply-short')
            require(self.clock()<self.state.ledger.deadline,'manager-gate-late-reply')
            self.state.delivered(ticket,sent=True);ticket=None
        except BaseException:
            if ticket is not None:
                try:self.state.delivered(ticket,sent=False)
                except BaseException:pass
            self.state.fail();raise
        finally:connection.close()

    @serialized
    def close(self):
        if self.closed:return
        # Wait for any bounded handler, then revoke before withdrawing transport.
        self.state.fail()
        self.closed=True
        try:
            if self.channel is not None:self.channel.close();self.channel=None
            if self.socket_identity is not None:
                info=os.stat('manager-gate.sock',dir_fd=self.owner.fd,follow_symlinks=False)
                require((info.st_dev,info.st_ino)==self.socket_identity,'manager-gate-socket-replaced')
                os.unlink('manager-gate.sock',dir_fd=self.owner.fd)
                self.cleanup_uncertain=False
            require(not self.cleanup_uncertain,'manager-gate-socket-cleanup-unknown')
        except BaseException:self.state.fail();raise
