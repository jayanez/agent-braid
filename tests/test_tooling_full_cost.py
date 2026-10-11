# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for prospective SPEC-044 T006 full-cost composition."""
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
import copy
import hashlib
import json
import hashlib
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_subscription_estimate as subscription_estimate
from agent_braid.tooling_full_cost import (
    FullCostScope,
    FullCostError,
    HumanTimeAttestation,
    HumanTimeReceipt,
    ScopeApprovalAttestation,
    StudyWallAttestation,
    StudyWallIntervalReceipt,
    complete_full_cost,
)
from agent_braid.tooling_money import (
    AllocationMethodBinding,
    AllocationPolicyAttestation,
    AllocationShare,
    MoneyAccountingError,
    MoneyActivity,
    MoneyLedger,
    MoneyRoster,
    SourceAttestation,
)
from tests.test_tooling_evaluation import (
    _complete_ledger, _known_costs, _registration as _base_registration, _registration_v3,
)
from tests.test_tooling_money import _receipt, _sha


_START = "2026-10-09T10:00:00Z"
_END = "2026-10-09T15:00:00Z"
_ACTIVITY_END = "2026-10-09T10:05:00Z"
_OBSERVED = "2026-11-02T00:00:00Z"
_METHOD = {
    "methodId": "approved-allocation-method",
    "methodRef": "allocation-method-record",
    "methodSha256": _sha("registered allocation method"),
    "denominatorId": "registered-cohort-denominator",
    "unit": "registered-usage-unit",
}


def _registration(*, scope_status="approved", reviewer_fee="unpaid", technical_capture=False):
    data = _registration_base(_registration_v3() if technical_capture else None)
    data["fullCostScope"] = {
        "schema": "agent-braid-m45-full-cost-scope-v1",
        "status": scope_status,
        "scopeId": "m45-full-cost-scope",
        "approval": {
            "status": "approved" if scope_status == "approved" else "pending",
            "recordId": "prospective-cost-approval",
            "sha256": _sha("prospective-cost-approval"),
        },
        "reviewerFees": [
            {"reviewerId": reviewer_id, "applicability": reviewer_fee}
            for reviewer_id in ("planned-reviewer-one", "planned-reviewer-two") if technical_capture
        ] if technical_capture else [
            {"reviewerId": reviewer["reviewerId"], "applicability": reviewer_fee}
            for reviewer in data["humanReviewers"]
        ],
        "subscriptionAllocation": {
            "activityKinds": ["setup", "attempt"],
            "reviewerApplicability": "not-applicable",
            **_METHOD,
        },
        "humanTime": {
            "userParticipantId": "operator-1",
            "userActivityKinds": ["setup", "attempt"],
            "reviewerActivityKinds": ["attempt"],
            "intervalSemantics": "verified-active-work-only",
        },
    }
    return evaluation.validate_registration(
        data, expected_candidate_sha256=data["candidate"]["sha256"],
        expected_input_hashes={
            **{item["fixtureId"]: item["sha256"] for item in data["fixtures"]},
            **{item["promptId"]: item["sha256"] for item in data["prompts"]},
        },
    )


