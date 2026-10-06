# SPDX-License-Identifier: AGPL-3.0-only
"""Offline reference backend and bounded request-local cooperative runtime."""
from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
import threading
from time import monotonic_ns
from typing import Callable, Protocol

from agent_braid.system_one import (BACKEND_ID, CAPABILITY_ID, MAX_BYTES, VERSION,
    CancellationToken, DecisionRequest, InvalidDecision, build_answers, freeze,
    make_response, validate_request, digest)
from agent_braid.system_one_policy import outcome


class Backend(Protocol):
    """No network/artifact allocation; outputs contain masses only, never authority."""
    def evaluate(self, request: DecisionRequest, *, deadline_ns: int,
                 cancellation: CancellationToken, clock: Callable[[], int]) -> tuple[tuple[float, ...], ...]: ...


class RuleBackend:
    """One-hot hand-authored fixture lookup, without interpreting natural language."""
    def evaluate(self, request: DecisionRequest, *, deadline_ns: int,
                 cancellation: CancellationToken, clock: Callable[[], int]) -> tuple[tuple[float, ...], ...]:
        distributions = []
        for question in request.questions:
            if cancellation.cancelled or clock() >= deadline_ns:
                return ()
            selected = request.state["ruleAnswers"].get(question.id)
            if selected is None:
                return ()
            distributions.append(tuple(float(option.id == selected) for option in question.options))
        return tuple(distributions)


def capabilities() -> Mapping:
    """Discover immutable local support without loading optional packages."""
    return freeze({"backendId": BACKEND_ID, "capabilityId": CAPABILITY_ID,
        "contractVersion": VERSION, "primitives": ["boolean", "choice", "score"],
        "tokenUnit": "character-token-v1", "renderer": "entire-canonical-request-v1",
        "numericRepresentation": "binary64", "maxInputBytes": MAX_BYTES,
        "maxTokens": MAX_BYTES, "maxQuestions": 32, "maxOptions": 32,
        "maxActive": 1, "maxWaiting": 8, "calibrationStatus": "absent",
        "executionAuthorization": False})


@dataclass(eq=False)
class _Ticket:
    request: DecisionRequest
    cancellation: CancellationToken
    deadline_ns: int


