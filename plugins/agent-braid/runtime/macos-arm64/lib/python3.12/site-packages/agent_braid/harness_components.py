# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T002 versioned component registry and compatibility compiler.

Compiles one task-local component inventory into an immutable ``ComponentProfile``
(``braid-harness-profile/v0.1``, frozen in specs/050-braid-harness-adaptation/
contracts/interface.md). The module is pure: it reads no file, starts no process,
opens no network connection and issues no grant. Every record keeps
``executionAuthorization`` false.

The compiler, not the input, decides the admission state (contract section 2):
hooks, plugins/tool loops and delegated roles (C6 to C8) start ``blocked``, so does
every class that declares child-process or network effects, and the classes whose
owner task is not implemented. Only C1 and C2 with inert effects (E0 to E2) are
``implemented``, which says nothing about any host. No host qualification record
exists yet, so every host row is ``unqualified``; ``qualified``, ``enabled`` and
``excluded`` are part of the closed vocabulary but cannot be produced or accepted
here. Effect class E5 (host or global configuration, authorities, verifiers) is
refused for every profile.

Inheritance is explicit. A child inventory states, for every path of its trusted
parent profile, ``inherit`` (identical bytes), ``override`` (new bytes) or
``delete`` (bound to the parent's bytes); an unmentioned parent path refuses, so a
deletion is never inherited silently. Protected layers always take precedence and
cannot be added, overridden, inherited or deleted. The ``root`` directory names per
class are registry conventions, not observed host schemas: the contract (section 4)
records that event, hook and plugin schemas are not yet inventoried, so the schema
lists stay empty and any content for them refuses.

``settings`` is a selection record, not a modification of the protected provider and
model layers. ``deleted`` lists the paths removed relative to the direct parent only;
a later version may add such a path again with new bytes.

Model, effort and route may be selected only from a caller-supplied approved list
bound to a trusted full SHA-256. A matching hash proves byte identity of that list,
never who approved it. Declared file hashes bind metadata only; the importer must
check actual bytes (``harness_surface``).
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata
from typing import Any

from .harness_manifest import DEFAULT_LIMITS, NATIVE_BUILD
from .harness_surface import _PROTECTED as PROTECTED_COMPONENTS, SurfaceError, normalize_rel
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

FORMAT = "braid-harness-profile/v0.1"
INVENTORY_FORMAT = "braid-harness-inventory/v0.1"
STATES = ("implemented", "qualified", "enabled", "blocked", "excluded")
CLASSES = ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8")
EFFECTS = ("E0", "E1", "E2", "E3", "E4", "E5")
HOSTS = ("claude", "codex")
OPS = ("add", "inherit", "override", "delete")
ROUTES = ("offline", "subscription")
# Registry conventions (not observed host schemas): inert text under one root per class.
ROOTS = {"C1": "guidance", "C2": "lessons", "C3": "skills", "C4": "toolguidance",
         "C5": "helpers", "C6": "eventnotes", "C7": "loopnotes", "C8": "roles"}
SUFFIXES = (".md", ".txt")
POLICIES = {"path": "positive-inventory-v1", "content": "inert-text-v1",
            "effect": "declared-effect-v1"}
LIMITS = {key: DEFAULT_LIMITS[key] for key in (
    "maxFiles", "maxFileBytes", "maxCandidateBytes", "maxPathDepth",
    "maxContextEntries", "maxContextBytes")}
SCHEMAS = {"tools": [], "events": [], "roles": []}
# Host rows at the contract freeze: Claude observed, Codex not installed; neither qualified.
HOST_SUPPORT = {"claude": {"observedBuild": NATIVE_BUILD, "qualification": "unqualified"},
                "codex": {"observedBuild": None, "qualification": "unqualified"}}
MAX_VERSION = 1_000_000
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_INVENTORY_KEYS = {"format", "componentClass", "host", "hostBuild", "version",
                   "parentSha256", "entries", "entriesSha256", "effectClass",
                   "settings", "provenance", "executionAuthorization"}
_PROFILE_KEYS = {"format", "version", "componentClass", "host", "hostSupport",
                 "inventory", "inventorySha256", "deleted", "parentSha256",
                 "inputSha256", "effectClass", "settings", "approvedSettingsSha256",
                 "provenance", "policies", "limits", "schemas", "admission",
                 "executionAuthorization"}
_PROVENANCE_KEYS = {"origin", "file", "revision", "sha256", "terms",
                    "noticesRetained", "modificationNotice"}
_SETTING_KEYS = {"model", "effort", "route"}


class ProfileError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-profile"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-profile") -> None:
    if not condition:
        raise ProfileError(reason)


