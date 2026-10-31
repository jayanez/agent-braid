# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic ABI/facts only. Rejected frames do not prove native interception."""
import unittest
from dataclasses import replace

from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_manager_escrow import decode_request, REQUEST, MAGIC, ManagerEscrowState
from agent_braid.forecast_v9_renderer import render_offline_v9
from tests.test_forecast_manager_escrow import binding, facts, complete_role
from tests.test_forecast_v9_driver import profile


def frame(name,site=0):
    return REQUEST.pack(MAGIC,1,site,0,name.encode(),b'd'*32+b'\0',b'\0'*7)


class PreexecCoverageTests(unittest.TestCase):
    def test_foreign_and_lookalike_names_cannot_enter_current_protocol_roster(self):
        b=binding();state=ManagerEscrowState(b,100);state.begin(77,now_ns=101)
        before=state.ledger.receipt()
        foreign=['modprobe@loop.service','modprobe@dm_mod.service','modprobe@dm_verity.service',
                 'fc1'+b.identity+'-modprobe.service','fc1'+'e'*64+'-prepare.service']
        for name in foreign:
            for site in (0,1):
                with self.subTest(name=name,site=site),self.assertRaisesRegex(ForecastError,'unit-binding'):
                    decode_request(frame(name,site),b)
        self.assertEqual(state.ledger.receipt(),before)
        # Positive control verifies this tests exact membership, not an always-deny parser.
        for role in range(6):
            self.assertEqual(decode_request(frame(b.unit(role)),b),(role,0,'d'*32))

    def test_known_name_does_not_bypass_executor_cgroup_binding_or_refund_prior_attempt(self):
        b=binding();state=ManagerEscrowState(b,100);state.begin(77,now_ns=101)
        for role in range(3):complete_role(state,role,102)
        request=decode_request(frame(b.unit(3),0),b)
        ticket,_=state.reserve(request,facts(b,3,0),now_ns=103);state.delivered(ticket,sent=True)
        consumed=len(state.ledger.records)
        request=decode_request(frame(b.unit(3),1),b)
        wrong=replace(facts(b,3,1),cgroup='/system.slice/modprobe@loop.service')
        with self.assertRaisesRegex(ForecastError,'executor-identity'):
            state.reserve(request,wrong,now_ns=104)
        self.assertTrue(state.failed)
        self.assertEqual(len(state.ledger.records),consumed)
        self.assertEqual(consumed,8)

    def test_protocol_refusal_is_not_a_claim_that_external_exec_was_blocked(self):
        report=render_offline_v9(profile())['dependencyInventory']['moduleBudgetObligations']
        coverage=report['preExecCoverage']
        self.assertEqual(len(coverage['receiverNames']),6)
        self.assertEqual(len(coverage['targets']),3)
        for row in coverage['targets']:
            self.assertIs(row['receiverNameEligible'],False)
            self.assertIs(row['receiverWouldRejectForeignName'],True)
            self.assertIs(row['site0SenderRequestsAdmission'],False)
            self.assertIs(row['site1SenderRequestsAdmission'],False)
            self.assertIs(row['preExecRejectionObserved'],False)
        self.assertIs(coverage['receiverRejectionEstablishesInterception'],False)
        self.assertIs(coverage['workerListenerCoversPID1SiblingServices'],False)
        self.assertEqual(coverage['additionalRolesGranted'],0)
        self.assertEqual(coverage['additionalExecAllowanceGranted'],0)
        self.assertIs(report['operationalBudgetClosed'],False)
        self.assertIsNone(report['execAttemptUpperBound'])
