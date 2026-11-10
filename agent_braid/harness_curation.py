# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T008 experience curation and context revalidation under drift.

Original implementation built on ``harness_experience``; it adds no second store. It is
pure and offline: no file, clock, host, model or network access, and every result keeps
``executionAuthorization`` false. Nothing here enables anything.

* ``retrieve``/``compact`` give bounded retrieval. Entries are served or omitted whole;
  text is never truncated or rewritten, so no semantic rewrite can become memory. Omitted
  entries leave a hash receipt. Entries whose producer or approving actor is absent from
  the caller's trusted registry are excluded, because decoding proves shape, not authorship.
  Entries whose cue matches after case/whitespace normalization but whose kinds differ
  are withheld together (a heuristic: paraphrased cues are not detected); duplicates keep
  the lowest id. A caller-held ledger of revoked hashes keeps lineage-revoked entries out
  even when they were added after the revocation. The trust registry is a hygiene filter
  on self-asserted ids, not authentication.
* ``curate`` expires, and withdraws stale or contradicted active entries back to
  ``validated`` (the store has no active-to-quarantined transition; ``validated`` entries
  are never served, and re-activation needs a fresh human decision). ``revalidate``
  needs a validator from a trusted registry and refuses contradicted or expired entries;
  it does not record the validation evidence hash. Store errors (unknown entry, time
  regression, invalid context) pass through as ``ExperienceError``.
* ``propagate_revocation`` revokes every live entry that cites a revoked hash as supporting
  evidence or as its source record, transitively; original evidence is never rewritten.
* ``compare_variants`` is a SYNTHETIC offline control. Outcomes, ``heldOut`` and the library
  family list are caller-declared and not verified against the store; only ``servedIds``
  derive from it, and metrics are aggregation of the declared outcomes. Arms: ``no-library``
  serves nothing; ``library-uncurated`` is the raw ``ExperienceStore.query`` (which already
  drops stale, expired and contradicted entries) with no budget, trust, conflict or
  duplicate screening; ``library-curated`` adds those. It keeps failures, negative transfer
  and costs, ranks no variant and makes no utility claim.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .harness_experience import (
    ExperienceError, ExperienceStore, TERMINAL, _contradicted, _expired, _hash, _id, _stale, _tick)
from .system_one import canonical, digest, thaw

COMPARISON_FORMAT = "braid-harness-curation-comparison/v0.1"
SCOPE = "synthetic-offline-control"
MAX_SERVED = 16
MAX_BYTES = 16_384
MAX_TASKS = 16
MAX_COST = 1 << 40
ARMS = ("no-library", "library-uncurated", "library-curated")
_TASK_KEYS = {"id", "family", "startedAt", "heldOut", "context"}


class CurationError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-input"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-input") -> None:
    if not condition:
        raise CurationError(reason)


def _store(store: Any) -> None:
    _require(type(store) is ExperienceStore, "invalid-store")


def _bound(value: Any, ceiling: int) -> int:
    _require(type(value) is int and 1 <= value <= ceiling, "invalid-budget")
    return value


def _registry(value: Any) -> frozenset:
    _require(type(value) is frozenset and value and all(map(_id, value)), "invalid-registry")
    return value


def canonical_row_bytes(row: Mapping) -> bytes:
    """Canonical bytes of a served row; the unit the byte budget counts."""
    return canonical(row)


@dataclass(frozen=True)
class Retrieval:
    """Advisory-data rows an online task may read, plus audit exclusions and hash receipts."""

    served: tuple[Mapping[str, Any], ...]
    excluded: tuple[tuple[str, str], ...]
    omitted: tuple[Mapping[str, Any], ...]
    max_entries: int
    max_bytes: int

    @property
    def executionAuthorization(self) -> bool:
        return False

    @property
    def sha256(self) -> str:
        return digest({"served": self.served, "excluded": self.excluded, "omitted": self.omitted})


