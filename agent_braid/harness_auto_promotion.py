# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T009 disabled-by-default automatic-promotion policy engine; offline, no authority.

Original implementation compiling the 16 ordered, fail-closed eligibility rules of
``specs/049-harness-evaluation-learning/auto-promotion-assessment.md`` (SPEC-049/T008, whose
prose table is the contract; its sha256 is bound as ``ASSESSMENT_SHA256``). Pure and offline:
no file, clock, host, model, network or process access. Every result carries
``executionAuthorization`` false, and no function here can activate anything:
``harness_promotion.AUTOMATIC_PROMOTION`` stays False, ``PolicyRun.activate`` always refuses,
and nothing creates, begins or commits a promotion decision.

* ``AutoPolicy`` is the exact, versioned, immutable policy. Only the ``synthetic`` cohort
  and the closed layers ``guidance`` and ``context-packaging`` can be named; the native
  cohort, wider layers or an adoption record are refused when the policy is built, because
  native activation needs a separately adopted policy that offline code cannot supply. No
  numeric default exists: budget, canary size and failure tolerance are caller-fixed limits.
* ``assess`` is the pure eligibility decision. Beyond the assessment table it rebuilds the
  T013 record from the verified T003 registration and report (a forged score or edited
  record no longer reproduces), derives change class, changed layers and scope from the
  hashed candidate and base inventories instead of trusting caller declarations, and binds
  the caller-supplied evaluation tick. Preconditions refuse with ``invalid-input`` or
  ``candidate-not-bound`` or ``record-not-reproducible`` before rule 1. Every stop signal
  (``revoked``, ``conflicts``, ``spent``, ``incident``) is required; an omitted or
  malformed one abstains with ``invalid-input``. Current T003 evidence lists pending
  endpoints, so a policy that tolerates none abstains with ``pending-endpoints``.
* ``PolicyRun`` is the immutable state machine ``disabled -> shadow -> canary -> stopped``
  (``active`` is in the vocabulary but unreachable). It starts ``disabled``. ``begin_canary``
  re-runs ``assess`` and never trusts an assessment value; ``observe`` and ``stop`` halt
  fail closed (a bad clock, registry or observation still halts) and report a failed
  registry rollback (``Step.registryFailure``) instead of hiding it. ``stop`` acts on the
  registry's current active profile, not only on this run's candidate: a canary never begins
  a registry transition, so a drift or incident stop withdraws whatever a human activated.
  ``PolicyRun`` is a value, not tamper-evident: ``dataclasses.replace`` can forge its fields,
  which grants nothing (``activate`` always refuses) but means the canary and terminal states
  are conventions for honest callers. A stopped run is terminal for these methods;
  restarting needs a new run and a new human decision.

Records prove binding, not authenticity: the T003 registration and report are only checked to
reproduce the record, not re-derived from unit rows, so a forged report that is internally
consistent is not detected here. Also: the human actor, checker identity, safety counts,
conflict and revocation ledgers, spend, incident flag and evaluation tick are
caller-asserted and must be checked against trusted records. Controls and tests use
synthetic doubles only and qualify nothing native.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
import re
from typing import Any

from .harness_evaluation import EvaluationRecord, Registration
from .harness_manifest import DEFAULT_LIMITS
from .harness_promotion import (COHORTS, MAX_LIST, MAX_TICK, PromotionDecision, PromotionError,
                                ProfileRegistry, decide)
from .harness_surface import _PROTECTED as PROTECTED_COMPONENTS, SurfaceError, normalize_rel
from .system_one import digest, freeze, thaw

POLICY_FORMAT = "braid-harness-auto-policy/v0.1"
ASSESSMENT_SHA256 = "f097a2cfb26af8ef1e0c9e60ff0912e16c1de1121dff1dd9a1b7e6d214fc8e51"
ASSESSMENT_PATH = "specs/049-harness-evaluation-learning/auto-promotion-assessment.md"
CHANGE_CLASS = "task-local-guidance-packaging"
SCOPE = "task-local"
ADOPTED_COHORTS = ("synthetic",)  # native needs a separately adopted policy (not representable)
ALLOWED_LAYERS = ("context-packaging", "guidance")  # closed; the policy may only narrow it
STATES = ("disabled", "shadow", "canary", "active", "stopped")
# Ordered rule table: the contract's order and abstention reasons, checked by a conformance test.
RULES = ("decision-not-pending", "limits-not-fixed-before-evaluation", "change-class-ineligible",
         "layer-not-allowed", "scope-changed", "effect-outside-bound", "cohort-not-adopted",
         "stale-identity", "evidence-revoked", "evidence-conflict", "regression-not-covered",
         "pending-endpoints", "safety-violation", "incident-stop", "budget-exhausted",
         "acceptance")
