# SPDX-License-Identifier: AGPL-3.0-only
"""Strict, non-executing SPEC-038 source and schedule preparation.

This module admits only the exact frozen public source frame and approved
protocol. It prepares verified static replay/runtime plans; it never issues
grants, allocates persistent runs, or authorizes registered capture.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from . import git_replay, git_runtime, runtime_policy
from .git_adapter import analyze_git_with_provenance

ROOT = Path(__file__).resolve().parents[1]
BASE = "f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6"
COMMITS = {
    "m2-observation-normalizer": "58351f812614058e53a8ee6aef1dd458f1bb70fc",
    "m2-counterexample-reducer": "083f1a390988a9527a5aaeb19133401243b1d714",
}
SEED = ("SPEC-038-v1|seed=380038|base=" + BASE + "|a=" + COMMITS["m2-observation-normalizer"]
        + "|b=" + COMMITS["m2-counterexample-reducer"])
SEED_SHA256 = "9a99f698a3b13f59329a5dee14fcc8af0e610cd8f1b2f3a6ad8d6dffaffbef8c"
RECEIPT_RELATIVE = "specs/038-m4-real-workload-closure/protocol-review-packet.md"
RIGHTS_RELATIVE = "specs/038-m4-real-workload-closure/source-rights-manifest.json"
APPROVED_SOURCE_RIGHTS_SHA256 = "8f1707b2ae5fc66b5ed5e45fa21d70b9e02a1765ec51c242db96c11bd1e1766d"
APPROVED_PROTOCOL_SHA256 = "656f0b67958e6cf0857bcf3a2908b8235eb2ea43a9a44a8ae18e1c6905790fd2"
APPROVAL_RECEIPT_SHA256 = "160441f088d148210fda174775fc5705fd0e319ccd1ad3b448e2a35cdf96db2f"
PREPARATION_INPUTS = (
    "agent_braid/m4_real_workload.py", "scripts/prepare_m4_real_workload.py",
    "agent_braid/git_replay.py", "agent_braid/git_runtime.py", "agent_braid/runtime_policy.py",
    "agent_braid/runtime_scheduler.py", "agent_braid/git_adapter.py", "agent_braid/git_process.py",
    "agent_braid/m4_real_workload_trials.py", "scripts/measure_m4_real_workload.py",
    "scripts/verify_m4_real_workload.py",
    "tests/test_m4_real_workload_preparation.py", "tests/test_m4_real_workload_trials.py",
    "schemas/0.1.0-alpha/git-runtime-request.schema.json",
    "schemas/0.1.0-alpha/runtime-policy.schema.json", RIGHTS_RELATIVE, RECEIPT_RELATIVE,
    "specs/013-m2-real-workload/m2-corpus-selection.json",
)
PAIR_ROWS = (
    ("W-AB-1", "warmup", "AB", 1, "serial"),
    ("W-AB-2", "warmup", "AB", 2, "parallel"),
    ("W-BA-1", "warmup", "BA", 3, "serial"),
    ("W-BA-2", "warmup", "BA", 4, "parallel"),
    ("M-AB-2", "measured", "AB", 5, "serial"),
    ("M-BA-2", "measured", "BA", 6, "parallel"),
    ("M-BA-3", "measured", "BA", 7, "serial"),
    ("M-AB-1", "measured", "AB", 8, "parallel"),
    ("M-AB-3", "measured", "AB", 9, "serial"),
    ("M-BA-1", "measured", "BA", 10, "parallel"),
)
OID = re.compile(r"^[0-9a-f]{40}$")
HEX256 = re.compile(r"^[0-9a-f]{64}$")


class InvalidRealWorkload(ValueError):
    """Malformed, stale, unsupported, or unauthorized preparation input."""


def _safe_git_environment() -> dict[str, str]:
    """Keep ambient Git configuration from changing source inspection semantics."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_LITERAL_PATHSPECS": "1",
        "GIT_ALLOW_PROTOCOL": "file",
        "GIT_PROTOCOL_FROM_USER": "0",
        "GIT_CONFIG_COUNT": "2",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_CONFIG_KEY_1": "core.hooksPath",
        "GIT_CONFIG_VALUE_1": "/dev/null",
    })
    return env


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _json(raw: bytes, label: str) -> dict:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InvalidRealWorkload(f"invalid {label} JSON") from exc
    if type(value) is not dict:
        raise InvalidRealWorkload(f"{label} must be an object")
    return value


