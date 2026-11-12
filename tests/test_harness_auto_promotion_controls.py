# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049/T008 offline controls for an optional automatic-promotion policy.

Reference evaluator and stop handler for the rules in ``auto-promotion-assessment.md``.
Synthetic doubles only; nothing here activates anything, and ``agent_braid.harness_promotion``
still refuses every automatic actor. The assessment disposition is asserted at the end.
"""
from pathlib import Path
import unittest

from agent_braid import harness_promotion as pr
from tests.test_harness_promotion import IDENTITY, SAFE, SCOPE, RefusalCase, decide, h

PROPOSER = {"kind": "proposer", "id": "proposer-1"}
CHECKER = {"kind": "independent-check", "id": "checker-1"}
CLASS = "task-local-guidance-packaging"
ALLOWED_LAYERS = ("context-packaging", "guidance")  # closed allowlist; everything else abstains
PENDING = ["conflict-precision-recall", "false-safe-admissions", "interrupted-recovery",
           "interventions", "rework", "useful-parallelism"]

# Limits fixed before evaluation (fixedAt < every decision tick used below).
POLICY = {"fixedAt": 1, "changeClass": CLASS, "scope": "task-local", "cohorts": ["synthetic"],
          "effects": ["write-workspace"], "allowedLayers": list(ALLOWED_LAYERS),
          "tolerablePendingEndpoints": [], "budgetCap": 100,
          "canary": {"size": 3, "maxFailures": 0}}
# Control-only policy: tolerates the six endpoints T003 still lists as pending.
CONTROL_POLICY = POLICY | {"tolerablePendingEndpoints": PENDING}
CLEAR = {"revoked": (), "conflicts": (), "spent": 0, "incident": False}
_DERIVED = object()


def pending(**kwargs):
    """An undecided record at tick 10, after every policy's fixedAt."""
    return decide(decision="pending", **{"at": 10} | kwargs)


def candidate(**override):
    return {"changeClass": CLASS, "scope": "task-local", "layersChanged": ["guidance"],
            "proposer": PROPOSER} | override


def acceptance(record, **override):
    data = record.to_dict()
    return {"checker": CHECKER, "verdict": "accepted", "decisionSha256": record.sha256,
            "evaluationSha256": data["evaluationSha256"],
            "candidateSha256": data["profile"]["candidateSha256"]} | override


def _ids(value):
    return type(value) in (list, tuple) and all(type(v) is str for v in value)


def _well_formed(policy, cand, accept, current, revoked, conflicts, spent, incident):
    ok = (type(policy) is dict and type(cand) is dict and type(current) is dict
          and type(incident) is bool and type(spent) is int and spent >= 0
          and _ids(revoked) and _ids(conflicts)
          and type(accept) is dict
          and type(policy.get("fixedAt")) is int and type(policy.get("budgetCap")) is int
          and all(_ids(policy.get(k)) for k in ("cohorts", "effects", "allowedLayers",
                                                "tolerablePendingEndpoints"))
          and _ids(cand.get("layersChanged")) and type(cand.get("proposer")) is dict
          and type(accept.get("checker")) is dict)
    return ok


