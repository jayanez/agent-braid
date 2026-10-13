# SPDX-License-Identifier: AGPL-3.0-only
"""Schema/integrity inspection only; absent input/source bindings remain unverified."""
from .forecast_data import keys,require,identifier,integer,finite,pin,digest,canonical,parse_record

FORECAST_FIELDS=('version','sourceKind','inputDigest','resourceReceiptDigest','partitionDigest','transformDigest','modelDigest',
    'targetIds','units','futureTimesNs','quantileLevels','quantiles','median','status','reasonCodes','intervalCalibration','costs',
    'evidenceClass','executionAuthorization','packetDigest')
ADVICE_FIELDS=('version','sourceKind','requestDigest','resourceDigest','forecastDigest','policyDigest','candidates','scores',
    'referenceAction','proposedAction','selectedAction','selectedPlanDigest','mode','status','expiresNs','reasonCodes','evidenceClass','executionAuthorization','packetDigest')

def validate_receipt_schema(raw):
    receipt=parse_record(canonical(raw));version=receipt.get('version')
    require(version in ('agent-braid-forecast-v1','agent-braid-parallelism-advice-v1'),'unsupported-receipt')
    keys(receipt,FORECAST_FIELDS if version=='agent-braid-forecast-v1' else ADVICE_FIELDS)
    require(receipt['evidenceClass']=='heuristic' and receipt['executionAuthorization'] is False,'receipt-cannot-authorize')
    reasons=receipt['reasonCodes'];require(type(reasons) is list and len(reasons)<=16,'invalid-receipt-reasons')
    for reason in reasons:identifier(reason)
    if version=='agent-braid-forecast-v1':
        require(receipt['sourceKind'] in ('synthetic','permissioned'),'invalid-receipt-provenance')
        for field in ('inputDigest','resourceReceiptDigest','partitionDigest','transformDigest','modelDigest'):pin(receipt[field])
        targets=receipt['targetIds'];units=receipt['units'];times=receipt['futureTimesNs']
        require(type(targets) is list and 1<=len(targets)<=8 and len(set(map(identifier,targets)))==len(targets),'invalid-targets')
        require(type(units) is list and len(units)==len(targets),'invalid-units')
        for unit in units:identifier(unit)
        require(type(times) is list and len(times) in (1,5,10),'invalid-horizon')
        for timestamp in times:integer(timestamp)
        require(all(a<b for a,b in zip(times,times[1:])),'invalid-forecast-times')
        require(receipt['quantileLevels']==[.1,.5,.9] and receipt['intervalCalibration']=='not-evaluated','invalid-quantile-semantics')
        require(receipt['status'] in ('forecast','refused','unavailable','timed-out','cancelled'),'invalid-forecast-status')
        if receipt['status']=='forecast':
            quantiles=receipt['quantiles'];median=receipt['median'];require(type(quantiles) is list and type(median) is list
               and len(quantiles)==len(median)==len(targets),'invalid-output-shape')
            for row,points in zip(quantiles,median):
                require(type(row) is list and type(points) is list and len(row)==len(points)==len(times),'invalid-output-shape')
                for triple,point in zip(row,points):
                    require(type(triple) is list and len(triple)==3,'invalid-output-shape')
                    for value in triple:finite(value)
                    require(triple[0]<=triple[1]<=triple[2] and finite(point)==triple[1],'invalid-quantiles')
        else:require(receipt['quantiles'] is None and receipt['median'] is None and reasons,'invalid-terminal-output')
        costs=receipt['costs'];keys(costs,('wallNs','rssBytes','rssReason','rssScope','containerMemoryBytes','containerMemoryReason','modelCpuNs','modelCpuReason'));integer(costs['wallNs'])
        for value_field,reason_field in (('rssBytes','rssReason'),('containerMemoryBytes','containerMemoryReason'),('modelCpuNs','modelCpuReason')):
            if costs[value_field] is None:identifier(costs[reason_field])
            else:integer(costs[value_field]);require(costs[reason_field] is None,'inconsistent-cost-counter')
        require(costs['rssScope'] in ('not-observed','process-lifetime-peak-linux'),'invalid-rss-scope')
    else:
        require(receipt['sourceKind'] in ('synthetic','verified-runtime') and receipt['mode'] in ('off','shadow','consultative'),'invalid-advice-provenance')
        require(receipt['status'] in ('disabled','abstained','advised'),'invalid-advice-status')
        for field in ('requestDigest','resourceDigest','forecastDigest','policyDigest','selectedPlanDigest'):pin(receipt[field])
        integer(receipt['expiresNs']);candidates=receipt['candidates'];scores=receipt['scores']
        require(type(candidates) is list and 1<=len(candidates)<=2 and type(scores) is list and len(scores)<=2,'invalid-advice-candidates')
        names=set()
        for c in candidates:
            keys(c,('id','mode','planDigest','baseWallNs','loadPenaltyNsPerUnit','eligible'))
            identifier(c['id']);require(c['id'] not in names and c['mode'] in ('serial','parallel') and c['eligible'] is True,'invalid-advice-candidate')
            names.add(c['id']);pin(c['planDigest']);integer(c['baseWallNs'],1);finite(c['loadPenaltyNsPerUnit']);require(c['loadPenaltyNsPerUnit']>=0,'invalid-cost-model')
        for score in scores:
            keys(score,('id','estimatedFullWallNs'));require(score['id'] in names and finite(score['estimatedFullWallNs'])>0,'invalid-advice-score')
        require(receipt['referenceAction'] in names and receipt['selectedAction'] in names,'invalid-selected-action')
        require(receipt['proposedAction'] is None if receipt['mode']=='off' else receipt['proposedAction'] in names,'invalid-proposed-action')
        selected=next(c for c in candidates if c['id']==receipt['selectedAction']);require(selected['planDigest']==receipt['selectedPlanDigest'],'selected-plan-drift')
        if receipt['mode'] in ('off','shadow'):require(receipt['selectedAction']==receipt['referenceAction'],'shadow-selection-drift')
    require(receipt['packetDigest']==digest({k:v for k,v in receipt.items() if k!='packetDigest'}),'receipt-integrity-drift')
    return receipt

def inspect_receipt(raw):
    receipt=validate_receipt_schema(raw)
    return {'version':'agent-braid-forecast-inspection-v1','receipt':receipt,'schemaValid':True,'integrityValid':True,
            'inputBindingsVerified':False,'sourceAuthorityVerified':False,'executionAuthorization':False}
