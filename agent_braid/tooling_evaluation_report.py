# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic offline structured and narrative utility reports for SPEC-044."""
from __future__ import annotations

import json
import re
from decimal import Decimal
from collections.abc import Iterator
from typing import Any, Mapping, Sequence

from . import tooling_evaluation as evaluation
from .tooling_money import MoneyAccountingError, MoneySummary, provider_accounting_total
from .tooling_full_cost import FullCostScope

REPORT_SCHEMA = "agent-braid-m45-utility-report-v1"
_REPORT_TOKEN = object()


class UtilityReport(Mapping[str, Any]):
    """Immutable mapping returned only by the validated report builder."""

    __slots__ = ("_encoded",)

    def __init__(self, data: Mapping[str, Any], *, _token: object = None) -> None:
        if _token is not _REPORT_TOKEN:
            raise TypeError("UtilityReport values must be created by build_utility_report")
        encoded = json.dumps(data, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False)
        object.__setattr__(self, "_encoded", encoded)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("UtilityReport is immutable")

    def __getitem__(self, key: str) -> Any:
        return json.loads(self._encoded)[key]

    def __iter__(self) -> Iterator[str]:
        return iter(json.loads(self._encoded))

    def __len__(self) -> int:
        return len(json.loads(self._encoded))


def build_utility_report(
    registration_data: Mapping[str, Any],
    ledger: evaluation.EvaluationLedger,
    *,
    expected_candidate_sha256: str,
    expected_input_hashes: Mapping[str, str],
    setup_costs: Mapping[str, Any] | None,
    human_ratings: Mapping[str, Sequence[Mapping[str, Any]]],
    adjudications: Mapping[str, Mapping[str, Any]] | None = None,
    monetary_summary: Any = None,
    expected_monetary_roster_sha256: str | None = None,
) -> UtilityReport:
    """Validate exact registration/roster, derive eligibility, and build a report.

    This function trusts neither a supplied assessment nor a supplied eligibility
    boolean. Declared approval/source records remain declarations; this offline
    report cannot authenticate them or authorize capture.
    """
    registration = evaluation.validate_registration(
        registration_data,
        expected_candidate_sha256=expected_candidate_sha256,
        expected_input_hashes=expected_input_hashes,
    )
    evaluation.validate_ledger(ledger, registration)
    assessment = evaluation.assess_utility_eligibility(
        registration, ledger, setup_costs=setup_costs, human_ratings=human_ratings,
        adjudications=adjudications, monetary_summary=monetary_summary,
        expected_monetary_roster_sha256=expected_monetary_roster_sha256,
    )
    data = registration.data
    denominators = assessment.denominators
    missing_costs = list(assessment.cost_assessment.missing)
    full_cost_complete: bool | None = None
    full_cost_missing: list[str] = []
    full_cost_reasons: list[str] = []
    if "billingPolicy" in registration.data:
        registered_full_cost_scope = FullCostScope.from_registration(registration)
        scope_complete = registered_full_cost_scope is not None
        if not scope_complete:
            full_cost_missing.append("subscription.registeredFullCostScope")
            full_cost_reasons.append("registered full-cost scope is absent, pending, or unresolved")
        roster_bound = (
            isinstance(expected_monetary_roster_sha256, str)
            and re.fullmatch(r"[0-9a-f]{64}", expected_monetary_roster_sha256) is not None
            and isinstance(monetary_summary, MoneySummary)
            and monetary_summary.roster_sha256 == expected_monetary_roster_sha256
        )
        registration_bound = (
            isinstance(monetary_summary, MoneySummary)
            and monetary_summary.registration_sha256 == registration.sha256
        )
        amount_fields = (
            "actual_additional_spend_eur", "allocated_subscription_cost_eur",
            "actual_provider_spend_eur", "provider_accounting_cost_eur",
            "human_time_seconds", "user_time_seconds", "reviewer_time_seconds",
            "study_wall_seconds",
        )
        amount_aliases = {
            "actual_additional_spend_eur": "actualAdditionalSpendEur",
            "allocated_subscription_cost_eur": "allocatedSubscriptionCostEur",
            "actual_provider_spend_eur": "actualProviderSpendEur",
            "provider_accounting_cost_eur": "providerAccountingCostEur",
            "human_time_seconds": "humanTimeSeconds",
            "user_time_seconds": "userTimeSeconds",
            "reviewer_time_seconds": "reviewerTimeSeconds",
            "study_wall_seconds": "studyWallSeconds",
        }
        invalid_amounts = [
            field for field in amount_fields
            if not isinstance(monetary_summary, MoneySummary)
            or not isinstance(getattr(monetary_summary, field), Decimal)
            or not getattr(monetary_summary, field).is_finite()
            or getattr(monetary_summary, field) < 0
        ]
        for field in invalid_amounts:
            missing_name = "subscription." + amount_aliases[field]
            full_cost_missing.append(missing_name)
            full_cost_reasons.append(f"required full-cost measure is missing or invalid: {amount_aliases[field]}")
        registered_cash_cap = Decimal(registration.data["billingPolicy"]["additionalSpendCapEur"])
        cap_valid = (
            isinstance(monetary_summary, MoneySummary)
            and isinstance(monetary_summary.actual_additional_spend_cap_eur, Decimal)
            and monetary_summary.actual_additional_spend_cap_eur.is_finite()
            and monetary_summary.actual_additional_spend_cap_eur >= 0
            and monetary_summary.actual_additional_spend_cap_eur == registered_cash_cap
            and isinstance(monetary_summary.actual_additional_spend_eur, Decimal)
            and monetary_summary.actual_additional_spend_eur.is_finite()
            and monetary_summary.actual_additional_spend_eur <= registered_cash_cap
        )
        if isinstance(monetary_summary, MoneySummary) and not cap_valid:
            full_cost_missing.append("subscription.actualAdditionalSpendCapEur")
            full_cost_reasons.append("registered additional-spend cap is unavailable or violated")
        wall_cap_valid = (
            isinstance(monetary_summary, MoneySummary)
            and isinstance(monetary_summary.study_wall_seconds, Decimal)
            and monetary_summary.study_wall_seconds.is_finite()
            and monetary_summary.study_wall_seconds <= Decimal(str(
                registration.data["costCaps"]["wall_seconds"]
            ))
        )
        if isinstance(monetary_summary, MoneySummary) and not wall_cap_valid:
            full_cost_missing.append("subscription.studyWallSecondsCap")
            full_cost_reasons.append("study wall time is unavailable or exceeds the registered cap")
        accounting_cap_valid = False
        if isinstance(monetary_summary, MoneySummary) and not invalid_amounts:
            try:
                recomputed = provider_accounting_total(
                    monetary_summary.actual_provider_spend_eur,
                    monetary_summary.allocated_subscription_cost_eur,
                )
            except MoneyAccountingError:
                pass
            else:
                accounting_cap_valid = (
                    recomputed == monetary_summary.provider_accounting_cost_eur
                    and monetary_summary.actual_provider_spend_eur <= monetary_summary.actual_additional_spend_eur
                    and recomputed <= Decimal(str(registration.data["costCaps"]["eur"]))
                )
        if not accounting_cap_valid:
            full_cost_missing.append("subscription.providerAccountingCostEurCap")
            full_cost_reasons.append("provider accounting total is unavailable, inconsistent, or exceeds the registered EUR cap")
        amounts_valid = not invalid_amounts and cap_valid and wall_cap_valid and accounting_cap_valid
        summary_complete = (
            scope_complete
            and amounts_valid
            and monetary_summary.full_economic_cost_complete is True
            and monetary_summary.full_economic_cost_status == "complete"
            and monetary_summary.required_measures_complete is True
            and not monetary_summary.missing_full_economic_cost
            and monetary_summary.stop_required is False
            and monetary_summary.cap_violation is False
            and isinstance(monetary_summary.actual_additional_spend_eur, Decimal)
            and isinstance(monetary_summary.allocated_subscription_cost_eur, Decimal)
        )
        full_cost_complete = bool(roster_bound and registration_bound and summary_complete)
        if not isinstance(monetary_summary, MoneySummary):
            full_cost_missing.append("subscription.fullEconomicCostSummary")
        else:
            safe_missing, invalid_missing = _safe_full_cost_missing(
                monetary_summary.missing_full_economic_cost, registration,
                registered_full_cost_scope,
            )
            full_cost_missing.extend(safe_missing)
            if invalid_missing:
                full_cost_missing.append("subscription.fullEconomicCostDetailInvalid")
                full_cost_reasons.append("full-cost summary contains unsupported missing-field details")
        if not registration_bound:
            full_cost_missing.append("subscription.registrationBinding")
        if not roster_bound:
            full_cost_missing.append("subscription.monetaryRosterBinding")
        if not full_cost_complete and not full_cost_missing:
            full_cost_missing.append("subscription.fullEconomicCostScope")
        if not full_cost_complete and not full_cost_reasons:
            full_cost_reasons.append("full economic cost scope or required measures are incomplete")
        missing_costs.extend(full_cost_missing)
    report_reasons = list(assessment.reasons)
    report_reasons.extend(full_cost_reasons)
    eligible = assessment.positive_claim_eligible and full_cost_complete is not False
    report = {
        "schemaVersion": REPORT_SCHEMA,
        "scope": {
            "registrationId": data["registrationId"],
            "registrationSha256": registration.sha256,
            "candidate": dict(data["candidate"]),
            "sourceEvidence": {
                "recordId": data["sourceRights"]["recordId"],
                "sha256": data["sourceRights"]["sha256"],
                "fixtureInputs": [
                    {"fixtureId": item["fixtureId"], "sha256": item["sha256"]}
                    for item in sorted(data["fixtures"], key=lambda value: value["fixtureId"])
                ],
                "fixtureCount": len(data["sourceRights"]["fixtureIds"]),
                "authenticatedByThisReport": False,
            },
            "population": {"hosts": list(evaluation.HOSTS), "arms": list(evaluation.ARMS),
                           "journeyClasses": list(evaluation.JOURNEY_CLASSES)},
        },
        "utilityClaimEligible": eligible,
        "conclusion": {
            "status": "pending-independent-human-founder-interpretation" if eligible else "inconclusive",
            "positiveUtilityAsserted": False,
            "text": ("Eligibility permits independent interpretation only; no positive utility, "
                     "acceptance, or milestone closure is asserted." if eligible else
                     "Utility is inconclusive because required eligibility conditions are unmet. "
                     "No positive utility claim is permitted."),
            "pendingDecisions": ["independent human interpretation", "founder decision"],
        },
        "eligibilityReasons": report_reasons,
        "denominators": denominators,
        "attempts": _safe_ledger(ledger),
        "costs": {
            "complete": assessment.cost_assessment.complete and full_cost_complete is not False,
            "legacyScalarComplete": assessment.cost_assessment.complete,
            "fullEconomicCostRequired": "billingPolicy" in registration.data,
            "fullEconomicCostComplete": full_cost_complete,
            "fullEconomicCostStatus": (
                "not-required-by-registration" if full_cost_complete is None else
                "complete" if full_cost_complete else "incomplete-or-unavailable"
            ),
            "fullEconomic": _full_economic_cost(monetary_summary),
            "missingRequired": sorted(set(missing_costs)),
            "totals": dict(assessment.cost_assessment.totals),
            "capAssessment": {
                "withinCaps": assessment.cap_assessment.within_caps,
                "stop": assessment.cap_assessment.stop,
                "reasons": list(assessment.cap_assessment.reasons),
                "observed": dict(assessment.cap_assessment.observed),
            },
        },
        "humanScoringComplete": assessment.human_scoring_complete,
        "armC": {
            "successfulByHost": dict(assessment.successful_by_host_arm_c),
            "authorityCorrectByHost": dict(assessment.authority_correct_by_host_arm_c),
        },
        "evidenceLimits": [
            "Registration approval, source rights, provider consent, and host receipts are not authenticated by this offline report.",
            "Eligibility does not establish positive utility, scientific validity, host acceptance, founder approval, or milestone closure.",
            "All 108 intended slots and their current statuses remain in the denominator; unknown costs are not zero.",
        ],
    }
    return UtilityReport(report, _token=_REPORT_TOKEN)


