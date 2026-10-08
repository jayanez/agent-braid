# SPDX-License-Identifier: AGPL-3.0-only
"""Single-dispatch coordination for externally implemented M4.5 sessions.

This module does not implement host, provider, MCP, grant, or human-review
adapters. It binds a previously prepared admission to one durable start marker,
then requires an injected trusted verifier to normalize and attest the adapter's
observed outcome before it can enter the evaluation ledger.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Mapping, Protocol

from . import tooling_capture as capture
from . import tooling_evaluation as evaluation


SESSION_SCHEMA = "agent-braid-m45-session-v1"
MAX_SESSION_RECORD_BYTES = 1024 * 1024
MAX_ADAPTER_OUTCOME_BYTES = 8 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TERMINAL = frozenset(evaluation.FINAL_STATUSES - {"recovered"})


class SessionError(ValueError):
    """A session is stale, already started, malformed, or unverifiable."""


@dataclass(frozen=True)
class VerifiedOutcome:
    """Outcome fields returned by the injected trusted outcome verifier."""

    status: str
    completion: bool | None
    authority_correct: bool | None
    costs: Mapping[str, int | float | None]
    input_sha256: str
    output_sha256: str
    source_timestamp: str
    interventions: int = 0
    reason: str | None = None


@dataclass(frozen=True)
class OutcomeAttestation:
    verifier_id: str
    decision_sha256: str
    subject_sha256: str
    verified_at: str


@dataclass(frozen=True)
class StartAttestation:
    verifier_id: str
    decision_sha256: str
    subject_sha256: str
    verified_at: str


@dataclass(frozen=True)
class SessionResult:
    status: str
    ledger: evaluation.EvaluationLedger
    started_path: Path
    lifecycle_path: Path | None
    lifecycle_sha256: str
    summary: str
    stop_required: bool = False
    stop_reasons: tuple[str, ...] = ()


class SessionAdapter(Protocol):
    """External one-shot adapter; it must not silently retry a dispatch."""

    def execute(self, admission: capture.AttemptAdmission) -> Any: ...


class OutcomeVerifier(Protocol):
    """Trusted external verifier for session facts and measured outcomes."""

    def verify_start(
        self, *, registration: evaluation.ValidatedRegistration,
        slot: evaluation.AttemptSlot, admission_receipt: Mapping[str, Any],
        ledger_sha256: str, measured_costs: capture.MeasuredCosts,
        stop_state: capture.StopState, subject_sha256: str,
    ) -> StartAttestation: ...

    def verify_outcome(
        self,
        *,
        registration: evaluation.ValidatedRegistration,
        slot: evaluation.AttemptSlot,
        admission_receipt: Mapping[str, Any],
        raw_outcome: Any,
        subject_sha256: str,
    ) -> tuple[VerifiedOutcome, OutcomeAttestation]: ...


def execute_admitted_attempt(
    *,
    admission: capture.AttemptAdmission,
    registration: evaluation.ValidatedRegistration,
    ledger: evaluation.EvaluationLedger,
    candidate_root: str | os.PathLike[str],
    candidate_artifact: str | os.PathLike[str],
    registration_path: str | os.PathLike[str],
    adapter: SessionAdapter,
    verifier: OutcomeVerifier,
    measured_costs: capture.MeasuredCosts,
    stop_state: capture.StopState,
) -> SessionResult:
    """Durably start one admitted slot, dispatch once, and record only verified output.

    The marker is created with O_EXCL before adapter dispatch. A started marker
    permanently consumes the slot. Adapter/verifier exceptions leave the
    attempted denominator open and write an interrupted lifecycle record; they
    never become a fabricated terminal outcome or a retry opportunity.
    """

    _validate_inputs(admission, registration, ledger, candidate_root,
                     candidate_artifact, registration_path, adapter, verifier)
    slot = next(slot for slot in ledger.slots if slot.slot_id == admission.slot_id)
    started_at = _utc_now()
    attempted_data = {
        "sourceTimestamp": started_at,
        "inputSha256": slot.fixture_sha256,
    }
    try:
        attempted_ledger = evaluation.append_slot_event(
            ledger, slot.slot_id, "attempted", attempt_id=admission.attempt_id,
            data=attempted_data,
        )
    except evaluation.EvaluationError as exc:
        raise SessionError(f"slot cannot be started: {exc}") from exc

    slot_key = _sha256(slot.slot_id.encode("utf-8"))[:32]
    started_path = admission.receipt_path.with_name(f"slot-{slot_key}.session.json")
    outcome_path = admission.receipt_path.with_name(f"slot-{slot_key}.outcome.json")
    interrupted_path = admission.receipt_path.with_name(f"slot-{slot_key}.interrupted.json")
    if outcome_path.exists() or interrupted_path.exists():
        raise SessionError("slot already has a sealed lifecycle result; do not retry")

    prior_ledger_sha256 = _ledger_sha256(ledger)
    start_payload = {
        "schemaVersion": SESSION_SCHEMA,
        "status": "started",
        "registrationSha256": registration.sha256,
        "slot": slot.as_dict(),
        "attemptId": admission.attempt_id,
        "admissionReceiptSha256": admission.receipt_sha256,
        "admissionSubjectSha256": admission.subject_sha256,
        "priorLedgerSha256": prior_ledger_sha256,
        "priorEventCount": len(ledger.events),
        "rosterSha256": _roster_sha256(ledger),
        "startedAt": started_at,
        "attemptedEvent": {
            "sequence": len(ledger.events) + 1,
            "slotId": slot.slot_id,
            "status": "attempted",
            "attemptId": admission.attempt_id,
            "data": attempted_data,
            "dataSha256": _canonical_sha256(attempted_data),
        },
    }
    started_record = _seal(start_payload)
    cohort = _claim_cohort(admission, registration, ledger, slot, started_at)
    try:
        admission_outer = _read_admission(admission, registration, slot)
        start_subject = _start_subject(registration, slot, admission, ledger,
                                       admission_outer, measured_costs, stop_state)
        start_attestation = verifier.verify_start(
            registration=registration, slot=slot, admission_receipt=admission_outer,
            ledger_sha256=prior_ledger_sha256, measured_costs=measured_costs,
            stop_state=stop_state, subject_sha256=_canonical_sha256(start_subject),
        )
        _validate_start_attestation(start_attestation, _canonical_sha256(start_subject))
        observation_floor = max(_parse_timestamp(measured_costs.observed_at),
                                _parse_timestamp(stop_state.observed_at))
        if _parse_timestamp(start_attestation.verified_at) < observation_floor:
            raise SessionError("start verifier attestation predates the fresh observations")
    except Exception as exc:
        _release_prelaunch_cohort(cohort)
        if isinstance(exc, SessionError):
            raise
        raise SessionError("fresh pre-dispatch cost/stop verification failed") from exc
    started_at = _utc_now()
    start_payload["startedAt"] = started_at
    start_payload["measuredCosts"] = capture._costs_dict(measured_costs)
    start_payload["stopState"] = capture._stop_dict(stop_state)
    start_payload["startSubjectSha256"] = _canonical_sha256(start_subject)
    start_payload["startAttestation"] = _start_attestation_dict(start_attestation)
    started_record = _seal(start_payload)
    try:
        _write_exclusive(started_path, _canonical_json(started_record))
    except FileExistsError as exc:
        # The reservation is intentionally retained: a durable cohort claim
        # without its slot marker is an ambiguous crash boundary.
        raise SessionError("slot already has a durable started marker; do not dispatch or retry") from exc
    started_sha256 = _canonical_sha256(start_payload)

    try:
        registration_file_sha256 = admission_outer["receipt"]["registrationFileSha256"]
        _check_candidate_identity(candidate_root, candidate_artifact, registration_path,
                                 registration, admission.receipt_path, registration_file_sha256)
        raw_outcome = adapter.execute(admission)
        _check_candidate_identity(candidate_root, candidate_artifact, registration_path,
                                 registration, admission.receipt_path, registration_file_sha256)
        raw_bytes = _canonical_json(raw_outcome)
        if len(raw_bytes) > MAX_ADAPTER_OUTCOME_BYTES:
            raise SessionError("adapter outcome exceeds the bounded 8 MiB receipt limit")
        raw_sha256 = _sha256(raw_bytes)
        subject = {
            "schemaVersion": SESSION_SCHEMA,
            "registrationSha256": registration.sha256,
            "slot": slot.as_dict(),
            "attemptId": admission.attempt_id,
            "admissionReceiptSha256": admission.receipt_sha256,
            "admissionSubjectSha256": admission.subject_sha256,
            "startedMarkerSha256": started_sha256,
            "rawOutcomeSha256": raw_sha256,
        }
        subject_sha256 = _canonical_sha256(subject)
        verified, attestation = verifier.verify_outcome(
            registration=registration, slot=slot,
            admission_receipt=admission_outer,
            raw_outcome=raw_outcome, subject_sha256=subject_sha256,
        )
        _validate_verified_outcome(verified, attestation, subject_sha256,
                                   slot, registration)
        cap_assessment = evaluation.check_cost_caps(
            registration,
            _cumulative_costs(measured_costs.values, verified.costs),
        )
        event_data: dict[str, Any] = {
            "sourceTimestamp": verified.source_timestamp,
            "completion": verified.completion,
            "authorityCorrect": verified.authority_correct,
            "costs": dict(verified.costs),
            "inputSha256": verified.input_sha256,
            "outputSha256": verified.output_sha256,
            "interventions": verified.interventions,
        }
        if verified.reason is not None:
            event_data["reason"] = verified.reason
        final_ledger = evaluation.append_slot_event(
            attempted_ledger, slot.slot_id, verified.status,
            attempt_id=admission.attempt_id, data=event_data,
        )
        _check_candidate_identity(candidate_root, candidate_artifact, registration_path,
                                 registration, admission.receipt_path, registration_file_sha256)
        outcome_payload = {
            "schemaVersion": SESSION_SCHEMA,
            "status": "outcome",
            "registrationSha256": registration.sha256,
            "slotId": slot.slot_id,
            "attemptId": admission.attempt_id,
            "admissionReceiptSha256": admission.receipt_sha256,
            "startedMarkerSha256": started_sha256,
            "rawOutcomeSha256": raw_sha256,
            "outcome": _outcome_dict(verified),
            "costCapAssessment": {"stop": cap_assessment.stop,
                                  "reasons": list(cap_assessment.reasons),
                                  "observed": dict(cap_assessment.observed)},
            "ledgerEvent": {
                "sequence": final_ledger.events[-1].sequence,
                "dataSha256": final_ledger.events[-1].data_sha256,
                "status": final_ledger.events[-1].status,
            },
            "attestation": _attestation_dict(attestation),
        }
        sealed = _seal(outcome_payload)
        _write_exclusive(outcome_path, _canonical_json(sealed))
        _advance_cohort(cohort, final_ledger, outcome_payload)
        return SessionResult("outcome", final_ledger, started_path, outcome_path,
                             _canonical_sha256(outcome_payload), "verified outcome recorded",
                             cap_assessment.stop, cap_assessment.reasons)
    except Exception as exc:
        # Start is already durable. Preserve it as unresolved, never call the
        # adapter again and never fill unknown measurements with zero.
        interruption = {
            "schemaVersion": SESSION_SCHEMA,
            "status": "interrupted",
            "registrationSha256": registration.sha256,
            "slotId": slot.slot_id,
            "attemptId": admission.attempt_id,
            "admissionReceiptSha256": admission.receipt_sha256,
            "startedMarkerSha256": started_sha256,
            "observedAt": _utc_now(),
            "reason": _safe_failure_reason(exc),
            "ledgerStatus": "attempted",
            "costs": {field: None for field in evaluation.COST_FIELDS},
            "limits": ["No verified terminal outcome; this record does not assert execution result or actual costs"],
        }
        sealed = _seal(interruption)
        try:
            _write_exclusive(interrupted_path, _canonical_json(sealed))
        except FileExistsError:
            pass
        return SessionResult("interrupted", attempted_ledger, started_path,
                             interrupted_path if interrupted_path.exists() else None,
                             _canonical_sha256(interruption),
                             "started session has no verified terminal outcome; do not retry",
                             True, ("session outcome or complete measured costs are unavailable",))


def reconcile_started_ledger(
    ledger: evaluation.EvaluationLedger,
    admission: capture.AttemptAdmission,
    registration: evaluation.ValidatedRegistration,
) -> evaluation.EvaluationLedger:
    """Recover only the durable attempted event after interruption; never dispatch."""

    evaluation.validate_ledger(ledger, registration)
    receipt = _read_admission(admission, registration,
                              next((item for item in ledger.slots if item.slot_id == admission.slot_id), None))
    slot = next(item for item in ledger.slots if item.slot_id == admission.slot_id)
    marker = _read_sealed(_started_path(admission, slot), "started marker")
    _validate_start_marker(marker, admission, registration, slot, _roster_sha256(ledger))
    if _ledger_sha256(ledger) == marker["priorLedgerSha256"]:
        event = marker["attemptedEvent"]
        updated = evaluation.append_slot_event(
            ledger, slot.slot_id, "attempted", attempt_id=admission.attempt_id,
            data=event["data"],
        )
        return updated
    if ledger.current_status(slot.slot_id) == "attempted":
        current = ledger.current_event(slot.slot_id)
        expected = marker["attemptedEvent"]
        if (current is not None and current.attempt_id == admission.attempt_id
                and current.sequence == expected["sequence"]
                and current.data == expected["data"]
                and current.data_sha256 == expected["dataSha256"]):
            return ledger
    raise SessionError("ledger differs from the exact pre-start snapshot; preserve for review")


def inspect_session(
    admission: capture.AttemptAdmission,
    registration: evaluation.ValidatedRegistration,
    ledger: evaluation.EvaluationLedger,
) -> Mapping[str, Any]:
    """Read-only lifecycle inspection; it never re-dispatches or repairs outcomes."""

    evaluation.validate_ledger(ledger, registration)
    slot = next((item for item in ledger.slots if item.slot_id == admission.slot_id), None)
    admission_outer = _read_admission(admission, registration, slot)
    if slot is None:
        raise SessionError("admission slot is absent from the registered roster")
    started = _read_sealed(_started_path(admission, slot), "started marker")
    _validate_start_marker(started, admission, registration, slot, _roster_sha256(ledger))
    outcome_path = _lifecycle_path(admission, slot, "outcome")
    interrupted_path = _lifecycle_path(admission, slot, "interrupted")
    if outcome_path.exists():
        outcome = _read_sealed(outcome_path, "outcome receipt")
        _validate_lifecycle_binding(outcome, "outcome", admission, registration, slot, started)
        _validate_outcome_record(outcome, admission, registration, slot,
                                 admission_outer["receipt"], started)
        ledger_event = ledger.current_event(slot.slot_id)
        stored_event = outcome.get("ledgerEvent", {})
        ledger_matches = (ledger_event is not None
                          and ledger_event.sequence == stored_event.get("sequence")
                          and ledger_event.status == stored_event.get("status")
                          and ledger_event.data_sha256 == stored_event.get("dataSha256"))
        return {"status": "outcome" if ledger_matches else "outcome-ledger-unreconciled",
                "ledgerEventPresent": ledger_matches,
                "startedSha256": started["recordSha256"],
                "outcomeSha256": outcome["recordSha256"], "slotId": slot.slot_id,
                "attemptId": admission.attempt_id}
    if interrupted_path.exists():
        interrupted = _read_sealed(interrupted_path, "interruption receipt")
        _validate_lifecycle_binding(interrupted, "interrupted", admission, registration, slot, started)
        return {"status": "interrupted", "startedSha256": started["recordSha256"],
                "interruptedSha256": interrupted["recordSha256"], "slotId": slot.slot_id,
                "attemptId": admission.attempt_id, "reason": interrupted["reason"]}
    return {"status": "started-unknown", "startedSha256": started["recordSha256"],
            "slotId": slot.slot_id, "attemptId": admission.attempt_id,
            "limits": ["A durable start exists without a sealed outcome; never retry"]}


def _validate_inputs(admission, registration, ledger, candidate_root,
                     candidate_artifact, registration_path, adapter, verifier) -> None:
    if not isinstance(admission, capture.AttemptAdmission):
        raise SessionError("a genuine capture admission receipt is required")
    if not callable(getattr(adapter, "execute", None)):
        raise SessionError("an external one-shot session adapter is required")
    if not callable(getattr(verifier, "verify_outcome", None)):
        raise SessionError("a trusted outcome verifier is required")
    if not callable(getattr(verifier, "verify_start", None)):
        raise SessionError("a trusted fresh-observation verifier is required")
    try:
        evaluation.validate_ledger(ledger, registration)
        slot = next((item for item in ledger.slots if item.slot_id == admission.slot_id), None)
        _read_admission(admission, registration, slot)
    except (evaluation.EvaluationError, SessionError) as exc:
        raise SessionError(f"admission or ledger validation failed: {exc}") from exc
    if slot is None or ledger.current_status(slot.slot_id) != "not-started":
        raise SessionError("slot is absent or already attempted; do not retry")
    outer = _read_admission(admission, registration, slot)
    _check_candidate_identity(candidate_root, candidate_artifact, registration_path,
                             registration, admission.receipt_path,
                             outer["receipt"]["registrationFileSha256"])


def _read_admission(admission, registration, slot):
    if slot is None:
        raise SessionError("admission slot is absent from the registered roster")
    root = capture.receipt_directory_for(registration.sha256)
    try:
        capture._ensure_private_store(root)
    except capture.CaptureAdmissionError as exc:
        raise SessionError("fixed per-user admission store is not safe") from exc
    requested = Path(admission.receipt_path)
    if requested.is_symlink():
        raise SessionError("admission receipt cannot be a symbolic link")
    path = requested.resolve(strict=True)
    if path.parent != root.resolve(strict=True):
        raise SessionError("admission receipt is outside the fixed registration store")
    expected_name = "slot-" + _sha256(slot.slot_id.encode("utf-8"))[:32] + ".json"
    if path.name != expected_name or path.is_symlink():
        raise SessionError("admission receipt path does not match the registered slot")
    _private_file(path)
    outer = _read_json(path, "admission receipt")
    if set(outer) != {"receipt", "receiptSha256"}:
        raise SessionError("admission receipt fields are invalid")
    body = outer.get("receipt")
    if not isinstance(body, dict) or _canonical_sha256(body) != outer.get("receiptSha256"):
        raise SessionError("admission receipt hash mismatch")
    if (outer["receiptSha256"] != admission.receipt_sha256
            or body.get("attemptId") != admission.attempt_id
            or body.get("subjectSha256") != admission.subject_sha256
            or body.get("status") != "admitted-not-started"
            or body.get("registrationSha256") != registration.sha256
            or body.get("slot") != slot.as_dict()):
        raise SessionError("admission receipt identity or status differs from the supplied admission")
    subject_keys = {
        "schemaVersion", "registrationSha256", "slot", "candidate", "registrationFileSha256",
        "fixturePromptInventorySha256", "hostBuild", "authorization", "measuredCosts", "stopState", "limits",
    }
    subject = {key: body.get(key) for key in subject_keys}
    if _canonical_sha256(subject) != body.get("subjectSha256"):
        raise SessionError("admission subject digest does not match its immutable receipt")
    if body.get("candidate", {}).get("commit") != registration.data["candidate"]["commit"] \
            or body.get("candidate", {}).get("artifactSha256") != registration.data["candidate"]["sha256"]:
        raise SessionError("admission candidate identity differs from the frozen registration")
    return outer


def _claim_cohort(admission, registration, ledger, slot, started_at):
    """Reserve the registration's single dispatch lane against its ledger head."""
    root = capture.receipt_directory_for(registration.sha256)
    head_path = root / "cohort-head.json"
    active_path = root / "cohort-active.json"
    ledger_sha = _ledger_sha256(ledger)
    if not head_path.exists():
        try:
            _write_atomic_json(head_path, _seal({
                "schemaVersion": SESSION_SCHEMA, "registrationSha256": registration.sha256,
                "rosterSha256": _roster_sha256(ledger), "headLedgerSha256": ledger_sha,
                "revision": 0,
            }), exclusive=True)
        except FileExistsError:
            # Another process initialized the same immutable initial head.
            pass
    head = _read_sealed(head_path, "cohort ledger head")
    if (head.get("registrationSha256") != registration.sha256
            or head.get("rosterSha256") != _roster_sha256(ledger)
            or head.get("headLedgerSha256") != ledger_sha):
        raise SessionError("stale ledger snapshot; reload the persisted cohort head before dispatch")
    reservation = _seal({
        "schemaVersion": SESSION_SCHEMA, "registrationSha256": registration.sha256,
        "rosterSha256": _roster_sha256(ledger), "priorLedgerSha256": ledger_sha,
        "slotId": slot.slot_id, "attemptId": admission.attempt_id,
        "admissionReceiptSha256": admission.receipt_sha256,
        "startedAt": started_at, "status": "active",
    })
    try:
        _write_exclusive(active_path, _canonical_json(reservation))
    except FileExistsError as exc:
        raise SessionError("registration already has an active or interrupted slot; inspect before proceeding") from exc
    # Close the check/create race by re-reading the head after acquiring the
    # exclusive marker. No other dispatcher can advance it while this marker exists.
    latest = _read_sealed(head_path, "cohort ledger head")
    if latest.get("headLedgerSha256") != ledger_sha:
        raise SessionError("cohort head changed during reservation; inspect the active marker")
    return (root, head_path, active_path, reservation, head)


