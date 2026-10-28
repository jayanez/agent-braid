# SPDX-License-Identifier: AGPL-3.0-only
"""Offline three-arm evaluation controls; deterministic doubles only, no host, model or verdict."""
from dataclasses import FrozenInstanceError
from fractions import Fraction
from hashlib import sha256
from math import comb
import unittest

from agent_braid import harness_evaluation as ev
from agent_braid import harness_verification as ver
from agent_braid.harness_refinement import RefinementDecision
from agent_braid.system_one import canonical, freeze

from tests.test_harness_costs import entry, reservation
from tests.test_harness_observation import NOW, events, observe
from tests.test_harness_refinement import Lab, done, make_policy, proposal

RUBRIC = "7" * 64
RATIONALE = "8" * 64
EXPECTED = {"out/result.txt": b"expected answer: forty-two exactly\n"}
WRONG = {"out/result.txt": b"a different answer entirely\n"}
GUIDANCE = sha256(b"checkpoint guidance").hexdigest()
PROFILE = sha256(b"profile").hexdigest()


def h(name: str) -> str:
    return sha256(name.encode()).hexdigest()


def refinement(decision: str = "candidate"):
    manifest, policy = make_policy()
    general = proposal(manifest, "general", {"guidance/general.md": b"Be brief.\n"})
    base = done(None) if decision == "inconclusive" else done(500_000)
    score = 700_000 if decision == "candidate" else 400_000
    return Lab(manifest, {"general": general, "task": None},
               {"base": base, "general": done(score)}).run(policy)


def edited(record, cls, **changes):
    """A record whose data was edited but whose canonical bytes are recomputed."""
    data = {**record.to_dict(), **changes}
    extra = {"units": record.units} if hasattr(record, "units") else {}
    return cls(freeze(data), canonical(data), **extra)


def make_unit(i: int, human: bool = False) -> ver.Unit:
    return ver.Unit(unit_id=f"u{i:02d}", partition="holdout", source_sha256=h(f"src{i}"),
                    rubric_sha256=RUBRIC, oracles=(ver.FixtureOracle(EXPECTED),),
                    human_required=human)


class Cohort:
    """Deterministic registered cohort; rows are built from real verification records."""

    def __init__(self, n=4, *, lineages=None, families=None, strata=None, decision="candidate",
                 human=()):
        self.units = [make_unit(i, i in human) for i in range(n)]
        self.refinement = refinement(decision)
        data = self.refinement.to_dict()
        base = data["baseSha256"]
        self.candidates = {"A": base, "B": GUIDANCE,
                           "C": data["chosenCandidateSha256"] or base}
        ids = [u.unit_id for u in self.units]
        self.lineages = lineages if lineages is not None else {i: "L-" + i for i in ids}
        self.families = families if families is not None else {i: "F1" for i in ids}
        self.strata = strata if strata is not None else {i: "synthetic" for i in ids}

    def register(self, **over):
        units = over.pop("units", self.units)
        args = dict(lineages=self.lineages, families=self.families, strata=self.strata, candidates=self.candidates,
                    refinement=self.refinement, profile_sha256=PROFILE, cohort="synthetic")
        args.update(over)
        return ev.register(units, **args)

    def row(self, i, arm, code, *, human=(), proxy=(), adjudicator=None, candidate=None):
        unit = self.units[i]
        attempt = f"{unit.unit_id}-{arm}"
        outputs = observation = None
        if code in ("pass", "fail"):
            outputs = EXPECTED if code == "pass" else WRONG
            observation = observe(before={}, after=outputs, attempt_id=attempt)
        elif code != "unobserved":
            observation = observe(events(terminal=code), attempt_id=attempt)
        commitment = ver.commit(unit, candidate_sha256=candidate or self.candidates[arm],
                                observation=observation, outputs=outputs, now=NOW)
        labels = [ver.human_label(unit, commitment, annotator=a, verdict=v, blind=True,
                                  rubric_sha256=RUBRIC) for a, v in human]
        proxies = [ver.proxy_label(unit, commitment, model="judge", score_micros=s) for s in proxy]
        adjudications = [ver.adjudication(unit, commitment, adjudicator=adjudicator, verdict="pass",
                                          rationale_sha256=RATIONALE, labels=labels)
                         ] if adjudicator else []
        verdict = ver.verify_unit(unit, commitment, outputs, human=labels, proxies=proxies,
                                  adjudications=adjudications)
        return {"arm": arm, "attemptId": attempt, "reservationSha256": None,
                "commitment": commitment, "verdict": verdict}

    def rows(self, table):
        return [self.row(i, arm, code) for (i, arm), code in table.items()]

    def evaluate(self, rows, *, registration=None, entries=None, reservations=()):
        if entries is None:
            entries = [entry(f"e-{r['attemptId']}", "proposal", attempt=r["attemptId"]) for r in rows]
        return ev.evaluate(registration or self.register(), rows, cost_entries=entries,
                           reservations=reservations)


