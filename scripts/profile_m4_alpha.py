#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Profile unchanged M4 treatments by phase; compare descriptive frozen captures."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
from fractions import Fraction
from functools import wraps
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
VERSION = 'm4-cost-profile-1'
SAMPLE_METRICS = ('wallNs', 'parentCpuNs', 'childUserCpuNs', 'childSystemCpuNs',
                  'processLifetimePeakChildRssBytes', 'gitCommands', 'capturedOutputBytes',
                  'sampledPeakPhaseScratchBytes', 'boundedPhaseCount', 'observedPeakWorkerIntervals')
LIMITS = [
    'Diagnostic sidecar; the frozen measurement script/protocol and historical evidence are unchanged.',
    'Six descriptive owned-fixture pairs with uncontrolled caches/background activity.',
    'Phase wall/counters are inclusive and nested: do not sum different phase labels.',
    'Each budget is listed once; shared worker counters are attributed to their coordinator phase.',
    'Profiling/instrumentation overhead and treatment cleanup are included in total wall time.',
    'RSS is a process-lifetime maximum; sampled scratch peaks are not simultaneous storage.',
    'No model/host calls, external workload, scientific result or whole-M4 acceptance.',
]


def _git(checkout: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(checkout), *args], timeout=30).decode().strip()


def _frozen_measurement(checkout: Path):
    # One checkout per interpreter: imports must never mix baseline/candidate code.
    if 'agent_braid' in sys.modules:
        loaded = Path(sys.modules['agent_braid'].__file__).resolve().parent.parent
        if loaded != checkout:
            raise RuntimeError('profile a different checkout in a fresh interpreter')
    sys.path.insert(0, str(checkout))
    spec = importlib.util.spec_from_file_location('_m4_frozen_measurement', checkout / 'scripts/measure_m4_alpha.py')
    if spec is None or spec.loader is None:
        raise RuntimeError('missing frozen M4 measurement script')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextmanager
def phase_capture(measurement):
    """Observe coordinator phases and every budget without changing their limits."""
    scheduler = measurement.runtime_policy.runtime_scheduler
    modules = {'replay': measurement.git_replay, 'runtime': measurement.git_runtime,
               'policy': measurement.runtime_policy, 'scheduler': scheduler}
    names = {
        'replay': ('produce', 'verify_plan'),
        'runtime': ('prepare_run', '_prepare', 'execute_run', 'verify_run'),
        'policy': ('prepare_policy_run', 'verify_policy_plan', 'issue_operator_grant',
                   'execute_policy_run', '_common_directory', '_report'),
        'scheduler': ('prepare_schedule', '_prepare_policy_schedule', '_preview',
                      '_wave_preview', '_serial_reference', 'run_preparations', 'verify_preparations'),
    }
    origin = time.monotonic_ns()
    stack = ContextVar('m4_diagnostic_phases', default=())
    phases, budgets = [], []
    lock = threading.Lock()
    original_budget = measurement.GitCommandBudget.__post_init__

    def counters():
        return (sum(b.commands for b, _ in budgets), sum(b.output_bytes for b, _ in budgets))

    def observe_budget(value):
        original_budget(value)
        budgets.append((value, tuple(item['phase'] for item in stack.get())))

    def wrap(function, name):
        @wraps(function)
        def observed(*args, **kwargs):
            ancestors = stack.get()
            with lock:
                record = {'id': len(phases), 'phase': name,
                          'parentId': ancestors[-1]['id'] if ancestors else None,
                          'startedNs': time.monotonic_ns() - origin}
                phases.append(record)
            token = stack.set((*ancestors, record))
            before = counters()
            record['status'] = 'failed'
            try:
                result = function(*args, **kwargs)
                record['status'] = 'completed'
                return result
            finally:
                after = counters()
                record.update(wallNs=time.monotonic_ns() - origin - record['startedNs'],
                              gitCommands=after[0] - before[0],
                              capturedOutputBytes=after[1] - before[1])
                stack.reset(token)
        return observed

    capture = {'phases': phases, 'budgets': []}
    with ExitStack() as resources:
        resources.enter_context(patch.object(measurement.GitCommandBudget, '__post_init__', observe_budget))
        for key, functions in names.items():
            for name in functions:
                if hasattr(modules[key], name):
                    function = getattr(modules[key], name)
                    resources.enter_context(patch.object(modules[key], name, wrap(function, key + '.' + name)))
        # The original treatment cleans its destination/grant store before ending
        # its total clock. Capture nested preparation and final cleanup too.
        resources.enter_context(patch.object(
            measurement.tempfile.TemporaryDirectory, 'cleanup',
            wrap(measurement.tempfile.TemporaryDirectory.cleanup, 'scratch.cleanup')))
        yield capture
    capture['budgets'] = [
        {'originPhases': list(ancestors), 'gitCommands': budget.commands,
         'capturedOutputBytes': budget.output_bytes, 'sampledPeakScratchBytes': budget.peak_scratch_bytes,
         'limits': {'wallSeconds': budget.wall_seconds, 'gitCommands': budget.max_commands,
                    'outputBytes': budget.max_output_bytes, 'commandOutputBytes': budget.max_command_output_bytes,
                    'scratchBytes': budget.max_scratch_bytes,
                    'childAddressSpaceBytes': budget.max_process_address_space_bytes}}
        for budget, ancestors in budgets]
    summary = {}
    for record in phases:
        value = summary.setdefault(record['phase'], {'invocations': 0, 'wallNs': 0,
                                                     'gitCommands': 0, 'capturedOutputBytes': 0})
        value['invocations'] += 1
        for name in ('wallNs', 'gitCommands', 'capturedOutputBytes'):
            value[name] += record[name]
    capture['phaseSummary'] = summary


