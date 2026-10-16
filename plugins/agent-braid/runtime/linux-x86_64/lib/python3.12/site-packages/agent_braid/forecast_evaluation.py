# SPDX-License-Identifier: AGPL-3.0-only
"""Forecast error/coverage accounting with explicit unavailable denominators."""
from copy import deepcopy
from .forecast_baselines import fit_regression, predict_regression, select_ewma, predict_baseline
from .forecast_data import keys, require, finite, digest
from .forecast_outputs import STATUSES, envelope
from .forecast_windows import validate_partitions

def rolling_origin_baselines(episodes,*,horizons=(1,5,10)):
    """Freeze an EWMA alpha on development episodes, then score later partitions.

    Each supplied episode is a separately registered causal origin with its
    future labels stored outside the window. No label enters prediction.
    This numeric procedure does not confer source or experiment admission.
    """
    from .forecast_baselines import predict_baseline
    from .forecast_data import digest
    from .forecast_lab import signal_episode
    from .forecast_windows import validate_partitions
    require(type(episodes) is list and 1<=len(episodes)<=4096,'invalid-evaluation-roster')
    require(tuple(horizons)==(1,5,10),'unsupported-evaluation-horizons')
    groups=set();development=[];partitions=[]
    for episode in episodes:
        require(episode.get('provenance')=='synthetic-simulation','evaluation-source-not-admitted')
        group=episode['episodeGroup'];require(group not in groups,'duplicate-independent-episode');groups.add(group)
        require(episode['partition'] in ('development','calibration','holdout'),'unsupported-partition')
        recipe=episode['recipe'];keys(recipe,('family','seed','partition','version'))
        require(recipe['partition']==episode['partition'] and recipe['version']==1,'episode-recipe-drift')
        expected=signal_episode(recipe['family'],seed=recipe['seed'],partition=recipe['partition'])
        require(episode['episodeGroup']==expected['episodeGroup'] and digest(episode['window'])==digest(expected['window']),'episode-window-binding-drift')
        require(episode['actual']==expected['actual'],'synthetic-label-binding-drift')
        window=episode['window'];partitions.append({'episodeGroup':group,'partition':episode['partition'],
            'startNs':window['gridStartNs'],'endNs':window['cutoffNs']+10*window['stepNs']})
        require(type(episode['actual']) is list and len(episode['actual'])==10,'invalid-future-labels')
        for value in episode['actual']:finite(value)
        if episode['partition']=='development':development.append(episode)
    validate_partitions(partitions);require(development,'development-roster-required')
    losses=[]
    for alpha in (.1,.3,.5,.9):
        errors=[]
        for episode in development:
            prediction=predict_baseline(episode['window'],10,method='ewma',alpha=alpha)
            if prediction['status']=='forecast':errors.extend(abs(a-b) for a,b in zip(episode['actual'],prediction['median'][0]))
        require(errors,'no-development-forecasts');losses.append((sum(errors)/len(errors),alpha))
    alpha=min(losses)[1]
    selection={'partition':'development','alpha':alpha,'developmentRosterDigest':digest([e['recipe'] for e in development]),'criterion':'mae','frozen':True}
    rows={}
    for partition in ('development','calibration','holdout'):
        for method in ('persistence','ewma'):
            for horizon in horizons:
                observations=[]
                for episode in episodes:
                    if episode['partition']!=partition:continue
                    forecast=predict_baseline(episode['window'],horizon,method=method,alpha=alpha)
                    observations.extend({'status':forecast['status'],'actual':episode['actual'][i],
                                         'quantiles':forecast['quantiles'][0][i] if forecast['status']=='forecast' else None} for i in range(horizon))
                if observations:rows[f'{partition}/{method}/{horizon}']=forecast_metrics(observations)
    return {'version':'agent-braid-synthetic-rolling-origin-v1','selection':selection,'metrics':rows,
            'independentEpisodes':len(episodes),'provenance':'synthetic-simulation','utilityAccepted':False,'realWorkloadEvidence':False}

