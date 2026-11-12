# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T010 (REQ-010 / SC-010): scoring rules fixed in advance for the native prompt sets.

A case is ``{id, prompt, expect}``. ``expect`` is the rule:

    {"kind": "aim" | "git",         # an accepted `units` call also satisfies "aim" (T008, FREEZE record 2)
     "baseRevision": "main",                       # git only
     "units": [{"key": "u1",
                "effects": [{"kind": "write", "resource": "README.md", "optional": false}],  # aim only
                "revision": "docs-guide",          # git only
                "dependsOn": ["u2"]}],
     "pairs": [{"left": "u1", "right": "u2", "classification": "conflicting",
                "constraints": ["serialize-or-isolate"]}]}

``attempts`` is the ordered list of ``analyze-work`` calls of one run:
``{kind, request, accepted, refusalSummary, report}``. Calls to ``plugin-status`` and
``workspaces`` are not attempts. A call is valid only if it was accepted, its kind matches,
every unit is encoded with exactly the expected resources and effect kinds (after lexical
normalization), the dependency closure matches, nothing is claimed as inferred or observed,
nothing is declared empty, and the report classifies every pair as expected. The first
attempt is the first call; a retry is the second call and counts only after a refusal.
"""

from __future__ import annotations

import itertools
import math
import re
from typing import Any

REQUIRED_HOSTS = ("claude-code", "codex", "opencode")
FIRST_ATTEMPT_MIN = 8
PROMPTS_PER_HOST = 10
REPETITIONS = 3
WRITE_LIKE = {"write", "delete", "deploy", "transform"}
_SCHEME = re.compile(r"^repo://[^/]+/(.*)$")
_ANY_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


# ----------------------------------------------------------------------------
# Lexical normalization
# ----------------------------------------------------------------------------
def normalize_resource(resource: Any) -> str | None:
    """Repository-relative path of ``repo://<workspace>/<path>`` or a bare path; None otherwise.

    Lexical only: backslashes to ``/``, ``.`` and empty segments dropped, ``..`` resolved,
    never case-folded. A path that escapes the root, is absolute or has another scheme is None.
    """
    if not isinstance(resource, str) or not resource.strip():
        return None
    match = _SCHEME.match(resource)
    if match:
        raw = match.group(1)
    elif _ANY_SCHEME.match(resource) and not re.match(r"^[A-Za-z]:[\\/]", resource):
        return None
    else:
        raw = resource
    raw = raw.replace("\\", "/")
    if raw.startswith("/"):
        return None
    parts: list[str] = []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts) or None


def normalize_revision(revision: Any) -> str | None:
    if not isinstance(revision, str) or not revision.strip():
        return None
    for prefix in ("refs/heads/", "heads/"):
        if revision.startswith(prefix):
            return revision[len(prefix):]
    return revision


# ----------------------------------------------------------------------------
# Reference requests (what a perfect host sends); used by tests and the fake-host driver
# ----------------------------------------------------------------------------
def _digest(char: str) -> str:
    return "sha256:" + char * 64


def reference_request(case: dict, repository: str = "<repository>") -> dict:
    expect = case["expect"]
    if expect["kind"] == "git":
        return {
            "gitAnalysisRequestVersion": "0.1.0-alpha",
            "repository": repository,
            "baseRevision": expect["baseRevision"],
            "operations": [
                {"instanceId": u["key"], "attemptId": u["key"] + "-1",
                 "dependencies": list(u["dependsOn"]), "uncertainPaths": [],
                 "source": {"kind": "commit", "revision": u["revision"]}}
                for u in expect["units"]
            ],
        }
    operations = []
    for index, unit in enumerate(expect["units"], 1):
        operations.append({
            "aimVersion": "0.2.0-draft",
            "instanceId": unit["key"], "attemptId": unit["key"] + "-1",
            "definition": {"id": "repository.update-file-v1", "digest": _digest(str(index))},
            "inputDigest": _digest("abcdef"[index % 6]),
            "dependencies": list(unit["dependsOn"]), "readVersions": {},
            "effects": {
                "declared": [{"kind": e["kind"], "resource": "repo://workspace/" + e["resource"]}
                             for e in unit["effects"] if not e.get("optional")],
                "inferred": [], "observed": [],
                "coverage": {"status": "complete", "domain": "exact repository paths",
                             "method": "user declaration"},
            },
            "evidence": [{"property": "independence", "method": "declared",
                          "domain": "exact repository paths",
                          "assumptions": ["no aliases or generated dependencies"],
                          "observationContract": "normalized repository tree",
                          "executionContract": "no execution; analysis only", "assuranceClass": 1}],
        })
    return {"analysisInputVersion": "0.1.0-alpha",
            "source": {"kind": "aim", "description": case["id"]}, "operations": operations}


# ----------------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------------
def _operations(kind: str, request: Any) -> list[dict] | None:
    if kind == "units":
        ops = request.get("units") if isinstance(request, dict) else None
    elif kind == "git":
        ops = request.get("operations") if isinstance(request, dict) else None
    elif isinstance(request, dict) and "operations" in request:
        ops = request["operations"]
    elif isinstance(request, dict):
        ops = [request]
    else:
        ops = request
    if not isinstance(ops, list) or not ops or not all(isinstance(o, dict) for o in ops):
        return None
    return ops


def _closure(deps: dict[str, set[str]]) -> dict[str, set[str]]:
    result = {}
    for start in deps:
        seen, stack = set(), list(deps[start])
        while stack:
            item = stack.pop()
            if item not in seen:
                seen.add(item)
                stack.extend(deps.get(item, ()))
        result[start] = seen
    return result


def _unit_effects_match(unit: dict, declared: set[tuple[str, str]]) -> bool:
    required = {(e["kind"], e["resource"]) for e in unit["effects"] if not e.get("optional")}
    allowed = {(e["kind"], e["resource"]) for e in unit["effects"]}
    allowed |= {("read", res) for kind, res in required if kind in WRITE_LIKE}  # a write implies a read
    return required <= declared <= allowed


def _describe(declared: set[tuple[str, str]]) -> str:
    return ", ".join(f"{k} {r}" for k, r in sorted(declared)) or "nothing"


def _aim_ops(ops: list[dict], reasons: list[str]) -> list[dict] | None:
    """Per-operation view of an AIM request, or None after recording why it is unusable."""
    view = []
    for op in ops:
        ident = op.get("instanceId")
        effects = op.get("effects") if isinstance(op.get("effects"), dict) else {}
        declared = effects.get("declared") if isinstance(effects.get("declared"), list) else []
        if not declared:
            reasons.append(f"operation {ident!r} declares no effect")
            return None
        if effects.get("inferred") or effects.get("observed"):
            reasons.append(f"operation {ident!r} claims inferred or observed effects")
            return None
        if any(not isinstance(i, dict) or i.get("method") != "declared" for i in op.get("evidence") or []):
            reasons.append(f"operation {ident!r} claims evidence that is not declared")
            return None
        pairs: set[tuple[str, str]] = set()
        for effect in declared:
            path = normalize_resource(effect.get("resource")) if isinstance(effect, dict) else None
            if path is None:
                reasons.append(f"operation {ident!r} has a resource outside the workspace form: "
                               f"{effect.get('resource') if isinstance(effect, dict) else effect!r}")
                return None
            pairs.add((effect.get("kind"), path))
        view.append({"id": ident, "effects": pairs, "deps": set(op.get("dependencies") or [])})
    return view


def _units_ops(ops: list[dict], reasons: list[str]) -> list[dict] | None:
    """Per-unit view of a ``units`` request (SPEC-069 REQ-006), shaped like ``_aim_ops``."""
    view = []
    for op in ops:
        ident = op.get("id")
        declared = op.get("effects") if isinstance(op.get("effects"), list) else []
        if not declared:
            reasons.append(f"unit {ident!r} declares no effect")
            return None
        pairs: set[tuple[str, str]] = set()
        for effect in declared:
            path = normalize_resource(effect.get("resource")) if isinstance(effect, dict) else None
            if path is None:
                reasons.append(f"unit {ident!r} has a resource outside the workspace form")
                return None
            pairs.add((effect.get("kind"), path))
        view.append({"id": ident, "effects": pairs, "deps": set(op.get("dependencies") or [])})
    return view


def _git_ops(ops: list[dict], expect: dict, reasons: list[str]) -> list[dict] | None:
    view = []
    for op in ops:
        source = op.get("source") if isinstance(op.get("source"), dict) else {}
        if source.get("kind") != "commit":
            reasons.append(f"operation {op.get('instanceId')!r} is not a commit source")
            return None
        view.append({"id": op.get("instanceId"), "revision": normalize_revision(source.get("revision")),
                     "deps": set(op.get("dependencies") or [])})
    return view


def _evaluate(case: dict, attempt: dict) -> list[str]:
    """Reasons the attempt fails the rule; an empty list means valid."""
    expect = case["expect"]
    if not attempt.get("accepted"):
        return ["refused: " + str(attempt.get("refusalSummary") or "no summary")]
    # A `units` call is the simple form of an `aim` case; it can only earn the classifications it can
    # report (it never yields independent-candidate), so the pair check below stays unchanged.
    kind = attempt.get("kind")
    if kind != expect["kind"] and not (kind == "units" and expect["kind"] == "aim"):
        return [f"kind {attempt.get('kind')!r} instead of {expect['kind']!r}"]
    report = attempt.get("report")
    if not isinstance(report, dict) or not isinstance(report.get("interactions"), list):
        return ["accepted call has no report"]
    request = attempt.get("request")
    ops = _operations(kind, request)
    units = expect["units"]
    if ops is None:
        return ["request has no operations"]
    if len(ops) != len(units):
        return [f"{len(ops)} operations instead of {len(units)}"]
    reasons: list[str] = []
    if expect["kind"] == "git":
        if normalize_revision(request.get("baseRevision")) != expect["baseRevision"]:
            return [f"base revision {request.get('baseRevision')!r} instead of {expect['baseRevision']!r}"]
        view = _git_ops(ops, expect, reasons)
        fits = lambda u, o: o["revision"] == u["revision"]  # noqa: E731
        describe = lambda o: f"revision {o['revision']}"  # noqa: E731
    else:
        view = _units_ops(ops, reasons) if kind == "units" else _aim_ops(ops, reasons)
        fits = lambda u, o: _unit_effects_match(u, o["effects"])  # noqa: E731
        describe = lambda o: _describe(o["effects"])  # noqa: E731
    if view is None:
        return reasons
    ids = [o["id"] for o in view]
    if len(set(ids)) != len(ids):
        return ["duplicate instanceId"]
    indexes = range(len(units))
    matching = [p for p in itertools.permutations(indexes) if all(fits(units[u], view[o]) for o, u in enumerate(p))]
    if not matching:
        wanted = [u.get("revision") or _describe({(e["kind"], e["resource"]) for e in u["effects"]}) for u in units]
        return ["operations do not match the expected units: got "
                + "; ".join(describe(o) for o in view) + " | expected " + "; ".join(wanted)]
    notes = []
    for perm in matching:  # perm[o] = index of the expected unit encoded by operation o
        by_key = {units[perm[o]]["key"]: view[o]["id"] for o in range(len(view))}
        to_key = {view[o]["id"]: units[perm[o]]["key"] for o in range(len(view))}
        got = {to_key[o["id"]]: {to_key[d] for d in o["deps"] if d in to_key} for o in view}
        unknown = [d for o in view for d in o["deps"] if d not in to_key]
        if unknown:
            notes.append("dependency on an unknown operation")
            continue
        want = {u["key"]: set(u["dependsOn"]) for u in units}
        if _closure(got) != _closure(want):
            notes.append("dependencies differ: got " + str({k: sorted(v) for k, v in got.items()})
                         + " expected " + str({k: sorted(v) for k, v in want.items()}))
            continue
        index = {frozenset((i["left"], i["right"])): i for i in report["interactions"]}
        problems = []
        for pair in expect["pairs"]:
            item = index.get(frozenset((by_key[pair["left"]], by_key[pair["right"]])))
            if item is None:
                problems.append(f"no interaction for {pair['left']}/{pair['right']}")
            elif item.get("classification") != pair["classification"]:
                problems.append(f"{pair['left']}/{pair['right']} is {item.get('classification')} "
                                f"instead of {pair['classification']}")
            elif sorted(item.get("constraints") or []) != sorted(pair["constraints"]):
                problems.append(f"{pair['left']}/{pair['right']} constraints {item.get('constraints')}")
        if not problems:
            return []
        notes.append("; ".join(problems))
    return notes[:1]


def score_case(case: dict, attempts: list[dict]) -> dict:
    """``validFirstAttempt``, ``validWithinRetry`` (first attempt, or one retry after a refusal), ``reasons``."""
    if not attempts:
        return {"validFirstAttempt": False, "validWithinRetry": False,
                "reasons": ["analyze-work was not called"]}
    first = _evaluate(case, attempts[0])
    if not first:
        return {"validFirstAttempt": True, "validWithinRetry": True, "reasons": []}
    reasons = ["first attempt: " + r for r in first]
    if attempts[0].get("accepted"):
        return {"validFirstAttempt": False, "validWithinRetry": False,
                "reasons": reasons + ["accepted but wrong, so no retry is credited"]}
    if len(attempts) < 2:
        return {"validFirstAttempt": False, "validWithinRetry": False,
                "reasons": reasons + ["no retry after the refusal"]}
    retry = _evaluate(case, attempts[1])
    if not retry:
        return {"validFirstAttempt": False, "validWithinRetry": True, "reasons": reasons}
    return {"validFirstAttempt": False, "validWithinRetry": False,
            "reasons": reasons + ["retry: " + r for r in retry]}


# ----------------------------------------------------------------------------
# Statistics and the D4 threshold
# ----------------------------------------------------------------------------
def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (95 % for the default z)."""
    if n <= 0 or not 0 <= successes <= n:
        raise ValueError("need n > 0 and 0 <= successes <= n")
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def _host_summary(runs: list[dict], prompts: int, repetitions: int) -> dict:
    """``runs``: one ``{caseId, validFirstAttempt, validWithinRetry}`` per repetition of a prompt."""
    by_case: dict[str, list[dict]] = {}
    for run in runs:
        by_case.setdefault(run["caseId"], []).append(run)
    complete = len(by_case) == prompts and all(len(v) == repetitions for v in by_case.values())
    trials = len(runs)
    first = sum(bool(r["validFirstAttempt"]) for r in runs)
    retry = sum(bool(r["validWithinRetry"]) for r in runs)
    # D4 applied per prompt: a prompt counts only if every repetition succeeded.
    first_prompts = sorted(c for c, v in by_case.items() if all(r["validFirstAttempt"] for r in v))
    retry_prompts = sorted(c for c, v in by_case.items() if all(r["validWithinRetry"] for r in v))
    failing = sorted(set(by_case) - set(retry_prompts))
    meets = complete and len(first_prompts) >= FIRST_ATTEMPT_MIN and len(retry_prompts) == prompts
    if not trials:
        verdict = "unobserved"
    elif not complete:
        verdict = "inconclusive"
    else:
        verdict = "meets" if meets else "misses"
    summary = {
        "verdict": verdict, "trials": trials, "prompts": len(by_case),
        "firstAttemptPrompts": len(first_prompts), "withinRetryPrompts": len(retry_prompts),
        "firstAttemptTrials": first, "withinRetryTrials": retry,
        "firstAttemptPromptsMissed": sorted(set(by_case) - set(first_prompts)),
        "withinRetryPromptsMissed": failing,
    }
    if trials:
        summary["firstAttemptInterval"] = wilson_interval(first, trials)
        summary["withinRetryInterval"] = wilson_interval(retry, trials)
        summary["pooledMeetsThreshold"] = complete and first / trials >= FIRST_ATTEMPT_MIN / prompts and retry == trials
    return summary


