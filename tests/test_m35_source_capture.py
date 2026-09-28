# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic source-feasibility capture and admission tests."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from scripts.instrument_m35_flow import audit_capture, capture_synthetic


FIXTURE = Path(__file__).resolve().parents[1] / "examples/m35/m35-synthetic-sessions.json"
FROZEN_CAPTURE = FIXTURE.with_name("m35-synthetic-capture.jsonl")
FROZEN_REPORT = FIXTURE.with_name("m35-synthetic-report.json")


class M35SourceCaptureTests(unittest.TestCase):
    def test_fixture_counts_and_reproduction(self) -> None:
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            capture_synthetic(FIXTURE, first)
            capture_synthetic(FIXTURE, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), FROZEN_CAPTURE.read_bytes())
            report = audit_capture(first)
            self.assertEqual(report, json.loads(FROZEN_REPORT.read_text(encoding="utf-8")))
            self.assertEqual(report["sessionsExamined"], 5)
            self.assertEqual(report["sessionsAdmitted"], 1)
            self.assertEqual(report["pairsExamined"], 5)
            self.assertEqual(report["pairsAdmitted"], 1)
            self.assertEqual(report["realPairsAdmitted"], 0)
            self.assertFalse(report["executionAuthorization"])
            self.assertEqual(report["pairsExcludedByReason"], {
                "invalid-anchor": 1, "invalid-base": 1,
                "missing-provenance": 1, "unsupported-operation": 1,
            })
            with self.assertRaises(FileExistsError):
                capture_synthetic(FIXTURE, first)

    def test_missing_event_is_excluded(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            capture = Path(directory) / "capture.jsonl"
            sessions = json.loads(FIXTURE.read_text(encoding="utf-8"))[:1]
            sessions[0]["events"].pop()
            source.write_text(json.dumps(sessions), encoding="utf-8")
            capture_synthetic(source, capture)
            report = audit_capture(capture)
            self.assertEqual(report["sessionsExcludedByReason"], {"incomplete-session": 1})
            self.assertEqual(report["pairsExamined"], 0)

    def test_duplicate_event_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            capture = Path(directory) / "capture.jsonl"
            sessions = json.loads(FIXTURE.read_text(encoding="utf-8"))[:1]
            sessions[0]["events"][1]["eventId"] = sessions[0]["events"][0]["eventId"]
            source.write_text(json.dumps(sessions), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate event id"):
                capture_synthetic(source, capture)
            self.assertFalse(capture.exists())

    def test_non_synthetic_source_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            capture = Path(directory) / "capture.jsonl"
            sessions = json.loads(FIXTURE.read_text(encoding="utf-8"))[:1]
            sessions[0]["sourceKind"] = "real"
            source.write_text(json.dumps(sessions), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "synthetic sessions only"):
                capture_synthetic(source, capture)
            self.assertFalse(capture.exists())


if __name__ == "__main__":
    unittest.main()
