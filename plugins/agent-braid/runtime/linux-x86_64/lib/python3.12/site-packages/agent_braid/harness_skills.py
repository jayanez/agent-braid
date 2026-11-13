# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T003 lazy skill loading and reusable workflow/context profiles.

Original implementation. It maps only the concepts of harness2 ``core/tree.py``
(skill surface layout, frontmatter fields, script-reference checks) and carries no
upstream text; ``core/prompts.py`` has no pinned hash and is not reused (contract
section 12, question 4). The module is pure: it reads no file, starts no process,
opens no network connection and issues no grant. Every record keeps
``executionAuthorization`` false and nothing is enabled.

A C3 ``ComponentProfile`` (``harness_components``) lists inert ``.md``/``.txt`` files
under ``skills/<name>/``. ``compile_catalog`` verifies the profile against a trusted
full hash, verifies every inventory file's bytes, parses the strict frontmatter of
each ``SKILL.md`` and emits a descriptor-only ``SkillCatalog``: names, bounded
descriptions, triggers, dependencies and in-directory references, never a body.
Bodies enter a ``SkillSession`` only through ``load`` (or a workflow ``advance``),
one named skill plus its dependencies at a time. Bytes are re-supplied and re-hashed
at every load, so a stale or forged body refuses, including after ``compact``.
Referenced files are screened like skill text.
A body that does not fit the context budget refuses whole; it is never truncated.

Skills are untrusted data. Frontmatter cannot carry authority, eager-load or
configuration keys. The session pins caller-supplied constraints ahead of every
loaded skill, renders skill text as line-quoted data, and compaction can evict skill
bodies but never the constraints. The constraint-weakening scan is a heuristic
refusal of obvious override phrasing, not a proof; the structural defenses are the
pinned constraints, the quoting and the absence of any authority field.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata
from typing import Any

from .harness_components import (
    LIMITS, ProfileError, ROOTS, SUFFIXES, verify_profile)
from .harness_context import ContextBudget, ContextPackage, _pack
from .harness_experience import ExperienceError, screen_text
from .harness_surface import SurfaceError, normalize_rel
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

FORMAT = "braid-harness-skills/v0.1"
WORKFLOW_FORMAT = "braid-harness-workflow/v0.1"
COMPACTION_FORMAT = "braid-harness-skill-compaction/v0.1"
TRUST = "untrusted-skill"
ROOT = ROOTS["C3"]
MAX_SKILLS = 16
MAX_DESCRIPTION = 240
MAX_TRIGGERS = 8
MAX_TRIGGER = 40
MIN_TRIGGER = 3
MAX_DEPENDENCIES = 4
MAX_DEPENDENCY_DEPTH = 4
MAX_REFERENCES = 4
MAX_MATCH_CHARS = 16_384
MAX_STEPS = 16
MAX_CONSTRAINTS = 8
MAX_CONSTRAINT_CHARS = 512
MAX_LINE = 400
_ENTRIES = LIMITS["maxContextEntries"]
_BYTES = LIMITS["maxContextBytes"]
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,31}\Z")
_TRIGGER = re.compile(r"[a-z0-9]+(?:[ -][a-z0-9]+)*\Z")
_LINE = re.compile(r"([A-Za-z][A-Za-z-]{0,23}):(?: (.*))?\Z")
# Script-like paths in text: parent traversal, absolute paths, script files and directories.
_ESCAPE = re.compile(r"(?:^|[\s`(\[\"'])(?:\.\./|/[A-Za-z0-9_.~-]+/|~/)")
_SCRIPT = re.compile(r"\b[\w./-]+\.(?:sh|bash|zsh|py|js|mjs|ts|rb|pl|php|ps1|bat|cmd|exe)\b"
                     r"|\bscripts?/", re.IGNORECASE)
_LOWER = {c: c + 32 for c in range(ord("A"), ord("Z") + 1)}
_FIELDS = ("name", "description", "triggers", "dependencies", "references")
_EAGER = frozenset({"eager", "autoload", "always", "preload", "lazy", "autoapply",
                    "autoload-body", "load"})
