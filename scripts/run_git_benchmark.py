#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run the bounded, local Git adapter reference corpus."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import git_adapter


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
}
BENCHMARK = ROOT / "examples/analysis/git-benchmark.json"


def _validated_pairs(scenarios: list[dict], definitions: list[dict]):
    expected_ids = [f"GIT-{number:03d}" for number in range(1, len(scenarios) + 1)]
    observed_ids = [item.get("id") for item in definitions]
    if len(scenarios) != len(definitions) or observed_ids != expected_ids:
        raise ValueError("Git benchmark scenarios and definitions are not aligned")
    return zip(scenarios, definitions, strict=True)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
        env=GIT_ENV,
    ).stdout


def _commit(repo: Path, base: str, branch: str, path: str, data: bytes, delete=False) -> str:
    _git(repo, "checkout", "-q", "-B", branch, base)
    target = repo / path
    if delete:
        target.unlink()
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", branch)
    return _git(repo, "rev-parse", "HEAD").strip()


def _request(repo: Path, base: str, left: str, right: str, *, dependency=False,
             uncertain=False) -> dict:
    return {
        "gitAnalysisRequestVersion": "0.1.0-alpha", "repository": str(repo),
        "baseRevision": base,
        "operations": [
            {"instanceId": "left", "attemptId": "left-1",
             "source": {"kind": "commit", "revision": left},
             "dependencies": [], "uncertainPaths": ["a.txt"] if uncertain else []},
            {"instanceId": "right", "attemptId": "right-1",
             "source": {"kind": "commit", "revision": right},
             "dependencies": ["left"] if dependency else [], "uncertainPaths": []},
        ],
    }


def _changed_paths(repo: Path, base: str, revision: str) -> tuple[set[str], int]:
    started = time.perf_counter_ns()
    output = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", "-z", base, revision],
        check=True, capture_output=True, env=GIT_ENV,
    ).stdout
    elapsed = time.perf_counter_ns() - started
    return {item.decode("utf-8", "surrogateescape") for item in output.split(b"\0") if item}, elapsed


def _file_overlap_baseline(repo: Path, base: str, scenarios: list[dict],
                           definitions: list[dict]) -> dict:
    results = []
    total_elapsed = 0
    for request, definition in _validated_pairs(scenarios, definitions):
        revisions = [operation["source"]["revision"] for operation in request["operations"]]
        left, left_elapsed = _changed_paths(repo, base, revisions[0])
        right, right_elapsed = _changed_paths(repo, base, revisions[1])
        elapsed = left_elapsed + right_elapsed
        total_elapsed += elapsed
        overlap = sorted(left & right)
        decision = "serialize" if overlap else "allow-overlap"
        results.append({
            "id": definition["id"],
            "decision": decision,
            "overlappingPaths": overlap,
            "elapsedNanoseconds": elapsed,
            "gitCommandCount": 2,
        })
    expected = {item["id"]: item["expected"] for item in definitions}
    return {
        "id": "file-overlap",
        "measuredHere": True,
        "elapsedNanoseconds": total_elapsed,
        "gitCommandCount": len(results) * 2,
        "unsafeAllowCount": sum(
            item["decision"] == "allow-overlap"
            and expected[item["id"]] != "independent-candidate"
            for item in results
        ),
        "falseSerializationCount": sum(
            item["decision"] == "serialize"
            and expected[item["id"]] == "independent-candidate"
            for item in results
        ),
        "results": results,
        "limits": "Exact changed-path overlap only; no dependencies, uncertainty, versions or semantics.",
    }


