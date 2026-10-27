# SPDX-License-Identifier: AGPL-3.0-only
"""Mocked transport/authority controls; never install seccomp or fork a broker."""
import array
import socket
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from agent_braid.forecast_data import ForecastError
from agent_braid import forecast_launcher as launcher


class LauncherTests(unittest.TestCase):
    def profile(self, ready=False):
        return SimpleNamespace(identity='a'*64, uid=61000,
            manifest=lambda:{'execAdmissionEnforced':ready},
            limits=[SimpleNamespace(requests=1,wall_seconds=10)]*5)

    def test_unready_profile_blocks_before_any_native_side_effect(self):
        p=self.profile()
        with patch.object(launcher.socket,'socket') as sock, patch.object(launcher.os,'fork') as fork, \
             patch.object(launcher,'install_on_current_task') as install:
            for action in (lambda:launcher.handoff_current_task(p,'prepare'),
                           lambda:launcher.spawn_root_actor(p,100,None),
                           lambda:launcher.prepare_initial_worker(p,100,None)):
                with self.assertRaisesRegex(ForecastError,'readiness-pending'):action()
            sock.assert_not_called();fork.assert_not_called();install.assert_not_called()

    def test_malformed_ancillary_closes_all_received_fds(self):
        for flags,raw in ((socket.MSG_CTRUNC,b'{}'),(0,b'{"x":1,"x":2}')):
            sock=MagicMock();sock.recvmsg.return_value=(raw,
                [(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[21,22]).tobytes())],flags,None)
            with patch.object(launcher.os,'set_inheritable'),patch.object(launcher.os,'close') as close:
                with self.assertRaises(ForecastError):launcher.receive_frame(sock,with_fd=True)
            self.assertEqual([c.args[0] for c in close.call_args_list],[21,22])

    def test_duplicate_json_key_closes_single_delivered_fd(self):
        sock=MagicMock();sock.recvmsg.return_value=(b'{"x":1,"x":2}',
            [(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[21]).tobytes())],0,None)
        with patch.object(launcher.os,'set_inheritable'),patch.object(launcher.os,'close') as close:
            with self.assertRaises(ValueError):launcher.receive_frame(sock,with_fd=True)
        close.assert_called_once_with(21)

    def test_handoff_closes_original_before_release_and_acceptance(self):
        p=self.profile(True);sock=MagicMock();events=[]
        def sent(channel,value,fd=None):events.append(('fd' if fd else 'frame',value))
        def received(channel):
            if len(events)==1:return {'challenge':'b'*64,'profileIdentity':p.identity},None
            self.assertIn(('close',41),events)
            self.assertEqual(events[-1],('frame',{'released':'b'*64}))
            return {'accepted':True,'profileIdentity':p.identity},None
        with patch.object(launcher.sys,'platform','linux'),patch.object(launcher.socket,'socket',return_value=sock), \
             patch.object(launcher,'peer'),patch.object(launcher,'send_frame',side_effect=sent), \
             patch.object(launcher,'receive_frame',side_effect=received), \
             patch.object(launcher,'install_on_current_task',return_value=41), \
             patch.object(launcher.os,'close',side_effect=lambda fd:events.append(('close',fd))):
            launcher.handoff_current_task(p,'prepare')
        self.assertEqual(sum(e==('close',41) for e in events),1)
        sock.close.assert_called_once()

    def actor(self):
        verifier=MagicMock();verifier.quiescent.return_value=True
        return launcher.RootBrokerActor(self.profile(),100,verifier=verifier,clock=lambda:101)

    def command(self,actor,event,**fields):
        return actor.command(dict(profileIdentity=actor.profile.identity,
                                  sequence=actor.sequence+1,event=event,**fields))

    def test_worker_entry_is_consumed_before_manager_intent_and_never_reused(self):
        actor=self.actor()
        with patch.object(actor.broker,'guard'):
            self.command(actor,'phase',index=0,deadlineNs=200)
            reply=self.command(actor,'workerStart',phase='prepare')
            self.assertEqual(reply['ticket'],0)
            self.assertIsNone(actor.ledger.records[0]['pid'])
            self.assertEqual(actor.ledger.records[0]['status'],'continued-not-launch-proof')
            with self.assertRaisesRegex(ForecastError,'start-phase'):
                self.command(actor,'workerStart',phase='prepare')
        self.assertTrue(actor.ledger.failed)

    def test_worker_handoff_without_reserved_manager_entry_refuses(self):
        actor=self.actor();sock=MagicMock()
        hello=dict(version=launcher.VERSION,profileIdentity=actor.profile.identity,
                   phase='prepare',role='worker',pid=44,filterSha256=launcher.filter_sha256())
        with patch.object(launcher.NativeExecBroker,'guard'),patch.object(launcher,'peer'), \
             patch.object(launcher,'receive_frame',return_value=(hello,None)):
            with self.assertRaisesRegex(ForecastError,'start-permit-required'):
                actor.accept_launcher(sock,role='worker')
        actor.verifier.launcher_identity.assert_not_called()
        self.assertTrue(actor.stopped)

    def test_wrong_controller_sequence_closes_broker(self):
        actor=self.actor()
        with self.assertRaisesRegex(ForecastError,'command-binding'):
            actor.command(dict(profileIdentity=actor.profile.identity,sequence=2,event='summary'))
        self.assertTrue(actor.stopped)

    def test_root_child_exit_race_still_closes_pidfd_and_confirms_reap(self):
        client=launcher.RootGateClient(self.profile(),MagicMock(),child_pidfd=31,child_pid=90,deadline_ns=1)
        with patch.object(client,'call',return_value={'stopped':True}), \
             patch.object(launcher.signal,'pidfd_send_signal',side_effect=ProcessLookupError,create=True), \
             patch.object(launcher.os,'waitpid',side_effect=[(0,0),(90,0)]), \
             patch.object(launcher.os,'close') as close:
            client.stop()
        self.assertTrue(client.cleanup_confirmed);self.assertEqual(client.exit_status,0)
        close.assert_called_once_with(31);self.assertIsNone(client.child_pidfd)

    def test_unreaped_root_child_never_returns_success(self):
        client=launcher.RootGateClient(self.profile(),MagicMock(),child_pidfd=31,child_pid=90,deadline_ns=1)
        with patch.object(client,'call',return_value={'stopped':True}), \
             patch.object(launcher.signal,'pidfd_send_signal',create=True), \
             patch.object(launcher.os,'waitpid',return_value=(0,0)), \
             patch.object(launcher.os,'close') as close:
            with self.assertRaisesRegex(ForecastError,'cleanup-unconfirmed'):client.stop()
        self.assertFalse(client.cleanup_confirmed);close.assert_called_once_with(31)

    def test_any_close_error_permanently_prevents_idempotent_success(self):
        for channel_failure in (True,False):
            channel=MagicMock()
            if channel_failure:channel.close.side_effect=OSError('close channel')
            client=launcher.RootGateClient(self.profile(),channel,child_pidfd=31,child_pid=90,deadline_ns=1)
            with patch.object(client,'call',return_value={'stopped':True}), \
                 patch.object(launcher.os,'waitpid',return_value=(90,0)), \
                 patch.object(launcher.os,'close',side_effect=None if channel_failure else OSError('close pidfd')):
                with self.assertRaises(OSError):client.stop()
                with self.assertRaisesRegex(ForecastError,'cleanup-unconfirmed'):client.stop()
            self.assertFalse(client.stop_succeeded)

    def test_pidfd_open_failure_still_kills_and_reaps_owned_child(self):
        parent=MagicMock();child=MagicMock();listener=MagicMock();p=self.profile(True)
        from agent_braid.forecast_bootstrap import RootBootstrapAuthority
        authority=object.__new__(RootBootstrapAuthority);authority.identity=p.identity;authority.channel=MagicMock()
        with patch.object(launcher.NativeExecBroker,'guard'), \
             patch.object(launcher.Path,'iterdir',return_value=iter([1])), \
             patch.object(launcher.Path,'read_text',return_value=''), \
             patch.object(launcher.os,'listdir',return_value=['0','1','2']), \
             patch.object(launcher.socket,'socketpair',return_value=(parent,child)), \
             patch.object(launcher.os,'fork',return_value=90), \
             patch.object(launcher.os,'pidfd_open',side_effect=OSError('fd cap'),create=True), \
             patch.object(launcher.os,'kill') as kill, \
             patch.object(launcher,'_reap_owned_child',return_value=0) as reap:
            with self.assertRaisesRegex(OSError,'fd cap'):launcher.spawn_root_actor(p,100,listener,bootstrap_receipt={},bootstrap_authority=authority)
        kill.assert_called_once_with(90,9);self.assertEqual(reap.call_args.args[0],90)
        parent.close.assert_called_once();child.close.assert_called_once();listener.close.assert_called_once();authority.channel.close.assert_called_once()

    def test_socket_cleanup_attempts_both_and_preserves_first_error(self):
        first=MagicMock();second=MagicMock()
        first.close.side_effect=OSError('first close');second.close.side_effect=OSError('second close')
        with self.assertRaisesRegex(OSError,'first close'):launcher._close_channels(first,second)
        first.close.assert_called_once();second.close.assert_called_once()

    def test_permission_matching_is_distinct_prior_and_never_refunds_unused(self):
        record=dict(pid=44,status='continued-not-launch-proof',admittedAtNs=10)
        receipt={'summary':{'failed':False},'records':[record,dict(record,pid=45)]}
        result=launcher.reconcile_exec_permits([dict(kind=2,pid=44,ns=11)],receipt)
        self.assertEqual(result['unusedConsumedPermits'],1)
        for events in ([dict(kind=2,pid=44,ns=9)], [dict(kind=2,pid=44,ns=11)]*2):
            with self.assertRaisesRegex(ForecastError,'unpermitted'):
                launcher.reconcile_exec_permits(events,receipt)
        receipt['summary']['failed']=True
        with self.assertRaisesRegex(ForecastError,'ledger-failed'):
            launcher.reconcile_exec_permits([],receipt)

    def test_bootstrap_reads_stay_charged_to_prepare(self):
        view=SimpleNamespace(bytes_read=20,remaining=0)
        verifier=launcher.NativeLauncherVerifier(self.profile(),controller_pid=44,view=view)
        view.remaining-=10;view.bytes_read+=10
        verifier.phase_budget(0)
        self.assertEqual(view.remaining,1024**3-10)
        verifier.phase_budget(1)
        self.assertEqual(verifier.phase_reads,[{'phaseIndex':0,'bytes':10}])
        self.assertEqual(view.remaining,1024**3)


if __name__=='__main__':unittest.main()
