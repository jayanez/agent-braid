# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-only Linux admission profile compiler; never installs or starts units.

Rendered system services require native qualification before use. In particular,
unit text is not evidence that a kernel honoured its directives. No model/client
payload can supply the image authority or turn a compiled profile into a grant.
"""
from dataclasses import dataclass, field
import hashlib
import json
import re
from pathlib import Path
import ctypes
import os
import sys
import select
import struct
import time
import threading

from .forecast_admission import PHASES, PhaseLedger, source_envelope
from .forecast_data import digest, integer, pin, require
from .forecast_git_launch import INPUT_COMMITS, INPUT_PATCHES

MIB = 1024 * 1024
STEPS = (*PHASES, 'terminal')
PATCH_BYTES = 71431
BASE = '48f4226db1e1b0565b1f8faf0eca81c150a65d30'


def proposed_limits(root, *, mode):
    """Explicit *proposal* of abort ceilings, never default launch allocations.

    Internal Git time/scratch sums plus fixed, visible non-Git/output allowances.
    Allowances are operator risk choices, not estimates of required work. A run
    may legitimately fail within them. No measured minimum is inferred.
    """
    route = 'runtime' if mode == 'serial' else 'policy'
    envelope = source_envelope(root, mode=mode, final_verifier=route)
    phases = []
    for row in envelope['phases']:
        stages = row['replayBudgets'] + row['runtimeBudgets']
        phases.append({
            'phase': row['phase'], 'requests': row['gitRequests'],
            'wallSeconds': row['internalCapSumSeconds'] + 30,
            'storageBytes': ((stages * 64 * MIB + PATCH_BYTES + 8 * MIB + 4095) // 4096) * 4096,
            'inodes': 65536,
        })
    phases.append({'phase': 'terminal', 'requests': 0, 'wallSeconds': 30,
                   'storageBytes': 8 * MIB, 'inodes': 4096})
    return {'mode': mode, 'finalVerifier': route, 'sourceDigest': envelope['sourceDigest'],
            'phases': phases, 'wallSeconds': sum(p['wallSeconds'] for p in phases),
            'storageBytes': sum(p['storageBytes'] for p in phases),
            'gitRequests': envelope['gitRequests'],
            'basis': 'conditional Git cap sums; 30s non-Git per phase; 8MiB output per phase; '
                     '64MiB per internal Git budget plus selected patch bytes; 30s/8MiB terminal',
            'status': 'proposed-abort-ceilings-owner-acceptance-pending',
            'minimumCost': None, 'completionGuaranteed': False,
            'executionAuthorization': False}


@dataclass(frozen=True)
class PhaseLimit:
    phase: str
    requests: int
    wall_seconds: int
    storage_bytes: int
    inodes: int

    def __post_init__(self):
        require(self.phase in STEPS, 'profile-phase')
        integer(self.requests, 0 if self.phase == 'terminal' else 1)
        require(self.phase != 'terminal' or self.requests == 0, 'profile-terminal-no-git')
        integer(self.wall_seconds, 3)
        integer(self.storage_bytes, 4096)
        require(self.storage_bytes % 4096 == 0, 'profile-page-aligned-quota-required')
        integer(self.inodes, 1)


@dataclass(frozen=True)
class LinuxAdmissionProfile:
    """Immutable configuration, supplied by the operator, not an admission receipt.

    The image must have one verity-protected root, no separate writable partitions,
    and contain source, both inputs and the trusted worker program. No host checkout
    is mounted. Runtime/compiler/manager identities are independent named pins.
    """
    mode: str
    image_sha256: str
    root_hash: str
    source_digest: str
    manager_sha256: str
    limits: tuple[PhaseLimit, ...]
    uid: int
    compiler_sha256: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'compiler_sha256', hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        require(self.mode in ('serial', 'parallel'), 'profile-mode')
        for value in (self.image_sha256, self.root_hash, self.source_digest, self.manager_sha256):
            pin(value)
        require(type(self.limits) is tuple and all(type(p) is PhaseLimit for p in self.limits)
                and tuple(p.phase for p in self.limits) == STEPS, 'profile-phase-order')
        integer(self.uid, 60000, 64999)
        require(sum(p.storage_bytes for p in self.limits) <= 1536 * MIB,
                'profile-retained-storage-ceiling')

    def manifest(self):
        return {'version': 'agent-braid-linux-admission-profile-v1', 'mode': self.mode,
                'imageSha256': self.image_sha256, 'rootHash': self.root_hash,
                'sourceDigest': self.source_digest, 'managerSha256': self.manager_sha256,
                'compilerSha256': self.compiler_sha256,
                'baseCommit': BASE, 'inputCommits': list(INPUT_COMMITS),
                'inputPatchSha256': list(INPUT_PATCHES), 'uid': self.uid,
                'maxWorkers': 1 if self.mode == 'serial' else 2,
                'cpuPercent': 100, 'memoryBytes': 2048 * MIB, 'swapBytes': 0,
                'tasks': 64, 'phases': [vars(p).copy() for p in self.limits],
                'wallSeconds': sum(p.wall_seconds for p in self.limits),
                'storageBytes': sum(p.storage_bytes for p in self.limits),
                'retries': 0, 'executionAuthorization': False,
                'actualProfileAdmitted': False}

    @property
    def identity(self):
        return digest(self.manifest())

    def units(self, *, remaining_seconds):
        """Render only. No [Install], shell, automatic phase chain or restart.

        Re-rendering with a smaller remaining deadline does not reset the flow.
        Operator supervision must keep the original origin and refuse any start
        without the remaining reserves. Native manager readback is a separate gate.
        """
        integer(remaining_seconds, 1, sum(p.wall_seconds for p in self.limits))
        require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == self.compiler_sha256,
                'profile-compiler-drift')
        identity = self.identity
        stem = 'fc1' + identity
        anchor = stem + '.service'
        image = '/var/lib/agent-braid/images/' + self.image_sha256 + '.raw'
        base = '/run/fc1/' + identity
        slice_name = stem + '.slice'
        units = {
            slice_name: '[Slice]\nCPUAccounting=yes\nCPUQuota=100%\nMemoryAccounting=yes\n'
                        'MemoryMax=2147483648\nMemorySwapMax=0\nTasksAccounting=yes\nTasksMax=64\n',
            anchor: '[Unit]\nDescription=FC1 external deadline\n'
                    '[Service]\nType=exec\nExecStart=/usr/bin/sleep ' + str(remaining_seconds) + '\n'
                    'RuntimeMaxSec=' + str(remaining_seconds) + '\nTimeoutStartSec=2\n'
                    'TimeoutStopSec=1\nKillMode=control-group\nSendSIGKILL=yes\nRestart=no\n'
                    'StandardOutput=null\nStandardError=null\n',
        }
        for limit in self.limits:
            phase = limit.phase
            if phase in ('grant', 'dispatch'):
                continue
            mount = 'run-fc1-' + identity + '-' + phase + '.mount'
            path = base + '/' + phase
            units[mount] = ('[Unit]\nDescription=FC1 reserved phase storage\n'
                            '[Mount]\nWhat=tmpfs\nWhere=' + path + '\nType=tmpfs\n'
                            'DirectoryMode=0700\nOptions=rw,nosuid,nodev,noexec,noswap,size='
                            + str(limit.storage_bytes) + ',nr_inodes=' + str(limit.inodes)
                            + ',mode=0700,uid=' + str(self.uid) + ',gid=' + str(self.uid) + '\n')
            # prepare/grant/dispatch share the ORIGINAL mutable run/grant paths.
            # Only the first phase starts a worker; external operator transitions
            # grow its work tmpfs and rearm its watchdog, never copy grants.
            prior = '' if phase == 'prepare' else (
                'BindReadOnlyPaths=' + base + '/prepare:/work\n')
            if phase == 'terminal':
                prior += 'BindReadOnlyPaths=' + base + '/verify:/prior/verify\n'
            requires = mount
            if phase != 'prepare':
                requires += ' run-fc1-' + identity + '-prepare.mount'
            if phase == 'terminal':
                requires += ' run-fc1-' + identity + '-verify.mount'
            # Two seconds activation and one second kill reserve are *inside*
            # each phase allocation, not extra uncounted time.
            runtime = max(1, min(sum(p.wall_seconds for p in self.limits[:3])
                                if phase == 'prepare' else limit.wall_seconds, remaining_seconds) - 3)
            scratch = '/work' if phase == 'prepare' else '/scratch'
            units[stem + '-' + phase + '.service'] = (
                '[Unit]\nDescription=FC1 isolated ' + phase + '\n'
                'BindsTo=' + anchor + '\nAfter=' + anchor + ' ' + requires + '\n'
                'Requires=' + requires + '\n[Service]\nType=exec\n'
                'Slice=' + slice_name + '\nUser=' + str(self.uid) + '\nGroup=' + str(self.uid)
                + '\nRootImage=' + image + '\nRootHash=' + self.root_hash + '\n'
                'RootImageOptions=root:ro\nMountAPIVFS=yes\nProtectSystem=strict\n'
                'ProtectHome=yes\nPrivateNetwork=yes\nPrivateDevices=yes\n'
                'ProtectControlGroups=yes\nProtectKernelTunables=yes\nProtectKernelModules=yes\n'
                'ProtectKernelLogs=yes\nProtectClock=yes\nNoNewPrivileges=yes\n'
                'CapabilityBoundingSet=\nAmbientCapabilities=\nRestrictNamespaces=yes\n'
                'RestrictSUIDSGID=yes\nRestrictRealtime=yes\nLockPersonality=yes\n'
                'Delegate=no\nInaccessiblePaths=/dev/shm /run /tmp /var/tmp\n'
                'ProtectProc=invisible\nProcSubset=pid\n'
                'BindPaths=' + path + ':' + scratch + '\n' + prior +
                'BindReadOnlyPaths=' + base + '/operator.sock:/operator.sock\n' +
                'WorkingDirectory=' + scratch + '\nUMask=0077\nEnvironment=HOME='
                + scratch + '/home TMPDIR=' + scratch + '/tmp\n'
                'Environment=PYTHONDONTWRITEBYTECODE=1\n'
                'ExecStart=/opt/agent-braid/bin/fc1-worker ' + identity + ' ' + phase + '\n'
                'TimeoutStartSec=2\nTimeoutStopSec=1\nRuntimeMaxSec=' + str(runtime) + '\n'
                'KillMode=control-group\nSendSIGKILL=yes\nOOMPolicy=kill\nRestart=no\n'
                'StandardInput=null\nStandardOutput=null\nStandardError=null\n')
        return units

    def validate_source(self, root):
        route = 'runtime' if self.mode == 'serial' else 'policy'
        envelope = source_envelope(root, mode=self.mode, final_verifier=route,
                                   expected_source_digest=self.source_digest)
        for limit, row in zip(self.limits, envelope['phases']):
            require(limit.requests <= row['gitRequests'], 'profile-request-cap-expanded')
        return envelope


class WorkQuota:
    """Root operator's tmpfs phase quota for the ORIGINAL work store.

    The path is derived from the immutable profile, not supplied by a worker.
    Called only after external phase closure. No mount creation or activation.
    The next cap is actual retained usage plus the next phase's allocation;
    dispatch cannot spend verifier or terminal capacity. Any uncertainty poisons
    the object. The caller must stop work on error; it cannot claim a live lease.
    """
    def __init__(self, profile):
        require(type(profile) is LinuxAdmissionProfile, 'operator-profile-required')
        self.profile = profile
        self.path = '/run/fc1/' + profile.identity + '/prepare'
        self.index = 0
        self.bytes = profile.limits[0].storage_bytes
        self.inodes = profile.limits[0].inodes
        self.failed = False

    def advance(self, phase, *, frozen_work):
        require(not self.failed, 'profile-quota-stopped')
        try:
            require(sys.platform == 'linux' and os.geteuid() == 0,
                    'linux-root-operator-required')
            require(self.index < 2 and phase == PHASES[self.index + 1], 'profile-quota-order')
            require(type(frozen_work) is FrozenWork and
                    frozen_work.profile.identity == self.profile.identity, 'profile-frozen-work-required')
            frozen_work.observe_frozen()
            require(str(Path(self.path).resolve(strict=True)) == self.path, 'profile-quota-path')
            # root-owned operator mountinfo, never a worker's file or declaration.
            self._verify_mount(self.bytes, self.inodes)
            limit = self.profile.limits[self.index + 1]
            usage = os.statvfs(self.path)
            used_bytes = (usage.f_blocks - usage.f_bfree) * usage.f_frsize
            used_inodes = usage.f_files - usage.f_ffree
            require(0 <= used_bytes <= self.bytes and 0 <= used_inodes <= self.inodes,
                    'profile-quota-usage-unverified')
            new_bytes, new_inodes = used_bytes + limit.storage_bytes, used_inodes + limit.inodes
            require(new_bytes % 4096 == 0, 'profile-page-aligned-quota-required')
            frozen_work.observe_frozen()
            options = ('rw,nosuid,nodev,noexec,noswap,size=' + str(new_bytes)
                       + ',nr_inodes=' + str(new_inodes)).encode('ascii')
            # MS_REMOUNT | MS_NOSUID | MS_NODEV | MS_NOEXEC. Only an existing,
            # verified, exact tmpfs mount can reach this operation.
            libc = ctypes.CDLL(None, use_errno=True)
            libc.mount.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
                                   ctypes.c_ulong, ctypes.c_void_p)
            libc.mount.restype = ctypes.c_int
            result = libc.mount(None, self.path.encode('ascii'), None, 32 | 2 | 4 | 8, options)
            require(result == 0, 'profile-quota-remount-failed')
            self._verify_mount(new_bytes, new_inodes)
            self.bytes, self.inodes = new_bytes, new_inodes
            self.index += 1
        except BaseException:
            self.failed = True
            raise

    def _verify_mount(self, size, inodes):
        rows = [line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
        rows = [r for r in rows if len(r) > 8 and r[4] == self.path]
        require(len(rows) == 1, 'profile-quota-mount-required')
        row = rows[0]
        separator = row.index('-')
        options = set(row[5].split(',')) | set(row[separator + 3].split(','))
        require(row[separator + 1] == 'tmpfs' and
                {'rw', 'nosuid', 'nodev', 'noexec', 'noswap', 'mode=700',
                 'uid=' + str(self.profile.uid), 'gid=' + str(self.profile.uid)} <= options,
                'profile-quota-mount-options')
        # tmpfs reports size in KiB, rounded to a page. Require page-aligned limits
        # rather than silently granting more bytes than the profile declares.
        require(size % 4096 == 0 and 'size=' + str(size // 1024) + 'k' in options
                and 'nr_inodes=' + str(inodes) in options, 'profile-quota-readback')


class FrozenWork:
    """Operator's kernel handoff; a producer cannot declare itself quiescent."""
    def __init__(self, profile, *, worker_pid, unit_phase='prepare'):
        require(type(profile) is LinuxAdmissionProfile, 'operator-profile-required')
        self.profile = profile
        self.worker_pid = integer(worker_pid, 2)
        require(unit_phase in ('prepare', 'verify', 'terminal'), 'profile-worker-unit')
        stem = 'fc1' + profile.identity
        self.path = Path('/sys/fs/cgroup') / (stem+'.slice') / (stem+'-'+unit_phase+'.service')
        self.kill_fd = None

    def arm_abort(self):
        """Open the operator's kill capability BEFORE freezing/arming a worker."""
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        require(self.kill_fd is None and Path('/sys/fs/cgroup/cgroup.controllers').is_file(),
                'profile-abort-capability-required')
        directory = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.kill_fd = os.open('cgroup.kill', os.O_WRONLY | os.O_NOFOLLOW, dir_fd=directory)
        finally:
            os.close(directory)
        self.observe_identity()

    def observe_identity(self):
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        require((self.path / 'cgroup.procs').read_text().split() == [str(self.worker_pid)],
                'profile-work-children-remain')
        require((Path('/proc') / str(self.worker_pid) / 'cgroup').read_text().splitlines()
                == ['0::/' + str(self.path.relative_to('/sys/fs/cgroup'))],
                'profile-worker-cgroup-mismatch')

    def observe_frozen(self):
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        events = (self.path / 'cgroup.events').read_text()
        require(re.findall(r'^frozen ([01])$', events, re.M) == ['1'] and
                re.findall(r'^populated ([01])$', events, re.M) == ['1'], 'profile-work-not-frozen')
        self.observe_identity()
        return events

    def observe_empty(self):
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        events = (self.path / 'cgroup.events').read_text()
        require(re.findall(r'^populated ([01])$', events, re.M) == ['0'] and
                not (self.path / 'cgroup.procs').read_text().split(), 'profile-worker-not-empty')
        return events

    def abort(self, *, deadline_ns):
        """Kill through retained kernel FD; ambiguity remains unconfirmed cleanup."""
        if self.kill_fd is None:
            return False
        try:
            os.write(self.kill_fd, b'1')
            while True:
                try:
                    self.observe_empty()
                    self.close_abort()
                    return True
                except (OSError, ValueError):
                    pass
                if time.monotonic_ns() >= deadline_ns:
                    return False
                time.sleep(.001)
        except (OSError, ValueError):
            return False

    def close_abort(self):
        if self.kill_fd is not None:
            os.close(self.kill_fd)
            self.kill_fd = None

    def freeze(self, *, deadline_ns):
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        (self.path / 'cgroup.freeze').write_text('1')
        while time.monotonic_ns() < deadline_ns:
            events = (self.path / 'cgroup.events').read_text()
            if re.findall(r'^frozen ([01])$', events, re.M) == ['1']:
                return self.observe_frozen()
            time.sleep(.001)
        require(False, 'profile-freeze-deadline')

    def resume(self):
        self.observe_frozen()
        (self.path / 'cgroup.freeze').write_text('0')


