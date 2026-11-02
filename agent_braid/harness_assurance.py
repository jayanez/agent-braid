# SPDX-License-Identifier: AGPL-3.0-only
"""Assurance profiles: closed checkpoint catalog, allowed-mode table, schema and floors; offline, advisory.

A profile (``braid-harness-assurance-profile/v0.1``, SPEC-067 contract) assigns every lifecycle checkpoint
of a closed catalog one human-in-the-loop (HITL) mode, and the ``pre-pr-review`` checkpoint also a review
depth ``R0``..``R4`` (Q6: depth applies to no other checkpoint in v0.1). ``validate_profile`` accepts
only a complete, exact profile and refuses everything else with one fixed reason and no partial view:
an unknown or missing checkpoint, a depth anywhere but ``pre-pr-review``, an unknown depth, a mode
outside the checkpoint's allowed set, an unknown key. The five REQ-003 floor checkpoints (``release``,
``clarification``, ``grant``, ``native-effect``, ``auto-promotion``) are ``human-only`` and a profile
listing one as anything else is refused. Only ``merge`` admits ``standing-authorization`` (Q2).

``PRESETS`` are the named profiles ``lite``, ``standard`` and ``strict``; Q1 fixes the names, the ``standard``
default and R2 for code, while the other per-checkpoint values are this task's proposal, never below a floor.

Nothing here executes, merges, releases or approves anything, reads a clock, host, network or model, and
``executionAuthorization`` is never true: a profile is operator-owned advisory configuration. Review depth
is unrelated to the "assurance level" compatibility classes of TERMINOLOGY.md.
"""
from __future__ import annotations

from collections.abc import Mapping
import re
from types import MappingProxyType
from typing import Any

from .system_one import InvalidDecision, digest, parse_json, thaw

PROFILE_FORMAT = "braid-harness-assurance-profile/v0.1"
VIEW_FORMAT = "braid-harness-assurance-view/v0.1"
EXECUTION_AUTHORIZATION = False

CHECKPOINTS = (
    "intake-spec", "clarification", "plan-tasks", "track-dispatch", "implementation", "pre-commit",
    "pre-pr-review", "pr-open", "ci", "merge", "release", "post-merge", "grant", "harness-self-change",
    "auto-promotion", "native-effect",
)
MODES = ("autonomous", "notify", "standing-authorization", "approve-each", "human-only")  # ordered, low to high
DEPTHS = ("R0", "R1", "R2", "R3", "R4")
DEPTH_CHECKPOINT = "pre-pr-review"
FLOORS = ("release", "clarification", "grant", "native-effect", "auto-promotion")  # REQ-003: human-only
NO_ATTRIBUTION = ("pr-open", "merge", "release", "post-merge")  # REQ-003 invariant, true and not settable
STANDING_CHECKPOINTS = ("merge",)  # Q2
_NO_STANDING = tuple(mode for mode in MODES if mode != "standing-authorization")
ALLOWED_MODES: Mapping[str, tuple[str, ...]] = MappingProxyType({
    **{checkpoint: _NO_STANDING for checkpoint in CHECKPOINTS},
    **{checkpoint: MODES for checkpoint in STANDING_CHECKPOINTS},
    # SPEC-050 / research R2: harness self-change (lesson/profile promotion) stays human-only.
    **{checkpoint: ("human-only",) for checkpoint in (*FLOORS, "harness-self-change")},
})

REASONS = (
    "invalid-profile", "unsupported-schema", "unknown-key", "missing-key", "invalid-name", "invalid-version",
    "unknown-checkpoint", "missing-checkpoint", "missing-mode", "unknown-mode", "mode-not-allowed",
    "floor-not-human-only", "depth-not-allowed", "missing-depth", "unknown-depth", "invalid-risk-rule",
    "invalid-standing-authorization", "unknown-preset", "invalid-json",
)

MAX_RULES = 16
MAX_PATTERNS = 16
MAX_PATTERN = 128
MAX_LINES = 10_000_000
MAX_AUTHORIZATIONS = 16
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_PROFILE_KEYS = frozenset({"schema", "name", "version", "checkpoints", "riskRules", "standingAuthorizations"})
_RULE_KEYS = frozenset({"id", "match", "raiseTo", "modeAtLeast"})
_MATCH_KEYS = frozenset({"paths", "minChangedLines"})


class AssuranceError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-profile"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise AssuranceError(reason)


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def _exact(value: Any, keys: frozenset[str], reason: str) -> None:
    _require(type(value) is dict, reason)
    _require(set(value) <= keys, "unknown-key")
    _require(set(value) == keys, reason)


def _check_checkpoint(checkpoint: str, entry: Any) -> None:
    _require(type(entry) is dict, "invalid-profile")
    _require(set(entry) <= {"mode", "depth"}, "unknown-key")
    _require("mode" in entry, "missing-mode")
    mode = entry["mode"]
    _require(type(mode) is str and mode in MODES, "unknown-mode")
    _require(checkpoint not in FLOORS or mode == "human-only", "floor-not-human-only")
    _require(mode in ALLOWED_MODES[checkpoint], "mode-not-allowed")
    if checkpoint != DEPTH_CHECKPOINT:
        _require("depth" not in entry, "depth-not-allowed")
        return
    _require("depth" in entry, "missing-depth")
    _require(type(entry["depth"]) is str and entry["depth"] in DEPTHS, "unknown-depth")