def _start_subject(registration, slot, admission, ledger, admission_outer,
                   measured_costs, stop_state):
    if not isinstance(measured_costs, capture.MeasuredCosts):
        raise SessionError("fresh cumulative cost observation is required")
    if not isinstance(stop_state, capture.StopState):
        raise SessionError("fresh stop-state observation is required")
    try:
        capture._validate_costs(measured_costs)
        capture._validate_prior_costs(ledger, measured_costs)
        capture._validate_stop_state(stop_state)
    except capture.CaptureAdmissionError as exc:
        raise SessionError(f"fresh pre-dispatch observations are invalid: {exc}") from exc
    if stop_state.incident_open or stop_state.unrecoverable_run or stop_state.consecutive_infrastructure_failures >= 2:
        raise SessionError("fresh stop-state observation blocks dispatch")
    baseline = admission_outer["receipt"]["measuredCosts"]["values"]
    for field in evaluation.COST_FIELDS:
        old, new = baseline[field], measured_costs.values[field]
        if old is not None and (new is None or new < old):
            raise SessionError(f"fresh cost observation regressed or lost {field}")
    cap = evaluation.check_cost_caps(registration, measured_costs.values)
    if cap.stop:
        raise SessionError("fresh cumulative cost observation does not establish cap compliance")
    admission_at = admission_outer["receipt"]["measuredCosts"]["observedAt"]
    event_times = [event.data.get("sourceTimestamp") for event in ledger.events]
    floor_value = max(
        [admission_at, *[value for value in event_times if isinstance(value, str)]],
        key=_parse_timestamp,
    )
    floor = _parse_timestamp(floor_value).isoformat().replace("+00:00", "Z")
    for value, label in ((measured_costs.observed_at, "cost observation"),
                         (stop_state.observed_at, "stop-state observation")):
        _timestamp(value, label)
        if _parse_timestamp(value) < _parse_timestamp(floor):
            raise SessionError(f"{label} predates the latest admission or ledger cost floor")
    return {
        "schemaVersion": SESSION_SCHEMA, "registrationSha256": registration.sha256,
        "slot": slot.as_dict(), "attemptId": admission.attempt_id,
        "admissionReceiptSha256": admission.receipt_sha256,
        "admissionSubjectSha256": admission.subject_sha256,
        "ledgerSha256": _ledger_sha256(ledger), "rosterSha256": _roster_sha256(ledger),
        "measuredCosts": capture._costs_dict(measured_costs),
        "stopState": capture._stop_dict(stop_state),
        "minimumObservedAt": floor,
    }


