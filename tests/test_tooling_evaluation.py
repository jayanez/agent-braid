# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic, offline controls for M4.5 evaluation preparation and accounting."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import unittest

from agent_braid import tooling_evaluation as evaluation


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _registration() -> dict:
    fixtures = [
        {
            "fixtureId": f"fixture-{journey}-{index}",
            "journeyClass": journey,
            "sha256": _sha(f"fixture:{journey}:{index}"),
        }
        for journey in evaluation.JOURNEY_CLASSES
        for index in range(1, 4)
    ]
    prompts = [
        {
            "promptId": f"prompt-{journey}",
            "journeyClass": journey,
            "sha256": _sha(f"prompt:{journey}"),
        }
        for journey in evaluation.JOURNEY_CLASSES
    ]
    hosts = []
    for host in evaluation.HOSTS:
        hosts.append(
            {
                "name": host,
                "version": "test-build-1",
                "sha256": _sha(f"host:{host}"),
                "model": {"name": f"model-{host}", "version": "model-build-1", "sha256": _sha(f"model:{host}")},
                "os": {"name": "macOS", "version": "test-arm64", "architecture": "arm64", "sha256": _sha(f"os:{host}")},
                "sdk": {"name": "mcp", "version": "2.3.0", "sha256": _sha(f"sdk:{host}")},
            }
        )
    fixture_ids = [fixture["fixtureId"] for fixture in fixtures]
    return {
        "schemaVersion": evaluation.REGISTRATION_SCHEMA,
        "registrationId": "m45-test-registration",
        "status": "approved",
        "ownerApproval": {"status": "approved", "recordId": "approval-record", "sha256": _sha("approval")},
        "candidate": {"commit": "a" * 40, "version": "0.1.0a1", "sha256": "a" * 64},
        "sourceRights": {
            "status": "approved",
            "recordId": "rights-record",
            "sha256": _sha("rights"),
            "fixtureIds": fixture_ids,
            "scope": "synthetic validator test data only",
        },
        "provider": {
            "optIn": True,
            "providerId": "provider-test",
            "consentRecordId": "consent-test",
            "consentRecordSha256": _sha("consent"),
        },
        "costCaps": {"eur": 25.0, "tokens": 250000, "wall_seconds": 3600.0, "rss_bytes": 2_000_000_000, "disk_bytes": 5_000_000_000},
        "costRates": {
            "currency": "EUR",
            "byHost": [
                {"host": host, "modelName": f"model-{host}",
                 "inputEurPerMillionTokens": 1.0, "outputEurPerMillionTokens": 2.0,
                 "recordId": f"rate-card-{host}", "sha256": _sha(f"rate-card:{host}")}
                for host in evaluation.HOSTS
            ],
        },
        "humanReviewers": [
            {"reviewerId": "rater-one", "type": "human", "independent": True},
            {"reviewerId": "rater-two", "type": "human", "independent": True},
        ],
        "rubric": {
            "version": "rubric-test-v1",
            "sha256": _sha("rubric"),
            "frozen": True,
            "thresholds": {"armCSuccessesPerHost": 16, "authorityCorrectPerHost": 18},
        },
        "fixtures": fixtures,
        "prompts": prompts,
        "hosts": hosts,
    }


def _inputs(registration: dict) -> dict[str, str]:
    return {
        **{item["fixtureId"]: item["sha256"] for item in registration["fixtures"]},
        **{item["promptId"]: item["sha256"] for item in registration["prompts"]},
    }


def _validated(registration: dict | None = None) -> evaluation.ValidatedRegistration:
    value = registration or _registration()
    return evaluation.validate_registration(
        value,
        expected_candidate_sha256=value["candidate"]["sha256"],
        expected_input_hashes=_inputs(value),
    )


def _known_costs(**overrides):
    values = {"eur": 0.0, "tokens": 0, "input_tokens": 0, "output_tokens": 0,
              "retry_tokens": 0, "wall_seconds": 0.0, "rss_bytes": 0, "disk_bytes": 0}
    values.update(overrides)
    return values


def _adjudication(reviewer_id: str, **fields):
    core = {"recordId": "adjudication-record", "adjudicatorId": reviewer_id, "fields": fields}
    encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {**core, "sha256": hashlib.sha256(encoded).hexdigest()}