# Heuristic refusal of obvious override phrasing in untrusted skill text.
_WEAKEN = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\b(ignore|disregard|override|overrule|bypass|forget|disable|skip|weaken|relax|waive)\b"
    r"[^\n]{0,80}\b(constitution|constraints?|polic(?:y|ies)|rules?|instructions?|verifiers?|"
    r"permissions?|guardrails?|safety|checks?|limits?|budgets?|authority|approvals?|grants?)\b",
    r"\b(constitution|constraints?|polic(?:y|ies)|rules?|instructions?|verifiers?|permissions?|"
    r"guardrails?|safety|checks?|limits?|budgets?|authority|approvals?|requirements?|grants?)\b"
    r"[^\n]{0,60}\b(waived|void|optional|suspended|lifted|no longer (?:apply|applies|bind|"
    r"binding|required)|not (?:required|binding))\b",
))


class SkillError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-skill"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise SkillError(reason)


def _parse(raw: Any, reason: str) -> dict:
    try:
        return parse_json(raw)
    except InvalidDecision as exc:
        raise SkillError("input-budget-exceeded" if exc.reason == "input-budget-exceeded"
                         else reason) from None


def _hash(value: Any, reason: str) -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, reason)


# --- strict skill document -------------------------------------------------
@dataclass(frozen=True)
class _Skill:
    name: str
    description: str
    triggers: tuple
    dependencies: tuple
    references: tuple


