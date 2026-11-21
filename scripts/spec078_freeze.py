# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T005 (REQ-007): freeze the protocol, the three v2 splits, the Gate 0 script and the A0 skill.

Writes ``prompts/FREEZE.json`` (sha256 of every bound file at the current commit) and ``prompts/fingerprints.json``
(hashed ids and 8-word windows of the validation and test splits, for the optimizer contamination scan). It
refuses unless the tree is clean, the current commit is on ``origin/develop`` and Gate 0 passes on these bytes.

    python -m scripts.spec078_freeze           # write the freeze on a develop commit
    python -m scripts.spec078_freeze --check   # exit 1 unless the committed freeze matches the files
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from agent_braid import lightning_heldout_v2 as v2

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def _render(value: dict) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def write() -> int:
    if _git("status", "--porcelain"):
        print("refused: the freeze needs a clean tree", file=sys.stderr)
        return 1
    commit = _git("rev-parse", "HEAD")
    develop = _git("rev-parse", "origin/develop")
    if subprocess.run(["git", "-C", str(ROOT), "merge-base", "--is-ancestor", commit, develop]).returncode:
        print("refused: the freeze is made on a commit that is on origin/develop", file=sys.stderr)
        return 1
    from scripts import spec078_gate0
    if not spec078_gate0.run()["passed"]:
        print("refused: Gate 0 does not pass on these bytes", file=sys.stderr)
        return 1
    (ROOT / v2.FREEZE).write_text(_render(v2.freeze_record(ROOT, commit)), encoding="utf-8")
    (ROOT / v2.FINGERPRINTS).write_text(_render(v2.fingerprints(ROOT)), encoding="utf-8")
    print(f"wrote {v2.FREEZE} and {v2.FINGERPRINTS} at {commit}")
    return 0


def check() -> int:
    try:
        record = v2.load_freeze(ROOT)
        for name in v2.PROMPT_FILES:
            v2.check_freeze(ROOT, name)
        if v2.load_fingerprints(ROOT) is None or (ROOT / v2.FINGERPRINTS).read_text() != _render(v2.fingerprints(ROOT)):
            raise v2.FreezeError("v2 fingerprints are missing or stale", "holdout-fingerprint-stale")
    except v2.FreezeError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        return 1
    print(f"freeze holds at {record['commit']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return check() if args.check else write()


if __name__ == "__main__":
    sys.exit(main())
