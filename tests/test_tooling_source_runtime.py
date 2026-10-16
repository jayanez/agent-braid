# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic installed cache bridge; real provider provenance is not supplied."""
from dataclasses import replace
from datetime import timedelta
import hashlib
from pathlib import Path
import tempfile
import unittest

from agent_braid import tooling_registration_v6 as v6
from agent_braid import tooling_source_observer as sources
from agent_braid import tooling_source_runtime as runtime
from agent_braid.tooling_subscription import SubscriptionError, operational_binding_from_dict
from tests.test_tooling_codex_sources import fixture, NOW
from tests.test_tooling_source_observer import SyntheticVerifier
from tests.test_tooling_supervisor import _snapshot


class SourceRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        observer, verifier = root / "observer.py", root / "verifier.py"
        observer.write_bytes(b"test-only observer")
        verifier.write_bytes(b"test-only verifier")
        observer.chmod(0o600)
        verifier.chmod(0o600)
        self.procedures = sources.ProcedureFiles(observer, verifier)
        contract, rows, _ = fixture()
        core = replace(operational_binding_from_dict(contract["binding"]),
            observer_source_sha256=hashlib.sha256(observer.read_bytes()).hexdigest(),
            observer_verifier_sha256=hashlib.sha256(verifier.read_bytes()).hexdigest())
        contract["binding"] = core.as_dict()
        from agent_braid import tooling_codex_sources as codex
        digest = codex.source_contract_sha256(contract)
        self.binding = v6.SourceRouteBinding(core, digest, v6._canonical(contract))
        for row in rows.values():
            row.update(binding=core.as_dict(), contractSha256=digest)
        self.rows = rows
        self.verifier = SyntheticVerifier()
        self.cache = sources.SourceObserverCache(contract, expected_contract_sha256=digest,
                                                receipt_verifier=self.verifier)
        self.cache.publish(rows, now=NOW)
        self.now = NOW
        self.bridge = runtime.CachedSourceRuntime(self.cache, self.binding,
            procedures=self.procedures, telemetry=lambda *_: _snapshot(eur=None),
            utc_now=lambda: self.now)
        from types import SimpleNamespace
        self.request = SimpleNamespace(source_route_binding=self.binding, subscription_binding=self.binding,
                                       native_route_binding=None, operational_route_binding=None)

    def test_consumer_and_verifier_use_authenticated_cache_without_acquisition(self):
        value = self.bridge.observe(None, 0, False)
        self.bridge.verify_source_observation(value.source_route, self.binding, None, self.request, False)
        self.assertEqual(["quota", "autoRecharge", "process"], self.verifier.calls)
        self.assertIsNone(value.costs.values["eur"])
        self.assertEqual(NOW + timedelta(seconds=30), value.source_route.composition.valid_until)

    def test_superseded_original_or_invalidated_claims_refuse(self):
        old = self.bridge.observe(None, 0, False).source_route
        for row in self.rows.values():
            row["observedSequence"] = 2
        self.cache.publish(self.rows, now=NOW)
        with self.assertRaises(SubscriptionError):
            self.bridge.verify_source_observation(old, self.binding, None, self.request, False)
        self.cache.invalidate()
        with self.assertRaises(sources.SourceObserverError):
            self.bridge.observe(None, 0, False)

    def test_original_expiry_refuses_without_retimestamp(self):
        self.now = NOW + timedelta(seconds=31)
        with self.assertRaises(sources.SourceObserverError):
            self.bridge.observe(None, 0, False)

    def test_missing_kernel_birth_refuses(self):
        from types import SimpleNamespace
        with self.assertRaises(sources.SourceObserverError):
            self.bridge.observe(SimpleNamespace(pid=42, birth=None), 0, False)

    def test_procedure_byte_drift_prevents_installation(self):
        self.procedures.verifier.write_bytes(b"changed verifier")
        with self.assertRaises(sources.SourceObserverError):
            runtime.CachedSourceRuntime(self.cache, self.binding, procedures=self.procedures,
                                       telemetry=lambda *_: _snapshot(eur=None))
