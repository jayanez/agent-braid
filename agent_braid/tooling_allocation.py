# SPDX-License-Identifier: AGPL-3.0-only
"""Provisional exact time-allocation arithmetic for M4.5 subscription costs.

This module is a pure calculator. It does not authenticate source data, validate
caller claims of interval completeness, convert currencies, choose rounding,
issue MoneyReceipt objects, or grant dispatch authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import re
from itertools import islice
from typing import Iterable, Literal, Sequence

SCHEMA_VERSION = "agent-braid-m45-time-allocation-calculation-v1"
MAX_INTERVALS = 4096
MAX_DECIMAL_DIGITS = 30
MAX_DECIMAL_EXPONENT = 30
MAX_DECIMAL_TEXT_CHARS = 64
MAX_RATIONAL_DIGITS = 128
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_SHA256 = re.compile(r"[a-f0-9]{64}\Z")
_CURRENCY = re.compile(r"[A-Z]{3}\Z")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_UTC_TIMESTAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)\Z")


class AllocationError(ValueError):
    """An allocation input is malformed, unsupported, or outside bounds."""


@dataclass(frozen=True)
class UsageInterval:
    """One externally referenced interval of actual use; authenticity is unverified."""

    receipt_ref: str
    receipt_sha256: str
    started_at: str
    ended_at: str

    def __post_init__(self) -> None:
        _identifier(self.receipt_ref, "interval receipt reference")
        _sha256(self.receipt_sha256, "interval receipt SHA-256")
        start = _parse_utc(self.started_at, "interval start")
        end = _parse_utc(self.ended_at, "interval end")
        if end <= start:
            raise AllocationError("usage interval must have positive duration")


@dataclass(frozen=True, init=False)
class IntervalCoverage:
    """Caller-supplied coverage declaration and immutable interval snapshot.

    ``declared_complete`` means the caller declares a complete observation,
    including the meaningful zero-use case. This calculator does not verify
    that declaration or the interval receipt hashes.
    """

    state: Literal["unknown", "declared-complete"]
    intervals: tuple[UsageInterval, ...]

    def __init__(self, state: Literal["unknown", "declared-complete"],
                 intervals: Iterable[UsageInterval] | None = None) -> None:
        if state == "unknown":
            if intervals is not None:
                raise AllocationError("unknown interval coverage must omit its interval list")
            frozen: tuple[UsageInterval, ...] = ()
        elif state == "declared-complete":
            if intervals is None:
                raise AllocationError("declared-complete coverage requires an explicit interval list")
            if isinstance(intervals, Sequence) and len(intervals) > MAX_INTERVALS:
                raise AllocationError(f"interval receipt count exceeds {MAX_INTERVALS}")
            frozen = tuple(islice(iter(intervals), MAX_INTERVALS + 1))
            if len(frozen) > MAX_INTERVALS:
                raise AllocationError(f"interval receipt count exceeds {MAX_INTERVALS}")
            if any(not isinstance(item, UsageInterval) for item in frozen):
                raise AllocationError("interval coverage must contain typed UsageInterval records")
        else:
            raise AllocationError("unknown interval coverage state")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "intervals", frozen)

    @classmethod
    def unknown(cls) -> "IntervalCoverage":
        return cls("unknown")

    @classmethod
    def declared_complete(cls, intervals: Iterable[UsageInterval]) -> "IntervalCoverage":
        """Declare complete interval coverage; this is not an attestation."""
        return cls("declared-complete", intervals)


def _identifier(value: object, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise AllocationError(f"invalid {label}")


def _sha256(value: object, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise AllocationError(f"{label} must be a lowercase SHA-256 digest")


def _parse_utc(value: object, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and len(value) <= 32 and _UTC_TIMESTAMP.fullmatch(value):
        try:
            parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
        except ValueError as exc:
            raise AllocationError(f"{label} must be an explicit UTC timestamp") from exc
    else:
        raise AllocationError(f"{label} must be an explicit UTC timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise AllocationError(f"{label} must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def _iso_utc(value: datetime) -> str:
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def _microseconds(value: datetime) -> int:
    delta = value - _EPOCH
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise AllocationError(f"{label} must be a finite nonnegative Decimal")
    sign, digits, exponent = value.as_tuple()
    if sign or len(digits) > MAX_DECIMAL_DIGITS or abs(exponent) > MAX_DECIMAL_EXPONENT:
        raise AllocationError(f"{label} exceeds bounded Decimal precision or exponent")
    if value < 0:
        raise AllocationError(f"{label} must be nonnegative")
    _decimal_text(value, label)
    return value


def _decimal_text(value: Decimal, label: str = "Decimal") -> str:
    sign, digits, exponent = value.as_tuple()
    if sign:
        raise AllocationError(f"{label} must be nonnegative")
    coefficient = "".join(str(digit) for digit in digits) or "0"
    if value.is_zero():
        result = "0"
    elif exponent >= 0:
        result = coefficient + ("0" * exponent)
    else:
        split = len(coefficient) + exponent
        if split > 0:
            result = coefficient[:split] + "." + coefficient[split:]
        else:
            result = "0." + ("0" * (-split)) + coefficient
        result = result.rstrip("0").rstrip(".")
    if len(result) > MAX_DECIMAL_TEXT_CHARS:
        raise AllocationError(f"{label} exceeds bounded decimal representation")
    return result


def _canonical_sha256(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _rational(value: Fraction, label: str) -> dict[str, str]:
    numerator = str(value.numerator)
    denominator = str(value.denominator)
    if len(numerator) > MAX_RATIONAL_DIGITS or len(denominator) > MAX_RATIONAL_DIGITS:
        raise AllocationError(f"{label} exceeds bounded rational representation")
    return {"numerator": numerator, "denominator": denominator,
            "rational": f"{numerator}/{denominator}"}


def _interval_payload(interval: UsageInterval) -> tuple[dict[str, object], int, int]:
    start = _parse_utc(interval.started_at, "interval start")
    end = _parse_utc(interval.ended_at, "interval end")
    start_us = _microseconds(start)
    end_us = _microseconds(end)
    return ({"receiptRef": interval.receipt_ref,
             "receiptSha256": interval.receipt_sha256,
             "startedAt": _iso_utc(start), "endedAt": _iso_utc(end),
             "durationMicroseconds": end_us - start_us}, start_us, end_us)


def _union_duration(intervals: list[tuple[int, int]]) -> int:
    if not intervals:
        return 0
    intervals.sort(key=lambda item: (item[0], item[1]))
    total = 0
    current_start, current_end = intervals[0]
    for start, end in intervals[1:]:
        if start > current_end:
            total += current_end - current_start
            current_start, current_end = start, end
        elif end > current_end:
            current_end = end
    return total + current_end - current_start


def calculate_subscription_time_allocation(
    *,
    source_ref: str,
    source_sha256: str,
    account_sha256: str,
    period_id: str,
    period_started_at: str | datetime,
    period_ended_at: str | datetime,
    fixed_period_fee: Decimal,
    currency: str,
    interval_coverage: IntervalCoverage,
) -> dict[str, object]:
    """Calculate exact fee × union(actual-use intervals) / elapsed period.

    ``interval_coverage=IntervalCoverage.unknown()`` produces an explicit
    unknown result. ``IntervalCoverage.declared_complete(())`` is a caller-declared
    complete zero-use observation and produces exact zero. The declaration and
    all supplied hashes/refs are inputs only; this function authenticates none.
    No currency conversion or rounding is performed.
    """
    _identifier(source_ref, "source reference")
    _sha256(source_sha256, "source SHA-256")
    _sha256(account_sha256, "account SHA-256")
    _identifier(period_id, "period id")
    if not isinstance(currency, str) or not _CURRENCY.fullmatch(currency):
        raise AllocationError("currency must be a three-letter uppercase code")
    if not isinstance(interval_coverage, IntervalCoverage):
        raise AllocationError("typed interval coverage is required")
    fee = _decimal(fixed_period_fee, "fixed period fee")
    period_start = _parse_utc(period_started_at, "period start")
    period_end = _parse_utc(period_ended_at, "period end")
    period_start_us = _microseconds(period_start)
    period_end_us = _microseconds(period_end)
    elapsed_us = period_end_us - period_start_us
    if elapsed_us <= 0:
        raise AllocationError("billing period must have positive elapsed duration")

    if interval_coverage.state == "unknown":
        interval_items: list[dict[str, object]] = []
        union_us: int | None = None
        share_payload = None
        amount_payload = None
        result_state = "unknown"
    else:
        intervals = interval_coverage.intervals
        if len(intervals) > MAX_INTERVALS:
            raise AllocationError(f"interval receipt count exceeds {MAX_INTERVALS}")
        refs: set[str] = set()
        digests: set[str] = set()
        interval_ranges: list[tuple[int, int]] = []
        records: list[tuple[int, int, str, str, dict[str, object]]] = []
        for interval in intervals:
            if not isinstance(interval, UsageInterval):
                raise AllocationError("interval coverage must contain typed UsageInterval records")
            if interval.receipt_ref in refs or interval.receipt_sha256 in digests:
                raise AllocationError("duplicate interval receipt reference or digest")
            refs.add(interval.receipt_ref)
            digests.add(interval.receipt_sha256)
            item, start_us, end_us = _interval_payload(interval)
            if start_us < period_start_us or end_us > period_end_us:
                raise AllocationError("usage interval falls outside the fixed billing period")
            records.append((start_us, end_us, interval.receipt_ref, interval.receipt_sha256, item))
            interval_ranges.append((start_us, end_us))
        records.sort(key=lambda item: item[:4])
        interval_items = [item[4] for item in records]
        union_us = _union_duration(interval_ranges)
        share = Fraction(union_us, elapsed_us)
        allocated = Fraction(fee) * share
        share_payload = _rational(share, "allocation share")
        amount_payload = {"currency": currency, **_rational(allocated, "allocated amount")}
        result_state = "calculated"

    inputs = {
        "schemaVersion": SCHEMA_VERSION,
        "source": {"sourceRef": source_ref, "sourceSha256": source_sha256,
                   "accountSha256": account_sha256, "fixedPeriodFee": _decimal_text(fee),
                   "currency": currency},
        "period": {"periodId": period_id, "startedAt": _iso_utc(period_start),
                   "endedAt": _iso_utc(period_end), "elapsedMicroseconds": elapsed_us},
        "intervalCoverage": {"state": interval_coverage.state, "receipts": interval_items},
    }
    calculation_inputs_sha256 = _canonical_sha256(inputs)
    payload: dict[str, object] = {
        "schemaVersion": SCHEMA_VERSION,
        "resultType": "provisional-calculation-not-final-money-receipt",
        "state": result_state,
        "source": inputs["source"],
        "period": inputs["period"],
        "intervalCoverage": inputs["intervalCoverage"],
        "calculationInputsSha256": calculation_inputs_sha256,
        "calculation": {
            "unionDurationMicroseconds": union_us,
            "elapsedPeriodMicroseconds": elapsed_us,
            "allocationShare": share_payload,
            "allocatedAmount": amount_payload,
        },
        "finalMoneyReceiptIssued": False,
        "limits": ["Caller-provided hashes and coverage declarations are not authenticated",
                   "No MoneyReceipt, verifier attestation, dispatch decision, FX, or rounding is issued"],
    }
    payload["canonicalPayloadSha256"] = _canonical_sha256(payload)
    return payload
