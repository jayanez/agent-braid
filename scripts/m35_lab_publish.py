# SPDX-License-Identifier: AGPL-3.0-only
"""Fast-forward a disposable lab snapshot branch from a filtered export."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from scripts.m35_lab_export import SNAPSHOT_FORMAT, _safe_file_name


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], check=check,
                          capture_output=True, text=True)


def _validated_snapshot(directory: Path, branch: str) -> dict:
    metadata = json.loads((directory / "lab-snapshot.json").read_text(encoding="utf-8"))
    if (type(metadata) is not dict or set(metadata) != {
            "format", "sourceRepo", "sourceRef", "sourceSha", "allowlistSha256", "files"}
            or metadata["format"] != SNAPSHOT_FORMAT or metadata["sourceRef"] != branch
            or type(metadata["files"]) is not dict or not metadata["files"]):
        raise ValueError("invalid filtered snapshot")
    expected = set(metadata["files"]) | {"lab-snapshot.json"}
    items = list(directory.rglob("*"))
    if any(item.is_symlink() for item in items):
        raise ValueError("snapshot contains a symbolic link")
    present = {item.relative_to(directory).as_posix() for item in items if item.is_file()}
    if present != expected:
        raise ValueError("snapshot has missing or unapproved files")
    for name, expected_digest in metadata["files"].items():
        _safe_file_name(name)
        item = directory / name
        if item.is_symlink() or sha256(item.read_bytes()).hexdigest() != expected_digest:
            raise ValueError(f"snapshot file digest changed: {name}")
    return metadata


def publish_snapshot(control: Path, snapshot: Path, branch: str) -> dict:
    if branch not in ("main", "develop"):
        raise ValueError("invalid lab source branch")
    metadata = _validated_snapshot(snapshot, branch)
    lab_ref = f"refs/heads/lab/{branch}"
    current = _git(control, "ls-remote", "--exit-code", "origin", lab_ref, check=False)
    if current.returncode not in (0, 2):
        raise ValueError("cannot inspect lab branch")
    exists = current.returncode == 0
    if exists:
        _git(control, "fetch", "origin", f"{lab_ref}:refs/remotes/origin/lab/{branch}")
    with TemporaryDirectory() as temporary:
        workdir = Path(temporary) / "publish"
        _git(control, "worktree", "add", "--detach", str(workdir), "HEAD")
        try:
            if exists:
                _git(workdir, "checkout", "--detach", f"refs/remotes/origin/lab/{branch}")
            else:
                _git(workdir, "checkout", "--orphan", f"m35-first-{branch}")
            for child in workdir.iterdir():
                if child.name == ".git":
                    continue
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            for item in snapshot.rglob("*"):
                if item.is_file():
                    target = workdir / item.relative_to(snapshot)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(item, target)
            _git(workdir, "add", "-A")
            if exists:
                difference = _git(workdir, "diff", "--cached", "--quiet", check=False)
                if difference.returncode == 0:
                    return {"changed": False, "branch": lab_ref, "sourceSha": metadata["sourceSha"]}
                if difference.returncode != 1:
                    raise ValueError("cannot compare the candidate lab snapshot")
            _git(workdir, "-c", "user.name=Agent Braid Lab Sync", "-c",
                 "user.email=lab-sync@users.noreply.github.com", "commit", "-m",
                 f"sync({branch}): reviewed source {metadata['sourceSha'][:12]}")
            _git(workdir, "push", "origin", f"HEAD:{lab_ref}")
            return {"changed": True, "branch": lab_ref, "sourceSha": metadata["sourceSha"],
                    "labCommit": _git(workdir, "rev-parse", "HEAD").stdout.strip()}
        finally:
            _git(control, "worktree", "remove", "--force", str(workdir))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("control", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("branch", choices=("main", "develop"))
    args = parser.parse_args()
    print(json.dumps(publish_snapshot(args.control, args.snapshot, args.branch), sort_keys=True))


if __name__ == "__main__":
    main()
