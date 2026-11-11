# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for SPEC-050/T007 depth/width search; synthetic doubles, no utility claim."""
import ast
import json
from pathlib import Path
import unittest

from agent_braid import harness_search as hs
from agent_braid.system_one import canonical
from tests.test_harness_refinement import done, make_policy, proposal

MODULE = Path(hs.__file__)
OBS = "a" * 64
G, T, M = "guidance/general.md", "guidance/task.md", "guidance/main.md"


def plan_wire(policy, **over):
    wire = {"format": hs.PLAN_FORMAT, "planId": "plan-1", "proberId": "prober-1",
            "policySha256": policy.sha256, "depth": 1, "width": 2, "compose": True,
            "stopOnPlateau": False, "proposalRetries": 0, "transportRetries": 0,
            "concurrency": "serial"}
    wire.update(over)
    return wire


def make_plan(manifest, policy, **over):
    return hs.parse_plan(canonical(plan_wire(policy, **over)), manifest=manifest, policy=policy)


class Flat(dict):
    """Scores every candidate the same, so no arm can show a gain."""

    def __init__(self, value=0):
        super().__init__()
        self.value = value

    def get(self, key, default=None):
        return done(self.value)


class Lab:
    """Scripted proposer/prober. ``proposals`` maps (round, slot, attempt) to a proposal
    (or exception); ``scores`` maps ``"base"`` or a sorted tuple of changed paths to a probe
    output, an exception, or a list of outputs consumed per call."""

    def __init__(self, manifest, proposals, scores):
        self.manifest, self.proposals, self.scores = manifest, proposals, scores
        self.contexts, self.requests, self.calls = [], [], {}

    def propose(self, ctx):
        self.contexts.append(ctx)
        value = self.proposals.get((ctx.round, ctx.slot, ctx.attempt))
        if isinstance(value, Exception):
            raise value
        return value

    def probe(self, request):
        self.requests.append(request)
        key = "base" if request.scope == "base" else tuple(sorted(request.changes))
        count = self.calls[key] = self.calls.get(key, 0) + 1
        value = self.scores.get(key)
        if isinstance(value, list):
            value = value[min(count, len(value)) - 1]
        if isinstance(value, Exception):
            raise value
        return value

    def run(self, plan, policy, **kw):
        return hs.run_search(self.manifest, policy, plan, propose=self.propose,
                             probe=self.probe, **kw)


class SearchBase(unittest.TestCase):
    def setUp(self):
        self.manifest, self.policy = make_policy()

    def lab(self, proposals, scores):
        return Lab(self.manifest, proposals, scores)

    def plan(self, **over):
        return make_plan(self.manifest, self.policy, **over)

    def p(self, scope, path, text):
        return proposal(self.manifest, scope, {path: text.encode()})


class PlanTests(SearchBase):
    def refuses(self, reason, raw=None, **over):
        raw = canonical(plan_wire(self.policy, **over)) if raw is None else raw
        with self.assertRaises(hs.SearchError) as caught:
            hs.parse_plan(raw, manifest=self.manifest, policy=self.policy)
        self.assertEqual(caught.exception.reason, reason)

    def test_plan_is_bound_to_the_verified_policy(self):
        self.assertEqual(self.plan().data["policySha256"], self.policy.sha256)
        self.refuses("policy-drift", policySha256="0" * 64)

    def test_native_concurrency_is_gated_and_other_values_refuse(self):
        self.refuses("native-concurrency-gated", concurrency="native")
        self.refuses("invalid-plan", concurrency="threads")

    def test_bounds_types_and_shape_refuse(self):
        for over in ({"depth": 0}, {"depth": hs.MAX_DEPTH + 1}, {"width": 0},
                     {"width": hs.MAX_WIDTH + 1}, {"depth": True}, {"width": 1.0},
                     {"proposalRetries": 3}, {"transportRetries": -1}, {"compose": "yes"},
                     {"stopOnPlateau": 1}, {"planId": "bad id"}, {"proberId": ""},
                     {"format": "other"}, {"policySha256": "zz"}):
            with self.subTest(over=over):
                self.refuses("invalid-plan", **over)
        wire = plan_wire(self.policy)
        wire["extra"] = 1
        self.refuses("invalid-plan", raw=canonical(wire))
        del wire["extra"], wire["depth"]
        self.refuses("invalid-plan", raw=canonical(wire))
        self.refuses("invalid-plan", raw=b"x" * (hs.MAX_PLAN_BYTES + 1))
        self.refuses("invalid-plan", raw=b"{not json")

    def test_reservation_is_computed_before_any_stage(self):
        plan = self.plan(depth=3, width=2, proposalRetries=1, transportRetries=2)
        self.assertEqual(plan.reservation, {
            "rounds": 3, "slotsPerRound": 2, "proposalAttempts": 6 * 4,
            "probeAttempts": (6 + 3) * 3, "baseProbeAttempts": 3})
        self.assertEqual(self.plan(width=1, compose=True).reservation["probeAttempts"], 1)

    def test_above_contract_ceiling_is_recorded_not_enabled(self):
        for depth, width, above in ((1, 1, False), (2, 1, True), (1, 2, True)):
            lab = self.lab({}, {"base": done(0)})
            wire = lab.run(self.plan(depth=depth, width=width), self.policy).to_dict()
            self.assertEqual(wire["shape"]["aboveContractCeiling"], above)
            self.assertEqual(wire["shape"]["amendmentRequired"], above)
            self.assertEqual(wire["admission"]["state"], "blocked")
            self.assertFalse(wire["executionAuthorization"])


