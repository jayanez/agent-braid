# SPDX-License-Identifier: AGPL-3.0-only
"""Private pre-exec quota broker, never installed or started by import/compilation.

CONTINUE governs a numeric exec allowance only. We never authorize a path or
payload from mutable tracee memory. Runtime grants, image/launcher identity,
filter inheritance and complete native placement remain separate prerequisites.
"""
import ctypes
import fcntl
import hashlib
import os
from pathlib import Path
import select
import secrets
import struct
import sys
import threading
import time

from .forecast_data import integer, require

ARCH = 0xc00000b7
EXEC_SYSCALLS = (221,281)
NOTIF = struct.Struct('<QIIiI7Q')
RESP = struct.Struct('<QqiI')
RECV = 0xc0502100
SEND = 0xc0182101
VALID = 0x40082102


def filter_bytes():
    """Classic BPF: exec notifies, foreign ABI kills, filter restacking denies."""
    # Prevent a later USER_NOTIF filter from shadowing this listener. Deny all
    # seccomp/prctl changes after installation; this conservative restriction
    # itself needs compatibility checks in the future native qualification.
    instructions = [(0x20,0,0,4),(0x15,1,0,ARCH),(0x06,0,0,0x80000000),
                    (0x20,0,0,0),(0x15,5,0,277),(0x15,4,0,167),
                    (0x15,1,0,221),(0x15,0,1,281),(0x06,0,0,0x7fc00000),
                    (0x06,0,0,0x7fff0000),(0x06,0,0,0x00050001)]
    return b''.join(struct.pack('<HBBI',*row) for row in instructions)


def filter_sha256(): return hashlib.sha256(filter_bytes()).hexdigest()


