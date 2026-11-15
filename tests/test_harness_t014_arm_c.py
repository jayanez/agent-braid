# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T014 offline arm-C controls: a real contrastive round, synthetic-control only."""
import socket
import subprocess
import unittest
from unittest import mock

from agent_braid import harness_evaluation as ev
from agent_braid import harness_refinement as ref
from tests import harness_guidance_double as double
from tests import harness_t005_cohort as t005
from tests import harness_t014_arm_c as arm_c

B_LINES = set(double.arm_files("B")[double.GUIDANCE_PATH].decode().split("\n"))


class ProposerTests(unittest.TestCase):
    def setUp(self):
        self.manifest, _ = t005.build_manifest()

    def test_signals_come_from_the_discovery_base_attempt_only(self):
        with mock.patch.object(arm_c.double, "run", wraps=double.run) as run:
            signals = arm_c.discovery_signals()
        self.assertEqual(signals, ("continued-past-drift", "repeated-completed-steps"))
        self.assertEqual({c.args[0] for c in run.call_args_list}, {t005.DISCOVERY})

    def test_each_scope_proposes_one_bounded_catalog_edit(self):
        propose = arm_c.make_proposer(self.manifest, arm_c.discovery_signals())
        for scope in ref.SCOPES:
            proposal = propose(scope)
            self.assertEqual(proposal["scope"], scope)
            self.assertEqual(proposal["parentManifestSha256"], self.manifest.sha256)
            self.assertEqual(set(proposal["changes"]), {double.GUIDANCE_PATH})
            content = proposal["changes"][double.GUIDANCE_PATH]
            self.assertLessEqual(set(content.decode().split("\n")), B_LINES)
            self.assertLess(len(content), len(double.arm_files("B")[double.GUIDANCE_PATH]))
        general = propose("general")["changes"][double.GUIDANCE_PATH].decode()
        task = propose("task")["changes"][double.GUIDANCE_PATH].decode()
        self.assertIn(arm_c.CATALOG["repeated-completed-steps"][1], general)
        self.assertIn(arm_c.CATALOG["continued-past-drift"][1], task)

    def test_no_signal_means_abstention(self):
        propose = arm_c.make_proposer(self.manifest, ())
        self.assertIsNone(propose("general"))
        self.assertIsNone(propose("task"))

    def test_unknown_signal_is_refused(self):
        with self.assertRaises(ValueError):
            arm_c.make_proposer(self.manifest, ("made-up",))


class RoundTests(unittest.TestCase):
    def setUp(self):
        self.units = t005.build_units()
        self.manifest, self.policy, self.decision, self.files = arm_c.contrastive_round(self.units)
        self.data = self.decision.to_dict()

    def test_round_selects_a_candidate_distinct_from_a_and_b(self):
        self.assertEqual(self.data["decision"], "candidate")
        chosen = self.data["chosenCandidateSha256"]
        self.assertNotIn(chosen, set(double.ARM_SHA256.values()))
        self.assertEqual(double.inventory_sha256(self.files), chosen)

    def test_probes_stay_within_the_frozen_budget(self):
        counts = self.data["counts"]
        self.assertLessEqual(counts["probes"], counts["maxProbes"])
        self.assertEqual(counts["probes"], 3)  # base, general, task; task fails so no compose
        status = {a["scope"]: a["status"] for a in self.data["attempts"]}
        self.assertEqual(status, {"base": "scored", "general": "scored", "task": "interrupted"})

    def test_round_is_deterministic(self):
        again = arm_c.contrastive_round(t005.build_units())[2]
        self.assertEqual(again.sha256, self.decision.sha256)

    def test_prober_refuses_every_holdout_case(self):
        for case in t005.HOLDOUT:
            with self.assertRaises(ValueError):
                arm_c.probe_case(case, self.units, self.manifest)

    def test_ungraded_probe_is_not_swallowed_as_a_score(self):
        probe = arm_c.probe_case(t005.DISCOVERY, self.units, self.manifest)
        ungraded = mock.Mock(to_dict=lambda: {"oracle": {"verdict": "bogus"}})
        with mock.patch.object(arm_c.ver, "verify_unit", return_value=ungraded):
            with self.assertRaises(ValueError):
                probe(ref.ProbeRequest("base", double.ARM_SHA256["A"], {}))

    def test_composed_winner_is_refused_not_guessed(self):
        with mock.patch.object(arm_c.ref, "run_round") as run_round:
            run_round.return_value.to_dict.return_value = {"chosenCandidateSha256": "f" * 64}
            with self.assertRaises(ValueError):
                arm_c.contrastive_round(self.units)


class CohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process")):
            cls.cohort = arm_c.run_cohort()
        cls.report = cls.cohort["report"].to_dict()
        cls.outcome = {(r["unitId"], r["arm"]): r["outcome"] for r in cls.report["rows"]}

    def test_registration_binds_a_non_base_arm_c(self):
        reg = self.cohort["registration"].to_dict()
        self.assertFalse(reg["refinement"]["armCIsBase"])
        self.assertEqual(reg["arms"]["C"]["candidateSha256"],
                         self.cohort["decision"].to_dict()["chosenCandidateSha256"])

    def test_arm_c_differs_from_a_and_from_b_on_fixtures(self):
        holdout = t005.HOLDOUT
        self.assertTrue(any(self.outcome[c, "C"] != self.outcome[c, "A"] for c in holdout))
        self.assertTrue(any(self.outcome[c, "C"] != self.outcome[c, "B"] for c in holdout))

    def test_costs_stay_unknown_and_claims_blocked(self):
        self.assertTrue(self.report["costs"]["economic"]["claimBlocked"])

    def test_result_is_labelled_synthetic_control(self):
        with mock.patch.object(socket, "socket", side_effect=AssertionError("network")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("process")):
            result = arm_c.results()
        self.assertEqual(result["label"], "synthetic-control")
        self.assertFalse(result["verdictEligible"] or result["executionAuthorization"])
        self.assertEqual(result["registrationSha256"], self.cohort["registration"].sha256)
        self.assertEqual(set(ev.ARMS), {r["arm"] for r in result["rows"]})


if __name__ == "__main__":
    unittest.main()
