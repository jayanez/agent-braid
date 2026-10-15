#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Observe installed synthetic cost receipt publication; never load a model/VM.

The parent measures the fixed child through durable inner receipt readback. Its
own terminal receipt is outside that interval and remains explicitly uncovered.
CPU scopes overlap the inner ledger and must not be added to its CPU counters.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


def durable_record(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    return hashlib.sha256(raw).hexdigest()


def usage_ns(who):
    value = resource.getrusage(who)
    return round((value.ru_utime + value.ru_stime) * 1e9)


def supervise(directory, *, paired_git=False):
    """One fixed synthetic child, no retries; retain every terminal attempt."""
    directory = Path(directory)
    # Existing/symlink output is refused before any allocation or execution.
    if directory.exists() or directory.is_symlink():
        raise FileExistsError(directory)
    directory.parent.resolve(strict=True)
    directory.mkdir(mode=0o700)
    directory = directory.resolve(strict=True)
    started = time.monotonic_ns()
    coordinator = usage_ns(resource.RUSAGE_SELF)
    children = usage_ns(resource.RUSAGE_CHILDREN)
    queued = {'signal': None}
    child = None
    cleanup = False
    error = None
    cleanup_error = None
    code = 2
    bindings = {}
    driver = Path(__file__).with_name('reproduce_forecast_cost.py').resolve(strict=True)
    driver_sha = hashlib.sha256(driver.read_bytes()).hexdigest()

    def forward(number, frame):
        queued['signal'] = number
        if child is not None and child.poll() is None:
            try:
                os.killpg(child.pid, number)
            except ProcessLookupError:
                pass

    old = {n: signal.signal(n, forward) for n in (signal.SIGINT, signal.SIGTERM)}
    try:
        args = [sys.executable, '-I', str(driver), '--output-directory', str(directory / 'inner')]
        if paired_git:
            args.append('--paired-git')
        durable_record(directory / 'start.json', {
            'driverSha256': driver_sha, 'pairedGit': paired_git,
            'provenance': 'authentic-on-synthetic', 'modelLoaded': False,
            'executionAuthorization': False,
        })
        if queued['signal'] is not None:
            raise InterruptedError('supervisor-interrupted-before-child')
        # The fixed child emits receipts, not unbounded terminal output.
        child = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                 start_new_session=True)
        try:
            code = child.wait(timeout=180)
        except subprocess.TimeoutExpired:
            error = 'synthetic-child-timeout'
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
                # Killing a coordinator does not prove descendant cleanup.
                cleanup = False
            code = 2
        for name in ('payload.json', 'ledger.json', 'summary.json'):
            path = directory / 'inner' / name
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                raw = stream.read(1048577)
                if len(raw) > 1048576:
                    raise ValueError('inner-receipt-budget')
            bindings[name] = hashlib.sha256(raw).hexdigest()
        from agent_braid.forecast_data import parse_record
        from agent_braid.forecast_cost import validate_cost_ledger
        ledger = validate_cost_ledger(parse_record((directory / 'inner/ledger.json').read_bytes()))
        cleanup = ledger['cleanupConfirmed'] and child.returncode is not None and error != 'synthetic-child-timeout'
        durable_record(directory / 'inner-index.json', {'sha256': bindings})
        if json.loads((directory / 'inner-index.json').read_bytes())['sha256'] != bindings:
            raise ValueError('publication-readback-drift')
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        error = error or type(exc).__name__
        code = 2
    finally:
        if child is not None and child.poll() is None:
            cleanup = False
            try:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_error = 'owned-child-reap-unconfirmed'
                code = 2
        for n, handler in old.items():
            signal.signal(n, handler)
    ended = time.monotonic_ns()
    result = {
        'version': 'agent-braid-synthetic-cost-supervisor-v1',
        'driverSha256': driver_sha, 'supervisorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'provenance': 'authentic-on-synthetic', 'wallNsThroughInnerPublicationReadback': ended - started,
        'coordinatorCpuNs': usage_ns(resource.RUSAGE_SELF) - coordinator,
        'waitedChildTreeCpuNs': usage_ns(resource.RUSAGE_CHILDREN) - children,
        'cpuScope': 'outer-process-and-waited-child-tree-overlap-inner-do-not-add',
        'innerReceiptSha256': bindings, 'cleanupConfirmed': cleanup,
        'exit': code, 'interruptedSignal': queued['signal'], 'error': error, 'cleanupError': cleanup_error,
        'gaps': ['prior-artifact-provisioning-unallocated', 'worker-and-daemon-not-exercised',
                 'this-terminal-receipt-publication-after-boundary'],
        'modelLoaded': False, 'fullDeploymentCostAccepted': False,
        'executionAuthorization': False,
    }
    durable_record(directory / 'supervisor.json', result)
    return (128 + queued['signal']) if queued['signal'] is not None else code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--paired-git', action='store_true')
    args = parser.parse_args()
    return supervise(args.output_directory, paired_git=args.paired_git)


if __name__ == '__main__':
    raise SystemExit(main())
