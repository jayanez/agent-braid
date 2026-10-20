# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in Core API preparation inside one live verified request.

Only owned synthetic repositories and the finite T024 patch domain are admitted.
No execute/recover/grant API is reachable through this adapter. This is not a
public tool registration, an external proposal ingress or a hard wall-time SLA.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import tempfile
import threading
from time import monotonic_ns
from collections.abc import Mapping

from . import git_replay, git_runtime
from .git_process import (GitCommandBudget, GitInfrastructureFailure, run_git,
                          GitCommandLimitExceeded, GitExecutionTimeout)
from .system_one import canonical, digest, freeze, parse_json, thaw
from . import system_one_verified_ir as ir
from .system_one_verified_selection import VerifiedRequestContext, _REASONS

_KEYS = {'format', 'consumerId', 'request', 'requestDigest', 'snapshot', 'snapshotDigest',
         'interpretationDigest', 'decision', 'decisionDigest', 'verifierResult',
         'runtimeRequest', 'executionAuthorization', 'proposalDigest'}
_EXTRA_REASONS = {'consumer-mismatch', 'proposal-digest-mismatch', 'inadmissible-choice',
    'runtime-request-mismatch', 'target-tree-mismatch', 'native-not-verified',
    'native-prepare-failed', 'transport-failure', 'evidence-incomplete',
    'cleanup-failed', 'termination-unknown'}


def _require(ok, reason='invalid-envelope'):
    if not ok:
        raise ValueError(reason)


def _reason(exc):
    if isinstance(exc, ValueError) and str(exc) in _REASONS | _EXTRA_REASONS:
        return str(exc)
    if isinstance(exc, GitInfrastructureFailure):
        return {'timeout': 'deadline-exceeded', 'cancelled': 'cancelled',
                'command-limit': 'work-budget-exceeded', 'output-limit': 'input-budget-exceeded',
                'scratch-limit': 'work-budget-exceeded'}.get(exc.category, 'internal-failure')
    return 'internal-failure'


class _StageBudget(GitCommandBudget):
    """One aggregate budget; stage/native caps can only restrict admission."""
    context = None
    stage = None

    def __post_init__(self):
        super().__post_init__()
        self._stage_lock = threading.Lock()
        self._native_window = None
        self._command_bytes = 0

    def set_stage(self, name):
        previous = self.stage, self._native_window
        self.stage = name
        caps = (git_runtime.LIMITS if name == 'nativePrepare' else
                {'wallSeconds': git_replay.MAX_REPLAY_SECONDS,
                 'gitCommands': git_replay.MAX_GIT_COMMANDS,
                 'outputBytes': git_replay.MAX_REPLAY_OUTPUT,
                 'commandOutputBytes': git_replay.MAX_GIT_OUTPUT} if name == 'nativeCheck' else None)
        self._native_window = (None if caps is None else {
            'end': self.context._clock() + int(caps['wallSeconds'] * 1e9),
            'commands': self.commands, 'output': self.output_bytes, 'caps': dict(caps)})
        return previous

    def restore_stage(self, state):
        self.stage, self._native_window = state

    def begin_command(self, command_timeout):
        if self.stage is not None:
            self.context.checkpoint(self.stage, 0)
            command_timeout = min(command_timeout, self.context.remaining_ns(self.stage) / 1e9)
        # Count refused command admissions exactly as the existing runner does.
        timeout = super().begin_command(command_timeout)
        window = self._native_window
        if window is not None:
            if self.commands - window['commands'] > window['caps']['gitCommands']:
                raise GitCommandLimitExceeded('native command allowance exhausted')
            remaining = (window['end'] - self.context._clock()) / 1e9
            if remaining <= 0:
                raise GitExecutionTimeout('native stage allowance exhausted')
            timeout = min(timeout, remaining)
        with self._stage_lock:
            self._command_bytes = 0
        return timeout

    def record_output(self, byte_count):
        # The stdout/stderr readers share this lock; no global/process patches.
        with self._stage_lock:
            window = self._native_window
            if window is not None and (
                self._command_bytes + byte_count > window['caps']['commandOutputBytes']
                or self.output_bytes + byte_count - window['output'] > window['caps']['outputBytes']):
                return False
            admitted = super().record_output(byte_count)
            if admitted:
                self._command_bytes += byte_count
            return admitted


