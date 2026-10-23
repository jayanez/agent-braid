# SPDX-License-Identifier: AGPL-3.0-only
"""Closed, private, bounded workload transitions; no external execution."""

from copy import deepcopy
import hashlib
import json

MODEL = "effectful-workload-simulation-v1"
LIMIT = 2**63 - 1
INPUT_BYTES = 8 * 1024 * 1024
READ_KINDS = frozenset({"snapshot-read", "config-read"})
WRITE_KINDS = frozenset({"literal-write", "derived-write", "guarded-write", "add-constant"})
KINDS = READ_KINDS | WRITE_KINDS | {"external-action"}


class InvalidWorkload(ValueError):
    """A request or internal call is outside the closed contract."""


def _require(condition, reason):
    if not condition:
        raise InvalidWorkload(reason)


def _scalar(value):
    _require(type(value) is str, "expected string")
    _require(not any(0xD800 <= ord(c) <= 0xDFFF for c in value), "invalid Unicode scalar string")


def _json(value, depth=0):
    _require(depth <= 64, "JSON nesting exceeds 64")
    if value is None or type(value) is bool:
        return
    if type(value) is str:
        _scalar(value)
    elif type(value) is int:
        _integer(value)
    elif type(value) is list:
        for item in value:
            _json(item, depth + 1)
    elif type(value) is dict:
        for key, item in value.items():
            _scalar(key)
            _json(item, depth + 1)
    else:
        raise InvalidWorkload("unsupported JSON type")


def canonical(value):
    """Return bounded-integer JSON as sorted compact ASCII bytes."""
    try:
        _json(value)
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False).encode("ascii")
    except (RecursionError, UnicodeError) as exc:
        raise InvalidWorkload("invalid JSON value") from exc


def digest(value):
    """Return the bare SHA-256 hex digest of canonical bytes."""
    return hashlib.sha256(canonical(value)).hexdigest()


def loads(text, limit=INPUT_BYTES):
    """Parse strict JSON under an explicit transport byte limit (8 MiB default)."""
    def pairs(items):
        result = {}
        for key, value in items:
            _require(key not in result, "duplicate JSON member")
            result[key] = value
        return result

    def reject(value):
        raise InvalidWorkload("floating/nonfinite JSON numbers are forbidden")

    try:
        _require(type(limit) is int and limit >= 0, "byte limit must be a nonnegative integer")
        _require(type(text) in (str, bytes), "expected JSON text")
        encoded = text.encode("utf-8") if type(text) is str else text
        _require(len(encoded) <= limit, "input exceeds byte limit")
        # Decode bytes strictly: json.loads otherwise admits UTF-16/UTF-32 bytes.
        decoded = encoded.decode("utf-8")
        value = json.loads(decoded, object_pairs_hook=pairs,
                           parse_float=reject, parse_constant=reject)
        canonical(value)
        return value
    except (ValueError, TypeError, RecursionError, UnicodeError) as exc:
        raise InvalidWorkload(str(exc)) from exc


def _record(value, required, optional=()):
    _require(type(value) is dict, "expected object")
    _require(set(required) <= value.keys() <= set(required) | set(optional), "missing or unknown fields")


def _integer(value, minimum=-LIMIT, maximum=LIMIT):
    _require(type(value) is int and minimum <= value <= maximum, "integer outside bounds")


def _name(value):
    _scalar(value)
    _require(0 < len(value) <= 256, "name length outside bounds")


def _names(value, maximum=None):
    _require(type(value) is list, "expected name list")
    if maximum is not None:
        _require(len(value) <= maximum, "too many names")
    for item in value:
        _name(item)
    _require(len(value) == len(set(value)), "duplicate name")


def resolve(initial, name):
    """Resolve one name through immutable initial aliases to a resource."""
    _name(name)
    seen = set()
    while name not in initial["state"]:
        _require(name not in seen and name in initial["aliases"], "cyclic or missing alias target")
        seen.add(name)
        name = initial["aliases"][name]
        _name(name)
    return name


def _expression(expr, depth=0):
    _require(depth <= 12, "expression depth exceeds 12")
    _require(type(expr) is dict, "expected expression")
    if set(expr) == {"int"}:
        _integer(expr["int"])
        return set()
    if set(expr) == {"result"}:
        _name(expr["result"])
        return {expr["result"]}
    _record(expr, {"op", "left", "right"})
    _require(expr["op"] in ("add", "subtract", "multiply"), "unknown expression opcode")
    return _expression(expr["left"], depth + 1) | _expression(expr["right"], depth + 1)