def _git_bytes(repository: Path, *args: str) -> bytes:
    try:
        command = ["git", "--no-replace-objects", "-C", str(repository),
                   "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null"]
        if args and args[0] in {"diff", "show"}:
            command.extend((args[0], "--no-ext-diff", "--no-textconv", *args[1:]))
        else:
            command.extend(args)
        return subprocess.check_output(command, stderr=subprocess.PIPE, timeout=30,
                                       env=_safe_git_environment())
    except (OSError, subprocess.SubprocessError, UnicodeError) as exc:
        raise InvalidRealWorkload("cannot inspect frozen source repository") from exc


def _git(repository: Path, *args: str) -> str:
    try:
        return _git_bytes(repository, *args).decode().strip()
    except UnicodeError as exc:
        raise InvalidRealWorkload("cannot inspect frozen source repository") from exc


def source_fingerprint(repository: Path) -> dict:
    """Bind the local source checkout, relevant refs, index and tracked tree."""
    root = repository.expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / ".git").exists():
        raise InvalidRealWorkload("source must be an existing Git worktree")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise InvalidRealWorkload("source repository must be clean")
    return {
        "repository": str(root), "head": _git(root, "rev-parse", "HEAD"),
        "tree": _git(root, "rev-parse", "HEAD^{tree}"),
        "indexSha256": _sha((root / _git(root, "rev-parse", "--git-path", "index")).read_bytes()),
        "commonDirectory": str((root / _git(root, "rev-parse", "--git-common-dir")).resolve(strict=True)),
        "refsSha256": _sha(_git(root, "for-each-ref", "--format=%(refname) %(objectname)").encode()),
        "status": "clean",
    }


def _candidate_state() -> dict:
    if _git(ROOT, "status", "--porcelain=v1", "--untracked-files=all"):
        raise InvalidRealWorkload("preparation requires a clean candidate commit")
    hashes = {}
    for name in PREPARATION_INPUTS:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            raise InvalidRealWorkload("missing or unsafe candidate input: " + name)
        hashes[name] = _sha(path.read_bytes())
    if hashes[RIGHTS_RELATIVE] != APPROVED_SOURCE_RIGHTS_SHA256:
        raise InvalidRealWorkload("approved source-rights candidate bytes differ")
    if hashes[RECEIPT_RELATIVE] != APPROVED_PROTOCOL_SHA256:
        raise InvalidRealWorkload("approved protocol candidate bytes differ")
    return {"candidateCommit": _git(ROOT, "rev-parse", "HEAD"), "candidateInputs": hashes}


def _harness_input_hashes() -> dict[str, str]:
    result = {}
    for name in PREPARATION_INPUTS:
        path = ROOT / name
        if path.is_file() and not path.is_symlink():
            result[name] = _sha(path.read_bytes())
    return result


def _approved_receipt(path: Path) -> dict:
    try:
        raw = path.expanduser().resolve(strict=True).read_bytes()
    except OSError as exc:
        raise InvalidRealWorkload("exact external source/protocol approval receipt is required") from exc
    receipt = _json(raw, "approval receipt")
    if _sha(raw) != APPROVAL_RECEIPT_SHA256:
        raise InvalidRealWorkload("exact approved source/protocol receipt bytes differ")
    expected = {
        "recordVersion": "m4-exact-source-protocol-decision-v1",
        "decision": "approved-implementation-and-evaluation-preparation-only",
        "repository": "jayanez/agent-braid", "baseCommit": BASE,
        "sourceRightsCandidateSha256": APPROVED_SOURCE_RIGHTS_SHA256,
        "protocolCandidateSha256": APPROVED_PROTOCOL_SHA256,
        "implementationAuthorized": True, "evaluationPreparationAuthorized": True,
        "registeredCaptureAuthorized": False, "m4Acceptance": False,
    }
    if any(receipt.get(key) != value for key, value in expected.items()):
        raise InvalidRealWorkload("approval receipt does not authorize this exact preparation scope")
    source_rows = receipt.get("sources")
    if source_rows != [{"pullRequest": 137, "commit": COMMITS["m2-observation-normalizer"]},
                       {"pullRequest": 138, "commit": COMMITS["m2-counterexample-reducer"]}]:
        raise InvalidRealWorkload("approval receipt source identities differ")
    return {"sha256": _sha(raw), "decision": receipt["decision"],
            "registeredCaptureAuthorized": False, "m4Acceptance": False}


