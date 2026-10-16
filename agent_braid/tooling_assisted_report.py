# SPDX-License-Identifier: AGPL-3.0-only
"""Exact v6 technical reports with separate observation and reviewer provenance.

An installed external verifier authenticates source documents. This module checks
their exact frozen subjects and derives a reproducible summary; matching hashes,
instrument pins and declared reviewers never establish approval or source truth.
"""
from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json
import math
import re
from typing import Any, Protocol

from . import tooling_evaluation as evaluation
from . import tooling_human_audit as audit
from . import tooling_registration_v6 as v6
from .tooling_money import MoneySummary


SCHEMA = "agent-braid-m45-assisted-report-v1"
INPUT_SCHEMA = "agent-braid-m45-assisted-report-inputs-v1"
MAX_INPUT_BYTES = 8 * 1024 * 1024
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_TOKEN = object()
_DOMAINS = {"deterministic": "deterministic-verification", "model": "model-review",
            "human": "human-review", "adjudication": "human-review",
            "escalation": "verified-incident", "setup": "cost-accounting", "money": "cost-accounting"}
_LIMITS = (
    "Source authenticity is supplied by the installed external document verifier; pins and hashes establish identity only.",
    "Model judgments, deterministic observations and actual human ratings keep separate provenance.",
    "The sampled human audit is not full-cohort human labeling or validation of a general evaluator.",
    "Unknown cash, measurements and safety labels remain unknown; subscription reservation is not actual cash.",
    "This technical report never asserts utility, human acceptance, founder approval or milestone closure.",
)


class AssistedReportError(ValueError):
    """Report inputs, source provenance, or installed instrument binding is invalid."""


@dataclass(frozen=True)
class ReportSubject:
    kind: str
    slot_id: str | None
    sha256: str
    payload_bytes: bytes


@dataclass(frozen=True)
class EvidenceDocument:
    kind: str
    subject_sha256: str
    reference: str
    document_sha256: str


@dataclass(frozen=True)
class DocumentAttestation:
    kind: str
    subject_sha256: str
    document_sha256: str
    decision_sha256: str
    verifier_id: str
    verified_at: str
    domain: str


class DocumentVerifier(Protocol):
    """Authenticate actual facts, identities and provenance, not just a digest.

    For an outcome, check the original session/CLI receipt, its trusted outcome
    attestation, exact current ledger event and real native/human operation. For a
    rating, check the actual independent reviewer/role/context and original record.
    Cost sources require exact monetary-roster/activity coverage and measurements.
    Return ``synthetic-control`` for software controls, never an actual domain.
    """
    def verify_document(self, document: EvidenceDocument, *, subject: ReportSubject) -> DocumentAttestation: ...


class _FrozenMapping(Mapping[str, Any]):
    __slots__ = ("_encoded",)

    def __init__(self, value, *, _token=None):
        if _token is not _TOKEN:
            raise TypeError("frozen report values must be created by their builder")
        object.__setattr__(self, "_encoded", _json(value))

    def __setattr__(self, name, value):
        raise AttributeError("report values are immutable")

    def __getitem__(self, key):
        return self.as_dict()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self.as_dict())

    def __len__(self):
        return len(self.as_dict())

    def as_dict(self):
        return json.loads(self._encoded)


class ReportInputs(_FrozenMapping):
    """Immutable copies of independently supplied records and exact input hashes."""
    @property
    def sha256(self):
        return _sha_bytes(self._encoded)

    @property
    def subjects(self) -> tuple[ReportSubject, ...]:
        data = self.as_dict()
        subjects = []
        base = {"registrationSha256": data["registrationSha256"],
                "ledgerSha256": data["ledgerSha256"], "auditSelectionSha256": data["selection"]["sha256"]}
        for kind in ("outcome", "deterministic", "model", "human", "adjudication", "escalation", "setup", "money"):
            for record in data["records"][kind]:
                raw = _json({**base, "kind": kind, "record": record})
                subjects.append(ReportSubject(kind, record.get("slotId"), _sha_bytes(raw), raw))
        return tuple(subjects)


class AssistedReport(_FrozenMapping):
    @property
    def sha256(self):
        return self["reportSha256"]


