#!/usr/bin/env python3
"""Validate foundational Agent Braid repository invariants without dependencies."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "CONSTITUTION.md",
    "RESEARCH.md",
    "MATHEMATICAL_FOUNDATIONS.md",
    "ARCHITECTURE.md",
    "TERMINOLOGY.md",
    "ROADMAP.md",
    "GOVERNANCE.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "LICENSE",
    "NOTICE",
    "TRADEMARKS.md",
    "LICENSES/AGPL-3.0-only.txt",
    "LICENSES/CC-BY-SA-4.0.txt",
    ".github/CODEOWNERS",
    "schemas/agent-interaction-metadata.schema.json",
    "schemas/confluence-certificate.schema.json",
    "schemas/0.2.0-draft/agent-interaction-metadata.schema.json",
    "schemas/0.2.0-draft/confluence-certificate.schema.json",
    "docs/theory/OPERATIONAL_SEMANTICS.md",
    "docs/theory/SCIENTIFIC_INTEGRATION.md",
    "docs/architecture/DRAFT_0_2.md",
    "research/REFERENCES.md",
    "research/lab/model.py",
    "research/lab/certificates.py",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/development/SPEC_KIT.md",
    "docs/development/VALIDATION_PROFILES.md",
    "docs/development/THIRD_PARTY.md",
    "docs/releases/M0_EXIT_MATRIX.md",
    "docs/releases/M0_POLICY_SUPERSESSION.md",
    "docs/releases/M1_CLOSURE.md",
    "docs/releases/RESEARCH_PREVIEW_PROPOSAL.md",
    "docs/releases/research-preview-readiness.json",
    "docs/releases/closure-anchors.json",
    "docs/releases/publication-cutover.json",
    "docs/releases/records/M1.json",
    "docs/releases/VALIDATION_POLICY.md",
    "examples/workloads/code-agent-repository.json",
    "examples/workloads/ci-deployment-controller.json",
    "specs/004-m0-closure/assurance.json",
    "scripts/validate_m0_closure.py",
    "scripts/validate_m1_closure.py",
    "scripts/run_m05_clean_room.py",
    "scripts/validate_m05_closure.py",
    "scripts/validate_release_records.py",
    "schemas/governance/release-validation-record.schema.json",
    "schemas/governance/public-export-manifest.schema.json",
    "LICENSES/Spec-Kit-MIT.txt",
    "LICENSES/python-skills-MIT.txt",
    ".specify/memory/PROVENANCE.md",
    ".specify/memory/constitution.md",
    "reports/agent-braid-market-trends-2026.pptx",
    "reports/agent-braid-market-trends-2026.pdf",
    "reports/assets/agent-braid-concurrency-cover.png",
    "research/radar/2026-09-18-m0.5.json",
    "research/adoption/README.md",
    "research/adoption/2026-09-initial-triage.json",
    "research/adoption/ADOPTION_PATHLINE.md",
    "research/adoption/adoption-track.schema.json",
    "research/reviews/2026-09-18-m0.5-radar.md",
    "specs/008-m0.5-closure/spec.md",
    "specs/008-m0.5-closure/plan.md",
    "specs/008-m0.5-closure/tasks.md",
    "specs/008-m0.5-closure/quickstart.md",
    "specs/008-m0.5-closure/assurance.json",
    "specs/008-m0.5-closure/evidence.json",
    "specs/009-public-research-preview/spec.md",
    "specs/009-public-research-preview/plan.md",
    "specs/009-public-research-preview/tasks.md",
    "specs/009-public-research-preview/quickstart.md",
    "specs/009-public-research-preview/assurance.json",
    "docs/adr/0010-clean-publication-provenance.md",
    "docs/adr/0011-risk-based-validation-gates.md",
    "docs/adr/0012-vendored-python-skills-license-boundary.md",
    "specs/010-risk-validation/spec.md",
    "specs/010-risk-validation/plan.md",
    "specs/010-risk-validation/tasks.md",
    "specs/010-risk-validation/quickstart.md",
    "specs/010-risk-validation/assurance.json",
    "specs/011-adoption-pathline/spec.md",
    "specs/011-adoption-pathline/plan.md",
    "specs/011-adoption-pathline/tasks.md",
    "specs/011-adoption-pathline/quickstart.md",
    "specs/011-adoption-pathline/assurance.json",
    "scripts/validate_adoption_tracks.py",
    "scripts/validate_change.py",
    "scripts/create_public_export.py",
    "scripts/validate_publication.py",
    "scripts/run_public_preview_clean_room.py",
    "docs/releases/RESEARCH_PREVIEW_RELEASE.md",
    "docs/adr/0013-isolated-git-replay-and-advisory-planning.md",
    "docs/architecture/GIT_REPLAY.md",
    "schemas/0.1.0-alpha/git-replay-evidence.schema.json",
    "schemas/0.1.0-alpha/git-plan.schema.json",
    "agent_braid/git_replay.py",
    "tests/test_git_replay.py",
    "scripts/run_git_replay_benchmark.py",
    "examples/analysis/git-replay-benchmark.json",
    "specs/012-m2-git-replay-planner/spec.md",
    "specs/012-m2-git-replay-planner/plan.md",
    "specs/012-m2-git-replay-planner/tasks.md",
    "specs/012-m2-git-replay-planner/quickstart.md",
    "specs/012-m2-git-replay-planner/assurance.json",
    "specs/012-m2-git-replay-planner/evidence.json",
)

MARKDOWN_LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
ARTICLE = re.compile(r"^## Article (\d+) — ", re.MULTILINE)
OBSOLETE_LICENSE_TEXT = (
    "No license " + "has been selected yet",
    "public " + "license;",
)
VENDORED_SKILLS = {
    "api-design": "designing-python-apis",
    "cli-development": "building-python-clis",
    "code-quality": "improving-python-code-quality",
    "documentation": "documenting-python-libraries",
    "testing-strategy": "testing-python-libraries",
}


def error(message: str, failures: list[str]) -> None:
    failures.append(message)


def repository_files(suffix: str = ""):
    """Do not traverse machine-local environments, caches or Git internals."""
    ignored = {".git", ".venv", ".venv-speckit", "__pycache__", "node_modules"}
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in ignored)
        for name in sorted(files):
            if name.endswith(suffix):
                yield Path(directory) / name


def validate_required_files(failures: list[str]) -> None:
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            error(f"missing required file: {relative}", failures)


def validate_json(failures: list[str]) -> None:
    for path in repository_files(".json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            error(f"invalid JSON: {path.relative_to(ROOT)}: {exc}", failures)


def validate_markdown_links(failures: list[str]) -> None:
    for path in repository_files(".md"):
        text = path.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target, _, fragment = raw_target.strip().partition("#")
            if "://" in target or target.startswith("mailto:"):
                continue
            resolved = (path.parent / unquote(target)).resolve() if target else path.resolve()
            try:
                resolved.relative_to(ROOT.resolve())
            except ValueError:
                error(
                    f"link escapes repository: {path.relative_to(ROOT)} -> {raw_target}",
                    failures,
                )
                continue
            if not resolved.exists():
                error(
                    f"broken relative link: {path.relative_to(ROOT)} -> {raw_target}",
                    failures,
                )
            elif fragment and resolved.suffix == ".md":
                if unquote(fragment) not in markdown_anchors(resolved.read_text(encoding="utf-8")):
                    error(f"broken anchor: {path.relative_to(ROOT)} -> {raw_target}", failures)


def validate_vendored_skills(failures: list[str]) -> None:
    """Check the discoverable metadata and complete Codex/Claude skill mirrors."""
    manifest_paths = [ROOT / agent / "skills" / "VENDORED-SKILLS.md"
                      for agent in (".agents", ".claude")]
    for path in manifest_paths:
        if not path.is_file():
            error(f"missing vendored skill manifest: {path.relative_to(ROOT)}", failures)
    if all(path.is_file() for path in manifest_paths) \
            and manifest_paths[0].read_bytes() != manifest_paths[1].read_bytes():
        error("vendored skill manifest mirror differs: VENDORED-SKILLS.md", failures)

    for folder, expected_name in VENDORED_SKILLS.items():
        mirrors: list[dict[str, bytes]] = []
        for agent in (".agents", ".claude"):
            directory = ROOT / agent / "skills" / folder
            if not directory.is_dir():
                error(f"missing vendored skill directory: {directory.relative_to(ROOT)}", failures)
                continue
            files = {
                path.relative_to(directory).as_posix(): path.read_bytes()
                for path in directory.rglob("*") if path.is_file()
            }
            mirrors.append(files)
            entry = files.get("SKILL.md")
            if entry is None:
                error(f"missing vendored skill entry: {directory.relative_to(ROOT)}", failures)
            else:
                match = re.match(r"\A---\n(.*?)\n---\n", entry.decode("utf-8"), re.DOTALL)
                metadata = match.group(1) if match else ""
                name = re.search(r"(?m)^name:\s*(\S.*?)\s*$", metadata)
                description = re.search(r"(?m)^description:\s*(\S.*?)\s*$", metadata)
                if not name or name.group(1) != expected_name or not description:
                    error(f"invalid vendored skill metadata: {directory.relative_to(ROOT)}", failures)
            for relative, payload in files.items():
                if not relative.endswith(".md"):
                    continue
                path = directory / relative
                for target in MARKDOWN_LINK.findall(payload.decode("utf-8")):
                    local = target.strip().split("#", 1)[0]
                    if not local or "://" in local or local.startswith("mailto:"):
                        continue
                    resolved = (path.parent / unquote(local)).resolve()
                    if not resolved.is_relative_to(ROOT.resolve()) or not resolved.exists():
                        error(f"broken vendored skill link: {path.relative_to(ROOT)} -> {target}", failures)
        if len(mirrors) == 2:
            for relative in sorted(mirrors[0].keys() | mirrors[1].keys()):
                if mirrors[0].get(relative) != mirrors[1].get(relative):
                    error(f"vendored skill mirror differs: {folder}/{relative}", failures)


def markdown_anchors(text: str) -> set[str]:
    """GitHub-style ATX heading anchors for the repository's Markdown subset."""
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        match = re.match(r"^#{1,6}\s+(.+?)(?:\s+#+)?$", line)
        if fenced or not match:
            continue
        title = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", match.group(1))
        slug = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        candidate = slug if count == 0 else f"{slug}-{count}"
        while candidate in anchors:
            count += 1
            candidate = f"{slug}-{count}"
        counts[slug] = count + 1
        anchors.add(candidate)
    return anchors


