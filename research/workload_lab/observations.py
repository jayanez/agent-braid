# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit terminal observations and separate finite event diagnostics."""

from collections import Counter

from .model import canonical, resolve


def observe(request, configuration):
    """Project a terminal configuration without changing its retained raw body."""
    if request["observation"]["mode"] == "selected-values":
        names = sorted(resolve(request["initial"], name)
                       for name in request["observation"]["resources"])
        return {"state": {name: configuration["state"][name] for name in names},
                "outcome": configuration["outcome"]}
    return {name: configuration[name] for name in
            ("state", "versions", "results", "outcome", "events")}


def compare(request, paths, complete):
    """Return only bounded finite/projection labels and all raw mismatches."""
    configurations = [path["configuration"] for path in paths]
    dimensions = ("state", "versions", "results", "events", "outcome")
    mismatches = [name for name in dimensions
                  if len({canonical(config[name]) for config in configurations}) > 1]
    if (not complete or not configurations
            or any(config["outcome"] != "success" for config in configurations)):
        verdict = "inconclusive"
    elif len({canonical(observe(request, config)) for config in configurations}) > 1:
        verdict = "divergent"
    elif request["observation"]["mode"] == "selected-values":
        verdict = "terminal-projection-match"
    else:
        verdict = "finite-exact-match"
    return {"verdict": verdict, "mismatches": mismatches}


def trace_safety(paths, complete):
    """Report explicit event witnesses without claiming general trace safety."""
    failures, duplicates, successful_events = [], [], set()
    all_successful = bool(paths)
    for index, path in enumerate(paths):
        config = path["configuration"]
        if config["outcome"] == "error" and config["events"]:
            failures.append(index)
        counts = Counter((event["resource"], event["name"], event["idempotencyKey"])
                         for event in config["events"])
        if any(count > 1 for count in counts.values()):
            duplicates.append(index)
        if config["outcome"] == "success":
            successful_events.add(canonical(config["events"]))
        else:
            all_successful = False
    order_mismatch = len(successful_events) > 1
    if failures or duplicates or order_mismatch:
        status = "witness"
    elif not complete or not all_successful:
        status = "inconclusive"
    else:
        status = "finite-no-event-witness"
    return {"status": status, "partialFailurePaths": failures,
            "duplicateEventPaths": duplicates, "eventOrderMismatch": order_mismatch}
