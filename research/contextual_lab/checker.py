# SPDX-License-Identifier: AGPL-3.0-only
"""Source-bound finite continuation checks using the unchanged integer interpreter."""
from copy import deepcopy
import hashlib
from pathlib import Path

from research.lab import model
from research.lab.model import Invalid, canonical, digest, require

VERSION = "contextual-continuations-v1"
REQUEST_BYTES = 8_000_000
REPORT_BYTES = 16_000_000
ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATHS = (
    "CONSTITUTION.md", "docs/adr/0005-evidence-contracts-and-bounded-laboratory.md",
    "docs/adr/0017-bounded-structured-exchange.md", "docs/theory/OPERATIONAL_SEMANTICS.md",
    "research/lab/model.py", "research/contextual_lab/__init__.py",
    "research/contextual_lab/checker.py", "research/contextual_lab/__main__.py",
    "specs/025-contextual-proof-obligations/premise-inventory.json",
    "specs/025-contextual-proof-obligations/contracts/continuations-v1.md",
)


def _read_sources():
    return {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in SOURCE_PATHS}


_LOADED_SOURCES = _read_sources()


def source_bindings():
    """Refuse source drift beneath already loaded interpreter/checker code."""
    current = _read_sources()
    require(current == _LOADED_SOURCES, "loaded source bytes changed")
    return current


def load(path, maximum=REQUEST_BYTES):
    with Path(path).open("rb") as stream:
        data = stream.read(maximum + 1)
    require(len(data) <= maximum, "artifact byte cap")
    return model.loads(data.decode("utf-8"))


def _order(order, ids):
    require(isinstance(order, list) and all(isinstance(x, str) for x in order), "invalid fragment")
    require(len(order) == len(set(order)), "repeated original instance")
    require(set(order) <= ids, "unknown original instance")


def _admissible(order, definitions):
    consumed = set()
    for identifier in order:
        require(set(definitions[identifier]["dependencies"]) <= consumed, "fragment dependency order")
        consumed.add(identifier)


def _validate(request):
    require(len(canonical(request)) <= REQUEST_BYTES, "request byte cap")
    model.record(request, ["requestVersion", "fixture", "leftPrefix", "rightPrefix",
                           "suffixes", "caps", "sourceBindings"])
    require(request["requestVersion"] == VERSION, "unknown contextual version")
    require(request["sourceBindings"] == source_bindings(), "source binding mismatch")
    fixture = model.validate_fixture(request["fixture"])
    definitions = {op["id"]: op for op in fixture["operations"]}
    ids = set(definitions)
    for key in ("leftPrefix", "rightPrefix"):
        _order(request[key], ids)
        _admissible(request[key], definitions)
    consumed = set(request["leftPrefix"])
    require(consumed == set(request["rightPrefix"]), "different consumed instances")
    suffixes = request["suffixes"]
    require(isinstance(suffixes, list) and 1 <= len(suffixes) <= 720, "suffix count cap")
    for suffix in suffixes:
        _order(suffix, ids - consumed)
        _admissible(request["leftPrefix"] + suffix, definitions)
        _admissible(request["rightPrefix"] + suffix, definitions)
    require([] in suffixes, "empty suffix required")
    require(len({tuple(s) for s in suffixes}) == len(suffixes), "duplicate suffix")
    model.record(request["caps"], ["checks", "steps"])
    for key, limit in (("checks", 20_000), ("steps", 120_000)):
        require(type(request["caps"][key]) is int and 0 <= request["caps"][key] <= limit,
                "invalid logical budget")
    return fixture, definitions, sorted(suffixes, key=lambda s: (len(s), tuple(s)))


class _Exhausted(Exception):
    def __init__(self, reason):
        self.reason = reason


