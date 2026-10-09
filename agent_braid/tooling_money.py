# SPDX-License-Identifier: AGPL-3.0-only
"""Experimental v2 monetary records for the M4.5 cohort.

This module is an additive representation.  It does not change the v1 cost
ledger, read provider billing pages, choose an allocation method, or calculate
FX/allocation/rate-card amounts.  An external verifier must authenticate each
source and bind its attestation to the exact immutable receipt.  A separate
policy verifier authenticates a registered allocation-method binding; that
binding is not an approval record.

The three EUR measures are deliberately disjoint.  ``actualAdditionalSpendEur``
is a proposed conservative study-cash measure spanning provider/setup activity
and paid human review; it is distinct from prepaid subscription value.  The
EUR 0 cap is a proposed study-level no-additional-cash boundary, stricter than
the provider-only billing policy and not authorization to pay reviewers.
Unpaid reviewer fees and human-time costing are not inferred as zero.  The
three EUR measures are deliberately disjoint.  API-reference estimates
remain estimates and are never added to actual additional spend or allocated
subscription cost.  Missing receipts or amounts remain unknown, including for
an authenticated EUR 0 additional-spend authorization.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from decimal import DecimalException
from fractions import Fraction
import hashlib
import json
import re
import threading
from typing import Literal, Protocol

from . import tooling_evaluation as evaluation
from .tooling_subscription import policy_sha256 as subscription_policy_sha256

SCHEMA_VERSION = "agent-braid-m45-money-receipt-v2"
MEASURES = (
    "actualAdditionalSpendEur",
    "allocatedSubscriptionCostEur",
    "apiReferenceEstimateEur",
)
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_CURRENCY = re.compile(r"[A-Z]{3}\Z")
_KINDS = {"invoice", "provider-meter", "subscription-statement", "reference-rate-card"}
_MEASURE_SOURCE_KINDS = {
    "actualAdditionalSpendEur": {"invoice", "provider-meter"},
    "allocatedSubscriptionCostEur": {"subscription-statement"},
    "apiReferenceEstimateEur": {"reference-rate-card"},
}
_MEASURE_ACTIVITY_KINDS = {
    "actualAdditionalSpendEur": {"setup", "attempt", "reviewer"},
    "allocatedSubscriptionCostEur": {"setup", "attempt"},
    "apiReferenceEstimateEur": {"attempt"},
}
_MAX_ACTIVITIES = 256
_MAX_DECIMAL_DIGITS = 30
_MAX_DECIMAL_EXPONENT = 30
_MAX_SERIALIZED_DECIMAL_CHARS = 64


class MoneyAccountingError(ValueError):
    """A receipt is malformed, unauthenticated, duplicated, or incomplete."""


def _identifier(value: str, label: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise MoneyAccountingError(f"invalid {label}")


def _digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise MoneyAccountingError(f"{label} must be a lowercase SHA-256 digest")


def _timestamp(value: str, label: str) -> datetime:
    if not isinstance(value, str):
        raise MoneyAccountingError(f"{label} must be an explicit UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MoneyAccountingError(f"{label} must be an explicit UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise MoneyAccountingError(f"{label} must be an explicit UTC timestamp")
    return parsed


def _decimal(value: Decimal, label: str, *, positive: bool = False) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise MoneyAccountingError(f"{label} must be a finite nonnegative Decimal")
    sign, digits, exponent = value.as_tuple()
    if sign or len(digits) > _MAX_DECIMAL_DIGITS or abs(exponent) > _MAX_DECIMAL_EXPONENT:
        raise MoneyAccountingError(f"{label} exceeds bounded Decimal precision or exponent")
    if value < 0:
        raise MoneyAccountingError(f"{label} must be a finite nonnegative Decimal")
    if positive and value == 0:
        raise MoneyAccountingError(f"{label} must be positive")


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if value == 0:
        return "0"
    sign, digits, exponent = value.as_tuple()
    text = format(Decimal((sign, digits, exponent)), "f")
    if len(text) > _MAX_SERIALIZED_DECIMAL_CHARS:
        raise MoneyAccountingError("serialized Decimal exceeds the bounded representation")
    return text


def _exact_decimal_sum(values: list[Decimal], label: str, *, max_digits: int = 36) -> Decimal:
    """Sum finite decimals exactly, independent of ambient Decimal context."""
    if not values:
        return Decimal(0)
    try:
        exponent = min(value.as_tuple().exponent for value in values)
        total = 0
        for value in values:
            sign, digits, item_exponent = value.as_tuple()
            coefficient = int("".join(str(digit) for digit in digits) or "0")
            total += (-coefficient if sign else coefficient) * (10 ** (item_exponent - exponent))
        sign = int(total < 0)
        digits = tuple(int(char) for char in str(abs(total)))
        result = Decimal((sign, digits, exponent))
    except (DecimalException, OverflowError, ValueError, MemoryError) as exc:
        raise MoneyAccountingError(f"{label} cannot be represented exactly") from exc
    if not result.is_finite() or len(result.as_tuple().digits) > max_digits:
        raise MoneyAccountingError(f"{label} exceeds the bounded exact aggregate")
    if len(_decimal_text(result) or "") > _MAX_SERIALIZED_DECIMAL_CHARS:
        raise MoneyAccountingError(f"{label} exceeds the bounded serialized aggregate")
    return result


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MoneyActivity:
    """One registered setup, attempt, or reviewer cost boundary."""

    activity_id: str
    kind: Literal["setup", "attempt", "reviewer"]
    account_ref: str
    account_sha256: str
    host: str | None = None
    reviewer_id: str | None = None
    started_at: str | None = None
    ended_at: str | None = None

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "activity id")
        _identifier(self.account_ref, "redacted account reference")
        _digest(self.account_sha256, "account SHA-256")
        if not isinstance(self.kind, str) or self.kind not in {"setup", "attempt", "reviewer"}:
            raise MoneyAccountingError("unknown activity kind")
        if self.host is not None and self.host not in evaluation.HOSTS:
            raise MoneyAccountingError("activity host must match a registered evaluation host")
        if self.kind == "attempt" and (self.host is None or self.reviewer_id is not None):
            raise MoneyAccountingError("attempt activities require a host and cannot identify a reviewer")
        if self.kind == "reviewer":
            _identifier(self.reviewer_id, "registered reviewer id")
            if self.host is not None:
                raise MoneyAccountingError("reviewer activities cannot use a provider host")
        elif self.reviewer_id is not None:
            raise MoneyAccountingError("only reviewer activities may bind a reviewer id")
        if (self.started_at is None) != (self.ended_at is None):
            raise MoneyAccountingError("activity start and end must both be present or both be unknown")
        if self.started_at is not None and _timestamp(self.started_at, "activity start") > _timestamp(
            self.ended_at, "activity end"
        ):
            raise MoneyAccountingError("activity boundaries are out of order")

    def as_dict(self) -> dict[str, str | None]:
        return {
            "activityId": self.activity_id, "kind": self.kind,
            "accountRef": self.account_ref, "accountSha256": self.account_sha256,
            "host": self.host, "reviewerId": self.reviewer_id,
            "startedAt": self.started_at, "endedAt": self.ended_at,
        }


@dataclass(frozen=True)
class AllocationMethodBinding:
    """Identity of a registered method; this asserts neither approval nor validity."""

    registration_ref: str
    registration_sha256: str
    method_id: str
    method_ref: str
    method_sha256: str
    denominator_id: str
    unit: str

    def __post_init__(self) -> None:
        for value, label in (
            (self.registration_ref, "method registration reference"),
            (self.method_id, "allocation method id"),
            (self.method_ref, "allocation method reference"),
            (self.denominator_id, "allocation denominator id"),
            (self.unit, "allocation unit"),
        ):
            _identifier(value, label)
        _digest(self.registration_sha256, "registration SHA-256")
        _digest(self.method_sha256, "method SHA-256")

    def as_dict(self) -> dict[str, str]:
        return {
            "registrationRef": self.registration_ref,
            "registrationSha256": self.registration_sha256,
            "methodId": self.method_id, "methodRef": self.method_ref,
            "methodSha256": self.method_sha256,
            "denominatorId": self.denominator_id, "unit": self.unit,
        }

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())


@dataclass(frozen=True)
class AllocationShare:
    """Externally calculated share inputs, checked for bounds and cohort totals."""

    numerator: Decimal
    denominator: Decimal

    def __post_init__(self) -> None:
        _decimal(self.numerator, "allocation numerator")
        _decimal(self.denominator, "allocation denominator", positive=True)
        if self.numerator > self.denominator:
            raise MoneyAccountingError("allocation numerator exceeds denominator")

    def as_dict(self) -> dict[str, str]:
        return {"numerator": _decimal_text(self.numerator),
                "denominator": _decimal_text(self.denominator)}


@dataclass(frozen=True)
class MoneyEvidence:
    """Source, account, period, FX, rate-card, and calculation-input bindings.

    A source scope identifies the unique invoice line, meter slice, subscription
    statement portion, or estimate input set claimed by this activity. Source
    billing periods may be wider than the cohort's allocation coverage period;
    the external verifier attests the exact covered slice.
    """

    source_kind: Literal["invoice", "provider-meter", "subscription-statement", "reference-rate-card"]
    source_ref: str
    source_sha256: str
    source_scope_id: str
    account_ref: str
    account_sha256: str
    source_period_id: str
    source_period_started_at: str
    source_period_ended_at: str
    coverage_period_id: str
    coverage_period_started_at: str
    coverage_period_ended_at: str
    currency: str
    source_amount: Decimal | None
    invoice_ref: str | None = None
    invoice_sha256: str | None = None
    fx_rate_to_eur: Decimal | None = None
    fx_source_ref: str | None = None
    fx_source_sha256: str | None = None
    rate_card_ref: str | None = None
    rate_card_sha256: str | None = None
    calculation_inputs_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.source_kind, str) or self.source_kind not in _KINDS:
            raise MoneyAccountingError("unknown monetary source kind")
        for value, label in (
            (self.source_ref, "source reference"),
            (self.source_scope_id, "source scope id"),
            (self.account_ref, "redacted account reference"),
            (self.source_period_id, "source billing period id"),
            (self.coverage_period_id, "cohort coverage period id"),
        ):
            _identifier(value, label)
        _digest(self.source_sha256, "source SHA-256")
        _digest(self.account_sha256, "account SHA-256")
        source_start = _timestamp(self.source_period_started_at, "source billing period start")
        source_end = _timestamp(self.source_period_ended_at, "source billing period end")
        coverage_start = _timestamp(self.coverage_period_started_at, "cohort coverage period start")
        coverage_end = _timestamp(self.coverage_period_ended_at, "cohort coverage period end")
        if source_start >= source_end or coverage_start >= coverage_end:
            raise MoneyAccountingError("source and coverage periods must have positive duration")
        if source_start > coverage_start or source_end < coverage_end:
            raise MoneyAccountingError("source billing period must contain the cohort coverage period")
        if not isinstance(self.currency, str) or not _CURRENCY.fullmatch(self.currency):
            raise MoneyAccountingError("currency must be a three-letter uppercase code")
        if self.source_amount is not None:
            _decimal(self.source_amount, "source amount")
        if self.fx_rate_to_eur is not None:
            _decimal(self.fx_rate_to_eur, "FX rate", positive=True)
        for ref, digest, label in (
            (self.invoice_ref, self.invoice_sha256, "invoice"),
            (self.fx_source_ref, self.fx_source_sha256, "FX source"),
            (self.rate_card_ref, self.rate_card_sha256, "rate card"),
        ):
            if (ref is None) != (digest is None):
                raise MoneyAccountingError(f"{label} reference and digest must appear together")
            if ref is not None:
                _identifier(ref, f"{label} reference")
                _digest(digest, f"{label} SHA-256")
        if self.calculation_inputs_sha256 is not None:
            _digest(self.calculation_inputs_sha256, "calculation-input SHA-256")
        if self.source_kind == "invoice" and self.invoice_ref is None:
            raise MoneyAccountingError("invoice sources require an invoice reference and digest")
        if self.currency == "EUR":
            if self.fx_rate_to_eur != Decimal(1):
                raise MoneyAccountingError("EUR sources must use the identity FX rate")
            if self.fx_source_ref is not None:
                raise MoneyAccountingError("EUR identity conversion does not use an external FX source")
        elif self.fx_rate_to_eur is not None and self.fx_source_ref is None:
            raise MoneyAccountingError("foreign-currency FX rate requires its source reference and digest")

    def as_dict(self) -> dict[str, object]:
        return {
            "sourceKind": self.source_kind, "sourceRef": self.source_ref,
            "sourceSha256": self.source_sha256, "sourceScopeId": self.source_scope_id,
            "accountRef": self.account_ref, "accountSha256": self.account_sha256,
            "sourcePeriodId": self.source_period_id,
            "sourcePeriodStartedAt": self.source_period_started_at,
            "sourcePeriodEndedAt": self.source_period_ended_at,
            "coveragePeriodId": self.coverage_period_id,
            "coveragePeriodStartedAt": self.coverage_period_started_at,
            "coveragePeriodEndedAt": self.coverage_period_ended_at,
            "currency": self.currency,
            "sourceAmount": _decimal_text(self.source_amount),
            "invoiceRef": self.invoice_ref, "invoiceSha256": self.invoice_sha256,
            "fxRateToEur": _decimal_text(self.fx_rate_to_eur),
            "fxSourceRef": self.fx_source_ref, "fxSourceSha256": self.fx_source_sha256,
            "rateCardRef": self.rate_card_ref, "rateCardSha256": self.rate_card_sha256,
            "calculationInputsSha256": self.calculation_inputs_sha256,
        }


@dataclass(frozen=True)
class MoneyReceipt:
    """One externally verifiable monetary measure for one frozen activity."""

    activity_id: str
    measure: Literal[
        "actualAdditionalSpendEur",
        "allocatedSubscriptionCostEur",
        "apiReferenceEstimateEur",
    ]
    amount_eur: Decimal | None
    observed_at: str
    evidence: MoneyEvidence
    allocation_method: AllocationMethodBinding | None = None
    allocation_share: AllocationShare | None = None

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "activity id")
        if not isinstance(self.measure, str) or self.measure not in MEASURES:
            raise MoneyAccountingError("unknown monetary measure")
        if not isinstance(self.evidence, MoneyEvidence):
            raise MoneyAccountingError("typed monetary source evidence is required")
        if (self.allocation_method is not None
                and not isinstance(self.allocation_method, AllocationMethodBinding)):
            raise MoneyAccountingError("typed registered allocation method binding is required")
        if self.allocation_share is not None and not isinstance(self.allocation_share, AllocationShare):
            raise MoneyAccountingError("typed allocation share is required")
        if self.amount_eur is not None:
            _decimal(self.amount_eur, "EUR amount")
            if self.evidence.source_amount is None:
                raise MoneyAccountingError("a known EUR amount requires a source amount")
            if self.evidence.currency != "EUR" and (
                self.evidence.fx_rate_to_eur is None or self.evidence.fx_source_ref is None
            ):
                raise MoneyAccountingError("a known foreign-currency amount requires bound FX evidence")
            if self.evidence.currency != "EUR" and self.evidence.calculation_inputs_sha256 is None:
                raise MoneyAccountingError("foreign-currency EUR amounts require bound conversion inputs")
            if (self.measure == "actualAdditionalSpendEur"
                    and self.evidence.currency == "EUR"
                    and self.amount_eur != self.evidence.source_amount):
                raise MoneyAccountingError("EUR invoice or meter amount must match its source amount")
        if self.evidence.source_kind not in _MEASURE_SOURCE_KINDS[self.measure]:
            raise MoneyAccountingError("source kind is incompatible with monetary measure")
        if self.measure == "apiReferenceEstimateEur":
            if self.evidence.rate_card_ref is None or self.evidence.calculation_inputs_sha256 is None:
                raise MoneyAccountingError("API reference estimates require a bound rate card and calculation inputs")
            if self.allocation_method is not None or self.allocation_share is not None:
                raise MoneyAccountingError("API reference estimates cannot carry subscription allocation data")
        elif self.measure == "allocatedSubscriptionCostEur":
            if (self.allocation_method is None) != (self.allocation_share is None):
                raise MoneyAccountingError("allocation method and share must appear together")
            if self.amount_eur is not None and self.allocation_method is None:
                raise MoneyAccountingError("known subscription allocation requires a registered method binding")
            if self.allocation_method is not None and self.evidence.calculation_inputs_sha256 is None:
                raise MoneyAccountingError("subscription allocation requires a bound calculation-input digest")
        elif self.allocation_method is not None or self.allocation_share is not None:
            raise MoneyAccountingError("actual additional spend cannot carry subscription allocation data")
        _timestamp(self.observed_at, "receipt observation")
        if _timestamp(self.observed_at, "receipt observation") < _timestamp(
            self.evidence.source_period_ended_at, "source billing period end"
        ):
            raise MoneyAccountingError("receipt observation predates the source billing period end")

    def as_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "activityId": self.activity_id, "measure": self.measure,
            "amountEur": _decimal_text(self.amount_eur), "observedAt": self.observed_at,
            "evidence": self.evidence.as_dict(),
            "allocationMethod": self.allocation_method.as_dict() if self.allocation_method else None,
            "allocationShare": self.allocation_share.as_dict() if self.allocation_share else None,
        }

    @property
    def sha256(self) -> str:
        """Digest of the exact, explicit receipt envelope."""
        return _canonical_sha256(self.as_dict())


@dataclass(frozen=True)
class SourceAttestation:
    verifier_id: str
    receipt_sha256: str
    verified_at: str


@dataclass(frozen=True)
class AllocationPolicyAttestation:
    verifier_id: str
    policy_sha256: str
    verified_at: str


class MoneySourceVerifier(Protocol):
    """Authenticates source facts, complete scope, and nonoverlapping source slices.

    For allocated subscription measures it also checks that the EUR claim is
    consistent with the separately verified method/share and the source bill.
    Local receipt hashes bind these claims; they do not authenticate them.
    """

    def verify_source(self, receipt: MoneyReceipt) -> SourceAttestation: ...


class AllocationPolicyVerifier(Protocol):
    """Separately authenticates a registered method identity, not its approval."""

    def verify_registered_method(
        self, binding: AllocationMethodBinding,
    ) -> AllocationPolicyAttestation: ...


@dataclass(frozen=True)
class MoneySummary:
    """Observed and complete totals with separate accounting and claim gates.

    ``required_measures_complete`` covers the registration-required additional
    spend field for all activities. Full economic cost remains incomplete until
    a prospective registered scope resolves reviewer-payment applicability and
    the human-cost fields. API rate-card estimates cannot complete it.
    """

    actual_additional_spend_eur: Decimal | None
    observed_additional_spend_subtotal_eur: Decimal | None
    actual_additional_spend_cap_eur: Decimal
    cap_violation: bool | None
    stop_required: bool
    allocated_subscription_cost_eur: Decimal | None
    api_reference_estimate_eur: Decimal | None
    required_measures_complete: bool
    full_economic_cost_complete: bool
    full_economic_cost_status: str
    missing_required: tuple[tuple[str, str], ...]
    missing_full_economic_cost: tuple[tuple[str, str], ...]
    registration_sha256: str
    roster_sha256: str
    receipt_sha256s: tuple[str, ...]
    human_time_seconds: Decimal | None = None
    human_time_receipt_sha256s: tuple[str, ...] = ()
    user_time_seconds: Decimal | None = None
    reviewer_time_seconds: Decimal | None = None
    study_wall_seconds: Decimal | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "schemaVersion": "agent-braid-m45-money-summary-v2",
            "actualAdditionalSpendEur": _decimal_text(self.actual_additional_spend_eur),
            "observedAdditionalSpendSubtotalEur": _decimal_text(
                self.observed_additional_spend_subtotal_eur
            ),
            "actualAdditionalSpendCapEur": _decimal_text(self.actual_additional_spend_cap_eur),
            "capViolation": self.cap_violation,
            "stopRequired": self.stop_required,
            "allocatedSubscriptionCostEur": _decimal_text(self.allocated_subscription_cost_eur),
            "apiReferenceEstimateEur": _decimal_text(self.api_reference_estimate_eur),
            "requiredMeasuresComplete": self.required_measures_complete,
            "fullEconomicCostComplete": self.full_economic_cost_complete,
            "fullEconomicCostStatus": self.full_economic_cost_status,
            "missingRequired": [
                {"activityId": activity, "measure": measure}
                for activity, measure in self.missing_required
            ],
            "missingFullEconomicCost": [
                {"activityId": activity, "measure": measure}
                for activity, measure in self.missing_full_economic_cost
            ],
            "registrationSha256": self.registration_sha256,
            "rosterSha256": self.roster_sha256,
            "receiptSha256s": list(self.receipt_sha256s),
            "humanTimeSeconds": _decimal_text(self.human_time_seconds),
            "humanTimeReceiptSha256s": list(self.human_time_receipt_sha256s),
            "userTimeSeconds": _decimal_text(self.user_time_seconds),
            "reviewerTimeSeconds": _decimal_text(self.reviewer_time_seconds),
            "studyWallSeconds": _decimal_text(self.study_wall_seconds),
        }


@dataclass(frozen=True)
class MoneyRoster:
    """Exact registration-bound SPEC-044 roster and monetary claim boundary."""

    registration: evaluation.ValidatedRegistration
    period_id: str
    period_started_at: str
    period_ended_at: str
    activities: tuple[MoneyActivity, ...]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not isinstance(self.registration, evaluation.ValidatedRegistration):
            raise MoneyAccountingError("a validated evaluation registration is required")
        try:
            slots = evaluation.generate_slots(self.registration)
        except evaluation.EvaluationError as exc:
            raise MoneyAccountingError("validated registration is missing or has drifted") from exc
        _identifier(self.period_id, "accounting period id")
        if _timestamp(self.period_started_at, "cohort period start") >= _timestamp(
            self.period_ended_at, "cohort period end"
        ):
            raise MoneyAccountingError("cohort period must have positive duration")
        if not isinstance(self.activities, tuple) or not 1 <= len(self.activities) <= _MAX_ACTIVITIES:
            raise MoneyAccountingError("a bounded immutable activity roster is required")
        if any(not isinstance(item, MoneyActivity) for item in self.activities):
            raise MoneyAccountingError("roster entries must be typed MoneyActivity records")
        ids = tuple(item.activity_id for item in self.activities)
        if len(set(ids)) != len(ids):
            raise MoneyAccountingError("activity ids must be unique")
        slot_by_id = {slot.slot_id: slot for slot in slots}
        attempt_activities = {item.activity_id: item for item in self.activities if item.kind == "attempt"}
        if set(attempt_activities) != set(slot_by_id) or len(attempt_activities) != 108:
            raise MoneyAccountingError("attempt activities must equal the exact 108 registered slots")
        billing_policy = self.registration.data.get("billingPolicy")
        if (not isinstance(billing_policy, dict)
                or billing_policy.get("additionalSpendCapEur") != 0):
            raise MoneyAccountingError("the frozen registration must bind the EUR 0 additional-spend cap")
        policy_accounts = {item["host"]: item["accountSha256"] for item in billing_policy["hosts"]}
        for slot_id, activity in attempt_activities.items():
            slot = slot_by_id[slot_id]
            if activity.host != slot.host:
                raise MoneyAccountingError("attempt activity host differs from its registered slot")
            if activity.account_sha256 != policy_accounts.get(slot.host):
                raise MoneyAccountingError("attempt account differs from the registered billing-policy account")
        setups = [item for item in self.activities if item.kind == "setup"]
        if len(setups) != 1 or setups[0].activity_id != "setup":
            raise MoneyAccountingError("one setup activity with id 'setup' is required")
        if setups[0].host is not None and setups[0].account_sha256 != policy_accounts.get(setups[0].host):
            raise MoneyAccountingError("setup account differs from the registered billing-policy account")
        reviewer_ids = {item["reviewerId"] for item in self.registration.data["humanReviewers"]}
        reviewers = [item for item in self.activities if item.kind == "reviewer"]
        if ({item.reviewer_id for item in reviewers} != reviewer_ids
                or len(reviewers) != len(reviewer_ids)
                or any(item.activity_id != f"reviewer:{item.reviewer_id}" for item in reviewers)):
            raise MoneyAccountingError("reviewer activities must bind the exact frozen reviewer IDs")
        start, end = (_timestamp(self.period_started_at, "cohort period start"),
                      _timestamp(self.period_ended_at, "cohort period end"))
        for item in self.activities:
            if item.started_at is None:
                continue
            if _timestamp(item.started_at, "activity start") < start or _timestamp(
                item.ended_at, "activity end"
            ) > end:
                raise MoneyAccountingError("activity boundaries must be inside the frozen cohort period")

    @property
    def registration_ref(self) -> str:
        return self.registration.data["registrationId"]

    @property
    def registration_sha256(self) -> str:
        return self.registration.sha256

    @property
    def required_measures(self) -> tuple[str, ...]:
        """Actual additional-spend evidence is mandatory for every roster row."""
        return ("actualAdditionalSpendEur",)

    @property
    def actual_additional_spend_cap_eur(self) -> Decimal:
        # Proposed study-wide cash cap: zero even for paid review/setup. This
        # intentionally extends beyond provider billing policy and is not
        # payment authorization; prospective protocol registration must ratify
        # the scope before cohort capture.
        return Decimal(str(self.registration.data["billingPolicy"]["additionalSpendCapEur"]))

    @property
    def attempt_slot_by_id(self) -> dict[str, evaluation.AttemptSlot]:
        self.validate()
        return {slot.slot_id: slot for slot in evaluation.generate_slots(self.registration)}

    @property
    def rate_cards_by_host(self) -> dict[str, tuple[str, str]]:
        self.validate()
        return {
            item["host"]: (item["recordId"], item["sha256"])
            for item in self.registration.data["costRates"]["byHost"]
        }

    def as_dict(self) -> dict[str, object]:
        self.validate()
        return {
            "schemaVersion": "agent-braid-m45-money-roster-v2",
            "registrationRef": self.registration_ref,
            "registrationSha256": self.registration_sha256,
            "billingPolicySha256": subscription_policy_sha256(
                self.registration.data["billingPolicy"]
            ),
            "actualAdditionalSpendCapEur": _decimal_text(self.actual_additional_spend_cap_eur),
            "actualAdditionalSpendCapScope": (
                "proposed-study-cash-including-paid-review; requires-prospective-registration"
            ),
            "periodId": self.period_id,
            "periodStartedAt": self.period_started_at,
            "periodEndedAt": self.period_ended_at,
            "activities": [activity.as_dict() for activity in self.activities],
            "requiredMeasures": list(self.required_measures),
        }

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())

    @property
    def activity_by_id(self) -> dict[str, MoneyActivity]:
        return {activity.activity_id: activity for activity in self.activities}


class MoneyLedger:
    """Verify and summarize one frozen monetary roster without changing v1 costs."""

    def __init__(
        self,
        roster: MoneyRoster,
        *,
        source_verifier: MoneySourceVerifier,
        allocation_policy_verifier: AllocationPolicyVerifier | None = None,
    ) -> None:
        if not isinstance(roster, MoneyRoster):
            raise MoneyAccountingError("a frozen MoneyRoster is required")
        roster.validate()
        if not callable(getattr(source_verifier, "verify_source", None)):
            raise MoneyAccountingError("an external monetary source verifier is required")
        if allocation_policy_verifier is not None and not callable(
            getattr(allocation_policy_verifier, "verify_registered_method", None)
        ):
            raise MoneyAccountingError("allocation policy verifier has an invalid interface")
        self.roster = roster
        self._source_verifier = source_verifier
        self._policy_verifier = allocation_policy_verifier
        self._receipts: dict[tuple[str, str], tuple[MoneyReceipt, SourceAttestation]] = {}
        self._policy_attestations: dict[str, AllocationPolicyAttestation] = {}
        self._source_scopes: set[str] = set()
        self._lock = threading.RLock()
        self._verifying = False

    @property
    def history(self) -> tuple[tuple[MoneyReceipt, SourceAttestation], ...]:
        with self._lock:
            return tuple(self._receipts.values())

    @property
    def verified_allocation_policy_attestations(self) -> tuple[AllocationPolicyAttestation, ...]:
        """Externally verified allocation policy records retained by this ledger."""
        with self._lock:
            return tuple(self._policy_attestations.values())

    def add(self, receipt: MoneyReceipt) -> None:
        with self._lock:
            if self._verifying:
                raise MoneyAccountingError("monetary verifier cannot reenter receipt publication")
            if not isinstance(receipt, MoneyReceipt):
                raise MoneyAccountingError("a typed MoneyReceipt is required")
            self.roster.validate()
            activity = self.roster.activity_by_id.get(receipt.activity_id)
            if activity is None:
                raise MoneyAccountingError("receipt activity is outside the frozen roster")
            evidence = receipt.evidence
            if evidence.account_sha256 != activity.account_sha256 or evidence.account_ref != activity.account_ref:
                raise MoneyAccountingError("receipt account binding differs from its roster activity")
            if (evidence.coverage_period_id != self.roster.period_id
                    or evidence.coverage_period_started_at != self.roster.period_started_at
                    or evidence.coverage_period_ended_at != self.roster.period_ended_at):
                raise MoneyAccountingError("receipt coverage differs from the frozen cohort period")
            if receipt.measure == "allocatedSubscriptionCostEur" and activity.kind == "reviewer":
                raise MoneyAccountingError("subscription allocation applies only to provider setup and attempt activities")
            if (receipt.measure == "actualAdditionalSpendEur" and activity.kind == "reviewer"
                    and evidence.source_kind != "invoice"):
                raise MoneyAccountingError("reviewer cash-cost evidence requires an authenticated invoice source")
            if receipt.measure == "apiReferenceEstimateEur":
                if activity.kind != "attempt" or activity.host is None:
                    raise MoneyAccountingError("API reference estimates apply only to registered model attempts")
                expected_rate = self.roster.rate_cards_by_host[activity.host]
                if (evidence.rate_card_ref, evidence.rate_card_sha256) != expected_rate:
                    raise MoneyAccountingError("API reference rate card differs from the registered host rate")
            key = (receipt.activity_id, receipt.measure)
            if key in self._receipts:
                raise MoneyAccountingError("an activity measure can be recorded only once in v2")
            if evidence.source_scope_id in self._source_scopes:
                raise MoneyAccountingError("one monetary source scope cannot be counted more than once")
            self._validate_allocation_totals(pending=receipt)
            policy_attestation = None
            binding = receipt.allocation_method
            if binding is not None:
                if (binding.registration_ref != self.roster.registration_ref
                        or binding.registration_sha256 != self.roster.registration_sha256):
                    raise MoneyAccountingError("allocation method binding differs from the frozen cohort registration")
            self._verifying = True
            try:
                if binding is not None:
                    policy_attestation = self._verify_policy(binding)
                attestation = self._source_verifier.verify_source(receipt)
                self._validate_source_attestation(receipt, attestation)
            finally:
                self._verifying = False
            self._receipts[key] = (receipt, attestation)
            self._source_scopes.add(evidence.source_scope_id)
            if binding is not None and policy_attestation is not None:
                self._policy_attestations[binding.sha256] = policy_attestation

    def _verify_policy(self, binding: AllocationMethodBinding) -> AllocationPolicyAttestation | None:
        cached = self._policy_attestations.get(binding.sha256)
        if cached is not None:
            return None
        if self._policy_verifier is None:
            raise MoneyAccountingError("a separate verifier is required for the registered allocation method")
        attestation = self._policy_verifier.verify_registered_method(binding)
        if not isinstance(attestation, AllocationPolicyAttestation) or attestation.policy_sha256 != binding.sha256:
            raise MoneyAccountingError("allocation verifier did not bind the exact registered method")
        _identifier(attestation.verifier_id, "allocation policy verifier id")
        _timestamp(attestation.verified_at, "allocation policy verification time")
        return attestation

    def _validate_source_attestation(self, receipt: MoneyReceipt, attestation: SourceAttestation) -> None:
        if not isinstance(attestation, SourceAttestation) or attestation.receipt_sha256 != receipt.sha256:
            raise MoneyAccountingError("source verifier did not bind the exact monetary receipt")
        _identifier(attestation.verifier_id, "source verifier id")
        if _timestamp(attestation.verified_at, "source verification time") < _timestamp(
            receipt.observed_at, "receipt observation"
        ):
            raise MoneyAccountingError("source verification predates the receipt observation")

    def _validate_allocation_totals(self, *, pending: MoneyReceipt | None = None) -> None:
        groups: dict[tuple[str, str, str, str, str, str], tuple[Fraction, Fraction]] = {}
        receipts = [item[0] for item in self._receipts.values()]
        if pending is not None:
            receipts.append(pending)
        for receipt in receipts:
            if receipt.measure != "allocatedSubscriptionCostEur" or receipt.allocation_method is None:
                continue
            assert receipt.allocation_share is not None
            key = (
                receipt.evidence.account_sha256, receipt.evidence.source_ref,
                receipt.evidence.source_sha256, receipt.allocation_method.sha256,
                receipt.evidence.coverage_period_id, receipt.allocation_method.denominator_id,
            )
            try:
                share_numerator = Fraction(receipt.allocation_share.numerator)
                share_denominator = Fraction(receipt.allocation_share.denominator)
                numerator, denominator = groups.get(key, (Fraction(0), share_denominator))
                if denominator != share_denominator:
                    raise MoneyAccountingError("allocation denominator changed within one account/source/method/period")
                numerator += share_numerator
                if numerator > denominator:
                    raise MoneyAccountingError("cohort allocation numerators exceed their registered denominator")
                groups[key] = (numerator, denominator)
            except (ArithmeticError, OverflowError, ValueError) as exc:
                if isinstance(exc, MoneyAccountingError):
                    raise
                raise MoneyAccountingError("allocation share aggregation is outside bounded arithmetic") from exc

    def summarize(self) -> MoneySummary:
        with self._lock:
            self.roster.validate()
            missing_required: list[tuple[str, str]] = []
            missing_full: list[tuple[str, str]] = []
            totals: dict[str, Decimal | None] = {}
            known_actual: list[Decimal] = []
            actual_complete = True
            allocated_complete = True
            for measure in MEASURES:
                activities = [
                    activity for activity in self.roster.activities
                    if activity.kind in _MEASURE_ACTIVITY_KINDS[measure]
                ]
                values: list[Decimal] = []
                complete_measure = True
                for activity in activities:
                    item = self._receipts.get((activity.activity_id, measure))
                    amount = item[0].amount_eur if item is not None else None
                    if amount is None:
                        complete_measure = False
                        if measure in self.roster.required_measures:
                            missing_required.append((activity.activity_id, measure))
                        if measure in {"actualAdditionalSpendEur", "allocatedSubscriptionCostEur"}:
                            missing_full.append((activity.activity_id, measure))
                    else:
                        values.append(amount)
                        if measure == "actualAdditionalSpendEur":
                            known_actual.append(amount)
                if measure == "actualAdditionalSpendEur":
                    actual_complete = complete_measure
                elif measure == "allocatedSubscriptionCostEur":
                    allocated_complete = complete_measure
                if complete_measure:
                    try:
                        total = _exact_decimal_sum(values, "monetary aggregate")
                    except (DecimalException, OverflowError, ArithmeticError) as exc:
                        if isinstance(exc, MoneyAccountingError):
                            raise
                        raise MoneyAccountingError("monetary aggregate overflow") from exc
                    totals[measure] = total
                else:
                    totals[measure] = None
            actual_total = totals["actualAdditionalSpendEur"]
            try:
                observed_subtotal = (
                    _exact_decimal_sum(known_actual, "observed additional-spend subtotal")
                    if known_actual else None
                )
            except (DecimalException, OverflowError, ArithmeticError) as exc:
                if isinstance(exc, MoneyAccountingError):
                    raise
                raise MoneyAccountingError("observed additional-spend subtotal overflow") from exc
            cap = self.roster.actual_additional_spend_cap_eur
            if any(amount > cap for amount in known_actual):
                cap_violation: bool | None = True
            elif actual_complete:
                cap_violation = False
            else:
                cap_violation = None
            required_complete = actual_complete
            # The present registration does not resolve reviewer-payment
            # applicability or represent the separate human-cost fields.
            full_economic_complete = False
            receipts = sorted((item[0].sha256 for item in self._receipts.values()))
            return MoneySummary(
                actual_additional_spend_eur=actual_total,
                observed_additional_spend_subtotal_eur=observed_subtotal,
                actual_additional_spend_cap_eur=cap,
                cap_violation=cap_violation,
                stop_required=(not required_complete or cap_violation is not False),
                allocated_subscription_cost_eur=totals["allocatedSubscriptionCostEur"],
                api_reference_estimate_eur=totals["apiReferenceEstimateEur"],
                required_measures_complete=required_complete,
                full_economic_cost_complete=full_economic_complete,
                full_economic_cost_status="pending-registered-cost-scope-and-human-cost-fields",
                missing_required=tuple(missing_required),
                missing_full_economic_cost=tuple(missing_full),
                registration_sha256=self.roster.registration_sha256,
                roster_sha256=self.roster.sha256,
                receipt_sha256s=tuple(receipts),
            )
