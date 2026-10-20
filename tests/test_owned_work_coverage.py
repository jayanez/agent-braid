# SPDX-License-Identifier: AGPL-3.0-only
"""Metadata controls, not real-source admission or decision-accuracy evidence."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest

from research.owned_work_coverage import CoverageError, VERIFIER_SHA256, assess_backlog


def attempt(number=1, paths=None, **changes):
    paths = ["work.txt"] if paths is None else paths
    value = {"taskId": "SPEC-045/T017", "attemptId": f"attempt-{number}",
             "originalPaths": paths, "presentedPaths": list(paths),
             "operationCount": 2, "workflowStatus": "registered"}
    value.update(changes)
    return value


class OwnedWorkCoverageTests(unittest.TestCase):
    def test_prefilter_references_the_unchanged_v1_verifier(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(sha256((root / "agent_braid/system_one_verified_ir.py").read_bytes()).hexdigest(),
                         VERIFIER_SHA256)

    def test_real_paths_are_unsupported_without_rewriting(self):
        for path in ("agent_braid/analysis.py", "README.md", "docs/work.txt"):
            with self.subTest(path=path):
                value = [attempt(paths=[path])]
                before = deepcopy(value)
                result = assess_backlog(value)
                self.assertEqual(result["attempts"][0]["status"], "unsupported")
                self.assertEqual(result["attempts"][0]["reasons"], ["path-outside-v1"])
                self.assertEqual(value, before)

    def test_matching_metadata_is_unknown_never_verified_support(self):
        result = assess_backlog([attempt()])
        self.assertEqual(result["attempts"][0]["status"], "unknown")
        self.assertEqual(result["attempts"][0]["reasons"], ["full-verifier-not-run"])
        self.assertEqual(result["counts"], {"supported": 0, "unsupported": 0,
                                         "refused": 0, "unknown": 1})
        self.assertFalse(result["executionAuthorization"])
        self.assertFalse(result["sourceAdmission"])
        self.assertFalse(result["typedDecisionProduced"])

    def test_laundering_or_dropping_paths_refuses(self):
        for original, presented in ((["source.py"], ["source.txt"]),
                                    (["a.txt", "README.md"], ["a.txt"]),
                                    (["docs/a.txt"], ["a.txt"])):
            with self.subTest(original=original):
                row = assess_backlog([attempt(paths=original, presentedPaths=presented)])["attempts"][0]
                self.assertEqual(row["status"], "refused")
                self.assertIn("source-path-transformed", row["reasons"])

    def test_path_order_does_not_change_classification(self):
        row = assess_backlog([attempt(paths=["a.txt", "b.txt"],
                                      presentedPaths=["b.txt", "a.txt"])])["attempts"][0]
        self.assertEqual(row["status"], "unknown")

    def test_operation_and_file_boundaries(self):
        for count in (0, 1, 5):
            row = assess_backlog([attempt(operationCount=count)])["attempts"][0]
            self.assertEqual(row["reasons"], ["operation-count-outside-v1"])
            self.assertEqual(row["status"], "unsupported")
        for count in (2, 3, 4):
            self.assertEqual(assess_backlog([attempt(operationCount=count)])["attempts"][0]["status"], "unknown")
        row = assess_backlog([attempt(paths=[f"p{i}.txt" for i in range(9)])])["attempts"][0]
        self.assertEqual(row["reasons"], ["file-count-outside-v1"])

    def test_missing_count_stays_unknown(self):
        row = assess_backlog([attempt(operationCount=None)])["attempts"][0]
        self.assertEqual(row["status"], "unknown")
        self.assertEqual(row["reasons"], ["operation-count-unavailable", "full-verifier-not-run"])

    def test_every_retry_and_terminal_state_stays_in_denominator(self):
        states = ("completed", "refused", "cancelled", "error", "missing", "abandoned", "not-selected")
        rows = [attempt(i, paths=["code.py"], workflowStatus=state) for i, state in enumerate(states)]
        result = assess_backlog(rows)
        self.assertEqual(result["totalAttempts"], 7)
        self.assertEqual(result["counts"], {"supported": 0, "unsupported": 7, "refused": 0, "unknown": 0})
        self.assertEqual([r["workflowStatus"] for r in result["attempts"]], list(states))
        self.assertEqual([r["attemptId"] for r in result["attempts"]], [f"attempt-{i}" for i in range(7)])

    def test_empty_population_cannot_be_perfect_coverage(self):
        result = assess_backlog([])
        self.assertEqual(result["totalAttempts"], 0)
        self.assertIsNone(result["supportedFraction"])

    def test_duplicate_attempt_identity_rejects_whole_batch(self):
        with self.assertRaisesRegex(CoverageError, "duplicate-attempt"):
            assess_backlog([attempt(), attempt()])

    def test_invalid_fields_types_and_paths_refuse(self):
        bad = [attempt(operationCount=True), attempt(operationCount=-1),
               attempt(workflowStatus="accepted"), attempt(prompt="private"),
               attempt(paths=["../a.txt"]), attempt(paths=["/a.txt"]),
               attempt(paths=["a\\b.txt"]), attempt(paths=["a\n.txt"]),
               attempt(paths=["a.txt", "a.txt"]), attempt(paths=[])]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(CoverageError):
                assess_backlog([row])

    def test_budgets_and_non_json_objects_refuse(self):
        for rows in ([attempt(i) for i in range(1001)], [attempt(paths=["a" * 513])],
                     [attempt(paths=[f"p{i}.txt" for i in range(257)])], [object()], None):
            with self.assertRaises(CoverageError):
                assess_backlog(rows)

    def test_canonical_input_byte_budget_refuses_without_partial_results(self):
        with self.assertRaisesRegex(CoverageError, "input-budget-exceeded"):
            assess_backlog([attempt(i, paths=["x" * 512]) for i in range(1000)])

    def test_digest_binds_inputs_and_results_do_not_alias(self):
        rows = [attempt()]
        first = assess_backlog(rows)
        self.assertEqual(first, assess_backlog(deepcopy(rows)))
        rows[0]["workflowStatus"] = "cancelled"
        second = assess_backlog(rows)
        self.assertNotEqual(first["inputDigest"], second["inputDigest"])
        self.assertEqual(first["attempts"][0]["workflowStatus"], "registered")