def _validate_start_attestation(value, subject_sha256):
    if not isinstance(value, StartAttestation):
        raise SessionError("trusted verifier returned no typed start attestation")
    if not _SHA256.fullmatch(value.decision_sha256) or value.subject_sha256 != subject_sha256:
        raise SessionError("start attestation does not bind the exact ledger/cost/stop subject")
    _text(value.verifier_id, "start verifier ID")
    _timestamp(value.verified_at, "startVerifiedAt")


def _release_prelaunch_cohort(cohort):
    """Release only a reservation that has not crossed the durable-start boundary."""
    root, _head_path, active_path, reservation, _head = cohort
    try:
        active = _read_sealed(active_path, "active cohort reservation")
        if active.get("recordSha256") == reservation.get("recordSha256"):
            active_path.unlink()
            _fsync_directory(root)
    except (OSError, SessionError):
        # Failure to release is fail-closed: the stale marker blocks later work.
        pass


def _advance_cohort(cohort, ledger, outcome_payload):
    root, head_path, active_path, reservation, head = cohort
    active = _read_sealed(active_path, "active cohort reservation")
    if (active.get("recordSha256") != reservation.get("recordSha256")
            or active.get("priorLedgerSha256") != head.get("headLedgerSha256")):
        raise SessionError("cohort reservation changed; preserve the outcome for inspection")
    updated = _seal({
        "schemaVersion": SESSION_SCHEMA, "registrationSha256": active["registrationSha256"],
        "rosterSha256": active["rosterSha256"], "headLedgerSha256": _ledger_sha256(ledger),
        "revision": head["revision"] + 1,
        "lastOutcomeSha256": _canonical_sha256(outcome_payload),
    })
    _write_atomic_json(head_path, updated)
    active_path.unlink()
    _fsync_directory(root)