class _Budget:
    def __init__(self, fixture, caps):
        self.fixture = fixture
        self.definitions = {op["id"]: op for op in fixture["operations"]}
        self.caps = caps
        self.checks = self.steps = self.actual_replays = self.cache_hits = 0
        self.cache = {}

    def logical(self):
        if self.checks >= self.caps["checks"]:
            raise _Exhausted("logical-check-cap")
        self.checks += 1

    def preflight_block(self, evaluations):
        # A block is retained atomically. Reserve conservative logical/step work
        # before executing it so cap exhaustion never drops an executed trace.
        if self.checks + len(evaluations) > self.caps["checks"]:
            raise _Exhausted("logical-check-cap")
        distinct = {tuple(order) for order in evaluations if order is not None}
        fresh_steps = sum(len(order) for order in distinct if order not in self.cache)
        if self.steps + fresh_steps > self.caps["steps"]:
            raise _Exhausted("modeled-step-cap")

    def plan(self, order):
        consumed = set(order)
        return [order] + [order + [identifier]
                         if set(self.definitions[identifier]["dependencies"]) <= consumed else None
                         for identifier in sorted(set(self.definitions) - consumed)]

    def replay(self, order):
        self.logical()  # All cache hits consume logical budget too.
        key = tuple(order)
        if key in self.cache:
            self.cache_hits += 1
            return deepcopy(self.cache[key])
        if self.steps + len(order) > self.caps["steps"]:
            raise _Exhausted("modeled-step-cap")
        if order:
            fixture = {**self.fixture, "operations": [self.definitions[i] for i in order]}
            outcome = model.run(fixture, order)
            self.actual_replays += 1
            self.steps += len(outcome["events"]) + (outcome["status"] != "complete")
        else:
            outcome = {"status": "complete", "reason": "", "state": deepcopy(self.fixture["state"]),
                       "versions": deepcopy(self.fixture["versions"]), "results": {}, "events": [], "pending": []}
        # Restore the full pending inventory before any exact observation.
        outcome["pending"] += sorted(set(self.definitions) - set(order))
        self.cache[key] = deepcopy(outcome)
        return outcome

    def enabledness(self, order):
        rows = {}
        consumed = set(order)
        for identifier in sorted(set(self.definitions) - consumed):
            op = self.definitions[identifier]
            if not set(op["dependencies"]) <= consumed:
                self.logical()
                rows[identifier] = {"status": "blocked", "reason": "unmet dependency", "outcome": None,
                                    "outcomeHash": None, "fragmentOutcome": None, "fragmentOutcomeHash": None}
                continue
            outcome = self.replay(order + [identifier])
            fragment = _fragment_outcome(outcome, order + [identifier])
            rows[identifier] = {"status": "enabled" if outcome["status"] == "complete" else outcome["status"],
                                "reason": outcome["reason"], "outcome": outcome, "outcomeHash": digest(outcome),
                                "fragmentOutcome": fragment, "fragmentOutcomeHash": digest(fragment)}
        return rows


def _fragment_outcome(outcome, order):
    fragment = deepcopy(outcome)
    fragment["pending"] = [identifier for identifier in outcome["pending"] if identifier in set(order)]
    return fragment


def _configuration_bound(fixture):
    """ASCII byte upper bound for any canonical retained original-model outcome."""
    resources = fixture["state"]
    ids = [op["id"] for op in fixture["operations"]]
    worst = {
        "status": "complete", "reason": "x" * 8192,
        "state": {r: -model.LIMIT for r in resources},
        "versions": {r: model.LIMIT for r in resources},
        "results": {i: -model.LIMIT for i in ids}, "pending": ids,
        "events": [{"id": op["id"], "kind": op["kind"], "resource": op["target"],
                    "value": -model.LIMIT, "reads": {r: model.LIMIT for r in resources},
                    "writes": [op["target"]]} for op in fixture["operations"]],
    }
    return len(canonical(worst))