def _complete_ledger(registration: evaluation.ValidatedRegistration, *, unknown_authority_slot: str | None = None,
                     successful_slots: set[str] | None = None, missing_cost_slot: str | None = None):
    ledger = evaluation.new_ledger(registration)
    ratings: dict[str, list[dict]] = {}
    for index, slot in enumerate(ledger.slots):
        attempt_id = f"attempt-{index:03d}"
        ledger = evaluation.append_slot_event(
            ledger, slot.slot_id, "attempted", attempt_id=attempt_id,
            data={"sourceTimestamp": "2026-10-08T10:00:00Z"},
        )
        authority = None if slot.slot_id == unknown_authority_slot else True
        costs = _known_costs(tokens=None, input_tokens=None) if slot.slot_id == missing_cost_slot else _known_costs()
        success = slot.slot_id not in (successful_slots or set())
        ledger = evaluation.append_slot_event(
            ledger, slot.slot_id, "valid", attempt_id=attempt_id,
            data={
                "sourceTimestamp": "2026-10-08T10:01:00Z",
                "completion": success,
                "authorityCorrect": authority,
                "costs": costs,
                "inputSha256": slot.fixture_sha256,
                "outputSha256": _sha(f"output:{slot.slot_id}"),
            },
        )
        ratings[slot.slot_id] = [
            {"reviewerId": "rater-one", "reviewerType": "human", "independent": True,
             "success": success, "authority_correct": authority, "fidelity": True},
            {"reviewerId": "rater-two", "reviewerType": "human", "independent": True,
             "success": success, "authority_correct": authority, "fidelity": True},
        ]
    return ledger, ratings


