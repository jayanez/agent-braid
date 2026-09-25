#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Measure bounded Git preparation against serial and frozen path-only baselines."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import random
import statistics
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.git_integration_prototype import run_prototype
from scripts.run_git_integration_benchmark import (
    commit_change, make_repository, request, source_state,
)


FROZEN_COMMIT = "60d6bcaba7245e9864298321b1038cddfde6fd9e"
FROZEN_PROTOTYPE_SHA256 = "3daf9c4ae946ab9a59fb4c2711492468ffdb6455a0bf04f6318a99b7664db860"
SEED = 20260925
BOOTSTRAP_SAMPLES = 10000


def path_overlap_waves(operations: list[dict], footprints: dict[str, dict]) -> list[list[str]]:
    """Conservative tracked-write baseline for independent complete patches."""
    if any(item["dependencies"] for item in operations) or any(
        not footprints[item["instanceId"]]["footprintComplete"]
        or not footprints[item["instanceId"]]["writes"]
        or footprints[item["instanceId"]]["reads"]
        or footprints[item["instanceId"]]["sharedResources"]
        for item in operations
    ):
        raise ValueError("path-only timing requires independent complete tracked writes")
    waves: list[list[str]] = []
    for item in sorted(operations, key=lambda value: value["instanceId"]):
        identifier = item["instanceId"]
        writes = footprints[identifier]["writes"]
        for wave in waves:
            occupied = set().union(*(footprints[member]["writes"] for member in wave))
            if not any(left == right or left.startswith(right + "/")
                       or right.startswith(left + "/")
                       for left in writes for right in occupied):
                wave.append(identifier)
                break
        else:
            waves.append([identifier])
    return waves