class OperatorSession:
    """Private supervisor protocol: ledger/reserves live OUTSIDE the worker.

    Its owner must attach the private launch IPC bridge and verify manager/mount/image
    readback. This object never trusts a worker reset of PhaseLedger. It does not
    issue grants, start workers, install units or accept source permissions.
    """
    def __init__(self, profile, *, origin_ns, worker_pid):
        self.timeline = AdmissionTimeline(profile, origin_ns=origin_ns)
        self.ledger = PhaseLedger(bounds={p.phase:p.requests for p in profile.limits[:4]},
                                 total=sum(p.requests for p in profile.limits),
                                 max_active=1 if profile.mode == 'serial' else 2)
        self.work = FrozenWork(profile, worker_pid=worker_pid)
        self.quota = WorkQuota(profile)
        self.watchdog = ExternalWatchdog(profile, self.timeline, self.work)
        self.failed = False
        self.cleanup_confirmed = False

    def _abort(self):
        self.failed = self.timeline.failed = True
        try:
            self.watchdog.revoke()
        finally:
            self.cleanup_confirmed = self.work.abort(
                deadline_ns=min(time.monotonic_ns()+10**9, self.timeline.deadline_ns))

    def attach_work(self):
        """After operator manager/image readback, attach a gated original worker."""
        require(self.timeline.index == -1 and not self.failed, 'profile-already-started')
        try:
            self.timeline.begin('prepare', now_ns=time.monotonic_ns())
            self.work.arm_abort()
            self.work.freeze(deadline_ns=self.timeline.phase_deadline_ns)
            self.ledger.enter('prepare')
            self.watchdog.start()
            self.work.resume()
        except BaseException:
            self._abort()
            raise

    def transition(self, phase):
        """Pause original worker, retain exact paths/grant, move one phase only."""
        require(not self.failed and phase in ('grant', 'dispatch'), 'profile-transition-state')
        try:
            require(self.timeline.active and
                    phase == PHASES[self.timeline.index+1], 'profile-phase-order')
            events = self.work.freeze(deadline_ns=self.timeline.phase_deadline_ns)
            require(self.ledger.receipt()['outstandingReservations'] == 0,
                    'profile-launches-outstanding')
            self.timeline.finish(now_ns=time.monotonic_ns(), cgroup_events=events, succeeded=True)
            self.timeline.begin(phase, now_ns=time.monotonic_ns())
            self.watchdog.arm()
            self.quota.advance(phase, frozen_work=self.work)
            self.ledger.enter(phase)
            self.work.resume()
        except BaseException:
            self._abort()
            raise

    def attach_final_worker(self, phase, *, worker_pid):
        """Stop/confirm prior cgroup, retain origin, attach separate gated worker.

        This does not launch it. Manager/image/read-only mount readback and the
        operator's actual launch IPC remain mandatory before releasing the gate.
        """
        require(not self.failed and phase in ('verify', 'terminal'), 'profile-final-worker-state')
        try:
            require(self.timeline.active and phase == STEPS[self.timeline.index+1], 'profile-phase-order')
            require(self.ledger.receipt()['outstandingReservations'] == 0, 'profile-launches-outstanding')
            events = self.work.observe_empty()
            self.work.close_abort()
            self.timeline.finish(now_ns=time.monotonic_ns(), cgroup_events=events, succeeded=True)
            self.watchdog.revoke()
            self.timeline.begin(phase, now_ns=time.monotonic_ns())
            if phase == 'verify':
                self.ledger.enter('verify')
            self.work = FrozenWork(self.timeline.profile, worker_pid=worker_pid, unit_phase=phase)
            self.work.arm_abort()
            self.work.freeze(deadline_ns=self.timeline.phase_deadline_ns)
            self.watchdog = ExternalWatchdog(self.timeline.profile, self.timeline, self.work)
            self.watchdog.start()
            self.work.resume()
        except BaseException:
            self._abort()
            raise

    def finish(self):
        require(not self.failed and self.timeline.index == 4 and self.timeline.active,
                'profile-terminal-required')
        try:
            events = self.work.observe_empty()
            self.work.close_abort()
            self.timeline.finish(now_ns=time.monotonic_ns(), cgroup_events=events, succeeded=True)
        except BaseException:
            self._abort()
            raise
        finally:
            self.watchdog.revoke()