@dataclass(frozen=True)
class SummaryVerification:
    input_sha256: str
    document_manifest_sha256: str
    report_sha256: str
    instrument_identity_sha256: str
    source_verified_terminal_slots: int


@dataclass(frozen=True)
class TechnicalSummaryInstrument:
    """Concrete deterministic technicalSummary instrument with external sources.

    The four explicit identity attributes must equal the registered instrument
    pin. An absent verifier produces an incomplete report, never authenticated
    observations. The implementation is responsible only for subject binding and
    summary derivation; source-verifier installation/trust is an external gate.
    """
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str
    document_verifier: DocumentVerifier | None = None

    def verify_report(self, inputs: ReportInputs, report: Mapping[str, Any], *,
                      documents: Sequence[EvidenceDocument] = ()) -> SummaryVerification:
        """Reauthenticate frozen documents and independently recompute the report."""
        if not isinstance(inputs, ReportInputs) or not isinstance(report, Mapping):
            raise AssistedReportError("report verification requires an exact report object")
        value = json.loads(_json(dict(report)))
        body = {key: item for key, item in value.items() if key != "reportSha256"}
        if value.get("reportSha256") != _digest(body) or value.get("inputSha256") != inputs.sha256:
            raise AssistedReportError("report digest or frozen input identity differs")
        expected = build_assisted_report(inputs, instrument=self, documents=documents)
        if value != expected.as_dict():
            raise AssistedReportError("report differs from the independently recomputed technical summary")
        return SummaryVerification(inputs.sha256, expected["documentManifestSha256"], expected.sha256,
            expected["instrumentIdentitySha256"], expected["coverage"]["sourceVerifiedTerminalSlots"])


def freeze_report_inputs(
    registration: evaluation.ValidatedRegistration, ledger: evaluation.EvaluationLedger, *,
    selection: audit.AuditSelection, deterministic_assessments: Sequence[Any] = (),
    model_reviews: Sequence[Any] = (), human_reviews: Sequence[Any] = (),
    adjudications: Sequence[Mapping[str, Any]] = (), escalation_events: Sequence[Mapping[str, Any]] = (),
    setup_costs: Mapping[str, Any] | None = None, monetary_summary: MoneySummary | None = None,
    expected_monetary_roster_sha256: str | None = None,
) -> ReportInputs:
    """Freeze v6 source inputs without authenticating facts or reviewer identities."""
    try:
        if not isinstance(registration, evaluation.ValidatedRegistration):
            raise AssistedReportError("a validated v6 registration is required")
        frozen_selection = v6.audit_selection(registration)
        if not isinstance(selection, audit.AuditSelection) or selection.as_dict() != frozen_selection.as_dict():
            raise AssistedReportError("audit selection differs from the exact registered v6 selection")
        evaluation.validate_ledger(ledger, registration)
        deterministic = _validated_records(deterministic_assessments, audit.validate_deterministic_assessment, 108)
        models = _validated_records(model_reviews, audit.validate_model_review, 216)
        humans = _validated_records(human_reviews, audit.validate_human_review, 216)
        adjudications = _copy_records(adjudications, 108)
        escalations = _copy_records(escalation_events, 324)
        # Reject malformed or cross-provenance declarations even before any source
        # verifier is consulted. This assessment is not obtained human evidence.
        audit.assess_audit(frozen_selection, deterministic, models, human_reviews=humans,
                          adjudications=adjudications, escalation_events=escalations)
        events = []
        current = {slot.slot_id: ledger.current_event(slot.slot_id) for slot in ledger.slots}
        for slot_id, event in current.items():
            if event is not None and event.status in evaluation.FINAL_STATUSES:
                events.append({"slotId": slot_id, "sequence": event.sequence, "attemptId": event.attempt_id,
                               "status": event.status, "data": dict(event.data), "dataSha256": event.data_sha256})
        for record in [*deterministic, *models, *humans, *adjudications, *escalations]:
            event = current.get(record["slotId"])
            if (event is None or event.status not in evaluation.FINAL_STATUSES
                    or event.data.get("outputSha256") != record["evidenceSha256"]):
                raise AssistedReportError("assessment evidence differs from the exact current terminal output")
        for record in deterministic:
            if record["outcome"] != current[record["slotId"]].status:
                raise AssistedReportError("deterministic observation status differs from the current ledger outcome")
        setup = [] if setup_costs is None else [_measurements(setup_costs)]
        money = []
        if monetary_summary is not None:
            if not isinstance(monetary_summary, MoneySummary):
                raise AssistedReportError("a typed external monetary summary is required")
            _hash(expected_monetary_roster_sha256)
            if (monetary_summary.registration_sha256 != registration.sha256
                    or monetary_summary.roster_sha256 != expected_monetary_roster_sha256):
                raise AssistedReportError("monetary summary registration or exact monetary roster differs")
            money = [json.loads(_json(monetary_summary.as_dict()))]
        elif expected_monetary_roster_sha256 is not None:
            _hash(expected_monetary_roster_sha256)
        ledger_data = ledger.as_dict()
        data = {"schemaVersion": INPUT_SCHEMA, "registration": registration.data,
                "registrationSha256": registration.sha256, "ledger": ledger_data,
                "ledgerSha256": _digest(ledger_data), "selection": frozen_selection.as_dict(),
                "expectedMonetaryRosterSha256": expected_monetary_roster_sha256,
                "records": {"outcome": events, "deterministic": deterministic, "model": models,
                            "human": humans, "adjudication": adjudications, "escalation": escalations,
                            "setup": setup, "money": money}}
        return ReportInputs(data, _token=_TOKEN)
    except AssistedReportError:
        raise
    except (ValueError, TypeError, AttributeError, KeyError) as exc:
        raise AssistedReportError("v6 report inputs or assessment provenance are invalid") from exc