def render_utility_report_json(report: UtilityReport) -> str:
    """Serialize a report deterministically as compact UTF-8-compatible JSON."""
    _validate_report(report)
    return report._encoded + "\n"


def render_utility_report_narrative(report: UtilityReport) -> str:
    """Render deterministic English decision text from the structured report."""
    _validate_report(report)
    raw = json.loads(report._encoded)
    scope = raw["scope"]
    costs = raw["costs"]
    denoms = raw["denominators"]
    lines = [
        "M4.5 utility evaluation report",
        f"Registration: {scope['registrationId']} ({scope['registrationSha256']})",
        f"Candidate: {scope['candidate']['commit']} ({scope['candidate']['sha256']})",
        f"Utility claim eligible: {str(raw['utilityClaimEligible']).lower()}",
        "Conclusion: " + ("Eligibility permits independent interpretation only; no positive utility, acceptance, or milestone closure is asserted."
                           if raw["utilityClaimEligible"] else
                           "Utility is inconclusive because required eligibility conditions are unmet. No positive utility claim is permitted."),
        f"Intended denominator: {denoms['intendedSlots']} slots across hosts {', '.join(scope['population']['hosts'])}, arms {', '.join(scope['population']['arms'])}, and {len(scope['population']['journeyClasses'])} journey classes.",
        f"Missing required cost measurements: {len(costs['missingRequired'])}.",
        "Full economic cost status: " + costs["fullEconomicCostStatus"]
        + "; actual extra EUR=" + _format_measure(costs["fullEconomic"]["actualAdditionalSpendEur"])
        + "; allocated subscription EUR=" + _format_measure(costs["fullEconomic"]["allocatedSubscriptionCostEur"])
        + "; provider accounting EUR=" + _format_measure(costs["fullEconomic"]["providerAccountingCostEur"])
        + "; active human seconds=" + _format_measure(costs["fullEconomic"]["humanTimeSeconds"])
        + "; study wall seconds=" + _format_measure(costs["fullEconomic"]["studyWallSeconds"]) + ".",
    ]
    if costs["missingRequired"]:
        lines.append("Missing cost fields/attempts: " + "; ".join(costs["missingRequired"]) + ".")
    for reason in raw["eligibilityReasons"]:
        lines.append("Eligibility reason: " + reason)
    lines.append("Per-host, arm, and journey-class intended and current-status counts follow.")
    for group in denoms["groups"]:
        counts = ", ".join(f"{key}={group[key]}" for key in (
            "intended", "notStarted", "attempted", "inProgress", "valid", "invalid",
            "refused", "cancelled", "recovered", "failed"))
        lines.append(f"{group['host']} / {group['arm']} / {group['journeyClass']}: {counts}.")
    lines.extend("Limit: " + item for item in raw["evidenceLimits"])
    return "\n".join(lines) + "\n"


