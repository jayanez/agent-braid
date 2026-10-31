# SPDX-License-Identifier: AGPL-3.0-only
"""Offline census ABI/ledger controls; no BPF syscall, native task or workload."""
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock
import struct
from agent_braid.forecast_exec_census import CensusLedger,KernelCensus,EVENT,decode_event
from agent_braid.forecast_data import ForecastError


def event(seq,pid,kind=2): return EVENT.pack(seq,100+seq,77,88,pid,pid,kind,0)


class CensusTests(unittest.TestCase):
    def ledger(self): return CensusLedger(SimpleNamespace(limits=[SimpleNamespace(requests=1)]*4+
                                                       [SimpleNamespace(requests=0)]),100)

    def test_each_exec_counts_even_same_pid_and_unknown_is_retained(self):
        ledger=self.ledger()
        row=ledger.reconcile([event(1,10),event(2,20),event(3,20)],cgroup=77,phase=0,
                             deadline_ns=200,known=[(10,'worker'),(20,'git')])
        self.assertEqual((row['execs'],row['auxiliaryOrUnclassified']),(3,1))
        self.assertFalse(row['nativeCoverageAccepted'])
        with self.assertRaisesRegex(ForecastError,'auxiliary-cap'):
            self.ledger().reconcile([event(i,20) for i in range(1,4)],cgroup=77,phase=0,
                                   deadline_ns=200,known=[(20,'git')])

    def test_missing_known_sequence_identity_time_and_later_phase_reserve_refuse(self):
        cases=[([event(2,10)],[(10,'git')],0,200,'record-binding'),
               ([event(1,10)],[(20,'git')],0,200,'missing-known'),
               ([event(1,10)],[(10,'git')],0,101,'time-boundary'),
               ([event(1,10)],[(10,'git')],1,200,'phase-or-capacity'),
               ([event(1,10),event(2,20)],[(10,'git'),(20,'git')],0,200,'known-cap')]
        for rows,known,phase,deadline,reason in cases:
            with self.subTest(reason=reason),self.assertRaisesRegex(ForecastError,reason):
                self.ledger().reconcile(rows,cgroup=77,phase=phase,deadline_ns=deadline,known=known)

    def test_journal_inflight_rewind_and_changing_boundary_refuse(self):
        census=object.__new__(KernelCensus);census._lookup=MagicMock(return_value=event(1,10))
        for states,cursor,reason in [([(1,0)],0,'inflight'), ([(1,1)],2,'rewind'),
                                      ([(1,1),(2,2)],0,'changing-boundary')]:
            census.check_live=MagicMock(side_effect=states)
            with self.subTest(reason=reason),self.assertRaisesRegex(ForecastError,reason):
                census.snapshot(cursor,frozen=MagicMock())

    def test_loss_capacity_and_config_drift_never_accept(self):
        census=object.__new__(KernelCensus);census.qualified=True;census.cgroup=77
        census.profile=SimpleNamespace(identity='a'*64)
        census.fds={name+'_program':i for i,name in enumerate(('fork','exec','exit'))}
        census._info=MagicMock(return_value=bytes(256))
        cfg=struct.pack('<QQIIQ',77,int('a'*16,16),1,0,1)
        for state in ((1,1,1,0),(65537,65537,0,0),(1,2,0,0)):
            census._lookup=MagicMock(side_effect=[cfg,struct.pack('<QQQQ',*state)])
            with self.assertRaisesRegex(ForecastError,'loss-or-overflow'): census.check_live()
        census._lookup=MagicMock(return_value=struct.pack('<QQIIQ',77,1,1,0,0))
        with self.assertRaisesRegex(ForecastError,'config-drift'): census.check_live()

    def test_wrong_sized_record_refuses(self):
        with self.assertRaisesRegex(ForecastError,'record-size'): decode_event(b'',1,77)

    def test_census_alone_cannot_release_native_worker(self):
        from agent_braid.forecast_native import NativeBoundary
        provider=object.__new__(NativeBoundary)
        provider.profile=MagicMock()
        provider.profile.manifest.return_value={'execAdmissionEnforced':False}
        provider.view=MagicMock()
        with self.assertRaisesRegex(ForecastError,'pre-exec-admission-unimplemented'):
            provider.qualify()
        provider.view.guard.assert_not_called()

    def test_closed_phase_cannot_be_reclassified_or_lend_helper_reserve(self):
        ledger=self.ledger()
        ledger.reconcile([event(1,10)],cgroup=77,phase=0,deadline_ns=200)
        with self.assertRaisesRegex(ForecastError,'missing-known'):
            ledger.reconcile([],cgroup=77,phase=1,deadline_ns=300,known=[(10,'git')])
        self.assertEqual(ledger.rows[0]['auxiliaryOrUnclassified'],1)
        with self.assertRaisesRegex(ForecastError,'auxiliary-cap'):
            ledger.reconcile([event(2,20),event(3,30)],cgroup=77,phase=1,deadline_ns=300)
