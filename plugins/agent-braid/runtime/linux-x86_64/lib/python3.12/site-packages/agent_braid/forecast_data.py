# SPDX-License-Identifier: AGPL-3.0-only
"""Finite feature-local numeric contracts; integrity is not authority."""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
import re

MAX_BYTES = 1048576
WINDOW_VERSION = 'agent-braid-telemetry-window-v1'
WINDOW_KEYS = {'version','sourceKind','episodeGroup','resourceReceiptDigest','gridStartNs',
               'stepNs','cutoffNs','targetIds','units','values','observedMask','availableAtNs',
               'missingReasons','pastCovariates','knownFutureCovariates','partitionDigest','transformDigest'}

class ForecastError(ValueError):
    """Sanitized refusal at a numeric, source or lifecycle boundary."""

def require(condition, reason):
    if not condition: raise ForecastError(reason)

def keys(value, names):
    require(type(value) is dict and set(value) == set(names), 'invalid-record-fields')

def integer(value, low=0, high=2**63-1):
    require(type(value) is int and low <= value <= high, 'invalid-integer')
    return value

def finite(value):
    require(type(value) in (int,float), 'invalid-number')
    try: valid = math.isfinite(value)
    except OverflowError: valid = False
    require(valid, 'nonfinite-number')
    return value

def identifier(value):
    require(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}', value), 'invalid-identifier')
    return value

def pin(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}',value), 'invalid-digest')
    return value

def canonical(value):
    try:
        raw = json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
    except (ValueError,TypeError,RecursionError,OverflowError): raise ForecastError('invalid-json') from None
    require(len(raw) <= MAX_BYTES,'input-budget-exceeded')
    return raw

def digest(value): return hashlib.sha256(canonical(value)).hexdigest()

def parse_record(raw):
    require(type(raw) is bytes and len(raw) <= MAX_BYTES,'input-budget-exceeded')
    def members(pairs):
        result={}
        for name,value in pairs:
            require(name not in result,'duplicate-json-key'); result[name]=value
        return result
    def number(token):
        require(len(token.lstrip('-')) <= 19,'integer-budget-exceeded')
        value=int(token); require(-(2**63) <= value <= 2**63-1,'invalid-integer'); return value
    def constant(_): raise ForecastError('nonfinite-json')
    try:
        text=raw.decode('utf-8'); depth=0; quoted=escaped=False
        for char in text:
            if quoted:
                if escaped: escaped=False
                elif char=='\\': escaped=True
                elif char=='"': quoted=False
            elif char=='"': quoted=True
            elif char in '[{':
                depth+=1; require(depth<=16,'json-depth-exceeded')
            elif char in ']}': depth-=1; require(depth>=0,'invalid-json')
        value=json.loads(text,object_pairs_hook=members,parse_int=number,
                         parse_float=lambda t: finite(float(t)),parse_constant=constant)
        require(type(value) is dict,'record-must-be-object')
        stack=[value]
        while stack:
            item=stack.pop()
            if type(item) is dict: stack.extend(item.keys()); stack.extend(item.values())
            elif type(item) is list: stack.extend(item)
            elif type(item) is str: require(not any(0xD800<=ord(c)<=0xDFFF for c in item),'invalid-unicode')
        return value
    except (UnicodeError,ValueError,TypeError,RecursionError,OverflowError) as exc:
        if isinstance(exc,ForecastError): raise
        raise ForecastError('invalid-json') from None