def _validate_report(report: UtilityReport) -> None:
    if not isinstance(report, UtilityReport):
        raise evaluation.EvaluationError("utility report must come from build_utility_report")
    raw = json.loads(report._encoded)
    if raw.get("schemaVersion") != REPORT_SCHEMA:
        raise evaluation.EvaluationError("unsupported utility report")
    if type(raw.get("utilityClaimEligible")) is not bool:
        raise evaluation.EvaluationError("utility report eligibility must be boolean")
    if not isinstance(raw.get("attempts"), Mapping) or len(raw["attempts"].get("slots", ())) != 108:
        raise evaluation.EvaluationError("utility report must retain all 108 attempt slots")
    conclusion = raw.get("conclusion", {})
    if conclusion.get("positiveUtilityAsserted") is not False:
        raise evaluation.EvaluationError("utility reports cannot assert positive utility")
    if raw["utilityClaimEligible"]:
        if conclusion.get("status") != "pending-independent-human-founder-interpretation":
            raise evaluation.EvaluationError("eligible report must await human and founder interpretation")
    else:
        if conclusion.get("status") != "inconclusive":
            raise evaluation.EvaluationError("ineligible utility report must be inconclusive")
        if not raw.get("eligibilityReasons"):
            raise evaluation.EvaluationError("ineligible utility report must explain its reasons")