def _watchdog_loop(read_fd, kill_fd, deadline_ns, *, original_deadline,
                   worker_pidfd=None, clock=time.monotonic_ns):
    """Separate operator process: no heartbeat extension beyond original deadline.

    Broken IPC, malformed/reversed arm, expiry, or any exception kills the entire
    cgroup through the already-open kernel descriptor. Worker never inherits it.
    """
    try:
        require(0 < deadline_ns <= original_deadline, 'watchdog-original-deadline')
        while clock() < deadline_ns:
            ready, _, _ = select.select([read_fd] + ([] if worker_pidfd is None else [worker_pidfd]),
                                        [], [], min(.1, (deadline_ns-clock()) / 10**9))
            if not ready:
                continue
            if clock() >= deadline_ns:
                break
            if worker_pidfd in ready:
                break
            raw = os.read(read_fd, 8)
            if len(raw) != 8:
                break
            next_deadline, = struct.unpack('!Q', raw)
            if not clock() < next_deadline <= original_deadline:
                break
            deadline_ns = next_deadline
    finally:
        os.write(kill_fd, b'1')


def _watchdog_child(read_fd, write_fd, kill_fd, pidfd, phase_deadline, deadline):
    """Even initialization failure revokes work before this process exits."""
    try:
        os.close(write_fd)
        for name in os.listdir('/proc/self/fd'):
            fd = int(name)
            if fd > 2 and fd not in (read_fd, kill_fd, pidfd):
                try:
                    os.close(fd)
                except OSError:
                    pass
        _watchdog_loop(read_fd, kill_fd, phase_deadline,
                       original_deadline=deadline, worker_pidfd=pidfd)
    finally:
        try:
            os.write(kill_fd, b'1')
        finally:
            os._exit(0)


