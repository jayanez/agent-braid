# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic three-arm evaluation with full denominators and costs; offline, no authority.

A registration binds held-out SPEC-049 units to their lineage, task family and stratum,
one matched profile and three arms: A the static base, B simple checkpoint/context
guidance and C the candidate a SPEC-048 contrastive refinement round selected (the base
when it explicitly kept the base), with no experience library. An inconclusive or
refused round defines no arm C. The registration also records, before any outcome, a
fixed Latin-square arm order rotated within each task family (T002 D1).

``evaluate`` reads T011 commitment and unit-verdict records, never candidate output.
Every registered unit x arm cell is reported: correct, incorrect, ungraded (a required
oracle or human verdict is missing, an optional human section is unresolved, the
available verdicts disagree, or the attempt was unobserved), not-completed (failed,
interrupted or refused) or not-attempted. Proxy scores are never correctness. Rates use
every registered unit as the denominator; a started-attempt rate is reported beside
it, and missing outcomes bound the rate from below and above. Intervals are exact
two-sided 95% Clopper-Pearson bounds rounded outward to micros.

Strata are reported separately and never pooled. Each comparator is paired with A per
stratum. A noninferiority verdict at the frozen D4 margin is assessed only when the
stratum has at least the D3 minimum of paired units, each from a distinct lineage;
otherwise the result is descriptive only. The assessment is D3's exact binomial bound
on comparator-worse pairs, with every missing pair counted as worse. Numeric time/quota
caps and improvement thresholds are deferred (D2/D4) and none is applied.

Verdict records are checked for binding, rubric and oracle identity but not re-graded:
outcome integrity rests on the T011 records' provenance. Lineage, family, stratum and
the matched profile are caller-declared; nothing ties lineage labels to the corpus
registry or a row's run manifest to the profile, so an assessed verdict is only as
independent and matched as those declarations. Costs are reconciled by T012
``reconcile`` over the same attempts, where not-completed attempts count as
"incorrect". Only the correctness endpoint is computed; ``PENDING_ENDPOINTS`` lists the
rest. Nothing reads a clock, file, host or model, and ``executionAuthorization`` is
always false.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from math import comb
import re
from typing import Any

# _q/_rate and _shape are private; reused so rationals and record shapes match T011/T012.
from .harness_costs import ATTEMPT_TERMINALS, CostError, _q, _rate, reconcile
from .harness_refinement import DECISION_FORMAT, RefinementDecision
from .harness_verification import (COMMITMENT_FORMAT, UNIT_FORMAT, VERDICTS, Unit,
                                   VerificationError, _shape)
from .system_one import canonical, freeze, thaw

REGISTRATION_FORMAT = "braid-harness-evaluation-registration/v0.1"
REPORT_FORMAT = "braid-harness-evaluation-report/v0.1"
ARMS = {"A": "static-base", "B": "checkpoint-guidance", "C": "contrastive-refinement"}
COHORTS = ("synthetic", "native")
OUTCOMES = ("correct", "incorrect", "ungraded", "not-completed", "not-attempted")
PENDING_ENDPOINTS = ("interventions", "rework", "interrupted-recovery",
                     "conflict-precision-recall", "false-safe-admissions", "useful-parallelism")
ALPHA = Fraction(1, 20)  # D3: one-sided 5%
DELTA = Fraction(3, 20)  # D4: correctness noninferiority margin
INTERVAL_TAIL = Fraction(1, 40)  # each tail of a two-sided 95% interval
INTERVAL_METHOD = "clopper-pearson-two-sided-0.95"
INTERVAL_SCALE = 1_000_000
MAX_UNITS = 256
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_ROW_KEYS = {"arm", "attemptId", "reservationSha256", "commitment", "verdict"}
_BINARY = {"correct": 1, "incorrect": 0, "not-completed": 0}  # other outcomes are missing
_PAIR = {(1, 1): "bothCorrect", (0, 1): "comparatorOnly", (1, 0): "baseOnly", (0, 0): "neither"}


