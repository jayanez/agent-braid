# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Agent Braid modifications Copyright 2026 Juan Antonio Yáñez García.
# Adapted SurfaceSpec/normalize_rel/read_tree/write_tree/validate scaffolding from
# harness2/core/tree.py:41-60,82-89,127-148,156-185,336-390 at
# 1cfe254e8d25b15f37048c3730134686abe60335. Changed to exact offline inventories,
# descriptor-relative no-follow reads, protected guidance-only paths, strict bytes,
# private exclusive staging and atomic accepted-tree publication. No candidate code
# compilation, host execution, inherited omissions or in-place tree replacement.
"""Bounded offline candidate import into a newly claimed private container.

Input roots are separate canonical operator-owned roots. Source/context reads
use only selected inventories; only base/candidate trees are enumerated. Candidate text is untrusted data. No code is imported or
executed. Accepted files are read-only, not a sandbox against their trusted owner;
subsequent consumers must independently verify their bytes. Hostile same-UID
ancestor replacement and power-loss durability are outside the adopted
operator/OS trust boundary. Ordinary symlinks, aliases, unexpected entries and drift still refuse.
"""
from __future__ import annotations

from collections.abc import Mapping
from contextlib import ExitStack
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import stat
import unicodedata
from typing import Any

from .harness_manifest import BINDING_NAMES, ManifestError, verify_manifest
from .system_one import canonical, digest, freeze

FORMAT = "braid-harness-surface-import/v0.1"
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
_MODES = {0o400, 0o444, 0o600, 0o644}
_PROTECTED = frozenset({
    "agents", "agent", "claude", "constitution", "governance", "settings",
    "permissions", "issuers", "grants", "verifier", "verifiers", "grader",
    "graders", "tests", "tools", "scripts", "hooks", "plugins", "models",
    "providers", "policy", "policies", "specify",
})


class SurfaceError(ValueError):
    """Sanitized refusal with an immutable failure/owned-cleanup receipt."""

    def __init__(self, reason: str, receipt: Mapping[str, Any] | None = None):
        self.reason = reason
        self.receipt = freeze(dict(receipt or {
            "format": FORMAT, "status": "refused", "reason": reason,
            "containerClaimed": False, "acceptedPublished": False,
            "cleanup": {"status": "not-needed", "ownedEntriesRemaining": 0},
            "executionAuthorization": False,
        }))
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SurfaceError(reason)


def normalize_rel(value: str, *, depth: int = 4) -> str:
    """Validate exact relative spelling; never repair an escaped/aliased path."""
    _require(type(value) is str, "invalid-path")
    try:
        bounded = 0 < len(value.encode("utf-8")) <= 512
    except UnicodeError:
        bounded = False
    _require(bounded and unicodedata.normalize("NFC", value) == value and
             not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value)
             and not any(c in value for c in "\\:*?[]{}~"), "invalid-path")
    parts = value.split("/")
    _require(len(parts) <= depth and all(p not in {"", ".", ".."} for p in parts),
             "invalid-path")
    return value


@dataclass(frozen=True)
class SurfaceSpec:
    """One positive guidance inventory, with immutable protected precedence."""

    allowed_paths: tuple[str, ...]
    max_files: int
    max_file_bytes: int
    max_total_bytes: int
    max_depth: int

    def validate_path(self, path: str) -> None:
        path = normalize_rel(path, depth=self.max_depth)
        parts = path.split("/")
        _require(path in self.allowed_paths and len(parts) >= 2 and
                 parts[0] == "guidance" and Path(parts[-1]).suffix in {".md", ".txt"},
                 "path-outside-surface")
        _require(not any(p.startswith(".") or p.split(".", 1)[0].casefold() in _PROTECTED
                         for p in parts), "protected-component")


def _absolute(value: str | Path) -> Path:
    _require(isinstance(value, (str, Path)), "invalid-root")
    raw = str(value)
    try:
        valid = raw.startswith("/") and not raw.startswith("//") and \
            raw == str(Path(raw)) and 0 < len(raw.encode("utf-8")) <= 4096 and \
            all(p not in {"", ".", ".."} for p in raw.split("/")[1:]) and \
            not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in raw)
    except UnicodeError:
        valid = False
    _require(valid, "invalid-root")
    return Path(raw)


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _owned_directory(info: os.stat_result) -> None:
    _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and
             not info.st_mode & 0o7022, "unsafe-directory")


