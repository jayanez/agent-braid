# SPDX-License-Identifier: AGPL-3.0-only
"""Complete experiment cost reconciliation and per-arm utility; offline, no authority.

The caller supplies a ledger: the registered unit population shared by every arm, the
attempts started on it, cost entries for each chain phase and the SPEC-048 reservation
receipts those attempts consumed. Every measurement is either observed (an exact
integer, a declared unit and the hash of the evidence it was read from) or unknown.
A dimension missing from an entry is unknown, and a total with no observation at all
is unknown: arithmetic never turns a missing invoice or token count into zero.

Dimensions stay separate and are never blended: additional cash, subscription quota
(never converted to cash; existing subscriptions are not zero-cost), wall and CPU
time, peak RSS, disk, journal bytes, processes and human time. Units convert by exact
integer factors into one canonical unit per dimension; rationals are reported as
integers or exact ``"n/d"`` strings.

A shared entry names its attempts and a rule. Per-arm costs carry sensitivity bounds:
``lower`` counts only what certainly belongs to the arm, ``upper`` charges it every
shared entry it touches, and ``point`` applies the declared rule (``equal`` splits by
attempt count; ``unallocated`` is left out and listed). Any unknown makes ``point``
and ``upper`` unknown while ``lower`` stays the known sum.

Additional cash is capped at EUR 0 (SPEC-049 T002 D2); numeric time/quota caps are
deferred until a native quota reading, so none is applied here. Unknown or nonzero
cash, open or missing reservations, journal overruns and unaccounted cleanup block an
economic claim, as does a started attempt with no cost entry beyond cleanup; an
unblocked report is not an acceptance. An attempt's journal bytes are checked against
its reservation under the declared allocation: a point estimate above it is an
overrun; an unknown point, or an upper bound above it because of an unallocated shared
entry, is unreconciled. Each value is bounded by ``MAX_VALUE``; totals are exact
integers that may exceed it. Nothing here reads a clock, file, host or model, and
``executionAuthorization`` is always false.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import re
from typing import Any

from .harness_admission import Reservation
from .harness_observation import _ALL_TERMINALS
from .system_one import InvalidDecision, canonical, digest, freeze, thaw

FORMAT = "braid-harness-cost-report/v0.1"
PHASES = ("setup", "context", "proposal", "probe", "retry", "selection", "reflection",
          "verification", "recovery", "review", "cleanup")
ATTEMPT_TERMINALS = _ALL_TERMINALS
OUTCOMES = ("correct", "incorrect", "ungraded")
RULES = ("equal", "unallocated")
CASH_CAP_EUR_CENTS = 0
MAX_ATTEMPTS = 1024
MAX_ENTRIES = 4096
MAX_TARGET_REFS = 65_536  # attempt references across all entries; bounds reconciliation work
MAX_VALUE = 1 << 53
_MS = {"ms": 1, "s": 1000, "min": 60_000}
_BYTES = {"byte": 1, "kib": 1024, "mib": 1 << 20}
# dimension -> (aggregation, {unit: factor into the canonical unit, whose factor is 1})
DIMENSIONS = {
    "cash": ("sum", {"eur-cent": 1, "eur": 100}),
    "quota": ("sum", {"token": 1, "ktoken": 1000}),
    "wall": ("sum", _MS),
    "cpu": ("sum", _MS),
    "rss": ("max", _BYTES),
    "disk": ("sum", _BYTES),
    "journal": ("sum", _BYTES),
    "processes": ("sum", {"count": 1}),
    "human": ("sum", {"s": 1, "min": 60}),
}
UNITS = {dim: next(u for u, f in units.items() if f == 1) for dim, (_, units) in DIMENSIONS.items()}
_SUMMED = tuple(dim for dim, (agg, _) in DIMENSIONS.items() if agg == "sum")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_REASON = re.compile(r"[a-z0-9][a-z0-9-]{0,63}\Z")
_RECONCILIATION_BLOCKERS = (("open-reservation", "openReservations"),
                            ("unreserved-attempt", "unreservedAttempts"),
                            ("incomplete-attempt-costs", "attemptsWithoutCost"),
                            ("journal-reservation-exceeded", "journalExceeded"),
                            ("journal-unreconciled", "journalUnreconciled"),
                            ("cleanup-unaccounted", "cleanupUnaccounted"))
_ATTEMPT_KEYS = {"id", "unitId", "arm", "reservationSha256", "observationSha256", "terminal",
                 "outcome"}


class CostError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-ledger"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-ledger") -> None:
    if not condition:
        raise CostError(reason)


def _is_hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _ids(value: Any, reason: str) -> list[str]:
    _require(type(value) in (list, tuple) and len(value) <= MAX_ATTEMPTS and
             all(type(v) is str and _ID.fullmatch(v) for v in value) and
             len(set(value)) == len(value), reason)
    return list(value)


def _q(value: Fraction) -> int | str:
    return value.numerator if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _measure(dim: str, raw: Any) -> int | None:
    """Canonical integer value, or None when the measurement is unknown or absent."""
    if raw is None:
        return None
    _require(isinstance(raw, Mapping), "invalid-measure")
    if raw.get("status") == "unknown":
        _require(set(raw) == {"status", "reason"} and type(raw["reason"]) is str and
                 _REASON.fullmatch(raw["reason"]) is not None, "invalid-measure")
        return None
    _require(raw.get("status") == "observed" and
             set(raw) == {"status", "value", "unit", "evidenceSha256"} and
             _is_hash(raw["evidenceSha256"]), "invalid-measure")
    factor = DIMENSIONS[dim][1].get(raw["unit"]) if type(raw["unit"]) is str else None
    _require(factor is not None, "invalid-unit")
    value = raw["value"]
    _require(type(value) is int and 0 <= value and value * factor <= MAX_VALUE, "invalid-value")
    return value * factor


@dataclass(frozen=True)
class _Entry:
    id: str
    phase: str
    targets: frozenset[str]
    rule: str  # "direct" for a single-attempt entry
    values: Mapping[str, int | None]


def _entry(raw: Any, attempts: Mapping[str, Mapping]) -> _Entry:
    _require(isinstance(raw, Mapping), "invalid-entry")
    shared = "shared" in raw
    _require(set(raw) == ({"id", "phase", "measures", "shared", "rule"} if shared else
                          {"id", "phase", "measures", "attempt"}), "invalid-entry")
    _require(type(raw["id"]) is str and _ID.fullmatch(raw["id"]) is not None and
             raw["phase"] in PHASES and isinstance(raw["measures"], Mapping) and
             set(raw["measures"]) <= set(DIMENSIONS), "invalid-entry")
    if shared:
        targets = raw["shared"]
        _require(type(targets) in (list, tuple) and len(targets) >= 2 and
                 all(type(t) is str for t in targets) and
                 len(set(targets)) == len(targets) and raw["rule"] in RULES, "invalid-entry")
        rule = raw["rule"]
    else:
        targets, rule = (raw["attempt"],), "direct"
    _require(all(type(t) is str and t in attempts for t in targets), "unknown-attempt")
    values = {dim: _measure(dim, raw["measures"].get(dim)) for dim in DIMENSIONS}
    return _Entry(raw["id"], raw["phase"], frozenset(targets), rule, values)


def _ledger_entry(raw: Mapping) -> dict:
    """Validated input entry with its shared targets in canonical order."""
    value = thaw(raw)
    if "shared" in value:
        value["shared"] = sorted(value["shared"])
    return value


def _rows(entries: Sequence[_Entry], members: set[str]):
    """(entry, lower, point, upper) weights of each entry touching ``members``.

    Weight 1 means certainly charged, 0 not charged; a None point weight marks an
    unallocated shared entry that the point estimate leaves out.
    """
    for e in entries:
        k = len(e.targets & members)
        if k == len(e.targets):
            yield e, 1, 1, 1
        elif k:
            yield e, 0, Fraction(k, len(e.targets)) if e.rule == "equal" else None, 1


def _fold(dim: str, rows) -> dict:
    summed = DIMENSIONS[dim][0] == "sum"
    acc = [Fraction(0)] * 3
    unknown, unallocated, seen = [], [], False
    for e, lower, point, upper in rows:
        seen = True
        value = e.values[dim]
        if value is None:
            unknown.append(e.id)
            continue
        if point is None:
            unallocated.append(e.id)
            point = 0
        for i, w in enumerate((lower, point, upper)):
            acc[i] = acc[i] + value * w if summed else max(acc[i], value if w else 0)
    known = seen and not unknown
    return {"lower": _q(acc[0]), "point": _q(acc[1]) if known else None,
            "upper": _q(acc[2]) if known else None, "unknownEntries": sorted(unknown),
            "unallocatedEntries": sorted(unallocated)}


def _costs(entries: Sequence[_Entry], members: set[str] | None = None) -> dict:
    rows = (list(_rows(entries, members)) if members is not None else
            [(e, 1, 1, 1) for e in entries])
    return {dim: _fold(dim, rows) for dim in DIMENSIONS}


def _divide(bound: dict, count: int) -> dict:
    return {key: (_q(Fraction(bound[key]) / count) if bound[key] is not None else None)
            for key in ("lower", "point", "upper")}


def _rate(numerator: int, denominator: int) -> int | str:
    return _q(Fraction(numerator, denominator)) if denominator else "undefined"


def _reservations(reservations: Any) -> dict[str, int]:
    _require(type(reservations) in (list, tuple) and len(reservations) <= MAX_ATTEMPTS,
             "invalid-reservation")
    journal: dict[str, int] = {}
    for r in reservations:
        _require(type(r) is Reservation, "invalid-reservation")
        try:
            data = r.to_dict()
        except InvalidDecision as exc:
            raise CostError("invalid-reservation") from exc
        _require(data.get("format") == "braid-harness-reservation/v0.1" and
                 data.get("executionAuthorization") is False and
                 type(data.get("reservedJournalBytes")) is int and
                 0 <= data["reservedJournalBytes"] <= MAX_VALUE and
                 r.sha256 not in journal, "invalid-reservation")
        journal[r.sha256] = data["reservedJournalBytes"]
    return journal


def _attempts(raw: Any, units: set[str], arms: set[str], reserved: Mapping[str, int]) -> dict:
    _require(type(raw) in (list, tuple) and len(raw) <= MAX_ATTEMPTS, "invalid-attempt")
    attempts: dict[str, Mapping] = {}
    cells, used = set(), set()
    for a in raw:
        _require(isinstance(a, Mapping) and set(a) == _ATTEMPT_KEYS and
                 type(a["id"]) is str and _ID.fullmatch(a["id"]) is not None and
                 a["id"] not in attempts and a["terminal"] in ATTEMPT_TERMINALS and
                 a["outcome"] in OUTCOMES and
                 type(a["unitId"]) is str and type(a["arm"]) is str and
                 (a["observationSha256"] is None or _is_hash(a["observationSha256"])) and
                 (a["reservationSha256"] is None or _is_hash(a["reservationSha256"])),
                 "invalid-attempt")
        _require(a["unitId"] in units, "unregistered-unit")
        _require(a["arm"] in arms, "unknown-arm")
        _require((a["unitId"], a["arm"]) not in cells, "duplicate-attempt")
        _require(a["outcome"] != "correct" or a["terminal"] == "completed", "inconsistent-outcome")
        # every terminal but "unobserved" comes from a bound SPEC-048 observation
        _require((a["terminal"] == "unobserved") == (a["observationSha256"] is None),
                 "inconsistent-outcome")
        if a["reservationSha256"] is not None:
            _require(a["reservationSha256"] in reserved, "unknown-reservation")
            _require(a["reservationSha256"] not in used, "reservation-reused")
            used.add(a["reservationSha256"])
        cells.add((a["unitId"], a["arm"]))
        attempts[a["id"]] = dict(a)
    return attempts


def _reconcile(attempts: Mapping[str, Mapping], entries: Sequence[_Entry],
               reserved: Mapping[str, int]) -> dict:
    used = {a["reservationSha256"] for a in attempts.values()}
    touching: dict[str, list[_Entry]] = {aid: [] for aid in attempts}
    for e in entries:
        for t in e.targets:
            touching[t].append(e)
    unreserved, uncosted, exceeded, unreconciled, uncleaned = [], [], [], [], []
    for aid, a in attempts.items():
        mine = touching[aid]
        if a["terminal"] != "refused" and all(e.phase == "cleanup" for e in mine):
            uncosted.append(aid)
        sha = a["reservationSha256"]
        if sha is None:
            if a["terminal"] != "refused":
                unreserved.append(aid)
            continue
        journal = _fold("journal", _rows(mine, {aid}))
        if journal["point"] is None or (journal["unallocatedEntries"] and
                                        Fraction(journal["upper"]) > reserved[sha]):
            unreconciled.append(aid)
        elif Fraction(journal["point"]) > reserved[sha]:
            exceeded.append(aid)
        if not any(e.phase == "cleanup" for e in mine):
            uncleaned.append(aid)
    return {"openReservations": sorted(set(reserved) - used),
            "unreservedAttempts": sorted(unreserved), "attemptsWithoutCost": sorted(uncosted),
            "journalExceeded": sorted(exceeded), "journalUnreconciled": sorted(unreconciled),
            "cleanupUnaccounted": sorted(uncleaned)}


def _arm(arm: str, units: int, attempts: Mapping[str, Mapping], entries: Sequence[_Entry]) -> dict:
    mine = {aid: a for aid, a in attempts.items() if a["arm"] == arm}
    terminals = {t: sum(a["terminal"] == t for a in mine.values()) for t in ATTEMPT_TERMINALS}
    outcomes = {o: sum(a["outcome"] == o for a in mine.values()) for o in OUTCOMES}
    started = len(mine) - terminals["refused"]
    correct = outcomes["correct"]
    arm_costs = _costs(entries, set(mine))
    return {"denominators": {"registered": units, "attempted": len(mine), "started": started,
                             "notAttempted": units - len(mine), "terminals": terminals,
                             "outcomes": outcomes},
            "correctPerRegistered": _rate(correct, units),
            "correctPerStarted": _rate(correct, started),
            "costs": arm_costs,
            "costPerCorrect": ({dim: _divide(arm_costs[dim], correct) for dim in _SUMMED}
                               if correct else "undefined")}


@dataclass(frozen=True)
class CostReport:
    """Immutable reconciliation report; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return thaw(self.data)


