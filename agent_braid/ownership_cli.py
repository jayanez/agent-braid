# SPDX-License-Identifier: AGPL-3.0-only
"""``expand-ownership``, ``check-ownership``, ``audit-isolation`` and ``report-recovery`` (SPEC-057).

Read-only, local and offline. ``expand-ownership`` turns a declaration into AIM
records and the pre-flight evidence block; its only repository observation is the
file list and symlink targets of one resolved base commit. ``check-ownership``
compares the declaration with the changes of committed or quiesced sources
(worktrees or commits, plus an optional shared working tree) and writes the
receipt to an explicit new private file. Both use the bounded Git helpers of the
Git adapter in-process, never the plugin MCP. A refusal prints the command-error
object, writes diagnostic codes (never repository text) to standard error, exits 2
and writes no result.

``audit-isolation`` and ``report-recovery`` print their result to standard output
and never launch the host binary: the operator supplies the host's session
listing from a file or standard input. They read Git with the same bounded
helpers, keep settings, session names, waiting text and working directories in
memory only, and output booleans, counts and closed enumerations.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from .analysis import analyze
from .git_adapter import InvalidGitAnalysis, _git, _git_result, _is_ancestor, _repo_root, _resolve, _text
from .git_process import (
    GitCommandBudget, GitCommandLimitExceeded, GitInfrastructureFailure, GitOutputLimitExceeded,
    GitScratchLimitExceeded,
)
from . import ownership

HELP = "expand an ownership declaration into AIM records and pre-flight evidence (read-only)"
AUDIT_HELP = "state isolation and base configuration observations (read-only)"
RECOVERY_HELP = "classify what stopped units left behind from a session listing and Git state (read-only)"
CHECK_HELP = "compare a declaration with committed or quiesced Git state and write a receipt (read-only)"
MAX_SYMLINK_TARGETS = 256
MAX_SOURCES = ownership.MAX_UNITS
MAX_FILE_BYTES = 8_000_000
OVER_BOUND_GIT = (GitCommandLimitExceeded, GitOutputLimitExceeded, GitScratchLimitExceeded)
SOURCE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]{0,63}?)=(worktree|commit):(.+)$", re.DOTALL)
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
    check = subparsers.add_parser("check-ownership", help=CHECK_HELP)
    check.add_argument("input", type=Path, help="ownership declaration JSON (with a base)")
    check.add_argument("--repository", type=Path, required=True, help="repository holding the declared base")
    check.add_argument("--source", action="append", default=[], metavar="UNIT=worktree:PATH|UNIT=commit:REV",
                       help="the committed or quiesced source of one unit; a unit without one is not-observed")
    check.add_argument("--shared-tree", type=Path,
                       help="a shared working tree: its changes are attributed to no unit")
    check.add_argument("--checkpoint", default="", help="checkpoint label recorded in the receipt")
    check.add_argument("--output", type=Path, required=True, help="new private file for the receipt; must not exist")
    audit = subparsers.add_parser("audit-isolation", help=AUDIT_HELP)
    audit.add_argument("--repository", type=Path, default=Path("."), help="repository to observe (default: current directory)")
    audit.add_argument("--settings", action="append", default=[], metavar="SCOPE=PATH",
                       help="a settings file of scope user, project or local; only worktree.baseRef and "
                            "worktree.bgIsolation are read")
    audit.add_argument("--agents-json", type=Path, help="host session listing as JSON; '-' reads standard input")
    audit.add_argument("--script", type=Path, help="workflow script text for the agent() isolation-option lint")
    recovery = subparsers.add_parser("report-recovery", help=RECOVERY_HELP)
    recovery.add_argument("input", type=Path, help="ownership declaration JSON (with a base)")
    recovery.add_argument("--repository", type=Path, required=True, help="repository holding the declared base")
    recovery.add_argument("--source", action="append", default=[], metavar="UNIT=worktree:PATH|UNIT=commit:REV",
                          help="the worktree or commit a unit left behind; a unit without one is unknown")
    recovery.add_argument("--agents-json", type=Path, help="host session listing as JSON; '-' reads standard input")


class _Refusal(Exception):
    def __init__(self, code: str, rule: str = "", unit_id: str | None = None):
        self.code, self.rule, self.unit_id = code, rule, unit_id


def _environment() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update({"LC_ALL": "C", "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"})
    return env


def _git_refusal(exc: Exception, rule: str, unit_id: str | None = None) -> _Refusal:
    over = isinstance(exc, OVER_BOUND_GIT) or (isinstance(exc, InvalidGitAnalysis) and "exceeds" in str(exc))
    code = "ERR-OVER-BOUND" if over else "ERR-UNOBSERVABLE-SOURCE"
    return _Refusal(code, rule, unit_id)


def _resolve_base(repository: Path, base: dict, env: dict, budget: GitCommandBudget) -> tuple[Path, str]:
    root = _repo_root(repository, env=env, budget=budget)
    commit = _resolve(root, base.get("commit") or base["ref"], env=env, budget=budget)
    if "ref" in base and "commit" in base and _resolve(root, base["ref"], env=env, budget=budget) != commit:
        raise _Refusal("ERR-MALFORMED-INPUT", "base-mismatch")
    return root, commit


def _read_tree(repository: Path, base: dict, temp: Path) -> tuple[ownership.BaseTree, str, str]:
    env = _environment()
    budget = GitCommandBudget(temp_root=temp, wall_seconds=30, max_commands=MAX_SYMLINK_TARGETS + 8)
    try:
        root, commit = _resolve_base(repository, base, env, budget)
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
    except (InvalidGitAnalysis, GitInfrastructureFailure, UnicodeDecodeError, ValueError) as exc:
        raise _git_refusal(exc, "base-tree") from None


def _refusal(exc: _Refusal) -> int:
    print(json.dumps(ownership.command_error(exc.code, unit_id=exc.unit_id, rule=exc.rule), sort_keys=True))
    return 2


def _load(path: Path) -> dict:
    try:
        return ownership.load_declaration_file(path)
    except ownership.DeclarationRefused as exc:
        for diagnostic in exc.diagnostics:
            print(f"{diagnostic.code} {diagnostic.where}".rstrip(), file=sys.stderr)
        first = exc.diagnostics[0].code
        code = ("ERR-OVER-BOUND" if first in OVER_BOUND else
                "ERR-UNOBSERVABLE-SOURCE" if first in UNOBSERVABLE else "ERR-MALFORMED-INPUT")
        raise _Refusal(code, first) from None


def _expand(args) -> int:
    declaration = _load(args.input)
    tree = commit = root = None
    if args.repository is not None and declaration.get("base"):
        with tempfile.TemporaryDirectory(prefix="ownership-") as temp:
            tree, commit, root = _read_tree(args.repository, declaration["base"], Path(temp))
    expansion = ownership.expand_declaration(declaration, tree, repo_root=root, pinned_commit=commit)
    records = ownership.to_aim(expansion)
    print(json.dumps({"records": records, "preflight": ownership.build_preflight(expansion),
                      "analysis": analyze(records), "executionAuthorization": False},
                     sort_keys=True, indent=2))
    return 0


# --- check-ownership ---------------------------------------------------------------


def _parse_sources(values: list[str], declaration: dict) -> dict[str, tuple[str, str]]:
    known = {unit["id"] for unit in declaration["units"]}
    sources: dict[str, tuple[str, str]] = {}
    for value in values:
        match = SOURCE.match(value)
        if match is None:
            raise _Refusal("ERR-MALFORMED-INPUT", "bad-source")
        unit_id, kind, target = match.groups()
        if target.startswith("-"):
            raise _Refusal("ERR-MALFORMED-INPUT", "bad-source")
        if unit_id not in known:
            raise _Refusal("ERR-MALFORMED-INPUT", "unknown-source-unit")
        if unit_id in sources:
            raise _Refusal("ERR-MALFORMED-INPUT", "duplicate-source-unit", unit_id)
        sources[unit_id] = (kind, target)
    return sources


def _busy(where: Path, env: dict, budget: GitCommandBudget) -> bool:
    lock = Path(_text(_git(where, "rev-parse", "--git-path", "index.lock", env=env, budget=budget), "lock path"))
    return (lock if lock.is_absolute() else where / lock).exists()


def _common_dir(where: Path, env: dict, budget: GitCommandBudget) -> Path:
    path = Path(_text(_git(where, "rev-parse", "--git-common-dir", env=env, budget=budget), "common directory"))
    return (path if path.is_absolute() else where / path).resolve()


def _kind(status: str, modes: tuple[str, str], binary: bool) -> str:
    if status == "D":
        return "deleted"
    if status in ("A", "M"):
        if "160000" in modes:
            return "submodule"
        if "120000" in modes:
            return "symlink"
        return "binary" if binary else ownership.WRITE
    return "unsupported"


def _tracked_changes(where: Path, base: str, tip: str | None, env: dict, budget: GitCommandBudget):
    """Tracked changes from the raw and numstat diffs (no renames); returns changes and the raw bytes."""
    tail = ("--no-ext-diff", "--no-textconv", "--no-renames", base, *([tip] if tip else []), "--")
    raw = _git(where, "diff", "--raw", "-z", *tail, env=env, budget=budget)
    numstat = _git(where, "diff", "--numstat", "-z", *tail, env=env, budget=budget)
    binary = set()
    for record in numstat.split(b"\0"):
        added, _, rest = record.partition(b"\t")
        if added == b"-":
            binary.add(rest.partition(b"\t")[2].decode("utf-8", "surrogateescape"))
    tokens = raw.split(b"\0")
    changes = []
    for index in range(0, len(tokens) - 1, 2):
        fields = tokens[index].decode("ascii").lstrip(":").split(" ")
        path = tokens[index + 1].decode("utf-8", "surrogateescape")
        changes.append(ownership.Change(_kind(fields[4][:1], (fields[0], fields[1]), path in binary), path))
    return changes, raw + numstat


def _untracked_changes(where: Path, env: dict, budget: GitCommandBudget):
    """Untracked, non-ignored paths of a worktree with a content digest for the snapshot."""
    listing = _git(where, "ls-files", "-z", "--others", "--exclude-standard", env=env, budget=budget)
    changes, digests = [], []
    for item in sorted(name for name in listing.split(b"\0") if name):
        path = item.decode("utf-8", "surrogateescape")
        candidate = where / os.fsdecode(item)
        if path.endswith("/"):
            kind, data = "submodule", b""
        elif candidate.is_symlink():
            kind, data = "symlink", os.readlink(candidate).encode("utf-8", "surrogateescape")
        elif candidate.is_file():
            with open(candidate, "rb") as handle:
                data = handle.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise _Refusal("ERR-OVER-BOUND", "untracked-file-size")
            kind = "binary" if b"\0" in data else ownership.WRITE
        else:
            kind, data = "unsupported", b""
        changes.append(ownership.Change(kind, path))
        digests.append(f"{path}\0{hashlib.sha256(data).hexdigest()}")
    return changes, "\n".join(digests).encode("utf-8", "surrogateescape")


def _observe_once(where: Path, base: str, tip: str, worktree: bool, env: dict,
                  budget: GitCommandBudget) -> ownership.Observation:
    changes, seen = _tracked_changes(where, base, None if worktree else tip, env, budget)
    digest = hashlib.sha256(tip.encode("ascii") + seen)
    if worktree:
        extra, content = _untracked_changes(where, env, budget)
        changes += extra
        digest.update(_git(where, "diff", "--no-ext-diff", "--no-textconv", "--binary", "--no-renames", base, "--",
                           env=env, budget=budget) + content)
    return ownership.Observation(tuple(changes), "sha256:" + digest.hexdigest())


def _observe_source(root: Path, base: str, kind: str, target: str, unit_id: str | None, env: dict,
                    budget: GitCommandBudget, roots: list[Path],
                    found: dict | None = None) -> ownership.Observation | str:
    """Two Git observations of one source; any difference, or a writer's lock, is a refusal."""
    worktree = kind == "worktree"
    try:
        if worktree:
            where = _repo_root(Path(target).expanduser().resolve(), env, budget)
            if _common_dir(where, env, budget) != _common_dir(root, env, budget):
                raise _Refusal("ERR-UNOBSERVABLE-SOURCE", "foreign-worktree", unit_id)
            roots.append(where)
            tip = _resolve(where, "HEAD", env, budget)
        else:
            where, tip = root, _resolve(root, target, env, budget)
        if found is not None:
            found.update(where=where, tip=tip)
        if not _is_ancestor(where, base, tip, env, budget):
            return "not-a-descendant-of-base"
        if worktree and _busy(where, env, budget):
            raise _Refusal("ERR-BUSY", "index-lock", unit_id)
        first = _observe_once(where, base, tip, worktree, env, budget)
        second = _observe_once(where, base, tip, worktree, env, budget)
        if worktree and _busy(where, env, budget):
            raise _Refusal("ERR-BUSY", "index-lock", unit_id)
    except (InvalidGitAnalysis, GitInfrastructureFailure, OSError, ValueError) as exc:
        raise _git_refusal(exc, "git-observation", unit_id) from None
    if first != second:
        raise _Refusal("ERR-UNSTABLE-SNAPSHOT", "changed-between-observations", unit_id)
    return first


