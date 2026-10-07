#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare the exact paired manifest; registered execution remains refused."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.utility_fixtures import (
    InvalidUtilityFixture, _destination, build_fixture, validate_prepared_manifest,
)
from agent_braid.utility_trials import (
    build_trial_plan, derive_admission_records, encode_trial_plan,
)
from scripts.measure_m4_utility import (
    DEFAULT_MANIFEST, INPUT_PATHS, PROTOCOL_SHA256, UnsafeDiagnostic,
    run_treatment, source_fingerprint,
)

PREPARATION_INPUTS = (*INPUT_PATHS, 'agent_braid/utility_trials.py', 'scripts/prepare_m4_utility_trials.py')


def _git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], timeout=30).decode().strip()


def _inputs():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in PREPARATION_INPUTS}


def _candidate_state():
    if _git('status', '--porcelain'):
        raise ValueError('preparation requires a clean candidate commit')
    inputs = _inputs()
    if inputs['specs/022-m4-utility-followup/technical-review-packet.md'] != PROTOCOL_SHA256:
        raise ValueError('approved protocol bytes differ')
    return {'candidateCommit': _git('rev-parse', 'HEAD'), 'inputs': inputs}


def _fresh_file(value: Path):
    raw = value.expanduser().absolute()
    if os.path.lexists(raw) or raw.name in {'', '.', '..'}:
        raise ValueError('output must be a fresh ordinary file')
    path = raw.parent.resolve(strict=True) / raw.name
    # _destination performs the full checkout/bare-ancestor guard without creating.
    path = _destination(path)
    if path.is_relative_to(ROOT.resolve()):
        raise ValueError('output must be outside the candidate checkout')
    return path


def prepare_plan(manifest: Path, diagnostics: Path, destination_root: Path, output: Path) -> int:
    """Write a reviewable manifest and receipt, without constructing trial copies."""
    state = _candidate_state()
    raw_manifest = manifest.read_bytes()
    prepared = validate_prepared_manifest(raw_manifest)
    future_root = _destination(destination_root)
    if future_root.is_relative_to(ROOT.resolve()):
        raise ValueError('trial destination must be outside the candidate checkout')
    target = _fresh_file(output)
    receipt_path = _fresh_file(Path(str(target) + '.provenance.json'))
    if target.is_relative_to(future_root) or receipt_path.is_relative_to(future_root):
        raise ValueError('manifest outputs must be outside the future private trial root')
    raw_records = {b['blockId']: (diagnostics / (b['blockId'] + '.json')).read_bytes()
                   for b in prepared['blocks'] if not b['directNumericExclusions']}
    admissions = derive_admission_records(raw_manifest, raw_records)
    for admission in admissions:
        if admission['status'] != 'excluded-by-pinned-cap' and admission.get('diagnosticInputHashes') != state['inputs']:
            raise ValueError('diagnostic code inputs do not match this candidate exactly')
    plan = build_trial_plan(raw_manifest, admissions, candidate_commit=state['candidateCommit'],
                            destination_root=str(future_root))
    raw = encode_trial_plan(plan)
    if _candidate_state() != state:
        raise ValueError('candidate changed during preparation')
    receipt = {'version': 'spec022-paired-plan-provenance-v1', **state,
               'manifestSha256': hashlib.sha256(raw).hexdigest(),
               'preparedManifestSha256': hashlib.sha256(raw_manifest).hexdigest(),
               'diagnosticSha256': {name: hashlib.sha256(data).hexdigest() for name, data in raw_records.items()},
               'registeredExecution': False, 'reviewDecision': 'pending-separate-stable-harness-manifest-review',
               'boundary': 'Plan preparation only; no fixture copies, grants, runtime calls or registered measurements.'}
    with target.open('xb') as stream:
        stream.write(raw)
    with receipt_path.open('xb') as stream:
        stream.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
    print(json.dumps({'status': 'prepared-review-pending', 'output': str(target),
                      'manifestSha256': receipt['manifestSha256'], 'registeredExecution': False}))
    return 0


