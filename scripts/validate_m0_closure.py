#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate M0 closure provenance; never infer reviewer identity or approval."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

try:
    from scripts.closure_anchors import validate_closure_anchor
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from closure_anchors import validate_closure_anchor


ROOT = Path(__file__).resolve().parents[1]
PILOT = "specs/001-certificate-verifier-pilot"
REPORTS = {
    "codex": f"{PILOT}/reviews/codex.json",
    "claude": f"{PILOT}/reviews/claude.json",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path, relative: str):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe repository file: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", value):
        raise ValueError("pilot Python version is malformed")
    return tuple(int(part) for part in value.split("."))


def validate_pilot(root: Path = ROOT) -> tuple[dict, dict]:
    evidence_path = root / PILOT / "evidence.json"
    evidence = load(root, f"{PILOT}/evidence.json")
    assurance = load(root, f"{PILOT}/assurance.json")
    if version(evidence.get("python", "")) < (3, 12):
        raise ValueError("pilot evidence requires Python 3.12 or newer")
    commit = evidence.get("candidate_commit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("pilot evidence requires an exact candidate commit")
    if evidence.get("repository_dirty") is not False:
        raise ValueError("pilot evidence must originate from a clean tracked worktree")
    if root.resolve() == ROOT.resolve():
        check = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root,
            capture_output=True, check=False,
        )
        if check.returncode:
            raise ValueError("pilot candidate commit is unavailable")
    inputs = evidence.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        raise ValueError("pilot evidence inputs are missing")
    for relative, checksum in inputs.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"pilot input is missing: {relative}")
        if digest(path) != checksum:
            raise ValueError(f"pilot input changed: {relative}")
    expected = digest(evidence_path)
    for requirement in assurance.get("requirements", []):
        for scenario in requirement.get("scenarios", []):
            obtained = scenario.get("obtained_evidence", [])
            if not obtained or any(item.get("sha256") != expected for item in obtained):
                raise ValueError("pilot assurance does not bind current evidence")
    return evidence, assurance


def validate_agent_report(report: dict, agent: str, candidate: str) -> None:
    required = {
        "reportVersion", "agent", "agentVersion", "executedAt", "reviewedCommit",
        "prompt", "unsupportedProof", "automatedHumanSeparation",
        "scientificLimitsRetained", "contradictions", "pendingChecks", "decision",
    }
    if set(report) != required:
        raise ValueError(f"{agent} review fields are incomplete or unexpected")
    if report["reportVersion"] != "0.1.0" or report["agent"] != agent:
        raise ValueError(f"invalid {agent} review identity")
    if report["reviewedCommit"] != candidate:
        raise ValueError(f"{agent} reviewed a different candidate commit")
    if report["unsupportedProof"] != "unverified":
        raise ValueError(f"{agent} promoted unsupported proof evidence")
    if report["automatedHumanSeparation"] is not True:
        raise ValueError(f"{agent} conflated automation and human approval")
    if report["scientificLimitsRetained"] is not True:
        raise ValueError(f"{agent} weakened scientific limits")
    if not isinstance(report["contradictions"], list) or not isinstance(report["pendingChecks"], list):
        raise ValueError(f"{agent} review lists are invalid")
    if report["decision"] != "compatible" or report["contradictions"]:
        raise ValueError(f"{agent} reported a material divergence")
    for field in ("agentVersion", "executedAt", "prompt"):
        if not isinstance(report[field], str) or not report[field].strip():
            raise ValueError(f"{agent} review lacks {field}")


def validate_review_record(record: dict, root: Path, candidate: str) -> None:
    required = {
        "recordVersion", "feature", "reviewedCommit", "reviewer", "conflictsOfInterest",
        "scientificReview", "milestoneClosure", "evidence", "limits",
    }
    if set(record) != required:
        raise ValueError("founder review record fields are incomplete or unexpected")
    if record["recordVersion"] != "0.1.0" or record["feature"] != "M0":
        raise ValueError("invalid founder review record identity")
    if record["reviewedCommit"] != candidate:
        raise ValueError("founder reviewed a different candidate commit")
    reviewer = record["reviewer"]
    if not isinstance(reviewer, dict) or reviewer.get("role") != "founder" or not reviewer.get("name"):
        raise ValueError("founder reviewer fields are incomplete")
    for decision_name in ("scientificReview", "milestoneClosure"):
        decision = record[decision_name]
        if not isinstance(decision, dict) or decision.get("decision") != "approved":
            raise ValueError(f"{decision_name} is not explicitly approved")
        if not decision.get("date") or not decision.get("rationale"):
            raise ValueError(f"{decision_name} lacks date or rationale")
    if not isinstance(record["conflictsOfInterest"], str) or not record["conflictsOfInterest"].strip():
        raise ValueError("conflicts-of-interest statement is required")
    if not isinstance(record["limits"], list) or not record["limits"]:
        raise ValueError("review limits are required")
    evidence = record["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("review evidence references are required")
    for item in evidence:
        path = (root / item.get("path", "")).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError("review evidence path is missing or unsafe")
        if item.get("sha256") != digest(path):
            raise ValueError(f"review evidence changed: {item.get('path')}")


def check(root: Path = ROOT, closure: bool = False) -> None:
    evidence, assurance = validate_pilot(root)
    candidate = evidence["candidate_commit"]
    present = {agent: (root / path).is_file() for agent, path in REPORTS.items()}
    if any(present.values()) and not all(present.values()):
        raise ValueError("Codex and Claude reviews must be recorded as one review set")
    if all(present.values()):
        reports = {}
        for agent, path in REPORTS.items():
            reports[agent] = load(root, path)
            validate_agent_report(reports[agent], agent, candidate)
        if reports["codex"]["prompt"] != reports["claude"]["prompt"]:
            raise ValueError("Codex and Claude did not receive the same prompt")
        for field in ("contradictions", "pendingChecks"):
            if reports["codex"][field] != reports["claude"][field]:
                raise ValueError(f"Codex and Claude disagree on {field}")
    if closure:
        if not all(present.values()):
            raise ValueError("closure requires both interactive agent reports")
        validate_closure_anchor(root, "M0", candidate)
        if evidence.get("interactive_codex") != REPORTS["codex"]:
            raise ValueError("pilot evidence does not reference the Codex report")
        if evidence.get("interactive_claude") != REPORTS["claude"]:
            raise ValueError("pilot evidence does not reference the Claude report")
        if assurance.get("human_review") != "approved":
            raise ValueError("pilot human review is not approved")
        record_path = assurance.get("review_record", "")
        record = load(root, record_path)
        validate_review_record(record, root, candidate)
        closure_text = (root / "docs/releases/M0_CLOSURE.md").read_text(encoding="utf-8")
        if "**Status:** closed by explicit founder decision" not in closure_text:
            raise ValueError("M0 closure document does not record the approved status")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else "readiness"
    if mode not in {"readiness", "closure"}:
        print("usage: validate_m0_closure.py [readiness|closure]", file=sys.stderr)
        return 2
    try:
        check(closure=mode == "closure")
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"M0 {mode} validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"M0 {mode} structural and provenance checks passed; no scientific approval inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
