# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, provenance-preserving evidence packets for M4.5 review.

Packet construction does not evaluate outcomes, select the audit sample, launch
sessions, or confer acceptance. Caller-selected excerpts must already be redacted
and suitable for blinded review. All excerpts remain untrusted quoted data.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import html
import json
import re
from typing import Any, Mapping, Sequence

from . import tooling_evaluation as evaluation


SCHEMA = "agent-braid-m45-evidence-packet-v1"
MAX_TEXT_BYTES = 4096
MAX_PACKET_BYTES = 256 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:-]{0,127}$")
_LIMITS = (
    "Packet integrity is structural; referenced evidence requires independent verification.",
    "Human packets omit structured host, arm, order and model predictions; source content may reveal them.",
    "Unknown values remain null; a packet does not establish a human rating or acceptance.",
)


class PacketError(ValueError):
    """Evidence packet data is malformed, oversized, or incorrectly bound."""


@dataclass(frozen=True)
class StepEvidence:
    step_id: str
    description: str
    observed: bool | None
    evidence_sha256: str | None


@dataclass(frozen=True)
class RedactedExcerpt:
    """Selected redacted text plus immutable original and excerpt identities.

    Naming this type does not perform redaction. The producer must verify that
    text contains neither personal/secret material nor removable blinding clues.
    """
    source_ref: str
    source_sha256: str
    text: str
    excerpt_sha256: str


@dataclass(frozen=True)
class CaseEvidence:
    slot: evaluation.AttemptSlot
    expected_outcome: str
    observed_outcome: str | None
    required_steps: tuple[StepEvidence, ...]
    excerpts: tuple[RedactedExcerpt, ...]
    limits: tuple[str, ...] = ()


@dataclass(frozen=True)
class AssessmentSummary:
    """Private summary with explicit evaluator provenance; never shown to raters."""
    reviewer_type: str
    reviewer_id: str
    evidence_sha256: str
    rubric_sha256: str
    success: bool | None
    authority_correct: bool | None
    fidelity: bool | None
    model: str | None = None


def build_human_packet(case: CaseEvidence, *, registration_sha256: str,
                       blinding_key: bytes) -> dict[str, Any]:
    """Build an independent rater packet without model judgments or raw slot IDs.

    Use one random private key (at least 32 bytes), frozen before capture. The
    keyed case IDs prevent decoding the small 108-slot population by enumeration.
    Full source-reference mappings are retained only in the machine packet.
    """
    _validate_case(case, registration_sha256, blinding_key)
    payload = _human_fields(case, registration_sha256, blinding_key)
    return _seal({"schemaVersion": SCHEMA, "audience": "human", **payload})


def build_machine_packet(case: CaseEvidence, *, registration_sha256: str,
                         blinding_key: bytes,
                         assessments: Sequence[AssessmentSummary] = ()) -> dict[str, Any]:
    """Retain private slot/source mappings and separated evaluator provenance."""
    _validate_case(case, registration_sha256, blinding_key)
    if not isinstance(assessments, (tuple, list)) or len(assessments) > 16:
        raise PacketError("assessment summaries must be bounded typed records")
    assessment_records = [_assessment(item) for item in assessments]
    if len({(item["reviewerType"], item["reviewerId"]) for item in assessment_records}) != len(assessment_records):
        raise PacketError("assessment summaries duplicate reviewer identities")
    payload = _human_fields(case, registration_sha256, blinding_key)
    payload.update(slot=case.slot.as_dict(), assessments=assessment_records,
                   sourceMap=[{"sourceId": _source_id(excerpt, registration_sha256, blinding_key),
                               "reference": excerpt.source_ref, "sourceSha256": excerpt.source_sha256,
                               "excerptSha256": excerpt.excerpt_sha256}
                              for excerpt in case.excerpts])
    return _seal({"schemaVersion": SCHEMA, "audience": "machine-private", **payload})


