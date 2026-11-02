# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-067 T007: deterministic track-brief section and PR "Pre-PR review" skeleton; pure, offline, advisory."""
import copy
import unittest

from agent_braid import harness_assurance as ha
from agent_braid import harness_assurance_render as render
from agent_braid import harness_assurance_risk as risk
from scripts import validate_change as validation

BRIEF = dict(ownership="SPEC-067 modules", isolation="own worktree", model="Sonnet 5.5", effort="medium")


def artifact(depth=None, docs_only=True, profile="standard", documents=None):
    prof = ha.preset(profile)
    cls = risk.classify_risk(prof, ["README.md"], 10, validation.classify(["README.md"]))
    if not docs_only:  # every code path is sensitive for the real classifier, so state an ordinary class directly
        cls = {**cls, "docsOnly": False, "riskClass": "ordinary"}
    if depth is not None:
        documents = {"repository": {"schema": ha.SETTINGS_FORMAT, "scope": "repository",
                                    "checkpoints": {"pre-pr-review": {"depth": depth}}}}
    return ha.compile_artifact(prof, documents, cls)


def brief(art):
    return render.track_brief_section(art, **BRIEF)


def refused(case, reason, call, *args, **kwargs):
    with case.assertRaises(ha.AssuranceError) as ctx:
        call(*args, **kwargs)
    case.assertEqual(ctx.exception.reason, reason)
    case.assertIn(reason, ha.REASONS)


def resealed(art, **changes):
    body = {**{k: v for k, v in art.items() if k != "digest"}, **changes}
    return {**body, "digest": ha.digest(body)}


ALL_KINDS = {kind for ladder in (ha.CODE_LADDER, ha.DOCS_LADDER) for kinds in ladder.values() for kind in kinds}


class DeterminismTests(unittest.TestCase):
    def test_equal_input_gives_byte_identical_output(self):
        for depth in (None, "R0", "R1", "R3", "R4"):
            first, second = artifact(depth), artifact(depth)
            self.assertEqual(brief(first), brief(second))
            self.assertEqual(render.pre_pr_review_block(first), render.pre_pr_review_block(second))

    def test_rendering_does_not_mutate_and_ignores_key_insertion_order(self):
        art = artifact("R4", docs_only=False)
        before = copy.deepcopy(art)
        first = (brief(art), render.pre_pr_review_block(art))
        self.assertEqual(art, before)
        reordered = {key: art[key] for key in reversed(list(art))}
        reordered["reviews"] = {key: art["reviews"][key] for key in reversed(list(art["reviews"]))}
        self.assertEqual((brief(reordered), render.pre_pr_review_block(reordered)), first)
        self.assertEqual((brief(art), render.pre_pr_review_block(art)), first)

    def test_output_ends_with_one_newline_and_has_no_trailing_spaces(self):
        for text in (brief(artifact()), render.pre_pr_review_block(artifact())):
            self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
            self.assertFalse(any(line != line.rstrip() for line in text.splitlines()))


class PrBlockTests(unittest.TestCase):
    def test_golden_docs_only_r2_block(self):
        art = artifact()
        self.assertEqual(render.pre_pr_review_block(art), f"""## Pre-PR review

Depth R2, documentation-only change; compiled artifact `{art['digest']}`.

### accuracy-review

- Findings applied: _pending_
- Findings rejected, with reason: _pending_

### claim-discipline-review

- Findings applied: _pending_
- Findings rejected, with reason: _pending_

### concision-review

- Findings applied: _pending_
- Findings rejected, with reason: _pending_
""")

    def test_lists_exactly_the_required_reviews_at_every_depth(self):
        for depth in ha.DEPTHS:
            for docs in (True, False):
                art = artifact(depth, docs_only=docs)
                text = render.pre_pr_review_block(art)
                headings = [line[4:] for line in text.splitlines() if line.startswith("### ")]
                self.assertEqual(headings, list(ha.required_reviews(depth, docs)), (depth, docs))
                for kind in ALL_KINDS - set(headings):  # a review the depth does not require is never named
                    self.assertNotIn(kind, text, (depth, docs))

    def test_r0_states_that_no_review_is_required(self):
        text = render.pre_pr_review_block(artifact("R0"))
        self.assertIn("No review is required at this depth.", text)
        self.assertNotIn("###", text)

    def test_r4_names_the_independent_reviewer_rule_once(self):
        text = render.pre_pr_review_block(artifact("R4", docs_only=False))
        self.assertEqual(text.count("Reviewers (at least 2, distinct from the author and from each other)"), 1)
        self.assertIn("### independent-multi-agent-review", text)
        self.assertNotIn("Reviewers (", render.pre_pr_review_block(artifact("R3", docs_only=False)))