def _open_directory(path: Path, *, lineage: list[tuple[int, int]] | None = None) -> int:
    """Open without following links and optionally retain actual ancestor inodes."""
    descriptor = os.open("/", _DIRECTORY)
    try:
        if lineage is not None:
            info = os.fstat(descriptor)
            lineage.append((info.st_dev, info.st_ino))
        for part in path.parts[1:]:
            child = os.open(part, _DIRECTORY, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            if lineage is not None:
                info = os.fstat(descriptor)
                lineage.append((info.st_dev, info.st_ino))
        _owned_directory(os.fstat(descriptor))
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _text(raw: bytes) -> None:
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise SurfaceError("unsupported-encoding") from None
    _require(not text.startswith("\ufeff") and
             not any(unicodedata.category(c) in {"Cc", "Cs"} and c not in "\n\r\t"
                     for c in text), "unsupported-encoding")
    # This rejects a script file signature, not hostile instructions in guidance.
    # Markdown snippets and claims of authority remain inert, untrusted text.
    _require(not text.lstrip().startswith("#!"), "executable-content")


@dataclass
class _Snapshot:
    files: dict[str, bytes]
    identities: dict[str, tuple[int, ...]]
    observation_sha256: str


def _read_tree(descriptor: int, inventory: Any, *, count: int, per_file: int,
               total_limit: int, depth: int) -> _Snapshot:
    expected = {row["path"]: row for row in inventory}
    _require(len(expected) <= count, "inventory-budget-exceeded")
    prefixes = {"/".join(path.split("/")[:i]) for path in expected
                for i in range(1, len(path.split("/")))}
    files, identities, modes = {}, {}, {}
    seen_entries = total = 0

    def walk(current: int, prefix: str = "") -> None:
        nonlocal seen_entries, total
        before = os.fstat(current)
        _owned_directory(before)
        identities[prefix + "/"] = _identity(before)
        with os.scandir(current) as entries:
            for entry in entries:
                seen_entries += 1
                _require(seen_entries <= max(1, count) * depth, "enumeration-budget-exceeded")
                rel = normalize_rel(prefix + "/" + entry.name if prefix else entry.name, depth=depth)
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    _require(rel in prefixes, "undeclared-entry")
                    child = os.open(entry.name, _DIRECTORY, dir_fd=current)
                    try:
                        _require(_identity(os.fstat(child)) == _identity(info), "input-drift")
                        walk(child, rel)
                    finally:
                        os.close(child)
                    continue
                _require(stat.S_ISREG(info.st_mode), "symlink-or-special-file")
                _require(rel in expected, "undeclared-entry")
                _require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) in _MODES
                         and info.st_nlink == 1, "unsafe-file-mode-or-alias")
                row = expected[rel]
                _require(info.st_size == row["sizeBytes"] and info.st_size <= per_file,
                         "file-size-mismatch")
                total += info.st_size
                _require(total <= total_limit, "input-budget-exceeded")
                handle = os.open(entry.name, _FILE, dir_fd=current)
                try:
                    _require(_identity(os.fstat(handle)) == _identity(info), "input-drift")
                    chunks, length = [], 0
                    while True:
                        block = os.read(handle, min(65_536, per_file + 1 - length))
                        if not block:
                            break
                        chunks.append(block)
                        length += len(block)
                        _require(length <= per_file, "input-budget-exceeded")
                    raw = b"".join(chunks)
                    _require(_identity(os.fstat(handle)) == _identity(info), "input-drift")
                finally:
                    os.close(handle)
                _require(len(raw) == row["sizeBytes"] and sha256(raw).hexdigest() == row["sha256"],
                         "file-identity-mismatch")
                _text(raw)
                files[rel], identities[rel], modes[rel] = raw, _identity(info), stat.S_IMODE(info.st_mode)
        _require(_identity(os.fstat(current)) == _identity(before), "input-drift")

    walk(descriptor)
    _require(set(files) == set(expected), "missing-inventory-file")
    observation = [{"path": path, "sha256": sha256(files[path]).hexdigest(),
                    "sizeBytes": len(files[path]), "mode": modes[path]} for path in sorted(files)]
    return _Snapshot(files, identities, digest(observation))



