# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic bounded reference semantics. No eval, network or tool execution."""

from copy import deepcopy
import hashlib
from itertools import permutations
import json

MODEL = "integer-batch-v1"
EXECUTION = "integer-batch-atomic-v1"
LIMIT = 2**63 - 1
ASSUMPTIONS = ["atomic modeled operations", "no external effects", "fixed batch without retries"]


class Invalid(ValueError):
    """Invalid model, contract or artifact input."""


def require(condition, message):
    if not condition:
        raise Invalid(message)


def record(value, required, optional=()):
    require(isinstance(value, dict), "expected object")
    require(set(required) <= value.keys(), "missing fields")
    require(value.keys() <= set(required) | set(optional), "unknown fields")


def name(value):
    require(isinstance(value, str) and 0 < len(value) <= 256, "invalid identifier")


def integer(value):
    require(type(value) is int and abs(value) <= LIMIT, "integer outside signed model bound")


def json_value(value, depth=0):
    require(depth <= 64, "JSON nesting limit")
    if value is None or type(value) in (str, bool, int):
        return
    if isinstance(value, list):
        for item in value:
            json_value(item, depth + 1)
        return
    if isinstance(value, dict):
        require(all(isinstance(k, str) for k in value), "JSON keys must be strings")
        for item in value.values():
            json_value(item, depth + 1)
        return
    raise Invalid("unsupported JSON value (including float)")


def canonical(value):
    json_value(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value):
    return "sha256:" + hashlib.sha256(canonical(value)).hexdigest()


def loads(text):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result
    try:
        value = json.loads(text, object_pairs_hook=pairs)
        canonical(value)
        return value
    except (ValueError, TypeError, RecursionError) as exc:
        raise Invalid(str(exc)) from exc


def expression(expr, depth=0):
    require(depth <= 12, "expression nesting limit")
    require(isinstance(expr, dict), "expression must be an object")
    if set(expr) == {"int"}:
        integer(expr["int"])
    elif set(expr) == {"read"}:
        name(expr["read"])
    elif set(expr) == {"op", "left", "right"}:
        require(expr["op"] in ("add", "multiply"), "unknown expression opcode")
        expression(expr["left"], depth + 1)
        expression(expr["right"], depth + 1)
    else:
        raise Invalid("invalid expression grammar")


def observation_contract(observation, state):
    require(isinstance(observation, dict), "observation object required")
    if observation.get("mode") == "exact":
        record(observation, ["mode"])
    else:
        record(observation, ["mode", "resources"])
        require(observation["mode"] == "projection", "unsupported observation")
        resources = observation["resources"]
        require(isinstance(resources, list) and resources, "empty projection")
        for resource in resources:
            name(resource)
        require(len(set(resources)) == len(resources), "duplicate projection resource")
        require(set(resources) <= state.keys(), "unknown projection resource")


def validate_fixture(fixture):
    record(fixture, ["modelVersion", "state", "versions", "operations", "observation"])
    require(fixture["modelVersion"] == MODEL, "unsupported model")
    state, versions = fixture["state"], fixture["versions"]
    require(isinstance(state, dict) and 0 < len(state) <= 64, "state size must be 1..64")
    require(isinstance(versions, dict) and versions.keys() == state.keys(), "version coverage")
    for key, value in state.items():
        name(key)
        integer(value)
        require(type(versions[key]) is int and 0 <= versions[key] <= LIMIT, "invalid version")
    observation_contract(fixture["observation"], state)
    operations = fixture["operations"]
    require(isinstance(operations, list) and 1 <= len(operations) <= 6, "batch size must be 1..6")
    ids = []
    for operation in operations:
        record(operation, ["id", "kind", "target", "dependencies", "readVersions"],
               ["expression", "guard"])
        name(operation["id"])
        name(operation["target"])
        ids.append(operation["id"])
        require(operation["kind"] in ("read", "assign", "add", "multiply"), "unknown operation")
        if operation["kind"] == "read":
            require("expression" not in operation, "read has no expression")
        else:
            require("expression" in operation, "missing expression")
            expression(operation["expression"])
        if "guard" in operation:
            guard = operation["guard"]
            record(guard, ["op", "left", "right"])
            require(guard["op"] in ("eq", "le"), "unknown guard")
            expression(guard["left"])
            expression(guard["right"])
        deps = operation["dependencies"]
        require(isinstance(deps, list), "dependencies must be an array")
        for dep in deps:
            name(dep)
        require(len(set(deps)) == len(deps), "duplicate dependency")
        reads = operation["readVersions"]
        require(isinstance(reads, dict), "read versions must be an object")
        for key, version in reads.items():
            name(key)
            require(type(version) is int and 0 <= version <= LIMIT, "invalid read version")
    require(len(set(ids)) == len(ids), "duplicate operation ID")
    done = set()
    for operation in operations:
        require(set(operation["dependencies"]) <= set(ids), "unknown dependency")
    while len(done) < len(ids):
        ready = {o["id"] for o in operations if set(o["dependencies"]) <= done} - done
        require(bool(ready), "cyclic dependencies")
        done.update(ready)
    return fixture


