# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T010: append a freeze record for the prompt sets and the scoring rules.

    python -m scripts.spec069_freeze --reason "why the frozen files changed"
    python -m scripts.spec069_freeze --check

Records are append-only and chained (each holds the hash of the previous one), so a change to
a frozen file is visible in review as a new record with a stated reason.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "specs/069-aim-request-authoring/prompts"
FREEZE = PROMPTS / "FREEZE.json"
FROZEN_FILES = [
    "specs/069-aim-request-authoring/prompts/development.json",
    "specs/069-aim-request-authoring/prompts/held-out.json",
    "scripts/spec069_scoring.py",
    "scripts/spec069_fixture_workspace.py",
]


def sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def record_hash(record: dict) -> str:
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reason")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    freeze = json.loads(FREEZE.read_text())
    current = {path: sha256(path) for path in FROZEN_FILES}
    if args.check:
        return 0 if freeze["records"][-1]["files"] == current else 1
    if not args.reason:
        parser.error("--reason is required")
    previous = record_hash(freeze["records"][-1]) if freeze["records"] else None
    freeze["records"].append({"reason": args.reason, "previous": previous, "files": current})
    FREEZE.write_text(json.dumps(freeze, indent=2, sort_keys=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
