# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic AIM 0.2 interaction analysis without execution or LLM calls."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from itertools import combinations


REPORT_VERSION = "0.1.0-alpha"
ANALYZER_VERSION = "0.1.0-alpha"
RULE_SET = "exact-resource-footprints-v1"
EFFECT_KINDS = {
    "read", "write", "call", "transform", "emit", "delete", "deploy", "unknown"
}
EXTERNAL_OR_TRANSFORMING = {"call", "transform", "emit", "delete", "deploy", "unknown"}
WRITE_LIKE = {"write", "transform", "delete", "deploy"}
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class InvalidAnalysis(ValueError):
    """The analysis input is malformed or outside the supported contract.

    A structural refusal carries ``pointer`` (a JSON Pointer into the request) and
    ``expected`` (the accepted form); a semantic refusal carries a fixed ``code``.
    All three are built from fixed text and schema-defined names only: request
    values are never echoed, and request keys not defined by the contract are
    replaced by ``_key_token`` (SPEC-069 REQ-007).
    """

    def __init__(self, message: str, *, pointer: str | None = None,
                 expected: str | None = None, code: str | None = None) -> None:
        self.pointer, self.expected, self.code = pointer, expected, code
        text = message
        if pointer is not None:
            text += f" at {pointer or '/'}"
            if expected:
                text += f"; expected {expected}"
        if code:
            text += f" [{code}]"
        super().__init__(text)


def _require(condition: bool, message: str, *, pointer: str | None = None,
             expected: str | None = None, code: str | None = None) -> None:
    if not condition:
        raise InvalidAnalysis(message, pointer=pointer, expected=expected, code=code)


def key_token(key: str) -> str:
    """Stable placeholder for a request key that the contract does not define."""
    return "<key:" + hashlib.sha256(key.encode("utf-8", "surrogatepass")).hexdigest()[:8] + ">"


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


NONBLANK = "a non-blank string"
DIGEST_FORM = "a string like sha256:<64 lowercase hex digits>"


def _nonempty(value: object, label: str, pointer: str | None = None) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"invalid {label}",
             pointer=pointer, expected=NONBLANK)
    return value


def exact_keys(value: dict, required: set[str], message: str, pointer: str) -> None:
    """Require exactly the named properties; report missing names and tokenized unknown keys."""
    if set(value) == required:
        return
    missing = sorted(required - set(value))
    unknown = sorted(key_token(key) for key in value if key not in required)
    detail = []
    if missing:
        detail.append("missing " + ", ".join(missing))
    if unknown:
        detail.append("unknown " + ", ".join(unknown))
    raise InvalidAnalysis(message, pointer=pointer, expected=(
        "an object with exactly the properties " + ", ".join(sorted(required))
        + " (" + "; ".join(detail) + ")"))


def _records(value: object) -> tuple[list[dict], str]:
    source_kind = "aim"
    if isinstance(value, dict) and value.get("analysisInputVersion") == REPORT_VERSION:
        exact_keys(value, {"analysisInputVersion", "source", "operations"},
                   "invalid analysis input envelope", "")
        source = value["source"]
        _require(isinstance(source, dict), "invalid source description",
                 pointer="/source", expected="an object with exactly the properties description, kind")
        exact_keys(source, {"kind", "description"}, "invalid source description", "/source")
        source_kind = _nonempty(source.get("kind"), "source kind", "/source/kind")
        _nonempty(source.get("description"), "source description", "/source/description")
        value = value["operations"]
        where = "/operations"
    elif isinstance(value, dict) and value.get("aimVersion") == "0.2.0-draft":
        value = [value]
        where = ""
    else:
        where = ""
    _require(isinstance(value, list) and value, "expected AIM record or nonempty AIM array",
             pointer=where, expected="an AIM record, a nonempty array of AIM records, or an analysis input envelope")
    for index, item in enumerate(value):
        _require(isinstance(item, dict), "AIM records must be objects",
                 pointer=f"{where}/{index}", expected="an AIM record object")
    return list(value), source_kind


def _bases(value: object, count: int) -> list[str]:
    """JSON Pointer of each record inside the request, for the request form ``_records`` accepted."""
    if isinstance(value, dict) and value.get("analysisInputVersion") == REPORT_VERSION:
        return [f"/operations/{index}" for index in range(count)]
    if isinstance(value, dict):
        return [""]
    return [f"/{index}" for index in range(count)]