def _read_inventory(descriptor: int, inventory: Any, *, count: int, per_file: int,
                    total_limit: int, depth: int) -> _Snapshot:
    """Read selected source/context paths without enumerating unrelated entries."""
    _require(len(inventory) <= count, "inventory-budget-exceeded")
    files, identities, modes = {}, {}, {}
    total = 0
    for row in inventory:
        rel = normalize_rel(row["path"], depth=depth)
        parts = rel.split("/")
        parent = os.dup(descriptor)
        try:
            identities["/"] = _identity(os.fstat(descriptor))
            for index, part in enumerate(parts[:-1], 1):
                child = os.open(part, _DIRECTORY, dir_fd=parent)
                os.close(parent)
                parent = child
                info = os.fstat(parent)
                _owned_directory(info)
                identities["/".join(parts[:index]) + "/"] = _identity(info)
            info = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and
                     stat.S_IMODE(info.st_mode) in _MODES and info.st_nlink == 1,
                     "unsafe-file-mode-or-alias")
            _require(info.st_size == row["sizeBytes"] and info.st_size <= per_file,
                     "file-size-mismatch")
            total += info.st_size
            _require(total <= total_limit, "input-budget-exceeded")
            handle = os.open(parts[-1], _FILE, dir_fd=parent)
            try:
                _require(_identity(os.fstat(handle)) == _identity(info), "input-drift")
                chunks, length = [], 0
                while True:
                    chunk = os.read(handle, min(65_536, per_file + 1 - length))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    length += len(chunk)
                    _require(length <= per_file, "input-budget-exceeded")
                raw = b"".join(chunks)
                _require(_identity(os.fstat(handle)) == _identity(info), "input-drift")
            finally:
                os.close(handle)
            _require(len(raw) == row["sizeBytes"] and sha256(raw).hexdigest() == row["sha256"],
                     "file-identity-mismatch")
            _text(raw)
            files[rel], identities[rel], modes[rel] = raw, _identity(info), stat.S_IMODE(info.st_mode)
        finally:
            os.close(parent)
    observations = [{"path": path, "sha256": sha256(files[path]).hexdigest(),
                     "sizeBytes": len(files[path]), "mode": modes[path]} for path in sorted(files)]
    return _Snapshot(files, identities, digest(observations))


def _child_directory(root: int, path: str) -> int:
    descriptor = os.dup(root)
    try:
        for part in path.split("/") if path else ():
            child = os.open(part, _DIRECTORY, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _cleanup(container: int, owned: list[tuple[str, bool, tuple[int, int]]]) -> dict:
    """Delete only recorded owned inode identities; leave unknown replacements."""
    for path, directory, identity in owned:
        if not directory:
            continue
        descriptor = None
        try:
            descriptor = _child_directory(container, path)
            info = os.fstat(descriptor)
            if stat.S_ISDIR(info.st_mode) and (info.st_dev, info.st_ino) == identity:
                os.fchmod(descriptor, 0o700)
        except OSError:
            pass
        finally:
            if descriptor is not None:
                os.close(descriptor)
    remaining = 0
    for path, directory, identity in reversed(owned):
        parent, _, name = path.rpartition("/")
        descriptor = None
        try:
            descriptor = _child_directory(container, parent)
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            if ((info.st_dev, info.st_ino) != identity or info.st_uid != os.getuid()
                    or (not directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1))
                    or (directory and not stat.S_ISDIR(info.st_mode))):
                remaining += 1
                continue
            if directory:
                os.rmdir(name, dir_fd=descriptor)
            else:
                os.unlink(name, dir_fd=descriptor)
        except FileNotFoundError:
            pass
        except OSError:
            remaining += 1
        finally:
            if descriptor is not None:
                os.close(descriptor)
    return {"status": "completed" if not remaining else "incomplete",
            "ownedEntriesRemaining": remaining}


