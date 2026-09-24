#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Measure the bounded T013 prototype against serial preparation fixtures."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.git_integration_prototype import MAX_PROCESS_ADDRESS_SPACE_BYTES, run_prototype
from agent_braid.git_process import (
    GitCommandBudget, GitCommandLimitExceeded, GitExecutionCancelled, GitExecutionTimeout,
    GitOutputLimitExceeded, GitScratchLimitExceeded, run_git,
)


def git(repository: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(repository), *arguments], input=input_bytes,
        capture_output=True, check=False, timeout=10,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
             "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C",
             "GIT_AUTHOR_NAME": "Agent Braid T013 benchmark",
             "GIT_AUTHOR_EMAIL": "agent-braid-t013@example.invalid",
             "GIT_COMMITTER_NAME": "Agent Braid T013 benchmark",
             "GIT_COMMITTER_EMAIL": "agent-braid-t013@example.invalid",
             "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
             "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"},
    )
    if process.returncode:
        raise RuntimeError("fixture Git command failed: " + (arguments[0] if arguments else "unknown"))
    return process.stdout


def git_text(repository: Path, *arguments: str) -> str:
    return git(repository, *arguments).decode("ascii", "strict").strip()


def make_repository(root: Path) -> tuple[Path, str]:
    repository = root / "source"
    repository.mkdir()
    git(repository, "init", "--quiet", "--initial-branch=main")
    git(repository, "config", "user.name", "Agent Braid T013 benchmark")
    git(repository, "config", "user.email", "agent-braid-t013@example.invalid")
    (repository / "left.txt").write_text("base left\n", encoding="utf-8")
    (repository / "right.txt").write_text("base right\n", encoding="utf-8")
    (repository / "third.txt").write_text("base third\n", encoding="utf-8")
    (repository / "shared.txt").write_text(
        "".join(f"line-{index:02}\n" for index in range(1, 41)), encoding="utf-8"
    )
    git(repository, "add", ".")
    git(repository, "commit", "--quiet", "-m", "base")
    return repository, git_text(repository, "rev-parse", "HEAD")


def commit_change(repository: Path, base: str, branch: str, path: str,
                  content: str) -> str:
    git(repository, "checkout", "--quiet", "-B", branch, base)
    (repository / path).write_text(content, encoding="utf-8")
    git(repository, "add", "--", path)
    git(repository, "commit", "--quiet", "-m", branch)
    revision = git_text(repository, "rev-parse", "HEAD")
    git(repository, "checkout", "--quiet", "main")
    return revision


def request(repository: Path, base: str, revisions: list[str], writes: list[list[str]],
            dependencies: list[list[str]] | None = None) -> dict:
    dependencies = dependencies or [[] for _ in revisions]
    return {
        "gitIntegrationPrototypeRequestVersion": "0.1.0-alpha",
        "repository": str(repository),
        "baseRevision": base,
        "targetRef": "refs/heads/main",
        "operations": [
            {
                "instanceId": f"op-{index}",
                "attemptId": f"attempt-{index}",
                "source": {"kind": "commit", "revision": revision},
                "dependencies": dependencies[index],
                "reads": [],
                "writes": writes[index],
                "sharedResources": [],
                "footprintComplete": True,
            }
            for index, revision in enumerate(revisions)
        ],
    }


def source_state(repository: Path) -> tuple[bytes, ...]:
    return (
        git(repository, "rev-parse", "HEAD"),
        git(repository, "show-ref"),
        git(repository, "status", "--porcelain=v1", "--untracked-files=all"),
        (repository / ".git" / "index").read_bytes(),
        git(repository, "count-objects", "-v"),
    )


