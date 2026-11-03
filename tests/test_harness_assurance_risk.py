# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-067 T004: deterministic raise-only risk classifier; pure, offline, advisory."""
import copy
import json
import unittest

from agent_braid import harness_assurance as ha
from agent_braid import harness_assurance_risk as risk
from scripts import validate_change as validation


def impact(*paths):
    return validation.classify(paths)


def classify(paths, lines=10, profile=None):
    return risk.classify_risk(profile or ha.preset("standard"), paths, lines, impact(*paths))


def view(profile=None, documents=None):
    return ha.resolve(profile or ha.preset("standard"), documents)


def row(resolved, checkpoint="pre-pr-review"):
    return next(r for r in resolved["checkpoints"] if r["checkpoint"] == checkpoint)


def with_rule(profile, **kw):
    rule = {"id": "r1", "match": {"paths": ["agent_braid/x.py"], "minChangedLines": 0},
            "raiseTo": "R3", "modeAtLeast": "notify"}
    rule.update(kw)
    profile["riskRules"] = [rule]
    return profile


def repo_settings(**entry):
    return {"repository": {"schema": ha.SETTINGS_FORMAT, "scope": "repository",
                           "checkpoints": {"pre-pr-review": entry}}}


class DefaultRuleTests(unittest.TestCase):
    def test_sensitive_path_raises_to_r3_with_reason(self):
        result = classify(["agent_braid/forecast_model.py"])
        self.assertEqual(result["raiseDepthTo"], "R3")
        self.assertEqual(result["riskClass"], "elevated")
        self.assertIn("sensitive-path", [r["rule"] for r in result["reasons"]])

    def test_size_over_400_raises_and_exactly_400_does_not(self):
        self.assertIsNone(classify(["README.md"], 400)["raiseDepthTo"])
        result = classify(["README.md"], 401)
        self.assertEqual(result["raiseDepthTo"], "R3")
        self.assertEqual([r["rule"] for r in result["reasons"]], ["size-over-400"])

    def test_each_shared_file_raises(self):
        for path in risk.SHARED_FILES:
            result = classify([path])
            self.assertEqual(result["raiseDepthTo"], "R3", path)
            self.assertIn("shared-file", [r["rule"] for r in result["reasons"]], path)

    def test_shared_file_set_is_the_founder_q5_set(self):
        self.assertEqual(set(risk.SHARED_FILES), {
            "docs/STATUS.md", "ROADMAP.md", "docs/development/SPEC_MILESTONE_INDEX.md",
            "agent_braid/cli.py", "agent_braid/ownership.py", "docs/development/github-tracking.json"})
        self.assertEqual(risk.SIZE_THRESHOLD, 400)

    def test_no_match_leaves_depth_and_mode(self):
        result = classify(["README.md"], 3)
        self.assertEqual((result["raiseDepthTo"], result["raiseModeTo"], result["reasons"]), (None, None, []))
        applied = risk.apply_risk(view(), result)
        self.assertEqual(row(applied)["depth"], "R2")
        self.assertEqual(row(applied)["depthSource"], "profile")

    def test_docs_only_class_is_reported(self):
        result = classify(["README.md", "docs/guide.md"], 12)
        self.assertTrue(result["docsOnly"])
        self.assertEqual(result["riskClass"], "docs-only")
        self.assertFalse(classify(["agent_braid/cli.py"])["docsOnly"])
        self.assertFalse(classify(["README.md", "agent_braid/harness_assurance.py"])["docsOnly"])
        self.assertFalse(classify(["docs/adr/0011.md"])["docsOnly"])  # sensitive docs are not docs-only

    def test_docs_only_with_a_big_diff_is_elevated(self):
        result = classify(["README.md"], 900)
        self.assertTrue(result["docsOnly"])
        self.assertEqual(result["riskClass"], "elevated")

    def test_empty_diff_is_not_docs_only(self):
        result = risk.classify_risk(ha.preset("standard"), [], 0, impact())
        self.assertFalse(result["docsOnly"])
        self.assertEqual(result["riskClass"], "ordinary")


