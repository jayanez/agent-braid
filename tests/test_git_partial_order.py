# SPDX-License-Identifier: AGPL-3.0-only
"""Finite partition and real-Git oracle controls for private M2 reduction."""

from copy import deepcopy
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from agent_braid.git_counterexamples import reduce_counterexample
from agent_braid.git_partial_order import (
    _classes_agree,
    _independent_pairs,
    _partition,
    compare,
)
from agent_braid.git_replay import _topological_orders, produce, verify


def _operation(identifier: str, dependencies: tuple[str, ...] = ()) -> dict:
    return {"instanceId": identifier, "dependencies": list(dependencies),
            "uncertainPaths": []}


def _observed(identifier: str, path: str) -> dict:
    return {"instanceId": identifier, "changes": [{"status": "M", "path": path}]}


class PartialOrderRelationTests(unittest.TestCase):
    def test_disjoint_siblings_are_independent(self):
        operations = [_operation("A"), _operation("B", ("A",)),
                      _operation("C", ("A",))]
        observed = [_observed("A", "root.txt"), _observed("B", "b.txt"),
                    _observed("C", "c.txt")]
        partition = _partition(operations, observed, {name: True for name in "ABC"})
        self.assertEqual(partition["independentPairs"], [["B", "C"]])
        self.assertEqual(partition["orderCount"], 2)
        self.assertEqual(partition["replayCount"], 1)
        self.assertEqual(partition["representatives"], [["A", "B", "C"]])

    def test_overlap_prefix_dependency_and_unsupported_pairs_are_not_swapped(self):
        operations = [_operation("A"), _operation("B"),
                      _operation("C", ("B",)), _operation("D")]
        observed = [_observed("A", "dir"), _observed("B", "dir/file.txt"),
                    _observed("C", "elsewhere.txt"), _observed("D", "last.txt")]
        pairs = _independent_pairs(operations, observed,
                                   {"A": True, "B": True, "C": True, "D": False})
        self.assertNotIn(("A", "B"), pairs)
        self.assertNotIn(("B", "C"), pairs)
        self.assertFalse(any("D" in pair for pair in pairs))
        self.assertIn(("A", "C"), pairs)

    def test_partition_is_deterministic_and_covers_every_order(self):
        operations = [_operation(name) for name in "ABCD"]
        observed = [_observed("A", "same.txt"), _observed("B", "same.txt"),
                    _observed("C", "c.txt"), _observed("D", "d.txt")]
        supported = {name: True for name in "ABCD"}
        first = _partition(operations, observed, supported)
        second = _partition(list(reversed(operations)), list(reversed(observed)), supported)
        self.assertEqual(first, second)
        covered = [tuple(order) for component in first["classes"]
                   for order in component["orders"]]
        expected = [tuple(order) for order in _topological_orders(operations)]
        self.assertEqual(sorted(covered), sorted(expected))
        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(first["orderCount"], 24)

    def test_disjoint_and_same_path_replay_counts(self):
        operations = [_operation(name) for name in "ABC"]
        supported = {name: True for name in "ABC"}
        disjoint = _partition(operations, [_observed(name, name + ".txt")
                                         for name in "ABC"], supported)
        same_path = _partition(operations, [_observed(name, "shared.txt")
                                          for name in "ABC"], supported)
        self.assertEqual((disjoint["orderCount"], disjoint["replayCount"]), (6, 1))
        self.assertEqual((same_path["orderCount"], same_path["replayCount"]), (6, 6))

    def test_class_mismatch_is_detected(self):
        operations = [_operation("A"), _operation("B")]
        partition = _partition(operations, [_observed("A", "a.txt"),
                                            _observed("B", "b.txt")],
                               {"A": True, "B": True})
        schedules = [
            {"order": ["A", "B"], "status": "complete", "finalTree": "tree-a"},
            {"order": ["B", "A"], "status": "complete", "finalTree": "tree-b"},
        ]
        self.assertFalse(_classes_agree(partition, schedules))
        schedules[1]["finalTree"] = "tree-a"
        self.assertTrue(_classes_agree(partition, schedules))


class PartialOrderRealGitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name) / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "Partial order test")
        self.git("config", "user.email", "test@example.invalid")
        for path, content in {"a.txt": "base a\n", "b.txt": "base b\n",
                              "c.txt": "base c\n", "other.txt": "base\n",
                              "overlap.txt": "same\n",
                              "repeated.txt": "x\n" * 30}.items():
            (self.repo / path).write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").decode().strip()

    def git(self, *args: str) -> bytes:
        return subprocess.run(["git", "-C", str(self.repo), *args],
                              capture_output=True, check=True).stdout

    def commit(self, branch: str, path: str, content: str) -> str:
        self.git("checkout", "-qb", branch, self.base)
        (self.repo / path).write_text(content, encoding="utf-8")
        self.git("add", "--", path)
        self.git("commit", "-qm", branch)
        revision = self.git("rev-parse", "HEAD").decode().strip()
        self.git("checkout", "-q", "main")
        return revision

    def request(self, revisions: dict[str, str]) -> dict:
        return {
            "gitAnalysisRequestVersion": "0.1.0-alpha",
            "repository": str(self.repo),
            "baseRevision": self.base,
            "operations": [
                {"instanceId": name, "attemptId": "attempt-" + name,
                 "source": {"kind": "commit", "revision": revision},
                 "dependencies": [], "uncertainPaths": []}
                for name, revision in sorted(revisions.items())
            ],
        }

    def test_selected_real_git_replay_matches_exhaustive_evidence(self):
        revisions = {name: self.commit(name, name.lower() + ".txt", name + "\n")
                     for name in "ABC"}
        request = self.request(revisions)
        before = (self.git("status", "--porcelain=v1"), self.git("show-ref"),
                  self.git("cat-file", "--batch-all-objects",
                           "--batch-check=%(objectname)"))
        bundle, plan = produce(request)
        result = compare(request)
        after = (self.git("status", "--porcelain=v1"), self.git("show-ref"),
                 self.git("cat-file", "--batch-all-objects",
                          "--batch-check=%(objectname)"))
        self.assertEqual(before, after)
        self.assertEqual(verify(bundle, str(self.repo))["status"], "verified")
        self.assertEqual(result["status"], "matched")
        self.assertEqual(result["oracleResult"], "equivalent-observed")
        self.assertEqual(result["oracleEvidence"], bundle)
        self.assertEqual((result["partition"]["orderCount"],
                          result["partition"]["replayCount"]), (6, 1))
        self.assertEqual(len(result["representativeSchedules"]), 1)
        self.assertEqual(len(bundle["schedules"]), 6)
        self.assertFalse(plan["executionAuthorization"])
        self.assertFalse(result["executionAuthorization"])

    def test_incomplete_and_tampered_oracle_are_not_positive(self):
        left = self.commit("left", "overlap.txt", "left\n")
        right = self.commit("right", "overlap.txt", "right\n")
        request = self.request({"A": left, "B": right})
        result = compare(request)
        self.assertEqual(result["status"], "oracle-inconclusive")
        self.assertEqual(result["oracleResult"], "inconclusive")
        self.assertEqual(result["partition"]["replayCount"], 2)
        self.assertFalse(result["executionAuthorization"])

        valid, _ = produce(request)
        tampered = deepcopy(valid)
        tampered["operations"][0]["patchDigest"] = "sha256:" + "0" * 64
        with mock.patch("agent_braid.git_partial_order.git_replay._build_evidence",
                        return_value=tampered):
            rejected = compare(request)
        self.assertEqual(rejected["status"], "inconclusive")
        self.assertEqual(rejected["representativeSchedules"], [])
        self.assertFalse(rejected["executionAuthorization"])

    def test_verified_real_git_divergence_reduces_redundant_operation(self):
        repeated = ["x\n"] * 30
        revisions = {}
        for name in "AB":
            changed = list(repeated)
            changed[8] = name + "\n"
            revisions[name] = self.commit(name, "repeated.txt", "".join(changed))
        revisions["C"] = self.commit("C", "other.txt", "changed\n")
        request = self.request(revisions)
        bundle, plan = produce(request)
        self.assertEqual(bundle["result"], "divergent")
        self.assertEqual(len(bundle["schedules"]), 6)
        self.assertTrue(all(item["status"] == "complete" for item in bundle["schedules"]))
        self.assertEqual(verify(bundle, str(self.repo))["status"], "verified")
        self.assertNotEqual(plan["mode"], "candidate-preparation-waves")

        reduced = reduce_counterexample(bundle, str(self.repo))
        self.assertEqual(reduced["status"], "reduced")
        self.assertEqual(reduced["selectedOperationIds"], ["A", "B"])
        self.assertEqual(reduced["witnessEvidence"]["result"], "divergent")
        self.assertEqual(verify(reduced["witnessEvidence"], str(self.repo))["status"], "verified")

        comparison = compare(request)
        self.assertEqual(comparison["status"], "matched")
        self.assertEqual(comparison["oracleResult"], "divergent")
        self.assertEqual((comparison["partition"]["orderCount"],
                          comparison["partition"]["replayCount"]), (6, 2))
        self.assertFalse(comparison["executionAuthorization"])


if __name__ == "__main__":
    unittest.main()