def scenario(repository: Path, base: str, identifier: str, changes: list[tuple[str, str]],
             writes: list[list[str]], sample: int) -> dict:
    revisions = [
        commit_change(repository, base, f"{identifier}-{index}", path, content)
        for index, (path, content) in enumerate(changes)
    ]
    before = source_state(repository)
    started = time.perf_counter_ns()
    report = run_prototype(request(repository, base, revisions, writes))
    elapsed = time.perf_counter_ns() - started
    unchanged = before == source_state(repository)
    comparison = report["comparison"]["status"]
    expected_comparison = "inconclusive" if identifier == "conflict" else "match"
    if not unchanged or comparison != expected_comparison or report["unsafeAdmissionCount"] != 0:
        raise RuntimeError(f"T013 benchmark scenario failed its expected safety result: {identifier}")
    if report["status"] != ("inconclusive" if expected_comparison != "match" else "completed"):
        raise RuntimeError(f"unexpected prototype status in scenario: {identifier}")
    path_waves: list[list[str]] = []
    for index, operation_writes in enumerate(writes):
        operation = f"op-{index}"
        for wave in path_waves:
            occupied = {path for member in wave
                        for path in writes[int(member.removeprefix("op-"))]}
            if not any(path == existing or path.startswith(existing + "/")
                       or existing.startswith(path + "/")
                       for path in operation_writes for existing in occupied):
                wave.append(operation)
                break
        else:
            path_waves.append([operation])
    merge_started = time.perf_counter_ns()
    merge_children_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    merge = subprocess.run(
        ["git", "-C", str(repository), "merge-tree", "--write-tree", *revisions[:2]],
        capture_output=True, check=False, timeout=10,
        env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
             "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "LC_ALL": "C"},
    )
    merge_elapsed = time.perf_counter_ns() - merge_started
    merge_children_after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "sample": sample,
        "id": identifier,
        "expectedComparison": expected_comparison,
        "comparison": comparison,
        "candidateWaves": report["candidateWaves"],
        "candidateWaveCount": len(report["candidateWaves"]),
        "serialWaveCount": len(report["operationOrder"]),
        "unsafeAdmissionCount": report["unsafeAdmissionCount"],
        "sourceRepositoryUnchanged": unchanged,
        "wallNanosecondsIncludingHarness": elapsed,
        "reportDigest": report["reportDigest"],
        "metrics": report.get("metrics"),
        "resourceLimits": report.get("resourceLimits"),
        "pathOverlapBaseline": {"waveCount": len(path_waves), "waves": path_waves},
        "gitMergeTreePairBaseline": {
            "command": "git merge-tree --write-tree <operation-0> <operation-1>",
            "inputOperationIds": ["op-0", "op-1"],
            "status": "match" if merge.returncode == 0 else "conflict",
            "exitCode": merge.returncode,
            "wallNanoseconds": merge_elapsed,
            "gitCommandCount": 1,
            "childUserCpuSeconds": merge_children_after.ru_utime - merge_children_before.ru_utime,
            "childSystemCpuSeconds": merge_children_after.ru_stime - merge_children_before.ru_stime,
            "capturedOutputBytes": len(merge.stdout) + len(merge.stderr),
        },
    }


def resource_exhaustion_controls() -> dict:
    controls = (
        ("wall", {"wall_seconds": 0.0}, GitExecutionTimeout),
        ("command-count", {"max_commands": 0}, GitCommandLimitExceeded),
        ("captured-output", {"max_output_bytes": 0}, GitOutputLimitExceeded),
    )
    outcomes = []
    for name, limits, expected in controls:
        with tempfile.TemporaryDirectory(prefix="agent-braid-t013-limit-") as directory:
            budget = GitCommandBudget(temp_root=Path(directory), **limits)
            try:
                run_git(Path(directory), ("version",),
                        env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
                        budget=budget)
            except expected as failure:
                outcomes.append({"id": name, "status": "rejected", "category": failure.category})
            else:
                raise RuntimeError(f"resource exhaustion did not fail closed: {name}")
    with tempfile.TemporaryDirectory(prefix="agent-braid-t013-limit-") as directory:
        scratch = Path(directory)
        (scratch / "over-budget.bin").write_bytes(b"x")
        budget = GitCommandBudget(temp_root=scratch, max_scratch_bytes=0)
        try:
            run_git(scratch, ("version",),
                    env={"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C"},
                    budget=budget)
        except GitScratchLimitExceeded as failure:
            outcomes.append({"id": "temporary-data", "status": "rejected",
                             "category": failure.category})
        else:
            raise RuntimeError("resource exhaustion did not fail closed: temporary-data")
    with tempfile.TemporaryDirectory(prefix="agent-braid-t013-inflight-") as directory:
        root = Path(directory)
        for mode, limits, expected in (
            ("inflight-wall", {"wall_seconds": 0.5}, GitExecutionTimeout),
            ("inflight-temporary-data", {"max_scratch_bytes": 0}, GitScratchLimitExceeded),
            ("inflight-cancellation", {}, GitExecutionCancelled),
        ):
            scratch = root / mode
            scratch.mkdir()
            marker = root / f"{mode}.pid"
            actual_popen = subprocess.Popen
            cancellation = threading.Event()

            def start_controlled_child(_command, **kwargs):
                child = actual_popen(["/bin/sleep", "10"], **kwargs)
                marker.write_text(str(child.pid), encoding="ascii")
                if mode == "inflight-temporary-data":
                    threading.Timer(
                        0.1, lambda: (scratch / "write.bin").write_bytes(b"excess")
                    ).start()
                if mode == "inflight-cancellation":
                    threading.Timer(0.1, cancellation.set).start()
                return child

            budget = GitCommandBudget(
                temp_root=scratch, max_process_address_space_bytes=MAX_PROCESS_ADDRESS_SPACE_BYTES,
                cancel_event=cancellation, **limits,
            )
            try:
                with patch("agent_braid.git_process.subprocess.Popen",
                           side_effect=start_controlled_child):
                    run_git(scratch, ("version",), env={"LC_ALL": "C"}, budget=budget)
            except expected as failure:
                if not marker.exists():
                    raise RuntimeError(f"Git shim never started: {mode}") from failure
                try:
                    os.kill(int(marker.read_text().strip()), 0)
                except ProcessLookupError:
                    outcomes.append({"id": mode, "status": "killed-after-start",
                                     "category": failure.category,
                                     "processControl": "test-only /bin/sleep at Git Popen boundary"})
                else:
                    raise RuntimeError(f"Git child survived resource exhaustion: {mode}")
            else:
                raise RuntimeError(f"in-flight resource exhaustion was not rejected: {mode}")
    return {"controls": outcomes, "allRejected": len(outcomes) == 7}