STOP_REASONS = {"drift": "drift-stop", "canary": "canary-halt", "incident": "incident-stop"}
MAX_ROWS = 256
INERT_SUFFIXES = (".md", ".txt")
_IDENTITY_KEYS = ("sourceSha256", "host", "model", "toolSetSha256", "policySha256")
_POLICY_KEYS = {"format", "assessmentSha256", "fixedAt", "changeClass", "scope", "cohorts",
                "effects", "allowedLayers", "tolerablePendingEndpoints", "budgetCap", "canary",
                "adoption", "executionAuthorization"}
_ROW_KEYS = {"path", "sha256", "sizeBytes"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


class AutoPromotionError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-input"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-input") -> None:
    if not condition:
        raise AutoPromotionError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _int(value: Any, low: int = 0, high: int = MAX_TICK) -> bool:
    return type(value) is int and low <= value < high


def _ids(value: Any, check=_id) -> bool:
    return (type(value) in (list, tuple) and len(value) <= MAX_LIST and all(map(check, value))
            and len(set(value)) == len(value))


def _sorted_ids(value: Any) -> bool:
    return _ids(value) and list(value) == sorted(value)


# --- policy -------------------------------------------------------------------------


@dataclass(frozen=True)
class AutoPolicy:
    """Immutable validated policy; ``sha256`` binds its canonical content."""

    data: Mapping[str, Any]

    @property
    def sha256(self) -> str:
        return digest(self.data)

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


def build_policy(value: Any) -> AutoPolicy:
    """Validate a policy mapping; it can never widen the assessed class, layers or cohort."""
    try:
        value = thaw(value)
    except RecursionError:
        raise AutoPromotionError("invalid-policy") from None
    _require(type(value) is dict and set(value) == _POLICY_KEYS, "invalid-policy")
    _require(value["format"] == POLICY_FORMAT and value["assessmentSha256"] == ASSESSMENT_SHA256
             and value["executionAuthorization"] is False and value["adoption"] is None,
             "invalid-policy")
    _require(_int(value["fixedAt"]) and _int(value["budgetCap"]), "invalid-policy")
    _require(value["changeClass"] == CHANGE_CLASS and value["scope"] == SCOPE, "invalid-policy")
    _require(_sorted_ids(value["cohorts"]) and value["cohorts"]
             and set(value["cohorts"]) <= set(COHORTS), "invalid-policy")
    _require(set(value["cohorts"]) <= set(ADOPTED_COHORTS), "cohort-not-adoptable")
    _require(_sorted_ids(value["allowedLayers"]) and value["allowedLayers"]
             and set(value["allowedLayers"]) <= set(ALLOWED_LAYERS), "layer-not-adoptable")
    _require(_sorted_ids(value["effects"]) and _sorted_ids(value["tolerablePendingEndpoints"]),
             "invalid-policy")
    canary = value["canary"]
    _require(type(canary) is dict and set(canary) == {"size", "maxFailures"}
             and _int(canary["size"], 1, 1 << 16) and _int(canary["maxFailures"], 0, 1 << 16),
             "invalid-policy")
    return AutoPolicy(freeze(value))


# --- candidate derivation -----------------------------------------------------------


def _rows(value: Any) -> dict[str, dict] | None:
    """Sorted, unique, exactly-spelled inventory rows keyed by path; None when malformed."""
    if type(value) not in (list, tuple) or len(value) > MAX_ROWS:
        return None
    rows: dict[str, dict] = {}
    for row in value:
        if type(row) is not dict or set(row) != _ROW_KEYS or not _hash(row["sha256"]) \
                or not _int(row["sizeBytes"], 0, 1 << 40):
            return None
        try:
            normalize_rel(row["path"], depth=DEFAULT_LIMITS["maxPathDepth"])
        except SurfaceError:
            return None
        rows[row["path"]] = row
    if list(rows) != sorted(rows) or len(rows) != len(value):
        return None
    return rows


def _layers(path: str) -> set[str]:
    """The root layer plus every protected or hidden component the path passes through."""
    parts = path.split("/")
    layers = {parts[0] if len(parts) > 1 else "(root)"}
    for part in parts:
        name = part.split(".", 1)[0].rstrip(" .").casefold()
        if part.startswith("."):
            layers.add("hidden")
        elif name in PROTECTED_COMPONENTS:
            layers.add(name)
    return layers


