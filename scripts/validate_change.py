#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Plan and run proportional validation without weakening candidate gates."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("quick", "pr", "sensitive")


@dataclass(frozen=True)
class Rule:
    domain: str
    patterns: tuple[str, ...]
    commands: tuple[str, ...] = ()
    sensitive: bool = False
    spec_kit_integration: bool = False
    boundary: str | None = None
    fallback: bool = False


@dataclass(frozen=True)
class Impact:
    paths: tuple[str, ...]
    domains: tuple[str, ...]
    reasons: tuple[str, ...]
    quick_commands: tuple[str, ...]
    sensitive: bool
    spec_kit_integration: bool
    boundaries: tuple[str, ...]
    unknown_paths: tuple[str, ...]


@dataclass(frozen=True)
class Plan:
    requested_profile: str
    effective_profile: str
    impact: Impact
    commands: tuple[str, ...]


RULES = (
    Rule("spec-kit-integration", (
        ".specify/templates/**", ".specify/scripts/**", ".specify/spec-kit.lock.json",
        ".agents/skills/**", ".claude/skills/**", "scripts/spec_kit.py",
        "scripts/test_spec_kit_integration.py", "scripts/restore_public_spec_history.py",
        "requirements-speckit.txt",
    ), ("spec-kit-structure", "spec-kit-render"), True, True),
    Rule("validation-process", (
        ".github/workflows/**", "AGENTS.md", "CONTRIBUTING.md",
        "docs/development/SPEC_KIT.md", "docs/development/VALIDATION.md",
        "docs/development/VALIDATION_PROFILES.md", "scripts/validate_*.py",
        "scripts/constitution_replica.py", "tests/test_validation_profiles.py",
    ), ("validation-profile-tests",), True),
    Rule("normative", (
        "CONSTITUTION.md", ".specify/memory/constitution.md", "GOVERNANCE.md",
        "LICENSE", "LICENSES/**", "NOTICE", "TRADEMARKS.md", "SECURITY.md",
        ".github/CODEOWNERS", "docs/adr/**", "docs/theory/**",
        "docs/architecture/**", "ARCHITECTURE.md", "MATHEMATICAL_FOUNDATIONS.md",
        "RESEARCH.md", "TERMINOLOGY.md",
    ), ("constitution-replica",), True),
    Rule("contracts", (
        "schemas/**", "examples/contracts/**", "examples/aim/**",
        "tests/test_contracts.py", "scripts/validate_contracts.py",
    ), ("contracts", "contract-tests"), True),
    Rule("runtime-analysis", (
        "agent_braid/analysis.py", "agent_braid/cli.py", "agent_braid/__init__.py",
        "agent_braid/__main__.py", "tests/test_analysis.py",
        "examples/analysis/file-edits.json", "scripts/run_software_benchmark.py",
    ), ("contracts", "analysis-tests")),
    Rule("runtime-git", (
        "agent_braid/git_adapter.py", "tests/test_git_adapter.py",
        "examples/analysis/git-benchmark.json", "scripts/run_git_benchmark.py",
    ), ("contracts", "git-adapter-tests")),
    Rule("git-replay", (
        "agent_braid/git_replay.py", "tests/test_git_replay.py",
        "examples/analysis/git-replay-benchmark.json",
        "scripts/run_git_replay_benchmark.py",
    ), ("contracts", "git-replay-tests")),
    Rule("scientific-laboratory", (
        "research/lab/**", "research/counterexamples/**", "examples/lab/**",
        "tests/test_lab.py",
    ), ("lab-tests", "scientific-controls", "contracts"), True,
        boundary="Scientific evidence capture or reproduction, when claims are refreshed"),
    Rule("strategy", (
        "docs/strategy/**", "research/adoption/**", "research/radar/**",
        "research/market/**", "reports/**",
        "tests/test_strategy.py", "scripts/market_sizing.py",
        "scripts/validate_research_radar.py", "scripts/validate_adoption_tracks.py",
        "tests/test_adoption_pathline.py",
    ), ("strategy-tests", "research-radar", "adoption-tracks", "market-model")),
    Rule("governance-release", (
        "docs/releases/**", "schemas/governance/**", "tests/test_release_records.py",
        "tests/test_publication.py", "tests/test_m0_closure.py",
        "tests/test_m05_closure.py", "tests/test_m1_closure.py",
        "scripts/validate_release_records.py", "scripts/validate_publication.py",
        "scripts/validate_m0_closure.py", "scripts/validate_m05_closure.py",
        "scripts/validate_m1_closure.py", "scripts/closure_anchors.py",
        "scripts/publication.py", "scripts/export_public_repository.py",
        "scripts/capture_feature_evidence.py", "scripts/run_*clean_room.py",
    ), ("governance-tests", "release-records", "publication"), True,
        boundary="Applicable milestone, release or publication clean-room protocol"),
    Rule("feature-assurance", ("specs/**",), ("spec-kit-structure",), True,
        boundary="Feature-specific evidence capture, freeze and human review"),
    Rule("supply-chain", (
        "pyproject.toml", "requirements-dev.txt", ".gitignore", ".gitattributes",
    ), ("cli-smoke",), True),
    Rule("contributor-documentation", (
        "README.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SUPPORT.md",
        "CITATION.cff", "CLAUDE.md", ".github/ISSUE_TEMPLATE/**",
        ".github/pull_request_template.md", "docs/**", "*.md",
    )),
    Rule("examples", ("examples/**",), ("contracts",)),
    Rule("tests-other", ("tests/**",), ("full-tests",), True, fallback=True),
    Rule("scripts-other", ("scripts/**",), ("full-tests",), True, fallback=True),
    Rule("python-package-other", ("agent_braid/**", "research/**"),
         ("full-tests",), True, fallback=True),
)


