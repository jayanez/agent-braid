# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.market_sizing import MODEL, load_and_calculate
from scripts.validate_research_radar import validate


ROOT = Path(__file__).resolve().parents[1]


class MarketModelTests(unittest.TestCase):
    def test_model_is_nested_monotonic_and_reproducible(self):
        first = load_and_calculate()
        self.assertEqual(first, load_and_calculate())
        for result in first["results"].values():
            self.assertLessEqual(result["samOrganizationProxy"], result["tamOrganizationProxy"])

    def test_rejects_non_monotonic_and_unitless_inputs(self):
        data = json.loads(MODEL.read_text())
        data["scenarios"]["high"]["agentDevelopingShare"] = 0.01
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "market.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_and_calculate(path)

    def test_rejects_duplicate_observation_ids(self):
        data = json.loads(MODEL.read_text())
        data["observations"].append(dict(data["observations"][0], value=1))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "market.json"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "unique"):
                load_and_calculate(path)
        data = json.loads(MODEL.read_text())
        data["observations"][0]["unit"] = ""
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "market.json"
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_and_calculate(path)


class RadarTests(unittest.TestCase):
    def test_committed_radar_has_milestone_review(self):
        self.assertEqual(validate("M0.5"), [])

    def test_milestone_gate_requires_an_approved_review(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research/radar").mkdir(parents=True)
            (root / "decision.md").write_text("review")
            record = {
                "review": {
                    "date": "2026-09-18", "kind": "milestone",
                    "milestones": ["M1"], "decision": "pending",
                    "decisionRecord": "decision.md",
                },
                "entries": [],
            }
            path = root / "research/radar/review.json"
            path.write_text(json.dumps(record))
            self.assertTrue(any("approved" in item for item in
                                validate("M1", root=root, require_approved=True)))
            record["review"]["decision"] = "approved"
            path.write_text(json.dumps(record))
            self.assertEqual(validate("M1", root=root, require_approved=True), [])

    def test_rejects_missing_provenance_and_bad_claim_level(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research/radar").mkdir(parents=True)
            (root / "decision.md").write_text("review")
            record = {
                "review": {"date": "2026-09-17", "kind": "monthly", "decisionRecord": "decision.md"},
                "entries": [{
                    "id": "RAD-X", "title": "x", "url": "https://example.test",
                    "sourceDate": "2026", "sourceClass": "paper", "provenance": "",
                    "peerReviewed": False, "claimLevel": "proof", "relationship": "x",
                    "affectedArtifacts": ["decision.md"], "status": "watch", "decision": "x"
                }]
            }
            (root / "research/radar/review.json").write_text(json.dumps(record))
            failures = validate(root=root)
            self.assertTrue(any("provenance" in item for item in failures))
            self.assertTrue(any("claim level" in item for item in failures))

    def test_rejects_invalid_provenance_and_peer_review_type(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "research/radar").mkdir(parents=True)
            (root / "decision.md").write_text("review")
            record = {
                "review": {"date": "2026-09-17", "kind": "monthly", "decisionRecord": "decision.md"},
                "entries": [{
                    "id": "RAD-X", "title": "x", "url": "https://example.test",
                    "sourceDate": "2026", "sourceClass": "paper", "provenance": "banana",
                    "peerReviewed": "yes", "claimLevel": "unreproduced-result", "relationship": "x",
                    "affectedArtifacts": ["decision.md"], "status": "watch", "decision": "x"
                }]
            }
            (root / "research/radar/review.json").write_text(json.dumps(record))
            failures = validate(root=root)
            self.assertTrue(any("invalid provenance" in item for item in failures))
            self.assertTrue(any("peerReviewed must be boolean" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
