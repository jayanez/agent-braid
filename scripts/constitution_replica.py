#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit byte-only replication; never grants amendment approval."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sync(root: Path, generate: bool = False) -> None:
    source = (root / "CONSTITUTION.md").read_bytes()
    target = root / ".specify/memory/constitution.md"
    if generate:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source)
    elif not target.is_file() or target.read_bytes() != source:
        raise ValueError("Constitution replica missing or divergent; check does not repair it")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("generate", "check"))
    args = parser.parse_args()
    sync(ROOT, args.mode == "generate")
    print("Constitution replica: " + args.mode + " passed (not an approval).")
