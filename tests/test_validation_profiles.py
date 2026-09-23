# SPDX-License-Identifier: AGPL-3.0-only
"""Tests for conservative, proportional validation planning."""

import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.capture_feature_evidence import redact_machine_paths
from scripts import validate_change as validation


ROOT = Path(__file__).resolve().parents[1]


class ValidationProfileTests(unittest.TestCase):
    def test_classification_is_deterministic_and_unknown_paths_fail_closed(self):
        first = validation.classify(["README.md", "new-area/input.bin", "README.md"])
        second = validation.classify(["new-area/input.bin", "README.md"])
        self.assertEqual(first, second)
        self.assertEqual(first.paths, ("README.md", "new-area/input.bin"))
        self.assertEqual(first.unknown_paths, ("new-area/input.bin",))
        self.assertTrue(first.sensitive)
        self.assertTrue(first.spec_kit_integration)
        plan = validation.build_plan(first.paths, "quick")
        self.assertEqual(plan.effective_profile, "sensitive")
        self.assertIn("full-tests", plan.commands)
        self.assertIn("spec-kit-integration", plan.commands)

    def test_quick_profile_runs_only_invariants_and_affected_domains(self):
        editorial = validation.build_plan(["README.md"], "quick")
        self.assertEqual(editorial.effective_profile, "quick")
        self.assertEqual(editorial.commands, validation.BASE_COMMANDS)
        self.assertNotIn("full-tests", editorial.commands)
        self.assertNotIn("spec-kit-integration", editorial.commands)

        runtime = validation.build_plan(["agent_braid/analysis.py"], "quick")
        self.assertIn("contracts", runtime.commands)
        self.assertIn("analysis-tests", runtime.commands)
        self.assertNotIn("git-adapter-tests", runtime.commands)
        self.assertNotIn("spec-kit-integration", runtime.commands)

        issue_template = validation.build_plan([".github/ISSUE_TEMPLATE/bug.yml"], "quick")
        self.assertEqual(issue_template.effective_profile, "quick")
        self.assertNotIn("spec-kit-integration", issue_template.commands)

        failed = subprocess.CompletedProcess(["ignored"], 7)
        with patch("scripts.validate_change.subprocess.run", return_value=failed) as run:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(validation.execute(editorial, "develop", None), 7)
            self.assertEqual(run.call_count, 1)

    def test_pr_profile_retains_complete_repository_gate(self):
        plan = validation.build_plan(["README.md"], "pr")
        required = {
            "repository", "contracts", "release-records", "publication",
            "m0-closure", "m1-closure", "m05-closure", "research-radar",
            "adoption-tracks", "market-model", "cli-smoke", "full-tests",
            "scientific-controls", "spec-kit-structure", "spec-kit-render",
            "constitution-replica", "whitespace",
        }
        self.assertEqual(set(plan.commands), required)
        self.assertNotIn("spec-kit-integration", plan.commands)
        for forbidden in ("capture", "freeze", "approve", "clean-room"):
            self.assertFalse(any(forbidden in command for command in plan.commands))

        portable = validation.build_plan(["README.md"], "pr", portable=True)
        for private_closure in ("m0-closure", "m1-closure", "m05-closure"):
            self.assertNotIn(private_closure, portable.commands)
        self.assertIn("publication", portable.commands)

    def test_specialist_matrix_is_limited_to_owned_inputs(self):
        for path in (
            ".specify/templates/overrides/guardrails.md",
            ".agents/skills/speckit-plan/SKILL.md",
            ".claude/skills/speckit-plan/SKILL.md",
            "scripts/spec_kit.py",
            "requirements-speckit.txt",
        ):
            with self.subTest(path=path):
                plan = validation.build_plan([path], "quick")
                self.assertEqual(plan.effective_profile, "sensitive")
                self.assertIn("spec-kit-integration", plan.commands)

        for path in ("CONSTITUTION.md", "research/lab/model.py", "schemas/example.json"):
            with self.subTest(path=path):
                plan = validation.build_plan([path], "quick")
                self.assertEqual(plan.effective_profile, "sensitive")
                self.assertNotIn("spec-kit-integration", plan.commands)

    def test_evidence_boundaries_are_deferred_and_non_authorizing(self):
        plan = validation.build_plan([
            "docs/releases/example.md", "specs/010-risk-validation/assurance.json",
            "research/lab/model.py",
        ], "quick")
        self.assertTrue(plan.impact.boundaries)
        record = validation.plan_record(plan, "develop", None)
        rendered = validation.render_text(record)
        self.assertIn("not executed", rendered)
        self.assertIn("not evidence capture", rendered)
        self.assertNotIn("independently validated", rendered)
        command_text = " ".join(
            argument for item in record["commands"] for argument in item["argv"]
        )
        self.assertNotIn("run_m0_clean_room", command_text)
        self.assertNotIn("run_m1_clean_room", command_text)
        self.assertNotIn("run_public_preview_clean_room", command_text)

    def test_ci_parallelizes_complete_gates_and_conditions_only_specialists(self):
        workflow = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
        for job in ("classify:", "invariants:", "tests:", "governance_science:",
                    "spec_kit:", "spec_kit_integration:", "validate:"):
            self.assertIn(job, workflow)
        self.assertIn("python3 -m unittest discover -s tests -v", workflow)
        self.assertIn("needs.classify.outputs.spec_kit_integration == 'true'", workflow)
        self.assertIn("scripts/test_spec_kit_integration.py", workflow)
        integration = workflow.index("spec_kit_integration:")
        condition = workflow.index("needs.classify.outputs.spec_kit_integration == 'true'")
        self.assertGreater(condition, integration)
        self.assertIn("needs.spec_kit_integration.result != 'success'", workflow)
        self.assertIn("name: validate", workflow)

    def test_explicit_paths_bypass_git_and_github_output_is_stable(self):
        plan = validation.build_plan(["README.md"], "quick")
        record = validation.plan_record(plan, "develop", "a" * 40)
        self.assertNotIn(str(ROOT), str(record))
        self.assertEqual(validation.render_github(record).splitlines(), [
            "effective_profile=quick",
            "sensitive=false",
            "spec_kit_integration=false",
            "unknown_paths=false",
            "changed=true",
        ])

    def test_changed_paths_include_untracked_files_only_for_working_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            (root / "README.md").write_text("initial\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
            base = validation.git_output(["rev-parse", "HEAD"], root).strip()
            (root / "README.md").write_text("changed\n", encoding="utf-8")
            (root / "new.md").write_text("new\n", encoding="utf-8")
            self.assertEqual(validation.changed_paths(base, root=root), ("README.md", "new.md"))
            self.assertEqual(validation.changed_paths(base, base, root), ())

    def test_invalid_explicit_paths_are_rejected(self):
        for path in ("", ".", "../outside", "/absolute"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validation.classify([path])

    def test_git_revisions_resolve_to_immutable_commits(self):
        resolved = validation.resolve_commit("HEAD")
        self.assertEqual(len(resolved), 40)
        with self.assertRaises(ValueError):
            validation.resolve_commit("--output=/tmp/not-a-revision")

    def test_evidence_output_redacts_the_local_repository_path(self):
        value = f"command ran in {ROOT}/scripts"
        redacted = redact_machine_paths(value)
        self.assertNotIn(str(ROOT), redacted)
        self.assertIn("<repository>/scripts", redacted)


if __name__ == "__main__":
    unittest.main()
