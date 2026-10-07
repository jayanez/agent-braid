# SPDX-License-Identifier: AGPL-3.0-only
"""Predeclared pull-buffer sequences, immutable privacy and publication controls."""
from copy import deepcopy
import json
from pathlib import Path
import threading
import unittest
from unittest.mock import patch

from agent_braid.system_one import CancellationToken, canonical, digest, thaw
from agent_braid.system_one_hooks import ObservationBuffer
from tests.test_system_one_core import fixture
from agent_braid.system_one import evaluate

_CORPUS = Path(__file__).resolve().parents[1] / "specs/032-system-one-product/fixtures/pull-hooks.json"


class ObservationTests(unittest.TestCase):
    def _digest(self, packet):
        self.assertEqual(packet["packetDigest"], digest({k:v for k,v in packet.items() if k != "packetDigest"}))
        self.assertIs(packet["executionAuthorization"], False)

    def test_frozen_predeclared_sequences(self):
        corpus = json.loads(_CORPUS.read_text())
        for case in corpus["cases"]:
            with self.subTest(case=case["caseId"]):
                responses = deepcopy(corpus["responses"])
                buffer = ObservationBuffer(case["capacity"])
                for step in case["steps"]:
                    controls = step.get("controls", {})
                    if step["operation"] == "mutateCallerResponse":
                        target = responses[step["response"]]
                        for key in step["path"][:-1]:target = target[key]
                        target[step["path"][-1]] = step["value"]
                        continue
                    held = controls.get("holdBufferLock", False)
                    if held: buffer._lock.acquire()
                    try:
                        if step["operation"] == "record":
                            token = CancellationToken()
                            if controls.get("cancelBeforeInsert"):token.cancel()
                            clock = [0,5_000_000_000] if "monotonicBeforeInsertMs" in controls else None
                            if clock:
                                with patch("agent_braid.system_one_hooks._monotonic_ns", side_effect=clock):
                                    result = buffer.record(canonical(responses[step["response"]]),request_bytes=None,cancellation=token)
                            else:
                                result = buffer.record(canonical(responses[step["response"]]),request_bytes=None,cancellation=token)
                            if "expectedInserted" in step:self.assertEqual(result["status"] == "recorded",step["expectedInserted"])
                            if "expectedReason" in step:self.assertEqual(result["reasonCodes"],(step["expectedReason"],))
                            if "expectedCapacityDropped" in step:self.assertEqual(result["droppedCount"],step["expectedCapacityDropped"])
                            for forbidden in step.get("mustNotEcho",[]):self.assertNotIn(forbidden,canonical(result).decode())
                        else:
                            result = buffer.drain()
                            expected = step["expectedRecords"]
                            self.assertEqual(thaw(result["records"]),None if expected is None else [corpus["expectedStoredMetadata"][key] for key in expected])
                            self.assertEqual(result["droppedCount"],step["expectedDropped"])
                        if "expectedStatus" in step:self.assertEqual(result["status"],step["expectedStatus"])
                        self._digest(result)
                    finally:
                        if held:buffer._lock.release()
        for capacity in corpus["constructionRefusals"]:
            value = capacity.get("capacity") if isinstance(capacity,dict) else capacity
            with self.assertRaisesRegex(ValueError,"^invalid observation capacity$"):ObservationBuffer(value)

    def test_matching_request_required_and_privacy_immutable(self):
        request = canonical(fixture()); response = canonical(evaluate(request)); buffer = ObservationBuffer()
        self.assertEqual(buffer.record(response,request_bytes=None)["status"],"refused")
        wrong = fixture(request_id="other")
        self.assertEqual(buffer.record(response,request_bytes=canonical(wrong))["status"],"refused")
        self.assertEqual(buffer.record(response,request_bytes=request)["status"],"recorded")
        row = buffer.drain()["records"][0]
        self.assertEqual(set(row),{"contractVersion","responseDigest","backendId","capabilityId","policyId","status","reasonCodes","usage","evidenceClass","executionAuthorization"})
        with self.assertRaises(TypeError):row["usage"]["totalMs"] = 1

    def test_refuse_non_bytes_bad_capacity_and_token_reuse(self):
        buffer = ObservationBuffer()
        for capacity in [True,0,65,1.0,None]:
            with self.assertRaises(ValueError):ObservationBuffer(capacity)
        for bad in [b"{}",bytearray(b"{}"),None,b'{"a":1,"a":2}']:
            self.assertEqual(buffer.record(bad,request_bytes=None)["status"],"refused")
        with self.assertRaisesRegex(TypeError,"^invalid cancellation token$"):
            buffer.record(b"{}",request_bytes=None,cancellation=object())
        token = CancellationToken();token.claim()
        with self.assertRaises(ValueError):buffer.record(b"{}",request_bytes=None,cancellation=token)
        token.release()

    def test_falsey_token_keeps_supplied_cancellation_and_claim(self):
        class Falsey(CancellationToken):
            def __bool__(self):return False
        token = Falsey();token.cancel()
        buffer = ObservationBuffer()
        response = canonical(json.loads(_CORPUS.read_text())["responses"]["A"])
        result = buffer.record(response,request_bytes=None,cancellation=token)
        self.assertEqual(result["status"],"defer")
        self.assertEqual(result["reasonCodes"],("cancelled",))
        self.assertEqual(buffer.drain()["records"],())
        token = Falsey();token.claim()
        try:
            with self.assertRaises(ValueError):buffer.record(response,request_bytes=None,cancellation=token)
        finally:token.release()

    def test_cancel_before_mutation_and_after_atomic_publication(self):
        corpus = json.loads(_CORPUS.read_text()); raw = canonical(corpus["responses"]["A"])
        class Before(CancellationToken):
            def publish(self,factory):self.cancel();return super().publish(factory)
        class After(CancellationToken):
            def publish(self,factory):
                result = super().publish(factory);self.cancel();return result
        buffer = ObservationBuffer()
        self.assertEqual(buffer.record(raw,request_bytes=None,cancellation=Before())["reasonCodes"],("cancelled",))
        self.assertEqual(buffer.record(raw,request_bytes=None,cancellation=After())["status"],"recorded")
        self.assertEqual(len(buffer.drain()["records"]),1)

    def test_saturation_and_real_lock_contention_preserve_capture(self):
        corpus = json.loads(_CORPUS.read_text());raw = canonical(corpus["responses"]["A"])
        buffer = ObservationBuffer(1);buffer.record(raw,request_bytes=None);buffer._dropped = 9223372036854775807
        self.assertEqual(buffer.record(raw,request_bytes=None)["droppedCount"],9223372036854775807)
        entered = threading.Event();release = threading.Event()
        def owner():
            with buffer._lock:entered.set();release.wait(2)
        worker = threading.Thread(target=owner);worker.start();self.assertTrue(entered.wait(1))
        try:
            self.assertEqual(buffer.record(raw,request_bytes=None)["status"],"busy")
            self.assertIsNone(buffer.drain()["droppedCount"])
        finally:release.set();worker.join(2)
        result = buffer.drain();self.assertEqual(len(result["records"]),1);self.assertEqual(result["droppedCount"],9223372036854775807)


if __name__ == "__main__":unittest.main()
