# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only, bounded acquisition of the opt-in T024 literal patch domain.

This extraction ports the documented finite acquisition contract; it does not
import research code, replay plans, interpret prose or grant execution. Git diff
uses explicit context/algorithm/format settings. Its actual raw bytes are bound,
without claiming byte parity with legacy acquisition under nondefault config.
The coordinator supplies one shared Git budget, deadline and cancellation state.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha1, sha256
import os
from pathlib import Path
import re

from .git_process import (
    GitCommandBudget, GitCommandFailure, GitInfrastructureFailure, run_git,
)
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json

_BOUNDS = {
    "maxFiles": 8, "minOperations": 2, "maxOperations": 4,
    "maxPathsPerOperation": 2, "maxHunksPerPath": 2,
    "maxPatchLinesPerHunk": 128, "maxInitialLines": 64,
    "maxInitialBytes": 4096, "maxResultLines": 128, "maxResultBytes": 8192,
    "maxTextBytes": 65536, "maxTextLines": 96, "offeredOptions": 4,
    "maxPlanLength": 6,
}
_GIT_ID = re.compile(r"[0-9a-f]{40}\Z")
_PATH = re.compile(r"[a-z0-9][a-z0-9.-]*\.txt\Z")
_ZERO = "0" * 40
_ALLOWED_FAILURES = frozenset({
    "invalid-envelope", "unsupported-version", "unsupported-domain",
    "invalid-budget", "input-budget-exceeded", "source-unavailable",
    "source-drift", "unsupported-effect", "incomplete-observation",
    "declaration-mismatch", "invalid-ir", "ambiguous-anchor",
    "work-budget-exceeded", "deadline-exceeded", "cancelled", "internal-failure",
})


def _require(condition: bool, reason: str = "invalid-envelope") -> None:
    if not condition:
        raise ValueError(reason)


def _keys(value: object, fields: set[str]) -> None:
    _require(type(value) is dict and set(value) == fields)


def _id(value: object) -> None:
    _require(type(value) is str and 0 < len(value.encode("utf-8")) <= 64)
    _require(not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value))


def _oid(value: object, *, absent: bool = False) -> None:
    _require(type(value) is str and _GIT_ID.fullmatch(value) is not None)
    _require(absent or value != _ZERO)


def _path(value: object) -> None:
    _require(type(value) is str and _PATH.fullmatch(value) is not None,
             "unsupported-effect")


