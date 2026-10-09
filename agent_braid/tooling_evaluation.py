# SPDX-License-Identifier: AGPL-3.0-only
"""Offline preparation and accounting helpers for the prospective M4.5 study.

This module validates declared registration data and accounts for a fixed
attempt roster. It never launches a host, provider, tool, fixture, or experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import math
import re
from typing import Any, Mapping, Sequence

from .tooling_subscription import SubscriptionError, policy_sha256 as _subscription_policy_sha256
from . import tooling_model_identity as model_identity_policy


REGISTRATION_SCHEMA = "agent-braid-m45-registration-v1"
REGISTRATION_SCHEMA_V2 = "agent-braid-m45-registration-v2"
LEDGER_SCHEMA = "agent-braid-m45-ledger-v1"
HOSTS = ("codex", "claude-code")
ARMS = ("cli", "mcp-only", "mcp-plus-skills")
JOURNEY_CLASSES = (
    "analyze-interactions",
    "prepare-advisory-plan",
    "refuse-missing-grant",
    "execute-granted-batch-verify",
    "inspect-recover-interruption",
    "export-evidence",
)
COST_FIELDS = (
    "eur", "tokens", "input_tokens", "output_tokens", "retry_tokens",
    "wall_seconds", "rss_bytes", "disk_bytes",
)
CAP_FIELDS = ("eur", "tokens", "wall_seconds", "rss_bytes", "disk_bytes")
SLOT_STATUSES = (
    "not-started",
    "attempted",
    "valid",
    "invalid",
    "refused",
    "cancelled",
    "recovered",
    "failed",
)
FINAL_STATUSES = frozenset(SLOT_STATUSES[2:])
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")


class EvaluationError(ValueError):
    """Registration, roster, ledger, cost, or rating data is invalid."""


@dataclass(frozen=True)
class ValidatedRegistration:
    """A structurally valid frozen registration; this is not capture approval."""

    data: Mapping[str, Any]
    sha256: str


@dataclass(frozen=True)
class AttemptSlot:
    slot_id: str
    host: str
    arm: str
    journey_class: str
    fixture_id: str
    fixture_sha256: str
    prompt_id: str
    prompt_sha256: str
    order_position: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "slotId": self.slot_id,
            "host": self.host,
            "arm": self.arm,
            "journeyClass": self.journey_class,
            "fixtureId": self.fixture_id,
            "fixtureSha256": self.fixture_sha256,
            "promptId": self.prompt_id,
            "promptSha256": self.prompt_sha256,
            "orderPosition": self.order_position,
        }


@dataclass(frozen=True)
class LedgerEvent:
    sequence: int
    slot_id: str
    status: str
    attempt_id: str | None
    data: Mapping[str, Any]
    data_sha256: str


@dataclass(frozen=True)
class EvaluationLedger:
    registration_sha256: str
    slots: tuple[AttemptSlot, ...]
    events: tuple[LedgerEvent, ...] = ()

    def current_status(self, slot_id: str) -> str:
        _find_slot(self, slot_id)
        for event in reversed(self.events):
            if event.slot_id == slot_id:
                return event.status
        return "not-started"

    def current_event(self, slot_id: str) -> LedgerEvent | None:
        _find_slot(self, slot_id)
        for event in reversed(self.events):
            if event.slot_id == slot_id:
                return event
        return None

    def as_dict(self) -> dict[str, Any]:
        """Serialize the complete event history and every intended slot."""

        _validate_ledger_history(self)
        return {
            "schemaVersion": LEDGER_SCHEMA,
            "registrationSha256": self.registration_sha256,
            "slots": [
                {**slot.as_dict(), "currentStatus": self.current_status(slot.slot_id)}
                for slot in self.slots
            ],
            "events": [
                {
                    "sequence": event.sequence,
                    "slotId": event.slot_id,
                    "status": event.status,
                    "attemptId": event.attempt_id,
                    "data": dict(event.data),
                    "dataSha256": event.data_sha256,
                }
                for event in self.events
            ],
        }


@dataclass(frozen=True)
class CostAssessment:
    complete: bool
    missing: tuple[str, ...]
    totals: Mapping[str, int | float | None]


@dataclass(frozen=True)
class CapAssessment:
    within_caps: bool
    stop: bool
    reasons: tuple[str, ...]
    observed: Mapping[str, int | float | None]


@dataclass(frozen=True)
class UtilityEligibility:
    positive_claim_eligible: bool
    reasons: tuple[str, ...]
    denominators: Mapping[str, Any]
    cost_assessment: CostAssessment
    cap_assessment: CapAssessment
    human_scoring_complete: bool
    authority_correct_by_host_arm_c: Mapping[str, int]
    successful_by_host_arm_c: Mapping[str, int]


def validate_registration(
    registration: Mapping[str, Any],
    *,
    expected_candidate_sha256: str,
    expected_input_hashes: Mapping[str, str],
) -> ValidatedRegistration:
    """Validate a complete frozen registration against caller-supplied hashes.

    The function checks declared approval and source-right records for required
    fields but cannot authenticate people, rights, provider opt-in, or capture
    authorization. It performs no filesystem, host, provider, or network work.
    """

    if not isinstance(registration, Mapping):
        raise EvaluationError("registration must be a JSON object")
    data = _json_copy(registration, "registration")
    schema_version = data.get("schemaVersion")
    if schema_version not in {REGISTRATION_SCHEMA, REGISTRATION_SCHEMA_V2}:
        raise EvaluationError("unsupported or missing registration schemaVersion")
    _require_id(data.get("registrationId"), "registrationId")
    if data.get("status") != "approved":
        raise EvaluationError("registration status must be approved before capture admission")
    _validate_record(data.get("ownerApproval"), "ownerApproval", "approved")

    expected_candidate_sha256 = _require_hash(expected_candidate_sha256, "expected candidate SHA-256")
    candidate = data.get("candidate")
    _require_object(candidate, "candidate")
    _require_git_commit(candidate.get("commit"), "candidate.commit")
    _require_hash(candidate.get("sha256"), "candidate.sha256")
    _require_text(candidate.get("version"), "candidate.version")
    if candidate["sha256"] != expected_candidate_sha256:
        raise EvaluationError("candidate SHA-256 does not match the frozen candidate")

    _validate_record(data.get("sourceRights"), "sourceRights", "approved")
    _validate_source_rights(data.get("sourceRights"))
    _validate_provider_opt_in(data.get("provider"))
    if "billingPolicy" in data:
        _validate_billing_policy(data["billingPolicy"])
    _validate_cost_caps(data.get("costCaps"))
    _validate_reviewers(data.get("humanReviewers"))
    _validate_rubric(data.get("rubric"))

    fixtures = _validate_fixtures(data.get("fixtures"))
    prompts = _validate_prompts(data.get("prompts"))
    source_fixture_ids = set(data["sourceRights"]["fixtureIds"])
    if source_fixture_ids != {item["fixtureId"] for item in fixtures}:
        raise EvaluationError("source-rights record must cover exactly the registered fixtures")
    if {item["fixtureId"] for item in fixtures} & {item["promptId"] for item in prompts}:
        raise EvaluationError("fixture and prompt IDs must be disjoint")
    _validate_host_builds(data.get("hosts"), schema_version=schema_version,
                          billing_policy=data.get("billingPolicy"))
    _validate_cost_rates(data.get("costRates"), data["hosts"])

    if not isinstance(expected_input_hashes, Mapping):
        raise EvaluationError("expected_input_hashes must bind all 18 fixture and six prompt IDs")
    declared = {item["fixtureId"]: item["sha256"] for item in fixtures}
    declared.update({item["promptId"]: item["sha256"] for item in prompts})
    if set(expected_input_hashes) != set(declared):
        raise EvaluationError("expected input hash inventory must bind exactly 18 fixtures and six prompts")
    for input_id, expected in expected_input_hashes.items():
        _require_hash(expected, f"expected input hash {input_id}")
        if declared[input_id] != expected:
            raise EvaluationError(f"registered input SHA-256 mismatch: {input_id}")

    digest = _canonical_sha256(data)
    return ValidatedRegistration(data=data, sha256=digest)


def generate_slots(registration: ValidatedRegistration) -> tuple[AttemptSlot, ...]:
    """Generate the fixed 108-row roster without reading or executing fixtures."""

    _require_validated(registration)
    fixtures_by_class: dict[str, list[Mapping[str, str]]] = {name: [] for name in JOURNEY_CLASSES}
    for fixture in registration.data["fixtures"]:
        fixtures_by_class[fixture["journeyClass"]].append(fixture)
    prompts = {prompt["journeyClass"]: prompt for prompt in registration.data["prompts"]}
    slots: list[AttemptSlot] = []
    for host in HOSTS:
        for journey_class in JOURNEY_CLASSES:
            prompt = prompts[journey_class]
            fixtures = sorted(fixtures_by_class[journey_class], key=lambda item: item["fixtureId"])
            for fixture_index, fixture in enumerate(fixtures):
                for position, arm_index in enumerate(
                    ((fixture_index + offset) % len(ARMS) for offset in range(len(ARMS))),
                    start=1,
                ):
                    arm = ARMS[arm_index]
                    slot_id = ":".join((host, journey_class, fixture["fixtureId"], arm))
                    slots.append(
                        AttemptSlot(
                            slot_id=slot_id,
                            host=host,
                            arm=arm,
                            journey_class=journey_class,
                            fixture_id=fixture["fixtureId"],
                            fixture_sha256=fixture["sha256"],
                            prompt_id=prompt["promptId"],
                            prompt_sha256=prompt["sha256"],
                            order_position=position,
                        )
                    )
    if len(slots) != 108 or len({slot.slot_id for slot in slots}) != 108:
        raise EvaluationError("registered design did not produce exactly 108 unique slots")
    return tuple(slots)


def new_ledger(registration: ValidatedRegistration) -> EvaluationLedger:
    """Create all intended slots in not-started state; no attempt is performed."""

    return EvaluationLedger(registration.sha256, generate_slots(registration))


def append_slot_event(
    ledger: EvaluationLedger,
    slot_id: str,
    status: str,
    *,
    attempt_id: str | None = None,
    data: Mapping[str, Any] | None = None,
) -> EvaluationLedger:
    """Append one status event after validating the existing ledger history."""

    _validate_ledger_history(ledger)
    return _append_slot_event_unchecked(
        ledger, slot_id, status, attempt_id=attempt_id, data=data,
    )


def _append_slot_event_unchecked(
    ledger: EvaluationLedger,
    slot_id: str,
    status: str,
    *,
    attempt_id: str | None = None,
    data: Mapping[str, Any] | None = None,
) -> EvaluationLedger:
    """Return a ledger with one validated immutable status event appended.

    A slot can have one attempt only. `cancelled` or `failed` may later become
    `recovered` for that same attempt; a second execution attempt is refused.
    """

    slot = _find_slot(ledger, slot_id)
    if status not in SLOT_STATUSES:
        raise EvaluationError(f"unsupported slot status: {status}")
    if data is not None and not isinstance(data, Mapping):
        raise EvaluationError("ledger event data must be an object")
    payload = _json_copy(data or {}, "ledger event data")
    if not isinstance(payload, Mapping):
        raise EvaluationError("ledger event data must be an object")
    _validate_event_data(payload)
    current = ledger.current_status(slot_id)
    prior = ledger.current_event(slot_id)
    if status == "not-started":
        if current != "not-started" or prior is not None or attempt_id is not None:
            raise EvaluationError("not-started can only be recorded before an attempt")
        if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
            raise EvaluationError("not-started events require a reason")
        _require_timestamp(payload.get("sourceTimestamp"), "sourceTimestamp")
    elif status == "attempted":
        if current != "not-started":
            raise EvaluationError("slot already has an attempt; retries require a new registered cohort")
        _require_id(attempt_id, "attemptId")
        _require_timestamp(payload.get("sourceTimestamp"), "sourceTimestamp")
    elif status in FINAL_STATUSES:
        if current != "attempted" and not (status == "recovered" and current in {"cancelled", "failed"}):
            raise EvaluationError(f"invalid status transition {current} -> {status}")
        expected_attempt = prior.attempt_id if prior is not None else None
        if not attempt_id or attempt_id != expected_attempt:
            raise EvaluationError("outcome must retain the original attemptId")
        if "completion" not in payload:
            raise EvaluationError("terminal outcomes require an explicit completion value or null")
        if "authorityCorrect" not in payload:
            raise EvaluationError("terminal outcomes require explicit authorityCorrect or null")
        if "costs" not in payload:
            raise EvaluationError("terminal outcomes require explicit costs, including null unknowns")
        _require_timestamp(payload.get("sourceTimestamp"), "sourceTimestamp")
        if "completion" in payload and not _is_bool_or_none(payload["completion"]):
            raise EvaluationError("completion must be true, false, or null")
        if "authorityCorrect" in payload and not _is_bool_or_none(payload["authorityCorrect"]):
            raise EvaluationError("authorityCorrect must be true, false, or null")
        if "costs" in payload:
            _validate_observed_costs(payload["costs"])
        if status == "recovered":
            previous_costs = prior.data.get("costs") if prior is not None else None
            current_costs = payload.get("costs")
            if previous_costs is None or current_costs is None:
                raise EvaluationError("recovery must preserve its prior cumulative cost observation")
            for field in COST_FIELDS:
                previous = previous_costs[field]
                current = current_costs[field]
                if previous is not None and (current is None or current < previous):
                    raise EvaluationError(f"recovery cumulative costs cannot decrease or become unavailable: {field}")
    else:
        raise EvaluationError("unsupported status transition")

    if prior is not None and "sourceTimestamp" in prior.data and "sourceTimestamp" in payload:
        if _parse_timestamp(payload["sourceTimestamp"]) < _parse_timestamp(prior.data["sourceTimestamp"]):
            raise EvaluationError("source timestamps must not move backward within a slot")

    if status == "attempted":
        if any(event.attempt_id == attempt_id for event in ledger.events):
            raise EvaluationError("attemptId must be unique")
        if any(event.slot_id == slot_id and event.status == "attempted" for event in ledger.events):
            raise EvaluationError("slot cannot be attempted more than once")
    elif status in FINAL_STATUSES and prior is None:
        raise EvaluationError("terminal outcome lacks a prior attempt")

    event = LedgerEvent(
        len(ledger.events) + 1, slot.slot_id, status, attempt_id, payload,
        _canonical_sha256(payload),
    )
    return EvaluationLedger(ledger.registration_sha256, ledger.slots, ledger.events + (event,))


def validate_ledger(
    ledger: EvaluationLedger,
    registration: ValidatedRegistration,
) -> EvaluationLedger:
    """Validate roster identity, event hashes, ordering, transitions and IDs."""

    _require_validated(registration)
    _validate_ledger_history(ledger)
    if ledger.registration_sha256 != registration.sha256:
        raise EvaluationError("ledger belongs to a different registration")
    if ledger.slots != generate_slots(registration):
        raise EvaluationError("ledger slot roster differs from its registration")
    return ledger


def _validate_ledger_history(ledger: EvaluationLedger) -> None:
    if not isinstance(ledger, EvaluationLedger):
        raise EvaluationError("evaluation ledger is required")
    _require_hash(ledger.registration_sha256, "ledger.registrationSha256")
    if len(ledger.slots) != 108 or len({slot.slot_id for slot in ledger.slots}) != 108:
        raise EvaluationError("ledger must retain exactly 108 unique registered slots")
    _validate_roster_structure(ledger.slots)
    replay = EvaluationLedger(ledger.registration_sha256, ledger.slots)
    for index, event in enumerate(ledger.events, start=1):
        if not isinstance(event, LedgerEvent) or event.sequence != index:
            raise EvaluationError("ledger event sequence is invalid")
        if _canonical_sha256(event.data) != event.data_sha256:
            raise EvaluationError(f"ledger event data hash mismatch at sequence {index}")
        replay = _append_slot_event_unchecked(
            replay, event.slot_id, event.status, attempt_id=event.attempt_id, data=event.data,
        )
        if replay.events[-1] != event:
            raise EvaluationError(f"ledger event does not match replay at sequence {index}")


def _validate_roster_structure(slots: Sequence[AttemptSlot]) -> None:
    """Reject public ledgers whose 108 rows do not encode the frozen design."""

    if len(slots) != 108:
        raise EvaluationError("ledger must retain the exact 2 x 3 x 6 x 3 roster")
    fixtures: dict[str, tuple[str, str]] = {}
    prompts: dict[str, tuple[str, str]] = {}
    groups: dict[tuple[str, str, str], list[AttemptSlot]] = {}
    fixture_ids_by_class: dict[str, set[str]] = {name: set() for name in JOURNEY_CLASSES}
    for slot in slots:
        if slot.host not in HOSTS or slot.arm not in ARMS or slot.journey_class not in JOURNEY_CLASSES:
            raise EvaluationError("ledger roster contains an unknown host, arm, or journey class")
        if slot.slot_id != ":".join((slot.host, slot.journey_class, slot.fixture_id, slot.arm)):
            raise EvaluationError("ledger slot ID does not match its registered dimensions")
        _require_id(slot.fixture_id, "ledger fixtureId")
        _require_hash(slot.fixture_sha256, "ledger fixtureSha256")
        _require_id(slot.prompt_id, "ledger promptId")
        _require_hash(slot.prompt_sha256, "ledger promptSha256")
        if not _is_int(slot.order_position) or slot.order_position not in (1, 2, 3):
            raise EvaluationError("ledger order position must be 1, 2, or 3")
        fixture_value = (slot.journey_class, slot.fixture_sha256)
        if slot.fixture_id in fixtures and fixtures[slot.fixture_id] != fixture_value:
            raise EvaluationError("a fixture ID must retain one class and input hash")
        fixtures[slot.fixture_id] = fixture_value
        prompt_value = (slot.prompt_id, slot.prompt_sha256)
        if slot.journey_class in prompts and prompts[slot.journey_class] != prompt_value:
            raise EvaluationError("each journey class must retain one prompt ID and hash")
        prompts[slot.journey_class] = prompt_value
        fixture_ids_by_class[slot.journey_class].add(slot.fixture_id)
        groups.setdefault((slot.host, slot.journey_class, slot.fixture_id), []).append(slot)
    if len(fixtures) != 18 or any(len(ids) != 3 for ids in fixture_ids_by_class.values()):
        raise EvaluationError("ledger must retain three unique fixture IDs per journey class")
    if set(prompts) != set(JOURNEY_CLASSES):
        raise EvaluationError("ledger must retain one prompt per journey class")
    if len(groups) != 36:
        raise EvaluationError("ledger roster must cover each host, class, and fixture")
    for (host, journey, fixture_id), group in groups.items():
        if len(group) != 3 or {slot.arm for slot in group} != set(ARMS):
            raise EvaluationError("each host/class/fixture must contain all three arms exactly once")
        fixture_index = sorted(fixture_ids_by_class[journey]).index(fixture_id)
        expected_positions = {
            ARMS[(fixture_index + offset) % len(ARMS)]: offset + 1
            for offset in range(len(ARMS))
        }
        if any(slot.order_position != expected_positions[slot.arm] for slot in group):
            raise EvaluationError("ledger roster order does not match the counterbalanced design")


def summarize_denominators(ledger: EvaluationLedger) -> dict[str, Any]:
    """Report full intended denominators and current plus historical statuses."""

    _validate_ledger_history(ledger)
    grouped: dict[str, dict[str, Any]] = {}
    for slot in ledger.slots:
        key = f"{slot.host}/{slot.journey_class}/{slot.arm}"
        group = grouped.setdefault(
            key,
            {"host": slot.host, "journeyClass": slot.journey_class, "arm": slot.arm,
             "intended": 0, "notStarted": 0, "attempted": 0, "inProgress": 0,
             "valid": 0, "invalid": 0, "refused": 0, "cancelled": 0,
             "recovered": 0, "failed": 0, "invalidHistory": 0,
             "refusedHistory": 0, "cancelledHistory": 0, "recoveredHistory": 0,
             "failedHistory": 0},
        )
        group["intended"] += 1
        current = ledger.current_status(slot.slot_id)
        if current == "not-started":
            group["notStarted"] += 1
        else:
            group["attempted"] += 1
            if current == "attempted":
                group["inProgress"] += 1
            else:
                group[current] += 1
        for event in ledger.events:
            if event.slot_id == slot.slot_id and event.status in {"invalid", "refused", "cancelled", "recovered", "failed"}:
                group[event.status + "History"] += 1
    return {
        "registrationSha256": ledger.registration_sha256,
        "intendedSlots": len(ledger.slots),
        "groups": [grouped[key] for key in sorted(grouped)],
    }


def assess_cost_completeness(
    ledger: EvaluationLedger,
    *,
    setup_costs: Mapping[str, Any] | None,
) -> CostAssessment:
    """Check complete declared costs while preserving unknown values as null."""

    _validate_ledger_history(ledger)
    missing: list[str] = []
    totals: dict[str, int | float | None] = {}
    normalized_setup = _cost_values(setup_costs, "setupCosts", missing)
    per_slot: dict[str, list[int | float]] = {field: [] for field in COST_FIELDS}
    for slot in ledger.slots:
        event = ledger.current_event(slot.slot_id)
        costs = event.data.get("costs") if event is not None else None
        normalized = _cost_values(costs, f"{slot.slot_id}.costs", missing)
        for field in COST_FIELDS:
            value = normalized[field]
            if value is not None:
                per_slot[field].append(value)
    for field in COST_FIELDS:
        setup = normalized_setup[field]
        values = per_slot[field]
        if setup is None or len(values) != len(ledger.slots):
            totals[field] = None
        elif field in {"rss_bytes", "disk_bytes"}:
            totals[field] = max([setup, *values])
        else:
            totals[field] = setup + sum(values)
    return CostAssessment(not missing, tuple(sorted(set(missing))), totals)


def check_cost_caps(
    registration: ValidatedRegistration,
    observed: Mapping[str, Any],
) -> CapAssessment:
    """Return a stop decision when a cap is exceeded or a required value is unknown."""

    _require_validated(registration)
    missing: list[str] = []
    values = _cost_values(observed, "observedCosts", missing)
    caps = registration.data["costCaps"]
    reasons: list[str] = []
    for field in CAP_FIELDS:
        value = values[field]
        if value is None:
            reasons.append(f"{field} is unavailable; cap compliance cannot be established")
        elif value > caps[field]:
            reasons.append(f"{field} cap exceeded")
    return CapAssessment(not reasons, bool(reasons), tuple(reasons), values)


def assess_utility_eligibility(
    registration: ValidatedRegistration,
    ledger: EvaluationLedger,
    *,
    setup_costs: Mapping[str, Any] | None,
    human_ratings: Mapping[str, Sequence[Mapping[str, Any]]],
    adjudications: Mapping[str, Mapping[str, Any]] | None = None,
    monetary_summary: Any = None,
    expected_monetary_roster_sha256: str | None = None,
) -> UtilityEligibility:
    """Assess preregistered positive-claim eligibility, never assert utility.

    Human ratings must come from two distinct independent humans for every slot.
    Disagreements require an explicit adjudication. Model/Luna annotations do not
    count. Unknown authority handling fails the 18/18 requirement. Subscription
    policies additionally require a registration-bound full economic cost summary;
    complete legacy scalars or zero additional spend cannot substitute for it.
    """

    _require_validated(registration)
    validate_ledger(ledger, registration)
    if not isinstance(human_ratings, Mapping):
        raise EvaluationError("human ratings must be keyed by registered slot ID")
    if adjudications is not None and not isinstance(adjudications, Mapping):
        raise EvaluationError("adjudications must be keyed by registered slot ID")
    costs = assess_cost_completeness(ledger, setup_costs=setup_costs)
    caps = check_cost_caps(registration, costs.totals)
    denominators = summarize_denominators(ledger)
    adjudications = adjudications or {}
    reasons: list[str] = []
    if "billingPolicy" in registration.data:
        # Legacy scalar EUR completeness cannot establish subscription allocation
        # or human-cost scope. Source authentication remains the caller's duty.
        from decimal import Decimal
        from .tooling_money import MoneySummary
        if not isinstance(monetary_summary, MoneySummary):
            reasons.append("registration-bound full subscription cost summary is unavailable")
        elif monetary_summary.registration_sha256 != registration.sha256:
            reasons.append("subscription cost summary belongs to a different registration")
        else:
            if expected_monetary_roster_sha256 is None:
                reasons.append("frozen subscription monetary roster identity is unavailable")
            elif monetary_summary.roster_sha256 != _require_hash(
                    expected_monetary_roster_sha256, "expected monetary roster SHA-256"):
                reasons.append("subscription cost summary belongs to a different monetary roster")
            actual = monetary_summary.actual_additional_spend_eur
            allocated = monetary_summary.allocated_subscription_cost_eur
            cap = monetary_summary.actual_additional_spend_cap_eur
            valid_amounts = all(isinstance(value, Decimal) and value.is_finite() and value >= 0
                               for value in (actual, allocated, cap))
            if not valid_amounts:
                reasons.append("subscription economic cost amounts are unavailable or malformed")
            elif cap != Decimal(registration.data["billingPolicy"]["additionalSpendCapEur"]) or actual > cap:
                reasons.append("subscription additional-spend amount or cap violates the registered policy")
            if (monetary_summary.full_economic_cost_complete is not True
                    or monetary_summary.full_economic_cost_status != "complete"
                    or monetary_summary.required_measures_complete is not True
                    or monetary_summary.missing_full_economic_cost):
                reasons.append("subscription economic cost scope and human cost fields are incomplete")
            if (monetary_summary.stop_required is not False
                    or monetary_summary.cap_violation is not False):
                reasons.append("subscription additional-spend compliance is unavailable or violated")
    resolved: dict[str, dict[str, bool | None]] = {}
    human_complete = True
    registered_reviewer_ids = {reviewer["reviewerId"] for reviewer in registration.data["humanReviewers"]}
    for slot in ledger.slots:
        ratings = human_ratings.get(slot.slot_id, ())
        result, slot_reasons = _resolve_human_ratings(
            ratings, adjudications.get(slot.slot_id), registered_reviewer_ids,
        )
        if slot_reasons:
            human_complete = False
            reasons.extend(f"{slot.slot_id}: {reason}" for reason in slot_reasons)
        resolved[slot.slot_id] = result

    if not costs.complete:
        reasons.append("required cost fields are incomplete; unknown costs are not zero")
    if caps.stop:
        reasons.extend(caps.reasons)
    if not human_complete:
        reasons.append("two independent human ratings and resolved required labels are incomplete")

    successes: dict[str, int] = {host: 0 for host in HOSTS}
    authorities: dict[str, int] = {host: 0 for host in HOSTS}
    authority_failure = False
    fidelity_failure = False
    for slot in ledger.slots:
        if slot.arm != "mcp-plus-skills":
            continue
        labels = resolved[slot.slot_id]
        if labels["success"] is True:
            successes[slot.host] += 1
        if labels["authority_correct"] is True:
            authorities[slot.host] += 1
        if labels["authority_correct"] is not True:
            authority_failure = True
        if labels["fidelity"] is not True:
            fidelity_failure = True
    required_successes = registration.data["rubric"]["thresholds"]["armCSuccessesPerHost"]
    for host in HOSTS:
        if successes[host] < required_successes:
            reasons.append(f"{host} arm C has {successes[host]}/18 successful journeys; requires at least {required_successes}/18")
        if authorities[host] != 18:
            reasons.append(f"{host} arm C has {authorities[host]}/18 correct authority outcomes; unknown counts as failure")
    if authority_failure:
        reasons.append("an arm C authority outcome is false or unknown")
    if fidelity_failure:
        reasons.append("an arm C fidelity outcome is false or unknown")

    return UtilityEligibility(
        positive_claim_eligible=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
        denominators=denominators,
        cost_assessment=costs,
        cap_assessment=caps,
        human_scoring_complete=human_complete,
        authority_correct_by_host_arm_c=authorities,
        successful_by_host_arm_c=successes,
    )


def _resolve_human_ratings(
    ratings: Sequence[Mapping[str, Any]],
    adjudication: Mapping[str, Any] | None,
    registered_reviewer_ids: set[str],
) -> tuple[dict[str, bool | None], tuple[str, ...]]:
    fields = ("success", "authority_correct", "fidelity")
    if not isinstance(ratings, Sequence) or isinstance(ratings, (str, bytes)) or len(ratings) != 2:
        return {field: None for field in fields}, ("exactly two ratings are required",)
    ids: set[str] = set()
    values: dict[str, list[bool | None]] = {field: [] for field in fields}
    errors: list[str] = []
    for index, rating in enumerate(ratings):
        if not isinstance(rating, Mapping):
            errors.append("rating must be an object")
            continue
        reviewer_id = rating.get("reviewerId")
        _require_id(reviewer_id, f"human rating {index + 1} reviewerId")
        if reviewer_id in ids:
            errors.append("reviewer IDs must be distinct")
        ids.add(reviewer_id)
        if reviewer_id not in registered_reviewer_ids:
            errors.append("rating reviewer is not in the frozen registration")
        if rating.get("reviewerType") != "human" or rating.get("independent") is not True:
            errors.append("ratings must be from independent human reviewers")
        for field in fields:
            value = rating.get(field)
            if not _is_bool_or_none(value):
                errors.append(f"{field} must be true, false, or null")
                value = None
            values[field].append(value)
    if ids != registered_reviewer_ids:
        errors.append("ratings must use both registered human reviewer IDs")
    adjudicated_fields: Mapping[str, Any] = {}
    adjudication_error: str | None = None
    if adjudication is not None:
        if not isinstance(adjudication, Mapping):
            adjudication_error = "adjudication record must be an object"
        else:
            try:
                core = {key: adjudication.get(key) for key in ("recordId", "adjudicatorId", "fields")}
                _require_id(core["recordId"], "adjudication.recordId")
                if core["adjudicatorId"] not in registered_reviewer_ids:
                    raise EvaluationError("adjudicator must be a registered human reviewer")
                _require_object(core["fields"], "adjudication.fields")
                for field, value in core["fields"].items():
                    if field not in fields or not _is_bool_or_none(value):
                        raise EvaluationError("adjudication fields must be known labels with boolean or null values")
                _require_hash(adjudication.get("sha256"), "adjudication.sha256")
                if _canonical_sha256(core) != adjudication["sha256"]:
                    raise EvaluationError("adjudication record SHA-256 mismatch")
                adjudicated_fields = core["fields"]
            except EvaluationError as exc:
                adjudication_error = str(exc)
    resolved: dict[str, bool | None] = {}
    for field, pair in values.items():
        if len(pair) != 2:
            resolved[field] = None
        elif pair[0] == pair[1]:
            resolved[field] = pair[0]
        elif adjudication_error is None and field in adjudicated_fields and _is_bool_or_none(adjudicated_fields[field]):
            resolved[field] = adjudicated_fields[field]
        else:
            resolved[field] = None
            errors.append(f"{field} disagreement requires explicit adjudication")
        if resolved[field] is None:
            errors.append(f"{field} remains missing or unresolved")
    if adjudication_error:
        errors.append(adjudication_error)
    return resolved, tuple(dict.fromkeys(errors))


def _validate_host_builds(hosts: Any, *, schema_version: str = REGISTRATION_SCHEMA,
                          billing_policy: Any = None) -> None:
    if not isinstance(hosts, list) or len(hosts) != len(HOSTS):
        raise EvaluationError("hosts must list Codex and Claude Code exactly once")
    if {host.get("name") for host in hosts if isinstance(host, Mapping)} != set(HOSTS):
        raise EvaluationError("registered host names must be codex and claude-code")
    for host in hosts:
        _require_object(host, "host")
        _require_version_hash(host, "host")
        model = host.get("model")
        _require_object(model, f"{host['name']}.model")
        _require_text(model.get("name"), f"{host['name']}.model.name")
        identity = host.get("modelIdentity")
        if schema_version == REGISTRATION_SCHEMA:
            if identity is not None or "modelIdentity" in host:
                raise EvaluationError("registration v1 cannot contain modelIdentity; use registration v2")
            _require_version_hash(model, f"{host['name']}.model")
        else:
            if identity is None:
                raise EvaluationError("registration v2 requires modelIdentity for every host")
            try:
                model_identity_policy.validate_identity(identity, host=host["name"], model=model)
            except model_identity_policy.ModelIdentityError as exc:
                raise EvaluationError(f"{host['name']} model identity is invalid: {exc}") from exc
            if identity["cliBuild"] != {"version": host["version"], "sha256": host["sha256"]}:
                raise EvaluationError(f"{host['name']} CLI build identity must match the registered host build")
            if billing_policy is not None:
                account = next(item for item in billing_policy["hosts"] if item["host"] == host["name"])
                route = identity["providerRoute"]
                if (route["accountSha256"] != account["accountSha256"]
                        or route["authMethod"] != account["authMethod"]):
                    raise EvaluationError(f"{host['name']} model provider route differs from billingPolicy account")
        os_build = host.get("os")
        _require_object(os_build, f"{host['name']}.os")
        if os_build.get("name") != "macOS" or os_build.get("architecture") != "arm64":
            raise EvaluationError("real-host registrations require exact macOS arm64 builds")
        _require_version_hash(os_build, f"{host['name']}.os")
        sdk = host.get("sdk")
        _require_object(sdk, f"{host['name']}.sdk")
        _require_text(sdk.get("name"), f"{host['name']}.sdk.name")
        _require_version_hash(sdk, f"{host['name']}.sdk")


def _validate_fixtures(fixtures: Any) -> list[dict[str, str]]:
    if not isinstance(fixtures, list) or len(fixtures) != 18:
        raise EvaluationError("registration requires exactly 18 immutable fixtures")
    result: list[dict[str, str]] = []
    for fixture in fixtures:
        _require_object(fixture, "fixture")
        fixture_id = _require_id(fixture.get("fixtureId"), "fixture.fixtureId")
        journey = fixture.get("journeyClass")
        if journey not in JOURNEY_CLASSES:
            raise EvaluationError(f"unknown fixture journeyClass: {journey}")
        result.append({"fixtureId": fixture_id, "journeyClass": journey,
                       "sha256": _require_hash(fixture.get("sha256"), f"fixture {fixture_id}.sha256")})
    if len({item["fixtureId"] for item in result}) != 18:
        raise EvaluationError("fixture IDs must be unique")
    if any(sum(item["journeyClass"] == journey for item in result) != 3 for journey in JOURNEY_CLASSES):
        raise EvaluationError("each journey class must have exactly three independent fixtures")
    return result


def _validate_prompts(prompts: Any) -> list[dict[str, str]]:
    if not isinstance(prompts, list) or len(prompts) != len(JOURNEY_CLASSES):
        raise EvaluationError("registration requires exactly one immutable prompt per journey class")
    result: list[dict[str, str]] = []
    for prompt in prompts:
        _require_object(prompt, "prompt")
        prompt_id = _require_id(prompt.get("promptId"), "prompt.promptId")
        journey = prompt.get("journeyClass")
        if journey not in JOURNEY_CLASSES:
            raise EvaluationError(f"unknown prompt journeyClass: {journey}")
        result.append({"promptId": prompt_id, "journeyClass": journey,
                       "sha256": _require_hash(prompt.get("sha256"), f"prompt {prompt_id}.sha256")})
    if len({item["promptId"] for item in result}) != len(result):
        raise EvaluationError("prompt IDs must be unique")
    if {item["journeyClass"] for item in result} != set(JOURNEY_CLASSES):
        raise EvaluationError("each journey class must have one prompt")
    return result


def _validate_source_rights(value: Any) -> None:
    _require_record(value, "sourceRights", "approved")
    fixture_ids = value.get("fixtureIds")
    _require_id(value.get("recordId"), "sourceRights.recordId")
    if not isinstance(fixture_ids, list):
        raise EvaluationError("sourceRights must enumerate all 18 approved fixture IDs")
    for fixture_id in fixture_ids:
        _require_id(fixture_id, "sourceRights.fixtureIds[]")
    if len(fixture_ids) != 18 or len(set(fixture_ids)) != 18:
        raise EvaluationError("sourceRights must enumerate all 18 approved fixture IDs")
    if not isinstance(value.get("scope"), str) or not value["scope"].strip():
        raise EvaluationError("sourceRights.scope is required")


def _validate_provider_opt_in(value: Any) -> None:
    _require_object(value, "provider")
    if value.get("optIn") is not True:
        raise EvaluationError("provider opt-in must be explicitly true for capture admission")
    _require_id(value.get("providerId"), "provider.providerId")
    _require_id(value.get("consentRecordId"), "provider.consentRecordId")
    _require_hash(value.get("consentRecordSha256"), "provider.consentRecordSha256")


def _validate_cost_caps(value: Any) -> None:
    _require_object(value, "costCaps")
    if set(value) != set(CAP_FIELDS):
        raise EvaluationError("costCaps must explicitly set EUR, total tokens, wall, RSS, and disk caps")
    for field in CAP_FIELDS:
        number = value[field]
        if number is None or not _is_finite_number(number) or number <= 0:
            raise EvaluationError(f"costCaps.{field} must be a positive finite number")


def _validate_billing_policy(value: Any) -> None:
    """Share the canonical policy constraints with subscription receipt binding."""
    try:
        _subscription_policy_sha256(value)
    except SubscriptionError as exc:
        raise EvaluationError(f"invalid billingPolicy: {exc}") from exc


def _validate_cost_rates(value: Any, hosts: Sequence[Mapping[str, Any]]) -> None:
    _require_object(value, "costRates")
    if value.get("currency") != "EUR":
        raise EvaluationError("costRates.currency must be EUR")
    rates = value.get("byHost")
    if not isinstance(rates, list) or len(rates) != len(HOSTS):
        raise EvaluationError("costRates.byHost must identify both registered host models")
    models = {host["name"]: host["model"]["name"] for host in hosts}
    seen: set[str] = set()
    for entry in rates:
        _require_object(entry, "costRates.byHost entry")
        host = entry.get("host")
        if host not in models or host in seen or entry.get("modelName") != models[host]:
            raise EvaluationError("cost rate entries must match each exact registered host/model")
        seen.add(host)
        for field in ("inputEurPerMillionTokens", "outputEurPerMillionTokens"):
            rate = entry.get(field)
            if not _is_finite_number(rate) or rate < 0:
                raise EvaluationError(f"costRates.byHost.{field} must be a finite nonnegative value")
        _require_id(entry.get("recordId"), "costRates.byHost.recordId")
        _require_hash(entry.get("sha256"), "costRates.byHost.sha256")
    if seen != set(HOSTS):
        raise EvaluationError("costRates must include exactly one rate record per host")


def _validate_reviewers(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise EvaluationError("registration must name exactly two human reviewers")
    ids: set[str] = set()
    for reviewer in value:
        _require_object(reviewer, "human reviewer")
        if reviewer.get("type") != "human" or reviewer.get("independent") is not True:
            raise EvaluationError("both registered reviewers must be independent humans")
        ids.add(_require_id(reviewer.get("reviewerId"), "human reviewer.reviewerId"))
    if len(ids) != 2:
        raise EvaluationError("human reviewer IDs must be distinct")


def _validate_rubric(value: Any) -> None:
    _require_object(value, "rubric")
    _require_id(value.get("version"), "rubric.version")
    _require_hash(value.get("sha256"), "rubric.sha256")
    thresholds = value.get("thresholds")
    _require_object(thresholds, "rubric.thresholds")
    successes = thresholds.get("armCSuccessesPerHost")
    authority = thresholds.get("authorityCorrectPerHost")
    if not _is_int(successes) or not 16 <= successes <= 18 or authority != 18:
        raise EvaluationError("rubric must set arm C success threshold from 16/18 through 18/18 and authority to 18/18")
    if value.get("frozen") is not True:
        raise EvaluationError("rubric must be frozen before capture")


def _validate_record(value: Any, label: str, status: str) -> None:
    _require_record(value, label, status)
    _require_id(value.get("recordId"), f"{label}.recordId")
    _require_hash(value.get("sha256"), f"{label}.sha256")


def _require_record(value: Any, label: str, status: str) -> None:
    _require_object(value, label)
    if value.get("status") != status:
        raise EvaluationError(f"{label}.status must be {status}")


def _require_version_hash(value: Mapping[str, Any], label: str) -> None:
    _require_text(value.get("version"), f"{label}.version")
    _require_hash(value.get("sha256"), f"{label}.sha256")


def _validate_event_data(data: Mapping[str, Any]) -> None:
    allowed = {"reason", "completion", "authorityCorrect", "costs", "inputSha256", "outputSha256", "interventions", "sourceTimestamp"}
    unknown = set(data) - allowed
    if unknown:
        raise EvaluationError("unsupported ledger event fields: " + ", ".join(sorted(unknown)))
    for field in ("inputSha256", "outputSha256"):
        if field in data:
            _require_hash(data[field], field)
    if "interventions" in data and (not _is_int(data["interventions"]) or data["interventions"] < 0):
        raise EvaluationError("interventions must be a nonnegative integer")
    if "reason" in data and not isinstance(data["reason"], str):
        raise EvaluationError("reason must be a string")
    if "sourceTimestamp" in data:
        _require_timestamp(data["sourceTimestamp"], "sourceTimestamp")


def _validate_observed_costs(value: Any) -> None:
    _require_object(value, "costs")
    if set(value) != set(COST_FIELDS):
        raise EvaluationError("costs must explicitly include EUR, tokens, wall, RSS, and disk fields")
    integer_fields = {"tokens", "input_tokens", "output_tokens", "retry_tokens", "rss_bytes", "disk_bytes"}
    for field, number in value.items():
        if number is None:
            continue
        if field in integer_fields:
            valid = _is_int(number) and number >= 0
        else:
            valid = _is_finite_number(number) and number >= 0
        if not valid:
            raise EvaluationError(f"costs.{field} must be a nonnegative finite value or null")
    token_parts = (value["input_tokens"], value["output_tokens"], value["retry_tokens"])
    if all(part is not None for part in token_parts):
        if value["tokens"] != sum(token_parts):
            raise EvaluationError("costs.tokens must equal input, output, and retry token totals")
    elif value["tokens"] is not None:
        raise EvaluationError("costs.tokens must remain null when any token component is unavailable")


def _cost_values(value: Mapping[str, Any] | None, label: str, missing: list[str]) -> dict[str, int | float | None]:
    if value is None:
        missing.extend(f"{label}.{field}" for field in COST_FIELDS)
        return {field: None for field in COST_FIELDS}
    _validate_observed_costs(value)
    result = dict(value)
    missing.extend(f"{label}.{field}" for field, number in result.items() if number is None)
    return result


def _find_slot(ledger: EvaluationLedger, slot_id: str) -> AttemptSlot:
    for slot in ledger.slots:
        if slot.slot_id == slot_id:
            return slot
    raise EvaluationError(f"unknown registered slot: {slot_id}")


def _require_validated(registration: ValidatedRegistration) -> None:
    if not isinstance(registration, ValidatedRegistration):
        raise EvaluationError("a validated registration object is required")
    if _canonical_sha256(registration.data) != registration.sha256:
        raise EvaluationError("validated registration was mutated after validation")


def _require_object(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise EvaluationError(f"{label} must be an object")


def _require_id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise EvaluationError(f"{label} must be a bounded nonempty identifier")
    return value


def _require_text(value: Any, label: str) -> str:
    if (not isinstance(value, str) or not value.strip() or len(value) > 256
            or any(ord(character) < 32 for character in value)):
        raise EvaluationError(f"{label} must be nonempty bounded text without control characters")
    return value


def _require_git_commit(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", value):
        raise EvaluationError(f"{label} must be a full lowercase Git commit ID")
    return value


def _require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise EvaluationError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _require_timestamp(value: Any, label: str) -> str:
    _parse_timestamp(value, label)
    return value


def _parse_timestamp(value: Any, label: str = "sourceTimestamp") -> datetime:
    if not isinstance(value, str):
        raise EvaluationError(f"{label} must be an ISO-8601 timestamp with a timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvaluationError(f"{label} must be an ISO-8601 timestamp with a timezone") from exc
    if parsed.tzinfo is None:
        raise EvaluationError(f"{label} must include a timezone")
    return parsed


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_bool_or_none(value: Any) -> bool:
    return value is None or isinstance(value, bool)


def _json_copy(value: Any, label: str) -> Any:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise EvaluationError(f"{label} must contain finite JSON values") from exc


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ARMS", "COST_FIELDS", "HOSTS", "JOURNEY_CLASSES", "LEDGER_SCHEMA",
    "REGISTRATION_SCHEMA", "REGISTRATION_SCHEMA_V2", "SLOT_STATUSES", "AttemptSlot", "CapAssessment",
    "CostAssessment", "EvaluationError", "EvaluationLedger", "LedgerEvent",
    "UtilityEligibility", "ValidatedRegistration", "append_slot_event",
    "assess_cost_completeness", "assess_utility_eligibility", "check_cost_caps",
    "generate_slots", "new_ledger", "summarize_denominators", "validate_ledger",
    "validate_registration",
]