def _minimum_paired_units() -> int:
    n = 1
    while (1 - DELTA) ** n >= ALPHA:
        n += 1
    return n


MIN_PAIRED_UNITS = _minimum_paired_units()  # 19 at delta 0.15, matching the D3 table
_PROTOCOL = {"alpha": _q(ALPHA), "correctnessMargin": _q(DELTA),
             "minimumPairedUnits": MIN_PAIRED_UNITS,
             "interval": INTERVAL_METHOD, "numericCaps": "deferred-D2",
             "improvementThresholds": "deferred-D4", "library": "excluded"}


class EvaluationError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-evaluation"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-registration") -> None:
    if not condition:
        raise EvaluationError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


@dataclass(frozen=True)
class EvaluationRecord:
    """Immutable report; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        return thaw(self.data)


@dataclass(frozen=True)
class Registration(EvaluationRecord):
    """Registration record plus the registered units it binds."""

    units: tuple[Unit, ...] = ()


def _record(cls, value: dict, **extra) -> Any:
    return cls(freeze(value), canonical(value), **extra)


# --- exact binomial arithmetic ------------------------------------------------------


def _scaled_cdf(x: int, n: int, a: int) -> int:
    """P(X <= x) for X ~ Binomial(n, a / INTERVAL_SCALE), times INTERVAL_SCALE ** n."""
    b = INTERVAL_SCALE - a
    return sum(comb(n, k) * a ** k * b ** (n - k) for k in range(x + 1))


def _first(ok) -> int:
    """Smallest a in [0, INTERVAL_SCALE] with ok(a), for ok monotone false -> true."""
    lo, hi = 0, INTERVAL_SCALE
    while lo < hi:
        mid = (lo + hi) // 2
        if ok(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def _interval(x: int, n: int) -> dict:
    """Exact Clopper-Pearson bounds of x/n in micros, lower floored and upper ceiled."""
    total = INTERVAL_SCALE ** n
    num, den = INTERVAL_TAIL.numerator, INTERVAL_TAIL.denominator

    def within(tail: int) -> bool:
        return tail * den <= num * total

    upper = INTERVAL_SCALE if x == n else _first(lambda a: within(_scaled_cdf(x, n, a)))
    lower = 0 if x == 0 else _first(lambda a: not within(total - _scaled_cdf(x - 1, n, a))) - 1
    return {"method": INTERVAL_METHOD, "lowerMicros": lower, "upperMicros": upper}


def _noninferiority(pairs: int, lineages: int, worse: int) -> dict:
    reasons = []
    if lineages < pairs:
        reasons.append("repeated-within-lineage")
    if pairs < MIN_PAIRED_UNITS:
        reasons.append("below-D3-minimum")
    if reasons:
        return {"status": "descriptive-only", "verdict": None, "reasons": reasons}
    tail = sum((comb(pairs, k) * DELTA ** k * (1 - DELTA) ** (pairs - k)
                for k in range(worse + 1)), Fraction(0))
    return {"status": "assessed",
            "verdict": "noninferior" if tail < ALPHA else "not-demonstrated", "reasons": []}


# --- registration -------------------------------------------------------------------


def _labels(value: Any, ids: list[str]) -> dict[str, str]:
    _require(isinstance(value, Mapping) and set(value) == set(ids)
             and all(_id(v) for v in value.values()))
    return dict(value)


def _arm_c(refinement: Any) -> tuple[dict, str, str]:
    """Refinement summary, its base and the candidate arm C must evaluate."""
    _require(type(refinement) is RefinementDecision
             and canonical(thaw(refinement.data)) == refinement.canonical_bytes,
             "invalid-refinement")
    data = refinement.to_dict()
    _require(data.get("format") == DECISION_FORMAT and data.get("executionAuthorization") is False
             and _hash(data.get("baseSha256")) and _hash(data.get("manifestSha256")),
             "invalid-refinement")
    # Only a selected candidate or an explicit keep-base defines arm C; an inconclusive or
    # refused round has no comparator and must not pose as the base.
    _require(data.get("decision") in ("candidate", "keep-base"), "refinement-not-selected")
    base = data["baseSha256"]
    chosen = data["chosenCandidateSha256"] if data["decision"] == "candidate" else base
    _require(_hash(chosen), "invalid-refinement")
    summary = {"sha256": refinement.sha256, "decision": data["decision"],
               "manifestSha256": data["manifestSha256"], "armCIsBase": chosen == base}
    return summary, base, chosen


def _order(units: list[str], families: Mapping[str, str]) -> dict[str, list[str]]:
    """Latin-square rotation of A/B/C within each task family (D1), by unit id."""
    arms, order, seen = list(ARMS), {}, Counter()
    for unit in sorted(units):
        shift = seen[families[unit]] % len(arms)
        seen[families[unit]] += 1
        order[unit] = arms[shift:] + arms[:shift]
    return order


def register(units: Sequence[Unit], *, lineages: Mapping[str, str],
             families: Mapping[str, str], strata: Mapping[str, str],
             candidates: Mapping[str, str], refinement: RefinementDecision,
             profile_sha256: str, cohort: str) -> Registration:
    """Freeze the units, arms, matched profile and arm order before any outcome."""
    _require(type(units) in (list, tuple) and 0 < len(units) <= MAX_UNITS
             and all(isinstance(u, Unit) for u in units))
    units = sorted(units, key=lambda u: u.unit_id)
    ids = [u.unit_id for u in units]
    _require(len(set(ids)) == len(ids))
    _require(all(u.partition == "holdout" for u in units), "not-holdout")
    lineages, families = _labels(lineages, ids), _labels(families, ids)
    strata = _labels(strata, ids)
    _require(isinstance(candidates, Mapping) and set(candidates) == set(ARMS)
             and all(_hash(c) for c in candidates.values()))
    _require(_hash(profile_sha256) and cohort in COHORTS)
    _require(candidates["B"] != candidates["A"], "comparator-not-distinct")
    summary, base, chosen = _arm_c(refinement)
    _require(candidates["A"] == base and candidates["C"] == chosen, "refinement-mismatch")
    data = {
        "format": REGISTRATION_FORMAT, "cohort": cohort, "profileSha256": profile_sha256,
        "units": [{"unitId": u.unit_id, "unitSha256": u.sha256, "lineage": lineages[u.unit_id],
                   "family": families[u.unit_id], "stratum": strata[u.unit_id]} for u in units],
        "arms": {arm: {"role": role, "candidateSha256": candidates[arm]}
                 for arm, role in ARMS.items()},
        "refinement": summary, "order": _order(ids, families),
        "protocol": dict(_PROTOCOL),
        "executionAuthorization": False,
    }
    return _record(Registration, data, units=tuple(units))


# --- rows and outcomes --------------------------------------------------------------


def _outcome(unit: Unit, verdict: Mapping[str, Any]) -> tuple[str, str | None]:
    """Correctness of one graded cell from its oracle and human sections only."""
    if verdict["terminal"] == "unobserved":  # no observation: the outcome is unknown
        return "ungraded", "unobserved"
    if verdict["terminal"] != "completed":
        return "not-completed", verdict["terminal"]
    required = {"oracle": bool(unit.oracles), "human": unit.human_required}
    found = set()
    for source in ("oracle", "human"):
        section = verdict[source]
        if section["verdict"] is not None:
            found.add(section["verdict"])
        elif required[source] or section["status"] != "not-used":
            return "ungraded", f"{source}-{section['status']}"
    if len(found) > 1:
        return "ungraded", "cross-provenance-disagreement"
    return ("correct" if found == {"pass"} else "incorrect"), None


def _oracle_consistent(unit: Unit, verdict: Mapping[str, Any]) -> bool:
    """The oracle section names only the unit's oracles and its verdict follows its labels."""
    labels = verdict["oracle"].get("labels")
    if not (type(labels) in (list, tuple) and all(isinstance(l, Mapping) for l in labels)):
        return False
    known = {o.sha256 for o in unit.oracles}
    found = {l.get("verdict") for l in labels}
    return (all(l.get("verifierSha256") in known for l in labels) and found <= set(VERDICTS)
            and verdict["oracle"]["verdict"] == (found.pop() if len(found) == 1 else None))


