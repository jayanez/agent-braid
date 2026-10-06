#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only refinement assessment; never promotes refs or executes project code."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys

VERSION = 'runtime-refinement-assessment-v1'
LIMIT = 1_048_576


class InvalidRefinement(ValueError):
    """The assessment input is unsupported or ambiguous."""


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidRefinement('duplicate JSON member')
        result[key] = value
    return result


def _git(repository: Path, *args: str) -> str:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith('GIT_'):
            del environment[key]
    environment.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_REPLACE_OBJECTS='1', GIT_CONFIG_NOSYSTEM='1')
    result = subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false',
                             '-c', 'core.untrackedCache=false', '-C', str(repository), *args],
                            env=environment, capture_output=True, timeout=10, check=False)
    if result.returncode or len(result.stdout) > LIMIT:
        raise InvalidRefinement('Git observation unavailable or exceeds budget')
    return result.stdout.decode('utf-8').strip()


def assess_promotion(value: object) -> dict:
    """Observe exact target state without validating a certificate or granting authority."""
    keys = {'version', 'capability', 'repository', 'targetRef', 'expectedOld', 'resultTree', 'grant', 'fault'}
    if not isinstance(value, dict) or set(value) != keys:
        raise InvalidRefinement('exact promotion assessment fields required')
    if value['version'] != VERSION or value['capability'] != 'promotion':
        raise InvalidRefinement('unsupported assessment version or capability')
    if not isinstance(value['repository'], str) or len(value['repository']) > 4096:
        raise InvalidRefinement('repository path required')
    ref = value['targetRef']
    if not isinstance(ref, str) or not re.fullmatch(r'refs/heads/[A-Za-z0-9][A-Za-z0-9/_-]{0,127}', ref):
        raise InvalidRefinement('bounded exact branch ref required')
    for key in ('expectedOld', 'resultTree'):
        if not isinstance(value[key], str) or not re.fullmatch('[0-9a-f]{40}|[0-9a-f]{64}', value[key]):
            raise InvalidRefinement('exact object identities required')
    fault = value['fault']
    if fault not in ('none', 'before-cas', 'after-cas', 'unknown'):
        raise InvalidRefinement('unknown simulated fault')
    if value['grant'] is not None:
        raise InvalidRefinement('existing grants cannot authorize expanded capabilities')
    repository = Path(value['repository']).absolute()
    if any(part.is_symlink() for part in (repository, *repository.parents)):
        raise InvalidRefinement('symlink repository path refused')
    reasons = []
    observed = {}
    try:
        common = _git(repository, 'rev-parse', '--git-common-dir')
        observed['commonDirectory'] = common
        observed['targetOld'] = _git(repository, 'show-ref', '--verify', '--hash', ref)
        if observed['targetOld'] != value['expectedOld']:
            reasons.append('stale-target')
        if _git(repository, 'cat-file', '-t', value['resultTree']) != 'tree':
            reasons.append('result-is-not-tree')
        worktrees = _git(repository, 'worktree', 'list', '--porcelain')
        entries = worktrees.split('\n\n')
        for entry in entries:
            lines = entry.splitlines()
            paths = [line[9:] for line in lines if line.startswith('worktree ')]
            if len(paths) != 1 or any(line.startswith(('prunable', 'locked')) for line in lines):
                reasons.append('unknown-worktree-state')
                continue
            if f'branch {ref}' in lines:
                reasons.append('attached-target')
            if 'bare' not in lines:
                if _git(Path(paths[0]), 'status', '--porcelain=v1', '--untracked-files=normal'):
                    reasons.append('dirty-worktree')
    except (InvalidRefinement, OSError, subprocess.TimeoutExpired, UnicodeError):
        reasons.append('unknown-repository-state')
    recovery = {'none': 'not-attempted', 'before-cas': 'no-publication-proposed',
                'after-cas': 'published-effect-would-require-reconciliation',
                'unknown': 'ambiguous-do-not-retry'}[fault]
    return {'version': VERSION, 'capability': 'promotion',
            'status': 'refused' if reasons else 'proposal-only', 'reasons': sorted(set(reasons)),
            'inputDigest': hashlib.sha256(canonical(value)).hexdigest(), 'observed': observed,
            'faultModel': fault, 'recoveryDisposition': recovery,
            'consumerVerification': 'not-performed', 'grantScope': 'none',
            'remainingGates': ['independent-result-verification', 'exclusive-revalidation-and-cas',
                               'adopted-versioned-contract', 'founder-capability-decision', 'specific-operator-grant'],
            'executionAuthorization': False, 'sourcePromotion': False}


