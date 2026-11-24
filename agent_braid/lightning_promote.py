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
import difflib
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import time
from typing import Any

from . import harness_promotion as promotion
from . import lightning_store as store
from . import plugin_registry
from .harness_evaluation import REGISTRATION_FORMAT, REPORT_FORMAT, EvaluationRecord, Registration
from .system_one import InvalidDecision, canonical, freeze, parse_json

COHORT = "native"
EFFECTS = ("skill-text",)
SUPPORTED = "supported"
NO_SUPPORT = "no-held-out-support"
PREVIEW_SCHEMA = "braid-lightning-promotion-preview/v0.1"
OVERRIDE_LIMIT = "owner-override-no-held-out-support"
# A scope's first decision names its baseline digest in a limit id (SPEC-049 ids hold at most
# 64 characters, so the id carries a 176-bit prefix that selects one cited evidence digest).
BASELINE_LIMIT = "lightning-baseline:"
BASELINE_PREFIX = 44
MAX_REASON = 512
MAX_TARGET = 64 * 1024


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
        self.reason = self.code = reason
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
    run: store.RunStore

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
                           support, profile, run)


# --- preview (REQ-003) ----------------------------------------------------------------


def registry_path(home: Path | None, scope: str) -> Path:
    """The working registry of ``scope`` in the private plugin home (OD-3)."""
    return plugin_registry.home_path(home) / "lightning-promotion" / scope_entry(scope).registry


def _hex(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def read_registry(home: Path | None, scope: str) -> tuple[promotion.ProfileRegistry, bytes]:
    """The scope's registry and its stored bytes; an absent file is the empty registry and ``b""``."""
    path = registry_path(home, scope)
    if not os.path.lexists(path):
        return promotion.ProfileRegistry.empty(scope), b""
    try:
        value = promotion.load(path)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None
    _require(value.scope == scope, "scope-mismatch")
    return value, value.to_bytes()


def read_target(root: Path, scope: str) -> bytes:
    """Bytes of the mapped file: a regular, non-linked file inside ``root``."""
    path = Path(root) / scope_entry(scope).target
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        raise PromoteError("target-unavailable") from None
    with os.fdopen(fd, "rb") as handle:
        _require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode), "target-unavailable")
        raw = handle.read(MAX_TARGET + 1)
    _require(len(raw) <= MAX_TARGET, "target-unavailable")
    return raw


def active_candidate(value: promotion.ProfileRegistry) -> str | None:
    active = value.active
    return value.decisions[active]["profile"]["candidateSha256"] if active else None


def check_reason(reason: Any) -> str | None:
    """An owner override reason: one line of at most 512 printable characters, or None."""
    if reason is None:
        return None
    _require(type(reason) is str and reason.strip() and len(reason) <= MAX_REASON
             and reason.isprintable(), "invalid-override-reason")
    return reason


def _diff(before: bytes, after: bytes) -> dict:
    old = before.decode("utf-8", "replace").splitlines()
    new = after.decode("utf-8", "replace").splitlines()
    added = removed = 0
    for line in difflib.ndiff(old, new):
        added += line.startswith("+ ")
        removed += line.startswith("- ")
    return {"added": added, "removed": removed}


def regression_covered(evaluation: EvaluationRecord) -> bool:
    """True when every stratum's C-vs-A noninferiority is assessed and met (``decide()`` gate, OD-4)."""
    strata = evaluation.to_dict().get("strata") or {}
    return bool(strata) and all(
        (s.get("comparisons", {}).get("C-vs-A", {}).get("noninferiority") or {}).get("status") == "assessed"
        and s["comparisons"]["C-vs-A"]["noninferiority"].get("verdict") == "noninferior"
        for s in strata.values())


def seal(document: dict) -> dict:
    """Add ``previewDigest`` (SHA-256 of the canonical fields) and ``executionAuthorization``."""
    body = {k: v for k, v in document.items() if k not in ("previewDigest", "executionAuthorization")}
    return {**body, "previewDigest": _hex(canonical(body)), "executionAuthorization": False}


