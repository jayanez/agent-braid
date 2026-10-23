# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in deterministic verified-plan composition over owned local fixtures.

No consumer preparation or execution is performed. ``VerifiedRequestContext`` is
trusted, request-local and deliberately nonserializable. Keep it alive through a
future consumer handoff: ``decide`` produces an immutable producer snapshot;
``revalidate`` repeats observations and all verification without resetting its
budgets. Context exit cleans resources and atomically publishes a new final
snapshot, preserving any previously returned immutable producer snapshot.
Cooperative checkpoints do not promise hard bounds for blocking filesystem I/O.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from contextlib import contextmanager
from pathlib import Path
import shutil
import tempfile
import threading
from time import monotonic_ns
from typing import Any

from .git_process import GitCommandBudget
from .system_one import CancellationToken, canonical, digest, freeze, parse_json
from . import system_one_verified_acquisition as acquisition
from . import system_one_verified_ir as ir
from . import system_one_verified_registry as registry

_STAGES = ('acquisition', 'interpretation', 'verification', 'selection', 'expectedTree',
           'handoffRevalidation', 'nativeCheck', 'nativePrepare', 'transportEvidence', 'cleanup')
_REASONS = frozenset({'invalid-envelope', 'unsupported-version', 'unsupported-domain',
    'unsupported-observation', 'invalid-budget', 'input-budget-exceeded', 'source-unavailable',
    'source-drift', 'unsupported-effect', 'incomplete-observation', 'declaration-mismatch',
    'text-mismatch', 'invalid-ir', 'ambiguous-anchor', 'work-budget-exceeded',
    'deadline-exceeded', 'cancelled', 'registry-mismatch', 'verifier-mismatch',
    'no-goal-reaching-plan', 'evidence-mismatch', 'internal-failure'})
_BOUNDS = freeze(acquisition._BOUNDS)
_VERIFIER_PIN = 'a0378c34b805387b0518cf6ebc3da05599976cb7f037d5f140c2571c8f362ea3'
_ENTRY = freeze({'domainId': 't024-eof-context-v1', 'irVersion': 't024-literal-program-v1',
                 'observationContract': 't024-path-blob-projection-v1',
                 'implementationId': 't024-eof-verifier-extracted-v1', 'verifierDigest': _VERIFIER_PIN})
_REGISTRY_DIGEST = digest({'format': 's1-static-verifier-registry-v1', 'entries': [_ENTRY],
                           'executionAuthorization': False})
_POLICY = freeze({'format': 's1-selection-policy-v1', 'cost': 'operation-count',
                  'tieBreak': 'ascii-option-id', 'requireComplete': True, 'executionAuthorization': False})


def _require(ok: bool, reason: str = 'invalid-envelope') -> None:
    if not ok:
        raise ValueError(reason)


def _reason(exc: BaseException) -> str:
    return str(exc) if isinstance(exc, ValueError) and str(exc) in _REASONS - {'no-goal-reaching-plan'} else 'internal-failure'


def _keys(value: Any, fields: set[str], reason: str = 'invalid-envelope') -> None:
    _require(type(value) is dict and set(value) == fields, reason)


def _integer(value: Any, low: int, high: int, reason: str = 'invalid-budget') -> None:
    _require(type(value) is int and low <= value <= high, reason)


