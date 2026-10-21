# SPDX-License-Identifier: AGPL-3.0-only
"""Source-bound deterministic simulation reports and independent replay checks."""

from hashlib import sha256
from pathlib import Path

from .explore import explore_paths
from .model import InvalidWorkload, canonical, declared_effects, digest, validate
from .observations import compare, trace_safety


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = "specs/024-effectful-workload-lab/contracts/simulation-v1.md"


def source_bindings():
    paths = [*sorted((ROOT / "research/workload_lab").glob("*.py")), ROOT / CONTRACT,
             ROOT / "research/workload_lab/SEMANTICS.md",
             *sorted((ROOT / "specs/024-effectful-workload-lab/contracts").glob("*.schema.json"))]
    return {path.relative_to(ROOT).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in paths}


def explore(request):
    """Validate and independently enumerate the complete bounded simulation."""
    request = validate(request)
    bound = source_bindings()
    result = explore_paths(request)
    complete = result["coverage"]["complete"]
    report = {"format": "effectful-workload-report-v1", "request": request,
              "requestHash": digest(request), "sourceBindings": bound,
              **result, "comparison": compare(request, result["paths"], complete),
              "traceSafety": trace_safety(result["paths"], complete),
              "uncertainty": [{"operationId": operation["id"],
                               **declared_effects(request, operation)}
                              for operation in sorted(request["operations"], key=lambda op: op["id"])],
              "executionAuthorization": False}
    if source_bindings() != bound:
        raise InvalidWorkload("simulation source changed during exploration")
    return report


def verify(report):
    """Regenerate every deterministic field; caller claims never authorize effects."""
    rejected = {"status": "rejected", "executionAuthorization": False}
    fields = {"format", "request", "requestHash", "sourceBindings", "paths", "coverage",
              "comparison", "traceSafety", "uncertainty", "executionAuthorization"}
    try:
        if type(report) is not dict or set(report) != fields:
            return {**rejected, "reason": "malformed-report"}
        if (report["format"] != "effectful-workload-report-v1"
                or report["executionAuthorization"] is not False
                or report["sourceBindings"] != source_bindings()):
            return {**rejected, "reason": "binding-or-format-mismatch"}
        expected = explore(report["request"])
        if canonical(report) != canonical(expected):
            return {**rejected, "reason": "replay-mismatch"}
        return {"status": "verified", "requestHash": expected["requestHash"],
                "verdict": expected["comparison"]["verdict"], "executionAuthorization": False}
    except (InvalidWorkload, ValueError, TypeError, KeyError, RecursionError, OSError):
        return {**rejected, "reason": "invalid-bounded-artifact"}
