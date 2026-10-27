# SPDX-License-Identifier: AGPL-3.0-only
"""Pure filter/permit controls and mocked ioctl sequencing; no seccomp activation."""
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock,patch
from agent_braid.forecast_exec_gate import (
    ARCH,NOTIF,RESP,RECV,SEND,VALID,ExecPermitLedger,NativeExecBroker,filter_bytes,
)
from agent_braid.forecast_data import ForecastError


def evaluate(nr,arch=ARCH):
    rows=list(struct.iter_unpack('<HBBI',filter_bytes()));pc=0;value=0
    for _ in range(32):
        code,jt,jf,k=rows[pc]
        if code==0x20:value={0:nr,4:arch}[k];pc+=1
        elif code==0x15:pc+=1+(jt if value==k else jf)
        elif code==0x06:return k
        else:raise AssertionError(code)
    raise AssertionError('unterminated filter')


class GateTests(unittest.TestCase):
    def ledger(self):
        return ExecPermitLedger(SimpleNamespace(identity='a'*64,
            limits=[SimpleNamespace(requests=1,wall_seconds=10)]*4+[SimpleNamespace(requests=0,wall_seconds=10)]),100)

    def test_both_exec_syscalls_notify_wrong_arch_kills_and_filter_stacking_denies(self):
        for nr in (221,281):self.assertEqual(evaluate(nr),0x7fc00000)
        for nr in (277,167):self.assertEqual(evaluate(nr),0x00050001)
        self.assertEqual(evaluate(172),0x7fff0000)
        self.assertEqual(evaluate(221,0xc000003e),0x80000000)

    def test_reserve_is_consumed_on_ambiguity_no_retry_or_refund(self):
        ledger=self.ledger();ledger.enter(0,200,now_ns=100)
        ticket=ledger.reserve(5,1,44,now_ns=101)
        ledger.finish(ticket,continued=False)
        self.assertEqual(ledger.receipt()['attemptsConsumed'],1)
        with self.assertRaises(ForecastError):ledger.reserve(5,2,44,now_ns=102)
        self.assertEqual(ledger.records[0]['status'],'indeterminate-consumed')

    def test_phase_cannot_borrow_future_quota_and_worker_start_has_separate_reserve(self):
        ledger=self.ledger();ledger.enter(0,200,now_ns=100)
        for i in range(5):
            token=ledger.reserve(5,i,44,now_ns=101);ledger.finish(token,continued=True)
        worker=ledger.reserve(6,1,45,now_ns=101,worker_entry=True);ledger.finish(worker,continued=True)
        with self.assertRaisesRegex(ForecastError,'quota-exhausted'):
            ledger.reserve(5,6,44,now_ns=102)
        self.assertEqual(ledger.denied,1)

    def test_outstanding_notification_replay_and_deadline_refuse(self):
        ledger=self.ledger();ledger.enter(0,200,now_ns=100)
        ticket=ledger.reserve(5,1,44,now_ns=101)
        with self.assertRaisesRegex(ForecastError,'outstanding'):ledger.enter(1,300,now_ns=150)
        ledger.finish(ticket,continued=True)
        with self.assertRaisesRegex(ForecastError,'replayed'):ledger.reserve(5,1,44,now_ns=102)
        with self.assertRaisesRegex(ForecastError,'deadline'):ledger.reserve(5,2,44,now_ns=200)

    def broker(self):
        ledger=self.ledger();ledger.enter(0,200,now_ns=100)
        broker=NativeExecBroker(ledger,validate_task=lambda pid,identity:pid==44,clock=lambda:101)
        broker._listeners={'token':{'fd':5,'identity':'owned-root-binding','phase':0}}
        return broker

    def test_ioctl_continuation_follows_write_ahead_reservation(self):
        broker=self.broker();seen=[]
        def ioctl(fd,op,arg,*unused):
            if op==RECV:arg[:]=NOTIF.pack(9,44,0,221,ARCH,*([0]*7))
            if op==SEND:
                seen.append(RESP.unpack(arg))
                self.assertEqual(broker._ledger.records[0]['status'],'reserved')
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.select.select',return_value=([5],[],[])), \
             patch('agent_braid.forecast_exec_gate.fcntl.ioctl',side_effect=ioctl):
            broker.serve_one('token')
        self.assertEqual(seen,[(9,0,0,1)])
        self.assertEqual(broker._ledger.records[0]['status'],'continued-not-launch-proof')

    def test_stale_id_after_reservation_consumes_and_closes_all_listeners(self):
        broker=self.broker();valid=0
        def ioctl(fd,op,arg,*unused):
            nonlocal valid
            if op==RECV:arg[:]=NOTIF.pack(9,44,0,281,ARCH,*([0]*7))
            if op==VALID:
                valid+=1
                if valid==2:raise ProcessLookupError()
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.select.select',return_value=([5],[],[])), \
             patch('agent_braid.forecast_exec_gate.fcntl.ioctl',side_effect=ioctl), \
             patch('agent_braid.forecast_exec_gate.os.close') as close:
            with self.assertRaises(ProcessLookupError):broker.serve_one('token')
        close.assert_called_once_with(5)
        self.assertTrue(broker._ledger.failed)
        self.assertEqual(broker._ledger.records[0]['status'],'indeterminate-consumed')

    def test_invalid_listener_authority_never_registers(self):
        broker=self.broker();broker._listeners={}
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.fcntl.fcntl',return_value=99), \
             patch('agent_braid.forecast_exec_gate.os.close') as closed:
            with self.assertRaisesRegex(ForecastError,'listener-unverified'):
                broker.register(5,identity='untrusted-worker',verify_listener=lambda *a:False)
        self.assertEqual(broker._listeners,{})
        closed.assert_called_once_with(99)

    def test_verified_owned_duplicate_survives_callers_fd_reuse(self):
        broker=self.broker();broker._listeners={};verify=MagicMock(return_value=True)
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.fcntl.fcntl',return_value=99):
            owned=broker.register(5,identity='root-pinned',verify_listener=verify)
        self.assertIsInstance(owned,str);self.assertNotIn(5,broker._listeners)
        self.assertEqual(broker._listeners[owned]['identity'],'root-pinned')
        self.assertEqual(verify.call_args.args[0],99)

    def test_pending_notification_and_direct_ledger_phase_advance_refuse(self):
        broker=self.broker()
        with self.assertRaisesRegex(ForecastError,'transition-owner'):
            broker._ledger.enter(1,300,now_ns=150)
        with self.assertRaises(TypeError):
            broker._ledger.enter(1,300,now_ns=150,_owner=broker)
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.select.select',return_value=([5],[],[])), \
             patch('agent_braid.forecast_exec_gate.os.close'):
            with self.assertRaisesRegex(ForecastError,'pending-at-transition'):
                broker.transition(1,300,verify_quiescent=lambda:True)
        self.assertTrue(broker.closed)

    def test_poll_notification_cannot_move_into_a_new_phase(self):
        broker=self.broker()
        def changed(*args):
            broker._ledger.phase=1
            return ([5],[],[])
        with patch.object(broker,'guard'),patch('agent_braid.forecast_exec_gate.select.select',side_effect=changed), \
             patch('agent_braid.forecast_exec_gate.fcntl.ioctl') as ioctl, \
             patch('agent_braid.forecast_exec_gate.os.close'):
            with self.assertRaisesRegex(ForecastError,'stale-phase'):broker.serve_one('token')
        ioctl.assert_not_called()
        self.assertEqual(broker._ledger.records,[])

    def test_another_reader_cannot_leave_recv_blocked_after_poll(self):
        broker=self.broker()
        with patch.object(broker,'guard'), \
             patch('agent_braid.forecast_exec_gate.select.select',side_effect=[([5],[],[]),([],[],[])]), \
             patch('agent_braid.forecast_exec_gate.fcntl.ioctl') as ioctl:
            self.assertFalse(broker.serve_one('token'))
        ioctl.assert_not_called()

    def test_phase_deadline_cannot_extend_original_budget(self):
        ledger=self.ledger()
        with self.assertRaisesRegex(ForecastError,'exec-gate-phase'):
            ledger.enter(0,ledger.whole_deadline+1,now_ns=100)
        with self.assertRaisesRegex(ForecastError,'exec-gate-phase'):
            ledger.enter(0,11*10**9+100,now_ns=100)
