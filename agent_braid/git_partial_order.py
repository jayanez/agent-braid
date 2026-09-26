# SPDX-License-Identifier: AGPL-3.0-only
"""Private finite partial-order experiment for fixed Git patch replay.

The public replay evidence and advisory planner remain exhaustive. This module
measures selected Git replays against a separately regenerated baseline using
the existing verifier and shared replay implementation.
"""

from __future__ import annotations

from itertools import combinations

from . import git_replay
from .git_process import GitInfrastructureFailure


LIMITS = [
    "Only two to four fixed Git commit patches and tracked-tree-v1 terminal observations.",
    "Path-disjointness is syntactic; it does not establish semantic independence or arbitrary interleaving safety.",
    "All admissible orders are generated; only isolated Git replays are reduced.",
    "The exhaustive oracle and selected experiment have separate per-call Git budgets, not one aggregate budget.",
    "No reduced result authorizes preparation waves, execution, integration or ref promotion.",
]


def _overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + "/") or right.startswith(left + "/")


def _prerequisites(identifier: str, dependencies: dict[str, set[str]]) -> set[str]:
    found: set[str] = set()
    pending = list(dependencies[identifier])
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(dependencies[current])
    return found


def _independent_pairs(operations: list[dict], provenance: list[dict],
                       supported: dict[str, bool]) -> set[tuple[str, str]]:
    identifiers = sorted(item["instanceId"] for item in operations)
    dependencies = {item["instanceId"]: set(item["dependencies"])
                    for item in operations}
    ancestors = {identifier: _prerequisites(identifier, dependencies)
                 for identifier in identifiers}
    observed = {item["instanceId"]: item for item in provenance}
    paths = {identifier: {change["path"] for change in observed[identifier]["changes"]}
             for identifier in identifiers}
    pairs = set()
    for left, right in combinations(identifiers, 2):
        if not supported[left] or not supported[right]:
            continue
        if left in ancestors[right] or right in ancestors[left]:
            continue
        if any(_overlap(first, second) for first in paths[left] for second in paths[right]):
            continue
        pairs.add((left, right))
    return pairs


def _partition(operations: list[dict], provenance: list[dict],
               supported: dict[str, bool]) -> dict:
    """Group every topological order by legal adjacent independent swaps."""
    orders = {tuple(order) for order in git_replay._topological_orders(operations)}
    independent = _independent_pairs(operations, provenance, supported)
    unseen = set(orders)
    classes = []
    while unseen:
        pending = [min(unseen)]
        component = set()
        while pending:
            order = pending.pop()
            if order not in unseen:
                continue
            unseen.remove(order)
            component.add(order)
            for index in range(len(order) - 1):
                if tuple(sorted((order[index], order[index + 1]))) not in independent:
                    continue
                swapped = list(order)
                swapped[index], swapped[index + 1] = swapped[index + 1], swapped[index]
                neighbour = tuple(swapped)
                if neighbour in orders and neighbour in unseen:
                    pending.append(neighbour)
        representative = min(component)
        classes.append({
            "representative": list(representative),
            "orders": [list(order) for order in sorted(component)],
        })
    classes.sort(key=lambda item: item["representative"])
    return {
        "classes": classes,
        "representatives": [item["representative"] for item in classes],
        "independentPairs": [list(pair) for pair in sorted(independent)],
        "orderCount": len(orders),
        "replayCount": len(classes),
    }


def _inconclusive(reason: str, oracle: dict | None = None,
                  partition: dict | None = None) -> dict:
    return {
        "status": "inconclusive",
        "reason": reason,
        "oracleResult": oracle["result"] if oracle else None,
        "oracleEvidence": oracle,
        "partition": partition,
        "representativeSchedules": [],
        "executionAuthorization": False,
        "limits": LIMITS,
    }


def _classes_agree(partition: dict, schedules: list[dict]) -> bool:
    by_order = {tuple(item["order"]): item for item in schedules}
    for component in partition["classes"]:
        signatures = {(by_order[tuple(order)]["status"],
                       by_order[tuple(order)]["finalTree"])
                      for order in component["orders"]}
        if len(signatures) != 1:
            return False
    return True


def compare(request: object) -> dict:
    """Replay selected orders privately and compare them to a full verified oracle."""
    oracle = None
    partition = None
    try:
        oracle = git_replay._build_evidence(request)
        repository = request["repository"]
        verification = git_replay.verify(oracle, repository)
        if verification.get("status") != "verified":
            return _inconclusive("existing verifier did not reproduce exhaustive evidence", oracle)

        pinned = git_replay._normalized_request({**oracle, "repositoryPath": repository})
        selected: dict = {}

        def choose_orders(normalized: dict, provenance: dict,
                          patches: dict[str, bytes], supported: dict[str, bool]
                          ) -> list[list[str]]:
            del patches  # Support and path observations have already been checked.
            partition = _partition(normalized["operations"],
                                   provenance["operations"], supported)
            selected["partition"] = partition
            return partition["representatives"]

        probe = git_replay._build_evidence(pinned, order_selector=choose_orders)
        partition = selected["partition"]
        metadata = set(oracle) - {"schedules", "result", "evidenceDigest"}
        if any(probe[field] != oracle[field] for field in metadata):
            return _inconclusive("source provenance changed during selected replay",
                                 oracle, partition)

        by_order = {tuple(item["order"]): item for item in oracle["schedules"]}
        selected_by_order = {tuple(item["order"]): item for item in probe["schedules"]}
        if set(selected_by_order) != {tuple(item) for item in partition["representatives"]}:
            return _inconclusive("selected replay omitted or duplicated a representative",
                                 oracle, partition)
        if any(selected_by_order[order] != by_order[order] for order in selected_by_order):
            return _inconclusive("selected replay disagreed with its oracle schedule",
                                 oracle, partition)

        if not _classes_agree(partition, oracle["schedules"]):
            return {
                **_inconclusive("an independent-swap class has different oracle outcomes",
                                oracle, partition),
                "status": "counterexample",
                "representativeSchedules": probe["schedules"],
            }

        return {
            "status": "matched" if oracle["result"] != "inconclusive" else "oracle-inconclusive",
            "reason": "selected replays and every finite exhaustive-baseline class agree",
            "oracleResult": oracle["result"],
            "oracleEvidence": oracle,
            "partition": partition,
            "representativeSchedules": probe["schedules"],
            "executionAuthorization": False,
            "limits": LIMITS,
        }
    except (git_replay.InvalidGitReplay, GitInfrastructureFailure,
            KeyError, TypeError, ValueError, OSError) as exc:
        return _inconclusive(str(exc), oracle, partition)