def capture_profile(output: Path, checkout: Path) -> int:
    checkout = checkout.expanduser().resolve(strict=True)
    if output.expanduser().resolve().is_relative_to(checkout):
        raise ValueError('profile output must be outside the frozen candidate checkout')
    if _git(checkout, 'status', '--porcelain'):
        raise RuntimeError('profiling requires a clean frozen candidate')
    measurement = _frozen_measurement(checkout)
    before = measurement.inventory()
    candidate = _git(checkout, 'rev-parse', 'HEAD')
    profiler_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    fixture = measurement.fixtures.GitRuntimeTests()
    with patch.dict(os.environ, {'GIT_AUTHOR_DATE': '2000-01-01T00:00:00+00:00',
                                 'GIT_COMMITTER_DATE': '2000-01-01T00:00:00+00:00'}):
        fixture.setUp()
    pairs = []
    try:
        for order in (['a', 'b'], ['b', 'a']):
            request = json.loads(json.dumps(fixture.request)); request['order'] = order
            for repetition in range(3):
                modes = ['serial', 'parallel'] if repetition % 2 == 0 else ['parallel', 'serial']
                samples = {}
                for mode in modes:
                    with phase_capture(measurement) as diagnostic:
                        sample = measurement.treatment(fixture, request, mode)
                    if (sum(b['gitCommands'] for b in diagnostic['budgets']) != sample['gitCommands']
                            or sum(b['capturedOutputBytes'] for b in diagnostic['budgets']) != sample['capturedOutputBytes']
                            or len(diagnostic['budgets']) != sample['boundedPhaseCount']):
                        raise RuntimeError('diagnostic budget coverage differs from frozen treatment')
                    sample['diagnostic'] = diagnostic
                    samples[mode] = sample
                if samples['serial']['resultTree'] != samples['parallel']['resultTree']:
                    raise RuntimeError('serial/parallel disagreement')
                ratio = Fraction(samples['serial']['wallNs'], samples['parallel']['wallNs'])
                pairs.append({'order': order, 'repetition': repetition + 1,
                              'exposure': 'first' if repetition == 0 else 'subsequent',
                              'treatmentOrder': modes, 'samples': samples, 'equivalentFinalTree': True,
                              'serialOverParallelWallRatio': _ratio(ratio)})
    finally:
        fixture.doCleanups()
    ratios = [Fraction(p['serialOverParallelWallRatio']['numerator'],
                       p['serialOverParallelWallRatio']['denominator']) for p in pairs]
    median = statistics.median(ratios)
    changed = (before != measurement.inventory() or bool(_git(checkout, 'status', '--porcelain'))
               or candidate != _git(checkout, 'rev-parse', 'HEAD')
               or profiler_hash != hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    record = {'profileVersion': VERSION, 'status': 'invalidated' if changed else 'captured',
              'candidateCommit': candidate, 'inputs': before, 'profilerSha256': profiler_hash,
              'candidateChangedDuringRun': changed,
              'environment': {'python': platform.python_version(), 'platform': platform.system(),
                              'machine': platform.machine(), 'git': _git(checkout, '--version')},
              'pairs': pairs, 'medianSerialOverParallelWallRatio': _ratio(median),
              'utilityOutcome': 'positive-descriptive' if median > 1 else 'negative-or-null-descriptive',
              'limits': LIMITS}
    _write(output, record)
    print(json.dumps({'status': record['status'], 'candidateCommit': candidate,
                      'utilityOutcome': record['utilityOutcome'], 'output': str(output)}))
    return 2 if changed else 0


def _ratio(value: Fraction) -> dict:
    return {'numerator': value.numerator, 'denominator': value.denominator}


def _integer(value: object, name: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError(name + ' must be a ' + ('positive' if positive else 'nonnegative') + ' integer')
    return value


def _validate_sample(sample: object, mode: str) -> None:
    if not isinstance(sample, dict) or sample.get('mode') != mode:
        raise ValueError('sample mode differs from its treatment')
    for name in SAMPLE_METRICS:
        _integer(sample.get(name), 'sample.' + name,
                 positive=name in {'wallNs', 'boundedPhaseCount', 'observedPeakWorkerIntervals'})
    diagnostic = sample.get('diagnostic')
    if not isinstance(diagnostic, dict) or not isinstance(diagnostic.get('budgets'), list):
        raise ValueError('sample has no diagnostic budget coverage')
    budgets = diagnostic['budgets']
    if len(budgets) != sample['boundedPhaseCount']:
        raise ValueError('diagnostic budget count differs from sample')
    for budget in budgets:
        if not isinstance(budget, dict) or not isinstance(budget.get('limits'), dict):
            raise ValueError('invalid diagnostic budget')
        for name in ('gitCommands', 'capturedOutputBytes', 'sampledPeakScratchBytes'):
            _integer(budget.get(name), 'budget.' + name)
        limits = budget['limits']
        for name in ('gitCommands', 'outputBytes', 'commandOutputBytes', 'scratchBytes'):
            _integer(limits.get(name), 'budget.limits.' + name, positive=True)
        wall = limits.get('wallSeconds')
        if (type(wall) not in (int, float) or wall <= 0
                or type(wall) is float and not math.isfinite(wall)):
            raise ValueError('invalid diagnostic wall limit')
        if limits.get('childAddressSpaceBytes') is not None:
            _integer(limits['childAddressSpaceBytes'], 'budget.limits.childAddressSpaceBytes', positive=True)
        for observed, maximum in (('gitCommands', 'gitCommands'), ('capturedOutputBytes', 'outputBytes'),
                                   ('sampledPeakScratchBytes', 'scratchBytes')):
            if budget[observed] > limits[maximum]:
                raise ValueError('diagnostic budget exceeds its limit')
    if (sum(b['gitCommands'] for b in budgets) != sample['gitCommands']
            or sum(b['capturedOutputBytes'] for b in budgets) != sample['capturedOutputBytes']
            or max(b['sampledPeakScratchBytes'] for b in budgets) != sample['sampledPeakPhaseScratchBytes']):
        raise ValueError('diagnostic budget counters differ from sample')
    phases, summary = diagnostic.get('phases'), diagnostic.get('phaseSummary')
    if not isinstance(phases, list) or not phases or not isinstance(summary, dict):
        raise ValueError('missing diagnostic phase coverage')
    expected_summary = {}
    for index, phase in enumerate(phases):
        if (not isinstance(phase, dict) or not isinstance(phase.get('phase'), str)
                or not phase['phase'] or phase.get('status') != 'completed'):
            raise ValueError('invalid or incomplete diagnostic phase')
        for name in ('id', 'startedNs', 'wallNs', 'gitCommands', 'capturedOutputBytes'):
            _integer(phase.get(name), 'phase.' + name)
        if phase['id'] != index:
            raise ValueError('invalid diagnostic phase identity')
        parent = phase.get('parentId')
        if parent is not None and _integer(parent, 'phase.parentId') >= index:
            raise ValueError('invalid diagnostic phase parent')
        expected = expected_summary.setdefault(phase['phase'], {'invocations': 0, 'wallNs': 0,
                                                               'gitCommands': 0, 'capturedOutputBytes': 0})
        expected['invocations'] += 1
        for name in ('wallNs', 'gitCommands', 'capturedOutputBytes'):
            expected[name] += phase[name]
    for values in summary.values():
        if not isinstance(values, dict) or set(values) != {'invocations', 'wallNs', 'gitCommands', 'capturedOutputBytes'}:
            raise ValueError('invalid diagnostic phase summary')
        for name in values:
            _integer(values[name], 'phaseSummary.' + name, positive=name == 'invocations')
    if summary != expected_summary:
        raise ValueError('diagnostic phase summary differs from its invocations')


def compare_profiles(baseline: dict, candidate: dict) -> dict:
    """Compare medians on matching descriptive corpus/platform, without inference."""
    for value in (baseline, candidate):
        if (not isinstance(value, dict) or value.get('profileVersion') != VERSION or value.get('status') != 'captured'
                or value.get('candidateChangedDuringRun') is not False
                or not isinstance(value.get('pairs'), list) or len(value['pairs']) != 6):
            raise ValueError('comparison requires two valid six-pair frozen profiles')
    if (baseline['environment'] != candidate['environment']
            or baseline['profilerSha256'] != candidate['profilerSha256']):
        raise ValueError('comparison requires matching environment and diagnostic instrument')
    for name in ('scripts/measure_m4_alpha.py', 'specs/021-m4-alpha-runtime/measurement-protocol.md',
                 'tests/test_git_runtime.py'):
        if baseline['inputs'][name] != candidate['inputs'][name]:
            raise ValueError('comparison corpus or frozen measurement boundary changed')
    expected_pairs = [(['a', 'b'], repetition) for repetition in range(1, 4)] + [
        (['b', 'a'], repetition) for repetition in range(1, 4)]
    for (order, repetition), left, right in zip(expected_pairs, baseline['pairs'], candidate['pairs'], strict=True):
        expected_modes = ['serial', 'parallel'] if repetition % 2 == 1 else ['parallel', 'serial']
        for value in (left, right):
            if (value['order'] != order or value['repetition'] != repetition
                    or value['treatmentOrder'] != expected_modes or value.get('equivalentFinalTree') is not True):
                raise ValueError('comparison pair identities or equivalence differ')
            if not isinstance(value.get('samples'), dict) or set(value['samples']) != {'serial', 'parallel'}:
                raise ValueError('invalid treatment coverage')
            for mode in ('serial', 'parallel'):
                _validate_sample(value['samples'][mode], mode)
        trees = {value['samples'][mode]['resultTree'] for value in (left, right) for mode in ('serial', 'parallel')}
        if len(trees) != 1:
            raise ValueError('baseline/candidate results differ')
    modes = {}
    for mode in ('serial', 'parallel'):
        medians = {key: {metric: statistics.median([p['samples'][mode][metric] for p in value['pairs']])
                         for metric in ('wallNs', 'gitCommands', 'capturedOutputBytes', 'boundedPhaseCount')}
                   for key, value in (('baseline', baseline), ('candidate', candidate))}
        wall_ratio = Fraction(medians['candidate']['wallNs']) / Fraction(medians['baseline']['wallNs'])
        modes[mode] = {'medians': medians, 'candidateOverBaselineWallRatio': _ratio(wall_ratio),
                       'candidateGitCommandsSaved': medians['baseline']['gitCommands'] - medians['candidate']['gitCommands']}
    return {'profileComparisonVersion': VERSION, 'status': 'descriptive-comparison',
            'baselineCommit': baseline['candidateCommit'], 'candidateCommit': candidate['candidateCommit'],
            'environment': candidate['environment'], 'modes': modes,
            'candidateParallelImprovedObserved': modes['parallel']['medians']['candidate']['wallNs'] < modes['parallel']['medians']['baseline']['wallNs'],
            'candidateSerialNotRegressedObserved': modes['serial']['medians']['candidate']['wallNs'] <= modes['serial']['medians']['baseline']['wallNs'],
            'limits': LIMITS + ['Observed median differences do not establish causality or general speedup.']}


def _write(output: Path, record: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument('--checkout', type=Path, default=ROOT)
    choice.add_argument('--compare', type=Path, nargs=2, metavar=('BASELINE', 'CANDIDATE'))
    args = parser.parse_args()
    if args.compare:
        baseline, candidate = [json.loads(path.read_text(encoding='utf-8')) for path in args.compare]
        record = compare_profiles(baseline, candidate)
        _write(args.output, record)
        print(json.dumps({'status': record['status'], 'output': str(args.output)}))
        return 0
    return capture_profile(args.output, args.checkout)


if __name__ == '__main__':
    raise SystemExit(main())