def _safe_ledger(ledger: evaluation.EvaluationLedger) -> dict[str, Any]:
    """Keep every slot and event while excluding free-form event text."""
    slots = []
    for slot in ledger.slots:
        slots.append({**slot.as_dict(), "currentStatus": ledger.current_status(slot.slot_id)})
    events = []
    for event in ledger.events:
        data = event.data
        projection = {key: data[key] for key in (
            "sourceTimestamp", "completion", "authorityCorrect", "costs",
            "inputSha256", "outputSha256") if key in data}
        events.append({
            "sequence": event.sequence, "slotId": event.slot_id,
            "status": event.status, "dataSha256": event.data_sha256,
            "observations": projection,
        })
    return {
        "schemaVersion": evaluation.LEDGER_SCHEMA,
        "registrationSha256": ledger.registration_sha256,
        "intendedSlots": len(slots), "slots": slots, "events": events,
    }


def _full_economic_cost(summary: Any) -> dict[str, str | None]:
    fields = {
        "actualAdditionalSpendEur": "actual_additional_spend_eur",
        "actualAdditionalSpendCapEur": "actual_additional_spend_cap_eur",
        "allocatedSubscriptionCostEur": "allocated_subscription_cost_eur",
        "actualProviderSpendEur": "actual_provider_spend_eur",
        "providerAccountingCostEur": "provider_accounting_cost_eur",
        "apiReferenceEstimateEur": "api_reference_estimate_eur",
        "humanTimeSeconds": "human_time_seconds",
        "userTimeSeconds": "user_time_seconds",
        "reviewerTimeSeconds": "reviewer_time_seconds",
        "studyWallSeconds": "study_wall_seconds",
    }
    if not isinstance(summary, MoneySummary):
        return {name: None for name in fields}
    return {
        name: (str(value) if isinstance(value, Decimal) else None)
        for name, attribute in fields.items()
        for value in (getattr(summary, attribute),)
    }


