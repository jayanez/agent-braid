# SPDX-License-Identifier: AGPL-3.0-only
"""Quota accounting only; no process, manager or real workload is used."""
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_exec_budget import ExecAllocation, PartitionLedger


class AllocationTests(unittest.TestCase):
    def allocation(self, requests=(1793, 769, 1025, 256, 0)):
        return ExecAllocation('a'*64, requests, (10,)*5)

    def test_exact_serial_parallel_totals_and_fixed_partition(self):
        for requests, total in [((1793,769,1025,256,0),7704),
                                ((2049,1025,2050,1538,0),13342)]:
            a = self.allocation(requests)
            self.assertEqual(a.total, total)
            self.assertEqual(a.manifest()['escrow'], [9,0,0,2,2])
            self.assertEqual(sum(a.manifest()['phases']), total)
            self.assertEqual(a.manifest()['phases'][-1], 3)

    def test_broker_cannot_spend_unused_escrow_or_future_phase(self):
        a=self.allocation((0,0,0,0,0));b=PartitionLedger(a,'broker',100)
        b.enter(0,200,now_ns=100)
        ticket=b.reserve('one',42,now_ns=101);b.finish(ticket,continued=True)
        with self.assertRaisesRegex(ForecastError,'partition-exhausted'):
            b.reserve('second',42,now_ns=102)
        self.assertTrue(b.failed)
        self.assertEqual(a.cap('escrow',0),9)

    def test_ambiguity_replay_and_deadline_never_refund(self):
        for cause in ('unknown','replay','deadline'):
            b=PartitionLedger(self.allocation(),'escrow',100);b.enter(0,200,now_ns=100)
            token=b.reserve('entry',42,now_ns=101)
            b.finish(token,continued=cause!='unknown')
            with self.subTest(cause=cause),self.assertRaises(ForecastError):
                b.reserve('entry',42,now_ns=200 if cause=='deadline' else 102)
            self.assertEqual(len(b.records),1)

    def test_outstanding_attempt_and_future_time_reserve_prevent_transition(self):
        b=PartitionLedger(self.allocation(),'escrow',100);b.enter(0,200,now_ns=100)
        b.reserve('entry',42,now_ns=101)
        with self.assertRaises(ForecastError):b.enter(1,300,now_ns=200)
        b=PartitionLedger(self.allocation(),'escrow',100)
        with self.assertRaisesRegex(ForecastError,'future-time-reserve'):
            b.enter(0,11*10**9,now_ns=10*10**9)