def all_pass(cohort, arms="ABC"):
    return {(i, arm): "pass" for i in range(len(cohort.units)) for arm in arms}


class RefusalCase(unittest.TestCase):
    def refused(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ev.EvaluationError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, reason)


class RegistrationTests(RefusalCase):
    def test_registration_binds_three_arms_without_a_library(self):
        cohort = Cohort()
        data = cohort.register().to_dict()
        self.assertEqual(data["format"], ev.REGISTRATION_FORMAT)
        self.assertEqual({a: v["role"] for a, v in data["arms"].items()},
                         {"A": "static-base", "B": "checkpoint-guidance",
                          "C": "contrastive-refinement"})
        self.assertEqual({a: v["candidateSha256"] for a, v in data["arms"].items()},
                         cohort.candidates)
        self.assertEqual(data["refinement"], {"sha256": cohort.refinement.sha256,
                                              "decision": "candidate",
                                              "manifestSha256": cohort.refinement.to_dict()["manifestSha256"],
                                              "armCIsBase": False})
        self.assertEqual(data["protocol"]["library"], "excluded")
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual([u["unitId"] for u in data["units"]], ["u00", "u01", "u02", "u03"])

    def test_protocol_constants_follow_the_frozen_decisions(self):
        protocol = Cohort().register().to_dict()["protocol"]
        self.assertEqual(ev.MIN_PAIRED_UNITS, 19)  # D3: delta 0.15 at one-sided 5%
        self.assertEqual(protocol["correctnessMargin"], "3/20")
        self.assertEqual(protocol["alpha"], "1/20")
        self.assertEqual(protocol["minimumPairedUnits"], 19)
        self.assertEqual(protocol["numericCaps"], "deferred-D2")
        self.assertEqual(protocol["improvementThresholds"], "deferred-D4")

    def test_latin_square_order_rotates_within_each_family(self):
        cohort = Cohort(5, families={"u00": "F1", "u01": "F1", "u02": "F1", "u03": "F1",
                                     "u04": "F2"})
        data = cohort.register().to_dict()
        self.assertEqual(data["units"][4]["family"], "F2")
        order = data["order"]
        self.assertEqual(order, {"u00": ["A", "B", "C"], "u01": ["B", "C", "A"],
                                 "u02": ["C", "A", "B"], "u03": ["A", "B", "C"],
                                 "u04": ["A", "B", "C"]})

    def test_distinct_lineages_in_one_family_still_counterbalance(self):
        cohort = Cohort(3)  # three lineages, one family
        orders = cohort.register().to_dict()["order"].values()
        self.assertEqual({o[0] for o in orders}, {"A", "B", "C"})

    def test_keep_base_refinement_makes_arm_c_the_base(self):
        cohort = Cohort(decision="keep-base")
        data = cohort.register().to_dict()
        self.assertEqual(data["refinement"]["decision"], "keep-base")
        self.assertIs(data["refinement"]["armCIsBase"], True)
        self.assertEqual(data["arms"]["C"]["candidateSha256"], data["arms"]["A"]["candidateSha256"])

    def test_registration_is_deterministic_and_immutable(self):
        cohort = Cohort()
        a, b = cohort.register(), cohort.register(units=list(reversed(cohort.units)))
        self.assertEqual(a.sha256, b.sha256)
        self.assertEqual(a.canonical_bytes, b.canonical_bytes)
        with self.assertRaises(FrozenInstanceError):
            a.units = ()
        with self.assertRaises(TypeError):
            a.data["cohort"] = "native"

    def test_invalid_registrations_refuse_with_fixed_reasons(self):
        cohort = Cohort()
        ids = [u.unit_id for u in cohort.units]
        discovery = ver.Unit(unit_id="u00", partition="discovery", source_sha256=h("s"),
                             rubric_sha256=RUBRIC, oracles=(ver.FixtureOracle(EXPECTED),),
                             human_required=False)
        self.refused("not-holdout", cohort.register, units=[discovery])
        self.refused("invalid-registration", cohort.register, units=[])
        self.refused("invalid-registration", cohort.register, units=["u00"])
        self.refused("invalid-registration", cohort.register, units=cohort.units + cohort.units[:1])
        self.refused("invalid-registration", cohort.register, lineages={ids[0]: "L"})
        self.refused("invalid-registration", cohort.register,
                     strata={**cohort.strata, ids[0]: "../bad"})
        self.refused("invalid-registration", cohort.register,
                     candidates={**cohort.candidates, "D": h("library")})
        self.refused("invalid-registration", cohort.register,
                     candidates={"A": cohort.candidates["A"], "B": GUIDANCE})
        self.refused("invalid-registration", cohort.register, profile_sha256="nothex")
        self.refused("invalid-registration", cohort.register, cohort="pooled")
        self.refused("comparator-not-distinct", cohort.register,
                     candidates={**cohort.candidates, "B": cohort.candidates["A"]})
        self.refused("refinement-mismatch", cohort.register,
                     candidates={**cohort.candidates, "C": cohort.candidates["A"]})
        self.refused("refinement-mismatch", cohort.register,
                     candidates={**cohort.candidates, "A": h("other base")})
        self.refused("invalid-registration", cohort.register,
                     families={**cohort.families, ids[0]: ""})
        self.refused("invalid-refinement", cohort.register, refinement=cohort.refinement.to_dict())

    def test_refinement_must_select_or_keep_the_base_and_be_intact(self):
        cohort = Cohort()
        inconclusive = refinement("inconclusive")
        self.assertEqual(inconclusive.to_dict()["decision"], "inconclusive")
        self.refused("refinement-not-selected", cohort.register, refinement=inconclusive,
                     candidates={**cohort.candidates, "A": inconclusive.to_dict()["baseSha256"],
                                 "C": inconclusive.to_dict()["baseSha256"]})
        authorized = edited(cohort.refinement, RefinementDecision, executionAuthorization=True)
        self.refused("invalid-refinement", cohort.register, refinement=authorized)
        tampered = RefinementDecision(freeze({**cohort.refinement.to_dict(), "decision": "keep-base"}),
                                      cohort.refinement.canonical_bytes)
        self.refused("invalid-refinement", cohort.register, refinement=tampered)
        bare = RefinementDecision(freeze({"format": "braid-harness-refinement-decision/v0.1",
                                          "executionAuthorization": False}),
                                  canonical({"format": "braid-harness-refinement-decision/v0.1",
                                             "executionAuthorization": False}))
        self.refused("invalid-refinement", cohort.register, refinement=bare)

    def test_unit_count_is_bounded(self):
        units = [make_unit(i) for i in range(ev.MAX_UNITS + 1)]
        ids = [u.unit_id for u in units]
        cohort = Cohort()
        self.refused("invalid-registration", cohort.register, units=units,
                     lineages={i: "L" for i in ids}, families={i: "F" for i in ids},
                     strata={i: "s" for i in ids})


