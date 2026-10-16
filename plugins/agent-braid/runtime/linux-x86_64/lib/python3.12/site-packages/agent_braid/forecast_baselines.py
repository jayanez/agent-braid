# SPDX-License-Identifier: AGPL-3.0-only
"""Inexpensive causal baselines; operation regression is not a time-series model."""
from time import monotonic_ns
from .forecast_data import validate_window, require, finite, integer, keys, digest
from .forecast_outputs import envelope

def predict_baseline(window, horizon, *, method='persistence', alpha=.3):
    started=monotonic_ns(); window=validate_window(window)
    require(method in ('persistence','ewma'),'unknown-baseline'); finite(alpha); require(0<alpha<=1,'invalid-ewma-alpha')
    model=digest({'method':method,'alpha':alpha if method=='ewma' else None,'version':1})
    quantiles=[]
    for row in window['values']:
        observed=[value for value in row if value is not None]
        if not observed: return envelope(window,horizon,model_digest=model,status='unavailable',reasons=('no-observed-history',),started_ns=started)
        point=observed[-1]
        if method=='ewma':
            point=observed[0]
            for value in observed[1:]: point=alpha*value+(1-alpha)*point
        # This past-only empirical width is a heuristic, not calibrated coverage.
        width=max((abs(b-a) for a,b in zip(observed,observed[1:])),default=0)
        quantiles.append([[point-width,point,point+width] for _ in range(horizon)])
    return envelope(window,horizon,model_digest=model,quantiles=quantiles,started_ns=started)

def select_ewma(rows):
    require(type(rows) is list and 1<=len(rows)<=4096,'invalid-development-roster')
    errors={alpha:[] for alpha in (.1,.3,.5,.9)}
    for row in rows:
        keys(row,('partition','window','actual'));require(row['partition']=='development','holdout-tuning-prohibited')
        require(type(row['actual']) is list and len(row['actual']) in (1,5,10),'invalid-labels')
        for value in row['actual']:finite(value)
        for alpha in errors:
            pred=predict_baseline(row['window'],len(row['actual']),method='ewma',alpha=alpha)
            require(pred['status']=='forecast' and len(pred['median'])==1,'unavailable-development-forecast')
            errors[alpha].extend(abs(a-b) for a,b in zip(pred['median'][0],row['actual']))
    scores={alpha:sum(values)/len(values) for alpha,values in errors.items()}
    chosen=min(scores,key=lambda alpha:(scores[alpha],alpha))
    return {'version':'agent-braid-ewma-selection-v1','partition':'development','alpha':chosen,'mae':scores[chosen],'rosterDigest':digest(rows)}

def fit_regression(rows, *, ridge=1.0):
    require(type(rows) is list and 1<=len(rows)<=4096,'invalid-development-roster')
    finite(ridge); require(ridge>0,'invalid-ridge')
    width=None; design=[]; outcomes=[]
    for row in rows:
        keys(row,('partition','features','outcome'));require(row['partition']=='development','holdout-fitting-prohibited')
        features=row['features'];require(type(features) is list and 1<=len(features)<=8,'invalid-features')
        for value in features:finite(value)
        width=len(features) if width is None else width;require(len(features)==width,'mixed-features')
        design.append([1.0]+features);outcomes.append(finite(row['outcome']))
    n=width+1
    matrix=[[sum(row[i]*row[j] for row in design)+(ridge if i==j and i else 0) for j in range(n)]
            +[sum(row[i]*outcome for row,outcome in zip(design,outcomes))] for i in range(n)]
    for i in range(n):
        pivot=max(range(i,n),key=lambda j:abs(matrix[j][i]));matrix[i],matrix[pivot]=matrix[pivot],matrix[i]
        require(abs(matrix[i][i])>1e-12,'singular-regression')
        divisor=matrix[i][i];matrix[i]=[finite(value/divisor) for value in matrix[i]]
        for j in range(n):
            if i==j:continue
            factor=matrix[j][i];matrix[j]=[finite(a-factor*b) for a,b in zip(matrix[j],matrix[i])]
    result={'version':'agent-braid-operation-regression-v1','kind':'operation-regression','coefficients':[row[-1] for row in matrix],
            'ridge':ridge,'developmentDigest':digest(rows)}
    result['modelDigest']=digest(result);return result

def predict_regression(model, features):
    keys(model,('version','kind','coefficients','ridge','developmentDigest','modelDigest'))
    require(model['version']=='agent-braid-operation-regression-v1' and model['kind']=='operation-regression','unsupported-regression')
    require(model['modelDigest']==digest({k:v for k,v in model.items() if k!='modelDigest'}),'regression-drift')
    require(type(features) is list and 1<=len(features)<=8 and len(model['coefficients'])==len(features)+1,'invalid-features')
    for value in features+model['coefficients']:finite(value)
    return finite(sum(a*b for a,b in zip([1.0]+features,model['coefficients'])))