def prepare_runtime_callback(plan: dict, controlled_child_scope: bool = False):
    """Preconstruct every private copy before the engine starts its dispatch clock.

    This is a library preparation operation, not CLI execution or approval. It
    retains owned fixture inputs for inspection; each runtime call cleans only
    its own newly-created sibling runtime root. Trusted local POSIX scope only;
    no hostile same-UID or source-rights/authentication guarantee.
    """
    raw_plan = encode_trial_plan(plan)
    state = _candidate_state()
    if plan['candidateCommit'] != state['candidateCommit']:
        raise ValueError('trial plan candidate differs from current code')
    for row in plan['admissionRecords']:
        if row['status'] != 'excluded-by-pinned-cap' and row.get('diagnosticInputHashes') != state['inputs']:
            raise ValueError('admission code inputs differ from exact candidate inventory')
    root = _destination(Path(plan['destinationRoot']))
    if root.is_relative_to(ROOT.resolve()):
        raise ValueError('private preparation root is inside candidate')
    start, cpu = time.monotonic_ns(), time.process_time_ns()
    root.mkdir(mode=0o700, exist_ok=False)
    fixtures, descriptors, fingerprints = {}, {}, {}
    for block in plan['blocks']:
        for pair in block['pairs']:
            for descriptor in pair['treatments']:
                key = descriptor['fixturePath']
                base = Path(key).parent
                base.mkdir(mode=0o700, parents=True, exist_ok=False)
                expected = {**deepcopy(descriptor), 'blockId': block['blockId'],
                            'pairIndex': pair['pairIndex'], 'category': pair['category'],
                            'preparedBlock': deepcopy(block['preparedBlock'])}
                fixture = build_fixture(block['preparedBlock'], Path(key))
                fingerprint = source_fingerprint(Path(fixture['repository']))
                fixture['preparedSourceFingerprint'] = deepcopy(fingerprint)
                fixtures[key], descriptors[key], fingerprints[key] = fixture, expected, fingerprint
    if _candidate_state() != state or encode_trial_plan(plan) != raw_plan:
        raise ValueError('candidate or manifest changed during fixture preparation')
    record = {'version': 'spec022-private-trial-preparation-v1', **deepcopy(state),
              'manifestSha256': hashlib.sha256(raw_plan).hexdigest(), 'fixtureCopies': len(fixtures),
              'wallNs': time.monotonic_ns() - start, 'parentCpuNs': time.process_time_ns() - cpu,
              'sourceFingerprints': deepcopy(fingerprints), 'ownedRoot': str(root),
              'boundary': 'All fixture reconstruction is outside operational treatment intervals and 45-minute dispatch budget.',
              'retention': 'Prepared fixture inputs remain in owned root; runtime cleanup is limited to fresh sibling runtime roots.',
              'trustScope': 'Trusted local POSIX filesystem; no hostile same-UID guarantee.'}
    used = set()

    def unchanged():
        try:
            return _candidate_state() == state and encode_trial_plan(plan) == raw_plan
        except (ValueError, OSError, subprocess.SubprocessError):
            return False

    def callback(descriptor):
        # A callback may only consume a prepared exact descriptor once. No fixture
        # construction occurs here or inside registered treatment wall accounting.
        if type(descriptor) is not dict:
            return {'status': 'invalidated', 'reason': 'descriptor-invalid'}
        key = descriptor.get('fixturePath')
        if type(key) is not str or key not in fixtures or descriptor != descriptors[key] or key in used:
            return {'status': 'invalidated', 'reason': 'descriptor-unbound-or-reused'}
        used.add(key)
        fixture = fixtures[key]
        try:
            if not unchanged():
                return {'status': 'invalidated', 'reason': 'candidate-or-manifest-drift'}
            if source_fingerprint(Path(fixture['repository'])) != fingerprints[key]:
                return {'status': 'no-go', 'reason': 'prepared-source-mutation'}
            run_path, grant_path = Path(descriptor['runPath']), Path(descriptor['grantPath'])
            runtime_root = _destination(run_path.parent)
            if grant_path.parent != runtime_root:
                return {'status': 'invalidated', 'reason': 'runtime-path-binding-differs'}
            result = run_treatment(deepcopy(fixture), descriptor['mode'],
                                   controlled_child_scope=controlled_child_scope,
                                   treatment_root=runtime_root, run_leaf=run_path.name,
                                   grant_leaf=grant_path.name)
            if not unchanged():
                return {'status': 'invalidated', 'reason': 'candidate-or-manifest-drift', 'retainedSample': result}
            if source_fingerprint(Path(fixture['repository'])) != fingerprints[key]:
                return {'status': 'no-go', 'reason': 'prepared-source-mutation', 'retainedSample': result}
            return result
        except (UnsafeDiagnostic, InvalidUtilityFixture) as exc:
            return {'status': 'no-go', 'reason': str(exc)}
        except Exception as exc:
            error = {'type': type(exc).__name__, 'message': str(exc)}
            if not unchanged():
                return {'status': 'invalidated', 'reason': 'candidate-or-manifest-drift', 'error': error}
            try:
                if source_fingerprint(Path(fixture['repository'])) != fingerprints[key]:
                    return {'status': 'no-go', 'reason': 'prepared-source-mutation-on-error', 'error': error}
            except (UnsafeDiagnostic, OSError) as safety_error:
                return {'status': 'no-go', 'reason': str(safety_error), 'error': error}
            return {'status': 'inconclusive', 'error': error}

    return callback, record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--diagnostics', type=Path)
    parser.add_argument('--destination-root', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true', help='refused: separate stable harness review is required')
    parser.add_argument('--registered', action='store_true', help='refused: this CLI prepares plans only')
    args = parser.parse_args(argv)
    if args.execute or args.registered:
        print(json.dumps({'status': 'refused', 'reason': 'registered execution requires separate reviewed stable harness/manifest; this CLI prepares only'}), file=sys.stderr)
        return 2
    if any(value is None for value in (args.diagnostics, args.destination_root, args.output)):
        parser.error('--diagnostics, --destination-root and --output are required for preparation')
    try:
        return prepare_plan(args.manifest, args.diagnostics, args.destination_root, args.output)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({'status': 'refused', 'reason': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
