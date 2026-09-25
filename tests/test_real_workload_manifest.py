# SPDX-License-Identifier: AGPL-3.0-only
"""Admission tests for the proposed real-repository M2 corpus."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.validate_real_workload_manifest import (
    InvalidRealWorkloadManifest,
    validate_manifest,
)


class RealWorkloadManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name)
        self.git("init", "-q", "-b", "develop")
        self.git("config", "user.name", "M2 Test")
        self.git("config", "user.email", "m2@example.invalid")
        self.git("remote", "add", "origin", "https://github.com/jayanez/agent-braid.git")
        (self.repository / "base.txt").write_text("base\n")
        self.git("add", "base.txt")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        self.commits = []
        for index in (1, 2):
            self.git("switch", "-qc", f"work-{index}", self.base)
            name = f"work-{index}.txt"
            (self.repository / name).write_text(f"work {index}\n")
            self.git("add", name)
            self.git("commit", "-qm", f"work {index}")
            self.commits.append(self.git("rev-parse", "HEAD"))
        self.git("switch", "-q", "develop")

    def git(self, *args: str) -> str:
        result = subprocess.run(["git", "-C", str(self.repository), *args],
                                capture_output=True, check=True, text=True)
        return result.stdout.strip()

    def manifest(self) -> dict:
        return {
            "version": "0.1.0-draft",
            "repository": "jayanez/agent-braid",
            "baseCommit": self.base,
            "targetRef": "refs/heads/develop",
            "validationProfile": "m2-real-read-only-v1",
            "operations": [
                {
                    "instanceId": f"work-{index}",
                    "sourceCommit": commit,
                    "workstreamUrl": f"https://github.com/jayanez/agent-braid/pull/{index}",
                    "dependencies": [],
                }
                for index, commit in enumerate(self.commits, start=1)
            ],
        }

    def test_binds_distinct_descendant_commits_without_execution(self) -> None:
        before = self.git("status", "--porcelain")
        result = validate_manifest(self.manifest(), self.repository)
        self.assertEqual(result["status"], "preflight-valid")
        self.assertEqual(result["baseCommit"], self.base)
        self.assertFalse(result["executionAuthorization"])
        self.assertFalse(result["projectValidationExecuted"])
        self.assertEqual(self.git("status", "--porcelain"), before)
        self.assertEqual(self.git("rev-parse", "develop"), self.base)

    def test_rejects_stale_base_and_missing_commits(self) -> None:
        manifest = self.manifest()
        (self.repository / "moved.txt").write_text("moved\n")
        self.git("add", "moved.txt")
        self.git("commit", "-qm", "move develop")
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "target branch has moved"):
            validate_manifest(manifest, self.repository)
        self.git("reset", "--hard", self.base)
        manifest["operations"][0]["sourceCommit"] = "f" * 40
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "source commit is unavailable"):
            validate_manifest(manifest, self.repository)

    def test_rejects_unrelated_source_history(self) -> None:
        self.git("switch", "--orphan", "unrelated")
        (self.repository / "unrelated.txt").write_text("unrelated\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "unrelated source")
        unrelated = self.git("rev-parse", "HEAD")
        self.git("switch", "-q", "develop")
        manifest = self.manifest()
        manifest["operations"][0]["sourceCommit"] = unrelated
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "does not descend"):
            validate_manifest(manifest, self.repository)

    def test_rejects_ambiguous_or_authority_bearing_inputs(self) -> None:
        manifest = self.manifest()
        manifest["operations"][1]["sourceCommit"] = self.commits[0]
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "repeated"):
            validate_manifest(manifest, self.repository)
        manifest = self.manifest()
        manifest["operations"][0]["dependencies"] = ["work-2"]
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "independent"):
            validate_manifest(manifest, self.repository)
        manifest = self.manifest()
        manifest["validationProfile"] = "execute-and-push"
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "unsupported"):
            validate_manifest(manifest, self.repository)
        manifest = self.manifest()
        self.git("remote", "set-url", "origin", "https://github.com/other/repository.git")
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "origin"):
            validate_manifest(manifest, self.repository)

    def test_rejects_more_than_three_workstreams(self) -> None:
        manifest = self.manifest()
        manifest["operations"].extend([
            {"instanceId": "work-3", "sourceCommit": "3" * 40,
             "workstreamUrl": "https://github.com/jayanez/agent-braid/pull/3",
             "dependencies": []},
            {"instanceId": "work-4", "sourceCommit": "4" * 40,
             "workstreamUrl": "https://github.com/jayanez/agent-braid/pull/4",
             "dependencies": []},
        ])
        with self.assertRaisesRegex(InvalidRealWorkloadManifest, "two or three"):
            validate_manifest(manifest, self.repository)

    @unittest.skip("SC-045 awaits ADR 0015 acceptance and a registered real corpus")
    def test_candidate_and_serial_project_validation(self) -> None:
        pass

    @unittest.skip("SC-046 awaits ADR 0015 acceptance and the isolated command stage")
    def test_project_validation_fails_closed(self) -> None:
        pass

    @unittest.skip("SC-047 awaits registered real-workload benchmark evidence")
    def test_real_workload_comparison_and_claim(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
