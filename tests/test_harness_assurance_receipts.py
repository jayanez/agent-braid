# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-067 T006: gate receipts, standing authorizations and the required-review check; pure, offline, advisory."""
import copy
import unittest

from agent_braid import harness_assurance as ha
from agent_braid import harness_assurance_receipts as rc
from agent_braid import harness_assurance_risk as risk
from scripts import validate_change as validation

BASE = "a" * 40
HEAD = "b" * 40
OTHER = "c" * 40
NOW = "2026-11-10T12:00:00Z"
REPO = "jayanez/agent-braid"
BRANCH = "har/067-t006-receipts"
ALL_MET = {name: True for name in rc.CONDITIONS}
STATEMENT = "Autorizo el merge de los tracks de SPEC-067 hasta el 2026-11-30."


def artifact(profile_name="standard", paths=("README.md",), lines=10, documents=None):
    profile = ha.preset(profile_name)
    cls = risk.classify_risk(profile, list(paths), lines, validation.classify(paths))
    return ha.compile_artifact(profile, documents, cls)


def at_depth(depth, docs_only=False):
    """Artifact with the effective depth set by a repository scope; a non-docs diff the classifier does not raise."""
    profile = ha.preset("standard")
    cls = risk.classify_risk(profile, ["README.md"], 10, validation.classify(["README.md"]))
    if not docs_only:  # every code path is sensitive for the real classifier, so state an ordinary class directly
        cls = {**cls, "docsOnly": False, "riskClass": "ordinary"}
    document = {"repository": {"schema": ha.SETTINGS_FORMAT, "scope": "repository",
                               "checkpoints": {"pre-pr-review": {"depth": depth}}}}
    return ha.compile_artifact(profile, document, cls)



def review(kind, reviewer=None, **kw):
    entry = {"kind": kind, "reviewer": reviewer or f"rev-{kind}", "status": "completed",
             "findingsApplied": ["f1"], "findingsRejected": [{"finding": "f2", "reason": "out of scope"}]}
    entry.update(kw)
    return entry


def reviews_for(art, **kw):
    return [review(kind, **kw) for kind in art["reviews"]["required"] if kind != ha.INDEPENDENT_REVIEW] + (
        [review(ha.INDEPENDENT_REVIEW, "agent-1"), review(ha.INDEPENDENT_REVIEW, "agent-2")]
        if ha.INDEPENDENT_REVIEW in art["reviews"]["required"] else [])


COMMAND = {"argv": ["python", "-m", "unittest"], "exitCode": 0, "outputSha256": "d" * 64}


def receipt(art=None, checkpoint="pre-pr-review", **kw):
    art = art or artifact()
    args = dict(checkpoint=checkpoint, base_commit=BASE, head_commit=HEAD, author="track-author",
                reviews=reviews_for(art) if checkpoint == "pre-pr-review" else [], commands=[copy.deepcopy(COMMAND)],
                approvals=[{"kind": "human", "ref": "pr-comment-1"}], created_at=NOW)
    args.update(kw)
    return rc.build_receipt(art, **args)


def verify(r, art=None, base=BASE, head=HEAD, checkpoint=None):
    checkpoint = checkpoint or (r["checkpoint"] if isinstance(r, dict) else "pre-pr-review")
    return rc.verify_receipt(r, art or artifact(), checkpoint=checkpoint, base_commit=base, head_commit=head)


def refused(case, reason, r, art=None, base=BASE, head=HEAD, review_kind=None, checkpoint=None):
    with case.assertRaises(rc.ReceiptError) as ctx:
        verify(r, art, base, head, checkpoint)
    case.assertEqual(ctx.exception.reason, reason)
    case.assertIn(reason, rc.RECEIPT_REASONS)
    case.assertEqual(ctx.exception.review, review_kind)


def resealed(r, **changes):
    body = {**{k: v for k, v in r.items() if k != "digest"}, **changes}
    return {**body, "digest": ha.digest(body)}


def authorization(**kw):
    fields = dict(id="auth-1", checkpoint="merge", repository=REPO, branch_pattern="har/067-*",
                  issued_at="2026-11-02T10:00:00Z", expires_at="2026-12-02T10:00:00Z", issuer="founder",
                  owner_statement=STATEMENT)
    fields.update(kw)
    return rc.build_authorization(**fields)


def evaluate(record, checkpoint="merge", repository=REPO, branch=BRANCH, now=NOW, met=None):
    return rc.evaluate_standing(record, checkpoint=checkpoint, repository=repository, branch=branch, now=now,
                                conditions_met=ALL_MET if met is None else met)


