# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-067 assurance profiles: catalog, allowed modes, schema, floors; offline, no authority."""
import copy
import json
import os
import tempfile
import unittest

from agent_braid import harness_assurance as ha


PINNED_STANDARD = "891ab76f56ed326354eef8500a076429892b0964a1ca06e59fd71677ab871033"


def profile(name: str = "standard") -> dict:
    return ha.preset(name)


def refused(case: unittest.TestCase, reason: str, value) -> None:
    with case.assertRaises(ha.AssuranceError) as ctx:
        ha.validate_profile(value)
    case.assertEqual(ctx.exception.reason, reason)
    case.assertIn(reason, ha.REASONS)


class CatalogTests(unittest.TestCase):
    def test_catalog_is_the_closed_set_of_req_001(self):
        self.assertEqual(ha.CHECKPOINTS, (
            "intake-spec", "clarification", "plan-tasks", "track-dispatch", "implementation", "pre-commit",
            "pre-pr-review", "pr-open", "ci", "merge", "release", "post-merge", "grant", "harness-self-change",
            "auto-promotion", "native-effect"))
        self.assertEqual(ha.ALLOWED_MODES["ci"], ("autonomous", "notify", "approve-each", "human-only"))
        self.assertEqual(ha.ALLOWED_MODES["harness-self-change"], ("human-only",))
        with self.assertRaises(TypeError):
            ha.ALLOWED_MODES["pr-open"] = ha.MODES
        self.assertEqual(set(ha.ALLOWED_MODES), set(ha.CHECKPOINTS))
        self.assertEqual(ha.MODES, ("autonomous", "notify", "standing-authorization", "approve-each", "human-only"))
        self.assertEqual(ha.DEPTHS, ("R0", "R1", "R2", "R3", "R4"))

    def test_floors_allow_only_human_only_and_release_is_a_floor(self):
        self.assertEqual(set(ha.FLOORS), {"release", "clarification", "grant", "native-effect", "auto-promotion"})
        for checkpoint in ha.FLOORS:
            self.assertEqual(ha.ALLOWED_MODES[checkpoint], ("human-only",))

    def test_only_merge_admits_standing_authorization(self):
        admitting = {c for c, modes in ha.ALLOWED_MODES.items() if "standing-authorization" in modes}
        self.assertEqual(admitting, {"merge"})

    def test_no_attribution_checkpoints_are_the_publishing_ones(self):
        self.assertEqual(set(ha.NO_ATTRIBUTION), {"pr-open", "merge", "release", "post-merge"})
        self.assertTrue(set(ha.NO_ATTRIBUTION) <= set(ha.CHECKPOINTS))

    def test_advisory_constant_is_false(self):
        self.assertIs(ha.EXECUTION_AUTHORIZATION, False)


class PresetTests(unittest.TestCase):
    def test_each_preset_is_valid_and_covers_every_checkpoint(self):
        for name in ha.PRESETS:
            value = ha.preset(name)
            self.assertEqual(ha.validate_profile(value), value)
            self.assertEqual(set(value["checkpoints"]), set(ha.CHECKPOINTS))

    def test_q1_defaults(self):
        self.assertEqual(ha.DEFAULT_PRESET, "standard")
        self.assertEqual(ha.PRESETS, ("lite", "standard", "strict"))
        self.assertEqual([ha.preset(n)["checkpoints"]["pre-pr-review"]["depth"] for n in ha.PRESETS],
                         ["R1", "R2", "R3"])

    def test_floors_are_human_only_in_every_preset(self):
        for name in ha.PRESETS:
            for checkpoint in ha.FLOORS:
                self.assertEqual(ha.preset(name)["checkpoints"][checkpoint], {"mode": "human-only"})

    def test_strictness_never_decreases_from_lite_to_strict(self):
        for low, high in (("lite", "standard"), ("standard", "strict")):
            for checkpoint in ha.CHECKPOINTS:
                a = ha.MODES.index(ha.preset(low)["checkpoints"][checkpoint]["mode"])
                b = ha.MODES.index(ha.preset(high)["checkpoints"][checkpoint]["mode"])
                self.assertLessEqual(a, b, (low, high, checkpoint))

    def test_unknown_preset_is_refused_and_copies_are_independent(self):
        for bad in ("", "Standard", None, 3):
            with self.assertRaises(ha.AssuranceError) as ctx:
                ha.preset(bad)
            self.assertEqual(ctx.exception.reason, "unknown-preset")
        first = ha.preset("lite")
        first["checkpoints"]["ci"]["mode"] = "human-only"
        self.assertEqual(ha.preset("lite")["checkpoints"]["ci"]["mode"], "autonomous")


