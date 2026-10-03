# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in, authorized serial Git execution in an owned persistent directory.

Only fixed text patches and Git plumbing are admitted. No source ref, checkout,
repository code or external effect is executed. See SPEC-020 for trust limits.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import os
from pathlib import Path
import stat
import shutil
import tempfile
import threading
import hashlib
import ctypes
import errno
import sys

from .analysis import _canonical, _digest
from .git_adapter import analyze_git_with_provenance
from .git_process import GitCommandBudget, GitCommandFailure
from .git_runtime_process import run_owned_git
from .git_replay import (
    OID, _patches, _sanitized_environment, _supported_operations,
    _mark_unsupported_binary_patches, _topological_orders, _validate_request,
)
from research.lab.model import loads

try:
    import fcntl
except ImportError:  # Windows is explicitly outside this increment.
    fcntl = None

VERSION = "0.1.0-alpha"
OBSERVATION = "runtime-private-tracked-tree-v1"
EXECUTION = "authorized-serial-index-patch-v1"
RESULT_REF = "refs/heads/result"
LIMITS = {"operations": 4, "changedPaths": 16, "patchBytes": 256 * 1024,
          "wallSeconds": 60, "gitCommands": 256, "outputBytes": 8 * 1024 * 1024,
          "commandOutputBytes": 2 * 1024 * 1024, "scratchBytes": 64 * 1024 * 1024,
          "childAddressSpaceBytes": None}
MAX_RECORD_BYTES = 1024 * 1024
_OWNERSHIP_FD: ContextVar[int | None] = ContextVar("runtime_ownership_fd", default=None)


