# SPDX-License-Identifier: AGPL-3.0-only
"""Prospective, offline M4.5 audit preparation; no capture or human approval.

Deterministic observations, model judgments and declared human ratings keep
separate provenance. Hashes establish content identity, not source authenticity.
The original full-cohort utility eligibility evaluator remains unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


POLICY_SCHEMA = "agent-braid-m45-human-audit-policy-v1"
SELECTION_SCHEMA = "agent-braid-m45-human-audit-selection-v1"
DETERMINISTIC_SCHEMA = "agent-braid-m45-deterministic-assessment-v1"
MODEL_SCHEMA = "agent-braid-m45-model-review-v1"
HUMAN_SCHEMA = "agent-braid-m45-human-review-v1"
ADJUDICATION_SCHEMA = "agent-braid-m45-human-adjudication-v1"
ALGORITHM = "sha256-host-class-fixture-v1"
ESCALATION = "cell-on-confirmed-discrepancy-cohort-on-critical-v1"
REVIEW_MODEL = "gpt-6-luna"
MODEL_ROLES = ("technical", "adversarial")
# These are the fixed original design, rather than a caller-selected population.
HOSTS = ("codex", "claude-code")
ARMS = ("cli", "mcp-only", "mcp-plus-skills")
JOURNEY_CLASSES = (
    "analyze-interactions", "prepare-advisory-plan", "refuse-missing-grant",
    "execute-granted-batch-verify", "inspect-recover-interruption", "export-evidence",
)
OUTCOMES = frozenset(("not-started", "attempted", "valid", "invalid", "refused",
                      "cancelled", "recovered", "failed"))
_HASH = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_SLOT_FIELDS = {
    "slot_id": "slotId", "host": "host", "arm": "arm", "journey_class": "journeyClass",
    "fixture_id": "fixtureId", "fixture_sha256": "fixtureSha256",
    "prompt_id": "promptId", "prompt_sha256": "promptSha256", "order_position": "orderPosition",
}
_COMMON = {"schema", "reviewerType", "slotId", "evidenceSha256", "rubricSha256", "labels"}


class HumanAuditError(ValueError):
    """Audit policy, frozen roster, provenance or coverage input is invalid."""


@dataclass(frozen=True)
class AuditPolicy:
    seed: str
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {"schema": POLICY_SCHEMA, "seed": self.seed, "algorithm": ALGORITHM,
                "initialCases": 36, "reviewersPerCase": 2,
                "escalation": ESCALATION, "compactEvidence": True}


@dataclass(frozen=True)
class AuditSlot:
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
        return {wire: getattr(self, name) for name, wire in _SLOT_FIELDS.items()}


@dataclass(frozen=True)
class AuditSelection:
    registration_sha256: str
    rubric_sha256: str
    policy: AuditPolicy
    roster: tuple[AuditSlot, ...]
    roster_sha256: str
    human_review_roles: tuple[str, str]
    initial_slot_ids: tuple[str, ...]
    sha256: str

    @property
    def policy_sha256(self) -> str:
        return self.policy.sha256

    def as_dict(self) -> dict[str, Any]:
        _validate_selection(self)
        return {**_selection_payload(self), "sha256": self.sha256,
                "policy": self.policy.as_dict(), "roster": [slot.as_dict() for slot in self.roster]}


@dataclass(frozen=True)
class OutcomeLabels:
    success: bool | None
    authority_correct: bool | None
    fidelity: bool | None

    def as_dict(self) -> dict[str, bool | None]:
        return {"success": self.success, "authorityCorrect": self.authority_correct, "fidelity": self.fidelity}

    @property
    def complete(self) -> bool:
        return all(value is not None for value in (self.success, self.authority_correct, self.fidelity))


@dataclass(frozen=True)
class DeterministicAssessment:
    slot_id: str
    evidence_sha256: str
    rubric_sha256: str
    labels: OutcomeLabels
    outcome: str
    expected_outcome: str
    oracle_matches: bool | None
    evidence_complete: bool
    conclusive: bool

    def as_dict(self) -> dict[str, Any]:
        return {**_common_dict(self, DETERMINISTIC_SCHEMA, "deterministic"),
                "outcome": self.outcome, "expectedOutcome": self.expected_outcome,
                "oracleMatches": self.oracle_matches, "evidenceComplete": self.evidence_complete,
                "conclusive": self.conclusive}


@dataclass(frozen=True)
class ModelReview:
    slot_id: str
    evidence_sha256: str
    rubric_sha256: str
    labels: OutcomeLabels
    role_id: str
    reviewer_id: str
    context_sha256: str
    model: str = REVIEW_MODEL
    independent: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {**_common_dict(self, MODEL_SCHEMA, "model"), "roleId": self.role_id,
                "reviewerId": self.reviewer_id, "contextSha256": self.context_sha256,
                "model": self.model, "independent": self.independent}


@dataclass(frozen=True)
class HumanReview:
    slot_id: str
    evidence_sha256: str
    rubric_sha256: str
    labels: OutcomeLabels
    role_id: str
    reviewer_id: str
    independent: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {**_common_dict(self, HUMAN_SCHEMA, "human"), "roleId": self.role_id,
                "reviewerId": self.reviewer_id, "independent": self.independent}


@dataclass(frozen=True)
class AuditAssessment:
    selection_sha256: str
    required_slot_ids: tuple[str, ...]
    reviewed_slot_ids: tuple[str, ...]
    unreviewed_slot_ids: tuple[str, ...]
    required_unreviewed_slot_ids: tuple[str, ...]
    automatic_complete: bool
    human_coverage_complete: bool
    acceptance_suspended: bool
    reasons_by_slot: tuple[tuple[str, tuple[str, ...]], ...]

    def as_dict(self) -> dict[str, Any]:
        return {"schema": "agent-braid-m45-human-audit-assessment-v1",
                "selectionSha256": self.selection_sha256, "intendedCases": 108,
                "requiredSlotIds": list(self.required_slot_ids), "reviewedSlotIds": list(self.reviewed_slot_ids),
                "unreviewedSlotIds": list(self.unreviewed_slot_ids),
                "requiredUnreviewedSlotIds": list(self.required_unreviewed_slot_ids),
                "automaticComplete": self.automatic_complete, "humanCoverageComplete": self.human_coverage_complete,
                "acceptanceSuspended": self.acceptance_suspended,
                "reasonsBySlot": {slot: list(reasons) for slot, reasons in self.reasons_by_slot}}


def validate_policy(value: Mapping[str, Any] | AuditPolicy, *, expected_sha256: str | None = None) -> AuditPolicy:
    """Validate the exact prospective policy and freeze a content identity."""
    original = value if isinstance(value, AuditPolicy) else None
    value = original.as_dict() if original else value
    _shape(value, {"schema", "seed", "algorithm", "initialCases", "reviewersPerCase", "escalation", "compactEvidence"}, "audit policy")
    if (value["schema"] != POLICY_SCHEMA or value["algorithm"] != ALGORITHM
            or value["escalation"] != ESCALATION or value["compactEvidence"] is not True
            or type(value["initialCases"]) is not int or value["initialCases"] != 36
            or type(value["reviewersPerCase"]) is not int or value["reviewersPerCase"] != 2):
        raise HumanAuditError("audit policy must preserve the frozen 36-case two-human design")
    seed = _identifier(value["seed"], "audit seed")
    digest = _sha(value)
    if original and original.sha256 != digest:
        raise HumanAuditError("validated audit policy identity was altered")
    if expected_sha256 is not None and _hash(expected_sha256, "expected policy SHA-256") != digest:
        raise HumanAuditError("audit policy SHA-256 mismatch")
    return AuditPolicy(seed, digest)


def policy_sha256(value: Mapping[str, Any] | AuditPolicy) -> str:
    return validate_policy(value).sha256


def freeze_selection(
    roster: Sequence[Any], policy: Mapping[str, Any] | AuditPolicy, *,
    expected_policy_sha256: str, registration_sha256: str, rubric_sha256: str,
    human_review_roles: Sequence[str],
) -> AuditSelection:
    """Freeze one fixture per host/class across all arms, independent of outcomes.

    Accept the original validated AttemptSlot roster without importing its
    registration module. The complete design is rechecked and copied immutably.
    The expected policy hash comes from the exact frozen registration; this
    check alone does not prove that registration/selection preceded capture.
    No registration approval or appointed-human identity is inferred here.
    """
    frozen_policy = validate_policy(policy, expected_sha256=_hash(expected_policy_sha256, "registered policy SHA-256"))
    slots = _validate_roster(roster)
    _sequence(human_review_roles, "human review roles")
    if len(human_review_roles) != 2:
        raise HumanAuditError("exactly two frozen independent human roles are required")
    roles = tuple(_identifier(role, "human role") for role in human_review_roles)
    if len(set(roles)) != 2:
        raise HumanAuditError("human review roles must be distinct")
    chosen = set()
    for host in HOSTS:
        for journey in JOURNEY_CLASSES:
            fixtures = {slot.fixture_id for slot in slots if slot.host == host and slot.journey_class == journey}
            fixture = min(fixtures, key=lambda fixture: (_sha({"seed": frozen_policy.seed,
                "host": host, "journeyClass": journey, "fixtureId": fixture}), fixture))
            chosen.update(slot.slot_id for slot in slots if slot.host == host
                          and slot.journey_class == journey and slot.fixture_id == fixture)
    result = AuditSelection(
        _hash(registration_sha256, "registration SHA-256"), _hash(rubric_sha256, "rubric SHA-256"),
        frozen_policy, slots, _sha([slot.as_dict() for slot in slots]), roles,
        tuple(sorted(chosen)), "",  # type: ignore[arg-type]
    )
    return AuditSelection(**{**result.__dict__, "sha256": _sha(_selection_payload(result))})


def validate_deterministic_assessment(value: Any) -> DeterministicAssessment:
    data, common = _record(value, DeterministicAssessment, DETERMINISTIC_SCHEMA, "deterministic",
                           {"outcome", "expectedOutcome", "oracleMatches", "evidenceComplete", "conclusive"})
    for field in ("outcome", "expectedOutcome"):
        _identifier(data[field], field)
        if data[field] not in OUTCOMES:
            raise HumanAuditError("deterministic outcomes must use registered roster statuses")
    for field in ("oracleMatches", "evidenceComplete", "conclusive"):
        if type(data[field]) is not bool and not (field == "oracleMatches" and data[field] is None):
            raise HumanAuditError(f"{field} must be a boolean" + (" or null" if field == "oracleMatches" else ""))
    return DeterministicAssessment(*common, data["outcome"], data["expectedOutcome"],
                                   data["oracleMatches"], data["evidenceComplete"], data["conclusive"])


def validate_model_review(value: Any) -> ModelReview:
    data, common = _record(value, ModelReview, MODEL_SCHEMA, "model",
                           {"roleId", "reviewerId", "contextSha256", "model", "independent"})
    role_id = _identifier(data["roleId"], "model review role")
    if data["model"] != REVIEW_MODEL or role_id not in MODEL_ROLES or data["independent"] is not True:
        raise HumanAuditError("model reviews require independent technical/adversarial Luna Latest agents")
    return ModelReview(*common, data["roleId"], _identifier(data["reviewerId"], "model reviewer ID"),
                       _hash(data["contextSha256"], "model context SHA-256"))


def validate_human_review(value: Any) -> HumanReview:
    data, common = _record(value, HumanReview, HUMAN_SCHEMA, "human", {"roleId", "reviewerId", "independent"})
    if data["independent"] is not True:
        raise HumanAuditError("human review must declare independence")
    return HumanReview(*common, _identifier(data["roleId"], "human role"),
                       _identifier(data["reviewerId"], "human reviewer ID"))


def assess_audit(
    selection: AuditSelection, deterministic_assessments: Sequence[Any], model_reviews: Sequence[Any], *,
    human_reviews: Sequence[Any] = (), adjudications: Sequence[Mapping[str, Any]] = (),
    escalation_events: Sequence[Mapping[str, Any]] = (),
) -> AuditAssessment:
    """Assess automatic coverage and required human coverage as separate facts.

    Missing or inconclusive records require audit; they never become success.
    Confirmed human discrepancy events expand one host/class/arm cell. Critical
    incidents expand all 108 and suspend acceptance. This is not utility approval
    or verification that a declared human is an authenticated person.
    """
    _validate_selection(selection)
    slots = {slot.slot_id: slot for slot in selection.roster}
    deterministic = _records_by_slot(deterministic_assessments, validate_deterministic_assessment, slots, selection)
    models = _records_by_slot(model_reviews, validate_model_review, slots, selection, by_role=True)
    humans = _records_by_slot(human_reviews, validate_human_review, slots, selection, by_role=True)
    evidence: dict[str, str] = {}
    for group in (deterministic, models, humans):
        for slot_id, records in group.items():
            for record in records.values():
                if slot_id in evidence and evidence[slot_id] != record.evidence_sha256:
                    raise HumanAuditError("assessment evidence identity differs for the same slot")
                evidence[slot_id] = record.evidence_sha256
    _validate_review_identities(models, humans, selection.human_review_roles)
    resolved = _resolve_humans(humans, adjudications, selection, evidence)
    reasons: dict[str, set[str]] = {slot_id: {"initial-sample"} for slot_id in selection.initial_slot_ids}
    automatic_complete = True
    for slot_id in slots:
        flags: set[str] = set()
        observation = deterministic.get(slot_id, {}).get("")
        pair = models.get(slot_id, {})
        if observation is None:
            flags.add("missing-deterministic-assessment")
            automatic_complete = False
        else:
            if observation.oracle_matches is not True:
                flags.add("oracle-mismatch" if observation.oracle_matches is False else "oracle-inconclusive")
            if not observation.evidence_complete:
                flags.add("incomplete-evidence")
            if (not observation.conclusive or not observation.labels.complete
                    or observation.outcome in {"not-started", "attempted", "cancelled"}):
                flags.add("inconclusive-result")
            if observation.outcome != observation.expected_outcome:
                flags.add("unexpected-outcome")
            if (not observation.evidence_complete or not observation.conclusive
                    or observation.oracle_matches is None or not observation.labels.complete
                    or observation.outcome in {"not-started", "attempted", "cancelled"}):
                automatic_complete = False
        if set(pair) != set(MODEL_ROLES) or any(not review.labels.complete for review in pair.values()):
            flags.add("missing-or-inconclusive-model-review")
            automatic_complete = False
        elif pair[MODEL_ROLES[0]].labels != pair[MODEL_ROLES[1]].labels:
            flags.add("model-disagreement")
        if observation and any(review.labels != observation.labels for review in pair.values()):
            flags.add("model-oracle-label-disagreement")
        if slot_id in humans and slot_id not in resolved:
            flags.add("unresolved-human-review")
        if flags:
            reasons.setdefault(slot_id, set()).update(flags)
    # A resolved independent pair itself confirms label disagreement. Requiring
    # a second caller flag here could silently discard an observed discrepancy.
    for slot_id, labels in resolved.items():
        observation = deterministic.get(slot_id, {}).get("")
        model_pair = models.get(slot_id, {})
        human_pair = humans[slot_id]
        discrepancy = (
            len({review.labels for review in human_pair.values()}) > 1
            or (observation is not None and observation.labels != labels)
            or any(review.labels != labels for review in model_pair.values())
        )
        if discrepancy:
            _expand_cell(slots[slot_id], slots, reasons)
    suspended = _apply_escalation_events(escalation_events, slots, deterministic, models, humans,
                                         resolved, selection, evidence, reasons)
    if (any(pair[""].labels.authority_correct is False for pair in deterministic.values())
            or any(labels.authority_correct is False for labels in resolved.values())):
        suspended = True
        for slot_id in slots:
            reasons.setdefault(slot_id, set()).add("confirmed-authority-incident-cohort")
    if any(_false_success(pair[""]) for pair in deterministic.values()):
        suspended = True
        for slot_id in slots:
            reasons.setdefault(slot_id, set()).add("confirmed-false-success-incident-cohort")
    required = set(reasons)
    reviewed = set(resolved)
    missing = required - reviewed
    return AuditAssessment(selection.sha256, tuple(sorted(required)), tuple(sorted(reviewed)),
        tuple(sorted(set(slots) - reviewed)), tuple(sorted(missing)), automatic_complete, not missing,
        suspended, tuple((slot, tuple(sorted(flags))) for slot, flags in sorted(reasons.items())))


def _validate_roster(roster: Sequence[Any]) -> tuple[AuditSlot, ...]:
    _sequence(roster, "roster")
    if len(roster) != 108:
        raise HumanAuditError("the original roster must contain exactly 108 slots")
    slots = []
    for value in roster:
        if isinstance(value, Mapping):
            _shape(value, set(_SLOT_FIELDS.values()), "roster slot")
            fields = {name: value[wire] for name, wire in _SLOT_FIELDS.items()}
        else:
            try:
                fields = {name: getattr(value, name) for name in _SLOT_FIELDS}
            except AttributeError as exc:
                raise HumanAuditError("roster slot must expose the original AttemptSlot fields") from exc
        slot = AuditSlot(**fields)
        for field in ("host", "arm", "journey_class"):
            _identifier(getattr(slot, field), field)
        if slot.host not in HOSTS or slot.arm not in ARMS or slot.journey_class not in JOURNEY_CLASSES:
            raise HumanAuditError("roster slot has an unknown host, class or arm")
        for field in ("fixture_id", "prompt_id"):
            _identifier(getattr(slot, field), field)
        for field in ("fixture_sha256", "prompt_sha256"):
            _hash(getattr(slot, field), field)
        if (slot.slot_id != ":".join((slot.host, slot.journey_class, slot.fixture_id, slot.arm))
                or type(slot.order_position) is not int or slot.order_position not in (1, 2, 3)):
            raise HumanAuditError("roster slot identity or order differs from the original design")
        slots.append(slot)
    if len({slot.slot_id for slot in slots}) != 108:
        raise HumanAuditError("roster contains duplicate slot IDs")
    global_fixtures: set[str] = set()
    global_prompts: set[str] = set()
    for journey in JOURNEY_CLASSES:
        group = [slot for slot in slots if slot.journey_class == journey]
        fixtures = sorted({slot.fixture_id for slot in group})
        prompts = {(slot.prompt_id, slot.prompt_sha256) for slot in group}
        if len(fixtures) != 3 or len(prompts) != 1 or set(fixtures) & global_fixtures:
            raise HumanAuditError("each class requires three independent fixtures and one matched prompt")
        prompt_id = next(iter(prompts))[0]
        if prompt_id in global_prompts:
            raise HumanAuditError("journey prompts must have distinct IDs")
        global_prompts.add(prompt_id)
        global_fixtures.update(fixtures)
        for fixture_index, fixture in enumerate(fixtures):
            fixture_slots = [slot for slot in group if slot.fixture_id == fixture]
            if len({slot.fixture_sha256 for slot in fixture_slots}) != 1:
                raise HumanAuditError("fixture hash differs between matched hosts or arms")
            for host in HOSTS:
                cell = [slot for slot in fixture_slots if slot.host == host]
                if len(cell) != 3 or {slot.arm for slot in cell} != set(ARMS):
                    raise HumanAuditError("fixtures must match all three arms in both hosts")
                for slot in cell:
                    expected_position = (ARMS.index(slot.arm) - fixture_index) % 3 + 1
                    if slot.order_position != expected_position:
                        raise HumanAuditError("roster arm order is not the original counterbalanced order")
    if global_fixtures & global_prompts:
        raise HumanAuditError("fixture and prompt ID namespaces must be disjoint")
    return tuple(sorted(slots, key=lambda slot: slot.slot_id))


def _selection_payload(selection: AuditSelection) -> dict[str, Any]:
    return {"schema": SELECTION_SCHEMA, "registrationSha256": selection.registration_sha256,
            "rubricSha256": selection.rubric_sha256, "policySha256": selection.policy_sha256,
            "rosterSha256": selection.roster_sha256, "humanReviewRoles": list(selection.human_review_roles),
            "initialSlotIds": list(selection.initial_slot_ids)}


def _validate_selection(selection: AuditSelection) -> None:
    if not isinstance(selection, AuditSelection):
        raise HumanAuditError("a frozen audit selection is required")
    expected = freeze_selection(selection.roster, selection.policy,
        expected_policy_sha256=selection.policy_sha256,
        registration_sha256=selection.registration_sha256, rubric_sha256=selection.rubric_sha256,
        human_review_roles=selection.human_review_roles)
    if selection != expected:
        raise HumanAuditError("frozen audit selection identity or roster was altered")


def _common_dict(record: Any, schema: str, reviewer_type: str) -> dict[str, Any]:
    return {"schema": schema, "reviewerType": reviewer_type, "slotId": record.slot_id,
            "evidenceSha256": record.evidence_sha256, "rubricSha256": record.rubric_sha256,
            "labels": record.labels.as_dict()}


def _record(value: Any, record_type: Any, schema: str, reviewer_type: str, fields: set[str]):
    data = value.as_dict() if isinstance(value, record_type) else value
    _shape(data, _COMMON | fields, "assessment record")
    if data["schema"] != schema or data["reviewerType"] != reviewer_type:
        raise HumanAuditError("assessment schema and reviewer type must preserve provenance")
    if not isinstance(data["slotId"], str) or not data["slotId"] or len(data["slotId"]) > 512:
        raise HumanAuditError("assessment slot ID must be nonempty bounded text")
    return data, (data["slotId"], _hash(data["evidenceSha256"], "evidence SHA-256"),
                  _hash(data["rubricSha256"], "rubric SHA-256"), _labels(data["labels"]))


def _labels(value: Any) -> OutcomeLabels:
    _shape(value, {"success", "authorityCorrect", "fidelity"}, "outcome labels")
    if any(item is not None and type(item) is not bool for item in value.values()):
        raise HumanAuditError("outcome labels must be booleans or null")
    return OutcomeLabels(value["success"], value["authorityCorrect"], value["fidelity"])


def _records_by_slot(values: Sequence[Any], validator: Any, slots: Mapping[str, AuditSlot],
                     selection: AuditSelection, *, by_role: bool = False) -> dict[str, dict[str, Any]]:
    _sequence(values, "assessment records")
    grouped: dict[str, dict[str, Any]] = {}
    for value in values:
        record = validator(value)
        if record.slot_id not in slots or record.rubric_sha256 != selection.rubric_sha256:
            raise HumanAuditError("assessment slot or rubric differs from the frozen selection")
        group = grouped.setdefault(record.slot_id, {})
        key = record.role_id if by_role else ""
        if key in group:
            raise HumanAuditError("duplicate assessment for slot/role")
        group[key] = record
    return grouped


def _validate_review_identities(models, humans, human_roles) -> None:
    for pair in models.values():
        if len({review.reviewer_id for review in pair.values()}) != len(pair):
            raise HumanAuditError("model reviewers must be distinct agents")
        if len({review.context_sha256 for review in pair.values()}) != len(pair):
            raise HumanAuditError("model reviewers require separate context identities")
    appointed: dict[str, str] = {}
    for pair in humans.values():
        for role, review in pair.items():
            if role not in human_roles:
                raise HumanAuditError("human rating uses an unfrozen role")
            if role in appointed and appointed[role] != review.reviewer_id:
                raise HumanAuditError("appointed human identity changed within a frozen role")
            appointed[role] = review.reviewer_id
    if len(set(appointed.values())) != len(appointed):
        raise HumanAuditError("the two human roles require distinct people")
    model_ids = {review.reviewer_id for pair in models.values() for review in pair.values()}
    if model_ids & set(appointed.values()):
        raise HumanAuditError("model reviewer identity cannot masquerade as an appointed human")


def _resolve_humans(humans, adjudications, selection, evidence) -> dict[str, OutcomeLabels]:
    _sequence(adjudications, "human adjudications")
    decisions: dict[str, OutcomeLabels] = {}
    for data in adjudications:
        _shape(data, {"schema", "reviewerType", "slotId", "adjudicatorId",
                      "evidenceSha256", "rubricSha256", "labels", "affirmedBy"}, "human adjudication")
        slot_id = _slot_identifier(data["slotId"])
        pair = humans.get(slot_id, {})
        adjudicator_id = _identifier(data["adjudicatorId"], "human adjudicator ID")
        if (data["schema"] != ADJUDICATION_SCHEMA or data["reviewerType"] != "human"
                or set(pair) != set(selection.human_review_roles)
                or adjudicator_id not in {review.reviewer_id for review in pair.values()}
                or data["evidenceSha256"] != evidence.get(slot_id)
                or data["rubricSha256"] != selection.rubric_sha256 or slot_id in decisions):
            raise HumanAuditError("human adjudication must bind the complete independent pair and exact evidence")
        affirmations = data["affirmedBy"]
        _sequence(affirmations, "joint human affirmations")
        if len(affirmations) != 2:
            raise HumanAuditError("human adjudication requires exactly two joint affirmations")
        affirmed_ids, affirmed_hashes = set(), set()
        for affirmation in affirmations:
            _shape(affirmation, {"reviewerId", "affirmationSha256"}, "joint human affirmation")
            affirmed_ids.add(_identifier(affirmation["reviewerId"], "affirming human ID"))
            affirmed_hashes.add(_hash(affirmation["affirmationSha256"], "human affirmation SHA-256"))
        if (affirmed_ids != {review.reviewer_id for review in pair.values()}
                or len(affirmed_ids) != 2 or len(affirmed_hashes) != 2):
            raise HumanAuditError("both original humans must independently affirm the joint adjudication")
        decisions[slot_id] = _labels(data["labels"])
    resolved = {}
    for slot_id, pair in humans.items():
        if set(pair) != set(selection.human_review_roles):
            continue
        labels = tuple(review.labels for review in pair.values())
        # Adjudication resolves disagreement only; it cannot invent missing ratings.
        if any(not value.complete for value in labels):
            continue
        if labels[0] == labels[1]:
            if slot_id in decisions and decisions[slot_id] != labels[0]:
                raise HumanAuditError("adjudication cannot replace two agreeing human ratings")
            resolved[slot_id] = labels[0]
        elif slot_id in decisions and decisions[slot_id].complete:
            resolved[slot_id] = decisions[slot_id]
    return resolved


def _apply_escalation_events(events, slots, deterministic, models, humans, resolved, selection, evidence, reasons) -> bool:
    _sequence(events, "audit escalation events")
    suspended = False
    seen = set()
    for event in events:
        common = {"eventType", "slotId", "reviewerType", "evidenceSha256", "rubricSha256"}
        if not isinstance(event, Mapping):
            raise HumanAuditError("audit event must be an object")
        kind = event.get("eventType")
        _identifier(kind, "audit event type")
        fields = {"reviewerIds"} if kind == "confirmed-human-discrepancy" else {"incidentKind", "reviewerId"}
        _shape(event, common | fields, "audit escalation event")
        slot_id = _slot_identifier(event["slotId"])
        if (slot_id not in slots or event["evidenceSha256"] != evidence.get(slot_id)
                or event["rubricSha256"] != selection.rubric_sha256):
            raise HumanAuditError("audit event must bind an assessed slot and its exact evidence/rubric")
        _identifier(event["reviewerType"], "audit event reviewer type")
        if kind == "confirmed-human-discrepancy":
            _sequence(event["reviewerIds"], "confirming human reviewer IDs")
            if len(event["reviewerIds"]) != 2:
                raise HumanAuditError("confirmed discrepancy requires exactly two human reviewer IDs")
            for reviewer_id in event["reviewerIds"]:
                _identifier(reviewer_id, "confirming human reviewer ID")
        event_sha = _sha(event)
        if event_sha in seen:
            raise HumanAuditError("duplicate audit escalation event")
        seen.add(event_sha)
        if kind == "confirmed-human-discrepancy":
            ids = event["reviewerIds"]
            expected = {review.reviewer_id for review in humans.get(slot_id, {}).values()}
            if (event["reviewerType"] != "human" or slot_id not in resolved or len(ids) != 2
                    or len(set(ids)) != 2 or set(ids) != expected):
                raise HumanAuditError("confirmed discrepancy needs the resolved pair of independent human reviewers")
            slot = slots[slot_id]
            _expand_cell(slot, slots, reasons)
        elif kind == "critical-incident":
            if event["incidentKind"] not in ("authority", "privacy", "false-success"):
                raise HumanAuditError("critical incident kind must be authority, privacy or false-success")
            source = event["reviewerType"]
            _identifier(source, "critical incident reviewer type")
            identity = event["reviewerId"]
            if source == "deterministic":
                valid_source = slot_id in deterministic and identity is None
            elif source in ("model", "human"):
                _identifier(identity, "critical incident reviewer ID")
                records = models if source == "model" else humans
                valid_source = identity in {review.reviewer_id for review in records.get(slot_id, {}).values()}
            else:
                valid_source = False
            if not valid_source:
                raise HumanAuditError("critical incident source must bind an existing assessment of the declared type")
            suspended = True
            for other in slots:
                reasons.setdefault(other, set()).add("critical-incident-cohort")
        else:
            raise HumanAuditError("unknown audit escalation event")
    return suspended


def _expand_cell(slot, slots, reasons) -> None:
    for other in slots.values():
        if (other.host, other.journey_class, other.arm) == (slot.host, slot.journey_class, slot.arm):
            reasons.setdefault(other.slot_id, set()).add("confirmed-human-discrepancy-cell")


def _false_success(observation: DeterministicAssessment) -> bool:
    return observation.labels.success is True and (
        observation.oracle_matches is False
        or (observation.outcome != observation.expected_outcome
            and observation.outcome in {"not-started", "attempted", "invalid", "refused", "cancelled", "failed"})
    )


def _shape(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise HumanAuditError(f"{label} must have exactly the declared fields")


def _sequence(value: Any, label: str) -> None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise HumanAuditError(f"{label} must be a sequence")


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise HumanAuditError(f"{label} must be a bounded identifier")
    return value


def _slot_identifier(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise HumanAuditError("assessment slot ID must be nonempty bounded text")
    return value


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _HASH.fullmatch(value):
        raise HumanAuditError(f"{label} must be a lowercase SHA-256")
    return value


def _sha(value: Any) -> str:
    try:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise HumanAuditError("audit value must have canonical finite JSON contents") from exc
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
