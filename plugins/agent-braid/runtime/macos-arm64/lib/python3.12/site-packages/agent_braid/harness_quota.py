# SPDX-License-Identifier: AGPL-3.0-only
"""Quota gate over a timestamped plan-usage reading; pure, offline, no authority.

SPEC-065 T004 (REQ-003). The orchestrator reads the Claude Desktop usage card
immediately before and after each native session (NC-6) and passes the readings in;
the caller also passes the clock (``now``, a timezone-aware datetime) and, for D2
cohort units, the cohort state owned by SPEC-049. Nothing here reads a clock, file,
host, quota source or network, and nothing launches anything.

A reading is ``{"source", "observedAt", "fiveHourPercent", "weeklyPercent",
"extraUsageEnabled"}``: the NC-6 source name, a UTC instant
``YYYY-MM-DDTHH:MM:SS[.ffffff]Z``, two integer percentages in [0, 100] and a
boolean. A missing, unparseable, stale (older than five minutes) or future-dated
reading is a stop, never a zero.

Cohort units (SPEC-049 D2 caps plus NC-6):
  * ``admit`` starts a unit only if the pre-reading is fresh, extra usage is
    disabled, the weekly window is at most 80 %, the 5-hour window is below 90 %,
    fewer than 16 units were used and the cohort has used less than 15 % of the
    weekly window; absent cohort state refuses.
  * ``settle`` checks a fresh post-reading: more than 10 % of the 5-hour window, a
    cohort total above 15 % of the weekly window, or a post-reading that itself
    shows a start condition failing stops the cohort. Use is attributed to the
    session only if the post-reading is strictly later than the pre-reading, at most
    ``MAX_READING_SPAN`` after it (one fresh pre-reading, a 30-minute F3/NC-8 session
    and one reading interval) and shows no smaller usage (a window reset).

Live qualification probes (NC-10) have their own cap, separate from the D2 cohort
caps: at most 3 sessions per attempt and at most 2 % of the 5-hour window each;
the NC-6 source, freshness and start rule and the reading-level stop conditions
(weekly > 80 %, extra usage) apply too. Cohort state is neither needed nor touched.

Caller-supplied state (readings, cohort state, probe count) that is absent or
malformed is a refusal; only a clock that is not a timezone-aware datetime raises
``TypeError``, as a programming error. Reasons name the rule, not its number; the
numbers are the module constants and the readings are in the evidence.

Every result is a ``QuotaDecision`` with a fixed reason and an evidence mapping for
the run record (readings and deltas); ``executionAuthorization`` is always false.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import re
from types import MappingProxyType
from typing import Any

SOURCE = "claude-desktop-usage-card"
FRESHNESS = timedelta(minutes=5)
SESSION_WALL = timedelta(minutes=30)
MAX_READING_SPAN = SESSION_WALL + 2 * FRESHNESS
WEEKLY_STOP_ABOVE = 80
FIVE_HOUR_START_BELOW = 90
SESSION_MAX_FIVE_HOUR = 10
COHORT_MAX_WEEKLY = 15
MAX_UNITS = 16
PROBE_MAX_SESSIONS = 3
PROBE_MAX_FIVE_HOUR = 2

_READING_KEYS = frozenset(("source", "observedAt", "fiveHourPercent", "weeklyPercent",
                           "extraUsageEnabled"))
_COHORT_KEYS = frozenset(("unitsUsed", "cohortWeeklyPercent"))
_INSTANT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z\Z")


@dataclass(frozen=True)
class QuotaDecision:
    proceed: bool
    reason: str
    evidence: Mapping[str, Any]
    executionAuthorization: bool = field(default=False, init=False)


@dataclass(frozen=True)
class _Reading:
    observed_at: datetime
    five_hour: int
    weekly: int
    extra_usage: bool

    def record(self) -> dict[str, Any]:
        return {"source": SOURCE, "observedAt": self.observed_at.isoformat().replace("+00:00", "Z"),
                "fiveHourPercent": self.five_hour, "weeklyPercent": self.weekly,
                "extraUsageEnabled": self.extra_usage}


class _Stop(Exception):
    @property
    def reason(self) -> str:
        return self.args[0]


def _percent(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= 100:
        raise _Stop("unparseable-reading")
    return value


def _reading(raw: Any, role: str) -> _Reading:
    if raw is None:
        raise _Stop(f"missing-{role}-reading")
    if not isinstance(raw, Mapping) or set(raw) != _READING_KEYS:
        raise _Stop("unparseable-reading")
    if raw["source"] != SOURCE:
        raise _Stop("unsupported-reading-source")
    stamp = raw["observedAt"]
    if not isinstance(stamp, str) or not _INSTANT.match(stamp):
        raise _Stop("unparseable-reading")
    try:
        observed = datetime.fromisoformat(stamp[:-1]).replace(tzinfo=timezone.utc)
    except ValueError:
        raise _Stop("unparseable-reading") from None
    if type(raw["extraUsageEnabled"]) is not bool:
        raise _Stop("unparseable-reading")
    return _Reading(observed, _percent(raw["fiveHourPercent"]), _percent(raw["weeklyPercent"]),
                    raw["extraUsageEnabled"])


def _clock(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise TypeError("now must be a timezone-aware datetime")
    return now.astimezone(timezone.utc)


def _fresh(reading: _Reading, now: datetime, role: str) -> None:
    if reading.observed_at > now:
        raise _Stop(f"future-dated-{role}-reading")
    if now - reading.observed_at > FRESHNESS:
        raise _Stop(f"stale-{role}-reading")


def _start_conditions(reading: _Reading) -> None:
    if reading.extra_usage:
        raise _Stop("extra-usage-enabled")
    if reading.weekly > WEEKLY_STOP_ABOVE:
        raise _Stop("weekly-above-stop")
    if reading.five_hour >= FIVE_HOUR_START_BELOW:
        raise _Stop("five-hour-at-start-limit")


def _cohort(raw: Any) -> tuple[int, int]:
    if raw is None:
        raise _Stop("cohort-state-absent")
    if not isinstance(raw, Mapping) or set(raw) != _COHORT_KEYS:
        raise _Stop("cohort-state-invalid")
    units, weekly = raw["unitsUsed"], raw["cohortWeeklyPercent"]
    if type(units) is not int or type(weekly) is not int or units < 0 or not 0 <= weekly <= 100:
        raise _Stop("cohort-state-invalid")
    return units, weekly


def _deltas(pre: _Reading, post: _Reading) -> tuple[int, int]:
    if post.observed_at <= pre.observed_at:
        raise _Stop("post-reading-not-after-pre-reading")
    if post.observed_at - pre.observed_at > MAX_READING_SPAN:
        raise _Stop("reading-span-too-long")
    five_hour, weekly = post.five_hour - pre.five_hour, post.weekly - pre.weekly
    if five_hour < 0 or weekly < 0:
        raise _Stop("usage-window-reset")
    return five_hour, weekly


def _decide(kind: str, check: Callable[[dict[str, Any]], None]) -> QuotaDecision:
    evidence: dict[str, Any] = {"kind": kind}
    try:
        check(evidence)
    except _Stop as stop:
        return QuotaDecision(False, stop.reason, MappingProxyType(evidence))
    return QuotaDecision(True, "within-caps", MappingProxyType(evidence))


def admit(pre: Any, now: datetime, cohort: Any) -> QuotaDecision:
    """Gate the start of one D2 cohort unit on a fresh pre-reading and cohort state."""
    now = _clock(now)

    def check(evidence: dict[str, Any]) -> None:
        reading = _reading(pre, "pre")
        evidence["pre"] = reading.record()
        _fresh(reading, now, "pre")
        units, weekly = _cohort(cohort)
        evidence["cohort"] = {"unitsUsed": units, "cohortWeeklyPercent": weekly}
        _start_conditions(reading)
        if units >= MAX_UNITS:
            raise _Stop("unit-cap-reached")
        if weekly >= COHORT_MAX_WEEKLY:
            raise _Stop("cohort-weekly-cap-reached")

    return _decide("cohort-unit", check)


def settle(pre: Any, post: Any, now: datetime, cohort: Any) -> QuotaDecision:
    """Check one finished D2 unit; ``proceed`` false stops the cohort.

    ``cohort`` is the state the unit was admitted with; ``evidence["cohort"]`` is the
    state after it, which the caller (SPEC-049) owns and stores. The next ``admit``
    re-checks every start condition on a new pre-reading.
    """
    now = _clock(now)

    def check(evidence: dict[str, Any]) -> None:
        before, after = _reading(pre, "pre"), _reading(post, "post")
        evidence.update(pre=before.record(), post=after.record())
        _fresh(after, now, "post")
        units, weekly = _cohort(cohort)
        five_hour, weekly_delta = _deltas(before, after)
        evidence.update(fiveHourDelta=five_hour, weeklyDelta=weekly_delta,
                        cohort={"unitsUsed": units + 1,
                                "cohortWeeklyPercent": weekly + weekly_delta})
        if five_hour > SESSION_MAX_FIVE_HOUR:
            raise _Stop("session-above-five-hour-cap")
        if weekly + weekly_delta > COHORT_MAX_WEEKLY:
            raise _Stop("cohort-above-weekly-cap")
        _start_conditions(after)

    return _decide("cohort-unit", check)


def admit_probe(pre: Any, now: datetime, probes_started: int) -> QuotaDecision:
    """Gate one live qualification probe session (NC-10), apart from the D2 caps."""
    now = _clock(now)

    def check(evidence: dict[str, Any]) -> None:
        reading = _reading(pre, "pre")
        evidence["pre"] = reading.record()
        _fresh(reading, now, "pre")
        if type(probes_started) is not int or probes_started < 0:
            raise _Stop("probe-count-invalid")
        evidence["probesStarted"] = probes_started
        _start_conditions(reading)
        if probes_started >= PROBE_MAX_SESSIONS:
            raise _Stop("probe-session-cap-reached")

    return _decide("live-probe", check)


def settle_probe(pre: Any, post: Any, now: datetime) -> QuotaDecision:
    """Check one finished probe session; ``proceed`` false stops the attempt."""
    now = _clock(now)

    def check(evidence: dict[str, Any]) -> None:
        before, after = _reading(pre, "pre"), _reading(post, "post")
        evidence.update(pre=before.record(), post=after.record())
        _fresh(after, now, "post")
        five_hour, weekly_delta = _deltas(before, after)
        evidence.update(fiveHourDelta=five_hour, weeklyDelta=weekly_delta)
        if five_hour > PROBE_MAX_FIVE_HOUR:
            raise _Stop("probe-above-five-hour-cap")
        _start_conditions(after)

    return _decide("live-probe", check)
