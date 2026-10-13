# SPDX-License-Identifier: AGPL-3.0-only
"""Additive Claude source composition; never synthesizes v3 payment booleans.

This validates source *claims*. Authentic acquisition and independent source
verification remain the observer's responsibility. A result is not a launch
permit and cannot be passed as an OperationalProcessRouteObservation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any

from .tooling_subscription import (
    OperationalProcessRouteBinding, SubscriptionError,
    operational_binding_from_dict,
)

CONTRACT_SCHEMA = "agent-braid-claude-source-contract-v1"
RECEIPT_SCHEMA = "agent-braid-claude-source-receipt-v1"
KINDS = ("quota", "autoRecharge", "process")
PIN_FIELDS = {"sourceRef", "sourceSha256", "verifierRef", "verifierSha256"}
PROCESS_TRUE = {"quotaBoundaryActive", "noProviderOperationBeforeBind", "observerConnected"}
PROCESS_FALSE = {"apiCredentialAvailable", "helperCredentialAvailable",
                 "providerOverrideAvailable", "fallbackAvailable"}
LAUNCH_TRUE = {"settingSourcesEmpty", "pinnedSettingsOnly", "childEnvAllowlistOnly", "canonicalConfigDir"}
LAUNCH_FALSE = {"policySettingsCanInjectCredentials"}
ORGANIZATION_BINDING = "owner-declared-single-organization"
INTERFACE_BASIS = "interface-observation"
AUTO_RECHARGE_MAX_AGE_CEILING_SECONDS = 900
PROFILE_UI_SKEW_SECONDS = 600
_WINDOWS = ("fiveHour", "sevenDay")
_SUFFIX = re.compile(r"[0-9a-f]{8}")


@dataclass(frozen=True)
class ClaudeSourceComposition:
    """Checked claims, not authenticated source evidence or capture authority."""

    contract_sha256: str
    binding: OperationalProcessRouteBinding
    keychain_suffix: str
    phase: str
    process_id: int | None
    process_birth_sha256: str | None
    observed_sequence: int
    receipt_sha256: tuple[str, ...]
    valid_until: datetime


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError) as exc:
        raise SubscriptionError("Claude source records must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _shape(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise SubscriptionError(f"invalid {label} fields")


def _hash(value: Any) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise SubscriptionError("source identity must be a lowercase SHA-256")


def _number(value: Any, label: str) -> float:
    try:
        finite = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise SubscriptionError(f"{label} must be a finite number")
    return value


def _time(value: Any, label: str) -> datetime:
    try:
        if not isinstance(value, str):
            raise ValueError("timestamp must be text")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("timezone required")
        return parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError) as exc:
        raise SubscriptionError(f"invalid {label}") from exc


def _limits(contract: Mapping[str, Any], binding: OperationalProcessRouteBinding) -> dict[str, float]:
    _shape(contract["sourceMaxAgeSeconds"], set(KINDS), "source age limits")
    limits = {kind: _number(contract["sourceMaxAgeSeconds"][kind], f"{kind} age limit") for kind in KINDS}
    for kind, ceiling in (("quota", binding.max_age_seconds), ("process", binding.max_age_seconds),
                          ("autoRecharge", AUTO_RECHARGE_MAX_AGE_CEILING_SECONDS)):
        if not 0 < limits[kind] <= ceiling:
            raise SubscriptionError(f"{kind} age limit is outside its ceiling")
    return limits


def source_contract_sha256(contract: Mapping[str, Any]) -> str:
    """Validate and hash a new contract; does not modify v1/v2/v3 policies."""
    _shape(contract, {"schema", "binding", "additionalSpendCapEur", "isolatedStore",
                      "organizationScope", "sourceMaxAgeSeconds", "sources"}, "source contract")
    if contract["schema"] != CONTRACT_SCHEMA:
        raise SubscriptionError("unsupported Claude source contract")
    cap = contract["additionalSpendCapEur"]
    if type(cap) is not int or cap != 0:
        raise SubscriptionError("additional spend cap must be integer EUR zero")
    binding = operational_binding_from_dict(contract["binding"])
    if binding.host != "claude-code":
        raise SubscriptionError("Claude source contract cannot bind another host")
    _shape(contract["isolatedStore"], {"keychainSuffix"}, "isolated store")
    suffix = contract["isolatedStore"]["keychainSuffix"]
    if not isinstance(suffix, str) or not _SUFFIX.fullmatch(suffix):
        raise SubscriptionError("isolated store suffix must be eight lowercase hex characters")
    _shape(contract["organizationScope"], {"binding", "declarationSha256"}, "organization scope")
    if contract["organizationScope"]["binding"] != ORGANIZATION_BINDING:
        raise SubscriptionError("organization scope must be the owner-declared single organization")
    _hash(contract["organizationScope"]["declarationSha256"])
    _limits(contract, binding)
    _shape(contract["sources"], set(KINDS), "source pins")
    for pin in contract["sources"].values():
        _shape(pin, PIN_FIELDS, "source pin")
        for field in PIN_FIELDS:
            if field.endswith("Sha256"):
                _hash(pin[field])
            elif not isinstance(pin[field], str) or not pin[field].strip():
                raise SubscriptionError("source and verifier references must be nonempty")
    return _digest(contract)


def compose_claude_sources(
    contract: Mapping[str, Any], receipts: Mapping[str, Any], *,
    expected_contract_sha256: str, now: datetime | None = None,
) -> ClaudeSourceComposition:
    """Reject incomplete, unsafe, stale or differently bound source claims.

    Each receipt must already have been independently authenticated against its
    frozen source/verifier pin. Matching labels/digests here does not perform
    that authentication. No runtime admission is granted by this function.
    """
    # Own a JSON snapshot so caller mutation cannot change the checked result.
    contract = json.loads(_canonical(contract))
    receipts = json.loads(_canonical(receipts))
    digest = source_contract_sha256(contract)
    _hash(expected_contract_sha256)
    if digest != expected_contract_sha256:
        raise SubscriptionError("Claude source contract differs from its frozen digest")
    binding = operational_binding_from_dict(contract["binding"])
    limits = _limits(contract, binding)
    suffix = contract["isolatedStore"]["keychainSuffix"]
    _shape(receipts, set(KINDS), "source receipts")
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime) or current.utcoffset() is None:
        raise SubscriptionError("source check time must be timezone-aware")
    identity = None
    expirations = []
    digests = []
    collector_digests = {}
    for kind in KINDS:
        receipt = receipts[kind]
        _shape(receipt, {"schema", "kind", "contractSha256", "binding", "phase", "processId",
                         "processBirthSha256", "observedSequence", "observedAt", "payload"}
                        | PIN_FIELDS, "source receipt")
        if (receipt["schema"] != RECEIPT_SCHEMA or receipt["kind"] != kind
                or receipt["contractSha256"] != digest):
            raise SubscriptionError("source receipt contract or kind mismatch")
        if operational_binding_from_dict(receipt["binding"]) != binding:
            raise SubscriptionError("source account, namespace, candidate or process binding drift")
        if {field: receipt[field] for field in PIN_FIELDS} != contract["sources"][kind]:
            raise SubscriptionError("source or verifier differs from its frozen pin")
        phase, pid, birth, sequence = (receipt[field] for field in (
            "phase", "processId", "processBirthSha256", "observedSequence"))
        if phase not in ("prelaunch", "running", "completed"):
            raise SubscriptionError("invalid source process phase")
        if phase == "prelaunch":
            if pid is not None or birth is not None:
                raise SubscriptionError("prelaunch source cannot claim a launched process")
        else:
            if type(pid) is not int or pid <= 0:
                raise SubscriptionError("launched source requires a positive process ID")
            _hash(birth)
        if type(sequence) is not int or sequence < 1:
            raise SubscriptionError("source sequence must be a positive integer")
        scope = (phase, pid, birth, sequence)
        if identity is not None and identity != scope:
            raise SubscriptionError("source receipts refer to different process observations")
        identity = scope
        observed = _time(receipt["observedAt"], "source timestamp")
        age = (current - observed).total_seconds()
        if not 0 <= age <= limits[kind]:
            raise SubscriptionError("Claude source is from the future or stale")
        expiry = observed + timedelta(seconds=limits[kind])
        expiry = min(expiry, _check_payload(kind, receipt["payload"], suffix, limits, observed,
                                            current, collector_digests,
                                            contract["organizationScope"]["binding"]))
        expirations.append(expiry)
        digests.append(_digest(receipt))
    if collector_digests["autoRecharge"] != collector_digests["process"]:
        raise SubscriptionError("auto-recharge and process claims refer to different collector receipts")
    assert identity is not None
    return ClaudeSourceComposition(digest, binding, suffix, *identity, tuple(digests), min(expirations))


def _flags(payload: Mapping[str, Any], required_true: set[str], required_false: set[str]) -> None:
    for field in required_true | required_false:
        if type(payload[field]) is not bool:
            raise SubscriptionError(f"{field} must be an explicit boolean")
        if payload[field] != (field in required_true):
            raise SubscriptionError(f"unsafe or unavailable Claude source control: {field}")


def _check_payload(kind: str, payload: Any, suffix: str, limits: Mapping[str, float],
                   observed: datetime, current: datetime,
                   collector_digests: dict[str, str], organization_binding: str) -> datetime:
    """Validate one payload and return the latest instant its claims stay current."""
    if kind == "quota":
        _shape(payload, {"extraUsageEnabled", "quotaWindows"}, "quota payload")
        _flags(payload, set(), {"extraUsageEnabled"})
        _shape(payload["quotaWindows"], set(_WINDOWS), "quota windows")
        valid_until = None
        for name in _WINDOWS:
            window = payload["quotaWindows"][name]
            _shape(window, {"usedPct", "resetsAt"}, "quota window")
            if not 0 <= _number(window["usedPct"], "quota used percentage") < 100:
                raise SubscriptionError("included quota window is exhausted or invalid")
            reset = _time(window["resetsAt"], "quota reset time")
            if reset <= max(observed, current):
                raise SubscriptionError("quota window reset is not in the future")
            valid_until = reset if valid_until is None else min(valid_until, reset)
        return valid_until
    if kind == "autoRecharge":
        _shape(payload, {"autoRechargeEnabled", "basis", "accountBound", "organizationBinding",
                         "uiObservedAt", "profileObservedAt", "collectorReceiptSha256",
                         "recorderRecordSha256"}, "auto-recharge payload")
        _flags(payload, {"accountBound"}, {"autoRechargeEnabled"})
        if payload["basis"] != INTERFACE_BASIS:
            raise SubscriptionError("auto-recharge must come from a bound interface observation")
        if payload["organizationBinding"] != organization_binding:
            raise SubscriptionError("auto-recharge organization scope differs from the frozen contract")
        ui = _time(payload["uiObservedAt"], "interface observation time")
        profile = _time(payload["profileObservedAt"], "profile read time")
        if ui > observed or profile > observed:
            raise SubscriptionError("interface or profile observation is from the future")
        if (current - ui).total_seconds() > limits["autoRecharge"]:
            raise SubscriptionError("interface observation is stale")
        if abs((ui - profile).total_seconds()) > PROFILE_UI_SKEW_SECONDS:
            raise SubscriptionError("interface observation is too far from the profile read")
        _hash(payload["collectorReceiptSha256"])
        _hash(payload["recorderRecordSha256"])
        collector_digests[kind] = payload["collectorReceiptSha256"]
        return ui + timedelta(seconds=limits["autoRecharge"])
    _shape(payload, PROCESS_TRUE | PROCESS_FALSE | LAUNCH_TRUE | LAUNCH_FALSE
           | {"authMethod", "route", "storeBinding", "keychainSuffix", "collectorReceiptSha256"},
           "process payload")
    if payload["authMethod"] != "claude.ai" or payload["route"] != "included-subscription-quota":
        raise SubscriptionError("Claude source route must use native included claude.ai usage")
    if payload["storeBinding"] != "bound":
        raise SubscriptionError("isolated credential store is not bound to the profile")
    if payload["keychainSuffix"] != suffix:
        raise SubscriptionError("credential store differs from the frozen isolated store")
    _hash(payload["collectorReceiptSha256"])
    collector_digests[kind] = payload["collectorReceiptSha256"]
    _flags(payload, PROCESS_TRUE | LAUNCH_TRUE, PROCESS_FALSE | LAUNCH_FALSE)
    return observed + timedelta(seconds=limits["process"])
