# SPDX-License-Identifier: AGPL-3.0-only
"""Offline RF-T10 metadata prefilter; never a verifier or collection grant.

Only necessary path/count restrictions of pinned typed-v1 are considered.
Matching metadata stays unknown: patch grammar, source rights, fixture ownership,
goals, budgets and native preparation have not been verified. No I/O occurs.
"""
from __future__ import annotations

import hashlib
import json
import re

FORMAT = "agent-braid-backlog-coverage/v1"
VERIFIER_SHA256 = "a0378c34b805387b0518cf6ebc3da05599976cb7f037d5f140c2571c8f362ea3"
MAX_BYTES = 1048576
_FIELDS = {"taskId", "attemptId", "originalPaths", "presentedPaths", "operationCount", "workflowStatus"}
_STATES = {"registered", "completed", "refused", "cancelled", "error", "missing", "abandoned", "not-selected"}


class CoverageError(ValueError):
    """Malformed/over-budget metadata; no partial population is returned."""


def _require(ok, reason="invalid-coverage-metadata"):
    if not ok:
        raise CoverageError(reason)


def _paths(value):
    _require(type(value) is list and 1 <= len(value) <= 256)
    for path in value:
        _require(type(path) is str and 1 <= len(path) <= 512)
        _require(not any(ord(c) < 32 or ord(c) == 127 or 0xD800 <= ord(c) <= 0xDFFF for c in path))
        _require(len(path.encode("utf-8")) <= 512 and "\\" not in path)
        _require(all(part not in ("", ".", "..") for part in path.split("/")))
    _require(len(set(value)) == len(value))


def assess_backlog(records):
    """Retain every supplied attempt; metadata alone cannot establish support.

    The caller owns population completeness and original-path provenance. This
    function detects a declared transformation, not an undisclosed false source.
    Malformed batches fail atomically; retain their raw inputs in the caller's
    authorized engineering records. The returned digest is integrity, not consent.
    """
    _require(type(records) is list and len(records) <= 1000, "attempt-budget-exceeded")
    seen, input_size = set(), 0
    for record in records:
        _require(type(record) is dict and set(record) == _FIELDS)
        for field in ("taskId", "attemptId"):
            value = record[field]
            _require(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9/:._-]{0,127}", value) is not None)
        _require(record["attemptId"] not in seen, "duplicate-attempt")
        seen.add(record["attemptId"])
        for field in ("originalPaths", "presentedPaths"):
            _paths(record[field])
            input_size += sum(len(p.encode("utf-8")) for p in record[field])
        _require(input_size <= MAX_BYTES, "input-budget-exceeded")
        count = record["operationCount"]
        _require(count is None or type(count) is int and 0 <= count <= 2**31 - 1)
        _require(type(record["workflowStatus"]) is str and record["workflowStatus"] in _STATES)
    raw = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    _require(len(raw) <= MAX_BYTES, "input-budget-exceeded")
    attempts = []
    counts = dict.fromkeys(("supported", "unsupported", "refused", "unknown"), 0)
    for record in records:
        paths, count = record["originalPaths"], record["operationCount"]
        reasons = []
        if set(paths) != set(record["presentedPaths"]):
            reasons.append("source-path-transformed")
        if any(re.fullmatch(r"[a-z0-9][a-z0-9.-]*\.txt", p) is None for p in paths):
            reasons.append("path-outside-v1")
        if len(paths) > 8:
            reasons.append("file-count-outside-v1")
        if count is not None and not 2 <= count <= 4:
            reasons.append("operation-count-outside-v1")
        status = "refused" if "source-path-transformed" in reasons else "unsupported" if reasons else "unknown"
        if count is None:
            reasons.append("operation-count-unavailable")
        if status == "unknown":
            reasons.append("full-verifier-not-run")
        counts[status] += 1
        attempts.append({key: record[key] for key in ("taskId", "attemptId", "workflowStatus")}
                        | {"status": status, "reasons": reasons})
    return {"format": FORMAT, "stage": "metadata-prefilter", "verifierSHA256": VERIFIER_SHA256,
            "inputDigest": hashlib.sha256(raw).hexdigest(), "attempts": attempts,
            "totalAttempts": len(attempts), "counts": counts,
            "supportedFraction": 0.0 if attempts else None,
            "typedDecisionProduced": False, "sourceAdmission": False, "executionAuthorization": False}