class OperatorRuleTests(unittest.TestCase):
    def test_operator_rule_matches_path_and_lines(self):
        quiet = ["docs/note.md"]
        profile = with_rule(ha.preset("standard"), match={"paths": ["docs/**"], "minChangedLines": 50},
                            modeAtLeast="approve-each")
        self.assertEqual((classify(quiet, 49, profile)["raiseDepthTo"], classify(quiet, 49, profile)["raiseModeTo"]),
                         (None, None))
        result = classify(quiet, 50, profile)
        self.assertEqual((result["raiseDepthTo"], result["raiseModeTo"]), ("R3", "approve-each"))
        self.assertIn("r1", [r["rule"] for r in result["reasons"]])

    def test_operator_rule_below_profile_depth_or_mode_is_refused(self):
        strict = ha.preset("strict")  # R3 / approve-each
        for kw in ({"raiseTo": "R2"}, {"modeAtLeast": "notify"}):
            bad = with_rule(copy.deepcopy(strict), **kw)
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.classify_risk(bad, ["README.md"], 1, impact("README.md"))
            self.assertEqual(ctx.exception.reason, "invalid-risk-rule")
            with self.assertRaises(ha.AssuranceError):
                risk.check_raise_only(bad)
        risk.check_raise_only(with_rule(copy.deepcopy(strict), raiseTo="R3", modeAtLeast="approve-each"))
        risk.check_raise_only(ha.preset("standard"))

    def test_rule_below_effective_depth_or_mode_leaves_configured_value(self):
        profile = with_rule(ha.preset("lite"), match={"paths": ["README.md"], "minChangedLines": 0},
                            raiseTo="R2", modeAtLeast="notify")  # valid against lite (R1, autonomous)
        resolved = view(profile, repo_settings(depth="R4", mode="approve-each"))
        applied = risk.apply_risk(resolved, classify(["README.md"], 1, profile))
        self.assertEqual((row(applied)["depth"], row(applied)["mode"]), ("R4", "approve-each"))
        self.assertEqual(row(applied)["depthSource"], "repository")
        self.assertEqual(row(applied)["modeSource"], "repository")

    def test_operator_rule_named_like_a_default_cannot_replace_it(self):
        for name in ("sensitive-path", "size-over-400", "shared-file"):
            profile = with_rule(ha.preset("standard"), id=name, match={"paths": ["agent_braid/**"], "minChangedLines": 0},
                                raiseTo="R2", modeAtLeast="notify")
            result = classify(["agent_braid/cli.py"], 500, profile)
            self.assertEqual(result["raiseDepthTo"], "R3")
            self.assertEqual(len([x for x in result["reasons"] if x["rule"] == name]), 2)

    def test_glob_pattern_rule(self):
        profile = with_rule(ha.preset("standard"), match={"paths": ["docs/*.md"], "minChangedLines": 0})
        self.assertEqual(classify(["docs/a.md"], 1, profile)["raiseDepthTo"], "R3")
        self.assertIsNone(classify(["README.md"], 1, profile)["raiseDepthTo"])

    def test_rule_mode_raise_picks_an_allowed_mode(self):
        profile = with_rule(ha.preset("lite"), match={"paths": ["README.md"], "minChangedLines": 0},
                            raiseTo="R1", modeAtLeast="standing-authorization")
        applied = risk.apply_risk(view(profile), classify(["README.md"], 1, profile))
        self.assertEqual(row(applied)["mode"], "approve-each")  # pre-pr-review does not admit standing-authorization
        self.assertEqual(row(applied)["modeSource"], "risk")


