# SPDX-License-Identifier: AGPL-3.0-only
"""Trusted bounded context assembly for the offline harness laboratory.

Original implementation; it maps only the concepts of harness2 ``core/context.py``
(evidence inventories, short pointers) to a positive manifest inventory with trust
labels, byte budgets and loss receipts. Entries come only from the verified
manifest context inventory that also holds ``context/<path>`` read authority;
retrieval (``disclose``) can only expand entries already in a package. Hidden
grader material is excluded by hash. Text is rendered as line-quoted data, so
instruction-like content cannot forge a trusted header. Pure: no filesystem,
process, model or network authority; every package has executionAuthorization
false.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import re
from types import MappingProxyType
from typing import Any

from .harness_manifest import HarnessManifest
from .system_one import digest, freeze, thaw

_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_NAMESPACES = ("source/", "base/", "candidate/", "lab/")
MAX_FEEDBACK_RECORDS = 64
MAX_RECORD_BYTES = 16_384
MAX_BUDGET_ENTRIES = 64
MAX_BUDGET_BYTES = 262_144
_FEEDBACK_TRUST = {"observed": "observed", "untrusted-text": "untrusted-evidence"}


class ContextError(ValueError):
    """A sanitized context-assembly refusal carrying a fixed reason code."""

    def __init__(self, reason: str = "invalid-context"):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class ContextBudget:
    """Frozen caps; they may only tighten the manifest's own context limits."""

    max_entries: int
    max_entry_bytes: int
    max_total_bytes: int
    excerpt_bytes: int


@dataclass(frozen=True)
class ContextPackage:
    """Immutable packaged entries and loss receipts; verified bytes stay private."""

    kind: str
    entries: tuple
    receipts: tuple
    budget: ContextBudget
    _verified: Mapping = field(repr=False, compare=False)

    @property
    def sha256(self) -> str:
        return digest(self._wire())

    def _wire(self) -> dict:
        return {"kind": self.kind, "entries": self.entries, "receipts": self.receipts,
                "budget": {"maxEntries": self.budget.max_entries,
                           "maxEntryBytes": self.budget.max_entry_bytes,
                           "maxTotalBytes": self.budget.max_total_bytes,
                           "excerptBytes": self.budget.excerpt_bytes},
                "executionAuthorization": False}

    def to_dict(self) -> dict:
        """Independent mutable copy of the wire record."""
        return thaw(self._wire())

    def render(self) -> str:
        """Line-quoted data blocks; text can never start a header line."""
        out = []
        for e in self.entries:
            out.append(f"<<<context id={e['id']} trust={e['trust']} "
                       f"disclosure={e['disclosure']} sha256={e['sha256']}>>>")
            out.extend("| " + line for line in e["text"].split("\n"))
            out.append(f"<<<end id={e['id']}>>>")
        return "\n".join(out)


def _check_budget(budget: ContextBudget, max_entries: int, max_bytes: int) -> None:
    values = (budget.max_entries, budget.max_entry_bytes, budget.max_total_bytes,
              budget.excerpt_bytes)
    ok = all(type(v) is int for v in values) and budget.max_entries >= 1 and \
        budget.max_entry_bytes >= 1 and budget.excerpt_bytes >= 0 and \
        budget.max_total_bytes >= 1 and budget.max_entries <= max_entries and \
        budget.max_total_bytes <= max_bytes and budget.max_entry_bytes <= budget.max_total_bytes
    if not ok:
        raise ContextError("invalid-budget")


def _cut(data: bytes, limit: int) -> bytes:
    """Longest valid-UTF-8 prefix of at most ``limit`` bytes."""
    return data[:limit].decode("utf-8", "ignore").encode("utf-8")


def _receipt(entry_id: str, reason: str, original: int, kept: int, hex_digest: str) -> dict:
    return {"id": entry_id, "reason": reason, "originalBytes": original,
            "keptBytes": kept, "sha256": hex_digest}


def _entry(entry_id: str, label: str | None, trust: str, data: bytes, kept: bytes) -> dict:
    return {"id": entry_id, "path": label, "trust": trust, "sizeBytes": len(data),
            "keptBytes": len(kept), "sha256": sha256(data).hexdigest(),
            "disclosure": "full" if len(kept) == len(data) else "excerpt",
            "text": kept.decode("utf-8")}


def _pack(kind: str, candidates: list, omitted: list, budget: ContextBudget,
          graders: frozenset) -> ContextPackage:
    """candidates: (id, label, trust, bytes) already inventory-verified, in order."""
    entries, receipts, verified, used = [], list(omitted), {}, 0
    for entry_id, label, trust, data in candidates:
        digest_hex = sha256(data).hexdigest()
        if digest_hex in graders:
            receipts.append(_receipt(entry_id, "excluded-grader", len(data), 0, digest_hex))
            continue
        if len(entries) >= budget.max_entries:
            receipts.append(_receipt(entry_id, "budget-entries", len(data), 0, digest_hex))
            continue
        take = min(len(data), budget.max_entry_bytes, budget.excerpt_bytes,
                   budget.max_total_bytes - used)
        kept = _cut(data, take)
        if data and not kept:
            reason = "budget-excerpt" if min(budget.max_entry_bytes,
                                             budget.excerpt_bytes) == 0 else "budget-total"
            receipts.append(_receipt(entry_id, reason, len(data), 0, digest_hex))
            continue
        if len(kept) < len(data):
            receipts.append(_receipt(entry_id, "truncated", len(data), len(kept), digest_hex))
        used += len(kept)
        entries.append(_entry(entry_id, label, trust, data, kept))
        verified[entry_id] = data
    return ContextPackage(kind, freeze(entries), freeze(receipts), budget,
                          MappingProxyType(verified))


