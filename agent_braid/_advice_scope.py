# SPDX-License-Identifier: AGPL-3.0-only
"""Private transport ownership scopes; same-process engineering controls only."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import threading
from time import monotonic_ns
from typing import Callable

from .system_one import CancellationToken, canonical, parse_json, HASH


class InvalidAdviceScope(ValueError):
    def __init__(self):
        super().__init__('invalid-scope')


@dataclass(frozen=True, eq=False)
class _Ingress:
    owner: object
    started_ns: int


@dataclass(frozen=True, eq=False)
class _TransportCallScope:
    owner: object
    request_id: tuple
    request_bytes: bytes
    request_digest: str
    expected_context_digest: str | None
    expected_registry_digest: str | None
    cancellation: CancellationToken
    ingress_started_ns: int
    deadline_ns: int
    stage: bool


@dataclass(frozen=True)
class _StageExecutionView:
    request_bytes: bytes
    request_digest: str
    expected_context_digest: str
    expected_registry_digest: str
    cancellation: CancellationToken
    ingress_started_ns: int
    deadline_ns: int
    clock: Callable[[], int]


class _TransportScopeRegistry:
    """Only transport admission constructs live scopes; never accepts timestamps.

    Clock replacement is private deterministic test instrumentation. Lock order is
    output -> token -> registry; no registry lock is held while acquiring a token.
    """
    def __init__(self, *, clock=monotonic_ns):
        self._clock = clock
        self._lock = threading.RLock()
        self._ingresses = set()
        self._records = {}
        self._ids = {}
        self._closed = False

    def begin_ingress(self):
        ticket = _Ingress(self, self._clock())
        with self._lock:
            if self._closed:
                raise InvalidAdviceScope()
            self._ingresses.add(ticket)
        return ticket

    def discard_ingress(self, ticket):
        with self._lock:
            self._ingresses.discard(ticket)

    def admit(self, ticket, identifier, request_bytes, *, expected_context_digest=None,
              expected_registry_digest=None, stage=True):
        # Parse only materialized bounded bytes. No timestamp or token parameter.
        if type(identifier) not in (str, int) or type(request_bytes) is not bytes or type(stage) is not bool:
            raise InvalidAdviceScope()
        try:
            value = parse_json(request_bytes)
            raw = canonical(value)
            budgets = value.get('budgets') if stage else None
            ceiling = budgets.get('deadlineMs') if type(budgets) is dict else (5000 if not stage else None)
        except (ValueError,TypeError,OverflowError):
            raise InvalidAdviceScope() from None
        if type(ceiling) is not int or not 1 <= ceiling <= 5000:
            raise InvalidAdviceScope()
        if stage and any(type(pin) is not str or not HASH.fullmatch(pin)
                         for pin in (expected_context_digest, expected_registry_digest)):
            raise InvalidAdviceScope()
        token = CancellationToken()
        token.claim()
        registered = False
        try:
            with self._lock:
                now = self._clock()
                key = (type(identifier), identifier)
                if (type(ticket) is not _Ingress or ticket.owner is not self
                        or ticket not in self._ingresses or self._closed
                        or type(ticket.started_ns) is not int or ticket.started_ns > now
                        or key in self._ids):
                    raise InvalidAdviceScope()
                self._ingresses.remove(ticket)
                scope = _TransportCallScope(self, key, raw, sha256(raw).hexdigest(),
                    expected_context_digest, expected_registry_digest, token,
                    ticket.started_ns, ticket.started_ns + min(5000, ceiling) * 1_000_000,
                    stage)
                # Snapshot tuple prevents dataclass/object mutation bypassing registry pins.
                self._records[scope] = [self._snapshot(scope), 'active']
                self._ids[key] = scope
                registered = True
            return scope
        finally:
            if not registered:
                token.release()

    @staticmethod
    def _snapshot(scope):
        return (scope.owner, scope.request_id, scope.request_bytes, scope.request_digest,
                scope.expected_context_digest, scope.expected_registry_digest,
                scope.cancellation, scope.ingress_started_ns, scope.deadline_ns, scope.stage)

    def _valid_locked(self, scope, *, publishing=False):
        record = self._records.get(scope)
        if (type(scope) is not _TransportCallScope or scope.owner is not self or record is None
                or record[0] != self._snapshot(scope)
                or record[1] not in ({'active', 'publishing'} if publishing else {'active'})
                or self._ids.get(scope.request_id) is not scope or self._closed
                or type(scope.cancellation) is not CancellationToken
                or not scope.cancellation._in_use
                or sha256(scope.request_bytes).hexdigest() != scope.request_digest
                or type(scope.ingress_started_ns) is not int
                or type(scope.deadline_ns) is not int
                or scope.ingress_started_ns > self._clock()
                or not scope.ingress_started_ns < scope.deadline_ns
                <= scope.ingress_started_ns + 5_000_000_000):
            raise InvalidAdviceScope()
        if scope.stage:
            original = parse_json(scope.request_bytes)
            ceiling = original['budgets']['deadlineMs']
            if scope.deadline_ns != scope.ingress_started_ns + ceiling * 1_000_000:
                raise InvalidAdviceScope()
        return record

    def active_identifier(self, identifier):
        with self._lock:
            return (type(identifier), identifier) in self._ids

    def cancel(self, identifier):
        with self._lock:
            scope = self._ids.get((type(identifier), identifier))
        if scope is not None:
            scope.cancellation.cancel()

    def complete(self, scope):
        # Idempotence uses exact registered identity; forged copies cannot release.
        with self._lock:
            record = self._records.get(scope)
            if record is None or type(scope) is not _TransportCallScope or record[0] != self._snapshot(scope):
                return False
            del self._records[scope]
            if self._ids.get(scope.request_id) is scope:
                del self._ids[scope.request_id]
        scope.cancellation.release()
        return True

    def close(self):
        with self._lock:
            self._closed = True
            tokens = [scope.cancellation for scope in self._records]
            self._ingresses.clear()
        for token in tokens:
            token.cancel()

    def publish(self, scope, write):
        """Called with transport output lock; one atomic write-begin transition.

        ``write`` is a private transport-owned writer, never a supplied scope method.
        Blocking writes have no hard termination guarantee.
        """
        def begin(cancelled):
            with self._lock:
                try:
                    record = self._valid_locked(scope)
                except InvalidAdviceScope:
                    return False
                if cancelled or self._clock() >= scope.deadline_ns:
                    return False
                record[1] = 'publishing'
            write()
            return True
        try:
            if _owner(scope) is not self:
                return False
            with self._lock:
                self._valid_locked(scope)
                token = scope.cancellation
        except InvalidAdviceScope:
            return False
        return token.publish(begin)


def _owner(scope):
    if type(scope) is not _TransportCallScope or type(scope.owner) is not _TransportScopeRegistry:
        raise InvalidAdviceScope()
    return scope.owner


def validate_for_stage(scope):
    owner = _owner(scope)
    with owner._lock:
        owner._valid_locked(scope)
        if not scope.stage:
            raise InvalidAdviceScope()
        return _StageExecutionView(scope.request_bytes, scope.request_digest,
            scope.expected_context_digest, scope.expected_registry_digest,
            scope.cancellation, scope.ingress_started_ns, scope.deadline_ns, owner._clock)


def _scope_checkpoint(scope):
    try:
        owner = _owner(scope)
        with owner._lock:
            owner._valid_locked(scope)
            token = scope.cancellation
            deadline = scope.deadline_ns
        if token.cancelled:
            return 'cancelled'
        if owner._clock() >= deadline:
            return 'deadline-exceeded'
        return 'live'
    except (InvalidAdviceScope, KeyError, TypeError, ValueError):
        return 'invalid-scope'
