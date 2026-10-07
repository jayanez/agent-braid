# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded SPEC-038 real-workload trial engine.

This module deliberately has no CLI execution route. A caller must supply an
independent authority verifier for both the stable candidate/manifest review
and a later capture-specific decision before it can construct treatment
fixtures or call a treatment callback. The verifier is the trust boundary; JSON
fields alone are not authentication.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import threading
import time
import uuid
from datetime import datetime, timezone

from .utility_accounting import UtilityAccounting
from .utility_trials import _accounting_valid as _utility_accounting_valid
from . import git_replay, git_runtime, runtime_policy

PLAN_VERSION = "agent-braid-m4-real-workload-plan-v1"
RECORD_VERSION = "agent-braid-m4-real-workload-capture-v1"
VERIFY_VERSION = "agent-braid-m4-real-workload-fresh-verification-v1"
RECOVERY_VERSION = "agent-braid-m4-real-workload-recovered-treatment-v1"
DISPATCH_BUDGET_NS = 45 * 60 * 1_000_000_000
TREATMENT_DEADLINE_SECONDS = 360
SEED = ("SPEC-038-v1|seed=380038|base=f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6|"
        "a=58351f812614058e53a8ee6aef1dd458f1bb70fc|"
        "b=083f1a390988a9527a5aaeb19133401243b1d714")
SEED_SHA256 = "9a99f698a3b13f59329a5dee14fcc8af0e610cd8f1b2f3a6ad8d6dffaffbef8c"
PHASES = ("input", "replay", "preparation", "grant", "execution",
          "independent_verification", "report_serialization", "cleanup")
_OID = re.compile(r"[0-9a-f]{40}\Z")


class InvalidRealWorkload(RuntimeError):
    """Malformed, stale, or unsafe trial data; dispatch must stop."""


