# SPDX-License-Identifier: AGPL-3.0-only
"""Checker for the SPEC-057 surface capability matrix (REQ-006, SC-006).

The checker reads the matrix as data and returns stable finding codes. It is a
documentation-consistency gate: it never observes a host and never turns a
documentation reading into a support, enforcement or coverage claim.
"""

from __future__ import annotations

import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "specs/057-claude-orchestration-advisory/contracts/surface-capability-matrix.json"

SURFACE_IDS = ("workflow-tracks", "linked-sessions", "agent-teams", "batch")
LIFECYCLES = ("pre-flight", "continuous", "recovery", "integration")
EVIDENCE_STATUSES = ("documented", "inferred", "unconfirmed", "host-observed")
CELL_STATUSES = ("planned", "deferred", "reuse-of-SPEC-052-unverified", "not-covered")
CLASSES = ("0-heuristic", "1-syntactic", "not-applicable")
PREVIEW_SURFACES = ("agent-teams", "linked-sessions")
NOT_COVERED = ("codex", "cloud sessions", "remote control", "vs code", "windows")
# The specification's integration row, by surface: (cell status, owner specification).
INTEGRATION = {
    "workflow-tracks": ("reuse-of-SPEC-052-unverified", "SPEC-052"),
    "linked-sessions": ("reuse-of-SPEC-052-unverified", "SPEC-052"),
    "agent-teams": ("not-covered", "none"),
    "batch": ("not-covered", "none"),
}

VERSION = re.compile(r"^\d+\.\d+\.\d+$")
OWNER = re.compile(r"^(SPEC-\d{3}|none)$")
PROBE = re.compile(r"^HV-(L)?\d+$")
SENTENCE = re.compile(r"(?<=[.;])\s+")
ENFORCE = re.compile(r"\benforc(?:e|es|ed|ing|ement)\b", re.IGNORECASE)
COVERAGE = re.compile(r"\b(?:covered|covers|serves)\b", re.IGNORECASE)
# A sentence may name enforcement or coverage only to defer or deny it.
DEFERRAL = re.compile(r"\b(?:not|no|never|until|unadopted|unverified|SPEC-058|SPEC-059)\b|only when", re.IGNORECASE)


def load_matrix(path: Path = MATRIX_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value: object):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _unqualified(value: object, pattern: re.Pattern) -> bool:
    return any(
        pattern.search(sentence) and not DEFERRAL.search(sentence)
        for text in _strings(value)
        for sentence in SENTENCE.split(text)
    )


def _check_header(matrix: dict, findings: list[str]) -> None:
    if tuple(matrix.get("surfaceIds") or ()) != SURFACE_IDS:
        findings.append("surface-ids-not-closed-set")
    for key in ("evidenceStatuses", "cellStatuses"):
        expected = EVIDENCE_STATUSES if key == "evidenceStatuses" else CELL_STATUSES
        if tuple(matrix.get(key) or ()) != expected:
            findings.append(f"{key}-changed")
    versions = matrix.get("hostVersionsRead")
    versions = versions if isinstance(versions, dict) else {}
    if not (isinstance(versions.get("versionBasis"), str) and versions["versionBasis"].strip()):
        findings.append("version-basis-missing")
    if not VERSION.match(str(versions.get("changelogLatest", ""))):
        findings.append("changelog-version-missing")
    if tuple(matrix.get("previewSurfaces") or ()) != PREVIEW_SURFACES:
        findings.append("preview-surfaces-changed")
    listed = " ".join(str(item) for item in matrix.get("notCovered") or ()).lower()
    if not all(item in listed for item in NOT_COVERED):
        findings.append("not-covered-list-incomplete")


def _check_cell(cell: object, findings: list[str]) -> tuple | None:
    if not isinstance(cell, dict):
        findings.append("cell-not-object")
        return None
    surface, lifecycle = cell.get("surface"), cell.get("lifecycle")
    where = f"{surface}/{lifecycle}"
    if surface not in SURFACE_IDS:
        findings.append(f"surface-id-outside-set:{surface}")
    if lifecycle not in LIFECYCLES:
        findings.append(f"lifecycle-unknown:{where}")
    if not (isinstance(cell.get("capability"), str) and cell["capability"].strip()):
        findings.append(f"capability-missing:{where}")
    if cell.get("status") not in CELL_STATUSES:
        findings.append(f"status-invalid:{where}")
    if cell.get("compatibilityClass") not in CLASSES:
        findings.append(f"class-missing:{where}")
    if not OWNER.match(str(cell.get("ownerSpec", ""))):
        findings.append(f"owner-missing:{where}")
    if not VERSION.match(str(cell.get("minHostVersion", ""))):
        findings.append(f"version-missing:{where}")
    if not isinstance(cell.get("preview"), bool):
        findings.append(f"preview-flag-missing:{where}")
    elif surface in PREVIEW_SURFACES and not cell["preview"]:
        findings.append(f"preview-label-missing:{where}")
    evidence = cell.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("status") not in EVIDENCE_STATUSES:
        findings.append(f"evidence-status-invalid:{where}")
    else:
        receipt = evidence.get("receipt")
        if evidence["status"] == "host-observed" and not (isinstance(receipt, str) and receipt.strip()):
            findings.append(f"host-observed-without-receipt:{where}")
        if evidence["status"] != "host-observed" and receipt is not None:
            findings.append(f"receipt-without-host-observation:{where}")
        probes = evidence.get("probes")
        if not isinstance(probes, list) or not all(PROBE.match(str(item)) for item in probes):
            findings.append(f"probes-invalid:{where}")
    if _unqualified(cell, ENFORCE):
        findings.append(f"enforcement-wording:{where}")
    if lifecycle == "integration":
        expected = INTEGRATION.get(surface)
        if expected and (cell.get("status"), cell.get("ownerSpec")) != expected:
            findings.append(f"integration-contradicts-specification:{where}")
        if _unqualified(cell, COVERAGE):
            findings.append(f"integration-coverage-wording:{where}")
    return surface, lifecycle


def check_matrix(matrix: object) -> list[str]:
    """Return sorted finding codes; an empty list means the matrix passes."""
    if not isinstance(matrix, dict):
        return ["matrix-not-object"]
    findings: list[str] = []
    _check_header(matrix, findings)
    cells = matrix.get("cells")
    seen = [_check_cell(cell, findings) for cell in cells] if isinstance(cells, list) else []
    if not isinstance(cells, list):
        findings.append("cells-missing")
    for surface in SURFACE_IDS:
        for lifecycle in LIFECYCLES:
            count = seen.count((surface, lifecycle))
            if count != 1:
                findings.append(f"cell-{'missing' if count == 0 else 'duplicated'}:{surface}/{lifecycle}")
    if _unqualified({k: v for k, v in matrix.items() if k != "cells"}, ENFORCE):
        findings.append("enforcement-wording:header")
    return sorted(set(findings))
