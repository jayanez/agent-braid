#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Serialize pure M3 terminal sequences into an isolated temporary Git store."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from agent_braid.structured_exchange import replay, validate_request


def _git(directory: Path, env: dict[str, str], *args: str, data: bytes | None = None) -> str:
    completed = subprocess.run(
        ["git", f"--git-dir={directory}", *args], input=data,
        capture_output=True, check=True, env=env, timeout=15,
    )
    return completed.stdout.decode("ascii").strip()


def witness(request: dict) -> dict:
    validate_request(request)
    if len(request["operations"]) != 2:
        raise ValueError("Git witness is limited to a pair")
    ids = [op["id"] for op in request["operations"]]
    input_hash = hashlib.sha256(json.dumps(
        request, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")).hexdigest()
    trees: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="agent-braid-m3-git-") as scratch:
        git_dir = Path(scratch) / "objects.git"
        environment = os.environ.copy()
        environment["GIT_CONFIG_NOSYSTEM"] = "1"
        environment["GIT_CONFIG_GLOBAL"] = os.devnull
        subprocess.run(["git", "init", "--bare", "-q", str(git_dir)],
                       check=True, capture_output=True, env=environment, timeout=15)
        for number, order in enumerate(itertools.permutations(ids)):
            result = replay(request, order)
            payload = json.dumps(result["final"], sort_keys=True,
                                 separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            environment["GIT_INDEX_FILE"] = str(Path(scratch) / f"index-{number}")
            blob = _git(git_dir, environment, "hash-object", "-w", "--stdin", data=payload)
            _git(git_dir, environment, "update-index", "--add", "--cacheinfo",
                 f"100644,{blob},sequence.json")
            tree = _git(git_dir, environment, "write-tree")
            trees.append({"order": list(order), "tree": tree, "blob": blob,
                          "observationHash": result["observationHash"]})
    return {"format": "m3-git-serialization-witness-v1", "requestHash": input_hash,
            "paths": trees, "sameTree": trees[0]["tree"] == trees[1]["tree"],
            "claim": "temporary serialization of pure terminal sequences only; not an M2 fixed-patch certificate",
            "executionAuthorization": False}


def main() -> int:
    request_path = Path(sys.argv[1])
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result = witness(request)
    inputs = [request_path, Path("agent_braid/structured_exchange.py"),
              Path("scripts/run_m3_git_witness.py")]
    result["inputs"] = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in inputs}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["sameTree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