def _row(raw: Any, registration: Registration, by_sha: Mapping[str, Unit]) -> tuple[dict, dict]:
    """Validated report cell and the T012 cost attempt for one submitted row."""
    _require(isinstance(raw, Mapping) and set(raw) == _ROW_KEYS, "invalid-row")
    _require(type(raw["arm"]) is str and raw["arm"] in ARMS, "unknown-arm")
    try:
        commitment, verdict = _shape(raw["commitment"]), _shape(raw["verdict"])
    except VerificationError:
        raise EvaluationError("invalid-row") from None
    _require(commitment["format"] == COMMITMENT_FORMAT and verdict["format"] == UNIT_FORMAT
             and all(isinstance(verdict[s], Mapping) and type(verdict[s].get("status")) is str
                     and verdict[s].get("verdict") in (None, *VERDICTS)
                     for s in ("oracle", "human")), "invalid-row")
    _require(verdict["commitmentSha256"] == raw["commitment"].sha256
             and verdict["unitSha256"] == commitment["unitSha256"]
             and verdict["candidateSha256"] == commitment["candidateSha256"]
             and verdict["terminal"] == commitment["terminal"], "verdict-binding-mismatch")
    unit = by_sha.get(commitment["unitSha256"])
    _require(unit is not None, "unregistered-unit")
    _require(verdict["rubricSha256"] == unit.rubric_sha256 and _oracle_consistent(unit, verdict),
             "verdict-unit-mismatch")
    arm = registration.data["arms"][raw["arm"]]
    _require(commitment["candidateSha256"] == arm["candidateSha256"], "candidate-mismatch")
    _require(commitment["attemptId"] in (None, raw["attemptId"]), "attempt-mismatch")
    outcome, reason = _outcome(unit, verdict)
    cell = {"unitId": unit.unit_id, "arm": raw["arm"], "attemptId": raw["attemptId"],
            "terminal": commitment["terminal"], "outcome": outcome, "reason": reason,
            "commitmentSha256": raw["commitment"].sha256, "verdictSha256": raw["verdict"].sha256}
    attempt = {"id": raw["attemptId"], "unitId": unit.unit_id, "arm": raw["arm"],
               "reservationSha256": raw["reservationSha256"],
               "observationSha256": commitment["observationSha256"],
               "terminal": commitment["terminal"],
               "outcome": outcome if outcome in ("correct", "ungraded") else "incorrect"}
    return cell, attempt


