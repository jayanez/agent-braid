# SPDX-License-Identifier: AGPL-3.0-only
"""New protocol/accounting cases; fake transport only, no native socket or model."""
import array
import socket
import struct
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_exec_budget import ExecAllocation, ROLE_PHASE
from agent_braid.forecast_manager_escrow import (GateBinding,ManagerEscrowState,ProcessFacts,
    REQUEST,REPLY,MAGIC,decode_request,receive_kernel_frame,RootManagerEscrow)


def binding():
    return GateBinding('a'*64,'b'*64,'c'*64,100,61001,
                       ExecAllocation('a'*64,(2,1,1,1,0),(10,)*5))


def frame(b,role=0,site=0,invocation='d'*32):
    return REQUEST.pack(MAGIC,1,site,0,b.unit(role).encode(),invocation.encode()+b'\0',b'\0'*7)


def facts(b,role,site):
    return ProcessFacts(1,0,0,0,100,b.manager_sha256,'/') if site==0 else ProcessFacts(
        99,0 if role<3 else b.worker_uid,0 if role<3 else b.worker_uid,1,101,
        b.executor_sha256,b.cgroup(role))


def complete_role(s,role,now):
    for site in (0,1):
        ticket,raw=s.reserve((role,site,'d'*32),facts(s.binding,role,site),now_ns=now)
        s.delivered(ticket,sent=True)
        assert REPLY.unpack(raw)[-1]<=s.ledger.whole_deadline