EFFECT_FORM = "an object with exactly the properties kind, resource"
RECORD_FIELDS = {
    "aimVersion", "instanceId", "attemptId", "definition", "inputDigest",
    "dependencies", "readVersions", "effects", "evidence",
}


def _validate_record(record: dict, base: str = "") -> None:
    exact_keys(record, RECORD_FIELDS, "AIM record fields do not match 0.2.0-draft", base)
    _require(record["aimVersion"] == "0.2.0-draft", "unsupported AIM version",
             pointer=f"{base}/aimVersion", expected="the constant 0.2.0-draft")
    _nonempty(record["instanceId"], "instanceId", f"{base}/instanceId")
    _nonempty(record["attemptId"], "attemptId", f"{base}/attemptId")
    definition = record["definition"]
    _require(isinstance(definition, dict), "invalid definition", pointer=f"{base}/definition",
             expected="an object with exactly the properties digest, id")
    exact_keys(definition, {"id", "digest"}, "invalid definition", f"{base}/definition")
    _nonempty(definition["id"], "definition id", f"{base}/definition/id")
    _require(isinstance(definition["digest"], str) and DIGEST.fullmatch(definition["digest"]),
             "invalid definition digest", pointer=f"{base}/definition/digest", expected=DIGEST_FORM)
    _require(isinstance(record["inputDigest"], str) and DIGEST.fullmatch(record["inputDigest"]),
             "invalid input digest", pointer=f"{base}/inputDigest", expected=DIGEST_FORM)
    dependencies = record["dependencies"]
    _require(isinstance(dependencies, list), "dependencies must be an array",
             pointer=f"{base}/dependencies", expected="an array of nonempty strings")
    for index, item in enumerate(dependencies):
        _require(isinstance(item, str) and item, "invalid dependency",
                 pointer=f"{base}/dependencies/{index}", expected="a nonempty string")
    _require(len(dependencies) == len(set(dependencies)), "duplicate dependency",
             pointer=f"{base}/dependencies", expected="an array of unique strings")
    versions = record["readVersions"]
    _require(isinstance(versions, dict), "readVersions must be an object",
             pointer=f"{base}/readVersions", expected="an object mapping resource names to integers >= 0")
    for resource, version in versions.items():
        _require(isinstance(resource, str) and bool(resource.strip()), "invalid version resource",
                 pointer=f"{base}/readVersions", expected="non-blank resource names as property names")
        _require(type(version) is int and version >= 0, "invalid read version",
                 pointer=f"{base}/readVersions/{key_token(resource)}", expected="an integer >= 0")
    effects = record["effects"]
    _require(isinstance(effects, dict), "invalid effects", pointer=f"{base}/effects",
             expected="an object with exactly the properties coverage, declared, inferred, observed")
    exact_keys(effects, {"declared", "inferred", "observed", "coverage"}, "invalid effects", f"{base}/effects")
    for channel in ("declared", "inferred", "observed"):
        _require(isinstance(effects[channel], list), f"{channel} effects must be an array",
                 pointer=f"{base}/effects/{channel}", expected="an array of effects")
        for index, effect in enumerate(effects[channel]):
            where = f"{base}/effects/{channel}/{index}"
            _require(isinstance(effect, dict), "invalid effect", pointer=where, expected=EFFECT_FORM)
            exact_keys(effect, {"kind", "resource"}, "invalid effect", where)
            _require(effect["kind"] in EFFECT_KINDS, "unsupported effect kind", pointer=f"{where}/kind",
                     expected="one of " + ", ".join(sorted(EFFECT_KINDS)))
            _nonempty(effect["resource"], "effect resource", f"{where}/resource")
    coverage = effects["coverage"]
    _require(isinstance(coverage, dict), "invalid coverage", pointer=f"{base}/effects/coverage",
             expected="an object with exactly the properties domain, method, status")
    exact_keys(coverage, {"status", "domain", "method"}, "invalid coverage", f"{base}/effects/coverage")
    _require(coverage["status"] in {"complete", "partial", "unknown"}, "invalid coverage status",
             pointer=f"{base}/effects/coverage/status", expected="one of complete, partial, unknown")
    _nonempty(coverage["domain"], "coverage domain", f"{base}/effects/coverage/domain")
    _nonempty(coverage["method"], "coverage method", f"{base}/effects/coverage/method")
    _require(isinstance(record["evidence"], list) and record["evidence"],
             "evidence must be a nonempty array", pointer=f"{base}/evidence",
             expected="a nonempty array of evidence items")


