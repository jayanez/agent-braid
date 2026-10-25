# SPDX-License-Identifier: AGPL-3.0-only
"""Ownership declaration loading and validation (SPEC-057).

Pure, standard-library-only and offline: this module opens no socket, starts no
process and never writes. A declaration is the orchestrator's claim about what
each parallel unit reads, writes, creates and deletes. Validation refuses
malformed or over-bound input before any expansion, with stable diagnostic
codes. A diagnostic carries a code and a location built only from schema-known
member names and array indices; it never echoes a repository string, an unknown
member name or an offending value.

The schema in ``specs/057-claude-orchestration-advisory/contracts`` stays the
published contract. The structural rules below mirror it (a test compares the
patterns and bounds byte for byte); the rules the schema cannot express are
validator rules and are named in ``_check_cross_references``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, NamedTuple

SCHEMA_VERSION = "agent-braid-ownership-declaration/v0.1"
SURFACES = ("workflow-tracks", "linked-sessions", "agent-teams", "batch")
PROVENANCES = ("orchestrator-session", "user-script", "human", "imported")
WRITERS = ("orchestrator", "human", "shared-tree")
RESOURCE_CLASSES = (
    "lockfile",
    "barrel",
    "generated",
    "formatter",
    "schema",
    "cache",
    "config",
    "other",
)

MAX_DECLARATION_BYTES = 1024 * 1024
MIN_UNITS = 2
MAX_UNITS = 32
MAX_PATHS = 512
MAX_STRING = 256
MAX_DEPENDENCIES = 31
MAX_SHARED_RESOURCES = 64
MAX_EXEMPTIONS = 16
MAX_DIAGNOSTICS = 64

RESERVED_UNIT_ID = "unattributed"

# Patterns are copied from the schema; each ends in (?!\n)$ because re.search
# lets a bare $ match before a final line feed.
REF_PATTERN = r"^(?!.*\.\.)(?!.*//)[A-Za-z0-9][A-Za-z0-9._/-]{0,127}(?!\n)$"
COMMIT_PATTERN = r"^[0-9a-f]{40}(?!\n)$"
TOOL_PATTERN = r"^[a-z][a-z0-9_.-]{0,63}(?!\n)$"
VERSION_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,63}(?!\n)$"
IDENT_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}(?!\n)$"
PATH_PATTERN = (
    "^[^\\u0000-\\u001f\\u007f-\\u009f\\u00ad\\u061c\\u115f-\\u1160\\u180e"
    "\\u200b-\\u200f\\u2028-\\u202e\\u2060-\\u206f\\u3164\\ufeff\\uffa0"
    "\\ufff9-\\ufffb\\U000e0000-\\U000e007f]+(?!\\n)$"
)

_REF = re.compile(REF_PATTERN)
_COMMIT = re.compile(COMMIT_PATTERN)
_TOOL = re.compile(TOOL_PATTERN)
_VERSION = re.compile(VERSION_PATTERN)
_IDENT = re.compile(IDENT_PATTERN)
_PATH = re.compile(PATH_PATTERN)

_TOP_MEMBERS = frozenset(
    {"schemaVersion", "base", "provenance", "units", "importedFrom", "unattributedWriterExemptions"}
)
_UNIT_MEMBERS = frozenset(
    {
        "id",
        "surface",
        "reads",
        "criticalReads",
        "writes",
        "creates",
        "deletes",
        "dependsOn",
        "sharedResources",
        "complete",
    }
)
_UNIT_PATH_LISTS = ("reads", "criticalReads", "writes", "creates", "deletes")


class Diagnostic(NamedTuple):
    """A stable refusal reason. ``where`` holds schema member names and indices only."""

    code: str
    where: str


class DeclarationRefused(Exception):
    """A declaration was refused; ``diagnostics`` lists every reason found (bounded)."""

    def __init__(self, diagnostics: tuple[Diagnostic, ...]):
        self.diagnostics = diagnostics
        super().__init__(", ".join(d.code for d in diagnostics[:3]) or "refused")


class _Collector:
    def __init__(self) -> None:
        self._items: list[Diagnostic] = []
        self._overflow = False

    def add(self, code: str, where: str) -> None:
        if len(self._items) < MAX_DIAGNOSTICS:
            self._items.append(Diagnostic(code, where))
        else:
            self._overflow = True

    def result(self) -> tuple[Diagnostic, ...]:
        if self._overflow:
            return (*self._items, Diagnostic("diagnostics-truncated", ""))
        return tuple(self._items)


def _join(where: str, member: str) -> str:
    return f"{where}.{member}" if where else member


def _string(value: Any, where: str, out: _Collector, pattern: re.Pattern[str] | None = None) -> bool:
    """Check type, the 256-character bound and an optional pattern."""
    if not isinstance(value, str):
        out.add("wrong-type", where)
        return False
    if len(value) > MAX_STRING:
        out.add("string-too-long", where)
        return False
    if pattern is not None and pattern.search(value) is None:
        out.add("bad-format", where)
        return False
    return True


def _members(
    value: Any, where: str, out: _Collector, allowed: frozenset[str], required: tuple[str, ...]
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        out.add("wrong-type", where)
        return None
    if any(key not in allowed for key in value):
        out.add("unknown-member", where)
    for name in required:
        if name not in value:
            out.add("missing-member", _join(where, name))
    return value


def _path_list(value: Any, where: str, out: _Collector, *, min_items: int = 0) -> list[str]:
    if not isinstance(value, list):
        out.add("wrong-type", where)
        return []
    if len(value) > MAX_PATHS:
        out.add("too-many-paths", where)
        return []
    if len(value) < min_items:
        out.add("too-few-items", where)
    paths: list[str] = []
    for index, item in enumerate(value):
        if _path(item, f"{where}[{index}]", out):
            paths.append(item)
    if len(set(paths)) != len(paths):
        out.add("duplicate-path", where)
    return paths


def _path(value: Any, where: str, out: _Collector) -> bool:
    if isinstance(value, str) and not value:
        out.add("empty-string", where)
        return False
    if not _string(value, where, out):
        return False
    if _PATH.search(value) is None:
        out.add("forbidden-character", where)
        return False
    return True


def _check_base(value: Any, out: _Collector) -> None:
    base = _members(value, "base", out, frozenset({"ref", "commit"}), ())
    if base is None:
        return
    if not base:
        out.add("missing-member", "base")
    if "ref" in base:
        _string(base["ref"], "base.ref", out, _REF)
    if "commit" in base:
        _string(base["commit"], "base.commit", out, _COMMIT)


def _check_unit(unit: Any, where: str, out: _Collector) -> dict[str, Any] | None:
    data = _members(unit, where, out, _UNIT_MEMBERS, ("id", "surface", "reads", "writes"))
    if data is None:
        return None
    if "id" in data:
        unit_id = data["id"]
        if unit_id == RESERVED_UNIT_ID:
            out.add("reserved-unit-id", _join(where, "id"))
        else:
            _string(unit_id, _join(where, "id"), out, _IDENT)
    if "surface" in data and data["surface"] not in SURFACES:
        out.add("unknown-surface", _join(where, "surface"))
    for name in _UNIT_PATH_LISTS:
        if name in data:
            _path_list(data[name], _join(where, name), out)
    if "dependsOn" in data:
        _check_depends_on(data["dependsOn"], _join(where, "dependsOn"), out)
    if "sharedResources" in data:
        _check_shared_resources(data["sharedResources"], _join(where, "sharedResources"), out)
    if "complete" in data and not isinstance(data["complete"], bool):
        out.add("wrong-type", _join(where, "complete"))
    return data


def _check_depends_on(value: Any, where: str, out: _Collector) -> None:
    if not isinstance(value, list):
        out.add("wrong-type", where)
        return
    if len(value) > MAX_DEPENDENCIES:
        out.add("too-many-dependencies", where)
        return
    valid = [item for index, item in enumerate(value) if _string(item, f"{where}[{index}]", out, _IDENT)]
    if len(set(valid)) != len(valid):
        out.add("duplicate-dependency", where)


def _check_shared_resources(value: Any, where: str, out: _Collector) -> None:
    if not isinstance(value, list):
        out.add("wrong-type", where)
        return
    if len(value) > MAX_SHARED_RESOURCES:
        out.add("too-many-shared-resources", where)
        return
    for index, item in enumerate(value):
        here = f"{where}[{index}]"
        entry = _members(item, here, out, frozenset({"class", "path"}), ("class",))
        if entry is None:
            continue
        if "class" in entry and entry["class"] not in RESOURCE_CLASSES:
            out.add("unknown-resource-class", _join(here, "class"))
        if "path" in entry:
            _path(entry["path"], _join(here, "path"), out)


def _check_provenance(data: dict[str, Any], out: _Collector) -> None:
    provenance = data.get("provenance")
    if "provenance" in data and provenance not in PROVENANCES:
        out.add("unknown-provenance", "provenance")
    imported_from = "importedFrom" in data
    if imported_from:
        origin = _members(
            data["importedFrom"], "importedFrom", out, frozenset({"tool", "version"}), ("tool", "version")
        )
        if origin is not None:
            if "tool" in origin:
                _string(origin["tool"], "importedFrom.tool", out, _TOOL)
            if "version" in origin:
                _string(origin["version"], "importedFrom.version", out, _VERSION)
    if imported_from != (provenance == "imported"):
        out.add("imported-from-mismatch", "importedFrom")


def _check_exemptions(value: Any, out: _Collector) -> list[tuple[str, list[str]]]:
    where = "unattributedWriterExemptions"
    if not isinstance(value, list):
        out.add("wrong-type", where)
        return []
    if len(value) > MAX_EXEMPTIONS:
        out.add("too-many-exemptions", where)
        return []
    rules: list[tuple[str, list[str]]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        here = f"{where}[{index}]"
        rule = _members(item, here, out, frozenset({"ruleId", "writer", "paths"}), ("ruleId", "writer", "paths"))
        if rule is None:
            continue
        if "ruleId" in rule and _string(rule["ruleId"], _join(here, "ruleId"), out, _IDENT):
            if rule["ruleId"] in seen:
                out.add("duplicate-rule-id", _join(here, "ruleId"))
            seen.add(rule["ruleId"])
        if "writer" in rule and rule["writer"] not in WRITERS:
            out.add("unknown-writer", _join(here, "writer"))
        if "paths" in rule:
            rules.append((here, _path_list(rule["paths"], _join(here, "paths"), out, min_items=1)))
    return rules


def _check_cross_references(
    units: list[dict[str, Any] | None], rules: list[tuple[str, list[str]]], out: _Collector
) -> None:
    """Validator rules the schema cannot express.

    - duplicate unit ids;
    - critical reads covered by reads (exact entries only: glob coverage belongs
      to expansion, so a critical read covered only by a pattern is refused here);
    - dependencies naming known units, and no unit depending on itself;
    - exemption rules naming only declared paths (exact entries).
    """
    ids = [u["id"] for u in units if u and isinstance(u.get("id"), str)]
    known = set(ids)
    seen: set[str] = set()
    declared: set[str] = set()
    for index, unit in enumerate(units):
        if unit is None:
            continue
        where = f"units[{index}]"
        unit_id = unit.get("id")
        if isinstance(unit_id, str):
            if unit_id in seen:
                out.add("duplicate-unit-id", _join(where, "id"))
            seen.add(unit_id)
        reads = {p for p in unit.get("reads", []) if isinstance(p, str)} if isinstance(unit.get("reads"), list) else set()
        for name in _UNIT_PATH_LISTS:
            if isinstance(unit.get(name), list):
                declared.update(p for p in unit[name] if isinstance(p, str))
        critical = unit.get("criticalReads")
        if isinstance(critical, list):
            for position, item in enumerate(critical):
                if isinstance(item, str) and item not in reads:
                    out.add("critical-read-not-read", f"{where}.criticalReads[{position}]")
        deps = unit.get("dependsOn")
        if isinstance(deps, list):
            for position, item in enumerate(deps):
                if not isinstance(item, str):
                    continue
                if item == unit_id:
                    out.add("self-dependency", f"{where}.dependsOn[{position}]")
                elif item not in known:
                    out.add("unknown-dependency", f"{where}.dependsOn[{position}]")
        shared = unit.get("sharedResources")
        if isinstance(shared, list):
            declared.update(
                s["path"] for s in shared if isinstance(s, dict) and isinstance(s.get("path"), str)
            )
    for where, paths in rules:
        for position, item in enumerate(paths):
            if item not in declared:
                out.add("exemption-path-undeclared", f"{where}.paths[{position}]")


def validate_declaration(data: Any) -> tuple[Diagnostic, ...]:
    """Return every diagnostic for an already parsed declaration (empty means accepted)."""
    out = _Collector()
    top = _members(data, "", out, _TOP_MEMBERS, ("schemaVersion", "units"))
    if top is None:
        return out.result()
    if "schemaVersion" in top and top["schemaVersion"] != SCHEMA_VERSION:
        out.add("bad-schema-version", "schemaVersion")
    if "base" in top:
        _check_base(top["base"], out)
    _check_provenance(top, out)

    units: list[dict[str, Any] | None] = []
    raw_units = top.get("units")
    if "units" in top:
        if not isinstance(raw_units, list):
            out.add("wrong-type", "units")
        elif len(raw_units) > MAX_UNITS:
            out.add("too-many-units", "units")
        else:
            if len(raw_units) < MIN_UNITS:
                out.add("too-few-units", "units")
            units = [_check_unit(unit, f"units[{i}]", out) for i, unit in enumerate(raw_units)]
    if "base" not in top and any(u is not None and u.get("complete") is True for u in units):
        out.add("complete-without-base", "base")

    rules = _check_exemptions(top["unattributedWriterExemptions"], out) if "unattributedWriterExemptions" in top else []
    _check_cross_references(units, rules, out)
    return out.result()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(_name: str) -> Any:
    raise ValueError("non-finite number")


def load_declaration(raw: bytes | str) -> dict[str, Any]:
    """Parse and validate declaration text; raise ``DeclarationRefused`` on any refusal.

    Over-bound input (more than 1 MiB), invalid UTF-8, invalid JSON, duplicate
    keys and non-finite numbers are refused before structural validation.
    """
    if isinstance(raw, str):
        try:
            raw = raw.encode("utf-8")
        except UnicodeEncodeError:
            raise DeclarationRefused((Diagnostic("invalid-encoding", ""),)) from None
    if len(raw) > MAX_DECLARATION_BYTES:
        raise DeclarationRefused((Diagnostic("input-too-large", ""),))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise DeclarationRefused((Diagnostic("invalid-encoding", ""),)) from None
    try:
        data = json.loads(text, object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise DeclarationRefused((Diagnostic("invalid-json", ""),)) from None
    diagnostics = validate_declaration(data)
    if diagnostics:
        raise DeclarationRefused(diagnostics)
    return data


def load_declaration_file(path: str | Path) -> dict[str, Any]:
    """Read at most one bound's worth of a file, then ``load_declaration``."""
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_DECLARATION_BYTES + 1)
    except OSError:
        raise DeclarationRefused((Diagnostic("unreadable-input", ""),)) from None
    return load_declaration(raw)