def _fit(rows, max_entries: int, max_bytes: int):
    served, omitted, used = [], [], 0
    for row in rows:
        size = len(canonical_row_bytes(row))
        if len(served) < max_entries and used + size <= max_bytes:
            served.append(row)
            used += size
        else:
            omitted.append(MappingProxyType({"id": row["id"], "contentSha256": row["contentSha256"],
                                             "bytes": size}))
    return tuple(served), tuple(omitted)


def _row(entry, served: Mapping) -> Mapping:
    evidence = entry.data["evidence"]
    return MappingProxyType({
        **served, "producer": entry.data["provenance"]["producer"],
        "sourceRecordSha256": entry.data["provenance"]["sourceRecordSha256"],
        "supportingSha256s": tuple(r["sha256"] for r in evidence if r["polarity"] == "supporting"),
        "contrarySha256s": tuple(r["sha256"] for r in evidence if r["polarity"] == "contrary")})


def _trusted(entry, producers: frozenset, actors: frozenset) -> bool:
    activation = entry.data["activation"]
    return (entry.data["provenance"]["producer"] in producers and activation is not None
            and activation["actor"]["id"] in actors)


def _cue(entry) -> str:
    return " ".join(entry.data["cue"].casefold().split())


def _screen(entries: list, excluded: list) -> list:
    """Withhold different-kind conflicts on one normalized cue and drop duplicates."""
    kinds: dict[str, set] = {}
    for entry in entries:
        kinds.setdefault(_cue(entry), set()).add(entry.data["kind"])
    kept, seen = [], set()
    for entry in entries:
        key = (_cue(entry), " ".join(entry.data["lesson"].casefold().split()), entry.data["kind"])
        if len(kinds[_cue(entry)]) > 1:
            excluded.append((entry.id, "entry-conflict"))
        elif key in seen:
            excluded.append((entry.id, "duplicate"))
        else:
            seen.add(key)
            kept.append(entry)
    return kept


def _lineage(entry) -> set:
    cited = {r["sha256"] for r in entry.data["evidence"] if r["polarity"] == "supporting"}
    return cited | {entry.data["provenance"]["sourceRecordSha256"]}


def retrieve(store: ExperienceStore, context: Any, *, max_entries: int, max_bytes: int,
             trusted_producers: frozenset, trusted_actors: frozenset,
             revoked_sha256s: frozenset = frozenset()) -> Retrieval:
    """Bounded, trust-checked, conflict-free retrieval over ``ExperienceStore.query``."""
    _store(store)
    max_entries, max_bytes = _bound(max_entries, MAX_SERVED), _bound(max_bytes, MAX_BYTES)
    producers, actors = _registry(trusted_producers), _registry(trusted_actors)
    _require(type(revoked_sha256s) is frozenset and all(map(_hash, revoked_sha256s)), "invalid-revoked")
    result = store.query(context)
    excluded = list(result.excluded)
    entries = []
    for row in result.served:
        entry = store.get(row["id"])
        if _lineage(entry) & revoked_sha256s:
            excluded.append((entry.id, "revoked-lineage"))
        elif _trusted(entry, producers, actors):
            entries.append((entry, row))
        else:
            excluded.append((entry.id, "untrusted-provenance"))
    rows = {e.id: _row(e, r) for e, r in entries}
    kept = _screen([e for e, _ in entries], excluded)
    served, omitted = _fit([rows[e.id] for e in kept], max_entries, max_bytes)
    excluded += [(o["id"], "over-budget") for o in omitted]
    return Retrieval(served, tuple(sorted(excluded)), omitted, max_entries, max_bytes)


def compact(retrieval: Retrieval, *, max_entries: int, max_bytes: int) -> Retrieval:
    """Shrink a retrieval to a smaller budget by omitting whole rows; text is never rewritten."""
    _require(type(retrieval) is Retrieval and all(
        type(r) is MappingProxyType and _id(r.get("id")) and _hash(r.get("contentSha256"))
        for r in retrieval.served), "invalid-retrieval")
    max_entries, max_bytes = _bound(max_entries, MAX_SERVED), _bound(max_bytes, MAX_BYTES)
    _require(max_entries <= retrieval.max_entries and max_bytes <= retrieval.max_bytes, "budget-grows")
    served, omitted = _fit(retrieval.served, max_entries, max_bytes)
    excluded = retrieval.excluded + tuple((o["id"], "over-budget") for o in omitted)
    return Retrieval(served, tuple(sorted(excluded)), retrieval.omitted + omitted, max_entries, max_bytes)