def _materialize(container: int, files: Mapping[str, bytes],
                 owned: list[tuple[str, bool, tuple[int, int]]]) -> None:
    def directory(path: str) -> None:
        parent, _, name = path.rpartition("/")
        descriptor = _child_directory(container, parent)
        try:
            os.mkdir(name, 0o700, dir_fd=descriptor)
            info = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            owned.append((path, True, (info.st_dev, info.st_ino)))
        finally:
            os.close(descriptor)

    directory("staging")
    directories = {"/".join(path.split("/")[:i]) for path in files
                   for i in range(1, len(path.split("/")))}
    for path in sorted(directories, key=lambda item: (item.count("/"), item)):
        directory("staging/" + path)
    for path, raw in sorted(files.items()):
        parent, _, name = ("staging/" + path).rpartition("/")
        descriptor = _child_directory(container, parent)
        handle = None
        try:
            handle = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=descriptor)
            info = os.fstat(handle)
            owned.append(("staging/" + path, False, (info.st_dev, info.st_ino)))
            offset = 0
            while offset < len(raw):
                written = os.write(handle, raw[offset:])
                _require(written > 0, "materialization-failed")
                offset += written
            os.fsync(handle)
            os.fchmod(handle, 0o400)
        finally:
            if handle is not None:
                os.close(handle)
            os.close(descriptor)
    for path, is_directory, _ in reversed(owned):
        if is_directory:
            descriptor = _child_directory(container, path)
            try:
                os.fsync(descriptor)
                os.fchmod(descriptor, 0o500)
            finally:
                os.close(descriptor)