def _decode(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise SkillError("unsupported-encoding") from None
    _require(not any(unicodedata.category(c) in {"Cc", "Cf", "Cs", "Zl", "Zp"} and c not in "\n\t"
                     for c in text), "unsupported-encoding")
    _require(not text.lstrip().startswith("#!"), "executable-content")
    return text


def _scan_text(text: str) -> None:
    """Refuse obvious override phrasing and script-like paths in untrusted text."""
    flat = " ".join(text.split())
    _require(not any(p.search(line) for p in _WEAKEN for line in (flat, *text.split("\n"))),
             "constraint-weakening")
    _require(_ESCAPE.search(text) is None, "reference-escapes-skill")
    _require(_SCRIPT.search(text) is None, "executable-reference")


def _list(value: str | None, *, limit: int, reason: str) -> tuple:
    if not value:
        return ()
    items = tuple(value.split(", "))
    _require(len(items) <= limit and len(set(items)) == len(items), reason)
    return items


def _parse_skill(raw: bytes) -> _Skill:
    text = _decode(raw)
    _require(text.startswith("---\n"), "invalid-frontmatter")
    end = text.find("\n---\n", 3)
    _require(end > 0, "invalid-frontmatter")
    header, body = text[4:end], text[end + 5:]
    _require(body.strip() != "", "invalid-frontmatter")
    fields: dict[str, str] = {}
    for line in header.split("\n"):
        match = _LINE.fullmatch(line) if len(line) <= MAX_LINE else None
        _require(match is not None, "invalid-frontmatter")
        key, value = match.group(1), match.group(2) or ""
        _require(key.casefold() not in _EAGER, "eager-load-refused")
        _require(key in _FIELDS and key not in fields, "invalid-frontmatter")
        fields[key] = value
    _require({"name", "description", "triggers"} <= set(fields), "invalid-frontmatter")
    name = fields["name"]
    _require(_NAME.fullmatch(name) is not None, "invalid-frontmatter")
    try:
        description = screen_text(fields["description"], MAX_DESCRIPTION)
    except ExperienceError:
        raise SkillError("invalid-description") from None
    triggers = _list(fields["triggers"], limit=MAX_TRIGGERS, reason="invalid-trigger")
    _require(triggers and all(
        MIN_TRIGGER <= len(t) <= MAX_TRIGGER and _TRIGGER.fullmatch(t) for t in triggers),
        "invalid-trigger")
    dependencies = _list(fields.get("dependencies"), limit=MAX_DEPENDENCIES,
                         reason="invalid-dependency")
    _require(all(_NAME.fullmatch(d) for d in dependencies), "invalid-dependency")
    references = _list(fields.get("references"), limit=MAX_REFERENCES, reason="invalid-reference")
    _scan_text(body)
    return _Skill(name, description, triggers, dependencies, references)


def _resolve_reference(name: str, reference: str, paths: frozenset) -> str:
    _require(reference != "SKILL.md", "reference-self")
    try:
        normalize_rel(reference, depth=2)
    except SurfaceError:
        raise SkillError("reference-escapes-skill") from None
    _require(reference.endswith(SUFFIXES), "executable-reference")
    full = f"{ROOT}/{name}/{reference}"
    _require(full in paths, "reference-missing")
    return full


def _collide(first: tuple, second: tuple) -> bool:
    """Contained, or one trigger's tail equals the other's head (a shared ambiguous phrase)."""
    short, long_ = sorted((first, second), key=len)
    if any(long_[i:i + len(short)] == short for i in range(len(long_) - len(short) + 1)):
        return True
    return any(first[-n:] == second[:n] or second[-n:] == first[:n]
               for n in range(1, min(len(first), len(second)) + 1))


def _check_triggers(skills: list[_Skill]) -> None:
    for i, one in enumerate(skills):
        for other in skills[i + 1:]:
            _require(not any(_collide(tuple(re.split("[ -]", a)), tuple(re.split("[ -]", b)))
                             for a in one.triggers for b in other.triggers), "trigger-collision")


def _closure(name: str, deps: Mapping[str, tuple], stack: tuple = ()) -> list[str]:
    """Dependencies first, then ``name``; refuses cycles and over-deep chains."""
    _require(name not in stack, "dependency-cycle")
    _require(len(stack) <= MAX_DEPENDENCY_DEPTH, "dependency-depth")
    order: list[str] = []
    for dep in deps[name]:
        _require(dep in deps, "unknown-dependency")
        order.extend(n for n in _closure(dep, deps, stack + (name,)) if n not in order)
    order.append(name)
    return order


@dataclass(frozen=True)
class SkillCatalog:
    """Immutable descriptor-only catalog; construction is not independent verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        """Independent mutable copy of the validated wire record."""
        return thaw(self.data)

    def descriptors(self) -> tuple:
        """Catalog rows (metadata only); no body is ever part of the catalog."""
        return tuple(self.data["skills"])

    def _lookup(self, name: str) -> Mapping:
        return next((s for s in self.data["skills"] if s["name"] == name), None)

    def closure(self, name: str) -> tuple:
        deps = {s["name"]: tuple(s["dependencies"]) for s in self.data["skills"]}
        _require(type(name) is str and name in deps, "unknown-skill")
        return tuple(_closure(name, deps))

    def match(self, text: str) -> tuple:
        """Names of skills whose triggers occur as whole words in ``text``; loads nothing."""
        _require(type(text) is str, "invalid-text")
        _require(len(text) <= MAX_MATCH_CHARS, "input-budget-exceeded")
        folded = " ".join(re.split(r"[ \t\n\r\f\v]+", text.translate(_LOWER)))
        return tuple(sorted(
            s["name"] for s in self.data["skills"]
            if any(re.search(r"(?<![a-z0-9-])" + re.escape(t) + r"(?![a-z0-9-])", folded)
                   for t in s["triggers"])))


def _verified(contents: Mapping, row: Mapping, stale: str) -> bytes:
    raw = contents.get(row["path"])
    _require(raw is not None, "missing-content")
    _require(type(raw) is bytes and len(raw) == row["sizeBytes"] and
             sha256(raw).hexdigest() == row["sha256"], stale)
    return raw


def compile_catalog(profile_raw: bytes, *, expected_profile_sha256: str,
                    contents: Mapping[str, bytes]) -> SkillCatalog:
    """Compile a trusted C3 profile and its verified file bytes into a descriptor catalog.

    ``contents`` must hold exactly the profile inventory's paths with the declared
    size and SHA-256. Raises ``SkillError`` with a fixed reason; never a partial
    catalog. Profiles that select model, effort or route settings are not supported.
    """
    try:
        profile = verify_profile(profile_raw, expected_sha256=expected_profile_sha256)
    except ProfileError:
        raise SkillError("profile-refused") from None
    pdata = profile.data
    _require(pdata["componentClass"] == "C3" and pdata["host"] == "claude", "profile-class")
    _require(pdata["effectClass"] in ("E0", "E1", "E2") and
             pdata["admission"]["blocker"] in (None, "owner-task-unimplemented"),
             "profile-effect")
    rows = pdata["inventory"]
    _require(isinstance(contents, Mapping), "invalid-contents")
    paths = frozenset(r["path"] for r in rows)
    _require(all(type(p) is str for p in contents) and set(contents) <= paths,
             "not-in-inventory")
    verified = {r["path"]: _verified(contents, r, "stale-content") for r in rows}
    for path, raw in verified.items():
        if not path.endswith("/SKILL.md"):
            _scan_text(_decode(raw))  # referenced files get the same screening as skill text
    docs: dict[str, str] = {}
    others: dict[str, list[str]] = {}
    for path in sorted(paths):
        parts = path.split("/")
        _require(len(parts) >= 3 and parts[0] == ROOT and _NAME.fullmatch(parts[1]) is not None,
                 "invalid-skill-path")
        if parts[-1] == "SKILL.md":
            _require(len(parts) == 3, "invalid-skill-path")
            docs[parts[1]] = path
        else:
            others.setdefault(parts[1], []).append(path)
    _require(len(docs) <= MAX_SKILLS, "skill-budget-exceeded")
    _require(set(others) <= set(docs), "missing-skill-file")
    parsed = []
    for name in sorted(docs):
        skill = _parse_skill(verified[docs[name]])
        _require(skill.name == name, "name-mismatch")
        parsed.append(skill)
    _check_triggers(parsed)
    deps = {s.name: s.dependencies for s in parsed}
    for name in deps:
        _closure(name, deps)
    skills, referenced = [], set()
    for skill in parsed:
        refs = [_resolve_reference(skill.name, r, paths) for r in skill.references]
        referenced.update(refs)
        path = docs[skill.name]
        skills.append({
            "name": skill.name, "path": path, "sha256": sha256(verified[path]).hexdigest(),
            "sizeBytes": len(verified[path]), "description": skill.description,
            "triggers": list(skill.triggers), "dependencies": list(skill.dependencies),
            "references": refs, "trust": TRUST})
    _require(all(p in referenced for ps in others.values() for p in ps), "unreferenced-file")
    wire = {"format": FORMAT, "profileSha256": profile.sha256,
            "inventorySha256": pdata["inventorySha256"], "componentClass": "C3",
            "host": pdata["host"], "admission": thaw(pdata["admission"]),
            "provenance": thaw(pdata["provenance"]), "skills": skills,
            "limits": {"maxSkills": MAX_SKILLS, "maxContextEntries": _ENTRIES,
                       "maxContextBytes": _BYTES},
            "executionAuthorization": False}
    return SkillCatalog(freeze(wire), canonical(wire))


def verify_catalog(raw: bytes, *, expected_sha256: str, profile_raw: bytes,
                   expected_profile_sha256: str, contents: Mapping[str, bytes]) -> SkillCatalog:
    """Recompile from the trusted profile and bytes; any forged or stale field refuses."""
    _hash(expected_sha256, "invalid-expected-hash")
    value = _parse(raw, "catalog-drift")
    catalog = compile_catalog(profile_raw, expected_profile_sha256=expected_profile_sha256,
                              contents=contents)
    _require(canonical(value) == catalog.canonical_bytes and
             catalog.sha256 == expected_sha256, "catalog-drift")
    return catalog


# --- reusable workflow profile ---------------------------------------------
@dataclass(frozen=True)
class WorkflowProfile:
    """Immutable ordered skill steps with a context budget, bound to one catalog."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def steps(self) -> tuple:
        return self.data["steps"]

    @property
    def catalog_sha256(self) -> str:
        return self.data["catalogSha256"]

    def to_dict(self) -> dict:
        return thaw(self.data)


def _budget(value: Any) -> tuple[int, int]:
    _require(type(value) is dict and set(value) == {"maxEntries", "maxTotalBytes"},
             "invalid-budget")
    entries, total = value["maxEntries"], value["maxTotalBytes"]
    _require(type(entries) is int and type(total) is int and 1 <= entries <= _ENTRIES and
             1 <= total <= _BYTES, "invalid-budget")
    return entries, total


def compile_workflow(raw: bytes, *, catalog: SkillCatalog, expected_sha256: str) -> WorkflowProfile:
    """Compile an exact workflow record against ``catalog``; the worst case must fit its budget."""
    _hash(expected_sha256, "invalid-expected-hash")
    value = _parse(raw, "invalid-workflow")
    _require(sha256(canonical(value)).hexdigest() == expected_sha256, "workflow-drift")
    _require(set(value) == {"format", "name", "catalogSha256", "steps", "budget",
                            "executionAuthorization"}, "invalid-workflow")
    _require(value["format"] == WORKFLOW_FORMAT, "unsupported-version")
    _require(value["executionAuthorization"] is False, "invalid-workflow")
    _require(type(value["name"]) is str and _NAME.fullmatch(value["name"]) is not None,
             "invalid-workflow")
    _hash(value["catalogSha256"], "invalid-workflow")
    _require(value["catalogSha256"] == catalog.sha256, "stale-catalog")
    steps = value["steps"]
    _require(type(steps) is list and 1 <= len(steps) <= MAX_STEPS and
             all(type(s) is str for s in steps) and len(set(steps)) == len(steps),
             "invalid-workflow")
    entries, total = _budget(value["budget"])
    needed: list[str] = []
    for step in steps:
        needed.extend(n for n in catalog.closure(step) if n not in needed)
    size = sum(catalog._lookup(n)["sizeBytes"] for n in needed)
    _require(len(needed) <= entries and size <= total, "context-budget-exceeded")
    return WorkflowProfile(freeze(value), canonical(value))


# --- lazy session ----------------------------------------------------------
def _constraints(value: Any) -> tuple:
    _require(type(value) in (tuple, list) and 1 <= len(value) <= MAX_CONSTRAINTS and
             all(type(c) is str and 0 < len(c) <= MAX_CONSTRAINT_CHARS and c == c.strip() and
                 not any(unicodedata.category(ch)[0] in "CZ" and ch != " " for ch in c)
                 for c in value), "invalid-constraints")
    return tuple(value)


class SkillSession:
    """Lazy per-task skill context: constraints pinned first, bodies loaded on demand."""

    def __init__(self, catalog: SkillCatalog, *, constraints: Any,
                 workflow: WorkflowProfile | None = None):
        _require(type(catalog) is SkillCatalog, "invalid-catalog")
        _require(workflow is None or type(workflow) is WorkflowProfile, "invalid-workflow")
        self._catalog = catalog
        self._constraints = _constraints(constraints)
        self._workflow = workflow
        self._loaded: dict[str, bytes] = {}
        self._cursor = 0
        if workflow is None:
            self._entries, self._bytes = _ENTRIES, _BYTES
            self._allowed = None
        else:
            _require(workflow.catalog_sha256 == catalog.sha256, "stale-catalog")
            budget = workflow.data["budget"]
            self._entries, self._bytes = budget["maxEntries"], budget["maxTotalBytes"]
            self._allowed = frozenset(n for s in workflow.steps for n in catalog.closure(s))

    @property
    def constraints_sha256(self) -> str:
        return digest(list(self._constraints))

    @property
    def loaded(self) -> tuple:
        return tuple(self._loaded)

    def load(self, name: str, contents: Mapping[str, bytes]) -> ContextPackage:
        """Load one named skill and its missing dependencies, all or nothing."""
        order = self._catalog.closure(name)
        _require(self._allowed is None or name in self._allowed, "outside-workflow")
        needed = [n for n in order if n not in self._loaded]
        fetched = {n: self._fetch(n, contents) for n in needed}
        _require(len(self._loaded) + len(fetched) <= self._entries and
                 sum(map(len, self._loaded.values())) + sum(map(len, fetched.values()))
                 <= self._bytes, "context-budget-exceeded")
        self._loaded.update(fetched)
        return self.package()

    def advance(self, contents: Mapping[str, bytes]) -> ContextPackage:
        """Load the next workflow step; one step per call."""
        _require(self._workflow is not None, "no-workflow")
        _require(self._cursor < len(self._workflow.steps), "workflow-complete")
        package = self.load(self._workflow.steps[self._cursor], contents)
        self._cursor += 1
        return package

    def _fetch(self, name: str, contents: Mapping[str, bytes]) -> bytes:
        _require(isinstance(contents, Mapping), "invalid-contents")
        return _verified(contents, self._catalog._lookup(name), "stale-skill")

    def package(self) -> ContextPackage:
        """Loaded skill bodies as untrusted, hash-labelled context entries."""
        budget = ContextBudget(self._entries, self._bytes, self._bytes, self._bytes)
        candidates = [(n, self._catalog._lookup(n)["path"], TRUST, raw)
                      for n, raw in self._loaded.items()]
        return _pack("skill", candidates, [], budget, frozenset())

    def render(self) -> str:
        """Pinned constraints first, then line-quoted skill data."""
        lines = [f"<<<constraints sha256={self.constraints_sha256}>>>"]
        lines.extend("| " + c for c in self._constraints)
        lines.append("<<<end constraints>>>")
        if self._loaded:
            lines.append(self.package().render())
        return "\n".join(lines)

    def compact(self) -> Mapping:
        """Evict every loaded body; the constraints stay and the receipt names each loss."""
        evicted = [{"name": n, "sha256": sha256(raw).hexdigest(), "sizeBytes": len(raw)}
                   for n, raw in self._loaded.items()]
        self._loaded.clear()
        return freeze({"format": COMPACTION_FORMAT, "catalogSha256": self._catalog.sha256,
                       "retainedConstraintsSha256": self.constraints_sha256,
                       "evicted": evicted, "executionAuthorization": False})
