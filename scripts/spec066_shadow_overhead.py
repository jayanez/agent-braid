#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T021: descriptive overhead of the System One shadow step; a receipt, not a gate.

Measures, for synthetic AIM batches of 2, 12 and 32 operations and with a cold or a
warm store, two parts of the shadow step:

- `requestPath`: `ToolingService._shadow`, the only shadow work on the caller's
  path (report extraction and the hand-off to the background worker);
- `worker`: `system_one_shadow.observe`, the work under the 50 ms budget
  (feature derivation, salting, validation and the store write), run synchronously.

A cold sample starts from an absent store (directory, salt and lock are created);
a warm sample appends to a store that already holds them and a day file. Every
store lives under a fresh temporary HOME; the script refuses to run unless the
shadow store resolves inside it. Telemetry stays off and no consent or setting of
the real user is read or changed. Timings are wall-clock `perf_counter_ns` on one
machine under whatever else runs on it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
SIZES = (2, 12, 32)
STORES = ('cold', 'warm')
RECEIPT_SCHEMA = 'agent-braid-spec066-overhead/v0.1'
INVENTORY = ('agent_braid/system_one_shadow.py', 'agent_braid/tooling_mcp.py', 'agent_braid/analysis.py',
             'agent_braid/tooling_telemetry.py', 'scripts/spec066_shadow_overhead.py')
WARM_TRUNCATE_BYTES = 2 * 1024 * 1024  # keep the warm day file well under the 4 MiB cap
LIMITS = [
    'Descriptive receipt of one machine and one run; not a gate, a guarantee or a cross-machine figure.',
    'Synthetic AIM batches; real reports may differ in pair mix and resource count.',
    'The worker step is timed synchronously; in service it runs on one background thread, '
    'so it adds no request latency unless the process is CPU-bound.',
    'A stalled or slow filesystem is not simulated; the store write is bounded by the platform only.',
    'Cold samples include directory, salt (with fsync) and lock creation; warm samples do not.',
    'The 50 ms budget is shown as a reference only.',
]


def request(count: int) -> dict:
    """A valid AIM batch with independent, conflicting, ordered and unknown pairs."""
    template = json.loads((ROOT / 'examples/analysis/file-edits.json').read_text())
    record = template['operations'][0]
    operations = []
    for index in range(count):
        name = f'op-{index:02d}'
        effects = [{'kind': 'write', 'resource': f'repo://bench/src/pkg{index % 4}/mod{index}.py'},
                   {'kind': 'read', 'resource': 'repo://bench/docs/guide.md'}]
        if index % 3 == 0:
            effects.append({'kind': 'write', 'resource': 'repo://bench/pyproject.toml'})
        item = json.loads(json.dumps(record))
        item.update(instanceId=name, attemptId=name + '-1',
                    inputDigest='sha256:' + hashlib.sha256(name.encode()).hexdigest(),
                    dependencies=[f'op-{index - 1:02d}'] if index % 5 == 4 else [])
        item['effects']['declared'] = sorted(effects, key=lambda effect: effect['resource'])
        item['effects']['coverage']['status'] = 'partial' if index % 4 == 3 else 'complete'
        operations.append(item)
    return dict(template, operations=operations)


def summary(samples: list[int]) -> dict:
    millis = sorted(value / 1e6 for value in samples)
    p95 = statistics.quantiles(millis, n=20, method='inclusive')[18] if len(millis) > 1 else millis[0]
    return {'samples': len(millis), 'medianMs': round(statistics.median(millis), 4), 'p95Ms': round(p95, 4),
            'minMs': round(millis[0], 4), 'maxMs': round(millis[-1], 4),
            'meanMs': round(statistics.fmean(millis), 4)}


def commit() -> dict:
    def git(*args):
        return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True).stdout.strip()
    return {'commit': git('rev-parse', 'HEAD') or None, 'dirty': bool(git('status', '--porcelain', '--', *INVENTORY))}


