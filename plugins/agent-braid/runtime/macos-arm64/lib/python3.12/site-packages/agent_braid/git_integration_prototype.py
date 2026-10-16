# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, local and read-only Git integration experiment."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
from pathlib import Path, PurePosixPath
import threading
import tempfile
import time
from typing import Callable

from .analysis import _digest
from .git_adapter import InvalidGitAnalysis, analyze_git_with_provenance
from .git_process import GitCommandBudget, GitCommandFailure, run_git
from .git_replay import (
    GitPatchRejected,
    InvalidGitReplay,
    OID,
    _mark_unsupported_binary_patches,
    _patches,
    _sanitized_environment,
    _supported_operations,
    _topological_orders,
)


REQUEST_VERSION = "0.1.0-alpha"
REPORT_VERSION = "0.1.0-alpha"
MAX_OPERATIONS = 4
MAX_CHANGED_PATHS = 16
MAX_PATCH_BYTES = 256 * 1024
MAX_WALL_SECONDS = 30.0
MAX_GIT_COMMANDS = 128
MAX_OUTPUT_BYTES = 8 * 1024 * 1024
MAX_COMMAND_OUTPUT_BYTES = 2 * 1024 * 1024
MAX_SCRATCH_BYTES = 32 * 1024 * 1024
MAX_WORKERS = 2
MAX_PROCESS_ADDRESS_SPACE_BYTES = 512 * 1024 * 1024
POLL_INTERVAL_SECONDS = 0.05