def preview_promote(record: CandidateRecord, *, home: Path | None, root: Path,
                    override_reason: str | None = None) -> dict:
    """The promotion preview of ``record``; reads the registry and the target, writes nothing."""
    _require(type(record) is CandidateRecord, "invalid-record")
    reason = check_reason(override_reason)
    value, raw = read_registry(home, record.scope)
    before = read_target(root, record.scope)
    evidence = set(record.evidence)
    if not value.decisions:
        # A scope's first decision cites the file it replaces: the baseline the build check
        # requires while no candidate is active, restored when none remains.
        evidence.add(_hex(before))
    if reason is not None:
        evidence.add(_hex(reason.encode("utf-8")))
    blockers = []
    if not regression_covered(record.evaluation):
        blockers.append("regression-not-covered")
    if record.heldOutSupport == NO_SUPPORT and reason is None:
        blockers.append(NO_SUPPORT)
    if value.pending is not None:
        blockers.append("transaction-in-progress")
    if active_candidate(value) == record.candidateSha256:
        blockers.append("already-active")
    return seal({
        "schema": PREVIEW_SCHEMA, "action": "promote", "scope": record.scope,
        "targetPath": record.target, "currentSha256": active_candidate(value),
        "candidateSha256": record.candidateSha256, "fileSha256Before": _hex(before),
        "registrySha256Before": _hex(raw), "cohort": COHORT, "evidence": sorted(evidence),
        "heldOutSupport": record.heldOutSupport, "overrideReason": reason,
        "diffSummary": _diff(before, record.text.encode("utf-8")),
        "blockers": sorted(blockers), "requiredDecision": "approved"})


# --- apply (REQ-002, REQ-003) ----------------------------------------------------------


def _private_dirs(home: Path | None) -> None:
    for directory in (plugin_registry.home_path(home), plugin_registry.home_path(home) / "lightning-promotion"):
        try:
            store._private_dir(directory)
        except (store.StoreError, OSError):
            raise PromoteError("registry-unavailable") from None


def write_target(root: Path, scope: str, raw: bytes) -> None:
    """Replace the mapped file atomically: same-directory temp file with the file's mode,
    fsync, rename, directory fsync. Any OS failure is ``target-write-failed``."""
    path = Path(root) / scope_entry(scope).target
    temp = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
    try:
        mode = stat.S_IMODE(os.lstat(path).st_mode)
    except OSError:
        mode = 0o644
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp, mode)
            os.replace(temp, path)
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except OSError:
        raise PromoteError("target-write-failed") from None


def _keep_text(run: store.RunStore, raw: bytes) -> None:
    """Keep a text content-addressed in the run store (a baseline or an override reason)."""
    try:
        run.write_candidate_text(_hex(raw), raw.decode("utf-8"))
    except (store.StoreError, UnicodeDecodeError):
        raise PromoteError("text-not-storable") from None


def baseline_limit(digest: str) -> str:
    return BASELINE_LIMIT + digest[:BASELINE_PREFIX]


def baseline_digest(value: promotion.ProfileRegistry) -> str | None:
    """The baseline file digest the scope's first decision names; None before any decision.

    Only the digest its ``lightning-baseline:`` limit selects counts: the same decision may
    also cite an override reason's digest, which is never a baseline.
    """
    if not value.journal:
        return None
    first = value.decisions[value.journal[0]["subject"]]
    marks = [limit[len(BASELINE_LIMIT):] for limit in first["limits"] if limit.startswith(BASELINE_LIMIT)]
    _require(len(marks) == 1, "baseline-unknown")
    found = [d for d in first["evidenceSha256s"] if d.startswith(marks[0])]
    _require(len(found) == 1, "baseline-unknown")
    return found[0]


def _save(home: Path | None, value: promotion.ProfileRegistry) -> None:
    try:
        promotion.save(registry_path(home, value.scope), value)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None


def _target_sha(value: promotion.ProfileRegistry) -> str | None:
    return value.decisions[value.active]["profileSha256"] if value.active else None


def _checked(document: dict, preview_digest: Any) -> None:
    """The recomputed preview must equal the one the human read, and carry no blocker."""
    _require(type(preview_digest) is str and document["previewDigest"] == preview_digest, "preview-stale")
    if document.get("blockers"):
        raise PromoteError(document["blockers"][0])