class BriefTests(unittest.TestCase):
    def test_states_ownership_isolation_model_effort_depth_reviews_and_modes(self):
        art = artifact()
        text = brief(art)
        for expected in ("## Assurance profile", "- Profile: standard v1", f"`{art['digest']}`",
                         "- Ownership: SPEC-067 modules", "- Isolation: own worktree",
                         "- Model and effort: Sonnet 5.5, medium",
                         "- Pre-PR review depth: R2 (documentation-only change)",
                         "- Depth source: profile; risk class: docs-only",
                         "- Required reviews: accuracy-review, claim-discipline-review, concision-review",
                         "| pre-pr-review | notify | profile |", "| merge | standing-authorization | profile |",
                         "Advisory only: this profile grants no tool, merge, release or approval."):
            self.assertIn(expected, text)
        self.assertEqual(text.count("\n| "), len(ha.CHECKPOINTS) + 1)  # header and one row each

    def test_every_checkpoint_row_matches_the_artifact(self):
        art = artifact(documents={"user": {"schema": ha.SETTINGS_FORMAT, "scope": "user",
                                           "checkpoints": {"ci": {"mode": "approve-each"}}}})
        text = brief(art)
        for row in art["checkpoints"]:
            self.assertIn(f"| {row['checkpoint']} | {row['mode']} | {row['modeSource']} |", text)
        self.assertIn("| ci | approve-each | user |", text)

    def test_required_reviews_none_at_r0_and_independent_rule_at_r4(self):
        self.assertIn("- Required reviews: none", brief(artifact("R0")))
        r4 = brief(artifact("R4", docs_only=False))
        self.assertIn("- Independent reviewers: at least 2, distinct from the author and from each other", r4)
        self.assertNotIn("Independent reviewers", brief(artifact("R3", docs_only=False)))

    def test_section_names_no_review_the_depth_does_not_require(self):
        for depth in ha.DEPTHS:
            for docs in (True, False):
                art = artifact(depth, docs_only=docs)
                text = brief(art)
                for kind in ALL_KINDS - set(art["reviews"]["required"]):
                    self.assertNotIn(kind, text, (depth, docs))

    def test_golden_r0_code_brief(self):
        art = artifact("R0", docs_only=False, profile="lite")
        rows = "\n".join(f"| {r['checkpoint']} | {r['mode']} | {r['modeSource']} |" for r in art["checkpoints"])
        self.assertEqual(brief(art), f"""## Assurance profile

- Profile: lite v1
- Compiled artifact digest: `{art['digest']}`
- Ownership: SPEC-067 modules
- Isolation: own worktree
- Model and effort: Sonnet 5.5, medium
- Pre-PR review depth: R0 (code change)
- Depth source: repository; risk class: ordinary
- Required reviews: none

| Checkpoint | Mode | Source |
|---|---|---|
{rows}

Advisory only: this profile grants no tool, merge, release or approval.
""")

    def test_refused_lowerings_are_listed(self):
        art = artifact(documents={"conversation": {"schema": ha.SETTINGS_FORMAT, "scope": "conversation",
                                                   "checkpoints": {"pre-pr-review": {"depth": "R0"}}}})
        self.assertIn("- Refused lowering: pre-pr-review depth requested by conversation "
                      "(conversation-lowering-refused)", brief(art))

    def test_free_text_must_be_one_printable_nonblank_line(self):
        art = artifact()
        for field in BRIEF:
            for bad in ("", "  ", "a\nb", "x" * 201, None, 3, "tab\there", "a|b", "`x`", "[l](http://e)", "# h", "<b>"):
                refused(self, "invalid-artifact", render.track_brief_section, art, **{**BRIEF, field: bad})


