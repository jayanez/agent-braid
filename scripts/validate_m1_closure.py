#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate M1 closure provenance without inferring scientific approval."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
import re
import subprocess
import sys

try:
    from scripts.closure_anchors import validate_closure_anchor
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from closure_anchors import validate_closure_anchor


ROOT = Path(__file__).resolve().parents[1]
FEATURE = "specs/007-m1-closure"
REPRODUCTION = f"{FEATURE}/reproduction.json"
REPRODUCTION_VERSION = "0.2.0"
INPUTS = (
    "requirements-dev.txt",
    "requirements-speckit.txt",
    "research/radar/2026-09-18-m1.json",
    "research/reviews/2026-09-18-m1-radar.md",
    "examples/analysis/software-benchmark.json",
    "examples/analysis/git-benchmark.json",
    "scripts/run_software_benchmark.py",
    "scripts/run_git_benchmark.py",
    "scripts/run_m1_clean_room.py",
    "scripts/spec_kit.py",
    "scripts/test_spec_kit_integration.py",
    "scripts/validate_m1_closure.py",
    "scripts/validate_release_records.py",
    "tests/test_analysis.py",
    "tests/test_git_adapter.py",
)
REQUIRED_OBSERVATIONS = (
    ("install", "-m pip install --no-cache-dir -r requirements-dev.txt -r requirements-speckit.txt"),
    ("repository", "scripts/validate_repository.py"),
    ("contracts", "scripts/validate_contracts.py"),
    ("release-records", "scripts/validate_release_records.py"),
    ("m1-radar", "scripts/validate_research_radar.py --milestone M1 --require-approved"),
    ("spec-kit", "scripts/validate_spec_kit.py"),
    ("spec-kit-render", "scripts/spec_kit.py check"),
    ("spec-kit-integration", "scripts/test_spec_kit_integration.py"),
    ("tests", "-m unittest discover -s tests -v"),
    ("scientific-controls", "-m research.lab.controls"),
    ("constitution-replica", "scripts/constitution_replica.py check"),
    ("software-benchmark", "scripts/run_software_benchmark.py"),
    ("git-benchmark", "scripts/run_git_benchmark.py"),
    ("whitespace", "git diff-tree --check --root --no-commit-id -r"),
)
FOUNDER_EVIDENCE = {
    "specs/003-read-only-analyzer/evidence.json",
    "specs/005-git-worktree-adapter/evidence.json",
    "specs/006-validation-status-policy/evidence.json",
    REPRODUCTION,
}
POST_FREEZE_PATHS = {
    "README.md",
    "ROADMAP.md",
    "docs/releases/M1_CLOSURE.md",
    "docs/releases/records/M1.json",
    "specs/003-read-only-analyzer/assurance.json",
    "specs/003-read-only-analyzer/tasks.md",
    "specs/005-git-worktree-adapter/assurance.json",
    "specs/005-git-worktree-adapter/tasks.md",
    "specs/006-validation-status-policy/assurance.json",
    "specs/006-validation-status-policy/implementation-review-0.2.0.json",
    "specs/006-validation-status-policy/tasks.md",
    "specs/007-m1-closure/assurance.json",
    "specs/007-m1-closure/founder-review.json",
    "specs/007-m1-closure/reproduction.json",
    "specs/007-m1-closure/tasks.md",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe repository file: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def _version(value: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+(?:\.\d+){1,2}", value):
        raise ValueError("reproduction Python version is malformed")
    return tuple(int(part) for part in value.split("."))


def observation_id(command: str) -> str | None:
    whitespace = "git diff-tree --check --root --no-commit-id -r "
    if command.startswith(whitespace) and re.fullmatch(r"[0-9a-f]{40}", command[len(whitespace):]):
        return "whitespace"
    for identifier, suffix in REQUIRED_OBSERVATIONS:
        if command == suffix or command.endswith(f" {suffix}"):
            return identifier
    return None


def validate_reproduction(root: Path = ROOT) -> dict:
    record = load(root, REPRODUCTION)
    required = {
        "recordVersion", "capturedAt", "reviewedCommit", "tree", "platform",
        "python", "git", "cleanRoom", "operator", "inputs", "observations",
        "benchmarks", "independentValidation", "limits",
    }
    if set(record) != required or record["recordVersion"] != REPRODUCTION_VERSION:
        raise ValueError("reproduction record fields or version are invalid")
    try:
        captured = datetime.fromisoformat(record["capturedAt"])
    except (TypeError, ValueError) as exc:
        raise ValueError("reproduction capturedAt must be an RFC 3339 timestamp") from exc
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError("reproduction capturedAt must include a timezone")
    if not isinstance(record["platform"], str) or not record["platform"].strip():
        raise ValueError("reproduction platform is required")
    if not isinstance(record["git"], str) \
            or not re.fullmatch(r"git version \d+\.\d+(?:\.\d+)?(?: .*)?", record["git"]):
        raise ValueError("reproduction Git version is malformed")
    if not isinstance(record["limits"], list) or not record["limits"] \
            or any(not isinstance(item, str) or not item.strip() for item in record["limits"]):
        raise ValueError("reproduction limits are required")
    commit = record["reviewedCommit"]
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("reproduction requires an exact candidate commit")
    if root.resolve() == ROOT.resolve():
        process = subprocess.run(["git", "cat-file", "-e", f"{commit}^{{commit}}"],
                                 cwd=root, capture_output=True, check=False)
        if process.returncode:
            raise ValueError("reproduction candidate commit is unavailable")
    if not isinstance(record["tree"], str) or not re.fullmatch(r"[0-9a-f]{40}", record["tree"]):
        raise ValueError("reproduction requires an exact candidate tree")
    tree_process = subprocess.run(
        ["git", "rev-parse", f"{commit}^{{tree}}"], cwd=root,
        capture_output=True, check=False,
    )
    if tree_process.returncode or tree_process.stdout.decode("ascii").strip() != record["tree"]:
        raise ValueError("reproduction tree does not match the candidate commit")
    if _version(record["python"]) < (3, 12):
        raise ValueError("reproduction requires Python 3.12 or newer")
    clean = record["cleanRoom"]
    if clean != {
        "freshClone": True, "freshEnvironment": True, "pipCacheDisabled": True,
        "initialStatus": "", "finalStatus": "",
    }:
        raise ValueError("reproduction is not a clean isolated run")
    operator = record["operator"]
    if not isinstance(operator, dict) or set(operator) != {
            "independent", "authorization", "supervisor", "automation"} \
            or operator.get("independent") is not False \
            or any(not isinstance(operator.get(field), str) or not operator[field].strip()
                   for field in ("authorization", "supervisor", "automation")):
        raise ValueError("internal operator roles are incomplete or mislabeled")
    if record["independentValidation"] != "pending":
        raise ValueError("M1 closure must not infer external validation")
    observations = record["observations"]
    if not isinstance(observations, list) or not observations \
            or any(item.get("exitCode") != 0 for item in observations):
        raise ValueError("reproduction observations are absent or failed")
    expected_observations = [identifier for identifier, _ in REQUIRED_OBSERVATIONS]
    observed_ids = []
    for item in observations:
        if set(item) != {"command", "exitCode", "stdout", "stderr"} \
                or not all(isinstance(item.get(field), str)
                           for field in ("command", "stdout", "stderr")):
            raise ValueError("reproduction observation fields are invalid")
        observed_ids.append(observation_id(item["command"]))
    if observed_ids != expected_observations:
        raise ValueError("reproduction observations are incomplete or out of order")
    if not isinstance(record["inputs"], dict) or set(record["inputs"]) != set(INPUTS):
        raise ValueError("candidate input inventory is incomplete")
    for relative, checksum in record["inputs"].items():
        if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError(f"candidate input hash is malformed: {relative}")
        process = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                                 capture_output=True, check=False)
        if process.returncode or hashlib.sha256(process.stdout).hexdigest() != checksum:
            raise ValueError(f"candidate input hash mismatch: {relative}")
    benchmarks = record["benchmarks"]
    if not isinstance(benchmarks, dict) or set(benchmarks) != {"software", "git"}:
        raise ValueError("reproduction benchmark inventory is invalid")
    software, git = benchmarks.get("software"), benchmarks.get("git")
    observations_by_id = dict(zip(observed_ids, observations, strict=True))
    for identifier, value in (("software-benchmark", software), ("git-benchmark", git)):
        try:
            observed_value = json.loads(observations_by_id[identifier]["stdout"])
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"{identifier} output is not valid JSON") from exc
        if observed_value != value:
            raise ValueError(f"{identifier} output does not match recorded benchmark evidence")
    if not isinstance(software, dict) or software.get("benchmarkVersion") != "software-m1-v2":
        raise ValueError("software benchmark v2 evidence is missing")
    if software.get("falseSafeCount") != 0 or software.get("conditionBoundScenarioCount") != 1:
        raise ValueError("software benchmark safety or condition result is invalid")
    if not isinstance(git, dict) or git.get("benchmarkVersion") != "git-m1-v2":
        raise ValueError("Git benchmark v2 evidence is missing")
    if git.get("falseSafeCount") != 0 or git.get("coverage") != 1.0:
        raise ValueError("Git benchmark safety or coverage result is invalid")
    baselines = {item.get("id"): item for item in git.get("baselineComparisons", [])}
    if set(baselines) != {"file-overlap", "git-merge"}:
        raise ValueError("measured Git baselines are incomplete")
    for baseline in baselines.values():
        if baseline.get("measuredHere") is not True or baseline.get("gitCommandCount", 0) <= 0 \
                or baseline.get("elapsedNanoseconds", 0) <= 0 or len(baseline.get("results", [])) != 6:
            raise ValueError("Git baseline measurements are incomplete")
    return record