class ToolingEvaluationTests(unittest.TestCase):
    def test_subscription_policy_is_optional_and_strict_when_present(self):
        # Legacy registrations keep their existing identity; the opt-in policy
        # has no effect on the independent positive total-cost cap/rate fields.
        original = _registration()
        legacy = _validated(original)
        policy_registration = copy.deepcopy(original)
        policy_registration["billingPolicy"] = {
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
        validated = _validated(policy_registration)
        self.assertEqual(legacy.data["costCaps"]["eur"], 25.0)
        self.assertEqual(validated.data["billingPolicy"]["additionalSpendCapEur"], 0)
        mutations = (
            ("additionalSpendCapEur", 1), ("paidApiAllowed", True),
            ("overageAllowed", True), ("creditsAllowed", True),
            ("autoRechargeAllowed", True), ("mode", "subscription-plus-api"),
        )
        for field, value in mutations:
            malformed = copy.deepcopy(policy_registration)
            malformed["billingPolicy"][field] = value
            with self.subTest(field=field), self.assertRaises(evaluation.EvaluationError):
                _validated(malformed)
        malformed = copy.deepcopy(policy_registration)
        malformed["billingPolicy"]["hosts"][0]["authMethod"] = "api"
        with self.assertRaises(evaluation.EvaluationError):
            _validated(malformed)

    def test_registration_requires_exact_hashes_rights_provider_opt_in_and_caps(self) -> None:
        registration = _registration()
        validated = _validated(registration)
        self.assertEqual(64, len(validated.sha256))

        changed = copy.deepcopy(registration)
        changed["candidate"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(evaluation.EvaluationError, "candidate SHA-256"):
            evaluation.validate_registration(
                changed,
                expected_candidate_sha256="a" * 64,
                expected_input_hashes=_inputs(changed),
            )

        changed = copy.deepcopy(registration)
        changed["provider"]["optIn"] = False
        with self.assertRaisesRegex(evaluation.EvaluationError, "opt-in"):
            _validated(changed)

        changed = copy.deepcopy(registration)
        changed["costCaps"]["eur"] = None
        with self.assertRaisesRegex(evaluation.EvaluationError, "costCaps.eur"):
            _validated(changed)

        changed_inputs = _inputs(registration)
        changed_inputs["fixture-analyze-interactions-1"] = "f" * 64
        with self.assertRaisesRegex(evaluation.EvaluationError, "input SHA-256 mismatch"):
            evaluation.validate_registration(
                registration,
                expected_candidate_sha256="a" * 64,
                expected_input_hashes=changed_inputs,
            )

        with self.assertRaisesRegex(TypeError, "expected_input_hashes"):
            evaluation.validate_registration(registration, expected_candidate_sha256="a" * 64)

        omitted = _inputs(registration)
        omitted.pop("prompt-analyze-interactions")
        with self.assertRaisesRegex(evaluation.EvaluationError, "exactly 18 fixtures and six prompts"):
            evaluation.validate_registration(
                registration, expected_candidate_sha256="a" * 64,
                expected_input_hashes=omitted,
            )

    def test_registration_refuses_nonfinite_values_and_unfrozen_rubric(self) -> None:
        changed = _registration()
        changed["costCaps"]["eur"] = math.inf
        with self.assertRaises(evaluation.EvaluationError):
            _validated(changed)
        changed = _registration()
        changed["rubric"]["frozen"] = False
        with self.assertRaisesRegex(evaluation.EvaluationError, "frozen"):
            _validated(changed)

        changed = _registration()
        changed["candidate"]["commit"] = "a" * 39
        with self.assertRaisesRegex(evaluation.EvaluationError, "full lowercase Git commit"):
            _validated(changed)

        changed = _registration()
        changed["rubric"]["thresholds"]["armCSuccessesPerHost"] = 19
        with self.assertRaisesRegex(evaluation.EvaluationError, "success threshold"):
            _validated(changed)

    def test_roster_has_108_slots_and_balances_order_per_host_and_class(self) -> None:
        slots = evaluation.generate_slots(_validated())
        self.assertEqual(108, len(slots))
        self.assertEqual(108, len({slot.slot_id for slot in slots}))
        for host in evaluation.HOSTS:
            for journey in evaluation.JOURNEY_CLASSES:
                group = [slot for slot in slots if slot.host == host and slot.journey_class == journey]
                self.assertEqual(9, len(group))
                for arm in evaluation.ARMS:
                    self.assertEqual(3, sum(slot.arm == arm for slot in group))
                for arm in evaluation.ARMS:
                    self.assertEqual({1, 2, 3}, {
                        slot.order_position for slot in group if slot.arm == arm
                    })

    def test_ledger_preserves_full_denominator_and_refusal_failure_cancelled_states(self) -> None:
        registration = _validated()
        ledger = evaluation.new_ledger(registration)
        first, second, third = (ledger.slots[index] for index in range(3))
        ledger = evaluation.append_slot_event(
            ledger, first.slot_id, "not-started",
            data={"sourceTimestamp": "2026-10-08T10:00:00Z", "reason": "operator did not start"},
        )
        for slot, attempt_id, status in ((second, "attempt-second", "refused"), (third, "attempt-third", "failed")):
            ledger = evaluation.append_slot_event(
                ledger, slot.slot_id, "attempted", attempt_id=attempt_id,
                data={"sourceTimestamp": "2026-10-08T10:00:00Z"},
            )
            ledger = evaluation.append_slot_event(
                ledger, slot.slot_id, status, attempt_id=attempt_id,
                data={"sourceTimestamp": "2026-10-08T10:01:00Z", "completion": False,
                      "authorityCorrect": None, "costs": _known_costs(tokens=None, input_tokens=None), "reason": status},
            )
        fourth = ledger.slots[3]
        ledger = evaluation.append_slot_event(
            ledger, fourth.slot_id, "attempted", attempt_id="attempt-fourth",
            data={"sourceTimestamp": "2026-10-08T10:00:00Z"},
        )
        ledger = evaluation.append_slot_event(
            ledger, fourth.slot_id, "cancelled", attempt_id="attempt-fourth",
            data={"sourceTimestamp": "2026-10-08T10:01:00Z", "completion": None,
                  "authorityCorrect": None, "costs": _known_costs(tokens=None, input_tokens=None), "reason": "cancelled"},
        )
        ledger = evaluation.append_slot_event(
            ledger, fourth.slot_id, "recovered", attempt_id="attempt-fourth",
            data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                  "authorityCorrect": None, "costs": _known_costs(tokens=None, input_tokens=None), "reason": "inspected after cancel"},
        )
        summary = evaluation.summarize_denominators(ledger)
        self.assertEqual(108, summary["intendedSlots"])
        self.assertEqual(108, sum(group["intended"] for group in summary["groups"]))
        self.assertEqual("not-started", ledger.current_status(first.slot_id))
        self.assertEqual("refused", ledger.current_status(second.slot_id))
        self.assertEqual("failed", ledger.current_status(third.slot_id))
        self.assertEqual("recovered", ledger.current_status(fourth.slot_id))
        self.assertEqual("recovered", ledger.as_dict()["events"][-1]["status"])
        fourth_group = next(
            group for group in summary["groups"]
            if group["host"] == fourth.host and group["journeyClass"] == fourth.journey_class and group["arm"] == fourth.arm
        )
        self.assertEqual(1, fourth_group["cancelledHistory"])
        self.assertEqual(1, fourth_group["recovered"])
        with self.assertRaisesRegex(evaluation.EvaluationError, "retries require"):
            evaluation.append_slot_event(
                ledger, second.slot_id, "attempted", attempt_id="retry-second",
                data={"sourceTimestamp": "2026-10-08T10:02:00Z"},
            )

    def test_recovery_cost_snapshot_is_monotonic_and_zero_is_not_a_reset(self) -> None:
        registration = _validated()
        slot = evaluation.new_ledger(registration).slots[0]

        def interrupted(costs):
            ledger = evaluation.new_ledger(registration)
            ledger = evaluation.append_slot_event(
                ledger, slot.slot_id, "attempted", attempt_id="attempt-recovery",
                data={"sourceTimestamp": "2026-10-08T10:00:00Z"},
            )
            return evaluation.append_slot_event(
                ledger, slot.slot_id, "failed", attempt_id="attempt-recovery",
                data={"sourceTimestamp": "2026-10-08T10:01:00Z", "completion": False,
                      "authorityCorrect": None, "costs": costs},
            )

        spent = _known_costs(eur=100.0, tokens=1000, input_tokens=700,
                             output_tokens=200, retry_tokens=100, wall_seconds=3900.0,
                             rss_bytes=500, disk_bytes=600)
        ledger = interrupted(spent)
        with self.assertRaisesRegex(evaluation.EvaluationError, "cannot decrease.*eur"):
            evaluation.append_slot_event(
                ledger, slot.slot_id, "recovered", attempt_id="attempt-recovery",
                data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                      "authorityCorrect": None, "costs": _known_costs()},
            )

        for field in ("rss_bytes", "disk_bytes"):
            with self.subTest(field=field):
                lower = dict(spent)
                lower[field] = spent[field] - 1
                prior_ledger = interrupted(spent)
                with self.assertRaisesRegex(evaluation.EvaluationError, f"cannot decrease.*{field}"):
                    evaluation.append_slot_event(
                        prior_ledger, slot.slot_id, "recovered", attempt_id="attempt-recovery",
                        data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                              "authorityCorrect": None, "costs": lower},
                    )

        increased = _known_costs(eur=101.0, tokens=1100, input_tokens=700,
                                 output_tokens=300, retry_tokens=100, wall_seconds=4000.0,
                                 rss_bytes=500, disk_bytes=600)
        recovered = evaluation.append_slot_event(
            ledger, slot.slot_id, "recovered", attempt_id="attempt-recovery",
            data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                  "authorityCorrect": None, "costs": increased},
        )
        self.assertEqual(increased, recovered.current_event(slot.slot_id).data["costs"])
        cap_result = evaluation.check_cost_caps(registration, increased)
        self.assertIn("eur cap exceeded", cap_result.reasons)
        self.assertIn("wall_seconds cap exceeded", cap_result.reasons)

        unknown_then_known = interrupted(_known_costs(eur=None))
        repaired = evaluation.append_slot_event(
            unknown_then_known, slot.slot_id, "recovered", attempt_id="attempt-recovery",
            data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                  "authorityCorrect": None, "costs": _known_costs(eur=3.0)},
        )
        self.assertEqual(3.0, repaired.current_event(slot.slot_id).data["costs"]["eur"])

        unknown_not_repaired = interrupted(_known_costs(eur=None))
        still_unknown = evaluation.append_slot_event(
            unknown_not_repaired, slot.slot_id, "recovered", attempt_id="attempt-recovery",
            data={"sourceTimestamp": "2026-10-08T10:02:00Z", "completion": False,
                  "authorityCorrect": None, "costs": _known_costs(eur=None)},
        )
        costs = evaluation.assess_cost_completeness(still_unknown, setup_costs=_known_costs())
        self.assertFalse(costs.complete)
        self.assertIsNone(costs.totals["eur"])

    def test_public_ledger_reporting_rejects_malformed_108_row_distribution(self) -> None:
        registration = _validated()
        healthy = evaluation.new_ledger(registration)
        self.assertEqual(108, evaluation.summarize_denominators(healthy)["intendedSlots"])
        source = healthy.slots[0]
        malformed_slots = tuple(
            evaluation.AttemptSlot(
                slot_id=f"codex:analyze-interactions:fake-{index}:cli",
                host="codex", arm="cli", journey_class="analyze-interactions",
                fixture_id=f"fake-{index}", fixture_sha256=source.fixture_sha256,
                prompt_id=source.prompt_id, prompt_sha256=source.prompt_sha256,
                order_position=1,
            )
            for index in range(108)
        )
        malformed = evaluation.EvaluationLedger(healthy.registration_sha256, malformed_slots)
        with self.assertRaisesRegex(evaluation.EvaluationError, "three unique fixture IDs"):
            evaluation.summarize_denominators(malformed)
        with self.assertRaisesRegex(evaluation.EvaluationError, "three unique fixture IDs"):
            malformed.as_dict()
        with self.assertRaisesRegex(evaluation.EvaluationError, "three unique fixture IDs"):
            evaluation.assess_cost_completeness(malformed, setup_costs=_known_costs())

    def test_zero_cost_is_known_but_null_cost_is_not(self) -> None:
        registration = _validated()
        ledger, _ = _complete_ledger(registration)
        all_zero = evaluation.assess_cost_completeness(ledger, setup_costs=_known_costs())
        self.assertTrue(all_zero.complete)
        self.assertEqual(0, all_zero.totals["tokens"])

        slot = ledger.slots[-1]
        incomplete, _ = _complete_ledger(registration, missing_cost_slot=slot.slot_id)
        costs = evaluation.assess_cost_completeness(incomplete, setup_costs=_known_costs())
        self.assertFalse(costs.complete)
        self.assertIsNone(costs.totals["tokens"])
        self.assertTrue(any(slot.slot_id in field for field in costs.missing))

    def test_cost_caps_stop_on_unknown_or_exceeded_amount(self) -> None:
        registration = _validated()
        unknown = evaluation.check_cost_caps(registration, _known_costs(tokens=None, input_tokens=None))
        self.assertTrue(unknown.stop)
        self.assertFalse(unknown.within_caps)
        self.assertIn("tokens is unavailable", unknown.reasons[0])

        exceeded = evaluation.check_cost_caps(registration, _known_costs(eur=25.01))
        self.assertTrue(exceeded.stop)
        self.assertIn("eur cap exceeded", exceeded.reasons)

        within = evaluation.check_cost_caps(registration, _known_costs(eur=25.0))
        self.assertTrue(within.within_caps)

    def test_positive_claim_eligibility_requires_costs_thresholds_and_two_humans(self) -> None:
        registration = _validated()
        ledger, ratings = _complete_ledger(registration)
        result = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertTrue(result.positive_claim_eligible)
        self.assertTrue(result.human_scoring_complete)
        self.assertEqual({host: 18 for host in evaluation.HOSTS}, dict(result.authority_correct_by_host_arm_c))
        self.assertEqual({host: 18 for host in evaluation.HOSTS}, dict(result.successful_by_host_arm_c))

        failures = {
            slot.slot_id for slot in ledger.slots
            if slot.arm == "mcp-plus-skills" and slot.host == "codex"
            and slot.journey_class == evaluation.JOURNEY_CLASSES[0]
            and slot.fixture_id.endswith(("-1", "-2"))
        }
        ledger, ratings = _complete_ledger(registration, successful_slots=failures)
        threshold = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertTrue(threshold.positive_claim_eligible)
        self.assertEqual(16, threshold.successful_by_host_arm_c["codex"])

        stricter = _registration()
        stricter["rubric"]["thresholds"]["armCSuccessesPerHost"] = 17
        stricter_registration = _validated(stricter)
        below_stricter, ratings = _complete_ledger(stricter_registration, successful_slots=failures)
        blocked = evaluation.assess_utility_eligibility(
            stricter_registration, below_stricter, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(blocked.positive_claim_eligible)
        self.assertTrue(any("requires at least 17/18" in reason for reason in blocked.reasons))

        one_failure = {next(iter(failures))}
        ledger, ratings = _complete_ledger(stricter_registration, successful_slots=one_failure)
        eligible = evaluation.assess_utility_eligibility(
            stricter_registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertTrue(eligible.positive_claim_eligible)

    def test_unknown_authority_missing_costs_and_model_ratings_block_claim(self) -> None:
        registration = _validated()
        ledger, ratings = _complete_ledger(registration)
        authority_slot = next(slot.slot_id for slot in ledger.slots if slot.host == "codex" and slot.arm == "mcp-plus-skills")
        for rating in ratings[authority_slot]:
            rating["authority_correct"] = None
        unknown = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(unknown.positive_claim_eligible)
        self.assertEqual(17, unknown.authority_correct_by_host_arm_c["codex"])
        self.assertTrue(any("unknown counts as failure" in reason for reason in unknown.reasons))

        ledger, ratings = _complete_ledger(registration, missing_cost_slot=ledger.slots[-1].slot_id)
        missing = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(missing.positive_claim_eligible)
        self.assertIsNone(missing.cost_assessment.totals["tokens"])

        for slot_ratings in ratings.values():
            slot_ratings[1]["reviewerType"] = "model"
        model_labels = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(model_labels.human_scoring_complete)
        self.assertFalse(model_labels.positive_claim_eligible)

        ledger, ratings = _complete_ledger(registration)
        arm_c_slot = next(slot.slot_id for slot in ledger.slots if slot.host == "codex" and slot.arm == "mcp-plus-skills")
        ratings[arm_c_slot][1]["fidelity"] = False
        fidelity = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(fidelity.positive_claim_eligible)
        self.assertTrue(any("fidelity outcome is false" in reason for reason in fidelity.reasons))

    def test_disagreement_requires_explicit_adjudication_and_registration_is_immutable(self) -> None:
        registration = _validated()
        ledger, ratings = _complete_ledger(registration)
        slot_id = ledger.slots[0].slot_id
        ratings[slot_id][1]["fidelity"] = False
        unresolved = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
        )
        self.assertFalse(unresolved.human_scoring_complete)
        resolved = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
            adjudications={slot_id: _adjudication("rater-one", fidelity=True)},
        )
        self.assertTrue(resolved.human_scoring_complete)

        bad_hash = _adjudication("rater-one", fidelity=True)
        bad_hash["sha256"] = "0" * 64
        rejected = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
            adjudications={slot_id: bad_hash},
        )
        self.assertFalse(rejected.human_scoring_complete)

        outsider = evaluation.assess_utility_eligibility(
            registration, ledger, setup_costs=_known_costs(), human_ratings=ratings,
            adjudications={slot_id: _adjudication("unregistered", fidelity=True)},
        )
        self.assertFalse(outsider.human_scoring_complete)

        registration.data["candidate"]["sha256"] = "b" * 64
        with self.assertRaisesRegex(evaluation.EvaluationError, "mutated after validation"):
            evaluation.generate_slots(registration)

    def test_ledger_validation_detects_event_mutation_and_reversed_time(self) -> None:
        registration = _validated()
        ledger = evaluation.new_ledger(registration)
        slot = ledger.slots[0]
        ledger = evaluation.append_slot_event(
            ledger, slot.slot_id, "attempted", attempt_id="attempt-a",
            data={"sourceTimestamp": "2026-10-08T10:00:00Z"},
        )
        with self.assertRaisesRegex(evaluation.EvaluationError, "move backward"):
            evaluation.append_slot_event(
                ledger, slot.slot_id, "failed", attempt_id="attempt-a",
                data={"sourceTimestamp": "2026-10-08T09:59:00Z", "completion": False,
                      "authorityCorrect": None, "costs": _known_costs()},
            )
        ledger = evaluation.append_slot_event(
            ledger, slot.slot_id, "failed", attempt_id="attempt-a",
            data={"sourceTimestamp": "2026-10-08T10:01:00Z", "completion": False,
                  "authorityCorrect": None, "costs": _known_costs()},
        )
        evaluation.validate_ledger(ledger, registration)
        ledger.events[-1].data["costs"]["eur"] = 5.0
        with self.assertRaisesRegex(evaluation.EvaluationError, "data hash mismatch"):
            evaluation.validate_ledger(ledger, registration)


if __name__ == "__main__":
    unittest.main()
