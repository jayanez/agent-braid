# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic fixture repositories and a Node runner for the braid-gate tests.

Truth labels are written here as literals before any analyzer or Git output is
read; tests compare tool output against them and never derive them from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "integrations/agent-braid/plugin/workflows/braid-gate.js"
HARNESS = ROOT / "tests/fixtures/claude_workflow_gate/harness.mjs"
RESULT_SCHEMA = ROOT / "specs/052-claude-workflow-gate/contracts/braid-gate-result.schema.json"
ARGS_SCHEMA = ROOT / "specs/052-claude-workflow-gate/contracts/braid-gate-args.schema.json"
WORKSPACE_ID = "0123456789abcdef0123456789abcdef"
_DATE = "2026-01-01T00:00:00+00:00"


def git_env() -> dict[str, str]:
    env = dict(os.environ)
    for name in list(env):
        if name.startswith("GIT_"):
            del env[name]
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_AUTHOR_NAME": "Fixture", "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture", "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": _DATE, "GIT_COMMITTER_DATE": _DATE,
    })
    return env


def git(repo, *args: str, check: bool = True, input: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
                          env=git_env(), capture_output=True, check=check, input=input)


def git_out(repo, *args: str) -> str:
    return git(repo, *args).stdout.decode().strip()


def git_version() -> str | None:
    try:
        text = subprocess.run(["git", "version"], capture_output=True, check=True).stdout.decode().strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return text


def supports_merge_tree_write_tree() -> bool:
    """True when the installed Git accepts `merge-tree --write-tree` (2.38+)."""
    text = git_version() or ""
    parts = text.replace("git version ", "").split(".")
    try:
        return (int(parts[0]), int(parts[1])) >= (2, 38)
    except (ValueError, IndexError):
        return False


def node_binary() -> str | None:
    return shutil.which("node")


def node_version() -> str | None:
    binary = node_binary()
    if binary is None:
        return None
    return subprocess.run([binary, "--version"], capture_output=True, check=True).stdout.decode().strip()


@dataclass(frozen=True)
class Case:
    """One pair of corpus branches with a file-level truth label."""

    name: str
    left: str
    right: str
    # Literal truth, fixed before any tool runs.
    shared_file: bool            # both sides touch one path
    analyzer: str                # expected analyzer class
    merge_tree: str              # expected `merge-tree --write-tree` result: clean | conflicted


@dataclass
class Corpus:
    repo: Path
    base: str
    shas: dict[str, str]
    cases: list[Case] = field(default_factory=list)


_A = "".join(f"line {i}\n" for i in range(1, 13))
_E = "".join(f"rename candidate line {i}\n" for i in range(1, 13))

# (left, right, shared_file, analyzer, merge_tree). Written before any tool runs.
TRUTH = [
    Case("disjoint-files", "ind1", "ind2", False, "independent-candidate", "clean"),
    Case("same-file-different-hunks", "hunkA", "hunkB", True, "conflicting", "clean"),
    Case("same-hunk", "sameA", "sameB", True, "conflicting", "conflicted"),
    Case("delete-versus-modify", "del", "mod", True, "unknown", "conflicted"),
    Case("rename-versus-modify", "ren", "modE", True, "unknown", "clean"),
    Case("binary-versus-disjoint", "bin1", "ind1", False, "unknown", "clean"),
    Case("symlink-versus-disjoint", "sym", "ind2", False, "unknown", "clean"),
    Case("untouched-pair", "solo1", "solo2", False, "independent-candidate", "clean"),
]


def _write(repo: Path, relative: str, data: bytes | str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())


def _commit(repo: Path, message: str) -> str:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--allow-empty", "-m", message)
    return git_out(repo, "rev-parse", "HEAD")


def _branch(repo: Path, name: str, base: str, edit) -> str:
    git(repo, "checkout", "-q", "-B", name, base)
    edit(repo)
    return _commit(repo, name)


def init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    return path


