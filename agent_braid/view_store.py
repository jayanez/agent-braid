# SPDX-License-Identifier: AGPL-3.0-only
"""The in-memory Loom event store: a bounded ring with monotonic `seq`, caps and subscribers.

The store holds validated agent-braid-loom/v0.1 events (see view_loom) only in process
memory; it never touches the file system and cannot grant, run or schedule anything.
Producers never block: an append takes a short lock, and a subscriber that falls too far
behind is dropped rather than waited for.

Behaviour in short:
* `append` validates a copy of the event, assigns the next `seq` (1, 2, 3, ... whatever
  `seq` the caller supplied), stores it, and evicts the oldest event past the ring bound.
* Per-session caps (strands, crossings, waves, grants) refuse input beyond the cap: the
  event is not stored and one `stream-truncated` gap per exhausted cap is stored instead.
* Eviction is announced at read time: `replay` and subscribers receive one derived
  `ring-evicted` gap covering the range a client missed. Its `seq` is the last evicted
  `seq`, so a client that resumes from the gap's id neither repeats nor skips anything.
* A subscriber is a cursor over the ring. It is dropped when more than `subscriber_queue`
  live events are waiting unread; the backlog replayed at subscribe time is exempt. A
  dropped client resumes with `subscribe(after_seq=last_seq)`.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from itertools import islice
import threading
import time
from typing import Any, Callable

from agent_braid.view_loom import MAX_EVENTS, SCHEMA_VERSION, LoomError, validate_event

MAX_SUBSCRIBERS = 8
SUBSCRIBER_QUEUE = 1024
CAP_LIMITS = {"strands": 256, "crossings": 4096, "waves": 64, "grants": 1024}
_GRANT_KINDS = ("grant.issued", "grant.consumed", "grant.expired", "grant.refused")


class StoreError(RuntimeError):
    """A store request was refused; `reason` is a stable name."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason


class SubscriberDropped(Exception):
    """The subscriber was closed or fell behind; resume with `subscribe(after_seq=last_seq)`."""

    def __init__(self, last_seq: int, reason: str) -> None:
        super().__init__(f"subscriber {reason} after seq {last_seq}")
        self.last_seq = last_seq
        self.reason = reason


def _seq_arg(value: Any, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} is a non-negative integer")
    return value


class Subscriber:
    """A cursor over the store's ring. Create with `LoomStore.subscribe`."""

    def __init__(self, store: "LoomStore", after_seq: int, start_head: int) -> None:
        self._store = store
        self._cursor = after_seq + 1  # seq of the next event to deliver
        self._start_head = start_head
        self._state: str | None = None  # None while live, then "closed" or "too-slow"

    def get(self, timeout: float | None = None) -> dict[str, Any] | None:
        """The next event or derived gap; None on timeout. Raises SubscriberDropped when over."""
        store = self._store
        with store._cond:
            store._cond.wait_for(lambda: self._state is not None or self._cursor <= store._head, timeout)
            if self._state is not None:
                raise SubscriberDropped(self._cursor - 1, self._state)
            if self._cursor > store._head:
                return None
            oldest = store._head - len(store._ring) + 1
            if self._cursor < oldest:
                gap = store._evicted_gap(self._cursor, oldest - 1)
                self._cursor = oldest
                return gap
            item = store._ring[self._cursor - oldest]
            self._cursor += 1
            return item

    def close(self) -> None:
        with self._store._cond:
            self._store._release(self, "closed")

    def __enter__(self) -> "Subscriber":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


