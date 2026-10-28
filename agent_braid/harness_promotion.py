# SPDX-License-Identifier: AGPL-3.0-only
"""Reversible task-local profile registry and human promotion transaction; offline, no authority.

``decide`` builds a candidate-bound approved/rejected/pending record from a T003
registration and report. It binds the exact arm-C candidate, a task-local scope, the
effect domain (cohort and declared effects), the source/host/model/tool/policy
identity, the evaluation, cost report and extra evidence hashes, the per-stratum
C-vs-A regression verdicts and the rollback target. Only a human actor may decide:
automatic promotion is disabled (``AUTOMATIC_PROMOTION``) and an automatic-policy
actor is refused for every outcome. Approval further requires the profile cohort to
match the evaluated cohort (synthetic evidence never approves a native profile), every
stratum's C-vs-A noninferiority to be assessed and met, and zero unsafe admissions,
authority violations and effect violations; an unknown count blocks like a violation.

``ProfileRegistry`` is one scope's immutable registry; every operation returns a new
value. Its state (active profile, prior profiles, pending transaction, revoked
evidence) is derived only by replaying its append-only journal, so a decoded registry
is checked by the same rules that produced it. Activation is a two-step transaction:
``begin`` records an approved decision whose rollback target is the current profile
and ``commit`` makes it active; a registry persisted between the two is an interrupted
promotion that keeps the prior profile until ``abort``. Both steps refuse a drifted
source/host/model/tool/policy identity, and ``resolve`` reports drift on read instead
of serving the profile; it also refuses a task of another cohort, so a synthetic-cohort
profile is never served to a native task. ``rollback`` restores the prior profile; revoking evidence
withdraws every pending or active decision that cites it, falling back to the newest
prior profile whose evidence is still valid. A rolled-back decision is withdrawn and
cannot be begun again; restoring that profile needs a new human decision. A commit is
refused when a rollback or revocation changed the active profile after ``begin``.

``save`` replaces the registry file atomically under an exclusive lock and refuses any
write whose journal does not extend the stored one, so a concurrent update is never
lost; the lock file stays beside the registry and the locking is POSIX-only. Records prove
binding, not authenticity: the human actor, profile identity, declared effects, safety
counts and extra evidence are self-asserted and must be checked by the caller against
trusted records. The T003 endpoints still pending are copied into the decision as
remaining limits; a human may approve a profile narrowed to the evidence that exists.
The caller supplies ticks and the current identity; nothing here reads a clock, host
or model. ``executionAuthorization`` is always false: an active profile is advisory
configuration, not a grant, and synthetic decisions never authorize native activation.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import fcntl
from hashlib import sha256
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Any

from .harness_evaluation import REGISTRATION_FORMAT, REPORT_FORMAT, EvaluationRecord, Registration
from .system_one import InvalidDecision, MAX_BYTES, canonical, digest, freeze, parse_json, thaw

DECISION_FORMAT = "braid-harness-promotion-decision/v0.1"
REGISTRY_FORMAT = "braid-harness-profile-registry/v0.1"
AUTOMATIC_PROMOTION = False  # REQ-007: no automatic transition has been adopted
DECISIONS = ("approved", "rejected", "pending")
COHORTS = ("synthetic", "native")
REGRESSION = ("noninferior", "not-demonstrated", "descriptive-only")
# Identity field -> refusal reason when the current value differs from the decided one.
IDENTITY = (("sourceSha256", "stale-source"), ("host", "stale-host"), ("model", "stale-model"),
            ("toolSetSha256", "stale-tool"), ("policySha256", "stale-policy"))
SAFETY = (("unsafeAdmissions", "unsafe-admission"), ("authorityViolations", "authority-violation"),
          ("effectViolations", "effect-violation"))
MAX_LIST = 16
MAX_DECISIONS = 64
MAX_JOURNAL = 256
MAX_TICK = 1 << 40
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_PROFILE_KEYS = {"candidateSha256", "scope", "cohort", "effects", "identity"}
_DECISION_KEYS = {"format", "actor", "decision", "profile", "profileSha256", "registrationSha256",
                  "evaluationSha256", "costReportSha256", "cohort", "regression", "pendingEndpoints",
                  "safety", "evidenceSha256s", "rollbackTargetSha256", "limits", "decidedAt",
                  "executionAuthorization"}
_EVENTS = ("recorded", "begun", "committed", "aborted", "rolled-back", "evidence-revoked")
_REASONED = frozenset({"aborted", "rolled-back", "evidence-revoked"})


class PromotionError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-decision"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-decision") -> None:
    if not condition:
        raise PromotionError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _tick(value: Any) -> bool:
    return type(value) is int and 0 <= value < MAX_TICK


def _exact(value: Any, keys: set[str], reason: str) -> None:
    _require(type(value) is dict and set(value) == keys, reason)


def _sorted_ids(value: Any, check) -> bool:
    return (type(value) is list and len(value) <= MAX_LIST and all(map(check, value))
            and value == sorted(set(value)))


def _plain(value: Any, reason: str) -> Any:
    try:
        return thaw(value)
    except RecursionError:
        raise PromotionError(reason) from None


def _check_identity(value: Any, reason: str) -> None:
    _exact(value, {key for key, _ in IDENTITY}, reason)
    _require(all(_hash(value[k]) if k.endswith("Sha256") else _id(value[k]) for k, _ in IDENTITY),
             reason)


def _fresh(identity: Mapping, current: Any) -> None:
    _check_identity(current, "invalid-identity")
    for key, reason in IDENTITY:
        _require(identity[key] == current[key], reason)


def _check_profile(p: Any) -> None:
    _exact(p, _PROFILE_KEYS, "invalid-profile")
    _require(_hash(p["candidateSha256"]) and _id(p["scope"]) and p["cohort"] in COHORTS
             and _sorted_ids(p["effects"], _id) and p["effects"], "invalid-profile")
    _check_identity(p["identity"], "invalid-profile")


def _check_decision(d: Any) -> None:
    """Shape of any decision plus the approval gates of an approved one."""
    _exact(d, _DECISION_KEYS, "invalid-decision")
    actor = d["actor"]
    _exact(actor, {"kind", "id"}, "invalid-decision")
    _require(actor["kind"] in ("human", "automatic-policy") and _id(actor["id"]))
    _require(AUTOMATIC_PROMOTION or actor["kind"] == "human", "automatic-promotion-disabled")
    _require(d["format"] == DECISION_FORMAT and d["executionAuthorization"] is False
             and d["decision"] in DECISIONS and d["cohort"] in COHORTS and _tick(d["decidedAt"])
             and all(_hash(d[k]) for k in ("registrationSha256", "evaluationSha256",
                                           "costReportSha256"))
             and (d["rollbackTargetSha256"] is None or _hash(d["rollbackTargetSha256"]))
             and _sorted_ids(d["evidenceSha256s"], _hash) and _sorted_ids(d["limits"], _id)
             and type(d["pendingEndpoints"]) is list and len(d["pendingEndpoints"]) <= MAX_LIST
             and all(map(_id, d["pendingEndpoints"])))
    regression = d["regression"]
    _require(type(regression) is dict and 0 < len(regression) <= MAX_LIST
             and all(_id(k) and v in REGRESSION for k, v in regression.items()))
    safety = d["safety"]
    _exact(safety, {key for key, _ in SAFETY}, "invalid-decision")
    _require(all(v is None or _tick(v) for v in safety.values()))
    _check_profile(d["profile"])
    _require(d["profileSha256"] == digest(d["profile"]))
    if d["decision"] != "approved":
        return
    _require(d["profile"]["cohort"] == d["cohort"], "cohort-mismatch")
    _require(all(v == "noninferior" for v in regression.values()), "regression-not-covered")
    for key, reason in SAFETY:
        _require(safety[key] is not None, "safety-unknown")
        _require(safety[key] == 0, reason)


def _cited(d: Mapping) -> set[str]:
    return {d["registrationSha256"], d["evaluationSha256"], d["costReportSha256"],
            *d["evidenceSha256s"]}


@dataclass(frozen=True)
class PromotionDecision:
    """Immutable validated decision; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]

    @property
    def sha256(self) -> str:
        return digest(self.data)

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


