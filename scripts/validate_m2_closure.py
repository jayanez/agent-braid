#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Check bounded M2 closure provenance; never infer founder approval."""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

try:
    from scripts.closure_anchors import validate_closure_anchor
except ModuleNotFoundError:  # Direct script invocation.
    from closure_anchors import validate_closure_anchor


ROOT = Path(__file__).resolve().parents[1]
FEATURE = "specs/017-m2-closure"
REPRODUCTION = f"{FEATURE}/reproduction.json"
VERSION = "m2-internal-cleanroom-v1"
RADAR = "research/radar/2026-09-27-m2.json"
RADAR_REVIEW = "research/reviews/2026-09-27-m2-radar.md"
RETEST = "docs/experiments/evidence/m2-real-corpus-performance-retest.json"
RETEST_INPUTS = "docs/experiments/m2-real-corpus-retest-inputs.json"
RETEST_DECISION = "specs/013-m2-real-workload/m2-retest-founder-decision.json"
RETEST_REVIEW = "specs/013-m2-real-workload/m2-retest-founder-review.json"
MINIMUM_BASE = "ecfaf24601154b0eaf4998e4d6c6a77b490cd093"
INPUTS = (
    "CONSTITUTION.md", "GOVERNANCE.md", "ROADMAP.md",
    "requirements-dev.txt", "requirements-speckit.txt",
    RADAR, RADAR_REVIEW, RETEST, RETEST_INPUTS, RETEST_DECISION, RETEST_REVIEW,
    "docs/experiments/M2_REAL_CORPUS_RETEST_RESULT.md",
    "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-batch.json",
    "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-result.json",
    "specs/013-m2-real-workload/m2-corpus-manifest.json",
    "specs/013-m2-real-workload/m2-corpus-selection.json",
    "scripts/docker/t013/Dockerfile", "scripts/docker/t013/apt-packages.lock",
    "scripts/docker/t013/constraints-t013.txt",
    "docs/releases/M2_READINESS_REVIEW.md",
    "docs/adr/0013-isolated-git-replay-and-advisory-planning.md",
    "docs/adr/0015-real-repository-validation-profile.md",
    "docs/architecture/GIT_REPLAY.md",
    "agent_braid/git_replay.py", "agent_braid/git_partial_order.py",
    "agent_braid/git_counterexamples.py", "agent_braid/git_integration_prototype.py",
    "agent_braid/git_process.py",
    "scripts/run_m2_clean_room.py", "scripts/validate_m2_closure.py",
    "scripts/restore_public_spec_history.py",
    "examples/analysis/git-replay-benchmark.json",
    "scripts/run_git_replay_benchmark.py", "scripts/benchmark_m2_parallel_preparation.py",
    "scripts/spec_kit.py", "scripts/test_spec_kit_integration.py",
    "specs/012-m2-git-replay-planner/reproduction.json",
    "specs/013-m2-real-workload/evidence/reproduction.json",
    "specs/014-m2-observation-normalizer/evidence.json",
    "specs/015-m2-counterexample-reducer/evidence.json",
    "specs/016-m2-partial-order-reduction/evidence.json",
    "specs/016-m2-partial-order-reduction/founder-review.json",
    f"{FEATURE}/spec.md", f"{FEATURE}/plan.md", f"{FEATURE}/tasks.md",
    f"{FEATURE}/quickstart.md", f"{FEATURE}/assurance.json",
    "tests/test_git_replay.py", "tests/test_git_counterexamples.py",
    "tests/test_git_partial_order.py", "tests/test_m2_performance_retest.py",
    "tests/test_m2_closure.py",
)
REQUIRED_OBSERVATIONS = (
    ("install", "-m pip install --no-cache-dir -r requirements-dev.txt -r requirements-speckit.txt"),
    ("history", "scripts/restore_public_spec_history.py"),
    ("reviewed-tag", "git fetch origin refs/tags/spec-016-reviewed-0974739:refs/tags/spec-016-reviewed-0974739"),
    ("reachable-objects", "git fsck --unreachable --no-reflogs"),
    ("repository", "scripts/validate_repository.py"),
    ("contracts", "scripts/validate_contracts.py"),
    ("release-records", "scripts/validate_release_records.py"),
    ("radar", "scripts/validate_research_radar.py --milestone M2 --require-approved"),
    ("m2-inputs", "scripts/validate_m2_closure.py inputs"),
    ("spec-kit", "scripts/validate_spec_kit.py"),
    ("spec-kit-render", "scripts/spec_kit.py check"),
    ("spec-kit-integration", "scripts/test_spec_kit_integration.py"),
    ("tests", "-m unittest discover -s tests -v"),
    ("scientific-controls", "-m research.lab.controls"),
    ("constitution-replica", "scripts/constitution_replica.py check"),
    ("replay-benchmark", "scripts/run_git_replay_benchmark.py"),
    ("whitespace", "git diff-tree --check --root --no-commit-id -r"),
)
EXIT_CRITERIA = {
    "immutableFixtureReplay": ("tests", "replay-benchmark"),
    "boundedPreparationGain": ("m2-inputs", "tests"),
    "fixedObservationContract": ("contracts", "tests"),
    "safeEffectDefaults": ("m2-inputs", "tests"),
}
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=root, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"Git provenance command failed: {' '.join(args)}")
    return result.stdout