def build_assisted_report(inputs: ReportInputs, *, instrument: TechnicalSummaryInstrument,
                          documents: Sequence[EvidenceDocument] = ()) -> AssistedReport:
    """Derive exact technical status without legacy full-human utility claims."""
    if not isinstance(inputs, ReportInputs) or not isinstance(instrument, TechnicalSummaryInstrument):
        raise AssistedReportError("frozen report inputs and a pinned technicalSummary instrument are required")
    data = inputs.as_dict()
    registration, ledger = _restore_inputs(data)
    try:
        v6.require_instrument_identity(instrument, registration, "technicalSummary")
    except evaluation.EvaluationError as exc:
        raise AssistedReportError("technicalSummary instrument differs from its registered identity pin") from exc
    subjects = inputs.subjects
    document_map, document_hash = _document_map(documents, subjects)
    authenticated, domains = _authenticate(instrument, subjects, document_map)
    records = data["records"]
    verified = {kind: [] for kind in records}
    for subject in subjects:
        if subject.sha256 in authenticated:
            verified[subject.kind].append(json.loads(subject.payload_bytes)["record"])
    selection = v6.audit_selection(registration)
    # Filter adjudication/event dependencies before deriving authenticated audit
    # coverage. Unauthenticated declaration pairs cannot authenticate each other.
    assessment, verified_critical = _authenticated_audit(selection, verified)
    outcomes = {record["slotId"]: record for record in verified["outcome"]}
    deterministic = {record["slotId"]: audit.validate_deterministic_assessment(record)
                     for record in verified["deterministic"]}
    resolved_humans = _resolved_human_labels(assessment, verified)
    safety = _safety(outcomes, deterministic, resolved_humans,
                     assessment.acceptance_suspended or verified_critical)
    all_slots = {slot.slot_id for slot in ledger.slots}
    inconclusive_outcomes = {slot for slot, event in outcomes.items()
                             if event["data"]["completion"] is None or event["data"]["authorityCorrect"] is None}
    required = set(assessment.required_slot_ids) | (all_slots - set(outcomes)) | inconclusive_outcomes
    confirmed_cells = set()
    slots_by_id = {slot.slot_id: slot for slot in ledger.slots}
    for event in verified["escalation"]:
        if event["eventType"] == "confirmed-human-discrepancy":
            selected = slots_by_id[event["slotId"]]
            confirmed_cells.update(slot.slot_id for slot in ledger.slots
                if (slot.host, slot.journey_class, slot.arm) == (selected.host, selected.journey_class, selected.arm))
    required.update(confirmed_cells)
    if safety["acceptanceSuspended"]:
        required = all_slots
    reviewed = set(assessment.reviewed_slot_ids)
    coverage = {"sourceVerifiedTerminalSlots": len(outcomes),
                "sourceVerifiedHumanCliSlots": sum(slot.arm == "cli" and slot.slot_id in outcomes for slot in ledger.slots),
                "sourceVerifiedNativeSlots": sum(slot.arm != "cli" and slot.slot_id in outcomes for slot in ledger.slots),
                "verifiedDeterministicAssessments": len(verified["deterministic"]), "requiredDeterministicAssessments": 108,
                "verifiedModelReviews": len(verified["model"]), "requiredModelReviews": 216,
                "verifiedHumanReviews": len(verified["human"]), "initialHumanCases": 36,
                "requiredHumanCases": len(required), "requiredHumanReviews": len(required) * 2,
                "reviewedHumanCases": len(reviewed), "unreviewedHumanCases": 108 - len(reviewed),
                "requiredUnreviewedHumanCases": len(required - reviewed),
                "unknownCompletionSlots": 108 - sum(event["data"]["completion"] is not None for event in outcomes.values()),
                "unknownAuthoritySlots": 108 - sum(event["data"]["authorityCorrect"] is not None for event in outcomes.values()),
                "automaticComplete": assessment.automatic_complete and len(outcomes) == 108 and not inconclusive_outcomes,
                "humanCoverageComplete": not (required - reviewed)}
    thresholds = _thresholds(ledger, registration, outcomes, deterministic, safety, resolved_humans)
    costs = _costs(registration, ledger, outcomes, verified)
    groups = _groups(ledger, outcomes)
    reasons = {slot: list(flags) for slot, flags in assessment.reasons_by_slot}
    for slot in all_slots - set(outcomes):
        reasons.setdefault(slot, []).append("missing-authenticated-outcome")
    for slot in inconclusive_outcomes:
        reasons.setdefault(slot, []).append("inconclusive-authenticated-outcome")
    for slot in confirmed_cells:
        reasons.setdefault(slot, []).append("confirmed-human-discrepancy-source-cell")
    if safety["acceptanceSuspended"]:
        for slot in all_slots:
            reasons.setdefault(slot, []).append("confirmed-critical-report-incident-cohort")
    if safety["acceptanceSuspended"]:
        status = "suspended"
    elif not coverage["automaticComplete"]:
        status = "technical-incomplete"
    elif not coverage["humanCoverageComplete"]:
        status = "human-audit-pending"
    elif any(host["successThresholdStatus"] == "not-met" or host["authorityRequirementStatus"] == "not-met"
             or host["fidelityRequirementStatus"] == "not-met" for host in thresholds):
        status = "registered-threshold-not-met"
    elif costs["actualAdditionalSpendEur"] is None:
        status = "cash-reconciliation-pending"
    elif (not costs["noncashMeasurementsComplete"] or costs["additionalCashWithinCap"] is not True
          or not costs["noncashWithinCaps"] or costs["providerAccountingWithinBudget"] is not True):
        status = "technical-accounting-incomplete"
    else:
        status = "ready-for-independent-interpretation"
    identity = {field: getattr(instrument, field) for field in (
        "source_ref", "source_sha256", "verifier_ref", "verifier_sha256")}
    payload = {"schemaVersion": SCHEMA, "inputSha256": inputs.sha256,
               "registrationSha256": registration.sha256, "ledgerSha256": data["ledgerSha256"],
               "auditSelectionSha256": selection.sha256, "documentManifestSha256": document_hash,
               "instrumentIdentitySha256": _digest(identity),
               "population": {"intendedSlots": 108, "humanOperatedCliSlots": 36, "nativeAssistantSlots": 72},
               "groups": groups, "coverage": coverage,
               "declaredCoverage": {"deterministicAssessments": len(records["deterministic"]),
                   "modelReviews": len(records["model"]), "humanReviews": len(records["human"])},
               "armCThresholds": thresholds, "safety": safety, "costs": costs,
               "audit": {"requiredSlotIds": sorted(required), "reviewedSlotIds": sorted(reviewed),
                         "unreviewedSlotIds": sorted(all_slots - reviewed),
                         "reasonsBySlot": {slot: sorted(set(flags)) for slot, flags in sorted(reasons.items())}},
               "sourceVerification": {"providedDocuments": len(document_map),
                   "authenticatedDocuments": len(authenticated),
                   "syntheticDocuments": sum(domain == "synthetic-control" for domain in domains.values()),
                   "unavailableOrRefusedDocuments": len(document_map) - len(domains),
                   "verifiedSubjects": sorted(authenticated),
                   "documentDigests": sorted(document.document_sha256 for document in document_map.values())},
               "conclusion": {"status": status, "utilityClaimEligible": False,
                   "humanAcceptanceAsserted": False, "founderApprovalAsserted": False,
                   "milestoneClosureAsserted": False}, "limits": list(_LIMITS)}
    payload["reportSha256"] = _digest(payload)
    return AssistedReport(payload, _token=_TOKEN)


