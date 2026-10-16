# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded isolated fixed-patch preparation; publication remains serial.

Only controlled Git plumbing is executed. Worker timing/isolation observations
are distinct from independently replayable tree/effect claims.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import tempfile
import threading
import time

from .analysis import _canonical, _digest
from . import git_runtime as runtime

VERSION = '0.1.0-alpha'
EXECUTION = 'isolated-preparation-serial-publication-v1'
MAX_RECORD_BYTES = 1024 * 1024
SCHEDULE_KEYS = {'runtimeScheduleVersion', 'executionContract', 'manifestDigest',
                 'waves', 'workers', 'resourceLimits', 'scheduleDigest'}
WORKER_KEYS = {'operationId', 'attemptId', 'sourceCommit', 'patchDigest', 'wave',
               'inputCommit', 'inputTree', 'reads', 'writes', 'sharedResources',
               'expectedEffects', 'expectedTree'}


class InvalidRuntimeSchedule(ValueError):
    """Unverified effects, altered schedule or incomplete worker observations."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise InvalidRuntimeSchedule(reason)


class _Cancellation:
    def __init__(self, external):
        self.external = external
        self.internal = threading.Event()

    def is_set(self):
        return self.internal.is_set() or (self.external is not None and self.external.is_set())


def _overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def _geometry(manifest: dict) -> tuple[list[list[str]], list[dict]]:
    request = manifest['request']
    operations = {op['instanceId']: op for op in request['operations']}
    steps = {step['operationId']: step for step in manifest['steps']}
    waves, pending, completed = [], [], set()
    writes = set()
    for identifier in request['order']:
        op = operations[identifier]
        paths = op['declaredWrites']
        if pending and (not set(op['dependencies']) <= completed
                        or any(_overlap(a, b) for a in paths for b in writes)):
            waves.append(pending)
            completed.update(pending)
            pending, writes = [], set()
        _require(set(op['dependencies']) <= completed, 'dependency is not ready at its wave')
        pending.append(identifier)
        writes.update(paths)
    if pending:
        waves.append(pending)
    workers = []
    order = request['order']
    for wave_number, wave in enumerate(waves):
        first_index = order.index(wave[0])
        input_commit = (request['baseRevision'] if first_index == 0
                        else manifest['steps'][first_index - 1]['commit'])
        input_tree = steps[wave[0]]['inputTree']
        for identifier in wave:
            op, step = operations[identifier], steps[identifier]
            _require([effect['path'] for effect in step['effects']] == op['declaredWrites'],
                     'manifest footprint coverage differs from declared paths')
            workers.append({'operationId': identifier, 'attemptId': op['attemptId'],
                            'sourceCommit': step['sourceCommit'], 'patchDigest': step['patchDigest'],
                            'wave': wave_number, 'inputCommit': input_commit, 'inputTree': input_tree,
                            'reads': [{'path': e['path'], 'mode': e['beforeMode'], 'blob': e['beforeBlob']}
                                      for e in step['effects']],
                            'writes': list(op['declaredWrites']),
                            'sharedResources': [{'kind': 'immutable-git-objects',
                                                 'repositoryId': manifest['repositoryId'],
                                                 'inputCommit': input_commit, 'access': 'read'}],
                            'expectedEffects': deepcopy(step['effects'])})
    return waves, workers


def _wave_preview(manifest: dict, temp: Path, budget):
    source = temp / 'rehearsal.git'
    env = runtime._environment(temp / 'preview-home')
    waves, workers = _geometry(manifest)
    # Advertise each fixed wave input before workers start. This owned preview is
    # immutable for the duration of worker fetches; workers never publish its refs.
    for number, wave in enumerate(waves):
        entry = next(w for w in workers if w['operationId'] == wave[0])
        runtime._git(source, env, budget, 'update-ref', 'refs/heads/wave-' + str(number),
                     entry['inputCommit'])
    return source, waves, workers


def _preview(manifest: dict, temp: Path, cancel_event):
    budget = runtime._budget(temp, cancel_event)
    computed, patches = runtime._prepare(manifest['request'], manifest['runDirectory'], temp,
                                         cancel_event, budget=budget)
    _require(_canonical(computed) == _canonical(manifest), 'runtime manifest changed at worker admission')
    source, waves, workers = _wave_preview(computed, temp, budget)
    return computed, patches, source, budget, waves, workers


def _worker(source: Path, patches: dict, entry: dict, root: Path, budget,
            origin_ns: int, barrier=None) -> dict:
    if barrier is not None:
        try:
            barrier.wait(timeout=10)
        except threading.BrokenBarrierError as exc:
            raise InvalidRuntimeSchedule('worker start barrier failed') from exc
    start = time.monotonic_ns() - origin_ns
    root.mkdir()
    repo = root / 'worker.git'
    env = runtime._environment(root / 'home')
    runtime._init(repo, source, entry['inputCommit'], env, budget)
    before = runtime._tree(repo, entry['inputCommit'], env, budget)
    _require(before == entry['inputTree'], 'worker read a stale input tree')
    patch = patches[entry['operationId']]
    _require(runtime._digest_bytes(patch) == entry['patchDigest'], 'worker patch changed')
    if patch:
        runtime._git(repo, env, budget, 'apply', '--cached', '--whitespace=nowarn', '-', input_bytes=patch)
    tree = runtime._git(repo, env, budget, 'write-tree').decode().strip()
    effects = runtime._effects(repo, before, tree, env, budget)
    _require(effects == entry['expectedEffects'], 'worker observed undeclared or stale effects')
    return {'operationId': entry['operationId'], 'attemptId': entry['attemptId'],
            'wave': entry['wave'], 'inputTree': before, 'outputTree': tree,
            'patchDigest': entry['patchDigest'], 'effects': effects,
            'writableRepository': str(repo), 'writableIndex': str(repo / 'index'),
            'startedNs': start, 'finishedNs': time.monotonic_ns() - origin_ns}


def _serial_reference(manifest: dict, patches: dict, source: Path, budget,
                      waves: list, workers: list, temp: Path) -> dict:
    origin = time.monotonic_ns()
    for index, entry in enumerate(workers):
        actual = _worker(source, patches, entry, temp / ('reference-' + str(index)), budget, origin)
        entry['expectedTree'] = actual['outputTree']
    schedule = {'runtimeScheduleVersion': VERSION, 'executionContract': EXECUTION,
                'manifestDigest': manifest['manifestDigest'], 'waves': waves, 'workers': workers,
                'resourceLimits': {**deepcopy(runtime.LIMITS), 'workers': 4}}
    schedule['scheduleDigest'] = _digest(schedule)
    return schedule


def prepare_schedule(manifest: dict, *, cancel_event=None) -> dict:
    """Compute deterministic expected worker results through a serial reference."""
    _require(isinstance(manifest, dict), 'runtime manifest must be an object')
    with tempfile.TemporaryDirectory(prefix='agent-braid-schedule-reference-') as directory:
        temp = Path(directory)
        _, patches, source, budget, waves, workers = _preview(manifest, temp, cancel_event)
        return _serial_reference(manifest, patches, source, budget, waves, workers, temp)


def _prepare_policy_schedule(request: object, run_directory: str | Path, *,
                             cancel_event=None) -> tuple[dict, dict]:
    """Share one freshly validated producer scratch within this invocation only.

    No caller-supplied manifest, digest or context is reused. The reference has a
    separate unchanged phase budget covering the retained scratch and workers.
    Public schedule reconstruction/receipt verification still rebuild independently.
    """
    with tempfile.TemporaryDirectory(prefix='agent-braid-policy-reference-') as directory:
        temp = Path(directory)
        manifest, patches = runtime._prepare(request, run_directory, temp, cancel_event)
        budget = runtime._budget(temp, cancel_event)
        source, waves, workers = _wave_preview(manifest, temp, budget)
        schedule = _serial_reference(manifest, patches, source, budget, waves, workers, temp)
        return manifest, schedule


def _schedule_shape(schedule: object) -> dict:
    _require(isinstance(schedule, dict) and set(schedule) == SCHEDULE_KEYS, 'invalid schedule fields')
    _require(len(_canonical(schedule)) <= MAX_RECORD_BYTES, 'schedule record too large')
    _require(schedule['runtimeScheduleVersion'] == VERSION
             and schedule['executionContract'] == EXECUTION, 'unsupported scheduler contract')
    _require(isinstance(schedule['workers'], list) and 2 <= len(schedule['workers']) <= 4,
             'invalid worker coverage')
    for entry in schedule['workers']:
        _require(isinstance(entry, dict) and set(entry) == WORKER_KEYS, 'incomplete worker footprint')
        _require(isinstance(entry['expectedTree'], str) and runtime.OID.fullmatch(entry['expectedTree']),
                 'invalid expected worker tree')
    payload = {k: v for k, v in schedule.items() if k != 'scheduleDigest'}
    _require(schedule['scheduleDigest'] == _digest(payload), 'schedule digest differs')
    return schedule


def run_preparations(manifest: dict, schedule: object, *, cancel_event=None) -> dict:
    """Run dependency-ready waves in isolated scratch, without publishing a run."""
    schedule = _schedule_shape(schedule)
    cancellation = _Cancellation(cancel_event)
    origin = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix='agent-braid-scheduled-workers-') as directory:
        temp = Path(directory)
        _, patches, source, budget, waves, geometry = _preview(manifest, temp, cancellation)
        expected_geometry = [{k:v for k,v in w.items() if k != 'expectedTree'}
                             for w in schedule['workers']]
        _require(_canonical(geometry) == _canonical(expected_geometry)
                 and waves == schedule['waves']
                 and schedule['manifestDigest'] == manifest['manifestDigest']
                 and _canonical(schedule['resourceLimits']) == _canonical({**runtime.LIMITS, 'workers': 4}),
                 'schedule footprints, dependencies, inputs or limits changed')
        by_id = {entry['operationId']: entry for entry in schedule['workers']}
        observations = {}
        try:
            # The pool is local to this run and created only when a wave can
            # overlap. Singleton waves remain synchronous in the same owned scope.
            with ExitStack() as resources:
                pool = None
                for wave in waves:
                    if len(wave) == 1:
                        identifier = wave[0]
                        entry = by_id[identifier]
                        result = _worker(source, patches, entry,
                                         temp / ('worker-' + str(manifest['request']['order'].index(identifier))),
                                         budget, origin)
                        _require(result['outputTree'] == entry['expectedTree'],
                                 'worker differs from serial reference')
                        observations[identifier] = result
                        continue
                    if pool is None:
                        pool = resources.enter_context(ThreadPoolExecutor(
                            max_workers=max(map(len, waves)), thread_name_prefix='braid-fixed-patch'))
                    barrier = threading.Barrier(len(wave))
                    futures = {pool.submit(_worker, source, patches, by_id[identifier],
                                           temp / ('worker-' + str(manifest['request']['order'].index(identifier))),
                                           budget, origin, barrier): identifier for identifier in wave}
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                            entry = by_id[futures[future]]
                            _require(result['outputTree'] == entry['expectedTree'],
                                     'worker differs from serial reference')
                        except BaseException:
                            cancellation.internal.set()
                            raise
                        observations[result['operationId']] = result
        except BaseException:
            cancellation.internal.set()
            raise
        _require(len(observations) == len(geometry), 'incomplete worker observations')
        records = [observations[identifier] for identifier in manifest['request']['order']]
        events = sorted([(r['startedNs'], 1) for r in records] + [(r['finishedNs'], -1) for r in records])
        active = peak = 0
        for _, delta in events:
            active += delta
            peak = max(peak, active)
        result = {'runtimePreparationEvidenceVersion': VERSION, 'executionContract': EXECUTION,
                  'manifestDigest': manifest['manifestDigest'], 'scheduleDigest': schedule['scheduleDigest'],
                  'workers': records, 'observedPeakWorkerIntervals': peak,
                  'wallNs': time.monotonic_ns() - origin,
                  'metrics': {'gitCommands': budget.commands, 'capturedOutputBytes': budget.output_bytes,
                              'sampledPeakScratchBytes': budget.peak_scratch_bytes,
                              'childUserCpuNs': int(budget.child_user_cpu_seconds * 10**9),
                              'childSystemCpuNs': int(budget.child_system_cpu_seconds * 10**9),
                              'processLifetimePeakChildRssBytes': budget.peak_child_rss_bytes},
                  'limits': ['Observed preparation intervals are not a CPU parallelism guarantee.',
                             'Trees/effects are independently replayable; recorded timings are observations.',
                             'Trusted Git and owned scratch; no arbitrary code or hostile same-UID isolation.']}
        result['evidenceDigest'] = _digest(result)
        _require(len(_canonical(result)) <= MAX_RECORD_BYTES, 'worker evidence exceeds record cap')
        return result


def verify_preparations(manifest: dict, schedule: object, evidence: object, *, cancel_event=None) -> dict:
    """Independently replay deterministic claims; timing/isolation remain observations."""
    schedule = _schedule_shape(schedule)
    expected = prepare_schedule(manifest, cancel_event=cancel_event)
    _require(_canonical(schedule) == _canonical(expected), 'schedule is not the serial reference')
    keys = {'runtimePreparationEvidenceVersion', 'executionContract', 'manifestDigest',
            'scheduleDigest', 'workers', 'observedPeakWorkerIntervals', 'wallNs', 'metrics', 'limits', 'evidenceDigest'}
    _require(isinstance(evidence, dict) and set(evidence) == keys, 'incomplete worker evidence')
    _require(len(_canonical(evidence)) <= MAX_RECORD_BYTES, 'worker evidence too large')
    _require(evidence['runtimePreparationEvidenceVersion'] == VERSION
             and evidence['executionContract'] == EXECUTION
             and evidence['manifestDigest'] == manifest['manifestDigest']
             and evidence['scheduleDigest'] == schedule['scheduleDigest'], 'worker evidence inputs differ')
    _require(evidence['evidenceDigest'] == _digest({k:v for k,v in evidence.items() if k != 'evidenceDigest'}),
             'worker evidence digest differs')
    records = evidence['workers']
    _require(isinstance(records, list) and len(records) == len(schedule['workers']), 'missing worker records')
    roots, indexes = set(), set()
    source = Path(manifest['request']['repository']).resolve()
    with tempfile.TemporaryDirectory(prefix='agent-braid-worker-scope-') as directory:
        temp = Path(directory)
        common_raw = runtime._git(source, runtime._environment(temp / 'home'),
                                  runtime._budget(temp, cancel_event), 'rev-parse', '--git-common-dir')
    common = (source / common_raw.decode().strip()).resolve(strict=True)
    wall = evidence['wallNs']
    _require(type(wall) is int and 0 <= wall <= runtime.LIMITS['wallSeconds'] * 10**9,
             'invalid preparation wall observation')
    metrics = evidence['metrics']
    bounds = {'gitCommands': runtime.LIMITS['gitCommands'],
              'capturedOutputBytes': runtime.LIMITS['outputBytes'],
              'sampledPeakScratchBytes': runtime.LIMITS['scratchBytes']}
    cpu = {'childUserCpuNs', 'childSystemCpuNs'}
    _require(isinstance(metrics, dict) and set(metrics) == set(bounds) | cpu |
             {'processLifetimePeakChildRssBytes'}, 'invalid cost observation fields')
    for key, limit in bounds.items():
        _require(type(metrics[key]) is int and 0 <= metrics[key] <= limit, 'invalid bounded cost observation')
    for key in cpu:
        _require(type(metrics[key]) is int and metrics[key] >= 0, 'invalid CPU observation')
    _require(type(metrics['processLifetimePeakChildRssBytes']) is int
             and metrics['processLifetimePeakChildRssBytes'] >= 0, 'invalid RSS observation')
    for expected_worker, record in zip(schedule['workers'], records, strict=True):
        required = {'operationId','attemptId','wave','inputTree','outputTree','patchDigest','effects',
                    'writableRepository','writableIndex','startedNs','finishedNs'}
        _require(isinstance(record, dict) and set(record) == required, 'invalid worker trace fields')
        fields = {key: expected_worker[key] for key in ('operationId','attemptId','wave','inputTree','patchDigest')}
        fields.update(outputTree=expected_worker['expectedTree'], effects=expected_worker['expectedEffects'])
        _require(_canonical({key: record[key] for key in fields}) == _canonical(fields),
                 'worker results differ from independently replayed effects')
        repository, index = record['writableRepository'], record['writableIndex']
        _require(isinstance(repository, str) and Path(repository).is_absolute()
                 and index == str(Path(repository) / 'index'), 'invalid recorded isolation scope')
        _require(repository not in roots and index not in indexes, 'workers shared writable resources')
        path = Path(repository)
        _require(str(path) == repository and '..' not in path.parts
                 and not path.is_relative_to(source) and not path.is_relative_to(common)
                 and not path.is_relative_to(Path(manifest['runDirectory']))
                 and all(not path.is_relative_to(Path(other))
                         and not Path(other).is_relative_to(path) for other in roots),
                 'recorded worker scopes overlap protected storage or each other')
        roots.add(repository); indexes.add(index)
        _require(type(record['startedNs']) is int and type(record['finishedNs']) is int
                 and 0 <= record['startedNs'] < record['finishedNs'] <= wall, 'invalid worker timing observation')
    events = sorted([(r['startedNs'], 1) for r in records] + [(r['finishedNs'], -1) for r in records])
    active = peak = 0
    for _, delta in events:
        active += delta
        peak = max(peak, active)
    _require(type(evidence['observedPeakWorkerIntervals']) is int
             and evidence['observedPeakWorkerIntervals'] == peak, 'inconsistent worker overlap observation')
    # Limits are part of the versioned producer contract, not an authority claim.
    _require(isinstance(evidence['limits'], list) and all(isinstance(v, str) for v in evidence['limits']),
             'invalid observation boundary')
    return {'status':'verified-worker-trees-and-effects', 'scheduleDigest':schedule['scheduleDigest'],
            'timingStatus':'recorded-observations-only', 'isolationStatus':'recorded-owned-scratch-scopes',
            'executionAuthorization':False}


def select_ready_rank_hint(request_bytes, packet_bytes, *, expected_context_digest,
                           expected_registry_digest, ready_ids,
                           scheduler_constraints_digest, grant_binding_digest,
                           cancellation=None):
    """Validate synthetic ranking into a pure sidecar; never changes dispatch.

    All existing preparation, dependency, budget, isolation, cancellation, plan,
    grant, stale-input and recovery gates remain in their unchanged execution path.
    Digests here pin caller-owned metadata; they do not certify a live grant.
    """
    from .system_one import CancellationToken, HASH, digest, freeze
    from .system_one_advisors import validate_stage_request, validate_stage_packet
    identifiers = list(ready_ids) if type(ready_ids) in (list,tuple) else []
    if (not 1 <= len(identifiers) <= 64
            or any(type(item) is not str or not 1 <= len(item.encode('utf-8')) <= 64
                   or any(ord(c)<32 or 127<=ord(c)<=159 for c in item) for item in identifiers)
            or len(set(identifiers)) != len(identifiers)
            or any(type(pin) is not str or not HASH.fullmatch(pin)
                   for pin in (scheduler_constraints_digest,grant_binding_digest))):
        raise InvalidRuntimeSchedule('invalid-advice-context')
    token = CancellationToken() if cancellation is None else cancellation
    if type(token) is not CancellationToken:
        raise InvalidRuntimeSchedule('invalid-advice-context')
    status, reason, ordered = 'fallback','invalid-hint',identifiers
    try:
        request = validate_stage_request(request_bytes,
            expected_context_digest=expected_context_digest,
            expected_registry_digest=expected_registry_digest)
        envelope = request.to_dict()
        packet = validate_stage_packet(packet_bytes,request_bytes=request_bytes,
            expected_context_digest=expected_context_digest,
            expected_registry_digest=expected_registry_digest)
        payload = envelope['payload']
        if (envelope['stage'] == 'ready-rank' and packet['stage']=='ready-rank'
                and packet['status']=='advised' and payload['readyIds']==identifiers
                and payload['readySetDigest']==digest(identifiers)
                and payload['schedulerConstraintsDigest']==scheduler_constraints_digest
                and payload['grantBindingDigest']==grant_binding_digest):
            advice = packet['advice']
            candidate = list(advice['orderedReadyIds'])
            if (len(candidate)==len(identifiers) and set(candidate)==set(identifiers)
                    and advice['readySetDigest']==digest(identifiers)
                    and advice['schedulerConstraintsDigest']==scheduler_constraints_digest
                    and advice['grantBindingDigest']==grant_binding_digest):
                ordered, status, reason = candidate, 'hinted', None
    except (ValueError,TypeError,KeyError,OverflowError):
        pass
    def result(cancelled):
        return freeze({'status':'fallback' if cancelled else status,
            'orderedReadyIds':identifiers if cancelled else ordered,
            'reasonCodes':['cancelled'] if cancelled else ([] if reason is None else [reason]),
            'fallback':'keep-original-order-and-use-existing-consumer',
            'readySetDigest':digest(identifiers),'schedulerConstraintsDigest':scheduler_constraints_digest,
            'grantBindingDigest':grant_binding_digest,'evidenceClass':'heuristic',
            'executionAuthorization':False,'consumerGates':'unchanged-existing-runtime-required'})
    return token.publish(result)