def _finish(report, budget, reason=None, location=None):
    if reason is not None:
        report["coverage"]["capReason"] = reason
        report["coverage"]["capLocation"] = location
        report["verdict"] = "inconclusive"
    report["costs"] = {"checks": budget.checks, "steps": budget.steps,
                       "actualReplays": budget.actual_replays, "cacheHits": budget.cache_hits}
    report["coverage"]["completed"] = len(report["checks"])
    report["coverage"]["unvisited"] = list(range(len(report["checks"]), report["coverage"]["requested"]))
    require(source_bindings() == report["sourceBindings"], "source drift during check")
    report["reportHash"] = digest(report)
    require(len(canonical(report)) <= REPORT_BYTES, "final report byte ceiling")
    return report


def _reserve(report, configuration_bound, count):
    # Fixed metadata/slack covers witness references, counters and final hash.
    required = len(canonical(report)) + 32_768 + count * configuration_bound + 4096
    if required > REPORT_BYTES:
        raise _Exhausted("report-byte-cap")
    return count * configuration_bound + 4096


def _enable_observation(rows):
    return {i: {"status": row["status"], "reason": row["reason"]} for i, row in rows.items()}


def _raw_differences(left, right):
    return [key for key in ("state", "versions", "results", "events", "pending", "status", "reason")
            if left[key] != right[key]]