class DenominatorTests(RefusalCase):
    def test_failures_refusals_and_ungraded_units_stay_in_the_denominator(self):
        cohort = Cohort(6, human=(5,))
        rows = [cohort.row(0, "A", "pass"), cohort.row(1, "A", "fail"),
                cohort.row(2, "A", "failed"), cohort.row(3, "A", "refused"),
                cohort.row(4, "A", "interrupted"), cohort.row(5, "A", "pass")]  # no human labels
        arm = cohort.evaluate(rows).to_dict()["strata"]["synthetic"]["arms"]["A"]
        self.assertEqual(arm["registered"], 6)
        self.assertEqual(arm["outcomes"], {"correct": 1, "incorrect": 1, "ungraded": 1,
                                           "not-completed": 3, "not-attempted": 0})
        self.assertEqual(arm["terminals"], {"completed": 3, "failed": 1, "interrupted": 1,
                                            "refused": 1, "unobserved": 0, "not-attempted": 0})
        self.assertEqual(arm["correctPerRegistered"], "1/6")
        self.assertEqual(arm["started"], 5)
        self.assertEqual(arm["correctPerStarted"], "1/5")
        self.assertEqual(arm["missingSensitivity"], {"lower": "1/6", "upper": "1/3"})

    def test_completers_alone_are_never_the_denominator(self):
        cohort = Cohort()
        rows = [cohort.row(0, "B", "pass"), cohort.row(1, "B", "failed"),
                cohort.row(2, "B", "unobserved")]
        arm = cohort.evaluate(rows).to_dict()["strata"]["synthetic"]["arms"]["B"]
        self.assertEqual(arm["correctPerRegistered"], "1/4")
        self.assertEqual(arm["outcomes"]["not-attempted"], 1)
        self.assertEqual(arm["outcomes"]["ungraded"], 1)  # unobserved: outcome unknown
        self.assertEqual(arm["terminals"]["unobserved"], 1)
        self.assertEqual(arm["started"], 3)  # unobserved attempts started, as in T012
        self.assertEqual(arm["missingSensitivity"], {"lower": "1/4", "upper": "3/4"})

    def test_an_arm_with_nothing_started_has_an_undefined_started_rate(self):
        cohort = Cohort(2)
        arm = cohort.evaluate([cohort.row(0, "C", "refused")]).to_dict()["strata"]["synthetic"]["arms"]["C"]
        self.assertEqual(arm["started"], 0)
        self.assertEqual(arm["correctPerStarted"], "undefined")
        self.assertEqual(arm["correctPerRegistered"], 0)

    def test_every_registered_cell_is_reported(self):
        cohort = Cohort(2)
        rows = cohort.evaluate([cohort.row(1, "B", "pass")]).to_dict()["rows"]
        self.assertEqual([(r["unitId"], r["arm"]) for r in rows],
                         [("u00", "A"), ("u00", "B"), ("u00", "C"),
                          ("u01", "A"), ("u01", "B"), ("u01", "C")])
        self.assertEqual(rows[0], {"unitId": "u00", "arm": "A", "attemptId": None,
                                   "terminal": "not-attempted", "outcome": "not-attempted",
                                   "reason": None, "commitmentSha256": None, "verdictSha256": None})
        self.assertEqual(rows[4]["outcome"], "correct")


