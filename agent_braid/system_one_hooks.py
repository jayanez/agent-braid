# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit bounded pull observation of core metadata, without callbacks or I/O."""
from __future__ import annotations

from collections.abc import Mapping
import threading
from time import monotonic_ns as _monotonic_ns

from agent_braid.system_one import (
    CancellationToken, InvalidDecision, canonical, digest, freeze, parse_json,
    validate_request, validate_response,
)

_VERSION = "s1-observation-outcome-v1"
_MAX_DROPS = 9223372036854775807
_FIELDS = ("contractVersion", "responseDigest", "backendId", "capabilityId",
           "policyId", "status", "reasonCodes", "usage", "evidenceClass",
           "executionAuthorization")


def _outcome(status: str, reasons: tuple[str, ...] = (), *, dropped=None,
             records=...) -> Mapping:
    value = {"contractVersion": _VERSION, "status": status,
             "reasonCodes": list(reasons), "droppedCount": dropped,
             "evidenceClass": "heuristic", "executionAuthorization": False}
    if records is not ...:
        value["records"] = records
    value["packetDigest"] = digest(value)
    return freeze(value)


class ObservationBuffer:
    """Owner-local immutable metadata; at most 64 records and 1024 bytes each."""

    def __init__(self, capacity: int = 64):
        if type(capacity) is not int or not 1 <= capacity <= 64:
            raise ValueError("invalid observation capacity")
        self._capacity = capacity
        self._lock = threading.Lock()
        self._records: list[Mapping] = []
        self._dropped = 0

    def record(self, response_bytes: bytes, *, request_bytes: bytes | None,
               cancellation: CancellationToken | None = None) -> Mapping:
        started = _monotonic_ns()
        deadline = started + 5_000_000_000
        if cancellation is not None and not isinstance(cancellation, CancellationToken):
            raise TypeError("invalid cancellation token")
        token = cancellation if cancellation is not None else CancellationToken()
        token.claim()
        try:
            def terminal():
                if token.cancelled:
                    return _outcome("defer", ("cancelled",))
                if _monotonic_ns() >= deadline:
                    return _outcome("defer", ("deadline-exceeded",))
                return None

            stopped = terminal()
            if stopped is not None:
                return stopped
            try:
                request = None if request_bytes is None else validate_request(request_bytes)
                response = parse_json(response_bytes)
                stopped = terminal()
                if stopped is not None:
                    return stopped
                validate_response(response, request=request)
                metadata = freeze({name: response[name] for name in _FIELDS})
                if len(canonical(metadata)) > 1024:
                    raise InvalidDecision()
            except (InvalidDecision, ValueError, TypeError, UnicodeError, OverflowError, KeyError):
                return _outcome("refused", ("invalid-observation",))
            stopped = terminal()
            if stopped is not None:
                return stopped
            if not self._lock.acquire(blocking=False):
                return _outcome("busy", ("busy",))
            try:
                def insert(cancelled):
                    if cancelled:
                        return _outcome("defer", ("cancelled",))
                    if _monotonic_ns() >= deadline:
                        return _outcome("defer", ("deadline-exceeded",))
                    if len(self._records) >= self._capacity:
                        self._dropped = min(_MAX_DROPS, self._dropped + 1)
                        return _outcome("dropped", ("buffer-full",), dropped=self._dropped)
                    self._records.append(metadata)
                    return _outcome("recorded", dropped=self._dropped)
                return token.publish(insert)
            finally:
                self._lock.release()
        finally:
            token.release()

    def drain(self) -> Mapping:
        if not self._lock.acquire(blocking=False):
            return _outcome("busy", ("busy",), records=None)
        try:
            value = _outcome("drained", dropped=self._dropped,
                             records=tuple(self._records))
            self._records.clear()
            self._dropped = 0
            return value
        finally:
            self._lock.release()
