# SPDX-License-Identifier: AGPL-3.0-only
"""Frozen offline economic decisions. All plans and cost labels are simulated.

There is no worker, runtime preparation, grant or execution interface here.
Synthetic manifests exercise existing wave geometry, not Git effect verification.
"""
from copy import deepcopy

from .forecast_baselines import predict_baseline, predict_regression
from .forecast_data import ForecastError, digest, require, integer
from .forecast_evaluation import _offline_rosters, _simulate_chronos, freeze_offline_evaluation
from .forecast_outputs import envelope
from .forecast_policy import advise
from .runtime_scheduler import _geometry

_SHAPES = ('independent', 'dependency-chain', 'conflict', 'unknown-effects')
_COST_LAW = {
    'version': 'agent-braid-synthetic-decision-cost-law-v1',
    'operationUnit': 'ms', 'outputUnit': 'ns', 'nsPerMs': 1000000,
    'serialLoadPenaltyNs': 1000000, 'parallelLoadPenaltyNs': 8000000,
    'parallelSetupNs': 5000000, 'mappingNs': 100000,
    'forecastNs': {'serial': 0, 'persistence': 10000, 'ewma': 20000, 'chronos-simulated': 500000},
}


def _paired_cases(signals, operations, evaluation, shapes):
    expected = freeze_offline_evaluation(signals, operations, simulated_statuses=evaluation.get('simulatedStatuses'))
    require(evaluation == expected, 'frozen-evaluation-drift')
    signals, operations = _offline_rosters(signals, operations)
    require(type(shapes) is dict and set(shapes) <= {s['episodeGroup'] for s in signals}, 'invalid-decision-shapes')
    require(all(shape in _SHAPES for shape in shapes.values()), 'invalid-decision-shapes')
    cases = []
    for partition in ('development', 'calibration', 'holdout'):
        left = [s for s in signals if s['partition'] == partition]
        right = [o for o in operations if o['partition'] == partition]
        require(len(left) == len(right), 'unpaired-decision-partition')
        for signal, operation in zip(left, right):
            shape = shapes.get(signal['episodeGroup'], 'independent')
            # Strip future labels before any candidate construction or predictor.
            inputs = {'window': signal['window'], 'resource': signal['resource'],
                      'features': operation['features'], 'featureNames': operation['featureNames'],
                      'operationGroup': operation['episodeGroup'], 'availableAtNs': operation['availableAtNs'],
                      'partition': partition, 'shape': shape}
            require(inputs['availableAtNs'] <= inputs['window']['cutoffNs'], 'future-operation-descriptors')
            labels = {'load': signal['actual'][0], 'durationMs': operation['outcome']}
            cases.append((deepcopy(inputs), labels))
    return cases