def _write_new(path: Path, text: str, forbidden: list[Path]) -> None:
    target = Path(os.path.abspath(path))
    parent = target.parent.resolve()
    if not parent.is_dir():
        raise _Refusal("ERR-MALFORMED-INPUT", "output-parent")
    if any(parent == root or root in parent.parents for root in forbidden):
        raise _Refusal("ERR-MALFORMED-INPUT", "output-in-repository")
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    except FileExistsError:
        raise _Refusal("ERR-OUTPUT-EXISTS") from None
    except OSError:
        raise _Refusal("ERR-MALFORMED-INPUT", "output-path") from None
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def _check(args) -> int:
    declaration = _load(args.input)
    if not declaration.get("base"):
        raise _Refusal("ERR-MALFORMED-INPUT", "missing-base")
    if not ownership.checkpoint_label_ok(args.checkpoint):
        raise _Refusal("ERR-MALFORMED-INPUT", "bad-checkpoint")
    sources = _parse_sources(args.source, declaration)
    if os.path.lexists(args.output):
        raise _Refusal("ERR-OUTPUT-EXISTS")
    with tempfile.TemporaryDirectory(prefix="ownership-") as temp:
        tree, commit, root = _read_tree(args.repository, declaration["base"], Path(temp))
        expansion = ownership.expand_declaration(declaration, tree, repo_root=root, pinned_commit=commit)
        env = _environment()
        budget = GitCommandBudget(temp_root=Path(temp), wall_seconds=120, max_commands=1024)
        roots = [Path(root)]
        observations = {
            unit_id: _observe_source(Path(root), commit, kind, target, unit_id, env, budget, roots)
            for unit_id, (kind, target) in sorted(sources.items())
        }
        shared = None
        if args.shared_tree is not None:
            shared = _observe_source(Path(root), commit, "worktree", str(args.shared_tree), None, env, budget, roots)
            if isinstance(shared, str):
                raise _Refusal("ERR-UNOBSERVABLE-SOURCE", "shared-tree-not-descendant")
    receipt = ownership.build_receipt(declaration, expansion, observations, shared, checkpoint=args.checkpoint)
    _write_new(args.output, json.dumps(receipt, sort_keys=True, indent=2) + "\n", roots)
    print(json.dumps({"executionAuthorization": False, "snapshot": receipt["snapshot"]["digest"]}, sort_keys=True))
    return 0