class SequentialDepthTests(SearchBase):
    def test_each_round_refines_the_incumbent_and_records_lineage(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n"),
                        (2, 1, 1): self.p("general", T, "two\n")},
                       {"base": done(500_000), (G,): done(650_000), (G, T): done(800_000)})
        wire = lab.run(self.plan(depth=2, width=1, compose=False), self.policy).to_dict()
        self.assertEqual(wire["decision"], "candidate")
        nodes = {n["id"]: n for n in wire["nodes"]}
        self.assertEqual(nodes["n2"]["parent"], "n1")
        self.assertEqual(nodes["n2"]["lineage"], ["base", "n1"])
        self.assertEqual(wire["chosenCandidateSha256"], nodes["n2"]["candidateSha256"])
        second = lab.contexts[1]
        self.assertEqual((second.round, second.incumbent_score), (2, 650_000))
        self.assertEqual(set(second.incumbent_changes), {G})
        self.assertEqual(set(lab.requests[2].changes), {G, T})  # refinement carries the incumbent
        self.assertEqual([r["advancedTo"] for r in wire["rounds"]], ["n1", "n2"])

    def test_plateau_stops_and_records_unrun_rounds(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n"),
                        (2, 1, 1): self.p("general", T, "two\n")},
                       {"base": done(0), (G,): done(500_000), (G, T): done(500_050)})
        wire = lab.run(self.plan(depth=3, width=1, compose=False, stopOnPlateau=True),
                       self.policy).to_dict()
        self.assertEqual(wire["stopReason"], "plateau")
        self.assertEqual([(r["status"], r["reason"]) for r in wire["rounds"]],
                         [("ran", None), ("ran", None), ("not-run", "plateau")])
        self.assertEqual(wire["chosenCandidateSha256"], wire["nodes"][0]["candidateSha256"])

    def test_without_the_stop_rule_later_rounds_still_run_and_can_win(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n"),
                        (3, 1, 1): self.p("general", T, "three\n")},
                       {"base": done(0), (G,): done(500_000), (G, T): done(900_000)})
        wire = lab.run(self.plan(depth=3, width=1, compose=False), self.policy).to_dict()
        self.assertEqual([r["status"] for r in wire["rounds"]], ["ran"] * 3)
        self.assertEqual(wire["nodes"][-1]["score"], 900_000)

    def test_later_regression_does_not_advance_the_incumbent(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n"),
                        (2, 1, 1): self.p("general", T, "two\n")},
                       {"base": done(300_000), (G,): done(600_000), (G, T): done(100_000)})
        wire = lab.run(self.plan(depth=2, width=1, compose=False), self.policy).to_dict()
        self.assertEqual(wire["decision"], "candidate")
        self.assertEqual(wire["chosenCandidateSha256"], wire["nodes"][0]["candidateSha256"])
        self.assertTrue(wire["nodes"][1]["regressed"])
        self.assertFalse(wire["nodes"][1]["eligible"])
        self.assertIsNone(wire["rounds"][1]["advancedTo"])

    def test_a_step_inside_the_margin_is_recorded_but_cannot_be_chosen(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n"),
                        (2, 1, 1): self.p("general", T, "two\n")},
                       {"base": done(0), (G,): done(500_000), (G, T): done(500_050)})
        wire = lab.run(self.plan(depth=2, width=1, compose=False), self.policy).to_dict()
        self.assertEqual(wire["nodes"][1]["deltaMicros"], 500_050)
        self.assertFalse(wire["nodes"][1]["eligible"])
        self.assertEqual(wire["chosenCandidateSha256"], wire["nodes"][0]["candidateSha256"])
        lab = self.lab({(1, 1, 1): self.p("general", G, "one\n")}, {"base": done(0), (G,): done(50)})
        wire = lab.run(self.plan(depth=1, width=1, compose=False), self.policy).to_dict()
        self.assertEqual((wire["decision"], wire["reasons"]),
                         ("keep-base", ["no-candidate-beats-base"]))