def _candidate_set(inputs, selection):
    """Make both synthetic alternatives before scoring, using runtime geometry."""
    window, resource, shape = inputs['window'], inputs['resource'], inputs['shape']
    count = inputs['features'][1]
    operations, steps = [], []
    for i in range(count):
        name = 'op'+str(i)
        path = 'shared.txt' if shape == 'conflict' else name+'.txt'
        operations.append({'instanceId': name, 'attemptId': name+'-attempt', 'declaredWrites': [path],
                           'dependencies': ['op'+str(i-1)] if i and (inputs['features'][2] == 1 or shape == 'dependency-chain') else []})
        steps.append({'operationId': name, 'sourceCommit': digest({'syntheticCommit': i}),
                      'patchDigest': digest({'syntheticPatch': i}), 'inputTree': digest({'syntheticTree': i}),
                      'commit': digest({'syntheticResult': i}),
                      'effects': [{'path': path, 'beforeMode': '100644', 'beforeBlob': digest({'syntheticBlob': i})}]})
    manifest = {'request': {'operations': operations, 'order': [o['instanceId'] for o in operations],
                            'baseRevision': digest({'syntheticBase': 1})},
                'steps': steps, 'repositoryId': digest({'syntheticRepository': inputs['operationGroup']})}
    waves, _ = _geometry(manifest)
    features = list(inputs['features'])
    # Negative shapes may add restrictions, never erase cutoff-known dependencies.
    base = max(1, round(predict_regression(selection['regression'], features)*_COST_LAW['nsPerMs']))
    descriptors = {'version': 'agent-braid-synthetic-manifest-v1', 'manifest': manifest,
                   'features': features, 'inputDigest': digest(window), 'shape': shape,
                   'resourceReceiptDigest': digest(resource), 'cutoffNs': window['cutoffNs']}
    candidates = []
    for mode in ('serial', 'parallel'):
        reasons = []
        if shape == 'unknown-effects': reasons.append('synthetic-effects-unknown')
        if mode not in resource['allowedModes']: reasons.append('resource-mode-unavailable')
        if count > resource['caps']['operations']: reasons.append('resource-capacity-exceeded')
        if mode == 'parallel' and (max(map(len, waves)) < 2 or resource['maxWorkers'] < 2):
            reasons.append('no-admissible-parallel-wave')
        plan = {'version': 'agent-braid-synthetic-action-plan-v1', 'identityKind': 'synthetic-plan',
                'descriptors': descriptors, 'mode': mode, 'waves': waves if mode == 'parallel' else [[o['instanceId']] for o in operations]}
        candidates.append({'id': mode, 'mode': mode, 'planDigest': digest(plan),
                           'baseWallNs': base if mode == 'serial' else max(1, round(base/count))+_COST_LAW['parallelSetupNs'],
                           'loadPenaltyNsPerUnit': _COST_LAW[mode+'LoadPenaltyNs'], 'eligible': not reasons,
                           'identityKind': 'synthetic-plan', 'reasonCodes': reasons, 'plan': plan})
    return candidates


def _forecast(inputs, method, selection, status='forecast'):
    window = inputs['window']
    if method == 'chronos-simulated':
        result = _simulate_chronos(window, 1, status)
    else:
        result = predict_baseline(window, 1, method=method, alpha=selection['alpha'])
    # Build a fresh explicitly synthetic envelope: do not mutate measured timing
    # receipts. The enclosing report supplies the nonzero synthetic cost law.
    return envelope(window, 1, model_digest=result['modelDigest'], status=result['status'],
                    quantiles=result['quantiles'], reasons=result['reasonCodes'])


def _advice(inputs, candidates, selection, policy, method, *, reference='serial', mode='consultative', status='forecast'):
    # Serial reference deliberately uses no future forecast; its proposal is off.
    forecast = _forecast(inputs, 'persistence' if method == 'serial' else method, selection, status)
    window = inputs['window']
    request = {'version': 'agent-braid-advice-request-v1', 'mode': 'off' if method == 'serial' else mode,
               'window': window, 'forecast': forecast, 'resource': inputs['resource'],
               'resourceDigest': digest(inputs['resource']), 'nowNs': window['cutoffNs'],
               'expiresNs': window['cutoffNs']+window['stepNs'], 'referenceMode': reference,
               'catalogue': {'sourceKind': 'synthetic', 'candidates': [
                   {k: c[k] for k in ('id', 'mode', 'planDigest', 'baseWallNs', 'loadPenaltyNsPerUnit', 'eligible')}
                   for c in candidates]},
               'policy': {**policy, 'advisoryOverheadNs': _COST_LAW['mappingNs']+_COST_LAW['forecastNs'][method]}}
    return request, advise(request)


def _simulated_label_cost(inputs, labels, action, method):
    """Future fixture label used ONLY after a decision or for development scoring."""
    duration = labels['durationMs']*_COST_LAW['nsPerMs']
    if action == 'parallel': duration = duration/inputs['features'][1]+_COST_LAW['parallelSetupNs']
    return duration+_COST_LAW[action+'LoadPenaltyNs']*labels['load']+_COST_LAW['mappingNs']+_COST_LAW['forecastNs'][method]


