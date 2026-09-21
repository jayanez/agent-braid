#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate M0.5 closure records without inferring human approval."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import zipfile

try:
    from scripts.closure_anchors import validate_closure_anchor
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from closure_anchors import validate_closure_anchor

if __package__:
    from .validate_release_records import validate_record
    from .validate_research_radar import validate as validate_radar
else:
    from validate_release_records import validate_record
    from validate_research_radar import validate as validate_radar


ROOT = Path(__file__).resolve().parents[1]
FEATURE = "specs/008-m0.5-closure"
RADAR = "research/radar/2026-09-18-m0.5.json"
RADAR_REVIEW = "research/reviews/2026-09-18-m0.5-radar.md"
PROPOSAL = "docs/releases/RESEARCH_PREVIEW_PROPOSAL.md"
READINESS = "docs/releases/research-preview-readiness.json"
REPRODUCTION = f"{FEATURE}/reproduction.json"
EVIDENCE = f"{FEATURE}/evidence.json"
FOUNDER_REVIEW = f"{FEATURE}/founder-review.json"
RELEASE_RECORD = "docs/releases/records/M0.5.json"
CLOSURE = "docs/releases/M0_5_CLOSURE.md"
REPORT_PPTX = "reports/agent-braid-market-trends-2026.pptx"
REPORT_PDF = "reports/agent-braid-market-trends-2026.pdf"
REPORT_ASSET = "reports/assets/agent-braid-concurrency-cover.png"
REPRODUCTION_VERSION = "0.1.0"

INPUTS = (
    "LICENSE",
    "NOTICE",
    "TRADEMARKS.md",
    "requirements-dev.txt",
    "requirements-speckit.txt",
    RADAR,
    RADAR_REVIEW,
    "research/market/2026-opportunity-model.json",
    "docs/strategy/OPEN_TOOLING_STRATEGY.md",
    "docs/strategy/ECOSYSTEM.md",
    "docs/strategy/MARKET_OPPORTUNITY.md",
    "docs/strategy/COMMUNITY.md",
    "docs/development/THIRD_PARTY.md",
    "docs/releases/VALIDATION_POLICY.md",
    PROPOSAL,
    READINESS,
    "reports/README.md",
    REPORT_PPTX,
    REPORT_PDF,
    REPORT_ASSET,
    "scripts/validate_m05_closure.py",
    "scripts/run_m05_clean_room.py",
    "scripts/validate_repository.py",
    "scripts/validate_research_radar.py",
    "scripts/market_sizing.py",
    f"{FEATURE}/spec.md",
    f"{FEATURE}/plan.md",
    f"{FEATURE}/quickstart.md",
    EVIDENCE,
    "tests/test_m05_closure.py",
    "tests/test_strategy.py",
)
REQUIRED_OBSERVATIONS = (
    ("install", "-m pip install --no-cache-dir -r requirements-dev.txt -r requirements-speckit.txt"),
    ("repository", "scripts/validate_repository.py"),
    ("contracts", "scripts/validate_contracts.py"),
    ("release-records", "scripts/validate_release_records.py"),
    ("m05-radar", "scripts/validate_research_radar.py --milestone M0.5"),
    ("market", "scripts/market_sizing.py --check"),
    ("spec-kit", "scripts/validate_spec_kit.py"),
    ("spec-kit-render", "scripts/spec_kit.py check"),
    ("spec-kit-integration", "scripts/test_spec_kit_integration.py"),
    ("tests", "-m unittest discover -s tests -v"),
    ("scientific-controls", "-m research.lab.controls"),
    ("constitution-replica", "scripts/constitution_replica.py check"),
    ("m05-candidate", "scripts/validate_m05_closure.py --candidate"),
    ("whitespace", "git diff-tree --check --root --no-commit-id -r"),
)
FOUNDER_EVIDENCE = {EVIDENCE, REPRODUCTION}
POST_FREEZE_PATHS = {
    "README.md",
    "ROADMAP.md",
    RADAR,
    RADAR_REVIEW,
    READINESS,
    RELEASE_RECORD,
    CLOSURE,
    f"{FEATURE}/assurance.json",
    f"{FEATURE}/founder-review.json",
    f"{FEATURE}/reproduction.json",
    f"{FEATURE}/tasks.md",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe repository file: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def _text(root: Path, relative: str) -> str:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe repository file: {relative}")
    return path.read_text(encoding="utf-8")


def validate_report_assets(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    for relative in (REPORT_PPTX, REPORT_PDF, REPORT_ASSET):
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            failures.append(f"missing report artifact: {relative}")
    pptx = root / REPORT_PPTX
    if pptx.is_file():
        try:
            with zipfile.ZipFile(pptx) as archive:
                names = set(archive.namelist())
                slides = [name for name in names
                          if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)]
                notes = [name for name in names
                         if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)]
                if len(slides) != 6:
                    failures.append("trends report must contain exactly six slides")
                if len(notes) != 6:
                    failures.append("every trends-report slide must retain speaker notes")
                elif any(not any(marker in archive.read(name).lower()
                                 for marker in (b"source", b"docs/", b"research/"))
                         for name in notes):
                    failures.append("every trends-report slide must cite sources or provenance")
                if not any(name.endswith("chart1.xml") for name in names):
                    failures.append("trends report must retain an editable native chart")
                if not any(name.startswith("ppt/embeddings/") and name.endswith(".xlsx")
                           for name in names):
                    failures.append("trends report chart must retain its editable workbook")
                slide_six = archive.read("ppt/slides/slide6.xml") \
                    if "ppt/slides/slide6.xml" in names else b""
                if b"<a:tbl>" not in slide_six:
                    failures.append("trends report must retain an editable native table")
                searchable = b"".join(
                    archive.read(name) for name in names
                    if name.endswith((".xml", ".rels"))
                ).lower()
                for marker in (b"market industry trends report", b"walnut exporter"):
                    if marker in searchable:
                        failures.append("current PPTX retains prohibited template provenance")
                core = archive.read("docProps/core.xml").decode("utf-8", "replace") \
                    if "docProps/core.xml" in names else ""
                if "Juan Antonio Yáñez García" not in core \
                        or "Agent Braid Open Tooling Outlook 2026" not in core:
                    failures.append("trends report metadata lacks canonical title or author")
        except (OSError, zipfile.BadZipFile) as exc:
            failures.append(f"invalid trends-report PPTX: {exc}")
    pdf = root / REPORT_PDF
    if pdf.is_file():
        payload = pdf.read_bytes()
        if not payload.startswith(b"%PDF-"):
            failures.append("trends-report preview is not a PDF")
        elif len(re.findall(rb"/Type\s*/Page\b", payload)) != 6:
            failures.append("trends-report PDF must contain exactly six pages")
    return failures


