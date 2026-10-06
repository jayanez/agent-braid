# SPDX-License-Identifier: AGPL-3.0-only
"""Independent finite oracle for the anchored candidate mapping, not a proof."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
from itertools import permutations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from agent_braid import structured_exchange as implementation

VERSION = "anchored-proof-mapping-v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def abstract_flatten(request, consumed):
    """Independent set-union carrier; no use of implementation flattening/indexes."""
    operations = {op["id"]: op for op in request["operations"]}
    buckets = {"$root": {}}
    for base in request["base"]:
        buckets[base["id"]] = {}
    for identifier in consumed:
        op = operations[identifier]
        buckets[op["anchorId"]][op["newId"]] = op["value"]
    result = [{"id": i, "value": value} for i, value in sorted(buckets["$root"].items())]
    for base in request["base"]:
        result.append(deepcopy(base))
        result.extend({"id": i, "value": value} for i, value in sorted(buckets[base["id"]].items()))
    return result


def exchange(order, crossings):
    order = list(order)
    for index in crossings:
        if type(index) is not int or not 0 <= index < len(order) - 1:
            raise ValueError("invalid adjacent crossing")
        order[index], order[index + 1] = order[index + 1], order[index]
    return order


def crosscheck(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {"version", "cases", "excluded"} or manifest["version"] != VERSION:
        raise ValueError("invalid mapping manifest")
    if not isinstance(manifest["cases"], list) or not 1 <= len(manifest["cases"]) <= 32:
        raise ValueError("mapping case cap")
    if not isinstance(manifest["excluded"], list) or len(manifest["excluded"]) > 32:
        raise ValueError("mapping exclusion cap")
    cases = []
    seen = set()
    for request in manifest["cases"]:
        implementation.validate_request(request)
        request_hash = digest(request)
        if request_hash in seen:
            raise ValueError("duplicate mapping case")
        seen.add(request_hash)
        ids = sorted(op["id"] for op in request["operations"])
        definitions = {op["id"]: op for op in request["operations"]}
        reference = abstract_flatten(request, set(ids))
        mismatches, orders, changed_residuals, trace_hashes = [], 0, set(), set()
        involutive = adjacent = far = 0
        for order in permutations(ids):
            concrete = implementation.replay(request, order)
            orders += 1
            trace_hashes.add(digest(concrete["steps"]))
            if concrete["final"] != reference:
                mismatches.append("flattening")
            consumed = set()
            for identifier, step in zip(order, concrete["steps"]):
                before = abstract_flatten(request, consumed)
                consumed.add(identifier)
                after = abstract_flatten(request, consumed)
                position = next(i for i, row in enumerate(after) if row["id"] == definitions[identifier]["newId"])
                changed_residuals.add((identifier, position))
                if (step["operationId"] != identifier or step["newId"] != definitions[identifier]["newId"]
                        or step["anchorId"] != definitions[identifier]["anchorId"]
                        or step["residualIndex"] != position
                        or step["beforeHash"] != digest(before) or step["afterHash"] != digest(after)):
                    mismatches.append("residual-source-mapping")
            for i in range(len(ids) - 1):
                involutive += 1
                if exchange(order, (i, i)) != list(order):
                    mismatches.append("involutivity")
            if len(ids) >= 3:
                adjacent += 1
                left, right = exchange(order, (0, 1, 0)), exchange(order, (1, 0, 1))
                if left != right or implementation.replay(request, left)["final"] != implementation.replay(request, right)["final"]:
                    mismatches.append("adjacent-coherence")
            if len(ids) == 4:
                far += 1
                left, right = exchange(order, (0, 2)), exchange(order, (2, 0))
                if left != right or implementation.replay(request, left)["final"] != implementation.replay(request, right)["final"]:
                    mismatches.append("far-commutation")
        if len(ids) in (2, 3):
            evidence = implementation.produce(request)
            if implementation.verify(evidence)["status"] != "verified-bounded":
                mismatches.append("bounded-producer-replay")
            if len(ids) == 3:
                expected_left = [exchange(ids, (0, 1, 0)[:i]) for i in range(4)]
                expected_right = [exchange(ids, (1, 0, 1)[:i]) for i in range(4)]
                if ([row["order"] for row in evidence["paths"]["left"]] != expected_left
                        or [row["order"] for row in evidence["paths"]["right"]] != expected_right):
                    mismatches.append("left-to-right-source-convention")
        cases.append({"requestHash": request_hash, "orders": orders, "reference": reference,
                      "mismatches": mismatches, "involutiveChecks": involutive,
                      "adjacentChecks": adjacent, "farChecks": far,
                      "distinctChronologicalTraceHashes": len(trace_hashes),
                      "distinctInstanceResidualIndices": len(changed_residuals)})
    excluded = []
    for request in manifest["excluded"]:
        try:
            implementation.validate_request(request)
            rejected = False
        except implementation.InvalidExchange:
            rejected = True
        excluded.append({"requestHash": digest(request), "rejected": rejected})
    sources = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in (
        "agent_braid/structured_exchange.py", "docs/adr/0017-bounded-structured-exchange.md",
        "docs/theory/STRUCTURED_EXCHANGE.md", "specs/025-contextual-proof-obligations/premise-inventory.json",
        "scripts/crosscheck_contextual_proof_mapping.py")}
    report = {"version": VERSION, "manifestHash": digest(manifest), "sources": sources,
              "cases": cases, "excluded": excluded,
              "status": "finite-mapping-match" if all(not row["mismatches"] for row in cases) and all(row["rejected"] for row in excluded) else "divergent",
              "proofAccepted": False, "executionAuthorization": False,
              "limits": "Named finite insert fixtures only; candidate argument and independent proof review remain separate."}
    report["reportHash"] = digest(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        from research.contextual_lab.checker import load
        from research.contextual_lab.__main__ import write_exclusive
        result = crosscheck(load(args.manifest))
        write_exclusive(args.output, canonical(result), args.manifest)
        return 0 if result["status"] == "finite-mapping-match" else 1
    except (ValueError, TypeError, KeyError, OSError, implementation.InvalidExchange):
        print("mapping artifact rejected", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