# --- audit-isolation and report-recovery -------------------------------------------


def _read_bounded(path: Path | None, limit: int, *, stdin: bool = False) -> bytes | None:
    """At most ``limit + 1`` bytes of a file (or standard input for ``-``); ``None`` when unreadable."""
    try:
        if stdin and str(path) == "-":
            return sys.stdin.buffer.read(limit + 1)
        with open(path, "rb") as handle:
            return handle.read(limit + 1)
    except (OSError, ValueError):
        return None


def _listing(path: Path | None) -> ownership.AgentsListing | None:
    if path is None:
        return None
    raw = _read_bounded(path, ownership.MAX_AGENTS_BYTES, stdin=True)
    if raw is None:
        raise _Refusal("ERR-UNOBSERVABLE-SOURCE", "agents-json")
    try:
        return ownership.parse_agents_listing(raw)
    except ownership.ListingRefused as exc:
        raise _Refusal(exc.code, exc.rule) from None


def _context(temp: str, commands: int = 64) -> tuple[dict, GitCommandBudget]:
    return _environment(), GitCommandBudget(temp_root=Path(temp), wall_seconds=60, max_commands=commands)


def _git_facts(repository: Path, env: dict, budget: GitCommandBudget):
    """Git facts for the audit, or ``None`` when the repository cannot be observed."""
    try:
        root = _repo_root(repository, env=env, budget=budget)
        entries = [Path(os.fsdecode(item)[len("worktree "):])
                   for item in _git(root, "worktree", "list", "--porcelain", "-z", env=env, budget=budget).split(b"\0")
                   if item.startswith(b"worktree ")]
        paths = [os.path.realpath(entry) for entry in entries]
        main = paths[0] if paths else os.path.realpath(root)
        try:
            here = os.path.realpath(_repo_root(Path.cwd(), env=env, budget=budget))
        except InvalidGitAnalysis:
            here = None
        location = ("outside-repository" if here not in paths else
                    "main-worktree" if here == main else "linked-worktree")
        ahead = None
        default = _git_result(root, "symbolic-ref", "-q", "refs/remotes/origin/HEAD", env=env, budget=budget,
                              allow_failure=True)
        if default.returncode == 0:
            count = _git_result(root, "rev-list", "--count", f"{_text(default.stdout, 'origin default')}..HEAD",
                                env=env, budget=budget, allow_failure=True)
            ahead = int(_text(count.stdout, "count")) if count.returncode == 0 else None
        return ownership.GitFacts(len(paths), location, ahead), main, paths[1:]
    except (InvalidGitAnalysis, GitInfrastructureFailure, UnicodeDecodeError, ValueError):
        return None, None, ()


