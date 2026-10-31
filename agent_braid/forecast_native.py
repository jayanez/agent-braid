# SPDX-License-Identifier: AGPL-3.0-only
"""Private Linux readback providers. No installation, activation or automatic probe.

Every native method is root/Linux gated. Tests replace reads/syscalls; importing
or constructing the provider never starts a service, child, model or control.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import re
import select
import stat
import subprocess
import signal
import selectors
import sys
import time
import resource
import fcntl

from .forecast_data import digest, integer, pin, require


def proc_stat(raw, *, allow_init=False):
    require(type(raw) is str and len(raw) <= 16384, 'native-stat-bound')
    head,sep,tail=raw.rpartition(') ')
    fields=tail.split()
    require(sep and len(fields) >= 50 and re.fullmatch(r'[0-9]+ \(.*',head,re.S), 'native-stat-shape')
    result={'pid':int(head.split(' ',1)[0]),'state':fields[0],'ppid':int(fields[1]),
            'start':int(fields[19]),'exitStatus':int(fields[49])}
    require(result['start'] > 0 and (result['ppid'] > 0 or
            (allow_init is True and result['pid']==1 and result['ppid']==0)), 'native-stat-hidden-or-invalid')
    return result


class KernelView:
    def __init__(self):
        self.bytes_read=0
        self.remaining=None

    def account(self, count):
        self.bytes_read+=count
        if self.remaining is not None:
            self.remaining-=count
            require(self.remaining>=0,'native-qualification-read-budget')

    def hash_file(self,path,maximum):
        self.guard()
        hashed=hashlib.sha256(); size=0
        with open(path,'rb',buffering=0) as stream:
            require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode),'native-regular-artifact-required')
            while True:
                block=stream.read(1024*1024)
                if not block:
                    break
                self.account(len(block));size+=len(block)
                require(size<=maximum,'native-file-bound')
                hashed.update(block)
        return hashed.hexdigest()

    @staticmethod
    def guard():
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')

    def read(self,path,maximum=65536):
        self.guard()
        with open(path,'rb',buffering=0) as stream:
            raw=stream.read(maximum+1)
        self.account(len(raw))
        require(len(raw) <= maximum, 'native-read-bound')
        return raw

    def state(self,pid):
        return proc_stat(self.read(f'/proc/{integer(pid,2)}/stat').decode())

    def executable(self,pid,expected_sha):
        path=f'/proc/{integer(pid,2)}/exe'
        require(self.hash_file(path,32*1024*1024) == pin(expected_sha), 'native-executable-drift')
        info=os.stat(path)
        return (info.st_dev,info.st_ino)

    def ready(self,fd):
        self.guard()
        return bool(select.select([fd],[],[],0)[0])


class ChildObserver:
    """Retain pidfd/starttime/live cgroup, then capture zombie exit before wait()."""
    def __init__(self,*,worker_pid,worker_cgroup,git_sha256,working_directory,git_identity=None):
        self.worker_pid=integer(worker_pid,2)
        require(re.fullmatch(r'/[A-Za-z0-9_.\-/]+',worker_cgroup), 'native-cgroup-path')
        self.cgroup=worker_cgroup
        self.git_sha=pin(git_sha256)
        self.git_identity=git_identity
        require(working_directory in ('/work','/scratch'), 'native-worker-cwd')
        self.cwd=working_directory
        self.view=KernelView()
        self.children={}
        self.failed=False

    def __call__(self,pid,event,invocation):
        try:
            self.view.guard()
            require(not self.failed, 'native-child-observer-stopped')
            if event == 'launched':
                require(pid not in self.children, 'native-child-reused')
                before=self.view.state(pid)
                require(before['pid'] == pid and before['ppid'] == self.worker_pid
                        and before['state'] not in ('Z','X'), 'native-child-not-live')
                fd=os.pidfd_open(pid,0)
                # Retain even if a later read fails; owner closes only after abort.
                self.children[pid]={'fd':fd,'state':before,'invocation':digest(invocation)}
                require(not self.view.ready(fd), 'native-child-already-exited')
                require(type(self.git_identity) is tuple and len(self.git_identity)==2,
                        'native-child-executable-not-qualified')
                executable=os.stat(f'/proc/{pid}/exe')
                require((executable.st_dev,executable.st_ino)==self.git_identity,
                        'native-child-executable-inode')
                require(self.view.read(f'/proc/{pid}/cgroup').decode() == '0::'+self.cgroup+'\n',
                        'native-child-cgroup')
                require(self.view.read(f'/proc/{pid}/cmdline') == b'\0'.join(
                        arg.encode() for arg in invocation['argv'])+b'\0', 'native-child-argv')
                environment=self.view.read(f'/proc/{pid}/environ').split(b'\0')
                require(environment[-1] == b'' and len(environment[:-1]) == len(set(environment[:-1]))
                        and set(environment[:-1]) == {k.encode()+b'='+v.encode() for k,v in invocation['env'].items()},
                        'native-child-environment')
                require(invocation['cwd'] is None and os.readlink(f'/proc/{pid}/cwd') == self.cwd,
                        'native-child-cwd')
                after=self.view.state(pid)
                require(after['start'] == before['start'] and after['ppid'] == self.worker_pid
                        and after['state'] not in ('Z','X') and not self.view.ready(fd),
                        'native-child-identity-race')
                return {'identityVerified':True}
            require(pid in self.children, 'native-child-unknown')
            child=self.children[pid]
            require(child['invocation'] == digest(invocation) and self.view.ready(child['fd']),
                    'native-child-not-terminated')
            if event == 'exited':
                state=self.view.state(pid)
                require('exit' not in child and state['state'] == 'Z'
                        and state['start'] == child['state']['start']
                        and state['ppid'] == self.worker_pid, 'native-zombie-identity')
                child['exit']=os.waitstatus_to_exitcode(state['exitStatus'])
                return {'exitObserved':True,'returncode':child['exit']}
            require(event == 'reaped' and 'exit' in child, 'native-exit-not-observed')
            result={'terminated':True,'returncode':child['exit']}
            os.close(child['fd']);del self.children[pid]
            return result
        except BaseException:
            self.failed=True
            raise

    def close(self):
        for child in self.children.values():
            os.close(child['fd'])
        self.children.clear()
        self.failed=True


def mount_rows(raw):
    rows={}
    for line in raw.decode().splitlines():
        values=line.split(); split=values.index('-')
        require(len(values) >= split+4 and values[4] not in rows, 'native-mount-shape')
        # The fixed image uses no escaped mountpoint names.
        require('\\' not in values[4], 'native-mount-escape')
        rows[values[4]]={'device':values[2],'mount':set(values[5].split(',')),
                         'type':values[split+1],'options':set(values[split+3].split(','))}
    return rows


class NativeBoundary:
    """Frozen-worker qualification plus fresh kernel/clock/quota leases.

    root_image and tool pins originate at the operator. qualify() is an explicit
    native readback procedure, never called here by compilation or unit tests.
    Complete qualification is mandatory after each new worker or phase handoff.
    """
    def __init__(self,session,*,git_sha256,systemctl_sha256,dmsetup_sha256,recipe_bytes,census_manifest_bytes,root_gate=None):
        self.session=session;self.profile=session.timeline.profile;self.root_gate=root_gate
        self.git_sha=pin(git_sha256)
        self.tool_pins={'/usr/bin/systemctl':pin(systemctl_sha256),
                        '/usr/sbin/dmsetup':pin(dmsetup_sha256)}
        require(hashlib.sha256(recipe_bytes).hexdigest() == self.profile.recipe_sha256,
                'native-recipe-pin')
        from research.lab.model import loads
        self.recipe=loads(recipe_bytes.decode())
        from .forecast_recipe import recipe_bytes as canonical_recipe
        require(canonical_recipe(self.recipe['request'],source_digest=self.profile.source_digest,
                git_sha256=self.git_sha) == recipe_bytes,'native-recipe-config')
        self.view=KernelView();self.view.remaining=512*1024**2
        self.qualified=None;self.binding=None
        if root_gate is not None:root_gate.account_io=self.view.account
        self.qualification_receipts=[]
        self.phase_start=None
        self.phase_receipts=[];self.exec_gate_receipts=[]
        self.native_tools=[]
        self.operator_identity=None
        from .forecast_exec_census import CensusLedger, KernelCensus
        self.census=KernelCensus(self.profile,census_manifest_bytes,self.view)
        self.census_ledger=CensusLedger(self.profile,self.session.timeline.origin_ns)
        self.known_execs=set()
        self.child_observer=None
        require(session.boundary is None, 'native-provider-already-attached')
        session.boundary=self

    def _tool(self,path,*args):
        self.view.guard()
        require(path in self.tool_pins and len(self.native_tools)<15,'native-tool-launch-cap')
        record={'phaseIndex':self.session.timeline.index,'argv':[path,*args],
                'attempted':True,'admitted':False,'launched':False,'finished':False}
        self.native_tools.append(record)
        fd=self._sealed_tool(path)
        # Fixed read-only commands only, never a caller supplied shell/manager verb.
        record['admitted']=True
        try:
            process=subprocess.Popen([path,*args],executable='/proc/self/fd/'+str(fd),pass_fds=(fd,),
                stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                env={'PATH':'/usr/bin:/usr/sbin','LANG':'C'},start_new_session=True)
        finally:
            os.close(fd)
        record.update(launched=True,pid=process.pid)
        self.known_execs.add((process.pid,'tool'))
        deadline=min(self.session.timeline.phase_deadline_ns,time.monotonic_ns()+10**9)
        output=bytearray(); selector=selectors.DefaultSelector()
        try:
            os.set_blocking(process.stdout.fileno(),False)
            selector.register(process.stdout,selectors.EVENT_READ)
            while selector.get_map():
                require(time.monotonic_ns()<deadline,'native-tool-deadline')
                for key,_ in selector.select(.01):
                    block=os.read(key.fd,4096)
                    require(len(output)+len(block)<=65536,'native-tool-output')
                    self.view.account(len(block))
                    output.extend(block)
                    if not block:
                        selector.unregister(key.fileobj)
            result=process.wait(timeout=max(.001,(deadline-time.monotonic_ns())/10**9))
            record.update(finished=True,returncode=result)
            require(result==0,'native-tool-failed')
            return output.decode()
        except BaseException:
            if not record['finished']:
                try:
                    os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
            try:
                record.update(finished=True,returncode=process.wait(timeout=.1))
            except subprocess.TimeoutExpired:
                pass
            raise
        finally:
            selector.close();process.stdout.close()

    def _sealed_tool(self,path):
        self.view.guard()
        raw=self.view.read(path,32*1024*1024)
        require(hashlib.sha256(raw).hexdigest()==self.tool_pins[path],'native-tool-drift')
        fd=os.memfd_create('fc1-tool',os.MFD_CLOEXEC|os.MFD_ALLOW_SEALING)
        try:
            written=0
            while written<len(raw):
                count=os.write(fd,raw[written:written+65536])
                require(count>0,'native-tool-snapshot-write')
                written+=count
            seals=fcntl.F_SEAL_WRITE|fcntl.F_SEAL_GROW|fcntl.F_SEAL_SHRINK|fcntl.F_SEAL_SEAL
            fcntl.fcntl(fd,fcntl.F_ADD_SEALS,seals)
            require(fcntl.fcntl(fd,fcntl.F_GET_SEALS)&seals==seals,'native-tool-unsealed')
            return fd
        except BaseException:
            os.close(fd)
            raise

    def _image_path(self,pid,path):
        root=Path(f'/proc/{pid}/root')
        path=Path(path)
        relative=path.relative_to(root)
        require('..' not in relative.parts,'native-image-path')
        device=os.stat(root).st_dev
        current=root
        for part in relative.parts:
            current=current/part
            info=current.lstat()
            require(not stat.S_ISLNK(info.st_mode) and info.st_dev==device,
                    'native-image-symlink-or-mount')
        return path

    def _image_read(self,pid,path,maximum=65536):
        path=self._image_path(pid,path)
        require(stat.S_ISREG(path.lstat().st_mode),'native-image-regular-file')
        return self.view.read(path,maximum)

    def qualify(self):
        # A journal observes execs after the fact. It is not a hard launch quota.
        # No native worker may be released through this incomplete candidate.
        require(self.profile.manifest()['execAdmissionEnforced'] is True,
                'native-pre-exec-admission-unimplemented')
        self.view.guard()
        require(len(self.qualification_receipts)<5,'native-qualification-count')
        require(self.session.timeline.index==len(self.qualification_receipts),'native-qualification-phase-order')
        first_phase=self.phase_start is None
        if self.phase_start is not None:
            self.phase_receipts.append(self._phase_cost())
        start=time.monotonic_ns();cpu=time.process_time_ns();before=self.view.bytes_read
        children=resource.getrusage(resource.RUSAGE_CHILDREN)
        child_cpu=children.ru_utime+children.ru_stime
        self.phase_start=(start,cpu,before,self.session.timeline.index)
        self.view.remaining=max(0,512*1024**2-(self.view.bytes_read if first_phase else 0))
        succeeded=False
        try:
            from .forecast_launcher import RootGateClient
            require(type(self.root_gate) is RootGateClient and self.root_gate.identity==self.profile.identity,
                    'native-root-gate-required')
            self.root_gate.phase(self.session.timeline.index,self.session.timeline.phase_deadline_ns)
            self._qualify()
            succeeded=True
        finally:
            self.qualification_receipts.append({'phaseIndex':self.session.timeline.index,
                'succeeded':succeeded,'instrumentedReadBytes':self.view.bytes_read-before,
                'verifierProcessCpuNs':time.process_time_ns()-cpu,
                'reapedOperatorChildrenCpuNs':round(((lambda r:r.ru_utime+r.ru_stime)(
                    resource.getrusage(resource.RUSAGE_CHILDREN))-child_cpu)*10**9),'wallNs':time.monotonic_ns()-start,
                'memoryScope':'operator host; outside worker slice; peak RSS not established',
                'executionAuthorization':False,'actualProfileAdmitted':False})
            if not succeeded:
                self.qualified=None

    def _qualify(self):
        self.view.guard()
        uname=os.uname()
        version=re.match(r'([0-9]+)\.([0-9]+)',uname.release)
        require(uname.machine=='aarch64' and version and tuple(map(int,version.groups()))>=(6,12)
                and os.cpu_count()==1,'native-linux-host-contract')
        work=self.session.work;work.observe_frozen()
        self.census.qualify(work.path.parent.parent.stat().st_ino)
        self.known_execs.add((work.worker_pid,'worker'))
        pid=work.worker_pid;profile=self.profile
        require(os.getpgid(pid)==pid,'native-worker-process-group')
        status=self.view.read(f'/proc/{pid}/status').decode()
        for key in ('Uid','Gid'):
            values=re.findall(r'^'+key+r':\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+([0-9]+)$',status,re.M)
            require(len(values)==1 and all(int(v)==profile.uid for v in values[0]),'native-worker-uid')
        require(re.findall(r'^NoNewPrivs:\s+([01])$',status,re.M)==['1']
                and re.findall(r'^CapEff:\s+([0-9a-f]+)$',status,re.M)==['0000000000000000'],
                'native-worker-privilege')
        manager=self.view.executable(1,profile.manager_sha256)
        unit=work.path.name
        hardening={'User':str(profile.uid),'Group':str(profile.uid),'ProtectHome':'yes',
            'ProtectKernelTunables':'yes','ProtectKernelModules':'yes','ProtectKernelLogs':'yes',
            'ProtectClock':'yes','RootImageOptions':'root:ro','CapabilityBoundingSet':'',
            'AmbientCapabilities':'','RestrictNamespaces':'yes','RestrictSUIDSGID':'yes',
            'RestrictRealtime':'yes','LockPersonality':'yes','ProtectProc':'invisible','ProcSubset':'pid',
            'InaccessiblePaths':'/dev/shm /run /tmp /var/tmp',
            'Restart':'no','KillMode':'control-group','SendSIGKILL':'yes','OOMPolicy':'kill'}
        properties=['RootImage','Delegate','ProtectSystem','PrivateDevices','PrivateNetwork',
                    'NoNewPrivileges','ProtectControlGroups','ControlGroup','MainPID',*hardening]
        manager_version=self._tool('/usr/bin/systemctl','--version').splitlines()[0]
        require(re.match(r'^systemd 261(?:\.3(?: |$)| \(261\.3\))',manager_version),
                'native-manager-version')
        raw=self._tool('/usr/bin/systemctl','show',unit,'--property='+','.join(properties))
        pairs=[line.split('=',1) for line in raw.splitlines()]
        require(all(len(p)==2 for p in pairs) and len({p[0] for p in pairs}) == len(pairs), 'native-manager-fields')
        props=dict(pairs)
        expected={'RootImage':'/var/lib/agent-braid/images/'+profile.image_sha256+'.raw',
                  'Delegate':'no','ProtectSystem':'strict','PrivateDevices':'yes','PrivateNetwork':'yes',
                  'NoNewPrivileges':'yes','ProtectControlGroups':'yes',
                  'ControlGroup':'/'+str(work.path.relative_to('/sys/fs/cgroup')),'MainPID':str(pid)}
        expected.update(hardening)
        require(props == expected, 'native-manager-readback')
        require(self.view.hash_file(expected['RootImage'],512*1024*1024) == profile.image_sha256, 'native-image-pin')
        rows=mount_rows(self.view.read(f'/proc/{pid}/mountinfo'))
        require('/' in rows and 'ro' in rows['/']['mount'], 'native-root-not-readonly')
        device=rows['/']['device']
        require(re.fullmatch('[0-9]+:[0-9]+',device), 'native-root-device')
        table=self._tool('/usr/sbin/dmsetup','table','--target','verity','/dev/block/'+device).split()
        require(len(table) >= 13 and table[2]=='verity' and table[10]=='sha256'
                and table[11] == profile.root_hash, 'native-verity-root')
        # Every ordinary writable filesystem must be a phase tmpfs. Pseudo
        # devices/proc are constrained separately by manager settings/cgroup.
        scratch='/work' if self.session.timeline.index < 3 else '/scratch'
        for path,row in rows.items():
            if 'rw' not in row['mount']:
                continue
            require(path == scratch or row['type'] in ('proc','devpts')
                    or path == '/dev' and row['type']=='tmpfs', 'native-uncovered-write-mount')
        dev=os.stat(f'/proc/{pid}/root/dev')
        require(dev.st_uid==0 and not dev.st_mode & 0o022,'native-device-directory-writable')
        if scratch == '/scratch':
            require('/work' in rows and 'ro' in rows['/work']['mount'], 'native-verifier-work-writable')
        require(scratch in rows and rows[scratch]['type']=='tmpfs' and
                {'nosuid','nodev','noexec'} <= rows[scratch]['mount'] and
                'noswap' in rows[scratch]['options'], 'native-scratch-mount')
        self._quota_readback(rows[scratch])
        self._cgroup_quotas()
        gitpath=self._image_path(pid,f'/proc/{pid}/root/opt/agent-braid/bin/git')
        require(not Path(gitpath).is_symlink() and self.view.hash_file(gitpath,32*1024*1024)==self.git_sha,
                'native-git-artifact')
        gitstat=os.stat(gitpath);git_identity=(gitstat.st_dev,gitstat.st_ino)
        # Future native qualification READS and hashes the closed tree/blob object
        # closure. No Git command or blob content is executed. Costs are retained.
        from .forecast_recipe import verify_loose_inputs
        gitdir=self._image_path(pid,f'/proc/{pid}/root/opt/agent-braid/inputs/repository/.git')
        for name in ('objects','refs','refs/heads'):
            self._image_path(pid,gitdir/name)
        from .forecast_recipe import IMAGE_GIT_CONFIG,BASE
        require(self._image_read(pid,gitdir/'config')==IMAGE_GIT_CONFIG
                and self._image_read(pid,gitdir/'shallow')==BASE.encode()+b'\n','native-source-git-config')
        for name in ('objects/info/alternates','info/grafts','config.worktree','commondir'):
            require(not os.path.lexists(gitdir/name),'native-source-git-redirect')
        require(self._image_read(pid,gitdir/'HEAD')==b'ref: refs/heads/admission-base\n'
                and self._image_read(pid,gitdir/'refs/heads/admission-base')==BASE.encode()+b'\n',
                'native-source-head')
        require(sorted(p.name for p in (gitdir/'refs/heads').iterdir())==['admission-base'],
                'native-source-extra-head')
        for name in ('hooks','refs/replace','refs/tags','objects/pack','objects/info'):
            path=gitdir/name
            require(not path.is_symlink(),'native-source-git-admin-symlink')
            if path.exists():
                self._image_path(pid,path)
                require(not self._names(path,1),'native-source-git-extra')
        require(not gitdir.is_symlink() and self._names(gitdir.parent,8)==['.git'],
                'native-source-working-tree')
        require(set(self._names(gitdir/'refs',8)) <= {'heads','tags','replace'},'native-source-extra-refs')
        inventory=set()
        for prefix in self._names(gitdir/'objects',258):
            if prefix in ('info','pack'):
                continue
            require(re.fullmatch('[0-9a-f]{2}',prefix) and not (gitdir/'objects'/prefix).is_symlink(),
                    'native-source-object-directory')
            for tail in self._names(gitdir/'objects'/prefix,20000):
                require(re.fullmatch('[0-9a-f]{38}',tail) and
                        not (gitdir/'objects'/prefix/tail).is_symlink(),'native-source-object-name')
                inventory.add(prefix+tail)
                require(len(inventory)<=20000,'native-source-object-count')
        request=verify_loose_inputs(gitdir,lambda p,n:self._image_read(pid,p,n),expected_inventory=inventory)
        require(request == self.recipe['request'], 'native-source-inputs')
        source=Path(f'/proc/{pid}/root/opt/agent-braid/source')
        from .forecast_admission import source_digest
        require(source_digest(source,reader=lambda p:self._image_read(pid,p,16*1024*1024))
                ==profile.source_digest, 'native-source-drift')
        require(hashlib.sha256(self._image_read(pid,f'/proc/{pid}/root/opt/agent-braid/fc1/recipe.json')).hexdigest()
                == profile.recipe_sha256, 'native-mounted-recipe-drift')
        work.observe_frozen()
        if self.qualified is not None and self.qualified['pid']==pid:
            require(self.view.state(pid)['start']==self.qualified['start']
                    and self.child_observer.git_identity==git_identity,'native-work-identity-drift')
        if self.qualified is None or self.qualified['pid'] != pid:
            if self.child_observer is not None:
                require(not self.child_observer.children,'native-prior-children-retained')
                self.child_observer.close()
            self.binding=None
            self.child_observer=ChildObserver(worker_pid=pid,
                worker_cgroup='/'+str(work.path.relative_to('/sys/fs/cgroup')),
                git_sha256=self.git_sha,working_directory=scratch,git_identity=git_identity)
            self.child_observer.view=self.view
        self.qualified={'pid':pid,'start':self.view.state(pid)['start'],
                        'phase':self.session.timeline.index,'scratch':scratch,'manager':manager}

    def bootstrap(self):
        self.view.guard()
        from .forecast_linux_profile import STEPS
        index=self.session.timeline.index
        require(index in (0,3,4) and self.qualified is not None,'native-bootstrap-state')
        return {'profileIdentity':self.profile.identity,'phase':STEPS[index],
                'originNs':self.session.timeline.origin_ns,'deadlineNs':self.session.timeline.deadline_ns,
                'verificationOf':None if index==0 else self.session.prior_binding,
                'profileConfig':self.profile.external_config()}

    def accept(self,sock):
        """Accept one already connected channel; never creates/starts a service."""
        from .forecast_operator_bridge import accept_binding
        return accept_binding(sock,self.session,worker_uid=self.profile.uid,
            worker_pid=self.session.work.worker_pid,bootstrap=self.bootstrap(),
            validate_binding=self.validate_binding,observe=self.observe,observe_child=self.observe_child)

    def _names(self,path,limit):
        result=[]
        with os.scandir(path) as entries:
            for entry in entries:
                require(len(result)<limit,'native-directory-bound')
                result.append(entry.name)
        return sorted(result)

    def _phase_cost(self):
        start,cpu,before,index=self.phase_start
        return {'phaseIndex':index,'wallNs':time.monotonic_ns()-start,
                'verifierProcessCpuNs':time.process_time_ns()-cpu,
                'instrumentedReadBytes':self.view.bytes_read-before,
                'operatorPeakRssEstablished':False,'unreapedChildrenCpuUnknown':True}

    def receipt(self):
        return {'version':'agent-braid-native-provider-software-receipt-v1',
                'qualifications':deepcopy(self.qualification_receipts),
                'completedPhases':deepcopy(self.phase_receipts),
                'currentPhase':None if self.phase_start is None else self._phase_cost(),
                'operatorToolLaunches':deepcopy(self.native_tools),
                'workerQuotaScope':'2GiB/64 tasks; aggregate 3GiB/96 tasks; operator 512MiB/16 tasks; 1 CPU shared',
                'gitLedgerScope':'Python requests reconciled against independent numeric exec census',
                'execCensus':deepcopy(self.census_ledger.rows),'execGateReceipts':deepcopy(self.exec_gate_receipts),
                'execAdmissionEnforced':False,'rootGateBound':self.root_gate is not None,
                'rootGateClosure':deepcopy(getattr(self,'root_gate_closure',None)),
                'operatorPeakRssEstablished':False,'wholeFlowCleanupVerified':False,
                'actualProfileAdmitted':False,'executionAuthorization':False}

    def observe_child(self,pid,event,invocation):
        require(self.qualified is not None and self.child_observer is not None,
                'native-child-provider-unqualified')
        observed=self.child_observer(pid,event,invocation)
        if event=='launched': self.known_execs.add((pid,'git'))
        return observed

    def close_phase(self, *, empty=False):
        """Bounded readback at a quiescent boundary; never admits later execution."""
        self.view.guard()
        frozen=self.session.work.observe_empty if empty else self.session.work.observe_frozen
        rows=self.census.snapshot(len(self.census_ledger.events),frozen=frozen)
        if self.root_gate is not None:
            from .forecast_exec_census import decode_event
            from .forecast_launcher import reconcile_exec_permits
            receipt=self.root_gate.phase_receipt(self.session.timeline.index)
            events=[decode_event(raw,len(self.census_ledger.events)+i+1,self.census.cgroup)
                    for i,raw in enumerate(rows)]
            receipt['reconciliation']=reconcile_exec_permits(events,receipt)
            self.exec_gate_receipts.append(receipt)
        return self.census_ledger.reconcile(rows,cgroup=self.census.cgroup,
            phase=self.session.timeline.index,deadline_ns=self.session.timeline.phase_deadline_ns,
            known=self.known_execs)

    def close_control(self):
        """Terminal root-child reap is part of the same phase, before success."""
        require(self.session.timeline.index==4,'native-terminal-control-close')
        start=time.monotonic_ns();cpu=time.process_time_ns()
        before=resource.getrusage(resource.RUSAGE_CHILDREN)
        try:
            require(self.root_gate is not None,'native-root-gate-required')
            self.root_gate.stop()
        finally:
            after=resource.getrusage(resource.RUSAGE_CHILDREN)
            self.root_gate_closure={'wallNs':time.monotonic_ns()-start,
                'verifierProcessCpuNs':time.process_time_ns()-cpu,
                'reapedChildrenCpuNs':round((after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime)*10**9),
                'cleanupConfirmed':bool(self.root_gate and self.root_gate.cleanup_confirmed),
                'exitStatus':None if self.root_gate is None else self.root_gate.exit_status,
                'nativeCoverageAccepted':False}
            self.census.close();self.qualified=None
            if self.child_observer is not None:self.child_observer.close()

    def abort(self):
        try:
            if self.root_gate is not None:self.root_gate.stop()
        finally:
            self.census.close()
            self.qualified=None
            if self.child_observer is not None:self.child_observer.close()

    def _cgroup_quotas(self):
        worker=self.session.work.path.parent
        aggregate=worker.parent
        root=aggregate/('fc1'+self.profile.identity+'-root.slice')
        operator=root/('fc1'+self.profile.identity+'-operator.service')
        expected='/'+str(operator.relative_to('/sys/fs/cgroup'))
        require(self.view.read('/proc/self/cgroup').decode().strip()=='0::'+expected,
                'native-operator-cgroup')
        executable=Path('/proc/self/exe')
        identity=os.stat(executable)
        pair=(identity.st_dev,identity.st_ino)
        if self.operator_identity is None:
            self.view.executable(os.getpid(),self.profile.operator_sha256)
            after=os.stat(executable)
            require(pair==(after.st_dev,after.st_ino),'native-operator-executable-race')
            self.operator_identity=pair
        require(pair==self.operator_identity,'native-operator-executable-replaced')
        for cgroup,memory,tasks in ((worker,2147483648,64),(aggregate,3221225472,96),
                                    (root,536870912,16)):
            cpu=self.view.read(cgroup/'cpu.max').decode().split()
            require(len(cpu)==2 and cpu[0]!='max' and 0<int(cpu[0])<=int(cpu[1]), 'native-cpu-quota')
            for name,value in [('memory.max',memory),('memory.swap.max',0),('pids.max',tasks)]:
                require(self.view.read(cgroup/name).decode().strip()==str(value), 'native-cgroup-quota')

    def _quota_readback(self, worker_row=None):
        index=self.session.timeline.index
        phase='prepare' if index<3 else ('verify' if index==3 else 'terminal')
        path='/run/fc1/'+self.profile.identity+'/'+phase
        rows=mount_rows(self.view.read('/proc/self/mountinfo'))
        require(path in rows,'native-phase-mount-absent')
        row=rows[path]
        if index<3:
            size,inodes=self.session.quota.bytes,self.session.quota.inodes
        else:
            limit=self.profile.limits[index];size,inodes=limit.storage_bytes,limit.inodes
        options=row['mount']|row['options']
        require(row['type']=='tmpfs' and
                {'rw','nosuid','nodev','noexec','noswap','mode=700',
                 'uid='+str(self.profile.uid),'gid='+str(self.profile.uid),
                 'size='+str(size//1024)+'k','nr_inodes='+str(inodes)}<=options,
                'native-phase-quota-readback')
        if worker_row is not None:
            require(worker_row['device']==row['device'],'native-scratch-device-mismatch')

    def validate_binding(self,binding):
        self.view.guard()
        q=self.qualified;timeline=self.session.timeline;profile=self.profile
        require(q is not None and q['pid']==self.session.work.worker_pid and q['phase']==timeline.index,
                'native-worker-not-qualified')
        if timeline.index == 4:
            return binding == {'terminalIdentity':profile.identity}
        expected={'version':'agent-braid-git-admission-boundary-v4',
            'workerPid':q['pid'],'workerPgid':q['pid'],'root':q['scratch'],
            'sourceRoot':'/opt/agent-braid/inputs/repository','sourceDigest':profile.source_digest,
            'gitExecutable':'/opt/agent-braid/bin/git','gitSha256':self.git_sha,
            'mode':profile.mode,'finalVerifier':'runtime' if profile.mode=='serial' else 'policy',
            'phaseRequests':{p.phase:p.requests for p in profile.limits[:4]},
            'phaseNs':{p.phase:p.wall_seconds*10**9 for p in profile.limits[:4]},
            'phaseBytes':{p.phase:p.storage_bytes for p in profile.limits[:4]},
            'terminalNs':profile.limits[-1].wall_seconds*10**9,'terminalBytes':profile.limits[-1].storage_bytes,
            'maxActive':1 if profile.mode=='serial' else 2,'wholeFlowDeadlineNs':timeline.deadline_ns,
            'flowOriginNs':timeline.origin_ns,'externalLaunchLedger':True}
        from .forecast_git_launch import INPUT_COMMITS,INPUT_PATCHES
        from .forecast_recipe import BASE
        expected.update(inputCommits=list(INPUT_COMMITS),inputPatchSha256=list(INPUT_PATCHES),baseCommit=BASE)
        require(all(binding.get(k)==v for k,v in expected.items()), 'native-binding-config')
        require(set(binding)==set(expected)|{'scopeNonce','verificationOf','verificationWorkRoot'}
                and re.fullmatch('[0-9a-f]{32}',binding['scopeNonce']), 'native-binding-fields')
        require((timeline.index==0 and binding['verificationOf'] is None and binding['verificationWorkRoot'] is None)
                or timeline.index==3 and binding['verificationOf'] == getattr(self.session,'prior_binding',None)
                and binding['verificationOf'] is not None and binding['verificationWorkRoot']=='/work'
                and getattr(self.session,'prior_empty',False), 'native-prior-work-binding')
        require(self.binding is None or self.binding == binding, 'native-binding-replaced')
        self.binding=deepcopy(binding)
        return True

    def observe(self,binding,phase,deadline,invocation):
        self.view.guard()
        q=self.qualified;timeline=self.session.timeline
        require(q is not None and self.binding == binding and q['phase']==timeline.index
                and q['pid']==self.session.work.worker_pid and timeline.active,
                'native-qualification-stale')
        require(self.view.state(q['pid'])['start']==q['start'], 'native-worker-reused')
        now=time.monotonic_ns()
        require(now < deadline == timeline.phase_deadline_ns <= timeline.deadline_ns, 'native-deadline')
        watchdog=self.session.watchdog
        require(watchdog.pid is not None and watchdog.write_fd is not None
                and os.waitpid(watchdog.pid,os.WNOHANG)==(0,0), 'native-watchdog-dead')
        self._cgroup_quotas()
        self.census.check_live()
        cgroup=self.session.work.path.parent
        index=timeline.index;limit=self.profile.limits[index]
        scratch=Path('/run/fc1')/self.profile.identity/('prepare' if index<3 else 'verify')
        self._quota_readback()
        usage=os.statvfs(scratch)
        require(usage.f_blocks*usage.f_frsize <= sum(p.storage_bytes for p in self.profile.limits[:index+1]),
                'native-scratch-cap')
        future=sum(p.storage_bytes for p in self.profile.limits[index+1:])
        # Future tmpfs allocations need an actual physical-memory reserve too.
        current=int(self.view.read(cgroup/'memory.current').decode())
        available=2147483648-current
        meminfo=self.view.read('/proc/meminfo').decode()
        physical=re.findall(r'^MemAvailable: +([0-9]+) kB$',meminfo,re.M)
        require(len(physical)==1 and available >= future and int(physical[0])*1024 >= future,
                'native-future-memory-reserve')
        observation={'bindingDigest':digest(binding),'containedProcessTree':True,'hardQuota':True,
            'externalWatchdog':True,'allWriteRootsCovered':True,'sourceInputsVerified':True,
            'immutableExecutable':True,'watchdogDeadlineNs':deadline,'expiresNs':min(deadline,now+10**8),
            'phaseQuotaBytes':limit.storage_bytes,'availableBytes':usage.f_bavail*usage.f_frsize+future}
        if index==3:
            observation.update(terminatedWorkBindingDigest=binding['verificationOf'],
                terminatedWorkDeadlineNs=timeline.deadline_ns,priorWorkTerminated=True)
        if invocation is not None:
            argv=invocation.get('argv',[])
            require(set(invocation)=={'argv','env','cwd','inputSha256','inheritedFds'} and
                    len(argv)>=4 and argv[0]==binding['gitExecutable'] and argv[1]=='-C'
                    and (argv[2]==binding['sourceRoot'] or argv[2].startswith('/work/')
                         or argv[2].startswith(q['scratch']+'/'))
                    and invocation['cwd'] is None, 'native-invocation')
            observation.update(launchAllowed=True,launchDigest=digest(invocation),readOnlyVerification=index==3)
        return observation
