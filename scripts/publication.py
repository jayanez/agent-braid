#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Shared validation for clean public-export artifacts."""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path, PurePosixPath
import re
import subprocess


MANIFEST = "docs/releases/public-export.json"
ADDENDUM = "docs/releases/public-export-addendum-m2.json"
MANIFEST_VERSION = "0.1.0"
MANIFEST_FIELDS = {
    "recordVersion", "sourceCommit", "sourceTree", "publicationMode",
    "historyIncluded", "historicalEvidence", "independentValidation", "files",
    "protectedPaths", "transformations",
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
PROHIBITED_TEXT = (
    re.compile(b"/" + b"Users/" + rb"[^/\s]+/"),
    re.compile(b"/private/" + b"var/folders/"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"gh[opusr]_[A-Za-z0-9_]{30,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
)
LOCAL_PATH_REDACTIONS = (
    (
        re.compile(rb"/(?:private/)?var/folders/[^/\s\"']+/[^/\s\"']+/T/agent-braid-[^/\s\"']+"),
        b"${CLEAN_ROOM}",
    ),
    (
        re.compile(rb"/(?:private/)?var/folders/[^/\s\"']+/[^/\s\"']+/T/pip-install-[^/\s\"']+"),
        b"${PIP_BUILD_DIR}",
    ),
    (
        re.compile(rb"/(?:private/)?var/folders/[^/\s\"']+/[^/\s\"']+/T/pip-ephem-wheel-cache-[^/\s\"']+"),
        b"${PIP_CACHE}",
    ),
    (
        re.compile(b"/" + b"Users/" + rb"[^/\s\"']+(?:/[^\s\"']*)?"),
        b"${LOCAL_PATH}",
    ),
    (re.compile(rb"/(?:private/)?var/folders/[^\s\"']+"), b"${LOCAL_TEMP_PATH}"),
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def redact_local_paths(value: bytes) -> bytes:
    redacted = value
    for pattern, replacement in LOCAL_PATH_REDACTIONS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def safe_relative(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts \
            or any(part in {"", ".", ".git"} for part in path.parts):
        raise ValueError(f"unsafe export path: {value}")
    return path.as_posix()


def inventory(root: Path) -> list[dict]:
    result: list[dict] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or ".git" in path.relative_to(root).parts:
            continue
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST:
            continue
        payload = path.read_bytes()
        result.append({"path": relative, "sha256": digest_bytes(payload), "size": len(payload)})
    return result


def canonical_manifest(data: dict) -> bytes:
    return (json.dumps(data, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_manifest(root: Path) -> dict:
    path = root / MANIFEST
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("public export manifest is missing or invalid") from exc
    if set(data) != MANIFEST_FIELDS or data.get("recordVersion") != MANIFEST_VERSION:
        raise ValueError("public export manifest fields or version are invalid")
    if not HEX40.fullmatch(str(data.get("sourceCommit", ""))) \
            or not HEX40.fullmatch(str(data.get("sourceTree", ""))):
        raise ValueError("public export manifest Git identities are invalid")
    if data.get("publicationMode") != "clean-root" or data.get("historyIncluded") is not False:
        raise ValueError("public export manifest does not declare a clean root")
    if data.get("historicalEvidence") != {
        "sourceVerification": "internal-only",
        "publicRepresentation": "deterministically-redacted",
        "limit": (
            "Private Git ancestry and original local-path-bearing bytes are "
            "unavailable in the public export."
        ),
    }:
        raise ValueError("public export manifest obscures the private-history limit")
    if data.get("independentValidation") != "pending":
        raise ValueError("public export cannot infer independent validation")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("public export manifest inventory is empty")
    normalized: list[dict] = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise ValueError("public export manifest file record is invalid")
        relative = safe_relative(item.get("path", ""))
        if not HEX64.fullmatch(str(item.get("sha256", ""))) \
                or type(item.get("size")) is not int or item["size"] < 0:
            raise ValueError(f"public export manifest metadata is invalid: {relative}")
        normalized.append({**item, "path": relative})
    if normalized != sorted(normalized, key=lambda item: item["path"]) \
            or len({item["path"] for item in normalized}) != len(normalized):
        raise ValueError("public export manifest paths must be unique and sorted")
    if (root / MANIFEST).read_bytes() != canonical_manifest(data):
        raise ValueError("public export manifest is not canonical JSON")
    protected = data.get("protectedPaths")
    if not isinstance(protected, list) or not protected \
            or protected != sorted(set(protected)):
        raise ValueError("public export protected paths must be nonempty, unique and sorted")
    inventory_paths = {item["path"] for item in normalized}
    for relative in protected:
        if safe_relative(relative) not in inventory_paths:
            raise ValueError(f"protected path is absent from export inventory: {relative}")
    transformations = data.get("transformations")
    if not isinstance(transformations, list) or not transformations:
        raise ValueError("public export must disclose its deterministic transformations")
    normalized_transformations: list[dict] = []
    allowed_rules = {"local-path-redaction", "transformed-digest-rebinding"}
    inventory_by_path = {item["path"]: item for item in normalized}
    for item in transformations:
        if not isinstance(item, dict) or set(item) != {
            "path", "sourceSha256", "publishedSha256", "rules",
        }:
            raise ValueError("public export transformation record is invalid")
        relative = safe_relative(item.get("path", ""))
        rules = item.get("rules")
        if not isinstance(rules, list) or rules != sorted(set(rules)) \
                or not rules or not set(rules).issubset(allowed_rules):
            raise ValueError(f"public export transformation rules are invalid: {relative}")
        source_hash = str(item.get("sourceSha256", ""))
        published_hash = str(item.get("publishedSha256", ""))
        if not HEX64.fullmatch(source_hash) or not HEX64.fullmatch(published_hash) \
                or source_hash == published_hash:
            raise ValueError(f"public export transformation digests are invalid: {relative}")
        if relative not in inventory_by_path \
                or inventory_by_path[relative]["sha256"] != published_hash:
            raise ValueError(f"public export transformation is not bound to payload: {relative}")
        normalized_transformations.append({**item, "path": relative})
    if normalized_transformations != sorted(
            normalized_transformations, key=lambda item: item["path"]
    ) or len({item["path"] for item in normalized_transformations}) \
            != len(normalized_transformations):
        raise ValueError("public export transformations must be unique and sorted")
    return data


def validate_export_tree(root: Path) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("public export root is missing")
    data = load_manifest(root)
    actual = inventory(root)
    if actual != data["files"]:
        raise ValueError("public export file inventory or bytes changed")
    for item in actual:
        payload = (root / item["path"]).read_bytes()
        for pattern in PROHIBITED_TEXT:
            if pattern.search(payload):
                raise ValueError(f"public export contains prohibited sensitive text: {item['path']}")
    return data


def _git(root: Path, *args: str, allow_failure: bool = False) -> subprocess.CompletedProcess:
    process = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if process.returncode and not allow_failure:
        raise ValueError(f"Git failed during portable validation: {' '.join(args)}")
    return process


def validate_portable_root(root: Path) -> dict:
    data = load_manifest(root)
    if not (root / ".git").exists():
        raise ValueError("portable validation requires a Git repository")
    roots = _git(root, "rev-list", "--max-parents=0", "--all").stdout.decode("ascii").split()
    if len(roots) != 1:
        raise ValueError("public repository must have exactly one clean root")
    root_commit = roots[0]
    manifest_at_root = _git(root, "show", f"{root_commit}:{MANIFEST}").stdout
    if manifest_at_root != (root / MANIFEST).read_bytes():
        raise ValueError("public export manifest must be unchanged since the root commit")
    root_inventory: list[dict] = []
    names = _git(root, "ls-tree", "-r", "--name-only", "-z", root_commit).stdout.split(b"\0")
    for raw in names:
        if not raw:
            continue
        try:
            relative = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("public root contains a non-UTF-8 path") from exc
        if relative == MANIFEST:
            continue
        payload = _git(root, "show", f"{root_commit}:{relative}").stdout
        root_inventory.append({
            "path": safe_relative(relative),
            "sha256": digest_bytes(payload),
            "size": len(payload),
        })
    if root_inventory != data["files"]:
        raise ValueError("public root commit does not match the clean-export manifest")
    for relative in data["protectedPaths"]:
        current = root / relative
        historical = _git(root, "show", f"{root_commit}:{relative}").stdout
        if not current.is_file() or current.read_bytes() != historical:
            raise ValueError(f"inherited historical record changed after export: {relative}")
    if _git(root, "cat-file", "-e", f"{data['sourceCommit']}^{{commit}}", allow_failure=True).returncode == 0:
        raise ValueError("public repository contains the private source commit")
    try:
        from scripts.closure_anchors import load_anchors
    except ModuleNotFoundError:
        from closure_anchors import load_anchors
    for anchor in load_anchors(root).values():
        for relative, checksum in anchor["protectedPaths"].items():
            current = root / safe_relative(relative)
            if not current.is_file() or digest(current) != checksum:
                raise ValueError(
                    f"public historical representation changed: {relative}"
                )
        for name in ("candidateCommit", "closureCommit"):
            if _git(root, "cat-file", "-e", f"{anchor[name]}^{{commit}}", allow_failure=True).returncode == 0:
                raise ValueError("public repository contains a private milestone commit")
    unreachable = _git(root, "fsck", "--unreachable", "--no-reflogs", allow_failure=True)
    if unreachable.returncode not in (0, 1) or b"unreachable " in unreachable.stdout + unreachable.stderr:
        raise ValueError("public repository contains unreachable objects")
    validate_addendum(root, data)
    return data


def validate_addendum(root: Path, base: dict | None = None) -> dict | None:
    """Bind post-root public files to one reachable, immutable snapshot."""
    root = root.resolve()
    path = root / ADDENDUM
    if not path.is_file():
        return None
    if base is None:
        base = load_manifest(root)
    payload = path.read_bytes()
    head = _git(root, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    return _validated_addendum(str(root), head, digest_bytes(payload),
                               digest(root / MANIFEST))


@lru_cache(maxsize=16)
def _validated_addendum(root_name: str, head: str, addendum_hash: str,
                        base_hash: str) -> dict:
    root = Path(root_name)
    path = root / ADDENDUM
    payload = path.read_bytes()
    if digest_bytes(payload) != addendum_hash:
        raise ValueError("public export addendum changed during validation")
    try:
        data = json.loads(payload)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("public export addendum is invalid") from exc
    if set(data) != {"recordVersion", "baseManifestSha256", "snapshotCommit",
                     "snapshotTree", "files", "limits"} \
            or data.get("recordVersion") != "0.1.0" \
            or data.get("baseManifestSha256") != base_hash \
            or not HEX40.fullmatch(str(data.get("snapshotCommit", ""))) \
            or not HEX40.fullmatch(str(data.get("snapshotTree", ""))):
        raise ValueError("public export addendum identity is invalid")
    if payload != canonical_manifest(data):
        raise ValueError("public export addendum is not canonical JSON")
    if not isinstance(data.get("limits"), list) or not data["limits"] \
            or any(not isinstance(item, str) or not item.strip() for item in data["limits"]):
        raise ValueError("public export addendum limits are required")
    files = data.get("files")
    if not isinstance(files, list) or not files:
        raise ValueError("public export addendum inventory is empty")
    base_paths = {item["path"] for item in load_manifest(root)["files"]}
    names = []
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise ValueError("public export addendum file record is invalid")
        relative = safe_relative(item.get("path", ""))
        if relative in base_paths or relative in {MANIFEST, ADDENDUM} \
                or not HEX64.fullmatch(str(item.get("sha256", ""))) \
                or type(item.get("size")) is not int or item["size"] < 0:
            raise ValueError(f"public export addendum file metadata is invalid: {relative}")
        names.append(relative)
    if names != sorted(set(names)):
        raise ValueError("public export addendum paths must be unique and sorted")
    introduced = _git(root, "log", "--format=%H", "--diff-filter=A", head,
                      "--", ADDENDUM).stdout.decode("ascii").splitlines()
    if len(introduced) != 1 \
            or _git(root, "show", f"{introduced[0]}:{ADDENDUM}").stdout != payload:
        raise ValueError("public export addendum must be unchanged since introduction")
    snapshot = data["snapshotCommit"]
    if _git(root, "merge-base", "--is-ancestor", snapshot, introduced[0],
            allow_failure=True).returncode != 0 \
            or _git(root, "merge-base", "--is-ancestor", snapshot, head,
                    allow_failure=True).returncode != 0 \
            or _git(root, "rev-parse", f"{snapshot}^{{tree}}").stdout.decode("ascii").strip() \
            != data["snapshotTree"]:
        raise ValueError("public export addendum snapshot is not in public ancestry")
    for item in files:
        relative = item["path"]
        blob = _git(root, "show", f"{snapshot}:{relative}").stdout
        if len(blob) != item["size"] or digest_bytes(blob) != item["sha256"] \
                or any(pattern.search(blob) for pattern in PROHIBITED_TEXT):
            raise ValueError(f"public export addendum payload is invalid: {relative}")
    return data


def manifest_record(root: Path, relative: str) -> dict:
    data = load_manifest(root)
    matches = [item for item in data["files"] if item["path"] == relative]
    if len(matches) != 1:
        raise ValueError(f"export manifest does not bind required file: {relative}")
    return matches[0]


def manifest_entry(root: Path, relative: str) -> dict:
    entry = manifest_record(root, relative)
    if digest(root / relative) != entry["sha256"]:
        raise ValueError(f"exported file changed: {relative}")
    return entry


def root_manifest_payload(root: Path, relative: str) -> bytes:
    """Read one manifest-bound file from an immutable public commit."""
    relative = safe_relative(relative)
    base = load_manifest(root)
    matches = [item for item in base["files"] if item["path"] == relative]
    if not matches:
        addendum = validate_addendum(root, base)
        matches = [item for item in addendum["files"] if item["path"] == relative] \
            if addendum is not None else []
        if len(matches) != 1:
            raise ValueError(f"export manifest does not bind required file: {relative}")
        entry = matches[0]
        payload = _git(root, "show", f"{addendum['snapshotCommit']}:{relative}").stdout
        if digest_bytes(payload) != entry["sha256"] or len(payload) != entry["size"]:
            raise ValueError(f"public snapshot payload does not match manifest: {relative}")
        return payload
    entry = matches[0]
    roots = _git(root, "rev-list", "--max-parents=0", "--all").stdout.decode("ascii").split()
    if len(roots) != 1:
        raise ValueError("public repository must have exactly one clean root")
    payload = _git(root, "show", f"{roots[0]}:{relative}").stdout
    if digest_bytes(payload) != entry["sha256"] or len(payload) != entry["size"]:
        raise ValueError(f"public root payload does not match manifest: {relative}")
    return payload