class CorrectnessTests(unittest.TestCase):
    def outcome(self, cohort, row):
        report = cohort.evaluate([row]).to_dict()
        (cell,) = [r for r in report["rows"] if r["attemptId"]]
        return cell["outcome"], cell["reason"]

    def test_proxy_scores_never_become_correctness(self):
        cohort = Cohort(human=(1,))
        self.assertEqual(self.outcome(cohort, cohort.row(0, "A", "fail", proxy=(1_000_000,))),
                         ("incorrect", None))
        self.assertEqual(self.outcome(cohort, cohort.row(1, "A", "pass", proxy=(1_000_000,))),
                         ("ungraded", "human-insufficient-annotators"))

    def test_human_labels_are_required_where_registered(self):
        cohort = Cohort(human=(0,))
        agreed = cohort.row(0, "A", "pass", human=(("ann-1", "pass"), ("ann-2", "pass")))
        self.assertEqual(self.outcome(cohort, agreed), ("correct", None))
        split = cohort.row(0, "A", "pass", human=(("ann-1", "pass"), ("ann-2", "fail")))
        self.assertEqual(self.outcome(cohort, split), ("ungraded", "human-unresolved-disagreement"))
        settled = cohort.row(0, "A", "pass", human=(("ann-1", "pass"), ("ann-2", "fail")),
                             adjudicator="adj-1")
        self.assertEqual(self.outcome(cohort, settled), ("correct", None))

    def test_a_required_human_section_cannot_be_skipped(self):
        cohort = Cohort(human=(0,))
        row = cohort.row(0, "A", "pass")
        human = {**row["verdict"].to_dict()["human"], "status": "not-used"}
        forged = ver.VerificationRecord(freeze({**row["verdict"].to_dict(), "human": human}))
        self.assertEqual(self.outcome(cohort, {**row, "verdict": forged}),
                         ("ungraded", "human-not-used"))

    def test_oracle_and_human_disagreement_is_ungraded(self):
        cohort = Cohort(human=(0,))
        row = cohort.row(0, "A", "fail", human=(("ann-1", "pass"), ("ann-2", "pass")))
        self.assertEqual(self.outcome(cohort, row), ("ungraded", "cross-provenance-disagreement"))

    def test_optional_human_labels_still_count_when_present(self):
        cohort = Cohort()
        row = cohort.row(0, "A", "pass", human=(("ann-1", "fail"), ("ann-2", "fail")))
        self.assertEqual(self.outcome(cohort, row), ("ungraded", "cross-provenance-disagreement"))

    def test_non_completed_attempts_are_not_completed_with_their_terminal(self):
        cohort = Cohort()
        for code in ("failed", "interrupted", "refused"):
            self.assertEqual(self.outcome(cohort, cohort.row(0, "A", code)), ("not-completed", code))
        self.assertEqual(self.outcome(cohort, cohort.row(0, "A", "unobserved")),
                         ("ungraded", "unobserved"))

    def test_unresolved_optional_human_labels_make_the_cell_ungraded(self):
        cohort = Cohort()
        split = cohort.row(0, "A", "pass", human=(("ann-1", "pass"), ("ann-2", "fail")))
        self.assertEqual(self.outcome(cohort, split), ("ungraded", "human-unresolved-disagreement"))
        single = cohort.row(0, "A", "pass", human=(("ann-1", "pass"),))
        self.assertEqual(self.outcome(cohort, single), ("ungraded", "human-insufficient-annotators"))