def _admit(source: Mapping[str, object], limits: Mapping[str, int]) -> dict:
    _require(isinstance(limits, Mapping) and set(limits) == set(_BOUNDS),
             "invalid-budget")
    _require(all(type(limits[k]) is int and limits[k] == v
                 for k, v in _BOUNDS.items()), "invalid-budget")
    # Reuse stdlib-v1 finite/depth/byte rules, then check this lane's exact schema.
    _require(isinstance(source, Mapping))
    data = parse_json(canonical(source))
    _keys(data, {"format", "task", "declaredEffects", "executionAuthorization"})
    _require(data["format"] == "t022-ingress-v1", "unsupported-version")
    _require(data["executionAuthorization"] is False)
    task = data["task"]
    _keys(task, {"request", "goal", "options", "optionOrder"})
    request = task["request"]
    _keys(request, {"gitAnalysisRequestVersion", "repository", "baseRevision", "operations"})
    _require(request["gitAnalysisRequestVersion"] == "0.1.0-alpha", "unsupported-version")
    _require(type(request["repository"]) is str and request["repository"] != "")
    _oid(request["baseRevision"])
    operations = request["operations"]
    _require(type(operations) is list and 2 <= len(operations) <= 4)
    names = list("abcd"[:len(operations)])
    actual = []
    for op in operations:
        _keys(op, {"instanceId", "attemptId", "source", "dependencies", "uncertainPaths"})
        _require(type(op["instanceId"]) is str and op["instanceId"] in names)
        actual.append(op["instanceId"])
        _id(op["attemptId"])
        _keys(op["source"], {"kind", "revision"})
        _require(op["source"]["kind"] == "commit", "unsupported-effect")
        _oid(op["source"]["revision"])
        _require(type(op["uncertainPaths"]) is list and not op["uncertainPaths"],
                 "incomplete-observation")
        deps = op["dependencies"]
        _require(type(deps) is list and all(type(d) is str and d in names
                 and d != op["instanceId"] for d in deps))
        _require(len(deps) == len(set(deps)))
    _require(len(set(actual)) == len(operations) and set(actual) == set(names))
    remaining, done = set(names), set()
    while remaining:
        ready = {op["instanceId"] for op in operations if op["instanceId"] in remaining
                 and set(op["dependencies"]) <= done}
        _require(bool(ready), "invalid-ir")
        remaining -= ready
        done |= ready
    goal = task["goal"]
    _require(type(goal) is list and 1 <= len(goal) <= 8)
    paths = []
    for entry in goal:
        _keys(entry, {"path", "blob"})
        _path(entry["path"])
        _oid(entry["blob"], absent=True)
        paths.append(entry["path"])
    _require(paths == sorted(set(paths)))
    options, order = task["options"], task["optionOrder"]
    _require(type(options) is dict and len(options) == 4)
    for option, seq in options.items():
        _id(option)
        _require(re.fullmatch(r"[a-z][a-z0-9]*", option) is not None)
        _require(seq is None or type(seq) is list and len(seq) <= 6
                 and all(type(n) is str and n in names for n in seq))
    _require(sum(seq is None for seq in options.values()) == 1)
    _require(type(order) is list and len(order) == 4
             and all(type(k) is str for k in order)
             and len(set(order)) == 4 and set(order) == set(options))
    declared = data["declaredEffects"]
    _keys(declared, set(names))
    for entries in declared.values():
        _require(type(entries) is list and 1 <= len(entries) <= 2)
        paths = []
        for entry in entries:
            _keys(entry, {"path", "before", "after"})
            _path(entry["path"])
            _oid(entry["before"], absent=True)
            _oid(entry["after"])
            paths.append(entry["path"])
        _require(paths == sorted(set(paths)))
    return data


def _unlinked(path: Path) -> None:
    """Reject symlink components, including a root supplied through a link."""
    _require(path.is_absolute(), "source-unavailable")
    _require(".." not in path.parts, "source-unavailable")
    for component in (path, *path.parents):
        _require(not component.is_symlink(), "source-unavailable")


def _repository(repository: str, owned_root: Path, budget: GitCommandBudget) -> Path:
    root, repo = Path(owned_root), Path(repository)
    _unlinked(root)
    _unlinked(repo)
    _require(root.is_dir() and repo.is_dir(), "source-unavailable")
    root, repo = root.resolve(strict=True), repo.resolve(strict=True)
    _require(repo != root and repo.is_relative_to(root), "source-unavailable")
    for child in (repo / ".owned-native-fixture", repo / ".git"):
        _unlinked(child)
    _require((repo / ".owned-native-fixture").is_file()
             and (repo / ".git").is_dir(), "source-unavailable")
    # Linked worktrees, alternates and links may widen observation beyond the
    # explicitly owned fixture; this first lane admits ordinary local repos.
    for entry in ("commondir", "objects/info/alternates", "objects/info/http-alternates"):
        _require(not (repo / ".git" / entry).exists(), "unsupported-effect")
    for entry in ("objects", "objects/pack", "objects/info", "config", "HEAD"):
        _unlinked(repo / ".git" / entry)
    pack = repo / ".git" / "objects" / "pack"
    if pack.is_dir():
        for item in pack.iterdir():
            _require(not item.is_symlink(), "source-unavailable")
    _require(isinstance(budget, GitCommandBudget) and budget.cancel_event is not None,
             "invalid-budget")
    _require(budget.temp_root.is_dir() and not budget.temp_root.is_symlink(),
             "invalid-budget")
    scratch = budget.temp_root.resolve(strict=True)
    _require(not scratch.is_relative_to(repo) and not repo.is_relative_to(scratch),
             "invalid-budget")
    return repo


