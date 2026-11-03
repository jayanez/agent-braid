# SPDX-License-Identifier: AGPL-3.0-only
"""Assurance profiles, risk escalation: a deterministic classifier that can only raise; offline, advisory.

``classify_risk`` maps a diff summary (changed paths, changed-line count and the ``scripts/validate_change.py``
``classify()`` impact of those paths, ADR 0011) to a risk classification using the fixed founder rules (Q5)
and the operator's ``riskRules``: a diff touching a ``sensitive`` path, a diff over 400 changed lines and a
diff touching a shared file each raise ``pre-pr-review`` to ``R3``; an operator rule raises depth to its
``raiseTo`` and mode to at least its ``modeAtLeast`` when one of its paths matches and the diff has at least
``minChangedLines`` changed lines. A documentation-only change (only contributor-documentation paths, none
sensitive) is reported as ``docsOnly``. ``apply_risk`` applies a classification to a resolved view and takes the
maximum of the configured and the raised value, so a rule below the configured depth or mode leaves the
configured value standing and nothing is ever lowered; ``check_raise_only`` refuses, with ``invalid-risk-rule``,
a profile whose rule would lower the profile's own ``pre-pr-review`` depth or mode (the check T003 left here).

Pure: no network, clock, model, filesystem (except ``repository_impact``, which imports the repository's own
``scripts/validate_change.py`` from a source checkout) or randomness; equal input yields equal output. Nothing
here executes, merges or approves anything, and ``executionAuthorization`` is never true.
"""
from __future__ import annotations

import copy
import fnmatch
from collections.abc import Iterable, Mapping
from typing import Any

from .harness_assurance import (
    ALLOWED_MODES, DEPTH_CHECKPOINT, DEPTHS, EXECUTION_AUTHORIZATION, MAX_LINES, MODES, RESOLVED_FORMAT,
    AssuranceError, _id, _int, _require, validate_profile,
)

RISK_FORMAT = "braid-harness-assurance-risk/v0.1"
RISK_CLASSES = ("docs-only", "ordinary", "elevated")
SIZE_THRESHOLD = 400  # Q5: a diff over 400 changed lines raises to R3
SHARED_FILES = (  # Q5: a diff touching any of these raises to R3
    "docs/STATUS.md", "ROADMAP.md", "docs/development/SPEC_MILESTONE_INDEX.md", "agent_braid/cli.py",
    "agent_braid/ownership.py", "docs/development/github-tracking.json",
)
DEFAULT_RAISE = "R3"
DOCS_DOMAIN = "contributor-documentation"  # the validate_change domain of documentation-only paths
MAX_PATHS = 2_000  # bounds paths x patterns work (fnmatch)
_CLASSIFICATION_KEYS = frozenset({"schema", "riskClass", "docsOnly", "paths", "changedLines", "reasons",
                                  "raiseDepthTo", "raiseModeTo", "executionAuthorization"})
_REASON_KEYS = frozenset({"rule", "raiseTo", "modeAtLeast"})


def _refuse() -> AssuranceError:
    return AssuranceError("invalid-diff-summary")


def _normalize(paths: Any) -> list[str]:
    if not isinstance(paths, (list, tuple)) or len(paths) > MAX_PATHS:
        raise _refuse()
    result = set()
    for path in paths:
        if type(path) is not str or not path.isprintable() or "\\" in path or path.startswith("/"):
            raise _refuse()
        parts = path.split("/")
        if parts[0] == ".":
            parts = parts[1:]
        if not parts or any(part in ("", ".", "..") for part in parts):
            raise _refuse()
        result.add("/".join(parts))
    return sorted(result)


def _matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def check_raise_only(profile: Any) -> None:
    """Refuse a profile whose risk rule would lower its own ``pre-pr-review`` depth or mode."""
    _check_raise_only(validate_profile(profile))


def _check_raise_only(profile: Mapping[str, Any]) -> None:
    configured = profile["checkpoints"][DEPTH_CHECKPOINT]
    for rule in profile["riskRules"]:
        _require(DEPTHS.index(rule["raiseTo"]) >= DEPTHS.index(configured["depth"])
                 and MODES.index(rule["modeAtLeast"]) >= MODES.index(configured["mode"]), "invalid-risk-rule")


def classify_risk(profile: Any, paths: Any, changed_lines: Any, impact: Any) -> dict[str, Any]:
    """Classify a diff summary; ``impact`` is ``validate_change.classify(paths)`` (see ``repository_impact``)."""
    profile = validate_profile(profile)
    _check_raise_only(profile)
    normalized = _normalize(paths)
    if not _int(changed_lines, 0, MAX_LINES):
        raise _refuse()
    if (getattr(impact, "paths", None) != tuple(normalized) or type(getattr(impact, "sensitive", None)) is not bool
            or not isinstance(getattr(impact, "domains", None), tuple)):
        raise _refuse()
    reasons: list[dict[str, Any]] = []  # a list: an operator rule id equal to a default name cannot replace it

    def add(rule: str, raise_to: str, mode_at_least: str | None) -> None:
        reasons.append({"rule": rule, "raiseTo": raise_to, "modeAtLeast": mode_at_least})

    if impact.sensitive:
        add("sensitive-path", DEFAULT_RAISE, None)
    if changed_lines > SIZE_THRESHOLD:
        add("size-over-400", DEFAULT_RAISE, None)
    if any(path in SHARED_FILES for path in normalized):
        add("shared-file", DEFAULT_RAISE, None)
    for rule in profile["riskRules"]:
        match = rule["match"]
        if changed_lines >= match["minChangedLines"] and any(
                _matches(path, pattern) for path in normalized for pattern in match["paths"]):
            add(rule["id"], rule["raiseTo"], rule["modeAtLeast"])
    ordered = sorted(reasons, key=lambda r: (r["rule"], r["raiseTo"], r["modeAtLeast"] or ""))
    depth = max((r["raiseTo"] for r in ordered), key=DEPTHS.index, default=None)
    mode = max((r["modeAtLeast"] for r in ordered if r["modeAtLeast"]), key=MODES.index, default=None)
    docs_only = bool(normalized) and not impact.sensitive and set(impact.domains) == {DOCS_DOMAIN}
    return {
        "schema": RISK_FORMAT,
        "riskClass": "elevated" if depth is not None else "docs-only" if docs_only else "ordinary",
        "docsOnly": docs_only,
        "paths": normalized,
        "changedLines": changed_lines,
        "reasons": ordered,
        "raiseDepthTo": depth,
        "raiseModeTo": mode,
        "executionAuthorization": EXECUTION_AUTHORIZATION,
    }


