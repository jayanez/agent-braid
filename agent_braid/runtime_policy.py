# SPDX-License-Identifier: AGPL-3.0-only
"""Verified portable plans and purpose-bound local operator grants.

The grant store is trusted operator-owned state, not a signature or protection
against hostile same-UID shell access. No MCP tool may create these grants.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import os
from pathlib import Path
import stat
import tempfile
import time
import uuid

from .analysis import _canonical, _digest
from research.lab.model import loads
from . import git_replay, git_runtime, runtime_scheduler

VERSION = "0.1.0-alpha"
POLICY = "owned-operator-grant-v1"
PARALLEL_POLICY = "parallel-owned-operator-grant-v1"
MAX_RECORD_BYTES = 1024 * 1024
MAX_GRANTS = 128
PLAN_KEYS = {"runtimePolicyPlanVersion", "policy", "runtimeManifest", "replayEvidence",
             "advisoryPlan", "consumerVerification", "sourceGitCommonDirectory", "planDigest"}
GRANT_KEYS = {"runtimeOperatorGrantVersion", "grantId", "policyRevision", "planDigest",
              "manifestDigest", "runDirectory", "action", "issuedAt", "expiresAt",
              "state", "grantDigest"}


class InvalidRuntimePolicy(ValueError):
    """Unverified plan, absent operator authority, or inconsistent owned state."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidRuntimePolicy(message)


def _check_cancel(cancel_event) -> None:
    _require(cancel_event is None or not cancel_event.is_set(), "policy dispatch cancelled")


def _bounded(value: object) -> None:
    try:
        _require(len(_canonical(value)) <= MAX_RECORD_BYTES, "policy record exceeds 1 MiB")
    except (TypeError, ValueError, RecursionError) as exc:
        raise InvalidRuntimePolicy("invalid or oversized policy record") from exc


def policy_definition(mode: str = "serial") -> dict:
    """Return a copy of the pinned per-phase policy, never execution authority."""
    _require(mode in {"serial", "parallel"}, "unsupported preparation mode")
    result = {"revision": POLICY if mode == "serial" else PARALLEL_POLICY, "scope": "private-run-only", "sourcePromotion": False,
            "runtimeStageLimits": deepcopy(git_runtime.LIMITS),
            "replayVerificationStageLimits": {
                "wallSeconds": git_replay.MAX_REPLAY_SECONDS,
                "gitCommands": git_replay.MAX_GIT_COMMANDS,
                "outputBytes": git_replay.MAX_REPLAY_OUTPUT,
                "commandOutputBytes": git_replay.MAX_GIT_OUTPUT,
                "scratchBytes": git_replay.MAX_REPLAY_SCRATCH},
            "sharedHardDeadline": False, "grantTtlSeconds": 300,
            "grantMaxTtlSeconds": 900, "maxGrantRecords": MAX_GRANTS}
    if mode == "parallel":
        result["workerStageLimits"] = {**deepcopy(git_runtime.LIMITS), "workers": 4}
        result["executionContract"] = runtime_scheduler.EXECUTION
    return result


def _common_directory(repository: str, cancel_event=None) -> str:
    with tempfile.TemporaryDirectory(prefix="agent-braid-policy-common-") as directory:
        temp = Path(directory)
        raw = git_runtime._git(Path(repository), git_runtime._environment(temp / 'home'),
                               git_runtime._budget(temp, cancel_event), 'rev-parse', '--git-common-dir')
    return str((Path(repository) / raw.decode().strip()).resolve(strict=True))