def _settings(values: list[str]) -> dict[str, dict[str, str] | None]:
    found: dict[str, dict[str, str] | None] = {}
    for value in values:
        scope, _, location = value.partition("=")
        if scope not in ownership.SETTINGS_SCOPES or not location or scope in found:
            raise _Refusal("ERR-MALFORMED-INPUT", "bad-settings")
        found[scope] = ownership.read_settings(_read_bounded(Path(location), ownership.MAX_SETTINGS_BYTES))
    return found


def _audit(args) -> int:
    script = None
    if args.script is not None:
        raw = _read_bounded(args.script, ownership.MAX_SCRIPT_BYTES)
        if raw is None:
            raise _Refusal("ERR-UNOBSERVABLE-SOURCE", "script")
        if len(raw) > ownership.MAX_SCRIPT_BYTES:
            raise _Refusal("ERR-OVER-BOUND", "script-too-large")
        script = raw.decode("utf-8", "replace")
    settings, listing = _settings(args.settings), _listing(args.agents_json)
    if listing is not None:  # compare real paths, as the worktree list does
        listing = listing._replace(sessions=tuple(
            s._replace(cwd=os.path.realpath(s.cwd)) if s.cwd else s for s in listing.sessions))
    with tempfile.TemporaryDirectory(prefix="ownership-") as temp:
        env, budget = _context(temp)
        git, main, linked = _git_facts(args.repository, env, budget)
    print(json.dumps(ownership.build_isolation_audit(git=git, settings=settings, listing=listing, main_root=main,
                                                      linked=linked, script=script), sort_keys=True, indent=2))
    return 0


