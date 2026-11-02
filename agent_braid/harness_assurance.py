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

``resolve`` follows the SPEC-058 REQ-006 / ``ownership.resolve_settings`` precedence (conversation over
repository over user, the profile as lowest source) per checkpoint and dimension (mode, depth). A scope value
that would lower a REQ-003 floor, or disable the no-attribution invariant, is not applied: the floor holds and
the attempt is recorded with its scope in ``refusedLowerings``. Scope documents and the profile are read only
from operator-owned locations (``read_operator_file``: no symlink, regular file, not group/other-writable,
inside the config directory, outside every working tree). ``ProfileJournal`` records profile changes as an
append-only begin/commit/abort/rollback journal following the ``harness_promotion`` pattern (that module is
not used): versions are immutable and strictly increasing per name, only a human actor from an operator-owned
source may change anything, an agent identity or an agent-writable source is refused and the refusal is
recorded, and the previous version stays restorable.

Nothing here executes, merges, releases or approves anything, reads a clock, host, network or model, and
``executionAuthorization`` is never true: a profile is operator-owned advisory configuration. Review depth
is unrelated to the "assurance level" compatibility classes of TERMINOLOGY.md.
"""
from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
import fcntl
import os
from pathlib import Path
import re
import secrets
import stat
from types import MappingProxyType
from typing import Any, NamedTuple

from .system_one import MAX_BYTES, InvalidDecision, canonical, digest, parse_json, thaw

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
    "unknown-scope", "scope-mismatch", "invalid-settings", "unobservable-source", "invalid-actor",
    "agent-identity", "agent-writable-source", "invalid-time", "time-regression", "invalid-reason",
    "invalid-journal", "journal-full", "profile-hash-mismatch", "version-not-newer", "no-transaction",
    "transaction-pending", "no-active-profile", "invalid-registry", "non-canonical", "concurrent-update",
    "journal-unavailable", "attribution-invariant",
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


# --- scope settings and resolution (REQ-003) ------------------------------------------

SETTINGS_FORMAT = "braid-harness-assurance-settings/v0.1"
RESOLVED_FORMAT = "braid-harness-assurance-resolved/v0.1"
SCOPES = ("conversation", "repository", "user")  # most specific first; the profile is the lowest source
_SETTINGS_KEYS = frozenset({"schema", "scope", "checkpoints", "noAttribution"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def validate_settings(document: Any) -> dict[str, Any]:
    """Return an independent copy of a scope settings document, or raise ``AssuranceError``.

    A floor checkpoint set to anything but ``human-only`` and ``noAttribution: false`` are well-formed
    requests; ``resolve`` refuses and records them. Everything else malformed is refused here.
    """
    _require(type(document) is dict, "invalid-settings")
    _require(set(document) <= _SETTINGS_KEYS, "unknown-key")
    _require({"schema", "scope"} <= set(document), "missing-key")
    _require(document["schema"] == SETTINGS_FORMAT, "unsupported-schema")
    _require(type(document["scope"]) is str and document["scope"] in SCOPES, "unknown-scope")
    checkpoints = document.get("checkpoints", {})
    _require(type(checkpoints) is dict, "invalid-settings")
    for checkpoint, entry in checkpoints.items():
        _require(checkpoint in CHECKPOINTS, "unknown-checkpoint")
        _require(type(entry) is dict and entry, "invalid-settings")
        _require(set(entry) <= {"mode", "depth"}, "unknown-key")
        if "mode" in entry:
            mode = entry["mode"]
            _require(type(mode) is str and mode in MODES, "unknown-mode")
            _require(checkpoint in FLOORS or mode in ALLOWED_MODES[checkpoint], "mode-not-allowed")
        if "depth" in entry:
            _require(checkpoint == DEPTH_CHECKPOINT, "depth-not-allowed")
            _require(type(entry["depth"]) is str and entry["depth"] in DEPTHS, "unknown-depth")
    _require(type(document.get("noAttribution", True)) is bool, "invalid-settings")
    return thaw(document)


def parse_settings(raw: bytes) -> dict[str, Any]:
    """Validate a scope settings document from bounded UTF-8 JSON without duplicate keys."""
    try:
        return validate_settings(parse_json(raw))
    except InvalidDecision:
        raise AssuranceError("invalid-json") from None


def resolve(profile: Any, documents: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Resolve the profile and already-read scope documents into the effective per-checkpoint view.

    The most specific scope that sets a value wins (conversation over repository over user over the profile),
    separately for each checkpoint's mode and for the ``pre-pr-review`` depth, and the source of every value is
    recorded. A request to lower a floor or to disable the no-attribution invariant is never applied and is
    recorded in ``refusedLowerings`` with its scope, so the floors hold whatever the sources say. Risk
    escalation (T004) only raises and is applied after this step.
    """
    profile = validate_profile(profile)
    documents = {} if documents is None else documents
    _require(isinstance(documents, Mapping) and all(scope in SCOPES for scope in documents), "unknown-scope")
    checked = {}
    for scope in SCOPES:
        if scope in documents:
            checked[scope] = validate_settings(documents[scope])
            _require(checked[scope]["scope"] == scope, "scope-mismatch")
    rows = _checkpoint_rows(profile)
    refused: list[dict[str, Any]] = []
    for scope, document in checked.items():  # most specific first: the first accepted value wins
        for row in rows:
            entry = document.get("checkpoints", {}).get(row["checkpoint"], {})
            for dimension in ("mode", "depth"):
                if dimension not in entry:
                    continue
                value = entry[dimension]
                if dimension == "mode" and row["checkpoint"] in FLOORS and value != "human-only":
                    refused.append({"checkpoint": row["checkpoint"], "dimension": "mode", "requested": value,
                                    "scope": scope, "floor": "human-only", "reason": "floor-not-human-only"})
                elif row[f"{dimension}Source"] == "profile":
                    row[dimension], row[f"{dimension}Source"] = value, scope
        if document.get("noAttribution", True) is not True:
            refused.append({"checkpoint": None, "dimension": "noAttribution", "requested": False, "scope": scope,
                            "floor": True, "reason": "attribution-invariant"})
    return {
        "schema": RESOLVED_FORMAT,
        "profile": {"name": profile["name"], "version": profile["version"], "digest": digest(profile)},
        "scopeSources": list(checked),
        "checkpoints": rows,
        "noAttribution": {"checkpoints": list(NO_ATTRIBUTION), "enforced": True},
        "refusedLowerings": refused,
        "executionAuthorization": EXECUTION_AUTHORIZATION,
    }