def _references(operation):
    refs = set()
    if "expression" in operation:
        refs |= _expression(operation["expression"])
    if "guard" in operation:
        guard = operation["guard"]
        _record(guard, {"op", "left", "right"})
        _require(guard["op"] in ("eq", "lt", "le"), "unknown guard opcode")
        refs |= _expression(guard["left"]) | _expression(guard["right"])
    return refs


def validate(request):
    """Validate the complete closed grammar and return an independent copy."""
    _require(len(canonical(request)) <= INPUT_BYTES, "input exceeds 8 MiB")
    _record(request, {"model", "initial", "operations", "observation", "caps"})
    _require(request["model"] == MODEL, "unknown workload model")
    initial = request["initial"]
    _record(initial, {"state", "versions", "aliases"})
    state, versions, aliases = (initial[k] for k in ("state", "versions", "aliases"))
    _require(type(state) is dict and 1 <= len(state) <= 64, "resource count outside bounds")
    _require(type(versions) is dict and set(versions) == set(state), "versions must match resources")
    _require(type(aliases) is dict and len(aliases) <= 64, "alias count outside bounds")
    for key, value in state.items():
        _name(key)
        _integer(value)
        _integer(versions[key], 0)
    for key, target in aliases.items():
        _name(key)
        _name(target)
        _require(key not in state, "alias shadows resource")
        resolve(initial, key)
    operations = request["operations"]
    _require(type(operations) is list and 1 <= len(operations) <= 6, "operation count outside bounds")
    ids = {}
    for operation in operations:
        _require(type(operation) is dict, "expected operation")
        kind = operation.get("kind")
        _require(type(kind) is str and kind in KINDS, "unknown operation kind")
        fields = {
            "literal-write": {"value"}, "add-constant": {"amount"},
            "guarded-write": {"expression", "guard"},
            "derived-write": {"expression"}, "external-action": {"event"},
        }.get(kind, set())
        optional = {"requiredVersion", "effects"} | ({"idempotencyKey"} if kind == "external-action" else set())
        _record(operation, {"id", "kind", "resource", "dependencies", "outcomes"} | fields, optional)
        _name(operation["id"])
        _require(operation["id"] not in ids, "duplicate operation ID")
        ids[operation["id"]] = operation
        resolve(initial, operation["resource"])
        _names(operation["dependencies"], 5)
        outcomes = operation["outcomes"]
        _names(outcomes, 2)
        allowed = {"success", "error"} | ({"send-then-error"} if kind == "external-action" else set())
        _require(1 <= len(outcomes) <= 2 and set(outcomes) <= allowed, "invalid outcomes")
        if "requiredVersion" in operation:
            _integer(operation["requiredVersion"], 0)
        if kind == "literal-write":
            _integer(operation["value"])
        if kind == "add-constant":
            _integer(operation["amount"])
        if kind == "external-action":
            _name(operation["event"])
            if "idempotencyKey" in operation:
                _name(operation["idempotencyKey"])
        _references(operation)
        if "effects" in operation:
            effects = operation["effects"]
            _record(effects, {"complete", "reads", "writes", "emits"})
            _require(type(effects["complete"]) is bool, "complete must be boolean")
            for category in ("reads", "writes", "emits"):
                _names(effects[category])
                for resource in effects[category]:
                    resolve(initial, resource)
    closures = {}

    def closure(identifier, active):
        _require(identifier in ids and identifier not in active, "missing dependency or dependency cycle")
        if identifier in closures:
            return closures[identifier]
        result = set()
        for dependency in ids[identifier]["dependencies"]:
            result.add(dependency)
            result |= closure(dependency, active | {identifier})
        closures[identifier] = result
        return result

    for identifier, operation in ids.items():
        ancestors = closure(identifier, set())
        for reference in _references(operation):
            _require(reference in ancestors and ids[reference]["kind"] in READ_KINDS,
                     "capture must reference a transitively dependent read operation")
    observation = request["observation"]
    _require(type(observation) is dict, "expected observation")
    if observation.get("mode") == "exact":
        _record(observation, {"mode"})
    else:
        _record(observation, {"mode", "resources"})
        _require(observation["mode"] == "selected-values", "unknown observation mode")
        _names(observation["resources"], 64)
        resources = [resolve(initial, name) for name in observation["resources"]]
        _require(len(set(resources)) == len(resources), "duplicate canonical observation resource")
    caps = request["caps"]
    _record(caps, {"paths", "steps", "events"})
    for key, bound in (("paths", 20000), ("steps", 120000), ("events", 240000)):
        _integer(caps[key], 0, bound)
    return deepcopy(request)


def initial_config(request):
    """Create a fresh configuration; pending may be replaced by a chosen order."""
    request = validate(request)
    return {**deepcopy(request["initial"]), "results": {}, "events": [],
            "idempotencyLedger": [], "pending": sorted(op["id"] for op in request["operations"]),
            "outcome": "success", "reason": None}