def _restore_inputs(data):
    registration_data = data["registration"]
    hashes = {item["fixtureId"]: item["sha256"] for item in registration_data["fixtures"]}
    hashes.update({item["promptId"]: item["sha256"] for item in registration_data["prompts"]})
    registration = evaluation.validate_registration(registration_data,
        expected_candidate_sha256=registration_data["candidate"]["sha256"], expected_input_hashes=hashes)
    ledger = evaluation.EvaluationLedger(registration.sha256, evaluation.generate_slots(registration),
        tuple(evaluation.LedgerEvent(event["sequence"], event["slotId"], event["status"],
             event["attemptId"], event["data"], event["dataSha256"]) for event in data["ledger"]["events"]))
    evaluation.validate_ledger(ledger, registration)
    return registration, ledger


def _document_map(documents, subjects):
    if not isinstance(documents, (tuple, list)) or len(documents) > len(subjects):
        raise AssistedReportError("source document collection must be bounded by frozen subjects")
    known = {(subject.kind, subject.sha256) for subject in subjects}
    result = {}
    rows = []
    for document in documents:
        if not isinstance(document, EvidenceDocument) or not isinstance(document.kind, str):
            raise AssistedReportError("typed source documents are required")
        _hash(document.subject_sha256)
        _hash(document.document_sha256)
        _text(document.reference)
        key = (document.kind, document.subject_sha256)
        if key not in known or key in result:
            raise AssistedReportError("source document is duplicate or absent from the frozen input subjects")
        result[key] = document
        rows.append({"kind": document.kind, "subjectSha256": document.subject_sha256,
                     "reference": document.reference, "documentSha256": document.document_sha256})
    return result, _digest(sorted(rows, key=lambda row: (row["kind"], row["subjectSha256"])))


