#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture local command evidence for approved Agent Braid feature records."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SPEC_PYTHON = Path(".venv-speckit") / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
FEATURES = {
    "010-risk-validation": {
        "commands": [
            [sys.executable, "-m", "unittest", "tests.test_validation_profiles", "-v"],
            [sys.executable, "scripts/validate_change.py", "--base", "develop", "--profile", "pr"],
            [str(SPEC_PYTHON), "scripts/test_spec_kit_integration.py"],
        ],
        "inputs": [
            ".github/workflows/validate.yml",
            ".specify/templates/overrides/guardrails.md",
            ".specify/generation.json",
            ".specify/integrations/codex.manifest.json",
            ".specify/integrations/claude.manifest.json",
            "AGENTS.md",
            "CONTRIBUTING.md",
            "README.md",
            "docs/adr/0011-risk-based-validation-gates.md",
            "docs/development/SPEC_KIT.md",
            "docs/development/VALIDATION_PROFILES.md",
            "scripts/capture_feature_evidence.py",
            "scripts/validate_change.py",
            "scripts/validate_repository.py",
            "tests/test_validation_profiles.py",
        ],
        "outcome": "Risk-based path classification, complete candidate validation, conditional multi-agent gates and negative fallbacks passed.",
        "limits": "Path selection is an operational optimization, not semantic dependency analysis, evidence reproduction, scientific proof, human approval or independent validation.",
    },
    "008-m0.5-closure": {
        "commands": [
            [sys.executable, "scripts/validate_m05_closure.py", "--candidate"],
            [sys.executable, "scripts/validate_research_radar.py", "--milestone", "M0.5"],
            [sys.executable, "scripts/market_sizing.py", "--check"],
        ],
        "inputs": [
            "LICENSE",
            "NOTICE",
            "TRADEMARKS.md",
            "docs/strategy/OPEN_TOOLING_STRATEGY.md",
            "docs/strategy/ECOSYSTEM.md",
            "docs/strategy/MARKET_OPPORTUNITY.md",
            "docs/strategy/COMMUNITY.md",
            "docs/development/THIRD_PARTY.md",
            "docs/releases/RESEARCH_PREVIEW_PROPOSAL.md",
            "docs/releases/research-preview-readiness.json",
            "research/radar/2026-09-18-m0.5.json",
            "research/reviews/2026-09-18-m0.5-radar.md",
            "research/market/2026-opportunity-model.json",
            "reports/README.md",
            "reports/agent-braid-market-trends-2026.pptx",
            "reports/agent-braid-market-trends-2026.pdf",
            "reports/assets/agent-braid-concurrency-cover.png",
            "scripts/validate_m05_closure.py",
            "scripts/run_m05_clean_room.py",
            "scripts/validate_repository.py",
            "tests/test_m05_closure.py",
        ],
        "outcome": "M0.5 candidate, offline radar, market arithmetic and report-package gates passed.",
        "limits": "Structural, arithmetic and current-tree artifact evidence only; no source freshness, market demand, scientific truth, publication approval or independent validation established.",
    },
    "006-validation-status-policy": {
        "commands": [
            [sys.executable, "scripts/validate_release_records.py"],
            [sys.executable, "-m", "unittest", "tests.test_release_records", "-v"],
            [sys.executable, "scripts/validate_repository.py"],
        ],
        "inputs": [
            "GOVERNANCE.md", "ROADMAP.md", "README.md",
            "docs/adr/0009-transparent-validation-status.md",
            "docs/releases/VALIDATION_POLICY.md",
            "docs/releases/M0_POLICY_SUPERSESSION.md",
            "schemas/governance/release-validation-record.schema.json",
            "scripts/validate_release_records.py", "scripts/validate_repository.py",
            "tests/test_release_records.py",
        ],
        "outcome": "Release validation states, disclosures and negative claim checks passed.",
        "limits": "Structural policy evidence only; no reviewer identity, independence, release approval or scientific result established.",
    },
    "002-open-tooling-strategy": {
        "commands": [
            [sys.executable, "scripts/validate_research_radar.py", "--milestone", "M0.5"],
            [sys.executable, "scripts/market_sizing.py"],
            [sys.executable, "-m", "unittest", "tests.test_strategy", "-v"],
        ],
        "inputs": [
            "docs/strategy/OPEN_TOOLING_STRATEGY.md", "docs/strategy/ECOSYSTEM.md",
            "docs/strategy/MARKET_OPPORTUNITY.md", "docs/strategy/COMMUNITY.md",
            "docs/releases/M0_READINESS.md", "research/radar/2026-09-17.json",
            "research/market/2026-opportunity-model.json", "scripts/market_sizing.py",
            "scripts/validate_research_radar.py", "tests/test_strategy.py",
        ],
        "outcome": "Offline radar, market arithmetic, and negative tests passed.",
        "limits": "Structural and arithmetic evidence only; no demand, currency, scientific truth, or approval established.",
    },
    "003-read-only-analyzer": {
        "commands": [
            [sys.executable, "-m", "unittest", "tests.test_analysis", "-v"],
            [sys.executable, "scripts/run_software_benchmark.py"],
            [sys.executable, "scripts/validate_contracts.py"],
        ],
        "inputs": [
            "agent_braid/__init__.py", "agent_braid/__main__.py", "agent_braid/analysis.py",
            "agent_braid/cli.py", "schemas/0.1.0-alpha/analysis-report.schema.json",
            "examples/analysis/file-edits.json", "examples/analysis/software-benchmark.json",
            "scripts/run_software_benchmark.py", "tests/test_analysis.py",
        ],
        "outcome": "Analyzer, CLI, report contract, verifier delegation, and nine-scenario benchmark passed with zero false-safe classifications.",
        "limits": "Synthetic exact-resource corpus only; no semantic code analysis, agent execution, or production-safety claim.",
    },
    "005-git-worktree-adapter": {
        "commands": [
            [sys.executable, "-m", "unittest", "tests.test_git_adapter", "-v"],
            [sys.executable, "scripts/run_git_benchmark.py"],
            [sys.executable, "scripts/validate_contracts.py"],
        ],
        "inputs": [
            "agent_braid/git_adapter.py", "agent_braid/cli.py",
            "schemas/0.1.0-alpha/git-analysis-request.schema.json",
            "schemas/0.1.0-alpha/git-analysis-provenance.schema.json",
            "examples/analysis/git-benchmark.json", "scripts/run_git_benchmark.py",
            "tests/test_git_adapter.py", "docs/adr/0008-read-only-git-worktree-adapter.md",
        ],
        "outcome": "Git adapter, mandatory provenance, negative cases, compatibility, and six-scenario benchmark passed with zero false-safe classifications.",
        "limits": "Synthetic local Git repositories and syntactic path observations only; no semantic commutation, merge safety, production-safety, or execution claim.",
    },
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def redact_machine_paths(text: str) -> str:
    return text.replace(str(ROOT.resolve()), "<repository>")


def capture(feature: str) -> None:
    config = FEATURES[feature]
    feature_dir = ROOT / "specs" / feature
    assurance_path = feature_dir / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    assurance["stage"] = "draft"
    assurance["human_review"] = "pending"
    for requirement in assurance["requirements"]:
        for scenario in requirement["scenarios"]:
            scenario["obtained_evidence"] = []
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")

    observations = []
    for command in config["commands"]:
        process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
        observations.append({
            "command": " ".join(command).replace(sys.executable, "python3", 1),
            "exit_code": process.returncode,
            "stdout": redact_machine_paths(process.stdout),
            "stderr": redact_machine_paths(process.stderr),
        })
        if process.returncode:
            raise RuntimeError(f"evidence command failed: {' '.join(command)}")
    evidence_path = feature_dir / "evidence.json"
    evidence = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.system(),
        "python": platform.python_version(),
        "human_review": "pending",
        "inputs": {name: digest(ROOT / name) for name in config["inputs"]},
        "observations": observations,
    }
    evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    item = {
        "path": evidence_path.relative_to(ROOT).as_posix(),
        "sha256": digest(evidence_path),
        "command": f"python3 scripts/capture_feature_evidence.py {feature}",
        "outcome": config["outcome"],
        "limits": config["limits"],
    }
    for requirement in assurance["requirements"]:
        for scenario in requirement["scenarios"]:
            scenario["obtained_evidence"] = [item]
    assurance["stage"] = "validated"
    assurance["human_review"] = "pending"
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in FEATURES:
        print("usage: capture_feature_evidence.py <002-open-tooling-strategy|003-read-only-analyzer|005-git-worktree-adapter|006-validation-status-policy|008-m0.5-closure|010-risk-validation>", file=sys.stderr)
        return 2
    capture(sys.argv[1])
    print(f"Captured executable evidence for {sys.argv[1]}; human review remains pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