class InvalidGitRuntime(ValueError):
    """Invalid input, unacknowledged authority, or unverified private state."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise InvalidGitRuntime(reason)


def _git(repo: Path, env: dict, budget: GitCommandBudget, *args: str,
         input_bytes: bytes | None = None) -> bytes:
    try:
        return run_owned_git(repo, ("-c", "core.hooksPath=/dev/null", "-c",
                             "core.fsync=objects,reference", *args),
                       env=env, budget=budget, input_bytes=input_bytes,
                             ownership_fd=_OWNERSHIP_FD.get()).stdout
    except GitCommandFailure as exc:
        raise InvalidGitRuntime("runtime Git command failed: " + args[0]) from exc


def _environment(home: Path) -> dict:
    env = _sanitized_environment(home)
    env.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_NO_LAZY_FETCH": "1", "GIT_LITERAL_PATHSPECS": "1",
                "GIT_CONFIG_COUNT": "0", "GIT_DEFAULT_HASH": "sha1",
                "GIT_AUTHOR_NAME": "Agent Braid local runtime",
                "GIT_AUTHOR_EMAIL": "runtime@example.invalid",
                "GIT_COMMITTER_NAME": "Agent Braid local runtime",
                "GIT_COMMITTER_EMAIL": "runtime@example.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"})
    return env


def _budget(root: Path, cancel_event: threading.Event | None = None) -> GitCommandBudget:
    _require(fcntl is not None and os.name == "posix", "runtime requires POSIX advisory locking")
    return GitCommandBudget(temp_root=root, wall_seconds=LIMITS["wallSeconds"],
                            max_commands=LIMITS["gitCommands"],
                            max_output_bytes=LIMITS["outputBytes"],
                            max_command_output_bytes=LIMITS["commandOutputBytes"],
                            max_scratch_bytes=LIMITS["scratchBytes"],
                            max_process_address_space_bytes=LIMITS["childAddressSpaceBytes"],
                            cancel_event=cancel_event)


def _destination(value: str | Path, source: Path) -> Path:
    path = Path(value).expanduser().absolute()
    _require(path.name not in {"", ".", ".."} and not path.is_symlink(), "unsafe run destination")
    parent = path.parent.resolve(strict=True)
    _require(parent.is_dir(), "run parent must exist")
    resolved = parent / path.name
    _require(not resolved.is_relative_to(source), "run destination is inside source repository")
    return resolved


def _path(value: object) -> str:
    _require(isinstance(value, str) and 0 < len(value) <= 1024, "invalid declared path")
    _require(not value.startswith("/") and "\\" not in value
             and not any(c in value for c in "\0\r\n*?[]")
             and all(p not in {"", ".", ".."} and p.lower() != ".git"
                     for p in value.split("/")), "unsafe declared path")
    return value


def _request(value: object) -> dict:
    _require(isinstance(value, dict) and set(value) == {
        "gitRuntimeRequestVersion", "repository", "baseRevision", "operations",
        "order", "expectedFinalTree"}, "invalid runtime request fields")
    _require(value["gitRuntimeRequestVersion"] == VERSION, "unsupported runtime version")
    request = deepcopy(value)
    for field in ("baseRevision", "expectedFinalTree"):
        _require(isinstance(request[field], str) and bool(OID.fullmatch(request[field])),
                 field + " must be an immutable full Git ID")
    _require(isinstance(request["operations"], list) and 2 <= len(request["operations"]) <= 4,
             "runtime accepts 2-4 operations")
    analysis_ops = []
    for op in request["operations"]:
        _require(isinstance(op, dict) and set(op) == {
            "instanceId", "attemptId", "source", "dependencies", "uncertainPaths",
            "declaredWrites"}, "invalid runtime operation fields")
        _require(op["uncertainPaths"] == [], "unknown effect coverage is not admitted")
        _require(isinstance(op["source"], dict)
                 and isinstance(op["source"].get("revision"), str)
                 and bool(OID.fullmatch(op["source"]["revision"])),
                 "runtime sources require immutable full Git IDs")
        paths = op["declaredWrites"]
        _require(isinstance(paths, list) and len(paths) <= LIMITS["changedPaths"],
                 "invalid declared writes")
        op["declaredWrites"] = sorted(_path(p) for p in paths)
        _require(len(set(op["declaredWrites"])) == len(paths), "duplicate declared writes")
        analysis_ops.append({k: v for k, v in op.items() if k != "declaredWrites"})
    analysis = {"gitAnalysisRequestVersion": VERSION, "repository": request["repository"],
                "baseRevision": request["baseRevision"], "operations": analysis_ops}
    _validate_request(analysis)
    _require(isinstance(request["order"], list) and all(isinstance(i, str) for i in request["order"])
             and request["order"] in _topological_orders(analysis_ops),
             "invalid dependency-respecting serial order")
    request["repository"] = str(Path(request["repository"]).expanduser().resolve(strict=True))
    return request


def _analysis_request(request: dict) -> dict:
    return {"gitAnalysisRequestVersion": VERSION, "repository": request["repository"],
            "baseRevision": request["baseRevision"],
            "operations": [{k: v for k, v in op.items() if k != "declaredWrites"}
                           for op in request["operations"]]}


def _tree(repo: Path, revision: str, env: dict, budget: GitCommandBudget) -> str:
    result = _git(repo, env, budget, "rev-parse", "--verify", revision + "^{tree}").decode().strip()
    _require(bool(OID.fullmatch(result)), "invalid observed tree ID")
    return result


def _head(repo: Path, env: dict, budget: GitCommandBudget) -> str:
    result = _git(repo, env, budget, "rev-parse", "--verify", RESULT_REF).decode().strip()
    _require(bool(OID.fullmatch(result)), "invalid private checkpoint ref")
    return result


def _effects(repo: Path, before: str, after: str, env: dict, budget: GitCommandBudget) -> list[dict]:
    raw = _git(repo, env, budget, "diff-tree", "--no-commit-id", "--raw", "-z", "-r",
               "--no-renames", "--no-abbrev", "--no-ext-diff", "--no-textconv", before, after, "--")
    parts = raw.split(b"\0")
    if parts[-1] == b"":
        parts.pop()
    _require(len(parts) % 2 == 0, "malformed private effect observation")
    result = []
    for i in range(0, len(parts), 2):
        header = parts[i].decode("ascii").split()
        _require(len(header) == 5 and header[0].startswith(":"), "invalid raw change header")
        path = _path(parts[i + 1].decode("utf-8"))
        old_mode, new_mode, old_blob, new_blob, status_code = header
        old_mode = old_mode[1:]
        _require(status_code in {"A", "M"} and old_mode in {"000000", "100644", "100755"}
                 and new_mode in {"100644", "100755"}, "unsupported path mode or change")
        result.append({"path": path, "status": status_code, "beforeMode": old_mode,
                       "afterMode": new_mode, "beforeBlob": old_blob, "afterBlob": new_blob})
    return sorted(result, key=lambda e: e["path"])


def _commit(repo: Path, tree: str, parent: str, op: dict, env: dict, budget: GitCommandBudget) -> str:
    message = _canonical({"executionContract": EXECUTION, "operation": op}) + b"\n"
    commit = _git(repo, env, budget, "commit-tree", tree, "-p", parent, "-F", "-",
                  input_bytes=message).decode().strip()
    _require(bool(OID.fullmatch(commit)), "invalid checkpoint commit")
    return commit


def _init(repo: Path, source: Path, base: str, env: dict, budget: GitCommandBudget) -> None:
    _git(repo.parent, env, budget, "init", "--bare", "--template=", "--quiet", str(repo))
    _git(repo, env, budget, "fetch", "--no-tags", "--no-recurse-submodules", "--depth=1",
         "--", str(source), base)
    _git(repo, env, budget, "read-tree", base)


def _prepare(request: object, run_directory: str | Path, temp: Path,
             cancel_event: threading.Event | None = None, *,
             budget: GitCommandBudget | None = None) -> tuple[dict, dict[str, bytes]]:
    req = _request(request)
    source = Path(req["repository"])
    dest = _destination(run_directory, source)
    env = _environment(temp / "home")
    budget = budget if budget is not None else _budget(temp, cancel_event)
    common = _git(source, env, budget, "rev-parse", "--git-common-dir").decode().strip()
    common_path = (source / common).resolve()
    _require(not dest.is_relative_to(common_path), "run destination is inside source Git storage")
    analysis = _analysis_request(req)
    _, provenance = analyze_git_with_provenance(analysis, env=env, budget=budget)
    supported, reasons, count = _supported_operations(provenance)
    patches = _patches(analysis, provenance, env, budget)
    _mark_unsupported_binary_patches(provenance, patches, supported, reasons)
    _require(all(supported.values()), "unsupported or unknown runtime operation")
    _require(count <= LIMITS["changedPaths"], "runtime changed-path limit exceeded")
    _require(sum(map(len, patches.values())) <= LIMITS["patchBytes"], "runtime patch limit exceeded")
    by_id = {op["instanceId"]: op for op in req["operations"]}
    by_provenance = {op["instanceId"]: op for op in provenance["operations"]}
    for op in req["operations"]:
        actual = sorted(change["path"] for change in by_provenance[op["instanceId"]]["changes"])
        _require(actual == op["declaredWrites"], "observed paths differ from declared writes")
    repo = temp / "rehearsal.git"
    _init(repo, source, req["baseRevision"], env, budget)
    parent = req["baseRevision"]
    base_tree = _tree(repo, parent, env, budget)
    previous_tree = base_tree
    steps = []
    for identifier in req["order"]:
        op = by_id[identifier]
        patch = patches[identifier]
        if patch:
            _git(repo, env, budget, "apply", "--cached", "--whitespace=nowarn", "-", input_bytes=patch)
        tree = _git(repo, env, budget, "write-tree").decode().strip()
        effects = _effects(repo, previous_tree, tree, env, budget)
        _require([e["path"] for e in effects] == op["declaredWrites"],
                 "serial operation effects differ from declaration")
        commit = _commit(repo, tree, parent, op, env, budget)
        steps.append({"operationId": identifier, "attemptId": op["attemptId"],
                      "sourceCommit": op["source"]["revision"], "patchDigest": _digest_bytes(patch),
                      "inputTree": previous_tree, "outputTree": tree,
                      "parentCommit": parent, "commit": commit, "effects": effects})
        parent, previous_tree = commit, tree
    _require(previous_tree == req["expectedFinalTree"], "declared final tree differs from serial result")
    manifest = {"gitRuntimeManifestVersion": VERSION, "request": req,
                "runDirectory": str(dest), "repositoryId": provenance["repositoryId"],
                "baseTree": base_tree, "steps": steps, "resourceLimits": LIMITS.copy(),
                "privateConfigDigest": _digest_bytes((repo / "config").read_bytes()),
                "observationContract": OBSERVATION, "executionContract": EXECUTION,
                "authorizationScope": "private-run-only", "sourcePromotion": False}
    manifest["manifestDigest"] = _digest(manifest)
    return manifest, patches


def _digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def prepare_run(request: object, run_directory: str | Path, *,
                cancel_event: threading.Event | None = None) -> dict:
    """Rehearse and describe a batch. Never allocate the persistent run directory."""
    with tempfile.TemporaryDirectory(prefix="agent-braid-runtime-prepare-") as directory:
        return _prepare(request, run_directory, Path(directory), cancel_event)[0]


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(root: Path, name: str, value: dict) -> None:
    destination = root / name
    _require(not destination.is_symlink(), "symlink runtime record")
    fd, temporary = tempfile.mkstemp(prefix=".runtime-", dir=root)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(_canonical(value) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        _fsync_dir(root)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _read_record(path: Path) -> dict:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise InvalidGitRuntime("symlink runtime record") from exc
        raise
    with os.fdopen(fd, "rb") as stream:
        _require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode), "runtime record is not regular")
        raw = stream.read(MAX_RECORD_BYTES + 1)
    _require(len(raw) <= MAX_RECORD_BYTES, "runtime record exceeds size limit")
    value = loads(raw.decode("utf-8"))
    _require(isinstance(value, dict), "runtime record must be an object")
    return value


@contextmanager
def _lock(root: Path, *, create: bool = True):
    _require(root.is_dir() and not root.is_symlink(), "missing or unsafe run directory")
    fd = os.open(root / "coordinator.lock", os.O_RDWR | (os.O_CREAT if create else 0) | os.O_NOFOLLOW, 0o600)
    try:
        _require(stat.S_ISREG(os.fstat(fd).st_mode), "invalid coordinator lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InvalidGitRuntime("run already owned by another coordinator") from exc
        token = _OWNERSHIP_FD.set(fd)
        try:
            yield
        finally:
            _OWNERSHIP_FD.reset(token)
    finally:
        os.close(fd)


def _storage(root: Path) -> None:
    # Trusted owned filesystem; reject persistent redirection between invocations.
    for directory, dirs, files in os.walk(root):
        for name in dirs + files:
            _require(not (Path(directory) / name).is_symlink(), "symlink in owned runtime storage")


def _layout(root: Path) -> None:
    _storage(root)
    repo = root / "result.git"
    _require(repo.is_dir() and (repo / "config").is_file(), "missing initialized private repository")
    _require(not (repo / "objects/info/alternates").exists(), "private object store uses alternates")
    _require(not (repo / "commondir").exists(), "private repository redirects common directory")
    _require(not (repo / "shallow.lock").exists(), "unexpected private repository lock")


def _state(manifest: dict, phase: str, index: int) -> dict:
    return {"gitRuntimeStateVersion": VERSION, "manifestDigest": manifest["manifestDigest"],
            "phase": phase, "nextIndex": index}


def _checkpoint(manifest: dict, index: int) -> tuple[str, str]:
    if index == 0:
        return manifest["request"]["baseRevision"], manifest["baseTree"]
    step = manifest["steps"][index - 1]
    return step["commit"], step["outputTree"]


def _inspect(root: Path, manifest: dict, env: dict, budget: GitCommandBudget, *,
             recover_locks: bool = False) -> tuple[dict, str]:
    _layout(root)
    _require(_read_record(root / "manifest.json") == manifest, "stored manifest differs from reconstructed input")
    state = _read_record(root / "state.json")
    _require(set(state) == {"gitRuntimeStateVersion", "manifestDigest", "phase", "nextIndex"}
             and state["gitRuntimeStateVersion"] == VERSION
             and state["manifestDigest"] == manifest["manifestDigest"], "invalid runtime state binding")
    phase, index = state["phase"], state["nextIndex"]
    size = len(manifest["steps"])
    _require(type(index) is int and 0 <= index <= size and phase in {
        "initializing", "ready", "applying", "completed", "aborting", "aborted"}, "invalid runtime state phase/index")
    _require(phase != "initializing" or index == 0, "invalid initialization index")
    _require(phase != "applying" or index < size, "invalid pending transition")
    _require(phase != "completed" or index == size, "forged terminal completion")
    _require(phase != "ready" or index < size, "invalid ready terminal")
    _require(phase != "aborted" or index == 0, "invalid aborted position")
    repo = root / "result.git"
    _require(_digest_bytes((repo / "config").read_bytes()) == manifest["privateConfigDigest"],
             "private Git configuration differs from owned initialization")
    _require(not (repo / "refs/heads/result").read_text().startswith("ref:"),
             "private result ref is symbolic")
    head = _head(repo, env, budget)
    before, _ = _checkpoint(manifest, index)
    admitted = {before}
    if phase == "applying":
        admitted.add(manifest["steps"][index]["commit"])
    if phase == "aborting":
        admitted.add(manifest["request"]["baseRevision"])
    _require(head in admitted, "private ref does not match owned checkpoint")
    if phase == "aborted":
        _require(head == manifest["request"]["baseRevision"], "abort did not restore base")
    if recover_locks:
        _clear_owned_git_locks(repo)
    _git(repo, env, budget, "fsck", "--strict", "--no-reflogs")
    # Validate the entire observed chain by recomputing commit IDs from contents.
    committed = index + (phase == "applying" and head != before)
    if phase in {"aborting", "aborted"} and head == manifest["request"]["baseRevision"]:
        committed = 0
    for step in manifest["steps"][:committed]:
        actual_tree = _tree(repo, step["commit"], env, budget)
        _require(actual_tree == step["outputTree"], "checkpoint tree differs from expected result")
        actual = _git(repo, env, budget, "cat-file", "commit", step["commit"])
        identity = hashlib.sha1(b"commit " + str(len(actual)).encode() + b"\0" + actual).hexdigest()
        _require(identity == step["commit"], "stored checkpoint object content is corrupt")
        _require(_effects(repo, step["inputTree"], step["outputTree"], env, budget) == step["effects"],
                 "checkpoint effects differ from manifest")
    return state, head


def _report(manifest: dict, state: dict, head: str, verified: bool = False) -> dict:
    phase = state["phase"]
    index = state["nextIndex"]
    if phase == "applying" and head == manifest["steps"][index]["commit"]:
        index += 1
    if phase in {"aborted", "aborting"} and head == manifest["request"]["baseRevision"]:
        index = 0
    tree = _checkpoint(manifest, index)[1]
    status = {"completed": "completed", "aborted": "aborted"}.get(phase, "interrupted")
    return {"gitRuntimeReportVersion": VERSION,
            "status": ("verified-" + (status if status != "interrupted" else "prefix")) if verified else status,
            "phase": phase, "manifestDigest": manifest["manifestDigest"],
            "runDirectory": manifest["runDirectory"], "resultCommit": head, "resultTree": tree,
            "completedOperations": [s["operationId"] for s in manifest["steps"][:index]],
            "authorizationScope": "private-run-only", "sourcePromotion": False,
            "observationContract": OBSERVATION, "executionContract": EXECUTION,
            "limits": ["Fixed text patches and private Git storage only; no repository code or source promotion.",
                       "Digest acknowledgement is not authentication; owned POSIX filesystem/Git are trusted.",
                       "Process interruption recovery; no power-loss, hostile same-UID or production-safety guarantee.",
                       "No hard child memory cap; scratch is sampled and can overshoot between checks.",
                       "Tree observations do not establish semantic correctness or safe concurrency."]}


def _clear_owned_git_locks(repo: Path) -> None:
    # A surviving Git child retains this FD and prevents another coordinator.
    # Only remove known scratch locks after validating the sealed state/config/ref.
    _require(_OWNERSHIP_FD.get() is not None, "private lock recovery requires coordinator ownership")
    for relative in ("index.lock", RESULT_REF + ".lock"):
        lock = repo / relative
        if lock.exists():
            _require(lock.is_file() and not lock.is_symlink(), "unsafe abandoned private Git lock")
            lock.unlink()
            _fsync_dir(lock.parent)


def _bootstrap(root: Path, manifest: dict, env: dict, budget: GitCommandBudget) -> None:
    """Discard only unpublished initialization scratch; retain any published result."""
    _storage(root)
    stage = root / "initializing.git"
    repo = root / "result.git"
    if not repo.exists():
        if stage.exists():
            # This unpublished copy has no operation result/evidence. The sealed
            # initializing state and coordinator lock establish owned scratch.
            shutil.rmtree(stage)
        _init(stage, Path(manifest["request"]["repository"]),
              manifest["request"]["baseRevision"], env, budget)
        _git(stage, env, budget, "update-ref", RESULT_REF, manifest["request"]["baseRevision"])
        _require(_digest_bytes((stage / "config").read_bytes()) == manifest["privateConfigDigest"],
                 "initialization config differs from prepared manifest")
        os.rename(stage, repo)
        _fsync_dir(root)
    _layout(root)
    _require(_digest_bytes((repo / "config").read_bytes()) == manifest["privateConfigDigest"],
             "private initialization config differs")
    _require(_head(repo, env, budget) == manifest["request"]["baseRevision"],
             "initialization has an unexpected private ref")
    _atomic_json(root, "state.json", _state(manifest, "ready", 0))


def _drive(root: Path, manifest: dict, patches: dict[str, bytes], env: dict,
           budget: GitCommandBudget, action: str) -> dict:
    _require(action in {"resume", "abort"}, "invalid recovery action")
    _storage(root)
    _require(_read_record(root / "manifest.json") == manifest,
             "stored manifest differs from reconstructed input")
    initial = _read_record(root / "state.json")
    if initial == _state(manifest, "initializing", 0):
        _bootstrap(root, manifest, env, budget)
    state, head = _inspect(root, manifest, env, budget, recover_locks=True)
    phase, index = state["phase"], state["nextIndex"]
    repo = root / "result.git"
    _require(action != "resume" or phase not in {"aborting", "aborted"}, "aborted run cannot resume")
    if action == "abort":
        if phase == "applying" and head == manifest["steps"][index]["commit"]:
            index += 1
        state = _state(manifest, "aborting", index)
        _atomic_json(root, "state.json", state)
        base = manifest["request"]["baseRevision"]
        _git(repo, env, budget, "update-ref", RESULT_REF, base, head)
        _git(repo, env, budget, "read-tree", base)
        state = _state(manifest, "aborted", 0)
        _atomic_json(root, "state.json", state)
        return _report(manifest, state, base)
    if phase == "applying" and head == manifest["steps"][index]["commit"]:
        index += 1
    by_id = {op["instanceId"]: op for op in manifest["request"]["operations"]}
    for i in range(index, len(manifest["steps"])):
        step = manifest["steps"][i]
        _git(repo, env, budget, "read-tree", head)
        state = _state(manifest, "applying", i)
        _atomic_json(root, "state.json", state)
        patch = patches[step["operationId"]]
        if patch:
            _git(repo, env, budget, "apply", "--cached", "--whitespace=nowarn", "-", input_bytes=patch)
        tree = _git(repo, env, budget, "write-tree").decode().strip()
        _require(tree == step["outputTree"], "runtime tree differs from admitted step")
        _require(_effects(repo, step["inputTree"], tree, env, budget) == step["effects"],
                 "runtime effects differ from admitted step")
        commit = _commit(repo, tree, head, by_id[step["operationId"]], env, budget)
        _require(commit == step["commit"], "runtime checkpoint differs from admitted step")
        _git(repo, env, budget, "update-ref", RESULT_REF, commit, head)
        head = commit
        phase = "completed" if i + 1 == len(manifest["steps"]) else "ready"
        state = _state(manifest, phase, i + 1)
        _atomic_json(root, "state.json", state)
    # Death after the last CAS leaves applying/last index; reconciliation completes it.
    state = _state(manifest, "completed", len(manifest["steps"]))
    _atomic_json(root, "state.json", state)
    return _report(manifest, state, head)


def _publish_directory(stage: Path, destination: Path) -> None:
    """Atomically publish a sealed directory without replacing any existing entry.

    Darwin SDK sys/stdio.h defines RENAME_EXCL=4. Linux renameat2 uses
    AT_FDCWD=-100 and RENAME_NOREPLACE=1. Unsupported platforms fail closed.
    """
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        fn = libc.renamex_np
        fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        code = fn(os.fsencode(stage), os.fsencode(destination), 4)
    elif sys.platform == "linux" and hasattr(libc, "renameat2"):
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        fn.restype = ctypes.c_int
        code = fn(-100, os.fsencode(stage), -100, os.fsencode(destination), 1)
    else:
        raise InvalidGitRuntime("atomic exclusive directory publication unavailable on this platform")
    if code != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))
    _fsync_dir(destination.parent)


def execute_run(request: object, run_directory: str | Path, authorization: str, *,
                cancel_event: threading.Event | None = None) -> dict:
    """Allocate and execute a new private run after matching explicit acknowledgement."""
    with tempfile.TemporaryDirectory(prefix="agent-braid-runtime-admission-") as directory:
        budget = _budget(Path(directory), cancel_event)
        manifest, patches = _prepare(request, run_directory, Path(directory), cancel_event, budget=budget)
    _require(authorization == manifest["manifestDigest"], "missing or mismatched runtime authorization")
    root = Path(manifest["runDirectory"])
    # Prepare the ownership seal before one atomic, exclusive publication. An
    # interruption before publication cannot reserve an unrecognizable run path.
    with tempfile.TemporaryDirectory(prefix="." + root.name + ".stage-", dir=root.parent) as staging:
        stage = Path(staging)
        with _lock(stage):
            _atomic_json(stage, "manifest.json", manifest)
            _atomic_json(stage, "state.json", _state(manifest, "initializing", 0))
            _publish_directory(stage, root)
            env = _environment(root / "home")
            budget.temp_root = root
            return _drive(root, manifest, patches, env, budget, "resume")


def recover_run(request: object, run_directory: str | Path, authorization: str,
                action: str = "resume", *, cancel_event: threading.Event | None = None) -> dict:
    """Reconstruct authority and reconcile only an owned private checkpoint."""
    with tempfile.TemporaryDirectory(prefix="agent-braid-runtime-recovery-") as directory:
        budget = _budget(Path(directory), cancel_event)
        manifest, patches = _prepare(request, run_directory, Path(directory), cancel_event, budget=budget)
    _require(authorization == manifest["manifestDigest"], "missing or mismatched runtime authorization")
    root = Path(manifest["runDirectory"])
    _require(_read_record(root / "manifest.json") == manifest, "stored manifest differs from reconstructed input")
    _read_record(root / "state.json")
    with _lock(root, create=False):
        _storage(root)
        env = _environment(root / "home")
        budget.temp_root = root
        return _drive(root, manifest, patches, env, budget, action)


def verify_run(request: object, run_directory: str | Path) -> dict:
    """Read-only reconstruction; never accepts a producer's claimed completion."""
    with tempfile.TemporaryDirectory(prefix="agent-braid-runtime-verifier-") as directory:
        temp = Path(directory)
        budget = _budget(temp)
        manifest, _ = _prepare(request, run_directory, temp, budget=budget)
        root = Path(manifest["runDirectory"])
        # Existing lock must exist: verifier never creates an artifact in the run.
        _require((root / "coordinator.lock").is_file(), "missing coordinator lock")
        with _lock(root, create=False):
            _storage(root)
            env = _environment(temp / "verify-home")
            initial = _read_record(root / "state.json")
            if initial == _state(manifest, "initializing", 0):
                _require(_read_record(root / "manifest.json") == manifest, "stored manifest differs")
                if (root / "result.git").exists():
                    _inspect(root, manifest, env, budget)
                return _report(manifest, initial, manifest["request"]["baseRevision"], verified=True)
            state, head = _inspect(root, manifest, env, budget)
            return _report(manifest, state, head, verified=True)