def _write_atomic_json(path, value, *, exclusive=False):
    path = Path(path)
    raw = _canonical_json(value)
    if exclusive:
        _write_exclusive(path, raw)
        return
    temporary = path.with_name(path.name + "." + os.urandom(8).hex() + ".tmp")
    _write_exclusive(temporary, raw)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _check_candidate_identity(candidate_root, artifact, registration_path, registration, receipt_path,
                              expected_registration_file_sha256):
    candidate = Path(candidate_root).resolve(strict=True)
    artifact = Path(artifact).resolve(strict=True)
    registration_path = Path(registration_path).resolve(strict=True)
    external = (artifact, registration_path, Path(receipt_path).resolve(strict=True))
    if (any(path.is_relative_to(candidate) or candidate.is_relative_to(path) for path in external)
            or artifact == registration_path
            or artifact.is_relative_to(registration_path) or registration_path.is_relative_to(artifact)):
        raise SessionError("candidate, registration, artifact, and lifecycle roots must remain disjoint")
    try:
        raw = capture._read_bounded(registration_path, capture.MAX_REGISTRATION_BYTES, "registration")
        parsed = capture._strict_json(raw, "registration")
        artifact_sha = capture._hash_file(artifact, capture.MAX_ARTIFACT_BYTES)
        commit = capture._git_head(candidate)
        dirty = capture._git_dirty(candidate)
        hashes = capture.input_hashes(candidate)
    except Exception as exc:
        raise SessionError("candidate or frozen inputs became unavailable") from exc
    expected_inputs = {item["fixtureId"]: item["sha256"] for item in registration.data["fixtures"]}
    expected_inputs.update({item["promptId"]: item["sha256"] for item in registration.data["prompts"]})
    if (dirty or commit != registration.data["candidate"]["commit"]
            or artifact_sha != registration.data["candidate"]["sha256"]
            or _sha256(raw) != expected_registration_file_sha256
            or parsed != registration.data or hashes != expected_inputs):
        raise SessionError("candidate, registration, or immutable inputs drifted; retain the slot")