class ComparisonTests(unittest.TestCase):
    def comparison(self, cohort, table, name="B-vs-A", stratum="synthetic"):
        report = cohort.evaluate(cohort.rows(table)).to_dict()
        return report["strata"][stratum]["comparisons"][name]

    def test_paired_counts_against_the_static_base(self):
        cohort = Cohort(5)
        table = {(0, "A"): "pass", (0, "B"): "pass", (1, "A"): "pass", (1, "B"): "fail",
                 (2, "A"): "fail", (2, "B"): "pass", (3, "A"): "failed", (3, "B"): "refused",
                 (4, "A"): "pass"}
        report = cohort.evaluate(cohort.rows(table)).to_dict()
        comparisons = report["strata"]["synthetic"]["comparisons"]
        result = comparisons["B-vs-A"]
        self.assertEqual({k: result[k] for k in ("pairs", "lineages", "bothCorrect", "comparatorOnly",
                                                 "baseOnly", "neither", "missing", "worseUpperBound")},
                         {"pairs": 5, "lineages": 5, "bothCorrect": 1, "comparatorOnly": 1,
                          "baseOnly": 1, "neither": 1, "missing": 1, "worseUpperBound": 2})
        self.assertEqual(set(comparisons), {"B-vs-A", "C-vs-A"})

    def test_ungraded_cells_are_missing_pairs_not_failures(self):
        cohort = Cohort(2, human=(0,))
        rows = [cohort.row(0, "A", "pass", human=(("ann-1", "pass"), ("ann-2", "pass"))),
                cohort.row(0, "B", "pass"), cohort.row(1, "A", "pass"), cohort.row(1, "B", "pass")]
        result = cohort.evaluate(rows).to_dict()["strata"]["synthetic"]["comparisons"]["B-vs-A"]
        self.assertEqual((result["missing"], result["baseOnly"], result["bothCorrect"]), (1, 0, 1))

    def test_small_cohort_is_descriptive_only(self):
        cohort = Cohort(4)
        result = self.comparison(cohort, all_pass(cohort))["noninferiority"]
        self.assertEqual(result, {"status": "descriptive-only", "verdict": None,
                                  "reasons": ["below-D3-minimum"]})

    def test_repeated_measurements_within_lineage_are_not_independent(self):
        cohort = Cohort(20, lineages={f"u{i:02d}": f"L{i % 4}" for i in range(20)})
        comparison = self.comparison(cohort, all_pass(cohort))
        self.assertEqual(comparison["noninferiority"]["status"], "descriptive-only")
        self.assertEqual(comparison["noninferiority"]["reasons"], ["repeated-within-lineage"])
        self.assertEqual(comparison["lineages"], 4)

    def test_zero_discordance_at_the_d3_minimum_is_noninferior(self):
        cohort = Cohort(19)
        result = self.comparison(cohort, all_pass(cohort))["noninferiority"]
        self.assertEqual(result, {"status": "assessed", "verdict": "noninferior", "reasons": []})
        cohort = Cohort(18)
        self.assertEqual(self.comparison(cohort, all_pass(cohort))["noninferiority"]["reasons"],
                         ["below-D3-minimum"])

    def test_one_worse_pair_at_the_minimum_is_not_demonstrated(self):
        cohort = Cohort(19)
        table = {**all_pass(cohort), (0, "C"): "fail"}
        result = self.comparison(cohort, table, "C-vs-A")["noninferiority"]
        self.assertEqual(result, {"status": "assessed", "verdict": "not-demonstrated", "reasons": []})
        self.assertEqual(self.comparison(cohort, table, "B-vs-A")["noninferiority"]["verdict"],
                         "noninferior")

    def test_missing_pairs_count_as_worse_in_the_assessment(self):
        cohort = Cohort(19)
        table = all_pass(cohort)
        del table[(0, "B")]
        result = self.comparison(cohort, table)
        self.assertEqual((result["missing"], result["worseUpperBound"]), (1, 1))
        self.assertEqual(result["noninferiority"]["verdict"], "not-demonstrated")

    def test_strata_are_reported_separately_and_never_pooled(self):
        strata = {"u00": "synthetic", "u01": "synthetic", "u02": "native-claude", "u03": "native-claude"}
        cohort = Cohort(strata=strata)
        report = cohort.evaluate(cohort.rows(all_pass(cohort))).to_dict()
        self.assertEqual(set(report["strata"]), {"synthetic", "native-claude"})
        for stratum in report["strata"].values():
            self.assertEqual(stratum["units"], 2)
            self.assertEqual(stratum["arms"]["A"]["registered"], 2)