def _load(root: Path, relative: str) -> dict:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError(f"missing or unsafe M2 file: {relative}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"M2 record is not an object: {relative}")
    return value


def _digest(root: Path, relative: str) -> str:
    return hashlib.sha256((root / relative).read_bytes()).hexdigest()


def observation_id(command: list[str]) -> str | None:
    if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command):
        return None
    if command == ["git", "fsck", "--unreachable", "--no-reflogs"]:
        return "reachable-objects"
    if command == ["git", "fetch", "origin",
                   "refs/tags/spec-016-reviewed-0974739:refs/tags/spec-016-reviewed-0974739"]:
        return "reviewed-tag"
    if (len(command) == 7 and command[:6] == [
            "git", "diff-tree", "--check", "--root", "--no-commit-id", "-r"]
            and HEX40.fullmatch(command[6])):
        return "whitespace"
    executable = Path(command[0])
    if (command[0] not in {
            "${CLEAN_ROOM}/venv/bin/python",
            "${CLEAN_ROOM}/venv/Scripts/python.exe"}
            and (not executable.is_absolute()
            or tuple(executable.parts[-2:]) not in {
                ("bin", "python"), ("Scripts", "python.exe")
            })):
        return None
    for identifier, suffix in REQUIRED_OBSERVATIONS:
        if command[1:] == shlex.split(suffix):
            return identifier
    return None


