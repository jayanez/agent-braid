# SPDX-License-Identifier: AGPL-3.0-only
"""Offline promotion controls; deterministic doubles only, no host, model or native activation."""
from functools import lru_cache
from hashlib import sha256
import os
from pathlib import Path
import tempfile
import unittest

from agent_braid import harness_promotion as pr
from agent_braid.harness_evaluation import EvaluationRecord
from agent_braid.system_one import canonical, digest, freeze, parse_json

from tests.test_harness_evaluation import Cohort, all_pass, edited

HUMAN = {"kind": "human", "id": "founder"}
SAFE = {"unsafeAdmissions": 0, "authorityViolations": 0, "effectViolations": 0}
IDENTITY = {"sourceSha256": sha256(b"source").hexdigest(), "host": "host-a:1.0",
            "model": "model-a:1", "toolSetSha256": sha256(b"tools").hexdigest(),
            "policySha256": sha256(b"policy").hexdigest()}
SCOPE = "task-001"


def h(name: str) -> str:
    return sha256(name.encode()).hexdigest()


@lru_cache(maxsize=None)
def evaluated(n: int = 19, cohort: str = "synthetic", decision: str = "candidate"):
    """A real T003 registration and report over ``n`` all-pass held-out units."""
    group = Cohort(n, decision=decision)
    registration = group.register(cohort=cohort)
    report = group.evaluate(group.rows(all_pass(group)), registration=registration)
    return registration, report


def profile(registration, *, cohort="synthetic", scope=SCOPE, **identity):
    return {"candidateSha256": registration.to_dict()["arms"]["C"]["candidateSha256"],
            "scope": scope, "cohort": cohort, "effects": ["write-workspace"],
            "identity": {**IDENTITY, **identity}}


def decide(n=19, cohort="synthetic", *, profile_cohort=None, decision="approved", actor=HUMAN,
           safety=SAFE, rollback=None, at=10, evidence=(), **identity):
    registration, report = evaluated(n, cohort)
    return pr.decide(registration, report,
                     profile=profile(registration, cohort=profile_cohort or cohort, **identity),
                     actor=actor, decision=decision, safety=safety, evidence=list(evidence),
                     rollback_target=rollback, limits=["synthetic-only"], at=at)


class RefusalCase(unittest.TestCase):
    def refused(self, expected, fn, /, *args, **kwargs):
        with self.assertRaises(pr.PromotionError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, expected)


