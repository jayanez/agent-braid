# SPDX-License-Identifier: AGPL-3.0-only
"""Software protocol controls only; no native admission or selected input replay."""
from types import SimpleNamespace
import unittest
from agent_braid.forecast_admission import PhaseLedger, PHASES
from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_operator_bridge import OperatorBridge


class OperatorBridgeTests(unittest.TestCase):
    def setUp(self):
        self.ledger = PhaseLedger(bounds={p: 2 for p in PHASES}, total=8, max_active=1)
        self.ledger.enter('prepare')
        self.aborts = []
        self.session = SimpleNamespace(ledger=self.ledger, failed=False,
            timeline=SimpleNamespace(active=True,index=0,phase_deadline_ns=100),
            _abort=lambda: self.aborts.append(True))
        self.binding = {'workerPid': 10}
        self.native = []
        self.bridge = OperatorBridge(self.session, binding=self.binding,
            observe=lambda b,p,d,i: {'bindingDigest': digest(b), 'launchAllowed':True, 'launchDigest':digest(i)},
            observe_child=self.child, clock=lambda:0)
        self.seq = 0

    def child(self, pid, event, invocation):
        self.native.append((pid,event))
        return {'identityVerified':True, 'terminated':True, 'returncode':0}

    def call(self, event, **payload):
        self.seq += 1
        if event == 'reserve':
            payload.update(phase='prepare', deadlineNs=100)
        return self.bridge.handle({'sequence': self.seq, 'bindingDigest': digest(self.binding),
                                   'event': event, **payload})

    def test_external_reservation_precedes_launch_and_native_reap(self):
        ticket = self.call('reserve', invocation={'argv':['git']})['ticket']
        self.assertEqual(self.ledger.receipt()['outstandingReservations'], 1)
        self.call('launched', ticket=ticket, pid=20)
        self.call('reaped', ticket=ticket, returncode=0)
        self.assertEqual(self.native, [(20,'launched'), (20,'reaped')])
        self.assertEqual(self.ledger.receipt()['phases']['prepare']['finished'], 1)

    def test_replayed_packet_aborts_and_cannot_resume(self):
        self.call('reserve', invocation={})
        packet = {'sequence':self.seq, 'bindingDigest':digest(self.binding), 'event':'check'}
        with self.assertRaises(ForecastError):
            self.bridge.handle(packet)
        with self.assertRaises(ForecastError):
            self.call('reserve', invocation={})
        self.assertTrue(self.aborts)

    def test_failed_native_observation_keeps_reservation_and_aborts(self):
        ticket = self.call('reserve', invocation={})['ticket']
        self.bridge.observe_child = lambda *args: (_ for _ in ()).throw(ValueError('unverified'))
        with self.assertRaises(ValueError):
            self.call('launched', ticket=ticket, pid=20)
        self.assertEqual(self.ledger.receipt()['outstandingReservations'], 1)
        self.assertTrue(self.aborts)

    def test_start_failure_is_retained_and_poisoned(self):
        ticket = self.call('reserve', invocation={})['ticket']
        with self.assertRaisesRegex(ForecastError,'operator-start-ambiguous'):
            self.call('startFailed', ticket=ticket)
        self.assertEqual(self.ledger.receipt()['phases']['prepare']['startFailed'], 0)
        self.assertEqual(self.ledger.receipt()['outstandingReservations'], 1)
        self.assertEqual(self.bridge.receipt()['ambiguous'][0]['ticket'], ticket)
        with self.assertRaises(ForecastError):
            self.call('reserve', invocation={})

    def test_worker_cannot_select_binding_or_extra_authority_fields(self):
        with self.assertRaises(ForecastError):
            self.call('reserve', invocation={}, containedProcessTree=True)
        self.assertTrue(self.aborts)

    def test_wrong_phase_cannot_charge_current_phase_reserve(self):
        with self.assertRaises(ForecastError):
            self.bridge.handle(dict(event='reserve', sequence=1, bindingDigest=digest(self.binding),
                phase='verify', deadlineNs=100, invocation={}))
        self.assertEqual(self.ledger.receipt()['phases']['prepare']['accepted'], 0)

    def test_worker_exit_code_does_not_override_independent_observation(self):
        ticket = self.call('reserve', invocation={})['ticket']
        self.call('launched', ticket=ticket, pid=20)
        with self.assertRaises(ForecastError):
            self.call('reaped', ticket=ticket, returncode=1)
        self.assertEqual(self.ledger.receipt()['outstandingReservations'], 1)
        self.assertEqual(self.aborts, [True])
        self.bridge.abort()
        self.assertEqual(self.aborts, [True])

    def test_complete_message_never_establishes_kernel_closure(self):
        self.session.timeline.index = 2
        result = self.call('complete', phase='dispatch')
        self.assertTrue(result['producerFinished'])
        self.assertFalse(result['kernelClosureVerified'])
        self.assertTrue(self.bridge.completed)


class TransportTests(unittest.TestCase):
    def test_kernel_peer_credentials_not_packet_claims(self):
        import socket
        import struct
        from unittest.mock import MagicMock, patch
        from agent_braid.forecast_operator_bridge import peer
        sock = MagicMock(family=socket.AF_UNIX,type=socket.SOCK_SEQPACKET)
        sock.getsockopt.return_value = struct.pack('3i',10,61000,61000)
        with patch('agent_braid.forecast_operator_bridge.sys.platform','linux'), \
             patch.object(socket,'SO_PEERCRED',17,create=True):
            peer(sock,uid=61000,pid=10)
            with self.assertRaises(ForecastError):
                peer(sock,uid=0)
            with self.assertRaises(ForecastError):
                peer(sock,uid=61000,pid=11)

    def test_duplicate_keys_truncated_packets_and_eof_refuse(self):
        import socket
        from unittest.mock import MagicMock
        from agent_braid.forecast_operator_bridge import receive
        for raw, flags in [(b'{"sequence":1,"sequence":2}',0),
                           (b'{}',socket.MSG_TRUNC), (b'',0), (b'{"x":NaN}',0)]:
            sock = MagicMock()
            sock.recvmsg.return_value = (raw,[],flags,None)
            with self.subTest(raw=raw), self.assertRaises(ForecastError):
                receive(sock)