def schedules(fixture):
    validate_fixture(fixture)
    operations = fixture["operations"]
    result = []
    for order in permutations(sorted(o["id"] for o in operations)):
        positions = {item: i for i, item in enumerate(order)}
        if all(positions[dep] < positions[o["id"]]
               for o in operations for dep in o["dependencies"]):
            result.append(list(order))
    return result


def run(fixture, order):
    validate_fixture(fixture)
    operations = {o["id"]: o for o in fixture["operations"]}
    require(isinstance(order, list) and all(isinstance(x, str) for x in order), "invalid schedule")
    require(len(order) == len(operations) and set(order) == set(operations), "incomplete schedule")
    state, versions = deepcopy(fixture["state"]), deepcopy(fixture["versions"])
    results, events = {}, []
    outcome = {"status": "complete", "reason": "", "state": state, "versions": versions,
               "results": results, "events": events, "pending": []}
    for index, identifier in enumerate(order):
        op = operations[identifier]
        reads = {}

        def read(resource):
            require(resource in state, "missing resource: " + resource)
            reads[resource] = versions[resource]
            return state[resource]

        def evaluate(expr):
            if "int" in expr:
                return expr["int"]
            if "read" in expr:
                return read(expr["read"])
            left, right = evaluate(expr["left"]), evaluate(expr["right"])
            value = left + right if expr["op"] == "add" else left * right
            integer(value)
            return value

        try:
            blocked = ""
            if not set(op["dependencies"]) <= results.keys():
                blocked = "unmet dependency"
            else:
                for resource, expected in op["readVersions"].items():
                    read(resource)
                    if versions[resource] != expected:
                        blocked = "stale read version"
                if not blocked and "guard" in op:
                    guard = op["guard"]
                    left, right = evaluate(guard["left"]), evaluate(guard["right"])
                    if not (left == right if guard["op"] == "eq" else left <= right):
                        blocked = "guard false"
            if blocked:
                outcome.update(status="blocked", reason=blocked, pending=order[index:])
                return outcome
            target, kind = op["target"], op["kind"]
            require(target in state, "missing target: " + target)
            value = read(target) if kind == "read" else evaluate(op["expression"])
            if kind in ("add", "multiply"):
                old = read(target)
                value = old + value if kind == "add" else old * value
            integer(value)
            if kind != "read":
                require(versions[target] < LIMIT, "version overflow")
                state[target] = value
                versions[target] += 1
            results[identifier] = value
            events.append({"id": identifier, "kind": kind, "resource": target,
                           "value": value, "reads": reads,
                           "writes": [] if kind == "read" else [target]})
        except Invalid as exc:
            outcome.update(status="error", reason=str(exc), pending=order[index:])
            return outcome
    return outcome


def observe(outcome, contract):
    if contract["mode"] == "exact":
        return outcome
    return {"status": outcome["status"],
            "state": {r: outcome["state"][r] for r in contract["resources"]}}


def verdict(outcomes, contract):
    require(bool(outcomes), "no observations")
    if any(o["status"] != "complete" for o in outcomes):
        return "inconclusive"
    observations = {digest(observe(o, contract)) for o in outcomes}
    return "equivalent-observed" if len(observations) == 1 else "divergent"