def _format_measure(value: str | None) -> str:
    return "unknown" if value is None else value


def _safe_full_cost_missing(
    missing: object, registration: evaluation.ValidatedRegistration,
    scope: FullCostScope | None,
) -> tuple[list[str], bool]:
    """Allowlist summary field paths before including them in any export."""
    if not isinstance(missing, tuple) or len(missing) > 1024:
        return [], True
    attempt_ids = {slot.slot_id for slot in evaluation.generate_slots(registration)}
    activity_ids = attempt_ids | {"setup"}
    participant_ids = ({scope.user_time_participant_id} | {
        reviewer_id for reviewer_id, _ in scope.reviewer_fee_applicability
    }) if scope is not None else set()
    allowed_measures = set(evaluation.COST_FIELDS) | {
        "attemptOutcome", "allocatedSubscriptionCostEur", "actualAdditionalSpendEur",
        "actual-spend-or-cap", "sourceVerification", "approvalVerification", "interval",
    }
    rendered: list[str] = []
    invalid = False
    for item in missing:
        if not isinstance(item, tuple) or len(item) != 2:
            invalid = True
            continue
        activity, field = item
        if not isinstance(activity, str) or not isinstance(field, str):
            invalid = True
            continue
        if activity in activity_ids and field in allowed_measures:
            rendered.append(f"subscription.{activity}.{field}")
        elif (activity in activity_ids and any(
                field == f"humanTime:{participant}" for participant in participant_ids)):
            participant = field.split(":", 1)[1]
            rendered.append(f"subscription.{activity}.humanTime.{participant}")
        elif activity == "registration-costs" and field in evaluation.COST_FIELDS:
            rendered.append(f"subscription.registrationCosts.{field}")
        elif activity == "study-cash" and field == "actual-spend-or-cap":
            rendered.append("subscription.actualSpendCompliance")
        elif activity == "studyWall" and field in {"sourceVerification", "interval"}:
            rendered.append(f"subscription.studyWall.{field}")
        elif activity == "numeric-stop" and field in {
            f"{cap} cap exceeded" for cap in evaluation.CAP_FIELDS
        } | {
            f"{cap} is unavailable; cap compliance cannot be established"
            for cap in evaluation.CAP_FIELDS
        }:
            rendered.append("subscription.registeredStopCap")
        elif activity == "registration" and field == "fullCostScope":
            rendered.append("subscription.registeredFullCostScope")
        else:
            invalid = True
    return sorted(set(rendered)), invalid
