# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded polling of watched artifact directories into the Loom store (SPEC-061 REQ-006).

`ArtifactTail` implements `--watch`: every `interval` seconds (500 ms) it walks the roots the
user named, looks only at files with a known artifact name, and feeds changed files through the
matching adapter into the store. It is read-only and follows
specs/061-activity-viewer/contracts/ui-security-privacy.md:

* at most 8 roots, 4 096 directory entries per scan across all roots and 16 MiB read per file;
  a bound that is exceeded is not an error: what lies beyond it is not read and one
  `stream-truncated` gap per bound is stored (again once the bound is met after having cleared);
* a symbolic link, a non-regular file or a path that leaves its root is never read, and a
  symbolic link to a directory is never entered; such entries are skipped without an event;
* a root inside another named root is not watched twice; an oversized file adds one gap while it
  stays oversized; a grant's derived expiry is computed only when its file is read (a changed file);
* directories are walked newest name first (report copies are named by UTC stamp), because the
  store's caps last for its whole life: when they are reached, the oldest copies are the ones refused;
* a file is read again only when its `os.stat` signature changes, and its events are stored
  again only when its SHA-256 changed, so touching a file adds nothing.

Events come from the artifact adapters, so they are `rehashed`. Nothing here writes to the file
system or reaches the network.

Root identity (REQ-010): the event contract names no root and `evidenceRef.path` stays relative to
it. The watcher therefore gives each watched root a stable, non-path label ("root 1" to "root 8", in
start order) and keeps it beside the store, per `seq`, in a `RootLabels` registry. `replay_with_roots`
returns the retained events with the labels read in the same step, and `build_model(events, roots=...)`
turns them into a per-element `root`. A label never contains a path or a user name. The labels are
per store, so one store has one watcher: two watchers on one store would both start at "root 1".
"""
from __future__ import annotations

import hashlib
from itertools import islice
import os
import stat
import threading
import time
import weakref
from pathlib import Path
from typing import Any, Callable, Mapping

from .view_adapters import (
    MAX_ARTIFACT_BYTES, AdapterError, events_from_analysis, events_from_gate_result, events_from_git_plan,
    events_from_grant, events_from_hazard_notice, events_from_ownership_receipt, events_from_runtime_state,
    events_from_scheduler, read_artifact,
)
from .view_loom import SCHEMA_VERSION, LoomError, validate_event
from .view_store import LoomStore

MAX_ROOTS = 8
MAX_ENTRIES = 4096
POLL_SECONDS = 0.5

Adapter = Callable[..., list[dict[str, Any]]]
# The artifact names the watcher reads (every other name is ignored). `state.json` is the runtime
# state file name; the rest are the conventional names of the other adapter families.
KNOWN_ARTIFACTS: Mapping[str, Adapter] = {
    "analysis.json": events_from_analysis,
    "git-replay-plan.json": events_from_git_plan,
    "scheduler-preparation.json": events_from_scheduler,
    "operator-grant.json": events_from_grant,
    "state.json": events_from_runtime_state,
    "hazard-notice.json": events_from_hazard_notice,
    "ownership-receipt.json": events_from_ownership_receipt,
    "gate-result.json": events_from_gate_result,
}


def root_label(index: int) -> str:
    """The label of the watched root at zero-based position `index`: "root 1", "root 2", ..."""
    return f"root {index + 1}"


class RootLabels:
    """Which watched root stored which `seq`, kept beside (never inside) the store's events."""

    def __init__(self) -> None:
        self.lock = threading.Lock()  # held by the watcher across append + record, and by readers
        self._by_seq: dict[int, str] = {}

    def record(self, seq: int, label: str) -> None:
        self._by_seq[seq] = label

    def prune(self, oldest_seq: int | None) -> None:
        """Forget the events the store's ring has evicted (those older than `oldest_seq`)."""
        for seq in [seq for seq in self._by_seq if oldest_seq is None or seq < oldest_seq]:
            del self._by_seq[seq]

    def copy(self) -> dict[int, str]:
        return dict(self._by_seq)