class StandingAuthorizationTests(unittest.TestCase):
    def assert_fallback(self, decision, reason):
        self.assertEqual(decision, {"mode": "approve-each", "authorization": None, "fallbackReason": reason})
        self.assertIn(reason, rc.FALLBACK_REASONS)

    def test_valid_authorization_is_cited(self):
        self.assertEqual(evaluate(authorization()),
                         {"mode": "standing-authorization", "authorization": "auth-1", "fallbackReason": None})

    def test_record_is_hashed_and_keeps_the_verbatim_statement(self):
        record = authorization()
        self.assertEqual(record["ownerStatement"], STATEMENT)
        self.assertEqual(record["digest"], ha.digest({k: v for k, v in record.items() if k != "digest"}))
        self.assertEqual(record["conditions"], ["ciGreen", "noOpenReviewThreads", "receiptsPresent"])
        self.assertIsNone(record["revokedAt"])

    def test_missing_falls_back(self):
        self.assert_fallback(evaluate(None), "missing")

    def test_expired_and_not_yet_valid_fall_back(self):
        self.assert_fallback(evaluate(authorization(), now="2026-12-02T10:00:00Z"), "expired")
        self.assert_fallback(evaluate(authorization(), now="2027-01-01T00:00:00Z"), "expired")
        self.assert_fallback(evaluate(authorization(), now="2026-11-01T00:00:00Z"), "not-yet-valid")
        self.assertEqual(evaluate(authorization(), now="2026-12-02T09:59:59Z")["mode"], "standing-authorization")

    def test_revoked_falls_back_from_the_revocation_moment(self):
        record = authorization(revoked_at="2026-11-05T00:00:00Z")
        self.assert_fallback(evaluate(record), "revoked")
        self.assertEqual(evaluate(record, now="2026-11-04T00:00:00Z")["mode"], "standing-authorization")

    def test_out_of_scope_falls_back(self):
        self.assert_fallback(evaluate(authorization(), repository="other/repo"), "out-of-scope")
        self.assert_fallback(evaluate(authorization(), branch="feature/x"), "out-of-scope")
        self.assert_fallback(evaluate(authorization(checkpoint="ci")), "out-of-scope")

    def test_non_permitted_issuer_falls_back(self):
        for issuer in ("orchestrator", "agent", "Founder", "founder "):
            self.assert_fallback(evaluate(authorization(issuer=issuer)), "issuer-not-permitted")

    def test_non_admitting_checkpoint_falls_back_even_when_the_record_names_it(self):
        for checkpoint in ("release", "ci", "pr-open", "grant"):
            self.assert_fallback(evaluate(authorization(checkpoint=checkpoint), checkpoint=checkpoint),
                                 "checkpoint-not-admitting")

    def test_missing_verbatim_statement_falls_back(self):
        for statement in ("", "   \n"):
            self.assert_fallback(evaluate(authorization(owner_statement=statement)), "statement-missing")

    def test_horizon_over_30_days_or_inverted_falls_back(self):
        self.assert_fallback(evaluate(authorization(expires_at="2026-12-02T10:00:01Z")), "horizon-exceeded")
        self.assert_fallback(evaluate(authorization(expires_at="2026-11-02T10:00:00Z")), "horizon-exceeded")
        self.assertEqual(evaluate(authorization(expires_at="2026-12-02T10:00:00Z"))["mode"], "standing-authorization")

    def test_each_failing_condition_falls_back(self):
        for name in rc.CONDITIONS:
            self.assert_fallback(evaluate(authorization(), met={**ALL_MET, name: False}), "condition-failed")
        self.assert_fallback(evaluate(authorization(), met={"ciGreen": True}), "condition-failed")
        self.assert_fallback(evaluate(authorization(), met={**ALL_MET, "ciGreen": "yes"}), "condition-failed")

    def test_edited_or_malformed_record_falls_back(self):
        record = authorization()
        record["expiresAt"] = "2027-12-02T10:00:00Z"
        self.assert_fallback(evaluate(record), "invalid-record")
        self.assert_fallback(evaluate({"schema": "x"}), "invalid-record")
        self.assert_fallback(evaluate("record"), "invalid-record")
        self.assert_fallback(evaluate(authorization(owner_statement=None)), "invalid-record")
        self.assert_fallback(evaluate(authorization(issued_at="yesterday")), "invalid-record")
        self.assert_fallback(evaluate(authorization(id="bad id!")), "invalid-record")
        self.assert_fallback(evaluate(authorization(issued_at=None)), "invalid-record")
        self.assert_fallback(evaluate(authorization(expires_at=None)), "invalid-record")
        self.assert_fallback(evaluate(authorization(issued_at="\u0662\u0660\u0662\u0666-11-01T00:00:00Z")), "invalid-record")

    def test_revocation_at_the_evaluation_moment_counts_and_conditions_must_be_a_mapping(self):
        self.assert_fallback(evaluate(authorization(revoked_at=NOW)), "revoked")
        decision = rc.evaluate_standing(authorization(), checkpoint="merge", repository=REPO, branch=BRANCH,
                                        now=NOW, conditions_met=None)
        self.assert_fallback(decision, "condition-failed")

    def test_bad_time_or_checkpoint_argument_is_an_error(self):
        for kwargs in ({"now": "today"}, {"now": "2026-13-45T00:00:00Z"}, {"checkpoint": "nope"}, {"branch": None},
                       {"repository": 1}):
            with self.assertRaises(rc.ReceiptError) as ctx:
                evaluate(authorization(), **kwargs)
            self.assertIn(ctx.exception.reason, ("invalid-time", "unknown-checkpoint", "invalid-authorization"))


