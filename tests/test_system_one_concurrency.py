# SPDX-License-Identifier: AGPL-3.0-only
"""Event/condition-driven admission, isolation, cancellation and deadline tests."""
from concurrent.futures import ThreadPoolExecutor
import threading
import unittest

from agent_braid.system_one import CancellationToken
from agent_braid.system_one_backends import DecisionRuntime, RuleBackend
from tests.test_system_one_core import encoded, fixture


class BlockingBackend(RuleBackend):
    def __init__(self):
        self.entered = threading.Event()
        self.release = threading.Event()
        self.ids = []
        self.concurrent = 0
        self.maximum = 0
        self.lock = threading.Lock()

    def evaluate(self, request, **kwargs):
        with self.lock:
            self.ids.append(request.envelope["requestId"])
            self.concurrent += 1
            self.maximum = max(self.maximum, self.concurrent)
            first = len(self.ids) == 1
        try:
            if first:
                self.entered.set()
                if not self.release.wait(3):
                    raise RuntimeError("test barrier was not released")
            return super().evaluate(request, **kwargs)
        finally:
            with self.lock:
                self.concurrent -= 1


class FakeClock:
    def __init__(self):
        self.now = 0
        self.lock = threading.Lock()

    def __call__(self):
        with self.lock:
            return self.now

    def advance(self, nanoseconds):
        with self.lock:
            self.now += nanoseconds


