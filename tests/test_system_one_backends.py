# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.system_one import CancellationToken, build_answers, validate_request
from agent_braid.system_one_backends import DecisionRuntime, RuleBackend, capabilities
from tests.test_system_one_core import encoded, fixture


class SystemOneBackendTests(unittest.TestCase):
    def test_public_runtime_refuses_custom_backend_injection(self):
        with self.assertRaises(TypeError):
            DecisionRuntime(backend=object())

    def test_offline_discovery_deeply_immutable(self):
        discovery = capabilities()
        self.assertEqual(discovery["tokenUnit"], "character-token-v1")
        self.assertEqual(discovery["primitives"], ("boolean", "choice", "score"))
        self.assertEqual(discovery["maxActive"], 1)
        self.assertFalse(discovery["executionAuthorization"])
        with self.assertRaises(TypeError):
            discovery["maxTokens"] = 0
        with self.assertRaises(TypeError):
            discovery["primitives"][0] = "generated"

    def test_rule_fixture_and_cooperative_stop(self):
        request = validate_request(encoded(fixture()))
        token = CancellationToken()
        backend = RuleBackend()
        self.assertEqual(backend.evaluate(request, deadline_ns=10, cancellation=token, clock=lambda: 0), ((0.0, 1.0),))
        self.assertEqual(backend.evaluate(request, deadline_ns=0, cancellation=token, clock=lambda: 0), ())
        token.cancel()
        self.assertEqual(backend.evaluate(request, deadline_ns=10, cancellation=token, clock=lambda: 0), ())

    def test_invalid_inputs_never_call_backend(self):
        class MustNotRun:
            def evaluate(self, *_args, **_kwargs):
                raise AssertionError("invalid input entered backend")
        runtime = test_runtime(backend=MustNotRun())
        response = runtime.evaluate(b'{"secret":"/private/source"}')
        self.assertEqual(response["reasonCodes"], ["invalid-envelope"])
        self.assertNotIn("secret", str(response))
        self.assertEqual(runtime.admission_snapshot()["active"], 0)

    def test_invalid_backend_masses_release_slot_and_refuse(self):
        class Invalid:
            def evaluate(self, *_args, **_kwargs):
                return ((0.0, float("nan")),)
        runtime = test_runtime(backend=Invalid())
        response = runtime.evaluate(encoded(fixture()))
        self.assertEqual(response["reasonCodes"], ["invalid-backend-output"])
        self.assertEqual(response["answers"], [])
        self.assertEqual(runtime.admission_snapshot()["active"], 0)


    def test_rule_allocation_is_lazy_until_valid_diagnostic_admission(self):
        from unittest.mock import patch
        from agent_braid.system_one import STRICT_POLICY
        with patch("agent_braid.system_one_backends.RuleBackend", side_effect=AssertionError("unexpected allocation")):
            runtime = DecisionRuntime()
            self.assertEqual(runtime.evaluate(b"{}")["status"], "refused")
            self.assertEqual(runtime.evaluate(encoded(fixture(policy=STRICT_POLICY)))["status"], "abstain")


def test_runtime(*, backend, **kwargs):
    """Private test seam; supported runtime cannot select an injected backend."""
    runtime = DecisionRuntime(**kwargs)
    runtime._backend = backend
    return runtime