def _validate_batch(records: list[dict], bases: list[str] | None = None) -> None:
    bases = bases or [f"/{index}" for index in range(len(records))]
    for record, base in zip(records, bases):
        _validate_record(record, base)
    identifiers = [record["instanceId"] for record in records]
    attempts = [record["attemptId"] for record in records]
    _require(len(identifiers) == len(set(identifiers)), "duplicate instance ID", code="duplicate-instance-id")
    _require(len(attempts) == len(set(attempts)), "duplicate attempt ID", code="duplicate-attempt-id")
    known = set(identifiers)
    for record in records:
        _require(set(record["dependencies"]) <= known, "unknown dependency", code="unknown-dependency")
        _require(record["instanceId"] not in record["dependencies"], "self dependency", code="self-dependency")
    completed: set[str] = set()
    while len(completed) < len(records):
        ready = {
            record["instanceId"] for record in records
            if set(record["dependencies"]) <= completed
        } - completed
        _require(bool(ready), "cyclic dependencies", code="cyclic-dependencies")
        completed.update(ready)


def _effect_map(record: dict) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for channel in ("declared", "inferred", "observed"):
        for effect in record["effects"][channel]:
            result.setdefault(effect["resource"], set()).add(effect["kind"])
    return result


def _ancestors(records: list[dict]) -> dict[str, set[str]]:
    direct = {record["instanceId"]: set(record["dependencies"]) for record in records}
    result = {identifier: set(items) for identifier, items in direct.items()}
    changed = True
    while changed:
        changed = False
        for identifier in result:
            expanded = result[identifier] | {
                ancestor for item in list(result[identifier]) for ancestor in result[item]
            }
            if expanded != result[identifier]:
                result[identifier] = expanded
                changed = True
    return result


DECLARED_NOT_OBSERVED = "declared-not-observed"


def _only_declared(record: dict) -> bool:
    """True when every evidence item of the record has method ``declared``."""
    evidence = record.get("evidence")
    return bool(evidence) and all(isinstance(item, dict) and item.get("method") == "declared" for item in evidence)


def _interaction(left: dict, right: dict, ancestors: dict[str, set[str]]) -> dict:
    left_id, right_id = left["instanceId"], right["instanceId"]
    left_effects, right_effects = _effect_map(left), _effect_map(right)
    shared = sorted(set(left_effects) & set(right_effects))
    all_kinds = {kind for kinds in (*left_effects.values(), *right_effects.values()) for kind in kinds}
    coverage = {left["effects"]["coverage"]["status"], right["effects"]["coverage"]["status"]}
    reasons: list[str] = []
    constraints: list[str] = []

    if left_id in ancestors[right_id] or right_id in ancestors[left_id]:
        classification = "ordered"
        reasons.append("An explicit dependency path orders the operations.")
        constraints.append("preserve-dependency-order")
    elif shared and any(
        (left_effects[resource] | right_effects[resource]) & WRITE_LIKE
        for resource in shared
    ):
        classification = "conflicting"
        reasons.append("At least one exact shared resource has a write-like effect.")
        constraints.append("serialize-or-isolate")
    elif coverage != {"complete"}:
        classification = "unknown"
        reasons.append("At least one effect footprint is partial or unknown.")
        constraints.append("serialize-unless-stronger-evidence")
    elif all_kinds & EXTERNAL_OR_TRANSFORMING:
        classification = "unknown"
        reasons.append("External, transforming, destructive, or unknown effects require adapter semantics.")
        constraints.append("serialize-unless-stronger-evidence")
    else:
        classification = "independent-candidate"
        reasons.append(
            "Complete exact-resource footprints have no write conflict."
            if shared else "Complete exact-resource footprints are disjoint."
        )
        constraints.append("requires-execution-contract-before-parallelism")

    if left["readVersions"] or right["readVersions"]:
        constraints.append("validate-read-versions-at-use")
        reasons.append("Read-version preconditions remain point-of-use obligations.")

    interaction = {
        "left": left_id,
        "right": right_id,
        "classification": classification,
        "sharedResources": shared,
        "reasons": reasons,
        "constraints": sorted(set(constraints)),
        "evidence": {
            "method": "exact-resource-footprint",
            "assuranceClass": 1 if classification == "independent-candidate" else 0,
            "coverage": sorted(coverage),
            "ruleSet": RULE_SET,
        },
    }
    if classification == "independent-candidate" and _only_declared(left) and _only_declared(right):
        # SPEC-069 REQ-015 / D7: completeness here is the producer's declaration, not an observation.
        interaction["completenessBasis"] = DECLARED_NOT_OBSERVED
    return interaction


