# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049/T014 native workload and grading bridge with deterministic doubles; nothing native runs.

Covers: the units equal the T005 freeze, the per-(case, arm) workload carries exactly the pins the native transport
compares, the visible prompt holds no held-out grader material, and the final-message bridge grades with the frozen
oracle into rows ``harness_evaluation.evaluate`` accepts, without publishing assistant text.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest import mock

from agent_braid import harness_evaluation as ev
from agent_braid import harness_host_claude as hc
from agent_braid import harness_hosts as hh
from agent_braid import harness_hosts_native as hn
from agent_braid import harness_t014_native as tn
from agent_braid import harness_verification as ver
from tests import harness_guidance_double as double
from tests import harness_t005_cohort as t005
from tests import harness_t014_arm_c as arm_c
from tests import test_harness_host_claude as host
from tests.test_harness_hosts import caps, decisions
from tests.test_harness_transport_claude import INIT_VERSION, WINDOW, Fixture, init, line

ROOT = Path(__file__).resolve().parents[1]
BASE = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
NOW = int(BASE.timestamp())
# the reviewed workload (task wording, checkpoint notes, normalizer, budget); the owner's terms must name it
WORKLOAD_SHA256 = "d6040663f19a4fdae3a37f5d1b90f1957eed7cf57f9b6de90dec45fbc2717489"
PINS = dict(environment_sha256="7" * 64, claude_sha256="a" * 64, containment_sha256="b" * 64,
            host_qualification_sha256="c" * 64)


def observation(**over):
    value = dict(host="claude", observed_at=NOW - 30, plan="max", route="subscription", five_hour_percent=20,
                 five_hour_resets_at=NOW + 3 * 3600, weekly_percent=10, weekly_resets_at=NOW + 4 * 86400,
                 extra_usage_enabled=False)
    return hh.QuotaObservation(**(value | over))


def chunks(*texts, version=None, **result_over):
    start = init(**({"claude_code_version": version} if version else {}))
    return [line(start), *(line(host.assistant({"type": "text", "text": t})) for t in texts),
            line(host.result(**result_over))]


class UnitTests(unittest.TestCase):
    def test_the_units_are_the_frozen_t005_units(self):
        units = tn.units()
        self.assertEqual(set(units), {*tn.HOLDOUT, tn.DISCOVERY})
        for case, unit in t005.build_units().items():
            self.assertEqual(units[case].sha256, unit.sha256)
        self.assertEqual(tn.CASES, double.CASES)  # the owned scenarios, read here without importing tests
        self.assertEqual((tn.HOLDOUT, tn.DISCOVERY, tn.RUBRIC_TEXT), (t005.HOLDOUT, t005.DISCOVERY, t005.RUBRIC_TEXT))
        self.assertEqual(sha256((ROOT / tn.UNITS_FREEZE).read_bytes()).hexdigest(), tn.UNITS_FREEZE_SHA256)

    def test_any_drift_from_the_freeze_refuses(self):
        changed = dict(double.CASES) | {"L1-C01-a": dict(double.CASES["L1-C01-a"]) | {"checkpoint": 1}}
        for patch in (mock.patch.object(tn, "UNITS_FREEZE_SHA256", "0" * 64),
                      mock.patch.object(tn, "CASES", changed),
                      mock.patch.object(tn, "RUBRIC_TEXT", b"lenient\n")):
            with self.subTest(patch=patch.attribute), patch, self.assertRaises(tn.T014Error) as cm:
                tn.units()
            self.assertEqual(cm.exception.reason, "units-freeze-drift")

    def test_arm_bytes_are_the_founder_frozen_ones(self):
        self.assertEqual(tn.arm_files("A"), double.arm_files("A"))
        self.assertEqual(tn.arm_files("B"), double.arm_files("B"))
        self.assertEqual(tn.ARM_SHA256, double.ARM_SHA256)
        with self.assertRaises(tn.T014Error):
            tn.arm_files("D")

    def test_arm_files_must_hash_to_their_candidate_and_hold_only_the_guidance(self):
        files = tn.arm_files("B")
        with self.assertRaises(tn.T014Error) as cm:
            tn.check_arm(files, tn.ARM_SHA256["A"])
        self.assertEqual(cm.exception.reason, "arm-hash-mismatch")
        for bad in ({"guidance/main.md": b"x\n"}, {tn.GUIDANCE_PATH: "text"}, {tn.GUIDANCE_PATH: b"\xff"}):
            with self.subTest(bad=bad), self.assertRaises(tn.T014Error):
                tn.check_arm(bad, tn.inventory_sha256({}))