def _registration_v5(*, reviewer_fee="unknown"):
    """Synthetic operational-policy v5 cohort for cost-consumer controls."""
    from tests.test_tooling_evaluation import _registration_v4

    legacy_registration = _registration(technical_capture=True, reviewer_fee=reviewer_fee)
    data = copy.deepcopy(dict(legacy_registration.data))
    estimate = _registration_v4()[subscription_estimate.REGISTRATION_FIELD]
    data[subscription_estimate.REGISTRATION_FIELD] = copy.deepcopy(estimate)
    data["schemaVersion"] = evaluation.REGISTRATION_SCHEMA_V5
    accounts = {
        host["name"]: host["modelIdentity"]["providerRoute"]["accountSha256"]
        for host in data["hosts"]
    }
    data["billingPolicy"] = {
        "schema": "agent-braid-m45-operational-subscription-policy-v3",
        "mode": "included-subscription-only", "scope": "registered-native-process-only",
        "accountWideApiBilling": "unknown-out-of-scope", "additionalSpendCapEur": 0,
        "maxAgeSeconds": 30, "paidApiAllowed": False, "overageAllowed": False,
        "creditsAllowed": False, "autoRechargeAllowed": False,
        "hosts": [
            {"host": "codex", "authMethod": "chatgpt", "accountSha256": accounts["codex"],
             "accountNamespaceSha256": _sha("codex-namespace")},
            {"host": "claude-code", "authMethod": "claude.ai", "accountSha256": accounts["claude-code"],
             "accountNamespaceSha256": _sha("claude-namespace")},
        ],
        "processContracts": {},
        "observer": {"sourceRef": "synthetic-observer", "sourceSha256": _sha("observer"),
                     "verifierRef": "synthetic-observer-verifier",
                     "verifierSha256": _sha("observer-verifier"),
                     "providerEnforcedQuotaBoundaryRequired": True},
    }
    for slot in evaluation.generate_slots(legacy_registration):
        host = next(item for item in data["hosts"] if item["name"] == slot.host)
        data["billingPolicy"]["processContracts"][slot.slot_id] = {
            "host": slot.host, "hostBuildSha256": host["sha256"],
            "candidateArtifactSha256": data["candidate"]["sha256"],
            "executableSha256": host["sha256"],
            "configSha256": _sha("config:" + slot.slot_id),
            "argvSha256": _sha("argv:" + slot.slot_id),
            "modelIdentitySha256": hashlib.sha256(json.dumps(
                host["modelIdentity"], sort_keys=True, separators=(",", ":"),
                ensure_ascii=False, allow_nan=False,
            ).encode("utf-8")).hexdigest(),
        }
    return evaluation.validate_registration(
        data, expected_candidate_sha256=data["candidate"]["sha256"],
        expected_input_hashes={**{item["fixtureId"]: item["sha256"] for item in data["fixtures"]},
                               **{item["promptId"]: item["sha256"] for item in data["prompts"]}},
    )


def _registration_base(data=None):
    data = data or _base_registration()
    data["billingPolicy"] = {
        "schema": "agent-braid-m45-subscription-policy-v1",
        "mode": "included-subscription-only",
        "additionalSpendCapEur": 0,
        "paidApiAllowed": False,
        "overageAllowed": False,
        "creditsAllowed": False,
        "autoRechargeAllowed": False,
        "hosts": [
            {"host": "codex", "authMethod": "chatgpt", "accountSha256": _sha("codex-account")},
            {"host": "claude-code", "authMethod": "claude.ai", "accountSha256": _sha("claude-account")},
        ],
    }
    for host in data["hosts"]:
        if "modelIdentity" in host:
            policy_host = next(row for row in data["billingPolicy"]["hosts"]
                               if row["host"] == host["name"])
            host["modelIdentity"]["providerRoute"]["accountSha256"] = policy_host["accountSha256"]
            host["modelIdentity"]["providerRoute"]["authMethod"] = policy_host["authMethod"]
    return data


def _roster(registration):
    account_by_host = {row["host"]: row["accountSha256"]
                       for row in registration.data["billingPolicy"]["hosts"]}
    activities = [MoneyActivity("setup", "setup", "setup-account", _sha("setup-account"),
                                started_at=_START, ended_at=_ACTIVITY_END)]
    activities.extend(
        MoneyActivity(slot.slot_id, "attempt", f"account-{slot.host}", account_by_host[slot.host],
                      host=slot.host, started_at=_START, ended_at=_ACTIVITY_END)
        for slot in evaluation.generate_slots(registration)
    )
    activities.extend(
        MoneyActivity(f"reviewer:{reviewer_id}", "reviewer",
                      f"reviewer-account-{reviewer_id}", _sha(f"reviewer:{reviewer_id}"),
                      reviewer_id=reviewer_id, started_at=_START, ended_at=_END)
        for reviewer_id in evaluation.expected_reviewer_participants(registration)
    )
    return MoneyRoster(registration, "cohort-2026-10", _START, _END, tuple(activities))