def _validate_verified_outcome(value, attestation, subject_sha256, slot, registration):
    if not isinstance(value, VerifiedOutcome):
        raise SessionError("trusted verifier returned no typed outcome")
    if not isinstance(attestation, OutcomeAttestation):
        raise SessionError("trusted verifier returned no outcome attestation")
    if value.status not in _TERMINAL:
        raise SessionError("verified outcome status is not an allowed terminal status")
    if value.input_sha256 != slot.fixture_sha256:
        raise SessionError("verified outcome input hash does not match the registered fixture")
    if not _SHA256.fullmatch(value.output_sha256):
        raise SessionError("verified outcome output hash is malformed")
    if not _SHA256.fullmatch(attestation.decision_sha256) or attestation.subject_sha256 != subject_sha256:
        raise SessionError("outcome attestation does not bind the exact session subject")
    _text(attestation.verifier_id, "verifier ID")
    _timestamp(attestation.verified_at, "verifiedAt")
    _timestamp(value.source_timestamp, "sourceTimestamp")
    if type(value.completion) not in (bool, type(None)) or type(value.authority_correct) not in (bool, type(None)):
        raise SessionError("completion and authority labels must be true, false, or null")
    if value.status == "valid" and value.completion is not True:
        raise SessionError("valid outcome must report completion true")
    if not isinstance(value.costs, Mapping):
        raise SessionError("verified costs must retain explicit unknowns")
    try:
        evaluation._validate_observed_costs(value.costs)
    except evaluation.EvaluationError as exc:
        raise SessionError(f"verified costs are malformed: {exc}") from exc
    if type(value.interventions) is not int or value.interventions < 0:
        raise SessionError("interventions must be a nonnegative integer")
    if value.reason is not None:
        _text(value.reason, "outcome reason")
    if slot.host not in {host["name"] for host in registration.data["hosts"]}:
        raise SessionError("slot host is absent from the frozen registration")