class ParallelWidthTests(SearchBase):
    def props(self):
        return {(1, 1, 1): self.p("general", G, "g\n"), (1, 2, 1): self.p("task", T, "t\n")}

    def test_width_two_composes_when_both_improve(self):
        lab = self.lab(self.props(), {"base": done(0), (G,): done(400_000), (T,): done(500_000),
                                      (G, T): done(900_000)})
        wire = lab.run(self.plan(), self.policy).to_dict()
        composed = [n for n in wire["nodes"] if n["scope"] == "composed"][0]
        self.assertEqual(composed["parents"], ["n1", "n2"])
        self.assertEqual(composed["lineage"], ["base", "n1", "n2"])
        self.assertEqual(wire["chosenCandidateSha256"], composed["candidateSha256"])
        self.assertEqual([r.scope for r in lab.requests], ["base", "general", "task", "composed"])

    def test_compose_off_never_composes(self):
        lab = self.lab(self.props(), {"base": done(0), (G,): done(400_000), (T,): done(500_000)})
        wire = lab.run(self.plan(compose=False), self.policy).to_dict()
        self.assertNotIn("composed", [n["scope"] for n in wire["nodes"]])
        self.assertEqual(wire["reservation"]["probeAttempts"], 2)

    def test_conflicting_changes_are_not_composed(self):
        props = {(1, 1, 1): self.p("general", M, "a\n"), (1, 2, 1): self.p("task", M, "b\n")}
        lab = self.lab(props, {"base": done(0), (M,): done(500_000)})
        wire = lab.run(self.plan(), self.policy).to_dict()
        self.assertIn("composition-conflict", wire["losses"])
        self.assertEqual(wire["decision"], "inconclusive")  # tied top, nothing composed

    def test_tied_top_is_inconclusive_and_a_tie_with_base_keeps_it(self):
        lab = self.lab(self.props(), {"base": done(0), (G,): done(500_000), (T,): done(500_000)})
        wire = lab.run(self.plan(compose=False), self.policy).to_dict()
        self.assertEqual((wire["decision"], wire["reasons"]), ("inconclusive", ["top-tied"]))
        lab = self.lab(self.props(), {"base": done(500_000), (G,): done(500_050),
                                      (T,): done(500_000)})
        wire = lab.run(self.plan(), self.policy).to_dict()
        self.assertEqual((wire["decision"], wire["reasons"]),
                         ("keep-base", ["no-candidate-beats-base"]))

    def test_all_abstentions_keep_the_base(self):
        lab = self.lab({}, {"base": done(0)})
        wire = lab.run(self.plan(), self.policy).to_dict()
        self.assertEqual((wire["decision"], wire["reasons"]), ("keep-base", ["all-abstained"]))
        self.assertEqual(wire["counts"]["abstained"], 2)

    def test_callbacks_cannot_see_or_alter_policy_and_changes_are_read_only(self):
        lab = self.lab(self.props(), {"base": done(0), (G,): done(1), (T,): done(1)})
        lab.run(self.plan(), self.policy)
        for ctx in lab.contexts:
            self.assertFalse(hasattr(ctx, "policy") or hasattr(ctx, "plan"))
        with self.assertRaises(TypeError):
            lab.requests[1].changes[G] = b"x"


