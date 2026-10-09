# SPDX-License-Identifier: AGPL-3.0-only
"""Prospective, registration-bound completion for SPEC-044 T006 cost scope.

This layer composes the existing attempt cost assessment and experimental
monetary ledger with authenticated human-time records and an externally
verified approved scope. It records observed time without assigning an hourly
price. Draft or missing scope, missing evidence, incomplete slots, or
unverified allocation can never be promoted to complete.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
from typing import Mapping, Protocol

from . import tooling_evaluation as evaluation
from .tooling_money import MoneyLedger, MoneyRoster, MoneySummary

_SCOPE_SCHEMA = "agent-braid-m45-full-cost-scope-v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_MAX_TIME_RECEIPTS = 512
_MAX_WALL_RECEIPTS = 109


class FullCostError(ValueError):
    """A full-cost policy, time receipt, or approval binding is invalid."""


def _identifier(value: object, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise FullCostError(f"{label} must be a bounded identifier")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise FullCostError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _canonical_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _utc(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise FullCostError(f"{label} must be an explicit UTC timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise FullCostError(f"{label} must be an explicit UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise FullCostError(f"{label} must be an explicit UTC timestamp")
    return parsed.astimezone(timezone.utc)


def _microseconds(value: datetime) -> int:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = value - epoch
    return (delta.days * 86_400 + delta.seconds) * 1_000_000 + delta.microseconds


@dataclass(frozen=True)
class FullCostScope:
    """Approved prospective policy embedded in the frozen registration.

    Fee applicability must be explicitly registered for both named reviewers.
    The allocation method is a registered identity; separate external
    attestations authenticate the approved scope and the method evidence.
    """

    registration_sha256: str
    scope_id: str
    scope_sha256: str
    approval_record_id: str
    approval_record_sha256: str
    user_time_participant_id: str
    reviewer_fee_applicability: tuple[tuple[str, str], ...]
    method_id: str
    method_ref: str
    method_sha256: str
    denominator_id: str
    unit: str

    @classmethod
    def from_registration(
        cls, registration: evaluation.ValidatedRegistration,
    ) -> "FullCostScope | None":
        evaluation._require_validated(registration)
        raw = registration.data.get("fullCostScope")
        if raw is None:
            return None
        if not isinstance(raw, Mapping):
            raise FullCostError("fullCostScope must be an object")
        if set(raw) != {"schema", "status", "scopeId", "approval", "reviewerFees",
                        "subscriptionAllocation", "humanTime"}:
            raise FullCostError("fullCostScope contains missing or unsupported fields")
        if raw.get("schema") != _SCOPE_SCHEMA:
            raise FullCostError("unsupported full-cost scope schema")
        if raw.get("status") != "approved":
            return None
        approval = raw.get("approval")
        if not isinstance(approval, Mapping) or approval.get("status") != "approved":
            return None
        if set(approval) != {"status", "recordId", "sha256"}:
            raise FullCostError("full-cost approval record contains unsupported fields")
        approval_id = _identifier(approval.get("recordId"), "full-cost approval record id")
        approval_sha = _digest(approval.get("sha256"), "full-cost approval record hash")
        method = raw.get("subscriptionAllocation")
        if not isinstance(method, Mapping):
            raise FullCostError("approved full-cost scope must bind subscription allocation")
        if set(method) != {"activityKinds", "reviewerApplicability", "methodId", "methodRef",
                           "methodSha256", "denominatorId", "unit"}:
            raise FullCostError("subscription allocation scope contains missing or unsupported fields")
        if method.get("activityKinds") != ["setup", "attempt"]:
            raise FullCostError("subscription allocation must cover setup and every attempt")
        if method.get("reviewerApplicability") != "not-applicable":
            raise FullCostError("reviewer subscription allocation applicability must be explicit")
        fee_rows = raw.get("reviewerFees")
        if not isinstance(fee_rows, list):
            raise FullCostError("reviewer fee applicability must be registered")
        expected_reviewers = {row["reviewerId"] for row in registration.data["humanReviewers"]}
        fees: dict[str, str] = {}
        for row in fee_rows:
            if not isinstance(row, Mapping):
                raise FullCostError("reviewer fee scope rows must be objects")
            if set(row) != {"reviewerId", "applicability"}:
                raise FullCostError("reviewer fee scope rows contain missing or unsupported fields")
            reviewer_id = _identifier(row.get("reviewerId"), "reviewer id")
            applicability = row.get("applicability")
            if applicability == "unknown":
                return None
            if applicability not in {"paid", "unpaid"}:
                raise FullCostError("reviewer fee applicability must be explicitly paid or unpaid")
            if reviewer_id in fees:
                raise FullCostError("reviewer fee scope contains duplicate reviewer ids")
            fees[reviewer_id] = applicability
        if set(fees) != expected_reviewers:
            raise FullCostError("reviewer fee scope must equal the registered reviewer roster")
        time_scope = raw.get("humanTime")
        if not isinstance(time_scope, Mapping):
            raise FullCostError("human time applicability must be registered")
        if set(time_scope) != {"userParticipantId", "userActivityKinds", "reviewerActivityKinds", "intervalSemantics"}:
            raise FullCostError("human-time scope contains missing or unsupported fields")
        if time_scope.get("userActivityKinds") != ["setup", "attempt"]:
            raise FullCostError("user time scope must cover setup and all attempts")
        if time_scope.get("reviewerActivityKinds") != ["attempt"]:
            raise FullCostError("reviewer time scope must cover all attempts")
        if time_scope.get("intervalSemantics") != "verified-active-work-only":
            raise FullCostError("human time must use approved active-work-only intervals")
        return cls(
            registration_sha256=registration.sha256,
            scope_id=_identifier(raw.get("scopeId"), "full-cost scope id"),
            scope_sha256=_canonical_sha256(raw),
            approval_record_id=approval_id,
            approval_record_sha256=approval_sha,
            user_time_participant_id=_identifier(
                time_scope.get("userParticipantId"), "user-time participant id"
            ),
            reviewer_fee_applicability=tuple(sorted(fees.items())),
            method_id=_identifier(method.get("methodId"), "allocation method id"),
            method_ref=_identifier(method.get("methodRef"), "allocation method reference"),
            method_sha256=_digest(method.get("methodSha256"), "allocation method hash"),
            denominator_id=_identifier(method.get("denominatorId"), "allocation denominator id"),
            unit=_identifier(method.get("unit"), "allocation unit"),
        )


@dataclass(frozen=True)
class ScopeApprovalAttestation:
    verifier_id: str
    registration_sha256: str
    roster_sha256: str
    scope_sha256: str
    approval_record_id: str
    approval_record_sha256: str
    verified_at: str


class FullCostScopeVerifier(Protocol):
    """Authenticates actual owner approval and the exact prospective scope."""

    def verify_scope(
        self, scope: FullCostScope, registration_sha256: str, roster_sha256: str,
    ) -> ScopeApprovalAttestation: ...


@dataclass(frozen=True)
class HumanTimeReceipt:
    """Observed active-work interval bound to one or more registered activities."""

    participant_id: str
    activity_ids: tuple[str, ...]
    started_at: str
    ended_at: str
    source_ref: str
    source_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.participant_id, "human-time participant id")
        if (not isinstance(self.activity_ids, tuple) or not self.activity_ids
                or len(self.activity_ids) > 109 or len(set(self.activity_ids)) != len(self.activity_ids)):
            raise FullCostError("human-time interval must bind a bounded unique activity set")
        for activity_id in self.activity_ids:
            _identifier(activity_id, "human-time activity id")
        _identifier(self.source_ref, "human-time source reference")
        _digest(self.source_sha256, "human-time source hash")
        start, end = _utc(self.started_at, "human-time start"), _utc(self.ended_at, "human-time end")
        if start >= end:
            raise FullCostError("human-time interval must have positive duration")

    def as_dict(self) -> dict[str, str]:
        return {
            "participantId": self.participant_id, "activityIds": list(self.activity_ids),
            "startedAt": self.started_at, "endedAt": self.ended_at,
            "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
        }

    @property
    def sha256(self) -> str:
        return _canonical_sha256(self.as_dict())


@dataclass(frozen=True)
class HumanTimeAttestation:
    verifier_id: str
    receipt_sha256: str
    verified_at: str


class HumanTimeVerifier(Protocol):
    """Authenticates each interval against its retained observation source."""

    def verify_human_time(self, receipt: HumanTimeReceipt) -> HumanTimeAttestation: ...


@dataclass(frozen=True)
class StudyWallIntervalReceipt:
    """Authenticated setup/attempt elapsed interval from a retained clock source."""

    activity_id: str
    started_at: str
    ended_at: str
    source_ref: str
    source_sha256: str

    def __post_init__(self) -> None:
        _identifier(self.activity_id, "study-wall activity id")
        _identifier(self.source_ref, "study-wall source reference")
        _digest(self.source_sha256, "study-wall source hash")
        if _utc(self.started_at, "study-wall start") >= _utc(self.ended_at, "study-wall end"):
            raise FullCostError("study-wall interval must have positive duration")

    @property
    def sha256(self) -> str:
        return _canonical_sha256({"activityId": self.activity_id, "startedAt": self.started_at,
                                 "endedAt": self.ended_at, "sourceRef": self.source_ref,
                                 "sourceSha256": self.source_sha256})


@dataclass(frozen=True)
class StudyWallAttestation:
    verifier_id: str
    receipt_sha256: str
    verified_at: str


class StudyWallVerifier(Protocol):
    def verify_study_wall(self, receipt: StudyWallIntervalReceipt) -> StudyWallAttestation: ...


def complete_full_cost(
    registration: evaluation.ValidatedRegistration,
    ledger: evaluation.EvaluationLedger,
    roster: MoneyRoster,
    money_ledger: MoneyLedger,
    money_summary: MoneySummary,
    *,
    setup_costs: Mapping[str, object] | None,
    human_time_receipts: tuple[HumanTimeReceipt, ...] | None,
    scope_verifier: FullCostScopeVerifier | None,
    time_verifier: HumanTimeVerifier | None,
    study_wall_receipts: tuple[StudyWallIntervalReceipt, ...] | None = None,
    study_wall_verifier: StudyWallVerifier | None = None,
) -> MoneySummary:
    """Return an upgraded immutable summary only when the full contract clears.

    This does not run capture or infer money/time. The registration scope must
    have a separate approval attestation bound to its final registration hash,
    exact monetary roster, and scope hash; no self-referential hash is needed.
    """
    evaluation._require_validated(registration)
    evaluation.validate_ledger(ledger, registration)
    roster.validate()
    if roster.registration_sha256 != registration.sha256:
        raise FullCostError("monetary roster belongs to a different registration")
    if money_ledger.roster.sha256 != roster.sha256 or money_summary.roster_sha256 != roster.sha256:
        raise FullCostError("money ledger or summary belongs to a different frozen roster")
    if money_summary.registration_sha256 != registration.sha256:
        raise FullCostError("money summary belongs to a different registration")
    if money_summary != money_ledger.summarize():
        raise FullCostError("money summary does not match the verified ledger receipt state")
    expected_money_hashes = tuple(sorted(receipt.sha256 for receipt, _ in money_ledger.history))
    if money_summary.receipt_sha256s != expected_money_hashes:
        raise FullCostError("money summary does not bind the complete verified receipt history")
    scope = FullCostScope.from_registration(registration)
    if scope is None:
        return replace(money_summary, full_economic_cost_complete=False,
                       full_economic_cost_status="pending-full-cost-scope-approval",
                       missing_full_economic_cost=tuple(sorted(
                           set(money_summary.missing_full_economic_cost)
                           | {("registration", "fullCostScope")}
                       )),
                       human_time_seconds=None, human_time_receipt_sha256s=(), study_wall_seconds=None)
    if scope_verifier is None or time_verifier is None or study_wall_verifier is None:
        return replace(money_summary, full_economic_cost_complete=False,
                       full_economic_cost_status="pending-external-scope-or-time-verification",
                       missing_full_economic_cost=tuple(sorted(
                           set(money_summary.missing_full_economic_cost)
                           | ({("scope", "approvalVerification")} if scope_verifier is None else set())
                           | ({("humanTime", "sourceVerification")} if time_verifier is None else set())
                           | ({("studyWall", "sourceVerification")} if study_wall_verifier is None else set())
                       )),
                       human_time_seconds=None, human_time_receipt_sha256s=())

    reasons: list[tuple[str, str]] = []
    scope_attestation = scope_verifier.verify_scope(scope, registration.sha256, roster.sha256)
    _validate_scope_attestation(scope, roster, scope_attestation)

    activity_by_id = roster.activity_by_id
    attempts = [slot.slot_id for slot in evaluation.generate_slots(registration)]
    if len(attempts) != 108 or set(attempts) != {item.activity_id for item in roster.activities if item.kind == "attempt"}:
        raise FullCostError("money roster does not preserve the exact 108 registered attempts")
    incomplete_slots = [slot_id for slot_id in attempts
                        if ledger.current_status(slot_id) not in evaluation.FINAL_STATUSES]
    if incomplete_slots:
        reasons.extend((slot_id, "attemptOutcome") for slot_id in incomplete_slots)

    for field in evaluation.COST_FIELDS:
        if money_summary.required_measures_complete is not True:
            reasons.append(("registration-costs", field))
            break
    cost_assessment = evaluation.assess_cost_completeness(ledger, setup_costs=setup_costs)
    if not cost_assessment.complete:
        reasons.extend(("registration-costs", field) for field in cost_assessment.missing)
    if money_summary.actual_additional_spend_eur is None or money_summary.cap_violation is not False or money_summary.stop_required:
        reasons.append(("study-cash", "actual-spend-or-cap"))

    expected_allocations = {item.activity_id for item in roster.activities
                            if item.kind in {"setup", "attempt"}}
    allocated = {
        receipt.activity_id: receipt
        for receipt, _attestation in money_ledger.history
        if receipt.measure == "allocatedSubscriptionCostEur"
    }
    verified_methods = {attestation.policy_sha256
                        for attestation in money_ledger.verified_allocation_policy_attestations}
    if set(allocated) != expected_allocations or money_summary.allocated_subscription_cost_eur is None:
        reasons.extend((activity_id, "allocatedSubscriptionCostEur")
                       for activity_id in sorted(expected_allocations - set(allocated)))
        if not reasons:
            reasons.append(("subscription-allocation", "incomplete-or-unknown"))
    for activity_id, receipt in allocated.items():
        binding = receipt.allocation_method
        if binding is None or (
            binding.registration_ref != roster.registration_ref
            or binding.registration_sha256 != registration.sha256
            or binding.method_id != scope.method_id
            or binding.method_ref != scope.method_ref
            or binding.method_sha256 != scope.method_sha256
            or binding.denominator_id != scope.denominator_id
            or binding.unit != scope.unit
            or binding.sha256 not in verified_methods
        ):
            reasons.append((activity_id, "allocation-method-approval"))

    expected_time_rows = _expected_time_rows(scope, roster)
    actual_time_rows: dict[tuple[str, str], HumanTimeReceipt] = {}
    if human_time_receipts is None:
        human_time_receipts = ()
    elif not isinstance(human_time_receipts, tuple):
        raise FullCostError("human-time receipts must be an immutable tuple or unavailable")
    if len(human_time_receipts) > _MAX_TIME_RECEIPTS:
        raise FullCostError("human-time receipt count exceeds the bounded scope")
    for receipt in human_time_receipts:
        if not isinstance(receipt, HumanTimeReceipt):
            raise FullCostError("human-time evidence must use typed receipts")
        activity_ids = set(receipt.activity_ids)
        keys = {(receipt.participant_id, item) for item in activity_ids}
        if keys & set(actual_time_rows):
            raise FullCostError("human-time participant/activity coverage is duplicated")
        if not keys <= expected_time_rows:
            raise FullCostError("human-time receipt is outside the approved participant/activity scope")
        start, end = _utc(receipt.started_at, "human-time start"), _utc(receipt.ended_at, "human-time end")
        if start < _utc(roster.period_started_at, "cohort start") or end > _utc(
            roster.period_ended_at, "cohort end"
        ):
            raise FullCostError("human-time receipt is outside the frozen cohort period")
        for activity_id in activity_ids:
            activity = activity_by_id.get(activity_id)
            if activity is None:
                raise FullCostError("human-time receipt references unknown activity")
        attestation = time_verifier.verify_human_time(receipt)
        _validate_time_attestation(receipt, attestation)
        for key in keys:
            actual_time_rows[key] = receipt
    missing_time = expected_time_rows - set(actual_time_rows)
    reasons.extend((activity_id, f"humanTime:{participant_id}")
                   for participant_id, activity_id in sorted(missing_time))
    distinct_time_receipts = {item.sha256: item for item in actual_time_rows.values()}
    wall_seconds = _study_wall_total(
        registration, roster, tuple(study_wall_receipts or ()), study_wall_verifier,
        tuple(distinct_time_receipts.values()), reasons,
    )
    cap_totals = dict(cost_assessment.totals)
    # Legacy EUR may already contain actual spend. Do not add it again.
    # The subscription accounting boundary is provider cash + prepaid allocation;
    # reference-price estimates and reviewer cash are separate measures.
    provider_total = money_summary.provider_accounting_cost_eur
    cap_totals["eur"] = float(provider_total) if provider_total is not None else None
    cap_totals["wall_seconds"] = float(wall_seconds) if wall_seconds is not None else None
    cap_assessment = evaluation.check_cost_caps(registration, cap_totals)
    exact_provider_cap_exceeded = (provider_total is not None and provider_total > Decimal(str(
        registration.data["costCaps"]["eur"])))
    if exact_provider_cap_exceeded:
        reasons.append(("numeric-stop", "provider accounting EUR cap exceeded"))
    if cap_assessment.stop:
        reasons.extend(("numeric-stop", reason) for reason in cap_assessment.reasons)
    human_microseconds_by_participant = _human_time_union(distinct_time_receipts.values())
    reviewers = {reviewer_id for reviewer_id, _ in scope.reviewer_fee_applicability}
    participant_seconds = {
        participant_id: _seconds_from_microseconds(microseconds)
        for participant_id, microseconds in human_microseconds_by_participant.items()
    }
    user_rows_missing = any(participant_id == scope.user_time_participant_id
                            for participant_id, _ in missing_time)
    reviewer_rows_missing = any(participant_id in reviewers
                                for participant_id, _ in missing_time)
    user_seconds = (participant_seconds.get(scope.user_time_participant_id, Decimal(0))
                    if not user_rows_missing else None)
    reviewer_seconds = (_seconds_from_microseconds(sum(
                            human_microseconds_by_participant.get(item, 0) for item in reviewers
                        ))
                        if not reviewer_rows_missing else None)
    human_seconds = (_seconds_from_microseconds(sum(human_microseconds_by_participant.values()))
                     if not missing_time else None)
    complete = not reasons and cost_assessment.complete
    return replace(
        money_summary,
        full_economic_cost_complete=complete,
        full_economic_cost_status="complete" if complete else "incomplete-registered-cost-scope",
        stop_required=(money_summary.stop_required or cap_assessment.stop
                       or exact_provider_cap_exceeded),
        missing_full_economic_cost=tuple(sorted(set(money_summary.missing_full_economic_cost) | set(reasons))),
        human_time_seconds=human_seconds,
        user_time_seconds=user_seconds,
        reviewer_time_seconds=reviewer_seconds,
        human_time_receipt_sha256s=tuple(sorted(distinct_time_receipts)),
        study_wall_seconds=wall_seconds,
    )


def _expected_time_rows(scope: FullCostScope, roster: MoneyRoster) -> set[tuple[str, str]]:
    by_kind = {
        kind: {item.activity_id for item in roster.activities if item.kind == kind}
        for kind in {"setup", "attempt"}
    }
    if len(by_kind["attempt"]) != 108 or len(by_kind["setup"]) != 1:
        raise FullCostError("human-time scope requires the full registered roster")
    expected = {(scope.user_time_participant_id, activity_id)
                for kind in ("setup", "attempt") for activity_id in by_kind[kind]}
    reviewer_ids = {reviewer_id for reviewer_id, _ in scope.reviewer_fee_applicability}
    if scope.user_time_participant_id in reviewer_ids:
        raise FullCostError("user-time participant must be distinct from registered reviewers")
    expected.update((reviewer_id, activity_id)
                    for reviewer_id in reviewer_ids for activity_id in by_kind["attempt"])
    return expected


def _study_wall_total(registration, roster, receipts, verifier, human_receipts, reasons):
    expected = {item.activity_id for item in roster.activities if item.kind in {"setup", "attempt"}}
    if len(expected) != 109:
        raise FullCostError("study-wall scope requires one setup and all 108 attempts")
    if verifier is None or receipts is None:
        reasons.append(("studyWall", "sourceVerification"))
        return None
    if not isinstance(receipts, tuple) or len(receipts) > _MAX_WALL_RECEIPTS:
        raise FullCostError("study-wall receipts must be a bounded immutable tuple")
    by_activity = {}
    cohort_start = _utc(roster.period_started_at, "cohort start")
    cohort_end = _utc(roster.period_ended_at, "cohort end")
    for receipt in receipts:
        if not isinstance(receipt, StudyWallIntervalReceipt):
            raise FullCostError("study-wall evidence must use typed receipts")
        if receipt.activity_id not in expected or receipt.activity_id in by_activity:
            raise FullCostError("study-wall activity coverage is duplicate or out of scope")
        start, end = _utc(receipt.started_at, "study-wall start"), _utc(receipt.ended_at, "study-wall end")
        if start < cohort_start or end > cohort_end:
            raise FullCostError("study-wall receipt is outside the frozen cohort period")
        attestation = verifier.verify_study_wall(receipt)
        if (not isinstance(attestation, StudyWallAttestation)
                or attestation.receipt_sha256 != receipt.sha256):
            raise FullCostError("study-wall verifier did not bind the exact interval receipt")
        _identifier(attestation.verifier_id, "study-wall verifier id")
        if _utc(attestation.verified_at, "study-wall verification timestamp") < end:
            raise FullCostError("study-wall verification predates its observation")
        by_activity[receipt.activity_id] = receipt
    if set(by_activity) != expected:
        reasons.extend((activity_id, "studyWall:interval") for activity_id in sorted(expected - set(by_activity)))
        return None
    spans = [(_microseconds(_utc(item.started_at, "study-wall start")),
              _microseconds(_utc(item.ended_at, "study-wall end"))) for item in by_activity.values()]
    spans.extend((_microseconds(_utc(item.started_at, "human-time start")),
                  _microseconds(_utc(item.ended_at, "human-time end"))) for item in human_receipts)
    return _seconds_from_microseconds(_union_duration(spans))


def _validate_scope_attestation(
    scope: FullCostScope, roster: MoneyRoster, attestation: ScopeApprovalAttestation,
) -> None:
    if not isinstance(attestation, ScopeApprovalAttestation):
        raise FullCostError("scope verifier did not return an authenticated approval attestation")
    if (attestation.registration_sha256 != scope.registration_sha256
            or attestation.roster_sha256 != roster.sha256
            or attestation.scope_sha256 != scope.scope_sha256
            or attestation.approval_record_id != scope.approval_record_id
            or attestation.approval_record_sha256 != scope.approval_record_sha256):
        raise FullCostError("scope approval attestation does not bind the exact registration and roster")
    _identifier(attestation.verifier_id, "scope verifier id")
    _utc(attestation.verified_at, "scope verification timestamp")


def _validate_time_attestation(receipt: HumanTimeReceipt, attestation: HumanTimeAttestation) -> None:
    if not isinstance(attestation, HumanTimeAttestation) or attestation.receipt_sha256 != receipt.sha256:
        raise FullCostError("human-time verifier did not bind the exact interval receipt")
    _identifier(attestation.verifier_id, "human-time verifier id")
    if _utc(attestation.verified_at, "human-time verification timestamp") < _utc(
        receipt.ended_at, "human-time end"
    ):
        raise FullCostError("human-time verification predates its observation")


def _human_time_union(receipts) -> dict[str, int]:
    grouped: dict[str, list[tuple[int, int]]] = {}
    for receipt in receipts:
        grouped.setdefault(receipt.participant_id, []).append((
            _microseconds(_utc(receipt.started_at, "human-time start")),
            _microseconds(_utc(receipt.ended_at, "human-time end")),
        ))
    return {participant_id: _union_duration(spans) for participant_id, spans in grouped.items()}


def _union_duration(spans: list[tuple[int, int]]) -> int:
    if not spans:
        return 0
    spans.sort()
    total = 0
    start, end = spans[0]
    for next_start, next_end in spans[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def _seconds_from_microseconds(microseconds: int) -> Decimal:
    return Decimal(f"{microseconds // 1_000_000}.{microseconds % 1_000_000:06d}")