def validate_source_evidence(root: Path = ROOT) -> dict:
    """Check finite existing evidence and the mandatory M2 radar decision."""
    radar = _load(root, RADAR).get("review", {})
    if (radar.get("kind") != "milestone" or "M2" not in radar.get("milestones", [])
            or radar.get("decision") != "approved"
            or radar.get("decisionRecord") != RADAR_REVIEW):
        raise ValueError("M2 radar lacks a bounded approved milestone decision")
    reviewer = radar.get("reviewer")
    if (not isinstance(reviewer, str) or not reviewer.strip()
            or "pending" in reviewer.lower()):
        raise ValueError("M2 radar lacks an identified approving founder")
    try:
        radar_review = (root / RADAR_REVIEW).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError("M2 radar decision record is unavailable") from exc
    if ("**Founder decision:** approved" not in radar_review
            or f"**Founder reviewer:** {reviewer}" not in radar_review):
        raise ValueError("M2 radar decision record contradicts its approval")

    retest = _load(root, RETEST)
    decision = _load(root, RETEST_DECISION)
    review = _load(root, RETEST_REVIEW)
    approved = _load(root, RETEST_INPUTS)
    reviewed_paths = {
        "docs/experiments/M2_REAL_CORPUS_RETEST_RESULT.md",
        RETEST,
        "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-batch.json",
        "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-result.json",
    }
    reviewed_artifacts = review.get("reviewedArtifacts", [])
    if (review.get("decision") != "approved-internal-result-review"
            or review.get("m2Closure") is not False
            or review.get("independentValidation") != "pending"
            or not isinstance(reviewed_artifacts, list)
            or len(reviewed_artifacts) != len(reviewed_paths)
            or {item.get("path") for item in reviewed_artifacts} != reviewed_paths):
        raise ValueError("accepted M2 retest review inventory is incomplete")
    for item in reviewed_artifacts:
        path = item["path"]
        checksum = item.get("sha256AtReviewedCommit")
        if (not isinstance(checksum, str) or not HEX64.fullmatch(checksum)
                or not (root / path).is_file()):
            raise ValueError("accepted M2 retest reviewed artifact is missing")
        # The explanatory result note was amended after the recorded review.
        # The three raw JSON artifacts remain byte-for-byte bound to that review.
        if path != "docs/experiments/M2_REAL_CORPUS_RETEST_RESULT.md" \
                and _digest(root, path) != checksum:
            raise ValueError("accepted M2 retest evidence differs from founder-reviewed bytes")
    bound_paths = {
        "specs/013-m2-real-workload/m2-corpus-manifest.json": approved.get("manifestFileSha256"),
        "specs/013-m2-real-workload/m2-corpus-selection.json": approved.get("selectionFileSha256"),
        "agent_braid/git_integration_prototype.py": approved.get("candidate", {}).get("prototypeSha256"),
        "agent_braid/git_process.py": approved.get("candidate", {}).get("gitProcessSha256"),
        "scripts/benchmark_m2_parallel_preparation.py": approved.get("candidate", {}).get("benchmarkScriptSha256"),
        **approved.get("dependencyFilesSha256", {}),
    }
    if any(not isinstance(checksum, str) or _digest(root, path) != checksum
           for path, checksum in bound_paths.items()):
        raise ValueError("registered M2 retest manifest or dependency inputs changed")
    if (decision.get("decision") != "accepted-exact-experiment"
            or decision.get("executionAuthorization") is not False
            or decision.get("m2Closure") is not False
            or _digest(root, RETEST_INPUTS) != decision.get("reviewedInputFileSha256")
            or retest.get("approvedInputsSha256") != decision.get("reviewedInputFileSha256")
            or retest.get("recordVersion") != "agent-braid-m2-real-performance-retest-1"
            or retest.get("status") != "completed"
            or retest.get("executionAuthorization") is not False
            or retest.get("promotionPerformed") is not False
            or retest.get("m2Closure") is not False):
        raise ValueError("registered M2 retest inputs, approval or safety state changed")
    batches = retest.get("batches")
    if not isinstance(batches, list) or len(batches) != 2:
        raise ValueError("M2 retest requires both registered batches")
    for index, batch in enumerate(batches, 1):
        comparisons = batch.get("comparisons", {})
        if (batch.get("batchIndex") != index or batch.get("goalMet") is not True
                or batch.get("status") != "measurement-complete"
                or batch.get("sampleCount") != 30
                or batch.get("executionAuthorization") is not False
                or len(batch.get("rawPairs", [])) != 30):
            raise ValueError("M2 retest batch is incomplete")
        for name in ("serial", "pathOverlap"):
            comparison = comparisons.get(name, {})
            interval = comparison.get("confidence95", [])
            if (comparison.get("meetsTenPercentAndPositiveInterval") is not True
                    or comparison.get("medianImprovement", 0) <= .10
                    or len(interval) != 2 or interval[0] <= 0):
                raise ValueError("M2 retest threshold or interval is unsupported")
        for pair in batch["rawPairs"]:
            report = pair.get("currentReport", {})
            if (pair.get("sourceUnchanged") is not True
                    or report.get("status") != "completed"
                    or report.get("executionAuthorization") is not False
                    or report.get("promotionPerformed") is not False
                    or report.get("unsafeAdmissionCount") != 0
                    or report.get("comparison", {}).get("treesEqual") is not True
                    or len(report.get("candidateWaves", [])) != 1):
                raise ValueError("M2 retest pair lacks bounded safe single-wave evidence")
    spec016_review = _load(root, "specs/016-m2-partial-order-reduction/founder-review.json")
    if (spec016_review.get("m2Closure") is not False
            or spec016_review.get("decision") != "approved-internal-result-review"
            or "Private finite" not in spec016_review.get("scope", "")):
        raise ValueError("SPEC-016 approval has been promoted outside its scope")
    return {
        "radar": "approved-bounded-review",
        "retest": "two-registered-30-pair-batches",
        "spec016": "private-same-replay-engine",
        "executionAuthorization": False,
    }


