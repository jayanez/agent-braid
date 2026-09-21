# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from agent_braid.git_adapter import InvalidGitAnalysis, analyze_git, analyze_git_with_provenance
from scripts.run_git_benchmark import run as run_benchmark


ROOT = Path(__file__).resolve().parents[1]


class GitAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Agent Braid Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "a.txt").write_text("base a\n")
        (self.repo / "b.txt").write_text("base b\n")
        self.git("add", "a.txt", "b.txt")
        self.git("commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.left = self.commit_change("left", "a.txt", "left\n")
        self.git("checkout", "-q", "main")
        self.right = self.commit_change("right", "b.txt", "right\n")
        self.git("checkout", "-q", "main")

    def tearDown(self):
        self.temporary.cleanup()

    def git(self, *args, cwd=None):
        result = subprocess.run(
            ["git", "-C", str(cwd or self.repo), *args], text=True,
            capture_output=True, check=True,
        )
        return result.stdout

    def commit_change(self, branch, path, content):
        self.git("checkout", "-q", "-b", branch, self.base)
        (self.repo / path).write_text(content)
        self.git("add", path)
        self.git("commit", "-q", "-m", branch)
        return self.git("rev-parse", "HEAD").strip()

    def request(self, left=None, right=None):
        return {
            "gitAnalysisRequestVersion": "0.1.0-alpha",
            "repository": str(self.repo),
            "baseRevision": self.base,
            "operations": [
                {"instanceId": "left", "attemptId": "left-1",
                 "source": left or {"kind": "commit", "revision": self.left},
                 "dependencies": [], "uncertainPaths": []},
                {"instanceId": "right", "attemptId": "right-1",
                 "source": right or {"kind": "commit", "revision": self.right},
                 "dependencies": [], "uncertainPaths": []},
            ],
        }

    def test_disjoint_commits_are_syntactic_candidates_with_provenance(self):
        report, provenance = analyze_git_with_provenance(self.request())
        self.assertEqual(report["sourceKind"], "git-worktree-adapter")
        self.assertEqual(report["interactions"][0]["classification"], "independent-candidate")
        self.assertFalse(report["executionAuthorization"])
        self.assertEqual(provenance["reportInputDigest"], report["inputDigest"])
        self.assertEqual(len(provenance["operations"]), 2)
        self.assertNotIn(str(self.repo), json.dumps(report))

    def test_overlap_dependency_delete_binary_and_uncertainty_are_conservative(self):
        overlap = self.commit_change("overlap", "a.txt", "overlap\n")
        self.git("checkout", "-q", "main")
        request = self.request(right={"kind": "commit", "revision": overlap})
        self.assertEqual(analyze_git(request)["interactions"][0]["classification"], "conflicting")
        request = self.request()
        request["operations"][1]["dependencies"] = ["left"]
        self.assertEqual(analyze_git(request)["interactions"][0]["classification"], "ordered")
        request = self.request()
        request["operations"][0]["uncertainPaths"] = ["a.txt"]
        self.assertEqual(analyze_git(request)["interactions"][0]["classification"], "unknown")
        self.git("checkout", "-q", "-b", "binary", self.base)
        (self.repo / "binary.dat").write_bytes(b"a\0b")
        self.git("add", "binary.dat")
        self.git("commit", "-q", "-m", "binary")
        binary = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "main")
        request = self.request(right={"kind": "commit", "revision": binary})
        self.assertEqual(analyze_git(request)["interactions"][0]["classification"], "unknown")

    def test_worktree_includes_untracked_and_does_not_mutate_repository(self):
        worktree = Path(self.temporary.name) / "worktree"
        self.git("worktree", "add", "-q", "--detach", str(worktree), self.base)
        (worktree / "new.txt").write_text("new\n")
        before = self.git("status", "--porcelain=v1", "--untracked-files=all", cwd=worktree)
        report = analyze_git(self.request(
            left={"kind": "worktree", "path": str(worktree)},
            right={"kind": "commit", "revision": self.right},
        ))
        after = self.git("status", "--porcelain=v1", "--untracked-files=all", cwd=worktree)
        self.assertEqual(before, after)
        self.assertEqual(report["interactions"][0]["classification"], "independent-candidate")
        self.assertTrue(any(resource.endswith("/new.txt") for resource in report["operations"][0]["resources"]))

    def test_symlink_is_unknown_and_external_diff_is_disabled(self):
        worktree = Path(self.temporary.name) / "worktree-safe"
        self.git("worktree", "add", "-q", "--detach", str(worktree), self.base)
        outside = Path(self.temporary.name) / "outside-secret.txt"
        outside.write_text("must not be read\n")
        (worktree / "link.txt").symlink_to(outside)
        self.git("config", "diff.external", "/definitely/not/an/executable", cwd=worktree)
        report = analyze_git(self.request(
            left={"kind": "worktree", "path": str(worktree)},
            right={"kind": "commit", "revision": self.right},
        ))
        self.assertEqual(report["interactions"][0]["classification"], "unknown")
        self.assertNotIn("must not be read", json.dumps(report))

    def test_commit_symlink_and_worktree_gitlink_are_unknown(self):
        self.git("checkout", "-q", "-b", "commit-symlink", self.base)
        (self.repo / "link.txt").symlink_to("a.txt")
        self.git("add", "link.txt")
        self.git("commit", "-q", "-m", "commit symlink")
        symlink_commit = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "main")
        report = analyze_git(self.request(
            left={"kind": "commit", "revision": symlink_commit},
            right={"kind": "commit", "revision": self.right},
        ))
        self.assertEqual(report["interactions"][0]["classification"], "unknown")

        self.git("checkout", "-q", "-b", "gitlink-base", self.base)
        self.git("update-index", "--add", "--cacheinfo", f"160000,{self.left},vendor/module")
        self.git("commit", "-q", "-m", "gitlink base")
        gitlink_base = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "-b", "gitlink-right", gitlink_base)
        (self.repo / "b.txt").write_text("gitlink right\n")
        self.git("add", "b.txt")
        self.git("commit", "-q", "-m", "gitlink right")
        gitlink_right = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "main")
        worktree = Path(self.temporary.name) / "worktree-gitlink"
        self.git("worktree", "add", "-q", "--detach", str(worktree), gitlink_base)
        (worktree / "vendor/module").mkdir(parents=True, exist_ok=True)
        self.git("update-index", "--cacheinfo", f"160000,{self.right},vendor/module", cwd=worktree)
        request = self.request(
            left={"kind": "worktree", "path": str(worktree)},
            right={"kind": "commit", "revision": gitlink_right},
        )
        request["baseRevision"] = gitlink_base
        report = analyze_git(request)
        self.assertEqual(report["interactions"][0]["classification"], "unknown")

    def test_git_paths_preserve_leading_and_trailing_spaces(self):
        path = " leading-and-trailing.txt "
        self.git("checkout", "-q", "-b", "spaced-path", self.base)
        (self.repo / path).write_text("spaces are significant\n")
        self.git("add", "--", path)
        self.git("commit", "-q", "-m", "spaced path")
        spaced_commit = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "main")
        report, provenance = analyze_git_with_provenance(self.request(
            left={"kind": "commit", "revision": spaced_commit},
            right={"kind": "commit", "revision": self.right},
        ))
        self.assertEqual(report["interactions"][0]["classification"], "independent-candidate")
        self.assertEqual(provenance["operations"][0]["changes"][0]["path"], path)

    def test_rejects_unstable_unrelated_and_malformed_requests(self):
        with patch("agent_braid.git_adapter._snapshot", side_effect=[([], "a", "1"), ([], "a", "2")]):
            with self.assertRaisesRegex(InvalidGitAnalysis, "changed"):
                analyze_git(self.request())
        request = self.request()
        request["operations"] = request["operations"][:1]
        with self.assertRaisesRegex(InvalidGitAnalysis, "at least two"):
            analyze_git(request)
        foreign = Path(self.temporary.name) / "foreign"
        foreign.mkdir()
        subprocess.run(["git", "-C", str(foreign), "init", "-q"], check=True)
        request = self.request(left={"kind": "worktree", "path": str(foreign)})
        with self.assertRaises(InvalidGitAnalysis):
            analyze_git(request)
        orphan = self.commit_change("orphan", "a.txt", "orphan\n")
        self.git("checkout", "-q", "main")
        request = self.request(left={"kind": "commit", "revision": orphan})
        request["baseRevision"] = self.right
        with self.assertRaisesRegex(InvalidGitAnalysis, "not an ancestor"):
            analyze_git(request)

    def test_schema_cli_and_existing_commands_remain_compatible(self):
        schema = json.loads((ROOT / "schemas/0.1.0-alpha/git-analysis-request.schema.json").read_text())
        Draft202012Validator(schema).validate(self.request())
        report, provenance = analyze_git_with_provenance(self.request())
        provenance_schema = json.loads((ROOT / "schemas/0.1.0-alpha/git-analysis-provenance.schema.json").read_text())
        Draft202012Validator(provenance_schema).validate(provenance)
        request_path = Path(self.temporary.name) / "request.json"
        request_path.write_text(json.dumps(self.request()))
        provenance_path = Path(self.temporary.name) / "provenance.json"
        result = subprocess.run(
            [sys.executable, "-m", "agent_braid", "analyze-git", str(request_path), "--format", "text",
             "--provenance-output", str(provenance_path)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Execution authorization: false", result.stdout)
        Draft202012Validator(provenance_schema).validate(json.loads(provenance_path.read_text()))
        missing = subprocess.run(
            [sys.executable, "-m", "agent_braid", "analyze-git", str(request_path)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(missing.returncode, 2)
        existing = subprocess.run(
            [sys.executable, "-m", "agent_braid", "analyze", "examples/analysis/file-edits.json"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(existing.returncode, 0, existing.stdout + existing.stderr)

    def test_git_benchmark_has_no_false_safe_classifications(self):
        result = run_benchmark()
        self.assertEqual(result["scenarioCount"], 6)
        self.assertEqual(result["benchmarkVersion"], "git-m1-v2")
        self.assertEqual(result["classificationAgreement"], 6)
        self.assertEqual(result["falseSafeCount"], 0)
        self.assertEqual(result["falseSerializationCount"], 0)
        self.assertEqual(result["coverage"], 1.0)
        self.assertEqual({item["id"] for item in result["baselineComparisons"]},
                         {"file-overlap", "git-merge"})
        for baseline in result["baselineComparisons"]:
            self.assertTrue(baseline["measuredHere"])
            self.assertGreater(baseline["elapsedNanoseconds"], 0)
            self.assertGreater(baseline["gitCommandCount"], 0)
            self.assertEqual(len(baseline["results"]), 6)
            self.assertEqual({item["id"] for item in baseline["results"]},
                             {f"GIT-{number:03d}" for number in range(1, 7)})
            self.assertTrue(all(item["elapsedNanoseconds"] > 0 for item in baseline["results"]))
        merge = next(item for item in result["baselineComparisons"]
                     if item["id"] == "git-merge")
        self.assertTrue(all(item["exitCode"] in (0, 1) for item in merge["results"]))
        self.assertTrue(all(len(item["outputSha256"]) == 64 for item in merge["results"]))

    def test_git_benchmark_rejects_manifest_drift(self):
        manifest = json.loads((ROOT / "examples/analysis/git-benchmark.json").read_text())
        extra = dict(manifest["scenarios"][-1])
        extra["id"] = "GIT-007"
        manifest["scenarios"].append(extra)
        path = Path(self.temporary.name) / "drifted-git-benchmark.json"
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "not aligned"):
            run_benchmark(path)


if __name__ == "__main__":
    unittest.main()