def _verified(record: Any, cls: type, fmt: str) -> dict:
    """Data of an evaluation record whose bytes still match and whose format is ``fmt``."""
    _require(type(record) is cls and canonical(record.data) == record.canonical_bytes,
             "invalid-evaluation")
    data = record.to_dict()
    _require(data.get("format") == fmt, "invalid-evaluation")
    return data


def decide(registration: Registration, evaluation: EvaluationRecord, *, profile: Any, actor: Any,
           decision: str, safety: Any, evidence: Any = (), rollback_target: str | None = None,
           limits: Any = (), at: int) -> PromotionDecision:
    """Record one human decision about the evaluated arm-C candidate in ``profile``."""
    reg = _verified(registration, Registration, REGISTRATION_FORMAT)
    report = _verified(evaluation, EvaluationRecord, REPORT_FORMAT)
    _require(report["registrationSha256"] == registration.sha256, "registration-mismatch")
    _require(not reg["refinement"]["armCIsBase"], "no-candidate")
    profile = _plain(profile, "invalid-profile")
    _check_profile(profile)
    _require(profile["candidateSha256"] == reg["arms"]["C"]["candidateSha256"], "candidate-mismatch")
    regression = {}
    for stratum, summary in report["strata"].items():
        check = summary["comparisons"]["C-vs-A"]["noninferiority"]
        regression[stratum] = check["verdict"] if check["status"] == "assessed" else "descriptive-only"
    d = {"format": DECISION_FORMAT, "actor": _plain(actor, "invalid-decision"), "decision": decision,
         "profile": profile, "profileSha256": digest(profile),
         "registrationSha256": registration.sha256, "evaluationSha256": evaluation.sha256,
         "costReportSha256": report["costReportSha256"], "cohort": report["cohort"],
         "regression": regression, "pendingEndpoints": report["pendingEndpoints"],
         "safety": _plain(safety, "invalid-decision"),
         "evidenceSha256s": _plain(evidence, "invalid-decision"),
         "rollbackTargetSha256": rollback_target,
         "limits": _plain(limits, "invalid-decision"),
         "decidedAt": at, "executionAuthorization": False}
    _check_decision(d)
    return PromotionDecision(freeze(d))