def prepare_policy_run(request: object, run_directory: str | Path, *,
                       replay_evidence: object, advisory_plan: object, mode: str = "serial",
                       cancel_event=None) -> dict:
    """Independently verify portable evidence, then rehearse an existing serial run.

    Parallel preparation has a separate policy revision; publication remains serial.
    """
    definition = policy_definition(mode)
    _check_cancel(cancel_event)
    _bounded({"request": request, "evidence": replay_evidence, "plan": advisory_plan})
    try:
        req = git_runtime._request(request)
        actual_request = git_replay._normalized_request({**replay_evidence, "repositoryPath": req["repository"]})
        expected_request = git_runtime._analysis_request(req)
        expected_request['operations'].sort(key=lambda item: item['instanceId'])
        for item in expected_request['operations']:
            item['dependencies'] = sorted(item['dependencies'])
        _require(actual_request == expected_request, "replay evidence belongs to different runtime inputs")
        verification = git_replay.verify_plan(advisory_plan, replay_evidence, req['repository'])
        _require(verification.get('status') == 'verified', "portable plan evidence is not independently verified")
        _require(advisory_plan.get('executionAuthorization') is False,
                 "advisory evidence cannot grant execution authority")
        _check_cancel(cancel_event)
        if mode == 'parallel':
            manifest, schedule = runtime_scheduler._prepare_policy_schedule(
                req, run_directory, cancel_event=cancel_event)
        else:
            manifest = git_runtime.prepare_run(req, run_directory, cancel_event=cancel_event)
        _check_cancel(cancel_event)
        result = {"runtimePolicyPlanVersion": VERSION, "policy": definition,
                  "runtimeManifest": manifest, "replayEvidence": deepcopy(replay_evidence),
                  "advisoryPlan": deepcopy(advisory_plan), "consumerVerification": verification,
                  "sourceGitCommonDirectory": _common_directory(req['repository'], cancel_event)}
        if mode == 'parallel':
            result['schedule'] = schedule
        result['planDigest'] = _digest(result)
        _bounded(result)
        return result
    except (git_runtime.InvalidGitRuntime, git_replay.InvalidGitReplay,
            runtime_scheduler.InvalidRuntimeSchedule, KeyError, TypeError, UnicodeError) as exc:
        raise InvalidRuntimePolicy("invalid policy inputs: " + str(exc)) from exc


def verify_policy_plan(value: object, *, cancel_event=None) -> dict:
    """Reconstruct a complete policy plan; a producer's digest is insufficient."""
    _require(isinstance(value, dict), "invalid policy plan")
    revision = value.get("policy", {}).get("revision") if isinstance(value.get("policy"), dict) else None
    _require(revision in {POLICY, PARALLEL_POLICY}, "unsupported policy revision")
    mode = "parallel" if revision == PARALLEL_POLICY else "serial"
    _require(set(value) == (PLAN_KEYS | {"schedule"} if mode == "parallel" else PLAN_KEYS),
             "invalid policy plan fields")
    _bounded(value)
    try:
        manifest = value['runtimeManifest']
        expected = prepare_policy_run(manifest['request'], manifest['runDirectory'],
                                      replay_evidence=value['replayEvidence'],
                                      advisory_plan=value['advisoryPlan'], mode=mode, cancel_event=cancel_event)
        _require(_canonical(value) == _canonical(expected), "policy plan differs from reconstructed inputs, policy or limits")
        return expected
    except (KeyError, TypeError) as exc:
        raise InvalidRuntimePolicy("invalid policy manifest") from exc


def _store(plan: dict, directory: str | Path, *, create: bool) -> Path:
    supplied = Path(directory).expanduser().absolute()
    _require(not supplied.is_symlink(), "grant store cannot be a symlink")
    root = supplied.parent.resolve() / supplied.name
    source = Path(plan['runtimeManifest']['request']['repository'])
    common = Path(plan['sourceGitCommonDirectory'])
    run = Path(plan['runtimeManifest']['runDirectory'])
    _require(not root.is_relative_to(source) and not root.is_relative_to(common),
             "grant store is inside source storage")
    _require(not root.is_relative_to(run) and not run.is_relative_to(root),
             "grant store overlaps private result")
    if create:
        try:
            root.mkdir(mode=0o700)
            git_runtime._fsync_dir(root.parent)
        except FileExistsError:
            pass
    try:
        info = root.lstat()
    except OSError as exc:
        raise InvalidRuntimePolicy("missing or unreadable grant store") from exc
    _require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
             and stat.S_IMODE(info.st_mode) == 0o700, "grant store must be owned mode 0700")
    return root


