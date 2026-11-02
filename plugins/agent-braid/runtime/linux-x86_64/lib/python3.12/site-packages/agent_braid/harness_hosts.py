# SPDX-License-Identifier: AGPL-3.0-only
"""T008 host-profile gate: independent Codex/Claude decisions, D2 caps and containment.

Binds the founder's per-host T008 decisions and the SPEC-049 D2 caps by the exact
hashes of their decision records, then supervises a serial qualification cohort for
one host. Before every unit it requires a fresh plan route/quota observation, the
D2 stop conditions, a headroom reservation (the session cap on the five-hour window,
the largest weekly delta seen so far on the cohort cap) and a hash-verified
containment qualification; after every unit it settles the observed quota deltas
and wall time against the caps and latches a stop on any breach or loss. Readings
must move forward in time, so an older reading cannot hide a later one.

Each host is decided on its own record: an authorized Claude profile never admits
Codex, and a qualified verdict for one host never implies both-host acceptance.
Only the Claude profile has a containment verifier (``harness_host_claude``); any
other host refuses here. Nothing in this module launches a host, process or model,
reads a quota or issues an admission; observations come from the trusted caller and
every result keeps ``executionAuthorization`` false.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from hashlib import sha256
import re
from typing import Any

from . import harness_host_claude
from .system_one import InvalidDecision, canonical, digest, parse_json

HOSTS = ("claude", "codex")
AUTHORIZED = "qualification-authorized"
NOT_QUALIFIED = "not-qualified"
FOUNDER_FORMAT = "spec048-founder-review-v1"
CAPS_FORMAT = "spec049-d2-caps-founder-decision-v1"
ROUTE = "subscription"  # plan route only; any other observed route is a possible paid route
_ITEMS = {"Claude profile qualification": "claude", "Codex profile qualification": "codex"}
_AUTHORITY = ("executionAuthorization", "nativeAdmission", "promotionAuthorization")
# The D2 founder decision of 2026-10-31, verbatim; a different record needs a new decision.
_D2_CAPS = {"perUnitWallTimeMinutes": 30, "perSessionMaxPercentOf5HourWindow": 10,
            "cohortMaxPercentOfWeeklyAllModels": 15, "maxNativeUnits": 16,
            "stopConditions": ["weekly all-models window above 80 % before the next unit",
                               "extra usage enabled", "quota reading unavailable or stale"]}
# Implementation freshness bound (the D2 record says only "stale"); matches the
# five-minute observation windows of the admission and Codex discovery seams.
MAX_OBSERVATION_AGE_SECONDS = 300
# Stops that only exhaust the budget; any other stop casts doubt on the evidence.
_BUDGET_STOPS = frozenset({"unit-cap", "weekly-stop", "cohort-cap", "five-hour-headroom",
                           "window-reset", "window-reset-imminent"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[a-z0-9][a-z0-9_.:-]{0,63}\Z")


class HostGateError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-host-gate"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-host-gate") -> None:
    if not condition:
        raise HostGateError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _percent(value: Any) -> bool:
    return type(value) in (int, float) and 0 <= value <= 100


def _record(raw: Any, expected_sha256: Any, record_format: str) -> dict:
    """Hash-bound decision record that grants no execution, admission or promotion."""
    _require(_hash(expected_sha256), "invalid-expected-hash")
    _require(type(raw) is bytes and sha256(raw).hexdigest() == expected_sha256, "record-drift")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise HostGateError("invalid-record") from None
    _require(type(value) is dict and value.get("recordVersion") == record_format
             and all(value.get(key) is False for key in _AUTHORITY), "invalid-record")
    return value


# --- founder decision records -------------------------------------------------------


@dataclass(frozen=True)
class ProfileDecision:
    """One host's T008 profile decision, bound to the exact founder record."""

    host: str
    decision: str
    reason: str
    record_sha256: str

    @property
    def authorized(self) -> bool:
        return self.decision == AUTHORIZED