class IntervalTests(unittest.TestCase):
    TAIL = Fraction(1, 40)

    @staticmethod
    def cdf(x, n, p):
        return sum((comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(x + 1)), Fraction(0))

    def test_exact_clopper_pearson_bounds_are_rounded_outward(self):
        micro = Fraction(1, ev.INTERVAL_SCALE)
        for x, n in ((0, 4), (1, 4), (3, 4), (4, 4), (0, 19), (7, 19), (19, 19), (1, 1)):
            interval = ev._interval(x, n)
            lower, upper = interval["lowerMicros"] * micro, interval["upperMicros"] * micro
            self.assertLessEqual(lower, Fraction(x, n))
            self.assertGreaterEqual(upper, Fraction(x, n))
            if x < n:  # the upper bound reaches the tail; one micro below does not
                self.assertLessEqual(self.cdf(x, n, upper), self.TAIL)
                self.assertGreater(self.cdf(x, n, upper - micro), self.TAIL)
            else:
                self.assertEqual(interval["upperMicros"], ev.INTERVAL_SCALE)
            if x > 0:
                self.assertLessEqual(1 - self.cdf(x - 1, n, lower), self.TAIL)
                self.assertGreater(1 - self.cdf(x - 1, n, lower + micro), self.TAIL)
            else:
                self.assertEqual(interval["lowerMicros"], 0)

    def test_known_values(self):
        self.assertEqual(ev._interval(0, 4), {"method": "clopper-pearson-two-sided-0.95",
                                               "lowerMicros": 0, "upperMicros": 602365})
        self.assertEqual(ev._interval(4, 4)["lowerMicros"], 397635)

    def test_arm_reports_the_interval_of_correct_per_registered(self):
        cohort = Cohort()
        arm = cohort.evaluate(cohort.rows(all_pass(cohort, "A"))).to_dict()["strata"]["synthetic"]["arms"]
        self.assertEqual(arm["A"]["interval"], ev._interval(4, 4))
        self.assertEqual(arm["B"]["interval"], ev._interval(0, 4))