def validate_constitution(failures: list[str]) -> None:
    path = ROOT / "CONSTITUTION.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    articles = [int(value) for value in ARTICLE.findall(text)]
    if articles != list(range(1, 26)):
        error(f"constitutional articles must be exactly 1..25; found {articles}", failures)

    required_clause = (
        "Agent Braid does not assume that Yang–Baxter applies to AI agents."
    )
    if required_clause not in text:
        error("constitutional clause zero is missing or altered", failures)


def validate_ownership(failures: list[str]) -> None:
    path = ROOT / ".github/CODEOWNERS"
    if path.exists() and "* @jayanez" not in path.read_text(encoding="utf-8"):
        error("CODEOWNERS must preserve @jayanez as foundational owner", failures)


def validate_licensing(failures: list[str]) -> None:
    license_path = ROOT / "LICENSE"
    if not license_path.exists():
        return

    license_text = license_path.read_text(encoding="utf-8")
    for path in (ROOT / "research").rglob("*.py"):
        if "SPDX-License-Identifier: AGPL-3.0-only" not in path.read_text(encoding="utf-8"):
            error(f"executable research needs explicit license: {path.relative_to(ROOT)}", failures)
    required_map = {
        "AGPL-3.0-only": ("scripts/**", "schemas/**", "examples/**"),
        "CC-BY-SA-4.0": ("docs/**", "reports/**", "research/**"),
    }
    for identifier, path_markers in required_map.items():
        if identifier not in license_text:
            error(f"LICENSE missing SPDX identifier: {identifier}", failures)
        for marker in path_markers:
            if marker not in license_text:
                error(f"LICENSE missing path mapping: {marker}", failures)
    if "LICENSES/python-skills-MIT.txt" not in license_text:
        error("LICENSE missing vendored Python skills exception", failures)

    canonical_markers = {
        "LICENSES/AGPL-3.0-only.txt": "GNU AFFERO GENERAL PUBLIC LICENSE",
        "LICENSES/CC-BY-SA-4.0.txt": "Attribution-ShareAlike 4.0 International",
        "LICENSES/python-skills-MIT.txt": "Copyright (c) 2025 Will McGinnis",
    }
    for relative, marker in canonical_markers.items():
        path = ROOT / relative
        if path.exists() and marker not in path.read_text(encoding="utf-8"):
            error(f"canonical license marker missing: {relative}", failures)

    notice_path = ROOT / "NOTICE"
    if notice_path.exists():
        notice = notice_path.read_text(encoding="utf-8")
        if "Juan Antonio Yáñez García" not in notice:
            error("NOTICE must preserve the founder attribution", failures)
        if "Will McGinnis" not in notice:
            error("NOTICE must preserve the vendored Python skills attribution", failures)

    for path in repository_files():
        if not path.is_file() or ".git" in path.parts or "LICENSES" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError:
            continue
        for obsolete in OBSOLETE_LICENSE_TEXT:
            if obsolete in text:
                error(
                    f"obsolete pending-license text in {path.relative_to(ROOT)}: {obsolete}",
                    failures,
                )


def validate_example(failures: list[str]) -> None:
    example_path = ROOT / "examples/aim/file-edits.json"
    if not example_path.exists():
        error("missing AIM example", failures)
        return
    data = json.loads(example_path.read_text(encoding="utf-8"))
    required = {"aimVersion", "operation", "effects", "properties", "evidence"}
    missing = required - data.keys()
    if missing:
        error(f"AIM example missing keys: {sorted(missing)}", failures)
    if data.get("aimVersion") != "0.1.0-draft":
        error("AIM example version does not match the draft schema", failures)


def main() -> int:
    failures: list[str] = []
    validate_required_files(failures)
    validate_json(failures)
    validate_markdown_links(failures)
    validate_vendored_skills(failures)
    validate_constitution(failures)
    validate_ownership(failures)
    validate_licensing(failures)
    validate_example(failures)

    if failures:
        print("Repository validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
