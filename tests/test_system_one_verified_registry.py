# SPDX-License-Identifier: AGPL-3.0-only
"""Static registry identity tests using an explicitly unregistered test entry."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import system_one_verified_registry as registry
from agent_braid.system_one import canonical, digest, freeze, thaw


class VerifiedRegistryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((Path(__file__).parent / "fixtures" /
                                   "system_one_verified_registry.json").read_text())
        self.private_test_entry = freeze(self.fixture["entry"])
        self.identity = self.fixture["identity"].copy()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name) / "private-test-verifier.py"
        self.source.write_bytes(self.fixture["sourceBytes"].encode())
        self.calls = []

    def checkpoint(self, stage, units):
        self.calls.append((stage, units))

    def configured(self):
        """Private test patch only; there is no product registration interface."""
        self.enterContext(patch.object(registry, "_PINNED_VERIFIER_SHA256",
                                       self.private_test_entry["verifierDigest"]))
        self.enterContext(patch.object(registry, "_VERIFIER_SOURCE", self.source))

    def assert_refusal(self, identity, reason):
        with self.assertRaises(ValueError) as caught:
            registry.resolve(identity, checkpoint=self.checkpoint)
        self.assertEqual(str(caught.exception), reason)

    def test_production_unavailable_without_pin_and_no_source_read(self):
        with patch.object(registry, "_PINNED_VERIFIER_SHA256", None), \
                patch.object(Path, "open", side_effect=AssertionError("unexpected read")):
            self.assert_refusal(self.identity, "registry-mismatch")
        self.assertEqual(self.calls, [("verification", 0)])

    def test_private_static_identity_and_canonical_manifest(self):
        self.configured()
        self.assertEqual(self.fixture["purpose"], "private-test-only-unregistered")
        self.assertEqual(sha256(self.source.read_bytes()).hexdigest(),
                         self.identity["verifierDigest"])
        self.assertEqual(digest(self.fixture["manifest"]), self.identity["registryDigest"])
        self.assertEqual(canonical(registry._manifest(self.private_test_entry)),
                         canonical(self.fixture["manifest"]))
        result = registry.resolve(freeze(self.identity), checkpoint=self.checkpoint)
        self.assertEqual(thaw(result), self.fixture["entry"])
        self.assertEqual(set(result), {"domainId", "irVersion", "observationContract",
                                     "implementationId", "verifierDigest"})
        self.assertEqual(self.calls, [("verification", 0)] * 3)
        with self.assertRaises(TypeError):
            result["domainId"] = "changed"
        manifest = registry._manifest(result)
        with self.assertRaises(TypeError):
            manifest["entries"][0]["verifierDigest"] = "0" * 64
        with self.assertRaises(TypeError):
            manifest["entries"][0] = result
        mutable = thaw(result)
        mutable["domainId"] = "changed"
        self.assertEqual(result["domainId"], self.fixture["entry"]["domainId"])

    def test_unknown_identity_fields_refuse_before_source_access(self):
        self.configured()
        for field, reason in (("domainId", "unsupported-domain"),
                              ("irVersion", "unsupported-version"),
                              ("observationContract", "unsupported-observation")):
            with self.subTest(field=field), patch.object(
                    Path, "open", side_effect=AssertionError("unexpected read")):
                self.assert_refusal({**self.identity, field: "unknown"}, reason)

    def test_exact_schema_rejects_missing_extra_and_authority_fields(self):
        self.configured()
        for field in self.identity:
            with self.subTest(missing=field):
                self.assert_refusal({k: v for k, v in self.identity.items() if k != field},
                                    "invalid-envelope")
        for field, value in (("plugin", "os.system"), ("module", "arbitrary"),
                             ("factory", lambda: None), ("confidence", 1),
                             ("calibratedProbability", 1.0), ("verified", True),
                             ("executionAuthorization", False)):
            with self.subTest(extra=field):
                self.assert_refusal({**self.identity, field: value}, "invalid-envelope")
        for malformed in (None, [], 1, True):
            with self.subTest(root=malformed):
                self.assert_refusal(malformed, "invalid-envelope")

    def test_identity_values_have_strict_types_bounds_and_encoding(self):
        self.configured()
        for field in self.identity:
            for value in (None, True, 1, 1.0, [], {}, b"bytes", "", "x" * 65,
                          "é" * 33, "x\x00", "x\x7f", "x\x9f", "\ud800"):
                with self.subTest(field=field, value=repr(value)):
                    self.assert_refusal({**self.identity, field: value}, "invalid-envelope")
        for field in ("registryDigest", "verifierDigest"):
            for value in ("A" * 64, "g" * 64, "a" * 63, "a" * 63 + "\n"):
                with self.subTest(field=field, value=repr(value)):
                    self.assert_refusal({**self.identity, field: value}, "invalid-envelope")

    def test_independent_pins_and_manifest_are_required(self):
        self.configured()
        self.assert_refusal({**self.identity, "registryDigest": "0" * 64},
                            "registry-mismatch")
        self.assert_refusal({**self.identity, "verifierDigest": "0" * 64},
                            "verifier-mismatch")
        altered_manifest = thaw(self.fixture["manifest"])
        altered_manifest["entries"][0]["implementationId"] = "caller-plugin"
        self.assert_refusal({**self.identity, "registryDigest": digest(altered_manifest)},
                            "registry-mismatch")
        for bad_pin in (None, "pending", "0" * 64, True):
            with self.subTest(pin=bad_pin), patch.object(
                    registry, "_PINNED_VERIFIER_SHA256", bad_pin):
                self.assert_refusal(self.identity, "registry-mismatch")

    def test_missing_changed_oversized_source_refuses_even_with_valid_manifest(self):
        self.configured()
        for contents in (b"altered verifier", b"", b"x" * 1_048_577):
            with self.subTest(length=len(contents)):
                self.source.write_bytes(contents)
                self.assert_refusal(self.identity, "verifier-mismatch")
        self.source.unlink()
        self.assert_refusal(self.identity, "verifier-mismatch")

    def test_source_read_is_bounded(self):
        self.configured()
        with patch.object(Path, "open") as opened:
            reader = opened.return_value.__enter__.return_value
            reader.read.return_value = self.fixture["sourceBytes"].encode()
            result = registry.resolve(self.identity, checkpoint=self.checkpoint)
        self.assertEqual(thaw(result), self.fixture["entry"])
        reader.read.assert_called_once_with(1_048_577)

    def test_checkpoint_errors_propagate_at_every_boundary(self):
        self.configured()
        for failure_at in (1, 2, 3):
            for reason in ("cancelled", "deadline-exceeded", "work-budget-exceeded"):
                with self.subTest(failure_at=failure_at, reason=reason):
                    failure = ValueError(reason)
                    seen = []
                    def checkpoint(stage, units):
                        seen.append((stage, units))
                        if len(seen) == failure_at:
                            raise failure
                    with self.assertRaises(ValueError) as caught:
                        registry.resolve(self.identity, checkpoint=checkpoint)
                    self.assertIs(caught.exception, failure)
                    self.assertEqual(seen, [("verification", 0)] * failure_at)

    def test_product_interface_has_no_caller_registration_or_dispatch(self):
        import inspect
        self.assertEqual(tuple(inspect.signature(registry.resolve).parameters),
                         ("identity", "checkpoint"))
        self.configured()
        for field in ("sourcePath", "entry", "registry", "implementationId"):
            self.assert_refusal({**self.identity, field: "chosen-by-caller"},
                                "invalid-envelope")


if __name__ == "__main__":
    unittest.main()
