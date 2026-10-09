# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed admission receipts for a future registered M4.5 capturer.

This module prepares one immutable attempt context. It never starts a host,
provider, MCP client, fixture execution, grant operation, or capture session.
Approval and measurement authenticity belong to an explicitly injected trusted
decision verifier; the structural evaluator cannot authenticate them.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping, Protocol
import uuid

from . import tooling_evaluation as evaluation
from . import tooling_subscription as subscription_policy
from .tooling_fixtures import FixtureInventoryError, load_inventory


CAPTURE_RECEIPT_SCHEMA = "agent-braid-m45-capture-admission-v1"
MAX_REGISTRATION_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT = re.compile(r"^[0-9a-f]{40,64}$")


class CaptureAdmissionError(ValueError):
    """Attempt admission was unavailable, stale, unauthorized, or over budget."""


@dataclass(frozen=True)
class AuthorizationContext:
    """Existing decision/run references to be authenticated by the trusted caller.

    `mode` must describe the registered journey: `none`, `missing-grant`,
    `existing-grant`, or `interrupted-run`. References are opaque identifiers
    and hashes, not authorization. This module never creates a grant.
    """

    mode: str
    decision_ref: str
    decision_sha256: str
    grant_ref: str | None = None
    grant_sha256: str | None = None
    plan_sha256: str | None = None
    interrupted_run_ref: str | None = None
    interrupted_run_sha256: str | None = None
    grant_action: str | None = None


@dataclass(frozen=True)
class MeasuredCosts:
    """Caller-collected cumulative costs and provenance for admission."""

    values: Mapping[str, int | float | None]
    source_ref: str
    source_sha256: str
    observed_at: str


@dataclass(frozen=True)
class StopState:
    """Externally observed stop conditions, authenticated by the verifier."""

    incident_open: bool
    unrecoverable_run: bool
    consecutive_infrastructure_failures: int
    source_ref: str
    source_sha256: str
    observed_at: str


@dataclass(frozen=True)
class DecisionAttestation:
    """Trusted verifier's attestation over the exact admission subject."""

    verifier_id: str
    decision_sha256: str
    subject_sha256: str
    verified_at: str


class AdmissionVerifier(Protocol):
    """Trusted caller boundary that authenticates human/rights/measurement facts."""

    def attest(
        self,
        *,
        registration: evaluation.ValidatedRegistration,
        slot: evaluation.AttemptSlot,
        authorization: AuthorizationContext,
        costs: MeasuredCosts,
        stop_state: StopState,
        subject_sha256: str,
        subscription: subscription_policy.SubscriptionObservation | None = None,
    ) -> DecisionAttestation: ...


@dataclass(frozen=True)
class AttemptAdmission:
    """Receipt path and digest for a prepared, not-started attempt."""

    attempt_id: str
    slot_id: str
    receipt_path: Path
    receipt_sha256: str
    subject_sha256: str
    subscription_binding: subscription_policy.SubscriptionBinding | None = None


def input_hashes(candidate_root: str | os.PathLike[str]) -> dict[str, str]:
    """Read and verify the candidate's frozen 18-fixture/six-prompt inventory."""

    root = Path(candidate_root).resolve(strict=True)
    try:
        inventory = load_inventory(
            source_checkout=True, assets_dir=root / "examples" / "tooling")
    except (OSError, FixtureInventoryError) as exc:
        raise CaptureAdmissionError("candidate fixture/prompt inventory is missing or changed") from exc
    result = {
        item.fixture_id: item.definition_sha256 for item in inventory.fixtures
    }
    result.update({item.prompt_id: item.sha256 for item in inventory.prompts})
    if len(result) != 24:
        raise CaptureAdmissionError("candidate input inventory is incomplete")
    return result


def receipt_directory_for(registration_sha256: str) -> Path:
    """Return the fixed per-user store for one frozen registration cohort."""

    _require_digest(registration_sha256, "registration SHA-256")
    return _user_state_root() / registration_sha256


