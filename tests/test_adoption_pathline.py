# SPDX-License-Identifier: AGPL-3.0-only

import json
from pathlib import Path
import tempfile
import unittest

from scripts.validate_adoption_tracks import validate


ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "research/adoption/2026-09-initial-triage.json"


def _write_registry(root: Path, records: list[dict]) -> None:
    (root / "research/adoption").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "docs/strategy").mkdir()
    (root / "docs/strategy/ECOSYSTEM.md").write_text("# ecosystem")
    for record in records:
        for artifact in record["affectedArtifacts"]:
            path = root / artifact
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture")
    (root / "research/adoption/records.json").write_text(json.dumps(records))


class AdoptionPathlineTests(unittest.TestCase):
    def _records(self) -> list[dict]:
        return json.loads(SEED.read_text())

    def test_seeded_registry_is_valid_and_has_no_adoption(self):
        self.assertEqual(validate(ROOT), [])
        records = self._records()
        self.assertTrue(all(record["decision"] != "adopted" for record in records))

    def test_rejects_missing_differentiation_metric(self):
        records = self._records()
        records[0]["capabilityDelta"].pop("observableMetric")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            failures = validate(root)
            self.assertTrue(any("observableMetric" in failure for failure in failures))

    def test_rejects_missing_owner_or_next_decision(self):
        records = self._records()
        records[0].pop("owner")
        records[1].pop("nextDecision")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            failures = validate(root)
            self.assertTrue(any("owner" in failure for failure in failures))
            self.assertTrue(any("nextDecision" in failure for failure in failures))

    def test_rejects_unknown_committed_radar_id(self):
        records = self._records()
        records[0]["sourceRadarIds"] = ["RAD-2026-999"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            (root / "research/radar").mkdir(parents=True)
            (root / "research/radar/current.json").write_text(
                json.dumps({"entries": [{"id": "RAD-2026-001"}]})
            )
            failures = validate(root)
            self.assertTrue(any("unknown sourceRadarIds" in failure for failure in failures))

    def test_rejects_schema_shape_drift(self):
        records = self._records()
        records[0]["sources"] = []
        records[1]["sourceRadarIds"] = ["RAD-2026-009", "RAD-2026-009"]
        records[2]["unexpected"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            failures = validate(root)
            self.assertTrue(any("sources must be a non-empty list" in failure for failure in failures))
            self.assertTrue(any("sourceRadarIds must be unique" in failure for failure in failures))
            self.assertTrue(any("unknown fields" in failure for failure in failures))

    def test_rejects_backward_stage_history(self):
        records = self._records()
        records[0]["stageHistory"].append({
            "stage": "observed", "date": "2026-09-24", "actor": "test", "record": "test"
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            self.assertTrue(any("moves backwards" in failure for failure in validate(root)))

    def test_rejects_adopted_track_without_feature_reference(self):
        records = self._records()
        records[0]["stage"] = "decision"
        records[0]["decision"] = "adopted"
        records[0]["decisionRationale"] = "test"
        records[0]["stageHistory"].append({
            "stage": "decision", "date": "2026-09-24", "actor": "test", "record": "test"
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            self.assertTrue(any("featureRef" in failure for failure in validate(root)))

    def test_negative_or_inconclusive_research_is_a_valid_terminal_decision(self):
        records = self._records()
        records[0]["stage"] = "decision"
        records[0]["decision"] = "research-only"
        records[0]["decisionRationale"] = "The bounded spike was inconclusive."
        records[0]["stageHistory"].append({
            "stage": "decision", "date": "2026-09-24", "actor": "test", "record": "test"
        })
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            _write_registry(root, records)
            self.assertEqual(validate(root), [])


if __name__ == "__main__":
    unittest.main()
