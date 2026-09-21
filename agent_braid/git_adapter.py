# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only Git snapshots translated to AIM 0.2 records."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from .analysis import InvalidAnalysis, analyze, _canonical, _digest


REQUEST_VERSION = "0.1.0-alpha"
MAX_GIT_OUTPUT = 8_000_000


class InvalidGitAnalysis(InvalidAnalysis):
    """The Git request or observed repository state is unsupported."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidGitAnalysis(message)


def _git(cwd: Path, *args: str) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(cwd), *args], capture_output=True, check=False
    )
    if process.returncode:
        reason = process.stderr.decode("utf-8", "replace").strip()
        raise InvalidGitAnalysis(f"Git observation failed: {reason or args[0]}")
    _require(len(process.stdout) <= MAX_GIT_OUTPUT, "Git observation exceeds 8 MB")
    return process.stdout


def _decode(output: bytes, label: str) -> str:
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InvalidGitAnalysis(f"invalid UTF-8 in {label}") from exc


def _text(output: bytes, label: str) -> str:
    return _decode(output, label).strip()


def _mode(output: bytes, label: str) -> str | None:
    if not output:
        return None
    entry = output.split(b"\0", 1)[0]
    header, separator, _ = entry.partition(b"\t")
    _require(bool(separator), f"malformed {label}")
    mode = header.split(b" ", 1)[0]
    try:
        value = mode.decode("ascii")
    except UnicodeDecodeError as exc:
        raise InvalidGitAnalysis(f"invalid mode in {label}") from exc
    _require(value.isdigit(), f"malformed mode in {label}")
    return value


def _repo_root(path: Path) -> Path:
    root = Path(_text(_git(path, "rev-parse", "--show-toplevel"), "repository root"))
    _require(root.is_absolute() and root.is_dir(), "repository must be a non-bare worktree")
    return root.resolve()


def _common_identity(root: Path, base: str) -> str:
    roots = _text(_git(root, "rev-list", "--max-parents=0", base), "root commits").splitlines()
    _require(bool(roots), "repository has no root commit")
    return hashlib.sha256("\n".join(sorted(roots)).encode()).hexdigest()


def _resolve(root: Path, revision: str) -> str:
    _require(isinstance(revision, str) and revision.strip(), "invalid Git revision")
    value = _text(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"), "revision")
    _require(len(value) == 40 and all(char in "0123456789abcdef" for char in value),
             "revision did not resolve to a commit")
    return value


def _is_ancestor(root: Path, base: str, source: str) -> bool:
    process = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", base, source],
        capture_output=True, check=False,
    )
    _require(process.returncode in {0, 1}, "Git ancestry observation failed")
    return process.returncode == 0


def _parse_name_status(output: bytes) -> list[tuple[str, str]]:
    parts = output.split(b"\0")
    if parts and parts[-1] == b"":
        parts.pop()
    _require(len(parts) % 2 == 0, "malformed Git name-status output")
    changes = []
    for index in range(0, len(parts), 2):
        status = _decode(parts[index], "change status")
        path = _decode(parts[index + 1], "changed path")
        _require(path and not path.startswith("/") and "\x00" not in path,
                 "unsafe changed path")
        changes.append((status, path))
    return changes


def _snapshot(root: Path, base: str, source: dict) -> tuple[list[tuple[str, str]], str, str]:
    kind = source.get("kind")
    _require(set(source) == ({"kind", "revision"} if kind == "commit" else
                             {"kind", "path"}), "invalid Git source")
    if kind == "commit":
        resolved = _resolve(root, source["revision"])
        _require(_is_ancestor(root, base, resolved),
                 "base revision is not an ancestor of the commit source")
        raw = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--name-status", "-z",
                   "--no-renames", base, resolved, "--")
        payload = _git(root, "diff", "--no-ext-diff", "--no-textconv", "--binary",
                       "--no-renames", base, resolved, "--")
        changes = _parse_name_status(raw)
        classified = []
        for status, path in changes:
            if status in {"A", "M"}:
                mode = _mode(_git(root, "ls-tree", "-z", resolved, "--", path), "tree entry")
                if mode in {"120000", "160000"}:
                    status = "B"
                else:
                    content = _git(root, "show", f"{resolved}:{path}")
                    if b"\0" in content:
                        status = "B"
            classified.append((status, path))
        changes = classified
        return changes, resolved, hashlib.sha256(payload).hexdigest()
    _require(kind == "worktree", "unsupported Git source kind")
    worktree = _repo_root(Path(source["path"]).expanduser().resolve())
    head = _resolve(worktree, "HEAD")
    _require(_is_ancestor(worktree, base, head),
             "base revision is not an ancestor of the worktree HEAD")
    common_root = _text(_git(root, "rev-parse", "--git-common-dir"), "common directory")
    common_worktree = _text(_git(worktree, "rev-parse", "--git-common-dir"), "common directory")
    common_root_path = (root / common_root).resolve() if not Path(common_root).is_absolute() else Path(common_root).resolve()
    common_worktree_path = ((worktree / common_worktree).resolve()
                            if not Path(common_worktree).is_absolute() else Path(common_worktree).resolve())
    _require(common_root_path == common_worktree_path,
             "worktree does not belong to the declared repository")
    raw = _git(worktree, "diff", "--no-ext-diff", "--no-textconv", "--name-status", "-z",
               "--no-renames", base, "--")
    untracked = _git(worktree, "ls-files", "-z", "--others", "--exclude-standard")
    changes = _parse_name_status(raw)
    untracked_paths = [_decode(item, "untracked path") for item in untracked.split(b"\0") if item]
    changes.extend(("A", path) for path in untracked_paths)
    classified = []
    for status, path in changes:
        candidate = worktree / path
        if status in {"A", "M"}:
            mode = _mode(
                _git(worktree, "ls-files", "--stage", "-z", "--", path),
                "index entry",
            )
            if candidate.is_symlink() or mode in {"120000", "160000"}:
                status = "B"
            elif candidate.is_file():
                resolved_candidate = candidate.resolve()
                _require(resolved_candidate.is_relative_to(worktree), "changed path escapes worktree")
                data = resolved_candidate.read_bytes()
                _require(len(data) <= MAX_GIT_OUTPUT, "changed file exceeds 8 MB")
                if b"\0" in data:
                    status = "B"
            else:
                status = "B"
        classified.append((status, path))
    changes = classified
    payload = _git(worktree, "diff", "--no-ext-diff", "--no-textconv", "--binary",
                   "--no-renames", base, "--")
    hashes = []
    for name in sorted(untracked_paths):
        candidate = worktree / name
        if candidate.is_symlink():
            data = os.readlink(candidate).encode("utf-8", "surrogateescape")
        else:
            candidate = candidate.resolve()
            _require(candidate.is_relative_to(worktree) and candidate.is_file(),
                     "unsafe or non-file untracked path")
            data = candidate.read_bytes()
        _require(len(data) <= MAX_GIT_OUTPUT, "untracked file exceeds 8 MB")
        hashes.append((name, hashlib.sha256(data).hexdigest()))
    fingerprint = hashlib.sha256(payload + _canonical(hashes)).hexdigest()
    return changes, f"worktree:{head}", fingerprint


def _record(operation: dict, repo_id: str, base: str, root: Path) -> tuple[dict, dict]:
    required = {"instanceId", "attemptId", "source", "dependencies", "uncertainPaths"}
    _require(set(operation) == required, "invalid Git operation fields")
    for name in ("instanceId", "attemptId"):
        _require(isinstance(operation[name], str) and operation[name].strip(), f"invalid {name}")
    dependencies = operation["dependencies"]
    uncertain = operation["uncertainPaths"]
    _require(isinstance(dependencies, list) and all(isinstance(x, str) and x for x in dependencies),
             "invalid dependencies")
    _require(isinstance(uncertain, list) and all(isinstance(x, str) and x for x in uncertain),
             "invalid uncertainPaths")
    before = _snapshot(root, base, operation["source"])
    after = _snapshot(root, base, operation["source"])
    _require(before == after, "Git source changed during observation")
    changes, resolved, snapshot = before
    effects = []
    partial = False
    for status, path in sorted(changes, key=lambda item: (item[1], item[0])):
        resource = f"git://{repo_id}/{path}"
        if path in uncertain or status not in {"A", "M", "D"}:
            resource = f"git-unsupported://{repo_id}/{path}?operation={operation['instanceId']}"
            kind, partial = "unknown", True
        elif status == "D":
            resource = f"git-unsupported://{repo_id}/{path}?operation={operation['instanceId']}"
            kind, partial = "unknown", True
        else:
            kind = "write"
        effects.append({"kind": kind, "resource": resource})
    if uncertain:
        partial = True
    observation = {
        "base": base, "resolvedSource": resolved, "snapshot": f"sha256:{snapshot}",
        "changes": changes, "uncertainPaths": sorted(uncertain),
    }
    record = {
        "aimVersion": "0.2.0-draft",
        "instanceId": operation["instanceId"],
        "attemptId": operation["attemptId"],
        "definition": {"id": "git-change-set", "digest": _digest(observation)},
        "inputDigest": _digest({"operation": operation, "observation": observation}),
        "dependencies": dependencies,
        "readVersions": {},
        "effects": {
            "declared": [], "inferred": [], "observed": effects,
            "coverage": {
                "status": "partial" if partial else "complete",
                "domain": "Git tracked and non-ignored untracked path mutations",
                "method": "read-only Git snapshot",
            },
        },
        "evidence": [{
            "property": "independence", "method": "declared",
            "domain": "syntactic Git path identity only",
            "assumptions": ["Git observations are stable", "Hidden semantic effects are outside coverage"],
            "observationContract": "Resolved commits, diff bytes, and untracked content hashes",
            "executionContract": "No execution authorization; read-only analysis only",
            "assuranceClass": 1,
        }],
    }
    return record, observation


def analyze_git_with_provenance(value: object) -> tuple[dict, dict]:
    """Return a report plus its separate, structured Git observation artifact."""
    _require(isinstance(value, dict), "Git analysis request must be an object")
    _require(set(value) == {"gitAnalysisRequestVersion", "repository", "baseRevision", "operations"},
             "invalid Git analysis request fields")
    _require(value["gitAnalysisRequestVersion"] == REQUEST_VERSION,
             "unsupported Git analysis request version")
    _require(isinstance(value["repository"], str) and value["repository"].strip(),
             "invalid repository")
    root = _repo_root(Path(value["repository"]).expanduser().resolve())
    base = _resolve(root, value["baseRevision"])
    operations = value["operations"]
    _require(isinstance(operations, list) and len(operations) >= 2,
             "at least two Git operations are required")
    repo_id = _common_identity(root, base)
    records, observations = [], []
    for operation in operations:
        _require(isinstance(operation, dict), "Git operations must be objects")
        record, observation = _record(operation, repo_id, base, root)
        records.append(record)
        observations.append((operation["instanceId"], observation))
    report = analyze({
        "analysisInputVersion": "0.1.0-alpha",
        "source": {"kind": "git-worktree-adapter", "description": "Stable read-only Git snapshots"},
        "operations": records,
    })
    report["limits"].append(
        "Git coverage is syntactic and excludes ignored files, hidden effects, and undeclared semantics."
    )
    report["analysisId"] = _digest({**report, "analysisId": None})
    provenance = {
        "gitAnalysisProvenanceVersion": REQUEST_VERSION,
        "reportInputDigest": report["inputDigest"],
        "repositoryId": f"sha256:{repo_id}",
        "baseCommit": base,
        "operations": [
            {
                "instanceId": identifier,
                "resolvedSource": observation["resolvedSource"],
                "snapshot": observation["snapshot"],
                "changes": [
                    {"status": status, "path": path}
                    for status, path in observation["changes"]
                ],
                "uncertainPaths": observation["uncertainPaths"],
            }
            for identifier, observation in sorted(observations)
        ],
        "observationContract": "Resolved commits, read-only diff bytes, and non-ignored untracked content hashes.",
        "executionAuthorization": False,
    }
    return report, provenance


def analyze_git(value: object) -> dict:
    """Analyze stable Git snapshots and discard the separate provenance artifact."""
    return analyze_git_with_provenance(value)[0]
