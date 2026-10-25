# SPDX-License-Identifier: AGPL-3.0-only
"""``expand-ownership``: a declaration to AIM records and the pre-flight evidence block.

Read-only, local and offline. The only repository observation is the file list
and symlink targets of one resolved base commit, taken through the bounded Git
helpers of the Git adapter. A refusal prints the command-error object, writes
the diagnostic codes (never repository text) to standard error and exits 2.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile

from .analysis import analyze
from .git_adapter import InvalidGitAnalysis, _git, _repo_root, _resolve
from .git_process import GitCommandBudget, GitInfrastructureFailure
from . import ownership

HELP = "expand an ownership declaration into AIM records and pre-flight evidence (read-only)"
MAX_SYMLINK_TARGETS = 256
OVER_BOUND = {
    "input-too-large", "too-many-units", "too-many-paths", "string-too-long", "too-many-dependencies",
    "too-many-shared-resources", "too-many-exemptions", "diagnostics-truncated",
}
UNOBSERVABLE = {"unreadable-input"}


def add_parser(subparsers):
    parser = subparsers.add_parser("expand-ownership", help=HELP)
    parser.add_argument("input", type=Path, help="ownership declaration JSON")
    parser.add_argument("--repository", type=Path,
                        help="repository holding the declared base; without it the base tree is unavailable and every unit is partial")


class _Refusal(Exception):
    def __init__(self, code: str, rule: str = ""):
        self.code, self.rule = code, rule


def _environment() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    return env


def _read_tree(repository: Path, base: dict, temp: Path) -> tuple[ownership.BaseTree, str, str]:
    env = _environment()
    budget = GitCommandBudget(temp_root=temp, wall_seconds=30, max_commands=MAX_SYMLINK_TARGETS + 8)
    try:
        root = _repo_root(repository, env=env, budget=budget)
        commit = _resolve(root, base.get("commit") or base["ref"], env=env, budget=budget)
        if "ref" in base and "commit" in base and _resolve(root, base["ref"], env=env, budget=budget) != commit:
            raise _Refusal("ERR-MALFORMED-INPUT", "base-mismatch")
        listing = _git(root, "ls-tree", "-r", "-z", "--full-tree", commit, env=env, budget=budget)
        files: set[str] = set()
        links: dict[str, str] = {}
        for entry in listing.split(b"\0"):
            if not entry:
                continue
            header, _, name = entry.partition(b"\t")
            mode, _, sha = header.decode("ascii").split(" ")
            path = name.decode("utf-8")
            if mode in ("100644", "100755"):
                files.add(path)
            elif mode == "120000":
                if len(links) < MAX_SYMLINK_TARGETS:
                    links[path] = _git(root, "cat-file", "blob", sha, env=env, budget=budget).decode("utf-8")
                else:
                    links[path] = "/"  # absolute: stays unresolved, so the unit is partial
        return ownership.BaseTree(frozenset(files), links), commit, str(root)
    except (InvalidGitAnalysis, GitInfrastructureFailure, UnicodeDecodeError, ValueError):
        raise _Refusal("ERR-UNOBSERVABLE-SOURCE", "base-tree") from None


def _refusal(code: str, rule: str) -> int:
    print(json.dumps({"schemaVersion": "agent-braid-command-error/v0.1", "executionAuthorization": False,
                      "resultProduced": False, "errorCode": code, **({"rule": rule} if rule else {})},
                     sort_keys=True))
    return 2


def run(args) -> int:
    try:
        try:
            declaration = ownership.load_declaration_file(args.input)
        except ownership.DeclarationRefused as exc:
            for diagnostic in exc.diagnostics:
                print(f"{diagnostic.code} {diagnostic.where}".rstrip(), file=sys.stderr)
            first = exc.diagnostics[0].code
            code = ("ERR-OVER-BOUND" if first in OVER_BOUND else
                    "ERR-UNOBSERVABLE-SOURCE" if first in UNOBSERVABLE else "ERR-MALFORMED-INPUT")
            raise _Refusal(code, first) from None
        tree = commit = root = None
        if args.repository is not None and declaration.get("base"):
            with tempfile.TemporaryDirectory(prefix="ownership-") as temp:
                tree, commit, root = _read_tree(args.repository, declaration["base"], Path(temp))
        expansion = ownership.expand_declaration(
            declaration, tree, repo_root=root, pinned_commit=commit)
    except _Refusal as exc:
        return _refusal(exc.code, exc.rule)
    records = ownership.to_aim(expansion)
    print(json.dumps({"records": records, "preflight": ownership.build_preflight(expansion),
                      "analysis": analyze(records), "executionAuthorization": False},
                     sort_keys=True, indent=2))
    return 0
