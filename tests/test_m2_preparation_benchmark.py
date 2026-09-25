# SPDX-License-Identifier: AGPL-3.0-only
"""Controls for the bounded M2 Git preparation performance comparison."""

from pathlib import Path
import tempfile
import unittest

from scripts.benchmark_m2_parallel_preparation import (
    cost_breakdown, load_frozen_prototype, path_overlap_waves, summarize, timed_phases,
)


class M2PreparationBenchmarkTests(unittest.TestCase):
    def test_path_baseline_serializes_prefix_conflicts(self):
        operations = [{"instanceId": name, "dependencies": []}
                      for name in ("a", "b", "c")]
        footprints = {
            "a": {"writes": {"shared"}, "reads": set(), "sharedResources": set(),
                  "footprintComplete": True},
            "b": {"writes": {"other"}, "reads": set(), "sharedResources": set(),
                  "footprintComplete": True},
            "c": {"writes": {"shared/child"}, "reads": set(), "sharedResources": set(),
                  "footprintComplete": True},
        }
        self.assertEqual(path_overlap_waves(operations, footprints),
                         [["a", "b"], ["c"]])
        footprints["b"]["reads"] = {"shared"}
        with self.assertRaisesRegex(ValueError, "independent complete"):
            path_overlap_waves(operations, footprints)

    def test_paired_interval_requires_gain_against_both_baselines(self):
        gain = [{"candidate": 80, "serial": 100, "pathOverlap": 100} for _ in range(30)]
        self.assertTrue(summarize(gain)["goalMet"])
        no_path_gain = [{"candidate": 80, "serial": 100, "pathOverlap": 80}
                        for _ in range(30)]
        result = summarize(no_path_gain)
        self.assertFalse(result["goalMet"])
        self.assertTrue(result["comparisons"]["serial"]["meetsTenPercentAndPositiveInterval"])
        self.assertFalse(result["comparisons"]["pathOverlap"]["meetsTenPercentAndPositiveInterval"])

    def test_frozen_module_must_match_reviewed_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / "prototype.py"
            changed.write_text("# changed baseline\n")
            with self.assertRaisesRegex(ValueError, "reviewed module bytes"):
                load_frozen_prototype(changed)

    def test_cost_breakdown_uses_paired_phase_differences(self):
        phases = {
            "candidate": {"patchPreparation": 8_000_000,
                          "fixtureCommitMaterialization": 3_000_000,
                          "treeIntegration": 4_000_000},
            "serial": {"patchPreparation": 12_000_000,
                       "fixtureCommitMaterialization": 3_000_000,
                       "treeIntegration": 4_000_000},
            "pathOverlap": {"patchPreparation": 12_000_000,
                            "fixtureCommitMaterialization": 4_000_000,
                            "treeIntegration": 6_000_000},
        }
        result = cost_breakdown([{"phases": phases}, {"phases": phases}])
        self.assertEqual(result["pairedMedianCandidateMinusBaselineMilliseconds"]["serial"],
                         {"patchPreparation": -4, "fixtureCommitMaterialization": 0,
                          "treeIntegration": 0})

    def test_phase_accounting_rejects_inconsistent_total(self):
        metrics = {"candidate" + suffix: value for suffix, value in (
            ("PreparationWallNanoseconds", 8),
            ("OperationCommitMaterializationWallNanoseconds", 3),
            ("IntegrationWallNanoseconds", 4),
            ("TotalWallNanoseconds", 16),
        )}
        with self.assertRaisesRegex(ValueError, "phase times do not account"):
            timed_phases({"metrics": metrics}, "candidate")


if __name__ == "__main__":
    unittest.main()