def summarize(results_by_host: dict[str, list[dict]], required_hosts: tuple[str, ...] = REQUIRED_HOSTS,
              prompts: int = PROMPTS_PER_HOST, repetitions: int = REPETITIONS) -> dict:
    """Apply D4 per host over D9 repetitions.

    A host meets the threshold only if it has all ``prompts`` x ``repetitions`` runs, at least
    8 prompts valid at the first attempt in every repetition, and all 10 prompts valid within one
    retry in every repetition. The pooled rates and Wilson intervals over runs are reported next
    to the verdict (repetitions of one prompt are not independent trials, so the intervals are
    descriptive). Overall: ``meets`` only if every required host meets; ``negative-result`` if a
    required host was observed completely and missed, with the failing prompts listed;
    otherwise ``inconclusive`` (a host unobserved or incomplete). Nothing is reinterpreted.
    """
    hosts = {host: _host_summary(results_by_host.get(host, []), prompts, repetitions)
             for host in sorted(set(required_hosts) | set(results_by_host))}
    required = [hosts[h] for h in required_hosts]
    if all(h["verdict"] == "meets" for h in required):
        overall = "meets"
    elif any(h["verdict"] == "misses" for h in required):
        overall = "negative-result"
    else:
        overall = "inconclusive"
    result: dict[str, Any] = {"overall": overall, "requiredHosts": list(required_hosts), "hosts": hosts}
    if overall != "meets":
        result["shortfall"] = {
            "label": "NEGATIVE RESULT: reported as observed, not reinterpreted" if overall == "negative-result"
            else "INCONCLUSIVE: a required host is unobserved or incomplete",
            "hosts": {h: {"verdict": hosts[h]["verdict"], "firstAttemptPromptsMissed": hosts[h]["firstAttemptPromptsMissed"],
                          "withinRetryPromptsMissed": hosts[h]["withinRetryPromptsMissed"]}
                      for h in required_hosts if hosts[h]["verdict"] != "meets"},
        }
    return result