def parse_profile_decisions(raw: bytes, *, expected_sha256: str) -> dict[str, ProfileDecision]:
    """Decide each host independently; a host without its own decision stays refused."""
    value = _record(raw, expected_sha256, FOUNDER_FORMAT)
    rows = value.get("decisions")
    _require(type(rows) is list, "invalid-record")
    found: dict[str, str] = {}
    for row in rows:
        if type(row) is not dict or row.get("task") != "SPEC-048/T008":
            continue
        host = _ITEMS.get(row.get("item"))
        _require(host is not None and host not in found
                 and row.get("decision") in (AUTHORIZED, NOT_QUALIFIED), "invalid-record")
        found[host] = row["decision"]
    observation = value.get("hostObservation")
    installed = observation.get("host") if type(observation) is dict else None
    if type(installed) is not dict:
        installed = {}
    decisions = {}
    for host in HOSTS:
        decision = found.get(host, NOT_QUALIFIED)
        if decision == AUTHORIZED:
            reason = AUTHORIZED
        elif host not in found:
            reason = "not-qualified: no decision"
        elif type(installed.get(host)) is str and installed[host].startswith("absent"):
            reason = "not-qualified: not installed"
        else:
            reason = NOT_QUALIFIED
        decisions[host] = ProfileDecision(host, decision, reason, expected_sha256)
    return decisions


@dataclass(frozen=True)
class D2Caps:
    """The frozen D2 caps; construction refuses any other values."""

    record_sha256: str
    unit_wall_seconds: int = 30 * 60
    session_max_five_hour_percent: int = 10
    cohort_max_weekly_percent: int = 15
    max_units: int = 16
    weekly_stop_percent: int = 80
    additional_cash_eur: int = 0

    def __post_init__(self) -> None:
        _require(_hash(self.record_sha256) and (self.unit_wall_seconds, self.session_max_five_hour_percent,
                      self.cohort_max_weekly_percent, self.max_units, self.weekly_stop_percent,
                      self.additional_cash_eur) == (1800, 10, 15, 16, 80, 0), "caps-drift")


def parse_d2_caps(raw: bytes, *, expected_sha256: str) -> D2Caps:
    value = _record(raw, expected_sha256, CAPS_FORMAT)
    _require(canonical(value.get("caps")) == canonical(_D2_CAPS)
             and canonical(value.get("additionalCashEur")) == b"0", "caps-drift")
    return D2Caps(expected_sha256)


# --- route/quota observations -------------------------------------------------------


@dataclass(frozen=True)
class QuotaObservation:
    """One trusted plan route/quota reading; percentages of each usage window."""

    host: str
    observed_at: int
    plan: str
    route: str
    five_hour_percent: int | float
    five_hour_resets_at: int
    weekly_percent: int | float
    weekly_resets_at: int
    extra_usage_enabled: bool

    def __post_init__(self) -> None:
        _require(self.host in HOSTS and all(type(v) is str and _ID.fullmatch(v) is not None
                                            for v in (self.plan, self.route))
                 and all(_int(v, 0, 1 << 40) for v in (self.observed_at, self.five_hour_resets_at,
                                                       self.weekly_resets_at))
                 and _percent(self.five_hour_percent) and _percent(self.weekly_percent)
                 and type(self.extra_usage_enabled) is bool, "invalid-observation")

    def to_dict(self) -> dict:
        return {"host": self.host, "observedAt": self.observed_at, "plan": self.plan,
                "route": self.route, "fiveHourPercent": self.five_hour_percent,
                "fiveHourResetsAt": self.five_hour_resets_at,
                "weeklyPercent": self.weekly_percent, "weeklyResetsAt": self.weekly_resets_at,
                "extraUsageEnabled": self.extra_usage_enabled}

    @property
    def sha256(self) -> str:
        return digest(self.to_dict())


# --- supervised qualification cohort ------------------------------------------------


@dataclass(frozen=True)
class UnitTicket:
    """Admission of one serial unit; accounting only, never an authorization."""

    index: int
    admitted_at: int
    deadline: int
    before: QuotaObservation
    containment_sha256: str


@dataclass(frozen=True)
class UnitRecord:
    """Settled unit: observed deltas, wall time and the first breach, if any."""

    index: int
    completed: bool
    before_sha256: str
    after_sha256: str | None
    containment_sha256: str
    wall_seconds: int
    five_hour_delta: int | float | None
    weekly_delta: int | float | None
    breach: str | None

    @property
    def within_caps(self) -> bool:
        return self.breach is None

    def to_dict(self) -> dict:
        return {"index": self.index, "completed": self.completed,
                "beforeSha256": self.before_sha256, "afterSha256": self.after_sha256,
                "containmentSha256": self.containment_sha256, "wallSeconds": self.wall_seconds,
                "fiveHourDelta": self.five_hour_delta, "weeklyDelta": self.weekly_delta,
                "breach": self.breach}


