# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T014 (REQ-014): freeze the v3 protocol, split, builder, Gate 0, analysis and the fixed skill.

Writes ``prompts/FREEZE-v3.json`` and ``prompts/fingerprints-v3.json``. It refuses unless the tree is clean, the
current commit is the ``origin/develop`` tip, the committed split equals a fresh build and Gate 0 passes on it.

    python -m scripts.spec078_freeze_v3           # write the v3 freeze on a develop commit
    python -m scripts.spec078_freeze_v3 --check   # exit 1 unless the committed v3 freeze matches the files
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from agent_braid import lightning_heldout_v3 as v3

ROOT = Path(__file__).resolve().parents[1]


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def _render(value: dict) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


def write() -> int:
    if _git("status", "--porcelain"):
        print("refused: the freeze needs a clean tree", file=sys.stderr)
        return 1
    _git("fetch", "-q", "origin", "develop")
    commit = _git("rev-parse", "HEAD")
    if commit != _git("rev-parse", "origin/develop"):
        print("refused: the freeze is made on the origin/develop tip", file=sys.stderr)
        return 1
    from scripts import spec078_build_v3, spec078_gate0
    if (ROOT / v3.PROMPT_FILES["v3-test"]).read_text("utf-8") != spec078_build_v3.render(spec078_build_v3.build()):
        print("refused: the committed v3 split differs from a fresh build", file=sys.stderr)
        return 1
    cases = json.loads((ROOT / v3.PROMPT_FILES["v3-test"]).read_text("utf-8"))["cases"]
    if not spec078_gate0.run({"test": cases})["passed"]:
        print("refused: Gate 0 does not pass on the v3 split", file=sys.stderr)
        return 1
    (ROOT / v3.FREEZE).write_text(_render(v3.freeze_record(ROOT, commit)), encoding="utf-8")
    (ROOT / v3.FINGERPRINTS).write_text(_render(v3.fingerprints(ROOT)), encoding="utf-8")
    print(f"wrote {v3.FREEZE} and {v3.FINGERPRINTS} at {commit}")
    return 0


def check() -> int:
    try:
        record = v3.load_freeze(ROOT)
        v3.check_freeze(ROOT, "v3-test")
        if v3.load_fingerprints(ROOT) is None or (ROOT / v3.FINGERPRINTS).read_text() != _render(v3.fingerprints(ROOT)):
            raise v3.FreezeError("v3 fingerprints are missing or stale", "holdout-fingerprint-stale")
    except v3.FreezeError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        return 1
    print(f"v3 freeze holds at {record['commit']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return check() if args.check else write()


if __name__ == "__main__":
    sys.exit(main())