def import_candidate(raw: bytes, *, expected_sha256: str,
                     expected_bindings: Mapping[str, str], source_root: str | Path,
                     base_root: str | Path, candidate_root: str | Path,
                     context_root: str | Path, destination: str | Path) -> Mapping[str, Any]:
    """Verify all four exact read inventories, then publish one private candidate.

    The destination must be new. It is claimed exclusively as a private container;
    only its `candidate/` subtree is an accepted tree, published by one rename after
    input and staged-byte revalidation. Failed staging never yields an accepted
    receipt. The failure receipt remains available on SurfaceError.receipt; durable
    persistence/recovery belongs to its future operator/journal consumer.

    Source Git commit and root selection are trusted operator observations: this
    function never shells out to discover Git state or discovers extra source paths.
    It performs no dispatch, admission issuance, promotion or context packaging.
    """
    claimed = False
    owned: list[tuple[str, bool, tuple[int, int]]] = []
    receipt: dict[str, Any] = {"format": FORMAT, "status": "refused",
        "containerClaimed": False, "acceptedPublished": False,
        "cleanup": {"status": "not-needed", "ownedEntriesRemaining": 0},
        "executionAuthorization": False}
    with ExitStack() as stack:
        container = None
        try:
            _require(isinstance(expected_bindings, Mapping) and
                     set(expected_bindings) == BINDING_NAMES, "incomplete-consumer-bindings")
            manifest = verify_manifest(raw, expected_sha256=expected_sha256,
                                       expected_bindings=expected_bindings)
            data, limits = manifest.data, manifest.data["limits"]
            receipt["manifestSha256"] = manifest.sha256
            spec = SurfaceSpec(tuple(data["allowedComponentPaths"]), limits["maxFiles"],
                limits["maxFileBytes"], limits["maxCandidateBytes"], limits["maxPathDepth"])
            for path in spec.allowed_paths:
                spec.validate_path(path)
            inventories = {"source": data["source"]["selectedInputs"],
                           "base": data["base"]["files"],
                           "candidate": data["candidate"]["files"], "context": data["context"]}
            reads = {namespace + "/" + row["path"] for namespace, rows in inventories.items() for row in rows}
            writes = {"lab/" + row["path"] for row in inventories["candidate"]}
            _require(reads <= set(data["effects"]["read"]) and
                     writes <= set(data["effects"]["write"]) and
                     writes <= set(data["effects"]["delete"]), "missing-effect")
            roots = dict(zip(inventories, map(_absolute,
                (source_root, base_root, candidate_root, context_root)), strict=True))
            target = _absolute(destination)
            root_paths = list(roots.values())
            _require(all(a != b and a not in b.parents and b not in a.parents
                         for i, a in enumerate(root_paths) for b in root_paths[i + 1:]), "root-alias")
            _require(all(target != root and target not in root.parents and root not in target.parents
                         for root in root_paths), "output-source-collision")
            destination_digest = sha256(target.as_posix().encode("utf-8")).hexdigest()
            _require(destination_digest == data["environment"]["outputDestinationSha256"],
                     "destination-drift")
            receipt["outputDestinationSha256"] = destination_digest
            descriptors = {}
            identities = set()
            lineages: dict[str, list[tuple[int, int]]] = {}
            for name, root_path in roots.items():
                lineages[name] = []
                descriptor = _open_directory(root_path, lineage=lineages[name])
                stack.callback(os.close, descriptor)
                info = os.fstat(descriptor)
                identity = info.st_dev, info.st_ino
                _require(identity not in identities, "root-alias")
                identities.add(identity)
                descriptors[name] = descriptor
            # Lexical paths miss aliases on case-insensitive filesystems. Compare
            # each observed root leaf against every other actual ancestor chain,
            # in both directions, before even claiming the destination container.
            _require(all(chain[-1] not in other for name, chain in lineages.items()
                         for other_name, other in lineages.items() if name != other_name),
                     "root-alias")
            parent_lineage: list[tuple[int, int]] = []
            parent = _open_directory(target.parent, lineage=parent_lineage)
            stack.callback(os.close, parent)
            _require(not identities.intersection(parent_lineage), "output-source-collision")
            try:
                os.stat(target.name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise SurfaceError("destination-exists")

            def scan(name: str) -> _Snapshot:
                context = name == "context"
                reader = _read_tree if name in {"base", "candidate"} else _read_inventory
                return reader(descriptors[name], inventories[name],
                    count=limits["maxContextEntries"] if context else spec.max_files,
                    per_file=limits["maxContextBytes"] if context else spec.max_file_bytes,
                    total_limit=limits["maxContextBytes"] if context else spec.max_total_bytes,
                    depth=spec.max_depth)

            snapshots = {name: scan(name) for name in inventories}
            receipt["observations"] = {name: {"files": len(snap.files),
                "bytes": sum(map(len, snap.files.values())), "sha256": snap.observation_sha256}
                for name, snap in snapshots.items()}
            _require(len(canonical(receipt)) + 256 <= limits["maxStageOutputBytes"], "receipt-budget-exceeded")
            # mkdir is the exclusive no-replace claim; os.rename alone could replace
            # an unrelated empty destination directory on portable POSIX systems.
            os.mkdir(target.name, 0o700, dir_fd=parent)
            claimed = True
            receipt["containerClaimed"] = True
            container = os.open(target.name, _DIRECTORY, dir_fd=parent)
            stack.callback(os.close, container)
            _require(stat.S_IMODE(os.fstat(container).st_mode) == 0o700, "unsafe-destination")
            _materialize(container, snapshots["candidate"].files, owned)
            for name in inventories:
                fresh = _open_directory(roots[name])
                try:
                    initial = os.fstat(descriptors[name])
                    current = os.fstat(fresh)
                    _require((current.st_dev, current.st_ino) == (initial.st_dev, initial.st_ino),
                             "input-root-drift")
                finally:
                    os.close(fresh)
                again = scan(name)
                _require(again.files == snapshots[name].files and
                         again.identities == snapshots[name].identities, "input-drift")
            stage = _child_directory(container, "staging")
            try:
                staged = _read_tree(stage, inventories["candidate"], count=spec.max_files,
                    per_file=spec.max_file_bytes, total_limit=spec.max_total_bytes, depth=spec.max_depth)
                _require(all(stat.S_IMODE(identity[3]) == (0o500 if path.endswith("/") else 0o400)
                             for path, identity in staged.identities.items()), "staged-mode-drift")
            finally:
                os.close(stage)
            try:
                os.stat("candidate", dir_fd=container, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                raise SurfaceError("publication-collision")
            receipt.update(status="completed", acceptedPublished=True,
                           acceptedTree="candidate", baseSha256=data["base"]["sha256"],
                           candidateSha256=data["candidate"]["sha256"],
                           acceptedObservationSha256=staged.observation_sha256,
                           acceptedModes={"file": 0o400, "directory": 0o500})
            result = freeze(receipt)
            _require(len(canonical(result)) <= limits["maxStageOutputBytes"], "receipt-budget-exceeded")
            os.rename("staging", "candidate", src_dir_fd=container, dst_dir_fd=container)
            return result
        except (SurfaceError, ManifestError, OSError) as exc:
            reason = exc.reason if isinstance(exc, (SurfaceError, ManifestError)) else "filesystem-error"
            receipt.update(status="refused", reason=reason, containerClaimed=claimed,
                           acceptedPublished=False)
            receipt.pop("acceptedTree", None)
            if claimed:
                receipt["cleanup"] = (_cleanup(container, owned) if container is not None else
                    {"status": "incomplete", "ownedEntriesRemaining": len(owned)})
            raise SurfaceError(reason, receipt) from None
