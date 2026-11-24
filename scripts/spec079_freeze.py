# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T007 (REQ-008, REQ-011): freeze the v4 protocol, split, builder, Gate 0 report and pinned plugin.

Writes ``prompts/FREEZE-v4.json``. It refuses unless the tree is clean apart from the freeze's own files, the
current commit is the ``origin/develop`` tip, the committed split equals a fresh build, a fresh Gate 0 equals
the committed passing report, and no frozen SPEC-069 or SPEC-078 path changed. The freeze commit is the pinned plugin commit (OD-D):
it holds the T001 refusal, the T002 descriptions and the analyze skill the v4 arm measures.

    python -m scripts.spec079_freeze           # write the v4 freeze on a develop commit
    python -m scripts.spec079_freeze --check   # exit 1 unless the committed v4 freeze matches the files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = "specs/079-kind-choice-tool-fix"
FREEZE = f"{SPEC}/prompts/FREEZE-v4.json"
SCHEMA = "braid-lightning-v4-freeze/v0.1"
SPLIT = f"{SPEC}/prompts/v4-test.json"
GATE0 = f"{SPEC}/evidence/gate0-v4-report.json"
SKILL = "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"

# What the v4 arm and its scoring depend on. The plugin itself is pinned by the freeze commit; these are the
# files whose bytes the run measures or scores with, bound so a later edit refuses the run.
BOUND = (
    f"{SPEC}/evaluation-protocol.md",
    SPLIT,
    GATE0,
    "scripts/spec079_build_v4.py",
    "scripts/spec078_build_set.py",   # fact generator and footprint rule the v4 builder uses
    "scripts/spec078_gate0.py",
    "scripts/spec069_scoring.py",     # the unchanged scorer
    "scripts/spec069_fixture_workspace.py",
    "agent_braid/lightning_heldout_v2.py",  # OD-1 analysis
    "agent_braid/tooling_mcp.py",     # T001 refusal and T002 descriptions
    "agent_braid/analysis.py",
    "agent_braid/units.py",
    "agent_braid/analyze_work_schema.py",
    SKILL,
)

# Closed records that SPEC-079 must not change (REQ-011). Each maps a freeze record to the files it binds.
SPEC069_FREEZE = "specs/069-aim-request-authoring/prompts/FREEZE.json"
SPEC078_FREEZE = "specs/078-lightning-heldout-v2/prompts/FREEZE.json"
SPEC078_FREEZE_V3 = "specs/078-lightning-heldout-v2/prompts/FREEZE-v3.json"
RECORDS = (SPEC069_FREEZE, SPEC078_FREEZE, SPEC078_FREEZE_V3)


class FreezeError(ValueError):
    pass


def sha256(root: Path, path: str) -> str:
    return hashlib.sha256((root / path).read_bytes()).hexdigest()


def frozen_paths(root: Path) -> dict[str, str]:
    """Every path a closed SPEC-069 or SPEC-078 freeze binds, with the hash it binds.

    The SPEC-078 v3 freeze supersedes the v2 freeze for any path both bind: the analyze skill changed in SPEC-078
    T012 (before SPEC-079) and was re-frozen in v3, so the v3 hash is the one that must still hold.
    """
    spec069 = json.loads((root / SPEC069_FREEZE).read_text("utf-8"))["records"][-1]["files"]
    v2 = json.loads((root / SPEC078_FREEZE).read_text("utf-8"))["files"]
    v3 = json.loads((root / SPEC078_FREEZE_V3).read_text("utf-8"))["files"]
    return {**spec069, **v2, **v3}


def boundary_problems(root: Path, records: dict[str, str]) -> list[str]:
    """REQ-011 / SC-014: the closed freeze records and every path they bind are unchanged."""
    problems = [f"{path} changed after the SPEC-079 freeze" for path, digest in records.items()
                if not (root / path).is_file() or sha256(root, path) != digest]
    for path, digest in frozen_paths(root).items():
        if not (root / path).is_file() or sha256(root, path) != digest:
            problems.append(f"{path} differs from its SPEC-069/078 freeze")
    return problems


def record(root: Path, commit: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise FreezeError("the freeze names a full develop commit")
    from agent_braid import __version__
    return {"schema": SCHEMA, "commit": commit, "pluginCommit": commit, "pluginVersion": __version__,
            "files": {path: sha256(root, path) for path in BOUND},
            "closedRecords": {path: sha256(root, path) for path in RECORDS}}


def load(root: Path) -> dict:
    path = root / FREEZE
    if not path.is_file():
        raise FreezeError("v4 is not frozen; v4 runs are refused")
    value = json.loads(path.read_text("utf-8"))
    if (value.get("schema") != SCHEMA or set(value.get("files") or {}) != set(BOUND)
            or set(value.get("closedRecords") or {}) != set(RECORDS) or value.get("pluginCommit") != value.get("commit")
            or not re.fullmatch(r"[0-9a-f]{40}", str(value.get("commit")))):
        raise FreezeError("unknown v4 freeze record")
    return value


def check_freeze(root: Path) -> dict:
    value = load(root)
    changed = [path for path in BOUND if not (root / path).is_file() or sha256(root, path) != value["files"][path]]
    if changed:
        raise FreezeError(f"{', '.join(changed)} differs from the v4 freeze")
    problems = boundary_problems(root, value["closedRecords"])
    if problems:
        raise FreezeError("; ".join(problems))
    return value


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout.strip()


def render(value: dict) -> str:
    return json.dumps(value, indent=1, sort_keys=True) + "\n"


# The freeze lands in one PR with its own tooling, so only these paths may differ from the develop tip while it
# is written. None of them is bound, so every bound byte is the committed byte at the freeze commit.
OWN = ("scripts/spec079_freeze.py", "tests/test_spec079_boundaries.py", FREEZE, f"{SPEC}/tasks.md")


def write() -> int:
    status = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=all"],
                            capture_output=True, text=True, check=True).stdout
    dirty = [line[3:] for line in status.splitlines()]
    if any(path not in OWN for path in dirty):
        print("refused: the freeze needs a clean tree apart from its own files", file=sys.stderr)
        return 1
    _git("fetch", "-q", "origin", "develop")
    commit = _git("rev-parse", "HEAD")
    if commit != _git("rev-parse", "origin/develop"):
        print("refused: the freeze is made on the origin/develop tip", file=sys.stderr)
        return 1
    from scripts import spec079_build_v4 as v4
    if (ROOT / SPLIT).read_text("utf-8") != v4.render(v4.build()):
        print("refused: the committed v4 split differs from a fresh build", file=sys.stderr)
        return 1
    committed = json.loads((ROOT / GATE0).read_text("utf-8"))
    fresh = json.loads(json.dumps(v4.gate0(json.loads((ROOT / SPLIT).read_text("utf-8"))["cases"]), sort_keys=True))
    if not committed.get("passed") or fresh != committed:
        print("refused: Gate 0 on v4 does not pass or differs from the committed report", file=sys.stderr)
        return 1
    problems = boundary_problems(ROOT, {path: sha256(ROOT, path) for path in RECORDS})
    if problems:
        print("refused: " + "; ".join(problems), file=sys.stderr)
        return 1
    (ROOT / FREEZE).write_text(render(record(ROOT, commit)), encoding="utf-8")
    print(f"wrote {FREEZE} at {commit}")
    return 0


def check() -> int:
    try:
        value = check_freeze(ROOT)
    except FreezeError as error:
        print(f"v4 freeze broken: {error}", file=sys.stderr)
        return 1
    print(f"v4 freeze holds at {value['commit']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    return check() if args.check else write()


if __name__ == "__main__":
    sys.exit(main())