class RowBindingTests(RefusalCase):
    def setUp(self):
        self.cohort = Cohort(2)

    def test_rows_must_bind_their_arm_candidate_and_registered_unit(self):
        c = self.cohort
        self.refused("candidate-mismatch", c.evaluate, [c.row(0, "B", "pass", candidate=h("x"))])
        self.refused("unknown-arm", c.evaluate, [{**c.row(0, "A", "pass"), "arm": "D"}])
        self.refused("duplicate-row", c.evaluate, [c.row(0, "A", "pass"), c.row(0, "A", "fail")])
        other = Cohort(3)
        self.refused("unregistered-unit", c.evaluate, [other.row(2, "A", "pass")])

    def test_verdict_must_bind_the_commitment(self):
        c = self.cohort
        a, b = c.row(0, "A", "pass"), c.row(1, "A", "pass")
        self.refused("verdict-binding-mismatch", c.evaluate, [{**a, "verdict": b["verdict"]}])
        other = c.row(0, "A", "fail")  # same unit, candidate and terminal; other commitment
        self.refused("verdict-binding-mismatch", c.evaluate, [{**a, "verdict": other["verdict"]}])
        forged = ver.VerificationRecord(freeze({**a["verdict"].to_dict(), "terminal": "failed"}))
        self.refused("verdict-binding-mismatch", c.evaluate, [{**a, "verdict": forged}])

    def test_verdict_must_match_the_registered_unit(self):
        c = self.cohort
        row = c.row(0, "A", "fail")
        verdict = row["verdict"].to_dict()
        oracle = {**verdict["oracle"], "verdict": "pass"}
        judge = [{**verdict["oracle"]["labels"][0], "verdict": "pass", "verifierSha256": h("judge")}]
        for changes in ({"rubricSha256": h("other rubric")},  # rubric drift
                        {"oracle": {**oracle, "labels": judge}},  # unregistered verifier
                        {"oracle": oracle},  # verdict contradicts its labels
                        {"oracle": {**oracle, "labels": []}}):  # verdict without labels
            forged = ver.VerificationRecord(freeze({**verdict, **changes}))
            self.refused("verdict-unit-mismatch", c.evaluate, [{**row, "verdict": forged}])

    def test_forged_verdict_bindings_are_refused(self):
        c = self.cohort
        row = c.row(0, "A", "pass")
        for changes in ({"unitSha256": h("u")}, {"candidateSha256": h("c")}):
            forged = ver.VerificationRecord(freeze({**row["verdict"].to_dict(), **changes}))
            self.refused("verdict-binding-mismatch", c.evaluate, [{**row, "verdict": forged}])

    def test_one_commitment_fills_one_cell(self):
        c = Cohort(2, decision="keep-base")
        row = c.row(0, "A", "unobserved")
        self.refused("duplicate-row", c.evaluate,
                     [row, {**row, "arm": "C", "attemptId": "u00-C"}])

    def test_row_count_is_bounded(self):
        c = self.cohort
        rows = [c.row(i, arm, "pass") for i in range(2) for arm in "ABC"]
        self.refused("invalid-row", c.evaluate, rows + rows[:1], entries=[])

    def test_malformed_rows_are_refused(self):
        c = self.cohort
        row = c.row(0, "A", "pass")
        self.refused("unknown-arm", c.evaluate, [{**row, "arm": ["A"]}])
        for section in ("x", {"status": "agreed", "verdict": "maybe", "labels": []}):
            forged = ver.VerificationRecord(freeze({**row["verdict"].to_dict(), "oracle": section}))
            self.refused("invalid-row", c.evaluate, [{**row, "verdict": forged}])
        self.refused("invalid-row", c.evaluate, [{**row, "extra": 1}])
        self.refused("invalid-row", c.evaluate, [{**row, "verdict": row["commitment"]}])
        self.refused("invalid-row", c.evaluate, [{**row, "commitment": row["verdict"]}])
        self.refused("invalid-row", c.evaluate, [{**row, "verdict": row["verdict"].to_dict()}])
        self.refused("invalid-row", c.evaluate, "not rows", entries=[])
        self.refused("attempt-mismatch", c.evaluate, [{**row, "attemptId": "other"}])

    def test_registration_must_be_genuine(self):
        c = self.cohort
        registration = c.register()
        self.refused("invalid-registration", c.evaluate, [], registration=registration.to_dict())
        protocol = {**registration.to_dict()["protocol"], "correctnessMargin": "1/2"}
        tampered = ev.Registration(freeze({**registration.to_dict(), "protocol": protocol}),
                                   registration.canonical_bytes, units=registration.units)
        self.refused("invalid-registration", c.evaluate, [], registration=tampered)
        cohort = {**registration.to_dict(), "cohort": "native"}
        relabelled = ev.Registration(freeze(cohort), registration.canonical_bytes,
                                     units=registration.units)
        self.refused("invalid-registration", c.evaluate, [], registration=relabelled)
        self.refused("invalid-registration", c.evaluate, [],
                     registration=edited(registration, ev.Registration, protocol=protocol))
        swapped = ev.Registration(registration.data, registration.canonical_bytes,
                                  units=tuple(reversed(registration.units)))
        self.refused("invalid-registration", c.evaluate, [], registration=swapped)


