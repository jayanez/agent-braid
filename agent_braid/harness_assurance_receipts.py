# SPDX-License-Identifier: AGPL-3.0-only
"""Assurance profiles, gate receipts and standing authorizations: builder, verifier, validity check; offline, advisory.

A gate receipt (``braid-harness-gate-receipt/v0.1``, SPEC-067 contract) records what a gate reported: the depth and
mode actually applied with their sources, base and head commit, the profile digest, the risk class, the reviews
run (with findings applied and rejected), the commands run with exit codes, the approvals and a content digest.
``verify_receipt`` checks it against a compiled artifact (T005) and the head commit the caller expects: structure,
digest, commit binding, profile binding, depth not below the effective depth, mode consistent with the effective
mode, approvals matching the mode and, at ``pre-pr-review``, every review the depth requires. The digest detects
inconsistent edits only (a recomputed digest is not detected); a receipt is a record of what was reported, not
proof that a review was sound or happened, and it belongs in an operator-owned store written by the orchestrator.
Each independent reviewer (R4) is one review entry of the gate receipt, distinct from the author and each other.

A standing authorization (``braid-harness-standing-authorization/v0.1``) is a hashed JSON record holding the
verbatim owner statement. ``evaluate_standing`` decides, for one gate, whether it is valid: only the founder may
issue (Q4), only ``merge`` admits it (Q2), at most 30 days per authorization (Q3), and the conditions green CI,
receipts present and no open review threads must all hold (Q2). Anything else (missing, malformed, expired, revoked,
out of scope, non-permitted issuer, non-admitting checkpoint, missing statement, failing condition) resolves to
``approve-each`` with a fixed fallback reason, never to ``autonomous``. Time is injected as ``YYYY-MM-DDTHH:MM:SSZ``
text; nothing here reads a clock, host, network or model. Like the profile journal this is binding, not
authenticity: the issuer is asserted by the stored record, which lives in an operator-owned location.

Nothing here executes, merges, releases or approves anything; ``executionAuthorization`` stays false.
"""
from __future__ import annotations

import fnmatch
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from .harness_assurance import (
    ALLOWED_MODES, CHECKPOINTS, CODE_LADDER, DEPTH_CHECKPOINT, DEPTHS, DOCS_LADDER, INDEPENDENT_REVIEW, MODES,
    AssuranceError, _hash, _id, _int, digest,
)

RECEIPT_FORMAT = "braid-harness-gate-receipt/v0.1"
AUTHORIZATION_FORMAT = "braid-harness-standing-authorization/v0.1"
PERMITTED_ISSUERS = ("founder",)  # Q4
MAX_HORIZON_SECONDS = 30 * 86400  # Q3, per authorization
CONDITIONS = ("ciGreen", "noOpenReviewThreads", "receiptsPresent")  # Q2: all required, sorted
REVIEW_KINDS = tuple(sorted({kind for ladder in (CODE_LADDER, DOCS_LADDER) for kinds in ladder.values() for kind in kinds}))
REVIEW_STATUSES = ("completed", "incomplete")
APPROVAL_KINDS = ("human", "standing-authorization")
FALLBACK_REASONS = (
    "missing", "invalid-record", "checkpoint-not-admitting", "out-of-scope", "issuer-not-permitted",
    "statement-missing", "revoked", "not-yet-valid", "expired", "horizon-exceeded", "condition-failed",
)
RECEIPT_REASONS = (
    "invalid-receipt", "unsupported-schema", "digest-mismatch", "invalid-artifact", "commit-mismatch",
    "profile-mismatch", "depth-below-effective", "mode-below-effective", "mode-mismatch", "mode-source-mismatch",
    "fallback-reason-invalid", "command-without-exit-code", "approval-mismatch", "review-missing",
    "independent-reviews-insufficient", "checkpoint-mismatch", "invalid-authorization", "invalid-time", "unknown-checkpoint",
)
MAX_ITEMS = 64
MAX_TEXT = 1024
_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_COMMIT = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_RECEIPT_KEYS = frozenset({
    "schema", "checkpoint", "depth", "depthSource", "mode", "modeSource", "baseCommit", "headCommit",
    "profileDigest", "riskClass", "author", "reviews", "commands", "approvals", "fallbackReason", "createdAt",
    "digest"})
_AUTHORIZATION_KEYS = frozenset({
    "schema", "id", "checkpoint", "repository", "branchPattern", "conditions", "issuedAt", "expiresAt", "issuer",
    "ownerStatement", "revokedAt", "digest"})