class DecisionRuntime:
    """One active/eight queued; cancellation suppresses late publication, not work.

    The supported runtime uses only the pinned rule backend. Tests may replace
    private collaborators; caller-selected backend injection is not a public API.
    """
    def __init__(self, *, clock: Callable[[], int] = monotonic_ns) -> None:
        self._backend: Backend | None = None
        self._clock = clock
        self._condition = threading.Condition()
        self._waiting: deque[_Ticket] = deque()
        self._active: _Ticket | None = None
        self._closed = False

    def capabilities(self) -> Mapping:
        return capabilities()

    def _wake(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def admission_snapshot(self) -> Mapping:
        """Immutable diagnostics; counts are observations, not capacity benchmarks."""
        with self._condition:
            return freeze({"active": int(self._active is not None), "waiting": len(self._waiting), "closed": self._closed})

    def close(self) -> None:
        with self._condition:
            self._closed = True
            active = self._active
            self._condition.notify_all()
        if active is not None:
            active.cancellation.cancel()

    def __enter__(self) -> DecisionRuntime:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def evaluate(self, raw: bytes, *, cancellation: CancellationToken | None = None) -> dict:
        """Validate at materialized-byte ingress, admit and publish one terminal result."""
        start = self._clock()
        token = CancellationToken() if cancellation is None else cancellation
        if not isinstance(token, CancellationToken):
            raise TypeError("cancellation must be a CancellationToken")
        token.claim()
        try:
            return self._evaluate(raw, token=token, start=start)
        finally:
            token.release()

    def _evaluate(self, raw: bytes, *, token: CancellationToken, start: int) -> dict:
        request = None
        status, reasons, answers = "refused", ["invalid-envelope"], []
        usage = {"queueMs": 0.0, "loadMs": 0.0, "renderMs": 0.0, "inferenceMs": 0.0,
                 "totalMs": 0.0, "inputBytes": min(len(raw), MAX_BYTES + 1) if type(raw) is bytes else 0,
                 "renderTokens": 0}
        try:
            request = validate_request(raw, clock=self._clock)
        except InvalidDecision as exc:
            reasons = [exc.reason]
            usage["totalMs"] = max(0.0, (self._clock() - start) / 1000000)
            return make_response(None, status=status, reasons=reasons, usage=usage).to_dict()
        usage.update(renderMs=request.render_ms, renderTokens=request.render_tokens)
        deadline = start + request.budgets.deadline_ms * 1000000
        ticket = _Ticket(request, token, deadline)
        remove_waker = token.add_waker(self._wake)
        admitted = False
        queued_at = self._clock()
        try:
            with self._condition:
                if self._closed:
                    status, reasons = "defer", ["backend-closed"]
                elif token.cancelled:
                    status, reasons = "defer", ["cancelled"]
                elif self._clock() >= deadline:
                    status, reasons = "defer", ["deadline-exceeded"]
                elif (self._active is not None or self._waiting) and len(self._waiting) >= 8:
                    status, reasons = "defer", ["overloaded"]
                else:
                    self._waiting.append(ticket)
                    self._condition.notify_all()
                    while True:
                        if self._closed or token.cancelled or self._clock() >= deadline:
                            status, reasons = "defer", ["backend-closed" if self._closed else "cancelled" if token.cancelled else "deadline-exceeded"]
                            self._waiting.remove(ticket)
                            self._condition.notify_all()
                            break
                        if self._active is None and self._waiting[0] is ticket:
                            self._waiting.popleft()
                            self._active = ticket
                            admitted = True
                            self._condition.notify_all()
                            break
                        self._condition.wait(timeout=min(0.05, max(0.000001, (deadline - self._clock()) / 1000000000)))
            usage["queueMs"] = max(0.0, (self._clock() - queued_at) / 1000000)
            if admitted:
                if token.cancelled or self._clock() >= deadline:
                    status, reasons = "defer", ["cancelled" if token.cancelled else "deadline-exceeded"]
                else:
                    status, reasons = outcome(request)
                    if status == "answered":
                        inference_start = self._clock()
                        try:
                            backend = RuleBackend() if self._backend is None else self._backend
                            if token.cancelled or self._clock() >= deadline:
                                status, reasons = "defer", ["cancelled" if token.cancelled else "deadline-exceeded"]
                            else:
                                distributions = backend.evaluate(request, deadline_ns=deadline, cancellation=token, clock=self._clock)
                                answers = build_answers(request, distributions)
                        except Exception:
                            status, reasons, answers = "refused", ["invalid-backend-output"], []
                        finally:
                            usage["inferenceMs"] = max(0.0, (self._clock() - inference_start) / 1000000)
            def publish(cancelled: bool) -> dict:
                final_status, final_reasons, final_answers = status, reasons, answers
                if cancelled or self._clock() >= deadline:
                    final_status, final_reasons, final_answers = "defer", ["cancelled" if cancelled else "deadline-exceeded"], []
                usage["totalMs"] = max(0.0, (self._clock() - start) / 1000000)
                response = make_response(request, status=final_status, reasons=final_reasons,
                                         answers=final_answers, usage=usage).to_dict()
                # Include response construction in total and enforce deadline after it.
                response["usage"]["totalMs"] = max(0.0, (self._clock() - start) / 1000000)
                response["responseDigest"] = digest({key: item for key, item in response.items() if key != "responseDigest"})
                if self._clock() >= deadline and response["status"] != "defer":
                    response = make_response(request, status="defer", reasons=["deadline-exceeded"],
                                             usage=response["usage"]).to_dict()
                return response
            return token.publish(publish)
        finally:
            remove_waker()
            if admitted:
                with self._condition:
                    self._active = None
                    self._condition.notify_all()
