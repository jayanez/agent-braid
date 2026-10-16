# SPDX-License-Identifier: AGPL-3.0-only
"""Offline subscription-only billing policy and observation checks for M4.5.

This module validates caller-provided observations. It does not authenticate
their source or inspect provider accounts; an external trusted observer must
establish authenticity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Mapping

POLICY_SCHEMA = "agent-braid-m45-subscription-policy-v1"
NATIVE_PROCESS_POLICY_SCHEMA = "agent-braid-m45-native-process-route-policy-v2"
OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA = "agent-braid-m45-operational-subscription-policy-v3"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_AUTH = {"codex": "chatgpt", "claude-code": "claude.ai"}


class SubscriptionError(ValueError):
    """Subscription policy or observed account state is unsafe or malformed."""


@dataclass(frozen=True)
class SubscriptionBinding:
    host: str
    registration_sha256: str
    slot_id: str
    policy_sha256: str
    account_sha256: str

    def as_dict(self) -> dict[str, str]:
        return {"host": self.host, "registrationSha256": self.registration_sha256,
                "slotId": self.slot_id, "policySha256": self.policy_sha256,
                "accountSha256": self.account_sha256}


@dataclass(frozen=True)
class SubscriptionObservation:
    binding: SubscriptionBinding
    auth_method: str
    subscription_active: bool
    extra_usage_enabled: bool
    credits_enabled: bool
    auto_recharge_enabled: bool
    api_billing_enabled: bool
    quota_available: bool
    additional_spend_eur: int | float
    source_ref: str
    source_sha256: str
    observed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        if not isinstance(self.binding, SubscriptionBinding):
            raise SubscriptionError("observation binding must be a SubscriptionBinding")
        if not isinstance(self.observed_at, datetime) or self.observed_at.tzinfo is None:
            raise SubscriptionError("observation timestamp must be timezone-aware")
        return {"binding": self.binding.as_dict(), "authMethod": self.auth_method,
                "subscriptionActive": self.subscription_active,
                "extraUsageEnabled": self.extra_usage_enabled,
                "creditsEnabled": self.credits_enabled,
                "autoRechargeEnabled": self.auto_recharge_enabled,
                "apiBillingEnabled": self.api_billing_enabled,
                "quotaAvailable": self.quota_available,
                "additionalSpendEur": self.additional_spend_eur,
                "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
                "observedAt": _iso(self.observed_at)}


@dataclass(frozen=True)
class NativeProcessRouteBinding:
    """Exact registration and native process contract for a single slot."""
    host: str
    registration_sha256: str
    slot_id: str
    policy_sha256: str
    account_sha256: str
    account_namespace_sha256: str
    host_build_sha256: str
    candidate_artifact_sha256: str
    executable_sha256: str
    config_sha256: str
    argv_sha256: str
    model_identity_sha256: str
    observer_source_ref: str
    observer_source_sha256: str
    observer_verifier_ref: str
    observer_verifier_sha256: str
    cash_source_ref: str
    cash_source_sha256: str
    cash_verifier_ref: str
    cash_verifier_sha256: str
    max_age_seconds: float

    def as_dict(self) -> dict[str, Any]:
        return {"host": self.host, "registrationSha256": self.registration_sha256,
                "slotId": self.slot_id, "policySha256": self.policy_sha256,
                "accountSha256": self.account_sha256,
                "accountNamespaceSha256": self.account_namespace_sha256,
                "hostBuildSha256": self.host_build_sha256,
                "candidateArtifactSha256": self.candidate_artifact_sha256,
                "executableSha256": self.executable_sha256,
                "configSha256": self.config_sha256, "argvSha256": self.argv_sha256,
                "modelIdentitySha256": self.model_identity_sha256,
                "observerSourceRef": self.observer_source_ref,
                "observerSourceSha256": self.observer_source_sha256,
                "observerVerifierRef": self.observer_verifier_ref,
                "observerVerifierSha256": self.observer_verifier_sha256,
                "cashSourceRef": self.cash_source_ref, "cashSourceSha256": self.cash_source_sha256,
                "cashVerifierRef": self.cash_verifier_ref,
                "cashVerifierSha256": self.cash_verifier_sha256,
                "maxAgeSeconds": self.max_age_seconds}


@dataclass(frozen=True)
class CohortCashObservation:
    """Independent cash-source snapshot; callers still need a trusted verifier."""
    registration_sha256: str
    additional_cash_eur: int | float
    setup_covered: bool
    started_slot_ids: tuple[str, ...]
    completion_reconciled: bool
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str
    observed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        _validate_cash_shape(self)
        return {"registrationSha256": self.registration_sha256,
                "additionalCashEur": self.additional_cash_eur,
                "setupCovered": self.setup_covered,
                "startedSlotIds": list(self.started_slot_ids),
                "completionReconciled": self.completion_reconciled,
                "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
                "verifierRef": self.verifier_ref, "verifierSha256": self.verifier_sha256,
                "observedAt": _iso(self.observed_at)}


@dataclass(frozen=True)
class NativeProcessRouteObservation:
    """Untrusted serialized assertions about one process-scoped route snapshot."""
    binding: NativeProcessRouteBinding
    phase: str
    auth_method: str
    route: str
    account_wide_api_billing: str
    subscription_active: bool
    quota_available: bool
    extra_usage_enabled: bool
    credits_enabled: bool
    auto_recharge_enabled: bool
    api_credential_available: bool
    provider_override_available: bool
    fallback_available: bool
    per_operation_gate_active: bool
    no_provider_operation_before_bind: bool
    observer_connected: bool
    process_id: int | None
    process_birth_sha256: str | None
    observed_sequence: int
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str
    observed_at: datetime
    cash: CohortCashObservation

    def as_dict(self) -> dict[str, Any]:
        _validate_native_observation_shape(self)
        return {"binding": self.binding.as_dict(), "phase": self.phase,
                "authMethod": self.auth_method, "route": self.route,
                "accountWideApiBilling": self.account_wide_api_billing,
                "subscriptionActive": self.subscription_active,
                "quotaAvailable": self.quota_available,
                "extraUsageEnabled": self.extra_usage_enabled,
                "creditsEnabled": self.credits_enabled,
                "autoRechargeEnabled": self.auto_recharge_enabled,
                "apiCredentialAvailable": self.api_credential_available,
                "providerOverrideAvailable": self.provider_override_available,
                "fallbackAvailable": self.fallback_available,
                "perOperationGateActive": self.per_operation_gate_active,
                "noProviderOperationBeforeBind": self.no_provider_operation_before_bind,
                "observerConnected": self.observer_connected,
                "processId": self.process_id,
                "processBirthSha256": self.process_birth_sha256,
                "observedSequence": self.observed_sequence,
                "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
                "verifierRef": self.verifier_ref, "verifierSha256": self.verifier_sha256,
                "observedAt": _iso(self.observed_at), "cash": self.cash.as_dict()}


@dataclass(frozen=True)
class OperationalProcessRouteBinding:
    """Registration-frozen process identity for an operational quota check."""
    host: str
    registration_sha256: str
    slot_id: str
    policy_sha256: str
    account_sha256: str
    account_namespace_sha256: str
    host_build_sha256: str
    candidate_artifact_sha256: str
    executable_sha256: str
    config_sha256: str
    argv_sha256: str
    model_identity_sha256: str
    observer_source_ref: str
    observer_source_sha256: str
    observer_verifier_ref: str
    observer_verifier_sha256: str
    max_age_seconds: float

    def as_dict(self) -> dict[str, Any]:
        return {"schema": OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA,
                "host": self.host, "registrationSha256": self.registration_sha256,
                "slotId": self.slot_id, "policySha256": self.policy_sha256,
                "accountSha256": self.account_sha256,
                "accountNamespaceSha256": self.account_namespace_sha256,
                "hostBuildSha256": self.host_build_sha256,
                "candidateArtifactSha256": self.candidate_artifact_sha256,
                "executableSha256": self.executable_sha256,
                "configSha256": self.config_sha256, "argvSha256": self.argv_sha256,
                "modelIdentitySha256": self.model_identity_sha256,
                "observerSourceRef": self.observer_source_ref,
                "observerSourceSha256": self.observer_source_sha256,
                "observerVerifierRef": self.observer_verifier_ref,
                "observerVerifierSha256": self.observer_verifier_sha256,
                "maxAgeSeconds": self.max_age_seconds}


@dataclass(frozen=True)
class OperationalProcessRouteObservation:
    """Fresh process route and provider-enforced quota snapshot; contains no cash claim."""
    binding: OperationalProcessRouteBinding
    phase: str
    auth_method: str
    route: str
    account_wide_api_billing: str
    subscription_active: bool
    quota_available: bool
    extra_usage_enabled: bool
    credits_enabled: bool
    auto_recharge_enabled: bool
    api_credential_available: bool
    provider_override_available: bool
    fallback_available: bool
    quota_boundary_active: bool
    no_provider_operation_before_bind: bool
    observer_connected: bool
    process_id: int | None
    process_birth_sha256: str | None
    observed_sequence: int
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str
    observed_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {"binding": self.binding.as_dict(), "phase": self.phase,
                "authMethod": self.auth_method, "route": self.route,
                "accountWideApiBilling": self.account_wide_api_billing,
                "subscriptionActive": self.subscription_active,
                "quotaAvailable": self.quota_available,
                "extraUsageEnabled": self.extra_usage_enabled,
                "creditsEnabled": self.credits_enabled,
                "autoRechargeEnabled": self.auto_recharge_enabled,
                "apiCredentialAvailable": self.api_credential_available,
                "providerOverrideAvailable": self.provider_override_available,
                "fallbackAvailable": self.fallback_available,
                "quotaBoundaryActive": self.quota_boundary_active,
                "noProviderOperationBeforeBind": self.no_provider_operation_before_bind,
                "observerConnected": self.observer_connected,
                "processId": self.process_id,
                "processBirthSha256": self.process_birth_sha256,
                "observedSequence": self.observed_sequence,
                "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
                "verifierRef": self.verifier_ref, "verifierSha256": self.verifier_sha256,
                "observedAt": _iso(self.observed_at)}


def policy_sha256(policy: Mapping[str, Any]) -> str:
    _validate_policy(policy)
    try:
        encoded = json.dumps(policy, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SubscriptionError("billing policy must contain finite JSON values") from exc
    return hashlib.sha256(encoded).hexdigest()


def binding_from_registration(registration: Any, slot_id: str, host: str) -> SubscriptionBinding | NativeProcessRouteBinding | OperationalProcessRouteBinding | None:
    data = getattr(registration, "data", registration)
    if isinstance(data, Mapping) and data.get("schemaVersion") == "agent-braid-m45-registration-v6":
        from .tooling_registration_v6 import binding_from_registration as source_binding
        return source_binding(registration, slot_id, host)
    registration_sha = getattr(registration, "sha256", None)
    if not isinstance(data, Mapping) or "billingPolicy" not in data:
        return None
    policy = data["billingPolicy"]
    if isinstance(policy, Mapping) and policy.get("schema") == OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA:
        _validate_operational_policy(policy)
        registration_sha = registration_sha or _canonical_sha256(data)
        _hash(registration_sha, "registration SHA-256")
        if not isinstance(slot_id, str) or not slot_id.strip() or host not in _AUTH:
            raise SubscriptionError("slot_id and registered host are required")
        host_row = next(row for row in policy["hosts"] if row["host"] == host)
        contract = policy["processContracts"].get(slot_id)
        if not isinstance(contract, Mapping) or contract.get("host") != host:
            raise SubscriptionError("slot has no operational process contract for the requested host")
        observer = policy["observer"]
        return OperationalProcessRouteBinding(
            host, registration_sha, slot_id, policy_sha256(policy), host_row["accountSha256"],
            host_row["accountNamespaceSha256"], contract["hostBuildSha256"],
            contract["candidateArtifactSha256"], contract["executableSha256"],
            contract["configSha256"], contract["argvSha256"], contract["modelIdentitySha256"],
            observer["sourceRef"], observer["sourceSha256"], observer["verifierRef"],
            observer["verifierSha256"], policy["maxAgeSeconds"])
    if isinstance(policy, Mapping) and policy.get("schema") == NATIVE_PROCESS_POLICY_SCHEMA:
        _validate_native_process_policy(policy)
        registration_sha = registration_sha or _canonical_sha256(data)
        _hash(registration_sha, "registration SHA-256")
        if not isinstance(slot_id, str) or not slot_id.strip():
            raise SubscriptionError("slot_id must be nonempty text")
        if not isinstance(host, str) or host not in _AUTH:
            raise SubscriptionError("host must be codex or claude-code")
        host_row = next(row for row in policy["hosts"] if row["host"] == host)
        contract = policy["processContracts"].get(slot_id)
        if not isinstance(contract, Mapping) or contract.get("host") != host:
            raise SubscriptionError("slot has no native process contract for the requested host")
        observer, cash_source = policy["observer"], policy["cashSource"]
        return NativeProcessRouteBinding(
            host, registration_sha, slot_id, policy_sha256(policy), host_row["accountSha256"],
            host_row["accountNamespaceSha256"], contract["hostBuildSha256"],
            contract["candidateArtifactSha256"], contract["executableSha256"],
            contract["configSha256"], contract["argvSha256"], contract["modelIdentitySha256"],
            observer["sourceRef"], observer["sourceSha256"], observer["verifierRef"],
            observer["verifierSha256"], cash_source["sourceRef"], cash_source["sourceSha256"],
            cash_source["verifierRef"], cash_source["verifierSha256"], policy["maxAgeSeconds"])
    digest = policy_sha256(policy)
    if registration_sha is None:
        registration_sha = _canonical_sha256(data)
    _hash(registration_sha, "registration SHA-256")
    if not isinstance(slot_id, str) or not slot_id.strip():
        raise SubscriptionError("slot_id must be nonempty text")
    if not isinstance(host, str) or host not in _AUTH:
        raise SubscriptionError("host must be codex or claude-code")
    account = next((entry["accountSha256"] for entry in policy["hosts"] if entry["host"] == host), None)
    if account is None:
        raise SubscriptionError("host is absent from subscription policy")
    return SubscriptionBinding(host, registration_sha, slot_id, digest, account)


def check_observation(observation: SubscriptionObservation | NativeProcessRouteObservation,
                      binding: SubscriptionBinding | NativeProcessRouteBinding | OperationalProcessRouteBinding,
                      now: datetime | None = None, max_age_seconds: float = 60) -> bool:
    if isinstance(observation, OperationalProcessRouteObservation) or isinstance(binding, OperationalProcessRouteBinding):
        return _check_operational_observation(observation, binding, now, max_age_seconds)
    if isinstance(observation, NativeProcessRouteObservation) or isinstance(binding, NativeProcessRouteBinding):
        return _check_native_process_observation(observation, binding, now, max_age_seconds)
    if not isinstance(observation, SubscriptionObservation) or not isinstance(binding, SubscriptionBinding):
        raise SubscriptionError("observation and binding must use the typed subscription records")
    binding_from_dict(binding.as_dict())
    if not _finite_number(max_age_seconds) or max_age_seconds < 0:
        raise SubscriptionError("max_age_seconds must be finite and nonnegative")
    if not isinstance(observation.binding, SubscriptionBinding):
        raise SubscriptionError("observation binding must be a SubscriptionBinding")
    binding_from_dict(observation.binding.as_dict())
    if observation.binding != binding:
        raise SubscriptionError("subscription observation is bound to a different registration, slot, policy, account, or host")
    if not isinstance(observation.auth_method, str) or binding.host not in _AUTH or observation.auth_method != _AUTH[binding.host]:
        raise SubscriptionError("subscription authentication method does not match the registered host")
    bool_fields = (observation.subscription_active, observation.extra_usage_enabled,
                   observation.credits_enabled, observation.auto_recharge_enabled,
                   observation.api_billing_enabled, observation.quota_available)
    if any(type(value) is not bool for value in bool_fields):
        raise SubscriptionError("subscription observations require explicit boolean values")
    if any((observation.extra_usage_enabled, observation.credits_enabled,
            observation.auto_recharge_enabled, observation.api_billing_enabled)):
        raise SubscriptionError("paid usage, credits, auto-recharge, and API billing must all be disabled")
    if not observation.subscription_active or not observation.quota_available:
        raise SubscriptionError("active included subscription quota is unavailable")
    spend = observation.additional_spend_eur
    if not _finite_number(spend) or spend != 0:
        raise SubscriptionError("additional observed spend must be finite and exactly zero EUR")
    if not isinstance(observation.source_ref, str) or not observation.source_ref.strip():
        raise SubscriptionError("source_ref must identify the observation source")
    _hash(observation.source_sha256, "observation source SHA-256")
    current = datetime.now(timezone.utc) if now is None else now
    if (not isinstance(current, datetime) or not isinstance(observation.observed_at, datetime)
            or current.tzinfo is None or observation.observed_at.tzinfo is None):
        raise SubscriptionError("observation timestamps must be timezone-aware")
    age = (current - observation.observed_at).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise SubscriptionError("subscription observation is from the future or stale")
    return True


def _check_operational_observation(observation: Any, binding: Any,
                                   now: datetime | None, max_age_seconds: float) -> bool:
    if not isinstance(observation, OperationalProcessRouteObservation) or not isinstance(binding, OperationalProcessRouteBinding):
        raise SubscriptionError("operational observation and binding must use typed operational records")
    if observation.binding != binding:
        raise SubscriptionError("operational observation is bound to a different registration, slot, or process contract")
    if not _finite_number(max_age_seconds) or max_age_seconds < 0:
        raise SubscriptionError("max_age_seconds must be finite and nonnegative")
    flags = (observation.subscription_active, observation.quota_available,
             observation.extra_usage_enabled, observation.credits_enabled,
             observation.auto_recharge_enabled, observation.api_credential_available,
             observation.provider_override_available, observation.fallback_available,
             observation.quota_boundary_active, observation.no_provider_operation_before_bind,
             observation.observer_connected)
    if any(type(flag) is not bool for flag in flags):
        raise SubscriptionError("operational route controls must be explicit booleans")
    if observation.auth_method != _AUTH[binding.host] or observation.route != "included-subscription-quota":
        raise SubscriptionError("operational route or authentication differs from the registered host")
    if observation.account_wide_api_billing != "unknown-out-of-scope":
        raise SubscriptionError("account-wide API billing must remain unknown and out of scope")
    if not observation.subscription_active or not observation.quota_available:
        raise SubscriptionError("included subscription quota is unavailable or exhausted")
    if any((observation.extra_usage_enabled, observation.credits_enabled,
            observation.auto_recharge_enabled, observation.api_credential_available,
            observation.provider_override_available, observation.fallback_available)):
        raise SubscriptionError("paid route, credential, override, or fallback is available")
    if not (observation.quota_boundary_active and observation.no_provider_operation_before_bind
            and observation.observer_connected):
        raise SubscriptionError("provider-enforced per-operation quota boundary is not active")
    if (observation.source_ref, observation.source_sha256,
            observation.verifier_ref, observation.verifier_sha256) != (
            binding.observer_source_ref, binding.observer_source_sha256,
            binding.observer_verifier_ref, binding.observer_verifier_sha256):
        raise SubscriptionError("operational observer or verifier differs from the frozen policy")
    if observation.phase not in {"prelaunch", "running", "completed"}:
        raise SubscriptionError("operational route phase is invalid")
    if observation.phase == "prelaunch":
        if observation.process_id is not None or observation.process_birth_sha256 is not None:
            raise SubscriptionError("prelaunch observation cannot identify a process")
    elif (type(observation.process_id) is not int or observation.process_id <= 0
          or not isinstance(observation.process_birth_sha256, str)
          or not _SHA256.fullmatch(observation.process_birth_sha256)):
        raise SubscriptionError("running operational observation requires process identity")
    if type(observation.observed_sequence) is not int or observation.observed_sequence < 1:
        raise SubscriptionError("operational observation sequence must be positive")
    _check_fresh(observation.observed_at, now, min(max_age_seconds, binding.max_age_seconds),
                 "operational subscription route observation")
    return True


def binding_from_dict(value: Mapping[str, Any]) -> SubscriptionBinding | NativeProcessRouteBinding | OperationalProcessRouteBinding:
    if isinstance(value, Mapping) and value.get("schema") == OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA:
        return operational_binding_from_dict(value)
    if isinstance(value, Mapping) and "accountNamespaceSha256" in value:
        return native_binding_from_dict(value)  # type: ignore[return-value]
    if not isinstance(value, Mapping) or set(value) != {
            "host", "registrationSha256", "slotId", "policySha256", "accountSha256"}:
        raise SubscriptionError("invalid serialized subscription binding")
    try:
        result = SubscriptionBinding(value["host"], value["registrationSha256"], value["slotId"],
                                     value["policySha256"], value["accountSha256"])
    except (KeyError, TypeError) as exc:
        raise SubscriptionError("invalid serialized subscription binding") from exc
    if not isinstance(result.host, str) or result.host not in _AUTH or not isinstance(result.slot_id, str) or not result.slot_id.strip():
        raise SubscriptionError("invalid serialized subscription binding")
    for key, digest in (("registration", result.registration_sha256), ("policy", result.policy_sha256),
                        ("account", result.account_sha256)):
        _hash(digest, f"{key} SHA-256")
    return result


def observation_from_dict(value: Mapping[str, Any]) -> SubscriptionObservation | NativeProcessRouteObservation | OperationalProcessRouteObservation:
    """Reconstruct a receipt observation; authenticity still needs external verification."""
    if isinstance(value, Mapping) and "quotaBoundaryActive" in value:
        return operational_observation_from_dict(value)
    if isinstance(value, Mapping) and "cash" in value:
        return native_process_observation_from_dict(value)  # type: ignore[return-value]
    expected = {"binding", "authMethod", "subscriptionActive", "extraUsageEnabled", "creditsEnabled",
                "autoRechargeEnabled", "apiBillingEnabled", "quotaAvailable", "additionalSpendEur",
                "sourceRef", "sourceSha256", "observedAt"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SubscriptionError("invalid serialized subscription observation")
    try:
        observed_at = datetime.fromisoformat(value["observedAt"].replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        result = SubscriptionObservation(
            binding=binding_from_dict(value["binding"]), auth_method=value["authMethod"],
            subscription_active=value["subscriptionActive"],
            extra_usage_enabled=value["extraUsageEnabled"], credits_enabled=value["creditsEnabled"],
            auto_recharge_enabled=value["autoRechargeEnabled"],
            api_billing_enabled=value["apiBillingEnabled"], quota_available=value["quotaAvailable"],
            additional_spend_eur=value["additionalSpendEur"], source_ref=value["sourceRef"],
            source_sha256=value["sourceSha256"], observed_at=observed_at)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise SubscriptionError("invalid serialized subscription observation") from exc
    if not isinstance(result.auth_method, str):
        raise SubscriptionError("invalid serialized subscription authentication method")
    if any(type(flag) is not bool for flag in (result.subscription_active, result.extra_usage_enabled,
            result.credits_enabled, result.auto_recharge_enabled, result.api_billing_enabled,
            result.quota_available)):
        raise SubscriptionError("serialized subscription flags must be booleans")
    if not _finite_number(result.additional_spend_eur):
        raise SubscriptionError("serialized additional spend must be finite numeric EUR")
    if not isinstance(result.source_ref, str) or not result.source_ref.strip():
        raise SubscriptionError("serialized source reference must be nonempty")
    _hash(result.source_sha256, "observation source SHA-256")
    return result


def native_process_observation_from_dict(value: Mapping[str, Any]) -> NativeProcessRouteObservation:
    """Decode strict v2 data. Decoding does not authenticate any assertion."""
    fields = {"binding", "phase", "authMethod", "route", "accountWideApiBilling",
              "subscriptionActive", "quotaAvailable", "extraUsageEnabled", "creditsEnabled",
              "autoRechargeEnabled", "apiCredentialAvailable", "providerOverrideAvailable",
              "fallbackAvailable", "perOperationGateActive", "noProviderOperationBeforeBind",
              "observerConnected", "processId", "processBirthSha256", "observedSequence",
              "sourceRef", "sourceSha256", "verifierRef", "verifierSha256", "observedAt", "cash"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise SubscriptionError("invalid serialized native process route observation")
    try:
        result = NativeProcessRouteObservation(
            binding=native_binding_from_dict(value["binding"]), phase=value["phase"],
            auth_method=value["authMethod"], route=value["route"],
            account_wide_api_billing=value["accountWideApiBilling"],
            subscription_active=value["subscriptionActive"], quota_available=value["quotaAvailable"],
            extra_usage_enabled=value["extraUsageEnabled"], credits_enabled=value["creditsEnabled"],
            auto_recharge_enabled=value["autoRechargeEnabled"],
            api_credential_available=value["apiCredentialAvailable"],
            provider_override_available=value["providerOverrideAvailable"],
            fallback_available=value["fallbackAvailable"],
            per_operation_gate_active=value["perOperationGateActive"],
            no_provider_operation_before_bind=value["noProviderOperationBeforeBind"],
            observer_connected=value["observerConnected"], process_id=value["processId"],
            process_birth_sha256=value["processBirthSha256"],
            observed_sequence=value["observedSequence"], source_ref=value["sourceRef"],
            source_sha256=value["sourceSha256"], verifier_ref=value["verifierRef"],
            verifier_sha256=value["verifierSha256"],
            observed_at=_parse_timestamp(value["observedAt"]),
            cash=cash_observation_from_dict(value["cash"]))
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise SubscriptionError("invalid serialized native process route observation") from exc
    _validate_native_observation_shape(result)
    return result


def native_binding_from_dict(value: Mapping[str, Any]) -> NativeProcessRouteBinding:
    expected = {"host", "registrationSha256", "slotId", "policySha256", "accountSha256",
                "accountNamespaceSha256", "hostBuildSha256", "candidateArtifactSha256",
                "executableSha256", "configSha256", "argvSha256", "modelIdentitySha256",
                "observerSourceRef", "observerSourceSha256", "observerVerifierRef",
                "observerVerifierSha256", "cashSourceRef", "cashSourceSha256",
                "cashVerifierRef", "cashVerifierSha256", "maxAgeSeconds"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SubscriptionError("invalid serialized native process route binding")
    result = NativeProcessRouteBinding(value["host"], value["registrationSha256"], value["slotId"],
        value["policySha256"], value["accountSha256"], value["accountNamespaceSha256"],
        value["hostBuildSha256"], value["candidateArtifactSha256"], value["executableSha256"],
        value["configSha256"], value["argvSha256"], value["modelIdentitySha256"],
        value["observerSourceRef"], value["observerSourceSha256"],
        value["observerVerifierRef"], value["observerVerifierSha256"],
        value["cashSourceRef"], value["cashSourceSha256"], value["cashVerifierRef"],
        value["cashVerifierSha256"], value["maxAgeSeconds"])
    if not isinstance(result.host, str) or result.host not in _AUTH or not isinstance(result.slot_id, str) or not result.slot_id.strip():
        raise SubscriptionError("invalid serialized native process route binding")
    for name, digest in result.as_dict().items():
        if name.endswith("Sha256"):
            _hash(digest, name)
    for name in ("observerSourceRef", "observerVerifierRef", "cashSourceRef", "cashVerifierRef"):
        if not isinstance(result.as_dict()[name], str) or not result.as_dict()[name].strip():
            raise SubscriptionError(f"{name} must be nonempty text")
    if not _finite_number(result.max_age_seconds) or not 0 < result.max_age_seconds <= 60:
        raise SubscriptionError("native process maximum age must be positive and at most 60 seconds")
    if (result.observer_source_ref, result.observer_source_sha256) == (
            result.cash_source_ref, result.cash_source_sha256):
        raise SubscriptionError("route observer and actual-cash evidence must use independent sources")
    return result


def operational_binding_from_dict(value: Mapping[str, Any]) -> OperationalProcessRouteBinding:
    fields = {"schema", "host", "registrationSha256", "slotId", "policySha256", "accountSha256",
              "accountNamespaceSha256", "hostBuildSha256", "candidateArtifactSha256", "executableSha256",
              "configSha256", "argvSha256", "modelIdentitySha256", "observerSourceRef",
              "observerSourceSha256", "observerVerifierRef", "observerVerifierSha256", "maxAgeSeconds"}
    if not isinstance(value, Mapping) or set(value) != fields or value["schema"] != OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA:
        raise SubscriptionError("invalid serialized operational subscription binding")
    parsed = {"host": value["host"], "registration_sha256": value["registrationSha256"],
              "slot_id": value["slotId"], "policy_sha256": value["policySha256"],
              "account_sha256": value["accountSha256"], "account_namespace_sha256": value["accountNamespaceSha256"],
              "host_build_sha256": value["hostBuildSha256"], "candidate_artifact_sha256": value["candidateArtifactSha256"],
              "executable_sha256": value["executableSha256"], "config_sha256": value["configSha256"],
              "argv_sha256": value["argvSha256"], "model_identity_sha256": value["modelIdentitySha256"],
              "observer_source_ref": value["observerSourceRef"], "observer_source_sha256": value["observerSourceSha256"],
              "observer_verifier_ref": value["observerVerifierRef"], "observer_verifier_sha256": value["observerVerifierSha256"],
              "max_age_seconds": value["maxAgeSeconds"]}
    result = OperationalProcessRouteBinding(**parsed)
    if result.host not in _AUTH or not isinstance(result.slot_id, str) or not result.slot_id.strip():
        raise SubscriptionError("invalid operational subscription host or slot")
    for name, digest in parsed.items():
        if name.endswith("_sha256"):
            _hash(digest, name)
    if not _finite_number(result.max_age_seconds) or not 0 < result.max_age_seconds <= 60:
        raise SubscriptionError("operational binding freshness limit is invalid")
    for name in ("observer_source_ref", "observer_verifier_ref"):
        if not isinstance(getattr(result, name), str) or not getattr(result, name).strip():
            raise SubscriptionError(f"{name} must be nonempty")
    return result


def operational_observation_from_dict(value: Mapping[str, Any]) -> OperationalProcessRouteObservation:
    fields = {"binding", "phase", "authMethod", "route", "accountWideApiBilling", "subscriptionActive",
              "quotaAvailable", "extraUsageEnabled", "creditsEnabled", "autoRechargeEnabled",
              "apiCredentialAvailable", "providerOverrideAvailable", "fallbackAvailable", "quotaBoundaryActive",
              "noProviderOperationBeforeBind", "observerConnected", "processId", "processBirthSha256",
              "observedSequence", "sourceRef", "sourceSha256", "verifierRef", "verifierSha256", "observedAt"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise SubscriptionError("invalid serialized operational subscription observation")
    try:
        observed_at = datetime.fromisoformat(value["observedAt"].replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            raise ValueError("timezone required")
        result = OperationalProcessRouteObservation(
            operational_binding_from_dict(value["binding"]), value["phase"], value["authMethod"],
            value["route"], value["accountWideApiBilling"], value["subscriptionActive"],
            value["quotaAvailable"], value["extraUsageEnabled"], value["creditsEnabled"],
            value["autoRechargeEnabled"], value["apiCredentialAvailable"], value["providerOverrideAvailable"],
            value["fallbackAvailable"], value["quotaBoundaryActive"], value["noProviderOperationBeforeBind"],
            value["observerConnected"], value["processId"], value["processBirthSha256"],
            value["observedSequence"], value["sourceRef"], value["sourceSha256"],
            value["verifierRef"], value["verifierSha256"], observed_at)
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise SubscriptionError("invalid serialized operational subscription observation") from exc
    if not isinstance(result.auth_method, str) or not isinstance(result.route, str):
        raise SubscriptionError("operational route identifiers must be text")
    for name in ("source_ref", "verifier_ref"):
        if not isinstance(getattr(result, name), str) or not getattr(result, name).strip():
            raise SubscriptionError(f"{name} must be nonempty")
    _hash(result.source_sha256, "operational source SHA-256")
    _hash(result.verifier_sha256, "operational verifier SHA-256")
    return result


def cash_observation_from_dict(value: Mapping[str, Any]) -> CohortCashObservation:
    expected = {"registrationSha256", "additionalCashEur", "setupCovered", "startedSlotIds",
                "completionReconciled", "sourceRef", "sourceSha256", "verifierRef",
                "verifierSha256", "observedAt"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SubscriptionError("invalid serialized cohort cash observation")
    if not isinstance(value["startedSlotIds"], list):
        raise SubscriptionError("cash started slots must be a list")
    try:
        result = CohortCashObservation(value["registrationSha256"], value["additionalCashEur"],
            value["setupCovered"], tuple(value["startedSlotIds"]), value["completionReconciled"],
            value["sourceRef"], value["sourceSha256"], value["verifierRef"],
            value["verifierSha256"], _parse_timestamp(value["observedAt"]))
    except (TypeError, ValueError) as exc:
        raise SubscriptionError("invalid serialized cohort cash observation") from exc
    _validate_cash_shape(result)
    return result


def check_cash_observation(cash: CohortCashObservation, binding: NativeProcessRouteBinding,
                           phase: str, now: datetime | None = None,
                           max_age_seconds: float = 60) -> bool:
    if not isinstance(cash, CohortCashObservation) or not isinstance(binding, NativeProcessRouteBinding):
        raise SubscriptionError("cash observation requires native v2 typed records")
    if not _finite_number(max_age_seconds) or max_age_seconds < 0:
        raise SubscriptionError("max_age_seconds must be finite and nonnegative")
    _validate_native_binding(binding)
    _validate_cash_shape(cash)
    if not isinstance(phase, str) or phase not in {"prelaunch", "running", "completed"}:
        raise SubscriptionError("native process phase must be prelaunch, running, or completed")
    _check_fresh(cash.observed_at, now, min(max_age_seconds, binding.max_age_seconds), "cohort cash observation")
    if cash.registration_sha256 != binding.registration_sha256:
        raise SubscriptionError("cash evidence is bound to a different registration cohort")
    if (cash.source_ref, cash.source_sha256, cash.verifier_ref, cash.verifier_sha256) != (
            binding.cash_source_ref, binding.cash_source_sha256,
            binding.cash_verifier_ref, binding.cash_verifier_sha256):
        raise SubscriptionError("cash evidence source or verifier differs from the frozen policy")
    if cash.additional_cash_eur != 0:
        raise SubscriptionError("independent cohort additional cash must be exactly zero EUR")
    if not cash.setup_covered or (phase in {"running", "completed"} and binding.slot_id not in cash.started_slot_ids):
        raise SubscriptionError("cash evidence does not cover setup and the current started slot")
    if (phase == "completed") != cash.completion_reconciled:
        raise SubscriptionError("cohort cash completion reconciliation does not match process phase")
    return True


def _validate_policy(policy: Mapping[str, Any]) -> None:
    if isinstance(policy, Mapping) and policy.get("schema") == OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA:
        _validate_operational_policy(policy)
        return
    if isinstance(policy, Mapping) and policy.get("schema") == NATIVE_PROCESS_POLICY_SCHEMA:
        _validate_native_process_policy(policy)
        return
    if not isinstance(policy, Mapping):
        raise SubscriptionError("billing policy must be an object")
    required = {"schema", "mode", "additionalSpendCapEur", "paidApiAllowed", "overageAllowed",
                "creditsAllowed", "autoRechargeAllowed", "hosts"}
    if set(policy) != required or policy.get("schema") != POLICY_SCHEMA or policy.get("mode") != "included-subscription-only":
        raise SubscriptionError("unsupported or malformed subscription-only billing policy")
    cap = policy.get("additionalSpendCapEur")
    if not _finite_number(cap) or cap != 0:
        raise SubscriptionError("additional spend cap must be exactly zero EUR")
    if any(policy.get(flag) is not False for flag in ("paidApiAllowed", "overageAllowed", "creditsAllowed", "autoRechargeAllowed")):
        raise SubscriptionError("paid API, overage, credits, and auto-recharge must be disabled")
    hosts = policy.get("hosts")
    if not isinstance(hosts, list) or len(hosts) != 2:
        raise SubscriptionError("policy must bind both subscription hosts")
    seen = set()
    for entry in hosts:
        if not isinstance(entry, Mapping) or set(entry) != {"host", "accountSha256", "authMethod"}:
            raise SubscriptionError("malformed policy host account binding")
        host = entry.get("host")
        if not isinstance(host, str) or host not in _AUTH or host in seen or entry.get("authMethod") != _AUTH[host]:
            raise SubscriptionError("policy host or authentication method is invalid")
        _hash(entry.get("accountSha256"), f"{host} account SHA-256")
        seen.add(host)
    if seen != set(_AUTH):
        raise SubscriptionError("policy must bind codex and claude-code")


def _validate_native_process_policy(policy: Mapping[str, Any]) -> None:
    required = {"schema", "mode", "scope", "accountWideApiBilling", "additionalSpendCapEur", "maxAgeSeconds",
                "paidApiAllowed", "overageAllowed", "creditsAllowed", "autoRechargeAllowed",
                "hosts", "processContracts", "observer", "cashSource"}
    if not isinstance(policy, Mapping) or set(policy) != required:
        raise SubscriptionError("unsupported or malformed native process route policy")
    if (policy["schema"] != NATIVE_PROCESS_POLICY_SCHEMA
            or policy["mode"] != "included-subscription-only"
            or policy["scope"] != "registered-native-process-only"
            or policy["accountWideApiBilling"] != "unknown-out-of-scope"):
        raise SubscriptionError("native process route policy scope is invalid")
    if not _finite_number(policy["additionalSpendCapEur"]) or policy["additionalSpendCapEur"] != 0:
        raise SubscriptionError("additional spend cap must be exactly zero EUR")
    if not _finite_number(policy["maxAgeSeconds"]) or not 0 < policy["maxAgeSeconds"] <= 60:
        raise SubscriptionError("native process maximum age must be positive and at most 60 seconds")
    if any(policy[name] is not False for name in
           ("paidApiAllowed", "overageAllowed", "creditsAllowed", "autoRechargeAllowed")):
        raise SubscriptionError("paid API, overage, credits, and auto-recharge must be disabled")
    hosts = policy["hosts"]
    if not isinstance(hosts, list) or len(hosts) != 2:
        raise SubscriptionError("policy must bind both subscription hosts")
    seen: set[str] = set()
    for row in hosts:
        if not isinstance(row, Mapping) or set(row) != {
                "host", "accountSha256", "accountNamespaceSha256", "authMethod"}:
            raise SubscriptionError("malformed native host account binding")
        host = row["host"]
        if not isinstance(host, str) or host not in _AUTH or host in seen or row["authMethod"] != _AUTH[host]:
            raise SubscriptionError("native host or authentication method is invalid")
        _hash(row["accountSha256"], f"{host} account SHA-256")
        _hash(row["accountNamespaceSha256"], f"{host} account namespace SHA-256")
        seen.add(host)
    if seen != set(_AUTH):
        raise SubscriptionError("policy must bind codex and claude-code")
    contracts = policy["processContracts"]
    if not isinstance(contracts, Mapping) or not contracts:
        raise SubscriptionError("native process contracts must be a nonempty slot mapping")
    expected_contract = {"host", "hostBuildSha256", "candidateArtifactSha256", "executableSha256",
                         "configSha256", "argvSha256", "modelIdentitySha256"}
    for slot, contract in contracts.items():
        if not isinstance(slot, str) or not slot.strip() or not isinstance(contract, Mapping) or set(contract) != expected_contract:
            raise SubscriptionError("malformed per-slot native process contract")
        if not isinstance(contract["host"], str) or contract["host"] not in _AUTH:
            raise SubscriptionError("native process contract host is invalid")
        for name in expected_contract - {"host"}:
            _hash(contract[name], name)
    _validate_source_pair(policy["observer"], "observer", extra={"continuousPerOperationControlRequired"})
    if policy["observer"]["continuousPerOperationControlRequired"] is not True:
        raise SubscriptionError("continuous trusted per-operation route control is mandatory")
    _validate_source_pair(policy["cashSource"], "cash source", extra={"cohortBindingRequired"})
    if policy["cashSource"]["cohortBindingRequired"] is not True:
        raise SubscriptionError("independent cohort cash source binding is mandatory")
    if (policy["observer"]["sourceRef"], policy["observer"]["sourceSha256"]) == (
            policy["cashSource"]["sourceRef"], policy["cashSource"]["sourceSha256"]):
        raise SubscriptionError("route observer and actual-cash evidence must use independent sources")


def _validate_operational_policy(policy: Mapping[str, Any]) -> None:
    """Validate the additive subscription-quota admission policy without a cash assertion."""
    required = {"schema", "mode", "scope", "accountWideApiBilling", "additionalSpendCapEur",
                "maxAgeSeconds", "paidApiAllowed", "overageAllowed", "creditsAllowed",
                "autoRechargeAllowed", "hosts", "processContracts", "observer"}
    if not isinstance(policy, Mapping) or set(policy) != required:
        raise SubscriptionError("unsupported or malformed operational subscription policy")
    if (policy["schema"] != OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA
            or policy["mode"] != "included-subscription-only"
            or policy["scope"] != "registered-native-process-only"
            or policy["accountWideApiBilling"] != "unknown-out-of-scope"):
        raise SubscriptionError("operational subscription policy scope is invalid")
    if not _finite_number(policy["additionalSpendCapEur"]) or policy["additionalSpendCapEur"] != 0:
        raise SubscriptionError("additional spend cap must be exactly zero EUR")
    if not _finite_number(policy["maxAgeSeconds"]) or not 0 < policy["maxAgeSeconds"] <= 60:
        raise SubscriptionError("operational route maximum age must be positive and at most 60 seconds")
    if any(policy[name] is not False for name in
           ("paidApiAllowed", "overageAllowed", "creditsAllowed", "autoRechargeAllowed")):
        raise SubscriptionError("paid API, overage, credits, and auto-recharge must be disabled")
    hosts = policy["hosts"]
    if not isinstance(hosts, list) or len(hosts) != 2:
        raise SubscriptionError("policy must bind both subscription hosts")
    seen = set()
    for row in hosts:
        if not isinstance(row, Mapping) or set(row) != {
                "host", "accountSha256", "accountNamespaceSha256", "authMethod"}:
            raise SubscriptionError("malformed operational host account binding")
        host = row["host"]
        if not isinstance(host, str) or host not in _AUTH or host in seen or row["authMethod"] != _AUTH[host]:
            raise SubscriptionError("operational host authentication is invalid")
        _hash(row["accountSha256"], "account SHA-256")
        _hash(row["accountNamespaceSha256"], "account namespace SHA-256")
        seen.add(host)
    if seen != set(_AUTH):
        raise SubscriptionError("policy must bind codex and claude-code")
    contracts = policy["processContracts"]
    expected = {"host", "hostBuildSha256", "candidateArtifactSha256", "executableSha256",
                "configSha256", "argvSha256", "modelIdentitySha256"}
    if not isinstance(contracts, Mapping) or not contracts:
        raise SubscriptionError("operational process contracts are required")
    for slot, contract in contracts.items():
        if not isinstance(slot, str) or not slot.strip() or not isinstance(contract, Mapping) or set(contract) != expected:
            raise SubscriptionError("malformed operational per-slot process contract")
        if not isinstance(contract["host"], str) or contract["host"] not in _AUTH:
            raise SubscriptionError("operational process contract host is invalid")
        for key in expected - {"host"}:
            _hash(contract[key], key)
    _validate_source_pair(policy["observer"], "operational observer",
                          extra={"providerEnforcedQuotaBoundaryRequired"})
    if policy["observer"]["providerEnforcedQuotaBoundaryRequired"] is not True:
        raise SubscriptionError("provider-enforced included-quota boundary is required")


def _validate_source_pair(value: Any, label: str, extra: set[str] | None = None) -> None:
    expected = {"sourceRef", "sourceSha256", "verifierRef", "verifierSha256"} | (extra or set())
    if not isinstance(value, Mapping) or set(value) != expected:
        raise SubscriptionError(f"malformed {label} source and verifier binding")
    for key in ("sourceRef", "verifierRef"):
        if not isinstance(value[key], str) or not value[key].strip():
            raise SubscriptionError(f"{label} {key} must be nonempty text")
    _hash(value["sourceSha256"], f"{label} source SHA-256")
    _hash(value["verifierSha256"], f"{label} verifier SHA-256")


def _check_native_process_observation(observation: Any, binding: Any,
                                     now: datetime | None, max_age_seconds: float) -> bool:
    if not isinstance(observation, NativeProcessRouteObservation) or not isinstance(binding, NativeProcessRouteBinding):
        raise SubscriptionError("native v2 observation and binding must use typed records")
    _validate_native_binding(binding)
    if not _finite_number(max_age_seconds) or max_age_seconds < 0:
        raise SubscriptionError("max_age_seconds must be finite and nonnegative")
    if observation.binding != binding:
        raise SubscriptionError("native process observation is bound to a different registration, slot, policy, identity, or host")
    _validate_native_observation_shape(observation)
    if observation.auth_method != _AUTH[binding.host]:
        raise SubscriptionError("native process authentication method differs from registered host")
    if observation.route != "included-subscription-quota":
        raise SubscriptionError("native process route is not included subscription quota")
    if observation.account_wide_api_billing != "unknown-out-of-scope":
        raise SubscriptionError("account-wide API billing must remain unknown and out of scope")
    if (not observation.subscription_active or not observation.quota_available
            or observation.extra_usage_enabled or observation.credits_enabled
            or observation.auto_recharge_enabled or observation.api_credential_available
            or observation.provider_override_available or observation.fallback_available):
        raise SubscriptionError("native process route controls or included quota are unsafe")
    if not (observation.per_operation_gate_active and observation.no_provider_operation_before_bind
            and observation.observer_connected):
        raise SubscriptionError("trusted continuous per-operation gate is not asserted active")
    if (observation.source_ref, observation.source_sha256,
            observation.verifier_ref, observation.verifier_sha256) != (
            binding.observer_source_ref, binding.observer_source_sha256,
            binding.observer_verifier_ref, binding.observer_verifier_sha256):
        raise SubscriptionError("observer source or verifier differs from the frozen policy")
    effective_age = min(max_age_seconds, binding.max_age_seconds)
    _check_fresh(observation.observed_at, now, effective_age, "native process route observation")
    check_cash_observation(observation.cash, binding, observation.phase, now, effective_age)
    return True


def _validate_native_binding(binding: NativeProcessRouteBinding) -> None:
    native_binding_from_dict(binding.as_dict())


def _validate_native_observation_shape(value: NativeProcessRouteObservation) -> None:
    if not isinstance(value, NativeProcessRouteObservation):
        raise SubscriptionError("native process route observation must use its typed record")
    if not isinstance(value.binding, NativeProcessRouteBinding):
        raise SubscriptionError("native process route observation requires a typed binding")
    _validate_native_binding(value.binding)
    if not isinstance(value.phase, str) or value.phase not in {"prelaunch", "running", "completed"}:
        raise SubscriptionError("native process phase must be prelaunch, running, or completed")
    if value.phase == "prelaunch":
        if value.process_id is not None or value.process_birth_sha256 is not None:
            raise SubscriptionError("prelaunch observation cannot claim a process identity")
    else:
        if type(value.process_id) is not int or value.process_id <= 0:
            raise SubscriptionError("launched process observation requires a positive PID")
        _hash(value.process_birth_sha256, "process birth identity SHA-256")
    if type(value.observed_sequence) is not int or value.observed_sequence < 0:
        raise SubscriptionError("observation sequence must be a nonnegative integer")
    flags = (value.subscription_active, value.quota_available, value.extra_usage_enabled,
             value.credits_enabled, value.auto_recharge_enabled, value.api_credential_available,
             value.provider_override_available, value.fallback_available,
             value.per_operation_gate_active, value.no_provider_operation_before_bind,
             value.observer_connected)
    if any(type(flag) is not bool for flag in flags):
        raise SubscriptionError("native route controls require explicit boolean values")
    for name in ("source_ref", "verifier_ref"):
        if not isinstance(getattr(value, name), str) or not getattr(value, name).strip():
            raise SubscriptionError(f"{name} must be nonempty text")
    for name in ("source_sha256", "verifier_sha256"):
        _hash(getattr(value, name), name)
    if not isinstance(value.observed_at, datetime) or value.observed_at.tzinfo is None:
        raise SubscriptionError("native route timestamp must be timezone-aware")
    if not isinstance(value.cash, CohortCashObservation):
        raise SubscriptionError("native route observation requires a typed independent cash record")
    _validate_cash_shape(value.cash)


def _validate_cash_shape(cash: CohortCashObservation) -> None:
    if not isinstance(cash, CohortCashObservation):
        raise SubscriptionError("cash observation must use its typed record")
    _hash(cash.registration_sha256, "cash registration SHA-256")
    if not _finite_number(cash.additional_cash_eur):
        raise SubscriptionError("cash amount must be finite numeric EUR")
    if type(cash.setup_covered) is not bool or type(cash.completion_reconciled) is not bool:
        raise SubscriptionError("cash coverage controls must be explicit booleans")
    if not isinstance(cash.started_slot_ids, tuple) or any(not isinstance(slot, str) or not slot.strip() for slot in cash.started_slot_ids):
        raise SubscriptionError("cash started slots must be nonempty identifiers")
    if len(set(cash.started_slot_ids)) != len(cash.started_slot_ids):
        raise SubscriptionError("cash started slot coverage contains duplicates")
    for name in ("source_ref", "verifier_ref"):
        if not isinstance(getattr(cash, name), str) or not getattr(cash, name).strip():
            raise SubscriptionError(f"cash {name} must be nonempty text")
    for name in ("source_sha256", "verifier_sha256"):
        _hash(getattr(cash, name), name)
    if not isinstance(cash.observed_at, datetime) or cash.observed_at.tzinfo is None:
        raise SubscriptionError("cash timestamp must be timezone-aware")


def _check_fresh(observed_at: datetime, now: datetime | None,
                 max_age_seconds: float, label: str) -> None:
    if not _finite_number(max_age_seconds) or max_age_seconds < 0:
        raise SubscriptionError("max_age_seconds must be finite and nonnegative")
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime) or current.tzinfo is None or observed_at.tzinfo is None:
        raise SubscriptionError("observation timestamps must be timezone-aware")
    age = (current - observed_at).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise SubscriptionError(f"{label} is from the future or stale")


def _parse_timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def _hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise SubscriptionError(f"{label} must be a lowercase SHA-256")
    return value


def _finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, TypeError):
        return False


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


__all__ = ["NATIVE_PROCESS_POLICY_SCHEMA", "OPERATIONAL_SUBSCRIPTION_POLICY_SCHEMA", "POLICY_SCHEMA",
           "CohortCashObservation", "NativeProcessRouteBinding", "NativeProcessRouteObservation",
           "OperationalProcessRouteBinding", "OperationalProcessRouteObservation", "SubscriptionBinding",
           "SubscriptionError", "SubscriptionObservation", "binding_from_dict",
           "binding_from_registration", "cash_observation_from_dict", "check_cash_observation",
           "check_observation", "native_binding_from_dict", "native_process_observation_from_dict",
           "observation_from_dict", "operational_binding_from_dict", "operational_observation_from_dict",
           "policy_sha256"]
