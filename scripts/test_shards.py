#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Partition tests/test_*.py into deterministic CI shards (standard library only).

Modules are sorted by name and dealt round-robin, so a new test file always lands
in exactly one shard. ``--run`` executes one shard with the import semantics of
``python3 -m unittest discover -s tests -v``: the tests directory is placed first on
``sys.path`` and each module is loaded by its top-level name. Run this module as
``python3 -m scripts.test_shards`` so the repository root, not ``scripts/``, is the
script directory on ``sys.path``.
"""

import argparse
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
DEFAULT_TOTAL = 6


def modules(directory=TESTS):
    """Return the sorted top-level test module names discover would load."""
    return sorted(path.stem for path in Path(directory).glob("test_*.py") if path.is_file())


def shard(names, index, total):
    if total < 1 or not 0 <= index < total:
        raise ValueError(f"shard {index} is outside 0..{total - 1}")
    return sorted(names)[index::total]


def plan(names, total):
    return [shard(names, index, total) for index in range(total)]


def check(names, total):
    """Return partition errors; an empty list means every module is in one shard."""
    errors = []
    if total < 1:
        return [f"total {total} must be at least 1"]
    if not names:
        errors.append("no test modules found")
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        errors.append(f"duplicate modules: {', '.join(duplicates)}")
    invalid = [name for name in names if not name.isidentifier()]
    if invalid:
        errors.append(f"modules are not importable names: {', '.join(invalid)}")
    shards = plan(names, total)
    assigned = [name for group in shards for name in group]
    if sorted(assigned) != sorted(names) or len(set(assigned)) != len(assigned):
        errors.append("shards do not partition the modules exactly once")
    empty = [str(index) for index, group in enumerate(shards) if not group]
    if empty:
        errors.append(f"empty shards would run no tests: {', '.join(empty)}")
    return errors


def run(names, directory):
    """Run the named modules like ``unittest discover -s <directory> -v`` and exit."""
    sys.path.insert(0, str(Path(directory).resolve()))
    unittest.main(module=None, argv=["python3 -m unittest", "-v", *names])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--total", type=int, default=DEFAULT_TOTAL)
    parser.add_argument("--shard", type=int)
    parser.add_argument("--check", action="store_true",
                        help="fail unless every test module is in exactly one non-empty shard")
    parser.add_argument("--run", action="store_true", help="execute the selected shard")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tests-dir", type=Path, default=TESTS)
    arguments = parser.parse_args(argv)
    names = modules(arguments.tests_dir)

    if arguments.check:
        errors = check(names, arguments.total)
        if arguments.json:
            shards = plan(names, arguments.total) if arguments.total >= 1 else []
            print(json.dumps({"total": arguments.total, "modules": len(names),
                              "shards": shards, "errors": errors}, indent=2))
        for error in errors:
            print(f"test shard check failed: {error}", file=sys.stderr)
        if errors:
            return 1
        if not arguments.json:
            print(f"{len(names)} test modules in {arguments.total} shards")
        return 0

    if arguments.shard is None:
        parser.error("--shard is required unless --check is given")
    try:
        selected = shard(names, arguments.shard, arguments.total)
    except ValueError as error:
        parser.error(str(error))
    if arguments.run:
        if not selected:
            print("test shard is empty", file=sys.stderr)
            return 1
        run(selected, arguments.tests_dir)
    if arguments.json:
        print(json.dumps(selected))
    else:
        print("\n".join(selected))
    return 0


if __name__ == "__main__":
    sys.exit(main())