def forecast_metrics(rows,*,scale=None):
    require(type(rows) is list and 1<=len(rows)<=4096,'invalid-evaluation-roster')
    if scale is not None:finite(scale);require(scale>0,'undefined-scale')
    absolute=[];pinball=[];widths=[];covered=0;unavailable=0
    for row in rows:
        keys(row,('status','actual','quantiles'))
        require(row['status'] in ('forecast','refused','unavailable','timed-out','cancelled'),'invalid-evaluation-status')
        if row['status']!='forecast':
            require(row['quantiles'] is None,'invalid-unavailable-outcome');unavailable+=1;continue
        actual=finite(row['actual']);q=row['quantiles'];require(type(q) is list and len(q)==3,'invalid-evaluation-quantiles')
        for value in q:finite(value)
        require(q[0]<=q[1]<=q[2],'crossed-evaluation-quantiles')
        absolute.append(abs(actual-q[1]));widths.append(q[2]-q[0]);covered+=int(q[0]<=actual<=q[2])
        pinball.append(sum(max(level*(actual-prediction),(level-1)*(actual-prediction)) for level,prediction in zip((.1,.5,.9),q))/3)
    count=len(absolute);mae=None if not count else sum(absolute)/count
    return {'intended':len(rows),'forecasted':count,'unavailable':unavailable,'actionableCoverage':count/len(rows),
            'mae':mae,'scaledError':None if scale is None or mae is None else mae/scale,
            'scaledErrorReason':'development-scale-undefined' if scale is None else None,
            'pinballLoss':None if not count else sum(pinball)/count,'nominalInterval':.8,
            'observedIntervalCoverage':None if not count else covered/count,'intervalWidth':None if not count else sum(widths)/count}


# This offline roster deliberately has no worker/adapter/provider injection.
# Simulated Chronos exercises the upstream axis/median contract, not its model.
_PARTITIONS = ('development', 'calibration', 'holdout')
_HORIZONS = (1, 5, 10)
_SIMULATOR = digest({'backend': 'chronos-simulated', 'algorithm': 'last-observed-slope', 'version': 1})


def _offline_rosters(episodes, operations):
    """Bind the complete synthetic recipes, including cutoff and resource bytes."""
    from .forecast_lab import signal_episode, operation_episode
    normalized = []
    intervals = []
    groups = set()
    for roster, kind in ((episodes, 'signal'), (operations, 'operation')):
        require(type(roster) is list and 1 <= len(roster) <= 32, 'invalid-offline-roster')
        ordered = []
        for row in roster:
            require(type(row) is dict and type(row.get('recipe')) is dict, 'invalid-offline-episode')
            recipe = row['recipe']
            if kind == 'signal':
                keys(recipe, ('family', 'seed', 'partition', 'version'))
                expected = signal_episode(recipe['family'], seed=recipe['seed'], partition=recipe['partition'])
                start = expected['window']['gridStartNs']
                end = expected['window']['cutoffNs']+10*expected['window']['stepNs']
            else:
                keys(recipe, ('seed', 'partition', 'version'))
                expected = operation_episode(seed=recipe['seed'], partition=recipe['partition'])
                start, end = expected['availableAtNs'], expected['outcomeAtNs']
            require(digest(row) == digest(expected), 'offline-episode-binding-drift')
            group = row['episodeGroup']
            require(group not in groups, 'duplicate-independent-episode')
            groups.add(group)
            intervals.append({'episodeGroup': group, 'partition': row['partition'], 'startNs': start, 'endNs': end})
            ordered.append(deepcopy(row))
        require({r['partition'] for r in ordered} == set(_PARTITIONS), 'offline-partitions-required')
        normalized.append(sorted(ordered, key=lambda r: (_PARTITIONS.index(r['partition']), r['episodeGroup'])))
    validate_partitions(intervals)
    return normalized


def _positive_scale(values):
    scale = sum(values)/len(values) if values else 0
    return scale if scale > 0 else None


