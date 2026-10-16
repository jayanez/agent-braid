# SPDX-License-Identifier: AGPL-3.0-only
"""The skill capture must never promote missing or synthetic host evidence."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.tooling_fixtures import load_inventory

from scripts import run_m45_skills_acceptance as capture


class SkillCaptureTests(unittest.TestCase):
    def records(self):
        return [{"testId": name, "outcome": "passed"}
                for name in capture.expected_tests()]

    def test_complete_controls_still_leave_every_native_procedure_pending(self):
        result = capture.summarize(self.records(), process_ok=True, inputs_unchanged=True)
        self.assertEqual("passed", result["status"])
        self.assertEqual(8, len(result["scenarios"]))
        self.assertTrue(all(row["status"] == "passed" for row in result["scenarios"]))
        self.assertFalse(result["nativeAcceptance"])
        self.assertEqual([], result["completedOriginalTasks"])

    def test_skip_failure_missing_duplicate_extra_and_drift_cannot_pass(self):
        for kind in ("skipped", "failed", "missing", "duplicate", "extra", "drift", "process"):
            with self.subTest(kind=kind):
                rows = deepcopy(self.records())
                if kind in {"skipped", "failed"}:
                    rows[0]["outcome"] = kind
                elif kind == "missing":
                    rows.pop()
                elif kind == "duplicate":
                    rows.append(rows[0])
                elif kind == "extra":
                    rows.append({"testId": "unselected.test", "outcome": "passed"})
                report = capture.summarize(rows, process_ok=kind != "process",
                                           inputs_unchanged=kind != "drift")
                self.assertEqual("incomplete-or-failed", report["status"])
                self.assertFalse(report["nativeAcceptance"])

    def test_native_matrix_requires_loaded_instruction_bytes_and_authentic_sources(self):
        matrix = capture.native_capture_plan()
        self.assertEqual({"codex", "claude-code"}, set(matrix["hosts"]))
        self.assertEqual(16, len(matrix["procedures"]))
        self.assertEqual(5, len(matrix["bundle"]["skills"]))
        self.assertFalse(matrix["launchAuthorized"])
        self.assertEqual("M4.5 continuation / SPEC-044 T002", matrix["captureOwner"])
        self.assertIn("loaded instruction bytes; catalog visibility is insufficient",
                      matrix["requiredBindings"])
        self.assertIn("authenticated process/configuration/quota and exact approval",
                      matrix["requiredBindings"])
        self.assertEqual(16, len({(r["host"], r["scenario"]) for r in matrix["procedures"]}))
        inventory = load_inventory(source_checkout=True)
        self.assertEqual({item.fixture_id: item.definition_sha256 for item in inventory.fixtures},
                         matrix["fixtureDefinitionSha256ById"])
        self.assertEqual({item.prompt_id: item.sha256 for item in inventory.prompts},
                         matrix["promptSha256ById"])
        self.assertEqual(inventory.inventory_sha256, matrix["fixtureInventorySha256"])
        self.assertEqual(inventory.prompts_sha256, matrix["promptInventorySha256"])

    def test_reserved_capture_retains_failures_from_runner_git_and_initial_write(self):
        for kind in ("runner", "git", "write"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                output = capture.reserve_output(Path(temporary).resolve() / "capture")
                process = {"status": "passed", "outputTruncated": False,
                           "stdout": json.dumps(self.records()), "stderr": "raw diagnostics"}
                original_write = capture._write

                def writer(path, raw):
                    if kind == "write" and path.name == "native-capture-plan.json":
                        raise OSError("synthetic initial-write failure")
                    original_write(path, raw)

                with patch.object(capture, "_inputs", return_value={"synthetic.py": "a" * 64}), \
                     patch.object(capture, "_source_state", side_effect=RuntimeError("synthetic git failure")
                                  if kind == "git" else None, return_value={"commit": "a" * 40, "tree": "b" * 40, "status": ""}), \
                     patch.object(capture, "_run_process", side_effect=RuntimeError("synthetic runner failure")
                                  if kind == "runner" else None, return_value=process), \
                     patch.object(capture, "_write", side_effect=writer):
                    result = capture.capture(output, timeout=1, before={"synthetic.py": "a" * 64}, native={})
                self.assertEqual("incomplete-or-failed", result["status"])
                receipt = json.loads((output / "receipt.json").read_bytes())
                self.assertIn("synthetic", receipt["error"])
                self.assertTrue((output / "manifest.json").is_file())
                self.assertFalse(receipt["nativeAcceptance"])

    def test_bounded_worker_retains_raw_output_and_rejects_truncation(self):
        for truncated in (False, True):
            with self.subTest(truncated=truncated), tempfile.TemporaryDirectory() as temporary:
                output = capture.reserve_output(Path(temporary).resolve() / "capture")
                with patch.object(capture, "_inputs", return_value={"synthetic.py": "a" * 64}), \
                     patch.object(capture, "_source_state", return_value={"commit": "a" * 40, "tree": "b" * 40, "status": ""}), \
                     patch.object(capture, "_run_process", return_value={"status": "passed", "outputTruncated": truncated,
                        "stdout": json.dumps(self.records()), "stderr": "retained raw output"}):
                    report = capture.capture(output, timeout=1, before={"synthetic.py": "a" * 64}, native={})
                self.assertEqual("incomplete-or-failed" if truncated else "passed", report["status"])
                self.assertEqual(b"retained raw output", (output / "stderr.txt").read_bytes())

    def test_output_refuses_checkout_existing_directory_and_symlink(self):
        with self.assertRaises(ValueError):
            capture.reserve_output(capture.ROOT / "never-create-skill-capture")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            existing = root / "existing"
            existing.mkdir()
            link = root / "alias"
            link.symlink_to(existing, target_is_directory=True)
            for path in (existing, link):
                with self.assertRaises(ValueError):
                    capture.reserve_output(path)
            fresh = capture.reserve_output(root / "fresh")
            self.assertEqual(0o700, fresh.stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
