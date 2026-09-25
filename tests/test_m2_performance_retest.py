# SPDX-License-Identifier: AGPL-3.0-only
"""Safety and outcome controls for the exact M2 performance retest runner."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_m2_performance_retest import (
    DECISION_PATH, INPUT_PATH, PROPOSAL_PATH, ROOT, RetestRejected,
    classify_retest, complete_report, docker_phase, real_path_overlap_waves,
    phase_exit_code, run, validate_output_path, verify_decision,
)


class M2PerformanceRetestTests(unittest.TestCase):
    def report(self) -> dict:
        return {
            "status": "completed", "comparison": {"status": "match"},
            "unsafeAdmissionCount": 0,
            "sourceTargetRefMatchesPinnedBaseAtFinalCheck": True,
            "candidateIntegration": {"status": "complete", "finalTree": "a" * 40},
            "serialReference": {"status": "complete", "finalTree": "a" * 40},
        }

    def test_complete_report_rejects_unsafe_or_incomplete_lanes(self) -> None:
        good = self.report()
        self.assertTrue(complete_report(good))
        for path, value in (("unsafeAdmissionCount", 1), ("status", "inconclusive")):
            bad = deepcopy(good)
            bad[path] = value
            with self.subTest(path=path):
                self.assertFalse(complete_report(bad))
        bad = deepcopy(good)
        bad["candidateIntegration"]["status"] = "inconclusive"
        self.assertFalse(complete_report(bad))

    def test_per_batch_goal_and_cleanroom_gates(self) -> None:
        batches = [{"status": "measurement-complete", "sampleCount": 30,
                    "finalTree": "a" * 40, "goalMet": True} for _ in range(2)]
        materialized = {"status": "completed", "gitReports": [self.report(), self.report()]}
        lane = {"status": "passed", "observedTree": "a" * 40, "testCount": 190}
        lanes = {name: [deepcopy(lane), deepcopy(lane)] for name in ("candidate", "serial")}
        self.assertEqual(classify_retest(batches, materialized, lanes, True),
                         ("completed", None))
        negative = deepcopy(batches)
        negative[1]["goalMet"] = False
        self.assertEqual(classify_retest(negative, materialized, lanes, True)[0],
                         "negative-performance")
        self.assertEqual(classify_retest(batches, materialized, lanes, False)[0],
                         "rejected")
        mismatch = deepcopy(batches)
        mismatch[1]["finalTree"] = "b" * 40
        self.assertEqual(classify_retest(mismatch, materialized, lanes, True)[0],
                         "inconclusive")
        failed = deepcopy(lanes)
        failed["serial"][1]["status"] = "inconclusive"
        self.assertEqual(classify_retest(batches, materialized, failed, True)[0],
                         "inconclusive")

    def test_decision_is_byte_bound_to_proposal_and_candidate(self) -> None:
        decision, proposal, _ = verify_decision()
        self.assertEqual(decision["decision"], "accepted-exact-experiment")
        self.assertFalse(decision["executionAuthorization"])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = (DECISION_PATH, INPUT_PATH, PROPOSAL_PATH,
                     "specs/013-m2-real-workload/m2-corpus-selection.json",
                     "agent_braid/git_integration_prototype.py",
                     "agent_braid/git_process.py",
                     "scripts/benchmark_m2_parallel_preparation.py")
            for name in paths:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / name).read_bytes())
            altered = dict(decision, reviewedInputFileSha256="f" * 64)
            (root / DECISION_PATH).write_text(json.dumps(altered))
            with self.assertRaisesRegex(RetestRejected, "exact founder decision"):
                verify_decision(root)
            (root / DECISION_PATH).write_text(json.dumps(decision))
            (root / "agent_braid/git_process.py").write_bytes(b"changed")
            with self.assertRaisesRegex(RetestRejected, "candidate implementation"):
                verify_decision(root)
        self.assertEqual(proposal["candidate"]["codeCommit"],
                         "7d1a07775c2663da93e369ceccf5a8b352c28e78")

    def test_offline_phase_has_fixed_resource_and_mount_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifacts = Path(directory)
            (artifacts / "batch-1.json").write_text(json.dumps({
                "status": "measurement-complete", "sampleCount": 30}))
            response = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
            with patch("scripts.run_m2_performance_retest.subprocess.run",
                       return_value=response) as invoke:
                result = docker_phase(Path("/tmp/read-only-source"), artifacts, "batch", 1)
            self.assertEqual(result["sampleCount"], 30)
            args = invoke.call_args.args[0]
            for required in ("--network=none", "--read-only", "--memory=2g",
                             "--memory-swap=2g", "--cpus=2", "--pids-limit=512",
                             "--cap-drop=ALL", "--security-opt=no-new-privileges"):
                self.assertIn(required, args)
            self.assertIn("--internal-phase", args)
            self.assertNotIn("python -m unittest discover -s tests", args)
            self.assertEqual(invoke.call_args.kwargs["timeout"], 180)

    def test_preflight_failure_never_enters_container_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            output = root / "evidence.json"
            with (patch("scripts.run_m2_performance_retest.validate_proposal",
                        side_effect=RetestRejected("stale base")),
                  patch("scripts.run_m2_performance_retest.docker_phase") as docker):
                with self.assertRaisesRegex(RetestRejected, "stale base"):
                    run(source, output)
            docker.assert_not_called()

    def test_real_corpus_reads_are_covered_by_its_tracked_writes(self) -> None:
        selection = json.loads((ROOT / "specs/013-m2-real-workload/m2-corpus-selection.json")
                               .read_text())
        operations = selection["manifest"]["operations"]
        waves = real_path_overlap_waves(operations, selection["footprints"])
        self.assertEqual(len(waves), 1)
        self.assertEqual(set(waves[0]), {item["instanceId"] for item in operations})
        uncovered = deepcopy(selection["footprints"])
        uncovered[operations[0]["instanceId"]]["reads"].append("other-agent-input.txt")
        with self.assertRaisesRegex(RetestRejected, "uncovered read"):
            real_path_overlap_waves(operations, uncovered)

    def test_completed_measurement_is_a_successful_internal_phase(self) -> None:
        self.assertEqual(phase_exit_code("measurement-complete", "batch"), 0)
        self.assertEqual(phase_exit_code("inconclusive", "batch"), 1)
        self.assertEqual(phase_exit_code("completed", "materialize"), 0)
        self.assertEqual(phase_exit_code("negative-performance", None), 0)

    def test_rejected_output_path_cannot_write_into_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            with self.assertRaisesRegex(RetestRejected, "outside"):
                validate_output_path(source / "rejection.json", source, None)
            redirect = root / "redirect.json"
            redirect.symlink_to(source / "rejection.json")
            with self.assertRaisesRegex(RetestRejected, "artifact directory"):
                validate_output_path(redirect, source, None)
            validate_output_path(root / "result.json", source, None)
            self.assertFalse((source / "rejection.json").exists())


if __name__ == "__main__":
    unittest.main()