def prepare_attempt(
    *,
    registration_path: str | os.PathLike[str],
    candidate_root: str | os.PathLike[str],
    candidate_artifact: str | os.PathLike[str],
    ledger: evaluation.EvaluationLedger,
    slot_id: str,
    authorization: AuthorizationContext,
    costs: MeasuredCosts,
    stop_state: StopState,
    verifier: AdmissionVerifier,
    receipt_directory: str | os.PathLike[str],
    subscription: subscription_policy.SubscriptionObservation | None = None,
) -> AttemptAdmission:
    """Validate exact frozen inputs and write one private hash-bound admission.

    This is a preflight receipt only. It records no `attempted` ledger event and
    does not schedule or execute the admitted host/model/fixture interaction.
    The caller must supply an authenticator; a structural registration alone
    never crosses the human approval boundary.
    """

    if verifier is None or not callable(getattr(verifier, "attest", None)):
        raise CaptureAdmissionError("a trusted decision verifier is required for admission")
    candidate = Path(candidate_root).resolve(strict=True)
    artifact = Path(candidate_artifact).resolve(strict=True)
    registration_file = Path(registration_path).resolve(strict=True)
    requested_output = Path(receipt_directory).expanduser().absolute()
    if any(path.is_relative_to(candidate) or candidate.is_relative_to(path)
           for path in (artifact, registration_file)):
        raise CaptureAdmissionError("candidate, registration, artifact, and receipt roots must be disjoint")
    registration_raw = _read_bounded(registration_file, MAX_REGISTRATION_BYTES, "registration")
    registration_sha256 = _sha256(registration_raw)
    registration_data = _strict_json(registration_raw, "registration")
    artifact_sha256 = _hash_file(artifact, MAX_ARTIFACT_BYTES)
    candidate_commit = _git_head(candidate)
    if _git(candidate, "rev-parse", "--show-prefix"):
        raise CaptureAdmissionError("candidate root must be the Git checkout root")
    if _git_dirty(candidate):
        raise CaptureAdmissionError("candidate checkout is dirty; freeze a clean candidate before admission")
    frozen_input_hashes = input_hashes(candidate)
    try:
        registration = evaluation.validate_registration(
            registration_data,
            expected_candidate_sha256=artifact_sha256,
            expected_input_hashes=frozen_input_hashes,
        )
        evaluation.validate_ledger(ledger, registration)
    except (evaluation.EvaluationError, CaptureAdmissionError) as exc:
        raise CaptureAdmissionError(f"frozen registration or ledger validation failed: {exc}") from exc
    expected_output = receipt_directory_for(registration.sha256)
    if requested_output != expected_output:
        raise CaptureAdmissionError("receipt directory must be the fixed per-user store for this registration cohort")
    output = expected_output
    if output.resolve(strict=False).is_relative_to(candidate) or candidate.is_relative_to(output.resolve(strict=False)):
        raise CaptureAdmissionError("candidate and per-user receipt roots must be disjoint")
    slot = _registered_slot(ledger, slot_id)
    host_record = next(item for item in registration.data["hosts"] if item["name"] == slot.host)
    candidate_record = registration.data["candidate"]
    if candidate_commit != candidate_record["commit"]:
        raise CaptureAdmissionError("candidate checkout commit differs from the frozen registration")
    if ledger.current_status(slot_id) != "not-started":
        raise CaptureAdmissionError("slot has already started or reached an outcome; do not retry")
    _validate_context(slot, authorization)
    _validate_costs(costs)
    _validate_prior_costs(ledger, costs)
    _validate_stop_state(stop_state)
    if stop_state.incident_open:
        raise CaptureAdmissionError("capture is stopped by an open incident")
    if stop_state.unrecoverable_run:
        raise CaptureAdmissionError("capture is stopped by an unrecoverable run")
    if stop_state.consecutive_infrastructure_failures >= 2:
        raise CaptureAdmissionError("capture is stopped after two consecutive infrastructure failures")
    cap_check = evaluation.check_cost_caps(registration, costs.values)
    if cap_check.stop:
        raise CaptureAdmissionError("measured cumulative costs do not establish cap compliance: "
                                    + "; ".join(cap_check.reasons))

    binding = subscription_policy.binding_from_registration(registration, slot_id, slot.host)
    if binding is not None:
        try:
            subscription_policy.check_observation(subscription, binding)
        except subscription_policy.SubscriptionError as exc:
            raise CaptureAdmissionError("subscription admission refused: " + str(exc)) from exc
    elif subscription is not None:
        raise CaptureAdmissionError("subscription observation requires a frozen billing policy")

    subject = {
        "schemaVersion": CAPTURE_RECEIPT_SCHEMA,
        "registrationSha256": registration.sha256,
        "slot": slot.as_dict(),
        "candidate": {
            "commit": candidate_commit,
            "artifactSha256": artifact_sha256,
            "version": candidate_record["version"],
        },
        "registrationFileSha256": registration_sha256,
        "fixturePromptInventorySha256": _sha256(_canonical_json(frozen_input_hashes)),
        "hostBuild": host_record,
        "authorization": _authorization_dict(authorization),
        "measuredCosts": _costs_dict(costs),
        "stopState": _stop_dict(stop_state),
        "limits": [
            "Admission receipt only; no host, provider, grant, or attempt was started",
            "Decision authenticity is asserted only by the configured trusted verifier",
            "Measured cost completeness and stop-state truth depend on verifier provenance",
        ],
    }
    if binding is not None:
        subject["subscription"] = subscription.as_dict()
    subject_sha256 = _sha256(_canonical_json(subject))
    try:
        verification_args = dict(
            registration=registration, slot=slot, authorization=authorization,
            costs=costs, stop_state=stop_state, subject_sha256=subject_sha256,
        )
        if binding is not None:
            # Legacy verifiers cannot silently attest a newly constrained policy.
            verification_args["subscription"] = subscription
        attestation = verifier.attest(**verification_args)
    except Exception as exc:
        raise CaptureAdmissionError("trusted decision verification failed") from exc
    _validate_attestation(attestation, subject_sha256)
    if binding is not None:
        try:
            subscription_policy.check_observation(subscription, binding)
        except subscription_policy.SubscriptionError as exc:
            raise CaptureAdmissionError("subscription observation expired during verification") from exc
    # Recheck immutable inputs after the potentially external verifier call.
    if _hash_file(artifact, MAX_ARTIFACT_BYTES) != artifact_sha256:
        raise CaptureAdmissionError("candidate artifact changed during admission")
    if _git_head(candidate) != candidate_commit or _git_dirty(candidate):
        raise CaptureAdmissionError("candidate checkout changed during admission")
    if _sha256(_read_bounded(registration_file, MAX_REGISTRATION_BYTES, "registration")) != registration_sha256:
        raise CaptureAdmissionError("registration changed during admission")
    if input_hashes(candidate) != frozen_input_hashes:
        raise CaptureAdmissionError("candidate input inventory changed during admission")

    attempt_id = "cap-" + uuid.uuid4().hex
    receipt_body = {
        **subject,
        "subjectSha256": subject_sha256,
        "attestation": {
            "verifierId": attestation.verifier_id,
            "decisionSha256": attestation.decision_sha256,
            "subjectSha256": attestation.subject_sha256,
            "verifiedAt": attestation.verified_at,
        },
        "attemptId": attempt_id,
        "admittedAt": _utc_now(),
        "status": "admitted-not-started",
    }
    receipt_sha256 = _sha256(_canonical_json(receipt_body))
    receipt = {"receipt": receipt_body, "receiptSha256": receipt_sha256}
    _ensure_private_store(output)
    receipt_path = output / ("slot-" + _sha256(slot_id.encode("utf-8"))[:32] + ".json")
    _write_exclusive(receipt_path, _canonical_json(receipt))
    return AttemptAdmission(attempt_id, slot_id, receipt_path, receipt_sha256, subject_sha256, binding)