def build_corpus(parent: Path) -> Corpus:
    """Build the known-answer corpus repository under `parent` (deterministic)."""
    repo = init_repo(parent / "corpus")
    _write(repo, "seed.txt", "seed\n")
    seed = _commit(repo, "seed")
    for name, data in {"a.txt": _A, "b.txt": "b\n", "c.txt": "c\n", "d.txt": "d\n", "e.txt": _E,
                       "bin.dat": b"\x00\x01\x02\x03", "dir/x.txt": "x\n"}.items():
        _write(repo, name, data)
    (repo / "link").symlink_to("a.txt")
    base = _commit(repo, "base")
    shas: dict[str, str] = {"seed": seed, "base": base}

    def replace_line(name, number, text):
        def edit(r):
            lines = (r / name).read_text().splitlines(keepends=True)
            lines[number - 1] = text + "\n"
            (r / name).write_text("".join(lines))
        return edit

    def rename_e(r):
        git(r, "mv", "e.txt", "f.txt")

    def retarget(r):
        (r / "link").unlink()
        (r / "link").symlink_to("b.txt")

    branches = {
        "ind1": lambda r: _write(r, "b.txt", "b changed by ind1\n"),
        "ind2": lambda r: _write(r, "c.txt", "c changed by ind2\n"),
        "hunkA": replace_line("a.txt", 1, "line 1 by A"),
        "hunkB": replace_line("a.txt", 12, "line 12 by B"),
        "sameA": replace_line("a.txt", 6, "line 6 by A"),
        "sameB": replace_line("a.txt", 6, "line 6 by B"),
        "del": lambda r: (r / "d.txt").unlink(),
        "mod": lambda r: _write(r, "d.txt", "d changed\n"),
        "ren": rename_e,
        "modE": replace_line("e.txt", 12, "rename candidate line 12 changed"),
        "bin1": lambda r: _write(r, "bin.dat", b"\x00\x09\x08\x07"),
        "sym": retarget,
        "solo1": lambda r: _write(r, "n1.txt", "new one\n"),
        "solo2": lambda r: _write(r, "n2.txt", "new two\n"),
        "equal": lambda r: None,
    }
    for name, edit in branches.items():
        if name == "equal":
            git(repo, "branch", "-f", "equal", base)
            shas[name] = base
        else:
            shas[name] = _branch(repo, name, base, edit)
    # A commit that does not descend from the base: a sibling of the base.
    shas["oldside"] = _branch(repo, "oldside", seed, lambda r: _write(r, "old.txt", "old\n"))
    git(repo, "checkout", "-q", "main")
    git(repo, "reset", "-q", "--hard", base)
    return Corpus(repo=repo, base=base, shas=shas, cases=list(TRUTH))


def build_many(corpus: Corpus, count: int, prefix: str = "m") -> list[str]:
    """Add `count` branches, each adding one unique file; return their names."""
    names = []
    for index in range(1, count + 1):
        name = f"{prefix}{index}"
        corpus.shas[name] = _branch(corpus.repo, name, corpus.base,
                                    lambda r, i=index: _write(r, f"many/f{i}.txt", f"file {i}\n"))
        names.append(name)
    git(corpus.repo, "checkout", "-q", "main")
    return names


def workspace_row(repo: Path, results: Path, *, identifier: str = WORKSPACE_ID,
                  runtime_enabled: bool = False, grant_store: str | None = None) -> dict:
    return {"workspaceId": identifier, "sourceRoot": str(repo.resolve()),
            "resultRoot": str(results.resolve()), "runtimeEnabled": runtime_enabled,
            "grantStore": grant_store, "worktreeRoots": []}


def run_gate(scenario: dict, *, timeout: int = 600) -> dict:
    """Run the workflow under Node with substituted agents; return the harness record."""
    binary = node_binary()
    if binary is None:
        raise RuntimeError("node is not available")
    scenario = {"script": str(WORKFLOW), **scenario, "python": sys.executable, "projectRoot": str(ROOT)}
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "scenario.json"
        path.write_text(json.dumps(scenario))
        done = subprocess.run([binary, str(HARNESS), str(path)], capture_output=True, text=True,
                              timeout=timeout, cwd=ROOT)
    if done.returncode != 0:
        raise RuntimeError(f"harness failed ({done.returncode}): {done.stderr[-2000:]}")
    return json.loads(done.stdout)
