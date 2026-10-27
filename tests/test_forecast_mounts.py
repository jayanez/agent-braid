# SPDX-License-Identifier: AGPL-3.0-only
"""Mocked mount syscalls only. Never mounts, starts units or reads host state."""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_mounts import RootMountOwner
from agent_braid.forecast_supervisor import ExecutionScope


class MountOwnerTests(unittest.TestCase):
    def owner(self):
        profile=SimpleNamespace(identity='a'*64,uid=61000,
            manifest=lambda:{'execAdmissionEnforced':False,'bootstrapSupervisionAccepted':False},
            limits=[SimpleNamespace(wall_seconds=10,storage_bytes=4096,inodes=8)]*5)
        view=MagicMock();view.bytes_read=0
        return RootMountOwner(profile,100,view=view,clock=lambda:150)

    def test_pending_profile_refuses_before_namespace_read_or_libc(self):
        owner=self.owner()
        with patch('agent_braid.forecast_mounts.os.stat') as stat, \
             patch('agent_braid.forecast_mounts.ctypes.CDLL') as load:
            with self.assertRaisesRegex(ForecastError,'readiness-pending'):owner.open()
        stat.assert_not_called();load.assert_not_called();owner.view.guard.assert_not_called()

    def test_wrong_namespace_refuses_before_any_mount(self):
        owner=self.owner()
        with patch('agent_braid.forecast_mounts.bootstrap_ready'), \
             patch('agent_braid.forecast_mounts.os.stat',side_effect=[
                 SimpleNamespace(st_dev=1,st_ino=2),SimpleNamespace(st_dev=1,st_ino=3)]), \
             patch.object(owner,'_libc') as load:
            with self.assertRaisesRegex(ForecastError,'wrong-namespace'):owner.open()
        load.assert_not_called()

    def test_create_is_write_ahead_bounded_and_cannot_retry(self):
        owner=self.owner();owner.fd=12;libc=MagicMock()
        def mount(*args):
            self.assertTrue(owner.records[0]['syscallAttempted'])
            self.assertEqual(args[3],14);self.assertIn(b'size=4096',args[-1]);return 0
        libc.mount.side_effect=mount
        with patch.object(owner,'_ready'),patch.object(owner,'_libc',return_value=libc), \
             patch.object(owner,'_observe',return_value=None), \
             patch.object(owner,'_verify',return_value={'mountId':42,'device':'0:1','bytes':4096,'inodes':8}), \
             patch('agent_braid.forecast_mounts.os.mkdir'):
            owner.create('prepare',deadline_ns=200)
            with self.assertRaises(ForecastError):owner.create('prepare',deadline_ns=200)
        self.assertTrue(owner.records[0]['succeeded']);libc.mount.assert_called_once()

    def test_failed_create_is_retained_and_refuses_next_phase(self):
        owner=self.owner();owner.fd=12;libc=MagicMock();libc.mount.return_value=-1
        with patch.object(owner,'_ready'),patch.object(owner,'_libc',return_value=libc), \
             patch.object(owner,'_observe',return_value=None),patch('agent_braid.forecast_mounts.os.mkdir'):
            with self.assertRaisesRegex(ForecastError,'create-failed'):owner.create('prepare',deadline_ns=200)
            with self.assertRaises(ForecastError):owner.create('verify',deadline_ns=200)
        self.assertTrue(owner.failed);self.assertEqual(len(owner.records),1)
        self.assertIn('prepare',owner.mounts)
        self.assertIsNone(owner.mounts['prepare'])

    def test_busy_cleanup_attempts_every_mount_once_and_never_detaches(self):
        owner=self.owner();owner.fd=12
        owner.mounts={p:{'bytes':4096,'inodes':8} for p in ('prepare','verify','terminal')}
        scope=object.__new__(ExecutionScope);scope.profile=owner.profile;scope.plan={}
        scope.verify_plan=MagicMock();scope.snapshot=MagicMock(return_value=[{'populated':False}]*2)
        libc=MagicMock();libc.umount2.side_effect=[-1,0,0]
        with patch.object(owner,'_ready'),patch.object(owner,'_libc',return_value=libc), \
             patch.object(owner,'_verify'),patch.object(owner,'_observe',return_value=None), \
             patch('agent_braid.forecast_mounts.os.close'):
            with self.assertRaisesRegex(ForecastError,'busy-or-failed'):owner.close_all(scope)
        self.assertEqual(libc.umount2.call_count,3)
        self.assertTrue(all(call.args[1]==0 for call in libc.umount2.call_args_list))
        self.assertTrue(owner.failed);self.assertTrue(owner.closed)
        self.assertFalse(owner.receipt()['nativeCoverageAccepted'])
