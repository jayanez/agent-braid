#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Create a deterministic clean-tree Agent Braid publication export."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

try:
    from scripts.publication import (
        MANIFEST, canonical_manifest, inventory, redact_local_paths,
        validate_export_tree,
    )
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from publication import (
        MANIFEST, canonical_manifest, inventory, redact_local_paths,
        validate_export_tree,
    )


ROOT = Path(__file__).resolve().parents[1]

def git(*args: str) -> bytes:
    process = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=False)
    if process.returncode:
        raise ValueError(f"Git failed: {' '.join(args)}")
    return process.stdout


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _export_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(root).parts
    )


def _sanitize_export(root: Path, source_payloads: dict[str, bytes]) -> list[dict]:
    """Redact local paths and rebind dependent digests without altering source bytes."""
    rules: dict[str, set[str]] = {}
    redacted_payloads: dict[str, bytes] = {}
    for path in _export_files(root):
        relative = path.relative_to(root).as_posix()
        payload = path.read_bytes()
        redacted = redact_local_paths(payload)
        if redacted != payload:
            path.write_bytes(redacted)
            rules.setdefault(relative, set()).add("local-path-redaction")
        redacted_payloads[relative] = redacted

    source_hashes = {relative: _digest(payload) for relative, payload in source_payloads.items()}
    # Historical records bind one another by SHA-256. Rebind those references to
    # their public, redacted representations. Acyclic evidence references converge
    # quickly; a cycle is rejected rather than emitted ambiguously.
    for _ in range(len(source_payloads) + 1):
        current_hashes = {
            relative: _digest((root / relative).read_bytes())
            for relative in source_payloads
        }
        replacements = {
            old.encode("ascii"): current_hashes[relative].encode("ascii")
            for relative, old in source_hashes.items()
            if old != current_hashes[relative]
        }
        changed = False
        for path in _export_files(root):
            relative = path.relative_to(root).as_posix()
            payload = path.read_bytes()
            # Rebuild from the stable redacted source on every pass. Replacing an
            # already rebound digest would otherwise strand second-order
            # references when a referenced record changes again on a later pass.
            rebound = redacted_payloads[relative]
            for old, new in sorted(replacements.items()):
                rebound = rebound.replace(old, new)
            if rebound != payload:
                path.write_bytes(rebound)
                rules.setdefault(relative, set()).add("transformed-digest-rebinding")
                changed = True
        if not changed:
            break
    else:
        raise ValueError("export digest references did not converge after redaction")

    transformations = []
    for relative in sorted(rules):
        source_hash = source_hashes[relative]
        published_hash = _digest((root / relative).read_bytes())
        if source_hash == published_hash:
            raise ValueError(f"declared export transformation made no change: {relative}")
        transformations.append({
            "path": relative,
            "sourceSha256": source_hash,
            "publishedSha256": published_hash,
            "rules": sorted(rules[relative]),
        })
    if not transformations:
        raise ValueError("export found no local-path-bearing evidence to sanitize")
    return transformations


def create_export(commit: str, destination: Path) -> dict:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("export requires an exact 40-character commit")
    resolved = git("rev-parse", f"{commit}^{{commit}}").decode("ascii").strip()
    if resolved != commit:
        raise ValueError("export commit did not resolve exactly")
    source_tree = git("rev-parse", f"{commit}^{{tree}}").decode("ascii").strip()
    target = destination.resolve()
    if target == ROOT.resolve() or target.is_relative_to(ROOT.resolve()):
        raise ValueError("export destination must be outside the source repository")
    if target.exists() and any(target.iterdir()):
        raise ValueError("export destination must be absent or empty")
    target.mkdir(parents=True, exist_ok=True)

    archive = git("archive", "--format=tar", commit)
    source_payloads: dict[str, bytes] = {}
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as package:
        for member in package.getmembers():
            relative = Path(member.name)
            if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
                raise ValueError(f"archive contains an unsafe path: {member.name}")
            output = (target / relative).resolve()
            if not output.is_relative_to(target):
                raise ValueError(f"archive path escapes destination: {member.name}")
            if member.isdir():
                output.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise ValueError(f"archive contains an unsupported non-file: {member.name}")
            if relative.as_posix() == MANIFEST:
                raise ValueError("source tree already contains a public export manifest")
            extracted = package.extractfile(member)
            if extracted is None:
                raise ValueError(f"archive file cannot be read: {member.name}")
            output.parent.mkdir(parents=True, exist_ok=True)
            payload = extracted.read()
            output.write_bytes(payload)
            source_payloads[relative.as_posix()] = payload
            os.chmod(output, member.mode & 0o777)

    transformations = _sanitize_export(target, source_payloads)

    manifest = {
        "recordVersion": "0.1.0",
        "sourceCommit": commit,
        "sourceTree": source_tree,
        "publicationMode": "clean-root",
        "historyIncluded": False,
        "historicalEvidence": {
            "sourceVerification": "internal-only",
            "publicRepresentation": "deterministically-redacted",
            "limit": (
                "Private Git ancestry and original local-path-bearing bytes are "
                "unavailable in the public export."
            ),
        },
        "independentValidation": "pending",
        "transformations": transformations,
        "protectedPaths": sorted(
            item["path"] for item in inventory(target)
            if re.match(r"specs/00[1-8]-", item["path"])
            or item["path"] in {
                "docs/releases/M0_CLOSURE.md",
                "docs/releases/M0_5_CLOSURE.md",
                "docs/releases/M1_CLOSURE.md",
                "docs/releases/closure-anchors.json",
                "docs/releases/records/M0.5.json",
                "docs/releases/records/M1.json",
            }
        ),
        "files": inventory(target),
    }
    manifest_path = target / MANIFEST
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(canonical_manifest(manifest))
    validate_export_tree(target)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit")
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        manifest = create_export(args.commit, args.destination)
    except (OSError, UnicodeError, ValueError, tarfile.TarError) as exc:
        print(f"Public export failed: {exc}")
        return 1
    print(json.dumps({
        "status": "created",
        "sourceCommit": manifest["sourceCommit"],
        "sourceTree": manifest["sourceTree"],
        "fileCount": len(manifest["files"]),
        "historyIncluded": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
