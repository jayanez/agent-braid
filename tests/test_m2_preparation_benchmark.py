# SPDX-License-Identifier: AGPL-3.0-only
"""Controls for the bounded M2 Git preparation performance comparison."""

from pathlib import Path
import tempfile
import unittest

from scripts.benchmark_m2_parallel_preparation import (
    load_frozen_prototype, path_overlap_waves, summarize,
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


if __name__ == "__main__":
    unittest.main()