@dataclass(frozen=True)
class HostVerdict:
    """One host's qualification evidence; never implies any other host."""

    host: str
    decision: ProfileDecision
    caps_sha256: str | None
    baseline_sha256: str | None
    units: tuple[UnitRecord, ...] = ()
    open_unit: bool = False
    stopped: str | None = None

    @property
    def qualified(self) -> bool:
        return (self.decision.authorized and self.decision.host == self.host
                and (self.stopped is None or self.stopped in _BUDGET_STOPS) and not self.open_unit
                and all(u.within_caps for u in self.units) and any(u.completed for u in self.units))

    def to_dict(self) -> dict:
        return {"host": self.host, "decision": self.decision.decision,
                "reason": self.decision.reason, "decisionRecordSha256": self.decision.record_sha256,
                "capsRecordSha256": self.caps_sha256, "baselineSha256": self.baseline_sha256,
                "units": [u.to_dict() for u in self.units], "openUnit": self.open_unit,
                "stopped": self.stopped, "qualified": self.qualified,
                "executionAuthorization": False}


def refused_verdict(decision: ProfileDecision) -> HostVerdict:
    """Verdict for a host whose profile is not authorized: refused, with no units."""
    _require(isinstance(decision, ProfileDecision) and not decision.authorized, "invalid-host-gate")
    return HostVerdict(decision.host, decision, None, None, stopped=decision.reason)


def both_hosts_accepted(verdicts: Mapping[str, HostVerdict]) -> bool:
    """True only when every host has its own qualified verdict."""
    return (isinstance(verdicts, Mapping) and set(verdicts) == set(HOSTS)
            and all(isinstance(v, HostVerdict) and v.host == host and v.qualified
                    for host, v in verdicts.items()))


def _verify_containment(host: str, raw: Any, expected_sha256: Any, environment_sha256: str,
                        deadline: int) -> str:
    """Hash-verified Claude containment that stays valid through the unit's deadline."""
    _require(host == harness_host_claude.HOST, "containment-unavailable")
    try:
        qualification = harness_host_claude.verify_host_qualification(
            raw, expected_sha256=expected_sha256)
    except harness_host_claude.ClaudeHostError as exc:
        raise HostGateError(exc.reason) from None
    _require(qualification.environment_sha256 == environment_sha256, "containment-environment")
    _require(deadline < qualification.expires_at, "containment-expired")
    return qualification.sha256


