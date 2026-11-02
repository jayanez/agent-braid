# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-067 assurance profiles: catalog, allowed modes, schema, floors; offline, no authority."""
import copy
import json
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


if __name__ == "__main__":
    unittest.main()