class WorkloadTests(unittest.TestCase):
    def setUp(self):
        self.units = tn.units()

    def inputs(self, case, arm, files=None, **pins):
        files = tn.arm_files(arm) if files is None else files
        return tn.unit_inputs(case, arm, files, candidate_sha256=tn.inventory_sha256(files),
                              registered=self.units, **(PINS | pins))

    def test_the_workload_is_the_reviewed_one(self):
        self.assertEqual(tn.WORKLOAD_SHA256, WORKLOAD_SHA256)
        self.assertEqual(tn.WORKLOAD_SHA256, tn._workload_sha256())

    def test_every_holdout_cell_builds_with_its_arm_and_no_grader_material(self):
        _, _, _, c_files = arm_c.contrastive_round(t005.build_units())
        for case in tn.HOLDOUT:
            for arm, files in (("A", tn.arm_files("A")), ("B", tn.arm_files("B")), ("C", c_files)):
                with self.subTest(case=case, arm=arm):
                    manifest, context = self.inputs(case, arm, files)
                    prompt = context.render()
                    self.assertIn(" ".join(tn.CASES[case]["steps"]), prompt)
                    self.assertNotIn(tn.expected_output(case).decode(), prompt)
                    self.assertNotIn(self.units[case].oracles[0].sha256, prompt)
                    ids = [e["id"] for e in context.to_dict()["entries"]]
                    self.assertEqual(ids, ["task", "guidance", "checkpoint"] if files else ["task", "checkpoint"])
                    if files:
                        self.assertIn(files[tn.GUIDANCE_PATH].decode().split("\n")[2], prompt)
                    data = manifest.data
                    self.assertEqual((data["task"]["id"], data["host"]["requested"]["model"],
                                      data["host"]["requested"]["route"], data["candidate"]["sha256"]),
                                     (case, "haiku", "subscription", tn.inventory_sha256(files)))
                    self.assertFalse(data["executionAuthorization"])

    def test_the_discovery_case_and_unknown_arms_are_refused(self):
        for case, arm in ((tn.DISCOVERY, "A"), ("L1-C01-a", "D"), ("L3-C02-a", "A")):
            with self.subTest(case=case, arm=arm), self.assertRaises(tn.T014Error):
                self.inputs(case, arm, {})

    def test_the_manifest_carries_exactly_the_pins_the_native_transport_compares(self):
        fx = Fixture(self)
        manifest, _ = self.inputs("L1-C01-a", "B", environment_sha256=fx.env_sha, claude_sha256=fx.exe_sha,
                                  containment_sha256=fx.qualification.sha256,
                                  host_qualification_sha256=fx.host_qualification.sha256)
        fx.transport().verify_containment(manifest, fx.host_qualification, 1_799_999_999)
        for wrong in (dict(claude_sha256="0" * 64), dict(containment_sha256="0" * 64),
                      dict(host_qualification_sha256="0" * 64), dict(environment_sha256="0" * 64)):
            with self.subTest(wrong=wrong):
                pins = dict(environment_sha256=fx.env_sha, claude_sha256=fx.exe_sha,
                            containment_sha256=fx.qualification.sha256,
                            host_qualification_sha256=fx.host_qualification.sha256) | wrong
                manifest, _ = self.inputs("L1-C01-a", "B", **pins)
                with self.assertRaises(hc.ClaudeHostError):
                    fx.transport().verify_containment(manifest, fx.host_qualification, 1_799_999_999)

    def test_grader_material_in_the_context_is_refused(self):
        with mock.patch.object(tn, "checkpoint_note", lambda case: tn.expected_output(case)), \
                self.assertRaises(ver.VerificationError) as cm:
            self.inputs("L1-C01-a", "A")
        self.assertEqual(cm.exception.reason, "grader-material-in-context")