class RetryTests(SearchBase):
    def test_invalid_proposals_retry_under_their_own_counter(self):
        bad = proposal(self.manifest, "general", {"../x": b"x"})
        lab = self.lab({(1, 1, 1): bad, (1, 1, 2): self.p("general", G, "g\n")},
                       {"base": done(0), (G,): done(500_000)})
        wire = lab.run(self.plan(width=1, compose=False, proposalRetries=1),
                       self.policy).to_dict()
        proposes = [s for s in wire["stages"] if s["kind"] == "propose"]
        self.assertEqual([(s["attempt"], s["status"]) for s in proposes],
                         [(1, "rejected"), (2, "valid")])
        self.assertEqual(wire["decision"], "candidate")

    def test_retries_exhaust_and_leave_the_slot_unfilled(self):
        bad = proposal(self.manifest, "general", {"../x": b"x"})
        lab = self.lab({(1, 1, a): bad for a in (1, 2, 3)}, {"base": done(0)})
        wire = lab.run(self.plan(width=1, compose=False, proposalRetries=1),
                       self.policy).to_dict()
        self.assertEqual(wire["ledger"]["proposalAttempts"], 2)  # 1 + 1 retry, not 3
        self.assertEqual(wire["counts"]["unfilled"], 1)
        self.assertEqual((wire["decision"], wire["reasons"]), ("keep-base", ["no-valid-candidate"]))

    def test_proposer_exceptions_use_the_transport_counter_not_the_proposal_one(self):
        lab = self.lab({(1, 1, 1): RuntimeError("secret /private/path"),
                        (1, 1, 2): self.p("general", G, "g\n")},
                       {"base": done(0), (G,): done(500_000)})
        wire = lab.run(self.plan(width=1, compose=False, transportRetries=1),
                       self.policy).to_dict()
        first = [s for s in wire["stages"] if s["kind"] == "propose"][0]
        self.assertEqual((first["status"], first["reason"]), ("failed", "proposer-failed"))
        self.assertNotIn("secret", json.dumps(wire))
        self.assertEqual(wire["decision"], "candidate")
        lab = self.lab({(1, 1, 1): RuntimeError("x"), (1, 1, 2): RuntimeError("y")},
                       {"base": done(0)})
        wire = lab.run(self.plan(width=1, compose=False, proposalRetries=2), self.policy).to_dict()
        self.assertEqual(wire["ledger"]["proposalAttempts"], 1)  # transport budget is zero

    def test_probe_transport_failures_retry_but_invalid_outputs_do_not(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")},
                       {"base": done(0), (G,): [None, RuntimeError("boom"), done(500_000)]})
        wire = lab.run(self.plan(width=1, compose=False, transportRetries=2),
                       self.policy).to_dict()
        probes = [s for s in wire["stages"] if s["nodeId"] == "n1"]
        self.assertEqual([s["status"] for s in probes], ["failed", "failed", "scored"])
        self.assertEqual(wire["decision"], "candidate")
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")},
                       {"base": done(0), (G,): {"terminal": "completed", "score": True}})
        wire = lab.run(self.plan(width=1, compose=False, transportRetries=2),
                       self.policy).to_dict()
        self.assertEqual(lab.calls[(G,)], 1)
        self.assertEqual(wire["nodes"][0]["status"], "invalid")
        self.assertEqual(wire["decision"], "inconclusive")

    def test_exhausted_probe_retries_never_win_and_stay_within_the_reservation(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")}, {"base": done(0), (G,): None})
        wire = lab.run(self.plan(width=1, compose=False, transportRetries=1),
                       self.policy).to_dict()
        self.assertEqual(wire["nodes"][0]["status"], "missing")
        self.assertEqual(wire["ledger"]["probeAttempts"], 2)
        self.assertLessEqual(wire["ledger"]["probeAttempts"], wire["reservation"]["probeAttempts"])
        self.assertEqual(wire["decision"], "inconclusive")

    def test_hostile_proposal_mapping_is_a_rejection(self):
        class Hostile(dict):
            def __iter__(self):
                raise TypeError("hostile")
        lab = self.lab({(1, 1, 1): Hostile(a=1)}, {"base": done(0)})
        wire = lab.run(self.plan(width=1, compose=False), self.policy).to_dict()
        self.assertEqual(wire["stages"][1]["reason"], "invalid-proposal")

    def test_duplicate_candidates_across_rounds_are_rejected_not_reprobed(self):
        same = self.p("general", G, "g\n")
        lab = self.lab({(1, 1, 1): same, (2, 1, 1): same}, {"base": done(0), (G,): done(500_000)})
        wire = lab.run(self.plan(depth=2, width=1, compose=False), self.policy).to_dict()
        self.assertEqual(lab.calls[(G,)], 1)
        self.assertEqual(wire["stages"][-1]["reason"], "duplicate-candidate")


class CacheAndSharedBaseTests(SearchBase):
    def props(self):
        return {(1, 1, 1): self.p("general", G, "g\n")}

    def test_scored_outcomes_are_reused_by_identity_without_spend(self):
        cache = hs.SearchCache()
        first = self.lab(self.props(), {"base": done(0), (G,): done(500_000)})
        first.run(self.plan(width=1, compose=False), self.policy, cache=cache)
        self.assertEqual(len(cache), 1)
        second = self.lab(self.props(), {"base": done(0)})  # prober cannot score the candidate
        wire = second.run(self.plan(width=1, compose=False), self.policy, cache=cache).to_dict()
        self.assertNotIn((G,), second.calls)
        self.assertEqual((wire["ledger"]["probeAttempts"], wire["ledger"]["cachedProbes"]), (0, 1))
        self.assertEqual(wire["decision"], "candidate")
        self.assertFalse([s for s in wire["stages"] if s["cached"]][0]["charged"])

    def test_cache_identity_includes_the_prober(self):
        cache = hs.SearchCache()
        self.lab(self.props(), {"base": done(0), (G,): done(500_000)}).run(
            self.plan(width=1, compose=False), self.policy, cache=cache)
        other = self.lab(self.props(), {"base": done(0), (G,): done(1_000)})
        wire = other.run(self.plan(width=1, compose=False, proberId="prober-2"), self.policy,
                         cache=cache).to_dict()
        self.assertEqual(other.calls[(G,)], 1)
        self.assertEqual(wire["ledger"]["cachedProbes"], 0)

    def test_cache_identity_includes_the_manifest_and_policy(self):
        cache = hs.SearchCache()
        self.lab(self.props(), {"base": done(0), (G,): done(500_000)}).run(
            self.plan(width=1, compose=False), self.policy, cache=cache)
        other_manifest, other_policy = make_policy(marginMicros=7)
        other = Lab(other_manifest, {(1, 1, 1): proposal(other_manifest, "general",
                                                         {G: b"g\n"})},
                    {"base": done(0), (G,): done(900_000)})
        wire = other.run(make_plan(other_manifest, other_policy, width=1, compose=False),
                         other_policy, cache=cache).to_dict()
        self.assertEqual(wire["ledger"]["cachedProbes"], 0)

    def test_failures_and_unscored_outcomes_are_never_cached(self):
        cache = hs.SearchCache()
        for output in (None, {"terminal": "interrupted", "score": None, "observationSha256": OBS},
                       {"terminal": "completed", "score": None, "observationSha256": OBS}):
            self.lab(self.props(), {"base": done(0), (G,): output}).run(
                self.plan(width=1, compose=False), self.policy, cache=cache)
        self.assertEqual(len(cache), 0)

    def test_shared_base_is_probed_once_and_bound_to_identity(self):
        lab = self.lab(self.props(), {"base": done(0), (G,): done(500_000)})
        shared = hs.probe_base(self.manifest, prober_id="prober-1", probe=lab.probe)
        wire = lab.run(self.plan(width=1, compose=False), self.policy,
                       shared_base=shared).to_dict()
        self.assertEqual(lab.calls["base"], 1)
        self.assertTrue(wire["counts"]["sharedBase"])
        self.assertEqual(wire["ledger"]["baseProbeAttempts"], 0)
        with self.assertRaises(hs.SearchError) as caught:
            lab.run(self.plan(width=1, compose=False, proberId="prober-2"), self.policy,
                    shared_base=shared)
        self.assertEqual(caught.exception.reason, "base-identity-mismatch")
        other_manifest, other_policy = make_policy(marginMicros=7)
        other = Lab(other_manifest, {}, {"base": done(0)})
        with self.assertRaises(hs.SearchError):
            other.run(make_plan(other_manifest, other_policy), other_policy, shared_base=shared)

    def test_unusable_base_stops_before_any_proposal(self):
        refused = {"terminal": "refused", "score": None, "observationSha256": OBS}
        failed = {"terminal": "failed", "score": None, "observationSha256": OBS}
        for output, decision in ((refused, "refused"), (failed, "inconclusive"),
                                 (None, "inconclusive")):
            lab = self.lab(self.props(), {"base": output})
            wire = lab.run(self.plan(depth=2), self.policy).to_dict()
            self.assertEqual(wire["decision"], decision)
            self.assertEqual(lab.contexts, [])
            self.assertEqual({r["status"] for r in wire["rounds"]}, {"not-run"})

    def test_base_transport_retries_are_counted(self):
        lab = self.lab(self.props(), {"base": [None, done(0)], (G,): done(500_000)})
        wire = lab.run(self.plan(width=1, compose=False, transportRetries=1),
                       self.policy).to_dict()
        self.assertEqual(wire["ledger"]["baseProbeAttempts"], 2)
        self.assertEqual(wire["decision"], "candidate")


class CancellationAndLedgerTests(SearchBase):
    def test_cancellation_stops_before_the_next_stage_and_selects_nothing(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n"),
                        (2, 1, 1): self.p("general", T, "t\n")},
                       {"base": done(0), (G,): done(900_000), (G, T): done(950_000)})
        wire = lab.run(self.plan(depth=3, width=1, compose=False), self.policy,
                       cancelled=lambda: any(r.scope == "general" for r in lab.requests)
                       ).to_dict()
        self.assertEqual((wire["decision"], wire["chosenCandidateSha256"]), ("cancelled", None))
        self.assertEqual(wire["rounds"][1]["status"], "not-run")
        self.assertEqual(lab.calls.get((G, T), 0), 0)

    def test_unreadable_cancel_signal_fails_closed(self):
        def broken():
            raise RuntimeError("boom")
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")}, {"base": done(0)})
        wire = lab.run(self.plan(width=1, compose=False), self.policy, cancelled=broken).to_dict()
        self.assertEqual((wire["decision"], wire["reasons"]),
                         ("cancelled", ["cancel-check-failed"]))
        self.assertEqual(lab.contexts, [])

    def test_stage_accounting_is_complete_and_within_the_reservation(self):
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n"),
                        (1, 2, 1): self.p("task", T, "t\n")},
                       {"base": done(0), (G,): done(400_000), (T,): done(500_000),
                        (G, T): done(900_000)})
        wire = lab.run(self.plan(), self.policy).to_dict()
        ids = [s["id"] for s in wire["stages"]]
        self.assertEqual(ids, [f"s{i}" for i in range(1, len(ids) + 1)])
        ledger = wire["ledger"]
        self.assertEqual((ledger["proposalAttempts"], ledger["probeAttempts"],
                          ledger["baseProbeAttempts"]), (2, 3, 1))
        self.assertEqual(ledger["unusedProbeAttempts"], 0)
        self.assertEqual(hs.reconcile_stages(wire["stages"], wire["reservation"]), ledger)

    def test_ledger_identity_refuses_repeated_ids_and_overspend(self):
        probe = {"id": "s1", "kind": "probe", "scope": "general", "charged": True, "cached": False}
        reservation = {"proposalAttempts": 1, "probeAttempts": 1, "baseProbeAttempts": 1}
        for stages in ([probe, dict(probe)],
                       [probe, {**probe, "id": "s2"}],
                       [{**probe, "kind": "propose"}, {**probe, "id": "s2", "kind": "propose"}]):
            with self.subTest(stages=stages), self.assertRaises(hs.SearchError) as caught:
                hs.reconcile_stages(stages, reservation)
            self.assertEqual(caught.exception.reason, "ledger-identity")

    def test_results_are_deterministic_and_never_authorize_execution(self):
        def run():
            lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")},
                           {"base": done(0), (G,): done(500_000)})
            return lab.run(self.plan(width=1, compose=False), self.policy)
        a, b = run(), run()
        self.assertEqual(a.sha256, b.sha256)
        self.assertIs(a.executionAuthorization, False)
        self.assertIs(a.to_dict()["executionAuthorization"], False)
        self.assertEqual(a.to_dict()["concurrency"], "serial-simulated")
        self.assertEqual(a.to_dict()["delegation"], "none")

    def test_invalid_arguments_raise_search_error(self):
        plan = self.plan()
        for kwargs in ({"propose": None}, {"probe": 1}, {"cache": {}}, {"cancelled": 1}):
            args = {"propose": lambda c: None, "probe": lambda r: None, **kwargs}
            with self.subTest(kwargs=kwargs), self.assertRaises(hs.SearchError):
                hs.run_search(self.manifest, self.policy, plan, **args)
        with self.assertRaises(hs.SearchError):
            hs.run_search(None, self.policy, plan, propose=lambda c: None, probe=lambda r: None)

    def test_internal_errors_propagate_instead_of_becoming_rejections(self):
        from unittest import mock
        lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")}, {"base": done(0)})
        with mock.patch.object(hs, "_candidate_hash", side_effect=AttributeError("bug")):
            with self.assertRaises(AttributeError):
                lab.run(self.plan(width=1, compose=False), self.policy)