def _env() -> dict[str, str]:
    # No inherited GIT_*, shell/DYLD overrides, user/system config or transport.
    return {"PATH": os.environ.get("PATH", os.defpath), "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull, "GIT_CONFIG_COUNT": "0",
            "GIT_NO_REPLACE_OBJECTS": "1", "GIT_GRAFT_FILE": os.devnull,
            "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "",
            "GIT_OPTIONAL_LOCKS": "0"}


class _Reader:
    def __init__(self, repo: Path, budget: GitCommandBudget,
                 remaining_ns: Callable[[str], int], checkpoint: Callable[[str, int], None]):
        self.repo, self.budget = repo, budget
        self.remaining_ns, self.checkpoint = remaining_ns, checkpoint

    def tick(self) -> None:
        self.checkpoint("acquisition", 0)

    def git(self, *args: str, allow_failure: bool = False):
        self.tick()
        remaining = self.remaining_ns("acquisition")
        _require(type(remaining) is int and remaining > 0, "deadline-exceeded")
        result = run_git(self.repo, (
            "-c", "core.hooksPath=" + os.devnull, "-c", "core.fsmonitor=false",
            "-c", "diff.external=", "-c", "core.quotePath=true", *args),
            env=_env(), budget=self.budget, allow_failure=allow_failure,
            command_timeout=min(30.0, remaining / 1_000_000_000))
        self.tick()
        return result

    def commit(self, oid: str) -> str:
        _unlinked(self.repo / ".git" / "objects" / oid[:2] / oid[2:])
        actual = self.git("rev-parse", "--verify", oid + "^{commit}").stdout.decode("ascii").strip()
        _require(actual == oid, "source-drift")
        return actual

    def content(self, oid: str) -> list[str] | None:
        if oid == _ZERO:
            return None
        _unlinked(self.repo / ".git" / "objects" / oid[:2] / oid[2:])
        count = int(self.git("cat-file", "-s", oid).stdout)
        _require(0 < count <= 4096, "unsupported-effect")
        value = self.git("cat-file", "blob", oid).stdout
        _require(len(value) == count and _blob(value) == oid, "source-drift")
        _require(b"\r" not in value and b"\0" not in value and value.endswith(b"\n"),
                 "unsupported-effect")
        text = value.decode("utf-8")
        lines = text.splitlines(keepends=True)
        _require(1 <= len(lines) <= 64 and all(line.endswith("\n")
                 and line.count("\n") == 1 and line.strip() for line in lines),
                 "unsupported-effect")
        return lines


def _blob(value: bytes) -> str:
    return sha1(b"blob " + str(len(value)).encode("ascii") + b"\0" + value).hexdigest()