def _unchanged(document: dict, home: Path | None, root: Path, scope: str):
    """Re-read registry and file right before writing; both must still be the previewed bytes."""
    value, raw = read_registry(home, scope)
    before = read_target(root, scope)
    _require(_hex(raw) == document["registrySha256Before"]
             and _hex(before) == document["fileSha256Before"], "preview-stale")
    return value, before


def apply_promote(record: CandidateRecord, *, home: Path | None, root: Path, preview_digest: str,
                  actor: Any, safety: Any, at: int, current: Any = None,
                  override_reason: str | None = None) -> dict:
    """Human decide, then begin, atomic file write and commit; abort and restore on any failure.

    ``current`` is the identity now in force (default: the profile's own); ``begin`` and
    ``commit`` refuse a drifted one. Writes only the scope's registry file and the mapped
    ``SKILL.md``.
    """
    current = record.profile["identity"] if current is None else current
    document = preview_promote(record, home=home, root=root, override_reason=override_reason)
    _checked(document, preview_digest)
    reason = document["overrideReason"]
    extra = sorted(set(document["evidence"]) - set(record.evidence))
    value, before = _unchanged(document, home, root, record.scope)
    limits = [OVERRIDE_LIMIT] if reason is not None else []
    if not value.decisions:
        limits.append(baseline_limit(_hex(before)))  # names the baseline among the evidence
    try:
        decision = promotion.decide(
            record.registration, record.evaluation, profile=record.profile, actor=actor,
            decision="approved", safety=safety, evidence=extra, rollback_target=_target_sha(value),
            limits=sorted(limits), at=at)
        begun = value.record(decision, at).begin(decision, current=current, at=at)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None
    if not value.decisions:
        _keep_text(record.run, before)  # the baseline, restorable later
    if reason is not None:
        _keep_text(record.run, reason.encode("utf-8"))  # OD-5: the text beside its cited digest
    _private_dirs(home)
    _save(home, begun)
    try:
        write_target(root, record.scope, record.text.encode("utf-8"))
        committed = begun.commit(current=current, at=at)
        _save(home, committed)
    except Exception:
        _abort(home, root, record.scope, begun, before, at)
        raise PromoteError("apply-failed") from None
    return {"status": "committed", "action": "promote", "scope": record.scope,
            "candidateSha256": record.candidateSha256, "decisionSha256": decision.sha256,
            "registrySha256After": committed.sha256,
            "fileSha256After": _hex(read_target(root, record.scope)), "executionAuthorization": False}


def _abort(home, root, scope, begun, before: bytes, at: int) -> None:
    """Restore the file bytes (if they changed) and record ``aborted``; the prior profile is kept.

    The abort is recorded even when the restore fails; a failure of either step is reported
    as ``abort-failed`` and left to ``--abort`` recovery (the build check flags the file)."""
    restored = True
    try:
        if read_target(root, scope) != before:
            write_target(root, scope, before)
    except PromoteError:
        restored = False
    try:
        _save(home, begun.abort(at=at, reason="apply-failed"))
    except (PromoteError, promotion.PromotionError):
        restored = False
    _require(restored, "abort-failed")


# --- recovery from an interrupted promotion ---------------------------------------------


def _restored_text(value: promotion.ProfileRegistry, after: promotion.ProfileRegistry,
                   run: store.RunStore) -> tuple[str, str]:
    """Digest and text the mapped file must hold after a change: the active candidate of
    ``after``, or, when none is active, the baseline cited by the scope's first decision."""
    candidate = active_candidate(after)
    if candidate is not None:
        return candidate, _text(run, candidate)
    digest = baseline_digest(value)
    _require(digest is not None, "candidate-not-stored")
    try:
        return digest, run.candidate_text(digest)
    except store.StoreError:
        raise PromoteError("candidate-not-stored") from None