def _empty(unit_id: str, arm: str) -> dict:
    return {"unitId": unit_id, "arm": arm, "attemptId": None, "terminal": "not-attempted",
            "outcome": "not-attempted", "reason": None, "commitmentSha256": None,
            "verdictSha256": None}


# --- summaries ----------------------------------------------------------------------


def _arm(cells: list[dict]) -> dict:
    n = len(cells)
    outcomes = {o: sum(c["outcome"] == o for c in cells) for o in OUTCOMES}
    terminals = {t: sum(c["terminal"] == t for c in cells)
                 for t in (*ATTEMPT_TERMINALS, "not-attempted")}
    correct = outcomes["correct"]
    per_registered = _rate(correct, n)
    started = n - terminals["not-attempted"] - terminals["refused"]
    missing = outcomes["ungraded"] + outcomes["not-attempted"]
    return {"registered": n, "started": started, "outcomes": outcomes, "terminals": terminals,
            "correctPerRegistered": per_registered, "correctPerStarted": _rate(correct, started),
            "interval": _interval(correct, n),
            "missingSensitivity": {"lower": per_registered, "upper": _rate(correct + missing, n)}}


def _paired(base: list[dict], comparator: list[dict], lineages: int) -> dict:
    counts = {"bothCorrect": 0, "comparatorOnly": 0, "baseOnly": 0, "neither": 0, "missing": 0}
    for a, c in zip(base, comparator):
        pair = (_BINARY.get(a["outcome"]), _BINARY.get(c["outcome"]))
        counts[_PAIR.get(pair, "missing")] += 1
    worse = counts["baseOnly"] + counts["missing"]
    return {"pairs": len(base), "lineages": lineages, **counts, "worseUpperBound": worse,
            "noninferiority": _noninferiority(len(base), lineages, worse)}