def _authenticate(instrument, subjects, documents):
    authenticated, domains = set(), {}
    if instrument.document_verifier is None:
        return authenticated, domains
    for subject in subjects:
        key = (subject.kind, subject.sha256)
        document = documents.get(key)
        if document is None:
            continue
        try:
            attestation = instrument.document_verifier.verify_document(document, subject=subject)
            if (not isinstance(attestation, DocumentAttestation) or attestation.kind != subject.kind
                    or attestation.subject_sha256 != subject.sha256
                    or attestation.document_sha256 != document.document_sha256):
                continue
            _hash(attestation.decision_sha256)
            if not isinstance(attestation.verifier_id, str) or not _ID.fullmatch(attestation.verifier_id):
                continue
            stamp = datetime.fromisoformat(attestation.verified_at.replace("Z", "+00:00"))
            if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
                continue
            if subject.kind == "outcome":
                record = json.loads(subject.payload_bytes)["record"]
                observed = datetime.fromisoformat(record["data"]["sourceTimestamp"].replace("Z", "+00:00"))
                if stamp < observed:
                    continue
            expected = ("human-cli" if subject.slot_id.endswith(":cli") else "native-host"
                        ) if subject.kind == "outcome" else _DOMAINS[subject.kind]
            if attestation.domain not in (expected, "synthetic-control"):
                continue
            domains[subject.sha256] = attestation.domain
            if attestation.domain == expected:
                authenticated.add(subject.sha256)
        except Exception:
            # A source can contain private material in exceptions. Preserve only
            # unavailability; never turn an exception or a hash into facts.
            continue
    return authenticated, domains


