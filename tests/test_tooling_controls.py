# SPDX-License-Identifier: AGPL-3.0-only
"""Integrity and failure-retention tests for the SPEC-044 T003 runner."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import sys
import subprocess
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
    def _owned_repo(self, parent):
        repo = parent / "source"
        repo.mkdir()
        for name in (
            "agent_braid/baseline.py", "tests/baseline.py", "examples/tooling/baseline.json",
            "examples/analysis/file-edits.json", "specs/044-ai-tooling-evaluation/evaluation-protocol.md",
            "scripts/run_tooling_controls.py", "docs/tooling/CONTROLS.md", "pyproject.toml",
        ):
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("owned synthetic source fixture\n", encoding="ascii")
        (repo / ".gitignore").write_text("*.ignored.py\n__pycache__/\n", encoding="ascii")
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
        for args in (("init", "-q"), ("add", "."), ("commit", "-qm", "owned fixture")):
            subprocess.run(["git", "-c", "user.name=Control Fixture", "-c",
                            "user.email=fixture@example.invalid", "-c", "core.hooksPath=" + os.devnull,
                            *args], cwd=repo, env=env, check=True, capture_output=True)
        return repo

    def test_source_drift_cannot_turn_green_case_results_into_complete_evidence(self):
        # The subprocess oracle is stubbed; the candidate tree and Git changes
        # are real and confined to this test's owned disposable repository.
        for mutation in ("none", "added", "ignored-added", "removed", "modified", "symlink", "git-state"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix="m45-source-drift-") as tmp:
                parent = Path(tmp)
                repo = self._owned_repo(parent)
                result = parent / "result"
                mutated = False

                def complete_case(_repo, _case, _timeout):
                    nonlocal mutated
                    if not mutated:
                        mutated = True
                        if mutation in ("added", "ignored-added"):
                            name = "new.ignored.py" if mutation == "ignored-added" else "new.py"
                            (repo / "agent_braid" / name).write_text("new candidate input\n")
                        elif mutation == "removed":
                            (repo / "tests/baseline.py").unlink()
                        elif mutation == "modified":
                            (repo / "agent_braid/baseline.py").write_text("changed candidate input\n")
                        elif mutation == "symlink":
                            (repo / "agent_braid/alias.py").symlink_to(repo / "tests/baseline.py")
                        elif mutation == "git-state":
                            (repo / "outside-inventory.txt").write_text("concurrent change\n")
                    return {"status": "passed", "returnCode": 0}

                with patch.object(controls, "_execute_case", side_effect=complete_case):
                    self.assertEqual(0 if mutation == "none" else 1, controls._run(repo, result, 1))
                receipt = json.loads((result / "receipt.json").read_text())
                self.assertTrue(all(value == "passed" for value in receipt["cases"].values()))
                self.assertEqual("passed" if mutation == "none" else "incomplete", receipt["status"])
                if mutation != "none":
                    self.assertIn({"caseId": "source-integrity", "status": "changed"}, receipt["failureLedger"])
                if mutation == "ignored-added":
                    self.assertIn("agent_braid/new.ignored.py", receipt["sourceChanges"])
                    self.assertEqual([], receipt["candidateStateChanges"])
                if mutation == "symlink":
                    self.assertEqual(["source-inventory:RuntimeError"], receipt["sourceIntegrityErrors"])
                if mutation == "git-state":
                    self.assertEqual([], receipt["sourceChanges"])
                    self.assertIn("workingTreeStatusPorcelain", receipt["candidateStateChanges"])
                self.assertEqual([], controls._verify_result_root(result))
                if mutation == "none":
                    alias = parent / "alias"
                    alias.symlink_to(result, target_is_directory=True)
                    self.assertEqual(0, controls.main(["--verify-root", str(result)]))
                    self.assertEqual(2, controls.main(["--verify-root", str(alias)]))

    def test_freeze_rejects_ignored_input_added_during_inventory_capture(self):
        with tempfile.TemporaryDirectory(prefix="m45-freeze-drift-") as tmp:
            repo = self._owned_repo(Path(tmp))
            source_paths = controls._source_paths
            calls = 0

            def moving_paths(root):
                nonlocal calls
                paths = source_paths(root)
                calls += 1
                if calls == 1:
                    (repo / "agent_braid/new.ignored.py").write_text("concurrent source\n")
                return paths

            with patch.object(controls, "_source_paths", side_effect=moving_paths):
                with self.assertRaisesRegex(RuntimeError, "changed while freezing"):
                    controls._freeze(repo)

    def test_source_rescan_catches_ignored_file_added_during_hashing(self):
        with tempfile.TemporaryDirectory(prefix="m45-hash-window-") as temporary:
            repo = self._owned_repo(Path(temporary))
            frozen = controls._freeze(repo)
            original_sha = controls._sha
            added = False

            def add_during_hash(data):
                nonlocal added
                if not added:
                    added = True
                    (repo / "agent_braid/new.ignored.py").write_text("arrived during hashing\n")
                return original_sha(data)

            with patch.object(controls, "_sha", side_effect=add_during_hash):
                integrity = controls._source_integrity(repo, frozen["candidate"])
            self.assertTrue(added)
            self.assertIn("agent_braid/new.ignored.py", integrity["sourceChanges"])
            self.assertEqual([], integrity["sourceIntegrityErrors"])

    def test_source_rescan_failure_is_retained_as_integrity_error(self):
        with tempfile.TemporaryDirectory(prefix="m45-rescan-failure-") as temporary:
            repo = self._owned_repo(Path(temporary))
            frozen = controls._freeze(repo)
            original_paths = controls._source_paths
            calls = 0

            def fail_second_scan(root):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise RuntimeError("synthetic rescan failure")
                return original_paths(root)

            with patch.object(controls, "_source_paths", side_effect=fail_second_scan):
                integrity = controls._source_integrity(repo, frozen["candidate"])
            self.assertIn("source-rescan:RuntimeError", integrity["sourceIntegrityErrors"])

    def test_git_helper_ignores_inherited_git_dir_and_disables_fsmonitor(self):
        with tempfile.TemporaryDirectory(prefix="m45-git-env-") as temporary:
            parent = Path(temporary)
            repo = self._owned_repo(parent)
            other = parent / "other"
            other.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=other, check=True, capture_output=True)
            marker = parent / "fsmonitor-ran"
            executable = parent / "fsmonitor"
            executable.write_text(f"#!/bin/sh\nprintf ran > {marker}\n", encoding="ascii")
            executable.chmod(0o700)
            config = repo / ".git/config"
            with config.open("a", encoding="ascii") as stream:
                stream.write(f"\n[core]\n\tfsmonitor = {executable}\n")
            with patch.dict(os.environ, {"GIT_DIR": str(other / ".git")}):
                top = controls._git(repo, "rev-parse", "--show-toplevel")
                controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertEqual(str(repo.resolve()), top)
            self.assertFalse(marker.exists(), "configured fsmonitor executable ran")

    def test_configured_local_filter_is_refused_before_filter_execution(self):
        with tempfile.TemporaryDirectory(prefix="m45-git-filter-") as temporary:
            parent = Path(temporary)
            repo = self._owned_repo(parent)
            frozen = controls._freeze(repo)
            marker = parent / "filter-ran"
            executable = parent / "filter"
            executable.write_text(f"#!/bin/sh\nprintf ran > {marker}\ncat\n", encoding="ascii")
            executable.chmod(0o700)
            (repo / ".gitattributes").write_text("*.py filter=probe\n", encoding="ascii")
            config = repo / ".git/config"
            with config.open("a", encoding="ascii") as stream:
                stream.write(f"\n[filter \"probe\"]\n\tclean = {executable}\n")
            with self.assertRaisesRegex(RuntimeError, "configured Git filters"):
                controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertFalse(marker.exists(), "configured filter executable ran")
            integrity = controls._source_integrity(repo, frozen["candidate"])
            self.assertIn("git-commit:RuntimeError", integrity["sourceIntegrityErrors"])
            self.assertFalse(marker.exists(), "source integrity scan ran configured filter")

    def test_configured_worktree_filter_is_refused_before_filter_execution(self):
        with tempfile.TemporaryDirectory(prefix="m45-git-worktree-filter-") as temporary:
            parent = Path(temporary)
            repo = self._owned_repo(parent)
            marker = parent / "worktree-filter-ran"
            executable = parent / "worktree-filter"
            executable.write_text(f"#!/bin/sh\nprintf ran > {marker}\ncat\n", encoding="ascii")
            executable.chmod(0o700)
            (repo / ".gitattributes").write_text("*.py filter=probe\n", encoding="ascii")
            config = repo / ".git/config"
            with config.open("a", encoding="ascii") as stream:
                stream.write("\n[extensions]\n\tworktreeConfig = true\n")
            (repo / ".git/config.worktree").write_text(
                f'[filter "probe"]\n\tclean = {executable}\n', encoding="ascii")
            with self.assertRaisesRegex(RuntimeError, "configured Git filters"):
                controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertFalse(marker.exists(), "worktree-configured filter executable ran")

    def test_configured_included_filter_is_refused_before_filter_execution(self):
        with tempfile.TemporaryDirectory(prefix="m45-git-include-filter-") as temporary:
            parent = Path(temporary)
            repo = self._owned_repo(parent)
            marker = parent / "included-filter-ran"
            executable = parent / "included-filter"
            executable.write_text(f"#!/bin/sh\nprintf ran > {marker}\ncat\n", encoding="ascii")
            executable.chmod(0o700)
            (repo / ".gitattributes").write_text("*.py filter=probe\n", encoding="ascii")
            included = parent / "included-config"
            included.write_text(f'[filter "probe"]\n\tclean = {executable}\n', encoding="ascii")
            config = repo / ".git/config"
            with config.open("a", encoding="ascii") as stream:
                stream.write(f"\n[include]\n\tpath = {included}\n")
            with self.assertRaisesRegex(RuntimeError, "configured Git filters"):
                controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            self.assertFalse(marker.exists(), "included filter executable ran")

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
