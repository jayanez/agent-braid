# SPDX-License-Identifier: AGPL-3.0-only
"""Bound numeric quantiles with explicit median and calibration semantics."""
from copy import deepcopy
from time import monotonic_ns
from .forecast_data import keys, require, integer, finite, pin, identifier, digest, validate_window, parse_record, canonical

VERSION='agent-braid-forecast-v1'
STATUSES=('forecast','refused','unavailable','timed-out','cancelled')

def envelope(window, horizon, *, model_digest, quantiles=None, status='forecast', reasons=(), started_ns=None):
    window=validate_window(window); integer(horizon); require(horizon in (1,5,10),'unsupported-horizon')
    pin(model_digest); require(status in STATUSES,'unsupported-status')
    if quantiles is not None:
        require(type(quantiles) is list and len(quantiles)==len(window['targetIds']),'invalid-output-shape')
        for row in quantiles:
            require(type(row) is list and len(row)==horizon,'invalid-output-shape')
            for triple in row:require(type(triple) is list and len(triple)==3,'invalid-output-shape')
    median=None if quantiles is None else [[triple[1] for triple in row] for row in quantiles]
    result={'version':VERSION,'sourceKind':window['sourceKind'],'inputDigest':digest(window),
            'resourceReceiptDigest':window['resourceReceiptDigest'],'partitionDigest':window['partitionDigest'],
            'transformDigest':window['transformDigest'],'modelDigest':model_digest,
            'targetIds':window['targetIds'],'units':window['units'],
            'futureTimesNs':[window['cutoffNs']+(i+1)*window['stepNs'] for i in range(horizon)],
            'quantileLevels':[.1,.5,.9],'quantiles':quantiles,'median':median,'status':status,
            'reasonCodes':list(reasons),'intervalCalibration':'not-evaluated',
            'costs':{'wallNs':0 if started_ns is None else max(0,monotonic_ns()-started_ns),
                     'rssBytes':None,'rssReason':'not-observed','rssScope':'not-observed',
                     'containerMemoryBytes':None,'containerMemoryReason':'not-observed',
                     'modelCpuNs':None,'modelCpuReason':'not-observed'},
            'evidenceClass':'heuristic','executionAuthorization':False}
    result['packetDigest']=digest(result)
    return validate_forecast(result,window,horizon)

def validate_forecast(raw, window, horizon):
    window=validate_window(window); result=parse_record(canonical(raw)); integer(horizon)
    keys(result,('version','sourceKind','inputDigest','resourceReceiptDigest','partitionDigest','transformDigest',
                 'modelDigest','targetIds','units','futureTimesNs','quantileLevels','quantiles','median','status',
                 'reasonCodes','intervalCalibration','costs','evidenceClass','executionAuthorization','packetDigest'))
    require(horizon in (1,5,10) and result['version']==VERSION,'unsupported-forecast-contract')
    require(result['sourceKind']==window['sourceKind'] and result['inputDigest']==digest(window),'forecast-input-drift')
    for field in ('resourceReceiptDigest','partitionDigest','transformDigest','targetIds','units'):
        require(result[field]==window[field],'forecast-binding-drift')
    pin(result['modelDigest']); require(result['quantileLevels']==[.1,.5,.9],'unsupported-quantiles')
    require(result['futureTimesNs']==[window['cutoffNs']+(i+1)*window['stepNs'] for i in range(horizon)],'forecast-horizon-drift')
    require(result['status'] in STATUSES and result['intervalCalibration']=='not-evaluated','invalid-forecast-status')
    require(type(result['reasonCodes']) is list and len(result['reasonCodes'])<=16,'invalid-reasons')
    for reason in result['reasonCodes']: identifier(reason)
    require(result['evidenceClass']=='heuristic' and result['executionAuthorization'] is False,'forecast-cannot-authorize')
    costs=result['costs']; keys(costs,('wallNs','rssBytes','rssReason','rssScope','containerMemoryBytes','containerMemoryReason','modelCpuNs','modelCpuReason')); integer(costs['wallNs'])
    if costs['rssBytes'] is None: identifier(costs['rssReason'])
    else: integer(costs['rssBytes']); require(costs['rssReason'] is None and costs['rssScope']=='process-lifetime-peak-linux','inconsistent-rss')
    for value_field,reason_field in (('containerMemoryBytes','containerMemoryReason'),('modelCpuNs','modelCpuReason')):
        if costs[value_field] is None:identifier(costs[reason_field])
        else:integer(costs[value_field]);require(costs[reason_field] is None,'inconsistent-cost-counter')
    if result['status']=='forecast':
        qs=result['quantiles']; med=result['median']; targets=len(window['targetIds'])
        require(type(qs) is list and len(qs)==targets and type(med) is list and len(med)==targets,'invalid-output-shape')
        for row,points in zip(qs,med):
            require(type(row) is list and len(row)==horizon and type(points) is list and len(points)==horizon,'invalid-output-shape')
            for triple,point in zip(row,points):
                require(type(triple) is list and len(triple)==3,'invalid-output-shape')
                for value in triple: finite(value)
                require(triple[0]<=triple[1]<=triple[2] and finite(point)==triple[1],'invalid-quantiles-or-median')
    else:
        require(result['quantiles'] is None and result['median'] is None and result['reasonCodes'],'invalid-terminal-output')
    require(result['packetDigest']==digest({k:v for k,v in result.items() if k!='packetDigest'}),'forecast-digest-drift')
    return deepcopy(result)