def _admit(raw: bytes) -> Mapping:
    value = parse_json(raw)
    _require(len(canonical(value)) <= 1048576, 'input-budget-exceeded')
    _keys(value, {'format', 'requestId', 'source', 'interpretation', 'budgets', 'executionAuthorization'})
    _require(value['format'] == 's1-verified-request-v1', 'unsupported-version')
    _require(value['executionAuthorization'] is False)
    identifier = value['requestId']
    _require(type(identifier) is str and 0 < len(identifier.encode('utf-8')) <= 64
             and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in identifier))
    budget = value['budgets']
    _keys(budget, {'decisionBudgetMs', 'acquisitionBudgetMs', 'prepareBudgetMs', 'stageBudgetMs',
                  'maxHunkApplications', 'maxGitCommands', 'maxOutputBytes', 'maxCommandOutputBytes',
                  'maxScratchBytes', 'terminationMode'}, 'invalid-budget')
    _require(budget['terminationMode'] == 'cooperative', 'invalid-budget')
    for key in ('decisionBudgetMs', 'acquisitionBudgetMs', 'prepareBudgetMs'):
        _integer(budget[key], 1, 2147483647)
    for key, low, high in (('maxHunkApplications', 0, 128), ('maxGitCommands', 1, 512),
                           ('maxOutputBytes', 1, 16777216), ('maxCommandOutputBytes', 1, 8388608),
                           ('maxScratchBytes', 1, 67108864)):
        _integer(budget[key], low, high)
    _require(budget['maxCommandOutputBytes'] <= budget['maxOutputBytes'], 'invalid-budget')
    stages = budget['stageBudgetMs']
    _keys(stages, set(_STAGES), 'invalid-budget')
    for name, duration in stages.items():
        _integer(duration, 1, 2147483647)
        _require(duration <= budget['prepareBudgetMs'], 'invalid-budget')
        if name == 'acquisition':
            _require(duration <= budget['acquisitionBudgetMs'], 'invalid-budget')
        if name in ('interpretation', 'verification', 'selection'):
            _require(duration <= budget['decisionBudgetMs'], 'invalid-budget')
    # Exact nested admission is shared with the existing acquisition implementation;
    # this helper is pure and is called before scratch allocation or any Git call.
    acquisition._admit(value['source'], _BOUNDS)
    # Zero G denotes an absent change preimage, never an admitted goal blob.
    _require(all(entry['blob'] != '0' * 40 for entry in value['source']['task']['goal']))
    payload = value['interpretation']
    _keys(payload, {'format', 'language', 'representation', 'text', 'executionAuthorization'})
    _require(payload['format'] == 't024-text-v1', 'unsupported-version')
    _require(payload['executionAuthorization'] is False)
    _require(payload['language'] in ('en', 'es') and payload['representation'] in ('symbolic', 'controlled'),
             'text-mismatch')
    text = payload['text']
    _require(type(text) is str and len(text.encode('utf-8')) <= 65536, 'text-mismatch')
    _require(text.endswith('\n') and 2 <= len(text[:-1].split('\n')) <= 96, 'text-mismatch')
    return freeze(value)