# --- registry -----------------------------------------------------------------------


@dataclass(frozen=True)
class Resolution:
    """The profile a task in ``scope`` may use now, or why none is served."""

    profile: dict | None
    decisionSha256: str | None
    reason: str | None

    @property
    def executionAuthorization(self) -> bool:
        return False


@dataclass(frozen=True)
class _State:
    active: str | None
    previous: tuple[str, ...]
    pending: str | None
    revoked: frozenset[str]


def _restore(previous: list[str], decisions: Mapping[str, Mapping], revoked: set[str]) -> str | None:
    """Newest prior decision whose evidence is still valid; revoked ones are dropped."""
    while previous:
        candidate = previous.pop()
        if not _cited(decisions[candidate]) & revoked:
            return candidate
    return None


def _replay(scope: str, decisions: Mapping[str, Mapping], journal: list) -> _State:
    """Derive the registry state from its journal, refusing any invalid transition."""

    def _target(active: str | None) -> str | None:
        return decisions[active]["profileSha256"] if active else None

    active, previous, pending, revoked, withdrawn, last = None, [], None, set(), set(), 0
    known: set[str] = set()
    for index, e in enumerate(journal):
        _exact(e, {"seq", "event", "subject", "at", "reason"}, "invalid-journal")
        name = e["event"]
        _require(type(e["seq"]) is int and e["seq"] == index and name in _EVENTS and _hash(e["subject"]) and _tick(e["at"])
                 and e["at"] >= last
                 and (_id(e["reason"]) if name in _REASONED else e["reason"] is None),
                 "invalid-journal")
        subject, last = e["subject"], e["at"]
        if name == "evidence-revoked":
            _require(subject not in revoked, "already-revoked")
            revoked.add(subject)
            if pending and subject in _cited(decisions[pending]):
                pending = None
            if active and subject in _cited(decisions[active]):
                active = _restore(previous, decisions, revoked)
            continue
        d = decisions.get(subject)
        _require(d is not None, "invalid-journal")
        if name == "recorded":
            _require(subject not in known, "duplicate-decision")
        known.add(subject)
        if name == "begun":
            _require(pending is None, "transaction-in-progress")
            _require(d["decision"] == "approved", "decision-not-approved")
            _require(d["profile"]["scope"] == scope, "scope-mismatch")
            _require(not _cited(d) & revoked, "revoked-evidence")
            _require(subject not in withdrawn, "decision-withdrawn")
            _require(d["rollbackTargetSha256"] == _target(active), "rollback-target-mismatch")
            _require(e["at"] >= d["decidedAt"], "decision-time-mismatch")
            pending = subject
        elif name in ("committed", "aborted"):
            _require(subject == pending, "no-transaction")
            if name == "committed":
                # A rollback or revocation while pending changes the profile the human
                # named as rollback target; the transaction must then be aborted.
                _require(d["rollbackTargetSha256"] == _target(active), "rollback-target-mismatch")
                if active:
                    previous.append(active)
                active = subject
            pending = None
        elif name == "rolled-back":
            _require(subject == active, "no-active-profile")
            withdrawn.add(subject)  # re-activation needs a new human decision
            active = _restore(previous, decisions, revoked)
    return _State(active, tuple(previous), pending, frozenset(revoked))


