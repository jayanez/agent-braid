# SPDX-License-Identifier: AGPL-3.0-only
"""The CI test shards partition tests/test_*.py completely, disjointly and stably."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from scripts import test_shards


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")


def cli(*arguments, cwd=ROOT):
    return subprocess.run(
        [sys.executable, "-m", "scripts.test_shards", *arguments], cwd=cwd,
        capture_output=True, text=True, check=False, timeout=60,
    )


class ShardPlanTests(unittest.TestCase):
    def test_repository_shards_are_complete_and_disjoint(self):
        names = test_shards.modules()
        self.assertEqual(names, sorted(path.stem for path in (ROOT / "tests").glob("test_*.py")))
        self.assertIn("test_test_shards", names)
        shards = test_shards.plan(names, test_shards.DEFAULT_TOTAL)
        flattened = [name for shard in shards for name in shard]
        self.assertEqual(len(flattened), len(set(flattened)))
        self.assertEqual(sorted(flattened), names)
        self.assertTrue(all(shards))
        self.assertEqual(test_shards.check(names, test_shards.DEFAULT_TOTAL), [])

    def test_split_is_sorted_round_robin_and_deterministic(self):
        names = [f"test_{letter}" for letter in "gabfcde"]
        shards = test_shards.plan(names, 3)
        self.assertEqual(shards, [["test_a", "test_d", "test_g"], ["test_b", "test_e"],
                                  ["test_c", "test_f"]])
        self.assertEqual(shards, test_shards.plan(list(reversed(names)), 3))
        first = cli("--shard", "2", "--total", "6")
        second = cli("--shard", "2", "--total", "6")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stdout.split(), test_shards.plan(test_shards.modules(), 6)[2])

    def test_new_test_file_is_assigned_to_exactly_one_shard(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for name in ("test_a.py", "test_b.py", "helpers.py", "test_c.txt"):
                (directory / name).write_text("", encoding="utf-8")
            (directory / "fixtures").mkdir()
            (directory / "fixtures" / "test_nested.py").write_text("", encoding="utf-8")
            before = test_shards.modules(directory)
            self.assertEqual(before, ["test_a", "test_b"])
            (directory / "test_new.py").write_text("", encoding="utf-8")
            after = test_shards.modules(directory)
            owners = [index for index, shard in enumerate(test_shards.plan(after, 6))
                      if "test_new" in shard]
            self.assertEqual(len(owners), 1)
            self.assertEqual(test_shards.check(after, 3), [])
            result = cli("--check", "--total", "3", "--tests-dir", str(directory), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["total"], 3)
            self.assertEqual(record["errors"], [])
            self.assertEqual(sorted(name for shard in record["shards"] for name in shard), after)

    def test_check_rejects_invalid_partitions_and_inputs(self):
        self.assertTrue(test_shards.check(["test_a"], 2))  # an empty shard would run nothing
        self.assertTrue(test_shards.check(["test_a", "test_a"], 1))
        self.assertTrue(test_shards.check(["test_bad-name"], 1))
        self.assertTrue(test_shards.check([], 1))
        for index, total in ((6, 6), (-1, 6), (0, 0)):
            with self.subTest(index=index, total=total), self.assertRaises(ValueError):
                test_shards.shard(["test_a"], index, total)
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / "test_only.py").write_text("", encoding="utf-8")
            failed = cli("--check", "--total", "2", "--tests-dir", temporary)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("empty", failed.stderr)
            failed_json = cli("--check", "--total", "2", "--tests-dir", temporary, "--json")
            self.assertEqual(failed_json.returncode, 1)
            self.assertTrue(json.loads(failed_json.stdout)["errors"])
        self.assertEqual(cli("--shard", "6", "--total", "6").returncode, 2)
        self.assertNotEqual(cli("--run").returncode, 0)
        self.assertEqual(cli("--check", "--run", "--shard", "0").returncode, 2)

    def test_run_executes_only_its_shard_with_discover_import_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / "shard_helper.py").write_text("VALUE = 7\n", encoding="utf-8")
            (directory / "test_one.py").write_text(
                "import unittest\nfrom shard_helper import VALUE\n"
                "class T(unittest.TestCase):\n    def test_one(self):\n"
                "        self.assertEqual(VALUE, 7)\n", encoding="utf-8")
            (directory / "test_two.py").write_text(
                "import unittest\nclass T(unittest.TestCase):\n    def test_two(self):\n"
                "        self.fail('shard 1 only')\n", encoding="utf-8")
            passed = cli("--run", "--shard", "0", "--total", "2", "--tests-dir", temporary)
            self.assertEqual(passed.returncode, 0, passed.stderr)
            self.assertIn("test_one", passed.stderr)
            self.assertNotIn("test_two", passed.stderr)
            failed = cli("--run", "--shard", "1", "--total", "2", "--tests-dir", temporary)
            self.assertEqual(failed.returncode, 1)
            self.assertIn("shard 1 only", failed.stderr)


class WorkflowShardTests(unittest.TestCase):
    def test_workflow_matrix_covers_every_shard_of_the_declared_total(self):
        block = WORKFLOW.split("  tests:\n", 1)[1].split("\n  governance_science:\n", 1)[0]
        matrix = re.search(r"^        shard: \[([0-9, ]+)\]$", block, re.MULTILINE)
        self.assertIsNotNone(matrix)
        shards = [int(value) for value in matrix.group(1).split(",")]
        self.assertEqual(shards, list(range(test_shards.DEFAULT_TOTAL)))
        self.assertIn("      fail-fast: false\n", block)
        self.assertIn(f"--total {test_shards.DEFAULT_TOTAL}", block)
        self.assertIn(f"python3 -m scripts.test_shards --check --total {test_shards.DEFAULT_TOTAL}",
                      block)
        self.assertIn("python3 -m scripts.test_shards --run --shard ${{ matrix.shard }} "
                      f"--total {test_shards.DEFAULT_TOTAL}", block)
        self.assertIn('AGENT_BRAID_REQUIRE_BUILD_TESTS: "1"', block)
        self.assertNotIn("unittest discover", block)
        self.assertEqual(1, WORKFLOW.count("python3 -m venv .venv-tooling"))
        self.assertIn("        if: ${{ matrix.shard == 0 }}\n", block)


if __name__ == "__main__":
    unittest.main()