# --- operator-owned locations ---------------------------------------------------------

ASSURANCE_DIRECTORY = "assurance"
PROFILE_FILE, SETTINGS_FILE, JOURNAL_FILE = "profile.json", "settings.json", "journal.json"


def _inside(path: str, roots: Collection[str]) -> bool:
    return any(path == root or path.startswith(root.rstrip(os.sep) + os.sep) for root in roots)


@dataclass(frozen=True)
class OperatorSpace:
    """The operator-owned configuration directory and the working trees an agent can write."""

    config_dir: str
    working_trees: tuple[str, ...] = ()

    def location(self, name: str, repository_digest: str | None = None) -> Path:
        base = Path(self.config_dir) / ASSURANCE_DIRECTORY
        if repository_digest is None:
            return base / name
        _require(_hash(repository_digest), "unobservable-source")
        return base / "repositories" / repository_digest / name

    def owns(self, path: str | os.PathLike) -> bool:
        """True when ``path`` is inside the config directory and inside no working tree."""
        real = os.path.realpath(path)
        return (_inside(real, [os.path.realpath(self.config_dir)])
                and not _inside(real, [os.path.realpath(root) for root in self.working_trees]))


def read_operator_file(path: str | os.PathLike, space: OperatorSpace) -> bytes | None:
    """Read an operator-owned file; ``None`` when it does not exist.

    Refused with ``unobservable-source``: a symlink, anything that is not a regular file, a file writable by
    group or others, and a file outside the config directory or inside any working tree.
    """
    try:
        if os.path.islink(path):
            raise AssuranceError("unobservable-source")
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except FileNotFoundError:
        return None
    except OSError:
        raise AssuranceError("unobservable-source") from None
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or not space.owns(path)):
            raise AssuranceError("unobservable-source")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_BYTES + 1)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_BYTES:
        raise AssuranceError("unobservable-source")
    return raw


def load_profile(space: OperatorSpace) -> dict[str, Any] | None:
    """The operator's profile file, or ``None`` when there is none."""
    raw = read_operator_file(space.location(PROFILE_FILE), space)
    return None if raw is None else parse_profile(raw)


def load_scope_documents(space: OperatorSpace, *, repository_digest: str | None = None,
                         conversation: bytes | None = None) -> dict[str, dict[str, Any]]:
    """Read the user and repository settings from operator-owned files and the conversation scope as given."""
    documents = {}
    sources = [("user", space.location(SETTINGS_FILE))]
    if repository_digest is not None:
        sources.append(("repository", space.location(SETTINGS_FILE, repository_digest)))
    for scope, path in sources:
        raw = read_operator_file(path, space)
        if raw is not None:
            documents[scope] = parse_settings(raw)
    if conversation is not None:
        documents["conversation"] = parse_settings(conversation)
    return documents


