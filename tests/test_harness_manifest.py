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


def make_native_manifest() -> dict:
    """Return a valid native-claude-laboratory wire fixture; nothing runs from it."""
    value = make_manifest()
    value.update(
        profile=manifests.NATIVE_PROFILE,
        host={"kind": "claude", "executableSha256": "a" * 64, "build": "2.1.292",
              "requested": {"model": "haiku", "effort": "low", "route": "subscription"},
              "observed": {"provider": None, "model": None, "build": None, "route": None}},
        containment={"backend": "macos-sandbox-exec", "qualificationSha256": "b" * 64},
        hostQualificationSha256="c" * 64, limits=thaw(manifests.NATIVE_LIMITS))
    return value


def offline_corpus() -> dict:
    """Offline manifests and single/multi-fault variants frozen by SC-001 goldens."""
    def variant(change):
        value = make_manifest()
        change(value)
        return canonical(value)

    def setter(*path, to):
        def change(value):
            for key in path[:-1]:
                value = value[key]
            value[path[-1]] = to
        return change

    def remover(*path):
        def change(value):
            for key in path[:-1]:
                value = value[key]
            del value[path[-1]]
        return change

    def faults(*changes):
        def change(value):
            for item in changes:
                item(value)
        return change

    corpus = {"valid": canonical(make_manifest()),
              "valid-indented": json.dumps(make_manifest(), indent=2).encode()}
    for key in sorted(make_manifest()):
        corpus["missing-" + key] = variant(remover(key))
    for key in ("containment", "hostQualificationSha256", "hiddenAuthority"):
        corpus["extra-" + key] = variant(setter(key, to="a" * 64))
    for key in ("format", "profile", "executionAuthorization"):
        corpus["true-" + key] = variant(setter(key, to=True))
    for key, bad in (("profile", ["offline-foundations"]), ("profile", {}), ("format", [])):
        corpus[f"{type(bad).__name__}-{key}"] = variant(setter(key, to=bad))
    for profile in ("native", "native-claude", "Offline-Foundations", "native-claude-laboratory"):
        corpus["profile-" + profile] = variant(setter("profile", to=profile))
    for key in sorted(manifests.DEFAULT_LIMITS):
        corpus["limit-" + key] = variant(setter("limits", key, to=1 if key != "cashCurrency" else "USD"))
    for key, bad in (("kind", "claude"), ("executableSha256", "a" * 64), ("build", "2.1.292")):
        corpus["host-" + key] = variant(setter("host", key, to=bad))
    corpus["host-route-subscription"] = variant(setter("host", "requested", "route", to="subscription"))
    corpus["host-model"] = variant(setter("host", "requested", "model", to="haiku"))
    corpus["host-observed"] = variant(setter("host", "observed", "provider", to="anthropic"))

    multi = {
        "extra-and-format": (setter("hiddenAuthority", to=True), setter("format", to="x")),
        "format-and-profile": (setter("format", to="x"), setter("profile", to="x")),
        "profile-and-limits": (setter("profile", to="x"), setter("limits", "maxFiles", to=99)),
        "authorization-and-host": (setter("executionAuthorization", to=True),
                                   setter("host", "kind", to="claude")),
        "limits-and-host": (setter("limits", "maxNativeSessions", to=1),
                            setter("host", "kind", to="claude")),
        "native-keys-and-native-profile": (
            setter("profile", to="native-claude-laboratory"),
            setter("containment", to={"backend": "x", "qualificationSha256": "a" * 64})),
        "native-profile-and-format": (setter("profile", to="native-claude-laboratory"),
                                      setter("format", to="x")),
        "native-keys-offline-profile": (
            setter("containment", to={"backend": "x", "qualificationSha256": "a" * 64}),
            setter("hostQualificationSha256", to="a" * 64)),
        "native-host-and-limits": (
            setter("host", "kind", to="claude"), setter("host", "build", to="2.1.292"),
            setter("host", "requested", "route", to="subscription"),
            setter("limits", "maxChildProcesses", to=16)),
    }
    for name, changes in multi.items():
        corpus["multi-" + name] = variant(faults(*changes))
    return corpus


def corpus_outcomes(corpus: dict) -> dict:
    """Bytes, digest, view and binding identity or fixed refusal for each case."""
    outcomes = {}
    for name, raw in corpus.items():
        try:
            result = manifests.parse_manifest(raw)
        except manifests.ManifestError as exc:
            outcomes[name] = {"raw": sha256(raw).hexdigest(), "refusal": exc.reason}
        else:
            outcomes[name] = {"raw": sha256(raw).hexdigest(), "sha256": result.sha256,
                              "view": digest(result.to_dict()),
                              "bindings": dict(result.bindings)}
    return outcomes