def _git_merge_baseline(repo: Path, scenarios: list[dict], definitions: list[dict]) -> dict:
    results = []
    total_elapsed = 0
    for request, definition in _validated_pairs(scenarios, definitions):
        revisions = [operation["source"]["revision"] for operation in request["operations"]]
        started = time.perf_counter_ns()
        process = subprocess.run(
            ["git", "-C", str(repo), "merge-tree", "--write-tree", "--no-messages",
             revisions[0], revisions[1]],
            capture_output=True, check=False,
            env=GIT_ENV,
        )
        elapsed = time.perf_counter_ns() - started
        total_elapsed += elapsed
        if process.returncode not in (0, 1):
            raise RuntimeError(
                f"git merge-tree failed for {definition['id']}: {process.returncode}"
            )
        results.append({
            "id": definition["id"],
            "decision": "allow-overlap" if process.returncode == 0 else "serialize",
            "exitCode": process.returncode,
            "elapsedNanoseconds": elapsed,
            "gitCommandCount": 1,
            "outputSha256": hashlib.sha256(process.stdout).hexdigest(),
        })
    expected = {item["id"]: item["expected"] for item in definitions}
    return {
        "id": "git-merge",
        "measuredHere": True,
        "elapsedNanoseconds": total_elapsed,
        "gitCommandCount": len(results),
        "unsafeAllowCount": sum(
            item["decision"] == "allow-overlap"
            and expected[item["id"]] != "independent-candidate"
            for item in results
        ),
        "falseSerializationCount": sum(
            item["decision"] == "serialize"
            and expected[item["id"]] == "independent-candidate"
            for item in results
        ),
        "results": results,
        "limits": "Temporary-repository mergeability only; not semantic independence or safe interleaving.",
    }


def run(path: Path = BENCHMARK) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.name", "Agent Braid Benchmark")
        _git(repo, "config", "user.email", "benchmark@example.invalid")
        (repo / "a.txt").write_text("base a\n")
        (repo / "b.txt").write_text("base b\n")
        _git(repo, "add", "a.txt", "b.txt")
        _git(repo, "commit", "-q", "-m", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()
        left = _commit(repo, base, "left", "a.txt", b"left\n")
        right = _commit(repo, base, "right", "b.txt", b"right\n")
        overlap = _commit(repo, base, "overlap", "a.txt", b"overlap\n")
        binary = _commit(repo, base, "binary", "binary.dat", b"a\0b")
        deletion = _commit(repo, base, "deletion", "a.txt", b"", delete=True)
        scenarios = [
            _request(repo, base, left, right),
            _request(repo, base, left, overlap),
            _request(repo, base, left, right, dependency=True),
            _request(repo, base, left, right, uncertain=True),
            _request(repo, base, left, binary),
            _request(repo, base, left, deletion),
        ]
        pairs = list(_validated_pairs(scenarios, manifest["scenarios"]))
        calls = 0
        original = git_adapter._git

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        started = time.perf_counter_ns()
        with patch("agent_braid.git_adapter._git", side_effect=counted):
            reports = [git_adapter.analyze_git(item) for item in scenarios]
        elapsed = time.perf_counter_ns() - started
        baselines = [
            _file_overlap_baseline(repo, base, scenarios, manifest["scenarios"]),
            _git_merge_baseline(repo, scenarios, manifest["scenarios"]),
        ]
        results = []
        for (_, definition), report in zip(pairs, reports, strict=True):
            results.append({**definition, "actual": report["interactions"][0]["classification"]})
        false_safe = sum(
            item["actual"] == "independent-candidate" and item["expected"] != item["actual"]
            for item in results
        )
        unknown = sum(item["actual"] == "unknown" for item in results)
        candidates = sum(item["actual"] == "independent-candidate" for item in results)
        output = {
            "benchmarkVersion": manifest["benchmarkVersion"],
            "scenarioCount": len(results), "results": results,
            "classificationAgreement": sum(item["actual"] == item["expected"] for item in results),
            "falseSafeCount": false_safe,
            "falseSerializationCount": sum(
                item["actual"] != "independent-candidate" and item["expected"] == "independent-candidate"
                for item in results
            ),
            "candidateRate": candidates / len(results), "unknownRate": unknown / len(results),
            "coverage": len(results) / len(manifest["scenarios"]),
            "analysisCost": {"gitCommandCount": calls, "elapsedNanoseconds": elapsed},
            "baselineComparisons": baselines,
            "limits": manifest["limits"],
        }
        return output


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
