# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded subscription allocation estimates, separate from actual money.

The estimator performs no provider/account access and never writes actual cash
or provider-accounting amounts. Evidence authenticity remains an injected
trusted-verifier responsibility at capture admission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext
import hashlib
import json
import re
from types import MappingProxyType
from typing import Any, Mapping

SCHEMA = "agent-braid-m45-subscription-estimate-v1"
REGISTRATION_FIELD = "subscriptionAllocationUpperBound"
METHOD_ID = "m45-nominal-28day-active-time-upper-bound-v1"
PERIOD_SECONDS = 2_419_200
MAX_ACTIVE_SECONDS_PER_HOST = 57_600
MAX_ACTIVE_TIME_OBSERVATION_AGE_SECONDS = 60
MAX_ACTIVE_TIME_FUTURE_SKEW_SECONDS = 0
RESERVATION_EUR = Decimal("5.045")
_SHA = re.compile(r"^[0-9a-f]{64}$")
_HOSTS = frozenset({"codex", "claude-code"})


class EstimateError(ValueError):
    """A subscription estimate is missing, stale, or outside its frozen bound."""


@dataclass(frozen=True)
class ActiveTimeEvidence:
    """Verifier-bound cumulative active seconds for a frozen cohort and roster."""

    registration_sha256: str
    ledger_sha256: str
    source_ref: str
    source_sha256: str
    observed_at: str
    seconds_by_host: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "seconds_by_host", MappingProxyType(dict(self.seconds_by_host)))

    def as_dict(self) -> dict[str, Any]:
        validate_active_time_evidence(self)
        return {
            "registrationSha256": self.registration_sha256,
            "ledgerSha256": self.ledger_sha256,
            "sourceRef": self.source_ref,
            "sourceSha256": self.source_sha256,
            "observedAt": self.observed_at,
            "activeSecondsByHost": dict(sorted(self.seconds_by_host.items())),
        }


@dataclass(frozen=True)
class EstimateAssessment:
    reservation_eur: Decimal
    allocated_upper_bound_eur: Decimal
    remaining_reservation_eur: Decimal
    seconds_by_host: Mapping[str, int]
    evidence_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "seconds_by_host", MappingProxyType(dict(self.seconds_by_host)))

    def as_dict(self) -> dict[str, Any]:
        return {
            "accountingStatus": "estimated-reservation",
            "subscriptionAllocationUpperBoundEur": str(self.allocated_upper_bound_eur),
            "reservationEur": str(self.reservation_eur),
            "remainingReservationEur": str(self.remaining_reservation_eur),
            "activeSecondsByHost": dict(sorted(self.seconds_by_host.items())),
            "activeTimeEvidenceSha256": self.evidence_sha256,
            "allocatedSubscriptionCostEur": None,
            "providerAccountingCostEur": None,
            "utilityClaimEligible": False,
        }