@dataclass(frozen=True)
class CurationResult:
    store: ExperienceStore
    actions: tuple[tuple[str, str], ...]
    needs_revalidation: tuple[str, ...]
    conflicts: tuple[tuple[str, str], ...]

    @property
    def executionAuthorization(self) -> bool:
        return False


def _conflicts(store: ExperienceStore) -> tuple[tuple[str, str], ...]:
    live = [e for e in store.entries if e.state == "active"]
    return tuple((a.id, b.id) for i, a in enumerate(live) for b in live[i + 1:]
                 if _cue(a) == _cue(b) and a.data["kind"] != b.data["kind"])


def curate(store: ExperienceStore, now: int) -> CurationResult:
    """Expire, and withdraw stale or contradicted active entries; report the rest."""
    _store(store)
    _require(_tick(now), "invalid-time")
    actions = []
    current = store.sweep(now)
    actions += [(e.id, "expired") for e in current.entries
                if e.state == "expired" and store.get(e.id).state != "expired"]
    for entry in current.entries:
        if entry.state != "active":
            continue
        if _contradicted(entry.data):
            current = current.rollback(entry.id, now, "contradicted")
            actions.append((entry.id, "withdrawn-contradicted"))
        elif _stale(entry.data, now):
            current = current.rollback(entry.id, now, "stale-revalidation")
            actions.append((entry.id, "withdrawn-stale"))
    stale = tuple(e.id for e in current.entries
                  if e.state in ("validated", "active") and _stale(e.data, now))
    return CurationResult(current, tuple(actions), stale, _conflicts(current))


def revalidate(store: ExperienceStore, entry_id: str, validation: Any, at: int, *,
               trusted_validators: frozenset) -> ExperienceStore:
    """Independent revalidation by a trusted validator; never activates."""
    _store(store)
    _require(_tick(at), "invalid-time")
    validators = _registry(trusted_validators)
    _require(type(validation) is dict and validation.get("validator") in validators, "untrusted-validator")
    entry = store.get(entry_id)
    _require(not _contradicted(entry.data), "contradicted")
    _require(not _expired(entry.data, at), "expired")
    return store.revalidate(entry_id, validation, at)


@dataclass(frozen=True)
class RevocationResult:
    store: ExperienceStore
    revoked: tuple[str, ...]

    @property
    def executionAuthorization(self) -> bool:
        return False


def propagate_revocation(store: ExperienceStore, revoked_sha256s: Any, at: int,
                         reason: str) -> RevocationResult:
    """Revoke live entries citing a revoked hash (evidence or source record), transitively."""
    _store(store)
    _require(type(revoked_sha256s) in (list, tuple) and 1 <= len(revoked_sha256s) <= 64
             and all(map(_hash, revoked_sha256s)) and _tick(at) and _id(reason), "invalid-input")
    pending, revoked = set(revoked_sha256s), []
    changed = True
    while changed:
        changed = False
        for entry in store.entries:
            if entry.state in TERMINAL:
                continue
            if _lineage(entry) & pending:
                pending |= {entry.sha256, entry.content_sha256}
                store = store.revoke(entry.id, at, reason)
                revoked.append(entry.id)
                changed = True
    return RevocationResult(store, tuple(sorted(revoked)))


def _cutoff(store: ExperienceStore) -> int:
    return max((e.data["history"][-1]["at"] for e in store.entries), default=0)