class BridgeTests(unittest.TestCase):
    """A launched cell becomes one graded row; only its hashes and verdict leave the bridge."""

    def setUp(self):
        self.units = tn.units()
        self.unit = self.units["L1-C01-a"]

    def grade(self, result, arm="A"):
        return tn.grade(self.unit, arm=arm, candidate_sha256=tn.ARM_SHA256[arm], attempt_id=f"t014-L1-C01-a-{arm}",
                        result=result, inventory=host.make_inventory(), now=NOW, retention_seconds=60)

    def oracle(self, cell):
        return cell.row["verdict"].to_dict()["oracle"]["verdict"]

    def test_the_last_message_is_the_result_and_is_graded_by_the_frozen_oracle(self):
        cell = self.grade(host.run(chunks("thinking it over", "done: s1 s2 s3 s4\nrepeated: none")))
        self.assertEqual((cell.terminal, self.oracle(cell)), ("completed", "pass"))
        self.assertEqual(cell.outcome_sha256, sha256(b"done: s1 s2 s3 s4\nrepeated: none\n").hexdigest())
        self.assertEqual(ev._outcome(self.unit, cell.row["verdict"].to_dict())[0], "correct")

    def test_whitespace_and_line_endings_are_normalized_and_nothing_else(self):
        cell = self.grade(host.run(chunks("\n  done: s1 s2 s3 s4\r\nrepeated: none  \n\n")))
        self.assertEqual(self.oracle(cell), "pass")
        for text in ("done: s1 s2 s3 s4\nrepeated: s1 s2", "```\ndone: s1 s2 s3 s4\nrepeated: none\n```",
                     "stopped: drift", "Done: s1 s2 s3 s4\nrepeated: none"):
            with self.subTest(text=text):
                self.assertEqual(self.oracle(self.grade(host.run(chunks(text)))), "fail")

    def test_a_completed_run_without_a_message_commits_an_empty_result(self):
        cell = self.grade(host.run(chunks()))
        self.assertEqual((cell.terminal, self.oracle(cell)), ("completed", "fail"))

    def test_a_run_that_did_not_complete_commits_nothing(self):
        cell = self.grade(host.run(chunks("done: s1 s2 s3 s4\nrepeated: none", subtype="error_max_turns",
                                          is_error=True)))
        self.assertEqual((cell.terminal, cell.outcome_sha256), ("failed", None))
        self.assertIsNone(cell.row["commitment"].data["outputs"])
        self.assertEqual(ev._outcome(self.unit, cell.row["verdict"].to_dict())[0], "not-completed")

    def test_a_launched_cell_without_a_result_is_ungraded_not_dropped(self):
        cell = self.grade(None)
        self.assertEqual(cell.terminal, "unobserved")
        self.assertEqual(ev._outcome(self.unit, cell.row["verdict"].to_dict()), ("ungraded", "unobserved"))

    def test_a_lossy_stream_is_ungraded(self):
        lossy = host.run([*chunks("done: s1 s2 s3 s4\nrepeated: none"), b"not json\n"])
        cell = self.grade(lossy)
        self.assertEqual(cell.terminal, "unobserved")

    def test_rows_are_published_without_assistant_text(self):
        words = "ASSISTANT-PRIVATE-WORDS"
        cell = self.grade(host.run(chunks(f"{words}\ndone: s1 s2 s3 s4\nrepeated: none")))
        for record in (cell.row["commitment"], cell.row["verdict"]):
            self.assertNotIn(words, json.dumps(record.to_dict()))
            self.assertEqual(tn.record_of(json.loads(json.dumps(record.to_dict()))).sha256, record.sha256)
        self.assertFalse(cell.executionAuthorization)