@dataclass(frozen=True)
class RuntimeGuard:
    """Per-process tightening derived from the pre-dispatch cohort snapshot."""

    registration_sha256: str
    ledger_sha256: str
    host: str
    prior_active_seconds_by_host: Mapping[str, int]
    source_sha256: str
    observed_at: str
    prices_eur_per_month: Mapping[str, Decimal]
    nominal_period_seconds: int
    reservation_eur: Decimal
    policy_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "prior_active_seconds_by_host",
                           MappingProxyType(dict(self.prior_active_seconds_by_host)))
        object.__setattr__(self, "prices_eur_per_month", MappingProxyType(
            {key: Decimal(str(value)) for key, value in self.prices_eur_per_month.items()}))

    def validate(self) -> None:
        if not _SHA.fullmatch(self.registration_sha256) or not _SHA.fullmatch(self.ledger_sha256):
            raise EstimateError("runtime guard must bind the registration and 108-slot ledger")
        if not _SHA.fullmatch(self.source_sha256):
            raise EstimateError("runtime guard must bind the verified active-time source")
        _parse_utc_timestamp(self.observed_at)
        if self.host not in _HOSTS:
            raise EstimateError("runtime guard host is not registered")
        values = self.prior_active_seconds_by_host
        if not isinstance(values, Mapping) or set(values) != set(_HOSTS):
            raise EstimateError("runtime guard requires both host active-time totals")
        if (set(self.prices_eur_per_month) != set(_HOSTS)
                or self.nominal_period_seconds != PERIOD_SECONDS
                or self.reservation_eur != RESERVATION_EUR
                or not isinstance(self.policy_sha256, str) or not _SHA.fullmatch(self.policy_sha256)):
            raise EstimateError("runtime guard convention differs from its validated registration")
        for host, seconds in values.items():
            if type(seconds) is not int or not 0 <= seconds <= MAX_ACTIVE_SECONDS_PER_HOST:
                raise EstimateError(f"{host} active-time total is outside its registered bound")
            if not self.prices_eur_per_month[host].is_finite() or self.prices_eur_per_month[host] <= 0:
                raise EstimateError(f"{host} registered price is not finite and positive")

    def remaining_seconds(self) -> int:
        self.validate()
        return MAX_ACTIVE_SECONDS_PER_HOST - self.prior_active_seconds_by_host[self.host]

    def validate_observation_freshness(self) -> None:
        validate_observation_freshness(self.observed_at)

    def assess_elapsed(self, elapsed_seconds: float) -> Decimal:
        self.validate()
        if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)):
            raise EstimateError("runtime elapsed time must be finite and nonnegative")
        from math import isfinite, ceil
        if not isfinite(float(elapsed_seconds)) or elapsed_seconds < 0:
            raise EstimateError("runtime elapsed time must be finite and nonnegative")
        active = dict(self.prior_active_seconds_by_host)
        active[self.host] += ceil(elapsed_seconds)
        if active[self.host] > MAX_ACTIVE_SECONDS_PER_HOST:
            raise EstimateError("subscription per-host active-time cap reached")
        with localcontext() as context:
            context.prec = 50
            raw_amount = sum((self.prices_eur_per_month[host] * Decimal(active[host]) /
                              Decimal(self.nominal_period_seconds) for host in _HOSTS), Decimal("0"))
            amount = (raw_amount * Decimal(1000)).to_integral_value(rounding=ROUND_CEILING) / Decimal(1000)
        if amount > RESERVATION_EUR:
            raise EstimateError("subscription estimate reservation exhausted during execution")
        return amount


def validate_policy(raw: Any) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping) or raw.get("schema") != SCHEMA:
        raise EstimateError("registration requires the versioned subscription estimate policy")
    if raw.get("methodId") != METHOD_ID:
        raise EstimateError("subscription estimate method differs from the approved convention")
    if raw.get("nominalPeriodSeconds") != PERIOD_SECONDS:
        raise EstimateError("subscription estimate requires the nominal 28-day denominator")
    if raw.get("maxActiveSecondsPerHost") != MAX_ACTIVE_SECONDS_PER_HOST:
        raise EstimateError("subscription estimate per-host active-time cap differs")
    try:
        reservation = Decimal(str(raw.get("reservationEur")))
        ceiling = Decimal(str(raw.get("budgetCeilingEur")))
        prices = raw.get("pricesEurPerMonth")
        if not isinstance(prices, Mapping):
            raise EstimateError("subscription estimate prices are missing")
        if set(prices) != set(_HOSTS):
            raise EstimateError("subscription estimate requires exactly both registered host prices")
        normalized = {host: Decimal(str(prices.get(host))) for host in _HOSTS}
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EstimateError("subscription estimate monetary assumptions are invalid") from exc
    if (not reservation.is_finite() or not ceiling.is_finite()
            or any(not value.is_finite() or value <= 0 for value in normalized.values())):
        raise EstimateError("subscription estimate monetary assumptions must be finite and positive")
    if reservation != RESERVATION_EUR or ceiling != Decimal("25.00"):
        raise EstimateError("subscription estimate reservation or EUR 25 ceiling differs")
    exact_total = sum(normalized.values(), Decimal("0")) * Decimal(MAX_ACTIVE_SECONDS_PER_HOST) / Decimal(PERIOD_SECONDS)
    if exact_total != reservation:
        raise EstimateError("registered per-host prices do not produce the fixed reservation under the declared convention")
    for name in ("decisionSha256", "codexPriceSourceSha256", "claudeCodePriceSourceSha256"):
        if not isinstance(raw.get(name), str) or not _SHA.fullmatch(raw[name]):
            raise EstimateError(f"subscription estimate must bind {name}")
    return raw