class ArtifactRefusalTests(unittest.TestCase):
    calls = (brief, render.pre_pr_review_block)

    def test_execution_authorization_true_is_refused_even_with_a_recomputed_digest(self):
        for call in self.calls:
            art = artifact()
            art["executionAuthorization"] = True
            refused(self, "execution-authorization", call, art)
            refused(self, "execution-authorization", call, resealed(art))

    def test_digest_mismatch_is_refused(self):
        for call in self.calls:
            art = artifact()
            art["checkpoints"][0]["mode"] = "autonomous"
            refused(self, "digest-mismatch", call, art)
            art = artifact()
            art["digest"] = "0" * 64
            refused(self, "digest-mismatch", call, art)

    def test_review_table_that_disagrees_with_the_ladder_is_refused(self):
        for call in self.calls:
            art = artifact()
            art = resealed(art, reviews={**art["reviews"], "required": ["code-review"]})
            refused(self, "invalid-artifact", call, art)

    def test_resealed_artifact_with_missing_or_hostile_values_is_refused(self):
        def mutate(change):
            art = artifact("R4", docs_only=False)
            change(art)
            return resealed(art)

        def row(art, name):
            return next(r for r in art["checkpoints"] if r["checkpoint"] == name)

        changes = (
            lambda a: a.pop("profile"), lambda a: a.pop("risk"), lambda a: a.pop("checkpoints"),
            lambda a: a.pop("refusedLowerings"), lambda a: a.update(profile=None), lambda a: a.update(checkpoints=["x"]),
            lambda a: a.update(checkpoints=[]), lambda a: a.update(refusedLowerings=5),
            lambda a: a.update(refusedLowerings=[1]),
            lambda a: a["profile"].update(name="x\n## Injected"),
            lambda a: row(a, "ci").update(mode="| x |\n# H"), lambda a: row(a, "ci").update(modeSource="[l](u)"),
            lambda a: a["reviews"].update(minIndependentReviewers=0),
            lambda a: a["reviews"].update(extra=1), lambda a: a["reviews"].update(required=tuple(a["reviews"]["required"])),
            lambda a: a["risk"].update(riskClass="`x`"),
            lambda a: row(a, "pre-pr-review").update(depth="R0"),
            lambda a: a.update(refusedLowerings=[{"checkpoint": "ci", "dimension": "mode", "requested": "x",
                                                   "scope": "user\n#", "floor": "x", "reason": "floor-not-human-only"}]),
        )
        for index, change in enumerate(changes):
            for call in self.calls:
                with self.subTest(index=index):
                    refused(self, "invalid-artifact", call, mutate(change))

    def test_malformed_input_is_refused(self):
        for call in self.calls:
            for bad in (None, "artifact", {}, {"schema": ha.COMPILED_FORMAT}, artifact() | {"schema": "x"}):
                with self.assertRaises(ha.AssuranceError):
                    call(bad)
            broken = artifact()
            del broken["reviews"]
            refused(self, "invalid-artifact", call, resealed(broken))
            broken = artifact()
            broken["risk"] = {1, 2}  # not JSON: refused rather than a raw TypeError
            refused(self, "invalid-artifact", call, broken)


if __name__ == "__main__":
    unittest.main()
