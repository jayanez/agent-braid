# SPDX-License-Identifier: AGPL-3.0-only
"""Additive source-based registration; declarations never become provider facts.

The legacy projection below checks unchanged registration declarations only.
It never produces a v3 observation, approval or paid-control assertion. Runtime
consumers must use the distinct SourceRouteBinding and authenticated receipts.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from . import tooling_codex_sources as codex
from . import tooling_claude_sources as claude
from . import tooling_subscription as subscription

REGISTRATION_SCHEMA = "agent-braid-m45-registration-v6"
SOURCE_POLICY_SCHEMA = "agent-braid-m45-source-subscription-policy-v1"
BINDING_SCHEMA = "agent-braid-m45-source-route-binding-v1"
FIELDS = frozenset({"sourceContractTemplates", "humanAuditPolicy", "humanAuditPolicySha256", "instrumentPins", "claudeLaunchStore"})
INSTRUMENTS = frozenset({"admission", "outcome", "costs", "technicalSummary"})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


@dataclass(frozen=True)
class SourceRouteBinding:
    """Frozen source contract and structural identity; no v3 facts are inferred."""
    binding: subscription.OperationalProcessRouteBinding
    contract_sha256: str
    _contract_bytes: bytes
    _launch_store_bytes: bytes | None = None

    @property
    def contract(self) -> dict[str, Any]:
        return json.loads(self._contract_bytes)

    @property
    def host(self):
        return self.binding.host

    @property
    def slot_id(self):
        return self.binding.slot_id

    @property
    def registration_sha256(self):
        return self.binding.registration_sha256

    @property
    def launch_store(self):
        return None if self._launch_store_bytes is None else json.loads(self._launch_store_bytes)

    def as_dict(self):
        return {"schema": BINDING_SCHEMA, "binding": self.binding.as_dict(),
                "contractSha256": self.contract_sha256, "contract": self.contract,
                "launchStore": self.launch_store}

    def validate(self):
        module = codex if self.host == "codex" else claude
        if module.source_contract_sha256(self.contract) != self.contract_sha256:
            raise subscription.SubscriptionError("source route contract differs from its frozen digest")
        if subscription.operational_binding_from_dict(self.contract["binding"]) != self.binding:
            raise subscription.SubscriptionError("source route contract and process binding disagree")
        if self.host == "claude-code":
            store = self.launch_store
            if not isinstance(store, dict) or set(store) != {"canonicalConfigDirSha256", "keychainSuffix"}:
                raise subscription.SubscriptionError("Claude source route requires its frozen launch store")
            subscription._hash(store["canonicalConfigDirSha256"], "canonical config directory")
            if store["keychainSuffix"] != self.contract["isolatedStore"]["keychainSuffix"]:
                raise subscription.SubscriptionError("Claude launch store and source suffix disagree")
        elif self.launch_store is not None:
            raise subscription.SubscriptionError("Codex cannot carry a Claude launch store")


def validate_registration(data, *, expected_candidate_sha256, expected_input_hashes):
    """Validate v6 without admitting any real account, source or native launch."""
    from . import tooling_evaluation as evaluation
    original = evaluation._json_copy(data, "v6 registration")
    if original.get("schemaVersion") != REGISTRATION_SCHEMA:
        raise evaluation.EvaluationError("source registration requires v6")
    if not FIELDS.issubset(original):
        raise evaluation.EvaluationError("v6 source contracts, audit policy and instrument pins are required")
    policy = original.get("billingPolicy")
    if not isinstance(policy, dict) or policy.get("schema") != SOURCE_POLICY_SCHEMA:
        raise evaluation.EvaluationError("v6 requires the separately versioned source subscription policy")
    # Reuse the existing fixed 108-slot, rights, owner/provider decisions, caps,
    # estimate, identities and human-deferral validators. Only DECLARATIONS
    # receive a legacy schema tag; no provider observation is created here.
    projection = copy.deepcopy(original)
    projection["schemaVersion"] = evaluation.REGISTRATION_SCHEMA_V5
    projection["billingPolicy"]["schema"] = subscription.OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA
    for field in FIELDS:
        projection.pop(field)
    evaluation.validate_registration(projection,
        expected_candidate_sha256=expected_candidate_sha256,
        expected_input_hashes=expected_input_hashes)
    try:
        from . import tooling_human_audit as audit
        audit.validate_policy(original["humanAuditPolicy"], expected_sha256=original["humanAuditPolicySha256"])
        templates = original["sourceContractTemplates"]
        if not isinstance(templates, dict) or set(templates) != set(evaluation.HOSTS):
            raise ValueError("source templates must cover exactly both hosts")
        instruments = original["instrumentPins"]
        if not isinstance(instruments, dict) or set(instruments) != INSTRUMENTS:
            raise ValueError("all four independent instrument pins are required")
        for pin in instruments.values():
            subscription._validate_source_pair(pin, "v6 instrument")
        result = evaluation.ValidatedRegistration(original, _digest(original))
        slots = evaluation.generate_slots(result)
        for host in evaluation.HOSTS:
            slot = next(row for row in slots if row.host == host)
            binding_from_registration(result, slot.slot_id, host).validate()
        return result
    except (ValueError, TypeError, KeyError, subscription.SubscriptionError) as exc:
        raise evaluation.EvaluationError(f"invalid v6 source or audit contract: {exc}") from exc


def binding_from_registration(registration, slot_id, host):
    """Instantiate a per-slot source contract after the registration hash exists."""
    from . import tooling_evaluation as evaluation
    evaluation._require_validated(registration)
    if registration.data.get("schemaVersion") != REGISTRATION_SCHEMA:
        raise evaluation.EvaluationError("source-route binding requires registration v6")
    if registration.sha256 != _digest(registration.data):
        raise evaluation.EvaluationError("frozen source registration was mutated")
    policy = registration.data["billingPolicy"]
    if policy.get("schema") != SOURCE_POLICY_SCHEMA:
        raise evaluation.EvaluationError("source policy schema drift")
    contract = policy["processContracts"].get(slot_id)
    if host not in evaluation.HOSTS or not isinstance(contract, Mapping) or contract.get("host") != host:
        raise evaluation.EvaluationError("source slot does not belong to the requested host")
    row = next(item for item in policy["hosts"] if item["host"] == host)
    observer = policy["observer"]
    core = subscription.OperationalProcessRouteBinding(
        host, registration.sha256, slot_id, _digest(policy), row["accountSha256"],
        row["accountNamespaceSha256"], contract["hostBuildSha256"],
        contract["candidateArtifactSha256"], contract["executableSha256"],
        contract["configSha256"], contract["argvSha256"], contract["modelIdentitySha256"],
        observer["sourceRef"], observer["sourceSha256"], observer["verifierRef"],
        observer["verifierSha256"], policy["maxAgeSeconds"])
    template = copy.deepcopy(registration.data["sourceContractTemplates"][host])
    if "binding" in template:
        raise evaluation.EvaluationError("source templates cannot embed a circular registration binding")
    template["binding"] = core.as_dict()
    module = codex if host == "codex" else claude
    digest = module.source_contract_sha256(template)
    store = _canonical(registration.data["claudeLaunchStore"]) if host == "claude-code" else None
    return SourceRouteBinding(core, digest, _canonical(template), store)


def observation_from_dict(value, binding, *, now):
    """Restore checked claims only; serialized hashes do not authenticate sources."""
    from .tooling_source_observer import source_observation_from_dict, SourceObserverError
    binding.validate()
    try:
        return source_observation_from_dict(value, binding.contract,
            expected_contract_sha256=binding.contract_sha256, now=now)
    except SourceObserverError as exc:
        raise subscription.SubscriptionError("source observation refused") from exc


def check_observation(observation, binding, *, now, phase=None,
                      process_id=None, process_birth_sha256=None):
    from .tooling_source_observer import check_source_observation, SourceObserverError
    if not isinstance(binding, SourceRouteBinding):
        raise subscription.SubscriptionError("typed source route binding is required")
    binding.validate()
    try:
        return check_source_observation(observation, binding.contract,
            expected_contract_sha256=binding.contract_sha256, now=now,
            expected_binding=binding.binding, phase=phase,
            process_id=process_id, process_birth_sha256=process_birth_sha256)
    except SourceObserverError as exc:
        raise subscription.SubscriptionError("source observation refused") from exc


def audit_selection(registration):
    """Reproduce the prospectively registered sample, never authenticate timing."""
    from . import tooling_evaluation as evaluation
    from . import tooling_human_audit as audit
    evaluation._require_validated(registration)
    if registration.data.get("schemaVersion") != REGISTRATION_SCHEMA or registration.sha256 != _digest(registration.data):
        raise evaluation.EvaluationError("an unchanged v6 registration is required for audit selection")
    return audit.freeze_selection(evaluation.generate_slots(registration), registration.data["humanAuditPolicy"],
        expected_policy_sha256=registration.data["humanAuditPolicySha256"],
        registration_sha256=registration.sha256, rubric_sha256=registration.data["rubric"]["sha256"],
        human_review_roles=evaluation.expected_reviewer_participants(registration))


def require_instrument_identity(verifier, registration, name):
    """Bind an installed trusted verifier's identity; pins alone are not trust."""
    from . import tooling_evaluation as evaluation
    evaluation._require_validated(registration)
    if registration.data.get("schemaVersion") != REGISTRATION_SCHEMA:
        return
    if registration.sha256 != _digest(registration.data) or name not in INSTRUMENTS:
        raise evaluation.EvaluationError("unchanged v6 registration and a known instrument are required")
    pin = registration.data["instrumentPins"][name]
    attributes = ("source_ref", "source_sha256", "verifier_ref", "verifier_sha256")
    expected = (pin["sourceRef"], pin["sourceSha256"], pin["verifierRef"], pin["verifierSha256"])
    if tuple(getattr(verifier, field, None) for field in attributes) != expected:
        raise evaluation.EvaluationError(f"{name} verifier identity differs from the v6 instrument pin")


def check_claude_directory(binding, environment):
    """Recheck the exact canonical path, independently of credential provenance."""
    if binding.host != "claude-code":
        return
    try:
        path = Path(environment["CLAUDE_CONFIG_DIR"])
        if not path.is_absolute() or path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path:
            raise ValueError
        if hashlib.sha256(str(path).encode("utf-8")).hexdigest() != binding.launch_store["canonicalConfigDirSha256"]:
            raise ValueError
    except (KeyError, OSError, TypeError, ValueError, RuntimeError) as exc:
        raise subscription.SubscriptionError("Claude canonical launch directory is unavailable or changed") from exc