class ReceiptBuildTests(unittest.TestCase):
    def test_receipt_records_effective_values_sources_and_digest(self):
        r = receipt()
        self.assertEqual((r["depth"], r["depthSource"], r["mode"], r["modeSource"]), ("R2", "profile", "notify", "profile"))
        self.assertEqual(r["profileDigest"], artifact()["inputs"]["profile"])
        self.assertEqual(r["riskClass"], "docs-only")
        self.assertEqual(r["digest"], ha.digest({k: v for k, v in r.items() if k != "digest"}))
        self.assertEqual(verify(r), r)

    def test_receipt_is_deterministic(self):
        self.assertEqual(ha.canonical(receipt()), ha.canonical(receipt()))

    def test_non_review_checkpoint_has_no_depth(self):
        r = receipt(checkpoint="ci", approvals=[])
        self.assertEqual((r["depth"], r["depthSource"]), (None, None))
        verify(r)

    def test_risk_raise_is_carried_with_its_source(self):
        art = artifact(paths=("agent_braid/forecast_model.py",))
        r = receipt(art)
        self.assertEqual((r["depth"], r["depthSource"], r["riskClass"]), ("R3", "risk", "elevated"))
        verify(r, art)

    def test_unknown_checkpoint_or_tampered_artifact_is_refused(self):
        with self.assertRaises(rc.ReceiptError) as ctx:
            receipt(checkpoint="nope")
        self.assertEqual(ctx.exception.reason, "unknown-checkpoint")
        art = artifact()
        art["reviews"]["required"] = []
        with self.assertRaises(rc.ReceiptError) as ctx:
            receipt(art)
        self.assertEqual(ctx.exception.reason, "invalid-artifact")