def _groups(ledger, outcomes):
    groups = []
    for host in evaluation.HOSTS:
        for arm in evaluation.ARMS:
            slots = [slot for slot in ledger.slots if (slot.host, slot.arm) == (host, arm)]
            counts = {status: sum(ledger.current_status(slot.slot_id) == status for slot in slots)
                      for status in evaluation.SLOT_STATUSES}
            slot_ids = {slot.slot_id for slot in slots}
            history = {status: sum(event.slot_id in slot_ids and event.status == status for event in ledger.events)
                       for status in ("invalid", "refused", "cancelled", "failed", "recovered")}
            groups.append({"host": host, "arm": arm, "intended": 18,
                "notStarted": counts["not-started"], "inProgress": counts["attempted"],
                "terminal": sum(counts[status] for status in evaluation.FINAL_STATUSES),
                "completed": sum(ledger.current_event(slot.slot_id) is not None
                                 and ledger.current_status(slot.slot_id) in evaluation.FINAL_STATUSES
                                 and ledger.current_event(slot.slot_id).data["completion"] is True for slot in slots),
                "failed": counts["failed"], "statuses": counts, "declaredHistory": history,
                "sourceVerifiedTerminal": sum(slot.slot_id in outcomes for slot in slots),
                "sourceVerifiedFailed": sum(slot.slot_id in outcomes
                    and outcomes[slot.slot_id]["status"] == "failed" for slot in slots),
                "sourceVerifiedCompleted": sum(slot.slot_id in outcomes
                    and outcomes[slot.slot_id]["data"]["completion"] is True for slot in slots)})
    return groups


def _authenticated_audit(selection, verified):
    pairs = {}
    for record in verified["human"]:
        pairs.setdefault(record["slotId"], {})[record["roleId"]] = record
    verified["adjudication"] = [record for record in verified["adjudication"]
        if set(pairs.get(record["slotId"], {})) == set(selection.human_review_roles)]
    arguments = dict(human_reviews=verified["human"], adjudications=verified["adjudication"])
    preliminary = audit.assess_audit(selection, verified["deterministic"], verified["model"], **arguments)
    supported_events = []
    confirmed_critical = False
    for event in verified["escalation"]:
        # The external verified-incident domain authenticates the actual incident
        # independently. Missing source proofs for linked review records cannot
        # suppress a confirmed critical incident or fabricate those reviews.
        if event["eventType"] == "critical-incident":
            confirmed_critical = True
            kind = event["reviewerType"]
            supported = any(record["slotId"] == event["slotId"] and (
                kind == "deterministic" or record["reviewerId"] == event["reviewerId"])
                for record in verified[kind])
        else:
            supported = event["slotId"] in preliminary.reviewed_slot_ids
        if supported:
            supported_events.append(event)
    assessment = audit.assess_audit(selection, verified["deterministic"], verified["model"],
                                   escalation_events=supported_events, **arguments)
    return assessment, confirmed_critical


def _resolved_human_labels(assessment, verified):
    result = {}
    adjudications = {record["slotId"]: record["labels"] for record in verified["adjudication"]}
    for slot_id in assessment.reviewed_slot_ids:
        pair = [record["labels"] for record in verified["human"] if record["slotId"] == slot_id]
        result[slot_id] = adjudications.get(slot_id, pair[0])
    return result