def freeze_offline_evaluation(episodes, operations, *, simulated_statuses=None):
    """Freeze a bounded synthetic evaluation without scoring later partitions.

    Inputs must be exact ``signal_episode`` / ``operation_episode`` recipes,
    with all three chronological partitions and at most 32 episodes per kind.
    Development alone selects EWMA and fits ridge=1 operation regression, its
    heuristic residual width and both scaled-error denominators. Failure scripts
    are frozen before scoring. This is an integrity receipt, not launch approval.
    """
    episodes, operations = _offline_rosters(episodes, operations)
    statuses = {} if simulated_statuses is None else deepcopy(simulated_statuses)
    require(type(statuses) is dict, 'invalid-simulated-statuses')
    slots = {f"{e['episodeGroup']}/{h}" for e in episodes for h in _HORIZONS}
    require(set(statuses) <= slots and all(s in STATUSES for s in statuses.values()), 'invalid-simulated-statuses')
    development = [e for e in episodes if e['partition'] == 'development']
    selected = select_ewma([{'partition': 'development', 'window': e['window'], 'actual': e['actual']} for e in development])
    training = [{'partition': 'development', 'features': e['features'], 'outcome': e['outcome']}
                for e in operations if e['partition'] == 'development']
    model = fit_regression(training, ridge=1.0)
    residuals = [abs(r['outcome']-predict_regression(model, r['features'])) for r in training]
    history_differences = []
    for episode in development:
        values = [v for v in episode['window']['values'][0] if v is not None]
        history_differences.extend(abs(b-a) for a, b in zip(values, values[1:]))
    mean = sum(r['outcome'] for r in training)/len(training)
    selection = {'partition': 'development', 'alpha': selected['alpha'], 'regression': model,
                 'regressionWidth': max(residuals), 'signalScale': _positive_scale(history_differences),
                 'operationScale': _positive_scale([abs(r['outcome']-mean) for r in training]),
                 'developmentDigest': digest({'signals': development, 'operations': training})}
    result = {'version': 'agent-braid-offline-evaluation-plan-v1',
              'roster': [{'kind': kind, 'episodeGroup': e['episodeGroup'], 'partition': e['partition'], 'digest': digest(e)}
                         for kind, roster in (('signal', episodes), ('operation', operations)) for e in roster],
              'selection': selection, 'simulatorDigest': _SIMULATOR,
              'simulatedStatuses': statuses, 'provenance': 'synthetic-simulation', 'executionAuthorization': False}
    result['planDigest'] = digest(result)
    return result


def _simulate_chronos(window, horizon, status):
    """Causal numerical stand-in using Chronos' quantile/median axis normalizer."""
    from .forecast_chronos import normalize_output
    from .forecast_chronos_inputs import translate_inputs
    translate_inputs(window, horizon)
    if status != 'forecast':
        return envelope(window, horizon, model_digest=_SIMULATOR, status=status, reasons=('simulated-'+status,))
    quantiles = []
    for row in window['values']:
        observed = [(i, v) for i, v in enumerate(row) if v is not None]
        if not observed:
            return envelope(window, horizon, model_digest=_SIMULATOR, status='unavailable', reasons=('no-observed-history',))
        index, last = observed[-1]
        slope = 0 if len(observed) < 2 else (last-observed[-2][1])/(index-observed[-2][0])
        points = [last+slope*(len(row)+i-index) for i in range(horizon)]
        quantiles.append([[p-abs(slope), p, p+abs(slope)] for p in points])
    return normalize_output(window, horizon, [quantiles], [[[q[1] for q in row] for row in quantiles]], model_digest=_SIMULATOR)