def _registered_slot(ledger: evaluation.EvaluationLedger, slot_id: str) -> evaluation.AttemptSlot:
    for slot in ledger.slots:
        if slot.slot_id == slot_id:
            return slot
    raise CaptureAdmissionError("slot is not present in the validated 108-slot roster")


def _validate_context(slot: evaluation.AttemptSlot, context: AuthorizationContext) -> None:
    if not isinstance(context, AuthorizationContext):
        raise CaptureAdmissionError("authorization context is required")
    journey = slot.journey_class
    expected = {
        "refuse-missing-grant": "missing-grant",
        "execute-granted-batch-verify": "existing-grant",
        "inspect-recover-interruption": "interrupted-run",
    }.get(journey, "none")
    if context.mode != expected:
        raise CaptureAdmissionError("authorization context does not match the registered journey")
    _require_text(context.decision_ref, "decision reference")
    _require_digest(context.decision_sha256, "decision reference SHA-256")
    if expected == "existing-grant":
        if context.grant_action != "execute":
            raise CaptureAdmissionError("execute journey requires an existing execute grant")
        _require_text(context.grant_ref, "existing grant reference")
        _require_digest(context.grant_sha256, "existing grant SHA-256")
        _require_digest(context.plan_sha256, "grant-bound plan SHA-256")
    elif expected == "interrupted-run":
        if context.grant_action not in {"resume", "abort"}:
            raise CaptureAdmissionError("recovery journey requires a matching resume or abort grant")
        _require_text(context.grant_ref, "existing recovery grant reference")
        _require_digest(context.grant_sha256, "existing recovery grant SHA-256")
        _require_digest(context.plan_sha256, "grant-bound plan SHA-256")
        _require_text(context.interrupted_run_ref, "interrupted run reference")
        _require_digest(context.interrupted_run_sha256, "interrupted run SHA-256")
    elif expected == "missing-grant":
        if any(value is not None for value in (
                context.grant_ref, context.grant_sha256, context.plan_sha256,
                context.interrupted_run_ref, context.interrupted_run_sha256, context.grant_action)):
            raise CaptureAdmissionError("missing-grant journey must carry no grant or run context")
    elif any(value is not None for value in (
            context.grant_ref, context.grant_sha256, context.plan_sha256,
            context.interrupted_run_ref, context.interrupted_run_sha256, context.grant_action)):
        raise CaptureAdmissionError("unexpected grant or interruption context for this journey")