def validate_window(raw, *, source_verifier=None):
    window=parse_record(canonical(raw)); keys(window,WINDOW_KEYS)
    require(window['version']==WINDOW_VERSION,'unsupported-window-version')
    kind=window['sourceKind']; require(kind in ('synthetic','permissioned'),'unsupported-source')
    if kind=='permissioned':
        require(source_verifier is not None and source_verifier(deepcopy(window)) is True,'source-not-admitted')
    identifier(window['episodeGroup'])
    for field in ('resourceReceiptDigest','partitionDigest','transformDigest'): pin(window[field])
    start=integer(window['gridStartNs']); step=integer(window['stepNs'],1); cutoff=integer(window['cutoffNs'])
    targets=window['targetIds']; units=window['units']; values=window['values']
    require(type(targets) is list and 1<=len(targets)<=8 and len(set(map(identifier,targets)))==len(targets),'invalid-targets')
    require(type(units) is list and len(units)==len(targets),'invalid-units')
    for unit in units: identifier(unit)
    require(type(values) is list and len(values)==len(targets),'invalid-values')
    require(type(values[0]) is list and 1<=len(values[0])<=128,'invalid-context-length')
    bins=len(values[0]); require(start+(bins-1)*step<=cutoff,'future-grid')
    for field in ('observedMask','availableAtNs','missingReasons'):
        matrix=window[field]
        require(type(matrix) is list and len(matrix)==len(targets),'invalid-matrix')
        require(all(type(row) is list and len(row)==bins for row in matrix),'invalid-matrix')
    for row_id,row in enumerate(values):
        require(type(row) is list and len(row)==bins,'invalid-values')
        for index,value in enumerate(row):
            mask=window['observedMask'][row_id][index]; arrival=window['availableAtNs'][row_id][index]
            reason=window['missingReasons'][row_id][index]
            require(type(mask) is bool,'invalid-mask')
            if mask:
                finite(value); integer(arrival)
                require(start+index*step<=arrival<=cutoff and reason is None,'late-or-inconsistent-value')
            else:
                require(value is None and arrival is None,'missing-not-null'); identifier(reason)
    for role in ('pastCovariates','knownFutureCovariates'):
        channels=window[role]; require(type(channels) is dict and len(channels)<=8,'invalid-covariates')
        for name,channel in channels.items():
            identifier(name)
            fields=('unit','values','availableAtNs','missingReasons')
            keys(channel,fields+('eventTimesNs',) if role=='knownFutureCovariates' else fields)
            identifier(channel['unit'])
            count=bins if role=='pastCovariates' else len(channel['values'])
            require(count in (1,5,10) if role=='knownFutureCovariates' else count==bins,'invalid-covariate-length')
            for field in ('values','availableAtNs','missingReasons'):
                require(type(channel[field]) is list and len(channel[field])==count,'invalid-covariates')
            if role=='knownFutureCovariates':
                require(channel['eventTimesNs']==[cutoff+(i+1)*step for i in range(count)],'future-covariate-time-drift')
            for index,(value,arrival,reason) in enumerate(zip(channel['values'],channel['availableAtNs'],channel['missingReasons'])):
                if value is None: require(arrival is None and type(reason) is str,'missing-covariate-reason')
                else:
                    finite(value); integer(arrival); require(arrival<=cutoff and reason is None,'future-covariate-leakage')
                    if role=='pastCovariates':require(arrival>=start+index*step,'past-covariate-event-leakage')
    for name,channel in window['knownFutureCovariates'].items():
        require(name in window['pastCovariates'] and channel['unit']==window['pastCovariates'][name]['unit'],'known-future-context-unavailable')
    return deepcopy(window)

def reconcile_phases(phases, complete_wall_ns):
    integer(complete_wall_ns); require(type(phases) is list and len(phases)<=1024,'phase-budget-exceeded')
    intervals=[]
    for phase in phases:
        keys(phase,('name','startedNs','finishedNs')); identifier(phase['name'])
        start=integer(phase['startedNs']); end=integer(phase['finishedNs'])
        require(start<=end<=complete_wall_ns,'invalid-phase-interval'); intervals.append((start,end))
    union=0; finish=0
    for start,end in sorted(intervals): union+=max(0,end-max(start,finish)); finish=max(finish,end)
    return {'completeWallNs':complete_wall_ns,'phaseUnionNs':union,'coordinatorResidualNs':complete_wall_ns-union}