class ExternalWatchdog:
    """Explicit native operator API, not invoked by compilation or any CLI.

    A separate process lives outside the work cgroup. Manager-level whole-flow
    BindsTo/runtime limits remain a second bound. Native qualification must prove
    namespace, cgroup identity and IPC isolation before any launch lease is issued.
    """
    def __init__(self, profile, timeline, work):
        require(type(profile) is LinuxAdmissionProfile and type(timeline) is AdmissionTimeline
                and timeline.profile.identity == profile.identity, 'watchdog-profile-binding')
        self.profile, self.timeline = profile, timeline
        require(type(work) is FrozenWork and work.profile.identity == profile.identity,
                'watchdog-worker-binding')
        self.work = work
        self.pid = self.write_fd = None

    def start(self):
        require(self.pid is None and self.timeline.active, 'watchdog-start-state')
        require(sys.platform == 'linux' and os.geteuid() == 0, 'linux-root-operator-required')
        require(threading.active_count() == 1, 'watchdog-single-thread-operator-required')
        stem = 'fc1' + self.profile.identity
        require(stem not in Path('/proc/self/cgroup').read_text(), 'watchdog-must-be-external')
        self.work.observe_frozen()
        path = str(self.work.path)
        require(Path('/sys/fs/cgroup/cgroup.controllers').is_file(), 'cgroup-v2-required')
        directory = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            kill_fd = os.open('cgroup.kill', os.O_WRONLY | os.O_NOFOLLOW, dir_fd=directory)
        finally:
            os.close(directory)
        pidfd = read_fd = write_fd = None
        try:
            pidfd = os.pidfd_open(self.work.worker_pid, 0)
            self.work.observe_frozen()
            require(select.select([pidfd], [], [], 0)[0] == [], 'watchdog-worker-exited')
            read_fd, write_fd = os.pipe2(os.O_CLOEXEC)
            pid = os.fork()
        except BaseException:
            os.write(kill_fd, b'1')
            for fd in (kill_fd, pidfd, read_fd, write_fd):
                if fd is not None:
                    os.close(fd)
            raise
        if pid == 0:
            _watchdog_child(read_fd, write_fd, kill_fd, pidfd,
                            self.timeline.phase_deadline_ns, self.timeline.deadline_ns)
        os.close(kill_fd); os.close(read_fd); os.close(pidfd)
        self.pid, self.write_fd = pid, write_fd

    def arm(self):
        require(self.pid is not None and self.timeline.active and not self.timeline.failed,
                'watchdog-arm-state')
        require(os.waitpid(self.pid, os.WNOHANG) == (0, 0), 'watchdog-not-alive')
        require(time.monotonic_ns() < self.timeline.phase_deadline_ns <= self.timeline.deadline_ns,
                'watchdog-original-deadline')
        require(os.write(self.write_fd, struct.pack('!Q', self.timeline.phase_deadline_ns)) == 8,
                'watchdog-arm-failed')

    def revoke(self):
        """EOF revokes work; operator must independently confirm empty afterward."""
        if self.write_fd is not None:
            os.close(self.write_fd)
            self.write_fd = None


