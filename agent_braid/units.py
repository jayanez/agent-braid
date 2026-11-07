# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 REQ-006: the ``units`` request kind of ``analyze-work``.

A host model declares units of work with exact workspace-relative resources and
Article 5 effect kinds. This module validates the declaration, normalizes the
resources lexically (no filesystem access) and builds one AIM 0.2.0-draft record
per unit, in input order, from the construction table in
``specs/069-aim-request-authoring/contracts/analyze-work-request.md``. Every
record is a declaration: coverage is always ``partial`` and the only evidence
item is ``method: declared`` with assurance class 0, so a ``units`` request is
never classified ``independent-candidate``.

Refusals are ``analysis.InvalidAnalysis`` built from fixed text, schema-defined
names and indices only (SPEC-069 REQ-007): request values are never echoed and
unknown keys are tokenized.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from . import analysis
from .analysis import InvalidAnalysis

UNITS_REQUEST_VERSION = "0.1.0-alpha"
CONSTRUCTION_ID = f"agent-braid.units-declaration/{UNITS_REQUEST_VERSION}"
CONSTRUCTION_DIGEST = "sha256:" + hashlib.sha256(CONSTRUCTION_ID.encode("utf-8")).hexdigest()
EFFECT_KINDS = ("read", "write", "call", "transform", "emit", "delete", "deploy")  # Article 5 families
COVERAGE_CLAIMS = ("complete", "partial", "unknown")
# The tooling_mcp adapter bounds (A7); tests keep them equal to MAX_OPERATIONS and MAX_IDENTIFIER_BYTES.
MAX_UNITS = 32
MAX_IDENTIFIER_BYTES = 256

DOMAIN = "workspace-relative paths declared by the host model"
COVERAGE = {"status": "partial", "domain": DOMAIN, "method": f"units declaration ({CONSTRUCTION_ID})"}
EVIDENCE = {
    "property": "independence",
    "method": "declared",
    "domain": DOMAIN,
    "assumptions": [
        "Effects are declared by the host model and not observed by Agent Braid.",
        "The declaration may be incomplete, so coverage is partial.",
        "Resources are compared after lexical normalization only; symbolic links, case-insensitive "
        "file systems, generated files and semantic dependencies are not resolved.",
    ],
    "observationContract": "none: built from the request without filesystem or repository access",
    "executionContract": "no execution; analysis only",
    "assuranceClass": 0,
}
SOURCE = {"kind": "units",
          "description": f"Agent Braid {CONSTRUCTION_ID}; effects declared by the host model, not observed"}

REQUEST_FIELDS = ("unitsRequestVersion", "units")
UNIT_REQUIRED, UNIT_OPTIONAL = ("id", "effects"), ("dependencies", "coverage")
RESOURCE_FORM = ("a workspace-relative path such as docs/guide.md (no scheme or drive letter, "
                 "leading /, .. segment, backslash or control character)")
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:")
_SCOPE = re.compile(r"[0-9a-f]{32}")


def workspace_scope(source_root: Path | str) -> str:
    """The scope written into constructed resources: ``repo://<scope>/<path>``.

    It is the plugin registry's workspace identifier, the first 32 hex digits of the
    SHA-256 of the canonical source root, so the service derives it from its own
    configuration even though the plugin strips ``workspaceId`` from the arguments (A4).
    """
    return hashlib.sha256(str(source_root).encode("utf-8")).hexdigest()[:32]


def _keys(value: dict, required: tuple[str, ...], optional: tuple[str, ...], message: str, pointer: str) -> None:
    allowed = set(required) | set(optional)
    missing = sorted(set(required) - set(value))
    unknown = sorted(analysis.key_token(key) for key in value if key not in allowed)
    if not missing and not unknown:
        return
    detail = (["missing " + ", ".join(missing)] if missing else []) + (["unknown " + ", ".join(unknown)] if unknown else [])
    form = "an object with the properties " + ", ".join(sorted(required))
    if optional:
        form += " and optionally " + ", ".join(sorted(optional))
    raise InvalidAnalysis(message, pointer=pointer, expected=f"{form} ({'; '.join(detail)})")


