# SPDX-License-Identifier: AGPL-3.0-only
"""Assurance profiles, risk escalation: a deterministic classifier that can only raise; offline, advisory.

``classify_risk`` maps a diff summary (changed paths, changed-line count and the ``scripts/validate_change.py``
``classify()`` impact of those paths, ADR 0011) to a risk classification using the fixed founder rules (Q5)
and the operator's ``riskRules``: a diff touching a ``sensitive`` path, a diff over 400 changed lines and a
diff touching a shared file each raise ``pre-pr-review`` to ``R3``; an operator rule raises depth to its
``raiseTo`` and mode to at least its ``modeAtLeast`` when one of its paths matches and the diff has at least
``minChangedLines`` changed lines. ``check_profile_binding`` re-derives every reason that needs no repository
impact (the size and shared-file defaults and the operator rules) from a classification's own paths and line
count under a given profile, so a classification computed under another profile is refused (``compile_artifact``
calls it). A documentation-only change (only contributor-documentation paths, none
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
from types import MappingProxyType
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


def _reason(rule: str, raise_to: str, mode_at_least: str | None) -> dict[str, Any]:
    return {"rule": rule, "raiseTo": raise_to, "modeAtLeast": mode_at_least}


SENSITIVE_REASON = MappingProxyType(_reason("sensitive-path", DEFAULT_RAISE, None))
SIZE_REASON = MappingProxyType(_reason("size-over-400", DEFAULT_RAISE, None))
SHARED_REASON = MappingProxyType(_reason("shared-file", DEFAULT_RAISE, None))


def _reason_key(reason: Mapping[str, Any]) -> tuple[str, str, str]:
    return (reason["rule"], reason["raiseTo"], reason["modeAtLeast"] or "")


def _derived_reasons(profile: Mapping[str, Any], paths: list[str], changed_lines: int) -> list[dict[str, Any]]:
    """Every reason that follows from the paths and line count alone: all but ``sensitive-path`` (impact)."""
    reasons = []
    if changed_lines > SIZE_THRESHOLD:
        reasons.append(dict(SIZE_REASON))
    if any(path in SHARED_FILES for path in paths):
        reasons.append(dict(SHARED_REASON))
    for rule in profile["riskRules"]:
        match = rule["match"]
        if changed_lines >= match["minChangedLines"] and any(
                _matches(path, pattern) for path in paths for pattern in match["paths"]):
            reasons.append(_reason(rule["id"], rule["raiseTo"], rule["modeAtLeast"]))
    return reasons


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
    # a list: an operator rule id equal to a default name cannot replace it
    reasons = ([dict(SENSITIVE_REASON)] if impact.sensitive else []) + _derived_reasons(profile, normalized, changed_lines)
    ordered = sorted(reasons, key=_reason_key)
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


def check_profile_binding(profile: Any, classification: Any) -> None:
    """Refuse (``invalid-diff-summary``) a classification that ``profile`` would not produce from its own paths.

    The reasons must be exactly those ``classify_risk`` derives under ``profile`` from the classification's paths
    and changed-line count, plus at most the impact-dependent ``sensitive-path`` reason, which only the repository
    impact can confirm (the recorded caller-supplied impact residual). A classification computed under another
    profile, or with an operator rule dropped, added or altered, is refused.
    """
    profile = validate_profile(profile)
    _check_classification(classification)
    actual = sorted(classification["reasons"], key=_reason_key)
    expected = _derived_reasons(profile, classification["paths"], classification["changedLines"])
    for candidate in (expected, [*expected, dict(SENSITIVE_REASON)]):
        if actual == sorted(candidate, key=_reason_key):
            return
    raise _refuse()


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
    risk class follows from them, and the fixed Q5 rules the paths and line count trigger are present with their
    canonical ``R3`` raise (an ``R2`` reason under a default name does not satisfy one). A
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
    _require(value["changedLines"] <= SIZE_THRESHOLD or SIZE_REASON in reasons, "invalid-diff-summary")
    _require(not any(path in SHARED_FILES for path in value["paths"]) or SHARED_REASON in reasons,
             "invalid-diff-summary")


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
