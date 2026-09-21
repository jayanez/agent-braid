#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate private source readiness or a clean public export."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess

try:
    from scripts.closure_anchors import validate_closure_anchor
    from scripts.publication import PROHIBITED_TEXT, validate_export_tree, validate_portable_root
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from closure_anchors import validate_closure_anchor
    from publication import PROHIBITED_TEXT, validate_export_tree, validate_portable_root


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPRODUCTION_VERSION = "0.1.0"
PUBLIC_REPRODUCTION = "docs/releases/publication/reproduction.json"
PUBLIC_INPUTS = (
    ".github/workflows/validate.yml",
    "CONSTITUTION.md",
    ".specify/memory/constitution.md",
    "docs/releases/public-export.json",
    "pyproject.toml",
    "requirements-dev.txt",
    "requirements-speckit.txt",
    "scripts/publication.py",
    "scripts/validate_publication.py",
    "scripts/validate_spec_kit.py",
    "tests/test_publication.py",
)
PUBLIC_OBSERVATIONS = (
    "install",
    "repository",
    "contracts",
    "release-records",
    "publication",
    "spec-kit",
    "spec-kit-render",
    "spec-kit-integration",
    "tests",
    "scientific-controls",
    "constitution-replica",
    "whitespace",
)


def load(root: Path, relative: str) -> dict:
    path = root / relative
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"missing or invalid publication record: {relative}") from exc


def validate_cutover_pending(root: Path) -> None:
    record = load(root, "docs/releases/publication-cutover.json")
    if set(record) != {
        "recordVersion", "status", "sourceRepository", "archiveRepository",
        "publicRepository", "defaultBranch", "release", "remoteOperations",
        "githubActions", "limits",
    } or record.get("recordVersion") != "0.1.0" or record.get("status") != "pending-authorization":
        raise ValueError("publication cutover record fields or status are invalid")
    if record.get("defaultBranch") != "develop" or record.get("release") != "v0.1.0-alpha.1":
        raise ValueError("publication cutover branches or release are inconsistent")
    operations = record.get("remoteOperations")
    if not isinstance(operations, list) or not operations \
            or any(not isinstance(item, dict) or set(item) != {"operation", "authorized", "executed"}
                   or item["authorized"] is not False or item["executed"] is not False
                   for item in operations):
        raise ValueError("remote operations must remain explicitly unauthorized and unexecuted")
    if record.get("githubActions") != "not-executed-billing-blocked":
        raise ValueError("GitHub Actions billing limitation must remain explicit")
    if not isinstance(record.get("limits"), list) or not record["limits"]:
        raise ValueError("publication cutover limits are required")


def validate_public_reproduction(root: Path, relative: str) -> dict:
    payload = (root / relative).read_bytes()
    if any(pattern.search(payload) for pattern in PROHIBITED_TEXT):
        raise ValueError("public reproduction contains prohibited sensitive text")
    record = load(root, relative)
    required = {
        "recordVersion", "capturedAt", "reviewedCommit", "tree", "platform",
        "python", "git", "cleanRoom", "operator", "inputs", "observations",
        "independentValidation", "limits",
    }
    if set(record) != required or record.get("recordVersion") != PUBLIC_REPRODUCTION_VERSION:
        raise ValueError("public reproduction fields or version are invalid")
    try:
        captured = datetime.fromisoformat(record["capturedAt"])
    except (TypeError, ValueError) as exc:
        raise ValueError("public reproduction timestamp is invalid") from exc
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError("public reproduction timestamp requires a timezone")
    commit = record.get("reviewedCommit", "")
    tree = record.get("tree", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("public reproduction Git identities are invalid")
    process = subprocess.run(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root,
                             capture_output=True, text=True, check=False)
    if process.returncode or process.stdout.strip() != tree:
        raise ValueError("public reproduction tree does not match its commit")
    version = record.get("python", "")
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", version) \
            or tuple(map(int, version.split("."))) < (3, 12):
        raise ValueError("public reproduction requires Python 3.12 or newer")
    if not isinstance(record.get("platform"), str) or not record["platform"].strip() \
            or not isinstance(record.get("git"), str) or not record["git"].startswith("git version "):
        raise ValueError("public reproduction environment metadata is incomplete")
    if record.get("cleanRoom") != {
        "freshClone": True, "freshEnvironment": True, "pipCacheDisabled": True,
        "initialStatus": "", "finalStatus": "",
    }:
        raise ValueError("public reproduction is not a clean isolated run")
    operator = record.get("operator")
    if not isinstance(operator, dict) or set(operator) != {
        "automation", "authorization", "supervisor", "independent",
    } or operator.get("independent") is not False \
            or any(not isinstance(operator.get(name), str) or not operator[name].strip()
                   for name in ("automation", "authorization", "supervisor")):
        raise ValueError("public reproduction operator roles are incomplete")
    if record.get("independentValidation") != "pending":
        raise ValueError("public reproduction cannot infer independent validation")
    if set(record.get("inputs", {})) != set(PUBLIC_INPUTS):
        raise ValueError("public reproduction input inventory is incomplete")
    for name, checksum in record["inputs"].items():
        shown = subprocess.run(["git", "show", f"{commit}:{name}"], cwd=root,
                               capture_output=True, check=False)
        if shown.returncode or hashlib.sha256(shown.stdout).hexdigest() != checksum:
            raise ValueError(f"public reproduction input changed: {name}")
    observations = record.get("observations")
    if not isinstance(observations, list) or [item.get("id") for item in observations] != list(PUBLIC_OBSERVATIONS):
        raise ValueError("public reproduction observations are incomplete or out of order")
    if any(set(item) != {"id", "command", "exitCode", "stdout", "stderr"}
           or item.get("exitCode") != 0 for item in observations):
        raise ValueError("public reproduction contains a failed or malformed observation")
    if not isinstance(record.get("limits"), list) or not record["limits"]:
        raise ValueError("public reproduction limits are required")
    return record


def validate_source(root: Path = ROOT) -> None:
    validate_closure_anchor(root, "M0")
    validate_closure_anchor(root, "M0.5")
    validate_closure_anchor(root, "M1")
    readiness = load(root, "docs/releases/research-preview-readiness.json")
    if readiness.get("status") != "approved" \
            or readiness.get("recommendedPublicationMode") != "clean-export" \
            or readiness.get("currentTreeRedistributable") is not True \
            or readiness.get("repositoryVisibilityChangeAuthorized") is not False:
        raise ValueError("research-preview readiness does not preserve the approved boundary")
    validate_cutover_pending(root)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--source", action="store_true")
    modes.add_argument("--export", type=Path)
    modes.add_argument("--portable", action="store_true")
    args = parser.parse_args()
    try:
        if args.source:
            validate_source(ROOT)
            message = "Private publication source gates passed; no remote publication inferred."
        elif args.export:
            validate_export_tree(args.export)
            message = "Clean export bytes and manifest passed; private ancestry was not verified."
        else:
            validate_portable_root(ROOT)
            reproduction = ROOT / PUBLIC_REPRODUCTION
            if reproduction.is_file():
                validate_public_reproduction(ROOT, PUBLIC_REPRODUCTION)
                message = (
                    "Portable export integrity and internal reproduction passed; "
                    "private ancestry remains unavailable."
                )
            else:
                message = "Portable export integrity passed; private ancestry remains unavailable."
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"Publication validation failed: {exc}")
        return 1
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