# --- journaled profile changes (REQ-008) ----------------------------------------------

JOURNAL_FORMAT = "braid-harness-assurance-journal/v0.1"
ACTOR_KINDS = ("human", "agent", "model", "tool")
EVENTS = ("begun", "committed", "aborted", "rolled-back", "refused")
REFUSALS = ("agent-identity", "agent-writable-source")
MAX_JOURNAL = 256
MAX_PROFILES = 64
MAX_TICK = 1 << 40
_REASONED = frozenset({"aborted", "rolled-back"})
_EVENT_KEYS = frozenset({"seq", "event", "subject", "actor", "at", "reason"})


@dataclass(frozen=True)
class Change:
    """A requested profile change: who asks, from which file (if any), at which caller-supplied tick."""

    actor_kind: str
    actor_id: str
    at: int
    source: str | None = None


class Outcome(NamedTuple):
    """The resulting journal and the refusal reason when the change was refused and only recorded."""

    journal: "ProfileJournal"
    refusal: str | None


class _State(NamedTuple):
    active: str | None
    previous: tuple[str, ...]
    pending: str | None


def _reason_ok(event: str, reason: Any) -> bool:
    if event == "refused":
        return reason in REFUSALS
    return _id(reason) if event in _REASONED else reason is None


def _replay(profiles: Mapping[str, Any], journal: list[Any]) -> _State:
    active = pending = None
    previous: list[str] = []
    begun: set[str] = set()
    newest: dict[str, int] = {}
    last = 0
    for index, entry in enumerate(journal):
        _require(type(entry) is dict and set(entry) == _EVENT_KEYS, "invalid-journal")
        event, subject, actor, at, reason = (entry[k] for k in ("event", "subject", "actor", "at", "reason"))
        _require(entry["seq"] == index and type(at) is int and 0 <= at < MAX_TICK and at >= last, "invalid-journal")
        _require(event in EVENTS and (subject is None or _hash(subject)), "invalid-journal")
        _require(type(actor) is dict and set(actor) == {"kind", "id"} and actor["kind"] in ACTOR_KINDS
                 and _id(actor["id"]), "invalid-journal")
        _require(_reason_ok(event, reason), "invalid-journal")
        last = at
        if event == "refused":
            continue
        _require(actor["kind"] == "human", "invalid-journal")
        if event == "begun":
            _require(pending is None and subject in profiles, "invalid-journal")
            name, version = profiles[subject]["name"], profiles[subject]["version"]
            _require(version > newest.get(name, 0), "version-not-newer")
            begun.add(subject)
            newest[name] = version
            pending = subject
        elif event == "rolled-back":
            _require(active is not None and subject == active, "invalid-journal")
            active = previous.pop() if previous else None
        else:
            _require(pending is not None and subject == pending, "invalid-journal")
            if event == "committed":
                if active is not None:
                    previous.append(active)
                active = pending
            pending = None
    _require(set(profiles) == begun, "invalid-registry")
    return _State(active, tuple(previous), pending)


