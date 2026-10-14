# SPDX-License-Identifier: AGPL-3.0-only
"""Forecast error/coverage accounting with explicit unavailable denominators."""
from .forecast_data import keys,require,finite,integer

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