def install_on_current_task():
    """Explicit future native action; unit tests never invoke its syscalls.

    Must precede threads/forks and task execution. A separately owned root broker
    must receive/retain the listener before any subsequent exec. No auto fallback.
    """
    require(sys.platform=='linux' and os.uname().machine=='aarch64','exec-gate-platform')
    require(len(list(Path('/proc/self/task').iterdir()))==1,'exec-gate-single-thread-required')
    libc=ctypes.CDLL(None,use_errno=True);libc.syscall.restype=ctypes.c_long
    sizes=(ctypes.c_ushort*3)()
    require(libc.syscall(ctypes.c_long(277),ctypes.c_uint(3),ctypes.c_uint(0),
                        ctypes.byref(sizes))==0 and tuple(sizes)==(80,24,64),'exec-gate-kernel-abi')
    require(libc.prctl(ctypes.c_int(38),ctypes.c_ulong(1),ctypes.c_ulong(0),
                       ctypes.c_ulong(0),ctypes.c_ulong(0))==0,'exec-gate-no-new-privs')
    class Instruction(ctypes.Structure):
        _fields_=[('code',ctypes.c_ushort),('jt',ctypes.c_ubyte),('jf',ctypes.c_ubyte),('k',ctypes.c_uint)]
    class Program(ctypes.Structure):
        _fields_=[('length',ctypes.c_ushort),('filter',ctypes.POINTER(Instruction))]
    raw=filter_bytes();instructions=(Instruction*(len(raw)//8)).from_buffer_copy(raw)
    program=Program(len(instructions),instructions)
    fd=libc.syscall(ctypes.c_long(277),ctypes.c_uint(1),ctypes.c_uint(8),ctypes.byref(program))
    require(fd>=0,'exec-gate-filter-install')
    os.set_inheritable(fd,False)
    return fd


class ExecPermitLedger:
    """Single root broker's phase-specific, write-ahead exec-attempt ledger.

    Failed/cancelled/ambiguous continuations consume their slot forever. Attempts
    after exhaustion poison the flow; no phase loans, refunds or automatic retry.
    It does not assert that an admitted syscall succeeded in launching a process.
    """
    def __init__(self,profile,origin_ns):
        self.identity=profile.identity;self.limits=profile.limits
        self.origin_ns=integer(origin_ns,1);self.phase=-1;self.deadline=0
        self.whole_deadline=self.origin_ns+sum(p.wall_seconds for p in self.limits)*10**9
        self.failed=False;self.records=[];self.keys=set();self.denied=0;self.lock=threading.RLock();self._broker_attached=False

    def enter(self,phase,deadline_ns,*,now_ns):
        with self.lock:
            require(not self._broker_attached,'exec-gate-transition-owner')
            require(not self.failed and phase==self.phase+1 and phase<5
                    and self.origin_ns<=now_ns<deadline_ns<=self.whole_deadline
                    and deadline_ns-now_ns<=self.limits[phase].wall_seconds*10**9,'exec-gate-phase')
            require(all(r['status']!='reserved' for r in self.records),'exec-gate-outstanding')
            self.phase=phase;self.deadline=deadline_ns

    def reserve(self,listener,notification,pid,*,now_ns,worker_entry=False,expected_phase=None):
        with self.lock:
            require(not self.failed and 0<=self.phase<5 and now_ns<self.deadline
                    and now_ns>=self.origin_ns,'exec-gate-deadline')
            require(type(listener) in (int,str),'exec-gate-listener-key')
            integer(notification,0)
            require(type(worker_entry) is bool,'exec-gate-entry-kind')
            if not worker_entry or pid is not None:integer(pid,1)
            require(expected_phase is None and not self._broker_attached or expected_phase==self.phase,
                    'exec-gate-stale-phase')
            require(len(self.records)<65536,'exec-gate-ledger-cap')
            key=(listener,notification)
            require(key not in self.keys,'exec-gate-replayed-notification')
            phase=self.phase;limit=self.limits[phase]
            rows=[r for r in self.records if r['phaseIndex']==phase]
            count=sum(r['workerEntry']==worker_entry for r in rows)
            cap=int(phase in (0,3,4)) if worker_entry else 2*limit.requests+3
            if count>=cap:
                self.denied+=1
                self.failed=True
                require(False,'exec-gate-quota-exhausted')
            self.keys.add(key)
            record=dict(phaseIndex=phase,listener=listener,notification=notification,pid=pid,
                        workerEntry=worker_entry,status='reserved',admittedAtNs=now_ns)
            self.records.append(record)
            return len(self.records)-1

    def finish(self,ticket,*,continued):
        with self.lock:
            require(type(ticket) is int and 0<=ticket<len(self.records)
                    and self.records[ticket]['status']=='reserved','exec-gate-ticket')
            self.records[ticket]['status']='continued-not-launch-proof' if continued else 'indeterminate-consumed'
            if not continued: self.failed=True

    def receipt(self):
        with self.lock:
            return {'version':'fc1-exec-permits-v1','profileIdentity':self.identity,
                    'attemptsConsumed':len(self.records),'deniedAtCap':self.denied,'records':[dict(r) for r in self.records],
                    'failed':self.failed,'nativeCoverageAccepted':False,'executionAuthorization':False}


class NativeExecBroker:
    """Root-owned listener driver; only registered independently verified FDs.

    validate_task belongs to the trusted operator and checks pending task/cgroup
    identity, never argv/path pointers. Registration cannot be supplied by a model
    or be inferred from a worker's claimed filter hash. The native verifier/launcher
    binding is deliberately still required; this class does not manufacture it.
    """
    def __init__(self,ledger,*,validate_task,clock=time.monotonic_ns,account_io=None):
        require(callable(validate_task),'exec-gate-task-verifier-required')
        self._ledger=ledger;self.validate_task=validate_task;self.clock=clock;self.account_io=account_io
        require(not ledger._broker_attached,'exec-gate-already-owned')
        ledger._broker_attached=True
        self._listeners={};self.closed=False

    def register(self,fd,*,identity,verify_listener):
        self.guard()
        with self._ledger.lock:
            require(not self.closed and type(fd) is int and fd>=0
                    and len(self._listeners)<4 and callable(verify_listener)
                    and all(r['identity']!=identity for r in self._listeners.values()),'exec-gate-listener')
            owned=fcntl.fcntl(fd,fcntl.F_DUPFD_CLOEXEC,3)
            try:
                require(verify_listener(owned,identity,filter_sha256()) is True,
                        'exec-gate-listener-unverified')
                token=secrets.token_hex(16)
                self._listeners[token]={'fd':owned,'identity':identity,'phase':self._ledger.phase}
            except BaseException:
                os.close(owned);raise
            return token

    def retire(self,token,*,verify_empty):
        self.guard()
        with self._ledger.lock:
            require(token in self._listeners and callable(verify_empty)
                    and verify_empty(self._listeners[token]['identity']) is True,'exec-gate-not-empty')
            record=self._listeners.pop(token)
            os.close(record['fd'])

    def transition(self,phase,deadline_ns,*,verify_quiescent):
        """Root must freeze/close every covered task and confirm no pending exec.

        Existing inherited filters/listeners persist across prepare/grant/dispatch.
        We reject a pending notification rather than charge it to the next phase.
        Caller cannot advance the owned ledger directly.
        """
        self.guard()
        with self._ledger.lock:
            try:
                require(not self.closed and callable(verify_quiescent)
                        and verify_quiescent() is True,'exec-gate-not-quiescent')
                if self._listeners:
                    ready,_,_=select.select([r['fd'] for r in self._listeners.values()],[],[],0)
                    require(not ready,'exec-gate-pending-at-transition')
                now=self.clock()
                require(not self._ledger.failed and phase==self._ledger.phase+1 and phase<5
                        and self._ledger.origin_ns<=now<deadline_ns<=self._ledger.whole_deadline
                        and deadline_ns-now<=self._ledger.limits[phase].wall_seconds*10**9,'exec-gate-phase')
                require(all(r['status']!='reserved' for r in self._ledger.records),'exec-gate-outstanding')
                self._ledger.phase=phase;self._ledger.deadline=deadline_ns
                for record in self._listeners.values(): record['phase']=phase
            except BaseException:
                self._ledger.failed=True;self.close();raise

    @staticmethod
    def guard(): require(sys.platform=='linux' and os.geteuid()==0,'exec-gate-root-linux')

    def serve_one(self,token):
        self.guard()
        with self._ledger.lock:
            require(not self.closed and token in self._listeners and not self._ledger.failed,'exec-gate-not-registered')
            fd=self._listeners[token]['fd']
            phase=self._ledger.phase
            deadline=self._ledger.deadline
        # Poll without the lifecycle lock so a quiet listener cannot prevent a
        # quiescent phase transition. Read/reserve/continue use one locked epoch.
        ready,_,_=select.select([fd],[],[],min(.05,max(0,(deadline-self.clock())/10**9)))
        if not ready:
            require(self.clock()<deadline,'exec-gate-deadline')
            return False
        with self._ledger.lock:
            ticket=None;raw=bytearray(NOTIF.size)
            try:
                require(not self.closed and token in self._listeners
                        and self._ledger.phase==phase==self._listeners[token]['phase'], 'exec-gate-stale-phase')
                require(self.clock()<self._ledger.deadline,'exec-gate-deadline')
                still_ready,_,_=select.select([fd],[],[],0)
                if not still_ready:return False
                if self.account_io:self.account_io(len(raw))
                fcntl.ioctl(fd,RECV,raw,True)
                notification,pid,flags,nr,arch,*unused=NOTIF.unpack(raw)
                require(pid>0 and flags==0 and arch==ARCH and nr in EXEC_SYSCALLS,'exec-gate-notification')
                identity=self._listeners[token]['identity']
                require(self.validate_task(pid,identity) is True,'exec-gate-task-binding')
                if self.account_io:self.account_io(8)
                fcntl.ioctl(fd,VALID,struct.pack('<Q',notification))
                ticket=self._ledger.reserve(token,notification,pid,now_ns=self.clock(),expected_phase=phase)
                if self.account_io:self.account_io(8)
                fcntl.ioctl(fd,VALID,struct.pack('<Q',notification))
                require(self.clock()<self._ledger.deadline,'exec-gate-deadline')
                if self.account_io:self.account_io(RESP.size)
                fcntl.ioctl(fd,SEND,RESP.pack(notification,0,0,1))
                self._ledger.finish(ticket,continued=True)
                return True
            except BaseException:
                try:
                    if ticket is not None:self._ledger.finish(ticket,continued=False)
                finally:
                    self._ledger.failed=True;self.close()
                raise

    def close(self):
        with self._ledger.lock:
            self.closed=True
            for record in self._listeners.values(): os.close(record['fd'])
            self._listeners.clear()