def validate_distribution_boundary(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    try:
        proposal = _text(root, PROPOSAL)
        readiness = load(root, READINESS)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]
    required_phrases = (
        "clean export", "historical Git objects", "does not rewrite history",
        "explicit authorization", "independent_validation: pending",
    )
    for phrase in required_phrases:
        if phrase.lower() not in proposal.lower():
            failures.append(f"research-preview proposal omits boundary: {phrase}")
    expected = {
        "recordVersion", "status", "currentTreeRedistributable",
        "historicalReportStatus", "recommendedPublicationMode",
        "repositoryVisibilityChangeAuthorized", "historyRewriteAuthorized",
        "limits",
    }
    if set(readiness) != expected or readiness.get("recordVersion") != "0.1.0":
        failures.append("research-preview readiness record fields or version are invalid")
    if readiness.get("status") not in {"prepared", "approved"}:
        failures.append("research-preview readiness status is invalid")
    if readiness.get("currentTreeRedistributable") is not True:
        failures.append("current tree is not recorded as redistributable")
    if readiness.get("historicalReportStatus") != "unresolved":
        failures.append("historical report redistribution must remain unresolved")
    if readiness.get("recommendedPublicationMode") != "clean-export":
        failures.append("clean export must remain the default publication mode")
    if readiness.get("repositoryVisibilityChangeAuthorized") is not False \
            or readiness.get("historyRewriteAuthorized") is not False:
        failures.append("readiness record cannot authorize visibility or history rewrite")
    if not isinstance(readiness.get("limits"), list) or not readiness["limits"]:
        failures.append("readiness limits are required")
    return failures


def validate_candidate(root: Path = ROOT) -> list[str]:
    failures = validate_radar("M0.5", root=root)
    failures.extend(validate_report_assets(root))
    failures.extend(validate_distribution_boundary(root))
    return failures


def observation_id(command: str) -> str | None:
    whitespace = "git diff-tree --check --root --no-commit-id -r "
    if command.startswith(whitespace) and re.fullmatch(
            r"[0-9a-f]{40}", command[len(whitespace):]):
        return "whitespace"
    for identifier, suffix in REQUIRED_OBSERVATIONS:
        if command == suffix or command.endswith(f" {suffix}"):
            return identifier
    return None


