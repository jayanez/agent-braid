# SPDX-License-Identifier: AGPL-3.0-only
"""Private pinned sd-bus backend; never loads a library or connects on import.

The complete .so dependency lock and the source/object correspondence are native
qualification prerequisites. Root/source pins are operator inputs, never MCP data.
The existing real profile refuses before any dlopen, socket or manager operation.
"""
import ctypes
import fcntl
import hashlib
import os
import select
import stat
import time

from .forecast_bootstrap import ROLES,bootstrap_ready
from .forecast_data import integer,pin,require
from .forecast_native import KernelView,proc_stat

ROSTER=(*ROLES,'prepare','verify','terminal')
PROPERTIES=('ActiveState','SubState','ControlGroup','FragmentPath','CPUUsageNSec',
            'MemoryCurrent','MemoryPeak','TasksCurrent','MainPID','ExecMainStatus')


def manager_launch_inventory(profile):
    """Inspect our rendered jobs only, without consulting or starting a manager.

    v261.3's pinned source has an executor then target exec per command, and up
    to 32 retries after the first umount attempt per mount unit. These are partial source bounds, never
    a whole-flow upper bound: RootImage/NSS/udev and other helpers remain open.
    """
    units=profile.units(remaining_seconds=sum(p.wall_seconds for p in profile.limits))
    services=sorted(n for n in units if n.endswith('.service'))
    mounts=sorted(n for n in units if n.endswith('.mount'))
    def explicit_no_defaults(text):
        section=None;values=[]
        for line in text.splitlines():
            line=line.strip()
            if not line or line.startswith(('#',';')):continue
            if line.startswith('[') and line.endswith(']'):section=line
            elif section=='[Unit]' and '=' in line:
                key,value=line.split('=',1)
                if key.strip()=='DefaultDependencies':values.append(value.strip())
        return values==['no']
    implicit=sorted(n for n,text in units.items() if not explicit_no_defaults(text))
    extra=sorted(n for n,text in units.items() if any(line.partition('=')[0].strip() in
        ('ExecStartPre','ExecStartPost','ExecCondition','ExecReload','ExecStop','ExecStopPost')
        for line in text.splitlines()))
    terminal=profile.limits[-1]
    # Existing terminal ledger: one worker entry plus 2*Git + 3 ordinary execs.
    terminal_cap=2*terminal.requests+3+1
    terminal_floor=(2*int(any(n.endswith('-terminal.service') for n in services))
                    +2*int(any(n.endswith('-terminal.mount') for n in mounts))+2*len(mounts))
    blockers=[]
    if mounts:blockers.append('manager-mount-helpers-outside-pre-exec-broker')
    if implicit:blockers.append('implicit-manager-job-dependencies')
    if extra:blockers.append('additional-manager-control-commands')
    if terminal_floor>terminal_cap:blockers.append('terminal-exec-reserve-insufficient-for-mount-cleanup')
    return {'version':'fc1-manager-launch-inventory-v1','services':services,'mounts':mounts,
            'implicitDependencyUnits':implicit,'extraControlCommandUnits':extra,
            'knownExecFloorPerStartCommand':2,'mountUnmountRetryCap':32,'mountUnmountAttemptCap':33,
            'knownServiceAndMountStartExecs':2*(len(services)+len(mounts)),
            'oneUnmountPerMountExecs':2*len(mounts),
            'mountUnmountExecCap':2*33*len(mounts),
            'mountUnmountExecCapScope':'one unmount campaign per mount only; excludes repeated jobs and other helpers',
            'terminalExecCap':terminal_cap,'terminalKnownExecFloor':terminal_floor,
            'terminalFloorScope':'terminal executor/target, terminal mount executor/mount, '
                                 'and one umount executor/umount for each retained mount; excludes other work',
            'wholeFlowExecUpperBound':None,'blockers':blockers,
            'nativeCoverageAccepted':False,'operationalBudgetClosed':False}


def require_closed_job_graph(profile):
    """Refuse known unsafe job graphs even if another readiness flag is changed.

    Passing this necessary check is never sufficient pre-exec qualification.
    The independent immutable native gates are still required by the caller.
    """
    report=manager_launch_inventory(profile)
    require(not report['blockers'],'manager-job-graph-unclosed:'+','.join(report['blockers']))
    return report


class Result(ctypes.Structure):
    _fields_=[('kind',ctypes.c_int32),('error',ctypes.c_int32),
              ('number',ctypes.c_uint64),('text',ctypes.c_char*1024)]