def reconcile(*, registered_units: Sequence[str], arms: Sequence[str],
              attempts: Sequence[Mapping[str, Any]], entries: Sequence[Mapping[str, Any]],
              reservations: Sequence[Reservation]) -> CostReport:
    """Reconcile a complete cost ledger; refuse malformed input with a fixed reason."""
    units = _ids(registered_units, "invalid-registration")
    arm_ids = _ids(arms, "invalid-registration")
    _require(bool(arm_ids), "invalid-registration")
    reserved = _reservations(reservations)
    by_id = _attempts(attempts, set(units), set(arm_ids), reserved)
    _require(type(entries) in (list, tuple) and len(entries) <= MAX_ENTRIES, "invalid-entry")
    parsed = [_entry(e, by_id) for e in entries]
    _require(len({e.id for e in parsed}) == len(parsed), "duplicate-entry")
    _require(sum(len(e.targets) for e in parsed) <= MAX_TARGET_REFS, "invalid-entry")
    parsed.sort(key=lambda e: e.id)

    totals = _costs(parsed)
    reconciliation = _reconcile(by_id, parsed, reserved)
    blockers = {code for code, key in _RECONCILIATION_BLOCKERS if reconciliation[key]}
    if totals["cash"]["point"] is None:
        blockers.add("unknown-cash")
    if Fraction(totals["cash"]["lower"]) > CASH_CAP_EUR_CENTS:
        blockers.add("additional-cash-observed")
    phases = {p: _costs([e for e in parsed if e.phase == p]) for p in PHASES}
    ledger = {"registeredUnits": sorted(units), "arms": sorted(arm_ids),
              "attempts": [by_id[k] for k in sorted(by_id)],
              "entries": sorted((_ledger_entry(e) for e in entries), key=lambda e: e["id"]),
              "reservations": sorted(reserved)}
    report = {
        "format": FORMAT, "ledgerSha256": digest(ledger), "units": dict(UNITS),
        "totals": totals, "phases": phases,
        "phasesWithoutEntries": [p for p in PHASES if p not in {e.phase for e in parsed}],
        "arms": {arm: _arm(arm, len(units), by_id, parsed) for arm in sorted(arm_ids)},
        "reconciliation": reconciliation,
        "economic": {"additionalCashEurCents": totals["cash"],
                     "cashCapEurCents": CASH_CAP_EUR_CENTS, "numericCaps": "deferred-D2",
                     "blockers": sorted(blockers), "claimBlocked": bool(blockers)},
        "executionAuthorization": False,
    }
    return CostReport(freeze(report), canonical(report))