def _validate_start_marker(marker, admission, registration, slot, expected_roster_sha256):
    if (marker.get("status") != "started"
            or marker.get("registrationSha256") != registration.sha256
            or marker.get("slot") != slot.as_dict()
            or marker.get("attemptId") != admission.attempt_id
            or marker.get("admissionReceiptSha256") != admission.receipt_sha256
            or marker.get("admissionSubjectSha256") != admission.subject_sha256
            or marker.get("rosterSha256") != expected_roster_sha256):
        raise SessionError("started marker does not bind this admission, slot, and registration")
    start_attestation = marker.get("startAttestation")
    if (not isinstance(start_attestation, dict)
            or start_attestation.get("subjectSha256") != marker.get("startSubjectSha256")
            or not _SHA256.fullmatch(start_attestation.get("decisionSha256", ""))):
        raise SessionError("started marker lacks a subject-bound pre-dispatch observation attestation")
    _timestamp(start_attestation.get("verifiedAt"), "startVerifiedAt")
    if not isinstance(marker.get("measuredCosts"), dict) or not isinstance(marker.get("stopState"), dict):
        raise SessionError("started marker lacks fresh cost/stop observations")
    event = marker.get("attemptedEvent")
    if (not isinstance(event, dict) or event.get("slotId") != slot.slot_id
            or event.get("status") != "attempted" or event.get("attemptId") != admission.attempt_id
            or event.get("data", {}).get("inputSha256") != slot.fixture_sha256
            or _canonical_sha256(event.get("data")) != event.get("dataSha256")):
        raise SessionError("started marker has an invalid attempted ledger event")
    if (not _SHA256.fullmatch(marker.get("priorLedgerSha256", ""))
            or type(marker.get("priorEventCount")) is not int or marker["priorEventCount"] < 0
            or type(event.get("sequence")) is not int
            or event["sequence"] != marker["priorEventCount"] + 1):
        raise SessionError("started marker does not bind a valid pre-start ledger identity")
    _timestamp(marker.get("startedAt"), "startedAt")