def _need(condition: bool, message: str, pointer: str, expected: str) -> None:
    if not condition:
        raise InvalidAnalysis(message, pointer=pointer, expected=expected)


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def normalize_resource(value: object, pointer: str) -> str:
    """Lexically normalized workspace-relative path, or a refusal naming ``pointer``.

    Refused: a non-string or blank value, a control character, a backslash, a scheme or
    drive letter, a leading ``/``, a ``..`` segment, and a path with no segment left.
    Then Unicode NFC, ``.`` and empty segments dropped (so a trailing ``/`` disappears).
    """
    _need(_nonblank(value), "invalid effect resource", pointer, RESOURCE_FORM)
    _need(not any(ord(ch) < 0x20 or ch == "\x7f" for ch in value),
          "control characters are not allowed in a resource", pointer, RESOURCE_FORM)
    _need("\\" not in value, "backslashes are not allowed in a resource", pointer, RESOURCE_FORM)
    _need(not _SCHEME.match(value), "schemes and drive letters are not allowed in a resource", pointer, RESOURCE_FORM)
    _need(not value.startswith("/"), "absolute paths are not allowed in a resource", pointer, RESOURCE_FORM)
    segments = value.split("/")
    _need(".." not in segments, "'..' segments are not allowed in a resource", pointer, RESOURCE_FORM)
    kept = [segment for segment in segments if segment not in ("", ".")]
    _need(bool(kept), "resource names no path", pointer, RESOURCE_FORM)
    return unicodedata.normalize("NFC", "/".join(kept))


def _validate_unit(unit: object, base: str) -> dict:
    _need(isinstance(unit, dict), "units must be objects", base,
          "an object with the properties effects, id and optionally coverage, dependencies")
    _keys(unit, UNIT_REQUIRED, UNIT_OPTIONAL, "invalid unit", base)
    identifier = unit["id"]
    _need(_nonblank(identifier), "invalid unit id", f"{base}/id", analysis.NONBLANK)
    _need(len(identifier.encode("utf-8")) <= MAX_IDENTIFIER_BYTES, "Operation identifier exceeds 256 bytes",
          f"{base}/id", f"a non-blank string of at most {MAX_IDENTIFIER_BYTES} UTF-8 bytes")
    dependencies = unit.get("dependencies", [])
    _need(isinstance(dependencies, list), "dependencies must be an array", f"{base}/dependencies",
          "an array of unique unit ids")
    for index, item in enumerate(dependencies):
        _need(_nonblank(item), "invalid dependency", f"{base}/dependencies/{index}", analysis.NONBLANK)
    _need(len(dependencies) == len(set(dependencies)), "duplicate dependency", f"{base}/dependencies",
          "an array of unique unit ids")
    effects = unit["effects"]
    _need(isinstance(effects, list) and bool(effects), "effects must be a nonempty array", f"{base}/effects",
          "a nonempty array of effects")
    normalized = []
    for index, effect in enumerate(effects):
        where = f"{base}/effects/{index}"
        _need(isinstance(effect, dict), "invalid effect", where, analysis.EFFECT_FORM)
        analysis.exact_keys(effect, {"kind", "resource"}, "invalid effect", where)
        _need(effect["kind"] in EFFECT_KINDS, "unsupported effect kind", f"{where}/kind",
              "one of " + ", ".join(EFFECT_KINDS))
        normalized.append({"kind": effect["kind"], "resource": normalize_resource(effect["resource"], f"{where}/resource")})
    if "coverage" in unit:
        _need(unit["coverage"] in COVERAGE_CLAIMS, "invalid coverage claim", f"{base}/coverage",
              "one of " + ", ".join(COVERAGE_CLAIMS) + " (always recorded as partial)")
    return {"id": identifier, "dependencies": list(dependencies), "effects": normalized}


def _refuse(message: str, code: str, pointer: str) -> InvalidAnalysis:
    return InvalidAnalysis(message, pointer=pointer, code=code)