class InvalidGitIntegrationPrototype(ValueError):
    """A prototype request is malformed or outside its fixed local profile."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidGitIntegrationPrototype(message)


def _git(repo: Path, env: dict[str, str], *args: str,
         budget: GitCommandBudget, input_bytes: bytes | None = None,
         allow_failure: bool = False):
    try:
        return run_git(repo, args, env=env, budget=budget, input_bytes=input_bytes,
                       allow_failure=allow_failure, command_timeout=MAX_WALL_SECONDS,
                       poll_interval=0.001)
    except GitCommandFailure as exc:
        command = args[0] if args else "unknown"
        if command == "apply":
            raise GitPatchRejected("fixed fixture patch was rejected") from exc
        raise InvalidGitIntegrationPrototype(f"Git fixture command failed: {command}") from exc


def _path(value: object, label: str) -> str:
    _require(isinstance(value, str) and 0 < len(value) <= 1024 and "\0" not in value,
             f"invalid {label} path")
    parsed = PurePosixPath(value)
    _require(not parsed.is_absolute() and all(part not in {"", ".", ".."}
                                               for part in value.split("/")),
             f"unsafe {label} path")
    return value


def _validate_request(value: object) -> tuple[dict, dict[str, dict]]:
    _require(isinstance(value, dict), "prototype request must be an object")
    expected = {
        "gitIntegrationPrototypeRequestVersion", "repository", "baseRevision",
        "targetRef", "operations",
    }
    _require(expected <= set(value) <= expected | {"expectedFinalTree"},
             "invalid prototype request fields")
    _require(value["gitIntegrationPrototypeRequestVersion"] == REQUEST_VERSION,
             "unsupported prototype request version")
    _require(isinstance(value["repository"], str) and value["repository"].strip(),
             "invalid repository path")
    _require(isinstance(value["baseRevision"], str) and OID.fullmatch(value["baseRevision"]),
             "baseRevision must be a full immutable commit ID")
    if "expectedFinalTree" in value:
        _require(isinstance(value["expectedFinalTree"], str)
                 and OID.fullmatch(value["expectedFinalTree"]),
                 "expectedFinalTree must be a full immutable tree ID")
    target_ref = value["targetRef"]
    _require(isinstance(target_ref, str) and target_ref.startswith("refs/heads/")
             and len(target_ref) <= 256 and not any(token in target_ref for token in ("..", "@{")),
             "targetRef must be a local branch reference")
    operations = value["operations"]
    _require(isinstance(operations, list) and 2 <= len(operations) <= MAX_OPERATIONS,
             "prototype accepts 2–4 operations")
    m1_operations = []
    footprints: dict[str, dict] = {}
    ids: list[str] = []
    attempts: list[str] = []
    for operation in operations:
        _require(isinstance(operation, dict) and set(operation) == {
            "instanceId", "attemptId", "source", "dependencies", "reads", "writes",
            "sharedResources", "footprintComplete",
        }, "invalid prototype operation fields")
        for field in ("instanceId", "attemptId"):
            _require(isinstance(operation[field], str) and 0 < len(operation[field]) <= 256,
                     f"invalid {field}")
        ids.append(operation["instanceId"])
        attempts.append(operation["attemptId"])
        source = operation["source"]
        _require(isinstance(source, dict) and set(source) == {"kind", "revision"}
                 and source["kind"] == "commit" and isinstance(source["revision"], str)
                 and OID.fullmatch(source["revision"]), "prototype accepts full commit sources only")
        dependencies = operation["dependencies"]
        _require(isinstance(dependencies, list)
                 and all(isinstance(item, str) and item for item in dependencies)
                 and len(dependencies) == len(set(dependencies)), "invalid dependencies")
        footprint_paths = {}
        has_wildcard = False
        for name in ("reads", "writes"):
            paths = operation[name]
            _require(isinstance(paths, list) and all(isinstance(item, str) for item in paths),
                     f"invalid {name} footprint")
            _require(len(paths) == len(set(paths)), f"duplicate {name} footprint")
            normalized = sorted(_path(item, name) for item in paths)
            has_wildcard = has_wildcard or any(
                any(character in item for character in "*?[]") for item in normalized
            )
            footprint_paths[name] = normalized
        resources = operation["sharedResources"]
        _require(isinstance(resources, list)
                 and all(isinstance(item, str) and item == item.strip()
                         and 0 < len(item) <= 256
                         for item in resources)
                 and len(resources) == len(set(resources)), "invalid shared resource footprint")
        _require(type(operation["footprintComplete"]) is bool, "footprintComplete must be boolean")
        identifier = operation["instanceId"]
        footprints[identifier] = {
            "reads": set(footprint_paths["reads"]),
            "writes": set(footprint_paths["writes"]),
            "sharedResources": set(resources),
            "footprintComplete": operation["footprintComplete"] and not has_wildcard,
        }
        m1_operations.append({
            "instanceId": identifier,
            "attemptId": operation["attemptId"],
            "source": source,
            "dependencies": dependencies,
            "uncertainPaths": [],
        })
    _require(len(ids) == len(set(ids)) and len(attempts) == len(set(attempts)),
             "duplicate operation or attempt ID")
    m1_request = {
        "gitAnalysisRequestVersion": "0.1.0-alpha",
        "repository": str(Path(value["repository"]).expanduser().resolve()),
        "baseRevision": value["baseRevision"],
        "operations": m1_operations,
    }
    try:
        from .git_replay import _validate_request
        _validate_request(m1_request)
    except InvalidGitReplay as exc:
        raise InvalidGitIntegrationPrototype(str(exc)) from exc
    return m1_request, footprints


def _waves(operations: list[dict], footprints: dict[str, dict]) -> list[list[str]]:
    by_id = {item["instanceId"]: item for item in operations}
    pending = set(by_id)
    completed: set[str] = set()
    waves: list[list[str]] = []
    while pending:
        ready = sorted(identifier for identifier in pending
                       if set(by_id[identifier]["dependencies"]) <= completed)
        _require(bool(ready), "dependency graph cannot make progress")
        wave: list[str] = []
        for identifier in ready:
            candidate = footprints[identifier]
            if not candidate["footprintComplete"]:
                continue
            conflict = False
            for member in wave:
                accepted = footprints[member]
                if (_path_sets_overlap(candidate["writes"], accepted["reads"] | accepted["writes"])
                        or _path_sets_overlap(accepted["writes"], candidate["reads"])
                        or candidate["sharedResources"] & accepted["sharedResources"]):
                    conflict = True
                    break
            if not conflict:
                wave.append(identifier)
        if not wave:
            # Unknown footprints never enter a candidate wave. A deterministic
            # singleton keeps the research result inspectable and serial.
            wave = [ready[0]]
        waves.append(wave)
        completed.update(wave)
        pending.difference_update(wave)
    return waves


def _path_sets_overlap(left: set[str], right: set[str]) -> bool:
    return any(first == second or first.startswith(second + "/")
               or second.startswith(first + "/") for first in left for second in right)


def _target_commit(repository: Path, target_ref: str, env: dict[str, str],
                   budget: GitCommandBudget) -> str:
    result = _git(repository, env, "rev-parse", "--verify", f"{target_ref}^{{commit}}",
                  budget=budget, allow_failure=True)
    if result.returncode != 0:
        return ""
    revision = result.stdout.decode("ascii", "strict").strip()
    return revision if OID.fullmatch(revision) else ""


def _new_worktree(scratch: Path, directory: Path, base: str,
                  env: dict[str, str], budget: GitCommandBudget) -> None:
    _git(scratch, env, "-c", "core.hooksPath=/dev/null", "worktree", "add",
         "--no-checkout", "--detach", str(directory), base, budget=budget)
    _git(directory, env, "read-tree", base, budget=budget)


def _prepare_one(worktree: Path, identifier: str, patch: bytes, source_tree: str,
                 env: dict[str, str], budget: GitCommandBudget) -> dict:
    started = time.perf_counter_ns()
    try:
        if patch:
            _git(worktree, env, "apply", "--cached",
                 "--binary", "--whitespace=nowarn", "-", budget=budget,
                 input_bytes=patch)
        tree = _git(worktree, env, "write-tree", budget=budget).stdout.decode().strip()
    except GitPatchRejected:
        return {
            "operationId": identifier, "status": "patch-rejected",
            "preparedTree": None, "sourceTree": source_tree,
            "matchesSourceTree": False,
            "elapsedNanoseconds": time.perf_counter_ns() - started,
        }
    if not OID.fullmatch(tree):
        raise InvalidGitIntegrationPrototype("Git returned an invalid prepared tree ID")
    return {
        "operationId": identifier,
        "status": "complete" if tree == source_tree else "tree-mismatch",
        "preparedTree": tree,
        "sourceTree": source_tree,
        "matchesSourceTree": tree == source_tree,
        "elapsedNanoseconds": time.perf_counter_ns() - started,
    }


def _operation_commit(worktree: Path, tree: str, base: str, identifier: str,
                      env: dict[str, str], budget: GitCommandBudget) -> str:
    message = f"agent-braid T013 fixture operation {identifier}\n".encode()
    result = _git(worktree, env, "commit-tree", tree, "-p", base, "-F", "-",
                  budget=budget, input_bytes=message)
    revision = result.stdout.decode("ascii", "strict").strip()
    _require(bool(OID.fullmatch(revision)), "Git returned an invalid fixture commit ID")
    return revision


def _integrate_lane(scratch: Path, base: str, order: list[str], operation_commits: dict[str, str],
                    operation_trees: dict[str, str], target_ref: str, source: Path, env: dict[str, str],
                    budget: GitCommandBudget) -> dict:
    current = base
    steps = []
    for identifier in order:
        observed_target = _target_commit(source, target_ref, env, budget)
        if observed_target != base:
            return {"status": "stale-base", "finalTree": None, "steps": steps,
                    "failure": "target-ref-changed-before-integration"}
        if not steps:
            # Every prepared tree was already checked against the source tree,
            # and its fixture commit has base as its parent. Merging that first
            # commit into base repeats a verified fast-forward and cannot find
            # an additional conflict.
            tree = operation_trees[identifier]
            commit = operation_commits[identifier]
            _require(bool(OID.fullmatch(tree) and OID.fullmatch(commit)),
                     "invalid verified first operation")
            steps.append({"operationId": identifier, "status": "merged",
                          "tree": tree, "temporaryCommit": commit})
            current = commit
            continue
        result = _git(scratch, env, "merge-tree", "--write-tree", current,
                      operation_commits[identifier], budget=budget, allow_failure=True)
        if result.returncode != 0:
            steps.append({"operationId": identifier, "status": "merge-conflict",
                          "exitCode": result.returncode})
            return {"status": "conflict", "finalTree": None, "steps": steps,
                    "failure": "merge-tree-reported-conflict"}
        tree = result.stdout.decode("ascii", "strict").splitlines()[0].strip()
        if not OID.fullmatch(tree):
            return {"status": "inconclusive", "finalTree": None, "steps": steps,
                    "failure": "merge-tree-returned-invalid-tree"}
        commit = _operation_commit(scratch, tree, base, "integration-" + identifier,
                                   env, budget)
        steps.append({"operationId": identifier, "status": "merged",
                      "tree": tree, "temporaryCommit": commit})
        current = commit
    final_tree = steps[-1]["tree"]
    return {"status": "complete", "finalTree": final_tree, "steps": steps,
            "failure": None}


def _resource_metrics(budget: GitCommandBudget) -> dict:
    budget._sample_child_usage()
    with budget.lock:
        return {
            "gitCommands": budget.commands,
            "capturedOutputBytes": budget.output_bytes,
            "gitChildUserCpuSeconds": round(budget.child_user_cpu_seconds, 6),
            "gitChildSystemCpuSeconds": round(budget.child_system_cpu_seconds, 6),
            "processPeakChildRssBytes": budget.peak_child_rss_bytes,
            "sampledPeakTemporaryDataBytes": budget.peak_scratch_bytes,
        }


def _usage_delta(after: dict, before: dict, field: str) -> float:
    return round(max(0.0, after[field] - before[field]), 6)


def _unstarted_report(status: str, base: str, target_ref: str, target_commit: str,
                      reason: str, expected_tree: str | None = None) -> dict:
    report = {
        "gitIntegrationPrototypeReportVersion": REPORT_VERSION,
        "status": status,
        "baseCommit": base,
        "targetRef": target_ref,
        "targetCommit": target_commit or None,
        "candidateWaves": [],
        "operationPreparations": [],
        "candidateIntegration": {"status": "not-run", "finalTree": None, "steps": [],
                                  "failure": reason},
        "serialReference": {"status": "not-run", "finalTree": None, "steps": [],
                            "failure": reason},
        "comparison": {"status": "not-run", "treesEqual": None},
        "declaredTrackedTreeCheck": {
            "status": "not-run" if expected_tree else "not-declared",
            "expectedTree": expected_tree,
        },
        "unsafeAdmissionCount": 0,
        "sourceTargetRefMatchesPinnedBaseAtFinalCheck": target_commit == base,
        "executionAuthorization": False,
        "promotionPerformed": False,
        "reason": reason,
    }
    report["reportDigest"] = _digest(report)
    return report


def run_prototype(request: object, *, cancel_event: threading.Event | None = None,
                  tree_consumer: Callable[[Path, str, str], None] | None = None,
                  benchmark_serial_first: bool = False) -> dict:
    """Prepare fixed Git patches concurrently in private worktrees and compare
    private merge results with a serial reference. Never update source refs.
    """
    _require(type(benchmark_serial_first) is bool, "invalid benchmark lane order")
    run_started = time.perf_counter_ns()
    m1_request, footprints = _validate_request(request)
    source = Path(m1_request["repository"])
    target_ref = request["targetRef"]
    expected_tree = request.get("expectedFinalTree")
    with tempfile.TemporaryDirectory(prefix="agent-braid-git-integration-") as directory:
        temp_root = Path(directory)
        env = _sanitized_environment(temp_root / "home")
        env.update({
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "safe.directory",
            "GIT_CONFIG_VALUE_0": str(source),
            "GIT_AUTHOR_NAME": "Agent Braid T013 fixture",
            "GIT_AUTHOR_EMAIL": "agent-braid-t013@example.invalid",
            "GIT_COMMITTER_NAME": "Agent Braid T013 fixture",
            "GIT_COMMITTER_EMAIL": "agent-braid-t013@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        })
        budget = GitCommandBudget(
            temp_root=temp_root,
            wall_seconds=MAX_WALL_SECONDS,
            max_commands=MAX_GIT_COMMANDS,
            max_output_bytes=MAX_OUTPUT_BYTES,
            max_command_output_bytes=MAX_COMMAND_OUTPUT_BYTES,
            max_scratch_bytes=MAX_SCRATCH_BYTES,
            max_process_address_space_bytes=MAX_PROCESS_ADDRESS_SPACE_BYTES,
            cancel_event=cancel_event,
        )
        checked_ref = _git(source, env, "check-ref-format", target_ref,
                           budget=budget, allow_failure=True)
        if checked_ref.returncode != 0:
            raise InvalidGitIntegrationPrototype("invalid target branch reference")
        base_before = _target_commit(source, target_ref, env, budget)
        if base_before != request["baseRevision"]:
            return _unstarted_report("stale-base", request["baseRevision"], target_ref,
                                     base_before, "target-ref-does-not-match-pinned-base",
                                     expected_tree)
        operation_ids = [item["instanceId"] for item in m1_request["operations"]]
        incomplete = [identifier for identifier in operation_ids
                      if not footprints[identifier]["footprintComplete"]]
        if incomplete:
            return _unstarted_report("manual-review", request["baseRevision"], target_ref,
                                     base_before, "incomplete-footprint:" + ",".join(incomplete),
                                     expected_tree)
        try:
            analysis, provenance = analyze_git_with_provenance(
                m1_request, env=env, budget=budget
            )
        except InvalidGitAnalysis as exc:
            raise InvalidGitIntegrationPrototype(str(exc)) from exc
        m1_request["baseRevision"] = provenance["baseCommit"]
        supported, reasons, changed_count = _supported_operations(provenance)
        if changed_count > MAX_CHANGED_PATHS:
            return _unstarted_report("manual-review", provenance["baseCommit"], target_ref,
                                     base_before, "changed-path-limit-exceeded", expected_tree)
        for operation in provenance["operations"]:
            identifier = operation["instanceId"]
            changed = {item["path"] for item in operation["changes"]}
            undeclared = changed - footprints[identifier]["writes"]
            if undeclared:
                return _unstarted_report("manual-review", provenance["baseCommit"], target_ref,
                                         base_before,
                                         "changed-paths-missing-from-write-footprint:" + identifier,
                                         expected_tree)
        patches = _patches(m1_request, provenance, env, budget)
        _mark_unsupported_binary_patches(provenance, patches, supported, reasons)
        if not all(supported.values()):
            unsupported = [f"{identifier}:{','.join(reasons[identifier])}"
                           for identifier in operation_ids if not supported[identifier]]
            return _unstarted_report("manual-review", provenance["baseCommit"], target_ref,
                                     base_before, "unsupported-fixture:" + ";".join(unsupported),
                                     expected_tree)
        patch_bytes = sum(len(patch) for patch in patches.values())
        if patch_bytes > MAX_PATCH_BYTES:
            return _unstarted_report("manual-review", provenance["baseCommit"], target_ref,
                                     base_before, "aggregate-patch-limit-exceeded", expected_tree)

        waves = _waves(m1_request["operations"], footprints)
        order = [identifier for wave in waves for identifier in wave]
        topological = _topological_orders(m1_request["operations"])
        _require(order in topological, "declared wave order violates dependencies")
        by_provenance = {item["instanceId"]: item for item in provenance["operations"]}
        source_trees = {
            identifier: _git(source, env, "rev-parse",
                             f"{by_provenance[identifier]['resolvedSource']}^{{tree}}",
                             budget=budget).stdout.decode().strip()
            for identifier in operation_ids
        }
        base = provenance["baseCommit"]
        base_tree = _git(source, env, "rev-parse", f"{base}^{{tree}}",
                         budget=budget).stdout.decode().strip()
        scratch = temp_root / "scratch.git"
        _git(temp_root, env, "init", "--bare", "--quiet", str(scratch), budget=budget)
        _git(scratch, env, "-c", "protocol.file.allow=always", "fetch", "--no-tags",
             "--no-recurse-submodules", "--depth=1", "--", str(source), base,
             budget=budget)

        lane_worktrees: dict[str, dict[str, Path]] = {"candidate": {}, "serial": {}}
        for lane in ("candidate", "serial"):
            for identifier in operation_ids:
                worktree = temp_root / lane / identifier
                _new_worktree(scratch, worktree, base, env, budget)
                lane_worktrees[lane][identifier] = worktree

        def prepare_candidate():
            prep_before = _resource_metrics(budget)
            start = time.perf_counter_ns()
            preparations: dict[str, dict] = {}
            for wave in waves:
                # Dependencies gate the next preparation wave. Every member
                # receives a private worktree and index.
                with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(wave))) as pool:
                    futures = {
                        identifier: pool.submit(
                            _prepare_one, lane_worktrees["candidate"][identifier], identifier,
                            patches[identifier], source_trees[identifier], env, budget
                        ) for identifier in wave
                    }
                    for identifier in wave:
                        preparations[identifier] = futures[identifier].result()
                if any(preparations[item]["status"] != "complete" for item in wave):
                    break
            for identifier in order:
                preparations.setdefault(identifier, {
                    "operationId": identifier, "status": "not-run",
                    "preparedTree": None, "sourceTree": source_trees[identifier],
                    "matchesSourceTree": False, "elapsedNanoseconds": 0,
                })
            prep_wall = time.perf_counter_ns() - start
            prep_usage = _resource_metrics(budget)
            bad = any(item["status"] != "complete" for item in preparations.values())
            commits: dict[str, str] = {}
            materialize_before = _resource_metrics(budget)
            materialize_start = time.perf_counter_ns()
            if not bad:
                commits = {
                    identifier: _operation_commit(
                        lane_worktrees["candidate"][identifier],
                        preparations[identifier]["preparedTree"], base,
                        identifier, env, budget
                    ) for identifier in operation_ids
                }
            materialize_wall = time.perf_counter_ns() - materialize_start
            materialize_usage = _resource_metrics(budget)
            return (preparations, bad, commits, prep_before, prep_wall, prep_usage,
                    materialize_before, materialize_wall, materialize_usage)

        def prepare_serial():
            prep_before = _resource_metrics(budget)
            start = time.perf_counter_ns()
            preparations = {
                identifier: _prepare_one(
                    lane_worktrees["serial"][identifier], identifier, patches[identifier],
                    source_trees[identifier], env, budget
                ) for identifier in order
            }
            prep_wall = time.perf_counter_ns() - start
            prep_usage = _resource_metrics(budget)
            bad = any(item["status"] != "complete" for item in preparations.values())
            commits: dict[str, str] = {}
            materialize_before = _resource_metrics(budget)
            materialize_start = time.perf_counter_ns()
            if not bad:
                commits = {
                    identifier: _operation_commit(
                        lane_worktrees["serial"][identifier],
                        preparations[identifier]["preparedTree"], base,
                        identifier, env, budget
                    ) for identifier in operation_ids
                }
            materialize_wall = time.perf_counter_ns() - materialize_start
            materialize_usage = _resource_metrics(budget)
            return (preparations, bad, commits, prep_before, prep_wall, prep_usage,
                    materialize_before, materialize_wall, materialize_usage)

        if benchmark_serial_first:
            (serial_preparations, serial_bad, serial_commits, serial_prep_before,
             serial_prep_wall, serial_prep_usage, serial_materialize_before,
             serial_materialize_wall, serial_materialize_usage) = prepare_serial()
            (candidate_preparations, candidate_bad, candidate_commits, candidate_prep_before,
             candidate_prep_wall, candidate_prep_usage, candidate_materialize_before,
             candidate_materialize_wall, candidate_materialize_usage) = prepare_candidate()
        else:
            (candidate_preparations, candidate_bad, candidate_commits, candidate_prep_before,
             candidate_prep_wall, candidate_prep_usage, candidate_materialize_before,
             candidate_materialize_wall, candidate_materialize_usage) = prepare_candidate()
            (serial_preparations, serial_bad, serial_commits, serial_prep_before,
             serial_prep_wall, serial_prep_usage, serial_materialize_before,
             serial_materialize_wall, serial_materialize_usage) = prepare_serial()

        target_after_prepare = _target_commit(source, target_ref, env, budget)
        if target_after_prepare != base:
            report = _unstarted_report("stale-base", base, target_ref, target_after_prepare,
                                       "target-ref-changed-after-preparation", expected_tree)
            report["candidateWaves"] = waves
            report["operationPreparations"] = list(candidate_preparations.values())
            report["analysisDigest"] = analysis["analysisId"]
            report["provenanceDigest"] = _digest(provenance)
            report["baseTree"] = base_tree
            report["resources"] = _resource_metrics(budget)
            report.pop("reportDigest", None)
            report["reportDigest"] = _digest(report)
            return report
        def integrate(commits: dict[str, str], bad: bool, lane: str):
            before = _resource_metrics(budget)
            start = time.perf_counter_ns()
            result = (
                _integrate_lane(scratch, base, order, commits, source_trees, target_ref,
                                source, env, budget)
                if not bad else
                {"status": "inconclusive", "finalTree": None, "steps": [],
                 "failure": lane + "-preparation-incomplete"}
            )
            return result, time.perf_counter_ns() - start, before, _resource_metrics(budget)

        if benchmark_serial_first:
            (serial_integration, serial_integrate_wall, serial_integrate_before,
             serial_integrate_usage) = integrate(serial_commits, serial_bad, "serial")
            (candidate_integration, candidate_integrate_wall, candidate_integrate_before,
             candidate_total_usage) = integrate(candidate_commits, candidate_bad, "candidate")
        else:
            (candidate_integration, candidate_integrate_wall, candidate_integrate_before,
             candidate_total_usage) = integrate(candidate_commits, candidate_bad, "candidate")
            (serial_integration, serial_integrate_wall, serial_integrate_before,
             serial_integrate_usage) = integrate(serial_commits, serial_bad, "serial")
        target_final = _target_commit(source, target_ref, env, budget)
        final_usage = _resource_metrics(budget)
        if target_final != base:
            candidate_integration = {"status": "stale-base", "finalTree": None,
                                     "steps": candidate_integration["steps"],
                                     "failure": "target-ref-changed-after-integration"}
            serial_integration = {"status": "stale-base", "finalTree": None,
                                  "steps": serial_integration["steps"],
                                  "failure": "target-ref-changed-after-integration"}
        equal = (
            candidate_integration["status"] == "complete"
            and serial_integration["status"] == "complete"
            and candidate_integration["finalTree"] == serial_integration["finalTree"]
        )
        comparison_status = (
            "match" if equal else
            "divergent" if (candidate_integration["status"] == "complete"
                            and serial_integration["status"] == "complete")
            else "inconclusive"
        )
        tree_check_status = (
            "not-declared" if expected_tree is None else
            "passed" if (comparison_status == "match"
                         and candidate_integration["finalTree"] == expected_tree) else
            "failed" if comparison_status == "match" else "not-run"
        )
        candidate_multi_waves = [wave for wave in waves if len(wave) > 1]
        unsafe_admissions = 0
        if candidate_bad or not equal or tree_check_status == "failed":
            unsafe_admissions = len(candidate_multi_waves)
        report = {
            "gitIntegrationPrototypeReportVersion": REPORT_VERSION,
            # A completed run is useful only when candidate and serial trees
            # agree. Divergence is a verification failure and must fail closed.
            "status": "completed" if comparison_status == "match"
            and tree_check_status in {"passed", "not-declared"} else "inconclusive",
            "repositoryId": provenance["repositoryId"],
            "baseCommit": base,
            "baseTree": base_tree,
            "targetRef": target_ref,
            "targetCommit": target_after_prepare,
            "targetCommitAtFinalCheck": target_final,
            "analysisDigest": analysis["analysisId"],
            "provenanceDigest": _digest(provenance),
            "observationContract": "private-tracked-tree-v1",
            "footprintContract": "declared-static-read-write-and-shared-resource-v1",
            "footprintsDynamicallyObserved": False,
            "operationOrder": order,
            "operationDeclarations": [
                {
                    "operationId": identifier,
                    "attemptId": operation["attemptId"],
                    "sourceCommit": by_provenance[identifier]["resolvedSource"],
                    "dependencies": sorted(operation["dependencies"]),
                    "reads": sorted(footprints[identifier]["reads"]),
                    "writes": sorted(footprints[identifier]["writes"]),
                    "sharedResources": sorted(footprints[identifier]["sharedResources"]),
                    "footprintComplete": footprints[identifier]["footprintComplete"],
                    "patchDigest": "sha256:" + hashlib.sha256(patches[identifier]).hexdigest(),
                    "actualChangedPaths": sorted(
                        item["path"] for item in by_provenance[identifier]["changes"]
                    ),
                }
                for identifier, operation in zip(operation_ids, m1_request["operations"], strict=True)
            ],
            "candidateWaves": waves,
            "operationPreparations": [candidate_preparations[key] for key in order],
            "serialPreparations": [serial_preparations[key] for key in order],
            "candidateIntegration": candidate_integration,
            "serialReference": serial_integration,
            "comparison": {"status": comparison_status, "treesEqual": equal
                           if comparison_status != "inconclusive" else None},
            "declaredTrackedTreeCheck": {
                "status": tree_check_status,
                "expectedTree": expected_tree,
            },
            "unsafeAdmissionCount": unsafe_admissions,
            "metrics": {
                "wallNanoseconds": time.perf_counter_ns() - run_started,
                "candidatePreparationWallNanoseconds": candidate_prep_wall,
                "serialPreparationWallNanoseconds": serial_prep_wall,
                "candidateOperationCommitMaterializationWallNanoseconds": candidate_materialize_wall,
                "serialOperationCommitMaterializationWallNanoseconds": serial_materialize_wall,
                "candidateIntegrationWallNanoseconds": candidate_integrate_wall,
                "serialIntegrationWallNanoseconds": serial_integrate_wall,
                "candidateTotalWallNanoseconds": candidate_prep_wall + candidate_materialize_wall + candidate_integrate_wall,
                "serialTotalWallNanoseconds": serial_prep_wall + serial_materialize_wall + serial_integrate_wall,
                "candidatePreparationGitUserCpuSeconds": _usage_delta(
                    candidate_prep_usage, candidate_prep_before, "gitChildUserCpuSeconds"),
                "serialPreparationGitUserCpuSeconds": _usage_delta(
                    serial_prep_usage, serial_prep_before, "gitChildUserCpuSeconds"),
                "candidateCommitMaterializationGitUserCpuSeconds": _usage_delta(
                    candidate_materialize_usage, candidate_materialize_before,
                    "gitChildUserCpuSeconds"),
                "serialCommitMaterializationGitUserCpuSeconds": _usage_delta(
                    serial_materialize_usage, serial_materialize_before,
                    "gitChildUserCpuSeconds"),
                "candidatePreparationGitCommands": candidate_prep_usage["gitCommands"] - candidate_prep_before["gitCommands"],
                "serialPreparationGitCommands": serial_prep_usage["gitCommands"] - serial_prep_before["gitCommands"],
                "candidateCommitMaterializationGitCommands": candidate_materialize_usage["gitCommands"] - candidate_materialize_before["gitCommands"],
                "serialCommitMaterializationGitCommands": serial_materialize_usage["gitCommands"] - serial_materialize_before["gitCommands"],
                "candidateIntegrationGitCommands": candidate_total_usage["gitCommands"] - candidate_integrate_before["gitCommands"],
                "serialIntegrationGitCommands": serial_integrate_usage["gitCommands"] - serial_integrate_before["gitCommands"],
                "candidateTotalGitCommands": (
                    candidate_prep_usage["gitCommands"] - candidate_prep_before["gitCommands"]
                    + candidate_materialize_usage["gitCommands"] - candidate_materialize_before["gitCommands"]
                    + candidate_total_usage["gitCommands"] - candidate_integrate_before["gitCommands"]
                ),
                "serialTotalGitCommands": (
                    serial_prep_usage["gitCommands"] - serial_prep_before["gitCommands"]
                    + serial_materialize_usage["gitCommands"] - serial_materialize_before["gitCommands"]
                    + serial_integrate_usage["gitCommands"] - serial_integrate_before["gitCommands"]
                ),
                "candidateIntegrationGitUserCpuSeconds": _usage_delta(
                    candidate_total_usage, candidate_integrate_before, "gitChildUserCpuSeconds"),
                "serialIntegrationGitUserCpuSeconds": _usage_delta(
                    serial_integrate_usage, serial_integrate_before, "gitChildUserCpuSeconds"),
                "capturedOutputBytes": final_usage["capturedOutputBytes"],
                "gitChildUserCpuSeconds": final_usage["gitChildUserCpuSeconds"],
                "gitChildSystemCpuSeconds": final_usage["gitChildSystemCpuSeconds"],
                "processPeakChildRssBytes": final_usage["processPeakChildRssBytes"],
                "processPeakChildRssScope": "process-lifetime peak; standalone CLI starts a fresh process",
                "sampledPeakTemporaryDataBytes": final_usage["sampledPeakTemporaryDataBytes"],
            },
            "resourceLimits": {
                "operations": MAX_OPERATIONS,
                "changedPaths": MAX_CHANGED_PATHS,
                "aggregatePatchBytes": MAX_PATCH_BYTES,
                "concurrentGitWorkers": MAX_WORKERS,
                "wallSeconds": MAX_WALL_SECONDS,
                "gitCommands": MAX_GIT_COMMANDS,
                "capturedOutputBytes": MAX_OUTPUT_BYTES,
                "perCommandOutputBytes": MAX_COMMAND_OUTPUT_BYTES,
                "temporaryDataBytes": MAX_SCRATCH_BYTES,
                "temporaryDataPollMilliseconds": int(POLL_INTERVAL_SECONDS * 1000),
                "addressSpaceBytesPerGitChild": MAX_PROCESS_ADDRESS_SPACE_BYTES,
            },
            "sourceTargetRefMatchesPinnedBaseAtFinalCheck": target_final == base,
            "executionAuthorization": False,
            "promotionPerformed": False,
            "limits": [
                "Runs allowlisted Git plumbing only; no repository commands, tests, hooks, agents, network effects, or ref promotion.",
                "Operation footprints are declared inputs and are not dynamically observed because repository code is never run.",
                "Serial and candidate tree agreement covers this fixture protocol only; it does not establish semantic safety or production concurrency.",
                "Temporary data is sampled every 50 ms; an in-flight write may overshoot before termination.",
                "Each Git child is capped at 512 MiB address space; peak RSS is reported from the process child-usage counter.",
                "The target ref is sampled at defined phase boundaries; a transient move and restore between samples may go undetected.",
                "Patch preparation can run concurrently; candidate tree integration remains serial in this prototype.",
            ],
        }
        report["reportDigest"] = _digest(report)
        if tree_consumer is not None and report["status"] == "completed":
            # The scratch object store disappears on return. A caller may
            # export both verified trees while it is still private and live.
            tree_consumer(scratch, candidate_integration["finalTree"],
                          serial_integration["finalTree"])
        return report