@contextmanager
def _store_lock(root: Path):
    _require(git_runtime.fcntl is not None, "grant store requires POSIX locking")
    fd = os.open(root / 'operator.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                 and stat.S_IMODE(info.st_mode) == 0o600, "unsafe operator lock")
        try:
            git_runtime.fcntl.flock(fd, git_runtime.fcntl.LOCK_EX | git_runtime.fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise InvalidRuntimePolicy("operator grant store is busy") from exc
        yield
    finally:
        os.close(fd)


def _grant_id(value: object) -> str:
    _require(isinstance(value, str), "invalid operator grant ID")
    try:
        _require(str(uuid.UUID(value)) == value, "invalid operator grant ID")
    except ValueError as exc:
        raise InvalidRuntimePolicy("invalid operator grant ID") from exc
    return value


def _read_grant(root: Path, identifier: str) -> dict:
    path = root / (identifier + '.json')
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                     and stat.S_IMODE(info.st_mode) == 0o600, "unsafe operator grant file")
            _require(info.st_size <= MAX_RECORD_BYTES, "operator grant too large")
            raw = stream.read(MAX_RECORD_BYTES + 1)
        grant = loads(raw.decode("utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        raise InvalidRuntimePolicy("missing or unreadable operator grant") from exc
    _require(isinstance(grant, dict) and set(grant) == GRANT_KEYS, "invalid operator grant fields")
    payload = {key: value for key, value in grant.items() if key not in {'state', 'grantDigest'}}
    _require(grant['grantDigest'] == _digest(payload), "operator grant bytes changed")
    return grant


def issue_operator_grant(plan: object, grant_store: str | Path, *, acknowledge: str,
                         action: str = 'execute', ttl_seconds: int = 300, cancel_event=None) -> dict:
    """Local operator path. Never register this function as a model-callable tool."""
    _require(isinstance(plan, dict) and acknowledge == plan.get('planDigest'),
             "explicit matching policy acknowledgement required")
    _require(isinstance(action, str) and action in {'execute', 'resume', 'abort'}, "invalid grant action")
    _require(type(ttl_seconds) is int and 1 <= ttl_seconds <= 900, "invalid grant lifetime")
    _check_cancel(cancel_event)
    verified = verify_policy_plan(plan, cancel_event=cancel_event)
    _check_cancel(cancel_event)
    root = _store(verified, grant_store, create=True)
    with _store_lock(root):
        _check_cancel(cancel_event)
        _require(len(list(root.glob('*.json'))) < MAX_GRANTS, "operator grant capacity reached")
        now = int(time.time())
        manifest = verified['runtimeManifest']
        grant = {'runtimeOperatorGrantVersion': VERSION, 'grantId': str(uuid.uuid4()),
                 'policyRevision': verified['policy']['revision'], 'planDigest': verified['planDigest'],
                 'manifestDigest': manifest['manifestDigest'], 'runDirectory': manifest['runDirectory'],
                 'action': action, 'issuedAt': now, 'expiresAt': now + ttl_seconds}
        grant['grantDigest'] = _digest(grant)
        grant['state'] = 'issued'
        path = root / (grant['grantId'] + '.json')
        # Exclusive creation prevents replacement of another grant. Partial records
        # from interruption are retained and fail closed; they never dispatch.
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(_canonical(grant) + b'\n')
            stream.flush()
            os.fsync(stream.fileno())
        git_runtime._fsync_dir(root)
        return grant


def _dispatch(plan: object, grant_store: str | Path, grant_id: str, action: str,
              *, cancel_event=None) -> dict:
    identifier = _grant_id(grant_id)
    _check_cancel(cancel_event)
    verified = verify_policy_plan(plan, cancel_event=cancel_event)
    _check_cancel(cancel_event)
    manifest = verified['runtimeManifest']
    root = _store(verified, grant_store, create=False)
    with _store_lock(root):
        grant = _read_grant(root, identifier)
        _require(grant['runtimeOperatorGrantVersion'] == VERSION and grant['policyRevision'] == verified['policy']['revision']
                 and grant['grantId'] == identifier and grant['planDigest'] == verified['planDigest']
                 and grant['manifestDigest'] == manifest['manifestDigest']
                 and grant['runDirectory'] == manifest['runDirectory'] and grant['action'] == action,
                 "operator grant does not match plan, destination or action")
        _require(type(grant['issuedAt']) is int and type(grant['expiresAt']) is int
                 and grant['issuedAt'] <= int(time.time()) < grant['expiresAt']
                 and 0 < grant['expiresAt'] - grant['issuedAt'] <= 900, "operator grant expired or invalid")
        request, destination = manifest['request'], Path(manifest['runDirectory'])
        if grant['state'] == 'consumed':
            _require(destination.exists(), "consumed grant has no inspectable run; operator inspection required")
            result = git_runtime.verify_run(request, destination)
            return _report(verified, root, identifier, 'not-repeated', result, cancel_event)
        _require(grant['state'] == 'issued', "invalid operator grant state")
        if cancel_event is not None:
            _require(not cancel_event.is_set(), "policy dispatch cancelled before grant consumption")
        grant['state'] = 'consumed'
        git_runtime._atomic_json(root, identifier + '.json', grant)
        if action == 'execute':
            if verified['policy']['revision'] == PARALLEL_POLICY:
                _require(not destination.exists(), 'parallel execute requires a new private destination')
                observations = runtime_scheduler.run_preparations(manifest, verified['schedule'],
                                                                   cancel_event=cancel_event)
                _check_cancel(cancel_event)
                git_runtime._atomic_json(root, _preparation_name(verified), observations)
            result = git_runtime.execute_run(request, destination, manifest['manifestDigest'],
                                              cancel_event=cancel_event)
        else:
            result = git_runtime.recover_run(request, destination, manifest['manifestDigest'],
                                              action, cancel_event=cancel_event)
        return _report(verified, root, identifier, 'performed', result, cancel_event)


def _preparation_name(plan: dict) -> str:
    return 'preparation-' + plan['planDigest'].removeprefix('sha256:') + '.json'


def _report(plan: dict, root: Path | None, identifier: str | None, dispatch: str, result: dict,
            cancel_event) -> dict:
    report = {'dispatch': dispatch, 'runtime': result}
    if identifier is not None:
        report['grantId'] = identifier
    if plan['policy']['revision'] == PARALLEL_POLICY:
        _require(root is not None, 'parallel report needs its owned preparation store')
        path = root / _preparation_name(plan)
        _require(path.exists() and not path.is_symlink(), 'missing preparation journal; inspect owned state')
        # Same bounded, owned-file rules as grants; historical timing remains observational.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            _require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                     and stat.S_IMODE(info.st_mode) == 0o600 and info.st_size <= MAX_RECORD_BYTES,
                     'unsafe preparation journal')
            evidence = loads(stream.read(MAX_RECORD_BYTES + 1).decode('utf-8'))
        _check_cancel(cancel_event)
        report['runtime'] = git_runtime.verify_run(plan['runtimeManifest']['request'],
                                                  plan['runtimeManifest']['runDirectory'])
        _check_cancel(cancel_event)
        verification = runtime_scheduler.verify_preparations(plan['runtimeManifest'], plan['schedule'],
                                                            evidence, cancel_event=cancel_event)
        report.update(preparation=evidence, preparationVerification=verification)
    return report


def execute_policy_run(plan: object, grant_store: str | Path, grant_id: str, *, cancel_event=None) -> dict:
    """Consume a locally issued execute grant; retries only inspect existing state."""
    return _dispatch(plan, grant_store, grant_id, 'execute', cancel_event=cancel_event)


def recover_policy_run(plan: object, grant_store: str | Path, grant_id: str, *, action: str,
                       cancel_event=None) -> dict:
    """Resume/abort only through a separately issued purpose-bound grant."""
    _require(isinstance(action, str) and action in {'resume', 'abort'}, "invalid policy recovery action")
    return _dispatch(plan, grant_store, grant_id, action, cancel_event=cancel_event)


def inspect_policy_run(plan: object, grant_store: str | Path, *, cancel_event=None) -> dict:
    """Read-only combined consumer verification; no grant is consumed or issued."""
    verified = verify_policy_plan(plan, cancel_event=cancel_event)
    _check_cancel(cancel_event)
    manifest = verified['runtimeManifest']
    if not Path(manifest['runDirectory']).exists():
        return {'status': 'no-private-run', 'planDigest': verified['planDigest'],
                'dispatchHistory': 'not-established-by-private-run-inspection',
                'executionAuthorization': False}
    parallel = verified['policy']['revision'] == PARALLEL_POLICY
    root = _store(verified, grant_store, create=False) if parallel else None
    result = {} if parallel else git_runtime.verify_run(manifest['request'], manifest['runDirectory'])
    report = _report(verified, root, None, 'not-dispatched', result, cancel_event)
    report['executionAuthorization'] = False
    return report
