# SPDX-License-Identifier: AGPL-3.0-only
"""Mocked cancellation only; no cgroup, process, syscall filter or native unit."""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_supervisor import ExecutionScope,watchdog_loop,READ_PARTITIONS


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        mocked=patch("agent_braid.forecast_supervisor.bootstrap_ready")
        mocked.start();self.addCleanup(mocked.stop)
    def profile(self):
        stem="fc1"+"a"*64
        return SimpleNamespace(identity="a"*64,manager_sha256="b"*64,operator_sha256="c"*64,
            operator_entry_sha256="d"*64,limits=[SimpleNamespace(wall_seconds=10)]*5,
            manifest=lambda:{"execAdmissionEnforced":False},
            units=lambda **kw:{stem+"-supervisor.service":"supervisor",stem+".service":"anchor",stem+"-operator.service":"operator"})

    def scope(self,view=None):
        return ExecutionScope(self.profile(),origin_ns=100,nonce="a"*64,view=MagicMock() if view is None else view)

    def plan(self):
        return {'nonce':'a'*64,'supervision':{'scope':'/test.slice','cancelAtNs':200,'closeByNs':300}}

    def test_pending_profile_blocks_before_native_read_or_open(self):
        profile=self.profile()
        view=MagicMock();scope=self.scope(view)
        with patch('agent_braid.forecast_supervisor.bootstrap_ready',side_effect=ForecastError('readiness-pending')), \
             patch('agent_braid.forecast_supervisor.os.open') as opened:
            with self.assertRaisesRegex(ForecastError,'readiness-pending'):scope.open()
            view.guard.assert_not_called();opened.assert_not_called()

    def test_changed_plan_cannot_extend_deadline_or_cancel_another_scope(self):
        from copy import deepcopy
        scope=self.scope()
        for field,value in [('closeByNs',999999999999),('scope','/another.slice')]:
            plan=deepcopy(scope.plan);plan['supervision'][field]=value
            with self.assertRaisesRegex(ForecastError,'plan-drift'):scope.verify_plan(plan)

    def test_root_read_partitions_do_not_expand_two_gib(self):
        self.assertEqual(sum(READ_PARTITIONS.values()),2*1024**3)

    def test_issuer_exit_revokes_without_calling_manager(self):
        plan=self.plan();scope=MagicMock();channel=MagicMock()
        with patch('agent_braid.forecast_supervisor.peer'), \
             patch('agent_braid.forecast_supervisor.select.select',return_value=([7],[],[])):
            result=watchdog_loop(plan,scope,channel,7,issuer_pid=42,clock=lambda:150)
        self.assertEqual(result['cause'],'issuer-exit')
        scope.revoke.assert_called_once_with(requested_ns=150,close_by_ns=300,clock=unittest.mock.ANY)

    def test_expiry_uses_original_deadline_without_extension(self):
        scope=MagicMock()
        with patch('agent_braid.forecast_supervisor.peer'):
            result=watchdog_loop(self.plan(),scope,MagicMock(),7,issuer_pid=42,clock=lambda:201)
        self.assertEqual(result['cause'],'expiry');self.assertEqual(scope.revoke.call_args.kwargs['close_by_ns'],300)

    def test_malformed_or_replayed_command_still_revokes(self):
        for request in ({},{'event':'extend','deadlineNs':999}):
            scope=MagicMock();channel=MagicMock()
            with patch('agent_braid.forecast_supervisor.peer'), \
                 patch('agent_braid.forecast_supervisor.select.select',return_value=([channel],[],[])), \
                 patch('agent_braid.forecast_supervisor.receive',return_value=request):
                result=watchdog_loop(self.plan(),scope,channel,7,issuer_pid=42,clock=lambda:150)
            self.assertEqual(result['cause'],'authority-or-ipc-failure');scope.revoke.assert_called_once()

    def test_failure_revokes_every_target_without_a_retry(self):
        profile=SimpleNamespace(identity='a'*64);view=MagicMock();scope=self.scope(view)
        scope.handles=[{'kill':21},{'kill':22}]
        with patch('agent_braid.forecast_supervisor.os.write',side_effect=[OSError('failed'),1]) as write:
            with self.assertRaises(OSError):scope.revoke(requested_ns=100,close_by_ns=200,clock=lambda:150)
            self.assertEqual(write.call_count,2)
            with self.assertRaisesRegex(ForecastError,'revoke-state'):scope.revoke(requested_ns=100,close_by_ns=200)
            self.assertEqual(write.call_count,2)

    def test_late_watchdog_still_kills_both_targets_before_refusing_closure(self):
        scope=self.scope()
        scope.handles=[{'kill':21},{'kill':22}]
        with patch('agent_braid.forecast_supervisor.os.write',return_value=1) as write:
            with self.assertRaisesRegex(ForecastError,'outside-budget'):
                scope.revoke(requested_ns=201,close_by_ns=200,clock=lambda:201)
        self.assertEqual(write.call_count,2)

    def test_old_empty_observation_cannot_confirm_revocation(self):
        profile=SimpleNamespace(identity='a'*64);scope=self.scope()
        scope.handles=[{'kill':21},{'kill':22}];scope.snapshot=MagicMock(return_value=[{'populated':False}]*2)
        times=iter([150,99,201,201])
        with patch('agent_braid.forecast_supervisor.os.write',return_value=1), \
             patch('agent_braid.forecast_supervisor.select.select',return_value=([],[],[])):
            with self.assertRaisesRegex(ForecastError,'outside-budget'):
                scope.revoke(requested_ns=100,close_by_ns=200,clock=lambda:next(times))


if __name__=='__main__':unittest.main()
