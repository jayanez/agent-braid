# SPDX-License-Identifier: AGPL-3.0-only
"""Offline composition only; invented process facts, no transport or model."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_v9_driver import offline_v9_plan, OfflineV9Integration
from agent_braid.forecast_manager import require_closed_job_graph
from tests.test_forecast_v9_driver import preparation, profile
from tests.test_forecast_manager_escrow import complete_role


class IntegrationTests(unittest.TestCase):
    def session(self):
        s = OfflineV9Integration(preparation(), profile(), 100)
        s.driver.begin(77, now_ns=101)
        return s

    def startup(self, s):
        for role in range(4):
            complete_role(s.driver.escrow, role, 102)
        s.broker.bind_launcher('prepare', 88, 50, now_ns=103)

    def test_plan_binds_graph_bootstrap_original_clock_and_disjoint_budget(self):
        p = offline_v9_plan(preparation(), profile(), 100)
        self.assertEqual(p['bootstrap']['graphDigest'], digest(p['graph']))
        self.assertEqual(p['bootstrap']['originNs'], 100)
        self.assertEqual(p['bootstrap']['wholeDeadlineNs'], 50000000100)
        self.assertEqual(p['bootstrap']['brokerStartupExecAttempts'], 0)
        self.assertEqual(p['bootstrap']['startupExecAttempts'], 7)
        self.assertEqual(p['bootstrap']['startupRoles'], ['supervisor','anchor','operator'])
        self.assertEqual(p['bootstrap']['phaseZeroWorkerRoles'], ['prepare'])
        self.assertEqual(p['bootstrap']['phaseZeroWorkerExecAttempts'], 2)
        self.assertEqual(p['bootstrap']['phaseZeroEscrowExecAttempts'], 9)
        self.assertEqual(p['allocation']['escrow'], [9,0,0,2,2])
        self.assertEqual(p['allocation']['broker'], [3,3,3,3,1])
        self.assertEqual(p['graph']['managerMountJobs'], [])
        self.assertFalse(p['graph']['nativeGraphClosed'])
        self.assertNotEqual(digest(p), digest(offline_v9_plan(preparation(), profile(), 101)))
        for key in ('profileV9Emitted','candidateReadyForNativeAdmission',
                    'operationalBudgetClosed','nativeQualification','executionAuthorization'):
            self.assertIs(p[key], False)

    def test_profile_mix_refused(self):
        with self.assertRaisesRegex(ForecastError, 'profile-binding'):
            offline_v9_plan(preparation(), replace(profile(), uid=61002), 100)

    def test_launcher_before_escrow_or_duplicate_binding_poisons_session(self):
        s = self.session()
        with self.assertRaisesRegex(ForecastError, 'before-escrow'):
            s.broker.bind_launcher('prepare',88,50,now_ns=102)
        self.assertTrue(s.driver.failed)
        s = self.session(); self.startup(s)
        with self.assertRaisesRegex(ForecastError, 'replay'):
            s.broker.bind_launcher('prepare',88,50,now_ns=104)
        self.assertTrue(s.driver.escrow.failed)

    def test_startup_not_charged_to_broker_and_receipt_is_detached(self):
        s = self.session(); self.startup(s)
        self.assertEqual(len(s.driver.escrow.ledger.records), 9)
        self.assertEqual(s.driver.broker.records, [])
        ticket = s.broker.reserve('prepare',88,50,1,now_ns=104)
        s.broker.delivered(ticket,continued=True,now_ns=105)
        r = s.receipt(); r['broker']['launchers']['prepare']['pid'] = 999
        self.assertEqual(s.receipt()['broker']['launchers']['prepare']['pid'],88)
        self.assertFalse(r['broker']['launcherIdentityVerified'])
        self.assertFalse(r['nativeQualification'])
        self.assertFalse(r['driver']['accountingFinished'])

    def test_notification_replay_across_phase_is_not_new_allowance(self):
        s = self.session(); self.startup(s)
        t = s.broker.reserve('prepare',88,50,1,now_ns=104)
        s.broker.delivered(t,continued=True,now_ns=105)
        s.driver.advance(1,now_ns=106)
        with self.assertRaisesRegex(ForecastError, 'notification-replay'):
            s.broker.reserve('prepare',88,50,1,now_ns=107)
        self.assertTrue(s.driver.failed)
        self.assertEqual(len(s.driver.broker.records),1)

    def test_wrong_process_and_late_or_unknown_delivery_never_refund(self):
        for reason in ('start','deadline','unknown'):
            s = self.session(); self.startup(s)
            with self.subTest(reason=reason), self.assertRaises(ForecastError):
                if reason == 'start':
                    s.broker.reserve('prepare',88,51,1,now_ns=104)
                else:
                    t = s.broker.reserve('prepare',88,50,1,now_ns=104)
                    s.broker.delivered(t,continued=reason!='unknown',
                        now_ns=s.driver.broker.deadline if reason=='deadline' else 105)
            self.assertTrue(s.driver.failed and s.driver.escrow.failed)
            self.assertEqual(len(s.driver.broker.records), int(reason!='start'))

    def test_old_renderer_and_native_entry_remain_independently_blocked(self):
        s = self.session()
        with self.assertRaisesRegex(ForecastError,'manager-job-graph-unclosed'):
            require_closed_job_graph(profile())
        with patch('agent_braid.forecast_v9_driver.bootstrap_ready'):
            with self.assertRaisesRegex(ForecastError,'outer-guard-pending'):
                s.driver.native_entry(profile())

    def test_worker_cannot_follow_operator_into_verification_phase(self):
        s = self.session(); self.startup(s)
        for phase in (1,2,3): s.driver.advance(phase,now_ns=105+phase)
        with self.assertRaisesRegex(ForecastError,'launcher-binding'):
            s.broker.reserve('prepare',88,50,1,now_ns=109)
        self.assertTrue(s.driver.failed)

    def test_second_adapter_cannot_reset_launcher_or_notification_history(self):
        from agent_braid.forecast_launcher import OfflineBrokerV2
        s = self.session(); self.startup(s)
        with self.assertRaisesRegex(ForecastError, 'already-attached'):
            OfflineBrokerV2(s.driver, s.identity)
        self.assertEqual(s.broker.receipt()['launchers']['prepare']['pid'], 88)

    def test_integrated_five_phase_accounting_keeps_all_acceptance_gates_false(self):
        s = self.session(); self.startup(s)
        s.broker.bind_launcher('operator', 89, 51, now_ns=104)
        for phase in range(5):
            if phase:
                s.driver.advance(phase,now_ns=110+phase*10)
            if phase in (3,4):
                complete_role(s.driver.escrow,phase+1,111+phase*10)
                role = 'verify' if phase==3 else 'terminal'
                s.broker.bind_launcher(role,90+phase,60+phase,now_ns=112+phase*10)
            else:
                role = 'prepare'
            row=s.broker.launchers[role]
            ticket=s.broker.reserve(role,row['pid'],row['startTicks'],phase+1,now_ns=113+phase*10)
            s.broker.delivered(ticket,continued=True,now_ns=114+phase*10)
        s.driver.finish_accounting(now_ns=155)
        receipt=s.receipt()
        self.assertTrue(receipt['driver']['accountingFinished'])
        self.assertEqual(len(receipt['broker']['partition']['records']),5)
        self.assertEqual(len(s.driver.escrow.ledger.records),13)
        self.assertIs(receipt['driver']['operationalBudgetClosed'],False)
        self.assertIs(receipt['driver']['wholeFlowCleanupVerified'],False)
        self.assertIs(receipt['executionAuthorization'],False)
