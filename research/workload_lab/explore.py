# SPDX-License-Identifier: AGPL-3.0-only
"""Finite lexical schedule/branch enumeration; no external effects."""

from copy import deepcopy
from itertools import permutations, product
from math import prod

from .model import initial_config, resolve, step


def schedules(request):
    """Return every dependency-admissible lexical order (at most 720)."""
    operations = {operation["id"]: operation for operation in request["operations"]}
    orders = []
    for order in permutations(sorted(operations)):
        positions = {identifier: index for index, identifier in enumerate(order)}
        if all(positions[dependency] < positions[identifier]
               for identifier, operation in operations.items()
               for dependency in operation["dependencies"]):
            orders.append(order)
    return orders


def _emits(operation, configuration, branch):
    if operation["kind"] != "external-action" or branch == "error":
        return False
    resource = resolve(configuration, operation["resource"])
    if ("requiredVersion" in operation
            and configuration["versions"][resource] != operation["requiredVersion"]):
        return False
    key = operation.get("idempotencyKey")
    return key is None or key not in configuration["idempotencyLedger"]


def explore_paths(request):
    """Enumerate a validated request, retaining partial paths and actual counts."""
    operations = {operation["id"]: operation for operation in request["operations"]}
    orders = schedules(request)
    assigned = len(orders) * prod(len(op["outcomes"]) for op in operations.values())
    caps = request["caps"]
    paths = []
    completed = steps_used = events_used = 0
    cap_reason = None
    for order in orders:
        for branches in product(*(operations[identifier]["outcomes"] for identifier in order)):
            if len(paths) >= caps["paths"]:
                cap_reason = "paths"
                break
            configuration = initial_config(request)
            configuration["pending"] = list(order)
            trace = []
            for identifier, branch in zip(order, branches):
                operation = operations[identifier]
                if steps_used >= caps["steps"]:
                    cap_reason = "steps"
                elif _emits(operation, configuration, branch) and events_used >= caps["events"]:
                    cap_reason = "events"
                if cap_reason:
                    configuration["outcome"] = "cap-exhausted"
                    configuration["reason"] = cap_reason
                    break
                before = deepcopy(configuration)
                configuration = step(request, configuration, identifier, branch)
                steps_used += 1
                events_used += len(configuration["events"]) - len(before["events"])
                trace.append({"operationId": identifier, "branch": branch,
                              "requestedResource": operation["resource"],
                              "canonicalResource": resolve(request["initial"], operation["resource"]),
                              "before": before, "after": deepcopy(configuration)})
                if configuration["outcome"] != "success":
                    break
            paths.append({"order": list(order), "branches": list(branches),
                          "steps": trace, "configuration": configuration})
            if not cap_reason:
                completed += 1
            else:
                break
        if cap_reason:
            break
    attempted = len(paths)
    return {"paths": paths, "coverage": {
        "schedules": len(orders), "assignedPaths": assigned,
        "attemptedPaths": attempted, "completedPaths": completed,
        "partialPaths": attempted - completed,
        "unattemptedPaths": assigned - attempted,
        "unresolvedUpperBound": assigned - completed,
        "steps": steps_used, "events": events_used,
        "complete": completed == assigned, "capReason": cap_reason}}