def validate_founder_review(root: Path, candidate: str) -> None:
    review = load(root, f"{FEATURE}/founder-review.json")
    required = {
        "recordVersion", "feature", "reviewedCommit", "reviewer",
        "conflictsOfInterest", "scientificReview", "milestoneClosure",
        "independentValidation", "evidence", "limits",
    }
    if set(review) != required or review.get("recordVersion") != "0.1.0" \
            or review.get("feature") != "M1" or review.get("reviewedCommit") != candidate:
        raise ValueError("M1 founder review identity or fields are invalid")
    reviewer = review.get("reviewer")
    if not isinstance(reviewer, dict) or set(reviewer) != {"name", "role"} \
            or reviewer.get("role") != "founder" \
            or not isinstance(reviewer.get("name"), str) or not reviewer["name"].strip() \
            or not isinstance(review.get("conflictsOfInterest"), str) \
            or not review["conflictsOfInterest"].strip():
        raise ValueError("M1 founder reviewer or conflict disclosure is incomplete")
    for name in ("scientificReview", "milestoneClosure"):
        decision = review[name]
        if not isinstance(decision, dict) or set(decision) != {"decision", "date", "rationale"} \
                or decision.get("decision") != "approved" \
                or not isinstance(decision.get("date"), str) \
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision["date"]) \
                or not isinstance(decision.get("rationale"), str) \
                or not decision["rationale"].strip():
            raise ValueError(f"{name} is not explicitly approved")
    if review["independentValidation"] != "pending":
        raise ValueError("founder review cannot promote independent validation")
    evidence = review["evidence"]
    if not isinstance(evidence, list) or not evidence \
            or any(not isinstance(item, dict) or set(item) != {"path", "sha256"}
                   for item in evidence) \
            or {item["path"] for item in evidence} != FOUNDER_EVIDENCE \
            or len(evidence) != len(FOUNDER_EVIDENCE):
        raise ValueError("founder review evidence inventory is incomplete")
    for item in evidence:
        path = (root / item.get("path", "")).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file() \
                or not isinstance(item.get("sha256"), str) \
                or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]) \
                or digest(path) != item["sha256"]:
            raise ValueError("founder review evidence is missing or changed")
    if not isinstance(review["limits"], list) or not review["limits"] \
            or any(not isinstance(item, str) or not item.strip() for item in review["limits"]):
        raise ValueError("founder review limits are required")


def validate_candidate_unchanged(root: Path, candidate: str) -> None:
    validate_closure_anchor(root, "M1", candidate)


def check(root: Path = ROOT, closure: bool = False) -> None:
    reproduction = validate_reproduction(root)
    if closure:
        validate_candidate_unchanged(root, reproduction["reviewedCommit"])
        validate_founder_review(root, reproduction["reviewedCommit"])
        release = load(root, "docs/releases/records/M1.json")
        if release.get("independent_validation", {}).get("status") != "pending":
            raise ValueError("M1 release record must preserve pending independent validation")
        closure_text = (root / "docs/releases/M1_CLOSURE.md").read_text(encoding="utf-8")
        if "**Status:** closed by explicit founder decision" not in closure_text:
            raise ValueError("M1 closure document lacks explicit founder decision")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else "readiness"
    if mode not in {"readiness", "closure"}:
        print("usage: validate_m1_closure.py [readiness|closure]", file=sys.stderr)
        return 2
    try:
        check(closure=mode == "closure")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"M1 {mode} validation failed: {exc}", file=sys.stderr)
        return 1
    print(f"M1 {mode} provenance passed; no external validation or scientific truth inferred.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