def _check_tasks(store: ExperienceStore, tasks: Any, families: Any) -> list:
    _require(type(tasks) is list and 1 <= len(tasks) <= MAX_TASKS, "invalid-tasks")
    _require(type(families) in (list, tuple) and families and all(map(_id, families))
             and len(set(families)) == len(families), "invalid-families")
    cutoff, last = _cutoff(store), -1
    for task in tasks:
        _require(type(task) is dict and set(task) == _TASK_KEYS and _id(task["id"]) and _id(task["family"])
                 and task["heldOut"] is True and _tick(task["startedAt"]), "invalid-tasks")
        _require(task["family"].casefold() not in {f.casefold() for f in families}, "family-leak")
        _require(task["startedAt"] > cutoff and task["startedAt"] > last, "temporal-order")
        _require(type(task["context"]) is dict and task["context"].get("taskStartedAt") == task["startedAt"],
                 "invalid-tasks")
        last = task["startedAt"]
    _require(len({t["id"] for t in tasks}) == len(tasks), "invalid-tasks")
    return tasks


def _check_outcomes(tasks: list, outcomes: Any) -> None:
    _require(type(outcomes) is dict and set(outcomes) == {t["id"] for t in tasks}, "outcomes-mismatch")
    for per_task in outcomes.values():
        _require(type(per_task) is dict and set(per_task) == set(ARMS), "outcomes-mismatch")
        for cell in per_task.values():
            _require(type(cell) is dict and set(cell) == {"passed", "cost"} and type(cell["passed"]) is bool
                     and type(cell["cost"]) is int and 0 <= cell["cost"] <= MAX_COST, "invalid-outcome")


def compare_variants(store: ExperienceStore, tasks: Any, outcomes: Any, *, library_families: Any,
                     outcomes_source: str, max_entries: int, max_bytes: int,
                     trusted_producers: frozenset, trusted_actors: frozenset) -> dict:
    """Synthetic offline comparison of no-library, uncurated and curated library arms."""
    _store(store)
    _require(outcomes_source == "synthetic", "outcomes-not-synthetic")
    tasks = _check_tasks(store, tasks, library_families)
    _check_outcomes(tasks, outcomes)
    trust = dict(trusted_producers=trusted_producers, trusted_actors=trusted_actors)
    curated, rows = store, []
    for task in tasks:
        raw = [r["id"] for r in store.query(task["context"]).served]
        curated = curate(curated, task["startedAt"]).store
        kept = retrieve(curated, task["context"], max_entries=max_entries, max_bytes=max_bytes, **trust)
        rows.append({"id": task["id"], "family": task["family"], "startedAt": task["startedAt"],
                     "servedIds": {"no-library": [], "library-uncurated": raw,
                                   "library-curated": [r["id"] for r in kept.served]},
                     "outcomes": thaw(outcomes[task["id"]])})
    arms = {a: {"tasks": len(rows), "passes": sum(r["outcomes"][a]["passed"] for r in rows),
                "failures": [r["id"] for r in rows if not r["outcomes"][a]["passed"]],
                "totalCost": sum(r["outcomes"][a]["cost"] for r in rows)} for a in ARMS}
    transfer = {a: [r["id"] for r in rows if r["outcomes"]["no-library"]["passed"]
                    and not r["outcomes"][a]["passed"]] for a in ARMS[1:]}
    families = {}
    for r in rows:
        for a in ARMS:
            cell = families.setdefault(r["family"], {}).setdefault(a, {"tasks": 0, "passes": 0, "cost": 0})
            cell["tasks"] += 1
            cell["passes"] += r["outcomes"][a]["passed"]
            cell["cost"] += r["outcomes"][a]["cost"]
    report = {"format": COMPARISON_FORMAT, "scope": SCOPE, "utilityClaim": False,
              "executionAuthorization": False, "outcomesSource": outcomes_source,
              "storeSha256": store.sha256, "libraryCutoff": _cutoff(store),
              "libraryFamilies": sorted(library_families), "arms": arms, "perFamily": families,
              "negativeTransfer": transfer, "tasks": rows, "outcomesSha256": digest(outcomes)}
    return report | {"sha256": digest(report)}