def _validate_costs(costs: MeasuredCosts) -> None:
    if not isinstance(costs, MeasuredCosts):
        raise CaptureAdmissionError("an observed cumulative cost snapshot is required")
    _require_text(costs.source_ref, "cost source reference")
    _require_digest(costs.source_sha256, "cost source SHA-256")
    _require_timestamp(costs.observed_at, "cost observation timestamp")
    if not isinstance(costs.values, Mapping) or set(costs.values) != set(evaluation.COST_FIELDS):
        raise CaptureAdmissionError("cost snapshot must explicitly include every registered cost field")
    for field, value in costs.values.items():
        if value is None:
            raise CaptureAdmissionError(f"measured cost {field} is unavailable; admission cannot assume zero")
        try:
            finite = math.isfinite(value)
        except (OverflowError, TypeError):
            finite = False
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not finite or value < 0:
            raise CaptureAdmissionError(f"measured cost {field} must be a finite nonnegative number")
    expected_tokens = costs.values["input_tokens"] + costs.values["output_tokens"] + costs.values["retry_tokens"]
    if costs.values["tokens"] != expected_tokens:
        raise CaptureAdmissionError("total tokens must equal input, output, and retry token totals")


def _validate_prior_costs(ledger: evaluation.EvaluationLedger, costs: MeasuredCosts) -> None:
    """Require a reconciled cumulative snapshot that covers every recorded cost."""
    additive = {"eur", "tokens", "input_tokens", "output_tokens", "retry_tokens", "wall_seconds"}
    lower_bounds: dict[str, int | float] = {field: 0 for field in additive}
    lower_bounds.update({"rss_bytes": 0, "disk_bytes": 0})
    for slot in ledger.slots:
        status = ledger.current_status(slot.slot_id)
        if status == "attempted":
            raise CaptureAdmissionError("an attempt is still open; settle or recover it before admission")
        if status == "not-started":
            continue
        event = ledger.current_event(slot.slot_id)
        prior = event.data.get("costs") if event is not None else None
        if not isinstance(prior, Mapping) or set(prior) != set(evaluation.COST_FIELDS):
            raise CaptureAdmissionError("prior attempt cost record is incomplete; cap compliance is unknown")
        for field in evaluation.COST_FIELDS:
            value = prior[field]
            if value is None:
                raise CaptureAdmissionError(f"prior attempt cost {field} is unknown; admission cannot assume zero")
            if field in additive:
                lower_bounds[field] += value
            else:
                lower_bounds[field] = max(lower_bounds[field], value)
    for field, lower_bound in lower_bounds.items():
        if costs.values[field] < lower_bound:
            raise CaptureAdmissionError(f"cumulative measured {field} is below previously recorded attempt costs")