def declared_tree_validation_control(repository: Path, base: str) -> dict:
    revisions = [
        commit_change(repository, base, "check-left", "left.txt", "validated left\n"),
        commit_change(repository, base, "check-right", "right.txt", "validated right\n"),
    ]
    before = source_state(repository)
    requested = request(repository, base, revisions, [["left.txt"], ["right.txt"]])
    requested["expectedFinalTree"] = git_text(repository, "rev-parse", f"{base}^{{tree}}")
    report = run_prototype(requested)
    unchanged = before == source_state(repository)
    passed = (report["status"] == "inconclusive"
              and report["comparison"]["status"] == "match"
              and report["declaredTrackedTreeCheck"]["status"] == "failed"
              and report["unsafeAdmissionCount"] == 1
              and not report["executionAuthorization"]
              and not report["promotionPerformed"] and unchanged)
    return {"id": "declared-tracked-tree-check-failure",
            "outcome": "rejected-as-inconclusive" if passed else "failed",
            "comparison": report["comparison"]["status"],
            "declaredCheck": report["declaredTrackedTreeCheck"],
            "unsafeAdmissionCount": report["unsafeAdmissionCount"],
            "sourceRepositoryUnchanged": unchanged,
            "controlPassed": passed}


def coordinator_restart_control(repository: Path, base: str, root: Path) -> dict:
    revisions = [
        commit_change(repository, base, "restart-left", "left.txt", "restart left\n"),
        commit_change(repository, base, "restart-right", "right.txt", "restart right\n"),
    ]
    requested = request(repository, base, revisions, [["left.txt"], ["right.txt"]])
    before = source_state(repository)
    request_path = root / "restart-request.json"
    report_path = root / "restart-report.json"
    request_path.write_text(json.dumps(requested), encoding="utf-8")
    tmpdir = root / "restart-temp"
    tmpdir.mkdir()
    command = [sys.executable, "-m", "agent_braid", "prototype-git",
               str(request_path), "--report-output", str(report_path)]
    common_env = {**os.environ, "TMPDIR": str(tmpdir), "PYTHONPATH": str(ROOT),
                  "PYTHONDONTWRITEBYTECODE": "1", "GIT_OPTIONAL_LOCKS": "0"}
    process = subprocess.Popen(command, cwd=ROOT, env=common_env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while (not list(tmpdir.glob("agent-braid-git-integration-*/scratch.git"))
               and process.poll() is None and time.monotonic() < deadline):
            time.sleep(0.005)
        if (not list(tmpdir.glob("agent-braid-git-integration-*/scratch.git"))
                or process.poll() is not None):
            raise RuntimeError("coordinator did not reach the private integration scratch state")
        process.send_signal(signal.SIGTERM)
        output, _ = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
    cancelled = json.loads(output)["category"] == GitExecutionCancelled.category
    scratch_clean = not list(tmpdir.glob("agent-braid-git-integration-*"))
    no_partial_report = not report_path.exists()
    rerun = subprocess.run(command, cwd=ROOT, env=common_env,
                           capture_output=True, check=False, timeout=35)
    if rerun.returncode != 0 or not report_path.exists():
        raise RuntimeError("coordinator restart did not complete a fresh read-only run")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    passed = (cancelled and process.returncode == 3 and scratch_clean
              and no_partial_report and report["status"] == "completed"
              and report["comparison"]["status"] == "match"
              and report["unsafeAdmissionCount"] == 0
              and not report["executionAuthorization"]
              and not report["promotionPerformed"]
              and before == source_state(repository)
              and not list(tmpdir.glob("agent-braid-git-integration-*")))
    return {"id": "graceful-coordinator-stop-and-fresh-replay",
            "firstProcessExitCode": process.returncode,
            "firstProcessCategory": "cancelled" if cancelled else "unexpected",
            "noPartialReport": no_partial_report,
            "scratchCleanAfterStop": scratch_clean,
            "freshReplayComparison": report["comparison"]["status"],
            "sourceRepositoryUnchanged": before == source_state(repository),
            "controlPassed": passed,
            "scope": "graceful SIGTERM followed by independent fresh process; not crash recovery"}


def verification_failure_control(repository: Path, base: str) -> dict:
    revisions = [
        commit_change(repository, base, "verification-left", "left.txt", "left candidate\n"),
        commit_change(repository, base, "verification-right", "right.txt", "right candidate\n"),
    ]
    before = source_state(repository)
    request_value = request(repository, base, revisions, [["left.txt"], ["right.txt"]])
    complete = {"status": "complete", "steps": [], "failure": None}
    mismatched = [
        {**complete, "finalTree": git_text(repository, "rev-parse", f"{base}^{{tree}}")},
        {**complete, "finalTree": git_text(repository, "rev-parse", f"{revisions[0]}^{{tree}}")},
    ]
    with patch("agent_braid.git_integration_prototype._integrate_lane", side_effect=mismatched):
        report = run_prototype(request_value)
    unchanged = before == source_state(repository)
    passed = (report["status"] == "inconclusive"
              and report["comparison"]["status"] == "divergent"
              and report["unsafeAdmissionCount"] == 1
              and not report["executionAuthorization"]
              and not report["promotionPerformed"] and unchanged)
    return {"id": "candidate-serial-tree-mismatch",
            "outcome": "rejected-as-inconclusive" if passed else "failed",
            "comparison": report["comparison"]["status"],
            "unsafeAdmissionCount": report["unsafeAdmissionCount"],
            "executionAuthorization": report["executionAuthorization"],
            "promotionPerformed": report["promotionPerformed"],
            "sourceRepositoryUnchanged": unchanged,
            "controlPassed": passed}


def run() -> dict:
    if sys.platform != "linux":
        raise RuntimeError("T013 benchmark must run in the Linux resource-validation container")
    with tempfile.TemporaryDirectory(prefix="agent-braid-t013-benchmark-") as directory:
        repository, base = make_repository(Path(directory))
        base_lines = [f"line-{index:02}\n" for index in range(1, 41)]
        upper = ["UPPER CHANGE\n", *base_lines[1:]]
        lower = [*base_lines[:-2], "LOWER CHANGE\n", base_lines[-1]]
        conflict_left = [*base_lines[:19], "CONFLICT LEFT\n", *base_lines[20:]]
        conflict_right = [*base_lines[:19], "CONFLICT RIGHT\n", *base_lines[20:]]
        definitions = [
            ("disjoint-two-operations", [
                ("left.txt", "left operation\n"), ("right.txt", "right operation\n"),
            ], [["left.txt"], ["right.txt"]]),
            ("disjoint-three-operations", [
                ("left.txt", "left operation\n"), ("right.txt", "right operation\n"),
                ("third.txt", "third operation\n"),
            ], [["left.txt"], ["right.txt"], ["third.txt"]]),
            ("same-file-distinct-hunks", [
                ("shared.txt", "".join(upper)), ("shared.txt", "".join(lower)),
            ], [["shared.txt"], ["shared.txt"]]),
            ("conflict", [
                ("shared.txt", "".join(conflict_left)),
                ("shared.txt", "".join(conflict_right)),
            ], [["shared.txt"], ["shared.txt"]]),
        ]
        samples = [
            scenario(repository, base, identifier, changes, writes, sample)
            for sample in range(1, 4)
            for identifier, changes, writes in definitions
        ]
        verification_control = verification_failure_control(repository, base)
        declared_validation_control = declared_tree_validation_control(repository, base)
        restart_control = coordinator_restart_control(repository, base, Path(directory))
    scenarios = []
    for identifier, _, _ in definitions:
        records = [item for item in samples if item["id"] == identifier]
        representative = dict(records[0])
        representative["repetitions"] = len(records)
        for output, metric in (
            ("medianCandidateTotalWallNanoseconds", "candidateTotalWallNanoseconds"),
            ("medianSerialTotalWallNanoseconds", "serialTotalWallNanoseconds"),
            ("medianCandidateGitCommands", "candidateTotalGitCommands"),
            ("medianSerialGitCommands", "serialTotalGitCommands"),
        ):
            values = sorted(record["metrics"][metric] for record in records)
            representative[output] = values[len(values) // 2]
        representative["sampleObservations"] = records
        scenarios.append(representative)
    eligible = [item for item in scenarios if item["expectedComparison"] == "match"]
    resource_controls = resource_exhaustion_controls()
    return {
        "benchmarkVersion": "agent-braid-t013-local-v3",
        "environment": {
            "python": sys.version.split()[0],
            "git": subprocess.run(["git", "--version"], capture_output=True,
                                  check=True, text=True).stdout.strip(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "addressSpaceBytesPerGitChild": MAX_PROCESS_ADDRESS_SPACE_BYTES,
        },
        "scenarios": scenarios,
        "negativeControls": {
            "resourceExhaustion": resource_controls,
            "candidateVerification": verification_control,
            "declaredTrackedTreeValidation": declared_validation_control,
            "gracefulCoordinatorRestart": restart_control,
            "failedProjectValidation": {
                "status": "out-of-scope",
                "reason": "T013 executes Git plumbing only. The declared tracked-tree check can fail, but repository tests and other project validation commands are not run.",
            },
        },
        "checks": {
            "allExpectedComparisonsObserved": all(
                item["comparison"] == item["expectedComparison"] for item in scenarios
            ),
            "allSourceRepositoriesUnchanged": all(
                item["sourceRepositoryUnchanged"] for item in scenarios
            ),
            "allEligibleTreesMatched": all(item["comparison"] == "match" for item in eligible),
            "conflictRemainedInconclusive": scenarios[-1]["comparison"] == "inconclusive",
            "zeroUnsafeAdmissions": all(item["unsafeAdmissionCount"] == 0 for item in scenarios),
            "resourceExhaustionFailedClosed": resource_controls["allRejected"],
            "verificationFailureRejected": verification_control["controlPassed"],
            "declaredTreeValidationFailureRejected": declared_validation_control["controlPassed"],
            "gracefulCoordinatorRestartedSafely": restart_control["controlPassed"],
            "sameFilePathOverlapBaselineReported": all(
                item["pathOverlapBaseline"]["waveCount"] == 2
                and len(item["candidateWaves"]) == 2
                for item in scenarios if item["id"] == "same-file-distinct-hunks"
            ),
            "executionAuthorization": False,
            "promotionPerformed": False,
        },
        "limits": [
            "Synthetic fixed-commit fixtures; no repository code, hooks, agents, or network actions run.",
            "A declared tracked-tree check is Git-only; project validation remains outside the authorized scope.",
            "In-flight resource controls substitute a test-only /bin/sleep child at the Git Popen boundary; they exercise monitoring and process-group termination, not Git workload memory pressure.",
            "The restart control covers graceful SIGTERM and a fresh process, not recovery from SIGKILL or a persisted coordinator state.",
            "The prototype concurrently prepares eligible patches; tree integration remains serial.",
            "Different hunks in one declared path remain serialized by the static footprint gate.",
            "Path-overlap wave counts are computed independently from the prototype; Git merge-tree timing is a pairwise two-operation baseline.",
            "Each scenario is repeated three times; the representative uses the median for candidate and serial wall time and Git command count.",
            "Timings are local measurements and do not establish semantic safety or production performance.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True,
                        help="explicit path for the T013 benchmark report")
    args = parser.parse_args()
    report = run()
    if not all(value for name, value in report["checks"].items()
               if name not in {"executionAuthorization", "promotionPerformed"}):
        raise RuntimeError("T013 benchmark failed a required safety check")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"status": "passed", "output": str(args.output),
                      "checks": report["checks"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