def freeze_decision_policy(signals, operations, *, evaluation, shapes=None):
    """Freeze H1 economic mapping/reference on development fixture costs only.

    Requires the exact SPEC-036/T003 evaluation plan and recipes. At most 32
    signals and operations, paired deterministically within each partition.
    Shapes change synthetic descriptors only; they do not admit runtime effects.
    Hashes are integrity commitments, never source/compute/launch approval.
    """
    require(type(evaluation) is dict, 'invalid-offline-plan')
    shapes = {} if shapes is None else deepcopy(shapes)
    cases = _paired_cases(signals, operations, evaluation, shapes)
    development = [(i, labels) for i, labels in cases if i['partition'] == 'development']
    selection = evaluation['selection']
    policies = [{'version': 1, 'partition': 'development', 'targetId': 'load', 'unit': 'count',
                 'minimumRatio': ratio, 'maximumIntervalWidth': width}
                for ratio in (1.0, 1.1) for width in (0.0, 100.0)]
    prepared = [(inputs, labels, _candidate_set(inputs, selection)) for inputs, labels in development]

    def score(method, policy, reference_method='serial', reference_policy=None):
        total = 0
        for inputs, labels, candidates in prepared:
            reference_action = 'serial'
            if reference_policy is not None:
                _, baseline = _advice(inputs, candidates, selection, reference_policy, reference_method)
                reference_action = baseline['selectedAction']
            status = evaluation['simulatedStatuses'].get(inputs['window']['episodeGroup']+'/1', 'forecast')
            _, advice = _advice(inputs, candidates, selection, policy, method,
                                reference=reference_action, status=status if method == 'chronos-simulated' else 'forecast')
            total += _simulated_label_cost(inputs, labels, advice['selectedAction'], method)
        return total

    # Each cheap method gets its own best development config BEFORE the neural
    # stand-in's mapper is tuned. It cannot pick a weaker shared reference.
    reference_scores = []
    for method in ('serial', 'persistence', 'ewma'):
        policy = min(policies, key=lambda p: (score(method, p), p['minimumRatio'], p['maximumIntervalWidth']))
        reference_scores.append({'method': method, 'simulatedFullWallNs': score(method, policy), 'policy': policy})
    best_reference = min(reference_scores, key=lambda r: (r['simulatedFullWallNs'], r['method']))
    reference = best_reference['method']
    policy = min(policies, key=lambda p: (score('chronos-simulated', p, reference, best_reference['policy']),
                                         p['minimumRatio'], p['maximumIntervalWidth']))
    result = {'version': 'agent-braid-synthetic-decision-policy-v1', 'evaluationPlanDigest': evaluation['planDigest'],
              'costLawDigest': digest(_COST_LAW), 'shapes': shapes,
              'selection': {'partition': 'development', 'criterion': 'synthetic-full-wall-cost',
                            'developmentDigest': digest(development), 'referenceMethod': reference, 'referencePolicy': best_reference['policy'],
                            'referenceScores': reference_scores, 'policy': policy},
              'provenance': 'synthetic-simulation', 'executionAuthorization': False}
    result['policyDigest'] = digest(result)
    return result