def assess(record, *, policy, cand, accept=_DERIVED, current=IDENTITY, revoked=None,
           conflicts=None, spent=None, incident=None):
    """First failing rule as an abstention; otherwise an eligible proposal that grants nothing.

    Every stop signal is required: an omitted or malformed input abstains, never passes.
    """
    d = record.to_dict()
    accept = acceptance(record) if accept is _DERIVED else accept

    def no(reason):
        return {"outcome": "abstain", "reason": reason, "executionAuthorization": False}

    if not _well_formed(policy, cand, accept or {"checker": {}}, current,
                        revoked, conflicts, spent, incident):
        return no("invalid-input")
    profile = d["profile"]
    cited = {d["registrationSha256"], d["evaluationSha256"], d["costReportSha256"],
             *d["evidenceSha256s"]}
    if d["decision"] != "pending":
        return no("decision-not-pending")
    if not 0 <= policy["fixedAt"] < d["decidedAt"]:
        return no("limits-not-fixed-before-evaluation")
    if cand.get("changeClass") != policy["changeClass"]:
        return no("change-class-ineligible")
    if not cand["layersChanged"] or not set(cand["layersChanged"]) <= set(policy["allowedLayers"]):
        return no("layer-not-allowed")
    if cand.get("scope") != policy["scope"] or profile["scope"] != SCOPE:
        return no("scope-changed")
    if not set(profile["effects"]) <= set(policy["effects"]):
        return no("effect-outside-bound")
    if d["cohort"] not in policy["cohorts"] or profile["cohort"] != d["cohort"]:
        return no("cohort-not-adopted")
    if set(profile["identity"]) != set(IDENTITY) or any(
            current.get(k) != v for k, v in profile["identity"].items()):
        return no("stale-identity")
    if cited & set(revoked):
        return no("evidence-revoked")
    if conflicts:
        return no("evidence-conflict")
    if not d["regression"] or any(v != "noninferior" for v in d["regression"].values()):
        return no("regression-not-covered")
    if set(d["pendingEndpoints"]) - set(policy["tolerablePendingEndpoints"]):
        return no("pending-endpoints")
    if set(d["safety"]) != set(SAFE) or any(v != 0 for v in d["safety"].values()):
        return no("safety-violation")
    if incident:
        return no("incident-stop")
    if spent > policy["budgetCap"]:
        return no("budget-exhausted")
    if accept is None:
        return no("acceptance-missing")
    checker = accept["checker"]
    if (set(checker) != {"kind", "id"} or checker["kind"] != "independent-check"
            or type(checker["id"]) is not str or not checker["id"]
            or checker["id"] == cand["proposer"].get("id")):
        return no("acceptance-not-independent")
    for key, want in (("decisionSha256", record.sha256), ("evaluationSha256", d["evaluationSha256"]),
                      ("candidateSha256", profile["candidateSha256"])):
        if accept.get(key) != want:
            return no("acceptance-forged")
    if accept.get("verdict") != "accepted":
        return no("acceptance-rejected")
    return {"outcome": "eligible-proposal", "reason": None, "executionAuthorization": False,
            "activation": "requires-separate-adr-and-operator-decision"}


def canary(policy, observations):
    """Replay canary observations ('ok'/'fail'/'violation'); anything else halts."""
    limits, failures = policy["canary"], 0
    if limits["size"] < 1:
        return "halted:invalid-canary"
    for i, seen in enumerate(observations, 1):
        if seen == "violation":
            return "halted:safety-violation"
        if seen not in ("ok", "fail"):
            return "halted:unknown-observation"
        failures += seen == "fail"
        if failures > limits["maxFailures"]:
            return "halted:failure-budget"
        if i > limits["size"]:
            return "halted:overrun"
    return "complete" if len(observations) == limits["size"] else "running"


STOP_REASONS = {"drift": "drift-stop", "canary": "canary-halt", "incident": "incident-stop"}


def stop(registry, trigger, *, at, evidence=None):
    """Map a stop trigger to the existing registry transition (rollback or revocation)."""
    if trigger == "revocation":
        return registry.revoke_evidence(evidence, at=at, reason="lesson-revoked")
    if trigger not in STOP_REASONS:
        raise pr.PromotionError("invalid-trigger")
    return registry.rollback(at=at, reason=STOP_REASONS[trigger])


def active_registry(*decisions):
    registry = pr.ProfileRegistry.empty(SCOPE)
    for decision in decisions:
        registry = registry.begin(decision, current=IDENTITY, at=20).commit(current=IDENTITY, at=20)
    return registry


def promoted_over(first, **kwargs):
    """Registry serving a model-b profile whose rollback target is ``first``."""
    current = IDENTITY | {"model": "model-b:2"}
    second = decide(model="model-b:2", rollback=first.to_dict()["profileSha256"], **kwargs)
    return second, active_registry(first).begin(second, current=current, at=30).commit(
        current=current, at=30)