def _approved_radar(root: Path) -> bool:
    return not validate_radar("M0.5", root=root, require_approved=True)


def validate_reproduction(root: Path = ROOT) -> dict:
    record = load(root, REPRODUCTION)
    required = {
        "recordVersion", "capturedAt", "reviewedCommit", "tree", "platform",
        "python", "git", "cleanRoom", "operator", "inputs", "observations",
        "reportArtifacts", "independentValidation", "limits",
    }
    if set(record) != required or record.get("recordVersion") != REPRODUCTION_VERSION:
        raise ValueError("M0.5 reproduction fields or version are invalid")
    try:
        captured = datetime.fromisoformat(record["capturedAt"])
    except (TypeError, ValueError) as exc:
        raise ValueError("M0.5 reproduction capturedAt must be an RFC 3339 timestamp") from exc
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError("M0.5 reproduction capturedAt must include a timezone")
    if not isinstance(record["platform"], str) or not record["platform"].strip():
        raise ValueError("M0.5 reproduction platform is required")
    if not isinstance(record["git"], str) or not re.fullmatch(
            r"git version \d+\.\d+(?:\.\d+)?(?: .*)?", record["git"]):
        raise ValueError("M0.5 reproduction Git version is malformed")
    version = record.get("python", "")
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", version) \
            or tuple(map(int, version.split("."))) < (3, 12):
        raise ValueError("M0.5 reproduction requires Python 3.12 or newer")
    commit = record.get("reviewedCommit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("M0.5 reproduction requires an exact candidate commit")
    if root.resolve() == ROOT.resolve():
        available = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"], cwd=root,
            capture_output=True, check=False,
        )
        if available.returncode:
            raise ValueError("M0.5 reproduction candidate commit is unavailable")
    tree = record.get("tree")
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise ValueError("M0.5 reproduction requires an exact candidate tree")
    process = subprocess.run(["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root,
                             capture_output=True, check=False)
    if process.returncode or process.stdout.decode("ascii").strip() != tree:
        raise ValueError("M0.5 reproduction tree does not match candidate")
    if record.get("cleanRoom") != {
        "freshClone": True, "freshEnvironment": True, "pipCacheDisabled": True,
        "initialStatus": "", "finalStatus": "",
    }:
        raise ValueError("M0.5 reproduction is not a clean isolated run")
    operator = record.get("operator")
    if not isinstance(operator, dict) or set(operator) != {
            "independent", "authorization", "supervisor", "automation"} \
            or operator.get("independent") is not False \
            or any(not isinstance(operator.get(field), str) or not operator[field].strip()
                   for field in ("authorization", "supervisor", "automation")):
        raise ValueError("M0.5 internal operator roles are incomplete or mislabeled")
    if record.get("independentValidation") != "pending":
        raise ValueError("M0.5 reproduction cannot infer external validation")
    if set(record.get("inputs", {})) != set(INPUTS):
        raise ValueError("M0.5 reproduction input inventory is incomplete")
    for relative, checksum in record["inputs"].items():
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError(f"M0.5 reproduction input hash is malformed: {relative}")
        shown = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                               capture_output=True, check=False)
        if shown.returncode or hashlib.sha256(shown.stdout).hexdigest() != checksum:
            raise ValueError(f"M0.5 reproduction input mismatch: {relative}")
    observations = record.get("observations")
    if not isinstance(observations, list) or not observations \
            or any(item.get("exitCode") != 0 for item in observations):
        raise ValueError("M0.5 reproduction observations are absent or failed")
    expected_observations = [identifier for identifier, _ in REQUIRED_OBSERVATIONS]
    observed_ids = []
    for item in observations:
        if set(item) != {"command", "exitCode", "stdout", "stderr"} \
                or not all(isinstance(item.get(field), str)
                           for field in ("command", "stdout", "stderr")):
            raise ValueError("M0.5 reproduction observation fields are invalid")
        observed_ids.append(observation_id(item["command"]))
    if observed_ids != expected_observations:
        raise ValueError("M0.5 reproduction observations are incomplete or out of order")
    artifacts = record.get("reportArtifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != {
            REPORT_PPTX, REPORT_PDF, REPORT_ASSET}:
        raise ValueError("M0.5 report artifact inventory is incomplete")
    for relative, checksum in artifacts.items():
        if checksum != record["inputs"][relative]:
            raise ValueError("M0.5 report artifact hash is inconsistent")
    if not isinstance(record.get("limits"), list) or not record["limits"] \
            or any(not isinstance(item, str) or not item.strip()
                   for item in record["limits"]):
        raise ValueError("M0.5 reproduction limits are required")
    return record