class ViewTests(unittest.TestCase):
    def test_full_profile_compiles_to_a_per_checkpoint_view(self):
        view = ha.profile_view(profile())
        self.assertEqual([row["checkpoint"] for row in view["checkpoints"]], list(ha.CHECKPOINTS))
        for row in view["checkpoints"]:
            self.assertEqual(row["modeSource"], "profile")
            self.assertEqual("depth" in row, row["checkpoint"] == "pre-pr-review")
        pre_pr = next(r for r in view["checkpoints"] if r["checkpoint"] == "pre-pr-review")
        self.assertEqual((pre_pr["depth"], pre_pr["depthSource"]), ("R2", "profile"))
        self.assertEqual(view["noAttribution"], {"checkpoints": list(ha.NO_ATTRIBUTION), "enforced": True})
        self.assertIs(view["executionAuthorization"], False)
        self.assertEqual(view["profile"]["digest"], ha.profile_digest(profile()))

    def test_standard_digest_is_pinned(self):
        self.assertEqual(ha.profile_digest(profile()), PINNED_STANDARD)

    def test_view_and_digest_are_deterministic(self):
        self.assertEqual(json.dumps(ha.profile_view(profile()), sort_keys=True),
                         json.dumps(ha.profile_view(profile()), sort_keys=True))
        self.assertNotEqual(ha.profile_digest(profile("lite")), ha.profile_digest(profile("strict")))

    def test_invalid_profile_yields_no_partial_view(self):
        broken = profile()
        del broken["checkpoints"]["ci"]
        with self.assertRaises(ha.AssuranceError):
            ha.profile_view(broken)


class SchemaNegativeTests(unittest.TestCase):
    def test_unknown_checkpoint(self):
        value = profile()
        value["checkpoints"]["deploy"] = {"mode": "notify"}
        refused(self, "unknown-checkpoint", value)

    def test_missing_checkpoint_each(self):
        for checkpoint in ha.CHECKPOINTS:
            value = profile()
            del value["checkpoints"][checkpoint]
            refused(self, "missing-checkpoint", value)

    def test_unknown_depth_and_non_string_depth(self):
        for bad in ("R5", "r2", "", 2, None, ["R2"]):
            value = profile()
            value["checkpoints"]["pre-pr-review"]["depth"] = bad
            refused(self, "unknown-depth", value)

    def test_pre_pr_review_needs_a_depth(self):
        value = profile()
        del value["checkpoints"]["pre-pr-review"]["depth"]
        refused(self, "missing-depth", value)

    def test_depth_on_any_other_checkpoint(self):
        for checkpoint in ha.CHECKPOINTS:
            if checkpoint == "pre-pr-review":
                continue
            value = profile()
            value["checkpoints"][checkpoint]["depth"] = "R2"
            refused(self, "depth-not-allowed", value)

    def test_unknown_mode_and_missing_mode(self):
        for bad in ("yolo", "", None, 1, ["notify"]):
            value = profile()
            value["checkpoints"]["ci"]["mode"] = bad
            refused(self, "unknown-mode", value)
        value = profile()
        del value["checkpoints"]["ci"]["mode"]
        refused(self, "missing-mode", value)

    def test_disallowed_mode_each_pair(self):
        for checkpoint in ha.CHECKPOINTS:
            if checkpoint in ha.FLOORS:
                continue
            for mode in ha.MODES:
                if mode in ha.ALLOWED_MODES[checkpoint]:
                    continue
                value = profile()
                value["checkpoints"][checkpoint]["mode"] = mode
                refused(self, "mode-not-allowed", value)

    def test_every_floor_must_be_human_only(self):
        for checkpoint in ha.FLOORS:
            for mode in ha.MODES:
                if mode == "human-only":
                    continue
                value = profile()
                value["checkpoints"][checkpoint]["mode"] = mode
                refused(self, "floor-not-human-only", value)

    def test_unknown_keys_at_every_level(self):
        for mutate in (
            lambda v: v.update(extra=1),
            lambda v: v["checkpoints"]["ci"].update(extra=1),
            lambda v: v.update(noAttribution=False),
        ):
            value = profile()
            mutate(value)
            refused(self, "unknown-key", value)

    def test_missing_top_level_key_each(self):
        for key in ("schema", "name", "version", "checkpoints", "riskRules", "standingAuthorizations"):
            value = profile()
            del value[key]
            refused(self, "missing-key", value)

    def test_not_a_mapping(self):
        for bad in (None, [], "profile", 3, (), b"{}"):
            refused(self, "invalid-profile", bad)
        value = profile()
        value["checkpoints"] = []
        refused(self, "invalid-profile", value)
        value = profile()
        value["checkpoints"]["ci"] = "notify"
        refused(self, "invalid-profile", value)

    def test_schema_name_and_version(self):
        value = profile()
        value["schema"] = "braid-harness-assurance-profile/v9"
        refused(self, "unsupported-schema", value)
        for bad in ("", "-x", "a b", 3, None, "x" * 65):
            value = profile()
            value["name"] = bad
            refused(self, "invalid-name", value)
        for bad in (0, -1, 1.0, True, "1", None):
            value = profile()
            value["version"] = bad
            refused(self, "invalid-version", value)

    def test_same_input_same_reason(self):
        value = profile()
        value["checkpoints"]["deploy"] = {"mode": "notify"}
        value["checkpoints"]["release"]["mode"] = "notify"
        del value["checkpoints"]["ci"]
        reasons = set()
        for _ in range(3):
            with self.assertRaises(ha.AssuranceError) as ctx:
                ha.validate_profile(copy.deepcopy(value))
            reasons.add(ctx.exception.reason)
        self.assertEqual(reasons, {"unknown-checkpoint"})

    def test_input_is_not_mutated_and_result_is_independent(self):
        value = profile()
        before = copy.deepcopy(value)
        result = ha.validate_profile(value)
        self.assertEqual(value, before)
        result["checkpoints"]["ci"]["mode"] = "human-only"
        self.assertEqual(value, before)