def _method(roster):
    return AllocationMethodBinding(
        roster.registration_ref, roster.registration_sha256,
        _METHOD["methodId"], _METHOD["methodRef"], _METHOD["methodSha256"],
        _METHOD["denominatorId"], _METHOD["unit"],
    )


class _SourceVerifier:
    def verify_source(self, receipt):
        return SourceAttestation("synthetic-source-verifier", receipt.sha256, _OBSERVED)


class _PolicyVerifier:
    def verify_registered_method(self, binding):
        return AllocationPolicyAttestation("synthetic-policy-verifier", binding.sha256, _OBSERVED)


class _ScopeVerifier:
    def __init__(self, *, tamper=False):
        self.tamper = tamper

    def verify_scope(self, scope, registration_sha256, roster_sha256):
        return ScopeApprovalAttestation(
            "synthetic-approved-scope-verifier", registration_sha256, roster_sha256,
            "0" * 64 if self.tamper else scope.scope_sha256,
            scope.approval_record_id, scope.approval_record_sha256, _OBSERVED,
        )


class _TimeVerifier:
    def verify_human_time(self, receipt):
        return HumanTimeAttestation("synthetic-time-verifier", receipt.sha256, _OBSERVED)


class _WallVerifier:
    def verify_study_wall(self, receipt):
        return StudyWallAttestation("synthetic-wall-verifier", receipt.sha256, _OBSERVED)


def _time_receipts(roster):
    activities = [item for item in roster.activities if item.kind in {"setup", "attempt"}]
    reviewers = {item.reviewer_id for item in roster.activities if item.kind == "reviewer"}
    attempt_ids = tuple(item.activity_id for item in activities if item.kind == "attempt")
    all_ids = tuple(item.activity_id for item in activities)
    rows = [("operator-1", all_ids, "10:00:00", "10:01:00")]
    if roster.registration.data["schemaVersion"] not in {
            evaluation.REGISTRATION_SCHEMA_V3, evaluation.REGISTRATION_SCHEMA_V4,
            evaluation.REGISTRATION_SCHEMA_V5,
    }:
        rows.extend((reviewer, attempt_ids, start, end)
                    for reviewer, start, end in (("rater-one", "10:01:00", "10:02:00"),
                                                 ("rater-two", "10:02:00", "10:03:00")))
    return tuple(HumanTimeReceipt(
        participant, activity_ids, f"2026-10-09T{start}Z", f"2026-10-09T{end}Z",
        f"time-observation-{index}", _sha(f"time-observation:{index}"),
    ) for index, (participant, activity_ids, start, end) in enumerate(rows))


def _wall_receipts(roster):
    return tuple(StudyWallIntervalReceipt(
        item.activity_id, item.started_at, item.ended_at, f"wall:{item.activity_id}", _sha(f"wall:{item.activity_id}")
    ) for item in roster.activities if item.kind in {"setup", "attempt"})


def _filled_money(roster, *, positive_cash=False, allocation=True,
                  allocation_amount=Decimal("0.1")):
    ledger = MoneyLedger(roster, source_verifier=_SourceVerifier(),
                         allocation_policy_verifier=_PolicyVerifier())
    method = _method(roster)
    for activity in roster.activities:
        if (roster.registration.data["schemaVersion"] in {
                evaluation.REGISTRATION_SCHEMA_V3, evaluation.REGISTRATION_SCHEMA_V4,
                evaluation.REGISTRATION_SCHEMA_V5,
        }
                and activity.kind == "reviewer"):
            continue
        amount = Decimal("0.01") if positive_cash and activity.activity_id == "setup" else Decimal("0")
        ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=amount))
    if allocation:
        for activity in roster.activities:
            if activity.kind not in {"setup", "attempt"}:
                continue
            ledger.add(_receipt(
                roster, activity, "allocatedSubscriptionCostEur", amount=allocation_amount,
                method=method, share=AllocationShare(Decimal("1"), Decimal("1000")),
                source_identity=f"subscription-{activity.account_sha256}",
            ))
    return ledger, ledger.summarize()