class ApplyTests(unittest.TestCase):
    def test_raise_to_r3_records_source_and_reason(self):
        resolved = view()
        applied = risk.apply_risk(resolved, classify(["agent_braid/ownership.py"]))
        self.assertEqual(row(applied)["depth"], "R3")
        self.assertEqual(row(applied)["depthSource"], "risk")
        self.assertEqual(applied["risk"]["riskClass"], "elevated")
        self.assertEqual(row(resolved)["depth"], "R2")  # input untouched

    def test_never_lowers_depth_or_mode_for_any_result(self):
        for name in ha.PRESETS:
            profile = ha.preset(name)
            resolved = view(profile)
            for paths, lines in ((["README.md"], 1), (["agent_braid/cli.py"], 900), (["agent_braid/x.py"], 1)):
                applied = risk.apply_risk(resolved, classify(paths, lines, profile))
                for before, after in zip(resolved["checkpoints"], applied["checkpoints"]):
                    self.assertGreaterEqual(ha.MODES.index(after["mode"]), ha.MODES.index(before["mode"]))
                    if "depth" in before:
                        self.assertGreaterEqual(ha.DEPTHS.index(after["depth"]), ha.DEPTHS.index(before["depth"]))

    def test_only_pre_pr_review_changes_and_floors_hold(self):
        resolved = view()
        applied = risk.apply_risk(resolved, classify(["agent_braid/cli.py"], 900))
        for before, after in zip(resolved["checkpoints"], applied["checkpoints"]):
            if before["checkpoint"] != "pre-pr-review":
                self.assertEqual(before, after)
        self.assertFalse(applied["executionAuthorization"])

    def test_r4_stays_r4(self):
        resolved = view(documents={"user": {"schema": ha.SETTINGS_FORMAT, "scope": "user",
                                            "checkpoints": {"pre-pr-review": {"depth": "R4"}}}})
        applied = risk.apply_risk(resolved, classify(["agent_braid/cli.py"]))
        self.assertEqual(row(applied)["depth"], "R4")
        self.assertEqual(row(applied)["depthSource"], "user")

    def test_malformed_resolved_view_is_refused(self):
        good = classify(["README.md"])
        broken = view()
        broken["checkpoints"] = [r for r in broken["checkpoints"] if r["checkpoint"] != "pre-pr-review"]
        for bad in ({}, {"schema": ha.RESOLVED_FORMAT}, broken, None):
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.apply_risk(bad, good)
            self.assertEqual(ctx.exception.reason, "invalid-diff-summary")

    def test_forged_classification_is_refused(self):
        resolved = view()
        good = classify(["README.md"])
        for bad in (dict(good, paths=["../x"]), dict(good, changedLines=-1), dict(good, riskClass="x"),
                    dict(good, docsOnly=1), dict(good, reasons=[{"rule": "a", "raiseTo": "R9", "modeAtLeast": None}]),
                    {}, dict(good, raiseDepthTo="R9"), dict(good, schema="x"), dict(good, raiseModeTo="bogus"),
                    dict(good, executionAuthorization=True), dict(good, extra=1)):
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.apply_risk(resolved, bad)
            self.assertEqual(ctx.exception.reason, "invalid-diff-summary")


class ClassificationConsistencyTests(unittest.TestCase):
    """F2: the supplied classification must agree with itself, so docsOnly cannot lower the required reviews."""

    def test_internally_inconsistent_classifications_are_refused(self):
        resolved = view()
        code = classify(["agent_braid/harness_lab.py"])
        docs = classify(["README.md"])
        rule = {"rule": "a", "raiseTo": "R2", "modeAtLeast": "notify"}
        for bad in (dict(code, docsOnly=True),  # code diff claimed as docs-only while elevated... and unraised below
                    dict(docs, riskClass="ordinary"), dict(docs, riskClass="elevated"),
                    dict(docs, docsOnly=False),  # docs-only class without docsOnly
                    dict(docs, paths=[], docsOnly=True),
                    dict(docs, reasons=[rule]),  # reason without the matching raise values
                    dict(docs, reasons=[rule], raiseDepthTo="R3", raiseModeTo="notify", riskClass="elevated"),
                    dict(docs, reasons=[rule], raiseDepthTo="R2", raiseModeTo=None, riskClass="elevated"),
                    dict(docs, raiseDepthTo="R3", riskClass="elevated"),
                    dict(code, reasons=[dict(rule, rule="b"), rule], raiseDepthTo="R2", raiseModeTo="notify")):
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.apply_risk(resolved, bad)
            self.assertEqual(ctx.exception.reason, "invalid-diff-summary")

    def test_residual_a_self_consistent_docs_only_claim_is_not_recomputed_from_the_diff(self):
        forged = dict(classify(["agent_braid/harness_lab.py"]), docsOnly=True, riskClass="docs-only", reasons=[],
                      raiseDepthTo=None, raiseModeTo=None)
        # residual: nothing here sees the diff, so only recomputing classify_risk from it can contradict this claim
        self.assertTrue(ha.compile_artifact(ha.preset("standard"), None, forged)["reviews"]["docsOnly"])

    def test_every_classifier_output_is_consistent(self):
        for paths in (["README.md"], ["agent_braid/cli.py"], ["agent_braid/harness_lab.py", "README.md"], ["docs/x.md"]):
            for lines in (0, 10, 500):
                risk.apply_risk(view(), classify(paths, lines))