_ARTIFACT_KEYS = frozenset({"checkpoints", "inputs", "reviews", "risk", "digest"})


class ReceiptError(AssuranceError):
    """Sanitized refusal: a fixed reason, plus the name of the unsatisfied review when a review is the cause."""

    def __init__(self, reason: str, review: str | None = None):
        super().__init__(reason)
        self.review = review


def _require(condition: bool, reason: str, review: str | None = None) -> None:
    if not condition:
        raise ReceiptError(reason, review)


def _text(value: Any, *, empty: bool = False) -> bool:
    return type(value) is str and (empty or value.strip() != "") and len(value) <= MAX_TEXT and value.isprintable()


def _seconds(value: Any) -> int:
    _require(type(value) is str and _TIME.fullmatch(value) is not None, "invalid-time")
    try:
        return int(datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp())
    except ValueError:
        raise ReceiptError("invalid-time") from None


def _sealed(body: Mapping[str, Any]) -> dict[str, Any]:
    return {**body, "digest": digest(body)}


def _unsealed(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if key != "digest"}


# --- standing authorizations ------------------------------------------------------------


def build_authorization(*, id: str, checkpoint: str, repository: str, branch_pattern: str, issued_at: str,
                        expires_at: str, issuer: str, owner_statement: str,
                        revoked_at: str | None = None) -> dict[str, Any]:
    """The hashed standing-authorization record; validity is decided by ``evaluate_standing``, not here."""
    return _sealed({
        "schema": AUTHORIZATION_FORMAT, "id": id, "checkpoint": checkpoint, "repository": repository,
        "branchPattern": branch_pattern, "conditions": list(CONDITIONS), "issuedAt": issued_at,
        "expiresAt": expires_at, "issuer": issuer, "ownerStatement": owner_statement, "revokedAt": revoked_at,
    })


def _check_authorization(record: Any) -> None:
    ok = (type(record) is dict and set(record) == _AUTHORIZATION_KEYS and record["schema"] == AUTHORIZATION_FORMAT
          and _id(record["id"]) and record["checkpoint"] in CHECKPOINTS
          and all(_text(record[key]) for key in ("repository", "branchPattern", "issuer"))
          and type(record["ownerStatement"]) is str and len(record["ownerStatement"]) <= 8 * MAX_TEXT
          and record["conditions"] == list(CONDITIONS)
          and (record["revokedAt"] is None or type(record["revokedAt"]) is str))
    _require(ok, "invalid-authorization")
    for key in ("issuedAt", "expiresAt", "revokedAt"):
        if record[key] is not None or key != "revokedAt":  # only the revocation time may be absent
            try:
                _seconds(record[key])
            except ReceiptError:
                raise ReceiptError("invalid-authorization") from None
    _require(record["digest"] == digest(_unsealed(record)), "invalid-authorization")


def _fallback(reason: str) -> dict[str, Any]:
    return {"mode": "approve-each", "authorization": None, "fallbackReason": reason}


def evaluate_standing(authorization: Any, *, checkpoint: str, repository: str, branch: str, now: str,
                      conditions_met: Mapping[str, Any]) -> dict[str, Any]:
    """Decide one gate: ``standing-authorization`` citing the record, or ``approve-each`` with a fallback reason."""
    _require(checkpoint in CHECKPOINTS, "unknown-checkpoint")
    _require(type(repository) is str and type(branch) is str, "invalid-authorization")
    moment = _seconds(now)
    if authorization is None:
        return _fallback("missing")
    try:
        _check_authorization(authorization)
    except ReceiptError:
        return _fallback("invalid-record")
    record = authorization
    issued, expires = _seconds(record["issuedAt"]), _seconds(record["expiresAt"])
    checks = (
        ("checkpoint-not-admitting", "standing-authorization" not in ALLOWED_MODES[checkpoint]),
        ("out-of-scope", record["checkpoint"] != checkpoint or record["repository"] != repository
         or not fnmatch.fnmatchcase(branch, record["branchPattern"])),
        ("issuer-not-permitted", record["issuer"] not in PERMITTED_ISSUERS),
        ("statement-missing", record["ownerStatement"].strip() == ""),
        ("horizon-exceeded", expires <= issued or expires - issued > MAX_HORIZON_SECONDS),
        ("revoked", record["revokedAt"] is not None and _seconds(record["revokedAt"]) <= moment),
        ("not-yet-valid", moment < issued),
        ("expired", moment >= expires),
        ("condition-failed", not isinstance(conditions_met, Mapping)
         or any(conditions_met.get(name) is not True for name in record["conditions"])),
    )
    for reason, failed in checks:
        if failed:
            return _fallback(reason)
    return {"mode": "standing-authorization", "authorization": record["id"], "fallbackReason": None}