BASE_COMMANDS = ("repository", "constitution-replica", "whitespace")
PR_COMMANDS = (
    "repository", "contracts", "release-records", "publication", "m0-closure",
    "m1-closure", "m05-closure", "research-radar", "adoption-tracks", "market-model", "cli-smoke",
    "full-tests", "scientific-controls", "spec-kit-structure", "spec-kit-render",
    "constitution-replica", "whitespace",
)


def normalize_path(value: str) -> str:
    value = value.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value in {"", "."}:
        raise ValueError(f"invalid repository-relative path: {value!r}")
    normalized = path.as_posix()
    return normalized[2:] if normalized.startswith("./") else normalized


def matches(path: str, pattern: str) -> bool:
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatchcase(path, pattern)


def unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def classify(paths: Iterable[str]) -> Impact:
    normalized = tuple(sorted({normalize_path(path) for path in paths}))
    domains: list[str] = []
    reasons: list[str] = []
    commands: list[str] = []
    boundaries: list[str] = []
    unknown: list[str] = []
    sensitive = False
    spec_integration = False

    for path in normalized:
        candidates = [rule for rule in RULES if any(matches(path, item) for item in rule.patterns)]
        matched = [rule for rule in candidates if not rule.fallback]
        if not matched:
            matched = [rule for rule in candidates if rule.fallback]
        if not matched:
            unknown.append(path)
            domains.append("unknown")
            reasons.append(f"{path}: no owned rule; conservative sensitive fallback")
            sensitive = True
            spec_integration = True
            continue
        for rule in matched:
            domains.append(rule.domain)
            reasons.append(f"{path}: {rule.domain}")
            commands.extend(rule.commands)
            sensitive = sensitive or rule.sensitive
            spec_integration = spec_integration or rule.spec_kit_integration
            if rule.boundary:
                boundaries.append(rule.boundary)

    return Impact(
        paths=normalized,
        domains=tuple(sorted(set(domains))),
        reasons=tuple(sorted(set(reasons))),
        quick_commands=unique(commands),
        sensitive=sensitive,
        spec_kit_integration=spec_integration,
        boundaries=tuple(sorted(set(boundaries))),
        unknown_paths=tuple(unknown),
    )


def build_plan(paths: Iterable[str], requested_profile: str, *, portable: bool = False) -> Plan:
    if requested_profile not in PROFILES:
        raise ValueError(f"unsupported profile: {requested_profile}")
    impact = classify(paths)
    effective = requested_profile
    if impact.sensitive and requested_profile == "quick":
        effective = "sensitive"

    if effective == "quick":
        commands = unique((*BASE_COMMANDS, *impact.quick_commands))
    else:
        commands = PR_COMMANDS
        if portable:
            commands = tuple(command for command in commands
                             if command not in {"m0-closure", "m1-closure", "m05-closure"})
        if effective == "sensitive" and impact.spec_kit_integration:
            commands = (*commands, "spec-kit-integration")
    return Plan(requested_profile, effective, impact, unique(commands))


def git_output(args: Sequence[str], cwd: Path = ROOT) -> str:
    process = subprocess.run(
        ["git", "-C", str(cwd), *args], text=True, capture_output=True, check=False,
    )
    if process.returncode:
        raise ValueError(process.stderr.strip() or f"Git failed: {' '.join(args)}")
    return process.stdout


