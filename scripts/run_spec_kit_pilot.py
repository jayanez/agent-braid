#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture actual bounded-verifier pilot evidence; never approve a review."""
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import subprocess
import sys

from validate_spec_kit import digest

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "specs/001-certificate-verifier-pilot"


def run():
    if sys.version_info < (3, 12):
        raise ValueError("The M0 pilot requires Python 3.12 or newer")
    status = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"], cwd=ROOT,
        capture_output=True, text=True, check=True,
    )
    if status.stdout.strip():
        raise ValueError("Capture requires a clean tracked worktree")
    candidate_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
        text=True, check=True,
    ).stdout.strip()
    observations = []
    for name, expected, code in (("exhaustive", "verified", 0),
                                 ("proof-unverified", "unverified", 1)):
        args = ["-m", "research.lab", "verify",
                f"examples/contracts/0.2.0-draft/{name}.json"]
        result = subprocess.run([sys.executable, *args], cwd=ROOT,
                                capture_output=True, text=True)
        if result.returncode != code or json.loads(result.stdout)["status"] != expected:
            raise ValueError(f"Unexpected pilot result: {name}: {result.stdout} {result.stderr}")
        observations.append({"command": "python3 " + " ".join(args),
                             "exit_code": result.returncode, "stdout": result.stdout,
                             "stderr": result.stderr})
    args = ["-m", "unittest", "discover", "-s", "tests", "-p", "test_lab.py", "-v"]
    result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    observations.append({"command": "python3 " + " ".join(args),
                         "exit_code": result.returncode,
                         "stdout": result.stdout, "stderr": result.stderr})
    inputs = [*ROOT.glob("research/lab/*.py"), ROOT / "tests/test_lab.py",
              *ROOT.glob("examples/contracts/0.2.0-draft/*.json"),
              *ROOT.glob("examples/lab/*.json"), Path(__file__).resolve()]
    evidence = {"captured_at": datetime.now(timezone.utc).isoformat(),
                "python": platform.python_version(), "platform": platform.system(),
                "python_executable": sys.executable,
                "candidate_commit": candidate_commit,
                "repository_dirty": False,
                "inputs": {p.relative_to(ROOT).as_posix(): digest(p) for p in sorted(inputs)},
                "observations": observations,
                "interactive_codex": "not executed", "interactive_claude": "not executed",
                "human_review": "pending"}
    artifact = FEATURE / "evidence.json"
    artifact.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    record_path = FEATURE / "assurance.json"
    record = json.loads(record_path.read_text())
    for req in record["requirements"]:
        for scenario in req["scenarios"]:
            scenario["obtained_evidence"] = [{
                "path": artifact.relative_to(ROOT).as_posix(), "sha256": digest(artifact),
                "command": "python3 scripts/run_spec_kit_pilot.py",
                "outcome": "Expected bounded acceptance outcome observed; see raw observations",
                "limits": "Finite fixture checks only; no live-agent or human approval",
            }]
    record["stage"] = "validated"
    record["human_review"] = "pending"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print("Pilot evidence captured; authority hashes unchanged and human review pending.")


if __name__ == "__main__":
    run()
