# SPDX-License-Identifier: AGPL-3.0-only
"""Private operator/worker protocol. Transport does not establish native authority.

The root operator supplies boundary and child observers from outside the worker.
No default observer, listener, manager activation or authority from request data.
"""
from copy import deepcopy
import json
import socket
import struct
import sys
import threading
import time

from .forecast_admission import PHASES

from .forecast_data import digest, integer, require

MAX_PACKET = 64 * 1024
FIELDS = {
    'check': {'phase', 'deadlineNs', 'invocation'},
    'reserve': {'phase', 'deadlineNs', 'invocation'},
    'launched': {'ticket', 'pid'}, 'reaped': {'ticket', 'returncode'},
    'startFailed': {'ticket'}, 'transition': {'phase'}, 'complete': {'phase'},
}


class OperatorBridge:
    """Serialized external accounting, with independently verified child lifecycle.

    observe_child must retain a kernel identity on `launched` and confirm the same
    child has terminated on `reaped`. A missing/short-lived child is uncertainty,
    never permission to accept a producer's report. Neither callback may block
    beyond the external watchdog deadline. Native adapters remain a separate gate.
    """
    def __init__(self, session, *, binding, observe, observe_child, clock=time.monotonic_ns):
        self.clock = clock
        require(callable(observe) and callable(observe_child), 'operator-observers-required')
        self.session, self.binding = session, deepcopy(binding)
        self.binding_digest = digest(self.binding)
        self.observe, self.observe_child = observe, observe_child
        self.sequence, self.stopped = 0, False
        self.completed = False
        self.tickets = {}
        self.ambiguous = []
        self.lock = threading.Lock()

    def abort(self):
        if not self.stopped:
            self.stopped = True
            self.session._abort()

    def handle(self, packet):
        with self.lock:
            try:
                require(not self.stopped and not self.completed and not self.session.failed, 'operator-bridge-stopped')
                require(type(packet) is dict and packet.get('event') in FIELDS,
                        'operator-packet-event')
                event = packet['event']
                require(set(packet) == {'event','sequence','bindingDigest'} | FIELDS[event],
                        'operator-packet-fields')
                require(type(packet['sequence']) is int and packet['sequence'] == self.sequence+1
                        and packet['bindingDigest'] == self.binding_digest, 'operator-packet-binding')
                self.sequence += 1
                result = self._event(event, packet)
                return {'sequence':self.sequence, 'bindingDigest':self.binding_digest, **result}
            except BaseException:
                self.abort()
                raise

    def _event(self, event, p):
        if event in ('check', 'reserve'):
            timeline = self.session.timeline
            require(timeline.active and 0 <= timeline.index < 4
                    and p['phase'] == PHASES[timeline.index]
                    and type(p['deadlineNs']) is int
                    and self.clock() < min(p['deadlineNs'], timeline.phase_deadline_ns),
                    'operator-phase-deadline')
            observation = self.observe(deepcopy(self.binding), p['phase'], min(p['deadlineNs'], timeline.phase_deadline_ns),
                                       deepcopy(p['invocation']))
            require(type(observation) is dict and observation.get('bindingDigest') == self.binding_digest,
                    'operator-boundary-binding')
            if event == 'check':
                return {'observation': observation}
            require(type(p['invocation']) is dict and observation.get('launchAllowed') is True
                    and observation.get('launchDigest') == digest(p['invocation']),
                    'operator-launch-unverified')
            ticket = self.session.ledger.reserve()
            self.tickets[ticket] = {'pid':None, 'invocation':deepcopy(p['invocation'])}
            return {'ticket':ticket}
        if event == 'complete':
            require(not self.tickets and p['phase'] in ('dispatch','verify')
                    and p['phase'] == PHASES[self.session.timeline.index], 'operator-completion-state')
            self.completed = True
            return {'producerFinished':True, 'kernelClosureVerified':False}
        if event == 'transition':
            require(not self.tickets, 'operator-children-outstanding')
            self.session.transition(p['phase'])
            return {}
        token = integer(p['ticket'], 1)
        require(token in self.tickets, 'operator-ticket-unknown')
        if event == 'startFailed':
            require(self.tickets[token]['pid'] is None, 'operator-ticket-already-launched')
            # A producer's failed-Popen report cannot prove no exec occurred.
            # Keep the reservation outstanding and poison the entire flow.
            self.ambiguous.append({'ticket':token,'reason':'producer-start-failure-unverified'})
            require(False, 'operator-start-ambiguous')
        elif event == 'launched':
            require(self.tickets[token]['pid'] is None, 'operator-ticket-already-launched')
            pid = integer(p['pid'], 2)
            native = self.observe_child(pid, 'launched', deepcopy(self.tickets[token]['invocation']))
            require(type(native) is dict and native.get('identityVerified') is True,
                    'operator-child-identity-unverified')
            self.session.ledger.launched(token)
            self.tickets[token]['pid'] = pid
        else:
            require(self.tickets[token]['pid'] is not None and type(p['returncode']) is int,
                    'operator-child-not-launched')
            native = self.observe_child(self.tickets[token]['pid'], 'reaped',
                                        deepcopy(self.tickets[token]['invocation']))
            require(type(native) is dict and native.get('terminated') is True
                    and type(native.get('returncode')) is int
                    and native['returncode'] == p['returncode'], 'operator-child-exit-unverified')
            self.session.ledger.finished(token)
            del self.tickets[token]
        return {}


    def receipt(self):
        return {'version':'agent-braid-operator-bridge-receipt-v1',
                'bindingDigest':self.binding_digest, 'sequence':self.sequence,
                'requests':self.session.ledger.receipt(),
                'ambiguous':deepcopy(self.ambiguous), 'outstandingTickets':list(self.tickets),
                'producerFinished':self.completed, 'stopped':self.stopped,
                'kernelClosureVerified':False, 'actualProfileAdmitted':False,
                'executionAuthorization':False}