class RiskRuleAndAuthorizationSchemaTests(unittest.TestCase):
    RULE = {"id": "sensitive", "match": {"paths": ["agent_braid/**"], "minChangedLines": 0},
            "raiseTo": "R3", "modeAtLeast": "autonomous"}

    def test_valid_rule_and_authorization_ids(self):
        value = profile()
        value["riskRules"] = [copy.deepcopy(self.RULE)]
        value["standingAuthorizations"] = ["auth-001", "auth-002"]
        self.assertEqual(ha.validate_profile(value), value)

    def test_invalid_rules(self):
        def with_rule(mutate):
            value = profile()
            rule = copy.deepcopy(self.RULE)
            mutate(rule)
            value["riskRules"] = [rule]
            return value

        for mutate in (
            lambda r: r.update(id=""),
            lambda r: r.update(raiseTo="R9"),
            lambda r: r.update(modeAtLeast="yolo"),
            lambda r: r["match"].update(paths=[]),
            lambda r: r["match"].update(paths=["/abs"]),
            lambda r: r["match"].update(paths=["a/../b"]),
            lambda r: r["match"].update(paths=["a\\b"]),
            lambda r: r["match"].update(paths=["a//b"]),
            lambda r: r["match"].update(paths=["./a"]),
            lambda r: r["match"].update(paths=["a\nb"]),
            lambda r: r["match"].update(minChangedLines=-1),
            lambda r: r["match"].update(minChangedLines=True),
            lambda r: r.pop("raiseTo"),
            lambda r: r["match"].pop("paths"),
        ):
            refused(self, "invalid-risk-rule", with_rule(mutate))
        for mutate in (lambda r: r.update(extra=1), lambda r: r["match"].update(extra=1)):
            refused(self, "unknown-key", with_rule(mutate))

    def test_duplicate_rule_ids_and_bounds(self):
        value = profile()
        value["riskRules"] = [copy.deepcopy(self.RULE), copy.deepcopy(self.RULE)]
        refused(self, "invalid-risk-rule", value)
        value["riskRules"] = [dict(copy.deepcopy(self.RULE), id=f"r{i}") for i in range(ha.MAX_RULES + 1)]
        refused(self, "invalid-risk-rule", value)
        value["riskRules"] = "none"
        refused(self, "invalid-risk-rule", value)

    def test_invalid_standing_authorizations(self):
        too_many = [f"a{i:02d}" for i in range(ha.MAX_AUTHORIZATIONS + 1)]
        for bad in (["b", "a"], ["a", "a"], [""], [3], "a", None, too_many):
            value = profile()
            value["standingAuthorizations"] = bad
            refused(self, "invalid-standing-authorization", value)


class ParseTests(unittest.TestCase):
    def test_round_trip_bytes(self):
        self.assertEqual(ha.parse_profile(json.dumps(profile()).encode()), profile())

    def test_bad_bytes(self):
        for raw in (b"", b"not json", b'{"a":1,"a":2}', b"\xff", json.dumps(profile())):
            with self.assertRaises(ha.AssuranceError) as ctx:
                ha.parse_profile(raw)
            self.assertEqual(ctx.exception.reason, "invalid-json")

    def test_valid_json_invalid_profile(self):
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.parse_profile(b"{}")
        self.assertEqual(ctx.exception.reason, "missing-key")