def _order_id(order: str) -> list[str]:
    identifiers = list(COMMITS)
    return identifiers if order == "AB" else list(reversed(identifiers))


def _runtime_request(repository: str, order: str, expected_tree: str) -> dict:
    ids = _order_id(order)
    return {
        "gitRuntimeRequestVersion": git_runtime.VERSION,
        "repository": repository, "baseRevision": BASE,
        "operations": [
            {"instanceId": identifier, "attemptId": "spec038-v1-" + identifier,
             "source": {"kind": "commit", "revision": COMMITS[identifier]},
             "dependencies": [], "uncertainPaths": [], "declaredWrites": []}
            for identifier in sorted(COMMITS)
        ],
        "order": ids, "expectedFinalTree": expected_tree,
    }


def _slots(root: Path) -> list[dict]:
    result = []
    for pair_id, kind, order, dispatch, first_mode in PAIR_ROWS:
        for treatment_order, mode in enumerate((first_mode, "parallel" if first_mode == "serial" else "serial")):
            slot_id = f"{pair_id}-{mode}"
            treatment = root.parent / (root.name + "-" + slot_id)
            result.append({"slotId": slot_id, "pairId": pair_id, "pairKind": kind,
                           "operationOrder": order, "globalPairDispatch": dispatch,
                           "treatmentOrder": treatment_order, "mode": mode,
                           "runPath": str(treatment),
                           "grantPath": str(treatment) + ".grants"})
    return result


def _assert_fresh_slots(slots: list[dict]) -> None:
    for slot in slots:
        if os.path.lexists(slot["runPath"]) or os.path.lexists(slot["grantPath"]):
            raise InvalidRealWorkload("all treatment destinations must be fresh before preparation")


def _validate_slot_set(slots: object) -> None:
    if type(slots) is not list or len(slots) != 20:
        raise InvalidRealWorkload("manifest must retain exactly 20 treatment slots")
    expected = _slots(Path("/spec038-placeholder"))
    for actual, want in zip(slots, expected):
        expected_keys = {"slotId", "pairId", "pairKind", "operationOrder", "globalPairDispatch",
                         "treatmentOrder", "mode", "runPath", "grantPath"}
        if type(actual) is not dict or set(actual) != expected_keys:
            raise InvalidRealWorkload("invalid treatment slot fields")
        for key in ("slotId", "pairId", "pairKind", "operationOrder", "globalPairDispatch", "treatmentOrder", "mode"):
            if actual.get(key) != want[key]:
                raise InvalidRealWorkload("treatment slot identity or schedule differs")
        for key in ("runPath", "grantPath"):
            raw = actual.get(key)
            if type(raw) is not str or not Path(raw).is_absolute():
                raise InvalidRealWorkload("treatment path must be absolute")
        run_path, grant_path = Path(actual["runPath"]), Path(actual["grantPath"])
        if run_path.parent != grant_path.parent or actual["grantPath"] != actual["runPath"] + ".grants":
            raise InvalidRealWorkload("run and grant destinations must be exact private siblings")
    if len({row.get("runPath") for row in slots}) != 20 or len({row.get("grantPath") for row in slots}) != 20:
        raise InvalidRealWorkload("treatment run and grant paths must be unique")


def _validate_private_destinations(slots: list[dict], source_repository: str,
                                   source_common: str) -> None:
    """Reject aliases and destinations within either checkout or Git storage."""
    try:
        source_path = Path(source_repository)
        common_path = Path(source_common)
        source_root = source_path.resolve(strict=True)
        source_common_root = common_path.resolve(strict=True)
        candidate_root = ROOT.resolve(strict=True)
    except OSError as exc:
        raise InvalidRealWorkload("protected source and candidate roots must exist") from exc
    if source_path != source_root or common_path != source_common_root:
        raise InvalidRealWorkload("source identity paths must be canonical and alias-free")
    protected = [source_root, source_common_root, candidate_root]
    for slot in slots:
        for key in ("runPath", "grantPath"):
            raw = Path(slot[key])
            canonical = raw.resolve(strict=False)
            if raw != canonical:
                raise InvalidRealWorkload("private treatment paths must not use symlink or path aliases")
            if any(canonical.is_relative_to(root) for root in protected):
                raise InvalidRealWorkload("private destination is inside source or candidate checkout")
            for ancestor in (canonical.parent, *canonical.parent.parents):
                if (os.path.lexists(ancestor / ".git")
                        or ((ancestor / "HEAD").is_file()
                            and (ancestor / "objects").is_dir()
                            and (ancestor / "refs").is_dir())):
                    raise InvalidRealWorkload("private destination is inside source or candidate Git storage")