class EligibilityTests(unittest.TestCase):
    def run_assess(self, record=None, *, policy=CONTROL_POLICY, cand=None, **kwargs):
        record = record or pending()
        return assess(record, policy=policy, cand=cand or candidate(), **CLEAR | kwargs)

    def abstains(self, reason, **kwargs):
        got = self.run_assess(**kwargs)
        self.assertEqual((got["outcome"], got["reason"]), ("abstain", reason))
        self.assertIs(got["executionAuthorization"], False)

    def test_narrow_low_risk_candidate_yields_a_proposal_that_grants_nothing(self):
        got = self.run_assess()
        self.assertEqual(got["outcome"], "eligible-proposal")
        self.assertIs(got["executionAuthorization"], False)
        self.assertEqual(got["activation"], "requires-separate-adr-and-operator-decision")
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)

    def test_only_an_undecided_record_is_assessed(self):
        for outcome in ("rejected", "approved"):
            self.abstains("decision-not-pending", record=decide(decision=outcome, at=10))

    def test_native_cohort_is_not_covered_by_a_synthetic_adoption(self):
        self.abstains("cohort-not-adopted", record=pending(cohort="native"))

    def test_profile_cohort_must_match_the_evaluated_cohort(self):
        # decide() itself refuses a mismatch; a hand-built record is the only way to get one.
        record = pending()
        data = record.to_dict()
        data["profile"] = data["profile"] | {"cohort": "native"}
        forged = pr.PromotionDecision(pr.freeze(data))
        self.abstains("cohort-not-adopted", record=forged,
                      policy=CONTROL_POLICY | {"cohorts": ["synthetic", "native"]})

    def test_eligibility_is_bounded_by_class_layers_scope_and_effects(self):
        self.abstains("change-class-ineligible", cand=candidate(changeClass="tool-addition"))
        for layer in ("authority", "containment", "hooks", "scripts", "settings", "tools", "Tools"):
            self.abstains("layer-not-allowed", cand=candidate(layersChanged=["guidance", layer]))
        self.abstains("layer-not-allowed", cand=candidate(layersChanged=[]))
        self.abstains("scope-changed", cand=candidate(scope="workspace"))
        self.abstains("scope-changed", record=pending(scope="task-002"))
        self.abstains("effect-outside-bound", policy=CONTROL_POLICY | {"effects": ["read-workspace"]})
        self.abstains("effect-outside-bound", policy=CONTROL_POLICY | {"effects": []})

    def test_limits_must_be_fixed_before_the_record(self):
        for fixed in (10, 11, -1):
            self.abstains("limits-not-fixed-before-evaluation",
                          policy=CONTROL_POLICY | {"fixedAt": fixed})

    def test_missing_regression_coverage_and_safety_counts_abstain(self):
        self.abstains("regression-not-covered", record=pending(n=4))
        for key in SAFE:
            for bad in (1, None):
                self.abstains("safety-violation", record=pending(safety=SAFE | {key: bad}))

    def test_pending_endpoints_need_every_one_tolerated(self):
        record = pending()
        self.abstains("pending-endpoints", record=record, policy=POLICY)  # production: none
        short = CONTROL_POLICY | {"tolerablePendingEndpoints": PENDING[1:]}
        self.abstains("pending-endpoints", record=record, policy=short)
        wide = CONTROL_POLICY | {"tolerablePendingEndpoints": PENDING + ["extra"]}
        self.assertEqual(self.run_assess(record, policy=wide)["outcome"], "eligible-proposal")

    def test_stale_identity_on_any_key_and_every_stop_signal_abstain(self):
        record = pending(evidence=[h("lesson-1")])
        d = record.to_dict()
        for key in IDENTITY:
            self.abstains("stale-identity", record=record,
                          current=IDENTITY | {key: h("drift") if key.endswith("Sha256") else "x:1"})
        self.abstains("stale-identity", record=record,
                      current={k: v for k, v in IDENTITY.items() if k != "host"})
        for cited in (h("lesson-1"), d["registrationSha256"], d["evaluationSha256"],
                      d["costReportSha256"]):
            self.abstains("evidence-revoked", record=record, revoked=[cited])
        self.abstains("evidence-conflict", record=record, conflicts=[h("lesson-2")])
        self.abstains("budget-exhausted", record=record, spent=101)
        self.abstains("incident-stop", record=record, incident=True)
        ok = self.run_assess(record, spent=100, revoked=[h("unrelated")])
        self.assertEqual(ok["outcome"], "eligible-proposal")

    def test_earlier_rule_wins_when_several_fail(self):
        bad = pending(safety=SAFE | {"unsafeAdmissions": 1})
        self.assertEqual(self.run_assess(pending(n=4, safety=SAFE | {"unsafeAdmissions": 1}),
                                         accept=None, incident=True)["reason"],
                         "regression-not-covered")
        self.assertEqual(self.run_assess(bad, accept=None, incident=True)["reason"],
                         "safety-violation")
        self.assertEqual(self.run_assess(accept=None, incident=True)["reason"], "incident-stop")
        self.assertEqual(self.run_assess(accept=None)["reason"], "acceptance-missing")
        self.assertEqual(self.run_assess(cand=candidate(changeClass="x", layersChanged=["tools"]))
                         ["reason"], "change-class-ineligible")

    def test_missing_or_malformed_inputs_abstain_instead_of_passing_or_crashing(self):
        record = pending()
        base = {"policy": CONTROL_POLICY, "cand": candidate()} | CLEAR
        for key in ("revoked", "conflicts", "spent", "incident"):
            got = assess(record, **base | {key: None})
            self.assertEqual(got["reason"], "invalid-input", key)
        no_proposer = {k: v for k, v in candidate().items() if k != "proposer"}
        no_budget = {k: v for k, v in CONTROL_POLICY.items() if k != "budgetCap"}
        for key, bad in (("spent", float("nan")), ("spent", -5), ("spent", "5"),
                         ("incident", 0), ("revoked", "abc"), ("current", None),
                         ("cand", {}), ("cand", candidate(layersChanged="guidance")),
                         ("cand", no_proposer), ("accept", "accepted"),
                         ("accept", acceptance(record) | {"checker": "checker-1"}),
                         ("policy", no_budget), ("policy", CONTROL_POLICY | {"fixedAt": None}),
                         ("policy", CONTROL_POLICY | {"cohorts": "synthetic-native"}),
                         ("policy", CONTROL_POLICY | {"fixedAt": True})):
            got = assess(record, **base | {key: bad})
            self.assertEqual((got["outcome"], got["reason"]), ("abstain", "invalid-input"), key)

    def test_acceptance_must_be_present_independent_bound_and_positive(self):
        record = pending()
        good = acceptance(record)
        self.abstains("acceptance-missing", record=record, accept=None)
        for checker in ({"kind": "independent-check", "id": "proposer-1"}, PROPOSER,
                        {"kind": "independent-check", "id": None},
                        {"kind": "independent-check"}, {}):
            self.abstains("acceptance-not-independent", record=record,
                          accept=good | {"checker": checker})
        for key in ("decisionSha256", "evaluationSha256", "candidateSha256"):
            self.abstains("acceptance-forged", record=record, accept=good | {key: h("forged")})
        self.abstains("acceptance-forged", record=pending(at=11), accept=good)  # stale record
        self.abstains("acceptance-rejected", record=record, accept=good | {"verdict": "rejected"})
        self.abstains("acceptance-rejected", record=record,
                      accept={k: v for k, v in good.items() if k != "verdict"})


