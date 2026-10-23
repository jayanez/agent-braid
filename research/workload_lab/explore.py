# SPDX-License-Identifier: AGPL-3.0-only
"""Finite lexical schedule/branch enumeration; no external effects."""

from copy import deepcopy
import json
from itertools import permutations, product
from math import prod

from .model import initial_config, resolve, step

# Retained path payload budget (canonical bytes), checked incrementally so that a
# report stays below the 512 MiB CLI transport bound with room for the request.
PATH_BYTES = 256 * 1024 * 1024


def _size(value):
    """Length of the canonical encoding of an already validated value."""
    return len(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True))


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


def explore_paths(request, byte_budget=None):
    """Enumerate a validated request, retaining partial paths and actual counts.

    Besides the request caps, stop before a retained step would exceed
    ``byte_budget`` canonical bytes (``capReason`` ``"bytes"``).
    """
    if byte_budget is None:
        byte_budget = PATH_BYTES
    operations = {operation["id"]: operation for operation in request["operations"]}
    orders = schedules(request)
    assigned = len(orders) * prod(len(op["outcomes"]) for op in operations.values())
    caps = request["caps"]
    paths = []
    completed = steps_used = events_used = bytes_used = 0
    cap_reason = None
    for order in orders:
        for branches in product(*(operations[identifier]["outcomes"] for identifier in order)):
            if len(paths) >= caps["paths"]:
                cap_reason = "paths"
                break
            if bytes_used >= byte_budget:
                cap_reason = "bytes"
                break
            configuration = initial_config(request)
            configuration["pending"] = list(order)
            configuration_size = _size(configuration)
            trace = []
            for identifier, branch in zip(order, branches):
                operation = operations[identifier]
                if steps_used >= caps["steps"]:
                    cap_reason = "steps"
                elif _emits(operation, configuration, branch) and events_used >= caps["events"]:
                    cap_reason = "events"
                if not cap_reason:
                    after = step(request, configuration, identifier, branch)
                    entry = {"operationId": identifier, "branch": branch,
                             "requestedResource": operation["resource"],
                             "canonicalResource": resolve(request["initial"], operation["resource"]),
                             "before": 0, "after": 0}
                    after_size = _size(after)
                    # Skeleton with one-byte placeholders, the two bodies and a separator.
                    size = _size(entry) - 2 + configuration_size + after_size + 1
                    if bytes_used + size > byte_budget:
                        cap_reason = "bytes"
                if cap_reason:
                    configuration["outcome"] = "cap-exhausted"
                    configuration["reason"] = cap_reason
                    break
                bytes_used += size
                steps_used += 1
                events_used += len(after["events"]) - len(configuration["events"])
                entry["before"], entry["after"] = deepcopy(configuration), deepcopy(after)
                trace.append(entry)
                configuration, configuration_size = after, after_size
                if configuration["outcome"] != "success":
                    break
            path = {"order": list(order), "branches": list(branches),
                    "steps": [], "configuration": configuration}
            bytes_used += _size(path) + 1
            path["steps"] = trace
            paths.append(path)
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