def _validate_batch(units: list[dict]) -> None:
    seen: set[str] = set()
    for index, unit in enumerate(units):
        if unit["id"] in seen:
            raise _refuse("duplicate unit id", "duplicate-unit-id", f"/units/{index}/id")
        seen.add(unit["id"])
    for index, unit in enumerate(units):
        for position, dependency in enumerate(unit["dependencies"]):
            where = f"/units/{index}/dependencies/{position}"
            if dependency == unit["id"]:
                raise _refuse("self dependency", "self-dependency", where)
            if dependency not in seen:
                raise _refuse("unknown dependency", "unknown-dependency", where)
    completed: set[str] = set()
    while len(completed) < len(units):
        ready = {unit["id"] for unit in units if set(unit["dependencies"]) <= completed} - completed
        if not ready:
            raise _refuse("cyclic dependencies", "cyclic-dependencies", "/units")
        completed |= ready
    spelling: dict[str, str] = {}
    for index, unit in enumerate(units):
        for position, effect in enumerate(unit["effects"]):
            path = effect["resource"]
            first = spelling.setdefault(path.casefold(), path)
            if first != path:
                raise _refuse("resources differ only by letter case", "case-only-duplicate-resource",
                              f"/units/{index}/effects/{position}/resource")


def validate(request: object) -> list[dict]:
    """Validated units with normalized resources, in input order."""
    _need(isinstance(request, dict), "units request shape is invalid", "",
          "an object with exactly the properties units, unitsRequestVersion")
    analysis.exact_keys(request, set(REQUEST_FIELDS), "units request shape is invalid", "")
    _need(request["unitsRequestVersion"] == UNITS_REQUEST_VERSION, "unsupported units request version",
          "/unitsRequestVersion", f"the constant {UNITS_REQUEST_VERSION}")
    units = request["units"]
    _need(isinstance(units, list) and bool(units), "units must be a nonempty array", "/units",
          f"an array of 1 to {MAX_UNITS} units")
    _need(len(units) <= MAX_UNITS, "Request exceeds the 32-operation adapter limit", "/units",
          f"an array of 1 to {MAX_UNITS} units")
    normalized = [_validate_unit(unit, f"/units/{index}") for index, unit in enumerate(units)]
    _validate_batch(normalized)
    return normalized


def _canonical_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _record(unit: dict, scope: str) -> dict:
    declaration = {"construction": CONSTRUCTION_ID, "workspace": scope, "id": unit["id"],
                   "dependencies": unit["dependencies"], "effects": unit["effects"]}
    return {
        "aimVersion": "0.2.0-draft",
        "instanceId": unit["id"],
        "attemptId": unit["id"],
        "definition": {"id": CONSTRUCTION_ID, "digest": CONSTRUCTION_DIGEST},
        "inputDigest": _canonical_digest(declaration),
        "dependencies": list(unit["dependencies"]),
        "readVersions": {},
        "effects": {
            "declared": [{"kind": effect["kind"], "resource": f"repo://{scope}/{effect['resource']}"}
                         for effect in unit["effects"]],
            "inferred": [],
            "observed": [],
            "coverage": dict(COVERAGE),
        },
        "evidence": [copy.deepcopy(EVIDENCE)],
    }


def construct(request: object, scope: str) -> dict:
    """``{constructedRequest, provenance}``: an analysis-input envelope with one record per unit."""
    if not isinstance(scope, str) or not _SCOPE.fullmatch(scope):
        raise ValueError("workspace scope must be 32 lowercase hex digits")
    units = validate(request)
    constructed = {"analysisInputVersion": analysis.REPORT_VERSION, "source": dict(SOURCE),
                   "operations": [_record(unit, scope) for unit in units]}
    provenance = {"source": "units declaration", "construction": CONSTRUCTION_ID,
                  "constructionDigest": CONSTRUCTION_DIGEST, "unitsRequestVersion": UNITS_REQUEST_VERSION,
                  "workspaceScope": scope, "coverage": "partial",
                  "replay": "analyze-work kind aim with constructedRequest", "executionAuthorization": False}
    return {"constructedRequest": constructed, "provenance": provenance}


def analyze(request: object, scope: str) -> dict:
    """``{report, constructedRequest, provenance}``; the report is ``analysis.analyze`` of the constructed request."""
    built = construct(request, scope)
    return {"report": analysis.analyze(built["constructedRequest"]), **built}


__all__ = ["UNITS_REQUEST_VERSION", "CONSTRUCTION_ID", "CONSTRUCTION_DIGEST", "EFFECT_KINDS",
           "MAX_UNITS", "MAX_IDENTIFIER_BYTES", "workspace_scope", "normalize_resource",
           "validate", "construct", "analyze"]
