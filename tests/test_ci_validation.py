# SPDX-License-Identifier: AGPL-3.0-only
"""Execute the CI aggregate's real inline guard and pin its workflow bindings."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

from scripts import validate_change


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
MANDATORY = ("classify", "invariants", "tests", "governance_science", "spec_kit")


def aggregate_code(workflow=WORKFLOW):
    """Read the literal Python heredoc executed by the aggregate, without PyYAML."""
    aggregate = workflow.split("  validate:\n", 1)[1]
    body = aggregate.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
    return "\n".join(line[10:] for line in body.splitlines()) + "\n"


def complete_needs(selected="false", unknown="false", profile="quick"):
    needs = {name: {"result": "success", "outputs": {}} for name in MANDATORY}
    needs["classify"]["outputs"] = {
        "spec_kit_integration": selected,
        "unknown_paths": unknown,
        "effective_profile": profile,
    }
    needs["spec_kit_integration"] = {
        "result": "success" if selected == "true" else "skipped", "outputs": {},
    }
    return needs


def run_guard(needs, cancelled="false", code=None):
    environment = os.environ.copy()
    environment.pop("NEEDS_JSON", None)
    environment.pop("WORKFLOW_CANCELLED", None)
    if needs is not None:
        environment["NEEDS_JSON"] = needs if isinstance(needs, str) else json.dumps(needs)
    if cancelled is not None:
        environment["WORKFLOW_CANCELLED"] = cancelled
    return subprocess.run(
        [sys.executable, "-c", code or aggregate_code()], env=environment,
        text=True, capture_output=True, check=False, timeout=10,
    )


def evaluate_expression(expression, values):
    """Evaluate only this workflow's boolean/context subset, not the runner API.

    actionlint separately validates GitHub syntax. This local context replay does
    not claim to reproduce runner scheduling, status defaults or cancellation.
    """
    expression = expression.strip().removeprefix("${{").removesuffix("}}").strip()
    expression = re.sub(r"\b(?:github|needs)\.[a-zA-Z0-9_.]+",
                        lambda match: f"values[{match.group()!r}]", expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", "not ", expression)
    expression = " ".join(expression.split())
    return eval(expression, {"__builtins__": {}}, {
        "values": values, "success": lambda: values["success"],
        "cancelled": lambda: values["cancelled"], "always": lambda: True,
    })


class CIValidationTests(unittest.TestCase):
    def assert_rejected(self, needs, cancelled="false", message=None):
        result = run_guard(needs, cancelled)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Aggregate validation rejected:", result.stderr)
        if message:
            self.assertIn(message, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_complete_results_accept_only_permitted_specialist_outcomes(self):
        for selected, profile in (("false", "quick"), ("false", "sensitive"),
                                  ("true", "sensitive")):
            for result in ("success", "skipped"):
                with self.subTest(selected=selected, profile=profile, result=result):
                    needs = complete_needs(selected, profile=profile)
                    needs["spec_kit_integration"]["result"] = result
                    self.assertEqual(run_guard(needs).returncode,
                                     1 if selected == "true" and result == "skipped" else 0)

    def test_every_mandatory_job_failure_cancellation_skip_unknown_or_absence_blocks(self):
        for name in MANDATORY:
            for result in ("failure", "cancelled", "skipped", "unknown", "", None):
                with self.subTest(name=name, result=result):
                    needs = complete_needs()
                    needs[name]["result"] = result
                    self.assert_rejected(needs, message=name)
            needs = complete_needs()
            del needs[name]
            self.assert_rejected(needs, message=name)
            needs[name] = []
            self.assert_rejected(needs, message=name)

    def test_specialist_failed_cancelled_missing_or_unknown_blocks_even_when_unselected(self):
        for selected in ("true", "false"):
            for result in ("failure", "cancelled", "unknown", "", None):
                with self.subTest(selected=selected, result=result):
                    needs = complete_needs(selected, profile="sensitive")
                    needs["spec_kit_integration"]["result"] = result
                    self.assert_rejected(needs, message="specialist")
            needs = complete_needs(selected, profile="sensitive")
            del needs["spec_kit_integration"]
            self.assert_rejected(needs, message="specialist")

    def test_global_cancellation_blocks_even_after_all_prerequisites_succeeded(self):
        needs = complete_needs("true", profile="sensitive")
        for cancelled in ("true", "", "False", None):
            with self.subTest(cancelled=cancelled):
                self.assert_rejected(needs, cancelled, "cancellation")

    def test_missing_malformed_or_non_object_prerequisite_json_blocks(self):
        for needs in (None, "{", "null", "[]", "42", '"success"', {}):
            with self.subTest(needs=needs):
                self.assert_rejected(needs)

    def test_missing_extra_or_non_object_classifier_outputs_block(self):
        for value in (None, [], "false", {}):
            needs = complete_needs()
            needs["classify"]["outputs"] = value
            self.assert_rejected(needs, message="fields")
        for field in ("spec_kit_integration", "unknown_paths", "effective_profile"):
            needs = complete_needs()
            del needs["classify"]["outputs"][field]
            self.assert_rejected(needs, message="fields")
        needs = complete_needs()
        needs["classify"]["outputs"]["new_unreviewed_field"] = "false"
        self.assert_rejected(needs, message="fields")

    def test_malformed_classifier_values_block_instead_of_becoming_false(self):
        for field in ("spec_kit_integration", "unknown_paths", "effective_profile"):
            for value in ("", "unknown", "FALSE", "true\n", True, False, None, [], {}):
                with self.subTest(field=field, value=value):
                    needs = complete_needs()
                    needs["classify"]["outputs"][field] = value
                    self.assert_rejected(needs, message="malformed")

    def test_unknown_or_selected_inputs_must_use_sensitive_specialist_validation(self):
        for selected, unknown, profile in (("false", "true", "sensitive"),
                                          ("true", "true", "quick"),
                                          ("true", "false", "quick")):
            with self.subTest(selected=selected, unknown=unknown, profile=profile):
                self.assert_rejected(complete_needs(selected, unknown, profile), message="uncertainty")
        self.assertEqual(run_guard(complete_needs("true", "true", "sensitive")).returncode, 0)

    def test_actual_classifier_unknown_path_runs_specialist_and_errors_emit_no_outputs(self):
        plan = validate_change.build_plan(["unowned/input.bin"], "quick", portable=True)
        outputs = dict(line.split("=", 1) for line in validate_change.render_github(
            validate_change.plan_record(plan, "base", "head")
        ).splitlines())
        needs = complete_needs()
        needs["classify"]["outputs"] = {key: outputs[key] for key in needs["classify"]["outputs"]}
        self.assert_rejected(needs, message="specialist")
        needs["spec_kit_integration"]["result"] = "success"
        self.assertEqual(run_guard(needs).returncode, 0)
        failed = subprocess.run([
            sys.executable, "scripts/validate_change.py", "--base", "nonexistent-ci-base",
            "--head", "HEAD", "--plan-only", "--format", "github",
        ], cwd=ROOT, capture_output=True, text=True, check=False, timeout=10)
        self.assertEqual(failed.returncode, 2)
        self.assertEqual(failed.stdout, "")
        needs["classify"] = {"result": "failure", "outputs": {}}
        self.assert_rejected(needs, message="classify")

    def test_specialist_condition_selects_work_for_unknown_or_malformed_outputs(self):
        condition = WORKFLOW.split("  spec_kit_integration:\n", 1)[1].split("    runs-on:", 1)[0]
        expression = condition[condition.index("${{"):condition.index("}}") + 2]
        for selected, unknown, profile, expected in (
            ("false", "false", "quick", False), ("false", "false", "sensitive", False),
            ("true", "false", "sensitive", True), ("false", "true", "sensitive", True),
            ("", "false", "quick", True), ("false", "", "quick", True),
            ("false", "false", "unknown", True),
        ):
            with self.subTest(selected=selected, unknown=unknown, profile=profile):
                values = {"needs.classify.outputs.spec_kit_integration": selected,
                          "needs.classify.outputs.unknown_paths": unknown,
                          "needs.classify.outputs.effective_profile": profile}
                self.assertEqual(evaluate_expression(expression, values), expected)

    def test_concurrency_supersedes_only_same_pr_and_preserves_each_non_pr_run(self):
        group = re.search(r"^  group: (.+)$", WORKFLOW, re.MULTILINE).group(1)
        cancel = re.search(r"^  cancel-in-progress: (.+)$", WORKFLOW, re.MULTILINE).group(1)

        def replay(event, number, run_id, workflow="Validate repository"):
            values = {"github.workflow": workflow, "github.event_name": event,
                      "github.event.pull_request.number": number, "github.run_id": run_id,
                      "github.sha": f"{run_id:040x}",
                      "github.ref": f"refs/pull/{number}/merge" if event == "pull_request"
                                    else "refs/heads/develop"}
            expanded = re.sub(r"\$\{\{.*?\}\}", lambda match: str(
                evaluate_expression(match.group(), values)), group)
            return expanded, evaluate_expression(cancel, values)

        old_pr = replay("pull_request", 12, 100)
        new_sha = replay("pull_request", 12, 101)
        self.assertEqual(old_pr, new_sha)
        self.assertTrue(old_pr[1])
        self.assertNotEqual(old_pr, replay("pull_request", 13, 102))
        self.assertNotEqual(old_pr, replay("pull_request", 12, 100, "Other validation"))
        for event in ("push", "workflow_dispatch", "release"):
            with self.subTest(event=event):
                first = replay(event, None, 100)
                second = replay(event, None, 101)
                self.assertNotEqual(first[0], second[0])
                self.assertNotEqual(first[0], old_pr[0])
                self.assertFalse(first[1])

    def test_required_workflow_retains_full_pr_and_post_merge_checks_without_path_filter(self):
        triggers = WORKFLOW.split("on:\n", 1)[1].split("concurrency:", 1)[0]
        self.assertIn("  push:\n    branches: [develop, main]\n  pull_request:\n", triggers)
        self.assertNotIn("paths:", triggers)
        self.assertNotIn("paths-ignore:", triggers)
        self.assertNotIn("types:", triggers)
        for name in ("invariants", "tests", "governance_science", "spec_kit"):
            block = WORKFLOW.split(f"  {name}:\n", 1)[1].split("    steps:\n", 1)[0]
            self.assertNotIn("    if:", block)
        aggregate = WORKFLOW.split("  validate:\n", 1)[1]
        self.assertIn("    name: validate\n", aggregate)
        expected_needs = "    needs:\n" + "".join(
            f"      - {name}\n" for name in (*MANDATORY, "spec_kit_integration")
        )
        self.assertIn(expected_needs, aggregate)
        self.assertIn("    if: ${{ always() }}\n", aggregate)
        self.assertIn("        if: ${{ always() }}\n", aggregate)
        self.assertIn("          NEEDS_JSON: ${{ toJSON(needs) }}\n", aggregate)
        self.assertIn("          WORKFLOW_CANCELLED: ${{ steps.cancellation.outcome != 'skipped' }}\n", aggregate)
        self.assertNotIn("${{", aggregate.split("        run: |\n", 1)[1].split("          PY\n", 1)[0])
        self.assertTrue(aggregate.rstrip().endswith("run: exit 1"))

    def test_confirmation_and_final_checkpoint_recheck_cancellation(self):
        aggregate = WORKFLOW.split("  validate:\n", 1)[1]
        entry = aggregate.split("      - name: Reject cancellation before aggregation\n", 1)[1]
        self.assertIn("        id: cancellation\n        if: ${{ cancelled() }}\n        run: exit 1", entry)
        confirmation = aggregate.split("      - name: Confirm aggregate validation\n", 1)[1]
        expression = re.search(r"^        if: (.+)$", confirmation, re.MULTILINE).group(1)
        for success in (True, False):
            for cancelled in (True, False):
                values = {"success": success, "cancelled": cancelled}
                self.assertEqual(evaluate_expression(expression, values), success and not cancelled)
        checkpoint = aggregate.split("      - name: Reject cancellation during aggregation\n", 1)[1]
        self.assertIn("        if: ${{ cancelled() }}\n        run: exit 1", checkpoint)


if __name__ == "__main__":
    unittest.main()