class VerifiedRequestContext:
    """One synchronous owner of admitted data, cancellation, work and scratch.

    Internal clock/checkpoint dependencies are trusted Python objects, never wire
    fields. Instances are single-owner, not concurrent sessions. Stage invocations
    may tighten enclosing deadlines but cannot restart them. The full cleanup
    phase cap is reserved from the outer allowance before other work is admitted;
    a representationally valid budget with no cleanup slack therefore refuses.
    """
    def __init__(self, raw: bytes, owned_root: Path, *, cancellation: CancellationToken | None = None,
                 clock: Callable[[], int] = monotonic_ns,
                 budget_factory: Callable[..., GitCommandBudget] = GitCommandBudget):
        self._clock, self._start = clock, clock()
        self._owned_processes = []
        self._owned_root = owned_root
        self._token = cancellation if isinstance(cancellation, CancellationToken) else CancellationToken()
        self._cancel = threading.Event()
        self._claimed = self._closed = self._published = self._decided = False
        self._remove_waker = None
        self._request = None
        self._budget = self._git_budget = self._scratch = None
        self._outer_end = self._work_end = self._acquire_end = self._decision_end = None
        self._decision_start = self._decision_ns = self._acquisition_ns = None
        self._cleanup_ns = self._entry_cleanup_ns = None
        self._termination, self._cleanup = 'not-started', 'not-allocated'
        self._hunks = 0
        self._rows, self._frames = [], []
        self._counts = {}
        self._failure = None
        self._known_pins = {}
        self._work_counts = {'acquisitionCalls': 0, 'verifierCalls': 0}
        self._snapshot = self._verifier = self._decision = None
        self._evidence = freeze({})
        try:
            self._owned_root = Path(owned_root)
            _require(cancellation is None or isinstance(cancellation, CancellationToken))
            try:
                self._token.claim()
            except ValueError:
                raise ValueError('invalid-envelope') from None
            self._claimed = True
            self._remove_waker = self._token.add_waker(self._cancel.set)
            _require(not self._token.cancelled, 'cancelled')
            self._request = _admit(raw)
            self._budget = self._request['budgets']
            self._outer_end = self._start + self._budget['prepareBudgetMs'] * 1000000
            self._work_end = self._outer_end - self._budget['stageBudgetMs']['cleanup'] * 1000000
            self._check('selection')
            self._scratch = Path(tempfile.mkdtemp(prefix='agent-braid-verified-')).resolve()
            self._cleanup = 'unknown'
            self._git_budget = budget_factory(
                temp_root=self._scratch, started_at=self._start / 1000000000,
                wall_seconds=self._budget['prepareBudgetMs'] / 1000,
                max_commands=self._budget['maxGitCommands'], max_output_bytes=self._budget['maxOutputBytes'],
                max_command_output_bytes=self._budget['maxCommandOutputBytes'],
                max_scratch_bytes=self._budget['maxScratchBytes'], cancel_event=self._cancel)
            self._termination = 'unknown'
        except Exception as exc:
            self._fail(_reason(exc))

    @property
    def request(self) -> Mapping | None:
        return self._request

    @property
    def work_counts(self) -> Mapping:
        """Observed invocation entries, excluding work blocked before entry."""
        return freeze(self._work_counts)

    @property
    def evidence(self) -> Mapping:
        return self._evidence

    @property
    def decision(self) -> Mapping | None:
        return self._decision

    @property
    def git_budget(self) -> GitCommandBudget | None:
        """Trusted same-object seam for a future in-process native adapter."""
        return self._git_budget

    def __getstate__(self):
        raise TypeError('trusted request contexts are not serializable')

    def __enter__(self):
        _require(not self._closed)
        return self

    def __exit__(self, kind, error, traceback):
        if error is not None:
            self._fail(_reason(error))
        self.close()
        self.publish()
        return False

    def _fail(self, reason: str) -> None:
        if self._published:
            return
        self._failure = reason
        self._verifier = None
        self._evidence = freeze({})
        self._decision = self._build()

    def _check(self, stage: str) -> None:
        _require(not self._closed)
        try:
            if self._token.cancelled:
                self._cancel.set()
            _require(not self._cancel.is_set(), 'cancelled')
            _require(self._failure is None, self._failure or 'internal-failure')
            _require(self._budget is not None)
            end = self._outer_end if stage == 'cleanup' else self._work_end
            if stage == 'acquisition' and self._acquire_end is not None:
                end = min(end, self._acquire_end)
            if stage in ('interpretation', 'verification', 'selection') and self._decision_end is not None:
                end = min(end, self._decision_end)
            if self._frames:
                end = min(end, *(frame['end'] for frame in self._frames))
            _require(self._clock() < end, 'deadline-exceeded')
        except ValueError as exc:
            self._fail(_reason(exc))
            raise

    def _open(self, stage: str, automatic: bool) -> dict:
        _require(stage in _STAGES)
        self._check(stage)
        # The last of the contract's 64 rows belongs to actual cleanup.
        _require(len(self._rows) < 63, 'work-budget-exceeded')
        now = self._clock()
        if stage == 'acquisition' and self._acquire_end is None:
            self._acquire_end = min(self._work_end, now + self._budget['acquisitionBudgetMs'] * 1000000)
        end = min(self._work_end, now + self._budget['stageBudgetMs'][stage] * 1000000)
        if stage == 'acquisition':
            end = min(end, self._acquire_end)
        if stage in ('interpretation', 'verification', 'selection') and self._decision_end is not None:
            end = min(end, self._decision_end)
        if self._frames:
            end = min(end, *(frame['end'] for frame in self._frames))
        occurrence = self._counts.get(stage, 0)
        self._counts[stage] = occurrence + 1
        row = {'name': stage, 'occurrence': occurrence, 'elapsedNs': None, 'outcome': 'unknown'}
        self._rows.append(row)
        frame = {'name': stage, 'start': now, 'end': end, 'automatic': automatic, 'row': row}
        self._frames.append(frame)
        self._check(stage)
        return frame

    def _finish(self, frame: dict, reason: str | None = None) -> None:
        elapsed = max(0, self._clock() - frame['start'])
        frame['row']['elapsedNs'] = elapsed
        frame['row']['outcome'] = ('completed' if reason is None else
            {'deadline-exceeded': 'expired', 'cancelled': 'cancelled'}.get(reason, 'refused'))
        if frame['name'] == 'acquisition':
            self._acquisition_ns = (self._acquisition_ns or 0) + elapsed
        self._frames.pop()

    @contextmanager
    def phase(self, stage: str):
        """Trusted nested stage scope; no new outer budget or counter reset."""
        _require(not self._closed)
        frame, reason = None, None
        try:
            frame = self._open(stage, False)
            yield
            self._check(stage)
        except Exception as exc:
            reason = _reason(exc)
            self._fail(reason)
            raise
        finally:
            if frame is not None:
                while self._frames and self._frames[-1] is not frame:
                    self._finish(self._frames[-1], reason)
                self._finish(frame, reason)

    def checkpoint(self, stage: str, units: int) -> None:
        try:
            _require(stage in _STAGES and type(units) is int and units >= 0)
            _require(units == 0 or stage == 'verification')
            self._check(stage)
            if not self._frames or self._frames[-1]['name'] != stage:
                if self._frames and self._frames[-1]['automatic']:
                    self._finish(self._frames[-1])
                if not self._frames or self._frames[-1]['name'] != stage:
                    self._open(stage, True)
            self._check(stage)
            _require(self._hunks + units <= self._budget['maxHunkApplications'], 'work-budget-exceeded')
            self._hunks += units
        except ValueError as exc:
            # Includes automatic stage admission, not only clock/hunk checks.
            # A caught operational error cannot leave the producer successful.
            self._fail(_reason(exc))
            raise

    def remaining_ns(self, stage: str) -> int:
        _require(stage in _STAGES)
        self._check(stage)
        end = self._outer_end if stage == 'cleanup' else self._work_end
        if stage == 'acquisition' and self._acquire_end is not None:
            end = min(end, self._acquire_end)
        if stage in ('interpretation', 'verification', 'selection') and self._decision_end is not None:
            end = min(end, self._decision_end)
        if self._frames:
            end = min(end, *(frame['end'] for frame in self._frames))
        return max(0, end - self._clock())

    def _acquire(self) -> Mapping:
        with self.phase('acquisition'):
            self._work_counts['acquisitionCalls'] += 1
            result = acquisition.acquire(self._request['source'], self._owned_root, limits=_BOUNDS,
                git_budget=self._git_budget, remaining_ns=self.remaining_ns, checkpoint=self.checkpoint)
            binding = result['binding']
            return freeze({'format': 's1-acquired-snapshot-v1',
                'sourceRequestDigest': digest(self._request['source']), 'snapshot': binding['snapshot'],
                'snapshotDigest': binding['snapshotDigest'], 'domainId': _ENTRY['domainId'],
                'irVersion': _ENTRY['irVersion'], 'irDigest': digest(result['program']),
                'grammarVersion': 't024-text-v1', 'observationContract': _ENTRY['observationContract'],
                'bounds': _BOUNDS, 'program': result['program'], 'observedEffects': result['observedEffects'],
                'declaredEffects': result['declaredEffects'], 'coverage': result['coverage'],
                'executionAuthorization': False})

    def reacquire(self) -> Mapping:
        """Fresh same-request observation; pins and cumulative budgets must match."""
        _require(self._snapshot is not None and self._failure is None and not self._closed)
        try:
            observed = self._acquire()
            _require(digest(observed) == digest(self._snapshot), 'source-drift')
            return observed
        except Exception as exc:
            self._fail(_reason(exc))
            raise

    def _verify(self, snapshot: Mapping) -> Mapping:
        if self._decision_start is None:
            self._decision_start = self._clock()
            self._decision_end = min(self._work_end,
                self._decision_start + self._budget['decisionBudgetMs'] * 1000000)
        with self.phase('interpretation'):
            restored = ir.interpret(self._request['interpretation'], checkpoint=self.checkpoint)
            _require(digest(restored) == snapshot['irDigest'], 'text-mismatch')
        with self.phase('verification'):
            identity = {key: _ENTRY[key] for key in ('domainId', 'irVersion', 'observationContract', 'verifierDigest')}
            identity['registryDigest'] = _REGISTRY_DIGEST
            _require(registry.resolve(identity, checkpoint=self.checkpoint) == _ENTRY, 'registry-mismatch')
            self._known_pins.update(registryDigest=_REGISTRY_DIGEST, verifierDigest=_VERIFIER_PIN)
            order = self._request['source']['task']['optionOrder']
            self._work_counts['verifierCalls'] += 1
            raw = ir.verify_program(restored, tuple(order), max_hunks=128, checkpoint=self.checkpoint)
            plans = []
            for option, plan in raw['plans'].items():
                self.checkpoint('verification', 0)
                plans.append({'optionId': option, **{key: val for key, val in plan.items()
                                                  if key != 'executionAuthorization'}})
            return freeze({'format': 's1-verifier-result-v1', 'registryDigest': _REGISTRY_DIGEST,
                'verifierDigest': _VERIFIER_PIN, 'snapshotDigest': snapshot['snapshotDigest'],
                'irDigest': snapshot['irDigest'], 'optionIds': order, 'plans': plans,
                'eligibleOptionIds': raw['eligible'], 'status': raw['status'],
                'reasonCodes': [] if raw['status'] == 'answered' else ['no-goal-reaching-plan'],
                'executionAuthorization': False})

    def decide(self) -> Mapping:
        """Produce one frozen finite decision; errors never expose partial plans."""
        _require(not self._closed)
        if self._decided or self._failure is not None:
            return self._decision if self._decision is not None else self._build()
        self._decided = True
        try:
            self._snapshot = self._acquire()
            self._verifier = self._verify(self._snapshot)
            self._known_pins['eligibilityDigest'] = digest(self._verifier)
            with self.phase('selection'):
                self._known_pins['policyDigest'] = digest(_POLICY)
                self._evidence = freeze({'snapshot': self._snapshot,
                    'interpretation': self._request['interpretation'], 'verifierResult': self._verifier})
                self._decision = self._build()
                self.checkpoint('selection', 0)
            self._decision_ns = max(0, self._clock() - self._decision_start)
            self._decision = self._build()
            self._check('selection')
        except Exception as exc:
            if self._decision_start is not None:
                self._decision_ns = max(0, self._clock() - self._decision_start)
            self._fail(_reason(exc))
        return self._decision

    def revalidate(self) -> Mapping:
        """Repeat acquisition, grammar, source pins and every offered plan live."""
        _require(self._verifier is not None and self._failure is None and not self._closed)
        decision_start = None
        try:
            with self.phase('handoffRevalidation'):
                observed = self.reacquire()
                decision_start = self._clock()
                result = self._verify(observed)
                with self.phase('selection'):
                    _require(result == self._verifier, 'evidence-mismatch')
                return result
        except Exception as exc:
            self._fail(_reason(exc))
            raise
        finally:
            if decision_start is not None:
                self._decision_ns = (self._decision_ns or 0) + max(0, self._clock() - decision_start)

    def _usage(self) -> dict:
        budget = self._git_budget
        return {'acquisitionNs': self._acquisition_ns, 'decisionNs': self._decision_ns,
            'prepareNs': None, 'cleanupNs': self._cleanup_ns, 'entryToCleanupNs': self._entry_cleanup_ns,
            'stages': self._rows, 'hunkApplications': self._hunks if self._request is not None else None,
            'gitCommands': budget.commands if budget is not None else None,
            'outputBytes': budget.output_bytes if budget is not None else None,
            'peakScratchBytes': budget.peak_scratch_bytes if budget is not None else None,
            'termination': self._termination, 'cleanup': self._cleanup}

    def _build(self) -> Mapping:
        request, snapshot, verifier = self._request, self._snapshot, self._verifier
        status = 'refused' if self._failure is not None or verifier is None else verifier['status']
        reasons = [self._failure or 'internal-failure'] if status == 'refused' else verifier['reasonCodes']
        source_task = request['source']['task'] if request is not None else None
        references = []
        if status != 'refused':
            references = [{'kind': 'snapshot', 'digest': digest(snapshot)},
                          {'kind': 'interpretation', 'digest': digest(request['interpretation'])},
                          {'kind': 'verifier-result', 'digest': digest(verifier)}]
        return freeze({'format': 's1-verified-plan-v1',
            'requestId': request['requestId'] if request is not None else None,
            'requestDigest': digest(request) if request is not None else None,
            'snapshotDigest': snapshot['snapshotDigest'] if snapshot is not None else None,
            'irDigest': snapshot['irDigest'] if snapshot is not None else None,
            'registryDigest': self._known_pins.get('registryDigest'),
            'verifierDigest': self._known_pins.get('verifierDigest'),
            'policyDigest': self._known_pins.get('policyDigest'),
            'optionSetDigest': digest({'optionOrder': source_task['optionOrder'], 'options': source_task['options']})
                               if source_task is not None else None,
            'eligibilityDigest': self._known_pins.get('eligibilityDigest'),
            'status': status, 'selectedOptionId': verifier['eligibleOptionIds'][0] if status == 'answered' else None,
            'reasonCodes': reasons, 'evidenceRefs': references, 'usage': self._usage(),
            'executionAuthorization': False})

    def close(self) -> None:
        """Attempt owned cleanup even after expiry/cancellation; keep honest usage."""
        if self._closed:
            return
        while self._frames:
            self._finish(self._frames[-1], self._failure)
        start = self._clock()
        # A transport child is a trusted local resource, never a wire capability.
        # Preserve its scratch/admission uncertainty until actual termination is
        # observed; synchronous Git helpers already reap their own children.
        try:
            pending = any(process.poll() is None for process in self._owned_processes)
        except Exception:
            pending = True
        if pending:
            self._failure = 'internal-failure'
            self._cleanup = 'failed'
            self._termination = 'unknown'
            self._cleanup_ns = max(0, self._clock() - start)
            self._entry_cleanup_ns = max(0, self._clock() - self._start)
            if len(self._rows) < 64:
                self._rows.append({'name': 'cleanup', 'occurrence': self._counts.get('cleanup', 0),
                                   'elapsedNs': self._cleanup_ns, 'outcome': 'refused'})
            self._verifier = None
            self._evidence = freeze({})
            self._closed = True
            self._decision = self._build()
            return
        if self._scratch is not None:
            cleanup_end = min(self._outer_end, start + self._budget['stageBudgetMs']['cleanup'] * 1000000)
            try:
                shutil.rmtree(self._scratch)
                self._cleanup = 'removed' if not self._scratch.exists() else 'failed'
            except Exception:
                self._cleanup = 'failed'
            end = self._clock()
            self._cleanup_ns = max(0, end - start)
            self._entry_cleanup_ns = max(0, end - self._start)
            outcome = 'completed' if self._cleanup == 'removed' else 'refused'
            if end >= cleanup_end:
                outcome = 'expired'
                self._failure = 'deadline-exceeded'
            if self._cleanup == 'failed':
                self._failure = 'internal-failure'
            if len(self._rows) < 64:
                self._rows.append({'name': 'cleanup', 'occurrence': self._counts.get('cleanup', 0),
                    'elapsedNs': self._cleanup_ns, 'outcome': outcome})
            else:
                self._failure = 'work-budget-exceeded'
            # All owned operations here are synchronous; Git helper reaps before
            # returning. This makes no claim about unstarted future native work.
            self._termination = 'stopped'
        self._closed = True
        if self._failure is not None:
            self._verifier = None
            self._evidence = freeze({})
        self._decision = self._build()

    def publish(self) -> Mapping:
        """Return the idempotent final producer record."""
        return self._publish()

    def seal(self, factory: Callable[[Mapping], Mapping]) -> Mapping:
        """Seal a trusted downstream record under the same publication lock.

        This is a local callable seam, never admitted through a wire request.
        A consumer must use it before ordinary publication releases ownership.
        """
        _require(not self._published)
        return self._publish(factory)

    def _publish(self, factory=None) -> Mapping:
        """Publish once after cleanup; cancellation/outer expiry suppress late success."""
        if self._published:
            return self._decision
        self.close()
        def final(cancelled: bool) -> Mapping:
            if cancelled or self._cancel.is_set():
                self._fail('cancelled')
            elif self._outer_end is not None and self._clock() >= self._outer_end:
                self._fail('deadline-exceeded')
            self._decision = self._build()
            try:
                result = self._decision if factory is None else freeze(factory(self._decision))
                # Recheck bounded serialization while retaining token ownership.
                if self._token.cancelled or self._cancel.is_set():
                    self._fail('cancelled')
                    result = self._decision if factory is None else freeze(factory(self._decision))
                elif self._outer_end is not None and self._clock() >= self._outer_end:
                    self._fail('deadline-exceeded')
                    result = self._decision if factory is None else freeze(factory(self._decision))
            except BaseException:
                # A failed downstream factory is terminal before ownership release.
                # The old context can subsequently return refusal, never retry work.
                self._fail('internal-failure')
                self._published = True
                raise
            self._published = True
            return result
        try:
            return self._token.publish(final) if self._claimed else final(False)
        finally:
            if self._remove_waker is not None and self._termination != 'unknown':
                self._remove_waker()
                self._remove_waker = None
            if self._claimed and self._termination != 'unknown':
                self._token.release()
                self._claimed = False


def evaluate(raw: bytes, owned_root: Path, *, cancellation: CancellationToken | None = None) -> Mapping:
    """Return only the exact final decision; evidence requires the trusted context API."""
    with VerifiedRequestContext(raw, owned_root, cancellation=cancellation) as context:
        context.decide()
    return context.decision
