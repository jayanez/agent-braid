# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T005 synthetic-control cohort controls: plumbing only, no host, model or verdict."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_evaluation as ev
from agent_braid import harness_verification as ver
from tests import harness_guidance_double as double
from tests import harness_t005_cohort as cohort

REGISTRATION = Path(__file__).resolve().parents[1] / (
    "specs/049-harness-evaluation-learning/evidence/registration")
EVIDENCE = Path(__file__).resolve().parents[1] / (
    "specs/049-harness-evaluation-learning/evidence/evaluation/"
    "deterministic-cohort-20261112.json")


def load(name):
    return json.loads((REGISTRATION / name).read_text(encoding="utf-8"))


class UnitFreezeTests(unittest.TestCase):
    def setUp(self):
        self.freeze = load("t005-units-freeze-20261112.json")
        self.units = cohort.build_units()

    def test_built_units_match_the_frozen_hashes(self):
        frozen = {u["unitId"]: u for u in self.freeze["units"]}
        self.assertEqual(set(frozen), set(self.units))
        for case, unit in self.units.items():
            self.assertEqual(unit.sha256, frozen[case]["unitSha256"], case)
            self.assertEqual(unit.partition, frozen[case]["partition"])
            self.assertEqual(unit.oracles[0].sha256, frozen[case]["oracleSha256"])
        self.assertEqual(cohort.rubric_sha256(), self.freeze["rubric"]["sha256"])
        self.assertEqual(self.freeze["rubric"]["text"].encode(), cohort.RUBRIC_TEXT)

    def test_partition_follows_the_roster_and_l3_is_absent(self):
        self.assertEqual({c for c, u in self.units.items() if u.partition == "holdout"},
                         set(cohort.HOLDOUT))
        self.assertEqual(self.units[cohort.DISCOVERY].partition, "discovery")
        self.assertNotIn("L3-C02-a", self.units)
        self.assertEqual(self.freeze["unassigned"], ["L3-C02-a"])
        self.assertTrue(all(not u.human_required and len(u.oracles) == 1
                            for u in self.units.values()))

    def test_oracle_accepts_only_the_complete_non_repeating_result(self):
        unit = self.units["L1-C01-a"]
        good = {cohort.RESULT_PATH: cohort.expected_output("L1-C01-a")}
        repeated = {cohort.RESULT_PATH: b"done: s1 s2 s3 s4\nrepeated: s1 s2\n"}
        partial = {cohort.RESULT_PATH: b"done: s3 s4\nrepeated: none\n"}
        for outputs, accepted in ((good, True), (repeated, False), (partial, False)):
            self.assertIs(unit.oracles[0]._accepts(outputs), accepted)

    def test_arm_c_freeze_matches_a_fresh_keep_base_round(self):
        manifest, policy, decision = cohort.keep_base_round(self.units)
        armc = self.freeze["armC"]
        data = decision.to_dict()
        self.assertEqual((data["decision"], data["reasons"], data["chosenCandidateSha256"]),
                         ("keep-base", ["all-abstained"], None))
        self.assertEqual(data["baseSha256"], double.ARM_SHA256["A"])
        self.assertEqual(armc["candidateSha256"], double.ARM_SHA256["A"])
        self.assertEqual(armc["manifestSha256"], manifest.sha256)
        self.assertEqual(armc["policySha256"], policy.sha256)
        self.assertEqual(armc["refinementDecisionSha256"], decision.sha256)
        self.assertEqual(data["counts"]["probes"], 1)  # the base only; both scopes abstained

    def test_discovery_base_probe_is_graded_by_the_discovery_oracle_not_the_holdout(self):
        _, _, decision = cohort.keep_base_round(self.units)
        base = next(a for a in decision.to_dict()["attempts"] if a["scope"] == "base")
        self.assertEqual(base["score"], 0)  # arm A repeats a completed step on L2-C01-a


class OwnerRecordTests(unittest.TestCase):
    def test_authorization_is_scoped_to_one_labelled_synthetic_run(self):
        record = load("t005-owner-decisions-20261112.json")
        run = record["runAuthorization"]
        self.assertEqual((run["runs"], run["label"], run["verdictEligible"],
                          run["additionalCashEur"]), (1, "synthetic-control", False, 0))
        self.assertIs(record["executionAuthorization"], False)
        self.assertIs(record["nativeAdmission"], False)
        self.assertEqual({d["item"] for d in record["decisions"]},
                         {"R11 unit construction", "R3 L3-C02-a", "R8 arm C", "Run authorization"})
        self.assertIn("paraphrase", record["decisionChannel"])


class CohortRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = cohort.results()

    def cells(self):
        return {(r["unitId"], r["arm"]): (r["outcome"], r["terminal"])
                for r in self.result["rows"]}

    def test_every_registered_cell_is_reported_once(self):
        self.assertEqual(len(self.result["rows"]), len(cohort.HOLDOUT) * 3)
        self.assertEqual(len(self.cells()), 15)
        self.assertEqual(len(self.result["attempts"]), 15)

    def test_outcomes_match_the_frozen_mapping(self):
        cells = self.cells()
        expected = {
            ("L1-C01-a", "A"): "incorrect", ("L1-C01-a", "B"): "correct",
            ("L1-C02-a", "A"): "correct", ("L1-C02-a", "B"): "not-completed",
            ("L1-C03-a", "A"): "correct", ("L1-C03-a", "B"): "correct",
            ("L1-C03-b", "A"): "correct", ("L1-C03-b", "B"): "correct",
            ("L1-C03-c", "A"): "incorrect", ("L1-C03-c", "B"): "correct"}
        for key, outcome in expected.items():
            self.assertEqual(cells[key][0], outcome, key)
        self.assertEqual(cells[("L1-C02-a", "B")][1], "interrupted")

    def test_arm_c_is_arm_a_in_every_cell(self):
        cells = self.cells()
        for case in cohort.HOLDOUT:
            self.assertEqual(cells[(case, "C")], cells[(case, "A")], case)
        by_case = {}
        for a in self.result["attempts"]:
            by_case.setdefault(a["caseId"], {})[a["arm"]] = a["doubleRecordSha256"]
        self.assertTrue(all(v["A"] == v["C"] for v in by_case.values()))
        self.assertTrue(self.result["refinement"]["armCIsBase"])

    def test_strata_are_descriptive_only_and_never_pooled(self):
        strata = self.result["strata"]
        self.assertEqual({k: (v["units"], v["lineages"]) for k, v in strata.items()},
                         {"continuity": (1, 1), "coordination": (4, 1)})
        for stratum in strata.values():
            for comparison in stratum["comparisons"].values():
                status = comparison["noninferiority"]
                self.assertEqual((status["status"], status["verdict"]), ("descriptive-only", None))
                self.assertIn("below-D3-minimum", status["reasons"])
        self.assertIn("repeated-within-lineage",
                      strata["coordination"]["comparisons"]["B-vs-A"]["noninferiority"]["reasons"])

    def test_the_interrupted_arm_b_cell_stays_in_the_denominator(self):
        b = self.result["strata"]["coordination"]["arms"]["B"]
        self.assertEqual((b["registered"], b["started"]), (4, 4))
        self.assertEqual(b["outcomes"]["not-completed"], 1)
        self.assertEqual(b["outcomes"]["correct"], 3)

    def test_nothing_claims_a_verdict_utility_or_authority(self):
        self.assertEqual(self.result["label"], "synthetic-control")
        self.assertIs(self.result["verdictEligible"], False)
        self.assertIs(self.result["executionAuthorization"], False)
        self.assertTrue(self.result["costs"]["claimBlocked"])
        self.assertIn("unknown-cash", self.result["costs"]["blockers"])
        self.assertEqual(self.result["pendingEndpoints"], list(ev.PENDING_ENDPOINTS))
        self.assertNotIn("verdict", json.dumps(self.result["strata"]).replace('"verdict": null', ""))

    def test_a_run_is_deterministic(self):
        self.assertEqual(json.dumps(cohort.results(), sort_keys=True),
                         json.dumps(self.result, sort_keys=True))

    def test_double_inputs_are_unchanged(self):
        self.assertEqual(sha256(Path(double.__file__).read_bytes()).hexdigest(),
                         "12090b191da647019f6e73b6e538797767af383c4f94bf86be4bf20fa0dd21fa")

    def test_recorded_run_evidence_equals_a_fresh_run(self):
        recorded = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(json.dumps(recorded["results"], sort_keys=True),
                         json.dumps(self.result, sort_keys=True))
        self.assertEqual(recorded["label"], "synthetic-control")
        self.assertIs(recorded["executionAuthorization"], False)


class RegistrationGuardTests(unittest.TestCase):
    def test_a_discovery_unit_cannot_be_registered_as_holdout(self):
        units = cohort.build_units()
        _, _, decision = cohort.keep_base_round(units)
        with self.assertRaises(ev.EvaluationError) as ctx:
            ev.register([units[cohort.DISCOVERY]], lineages={cohort.DISCOVERY: "L2"},
                        families={cohort.DISCOVERY: "C01"}, strata={cohort.DISCOVERY: "continuity"},
                        candidates={"A": double.ARM_SHA256["A"], "B": double.ARM_SHA256["B"],
                                    "C": double.ARM_SHA256["A"]},
                        refinement=decision, profile_sha256=cohort.PROFILE_SHA256,
                        cohort="synthetic")
        self.assertEqual(ctx.exception.reason, "not-holdout")

    def test_registration_binds_the_frozen_arm_identities(self):
        units = cohort.build_units()
        _, _, decision = cohort.keep_base_round(units)
        registration = cohort.register(units, decision)
        arms = registration.data["arms"]
        self.assertEqual(arms["A"]["candidateSha256"], double.ARM_SHA256["A"])
        self.assertEqual(arms["B"]["candidateSha256"], double.ARM_SHA256["B"])
        self.assertEqual(arms["C"]["candidateSha256"], arms["A"]["candidateSha256"])
        self.assertEqual(registration.data["cohort"], "synthetic")
        self.assertIsInstance(registration.units[0], ver.Unit)


if __name__ == "__main__":
    unittest.main()
