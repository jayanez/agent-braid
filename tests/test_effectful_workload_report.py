# SPDX-License-Identifier: AGPL-3.0-only
"""SC-007: negative and inconclusive completion, pending review, packet shape."""
import copy
import json
import unittest
from pathlib import Path

from research.workload_lab.analysis import validate_manifest
from research.workload_lab.evidence import explore, verify

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/024-effectful-workload-lab"
CHECKLIST_TOPICS = (
    "Rights", "Effect completeness", "Atomicity and interleavings", "Version and alias enforcement",
    "Return values", "Failure after effect", "Retries", "Event visibility", "Idempotency semantics")
PACKET = ("report.md", "refinement-checklist.md", "reproduction-record.md")


def fixtures():
    manifest = json.loads((ROOT / "examples/workload-lab/manifest.json").read_text())
    registration = json.loads((ROOT / "examples/workload-lab/registration.json").read_text())
    validate_manifest(manifest, registration)
    return manifest["fixtures"]


class WorkloadReportTests(unittest.TestCase):
    def test_negative_and_inconclusive_completion(self):
        for fixture in fixtures():
            with self.subTest(fixture=fixture["id"]):
                request = copy.deepcopy(fixture["request"])
                request["caps"]["paths"] = 0
                report = explore(request)
                self.assertFalse(report["coverage"]["complete"])
                self.assertEqual(report["comparison"]["verdict"], "inconclusive")
                self.assertIs(report["executionAuthorization"], False)
                replay = verify(report)
                self.assertEqual((replay["status"], replay["verdict"]), ("verified", "inconclusive"))
                self.assertIs(replay["executionAuthorization"], False)
        lost = next(f for f in fixtures() if f["id"] == "lost-update")
        negative = explore(copy.deepcopy(lost["request"]))
        self.assertEqual(negative["comparison"]["verdict"], "divergent")
        self.assertEqual(verify(negative)["status"], "verified")
        evidence = json.loads((SPEC / "evidence/comparison-20261024.json").read_text())
        for field in ("contextualEquivalence", "runtimeSafety"):
            self.assertEqual(evidence[field], "unknown")
        self.assertEqual(evidence["scientificReview"], "pending")
        self.assertIs(evidence["executionAuthorization"], False)
        self.assertEqual(evidence["accounting"]["falseTerminalCandidates"], 0)

    def test_packet_keeps_review_pending_and_covers_the_refinement_topics(self):
        for name in PACKET:
            self.assertTrue((SPEC / name).is_file(), name)
        report = " ".join((SPEC / "report.md").read_text().split())
        for phrase in ("Scientific review: pending", "executionAuthorization: false",
                       "no real refinement or independent validation"):
            self.assertIn(phrase, report)
        checklist = (SPEC / "refinement-checklist.md").read_text()
        for topic in CHECKLIST_TOPICS:
            self.assertIn(f"## {topic}", checklist)
        for name in ("refinement-checklist.md", "reproduction-record.md"):
            text = (SPEC / name).read_text()
            self.assertIn("Scientific review: pending", text)
            self.assertIn("executionAuthorization: false", text)


if __name__ == "__main__":
    unittest.main()