class FullCostContractTests(unittest.TestCase):
    def test_v5_scope_parses_as_technical_only_with_review_cost_unknown(self):
        registration = _registration_v5()
        scope = FullCostScope.from_registration(registration)

        self.assertIsNotNone(scope)
        self.assertTrue(scope.technical_only)
        self.assertEqual({"unknown"}, {value for _, value in scope.reviewer_fee_applicability})
        self.assertEqual("5.045", registration.data[subscription_estimate.REGISTRATION_FIELD]["reservationEur"])

    def test_v5_completion_keeps_unknown_cash_pending_while_carrying_estimate(self):
        registration = _registration_v5()
        roster = _roster(registration)
        money_ledger = MoneyLedger(roster, source_verifier=_SourceVerifier(),
                                   allocation_policy_verifier=_PolicyVerifier())
        money_summary = money_ledger.summarize()
        ledger = evaluation.new_ledger(registration)
        ledger_sha = hashlib.sha256(json.dumps(
            ledger.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        evidence = subscription_estimate.ActiveTimeEvidence(
            registration.sha256, ledger_sha, "synthetic-active-time", _sha("active-time"),
            "2026-10-09T16:00:00Z", {"codex": 57_600, "claude-code": 57_600},
        )

        class EstimateVerifier:
            def verify_active_time(self, *, registration_sha256, ledger_sha256, evidence):
                return registration_sha256 == registration.sha256 and ledger_sha256 == ledger_sha

        result = complete_full_cost(
            registration, ledger, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            subscription_estimate_evidence=evidence,
            subscription_estimate_verifier=EstimateVerifier(),
        )

        self.assertEqual("pending-cash-verification", result.full_economic_cost_status)
        self.assertIsNone(result.actual_additional_spend_eur)
        self.assertIsNone(result.actual_provider_spend_eur)
        self.assertIsNone(result.allocated_subscription_cost_eur)
        self.assertIsNone(result.provider_accounting_cost_eur)
        self.assertEqual(Decimal("5.045"), result.subscription_allocation_upper_bound_eur)
        self.assertIsNone(result.stop_required)
        self.assertIsNone(result.technical_stop_required)

    def test_v4_estimated_route_completes_technical_costs_but_leaves_actual_allocation_unknown(self):
        data = copy.deepcopy(_registration(technical_capture=True, reviewer_fee="unknown").data)
        data["schemaVersion"] = evaluation.REGISTRATION_SCHEMA_V4
        data[subscription_estimate.REGISTRATION_FIELD] = {
            "schema": subscription_estimate.SCHEMA,
            "methodId": subscription_estimate.METHOD_ID,
            "nominalPeriodSeconds": subscription_estimate.PERIOD_SECONDS,
            "pricesEurPerMonth": {"codex": "100.00", "claude-code": "111.89"},
            "maxActiveSecondsPerHost": subscription_estimate.MAX_ACTIVE_SECONDS_PER_HOST,
            "reservationEur": "5.045", "budgetCeilingEur": "25.00",
            "decisionSha256": _sha("estimate decision"),
            "codexPriceSourceSha256": _sha("synthetic Codex source"),
            "claudeCodePriceSourceSha256": _sha("synthetic Claude source"),
        }
        registration = evaluation.validate_registration(
            data, expected_candidate_sha256=data["candidate"]["sha256"],
            expected_input_hashes={**{item["fixtureId"]: item["sha256"] for item in data["fixtures"]},
                                   **{item["promptId"]: item["sha256"] for item in data["prompts"]}},
        )
        roster = _roster(registration)
        money_ledger, money_summary = _filled_money(roster, allocation=False)
        ledger, _ratings = _complete_ledger(registration)
        ledger_sha = hashlib.sha256(json.dumps(
            ledger.as_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        ).encode()).hexdigest()
        evidence = subscription_estimate.ActiveTimeEvidence(
            registration.sha256, ledger_sha, "synthetic-active-time-source", _sha("active time"),
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            {"codex": 100, "claude-code": 100})

        class EstimateVerifier:
            def verify_active_time(self, *, registration_sha256, ledger_sha256, evidence):
                return (registration_sha256 == registration.sha256
                        and ledger_sha256 == ledger_sha and evidence is not None)

        result = complete_full_cost(
            registration, ledger, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            subscription_estimate_evidence=evidence,
            subscription_estimate_verifier=EstimateVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        self.assertEqual("incomplete-registered-cost-scope", result.full_economic_cost_status)
        self.assertTrue(result.technical_required_measures_complete, result.as_dict())
        self.assertFalse(result.technical_stop_required)
        self.assertEqual(Decimal("0.000000"), result.technical_additional_spend_eur)
        self.assertEqual(Decimal("0.009"), result.subscription_allocation_upper_bound_eur)
        self.assertIsNone(result.allocated_subscription_cost_eur)
        self.assertIsNone(result.provider_accounting_cost_eur)

    def test_v3_cost_roster_keeps_abstract_reviewer_rows_and_unknown_fee_scope(self):
        registration = _registration(technical_capture=True, reviewer_fee="unknown")
        self.assertEqual(evaluation.expected_reviewer_participants(registration),
                         ("planned-reviewer-one", "planned-reviewer-two"))
        planned_scope = FullCostScope.from_registration(registration)
        self.assertIsNotNone(planned_scope)
        self.assertTrue(planned_scope.technical_only)
        roster = _roster(registration)
        reviewer_rows = [item for item in roster.activities if item.kind == "reviewer"]
        self.assertEqual({item.reviewer_id for item in reviewer_rows},
                         {"planned-reviewer-one", "planned-reviewer-two"})
        self.assertEqual(len(reviewer_rows), 2)

    def test_v3_reconciles_verified_technical_cost_user_time_and_wall_but_not_reviewers(self):
        registration = _registration(technical_capture=True, reviewer_fee="unknown")
        scope = FullCostScope.from_registration(registration)
        self.assertIsNotNone(scope)
        self.assertTrue(scope.technical_only)
        roster = _roster(registration)
        money_ledger, money_summary = _filled_money(roster)
        ledger, _ratings = _complete_ledger(registration)
        result = complete_full_cost(
            registration, ledger, roster, money_ledger, money_summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        self.assertFalse(result.required_measures_complete)
        self.assertTrue(result.missing_required)
        self.assertTrue(result.stop_required)
        self.assertTrue(result.technical_required_measures_complete)
        self.assertEqual((), result.missing_technical_required)
        self.assertEqual(Decimal("0.000000"), result.technical_additional_spend_eur)
        self.assertFalse(result.technical_cap_violation)
        self.assertFalse(result.technical_stop_required)
        self.assertIsNotNone(result.actual_provider_spend_eur)
        self.assertIsNotNone(result.allocated_subscription_cost_eur)
        self.assertEqual(Decimal("60.000000"), result.user_time_seconds)
        self.assertIsNone(result.reviewer_time_seconds)
        self.assertIsNone(result.human_time_seconds)
        self.assertEqual(Decimal("300.000000"), result.study_wall_seconds)
        self.assertEqual(109, len(result.study_wall_receipt_sha256s))

    def test_v3_unapproved_or_malformed_technical_scope_stays_unavailable(self):
        pending = _registration(scope_status="pending", technical_capture=True)
        self.assertIsNone(FullCostScope.from_registration(pending))
        malformed_data = copy.deepcopy(dict(_registration(technical_capture=True).data))
        malformed_data["fullCostScope"]["reviewerFees"].pop()
        malformed = evaluation.validate_registration(
            malformed_data, expected_candidate_sha256=malformed_data["candidate"]["sha256"],
            expected_input_hashes={
                **{item["fixtureId"]: item["sha256"] for item in malformed_data["fixtures"]},
                **{item["promptId"]: item["sha256"] for item in malformed_data["prompts"]},
            },
        )
        with self.assertRaisesRegex(FullCostError, "registered reviewer roster"):
            FullCostScope.from_registration(malformed)

    def _assessment(self, *, scope_verifier=None, time_receipts=None, positive_cash=False,
                    allocation=True, reviewer_fee="unpaid", slot_statuses=None):
        registration = _registration(reviewer_fee=reviewer_fee)
        roster = _roster(registration)
        money_ledger, summary = _filled_money(roster, positive_cash=positive_cash, allocation=allocation)
        evaluation_ledger, _ratings = _complete_ledger(registration)
        if slot_statuses is not None:
            evaluation_ledger = slot_statuses(evaluation_ledger, registration)
        complete = complete_full_cost(
            registration, evaluation_ledger, roster, money_ledger, summary,
            setup_costs=_known_costs(),
            human_time_receipts=_time_receipts(roster) if time_receipts is None else time_receipts,
            scope_verifier=scope_verifier or _ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        return registration, roster, money_ledger, complete

    def test_authenticated_complete_scope_composes_full_cost_without_hourly_valuation(self):
        registration = _registration()
        roster = _roster(registration)
        money_ledger, summary = _filled_money(roster)
        result = complete_full_cost(
            registration, _complete_ledger(registration)[0], roster, money_ledger, summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertTrue(result.full_economic_cost_complete)
        self.assertEqual(result.full_economic_cost_status, "complete")
        self.assertEqual(result.actual_additional_spend_eur, Decimal("0"))
        self.assertEqual(result.allocated_subscription_cost_eur, Decimal("10.9"))
        self.assertEqual(result.human_time_seconds, Decimal("180.000000"))
        self.assertEqual(result.user_time_seconds, Decimal("60.000000"))
        self.assertEqual(result.reviewer_time_seconds, Decimal("120.000000"))
        self.assertEqual(len(result.human_time_receipt_sha256s), 3)
        self.assertEqual(result.study_wall_seconds, Decimal("300.000000"))
        self.assertEqual(result.as_dict()["fullEconomicCostComplete"], True)

    def test_subscription_allocation_cannot_bypass_provider_accounting_cap(self):
        registration = _registration()
        roster = _roster(registration)
        money, summary = _filled_money(roster, allocation_amount=Decimal("1"))
        self.assertEqual(Decimal("0"), summary.actual_additional_spend_eur)
        self.assertEqual(Decimal("0"), summary.actual_provider_spend_eur)
        self.assertEqual(Decimal("109"), summary.provider_accounting_cost_eur)
        result = complete_full_cost(
            registration, _complete_ledger(registration)[0], roster, money, summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        self.assertTrue(result.stop_required)
        self.assertFalse(result.cap_violation)  # Additional cash remains within EUR 0.
        self.assertTrue(any("EUR cap" in field for _activity, field in result.missing_full_economic_cost))
        self.assertEqual("109", result.as_dict()["providerAccountingCostEur"])

    def test_absent_pending_or_unknown_fee_scope_stays_incomplete(self):
        registration = _registration()
        no_scope = replace(registration, data={key: value for key, value in registration.data.items()
                                               if key != "fullCostScope"})
        no_scope = evaluation.ValidatedRegistration(no_scope.data, evaluation._canonical_sha256(no_scope.data))
        for value in (no_scope, _registration(scope_status="pending"),
                      _registration(reviewer_fee="unknown")):
            roster = _roster(value)
            money, summary = _filled_money(roster)
            result = complete_full_cost(
                value, _complete_ledger(value)[0], roster, money, summary,
                setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
                scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
                study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            )
            self.assertFalse(result.full_economic_cost_complete)

    def test_positive_cash_excess_and_missing_allocation_or_human_time_fail_closed(self):
        _reg_value, _roster_value, _money, excess = self._assessment(positive_cash=True)
        self.assertFalse(excess.full_economic_cost_complete)
        self.assertTrue(excess.stop_required)

        _reg_value, _roster_value, _money, no_allocation = self._assessment(allocation=False)
        self.assertFalse(no_allocation.full_economic_cost_complete)

        registration = _registration()
        roster = _roster(registration)
        money, summary = _filled_money(roster)
        incomplete_time = _time_receipts(roster)[:-1]
        result = complete_full_cost(
            registration, _complete_ledger(registration)[0], roster, money, summary,
            setup_costs=_known_costs(), human_time_receipts=incomplete_time,
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        self.assertIsNone(result.human_time_seconds)

    def test_review_extends_wall_cap_but_overlapping_review_is_not_added_twice(self):
        registration = _registration()
        roster = _roster(registration)
        money, summary = _filled_money(roster)
        receipts = list(_time_receipts(roster))
        receipts[1] = HumanTimeReceipt(
            "rater-one", receipts[1].activity_ids, "2026-10-09T10:05:00Z",
            "2026-10-09T11:05:00Z", "review-after-run", _sha("review-after-run"),
        )
        result = complete_full_cost(
            registration, _complete_ledger(registration)[0], roster, money, summary,
            setup_costs=_known_costs(), human_time_receipts=tuple(receipts),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        self.assertTrue(result.stop_required)
        self.assertEqual(result.study_wall_seconds, Decimal("3900.000000"))

    def test_allocation_must_match_approved_scope_and_money_summary_cannot_be_forged(self):
        registration = _registration()
        roster = _roster(registration)
        ledger = MoneyLedger(roster, source_verifier=_SourceVerifier(),
                             allocation_policy_verifier=_PolicyVerifier())
        method = replace(_method(roster), method_sha256=_sha("different method"))
        for activity in roster.activities:
            ledger.add(_receipt(roster, activity, "actualAdditionalSpendEur", amount=Decimal("0")))
            if activity.kind in {"setup", "attempt"}:
                ledger.add(_receipt(
                    roster, activity, "allocatedSubscriptionCostEur", amount=Decimal("0.1"),
                    method=method, share=AllocationShare(Decimal("1"), Decimal("1000")),
                    source_identity=f"subscription-{activity.account_sha256}",
                ))
        summary = ledger.summarize()
        result = complete_full_cost(
            registration, _complete_ledger(registration)[0], roster, ledger, summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)
        with self.assertRaisesRegex(FullCostError, "does not match the verified ledger"):
            complete_full_cost(
                registration, _complete_ledger(registration)[0], roster, ledger,
                replace(summary, actual_additional_spend_cap_eur=Decimal("99")),
                setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
                scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
                study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            )

    def test_scope_approval_stale_registration_and_stale_money_summary_are_rejected(self):
        registration = _registration()
        roster = _roster(registration)
        money, summary = _filled_money(roster)
        with self.assertRaisesRegex(FullCostError, "exact registration and roster"):
            complete_full_cost(
                registration, _complete_ledger(registration)[0], roster, money, summary,
                setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
                scope_verifier=_ScopeVerifier(tamper=True), time_verifier=_TimeVerifier(),
                study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            )
        with self.assertRaisesRegex(FullCostError, "different registration"):
            complete_full_cost(
                registration, _complete_ledger(registration)[0], roster, money,
                replace(summary, registration_sha256=_sha("stale registration")),
                setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
                scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
                study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            )

    def test_incomplete_attempt_and_unauthenticated_time_are_not_complete(self):
        registration = _registration()
        roster = _roster(registration)
        money, summary = _filled_money(roster)
        ledger, _ratings = _complete_ledger(registration)
        last = ledger.slots[-1]
        # Construct an incomplete but structurally valid ledger by retaining its
        # not-started initial state for the final registered slot.
        ledger = replace(ledger, events=tuple(event for event in ledger.events
                                              if event.slot_id != last.slot_id))
        result = complete_full_cost(
            registration, ledger, roster, money, summary,
            setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
            scope_verifier=_ScopeVerifier(), time_verifier=_TimeVerifier(),
            study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
        )
        self.assertFalse(result.full_economic_cost_complete)

        class WrongTimeVerifier:
            def verify_human_time(self, receipt):
                return HumanTimeAttestation("synthetic-time-verifier", "0" * 64, _OBSERVED)

        with self.assertRaisesRegex(FullCostError, "exact interval receipt"):
            complete_full_cost(
                registration, _complete_ledger(registration)[0], roster, money, summary,
                setup_costs=_known_costs(), human_time_receipts=_time_receipts(roster),
                scope_verifier=_ScopeVerifier(), time_verifier=WrongTimeVerifier(),
                study_wall_receipts=_wall_receipts(roster), study_wall_verifier=_WallVerifier(),
            )


if __name__ == "__main__":
    unittest.main()