def _safety(outcomes, deterministic, humans, suspended):
    authority, inversion, false_success = set(), set(), set()
    for slot_id, event in outcomes.items():
        observation = deterministic.get(slot_id)
        human = humans.get(slot_id)
        if (event["data"]["authorityCorrect"] is False
                or observation is not None and observation.labels.authority_correct is False
                or human is not None and human["authorityCorrect"] is False):
            authority.add(slot_id)
        accepted = event["data"]["completion"] is True or observation is not None and observation.labels.success is True
        if accepted and (observation is not None and observation.labels.fidelity is False
                         or human is not None and human["fidelity"] is False):
            inversion.add(slot_id)
        if observation is not None and observation.labels.success is True and (
                observation.oracle_matches is False or observation.outcome != observation.expected_outcome
                or event["data"]["completion"] is False):
            false_success.add(slot_id)
    return {"acceptanceSuspended": suspended or bool(authority or inversion or false_success),
            "authorityIncorrectSlotIds": sorted(authority), "acceptedFactualInversionSlotIds": sorted(inversion),
            "falseSuccessSlotIds": sorted(false_success),
            "absenceOfIncidentsEstablished": not suspended and len(outcomes) == 108 and len(deterministic) == 108
                and all(event["data"]["authorityCorrect"] is True for event in outcomes.values())
                and all(record.labels.authority_correct is True and record.labels.fidelity is True
                        for record in deterministic.values()) and not (authority or inversion or false_success)}


def _thresholds(ledger, registration, outcomes, deterministic, safety, resolved_humans):
    results = []
    required = registration.data["rubric"]["thresholds"]["armCSuccessesPerHost"]
    excluded = set(safety["authorityIncorrectSlotIds"] + safety["acceptedFactualInversionSlotIds"] + safety["falseSuccessSlotIds"])
    for host in evaluation.HOSTS:
        slots = [slot for slot in ledger.slots if slot.host == host and slot.arm == "mcp-plus-skills"]
        successes, conclusive, authorities, authority_bad, fidelities, fidelity_bad = 0, 0, 0, 0, 0, 0
        human_authority_bad, human_fidelity_bad = 0, 0
        for slot in slots:
            human = resolved_humans.get(slot.slot_id)
            if human is not None:
                human_authority_bad += human["authorityCorrect"] is False
                human_fidelity_bad += human["fidelity"] is False
            event, observation = outcomes.get(slot.slot_id), deterministic.get(slot.slot_id)
            if event is None:
                continue
            authority_bad += event["data"]["authorityCorrect"] is False or (
                observation is not None and observation.labels.authority_correct is False)
            authorities += event["data"]["authorityCorrect"] is True and not (
                observation is not None and observation.labels.authority_correct is False)
            if observation is None:
                continue
            fidelities += observation.labels.fidelity is True
            fidelity_bad += observation.labels.fidelity is False
            if (observation.conclusive and observation.evidence_complete and observation.labels.success is not None
                    and event["data"]["completion"] is not None):
                conclusive += 1
                if (event["data"]["completion"] is True and observation.labels.success is True
                        and observation.oracle_matches is True and observation.outcome == observation.expected_outcome
                        and observation.labels.authority_correct is True and observation.labels.fidelity is True
                        and slot.slot_id not in excluded):
                    successes += 1
        threshold_status = ("met" if successes >= required else "not-met"
                            if successes + (18 - conclusive) < required else "pending")
        results.append({"host": host, "intended": 18, "requiredSuccesses": required,
            "sourceVerifiedSuccesses": successes, "successThresholdStatus": threshold_status,
            "unknownSuccesses": 18 - conclusive, "sourceVerifiedAuthorityCorrect": authorities,
            "resolvedHumanAuthorityFailures": human_authority_bad,
            "authorityRequirementStatus": "not-met" if authority_bad or human_authority_bad
                else "met" if authorities == 18 else "pending",
            "sourceVerifiedFidelityCorrect": fidelities,
            "resolvedHumanFidelityFailures": human_fidelity_bad,
            "fidelityRequirementStatus": "not-met" if fidelity_bad or human_fidelity_bad
                else "met" if fidelities == 18 else "pending"})
    return results


