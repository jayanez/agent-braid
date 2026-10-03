#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture a fresh-process bounded runtime reproduction, separate from CI profiles."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
INPUTS = [
    'agent_braid/git_runtime.py', 'agent_braid/git_process.py', 'agent_braid/git_exec.py',
    'agent_braid/git_adapter.py', 'agent_braid/git_replay.py', 'agent_braid/analysis.py',
    'agent_braid/cli.py', 'research/lab/model.py', 'tests/test_git_runtime.py',
    'scripts/reproduce_m4_runtime.py', 'specs/020-m4-local-git-runtime/spec.md',
    'specs/020-m4-local-git-runtime/plan.md', 'docs/adr/0019-bounded-local-git-runtime.md',
    'schemas/0.1.0-alpha/git-runtime-request.schema.json',
    'schemas/0.1.0-alpha/git-runtime-manifest.schema.json',
    'schemas/0.1.0-alpha/git-runtime-report.schema.json',
    'schemas/0.1.0-alpha/git-runtime-state.schema.json',
]


def run(output: Path) -> int:
    before = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INPUTS}
    command = [sys.executable, '-m', 'unittest', '-v', 'tests.test_git_runtime']
    process = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, timeout=240)
    # Preserve raw output alongside the machine-readable reproduction record.
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.with_suffix('.txt')
    log.write_bytes(process.stdout)
    def git(*args):
        return subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True,
                              check=True, timeout=30).stdout.decode().strip()
    record = {
        'm4ReproductionVersion': '0.1.0-alpha', 'candidateCommit': git('rev-parse', 'HEAD'),
        'candidateWorkingTreeDirty': bool(git('status', '--porcelain')),
        'environment': {'python': platform.python_version(), 'git': git('--version'),
                        'platform': platform.system(), 'machine': platform.machine()},
        'command': 'python -m unittest -v tests.test_git_runtime',
        'exitCode': process.returncode, 'status': 'passed' if process.returncode == 0 else 'failed',
        'logSha256': hashlib.sha256(process.stdout).hexdigest(),
        'inputs': before,
        'candidateInputsChangedDuringRun': before != {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in INPUTS},
        'limits': ['Owned local fixed-patch software tests; no external-source corpus or semantic code correctness.',
                   'Fresh Python/subprocess reproduction on recorded host, not independent external validation.',
                   'Process interruption controls; power loss and malicious same-UID interference excluded.',
                   'No hard child memory cap; bounded time/commands/output and sampled scratch.',
                   'Passing tests neither adopt ADR 0019 nor record founder acceptance or whole M4 closure.'],
    }
    if record['candidateInputsChangedDuringRun']:
        record['status'] = 'invalidated'
        record['exitCode'] = 2
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': record['status'], 'exitCode': process.returncode,
                      'output': str(output)}, sort_keys=True))
    return record['exitCode']


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    return run(parser.parse_args().output)


if __name__ == '__main__':
    raise SystemExit(main())
