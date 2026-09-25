# SPDX-License-Identifier: AGPL-3.0-only
"""Keep the reviewed public SPEC-012 candidate reachable for CI validation.

The public repository squash-merged its implementation PR, so a normal clone
does not retain the candidate commit named by historical assurance. This tool
fetches only that exact public commit and adds a local remote-tracking ref.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
ASSURANCE = ROOT / "specs/012-m2-git-replay-planner/assurance.json"
REF = "refs/remotes/origin/spec-012-reviewed-candidate"


def git(*args: str, allow_failure: bool = False) -> str:
    environment = os.environ.copy()
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    result = subprocess.run(["git", "-C", str(ROOT), *args], env=environment,
                            capture_output=True, check=False, text=True, timeout=90)
    if result.returncode and not allow_failure:
        raise ValueError(f"Git public-history check failed: {args[0]}")
    return result.stdout.strip() if result.returncode == 0 else ""


def main() -> int:
    record = json.loads(ASSURANCE.read_text())
    authority = record["authority_snapshot"]
    evidence = record["evidence_snapshot"]
    candidate = authority.get("commit")
    if (authority.get("mode") != "historical"
            or evidence.get("mode") != "historical"
            or evidence.get("commit") != candidate
            or not isinstance(candidate, str)
            or not re.fullmatch(r"[0-9a-f]{40}", candidate)):
        raise ValueError("SPEC-012 reviewed candidate is not consistently frozen")
    origin = git("remote", "get-url", "origin")
    if origin not in {
        "https://github.com/jayanez/agent-braid",
        "https://github.com/jayanez/agent-braid.git",
        "git@github.com:jayanez/agent-braid.git",
    }:
        raise ValueError("origin must be the public Agent Braid repository")
    roots = git("rev-list", "--max-parents=0", "HEAD").splitlines()
    if len(roots) != 1:
        raise ValueError("public checkout must have one clean root")
    if git("rev-parse", "--verify", f"{candidate}^{{commit}}",
           allow_failure=True) != candidate:
        git("fetch", "--quiet", "--no-tags", "origin", candidate)
    if git("rev-parse", "--verify", f"{candidate}^{{commit}}") != candidate:
        raise ValueError("reviewed candidate is unavailable after fetch")
    if git("merge-base", roots[0], candidate, allow_failure=True) != roots[0]:
        raise ValueError("reviewed candidate does not descend from the public root")
    git("update-ref", REF, candidate)
    print(f"SPEC-012 historical candidate reachable at {REF}; no remote ref changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