def preview_abort(scope: str, *, home: Path | None, root: Path, run: store.RunStore,
                  reason: str = "owner-abort", at: int) -> dict:
    """Preview dropping a pending (interrupted) promotion and restoring the active text."""
    value, raw = read_registry(home, scope)
    _require(value.pending is not None, "no-transaction")
    try:
        after = value.abort(at=at, reason=reason)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None
    candidate, text = _restored_text(value, after, run)
    before = read_target(root, scope)
    return seal({
        "schema": PREVIEW_SCHEMA, "action": "abort", "scope": scope,
        "targetPath": scope_entry(scope).target, "currentSha256": active_candidate(value),
        "pendingSha256": value.decisions[value.pending]["profile"]["candidateSha256"],
        "candidateSha256": candidate, "fileSha256Before": _hex(before),
        "registrySha256Before": _hex(raw), "cohort": COHORT, "reason": reason,
        "diffSummary": _diff(before, text.encode("utf-8")), "requiredDecision": "human-apply"})


def apply_abort(scope: str, *, home: Path | None, root: Path, run: store.RunStore,
                preview_digest: str, reason: str = "owner-abort", at: int) -> dict:
    """Restore the active (or baseline) text, then record ``aborted`` for the pending entry."""
    document = preview_abort(scope, home=home, root=root, run=run, reason=reason, at=at)
    _checked(document, preview_digest)
    value, before = _unchanged(document, home, root, scope)
    after = value.abort(at=at, reason=reason)
    _, text = _restored_text(value, after, run)
    write_target(root, scope, text.encode("utf-8"))
    try:
        _save(home, after)
    except PromoteError:
        write_target(root, scope, before)
        raise PromoteError("apply-failed") from None
    return {"status": "aborted", "action": "abort", "scope": scope,
            "activeSha256": active_candidate(after), "registrySha256After": after.sha256,
            "fileSha256After": _hex(read_target(root, scope)), "executionAuthorization": False}


# --- rollback and revocation (REQ-005, REQ-006) ---------------------------------------


def rollback_change(*, at: int, reason: str):
    """The registry change of a rollback: withdraw the active profile, restore the prior one."""
    def change(value: promotion.ProfileRegistry) -> promotion.ProfileRegistry:
        _require(value.active is not None, "no-active-profile")
        after = value.rollback(at=at, reason=reason)
        _require(after.active is not None, "no-previous")
        return after
    change.fields = {"reason": reason}  # sealed into the preview digest
    return change


def _changed(value: promotion.ProfileRegistry, change) -> promotion.ProfileRegistry:
    try:
        return change(value)
    except promotion.PromotionError as exc:
        raise PromoteError(exc.reason) from None


def preview_transition(action: str, scope: str, change, *, home: Path | None, root: Path,
                       run: store.RunStore) -> dict:
    """Preview a rollback or revocation; reads the registry, the target and the run store only."""
    _require(action in ("rollback", "revoke"), "invalid-action")
    value, raw = read_registry(home, scope)
    _require(value.pending is None, "transaction-in-progress")
    after = _changed(value, change)
    candidate, text = _restored_text(value, after, run)
    before = read_target(root, scope)
    cited = after.decisions[after.active] if after.active else None
    evidence = sorted(promotion._cited(cited)) if cited else [candidate]  # the named baseline
    return seal({
        "schema": PREVIEW_SCHEMA, "action": action, "scope": scope,
        "targetPath": scope_entry(scope).target, "currentSha256": active_candidate(value),
        "candidateSha256": candidate, "fileSha256Before": _hex(before),
        "registrySha256Before": _hex(raw), "cohort": COHORT, "evidence": evidence,
        "heldOutSupport": None, "overrideReason": None,
        "diffSummary": _diff(before, text.encode("utf-8")), "blockers": [],
        "requiredDecision": "human-apply", **change.fields})


def apply_transition(action: str, scope: str, change, *, home: Path | None, root: Path,
                     run: store.RunStore, preview_digest: str) -> dict:
    """Write the restored text, then the registry; restore the file if the registry save fails."""
    document = preview_transition(action, scope, change, home=home, root=root, run=run)
    _checked(document, preview_digest)
    value, before = _unchanged(document, home, root, scope)
    after = _changed(value, change)
    _, text = _restored_text(value, after, run)
    try:
        write_target(root, scope, text.encode("utf-8"))
        _save(home, after)
    except PromoteError:
        if read_target(root, scope) != before:
            write_target(root, scope, before)
        raise PromoteError("apply-failed") from None
    return {"status": "applied", "action": action, "scope": scope,
            "candidateSha256": document["candidateSha256"], "activeSha256": active_candidate(after),
            "registrySha256After": after.sha256,
            "fileSha256After": _hex(read_target(root, scope)), "executionAuthorization": False}


