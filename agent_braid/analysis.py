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
    """The analysis input is malformed or outside the supported contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidAnalysis(message)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _nonempty(value: object, label: str) -> str:
    _require(isinstance(value, str) and bool(value.strip()), f"invalid {label}")
    return value


def _records(value: object) -> tuple[list[dict], str]:
    source_kind = "aim"
    if isinstance(value, dict) and value.get("analysisInputVersion") == REPORT_VERSION:
        _require(set(value) == {"analysisInputVersion", "source", "operations"},
                 "invalid analysis input envelope")
        source = value["source"]
        _require(isinstance(source, dict) and set(source) == {"kind", "description"},
                 "invalid source description")
        source_kind = _nonempty(source.get("kind"), "source kind")
        _nonempty(source.get("description"), "source description")
        value = value["operations"]
    elif isinstance(value, dict) and value.get("aimVersion") == "0.2.0-draft":
        value = [value]
    _require(isinstance(value, list) and value, "expected AIM record or nonempty AIM array")
    _require(all(isinstance(item, dict) for item in value), "AIM records must be objects")
    return list(value), source_kind


def _validate_record(record: dict) -> None:
    required = {
        "aimVersion", "instanceId", "attemptId", "definition", "inputDigest",
        "dependencies", "readVersions", "effects", "evidence",
    }
    _require(set(record) == required, "AIM record fields do not match 0.2.0-draft")
    _require(record["aimVersion"] == "0.2.0-draft", "unsupported AIM version")
    _nonempty(record["instanceId"], "instanceId")
    _nonempty(record["attemptId"], "attemptId")
    definition = record["definition"]
    _require(isinstance(definition, dict) and set(definition) == {"id", "digest"},
             "invalid definition")
    _nonempty(definition["id"], "definition id")
    _require(isinstance(definition["digest"], str) and DIGEST.fullmatch(definition["digest"]),
             "invalid definition digest")
    _require(isinstance(record["inputDigest"], str) and DIGEST.fullmatch(record["inputDigest"]),
             "invalid input digest")
    dependencies = record["dependencies"]
    _require(isinstance(dependencies, list), "dependencies must be an array")
    _require(all(isinstance(item, str) and item for item in dependencies),
             "invalid dependency")
    _require(len(dependencies) == len(set(dependencies)), "duplicate dependency")
    versions = record["readVersions"]
    _require(isinstance(versions, dict), "readVersions must be an object")
    for resource, version in versions.items():
        _nonempty(resource, "version resource")
        _require(type(version) is int and version >= 0, "invalid read version")
    effects = record["effects"]
    _require(isinstance(effects, dict) and
             set(effects) == {"declared", "inferred", "observed", "coverage"},
             "invalid effects")
    for channel in ("declared", "inferred", "observed"):
        _require(isinstance(effects[channel], list), f"{channel} effects must be an array")
        for effect in effects[channel]:
            _require(isinstance(effect, dict) and set(effect) == {"kind", "resource"},
                     "invalid effect")
            _require(effect["kind"] in EFFECT_KINDS, "unsupported effect kind")
            _nonempty(effect["resource"], "effect resource")
    coverage = effects["coverage"]
    _require(isinstance(coverage, dict) and set(coverage) == {"status", "domain", "method"},
             "invalid coverage")
    _require(coverage["status"] in {"complete", "partial", "unknown"},
             "invalid coverage status")
    _nonempty(coverage["domain"], "coverage domain")
    _nonempty(coverage["method"], "coverage method")
    _require(isinstance(record["evidence"], list) and record["evidence"],
             "evidence must be a nonempty array")


def _validate_batch(records: list[dict]) -> None:
    for record in records:
        _validate_record(record)
    identifiers = [record["instanceId"] for record in records]
    attempts = [record["attemptId"] for record in records]
    _require(len(identifiers) == len(set(identifiers)), "duplicate instance ID")
    _require(len(attempts) == len(set(attempts)), "duplicate attempt ID")
    known = set(identifiers)
    for record in records:
        _require(set(record["dependencies"]) <= known, "unknown dependency")
        _require(record["instanceId"] not in record["dependencies"], "self dependency")
    completed: set[str] = set()
    while len(completed) < len(records):
        ready = {
            record["instanceId"] for record in records
            if set(record["dependencies"]) <= completed
        } - completed
        _require(bool(ready), "cyclic dependencies")
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

    return {
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


def analyze(value: object) -> dict:
    """Analyze AIM records and return a deterministic, non-authorizing report."""
    records, source_kind = _records(value)
    _validate_batch(records)
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
    if report["uncertainty"]:
        lines.append("Uncertainty:")
        lines.extend(f"  - {item}" for item in report["uncertainty"])
    lines.append("Execution authorization: false")
    return "\n".join(lines) + "\n"

