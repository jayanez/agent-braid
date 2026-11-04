# SPDX-License-Identifier: AGPL-3.0-only
"""Root identity for watched artifact roots, kept beside the store (SPEC-061 REQ-010, T044, T047).

The event contract names no root. The watcher (`view_tail`) gives each watched root a stable, non-path label
("root 1" to "root 8", in start order) and records it per `seq` in a `RootLabels` registry that belongs to
one store. The server reads the labels through `replay_with_roots` without importing the watcher.
"""
from __future__ import annotations

import threading
import weakref
from typing import Any

from .view_store import LoomStore


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


__all__ = ["RootLabels", "replay_with_roots", "root_label", "root_labels_of"]
