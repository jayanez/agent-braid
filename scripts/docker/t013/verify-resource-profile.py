#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Fail unless Linux enforces the accepted address-space cap on a Git child."""

from __future__ import annotations

import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
CAP = 512 * 1024 * 1024
sys.path.insert(0, str(ROOT))


def main() -> int:
    if sys.platform != "linux" or not hasattr(resource, "RLIMIT_AS"):
        raise SystemExit("T013 resource gate requires Linux RLIMIT_AS")

    child_code = (
        "import json, resource; "
        "soft, hard = resource.getrlimit(resource.RLIMIT_AS); "
        "print(json.dumps({'soft': soft, 'hard': hard}))"
    )
    launcher = ROOT / "agent_braid" / "git_exec.py"
    process = subprocess.run(
        [sys.executable, str(launcher), str(CAP), sys.executable, "-c", child_code],
        check=True, capture_output=True, text=True, timeout=10,
        env={
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": "/tmp/home",
            "LC_ALL": "C",
        },
    )
    observed = json.loads(process.stdout)
    if observed != {"soft": CAP, "hard": CAP}:
        raise SystemExit(f"RLIMIT_AS child did not inherit the exact cap: {observed}")

    from agent_braid.git_process import GitCommandBudget, run_git

    with tempfile.TemporaryDirectory(prefix="agent-braid-t013-resource-check-") as scratch:
        budget = GitCommandBudget(
            temp_root=Path(scratch), max_process_address_space_bytes=CAP,
        )
        result = run_git(
            Path(scratch), ("version",),
            env={"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                 "HOME": "/tmp/home", "LC_ALL": "C"},
            budget=budget,
        )
        if not result.stdout.startswith(b"git version "):
            raise SystemExit("Git child did not complete under the address-space cap")

    print(json.dumps({
        "status": "verified",
        "platform": sys.platform,
        "addressSpaceLimitBytes": CAP,
        "observedChildSoftLimitBytes": observed["soft"],
        "observedChildHardLimitBytes": observed["hard"],
        "gitVersion": result.stdout.decode("ascii", "strict").strip(),
        "executionAuthorization": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