def evaluate(registration: Registration, rows: Sequence[Mapping[str, Any]], *,
             cost_entries: Sequence[Mapping[str, Any]],
             reservations: Sequence[Any]) -> EvaluationRecord:
    """Report every registered cell, paired comparisons per stratum and complete costs."""
    # A registration whose data no longer matches its bytes or the frozen protocol is refused.
    _require(type(registration) is Registration
             and canonical(thaw(registration.data)) == registration.canonical_bytes
             and registration.data.get("format") == REGISTRATION_FORMAT
             and thaw(registration.data.get("protocol")) == _PROTOCOL
             and [u.sha256 for u in registration.units]
             == [u["unitSha256"] for u in registration.data["units"]])
    units = registration.units
    by_sha = {u.sha256: u for u in units}
    _require(type(rows) in (list, tuple) and len(rows) <= len(units) * len(ARMS), "invalid-row")
    cells: dict[tuple[str, str], dict] = {}
    attempts: dict[tuple[str, str], dict] = {}
    commitments: set[str] = set()
    for raw in rows:
        cell, attempt = _row(raw, registration, by_sha)
        key = (cell["unitId"], cell["arm"])
        _require(key not in cells, "duplicate-row")
        # One committed attempt fills one cell, even when two arms share a candidate.
        _require(cell["commitmentSha256"] not in commitments, "duplicate-row")
        commitments.add(cell["commitmentSha256"])
        cells[key], attempts[key] = cell, attempt
    try:
        costs = reconcile(registered_units=[u.unit_id for u in units], arms=list(ARMS),
                          attempts=[attempts[k] for k in sorted(attempts)],
                          entries=cost_entries, reservations=reservations)
    except CostError as exc:
        raise EvaluationError(exc.reason) from None

    grid = [cells.get((u.unit_id, arm)) or _empty(u.unit_id, arm)
            for u in units for arm in ARMS]
    meta = {u["unitId"]: u for u in registration.data["units"]}
    strata = {}
    for stratum in sorted({m["stratum"] for m in meta.values()}):
        members = [c for c in grid if meta[c["unitId"]]["stratum"] == stratum]
        by_arm = {arm: [c for c in members if c["arm"] == arm] for arm in ARMS}
        lineages = len({meta[c["unitId"]]["lineage"] for c in by_arm["A"]})
        strata[stratum] = {
            "units": len(by_arm["A"]), "lineages": lineages,
            "arms": {arm: _arm(cs) for arm, cs in by_arm.items()},
            "comparisons": {f"{arm}-vs-A": _paired(by_arm["A"], by_arm[arm], lineages)
                            for arm in ARMS if arm != "A"}}
    report = {"format": REPORT_FORMAT, "registrationSha256": registration.sha256,
              "cohort": registration.data["cohort"], "refinement": registration.data["refinement"],
              "strata": strata, "rows": grid, "costReportSha256": costs.sha256,
              "costs": costs.to_dict(), "pendingEndpoints": list(PENDING_ENDPOINTS),
              "executionAuthorization": False}
    return _record(EvaluationRecord, report)
