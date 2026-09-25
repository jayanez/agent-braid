# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only admission check for a proposed M2 real-repository experiment.

This checker does not run repository code, prepare patches, or authorize an
experiment. It only binds a proposed corpus to immutable local Git objects.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess


OID = re.compile(r"[0-9a-f]{40}\Z")
PR_URL = re.compile(r"https://github\.com/jayanez/agent-braid/pull/[1-9][0-9]*\Z")
VERSION = "0.1.0-draft"
PUBLIC_ROOT = "9b84467d54444138db8c000f442d9aea6040cab2"


class InvalidRealWorkloadManifest(ValueError):
    """The corpus is malformed, stale, or not locally reproducible."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidRealWorkloadManifest(message)


def _git(repository: Path, *args: str, allow_failure: bool = False) -> str:
    environment = os.environ.copy()
    environment.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    result = subprocess.run(
        ["git", "-C", str(repository), "-c", "core.hooksPath=/dev/null", *args],
        env=environment, capture_output=True, check=False, timeout=10,
    )
    if result.returncode and not allow_failure:
        raise InvalidRealWorkloadManifest(f"Git preflight failed: {args[0]}")
    return result.stdout.decode("ascii", "strict").strip() if result.returncode == 0 else ""


def validate_manifest(value: object, repository: Path) -> dict:
    """Validate identity and ancestry; return a non-authorizing preflight result."""
    return _validate_manifest(value, repository, PUBLIC_ROOT)


def _validate_manifest(value: object, repository: Path, expected_public_root: str) -> dict:
    """Testable core with an injected root for isolated synthetic repositories."""
    _require(isinstance(value, dict), "manifest must be an object")
    _require(set(value) == {"version", "repository", "baseCommit", "targetRef",
                            "operations", "validationProfile"}, "manifest fields are invalid")
    _require(value["version"] == VERSION, "manifest version is unsupported")
    _require(value["repository"] == "jayanez/agent-braid", "repository identity is unsupported")
    base = value["baseCommit"]
    _require(isinstance(base, str) and OID.fullmatch(base), "baseCommit must be immutable")
    _require(value["targetRef"] == "refs/heads/develop", "targetRef must be develop")
    _require(value["validationProfile"] == "m2-real-read-only-v1",
             "validation profile is unsupported")
    operations = value["operations"]
    _require(isinstance(operations, list) and 2 <= len(operations) <= 3,
             "two or three workstream commits are required")
    identifiers: set[str] = set()
    commits: set[str] = set()
    urls: set[str] = set()
    for item in operations:
        _require(isinstance(item, dict) and set(item) == {
            "instanceId", "sourceCommit", "workstreamUrl", "dependencies"},
            "operation fields are invalid")
        identifier = item["instanceId"]
        commit = item["sourceCommit"]
        url = item["workstreamUrl"]
        dependencies = item["dependencies"]
        _require(isinstance(identifier, str)
                 and re.fullmatch(r"[a-z][a-z0-9-]{0,63}", identifier)
                 and identifier not in identifiers, "instanceId is invalid or repeated")
        _require(isinstance(commit, str) and OID.fullmatch(commit)
                 and commit not in commits and commit != base,
                 "sourceCommit is invalid or repeated")
        _require(isinstance(url, str) and PR_URL.fullmatch(url) and url not in urls,
                 "workstreamUrl must identify a distinct repository PR")
        _require(isinstance(dependencies, list) and not dependencies,
                 "first real-workload profile requires independent workstreams")
        identifiers.add(identifier)
        commits.add(commit)
        urls.add(url)
    _require(repository.is_dir(), "repository directory is unavailable")
    _require(_git(repository, "rev-parse", "--is-inside-work-tree") == "true",
             "repository must be a Git worktree")
    _require(_git(repository, "remote", "get-url", "origin", allow_failure=True) in {
        "https://github.com/jayanez/agent-braid.git",
        "https://github.com/jayanez/agent-braid",
        "git@github.com:jayanez/agent-braid.git",
    }, "origin does not identify the public repository")
    _require(_git(repository, "rev-parse", "--verify", "refs/heads/develop^{commit}") == base,
             "target branch has moved from the pinned base")
    _require(_git(repository, "rev-list", "--max-parents=0", base).splitlines()
             == [expected_public_root], "base is not from the public repository root")
    for commit in sorted(commits):
        _require(_git(repository, "rev-parse", "--verify", f"{commit}^{{commit}}",
                      allow_failure=True) == commit,
                 "source commit is unavailable")
        _require(_git(repository, "merge-base", base, commit, allow_failure=True) == base,
                 "source commit does not descend from the pinned base")
    ordered_commits = sorted(commits)
    for index, left in enumerate(ordered_commits):
        for right in ordered_commits[index + 1:]:
            _require(_git(repository, "merge-base", left, right) not in {left, right},
                     "source commits must be separate workstreams")
    return {
        "status": "preflight-valid",
        "baseCommit": base,
        "sourceCommits": sorted(commits),
        "validationProfile": value["validationProfile"],
        "executionAuthorization": False,
        "projectValidationExecuted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repository", type=Path, required=True)
    args = parser.parse_args()
    try:
        value = json.loads(args.manifest.read_text())
        print(json.dumps(validate_manifest(value, args.repository), sort_keys=True, indent=2))
    except (OSError, json.JSONDecodeError, InvalidRealWorkloadManifest,
            subprocess.TimeoutExpired, UnicodeError) as exc:
        parser.exit(1, f"Real-workload preflight failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