class NativeCellTests(unittest.TestCase):
    """One cell end to end through ``run_native_unit`` with the fake contained launcher, then the report."""

    def test_a_native_cell_settles_grades_and_enters_the_native_report(self):
        units = tn.units()
        fx = Fixture(self, chunks=chunks("done: s1 s2 s3 s4\nrepeated: none", version=INIT_VERSION))
        fx.qualification = fx.backend_qualification(expiresAt=NOW + 40 * 86400)
        fx.host_qualification = fx.host_record(expiresAt=NOW + 40 * 86400)
        fx.launcher.qualification, fx.launcher.host_qualification = fx.qualification, fx.host_qualification
        files = tn.arm_files("B")
        manifest, context = tn.unit_inputs(
            "L1-C01-a", "B", files, candidate_sha256=tn.ARM_SHA256["B"], registered=units,
            environment_sha256=fx.env_sha, claude_sha256=fx.exe_sha, containment_sha256=fx.qualification.sha256,
            host_qualification_sha256=fx.host_qualification.sha256)
        run = hh.HostQualificationRun(decisions(), caps(), "claude", fx.env_sha, observation(observed_at=NOW - 3600))
        outcome = hn.run_native_unit(
            run=run, backend=fx.launcher, workdir=fx.tmp, containment=fx.host_qualification.canonical_bytes,
            containment_sha256=fx.host_qualification.sha256, manifest=manifest, context=context,
            request=hc.ClaudeRequest(session_id=host.SESSION), compatibility=WINDOW,
            inventory=host.make_inventory(), attempt_id="t014-L1-C01-a-B", before=observation(),
            read_after=lambda: observation(observed_at=NOW + 120, five_hour_percent=21, weekly_percent=10),
            now=lambda: BASE, retention_seconds=3600, settle_now=lambda: NOW + 130, environ={})
        self.assertTrue(outcome.record.completed)
        prompt = fx.launcher.run_calls[-1]["stdin"]
        self.assertIn(b"Do not repeat completed steps.", prompt)
        cell = tn.grade(units["L1-C01-a"], arm="B", candidate_sha256=tn.ARM_SHA256["B"],
                        attempt_id="t014-L1-C01-a-B", result=outcome.result, inventory=host.make_inventory(),
                        now=NOW + 140, retention_seconds=3600)
        _, _, decision, _ = arm_c.contrastive_round(t005.build_units())
        registration = ev.register(
            [units[c] for c in tn.HOLDOUT], lineages={c: tn.LINEAGE for c in tn.HOLDOUT},
            families={c: c.split("-")[1] for c in tn.HOLDOUT}, strata={c: tn.CASES[c]["stratum"] for c in tn.HOLDOUT},
            candidates={"A": tn.ARM_SHA256["A"], "B": tn.ARM_SHA256["B"],
                        "C": decision.to_dict()["chosenCandidateSha256"]},
            refinement=decision, profile_sha256="d" * 64, cohort="native")
        report = ev.evaluate(registration, [cell.row], cost_entries=[
            {"id": "cost-1", "phase": "verification", "attempt": "t014-L1-C01-a-B",
             "measures": {k: {"status": "unknown", "reason": "native-cost-unobserved"} for k in t005.COST_KEYS}}],
            reservations=[]).to_dict()
        outcomes = {(r["unitId"], r["arm"]): r["outcome"] for r in report["rows"]}
        self.assertEqual(outcomes[("L1-C01-a", "B")], "correct")
        self.assertEqual(sum(o == "not-attempted" for o in outcomes.values()), 14)
        self.assertTrue(report["costs"]["economic"]["claimBlocked"])
        self.assertNotIn("repeated: none", json.dumps(report))


if __name__ == "__main__":
    unittest.main()