class AdmissionTimeline:
    """External supervisor state; no native effects and no authority from reports.

    The operator must use kernel cgroup.events readback after service termination.
    It must never pass producer-owned bytes as this observation. Uncertain closure
    stops progression; a failed phase is not retried. The original origin survives
    creation of the independent verification worker.
    """
    def __init__(self, profile, *, origin_ns):
        require(type(profile) is LinuxAdmissionProfile, 'operator-profile-required')
        self.profile = profile
        self.origin_ns = integer(origin_ns, 0)
        self.deadline_ns = origin_ns + sum(p.wall_seconds for p in profile.limits) * 10**9
        self.index = -1
        self.active = False
        self.failed = False
        self.phase_deadline_ns = None
        self.last_ns = self.origin_ns

    def begin(self, phase, *, now_ns):
        integer(now_ns, self.last_ns)
        require(not self.active and not self.failed, 'profile-stopped-or-active')
        require(self.index + 1 < len(STEPS) and phase == STEPS[self.index + 1], 'profile-phase-order')
        index = self.index + 1
        future = sum(p.wall_seconds for p in self.profile.limits[index + 1:]) * 10**9
        limit = self.profile.limits[index]
        # Startup/IPC consumes this phase's own allocation; never extend the
        # original clock or borrow from future reserves. Keep 3s for start/kill.
        available = self.deadline_ns - future - now_ns
        if available <= 3 * 10**9:
            self.failed = True
            require(False, 'profile-reserves-exhausted')
        self.index, self.active = index, True
        self.last_ns = now_ns
        self.phase_deadline_ns = min(now_ns + limit.wall_seconds * 10**9, self.deadline_ns - future)
        return self.phase_deadline_ns

    def finish(self, *, now_ns, cgroup_events, succeeded):
        require(self.active, 'profile-no-active-phase')
        integer(now_ns, self.last_ns)
        require(type(succeeded) is bool, 'profile-result-required')
        # Work phases hand over while kernel-frozen; dispatch must terminate the
        # original worker before verification. No copying the grant/run store.
        populated = (re.findall(r'^populated ([01])$', cgroup_events, re.M)
                     if type(cgroup_events) is str else [])
        frozen = (re.findall(r'^frozen ([01])$', cgroup_events, re.M)
                  if type(cgroup_events) is str else [])
        closed = (populated == ['1'] and frozen == ['1'] if self.index < 2
                  else populated == ['0'])
        self.active = False
        self.last_ns = now_ns
        if not closed or not succeeded or now_ns > self.phase_deadline_ns:
            self.failed = True
            require(False, 'profile-closure-unverified')

    def receipt(self):
        return json.loads(json.dumps({'profileIdentity': self.profile.identity,
            'originNs': self.origin_ns, 'wholeFlowDeadlineNs': self.deadline_ns,
            'phaseDeadlineNs': self.phase_deadline_ns, 'phaseIndex': self.index,
            'active': self.active, 'failed': self.failed,
            'executionAuthorization': False, 'actualProfileAdmitted': False}))