class CoreRequestContext:
    """Single-owner request with exact producer and complete prepared-body access.

    ``propose`` and ``consume`` share the original context. A wire proposal cannot
    manufacture this live binding. ``consume`` seals once and returns the exact
    ConsumerResult; ``prepared`` retains its full checked native body separately.
    """
    consumer_id = 'core-api'

    def __init__(self, raw: bytes, owned_root: Path, *, cancellation=None, clock=monotonic_ns):
        self._start = clock()
        self._context = VerifiedRequestContext(raw, owned_root, cancellation=cancellation,
                                               clock=clock, budget_factory=_StageBudget)
        if self._context.git_budget is not None:
            self._context.git_budget.context = self._context
        self._clock = clock
        self._producer = self._proposal = self._prepared = self._result = None
        self._producer_evidence = freeze({})
        self._failure = None
        self._prepare_ns = None
        self._counters = {k: 0 for k in ('acquisitionCalls', 'verifierCalls', 'treeBuildCalls',
            'nativeCalls', 'consumerCalls', 'executeCalls', 'recoverCalls', 'grantWrites',
            'persistentRunAllocations')}
        self._observed = {'nativeVerified': None, 'expectedFinalTree': None,
                          'observedFinalTree': None, 'preparedBodyChecked': None}

    @property
    def prepared(self):
        return self._prepared

    @property
    def producer(self):
        """Exact immutable producer body bound by this request's proposal."""
        return self._producer

    @property
    def producer_evidence(self):
        """Original complete producer evidence, never a later replacement."""
        return self._producer_evidence

    @property
    def proposal(self):
        return self._proposal

    @property
    def context(self):
        """Trusted local context, never reconstructed from wire fields."""
        return self._context

    def __getstate__(self):
        raise TypeError('trusted consumer contexts are not serializable')

    def __enter__(self):
        self._context.__enter__()
        return self

    def __exit__(self, kind, error, traceback):
        return self._context.__exit__(kind, error, traceback)

    @contextmanager
    def _phase(self, name):
        budget = self._context.git_budget
        previous = None
        try:
            with self._context.phase(name):
                previous = budget.set_stage(name)
                yield
        finally:
            if previous is not None:
                budget.restore_stage(previous)

    def _tree(self, snapshot, choice):
        self._counters['treeBuildCalls'] += 1
        with self._phase('expectedTree'):
            program = snapshot['program']
            files = thaw(program['files'])
            sequence = program['plans'][choice]
            for name in sequence:
                files, _, failure = ir._apply(files, thaw(program['ops'][name]['changes']),
                                               self._context.checkpoint)
                _require(failure is None, 'invalid-ir')
            _require(all(lines is not None and ir._blob(lines) == program['goal'][path]
                         for path, lines in files.items()), 'target-tree-mismatch')
            budget = self._context.git_budget
            with tempfile.TemporaryDirectory(prefix='verified-tree-', dir=budget.temp_root) as directory:
                root = Path(directory)
                repo = root / 'tree.git'
                env = git_replay._sanitized_environment(root / 'home')
                env.update({'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1',
                            'GIT_CONFIG_COUNT': '0', 'GIT_LITERAL_PATHSPECS': '1',
                            'GIT_DEFAULT_HASH': 'sha1', 'GIT_INDEX_FILE': str(root / 'index')})
                def git(cwd, *args, data=None):
                    return run_git(cwd, ('-c', 'core.hooksPath=/dev/null', *args), env=env,
                                   budget=budget, input_bytes=data).stdout
                git(root, 'init', '--bare', '--template=', '--quiet', str(repo))
                source = self._context.request['source']['task']['request']['repository']
                git(repo, 'fetch', '--quiet', '--no-tags', '--no-recurse-submodules',
                    '--', source, snapshot['snapshot']['base'])
                git(repo, 'read-tree', snapshot['snapshot']['base'])
                for path, lines in sorted(files.items()):
                    oid = git(repo, 'hash-object', '-w', '--stdin',
                              data=''.join(lines).encode('utf-8')).decode().strip()
                    _require(oid == ir._blob(lines), 'target-tree-mismatch')
                    git(repo, 'update-index', '--add', '--cacheinfo', '100644', oid, path)
                result = git(repo, 'write-tree').decode().strip()
                _require(len(result) == 40 and all(c in '0123456789abcdef' for c in result)
                         and result != '0' * 40, 'target-tree-mismatch')
                return result

    def _runtime(self, snapshot, producer):
        if producer['status'] == 'semantic-defer':
            return None
        choice = producer['selectedOptionId']
        sequence = snapshot['program']['plans'][choice]
        original = self._context.request['source']['task']['request']
        by_id = {op['instanceId']: thaw(op) for op in original['operations']}
        _require(len(sequence) == len(by_id) and set(sequence) == set(by_id), 'inadmissible-choice')
        operations = []
        for index, name in enumerate(sequence):
            op = by_id[name]
            _require(set(op['dependencies']) <= set(sequence[:index]), 'inadmissible-choice')
            op['dependencies'] = sorted(set(op['dependencies']) | set(sequence[:index]))
            op['source']['revision'] = snapshot['snapshot']['sources'][name]
            op['declaredWrites'] = sorted(c['path'] for c in snapshot['program']['ops'][name]['changes'])
            operations.append(op)
        return freeze({'gitRuntimeRequestVersion': '0.1.0-alpha', 'repository': original['repository'],
            'baseRevision': snapshot['snapshot']['base'], 'operations': operations, 'order': sequence,
            'expectedFinalTree': self._tree(snapshot, choice)})

    def propose(self):
        """Create a bounded advisory proposal; refused producers cannot propose."""
        _require(self._result is None and self._proposal is None)
        self._producer = self._context.decide()
        self._producer_evidence = self._context.evidence
        _require(self._producer['status'] != 'refused', self._producer['reasonCodes'][0]
                 if self._producer['reasonCodes'] else 'internal-failure')
        bodies = self._context.evidence
        runtime = self._runtime(bodies['snapshot'], self._producer)
        value = {'format': 's1-verified-consumer-proposal-v1', 'consumerId': self.consumer_id,
            'request': self._context.request, 'requestDigest': digest(self._context.request),
            'snapshot': bodies['snapshot'], 'snapshotDigest': bodies['snapshot']['snapshotDigest'],
            'interpretationDigest': digest(self._context.request['interpretation']),
            'decision': self._producer, 'decisionDigest': digest(self._producer),
            'verifierResult': bodies['verifierResult'], 'runtimeRequest': runtime,
            'executionAuthorization': False}
        value['proposalDigest'] = digest(value)
        # Enforce whole-proposal limits, not per-field limits. Freeze is not admission.
        self._proposal = freeze(parse_json(canonical(value)))
        return self._proposal

    def _admit(self, raw):
        value = parse_json(raw)
        _require(type(value) is dict and set(value) == _KEYS)
        _require(value['format'] == 's1-verified-consumer-proposal-v1', 'unsupported-version')
        _require(value['consumerId'] == self.consumer_id, 'consumer-mismatch')
        _require(value['executionAuthorization'] is False)
        _require(value['proposalDigest'] == digest({k: v for k, v in value.items()
                                                  if k != 'proposalDigest'}), 'proposal-digest-mismatch')
        _require(self._proposal is not None, 'evidence-incomplete')
        _require(value['runtimeRequest'] == thaw(self._proposal['runtimeRequest']), 'runtime-request-mismatch')
        for key in _KEYS - {'runtimeRequest', 'proposalDigest'}:
            _require(value[key] == thaw(self._proposal[key]), 'evidence-mismatch')
        return freeze(value)

    def _native(self, request):
        with self._phase('nativeCheck'):
            self._counters['nativeCalls'] += 1
            analysis = {k: thaw(request[k]) for k in ('repository', 'baseRevision', 'operations')}
            analysis['gitAnalysisRequestVersion'] = request['gitRuntimeRequestVersion']
            analysis['operations'] = [{k: v for k, v in op.items() if k != 'declaredWrites'}
                                      for op in analysis['operations']]
            bundle, plan = git_replay.produce(analysis, budget=self._context.git_budget)
            # produce already performs independent native replay. Validate the complete
            # returned bodies and their binding rather than trusting its summary.
            try:
                git_replay._validate_bundle_shape(bundle)
                git_replay._validate_plan_shape(plan)
                _require(bundle['evidenceDigest'] == git_replay._bundle_digest(bundle), 'native-not-verified')
                _require(plan['evidenceDigest'] == bundle['evidenceDigest'], 'native-not-verified')
            except (KeyError, TypeError, ValueError):
                raise ValueError('native-not-verified') from None
            _require(plan['executionAuthorization'] is False, 'native-not-verified')
            schedules = bundle['schedules']
            verified = plan['verificationStatus'] == 'verified' and len(schedules) == 1
            self._observed['nativeVerified'] = verified
            _require(verified, 'native-not-verified')
            schedule = schedules[0]
            self._observed['observedFinalTree'] = schedule['finalTree']
            _require(bundle['executionAuthorization'] is False and schedule['status'] == 'complete'
                     and schedule['order'] == thaw(request['order']), 'native-not-verified')
            _require(schedule['finalTree'] == request['expectedFinalTree'], 'target-tree-mismatch')
        with self._phase('nativePrepare'):
            self._counters['consumerCalls'] += 1
            budget = self._context.git_budget
            with tempfile.TemporaryDirectory(prefix='verified-core-', dir=budget.temp_root) as directory:
                destination = Path(directory) / 'unallocated-run'
                manifest = self._prepare_native(request, destination)
                _require(not destination.exists(), 'native-prepare-failed')
                _require(type(manifest) is dict and set(manifest) == {
                    'gitRuntimeManifestVersion', 'request', 'runDirectory', 'repositoryId',
                    'baseTree', 'steps', 'resourceLimits', 'privateConfigDigest',
                    'observationContract', 'executionContract', 'authorizationScope',
                    'sourcePromotion', 'manifestDigest'}, 'evidence-incomplete')
                _require(manifest['gitRuntimeManifestVersion'] == git_runtime.VERSION
                    and manifest['observationContract'] == git_runtime.OBSERVATION
                    and manifest['executionContract'] == git_runtime.EXECUTION
                    and manifest['authorizationScope'] == 'private-run-only'
                    and manifest['runDirectory'] == str(destination), 'evidence-incomplete')
                _require(type(manifest['steps']) is list and len(manifest['steps']) == len(request['order']),
                         'evidence-incomplete')
                parent, tree = request['baseRevision'], manifest['baseTree']
                for step, operation in zip(manifest['steps'], request['operations'], strict=True):
                    _require(type(step) is dict and set(step) == {'operationId', 'attemptId',
                        'sourceCommit', 'patchDigest', 'inputTree', 'outputTree', 'parentCommit',
                        'commit', 'effects'}, 'evidence-incomplete')
                    _require(step['operationId'] == operation['instanceId']
                        and step['attemptId'] == operation['attemptId']
                        and step['sourceCommit'] == operation['source']['revision']
                        and step['parentCommit'] == parent and step['inputTree'] == tree
                        and [e['path'] for e in step['effects']] == thaw(operation['declaredWrites']),
                        'evidence-incomplete')
                    parent, tree = step['commit'], step['outputTree']
                _require(manifest['request'] == thaw(request) and manifest['sourcePromotion'] is False,
                         'runtime-request-mismatch')
                _require(manifest['steps'][-1]['outputTree'] == request['expectedFinalTree'],
                         'target-tree-mismatch')
                _require(manifest['manifestDigest'] == git_runtime._digest(
                    {k: v for k, v in manifest.items() if k != 'manifestDigest'}), 'evidence-incomplete')
                self._prepared = freeze(parse_json(canonical(manifest)))
                self._observed['preparedBodyChecked'] = True

    def _record(self, final_decision):
        status = 'refused' if self._failure or final_decision['status'] == 'refused' else self._producer['status']
        reasons = set()
        if self._failure:
            reasons.add(self._failure)
        if final_decision['status'] == 'refused':
            # A known consumer refusal uses a producer-internal stop marker; it
            # is not an additional unexpected internal fault in ConsumerResult.
            reasons.update(code for code in final_decision['reasonCodes']
                           if not (code == 'internal-failure' and self._failure in _EXTRA_REASONS))
        usage = thaw(final_decision['usage'])
        # Full adapter latency includes producer acquisition/decision, handoff and
        # actual cleanup. Nested spans must not be added to this total.
        usage['prepareNs'] = usage['entryToCleanupNs'] if usage['entryToCleanupNs'] is not None else self._prepare_ns
        if usage['cleanup'] == 'failed':
            status = 'refused'
            reasons.add('cleanup-failed')
        if usage['termination'] == 'unknown':
            status = 'refused'
            reasons.add('termination-unknown')
        if status == 'semantic-defer':
            reasons = {'no-goal-reaching-plan'}
        if status != 'answered':
            self._prepared = None
        return freeze({'format': 's1-verified-consumer-result-v1', 'consumerId': self.consumer_id,
            'requestDigest': final_decision['requestDigest'],
            'proposalDigest': self._proposal['proposalDigest'] if self._proposal is not None else None,
            'decisionDigest': digest(self._producer) if self._producer is not None else None,
            'status': status, 'reasonCodes': sorted(reasons),
            'preparedDigest': digest(self._prepared) if self._prepared is not None else None,
            'evidence': self._observed, 'counters': {**self._counters, **self._context.work_counts}, 'usage': usage,
            'executionAuthorization': False})

    def _prepare_native(self, request, destination):
        """Trusted local consumer seam; never a callable selected by wire input."""
        budget = self._context.git_budget
        return git_runtime.prepare_run(thaw(request), destination,
            cancel_event=budget.cancel_event, budget=budget)

    def consume(self, raw: bytes):
        """Validate, freshly revalidate and prepare only this request's proposal."""
        _require(self._result is None)
        try:
            value = self._admit(raw)
            self._context.revalidate()
            snapshot = self._context.evidence['snapshot']
            rebuilt = self._runtime(snapshot, self._producer)
            _require(value['runtimeRequest'] == rebuilt, 'runtime-request-mismatch')
            if rebuilt is not None:
                validated = git_runtime._request(thaw(rebuilt))
                _require(validated == thaw(rebuilt), 'runtime-request-mismatch')
                self._observed['expectedFinalTree'] = rebuilt['expectedFinalTree']
                self._native(rebuilt)
        except Exception as exc:
            self._failure = _reason(exc)
            self._context._fail(self._failure if self._failure in _REASONS else 'internal-failure')
        finally:
            self._prepare_ns = max(0, self._clock() - self._start)
        try:
            self._result = self._context.seal(self._record)
        except Exception:
            # A factory failure terminally seals producer refusal before release.
            # Only a refused wrapper may be assembled after that failure.
            self._failure = 'internal-failure'
            self._result = self._record(self._context.publish())
        return self._result

    def prepare(self):
        """Propose and consume once, retaining full bodies and exact refusals."""
        _require(self._result is None and self._proposal is None)
        try:
            proposal = self.propose()
            return self.consume(canonical(proposal))
        except Exception as exc:
            self._failure = _reason(exc)
            self._context._fail(self._failure if self._failure in _REASONS else 'internal-failure')
            self._result = self._context.seal(self._record)
            return self._result


def prepare_core(raw: bytes, owned_root: Path, *, cancellation=None):
    """Return (exact ConsumerResult, complete checked body or None), with cleanup."""
    with CoreRequestContext(raw, owned_root, cancellation=cancellation) as context:
        result = context.prepare()
        return result, context.prepared
