#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture executable M0 closure evidence without approving the milestone."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

from validate_spec_kit import digest


ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "specs/004-m0-closure"


def run_command(args: list[str]) -> dict:
    process = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    result = {
        "command": " ".join(args).replace(sys.executable, "python3", 1),
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }
    if process.returncode:
        raise ValueError(f"M0 evidence command failed: {result}")
    return result


def run() -> None:
    if sys.version_info < (3, 12):
        raise ValueError("M0 evidence requires Python 3.12 or newer")
    pilot = json.loads((ROOT / "specs/001-certificate-verifier-pilot/evidence.json").read_text())
    commands = [
        [sys.executable, "scripts/validate_m0_closure.py", "readiness"],
        [sys.executable, "-m", "unittest", "tests.test_m0_closure", "-v"],
        [sys.executable, "scripts/validate_contracts.py"],
        [sys.executable, "-m", "research.lab.controls"],
    ]
    inputs = [
        "docs/releases/M0_EXIT_MATRIX.md",
        "examples/workloads/README.md",
        "examples/workloads/code-agent-repository.json",
        "examples/workloads/ci-deployment-controller.json",
        "scripts/validate_m0_closure.py",
        "tests/test_m0_closure.py",
        "specs/001-certificate-verifier-pilot/evidence.json",
        "specs/001-certificate-verifier-pilot/reviews/codex.json",
        "specs/001-certificate-verifier-pilot/reviews/claude.json",
    ]
    evidence = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.system(),
        "candidate_commit": pilot["candidate_commit"],
        "inputs": {name: digest(ROOT / name) for name in inputs},
        "observations": [run_command(command) for command in commands],
        "limits": "Structural, finite and provenance checks only; human and founder decisions remain pending.",
    }
    evidence_path = FEATURE / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    assurance_path = FEATURE / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    item = {
        "path": evidence_path.relative_to(ROOT).as_posix(),
        "sha256": digest(evidence_path),
        "command": "python3 scripts/capture_m0_closure_evidence.py",
        "outcome": "M0 exit matrix, portable fixtures, pilot provenance and negative controls passed.",
        "limits": evidence["limits"],
    }
    for requirement in assurance["requirements"]:
        for scenario in requirement["scenarios"]:
            scenario["obtained_evidence"] = [item] if requirement["id"] in {
                "REQ-001", "REQ-002", "REQ-003"
            } else []
    assurance["stage"] = "draft"
    assurance["human_review"] = "pending"
    assurance.pop("review_record", None)
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")
    print("Captured M0 candidate evidence; human and founder decisions remain pending.")


if __name__ == "__main__":
    run()