def _check_classification(value: Any) -> None:
    _require(type(value) is dict and set(value) == _CLASSIFICATION_KEYS and value["schema"] == RISK_FORMAT
             and value["executionAuthorization"] is False, "invalid-diff-summary")
    depth, mode = value["raiseDepthTo"], value["raiseModeTo"]
    _require(depth is None or (type(depth) is str and depth in DEPTHS), "invalid-diff-summary")
    _require(mode is None or (type(mode) is str and mode in MODES), "invalid-diff-summary")
    _require(type(value["reasons"]) is list and all(
        type(r) is dict and set(r) == _REASON_KEYS and _id(r["rule"]) and r["raiseTo"] in DEPTHS
        and (r["modeAtLeast"] is None or r["modeAtLeast"] in MODES) for r in value["reasons"]), "invalid-diff-summary")
    _require(value["riskClass"] in RISK_CLASSES and type(value["docsOnly"]) is bool
             and _int(value["changedLines"], 0, MAX_LINES) and type(value["paths"]) is list
             and value["paths"] == _normalize(value["paths"]), "invalid-diff-summary")
    _check_consistency(value)


def _check_consistency(value: Mapping[str, Any]) -> None:
    """The classification must agree with itself: ``docsOnly`` is the one field that lowers the required reviews.

    Mirrors ``classify_risk``: reasons in canonical order, the raise values are the maxima over the reasons, the
    risk class follows from them, and the fixed Q5 rules the paths and line count trigger are present. A
    documentation-only claim needs paths and no ``sensitive-path`` reason. A forgery that stays consistent with its
    own paths can only be caught by recomputing the classification from the diff.
    """
    reasons = value["reasons"]
    keys = [(r["rule"], r["raiseTo"], r["modeAtLeast"] or "") for r in reasons]
    names = {r["rule"] for r in reasons}
    depth = max((r["raiseTo"] for r in reasons), key=DEPTHS.index, default=None)
    mode = max((r["modeAtLeast"] for r in reasons if r["modeAtLeast"]), key=MODES.index, default=None)
    docs_only = value["docsOnly"]
    expected = "elevated" if depth is not None else "docs-only" if docs_only else "ordinary"
    _require(keys == sorted(keys) and value["raiseDepthTo"] == depth and value["raiseModeTo"] == mode
             and value["riskClass"] == expected, "invalid-diff-summary")
    _require(not docs_only or (bool(value["paths"]) and "sensitive-path" not in names), "invalid-diff-summary")
    _require(value["changedLines"] <= SIZE_THRESHOLD or "size-over-400" in names, "invalid-diff-summary")
    _require(not any(path in SHARED_FILES for path in value["paths"]) or "shared-file" in names, "invalid-diff-summary")


def apply_risk(resolved: Mapping[str, Any], classification: Any) -> dict[str, Any]:
    """The resolved view with ``pre-pr-review`` raised to the classification; never lowered.

    Depth becomes the higher of the configured and the raised depth. Mode becomes the lowest mode the checkpoint
    allows that is at least the raised mode, and never below the configured mode. A raised value is recorded
    with source ``risk``; a value that stands keeps its source.
    """
    _check_classification(classification)
    _require(isinstance(resolved, Mapping) and resolved.get("schema") == RESOLVED_FORMAT
             and isinstance(resolved.get("checkpoints"), list), "invalid-diff-summary")
    view = copy.deepcopy(dict(resolved))
    row = next((r for r in view["checkpoints"] if isinstance(r, dict) and r.get("checkpoint") == DEPTH_CHECKPOINT), None)
    _require(row is not None and row.get("depth") in DEPTHS and row.get("mode") in MODES, "invalid-diff-summary")
    if classification["raiseDepthTo"] is not None and DEPTHS.index(classification["raiseDepthTo"]) > DEPTHS.index(row["depth"]):
        row["depth"], row["depthSource"] = classification["raiseDepthTo"], "risk"
    if classification["raiseModeTo"] is not None:
        floor = MODES.index(classification["raiseModeTo"])
        raised = next(mode for mode in ALLOWED_MODES[DEPTH_CHECKPOINT] if MODES.index(mode) >= floor)
        if MODES.index(raised) > MODES.index(row["mode"]):
            row["mode"], row["modeSource"] = raised, "risk"
    view["risk"] = copy.deepcopy(classification)
    return view


def repository_impact(paths: Iterable[str]) -> Any:
    """``scripts/validate_change.py`` ``classify()`` of ``paths``; needs a source checkout of the repository."""
    try:
        from scripts import validate_change
    except ImportError:
        raise AssuranceError("unobservable-source") from None
    try:
        return validate_change.classify(paths)
    except ValueError:
        raise _refuse() from None
    except AttributeError:
        raise AssuranceError("unobservable-source") from None