class ProfileRegistry:
    """Immutable journaled registry of one task-local scope; every operation returns a new one."""

    def __init__(self, scope: str, decisions: Mapping[str, Any], journal: Any):
        _require(_id(scope), "invalid-registry")
        decisions, journal = _plain(decisions, "invalid-registry"), _plain(journal, "invalid-registry")
        _require(type(decisions) is dict and len(decisions) <= MAX_DECISIONS
                 and type(journal) is list and len(journal) <= MAX_JOURNAL, "invalid-registry")
        for key, d in decisions.items():
            _require(_hash(key) and type(d) is dict, "invalid-registry")
            try:
                matches = key == digest(d)
            except (TypeError, ValueError, RecursionError):
                raise PromotionError("invalid-decision") from None
            _require(matches, "decision-hash-mismatch")
            _check_decision(d)
        self._state = _replay(scope, decisions, journal)
        _require(set(decisions) <= {e["subject"] for e in journal}, "invalid-registry")
        self._scope, self._decisions, self._journal = scope, freeze(decisions), freeze(journal)

    @classmethod
    def empty(cls, scope: str) -> "ProfileRegistry":
        return cls(scope, {}, [])

    @property
    def scope(self) -> str:
        return self._scope

    @property
    def decisions(self) -> Mapping[str, Mapping]:
        return self._decisions

    @property
    def journal(self) -> tuple[Mapping[str, Any], ...]:
        return self._journal

    @property
    def pending(self) -> str | None:
        return self._state.pending

    @property
    def previous(self) -> tuple[str, ...]:
        return self._state.previous

    def _append(self, event: str, subject: str, at: int, reason: str | None = None,
                decision: PromotionDecision | None = None) -> "ProfileRegistry":
        _require(_tick(at), "invalid-time")
        _require(not self._journal or at >= self._journal[-1]["at"], "time-regression")
        _require(len(self._journal) < MAX_JOURNAL, "journal-full")
        _require(_id(reason) if event in _REASONED else reason is None, "invalid-reason")
        decisions = thaw(self._decisions)
        if decision is not None:  # revalidated, with the rest, by the constructor
            decisions[decision.sha256] = decision.to_dict()
        journal = thaw(self._journal) + [{"seq": len(self._journal), "event": event,
                                         "subject": subject, "at": at, "reason": reason}]
        return ProfileRegistry(self._scope, decisions, journal)

    @staticmethod
    def _decision(decision: Any) -> PromotionDecision:
        _require(type(decision) is PromotionDecision, "invalid-decision")
        _check_decision(_plain(decision.data, "invalid-decision"))
        return decision

    def record(self, decision: PromotionDecision, at: int) -> "ProfileRegistry":
        """Audit any decision, including rejected or pending ones, without activating it."""
        decision = self._decision(decision)
        _require(decision.sha256 not in self._decisions, "duplicate-decision")
        return self._append("recorded", decision.sha256, at, decision=decision)

    def begin(self, decision: PromotionDecision, *, current: Any, at: int) -> "ProfileRegistry":
        """Start activating an approved decision against the current identity."""
        decision = self._decision(decision)
        _fresh(decision.data["profile"]["identity"], current)
        _require(_tick(at), "invalid-time")
        _require(decision.data["decidedAt"] <= at, "decision-time-mismatch")
        return self._append("begun", decision.sha256, at, decision=decision)

    def commit(self, *, current: Any, at: int) -> "ProfileRegistry":
        """Atomically make the pending decision active if its identity is still current."""
        pending = self._state.pending
        _require(pending is not None, "no-transaction")
        _fresh(self._decisions[pending]["profile"]["identity"], current)
        return self._append("committed", pending, at)

    def abort(self, *, at: int, reason: str) -> "ProfileRegistry":
        """Drop a pending (for example interrupted) transaction; the active profile is kept."""
        _require(self._state.pending is not None, "no-transaction")
        return self._append("aborted", self._state.pending, at, reason)

    def rollback(self, *, at: int, reason: str) -> "ProfileRegistry":
        """Withdraw the active profile and restore the newest prior usable one."""
        _require(self._state.active is not None, "no-active-profile")
        return self._append("rolled-back", self._state.active, at, reason)

    def revoke_evidence(self, evidence_sha256: str, *, at: int, reason: str) -> "ProfileRegistry":
        """Withdraw every pending or active decision citing this evidence; terminal."""
        _require(_hash(evidence_sha256), "invalid-evidence")
        _require(evidence_sha256 not in self._state.revoked, "already-revoked")
        return self._append("evidence-revoked", evidence_sha256, at, reason)

    def resolve(self, current: Any, *, cohort: str) -> Resolution:
        """The active profile if its cohort and identity match the task; otherwise the reason."""
        _check_identity(current, "invalid-identity")
        _require(cohort in COHORTS, "invalid-identity")
        active = self._state.active
        if active is None:
            return Resolution(None, None, "no-active-profile")
        profile = self._decisions[active]["profile"]
        if profile["cohort"] != cohort:
            return Resolution(None, active, "cohort-mismatch")
        try:
            _fresh(profile["identity"], current)
        except PromotionError as exc:
            return Resolution(None, active, exc.reason)
        return Resolution(thaw(profile), active, None)

    # --- codec -----------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        return canonical({"format": REGISTRY_FORMAT, "scope": self._scope,
                          "decisions": self._decisions, "journal": self._journal})

    @property
    def sha256(self) -> str:
        return sha256(self.to_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProfileRegistry":
        """Accept only the exact canonical bytes ``to_bytes`` would produce."""
        try:
            value = parse_json(raw)
        except InvalidDecision:
            raise PromotionError("invalid-json") from None
        _exact(value, {"format", "scope", "decisions", "journal"}, "invalid-registry")
        _require(value["format"] == REGISTRY_FORMAT, "invalid-registry")
        registry = cls(value["scope"], value["decisions"], value["journal"])
        _require(registry.to_bytes() == raw, "non-canonical")
        return registry


# --- persistence --------------------------------------------------------------------


def load(path: Path) -> ProfileRegistry:
    """Read a regular, non-linked registry file; a FIFO or directory is refused, not opened."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise PromotionError("registry-unavailable") from None
    try:
        with os.fdopen(fd, "rb") as handle:
            _require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "registry-unavailable")
            raw = handle.read(MAX_BYTES + 1)
    except OSError:
        raise PromotionError("registry-unavailable") from None
    return ProfileRegistry.from_bytes(raw)


def save(path: Path, registry: ProfileRegistry) -> None:
    """Atomically replace ``path`` unless the stored journal is not a prefix of the new one."""
    _require(type(registry) is ProfileRegistry, "invalid-registry")
    path = Path(path)
    try:
        lock = os.open(path.with_name(path.name + ".lock"),
                       os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise PromotionError("registry-unavailable") from None
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(path):
            stored = load(path)
            _require(stored.scope == registry.scope
                     and registry.journal[:len(stored.journal)] == stored.journal,
                     "concurrent-update")
        temp = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        except OSError:
            raise PromotionError("registry-unavailable") from None
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(registry.to_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            temp.unlink(missing_ok=True)
            raise PromotionError("registry-unavailable") from None
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    finally:
        os.close(lock)
