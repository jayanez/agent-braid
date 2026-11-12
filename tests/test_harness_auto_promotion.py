# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T009 controls for the disabled-by-default automatic-promotion engine.

Synthetic doubles only: nothing here activates anything, and the engine grants nothing.
"""
from hashlib import sha256
from pathlib import Path
import ast
import re
import unittest

from agent_braid import harness_auto_promotion as ap
from agent_braid import harness_evaluation as ev
from agent_braid import harness_promotion as pr
from agent_braid.system_one import digest, freeze

from tests.test_harness_evaluation import Cohort, all_pass, edited
from tests.test_harness_promotion import HUMAN, IDENTITY, SAFE, SCOPE, RefusalCase, h, profile
from tests.test_harness_refinement import make_policy

ROOT = Path(__file__).resolve().parent.parent
ASSESSMENT = ROOT / ap.ASSESSMENT_PATH
PROPOSER = {"kind": "proposer", "id": "proposer-1"}
CHECKER = {"kind": "independent-check", "id": "checker-1"}
PENDING = ["conflict-precision-recall", "false-safe-admissions", "interrupted-recovery",
           "interventions", "rework", "useful-parallelism"]
POLICY_DATA = {"format": ap.POLICY_FORMAT, "assessmentSha256": ap.ASSESSMENT_SHA256, "fixedAt": 1,
               "changeClass": ap.CHANGE_CLASS, "scope": ap.SCOPE, "cohorts": ["synthetic"],
               "effects": ["write-workspace"], "allowedLayers": ["context-packaging", "guidance"],
               "tolerablePendingEndpoints": [], "budgetCap": 100,
               "canary": {"size": 3, "maxFailures": 0}, "adoption": None,
               "executionAuthorization": False}
# Control-only: tolerates the six endpoints that every real T003 report still lists as pending.
CONTROL = POLICY_DATA | {"tolerablePendingEndpoints": PENDING}
CLEAR = {"revoked": (), "conflicts": (), "spent": 0, "incident": False}


def policy(**over):
    return ap.build_policy(POLICY_DATA | over)


def row(path, content):
    return {"path": path, "sha256": sha256(content).hexdigest(), "sizeBytes": len(content)}


def rows(*items):
    return sorted((row(p, c) for p, c in items), key=lambda r: r["path"])


BASE = rows(("guidance/main.md", b"Retain the static base.\n"))
CANDIDATE = rows(("guidance/main.md", b"Retain the static base.\n"),
                 ("guidance/general.md", b"Be brief.\n"))


class World:
    """A real T003 registration and report whose arm C binds ``candidate`` rows."""

    def __init__(self, candidate=CANDIDATE, base=BASE, *, n=19, decision="pending", at=10,
                 cohort="synthetic", **record):
        group = Cohort(n)
        registration = group.register()
        arms = registration.to_dict()["arms"]
        # The refinement lab only produces guidance candidates, so bind other inventories here.
        group.candidates["A"], group.candidates["C"] = digest(base), digest(candidate)
        arms["A"]["candidateSha256"], arms["C"]["candidateSha256"] = group.candidates["A"], group.candidates["C"]
        self.registration = edited(registration, ev.Registration, arms=arms)
        self.report = group.evaluate(group.rows(all_pass(group)), registration=self.registration)
        self.base, self.candidate = base, candidate
        self.record = pr.decide(
            self.registration, self.report, profile=profile(self.registration, cohort=cohort),
            actor=HUMAN, decision=decision, safety=record.pop("safety", SAFE),
            evidence=record.pop("evidence", []), rollback_target=None, limits=["synthetic-only"],
            at=at)
        self.registry = pr.ProfileRegistry.empty(SCOPE)

    def accept(self, **over):
        d = self.record.to_dict()
        return {"checker": CHECKER, "verdict": "accepted", "decisionSha256": self.record.sha256,
                "evaluationSha256": d["evaluationSha256"],
                "candidateSha256": d["profile"]["candidateSha256"]} | over

    def run(self, pol=None, record=None, **over):
        args = {"registration": self.registration, "evaluation": self.report,
                "base_files": self.base, "candidate_files": self.candidate,
                "proposer": PROPOSER, "acceptance": self.accept(), "registry": self.registry,
                "identity": IDENTITY, "evaluated_at": 10} | CLEAR | over
        return ap.assess(pol or ap.build_policy(CONTROL), record or self.record, **args)


class PolicyTests(unittest.TestCase):
    def refuses(self, reason, **over):
        with self.assertRaises(ap.AutoPromotionError) as ctx:
            ap.build_policy(POLICY_DATA | over)
        self.assertEqual(ctx.exception.reason, reason)

    def test_valid_policy_is_immutable_hashed_and_grants_nothing(self):
        pol = policy()
        self.assertIs(pol.executionAuthorization, False)
        self.assertEqual(pol.sha256, digest(pol.data))
        self.assertEqual(ap.build_policy(pol.to_dict()).sha256, pol.sha256)
        with self.assertRaises(TypeError):
            pol.data["budgetCap"] = 10_000
        pol.to_dict()["budgetCap"] = 10_000  # a copy
        self.assertEqual(pol.data["budgetCap"], 100)

    def test_native_cohort_wider_layers_and_adoption_are_not_representable(self):
        self.refuses("cohort-not-adoptable", cohorts=["native", "synthetic"])
        self.refuses("cohort-not-adoptable", cohorts=["native"])
        self.refuses("layer-not-adoptable", allowedLayers=["guidance", "tools"])
        self.refuses("layer-not-adoptable", allowedLayers=["Guidance"])
        self.refuses("invalid-policy", adoption={"operator": "founder"})
        self.refuses("invalid-policy", executionAuthorization=True)
        self.refuses("invalid-policy", changeClass="tool-addition")
        self.refuses("invalid-policy", scope="workspace")
        self.refuses("invalid-policy", assessmentSha256=h("another-contract"))

    def test_malformed_policies_and_limits_refuse(self):
        for key in POLICY_DATA:
            partial = {k: v for k, v in POLICY_DATA.items() if k != key}
            with self.assertRaises(ap.AutoPromotionError):
                ap.build_policy(partial)
        for bad in ({"fixedAt": True}, {"fixedAt": -1}, {"fixedAt": None}, {"budgetCap": "100"},
                    {"budgetCap": 1.5}, {"cohorts": "synthetic"}, {"cohorts": []},
                    {"effects": ["b", "a"]}, {"effects": ["a", "a"]},
                    {"tolerablePendingEndpoints": ["z", "a"]},
                    {"canary": {"size": 0, "maxFailures": 0}},
                    {"canary": {"size": 3, "maxFailures": -1}},
                    {"canary": {"size": 3}}, {"canary": {"size": True, "maxFailures": 0}},
                    {"unknown": 1}):
            with self.assertRaises(ap.AutoPromotionError, msg=str(bad)):
                ap.build_policy(POLICY_DATA | bad)
        with self.assertRaises(ap.AutoPromotionError):
            ap.build_policy(None)

    def test_contract_hash_and_rule_table_match_the_assessment_document(self):
        text = ASSESSMENT.read_text()
        self.assertEqual(sha256(ASSESSMENT.read_bytes()).hexdigest(), ap.ASSESSMENT_SHA256)
        table = re.findall(r"^\| (\d+) \| .*? \| `([a-z*-]+)` \|$", text, re.M)
        self.assertEqual([int(n) for n, _ in table], list(range(1, 17)))
        self.assertEqual([reason for _, reason in table[:15]], list(ap.RULES[:15]))
        self.assertEqual(table[15][1], "acceptance-*")
        self.assertEqual(ap.RULES[15], "acceptance")
        self.assertIn("Disposition: **deferred**", text)


class DerivationTests(unittest.TestCase):
    def test_inert_guidance_change_is_the_policy_class_layer_and_scope(self):
        got = ap.derive_candidate(BASE, CANDIDATE)
        self.assertEqual(got, {"changeClass": ap.CHANGE_CLASS, "layersChanged": ["guidance"],
                               "scope": ap.SCOPE, "changedPaths": ["guidance/general.md"]})

    def test_only_changed_paths_count_and_deletion_is_a_change(self):
        same = ap.derive_candidate(BASE, BASE)
        self.assertEqual((same["layersChanged"], same["changeClass"]),
                         ([], ap.CHANGE_CLASS))
        deleted = ap.derive_candidate(rows(("tools/x.md", b"1")), [])
        self.assertEqual(deleted["layersChanged"], ["tools"])

    def test_executable_protected_hidden_and_root_paths_leave_the_class_and_layers(self):
        cases = {"guidance/run.sh": (["guidance"], "not-inert-text"),
                 "guidance/run.py": (["guidance"], "not-inert-text"),
                 "scripts/run.md": (["scripts"], ap.CHANGE_CLASS),
                 "guidance/hooks/x.md": (["guidance", "hooks"], ap.CHANGE_CLASS),
                 "guidance/Tools.md": (["guidance", "tools"], ap.CHANGE_CLASS),
                 "guidance/.hidden.md": (["guidance", "hidden"], ap.CHANGE_CLASS),
                 "lessons/a.md": (["lessons"], ap.CHANGE_CLASS),
                 "guidance.md": (["(root)"], ap.CHANGE_CLASS),
                 "Guidance/a.md": (["Guidance"], ap.CHANGE_CLASS),
                 "tools/x.md": (["tools"], ap.CHANGE_CLASS),
                 "guidance/tools .md": (["guidance", "tools"], ap.CHANGE_CLASS),
                 "guidance/hooks..md": (["guidance", "hooks"], ap.CHANGE_CLASS)}
        for path, (layers, klass) in cases.items():
            got = ap.derive_candidate(BASE, rows(*BASE_ITEMS, (path, b"x\n")))
            self.assertEqual((got["layersChanged"], got["changeClass"]), (layers, klass), path)

    def test_scope_is_task_local_only_inside_the_laboratory_ceilings(self):
        many = rows(*((f"guidance/f{i:02d}.md", b"x\n") for i in range(33)))
        self.assertEqual(ap.derive_candidate(BASE, many)["scope"], "beyond-task-local")
        large = rows(("guidance/big.md", b"x" * 32_769))
        self.assertEqual(ap.derive_candidate(BASE, large)["scope"], "beyond-task-local")
        total = rows(*((f"guidance/t{i}.md", b"x" * 30_000) for i in range(9)))  # 270 kB in total
        self.assertEqual(ap.derive_candidate(BASE, total)["scope"], "beyond-task-local")

    def test_malformed_inventories_derive_nothing(self):
        good = CANDIDATE[0]
        for bad in (None, "x", [None], [good | {"extra": 1}], [good | {"sha256": "ab"}],
                    [good | {"sizeBytes": -1}], [good | {"sizeBytes": True}],
                    [good | {"path": "../x.md"}], [good | {"path": "a\\b.md"}],
                    [good | {"path": "a/b/c/d/e.md"}], list(reversed(CANDIDATE)),
                    [good, good], [good] * (ap.MAX_ROWS + 1)):
            self.assertIsNone(ap.derive_candidate(BASE, bad), str(bad)[:40])
            self.assertIsNone(ap.derive_candidate(bad, BASE), str(bad)[:40])


BASE_ITEMS = (("guidance/main.md", b"Retain the static base.\n"),)


class EligibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = World()

    def abstains(self, reason, world=None, rule=None, **kwargs):
        world = world or self.world
        got = world.run(**kwargs)
        self.assertEqual((got.outcome, got.reason), ("abstain", reason), got)
        self.assertIs(got.executionAuthorization, False)
        self.assertIs(got.to_dict()["executionAuthorization"], False)
        if rule is not None:
            self.assertEqual(got.rule, rule)
        return got

    def test_narrow_candidate_yields_a_proposal_that_grants_nothing(self):
        got = self.world.run()
        self.assertTrue(got.eligible)
        self.assertEqual(got.to_dict()["activation"], "requires-separate-adr-and-operator-decision")
        self.assertIs(got.executionAuthorization, False)
        self.assertEqual(got.decisionSha256, self.world.record.sha256)
        self.assertEqual(got.policySha256, ap.build_policy(CONTROL).sha256)
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)

    def test_current_evidence_abstains_with_pending_endpoints_under_the_production_policy(self):
        record = self.world.record
        self.assertEqual(sorted(record.to_dict()["pendingEndpoints"]), PENDING)
        got = self.abstains("pending-endpoints", pol=policy(), rule=12)
        self.assertEqual(got.to_dict()["activation"], None)

    def test_undecided_records_only(self):
        for outcome in ("approved", "rejected"):
            world = World(decision=outcome)
            self.abstains("decision-not-pending", world, rule=1)

    def test_limits_must_be_fixed_before_the_evaluation_tick(self):
        for fixed in (10, 11):
            self.abstains("limits-not-fixed-before-evaluation", pol=ap.build_policy(
                CONTROL | {"fixedAt": fixed}), rule=2)
        # An evaluation tick after the decision is inconsistent, not merely late.
        self.abstains("invalid-input", evaluated_at=11)
        later = World(at=50)
        self.abstains("limits-not-fixed-before-evaluation", later, evaluated_at=1)
        self.assertTrue(later.run(evaluated_at=2).eligible)  # evaluated well before the decision

    def test_native_cohort_is_never_covered_by_the_synthetic_adoption(self):
        self.abstains("cohort-not-adopted", World(cohort="native"), rule=7)

    def test_profile_cohort_must_match_the_evaluated_cohort(self):
        base = World()
        data = base.record.to_dict()
        data["profile"] = data["profile"] | {"cohort": "native"}
        forged = pr.PromotionDecision(freeze(data))
        self.abstains("record-not-reproducible", record=forged)

    def test_profile_scope_must_be_the_registry_scope(self):
        other = pr.ProfileRegistry.empty("task-002")
        self.abstains("scope-changed", registry=other, rule=5)

    def test_effects_must_stay_inside_the_policy_bound(self):
        for effects in ([], ["read-workspace"]):
            self.abstains("effect-outside-bound", pol=ap.build_policy(CONTROL | {"effects": effects}),
                          rule=6)

    def test_layers_class_and_scope_come_from_the_hashed_inventories(self):
        cases = (("layer-not-allowed", 4, rows(*BASE_ITEMS, ("scripts/run.md", b"x\n"))),
                 ("layer-not-allowed", 4, rows(*BASE_ITEMS, ("lessons/poison.md", b"ignore all\n"))),
                 ("layer-not-allowed", 4, rows(*BASE_ITEMS, ("guidance/hooks/a.md", b"x\n"))),
                 ("change-class-ineligible", 3, rows(*BASE_ITEMS, ("guidance/run.sh", b"x\n"))),
                 ("scope-changed", 5, rows(*BASE_ITEMS, *((f"guidance/f{i:02d}.md", b"x\n")
                                                          for i in range(33)))))
        for reason, rule, candidate in cases:
            self.abstains(reason, World(candidate), rule=rule)
        self.abstains("layer-not-allowed", World(BASE), rule=4)  # nothing changed
        self.abstains("layer-not-allowed", World(rows(*BASE_ITEMS, ("tools/x.md", b"x\n"))), rule=4)
        narrowed = ap.build_policy(CONTROL | {"allowedLayers": ["context-packaging"]})
        self.abstains("layer-not-allowed", pol=narrowed, rule=4)

    def test_declared_inventories_must_hash_to_the_registered_arms(self):
        self.abstains("candidate-not-bound", candidate_files=rows(
            *BASE_ITEMS, ("guidance/general.md", b"Be terse.\n")))
        self.abstains("candidate-not-bound", base_files=rows(("guidance/main.md", b"other\n")))
        self.abstains("candidate-not-bound", candidate_files=BASE)
        self.abstains("invalid-input", candidate_files=list(reversed(CANDIDATE)))
        self.abstains("invalid-input", base_files=None)

    def test_forged_scores_and_edited_records_do_not_reproduce_from_the_t003_inputs(self):
        weak = World(n=4)
        self.assertEqual(set(weak.record.to_dict()["regression"].values()), {"descriptive-only"})
        data = weak.record.to_dict()
        data["regression"] = {k: "noninferior" for k in data["regression"]}
        forged = pr.PromotionDecision(freeze(data))
        # The forged record is internally valid and even carries its own consistent hash.
        self.assertEqual(forged.sha256, digest(data))
        self.abstains("record-not-reproducible", weak, record=forged)
        self.abstains("regression-not-covered", weak, rule=11)
        # Every other self-asserted field is bound the same way.
        # Derived fields are bound the same way: pending endpoints, cost report, hashes, cohort.
        for key, value in (("pendingEndpoints", []), ("pendingEndpoints", ["interventions"]),
                           ("costReportSha256", h("cheaper")), ("evaluationSha256", h("other")),
                           ("registrationSha256", h("other")), ("cohort", "native"),
                           ("regression", {"synthetic": "noninferior", "extra": "noninferior"})):
            edited_record = pr.PromotionDecision(freeze(self.world.record.to_dict() | {key: value}))
            self.abstains("record-not-reproducible", record=edited_record)
        # Safety counts, limits and extra evidence are human assertions, not derived: they stay
        # caller-asserted and are judged by their own rules (13, 9) instead.
        # Another cohort's report cannot stand in for this record's evaluation.
        self.abstains("record-not-reproducible", evaluation=weak.report)
        self.abstains("record-not-reproducible", registration=weak.registration)
        # An automatic actor is refused by the T013 transaction, so it never reproduces.
        data = self.world.record.to_dict() | {"actor": {"kind": "automatic-policy", "id": "policy-1"}}
        self.abstains("record-not-reproducible", record=pr.PromotionDecision(freeze(data)))

    def test_hand_built_records_and_hostile_identity_values_abstain(self):
        for data in ({}, {"profile": {}}, {"profile": {"candidateSha256": "x"}}):
            self.abstains("record-not-reproducible", record=pr.PromotionDecision(freeze(data)))

        class Always(str):
            def __eq__(self, other):
                return True
            __hash__ = str.__hash__

        self.abstains("invalid-input", identity=IDENTITY | {"host": Always("x")})

    def test_stale_identity_on_any_key_or_missing_key_abstains(self):
        for key in IDENTITY:
            moved = IDENTITY | {key: h("drift") if key.endswith("Sha256") else "x:1"}
            self.abstains("stale-identity", identity=moved, rule=8)
        self.abstains("invalid-input", identity={k: v for k, v in IDENTITY.items() if k != "host"})
        self.abstains("invalid-input", identity=IDENTITY | {"extra": "x"})
        self.abstains("invalid-input", identity=None)

    def test_revoked_citations_poisoned_lessons_and_conflicts_abstain(self):
        world = World(evidence=[h("lesson-1")])
        d = world.record.to_dict()
        for cited in (h("lesson-1"), d["registrationSha256"], d["evaluationSha256"],
                      d["costReportSha256"]):
            self.abstains("evidence-revoked", world, revoked=[cited], rule=9)
        self.abstains("evidence-conflict", world, conflicts=[h("lesson-2")], rule=10)
        self.assertTrue(world.run(revoked=[h("unrelated")]).eligible)
        # The registry's own revocation ledger is honoured even when the caller omits it.
        revoked = pr.ProfileRegistry.empty(SCOPE).revoke_evidence(h("lesson-1"), at=5, reason="lesson-revoked")
        self.abstains("evidence-revoked", world, registry=revoked)

    def test_pending_endpoints_need_every_one_tolerated(self):
        short = ap.build_policy(CONTROL | {"tolerablePendingEndpoints": PENDING[1:]})
        self.abstains("pending-endpoints", pol=short)
        wide = ap.build_policy(CONTROL | {"tolerablePendingEndpoints": sorted(PENDING + ["extra"])})
        self.assertTrue(self.world.run(pol=wide).eligible)

    def test_unknown_or_nonzero_safety_counts_abstain(self):
        # decide() records them honestly; a pending record may carry any safety count.
        for key in SAFE:
            for bad in (1, None):
                self.abstains("safety-violation", World(safety=SAFE | {key: bad}), rule=13)

    def test_incident_and_budget_stops(self):
        self.abstains("incident-stop", incident=True, rule=14)
        self.abstains("budget-exhausted", spent=101, rule=15)
        self.assertTrue(self.world.run(spent=100).eligible)

    def test_earlier_rule_wins_when_several_fail(self):
        bad = World(n=4, safety=SAFE | {"unsafeAdmissions": 1})
        self.assertEqual(bad.run(acceptance=None, incident=True).reason, "regression-not-covered")
        unsafe = World(safety=SAFE | {"unsafeAdmissions": 1})
        self.assertEqual(unsafe.run(acceptance=None, incident=True).reason, "safety-violation")
        self.assertEqual(self.world.run(acceptance=None, incident=True).reason, "incident-stop")
        self.assertEqual(self.world.run(acceptance=None).reason, "acceptance-missing")
        both = World(rows(*BASE_ITEMS, ("guidance/x.sh", b"x\n"), ("tools/y.md", b"y\n")))
        self.assertEqual(both.run().reason, "change-class-ineligible")

    def test_missing_or_malformed_inputs_abstain_instead_of_passing_or_crashing(self):
        w = self.world
        for key in ("revoked", "conflicts", "spent", "incident"):
            self.abstains("invalid-input", **{key: None})
        for key, bad in (("spent", float("nan")), ("spent", -5), ("spent", "5"), ("spent", True),
                         ("spent", 1 << 70), ("incident", 0), ("incident", None),
                         ("revoked", "abc"), ("revoked", [1]), ("revoked", ["short"]),
                         ("conflicts", [h("a"), h("a")]), ("evaluated_at", None),
                         ("evaluated_at", True), ("evaluated_at", -1), ("identity", "x"),
                         ("proposer", None), ("proposer", {"kind": "human", "id": "p"}),
                         ("proposer", {"kind": "proposer"}), ("registry", None),
                         ("registration", None), ("evaluation", w.registration)):
            self.abstains("invalid-input", **{key: bad})
        for bad_policy in (None, ap.AutoPolicy(freeze({"format": "x"})), ap.AutoPolicy(
                freeze(CONTROL | {"cohorts": ["native"]}))):
            got = ap.assess(bad_policy, w.record, registration=w.registration, evaluation=w.report,
                            base_files=w.base, candidate_files=w.candidate, proposer=PROPOSER,
                            acceptance=w.accept(), registry=w.registry, identity=IDENTITY,
                            evaluated_at=10, **CLEAR)
            self.assertEqual((got.outcome, got.reason), ("abstain", "invalid-input"))
        got = ap.assess(ap.build_policy(CONTROL), None, registration=w.registration,
                        evaluation=w.report, base_files=w.base, candidate_files=w.candidate,
                        proposer=PROPOSER, acceptance=w.accept(), registry=w.registry,
                        identity=IDENTITY, evaluated_at=10, **CLEAR)
        self.assertEqual((got.reason, got.decisionSha256), ("invalid-input", None))

    def test_acceptance_must_be_present_independent_bound_and_positive(self):
        w = self.world
        good = w.accept()
        self.abstains("acceptance-missing", acceptance=None, rule=16)
        for checker in ({"kind": "independent-check", "id": "proposer-1"},
                        {"kind": "independent-check", "id": "Proposer-1"}, PROPOSER,
                        {"kind": "independent-check", "id": None},
                        {"kind": "independent-check", "id": ""},
                        {"kind": "independent-check", "id": "bad id"},
                        {"kind": "independent-check"}, {}, "checker-1", None,
                        CHECKER | {"extra": 1}):
            self.abstains("acceptance-not-independent", acceptance=good | {"checker": checker})
        for key in ("decisionSha256", "evaluationSha256", "candidateSha256"):
            self.abstains("acceptance-forged", acceptance=good | {key: h("forged")})
            self.abstains("acceptance-forged", acceptance={k: v for k, v in good.items() if k != key})
        self.abstains("acceptance-forged", acceptance=good | {"extra": 1})
        self.abstains("acceptance-forged", acceptance=World(at=11).accept())  # stale record
        self.abstains("acceptance-rejected", acceptance=good | {"verdict": "rejected"})
        self.abstains("acceptance-rejected", acceptance=good | {"verdict": "ACCEPTED"})
        self.abstains("acceptance-not-independent", acceptance="accepted")
        self.assertTrue(w.run(acceptance=good).eligible)


def eligible_run(world, pol=None, **over):
    """A run moved ``disabled`` -> ``shadow`` -> ``canary`` through a fresh eligible assessment."""
    pol = pol or ap.build_policy(CONTROL)
    inputs = {"registration": world.registration, "evaluation": world.report,
              "base_files": world.base, "candidate_files": world.candidate, "proposer": PROPOSER,
              "acceptance": world.accept(), "registry": world.registry, "identity": IDENTITY,
              "evaluated_at": 10} | CLEAR | over
    run = ap.PolicyRun(pol).enable(HUMAN, at=11)
    return run.begin_canary(world.record, at=12, **inputs)


def active_registry(decision):
    return pr.ProfileRegistry.empty(SCOPE).begin(decision, current=IDENTITY, at=20).commit(
        current=IDENTITY, at=20)


class StateMachineTests(RefusalCase):
    @classmethod
    def setUpClass(cls):
        cls.world = World(evidence=[h("lesson-1")])

    def refuses(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ap.AutoPromotionError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, reason)

    def test_a_run_is_disabled_by_default_and_never_active(self):
        run = ap.PolicyRun(policy())
        self.assertEqual((run.state, run.canary, run.journal), ("disabled", None, ()))
        self.assertIs(run.executionAuthorization, False)
        self.refuses("activation-requires-adoption", run.activate)
        self.refuses("not-shadow", run.begin_canary, self.world.record, at=1)
        self.refuses("not-canary", run.observe, "ok", current=IDENTITY, at=1)
        for state in ("active", "unknown", None):
            self.refuses("invalid-state", ap.PolicyRun, policy(), state)
        self.refuses("invalid-state", ap.PolicyRun, None)
        self.assertEqual(run.stop("incident", at=1).run.state, "stopped")  # stops always work

    def test_only_a_human_operator_enables_shadow_once(self):
        run = ap.PolicyRun(policy())
        self.refuses("automatic-promotion-disabled", run.enable,
                     {"kind": "automatic-policy", "id": "policy-1"}, at=1)
        for bad in (None, {"kind": "human"}, {"kind": "human", "id": "bad id"},
                    {"kind": "robot", "id": "x"}, "human"):
            self.refuses("invalid-input", run.enable, bad, at=1)
        shadow = run.enable(HUMAN, at=1)
        self.assertEqual(shadow.state, "shadow")
        self.assertEqual(run.state, "disabled")  # the original value is untouched
        self.refuses("not-disabled", shadow.enable, HUMAN, at=2)
        self.refuses("policy-stopped", shadow.stop("incident", at=3).run.enable, HUMAN, at=4)
        for bad_time in (None, -1, True, 1 << 41):
            self.refuses("invalid-time", run.enable, HUMAN, at=bad_time)
        self.assertEqual(shadow.stop("incident", at=0).run.state, "stopped")  # a stop never refuses

    def test_canary_needs_a_fresh_eligible_assessment_and_rechecks_everything(self):
        w = self.world
        run = ap.PolicyRun(ap.build_policy(CONTROL)).enable(HUMAN, at=11)
        inputs = {"registration": w.registration, "evaluation": w.report, "base_files": w.base,
                  "candidate_files": w.candidate, "proposer": PROPOSER, "acceptance": w.accept(),
                  "registry": w.registry, "identity": IDENTITY, "evaluated_at": 10} | CLEAR
        for reason, over in (("stale-identity", {"identity": IDENTITY | {"model": "model-b:2"}}),
                             ("acceptance-missing", {"acceptance": None}),
                             ("incident-stop", {"incident": True}),
                             ("evidence-revoked", {"revoked": [h("lesson-1")]}),
                             ("invalid-input", {"spent": None})):
            self.refuses(reason, run.begin_canary, w.record, at=12, **inputs | over)
        self.refuses("pending-endpoints", ap.PolicyRun(policy()).enable(HUMAN, at=11).begin_canary,
                     w.record, at=12, **inputs)
        canary = run.begin_canary(w.record, at=12, **inputs)
        self.assertEqual((canary.state, canary.canary, canary.decisionSha256),
                         ("canary", "running", w.record.sha256))
        self.assertEqual(canary.journal[-1]["event"], "canary-begun")
        self.refuses("not-shadow", canary.begin_canary, w.record, at=13, **inputs)
        self.refuses("activation-requires-adoption", canary.activate)

    def test_canary_completes_without_promoting_and_halts_on_every_bad_observation(self):
        run = eligible_run(self.world)
        for seen in ("ok", "ok", "ok"):
            step = run.observe(seen, current=IDENTITY, at=13)
            run = step.run
        self.assertEqual((run.state, run.canary), ("canary", "complete"))
        self.assertIsNone(step.registry)
        self.assertEqual(ap.canary_status({"size": 3, "maxFailures": 0}, ["ok"] * 3), "complete")
        # Complete never becomes active, and one more observation overruns.
        self.refuses("activation-requires-adoption", run.activate)
        self.assertEqual(run.observe("ok", current=IDENTITY, at=14).run.state, "stopped")
        for sequence, status in ((["fail"], "halted:failure-budget"),
                                 (["ok", "violation"], "halted:safety-violation"),
                                 (["timeout"], "halted:unknown-observation"),
                                 ([None], "halted:unknown-observation"),
                                 (["okk"], "halted:unknown-observation"),
                                 (["ok"] * 4, "halted:overrun")):
            current = eligible_run(self.world)
            for seen in sequence:
                step = current.observe(seen, current=IDENTITY, at=13)
                current = step.run
            self.assertEqual(current.state, "stopped", sequence)
            self.assertEqual(current.journal[-1]["reason"], "canary-halt")
            self.assertEqual(ap.canary_status({"size": 3, "maxFailures": 0}, sequence), status)
        tolerant = ap.build_policy(CONTROL | {"canary": {"size": 3, "maxFailures": 1}})
        run = eligible_run(self.world, tolerant)
        for seen in ("fail", "ok", "ok"):
            run = run.observe(seen, current=IDENTITY, at=13).run
        self.assertEqual(run.canary, "complete")

    def test_identity_drift_during_canary_stops_and_rolls_back_the_prior_profile(self):
        first = pr.decide(*(lambda r: (r.registration, r.report))(World(at=5)), profile=profile(
            World(at=5).registration), actor=HUMAN, decision="approved", safety=SAFE, evidence=[],
            rollback_target=None, limits=["synthetic-only"], at=5)
        registry = active_registry(first)
        self.assertEqual(registry.active, first.sha256)
        for current in (IDENTITY | {"model": "model-b:2"}, None, {}, "x",
                        IDENTITY | {"extra": "x"}):
            step = eligible_run(self.world).observe("ok", current=current, at=30, registry=registry)
            self.assertEqual(step.run.state, "stopped")
            self.assertEqual(step.run.journal[-1]["reason"], "drift-stop")
            self.assertIsNone(step.registryFailure)
            self.assertIsNone(step.registry.active)  # only profile: nothing left to serve
            self.assertEqual(step.registry.journal[-1]["reason"], "drift-stop")

    def test_incident_and_canary_stops_roll_back_and_a_stopped_run_is_terminal(self):
        first = pr.decide(*(lambda r: (r.registration, r.report))(World(at=5)), profile=profile(
            World(at=5).registration), actor=HUMAN, decision="approved", safety=SAFE, evidence=[],
            rollback_target=None, limits=["synthetic-only"], at=5)
        for trigger, reason in ap.STOP_REASONS.items():
            step = eligible_run(self.world).stop(trigger, at=30, registry=active_registry(first))
            self.assertEqual((step.run.state, step.run.journal[-1]["reason"]), ("stopped", reason))
            self.assertEqual(step.registry.journal[-1]["reason"], reason)
            self.assertIsNone(step.registryFailure)
        stopped = eligible_run(self.world).stop("incident", at=30).run
        self.refuses("not-canary", stopped.observe, "ok", current=IDENTITY, at=31)
        self.refuses("not-shadow", stopped.begin_canary, self.world.record, at=31)
        again = stopped.stop("incident", at=31)
        self.assertEqual(again.run, stopped)  # no second stop event

    def test_rollback_failures_are_visible_and_never_leave_a_running_canary(self):
        empty = pr.ProfileRegistry.empty(SCOPE)
        step = eligible_run(self.world).stop("incident", at=30, registry=empty)
        self.assertEqual(step.run.state, "stopped")
        self.assertEqual(step.registryFailure, "no-active-profile")
        self.assertEqual(step.registry, empty)
        # A registry that moved past the stop tick fails visibly with its own reason.
        late = empty.revoke_evidence(h("x"), at=99, reason="lesson-revoked")
        step = eligible_run(self.world).stop("drift", at=30, registry=late)
        self.assertEqual((step.run.state, step.registryFailure), ("stopped", "no-active-profile"))
        first = pr.decide(*(lambda r: (r.registration, r.report))(World(at=5)), profile=profile(
            World(at=5).registration), actor=HUMAN, decision="approved", safety=SAFE, evidence=[],
            rollback_target=None, limits=["synthetic-only"], at=5)
        active = active_registry(first)
        gone = eligible_run(self.world).stop("incident", at=30, registry=active).registry
        again = eligible_run(self.world).stop("incident", at=31, registry=gone)
        self.assertEqual(again.registryFailure, "no-active-profile")
        regressed = eligible_run(self.world).stop("incident", at=15, registry=active)
        self.assertEqual((regressed.run.state, regressed.registryFailure),
                         ("stopped", "time-regression"))
        self.refuses("invalid-trigger", eligible_run(self.world).stop, "budget", at=30)
        bad = eligible_run(self.world).stop("drift", at=30, registry=object())
        self.assertEqual((bad.run.state, bad.registryFailure, bad.registry),
                         ("stopped", "invalid-registry", None))

    def test_revocation_withdraws_citing_profiles_and_stops_only_a_citing_canary(self):
        lesson = h("lesson-1")
        cited = pr.decide(*(lambda r: (r.registration, r.report))(self.world), profile=profile(
            self.world.registration), actor=HUMAN, decision="approved", safety=SAFE,
            evidence=[lesson], rollback_target=None, limits=["synthetic-only"], at=5)
        registry = active_registry(cited)
        step = eligible_run(self.world).stop("revocation", at=30, registry=registry, evidence=lesson)
        self.assertEqual(step.run.state, "stopped")
        self.assertIsNone(step.registry.active)
        self.assertIn(lesson, step.registry.revoked)
        # A different lesson revokes in the registry but leaves this canary running.
        other = eligible_run(self.world).stop("revocation", at=30, registry=registry,
                                              evidence=h("lesson-9"))
        self.assertEqual(other.run.state, "canary")
        self.assertIn(h("lesson-9"), other.registry.revoked)
        self.assertEqual(other.registry.active, cited.sha256)
        # Revoking twice is a visible failure; the citing canary still stops.
        twice = eligible_run(self.world).stop("revocation", at=31, registry=step.registry,
                                              evidence=lesson)
        self.assertEqual((twice.run.state, twice.registryFailure), ("stopped", "already-revoked"))
        # A later assessment keeps the revoked lesson ineligible.
        got = self.world.run(pol=ap.build_policy(CONTROL), registry=step.registry)
        self.assertEqual(got.reason, "evidence-revoked")
        for bad in (None, "short", 5):
            self.refuses("invalid-evidence", eligible_run(self.world).stop, "revocation", at=30,
                         evidence=bad)
            self.refuses("invalid-evidence", eligible_run(self.world).stop, "revocation", at=30,
                         registry=registry, evidence=bad)

    def test_stops_still_halt_on_a_bad_clock_registry_or_observation(self):
        run = eligible_run(self.world)
        step = run.stop("incident", at=10**30, registry=self.world.registry)
        self.assertEqual((step.run.state, step.registryFailure), ("stopped", "invalid-time"))
        step = run.observe("ok", current=IDENTITY, at=13, registry="x")
        self.assertEqual(step.run.state, "canary")  # a good observation needs no registry
        step = run.observe("ok", current={}, at=13, registry="x")
        self.assertEqual((step.run.state, step.registryFailure), ("stopped", "invalid-registry"))
        step = run.observe("ok", current=IDENTITY, at=1)  # time moved backwards
        self.assertEqual((step.run.state, step.registryFailure), ("stopped", "invalid-time"))

        class Hostile:
            def __eq__(self, other):
                raise ZeroDivisionError

        step = run.observe(Hostile(), current=IDENTITY, at=13)
        self.assertEqual((step.run.state, step.run.observations[-1]), ("stopped", "invalid"))
        for kwargs in ({}, {"bogus": 1}, {"policy": 1}):
            shadow = ap.PolicyRun(policy()).enable(HUMAN, at=1)
            self.refuses("invalid-input", shadow.begin_canary, self.world.record, at=2, **kwargs)

    def test_canary_remembers_the_cited_evidence_and_identity(self):
        run = eligible_run(self.world)
        d = self.world.record.to_dict()
        self.assertEqual(run.cited, frozenset({d["registrationSha256"], d["evaluationSha256"],
                                               d["costReportSha256"], h("lesson-1")}))
        self.assertEqual(dict(run.identity), IDENTITY)

    def test_nothing_in_the_engine_creates_begins_or_commits_a_decision(self):
        w = self.world
        registry = w.registry
        step = eligible_run(w).observe("ok", current=IDENTITY, at=13, registry=registry)
        self.assertIs(step.registry, registry)
        self.assertEqual((registry.active, registry.pending, len(registry.journal)), (None, None, 0))
        tree = ast.parse(Path(ap.__file__).read_text())
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.level == 0}
        self.assertFalse(imported & {"os", "subprocess", "socket", "time", "pathlib", "random"})
        called = {n.func.attr for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertFalse(called & {"begin", "commit", "record", "abort"})
        self.assertNotIn("open", {n.func.id for n in ast.walk(tree)
                                  if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)})


if __name__ == "__main__":
    unittest.main()
