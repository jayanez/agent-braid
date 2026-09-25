# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded T013 prototype regression tests."""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from agent_braid import git_integration_prototype as prototype
from agent_braid.cli import main
from agent_braid.git_process import (
    GitCommandLimitExceeded,
    GitCommandBudget,
    GitExecutionCancelled,
    GitExecutionTimeout,
    GitOutputLimitExceeded,
    GitResourceLimitUnavailable,
    GitScratchLimitExceeded,
    run_git,
)
from research.lab.model import loads


ROOT = Path(__file__).resolve().parents[1]


class GitIntegrationPrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as scratch:
            budget = GitCommandBudget(
                temp_root=Path(scratch), max_process_address_space_bytes=512 * 1024 * 1024,
            )
            environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
            try:
                run_git(Path(scratch), ("version",), env=environment, budget=budget)
                cls.hard_address_space_limit_available = True
            except GitResourceLimitUnavailable:
                cls.hard_address_space_limit_available = False

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Prototype fixture")
        self.git(self.repo, "config", "user.email", "prototype@example.invalid")
        files = {
            "a.txt": "base a\n",
            "b.txt": "base b\n",
            "c.txt": "base c\n",
            "conflict.txt": "same\n",
            "sections.txt": "alpha\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\ndelta\n",
        }
        for name, content in files.items():
            (self.repo / name).write_text(content, encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "base")
        self.base = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.left = self.commit_change("left", "a.txt", "left\n")
        self.right = self.commit_change("right", "b.txt", "right\n")
        self.third = self.commit_change("third", "c.txt", "third\n")
        self.hunk_left = self.commit_change(
            "hunk-left", "sections.txt",
            "ALPHA\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\ndelta\n",
        )
        self.hunk_right = self.commit_change(
            "hunk-right", "sections.txt",
            "alpha\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\nDELTA\n",
        )
        self.conflict_left = self.commit_change("conflict-left", "conflict.txt", "left\n")
        self.conflict_right = self.commit_change("conflict-right", "conflict.txt", "right\n")

    @staticmethod
    def git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", "-C", str(repo), *args], input=input_bytes,
            capture_output=True, check=True,
        ).stdout

    @staticmethod
    def text(output: bytes) -> str:
        return output.decode("ascii").strip()

    def commit_change(self, branch: str, path: str, content: str) -> str:
        self.git(self.repo, "checkout", "-qb", branch, self.base)
        (self.repo / path).write_text(content, encoding="utf-8")
        self.git(self.repo, "add", "--", path)
        self.git(self.repo, "commit", "-qm", branch)
        revision = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        return revision

    def request(self, commits=None, *, dependencies=None, reads=None, writes=None,
                resources=None, complete=None):
        commits = commits or [self.left, self.right]
        size = len(commits)
        dependencies = dependencies or [[] for _ in commits]
        reads = reads or [[] for _ in commits]
        writes = writes or [["a.txt" if index == 0 else "b.txt"]
                            for index in range(size)]
        resources = resources or [[] for _ in commits]
        complete = complete or [True for _ in commits]
        return {
            "gitIntegrationPrototypeRequestVersion": "0.1.0-alpha",
            "repository": str(self.repo),
            "baseRevision": self.base,
            "targetRef": "refs/heads/main",
            "operations": [
                {
                    "instanceId": f"op-{index}", "attemptId": f"attempt-{index}",
                    "source": {"kind": "commit", "revision": revision},
                    "dependencies": dependencies[index], "reads": reads[index],
                    "writes": writes[index], "sharedResources": resources[index],
                    "footprintComplete": complete[index],
                }
                for index, revision in enumerate(commits)
            ],
        }

    def source_state(self):
        index = self.repo / ".git" / "index"
        return {
            "head": self.git(self.repo, "rev-parse", "HEAD"),
            "refs": self.git(self.repo, "show-ref"),
            "status": self.git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"),
            "index": index.read_bytes(),
            "objects": self.git(self.repo, "count-objects", "-v"),
            "a": (self.repo / "a.txt").read_bytes(),
            "b": (self.repo / "b.txt").read_bytes(),
        }

    def assert_report_schema(self, report):
        schema = loads((ROOT / "schemas/0.1.0-alpha/git-integration-prototype-report.schema.json").read_text())
        Draft202012Validator(schema).validate(report)

    def run_prototype(self, request, **kwargs):
        if self.hard_address_space_limit_available:
            return prototype.run_prototype(request, **kwargs)
        # The production command remains fail-closed on this host. This test
        # adapter removes only the unsupported RLIMIT_AS setting so the rest
        # of the bounded algorithm can still receive regression coverage.
        original = prototype.GitCommandBudget

        def budget_without_unsupported_as_limit(**values):
            values["max_process_address_space_bytes"] = None
            return original(**values)

        with patch.object(prototype, "GitCommandBudget", budget_without_unsupported_as_limit):
            return prototype.run_prototype(request, **kwargs)

    def test_disjoint_preparation_is_parallel_and_source_stays_unchanged(self):
        before = self.source_state()
        report = self.run_prototype(self.request())
        self.assert_report_schema(report)
        self.assertEqual(report["candidateWaves"], [["op-0", "op-1"]])
        self.assertEqual(report["comparison"], {"status": "match", "treesEqual": True})
        self.assertEqual(report["unsafeAdmissionCount"], 0)
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["promotionPerformed"])
        self.assertTrue(report["sourceTargetRefMatchesPinnedBaseAtFinalCheck"])
        self.assertGreater(report["metrics"]["sampledPeakTemporaryDataBytes"], 0)
        self.assertLessEqual(report["metrics"]["sampledPeakTemporaryDataBytes"],
                             report["resourceLimits"]["temporaryDataBytes"])
        self.assertTrue(all(item["matchesSourceTree"] for item in report["operationPreparations"]))
        self.assertEqual(before, self.source_state())

    def test_verified_first_operation_uses_its_tree_without_redundant_merge(self):
        before = self.source_state()
        with patch.object(prototype, "_git", wraps=prototype._git) as invoke:
            report = self.run_prototype(self.request())
        merges = [call for call in invoke.call_args_list
                  if call.args[2:4] == ("merge-tree", "--write-tree")]
        self.assertEqual(len(merges), 2)  # One later merge per private lane.
        self.assertEqual(report["comparison"]["status"], "match")
        self.assertEqual(report["unsafeAdmissionCount"], 0)
        self.assertEqual(report["candidateIntegration"]["steps"][0]["tree"],
                         self.text(self.git(self.repo, "rev-parse", f"{self.left}^{{tree}}")))
        self.assertEqual(report["serialReference"]["steps"][0]["tree"],
                         self.text(self.git(self.repo, "rev-parse", f"{self.left}^{{tree}}")))
        self.assertEqual(before, self.source_state())

    def test_balanced_benchmark_order_preserves_verified_tree(self):
        before = self.source_state()
        ordinary = self.run_prototype(self.request())
        with patch.object(prototype, "_prepare_one", wraps=prototype._prepare_one) as prepare:
            reversed_order = self.run_prototype(self.request(), benchmark_serial_first=True)
        lanes = ["serial" if "serial" in call.args[0].parts else "candidate"
                 for call in prepare.call_args_list]
        self.assertEqual(lanes[:2], ["serial", "serial"])
        self.assertEqual(set(lanes[2:]), {"candidate"})
        self.assert_report_schema(reversed_order)
        self.assertEqual(reversed_order["comparison"]["status"], "match")
        self.assertEqual(reversed_order["candidateIntegration"]["finalTree"],
                         ordinary["candidateIntegration"]["finalTree"])
        self.assertEqual(reversed_order["serialReference"]["finalTree"],
                         ordinary["serialReference"]["finalTree"])
        self.assertEqual(reversed_order["unsafeAdmissionCount"], 0)
        self.assertEqual(before, self.source_state())

    def test_request_schema_is_versioned_and_rejects_unknown_fields(self):
        schema = loads((ROOT / "schemas/0.1.0-alpha/git-integration-prototype-request.schema.json").read_text())
        validator = Draft202012Validator(schema)
        request = self.request()
        validator.validate(request)
        changed = dict(request)
        changed["executionAuthorization"] = True
        self.assertTrue(list(validator.iter_errors(changed)))

    def test_read_write_and_shared_resource_overlap_are_serialized(self):
        operations = [
            {"instanceId": "op-0", "dependencies": []},
            {"instanceId": "op-1", "dependencies": []},
        ]
        for footprints in (
            {"op-0": {"reads": set(), "writes": {"a.txt"}, "sharedResources": set(), "footprintComplete": True},
             "op-1": {"reads": {"a.txt"}, "writes": {"b.txt"}, "sharedResources": set(), "footprintComplete": True}},
            {"op-0": {"reads": set(), "writes": {"a.txt"}, "sharedResources": {"build-cache"}, "footprintComplete": True},
             "op-1": {"reads": set(), "writes": {"b.txt"}, "sharedResources": {"build-cache"}, "footprintComplete": True}},
        ):
            self.assertEqual(prototype._waves(operations, footprints),
                             [["op-0"], ["op-1"]])

    def test_dependencies_constrain_candidate_waves(self):
        operations = [
            {"instanceId": "op-0", "dependencies": []},
            {"instanceId": "op-1", "dependencies": ["op-0"]},
        ]
        footprints = {
            "op-0": {"reads": set(), "writes": {"a.txt"}, "sharedResources": set(), "footprintComplete": True},
            "op-1": {"reads": set(), "writes": {"b.txt"}, "sharedResources": set(), "footprintComplete": True},
        }
        self.assertEqual(prototype._waves(operations, footprints), [["op-0"], ["op-1"]])

    def test_path_prefix_conflicts_and_distinct_hunks(self):
        self.assertTrue(prototype._path_sets_overlap({"dir"}, {"dir/file.txt"}))
        report = self.run_prototype(
            self.request([self.hunk_left, self.hunk_right],
                         writes=[["sections.txt"], ["sections.txt"]])
        )
        self.assertEqual(report["candidateWaves"], [["op-0"], ["op-1"]])
        self.assertEqual(report["comparison"]["status"], "match")

    def test_conflict_is_inconclusive_and_not_admitted(self):
        report = self.run_prototype(
            self.request([self.conflict_left, self.conflict_right],
                         writes=[["conflict.txt"], ["conflict.txt"]])
        )
        self.assertEqual(report["candidateWaves"], [["op-0"], ["op-1"]])
        self.assertEqual(report["candidateIntegration"]["status"], "conflict")
        self.assertEqual(report["comparison"]["status"], "inconclusive")
        self.assertEqual(report["unsafeAdmissionCount"], 0)
        self.assert_report_schema(report)

    def test_candidate_tree_verification_failure_is_inconclusive(self):
        before = self.source_state()
        result = {"status": "complete", "steps": [], "failure": None}
        candidate = {**result, "finalTree": self.text(self.git(self.repo, "rev-parse", "HEAD^{tree}"))}
        serial = {**result, "finalTree": self.text(self.git(self.repo, "rev-parse", f"{self.left}^{{tree}}"))}
        with patch.object(prototype, "_integrate_lane", side_effect=[candidate, serial]):
            report = self.run_prototype(self.request())
        self.assertEqual(report["comparison"], {"status": "divergent", "treesEqual": False})
        self.assertEqual(report["status"], "inconclusive")
        self.assertEqual(report["unsafeAdmissionCount"], 1)
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["promotionPerformed"])
        self.assert_report_schema(report)
        self.assertEqual(before, self.source_state())

    def test_declared_tracked_tree_check_fails_closed(self):
        expected = self.text(self.git(
            self.repo, "merge-tree", "--write-tree", self.left, self.right
        ))
        before = self.source_state()
        correct = self.request()
        correct["expectedFinalTree"] = expected
        passed = self.run_prototype(correct)
        self.assertEqual(passed["status"], "completed")
        self.assertEqual(passed["declaredTrackedTreeCheck"]["status"], "passed")
        wrong = self.request()
        wrong["expectedFinalTree"] = self.text(self.git(self.repo, "rev-parse", "HEAD^{tree}"))
        failed = self.run_prototype(wrong)
        self.assertEqual(failed["comparison"]["status"], "match")
        self.assertEqual(failed["declaredTrackedTreeCheck"]["status"], "failed")
        self.assertEqual(failed["status"], "inconclusive")
        self.assertEqual(failed["unsafeAdmissionCount"], 1)
        self.assertFalse(failed["executionAuthorization"])
        self.assert_report_schema(failed)
        self.assertEqual(before, self.source_state())

    def test_unknown_wildcard_and_undeclared_footprints_require_manual_review(self):
        unknown = self.request(complete=[False, True])
        report = self.run_prototype(unknown)
        self.assertEqual(report["status"], "manual-review")
        self.assertFalse(report["candidateWaves"])
        wildcard = self.request(writes=[["*.txt"], ["b.txt"]])
        self.assertEqual(self.run_prototype(wildcard)["status"], "manual-review")
        undeclared = self.request(writes=[[], ["b.txt"]])
        self.assertEqual(self.run_prototype(undeclared)["status"], "manual-review")

    def test_stale_target_ref_is_rejected_before_work(self):
        self.git(self.repo, "update-ref", "refs/heads/main", self.third)
        report = self.run_prototype(self.request())
        self.assertEqual(report["status"], "stale-base")
        self.assertEqual(report["reason"], "target-ref-does-not-match-pinned-base")
        self.assertFalse(report["sourceTargetRefMatchesPinnedBaseAtFinalCheck"])

    def test_target_ref_change_during_use_invalidates_both_lanes(self):
        original = prototype._target_commit
        calls = 0

        def move_after_post_prepare_check(repository, target_ref, env, budget):
            nonlocal calls
            observed = original(repository, target_ref, env, budget)
            calls += 1
            if calls == 2:
                self.git(self.repo, "update-ref", target_ref, self.third)
            return observed

        try:
            with patch.object(prototype, "_target_commit", side_effect=move_after_post_prepare_check):
                report = self.run_prototype(self.request())
            self.assertEqual(report["candidateIntegration"]["status"], "stale-base")
            self.assertEqual(report["comparison"]["status"], "inconclusive")
            self.assertFalse(report["sourceTargetRefMatchesPinnedBaseAtFinalCheck"])
        finally:
            self.git(self.repo, "update-ref", "refs/heads/main", self.base)

    def test_cancellation_stops_git_and_preserves_source_state(self):
        before = self.source_state()
        event = threading.Event()
        original_run_git = prototype.run_git
        first = True

        def cancel_after_first_process(*args, **kwargs):
            nonlocal first
            result = original_run_git(*args, **kwargs)
            if first:
                first = False
                event.set()
            return result

        try:
            with patch.object(prototype, "run_git", side_effect=cancel_after_first_process):
                with self.assertRaises(GitExecutionCancelled):
                    self.run_prototype(self.request(), cancel_event=event)
        finally:
            self.assertEqual(before, self.source_state())

    def test_cli_writes_report_only_to_explicit_output(self):
        request_path = self.root / "request.json"
        report_path = self.root / "report.json"
        request = self.request()
        request["targetRef"] = "refs/heads/not-present"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            if self.hard_address_space_limit_available:
                result = main([
                    "prototype-git", str(request_path), "--report-output", str(report_path)
                ])
            else:
                original = prototype.GitCommandBudget

                def budget_without_unsupported_as_limit(**values):
                    values["max_process_address_space_bytes"] = None
                    return original(**values)

                with patch.object(prototype, "GitCommandBudget", budget_without_unsupported_as_limit):
                    result = main([
                        "prototype-git", str(request_path), "--report-output", str(report_path)
                    ])
            self.assertEqual(result, 0)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(stdout.getvalue()), report)
        self.assertEqual(report["status"], "stale-base")
        self.assert_report_schema(report)

    def test_production_cli_fails_closed_when_hard_memory_limit_is_unavailable(self):
        if self.hard_address_space_limit_available:
            self.skipTest("host can enforce the production child address-space limit")
        request_path = self.root / "bounded-request.json"
        report_path = self.root / "bounded-report.json"
        request_path.write_text(json.dumps(self.request()), encoding="utf-8")
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            result = main([
                "prototype-git", str(request_path), "--report-output", str(report_path)
            ])
        self.assertEqual(result, 3)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "infrastructure-failure")
        self.assertEqual(json.loads(stdout.getvalue())["category"], "resource-limit-unavailable")
        self.assertFalse(report_path.exists())

    def test_address_space_limit_wrapper_runs_git_without_touching_source(self):
        with tempfile.TemporaryDirectory() as scratch:
            budget = GitCommandBudget(temp_root=Path(scratch),
                                      max_process_address_space_bytes=512 * 1024 * 1024)
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"}
            if self.hard_address_space_limit_available:
                output = run_git(self.repo, ("version",), env=env, budget=budget).stdout
                self.assertTrue(output.startswith(b"git version "))
            else:
                with self.assertRaises(GitResourceLimitUnavailable):
                    run_git(self.repo, ("version",), env=env, budget=budget)

    def test_resource_exhaustion_controls_fail_closed_without_source_mutation(self):
        before = self.source_state()
        controls = (
            ("wall", GitCommandBudget, {"wall_seconds": 0.0}, GitExecutionTimeout),
            ("commands", GitCommandBudget, {"max_commands": 0}, GitCommandLimitExceeded),
            ("output", GitCommandBudget, {"max_output_bytes": 0}, GitOutputLimitExceeded),
        )
        for name, budget_type, limits, failure in controls:
            with self.subTest(limit=name), tempfile.TemporaryDirectory() as directory:
                budget = budget_type(temp_root=Path(directory), **limits)
                with self.assertRaises(failure):
                    run_git(self.repo, ("version",), env={"LC_ALL": "C"}, budget=budget)

        with tempfile.TemporaryDirectory() as directory:
            scratch = Path(directory)
            (scratch / "over-budget.bin").write_bytes(b"x")
            budget = GitCommandBudget(temp_root=scratch, max_scratch_bytes=0)
            with self.assertRaises(GitScratchLimitExceeded):
                run_git(self.repo, ("version",), env={"LC_ALL": "C"}, budget=budget)
        self.assertEqual(before, self.source_state())

    def test_inflight_git_timeout_and_scratch_limit_kill_the_child(self):
        before = self.source_state()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mode, limits, expected in (
                ("timeout", {"wall_seconds": 0.5}, GitExecutionTimeout),
                ("scratch", {"max_scratch_bytes": 0}, GitScratchLimitExceeded),
                ("cancel", {}, GitExecutionCancelled),
            ):
                with self.subTest(mode=mode):
                    scratch = root / mode
                    scratch.mkdir()
                    marker = root / f"{mode}.pid"
                    actual_popen = subprocess.Popen
                    cancellation = threading.Event()

                    def start_controlled_child(_command, **kwargs):
                        child = actual_popen(["/bin/sleep", "10"], **kwargs)
                        marker.write_text(str(child.pid), encoding="ascii")
                        if mode == "scratch":
                            threading.Timer(
                                0.1, lambda: (scratch / "write.bin").write_bytes(b"excess")
                            ).start()
                        if mode == "cancel":
                            threading.Timer(0.1, cancellation.set).start()
                        return child

                    budget = GitCommandBudget(temp_root=scratch,
                                              cancel_event=cancellation, **limits)
                    with patch("agent_braid.git_process.subprocess.Popen",
                               side_effect=start_controlled_child):
                        with self.assertRaises(expected):
                            run_git(self.repo, ("version",), env={"LC_ALL": "C"}, budget=budget)
                    self.assertTrue(marker.exists(), "the Git child must have started")
                    with self.assertRaises(ProcessLookupError):
                        os.kill(int(marker.read_text().strip()), 0)
        self.assertEqual(before, self.source_state())


if __name__ == "__main__":
    unittest.main()