def _validate_lifecycle_binding(record, status, admission, registration, slot, started):
    if (record.get("status") != status
            or record.get("registrationSha256") != registration.sha256
            or record.get("slotId") != slot.slot_id
            or record.get("attemptId") != admission.attempt_id
            or record.get("admissionReceiptSha256") != admission.receipt_sha256
            or record.get("startedMarkerSha256") != started["recordSha256"]):
        raise SessionError("lifecycle record is not bound to this admission and start")


def _validate_outcome_record(record, admission, registration, slot, admission_body, started):
    outcome = record.get("outcome")
    attestation = record.get("attestation")
    if not isinstance(outcome, dict) or not isinstance(attestation, dict):
        raise SessionError("sealed outcome receipt is incomplete")
    try:
        verified = VerifiedOutcome(
            status=outcome["status"], completion=outcome["completion"],
            authority_correct=outcome["authorityCorrect"], costs=outcome["costs"],
            input_sha256=outcome["inputSha256"], output_sha256=outcome["outputSha256"],
            source_timestamp=outcome["sourceTimestamp"], interventions=outcome["interventions"],
            reason=outcome["reason"],
        )
        attested = OutcomeAttestation(
            verifier_id=attestation["verifierId"], decision_sha256=attestation["decisionSha256"],
            subject_sha256=attestation["subjectSha256"], verified_at=attestation["verifiedAt"],
        )
    except (KeyError, TypeError) as exc:
        raise SessionError("sealed outcome receipt fields are invalid") from exc
    raw_sha = record.get("rawOutcomeSha256")
    if not isinstance(raw_sha, str) or not _SHA256.fullmatch(raw_sha):
        raise SessionError("raw adapter receipt digest is invalid")
    subject = {
        "schemaVersion": SESSION_SCHEMA,
        "registrationSha256": registration.sha256,
        "slot": slot.as_dict(),
        "attemptId": admission.attempt_id,
        "admissionReceiptSha256": admission.receipt_sha256,
        "admissionSubjectSha256": admission.subject_sha256,
        "startedMarkerSha256": started["recordSha256"],
        "rawOutcomeSha256": raw_sha,
    }
    _validate_verified_outcome(verified, attested, _canonical_sha256(subject), slot, registration)
    if record.get("outcome") != _outcome_dict(verified):
        raise SessionError("sealed outcome differs from its normalized form")


