# SPDX-License-Identifier: AGPL-3.0-only
"""Immutable synthetic paired plans; execution needs a separate matching review.

Structured local diagnostic records are not source-rights or reviewer identity
evidence. A review record's fields are checked, not authenticated by this module.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import time
import uuid

from .utility_fixtures import (
    PREPARED_MANIFEST_SHA256, _BLOCK_HASHES, _validate_block,
    validate_prepared_manifest,
)

DISPATCH_BUDGET_NS = 45 * 60 * 1_000_000_000
_OID = re.compile(r'[0-9a-f]{40}')
_PHASES = ('input', 'replay', 'preparation', 'grant', 'execution',
           'independent_verification', 'report_serialization', 'cleanup')
_CPU = ('parentCpuSeconds', 'completedChildUserCpuSeconds', 'completedChildSystemCpuSeconds')


class InvalidUtilityTrials(ValueError):
    """Trial preparation or a separate registration-review binding is invalid."""


def _require(condition, reason):
    if not condition:
        raise InvalidUtilityTrials(reason)


def _encode(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          allow_nan=False, ensure_ascii=True).encode()
    except (ValueError, TypeError, RecursionError) as exc:
        raise InvalidUtilityTrials('invalid trial JSON') from exc


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _valid_grant(value):
    if type(value) is not str:
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _request_matches(request, block):
    if type(request) is not dict:
        return False
    expected_operations = [
        {'instanceId': i['instanceId'], 'attemptId': i['instanceId'] + '-attempt',
         'source': {'kind': 'commit', 'revision': i['sourceCommit']},
         'dependencies': i['dependencies'], 'uncertainPaths': [], 'declaredWrites': [i['path']]}
        for i in block['operationIdentities']]
    return (set(request) == {'gitRuntimeRequestVersion', 'repository', 'baseRevision',
                              'expectedFinalTree', 'order', 'operations'}
            and request['gitRuntimeRequestVersion'] == '0.1.0-alpha'
            and type(request['repository']) is str and bool(request['repository'])
            and request['baseRevision'] == block['baseCommit']
            and request['expectedFinalTree'] == block['expectedFinalTree']
            and request['order'] == block['plannedOrder']
            and request['operations'] == expected_operations)


def _accounting_valid(accounting):
    """Check actual disjoint phase/counter records, never trust `complete` alone."""
    def integer(value):
        return type(value) is int and 0 <= value <= 2**63 - 1

    def optional(record, field, reasons, *, cpu=False):
        if field not in record or type(reasons) is not dict:
            return False
        value = record[field]
        if value is None:
            return type(reasons.get(field)) is str and bool(reasons[field].strip())
        if reasons.get(field) is not None:
            return False
        if not cpu:
            return integer(value)
        try:
            return type(value) in (int, float) and math.isfinite(value) and value >= 0
        except OverflowError:
            return False

    def span(record):
        if type(record) is not dict or not all(integer(record.get(f)) for f in ('startWallNs', 'endWallNs', 'wallNs')):
            return False
        if record['endWallNs'] - record['startWallNs'] != record['wallNs']:
            return False
        return all(optional(record, field, record.get('counterReasons'), cpu=True) for field in _CPU)

    if (type(accounting) is not dict or accounting.get('complete') is not True
            or accounting.get('outcome') != 'success' or accounting.get('errors') != []):
        return False
    outer, phases = accounting.get('outer'), accounting.get('phases')
    if not span(outer) or outer['wallNs'] <= 0 or type(phases) is not list or len(phases) != len(_PHASES):
        return False
    last, total = outer['startWallNs'], 0
    for name, phase in zip(_PHASES, phases):
        if (not span(phase) or phase.get('name') != name or phase.get('outcome') != 'success'
                or phase['startWallNs'] < last or phase['endWallNs'] > outer['endWallNs']):
            return False
        if not all(optional(phase, f, phase.get('counterReasons')) for f in
                   ('gitCommands', 'acceptedBudgetOutputBytes', 'observedCapturedOutputBytes', 'sampledScratchPeakBytes')):
            return False
        last, total = phase['endWallNs'], total + phase['wallNs']
    residual = accounting.get('residualWallNs')
    if not integer(residual) or residual != outer['wallNs'] - total:
        return False
    if not integer(accounting.get('gitBudgetCount')):
        return False
    for field in ('gitCommands', 'acceptedBudgetOutputBytes', 'observedCapturedOutputBytes',
                  'sampledScratchPeakBytes', 'processLifetimeRssBytes'):
        if not optional(accounting, field, accounting.get('optionalReasons')):
            return False
    for field in ('gitCommands', 'acceptedBudgetOutputBytes', *_CPU):
        whole = accounting.get(field) if field not in _CPU else outer[field]
        values = [p[field] for p in phases]
        if whole is not None and all(v is not None for v in values):
            tolerance = 1e-9 * max(1, whole) if field in _CPU else 0
            if sum(values) > whole + tolerance:
                return False
    workers = accounting.get('workerIntervals')
    if type(workers) is not dict:
        return False
    union, peak = workers.get('unionWallNs'), workers.get('peakOccupancy')
    if union is None or peak is None:
        if union is not None or peak is not None or type(workers.get('reason')) is not str or not workers['reason'].strip():
            return False
    elif not integer(union) or union > outer['wallNs'] or type(peak) is not int or not 0 <= peak <= 4:
        return False
    return True


def _sample_disposition(sample, block, mode):
    """Final envelope governs completion; missing mandatory safety checks stop."""
    if type(sample) is not dict:
        return 'invalid', 'missing-treatment-record'
    if sample.get('status') == 'invalidated' or sample.get('identityDrift') is True:
        return 'invalidated', 'immutable-input-drift'
    if sample.get('status') == 'no-go':
        return 'no-go', 'unsafe-treatment'
    if sample.get('status') != 'completed':
        return 'invalid', 'incomplete-treatment'
    operational = sample.get('operational')
    if type(operational) is not dict or operational.get('blockId') != block['blockId'] or operational.get('mode') != mode:
        return 'invalidated', 'treatment-identity-mismatch'
    digest = operational.get('planDigest')
    if (operational.get('immutableSourceUnchanged') is not True
            or not _valid_grant(operational.get('grantId'))
            or type(digest) is not str or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest)):
        return 'no-go', 'mandatory-source-or-grant-proof-failure'
    manifest = operational.get('runtimeManifest')
    if type(manifest) is not dict or not _request_matches(manifest.get('request'), block):
        return 'invalidated', 'runtime-input-identity-mismatch'
    verification = operational.get('independentVerification')
    if (type(verification) is not dict or verification.get('status') != 'verified-completed'
            or verification.get('resultTree') != block['expectedFinalTree']
            or operational.get('resultTree') != block['expectedFinalTree']
            or verification.get('completedOperations') != block['plannedOrder']):
        return 'no-go', 'mandatory-verification-tree-or-order-failure'
    accounting = sample.get('accounting')
    if not _accounting_valid(accounting):
        return 'invalid', 'missing-complete-accounting'
    outer = accounting.get('outer')
    wall = outer.get('wallNs') if type(outer) is dict else None
    if type(wall) is not int or not 0 < wall <= 2**63 - 1:
        return 'invalid', 'invalid-whole-wall-cost'
    return 'valid', None


def derive_admission_records(prepared_manifest: bytes, diagnostics: dict[str, bytes]) -> list[dict]:
    """Bind actual diagnostic bytes, retaining every named pre-registration row."""
    prepared = validate_prepared_manifest(prepared_manifest)
    _require(type(diagnostics) is dict, 'diagnostic records must be keyed by block')
    eligible = {b['blockId'] for b in prepared['blocks'] if not b['directNumericExclusions']}
    _require(set(diagnostics) == eligible, 'all four eligible diagnostic records are required')
    rows, common_candidate, common_inputs = [], None, None
    grants, plans = set(), set()
    for block in prepared['blocks']:
        name = block['blockId']
        if block['directNumericExclusions']:
            rows.append({'blockId': name, 'status': 'excluded-by-pinned-cap',
                         'exclusions': deepcopy(block['directNumericExclusions'])})
            continue
        raw = diagnostics[name]
        _require(type(raw) is bytes and len(raw) <= 16 * 1024 * 1024, 'invalid diagnostic bytes')
        try:
            record = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise InvalidUtilityTrials('invalid diagnostic JSON') from exc
        _require(type(record) is dict and record.get('recordVersion') == 'spec022-diagnostic-preparation-v1'
                 and record.get('purpose') == 'diagnostic-only'
                 and record.get('manifestSha256') == PREPARED_MANIFEST_SHA256
                 and record.get('registeredMeasurementExecuted') is False
                 and record.get('candidateInputsChangedDuringRun') is False,
                 'diagnostic identity or observation boundary differs')
        candidate = record.get('candidateCommit')
        _require(type(candidate) is str and bool(_OID.fullmatch(candidate)), 'diagnostic candidate is not immutable')
        inputs = record.get('inputs')
        _require(type(inputs) is dict and bool(inputs), 'diagnostic source bindings missing')
        if common_candidate is None:
            common_candidate, common_inputs = candidate, inputs
        _require(candidate == common_candidate and inputs == common_inputs, 'diagnostic candidates or inputs differ')
        pairs = record.get('diagnosticPairs')
        _require(type(pairs) is list and len(pairs) == 1 and type(pairs[0]) is dict and pairs[0].get('blockId') == name,
                 'diagnostic block or pair inventory differs')
        samples = pairs[0].get('samples')
        _require(type(samples) is list and len(samples) == 2, 'both diagnostic treatments required')
        dispositions = [_sample_disposition(s, block, mode) for s, mode in zip(samples, ['serial', 'parallel'])]
        _require(not any(d in {'no-go', 'invalidated'} for d, _ in dispositions),
                 'unsafe or invalidated diagnosis cannot become an exclusion')
        for sample, (disposition, _) in zip(samples, dispositions):
            if disposition == 'valid':
                grant = sample['operational']['grantId']
                digest = sample['operational']['planDigest']
                _require(grant not in grants and digest not in plans,
                         'diagnostic grants or plans reused across private treatments')
                grants.add(grant)
                plans.add(digest)
        admitted = all(d == 'valid' for d, _ in dispositions)
        _require(record.get('status') == ('prepared-or-diagnosed' if admitted else 'inconclusive'),
                 'diagnostic closing status differs')
        rows.append({'blockId': name, 'status': 'admitted' if admitted else 'excluded-by-diagnostic-refusal',
                     'diagnosticSha256': _sha(raw), 'diagnosticCandidateCommit': candidate,
                     'diagnosticInputHashes': deepcopy(inputs),
                     'exclusions': [] if admitted else [{'reason': r} for d, r in dispositions if d != 'valid']})
    return rows


def build_trial_plan(prepared_manifest: bytes, admissions: list[dict], *,
                     candidate_commit: str, destination_root: str) -> dict:
    prepared = validate_prepared_manifest(prepared_manifest)
    return _build_from_prepared(prepared, admissions, candidate_commit=candidate_commit,
                                destination_root=destination_root)


def _build_from_prepared(prepared, admissions, *, candidate_commit, destination_root):
    _require(type(candidate_commit) is str and bool(_OID.fullmatch(candidate_commit)), 'candidate must be full commit ID')
    _require(type(destination_root) is str and destination_root.startswith('/')
             and '\\' not in destination_root and '\0' not in destination_root
             and not any(p in {'.', '..'} for p in destination_root.split('/')),
             'destination root must be an absolute clean path')
    root = Path(destination_root).resolve()
    _require(type(admissions) is list and len(admissions) == 9
             and all(type(a) is dict for a in admissions), 'complete admission inventory required')
    _require([a.get('blockId') for a in admissions] == [b['blockId'] for b in prepared['blocks']], 'admission inventory order differs')
    blocks = []
    for block, admission in zip(prepared['blocks'], admissions):
        status = admission.get('status')
        if block['directNumericExclusions']:
            _require(admission == {'blockId': block['blockId'], 'status': 'excluded-by-pinned-cap',
                                  'exclusions': block['directNumericExclusions']}, 'pinned exclusions changed')
        else:
            _require(status in {'admitted', 'excluded-by-diagnostic-refusal'}
                     and type(admission.get('diagnosticSha256')) is str
                     and re.fullmatch(r'[0-9a-f]{64}', admission['diagnosticSha256'])
                     and type(admission.get('diagnosticCandidateCommit')) is str
                     and bool(_OID.fullmatch(admission['diagnosticCandidateCommit']))
                     and type(admission.get('diagnosticInputHashes')) is dict
                     and bool(admission['diagnosticInputHashes'])
                     and type(admission.get('exclusions')) is list
                     and (admission['exclusions'] == [] if status == 'admitted' else bool(admission['exclusions'])),
                     'admission proof is incomplete')
        pairs = []
        if status == 'admitted':
            for index in range(22):
                order = ['serial', 'parallel'] if index % 2 == 0 else ['parallel', 'serial']
                treatments = []
                for mode in order:
                    base = root / block['blockId'] / f'pair-{index:02d}' / mode
                    treatments.append({'mode': mode, 'fixturePath': str(base / 'fixture'),
                                       'runPath': str(base / 'runtime' / 'run'), 'grantPath': str(base / 'runtime' / 'grants')})
                pairs.append({'pairIndex': index, 'category': 'warmup' if index < 2 else 'measured',
                              'treatmentOrder': order, 'treatments': treatments})
        blocks.append({'blockId': block['blockId'], 'family': block['family'], 'status': status,
                       'preparedBlock': deepcopy(block), 'exclusions': deepcopy(admission['exclusions']), 'pairs': pairs})
    plan = {'version': 'spec022-paired-evaluation-plan-v1', 'candidateCommit': candidate_commit,
            'preparedManifestSha256': PREPARED_MANIFEST_SHA256, 'admissionRecords': deepcopy(admissions),
            'destinationRoot': str(root), 'dispatchBudgetNs': DISPATCH_BUDGET_NS,
            'blocks': blocks, 'registrationReview': 'separate-matching-stable-harness-review-required',
            'claimBoundary': 'Synthetic diagnostic observations only; no actual-workload utility, G4 or M4 acceptance.'}
    plan['planDigest'] = _sha(_encode(plan))
    return plan


def encode_trial_plan(plan: dict) -> bytes:
    """Canonical bytes are the exact manifest bytes bound by separate review."""
    _require(type(plan) is dict, 'plan must be an object')
    body = {k: v for k, v in plan.items() if k != 'planDigest'}
    _require(plan.get('planDigest') == _sha(_encode(body)), 'trial plan identity drift')
    _require(plan.get('version') == 'spec022-paired-evaluation-plan-v1'
             and type(plan.get('candidateCommit')) is str and bool(_OID.fullmatch(plan['candidateCommit']))
             and plan.get('preparedManifestSha256') == PREPARED_MANIFEST_SHA256,
             'trial plan candidate or manifest differs')
    _require(plan.get('dispatchBudgetNs') == DISPATCH_BUDGET_NS and type(plan['dispatchBudgetNs']) is int,
             'dispatch budget differs')
    blocks = plan.get('blocks')
    _require(type(blocks) is list and len(blocks) == 9 and all(type(b) is dict for b in blocks)
             and [b.get('blockId') for b in blocks] == list(_BLOCK_HASHES), 'fixed trial inventory differs')
    root = Path(plan['destinationRoot']).resolve()
    _require(str(root) == plan['destinationRoot'], 'trial destination root is not canonical')
    for block in blocks:
        prepared = _validate_block(block['preparedBlock'])
        _require(block['blockId'] == prepared['blockId'] and block['family'] == prepared['family'], 'block identity differs')
        _require(block['status'] in {'admitted', 'excluded-by-pinned-cap', 'excluded-by-diagnostic-refusal'},
                 'unknown admission disposition')
        if prepared['directNumericExclusions']:
            _require(block['exclusions'] == prepared['directNumericExclusions'], 'pinned exclusions changed')
        pairs = block.get('pairs')
        _require(type(pairs) is list and len(pairs) == (22 if block['status'] == 'admitted' else 0), 'pair denominator differs')
        _require(not prepared['directNumericExclusions'] or block['status'] == 'excluded-by-pinned-cap', 'known excluded block admitted')
        for index, pair in enumerate(pairs):
            order = ['serial', 'parallel'] if index % 2 == 0 else ['parallel', 'serial']
            treatments = []
            for mode in order:
                base = root / block['blockId'] / f'pair-{index:02d}' / mode
                treatments.append({'mode': mode, 'fixturePath': str(base / 'fixture'),
                                   'runPath': str(base / 'runtime' / 'run'), 'grantPath': str(base / 'runtime' / 'grants')})
            _require(pair == {'pairIndex': index, 'category': 'warmup' if index < 2 else 'measured',
                              'treatmentOrder': order, 'treatments': treatments}, 'pair order or destination differs')
    rebuilt = _build_from_prepared({'blocks': [b['preparedBlock'] for b in blocks]},
                                   plan.get('admissionRecords'), candidate_commit=plan['candidateCommit'],
                                   destination_root=plan['destinationRoot'])
    _require(plan == rebuilt, 'trial blocks contradict admission records or canonical inventory')
    return _encode(plan)


def run_trial_plan(plan: dict, treatment_callback, *, registration_review: dict,
                   monotonic_ns=time.monotonic_ns) -> dict:
    """Execute injected treatments only after a separate exact review binding.

    This function never creates grants or calls runtime APIs. Caller owns review
    identity/authentication and private preparation/cleanup; unit tests inject fakes.
    """
    raw = encode_trial_plan(plan)
    _require(type(registration_review) is dict and registration_review.get('decision') == 'approved'
             and registration_review.get('reviewedManifestSha256') == _sha(raw)
             and registration_review.get('reviewedCandidateCommit') == plan['candidateCommit'],
             'matching separate registration review required')
    _require(callable(treatment_callback), 'treatment callback required')
    frozen = deepcopy(plan)
    start = monotonic_ns()
    _require(type(start) is int and start >= 0, 'invalid dispatch clock')
    previous, stop = start, None
    output = {'version': 'spec022-paired-evaluation-record-v1', 'manifestSha256': _sha(raw),
              'candidateCommit': frozen['candidateCommit'], 'status': 'complete',
              'blocks': [], 'claimBoundary': frozen['claimBoundary']}
    seen_grants, seen_plans = set(), set()
    def unchanged():
        try:
            return _encode(plan) == raw
        except InvalidUtilityTrials:
            return False
    for block in frozen['blocks']:
        recorded = {k: deepcopy(v) for k, v in block.items() if k != 'pairs'}
        recorded['pairs'] = []
        for pair in block['pairs']:
            recorded_pair = {k: deepcopy(v) for k, v in pair.items() if k != 'treatments'}
            recorded_pair['treatments'] = []
            for descriptor in pair['treatments']:
                row = {**deepcopy(descriptor), 'status': 'unexecuted', 'reason': stop or 'not-dispatched', 'sample': None}
                if stop is None:
                    if not unchanged():
                        stop = 'identity-drift'
                    else:
                        now = monotonic_ns()
                        _require(type(now) is int and now >= previous, 'dispatch clock must be monotonic')
                        previous = now
                        if now - start >= DISPATCH_BUDGET_NS:
                            stop = 'dispatch-budget-exhausted'
                if stop is None:
                    call = {**deepcopy(descriptor), 'blockId': block['blockId'],
                            'pairIndex': pair['pairIndex'], 'category': pair['category'],
                            'preparedBlock': deepcopy(block['preparedBlock'])}
                    try:
                        sample = treatment_callback(call)
                        row['sample'] = deepcopy(sample)
                        disposition, reason = _sample_disposition(sample, block['preparedBlock'], descriptor['mode'])
                        if disposition == 'valid':
                            operation = sample['operational']
                            grant = operation.get('grantId')
                            digest = operation.get('planDigest')
                            if (operation['independentVerification'].get('runDirectory') != descriptor['runPath']
                                    or operation.get('immutableSourceUnchanged') is not True
                                    or not _valid_grant(grant) or grant in seen_grants
                                    or type(digest) is not str or not re.fullmatch(r'sha256:[0-9a-f]{64}', digest)
                                    or digest in seen_plans):
                                disposition, reason = 'no-go', 'private-destination-source-or-grant-proof-failure'
                            else:
                                seen_grants.add(grant)
                                seen_plans.add(digest)
                    except Exception as exc:
                        disposition, reason = 'invalid', 'callback-error'
                        row['error'] = {'type': type(exc).__name__, 'message': str(exc)}
                    row.update(status=disposition, reason=reason)
                    if disposition in {'no-go', 'invalidated'}:
                        stop = 'unsafe-treatment' if disposition == 'no-go' else 'identity-drift'
                    if not unchanged():
                        stop = 'identity-drift'
                    if stop is None:
                        # Let active work finish, but observe its closing cost even
                        # when no subsequent dispatch remains to check the clock.
                        now = monotonic_ns()
                        _require(type(now) is int and now >= previous, 'dispatch clock must be monotonic')
                        previous = now
                        if now - start >= DISPATCH_BUDGET_NS:
                            stop = 'dispatch-budget-exhausted'
                elif row['status'] == 'unexecuted':
                    row['reason'] = stop
                recorded_pair['treatments'].append(row)
            recorded['pairs'].append(recorded_pair)
        pairs = recorded['pairs']
        valid = sum(all(t['status'] == 'valid' for t in p['treatments']) for p in pairs)
        recorded['counts'] = {'intendedPairs': len(pairs), 'validPairs': valid,
                              'invalidPairs': sum(any(t['status'] in {'invalid', 'no-go', 'invalidated'} for t in p['treatments']) for p in pairs),
                              'unexecutedPairs': sum(any(t['status'] == 'unexecuted' for t in p['treatments']) for p in pairs),
                              'attemptedTreatments': sum(t['status'] != 'unexecuted' for p in pairs for t in p['treatments'])}
        recorded['medianPairedRatio'] = None
        if block['status'] != 'admitted':
            recorded['outcome'] = 'excluded'
        elif valid != 22:
            recorded['outcome'] = 'inconclusive'
        elif block['family'] == 'dependency-chain':
            recorded['outcome'] = 'complete-order-control'
        else:
            ratios = []
            for p in pairs[2:]:
                walls = {t['mode']: t['sample']['accounting']['outer']['wallNs'] for t in p['treatments']}
                ratios.append(walls['serial'] / walls['parallel'])
            median = statistics.median(ratios)
            _require(math.isfinite(median) and median > 0, 'invalid paired ratio')
            recorded['medianPairedRatio'] = median
            recorded['outcome'] = 'positive-synthetic-diagnostic' if median >= 1.10 else 'negative-synthetic-diagnostic'
        output['blocks'].append(recorded)
    output['stopReason'] = stop
    output['status'] = ('invalidated' if stop == 'identity-drift' else 'no-go' if stop == 'unsafe-treatment'
                        else 'incomplete' if stop or any(b['outcome'] == 'inconclusive' for b in output['blocks']) else 'complete')
    if output['status'] != 'complete':
        # An incomplete whole capture cannot retain a positive complete-protocol claim.
        for block in output['blocks']:
            if block['outcome'] == 'positive-synthetic-diagnostic':
                block['outcome'] = 'complete-block-diagnostic-only-incomplete-protocol'
    return output
