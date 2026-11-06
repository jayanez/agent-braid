# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T009 / T015 (procedures 009 and 015): alpha.7 replay of recorded requests."""

from __future__ import annotations

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import analysis
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts import spec069_record_alpha7 as recorder

EVIDENCE = json.loads(recorder.OUTPUT.read_text())


def strip_label(report: dict) -> dict:
    """The candidate report as alpha.7 would have produced it: no label, digest recomputed."""
    stripped = copy.deepcopy(report)
    for item in stripped["interactions"]:
        item.pop("completenessBasis", None)
    stripped["analysisId"] = analysis._digest({**stripped, "analysisId": None})
    return stripped


class ReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests = {item["id"]: item["request"] for item in recorder.requests()}

    def setUp(self):
        # A fresh service per test: the owned-evidence inventory is capped at 128 artifacts.
        self.temp = tempfile.TemporaryDirectory()
        source, results = Path(self.temp.name) / "source", Path(self.temp.name) / "results"
        source.mkdir(), results.mkdir()
        self.service = ToolingService(ToolingConfig(source, results))

    def tearDown(self):
        self.temp.cleanup()

    def candidate(self, request):
        return self.service.invoke("analyze-work", {"kind": "aim", "request": request}, threading.Event())

    def problems(self) -> list[str]:
        found = []
        for entry in EVIDENCE["entries"]:
            request = self.requests[entry["id"]]
            envelope = self.candidate(request)
            if entry["status"] == "ok":
                if envelope["status"] != "ok":
                    found.append(f"{entry['id']}: accepted by alpha.7, now {envelope['status']}")
                    continue
                report = strip_label(envelope["result"]["report"])
                sha = recorder.canonical_sha(report)
                if sha != entry["reportSha256"] or report["analysisId"] != entry["analysisId"]:
                    found.append(f"{entry['id']}: report differs from alpha.7 beyond the label")
            elif envelope["status"] == "ok":
                found.append(f"{entry['id']}: refused by alpha.7 ({entry['status']}), now accepted")
        return found

    def test_the_recorded_request_set_is_unchanged(self):
        for entry in EVIDENCE["entries"]:
            self.assertEqual(recorder.canonical_sha(self.requests[entry["id"]]), entry["requestSha256"], entry["id"])

    def test_recorded_counts_cover_examples_workloads_t010_and_the_corpus(self):
        counts = EVIDENCE["counts"]
        self.assertEqual(counts["requests"], counts["accepted"] + counts["notAccepted"])
        ids = {entry["id"] for entry in EVIDENCE["entries"]}
        for expected in ("file:examples/analysis/file-edits.json", "file:examples/analysis/file-edits-conflict.json",
                         "literal:t010-f1-units"):
            self.assertIn(expected, ids)
        self.assertTrue(any(i.startswith("file:examples/workloads/") for i in ids))
        self.assertGreater(counts["accepted"], 50)
        self.assertEqual(EVIDENCE["baseline"]["plugin"], "0.1.0-alpha.7")

    def test_accepted_requests_keep_identical_reports_except_the_label(self):
        self.assertEqual(self.problems(), [])

    def test_the_label_appears_exactly_for_declared_only_independent_candidates(self):
        labelled = unlabelled = 0
        for entry in EVIDENCE["entries"]:
            if entry["status"] != "ok":
                continue
            request = self.requests[entry["id"]]
            records = request["operations"] if isinstance(request, dict) and "operations" in request else (
                request if isinstance(request, list) else [request])
            by_id = {record["instanceId"]: record for record in records}
            report = self.candidate(request)["result"]["report"]
            for item in report["interactions"]:
                declared_only = all(
                    all(isinstance(ev, dict) and ev.get("method") == "declared" for ev in by_id[name]["evidence"]) and by_id[name]["evidence"]
                    for name in (item["left"], item["right"]))
                expected = item["classification"] == "independent-candidate" and declared_only
                with self.subTest(entry["id"], pair=(item["left"], item["right"])):
                    self.assertEqual(item.get("completenessBasis") == "declared-not-observed", expected)
                labelled += bool(item.get("completenessBasis"))
                unlabelled += not item.get("completenessBasis")
        self.assertGreater(labelled, 0)
        self.assertGreater(unlabelled, 0)

    def test_alpha7_refused_requests_are_still_not_accepted(self):
        refused = [e for e in EVIDENCE["entries"] if e["status"] != "ok"]
        self.assertGreater(len(refused), 100)
        self.assertEqual([p for p in self.problems() if "now accepted" in p], [])

    def test_negative_control_a_new_runtime_refusal_is_detected(self):
        original = analysis._validate_record

        def stricter(record, base=""):
            original(record, base)
            if record["effects"]["coverage"]["status"] == "partial":
                raise analysis.InvalidAnalysis("partial refused")

        with patch.object(analysis, "_validate_record", stricter):
            self.assertTrue(any("accepted by alpha.7, now" in p for p in self.problems()))

    def test_negative_control_changed_report_bytes_are_detected(self):
        original = analysis._interaction

        def altered(left, right, ancestors):
            item = original(left, right, ancestors)
            item["reasons"] = item["reasons"] + ["extra"]
            return item

        with patch.object(analysis, "_interaction", altered):
            self.assertTrue(any("differs from alpha.7" in p for p in self.problems()))

    def test_negative_control_a_loosened_validator_is_detected(self):
        with patch.object(analysis, "_nonempty", lambda value, label, pointer=None: value):
            self.assertTrue(any("now accepted" in p for p in self.problems()))

    def test_record_is_current(self):
        self.assertEqual(recorder.render(recorder.record()), recorder.OUTPUT.read_text())


if __name__ == "__main__":
    unittest.main()