class SystemOneConcurrencyTests(unittest.TestCase):
    def test_policy_crossing_deadline_or_cancellation_never_enters_backend(self):
        from unittest.mock import patch
        from agent_braid.system_one_policy import outcome
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                clock = FakeClock()
                token = CancellationToken()
                backend = BlockingBackend()
                runtime = test_runtime(backend=backend, clock=clock)
                value = fixture()
                value["budgets"]["deadlineMs"] = 1
                def crossing(request):
                    if cancel:
                        token.cancel()
                    else:
                        clock.advance(1_000_000)
                    return outcome(request)
                with patch("agent_braid.system_one_backends.outcome", side_effect=crossing):
                    response = runtime.evaluate(encoded(value), cancellation=token)
                self.assertEqual(response["status"], "defer")
                self.assertEqual(response["answers"], [])
                self.assertEqual(response["reasonCodes"], ["cancelled" if cancel else "deadline-exceeded"])
                self.assertEqual(backend.ids, [])
                self.assertEqual(runtime.admission_snapshot()["active"], 0)

    def wait_queued(self, runtime, count):
        # The condition is a synchronization barrier, not a timing assumption.
        with runtime._condition:
            self.assertTrue(runtime._condition.wait_for(lambda: len(runtime._waiting) == count, timeout=2))

    def test_interleaved_inputs_keep_their_own_state_and_one_active_slot(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                first = pool.submit(runtime.evaluate, encoded(fixture(request_id="first", choice="false")))
                self.assertTrue(backend.entered.wait(2))
                second = pool.submit(runtime.evaluate, encoded(fixture(request_id="second", choice="true")))
                self.wait_queued(runtime, 1)
                self.assertEqual(backend.ids, ["first"])
                backend.release.set()
                left, right = first.result(2), second.result(2)
            finally:
                backend.release.set()
        self.assertEqual([left["requestId"], right["requestId"]], ["first", "second"])
        self.assertEqual([left["answers"][0]["choiceId"], right["answers"][0]["choiceId"]], ["false", "true"])
        self.assertNotEqual(left["stateDigest"], right["stateDigest"])
        self.assertEqual(backend.maximum, 1)
        self.assertEqual(runtime.admission_snapshot()["active"], 0)

    def test_eight_waiters_and_ninth_overload(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        with ThreadPoolExecutor(max_workers=9) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")))
                self.assertTrue(backend.entered.wait(2))
                waiting = [pool.submit(runtime.evaluate, encoded(fixture(request_id=f"queued-{i}"))) for i in range(8)]
                self.wait_queued(runtime, 8)
                overflow = runtime.evaluate(encoded(fixture(request_id="overflow")))
                self.assertEqual(overflow["status"], "defer")
                self.assertEqual(overflow["reasonCodes"], ["overloaded"])
                self.assertEqual(backend.ids, ["active"])
                backend.release.set()
                self.assertEqual(active.result(2)["status"], "answered")
                self.assertTrue(all(future.result(2)["status"] == "answered" for future in waiting))
            finally:
                backend.release.set()
        self.assertNotIn("overflow", backend.ids)
        self.assertEqual(backend.maximum, 1)

    def test_queued_cancellation_removes_ticket_without_backend_call(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        token = CancellationToken()
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")))
                self.assertTrue(backend.entered.wait(2))
                queued = pool.submit(runtime.evaluate, encoded(fixture(request_id="cancelled")), cancellation=token)
                self.wait_queued(runtime, 1)
                token.cancel()
                token.cancel()
                response = queued.result(2)
                self.assertEqual(response["reasonCodes"], ["cancelled"])
                self.assertEqual(response["answers"], [])
                self.assertEqual(backend.ids, ["active"])
                self.assertEqual(runtime.admission_snapshot()["active"], 1)
                backend.release.set()
                active.result(2)
            finally:
                backend.release.set()
        self.assertTrue(token.cancelled)

    def test_active_cancellation_suppresses_late_answer_keeps_slot_until_stop(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        token = CancellationToken()
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")), cancellation=token)
                self.assertTrue(backend.entered.wait(2))
                token.cancel()
                waiting = pool.submit(runtime.evaluate, encoded(fixture(request_id="next")))
                self.wait_queued(runtime, 1)
                self.assertEqual(backend.ids, ["active"])
                self.assertFalse(active.done())
                backend.release.set()
                response = active.result(2)
                self.assertEqual(response["status"], "defer")
                self.assertEqual(response["reasonCodes"], ["cancelled"])
                self.assertEqual(response["answers"], [])
                self.assertEqual(waiting.result(2)["requestId"], "next")
            finally:
                backend.release.set()
        self.assertEqual(backend.maximum, 1)

    def test_monotonic_exact_deadline_suppresses_finished_work(self):
        clock = FakeClock()
        class Advance(RuleBackend):
            def evaluate(self, request, **kwargs):
                result = super().evaluate(request, **kwargs)
                clock.advance(5000000)
                return result
        runtime = test_runtime(backend=Advance(), clock=clock)
        value = fixture()
        value["budgets"]["deadlineMs"] = 5
        response = runtime.evaluate(encoded(value))
        self.assertEqual(response["reasonCodes"], ["deadline-exceeded"])
        self.assertEqual(response["answers"], [])
        self.assertEqual(response["usage"]["inferenceMs"], 5)
        self.assertEqual(response["usage"]["totalMs"], 5)

    def test_expired_queue_and_close_do_not_start_new_work(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")))
                self.assertTrue(backend.entered.wait(2))
                queued = pool.submit(runtime.evaluate, encoded(fixture(request_id="queued")))
                self.wait_queued(runtime, 1)
                runtime.close()
                self.assertEqual(queued.result(2)["reasonCodes"], ["backend-closed"])
                self.assertEqual(runtime.evaluate(encoded(fixture()))["reasonCodes"], ["backend-closed"])
                backend.release.set()
                self.assertEqual(active.result(2)["answers"], [])
            finally:
                backend.release.set()
        self.assertEqual(backend.ids, ["active"])

    def test_pre_cancel_and_after_publication_are_distinct(self):
        token = CancellationToken()
        runtime = DecisionRuntime()
        response = runtime.evaluate(encoded(fixture()), cancellation=token)
        token.cancel()
        self.assertEqual(response["status"], "answered")
        cancelled = runtime.evaluate(encoded(fixture()), cancellation=token)
        self.assertEqual(cancelled["reasonCodes"], ["cancelled"])
        self.assertEqual(cancelled["answers"], [])


    def test_queued_deadline_expires_without_evaluating(self):
        clock = FakeClock()
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend, clock=clock)
        with ThreadPoolExecutor(max_workers=2) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")))
                self.assertTrue(backend.entered.wait(2))
                value = fixture(request_id="expired")
                value["budgets"]["deadlineMs"] = 1
                queued = pool.submit(runtime.evaluate, encoded(value))
                self.wait_queued(runtime, 1)
                clock.advance(1000000)
                runtime._wake()  # Notify an injected clock change, without sleeping.
                response = queued.result(2)
                self.assertEqual(response["reasonCodes"], ["deadline-exceeded"])
                self.assertEqual(response["answers"], [])
                self.assertEqual(backend.ids, ["active"])
                backend.release.set()
                active.result(2)
            finally:
                backend.release.set()

    def test_concurrent_token_reuse_is_rejected_and_no_cross_request_cancel(self):
        backend = BlockingBackend()
        runtime = test_runtime(backend=backend)
        token = CancellationToken()
        with ThreadPoolExecutor(max_workers=1) as pool:
            try:
                active = pool.submit(runtime.evaluate, encoded(fixture(request_id="active")), cancellation=token)
                self.assertTrue(backend.entered.wait(2))
                with self.assertRaisesRegex(ValueError, "active request"):
                    runtime.evaluate(encoded(fixture(request_id="unrelated")), cancellation=token)
                self.assertEqual(backend.ids, ["active"])
                backend.release.set()
                self.assertEqual(active.result(2)["status"], "answered")
            finally:
                backend.release.set()
        self.assertFalse(token.cancelled)

    def test_publication_construction_cannot_escape_deadline(self):
        from unittest.mock import patch
        from agent_braid import system_one_backends
        clock = FakeClock()
        original = system_one_backends.make_response
        def costly_response(*args, **kwargs):
            result = original(*args, **kwargs)
            clock.advance(1000000)
            return result
        value = fixture()
        value["budgets"]["deadlineMs"] = 1
        with patch.object(system_one_backends, "make_response", costly_response):
            response = DecisionRuntime(clock=clock).evaluate(encoded(value))
        self.assertEqual(response["reasonCodes"], ["deadline-exceeded"])
        self.assertEqual(response["answers"], [])


def test_runtime(*, backend, **kwargs):
    """Private test seam; supported runtime cannot select an injected backend."""
    runtime = DecisionRuntime(**kwargs)
    runtime._backend = backend
    return runtime
