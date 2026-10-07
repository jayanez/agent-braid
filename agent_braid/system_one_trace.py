# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit pull-only bounded stage metadata; never exports private contents."""
from __future__ import annotations

import math
import threading
from time import monotonic_ns

from .system_one import CancellationToken, canonical, freeze, thaw

COST_KEYS = {'adviceMs','fallbackMs','verifierMs','runtimeMs','totalMs'}
FALLBACKS = {'kept-original-order','used-existing-consumer','not-observed','none-needed'}


class StageObservationBuffer:
    def __init__(self, capacity=64, *, _clock=monotonic_ns):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError('invalid-capacity')
        self._capacity = capacity
        self._clock = _clock
        self._lock = threading.Lock()
        self._records = []
        self._dropped = 0

    @staticmethod
    def _result(status, reason=None):
        return freeze({'status':status,'reasonCodes':[] if reason is None else [reason]})

    def record(self, packet_bytes, *, request_bytes, expected_context_digest,
               expected_registry_digest, cost, fallback='not-observed', cancellation=None):
        start = self._clock()
        token = CancellationToken() if cancellation is None else cancellation
        if type(token) is not CancellationToken:
            return self._result('refused','invalid-observation')
        if not self._lock.acquire(blocking=False):
            return self._result('busy','busy')
        self._lock.release()
        try:
            from .system_one_advisors import validate_stage_packet
            if type(packet_bytes) is not bytes or (request_bytes is not None and type(request_bytes) is not bytes):
                raise ValueError()
            packet = validate_stage_packet(packet_bytes, request_bytes=request_bytes,
                expected_context_digest=expected_context_digest,
                expected_registry_digest=expected_registry_digest)
            if type(cost) is not dict or set(cost)!=COST_KEYS or fallback not in FALLBACKS:
                raise ValueError()
            for value in cost.values():
                if value is not None and (type(value) not in (int,float) or not math.isfinite(value) or value<0):
                    raise ValueError()
            copied_cost = dict(cost)
            if any(copied_cost[key] is None for key in COST_KEYS-{'totalMs'}):
                copied_cost['totalMs'] = None
            reasons = list(packet['reasonCodes'])
            if len(reasons)>8:
                raise ValueError()
            record = {'version':'s1-stage-observation-v1','stage':packet['stage'],
                'status':packet['status'],'reasonCodes':reasons,
                'requestDigest':packet['requestDigest'],'contextDigest':packet['contextDigest'],
                'registryDigest':packet['registryDigest'],'adviceDigest':packet['packetDigest'],
                'cost':copied_cost,'fallback':fallback}
            if len(canonical(record))>1024:
                raise ValueError()
            record = freeze(record)
        except (ValueError,TypeError,KeyError,OverflowError):
            return self._result('refused','invalid-observation')
        def insert(cancelled):
            if cancelled:
                return self._result('refused','cancelled')
            if self._clock() >= start + 5_000_000_000:
                return self._result('refused','deadline-exceeded')
            if not self._lock.acquire(blocking=False):
                return self._result('busy','busy')
            try:
                if len(self._records)==self._capacity:
                    self._dropped = min(2**63-1,self._dropped+1)
                    return self._result('dropped','overflow')
                self._records.append(record)
                return self._result('recorded')
            finally:
                self._lock.release()
        return token.publish(insert)

    def drain(self):
        if not self._lock.acquire(blocking=False):
            return freeze({'status':'busy','records':[],'dropped':None})
        try:
            result = freeze({'status':'drained','records':self._records,'dropped':self._dropped})
            self._records = []
            self._dropped = 0
            return result
        finally:
            self._lock.release()