def check(request):
    """Check only listed continuations and remaining enabledness; never authorize."""
    fixture, definitions, suffixes = _validate(request)
    request = deepcopy(request)
    bound = _configuration_bound(fixture)
    budget = _Budget(fixture, request["caps"])
    remaining_ids = sorted(set(definitions) - set(request["leftPrefix"]))
    unavailable = {"available": False, "reason": "not-evaluated", "outcome": None,
                   "outcomeHash": None, "fragmentOutcome": None, "fragmentOutcomeHash": None}
    probe_unavailable = {"status": "unavailable", "reason": "not-evaluated", "outcome": None,
                         "outcomeHash": None, "fragmentOutcome": None, "fragmentOutcomeHash": None}
    report = {"reportVersion": VERSION, "request": request, "requestHash": digest(request),
              "sourceBindings": source_bindings(),
              "prefixes": {side: deepcopy(unavailable) for side in ("left", "right")},
              "initialEnabledness": {side: {i: deepcopy(probe_unavailable) for i in remaining_ids}
                                    for side in ("left", "right")},
              "checks": [], "coverage": {"requested": len(suffixes), "completed": 0,
                                          "unvisited": list(range(len(suffixes))), "capReason": None, "capLocation": None,
                                          "prelude": {"prefixes": {side: "unvisited" for side in ("left", "right")},
                                                      "initialProbes": {side: {i: "unvisited" for i in remaining_ids}
                                                                        for side in ("left", "right")}},
                                          "ordering": "length-then-lexical"},
              "costs": {}, "verdict": "inconclusive", "witness": None,
              "executionAuthorization": False, "proofAccepted": False,
              "limits": "Finite named observation/enablement product only; no theorem or universal equivalence."}
    require(len(canonical(report)) + 32_768 <= REPORT_BYTES, "minimum report envelope byte ceiling")
    location = {"phase": "prefix-and-initial-probe-preparation"}
    try:
        remaining = len(definitions) - len(request["leftPrefix"])
        reserved = _reserve(report, bound, 4 + 4 * remaining)
        budget.preflight_block(budget.plan(request["leftPrefix"]) + budget.plan(request["rightPrefix"]))
        prefixes, enabled = {}, {}
        for side, key in (("left", "leftPrefix"), ("right", "rightPrefix")):
            outcome = budget.replay(request[key])
            require(outcome["status"] == "complete" and set(outcome["results"]) == set(request[key]),
                    "prefix is not successfully reachable")
            fragment = _fragment_outcome(outcome, request[key])
            prefixes[side] = {"available": True, "reason": "replayed", "outcome": outcome, "outcomeHash": digest(outcome),
                              "fragmentOutcome": fragment, "fragmentOutcomeHash": digest(fragment)}
            enabled[side] = budget.enabledness(request[key])
        require(len(canonical({"prefixes": prefixes, "enabled": enabled})) <= reserved,
                "prefix reservation bound violation")
        report["prefixes"], report["initialEnabledness"] = prefixes, enabled
        report["coverage"]["prelude"] = {"prefixes": {side: "completed" for side in ("left", "right")},
                                          "initialProbes": {side: {i: "completed" for i in remaining_ids}
                                                            for side in ("left", "right")}}
        has_failure = any(r["status"] == "error" for rows in enabled.values() for r in rows.values())
        divergent = False
        for index, suffix in enumerate(suffixes):
            location = {"phase": "listed-suffix", "index": index}
            remaining_after = remaining - len(suffix)
            reserved = _reserve(report, bound, 6 + 4 * remaining_after)
            budget.preflight_block(budget.plan(request["leftPrefix"] + suffix)
                                   + budget.plan(request["rightPrefix"] + suffix) + [None])
            outputs, fragments, observations, enable_rows = {}, {}, {}, {}
            unavailable = []
            for side, key in (("left", "leftPrefix"), ("right", "rightPrefix")):
                order = request[key] + suffix
                outcome = budget.replay(order)
                outputs[side] = outcome
                fragments[side] = _fragment_outcome(outcome, order)
                observations[side] = model.observe(outcome, fixture["observation"])
                if outcome["status"] == "complete":
                    enable_rows[side] = budget.enabledness(order)
                    has_failure |= any(r["status"] == "error" for r in enable_rows[side].values())
                else:
                    has_failure = True
                    enable_rows[side] = None
                    unavailable.append(side + ":listed-fragment-" + outcome["status"])
            budget.logical()  # Pair comparison is logical work, even for cached sides.
            products = {side: {"observation": observations[side],
                               "enabledness": _enable_observation(enable_rows[side])
                               if enable_rows[side] is not None else None} for side in ("left", "right")}
            differs = products["left"] != products["right"]
            row = {"index": index, "suffix": suffix, "outcomes": outputs,
                   "fragmentOutcomes": fragments,
                   "fragmentOutcomeHashes": {side: digest(value) for side, value in fragments.items()},
                   "outcomeHashes": {side: digest(value) for side, value in outputs.items()},
                   "observations": observations,
                   "observationHashes": {side: digest(value) for side, value in observations.items()},
                   "enabledness": enable_rows, "comparison": "different" if differs else "matching",
                   "unavailable": unavailable, "rawDifferences": _raw_differences(outputs["left"], outputs["right"])}
            require(len(canonical(row)) <= reserved, "check reservation bound violation")
            report["checks"].append(row)
            if differs:
                divergent = True
                if report["witness"] is None:
                    report["witness"] = {"checkIndex": index, "suffix": suffix,
                                         "minimality": "shortest-then-lexical registered suffix"}
        report["verdict"] = "inconclusive" if has_failure else (
            "divergent" if divergent else "equivalent-for-listed-continuations")
        require(source_bindings() == report["sourceBindings"], "source drift during check")
        return _finish(report, budget)
    except _Exhausted as exc:
        return _finish(report, budget, exc.reason, location)


def verify(report):
    """Recompute all bounded bytes; verification supplies no proof or permission."""
    try:
        require(len(canonical(report)) <= REPORT_BYTES, "report input byte ceiling")
        require(isinstance(report, dict) and "request" in report, "missing report request")
        recomputed = check(report["request"])
        require(canonical(report) == canonical(recomputed), "report replay mismatch")
        return {"status": "verified", "verdict": recomputed["verdict"],
                "executionAuthorization": False, "proofAccepted": False}
    except (Invalid, ValueError, TypeError, KeyError, RecursionError, OSError):
        return {"status": "rejected", "reason": "bounded replay or source mismatch",
                "executionAuthorization": False, "proofAccepted": False}
