# SPDX-License-Identifier: AGPL-3.0-only
"""Finite economic advice; independent runtime verification retains authority."""
from copy import deepcopy
from .forecast_data import keys,require,identifier,pin,digest,finite,integer,validate_window,parse_record,canonical
from .forecast_resources import validate_resource
from .forecast_outputs import validate_forecast

def advise(raw, *, candidate_verifier=None, resource_verifier=None):
    request=parse_record(canonical(raw))
    keys(request,('version','mode','window','forecast','resource','resourceDigest','nowNs','expiresNs','referenceMode','catalogue','policy'))
    require(request['version']=='agent-braid-advice-request-v1','unsupported-advice-version')
    mode=request['mode'];require(mode in ('off','shadow','consultative'),'capability-not-promoted')
    window=validate_window(request['window']);integer(request['nowNs']);integer(request['expiresNs'])
    resource=validate_resource(request['resource'],expected_digest=request['resourceDigest'],now_ns=request['nowNs'],authority_verifier=resource_verifier)
    require(request['resourceDigest']==window['resourceReceiptDigest'],'resource-window-drift')
    require(request['nowNs']<request['expiresNs']<=resource['expiresNs'],'invalid-advice-expiry')
    forecast=request['forecast'];require(type(forecast) is dict and type(forecast.get('futureTimesNs')) is list,'invalid-forecast-record')
    horizon=len(forecast['futureTimesNs'])
    forecast=validate_forecast(forecast,window,horizon)
    catalogue=request['catalogue'];keys(catalogue,('sourceKind','candidates'))
    require(catalogue['sourceKind'] in ('synthetic','verified-runtime'),'unsupported-catalogue')
    if catalogue['sourceKind']=='synthetic':
        require(window['sourceKind']==resource['sourceKind']==forecast['sourceKind']=='synthetic','catalogue-provenance-drift')
    else:
        # Current session/MCP accept synthetic inputs only. Real-source advice
        # remains disabled until its complete independent source chain is wired.
        require(window['sourceKind']==resource['sourceKind']==forecast['sourceKind']=='permissioned','catalogue-provenance-drift')
    if catalogue['sourceKind']=='verified-runtime':
        require(candidate_verifier is not None and candidate_verifier(deepcopy(catalogue)) is True,'unverified-runtime-catalogue')
    candidates=catalogue['candidates'];require(type(candidates) is list and 1<=len(candidates)<=2,'invalid-candidates')
    seen=set();seen_modes=set();eligible=[]
    for candidate in candidates:
        keys(candidate,('id','mode','planDigest','baseWallNs','loadPenaltyNsPerUnit','eligible'))
        name=identifier(candidate['id']);require(name not in seen,'duplicate-candidate');seen.add(name)
        candidate_mode=candidate['mode'];require(candidate_mode in ('serial','parallel') and candidate_mode not in seen_modes,'unsupported-candidate-mode');seen_modes.add(candidate_mode)
        pin(candidate['planDigest']);integer(candidate['baseWallNs'],1);finite(candidate['loadPenaltyNsPerUnit'])
        require(candidate['loadPenaltyNsPerUnit']>=0 and type(candidate['eligible']) is bool,'invalid-cost-model')
        if candidate['eligible'] and candidate_mode in resource['allowedModes']: eligible.append(candidate)
    reference=next((c for c in eligible if c['mode']==request['referenceMode']),None)
    require(reference is not None,'reference-not-admitted')
    policy=request['policy'];keys(policy,('version','partition','targetId','unit','minimumRatio','maximumIntervalWidth','advisoryOverheadNs'))
    require(policy['version']==1 and type(policy['version']) is int and policy['partition']=='development','unfrozen-or-unsupported-policy')
    identifier(policy['targetId']);identifier(policy['unit']);require(policy['targetId'] in window['targetIds'],'economic-target-unavailable')
    target_index=window['targetIds'].index(policy['targetId']);require(window['units'][target_index]==policy['unit'],'economic-unit-drift')
    finite(policy['minimumRatio']);finite(policy['maximumIntervalWidth']);integer(policy['advisoryOverheadNs'])
    require(policy['minimumRatio']>=1 and policy['maximumIntervalWidth']>=0,'invalid-abstention-policy')
    proposed=reference;status='disabled' if mode=='off' else 'abstained';reasons=[];scores=[]
    if mode!='off' and forecast['status']=='forecast':
        # One prespecified numeric target drives a frozen development cost model.
        load=sum(forecast['median'][target_index])/horizon
        require(load>=0,'negative-economic-load')
        width=max(triple[2]-triple[0] for triple in forecast['quantiles'][target_index])
        for c in eligible:
            total=finite(c['baseWallNs']+c['loadPenaltyNsPerUnit']*load+policy['advisoryOverheadNs'])
            scores.append({'id':c['id'],'estimatedFullWallNs':total})
        if width<=policy['maximumIntervalWidth']:
            best=min(scores,key=lambda c:(c['estimatedFullWallNs'],c['id']))
            ref_score=next(c['estimatedFullWallNs'] for c in scores if c['id']==reference['id'])
            if ref_score/best['estimatedFullWallNs']>=policy['minimumRatio']:
                proposed=next(c for c in eligible if c['id']==best['id']);status='advised'
            else: reasons.append('insufficient-estimated-benefit')
        else:reasons.append('interval-too-wide')
    elif mode!='off':reasons.append('forecast-unavailable')
    selected=reference if mode in ('off','shadow') else proposed
    result={'version':'agent-braid-parallelism-advice-v1','sourceKind':catalogue['sourceKind'],
            'requestDigest':digest(request),'resourceDigest':request['resourceDigest'],'forecastDigest':forecast['packetDigest'],
            'policyDigest':digest(policy),'candidates':deepcopy(eligible),'scores':scores,
            'referenceAction':reference['id'],'proposedAction':None if mode=='off' else proposed['id'],
            'selectedAction':selected['id'],'selectedPlanDigest':selected['planDigest'],
            'mode':mode,'status':status,'expiresNs':request['expiresNs'],'reasonCodes':reasons,
            'evidenceClass':'heuristic','executionAuthorization':False}
    result['packetDigest']=digest(result);return result

def validate_advice(advice, request, *, now_ns, candidate_verifier=None, resource_verifier=None):
    integer(now_ns);require(type(advice) is dict and now_ns<advice.get('expiresNs',0),'stale-advice')
    expected=advise(request,candidate_verifier=candidate_verifier,resource_verifier=resource_verifier)
    require(canonical(advice)==canonical(expected),'advice-drift')
    validate_resource(request['resource'],expected_digest=request['resourceDigest'],now_ns=now_ns,authority_verifier=resource_verifier)
    return deepcopy(expected)

def verify_consumption(advice, request, *, plan_digest, now_ns, candidate_verifier=None, resource_verifier=None):
    """Return an exact binding only; caller must supply an existing runtime grant."""
    result=validate_advice(advice,request,now_ns=now_ns,candidate_verifier=candidate_verifier,resource_verifier=resource_verifier)
    require(result['sourceKind']=='verified-runtime','synthetic-advice-cannot-dispatch')
    require(result['selectedPlanDigest']==pin(plan_digest),'selected-policy-plan-drift')
    return {'planDigest':plan_digest,'adviceDigest':result['packetDigest'],'executionAuthorization':False}
