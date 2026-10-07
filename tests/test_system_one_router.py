# SPDX-License-Identifier: AGPL-3.0-only
"""Frozen metadata classification controls and actual package pin checks."""
from contextlib import ExitStack
import json
from pathlib import Path
import unittest
import threading
from unittest.mock import patch

from agent_braid import system_one_router as router
from agent_braid.system_one import CancellationToken, canonical, digest, freeze, thaw

_FIXTURES = Path(__file__).resolve().parents[1] / "specs/032-system-one-product/fixtures"


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((_FIXTURES / "metadata-router.json").read_text())

    def assert_packet(self, result):
        value = thaw(result)
        self.assertEqual(set(value), {"contractVersion", "requestId", "requestDigest", "registryDigest", "status", "route", "reasonCodes", "evidenceClass", "executionAuthorization", "packetDigest"})
        self.assertIs(value["executionAuthorization"], False)
        self.assertEqual(value["evidenceClass"], "heuristic")
        self.assertEqual(value["packetDigest"], digest({k: v for k, v in value.items() if k != "packetDigest"}))
        return value

    def fixture_registry(self, variant=None):
        # Substitute only fixture's illustrative manifest pins. The frozen expected
        # statuses/reasons/route identities are never obtained from implementation.
        body = thaw(self.corpus["syntheticRegistryBody"] if variant is None else self.corpus["registryVariants"][variant])
        for route in body["routes"]:
            route["installedManifestDigest"] = digest(router.COMPILER_MANIFEST if route["taskId"] == "schema-compile-fixture" else router.CORE_ROUTE_MANIFEST)
        return {**body, "digest": digest(body)}

    def request(self, registry=None):
        registry = router.router_registry_manifest() if registry is None else registry
        return dict(contractVersion=router.VERSION, requestId="fixture-route", sourceKind="synthetic", languageTag="en", taskId="boolean-fixture", registryDigest=registry["digest"], deadlineMs=5000)

    def test_frozen_classifications_with_explicit_pin_substitution(self):
        for case in self.corpus["cases"]:
            with self.subTest(case=case["caseId"]), ExitStack() as stack:
                variant = case.get("registryVariant")
                registry = self.fixture_registry(variant)
                fixture_body = self.corpus["syntheticRegistryBody"] if variant is None else self.corpus["registryVariants"][variant]
                placeholder = digest(fixture_body)
                request = thaw(case["request"])
                expected_pin = case["expectedRegistryDigest"]
                original_pin = request["registryDigest"]
                if original_pin == placeholder:
                    request["registryDigest"] = registry["digest"]
                if expected_pin == placeholder:
                    expected_pin = registry["digest"]
                if case["caseId"] == "stale-pin":
                    self.assertEqual(request["registryDigest"], original_pin)
                    self.assertNotEqual(request["registryDigest"], registry["digest"])
                stack.enter_context(patch.object(router, "ROUTER_REGISTRY", freeze(registry)))
                token = CancellationToken()
                original = router._packet
                now = [0]
                controls = case["controls"]
                def at_boundary(request, pin, status, reason, route=None):
                    result = original(request, pin, status, reason, route)
                    if status == "matched":
                        if controls.get("cancelBeforePublication"):
                            token.cancel()
                        if "monotonicBeforePublicationMs" in controls:
                            now[0] = 5000000000
                    return result
                stack.enter_context(patch.object(router, "_packet", side_effect=at_boundary))
                stack.enter_context(patch.object(router, "_monotonic_ns", side_effect=lambda: now[0]))
                result = self.assert_packet(router.route_metadata(canonical(request), expected_registry_digest=expected_pin, cancellation=token))
                for key, value in case["expected"].items():
                    if key == "mustNotEcho":
                        for secret in value:
                            self.assertNotIn(secret, canonical(result).decode())
                    elif key == "route" and value is not None:
                        expected_route = thaw(value)
                        expected_route["installedManifestDigest"] = digest(router.COMPILER_MANIFEST if value["taskId"] == "schema-compile-fixture" else router.CORE_ROUTE_MANIFEST)
                        self.assertEqual(result[key], expected_route)
                    else:
                        self.assertEqual(result[key], value)

    def test_actual_package_registry_pins_and_capabilities(self):
        registry = router.router_registry_manifest()
        self.assertEqual(registry["digest"], digest({"version": registry["version"], "routes": registry["routes"]}))
        capabilities = router.router_capabilities()
        self.assertEqual(capabilities["registryDigest"], registry["digest"])
        self.assertEqual(capabilities["routes"], tuple(r for r in registry["routes"] if r["supported"]))
        result = self.assert_packet(router.route_metadata(canonical(self.request(registry)), expected_registry_digest=registry["digest"]))
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["route"]["policyId"], "strict-uncalibrated-v1")
        self.assertEqual(result["requestDigest"], digest(self.request(registry)))
        for pin in ["0" * 64, "bad", None, True, []]:
            result = self.assert_packet(router.route_metadata(canonical(self.request(registry)), expected_registry_digest=pin))
            self.assertEqual(result["reasonCodes"], ["registry-pin-mismatch"])

    def test_registry_forgery_is_rejected_before_matching(self):
        good = self.fixture_registry()
        def assert_rejected(value):
            with patch.object(router, "ROUTER_REGISTRY", freeze(value)):
                result = self.assert_packet(router.route_metadata(canonical(self.request(good)), expected_registry_digest=good["digest"]))
                self.assertEqual(result["reasonCodes"], ["registry-pin-mismatch"])
                self.assertIsNone(result["route"])
        for alteration in ["manifest", "authority", "duplicate", "order", "backend", "supported", "extra", "version", "digest"]:
            value = thaw(good)
            if alteration == "manifest": value["routes"][0]["installedManifestDigest"] = "0" * 64
            if alteration == "authority": value["routes"][0]["executionAuthorization"] = True
            if alteration == "duplicate": value["routes"][1] = thaw(value["routes"][0])
            if alteration == "order": value["routes"].reverse()
            if alteration == "backend": value["routes"][0]["backendId"] = "model"
            if alteration == "supported": value["routes"][0]["supported"] = 1
            if alteration == "extra": value["secret"] = "sentinel"
            if alteration == "version": value["version"] = "other"
            value["digest"] = "0" * 64 if alteration == "digest" else digest({"version": value["version"], "routes": value["routes"]})
            with self.subTest(alteration=alteration):
                assert_rejected(value)

    def test_raw_limits_builtin_bytes_and_unsafe_envelopes(self):
        registry = router.router_registry_manifest()
        raw = canonical(self.request(registry))
        for bad in [bytearray(raw), memoryview(raw), raw.decode(), b'{} trailing', b'\xef\xbb\xbf{}', b'{"x":1,"x":2}', b'x' * 1048577,
                    b'{"x":NaN}', b'{"x":"\\ud800"}', b'{"x":1e999}']:
            result = self.assert_packet(router.route_metadata(bad, expected_registry_digest=registry["digest"]))
            self.assertEqual(result["reasonCodes"], ["invalid-router-request"])
            self.assertIsNone(result["requestId"])
            self.assertIsNone(result["requestDigest"])
        self.assertEqual(router.route_metadata(raw + b' ' * (1048576 - len(raw)), expected_registry_digest=registry["digest"])["status"], "matched")
        for key, bad in [("languageTag", []), ("taskId", {}), ("taskId", ""), ("requestId", "x" * 65), ("requestId", "a\x7f"), ("deadlineMs", 0), ("deadlineMs", 5001), ("deadlineMs", 1.0), ("registryDigest", "A" * 64)]:
            value = self.request(registry)
            value[key] = bad
            self.assertEqual(router.route_metadata(canonical(value), expected_registry_digest=registry["digest"])["reasonCodes"], ("invalid-router-request",))

    def test_immutability_absent_routes_and_no_silent_policy_change(self):
        registry = self.fixture_registry()
        with patch.object(router, "ROUTER_REGISTRY", freeze(registry)):
            result = router.route_metadata(canonical(self.request(registry)), expected_registry_digest=registry["digest"])
            with self.assertRaises(TypeError): result["route"]["policyId"] = "synthetic-diagnostic-v1"
            copied = thaw(result)
            copied["route"]["supported"] = False
            self.assertIs(result["route"]["supported"], True)
        body = {"version": router.VERSION, "routes": []}
        empty = {**body, "digest": digest(body)}
        with patch.object(router, "ROUTER_REGISTRY", freeze(empty)):
            self.assertEqual(router.route_metadata(canonical(self.request(empty)), expected_registry_digest=empty["digest"])["reasonCodes"], ("capability-not-installed",))

    def test_token_reuse_and_atomic_cancel_deadline_precedence(self):
        registry = router.router_registry_manifest()
        request = canonical(self.request(registry))
        with self.assertRaisesRegex(TypeError, "invalid cancellation token"):
            router.route_metadata(request, expected_registry_digest=registry["digest"], cancellation=object())
        token = CancellationToken()
        token.claim()
        try:
            with self.assertRaises(ValueError): router.route_metadata(request, expected_registry_digest=registry["digest"], cancellation=token)
        finally:
            token.release()
        original = router._packet
        now = [0]
        def boundary(request, pin, status, reason, route=None):
            result = original(request, pin, status, reason, route)
            if status == "matched":
                token.cancel()
                now[0] = 5000000000
            return result
        with patch.object(router, "_packet", side_effect=boundary), patch.object(router, "_monotonic_ns", side_effect=lambda: now[0]):
            result = self.assert_packet(router.route_metadata(request, expected_registry_digest=registry["digest"], cancellation=token))
        self.assertEqual(result["reasonCodes"], ["cancelled"])
        token.claim()
        token.release()

    def test_real_token_cancellation_race_suppresses_route(self):
        entered, release = threading.Event(), threading.Event()
        token = CancellationToken()
        outcomes, errors = [], []
        original = router._packet
        registry = router.router_registry_manifest()
        raw = canonical(self.request(registry))
        def boundary(request, pin, status, reason, route=None):
            result = original(request, pin, status, reason, route)
            if status == "matched":
                entered.set()
                if not release.wait(2):
                    raise AssertionError("barrier timeout")
            return result
        def worker():
            try:
                outcomes.append(router.route_metadata(raw, expected_registry_digest=registry["digest"], cancellation=token))
            except Exception as exc:
                errors.append(exc)
        with patch.object(router, "_packet", side_effect=boundary):
            thread = threading.Thread(target=worker)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                with self.assertRaises(ValueError):
                    router.route_metadata(raw, expected_registry_digest=registry["digest"], cancellation=token)
                token.cancel()
            finally:
                release.set()
                thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(len(outcomes), 1)
        result = self.assert_packet(outcomes[0])
        self.assertEqual(result["reasonCodes"], ["cancelled"])
        self.assertIsNone(result["route"])

    def test_zero_dispatch_and_no_feature_import_discovery(self):
        import socket
        import subprocess
        import builtins
        from agent_braid import system_one, system_one_backends
        registry = router.router_registry_manifest()
        with patch.object(socket, "socket", side_effect=AssertionError("network")), patch.object(subprocess, "Popen", side_effect=AssertionError("process")), patch.object(system_one, "evaluate", side_effect=AssertionError("evaluation")), patch.object(system_one_backends, "DecisionRuntime", side_effect=AssertionError("admission")), patch.object(builtins, "__import__", side_effect=AssertionError("dynamic import")):
            self.assertEqual(router.route_metadata(canonical(self.request(registry)), expected_registry_digest=registry["digest"])["status"], "matched")
            router.router_capabilities()
            router.router_registry_manifest()