_REASONS = {"ERR-BUSY": "busy", "ERR-UNSTABLE-SNAPSHOT": "unstable", "ERR-OVER-BOUND": "over-bound"}


def _evidence(root: Path, base: str, kind: str, target: str, unit_id: str, env: dict,
              budget: GitCommandBudget) -> tuple[ownership.UnitEvidence, str | None]:
    """Git evidence of one unit and the real path of its worktree; a source that cannot be observed is unknown."""
    worktree = kind == "worktree"
    seen: dict = {}
    try:
        observed = _observe_source(root, base, kind, target, unit_id, env, budget, [], seen)
    except _Refusal as exc:
        return ownership.UnitEvidence(None, _REASONS.get(exc.code, "unobservable")), None
    if isinstance(observed, str):
        return ownership.UnitEvidence(None, observed), None
    try:
        where, tip = seen["where"], seen["tip"]
        uncommitted = worktree and bool(_git(where, "status", "--porcelain=v1", "-z", "--untracked-files=all",
                                              env=env, budget=budget))
        ahead = tip != base
        published = ahead and bool(_git(where, "for-each-ref", "--count=1", "--contains", tip,
                                         "--format=%(refname)", "refs/remotes", env=env, budget=budget).strip())
    except (InvalidGitAnalysis, GitInfrastructureFailure, OSError, ValueError) as exc:
        reason = "over-bound" if _git_refusal(exc, "git-observation").code == "ERR-OVER-BOUND" else "unobservable"
        return ownership.UnitEvidence(None, reason), None
    return ownership.UnitEvidence(observed, None, uncommitted, ahead, published, worktree), \
        os.path.realpath(where) if worktree else None