def _sealed_library(path,sha,view):
    view.guard();pin(sha)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd);require(stat.S_ISREG(before.st_mode) and 0<before.st_size<=4*1024**2,
                                   'manager-bridge-file')
        raw=bytearray()
        while len(raw)<=before.st_size:
            block=os.read(fd,min(65536,before.st_size-len(raw)+1))
            if not block:break
            view.account(len(block));raw.extend(block)
        after=os.fstat(fd)
        require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
                (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) and
                len(raw)==before.st_size and hashlib.sha256(raw).hexdigest()==sha,'manager-bridge-drift')
    finally:os.close(fd)
    sealed=os.memfd_create('fc1-manager',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
    try:
        offset=0
        while offset<len(raw):
            written=os.write(sealed,raw[offset:offset+65536]);require(written>0,'manager-bridge-copy');offset+=written
        seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
        fcntl.fcntl(sealed,fcntl.F_ADD_SEALS,seals)
        require(fcntl.fcntl(sealed,fcntl.F_GET_SEALS)&seals==seals,'manager-bridge-unsealed')
        return sealed
    except BaseException:os.close(sealed);raise


class RootManager:
    """One outstanding fixed request; no worker-owned unit/method/property names."""
    def __init__(self,profile,*,bridge_path,bridge_sha256,view=None,clock=time.monotonic_ns):
        self.profile=profile;self.path=bridge_path;self.sha=pin(bridge_sha256)
        self.view=KernelView() if view is None else view
        if view is None:self.view.remaining=256*1024**2
        self.clock=clock;self.library=None;self.context=ctypes.c_void_p();self.fd=None
        self.pending=False;self.failed=False;self.starts=set();self.calls=0;self.init_start=None

    def _manager_identity(self):
        # PID1 has ppid0, deliberately distinct from normal child verification.
        state=proc_stat(self.view.read('/proc/1/stat').decode(),allow_init=True)
        require(state['pid']==1 and state['state'] not in ('Z','X'),'manager-init-state')
        require(self.view.hash_file('/proc/1/exe',32*1024**2)==self.profile.manager_sha256,
                'manager-init-executable')
        require(self.init_start is None or self.init_start==state['start'],'manager-init-reused')
        self.init_start=state['start']

    def open(self):
        bootstrap_ready(self.profile);require_closed_job_graph(self.profile);self.view.guard()
        require(self.library is None and not self.failed,'manager-open-state')
        self._manager_identity();self.fd=_sealed_library(self.path,self.sha,self.view)
        try:
            lib=ctypes.CDLL('/proc/self/fd/'+str(self.fd));self.library=lib
            lib.fc1_manager_open.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)]
            lib.fc1_manager_open.restype=ctypes.c_int
            for name,args in {'start':[ctypes.c_void_p,ctypes.c_int,ctypes.c_uint64],
                'property':[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_uint64],
                'step':[ctypes.c_void_p,ctypes.POINTER(Result)],'fd':[ctypes.c_void_p],
                'events':[ctypes.c_void_p]}.items():
                function=getattr(lib,'fc1_manager_'+name);function.argtypes=args;function.restype=ctypes.c_int
            lib.fc1_manager_close.argtypes=[ctypes.c_void_p];lib.fc1_manager_close.restype=None
            require(lib.fc1_manager_open(self.profile.identity.encode(),ctypes.byref(self.context))==0 and
                    self.context.value is not None,'manager-private-connect')
            self._manager_identity()
        except BaseException:self.failed=True;self.close();raise
        return self

    def _call(self,role,property_name,deadline_ns):
        self.view.guard();integer(deadline_ns,1)
        require(self.library is not None and self.context.value and not self.pending and not self.failed,
                'manager-not-ready')
        require(role in ROSTER and self.clock()<deadline_ns,'manager-role-or-deadline')
        self.pending=True;self.calls+=1
        try:
            self._manager_identity();index=ROSTER.index(role)
            if property_name is None:
                result=self.library.fc1_manager_start(self.context,index,deadline_ns//1000)
            else:
                require(property_name in PROPERTIES,'manager-property-denied')
                result=self.library.fc1_manager_property(self.context,index,PROPERTIES.index(property_name),deadline_ns//1000)
            require(result==0,'manager-request-refused')
            while self.clock()<deadline_ns:
                value=Result();result=self.library.fc1_manager_step(self.context,ctypes.byref(value))
                require(result>=0,'manager-request-failed')
                if result==1:
                    self._manager_identity();require(self.clock()<deadline_ns,'manager-late-reply')
                    self.view.account(1024+16)
                    if value.kind==1:return value.text.decode('utf-8')
                    require(value.kind in (2,3),'manager-result-type')
                    return int(value.number) if value.kind==2 else ctypes.c_int64(value.number).value
                fd=self.library.fc1_manager_fd(self.context);events=self.library.fc1_manager_events(self.context)
                require(fd>=0 and events>=0,'manager-poll-state')
                wait=min(.01,max(0,(deadline_ns-self.clock())/10**9))
                poll=select.poll();poll.register(fd,events|select.POLLERR|select.POLLHUP);poll.poll(max(0,int(wait*1000)))
            require(False,'manager-deadline')
        except BaseException:self.failed=True;raise
        finally:self.pending=False

    def request_start(self,unit,reservation,deadline_ns):
        bootstrap_ready(self.profile)
        require_closed_job_graph(self.profile)
        role=reservation['role']
        stem='fc1'+self.profile.identity
        expected=stem+('.service' if role=='anchor' else '-'+role+'.service')
        require(unit==expected and role in ROSTER and role not in self.starts and
                reservation.get('admitted') is True and reservation.get('state')=='dispatch-indeterminate',
                'manager-prior-reservation-required')
        # Consume before the IPC; failure/unknown outcome can never retry.
        self.starts.add(role)
        job=self._call(role,None,deadline_ns)
        require(type(job) is str and job.startswith('/org/freedesktop/systemd1/job/'),'manager-job-path')
        return job

    def property(self,role,name,deadline_ns):return self._call(role,name,deadline_ns)

    def close(self):
        try:
            if self.library is not None and self.context.value:
                self.library.fc1_manager_close(self.context);self.context=ctypes.c_void_p()
        finally:
            if self.fd is not None:os.close(self.fd);self.fd=None
            self.library=None
