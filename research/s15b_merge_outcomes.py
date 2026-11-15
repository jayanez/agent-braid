# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T405 (REQ-402): structural merge-outcome records of the owner's parallel work.

The recorder (`scripts/spec066_record_merge_outcomes.py`) writes one record per pair of merged
branch heads: the `git merge-tree --write-tree` verdict (`merge-clean` | `merge-conflict`) and the
salted pseudonym lists of the pair's resources, computed exactly as a System One shadow episode
computes them. The observer reads these records through `MergeOutcomeSource` and joins them to
shadow episodes; nothing here stores a path, ref, commit id, author, message or workspace id.

The file lives in a gitignored private directory under the admitted workspace's registered source
root, so the W0 corpus gate admits it. It is a rolling view: every run merges the new records into
the retained ones (identical bodies collapse) and drops records older than the retention window.
Consent: source family "real runs (runtime conflict, merge conflict, verify result)" of the T101
record; owner-authored commits only; structural only; 30 days. Nothing here widens that scope.
"""
from __future__ import annotations

from collections import Counter
from datetime import date
import json
import os
from pathlib import Path
import re
import secrets
import stat

from agent_braid import plugin_registry
from research import s15b_corpus_gate as gate, s15b_outcome_observer as observer

FAMILY = "real runs (runtime conflict, merge conflict, verify result)"
SCHEMA = "agent-braid-s1-merge-outcome/v0.1"
KINDS = ("merge-clean", "merge-conflict")
DIRECTORY = (".claude", "agent-braid-s1")  # gitignored by the repository's `.claude/*` rule
FILENAME = "merge-outcomes.jsonl"
MAX_RECORDS = 4096
MAX_BYTES = 4 * 1024 * 1024
MAX_VARIANTS = 64
FIELDS = frozenset({"schema", "day", "outcomeKind", "variants", "canonicalSharedCount", "executionAuthorization"})
_HASH = re.compile(r"^[0-9a-f]{16}$")


class MergeOutcomeError(Exception):
    """A fixed code; the message carries nothing else."""

    CODES = ("registry-unavailable", "output-not-ignored", "store-unsafe", "invalid-store", "store-full")

    def __init__(self, code: str) -> None:
        if code not in self.CODES:
            raise ValueError("unknown merge-outcome error code")
        self.code = code
        super().__init__(code)


def source_root(*, home: Path | None = None) -> Path:
    """The admitted workspace's registered source root, from the plugin registry."""
    try:
        rows = plugin_registry.inspect_registry(home)["value"]["workspaces"]
        row = next(item for item in rows if item["workspaceId"] == gate.ADMITTED_WORKSPACE_ID)
        return Path(os.path.realpath(row["sourceRoot"]))
    except (plugin_registry.RegistryError, OSError, KeyError, TypeError, ValueError, StopIteration):
        raise MergeOutcomeError("registry-unavailable") from None


def store_directory(*, home: Path | None = None) -> Path:
    return source_root(home=home).joinpath(*DIRECTORY)


def store_path(*, home: Path | None = None) -> Path:
    return store_directory(home=home) / FILENAME


def _hash_list(value) -> bool:
    return (isinstance(value, list) and len(value) <= observer.shadow.MAX_HASHES
            and all(isinstance(item, str) and _HASH.fullmatch(item) for item in value))


def validate_record(record) -> dict:
    """The closed record: day, kind, pseudonym lists and counts only."""
    ok = (type(record) is dict and set(record) == FIELDS and record["schema"] == SCHEMA
          and record["executionAuthorization"] is False
          and type(record["day"]) is str and date.fromisoformat(record["day"]).isoformat() == record["day"]
          and record["outcomeKind"] in KINDS
          and type(record["canonicalSharedCount"]) is int and 0 <= record["canonicalSharedCount"] <= 4096
          and isinstance(record["variants"], list) and 0 < len(record["variants"]) <= MAX_VARIANTS
          and all(type(v) is dict and set(v) == {"left", "right", "shared"} and all(_hash_list(x) for x in v.values())
                  and v["left"] and v["right"] for v in record["variants"]))
    if not ok:
        raise MergeOutcomeError("invalid-store")
    return record


def make_record(kind: str, day: date, variants, canonical_shared: int) -> dict:
    return validate_record({"schema": SCHEMA, "day": day.isoformat(), "outcomeKind": kind,
                            "variants": [{key: list(v[key]) for key in ("left", "right", "shared")} for v in variants],
                            "canonicalSharedCount": min(canonical_shared, 4096), "executionAuthorization": False})


def _body(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


def read_records(directory: Path, today: date) -> list:
    """Retained records (older ones are dropped); an absent file is empty; an unsafe or invalid one raises."""
    target = directory / FILENAME
    if not target.exists():
        return []
    try:
        data = observer._read_private(target, MAX_BYTES)
    except (OSError, observer.ObserverRefused):
        raise MergeOutcomeError("store-unsafe") from None
    cutoff = gate.retention_cutoff(today)
    records = []
    for line in data.split(b"\n"):
        if not line:
            continue
        try:
            record = validate_record(json.loads(line))
        except (ValueError, RecursionError, UnicodeError, KeyError, TypeError):
            raise MergeOutcomeError("invalid-store") from None
        if date.fromisoformat(record["day"]) >= cutoff:
            records.append(record)
    return records


def write_records(directory: Path, new_records, today: date) -> Counter:
    """Merge `new_records` into the retained ones and replace the file atomically (0600)."""
    counts = Counter()
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = os.lstat(directory)
    except OSError:
        raise MergeOutcomeError("store-unsafe") from None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise MergeOutcomeError("store-unsafe")
    kept = read_records(directory, today)
    known = {_body(record) for record in kept}
    for record in new_records:
        validate_record(record)
        if _body(record) in known:
            counts["duplicate"] += 1
            continue
        known.add(_body(record))
        kept.append(record)
        counts["written"] += 1
    payload = "".join(_body(record).decode() + "\n" for record in kept).encode()
    if len(kept) > MAX_RECORDS or len(payload) > MAX_BYTES:
        raise MergeOutcomeError("store-full")
    temporary = directory / f".merge-outcomes.{secrets.token_hex(8)}.tmp"
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, directory / FILENAME)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise MergeOutcomeError("store-unsafe") from None
    return counts


class MergeOutcomeSource:
    """An observer outcome source over the recorder's file; `root` is what the corpus gate must admit.

    Rows are `HashedRow`s (pseudonyms only), so the observer matches them to episodes without any resource.
    """

    def __init__(self, directory: Path) -> None:
        self.root = Path(directory)

    def outcomes(self, window: tuple):
        _, last = window
        for record in read_records(self.root, last):
            yield observer.HashedRow(record["outcomeKind"], date.fromisoformat(record["day"]),
                                     tuple(record["variants"]))


def purge(*, home: Path | None = None) -> dict:
    """Remove the recorder's file (and its directory when empty); revocation for this store."""
    try:
        directory = store_directory(home=home)
    except MergeOutcomeError:
        return {"status": "empty"}
    target = directory / FILENAME
    if not target.exists() and not target.is_symlink():
        return {"status": "empty"}
    target.unlink()
    try:
        directory.rmdir()
    except OSError:
        pass  # other files in the directory are not ours
    return {"status": "purged", "filesRemoved": 1}