def _check_rule(rule: Any) -> str:
    _exact(rule, _RULE_KEYS, "invalid-risk-rule")
    _require(_id(rule["id"]), "invalid-risk-rule")
    _exact(rule["match"], _MATCH_KEYS, "invalid-risk-rule")
    paths = rule["match"]["paths"]
    _require(type(paths) is list and 0 < len(paths) <= MAX_PATTERNS, "invalid-risk-rule")
    _require(all(type(p) is str and 0 < len(p) <= MAX_PATTERN and p.isprintable() and "\\" not in p
                 and all(part not in ("", ".", "..") for part in p.split("/")) for p in paths), "invalid-risk-rule")
    # Raise-only against the configured depth and mode is checked where those are known (T004).
    _require(_int(rule["match"]["minChangedLines"], 0, MAX_LINES), "invalid-risk-rule")
    _require(type(rule["raiseTo"]) is str and rule["raiseTo"] in DEPTHS, "invalid-risk-rule")
    _require(type(rule["modeAtLeast"]) is str and rule["modeAtLeast"] in MODES, "invalid-risk-rule")
    return rule["id"]


def validate_profile(profile: Any) -> dict[str, Any]:
    """Return an independent copy of a complete, exact profile, or raise ``AssuranceError`` with a fixed reason."""
    _require(type(profile) is dict, "invalid-profile")
    _exact(profile, _PROFILE_KEYS, "missing-key")
    _require(profile["schema"] == PROFILE_FORMAT, "unsupported-schema")
    _require(_id(profile["name"]), "invalid-name")
    _require(_int(profile["version"], 1, (1 << 31) - 1), "invalid-version")
    checkpoints = profile["checkpoints"]
    _require(type(checkpoints) is dict, "invalid-profile")
    _require(all(c in CHECKPOINTS for c in checkpoints), "unknown-checkpoint")
    _require(all(c in checkpoints for c in CHECKPOINTS), "missing-checkpoint")
    for checkpoint in CHECKPOINTS:
        _check_checkpoint(checkpoint, checkpoints[checkpoint])
    rules = profile["riskRules"]
    _require(type(rules) is list and len(rules) <= MAX_RULES, "invalid-risk-rule")
    ids = [_check_rule(rule) for rule in rules]
    _require(len(set(ids)) == len(ids), "invalid-risk-rule")
    grants = profile["standingAuthorizations"]
    _require(type(grants) is list and len(grants) <= MAX_AUTHORIZATIONS and all(map(_id, grants))
             and grants == sorted(set(grants)), "invalid-standing-authorization")
    return thaw(profile)


def parse_profile(raw: bytes) -> dict[str, Any]:
    """Validate a profile from bounded UTF-8 JSON without duplicate keys."""
    try:
        return validate_profile(parse_json(raw))
    except InvalidDecision:
        raise AssuranceError("invalid-json") from None


def profile_digest(profile: Any) -> str:
    """SHA-256 over the canonical bytes of a valid profile."""
    return digest(validate_profile(profile))


def _checkpoint_rows(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One row per checkpoint, in catalog order, with mode, depth (``pre-pr-review`` only) and source."""
    rows = []
    for checkpoint in CHECKPOINTS:
        entry = profile["checkpoints"][checkpoint]
        row = {"checkpoint": checkpoint, "mode": entry["mode"], "modeSource": "profile"}
        if "depth" in entry:
            row.update(depth=entry["depth"], depthSource="profile")
        rows.append(row)
    return rows


def profile_view(profile: Any) -> dict[str, Any]:
    """The compiled per-checkpoint view of a valid profile; refused whole when the profile is invalid."""
    profile = validate_profile(profile)
    return {
        "schema": VIEW_FORMAT,
        "profile": {"name": profile["name"], "version": profile["version"], "digest": digest(profile)},
        "checkpoints": _checkpoint_rows(profile),
        "noAttribution": {"checkpoints": list(NO_ATTRIBUTION), "enforced": True},
        "executionAuthorization": EXECUTION_AUTHORIZATION,
    }


# Q1: ``standard`` is the default; each column is a preset, strictness never decreases left to right.
_PRESET_TABLE = {
    #                      lite                standard            strict
    "intake-spec":        ("autonomous",       "notify",           "approve-each"),
    "clarification":      ("human-only",) * 3,
    "plan-tasks":         ("autonomous",       "notify",           "approve-each"),
    "track-dispatch":     ("notify",           "notify",           "approve-each"),
    "implementation":     ("autonomous",       "autonomous",       "notify"),
    "pre-commit":         ("autonomous",       "autonomous",       "notify"),
    "pre-pr-review":      ("autonomous",       "notify",           "approve-each"),
    "pr-open":            ("notify",           "notify",           "approve-each"),
    "ci":                 ("autonomous",       "notify",           "notify"),
    "merge":              ("standing-authorization", "standing-authorization", "approve-each"),
    "release":            ("human-only",) * 3,
    "post-merge":         ("autonomous",       "notify",           "notify"),
    "grant":              ("human-only",) * 3,
    "harness-self-change": ("human-only",) * 3,
    "auto-promotion":     ("human-only",) * 3,
    "native-effect":      ("human-only",) * 3,
}
PRESET_DEPTHS = {"lite": "R1", "standard": "R2", "strict": "R3"}
DEFAULT_PRESET = "standard"
PRESETS = tuple(PRESET_DEPTHS)


def preset(name: str) -> dict[str, Any]:
    """A fresh, validated copy of the ``lite``, ``standard`` or ``strict`` profile."""
    _require(type(name) is str and name in PRESET_DEPTHS, "unknown-preset")
    column = PRESETS.index(name)
    checkpoints = {c: {"mode": _PRESET_TABLE[c][column]} for c in CHECKPOINTS}
    checkpoints[DEPTH_CHECKPOINT]["depth"] = PRESET_DEPTHS[name]
    return validate_profile({"schema": PROFILE_FORMAT, "name": name, "version": 1, "checkpoints": checkpoints,
                             "riskRules": [], "standingAuthorizations": []})
