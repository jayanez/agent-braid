# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls of profile compilation; no systemd or native launch."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
import struct
from types import SimpleNamespace

from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_linux_profile import (
    AdmissionTimeline, LinuxAdmissionProfile, PhaseLimit, STEPS, proposed_limits,
    WorkQuota, FrozenWork, OperatorSession, ExternalWatchdog, _watchdog_loop, _watchdog_child,
)


class LinuxProfileTests(unittest.TestCase):
    def profile(self, **changes):
        values = dict(mode='serial', image_sha256='a'*64, root_hash='b'*64,
                      source_digest='c'*64, manager_sha256='d'*64, uid=61000,
                      limits=tuple(PhaseLimit(p, 0 if p == 'terminal' else 1,
                                              10, 4096, 8) for p in STEPS))
        values.update(changes)
        return LinuxAdmissionProfile(**values)

    def test_identity_immutable_and_bound_to_each_operator_choice(self):
        p = self.profile()
        with self.assertRaises(FrozenInstanceError):
            p.mode = 'parallel'
        manifest = p.manifest()
        manifest['phases'][0]['storage_bytes'] = 999
        self.assertEqual(p.limits[0].storage_bytes, 4096)
        for name, value in [('mode', 'parallel'), ('root_hash', 'e'*64),
                            ('image_sha256', 'e'*64), ('source_digest', 'e'*64),
                            ('manager_sha256', 'e'*64), ('uid', 61001)]:
            self.assertNotEqual(p.identity, self.profile(**{name:value}).identity)
        q = replace(p, limits=(replace(p.limits[0], storage_bytes=8192), *p.limits[1:]))
        self.assertNotEqual(p.identity, q.identity)
        with patch('agent_braid.forecast_linux_profile.Path.read_bytes', return_value=b'drift'):
            self.assertEqual(p.identity, p.identity)
            with self.assertRaisesRegex(ForecastError, 'compiler-drift'):
                p.units(remaining_seconds=50)

    def test_missing_pins_injection_mutable_limits_and_large_storage_refuse(self):
        for name, value in [('root_hash', ''), ('image_sha256', 'tag:latest'),
                            ('manager_sha256', 'a'*64+'\nExecStart=/bin/sh'),
                            ('uid', 0), ('limits', list(self.profile().limits))]:
            with self.subTest(name=name), self.assertRaises(ForecastError):
                self.profile(**{name:value})
        with self.assertRaisesRegex(ForecastError, 'retained-storage'):
            self.profile(limits=tuple(PhaseLimit(p, 0 if p == 'terminal' else 1, 10, 1024**3, 8)
                                      for p in STEPS))

    def test_units_preserve_manager_containment_verity_and_no_host_export(self):
        p = self.profile()
        units = p.units(remaining_seconds=50)
        workers = [s for n,s in units.items() if n.endswith('.service') and 'RootImage=' in s]
        self.assertEqual(len(workers), 3)
        for worker in workers:
            for setting in ('RootHash='+'b'*64, 'RootImageOptions=root:ro',
                            'ProtectControlGroups=yes', 'NoNewPrivileges=yes',
                            'Delegate=no', 'RestrictNamespaces=yes', 'PrivateNetwork=yes',
                            'KillMode=control-group', 'SendSIGKILL=yes', 'Restart=no',
                            'TimeoutStartSec=2', 'TimeoutStopSec=1',
                            'StandardOutput=null', 'StandardError=null'):
                self.assertIn(setting+'\n', worker)
            self.assertNotIn('/artifacts', worker)
            self.assertNotIn('EnvironmentFile=', worker)
            self.assertNotIn('[Install]', worker)
        slices = [s for n,s in units.items() if n.endswith('.slice')]
        self.assertEqual(len(slices), 1)
        for setting in ('CPUQuota=100%', 'MemoryMax=2147483648', 'MemorySwapMax=0', 'TasksMax=64'):
            self.assertIn(setting+'\n', slices[0])

    def test_phase_storage_separate_bounded_and_prior_outputs_readonly(self):
        p = self.profile()
        units = p.units(remaining_seconds=50)
        mounts = [s for n,s in units.items() if n.endswith('.mount')]
        self.assertEqual(len(mounts), 3)
        for mount in mounts:
            self.assertIn('nosuid,nodev,noexec,noswap,size=4096,nr_inodes=8', mount)
        prefix = 'fc1'+p.identity
        prep = units[prefix+'-prepare.service']
        verify = units[prefix+'-verify.service']
        self.assertNotIn(':/prior/', prep)
        self.assertIn(':/work\n', verify)
        self.assertIn(':/scratch\n', verify)
        self.assertIn('Environment=HOME=/scratch/home TMPDIR=/scratch/tmp\n', verify)
        self.assertNotIn(':/prior/terminal', verify)
        self.assertEqual(verify.count('BindPaths='), 1)
        self.assertEqual(verify.count('BindReadOnlyPaths='), 1)

    def test_deadline_never_resets_and_future_reserves_block_late_start(self):
        timeline = AdmissionTimeline(self.profile(), origin_ns=10)
        deadline = timeline.deadline_ns
        timeline.begin('prepare', now_ns=10)
        timeline.finish(now_ns=10**9, cgroup_events='populated 1\nfrozen 1\n', succeeded=True)
        timeline.begin('grant', now_ns=10**9)
        self.assertEqual(timeline.deadline_ns, deadline)
        timeline.finish(now_ns=2*10**9, cgroup_events='populated 1\nfrozen 1\n', succeeded=True)
        with self.assertRaisesRegex(ForecastError, 'reserves-exhausted'):
            timeline.begin('dispatch', now_ns=25*10**9)
        self.assertTrue(timeline.failed)

    def test_uncertain_kernel_empty_or_expired_phase_stops_without_retry(self):
        for events, now, succeeded in [('populated 1\n',1,True),
                                      ('ActiveState=inactive',1,True),
                                      ('populated 0\npopulated 0\n',1,True),
                                      ('populated 0\n',11*10**9,True),
                                      ('populated 0\n',1,False)]:
            timeline = AdmissionTimeline(self.profile(), origin_ns=0)
            timeline.begin('prepare', now_ns=0)
            with self.assertRaisesRegex(ForecastError, 'closure-unverified'):
                timeline.finish(now_ns=now, cgroup_events=events, succeeded=succeeded)
            with self.assertRaisesRegex(ForecastError, 'stopped-or-active'):
                timeline.begin('grant', now_ns=now)

    def test_no_verify_without_previous_work_closure(self):
        timeline = AdmissionTimeline(self.profile(), origin_ns=0)
        with self.assertRaisesRegex(ForecastError, 'phase-order'):
            timeline.begin('verify', now_ns=0)
        for index, phase in enumerate(STEPS):
            timeline.begin(phase, now_ns=index*10**9)
            timeline.finish(now_ns=(index+1)*10**9,
                            cgroup_events='populated 1\nfrozen 1\n' if index < 2 else 'populated 0\n',
                            succeeded=True)
        receipt = timeline.receipt()
        self.assertFalse(receipt['actualProfileAdmitted'])
        self.assertFalse(receipt['executionAuthorization'])

    def test_selected_input_proposals_are_explicit_caps_not_cost_evidence(self):
        root = Path(__file__).resolve().parents[1]
        for mode, requests, wall in [('serial',3843,1140), ('parallel',6662,1890)]:
            proposal = proposed_limits(root, mode=mode)
            self.assertEqual(proposal['gitRequests'], requests)
            self.assertEqual(proposal['wallSeconds'], wall)
            self.assertEqual(proposal['phases'][-1]['storageBytes'], 8*1024**2)
            self.assertIsNone(proposal['minimumCost'])
            self.assertFalse(proposal['completionGuaranteed'])
            self.assertFalse(proposal['executionAuthorization'])

    def test_root_quota_growth_checked_before_and_after_remount(self):
        quota = WorkQuota(self.profile())
        libc = MagicMock()
        libc.mount.return_value = 0
        def mountinfo():
            n = 2 if libc.mount.called else 1
            return ('20 19 0:20 / '+quota.path+' rw,nosuid,nodev,noexec - tmpfs tmpfs '
                    'rw,noswap,mode=700,uid=61000,gid=61000,size='+str(4*n)+'k,nr_inodes='+str(8*n)+'\n')
        with patch('agent_braid.forecast_linux_profile.sys.platform','linux'), \
             patch('agent_braid.forecast_linux_profile.os.geteuid',return_value=0), \
             patch('agent_braid.forecast_linux_profile.Path.resolve',return_value=Path(quota.path)), \
             patch('agent_braid.forecast_linux_profile.Path.read_text',side_effect=mountinfo), \
             patch('agent_braid.forecast_linux_profile.ctypes.CDLL',return_value=libc), \
             patch.object(FrozenWork,'observe_frozen'), \
             patch('agent_braid.forecast_linux_profile.os.statvfs',return_value=SimpleNamespace(
                 f_blocks=1,f_bfree=0,f_frsize=4096,f_files=8,f_ffree=0)):
            quota.advance('grant',frozen_work=FrozenWork(quota.profile,worker_pid=100))
        self.assertEqual(quota.bytes, 8192)
        self.assertEqual(quota.index, 1)
        self.assertIn(b'size=8192', libc.mount.call_args.args[-1])
        self.assertNotIn(b'verify', libc.mount.call_args.args[-1])

    def test_quota_readback_uncertain_blocks_future_growth(self):
        quota = WorkQuota(self.profile())
        with patch('agent_braid.forecast_linux_profile.sys.platform','linux'), \
             patch('agent_braid.forecast_linux_profile.os.geteuid',return_value=0), \
             patch('agent_braid.forecast_linux_profile.Path.resolve',return_value=Path(quota.path)), \
             patch('agent_braid.forecast_linux_profile.Path.read_text',return_value=''), \
             patch('agent_braid.forecast_linux_profile.ctypes.CDLL') as libc, \
             patch.object(FrozenWork,'observe_frozen'):
            with self.assertRaisesRegex(ForecastError, 'mount-required'):
                quota.advance('grant',frozen_work=FrozenWork(quota.profile,worker_pid=100))
            libc.assert_not_called()
        with self.assertRaisesRegex(ForecastError, 'quota-stopped'):
            quota.advance('grant',frozen_work=FrozenWork(quota.profile,worker_pid=100))

    def test_external_watchdog_revokes_on_ipc_failure_and_deadline_extension(self):
        for messages in [[b''], [b'invalid'], [struct.pack('!Q',101)],
                         [struct.pack('!Q',30), b'']]:
            with self.subTest(messages=messages), \
                 patch('agent_braid.forecast_linux_profile.select.select',return_value=([7],[],[])), \
                 patch('agent_braid.forecast_linux_profile.os.read',side_effect=messages), \
                 patch('agent_braid.forecast_linux_profile.os.write') as write:
                _watchdog_loop(7,8,10,original_deadline=100,clock=lambda:0)
                write.assert_called_once_with(8,b'1')

    def test_watchdog_expiry_kills_without_heartbeat(self):
        with patch('agent_braid.forecast_linux_profile.os.write') as write:
            _watchdog_loop(7,8,10,original_deadline=100,clock=lambda:11)
        write.assert_called_once_with(8,b'1')

    def test_late_arm_cannot_rescue_expired_phase(self):
        times = iter([0,0,11])
        with patch('agent_braid.forecast_linux_profile.select.select',return_value=([7],[],[])), \
             patch('agent_braid.forecast_linux_profile.os.read') as read, \
             patch('agent_braid.forecast_linux_profile.os.write') as write:
            _watchdog_loop(7,8,10,original_deadline=100,clock=lambda:next(times))
        read.assert_not_called()
        write.assert_called_once_with(8,b'1')

    def test_phase_handoff_retains_worker_and_external_ledger(self):
        session = OperatorSession(self.profile(), origin_ns=0, worker_pid=100)
        session.timeline.begin('prepare',now_ns=0)
        session.ledger.enter('prepare')
        ledger = session.ledger
        order=[]
        with patch.object(session.work,'freeze',side_effect=lambda **kw:order.append('freeze') or
                          'populated 1\nfrozen 1\n'), \
             patch.object(session.quota,'advance',side_effect=lambda *a,**kw:order.append('quota')), \
             patch.object(session.watchdog,'arm',side_effect=lambda:order.append('arm')), \
             patch.object(session.work,'resume',side_effect=lambda:order.append('resume')), \
             patch('agent_braid.forecast_linux_profile.time.monotonic_ns',return_value=1):
            session.transition('grant')
        self.assertEqual(order,['freeze','arm','quota','resume'])
        self.assertIs(session.ledger,ledger)
        self.assertEqual(session.work.worker_pid,100)
        self.assertEqual(session.timeline.deadline_ns,50*10**9)

    def test_handoff_failure_never_resumes_and_revokes_watchdog(self):
        session=OperatorSession(self.profile(),origin_ns=0,worker_pid=100)
        session.timeline.begin('prepare',now_ns=0)
        session.ledger.enter('prepare')
        session.ledger.reserve()
        with patch.object(session.work,'freeze',return_value='populated 1\nfrozen 1\n'), \
             patch.object(session.work,'resume') as resume, \
             patch.object(session.quota,'advance') as advance, \
             patch.object(session.watchdog,'revoke') as revoke:
            with self.assertRaisesRegex(ForecastError,'launches-outstanding'):
                session.transition('grant')
        resume.assert_not_called();advance.assert_not_called();revoke.assert_called_once()
        self.assertTrue(session.failed)

    def test_kernel_handoff_rejects_children_even_when_frozen(self):
        frozen=FrozenWork(self.profile(),worker_pid=100)
        with patch('agent_braid.forecast_linux_profile.sys.platform','linux'), \
             patch('agent_braid.forecast_linux_profile.os.geteuid',return_value=0), \
             patch('agent_braid.forecast_linux_profile.Path.read_text',
                   side_effect=['populated 1\nfrozen 1\n','100\n101\n']):
            with self.assertRaisesRegex(ForecastError,'children-remain'):
                frozen.observe_frozen()

    def test_initial_watchdog_denies_unbound_worker_before_open_or_fork(self):
        profile=self.profile()
        timeline=AdmissionTimeline(profile,origin_ns=0)
        timeline.begin('prepare',now_ns=0)
        frozen=FrozenWork(profile,worker_pid=100)
        watchdog=ExternalWatchdog(profile,timeline,frozen)
        with patch('agent_braid.forecast_linux_profile.sys.platform','linux'), \
             patch('agent_braid.forecast_linux_profile.os.geteuid',return_value=0), \
             patch('agent_braid.forecast_linux_profile.threading.active_count',return_value=1), \
             patch('agent_braid.forecast_linux_profile.Path.read_text',return_value='0::/operator'), \
             patch.object(frozen,'observe_frozen',side_effect=ForecastError('wrong-worker')), \
             patch('agent_braid.forecast_linux_profile.os.open') as opened, \
             patch('agent_braid.forecast_linux_profile.os.fork',create=True) as fork:
            with self.assertRaisesRegex(ForecastError,'wrong-worker'):
                watchdog.start()
        opened.assert_not_called();fork.assert_not_called()

    def test_final_workers_keep_origin_and_confirm_prior_empty(self):
        session=OperatorSession(self.profile(),origin_ns=0,worker_pid=100)
        for index, phase in enumerate(STEPS[:3]):
            session.timeline.begin(phase,now_ns=index*10**9)
            session.ledger.enter(phase)
            if index < 2:
                session.timeline.finish(now_ns=index*10**9+1,
                    cgroup_events='populated 1\nfrozen 1\n',succeeded=True)
        original=session.timeline.deadline_ns
        with patch.object(FrozenWork,'observe_empty',return_value='populated 0\n'), \
             patch.object(FrozenWork,'freeze'),patch.object(FrozenWork,'resume'), \
             patch.object(FrozenWork,'arm_abort'), \
             patch.object(ExternalWatchdog,'start'),patch.object(ExternalWatchdog,'revoke'), \
             patch('agent_braid.forecast_linux_profile.time.monotonic_ns',return_value=3*10**9):
            session.attach_final_worker('verify',worker_pid=101)
            self.assertEqual(session.work.worker_pid,101)
            session.attach_final_worker('terminal',worker_pid=102)
            self.assertEqual(session.work.worker_pid,102)
            session.finish()
        self.assertEqual(session.timeline.deadline_ns,original)
        self.assertFalse(session.timeline.active)
        self.assertFalse(session.failed)

    def test_watchdog_initialization_failure_revokes_before_exit(self):
        with patch('agent_braid.forecast_linux_profile.os.close'), \
             patch('agent_braid.forecast_linux_profile.os.listdir',side_effect=OSError('fd read failed')), \
             patch('agent_braid.forecast_linux_profile.os.write') as write, \
             patch('agent_braid.forecast_linux_profile.os._exit',side_effect=SystemExit):
            with self.assertRaises(SystemExit):
                _watchdog_child(7,8,9,10,100,200)
        write.assert_called_once_with(9,b'1')

    def test_initial_freeze_failure_uses_preopened_abort_capability(self):
        session=OperatorSession(self.profile(),origin_ns=0,worker_pid=100)
        order=[]
        with patch.object(session.work,'arm_abort',side_effect=lambda:order.append('open-kill')), \
             patch.object(session.work,'freeze',side_effect=ForecastError('freeze-expired')), \
             patch.object(session.work,'abort',return_value=True) as abort, \
             patch.object(session.watchdog,'start') as start, \
             patch('agent_braid.forecast_linux_profile.time.monotonic_ns',return_value=0):
            with self.assertRaisesRegex(ForecastError,'freeze-expired'):
                session.attach_work()
        self.assertEqual(order,['open-kill'])
        abort.assert_called_once();start.assert_not_called()
        self.assertTrue(session.cleanup_confirmed)
        self.assertTrue(session.failed)

    def test_final_freeze_failure_aborts_new_group_before_watchdog_start(self):
        session=OperatorSession(self.profile(),origin_ns=0,worker_pid=100)
        for index,phase in enumerate(STEPS[:3]):
            session.timeline.begin(phase,now_ns=index)
            session.ledger.enter(phase)
            if index < 2:
                session.timeline.finish(now_ns=index,cgroup_events='populated 1\nfrozen 1\n',succeeded=True)
        with patch.object(FrozenWork,'observe_empty',return_value='populated 0\n'), \
             patch.object(FrozenWork,'arm_abort') as armed, \
             patch.object(FrozenWork,'freeze',side_effect=ForecastError('freeze-expired')), \
             patch.object(FrozenWork,'abort',return_value=False) as abort, \
             patch.object(ExternalWatchdog,'start') as start, \
             patch('agent_braid.forecast_linux_profile.time.monotonic_ns',return_value=3):
            with self.assertRaisesRegex(ForecastError,'freeze-expired'):
                session.attach_final_worker('verify',worker_pid=101)
        armed.assert_called_once();abort.assert_called_once();start.assert_not_called()
        self.assertEqual(session.work.worker_pid,101)
        self.assertTrue(session.failed)
        self.assertFalse(session.cleanup_confirmed)


if __name__ == '__main__':
    unittest.main()