class CostTests(RefusalCase):
    def test_cost_report_reconciles_every_attempt_with_its_outcome(self):
        cohort = Cohort(2, human=(1,))
        rows = [cohort.row(0, "A", "pass"), cohort.row(1, "A", "refused"), cohort.row(0, "B", "fail"),
                cohort.row(1, "B", "pass")]
        report = cohort.evaluate(rows).to_dict()
        costs = report["costs"]
        self.assertEqual(report["costReportSha256"], sha256(canonical(costs)).hexdigest())
        self.assertEqual(costs["arms"]["A"]["denominators"]["registered"], 2)
        self.assertEqual(costs["arms"]["A"]["denominators"]["outcomes"],
                         {"correct": 1, "incorrect": 1, "ungraded": 0})
        self.assertEqual(costs["arms"]["B"]["denominators"]["outcomes"],
                         {"correct": 0, "incorrect": 1, "ungraded": 1})
        self.assertEqual(costs["arms"]["C"]["denominators"]["notAttempted"], 2)
        self.assertIn("unreserved-attempt", costs["economic"]["blockers"])
        self.assertTrue(costs["economic"]["claimBlocked"])

    def test_fully_reconciled_ledger_has_no_blockers(self):
        cohort = Cohort(1)
        res = {arm: reservation("r" + arm) for arm in "ABC"}
        rows = [{**cohort.row(0, arm, "pass"), "reservationSha256": res[arm].sha256} for arm in "ABC"]
        entries = [e for r in rows for e in (
            entry(f"p-{r['attemptId']}", "proposal", attempt=r["attemptId"]),
            entry(f"c-{r['attemptId']}", "cleanup", attempt=r["attemptId"]))]
        report = cohort.evaluate(rows, entries=entries, reservations=list(res.values())).to_dict()
        self.assertEqual(report["costs"]["economic"]["blockers"], [])

    def test_cost_refusals_surface_with_their_reason(self):
        cohort = Cohort(1)
        rows = [cohort.row(0, "A", "pass")]
        self.refused("unknown-attempt", cohort.evaluate, rows,
                     entries=[entry("e", "proposal", attempt="ghost")])
        self.refused("unknown-reservation", cohort.evaluate,
                     [{**rows[0], "reservationSha256": h("nope")}])


class ReportTests(unittest.TestCase):
    def test_report_is_deterministic_and_carries_no_authority(self):
        cohort = Cohort()
        rows = cohort.rows({(0, "A"): "pass", (1, "B"): "fail", (2, "C"): "refused"})
        first = cohort.evaluate(rows)
        second = cohort.evaluate(list(reversed(rows)))
        self.assertEqual(first.sha256, second.sha256)
        data = first.to_dict()
        self.assertEqual(data["format"], ev.REPORT_FORMAT)
        self.assertEqual(data["registrationSha256"], cohort.register().sha256)
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual(data["pendingEndpoints"], list(ev.PENDING_ENDPOINTS))
        with self.assertRaises(TypeError):
            first.data["strata"] = {}


if __name__ == "__main__":
    unittest.main()