# --- receipts ----------------------------------------------------------------------------


def _row(artifact: Mapping[str, Any], checkpoint: str) -> Mapping[str, Any]:
    _require(checkpoint in CHECKPOINTS, "unknown-checkpoint")
    _require(isinstance(artifact, Mapping) and _ARTIFACT_KEYS <= set(artifact)
             and isinstance(artifact["checkpoints"], list), "invalid-artifact")
    _require(artifact["digest"] == digest(_unsealed(artifact)), "invalid-artifact")
    row = next((r for r in artifact["checkpoints"] if isinstance(r, Mapping) and r.get("checkpoint") == checkpoint), None)
    _require(row is not None, "invalid-artifact")
    return row


def build_receipt(artifact: Mapping[str, Any], *, checkpoint: str, base_commit: str, head_commit: str, author: str,
                  reviews: list[Any], commands: list[Any], approvals: list[Any], created_at: str,
                  standing: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Assemble and seal a receipt from a compiled artifact; ``verify_receipt`` decides whether it passes.

    When the effective mode is ``standing-authorization`` the applied mode comes from ``standing`` (an
    ``evaluate_standing`` decision); without a decision the gate falls back to ``approve-each`` as ``missing``.
    """
    row = _row(artifact, checkpoint)
    mode, source, reason = row["mode"], row["modeSource"], None
    if mode == "standing-authorization":
        decision = standing if standing is not None else _fallback("missing")
        mode, reason = decision["mode"], decision["fallbackReason"]
        if mode == "standing-authorization":
            approvals = [*approvals, {"kind": "standing-authorization", "ref": decision["authorization"]}]
        else:
            source = "fallback"
    return _sealed({
        "schema": RECEIPT_FORMAT, "checkpoint": checkpoint, "depth": row.get("depth"),
        "depthSource": row.get("depthSource"), "mode": mode, "modeSource": source, "baseCommit": base_commit,
        "headCommit": head_commit, "profileDigest": artifact["inputs"]["profile"],
        "riskClass": artifact["risk"]["riskClass"], "author": author, "reviews": reviews, "commands": commands,
        "approvals": approvals, "fallbackReason": reason, "createdAt": created_at,
    })


def _check_findings(review: Mapping[str, Any]) -> bool:
    applied, rejected = review["findingsApplied"], review["findingsRejected"]
    return (type(applied) is list and len(applied) <= MAX_ITEMS and all(_text(item) for item in applied)
            and type(rejected) is list and len(rejected) <= MAX_ITEMS
            and all(type(item) is dict and set(item) == {"finding", "reason"} and _text(item["finding"])
                    and _text(item["reason"]) for item in rejected))


def _check_shape(receipt: Any) -> None:
    _require(type(receipt) is dict and set(receipt) == _RECEIPT_KEYS, "invalid-receipt")
    _require(receipt["schema"] == RECEIPT_FORMAT, "unsupported-schema")
    commands = receipt["commands"]
    _require(type(commands) is list and len(commands) <= MAX_ITEMS, "invalid-receipt")
    for command in commands:  # a command without an exit code has its own fixed reason
        _require(type(command) is dict and _int(command.get("exitCode"), -255, 255), "command-without-exit-code")
        _require(set(command) == {"argv", "exitCode", "outputSha256"} and type(command["argv"]) is list
                 and 0 < len(command["argv"]) <= MAX_ITEMS and all(_text(arg, empty=True) for arg in command["argv"])
                 and _hash(command["outputSha256"]), "invalid-receipt")
    reviews = receipt["reviews"]
    _require(type(reviews) is list and len(reviews) <= MAX_ITEMS and all(
        type(r) is dict and set(r) == {"kind", "reviewer", "status", "findingsApplied", "findingsRejected"}
        and r["kind"] in REVIEW_KINDS and _id(r["reviewer"]) and r["status"] in REVIEW_STATUSES
        and _check_findings(r) for r in reviews), "invalid-receipt")
    approvals = receipt["approvals"]
    _require(type(approvals) is list and len(approvals) <= MAX_ITEMS and all(
        type(a) is dict and set(a) == {"kind", "ref"} and a["kind"] in APPROVAL_KINDS and _text(a["ref"])
        for a in approvals), "invalid-receipt")
    _require(receipt["checkpoint"] in CHECKPOINTS and receipt["mode"] in MODES and _id(receipt["author"])
             and _COMMIT.fullmatch(str(receipt["baseCommit"])) and _COMMIT.fullmatch(str(receipt["headCommit"]))
             and _hash(receipt["profileDigest"]) and _text(receipt["riskClass"])
             and (receipt["fallbackReason"] is None or receipt["fallbackReason"] in FALLBACK_REASONS)
             and (receipt["depth"] is None) == (receipt["depthSource"] is None)
             and (receipt["depth"] is None or receipt["depth"] in DEPTHS) and _text(receipt["modeSource"])
             and (receipt["depthSource"] is None or _text(receipt["depthSource"])), "invalid-receipt")
    _seconds(receipt["createdAt"])


def _check_mode(receipt: Mapping[str, Any], row: Mapping[str, Any]) -> None:
    effective, applied = row["mode"], receipt["mode"]
    _require(MODES.index(applied) >= MODES.index(effective), "mode-below-effective")
    fell_back = effective == "standing-authorization" and applied == "approve-each"
    _require(fell_back or applied == effective, "mode-mismatch")  # raising by hand is not a recorded fallback
    _require((receipt["fallbackReason"] is not None) == fell_back, "fallback-reason-invalid")
    _require(receipt["modeSource"] == ("fallback" if fell_back else row["modeSource"]), "mode-source-mismatch")
    kinds = [approval["kind"] for approval in receipt["approvals"]]
    if applied == "standing-authorization":
        _require(kinds == ["standing-authorization"], "approval-mismatch")
    elif applied in ("approve-each", "human-only"):
        _require("human" in kinds and "standing-authorization" not in kinds, "approval-mismatch")
    else:
        _require("standing-authorization" not in kinds, "approval-mismatch")


def _check_reviews(receipt: Mapping[str, Any], artifact: Mapping[str, Any]) -> None:
    required = artifact["reviews"]["required"]
    done = [r for r in receipt["reviews"] if r["status"] == "completed"]
    for kind in required:
        if kind == INDEPENDENT_REVIEW:
            reviewers = {r["reviewer"] for r in done if r["kind"] == kind and r["reviewer"] != receipt["author"]}
            _require(len(reviewers) >= artifact["reviews"]["minIndependentReviewers"],
                     "independent-reviews-insufficient", kind)
        else:
            _require(any(r["kind"] == kind for r in done), "review-missing", kind)


def verify_receipt(receipt: Any, artifact: Mapping[str, Any], *, checkpoint: str, base_commit: str,
                   head_commit: str) -> dict[str, Any]:
    """Return the receipt when it passes the ``checkpoint`` gate for ``head_commit``; else raise ``ReceiptError``.

    ``ReceiptError.reason`` is a fixed string from ``RECEIPT_REASONS``; ``ReceiptError.review`` names the first
    unsatisfied required review. Checks run in the order: structure, digest, artifact, checkpoint, commits,
    profile, depth, mode and approvals, reviews. A standing-authorization approval is checked only for form: its
    reference is not resolved here, so the caller confirms the cited record with ``evaluate_standing``.
    """
    _check_shape(receipt)
    _require(receipt["digest"] == digest(_unsealed(receipt)), "digest-mismatch")
    try:
        _verify_against(receipt, artifact, checkpoint, base_commit, head_commit)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as error:
        if isinstance(error, ReceiptError):
            raise
        raise ReceiptError("invalid-artifact") from None  # a self-consistent but malformed artifact
    return receipt


def _verify_against(receipt: Mapping[str, Any], artifact: Mapping[str, Any], checkpoint: str, base_commit: str,
                    head_commit: str) -> None:
    row = _row(artifact, receipt["checkpoint"])
    _require(receipt["checkpoint"] == checkpoint, "checkpoint-mismatch")
    _require(receipt["headCommit"] == head_commit and receipt["baseCommit"] == base_commit, "commit-mismatch")
    _require(receipt["profileDigest"] == artifact["inputs"]["profile"]
             and receipt["riskClass"] == artifact["risk"]["riskClass"], "profile-mismatch")
    effective_depth = row.get("depth")
    _require((receipt["depth"] is None) == (effective_depth is None) and (
        effective_depth is None or DEPTHS.index(receipt["depth"]) >= DEPTHS.index(effective_depth)),
        "depth-below-effective")
    _check_mode(receipt, row)
    if receipt["checkpoint"] == DEPTH_CHECKPOINT:
        _check_reviews(receipt, artifact)