def _hunks(patch: bytes, before: list[str] | None, after: list[str], tick) -> list[dict]:
    fragments: list[dict] = []
    current = None
    for line in patch.decode("utf-8").splitlines(keepends=True):
        tick()
        if line.startswith("@@ "):
            match = re.fullmatch(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n", line)
            _require(match is not None, "unsupported-effect")
            begin, count = int(match[1]) - 1, int(match[2] or "1")
            current = {"begin": begin, "end": begin + count, "old": [], "new": [],
                       "newBegin": int(match[3]) - 1, "newCount": int(match[4] or "1"),
                       "patchLines": []}
            fragments.append(current)
        elif current is not None:
            _require(line[:1] in (" ", "+", "-"), "unsupported-effect")
            current["patchLines"].append(line)
            if line[0] in " -":
                current["old"].append(line[1:])
            if line[0] in " +":
                current["new"].append(line[1:])
    _require(1 <= len(fragments) <= 2, "unsupported-effect")
    cursor, reconstructed = 0, []
    for h in fragments:
        tick()
        _require(1 <= len(h["patchLines"]) <= 128
                 and any(x[0] in "+-" for x in h["patchLines"]), "unsupported-effect")
        _require(h["new"] and h["newCount"] == len(h["new"]), "unsupported-effect")
        if before is None:
            _require(len(fragments) == 1 and h["begin"] == -1 and h["end"] == -1
                     and not h["old"] and h["newBegin"] == 0 and h["new"] == after,
                     "incomplete-observation")
            h.update(begin=0, end=0, old=None, atStart=True, atEnd=True)
            reconstructed = list(after)
        else:
            _require(cursor <= h["begin"] < h["end"] <= len(before)
                     and before[h["begin"]:h["end"]] == h["old"], "incomplete-observation")
            matches = [i for i in range(len(before) - len(h["old"]) + 1)
                       if before[i:i + len(h["old"])] == h["old"]]
            _require(matches == [h["begin"]], "ambiguous-anchor")
            _require(after[h["newBegin"]:h["newBegin"] + h["newCount"]] == h["new"],
                     "incomplete-observation")
            h.update(atStart=h["begin"] == 0, atEnd=h["end"] == len(before))
            reconstructed += before[cursor:h["begin"]] + h["new"]
            cursor = h["end"]
        del h["newBegin"], h["newCount"]
    if before is not None:
        reconstructed += before[cursor:]
    _require(reconstructed == after, "incomplete-observation")
    # Like retained T024 source validation, ensure earlier hunks have not made a
    # later runtime anchor ambiguous. This is source-domain admission, not a
    # replay of any offered plan or an oracle call.
    if before is not None:
        staged = list(before)
        for h in fragments:
            tick()
            trailing = bool(h["patchLines"][-1].startswith(" "))
            matches = [i for i in range(len(staged) - len(h["old"]) + 1)
                       if staged[i:i + len(h["old"])] == h["old"]
                       and (not h["atStart"] or i == 0)
                       and (not h["atEnd"] or trailing or i + len(h["old"]) == len(staged))]
            _require(len(matches) == 1, "ambiguous-anchor" if len(matches) > 1 else "invalid-ir")
            pos = matches[0]
            staged[pos:pos + len(h["old"])] = h["new"]
        _require(staged == after, "incomplete-observation")
    return fragments


def _project(data: dict, repo: Path, reader: _Reader) -> dict:
    task, request = data["task"], data["task"]["request"]
    base = reader.commit(request["baseRevision"])
    files, ops, sources, parsed, observed = {}, {}, {}, {}, {}
    for op in sorted(request["operations"], key=lambda row: row["instanceId"]):
        reader.tick()
        name = op["instanceId"]
        source = reader.commit(op["source"]["revision"])
        _require(reader.git("merge-base", "--is-ancestor", base, source,
                            allow_failure=True).returncode == 0, "source-drift")
        pieces = reader.git("diff", "--raw", "--no-abbrev", "--no-renames",
                            "--no-ext-diff", "--no-textconv", "-z", base, source).stdout.split(b"\0")
        _require(pieces[-1] == b"" and len(pieces) % 2 == 1
                 and 1 <= (len(pieces) - 1) // 2 <= 2, "unsupported-effect")
        changes, acquired, effects = [], [], []
        for i in range(0, len(pieces) - 1, 2):
            reader.tick()
            descriptor = pieces[i].decode("ascii").split()
            _require(len(descriptor) == 5 and descriptor[0].startswith(":"),
                     "incomplete-observation")
            oldmode, newmode, old, new, status = descriptor[0][1:], *descriptor[1:]
            _oid(old, absent=True)
            _oid(new, absent=True)
            path = pieces[i + 1].decode("utf-8")
            _path(path)
            _require((status == "A" and oldmode == "000000" and old == _ZERO
                      or status == "M" and oldmode == "100644" and old != _ZERO)
                     and newmode == "100644" and new != _ZERO, "unsupported-effect")
            before, after = reader.content(old), reader.content(new)
            _require(before != after and after is not None, "unsupported-effect")
            patch = reader.git("diff", "--binary", "--no-ext-diff", "--no-textconv",
                               "--no-renames", "--no-color", "--unified=3",
                               "--inter-hunk-context=0", "--diff-algorithm=myers",
                               "--src-prefix=a/", "--dst-prefix=b/", base, source,
                               "--", path).stdout
            hunks = _hunks(patch, before, after, reader.tick)
            _require(path not in files or files[path] == before, "source-drift")
            files[path] = before
            changes.append({"path": path, "old": old, "new": new, "hunks": hunks})
            acquired.append({"path": path, "old": old, "new": new,
                             "oldLines": before, "newLines": after, "hunks": hunks,
                             "patchSha256": sha256(patch).hexdigest()})
            effects.append({"path": path, "before": old, "after": new})
        _require([c["path"] for c in changes] == sorted({c["path"] for c in changes}),
                 "incomplete-observation")
        sources[name] = source
        ops[name] = {"dependencies": op["dependencies"], "changes": changes}
        parsed[name] = {"source": source, "dependencies": op["dependencies"], "changes": acquired}
        observed[name] = effects
    _require(len(files) <= 8 and {g["path"] for g in task["goal"]} == set(files),
             "invalid-ir")
    _require(observed == data["declaredEffects"], "declaration-mismatch")
    program = {"files": files, "goal": {g["path"]: g["blob"] for g in task["goal"]},
               "ops": ops, "plans": {k: task["options"][k] for k in task["optionOrder"]}}
    snapshot = {"base": base, "sources": sources, "operations": parsed,
                "taskDigest": digest(task), "semanticVersion": "t024-eof-context-v1"}
    reader.tick()
    return {"program": program,
            "binding": {"snapshot": snapshot, "snapshotDigest": digest(snapshot),
                        "executionAuthorization": False},
            "observedEffects": observed, "declaredEffects": data["declaredEffects"],
            "coverage": {"status": "complete", "paths": sorted(files), "operations": sorted(ops)}}


def acquire(source: Mapping[str, object], owned_root: Path, *,
            limits: Mapping[str, int], git_budget: GitCommandBudget,
            remaining_ns: Callable[[str], int],
            checkpoint: Callable[[str, int], None]) -> Mapping[str, object]:
    """Acquire one exact owned-fixture snapshot, or raise a sanitized ValueError.

    No writes are made to the source or parent scratch, and no budget/deadline is
    created or reset. Reacquisition must reuse the coordinator-owned context.
    The caller checks binding equality at handoff; a digest is not authorization.
    """
    try:
        checkpoint("acquisition", 0)
        data = _admit(source, limits)
        repo = _repository(data["task"]["request"]["repository"], owned_root, git_budget)
        reader = _Reader(repo, git_budget, remaining_ns, checkpoint)
        result = _project(data, repo, reader)
        # Recheck scope and immutable commit resolution before publishing.
        _repository(str(repo), owned_root, git_budget)
        reader.commit(data["task"]["request"]["baseRevision"])
        for op in data["task"]["request"]["operations"]:
            reader.commit(op["source"]["revision"])
        reader.tick()
        return freeze(result)
    except GitInfrastructureFailure as exc:
        reason = {"cancelled": "cancelled", "timeout": "deadline-exceeded",
                  "command-limit": "work-budget-exceeded", "output-limit": "work-budget-exceeded",
                  "scratch-limit": "work-budget-exceeded"}.get(exc.category, "source-unavailable")
        raise ValueError(reason) from None
    except GitCommandFailure:
        raise ValueError("source-unavailable") from None
    except InvalidDecision as exc:
        reason = str(exc) if str(exc) in _ALLOWED_FAILURES else "invalid-envelope"
        raise ValueError(reason) from None
    except (OSError, UnicodeError):
        raise ValueError("source-unavailable") from None
    except (KeyError, TypeError, AttributeError, RecursionError, OverflowError):
        raise ValueError("invalid-envelope") from None
    except ValueError as exc:
        if str(exc) in _ALLOWED_FAILURES:
            raise
        raise ValueError("invalid-envelope") from None
