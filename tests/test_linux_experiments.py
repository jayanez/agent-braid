# SPDX-License-Identifier: AGPL-3.0-only
"""Public-runner boundaries and fail-closed reproduction/record regression checks."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts import reproduce_m35_synthetic as reproduction
from scripts import summarize_public_experiment as summary


ROOT = Path(__file__).resolve().parents[1]
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
PYTHON = "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
EXPERIMENTS = ("m4-reproduction.yml", "m4-alpha-reproduction.yml", "m35-synthetic-reproduction.yml")


def workflow(name):
    return (ROOT / ".github/workflows" / name).read_text(encoding="utf-8")


def entry_guard(name):
    block = workflow(name).split("      - name: Require a public immutable candidate\n", 1)[1]
    body = block.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0]
    return "\n".join(line[10:] for line in body.splitlines()) + "\n"


class LinuxWorkflowTests(unittest.TestCase):
    def test_public_experiments_keep_standard_x64_read_only_identity_and_storage_boundaries(self):
        for name in EXPERIMENTS:
            with self.subTest(workflow=name):
                text = workflow(name)
                self.assertEqual(["ubuntu-24.04"], re.findall(r"^    runs-on: (.+)$", text, re.MULTILINE))
                self.assertEqual([CHECKOUT, PYTHON], re.findall(r"^        uses: (\S+)", text, re.MULTILINE))
                self.assertIn("permissions:\n  contents: read\n", text)
                self.assertIn("          ref: ${{ inputs.candidate_commit }}\n", text)
                self.assertIn("          fetch-depth: 0\n          persist-credentials: false\n", text)
                self.assertIn('          python-version: "3.12"\n', text)
                self.assertIn('          test "$(git rev-parse HEAD)" = "$CANDIDATE_COMMIT"', text)
                self.assertIn('          test -z "$(git status --porcelain)"', text)
                self.assertIn('          test "$(uname -s)" = "Linux"', text)
                self.assertIn('          test "$(uname -m)" = "x86_64"', text)
                for forbidden in ("upload-artifact", "cache:", "actions/cache", "secrets:",
                                  "GH_TOKEN:", "GITHUB_TOKEN:", "self-hosted", "-16core"):
                    self.assertNotIn(forbidden, text)
                self.assertIn("        if: ${{ always() }}\n", text)
                self.assertIn("python3 -m scripts.summarize_public_experiment --record", text)

    def test_real_entry_guards_reject_private_mutable_and_shell_payload_candidates(self):
        for name in EXPERIMENTS:
            for candidate, private, accepted in (("a" * 40, "false", True),
                                                  ("a" * 40, "true", False),
                                                  ("a" * 40, "", False),
                                                  ("develop", "false", False),
                                                  ("a" * 39, "false", False),
                                                  ("A" * 40, "false", False),
                                                  ("$(exit 0)", "false", False)):
                with self.subTest(workflow=name, candidate=candidate, private=private):
                    environment = os.environ.copy()
                    environment.update(CANDIDATE_COMMIT=candidate, REPOSITORY_PRIVATE=private,
                                       BASELINE_COMMIT="", PROFILE_COST="false")
                    result = subprocess.run(["bash", "-eu", "-c", entry_guard(name)],
                                            env=environment, capture_output=True, timeout=5)
                    self.assertEqual(result.returncode == 0, accepted, result.stderr)

    def test_baseline_comparison_requires_immutable_source_and_opted_in_cost_capture(self):
        for baseline, profile, accepted in (("", "false", True), ("b" * 40, "true", True),
                                            ("b" * 40, "false", False), ("develop", "true", False)):
            with self.subTest(baseline=baseline, profile=profile):
                environment = os.environ.copy()
                environment.update(CANDIDATE_COMMIT="a" * 40, REPOSITORY_PRIVATE="false",
                                   BASELINE_COMMIT=baseline, PROFILE_COST=profile)
                result = subprocess.run(["bash", "-eu", "-c", entry_guard("m4-alpha-reproduction.yml")],
                                        env=environment, capture_output=True, timeout=5)
                self.assertEqual(result.returncode == 0, accepted, result.stderr)
        alpha = workflow("m4-alpha-reproduction.yml")
        self.assertIn('git clone --no-local --no-checkout -- . "$RUNNER_TEMP/m4-baseline"', alpha)
        self.assertIn('test "$(git -C "$RUNNER_TEMP/m4-baseline" rev-parse HEAD)" = "$BASELINE_COMMIT"', alpha)
        self.assertIn('test -z "$(git -C "$RUNNER_TEMP/m4-baseline" status --porcelain)"', alpha)
        self.assertIn('--checkout "$RUNNER_TEMP/m4-baseline"', alpha)
        self.assertIn('--compare "$RUNNER_TEMP/m4-alpha-evidence/baseline-cost-profile.json"', alpha)

    def test_existing_alpha_workflow_calls_same_commit_synthetic_job_without_secrets(self):
        alpha = workflow("m4-alpha-reproduction.yml")
        call = alpha.split("  m35_synthetic:\n", 1)[1]
        self.assertIn("    uses: ./.github/workflows/m35-synthetic-reproduction.yml\n", call)
        self.assertIn("      candidate_commit: ${{ inputs.candidate_commit }}\n", call)
        self.assertNotIn("secrets:", call)
        synthetic = workflow("m35-synthetic-reproduction.yml")
        self.assertIn("  workflow_dispatch:\n", synthetic)
        self.assertIn("  workflow_call:\n", synthetic)
        self.assertEqual(2, synthetic.count("      candidate_commit:\n"))
        self.assertIn("      profile_cost:\n", alpha)
        self.assertIn("        default: false\n        type: boolean\n", alpha)
        self.assertIn("        if: ${{ inputs.profile_cost }}\n", alpha)
        self.assertIn("python3 scripts/profile_m4_alpha.py --output", alpha)

    def test_validation_and_tracking_modernization_preserve_required_gate_and_events(self):
        validation = workflow("validate.yml")
        self.assertEqual(["ubuntu-24.04"] * 7,
                         re.findall(r"^    runs-on: (.+)$", validation, re.MULTILINE))
        self.assertEqual([CHECKOUT] * 6,
                         re.findall(r"^        uses: (actions/checkout@\S+)", validation, re.MULTILINE))
        self.assertEqual(6, validation.count("          persist-credentials: false\n"))
        self.assertIn("  push:\n    branches: [develop, main]\n  pull_request:\n", validation)
        tracking = workflow("audit-spec-tracking.yml")
        self.assertIn("  contents: read\n  issues: read\n", tracking)
        self.assertIn("  pull_request:\n    paths:\n", tracking)
        self.assertIn("  push:\n    branches: [develop]\n    paths:\n", tracking)
        self.assertIn('    - cron: "17 8 * * 1"', tracking)
        self.assertIn("  workflow_dispatch:\n", tracking)
        self.assertIn("if: github.event_name != 'pull_request'", tracking)
        self.assertIn(CHECKOUT, tracking)


class SyntheticReproductionTests(unittest.TestCase):
    def _run(self, output, raw=b"Ran 44 tests in 1.0s\n\nOK\n", code=0,
             dirty="", dirty_after=False, changed=False, head_changed=False, timeout=False):
        calls = {"head": 0, "status": 0}
        def git(*args):
            if args == ("rev-parse", "HEAD"):
                calls["head"] += 1
                return "b" * 40 if head_changed and calls["head"] > 1 else "a" * 40
            if args == ("status", "--porcelain"):
                calls["status"] += 1
                return dirty if calls["status"] == 1 else ("?? changed.py" if dirty_after else "")
            if args == ("--version",):
                return "git version test"
            self.fail(f"unexpected Git call: {args}")
        process = subprocess.CompletedProcess([], code, stdout=raw)
        inventories = [{"fixture": "a" * 64}, {"fixture": ("b" if changed else "a") * 64}]
        with patch.object(reproduction, "_git", side_effect=git), \
                patch.object(reproduction, "inventory", side_effect=inventories), \
                patch.object(reproduction.subprocess, "run", return_value=process) as runner, \
                redirect_stdout(StringIO()):
            if timeout:
                runner.side_effect = subprocess.TimeoutExpired(["python"], 600, output=raw)
            status = reproduction.run(output)
        return status, json.loads(output.read_text(encoding="utf-8"))

    def test_success_records_public_fixture_zero_real_yield_and_bound_raw_output(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            code, record = self._run(path)
            self.assertEqual(0, code)
            self.assertEqual("passed", record["status"])
            self.assertEqual(44, record["tests"])
            self.assertEqual(hashlib.sha256(path.with_suffix(".txt").read_bytes()).hexdigest(), record["logSha256"])
            self.assertEqual(0, record["realPairsAdmitted"])
            self.assertFalse(record["executionAuthorization"])
            self.assertEqual(0, record["capture"]["report"]["realPairsAdmitted"])
            self.assertEqual(6, record["capture"]["report"]["pairsExamined"])
            self.assertEqual(1, record["capture"]["report"]["pairsAdmitted"])
            self.assertEqual([1, 2, 3], [row["repetition"] for row in record["capture"]["samples"]])
            self.assertEqual([], list(path.parent.glob("m35-synthetic-*")))
            self.assertFalse(record["candidateInputsChangedDuringRun"])

    def test_dirty_internal_symlink_and_existing_output_reject_without_test_execution(self):
        with TemporaryDirectory() as temporary:
            outside = Path(temporary)
            with patch.object(reproduction, "_git", return_value=" M tracked.py"), \
                    patch.object(reproduction.subprocess, "run") as runner:
                with self.assertRaisesRegex(ValueError, "clean frozen candidate"):
                    reproduction.run(outside / "dirty.json")
                runner.assert_not_called()
            link = outside / "checkout-link"
            link.symlink_to(ROOT, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "outside the candidate checkout"):
                reproduction.run(link / "record.json")
            path = outside / "existing.json"
            path.write_bytes(b"retained")
            with self.assertRaises(FileExistsError):
                reproduction.run(path)
            self.assertEqual(b"retained", path.read_bytes())

    def test_missing_zero_and_skipped_suite_cannot_look_passed(self):
        for raw in (b"OK\n", b"Ran 0 tests in 0.0s\n\nOK\n",
                    b"test_case ... skipped 'unavailable'\nRan 44 tests in 1.0s\nOK (skipped=1)\n",
                    b"test_case ... expected failure\nRan 44 tests in 1.0s\nOK (expected failures=1)\n"):
            with self.subTest(raw=raw), TemporaryDirectory() as temporary:
                code, record = self._run(Path(temporary) / "record.json", raw=raw)
                self.assertEqual(2, code)
                self.assertEqual("incomplete", record["status"])

    def test_failed_or_timed_out_suite_preserves_failure_and_raw_log(self):
        for code, timed_out in ((1, False), (0, True)):
            with self.subTest(code=code, timed_out=timed_out), TemporaryDirectory() as temporary:
                path = Path(temporary) / "record.json"
                status, record = self._run(path, raw=b"partial output", code=code, timeout=timed_out)
                self.assertEqual(124 if timed_out else 1, status)
                self.assertEqual("failed", record["status"])
                self.assertEqual(timed_out, record["timedOut"])
                self.assertEqual(b"partial output", path.with_suffix(".txt").read_bytes())

    def test_changed_input_or_head_invalidates_successful_suite(self):
        for changed, head_changed, dirty_after in ((True, False, False), (False, True, False), (False, False, True)):
            with self.subTest(changed=changed, head_changed=head_changed, dirty_after=dirty_after), TemporaryDirectory() as temporary:
                code, record = self._run(Path(temporary) / "record.json", changed=changed,
                                         head_changed=head_changed, dirty_after=dirty_after)
                self.assertEqual(2, code)
                self.assertEqual("invalidated", record["status"])
                self.assertEqual(changed, record["candidateInputsChangedDuringRun"])
                self.assertEqual(head_changed, record["candidateHeadChangedDuringRun"])
                self.assertEqual(dirty_after, record["candidateWorkingTreeChangedDuringRun"])

    def test_changed_capture_is_failed_even_with_successful_suite(self):
        original = reproduction.capture_synthetic
        def changed_capture(fixture, output):
            result = original(fixture, output)
            output.write_bytes(output.read_bytes() + b"{}\n")
            return result
        with TemporaryDirectory() as temporary, patch.object(reproduction, "capture_synthetic", side_effect=changed_capture):
            code, record = self._run(Path(temporary) / "record.json")
            self.assertEqual(1, code)
            self.assertEqual("failed", record["status"])
            self.assertIsNotNone(record["captureError"])


class PublicSummaryTests(unittest.TestCase):
    def _record(self, directory, **changes):
        path = Path(directory) / "record.json"
        record = {"candidateCommit": "a" * 40, "status": "passed", "tests": 44,
                  "environment": {"machine": "x86_64", "platform": "Linux"},
                  "realPairsAdmitted": 0, "executionAuthorization": False,
                  "limits": ["public synthetic only"]}
        record.update(changes)
        path.write_text(json.dumps(record) + "\n", encoding="utf-8")
        return path

    def test_records_zero_and_false_values_with_hashes_and_disables_log_commands(self):
        with TemporaryDirectory() as temporary:
            raw_log = b"::error::public fixture text\nRan 44 tests in 1.0s\nOK\n"
            path = self._record(temporary, logSha256=hashlib.sha256(raw_log).hexdigest())
            path.with_suffix(".txt").write_bytes(raw_log)
            summary_path = Path(temporary) / "summary.md"
            output = StringIO()
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=True), redirect_stdout(output):
                self.assertEqual(0, summary.publish(path))
            printed = output.getvalue()
            stop = re.match(r"::stop-commands::([0-9a-f]{32})\n", printed)
            self.assertIsNotNone(stop)
            self.assertTrue(printed.endswith(f"::{stop.group(1)}::\n"))
            self.assertIn(raw_log.decode(), printed)
            text = summary_path.read_text(encoding="utf-8")
            self.assertIn("| realPairsAdmitted | 0 |", text)
            self.assertIn("| executionAuthorization | False |", text)
            self.assertIn(hashlib.sha256(path.read_bytes()).hexdigest(), text)
            self.assertIn("does not approve a real M3.5 capture or close M4", text)

    def test_missing_or_changed_bound_log_fails_before_printing_success_or_writing_summary(self):
        for changed in (False, True):
            with self.subTest(changed=changed), TemporaryDirectory() as temporary:
                path = self._record(temporary, logSha256=hashlib.sha256(b"original").hexdigest())
                if changed:
                    path.with_suffix(".txt").write_bytes(b"modified")
                summary_path = Path(temporary) / "summary.md"
                output = StringIO()
                with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=True), redirect_stdout(output):
                    with self.assertRaises(ValueError):
                        summary.publish(path)
                self.assertEqual("", output.getvalue())
                self.assertFalse(summary_path.exists())

    def test_malformed_identity_status_and_non_object_records_fail_closed(self):
        for changes in ({"candidateCommit": "develop"}, {"candidateCommit": 123}, {"status": None}, {"status": "green"}):
            with self.subTest(changes=changes), TemporaryDirectory() as temporary:
                path = self._record(temporary, **changes)
                with self.assertRaises(ValueError):
                    summary.publish(path)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "record.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(ValueError):
                summary.publish(path)

    def test_descriptive_comparison_preserves_negative_observations(self):
        with TemporaryDirectory() as temporary:
            path = self._record(temporary, status="descriptive-comparison", baselineCommit="b" * 40,
                                candidateParallelImprovedObserved=False,
                                candidateSerialNotRegressedObserved=False)
            summary_path = Path(temporary) / "summary.md"
            with patch.dict(os.environ, {"GITHUB_STEP_SUMMARY": str(summary_path)}, clear=True), redirect_stdout(StringIO()):
                self.assertEqual(0, summary.publish(path))
            text = summary_path.read_text(encoding="utf-8")
            self.assertIn("| Status | descriptive-comparison |", text)
            self.assertIn("| candidateParallelImprovedObserved | False |", text)
            self.assertIn("| candidateSerialNotRegressedObserved | False |", text)


if __name__ == "__main__":
    unittest.main()