def footprint(request, operation):
    """Return actual canonical read/write/emit resource sets, including captures."""
    resource = resolve(request["initial"], operation["resource"])
    result = {"reads": set(), "writes": set(), "emits": set()}
    kind = operation["kind"]
    if kind in READ_KINDS or kind in ("add-constant", "external-action") or "requiredVersion" in operation:
        result["reads"].add(resource)
    if kind in WRITE_KINDS:
        result["writes"].add(resource)
    if kind == "external-action":
        result["emits"].add(resource)
    operations = {op["id"]: op for op in request["operations"]}
    for reference in _references(operation):
        result["reads"].add(resolve(request["initial"], operations[reference]["resource"]))
    return result


def declared_effects(request, operation):
    """Expose conservative declarations and explicit completeness uncertainty."""
    effects = operation.get("effects")
    reasons = []
    declared = {key: [] for key in ("reads", "writes", "emits")}
    if effects is None:
        reasons.append("missing-declaration")
    else:
        for key in declared:
            declared[key] = sorted({resolve(request["initial"], name) for name in effects[key]})
        if not effects["complete"]:
            reasons.append("incomplete-declaration")
        for key, actual in footprint(request, operation).items():
            if not actual <= set(declared[key]):
                reasons.append("missing-" + key)
    return {"known": not reasons, **declared, "reasons": reasons}


class _Blocked(Exception):
    pass


class _Overflow(Exception):
    pass


def _evaluate(expr, results):
    if "int" in expr:
        return expr["int"]
    if "result" in expr:
        if expr["result"] not in results:
            raise _Blocked("missing-capture")
        return results[expr["result"]]
    left = _evaluate(expr["left"], results)
    right = _evaluate(expr["right"], results)
    operator = expr["op"]
    value = left + right if operator == "add" else left - right if operator == "subtract" else left * right
    if abs(value) > LIMIT:
        raise _Overflow("arithmetic-overflow")
    return value


def step(request, config, operation_id, branch):
    """Apply one chosen atomic branch to a private copy, preserving prior effects."""
    operations = {op["id"]: op for op in request["operations"]}
    _require(operation_id in operations, "unknown operation ID")
    _require(config["outcome"] == "success", "cannot advance terminal configuration")
    _require(config["pending"] and config["pending"][0] == operation_id, "operation is not first pending")
    operation = operations[operation_id]
    _require(branch in operation["outcomes"], "branch is not declared")
    result = deepcopy(config)
    resource = resolve(request["initial"], operation["resource"])

    def terminal(outcome, reason):
        result["outcome"], result["reason"] = outcome, reason
        if outcome == "error":
            result["pending"].pop(0)
        return result

    try:
        if any(ref not in result["results"] for ref in _references(operation)):
            raise _Blocked("missing-capture")
        if any(dep not in result["results"] for dep in operation["dependencies"]):
            raise _Blocked("unmet-dependency")
        if "requiredVersion" in operation and result["versions"][resource] != operation["requiredVersion"]:
            raise _Blocked("stale-version")
        if "guard" in operation:
            guard = operation["guard"]
            left, right = _evaluate(guard["left"], result["results"]), _evaluate(guard["right"], result["results"])
            truth = left == right if guard["op"] == "eq" else left < right if guard["op"] == "lt" else left <= right
            if not truth:
                raise _Blocked("false-guard")
        if branch == "error":
            return terminal("error", "configured-error")
        kind = operation["kind"]
        if kind in READ_KINDS:
            value = result["state"][resource]
        elif kind in WRITE_KINDS:
            if kind == "literal-write":
                value = operation["value"]
            elif kind == "add-constant":
                value = result["state"][resource] + operation["amount"]
                if abs(value) > LIMIT:
                    raise _Overflow("arithmetic-overflow")
            else:
                value = _evaluate(operation["expression"], result["results"])
            if result["versions"][resource] == LIMIT:
                raise _Overflow("version-overflow")
            result["state"][resource] = value
            result["versions"][resource] += 1
        else:
            key = operation.get("idempotencyKey")
            value = int(key is None or key not in result["idempotencyLedger"])
            if value:
                result["events"].append({"operationId": operation_id, "resource": resource,
                                         "name": operation["event"], "value": result["state"][resource],
                                         "idempotencyKey": key})
                if key is not None:
                    result["idempotencyLedger"].append(key)
        result["results"][operation_id] = value
        if branch == "send-then-error":
            return terminal("error", "send-then-error")
        result["pending"].pop(0)
        return result
    except _Blocked as exc:
        return terminal("blocked", str(exc))
    except _Overflow as exc:
        return terminal("error", str(exc))
