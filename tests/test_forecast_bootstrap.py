# SPDX-License-Identifier: AGPL-3.0-only
"""Pure escrow/import and mocked manager controls; no native starts or grants."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from agent_braid.forecast_bootstrap import ExternalBootstrapEscrow,RootBootstrapAuthority,EscrowAuthorityServer,adopt_bootstrap
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_exec_gate import ExecPermitLedger


ROOT_GUARD=RootBootstrapAuthority.guard


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        mocked=patch.object(RootBootstrapAuthority,'guard')
        mocked.start();self.addCleanup(mocked.stop)

    def authority(self,escrow,verified=True):
        obj=object.__new__(RootBootstrapAuthority)
        obj.identity=escrow.profile.identity;obj.expected_plan_digest=escrow.plan_digest
        obj.verify_prior=MagicMock(return_value=verified);obj.channel=MagicMock()
        return obj

    def test_kernel_root_guard_rejects_worker_uid(self):
        with patch('agent_braid.forecast_bootstrap.sys.platform','linux'), \
             patch('agent_braid.forecast_bootstrap.os.geteuid',return_value=61000):
            with self.assertRaisesRegex(ForecastError,'root-only'):ROOT_GUARD()

    def profile(self,ready=False):
        identity='a'*64;stem='fc1'+identity
        return SimpleNamespace(identity=identity,manager_sha256='b'*64,
            operator_sha256='c'*64,operator_entry_sha256='d'*64,
            limits=[SimpleNamespace(requests=1,wall_seconds=10)]*5,
            manifest=lambda:{'execAdmissionEnforced':ready,'bootstrapSupervisionAccepted':ready},
            units=lambda **kw:{stem+'-supervisor.service':'supervisor',stem+'.service':'anchor',stem+'-operator.service':'operator'})

    def escrow(self,ready=True):
        profile=self.profile(ready);provider=MagicMock();backend=MagicMock();backend.request_start.return_value='job/1'
        escrow=ExternalBootstrapEscrow(profile,100,'e'*64,provider=provider,backend=backend,clock=lambda:150)
        provider.authorize_start.return_value=True
        provider.read_loaded.side_effect=lambda plan,unit:{'profileIdentity':profile.identity,
            'managerSha256':profile.manager_sha256,'unit':unit,'unitSha256':plan['unitSha256'][unit],
            'absoluteDeadlineNs':plan['wholeDeadlineNs']}
        provider.read_watchdog.side_effect=lambda plan:{**plan['supervision'],'armedAtNs':100,
            'observedAtNs':150,'running':True,'planDigest':digest(plan)}
        provider.cancel_and_verify_empty.side_effect=lambda plan,request:{
            **request,'observedAtNs':150,'populated':False}
        provider.observe_started.side_effect=lambda plan,row:{'pid':40+row['reservation'],
            'observedAtNs':150,'processStartTicks':700+row['reservation'],'unitSha256':row['unitSha256'],'unaccountedExecs':0}
        return escrow

    def completed(self):
        escrow=self.escrow();escrow.dispatch('supervisor');escrow.dispatch('anchor');escrow.dispatch('operator');return escrow

    def test_false_readiness_precedes_callbacks_and_reservations(self):
        escrow=self.escrow(False)
        with self.assertRaisesRegex(ForecastError,'readiness-pending'):escrow.dispatch('supervisor')
        self.assertEqual(escrow.records,[]);escrow.provider.authorize_start.assert_not_called()
        escrow.backend.request_start.assert_not_called()

    def test_exec_readiness_alone_cannot_admit_bootstrap(self):
        escrow=self.escrow()
        escrow.profile.manifest=lambda:{'execAdmissionEnforced':True,'bootstrapSupervisionAccepted':False}
        with self.assertRaisesRegex(ForecastError,'readiness-pending'):escrow.dispatch('supervisor')
        escrow.provider.read_watchdog.assert_not_called();escrow.backend.request_start.assert_not_called()

    def test_relative_timer_or_late_rearmed_watchdog_cannot_start_operator(self):
        for change in ({'managerIndependent':False},{'issuerExitRevokes':False},
                       {'armedAtNs':151},{'cancelAtNs':50*10**9+100}):
            escrow=self.escrow();plan=escrow.plan
            value={**plan['supervision'],'armedAtNs':100,'observedAtNs':150,
                   'running':True,'planDigest':digest(plan),**change}
            escrow.provider.read_watchdog.side_effect=None;escrow.provider.read_watchdog.return_value=value
            with self.assertRaises(ForecastError):escrow.dispatch('supervisor')
            escrow.backend.request_start.assert_not_called()
        escrow=self.escrow();escrow.dispatch('supervisor')
        escrow.provider.read_watchdog.side_effect=lambda plan:{**plan['supervision'],'armedAtNs':101,
            'observedAtNs':150,'running':True,'planDigest':digest(plan)}
        with self.assertRaisesRegex(ForecastError,'rearmed'):escrow.dispatch('anchor')
        self.assertEqual(escrow.backend.request_start.call_count,1)
        self.assertTrue(escrow.cleanup['confirmed'])

    def test_watchdog_loss_after_manager_start_cancels_whole_scope_without_retry(self):
        escrow=self.escrow();read=escrow.provider.read_watchdog.side_effect
        escrow.provider.read_watchdog.side_effect=lambda plan: read(plan) if not escrow.backend.request_start.called else {}
        with self.assertRaisesRegex(ForecastError,'watchdog-fields'):escrow.dispatch('supervisor')
        self.assertTrue(escrow.records[0]['admitted']);self.assertTrue(escrow.cleanup['confirmed'])
        escrow.provider.cancel_and_verify_empty.assert_called_once_with(escrow.plan,escrow.cleanup['request'])
        with self.assertRaises(ForecastError):escrow.dispatch('operator')
        self.assertEqual(escrow.backend.request_start.call_count,1)

    def test_uncertain_or_late_cleanup_never_becomes_confirmed(self):
        for change in ({'scope':'wrong'}, {'populated':True}, {'observedAtNs':50*10**9+100},
                       {'observedAtNs':149}, {'nonce':'f'*64}, {'planDigest':'f'*64},
                       {'requestedAtNs':149}):
            escrow=self.escrow();escrow.provider.observe_started.side_effect=OSError('uncertain')
            escrow.provider.cancel_and_verify_empty.side_effect=lambda plan,request:{
                **request,'observedAtNs':150,'populated':False,**change}
            with self.assertRaises(OSError):escrow.dispatch('supervisor')
            self.assertTrue(escrow.failed);self.assertFalse(escrow.cleanup['confirmed'])
            with self.assertRaises(ForecastError):escrow.dispatch('operator')
            self.assertEqual(escrow.provider.cancel_and_verify_empty.call_count,1)

    def test_failed_reservation_after_anchor_also_revokes_without_starting_operator(self):
        escrow=self.escrow();escrow.dispatch('supervisor')
        with self.assertRaisesRegex(ForecastError,'order-or-retry'):escrow.dispatch('supervisor')
        self.assertTrue(escrow.cleanup['confirmed'])
        self.assertEqual(escrow.backend.request_start.call_count,1)

    def test_prior_reservation_and_loaded_unit_binding_precede_manager_request(self):
        escrow=self.escrow()
        def start(unit,row,deadline):
            self.assertTrue(escrow.records[0]['attempted']);self.assertTrue(row['admitted'])
            self.assertEqual(row['state'],'dispatch-indeterminate');return 'job/1'
        escrow.backend.request_start.side_effect=start
        self.assertTrue(escrow.dispatch('supervisor')['launched'])
        self.assertFalse(escrow.receipt()['nativeCoverageAccepted'])

    def test_wrong_loaded_definition_or_missing_absolute_watchdog_never_starts(self):
        for loaded in ({}, {'managerSha256':'f'*64}):
            escrow=self.escrow();escrow.provider.read_loaded.return_value=loaded
            escrow.provider.read_loaded.side_effect=None
            with self.assertRaisesRegex(ForecastError,'loaded-definition'):escrow.dispatch('supervisor')
            escrow.backend.request_start.assert_not_called();self.assertTrue(escrow.failed)
            self.assertEqual(escrow.records[0]['state'],'refused-consumed')

    def test_unobserved_start_is_consumed_and_cannot_retry(self):
        escrow=self.escrow();escrow.provider.observe_started.side_effect=OSError('unknown launch')
        with self.assertRaises(OSError):escrow.dispatch('supervisor')
        self.assertTrue(escrow.records[0]['admitted']);self.assertFalse(escrow.records[0]['launched'])
        with self.assertRaisesRegex(ForecastError,'order-or-retry'):escrow.dispatch('supervisor')
        self.assertEqual(len(escrow.records),1)

    def test_operator_cannot_precede_independently_observed_anchor(self):
        escrow=self.escrow();escrow.reserve('supervisor')
        with self.assertRaisesRegex(ForecastError,'prior-start-unconfirmed'):escrow.reserve('anchor')
        escrow.backend.request_start.assert_not_called()

    def test_unit_or_challenge_drift_poison_escrow(self):
        escrow=self.escrow();escrow.plan['nonce']='f'*64
        with self.assertRaisesRegex(ForecastError,'plan-drift'):escrow.reserve('supervisor')
        self.assertTrue(escrow.failed)

    def test_root_authority_checks_kernel_peer_elf_and_process_lifetime(self):
        escrow=self.completed();channel=MagicMock();view=MagicMock()
        view.state.return_value={'start':800}
        expected={'event':'verifyPriorBootstrap','profileIdentity':escrow.profile.identity,
                  'sequence':1,'planDigest':escrow.plan_digest,'receiptDigest':digest(escrow.receipt())}
        with patch('agent_braid.forecast_operator_bridge.peer') as peer, \
             patch('agent_braid.forecast_operator_bridge.send') as send, \
             patch('agent_braid.forecast_operator_bridge.receive',return_value={**expected,'priorEscrowVerified':True}), \
             patch('agent_braid.forecast_bootstrap.time.monotonic_ns',return_value=151):
            authority=RootBootstrapAuthority(escrow.profile,channel,issuer_pid=88,issuer_sha256='f'*64,
                                           expected_plan_digest=escrow.plan_digest,view=view)
            self.assertTrue(authority.verify_prior(escrow.receipt()))
            peer.assert_called_with(channel,uid=0,pid=88);send.assert_called_once_with(channel,expected)
            view.state.return_value={'start':801}
            with self.assertRaisesRegex(ForecastError,'issuer-reused'):authority.verify_prior(escrow.receipt())
        self.assertEqual(view.executable.call_count,2)

    def test_issuer_authenticates_its_retained_history_not_a_supplied_receipt(self):
        escrow=self.completed();view=MagicMock();channel=MagicMock()
        view.state.side_effect=lambda pid:{'start':700+pid-40,'state':'S'}
        request={'event':'verifyPriorBootstrap','profileIdentity':escrow.profile.identity,'sequence':1,
                 'planDigest':escrow.plan_digest,'receiptDigest':digest(escrow.receipt())}
        with patch('agent_braid.forecast_operator_bridge.peer') as peer, \
             patch('agent_braid.forecast_operator_bridge.send') as send, \
             patch('agent_braid.forecast_operator_bridge.receive',return_value=request), \
             patch('agent_braid.forecast_bootstrap.time.monotonic_ns',return_value=151):
            server=EscrowAuthorityServer(escrow,view=view)
            self.assertTrue(server.serve_once(channel)['retainedHistoryMatched'])
            peer.assert_called_with(channel,uid=0,pid=42)
            send.assert_called_once_with(channel,{**request,'priorEscrowVerified':True})
            with self.assertRaisesRegex(ForecastError,'replay-or-drift'):server.serve_once(channel)

    def test_actor_imports_startup_before_phase_zero_and_binds_operator_pid(self):
        from agent_braid.forecast_launcher import RootBrokerActor,VERSION,filter_sha256
        from agent_braid.forecast_exec_gate import NativeExecBroker
        escrow=self.completed();verifier=MagicMock();authority=self.authority(escrow)
        actor=RootBrokerActor(escrow.profile,100,verifier=verifier,clock=lambda:151,
                              bootstrap_receipt=escrow.receipt(),bootstrap_authority=authority)
        self.assertEqual(actor.ledger.phase,0);self.assertEqual(len(actor.ledger.records),3)
        verifier.phase_budget.assert_called_once_with(0)
        hello={'version':VERSION,'profileIdentity':escrow.profile.identity,'phase':'prepare',
               'role':'operator','pid':99,'filterSha256':filter_sha256()}
        with patch.object(NativeExecBroker,'guard'), \
             patch('agent_braid.forecast_launcher.receive_frame',return_value=(hello,None)):
            with self.assertRaisesRegex(ForecastError,'bootstrap-unbound'):
                actor.accept_launcher(MagicMock(),role='operator')
        verifier.launcher_identity.assert_not_called()

    def test_external_prior_authority_is_mandatory_not_just_receipt_hash(self):
        escrow=self.completed();ledger=ExecPermitLedger(escrow.profile,100)
        with self.assertRaisesRegex(ForecastError,'prior-escrow-unverified'):
            adopt_bootstrap(escrow.profile,ledger,escrow.receipt(),authority=self.authority(escrow,False),now_ns=151)
        self.assertEqual(ledger.records,[]);self.assertTrue(ledger.failed)

    def test_caller_callback_is_not_a_root_authority(self):
        escrow=self.completed();ledger=ExecPermitLedger(escrow.profile,100)
        with self.assertRaisesRegex(ForecastError,'root-authority-required'):
            adopt_bootstrap(escrow.profile,ledger,escrow.receipt(),authority=lambda receipt:True,now_ns=151)
        self.assertEqual(ledger.records,[])

    def test_unready_import_cannot_invoke_even_a_root_authority(self):
        escrow=self.escrow(False);ledger=ExecPermitLedger(escrow.profile,100);authority=MagicMock()
        with self.assertRaisesRegex(ForecastError,'readiness-pending'):
            adopt_bootstrap(escrow.profile,ledger,{},authority=authority,now_ns=151)
        authority.verify_prior.assert_not_called();self.assertEqual(ledger.records,[])

    def test_startup_import_consumes_existing_prepare_slots_and_does_not_extend_clock(self):
        escrow=self.completed();ledger=ExecPermitLedger(escrow.profile,100)
        result=adopt_bootstrap(escrow.profile,ledger,escrow.receipt(),authority=self.authority(escrow),now_ns=151)
        self.assertEqual(result['additionalExecAllowance'],0);self.assertEqual(len(ledger.records),3)
        self.assertEqual(ledger.deadline,100+10*10**9)
        for i in range(2):
            token=ledger.reserve('tool',i,70,now_ns=152);ledger.finish(token,continued=True)
        with self.assertRaisesRegex(ForecastError,'quota-exhausted'):ledger.reserve('tool',4,70,now_ns=152)

    def test_reordered_replayed_or_backdated_receipt_cannot_import(self):
        escrow=self.completed();original=escrow.receipt()
        mutations=[lambda r:r['records'].reverse(),lambda r:r['records'][1].update(admittedAtNs=99),
                   lambda r:r['records'][1].update(pid=40),lambda r:r.update(nativeCoverageAccepted=True),
                   lambda r:r['watchdogObservations'].pop(),
                   lambda r:r['watchdogObservations'][2].update(armedAtNs=101)]
        for mutate in mutations:
            receipt=deepcopy(original);mutate(receipt);ledger=ExecPermitLedger(escrow.profile,100)
            with self.assertRaises(ForecastError):
                adopt_bootstrap(escrow.profile,ledger,receipt,authority=self.authority(escrow),now_ns=151)
            self.assertTrue(ledger.failed);self.assertEqual(ledger.records,[])
        ledger=ExecPermitLedger(escrow.profile,100)
        adopt_bootstrap(escrow.profile,ledger,original,authority=self.authority(escrow),now_ns=151)
        with self.assertRaisesRegex(ForecastError,'origin-state'):
            adopt_bootstrap(escrow.profile,ledger,original,authority=self.authority(escrow),now_ns=151)


if __name__=='__main__':unittest.main()