def _keys(value: Any, fields: set[str], reason: str = "invalid-profile") -> None:
    _require(type(value) is dict and set(value) == fields, reason)


def _hash(value: Any, reason: str = "invalid-profile") -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, reason)


def _optional_hash(value: Any) -> None:
    if value is not None:
        _hash(value)


def _parse(raw: Any) -> dict:
    try:
        return parse_json(raw)
    except InvalidDecision as exc:
        raise ProfileError("input-budget-exceeded" if exc.reason == "input-budget-exceeded"
                           else "invalid-json") from None


def _path(value: Any, *, depth: int) -> str:
    try:
        return normalize_rel(value, depth=depth)
    except SurfaceError:
        raise ProfileError("invalid-path") from None


def derive_admission(component_class: str, effect_class: str) -> tuple[str, str | None]:
    """Return ``(state, blocker)``; the only source of an admission state."""
    _require(component_class in CLASSES, "unknown-class")
    _require(effect_class in EFFECTS, "invalid-effect")
    _require(effect_class != "E5", "excluded-effect")
    if component_class in ("C6", "C7", "C8"):
        return "blocked", "no-containment-qualification"
    if effect_class in ("E3", "E4"):
        return "blocked", "effects-not-adopted"
    if component_class in ("C3", "C4", "C5"):
        return "blocked", "owner-task-unimplemented"
    return "implemented", None


def _provenance(value: Any) -> None:
    _keys(value, _PROVENANCE_KEYS, "invalid-provenance")
    _require(value["origin"] in ("original", "adapted"), "invalid-provenance")
    rest = {key: value[key] for key in _PROVENANCE_KEYS - {"origin"}}
    if value["origin"] == "original":
        _require(all(v is None for v in rest.values()), "invalid-provenance")
        return
    try:
        _path(value["file"], depth=6)
    except ProfileError:
        raise ProfileError("invalid-provenance") from None
    _require(type(value["revision"]) is str and _COMMIT.fullmatch(value["revision"]) is not None
             and type(value["terms"]) is str and _ID.fullmatch(value["terms"]) is not None
             and value["noticesRetained"] is True and value["modificationNotice"] is True,
             "invalid-provenance")
    _hash(value["sha256"], "invalid-provenance")


def _settings(value: Any) -> bool:
    """Validate the selection shape; return whether anything is selected."""
    _keys(value, _SETTING_KEYS, "invalid-settings")
    for name in ("model", "effort"):
        _require(value[name] is None or (type(value[name]) is str and
                                          _ID.fullmatch(value[name]) is not None),
                 "invalid-settings")
    _require(value["route"] is None or value["route"] in ROUTES, "invalid-settings")
    return any(v is not None for v in value.values())


def _rows(value: Any, *, ops: bool) -> list[dict]:
    _require(type(value) is list)
    _require(len(value) <= 2 * LIMITS["maxFiles"], "inventory-budget-exceeded")
    paths = []
    for row in value:
        _keys(row, {"path", "sha256", "sizeBytes", "op"} if ops else
              {"path", "sha256", "sizeBytes"})
        _path(row["path"], depth=LIMITS["maxPathDepth"])
        _hash(row["sha256"])
        _require(type(row["sizeBytes"]) is int and 0 <= row["sizeBytes"] <= LIMITS["maxFileBytes"],
                 "inventory-budget-exceeded")
        if ops:
            _require(row["op"] in OPS, "invalid-op")
        paths.append(row["path"])
    _ordered_paths(paths)
    return value


def _ordered_paths(paths: list[str]) -> None:
    _require(paths == sorted(paths) and len(set(paths)) == len(paths),
             "duplicate-or-unordered-inventory")
    _require(len({p.casefold() for p in paths}) == len(paths), "path-alias")


def _surface(component_class: str, paths: list[str]) -> None:
    """Positive root/suffix inventory with protected layers taking precedence."""
    for path in paths:
        parts = path.split("/")
        _require(not any(unicodedata.category(c).startswith("Z") for c in path), "invalid-path")
        _require(not any(p.startswith(".") or
                         p.split(".", 1)[0].rstrip(" .").casefold() in PROTECTED_COMPONENTS
                         for p in parts), "protected-component")
        _require(len(parts) >= 2 and parts[0] == ROOTS[component_class] and
                 path.endswith(SUFFIXES), "path-outside-surface")


def _budget(rows: list[dict]) -> None:
    _require(rows, "empty-inventory")
    _require(len(rows) <= LIMITS["maxFiles"] and
             sum(r["sizeBytes"] for r in rows) <= LIMITS["maxCandidateBytes"],
             "inventory-budget-exceeded")


