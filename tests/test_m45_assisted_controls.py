# SPDX-License-Identifier: AGPL-3.0-only
"""Actual offline runner integration; no host or provider observation."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import run_m45_assisted_controls as runner


class AssistedControlRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.repo = Path(__file__).resolve().parents[1]

    def test_preparation_uses_pinned_owned_inventory_and_never_fills_unknown_outcomes(self):
        candidate = {"commit": "a" * 40, "sourceManifestSha256": "b" * 64}
        data = runner.prepare_controls(self.repo, candidate, seed="frozen-offline-control-seed",
                                       blinding_key=b"synthetic-fixed-blinding-key-32-byte")
        cohort = data["cohort"]
        self.assertEqual(108, cohort["intendedSlots"])
        self.assertEqual({"not-started"}, set(cohort["outcomes"].values()))
        self.assertEqual((0, 0, 0), (cohort["nativeAttempts"], cohort["modelReviews"], cohort["humanReviews"]))
        self.assertEqual(108, len(data["machinePackets"]))
        self.assertEqual({"human-reviewer-1", "human-reviewer-2"}, set(data["humanReviewerPackets"]))
        self.assertTrue(all(len(bundle["casePackets"]) == 36 for bundle in data["humanReviewerPackets"].values()))
        self.assertEqual(36, len(data["auditSelection"]["initialSlotIds"]))
        self.assertEqual("frozen-offline-control-seed", data["auditSelection"]["policy"]["seed"])
        self.assertFalse(data["auditAssessment"]["automaticComplete"])
        self.assertFalse(data["auditAssessment"]["humanCoverageComplete"])
        for packet in data["machinePackets"]:
            self.assertIsNone(packet["observedOutcome"])
            self.assertEqual([], packet["assessments"])
            self.assertTrue(all(step["observed"] is None for step in packet["requiredSteps"]))
            self.assertIn("m45-", packet["slot"]["fixtureId"])
        self.assertEqual({1, 2, 3}, {packet["slot"]["orderPosition"] for packet in data["machinePackets"]})

    def assert_human_only(self, value):
        private_keys = {"slot", "slotId", "arm", "host", "order", "orderPosition", "fixtureId", "promptId",
                        "machinePackets", "machineBundle", "sourceMap", "assessments", "model", "modelPredictions",
                        "predictions", "inverseMap", "reviewerSequences", "seed", "shuffleSeed", "blindingKey"}
        if isinstance(value, dict):
            self.assertFalse(private_keys.intersection(value), private_keys.intersection(value))
            for child in value.values():
                self.assert_human_only(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_human_only(child)

    def test_independent_reviewer_shuffles_are_reproducible_and_hide_roster_mapping(self):
        candidate = {"commit": "a" * 40, "sourceManifestSha256": "b" * 64}
        kwargs = {"seed": "frozen-offline-control-seed", "blinding_key": b"synthetic-fixed-blinding-key-32-byte"}
        first = runner.prepare_controls(self.repo, candidate, **kwargs)
        repeated = runner.prepare_controls(self.repo, candidate, **kwargs)
        selected = set(first["auditSelection"]["initialSlotIds"])
        roster_order = [packet["caseId"] for packet in first["machinePackets"] if packet["slot"]["slotId"] in selected]
        # Also demonstrate the actual leak in the previous single-bundle API.
        legacy_or_new = first.get("humanReviewerPackets") or {"legacy": {"casePackets": first["humanPackets"]}}
        for bundle in legacy_or_new.values():
            self.assertNotEqual([packet["caseId"] for packet in bundle["casePackets"]], roster_order)
        self.assertEqual(first["humanReviewerPackets"], repeated["humanReviewerPackets"])
        self.assertEqual(first["privateBlinding"], repeated["privateBlinding"])
        self.assertNotEqual(kwargs["seed"], first["privateBlinding"]["shuffleSeed"])
        sequences = []
        for role, bundle in first["humanReviewerPackets"].items():
            self.assert_human_only(bundle)
            sequence = [packet["caseId"] for packet in bundle["casePackets"]]
            self.assertCountEqual(sequence, roster_order)
            self.assertNotEqual(sequence, roster_order)
            self.assertEqual(role, bundle["reviewerRole"])
            self.assertEqual(first["privateBlinding"]["blindingSha256"], bundle["blindingSha256"])
            self.assertEqual(sequence, first["privateBlinding"]["reviewerSequences"][role])
            self.assertEqual(selected, {first["privateBlinding"]["inverseMap"][case] for case in sequence})
            human_bytes = json.dumps(bundle)
            self.assertTrue(all(slot not in human_bytes for slot in selected))
            self.assertNotIn(first["privateBlinding"]["shuffleSeed"], human_bytes)
            sequences.append(sequence)
        self.assertNotEqual(*sequences)
        for bundle in first["humanReviewerPackets"].values():
            self.assertEqual(bundle["bundleSha256"], runner._sha({key: value for key, value in bundle.items()
                                                               if key != "bundleSha256"}))
        # Human bundle objects cannot alias one another or the private packets.
        first_bundle = first["humanReviewerPackets"]["human-reviewer-1"]["casePackets"]
        shared_case = first_bundle[0]["caseId"]
        first_bundle[0]["expectedOutcome"] = "changed by one rater only"
        second_bundle = first["humanReviewerPackets"]["human-reviewer-2"]["casePackets"]
        self.assertNotEqual("changed by one rater only", next(packet["expectedOutcome"] for packet in second_bundle
                                                             if packet["caseId"] == shared_case))
        changed = runner.prepare_controls(self.repo, candidate, **{**kwargs, "seed": "different-private-seed"})
        self.assertNotEqual(first["privateBlinding"]["blindingSha256"], changed["privateBlinding"]["blindingSha256"])

    def test_real_cli_runs_named_controls_and_exclusively_writes_private_report(self):
        output = self.parent / "controls"
        argv = [sys.executable, "-m", "scripts.run_m45_assisted_controls",
                "--output-root", str(output), "--timeout-seconds", "30"]
        result = subprocess.run(argv, cwd=self.repo, capture_output=True, text=True, timeout=120)
        self.assertEqual(0, result.returncode, result.stderr)
        summary = json.loads(result.stdout)
        report = json.loads((output / "machine-private" / "report.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", summary["status"])
        self.assertEqual(len(runner.CASES), len(report["controls"]))
        self.assertEqual({"passed"}, {case["status"] for case in report["controls"]})
        self.assertTrue(all(case["testCount"] == 1 for case in report["controls"]))
        self.assertTrue(all(case["testSourceSha256"] for case in report["controls"]))
        self.assertEqual(0, summary["actualNativeAttempts"])
        self.assertEqual(0, summary["modelReviews"])
        self.assertEqual(0, summary["humanReviews"])
        self.assertEqual(108, summary["preparedSlots"])
        self.assertEqual(36, summary["humanPacketCount"])
        self.assertEqual(2, summary["humanReviewerCount"])
        self.assertEqual(report["reportSha256"], summary["reportSha256"])
        self.assertEqual(0, output.stat().st_mode & 0o077)
        for path in output.rglob("*"):
            self.assertEqual(0, path.stat().st_mode & 0o077, str(path.relative_to(output)))
        self.assertEqual({"machine-private", "human-reviewer-1", "human-reviewer-2"},
                         {path.name for path in output.iterdir()})
        self.assertFalse((output / "prepared-packets.json").exists())
        for role in ("human-reviewer-1", "human-reviewer-2"):
            reviewer_dir = output / role
            self.assertEqual({"packets.json", "INSTRUCTIONS.md"}, {path.name for path in reviewer_dir.iterdir()})
            self.assert_human_only(json.loads((reviewer_dir / "packets.json").read_text()))
            self.assertIn(role, (reviewer_dir / "INSTRUCTIONS.md").read_text())
            self.assertIn("Never share the master", (reviewer_dir / "INSTRUCTIONS.md").read_text())
        private_map = json.loads((output / "machine-private" / "blinding-manifest.json").read_text())
        self.assertEqual(108, len(private_map["inverseMap"]))
        private_packets = json.loads((output / "machine-private" / "machine-packets.json").read_text())
        self.assertEqual(108, len(private_packets["machinePackets"]))
        self.assertNotIn("humanPackets", private_packets)
        before = (output / "machine-private" / "report.json").read_bytes()
        repeated = subprocess.run(argv, cwd=self.repo, capture_output=True, text=True, timeout=10)
        self.assertEqual(2, repeated.returncode)
        self.assertEqual(before, (output / "machine-private" / "report.json").read_bytes())
        self.assertNotIn(str(self.parent), result.stdout)
        self.assertNotIn("stdout", result.stdout)
        self.assertNotIn("stderr", result.stdout)

    def test_checkout_output_and_existing_symlink_are_refused_before_creating_files(self):
        checkout = self.repo / ".m45-assisted-test-output-must-not-exist"
        with self.assertRaises(ValueError):
            runner.run_controls(self.repo, checkout, seed="offline-only", timeout_seconds=30)
        self.assertFalse(checkout.exists())
        alias = self.parent / "alias"
        alias.symlink_to(self.parent, target_is_directory=True)
        with self.assertRaises(FileExistsError):
            runner.run_controls(self.repo, alias, seed="offline-only", timeout_seconds=30)

    def test_unknown_test_is_failure_and_empty_control_set_cannot_pass(self):
        case = {"id": "synthetic-missing-test", "test": "tests.test_tooling_coordination.CoordinationTests.missing_method",
                "oracle": "A missing test must not become passing control evidence", "role": "negative"}
        result = runner.execute_control(self.repo, case, timeout_seconds=10)
        self.assertEqual("failed", result["status"])
        self.assertNotEqual(0, result["returnCode"])
        with patch.object(runner, "CASES", ()):
            with self.assertRaises(ValueError):
                runner.run_controls(self.repo, self.parent / "empty", seed="offline-only", timeout_seconds=30)
        self.assertFalse((self.parent / "empty").exists())


if __name__ == "__main__":
    unittest.main()
