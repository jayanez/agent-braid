#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the bounded synthetic Git replay planner benchmark."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.git_replay import produce


MANIFEST = ROOT / "examples/analysis/git-replay-benchmark.json"


def _git(repo: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    process = subprocess.run(
        ["git", "-C", str(repo), *args], input=input_bytes,
        capture_output=True, check=False,
    )
    if process.returncode:
        raise RuntimeError("benchmark Git command failed: " + (args[0] if args else "unknown"))
    return process.stdout


def _commit(repo: Path, base: str, branch: str, path: str, content: bytes,
            *, delete: bool = False, binary: bool = False) -> str:
    _git(repo, "checkout", "-qb", branch, base)
    candidate = repo / path
    if delete:
        candidate.unlink()
        _git(repo, "add", "-u", "--", path)
    else:
        candidate.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            candidate.write_bytes(content)
        else:
            candidate.write_bytes(content)
        _git(repo, "add", "--", path)
    _git(repo, "commit", "-qm", branch)
    revision = _git(repo, "rev-parse", "HEAD").decode().strip()
    _git(repo, "checkout", "-q", "main")
    return revision


def _request(repo: Path, base: str, revisions: list[str], dependencies=None,
             uncertain=None) -> dict:
    dependencies = dependencies or [[] for _ in revisions]
    uncertain = uncertain or [[] for _ in revisions]
    return {
        "gitAnalysisRequestVersion": "0.1.0-alpha",
        "repository": str(repo),
        "baseRevision": base,
        "operations": [
            {
                "instanceId": f"op-{index}",
                "attemptId": f"attempt-{index}",
                "source": {"kind": "commit", "revision": revision},
                "dependencies": dependencies[index],
                "uncertainPaths": uncertain[index],
            }
            for index, revision in enumerate(revisions)
        ],
    }


def _path_waves(operation_ids: list[str], paths: dict[str, list[str]],
                dependencies: dict[str, list[str]]) -> int:
    waves: list[list[str]] = []
    completed: set[str] = set()
    while len(completed) < len(operation_ids):
        ready = sorted(item for item in operation_ids
                       if item not in completed and set(dependencies[item]) <= completed)
        wave: list[str] = []
        for item in ready:
            changed = set(paths[item])
            if all(changed.isdisjoint(paths[member]) for member in wave):
                wave.append(item)
        if not wave:
            raise RuntimeError("path-overlap baseline cannot make progress")
        waves.append(wave)
        completed.update(wave)
    return len(waves)


def _merge_waves(repo: Path, operation_ids: list[str], revisions: dict[str, str],
                 dependencies: dict[str, list[str]]) -> tuple[int, int, int]:
    started = time.perf_counter_ns()
    calls = 0
    waves: list[list[str]] = []
    completed: set[str] = set()
    while len(completed) < len(operation_ids):
        ready = sorted(item for item in operation_ids
                       if item not in completed and set(dependencies[item]) <= completed)
        wave: list[str] = []
        for operation_id in ready:
            mergeable = True
            for member in wave:
                calls += 1
                process = subprocess.run(
                    ["git", "-C", str(repo), "merge-tree", "--write-tree",
                     revisions[member], revisions[operation_id]],
                    capture_output=True, check=False,
                )
                if process.returncode not in {0, 1}:
                    raise RuntimeError("git merge-tree baseline failed")
                if process.returncode != 0:
                    mergeable = False
                    break
            if mergeable:
                wave.append(operation_id)
        if not wave:
            raise RuntimeError("Git merge baseline cannot make progress")
        waves.append(wave)
        completed.update(wave)
    return len(waves), time.perf_counter_ns() - started, calls


def _run_planner(request: dict) -> tuple[dict, dict, int, int]:
    calls = 0
    original = subprocess.Popen

    def counted(*args, **kwargs):
        nonlocal calls
        command = args[0] if args else kwargs.get("args", [])
        if (isinstance(command, (list, tuple)) and command
                and Path(command[0]).name == "git"):
            calls += 1
        return original(*args, **kwargs)

    started = time.perf_counter_ns()
    # The resource-bounded runner uses Popen so it can cap streamed output and
    # kill the process group. Count at that boundary to include every planner
    # Git process without counting fixture or baseline setup commands.
    with patch("agent_braid.git_process.subprocess.Popen", side_effect=counted):
        bundle, plan = produce(request)
    elapsed = time.perf_counter_ns() - started
    return bundle, plan, elapsed, calls


def run(path: Path = MANIFEST) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="agent-braid-replay-benchmark-") as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.name", "Agent Braid benchmark")
        _git(repo, "config", "user.email", "benchmark@example.invalid")
        (repo / "a.txt").write_text("base a\n", encoding="utf-8")
        (repo / "b.txt").write_text("base b\n", encoding="utf-8")
        (repo / "c.txt").write_text("base c\n", encoding="utf-8")
        sections = "alpha\n" + "".join(f"line-{index:02d}\n" for index in range(2, 12)) + "delta\n"
        (repo / "sections.txt").write_text(sections, encoding="utf-8")
        (repo / "overlap.txt").write_text("same\n", encoding="utf-8")
        _git(repo, "add", ".")
        _git(repo, "commit", "-qm", "base")
        base = _git(repo, "rev-parse", "HEAD").decode().strip()

        revisions = {
            "a": _commit(repo, base, "a", "a.txt", b"left a\n"),
            "b": _commit(repo, base, "b", "b.txt", b"right b\n"),
            "c": _commit(repo, base, "c", "c.txt", b"third c\n"),
            "hunk-a": _commit(repo, base, "hunk-a", "sections.txt", ("ALPHA\n" + "".join(f"line-{index:02d}\n" for index in range(2, 12)) + "delta\n").encode()),
            "hunk-b": _commit(repo, base, "hunk-b", "sections.txt", ("alpha\n" + "".join(f"line-{index:02d}\n" for index in range(2, 12)) + "DELTA\n").encode()),
            "overlap-a": _commit(repo, base, "overlap-a", "overlap.txt", b"left\n"),
            "overlap-b": _commit(repo, base, "overlap-b", "overlap.txt", b"right\n"),
            "delete": _commit(repo, base, "delete", "a.txt", b"", delete=True),
            "binary": _commit(repo, base, "binary", "binary.bin", b"a\x00b", binary=True),
        }
        definitions = [
            ("GIT-REPLAY-001", ["a", "b", "c"], ["a.txt", "b.txt", "c.txt"], None, None),
            ("GIT-REPLAY-002", ["hunk-a", "hunk-b"], ["sections.txt", "sections.txt"], None, None),
            ("GIT-REPLAY-003", ["overlap-a", "overlap-b"], ["overlap.txt", "overlap.txt"], None, None),
            ("GIT-REPLAY-004", ["a", "b"], ["a.txt", "b.txt"], [["op-1"], []], None),
            ("GIT-REPLAY-005", ["a", "b"], ["a.txt", "b.txt"], None, [["a.txt"], []]),
            ("GIT-REPLAY-006", ["delete", "b"], ["a.txt", "b.txt"], None, None),
            ("GIT-REPLAY-007", ["binary", "b"], ["binary.bin", "b.txt"], None, None),
        ]
        scenario_by_id = {item["id"]: item for item in manifest["scenarios"]}
        _require_manifest({item[0] for item in definitions}, scenario_by_id)
        results = []
        for identifier, names, changed_paths, dependencies, uncertain in definitions:
            selected = [revisions[name] for name in names]
            request = _request(repo, base, selected, dependencies, uncertain)
            bundle, plan, elapsed, git_calls = _run_planner(request)
            operation_ids = [operation["instanceId"] for operation in request["operations"]]
            path_map = {operation_id: [changed_path]
                        for operation_id, changed_path in zip(operation_ids, changed_paths)}
            dependency_map = {operation["instanceId"]: operation["dependencies"]
                              for operation in request["operations"]}
            revision_map = dict(zip(operation_ids, selected))
            merge_waves, merge_elapsed, merge_calls = _merge_waves(
                repo, operation_ids, revision_map, dependency_map
            )
            candidate = plan["mode"] == "candidate-preparation-waves"
            expected = scenario_by_id[identifier]["candidateExpected"]
            result = {
                "id": identifier,
                "family": scenario_by_id[identifier]["family"],
                "expectedCandidate": expected,
                "candidate": candidate,
                "replayResult": bundle["result"],
                "scheduleCount": len(bundle["schedules"]),
                "plannerWaveCount": len(plan["waves"]),
                "serialWaveCount": len(selected),
                "pathOverlapWaveCount": _path_waves(operation_ids, path_map, dependency_map),
                "gitMergeWaveCount": merge_waves,
                "plannerElapsedNanoseconds": elapsed,
                "plannerGitCommandCount": git_calls,
                "mergeElapsedNanoseconds": merge_elapsed,
                "mergeGitCommandCount": merge_calls,
                "unsafeCandidate": candidate and (
                    bundle["result"] != "equivalent-observed"
                    or any(schedule["status"] != "complete" for schedule in bundle["schedules"])
                ),
            }
            results.append(result)
        thresholds = manifest["thresholds"]
        false_candidates = sum(item["candidate"] and not item["expectedCandidate"] for item in results)
        unsafe_candidates = sum(item["unsafeCandidate"] for item in results)
        three = next(item for item in results if item["id"] == "GIT-REPLAY-001")
        hunks = next(item for item in results if item["id"] == "GIT-REPLAY-002")
        return {
            "benchmarkVersion": manifest["benchmarkVersion"],
            "scenarioCount": len(results),
            "results": results,
            "falseCandidateCount": false_candidates + unsafe_candidates,
            "thresholds": thresholds,
            "thresholdsPassed": (
                false_candidates == thresholds["falseCandidateCount"]
                and unsafe_candidates == 0
                and three["plannerWaveCount"] == thresholds["threeOperationPlannerWaves"]
                and three["serialWaveCount"] == thresholds["threeOperationSerialWaves"]
                and hunks["plannerWaveCount"] == thresholds["differentHunkPlannerWaves"]
                and hunks["pathOverlapWaveCount"] == thresholds["differentHunkPathOverlapWaves"]
            ),
            "limits": manifest["limits"],
        }


def _require_manifest(expected: set[str], actual: dict) -> None:
    if set(actual) != expected:
        raise ValueError("replay benchmark manifest and generated scenarios are not aligned")


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