def validate_reproduction(root: Path = ROOT) -> dict:
    record = _load(root, REPRODUCTION)
    required = {
        "recordVersion", "capturedAt", "reviewedCommit", "candidateRef",
        "developBase", "sourceRemote", "tree", "platform",
        "python", "git", "cleanRoom", "operator", "inputs", "observations",
        "exitCriteria", "sourceEvidence", "independentValidation", "limits",
    }
    if set(record) != required or record["recordVersion"] != VERSION:
        raise ValueError("M2 reproduction fields or version are invalid")
    try:
        captured = datetime.fromisoformat(record["capturedAt"])
    except (TypeError, ValueError) as exc:
        raise ValueError("M2 capturedAt is invalid") from exc
    if captured.tzinfo is None or captured.utcoffset() is None:
        raise ValueError("M2 capturedAt must include a timezone")
    commit = record["reviewedCommit"]
    if not isinstance(commit, str) or not HEX40.fullmatch(commit):
        raise ValueError("M2 candidate must be an exact commit")
    candidate_ref = record["candidateRef"]
    if (not isinstance(candidate_ref, str)
            or not candidate_ref.startswith("refs/heads/")
            or candidate_ref == "refs/heads/develop"
            or subprocess.run(["git", "check-ref-format", candidate_ref], cwd=root,
                              capture_output=True, check=False).returncode):
        raise ValueError("M2 candidate ref must be a valid feature branch")
    base = record["developBase"]
    if not isinstance(base, str) or not HEX40.fullmatch(base):
        raise ValueError("M2 recorded develop base is invalid")
    if record["sourceRemote"] not in {
            "https://github.com/jayanez/agent-braid",
            "https://github.com/jayanez/agent-braid.git",
            "git@github.com:jayanez/agent-braid.git"}:
        raise ValueError("M2 candidate does not name the public repository")
    _git(root, "merge-base", "--is-ancestor", MINIMUM_BASE, base)
    _git(root, "merge-base", "--is-ancestor", base, commit)
    if (not isinstance(record["tree"], str) or not HEX40.fullmatch(record["tree"])
            or _git(root, "rev-parse", f"{commit}^{{tree}}").decode().strip() != record["tree"]):
        raise ValueError("M2 candidate tree does not match")
    if (not isinstance(record["python"], str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", record["python"])
            or tuple(map(int, record["python"].split("."))) < (3, 12)):
        raise ValueError("M2 reproduction requires Python 3.12+")
    if not isinstance(record["platform"], str) or not record["platform"]:
        raise ValueError("M2 platform is missing")
    if not isinstance(record["git"], str) or not record["git"].startswith("git version "):
        raise ValueError("M2 Git version is missing")
    if record["cleanRoom"] != {
        "freshClone": True, "freshEnvironment": True, "pipCacheDisabled": True,
        "initialStatus": "", "finalStatus": "",
    }:
        raise ValueError("M2 reproduction is not clean")
    operator = record["operator"]
    if (not isinstance(operator, dict) or set(operator) != {
            "independent", "authorization", "supervisor", "automation"}
            or operator["independent"] is not False
            or any(not isinstance(operator[key], str) or not operator[key].strip()
                   for key in ("authorization", "supervisor", "automation"))):
        raise ValueError("M2 operator role is incomplete or mislabeled")
    if record["independentValidation"] != "pending":
        raise ValueError("M2 external independent validation remains pending")
    if not isinstance(record["limits"], list) or not record["limits"]:
        raise ValueError("M2 limits are missing")

    inputs = record["inputs"]
    if not isinstance(inputs, dict) or set(inputs) != set(INPUTS):
        raise ValueError("M2 candidate input inventory is incomplete")
    for relative, checksum in inputs.items():
        if not isinstance(checksum, str) or not HEX64.fullmatch(checksum):
            raise ValueError(f"M2 input checksum is malformed: {relative}")
        historical = _git(root, "show", f"{commit}:{relative}")
        if hashlib.sha256(historical).hexdigest() != checksum:
            raise ValueError(f"M2 candidate input hash mismatch: {relative}")

    observations = record["observations"]
    if (not isinstance(observations, list)
            or not all(isinstance(item, dict) for item in observations)
            or [observation_id(item.get("command", [])) for item in observations]
            != [name for name, _ in REQUIRED_OBSERVATIONS]
            or any(set(item) != {"command", "exitCode", "stdout", "stderr"}
                   or not isinstance(item["command"], list)
                   or item["exitCode"] != 0 or not isinstance(item["stdout"], str)
                   or not isinstance(item["stderr"], str) for item in observations)):
        raise ValueError("M2 observations are missing, failed or out of order")
    ids = {observation_id(item["command"]) for item in observations}
    if record["exitCriteria"] != {
            key: {"status": "supported-bounded", "observations": list(required)}
            for key, required in EXIT_CRITERIA.items()}:
        raise ValueError("M2 exit-criterion inventory is invalid")
    if any(not set(required).issubset(ids) for required in EXIT_CRITERIA.values()):
        raise ValueError("M2 exit-criterion observation is missing")
    observed_by_id = {observation_id(item["command"]): item for item in observations}
    if any(item["command"][0].startswith("/")
           for item in observations if observation_id(item["command"]) not in {
               "reviewed-tag", "reachable-objects", "whitespace"}):
        raise ValueError("M2 reproduction command contains an unredacted local path")
    if observed_by_id["reachable-objects"]["stdout"].strip():
        raise ValueError("M2 clean-room object store contains unreachable objects")
    try:
        benchmark = json.loads(observed_by_id["replay-benchmark"]["stdout"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("M2 replay benchmark output is invalid") from exc
    if (benchmark.get("scenarioCount") != 7
            or benchmark.get("falseCandidateCount") != 0
            or benchmark.get("thresholdsPassed") is not True):
        raise ValueError("M2 replay benchmark thresholds are unsupported")
    try:
        observed_source = json.loads(observed_by_id["m2-inputs"]["stdout"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("M2 source-evidence output is missing") from exc
    if observed_source != record["sourceEvidence"] or observed_source != {
            "radar": "approved-bounded-review",
            "retest": "two-registered-30-pair-batches",
            "spec016": "private-same-replay-engine",
            "executionAuthorization": False,
    }:
        raise ValueError("M2 source evidence does not match the bounded record")
    return record


def validate_founder_review(root: Path, candidate: str) -> None:
    review = _load(root, f"{FEATURE}/founder-review.json")
    required = {
        "recordVersion", "feature", "reviewedCommit", "reviewer",
        "conflictsOfInterest", "scientificReview", "milestoneClosure",
        "independentValidation", "evidence", "limits",
    }
    if (set(review) != required or review.get("recordVersion") != "0.1.0"
            or review.get("feature") != "M2" or review.get("reviewedCommit") != candidate):
        raise ValueError("M2 founder review identity is invalid")
    reviewer = review["reviewer"]
    if (not isinstance(reviewer, dict) or set(reviewer) != {"name", "role"}
            or reviewer.get("role") != "founder"
            or not isinstance(reviewer.get("name"), str)
            or not reviewer["name"].strip()
            or not isinstance(review.get("conflictsOfInterest"), str)
            or not review["conflictsOfInterest"].strip()):
        raise ValueError("M2 founder conflict disclosure is missing")
    for name in ("scientificReview", "milestoneClosure"):
        decision = review[name]
        if (not isinstance(decision, dict) or set(decision) != {"decision", "date", "rationale"}
                or decision.get("decision") != "approved"
                or not isinstance(decision.get("date"), str)
                or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", decision["date"])
                or not isinstance(decision.get("rationale"), str)
                or not decision["rationale"].strip()):
            raise ValueError(f"M2 {name} requires explicit founder approval")
        try:
            datetime.strptime(decision["date"], "%Y-%m-%d")
        except ValueError as exc:
            raise ValueError(f"M2 {name} date is not a calendar date") from exc
    if review["independentValidation"] != "pending":
        raise ValueError("M2 founder review cannot infer external validation")
    if (not isinstance(review["limits"], list) or not review["limits"]
            or any(not isinstance(item, str) or not item.strip()
                   for item in review["limits"])):
        raise ValueError("M2 founder review limits are missing")
    evidence = review["evidence"]
    expected = {REPRODUCTION, RADAR, RADAR_REVIEW, RETEST,
                "specs/016-m2-partial-order-reduction/evidence.json"}
    if (not isinstance(evidence, list) or len(evidence) != len(expected)
            or {item.get("path") for item in evidence} != expected):
        raise ValueError("M2 founder evidence inventory is incomplete")
    for item in evidence:
        if (set(item) != {"path", "sha256"}
                or item["sha256"] != _digest(root, item["path"])):
            raise ValueError("M2 founder evidence hash is missing or changed")


def validate_candidate_unchanged(root: Path, candidate: str) -> None:
    anchor = validate_closure_anchor(root, "M2", candidate)
    allowed = {
        "README.md", "ROADMAP.md", "docs/development/github-tracking.json",
        "docs/releases/M2_CLOSURE.md", "docs/releases/records/M2.json",
        "specs/017-m2-closure/assurance.json",
        "specs/017-m2-closure/founder-review.json",
        "specs/017-m2-closure/reproduction.json",
        "specs/017-m2-closure/tasks.md",
    }
    unexpected = set(anchor["changedPaths"]) - allowed
    if unexpected:
        raise ValueError(f"M2 post-freeze implementation or unreviewed path changed: {sorted(unexpected)}")


def check(root: Path = ROOT, closure: bool = False) -> None:
    record = validate_reproduction(root)
    if closure:
        validate_candidate_unchanged(root, record["reviewedCommit"])
        validate_founder_review(root, record["reviewedCommit"])
        release = _load(root, "docs/releases/records/M2.json")
        if release.get("independent_validation", {}).get("status") != "pending":
            raise ValueError("M2 release record must keep independent validation pending")
        closure_text = (root / "docs/releases/M2_CLOSURE.md").read_text(encoding="utf-8")
        if "**Status:** closed by explicit founder decision" not in closure_text:
            raise ValueError("M2 closure document lacks explicit founder decision")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else "readiness"
    if mode not in {"inputs", "readiness", "closure"}:
        print("usage: validate_m2_closure.py [inputs|readiness|closure]", file=sys.stderr)
        return 2
    try:
        if mode == "inputs":
            print(json.dumps(validate_source_evidence(), sort_keys=True))
        else:
            check(closure=mode == "closure")
            print(f"M2 {mode} provenance passed; scientific and external validation remain separate.")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"M2 {mode} validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
