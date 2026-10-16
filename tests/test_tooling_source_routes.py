# SPDX-License-Identifier: AGPL-3.0-only
"""Owned synthetic subprocesses for the distinct source route; no native host."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import time
import unittest
from unittest.mock import patch

from agent_braid import tooling_codex_sources as codex
from agent_braid import tooling_registration_v6 as v6
from agent_braid import tooling_source_observer as sources
from agent_braid import tooling_supervisor as supervisor
from tests.test_tooling_codex_sources import fixture
from tests import test_tooling_supervisor as _helpers
from tests.test_tooling_supervisor import _snapshot, _sha


class SyntheticSourceVerifier:
    def __init__(self, binding):
        core = binding.binding
        self.source_ref, self.source_sha256 = core.observer_source_ref, core.observer_source_sha256
        self.verifier_ref, self.verifier_sha256 = core.observer_verifier_ref, core.observer_verifier_sha256

    def verify_source_observation(self, observation, binding, identity, request, final):
        # Synthetic unit trust only. This class is never shipped as a verifier.
        return None


class SourceRouteSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.helper = _helpers.ToolingSupervisorTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)

    def inputs(self, *, max_age=2):
        req = replace(self.helper.request("import sys; print(sys.stdin.read(), flush=True)", stdin=b"owned-synthetic-input"), env={})
        contract, receipts, _ = fixture()
        core = replace(supervisor.OperationalProcessRouteBinding(**{
            "host": "codex", "registration_sha256": _sha("reg"), "slot_id": "synthetic-slot",
            "policy_sha256": _sha("source-policy"), "account_sha256": _sha("account"),
            "account_namespace_sha256": _sha("namespace"), "host_build_sha256": req.executable_sha256,
            "candidate_artifact_sha256": _sha("candidate"), "executable_sha256": req.executable_sha256,
            "config_sha256": supervisor._native_config_digest(()),
            "argv_sha256": _sha(supervisor._json_bytes(list(req.argv))), "model_identity_sha256": _sha("model"),
            "observer_source_ref": "private-source-observer", "observer_source_sha256": _sha("observer"),
            "observer_verifier_ref": "private-source-verifier", "observer_verifier_sha256": _sha("verifier"),
            "max_age_seconds": max_age,
        }))
        contract["binding"] = core.as_dict()
        digest = codex.source_contract_sha256(contract)
        binding = v6.SourceRouteBinding(core, digest, v6._canonical(contract))
        req = replace(req, source_route_binding=binding, subscription_binding=binding)
        calls = [0]

        def observe(identity, elapsed, final):
            calls[0] += 1
            records = deepcopy(receipts)
            now = datetime.now(timezone.utc)
            for row in records.values():
                row.update(binding=core.as_dict(), contractSha256=digest,
                           phase="prelaunch" if identity is None else ("completed" if final else "running"),
                           processId=None if identity is None else identity.pid,
                           processBirthSha256=None if identity is None else supervisor._process_birth_sha256(identity.birth),
                           observedSequence=calls[0], observedAt=now.isoformat())
            composition = codex.compose_codex_sources(contract, records, expected_contract_sha256=digest, now=now)
            return replace(_snapshot(eur=None, wall=0.1 + elapsed),
                           source_route=sources.SourceObservation(composition, records))
        return req, observe, binding

    def test_fresh_source_route_completes_without_any_v3_flag_synthesis(self):
        req, observe, binding = self.inputs()
        result = supervisor.run_supervised(req, self.helper.caps, observe,
                                           source_route_verifier=SyntheticSourceVerifier(binding))
        self.assertTrue(result.completed, result)
        self.assertEqual("owned-synthetic-input", result.stdout_path.read_text().strip())
        record = json.loads(result.receipt_path.read_text())
        self.assertNotIn("private-source-observer", result.receipt_path.read_text())
        proof = supervisor._snapshot_dict(result.last_snapshot)["sourceProcessRoute"]
        self.assertNotIn("subscriptionActive", proof)
        self.assertEqual("completed", proof["phase"])
        self.assertIsNone(result.last_snapshot.costs.values["eur"])

    def test_missing_verifier_and_mixed_legacy_route_refuse_before_launch(self):
        req, observe, binding = self.inputs()
        with self.assertRaises(supervisor.SupervisorError):
            supervisor.run_supervised(req, self.helper.caps, observe)
        req = replace(req, operational_route_binding=binding.binding)
        with self.assertRaises(supervisor.SupervisorError):
            supervisor.run_supervised(req, self.helper.caps, observe,
                                     source_route_verifier=SyntheticSourceVerifier(binding))

    def test_unavailable_prelaunch_source_never_starts(self):
        req, _, binding = self.inputs()
        result = supervisor.run_supervised(req, self.helper.caps,
            lambda *_: _snapshot(eur=None), source_route_verifier=SyntheticSourceVerifier(binding))
        self.assertFalse(result.launched)
        self.assertFalse(result.completed)

    def test_wrong_process_birth_stops_before_stdin_release(self):
        req, observe, binding = self.inputs()
        def wrong(identity, elapsed, final):
            value = observe(identity, elapsed, final)
            if identity is None:
                return value
            rows = value.source_route.as_dict()["receipts"]
            for row in rows.values():
                row["processBirthSha256"] = "f" * 64
            composition = codex.compose_codex_sources(binding.contract, rows,
                expected_contract_sha256=binding.contract_sha256, now=datetime.now(timezone.utc))
            return replace(value, source_route=sources.SourceObservation(composition, rows))
        result = supervisor.run_supervised(req, self.helper.caps, wrong,
                                           source_route_verifier=SyntheticSourceVerifier(binding))
        self.assertTrue(result.launched)
        self.assertFalse(result.completed)
        self.assertNotIn("owned-synthetic-input", result.stdout_path.read_text())

    def test_source_expiry_during_verification_refuses_prelaunch(self):
        req, observe, binding = self.inputs(max_age=0.03)
        class SlowVerifier(SyntheticSourceVerifier):
            def verify_source_observation(self, *args):
                time.sleep(0.06)
        result = supervisor.run_supervised(req, self.helper.caps, observe,
                                           source_route_verifier=SlowVerifier(binding))
        self.assertFalse(result.launched)
        self.assertFalse(result.completed)

    def test_source_invalidated_after_initial_verification_never_starts(self):
        req, observe, binding = self.inputs()
        class InvalidatedVerifier(SyntheticSourceVerifier):
            calls = 0

            def verify_source_observation(self, *args):
                self.calls += 1
                if self.calls > 1:
                    raise supervisor.SubscriptionError("source cache invalidated after initial verification")

        verifier = InvalidatedVerifier(binding)
        with patch.object(supervisor.subprocess, "Popen", side_effect=AssertionError("must not launch")) as launch:
            result = supervisor.run_supervised(req, self.helper.caps, observe,
                                               source_route_verifier=verifier)
        launch.assert_not_called()
        self.assertEqual(2, verifier.calls)
        self.assertFalse(result.launched)
        self.assertFalse(result.completed)