def evaluate_offline(episodes, operations, *, frozen):
    """Score the exact frozen synthetic population; retain every attempted origin.

    Recompute the development-only plan to reject even re-signed tuning or roster
    edits. No later outcome enters a predictor or transform. Aggregate temporal
    horizons separately from scalar operation duration. Costs/utility, model
    conformance, real sources and scientific interpretation remain outside scope.
    """
    require(type(frozen) is dict, 'invalid-offline-plan')
    expected = freeze_offline_evaluation(episodes, operations, simulated_statuses=frozen.get('simulatedStatuses'))
    require(frozen == expected, 'frozen-evaluation-drift')
    episodes, operations = _offline_rosters(episodes, operations)
    selection = expected['selection']
    receipts, grouped = [], {}

    def record(episode, method, target, unit, horizon, kind, forecast, observations, scale):
        group = episode['resource']['profileId'] if kind == 'temporal' else episode['resourceGroup']
        identity = (episode['partition'], method, target, unit, horizon, kind, group)
        grouped.setdefault(identity, {'observations': [], 'scale': scale})['observations'].extend(observations)
        receipts.append({'episodeGroup': episode['episodeGroup'], 'partition': episode['partition'],
                         'method': method, 'targetId': target, 'unit': unit, 'horizon': horizon,
                         'horizonKind': kind, 'resourceGroup': group,
                         'inputDigest': forecast['inputDigest'], 'modelDigest': forecast['modelDigest'],
                         'resourceReceiptDigest': forecast['resourceReceiptDigest'],
                         'cutoffNs': episode['window']['cutoffNs'] if kind == 'temporal' else episode['cutoffNs'],
                         'status': forecast['status'], 'reasonCodes': forecast['reasonCodes'],
                         'intervalCalibration': 'not-evaluated', 'observations': observations,
                         'scores': forecast_metrics(observations, scale=scale), 'provenance': 'synthetic-simulation'})

    for episode in episodes:
        window = episode['window']
        for method in ('persistence', 'ewma', 'chronos-simulated'):
            for horizon in _HORIZONS:
                if method == 'chronos-simulated':
                    status = expected['simulatedStatuses'].get(f"{episode['episodeGroup']}/{horizon}", 'forecast')
                    forecast = _simulate_chronos(deepcopy(window), horizon, status)
                else:
                    forecast = predict_baseline(window, horizon, method=method, alpha=selection['alpha'])
                observations = [{'status': forecast['status'], 'actual': episode['actual'][i],
                                 'quantiles': forecast['quantiles'][0][i] if forecast['status'] == 'forecast' else None}
                                for i in range(horizon)]
                record(episode, method, 'load', 'count', horizon, 'temporal', forecast, observations, selection['signalScale'])
    for episode in operations:
        point = predict_regression(selection['regression'], episode['features'])
        width = selection['regressionWidth']
        forecast = {'inputDigest': digest({k: v for k, v in episode.items() if k not in ('outcome', 'outcomeAtNs')}),
                    'modelDigest': selection['regression']['modelDigest'],
                    'resourceReceiptDigest': episode['resourceReceiptDigest'], 'status': 'forecast', 'reasonCodes': []}
        observations = [{'status': 'forecast', 'actual': episode['outcome'], 'quantiles': [point-width, point, point+width]}]
        record(episode, 'operation-regression', episode['targetId'], episode['unit'], 1, 'operation', forecast, observations, selection['operationScale'])
    metrics = []
    for identity, values in sorted(grouped.items()):
        partition, method, target, unit, horizon, kind, group = identity
        metrics.append({'partition': partition, 'method': method, 'targetId': target, 'unit': unit,
                        'horizon': horizon, 'horizonKind': kind, 'resourceGroup': group,
                        'scores': forecast_metrics(values['observations'], scale=values['scale'])})
    return {'version': 'agent-braid-offline-evaluation-report-v1', 'planDigest': expected['planDigest'],
            'selection': deepcopy(selection), 'metrics': metrics, 'receipts': receipts,
            'episodeIdentityCount': len(episodes)+len(operations), 'provenance': 'synthetic-simulation',
            'utilityAccepted': False, 'realWorkloadEvidence': False, 'executionAuthorization': False}