class InvalidatedRealWorkload(InvalidRealWorkload):
    """Candidate or manifest identity drifted; a fresh review is required."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidRealWorkload(message)


def encode(value: object) -> bytes:
    try:
        return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidRealWorkload("invalid JSON record") from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_schedule() -> dict:
    """Return the exact SPEC-038 ten-pair order and twenty treatment slots."""
    _require(_sha(SEED.encode()) == SEED_SHA256, "protocol seed digest differs")
    pairs = [
        ("W-AB-1", "warmup", "AB", "serial"),
        ("W-AB-2", "warmup", "AB", "parallel"),
        ("W-BA-1", "warmup", "BA", "serial"),
        ("W-BA-2", "warmup", "BA", "parallel"),
    ]
    measured = [(f"M-{order}-{i}", "measured", order, None)
                for order in ("AB", "BA") for i in range(1, 4)]
    measured.sort(key=lambda p: (hashlib.sha256((SEED + "|" + p[0]).encode()).hexdigest(), p[0]))
    for pair_id, kind, order, _ in measured:
        digest = hashlib.sha256((SEED + "|" + pair_id).encode()).digest()
        first = "serial" if digest[0] % 2 == 0 else "parallel"
        pairs.append((pair_id, kind, order, first))
    slots = []
    for dispatch, (pair_id, kind, order, first) in enumerate(pairs, start=1):
        for treatment_order, mode in enumerate((first, "parallel" if first == "serial" else "serial")):
            slots.append({"slotId": f"{pair_id}-{mode}", "pairId": pair_id,
                          "pairKind": kind, "operationOrder": order,
                          "globalPairDispatch": dispatch, "treatmentOrder": treatment_order,
                          "mode": mode})
    return {"version": PLAN_VERSION, "seed": SEED, "seedSha256": SEED_SHA256,
            "dispatchBudgetNs": DISPATCH_BUDGET_NS,
            "treatmentDeadlineSeconds": TREATMENT_DEADLINE_SECONDS,
            "pairs": [{"pairId": p[0], "pairKind": p[1], "operationOrder": p[2],
                       "globalPairDispatch": i + 1,
                       "treatmentOrder": [p[3], "parallel" if p[3] == "serial" else "serial"]}
                      for i, p in enumerate(pairs)],
            "slots": slots}


def _canonical_schedule(value: object) -> list[dict]:
    expected = build_schedule()
    _require(type(value) is list and len(value) == 20, "complete 20-slot schedule required")
    for got, want in zip(value, expected["slots"]):
        for key, expected_value in want.items():
            _require(got.get(key) == expected_value, "manifest treatment schedule differs from protocol")
        _require(set(got) >= set(want), "manifest slot omits protocol fields")
    return expected["slots"]


def _validate_authority_record(raw: bytes, *, record_version: str, decision: str,
                               candidate_commit: str, manifest_sha256: str,
                               verifier, kind: str) -> dict:
    _require(type(raw) is bytes and len(raw) <= 1024 * 1024, "invalid authority record bytes")
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidRealWorkload("invalid authority record JSON") from exc
    _require(type(value) is dict and value.get("recordVersion") == record_version
             and value.get("decision") == decision
             and value.get("reviewedCandidateCommit") == candidate_commit
             and value.get("reviewedManifestSha256") == manifest_sha256,
             f"{kind} does not bind exact candidate and manifest")
    _require(callable(verifier) and verifier(kind, raw, candidate_commit, manifest_sha256) is True,
             f"authenticated {kind} approval required")
    return value


def _decision_time(record: dict, field: str) -> float:
    value = record.get(field)
    _require(type(value) is str and bool(value), f"{field} timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidRealWorkload(f"invalid {field} timestamp") from exc
    _require(parsed.tzinfo is not None, f"{field} timestamp must include a timezone")
    return parsed.timestamp()


def validate_review_and_capture_authority(*, manifest: dict, manifest_raw: bytes,
                                          review_raw: bytes, capture_raw: bytes,
                                          authority_verifier) -> dict:
    """Validate both distinct exact decisions before any fixture/callback work.

    `authority_verifier` must authenticate the reviewer/owner provenance from a
    trusted channel. This module does not treat self-asserted JSON as a signature.
    """
    manifest_sha = _sha(manifest_raw)
    candidate = manifest.get("candidateCommit")
    _require(type(candidate) is str and bool(_OID.fullmatch(candidate)), "invalid candidate commit")
    _require(manifest.get("manifestSha256") == manifest_sha,
             "prepared manifest raw-byte digest differs")
    _require(manifest.get("captureAuthorization") is False,
             "preparation manifest must not self-assert capture authorization")
    _validate_authority_record(review_raw, record_version="m4-real-workload-harness-review-v1",
                               decision="approved", candidate_commit=candidate,
                               manifest_sha256=manifest_sha, verifier=authority_verifier,
                               kind="stable-harness-manifest-review")
    capture = _validate_authority_record(
        capture_raw, record_version="m4-real-workload-capture-authorization-v1",
        decision="approved", candidate_commit=candidate, manifest_sha256=manifest_sha,
        verifier=authority_verifier, kind="capture-authorization")
    _require(capture.get("registeredCaptureAuthorized") is True,
             "capture authorization does not permit registered capture")
    _require(capture.get("reviewedReviewSha256") == _sha(review_raw),
             "capture authorization does not bind the exact stable review")
    review_time = _decision_time(json.loads(review_raw), "reviewedAt")
    capture_time = _decision_time(capture, "authorizedAt")
    _require(review_time <= capture_time < time.time(),
             "stable review and capture authorization must predate this action in order")
    _require(review_raw != capture_raw, "review and capture authority must be distinct records")
    return {"candidateCommit": candidate, "manifestSha256": manifest_sha,
            "stableReviewSha256": _sha(review_raw), "captureAuthorizationSha256": _sha(capture_raw),
            "captureAuthorized": True}


def _source_fingerprint(repository: Path) -> dict:
    _require(repository.is_dir() and not repository.is_symlink(), "owned source repository missing or unsafe")
    result = {}
    for path in sorted(repository.rglob("*")):
        _require(not path.is_symlink(), "source repository contains symlink")
        if path.is_file():
            result[path.relative_to(repository).as_posix()] = _sha(path.read_bytes())
    return result


def _failure_status(exc: Exception, cancel_event=None) -> str:
    if isinstance(exc, InvalidatedRealWorkload):
        return "invalidated"
    if isinstance(exc, InvalidRealWorkload):
        return "no-go"
    if type(exc).__name__ == "InvalidRealWorkload":
        return "no-go"
    if type(exc).__name__ in {"InvalidGitRuntime", "InvalidGitReplay", "InvalidRuntimePolicy",
                              "InvalidRuntimeSchedule"}:
        return "inconclusive" if cancel_event is not None and cancel_event.is_set() else "no-go"
    return "inconclusive"


def run_treatment(slot: dict, *, input_factory, source_repository: Path,
                  source_fingerprint: dict, controlled_child_scope: bool = True,
                  source_integrity_check=None,
                  accounting_factory=UtilityAccounting,
                  cancel_event: threading.Event | None = None,
                  identity_check=None) -> dict:
    """Run one exact coordinator treatment, retaining run/grant data for fresh verification."""
    mode = slot["mode"]
    _require(mode in {"serial", "parallel"}, "unsupported coordinator mode")
    run_path, grant_path = Path(slot["runPath"]), Path(slot["grantPath"])
    _require(run_path.is_absolute() and grant_path.is_absolute() and run_path != grant_path
             and run_path.parent == grant_path.parent, "run and grant destinations must be private siblings")
    _require(not run_path.exists() and not grant_path.exists()
             and not run_path.is_symlink() and not grant_path.is_symlink(),
             "treatment destinations must be fresh")
    accounting = accounting_factory(child_attribution_valid=controlled_child_scope)
    operation = {"slotId": slot["slotId"], "mode": mode, "status": "incomplete",
                 "resultTree": None, "immutableSourceUnchanged": None}
    before = None
    plan = grant = None
    runtime_request = replay_request = expected_tree = None
    timer = None
    started = time.monotonic()
    accounting.start()
    if cancel_event is None:
        cancel_event = threading.Event()
    if source_integrity_check is None:
        source_integrity_check = _source_fingerprint
    timer = threading.Timer(TREATMENT_DEADLINE_SECONDS, cancel_event.set)
    timer.daemon = True
    timer.start()
    try:
        with accounting.activate_git_budget_registry():
            try:
                with accounting.phase("input"):
                    if identity_check is not None and identity_check() is not True:
                        raise InvalidatedRealWorkload("candidate or harness identity drifted")
                    inputs = input_factory()
                    _require(type(inputs) is dict and set(inputs) == {
                        "runtimeRequest", "replayRequest", "expectedFinalTree"},
                        "slot input production returned unexpected fields")
                    runtime_request = inputs["runtimeRequest"]
                    replay_request = inputs["replayRequest"]
                    expected_tree = inputs["expectedFinalTree"]
                    before = source_integrity_check(source_repository)
                    if before != source_fingerprint:
                        raise InvalidRealWorkload("prepared source integrity differs")
                    if Path(runtime_request.get("repository", "")).resolve() != source_repository.resolve():
                        raise InvalidatedRealWorkload("runtime request source path differs")
                    if runtime_request.get("expectedFinalTree") != expected_tree:
                        raise InvalidatedRealWorkload("runtime request expected tree differs")
                with accounting.phase("replay"):
                    evidence, advisory = git_replay.produce(replay_request)
                with accounting.phase("preparation"):
                    plan = runtime_policy.prepare_policy_run(
                        runtime_request, run_path, replay_evidence=evidence,
                        advisory_plan=advisory, mode=mode, cancel_event=cancel_event)
                    operation["plan"] = deepcopy(plan)
                with accounting.phase("grant"):
                    grant = runtime_policy.issue_operator_grant(
                        plan, grant_path, acknowledge=plan["planDigest"], cancel_event=cancel_event)
                    operation["grantId"] = grant["grantId"]
                with accounting.phase("execution"):
                    report = runtime_policy.execute_policy_run(
                        plan, grant_path, grant["grantId"], cancel_event=cancel_event)
                with accounting.phase("independent_verification"):
                    verification = runtime_policy.inspect_policy_run(plan, grant_path,
                                                                     cancel_event=cancel_event)
                    _require(verification.get("runtime", {}).get("status") == "verified-completed"
                             and verification.get("runtime", {}).get("resultTree") == expected_tree,
                             "read-only consumer verification failed or tree differs")
                    _require(source_integrity_check(source_repository) == before,
                             "immutable source changed during treatment")
                    operation.update(status="completed", resultTree=expected_tree,
                                     immutableSourceUnchanged=True,
                                     executionReport=deepcopy(report),
                                     independentVerification=deepcopy(verification))
            except Exception as exc:
                failure_status = _failure_status(exc, cancel_event)
                if failure_status == "inconclusive" and cancel_event.is_set():
                    failure_status = "interrupted"
                    operation["interruption"] = {"kind": "cancel-or-observation-deadline",
                                                  "message": str(exc),
                                                  "grantId": operation.get("grantId"),
                                                  "planDigest": (operation.get("plan", {}).get("planDigest")
                                                                 if type(operation.get("plan")) is dict else None)}
                operation.update(status=failure_status,
                                 error={"type": type(exc).__name__, "message": str(exc)})
                if before is not None:
                    try:
                        if source_integrity_check(source_repository) != before:
                            operation["sourceIntegrityAtFailure"] = "changed"
                            operation.update(status="no-go", safetyError="immutable-source-changed-on-failure")
                        else:
                            operation["sourceIntegrityAtFailure"] = "unchanged"
                    except Exception as integrity_exc:
                        operation["sourceIntegrityAtFailure"] = "unknown"
                        operation.update(status="no-go", safetyError=str(integrity_exc))
            finally:
                try:
                    with accounting.phase("report_serialization"):
                        operation["accountingPreview"] = accounting.preview()
                        operation["operationalEncoded"] = encode(operation).decode()
                finally:
                    # Existing runtime/replay helpers remove temporary scratch in
                    # the phase that creates it. Result and grant artifacts remain
                    # for the required fresh-process inspection.
                    with accounting.phase("cleanup"):
                        operation["cleanupObservation"] = {
                            "additionalTreatmentOwnedArtifactsRemoved": 0,
                            "reason": "no additional per-treatment artifacts require cleanup before fresh inspection; runtime-created temporary scopes are cleaned in their generating phase",
                            "scope": "explicit zero additional cleanup work"}
                    if identity_check is not None and identity_check() is not True:
                        operation.update(status="invalidated", closingIdentityCheck="candidate-or-harness-drift")
    finally:
        timer.cancel()
    final_status = operation["status"]
    if time.monotonic() - started > TREATMENT_DEADLINE_SECONDS and final_status == "completed":
        final_status = "interrupted"
        operation["deadlineDisposition"] = "observation-deadline-exceeded"
        operation["status"] = "interrupted"
    observation = accounting.finish(outcome="success" if final_status == "completed" else "failure")
    if final_status == "completed" and not observation["complete"]:
        final_status = "inconclusive"
    result, observer = accounting.seal(lambda closed: {
        "recordVersion": "agent-braid-m4-real-workload-treatment-v1",
        "operational": deepcopy(operation), "status": final_status,
        "accounting": closed,
        "boundary": "outer timing includes input, replay, preparation, grant, execution, consumer verification, report serialization, cleanup phase and residual; no additional per-treatment cleanup was required before fresh inspection; result/grant artifacts are retained"})
    result["observerFinalization"] = observer
    return result


def _sample_disposition(sample: object, slot: dict, expected_tree: str, manifest: dict | None = None) -> tuple[str, str | None]:
    if type(sample) is not dict:
        return "invalid", "missing-treatment-record"
    status = sample.get("status")
    if status in {"no-go", "invalidated"}:
        return status, "unsafe-or-identity-drift"
    if status in {"interrupted", "failed", "refused"}:
        return status, "treatment-outcome-retained-stop-dispatch"
    if status == "recovered":
        try:
            _validate_recovered_sample(sample, slot, expected_tree, manifest)
        except Exception as exc:
            return "invalid", "recovery-evidence-invalid: " + str(exc)
        return "recovered", "same-slot recovery observed; retained and excluded from valid ratios"
    if status != "completed":
        return "invalid", "treatment-incomplete"
    operation = sample.get("operational")
    if type(operation) is not dict or operation.get("slotId") != slot["slotId"] or operation.get("mode") != slot["mode"]:
        return "invalidated", "treatment-identity-differs"
    if (operation.get("immutableSourceUnchanged") is not True
            or operation.get("resultTree") != expected_tree
            or type(operation.get("grantId")) is not str):
        return "no-go", "source-grant-or-tree-proof-failed"
    try:
        uuid.UUID(operation["grantId"])
    except (ValueError, AttributeError):
        return "no-go", "grant-identity-invalid"
    if not _valid_accounting(sample.get("accounting")):
        return "invalid", "incomplete-accounting"
    return "valid", None


def _validate_recovered_sample(sample: dict, slot: dict, expected_tree: str,
                               manifest: dict | None) -> dict:
    """Validate a caller-ingested recovery receipt without issuing or consuming grants."""
    _require(type(manifest) is dict, "recovery requires the exact prepared manifest")
    _require(set(sample) == {"recordVersion", "status", "originalTreatment", "recovery"}
             and sample.get("recordVersion") == RECOVERY_VERSION and sample.get("status") == "recovered",
             "invalid recovered treatment envelope")
    original, recovery = sample["originalTreatment"], sample["recovery"]
    _require(type(original) is dict and original.get("status") == "interrupted"
             and _valid_retained_accounting(original.get("accounting")),
             "recovery must retain an accounted interrupted original treatment")
    original_op = original.get("operational")
    _require(type(original_op) is dict and original_op.get("status") == "interrupted"
             and original_op.get("slotId") == slot["slotId"] and original_op.get("mode") == slot["mode"]
             and original_op.get("sourceIntegrityAtFailure") == "unchanged",
             "interrupted original treatment identity differs")
    _require(type(recovery) is dict and set(recovery) == {
        "plan", "grantStore", "grantId", "report", "finalInspection", "accounting"},
        "invalid recovery receipt fields")
    _require(_valid_accounting(recovery.get("accounting")), "recovery accounting is incomplete")
    plan = recovery["plan"]
    _require(type(plan) is dict and recovery["grantStore"] == slot["grantPath"],
             "recovery plan or private grant store differs from the frozen slot")
    from . import m4_real_workload as source
    inputs = source.runtime_inputs_for_slot(manifest, slot)
    expected_request = inputs["runtimeRequest"]
    verified = runtime_policy.verify_policy_plan(plan)
    runtime_manifest = verified["runtimeManifest"]
    original_plan = original_op.get("plan")
    original_verified = runtime_policy.verify_policy_plan(original_plan)
    expected_revision = (runtime_policy.POLICY if slot["mode"] == "serial"
                         else runtime_policy.PARALLEL_POLICY)
    _require(runtime_manifest["request"] == expected_request
             and runtime_manifest["runDirectory"] == slot["runPath"]
             and original_verified["planDigest"] == verified["planDigest"]
             and original_verified["runtimeManifest"]["manifestDigest"] == runtime_manifest["manifestDigest"]
             and verified["policy"]["revision"] == expected_revision
             and inputs["expectedFinalTree"] == expected_tree,
             "recovery plan differs from exact slot inputs, destination, or expected tree")
    plan_digest = verified["planDigest"]
    manifest_digest = runtime_manifest["manifestDigest"]

    def bound_grant(identifier: object, action: str) -> dict:
        _require(type(identifier) is str, "missing recovery grant identity")
        uuid.UUID(identifier)
        root = runtime_policy._store(verified, recovery["grantStore"], create=False)
        grant = runtime_policy._read_grant(root, identifier)
        _require(grant["grantId"] == identifier and grant["action"] == action
                 and grant["state"] == "consumed" and grant["planDigest"] == plan_digest
                 and grant["manifestDigest"] == manifest_digest
                 and grant["runDirectory"] == slot["runPath"],
                 "grant bytes are not a consumed same-plan/same-destination " + action + " grant")
        return grant

    original_grant_id = original_op.get("grantId")
    original_grant = bound_grant(original_grant_id, "execute")
    recovery_grant = bound_grant(recovery["grantId"], "resume")
    _require(recovery_grant["grantId"] != original_grant["grantId"],
             "recovery must use a fresh purpose-bound resume grant")
    report = recovery["report"]
    _require(type(report) is dict and report.get("dispatch") == "performed"
             and report.get("grantId") == recovery_grant["grantId"],
             "recovery report is not bound to the consumed resume grant")
    runtime = report.get("runtime")
    _require(type(runtime) is dict and runtime.get("status") == "completed"
             and runtime.get("manifestDigest") == manifest_digest
             and runtime.get("runDirectory") == slot["runPath"]
             and runtime.get("resultTree") == expected_tree,
             "recovery report does not complete the same frozen destination/tree")
    inspection = recovery["finalInspection"]
    inspected_runtime = inspection.get("runtime") if type(inspection) is dict else None
    _require(type(inspection) is dict and inspection.get("dispatch") == "not-dispatched"
             and inspection.get("executionAuthorization") is False
             and type(inspected_runtime) is dict
             and inspected_runtime.get("status") == "verified-completed"
             and inspected_runtime.get("manifestDigest") == manifest_digest
             and inspected_runtime.get("runDirectory") == slot["runPath"]
             and inspected_runtime.get("resultTree") == expected_tree,
             "final read-only inspection does not verify the recovered same-slot result")
    return {"planDigest": plan_digest, "manifestDigest": manifest_digest,
            "originalGrant": original_grant, "resumeGrant": recovery_grant,
            "resultTree": expected_tree}


def _valid_accounting(value: object) -> bool:
    return _utility_accounting_valid(value)


def _valid_retained_accounting(value: object) -> bool:
    """Validate failure-outcome accounting without relabeling it successful."""
    if (type(value) is not dict or value.get("complete") is not False
            or value.get("outcome") != "failure" or type(value.get("errors")) is not list
            or not value["errors"] or any(type(item) is not str for item in value["errors"])):
        return False
    outer, phases = value.get("outer"), value.get("phases")
    if (type(outer) is not dict or type(phases) is not list or not phases
            or type(outer.get("startWallNs")) is not int or type(outer.get("endWallNs")) is not int
            or type(outer.get("wallNs")) is not int or outer["wallNs"] <= 0
            or outer["endWallNs"] - outer["startWallNs"] != outer["wallNs"]):
        return False
    allowed_order = list(PHASES)
    phase_names = [phase.get("name") if type(phase) is dict else None for phase in phases]
    if phase_names != [name for name in allowed_order if name in phase_names]:
        return False
    total = 0
    previous_end = outer["startWallNs"]
    for phase in phases:
        if (type(phase.get("startWallNs")) is not int or type(phase.get("endWallNs")) is not int
                or type(phase.get("wallNs")) is not int
                or phase["endWallNs"] - phase["startWallNs"] != phase["wallNs"]
                or phase["startWallNs"] < previous_end or phase["endWallNs"] > outer["endWallNs"]):
            return False
        previous_end = phase["endWallNs"]
        total += phase["wallNs"]
    residual = value.get("residualWallNs")
    return (type(residual) is int and residual >= 0
            and residual == outer["wallNs"] - total)


def _current_before_dispatch(manifest_raw: bytes, manifest: dict, expected_candidate: str,
                             identity_check) -> None:
    _require(callable(identity_check) and identity_check() is True,
             "current exact candidate and code inventory check required")
    _require(manifest.get("candidateCommit") == expected_candidate
             and type(manifest_raw) is bytes and bool(manifest_raw)
             and manifest.get("manifestSha256") == _sha(manifest_raw),
             "candidate or exact manifest bytes changed after authorization")


def run_trials(*, manifest_raw: bytes, manifest: dict, manifest_validator,
               review_raw: bytes,
               capture_authorization_raw: bytes, authority_verifier,
               identity_check, callback_factory, monotonic_ns=time.monotonic_ns) -> dict:
    """Execute the frozen 20-slot schedule after both authenticated gates.

    `callback_factory(manifest)` returns `(treatment_callback,
    preparation_receipt)`. It is called only after review, capture, and exact
    candidate/manifest checks pass. The capture runner does not manufacture
    source fixtures; each callback dispatches the frozen runtime inputs directly.
    """
    _require(callable(manifest_validator), "exact source manifest validator required")
    validated_manifest = manifest_validator(manifest_raw)
    _require(type(validated_manifest) is dict and validated_manifest == manifest,
             "manifest object is not the canonical validation of its bytes")
    authority = validate_review_and_capture_authority(
        manifest=manifest, manifest_raw=manifest_raw, review_raw=review_raw,
        capture_raw=capture_authorization_raw, authority_verifier=authority_verifier)
    schedule = build_schedule()
    slots = _canonical_schedule(manifest.get("slots"))
    _require(callable(callback_factory), "fixture/callback factory required")
    stop, preparation, callback = None, None, None
    try:
        _current_before_dispatch(manifest_raw, manifest, authority["candidateCommit"], identity_check)
    except Exception as exc:
        stop = "identity-drift"
        preparation = {"status": "not-created", "reason": str(exc)}
    if stop is None:
        # No fixture copies, grants, or runtime results are produced here. This
        # callback factory follows both authenticated gates and exact identity.
        try:
            callback, preparation = callback_factory(deepcopy(manifest))
            if not callable(callback):
                raise InvalidRealWorkload("treatment callback required")
        except Exception as exc:
            stop = "preparation-failed"
            preparation = {"status": "failed", "error": {"type": type(exc).__name__,
                                                              "message": str(exc)}}
    start = monotonic_ns()
    _require(type(start) is int and start >= 0, "invalid monotonic dispatch clock")
    previous = start
    output = {"recordVersion": RECORD_VERSION, "candidateCommit": authority["candidateCommit"],
              "manifestSha256": authority["manifestSha256"], "authority": authority,
              "preparation": deepcopy(preparation), "status": "complete", "slots": [],
              "dispatchBudgetNs": DISPATCH_BUDGET_NS,
              "externalCosts": {
                  "sourceAndRightsAcquisition": {"wallNs": None, "reason": "pre-existing source-rights and protocol approval time was not instrumented by this capture runner"},
                  "independentReview": {"wallNs": None, "reason": "reviewer elapsed time is not available to the local runner"},
                  "environmentSetup": {"wallNs": None, "reason": "environment setup predates the dispatch interval and is not instrumented here"},
                  "operatorEffort": {"wallNs": None, "reason": "operator effort is not observable by the local runner"},
                  "staticManifestPreparation": {"wallNs": None, "reason": "preparation receipt must be reported separately; no timing is bound into this capture record"}},
              "claimBoundary": "Finite descriptive actual-workload trial only; no general utility, safety, scientific, or M4 acceptance claim."}
    seen_grants, seen_plans = set(), set()
    slot_by_id = {slot.get("slotId"): slot for slot in manifest["slots"]}
    for frozen in slots:
        descriptor = slot_by_id.get(frozen["slotId"])
        _require(type(descriptor) is dict, "manifest slot identity missing")
        for key, value in frozen.items():
            _require(descriptor.get(key) == value, "manifest slot differs from exact schedule")
        row = {**deepcopy(descriptor), "status": "unexecuted", "reason": stop or "not-dispatched", "sample": None}
        if stop is None:
            try:
                _current_before_dispatch(manifest_raw, manifest, authority["candidateCommit"], identity_check)
            except Exception:
                stop = "identity-drift"
            if stop is None:
                now = monotonic_ns()
                _require(type(now) is int and now >= previous, "dispatch clock reversed")
                previous = now
                if now - start >= DISPATCH_BUDGET_NS:
                    stop = "dispatch-budget-exhausted"
        if stop is None:
            try:
                sample = callback(deepcopy(descriptor))
                row["sample"] = deepcopy(sample)
                expected_tree = descriptor.get("expectedFinalTree")
                if expected_tree is None:
                    expected_tree = manifest.get("expectedFinalTrees", {}).get(descriptor["operationOrder"])
                disposition, reason = _sample_disposition(sample, descriptor, expected_tree, manifest)
                if disposition == "valid":
                    op = sample["operational"]
                    grant, digest = op["grantId"], op.get("plan", {}).get("planDigest")
                    if grant in seen_grants or type(digest) is not str or digest in seen_plans:
                        disposition, reason = "no-go", "grant-or-plan-reused"
                    else:
                        seen_grants.add(grant)
                        seen_plans.add(digest)
                row.update(status=disposition, reason=reason)
            except Exception as exc:
                row.update(status="invalid", reason="callback-error",
                            error={"type": type(exc).__name__, "message": str(exc)})
            if row["status"] in {"no-go", "invalidated", "invalid", "interrupted", "recovered",
                                  "failed", "refused"}:
                stop = ("unsafe-treatment" if row["status"] == "no-go" else
                        "identity-drift" if row["status"] == "invalidated" else
                        "treatment-interrupted" if row["status"] == "interrupted" else
                        "recovery-observed" if row["status"] == "recovered" else
                        "treatment-failed" if row["status"] == "failed" else
                        "treatment-refused" if row["status"] == "refused" else
                        "uncertain-treatment")
            try:
                _current_before_dispatch(manifest_raw, manifest, authority["candidateCommit"], identity_check)
            except Exception:
                stop = "identity-drift"
            now = monotonic_ns()
            _require(type(now) is int and now >= previous, "dispatch clock reversed")
            previous = now
            if stop is None and now - start >= DISPATCH_BUDGET_NS:
                stop = "dispatch-budget-exhausted"
        elif row["status"] == "unexecuted":
            row["reason"] = stop
        output["slots"].append(row)
    output["stopReason"] = stop
    by_pair = {}
    for row in output["slots"]:
        by_pair.setdefault(row["pairId"], []).append(row)
    pairs = []
    ratios = []
    for pair in schedule["pairs"]:
        pair_rows = sorted(by_pair[pair["pairId"]], key=lambda r: r["treatmentOrder"])
        statuses = [row["status"] for row in pair_rows]
        valid = len(pair_rows) == 2 and all(status == "valid" for status in statuses)
        ratio = None
        if valid and pair["pairKind"] == "measured":
            walls = {row["mode"]: row["sample"]["accounting"]["outer"]["wallNs"] for row in pair_rows}
            ratio = walls["serial"] / walls["parallel"]
            _require(math.isfinite(ratio) and ratio > 0, "invalid paired wall ratio")
            ratios.append(ratio)
        pairs.append({**deepcopy(pair), "slotIds": [r["slotId"] for r in pair_rows],
                      "statuses": statuses, "valid": valid, "serialOverParallelWallRatio": ratio})
    measured = [p for p in pairs if p["pairKind"] == "measured"]
    complete = len(measured) == 6 and all(p["valid"] for p in measured)
    output["pairs"] = pairs
    order_summaries = {}
    for order in ("AB", "BA"):
        order_pairs = [p for p in measured if p["operationOrder"] == order]
        order_ratios = [p["serialOverParallelWallRatio"] for p in order_pairs]
        order_summaries[order] = {
            "intendedMeasuredPairs": 3,
            "validMeasuredPairs": sum(p["valid"] for p in order_pairs),
            "ratios": order_ratios,
            "medianRatio": statistics.median(order_ratios) if len(order_ratios) == 3 and all(
                ratio is not None for ratio in order_ratios) else None,
        }
    exposure_groups = {}
    for order in ("AB", "BA"):
        first_id = f"W-{order}-1"
        first = next(p for p in pairs if p["pairId"] == first_id)
        later = [p for p in pairs if p["operationOrder"] == order and p["pairId"] != first_id]
        exposure_groups[order] = {
            "firstExposurePair": {"pairId": first_id, "valid": first["valid"],
                                  "statuses": first["statuses"]},
            "laterExposurePairs": [{"pairId": p["pairId"], "pairKind": p["pairKind"],
                                     "valid": p["valid"], "statuses": p["statuses"]}
                                    for p in later],
        }
    output["perOrderMeasuredSummary"] = order_summaries
    output["firstAndLaterExposureSummary"] = exposure_groups
    output["denominator"] = {"intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
                             "validMeasuredPairs": sum(p["valid"] for p in measured),
                             "invalidPairs": sum(any(s in {"invalid", "no-go", "invalidated", "failed",
                                                         "refused", "interrupted", "recovered"}
                                                     for s in p["statuses"]) for p in pairs),
                             "failedPairs": sum("failed" in p["statuses"] for p in pairs),
                             "refusedPairs": sum("refused" in p["statuses"] for p in pairs),
                             "interruptedPairs": sum("interrupted" in p["statuses"] for p in pairs),
                             "recoveredPairs": sum("recovered" in p["statuses"] for p in pairs),
                             "unexecutedPairs": sum(any(s == "unexecuted" for s in p["statuses"]) for p in pairs),
                             "attemptedTreatments": sum(r["status"] != "unexecuted" for r in output["slots"])}
    disposition_names = ("valid", "invalid", "failed", "refused", "interrupted", "recovered",
                         "no-go", "invalidated", "unexecuted")
    output["treatmentDispositionCounts"] = {
        "intended": len(output["slots"]),
        "attempted": sum(row["status"] != "unexecuted" for row in output["slots"]),
        **{name: sum(row["status"] == name for row in output["slots"])
           for name in disposition_names},
    }
    output["pairDenominatorInterpretation"] = (
        "invalidPairs counts any pair with an explicit invalid, failed, refused, interrupted, recovered, no-go, or invalidated slot; "
        "unexecutedPairs counts any pair with an unexecuted slot. These counts can overlap "
        "when one treatment fails and its pair partner is not dispatched.")
    output["measuredRatios"] = [p["serialOverParallelWallRatio"] for p in measured]
    output["medianMeasuredRatio"] = statistics.median(ratios) if complete else None
    output["status"] = ("invalidated" if stop == "identity-drift" else "no-go" if stop == "unsafe-treatment"
                        else "incomplete" if stop or not complete else "complete")
    output["pairInterpretation"] = "Descriptive repetitions of one finite source frame; no population or causal inference."
    return output


def _valid_oid(value: object) -> bool:
    return type(value) is str and bool(_OID.fullmatch(value))
