# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T005 R13 guidance-observable double: a synthetic-control positive control only.

Shows that guidance can reach a solver and make arms A and B distinguishable. It is never
native evidence, never a D4 verdict input and never a claim that any guidance helps.
"""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import harness_evaluation as ev
from agent_braid import harness_manifest as manifests
from agent_braid import harness_refinement as ref
from agent_braid import harness_verification as ver
from agent_braid.system_one import canonical
from tests import harness_guidance_double as double
from tests.test_harness_evaluation import Cohort
from tests.test_harness_lab import make_inventory, manifest_for, run as run_lab
from tests.test_harness_manifest import make_manifest

ARM_A_SHA256 = "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
ARM_B_SHA256 = "4bc36ca01e403f9312a74c7658fb77cea88465fc993875a540eff8974fa36516"
CONTROL_SHA256 = "4121338c1175c7c0f6b64741915c324ba90aaa4c6ae6896f480fbd1eac8fbd49"
PREDICTED_DIFFERENT = {"L1-C01-a", "L2-C01-a", "L1-C02-a", "L1-C03-c"}
REWORDED = (b"# Checkpoint and context guidance\n\n"
            b"- After an interruption, resume from the latest checkpoint.\n"
            b"- If inputs drift, stop.\n")


def behaviour(record):
    """The behaviour cells of a result, without its candidate identity."""
    data = record.to_dict()
    return {k: data[k] for k in ("events", "terminal", "executed", "repeated")}


def run_files(case, files):
    return double.run(case, files, candidate_sha256=double.inventory_sha256(files))


def run(case, arm):
    return run_files(case, double.arm_files(arm))


class ArmIdentityTests(unittest.TestCase):
    def test_arm_bytes_hash_to_the_frozen_roster_candidates(self):
        self.assertEqual(double.inventory_sha256(double.arm_files("A")), ARM_A_SHA256)
        self.assertEqual(double.inventory_sha256(double.arm_files("B")), ARM_B_SHA256)
        self.assertEqual(double.ARM_SHA256, {"A": ARM_A_SHA256, "B": ARM_B_SHA256})

    def test_inventory_hash_matches_the_refinement_candidate_hash(self):
        manifest = manifests.parse_manifest(canonical(make_manifest()))
        data = manifest.to_dict()
        data["base"]["files"] = []  # arm A: the empty base inventory
        empty_base = replace(manifest, data=data)
        for arm in "AB":
            files = double.arm_files(arm)
            self.assertEqual(ref._candidate_hash(empty_base, files)[0],
                             double.inventory_sha256(files))

    def test_grammar_mapping_and_cases_are_frozen_before_any_run(self):
        self.assertEqual(double.CONTROL_SHA256, CONTROL_SHA256)
        self.assertEqual(set(double.CASES), {"L1-C01-a", "L2-C01-a", "L1-C02-a",
                                             "L1-C03-a", "L1-C03-b", "L1-C03-c"})
        self.assertNotIn("L3-C02-a", double.CASES)  # unassigned (R3)
        self.assertEqual(sorted(double.GRAMMAR.values()), sorted(double.DEFAULTS))
        # stop-on-drift needs a checkpoint to compare against; every drift case has one.
        self.assertTrue(all(c["checkpoint"] is not None
                            for c in double.CASES.values() if c["drift"]))

    def test_frozen_tables_are_immutable_and_drift_is_refused(self):
        with self.assertRaises(TypeError):
            double.CASES["L1-C01-a"]["checkpoint"] = 0
        altered = {**double.CASES, "L1-C01-a": {**double.CASES["L1-C01-a"], "checkpoint": 0}}
        with patch.object(double, "CASES", altered), \
                self.assertRaises(double.GuidanceDoubleError) as ctx:
            run("L1-C01-a", "A")
        self.assertEqual(ctx.exception.reason, "control-drift")


class GuidanceObservableTests(unittest.TestCase):
    def test_a_and_b_differ_exactly_in_the_predicted_cells(self):
        different = {case for case in double.CASES
                     if behaviour(run(case, "A")) != behaviour(run(case, "B"))}
        self.assertEqual(different, PREDICTED_DIFFERENT)
        strata = {double.CASES[c]["stratum"] for c in different}
        self.assertEqual(strata, {"continuity", "coordination"})

    def test_continuity_resume_does_not_repeat_completed_steps_only_under_b(self):
        a, b = run("L1-C01-a", "A").to_dict(), run("L1-C01-a", "B").to_dict()
        self.assertEqual((a["executed"], a["repeated"]), (["s1", "s2", "s3", "s4"], ["s1", "s2"]))
        self.assertEqual((b["executed"], b["repeated"]), (["s3", "s4"], []))
        self.assertEqual(b["switches"], ["resume-from-checkpoint", "stop-on-drift"])
        self.assertEqual(a["switches"], [])

    def test_coordination_stale_input_starts_no_worker_only_under_b(self):
        a, b = run("L1-C02-a", "A").to_dict(), run("L1-C02-a", "B").to_dict()
        self.assertEqual((a["executed"], a["terminal"]), (["w1", "w2"], "completed"))
        self.assertEqual((b["executed"], b["terminal"]), ([], "interrupted"))
        self.assertIn({"seq": 1, "kind": "message", "text": "drift-reported"}, b["events"])

    def test_each_directive_alone_moves_only_its_own_cells(self):
        lines = {v: k for k, v in double.GRAMMAR.items()}
        expected = {"resume-from-checkpoint": {"L1-C01-a", "L2-C01-a", "L1-C03-c"},
                    "stop-on-drift": {"L2-C01-a", "L1-C02-a"}}
        for switch, cells in expected.items():
            files = {double.GUIDANCE_PATH: (lines[switch] + "\n").encode()}
            moved = {case for case in double.CASES
                     if behaviour(run_files(case, files)) != behaviour(run(case, "A"))}
            self.assertEqual(moved, cells, switch)
            self.assertEqual(run_files("L1-C01-a", files).to_dict()["switches"], [switch])

    def test_cases_without_interruption_or_drift_are_identical(self):
        for case in ("L1-C03-a", "L1-C03-b"):
            self.assertEqual(behaviour(run(case, "A")), behaviour(run(case, "B")))

    def test_runs_are_deterministic(self):
        self.assertEqual(run("L2-C01-a", "B").canonical_bytes,
                         run("L2-C01-a", "B").canonical_bytes)


class NegativeControlTests(unittest.TestCase):
    def test_reworded_directives_change_nothing(self):
        files = {double.GUIDANCE_PATH: REWORDED}
        for case in double.CASES:
            reworded = run_files(case, files)
            self.assertEqual(behaviour(reworded), behaviour(run(case, "A")))

    def test_empty_perturbation_of_a_is_identical_to_a(self):
        files = {double.GUIDANCE_PATH: b""}
        self.assertNotEqual(double.inventory_sha256(files), ARM_A_SHA256)
        for case in double.CASES:
            empty = run_files(case, files)
            self.assertEqual(behaviour(empty), behaviour(run(case, "A")))


class WithoutTheDoubleTests(unittest.TestCase):
    """The existing guidance-blind lab path gives A = B on the same cases."""

    def test_lab_fixture_observations_are_identical_for_a_and_b(self):
        for case in sorted(PREDICTED_DIFFERENT):
            fixture = double.blind_fixture(case)
            observed = {}
            for arm in "AB":
                result = run_lab(fixture, manifest_for(fixture), inputs=double.arm_files(arm),
                                 inventory=make_inventory()).observation.to_dict()
                observed[arm] = {k: result[k] for k in ("events", "terminal", "artifacts")}
            self.assertEqual(observed["A"], observed["B"])
            # The blind fixture replays the default (arm A) behaviour of the double.
            self.assertEqual(observed["A"]["events"], run(case, "A").to_dict()["events"])


class RefusalTests(unittest.TestCase):
    def refused(self, reason, case, files, candidate):
        with self.assertRaises(double.GuidanceDoubleError) as ctx:
            double.run(case, files, candidate_sha256=candidate)
        self.assertEqual(ctx.exception.reason, reason)

    def test_guidance_hash_mismatch_is_refused(self):
        self.refused("guidance-hash-mismatch", "L1-C01-a", double.arm_files("B"), ARM_A_SHA256)
        tampered = {double.GUIDANCE_PATH: double.arm_files("B")[double.GUIDANCE_PATH] + b" "}
        self.refused("guidance-hash-mismatch", "L1-C01-a", tampered, ARM_B_SHA256)

    def test_paths_outside_the_guidance_surface_are_refused(self):
        files = {"guidance/other.md": b"x\n"}
        self.refused("path-not-allowed", "L1-C01-a", files, double.inventory_sha256(files))

    def test_invalid_guidance_and_unknown_cases_are_refused(self):
        files = {double.GUIDANCE_PATH: b"\xff"}
        self.refused("invalid-guidance", "L1-C01-a", files, double.inventory_sha256(files))
        self.refused("unknown-case", "L3-C02-a", {}, ARM_A_SHA256)

    def test_arm_bytes_not_bound_by_the_freeze_record_are_refused(self):
        record = json.loads(double.FREEZE.read_text(encoding="utf-8"))
        record["draftEvidenceSha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "freeze.json")
            path.write_text(json.dumps(record), encoding="utf-8")
            with patch.object(double, "FREEZE", path), \
                    self.assertRaises(double.GuidanceDoubleError) as ctx:
                double.arm_files("B")
        self.assertEqual(ctx.exception.reason, "roster-drift")

    def test_only_a_line_feed_ends_a_directive(self):
        line = next(iter(double.GRAMMAR))
        files = {double.GUIDANCE_PATH: ("x\x0c" + line + "\n").encode()}
        self.assertEqual(run_files("L1-C01-a", files).to_dict()["switches"], [])


class SyntheticControlLabelTests(unittest.TestCase):
    def test_every_record_is_labelled_synthetic_control_and_never_verdict_eligible(self):
        for case in double.CASES:
            for arm in "AB":
                data = run(case, arm).to_dict()
                self.assertEqual(data["label"], "synthetic-control")
                self.assertIs(data["verdictEligible"], False)
                self.assertIs(data["executionAuthorization"], False)
                self.assertEqual(data["controlSha256"], CONTROL_SHA256)

    def test_synthetic_control_label_cannot_register_a_cohort(self):
        self.assertNotIn(double.LABEL, ev.COHORTS)  # the cohort whitelist excludes it
        with self.assertRaises(ev.EvaluationError) as ctx:
            Cohort().register(cohort=double.LABEL)
        self.assertEqual(ctx.exception.reason, "invalid-registration")

    def test_double_records_are_rejected_as_evaluation_rows(self):
        cohort = Cohort(n=1)
        record = run("L1-C01-a", "B")
        rewrapped = ver.VerificationRecord(record.data)  # even repackaged as a T011 record
        for item in (record, rewrapped):
            row = {"arm": "B", "attemptId": "u00-B", "reservationSha256": None,
                   "commitment": item, "verdict": item}
            with self.assertRaises(ev.EvaluationError) as ctx:
                cohort.evaluate([row])
            self.assertEqual(ctx.exception.reason, "invalid-row")


if __name__ == "__main__":
    unittest.main()