def _validate_stop_state(state: StopState) -> None:
    if not isinstance(state, StopState):
        raise CaptureAdmissionError("externally observed stop state is required")
    if type(state.incident_open) is not bool or type(state.unrecoverable_run) is not bool:
        raise CaptureAdmissionError("stop flags must be explicit booleans")
    if type(state.consecutive_infrastructure_failures) is not int or state.consecutive_infrastructure_failures < 0:
        raise CaptureAdmissionError("infrastructure failure count must be a nonnegative integer")
    _require_text(state.source_ref, "stop-state source reference")
    _require_digest(state.source_sha256, "stop-state source SHA-256")
    _require_timestamp(state.observed_at, "stop-state observation timestamp")


def _validate_attestation(value: Any, subject_sha256: str) -> None:
    if not isinstance(value, DecisionAttestation):
        raise CaptureAdmissionError("trusted verifier returned no decision attestation")
    _require_text(value.verifier_id, "trusted verifier ID")
    _require_digest(value.decision_sha256, "decision attestation SHA-256")
    _require_timestamp(value.verified_at, "decision attestation timestamp")
    if value.subject_sha256 != subject_sha256:
        raise CaptureAdmissionError("trusted verifier attested a different admission subject")


def _authorization_dict(value: AuthorizationContext) -> dict[str, Any]:
    return {
        "mode": value.mode,
        "decisionRef": value.decision_ref,
        "decisionSha256": value.decision_sha256,
        "grantRef": value.grant_ref,
        "grantSha256": value.grant_sha256,
        "planSha256": value.plan_sha256,
        "interruptedRunRef": value.interrupted_run_ref,
        "interruptedRunSha256": value.interrupted_run_sha256,
        "grantAction": value.grant_action,
    }


def _costs_dict(value: MeasuredCosts) -> dict[str, Any]:
    return {"values": dict(value.values), "sourceRef": value.source_ref,
            "sourceSha256": value.source_sha256, "observedAt": value.observed_at}


def _stop_dict(value: StopState) -> dict[str, Any]:
    return {"incidentOpen": value.incident_open,
            "unrecoverableRun": value.unrecoverable_run,
            "consecutiveInfrastructureFailures": value.consecutive_infrastructure_failures,
            "sourceRef": value.source_ref, "sourceSha256": value.source_sha256,
            "observedAt": value.observed_at}