def simulate_decisions(signals, operations, *, evaluation, frozen, mode='shadow'):
    """Map all frozen origins without running an arm; retain every refusal.

    Shadow keeps the development-selected reference. Simulated later cost labels
    are separated from inputs; they never represent observed alternate outcomes.
    Synthetic advice cannot pass the existing runtime consumption boundary.
    """
    require(mode in ('off', 'shadow', 'consultative'), 'capability-not-promoted')
    require(type(frozen) is dict, 'invalid-decision-policy')
    expected = freeze_decision_policy(signals, operations, evaluation=evaluation, shapes=frozen.get('shapes'))
    require(frozen == expected, 'frozen-decision-policy-drift')
    cases = _paired_cases(signals, operations, evaluation, frozen['shapes'])
    rows, labels = [], []
    for inputs, outcome in cases:
        window = inputs['window']; candidates = _candidate_set(inputs, evaluation['selection'])
        row = {'episodeGroup': window['episodeGroup'], 'partition': inputs['partition'],
               'cutoffNs': window['cutoffNs'], 'inputDigest': digest(inputs), 'policyDigest': frozen['policyDigest'],
               'evaluationPlanDigest': evaluation['planDigest'], 'candidates': candidates,
               'status': 'refused', 'reasonCodes': [], 'request': None, 'advice': None,
               'arms': [{'arm': arm, 'action': None, 'planDigest': None,
                         'status': 'not-mapped-refused', 'executionAuthorization': False}
                        for arm in ('serial-reference', 'non-model-reference', 'forecast-choice')]}
        try:
            reference_method = frozen['selection']['referenceMethod']; policy = frozen['selection']['policy']
            _, reference = _advice(inputs, candidates, evaluation['selection'], frozen['selection']['referencePolicy'], reference_method)
            status = evaluation['simulatedStatuses'].get(window['episodeGroup']+'/1', 'forecast')
            request, advice = _advice(inputs, candidates, evaluation['selection'], policy, 'chronos-simulated',
                                      reference=reference['selectedAction'], mode=mode, status=status)
            row.update(status='mapped', request=request, advice=advice, arms=[])
            for arm, action, method in (('serial-reference', 'serial', 'serial'),
                                       ('non-model-reference', reference['selectedAction'], reference_method),
                                       ('forecast-choice', advice['selectedAction'], 'chronos-simulated')):
                row['arms'].append({'arm': arm, 'action': action, 'planDigest': next(c['planDigest'] for c in candidates if c['id'] == action),
                                    'status': 'not-executed-simulation', 'executionAuthorization': False})
                labels.append({'episodeGroup': row['episodeGroup'], 'arm': arm,
                               'simulatedFullWallNs': _simulated_label_cost(inputs, outcome, action, method),
                               'provenance': 'synthetic-simulation-not-observed'})
        except ForecastError as error:
            row['reasonCodes'] = [str(error)]
        row['receiptDigest'] = digest(row); rows.append(row)
    report = {'version': 'agent-braid-synthetic-decisions-v1', 'policyDigest': frozen['policyDigest'],
              'evaluationPlanDigest': evaluation['planDigest'], 'mode': mode, 'decisions': rows,
              'simulatedLabels': labels, 'costBoundary': 'synthetic-cost-law-not-observed',
              'provenance': 'synthetic-simulation', 'utilityAccepted': False,
              'realWorkloadEvidence': False, 'executionAuthorization': False}
    report['receiptDigest'] = digest(report)
    return report


def validate_synthetic_decision(receipt, signals, operations, *, evaluation, frozen, mode, now_ns):
    """Recompute the frozen synthetic binding at use; return no execution grant.

    A matching checksum alone cannot validate a changed plan, exclusion, policy,
    forecast or manifest. The complete fixture chain is recomputed and compared.
    """
    from .forecast_policy import validate_advice
    integer(now_ns)
    require(type(receipt) is dict, 'invalid-decision-receipt')
    report = simulate_decisions(signals, operations, evaluation=evaluation, frozen=frozen, mode=mode)
    expected = next((row for row in report['decisions'] if row['episodeGroup'] == receipt.get('episodeGroup')), None)
    require(expected is not None and receipt == expected, 'synthetic-decision-binding-drift')
    require(expected['status'] == 'mapped', 'synthetic-decision-refused')
    require(now_ns >= expected['cutoffNs'], 'decision-not-yet-available')
    validate_advice(expected['advice'], expected['request'], now_ns=now_ns)
    return deepcopy(expected)