def validate_active_time_evidence(evidence: ActiveTimeEvidence) -> None:
    if not isinstance(evidence, ActiveTimeEvidence):
        raise EstimateError("verified cumulative active-time evidence is required")
    for name, digest in (("registration", evidence.registration_sha256),
                         ("ledger", evidence.ledger_sha256),
                         ("active-time source", evidence.source_sha256)):
        if not isinstance(digest, str) or not _SHA.fullmatch(digest):
            raise EstimateError(f"{name} SHA-256 is missing or invalid")
    if not isinstance(evidence.source_ref, str) or not evidence.source_ref.strip():
        raise EstimateError("active-time evidence source reference is required")
    _parse_utc_timestamp(evidence.observed_at)
    values = evidence.seconds_by_host
    if not isinstance(values, Mapping) or set(values) != set(_HOSTS):
        raise EstimateError("active-time evidence must cover both registered hosts")
    for host, seconds in values.items():
        if type(seconds) is not int or seconds < 0:
            raise EstimateError(f"{host} active time must be a known nonnegative integer")
        if seconds > MAX_ACTIVE_SECONDS_PER_HOST:
            raise EstimateError(f"{host} active-time cap is exceeded")


def assess(policy: Mapping[str, Any], evidence: ActiveTimeEvidence, *,
           registration_sha256: str, ledger_sha256: str) -> EstimateAssessment:
    validate_policy(policy)
    validate_active_time_evidence(evidence)
    if (evidence.registration_sha256 != registration_sha256
            or evidence.ledger_sha256 != ledger_sha256):
        raise EstimateError("active-time evidence is bound to a different registration or roster ledger")
    with localcontext() as context:
        context.prec = 50
        prices = _registered_prices(policy)
        amount = sum((prices[host] * Decimal(evidence.seconds_by_host[host]) /
                      Decimal(PERIOD_SECONDS) for host in _HOSTS), Decimal("0"))
        amount = (amount * Decimal(1000)).to_integral_value(rounding=ROUND_CEILING) / Decimal(1000)
    reservation = RESERVATION_EUR
    if amount > reservation:
        raise EstimateError("subscription estimate reservation is exhausted")
    return EstimateAssessment(reservation, amount, reservation - amount,
                              dict(evidence.seconds_by_host), evidence_sha256(evidence))


def policy_sha256(policy: Mapping[str, Any]) -> str:
    validate_policy(policy)
    encoded = json.dumps(policy, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _registered_prices(policy: Mapping[str, Any]) -> Mapping[str, Decimal]:
    validate_policy(policy)
    return MappingProxyType({host: Decimal(str(policy["pricesEurPerMonth"][host]))
                             for host in _HOSTS})


def runtime_guard(registration_sha256: str, ledger_sha256: str, host: str,
                  evidence: ActiveTimeEvidence, policy: Mapping[str, Any]) -> RuntimeGuard:
    validate_policy(policy)
    validate_active_time_evidence(evidence)
    if evidence.registration_sha256 != registration_sha256 or evidence.ledger_sha256 != ledger_sha256:
        raise EstimateError("runtime guard evidence does not match its registration and ledger")
    guard = RuntimeGuard(registration_sha256, ledger_sha256, host,
                         dict(evidence.seconds_by_host), evidence.source_sha256,
                         evidence.observed_at,
                         _registered_prices(policy), PERIOD_SECONDS, RESERVATION_EUR,
                         policy_sha256(policy))
    guard.validate()
    return guard


def evidence_sha256(evidence: ActiveTimeEvidence) -> str:
    encoded = json.dumps(evidence.as_dict(), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_observation_freshness(observed_at: str, *, now: datetime | None = None,
                                   maximum_age_seconds: int = MAX_ACTIVE_TIME_OBSERVATION_AGE_SECONDS,
                                   future_skew_seconds: int = MAX_ACTIVE_TIME_FUTURE_SKEW_SECONDS) -> None:
    observed = _parse_utc_timestamp(observed_at)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() != timedelta(0):
        raise EstimateError("active-time freshness reference must be UTC")
    age = (current - observed).total_seconds()
    if age < -future_skew_seconds:
        raise EstimateError("active-time observation timestamp is in the future")
    if age > maximum_age_seconds:
        raise EstimateError("active-time observation is stale")


def _parse_utc_timestamp(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EstimateError("active-time evidence UTC timestamp is required")
    if not value.endswith("Z"):
        raise EstimateError("active-time evidence timestamp must use ISO-8601 UTC Z format")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except ValueError as exc:
        raise EstimateError("active-time evidence timestamp must be valid ISO-8601 UTC") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise EstimateError("active-time evidence timestamp must use UTC")
    return parsed.astimezone(timezone.utc)