def derive_candidate(base_rows: Any, candidate_rows: Any) -> dict | None:
    """Change class, changed layers and scope from the two hashed inventories.

    Every added, modified or deleted path counts as changed; the class is the policy class
    only when every changed path is inert text (an empty change has no layer and abstains at
    the layer rule), and the scope is task-local only inside the
    laboratory file and byte ceilings. ``None`` when either inventory is malformed.
    """
    base, candidate = _rows(base_rows), _rows(candidate_rows)
    if base is None or candidate is None:
        return None
    changed = sorted(p for p in base.keys() | candidate.keys() if base.get(p) != candidate.get(p))
    layers = sorted(set().union(*map(_layers, changed)))
    inert = all(p.endswith(INERT_SUFFIXES) for p in changed)
    bounded = (len(candidate) <= DEFAULT_LIMITS["maxFiles"]
               and sum(r["sizeBytes"] for r in candidate.values()) <= DEFAULT_LIMITS["maxCandidateBytes"]
               and all(r["sizeBytes"] <= DEFAULT_LIMITS["maxFileBytes"] for r in candidate.values()))
    return {"changeClass": CHANGE_CLASS if inert else "not-inert-text", "layersChanged": layers,
            "scope": SCOPE if bounded else "beyond-task-local", "changedPaths": changed}


# --- eligibility --------------------------------------------------------------------


@dataclass(frozen=True)
class Assessment:
    """One deterministic eligibility decision; it grants nothing."""

    outcome: str
    reason: str | None
    rule: int | None  # 1-16 for a rule abstention, 0 for a precondition, None when eligible
    decisionSha256: str | None
    policySha256: str

    @property
    def executionAuthorization(self) -> bool:
        return False

    @property
    def eligible(self) -> bool:
        return self.outcome == "eligible-proposal"

    def to_dict(self) -> dict:
        return {"outcome": self.outcome, "reason": self.reason, "rule": self.rule,
                "decisionSha256": self.decisionSha256, "policySha256": self.policySha256,
                "assessmentSha256": ASSESSMENT_SHA256, "executionAuthorization": False,
                "activation": "requires-separate-adr-and-operator-decision" if self.eligible
                else None}


def _cited(d: Mapping) -> frozenset:
    return frozenset({d["registrationSha256"], d["evaluationSha256"], d["costReportSha256"],
                      *d["evidenceSha256s"]})


def _rebuilt(record: PromotionDecision, registration: Registration,
             evaluation: EvaluationRecord) -> bool:
    """Whether the verified T003 inputs reproduce this exact record (forged scores do not)."""
    d = record.to_dict()
    try:
        again = decide(registration, evaluation, profile=d["profile"], actor=d["actor"],
                       decision=d["decision"], safety=d["safety"], evidence=d["evidenceSha256s"],
                       rollback_target=d["rollbackTargetSha256"], limits=d["limits"],
                       at=d["decidedAt"])
    except PromotionError:
        return False
    return again.sha256 == record.sha256


def _acceptance(accept: Any, record: PromotionDecision, d: Mapping, proposer: Mapping) -> str | None:
    """The acceptance abstention reason, or None when the record is bound and independent."""
    if accept is None:
        return "acceptance-missing"
    checker = accept.get("checker") if type(accept) is dict else None
    if (type(checker) is not dict or set(checker) != {"kind", "id"}
            or checker["kind"] != "independent-check" or not _id(checker["id"])
            or checker["id"].casefold() == proposer["id"].casefold()):
        return "acceptance-not-independent"
    bound = (("decisionSha256", record.sha256), ("evaluationSha256", d["evaluationSha256"]),
             ("candidateSha256", d["profile"]["candidateSha256"]))
    if set(accept) != {"checker", "verdict"} | {k for k, _ in bound} \
            or any(accept[k] != want for k, want in bound):
        return "acceptance-forged"
    return None if accept["verdict"] == "accepted" else "acceptance-rejected"


def _inputs_ok(policy, record, registration, evaluation, proposer, registry, identity,
               evaluated_at, revoked, conflicts, spent, incident) -> bool:
    return (type(policy) is AutoPolicy and type(record) is PromotionDecision
            and type(registration) is Registration and type(evaluation) is EvaluationRecord
            and type(registry) is ProfileRegistry
            and type(proposer) is dict and set(proposer) == {"kind", "id"}
            and proposer["kind"] == "proposer" and _id(proposer["id"])
            and type(identity) is dict and set(identity) == set(_IDENTITY_KEYS)
            and all(_hash(v) if k.endswith("Sha256") else _id(v) for k, v in identity.items())
            and _int(evaluated_at) and type(incident) is bool and _int(spent, 0, 1 << 62)
            and _ids(revoked, _hash) and _ids(conflicts, _hash))


