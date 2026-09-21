# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from jsonschema import Draft202012Validator

from agent_braid.analysis import InvalidAnalysis, analyze
from scripts.run_software_benchmark import run


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/analysis/file-edits.json"


class AnalyzerTests(unittest.TestCase):
    def input(self):
        return json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_complete_disjoint_footprints_are_candidates_not_authorization(self):
        report = analyze(self.input())
        self.assertEqual(report["interactions"][0]["classification"], "independent-candidate")
        self.assertFalse(report["executionAuthorization"])
        self.assertIn("requires-execution-contract-before-parallelism",
                      report["interactions"][0]["constraints"])

    def test_overlap_dependency_partial_and_external_are_conservative(self):
        value = self.input()
        operations = value["operations"]
        operations[1]["effects"]["declared"][0]["resource"] = \
            operations[0]["effects"]["declared"][0]["resource"]
        self.assertEqual(analyze(value)["interactions"][0]["classification"], "conflicting")
        value = self.input()
        value["operations"][1]["dependencies"] = ["edit-readme"]
        self.assertEqual(analyze(value)["interactions"][0]["classification"], "ordered")
        value = self.input()
        value["operations"][0]["effects"]["coverage"]["status"] = "partial"
        self.assertEqual(analyze(value)["interactions"][0]["classification"], "unknown")
        value = self.input()
        value["operations"][0]["effects"]["declared"][0]["kind"] = "emit"
        self.assertEqual(analyze(value)["interactions"][0]["classification"], "unknown")

    def test_deterministic_and_input_order_independent(self):
        first = analyze(self.input())
        reversed_input = self.input()
        reversed_input["operations"].reverse()
        self.assertEqual(first, analyze(reversed_input))

    def test_read_versions_remain_constraints(self):
        value = self.input()
        value["operations"][0]["readVersions"] = {"repo://agent-braid/README.md": 2}
        interaction = analyze(value)["interactions"][0]
        self.assertIn("validate-read-versions-at-use", interaction["constraints"])

    def test_invalid_and_cyclic_batches_are_rejected(self):
        value = self.input()
        value["operations"][0]["effects"]["coverage"]["status"] = "guaranteed"
        with self.assertRaises(InvalidAnalysis):
            analyze(value)
        value = self.input()
        value["operations"][0]["dependencies"] = ["edit-roadmap"]
        value["operations"][1]["dependencies"] = ["edit-readme"]
        with self.assertRaisesRegex(InvalidAnalysis, "cyclic"):
            analyze(value)

    def test_report_schema(self):
        schema = json.loads((ROOT / "schemas/0.1.0-alpha/analysis-report.schema.json").read_text())
        Draft202012Validator(schema).validate(analyze(self.input()))

    def test_cli_json_text_and_rejection(self):
        for extra in ([], ["--format", "text"]):
            result = subprocess.run(
                [sys.executable, "-m", "agent_braid", "analyze", str(EXAMPLE), *extra],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("execution", result.stdout.lower())
        invalid = subprocess.run(
            [sys.executable, "-m", "agent_braid", "analyze", "README.md"],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(invalid.returncode, 2)

    def test_verify_command_preserves_bounded_checker(self):
        valid = ROOT / "examples/contracts/0.2.0-draft/exhaustive.json"
        result = subprocess.run(
            [sys.executable, "-m", "agent_braid", "verify", str(valid)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "verified")

    def test_software_benchmark_has_no_false_safe_classification(self):
        result = run()
        self.assertEqual(result["falseSafeCount"], 0)
        self.assertEqual(result["falseSerializationCount"], 0)
        self.assertEqual(result["classificationCoverage"], 1.0)
        self.assertEqual(result["analysisCost"], {"unit": "pair evaluations", "value": 9})
        self.assertEqual(result["benchmarkVersion"], "software-m1-v2")
        self.assertEqual(result["conditionBoundScenarioCount"], 1)
        conditioned = next(item for item in result["results"] if item["id"] == "SW-005")
        self.assertEqual(conditioned["actual"], "independent-candidate")
        self.assertEqual(conditioned["requiredConstraint"], "validate-read-versions-at-use")
        self.assertEqual(conditioned["conditionEnforcement"], "required-at-use")
        self.assertEqual(len(result["baselineComparisons"]), 5)
        self.assertEqual(result["classificationAgreement"], result["scenarioCount"])


if __name__ == "__main__":
    unittest.main()