def load_frozen_prototype(path: Path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != FROZEN_PROTOTYPE_SHA256:
        raise ValueError("path baseline does not match the T003 reviewed module bytes")
    spec = importlib.util.spec_from_file_location("agent_braid._frozen_t003_prototype", path)
    if spec is None or spec.loader is None:
        raise ValueError("cannot load frozen T003 module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def median_interval(values: list[float]) -> tuple[float, float, float]:
    if not values:
        raise ValueError("empty performance sample")
    rng = random.Random(SEED)
    resampled = sorted(statistics.median(rng.choices(values, k=len(values)))
                       for _ in range(BOOTSTRAP_SAMPLES))
    return (statistics.median(values), resampled[249], resampled[9749])


def summarize(samples: list[dict]) -> dict:
    comparisons = {}
    for name in ("serial", "pathOverlap"):
        if any(item[name] <= 0 or item["candidate"] <= 0 for item in samples):
            raise ValueError("nonpositive benchmark timing")
        improvements = [(item[name] - item["candidate"]) / item[name]
                        for item in samples]
        median, lower, upper = median_interval(improvements)
        comparisons[name] = {
            "medianImprovement": round(median, 6),
            "confidence95": [round(lower, 6), round(upper, 6)],
            "meetsTenPercentAndPositiveInterval": median >= 0.10 and lower > 0,
        }
    return {"comparisons": comparisons,
            "goalMet": all(item["meetsTenPercentAndPositiveInterval"]
                           for item in comparisons.values())}


def measure(frozen_module, samples_per_scenario: int = 30) -> dict:
    if samples_per_scenario < 2:
        raise ValueError("at least two samples are required")
    scenarios = []
    with tempfile.TemporaryDirectory(prefix="agent-braid-m2-performance-") as folder:
        for operation_count in (2, 3):
            scenario_root = Path(folder) / str(operation_count)
            scenario_root.mkdir()
            repository, base = make_repository(scenario_root)
            names = ["left.txt", "right.txt", "third.txt"][:operation_count]
            revisions = [commit_change(repository, base, f"op-{index}", name,
                                       f"operation-{index}\n")
                         for index, name in enumerate(names)]
            job = request(repository, base, revisions, [[name] for name in names])
            before = source_state(repository)
            samples = []
            expected_tree = None
            for index in range(samples_per_scenario):
                serial_first = index % 2 == 1

                def current():
                    return run_prototype(job, benchmark_serial_first=serial_first)

                def path_baseline():
                    with patch.object(frozen_module, "_waves", side_effect=path_overlap_waves):
                        return frozen_module.run_prototype(job)

                if index % 2:
                    path_report = path_baseline()
                    report = current()
                else:
                    report = current()
                    path_report = path_baseline()
                if any(item["status"] != "completed"
                       or item["comparison"]["status"] != "match"
                       or item["unsafeAdmissionCount"] != 0
                       or not item["sourceTargetRefMatchesPinnedBaseAtFinalCheck"]
                       for item in (report, path_report)):
                    raise RuntimeError("a benchmark lane failed closed")
                trees = {item[lane]["finalTree"] for item in (report, path_report)
                         for lane in ("candidateIntegration", "serialReference")}
                if len(trees) != 1 or (expected_tree is not None and trees != {expected_tree}):
                    raise RuntimeError("benchmark trees diverged")
                expected_tree = trees.pop()
                if before != source_state(repository):
                    raise RuntimeError("benchmark changed its source repository")
                samples.append({
                    "sample": index + 1,
                    "executionOrder": "path-first" if index % 2 else "current-first",
                    "currentLaneOrder": "serial-first" if serial_first else "candidate-first",
                    "candidate": report["metrics"]["candidateTotalWallNanoseconds"],
                    "serial": report["metrics"]["serialTotalWallNanoseconds"],
                    "pathOverlap": path_report["metrics"]["candidateTotalWallNanoseconds"],
                    "candidateGitCommands": report["metrics"]["candidateTotalGitCommands"],
                    "serialGitCommands": report["metrics"]["serialTotalGitCommands"],
                    "pathOverlapGitCommands": path_report["metrics"]["candidateTotalGitCommands"],
                })
            summary = summarize(samples)
            scenarios.append({
                "operationCount": operation_count,
                "sampleCount": len(samples),
                "candidateWaves": report["candidateWaves"],
                "pathOverlapWaves": path_report["candidateWaves"],
                "pathScheduleMatchesCandidate": report["candidateWaves"] == path_report["candidateWaves"],
                "finalTree": expected_tree,
                "samplesNanoseconds": samples,
                **summary,
            })
    return {
        "benchmarkVersion": "agent-braid-m2-parallel-preparation-v1",
        "status": "measurement-complete",
        "frozenBaselineCommit": FROZEN_COMMIT,
        "frozenPrototypeSha256": FROZEN_PROTOTYPE_SHA256,
        "candidatePrototypeSha256": hashlib.sha256(
            (ROOT / "agent_braid/git_integration_prototype.py").read_bytes()).hexdigest(),
        "environment": {
            "python": sys.version.split()[0],
            "git": subprocess.run(["git", "--version"], capture_output=True,
                                  check=True, text=True).stdout.strip(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "bootstrap": {"samples": BOOTSTRAP_SAMPLES, "seed": SEED,
                      "confidence": 0.95, "statistic": "median paired fractional improvement"},
        "scenarios": scenarios,
        "goalMetOnAllScenarios": all(item["goalMet"] for item in scenarios),
        "executionAuthorization": False,
        "promotionPerformed": False,
        "limits": [
            "Synthetic fixed-patch Git workloads only; no project tests or live agents.",
            "The frozen path-only baseline uses the reviewed T003 module with a conservative write-path scheduler.",
            "On disjoint paths, candidate and path-only schedules are identical; any timing gain is implementation cost reduction, not a scheduling advantage.",
            "The prior T003 real-corpus result remains unchanged. A changed real-workload protocol requires a new founder decision.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-module", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = measure(load_frozen_prototype(args.frozen_module), args.samples)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"status": report["status"],
                      "goalMetOnAllScenarios": report["goalMetOnAllScenarios"],
                      "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
