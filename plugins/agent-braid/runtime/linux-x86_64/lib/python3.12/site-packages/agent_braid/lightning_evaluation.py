# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-011: the H1 outcome as a SPEC-049 Registration/EvaluationRecord pair.

The held-out report (T010) calls ``spec049_pair`` with the baseline arm A0 and the
preregistered primary arm A2 (GEPA). Each arm carries its candidate hash, its canary
hit count and the per-host D4 summary of ``scripts/spec069_scoring.summarize`` on the
frozen held-out set. The pair uses the SPEC-049 record types and formats
(``REGISTRATION_FORMAT``, ``REPORT_FORMAT``) so that SPEC-073 can pass it to
``harness_promotion.decide()``; arm A is A0 and arm C is A2, and APO (A1) or the
exploratory arms are refused as arm C.

H1 follows ``evaluation-protocol.md`` (analysis plan item 3) per required host: if A0
meets D4 the host is ``not-assessable``; if A0 misses and A2 meets it is ``supported``;
anything else, including an incomplete arm or a canary hit (item 5), is
``not-supported``. Overall: ``not-assessable`` if any required host is, ``supported``
only if every required host is, otherwise ``not-supported``.

The SPEC-049 paired noninferiority test is not part of the frozen protocol, so every
stratum's ``C-vs-A`` comparison is ``descriptive-only``. Candidates appear by hash only.
This module writes records; it never calls ``decide()``, reads no file, host, model or
clock, and ``executionAuthorization`` is always false.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
import re
from typing import Any

from .harness_evaluation import (REGISTRATION_FORMAT, REPORT_FORMAT, EvaluationRecord, Registration,
                                 _record)
from .system_one import digest

REQUIRED_HOSTS = ("claude-code",)  # Amendment 1 (2026-11-13)
SOURCE = "spec072-lightning-heldout"
ARMS = {"A": ("A0", "baseline-current-guidance"), "C": ("A2", "gepa-primary")}
VERDICTS = ("meets", "misses", "inconclusive", "unobserved")
OUTCOMES = ("supported", "not-supported", "not-assessable")
PENDING_ENDPOINTS = ("interventions", "rework", "interrupted-recovery",
                     "conflict-precision-recall", "false-safe-admissions", "useful-parallelism")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ARM_KEYS = {"arm", "candidateSha256", "canaryHits", "summary"}
_HOST_FIELDS = ("verdict", "trials", "prompts", "firstAttemptPrompts", "withinRetryPrompts")


class LightningEvaluationError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise LightningEvaluationError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _count(value: Any) -> bool:
    return type(value) is int and value >= 0


def _cost(value: Any) -> bool:
    """A cost table: string keys and non-negative finite numbers only (no text)."""
    return isinstance(value, Mapping) and all(
        type(k) is str and (_count(v) or (type(v) is float and math.isfinite(v) and v >= 0))
        for k, v in value.items())


def _arm(result: Any, slot: str, hosts: tuple[str, ...]) -> dict:
    """Validated arm result for ``slot``; only the per-host D4 fields are kept."""
    _require(isinstance(result, Mapping) and set(result) == _ARM_KEYS, "invalid-arm")
    label = ARMS[slot][0]
    _require(result["arm"] == label, f"arm-{slot.lower()}-not-{label.lower()}")
    _require(_hash(result["candidateSha256"]) and _count(result["canaryHits"]), "invalid-arm")
    summary = result["summary"]
    _require(isinstance(summary, Mapping) and isinstance(summary.get("hosts"), Mapping)
             and all(isinstance(summary["hosts"].get(h), Mapping) for h in hosts), "host-missing")
    per_host = {}
    for host in hosts:
        raw = summary["hosts"][host]
        _require(raw.get("verdict") in VERDICTS
                 and all(_count(raw.get(k)) for k in _HOST_FIELDS[1:]), "invalid-arm")
        per_host[host] = {k: raw[k] for k in _HOST_FIELDS}
    return {"candidateSha256": result["candidateSha256"], "canaryHits": result["canaryHits"],
            "valid": result["canaryHits"] == 0, "hosts": per_host}


def h1_outcome(a0: Mapping, a2: Mapping, hosts: tuple[str, ...] = REQUIRED_HOSTS) -> dict:
    """The protocol's decision rule over two validated arms (see the module docstring)."""
    per_host = {}
    for host in hosts:
        base = a0["hosts"][host]["verdict"] if a0["valid"] else "invalidated"
        primary = a2["hosts"][host]["verdict"] if a2["valid"] else "invalidated"
        if base == "meets":
            per_host[host] = "not-assessable"
        elif base == "misses" and primary == "meets":
            per_host[host] = "supported"
        else:
            per_host[host] = "not-supported"
    values = set(per_host.values())
    overall = ("not-assessable" if "not-assessable" in values
               else "supported" if values == {"supported"} else "not-supported")
    return {"outcome": overall, "hosts": per_host}


def spec049_pair(*, baseline: Mapping, primary: Mapping, heldout_sha256: str, protocol_sha256: str,
                 costs: Mapping[str, Any],
                 required_hosts: tuple[str, ...] = REQUIRED_HOSTS) -> tuple[Registration, EvaluationRecord]:
    """Registration (A = A0, C = A2) and the H1 report bound to it by ``registrationSha256``."""
    _require(type(required_hosts) is tuple and required_hosts
             and all(type(h) is str and h for h in required_hosts)
             and len(set(required_hosts)) == len(required_hosts), "invalid-hosts")
    _require(_hash(heldout_sha256) and _hash(protocol_sha256), "invalid-binding")
    _require(isinstance(costs, Mapping) and set(costs) == {"A", "C"}
             and all(_cost(v) for v in costs.values()), "invalid-costs")
    a0 = _arm(baseline, "A", required_hosts)
    a2 = _arm(primary, "C", required_hosts)
    arm_c_is_base = a2["candidateSha256"] == a0["candidateSha256"]
    refinement = {"decision": "keep-base" if arm_c_is_base else "candidate",
                  "selection": "development-score-P2", "armCIsBase": arm_c_is_base}
    registration = _record(Registration, {
        "format": REGISTRATION_FORMAT, "source": SOURCE, "cohort": "native",
        "heldOutSha256": heldout_sha256, "protocolSha256": protocol_sha256,
        "requiredHosts": list(required_hosts),
        "arms": {slot: {"arm": label, "role": role, "candidateSha256": arm["candidateSha256"]}
                 for (slot, (label, role)), arm in zip(ARMS.items(), (a0, a2))},
        "refinement": refinement, "executionAuthorization": False})
    h1 = h1_outcome(a0, a2, required_hosts)
    strata = {host: {
        "arms": {"A": {**a0["hosts"][host], "canaryHits": a0["canaryHits"], "valid": a0["valid"]},
                 "C": {**a2["hosts"][host], "canaryHits": a2["canaryHits"], "valid": a2["valid"]}},
        "comparisons": {"C-vs-A": {
            "h1": h1["hosts"][host],
            "noninferiority": {"status": "descriptive-only", "verdict": None,
                               "reasons": ["spec072-d4-rule"]}}}} for host in required_hosts}
    costs = {slot: dict(value) for slot, value in costs.items()}
    report = _record(EvaluationRecord, {
        "format": REPORT_FORMAT, "source": SOURCE, "registrationSha256": registration.sha256,
        "cohort": "native", "refinement": refinement, "h1": h1, "strata": strata,
        "costs": costs, "costReportSha256": digest(costs),
        "pendingEndpoints": list(PENDING_ENDPOINTS), "executionAuthorization": False})
    return registration, report