def validate_manifest(raw: bytes) -> dict:
    """Validate canonical prepared-manifest bytes and return their object."""
    if type(raw) is not bytes or len(raw) > 1_048_576:
        raise InvalidRealWorkload("manifest must be bounded bytes")
    value = _json(raw, "prepared manifest")
    if _canonical(value) + b"\n" != raw:
        raise InvalidRealWorkload("prepared manifest is not canonical JSON")
    required = {"version", "candidateCommit", "candidateInputs", "harnessInputHashes",
                "sourceRepository", "sourceFingerprint", "sourceRightsApproval",
                "protocolApproval", "captureAuthorization", "m4Acceptance",
                "seed", "seedSha256", "operations", "expectedFinalTrees", "expectedStepTrees", "slots",
                "dispatchBudgetMinutes", "treatmentDeadlineSeconds", "runtimeCaps",
                "exclusions", "runtimeInputs", "replayInputs"}
    if set(value) != required or value["version"] != "spec038-real-workload-preparation-v1":
        raise InvalidRealWorkload("prepared manifest fields or version differ")
    if value["captureAuthorization"] is not False or value["m4Acceptance"] is not False:
        raise InvalidRealWorkload("preparation cannot authorize capture or M4 acceptance")
    if value["seed"] != SEED or value["seedSha256"] != SEED_SHA256:
        raise InvalidRealWorkload("frozen schedule seed differs")
    if value["dispatchBudgetMinutes"] != 45 or value["treatmentDeadlineSeconds"] != 360:
        raise InvalidRealWorkload("frozen observation budgets differ")
    if type(value["sourceRepository"]) is not str or not Path(value["sourceRepository"]).is_absolute():
        raise InvalidRealWorkload("source repository path must be absolute")
    if type(value["sourceRepository"]) is not str or not Path(value["sourceRepository"]).is_absolute():
        raise InvalidRealWorkload("source repository path must be absolute")
    _validate_slot_set(value["slots"])
    if type(value["operations"]) is not list or len(value["operations"]) != 2 or any(type(row) is not dict for row in value["operations"]):
        raise InvalidRealWorkload("manifest must retain both exact source candidates")
    if {row.get("operationId") for row in value["operations"]} != set(COMMITS):
        raise InvalidRealWorkload("source substitution or omission is forbidden")
    if {row.get("sourceCommit") for row in value["operations"]} != set(COMMITS.values()):
        raise InvalidRealWorkload("source commit identity differs")
    operation_ids = {row["operationId"] for row in value["operations"]}
    if operation_ids != set(COMMITS):
        raise InvalidRealWorkload("operation identity differs")
    for row in value["operations"]:
        if set(row) != {"operationId", "sourceCommit", "changedPaths", "changedBytes", "dependencies",
                        "paths", "patchSha256", "tree", "blobTransitions"}:
            raise InvalidRealWorkload("invalid source operation inventory fields")
        if (type(row["changedPaths"]) is not int or type(row["changedBytes"]) is not int
                or row["changedPaths"] != len(row["paths"]) or row["changedBytes"] < 0
                or type(row["paths"]) is not list or row["paths"] != sorted(set(row["paths"]))
                or type(row["dependencies"]) is not list or row["dependencies"] != []
                or type(row["patchSha256"]) is not str
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", row["patchSha256"])
                or type(row["tree"]) is not str or not OID.fullmatch(row["tree"])
                or type(row["blobTransitions"]) is not list or len(row["blobTransitions"]) != row["changedPaths"]):
            raise InvalidRealWorkload("invalid source operation identity or patch inventory")
        try:
            checked_paths = [git_runtime._path(path) for path in row["paths"]]
        except git_runtime.InvalidGitRuntime as exc:
            raise InvalidRealWorkload("unsafe source operation path") from exc
        if checked_paths != row["paths"]:
            raise InvalidRealWorkload("source operation paths are not canonical")
        transitions = row["blobTransitions"]
        if any(type(item) is not dict or set(item) != {"path", "status", "beforeMode", "afterMode", "beforeBlob", "afterBlob"}
               for item in transitions):
            raise InvalidRealWorkload("invalid static Git blob/mode transition inventory")
        if ([item["path"] for item in transitions] != row["paths"]
                or any(item["status"] not in {"A", "M"}
                       or item["beforeMode"] not in {"000000", "100644", "100755"}
                       or item["afterMode"] not in {"100644", "100755"}
                       or type(item["beforeBlob"]) is not str or not OID.fullmatch(item["beforeBlob"])
                       or type(item["afterBlob"]) is not str or not OID.fullmatch(item["afterBlob"])
                       for item in transitions)):
            raise InvalidRealWorkload("unsupported or malformed static Git blob/mode transition")
    if (sum(row["changedPaths"] for row in value["operations"]) > git_runtime.LIMITS["changedPaths"]
            or sum(row["changedBytes"] for row in value["operations"]) > git_runtime.LIMITS["patchBytes"]):
        raise InvalidRealWorkload("source frame exceeds current fixed-patch caps")
    if (sum(row["changedPaths"] for row in value["operations"]) > git_runtime.LIMITS["changedPaths"]
            or sum(row["changedBytes"] for row in value["operations"]) > git_runtime.LIMITS["patchBytes"]):
        raise InvalidRealWorkload("source frame exceeds current fixed-patch caps")
    if (type(value["harnessInputHashes"]) is not dict or not value["harnessInputHashes"]
            or any(type(name) is not str or type(digest) is not str or not HEX256.fullmatch(digest)
                   for name, digest in value["harnessInputHashes"].items())):
        raise InvalidRealWorkload("harness input hashes are incomplete or malformed")
    if type(value["candidateCommit"]) is not str or not OID.fullmatch(value["candidateCommit"]):
        raise InvalidRealWorkload("candidate commit is not immutable")
    if (type(value["candidateInputs"]) is not dict or not value["candidateInputs"]
            or any(type(name) is not str or type(digest) is not str or not HEX256.fullmatch(digest)
                   for name, digest in value["candidateInputs"].items())):
        raise InvalidRealWorkload("candidate input hashes are malformed")
    if set(value["candidateInputs"]) != set(PREPARATION_INPUTS) or value["candidateInputs"] != value["harnessInputHashes"]:
        raise InvalidRealWorkload("candidate and harness input inventories differ")
    fingerprint = value["sourceFingerprint"]
    if (type(fingerprint) is not dict or set(fingerprint) != {"repository", "head", "tree", "indexSha256",
                                                              "commonDirectory", "refsSha256", "status"}
            or fingerprint["repository"] != value["sourceRepository"]
            or type(fingerprint["head"]) is not str or not OID.fullmatch(fingerprint["head"])
            or type(fingerprint["tree"]) is not str or not OID.fullmatch(fingerprint["tree"])
            or type(fingerprint["commonDirectory"]) is not str or not Path(fingerprint["commonDirectory"]).is_absolute()
            or type(fingerprint["refsSha256"]) is not str or not HEX256.fullmatch(fingerprint["refsSha256"])
            or type(fingerprint["indexSha256"]) is not str or not HEX256.fullmatch(fingerprint["indexSha256"])
            or fingerprint["status"] != "clean"):
        raise InvalidRealWorkload("source fingerprint is malformed")
    caps = {"operations": 4, "changedPaths": 16, "patchBytes": 262144,
            "wallSeconds": 60, "gitCommands": 256, "outputBytes": 8388608,
            "commandOutputBytes": 2097152, "scratchBytes": 67108864,
            "workers": 4, "sourcePromotion": False}
    if value["runtimeCaps"] != caps or value["exclusions"] != []:
        raise InvalidRealWorkload("runtime caps or frozen source exclusions differ")
    if (type(value["sourceRightsApproval"]) is not dict
            or set(value["sourceRightsApproval"]) != {"record", "candidateSha256", "receiptSha256", "scope"}
            or type(value["protocolApproval"]) is not dict
            or set(value["protocolApproval"]) != {"candidateSha256", "receiptSha256"}
            or value["sourceRightsApproval"].get("record") != "external exact approval receipt"
            or value["sourceRightsApproval"].get("scope") != "local-preparation-and-evaluation-preparation"
            or value["sourceRightsApproval"].get("candidateSha256") != APPROVED_SOURCE_RIGHTS_SHA256
            or value["protocolApproval"].get("candidateSha256") != APPROVED_PROTOCOL_SHA256
            or value["sourceRightsApproval"].get("receiptSha256") != APPROVAL_RECEIPT_SHA256
            or value["protocolApproval"].get("receiptSha256") != APPROVAL_RECEIPT_SHA256
            or value["sourceRightsApproval"].get("receiptSha256") != value["protocolApproval"].get("receiptSha256")):
        raise InvalidRealWorkload("approval bindings differ from exact source/protocol decision")
    if type(value["expectedFinalTrees"]) is not dict or set(value["expectedFinalTrees"]) != {"AB", "BA"}:
        raise InvalidRealWorkload("both legal serial orders must be admitted")
    for tree in value["expectedFinalTrees"].values():
        if type(tree) is not str or not OID.fullmatch(tree):
            raise InvalidRealWorkload("invalid expected final tree")
    if type(value["expectedStepTrees"]) is not dict or set(value["expectedStepTrees"]) != {"AB", "BA"}:
        raise InvalidRealWorkload("both legal per-step tree sequences must be frozen")
    for order, rows in value["expectedStepTrees"].items():
        if type(rows) is not list or len(rows) != 2:
            raise InvalidRealWorkload("invalid per-step tree sequence")
        for index, row in enumerate(rows):
            if (type(row) is not dict or set(row) != {"operationId", "inputTree", "outputTree"}
                    or row["operationId"] != _order_id(order)[index]
                    or type(row["inputTree"]) is not str or not OID.fullmatch(row["inputTree"])
                    or type(row["outputTree"]) is not str or not OID.fullmatch(row["outputTree"])):
                raise InvalidRealWorkload("malformed frozen per-step tree identity")
        if rows[-1]["outputTree"] != value["expectedFinalTrees"][order]:
            raise InvalidRealWorkload("per-step and final tracked trees differ")
    if (type(value["runtimeInputs"]) is not dict or type(value["replayInputs"]) is not dict
            or set(value["runtimeInputs"]) != {"AB", "BA"} or set(value["replayInputs"]) != {"AB", "BA"}):
        raise InvalidRealWorkload("manifest must bind request inputs for both orders")
    for order in ("AB", "BA"):
        runtime = value["runtimeInputs"][order]
        replay = value["replayInputs"][order]
        try:
            git_runtime._request(runtime)
            git_replay._validate_request(replay)
        except (git_runtime.InvalidGitRuntime, git_replay.InvalidGitReplay, TypeError, KeyError) as exc:
            raise InvalidRealWorkload("manifest contains an invalid immutable runtime/replay request") from exc
        if runtime["repository"] != value["sourceRepository"] or replay["repository"] != value["sourceRepository"]:
            raise InvalidRealWorkload("request repository differs from frozen source repository")
        if runtime["baseRevision"] != BASE or replay["baseRevision"] != BASE:
            raise InvalidRealWorkload("request base differs from exact frozen base")
        if runtime["expectedFinalTree"] != value["expectedFinalTrees"][order] or runtime["order"] != _order_id(order):
            raise InvalidRealWorkload("runtime request differs from frozen order/tree")
        runtime_ops = {row["instanceId"]: row for row in runtime["operations"]}
        replay_ops = {row["instanceId"]: row for row in replay["operations"]}
        if set(runtime_ops) != set(COMMITS) or set(replay_ops) != set(COMMITS):
            raise InvalidRealWorkload("request operation frame differs from exact source candidates")
        for operation in value["operations"]:
            identifier = operation["operationId"]
            runtime_op, replay_op = runtime_ops[identifier], replay_ops[identifier]
            if (runtime_op["source"]["revision"] != operation["sourceCommit"]
                    or runtime_op["declaredWrites"] != operation["paths"]
                    or replay_op["source"]["revision"] != operation["sourceCommit"]
                    or runtime_op["dependencies"] != operation["dependencies"]
                    or replay_op["dependencies"] != operation["dependencies"]):
                raise InvalidRealWorkload("request operation identity/effects differ from frozen inventory")
    _validate_private_destinations(value["slots"], value["sourceRepository"],
                                   value["sourceFingerprint"]["commonDirectory"])
    paths = [slot[k] for slot in value["slots"] for k in ("runPath", "grantPath")]
    if len(paths) != len(set(paths)):
        raise InvalidRealWorkload("private destinations overlap")
    for slot in value["slots"]:
        source = Path(value["sourceRepository"])
        common = Path(value["sourceFingerprint"]["commonDirectory"])
        run, grant = Path(slot["runPath"]), Path(slot["grantPath"])
        if (run.is_relative_to(source) or grant.is_relative_to(source)
                or run.is_relative_to(common) or grant.is_relative_to(common)):
            raise InvalidRealWorkload("private destination is inside source")
        if (str(run) != os.path.normpath(str(run)) or str(grant) != os.path.normpath(str(grant))
                or run == grant or run.is_relative_to(grant) or grant.is_relative_to(run)):
            raise InvalidRealWorkload("private treatment paths are noncanonical or overlap")
    value["manifestSha256"] = _sha(raw)
    return value


