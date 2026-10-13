# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for prospective M4.5 sampling and assessment provenance."""

from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, replace
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_human_audit as audit
from tests.test_tooling_evaluation import _inputs, _registration, _sha


def _policy() -> dict:
    return {
        "schema": "agent-braid-m45-human-audit-policy-v1",
        "seed": "m45-human-audit-2026-10-13",
        "algorithm": "sha256-host-class-fixture-v1",
        "initialCases": 36,
        "reviewersPerCase": 2,
        "escalation": "cell-on-confirmed-discrepancy-cohort-on-critical-v1",
        "compactEvidence": True,
    }


def _selection():
    data = _registration()
    registration = evaluation.validate_registration(
        data, expected_candidate_sha256=data["candidate"]["sha256"],
        expected_input_hashes=_inputs(data),
    )
    return audit.freeze_selection(
        evaluation.generate_slots(registration), _policy(),
        expected_policy_sha256=audit.policy_sha256(_policy()),
        registration_sha256=registration.sha256,
        rubric_sha256=data["rubric"]["sha256"],
        human_review_roles=("planned-reviewer-one", "planned-reviewer-two"),
    )


def _labels(**changes) -> dict:
    return {"success": True, "authorityCorrect": True, "fidelity": True, **changes}


def _deterministic(selection, slot_id: str, **changes) -> dict:
    return {
        "schema": "agent-braid-m45-deterministic-assessment-v1",
        "reviewerType": "deterministic", "slotId": slot_id,
        "evidenceSha256": _sha(slot_id), "rubricSha256": selection.rubric_sha256,
        "outcome": "valid", "expectedOutcome": "valid", "oracleMatches": True,
        "evidenceComplete": True, "conclusive": True, "labels": _labels(),
        **changes,
    }


def _model(selection, slot_id: str, role: str, **changes) -> dict:
    return {
        "schema": "agent-braid-m45-model-review-v1", "reviewerType": "model",
        "model": "gpt-6-luna", "slotId": slot_id, "roleId": role,
        "reviewerId": "model-" + role, "independent": True,
        "contextSha256": _sha(slot_id + ":" + role),
        "evidenceSha256": _sha(slot_id), "rubricSha256": selection.rubric_sha256,
        "labels": _labels(), **changes,
    }


def _human(selection, slot_id: str, role: str, **changes) -> dict:
    return {
        "schema": "agent-braid-m45-human-review-v1", "reviewerType": "human",
        "slotId": slot_id, "roleId": role, "reviewerId": "human-" + role,
        "independent": True, "evidenceSha256": _sha(slot_id),
        "rubricSha256": selection.rubric_sha256, "labels": _labels(), **changes,
    }


def _automatic(selection):
    deterministic = [_deterministic(selection, slot.slot_id) for slot in selection.roster]
    models = [_model(selection, slot.slot_id, role)
              for slot in selection.roster for role in ("technical", "adversarial")]
    return deterministic, models


def _humans(selection, slot_ids):
    return [_human(selection, slot_id, role)
            for slot_id in slot_ids for role in selection.human_review_roles]


def _affirmations(humans) -> list[dict]:
    return [{"reviewerId": human["reviewerId"],
             "affirmationSha256": _sha("joint-consensus:" + human["slotId"] + ":" + human["reviewerId"])}
            for human in humans[:2]]


