# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded replay of immutable Git patches with advisory planning only."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import tempfile

from .analysis import _canonical, _digest
from .git_adapter import InvalidGitAnalysis, analyze_git_with_provenance
from .git_process import (
    GitCommandBudget,
    GitCommandFailure,
    GitInfrastructureFailure,
    run_git,
)


EVIDENCE_VERSION = "0.1.0-alpha"
PLAN_VERSION = "0.1.0-alpha"
OBSERVATION = "tracked-tree-v1"
EXECUTION = "isolated-index-patch-v1"
MAX_OPERATIONS = 4
MAX_PATHS = 64
MAX_PATCH_BYTES = 1_048_576
MAX_GIT_OUTPUT = 8 * 1024 * 1024
MAX_REPLAY_OUTPUT = 16 * 1024 * 1024
MAX_REPLAY_SCRATCH = 64 * 1024 * 1024
MAX_REPLAY_SECONDS = 120
MAX_GIT_COMMANDS = 512
GIT_TIMEOUT_SECONDS = 30
OID = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")


class InvalidGitReplay(ValueError):
    """A request is invalid or outside the bounded Git replay contract."""


class GitPatchRejected(RuntimeError):
    """A patch is incompatible with the current replay tree."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidGitReplay(message)


def _sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _sanitized_environment(home: Path) -> dict[str, str]:
    """Build a bounded Git environment without inheriting config or remotes."""
    home.mkdir(parents=True, exist_ok=True)
    return_env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "TMPDIR": str(home),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_PROTOCOL_FROM_USER": "0",
    }
    return return_env


def _git(repo: Path, env: dict[str, str], *args: str,
         budget: GitCommandBudget, input_bytes: bytes | None = None,
         allow_failure: bool = False) -> bytes:
    try:
        process = run_git(repo, args, env=env, budget=budget, input_bytes=input_bytes,
                          allow_failure=allow_failure,
                          command_timeout=GIT_TIMEOUT_SECONDS)
    except GitCommandFailure as exc:
        if args and args[0] == "apply":
            raise GitPatchRejected("fixed patch was rejected by git apply") from exc
        raise InvalidGitReplay("Git command failed: " + (args[0] if args else "unknown")) from exc
    return process.stdout


def _validate_request(value: object) -> dict:
    _require(isinstance(value, dict), "Git replay request must be an object")
    required = {"gitAnalysisRequestVersion", "repository", "baseRevision", "operations"}
    _require(set(value) == required, "invalid Git replay request fields")
    _require(value["gitAnalysisRequestVersion"] == "0.1.0-alpha",
             "unsupported Git analysis request version")
    _require(isinstance(value["repository"], str) and value["repository"].strip(),
             "invalid repository")
    _require(isinstance(value["baseRevision"], str) and value["baseRevision"].strip(),
             "invalid base revision")
    operations = value["operations"]
    _require(isinstance(operations, list) and 2 <= len(operations) <= MAX_OPERATIONS,
             "Git replay requires 2–4 operations")
    identifiers: list[str] = []
    attempts: list[str] = []
    for operation in operations:
        _require(isinstance(operation, dict), "Git operations must be objects")
        expected = {"instanceId", "attemptId", "source", "dependencies", "uncertainPaths"}
        _require(set(operation) == expected, "invalid Git operation fields")
        for field in ("instanceId", "attemptId"):
            _require(isinstance(operation[field], str) and 0 < len(operation[field]) <= 256,
                     f"invalid {field}")
        identifiers.append(operation["instanceId"])
        attempts.append(operation["attemptId"])
        source = operation["source"]
        _require(isinstance(source, dict) and set(source) == {"kind", "revision"}
                 and source.get("kind") == "commit"
                 and isinstance(source.get("revision"), str) and source["revision"].strip(),
                 "Git replay accepts commit sources only")
        dependencies = operation["dependencies"]
        uncertain = operation["uncertainPaths"]
        _require(isinstance(dependencies, list)
                 and all(isinstance(item, str) and item for item in dependencies)
                 and len(set(dependencies)) == len(dependencies), "invalid dependencies")
        _require(isinstance(uncertain, list)
                 and all(isinstance(item, str) and item for item in uncertain)
                 and len(set(uncertain)) == len(uncertain), "invalid uncertain paths")
    _require(len(set(identifiers)) == len(identifiers), "duplicate operation ID")
    _require(len(set(attempts)) == len(attempts), "duplicate attempt ID")
    known = set(identifiers)
    _require(all(set(operation["dependencies"]) <= known for operation in operations),
             "unknown operation dependency")
    _topological_orders(operations)
    return value


def _topological_orders(operations: list[dict]) -> list[list[str]]:
    identifiers = sorted(operation["instanceId"] for operation in operations)
    dependencies = {operation["instanceId"]: set(operation["dependencies"])
                    for operation in operations}
    orders = [list(order) for order in itertools.permutations(identifiers)
              if all(order.index(dep) < order.index(identifier)
                     for identifier, deps in dependencies.items() for dep in deps)]
    _require(bool(orders), "cyclic operation dependencies")
    return orders


def _hash_digest(value: object) -> str:
    return _digest(value)


def _normalized_request(evidence: dict) -> dict:
    return {
        "gitAnalysisRequestVersion": "0.1.0-alpha",
        "repository": evidence["repositoryPath"],
        "baseRevision": evidence["baseCommit"],
        "operations": [
            {
                "instanceId": operation["instanceId"],
                "attemptId": operation["attemptId"],
                "source": {"kind": "commit", "revision": operation["sourceCommit"]},
                "dependencies": operation["dependencies"],
                "uncertainPaths": operation["uncertainPaths"],
            }
            for operation in evidence["operations"]
        ],
    }


def _supported_operations(provenance: dict) -> tuple[dict[str, bool], dict[str, list[str]], int]:
    supported: dict[str, bool] = {}
    reasons: dict[str, list[str]] = {}
    path_count = 0
    for operation in provenance["operations"]:
        identifier = operation["instanceId"]
        changes = operation["changes"]
        path_count += len(changes)
        why: list[str] = []
        if operation["uncertainPaths"]:
            why.append("declared-uncertain-path")
        if any(change["status"] not in {"A", "M"} for change in changes):
            why.append("unsupported-git-change-kind")
        reasons[identifier] = why
        supported[identifier] = not why
    return supported, reasons, path_count


def _mark_unsupported_binary_patches(
    provenance: dict, patches: dict[str, bytes],
    supported: dict[str, bool], reasons: dict[str, list[str]],
) -> None:
    """Keep Git binary patches replayable as evidence but never plan them."""
    for operation in provenance["operations"]:
        identifier = operation["instanceId"]
        patch = patches[identifier]
        if b"GIT binary patch\n" in patch or b"Binary files " in patch:
            supported[identifier] = False
            reasons[identifier].append("binary-patch")


def _patches(request: dict, provenance: dict, env: dict[str, str],
             budget: GitCommandBudget) -> dict[str, bytes]:
    root = Path(request["repository"]).expanduser().resolve()
    patches: dict[str, bytes] = {}
    aggregate = 0
    for item in provenance["operations"]:
        patch = _git(root, env, "diff", "--binary", "--no-ext-diff", "--no-textconv",
                     "--no-renames", request["baseRevision"], item["resolvedSource"], "--",
                     budget=budget)
        expected = item["snapshot"]
        _require(expected == "sha256:" + hashlib.sha256(patch).hexdigest(),
                 "patch bytes do not match read-only Git provenance")
        aggregate += len(patch)
        _require(aggregate <= MAX_PATCH_BYTES, "aggregate patch bytes exceed 1 MiB")
        patches[item["instanceId"]] = patch
    return patches


def _tree(repo: Path, env: dict[str, str], budget: GitCommandBudget) -> str:
    tree = _git(repo, env, "write-tree", budget=budget).decode().strip()
    _require(bool(OID.fullmatch(tree)), "unexpected Git tree object ID")
    return tree


def _replay_all(request: dict, provenance: dict, patches: dict[str, bytes],
                source_env: dict[str, str], temp_root: Path,
                budget: GitCommandBudget) -> list[dict]:
    return _replay_orders(request, provenance, patches, source_env, temp_root,
                          budget, _topological_orders(request["operations"]))


def _replay_orders(request: dict, provenance: dict, patches: dict[str, bytes],
                   source_env: dict[str, str], temp_root: Path,
                   budget: GitCommandBudget, orders: list[list[str]]) -> list[dict]:
    """Replay caller-selected orders privately; public evidence still uses all orders."""
    root = Path(request["repository"]).expanduser().resolve()
    scratch = temp_root / "scratch.git"
    _git(temp_root, source_env, "init", "--bare", "--quiet", str(scratch), budget=budget)
    scratch_env = dict(source_env)
    scratch_env["GIT_CONFIG_GLOBAL"] = os.devnull
    _git(scratch, scratch_env, "-c", "protocol.file.allow=always", "fetch",
         "--no-tags", "--no-recurse-submodules", "--depth=1", "--", str(root),
         provenance["baseCommit"],
         *[operation["resolvedSource"] for operation in provenance["operations"]],
         budget=budget)
    base_tree = _git(scratch, scratch_env, "rev-parse",
                     f"{provenance['baseCommit']}^{{tree}}", budget=budget).decode().strip()
    _require(bool(OID.fullmatch(base_tree)), "unexpected base tree ID")

    result: list[dict] = []
    for index, order in enumerate(orders):
        index_path = temp_root / f"schedule-{index}.index"
        schedule_env = dict(scratch_env)
        schedule_env["GIT_INDEX_FILE"] = str(index_path)
        _git(scratch, schedule_env, "read-tree", provenance["baseCommit"], budget=budget)
        steps = []
        failed = False
        for identifier in order:
            before = _tree(scratch, schedule_env, budget)
            patch = patches[identifier]
            if patch:
                try:
                    _git(scratch, schedule_env, "apply", "--cached", "--binary",
                         "--whitespace=nowarn", "-", input_bytes=patch, budget=budget)
                except GitPatchRejected:
                    steps.append({"operationId": identifier, "inputTree": before,
                                  "outputTree": None, "status": "patch-rejected"})
                    failed = True
                    break
            after = _tree(scratch, schedule_env, budget)
            steps.append({"operationId": identifier, "inputTree": before,
                          "outputTree": after, "status": "applied"})
        if failed:
            result.append({"order": order, "status": "incomplete", "steps": steps,
                           "finalTree": None, "failure": "patch-rejected"})
        else:
            final_tree = _tree(scratch, schedule_env, budget)
            result.append({"order": order, "status": "complete", "steps": steps,
                           "finalTree": final_tree, "failure": None})
        try:
            index_path.unlink(missing_ok=True)
        except OSError:
            pass
    return result


def _tracked_tree_observation(schedule: dict) -> str | None:
    """Return the tracked-tree-v1 observation for a complete replay schedule.

    An incomplete schedule has no successful observation. A malformed internal
    schedule must not be mistaken for a successful, equivalent observation.
    """
    _require(isinstance(schedule, dict), "invalid internal schedule")
    _require({"status", "finalTree"} <= schedule.keys(),
             "internal schedule lacks observation fields")
    status = schedule.get("status")
    final_tree = schedule.get("finalTree")
    if status == "incomplete":
        _require(final_tree is None, "incomplete schedule has a final tree")
        return None
    _require(status == "complete", "invalid internal schedule status")
    _require(isinstance(final_tree, str) and bool(OID.fullmatch(final_tree)),
             "complete schedule has no valid tracked tree")
    return final_tree


def _result(schedules: list[dict]) -> str:
    _require(bool(schedules), "no replay schedules")
    observations = [_tracked_tree_observation(schedule) for schedule in schedules]
    if any(observation is None for observation in observations):
        return "inconclusive"
    return ("equivalent-observed" if len(set(observations)) == 1 else "divergent")


def _bundle_digest(bundle: dict) -> str:
    payload = dict(bundle)
    payload.pop("evidenceDigest", None)
    return _hash_digest(payload)


def _build_evidence(request: dict, *, order_selector=None) -> dict:
    _validate_request(request)
    source_root = Path(request["repository"]).expanduser().resolve()
    normalized = deepcopy(request)
    normalized["repository"] = str(source_root)
    normalized["operations"] = sorted(
        normalized["operations"], key=lambda item: item["instanceId"]
    )
    for operation in normalized["operations"]:
        operation["dependencies"] = sorted(operation["dependencies"])
        operation["uncertainPaths"] = sorted(operation["uncertainPaths"])
    with tempfile.TemporaryDirectory(prefix="agent-braid-git-replay-") as directory:
        temp_root = Path(directory)
        env = dict(_sanitized_environment(temp_root / "home"))
        budget = GitCommandBudget(
            temp_root=temp_root,
            wall_seconds=MAX_REPLAY_SECONDS,
            max_commands=MAX_GIT_COMMANDS,
            max_output_bytes=MAX_REPLAY_OUTPUT,
            max_command_output_bytes=MAX_GIT_OUTPUT,
            max_scratch_bytes=MAX_REPLAY_SCRATCH,
        )
        try:
            # M1 remains the authority for request normalization and Git provenance.
            # Its subprocesses receive this request's sanitized environment and
            # shared end-to-end budget directly; process-global state is untouched.
            report, provenance = analyze_git_with_provenance(
                normalized, env=env, budget=budget
            )

            normalized["baseRevision"] = provenance["baseCommit"]
            supported, reasons, path_count = _supported_operations(provenance)
            _require(path_count <= MAX_PATHS, "changed path count exceeds 64")
            patches = _patches(normalized, provenance, env, budget)
            _mark_unsupported_binary_patches(provenance, patches, supported, reasons)
            if order_selector is None:
                schedules = _replay_all(normalized, provenance, patches, env,
                                        temp_root, budget)
            else:
                # The partial bundle is private experiment data, never a public
                # replay evidence record or an input to the public verifier.
                orders = order_selector(normalized, provenance, patches, supported)
                schedules = _replay_orders(normalized, provenance, patches, env,
                                           temp_root, budget, orders)
            operations = []
            resolved_by_id = {item["instanceId"]: item for item in provenance["operations"]}
            for operation in normalized["operations"]:
                observed = resolved_by_id[operation["instanceId"]]
                operations.append({
                    "instanceId": operation["instanceId"],
                    "attemptId": operation["attemptId"],
                    "sourceCommit": observed["resolvedSource"],
                    "dependencies": sorted(operation["dependencies"]),
                    "uncertainPaths": sorted(operation["uncertainPaths"]),
                    "patchDigest": _sha256(patches[operation["instanceId"]]),
                    "eligible": supported[operation["instanceId"]],
                    "ineligibleReasons": reasons[operation["instanceId"]],
                })
            bundle = {
                "gitReplayEvidenceVersion": EVIDENCE_VERSION,
                "repositoryId": provenance["repositoryId"],
                "baseCommit": provenance["baseCommit"],
                "baseTree": _git(source_root, env, "rev-parse",
                                  f"{provenance['baseCommit']}^{{tree}}",
                                  budget=budget).decode().strip(),
                "operations": operations,
                "analysisDigest": report["analysisId"],
                "provenanceDigest": _hash_digest(provenance),
                "observationContract": OBSERVATION,
                "executionContract": EXECUTION,
                "schedules": schedules,
                "result": _result(schedules),
                "limits": [
                    "Fixed commit patches and the declared dependency graph only.",
                    "Tracked paths, modes and blob identities only; no project tests or semantic effects.",
                    "End-to-end Git execution is limited to 120 seconds, 512 commands, 16 MiB output and 64 MiB temporary data.",
                    "Finite observation does not authorize concurrency or establish task correctness.",
                ],
                "executionAuthorization": False,
            }
            bundle["evidenceDigest"] = _bundle_digest(bundle)
            return bundle
        except InvalidGitAnalysis as exc:
            raise InvalidGitReplay(str(exc)) from exc


def _plan(bundle: dict, verification: dict) -> dict:
    operations = bundle["operations"]
    by_id = {item["instanceId"]: item for item in operations}
    conditions = ["Fixed commit patches only; revalidate the same base and commit IDs before use.",
                  "Integration is serial; the plan is advisory preparation guidance."]
    all_eligible = all(item["eligible"] for item in operations)
    candidate = (
        verification.get("status") == "verified"
        and bundle["result"] == "equivalent-observed"
        and all(schedule["status"] == "complete" for schedule in bundle["schedules"])
        and all_eligible
    )
    if candidate:
        pending = {identifier: set(item["dependencies"]) for identifier, item in by_id.items()}
        waves: list[list[str]] = []
        completed: set[str] = set()
        while len(completed) < len(operations):
            ready = sorted(identifier for identifier, deps in pending.items()
                           if identifier not in completed and deps <= completed)
            if not ready:
                raise InvalidGitReplay("cyclic dependency graph while planning")
            waves.append(ready)
            completed.update(ready)
        mode = "candidate-preparation-waves"
        order = [identifier for wave in waves for identifier in wave]
    elif verification.get("status") != "verified":
        # Unverified schedule records are not a basis even for the serial fallback.
        mode = "manual-review"
        order = None
        waves = []
        conditions.append("Evidence did not verify against the supplied repository; review is required.")
    else:
        # Select the lexicographically first admissible order independent of input order.
        lex_order = min((schedule["order"] for schedule in bundle["schedules"]), default=[])
        canonical = next((schedule for schedule in bundle["schedules"]
                          if schedule["order"] == lex_order), None)
        if canonical and canonical["status"] == "complete":
            mode = "serial-fallback"
            order = lex_order
            waves = [[identifier] for identifier in order]
        else:
            mode = "manual-review"
            order = None
            waves = []
        conditions.append("Unknown, unsupported, divergent or incomplete evidence prevents candidate waves.")
    plan = {
        "gitPlanVersion": PLAN_VERSION,
        "evidenceDigest": bundle["evidenceDigest"],
        "verificationStatus": verification.get("status", "rejected"),
        "replayResult": bundle["result"],
        "mode": mode,
        "waves": waves,
        "fallbackOrder": order,
        "conditions": conditions,
        "executionAuthorization": False,
        "limits": bundle["limits"],
    }
    plan["planDigest"] = _hash_digest(plan)
    return plan


def _plan_digest(plan: dict) -> str:
    payload = dict(plan)
    payload.pop("planDigest", None)
    return _hash_digest(payload)


def _validate_plan_shape(value: object) -> dict:
    _require(isinstance(value, dict), "plan must be an object")
    required = {
        "gitPlanVersion", "evidenceDigest", "verificationStatus", "replayResult",
        "mode", "waves", "fallbackOrder", "conditions", "executionAuthorization",
        "limits", "planDigest",
    }
    _require(set(value) == required, "invalid plan fields")
    _require(value["gitPlanVersion"] == PLAN_VERSION, "unsupported plan version")
    for field in ("evidenceDigest", "planDigest"):
        _require(isinstance(value[field], str) and bool(SHA256.fullmatch(value[field])),
                 f"invalid plan {field}")
    _require(value["verificationStatus"] in {"verified", "unverified", "rejected"},
             "invalid plan verification status")
    _require(value["replayResult"] in {"equivalent-observed", "divergent", "inconclusive"},
             "invalid plan replay result")
    _require(value["mode"] in {"candidate-preparation-waves", "serial-fallback", "manual-review"},
             "invalid plan mode")
    _require(value["executionAuthorization"] is False,
             "a Git plan cannot authorize execution")
    _require(isinstance(value["waves"], list)
             and all(isinstance(wave, list) and wave
                     and all(isinstance(item, str) and item for item in wave)
                     for wave in value["waves"]), "invalid plan waves")
    order = value["fallbackOrder"]
    _require(order is None or isinstance(order, list)
             and all(isinstance(item, str) and item for item in order),
             "invalid plan fallback order")
    _require(isinstance(value["conditions"], list) and value["conditions"]
             and all(isinstance(item, str) and item for item in value["conditions"]),
             "invalid plan conditions")
    _require(isinstance(value["limits"], list)
             and all(isinstance(item, str) and item for item in value["limits"]),
             "invalid plan limits")
    _require(value["planDigest"] == _plan_digest(value), "plan digest mismatch")
    return value


def produce(request: object) -> tuple[dict, dict]:
    """Return an evidence bundle and plan after producer-side replay checking."""
    bundle = _build_evidence(request)
    verification = verify(bundle, request["repository"])
    if verification.get("status") not in {"verified", "unverified"}:
        raise InvalidGitReplay("producer replay evidence did not verify")
    return bundle, _plan(bundle, verification)


def _validate_bundle_shape(bundle: object) -> dict:
    _require(isinstance(bundle, dict), "evidence bundle must be an object")
    required = {
        "gitReplayEvidenceVersion", "evidenceDigest", "repositoryId", "baseCommit", "baseTree",
        "operations", "analysisDigest", "provenanceDigest", "observationContract",
        "executionContract", "schedules", "result", "limits", "executionAuthorization",
    }
    _require(set(bundle) == required, "invalid evidence bundle fields")
    _require(bundle["gitReplayEvidenceVersion"] == EVIDENCE_VERSION, "unsupported evidence version")
    for field in ("repositoryId", "analysisDigest", "provenanceDigest", "evidenceDigest"):
        _require(isinstance(bundle[field], str) and bool(SHA256.fullmatch(bundle[field])),
                 f"invalid {field}")
    for field in ("baseCommit", "baseTree"):
        _require(isinstance(bundle[field], str) and bool(OID.fullmatch(bundle[field])),
                 f"invalid {field}")
    _require(bundle["observationContract"] == OBSERVATION
             and bundle["executionContract"] == EXECUTION, "unsupported replay contract")
    _require(bundle["executionAuthorization"] is False, "evidence cannot authorize execution")
    _require(bundle["result"] in {"equivalent-observed", "divergent", "inconclusive"},
             "invalid replay result")
    _require(isinstance(bundle["operations"], list)
             and 2 <= len(bundle["operations"]) <= MAX_OPERATIONS, "invalid operation list")
    ids: list[str] = []
    for operation in bundle["operations"]:
        _require(isinstance(operation, dict) and set(operation) == {
            "instanceId", "attemptId", "sourceCommit", "dependencies", "uncertainPaths",
            "patchDigest", "eligible", "ineligibleReasons",
        }, "invalid evidence operation")
        _require(isinstance(operation["instanceId"], str) and operation["instanceId"],
                 "invalid evidence operation ID")
        ids.append(operation["instanceId"])
        _require(isinstance(operation["attemptId"], str) and operation["attemptId"],
                 "invalid evidence attempt ID")
        _require(isinstance(operation["sourceCommit"], str)
                 and bool(OID.fullmatch(operation["sourceCommit"])), "invalid source commit")
        _require(isinstance(operation["dependencies"], list)
                 and all(isinstance(dep, str) for dep in operation["dependencies"]),
                 "invalid evidence dependencies")
        _require(isinstance(operation["uncertainPaths"], list)
                 and all(isinstance(path, str) for path in operation["uncertainPaths"]),
                 "invalid evidence uncertainty")
        _require(isinstance(operation["patchDigest"], str)
                 and bool(SHA256.fullmatch(operation["patchDigest"])), "invalid patch digest")
        _require(type(operation["eligible"]) is bool, "invalid eligibility")
        _require(isinstance(operation["ineligibleReasons"], list)
                 and all(isinstance(reason, str) for reason in operation["ineligibleReasons"]),
                 "invalid ineligibility reasons")
    _require(len(set(ids)) == len(ids), "duplicate evidence operation ID")
    known = set(ids)
    _require(all(set(item["dependencies"]) <= known for item in bundle["operations"]),
             "unknown evidence dependency")
    schedules = bundle["schedules"]
    _require(isinstance(schedules, list) and 1 <= len(schedules) <= 24,
             "invalid schedule list")
    seen = set()
    for schedule in schedules:
        _require(isinstance(schedule, dict) and set(schedule) == {
            "order", "status", "steps", "finalTree", "failure",
        }, "invalid schedule record")
        _require(isinstance(schedule["order"], list)
                 and set(schedule["order"]) == known
                 and len(schedule["order"]) == len(known), "invalid schedule order")
        _require(tuple(schedule["order"]) not in seen, "duplicate schedule order")
        seen.add(tuple(schedule["order"]))
        _require(schedule["status"] in {"complete", "incomplete"}, "invalid schedule status")
        _require(isinstance(schedule["steps"], list), "invalid schedule steps")
        _require(schedule["finalTree"] is None or
                 isinstance(schedule["finalTree"], str) and bool(OID.fullmatch(schedule["finalTree"])),
                 "invalid final tree")
        _require(schedule["failure"] is None or isinstance(schedule["failure"], str),
                 "invalid schedule failure")
    _require(isinstance(bundle["limits"], list)
             and all(isinstance(limit, str) for limit in bundle["limits"]), "invalid limits")
    return bundle


def verify(bundle: object, repository: str) -> dict:
    """Reconstruct and independently replay a Git evidence bundle."""
    try:
        _validate_bundle_shape(bundle)
        _require(isinstance(repository, str) and repository.strip(), "invalid repository path")
        if bundle["evidenceDigest"] != _bundle_digest(bundle):
            return {"status": "rejected", "reason": "evidence digest mismatch"}
        request = _normalized_request({**bundle, "repositoryPath": repository})
        computed = _build_evidence(request)
        if computed != bundle:
            return {"status": "rejected", "reason": "replayed evidence mismatch"}
        return {
            "status": "verified",
            "reason": "all bounded Git schedules were independently replayed; no execution authorization",
            "checkedClaim": {
                "property": "tracked-tree-equivalence",
                "method": "exhaustive-finite-replay",
                "domain": "repository:" + bundle["repositoryId"] + ":base:" + bundle["baseCommit"],
                "result": bundle["result"],
                "schedulesChecked": len(bundle["schedules"]),
            },
        }
    except InvalidGitReplay as exc:
        text = str(exc)
        status = "unverified" if any(token in text.lower() for token in
                                      ("unavailable", "not found", "could not be started")) else "rejected"
        return {"status": status, "reason": text}
    except GitInfrastructureFailure as exc:
        return {"status": "unverified", "category": exc.category, "reason": str(exc)}
    except (KeyError, TypeError, ValueError, OSError, RecursionError) as exc:
        return {"status": "rejected", "reason": str(exc)}


def plan(bundle: object, repository: str) -> dict:
    """Create an advisory plan only after this repository independently verifies it."""
    try:
        _validate_bundle_shape(bundle)
        verification = verify(bundle, repository)
        return _plan(bundle, verification)
    except (InvalidGitReplay, KeyError, TypeError, ValueError) as exc:
        raise InvalidGitReplay(str(exc)) from exc


def verify_plan(plan_value: object, bundle: object, repository: str) -> dict:
    """Accept a plan only when it is the deterministic plan for verified evidence."""
    try:
        candidate = _validate_plan_shape(plan_value)
        _validate_bundle_shape(bundle)
        verification = verify(bundle, repository)
        if verification.get("status") != "verified":
            return {
                "status": verification.get("status", "rejected"),
                "category": verification.get("category"),
                "reason": "plan evidence is not verified: " + verification.get("reason", "unknown"),
            }
        expected = _plan(bundle, verification)
        if candidate != expected:
            return {"status": "rejected", "reason": "plan does not match the regenerated evidence plan"}
        return {
            "status": "verified",
            "reason": "plan digest and all fields match independently replayed evidence",
            "checkedClaim": {
                "property": "plan-evidence-consistency",
                "evidenceDigest": candidate["evidenceDigest"],
                "mode": candidate["mode"],
                "executionAuthorization": False,
            },
        }
    except (InvalidGitReplay, KeyError, TypeError, ValueError, RecursionError) as exc:
        return {"status": "rejected", "reason": str(exc)}
