# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-052 T021: corpus comparison classifies each pair as the pre-stated truth predicts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from scripts import compare_gate_corpus as comparison
from tests import claude_workflow_gate_helpers as fixtures


class CorpusComparisonTests(unittest.TestCase):
    def test_classification_rules(self):
        self.assertEqual(comparison.classify("independent-candidate", "conflicted"), "baseline-stricter")
        self.assertEqual(comparison.classify("conflicting", "clean"), "analyzer-stricter")
        self.assertEqual(comparison.classify("unknown", "clean"), "analyzer-unknown")
        self.assertEqual(comparison.classify("unknown", "unavailable"), "baseline-unavailable")
        self.assertEqual(comparison.classify(None, "clean"), "not-comparable")

    @unittest.skipUnless(fixtures.supports_merge_tree_write_tree(), "needs Git 2.38+")
    def test_corpus_matches_truth_and_store_is_untouched(self):
        with tempfile.TemporaryDirectory() as work:
            evidence = comparison.compare(Path(work))
        self.assertEqual(evidence["truthMismatches"], [])
        self.assertTrue(evidence["repositoryStoreUnchanged"])
        self.assertEqual(evidence["denominators"]["pairs"], len(fixtures.TRUTH))
        self.assertEqual(sum(evidence["denominators"][name] for name in comparison.CLASSES), len(fixtures.TRUTH))
        self.assertEqual(evidence["counterexamples"], "none observed in this corpus")

    @unittest.skipUnless(fixtures.supports_merge_tree_write_tree(), "needs Git 2.38+")
    def test_evidence_is_reproducible_and_machine_independent(self):
        runs = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as work:
                runs.append(comparison.compare(Path(work)))
        self.assertEqual(runs[0], runs[1])
        text = json.dumps(runs[0])
        self.assertNotIn(str(comparison.ROOT), text)
        self.assertNotIn(sys.executable, text)
        self.assertNotIn(tempfile.gettempdir(), text)


if __name__ == "__main__":
    unittest.main()