class ProfileJournal:
    """Immutable journal of profile versions; every operation returns a new one.

    The state (active version, restorable earlier versions, pending transaction) is derived only by replaying
    the append-only event list, so a decoded journal is checked by the rules that produced it. Profile versions
    are keyed by digest, immutable, and strictly increasing per profile name.
    """

    def __init__(self, profiles: Mapping[str, Any] | None = None, journal: Any = None):
        profiles, journal = thaw(profiles or {}), thaw(journal or [])
        _require(type(profiles) is dict and len(profiles) <= MAX_PROFILES
                 and type(journal) is list and len(journal) <= MAX_JOURNAL, "invalid-registry")
        for key, profile in profiles.items():
            _require(_hash(key) and key == digest(validate_profile(profile)), "profile-hash-mismatch")
        self._state = _replay(profiles, journal)
        self._profiles, self._journal = profiles, journal

    @property
    def journal(self) -> tuple[dict[str, Any], ...]:
        return tuple(thaw(self._journal))

    @property
    def active(self) -> str | None:
        return self._state.active

    @property
    def pending(self) -> str | None:
        return self._state.pending

    @property
    def previous(self) -> tuple[str, ...]:
        return self._state.previous

    @property
    def active_profile(self) -> dict[str, Any] | None:
        return None if self._state.active is None else thaw(self._profiles[self._state.active])

    def _append(self, event: str, subject: str | None, change: Change, reason: str | None,
                profile: Mapping[str, Any] | None = None) -> "ProfileJournal":
        _require(len(self._journal) < MAX_JOURNAL, "journal-full")
        _require(type(change.at) is int and 0 <= change.at < MAX_TICK, "invalid-time")
        _require(not self._journal or change.at >= self._journal[-1]["at"], "time-regression")
        entry = {"seq": len(self._journal), "event": event, "subject": subject,
                 "actor": {"kind": change.actor_kind, "id": change.actor_id}, "at": change.at, "reason": reason}
        profiles = dict(self._profiles)
        if profile is not None:
            profiles[subject] = profile
        return ProfileJournal(profiles, [*self._journal, entry])

    def _act(self, event: str, change: Change, space: OperatorSpace, *, reason: str | None = None,
             profile: Mapping[str, Any] | None = None, subject: str | None = None) -> Outcome:
        _require(isinstance(change, Change) and type(change.actor_kind) is str and change.actor_kind in ACTOR_KINDS
                 and _id(change.actor_id), "invalid-actor")
        _require(_reason_ok(event, reason), "invalid-reason")
        refusal = ("agent-identity" if change.actor_kind != "human"
                   else "agent-writable-source" if change.source is not None and not space.owns(change.source)
                   else None)
        if refusal is not None:
            return Outcome(self._append("refused", subject, change, refusal), refusal)
        return Outcome(self._append(event, subject, change, reason, profile), None)

    def begin(self, profile: Any, change: Change, space: OperatorSpace) -> Outcome:
        """Start activating a new profile version; the active profile is unchanged until ``commit``."""
        profile = validate_profile(profile)
        _require(self._state.pending is None, "transaction-pending")
        return self._act("begun", change, space, profile=profile, subject=digest(profile))

    def commit(self, change: Change, space: OperatorSpace) -> Outcome:
        """Make the pending version active; the former active version stays restorable."""
        _require(self._state.pending is not None, "no-transaction")
        return self._act("committed", change, space, subject=self._state.pending)

    def abort(self, change: Change, space: OperatorSpace, *, reason: str) -> Outcome:
        """Drop the pending version; the active profile is kept."""
        _require(self._state.pending is not None, "no-transaction")
        return self._act("aborted", change, space, reason=reason, subject=self._state.pending)

    def rollback(self, change: Change, space: OperatorSpace, *, reason: str) -> Outcome:
        """Withdraw the active version and restore the newest earlier one."""
        _require(self._state.active is not None, "no-active-profile")
        return self._act("rolled-back", change, space, reason=reason, subject=self._state.active)

    def to_bytes(self) -> bytes:
        return canonical({"format": JOURNAL_FORMAT, "profiles": self._profiles, "journal": self._journal})

    @property
    def sha256(self) -> str:
        return digest({"format": JOURNAL_FORMAT, "profiles": self._profiles, "journal": self._journal})

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ProfileJournal":
        """Accept only the exact canonical bytes ``to_bytes`` would produce."""
        try:
            value = parse_json(raw)
        except InvalidDecision:
            raise AssuranceError("invalid-json") from None
        _require(set(value) == {"format", "profiles", "journal"} and value["format"] == JOURNAL_FORMAT,
                 "invalid-registry")
        journal = cls(value["profiles"], value["journal"])
        _require(journal.to_bytes() == raw, "non-canonical")
        return journal


def load_journal(space: OperatorSpace) -> ProfileJournal:
    """The operator's journal file, or an empty journal when there is none."""
    raw = read_operator_file(space.location(JOURNAL_FILE), space)
    return ProfileJournal() if raw is None else ProfileJournal.from_bytes(raw)


def save_journal(space: OperatorSpace, journal: ProfileJournal) -> None:
    """Atomically replace the journal file unless the stored journal is not a prefix of the new one."""
    _require(type(journal) is ProfileJournal, "invalid-registry")
    path = space.location(JOURNAL_FILE)
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        lock = os.open(path.with_name(path.name + ".lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise AssuranceError("journal-unavailable") from None
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if os.path.lexists(path):
            stored = load_journal(space)
            _require(journal.journal[:len(stored.journal)] == stored.journal, "concurrent-update")
        temp = path.with_name(f".{path.name}.tmp-{secrets.token_hex(8)}")
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as handle:
                handle.write(journal.to_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        except OSError:
            temp.unlink(missing_ok=True)
            raise AssuranceError("journal-unavailable") from None
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    finally:
        os.close(lock)