def _match_sessions(listing: ownership.AgentsListing | None, places: dict[str, str]) -> dict[str, ownership.Session]:
    """Sessions whose working directory is a unit's worktree; several that disagree leave the state unknown."""
    if listing is None:
        return {}
    matched: dict[str, ownership.Session] = {}
    for unit_id, place in places.items():
        here = [s for s in listing.sessions if s.cwd and os.path.realpath(s.cwd) == place]
        if len(here) == 1:
            matched[unit_id] = here[0]
        elif here:
            states, kinds = {s.state for s in here}, {s.kind for s in here}
            matched[unit_id] = ownership.Session(
                place, states.pop() if len(states) == 1 else "unknown", kinds.pop() if len(kinds) == 1 else "unknown",
                tuple(sorted({name for s in here for name in s.drift})))
    return matched


def _recover(args) -> int:
    declaration = _load(args.input)
    if not declaration.get("base"):
        raise _Refusal("ERR-MALFORMED-INPUT", "missing-base")
    sources = _parse_sources(args.source, declaration)
    listing = _listing(args.agents_json)
    with tempfile.TemporaryDirectory(prefix="ownership-") as temp:
        _, commit, root = _read_tree(args.repository, declaration["base"], Path(temp))
        env, budget = _context(temp, 1024)
        evidence, places = {}, {}
        for unit in declaration["units"]:
            name = unit["id"]
            if name not in sources:
                evidence[name] = ownership.UnitEvidence(None, "no-source-supplied")
                continue
            kind, target = sources[name]
            evidence[name], place = _evidence(Path(root), commit, kind, target, name, env, budget)
            if place:
                places[name] = place
    print(json.dumps(ownership.build_recovery_report(declaration, evidence, listing, _match_sessions(listing, places)),
                     sort_keys=True, indent=2))
    return 0


def run(args) -> int:
    try:
        if args.command == "audit-isolation":
            return _audit(args)
        if args.command == "report-recovery":
            return _recover(args)
        return _check(args) if args.command == "check-ownership" else _expand(args)
    except _Refusal as exc:
        return _refusal(exc)