def validate_founder_review(root: Path, candidate: str) -> list[str]:
    failures: list[str] = []
    try:
        review = load(root, FOUNDER_REVIEW)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]
    required = {
        "recordVersion", "feature", "reviewedCommit", "reviewer",
        "conflictsOfInterest", "boundedReview", "milestoneClosure",
        "researchPreviewProposal", "independentValidation",
        "repositoryVisibilityChangeAuthorized", "evidence", "limits",
    }
    if set(review) != required or review.get("recordVersion") != "0.1.0" \
            or review.get("feature") != "M0.5" \
            or review.get("reviewedCommit") != candidate:
        failures.append("M0.5 founder review identity or fields are invalid")
        return failures
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, dict) or set(reviewer) != {"name", "role"} \
            or reviewer.get("role") != "founder" \
            or not isinstance(reviewer.get("name"), str) or not reviewer["name"].strip() \
            or not isinstance(review.get("conflictsOfInterest"), str) \
            or not review["conflictsOfInterest"].strip():
        failures.append("M0.5 founder reviewer or conflict disclosure is incomplete")
    for name in ("boundedReview", "milestoneClosure", "researchPreviewProposal"):
        decision = review.get(name)
        if not isinstance(decision, dict) or set(decision) != {
                "decision", "date", "rationale"} \
                or decision.get("decision") != "approved" \
                or not isinstance(decision.get("date"), str) \
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision["date"]) \
                or not isinstance(decision.get("rationale"), str) \
                or not decision["rationale"].strip():
            failures.append(f"{name} is not explicitly approved")
    if review.get("independentValidation") != "pending":
        failures.append("founder review cannot promote independent validation")
    if review.get("repositoryVisibilityChangeAuthorized") is not False:
        failures.append("founder review cannot authorize repository visibility")
    evidence = review.get("evidence")
    if not isinstance(evidence, list) or not evidence \
            or any(not isinstance(item, dict) or set(item) != {"path", "sha256"}
                   for item in evidence) \
            or {item["path"] for item in evidence} != FOUNDER_EVIDENCE \
            or len(evidence) != len(FOUNDER_EVIDENCE):
        failures.append("M0.5 founder review evidence inventory is incomplete")
    else:
        for item in evidence:
            path = (root / item["path"]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file() \
                    or not isinstance(item["sha256"], str) \
                    or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) \
                    or digest(path) != item["sha256"]:
                failures.append("M0.5 founder review evidence is missing or changed")
                break
    if not isinstance(review.get("limits"), list) or not review["limits"] \
            or any(not isinstance(item, str) or not item.strip()
                   for item in review.get("limits", [])):
        failures.append("M0.5 founder review limits are required")
    return failures


def validate_candidate_unchanged(root: Path, candidate: str) -> list[str]:
    try:
        validate_closure_anchor(root, "M0.5", candidate)
    except ValueError as exc:
        return [str(exc)]
    return []


def validate_closure(root: Path = ROOT) -> list[str]:
    failures = validate_candidate(root)
    if not _approved_radar(root):
        failures.append("M0.5 milestone radar review is not approved")
    try:
        reproduction = validate_reproduction(root)
    except ValueError as exc:
        failures.append(str(exc))
        return failures
    failures.extend(validate_candidate_unchanged(root, reproduction["reviewedCommit"]))
    failures.extend(validate_founder_review(root, reproduction["reviewedCommit"]))
    try:
        release = load(root, RELEASE_RECORD)
        failures.extend(validate_record(release, root))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        failures.append(str(exc))
    if not (root / CLOSURE).is_file():
        failures.append("M0.5 closure record is missing")
    else:
        closure_text = _text(root, CLOSURE)
        if "**Status:** closed by explicit founder decision" not in closure_text:
            failures.append("M0.5 closure document lacks explicit founder decision")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    failures = validate_candidate() if args.candidate else validate_closure()
    if failures:
        print("M0.5 closure validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    scope = "candidate" if args.candidate else "closure"
    print(f"M0.5 {scope} gates passed; no scientific or publication approval inferred.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
