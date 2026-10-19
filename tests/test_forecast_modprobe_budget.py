# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic advisory budget fixtures only; no modprobe, manager or model."""
from copy import deepcopy
import unittest

from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_exec_budget import ExecAllocation, module_dependency_budget, ESCROW
from agent_braid.forecast_v9_renderer import render_offline_v9
from tests.test_forecast_v9_driver import profile


class ModuleBudgetTests(unittest.TestCase):
    def fixture(self):
        p=profile();d=render_offline_v9(p)['dependencyInventory']
        return ExecAllocation.from_profile(p),d['contextGeneratedJobObligations']

    def test_nine_references_are_three_targets_and_never_nine_observed_starts(self):
        allocation,rows=self.fixture();d=module_dependency_budget(allocation,rows)
        self.assertEqual(d['wantsReferences'],9);self.assertEqual(len(d['distinctTargets']),3)
        self.assertIsNone(d['observedActivations'])
        one,phased=d['illustrations']
        self.assertEqual(one['subtotalExecAttempts'],6)
        self.assertEqual(phased['subtotalExecAttempts'],18)
        self.assertEqual(phased['extraAttemptsByPhase'],[6,0,0,6,6])
        self.assertFalse(one['isUpperBound'] or phased['isUpperBound'])
        self.assertIsNone(d['execAttemptUpperBound']);self.assertIsNone(d['wholeFlowCostUpperBound'])

    def test_no_lending_refund_or_allocation_growth(self):
        allocation,rows=self.fixture();before=allocation.manifest();d=module_dependency_budget(allocation,rows)
        self.assertEqual(allocation.manifest(),before)
        self.assertEqual(d['retainedAllocation'],before)
        self.assertEqual(d['retainedEscrow'],list(ESCROW))
        self.assertIs(d['brokerMayCoverTheseJobs'],False)
        self.assertEqual(d['extraExecAllowanceGranted'],0)
        for field in ('escrowCoverageVerified','operationalBudgetClosed','nativeQualification','executionAuthorization'):
            self.assertIs(d[field],False)

    def test_synthetic_one_site_vs_three_sites_changes_references_not_unique_targets(self):
        a,rows=self.fixture();one=module_dependency_budget(a,rows[:1]);three=module_dependency_budget(a,rows)
        self.assertEqual(one['distinctTargets'],three['distinctTargets'])
        self.assertEqual(one['illustrations'][1]['extraAttemptsByPhase'],[6,0,0,0,0])
        self.assertEqual(one['illustrations'][0]['subtotalExecAttempts'],three['illustrations'][0]['subtotalExecAttempts'])
        self.assertIs(one['operationalBudgetClosed'],False)

    def test_replayed_site_bad_target_or_claimed_native_fact_is_rejected(self):
        a,rows=self.fixture()
        cases=[rows[:1]*2,deepcopy(rows),deepcopy(rows),deepcopy(rows)]
        cases[1][0]['edges'][0]['to']='other.service'
        cases[2][0]['activationObserved']=True
        cases[3][0]['effectiveContextVerified']=True
        for rows in cases:
            with self.subTest(rows=len(rows)),self.assertRaises(ForecastError):module_dependency_budget(a,rows)

    def test_empty_projection_does_not_close_budget_or_invent_observation(self):
        a,_=self.fixture();d=module_dependency_budget(a,[])
        self.assertEqual(d['distinctTargets'],[])
        self.assertIsNone(d['observedActivations'])
        self.assertIsNone(d['execAttemptUpperBound'])
        self.assertIs(d['operationalBudgetClosed'],False)