def resolve_default_base(root: Path = ROOT) -> str:
    for candidate in ("develop", "origin/develop", "HEAD"):
        process = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", f"{candidate}^{{commit}}"],
            text=True, capture_output=True, check=False,
        )
        if process.returncode == 0:
            return candidate
    raise ValueError("unable to resolve a validation base")


def resolve_commit(reference: str, root: Path = ROOT) -> str:
    if not reference or reference.startswith("-") or any(character.isspace() for character in reference):
        raise ValueError(f"invalid Git revision: {reference!r}")
    resolved = git_output(["rev-parse", "--verify", f"{reference}^{{commit}}"], root).strip()
    if len(resolved) != 40 or any(character not in "0123456789abcdef" for character in resolved):
        raise ValueError(f"Git revision did not resolve to a full commit: {reference!r}")
    return resolved


def changed_paths(base: str, head: str | None = None, root: Path = ROOT) -> tuple[str, ...]:
    revision = f"{base}...{head}" if head else base
    tracked = git_output([
        "diff", "--name-only", "-z", "--find-renames", "--diff-filter=ACMRTUXBD", revision, "--",
    ], root).split("\0")
    untracked: list[str] = []
    if head is None:
        untracked = git_output([
            "ls-files", "--others", "--exclude-standard", "-z", "--",
        ], root).split("\0")
    return tuple(sorted({normalize_path(path) for path in (*tracked, *untracked) if path}))


def spec_python(root: Path = ROOT) -> str:
    configured = os.environ.get("AGENT_BRAID_SPEC_KIT_PYTHON")
    if configured:
        return configured
    candidates = (
        root / ".venv-speckit" / ("Scripts/python.exe" if os.name == "nt" else "bin/python"),
        Path(sys.executable),
    )
    return str(next((path for path in candidates if path.exists()), Path(sys.executable)))


def publication_mode(root: Path = ROOT) -> str:
    return "--portable" if (root / "docs/releases/public-export.json").exists() else "--source"