def _started_path(admission, slot):
    return _lifecycle_path(admission, slot, "session")


def _lifecycle_path(admission, slot, kind):
    key = _sha256(slot.slot_id.encode("utf-8"))[:32]
    return Path(admission.receipt_path).with_name(f"slot-{key}.{kind}.json")


def _read_sealed(path, label):
    record = _read_json(path, label)
    payload = {key: value for key, value in record.items() if key != "recordSha256"}
    if record.get("recordSha256") != _canonical_sha256(payload):
        raise SessionError(f"{label} hash mismatch")
    return record


def _read_json(path, label):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise SessionError(f"{label} is unavailable or unsafe")
    _private_file(path)
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_SESSION_RECORD_BYTES + 1)
        if len(raw) > MAX_SESSION_RECORD_BYTES:
            raise SessionError(f"{label} exceeds the bounded read limit")
        value = capture._strict_json(raw, label)
    except (OSError, UnicodeError, json.JSONDecodeError, capture.CaptureAdmissionError) as exc:
        raise SessionError(f"{label} is not bounded UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SessionError(f"{label} must be a JSON object")
    return value


def _private_file(path):
    try:
        info = path.lstat()
    except OSError as exc:
        raise SessionError("private session file is unavailable") from exc
    if not path.is_file() or path.is_symlink() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise SessionError("session file must be user-owned, regular, and mode 0600")


def _write_exclusive(path, raw):
    path = Path(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        raise
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _seal(payload):
    return {**payload, "recordSha256": _canonical_sha256(payload)}


def _ledger_sha256(ledger):
    evaluation._validate_ledger_history(ledger)
    return _canonical_sha256(ledger.as_dict())


def _roster_sha256(ledger):
    return _canonical_sha256([slot.as_dict() for slot in ledger.slots])


def _cumulative_costs(before, attempt):
    """Combine verified per-attempt costs with the admission's measured baseline."""
    try:
        evaluation._validate_observed_costs(before)
        evaluation._validate_observed_costs(attempt)
    except evaluation.EvaluationError as exc:
        raise SessionError(f"cost snapshot is malformed: {exc}") from exc
    cumulative: dict[str, int | float | None] = {}
    for field in evaluation.COST_FIELDS:
        previous, current = before[field], attempt[field]
        if previous is None or current is None:
            cumulative[field] = None
        elif field in {"rss_bytes", "disk_bytes"}:
            cumulative[field] = max(previous, current)
        else:
            cumulative[field] = previous + current
    return cumulative


def _outcome_dict(value):
    return {"status": value.status, "completion": value.completion,
            "authorityCorrect": value.authority_correct, "costs": dict(value.costs),
            "inputSha256": value.input_sha256, "outputSha256": value.output_sha256,
            "sourceTimestamp": value.source_timestamp, "interventions": value.interventions,
            "reason": value.reason}


def _attestation_dict(value):
    return {"verifierId": value.verifier_id, "decisionSha256": value.decision_sha256,
            "subjectSha256": value.subject_sha256, "verifiedAt": value.verified_at}


def _canonical_json(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise SessionError("session values must be bounded JSON data") from exc


def _canonical_sha256(value):
    return _sha256(_canonical_json(value))


def _sha256(value):
    return hashlib.sha256(value).hexdigest()


def _timestamp(value, label="timestamp"):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise SessionError(f"{label} must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise SessionError(f"{label} must be a timezone-aware ISO timestamp")


def _parse_timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _start_attestation_dict(value):
    return {"verifierId": value.verifier_id, "decisionSha256": value.decision_sha256,
            "subjectSha256": value.subject_sha256, "verifiedAt": value.verified_at}


def _text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 2048:
        raise SessionError(f"{label} must be bounded nonempty text")


def _safe_failure_reason(exc):
    # Error messages can contain prompt or provider material; retain only the
    # exception type and a fixed explanation in the public lifecycle record.
    return f"{type(exc).__name__}: verified outcome unavailable"


def _utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "OutcomeAttestation", "OutcomeVerifier", "SessionAdapter", "SessionError", "StartAttestation",
    "SessionResult", "VerifiedOutcome", "execute_admitted_attempt",
    "inspect_session", "reconcile_started_ledger",
]
