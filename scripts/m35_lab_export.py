# SPDX-License-Identifier: AGPL-3.0-only
"""Export a reviewed, exact-file decision context without Git ancestry.

The manifest pins each permitted Git blob. A changed file blocks the next
snapshot until its new bytes receive a separate review. This is deliberately
not a whole-repository mirror or a scanner that claims to find every secret.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


FORMAT = "m35-lab-export-v1"
SNAPSHOT_FORMAT = "m35-lab-snapshot-v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MAX_FILE_BYTES = 64 * 1024


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _safe_file_name(name: object) -> str:
    if type(name) is not str or not name or "\\" in name:
        raise ValueError("export path is invalid")
    item = PurePosixPath(name)
    if (item.is_absolute() or item.as_posix() != name
            or any(part in ("", ".", "..") for part in name.split("/"))
            or not name.endswith(".md")
            or not name.startswith(("docs/adr/", "specs/", ".specify/templates/"))):
        raise ValueError("export path escapes the snapshot")
    return name


def validate_manifest(value: object) -> dict:
    if (type(value) is not dict or set(value) != {"format", "sourceRepo", "branches"}
            or value.get("format") != FORMAT or type(value.get("sourceRepo")) is not str
            or REPOSITORY.fullmatch(value["sourceRepo"]) is None):
        raise ValueError("invalid lab export manifest")
    branches = value["branches"]
    if type(branches) is not dict or set(branches) != {"main", "develop"}:
        raise ValueError("lab export must pin both main and develop")
    for branch in branches.values():
        if type(branch) is not dict or set(branch) != {"files"} or type(branch["files"]) is not dict:
            raise ValueError("invalid branch allowlist")
        if not branch["files"]:
            raise ValueError("empty branch allowlist")
        for name, blob_sha in branch["files"].items():
            _safe_file_name(name)
            if type(blob_sha) is not str or HEX40.fullmatch(blob_sha) is None:
                raise ValueError("approved blob SHA must be complete")
    return value


def export_snapshot(source: Path, manifest_path: Path, branch: str, output: Path,
                    *, expected_repo: str | None = None) -> dict:
    manifest_bytes = manifest_path.read_bytes()
    manifest = validate_manifest(json.loads(manifest_bytes))
    if branch not in ("main", "develop"):
        raise ValueError("invalid source branch")
    if expected_repo is not None and manifest["sourceRepo"] != expected_repo:
        raise ValueError("source repository differs from expected lab source")
    source_sha = _git(source, "rev-parse", "HEAD")
    if HEX40.fullmatch(source_sha) is None:
        raise ValueError("source checkout has no full Git SHA")
    if _git(source, "status", "--porcelain"):
        raise ValueError("source checkout has uncommitted changes")
    files = manifest["branches"][branch]["files"]
    inspected = []
    for name, approved_blob in sorted(files.items()):
        actual_blob = _git(source, "rev-parse", f"HEAD:{name}")
        if actual_blob != approved_blob:
            raise ValueError(f"approved content changed: {name}")
        mode = _git(source, "ls-tree", "HEAD", "--", name).split()[0]
        if mode != "100644":
            raise ValueError(f"only ordinary non-executable files may be exported: {name}")
        item = source / name
        if item.is_symlink() or not item.is_file():
            raise ValueError(f"source file is missing or linked: {name}")
        raw = item.read_bytes()
        if len(raw) > MAX_FILE_BYTES:
            raise ValueError(f"source file exceeds the reviewed size limit: {name}")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"source file is not UTF-8 text: {name}") from exc
        inspected.append((name, raw))
    output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, raw in inspected:
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    snapshot = {"format": SNAPSHOT_FORMAT, "sourceRepo": manifest["sourceRepo"],
                "sourceRef": branch, "sourceSha": source_sha,
                "allowlistSha256": sha256(manifest_bytes).hexdigest(),
                "files": {name: sha256(raw).hexdigest() for name, raw in inspected}}
    (output / "lab-snapshot.json").write_text(json.dumps(snapshot, sort_keys=True, indent=2) + "\n",
                                              encoding="utf-8")
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("branch", choices=("main", "develop"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--expected-repo")
    args = parser.parse_args()
    snapshot = export_snapshot(args.source, args.manifest, args.branch, args.output,
                               expected_repo=args.expected_repo)
    print(json.dumps({"sourceRef": snapshot["sourceRef"], "sourceSha": snapshot["sourceSha"],
                      "fileCount": len(snapshot["files"]), "allowlistSha256": snapshot["allowlistSha256"]},
                     sort_keys=True))


if __name__ == "__main__":
    main()