def command_argv(identifier: str, base: str, head: str | None, root: Path = ROOT) -> list[str]:
    python = sys.executable
    spec = spec_python(root)
    revision = f"{base}...{head}" if head else base
    m05_arguments = [] if (root / "specs/008-m0.5-closure/founder-review.json").exists() else ["--candidate"]
    commands = {
        "repository": [python, "scripts/validate_repository.py"],
        "contracts": [python, "scripts/validate_contracts.py"],
        "contract-tests": [python, "-m", "unittest", "tests.test_contracts", "-v"],
        "analysis-tests": [python, "-m", "unittest", "tests.test_analysis", "-v"],
        "git-adapter-tests": [python, "-m", "unittest", "tests.test_git_adapter", "-v"],
        "git-replay-tests": [python, "-m", "unittest", "tests.test_git_replay", "-v"],
        "lab-tests": [python, "-m", "unittest", "tests.test_lab", "-v"],
        "strategy-tests": [python, "-m", "unittest", "tests.test_strategy", "-v"],
        "governance-tests": [python, "-m", "unittest", "tests.test_m0_closure",
                             "tests.test_m05_closure", "tests.test_m1_closure",
                             "tests.test_publication", "tests.test_release_records", "-v"],
        "validation-profile-tests": [python, "-m", "unittest", "tests.test_validation_profiles", "-v"],
        "full-tests": [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
        "scientific-controls": [python, "-m", "research.lab.controls"],
        "research-radar": [python, "scripts/validate_research_radar.py", "--milestone", "M0.5"],
        "adoption-tracks": [python, "scripts/validate_adoption_tracks.py"],
        "market-model": [python, "scripts/market_sizing.py", "--check"],
        "release-records": [python, "scripts/validate_release_records.py"],
        "publication": [python, "scripts/validate_publication.py", publication_mode(root)],
        "m0-closure": [python, "scripts/validate_m0_closure.py", "closure"],
        "m1-closure": [python, "scripts/validate_m1_closure.py", "closure"],
        "m05-closure": [python, "scripts/validate_m05_closure.py", *m05_arguments],
        "spec-kit-structure": [python, "scripts/validate_spec_kit.py"],
        "spec-kit-render": [spec, "scripts/spec_kit.py", "check"],
        "spec-kit-integration": [spec, "scripts/test_spec_kit_integration.py"],
        "constitution-replica": [python, "scripts/constitution_replica.py", "check"],
        "cli-smoke": [python, "-m", "agent_braid", "--help"],
        "whitespace": ["git", "diff", "--check", revision, "--"],
    }
    try:
        return commands[identifier]
    except KeyError as exc:
        raise ValueError(f"unknown validation command: {identifier}") from exc


def display_argv(argv: Sequence[str], root: Path = ROOT) -> list[str]:
    displayed: list[str] = []
    for argument in argv:
        if argument == sys.executable:
            displayed.append("python3")
            continue
        try:
            relative = Path(argument).resolve().relative_to(root.resolve())
        except (OSError, ValueError):
            displayed.append(argument)
        else:
            displayed.append(relative.as_posix())
    return displayed


def plan_record(plan: Plan, base: str, head: str | None, root: Path = ROOT) -> dict:
    return {
        "base": base,
        "head": head,
        "requestedProfile": plan.requested_profile,
        "effectiveProfile": plan.effective_profile,
        "changedPaths": list(plan.impact.paths),
        "domains": list(plan.impact.domains),
        "reasons": list(plan.impact.reasons),
        "sensitive": plan.impact.sensitive,
        "specKitIntegration": plan.impact.spec_kit_integration,
        "unknownPaths": list(plan.impact.unknown_paths),
        "commands": [
            {"id": identifier,
             "argv": display_argv(command_argv(identifier, base, head, root), root)}
            for identifier in plan.commands
        ],
        "deferredBoundaryGates": list(plan.impact.boundaries),
        "limits": [
            "Path selection is not semantic dependency analysis or proof.",
            "Passing commands is not evidence capture, human review, founder approval or independent validation.",
            "Clean-room procedures remain separate and are not executed by this plan.",
        ],
    }


def render_text(record: dict) -> str:
    lines = [
        f"Requested profile: {record['requestedProfile']}",
        f"Effective profile: {record['effectiveProfile']}",
        "Changed paths: " + (", ".join(record["changedPaths"]) or "none"),
        "Domains: " + (", ".join(record["domains"]) or "none"),
        "Commands:",
    ]
    lines.extend(f"  - {item['id']}: {' '.join(item['argv'])}" for item in record["commands"])
    lines.append("Deferred boundary gates:")
    lines.extend(f"  - {item} (not executed)" for item in record["deferredBoundaryGates"])
    if not record["deferredBoundaryGates"]:
        lines.append("  - none")
    lines.append("Limits:")
    lines.extend(f"  - {item}" for item in record["limits"])
    return "\n".join(lines)


def render_github(record: dict) -> str:
    values = {
        "effective_profile": record["effectiveProfile"],
        "sensitive": str(record["sensitive"]).lower(),
        "spec_kit_integration": str(record["specKitIntegration"]).lower(),
        "unknown_paths": str(bool(record["unknownPaths"])).lower(),
        "changed": str(bool(record["changedPaths"])).lower(),
    }
    return "\n".join(f"{key}={value}" for key, value in values.items())


def execute(plan: Plan, base: str, head: str | None, root: Path = ROOT) -> int:
    for identifier in plan.commands:
        argv = command_argv(identifier, base, head, root)
        print(f"\n==> {identifier}: {' '.join(display_argv(argv, root))}", flush=True)
        result = subprocess.run(argv, cwd=root, check=False)
        if result.returncode:
            print(f"Validation failed at {identifier} (exit {result.returncode}).", file=sys.stderr)
            return result.returncode
    print("\nSelected executable validation passed. Deferred boundary gates remain unexecuted.")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Git base revision; defaults to local develop, origin/develop or HEAD")
    parser.add_argument("--head", help="Optional immutable head revision for committed-range planning")
    parser.add_argument("--profile", choices=PROFILES, default="quick")
    parser.add_argument("--path", action="append", dest="paths",
                        help="Explicit changed path; repeat to bypass Git discovery")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--format", choices=("text", "json", "github"), default="text")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        base = resolve_commit(args.base or resolve_default_base())
        head = resolve_commit(args.head) if args.head else None
        paths = tuple(args.paths) if args.paths is not None else changed_paths(base, head)
        plan = build_plan(
            paths, args.profile,
            portable=(ROOT / "docs/releases/public-export.json").exists(),
        )
        record = plan_record(plan, base, head)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"Validation planning failed: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(record, indent=2, sort_keys=True))
    elif args.format == "github":
        print(render_github(record))
    else:
        print(render_text(record))
    if args.plan_only:
        return 0
    return execute(plan, base, head)


if __name__ == "__main__":
    raise SystemExit(main())