def assess(policy: AutoPolicy, record: PromotionDecision, *, registration: Registration,
           evaluation: EvaluationRecord, base_files: Any, candidate_files: Any, proposer: Any,
           acceptance: Any, registry: ProfileRegistry, identity: Any, evaluated_at: Any,
           revoked: Any = None, conflicts: Any = None, spent: Any = None,
           incident: Any = None) -> Assessment:
    """First failing rule as an abstention; otherwise an eligible proposal that grants nothing."""
    try:
        policy = build_policy(policy.data) if type(policy) is AutoPolicy else None
    except AutoPromotionError:
        policy = None
    pid = policy.sha256 if policy else ""

    def no(reason: str, rule: int = 0) -> Assessment:
        try:
            sha = record.sha256 if type(record) is PromotionDecision else None
        except (TypeError, ValueError, RecursionError):
            sha = None
        return Assessment("abstain", reason, rule, sha, pid)

    if policy is None or not _inputs_ok(policy, record, registration, evaluation, proposer, registry, identity,
                      evaluated_at, revoked, conflicts, spent, incident):
        return no("invalid-input")
    try:
        d = record.to_dict()
        p, cfg = d["profile"], policy.data
        reproduced = _rebuilt(record, registration, evaluation)
    except (KeyError, TypeError, AttributeError, ValueError, RecursionError):
        return no("record-not-reproducible")  # a hand-built mapping is not a decision record
    if not reproduced:
        return no("record-not-reproducible")
    derived = derive_candidate(base_files, candidate_files)
    if derived is None:
        return no("invalid-input")
    arms = registration.to_dict()["arms"]
    if digest(thaw(base_files)) != arms["A"]["candidateSha256"] \
            or digest(thaw(candidate_files)) != p["candidateSha256"]:
        return no("candidate-not-bound")
    if evaluated_at > d["decidedAt"]:
        return no("invalid-input")
    cited = _cited(d)
    checks = (
        (d["decision"] == "pending"),
        (cfg["fixedAt"] < evaluated_at),
        (derived["changeClass"] == cfg["changeClass"]),
        (bool(derived["layersChanged"]) and set(derived["layersChanged"]) <= set(cfg["allowedLayers"])),
        (derived["scope"] == cfg["scope"] and p["scope"] == registry.scope),
        (set(p["effects"]) <= set(cfg["effects"])),
        (d["cohort"] in cfg["cohorts"] and p["cohort"] == d["cohort"]),
        (all(identity[k] == v for k, v in p["identity"].items())),
        (not cited & (set(revoked) | registry.revoked)),
        (not conflicts),
        (bool(d["regression"]) and all(v == "noninferior" for v in d["regression"].values())),
        (set(d["pendingEndpoints"]) <= set(cfg["tolerablePendingEndpoints"])),
        (set(d["safety"].values()) == {0}),
        (not incident),
        (spent <= cfg["budgetCap"]),
    )
    for rule, ok in enumerate(checks, 1):
        if not ok:
            return no(RULES[rule - 1], rule)
    reason = _acceptance(acceptance, record, d, proposer)
    if reason is not None:
        return no(reason, 16)
    return Assessment("eligible-proposal", None, None, record.sha256, pid)


# --- canary and stops ---------------------------------------------------------------


def canary_status(limits: Mapping[str, int], observations: tuple | list) -> str:
    """Replay canary observations ('ok'/'fail'/'violation'); anything else halts."""
    failures = 0
    for i, seen in enumerate(observations, 1):
        if type(seen) is str and seen == "violation":
            return "halted:safety-violation"
        if type(seen) is not str or seen not in ("ok", "fail"):
            return "halted:unknown-observation"
        failures += seen == "fail"
        if failures > limits["maxFailures"]:
            return "halted:failure-budget"
        if i > limits["size"]:
            return "halted:overrun"
    return "complete" if len(observations) == limits["size"] else "running"


@dataclass(frozen=True)
class Step:
    """One transition: the new run, the registry after any rollback, and a visible failure."""

    run: "PolicyRun"
    registry: ProfileRegistry | None
    registryFailure: str | None = None