def _admission(value: Any, component_class: str, effect_class: str) -> None:
    _keys(value, {"state", "blocker"})
    _require(value["state"] in STATES, "invalid-admission")
    _require(value["state"] not in ("qualified", "enabled"), "state-escalation")
    state, blocker = derive_admission(component_class, effect_class)
    _require(value == {"state": state, "blocker": blocker}, "admission-mismatch")


@dataclass(frozen=True)
class ComponentProfile:
    """Immutable parsed profile; construction is not independent verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def version(self) -> int:
        return self.data["version"]

    def to_dict(self) -> dict:
        """Return an independent mutable copy of the validated wire record."""
        return thaw(self.data)


def parse_profile(raw: bytes) -> ComponentProfile:
    """Parse strict bounded UTF-8 JSON and revalidate every compiler invariant."""
    value = _parse(raw)
    _keys(value, _PROFILE_KEYS)
    _require(value["format"] == FORMAT, "unsupported-version")
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    component_class, effect_class = value["componentClass"], value["effectClass"]
    _require(component_class in CLASSES, "unknown-class")
    _require(value["host"] in HOSTS, "unknown-host")
    _require(value["host"] == "claude", "host-refused")
    _require(type(value["version"]) is int and 1 <= value["version"] <= MAX_VERSION,
             "invalid-version")
    _keys(value["hostSupport"], set(HOSTS))
    for host, row in value["hostSupport"].items():
        _keys(row, {"observedBuild", "qualification"})
        _require(row["qualification"] == "unqualified", "state-escalation")
        _require(row == HOST_SUPPORT[host], "host-build-drift")
    rows = _rows(value["inventory"], ops=False)
    paths = [r["path"] for r in rows]
    deleted = value["deleted"]
    _require(type(deleted) is list and len(deleted) <= LIMITS["maxFiles"], "invalid-profile")
    for path in deleted:
        _path(path, depth=LIMITS["maxPathDepth"])
    _ordered_paths(deleted)
    _surface(component_class, paths + deleted)
    _ordered_paths(sorted(paths + deleted))
    _budget(rows)
    _hash(value["inventorySha256"])
    _require(value["inventorySha256"] == digest(rows), "inventory-digest-mismatch")
    _optional_hash(value["parentSha256"])
    _hash(value["inputSha256"])
    _require((value["parentSha256"] is None) == (value["version"] == 1), "stale-parent")
    _require(value["parentSha256"] is not None or not deleted, "stale-parent")
    selected = _settings(value["settings"])
    _require((value["approvedSettingsSha256"] is not None) == selected, "invalid-settings")
    _optional_hash(value["approvedSettingsSha256"])
    _provenance(value["provenance"])
    _require(all(canonical(value[k]) == canonical(c) for k, c in (
        ("policies", POLICIES), ("limits", LIMITS), ("schemas", SCHEMAS))), "unsupported-profile")
    _admission(value["admission"], component_class, effect_class)
    return ComponentProfile(freeze(value), canonical(value))


def verify_profile(raw: bytes, *, expected_sha256: str,
                   approved_settings: Mapping[str, Any] | None = None,
                   expected_approved_sha256: str | None = None) -> ComponentProfile:
    """Reparse and compare a trusted full identity; equality is not authority.

    ``parse_profile`` alone cannot show that selected settings were approved or
    that deletions match a parent. When settings are selected, supply the approved
    list and its trusted hash here; it must hash to the profile's recorded value.
    """
    _hash(expected_sha256, "invalid-expected-hash")
    profile = parse_profile(raw)
    _require(profile.sha256 == expected_sha256, "profile-drift")
    recorded = profile.data["approvedSettingsSha256"]
    if recorded is not None:
        _require(expected_approved_sha256 == recorded, "approved-settings-drift")
        _within_approved(profile.data["settings"], approved_settings, recorded)
    return profile


def _approved(approved: Any, expected: Any) -> dict:
    approved = thaw(approved)
    _require(type(approved) is dict and set(approved) == {"models", "efforts", "routes"},
             "approved-settings-drift")
    for name in ("models", "efforts", "routes"):
        _require(type(approved[name]) is list and all(
            type(v) is str and _ID.fullmatch(v) is not None for v in approved[name]),
            "approved-settings-drift")
    _require(set(approved["routes"]) <= set(ROUTES), "approved-settings-drift")
    _hash(expected, "approved-settings-drift")
    _require(digest(approved) == expected, "approved-settings-drift")
    return approved


def _within_approved(settings: Mapping[str, Any], approved_settings: Any,
                     expected_sha256: Any) -> None:
    _require(approved_settings is not None, "settings-not-approved")
    approved = _approved(approved_settings, expected_sha256)
    for name, key in (("model", "models"), ("effort", "efforts"), ("route", "routes")):
        _require(settings[name] is None or settings[name] in approved[key],
                 "settings-outside-approved")


def _resolve(entries: list[dict], parent: ComponentProfile | None) -> tuple[list[dict], list[str]]:
    """Apply explicit inherit/override/add/delete semantics against the parent."""
    before = {r["path"]: r for r in parent.data["inventory"]} if parent else {}
    kept, deleted, seen = [], [], set()
    for row in entries:
        path, op = row["path"], row["op"]
        old = before.get(path)
        if op == "add":
            _require(old is None, "path-exists")
        else:
            _require(old is not None, "path-missing")
            same = (old["sha256"], old["sizeBytes"]) == (row["sha256"], row["sizeBytes"])
            if op == "override":
                _require(not same, "override-unchanged")
            else:
                _require(same, "inherit-drift" if op == "inherit" else "delete-mismatch")
            seen.add(path)
        if op == "delete":
            deleted.append(path)
        else:
            kept.append({"path": path, "sha256": row["sha256"], "sizeBytes": row["sizeBytes"]})
    _require(seen == set(before), "silent-omission")
    return kept, deleted


def compile_inventory(raw: bytes, *, expected_input_sha256: str,
                      parent_raw: bytes | None = None,
                      expected_parent_sha256: str | None = None,
                      approved_settings: Mapping[str, Any] | None = None,
                      expected_approved_sha256: str | None = None) -> ComponentProfile:
    """Compile one task-local inventory into an immutable, non-enabled profile.

    ``expected_input_sha256`` is the SHA-256 of the canonical inventory JSON from
    the caller's trusted observation. A parent profile is accepted only with its
    own trusted full hash. Raises ``ProfileError`` with a fixed reason; never a
    partial profile.
    """
    _hash(expected_input_sha256, "invalid-expected-hash")
    value = _parse(raw)
    _require(sha256(canonical(value)).hexdigest() == expected_input_sha256, "input-drift")
    _keys(value, _INVENTORY_KEYS)
    _require(value["format"] == INVENTORY_FORMAT, "unsupported-version")
    _require(value["executionAuthorization"] is False, "unsupported-profile")
    component_class, effect_class = value["componentClass"], value["effectClass"]
    _require(component_class in CLASSES, "unknown-class")
    _require(value["host"] in HOSTS, "unknown-host")
    _require(value["host"] == "claude", "host-refused")
    _require(value["hostBuild"] == HOST_SUPPORT["claude"]["observedBuild"], "host-build-drift")
    state, blocker = derive_admission(component_class, effect_class)
    version = value["version"]
    _require(type(version) is int and 1 <= version <= MAX_VERSION, "invalid-version")
    parent = None
    if parent_raw is not None:
        _require(expected_parent_sha256 is not None, "invalid-expected-hash")
        parent = verify_profile(parent_raw, expected_sha256=expected_parent_sha256)
        _require(parent.data["componentClass"] == component_class and
                 parent.data["host"] == value["host"], "parent-mismatch")
    else:
        _require(expected_parent_sha256 is None, "invalid-expected-hash")
    _require(value["parentSha256"] == (parent.sha256 if parent else None), "stale-parent")
    expected_version = parent.version + 1 if parent else 1
    _require(version >= expected_version, "stale-version")
    _require(version <= expected_version, "future-version")
    entries = _rows(value["entries"], ops=True)
    _surface(component_class, [r["path"] for r in entries])
    _hash(value["entriesSha256"])
    _require(value["entriesSha256"] == digest(entries), "inventory-digest-mismatch")
    kept, deleted = _resolve(entries, parent)
    _budget(kept)
    selected = _settings(value["settings"])
    approved_sha = None
    if selected:
        _within_approved(value["settings"], approved_settings, expected_approved_sha256)
        approved_sha = expected_approved_sha256
    _provenance(value["provenance"])
    profile = {
        "format": FORMAT, "version": version, "componentClass": component_class,
        "host": value["host"], "hostSupport": thaw(HOST_SUPPORT), "inventory": kept,
        "inventorySha256": digest(kept), "deleted": deleted,
        "parentSha256": parent.sha256 if parent else None,
        "inputSha256": expected_input_sha256, "effectClass": effect_class,
        "settings": value["settings"], "approvedSettingsSha256": approved_sha,
        "provenance": value["provenance"], "policies": dict(POLICIES),
        "limits": dict(LIMITS), "schemas": thaw(SCHEMAS),
        "admission": {"state": state, "blocker": blocker},
        "executionAuthorization": False,
    }
    return parse_profile(canonical(profile))
