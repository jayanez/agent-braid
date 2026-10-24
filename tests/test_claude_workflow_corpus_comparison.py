# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-052 T021: corpus comparison classifies each pair as the pre-stated truth predicts."""
import dataclasses
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
        self.assertEqual(comparison.classify("independent-candidate", "clean"), "both-clean")
        self.assertEqual(comparison.classify("conflicting", "conflicted"), "both-conflicting")
        self.assertEqual(comparison.classify("something-else", "clean"), "not-comparable")

    def test_counterexamples_are_independent_candidates_against_a_conflicted_baseline(self):
        def row(name, analyzer, baseline):
            return {"case": name, "left": {"commit": "l"}, "right": {"commit": "r"},
                    "analyzer": {"classification": analyzer}, "baseline": {"result": baseline}}
        rows = [row("hit", "independent-candidate", "conflicted"),
                row("agree", "independent-candidate", "clean"),
                row("stricter", "conflicting", "clean"),
                row("unknown", "unknown", "conflicted")]
        self.assertEqual(comparison.find_counterexamples(rows, "base"),
                         [{"case": "hit", "left": "l", "right": "r", "base": "base"}])
        self.assertEqual(comparison.find_counterexamples(rows[1:], "base"), [])

    def test_scrub_replaces_machine_specific_paths(self):
        with tempfile.TemporaryDirectory() as work:
            text = f"{work}/x {comparison.ROOT}/y {sys.executable}"
            self.assertEqual(comparison.scrub(text, Path(work)), "<work>/x <repo>/y python")

    @unittest.skipUnless(fixtures.supports_merge_tree_write_tree(), "needs Git 2.38+")
    def test_baseline_failure_maps_to_unavailable(self):
        with tempfile.TemporaryDirectory() as work:
            corpus = fixtures.build_corpus(Path(work))
            case = corpus.cases[0]
            bogus = dataclasses.replace(corpus, shas={**corpus.shas, case.left: "0" * 40})
            with tempfile.TemporaryDirectory(dir=work) as objects:
                _, result = comparison.run_baseline(bogus, case, Path(objects))
        self.assertEqual(result, "unavailable")

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