# Computed with the pre-SPEC-065 parser (develop e1677c1d); SC-001 requires equality.
OFFLINE_GOLDEN_CASES = 65
OFFLINE_GOLDEN_SHA256 = "17ff237893c23585fefdd16fca875d8d9e5fc6b582041015504ec33186e68772"


class HarnessManifestTests(unittest.TestCase):
    def test_offline_goldens_are_unchanged(self):
        outcomes = corpus_outcomes(offline_corpus())
        self.assertEqual(len(outcomes), OFFLINE_GOLDEN_CASES)
        self.assertEqual(digest(outcomes), OFFLINE_GOLDEN_SHA256)

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

    def assert_reason(self, value, reason):
        with self.assertRaises(manifests.ManifestError) as caught:
            self.parse(value)
        self.assertEqual(caught.exception.reason, reason)

    def test_write_and_delete_effects_are_confined_to_lab_namespace(self):
        # The path is an allowed component, so only the namespace can refuse it.
        for kind in ("write", "delete"):
            for namespace in ("source", "base", "candidate", "context"):
                value = make_manifest()
                value["effects"][kind] = [namespace + "/guidance/main.md"]
                with self.subTest(kind=kind, namespace=namespace):
                    self.assert_reason(value, "effect-outside-inventory")
            value = make_manifest()
            value["effects"][kind] = ["lab/guidance/main.md"]
            self.parse(value)

    def test_base_and_candidate_inventories_stay_inside_allowed_surface(self):
        for name in ("base", "candidate"):
            value = make_manifest()
            value[name]["files"][0]["path"] = "guidance/other.md"
            value[name]["sha256"] = digest(value[name]["files"])
            value["effects"]["read"][value["effects"]["read"].index(
                name + "/guidance/main.md")] = name + "/guidance/other.md"
            with self.subTest(name=name):
                self.assert_reason(value, "path-outside-surface")