def runtime_inputs_for_slot(manifest: dict, slot: dict) -> dict:
    """Return immutable request inputs for an already-authorized slot consumer."""
    payload = dict(manifest)
    payload.pop("manifestSha256", None)
    raw = _canonical(payload) + b"\n"
    checked = validate_manifest(raw)
    selected = next((item for item in checked["slots"] if item["slotId"] == slot.get("slotId")), None)
    if selected != slot:
        raise InvalidRealWorkload("slot is not bound to this manifest")
    order = selected["operationOrder"]
    return {"runtimeRequest": deepcopy(checked["runtimeInputs"][order]),
            "replayRequest": deepcopy(checked["replayInputs"][order]),
            "expectedFinalTree": checked["expectedFinalTrees"][order]}


def prepare_workload(repository: Path, destination_root: Path, approval_receipt: Path) -> bytes:
    """Run static admission/preparation only and return canonical review bytes.

    Both outputs are descriptions of future private paths. This function never
    creates those paths, grants, fixtures, or treatment results.
    """
    candidate = _candidate_state()
    approval = _approved_receipt(approval_receipt)
    source = repository.expanduser().resolve(strict=True)
    fingerprint_before = source_fingerprint(source)
    root = destination_root.expanduser().absolute()
    if root.exists() or root.is_symlink() or not root.parent.resolve(strict=True).is_dir():
        raise InvalidRealWorkload("destination root must be a fresh path with an existing parent")
    root = root.parent.resolve(strict=True) / root.name
    if root.is_relative_to(source) or root.is_relative_to(Path(fingerprint_before["commonDirectory"])):
        raise InvalidRealWorkload("destination root overlaps source Git storage")
    slots = _slots(root)
    _assert_fresh_slots(slots)

    replay_requests = {}
    runtime_requests = {}
    trees = {}
    step_trees = {}
    operation_rows = []
    blob_transitions = {}
    for identifier, commit in COMMITS.items():
        if _git(source, "cat-file", "-t", commit) != "commit":
            raise InvalidRealWorkload("exact frozen source commit is absent")
        if _git(source, "cat-file", "-t", BASE) != "commit":
            raise InvalidRealWorkload("exact frozen base commit is absent")
    analysis_request = {
        "gitAnalysisRequestVersion": git_replay.EVIDENCE_VERSION,
        "repository": str(source), "baseRevision": BASE,
        "operations": [{"instanceId": identifier, "attemptId": "spec038-v1-" + identifier,
                        "source": {"kind": "commit", "revision": commit},
                        "dependencies": [], "uncertainPaths": []}
                       for identifier, commit in sorted(COMMITS.items())],
    }
    evidence, advisory = git_replay.produce(analysis_request)
    verified = git_replay.verify_plan(advisory, evidence, str(source))
    if verified.get("status") != "verified" or advisory.get("executionAuthorization") is not False:
        raise InvalidRealWorkload("existing independent replay verifier did not admit candidate")
    _report, provenance = analyze_git_with_provenance(
        analysis_request, env=_safe_git_environment())
    provenance_by_operation = {row["instanceId"]: row for row in provenance["operations"]}
    replay_by_operation = {row["instanceId"]: row for row in evidence["operations"]}
    paths_by_operation = {identifier: sorted(change["path"] for change in provenance_by_operation[identifier]["changes"])
                          for identifier in COMMITS}
    for order in ("AB", "BA"):
        schedule = next((row for row in evidence.get("schedules", []) if row.get("order") == _order_id(order)), None)
        if schedule is None or schedule.get("status") != "complete" or not OID.fullmatch(schedule.get("finalTree", "")):
            raise InvalidRealWorkload("frozen source order is infeasible under existing replay contract")
        trees[order] = schedule["finalTree"]
        runtime_requests[order] = _runtime_request(str(source), order, trees[order])
        for operation in runtime_requests[order]["operations"]:
            operation["declaredWrites"] = paths_by_operation[operation["instanceId"]]
        replay_requests[order] = analysis_request
        # Admission recomputes fixed-patch provenance, path/mode/effect rules,
        # limits and expected tree; no persistent run or operator grant exists.
        expected_slots = [row for row in _slots(root)
                          if row["operationOrder"] == order and row["mode"] == "serial"]
        expected_slots += [row for row in _slots(root)
                           if row["operationOrder"] == order and row["mode"] == "parallel"]
        for slot in expected_slots:
            policy = runtime_policy.prepare_policy_run(
                runtime_requests[order], slot["runPath"], replay_evidence=evidence,
                advisory_plan=advisory, mode=slot["mode"])
            if policy["runtimeManifest"]["request"]["expectedFinalTree"] != trees[order]:
                raise InvalidRealWorkload("runtime admission tree differs from replay observation")
            for step in policy["runtimeManifest"]["steps"]:
                identifier = step["operationId"]
                frozen_effect = step["effects"]
                if identifier in blob_transitions and blob_transitions[identifier] != frozen_effect:
                    raise InvalidRealWorkload("operation path/blob/mode identity changes across approved order/mode")
                blob_transitions[identifier] = frozen_effect
            observed_steps = [{"operationId": step["operationId"], "inputTree": step["inputTree"],
                               "outputTree": step["outputTree"]}
                              for step in policy["runtimeManifest"]["steps"]]
            if order in step_trees and step_trees[order] != observed_steps:
                raise InvalidRealWorkload("per-step tree identities change across coordinator mode")
            step_trees[order] = observed_steps
        if not operation_rows:
            for op_id, commit in COMMITS.items():
                patch = _git_bytes(source, "diff", "--binary", "--no-renames", BASE, commit, "--")
                row = provenance_by_operation[op_id]
                if "sha256:" + _sha(patch) != replay_by_operation[op_id]["patchDigest"]:
                    raise InvalidRealWorkload("fixed patch bytes differ from independently prepared evidence")
                operation_rows.append({"operationId": op_id, "sourceCommit": commit,
                                       "changedPaths": len(row["changes"]),
                                       "changedBytes": len(patch),
                                       "dependencies": [],
                                       "paths": sorted(change["path"] for change in row["changes"]),
                                       "patchSha256": replay_by_operation[op_id]["patchDigest"],
                                       "tree": _git(source, "rev-parse", commit + "^{tree}"),
                                       "blobTransitions": blob_transitions[op_id]})
    fingerprint_after = source_fingerprint(source)
    if fingerprint_after != fingerprint_before:
        raise InvalidRealWorkload("source checkout changed during static preparation")
    if _candidate_state() != candidate:
        raise InvalidRealWorkload("candidate changed during static preparation")
    harness_inputs = _harness_input_hashes()
    if len(harness_inputs) != len(PREPARATION_INPUTS):
        raise InvalidRealWorkload("one or more exact harness identity inputs are missing")
    payload = {
        "version": "spec038-real-workload-preparation-v1", "candidateCommit": candidate["candidateCommit"],
        "candidateInputs": candidate["candidateInputs"], "harnessInputHashes": harness_inputs,
        "sourceRepository": str(source),
        "sourceFingerprint": fingerprint_before,
        "sourceRightsApproval": {"record": "external exact approval receipt",
                                 "candidateSha256": APPROVED_SOURCE_RIGHTS_SHA256,
                                 "receiptSha256": approval["sha256"], "scope": "local-preparation-and-evaluation-preparation"},
        "protocolApproval": {"candidateSha256": APPROVED_PROTOCOL_SHA256,
                             "receiptSha256": approval["sha256"]},
        "captureAuthorization": False, "m4Acceptance": False,
        "seed": SEED, "seedSha256": SEED_SHA256,
        "operations": operation_rows, "expectedFinalTrees": trees,
        "expectedStepTrees": step_trees, "slots": slots,
        "dispatchBudgetMinutes": 45, "treatmentDeadlineSeconds": 360,
        "runtimeCaps": {"operations": 4, "changedPaths": 16, "patchBytes": 262144,
                        "wallSeconds": 60, "gitCommands": 256, "outputBytes": 8388608,
                        "commandOutputBytes": 2097152, "scratchBytes": 67108864,
                        "workers": 4, "sourcePromotion": False},
        "exclusions": [], "runtimeInputs": runtime_requests, "replayInputs": replay_requests,
    }
    return _canonical(payload) + b"\n"