class DecisionTests(RefusalCase):
    def test_approval_binds_candidate_domain_identity_evidence_and_rollback(self):
        registration, report = evaluated()
        record = decide(evidence=[h("safety-review")])
        data = record.to_dict()
        self.assertEqual(data["format"], pr.DECISION_FORMAT)
        self.assertEqual(data["decision"], "approved")
        self.assertEqual(data["actor"], HUMAN)
        self.assertEqual(data["profile"]["candidateSha256"],
                         registration.to_dict()["arms"]["C"]["candidateSha256"])
        self.assertEqual(data["profile"]["identity"], IDENTITY)
        self.assertEqual(data["profileSha256"], digest(data["profile"]))
        self.assertEqual(data["registrationSha256"], registration.sha256)
        self.assertEqual(data["evaluationSha256"], report.sha256)
        self.assertEqual(data["costReportSha256"], report.to_dict()["costReportSha256"])
        self.assertEqual(data["regression"], {"synthetic": "noninferior"})
        self.assertEqual(data["evidenceSha256s"], [h("safety-review")])
        self.assertIsNone(data["rollbackTargetSha256"])
        self.assertEqual(data["pendingEndpoints"], report.to_dict()["pendingEndpoints"])
        self.assertIs(data["executionAuthorization"], False)
        self.assertIs(record.executionAuthorization, False)
        self.assertEqual(record.sha256, digest(data))

    def test_automatic_promotion_is_disabled(self):
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)
        robot = {"kind": "automatic-policy", "id": "policy-1"}
        for outcome in pr.DECISIONS:
            self.refused("automatic-promotion-disabled", decide, actor=robot, decision=outcome)
        self.refused("invalid-decision", decide, actor={"kind": "model", "id": "judge"})

    def test_decision_is_bound_to_the_evaluated_arm_c_candidate(self):
        registration, report = evaluated()
        other = profile(registration) | {"candidateSha256": h("other")}
        self.refused("candidate-mismatch", pr.decide, registration, report, profile=other,
                     actor=HUMAN, decision="approved", safety=SAFE, at=10)
        base_reg, base_report = evaluated(4, decision="keep-base")
        self.refused("no-candidate", pr.decide, base_reg, base_report,
                     profile=profile(base_reg), actor=HUMAN, decision="pending", safety=SAFE, at=10)

    def test_evaluation_must_bind_its_registration_and_bytes(self):
        registration, report = evaluated()
        other_reg, _ = evaluated(4)
        args = dict(profile=profile(registration), actor=HUMAN, decision="approved",
                    safety=SAFE, at=10)
        self.refused("registration-mismatch", pr.decide, other_reg, report,
                     **args | {"profile": profile(other_reg)})
        forged = EvaluationRecord(report.data, canonical({"x": 1}))
        self.refused("invalid-evaluation", pr.decide, registration, forged, **args)
        self.refused("invalid-evaluation", pr.decide, registration, registration, **args)
        tampered = edited(report, EvaluationRecord, format="other")
        self.refused("invalid-evaluation", pr.decide, registration, tampered, **args)

    def test_synthetic_evidence_cannot_approve_a_native_profile(self):
        self.refused("cohort-mismatch", decide, profile_cohort="native")
        self.assertEqual(decide(cohort="native").to_dict()["cohort"], "native")

    def test_regression_coverage_is_required_for_approval_only(self):
        self.refused("regression-not-covered", decide, n=4)
        for outcome in ("rejected", "pending"):
            data = decide(n=4, decision=outcome).to_dict()
            self.assertEqual(data["regression"], {"synthetic": "descriptive-only"})

    def test_any_unsafe_admission_or_authority_violation_blocks_promotion(self):
        for key, reason in (("unsafeAdmissions", "unsafe-admission"),
                            ("authorityViolations", "authority-violation"),
                            ("effectViolations", "effect-violation")):
            self.refused(reason, decide, safety=SAFE | {key: 1})
            self.refused("safety-unknown", decide, safety=SAFE | {key: None})
            self.assertEqual(decide(safety=SAFE | {key: 1}, decision="rejected")
                             .to_dict()["decision"], "rejected")
        self.refused("invalid-decision", decide, safety=SAFE | {"unsafeAdmissions": True})
        self.refused("invalid-decision", decide, safety={"unsafeAdmissions": 0})

    def test_profile_and_fields_are_validated(self):
        self.refused("invalid-profile", decide, model="bad model")
        self.refused("invalid-profile", decide, policySha256="x")
        self.refused("invalid-decision", decide, decision="adopted")
        self.refused("invalid-decision", decide, at=-1)
        self.refused("invalid-decision", decide, evidence=sorted([h("a"), h("b")], reverse=True))
        self.refused("invalid-decision", decide, evidence=[h("a"), h("a")])
        self.refused("invalid-decision", decide, rollback="not-a-hash")


def registry_with(*decisions, at=20):
    registry = pr.ProfileRegistry.empty(SCOPE)
    for decision in decisions:
        registry = registry.begin(decision, current=IDENTITY, at=at).commit(current=IDENTITY, at=at)
    return registry


