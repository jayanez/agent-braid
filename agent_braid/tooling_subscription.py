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


def policy_sha256(policy: Mapping[str, Any]) -> str:
    _validate_policy(policy)
    try:
        encoded = json.dumps(policy, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SubscriptionError("billing policy must contain finite JSON values") from exc
    return hashlib.sha256(encoded).hexdigest()


def binding_from_registration(registration: Any, slot_id: str, host: str) -> SubscriptionBinding | None:
    data = getattr(registration, "data", registration)
    registration_sha = getattr(registration, "sha256", None)
    if not isinstance(data, Mapping) or "billingPolicy" not in data:
        return None
    policy = data["billingPolicy"]
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


def check_observation(observation: SubscriptionObservation, binding: SubscriptionBinding,
                      now: datetime | None = None, max_age_seconds: float = 60) -> bool:
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


def binding_from_dict(value: Mapping[str, Any]) -> SubscriptionBinding:
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


def observation_from_dict(value: Mapping[str, Any]) -> SubscriptionObservation:
    """Reconstruct a receipt observation; authenticity still needs external verification."""
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


def _validate_policy(policy: Mapping[str, Any]) -> None:
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


__all__ = ["POLICY_SCHEMA", "SubscriptionBinding", "SubscriptionError", "SubscriptionObservation",
           "binding_from_dict", "binding_from_registration", "check_observation", "observation_from_dict",
           "policy_sha256"]
