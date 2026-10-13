# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for exact v6 reports and externally authenticated sources."""
from __future__ import annotations

import copy
from dataclasses import replace
from decimal import Decimal
import hashlib
import json
import unittest

from agent_braid import tooling_assisted_report as reporting
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_human_audit as audit
from agent_braid import tooling_registration_v6 as v6
from agent_braid.tooling_money import MoneySummary
from tests.test_tooling_evaluation import _complete_ledger, _known_costs, _sha
from tests.test_tooling_human_audit import _deterministic, _model, _human, _affirmations
from tests.test_tooling_registration_v6 import validated_v6


class SyntheticDocumentVerifier:
    """A test-only external boundary; no real observation is claimed by these tests."""
    def __init__(self, *, synthetic=False, mismatch=False):
        self.synthetic, self.mismatch = synthetic, mismatch
        self.calls = 0

    def verify_document(self, document, *, subject):
        self.calls += 1
        if self.synthetic:
            domain = "synthetic-control"
        elif subject.kind == "outcome":
            domain = "human-cli" if subject.slot_id.endswith(":cli") else "native-host"
        else:
            domain = {"deterministic": "deterministic-verification", "model": "model-review",
                      "human": "human-review", "adjudication": "human-review",
                      "escalation": "verified-incident", "setup": "cost-accounting",
                      "money": "cost-accounting"}[subject.kind]
        return reporting.DocumentAttestation(
            subject.kind, "0" * 64 if self.mismatch else subject.sha256,
            document.document_sha256, _sha("synthetic-decision:" + subject.sha256),
            "synthetic-test-source-verifier", "2026-10-14T00:00:00Z", domain)


def _instrument(registration, source=None):
    pin = registration.data["instrumentPins"]["technicalSummary"]
    return reporting.TechnicalSummaryInstrument(pin["sourceRef"], pin["sourceSha256"],
        pin["verifierRef"], pin["verifierSha256"], source)


def _documents(inputs):
    return tuple(reporting.EvidenceDocument(subject.kind, subject.sha256,
                 "private:synthetic-source:" + subject.sha256, _sha("document:" + subject.sha256))
                 for subject in inputs.subjects)


class AssistedReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registration = validated_v6()
        cls.complete_ledger = _complete_ledger(cls.registration)[0]

    def setUp(self):
        self.registration = copy.deepcopy(type(self).registration)
        self.selection = v6.audit_selection(self.registration)
        self.ledger = copy.deepcopy(type(self).complete_ledger)

    def records(self, *, human_sample=False):
        deterministic, models, humans = [], [], []
        for slot in self.ledger.slots:
            evidence = self.ledger.current_event(slot.slot_id).data["outputSha256"]
            deterministic.append(_deterministic(self.selection, slot.slot_id, evidenceSha256=evidence))
            models.extend(_model(self.selection, slot.slot_id, role, evidenceSha256=evidence)
                          for role in audit.MODEL_ROLES)
            if human_sample and slot.slot_id in self.selection.initial_slot_ids:
                humans.extend(_human(self.selection, slot.slot_id, role, evidenceSha256=evidence)
                              for role in self.selection.human_review_roles)
        return deterministic, models, humans

    def freeze(self, **changes):
        return reporting.freeze_report_inputs(self.registration, self.ledger,
            selection=self.selection, **changes)

    def build(self, inputs, *, source=None, documents=None):
        return reporting.build_assisted_report(inputs,
            instrument=_instrument(self.registration, source),
            documents=_documents(inputs) if documents is None else documents)

    def test_empty_108_ledger_preserves_population_unknowns_and_zero_authenticated_coverage(self):
        self.ledger = evaluation.new_ledger(self.registration)
        inputs = self.freeze()
        report = self.build(inputs)
        self.assertEqual({"intendedSlots": 108, "humanOperatedCliSlots": 36, "nativeAssistantSlots": 72}, report["population"])
        self.assertEqual(108, sum(group["notStarted"] for group in report["groups"]))
        self.assertTrue(all(group["intended"] == 18 for group in report["groups"]))
        self.assertIsNone(report["costs"]["actualAdditionalSpendEur"])
        self.assertFalse(report["coverage"]["automaticComplete"])
        self.assertEqual(0, report["coverage"]["sourceVerifiedTerminalSlots"])
        self.assertEqual(108, report["coverage"]["requiredHumanCases"])
        self.assertEqual("technical-incomplete", report["conclusion"]["status"])
        self.assertFalse(report["conclusion"]["utilityClaimEligible"])

    def test_declared_completed_results_and_model_labels_without_sources_never_conclude(self):
        deterministic, models, _ = self.records()
        report = self.build(self.freeze(deterministic_assessments=deterministic, model_reviews=models))
        self.assertEqual(108, sum(group["completed"] for group in report["groups"]))
        self.assertEqual(0, report["coverage"]["verifiedModelReviews"])
        self.assertEqual(216, report["declaredCoverage"]["modelReviews"])
        self.assertTrue(all(host["sourceVerifiedSuccesses"] == 0 for host in report["armCThresholds"]))
        self.assertTrue(all(host["successThresholdStatus"] == "pending" for host in report["armCThresholds"]))
        self.assertEqual(0, report["coverage"]["reviewedHumanCases"])

    def test_authenticated_sample36_keeps_remaining72_unreviewed_and_cash_unknown(self):
        deterministic, models, humans = self.records(human_sample=True)
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                             human_reviews=humans, setup_costs=_known_costs())
        source = SyntheticDocumentVerifier()
        report = self.build(inputs, source=source)
        coverage = report["coverage"]
        self.assertEqual((108, 216, 72), (coverage["verifiedDeterministicAssessments"],
                         coverage["verifiedModelReviews"], coverage["verifiedHumanReviews"]))
        self.assertEqual((36, 36, 72), (coverage["requiredHumanCases"], coverage["reviewedHumanCases"], coverage["unreviewedHumanCases"]))
        self.assertTrue(coverage["automaticComplete"])
        self.assertTrue(coverage["humanCoverageComplete"])
        self.assertEqual(108, coverage["sourceVerifiedTerminalSlots"])
        self.assertEqual([18, 18], [host["sourceVerifiedSuccesses"] for host in report["armCThresholds"]])
        self.assertEqual(["met", "met"], [host["successThresholdStatus"] for host in report["armCThresholds"]])
        self.assertIsNone(report["costs"]["actualAdditionalSpendEur"])
        self.assertIsNone(report["costs"]["observedTotals"]["eur"])
        self.assertEqual("cash-reconciliation-pending", report["conclusion"]["status"])
        self.assertFalse(report["conclusion"]["humanAcceptanceAsserted"])
        self.assertFalse(report["conclusion"]["founderApprovalAsserted"])
        self.assertNotIn("private:synthetic-source", str(dict(report)))
        self.assertGreater(source.calls, 0)

    def test_synthetic_or_mismatched_document_attestations_cannot_count_native_results(self):
        deterministic, models, _ = self.records()
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models)
        for verifier in (SyntheticDocumentVerifier(synthetic=True), SyntheticDocumentVerifier(mismatch=True)):
            with self.subTest(verifier=verifier):
                report = self.build(inputs, source=verifier)
                self.assertEqual(0, report["coverage"]["sourceVerifiedTerminalSlots"])
                self.assertFalse(report["coverage"]["automaticComplete"])

    def test_exact_pin_input_selection_and_current_output_binding_are_required(self):
        inputs = self.freeze()
        bad = replace(_instrument(self.registration), verifier_sha256="0" * 64)
        with self.assertRaises(reporting.AssistedReportError):
            reporting.build_assisted_report(inputs, instrument=bad)
        with self.assertRaises(reporting.AssistedReportError):
            reporting.build_assisted_report(inputs, instrument=None)
        with self.assertRaises(reporting.AssistedReportError):
            reporting.freeze_report_inputs(self.registration, self.ledger,
                selection=replace(self.selection, registration_sha256="0" * 64))
        deterministic, _, _ = self.records()
        deterministic[0]["evidenceSha256"] = "0" * 64
        with self.assertRaises(reporting.AssistedReportError):
            self.freeze(deterministic_assessments=deterministic)

    def test_critical_false_success_and_accepted_factual_inversion_suspend_all108(self):
        for mutation in (lambda record: record.update(oracleMatches=False),
                         lambda record: record["labels"].update(fidelity=False),
                         lambda record: record["labels"].update(authorityCorrect=False)):
            deterministic, models, _ = self.records()
            mutation(deterministic[0])
            inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models)
            report = self.build(inputs, source=SyntheticDocumentVerifier())
            self.assertTrue(report["safety"]["acceptanceSuspended"])
            self.assertEqual(108, report["coverage"]["requiredHumanCases"])
            self.assertEqual("suspended", report["conclusion"]["status"])

    def test_three_verified_unsuccessful_C_journeys_make16_of18_impossible(self):
        slots = [slot for slot in self.ledger.slots if slot.host == "codex" and slot.arm == "mcp-plus-skills"][:3]
        unsuccessful = {slot.slot_id for slot in slots}
        self.ledger = _complete_ledger(self.registration, successful_slots=unsuccessful)[0]
        deterministic, models, _ = self.records()
        for record in deterministic:
            if record["slotId"] in unsuccessful:
                record["labels"]["success"] = False
        for record in models:
            if record["slotId"] in unsuccessful:
                record["labels"]["success"] = False
        report = self.build(self.freeze(deterministic_assessments=deterministic, model_reviews=models),
                            source=SyntheticDocumentVerifier())
        codex = next(host for host in report["armCThresholds"] if host["host"] == "codex")
        self.assertEqual(15, codex["sourceVerifiedSuccesses"])
        self.assertEqual("not-met", codex["successThresholdStatus"])

    def test_frozen_inputs_and_report_are_immutable_and_summary_verification_recomputes(self):
        deterministic, models, _ = self.records()
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models)
        original = inputs.sha256
        deterministic[0]["labels"]["success"] = False
        self.registration.data["candidate"]["version"] = "drifted"
        self.assertEqual(original, inputs.sha256)
        verifier = _instrument(type(self).registration, SyntheticDocumentVerifier())
        documents = _documents(inputs)
        report = reporting.build_assisted_report(inputs, instrument=verifier, documents=documents)
        copied = report["coverage"]
        copied["verifiedModelReviews"] = 999
        self.assertEqual(216, report["coverage"]["verifiedModelReviews"])
        with self.assertRaises((AttributeError, TypeError)):
            report.sha256 = "0" * 64
        verified = verifier.verify_report(inputs, report, documents=documents)
        self.assertEqual(report.sha256, verified.report_sha256)
        changed = report.as_dict()
        changed["coverage"]["verifiedModelReviews"] = 999
        with self.assertRaises(reporting.AssistedReportError):
            verifier.verify_report(inputs, changed, documents=documents)

    def test_model_review_cannot_masquerade_as_human_even_before_document_verification(self):
        deterministic, models, humans = self.records(human_sample=True)
        humans[0]["reviewerId"] = models[0]["reviewerId"]
        with self.assertRaises(reporting.AssistedReportError):
            self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                        human_reviews=humans)

    def test_missing_source_for_one_human_does_not_allow_authenticated_adjudication_to_fill_pair(self):
        deterministic, models, humans = self.records(human_sample=True)
        humans[0]["labels"]["fidelity"] = False
        adjudication = {"schema": audit.ADJUDICATION_SCHEMA, "reviewerType": "human",
            "slotId": humans[0]["slotId"], "adjudicatorId": humans[0]["reviewerId"],
            "evidenceSha256": humans[0]["evidenceSha256"], "rubricSha256": self.selection.rubric_sha256,
            "labels": {"success": True, "authorityCorrect": True, "fidelity": True},
            "affirmedBy": _affirmations(humans)}
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                             human_reviews=humans, adjudications=(adjudication,))
        missing = next(subject.sha256 for subject in inputs.subjects if subject.kind == "human"
            and json.loads(subject.payload_bytes)["record"]["slotId"] == humans[0]["slotId"]
            and json.loads(subject.payload_bytes)["record"]["roleId"] == humans[0]["roleId"])
        documents = tuple(document for document in _documents(inputs) if document.subject_sha256 != missing)
        report = self.build(inputs, source=SyntheticDocumentVerifier(), documents=documents)
        self.assertEqual(35, report["coverage"]["reviewedHumanCases"])
        self.assertEqual(1, report["coverage"]["requiredUnreviewedHumanCases"])
        self.assertFalse(report["coverage"]["humanCoverageComplete"])

    def test_authenticated_critical_incident_still_suspends_when_its_assessment_source_is_missing(self):
        deterministic, models, _ = self.records()
        record = deterministic[0]
        event = {"eventType": "critical-incident", "slotId": record["slotId"],
            "reviewerType": "deterministic", "reviewerId": None, "incidentKind": "privacy",
            "evidenceSha256": record["evidenceSha256"], "rubricSha256": self.selection.rubric_sha256}
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                             escalation_events=(event,))
        missing = next(subject.sha256 for subject in inputs.subjects if subject.kind == "deterministic"
                       and subject.slot_id == record["slotId"])
        documents = tuple(document for document in _documents(inputs) if document.subject_sha256 != missing)
        report = self.build(inputs, source=SyntheticDocumentVerifier(), documents=documents)
        self.assertTrue(report["safety"]["acceptanceSuspended"])
        self.assertEqual(108, report["coverage"]["requiredHumanCases"])

    def test_unknown_completion_is_pending_without_fabricating_a_confirmed_incident(self):
        target = next(slot for slot in self.ledger.slots if slot.arm == "mcp-plus-skills")
        events = []
        for event in self.ledger.events:
            if event.slot_id == target.slot_id and event.status == "valid":
                payload = {**event.data, "completion": None, "authorityCorrect": None}
                digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                                  ensure_ascii=False).encode()).hexdigest()
                event = replace(event, data=payload, data_sha256=digest)
            events.append(event)
        self.ledger = replace(self.ledger, events=tuple(events))
        deterministic, models, _ = self.records()
        report = self.build(self.freeze(deterministic_assessments=deterministic, model_reviews=models),
                            source=SyntheticDocumentVerifier())
        host = next(item for item in report["armCThresholds"] if item["host"] == target.host)
        self.assertEqual(1, host["unknownSuccesses"])
        self.assertFalse(report["safety"]["acceptanceSuspended"])
        self.assertFalse(report["safety"]["absenceOfIncidentsEstablished"])

    def test_cash_zero_needs_independent_exact_roster_source_and_reservation_is_not_cash(self):
        deterministic, models, _ = self.records()
        money = MoneySummary(Decimal("0"), Decimal("0"), Decimal("0"), False, False,
            None, None, True, False, "pending", (), (), self.registration.sha256, _sha("money-roster"),
            (_sha("synthetic-cash-receipt"),), subscription_allocation_upper_bound_eur=Decimal("5.045"))
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models,
            monetary_summary=money, expected_monetary_roster_sha256=money.roster_sha256)
        declared = self.build(inputs)
        self.assertIsNone(declared["costs"]["actualAdditionalSpendEur"])
        actual = self.build(inputs, source=SyntheticDocumentVerifier())
        self.assertEqual("0", actual["costs"]["actualAdditionalSpendEur"])
        self.assertTrue(actual["costs"]["additionalCashWithinCap"])
        self.assertIsNone(actual["costs"]["allocatedSubscriptionCostEur"])
        self.assertIsNone(actual["costs"]["observedTotals"]["eur"])
        with self.assertRaises(reporting.AssistedReportError):
            self.freeze(monetary_summary=money, expected_monetary_roster_sha256="0" * 64)

    def test_failed_open_and_not_started_slots_keep_exact_108_denominators(self):
        self.ledger = evaluation.new_ledger(self.registration)
        failed, opened = self.ledger.slots[:2]
        self.ledger = evaluation.append_slot_event(self.ledger, failed.slot_id, "attempted",
            attempt_id="synthetic-failed-attempt", data={"sourceTimestamp": "2026-10-08T10:00:00Z"})
        self.ledger = evaluation.append_slot_event(self.ledger, failed.slot_id, "failed",
            attempt_id="synthetic-failed-attempt", data={"sourceTimestamp": "2026-10-08T10:01:00Z",
                "completion": False, "authorityCorrect": True, "costs": _known_costs(),
                "inputSha256": failed.fixture_sha256, "outputSha256": _sha("synthetic-failed-output")})
        self.ledger = evaluation.append_slot_event(self.ledger, opened.slot_id, "attempted",
            attempt_id="synthetic-open-attempt", data={"sourceTimestamp": "2026-10-08T10:02:00Z"})
        observation = _deterministic(self.selection, failed.slot_id,
            evidenceSha256=_sha("synthetic-failed-output"), outcome="failed", oracleMatches=False,
            labels={"success": False, "authorityCorrect": True, "fidelity": True})
        report = self.build(self.freeze(deterministic_assessments=(observation,)),
                            source=SyntheticDocumentVerifier())
        self.assertEqual(108, sum(group["intended"] for group in report["groups"]))
        self.assertEqual(106, sum(group["notStarted"] for group in report["groups"]))
        self.assertEqual(1, sum(group["inProgress"] for group in report["groups"]))
        self.assertEqual(1, sum(group["failed"] for group in report["groups"]))
        self.assertEqual(1, sum(group["sourceVerifiedFailed"] for group in report["groups"]))
        self.assertEqual(1, sum(group["declaredHistory"]["failed"] for group in report["groups"]))
        self.assertEqual(0, sum(group["completed"] for group in report["groups"]))
        self.assertFalse(report["safety"]["acceptanceSuspended"])

    def test_duplicate_or_unknown_documents_are_refused_before_external_verifier_calls(self):
        inputs = self.freeze()
        documents = _documents(inputs)
        source = SyntheticDocumentVerifier()
        for values in ((documents[0], documents[0]),
                       (replace(documents[0], subject_sha256="0" * 64),)):
            with self.assertRaises(reporting.AssistedReportError):
                self.build(inputs, source=source, documents=values)
        self.assertEqual(0, source.calls)

    def test_outcome_attestation_cannot_predate_its_original_source_observation(self):
        class OldVerifier(SyntheticDocumentVerifier):
            def verify_document(self, document, *, subject):
                result = super().verify_document(document, subject=subject)
                return replace(result, verified_at="2026-10-07T00:00:00Z")
        report = self.build(self.freeze(), source=OldVerifier())
        self.assertEqual(0, report["coverage"]["sourceVerifiedTerminalSlots"])

    def test_authenticated_human_discrepancy_expands_cell_without_inventing_a_missing_rating(self):
        deterministic, models, humans = self.records(human_sample=True)
        for human in humans[:2]:
            human["labels"]["success"] = False
        event = {"eventType": "confirmed-human-discrepancy", "slotId": humans[0]["slotId"],
            "reviewerType": "human", "reviewerIds": [human["reviewerId"] for human in humans[:2]],
            "evidenceSha256": humans[0]["evidenceSha256"], "rubricSha256": self.selection.rubric_sha256}
        inputs = self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                             human_reviews=humans, escalation_events=(event,))
        missing = next(subject.sha256 for subject in inputs.subjects if subject.kind == "human"
            and subject.slot_id == humans[0]["slotId"]
            and json.loads(subject.payload_bytes)["record"]["roleId"] == humans[0]["roleId"])
        documents = tuple(document for document in _documents(inputs) if document.subject_sha256 != missing)
        report = self.build(inputs, source=SyntheticDocumentVerifier(), documents=documents)
        self.assertEqual(38, report["coverage"]["requiredHumanCases"])
        self.assertEqual(35, report["coverage"]["reviewedHumanCases"])
        self.assertFalse(report["safety"]["acceptanceSuspended"])

    def test_confirmed_privacy_incident_cannot_claim_absence_of_incidents(self):
        deterministic, models, _ = self.records()
        record = deterministic[0]
        event = {"eventType": "critical-incident", "slotId": record["slotId"],
            "reviewerType": "deterministic", "reviewerId": None, "incidentKind": "privacy",
            "evidenceSha256": record["evidenceSha256"], "rubricSha256": self.selection.rubric_sha256}
        report = self.build(self.freeze(deterministic_assessments=deterministic, model_reviews=models,
                                       escalation_events=(event,)), source=SyntheticDocumentVerifier())
        self.assertTrue(report["safety"]["acceptanceSuspended"])
        self.assertFalse(report["safety"]["absenceOfIncidentsEstablished"])

    def test_authenticated_human_failure_overrules_arm_C_criterion_without_changing_source_counts(self):
        target = next(slot for slot in self.ledger.slots if slot.host == "codex"
            and slot.arm == "mcp-plus-skills" and slot.slot_id in self.selection.initial_slot_ids)
        fields = (("authorityCorrect", "authorityRequirementStatus", "resolvedHumanAuthorityFailures", "sourceVerifiedAuthorityCorrect"),
                  ("fidelity", "fidelityRequirementStatus", "resolvedHumanFidelityFailures", "sourceVerifiedFidelityCorrect"))
        for label, status, failures, source_count in fields:
            with self.subTest(label=label):
                deterministic, models, humans = self.records(human_sample=True)
                for human in humans:
                    if human["slotId"] == target.slot_id:
                        human["labels"][label] = False
                report = self.build(self.freeze(deterministic_assessments=deterministic,
                    model_reviews=models, human_reviews=humans), source=SyntheticDocumentVerifier())
                codex = next(host for host in report["armCThresholds"] if host["host"] == "codex")
                other = next(host for host in report["armCThresholds"] if host["host"] == "claude-code")
                self.assertEqual("not-met", codex[status])
                self.assertEqual(1, codex[failures])
                self.assertEqual(18, codex[source_count])
                self.assertEqual("met", other[status])
                self.assertEqual(0, other[failures])
                self.assertTrue(report["safety"]["acceptanceSuspended"])
                self.assertEqual("suspended", report["conclusion"]["status"])

    def test_non_arm_C_authenticated_human_failure_suspends_without_rejecting_arm_C_criterion(self):
        target = next(slot for slot in self.ledger.slots if slot.host == "codex"
            and slot.arm == "cli" and slot.slot_id in self.selection.initial_slot_ids)
        for label, status, failures in (("authorityCorrect", "authorityRequirementStatus", "resolvedHumanAuthorityFailures"),
                                        ("fidelity", "fidelityRequirementStatus", "resolvedHumanFidelityFailures")):
            with self.subTest(label=label):
                deterministic, models, humans = self.records(human_sample=True)
                for human in humans:
                    if human["slotId"] == target.slot_id:
                        human["labels"][label] = False
                report = self.build(self.freeze(deterministic_assessments=deterministic,
                    model_reviews=models, human_reviews=humans), source=SyntheticDocumentVerifier())
                self.assertEqual(["met", "met"], [host[status] for host in report["armCThresholds"]])
                self.assertEqual([0, 0], [host[failures] for host in report["armCThresholds"]])
                self.assertTrue(report["safety"]["acceptanceSuspended"])

    def test_jointly_adjudicated_authenticated_human_failure_rejects_arm_C_criterion(self):
        target = next(slot for slot in self.ledger.slots if slot.host == "codex"
            and slot.arm == "mcp-plus-skills" and slot.slot_id in self.selection.initial_slot_ids)
        for label, status in (("authorityCorrect", "authorityRequirementStatus"), ("fidelity", "fidelityRequirementStatus")):
            with self.subTest(label=label):
                deterministic, models, humans = self.records(human_sample=True)
                pair = [human for human in humans if human["slotId"] == target.slot_id]
                pair[0]["labels"][label] = False
                adjudication = {"schema": audit.ADJUDICATION_SCHEMA, "reviewerType": "human",
                    "slotId": target.slot_id, "adjudicatorId": pair[0]["reviewerId"],
                    "evidenceSha256": pair[0]["evidenceSha256"], "rubricSha256": self.selection.rubric_sha256,
                    "labels": {**pair[0]["labels"]}, "affirmedBy": _affirmations(pair)}
                report = self.build(self.freeze(deterministic_assessments=deterministic,
                    model_reviews=models, human_reviews=humans, adjudications=(adjudication,)),
                    source=SyntheticDocumentVerifier())
                codex = next(host for host in report["armCThresholds"] if host["host"] == "codex")
                self.assertEqual("not-met", codex[status])
                self.assertTrue(report["safety"]["acceptanceSuspended"])


if __name__ == "__main__":
    unittest.main()