@dataclass
class HostQualificationRun:
    """Serial D2-capped qualification cohort for exactly one authorized host profile."""

    decisions: Mapping[str, ProfileDecision]
    caps: D2Caps
    host: str
    environment_sha256: str
    baseline: QuotaObservation
    _stopped: str | None = field(default=None, init=False, repr=False)
    _units: list[UnitRecord] = field(default_factory=list, init=False, repr=False)
    _open: UnitTicket | None = field(default=None, init=False, repr=False)
    _last_observed_at: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        _require(self.host in HOSTS and isinstance(self.caps, D2Caps)
                 and isinstance(self.decisions, Mapping)
                 and isinstance(self.decisions.get(self.host), ProfileDecision)
                 and self.decisions[self.host].host == self.host
                 and _hash(self.environment_sha256))
        decision = self.decisions[self.host]
        _require(decision.authorized, decision.reason)
        self.decisions = {self.host: decision}  # snapshot; later caller edits cannot widen it
        _require(isinstance(self.baseline, QuotaObservation) and self.baseline.host == self.host
                 and self.baseline.route == ROUTE and not self.baseline.extra_usage_enabled,
                 "invalid-observation")
        self._last_observed_at = self.baseline.observed_at

    @property
    def stopped(self) -> str | None:
        """First stop reason; latched for the life of the cohort."""
        return self._stopped

    def _stop(self, reason: str) -> None:
        self._stopped = reason
        raise HostGateError(reason)

    def _fresh(self, observation: Any, now: int) -> bool:
        return (isinstance(observation, QuotaObservation) and observation.host == self.host
                and 0 <= now - observation.observed_at <= MAX_OBSERVATION_AGE_SECONDS)

    def admit_unit(self, observation: QuotaObservation | None, *, containment: bytes,
                   containment_sha256: str, now: int) -> UnitTicket:
        """Check every D2 stop condition, reserve headroom and verify containment."""
        _require(_int(now, 0, 1 << 40), "invalid-clock")
        _require(self._stopped is None, "stopped")
        _require(self._open is None, "unit-open")
        caps = self.caps
        if len(self._units) >= caps.max_units:
            self._stop("unit-cap")
        if not self._fresh(observation, now) or observation.observed_at < self._last_observed_at:
            self._stop("stale-observation")
        if observation.extra_usage_enabled:
            self._stop("extra-usage-enabled")
        if observation.route != ROUTE:
            self._stop("paid-route")
        if observation.weekly_resets_at != self.baseline.weekly_resets_at \
                or observation.weekly_percent < self.baseline.weekly_percent:
            self._stop("window-reset")  # cohort consumption is no longer observable
        # Weekly cost of a unit is unknown before it runs; reserve the largest seen so far.
        reserve = max((u.weekly_delta for u in self._units if u.weekly_delta is not None), default=0)
        if observation.weekly_percent + reserve > caps.weekly_stop_percent:
            self._stop("weekly-stop")
        if observation.weekly_percent - self.baseline.weekly_percent + reserve >= \
                caps.cohort_max_weekly_percent:
            self._stop("cohort-cap")
        if observation.five_hour_percent + caps.session_max_five_hour_percent > 100:
            self._stop("five-hour-headroom")
        if min(observation.five_hour_resets_at, observation.weekly_resets_at) <= \
                now + caps.unit_wall_seconds:
            self._stop("window-reset-imminent")  # the settlement could not measure deltas
        deadline = now + caps.unit_wall_seconds
        try:
            verified = _verify_containment(self.host, containment, containment_sha256,
                                           self.environment_sha256, deadline)
        except HostGateError as exc:
            self._stop(exc.reason)
        self._open = UnitTicket(len(self._units), now, deadline, observation, verified)
        return self._open

    def settle_unit(self, ticket: UnitTicket, after: QuotaObservation | None, *,
                    completed: bool, now: int) -> UnitRecord:
        """Record the unit against the caps; a breach or lost reading stops the cohort."""
        _require(ticket is not None and ticket == self._open and type(completed) is bool
                 and _int(now, ticket.admitted_at, 1 << 40), "invalid-settlement")
        before, caps = ticket.before, self.caps
        five_hour = weekly = None
        if after is None:
            breach = "missing-observation"
        elif not self._fresh(after, now) or after.observed_at <= ticket.admitted_at:
            breach = "stale-observation"
        elif after.extra_usage_enabled:
            breach = "extra-usage-enabled"
        elif after.route != ROUTE:
            breach = "paid-route"
        elif (after.five_hour_resets_at, after.weekly_resets_at) != \
                (before.five_hour_resets_at, before.weekly_resets_at):
            breach = "window-reset"  # deltas across a reset are unknown, not zero
        else:
            five_hour = after.five_hour_percent - before.five_hour_percent
            weekly = after.weekly_percent - before.weekly_percent
            cohort = after.weekly_percent - self.baseline.weekly_percent
            breach = None
            if five_hour < 0 or weekly < 0:
                breach = "inconsistent-observation"  # usage cannot fall without a reset
            elif now > ticket.deadline:
                breach = "unit-wall-time"
            elif five_hour > caps.session_max_five_hour_percent:
                breach = "session-cap"
            elif cohort > caps.cohort_max_weekly_percent:
                breach = "cohort-cap"
        record = UnitRecord(ticket.index, completed, before.sha256,
                            after.sha256 if isinstance(after, QuotaObservation) else None,
                            ticket.containment_sha256, now - ticket.admitted_at,
                            five_hour, weekly, breach)
        self._units.append(record)
        if isinstance(after, QuotaObservation):
            self._last_observed_at = max(self._last_observed_at, after.observed_at)
        self._open = None
        if breach is not None:
            self._stopped = breach
        return record

    def verdict(self) -> HostVerdict:
        return HostVerdict(self.host, self.decisions[self.host], self.caps.record_sha256,
                           self.baseline.sha256, tuple(self._units), self._open is not None,
                           self._stopped)