class PathSum(dict):
    """Scores a candidate as the sum of a fixed value per changed path; base scores 0."""

    VALUES = {G: 300_000, T: 200_000, M: 100_000}

    def get(self, key, default=None):
        return done(0 if key == "base" else sum(self.VALUES[p] for p in key))


class ComparisonTests(SearchBase):
    def props(self, depth=4):
        """Four distinct proposals per round, one per slot, alternating scope."""
        paths = [G, T, M]
        out = {}
        for rnd in range(1, depth + 1):
            for slot in range(1, 5):
                scope = "general" if slot % 2 else "task"
                out[(rnd, slot, 1)] = self.p(scope, paths[(rnd + slot) % 3], f"r{rnd}s{slot}\n")
        return out

    def compare(self, scores, budget=3, proposals=None):
        lab = self.lab(self.props() if proposals is None else proposals, scores)
        record = hs.compare_arms(self.manifest, self.policy, probe_budget=budget,
                                 prober_id="prober-1", propose=lab.propose, probe=lab.probe)
        return lab, record, record.to_dict()

    @staticmethod
    def arms(wire):
        return {a["arm"]: a for a in wire["arms"]}

    def test_every_arm_stays_within_the_equal_budget_and_base_is_probed_once(self):
        lab, _, wire = self.compare(Flat(), budget=3)
        arms = self.arms(wire)
        self.assertEqual(set(arms), {"keep-base", "one-round", "static", "sequential", "parallel"})
        for arm in arms.values():
            self.assertLessEqual(arm["executedProbes"], 3)
            self.assertFalse(arm["overspent"])
        self.assertEqual(arms["static"]["executedProbes"], 3)
        self.assertEqual(arms["sequential"]["executedProbes"], 3)
        self.assertEqual(sum(1 for r in lab.requests if r.scope == "base"), 1)
        self.assertEqual(len([r for r in lab.requests if r.scope != "base"]),
                         sum(a["executedProbes"] for a in arms.values()))

    def test_one_round_cannot_exceed_a_smaller_equal_budget(self):
        lab, _, wire = self.compare(PathSum(), budget=2)
        arm = self.arms(wire)["one-round"]
        self.assertEqual(arm["executedProbes"], 2)  # the composed probe was never dispatched
        self.assertFalse(arm["overspent"])
        self.assertNotIn("composed", [r.scope for r in lab.requests])

    def test_search_volume_is_not_rewarded_when_quality_is_flat(self):
        _, _, wire = self.compare(Flat(), budget=3)
        self.assertEqual(wire["spentWithoutGain"],
                         ["one-round", "parallel", "sequential", "static"])
        self.assertTrue(all(a["gainMicros"] == 0 for a in wire["arms"]))
        self.assertIn("no-marginal-gain", [m["verdict"] for m in wire["marginal"]])
        self.assertFalse(wire["volumeScored"])
        self.assertFalse(wire["utilityClaim"])
        self.assertEqual(wire["evidence"], "synthetic-offline-doubles")

    def test_depth_pays_when_only_a_later_round_builds_on_an_earlier_one(self):
        props = {(1, 1, 1): self.p("general", G, "a\n"), (2, 1, 1): self.p("general", T, "b\n"),
                 (1, 2, 1): self.p("task", M, "c\n"), (1, 3, 1): self.p("general", T, "d\n")}
        scores = {"base": done(0), (G,): done(200_000), (G, T): done(700_000),
                  (M,): done(0), (T,): done(0)}
        _, _, wire = self.compare(scores, budget=3, proposals=props)
        arms = self.arms(wire)
        self.assertEqual(arms["sequential"]["gainMicros"], 700_000)
        self.assertEqual(arms["static"]["gainMicros"], 200_000)
        self.assertGreater(arms["sequential"]["axes"]["depthCost"],
                           arms["static"]["axes"]["depthCost"])
        self.assertGreater(arms["static"]["axes"]["widthCost"],
                           arms["sequential"]["axes"]["widthCost"])
        self.assertEqual(arms["keep-base"]["executedProbes"], 0)
        verdicts = {(m["from"], m["to"]): m["verdict"] for m in wire["marginal"]}
        self.assertIn("gain", verdicts.values())

    def test_marginal_rows_report_exact_gain_per_extra_probe(self):
        _, _, wire = self.compare(PathSum(), budget=2)
        arms = self.arms(wire)
        self.assertEqual(arms["one-round"]["gainMicros"], 300_000)
        row = next(m for m in wire["marginal"] if m["to"] == "one-round")
        self.assertEqual((row["from"], row["extraProbes"]), ("keep-base", 2))
        self.assertEqual(row["extraGainMicros"], 300_000)
        self.assertEqual(row["gainPerExtraProbeMicros"], 150_000)
        self.assertEqual(row["verdict"], "gain")
        _, _, wire = self.compare(PathSum(), budget=3)
        rates = [m["gainPerExtraProbeMicros"] for m in wire["marginal"]
                 if m["gainPerExtraProbeMicros"] is not None]
        self.assertTrue(all(isinstance(r, (int, str)) for r in rates))

    def test_small_budgets_omit_parallel_and_one_round_can_be_underspent(self):
        _, _, wire = self.compare(Flat(), budget=2)
        self.assertNotIn("parallel", self.arms(wire))
        self.assertEqual(wire["omitted"], [{"arm": "parallel",
                                            "reason": "budget-too-small-for-composition"}])
        _, _, wire = self.compare(Flat(), budget=4)
        arms = self.arms(wire)
        self.assertTrue(arms["one-round"]["underspent"])
        self.assertFalse(arms["static"]["underspent"])

    def test_one_round_arm_is_the_unchanged_refinement(self):
        _, _, wire = self.compare(PathSum(), budget=3)
        arm = self.arms(wire)["one-round"]
        self.assertEqual(arm["shape"], {"depth": 1, "width": 2, "compose": True})
        self.assertEqual(arm["executedProbes"], 3)
        self.assertRegex(arm["resultSha256"], r"[0-9a-f]{64}\Z")

    def test_unusable_base_omits_all_search_arms(self):
        _, _, wire = self.compare({"base": None}, budget=3)
        self.assertEqual([a["arm"] for a in wire["arms"]], ["keep-base"])
        self.assertEqual(wire["omitted"], [{"arm": "all-search-arms", "reason": "base-missing"}])

    def test_each_arm_has_its_own_cache_and_the_record_is_deterministic(self):
        a = self.compare(PathSum(), budget=3)[1]
        b = self.compare(PathSum(), budget=3)[1]
        self.assertEqual(a.sha256, b.sha256)
        self.assertEqual(self.arms(a.to_dict())["static"]["cachedProbes"], 0)
        self.assertIs(a.executionAuthorization, False)
        self.assertEqual(a.to_dict()["admission"]["state"], "blocked")

    def test_invalid_budget_and_arguments_refuse(self):
        lab = self.lab({}, {"base": done(0)})
        for budget in (0, hs.MAX_BUDGET + 1, True, 2.0):
            with self.subTest(budget=budget), self.assertRaises(hs.SearchError):
                hs.compare_arms(self.manifest, self.policy, probe_budget=budget,
                                prober_id="prober-1", propose=lab.propose, probe=lab.probe)
        with self.assertRaises(hs.SearchError):
            hs.compare_arms(self.manifest, self.policy, probe_budget=2, prober_id="bad id",
                            propose=lab.propose, probe=lab.probe)


