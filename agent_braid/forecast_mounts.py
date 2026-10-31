# SPDX-License-Identifier: AGPL-3.0-only
"""Private root-owner tmpfs lifecycle; never runs on import or construction.

No mount units, shell, mount/umount helper, lazy detach or automatic retry.
The owner must remain in PID1's mount namespace. Native qualification is still
required; syscall/readback mocks do not accredit isolation or actual quotas.
"""
import ctypes
import os
import stat
import time

from .forecast_bootstrap import bootstrap_ready
from .forecast_data import integer, require
from .forecast_native import KernelView, mount_rows

PHASE_INDEX = {'prepare': 0, 'verify': 3, 'terminal': 4}


class RootMountOwner:
    def __init__(self, profile, origin_ns, *, view=None, clock=time.monotonic_ns):
        self.profile = profile
        self.origin_ns = integer(origin_ns, 1)
        self.deadline = origin_ns+sum(p.wall_seconds for p in profile.limits)*10**9
        self.path = '/run/fc1/'+profile.identity
        self.view = KernelView() if view is None else view
        if view is None: self.view.remaining = 256*1024**2
        self.clock = clock
        self.fd = None
        self.mounts = {}
        self.attempted = set()
        self.records = []
        self.failed = False
        self.closed = False

    def _ready(self):
        bootstrap_ready(self.profile)
        self.view.guard()
        require(not self.closed, 'mount-owner-closed')
        own = os.stat('/proc/self/ns/mnt')
        init = os.stat('/proc/1/ns/mnt')
        require((own.st_dev, own.st_ino) == (init.st_dev, init.st_ino),
                'mount-owner-wrong-namespace')

    def open(self):
        self._ready()
        require(self.fd is None and not self.failed and self.clock() < self.deadline,
                'mount-owner-open-state')
        fd = os.open('/run', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            for part in ('fc1', self.profile.identity):
                child = os.open(part, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC, dir_fd=fd)
                os.close(fd); fd = child
                info = os.fstat(fd)
                require(info.st_uid == 0 and not info.st_mode & 0o077, 'mount-owner-directory')
            self.fd = fd; fd = None
        finally:
            if fd is not None: os.close(fd)

    def _observe(self, phase):
        raw = self.view.read('/proc/self/mountinfo', 1024**2)
        path = self.path+'/'+phase
        rows = mount_rows(raw)
        if path not in rows: return None
        row = rows[path]
        ids = [line.split()[0] for line in raw.decode().splitlines() if line.split()[4] == path]
        require(len(ids) == 1 and ids[0].isdigit(), 'mount-owner-mount-id')
        return {**row, 'mountId': int(ids[0])}

    def _verify(self, phase, size, inodes):
        row = self._observe(phase)
        required = {'rw','nosuid','nodev','noexec','noswap','mode=700',
                    'uid='+str(self.profile.uid), 'gid='+str(self.profile.uid),
                    'size='+str(size//1024)+'k', 'nr_inodes='+str(inodes)}
        require(row is not None and row['type'] == 'tmpfs' and
                required <= row['mount']|row['options'], 'mount-owner-quota-readback')
        prior = self.mounts.get(phase)
        require(prior is None or (row['mountId'], row['device']) ==
                (prior['mountId'], prior['device']), 'mount-owner-replaced')
        return {**row, 'bytes': size, 'inodes': inodes}

    def _libc(self):
        libc = ctypes.CDLL(None, use_errno=True)
        libc.mount.argtypes = (ctypes.c_char_p,ctypes.c_char_p,ctypes.c_char_p,
                               ctypes.c_ulong,ctypes.c_void_p)
        libc.mount.restype = ctypes.c_int
        libc.umount2.argtypes = (ctypes.c_char_p,ctypes.c_int)
        libc.umount2.restype = ctypes.c_int
        return libc

    def _operation(self, phase, event):
        row = {'phase': phase, 'event': event, 'attemptedAtNs': self.clock(),
               'cpuStartNs': time.process_time_ns(), 'readStartBytes': self.view.bytes_read,
               'syscallAttempted': False, 'succeeded': False, 'closedAtNs': None}
        self.records.append(row)
        return row

    def _finish(self, row):
        row.update(closedAtNs=self.clock(), cpuNs=time.process_time_ns()-row.pop('cpuStartNs'),
                   readBytes=self.view.bytes_read-row.pop('readStartBytes'))

    def create(self, phase, *, deadline_ns):
        self._ready(); integer(deadline_ns, self.origin_ns, self.deadline)
        require(not self.failed and self.fd is not None and phase in PHASE_INDEX and
                phase not in self.attempted and self.clock() < deadline_ns,
                'mount-owner-create-state')
        require(list(self.mounts) == list(PHASE_INDEX)[:list(PHASE_INDEX).index(phase)],
                'mount-owner-phase-order')
        self.attempted.add(phase)
        row = self._operation(phase, 'create')
        try:
            limit = self.profile.limits[PHASE_INDEX[phase]]
            size, inodes = limit.storage_bytes, limit.inodes
            require(size % 4096 == 0 and self._observe(phase) is None, 'mount-owner-preexisting')
            os.mkdir(phase, 0o700, dir_fd=self.fd)
            target = ('/proc/self/fd/'+str(self.fd)+'/'+phase).encode('ascii')
            options = ('noswap,size='+str(size)+',nr_inodes='+str(inodes)+
                       ',mode=0700,uid='+str(self.profile.uid)+',gid='+str(self.profile.uid)).encode('ascii')
            libc = self._libc(); row['syscallAttempted'] = True
            # The syscall may have taken effect even if its result is lost.
            self.mounts[phase] = None
            require(libc.mount(b'tmpfs', target, b'tmpfs', 2|4|8, options) == 0,
                    'mount-owner-create-failed')
            self.mounts[phase] = self._verify(phase, size, inodes)
            require(self.clock() < deadline_ns, 'mount-owner-create-late')
            row['succeeded'] = True
        except BaseException:
            self.failed = True
            raise
        finally: self._finish(row)

    def advance(self, phase, *, frozen_work):
        self._ready()
        require(not self.failed and self.fd is not None and phase in ('grant','dispatch')
                and 'prepare' in self.mounts, 'mount-owner-advance-state')
        from .forecast_linux_profile import WorkQuota
        require(type(frozen_work.profile) is type(self.profile) and
                frozen_work.profile.identity == self.profile.identity, 'mount-owner-work-binding')
        if not hasattr(self, 'quota'): self.quota = WorkQuota(self.profile)
        row = self._operation(phase, 'resize')
        try:
            before = self.mounts['prepare']
            require(before is not None, 'mount-owner-unverified-create')
            self._verify('prepare', before['bytes'], before['inodes'])
            row['syscallAttempted'] = True
            self.quota.advance(phase, frozen_work=frozen_work)
            self.mounts['prepare'] = self._verify('prepare', self.quota.bytes, self.quota.inodes)
            row['succeeded'] = True
        except BaseException:
            self.failed = True
            raise
        finally: self._finish(row)

    def close_all(self, scope):
        """After independent consumer emptiness, one non-lazy syscall per mount.

        scope is the retained kernel-capability provider, never a JSON assertion.
        Failure on one mount does not skip the remaining cleanup attempts.
        """
        self._ready()
        from .forecast_supervisor import ExecutionScope
        require(type(scope) is ExecutionScope and scope.profile.identity == self.profile.identity,
                'mount-owner-scope-binding')
        scope.verify_plan(scope.plan)
        require(all(not row['populated'] for row in scope.snapshot()), 'mount-owner-live-consumers')
        require(self.fd is not None, 'mount-owner-not-open')
        first = None
        for phase in reversed(tuple(self.mounts)):
            row = self._operation(phase, 'close')
            try:
                require(phase not in {r['phase'] for r in self.records[:-1] if r['event'] == 'close'},
                        'mount-owner-close-retry')
                prior = self.mounts[phase]
                require(prior is not None, 'mount-owner-unverified-mount')
                self._verify(phase, prior['bytes'], prior['inodes'])
                target = ('/proc/self/fd/'+str(self.fd)+'/'+phase).encode('ascii')
                row['syscallAttempted'] = True
                require(self._libc().umount2(target, 0) == 0, 'mount-owner-close-busy-or-failed')
                require(self._observe(phase) is None, 'mount-owner-still-mounted')
                require(self.clock() < self.deadline, 'mount-owner-close-late')
                row['succeeded'] = True
            except BaseException as error:
                self.failed = True
                if first is None: first = error
            finally: self._finish(row)
        self.closed = True
        try: os.close(self.fd)
        finally: self.fd = None
        if first is not None: raise first

    def receipt(self):
        from copy import deepcopy
        return {'version': 'fc1-root-mount-lifecycle-v1', 'profileIdentity': self.profile.identity,
                'originNs': self.origin_ns, 'deadlineNs': self.deadline,
                'records': deepcopy(self.records), 'failed': self.failed,
                'nativeCoverageAccepted': False, 'executionAuthorization': False}