class LoomStore:
    """Thread-safe bounded ring of validated Loom events."""

    def __init__(self, max_events: int = MAX_EVENTS, max_subscribers: int = MAX_SUBSCRIBERS,
                 subscriber_queue: int = SUBSCRIBER_QUEUE, caps: dict[str, int] | None = None,
                 clock: Callable[[], int] = time.monotonic_ns) -> None:
        if not 1 <= max_events <= MAX_EVENTS:
            raise ValueError(f"max_events is between 1 and {MAX_EVENTS}")
        if max_subscribers < 1 or subscriber_queue < 1:
            raise ValueError("max_subscribers and subscriber_queue are at least 1")
        self._caps = dict(CAP_LIMITS)
        for name, value in (caps or {}).items():
            if name not in CAP_LIMITS or not 1 <= value <= CAP_LIMITS[name]:
                raise ValueError(f"cap {name!r} is between 1 and its contract limit")
            self._caps[name] = value
        self._max_events = max_events
        self._max_subscribers = max_subscribers
        self._queue_limit = subscriber_queue
        self._clock = clock
        self._origin = clock()
        self._cond = threading.Condition()
        self._ring: deque[dict[str, Any]] = deque()
        self._head = 0  # seq of the newest event ever stored; the next seq is head + 1
        self._evicted = 0
        self._subscribers: list[Subscriber] = []
        self._known: dict[str, set[Any]] = {name: set() for name in CAP_LIMITS}
        self._refused: dict[str, int] = {}
        self._announced: set[str] = set()

    # -- producers -------------------------------------------------------------------------

    def append(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Validate and store `event` under the next `seq`; return the stored event.

        Returns None when a cap refused it (a `stream-truncated` gap is stored once per cap).
        Raises LoomError for an invalid event; nothing is stored and no `seq` is consumed.
        The caller's dict is neither modified nor kept.
        """
        candidate = deepcopy(event) if isinstance(event, dict) else event
        validate_event(candidate)
        with self._cond:
            cap = self._cap_check(candidate)
            if cap is not None:
                self._refused[cap] = self._refused.get(cap, 0) + 1
                if cap not in self._announced:
                    self._announced.add(cap)
                    self._store(self._truncation_gap())
                return None
            return self._store(candidate)

    # -- consumers -------------------------------------------------------------------------

    def replay(self, after_seq: int = 0, limit: int | None = None) -> list[dict[str, Any]]:
        """Retained events with `seq` > after_seq, led by a `ring-evicted` gap if some were lost.

        The events are shared with the store: treat them as read-only.
        """
        _seq_arg(after_seq, "after_seq")
        if limit is not None and (type(limit) is not int or limit < 1):
            raise ValueError("limit is a positive integer")
        with self._cond:
            items: list[dict[str, Any]] = []
            oldest = self._head - len(self._ring) + 1
            start = after_seq + 1
            if start < oldest:
                items.append(self._evicted_gap(start, oldest - 1))
                start = oldest
            if start <= self._head:
                items.extend(islice(self._ring, start - oldest, None))
            return items if limit is None else items[:limit]

    def subscribe(self, after_seq: int | None = None) -> Subscriber:
        """Register a subscriber; with `after_seq` it first receives the retained backlog.

        Raises StoreError('subscriber-limit') when the maximum is reached.
        """
        if after_seq is not None:
            _seq_arg(after_seq, "after_seq")
        with self._cond:
            if len(self._subscribers) >= self._max_subscribers:
                raise StoreError("subscriber-limit", f"at most {self._max_subscribers} subscribers")
            subscriber = Subscriber(self, self._head if after_seq is None else after_seq, self._head)
            self._subscribers.append(subscriber)
            return subscriber

    def stats(self) -> dict[str, Any]:
        with self._cond:
            return {
                "count": len(self._ring),
                "headSeq": self._head,
                "oldestSeq": self._head - len(self._ring) + 1 if self._ring else None,
                "evicted": self._evicted,
                "subscribers": len(self._subscribers),
                "refused": dict(self._refused),
                "limits": {"events": self._max_events, **self._caps, "subscribers": self._max_subscribers},
            }

    # -- internals (callers hold the lock) ---------------------------------------------------

    def _store(self, event: dict[str, Any]) -> dict[str, Any]:
        self._head += 1
        event["seq"] = self._head
        self._ring.append(event)
        if len(self._ring) > self._max_events:
            self._ring.popleft()
            self._evicted += 1
        for subscriber in tuple(self._subscribers):
            if self._head - max(subscriber._cursor - 1, subscriber._start_head) > self._queue_limit:
                self._release(subscriber, "too-slow")
        self._cond.notify_all()
        return event

    def _release(self, subscriber: Subscriber, state: str) -> None:
        if subscriber._state is None:
            subscriber._state = state
            self._subscribers.remove(subscriber)
            self._cond.notify_all()

    def _cap_check(self, event: dict[str, Any]) -> str | None:
        """The name of the exhausted cap that refuses `event`, else None (new entities are counted)."""
        kind, data = event["kind"], event["data"]
        if kind == "strand.open":
            name, key = "strands", data["strandId"]
        elif kind == "crossing.classified":
            name, key = "crossings", (data["reportId"], data["left"], data["right"])
        elif kind in ("wave.started", "wave.finished"):
            name, key = "waves", (data["scheduleId"], data["wave"])
        elif kind in _GRANT_KINDS:
            name, key = "grants", data["grantId"]
        else:
            return None
        known = self._known[name]
        if key not in known:
            if len(known) >= self._caps[name]:
                return name
            known.add(key)
        return None

    def _derived_gap(self, reason: str, from_seq: int | None, to_seq: int | None) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION, "seq": 1, "kind": "observation.gap",
            "at": {"relMs": (self._clock() - self._origin) // 1_000_000, "basis": "viewer-monotonic"},
            "source": {"adapter": "viewer", "evidenceRef": None, "host": "braid", "verification": "derived"},
            "assurance": {"compatibilityClass": None, "notAGuarantee": True},
            "executionAuthorization": False,
            "data": {"reason": reason, "strandId": None, "fromSeq": from_seq, "toSeq": to_seq},
        }

    def _truncation_gap(self) -> dict[str, Any]:
        return self._derived_gap("stream-truncated", None, None)

    def _evicted_gap(self, from_seq: int, to_seq: int) -> dict[str, Any]:
        gap = self._derived_gap("ring-evicted", from_seq, to_seq)
        gap["seq"] = to_seq
        return gap


__all__ = ["LoomError", "LoomStore", "StoreError", "Subscriber", "SubscriberDropped"]