def public_packet_summary(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Export structural counts and opaque identity; omit all caller free text."""
    data = _validate_packet(packet)
    return {"schemaVersion": SCHEMA, "caseId": data["caseId"],
            "packetSha256": data["packetSha256"],
            "expectedOutcomeKnown": data["expectedOutcome"] is not None,
            "observedOutcomeKnown": data["observedOutcome"] is not None,
            "requiredStepCount": len(data["requiredSteps"]), "excerptCount": len(data["excerpts"]),
            "limits": ["Structural summary only; no outcomes, native acceptance or human decisions asserted."]}


def render_human_markdown(packet: Mapping[str, Any]) -> str:
    """Render verified human fields, quoting every caller-provided string as data."""
    data = _validate_packet(packet)
    if data["audience"] != "human":
        raise PacketError("only blinded human packets can be rendered for raters")
    lines = [f"# Evidence case {data['caseId']}", "", "Expected outcome:", "",
             _quote(data["expectedOutcome"]), "", "Observed outcome:", "",
             _quote(data["observedOutcome"] if data["observedOutcome"] is not None else "Unknown (null)"),
             "", "Required steps:", ""]
    for step in data["requiredSteps"]:
        lines.extend([_quote(f"{step['stepId']}: {step['description']}"),
                      _quote(f"Observed: {json.dumps(step['observed'])}; evidence SHA-256: {step['evidenceSha256']}"), ""])
    for excerpt in data["excerpts"]:
        lines.extend([f"Untrusted source excerpt {excerpt['sourceId']}:", "",
                      _quote(excerpt["text"]), "",
                      f"Source SHA-256: {excerpt['sourceSha256']}; excerpt SHA-256: {excerpt['excerptSha256']}", ""])
    lines.extend(["Observation and blinding limits:", ""])
    lines.extend(_quote(limit) + "\n" for limit in data["limits"])
    rendered = "\n".join(lines) + "\n"
    if len(rendered.encode("utf-8")) > MAX_PACKET_BYTES * 2:
        raise PacketError("rendered evidence packet exceeds its bound")
    return rendered


def _human_fields(case, registration, key):
    return {"caseId": _opaque("case", registration, case.slot.slot_id, key),
            "registrationSha256": registration,
            "expectedOutcome": case.expected_outcome, "observedOutcome": case.observed_outcome,
            "requiredSteps": [{"stepId": step.step_id, "description": step.description,
                               "observed": step.observed, "evidenceSha256": step.evidence_sha256}
                              for step in case.required_steps],
            "excerpts": [{"sourceId": _source_id(excerpt, registration, key),
                          "sourceSha256": excerpt.source_sha256, "excerptSha256": excerpt.excerpt_sha256,
                          "text": excerpt.text} for excerpt in case.excerpts],
            "limits": list(_LIMITS + case.limits)}


def _validate_case(case, registration, key):
    _digest(registration, "registration")
    if type(key) is not bytes or not 32 <= len(key) <= 1024:
        raise PacketError("frozen private blinding key must contain at least 32 bytes")
    if not isinstance(case, CaseEvidence) or not isinstance(case.slot, evaluation.AttemptSlot):
        raise PacketError("typed case evidence and attempt slot required")
    _validate_slot(case.slot)
    _text(case.expected_outcome)
    if case.observed_outcome is not None:
        _text(case.observed_outcome)
    if type(case.required_steps) is not tuple or not 1 <= len(case.required_steps) <= 32:
        raise PacketError("required steps must be a nonempty bounded immutable tuple")
    step_ids = []
    for step in case.required_steps:
        if not isinstance(step, StepEvidence):
            raise PacketError("typed step evidence required")
        _identifier(step.step_id)
        _text(step.description)
        _label(step.observed)
        if step.evidence_sha256 is not None:
            _digest(step.evidence_sha256, "step evidence")
        step_ids.append(step.step_id)
    if len(set(step_ids)) != len(step_ids):
        raise PacketError("required steps have duplicate identities")
    if type(case.excerpts) is not tuple or len(case.excerpts) > 32:
        raise PacketError("selected excerpts must be a bounded immutable tuple")
    refs = []
    for excerpt in case.excerpts:
        if not isinstance(excerpt, RedactedExcerpt):
            raise PacketError("typed redacted excerpt required")
        _text(excerpt.source_ref)
        _text(excerpt.text)
        _digest(excerpt.source_sha256, "source")
        _digest(excerpt.excerpt_sha256, "excerpt")
        if excerpt.excerpt_sha256 != hashlib.sha256(excerpt.text.encode("utf-8")).hexdigest():
            raise PacketError("redacted excerpt content differs from its immutable hash")
        refs.append((excerpt.source_ref, excerpt.source_sha256, excerpt.excerpt_sha256))
    if len(set(refs)) != len(refs):
        raise PacketError("selected excerpts contain duplicate identities")
    if type(case.limits) is not tuple or len(case.limits) > 16:
        raise PacketError("observation limits must be a bounded immutable tuple")
    for limit in case.limits:
        _text(limit)


def _validate_slot(slot):
    if (slot.host not in evaluation.HOSTS or slot.arm not in evaluation.ARMS
            or slot.journey_class not in evaluation.JOURNEY_CLASSES
            or slot.slot_id != ":".join((slot.host, slot.journey_class, slot.fixture_id, slot.arm))
            or type(slot.order_position) is not int or slot.order_position not in (1, 2, 3)):
        raise PacketError("attempt slot identity or order is invalid")
    _identifier(slot.fixture_id)
    _identifier(slot.prompt_id)
    _digest(slot.fixture_sha256, "fixture")
    _digest(slot.prompt_sha256, "prompt")


def _assessment(item):
    if (not isinstance(item, AssessmentSummary) or not isinstance(item.reviewer_type, str)
            or item.reviewer_type not in {"deterministic", "model", "human"}):
        raise PacketError("assessment requires explicit deterministic, model or human provenance")
    _identifier(item.reviewer_id)
    _digest(item.evidence_sha256, "assessment evidence")
    _digest(item.rubric_sha256, "assessment rubric")
    for label in (item.success, item.authority_correct, item.fidelity):
        _label(label)
    if (item.reviewer_type == "model" and item.model != "gpt-6-luna"
            or item.reviewer_type != "model" and item.model is not None):
        raise PacketError("model reviews require Luna Latest and cannot be labeled human")
    return {"reviewerType": item.reviewer_type, "reviewerId": item.reviewer_id,
            "evidenceSha256": item.evidence_sha256, "rubricSha256": item.rubric_sha256,
            "labels": {"success": item.success, "authorityCorrect": item.authority_correct, "fidelity": item.fidelity},
            "model": item.model}


def _source_id(excerpt, registration, key):
    return _opaque("source", registration,
                   _json([excerpt.source_ref, excerpt.source_sha256, excerpt.excerpt_sha256]).decode("utf-8"), key)


def _opaque(kind, registration, identity, key):
    subject = _json([SCHEMA, kind, registration, identity])
    return f"{kind}-{hmac.new(key, subject, hashlib.sha256).hexdigest()[:24]}"


def _seal(payload):
    raw = _json(payload)
    if len(raw) > MAX_PACKET_BYTES - 128:
        raise PacketError("evidence packet exceeds its bounded size")
    return {**payload, "packetSha256": hashlib.sha256(raw).hexdigest()}


def _validate_packet(packet):
    if not isinstance(packet, Mapping):
        raise PacketError("evidence packet must be a bounded JSON object")
    data = json.loads(_json(dict(packet)))
    common = {"schemaVersion", "audience", "caseId", "registrationSha256", "expectedOutcome",
              "observedOutcome", "requiredSteps", "excerpts", "limits", "packetSha256"}
    extra = {"slot", "assessments", "sourceMap"} if data.get("audience") == "machine-private" else set()
    if (set(data) != common | extra or data.get("schemaVersion") != SCHEMA
            or data.get("audience") not in ("human", "machine-private")
            or not isinstance(data.get("caseId"), str)
            or not re.fullmatch(r"case-[0-9a-f]{24}", data["caseId"])):
        raise PacketError("evidence packet schema or audience is invalid")
    payload = {key: value for key, value in data.items() if key != "packetSha256"}
    if data["packetSha256"] != hashlib.sha256(_json(payload)).hexdigest():
        raise PacketError("evidence packet hash mismatch")
    _digest(data["registrationSha256"], "registration")
    _text(data["expectedOutcome"])
    if data["observedOutcome"] is not None:
        _text(data["observedOutcome"])
    if not isinstance(data["requiredSteps"], list) or not 1 <= len(data["requiredSteps"]) <= 32:
        raise PacketError("evidence packet required steps are invalid")
    for step in data["requiredSteps"]:
        if not isinstance(step, dict) or set(step) != {"stepId", "description", "observed", "evidenceSha256"}:
            raise PacketError("evidence packet step record is invalid")
        _identifier(step["stepId"])
        _text(step["description"])
        _label(step["observed"])
        if step["evidenceSha256"] is not None:
            _digest(step["evidenceSha256"], "step evidence")
    if len({step["stepId"] for step in data["requiredSteps"]}) != len(data["requiredSteps"]):
        raise PacketError("evidence packet step identities are duplicated")
    if not isinstance(data["excerpts"], list) or len(data["excerpts"]) > 32:
        raise PacketError("evidence packet excerpts are invalid")
    for excerpt in data["excerpts"]:
        if (not isinstance(excerpt, dict)
                or set(excerpt) != {"sourceId", "sourceSha256", "excerptSha256", "text"}
                or not isinstance(excerpt["sourceId"], str)
                or not re.fullmatch(r"source-[0-9a-f]{24}", excerpt["sourceId"])):
            raise PacketError("evidence packet excerpt record is invalid")
        _text(excerpt["text"])
        _digest(excerpt["sourceSha256"], "source")
        _digest(excerpt["excerptSha256"], "excerpt")
        if hashlib.sha256(excerpt["text"].encode("utf-8")).hexdigest() != excerpt["excerptSha256"]:
            raise PacketError("evidence packet excerpt digest differs")
    if len({excerpt["sourceId"] for excerpt in data["excerpts"]}) != len(data["excerpts"]):
        raise PacketError("evidence packet excerpt identities are duplicated")
    if not isinstance(data["limits"], list) or not len(_LIMITS) <= len(data["limits"]) <= 16 + len(_LIMITS):
        raise PacketError("evidence packet observation limits are invalid")
    if data["limits"][:len(_LIMITS)] != list(_LIMITS):
        raise PacketError("evidence packet structural and blinding limits are absent")
    for limit in data["limits"]:
        _text(limit)
    if data["audience"] == "machine-private":
        _validate_machine_fields(data)
    return data


def _validate_machine_fields(data):
    slot = data["slot"]
    slot_fields = ("slotId", "host", "arm", "journeyClass", "fixtureId", "fixtureSha256",
                   "promptId", "promptSha256", "orderPosition")
    if not isinstance(slot, dict) or set(slot) != set(slot_fields):
        raise PacketError("private packet slot record is invalid")
    _validate_slot(evaluation.AttemptSlot(*(slot[field] for field in slot_fields)))
    assessments = data["assessments"]
    if not isinstance(assessments, list) or len(assessments) > 16:
        raise PacketError("private packet assessment records are unbounded")
    records = []
    for item in assessments:
        if (not isinstance(item, dict)
                or set(item) != {"reviewerType", "reviewerId", "evidenceSha256", "rubricSha256", "labels", "model"}
                or not isinstance(item["labels"], dict)
                or set(item["labels"]) != {"success", "authorityCorrect", "fidelity"}):
            raise PacketError("private packet assessment record is invalid")
        labels = item["labels"]
        records.append(_assessment(AssessmentSummary(
            item["reviewerType"], item["reviewerId"], item["evidenceSha256"], item["rubricSha256"],
            labels["success"], labels["authorityCorrect"], labels["fidelity"], item["model"])))
    if len({(item["reviewerType"], item["reviewerId"]) for item in records}) != len(records):
        raise PacketError("private packet assessment identities are duplicated")
    source_map = data["sourceMap"]
    if not isinstance(source_map, list) or len(source_map) != len(data["excerpts"]):
        raise PacketError("private packet source-reference map is incomplete")
    for source, excerpt in zip(source_map, data["excerpts"]):
        if (not isinstance(source, dict)
                or set(source) != {"sourceId", "reference", "sourceSha256", "excerptSha256"}
                or any(source[field] != excerpt[field] for field in ("sourceId", "sourceSha256", "excerptSha256"))):
            raise PacketError("private packet source-reference map differs from its excerpts")
        _text(source["reference"])


def _quote(value):
    return "\n".join("    " + html.escape(line, quote=True) for line in value.splitlines())


def _identifier(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise PacketError("record ID must be bounded nonempty identifier text")


def _text(value):
    try:
        valid = isinstance(value, str) and bool(value.strip()) and len(value.encode("utf-8")) <= MAX_TEXT_BYTES
    except UnicodeError as exc:
        raise PacketError("packet text must be valid UTF-8") from exc
    if not valid:
        raise PacketError("packet text must be bounded nonempty UTF-8")


def _digest(value, label):
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise PacketError(f"{label} SHA-256 must be an exact lowercase digest")


def _label(value):
    if value is not None and type(value) is not bool:
        raise PacketError("observed labels must be boolean or null")


def _json(value):
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise PacketError("packet values must be bounded JSON data") from exc
    if len(raw) > MAX_PACKET_BYTES:
        raise PacketError("evidence packet exceeds its bounded size")
    return raw


__all__ = ["AssessmentSummary", "CaseEvidence", "PacketError", "RedactedExcerpt", "StepEvidence",
           "build_human_packet", "build_machine_packet", "public_packet_summary", "render_human_markdown"]
