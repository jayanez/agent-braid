#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Cross-check the finite M3 replay with a separately written rank-key oracle.

This is an internal, independent-implementation check of the named sequence
model, not independent scientific validation or an execution authorization.
"""

from __future__ import annotations

from hashlib import sha256
from itertools import permutations, product
import json
from pathlib import Path
import platform
import random
import sys

from agent_braid.structured_exchange import ROOT, VERSION, produce, replay, verify


def _hash(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(data.encode("utf-8")).hexdigest()


def oracle_replay(request: dict, order: tuple[str, ...]) -> dict:
    """Rank each visible element directly; do not call the M3 state machine."""
    base = request["base"]
    anchor_rank = {ROOT: -1} | {item["id"]: i for i, item in enumerate(base)}
    operations = {item["id"]: item for item in request["operations"]}
    inserted: list[dict] = []
    steps = []

    def visible() -> list[dict]:
        ranked = [(2 * i, "", item) for i, item in enumerate(base)]
        ranked.extend((2 * anchor_rank[op["anchorId"]] + 1, op["newId"],
                       {"id": op["newId"], "value": op["value"]})
                      for op in inserted)
        return [item for _, _, item in sorted(ranked, key=lambda row: row[:2])]

    for operation_id in order:
        before = visible()
        operation = operations[operation_id]
        inserted.append(operation)
        after = visible()
        position = next(i for i, item in enumerate(after)
                        if item["id"] == operation["newId"])
        steps.append({"operationId": operation_id,
                      "anchorId": operation["anchorId"],
                      "newId": operation["newId"],
                      "residualIndex": position,
                      "beforeHash": _hash(before), "afterHash": _hash(after)})
    final = visible()
    return {"order": list(order), "steps": steps, "final": final,
            "observationHash": _hash(final)}


def check_request(request: dict) -> int:
    ids = tuple(op["id"] for op in request["operations"])
    count = 0
    for order in permutations(ids):
        actual, expected = replay(request, order), oracle_replay(request, order)
        if actual != expected:
            raise AssertionError(f"replay mismatch: {request!r}, {order!r}")
        count += 1
    if len(ids) <= 3:
        bundle = produce(request)
        if verify(bundle)["status"] != "verified-bounded":
            raise AssertionError(f"unexpected verifier result: {request!r}")
        paths = bundle["paths"]
        records = ([paths["forward"], paths["exchanged"]] if len(ids) == 2
                   else paths["left"] + paths["right"])
        for record in records:
            if record != oracle_replay(request, tuple(record["order"])):
                raise AssertionError(f"producer path mismatch: {request!r}")
        if not paths["equivalent"]:
            raise AssertionError(f"unexpected terminal divergence: {request!r}")
    return count


def main() -> int:
    topology_cases = topology_orders = 0
    for size in range(4):
        base = [{"id": f"b{i}", "value": f"B{i}"} for i in range(size)]
        anchors = [ROOT] + [item["id"] for item in base]
        for count in range(2, 5):
            for assignment in product(anchors, repeat=count):
                operations = [{"id": f"o{i}", "kind": "insert",
                               "anchorId": anchor, "newId": f"n{i}",
                               "value": f"N{i}"}
                              for i, anchor in enumerate(assignment)]
                request = {"model": VERSION, "base": base,
                           "operations": operations}
                topology_orders += check_request(request)
                topology_cases += 1

    rng = random.Random(19351)
    random_cases = random_orders = 0
    alphabets = ("a", "Z", "é", "Ω", "🐍", " a ")
    for case in range(1000):
        size, count = rng.randrange(4), rng.randrange(2, 5)
        base = [{"id": f"b{i}-{rng.choice(alphabets)}",
                 "value": rng.choice(("", "zero", "été", "🐍"))}
                for i in range(size)]
        anchors = [ROOT] + [item["id"] for item in base]
        operations = [{"id": f"op{i}-{rng.choice(alphabets)}",
                       "kind": "insert", "anchorId": rng.choice(anchors),
                       "newId": f"new{case}-{i}-{rng.choice(alphabets)}",
                       "value": rng.choice(("", "one", "Ω", "🐍"))}
                      for i in range(count)]
        rng.shuffle(operations)
        request = {"model": VERSION, "base": base,
                   "operations": operations}
        random_orders += check_request(request)
        random_cases += 1

    paths = [Path("scripts/crosscheck_m3_oracle.py"),
             Path("agent_braid/structured_exchange.py")]
    print(json.dumps({"format": "m3-oracle-crosscheck-v1",
                      "inputs": {str(path): sha256(path.read_bytes()).hexdigest()
                                 for path in paths},
                      "python": sys.version.split()[0],
                      "platform": platform.platform(),
                      "topologyCases": topology_cases,
                      "topologyOrders": topology_orders,
                      "seededCases": random_cases,
                      "seededOrders": random_orders,
                      "mismatches": 0,
                      "limits": [
                          "Fixed 0..3 base / 2..4 insert topology corpus plus 1000 seeded bounded cases.",
                          "Oracle uses rank keys instead of the production anchor buckets.",
                          "Same author and machine; not independent scientific validation.",
                          "Only the named pure model, final sequence and physical residual trace are checked.",
                      ]}, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
