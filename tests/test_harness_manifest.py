# SPDX-License-Identifier: AGPL-3.0-only
"""Offline manifest/consumer controls; no source or native execution acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import unittest

from agent_braid import harness_manifest as manifests
from agent_braid.system_one import canonical, digest, thaw


def make_manifest() -> dict:
    """Return a fresh valid wire fixture for dependent offline module tests."""
    def file(path, content, **extra):
        return {"path": path, "sha256": sha256(content).hexdigest(),
                "sizeBytes": len(content), **extra}

    base = [file("guidance/main.md", b"Retain the static base.\n")]
    candidate = [file("guidance/main.md", b"Use a bounded handoff.\n")]
    return {
        "format": manifests.FORMAT, "profile": manifests.PROFILE,
        "source": {"commit": "1" * 40, "selectedInputs": [
            file("task.txt", b"owned task\n", origin="committed")]},
        "base": {"sha256": digest(base), "files": base},
        "candidate": {"sha256": digest(candidate), "files": candidate},
        "task": {"id": "C01-001", "inputSha256": digest({"task": "owned"}),
                 "fixtureSha256": digest({"oracle": "independent"})},
        "context": [{"id": "context-1", "path": "notes/context.txt", "sha256": "2" * 64,
                     "sizeBytes": 12, "trust": "untrusted-evidence", "selected": True}],
        "host": {"kind": "offline", "executableSha256": None, "build": None,
                 "requested": {"model": None, "effort": None, "route": "offline"},
                 "observed": {"provider": None, "model": None, "build": None, "route": None}},
        "tools": [{"id": "fixture-contract", "sha256": "3" * 64}],
        "policy": {"version": "offline-v1", "sha256": "4" * 64},
        "verifier": {"version": "fixture-v1", "sha256": "5" * 64},
        "normalizer": {"version": "exact-v1", "sha256": "6" * 64},
        "environment": {"os": "Darwin", "architecture": "arm64", "sha256": "7" * 64,
                        "outputDestinationSha256": "8" * 64},
        "envelopeSha256": "9" * 64,
        "allowedComponentPaths": ["guidance/main.md"],
        "effects": {"read": ["base/guidance/main.md", "candidate/guidance/main.md",
                             "context/notes/context.txt", "source/task.txt"],
                    "write": ["lab/guidance/main.md"], "delete": []},
        "limits": thaw(manifests.DEFAULT_LIMITS), "executionAuthorization": False,
    }


class HarnessManifestTests(unittest.TestCase):
    def parse(self, value):
        return manifests.parse_manifest(canonical(value))

    def rejects(self, value):
        with self.assertRaises(manifests.ManifestError):
            self.parse(value)

    def test_canonical_identity_and_all_named_bindings(self):
        value = make_manifest()
        result = self.parse(value)
        raw = json.dumps(value, indent=2).encode()
        self.assertEqual(result.sha256, sha256(canonical(value)).hexdigest())
        self.assertEqual(result.canonical_bytes, canonical(value))
        self.assertEqual(set(result.bindings), manifests.BINDING_NAMES)
        self.assertEqual(result.bindings["fixture"], value["task"]["fixtureSha256"])
        self.assertEqual(result.bindings["envelope"], value["envelopeSha256"])
        verified = manifests.verify_manifest(raw, expected_sha256=result.sha256,
                                             expected_bindings=result.bindings)
        self.assertEqual(verified.to_dict(), value)
        self.assertFalse(verified.data["executionAuthorization"])

    def test_view_and_returned_copies_have_no_mutable_aliases(self):
        value = make_manifest()
        result = self.parse(value)
        before = result.canonical_bytes
        value["context"][0]["selected"] = False
        copy = result.to_dict()
        copy["candidate"]["files"][0]["sha256"] = "a" * 64
        with self.assertRaises(TypeError):
            result.data["context"][0]["selected"] = False
        with self.assertRaises(TypeError):
            result.bindings["source"] = "b" * 64
        with self.assertRaises(FrozenInstanceError):
            result.canonical_bytes = b"forged"
        self.assertEqual(result.canonical_bytes, before)
        self.assertTrue(result.to_dict()["context"][0]["selected"])

    def test_full_identity_detects_every_top_level_binding_change(self):
        original = self.parse(make_manifest())
        for field in ("source", "task", "context", "tools", "policy", "verifier",
                      "normalizer", "environment", "envelopeSha256"):
            value = make_manifest()
            if field == "source":
                value[field]["selectedInputs"][0]["origin"] = "uncommitted"
            elif field == "task":
                value[field]["id"] = "C02-002"
            elif field == "context":
                value[field][0]["selected"] = False
            elif field == "tools":
                value[field][0]["sha256"] = "a" * 64
            elif field == "envelopeSha256":
                value[field] = "a" * 64
            else:
                value[field]["sha256"] = "a" * 64
            with self.subTest(field=field), self.assertRaisesRegex(
                    manifests.ManifestError, "^manifest-drift$"):
                manifests.verify_manifest(canonical(value), expected_sha256=original.sha256,
                                          expected_bindings={})

    def test_each_independent_binding_refuses_even_with_matching_complete_digest(self):
        raw = canonical(make_manifest())
        result = manifests.parse_manifest(raw)
        for name in manifests.BINDING_NAMES:
            with self.subTest(name=name), self.assertRaisesRegex(
                    manifests.ManifestError, "^binding-drift$"):
                manifests.verify_manifest(raw, expected_sha256=result.sha256,
                                          expected_bindings={name: "f" * 64})
        for expected in ({"source.commit": "f" * 64}, {"source": "short"}, {1: "f" * 64}, []):
            with self.subTest(expected=expected), self.assertRaises(manifests.ManifestError):
                manifests.verify_manifest(raw, expected_sha256=result.sha256,
                                          expected_bindings=expected)
        with self.assertRaises(manifests.ManifestError):
            manifests.verify_manifest(raw, expected_sha256="short", expected_bindings={})

    def test_strict_json_types_duplicates_unicode_depth_and_nonfinite(self):
        raws = [b'{"format":"x","format":"y"}', b'{"x":NaN}', b'{"x":Infinity}',
                b'{"x":1e999}', b'{"x":9223372036854775808}', b'{"x":"\\ud800"}',
                b'\xef\xbb\xbf{}', b'\xff', b'{} trailing', b'[]',
                b'{"x":' + b'[' * 16 + b'0' + b']' * 16 + b'}']
        for raw in raws:
            with self.subTest(raw=raw[:40]), self.assertRaises(manifests.ManifestError):
                manifests.parse_manifest(raw)
        for raw in (None, {}, "{}", bytearray(b"{}")):
            with self.subTest(type=type(raw)), self.assertRaises(manifests.ManifestError):
                manifests.parse_manifest(raw)

    def test_unknown_missing_fields_and_wrong_nested_types_refuse(self):
        for target in (None, "source", "host", "limits", "environment", "policy", "effects"):
            for action in ("extra", "missing"):
                value = make_manifest()
                record = value if target is None else value[target]
                if action == "extra":
                    record["hiddenAuthority"] = True
                else:
                    del record[next(iter(record))]
                with self.subTest(target=target, action=action):
                    self.rejects(value)
        for field in ("context", "tools", "allowedComponentPaths"):
            value = make_manifest()
            value[field] = {}
            self.rejects(value)
        for row, field in (("source", "origin"), ("context", "trust")):
            value = make_manifest()
            record = value["source"]["selectedInputs"][0] if row == "source" else value["context"][0]
            record[field] = []
            self.rejects(value)

    def test_capability_expansion_and_implicit_unknown_hosts_refuse(self):
        for field in ("maxNativeSessions", "maxModelSessions", "maxChildProcesses",
                      "maxNetworkConnections", "maxAdditionalCashMicros", "maxAutomaticRetries"):
            value = make_manifest()
            value["limits"][field] = 1
            self.rejects(value)
        for field in ("kind", "executableSha256", "build"):
            value = make_manifest()
            value["host"][field] = "native"
            self.rejects(value)
        for part, field in (("requested", "route"), ("requested", "model"),
                            ("observed", "provider"), ("observed", "build")):
            value = make_manifest()
            value["host"][part][field] = "paid-or-unqualified"
            self.rejects(value)
        for field in ("profile", "format", "executionAuthorization"):
            value = make_manifest()
            value[field] = True
            self.rejects(value)
        value = make_manifest()
        del value["host"]["observed"]["model"]
        self.rejects(value)

    def test_integer_budgets_tightening_and_raw_byte_limit(self):
        for bad in (True, False, 1.0, -1, 33, "1", None):
            value = make_manifest()
            value["limits"]["maxFiles"] = bad
            self.rejects(value)
        value = make_manifest()
        value["limits"].update(maxFiles=1, maxContextEntries=1)
        self.assertEqual(self.parse(value).data["limits"]["maxFiles"], 1)
        raw = canonical(make_manifest())
        self.assertEqual(manifests.parse_manifest(raw + b" " * (manifests.MAX_BYTES - len(raw))).sha256,
                         self.parse(make_manifest()).sha256)
        with self.assertRaisesRegex(manifests.ManifestError, "^input-budget-exceeded$"):
            manifests.parse_manifest(raw + b" " * (manifests.MAX_BYTES + 1 - len(raw)))
        value = make_manifest()
        value["limits"]["maxManifestBytes"] = 32
        self.rejects(value)

    def test_inventory_digests_sizes_paths_aliases_and_surface_are_checked(self):
        for path in ("../secret", "/outside", "a//b", "a/./b", "a/../b", "a\\b",
                     "a/b/c/d/e", "a*", "a\x00b", "e\u0301.md", "a\u202eb"):
            value = make_manifest()
            value["source"]["selectedInputs"][0]["path"] = path
            self.rejects(value)
        for name in ("base", "candidate"):
            value = make_manifest()
            value[name]["sha256"] = "f" * 64
            self.rejects(value)
            value = make_manifest()
            value[name]["files"][0]["path"] = "other.md"
            value[name]["sha256"] = digest(value[name]["files"])
            self.rejects(value)
        for bad in (True, -1, 32_769, "12"):
            value = make_manifest()
            value["source"]["selectedInputs"][0]["sizeBytes"] = bad
            self.rejects(value)
        value = make_manifest()
        value["source"]["selectedInputs"] *= 2
        self.rejects(value)
        value = make_manifest()
        extra = deepcopy(value["source"]["selectedInputs"][0])
        extra["path"] = "TASK.txt"
        value["source"]["selectedInputs"].insert(0, extra)
        self.rejects(value)
        value = make_manifest()
        value["limits"].update(maxFileBytes=16, maxCandidateBytes=16)
        value["source"]["selectedInputs"] = [
            {"path": f"{i}.txt", "sha256": "a" * 64, "sizeBytes": 10, "origin": "committed"}
            for i in range(2)]
        self.rejects(value)

    def test_context_trust_order_and_total_budget(self):
        value = make_manifest()
        for index in range(1, 3):
            extra = deepcopy(value["context"][0])
            extra.update(id=f"context-{index + 1}", path=f"notes/{index}.txt")
            value["context"].append(extra)
        original = self.parse(value)
        value["context"].reverse()
        self.assertNotEqual(self.parse(value).bindings["context"], original.bindings["context"])
        for field, bad in (("trust", "hidden-grader"), ("selected", 1),
                           ("sizeBytes", 131_073)):
            changed = make_manifest()
            changed["context"][0][field] = bad
            self.rejects(changed)
        changed = make_manifest()
        changed["context"] *= 2
        self.rejects(changed)
        value["context"][0]["sizeBytes"] = 131_072
        self.rejects(value)

    def test_effect_inventory_namespaces_no_globs_or_aliases(self):
        for kind, bad in (("read", "source/secret.txt"), ("read", "context/hidden.txt"),
                          ("read", "base/other.md"), ("read", "candidate/other.md"),
                          ("read", "lab/task.txt"), ("write", "source/task.txt"),
                          ("delete", "context/notes/context.txt"), ("write", "lab/../escape"),
                          ("write", "lab/*"), ("write", "lab//alias"),
                          ("write", "lab/not-in-allowedComponentPaths.md"),
                          ("delete", "lab/not-in-allowedComponentPaths.md")):
            value = make_manifest()
            value["effects"][kind] = [bad]
            with self.subTest(kind=kind, resource=bad):
                self.rejects(value)
        value = make_manifest()
        value["effects"]["write"] = ["lab/A.md", "lab/a.md"]
        self.rejects(value)


if __name__ == "__main__":
    unittest.main()