def measure(samples: int, warmup: int) -> dict:
    # HOME must point at the private temporary root before any store path is computed.
    base = Path(tempfile.mkdtemp(prefix='agent-braid-s1-overhead-')).resolve()
    real_home = os.environ.get('HOME')
    try:
        os.environ['HOME'] = str(base / 'home')
        (base / 'home').mkdir(mode=0o700)
        sys.path.insert(0, str(ROOT))
        import threading
        from agent_braid import analysis, system_one_shadow as shadow
        from agent_braid.tooling_mcp import ToolingConfig, ToolingService

        def store() -> Path:
            directory = shadow.default_directory()
            if not directory.resolve().is_relative_to(base):
                raise SystemExit('refused: the shadow store does not resolve inside the temporary root')
            return directory

        store()
        source, results = base / 'source', base / 'results'
        source.mkdir()
        results.mkdir()
        service = ToolingService(ToolingConfig(source, results, system_one='shadow'))
        refusals_before = shadow.refusal_counts()
        cells = []
        for size in SIZES:
            aim = request(size)
            report = analysis.analyze(aim)
            args = {'kind': 'aim', 'request': aim}
            envelope = service.invoke('analyze-work', args, threading.Event())
            if envelope.get('status') != 'ok':
                raise SystemExit(f'fixture of {size} operations did not analyze')
            shadow.flush(30)
            for kind in STORES:
                worker, path, statuses = [], [], {}
                for index in range(warmup + samples):
                    if kind == 'cold':
                        shutil.rmtree(store(), ignore_errors=True)
                    else:
                        for day in store().glob('episodes-*.jsonl'):
                            if day.stat().st_size > WARM_TRUNCATE_BYTES:
                                os.truncate(day, 0)
                    before = _lines(store())
                    started = time.perf_counter_ns()
                    shadow.observe('analyze-work', 'aim', report, aim, str(source))
                    elapsed = time.perf_counter_ns() - started
                    episode = _last(store(), before)
                    status = 'not-stored' if episode is None else (
                        episode['systemOne']['status'] + '/' + str(episode['systemOne']['reason']))
                    if kind == 'cold':
                        shutil.rmtree(store(), ignore_errors=True)
                    started = time.perf_counter_ns()
                    service._shadow('analyze-work', args, envelope)
                    handed = time.perf_counter_ns() - started
                    if not shadow.flush(30):
                        raise SystemExit('shadow worker did not finish')
                    if index >= warmup:
                        worker.append(elapsed)
                        path.append(handed)
                        statuses[status] = statuses.get(status, 0) + 1
                pairs = report['summary']['pairCount']
                cells.append({'operations': size, 'pairs': pairs, 'pairsRecorded': min(pairs, shadow.MAX_PAIRS),
                              'store': kind, 'worker': summary(worker), 'requestPath': summary(path),
                              'workerStatuses': dict(sorted(statuses.items()))})
        refusals = {reason: count - refusals_before.get(reason, 0)
                    for reason, count in shadow.refusal_counts().items()
                    if count != refusals_before.get(reason, 0)}
        return {'cells': cells, 'refusalsDuringMeasurement': refusals,
                'budgetReferenceMs': shadow.BUDGET_NANOSECONDS / 1e6}
    finally:
        if real_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = real_home
        shutil.rmtree(base, ignore_errors=True)


def _lines(directory: Path) -> int:
    return sum(path.read_bytes().count(b'\n') for path in directory.glob('episodes-*.jsonl'))


def _last(directory: Path, before: int) -> dict | None:
    """The episode just appended (status only is used), or None when nothing was stored."""
    if not directory.exists() or _lines(directory) == before:
        return None
    newest = max(directory.glob('episodes-*.jsonl'))
    return json.loads(newest.read_bytes().splitlines()[-1])


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--samples', type=int, default=200)
    parser.add_argument('--warmup', type=int, default=10)
    parser.add_argument('--output', type=Path, help='write the JSON receipt here (default: stdout)')
    args = parser.parse_args(argv)
    if args.samples < 2 or args.warmup < 0:
        parser.error('--samples must be at least 2 and --warmup not negative')
    started = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    load = [round(value, 2) for value in os.getloadavg()] if hasattr(os, 'getloadavg') else None
    measured = measure(args.samples, args.warmup)
    receipt = {
        'schema': RECEIPT_SCHEMA,
        'specification': 'SPEC-066 T021 (REQ-002 / SC-003)',
        'kind': 'measurement receipt (descriptive, not a gate)',
        'startedAt': started,
        'command': 'python3 scripts/spec066_shadow_overhead.py --samples {} --warmup {}'.format(
            args.samples, args.warmup),
        'source': commit(),
        'inputs': {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INVENTORY},
        'environment': {'platform': platform.platform(), 'machine': platform.machine(),
                        'python': platform.python_version(), 'implementation': platform.python_implementation(),
                        'cpuCount': os.cpu_count(),
                        'loadAverageAtStart': load},
        'method': {'sizes': list(SIZES), 'stores': list(STORES), 'samplesPerCell': args.samples,
                   'warmupPerCell': args.warmup, 'clock': 'time.perf_counter_ns',
                   'p95': 'statistics.quantiles(n=20, method="inclusive")[18]',
                   'store': 'fresh temporary HOME; telemetry off; no real consent read or changed',
                   'warmTruncateBytes': WARM_TRUNCATE_BYTES},
        **measured,
        'limits': LIMITS,
        'executionAuthorization': False,
    }
    text = json.dumps(receipt, indent=1, sort_keys=True) + '\n'
    if args.output:
        args.output.write_text(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
