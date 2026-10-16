# SPDX-License-Identifier: AGPL-3.0-only
"""Additive Codex source composition; never synthesizes v3 payment booleans.

This validates source *claims*. Authentic acquisition and independent source
verification remain the observer's responsibility. A result is not a launch
permit and cannot be passed as an OperationalProcessRouteObservation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from .tooling_subscription import (
    OperationalProcessRouteBinding, SubscriptionError,
    operational_binding_from_dict,
)

CONTRACT_SCHEMA = "agent-braid-codex-source-contract-v1"
RECEIPT_SCHEMA = "agent-braid-codex-source-receipt-v1"
KINDS = ("quota", "autoRecharge", "process")
PIN_FIELDS = {"sourceRef", "sourceSha256", "verifierRef", "verifierSha256"}
PROCESS_TRUE = {"quotaBoundaryActive", "noProviderOperationBeforeBind", "observerConnected"}
PROCESS_FALSE = {"apiCredentialAvailable", "helperCredentialAvailable",
                 "providerOverrideAvailable", "fallbackAvailable"}


@dataclass(frozen=True)
class CodexSourceComposition:
    """Checked claims, not authenticated source evidence or capture authority."""

    contract_sha256: str
    binding: OperationalProcessRouteBinding
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
        raise SubscriptionError("Codex source records must be finite JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _shape(value: Any, keys: set[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise SubscriptionError(f"invalid {label} fields")


def _hash(value: Any) -> None:
    if (not isinstance(value, str) or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise SubscriptionError("source identity must be a lowercase SHA-256")


def source_contract_sha256(contract: Mapping[str, Any]) -> str:
    """Validate and hash a new contract; does not modify v1/v2/v3 policies."""
    _shape(contract, {"schema", "binding", "additionalSpendCapEur", "sources"}, "source contract")
    if contract["schema"] != CONTRACT_SCHEMA:
        raise SubscriptionError("unsupported Codex source contract")
    cap = contract["additionalSpendCapEur"]
    if type(cap) is not int or cap != 0:
        raise SubscriptionError("additional spend cap must be integer EUR zero")
    binding = operational_binding_from_dict(contract["binding"])
    if binding.host != "codex":
        raise SubscriptionError("Codex source contract cannot bind another host")
    _shape(contract["sources"], set(KINDS), "source pins")
    for pin in contract["sources"].values():
        _shape(pin, PIN_FIELDS, "source pin")
        for field in PIN_FIELDS:
            if field.endswith("Sha256"):
                _hash(pin[field])
            elif not isinstance(pin[field], str) or not pin[field].strip():
                raise SubscriptionError("source and verifier references must be nonempty")
    return _digest(contract)


def compose_codex_sources(
    contract: Mapping[str, Any], receipts: Mapping[str, Any], *,
    expected_contract_sha256: str, now: datetime | None = None,
) -> CodexSourceComposition:
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
        raise SubscriptionError("Codex source contract differs from its frozen digest")
    binding = operational_binding_from_dict(contract["binding"])
    _shape(receipts, set(KINDS), "source receipts")
    current = datetime.now(timezone.utc) if now is None else now
    if not isinstance(current, datetime) or current.tzinfo is None:
        raise SubscriptionError("source check time must be timezone-aware")
    identity = None
    expirations = []
    digests = []
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
        try:
            timestamp = receipt["observedAt"]
            if not isinstance(timestamp, str):
                raise ValueError("timestamp must be text")
            observed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                raise ValueError("timezone required")
            age = (current - observed).total_seconds()
        except (ValueError, TypeError, OverflowError) as exc:
            raise SubscriptionError("invalid source timestamp") from exc
        if not 0 <= age <= binding.max_age_seconds:
            raise SubscriptionError("Codex source is from the future or stale")
        expirations.append(observed + timedelta(seconds=binding.max_age_seconds))
        _check_payload(kind, receipt["payload"])
        digests.append(_digest(receipt))
    assert identity is not None
    return CodexSourceComposition(digest, binding, *identity, tuple(digests), min(expirations))


def _flags(payload: Mapping[str, Any], required_true: set[str], required_false: set[str]) -> None:
    for field in required_true | required_false:
        if type(payload[field]) is not bool:
            raise SubscriptionError(f"{field} must be an explicit boolean")
        if payload[field] != (field in required_true):
            raise SubscriptionError(f"unsafe or unavailable Codex source control: {field}")


def _check_payload(kind: str, payload: Any) -> None:
    if kind == "quota":
        _shape(payload, {"ordinaryUsageAllowed", "credits", "spendControlReached"}, "quota payload")
        _shape(payload["credits"], {"hasCredits", "unlimited"}, "credit availability")
        _flags(payload, {"ordinaryUsageAllowed"}, {"spendControlReached"})
        _flags(payload["credits"], set(), {"hasCredits", "unlimited"})
    elif kind == "autoRecharge":
        _shape(payload, {"autoRechargeEnabled"}, "auto-recharge payload")
        _flags(payload, set(), {"autoRechargeEnabled"})
    else:
        _shape(payload, PROCESS_TRUE | PROCESS_FALSE | {"authMethod", "route"}, "process payload")
        if payload["authMethod"] != "chatgpt" or payload["route"] != "included-subscription-quota":
            raise SubscriptionError("Codex source route must use native included ChatGPT usage")
        _flags(payload, PROCESS_TRUE, PROCESS_FALSE)
