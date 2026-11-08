# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for the SPEC-050/T002 component registry and compiler."""
import ast
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_components as hc
from agent_braid.system_one import canonical, digest

MODULE = Path(hc.__file__)


def file_row(path, content, op="add"):
    return {"path": path, "sha256": sha256(content).hexdigest(),
            "sizeBytes": len(content), "op": op}


def original():
    return {"origin": "original", "file": None, "revision": None, "sha256": None,
            "terms": None, "noticesRetained": None, "modificationNotice": None}


def make_inventory(entries=None, **over):
    entries = entries if entries is not None else [
        file_row("guidance/main.md", b"Use a bounded handoff.\n")]
    value = {"format": hc.INVENTORY_FORMAT, "componentClass": "C1", "host": "claude",
             "hostBuild": "2.1.292", "version": 1, "parentSha256": None,
             "entries": entries, "entriesSha256": digest(entries), "effectClass": "E0",
             "settings": {"model": None, "effort": None, "route": None},
             "provenance": original(), "executionAuthorization": False}
    value.update(over)
    return value


def _compile(value, **kwargs):
    expected = kwargs.pop("expected_input_sha256", sha256(canonical(value)).hexdigest())
    return hc.compile_inventory(json.dumps(value).encode(), expected_input_sha256=expected,
                                **kwargs)