def _unsafe(path: str) -> bool:
    return (not isinstance(path, str) or path.startswith("/") or ".." in path.split("/")
            or path.startswith(_NAMESPACES) or "\\" in path)


def assemble_context(manifest: HarnessManifest, contents: Mapping[str, bytes], *,
                     budget: ContextBudget,
                     grader_hashes: frozenset = frozenset()) -> ContextPackage:
    """Package selected, read-authorized, hash-verified manifest context entries."""
    data = manifest.data
    limits = data["limits"]
    _check_budget(budget, limits["maxContextEntries"], limits["maxContextBytes"])
    graders = frozenset(grader_hashes) | {
        data["task"]["fixtureSha256"], data["verifier"]["sha256"],
        data["normalizer"]["sha256"]}
    if not isinstance(contents, Mapping) or not all(type(k) is str for k in contents):
        raise ContextError("invalid-context")
    readable = set(data["effects"]["read"])
    inventory = {row["path"] for row in data["context"]}
    omitted, candidates = [], []

    def _omit(row, reason):
        omitted.append(_receipt(row["id"], reason, row["sizeBytes"], 0, row["sha256"]))

    for path in sorted(p for p in contents if p not in inventory):
        reason = "cross-workspace" if _unsafe(path) else "not-in-inventory"
        omitted.append(_receipt(str(path), reason, 0, 0, "0" * 64))
    for row in data["context"]:
        raw = contents.get(row["path"])
        if not row["selected"]:
            _omit(row, "unselected")
        elif "context/" + row["path"] not in readable:
            _omit(row, "no-read-authority")
        elif raw is None:
            _omit(row, "missing-content")
        elif type(raw) is not bytes or len(raw) != row["sizeBytes"] or \
                sha256(raw).hexdigest() != row["sha256"]:
            _omit(row, "stale-content")
        else:
            try:
                raw.decode("utf-8")
            except UnicodeDecodeError:
                _omit(row, "unsupported-encoding")
                continue
            candidates.append((row["id"], row["path"], row["trust"], raw))
    return _pack("context", candidates, omitted, budget, graders)


def disclose(package: ContextPackage, ref: str) -> ContextPackage:
    """Expand one packaged entry (by id or path) as far as the frozen budget allows."""
    target = next((e["id"] for e in package.entries if ref in (e["id"], e["path"])), None)
    if target is None:
        raise ContextError("not-in-inventory")
    budget = package.budget
    used = sum(e["keptBytes"] for e in package.entries if e["id"] != target)
    entries = []
    receipts = [r for r in package.receipts if r["reason"] != "truncated" or r["id"] != target]
    for e in package.entries:
        if e["id"] != target:
            entries.append(e)
            continue
        raw = package._verified[target]
        kept = _cut(raw, min(len(raw), budget.max_entry_bytes, budget.max_total_bytes - used))
        if len(kept) < len(raw):
            receipts.append(_receipt(target, "truncated", len(raw), len(kept),
                                     sha256(raw).hexdigest()))
        entries.append(_entry(target, e["path"], e["trust"], raw, kept))
    return ContextPackage(package.kind, freeze(entries), freeze(receipts), budget,
                          package._verified)


def build_feedback(records: Any, *, budget: ContextBudget,
                   grader_hashes: frozenset = frozenset()) -> ContextPackage:
    """Bound caller-supplied feedback text; free text is always untrusted evidence."""
    if type(records) is not list:
        raise ContextError("invalid-feedback")
    # Feedback has no manifest, so fixed module caps bound the input and the budget.
    _check_budget(budget, MAX_BUDGET_ENTRIES, MAX_BUDGET_BYTES)
    if len(records) > MAX_FEEDBACK_RECORDS:
        raise ContextError("input-budget-exceeded")
    candidates, seen = [], set()
    for record in records:
        if type(record) is not dict or set(record) != {"id", "kind", "text"} or \
                type(record["id"]) is not str or _ID.fullmatch(record["id"]) is None or \
                record["id"] in seen or record["kind"] not in _FEEDBACK_TRUST or \
                type(record["text"]) is not str:
            raise ContextError("invalid-feedback")
        if len(record["text"]) > MAX_RECORD_BYTES:  # chars <= bytes: refuse before encoding
            raise ContextError("input-budget-exceeded")
        try:
            raw = record["text"].encode("utf-8")
        except UnicodeEncodeError:
            raise ContextError("invalid-feedback") from None
        if len(raw) > MAX_RECORD_BYTES:
            raise ContextError("input-budget-exceeded")
        seen.add(record["id"])
        candidates.append((record["id"], None, _FEEDBACK_TRUST[record["kind"]], raw))
    return _pack("feedback", candidates, [], budget, frozenset(grader_hashes))
