# SPDX-License-Identifier: AGPL-3.0-only
"""Mocked sd-bus ABI only; no compiler, ELF load or PID1 socket is used."""
import ctypes
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_manager import RootManager,manager_launch_inventory,require_closed_job_graph
from agent_braid.forecast_native import proc_stat


class ManagerTests(unittest.TestCase):
    def manager(self,ready=False):
        profile=SimpleNamespace(identity='a'*64,manager_sha256='b'*64,
            manifest=lambda:{'execAdmissionEnforced':ready,'bootstrapSupervisionAccepted':ready},
            limits=[SimpleNamespace(wall_seconds=10,requests=0)],
            units=lambda **kw:{'fixed.service':'[Unit]\nDefaultDependencies=no\n[Service]\nExecStart=/owned/fixed\n'})
        return RootManager(profile,bridge_path='/owned/bridge.so',bridge_sha256='c'*64,view=MagicMock(),clock=lambda:150)

    def test_pending_candidate_refuses_before_read_dlopen_or_connect(self):
        manager=self.manager()
        with patch('agent_braid.forecast_manager.ctypes.CDLL') as load:
            with self.assertRaisesRegex(ForecastError,'readiness-pending'):manager.open()
        load.assert_not_called();manager.view.guard.assert_not_called();manager.view.read.assert_not_called()

    def test_failed_start_is_consumed_and_cannot_retry(self):
        manager=self.manager(True);unit='fc1'+'a'*64+'-supervisor.service'
        row={'role':'supervisor','admitted':True,'state':'dispatch-indeterminate'}
        with patch.object(manager,'_call',side_effect=OSError('ambiguous')) as call:
            with self.assertRaises(OSError):manager.request_start(unit,row,200)
            with self.assertRaisesRegex(ForecastError,'prior-reservation'):manager.request_start(unit,row,200)
            call.assert_called_once()

    def test_arbitrary_unit_or_unadmitted_start_never_reaches_bus(self):
        manager=self.manager(True)
        for unit,row in [('sshd.service',{'role':'operator','admitted':True,'state':'dispatch-indeterminate'}),
                         ('fc1'+'a'*64+'-operator.service',{'role':'operator','admitted':False})]:
            with patch.object(manager,'_call') as call:
                with self.assertRaises(ForecastError):manager.request_start(unit,row,200)
                call.assert_not_called()

    def test_pid1_exception_is_explicit_and_not_available_for_another_child(self):
        fields=['0']*50;fields[0]='S';fields[19]='123';raw='1 (systemd) '+' '.join(fields)
        with self.assertRaises(ForecastError):proc_stat(raw)
        self.assertEqual(proc_stat(raw,allow_init=True)['ppid'],0)
        with self.assertRaises(ForecastError):proc_stat(raw.replace('1 (','2 ('),allow_init=True)

    def client(self):
        manager=self.manager(True);manager.context=ctypes.c_void_p(1);manager.library=MagicMock()
        manager.library.fc1_manager_property.return_value=0
        def step(context,out):out._obj.kind=2;out._obj.number=42;return 1
        manager.library.fc1_manager_step.side_effect=step
        manager._manager_identity=MagicMock();return manager

    def test_numeric_property_is_typed_and_late_reply_is_rejected(self):
        manager=self.client();self.assertEqual(manager.property('operator','MainPID',200),42)
        manager=self.client();times=iter([150,150,201]);manager.clock=lambda:next(times)
        with self.assertRaisesRegex(ForecastError,'late-reply'):manager.property('operator','MainPID',200)
        self.assertTrue(manager.failed)

    def test_unlisted_property_does_not_reach_native_abi(self):
        manager=self.client()
        with self.assertRaisesRegex(ForecastError,'property-denied'):
            manager.property('operator','Environment',200)
        manager.library.fc1_manager_property.assert_not_called()

    def real_profile(self):
        from agent_braid.forecast_linux_profile import LinuxAdmissionProfile,PhaseLimit,STEPS
        return LinuxAdmissionProfile(mode='serial',image_sha256='a'*64,root_hash='b'*64,
            source_digest='c'*64,manager_sha256='d'*64,operator_sha256='e'*64,
            operator_entry_sha256='f'*64,worker_sha256='1'*64,census_sha256='2'*64,
            recipe_sha256='3'*64,uid=61000,
            limits=tuple(PhaseLimit(p,0 if p=='terminal' else 1,10,4096,8) for p in STEPS))

    def test_current_profile_exposes_exact_terminal_reserve_shortfall(self):
        report=manager_launch_inventory(self.real_profile())
        self.assertEqual(len(report['services']),6);self.assertEqual(len(report['mounts']),3)
        self.assertEqual(report['terminalExecCap'],4)
        self.assertEqual(report['terminalKnownExecFloor'],10)
        self.assertEqual(report['mountUnmountExecCap'],198)
        self.assertIsNone(report['wholeFlowExecUpperBound'])
        with self.assertRaisesRegex(ForecastError,'job-graph-unclosed'):
            require_closed_job_graph(self.real_profile())

    def test_commented_duplicate_or_wrong_section_defaults_never_close_graph(self):
        for text in ('[Unit]\n# DefaultDependencies=no\n',
                     '[Unit]\nDefaultDependencies=no\nDefaultDependencies=yes\n',
                     '[Service]\nDefaultDependencies=no\n'):
            profile=self.manager(True).profile;profile.units=lambda **kw:{'fixed.service':text}
            with self.subTest(text=text),self.assertRaisesRegex(ForecastError,'job-graph-unclosed'):
                require_closed_job_graph(profile)

    def test_indented_extra_control_command_is_rejected(self):
        for command in ('  ExecStartPre=/owned/extra',' ExecStartPre = /owned/extra'):
            profile=self.manager(True).profile
            profile.units=lambda **kw:{'fixed.service':'[Unit]\nDefaultDependencies=no\n[Service]\n'+command+'\n'}
            with self.subTest(command=command),self.assertRaisesRegex(ForecastError,'additional-manager-control-commands'):
                require_closed_job_graph(profile)

    def test_unclosed_graph_refuses_before_reads_loading_or_start_rpc(self):
        manager=self.manager(True);profile=self.real_profile()
        # Model a separately changed readiness state, leaving the actual graph.
        manager.profile.units=profile.units;manager.profile.limits=profile.limits
        with patch('agent_braid.forecast_manager.ctypes.CDLL') as load:
            with self.assertRaisesRegex(ForecastError,'job-graph-unclosed'):manager.open()
        load.assert_not_called();manager.view.guard.assert_not_called()
        with patch.object(manager,'_call') as call:
            with self.assertRaisesRegex(ForecastError,'job-graph-unclosed'):
                manager.request_start('sshd.service',{},200)
        call.assert_not_called()


if __name__=='__main__':unittest.main()