class ComponentProfileTests(unittest.TestCase):
    def refuses(self, reason, value=None, **kwargs):
        with self.assertRaises(hc.ProfileError) as caught:
            _compile(value if value is not None else make_inventory(), **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def refuses_profile(self, reason, data):
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(data))
        self.assertEqual(caught.exception.reason, reason)

    def child(self, parent, entries, **over):
        return make_inventory(entries, version=parent.version + 1,
                              parentSha256=parent.sha256, **over)

    def parent_profile(self):
        return _compile(make_inventory([
            file_row("guidance/a.md", b"a"), file_row("guidance/b.md", b"b"),
            file_row("guidance/d.md", b"d")]))

    # --- positive controls -------------------------------------------------
    def test_compiles_immutable_non_enabled_profile(self):
        profile = _compile(make_inventory())
        data = profile.to_dict()
        self.assertEqual(data["format"], "braid-harness-profile/v0.1")
        self.assertEqual(data["admission"], {"state": "implemented", "blocker": None})
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual(data["hostSupport"]["claude"]["qualification"], "unqualified")
        self.assertEqual(data["hostSupport"]["codex"]["observedBuild"], None)
        with self.assertRaises(FrozenInstanceError):
            profile.data = {}
        with self.assertRaises(TypeError):
            profile.data["admission"]["state"] = "enabled"
        data["admission"]["state"] = "enabled"
        self.assertEqual(profile.data["admission"]["state"], "implemented")

    def test_compile_is_deterministic_and_round_trips(self):
        first, second = _compile(make_inventory()), _compile(make_inventory())
        self.assertEqual(first.canonical_bytes, second.canonical_bytes)
        self.assertEqual(hc.parse_profile(first.canonical_bytes).sha256, first.sha256)
        self.assertEqual(hc.verify_profile(first.canonical_bytes,
                                           expected_sha256=first.sha256).sha256, first.sha256)

    def test_inheritance_override_add_and_explicit_delete(self):
        parent = self.parent_profile()
        rows = [file_row("guidance/a.md", b"a", "inherit"),
                file_row("guidance/b.md", b"b2", "override"),
                file_row("guidance/c.md", b"c", "add"),
                file_row("guidance/d.md", b"d", "delete")]
        profile = _compile(self.child(parent, rows), parent_raw=parent.canonical_bytes,
                           expected_parent_sha256=parent.sha256)
        data = profile.to_dict()
        self.assertEqual([r["path"] for r in data["inventory"]],
                         ["guidance/a.md", "guidance/b.md", "guidance/c.md"])
        self.assertEqual(data["inventory"][1]["sha256"], sha256(b"b2").hexdigest())
        self.assertEqual(data["deleted"], ["guidance/d.md"])
        self.assertEqual(data["parentSha256"], parent.sha256)
        self.assertEqual(data["version"], 2)

    def test_no_class_or_effect_reaches_qualified_or_enabled(self):
        expected = {"C1": "implemented", "C2": "implemented"}
        for cls in hc.CLASSES:
            for effect in ("E0", "E1", "E2", "E3", "E4"):
                state, blocker = hc.derive_admission(cls, effect)
                self.assertNotIn(state, ("qualified", "enabled", "excluded"))
                if cls in ("C6", "C7", "C8"):
                    self.assertEqual((state, blocker), ("blocked", "no-containment-qualification"))
                elif effect in ("E3", "E4"):
                    self.assertEqual((state, blocker), ("blocked", "effects-not-adopted"))
                elif cls in expected:
                    self.assertEqual((state, blocker), ("implemented", None))
                else:
                    self.assertEqual((state, blocker), ("blocked", "owner-task-unimplemented"))

    def test_blocked_classes_compile_visibly_as_blocked(self):
        for cls, root in hc.ROOTS.items():
            if cls in ("C1", "C2"):
                continue
            entries = [file_row(f"{root}/x.md", b"inert")]
            profile = _compile(make_inventory(entries, componentClass=cls))
            self.assertEqual(profile.data["admission"]["state"], "blocked", cls)
            self.assertIsNotNone(profile.data["admission"]["blocker"], cls)

    def test_settings_selected_only_within_approved_profile(self):
        approved = {"models": ["haiku"], "efforts": ["low"], "routes": ["subscription"]}
        sha = digest(approved)
        value = make_inventory(settings={"model": "haiku", "effort": "low",
                                         "route": "subscription"})
        profile = _compile(value, approved_settings=approved, expected_approved_sha256=sha)
        self.assertEqual(profile.data["approvedSettingsSha256"], sha)
        self.assertEqual(profile.data["settings"]["model"], "haiku")

    def test_adapted_provenance_requires_complete_notices(self):
        adapted = {"origin": "adapted", "file": "core/tree.py", "revision": "1" * 40,
                   "sha256": "2" * 64, "terms": "Apache-2.0", "noticesRetained": True,
                   "modificationNotice": True}
        self.assertEqual(_compile(make_inventory(provenance=adapted)).data["provenance"], adapted)

    # --- negative controls: forged, stale, unknown, escalation -------------
    def test_forged_inventory_digest_refuses(self):
        value = make_inventory()
        value["entriesSha256"] = "0" * 64
        self.refuses("inventory-digest-mismatch", value)

    def test_input_drift_against_trusted_hash_refuses(self):
        self.refuses("input-drift", expected_input_sha256="0" * 64)
        self.refuses("invalid-expected-hash", expected_input_sha256="ABC")

    def test_forged_or_tampered_profile_refuses(self):
        profile = _compile(make_inventory())
        with self.assertRaises(hc.ProfileError) as caught:
            hc.verify_profile(profile.canonical_bytes, expected_sha256="0" * 64)
        self.assertEqual(caught.exception.reason, "profile-drift")
        tampered = profile.to_dict()
        tampered["inventory"][0]["sha256"] = "0" * 64
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(tampered))
        self.assertEqual(caught.exception.reason, "inventory-digest-mismatch")

    def test_unknown_and_refused_hosts(self):
        self.refuses("unknown-host", make_inventory(host="gemini"))
        self.refuses("host-refused", make_inventory(host="codex"))
        self.refuses("host-build-drift", make_inventory(hostBuild="2.1.300"))

    def test_unknown_class_and_effects(self):
        self.refuses("unknown-class", make_inventory(componentClass="C9"))
        self.refuses("excluded-effect", make_inventory(effectClass="E5"))
        self.refuses("invalid-effect", make_inventory(effectClass="E9"))

    def test_state_escalation_attempts_refuse(self):
        self.refuses("invalid-profile", make_inventory(admission={"state": "enabled"}))  # unknown key
        profile = _compile(make_inventory()).to_dict()
        for state in ("enabled", "qualified"):
            forged = deepcopy(profile)
            forged["admission"]["state"] = state
            with self.assertRaises(hc.ProfileError) as caught:
                hc.parse_profile(canonical(forged))
            self.assertEqual(caught.exception.reason, "state-escalation")
        forged = deepcopy(profile)
        forged["admission"]["state"] = "excluded"
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(forged))
        self.assertEqual(caught.exception.reason, "admission-mismatch")
        forged = deepcopy(profile)
        forged["hostSupport"]["claude"]["qualification"] = "a" * 64
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(forged))
        self.assertEqual(caught.exception.reason, "state-escalation")

    def test_hook_plugin_and_role_profiles_cannot_be_unblocked(self):
        profile = _compile(make_inventory([file_row("eventnotes/x.md", b"hook")],
                                          componentClass="C6")).to_dict()
        profile["admission"] = {"state": "implemented", "blocker": None}
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(profile))
        self.assertEqual(caught.exception.reason, "admission-mismatch")

    def test_native_effects_stay_blocked(self):
        profile = _compile(make_inventory(effectClass="E3")).to_dict()
        self.assertEqual(profile["admission"],
                         {"state": "blocked", "blocker": "effects-not-adopted"})

    def test_execution_authorization_must_be_false(self):
        self.refuses("unsupported-profile", make_inventory(executionAuthorization=True))
        profile = _compile(make_inventory()).to_dict()
        profile["executionAuthorization"] = True
        self.refuses_profile("unsupported-profile", profile)

    def test_stale_and_future_versions(self):
        self.refuses("unsupported-version", make_inventory(format="braid-harness-inventory/v0.2"))
        self.refuses("future-version", make_inventory(version=2))
        self.refuses("invalid-version", make_inventory(version=0))
        self.refuses("invalid-version", make_inventory(version=True))
        profile = _compile(make_inventory()).to_dict()
        profile["format"] = "braid-harness-profile/v0.2"
        with self.assertRaises(hc.ProfileError) as caught:
            hc.parse_profile(canonical(profile))
        self.assertEqual(caught.exception.reason, "unsupported-version")
        parent = self.parent_profile()
        rows = [file_row("guidance/a.md", b"a", "inherit"), file_row("guidance/b.md", b"b", "inherit"),
                file_row("guidance/d.md", b"d", "inherit")]
        kwargs = dict(parent_raw=parent.canonical_bytes, expected_parent_sha256=parent.sha256)
        self.refuses("stale-version", make_inventory(rows, version=1, parentSha256=parent.sha256),
                     **kwargs)
        self.refuses("future-version", make_inventory(rows, version=3, parentSha256=parent.sha256),
                     **kwargs)

    def test_stale_or_forged_parent(self):
        parent = self.parent_profile()
        rows = [file_row(p, c, "inherit") for p, c in
                (("guidance/a.md", b"a"), ("guidance/b.md", b"b"), ("guidance/d.md", b"d"))]
        kwargs = dict(parent_raw=parent.canonical_bytes, expected_parent_sha256=parent.sha256)
        self.refuses("stale-parent", make_inventory(rows, version=2, parentSha256="0" * 64),
                     **kwargs)
        self.refuses("stale-parent", make_inventory(rows, version=2), **kwargs)
        self.refuses("stale-parent", make_inventory(version=1, parentSha256=parent.sha256))
        self.refuses("profile-drift", self.child(parent, rows), parent_raw=parent.canonical_bytes,
                     expected_parent_sha256="0" * 64)
        self.refuses("invalid-expected-hash", self.child(parent, rows),
                     parent_raw=parent.canonical_bytes)
        other = _compile(make_inventory([file_row("lessons/a.md", b"a")], componentClass="C2"))
        self.refuses("parent-mismatch", self.child(other, [file_row("lessons/a.md", b"a", "inherit")]),
                     parent_raw=other.canonical_bytes, expected_parent_sha256=other.sha256)

    def test_inheritance_and_deletion_semantics_refuse(self):
        parent = self.parent_profile()
        kwargs = dict(parent_raw=parent.canonical_bytes, expected_parent_sha256=parent.sha256)
        keep = [file_row("guidance/a.md", b"a", "inherit"), file_row("guidance/b.md", b"b", "inherit")]
        d_inherit = file_row("guidance/d.md", b"d", "inherit")
        self.refuses("silent-omission", self.child(parent, keep), **kwargs)
        self.refuses("inherit-drift", self.child(parent, keep + [file_row("guidance/d.md", b"x", "inherit")]), **kwargs)
        self.refuses("delete-mismatch", self.child(parent, keep + [file_row("guidance/d.md", b"x", "delete")]), **kwargs)
        self.refuses("override-unchanged", self.child(parent, keep + [file_row("guidance/d.md", b"d", "override")]), **kwargs)
        self.refuses("path-exists", self.child(parent, [file_row("guidance/a.md", b"a")] + keep[1:] + [d_inherit]), **kwargs)
        self.refuses("path-missing", self.child(parent, keep + [d_inherit, file_row("guidance/e.md", b"e", "inherit")]), **kwargs)
        self.refuses("path-missing", make_inventory([file_row("guidance/a.md", b"a", "inherit")]))
        self.refuses("empty-inventory", self.child(parent, [
            file_row("guidance/a.md", b"a", "delete"), file_row("guidance/b.md", b"b", "delete"),
            file_row("guidance/d.md", b"d", "delete")]), **kwargs)
        bad_op = make_inventory([dict(file_row("guidance/a.md", b"a"), op="rename")])
        self.refuses("invalid-op", bad_op)

    def test_protected_layers_take_precedence(self):
        for name in ("guidance/settings.md", "guidance/Hooks.md", "guidance/AGENTS.md",
                     "guidance/.hidden.md", "guidance/permissions/x.md", "guidance/verifier.txt"):
            self.refuses("protected-component",
                         make_inventory([file_row(name, b"x")]))

    def test_paths_outside_the_positive_surface_refuse(self):
        for name in ("other/x.md", "guidance/x.py", "guidance.md", "lessons/x.md"):
            self.refuses("path-outside-surface", make_inventory([file_row(name, b"x")]))
        for name in ("../guidance/x.md", "guidance/../x.md", "/guidance/x.md",
                     "guidance/a/b/c/d.md", "guidance/́x.md"[:0] + "guidance/a:b.md"):
            self.refuses("invalid-path", make_inventory([file_row(name, b"x")]))

    def test_alias_unordered_and_unbounded_inventories_refuse(self):
        self.refuses("path-alias", make_inventory([file_row("guidance/A.md", b"x"),
                                                    file_row("guidance/a.md", b"x")]))
        self.refuses("duplicate-or-unordered-inventory", make_inventory(
            [file_row("guidance/b.md", b"x"), file_row("guidance/a.md", b"x")]))
        many = [file_row(f"guidance/f{i:02d}.md", b"x") for i in range(33)]
        self.refuses("inventory-budget-exceeded", make_inventory(many))
        self.refuses("inventory-budget-exceeded", make_inventory(
            [file_row("guidance/big.md", b"x" * 32_769)]))
        big = [file_row(f"guidance/f{i}.md", b"x" * 32_768) for i in range(9)]
        self.refuses("inventory-budget-exceeded", make_inventory(big))
        with self.assertRaises(hc.ProfileError) as caught:
            hc.compile_inventory(b"{" + b" " * 1_048_577, expected_input_sha256="0" * 64)
        self.assertEqual(caught.exception.reason, "input-budget-exceeded")
        with self.assertRaises(hc.ProfileError) as caught:
            hc.compile_inventory(b'{"a":1,"a":2}', expected_input_sha256="0" * 64)
        self.assertEqual(caught.exception.reason, "invalid-json")

    def test_settings_outside_or_without_approved_profile_refuse(self):
        approved = {"models": ["haiku"], "efforts": ["low"], "routes": ["subscription"]}
        sha = digest(approved)
        value = make_inventory(settings={"model": "haiku", "effort": None, "route": None})
        self.refuses("settings-not-approved", value)
        self.refuses("settings-outside-approved", make_inventory(
            settings={"model": "opus", "effort": None, "route": None}),
            approved_settings=approved, expected_approved_sha256=sha)
        self.refuses("approved-settings-drift", value, approved_settings=approved,
                     expected_approved_sha256="0" * 64)
        self.refuses("approved-settings-drift", value, approved_settings=approved)
        paid = {"models": ["haiku"], "efforts": ["low"], "routes": ["api-key"]}
        self.refuses("approved-settings-drift", make_inventory(
            settings={"model": None, "effort": None, "route": "subscription"}),
            approved_settings=paid, expected_approved_sha256=digest(paid))
        self.refuses("invalid-settings", make_inventory(
            settings={"model": None, "effort": None, "route": "api-key"}),
            approved_settings=approved, expected_approved_sha256=sha)
        self.refuses("invalid-settings", make_inventory(settings={"model": "haiku"}))

    def test_incomplete_adapted_provenance_refuses(self):
        adapted = {"origin": "adapted", "file": "core/tree.py", "revision": "1" * 40,
                   "sha256": "2" * 64, "terms": "Apache-2.0", "noticesRetained": True,
                   "modificationNotice": True}
        for field in ("noticesRetained", "modificationNotice"):
            self.refuses("invalid-provenance",
                         make_inventory(provenance=dict(adapted, **{field: False})))
        self.refuses("invalid-provenance", make_inventory(provenance=dict(adapted, revision="abc")))
        self.refuses("invalid-provenance", make_inventory(provenance=dict(original(), file="x")))
        self.refuses("invalid-provenance", make_inventory(provenance=dict(adapted, origin="unknown")))

    def test_unknown_fields_and_future_minor_refuse(self):
        self.refuses("invalid-profile", make_inventory(extra=1))
        profile = _compile(make_inventory()).to_dict()
        profile["extra"] = 1
        self.refuses_profile("invalid-profile", profile)

    def test_forged_profiles_fail_every_consumer_side_check(self):
        base = _compile(make_inventory()).to_dict()

        def forged(reason, mutate):
            data = deepcopy(base)
            mutate(data)
            self.refuses_profile(reason, data)

        forged("stale-parent", lambda d: d.update(parentSha256="a" * 64))
        forged("stale-parent", lambda d: d.update(version=2))
        forged("stale-parent", lambda d: d.update(deleted=["guidance/x.md"]))
        forged("host-build-drift", lambda d: d["hostSupport"]["claude"].update(observedBuild="9"))
        forged("host-build-drift", lambda d: d["hostSupport"]["codex"].update(observedBuild="1"))
        forged("host-refused", lambda d: d.update(host="codex"))
        forged("unknown-host", lambda d: d.update(host="gemini"))
        forged("invalid-settings", lambda d: d.update(approvedSettingsSha256="a" * 64))
        forged("invalid-settings", lambda d: d["settings"].update(model="haiku"))
        forged("unsupported-profile", lambda d: d["limits"].update(maxFiles=32.0))
        forged("unsupported-profile", lambda d: d["schemas"].update(tools=["x"]))
        forged("unsupported-profile", lambda d: d["policies"].update(content="code"))
        forged("excluded-effect", lambda d: d.update(effectClass="E5"))
        forged("protected-component", lambda d: d["inventory"][0].update(path="guidance/hooks.md"))
        two = deepcopy(base)
        two.update(version=2, parentSha256="a" * 64, deleted=["guidance/MAIN.md"])
        self.refuses_profile("path-alias", two)
        two["deleted"] = ["guidance/z.md", "guidance/y.md"]
        self.refuses_profile("duplicate-or-unordered-inventory", two)
        two["deleted"] = ["other/z.md"]
        self.refuses_profile("path-outside-surface", two)

    def test_verify_profile_rechecks_approved_settings(self):
        approved = {"models": ["haiku"], "efforts": ["low"], "routes": ["subscription"]}
        sha = digest(approved)
        profile = _compile(make_inventory(settings={"model": "haiku", "effort": None,
                                                    "route": None}),
                           approved_settings=approved, expected_approved_sha256=sha)
        args = dict(expected_sha256=profile.sha256)
        hc.verify_profile(profile.canonical_bytes, **args, approved_settings=approved,
                          expected_approved_sha256=sha)
        for kwargs in ({}, {"approved_settings": approved},
                       {"approved_settings": approved, "expected_approved_sha256": "0" * 64}):
            with self.assertRaises(hc.ProfileError) as caught:
                hc.verify_profile(profile.canonical_bytes, **args, **kwargs)
            self.assertIn(caught.exception.reason, ("approved-settings-drift", "settings-not-approved"))
        other = {"models": ["opus"], "efforts": [], "routes": []}
        with self.assertRaises(hc.ProfileError):
            hc.verify_profile(profile.canonical_bytes, **args, approved_settings=other,
                              expected_approved_sha256=digest(other))
        with self.assertRaises(hc.ProfileError) as caught:
            hc.verify_profile(profile.canonical_bytes, expected_sha256="x")
        self.assertEqual(caught.exception.reason, "invalid-expected-hash")

    def test_malformed_approved_settings_never_leak_non_profile_errors(self):
        value = make_inventory(settings={"model": "haiku", "effort": None, "route": None})
        for bad in ({"models": {"haiku"}, "efforts": [], "routes": []},
                    {"models": [object()], "efforts": [], "routes": []},
                    {"models": [float("nan")], "efforts": [], "routes": []}):
            self.refuses("approved-settings-drift", value, approved_settings=bad,
                         expected_approved_sha256="0" * 64)

    def test_hidden_alias_spellings_and_provenance_paths_refuse(self):
        for name in ("guidance/tests .md", "guidance/tests\u3000.md", "guidance/hooks .md",
                     "guidance/a\u2028b.md"):
            self.assertRaises(hc.ProfileError, _compile, make_inventory([file_row(name, b"x")]))
        adapted = {"origin": "adapted", "file": "../x", "revision": "1" * 40, "sha256": "2" * 64,
                   "terms": "Apache-2.0", "noticesRetained": True, "modificationNotice": True}
        self.refuses("invalid-provenance", make_inventory(provenance=adapted))
        self.refuses("invalid-profile", make_inventory(entries="x"))

    def test_boundary_budgets_and_recreation_after_delete_compile(self):
        limits = hc.LIMITS
        rows = [file_row(f"guidance/f{i}.md", b"x" * limits["maxFileBytes"])
                for i in range(limits["maxCandidateBytes"] // limits["maxFileBytes"])]
        self.assertEqual(len(_compile(make_inventory(rows)).data["inventory"]), 8)
        many = [file_row(f"guidance/f{i:02d}.md", b"x") for i in range(limits["maxFiles"])]
        self.assertEqual(len(_compile(make_inventory(many, effectClass="E4")).data["inventory"]), 32)
        parent = _compile(make_inventory([file_row("guidance/a.md", b"a"), file_row("guidance/b.md", b"b")]))
        kw = dict(parent_raw=parent.canonical_bytes, expected_parent_sha256=parent.sha256)
        mid = _compile(self.child(parent, [file_row("guidance/a.md", b"a", "delete"),
                                           file_row("guidance/b.md", b"b", "inherit")]), **kw)
        again = _compile(self.child(mid, [file_row("guidance/a.md", b"a2"),
                                          file_row("guidance/b.md", b"b", "inherit")]),
                         parent_raw=mid.canonical_bytes, expected_parent_sha256=mid.sha256)
        self.assertEqual(len(again.data["deleted"]), 0)
        self.assertEqual(again.version, 3)

    def test_protected_set_is_the_surface_set(self):
        self.assertTrue({"hooks", "settings", "tests", "agents"} <= hc.PROTECTED_COMPONENTS)

    def test_module_is_pure(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        self.assertFalse(imported & {"os", "subprocess", "socket", "urllib", "http", "shutil",
                                     "pathlib", "ctypes", "multiprocessing", "threading"})
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {"open", "exec", "eval", "compile", "__import__"})


if __name__ == "__main__":
    unittest.main()