def analyze(value: object) -> dict:
    """Analyze AIM records and return a deterministic, non-authorizing report."""
    records, source_kind = _records(value)
    _validate_batch(records, _bases(value, len(records)))
    records = sorted(records, key=lambda item: item["instanceId"])
    ancestors = _ancestors(records)
    interactions = [
        _interaction(left, right, ancestors) for left, right in combinations(records, 2)
    ]
    counts = Counter(item["classification"] for item in interactions)
    uncertainty = []
    if any(record["effects"]["coverage"]["status"] != "complete" for record in records):
        uncertainty.append("At least one operation lacks complete effect coverage.")
    if any(_effect_map(record) == {} for record in records):
        uncertainty.append("At least one operation has no declared, inferred, or observed effect.")
    if any(
        kind in EXTERNAL_OR_TRANSFORMING
        for record in records for kinds in _effect_map(record).values() for kind in kinds
    ):
        uncertainty.append("External or transforming effects require adapter-specific contracts.")
    report = {
        "reportVersion": REPORT_VERSION,
        "analysisId": "",
        "inputDigest": _digest(records),
        "sourceKind": source_kind,
        "analyzer": {
            "name": "agent-braid",
            "version": ANALYZER_VERSION,
            "ruleSet": RULE_SET,
        },
        "operations": [
            {
                "instanceId": record["instanceId"],
                "attemptId": record["attemptId"],
                "dependencies": sorted(record["dependencies"]),
                "coverage": record["effects"]["coverage"],
                "resources": sorted(_effect_map(record)),
            }
            for record in records
        ],
        "interactions": interactions,
        "summary": {
            "operationCount": len(records),
            "pairCount": len(interactions),
            "classifications": {
                name: counts.get(name, 0)
                for name in ("independent-candidate", "ordered", "conflicting", "unknown")
            },
        },
        "uncertainty": uncertainty,
        "limits": [
            "Resource identity is exact-string equality; aliases and semantic dependencies are not inferred.",
            "A candidate establishes no concurrent-execution refinement, authorization, or task correctness.",
            "The analyzer does not execute agents, tools, Git operations, or external effects.",
        ],
        "executionAuthorization": False,
    }
    report["analysisId"] = _digest({**report, "analysisId": None})
    return report


def render_text(report: dict) -> str:
    lines = [
        f"Agent Braid analysis {report['analysisId']}",
        f"Operations: {report['summary']['operationCount']}  Pairs: {report['summary']['pairCount']}",
    ]
    for item in report["interactions"]:
        lines.append(f"{item['left']} / {item['right']}: {item['classification']}")
        for reason in item["reasons"]:
            lines.append(f"  - {reason}")
        lines.append("  constraints: " + ", ".join(item["constraints"]))
        if item.get("completenessBasis"):
            lines.append("  completeness: declared by the producer, not observed")
    if report["uncertainty"]:
        lines.append("Uncertainty:")
        lines.extend(f"  - {item}" for item in report["uncertainty"])
    lines.append("Execution authorization: false")
    return "\n".join(lines) + "\n"



def analyze_with_advice(value: object, *, advice_request_bytes: bytes,
                        expected_context_digest: str, expected_registry_digest: str,
                        cancellation=None) -> tuple[dict, object]:
    """Opt-in sidecar; preserve the complete legacy report and analysis budget.

    The analyzer-choice packet is metadata only. It cannot select a different
    analyzer, prune operations or change the report's shape or digest.
    """
    from agent_braid.system_one_advisors import advise_bound_stage
    records, _ = _records(value)
    report = analyze(value)
    advice = advise_bound_stage(advice_request_bytes,
        expected_context_digest=expected_context_digest,
        expected_registry_digest=expected_registry_digest,
        stage='analyzer-choice', population_ids=[r['instanceId'] for r in records],
        operations=records, cancellation=cancellation)
    return report, advice