class VerifyReceiptTests(unittest.TestCase):
    def test_edit_without_digest_recompute_is_refused(self):
        r = receipt()
        r["author"] = "someone-else"
        refused(self, "digest-mismatch", r)
        r = receipt()
        r["commands"][0]["exitCode"] = 1
        refused(self, "digest-mismatch", r)

    def test_wrong_commit_is_refused(self):
        refused(self, "commit-mismatch", receipt(), head=OTHER)
        refused(self, "commit-mismatch", receipt(), base=OTHER)
        refused(self, "commit-mismatch", receipt(head_commit=OTHER))

    def test_profile_digest_mismatch_is_refused(self):
        refused(self, "profile-mismatch", receipt(), art=artifact("strict"))
        refused(self, "profile-mismatch", resealed(receipt(), profileDigest="e" * 64))
        refused(self, "profile-mismatch", resealed(receipt(), riskClass="elevated"))

    def test_depth_below_effective_is_refused(self):
        art = artifact(paths=("agent_braid/forecast_model.py",))
        r = receipt(art)
        refused(self, "depth-below-effective", resealed(r, depth="R2"), art=art)
        refused(self, "depth-below-effective", resealed(receipt(), depth=None, depthSource=None))
        verify(resealed(receipt(), depth="R4", depthSource="profile"))

    def test_lower_depth_receipt_for_a_raised_gate_is_refused(self):
        low = receipt(artifact("lite"))  # R1 receipt against an R2 artifact
        refused(self, "profile-mismatch", low)
        refused(self, "depth-below-effective", resealed(low, profileDigest=artifact()["inputs"]["profile"]))
        art = at_depth("R3")
        low = receipt(at_depth("R2"))
        refused(self, "depth-below-effective", low, art=art)

    def test_mode_must_match_and_approvals_match_the_mode(self):
        refused(self, "mode-below-effective", resealed(receipt(), mode="autonomous"))
        refused(self, "mode-mismatch", resealed(receipt(), mode="human-only"))
        refused(self, "mode-source-mismatch", resealed(receipt(), modeSource="repository"))
        refused(self, "fallback-reason-invalid", resealed(receipt(), fallbackReason="missing"))
        refused(self, "approval-mismatch", resealed(receipt(), approvals=[{"kind": "standing-authorization", "ref": "a"}]))

    def test_approve_each_checkpoint_needs_a_human_approval(self):
        art = artifact("strict")
        refused(self, "approval-mismatch", receipt(art, approvals=[]), art=art)
        verify(receipt(art), art)

    def test_malformed_receipts_are_refused(self):
        refused(self, "invalid-receipt", "receipt")
        r = receipt()
        del r["reviews"]
        refused(self, "invalid-receipt", r)
        refused(self, "invalid-receipt", {**receipt(), "extra": 1})
        refused(self, "unsupported-schema", resealed(receipt(), schema="other"))
        for change, reason in (({"headCommit": "short"}, "invalid-receipt"), ({"createdAt": "yesterday"}, "invalid-time"),
                               ({"author": "bad author"}, "invalid-receipt"),
                               ({"reviews": [{"kind": ["x"]}]}, "invalid-receipt"),
                               ({"approvals": [{"kind": "robot", "ref": "x"}]}, "invalid-receipt"),
                               ({"commands": [COMMAND] * 65}, "invalid-receipt")):
            refused(self, reason, resealed(receipt(), **change))
        refused(self, "command-without-exit-code", receipt(commands=["ls"]))
        refused(self, "command-without-exit-code", receipt(commands=[{**COMMAND, "exitCode": 1000}]))

    def test_command_without_exit_code_is_refused(self):
        for command in ({"argv": ["x"], "outputSha256": "d" * 64},
                        {**COMMAND, "exitCode": None}, {**COMMAND, "exitCode": True}, {**COMMAND, "exitCode": "0"}):
            refused(self, "command-without-exit-code", receipt(commands=[command]))
        refused(self, "invalid-receipt", receipt(commands=[{**COMMAND, "argv": []}]))
        refused(self, "invalid-receipt", receipt(commands=[{**COMMAND, "outputSha256": "x"}]))
        verify(receipt(commands=[{**COMMAND, "exitCode": 2}]))

    def test_tampered_or_malformed_artifact_is_refused(self):
        art = artifact()
        art["reviews"]["required"] = []
        refused(self, "invalid-artifact", receipt(), art=art)
        broken = artifact()
        del broken["reviews"]["required"]  # self-consistent: digest recomputed
        broken["digest"] = ha.digest({k: v for k, v in broken.items() if k != "digest"})
        refused(self, "invalid-artifact", receipt(), art=broken)

    def test_receipt_for_another_checkpoint_is_refused(self):
        refused(self, "checkpoint-mismatch", receipt(checkpoint="pre-commit", approvals=[]), checkpoint="pre-pr-review")
        refused(self, "checkpoint-mismatch", receipt(), checkpoint="merge")


