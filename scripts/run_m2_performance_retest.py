#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the exact founder-accepted M2 real-corpus performance retest."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.git_integration_prototype import run_prototype
from scripts.benchmark_m2_parallel_preparation import (
    cost_breakdown, load_frozen_prototype, path_overlap_waves, summarize, timed_phases,
)
from scripts.run_git_integration_benchmark import source_state
from scripts.run_m2_real_workload import archive_tree, classify, prototype_request, run_lane
from scripts.validate_m2_retest_proposal import (
    IMAGE, INPUT_PATH, INPUT_SHA256, PROPOSAL_COMMIT, PROPOSAL_PATH,
    PROPOSAL_SHA256, expected_refs, git,
    sha, validate_proposal,
)


DECISION_PATH = "specs/013-m2-real-workload/m2-retest-founder-decision.json"
SELECTION_PATH = "specs/013-m2-real-workload/m2-corpus-selection.json"
MAX_CONTAINER_SECONDS = 180
MAX_CONTAINER_OUTPUT = 8 * 1024 * 1024


class RetestRejected(ValueError):
    """The approval, safety contract, or experiment observation failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise RetestRejected(reason)


def verify_decision(root: Path = ROOT) -> tuple[dict, dict, dict]:
    decision = json.loads((root / DECISION_PATH).read_bytes())
    proposal = json.loads((root / INPUT_PATH).read_bytes())
    selection = json.loads((root / SELECTION_PATH).read_bytes())
    require(decision["decision"] == "accepted-exact-experiment"
            and decision["reviewedProposalCommit"] == PROPOSAL_COMMIT
            and decision["reviewedProposalPath"] == PROPOSAL_PATH
            and decision["approvedInputsPath"] == INPUT_PATH
            and decision["reviewedProposalSha256"] == PROPOSAL_SHA256
            and decision["reviewedInputFileSha256"] == INPUT_SHA256,
            "exact founder decision is absent or changed")
    require(sha((root / PROPOSAL_PATH).read_bytes()) == PROPOSAL_SHA256
            and sha((root / INPUT_PATH).read_bytes()) == INPUT_SHA256,
            "approved proposal bytes changed")
    require(decision["executionAuthorization"] is False
            and decision["m2Closure"] is False
            and decision["externalHumanValidation"] == "pending",
            "decision claims unearned validation")
    require(proposal["status"] == "pending-founder-decision"
            and proposal["executionAuthorization"] is False,
            "approved input file must remain the frozen proposal")
    require(sha((root / "agent_braid/git_integration_prototype.py").read_bytes())
            == proposal["candidate"]["prototypeSha256"]
            and sha((root / "agent_braid/git_process.py").read_bytes())
            == proposal["candidate"]["gitProcessSha256"]
            and sha((root / "scripts/benchmark_m2_parallel_preparation.py").read_bytes())
            == proposal["candidate"]["benchmarkScriptSha256"],
            "candidate implementation changed after approval")
    return decision, proposal, selection


def frozen_baseline(repository: Path, proposal: dict, directory: Path):
    baseline = proposal["pathOverlapBaseline"]
    content = git(repository, "show", baseline["prototypeCommit"]
                  + ":agent_braid/git_integration_prototype.py")
    require(sha(content) == baseline["prototypeSha256"],
            "frozen path baseline bytes changed")
    path = directory / "frozen-t003-prototype.py"
    path.write_bytes(content)
    return load_frozen_prototype(path)


def source_fingerprint(repository: Path) -> str:
    parts = source_state(repository)
    digest = hashlib.sha256()
    for part in parts:
        digest.update(len(part).to_bytes(8, "big"))
        digest.update(part)
    return digest.hexdigest()


def complete_report(report: dict) -> bool:
    return (report["status"] == "completed"
            and report["comparison"]["status"] == "match"
            and report["unsafeAdmissionCount"] == 0
            and report["sourceTargetRefMatchesPinnedBaseAtFinalCheck"] is True
            and report["candidateIntegration"]["status"] == "complete"
            and report["serialReference"]["status"] == "complete")


def trees(report: dict) -> set[str]:
    return {report["candidateIntegration"]["finalTree"],
            report["serialReference"]["finalTree"]}


def real_path_overlap_waves(operations: list[dict],
                            footprints: dict[str, dict]) -> list[list[str]]:
    """Use tracked writes only when every declared read is already a write."""
    require(all(set(footprints[item["instanceId"]]["reads"])
                <= set(footprints[item["instanceId"]]["writes"])
                for item in operations), "path baseline has an uncovered read")
    write_only = {identifier: {**footprint, "reads": []}
                  for identifier, footprint in footprints.items()}
    return path_overlap_waves(operations, write_only)


def measure_batch(repository: Path, proposal: dict, selection: dict,
                  batch_index: int) -> dict:
    """Run one offline 30-pair batch; keep every raw lane report."""
    require(batch_index in (1, 2), "batch index is outside the approved protocol")
    _, _, _ = verify_decision()
    request = prototype_request(repository, selection)
    before = source_fingerprint(repository)
    raw_pairs = []
    samples = []
    final_tree = None
    with tempfile.TemporaryDirectory(prefix="agent-braid-m2-retest-baseline-") as folder:
        frozen = frozen_baseline(repository, proposal, Path(folder))
        for index in range(30):
            serial_first = bool(index % 2)

            def current():
                return run_prototype(request, benchmark_serial_first=serial_first)

            def path_baseline():
                with patch.object(frozen, "_waves", side_effect=real_path_overlap_waves):
                    return frozen.run_prototype(request)

            if index % 2:
                path_report = path_baseline()
                report = current()
            else:
                report = current()
                path_report = path_baseline()
            after = source_fingerprint(repository)
            pair = {"pair": index + 1,
                    "executionOrder": "path-first" if index % 2 else "current-first",
                    "currentLaneOrder": "serial-first" if serial_first else "candidate-first",
                    "sourceFingerprintBefore": before,
                    "sourceFingerprintAfter": after,
                    "sourceUnchanged": before == after,
                    "currentReport": report, "pathReport": path_report}
            raw_pairs.append(pair)
            equal_trees = (complete_report(report) and complete_report(path_report)
                           and len(trees(report) | trees(path_report)) == 1)
            if not equal_trees or before != after:
                return {"status": "inconclusive", "reason": "tree-safety-or-source-check",
                        "batchIndex": batch_index, "rawPairs": raw_pairs,
                        "executionAuthorization": False}
            tree = next(iter(trees(report)))
            if final_tree is not None and tree != final_tree:
                return {"status": "inconclusive", "reason": "nonrepeatable-tree",
                        "batchIndex": batch_index, "rawPairs": raw_pairs,
                        "executionAuthorization": False}
            final_tree = tree
            sample = {
                "pair": index + 1,
                "candidate": report["metrics"]["candidateTotalWallNanoseconds"],
                "serial": report["metrics"]["serialTotalWallNanoseconds"],
                "pathOverlap": path_report["metrics"]["candidateTotalWallNanoseconds"],
                "phases": {
                    "candidate": timed_phases(report, "candidate"),
                    "serial": timed_phases(report, "serial"),
                    "pathOverlap": timed_phases(path_report, "candidate"),
                },
                "candidateGitCommands": report["metrics"]["candidateTotalGitCommands"],
                "serialGitCommands": report["metrics"]["serialTotalGitCommands"],
                "pathOverlapGitCommands": path_report["metrics"]["candidateTotalGitCommands"],
            }
            samples.append(sample)
    summary = summarize(samples)
    return {
        "recordVersion": "agent-braid-m2-real-performance-batch-1",
        "status": "measurement-complete", "batchIndex": batch_index,
        "sampleCount": len(samples), "finalTree": final_tree,
        "sourceFingerprint": before, "rawPairs": raw_pairs,
        "samplesNanoseconds": samples,
        "costBreakdown": cost_breakdown(samples), **summary,
        "executionAuthorization": False,
    }


def materialize(repository: Path, selection: dict, directory: Path,
                expected_tree: str) -> dict:
    request = prototype_request(repository, selection)
    before = source_fingerprint(repository)
    reports = []
    archives = {}
    for pair in range(2):
        paths = {lane: directory / f"{lane}-{pair}.tar"
                 for lane in ("candidate", "serial")}

        def consume(scratch: Path, candidate: str, serial: str) -> None:
            archive_tree(scratch, candidate, paths["candidate"])
            archive_tree(scratch, serial, paths["serial"])

        report = run_prototype(request, tree_consumer=consume,
                               benchmark_serial_first=bool(pair % 2))
        reports.append(report)
        if (not complete_report(report) or trees(report) != {expected_tree}
                or source_fingerprint(repository) != before):
            return {"status": "inconclusive", "reason": "materialized-tree-or-source-check",
                    "gitReports": reports, "archives": archives,
                    "executionAuthorization": False}
        archives[str(pair)] = {
            lane: {"sha256": sha(paths[lane].read_bytes()),
                   "bytes": paths[lane].stat().st_size,
                   "tree": expected_tree}
            for lane in ("candidate", "serial")
        }
    return {"status": "completed", "gitReports": reports, "archives": archives,
            "sourceFingerprint": before, "executionAuthorization": False}


def docker_phase(repository: Path, artifacts: Path, phase: str,
                 batch_index: int | None = None, expected_tree: str | None = None) -> dict:
    name = "agent-braid-m2-retest-" + uuid.uuid4().hex
    output = f"/artifacts/{phase}-{batch_index if batch_index is not None else 'trees'}.json"
    args = [
        "docker", "run", "--rm", "--name", name, "--network=none", "--read-only",
        "--memory=2g", "--memory-swap=2g", "--cpus=2", "--pids-limit=512",
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777",
        "--mount", f"type=bind,src={ROOT},dst=/harness,readonly",
        "--mount", f"type=bind,src={repository},dst={repository},readonly",
        "--mount", f"type=bind,src={artifacts},dst=/artifacts",
        "--workdir=/harness", "--env=HOME=/tmp/home", "--env=TMPDIR=/tmp",
        "--env=PYTHONDONTWRITEBYTECODE=1",
        "--env=GIT_CONFIG_NOSYSTEM=1", "--env=GIT_CONFIG_GLOBAL=/dev/null",
        "--env=GIT_NO_REPLACE_OBJECTS=1", "--env=GIT_TERMINAL_PROMPT=0",
        "--env=GIT_CONFIG_COUNT=2", "--env=GIT_CONFIG_KEY_0=core.hooksPath",
        "--env=GIT_CONFIG_VALUE_0=/dev/null",
        "--env=GIT_CONFIG_KEY_1=safe.directory",
        "--env=GIT_CONFIG_VALUE_1=" + str(repository),
        IMAGE, "python", "/harness/scripts/run_m2_performance_retest.py",
        "--internal-phase", phase, "--repository", str(repository),
        "--output", output,
    ]
    if batch_index is not None:
        args.extend(["--batch-index", str(batch_index)])
    if expected_tree is not None:
        args.extend(["--expected-tree", expected_tree])
    try:
        process = subprocess.run(args, capture_output=True, timeout=MAX_CONTAINER_SECONDS,
                                 check=False)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True,
                       timeout=15, check=False)
        subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                       timeout=15, check=False)
        return {"status": "inconclusive", "reason": "offline-container-timeout",
                "executionAuthorization": False}
    require(len(process.stdout) <= MAX_CONTAINER_OUTPUT
            and len(process.stderr) <= MAX_CONTAINER_OUTPUT,
            "offline container exceeded output bound")
    result_path = artifacts / Path(output).name
    if result_path.is_file():
        require(result_path.stat().st_size <= 64 * 1024 * 1024,
                "offline evidence file exceeded bound")
        result = json.loads(result_path.read_bytes())
        if process.returncode == 0 or result.get("status") in {"inconclusive", "rejected"}:
            return result
    raise RetestRejected("offline phase failed without bounded evidence: "
                         + process.stderr[-2048:].decode("utf-8", "replace"))


def remote_snapshot(repository: Path, proposal: dict) -> dict[str, str]:
    refs = sorted(expected_refs(proposal))
    lines = git(repository, "ls-remote", "origin", *refs).decode("ascii", "strict").splitlines()
    return {ref: oid for oid, ref in (line.split() for line in lines)}


def classify_retest(batches: list[dict], materialized: dict,
                    lanes: dict[str, list[dict]], remote_exact: bool) -> tuple[str, str | None]:
    if not remote_exact:
        return "rejected", "live-remote-ref-moved"
    if len(batches) != 2 or any(item.get("status") != "measurement-complete"
                                or item.get("sampleCount") != 30 for item in batches):
        return "inconclusive", "git-measurement-incomplete"
    if batches[0]["finalTree"] != batches[1]["finalTree"]:
        return "inconclusive", "nonrepeatable-batch-tree"
    if materialized.get("status") != "completed":
        return "inconclusive", "tree-materialization-incomplete"
    status, reason = classify(materialized["gitReports"], lanes, remote_exact)
    if status != "completed":
        return status, reason
    if any(not item["goalMet"] for item in batches):
        return "negative-performance", "median-or-bootstrap-threshold-not-met"
    return "completed", None


def phase_exit_code(status: str, internal_phase: str | None) -> int:
    if internal_phase == "batch":
        return 0 if status == "measurement-complete" else 1
    if internal_phase == "materialize":
        return 0 if status == "completed" else 1
    return 0 if status in {"completed", "negative-performance"} else 1


def validate_output_path(output: Path, repository: Path,
                         internal_phase: str | None) -> None:
    require(output.parent.is_dir() and not output.is_symlink(),
            "explicit evidence artifact directory required")
    if internal_phase:
        require(output.parent == Path("/artifacts")
                and Path("/artifacts") in output.resolve().parents,
                "internal phase needs the designated artifact directory")
    else:
        target = output.resolve()
        require(ROOT.resolve() not in (target, *target.parents)
                and repository.resolve() not in (target, *target.parents),
                "evidence must be outside the harness and source repositories")


def run(repository: Path, output: Path) -> dict:
    decision, proposal, _ = verify_decision()
    validate_output_path(output, repository, None)
    started = time.monotonic()
    preflights = []
    batches = []
    remote_snapshots = []
    materialized = {}
    lanes: dict[str, list[dict]] = {}
    status = "inconclusive"
    reason = None
    preflights.append(validate_proposal(repository))
    remote_snapshots.append(preflights[-1]["remoteRefsAfter"])
    for index in (1, 2):
        if index > 1:
            preflights.append(validate_proposal(repository))
            remote_snapshots.append(preflights[-1]["remoteRefsAfter"])
        batch = docker_phase(repository, output.parent, "batch", index)
        batches.append(batch)
        remote = remote_snapshot(repository, proposal)
        remote_snapshots.append(remote)
        if remote != expected_refs(proposal):
            status, reason = "rejected", "live-remote-ref-moved"
            break
        if batch.get("status") != "measurement-complete":
            reason = "git-measurement-incomplete"
            break
        if len(batches) == 2 and batches[0]["finalTree"] != batches[1]["finalTree"]:
            reason = "nonrepeatable-batch-tree"
            break
    if len(batches) == 2 and all(item.get("status") == "measurement-complete"
                                 for item in batches) and reason is None:
        preflights.append(validate_proposal(repository))
        remote_snapshots.append(preflights[-1]["remoteRefsAfter"])
        materialized = docker_phase(repository, output.parent, "materialize",
                                    expected_tree=batches[0]["finalTree"])
        remote_snapshots.append(remote_snapshot(repository, proposal))
        if materialized.get("status") == "completed":
            if remote_snapshots[-1] == expected_refs(proposal):
                for lane in ("candidate", "serial"):
                    lanes[lane] = [run_lane(repository, output.parent / f"{lane}-{index}.tar",
                                            batches[0]["finalTree"])
                                   for index in range(2)]
                remote_snapshots.append(remote_snapshot(repository, proposal))
        status, reason = classify_retest(batches, materialized, lanes,
                                         all(ref == expected_refs(proposal)
                                             for ref in remote_snapshots))
    return {
        "recordVersion": "agent-braid-m2-real-performance-retest-1",
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "status": status, "reason": reason,
        "decisionSha256": sha((ROOT / DECISION_PATH).read_bytes()),
        "approvedInputsSha256": INPUT_SHA256,
        "preflightCheckerCommit": preflights[0]["checkerCommit"],
        "preflights": preflights, "remoteSnapshots": remote_snapshots,
        "batches": batches, "materialization": materialized,
        "testLanes": lanes,
        "image": IMAGE, "command": proposal["allowlistedCommand"],
        "resourceLimits": proposal["resourceLimits"],
        "elapsedSeconds": round(time.monotonic() - started, 6),
        "executionAuthorization": False, "promotionPerformed": False,
        "externalHumanValidation": "pending", "m2Closure": False,
        "limits": ["Finite registered corpus only; no live agents or external effects verified.",
                   "A positive timing result would require separate human assessment."],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--internal-phase", choices=("batch", "materialize"),
                        help=argparse.SUPPRESS)
    parser.add_argument("--batch-index", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--expected-tree", help=argparse.SUPPRESS)
    args = parser.parse_args()
    repository = args.repository.resolve()
    try:
        validate_output_path(args.output, repository, args.internal_phase)
    except RetestRejected as exc:
        parser.exit(1, f"M2 retest rejected: {exc}\n")
    try:
        if args.internal_phase:
            _, proposal, selection = verify_decision()
            if args.internal_phase == "batch":
                report = measure_batch(repository, proposal, selection, args.batch_index)
            else:
                require(args.expected_tree is not None and len(args.expected_tree) == 40,
                        "materialization requires the verified tree")
                report = materialize(repository, selection, args.output.parent,
                                     args.expected_tree)
        else:
            report = run(repository, args.output)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError,
            subprocess.TimeoutExpired) as exc:
        report = {"recordVersion": "agent-braid-m2-real-performance-retest-1",
                  "status": "rejected", "reason": str(exc),
                  "executionAuthorization": False, "promotionPerformed": False}
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"], "reason": report.get("reason"),
                      "output": str(args.output)}, sort_keys=True))
    return phase_exit_code(report["status"], args.internal_phase)


if __name__ == "__main__":
    raise SystemExit(main())
