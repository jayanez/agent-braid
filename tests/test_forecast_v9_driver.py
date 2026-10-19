# SPDX-License-Identifier: AGPL-3.0-only
"""New driver accounting regression cases; no provider, socket, process or model."""
from dataclasses import FrozenInstanceError,replace
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_exec_budget import ExecAllocation
from agent_braid.forecast_linux_profile import LinuxAdmissionProfile,PhaseLimit,STEPS
from agent_braid.forecast_manager_escrow import GateBinding
from agent_braid.forecast_v9_driver import DriverPreparation,V9Driver,prepare_driver
from tests.test_forecast_manager_escrow import complete_role


def profile():
    return LinuxAdmissionProfile(mode='serial',image_sha256='a'*64,root_hash='b'*64,
        source_digest='c'*64,manager_sha256='d'*64,operator_sha256='f'*64,
        operator_entry_sha256='8'*64,worker_sha256='9'*64,census_sha256='a'*64,
        recipe_sha256='e'*64,uid=61001,
        limits=tuple(PhaseLimit(p,0 if p=='terminal' else 1,10,4096,8) for p in STEPS))


def preparation():
    p=profile();b=GateBinding(p.identity,p.manager_sha256,'7'*64,100,p.uid,ExecAllocation.from_profile(p))
    return DriverPreparation(p.identity,p.source_digest,'1'*64,'2'*64,'3'*64,'4'*64,b'{}',b)


class DriverTests(unittest.TestCase):
    def test_frozen_identity_binds_inventory_executor_nonce_and_allocation(self):
        p=preparation()
        with self.assertRaises(FrozenInstanceError):p.nonce='5'*64
        for changed in (replace(p,nonce='5'*64),replace(p,inventory_digest='5'*64),
                        replace(p,binding=replace(p.binding,executor_sha256='5'*64)),
                        replace(p,binding=replace(p.binding,allocation=replace(p.binding.allocation,seconds=(11,10,10,10,10))))):
            self.assertNotEqual(p.identity,changed.identity)

    def test_preparation_binds_actual_census_fields_without_promoting_provenance(self):
        p=profile();fields={'manager':'manager_sha256','operatorPython':'operator_sha256',
            'operatorLauncher':'operator_entry_sha256','workerPython':'worker_sha256','execCensus':'census_sha256'}
        census={'sourceDigest':p.source_digest,'manifestSha256':'1'*64,'inventoryDigest':'2'*64,
                'provenanceSha256':'3'*64,'bindings':{role:{'sha256':getattr(p,field)} for role,field in fields.items()}}
        census['bindings']['executor']={'sha256':'7'*64}
        with patch('agent_braid.forecast_v9_driver.inspect_staged_host',return_value=census) as inspect:
            ready=prepare_driver(p,'/unused',b'not read by mock',expected_manifest_sha256='1'*64,
                                 nonce='4'*64,manager_start_ticks=100)
            self.assertEqual(ready.binding.executor_sha256,'7'*64);inspect.assert_called_once()
            census['bindings']['manager']['sha256']='0'*64
            with self.assertRaisesRegex(ForecastError,'artifact-binding'):
                prepare_driver(p,'/unused',b'',expected_manifest_sha256='1'*64,nonce='4'*64,manager_start_ticks=100)

    def test_complete_accounting_is_never_native_or_cleanup_acceptance(self):
        d=V9Driver(preparation(),100);d.begin(77,now_ns=101)
        for r in range(4):complete_role(d.escrow,r,102)
        for phase in (1,2,3):d.advance(phase,now_ns=110+phase)
        complete_role(d.escrow,4,120);d.advance(4,now_ns=121);complete_role(d.escrow,5,122)
        d.finish_accounting(now_ns=123);receipt=d.receipt()
        self.assertTrue(receipt['accountingFinished'])
        for field in ('nativeQualification','executionAuthorization','wholeFlowCleanupVerified',
                      'operationalBudgetClosed','hostActivationClosed','externalWatchdogAccepted'):
            self.assertFalse(receipt[field])
        with self.assertRaises(ForecastError):d.begin(77,now_ns=124)

    def test_expiry_outstanding_and_ambiguity_poison_both_partitions(self):
        for reason in ('expiry','outstanding','unknown'):
            d=V9Driver(preparation(),100);d.begin(77,now_ns=101)
            for r in range(4):complete_role(d.escrow,r,102)
            t=d.reserve_broker('readback',77,now_ns=103)
            with self.subTest(reason=reason),self.assertRaises(ForecastError):
                if reason=='expiry':d.advance(1,now_ns=d.broker.deadline)
                elif reason=='outstanding':d.advance(1,now_ns=104)
                else:d.finish_broker(t,continued=False,now_ns=104)
            self.assertTrue(d.failed and d.escrow.failed and d.broker.failed)
            self.assertEqual(d.receipt()['originalOriginNs'],100)
            self.assertEqual(len(d.broker.records),1)

    def test_native_entry_refuses_before_any_bootstrap_or_host_side_effect(self):
        d=V9Driver(preparation(),100)
        with self.assertRaisesRegex(ForecastError,'bootstrap-native-readiness-pending'):
            d.native_entry(profile())
        with patch('agent_braid.forecast_v9_driver.bootstrap_ready'):
            with self.assertRaisesRegex(ForecastError,'outer-guard-pending'):d.native_entry(profile())

    def test_partition_tampering_cannot_advance_one_clock(self):
        d=V9Driver(preparation(),100);d.begin(77,now_ns=101);d.broker.deadline+=1
        with self.assertRaisesRegex(ForecastError,'partition-drift'):
            d.reserve_broker('not admitted',77,now_ns=102)
        self.assertTrue(d.failed)