class SettingsAndResolveTests(unittest.TestCase):
    def doc(self, scope, checkpoints=None, **extra):
        value = {"schema": ha.SETTINGS_FORMAT, "scope": scope}
        if checkpoints is not None:
            value["checkpoints"] = checkpoints
        return {**value, **extra}

    def row(self, resolved, checkpoint):
        return next(r for r in resolved["checkpoints"] if r["checkpoint"] == checkpoint)

    def test_no_documents_equals_the_profile_view(self):
        resolved = ha.resolve(profile())
        view = ha.profile_view(profile())
        self.assertEqual(resolved["checkpoints"], view["checkpoints"])
        self.assertEqual(resolved["refusedLowerings"], [])
        self.assertEqual(resolved["scopeSources"], [])
        self.assertIs(resolved["executionAuthorization"], False)
        self.assertEqual(resolved["noAttribution"], {"checkpoints": list(ha.NO_ATTRIBUTION), "enforced": True})

    def test_precedence_conversation_over_repository_over_user_over_profile(self):
        docs = {
            "user": self.doc("user", {"ci": {"mode": "approve-each"}, "pr-open": {"mode": "autonomous"},
                                      "pre-pr-review": {"depth": "R0"}}),
            "repository": self.doc("repository", {"ci": {"mode": "human-only"},
                                                  "pre-pr-review": {"depth": "R3"}}),
            "conversation": self.doc("conversation", {"ci": {"mode": "autonomous"}}),
        }
        resolved = ha.resolve(profile(), docs)
        self.assertEqual(resolved["scopeSources"], ["conversation", "repository", "user"])
        ci = self.row(resolved, "ci")
        self.assertEqual((ci["mode"], ci["modeSource"]), ("autonomous", "conversation"))
        pr_open = self.row(resolved, "pr-open")
        self.assertEqual((pr_open["mode"], pr_open["modeSource"]), ("autonomous", "user"))
        review = self.row(resolved, "pre-pr-review")
        self.assertEqual((review["depth"], review["depthSource"]), ("R3", "repository"))
        self.assertEqual((review["mode"], review["modeSource"]), ("notify", "profile"))
        self.assertEqual(resolved["refusedLowerings"], [])

    def test_lowering_each_floor_at_each_scope_is_refused_and_recorded(self):
        for scope in ha.SCOPES:
            for floor in ha.FLOORS:
                for mode in ha.MODES:
                    if mode == "human-only":
                        continue
                    resolved = ha.resolve(profile(), {scope: self.doc(scope, {floor: {"mode": mode}})})
                    row = self.row(resolved, floor)
                    self.assertEqual((row["mode"], row["modeSource"]), ("human-only", "profile"))
                    self.assertEqual(resolved["refusedLowerings"], [
                        {"checkpoint": floor, "dimension": "mode", "requested": mode, "scope": scope,
                         "floor": "human-only", "reason": "floor-not-human-only"}])

    def test_floor_holds_when_every_scope_tries_to_lower_it(self):
        docs = {s: self.doc(s, {"release": {"mode": "autonomous"}}) for s in ha.SCOPES}
        resolved = ha.resolve(profile(), docs)
        self.assertEqual(self.row(resolved, "release")["mode"], "human-only")
        self.assertEqual([r["scope"] for r in resolved["refusedLowerings"]], list(ha.SCOPES))

    def test_human_only_for_a_floor_is_not_a_lowering(self):
        resolved = ha.resolve(profile(), {"user": self.doc("user", {"release": {"mode": "human-only"}})})
        self.assertEqual(resolved["refusedLowerings"], [])

    def test_disabling_the_attribution_invariant_is_refused_at_each_scope(self):
        for scope in ha.SCOPES:
            resolved = ha.resolve(profile(), {scope: self.doc(scope, noAttribution=False)})
            self.assertEqual(resolved["refusedLowerings"], [
                {"checkpoint": None, "dimension": "noAttribution", "requested": False, "scope": scope,
                 "floor": True, "reason": "attribution-invariant"}])
            self.assertTrue(resolved["noAttribution"]["enforced"])
            resolved = ha.resolve(profile(), {scope: self.doc(scope, noAttribution=True)})
            self.assertEqual(resolved["refusedLowerings"], [])

    def test_a_refused_lowering_does_not_stop_other_values_of_the_same_document(self):
        doc = self.doc("conversation", {"release": {"mode": "notify"}, "ci": {"mode": "approve-each"}})
        resolved = ha.resolve(profile(), {"conversation": doc})
        self.assertEqual(self.row(resolved, "ci")["mode"], "approve-each")
        self.assertEqual(self.row(resolved, "release")["mode"], "human-only")
        self.assertEqual(len(resolved["refusedLowerings"]), 1)

    def test_standing_authorization_through_a_scope_only_for_merge(self):
        resolved = ha.resolve(profile("strict"), {"user": self.doc("user", {"merge": {"mode": "standing-authorization"}})})
        self.assertEqual(self.row(resolved, "merge")["mode"], "standing-authorization")
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.resolve(profile(), {"user": self.doc("user", {"pr-open": {"mode": "standing-authorization"}})})
        self.assertEqual(ctx.exception.reason, "mode-not-allowed")
        resolved = ha.resolve(profile(), {"user": self.doc("user", {"harness-self-change": {"mode": "approve-each"}})})
        self.assertEqual(self.row(resolved, "harness-self-change")["mode"], "human-only")
        self.assertEqual(resolved["refusedLowerings"][0]["checkpoint"], "harness-self-change")

    def test_malformed_documents_are_refused_whole(self):
        cases = [
            ("scope-mismatch", {"user": self.doc("repository")}),
            ("unknown-scope", {"team": self.doc("user")}),
            ("unknown-scope", {"user": self.doc("team")}),
            ("unknown-checkpoint", {"user": self.doc("user", {"deploy": {"mode": "notify"}})}),
            ("unknown-mode", {"user": self.doc("user", {"ci": {"mode": "yolo"}})}),
            ("unknown-mode", {"user": self.doc("user", {"release": {"mode": "yolo"}})}),
            ("depth-not-allowed", {"user": self.doc("user", {"ci": {"depth": "R1"}})}),
            ("unknown-depth", {"user": self.doc("user", {"pre-pr-review": {"depth": "R9"}})}),
            ("unknown-key", {"user": self.doc("user", {"ci": {"extra": 1}})}),
            ("unknown-key", {"user": self.doc("user", extra=1)}),
            ("invalid-settings", {"user": self.doc("user", {"ci": {}})}),
            ("invalid-settings", {"user": self.doc("user", noAttribution="no")}),
            ("invalid-settings", {"user": "settings"}),
            ("unsupported-schema", {"user": {"schema": "x", "scope": "user"}}),
            ("missing-key", {"user": {"schema": ha.SETTINGS_FORMAT}}),
        ]
        for reason, docs in cases:
            with self.assertRaises(ha.AssuranceError) as ctx:
                ha.resolve(profile(), docs)
            self.assertEqual(ctx.exception.reason, reason, docs)
        with self.assertRaises(ha.AssuranceError):
            ha.resolve({"not": "a profile"}, {})
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.resolve(profile(), [])
        self.assertEqual(ctx.exception.reason, "unknown-scope")

    def test_resolution_is_deterministic_and_does_not_mutate_inputs(self):
        docs = {"user": self.doc("user", {"ci": {"mode": "notify"}}),
                "conversation": self.doc("conversation", {"release": {"mode": "notify"}})}
        before = copy.deepcopy(docs)
        first, second = ha.resolve(profile(), docs), ha.resolve(profile(), docs)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(docs, before)

    def test_parse_settings_bytes(self):
        self.assertEqual(ha.parse_settings(json.dumps(self.doc("user")).encode()), self.doc("user"))
        for raw in (b"", b"x", b'{"a":1,"a":2}'):
            with self.assertRaises(ha.AssuranceError) as ctx:
                ha.parse_settings(raw)
            self.assertEqual(ctx.exception.reason, "invalid-json")


class OperatorFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = os.path.realpath(self.tmp.name)
        self.config = os.path.join(root, "config")
        self.tree = os.path.join(root, "worktree")
        for path in (self.config, self.tree):
            os.mkdir(path, 0o700)
        self.space = ha.OperatorSpace(self.config, (self.tree,))

    def write(self, path, data, mode=0o600):
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
        os.chmod(path, mode)
        return path


class OperatorLoaderTests(OperatorFixture):
    def settings_bytes(self, scope="user", **checkpoints):
        return json.dumps({"schema": ha.SETTINGS_FORMAT, "scope": scope, "checkpoints": checkpoints}).encode()

    def unobservable(self, call):
        with self.assertRaises(ha.AssuranceError) as ctx:
            call()
        self.assertEqual(ctx.exception.reason, "unobservable-source")

    def test_missing_files_yield_nothing(self):
        self.assertIsNone(ha.load_profile(self.space))
        self.assertEqual(ha.load_scope_documents(self.space, repository_digest="a" * 64), {})
        self.assertEqual(ha.load_journal(self.space).journal, ())

    def test_loads_profile_and_all_three_scopes(self):
        self.write(self.space.location(ha.PROFILE_FILE), json.dumps(profile()).encode())
        self.write(self.space.location(ha.SETTINGS_FILE), self.settings_bytes("user", ci={"mode": "notify"}))
        digest = "b" * 64
        self.write(self.space.location(ha.SETTINGS_FILE, digest), self.settings_bytes("repository"))
        self.assertEqual(ha.load_profile(self.space), profile())
        documents = ha.load_scope_documents(self.space, repository_digest=digest,
                                            conversation=self.settings_bytes("conversation"))
        self.assertEqual(set(documents), {"user", "repository", "conversation"})
        self.assertEqual(ha.resolve(profile(), documents)["scopeSources"], ["conversation", "repository", "user"])

    def test_group_or_other_writable_file_is_refused(self):
        path = self.write(self.space.location(ha.SETTINGS_FILE), self.settings_bytes(), 0o620)
        self.unobservable(lambda: ha.load_scope_documents(self.space))
        os.chmod(path, 0o602)
        self.unobservable(lambda: ha.load_scope_documents(self.space))

    def test_symlink_is_refused(self):
        target = self.write(os.path.join(self.config, "elsewhere.json"), self.settings_bytes())
        link = self.space.location(ha.SETTINGS_FILE)
        os.makedirs(os.path.dirname(link))
        os.symlink(target, link)
        self.unobservable(lambda: ha.load_scope_documents(self.space))

    def test_symlinked_directory_leaving_the_config_directory_is_refused(self):
        outside = os.path.join(os.path.dirname(self.config), "outside")
        self.write(os.path.join(outside, ha.SETTINGS_FILE), self.settings_bytes())
        os.symlink(outside, os.path.join(self.config, ha.ASSURANCE_DIRECTORY))
        self.unobservable(lambda: ha.load_scope_documents(self.space))

    def test_file_inside_a_working_tree_is_refused(self):
        inside = ha.OperatorSpace(self.config, (self.config,))
        self.write(inside.location(ha.PROFILE_FILE), json.dumps(profile()).encode())
        self.unobservable(lambda: ha.load_profile(inside))
        agent_file = self.write(os.path.join(self.tree, "profile.json"), json.dumps(profile()).encode())
        self.unobservable(lambda: ha.read_operator_file(agent_file, self.space))

    def test_directory_and_oversize_are_refused(self):
        os.makedirs(self.space.location(ha.SETTINGS_FILE))
        self.unobservable(lambda: ha.load_scope_documents(self.space))
        big = self.write(self.space.location(ha.JOURNAL_FILE), b" " * (ha.MAX_BYTES + 1))
        self.unobservable(lambda: ha.read_operator_file(big, self.space))

    def test_invalid_repository_digest_is_refused(self):
        self.unobservable(lambda: ha.load_scope_documents(self.space, repository_digest="../x"))

    def test_malformed_content_is_refused_with_its_own_reason(self):
        self.write(self.space.location(ha.SETTINGS_FILE), b"{}")
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.load_scope_documents(self.space)
        self.assertEqual(ctx.exception.reason, "missing-key")