@dataclass(frozen=True)
class PolicyRun:
    """Immutable run of one policy over at most one pending candidate; starts ``disabled``."""

    policy: AutoPolicy
    state: str = "disabled"
    decisionSha256: str | None = None
    identity: tuple = ()
    cited: frozenset = frozenset()
    observations: tuple = ()
    journal: tuple = ()

    def __post_init__(self):
        # "active" is vocabulary only: no constructor argument can reach it.
        _require(type(self.policy) is AutoPolicy and self.state in STATES
                 and self.state != "active", "invalid-state")

    @property
    def executionAuthorization(self) -> bool:
        return False

    @property
    def canary(self) -> str | None:
        if self.state != "canary":
            return None
        return canary_status(self.policy.data["canary"], self.observations)

    def _at(self, at: Any) -> int:
        _require(_int(at) and (not self.journal or at >= self.journal[-1]["at"]), "invalid-time")
        return at

    def _next(self, event: str, at: int, reason: str | None, **changes) -> "PolicyRun":
        entry = {"seq": len(self.journal), "event": event, "at": at, "reason": reason}
        return replace(self, journal=(*self.journal, entry), **changes)

    def enable(self, operator: Any, *, at: int) -> "PolicyRun":
        """``disabled`` -> ``shadow`` (assessments only); a human operator, never a policy."""
        at = self._at(at)
        _require(type(operator) is dict and set(operator) == {"kind", "id"}
                 and operator["kind"] in ("human", "automatic-policy") and _id(operator["id"]))
        _require(operator["kind"] == "human", "automatic-promotion-disabled")
        _require(self.state == "disabled", "policy-stopped" if self.state == "stopped"
                 else "not-disabled")
        return self._next("enabled", at, None, state="shadow")

    def begin_canary(self, record: PromotionDecision, *, at: int, **inputs) -> "PolicyRun":
        """``shadow`` -> ``canary`` only if a fresh ``assess`` over ``inputs`` is eligible."""
        at = self._at(at)
        _require(self.state == "shadow", "not-shadow")
        try:
            got = assess(self.policy, record, **inputs)
        except TypeError:  # missing, unknown or duplicated keyword
            raise AutoPromotionError("invalid-input") from None
        _require(got.eligible, got.reason or "invalid-input")
        d = record.to_dict()
        cited = _cited(d)
        identity = tuple(sorted(d["profile"]["identity"].items()))
        return self._next("canary-begun", at, None, state="canary", decisionSha256=record.sha256,
                          identity=identity, cited=cited)

    def activate(self) -> "PolicyRun":
        """Always refused: activation needs a separately adopted policy and operator decision."""
        raise AutoPromotionError("activation-requires-adoption")

    def observe(self, seen: Any, *, current: Any, at: int,
                registry: ProfileRegistry | None = None) -> Step:
        """Record one canary observation; drift, violation, overrun or unknown halts."""
        _require(self.state == "canary", "not-canary")
        if not (_int(at) and at >= self.journal[-1]["at"]) or type(current) is not dict \
                or not all(type(v) is str for v in current.values()) \
                or current != dict(self.identity):
            return self.stop("drift", at=at, registry=registry)
        run = self._next("observed", at, None, observations=(
            *self.observations, seen if type(seen) is str else "invalid"))
        if run.canary.startswith("halted"):
            return run.stop("canary", at=at, registry=registry)
        return Step(run, registry)

    def stop(self, trigger: str, *, at: int, registry: ProfileRegistry | None = None,
             evidence: Any = None) -> Step:
        """Stop fail closed and apply the registry rollback or revocation; failures are visible.

        An unknown trigger is refused without a transition. A revocation stops this run only
        when the revoked hash is cited by its candidate; the registry is still revoked.
        """
        _require(trigger in (*STOP_REASONS, "revocation"), "invalid-trigger")
        _require(trigger != "revocation" or _hash(evidence), "invalid-evidence")
        reason = "lesson-revoked" if trigger == "revocation" else STOP_REASONS[trigger]
        failure = None
        try:
            at = self._at(at)
        except AutoPromotionError:  # a stop must still halt: keep the run clock, skip the registry
            at, failure, registry = (self.journal[-1]["at"] if self.journal else 0), "invalid-time", None
        if registry is not None and type(registry) is not ProfileRegistry:
            registry, failure = None, "invalid-registry"
        if registry is not None:
            try:
                registry = (registry.revoke_evidence(evidence, at=at, reason=reason)
                            if trigger == "revocation" else registry.rollback(at=at, reason=reason))
            except PromotionError as exc:
                failure = exc.reason
        if self.state == "stopped" or (trigger == "revocation" and evidence not in self.cited):
            return Step(self, registry, failure)
        return Step(self._next("stopped", at, reason, state="stopped"), registry, failure)
