# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-073: human promotion of a Braid Lightning candidate through the HAR profile registry.

A BL.2 candidate is a whole skill text. It is promoted as a native profile of the
SPEC-049 ``ProfileRegistry`` (``harness_promotion``), identified by its
``candidateSha256``; the text itself lives content-addressed in the Lightning run
store and is copied to the mapped ``SKILL.md`` only by a human-approved apply.

``SCOPES`` is the closed scope map (OD-1: ``lightning.skill.analyze`` only); any
other scope is refused with ``unknown-scope``. ``build_record`` turns a stored
candidate and its SPEC-072 REQ-011 ``Registration``/``EvaluationRecord`` pair into a
checked ``CandidateRecord`` whose ``profile`` is a valid ``harness_promotion``
profile. It refuses an unknown scope, a text that is not stored or does not match
its digest, a text over the scope's limit, a pair whose arm C is not the candidate
and a non-native cohort. The H1 outcome is reported, not enforced here: a pair
without H1 ``supported`` for every required host yields ``no-held-out-support``,
and an apply then needs an explicit owner override reason (OD-5).

Nothing here decides, begins or commits a promotion (``AUTOMATIC_PROMOTION`` stays
``False``); ``executionAuthorization`` is always false.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import harness_promotion as promotion
from . import lightning_store as store
from .harness_evaluation import REGISTRATION_FORMAT, REPORT_FORMAT, EvaluationRecord, Registration
from .system_one import InvalidDecision, canonical, freeze, parse_json

COHORT = "native"
EFFECTS = ("skill-text",)
SUPPORTED = "supported"
NO_SUPPORT = "no-held-out-support"


@dataclass(frozen=True)
class Scope:
    """One closed scope-map entry: the file a promotion may write and its text limit."""

    target: str
    limit: int
    registry: str


# Closed table (OD-1, contracts/scope-map.md). Paths are repository-relative.
SCOPES = {
    "lightning.skill.analyze": Scope(
        target="integrations/agent-braid/skills/agent-braid-analyze/SKILL.md",
        limit=32 * 1024, registry="registry.json"),
}


class PromoteError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise PromoteError(reason)


def scope_entry(scope: Any) -> Scope:
    _require(type(scope) is str and scope in SCOPES, "unknown-scope")
    return SCOPES[scope]


def load_record(cls: type, raw: bytes) -> Any:
    """A SPEC-049 record from its exact canonical JSON bytes (as SPEC-072 commits them)."""
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise PromoteError("invalid-evaluation") from None
    _require(canonical(value) == raw, "invalid-evaluation")
    return cls(freeze(value), raw)


@dataclass(frozen=True)
class CandidateRecord:
    """A stored candidate checked against its scope and evaluation pair; never an authorization."""

    scope: str
    target: str
    candidateSha256: str
    text: str
    registration: Registration
    evaluation: EvaluationRecord
    heldOutSupport: str
    profile: dict

    @property
    def executionAuthorization(self) -> bool:
        return False

    @property
    def evidence(self) -> list[str]:
        """The SPEC-049 record digests this candidate rests on, sorted."""
        return sorted({self.registration.sha256, self.evaluation.sha256})


def _text(run: store.RunStore, sha256: str) -> str:
    try:
        return run.candidate_text(sha256)
    except store.StoreError as exc:
        if exc.code == "candidate-text-missing":
            raise PromoteError("candidate-not-stored") from None
        if exc.code == "candidate-hash-mismatch":
            raise PromoteError("digest-mismatch") from None
        raise PromoteError("candidate-not-stored") from None


def build_record(run: store.RunStore, candidate_sha256: str, scope: str, *,
                 registration: Registration, evaluation: EvaluationRecord,
                 identity: Any) -> CandidateRecord:
    """Check a BL.2 winner for ``scope`` and return its native profile record (REQ-001)."""
    entry = scope_entry(scope)
    _require(type(run) is store.RunStore, "candidate-not-stored")
    text = _text(run, candidate_sha256)
    _require(len(text.encode("utf-8")) <= entry.limit, "text-too-large")
    try:
        reg = promotion._verified(registration, Registration, REGISTRATION_FORMAT)
        report = promotion._verified(evaluation, EvaluationRecord, REPORT_FORMAT)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None
    _require(report.get("registrationSha256") == registration.sha256, "registration-mismatch")
    _require(reg.get("cohort") == COHORT and report.get("cohort") == COHORT, "cohort-mismatch")
    _require(not reg["refinement"]["armCIsBase"], "no-candidate")
    _require(reg["arms"]["C"]["candidateSha256"] == candidate_sha256, "candidate-mismatch")
    hosts = reg.get("requiredHosts") or []
    h1 = (report.get("h1") or {}).get("hosts") or {}
    support = SUPPORTED if hosts and all(h1.get(h) == SUPPORTED for h in hosts) else NO_SUPPORT
    profile = {"candidateSha256": candidate_sha256, "scope": scope, "cohort": COHORT,
               "effects": list(EFFECTS), "identity": identity}
    try:
        promotion._check_profile(profile)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None
    return CandidateRecord(scope, entry.target, candidate_sha256, text, registration, evaluation,
                           support, profile)