class StopControlTests(RefusalCase):
    def test_canary_halts_on_any_violation_failure_budget_overrun_or_unknown(self):
        self.assertEqual(canary(POLICY, []), "running")
        self.assertEqual(canary(POLICY, ["ok"]), "running")
        self.assertEqual(canary(POLICY, ["ok", "ok", "ok"]), "complete")
        self.assertEqual(canary(POLICY, ["ok", "fail"]), "halted:failure-budget")
        self.assertEqual(canary(POLICY, ["ok", "violation"]), "halted:safety-violation")
        self.assertEqual(canary(POLICY, ["fail", "violation"]), "halted:failure-budget")
        self.assertEqual(canary(POLICY, ["ok"] * 3 + ["violation"]), "halted:safety-violation")
        self.assertEqual(canary(POLICY, ["ok"] * 3 + ["fail"]), "halted:failure-budget")
        self.assertEqual(canary(POLICY, ["ok"] * 4), "halted:overrun")
        for bad in ("okk", None, "timeout"):
            self.assertEqual(canary(POLICY, ["ok", bad, "ok"]), "halted:unknown-observation")
        tolerant = POLICY | {"canary": {"size": 3, "maxFailures": 1}}
        self.assertEqual(canary(tolerant, ["fail", "ok", "ok"]), "complete")
        self.assertEqual(canary(POLICY | {"canary": {"size": 0, "maxFailures": 0}}, []),
                         "halted:invalid-canary")

    def test_drift_canary_and_incident_stops_roll_back_to_the_prior_profile(self):
        first = decide(evidence=[h("lesson-1")])
        _, promoted = promoted_over(first)
        drifted = IDENTITY | {"model": "model-b:2", "policySha256": h("policy-b")}
        self.assertEqual(promoted.resolve(drifted, cohort="synthetic").reason, "stale-policy")
        for trigger, reason in STOP_REASONS.items():
            back = stop(promoted, trigger, at=40)
            served = back.resolve(IDENTITY, cohort="synthetic")
            self.assertEqual(served.decisionSha256, first.sha256)
            self.assertIs(served.executionAuthorization, False)
            self.assertEqual(back.journal[-1]["reason"], reason)
        self.refused("invalid-trigger", stop, promoted, "budget", at=40)

    def test_resolve_serves_nothing_on_any_identity_change(self):
        active = active_registry(decide())
        for key, reason in (("sourceSha256", "stale-source"), ("host", "stale-host"),
                            ("model", "stale-model"), ("toolSetSha256", "stale-tool"),
                            ("policySha256", "stale-policy")):
            moved = IDENTITY | {key: h("d") if key.endswith("Sha256") else "moved:1"}
            self.assertEqual(active.resolve(moved, cohort="synthetic").reason, reason)

    def test_stale_manifest_cannot_start_or_finish_a_transition(self):
        record = decide(decision="approved")
        drifted = IDENTITY | {"sourceSha256": h("new-source")}
        empty = pr.ProfileRegistry.empty(SCOPE)
        self.refused("stale-source", empty.begin, record, current=drifted, at=20)
        begun = empty.begin(record, current=IDENTITY, at=20)
        self.refused("stale-source", begun.commit, current=drifted, at=21)

    def test_revocation_withdraws_every_citing_profile_and_skips_revoked_fallbacks(self):
        one = decide(evidence=[h("lesson-1")])
        second, mid = promoted_over(one, evidence=sorted([h("lesson-1"), h("lesson-2")]))
        third = decide(model="model-c:3", rollback=second.to_dict()["profileSha256"],
                       evidence=[h("lesson-3")])
        top = IDENTITY | {"model": "model-c:3"}
        registry = mid.begin(third, current=top, at=35).commit(current=top, at=35)
        after3 = stop(registry, "revocation", at=40, evidence=h("lesson-3"))
        served = after3.resolve(IDENTITY | {"model": "model-b:2"}, cohort="synthetic")
        self.assertEqual(served.decisionSha256, second.sha256)
        # lesson-1 is cited by both remaining profiles: both are withdrawn, nothing is served.
        after1 = stop(after3, "revocation", at=41, evidence=h("lesson-1"))
        self.assertEqual(after1.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")
        self.refused("revoked-evidence", after1.begin, one, current=IDENTITY, at=50)
        self.refused("invalid-evidence", stop, registry, "revocation", at=40, evidence=None)
        # A revoked lesson keeps a later candidate ineligible.
        got = assess(pending(evidence=[h("lesson-1")], at=60), policy=CONTROL_POLICY,
                     cand=candidate(), **CLEAR | {"revoked": sorted(after1.revoked)})
        self.assertEqual(got["reason"], "evidence-revoked")

    def test_revocation_falls_back_to_the_newest_prior_profile_with_valid_evidence(self):
        first = decide(evidence=[h("lesson-1")])
        _, promoted = promoted_over(first, evidence=[h("lesson-2")])
        fallback = stop(promoted, "revocation", at=40, evidence=h("lesson-2"))
        self.assertEqual(fallback.resolve(IDENTITY, cohort="synthetic").decisionSha256, first.sha256)

    def test_rollback_failure_is_visible_and_never_leaves_a_served_profile(self):
        self.refused("no-active-profile", stop, pr.ProfileRegistry.empty(SCOPE), "incident", at=40)
        gone = stop(active_registry(decide()), "incident", at=40)
        self.assertEqual(gone.resolve(IDENTITY, cohort="synthetic").reason, "no-active-profile")
        self.refused("no-active-profile", stop, gone, "drift", at=41)
        self.refused("decision-withdrawn", gone.begin, decide(), current=IDENTITY, at=50)


class DispositionTests(unittest.TestCase):
    def test_assessment_disposition_is_deferred_and_matches_the_document(self):
        text = (Path(__file__).resolve().parent.parent / "specs" / "049-harness-evaluation-learning"
                / "auto-promotion-assessment.md").read_text()
        self.assertIn("Disposition: **deferred**", text)
        record = pending()
        # Current evidence: T003 still lists six pending endpoints and the production policy
        # tolerates none, so it abstains.
        got = assess(record, policy=POLICY, cand=candidate(), **CLEAR)
        self.assertEqual(got["reason"], "pending-endpoints")
        self.assertEqual(sorted(record.to_dict()["pendingEndpoints"]), PENDING)
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)
        self.assertIs(got["executionAuthorization"], False)
        robot = {"kind": "automatic-policy", "id": "policy-1"}
        for outcome in pr.DECISIONS:
            with self.assertRaises(pr.PromotionError) as ctx:
                decide(actor=robot, decision=outcome)
            self.assertEqual(ctx.exception.reason, "automatic-promotion-disabled")


if __name__ == "__main__":
    unittest.main()