def peer(sock, *, uid, pid=None):
    """Kernel credentials of a connected Linux Unix socket, never payload fields."""
    require(sys.platform == 'linux' and sock.family == socket.AF_UNIX
            and sock.type == socket.SOCK_SEQPACKET, 'operator-linux-seqpacket-required')
    actual_pid, actual_uid, _ = struct.unpack('3i', sock.getsockopt(
        socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i')))
    require(actual_uid == uid and (pid is None or actual_pid == pid), 'operator-peer-mismatch')


def send(sock, packet):
    raw = json.dumps(packet, separators=(',', ':'), allow_nan=False).encode()
    require(len(raw) <= MAX_PACKET and sock.send(raw) == len(raw), 'operator-packet-output')


def receive(sock):
    raw, ancillary, flags, _ = sock.recvmsg(MAX_PACKET, 0)
    require(raw and not ancillary and not flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC),
            'operator-packet-truncated-or-eof')
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, 'operator-packet-duplicate-key')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: require(False, 'operator-nonfinite-json'))
    require(type(value) is dict, 'operator-packet-object')
    return value


def serve_one(sock, bridge, *, worker_uid, worker_pid):
    """One bounded request on an already accepted socket; never opens a listener.

    Owner must poll against the original deadline and abort on disconnect even
    when no request is outstanding. No connection/retry loop is supplied here.
    """
    try:
        peer(sock, uid=worker_uid, pid=worker_pid)
        require(sock.gettimeout() is not None and 0 < sock.gettimeout() <= 1,
                'operator-transport-timeout-required')
        send(sock, bridge.handle(receive(sock)))
    except BaseException:
        bridge.abort()
        raise


class WorkerBridge:
    """Trusted image code's single ordered channel; no authority-selector argument."""
    def __init__(self, sock, binding):
        peer(sock, uid=0)
        sock.settimeout(1)
        sock.set_inheritable(False)
        self.sock, self.binding_digest = sock, digest(binding)
        self.sequence, self.stopped = 0, False
        self.lock = threading.Lock()

    def call(self, event, **fields):
        with self.lock:
            try:
                require(not self.stopped, 'operator-channel-stopped')
                self.sequence += 1
                send(self.sock, dict(event=event, sequence=self.sequence,
                                    bindingDigest=self.binding_digest, **fields))
                result = receive(self.sock)
                require(result.get('sequence') == self.sequence and
                        result.get('bindingDigest') == self.binding_digest, 'operator-reply-binding')
                return result
            except BaseException:
                self.stopped = True
                self.sock.close()
                raise

    def verify(self, binding, phase, deadline, invocation=None):
        require(digest(binding) == self.binding_digest, 'operator-worker-binding-drift')
        return self.call('check', phase=phase, deadlineNs=deadline,
                         invocation=invocation)['observation']

    def lifecycle(self, event, **fields):
        return self.call(event, **fields)


def accept_binding(sock, session, *, worker_uid, worker_pid, bootstrap, validate_binding,
                   observe, observe_child):
    """Operator-only handshake on a connected socket, after native readback/gating.

    validate_binding compares *all* fields against trusted image/worker state,
    including the nonce, original origin, prior-work identity and exact limits.
    It must reject unsupported configuration; no default implementation exists.
    """
    try:
        peer(sock, uid=worker_uid, pid=worker_pid)
        sock.settimeout(1)
        sock.set_inheritable(False)
        send(sock, bootstrap)
        packet = receive(sock)
        if bootstrap['phase'] == 'terminal':
            require(packet == {'terminalIdentity':bootstrap['profileIdentity']}
                    and validate_binding(deepcopy(packet)) is True, 'operator-terminal-binding')
            send(sock, {'terminalAccepted':bootstrap['profileIdentity']})
            return None
        require(set(packet) == {'binding'}, 'operator-handshake-fields')
        binding = packet['binding']
        require(type(binding) is dict and binding.get('workerPid') == worker_pid
                and binding.get('externalLaunchLedger') is True
                and validate_binding(deepcopy(binding)) is True, 'operator-handshake-binding')
        bridge = OperatorBridge(session, binding=binding, observe=observe, observe_child=observe_child)
        send(sock, {'bindingDigest': bridge.binding_digest})
        return bridge
    except BaseException:
        session._abort()
        raise


def serve(sock, bridge, *, worker_uid, worker_pid):
    """Monitor one authenticated channel to completion, under the original clock.

    A completion message is only a request to inspect kernel closure. Owner must
    independently observe an empty cgroup before attaching the next worker.
    """
    import select
    try:
        peer(sock, uid=worker_uid, pid=worker_pid)
        sock.settimeout(1)
        sock.set_inheritable(False)
        while not bridge.completed:
            require(time.monotonic_ns() < bridge.session.timeline.phase_deadline_ns,
                    'operator-channel-deadline')
            ready, _, _ = select.select([sock], [], [], .05)
            if ready:
                serve_one(sock, bridge, worker_uid=worker_uid, worker_pid=worker_pid)
        return {'producerFinished':True, 'kernelClosureVerified':False}
    except BaseException:
        bridge.abort()
        raise