def simulate_external(attempts: object) -> dict:
    """Retain every abstract attempt/event, including failure after visible effect."""
    if not isinstance(attempts, list) or not 1 <= len(attempts) <= 32:
        raise InvalidRefinement('one to 32 synthetic attempts required')
    seen = set()
    events = []
    uncertain = False
    for item in attempts:
        if not isinstance(item, dict) or set(item) != {'attemptId', 'operationId', 'idempotencyKey', 'outcome', 'effect'}:
            raise InvalidRefinement('exact abstract attempt fields required')
        for key in ('attemptId', 'operationId', 'idempotencyKey'):
            if not isinstance(item[key], str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}', item[key]):
                raise InvalidRefinement('opaque synthetic identity required')
        if item['attemptId'] in seen:
            raise InvalidRefinement('duplicate attempt identity')
        seen.add(item['attemptId'])
        if item['outcome'] not in ('success', 'failure-before-effect', 'failure-after-effect', 'ambiguous-timeout'):
            raise InvalidRefinement('unknown abstract outcome')
        if type(item['effect']) is not bool:
            raise InvalidRefinement('explicit visible effect boolean required')
        if (item['outcome'] == 'success' and not item['effect']) or (item['outcome'] == 'failure-before-effect' and item['effect']) or (item['outcome'] == 'failure-after-effect' and not item['effect']):
            raise InvalidRefinement('contradictory outcome/effect')
        uncertain |= item['outcome'] in ('failure-after-effect', 'ambiguous-timeout')
        events.append(dict(item))
    return {'version': VERSION, 'domain': 'abstract-synthetic-only', 'attempts': events,
            'visibleEffects': sum(item['effect'] for item in events),
            'status': 'unresolved' if uncertain else 'simulated', 'automaticRetry': False,
            'compensationIsInverse': False, 'executionAuthorization': False}


def inventory_isolation() -> dict:
    """Discover executable presence only; never launches a sandbox or a probe."""
    present = {name: bool(shutil.which(name)) for name in ('bwrap', 'docker', 'podman', 'sandbox-exec')}
    return {'version': VERSION, 'capability': 'code-check', 'installedExecutables': present,
            'status': 'NO-GO', 'enforcement': 'not-verified', 'probesExecuted': 0,
            'unsupportedControls': ['filesystem', 'network', 'descendants', 'memory', 'credentials'],
            'fallback': 'read-only analysis and private fixed-patch replay',
            'executionAuthorization': False}


def _local_file(path: Path, *, output=False) -> Path:
    path = path.absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise InvalidRefinement('symlink path refused')
    if output:
        if path.exists() or not path.parent.is_dir():
            raise InvalidRefinement('new explicit output required')
    elif not path.is_file():
        raise InvalidRefinement('regular bounded input required')
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capability', choices=('promotion', 'code-check', 'external'), required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.capability == 'code-check':
            if args.input is not None:
                raise InvalidRefinement('inventory accepts no project input')
            result = inventory_isolation()
        else:
            if args.input is None:
                raise InvalidRefinement('regular bounded input required')
            input_path = _local_file(args.input)
            descriptor = os.open(input_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            with os.fdopen(descriptor, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise InvalidRefinement('regular bounded input required')
                raw = stream.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise InvalidRefinement('input exceeds one MiB')
            value = json.loads(raw, object_pairs_hook=_pairs,
                               parse_constant=lambda _: (_ for _ in ()).throw(InvalidRefinement('non-finite input')))
            result = assess_promotion(value) if args.capability == 'promotion' else simulate_external(value)
        serialized = json.dumps(result, sort_keys=True, indent=2) + '\n'
        if args.output is not None:
            destination = _local_file(args.output, output=True)
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                    stream.write(serialized)
                    stream.flush()
                    os.fsync(stream.fileno())
            except BaseException:
                destination.unlink(missing_ok=True)
                raise
        print(serialized, end='')
        return 0
    except (InvalidRefinement, ValueError, OSError, UnicodeError, RecursionError):
        print(json.dumps({'status': 'refused', 'reason': 'invalid or unavailable assessment input',
                          'executionAuthorization': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
