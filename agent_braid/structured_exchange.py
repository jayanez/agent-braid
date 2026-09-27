# SPDX-License-Identifier: AGPL-3.0-only
"""Finite, consultative exchange laboratory for anchored sequence inserts.

This model is intentionally separate from Git patch replay and AIM. It has no
external effects and grants no execution permission.
"""

from __future__ import annotations

from hashlib import sha256
import itertools
import json
import math
from typing import Any


VERSION = "anchored-sequence-v1"
ROOT = "$root"


class InvalidExchange(ValueError):
    """A request falls outside the finite exchange contract."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _keys(value: Any, keys: set[str], name: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise InvalidExchange(f"{name} must contain exactly {sorted(keys)}")
    return value


def _identifier(value: Any, name: str) -> str:
    if type(value) is not str or not value or len(value) > 64 or value == ROOT:
        raise InvalidExchange(f"{name} must be a nonempty identifier of at most 64 characters")
    return value


def _value(value: Any, name: str) -> str:
    if type(value) is not str or len(value) > 256:
        raise InvalidExchange(f"{name} must be a string of at most 256 characters")
    return value


def validate_request(request: Any) -> dict:
    request = _keys(request, {"model", "base", "operations"}, "request")
    if request["model"] != VERSION:
        raise InvalidExchange("unsupported model")
    base, operations = request["base"], request["operations"]
    if type(base) is not list or len(base) > 3:
        raise InvalidExchange("base must contain at most three elements")
    if type(operations) is not list or not 2 <= len(operations) <= 4:
        raise InvalidExchange("operations must contain two to four inserts")
    base_ids: set[str] = set()
    for item in base:
        _keys(item, {"id", "value"}, "base element")
        identifier = _identifier(item["id"], "base id")
        _value(item["value"], "base value")
        if identifier in base_ids:
            raise InvalidExchange("duplicate base id")
        base_ids.add(identifier)
    operation_ids: set[str] = set()
    inserted_ids: set[str] = set()
    for op in operations:
        _keys(op, {"id", "kind", "anchorId", "newId", "value"}, "operation")
        identifier = _identifier(op["id"], "operation id")
        new_id = _identifier(op["newId"], "new id")
        _value(op["value"], "insert value")
        if op["kind"] != "insert":
            raise InvalidExchange("only insert is supported")
        if op["anchorId"] != ROOT and op["anchorId"] not in base_ids:
            raise InvalidExchange("anchor must identify the root or an immutable base element")
        if identifier in operation_ids or new_id in inserted_ids or new_id in base_ids:
            raise InvalidExchange("duplicate operation or inserted id")
        operation_ids.add(identifier)
        inserted_ids.add(new_id)
    return request


def _flatten(base: list[dict], buckets: dict[str, list[dict]]) -> list[dict]:
    result = sorted(buckets[ROOT], key=lambda item: item["id"])
    for item in base:
        result.append(item)
        result.extend(sorted(buckets[item["id"]], key=lambda child: child["id"]))
    return result


def replay(request: dict, order: tuple[str, ...] | list[str]) -> dict:
    """Replay a complete order and record context-dependent physical indices."""
    validate_request(request)
    ops = {op["id"]: op for op in request["operations"]}
    if len(order) != len(ops) or set(order) != set(ops) or len(set(order)) != len(order):
        raise InvalidExchange("order must be a permutation of operation ids")
    buckets = {ROOT: []} | {item["id"]: [] for item in request["base"]}
    steps = []
    for op_id in order:
        op = ops[op_id]
        before = _flatten(request["base"], buckets)
        buckets[op["anchorId"]].append({"id": op["newId"], "value": op["value"]})
        after = _flatten(request["base"], buckets)
        index = next(i for i, item in enumerate(after) if item["id"] == op["newId"])
        steps.append({"operationId": op_id, "anchorId": op["anchorId"],
                      "newId": op["newId"], "residualIndex": index,
                      "beforeHash": _digest(before), "afterHash": _digest(after)})
    final = _flatten(request["base"], buckets)
    return {"order": list(order), "steps": steps, "final": final,
            "observationHash": _digest(final)}


def _pair(request: dict) -> dict:
    ids = [op["id"] for op in request["operations"]]
    forward = replay(request, ids)
    exchanged = replay(request, ids[::-1])
    return {"forward": forward, "exchanged": exchanged,
            "equivalent": forward["final"] == exchanged["final"],
            "residualChanged": (forward["steps"][1]["residualIndex"] !=
                                exchanged["steps"][0]["residualIndex"] or
                                forward["steps"][0]["residualIndex"] !=
                                exchanged["steps"][1]["residualIndex"])}


def _braid(request: dict) -> dict:
    ids = [op["id"] for op in request["operations"]]
    def path(crossings: tuple[int, ...]) -> list[dict]:
        order = ids[:]
        records = [replay(request, order)]
        for crossing in crossings:
            order[crossing], order[crossing + 1] = order[crossing + 1], order[crossing]
            records.append(replay(request, order))
        return records
    left, right = path((0, 1, 0)), path((1, 0, 1))
    return {"left": left, "right": right,
            "equivalent": left[-1]["order"] == right[-1]["order"] and
                          left[-1]["final"] == right[-1]["final"]}


def produce(request: Any) -> dict:
    request = validate_request(request)
    count = len(request["operations"])
    if count not in (2, 3):
        raise InvalidExchange("consultative evidence requires two or three operations")
    paths = _pair(request) if count == 2 else _braid(request)
    anchors = [op["anchorId"] for op in request["operations"]]
    decision = ("review" if count == 3 else
                "propose-swap" if anchors[0] == anchors[1] else "keep-order")
    return {"format": "structured-exchange-evidence-v1", "request": request,
            "requestHash": _digest(request), "kind": "pair" if count == 2 else "braid",
            "paths": paths, "proposal": decision,
            "property": "semantic-final-sequence-equality",
            "observation": "final ordered id/value sequence; chronological steps retained",
            "evidenceMethod": "deterministic-finite-replay",
            "executionAuthorization": False}


def verify(bundle: Any) -> dict:
    if type(bundle) is not dict or set(bundle) != {
        "format", "request", "requestHash", "kind", "paths", "proposal", "property",
        "observation", "evidenceMethod", "executionAuthorization",
    }:
        return {"status": "inconclusive", "reason": "malformed evidence", "executionAuthorization": False}
    try:
        expected = produce(bundle["request"])
    except InvalidExchange as exc:
        return {"status": "inconclusive", "reason": str(exc), "executionAuthorization": False}
    if _canonical(bundle) != _canonical(expected):
        return {"status": "inconclusive", "reason": "evidence differs from regenerated paths",
                "executionAuthorization": False}
    equivalent = expected["paths"]["equivalent"]
    return {"status": "verified-bounded" if equivalent else "divergent",
            "requestHash": expected["requestHash"], "kind": expected["kind"],
            "proposal": expected["proposal"], "executionAuthorization": False}


def exhaustive_corpus() -> dict:
    """Exhaust every anchor assignment in the preregistered 0..3 / 2..4 domain.

    Payloads and ID naming are fixed because they do not affect anchor topology.
    The four-operation cases test all 24 terminal orders but no braid path.
    """
    cases = pair_cases = braid_cases = four_cases = false_certificates = 0
    overlapping_pairs = 0
    path_disjoint_pairs = 0
    serial_steps = 0
    exhaustive_steps = 0
    for base_size in range(4):
        base = [{"id": f"b{i}", "value": f"B{i}"} for i in range(base_size)]
        anchors = [ROOT] + [item["id"] for item in base]
        for count in range(2, 5):
            for assignment in itertools.product(anchors, repeat=count):
                operations = [{"id": f"o{i}", "kind": "insert", "anchorId": anchor,
                               "newId": f"n{i}", "value": f"N{i}"}
                              for i, anchor in enumerate(assignment)]
                request = {"model": VERSION, "base": base, "operations": operations}
                observations = {replay(request, order)["observationHash"]
                                for order in itertools.permutations(op["id"] for op in operations)}
                cases += 1
                serial_steps += count
                exhaustive_steps += count * math.factorial(count)
                if count == 2:
                    pair_cases += 1
                    if assignment[0] == assignment[1]:
                        overlapping_pairs += 1
                    else:
                        path_disjoint_pairs += 1
                    verdict = verify(produce(request))
                    false_certificates += int(verdict["status"] == "verified-bounded" and len(observations) != 1)
                elif count == 3:
                    braid_cases += 1
                    verdict = verify(produce(request))
                    false_certificates += int(verdict["status"] == "verified-bounded" and len(observations) != 1)
                else:
                    four_cases += 1
                    false_certificates += int(len(observations) != 1)
    return {"domain": "base-size-0..3; inserts-2..4; all base/root anchor assignments; fixed ids and payloads",
            "cases": cases, "pairCases": pair_cases, "braidCases": braid_cases,
            "fourOperationCases": four_cases, "overlappingPairCases": overlapping_pairs,
            "pathDisjointPairCases": path_disjoint_pairs,
            "serialStepBaseline": serial_steps,
            "allOrdersStepBaseline": exhaustive_steps,
            "falseCertificates": false_certificates,
            "executionAuthorization": False}