class NativeManifestTests(unittest.TestCase):
    def assert_reason(self, value, reason):
        with self.assertRaises(manifests.ManifestError) as caught:
            manifests.parse_manifest(canonical(value))
        self.assertEqual(caught.exception.reason, reason)

    def test_founder_caps_and_offline_constants(self):
        self.assertEqual(manifests.PROFILE, "offline-foundations")
        self.assertEqual(manifests.NATIVE_PROFILE, "native-claude-laboratory")
        self.assertEqual(set(manifests.NATIVE_LIMITS), set(manifests.DEFAULT_LIMITS))
        native = {"maxNativeSessions": 1, "maxModelSessions": 1, "maxChildProcesses": 16,
                  "maxNetworkConnections": 8, "maxAdditionalCashMicros": 0,
                  "maxAutomaticRetries": 0}
        for key, value in manifests.NATIVE_LIMITS.items():
            with self.subTest(key=key):
                self.assertEqual(value, native.get(key, manifests.DEFAULT_LIMITS[key]))

    def test_valid_native_manifest_parses_without_authority(self):
        value = make_native_manifest()
        result = manifests.parse_manifest(canonical(value))
        self.assertEqual(result.to_dict(), value)
        self.assertEqual(set(result.bindings), manifests.BINDING_NAMES)
        self.assertFalse(result.data["executionAuthorization"])
        verified = manifests.verify_manifest(canonical(value), expected_sha256=result.sha256,
                                             expected_bindings=result.bindings)
        self.assertEqual(verified.sha256, result.sha256)
        for model, effort in ((None, None), ("claude-opus-5-5", "high")):
            value["host"]["requested"].update(model=model, effort=effort)
            manifests.parse_manifest(canonical(value))
        tightened = make_native_manifest()
        tightened["limits"]["maxChildProcesses"] = 1
        manifests.parse_manifest(canonical(tightened))

    def test_full_identity_binds_native_containment_and_host_qualification(self):
        original = manifests.parse_manifest(canonical(make_native_manifest()))
        for change in (lambda v: v["containment"].update(backend="other"),
                       lambda v: v["containment"].update(qualificationSha256="d" * 64),
                       lambda v: v.update(hostQualificationSha256="d" * 64),
                       lambda v: v["host"].update(executableSha256="d" * 64)):
            value = make_native_manifest()
            change(value)
            with self.assertRaisesRegex(manifests.ManifestError, "^manifest-drift$"):
                manifests.verify_manifest(canonical(value), expected_sha256=original.sha256,
                                          expected_bindings={})

    def test_unknown_or_missing_native_fields_refuse(self):
        for target in (None, "host", "containment", "limits"):
            for action in ("extra", "missing"):
                value = make_native_manifest()
                record = value if target is None else value[target]
                if action == "extra":
                    record["hiddenAuthority"] = True
                else:
                    del record[next(iter(record))]
                with self.subTest(target=target, action=action):
                    self.assert_reason(value, "invalid-manifest")
        for part in ("requested", "observed"):
            value = make_native_manifest()
            value["host"][part]["hiddenAuthority"] = None
            self.assert_reason(value, "invalid-manifest")
        for key in ("containment", "hostQualificationSha256"):
            value = make_native_manifest()
            del value[key]
            with self.subTest(key=key):
                self.assert_reason(value, "invalid-manifest")

    def test_any_limit_above_founder_cap_refuses(self):
        for key, cap in manifests.NATIVE_LIMITS.items():
            if key == "cashCurrency":
                continue
            value = make_native_manifest()
            value["limits"][key] = cap + 1
            with self.subTest(key=key):
                self.assert_reason(value, "invalid-budget")
        for key in ("maxNativeSessions", "maxModelSessions", "maxChildProcesses",
                    "maxNetworkConnections"):
            value = make_native_manifest()
            value["limits"][key] = 0
            with self.subTest(key=key, value=0):
                self.assert_reason(value, "invalid-budget")
        value = make_native_manifest()
        value["limits"]["cashCurrency"] = "USD"
        self.assert_reason(value, "unsupported-profile")

    def test_host_route_build_and_authority_negative_controls(self):
        unsupported, invalid = "unsupported-profile", "invalid-manifest"
        cases = [
            (("requested", "route"), "offline", unsupported),
            (("requested", "route"), "api-key", unsupported),
            (("requested", "route"), None, unsupported),
            (("kind",), "offline", unsupported), (("kind",), "codex", unsupported),
            (("build",), "2.1.293", unsupported), (("build",), "2.1.29", unsupported),
            (("build",), None, unsupported),
            (("executableSha256",), None, invalid), (("executableSha256",), "A" * 64, invalid),
            (("requested", "model"), "bad model", invalid), (("requested", "effort"), 1, invalid),
            (("observed", "provider"), "anthropic", unsupported),
            (("observed", "route"), "subscription", unsupported),
        ]
        for path, bad, reason in cases:
            value = make_native_manifest()
            record = value["host"]
            for key in path[:-1]:
                record = record[key]
            record[path[-1]] = bad
            with self.subTest(path=path, bad=bad):
                self.assert_reason(value, reason)
        value = make_native_manifest()
        value["executionAuthorization"] = True
        self.assert_reason(value, "unsupported-profile")
        for field, bad in (("backend", "bad backend"), ("backend", None),
                           ("qualificationSha256", "short")):
            value = make_native_manifest()
            value["containment"][field] = bad
            with self.subTest(field=field):
                self.assert_reason(value, "invalid-manifest")
        value = make_native_manifest()
        value["hostQualificationSha256"] = None
        self.assert_reason(value, "invalid-manifest")

    def test_profile_and_shape_cannot_be_mixed(self):
        native_host = make_native_manifest()["host"]
        offline_host = make_manifest()["host"]
        value = make_manifest()
        value.update(containment={"backend": "macos-sandbox-exec", "qualificationSha256": "b" * 64},
                     hostQualificationSha256="c" * 64)
        self.assert_reason(value, "invalid-manifest")
        value = make_native_manifest()
        value["host"] = offline_host
        self.assert_reason(value, "unsupported-profile")
        value = make_native_manifest()
        value["profile"] = manifests.PROFILE
        self.assert_reason(value, "invalid-manifest")
        value = make_manifest()
        value["profile"] = manifests.NATIVE_PROFILE
        self.assert_reason(value, "unsupported-profile")  # offline shape keeps its old reason
        value = make_manifest()
        value["host"] = native_host
        self.assert_reason(value, "unsupported-profile")
        value = make_native_manifest()
        value["limits"] = thaw(manifests.DEFAULT_LIMITS)
        self.assert_reason(value, "invalid-budget")
        value = make_native_manifest()
        value["format"] = "braid-harness-manifest/v0.2"
        self.assert_reason(value, "unsupported-version")

    def test_shared_inventory_checks_still_apply_to_native(self):
        value = make_native_manifest()
        value["source"]["selectedInputs"][0]["path"] = "../secret"
        self.assert_reason(value, "invalid-path")
        value = make_native_manifest()
        value["effects"]["write"] = ["source/task.txt"]
        self.assert_reason(value, "effect-outside-inventory")


if __name__ == "__main__":
    unittest.main()
