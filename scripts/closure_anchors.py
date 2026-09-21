#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate immutable milestone intervals without freezing a moving HEAD."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess


ANCHORS = "docs/releases/closure-anchors.json"
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def _git(root: Path, *args: str) -> bytes:
    process = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, check=False,
    )
    if process.returncode:
        raise ValueError(
            f"Git failed while validating closure anchor: {' '.join(args)}"
        )
    return process.stdout


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_anchors(root: Path) -> dict:
    path = root / ANCHORS
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("closure anchor registry is missing or invalid") from exc
    if set(data) != {"recordVersion", "milestones"} \
            or data["recordVersion"] != "0.1.0" \
            or set(data["milestones"]) != {"M0", "M0.5", "M1"}:
        raise ValueError("closure anchor registry fields or version are invalid")
    return data["milestones"]


def validate_closure_anchor(root: Path, milestone: str, candidate: str | None = None) -> dict:
    try:
        anchor = load_anchors(root)[milestone]
    except KeyError as exc:
        raise ValueError(f"missing closure anchor: {milestone}") from exc
    if set(anchor) != {
        "candidateCommit", "closureCommit", "closureTree", "changedPaths",
        "protectedPaths",
    }:
        raise ValueError(f"{milestone} closure anchor fields are invalid")
    if any(not isinstance(anchor[name], str) or not HEX40.fullmatch(anchor[name])
           for name in ("candidateCommit", "closureCommit", "closureTree")):
        raise ValueError(f"{milestone} closure anchor contains an invalid Git identity")
    if candidate is not None and anchor["candidateCommit"] != candidate:
        raise ValueError(f"{milestone} closure anchor names a different candidate")
    changed = anchor["changedPaths"]
    protected = anchor["protectedPaths"]
    if not isinstance(changed, list) or changed != sorted(set(changed)) \
            or not isinstance(protected, dict) or not protected:
        raise ValueError(f"{milestone} closure anchor inventories are invalid")
    if any(not isinstance(path, str) or not path or path.startswith(("/", "../"))
           for path in [*changed, *protected]):
        raise ValueError(f"{milestone} closure anchor contains an unsafe path")
    if any(not isinstance(value, str) or not HEX64.fullmatch(value)
           for value in protected.values()):
        raise ValueError(f"{milestone} closure anchor contains an invalid digest")

    candidate_commit = anchor["candidateCommit"]
    closure_commit = anchor["closureCommit"]
    _git(root, "cat-file", "-e", f"{candidate_commit}^{{commit}}")
    _git(root, "cat-file", "-e", f"{closure_commit}^{{commit}}")
    tree = _git(root, "rev-parse", f"{closure_commit}^{{tree}}").decode("ascii").strip()
    if tree != anchor["closureTree"]:
        raise ValueError(f"{milestone} closure tree does not match its anchor")
    _git(root, "merge-base", "--is-ancestor", candidate_commit, closure_commit)
    _git(root, "merge-base", "--is-ancestor", closure_commit, "HEAD")
    actual_changed = sorted(filter(None, _git(
        root, "diff", "--name-only", candidate_commit, closure_commit, "--",
    ).decode("utf-8").splitlines()))
    if actual_changed != changed:
        raise ValueError(f"{milestone} candidate-to-closure path inventory changed")
    for relative, checksum in protected.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() \
                or _digest(path) != checksum:
            raise ValueError(f"{milestone} protected closure record changed: {relative}")
        historical = _git(root, "show", f"{closure_commit}:{relative}")
        if hashlib.sha256(historical).hexdigest() != checksum:
            raise ValueError(f"{milestone} anchor digest does not match closure history: {relative}")
    return anchor
