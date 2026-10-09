# SPDX-License-Identifier: AGPL-3.0-only
"""Integrity and failure-retention tests for the SPEC-044 T003 runner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

from scripts import run_tooling_controls as controls


REPO = Path(__file__).resolve().parents[1]


class ControlsManifestTests(unittest.TestCase):
    def test_matrix_has_unique_exact_sources_and_positive_refusal_pairs(self):
        case_ids = [case["id"] for case in controls.CASES]
        self.assertEqual(len(case_ids), len(set(case_ids)))
        case_by_id = {case["id"]: case for case in controls.CASES}
        for category, specification in controls.MANDATORY_CATEGORIES.items():
            rows = [case_by_id[case_id] for case_id in specification["caseIds"]]
            # A named positive oracle may be shared by an adjacent refusal
            # category (for example, valid parity is the malformed-input pair).
            self.assertTrue(all(row["category"] in controls.MANDATORY_CATEGORIES for row in rows))
            self.assertTrue(all(row["oracle"].strip() for row in rows))
            roles = {row["role"] for row in rows}
            self.assertIn("positive", roles, category)
            if category == "recovery":
                self.assertEqual({"positive"}, roles)
                self.assertTrue(any("interruption" in row["oracle"] and "recovers" in row["oracle"]
                                    for row in rows))
            elif category != "parity":
                self.assertIn("refusal", roles, category)
        self.assertTrue(all("tests." in case["test"] and ".test_" in case["test"]
                            for case in controls.CASES))

    def test_freeze_binds_candidate_dirty_state_and_full_owned_fixture_tree(self):
        frozen = controls._freeze(REPO)
        candidate = frozen["candidate"]
        manifest = {row["path"]: row for row in candidate["sourceManifest"]}
        self.assertEqual(40, len(candidate["commit"]))
        self.assertIn("workingTreeStatusPorcelain", candidate)
        self.assertIn("agent_braid/tooling_mcp.py", manifest)
        self.assertIn("examples/tooling/fixture-inventory.json", manifest)
        self.assertIn("tests/test_tooling_fixtures.py", manifest)
        self.assertIn("tests/test_git_runtime.py", manifest)
        self.assertIn("specs/044-ai-tooling-evaluation/evaluation-protocol.md", manifest)
        self.assertEqual(controls._sha(controls._json_bytes(candidate["sourceManifest"])),
                         candidate["sourceManifestSha256"])
        self.assertEqual("unittest-control-source", frozen["execution"]["kind"])
        self.assertEqual(0, frozen["execution"]["providerCalls"])


class ControlsResultTests(unittest.TestCase):
    def test_result_root_is_exclusive_and_outside_source(self):
        with tempfile.TemporaryDirectory(prefix="m45-controls-path-") as temporary:
            parent = Path(temporary)
            existing = parent / "existing"
            existing.mkdir()
            payload = existing / "keep"
            payload.write_text("preserve", encoding="ascii")
            with self.assertRaises(FileExistsError):
                controls._run(REPO, existing, 1)
            self.assertEqual("preserve", payload.read_text(encoding="ascii"))
            inside = REPO / "never-create-t003-result-root"
            with self.assertRaisesRegex(ValueError, "disjoint"):
                controls._run(REPO, inside, 1)
            self.assertFalse(inside.exists())

    def test_interrupt_retains_interrupted_case_and_not_started_denominator(self):
        with tempfile.TemporaryDirectory(prefix="m45-controls-notstarted-") as temporary:
            parent = Path(temporary)
            result = parent / "result"

            def interrupt_before_case(_repo, _case, _timeout):
                self.assertTrue((result / "manifest.json").is_file())
                rows = {path.stem: json.loads(path.read_text(encoding="ascii"))
                        for path in (result / "cases").glob("*.json")}
                self.assertEqual(len(controls.CASES), len(rows))
                self.assertEqual("running", rows[controls.CASES[0]["id"]]["status"])
                self.assertTrue(all(row["status"] == "not-started"
                                    for case_id, row in rows.items()
                                    if case_id != controls.CASES[0]["id"]))
                raise KeyboardInterrupt

            with patch.object(controls, "_execute_case", side_effect=interrupt_before_case):
                self.assertEqual(130, controls._run(REPO, result, 1))
            rows = {path.stem: json.loads(path.read_text(encoding="ascii"))
                    for path in (result / "cases").glob("*.json")}
            self.assertEqual("interrupted", rows[controls.CASES[0]["id"]]["status"])
            self.assertTrue(all(row["status"] == "not-started"
                                for case_id, row in rows.items()
                                if case_id != controls.CASES[0]["id"]))
            receipt = json.loads((result / "receipt.json").read_text(encoding="ascii"))
            self.assertEqual("incomplete", receipt["status"])
            self.assertEqual("interrupted", receipt["cases"][controls.CASES[0]["id"]])
            self.assertEqual([], controls._verify_result_root(result))

    def test_failures_remain_in_failure_ledger_and_result_tampering_is_detected(self):
        with tempfile.TemporaryDirectory(prefix="m45-controls-failure-") as temporary:
            result = Path(temporary) / "result"
            first_id = controls.CASES[0]["id"]

            def fail_first(_repo, case, _timeout):
                return {"status": "failed" if case["id"] == first_id else "passed",
                        "returnCode": 1 if case["id"] == first_id else 0,
                        "timedOut": False, "stdout": "", "stderr": "synthetic expected failure" if case["id"] == first_id else "",
                        "stdoutBytesRetained": 0, "stderrBytesRetained": 0,
                        "outputTruncated": False, "argv": ["python", "-m", "unittest", case["test"]]}

            with patch.object(controls, "_execute_case", side_effect=fail_first):
                code = controls._run(REPO, result, 1)
            self.assertEqual(1, code)
            receipt = json.loads((result / "receipt.json").read_text(encoding="ascii"))
            self.assertEqual("incomplete", receipt["status"])
            self.assertEqual({"caseId": first_id, "status": "failed"}, receipt["failureLedger"][0])
            self.assertEqual("failed", receipt["cases"][first_id])
            self.assertEqual("passed", receipt["cases"][controls.CASES[1]["id"]])
            self.assertEqual([], controls._verify_result_root(result))

            case_path = result / "cases" / f"{first_id}.json"
            case_path.write_bytes(case_path.read_bytes() + b"tamper")
            self.assertTrue(any("hash mismatch" in error for error in controls._verify_result_root(result)))

    @unittest.skipUnless(os.name == "posix", "owned process-group control requires POSIX sessions")
    def test_parent_exit_with_pipe_inheriting_child_cleans_owned_group_and_fails(self):
        child_code = "import time; time.sleep(60)"
        parent_code = (
            "import subprocess,sys; "
            f"child=subprocess.Popen([sys.executable,'-c',{child_code!r}], "
            "stdout=sys.stdout,stderr=sys.stderr); "
            "print(child.pid,flush=True)"
        )
        own_group = os.getpgrp()
        result = controls._run_process([sys.executable, "-c", parent_code], REPO, 10)
        self.assertEqual("failed", result["status"])
        self.assertTrue(result["lingeringDescendantDetected"])
        self.assertEqual("absent", result["ownedProcessGroupState"])
        self.assertEqual("present", controls._group_state(own_group), "cleanup signaled an unrelated group")
        self.assertTrue(result["stdout"].strip().isdigit(), result["stdout"])

    @unittest.skipUnless(os.name == "posix", "owned process-group control requires POSIX sessions")
    def test_timeout_terminates_and_reaps_only_owned_group(self):
        own_group = os.getpgrp()
        result = controls._run_process([sys.executable, "-c", "import time; time.sleep(60)"], REPO, 1)
        self.assertEqual("timeout", result["status"])
        self.assertEqual("absent", result["ownedProcessGroupState"])
        self.assertEqual("present", controls._group_state(own_group), "timeout cleanup signaled an unrelated group")

    @unittest.skipUnless(os.name == "posix", "owned process-group control requires POSIX sessions")
    def test_interruption_during_wait_cleans_owned_group_before_propagating(self):
        real_popen = controls.subprocess.Popen
        launched = {}

        def capture_process(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            launched["pid"] = process.pid
            self.assertEqual(process.pid, os.getpgid(process.pid))
            return process

        with patch.object(controls.subprocess, "Popen", side_effect=capture_process):
            with patch.object(controls, "_wait_events", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    controls._run_process([sys.executable, "-c", "import time; time.sleep(60)"], REPO, 30)
        self.assertIn("pid", launched)
        self.assertEqual("absent", controls._group_state(launched["pid"]))
        self.assertEqual("present", controls._group_state(os.getpgrp()), "interrupt cleanup signaled an unrelated group")

    def test_successfully_skipped_oracle_is_unavailable_not_passed(self):
        code = "import sys; print('test_optional (tests.x.Suite) ... skipped missing SDK', file=sys.stderr)"
        result = controls._run_process(
            [sys.executable, "-c", code, "tests.x.Suite.test_optional"], REPO, 5)
        self.assertEqual(0, result["returnCode"])
        self.assertTrue(result["skipDetected"])
        self.assertEqual("unavailable", result["status"])

if __name__ == "__main__":
    unittest.main()