class EscrowTests(unittest.TestCase):
    def test_two_sites_six_roles_and_owner_consume_exact_disjoint_reserves(self):
        s=ManagerEscrowState(binding(),100);s.begin(77,now_ns=101)
        for role in range(4):complete_role(s,role,102+role)
        for phase in (1,2,3):s.advance(phase,now_ns=110+phase)
        complete_role(s,4,120);s.advance(4,now_ns=121);complete_role(s,5,122)
        self.assertEqual([sum(r['phase']==i for r in s.ledger.records) for i in range(5)],[9,0,0,2,2])
        self.assertEqual(s.completed,list(range(6)))
        self.assertFalse(s.receipt()['targetExecSuccessVerified'])

    def test_wrong_uid_cgroup_manager_start_and_site_order_fail_closed(self):
        for field,value in (('uid',0),('cgroup','/wrong'),('ppid',9)):
            b=binding();s=ManagerEscrowState(b,100);s.begin(77,now_ns=101)
            for role in range(3):complete_role(s,role,102)
            ticket,_=s.reserve((3,0,'d'*32),facts(b,3,0),now_ns=103);s.delivered(ticket,sent=True)
            f=facts(b,3,1);f=ProcessFacts(**{**f.__dict__,field:value})
            with self.subTest(field=field),self.assertRaises(ForecastError):
                s.reserve((3,1,'d'*32),f,now_ns=104)
            self.assertTrue(s.failed)
        b=binding();s=ManagerEscrowState(b,100);s.begin(77,now_ns=101)
        with self.assertRaises(ForecastError):s.reserve((0,1,'d'*32),facts(b,0,1),now_ns=102)
        s=ManagerEscrowState(b,100);s.begin(77,now_ns=101)
        f=facts(b,0,0);f=ProcessFacts(**{**f.__dict__,'start_ticks':101})
        with self.assertRaises(ForecastError):s.reserve((0,0,'d'*32),f,now_ns=102)

    def test_unknown_send_is_consumed_and_cannot_retry_or_rearm(self):
        s=ManagerEscrowState(binding(),100);s.begin(77,now_ns=101)
        ticket,_=s.reserve((0,0,'d'*32),facts(s.binding,0,0),now_ns=102)
        with self.assertRaises(ForecastError):s.delivered(ticket,sent=False)
        self.assertEqual(s.ledger.records[-1]['state'],'indeterminate-consumed')
        with self.assertRaises(ForecastError):s.begin(77,now_ns=103)
        self.assertEqual(s.origin_ns,100)

    def test_expired_phase_cannot_reset_clock_and_invocation_is_bound(self):
        s=ManagerEscrowState(binding(),100);s.begin(77,now_ns=101)
        for role in range(4):complete_role(s,role,102)
        with self.assertRaisesRegex(ForecastError,'phase-expired'):
            s.advance(1,now_ns=s.ledger.deadline)
        s=ManagerEscrowState(binding(),100);s.begin(77,now_ns=101)
        ticket,_=s.reserve((0,0,'d'*32),facts(s.binding,0,0),now_ns=102);s.delivered(ticket,sent=True)
        with self.assertRaises(ForecastError):s.reserve((0,1,'e'*32),facts(s.binding,0,1),now_ns=103)

    def test_abi_and_padding_reject_oversize_and_foreign_unit(self):
        b=binding();self.assertEqual((REQUEST.size,REPLY.size),(152,32))
        self.assertEqual(decode_request(frame(b),b),(0,0,'d'*32))
        for raw in (frame(b)+b'x',frame(b)[:-1]+b'x',frame(binding()).replace(b'fc1a',b'fc1z')):
            with self.assertRaises(ForecastError):decode_request(raw,b)

    def test_per_message_credentials_reject_duplicates_and_close_all_rights(self):
        class Fake:
            def __init__(self,anc):self.anc=anc
            def recvmsg(self,*args):return b'x',self.anc,0,None
        credentials=struct.pack('=iii',1,0,0)
        with patch.object(socket,'SCM_CREDENTIALS',2,create=True):
            item=(socket.SOL_SOCKET,2,credentials)
            self.assertEqual(receive_kernel_frame(Fake([item])),(b'x',(1,0,0)))
            with self.assertRaises(ForecastError):receive_kernel_frame(Fake([item,item]))
            rights=array.array('i',[501,502]).tobytes()
            with patch('agent_braid.forecast_manager_escrow.os.close',side_effect=[OSError(),None]) as close:
                with self.assertRaises(ForecastError):receive_kernel_frame(Fake([item,(socket.SOL_SOCKET,socket.SCM_RIGHTS,rights)]))
                self.assertEqual(close.call_count,2)

    def test_proc_task_state_change_is_allowed_but_pid_reuse_is_not(self):
        b=binding();adapter=object.__new__(RootManagerEscrow)
        adapter.state=ManagerEscrowState(b,100)
        class View:
            def read(self,path):
                if path.endswith('status'):return b'Uid: 0 0 0 0\nGid: 0 0 0 0\n'
                if path.endswith('cgroup'):return b'0::/\n'
                return b'not parsed by fake'
            def hash_file(self,*args):return b.manager_sha256
        adapter.view=View();before={'pid':1,'ppid':0,'start':100,'state':'S','exitStatus':0}
        after={**before,'state':'R'}
        with patch('agent_braid.forecast_manager_escrow.proc_stat',side_effect=[before,after]):
            self.assertEqual(adapter._facts((0,0,'d'*32),(1,0,0)).start_ticks,100)
        with patch('agent_braid.forecast_manager_escrow.proc_stat',side_effect=[before,{**after,'start':101}]):
            with self.assertRaises(ForecastError):adapter._facts((0,0,'d'*32),(1,0,0))

    def test_whole_transport_is_serialized_and_late_send_consumes_uncertain_permit(self):
        from threading import RLock
        b=binding();s=ManagerEscrowState(b,100);s.begin(77,now_ns=101)
        class TracedLock:
            def __init__(self):self.inner=RLock();self.depth=0
            def __enter__(self):self.inner.acquire();self.depth+=1;return self
            def __exit__(self,*args):self.depth-=1;self.inner.release()
        s.lock=TracedLock()
        adapter=object.__new__(RootManagerEscrow);adapter.profile=object();adapter.state=s
        class View:
            def guard(self):pass
            def account(self,count):pass
        class Connection:
            closed=False
            def setsockopt(self,*args):pass
            def settimeout(self,value):self.timeout=value
            def send(self,data):
                if s.lock.depth<1:raise AssertionError('transport not serialized')
                return len(data)
            def close(self):self.closed=True
        channel=Connection();adapter.view=View()
        adapter.clock=iter((102,103,104,s.ledger.deadline)).__next__
        with patch.object(socket,'SO_PASSCRED',16,create=True),\
             patch('agent_braid.forecast_manager_escrow.bootstrap_ready'),\
             patch('agent_braid.forecast_manager_escrow.receive_kernel_frame',return_value=(frame(b),(1,0,0))),\
             patch.object(adapter,'_facts',return_value=facts(b,0,0)):
            with self.assertRaisesRegex(ForecastError,'late-reply'):adapter.serve_connection(channel)
        self.assertTrue(channel.closed and s.failed)
        self.assertIsNone(s.pending);self.assertEqual(s.completed,[])
        self.assertEqual(s.ledger.records[-1]['state'],'indeterminate-consumed')
        self.assertEqual(s.lock.depth,0)

    def test_close_revokes_under_transaction_lock_before_withdrawing_listener(self):
        from threading import RLock
        s=ManagerEscrowState(binding(),100);s.begin(77,now_ns=101)
        class TracedLock:
            def __init__(self):self.lock=RLock();self.depth=0
            def __enter__(self):self.lock.acquire();self.depth+=1
            def __exit__(self,*args):self.depth-=1;self.lock.release()
        s.lock=TracedLock();adapter=object.__new__(RootManagerEscrow)
        adapter.state=s;adapter.closed=False;adapter.socket_identity=None;adapter.cleanup_uncertain=False
        observations=[]
        class Listener:
            def close(self):observations.append((s.failed,s.lock.depth))
        adapter.channel=Listener();adapter.close()
        self.assertTrue(adapter.closed and s.failed)
        self.assertEqual(observations,[(True,1)])
        self.assertIsNone(adapter.channel);adapter.close();self.assertEqual(len(observations),1)