class ReviewRegressionTests(SearchBase):
    def test_composition_takes_the_best_node_per_scope_not_the_last(self):
        props = {(1, 1, 1): self.p("general", G, "g1\n"), (1, 2, 1): self.p("task", T, "t1\n"),
                 (1, 3, 1): self.p("general", M, "g3\n")}
        lab = self.lab(props, {"base": done(0), (G,): done(900_000), (T,): done(600_000),
                               (M,): done(200_000), (G, T): done(950_000)})
        wire = self.plan_run(lab, width=3).to_dict()
        composed = [n for n in wire["nodes"] if n["scope"] == "composed"][0]
        self.assertEqual(composed["parents"], ["n1", "n2"])

    def plan_run(self, lab, **over):
        return lab.run(self.plan(**over), self.policy)

    def test_margin_boundary_is_inclusive(self):
        for score, expected in ((100, "candidate"), (99, "keep-base")):
            lab = self.lab({(1, 1, 1): self.p("general", G, "g\n")},
                           {"base": done(0), (G,): done(score)})
            wire = self.plan_run(lab, width=1, compose=False).to_dict()
            self.assertEqual(wire["decision"], expected)

    def test_tied_round_does_not_advance_and_next_round_refines_the_base(self):
        props = {(1, 1, 1): self.p("general", G, "g\n"), (1, 2, 1): self.p("task", T, "t\n"),
                 (2, 1, 1): self.p("general", M, "m\n")}
        lab = self.lab(props, {"base": done(0), (G,): done(500_000), (T,): done(500_000),
                               (M,): done(300_000)})
        wire = self.plan_run(lab, depth=2, compose=False).to_dict()
        self.assertIsNone(wire["rounds"][0]["advancedTo"])
        self.assertEqual(lab.contexts[2].incumbent_sha256, self.manifest.data["base"]["sha256"])
        with self.assertRaises(TypeError):
            lab.contexts[2].incumbent_changes["x"] = b""

    def test_cancellation_between_slots_never_dispatches_the_next_probe(self):
        props = {(1, 1, 1): self.p("general", G, "g\n"), (1, 2, 1): self.p("task", T, "t\n")}
        lab = self.lab(props, {"base": done(0), (G,): done(500_000), (T,): done(500_000)})
        wire = lab.run(self.plan(), self.policy,
                       cancelled=lambda: any(r.scope == "general" for r in lab.requests)).to_dict()
        self.assertEqual(wire["decision"], "cancelled")
        self.assertEqual(lab.calls.get((T,), 0), 0)
        self.assertIsNone(wire["rounds"][0]["advancedTo"])

    def test_shared_base_is_a_snapshot_and_its_attempts_are_bounded(self):
        lab = self.lab({}, {"base": done(5)})
        shared = hs.probe_base(self.manifest, prober_id="prober-1", probe=lab.probe)
        self.assertIs(type(shared.raw), dict)
        forged = hs.SharedBase(self.manifest.sha256, "prober-1", done(0), 5000)
        for attempts in (0, 5000):
            forged = hs.SharedBase(self.manifest.sha256, "prober-1", done(0), attempts)
            with self.assertRaises(hs.SearchError) as caught:
                lab.run(self.plan(), self.policy, shared_base=forged)
            self.assertEqual(caught.exception.reason, "invalid-shared-base")
        with self.assertRaises(hs.SearchError):
            hs.probe_base(self.manifest, prober_id="bad id", probe=lab.probe)
        with self.assertRaises(hs.SearchError):
            hs.probe_base(self.manifest, prober_id="prober-1", probe=lab.probe, retries=3)

    def test_cache_identity_includes_the_scope(self):
        key = hs._cache_key
        a = key(self.manifest, self.policy.sha256, "p", "task", "c" * 64)
        self.assertNotEqual(a, key(self.manifest, self.policy.sha256, "p", "composed", "c" * 64))

    def test_parallel_and_one_round_axes_are_reported(self):
        props = ComparisonTests.props(self)
        lab = self.lab(props, PathSum())
        wire = hs.compare_arms(self.manifest, self.policy, probe_budget=3, prober_id="prober-1",
                               propose=lab.propose, probe=lab.probe).to_dict()
        arms = {a["arm"]: a for a in wire["arms"]}
        self.assertEqual(arms["one-round"]["axes"]["widthCost"], 2)
        self.assertEqual(arms["one-round"]["axes"]["depthCost"], 2)  # round + composed probe
        self.assertEqual(arms["one-round"]["axes"]["stageCount"], 3 + 2)
        self.assertEqual(arms["parallel"]["axes"]["widthCost"], 2)
        self.assertEqual(arms["static"]["axes"], {"depthCost": 1, "widthCost": 3, "stageCount": 6})


class ModuleBoundaryTests(unittest.TestCase):
    def test_module_is_offline_and_reuses_refinement_instead_of_copying_it(self):
        tree = ast.parse(MODULE.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or "").split(".")[0])
        banned = {"subprocess", "socket", "threading", "asyncio", "concurrent", "multiprocessing",
                  "urllib", "http", "os", "shutil", "requests", "random", "time", "datetime"}
        self.assertEqual(imported & banned, set())
        defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        for reused in ("_validate_proposal", "_candidate_hash", "_compose", "_outcome",
                       "_decide", "parse_policy", "run_round"):
            self.assertNotIn(reused, defined)
        self.assertNotIn('"executionAuthorization": True', MODULE.read_text())


if __name__ == "__main__":
    unittest.main()