class JournalTests(OperatorFixture):
    def change(self, at, kind="human", who="founder", source=None):
        return ha.Change(kind, who, at, source)

    def versioned(self, version, name="standard", **changes):
        value = profile()
        value["name"], value["version"] = name, version
        for checkpoint, mode in changes.items():
            value["checkpoints"][checkpoint.replace("_", "-")]["mode"] = mode
        return value

    def adopt(self, journal, value, at):
        journal = journal.begin(value, self.change(at), self.space).journal
        outcome = journal.commit(self.change(at + 1), self.space)
        self.assertIsNone(outcome.refusal)
        return outcome.journal

    def test_human_change_is_versioned_and_the_previous_stays_restorable(self):
        v1, v2 = self.versioned(1), self.versioned(2, ci="human-only")
        journal = self.adopt(ha.ProfileJournal(), v1, 1)
        self.assertEqual(journal.active_profile, v1)
        journal = self.adopt(journal, v2, 3)
        self.assertEqual(journal.active_profile, v2)
        self.assertEqual(journal.previous, (ha.profile_digest(v1),))
        restored = journal.rollback(self.change(5), self.space, reason="regression").journal
        self.assertEqual(restored.active_profile, v1)
        self.assertEqual(restored.journal[-1]["event"], "rolled-back")
        emptied = restored.rollback(self.change(6), self.space, reason="again").journal
        self.assertIsNone(emptied.active_profile)

    def test_begin_alone_does_not_change_the_active_profile(self):
        journal = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        pending = journal.begin(self.versioned(2), self.change(3), self.space).journal
        self.assertEqual(pending.active_profile, self.versioned(1))
        self.assertEqual(pending.pending, ha.profile_digest(self.versioned(2)))
        aborted = pending.abort(self.change(4), self.space, reason="changed-mind").journal
        self.assertEqual(aborted.active_profile, self.versioned(1))
        self.assertIsNone(aborted.pending)

    def test_agent_like_identities_are_refused_and_recorded(self):
        base = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        for kind in ("agent", "model", "tool"):
            outcome = base.begin(self.versioned(2), self.change(5, kind, "claude"), self.space)
            self.assertEqual(outcome.refusal, "agent-identity")
            self.assertEqual(outcome.journal.active, base.active)
            self.assertIsNone(outcome.journal.pending)
            last = outcome.journal.journal[-1]
            self.assertEqual((last["event"], last["reason"], last["actor"]["kind"]), ("refused", "agent-identity", kind))

    def test_agent_cannot_commit_abort_or_roll_back_its_own_pending_change(self):
        base = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        pending = base.begin(self.versioned(2), self.change(3), self.space).journal
        agent = self.change(4, "agent", "claude")
        for outcome in (pending.commit(agent, self.space), pending.abort(agent, self.space, reason="x"),
                        base.rollback(agent, self.space, reason="x")):
            self.assertEqual(outcome.refusal, "agent-identity")
        self.assertEqual(pending.commit(agent, self.space).journal.active, base.active)
        self.assertEqual(pending.commit(agent, self.space).journal.pending, pending.pending)

    def test_agent_writable_sources_are_refused_and_recorded(self):
        sources = [os.path.join(self.tree, "profile.json"), os.path.join(os.path.dirname(self.config), "other.json"),
                   os.path.join(self.config, "..", "worktree", "x.json")]
        for source in sources:
            outcome = ha.ProfileJournal().begin(self.versioned(1), self.change(1, source=source), self.space)
            self.assertEqual(outcome.refusal, "agent-writable-source", source)
            self.assertIsNone(outcome.journal.active)
            self.assertEqual(outcome.journal.journal[-1]["event"], "refused")
        owned = os.path.join(self.config, ha.ASSURANCE_DIRECTORY, "profile.json")
        self.assertIsNone(ha.ProfileJournal().begin(self.versioned(1), self.change(1, source=owned), self.space).refusal)

    def test_registered_version_cannot_be_edited_in_place_or_reregistered(self):
        journal = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        for edited in (self.versioned(1, ci="human-only"), self.versioned(1)):
            with self.assertRaises(ha.AssuranceError) as ctx:
                journal.begin(edited, self.change(5), self.space)
            self.assertEqual(ctx.exception.reason, "version-not-newer")
        edited = json.loads(journal.to_bytes())
        key = next(iter(edited["profiles"]))
        edited["profiles"][key]["checkpoints"]["ci"]["mode"] = "human-only"
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.ProfileJournal.from_bytes(ha.canonical(edited))
        self.assertEqual(ctx.exception.reason, "profile-hash-mismatch")

    def test_forged_journals_are_refused(self):
        journal = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        for mutate in (
            lambda d: d["journal"][1]["actor"].update(kind="agent"),
            lambda d: d["journal"].pop(0),
            lambda d: d["journal"][1].update(seq=7),
            lambda d: d["journal"][1].update(at=0),
            lambda d: d["journal"][0].update(subject="f" * 64),
            lambda d: d["journal"][1].update(reason="x"),
            lambda d: d["journal"].append(dict(d["journal"][1], seq=2, at=9)),
            lambda d: d.update(profiles={}),
        ):
            forged = json.loads(journal.to_bytes())
            mutate(forged)
            with self.assertRaises(ha.AssuranceError):
                ha.ProfileJournal.from_bytes(ha.canonical(forged))

    def test_refusal_is_recorded_before_state_checks_and_has_its_own_cap(self):
        agent = self.change(5, "agent", "claude")
        empty = ha.ProfileJournal()
        for outcome in (empty.commit(agent, self.space), empty.rollback(agent, self.space, reason="x"),
                        empty.abort(agent, self.space, reason="x")):
            self.assertEqual(outcome.refusal, "agent-identity")
            self.assertEqual(outcome.journal.journal[-1]["subject"], None)
        pending = empty.begin(self.versioned(1), self.change(1), self.space).journal
        self.assertEqual(pending.begin(self.versioned(2), agent, self.space).refusal, "agent-identity")
        flooded = empty
        for i in range(ha.MAX_JOURNAL):
            flooded = flooded.commit(self.change(5 + i, "agent", "claude"), self.space).journal
        with self.assertRaises(ha.AssuranceError) as ctx:
            flooded.commit(self.change(9999, "agent", "claude"), self.space)
        self.assertEqual(ctx.exception.reason, "journal-full")
        self.assertIsNone(self.adopt(flooded, self.versioned(1), 9999).pending)

    def test_group_writable_or_foreign_files_cannot_be_operator_input(self):
        path = self.write(self.space.location(ha.PROFILE_FILE), json.dumps(profile()).encode(), 0o666)
        with self.assertRaises(ha.AssuranceError):
            ha.load_profile(self.space)
        self.assertTrue(path)

    def test_state_machine_refusals(self):
        empty = ha.ProfileJournal()
        for call, reason in (
            (lambda: empty.commit(self.change(1), self.space), "no-transaction"),
            (lambda: empty.abort(self.change(1), self.space, reason="x"), "no-transaction"),
            (lambda: empty.rollback(self.change(1), self.space, reason="x"), "no-active-profile"),
        ):
            with self.assertRaises(ha.AssuranceError) as ctx:
                call()
            self.assertEqual(ctx.exception.reason, reason)
        pending = empty.begin(self.versioned(1), self.change(1), self.space).journal
        with self.assertRaises(ha.AssuranceError) as ctx:
            pending.begin(self.versioned(2), self.change(2), self.space)
        self.assertEqual(ctx.exception.reason, "transaction-pending")
        with self.assertRaises(ha.AssuranceError) as ctx:
            pending.commit(self.change(0), self.space)
        self.assertEqual(ctx.exception.reason, "time-regression")
        for bad, reason in ((ha.Change("human", "x", -1), "invalid-time"), (ha.Change("robot", "x", 1), "invalid-actor"),
                            (ha.Change("human", "bad id", 1), "invalid-actor"), ("change", "invalid-actor")):
            with self.assertRaises(ha.AssuranceError) as ctx:
                empty.begin(self.versioned(1), bad, self.space)
            self.assertEqual(ctx.exception.reason, reason)
        with self.assertRaises(ha.AssuranceError) as ctx:
            self.adopt(empty, self.versioned(1), 1).rollback(self.change(5), self.space, reason="bad reason!")
        self.assertEqual(ctx.exception.reason, "invalid-reason")
        with self.assertRaises(ha.AssuranceError):
            empty.begin({"not": "a profile"}, self.change(1), self.space)

    def test_codec_round_trip_and_canonical_only(self):
        journal = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        refused = journal.begin(self.versioned(2), self.change(5, "agent", "claude"), self.space).journal
        decoded = ha.ProfileJournal.from_bytes(refused.to_bytes())
        self.assertEqual((decoded.to_bytes(), decoded.sha256, decoded.active), (refused.to_bytes(), refused.sha256, refused.active))
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.ProfileJournal.from_bytes(json.dumps(json.loads(refused.to_bytes()), indent=1).encode())
        self.assertEqual(ctx.exception.reason, "non-canonical")
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.ProfileJournal.from_bytes(b"[]")
        self.assertEqual(ctx.exception.reason, "invalid-json")
        for raw in (b'{"format":1}', ha.canonical({"format": ha.JOURNAL_FORMAT, "profiles": [], "journal": []})):
            with self.assertRaises(ha.AssuranceError):
                ha.ProfileJournal.from_bytes(raw)

    def test_save_and_load_and_concurrent_update(self):
        first = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        ha.save_journal(self.space, first)
        path = self.space.location(ha.JOURNAL_FILE)
        self.assertEqual(os.stat(path).st_mode & 0o077, 0)
        self.assertEqual(ha.load_journal(self.space).to_bytes(), first.to_bytes())
        second = self.adopt(first, self.versioned(2), 3)
        ha.save_journal(self.space, second)
        self.assertEqual(ha.load_journal(self.space).active_profile, self.versioned(2))
        with self.assertRaises(ha.AssuranceError) as ctx:
            ha.save_journal(self.space, first)
        self.assertEqual(ctx.exception.reason, "concurrent-update")
        with self.assertRaises(ha.AssuranceError):
            ha.save_journal(self.space, "journal")

    def test_resolve_from_the_journaled_active_profile(self):
        journal = self.adopt(ha.ProfileJournal(), self.versioned(1), 1)
        resolved = ha.resolve(journal.active_profile)
        self.assertEqual(resolved["profile"]["digest"], journal.active)
        self.assertIs(resolved["executionAuthorization"], False)


if __name__ == "__main__":
    unittest.main()