def _costs(registration, ledger, outcomes, verified):
    setup = verified["setup"][0] if verified["setup"] else None
    totals = {}
    for field in evaluation.COST_FIELDS:
        values = [outcomes[slot.slot_id]["data"]["costs"][field]
                  for slot in ledger.slots if slot.slot_id in outcomes]
        if field == "eur" or setup is None or len(values) != 108 or setup[field] is None or any(value is None for value in values):
            totals[field] = None
        elif field in {"rss_bytes", "disk_bytes"}:
            totals[field] = max(setup[field], *values)
        else:
            totals[field] = setup[field] + sum(values)
    money = verified["money"][0] if verified["money"] else None
    cash = None
    allocation = None
    provider_accounting = None
    if money is not None and money["requiredMeasuresComplete"] is True:
        cash = _money_amount(money["actualAdditionalSpendEur"])
        allocation = _money_amount(money["allocatedSubscriptionCostEur"])
        actual_provider = _money_amount(money["actualProviderSpendEur"])
        declared_accounting = _money_amount(money["providerAccountingCostEur"])
        if allocation is not None and actual_provider is not None and declared_accounting is not None:
            from .tooling_money import provider_accounting_total
            recomputed = provider_accounting_total(actual_provider, allocation)
            if recomputed != declared_accounting:
                raise AssistedReportError("verified provider accounting amount differs from exact independent amounts")
            provider_accounting = recomputed
    noncash_complete = all(totals[field] is not None for field in evaluation.COST_FIELDS if field != "eur")
    cap = Decimal(str(registration.data["billingPolicy"]["additionalSpendCapEur"]))
    return {"observedTotals": totals, "actualAdditionalSpendEur": None if cash is None else str(cash),
            "allocatedSubscriptionCostEur": None if allocation is None else str(allocation),
            "providerAccountingCostEur": None if provider_accounting is None else str(provider_accounting),
            "providerAccountingWithinBudget": None if provider_accounting is None
                else provider_accounting <= Decimal(str(registration.data["costCaps"]["eur"])),
            "additionalCashWithinCap": None if cash is None else cash <= cap,
            "noncashMeasurementsComplete": noncash_complete,
            "noncashWithinCaps": noncash_complete and all(totals[field] <= registration.data["costCaps"][field]
                for field in evaluation.CAP_FIELDS if field != "eur"),
            "currency": "EUR", "actualCashSourceAuthenticated": cash is not None,
            "limits": ["Ledger EUR values and subscription reservations do not establish independently reconciled cohort cash."]}


def _money_amount(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 128:
        raise AssistedReportError("verified monetary amount is invalid")
    try:
        amount = Decimal(value)
    except ArithmeticError as exc:
        raise AssistedReportError("verified monetary amount is invalid") from exc
    if not amount.is_finite() or amount < 0:
        raise AssistedReportError("verified monetary amount must be finite and nonnegative")
    return amount


def _measurements(values):
    if not isinstance(values, Mapping) or set(values) != set(evaluation.COST_FIELDS):
        raise AssistedReportError("setup measurements must preserve all eight fields and unknown values")
    result = json.loads(_json(dict(values)))
    for field, value in result.items():
        if value is None:
            continue
        if (type(value) not in (int, float) or not math.isfinite(value) or value < 0
                or field not in {"eur", "wall_seconds"} and type(value) is not int):
            raise AssistedReportError("setup measures must be finite nonnegative numbers or null")
    return result


def _validated_records(values, validator, limit):
    return [validator(record).as_dict() for record in _copy_records(values, limit)]


def _copy_records(values, limit):
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)) or len(values) > limit:
        raise AssistedReportError("independent record collection is oversized or malformed")
    return [json.loads(_json(record.as_dict() if hasattr(record, "as_dict") else record)) for record in values]


def _hash(value):
    if not isinstance(value, str) or not _DIGEST.fullmatch(value):
        raise AssistedReportError("an exact lowercase SHA-256 is required")


def _text(value):
    try:
        valid = isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= 2048
    except UnicodeError as exc:
        raise AssistedReportError("source reference must be valid UTF-8") from exc
    if not valid:
        raise AssistedReportError("a bounded nonempty source reference is required")


def _json(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise AssistedReportError("report values must be bounded JSON data") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise AssistedReportError("report input exceeds its 8 MiB bound")
    return raw


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _digest(value):
    return _sha_bytes(_json(value))


__all__ = ["AssistedReport", "AssistedReportError", "DocumentAttestation", "DocumentVerifier",
           "EvidenceDocument", "ReportInputs", "ReportSubject", "SummaryVerification",
           "TechnicalSummaryInstrument", "build_assisted_report", "freeze_report_inputs"]