# --- build check (REQ-004) -------------------------------------------------------------

EXPORT_FORMAT = "braid-lightning-promotion-export/v0.1"
EXPORT_PATH = "integrations/lightning-promotion/registry-export.json"


def export_bytes(registries: Any) -> bytes:
    """Canonical committed export of scope registries (OD-3), consumed by release builds."""
    _require(isinstance(registries, (list, tuple)) and all(type(r) is promotion.ProfileRegistry
                                                           for r in registries), "invalid-export")
    documents = {r.scope: json.loads(r.to_bytes()) for r in registries}
    _require(len(documents) == len(registries) and all(map(scope_entry, documents)), "invalid-export")
    return canonical({"format": EXPORT_FORMAT, "registries": documents})


def load_export(raw: bytes) -> dict:
    """Scope -> ProfileRegistry from export bytes; unknown scopes and non-canonical bytes refused."""
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise PromoteError("invalid-export") from None
    _require(canonical(value) == raw and type(value) is dict
             and set(value) == {"format", "registries"} and value["format"] == EXPORT_FORMAT
             and type(value["registries"]) is dict, "invalid-export")
    result = {}
    for scope, document in value["registries"].items():
        scope_entry(scope)
        try:
            registry = promotion.ProfileRegistry.from_bytes(canonical(document))
        except promotion.PromotionError:
            raise PromoteError("invalid-export") from None
        _require(registry.scope == scope, "invalid-export")
        result[scope] = registry
    return result


def mismatches(source_root: Path, registries: Any) -> list[str]:
    """``lightning-promotion-mismatch`` lines for mapped files that disagree with their registry.

    The digest is of the canonical source ``SKILL.md`` the packaged skill is built from
    (packaging applies the SPEC-054 name substitutions). A scope without a registry is
    not checked; a registry with no active candidate requires the baseline its first
    decision cites.
    """
    lines = []
    for scope, value in sorted(dict(registries).items()):
        scope_entry(scope)
        try:
            actual = _hex(read_target(source_root, scope))
        except PromoteError:
            actual = "missing"
        expected = active_candidate(value)
        if expected is None:
            try:
                expected = baseline_digest(value)
            except PromoteError:
                expected = "baseline-unknown"
            if expected is None:
                continue
        if actual != expected:
            lines.append(f"lightning-promotion-mismatch: {scope} expected {expected} actual {actual}")
    return lines


# --- CLI: agent-braid lightning promote -----------------------------------------------


def add_arguments(parser) -> None:
    parser.add_argument("--home", type=Path, help="explicit private Agent Braid state root")
    parser.add_argument("--scope", default="lightning.skill.analyze", help="registry scope (closed map)")
    parser.add_argument("--root", type=Path, default=Path("."), help="plugin source checkout (default: .)")
    parser.add_argument("--candidate", metavar="SHA256", help="candidate text digest")
    parser.add_argument("--run-id", required=True,
                        help="Lightning run that stores the candidate (or restored) text")
    parser.add_argument("--registration", type=Path, help="SPEC-049 registration JSON")
    parser.add_argument("--evaluation", type=Path, help="SPEC-049 evaluation record JSON")
    parser.add_argument("--identity", type=Path,
                        help="JSON identity: sourceSha256, host, model, toolSetSha256, policySha256")
    parser.add_argument("--current-identity", type=Path,
                        help="JSON identity now in force (default: --identity); begin and commit "
                             "refuse a drifted one")
    parser.add_argument("--override-reason", help="owner reason to promote without held-out support")
    parser.add_argument("--abort", action="store_true",
                        help="recover an interrupted promotion of --scope: drop the pending entry, "
                             "restore the active text (preview unless --apply)")
    parser.add_argument("--rollback", action="store_true",
                        help="restore the previous active candidate of --scope (preview unless --apply)")
    parser.add_argument("--reason", default=None,
                        help="journal reason id (default: owner-abort, owner-rollback or owner-revoke)")
    parser.add_argument("--apply", action="store_true",
                        help="write; requires --preview-digest (and --actor and --safety to promote)")
    parser.add_argument("--preview-digest", help="digest of the preview the human read")
    parser.add_argument("--actor", help="human decider id (a human decision is the only accepted kind)")
    parser.add_argument("--safety", type=Path,
                        help="JSON safety counts: unsafeAdmissions, authorityViolations, effectViolations")