_REGISTRIES: "weakref.WeakKeyDictionary[LoomStore, RootLabels]" = weakref.WeakKeyDictionary()
_REGISTRIES_LOCK = threading.Lock()


def root_labels_of(store: LoomStore) -> RootLabels:
    """The registry belonging to `store` (created empty on first use, released with the store)."""
    with _REGISTRIES_LOCK:
        registry = _REGISTRIES.get(store)
        if registry is None:
            registry = _REGISTRIES[store] = RootLabels()
        return registry


def replay_with_roots(store: LoomStore) -> tuple[list[dict[str, Any]], dict[int, str]]:
    """`store.replay()` plus the `seq` -> root label map, read together so they agree."""
    registry = root_labels_of(store)
    with registry.lock:
        return store.replay(), registry.copy()


class TailError(ValueError):
    """The watcher could not be created; `reason` is a stable name."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class ArtifactTail:
    """Polls `roots` and appends adapter events to `store`. Use `poll_once` or `start`/`stop`."""

    def __init__(self, store: LoomStore, roots: list[str | os.PathLike[str]], *,
                 interval: float = POLL_SECONDS, max_roots: int = MAX_ROOTS,
                 max_entries: int = MAX_ENTRIES, max_file_bytes: int = MAX_ARTIFACT_BYTES,
                 known: Mapping[str, Adapter] | None = None,
                 wall_clock: Callable[[], float] = time.time) -> None:
        if interval <= 0 or max_roots < 1 or max_entries < 1 or max_file_bytes < 1:
            raise ValueError("limits are positive")
        self.store = store
        self.interval = interval
        self._max_entries = max_entries
        self._max_file_bytes = max_file_bytes
        self._known = dict(KNOWN_ARTIFACTS if known is None else known)
        self._wall_clock = wall_clock
        self._origin = time.monotonic()
        resolved: list[Path] = []
        for root in roots:
            try:
                path = Path(root).resolve(strict=True)
            except (OSError, RuntimeError) as exc:
                raise TailError("root", f"cannot resolve the watched root: {exc}") from exc
            if not path.is_dir():
                raise TailError("root", "a watched root is a directory")
            if not any(path == kept or kept in path.parents for kept in resolved):
                resolved = [kept for kept in resolved if path not in kept.parents]
                resolved.append(path)
        self._roots = resolved[:max_roots]
        self._labels = root_labels_of(store)
        self._roots_exceeded = len(resolved) > max_roots
        self._seen: dict[tuple[int, str], tuple[tuple[int, ...], str | None]] = {}
        self._reported: set[Any] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def roots(self) -> tuple[Path, ...]:
        """The watched roots in label order: `roots[0]` is "root 1" on the page."""
        return tuple(self._roots)

    # -- polling ---------------------------------------------------------------------------

    def poll_once(self) -> int:
        """Scan once; return the number of events appended to the store."""
        with self._lock:
            return self._scan()

    def _scan(self) -> int:
        appended = 0
        exceeded: set[Any] = set()
        if self._roots_exceeded:
            exceeded.add("roots")
        budget = [self._max_entries]
        present: set[tuple[int, str]] = set()
        for index, root in enumerate(self._roots):
            for relative, signature in self._walk(root, budget):
                key = (index, relative)
                present.add(key)
                if self._seen.get(key, (None, None))[0] == signature:
                    if signature[1] > self._max_file_bytes:
                        exceeded.add((index, relative, "size"))  # still over the bound: not reported again
                    continue
                appended += self._ingest(index, root, relative, signature, exceeded)
            if budget[0] < 0:
                break
        if budget[0] < 0:
            exceeded.add("entries")
        for key in [key for key in self._seen if key not in present and budget[0] >= 0]:
            del self._seen[key]  # a vanished file is read afresh if it returns
        for _ in exceeded - self._reported:
            appended += self._append(self._gap())
        self._reported = exceeded
        with self._labels.lock:
            self._labels.prune(self.store.stats()["oldestSeq"])
        return appended

    def _walk(self, root: Path, budget: list[int]):
        """Yield (posix path relative to `root`, stat signature) of known files, bounded.

        Files of one directory come in name order; directories come newest name first, so the plugin's
        `analysis-<UTC stamp>-<id>` report copies are read newest first and a store cap that is reached
        refuses the oldest copies (with its `stream-truncated` gap), never today's analysis."""
        stack: list[tuple[Path, str]] = [(root, "")]
        while stack:
            directory, prefix = stack.pop()
            try:
                with os.scandir(directory) as entries:
                    listing = sorted(islice(entries, max(budget[0], 0) + 1), key=lambda entry: entry.name)
            except OSError:
                continue
            subdirectories = []
            for entry in listing:
                budget[0] -= 1
                if budget[0] < 0:
                    return
                try:
                    info = entry.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISDIR(info.st_mode):
                    subdirectories.append((Path(entry.path), f"{prefix}{entry.name}/"))
                elif stat.S_ISREG(info.st_mode) and entry.name in self._known:
                    yield f"{prefix}{entry.name}", (info.st_mtime_ns, info.st_size, info.st_ino, info.st_dev)
            stack.extend(subdirectories)  # popped last-first: the newest-named directory is read first

    def _ingest(self, index: int, root: Path, relative: str, signature: tuple[int, ...],
                exceeded: set[Any]) -> int:
        key = (index, relative)
        digest = self._seen.get(key, (None, None))[1]
        if signature[1] > self._max_file_bytes:
            exceeded.add((index, relative, "size"))
            self._seen[key] = (signature, digest)
            return 0
        try:
            data = read_artifact(root, relative, limit=self._max_file_bytes)
        except AdapterError:
            # A link swapped in, grown past the limit while read, or not a regular file any more:
            # not read. The signature is kept, so the file is tried again only after it changes.
            self._seen[key] = (signature, digest)
            return 0
        self._seen[key] = (signature, hashlib.sha256(data).hexdigest())
        if self._seen[key][1] == digest:
            return 0
        adapter = self._known[relative.rpartition("/")[2]]
        arguments = {"now": int(self._wall_clock())} if adapter is events_from_grant else {}
        try:
            events = adapter(data, path=relative, **arguments)
        except (ValueError, TypeError):
            return 0  # a path the contract cannot name: nothing is stored for it
        stored = 0
        label = root_label(index)
        for event in events:
            try:
                stored += self._append(event, label)
            except LoomError:
                break  # an event the store refuses ends this file's events; the file is not retried
        return stored

    def _append(self, event: dict[str, Any], label: str | None = None) -> int:
        with self._labels.lock:  # store and label change together, so a reader never sees one without the other
            stored = self.store.append(event)
            if stored is not None and label is not None:
                self._labels.record(stored["seq"], label)
        return 0 if stored is None else 1

    def _gap(self) -> dict[str, Any]:
        return validate_event({
            "schemaVersion": SCHEMA_VERSION, "seq": 1, "kind": "observation.gap",
            "at": {"relMs": int((time.monotonic() - self._origin) * 1000), "basis": "viewer-monotonic"},
            "source": {"adapter": "viewer", "evidenceRef": None, "host": "braid", "verification": "derived"},
            "assurance": {"compatibilityClass": None, "notAGuarantee": True},
            "executionAuthorization": False,
            "data": {"reason": "stream-truncated", "strandId": None, "fromSeq": None, "toSeq": None},
        })

    # -- background thread -----------------------------------------------------------------

    def start(self) -> None:
        """Poll every `interval` seconds on a daemon thread until `stop`."""
        if self._thread is not None:
            raise RuntimeError("the watcher is already running")
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="view-tail", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.poll_once()
            except Exception:
                pass  # a failed scan is retried at the next interval; the viewer keeps serving
            self._stop.wait(self.interval)

    def stop(self) -> None:
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(5)

    def __enter__(self) -> "ArtifactTail":
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


__all__ = ["ArtifactTail", "KNOWN_ARTIFACTS", "MAX_ENTRIES", "MAX_ROOTS", "POLL_SECONDS", "RootLabels", "TailError",
           "replay_with_roots", "root_label", "root_labels_of"]