class AuditSelectionTests(unittest.TestCase):
    def test_fixed_sample_mirrors_one_instance_across_three_arms(self):
        selection = _selection()
        self.assertEqual(len(selection.roster), 108)
        self.assertEqual(len(selection.initial_slot_ids), 36)
        expected = {
            "codex": (3, 3, 3, 2, 2, 1),
            "claude-code": (3, 1, 2, 3, 1, 2),
        }
        for host in evaluation.HOSTS:
            for journey, instance in zip(evaluation.JOURNEY_CLASSES, expected[host]):
                chosen = [slot for slot in selection.roster
                          if slot.slot_id in selection.initial_slot_ids
                          and slot.host == host and slot.journey_class == journey]
                self.assertEqual({slot.fixture_id for slot in chosen}, {f"fixture-{journey}-{instance}"})
                self.assertEqual({slot.arm for slot in chosen}, set(evaluation.ARMS))

    def test_freeze_requires_the_registered_policy_hash_and_rejects_policy_swap(self):
        selection = _selection()
        kwargs = dict(registration_sha256=selection.registration_sha256,
                      rubric_sha256=selection.rubric_sha256,
                      human_review_roles=selection.human_review_roles)
        with self.assertRaises(TypeError):
            audit.freeze_selection(selection.roster, _policy(), **kwargs)
        for digest in (None, "", _sha("wrong-policy")):
            with self.subTest(digest=digest), self.assertRaises(audit.HumanAuditError):
                audit.freeze_selection(selection.roster, _policy(), expected_policy_sha256=digest, **kwargs)
        with self.assertRaises(audit.HumanAuditError):
            audit.freeze_selection(selection.roster, {**_policy(), "seed": "post-outcome-redraw"},
                                   expected_policy_sha256=selection.policy_sha256, **kwargs)

    def test_fixture_and_prompt_namespaces_are_disjoint(self):
        selection = _selection()
        fixture = selection.roster[0].fixture_id
        journey = selection.roster[0].journey_class
        roster = tuple(replace(slot, prompt_id=fixture) if slot.journey_class == journey else slot
                       for slot in selection.roster)
        with self.assertRaises(audit.HumanAuditError):
            audit.freeze_selection(roster, _policy(), expected_policy_sha256=selection.policy_sha256,
                registration_sha256=selection.registration_sha256, rubric_sha256=selection.rubric_sha256,
                human_review_roles=selection.human_review_roles)

    def test_input_order_is_irrelevant_and_all_bindings_change_identity(self):
        selection = _selection()
        again = audit.freeze_selection(
            tuple(reversed(selection.roster)), _policy(),
            expected_policy_sha256=selection.policy_sha256,
            registration_sha256=selection.registration_sha256,
            rubric_sha256=selection.rubric_sha256,
            human_review_roles=selection.human_review_roles,
        )
        self.assertEqual(again, selection)
        changed = audit.freeze_selection(
            selection.roster, _policy(), registration_sha256=_sha("other-registration"),
            expected_policy_sha256=selection.policy_sha256,
            rubric_sha256=selection.rubric_sha256, human_review_roles=selection.human_review_roles,
        )
        self.assertEqual(changed.initial_slot_ids, selection.initial_slot_ids)
        self.assertNotEqual(changed.sha256, selection.sha256)

    def test_policy_exact_shape_fixed_values_hash_and_snapshot(self):
        policy = _policy()
        validated = audit.validate_policy(policy)
        self.assertEqual(audit.policy_sha256(validated), audit.policy_sha256(policy))
        policy["seed"] = "changed-input"
        self.assertNotEqual(audit.policy_sha256(policy), validated.sha256)
        for field, value in (("initialCases", 108), ("reviewersPerCase", True),
                             ("compactEvidence", 1), ("algorithm", "random"),
                             ("escalation", "none"), ("seed", "")):
            with self.subTest(field=field):
                invalid = {**_policy(), field: value}
                with self.assertRaises(audit.HumanAuditError):
                    audit.validate_policy(invalid)
        with self.assertRaises(audit.HumanAuditError):
            audit.validate_policy({**_policy(), "allowModelHumans": True})
        with self.assertRaises(audit.HumanAuditError):
            audit.validate_policy(_policy(), expected_sha256=_sha("other"))

    def test_roster_rejects_duplicates_missing_cells_drift_and_non_counterbalanced_order(self):
        selection = _selection()
        original = list(selection.roster)
        bad_rosters = [original[:-1], [original[0], *original[1:-1], original[0]]]
        for field, value in (("host", "other"), ("arm", "other"),
                             ("fixture_sha256", _sha("drift")), ("prompt_sha256", _sha("drift")),
                             ("order_position", True), ("order_position", 2),
                             ("slot_id", "forged-slot")):
            roster = original.copy()
            roster[0] = replace(roster[0], **{field: value})
            bad_rosters.append(roster)
        for index, roster in enumerate(bad_rosters):
            with self.subTest(index=index), self.assertRaises(audit.HumanAuditError):
                audit.freeze_selection(roster, _policy(),
                    expected_policy_sha256=selection.policy_sha256,
                    registration_sha256=selection.registration_sha256,
                    rubric_sha256=selection.rubric_sha256,
                    human_review_roles=selection.human_review_roles)

    def test_selection_and_nested_state_immutable_and_forged_identity_rejected(self):
        selection = _selection()
        with self.assertRaises(FrozenInstanceError):
            selection.sha256 = _sha("forged")
        with self.assertRaises(FrozenInstanceError):
            selection.roster[0].host = "other"
        forged = replace(selection, initial_slot_ids=selection.initial_slot_ids[:-1])
        with self.assertRaises(audit.HumanAuditError):
            audit.assess_audit(forged, [], [])

    def test_role_rubric_seed_and_complete_roster_identity_are_pinned(self):
        selection = _selection()
        variations = (
            {"rubric_sha256": _sha("different-rubric")},
            {"human_review_roles": ("other-human-one", "other-human-two")},
            {"policy": {**_policy(), "seed": "a-new-prospective-cohort"}},
        )
        for variation in variations:
            values = {"roster": selection.roster, "policy": _policy(),
                      "registration_sha256": selection.registration_sha256,
                      "rubric_sha256": selection.rubric_sha256,
                      "human_review_roles": selection.human_review_roles, **variation}
            values["expected_policy_sha256"] = audit.policy_sha256(values["policy"])
            with self.subTest(variation=variation):
                self.assertNotEqual(audit.freeze_selection(**values).sha256, selection.sha256)
        fixture = selection.roster[0].fixture_id
        roster = tuple(replace(slot, fixture_sha256=_sha("new-fixture-contents"))
                       if slot.fixture_id == fixture else slot for slot in selection.roster)
        changed = audit.freeze_selection(roster, _policy(),
            expected_policy_sha256=selection.policy_sha256,
            registration_sha256=selection.registration_sha256, rubric_sha256=selection.rubric_sha256,
            human_review_roles=selection.human_review_roles)
        self.assertNotEqual(changed.roster_sha256, selection.roster_sha256)
        self.assertNotEqual(changed.sha256, selection.sha256)
        # Selection ranks fixture IDs, so hashes changing cannot secretly redraw it.
        self.assertEqual(changed.initial_slot_ids, selection.initial_slot_ids)


class AuditAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.selection = _selection()
        self.deterministic, self.models = _automatic(self.selection)
        self.unselected = next(slot.slot_id for slot in self.selection.roster
                               if slot.slot_id not in self.selection.initial_slot_ids)

    def assess(self, humans=(), **kwargs):
        return audit.assess_audit(self.selection, self.deterministic, self.models,
                                 human_reviews=humans, **kwargs)

    def test_successful_automatic_cohort_requires_only_sample_and_no_implicit_humans(self):
        result = self.assess()
        self.assertTrue(result.automatic_complete)
        self.assertEqual(result.required_slot_ids, self.selection.initial_slot_ids)
        self.assertFalse(result.human_coverage_complete)
        self.assertEqual(len(result.unreviewed_slot_ids), 108)
        self.assertFalse(result.acceptance_suspended)

    def test_two_independent_humans_cover_36_while_remaining_72_stay_unreviewed(self):
        result = self.assess(_humans(self.selection, self.selection.initial_slot_ids))
        self.assertTrue(result.human_coverage_complete)
        self.assertEqual(len(result.reviewed_slot_ids), 36)
        self.assertEqual(len(result.unreviewed_slot_ids), 72)
        self.assertEqual(result.required_unreviewed_slot_ids, ())
        self.assertEqual(result.as_dict()["intendedCases"], 108)

    def test_expected_refusal_is_not_automatically_escalated(self):
        row = next(item for item in self.deterministic if item["slotId"] == self.unselected)
        row.update(outcome="refused", expectedOutcome="refused", labels=_labels(success=False))
        for item in self.models:
            if item["slotId"] == self.unselected:
                item["labels"] = _labels(success=False)
        self.assertNotIn(self.unselected, self.assess().required_slot_ids)

    def test_every_unexpected_registered_outcome_is_audited(self):
        for outcome in evaluation.SLOT_STATUSES:
            if outcome == "valid":
                continue
            with self.subTest(outcome=outcome):
                deterministic = copy.deepcopy(self.deterministic)
                next(row for row in deterministic if row["slotId"] == self.unselected).update(
                    outcome=outcome, labels=_labels(success=False))
                result = audit.assess_audit(self.selection, deterministic, self.models)
                self.assertIn(self.unselected, result.required_slot_ids)
                self.assertIn("unexpected-outcome", dict(result.reasons_by_slot)[self.unselected])

    def test_false_success_on_failed_oracle_or_unexpected_failure_suspends_cohort(self):
        for changes in ({"oracleMatches": False}, {"outcome": "invalid"}, {"outcome": "failed"},
                        {"outcome": "refused"}, {"outcome": "cancelled"}):
            with self.subTest(changes=changes):
                deterministic = copy.deepcopy(self.deterministic)
                next(row for row in deterministic if row["slotId"] == self.unselected).update(changes)
                result = audit.assess_audit(self.selection, deterministic, self.models)
                self.assertTrue(result.acceptance_suspended)
                self.assertEqual(len(result.required_slot_ids), 108)

    def test_outcome_enums_and_identifier_types_fail_closed(self):
        for outcome in ("unknown-state", {}, [], 5, "x" * 1000):
            with self.subTest(outcome=outcome), self.assertRaises(audit.HumanAuditError):
                audit.validate_deterministic_assessment({**self.deterministic[0], "outcome": outcome})
        humans = _humans(self.selection, (self.unselected,))
        adjudication = {"schema": "agent-braid-m45-human-adjudication-v1", "reviewerType": "human",
                        "slotId": self.unselected, "adjudicatorId": {},
                        "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
                        "labels": _labels(), "affirmedBy": _affirmations(humans)}
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, adjudications=(adjudication,))
        event = {"eventType": "critical-incident", "slotId": self.unselected,
                 "incidentKind": "privacy", "reviewerType": "model", "reviewerId": {},
                 "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256}
        with self.assertRaises(audit.HumanAuditError):
            self.assess(escalation_events=(event,))

    def test_detects_each_failure_and_retains_all_denominators(self):
        changes = (
            {"oracleMatches": False}, {"outcome": "failed"}, {"outcome": "refused"},
            {"evidenceComplete": False}, {"conclusive": False},
            {"oracleMatches": None}, {"labels": _labels(success=None)},
        )
        for change in changes:
            with self.subTest(change=change):
                deterministic = copy.deepcopy(self.deterministic)
                next(item for item in deterministic if item["slotId"] == self.unselected).update(change)
                if "labels" not in change:
                    next(item for item in deterministic if item["slotId"] == self.unselected)["labels"] = _labels(success=False)
                result = audit.assess_audit(self.selection, deterministic, self.models)
                self.assertIn(self.unselected, result.required_slot_ids)
                self.assertEqual(len(result.required_slot_ids), 37)
                self.assertEqual(len(result.unreviewed_slot_ids), 108)

    def test_missing_assessments_and_model_disagreement_are_required(self):
        deterministic = [item for item in self.deterministic if item["slotId"] != self.unselected]
        result = audit.assess_audit(self.selection, deterministic, self.models)
        self.assertFalse(result.automatic_complete)
        self.assertIn(self.unselected, result.required_slot_ids)
        models = copy.deepcopy(self.models)
        next(item for item in models if item["slotId"] == self.unselected)["labels"] = _labels(fidelity=False)
        result = audit.assess_audit(self.selection, self.deterministic, models)
        self.assertIn(self.unselected, result.required_slot_ids)
        models = [item for item in self.models if item["slotId"] != self.unselected]
        result = audit.assess_audit(self.selection, self.deterministic, models)
        self.assertFalse(result.automatic_complete)
        self.assertIn(self.unselected, result.required_slot_ids)

    def test_all_missing_automatic_results_require_108_and_do_not_count_complete(self):
        result = audit.assess_audit(self.selection, [], [])
        self.assertEqual(len(result.required_slot_ids), 108)
        self.assertFalse(result.automatic_complete)

    def test_models_must_be_luna_separate_roles_agents_and_contexts(self):
        mutations = ({"model": "gpt-6.1-sol"}, {"reviewerType": "human"},
                     {"roleId": "human-role"}, {"independent": False},
                     {"reviewerId": "model-adversarial"})
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                models = copy.deepcopy(self.models)
                models[0].update(mutation)
                with self.assertRaises(audit.HumanAuditError):
                    audit.assess_audit(self.selection, self.deterministic, models)
        models = copy.deepcopy(self.models)
        models[0]["contextSha256"] = models[1]["contextSha256"]
        with self.assertRaises(audit.HumanAuditError):
            audit.assess_audit(self.selection, self.deterministic, models)

    def test_human_spoofing_missing_labels_duplicate_people_and_role_drift_rejected(self):
        humans = _humans(self.selection, self.selection.initial_slot_ids)
        mutations = ({"reviewerType": "model"}, {"model": "gpt-6-luna"},
                     {"roleId": "unknown-role"}, {"independent": False},
                     {"reviewerId": humans[1]["reviewerId"]})
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(humans)
                changed[0].update(mutation)
                with self.assertRaises(audit.HumanAuditError):
                    self.assess(changed)
        changed = copy.deepcopy(humans)
        changed[2]["reviewerId"] = "different-human-for-same-frozen-role"
        with self.assertRaises(audit.HumanAuditError):
            self.assess(changed)
        humans[0]["labels"] = _labels(fidelity=None)
        self.assertFalse(self.assess(humans).human_coverage_complete)

    def test_evidence_and_rubric_drift_unknown_slots_and_duplicate_assessments_rejected(self):
        for mutation in ({"evidenceSha256": _sha("drift")},
                         {"rubricSha256": _sha("drift")}, {"slotId": "foreign"}):
            with self.subTest(mutation=mutation):
                models = copy.deepcopy(self.models)
                models[0].update(mutation)
                with self.assertRaises(audit.HumanAuditError):
                    audit.assess_audit(self.selection, self.deterministic, models)
        with self.assertRaises(audit.HumanAuditError):
            audit.assess_audit(self.selection, [*self.deterministic, self.deterministic[0]], self.models)

    def test_confirmed_human_discrepancy_expands_only_host_class_arm_cell(self):
        humans = _humans(self.selection, (self.unselected,))
        event = {
            "eventType": "confirmed-human-discrepancy", "slotId": self.unselected,
            "reviewerType": "human", "reviewerIds": [item["reviewerId"] for item in humans],
            "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
        }
        result = self.assess(humans, escalation_events=(event,))
        slot = next(slot for slot in self.selection.roster if slot.slot_id == self.unselected)
        cell = {item.slot_id for item in self.selection.roster
                if (item.host, item.journey_class, item.arm) == (slot.host, slot.journey_class, slot.arm)}
        self.assertEqual(set(result.required_slot_ids), set(self.selection.initial_slot_ids) | cell)
        self.assertEqual(len(result.required_slot_ids), 38)
        self.assertFalse(result.acceptance_suspended)
        with self.assertRaises(audit.HumanAuditError):
            self.assess((), escalation_events=(event,))
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, escalation_events=({**event, "reviewerType": "model"},))

    def test_reviewer_id_count_is_bounded_before_iteration_or_serialization(self):
        iterated = []

        class OversizedReviewerIds(list):
            def __iter__(self):
                iterated.append(True)
                return super().__iter__()

        humans = _humans(self.selection, (self.unselected,))
        event = {
            "eventType": "confirmed-human-discrepancy", "slotId": self.unselected,
            "reviewerType": "human", "reviewerIds": OversizedReviewerIds(("a", "b", "c")),
            "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
        }
        with self.assertRaisesRegex(audit.HumanAuditError, "exactly two"):
            self.assess(humans, escalation_events=(event,))
        self.assertEqual(iterated, [])

    def test_critical_incidents_expand_whole_cohort_and_suspend_acceptance(self):
        for kind in ("authority", "privacy", "false-success"):
            event = {
                "eventType": "critical-incident", "slotId": self.unselected,
                "incidentKind": kind, "reviewerType": "deterministic", "reviewerId": None,
                "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
            }
            with self.subTest(kind=kind):
                result = self.assess(escalation_events=(event,))
                self.assertEqual(len(result.required_slot_ids), 108)
                self.assertTrue(result.acceptance_suspended)

    def test_confirmed_authority_failure_suspends_without_extra_incident_flag(self):
        row = next(item for item in self.deterministic if item["slotId"] == self.unselected)
        row["labels"] = _labels(authorityCorrect=False)
        deterministic_failure = self.assess()
        self.assertTrue(deterministic_failure.acceptance_suspended)
        self.assertEqual(len(deterministic_failure.required_slot_ids), 108)
        row["labels"] = _labels()
        humans = _humans(self.selection, (self.unselected,))
        for human in humans:
            human["labels"] = _labels(authorityCorrect=False)
        human_failure = self.assess(humans)
        self.assertTrue(human_failure.acceptance_suspended)
        self.assertEqual(len(human_failure.required_slot_ids), 108)

    def test_model_authority_suspicion_remains_model_judgment(self):
        for model in self.models:
            if model["slotId"] == self.unselected:
                model["labels"] = _labels(authorityCorrect=False)
        result = self.assess()
        self.assertFalse(result.acceptance_suspended)
        self.assertEqual(len(result.required_slot_ids), 37)

    def test_human_disagreement_requires_bound_human_adjudication(self):
        humans = _humans(self.selection, self.selection.initial_slot_ids)
        humans[0]["labels"] = _labels(success=False)
        result = self.assess(humans)
        self.assertFalse(result.human_coverage_complete)
        slot_id = humans[0]["slotId"]
        adjudication = {
            "schema": "agent-braid-m45-human-adjudication-v1", "reviewerType": "human",
            "slotId": slot_id, "adjudicatorId": humans[0]["reviewerId"],
            "evidenceSha256": _sha(slot_id), "rubricSha256": self.selection.rubric_sha256,
            "labels": _labels(success=False),
            "affirmedBy": _affirmations(humans),
        }
        adjudicated = self.assess(humans, adjudications=(adjudication,))
        self.assertFalse(adjudicated.human_coverage_complete)
        self.assertEqual(len(adjudicated.required_slot_ids), 38)
        additional = set(adjudicated.required_slot_ids) - set(self.selection.initial_slot_ids)
        completed = self.assess([*humans, *_humans(self.selection, additional)], adjudications=(adjudication,))
        self.assertTrue(completed.human_coverage_complete)
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, adjudications=({**adjudication, "reviewerType": "model"},))

    def test_human_adjudication_requires_both_original_reviewers_joint_affirmation(self):
        humans = _humans(self.selection, (self.unselected,))
        humans[0]["labels"] = _labels(fidelity=False)
        consensus = {
            "schema": "agent-braid-m45-human-adjudication-v1", "reviewerType": "human",
            "slotId": self.unselected, "adjudicatorId": humans[0]["reviewerId"],
            "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
            "labels": _labels(fidelity=False), "affirmedBy": _affirmations(humans),
        }
        self.assertIn(self.unselected, self.assess(humans, adjudications=(consensus,)).reviewed_slot_ids)
        unilateral = {key: value for key, value in consensus.items() if key != "affirmedBy"}
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, adjudications=(unilateral,))
        for affirmations in (
            consensus["affirmedBy"][:1],
            [consensus["affirmedBy"][0], consensus["affirmedBy"][0]],
            [consensus["affirmedBy"][0], {**consensus["affirmedBy"][1], "reviewerId": "foreign-human"}],
            [consensus["affirmedBy"][0], {**consensus["affirmedBy"][1],
                                           "affirmationSha256": consensus["affirmedBy"][0]["affirmationSha256"]}],
        ):
            with self.subTest(affirmations=affirmations), self.assertRaises(audit.HumanAuditError):
                self.assess(humans, adjudications=({**consensus, "affirmedBy": affirmations},))

    def test_two_humans_confirming_label_discrepancy_expand_cell_without_extra_flag(self):
        humans = _humans(self.selection, (self.unselected,))
        for human in humans:
            human["labels"] = _labels(fidelity=False)
        result = self.assess(humans)
        self.assertEqual(len(result.required_slot_ids), 38)
        slot = next(slot for slot in self.selection.roster if slot.slot_id == self.unselected)
        cell = {item.slot_id for item in self.selection.roster
                if (item.host, item.journey_class, item.arm) == (slot.host, slot.journey_class, slot.arm)}
        self.assertEqual(set(result.required_slot_ids), set(self.selection.initial_slot_ids) | cell)

    def test_model_labels_conflicting_with_oracle_are_audited_even_when_models_agree(self):
        for model in self.models:
            if model["slotId"] == self.unselected:
                model["labels"] = _labels(fidelity=False)
        self.assertIn(self.unselected, self.assess().required_slot_ids)

    def test_adjudication_cannot_overwrite_agreeing_labels_or_fill_missing_human_labels(self):
        humans = _humans(self.selection, (self.unselected,))
        adjudication = {
            "schema": "agent-braid-m45-human-adjudication-v1", "reviewerType": "human",
            "slotId": self.unselected, "adjudicatorId": humans[0]["reviewerId"],
            "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
            "labels": _labels(success=False),
            "affirmedBy": _affirmations(humans),
        }
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, adjudications=(adjudication,))
        humans[0]["labels"] = _labels(success=None)
        result = self.assess(humans, adjudications=(adjudication,))
        self.assertIn(self.unselected, result.required_unreviewed_slot_ids)

    def test_validated_records_are_immutable_and_preserve_provenance(self):
        record = audit.validate_model_review(self.models[0])
        self.assertEqual(record.as_dict()["reviewerType"], "model")
        self.assertEqual(record.as_dict()["model"], "gpt-6-luna")
        with self.assertRaises(FrozenInstanceError):
            record.labels.success = False
        self.assertTrue(audit.assess_audit(
            self.selection, self.deterministic, [record, *self.models[1:]],
        ).automatic_complete)

    def test_late_validation_error_preserves_all_caller_owned_inputs(self):
        humans = _humans(self.selection, self.selection.initial_slot_ids)
        values = (self.deterministic, self.models, humans)
        before = copy.deepcopy(values)
        invalid_event = {
            "eventType": "critical-incident", "slotId": self.unselected,
            "incidentKind": "privacy", "reviewerType": "model", "reviewerId": "foreign-model",
            "evidenceSha256": _sha(self.unselected), "rubricSha256": self.selection.rubric_sha256,
        }
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans, escalation_events=(invalid_event,))
        self.assertEqual(values, before)

    def test_wire_labels_reject_numeric_booleans_and_records_snapshot_nested_inputs(self):
        row = copy.deepcopy(self.models[0])
        row["labels"]["success"] = 1
        with self.assertRaises(audit.HumanAuditError):
            audit.validate_model_review(row)
        row["labels"]["success"] = True
        record = audit.validate_model_review(row)
        row["labels"]["success"] = False
        self.assertTrue(record.labels.success)
        serialized = record.as_dict()
        serialized["labels"]["success"] = False
        self.assertTrue(record.labels.success)

    def test_model_identity_relabelled_human_is_rejected_across_roles(self):
        humans = _humans(self.selection, self.selection.initial_slot_ids)
        for human in humans:
            if human["roleId"] == self.selection.human_review_roles[0]:
                human["reviewerId"] = self.models[0]["reviewerId"]
        with self.assertRaises(audit.HumanAuditError):
            self.assess(humans)


if __name__ == "__main__":
    unittest.main()
