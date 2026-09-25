# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed classification controls for the approved M2 experiment."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from scripts.run_m2_real_workload import (
    COMMAND, FEATURE, IMAGE, LANE_CODE, classify, run, run_lane,
)


class M2RealWorkloadTests(unittest.TestCase):
    def fixture(self) -> tuple[list[dict], dict[str, list[dict]]]:
        report = {
            "status": "completed",
            "comparison": {"status": "match"},
            "unsafeAdmissionCount": 0,
            "sourceTargetRefMatchesPinnedBaseAtFinalCheck": True,
            "candidateIntegration": {"finalTree": "a" * 40},
            "serialReference": {"finalTree": "a" * 40},
        }
        lane = {"status": "passed", "observedTree": "a" * 40,
                "testCount": 200}
        return [deepcopy(report), deepcopy(report)], {
            "candidate": [deepcopy(lane), deepcopy(lane)],
            "serial": [deepcopy(lane), deepcopy(lane)],
        }

    def test_candidate_and_serial_project_validation(self) -> None:
        reports, lanes = self.fixture()
        self.assertEqual(classify(reports, lanes, True), ("completed", None))

    def test_project_validation_fails_closed(self) -> None:
        reports, lanes = self.fixture()
        lanes["serial"][0]["status"] = "inconclusive"
        lanes["serial"][0]["reason"] = "test-failed"
        self.assertEqual(classify(reports, lanes, True)[0], "inconclusive")
        reports, lanes = self.fixture()
        del lanes["serial"]
        self.assertEqual(classify(reports, lanes, True)[1], "missing-test-lane")
        reports, lanes = self.fixture()
        lanes["candidate"][0]["observedTree"] = "b" * 40
        self.assertEqual(classify(reports, lanes, True)[1], "test-tree-mismatch")
        reports, lanes = self.fixture()
        reports[1]["serialReference"]["finalTree"] = "b" * 40
        self.assertEqual(classify(reports, lanes, True)[1], "nonrepeatable-git-tree")
        reports, lanes = self.fixture()
        self.assertEqual(classify(reports, lanes, False)[0], "rejected")
        reports, lanes = self.fixture()
        reports[0]["unsafeAdmissionCount"] = 1
        self.assertEqual(classify(reports, lanes, True)[0], "inconclusive")

    def test_real_workload_comparison_and_claim(self) -> None:
        reports, lanes = self.fixture()
        for item in reports:
            item.update({
                "operationOrder": ["m2-observation-normalizer",
                                   "m2-counterexample-reducer"],
                "candidateWaves": [["m2-observation-normalizer",
                                    "m2-counterexample-reducer"]],
                "metrics": {"candidateTotalWallNanoseconds": 11,
                            "serialTotalWallNanoseconds": 17},
            })
        approved = json.loads((FEATURE / "m2-t003-inputs.json").read_text())
        selection = json.loads((FEATURE / "m2-corpus-selection.json").read_text())
        with (patch("scripts.run_m2_real_workload.verify_inputs",
                    return_value=(approved, selection, {"refs/heads/develop": approved["baseCommit"]})),
              patch("scripts.run_m2_real_workload.run_git_phase_docker",
                    return_value={"gitReports": reports, "privateTreeArchives": {}}),
              patch("scripts.run_m2_real_workload.live_remote_refs",
                    return_value={"refs/heads/develop": approved["baseCommit"]}),
              patch("scripts.run_m2_real_workload.run_lane",
                    side_effect=[deepcopy(item) for pair in lanes.values() for item in pair])):
            report = run(FEATURE.parent.parent)
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["baselines"]["serialWaveCount"], 2)
        self.assertEqual(report["baselines"]["pathOverlapWaveCount"], 1)
        self.assertEqual(report["baselines"]["candidateWaveCount"], 1)
        self.assertEqual(report["baselines"]["candidateGitWallNanoseconds"], 11)
        self.assertEqual(report["baselines"]["serialGitWallNanoseconds"], 17)
        self.assertEqual(report["command"], " ".join(COMMAND))
        self.assertEqual(report["image"], IMAGE)
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["promotionPerformed"])
        self.assertFalse(report["m2Closure"])

    def test_container_command_and_isolation_are_fixed(self) -> None:
        response = subprocess.CompletedProcess(
            [], 0, stdout=b'{"status":"passed","observedTree":"'
            + b"a" * 40 + b'"}', stderr=b"")
        with patch("scripts.run_m2_real_workload.subprocess.run",
                   return_value=response) as invoke:
            result = run_lane(Path("/tmp/source"), Path("/tmp/tree.tar"), "a" * 40)
        args = invoke.call_args.args[0]
        self.assertEqual(result["status"], "passed")
        for required in ("--network=none", "--read-only", "--memory=2g",
                         "--memory-swap=2g", "--cpus=2", "--pids-limit=512",
                         "--cap-drop=ALL", "--security-opt=no-new-privileges"):
            self.assertIn(required, args)
        self.assertEqual(args[-5], IMAGE)
        self.assertEqual(args[-4:-2], ["python", "-c"])
        self.assertEqual(args[-1], "a" * 40)
        self.assertIn('["python", "-m", "unittest", "discover", "-s", "tests"]',
                      LANE_CODE)
        self.assertEqual(invoke.call_args.kwargs["timeout"], 180)

    def test_container_timeout_kills_private_lane(self) -> None:
        response = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
        with patch("scripts.run_m2_real_workload.subprocess.run",
                   side_effect=[subprocess.TimeoutExpired("docker", 180),
                                response, response]) as invoke:
            result = run_lane(Path("/tmp/source"), Path("/tmp/tree.tar"), "a" * 40)
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["reason"], "container-timeout")
        self.assertEqual(invoke.call_args_list[1].args[0][:2], ["docker", "kill"])
        self.assertEqual(invoke.call_args_list[2].args[0][:3], ["docker", "rm", "-f"])


if __name__ == "__main__":
    unittest.main()