class RequiredReviewTests(unittest.TestCase):
    def test_each_depth_passes_with_its_required_reviews(self):
        for depth in ("R1", "R2", "R3", "R4"):
            art = at_depth(depth)
            self.assertEqual(art["reviews"]["depth"], depth)
            verify(receipt(art), art)

    def test_r0_requires_no_review(self):
        art = artifact(documents={"repository": {"schema": ha.SETTINGS_FORMAT, "scope": "repository",
                                                  "checkpoints": {"pre-pr-review": {"depth": "R0"}}}})
        self.assertEqual(art["reviews"]["required"], [])
        verify(receipt(art, reviews=[]), art)

    def test_r2_needs_code_quality_and_simplification(self):
        art = at_depth("R2")
        self.assertEqual(art["reviews"]["depth"], "R2")
        self.assertEqual(art["reviews"]["required"], ["code-review", "quality-review", "simplification-review"])
        full = reviews_for(art)
        for missing in art["reviews"]["required"]:
            partial = [r for r in full if r["kind"] != missing]
            refused(self, "review-missing", receipt(art, reviews=partial), art=art, review_kind=missing)
        verify(receipt(art, reviews=full), art)

    def test_docs_only_r2_needs_the_docs_reviews(self):
        art = artifact()
        self.assertEqual(art["reviews"]["required"], ["accuracy-review", "claim-discipline-review", "concision-review"])
        refused(self, "review-missing", receipt(art, reviews=[review("code-review")]), art=art,
                review_kind="accuracy-review")

    def test_incomplete_review_does_not_count(self):
        art = artifact()
        bad = [review(kind, status="incomplete") if kind == "concision-review" else review(kind)
               for kind in art["reviews"]["required"]]
        refused(self, "review-missing", receipt(art, reviews=bad), art=art, review_kind="concision-review")

    def test_r4_needs_two_distinct_independent_reviewers_other_than_the_author(self):
        art = at_depth("R4")
        base = [r for r in reviews_for(art) if r["kind"] != ha.INDEPENDENT_REVIEW]
        kind = ha.INDEPENDENT_REVIEW
        for reviewers in ([], ["agent-1"], ["agent-1", "agent-1"], ["agent-1", "track-author"]):
            r = receipt(art, reviews=[*base, *[review(kind, who) for who in reviewers]])
            refused(self, "independent-reviews-insufficient", r, art=art, review_kind=kind)
        r = receipt(art, reviews=[*base, review(kind, "agent-1", status="incomplete"), review(kind, "agent-2")])
        refused(self, "independent-reviews-insufficient", r, art=art, review_kind=kind)
        verify(receipt(art, reviews=[*base, review(kind, "agent-1"), review(kind, "agent-2")]), art)

    def test_review_needs_findings_dispositions_with_reasons(self):
        art = artifact()
        for bad in ({"findingsRejected": [{"finding": "f", "reason": ""}]}, {"findingsApplied": "none"},
                    {"findingsRejected": [{"finding": "f"}]}, {"status": "passed"}):
            reviews = [review(kind, **bad) for kind in art["reviews"]["required"]]
            refused(self, "invalid-receipt", receipt(art, reviews=reviews), art=art)

    def test_lower_depth_receipt_cannot_satisfy_a_higher_gate(self):
        art = at_depth("R3")
        low = receipt(art, reviews=reviews_for(at_depth("R2")))
        refused(self, "review-missing", low, art=art, review_kind="adversarial-security-review")


class StandingReceiptTests(unittest.TestCase):
    merge_artifact = staticmethod(artifact)

    def test_valid_authorization_is_cited_in_the_merge_receipt(self):
        art = self.merge_artifact()
        decision = evaluate(authorization())
        r = receipt(art, checkpoint="merge", approvals=[], standing=decision)
        self.assertEqual((r["mode"], r["modeSource"], r["fallbackReason"]), ("standing-authorization", "profile", None))
        self.assertEqual(r["approvals"], [{"kind": "standing-authorization", "ref": "auth-1"}])
        verify(r, art)

    def test_failed_authorization_falls_back_to_approve_each_and_records_why(self):
        art = self.merge_artifact()
        decision = evaluate(authorization(), now="2027-01-01T00:00:00Z")
        r = receipt(art, checkpoint="merge", standing=decision)
        self.assertEqual((r["mode"], r["modeSource"], r["fallbackReason"]), ("approve-each", "fallback", "expired"))
        verify(r, art)
        r = receipt(art, checkpoint="merge")
        self.assertEqual(r["fallbackReason"], "missing")
        verify(r, art)

    def test_fallback_without_a_human_approval_is_refused(self):
        art = self.merge_artifact()
        r = receipt(art, checkpoint="merge", approvals=[], standing=evaluate(None))
        refused(self, "approval-mismatch", r, art=art)

    def test_downgrade_without_a_reason_or_a_reason_without_downgrade_is_refused(self):
        art = self.merge_artifact()
        r = receipt(art, checkpoint="merge", standing=evaluate(None))
        refused(self, "fallback-reason-invalid", resealed(r, fallbackReason=None), art=art)
        ok = receipt(art, checkpoint="merge", approvals=[], standing=evaluate(authorization()))
        refused(self, "fallback-reason-invalid", resealed(ok, fallbackReason="expired"), art=art)

    def test_standing_authorization_cannot_be_claimed_where_the_mode_is_not_effective(self):
        art = artifact("strict")  # merge is approve-each there
        r = receipt(art, checkpoint="merge", approvals=[{"kind": "standing-authorization", "ref": "auth-1"}])
        refused(self, "approval-mismatch", r, art=art)
        forged = resealed(receipt(art, checkpoint="merge"), mode="standing-authorization",
                          approvals=[{"kind": "standing-authorization", "ref": "auth-1"}])
        refused(self, "mode-below-effective", forged, art=art)


if __name__ == "__main__":
    unittest.main()