def _ensure_private_store(path: Path) -> None:
    account_home = _account_home()
    expected_root = account_home / ".agent-braid" / "m45-capture-admissions"
    if path != expected_root / path.name:
        raise CaptureAdmissionError("receipt store path is not canonical for the current OS account")
    current = account_home
    for part in (".agent-braid", "m45-capture-admissions", path.name):
        current = current / part
        if current.is_symlink():
            raise CaptureAdmissionError("receipt store cannot contain symbolic links")
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            pass
        try:
            info = current.stat()
        except OSError as exc:
            raise CaptureAdmissionError("private receipt store is unavailable") from exc
        if not current.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise CaptureAdmissionError("receipt store must be user-owned and mode 0700")


def _account_home() -> Path:
    """Resolve the OS account home without consulting caller-overridable HOME."""
    try:
        import pwd
        home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve(strict=True)
    except (ImportError, KeyError, OSError) as exc:
        raise CaptureAdmissionError("OS account home could not be resolved for the private receipt store") from exc
    if not home.is_dir():
        raise CaptureAdmissionError("OS account home is not a directory")
    return home


def _user_state_root() -> Path:
    return _account_home() / ".agent-braid" / "m45-capture-admissions"


def _write_exclusive(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as exc:
        raise CaptureAdmissionError("slot already has an admission receipt; do not retry") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
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


def _git_head(root: Path) -> str:
    value = _git(root, "rev-parse", "--verify", "HEAD^{commit}")
    if not _GIT_COMMIT.fullmatch(value):
        raise CaptureAdmissionError("candidate checkout has no valid full Git commit")
    return value


def _git_dirty(root: Path) -> bool:
    return bool(_git(root, "status", "--porcelain=v1", "--untracked-files=all"))


def _git(root: Path, *args: str) -> str:
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    try:
        result = subprocess.run(["git", "-C", str(root), *args], stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                env=env, timeout=8, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise CaptureAdmissionError("candidate Git identity could not be verified") from exc
    if len(result.stdout) > 1024 * 1024:
        raise CaptureAdmissionError("candidate Git observation exceeds its output limit")
    try:
        return result.stdout.decode("ascii").strip()
    except UnicodeError as exc:
        raise CaptureAdmissionError("candidate Git observation is malformed") from exc


def _hash_file(path: Path, limit: int) -> str:
    digest = hashlib.sha256()
    total = 0
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                total += len(chunk)
                if total > limit:
                    raise CaptureAdmissionError("candidate artifact exceeds the bounded hash limit")
                digest.update(chunk)
    except OSError as exc:
        raise CaptureAdmissionError("candidate artifact is unavailable") from exc
    return digest.hexdigest()


def _read_bounded(path: Path, limit: int, label: str) -> bytes:
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
    except OSError as exc:
        raise CaptureAdmissionError(f"{label} is unavailable") from exc
    if len(raw) > limit:
        raise CaptureAdmissionError(f"{label} exceeds its bounded read limit")
    return raw


def _strict_json(raw: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise CaptureAdmissionError(f"{label} contains a duplicate JSON member")
            result[key] = value
        return result

    def constant(_value: str) -> None:
        raise CaptureAdmissionError(f"{label} contains a nonfinite JSON number")

    try:
        return json.loads(raw.decode("utf-8", "strict"), object_pairs_hook=pairs,
                          parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise CaptureAdmissionError(f"{label} is not bounded UTF-8 JSON") from exc


def _canonical_json(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise CaptureAdmissionError("admission receipt is not serializable JSON") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_digest(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise CaptureAdmissionError(f"{label} must be lowercase SHA-256")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 2048:
        raise CaptureAdmissionError(f"{label} must be nonempty bounded text")
    return value


def _require_timestamp(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise CaptureAdmissionError(f"{label} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureAdmissionError(f"{label} must be a timezone-aware ISO timestamp") from exc
    if parsed.tzinfo is None:
        raise CaptureAdmissionError(f"{label} must include a timezone")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "AdmissionVerifier", "AttemptAdmission", "AuthorizationContext",
    "CaptureAdmissionError", "DecisionAttestation", "MeasuredCosts",
    "StopState", "input_hashes", "prepare_attempt", "receipt_directory_for",
]