class RegistryTests(RefusalCase):
    def test_human_transaction_activates_only_the_approved_profile(self):
        decision = decide()
        empty = pr.ProfileRegistry.empty(SCOPE)
        begun = empty.begin(decision, current=IDENTITY, at=20)
        self.assertEqual(begun.pending, decision.sha256)
        self.assertIsNone(begun.resolve(IDENTITY, cohort="synthetic").profile)  # not active until commit
        active = begun.commit(current=IDENTITY, at=21)
        resolved = active.resolve(IDENTITY, cohort="synthetic")
        self.assertEqual(resolved.decisionSha256, decision.sha256)
        self.assertEqual(resolved.profile, decision.to_dict()["profile"])
        self.assertIsNone(resolved.reason)
        self.assertIs(resolved.executionAuthorization, False)
        self.assertIsNone(active.pending)
        self.assertEqual([e["event"] for e in active.journal], ["begun", "committed"])
        self.assertIsNone(empty.resolve(IDENTITY, cohort="synthetic").profile)  # values are persistent
        self.assertEqual(empty.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")

    def test_stale_identity_is_detected_on_read_and_refused_on_begin_and_commit(self):
        decision = decide()
        active = registry_with(decision)
        for key, reason in (("sourceSha256", "stale-source"), ("host", "stale-host"),
                            ("model", "stale-model"), ("toolSetSha256", "stale-tool"),
                            ("policySha256", "stale-policy")):
            drifted = IDENTITY | {key: h("drift") if key.endswith("Sha256") else "drifted"}
            resolved = active.resolve(drifted, cohort="synthetic")
            self.assertIsNone(resolved.profile)
            self.assertEqual(resolved.reason, reason)
            self.refused(reason, pr.ProfileRegistry.empty(SCOPE).begin, decision,
                         current=drifted, at=20)
            begun = pr.ProfileRegistry.empty(SCOPE).begin(decision, current=IDENTITY, at=20)
            self.refused(reason, begun.commit, current=drifted, at=21)
        self.refused("invalid-identity", active.resolve, {"host": "x"}, cohort="synthetic")
        self.refused("invalid-identity", active.resolve, IDENTITY, cohort="other")
        # A synthetic-cohort profile is never served to a native task in the same scope.
        native = active.resolve(IDENTITY, cohort="native")
        self.assertEqual((native.profile, native.reason), (None, "cohort-mismatch"))

    def test_begin_refuses_unapproved_mismatched_or_concurrent_transactions(self):
        empty = pr.ProfileRegistry.empty(SCOPE)
        self.refused("decision-not-approved", empty.begin, decide(n=4, decision="pending"),
                     current=IDENTITY, at=20)
        self.refused("scope-mismatch", empty.begin, decide(scope="task-002"),
                     current=IDENTITY, at=20)
        self.refused("rollback-target-mismatch", empty.begin, decide(rollback=h("x")),
                     current=IDENTITY, at=20)
        self.refused("decision-time-mismatch", empty.begin, decide(at=30), current=IDENTITY, at=20)
        self.refused("invalid-decision", empty.begin, decide().to_dict(), current=IDENTITY, at=20)
        begun = empty.begin(decide(), current=IDENTITY, at=20)
        self.refused("transaction-in-progress", begun.begin, decide(model="model-b:2"),
                     current=IDENTITY | {"model": "model-b:2"}, at=21)
        self.refused("no-transaction", empty.commit, current=IDENTITY, at=20)
        self.refused("time-regression", begun.commit, current=IDENTITY, at=19)
        self.refused("invalid-time", empty.begin, decide(), current=IDENTITY, at="20")
        self.refused("invalid-reason", begun.abort, at=21, reason=None)

    def test_second_promotion_needs_the_current_profile_as_rollback_target(self):
        first = decide()
        active = registry_with(first)
        self.refused("rollback-target-mismatch", active.begin, decide(model="model-b:2"),
                     current=IDENTITY | {"model": "model-b:2"}, at=30)
        second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"])
        current = IDENTITY | {"model": "model-b:2"}
        promoted = active.begin(second, current=current, at=30).commit(current=current, at=30)
        self.assertEqual(promoted.resolve(current, cohort="synthetic").decisionSha256, second.sha256)
        self.assertEqual(promoted.previous, (first.sha256,))

    def test_rollback_restores_the_prior_usable_profile_and_is_journaled(self):
        first = decide()
        second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"])
        current = IDENTITY | {"model": "model-b:2"}
        promoted = registry_with(first).begin(second, current=current, at=30).commit(
            current=current, at=30)
        back = promoted.rollback(at=40, reason="operator-rollback")
        self.assertEqual(back.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)
        none = back.rollback(at=41, reason="operator-rollback")
        self.assertEqual(none.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")
        self.refused("no-active-profile", none.rollback, at=42, reason="again")
        self.assertEqual([(e["event"], e["reason"]) for e in none.journal][-2:],
                         [("rolled-back", "operator-rollback")] * 2)
        # A rolled-back decision is withdrawn; restoring it needs a new human decision.
        self.refused("decision-withdrawn", none.begin, first, current=IDENTITY, at=50)
        renewed = decide(at=45)
        again = none.begin(renewed, current=IDENTITY, at=50).commit(current=IDENTITY, at=50)
        self.assertEqual(again.resolve(IDENTITY, cohort="synthetic").decisionSha256, renewed.sha256)
        self.refused("invalid-reason", promoted.rollback, at=40, reason="bad reason")

    def test_commit_refuses_when_the_rollback_target_changed_while_pending(self):
        first = decide(evidence=[h("review-1")])
        second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"])
        current = IDENTITY | {"model": "model-b:2"}
        pending = registry_with(first).begin(second, current=current, at=30)
        for changed in (pending.rollback(at=31, reason="operator-rollback"),
                        pending.revoke_evidence(h("review-1"), at=31, reason="withdrawn")):
            self.refused("rollback-target-mismatch", changed.commit, current=current, at=32)
            self.assertIsNone(changed.abort(at=32, reason="target-changed").pending)

    def test_hand_built_decisions_are_validated_before_use(self):
        empty = pr.ProfileRegistry.empty(SCOPE)
        for data in ({}, decide().to_dict() | {"executionAuthorization": True}):
            forged = pr.PromotionDecision(freeze(data))
            self.refused("invalid-decision", empty.begin, forged, current=IDENTITY, at=20)
            self.refused("invalid-decision", empty.record, forged, at=20)

    def test_interrupted_promotion_keeps_the_prior_profile_until_aborted(self):
        first = decide()
        second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"])
        current = IDENTITY | {"model": "model-b:2"}
        interrupted = registry_with(first).begin(second, current=current, at=30)
        restored = pr.ProfileRegistry.from_bytes(interrupted.to_bytes())
        self.assertEqual(restored.pending, second.sha256)
        self.assertEqual(restored.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)
        self.refused("transaction-in-progress", restored.begin, second, current=current, at=31)
        recovered = restored.abort(at=31, reason="interrupted")
        self.assertIsNone(recovered.pending)
        self.assertEqual(recovered.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)
        self.assertEqual(recovered.journal[-1]["event"], "aborted")
        self.refused("no-transaction", recovered.abort, at=32, reason="again")

    def test_revoked_evidence_withdraws_profiles_and_blocks_new_transactions(self):
        first = decide(evidence=[h("review-1")])
        second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"],
                        evidence=[h("review-2")])
        current = IDENTITY | {"model": "model-b:2"}
        promoted = registry_with(first).begin(second, current=current, at=30).commit(
            current=current, at=30)
        revoked = promoted.revoke_evidence(h("review-2"), at=40, reason="review-withdrawn")
        self.assertEqual(revoked.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)
        self.refused("revoked-evidence", revoked.rollback(at=41, reason="x").begin, second,
                     current=current, at=42)
        # Revoking shared evaluation evidence withdraws every profile that cites it.
        shared = second.to_dict()["evaluationSha256"]
        gone = promoted.revoke_evidence(shared, at=40, reason="evaluation-withdrawn")
        self.assertEqual(gone.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")
        self.assertEqual(gone.previous, ())
        # Revocation falls back past a prior profile whose own evidence is revoked.
        third = decide(policySha256=h("policy-c"), rollback=second.to_dict()["profileSha256"],
                       evidence=[h("review-3")])
        latest = IDENTITY | {"policySha256": h("policy-c")}
        stacked = promoted.begin(third, current=latest, at=31).commit(current=latest, at=31)
        fallback = stacked.revoke_evidence(h("review-2"), at=32, reason="withdrawn").revoke_evidence(
            h("review-3"), at=33, reason="withdrawn")
        self.assertEqual(fallback.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)
        self.assertEqual(fallback.previous, ())
        pending = registry_with(first).begin(second, current=current, at=30)
        aborted = pending.revoke_evidence(h("review-2"), at=31, reason="review-withdrawn")
        self.assertIsNone(aborted.pending)
        self.refused("already-revoked", aborted.revoke_evidence, h("review-2"), at=32, reason="x")
        self.refused("invalid-evidence", aborted.revoke_evidence, "x", at=32, reason="x")

    def test_journal_is_bounded(self):
        registry = pr.ProfileRegistry.empty(SCOPE)
        decision = decide()
        while len(registry.journal) < pr.MAX_JOURNAL:
            registry = registry.begin(decision, current=IDENTITY, at=20).abort(at=20, reason="retry")
        self.refused("journal-full", registry.begin, decision, current=IDENTITY, at=20)

    def test_rejected_and_pending_decisions_are_audited_without_activation(self):
        registry = pr.ProfileRegistry.empty(SCOPE)
        for outcome in ("rejected", "pending"):
            registry = registry.record(decide(n=4, decision=outcome), at=20)
        self.assertEqual([e["event"] for e in registry.journal], ["recorded", "recorded"])
        self.assertEqual(len(registry.decisions), 2)
        self.assertEqual(registry.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")
        self.refused("duplicate-decision", registry.record, decide(n=4, decision="pending"), at=21)


class CodecTests(RefusalCase):
    def test_round_trip_is_exact_and_canonical(self):
        registry = registry_with(decide()).rollback(at=30, reason="operator-rollback")
        raw = registry.to_bytes()
        self.assertEqual(pr.ProfileRegistry.from_bytes(raw).to_bytes(), raw)
        self.assertEqual(pr.ProfileRegistry.from_bytes(raw).sha256, registry.sha256)
        self.refused("non-canonical", pr.ProfileRegistry.from_bytes, raw + b" ")
        self.refused("invalid-json", pr.ProfileRegistry.from_bytes, b"{")

    def value(self):
        return parse_json(registry_with(decide()).to_bytes())

    def test_forged_journals_and_decisions_are_refused(self):
        cases = []
        skipped = self.value()
        skipped["journal"] = [skipped["journal"][1] | {"seq": 0}]
        cases.append(("no-transaction", skipped))
        forged = self.value()
        sha = next(iter(forged["decisions"]))
        forged["decisions"][sha]["safety"]["unsafeAdmissions"] = 1
        cases.append(("decision-hash-mismatch", forged))
        automatic = self.value()
        decision = automatic["decisions"].pop(sha)
        decision["actor"] = {"kind": "automatic-policy", "id": "policy-1"}
        automatic["decisions"][digest(decision)] = decision
        for e in automatic["journal"]:
            e["subject"] = digest(decision)
        cases.append(("automatic-promotion-disabled", automatic))
        orphan = self.value()
        extra = decide(n=4, decision="pending").to_dict()
        orphan["decisions"][digest(extra)] = extra
        cases.append(("invalid-registry", orphan))
        reordered = self.value()
        reordered["journal"][1]["at"] = 1
        cases.append(("invalid-journal", reordered))
        boolean = self.value()
        boolean["journal"][1]["seq"] = True
        cases.append(("invalid-journal", boolean))
        for outcome, reason in (("pending", "decision-not-approved"),
                                ("rejected", "decision-not-approved")):
            unapproved = self.value()
            extra = decide(n=4, decision=outcome).to_dict()
            unapproved["decisions"] = {digest(extra): extra}
            unapproved["journal"] = unapproved["journal"][:1]
            unapproved["journal"][0]["subject"] = digest(extra)
            cases.append((reason, unapproved))
        foreign = self.value()
        foreign["scope"] = "task-002"
        cases.append(("scope-mismatch", foreign))
        early = self.value()
        early["journal"][0]["at"] = early["journal"][1]["at"] = 5
        cases.append(("decision-time-mismatch", early))
        twice = self.value()
        revoke = {"seq": 2, "event": "evidence-revoked", "subject": h("e"), "at": 30, "reason": "x"}
        twice["journal"] += [revoke, revoke | {"seq": 3}]
        cases.append(("already-revoked", twice))
        duplicate = self.value()
        duplicate["journal"].append(duplicate["journal"][0] | {"seq": 2, "event": "recorded"})
        cases.append(("duplicate-decision", duplicate))
        for field, value, reason in (("profileSha256", h("x"), "invalid-decision"),
                                     ("executionAuthorization", True, "invalid-decision"),
                                     ("format", "other", "invalid-decision")):
            rekeyed = self.value()
            decision = rekeyed["decisions"].pop(sha) | {field: value}
            rekeyed["decisions"][digest(decision)] = decision
            for e in rekeyed["journal"]:
                e["subject"] = digest(decision)
            cases.append((reason, rekeyed))
        for reason, value in cases:
            with self.subTest(reason):
                self.refused(reason, pr.ProfileRegistry.from_bytes, canonical(value))


class PersistenceTests(RefusalCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "profiles.json"

    def test_save_is_atomic_private_and_refuses_lost_updates(self):
        base = pr.ProfileRegistry.empty(SCOPE)
        pr.save(self.path, base)
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)
        loaded = pr.load(self.path)
        one = loaded.record(decide(n=4, decision="pending"), at=20)
        two = loaded.record(decide(n=4, decision="rejected"), at=20)
        pr.save(self.path, one)
        self.refused("concurrent-update", pr.save, self.path, two)
        self.assertEqual(pr.load(self.path).sha256, one.sha256)
        self.refused("concurrent-update", pr.save, self.path, pr.ProfileRegistry.empty("task-002"))
        self.assertEqual(sorted(os.listdir(self.temp.name)), ["profiles.json", "profiles.json.lock"])

    def test_save_refuses_unavailable_or_corrupt_targets(self):
        registry = pr.ProfileRegistry.empty(SCOPE)
        self.refused("registry-unavailable", pr.save, Path(self.temp.name) / "no" / "p.json",
                     registry)
        self.path.write_bytes(b"{")
        self.refused("invalid-json", pr.save, self.path, registry)
        self.assertEqual(self.path.read_bytes(), b"{")

    def test_load_refuses_non_regular_files(self):
        self.refused("registry-unavailable", pr.load, Path(self.temp.name))
        fifo = Path(self.temp.name) / "fifo.json"
        os.mkfifo(fifo)
        self.refused("registry-unavailable", pr.load, fifo)

    def test_load_refuses_missing_or_linked_files(self):
        self.refused("registry-unavailable", pr.load, self.path)
        pr.save(self.path, pr.ProfileRegistry.empty(SCOPE))
        link = Path(self.temp.name) / "link.json"
        link.symlink_to(self.path)
        self.refused("registry-unavailable", pr.load, link)


if __name__ == "__main__":
    unittest.main()