def _read_file(path: Path, limit: int = 1 << 20) -> bytes:
    try:
        with Path(path).open("rb") as handle:
            raw = handle.read(limit + 1)
    except OSError:
        raise PromoteError("input-unavailable") from None
    _require(len(raw) <= limit, "input-unavailable")
    return raw


def record_from_args(args) -> CandidateRecord:
    scope_entry(args.scope)
    _require(all(getattr(args, k) for k in ("candidate", "registration", "evaluation", "identity")),
             "promote-needs-candidate-pair-identity")
    registration = load_record(Registration, _read_file(args.registration))
    evaluation = load_record(EvaluationRecord, _read_file(args.evaluation))
    try:
        identity = json.loads(_read_file(args.identity))
    except ValueError:
        raise PromoteError("invalid-identity") from None
    try:
        run = store.RunStore(args.home, args.run_id)
    except store.StoreError:
        raise PromoteError("candidate-not-stored") from None
    return build_record(run, args.candidate, args.scope, registration=registration,
                        evaluation=evaluation, identity=identity)


def _run_store(args) -> store.RunStore:
    try:
        return store.RunStore(args.home, args.run_id)
    except store.StoreError:
        raise PromoteError("candidate-not-stored") from None


def _transition(args, action: str, change) -> dict:
    """Preview, or apply with the preview digest, a rollback or revocation."""
    run_store = _run_store(args)
    if not args.apply:
        _require(args.preview_digest is None, "preview-digest-needs-apply")
        return preview_transition(action, args.scope, change, home=args.home, root=args.root, run=run_store)
    _require(bool(args.preview_digest), "apply-needs-digest")
    return apply_transition(action, args.scope, change, home=args.home, root=args.root, run=run_store,
                            preview_digest=args.preview_digest)


def run(args) -> int:
    """Print the preview JSON and return 0; a refusal is one stderr line and exit 2."""
    try:
        at = int(time.time())
        if args.abort:
            run_store = _run_store(args)
            reason = args.reason or "owner-abort"
            if args.apply:
                _require(bool(args.preview_digest), "apply-needs-digest")
                output = apply_abort(args.scope, home=args.home, root=args.root, run=run_store,
                                     preview_digest=args.preview_digest, reason=reason, at=at)
            else:
                _require(args.preview_digest is None, "preview-digest-needs-apply")
                output = preview_abort(args.scope, home=args.home, root=args.root, run=run_store,
                                       reason=reason, at=at)
            print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        if args.rollback:
            output = _transition(args, "rollback", rollback_change(at=at, reason=args.reason or "owner-rollback"))
            print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        record = record_from_args(args)
        if args.apply:
            _require(args.preview_digest and args.actor and args.safety, "apply-needs-digest-actor-safety")
            try:
                safety = json.loads(_read_file(args.safety))
            except ValueError:
                raise PromoteError("invalid-safety") from None
            current = None
            if args.current_identity:
                try:
                    current = json.loads(_read_file(args.current_identity))
                except ValueError:
                    raise PromoteError("invalid-identity") from None
            output = apply_promote(record, home=args.home, root=args.root, current=current,
                                   preview_digest=args.preview_digest,
                                   actor={"kind": "human", "id": args.actor}, safety=safety,
                                   at=at, override_reason=args.override_reason)
        else:
            _require(args.preview_digest is None, "preview-digest-needs-apply")
            output = preview_promote(record, home=args.home, root=args.root,
                                     override_reason=args.override_reason)
    except PromoteError as exc:
        print(f"lightning promote refused ({exc.reason})", file=sys.stderr)
        return 2
    except OSError:
        print("lightning promote refused (io-error)", file=sys.stderr)
        return 2
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
    return 0
