# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import Draft202012Validator

from agent_braid.git_replay import (
    InvalidGitReplay,
    _bundle_digest,
    _plan_digest,
    plan as plan_git,
    produce,
    verify,
    verify_plan,
)
from agent_braid.git_process import (
    GitCommandBudget,
    GitExecutionTimeout,
    GitOutputLimitExceeded,
    GitProcessStartFailure,
    GitScratchLimitExceeded,
    run_git,
)
from scripts.run_git_replay_benchmark import run as run_benchmark


ROOT = Path(__file__).resolve().parents[1]


class GitReplayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Git replay test")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        for name, content in {
            "a.txt": "base a\n",
            "b.txt": "base b\n",
            "c.txt": "base c\n",
            "sections.txt": "alpha\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\ndelta\n",
            "overlap.txt": "same\n",
        }.items():
            (self.repo / name).write_text(content, encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "base")
        self.base = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.left = self.commit_change("left", "a.txt", "left\n")
        self.right = self.commit_change("right", "b.txt", "right\n")
        self.third = self.commit_change("third", "c.txt", "third\n")
        self.hunk_left = self.commit_change(
            "hunk-left", "sections.txt", "ALPHA\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\ndelta\n"
        )
        self.hunk_right = self.commit_change(
            "hunk-right", "sections.txt", "alpha\nline-02\nline-03\nline-04\nline-05\nline-06\nline-07\nline-08\nline-09\nline-10\nline-11\nDELTA\n"
        )
        self.overlap_left = self.commit_change("overlap-left", "overlap.txt", "left\n")
        self.overlap_right = self.commit_change("overlap-right", "overlap.txt", "right\n")

    @staticmethod
    def text(value):
        return value.decode().strip()

    @staticmethod
    def git(repo, *args, input_bytes=None):
        return subprocess.run(
            ["git", "-C", str(repo), *args], input=input_bytes,
            capture_output=True, check=True,
        ).stdout

    def commit_change(self, branch, path, content):
        self.git(self.repo, "checkout", "-qb", branch, self.base)
        (self.repo / path).write_text(content, encoding="utf-8")
        self.git(self.repo, "add", "--", path)
        self.git(self.repo, "commit", "-qm", branch)
        commit = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        return commit

    def request(self, commits=None, dependencies=None, uncertain=None):
        commits = commits or [self.left, self.right]
        dependencies = dependencies or [[] for _ in commits]
        uncertain = uncertain or [[] for _ in commits]
        return {
            "gitAnalysisRequestVersion": "0.1.0-alpha",
            "repository": str(self.repo),
            "baseRevision": self.base,
            "operations": [
                {
                    "instanceId": f"op-{index}",
                    "attemptId": f"attempt-{index}",
                    "source": {"kind": "commit", "revision": commit},
                    "dependencies": dependencies[index],
                    "uncertainPaths": uncertain[index],
                }
                for index, commit in enumerate(commits)
            ],
        }

    def test_plan_replay_two_immutable_commits(self):
        bundle, plan = produce(self.request())
        self.assertEqual(bundle["result"], "equivalent-observed")
        self.assertEqual(bundle["observationContract"], "tracked-tree-v1")
        self.assertEqual(plan["mode"], "candidate-preparation-waves")
        self.assertEqual(plan["waves"], [["op-0", "op-1"]])
        self.assertFalse(plan["executionAuthorization"])
        self.assertNotIn(str(self.repo), json.dumps(bundle))
        self.assertEqual(verify(bundle, str(self.repo))["status"], "verified")

    def test_concurrent_replays_do_not_mutate_process_environment(self):
        original_environment = os.environ.copy()
        request = self.request([self.left, self.right, self.third])
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: produce(request), range(4)))
        self.assertEqual(os.environ.copy(), original_environment)
        self.assertTrue(all(item == results[0] for item in results[1:]))

    def test_resource_budget_bounds_time_output_temp_data_and_start_errors(self):
        environment = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.root),
            "LC_ALL": "C",
        }
        with self.subTest("time"):
            temp_root = self.root / "budget-time"
            temp_root.mkdir()
            budget = GitCommandBudget(temp_root=temp_root, wall_seconds=0)
            with self.assertRaises(GitExecutionTimeout):
                run_git(self.repo, ("status", "--short"), env=environment, budget=budget)
        with self.subTest("streamed output"):
            temp_root = self.root / "budget-output"
            temp_root.mkdir()
            budget = GitCommandBudget(
                temp_root=temp_root, max_output_bytes=32, max_command_output_bytes=32
            )
            with self.assertRaises(GitOutputLimitExceeded):
                run_git(self.repo, ("show", self.left), env=environment, budget=budget)
        with self.subTest("temporary data"):
            temp_root = self.root / "budget-scratch"
            temp_root.mkdir()
            scratch = temp_root / "over-budget"
            scratch.mkdir()
            (scratch / "large.bin").write_bytes(b"x" * 128)
            budget = GitCommandBudget(temp_root=temp_root, max_scratch_bytes=64)
            with self.assertRaises(GitScratchLimitExceeded):
                run_git(self.repo, ("status", "--short"), env=environment, budget=budget)
        with self.subTest("process start"):
            temp_root = self.root / "budget-start"
            temp_root.mkdir()
            budget = GitCommandBudget(temp_root=temp_root)
            with self.assertRaises(GitProcessStartFailure):
                run_git(self.repo, ("status", "--short"), env={"PATH": ""}, budget=budget)

    def test_plan_verifier_regenerates_from_verified_evidence(self):
        bundle, plan = produce(self.request())
        self.assertEqual(verify_plan(plan, bundle, str(self.repo))["status"], "verified")

        changed = deepcopy(plan)
        changed["waves"] = [["op-0"], ["op-1"]]
        changed["planDigest"] = _plan_digest(changed)
        result = verify_plan(changed, bundle, str(self.repo))
        self.assertEqual(result["status"], "rejected")
        self.assertIn("regenerated", result["reason"])

        bad_digest = deepcopy(plan)
        bad_digest["planDigest"] = "sha256:" + "0" * 64
        self.assertEqual(verify_plan(bad_digest, bundle, str(self.repo))["status"], "rejected")

        changed_evidence = deepcopy(bundle)
        changed_evidence["evidenceDigest"] = "sha256:" + "0" * 64
        self.assertEqual(verify_plan(plan, changed_evidence, str(self.repo))["status"], "rejected")

    def test_evidence_is_canonical_for_input_operation_order(self):
        request = self.request([self.left, self.right, self.third])
        reordered = deepcopy(request)
        reordered["operations"].reverse()
        first, first_plan = produce(request)
        second, second_plan = produce(reordered)
        self.assertEqual(first, second)
        self.assertEqual(first_plan, second_plan)

    def test_rejects_worktree_batch_limits_and_invalid_graph(self):
        request = self.request()
        request["operations"][0]["source"] = {"kind": "worktree", "path": str(self.repo)}
        with self.assertRaisesRegex(InvalidGitReplay, "commit sources only"):
            produce(request)
        five = self.request([self.left, self.right, self.third, self.left, self.right])
        with self.assertRaisesRegex(InvalidGitReplay, "2–4 operations"):
            produce(five)
        cyclic = self.request(dependencies=[["op-1"], ["op-0"]])
        with self.assertRaisesRegex(InvalidGitReplay, "cyclic"):
            produce(cyclic)
        missing = self.request(["0" * 40, self.right])
        with self.assertRaises(InvalidGitReplay):
            produce(missing)

    def test_enforces_changed_path_and_aggregate_patch_bounds(self):
        many_sources = []
        for operation in range(4):
            branch = f"path-bound-{operation}"
            self.git(self.repo, "checkout", "-qb", branch, self.base)
            paths = []
            for index in range(17):
                name = f"bound-{operation}-{index}.txt"
                (self.repo / name).write_text("bounded path\n", encoding="utf-8")
                paths.append(name)
            self.git(self.repo, "add", "--", *paths)
            self.git(self.repo, "commit", "-qm", branch)
            many_sources.append(self.text(self.git(self.repo, "rev-parse", "HEAD")))
            self.git(self.repo, "checkout", "-q", "main")
        with self.assertRaisesRegex(InvalidGitReplay, "changed path count exceeds 64"):
            produce(self.request(many_sources))

        self.git(self.repo, "checkout", "-qb", "patch-bound", self.base)
        large = self.repo / "large.txt"
        large.write_text("x" * 1_048_577 + "\n", encoding="utf-8")
        self.git(self.repo, "add", "--", "large.txt")
        self.git(self.repo, "commit", "-qm", "oversized patch")
        large_commit = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        with self.assertRaisesRegex(InvalidGitReplay, "aggregate patch bytes exceed 1 MiB"):
            produce(self.request([large_commit, self.right]))

    def test_replays_disjoint_and_different_hunk_patches(self):
        before = {
            "head": self.text(self.git(self.repo, "rev-parse", "HEAD")),
            "status": self.git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"),
            "refs": self.git(self.repo, "show-ref"),
            "objects": sorted(self.git(
                self.repo, "cat-file", "--batch-all-objects",
                "--batch-check=%(objectname)",
            ).splitlines()),
        }
        disjoint, _ = produce(self.request([self.left, self.right, self.third]))
        hunks, plan = produce(self.request([self.hunk_left, self.hunk_right]))
        self.assertEqual(disjoint["result"], "equivalent-observed")
        self.assertEqual(len(disjoint["schedules"]), 6)
        self.assertEqual(hunks["result"], "equivalent-observed")
        self.assertEqual(plan["waves"], [["op-0", "op-1"]])
        after = {
            "head": self.text(self.git(self.repo, "rev-parse", "HEAD")),
            "status": self.git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"),
            "refs": self.git(self.repo, "show-ref"),
            "objects": sorted(self.git(
                self.repo, "cat-file", "--batch-all-objects",
                "--batch-check=%(objectname)",
            ).splitlines()),
        }
        self.assertEqual(after, before)

    def test_divergent_and_failed_orders_are_not_candidates(self):
        bundle, plan = produce(self.request([self.overlap_left, self.overlap_right]))
        self.assertIn(bundle["result"], {"inconclusive", "divergent"})
        self.assertNotEqual(plan["mode"], "candidate-preparation-waves")
        self.assertFalse(plan["executionAuthorization"])

    def test_verifier_rejects_tampering_and_omitted_orders(self):
        bundle, _ = produce(self.request())
        self.assertEqual(verify(bundle, str(self.repo))["status"], "verified")
        changed = deepcopy(bundle)
        changed["operations"][0]["patchDigest"] = "sha256:" + "0" * 64
        changed["evidenceDigest"] = _bundle_digest(changed)
        self.assertEqual(verify(changed, str(self.repo))["status"], "rejected")
        self.assertEqual(plan_git(changed, str(self.repo))["mode"], "manual-review")
        omitted = deepcopy(bundle)
        omitted["schedules"].pop()
        omitted["evidenceDigest"] = _bundle_digest(omitted)
        self.assertEqual(verify(omitted, str(self.repo))["status"], "rejected")
        duplicated = deepcopy(bundle)
        duplicated["schedules"].append(deepcopy(duplicated["schedules"][0]))
        duplicated["evidenceDigest"] = _bundle_digest(duplicated)
        self.assertEqual(verify(duplicated, str(self.repo))["status"], "rejected")

    def test_advisory_waves_preserve_dependencies_and_demonstrate_gain(self):
        bundle, plan = produce(self.request(
            [self.left, self.right, self.third], dependencies=[[], ["op-0"], []]
        ))
        self.assertEqual(bundle["result"], "equivalent-observed")
        self.assertEqual(plan["waves"], [["op-0", "op-2"], ["op-1"]])
        self.assertEqual(sum(map(len, plan["waves"])), 3)
        self.assertFalse(plan["executionAuthorization"])

    def test_unknown_and_inconclusive_inputs_never_make_candidate_waves(self):
        uncertain, uncertain_plan = produce(self.request(
            [self.left, self.right], uncertain=[["a.txt"], []]
        ))
        self.assertEqual(uncertain["result"], "equivalent-observed")
        self.assertEqual(uncertain_plan["mode"], "serial-fallback")
        self.assertEqual(uncertain_plan["waves"], [["op-0"], ["op-1"]])

        # Use a real deletion commit from the common base.
        self.git(self.repo, "checkout", "-qb", "actual-deletion", self.base)
        (self.repo / "a.txt").unlink()
        self.git(self.repo, "add", "-u", "--", "a.txt")
        self.git(self.repo, "commit", "-qm", "actual deletion")
        deletion = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        deleted, delete_plan = produce(self.request([deletion, self.right]))
        self.assertFalse(deleted["operations"][0]["eligible"])
        self.assertNotEqual(delete_plan["mode"], "candidate-preparation-waves")

        _, failed_plan = produce(self.request([self.overlap_left, self.overlap_right]))
        self.assertNotEqual(failed_plan["mode"], "candidate-preparation-waves")

        self.git(self.repo, "checkout", "-qb", "actual-symlink", self.base)
        (self.repo / "link.txt").symlink_to("a.txt")
        self.git(self.repo, "add", "--", "link.txt")
        self.git(self.repo, "commit", "-qm", "symlink")
        symlink = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        link_bundle, link_plan = produce(self.request([symlink, self.right]))
        self.assertFalse(link_bundle["operations"][0]["eligible"])
        self.assertNotEqual(link_plan["mode"], "candidate-preparation-waves")

    def test_benchmark_thresholds_and_baselines(self):
        report = run_benchmark()
        self.assertEqual(report["scenarioCount"], 7)
        self.assertEqual(report["falseCandidateCount"], 0)
        three = next(item for item in report["results"] if item["id"] == "GIT-REPLAY-001")
        self.assertEqual(three["plannerWaveCount"], 1)
        self.assertEqual(three["serialWaveCount"], 3)
        hunks = next(item for item in report["results"] if item["id"] == "GIT-REPLAY-002")
        self.assertEqual(hunks["plannerWaveCount"], 1)
        self.assertEqual(hunks["pathOverlapWaveCount"], 2)
        self.assertEqual(hunks["gitMergeWaveCount"], 1)
        self.assertTrue(all(item["plannerGitCommandCount"] > 0
                            for item in report["results"]))
        self.assertGreater(sum(item["mergeGitCommandCount"] for item in report["results"]), 0)

    def test_cli_and_schemas(self):
        request = self.request()
        request_path = self.root / "request.json"
        evidence_path = self.root / "evidence.json"
        plan_path = self.root / "plan.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "agent_braid", "plan-git", str(request_path),
             "--evidence-output", str(evidence_path)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        plan = json.loads(result.stdout)
        bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        Draft202012Validator(json.loads((ROOT / "schemas/0.1.0-alpha/git-plan.schema.json").read_text())).validate(plan)
        Draft202012Validator(json.loads((ROOT / "schemas/0.1.0-alpha/git-replay-evidence.schema.json").read_text())).validate(bundle)
        verified = subprocess.run(
            [sys.executable, "-m", "agent_braid", "verify-git", str(evidence_path),
             "--repository", str(self.repo)], cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
        self.assertEqual(json.loads(verified.stdout)["status"], "verified")
        plan_verified = subprocess.run(
            [sys.executable, "-m", "agent_braid", "verify-plan", str(plan_path),
             "--evidence", str(evidence_path), "--repository", str(self.repo)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(plan_verified.returncode, 0,
                         plan_verified.stdout + plan_verified.stderr)
        self.assertEqual(json.loads(plan_verified.stdout)["status"], "verified")


if __name__ == "__main__":
    unittest.main()