class InputTests(unittest.TestCase):
    def test_invalid_summaries_are_refused_with_a_fixed_reason(self):
        profile = ha.preset("standard")
        cases = [(["/etc/passwd"], 1), (["../x"], 1), (["a\\b"], 1), ([""], 1), (["a//b"], 1), ([3], 1),
                 ("README.md", 1), (["README.md"], -1), (["README.md"], True), (["README.md"], 1.5),
                 (["README.md"], ha.MAX_LINES + 1), ([f"f{i}" for i in range(risk.MAX_PATHS + 1)], 1)]
        for paths, lines in cases:
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.classify_risk(profile, paths, lines, None)
            self.assertEqual(ctx.exception.reason, "invalid-diff-summary", (paths, lines))

    def test_invalid_impact_is_refused(self):
        class Fake:
            sensitive = "yes"
            domains = ()
            paths = ("README.md",)
        for bad in (None, object(), Fake()):
            with self.assertRaises(ha.AssuranceError) as ctx:
                risk.classify_risk(ha.preset("standard"), ["README.md"], 1, bad)
            self.assertEqual(ctx.exception.reason, "invalid-diff-summary")

    def test_invalid_profile_is_refused_whole(self):
        with self.assertRaises(ha.AssuranceError):
            risk.classify_risk({}, ["README.md"], 1, impact("README.md"))

    def test_impact_must_describe_the_same_paths(self):
        with self.assertRaises(ha.AssuranceError) as ctx:
            risk.classify_risk(ha.preset("standard"), ["README.md"], 1, impact("agent_braid/cli.py"))
        self.assertEqual(ctx.exception.reason, "invalid-diff-summary")

    def test_paths_are_normalized_sorted_and_deduplicated(self):
        result = classify(["docs/b.md", "./docs/a.md", "docs/b.md"])
        self.assertEqual(result["paths"], ["docs/a.md", "docs/b.md"])


class DeterminismTests(unittest.TestCase):
    def test_repeated_and_reordered_input_is_byte_identical(self):
        paths = ["agent_braid/cli.py", "README.md", "docs/STATUS.md"]
        a = json.dumps(classify(paths, 500), sort_keys=True)
        b = json.dumps(classify(list(reversed(paths)), 500), sort_keys=True)
        self.assertEqual(a, b)
        self.assertEqual(a, json.dumps(classify(paths, 500), sort_keys=True))

    def test_inputs_are_not_mutated_and_advisory_only(self):
        profile = with_rule(ha.preset("standard"), match={"paths": ["docs/**"], "minChangedLines": 0})
        before = copy.deepcopy(profile)
        result = classify(["docs/x.md"], 1, profile)
        self.assertEqual(profile, before)
        self.assertFalse(result["executionAuthorization"])
        self.assertEqual(result["schema"], risk.RISK_FORMAT)

    def test_loader_uses_the_repository_classifier(self):
        loaded = risk.repository_impact(["agent_braid/cli.py", "README.md"])
        self.assertTrue(loaded.sensitive)
        self.assertEqual(loaded, impact("agent_braid/cli.py", "README.md"))


if __name__ == "__main__":
    unittest.main()
