# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded deterministic metadata advice, separate from every consumer action."""
from dataclasses import dataclass
from collections import Counter
from time import monotonic_ns
import math
from agent_braid.system_one import (MAX_BYTES, CancellationToken, InvalidDecision,
    canonical, digest, freeze, thaw, parse_json)
from agent_braid.system_one_context import InvalidContext, keys, pin, identifier, integer, validate_snapshot

VERSION='s1-stage-advice-v1'
FALLBACK='keep-original-order-and-use-existing-consumer'
STAGES=('candidate-priority','analyzer-choice','effect-review','shortlist','adequacy','triage','ready-rank')
RULES=('stable-priority-v1','exact-resource-footprints-v1','effect-multiset-v1','installed-metadata-match-v1','required-field-completeness-v1','preserve-category-v1','stable-ready-priority-v1')
REASONS=frozenset(('invalid-stage-request','unsupported-stage','unsupported-source','context-pin-mismatch','registry-pin-mismatch','identity-set-mismatch','unknown-metadata','unsupported-metadata','stage-budget-exceeded','cancelled','deadline-exceeded','overloaded'))

class InvalidStage(ValueError):
    """Sanitized fixed refusal code."""
    def __init__(self, code='invalid-stage-request'):
        self.code=code; super().__init__(code)

@dataclass(frozen=True)
class StageRequest:
    envelope: object
    canonical_bytes: bytes
    input_bytes: int
    candidate_count: int
    def to_dict(self): return thaw(self.envelope)

def _installed_manifest():
    try:
        from agent_braid._system_one_stage_manifest import MANIFEST
    except ModuleNotFoundError as exc:
        if exc.name!='agent_braid._system_one_stage_manifest': raise
        return {'version':'s1-stage-registry-v1','stages':[],'rules':[], 'inventory':{'entries':[],'sources':[]}}
    return thaw(MANIFEST)

def stage_registry_manifest():
    """Static installed metadata only; absent composition advertises no support."""
    manifest=_installed_manifest()
    _validate_registry(manifest)
    return freeze(manifest)

def stage_capabilities():
    manifest=stage_registry_manifest()
    return freeze({'version':manifest['version'],'registryDigest':digest(manifest),'stages':manifest['stages'],
        'limits':{'maxInputBytes':MAX_BYTES,'maxCandidates':64,'deadlineMs':5000},'executionAuthorization':False})

def _names(value,maximum=64,minimum=0):
    if type(value) is not list or not minimum<=len(value)<=maximum: raise InvalidStage()
    for item in value: identifier(item)
    if len(set(value))!=len(value): raise InvalidStage('identity-set-mismatch')
    return value

def _hints(ids,hints):
    if type(hints) is not list or len(hints)!=len(ids): raise InvalidStage('identity-set-mismatch')
    priority={}
    for hint in hints:
        keys(hint,('candidateId','rulePriority')); identifier(hint['candidateId']); integer(hint['rulePriority'],0,63)
        if hint['candidateId'] in priority: raise InvalidStage('identity-set-mismatch')
        priority[hint['candidateId']]=hint['rulePriority']
    if set(priority)!=set(ids): raise InvalidStage('identity-set-mismatch')
    return sorted(ids,key=lambda item:priority[item])

def _effects(value):
    from agent_braid.analysis import EFFECT_KINDS
    if type(value) is not list or len(value)>64: raise InvalidStage()
    for effect in value:
        keys(effect,('kind','resource'))
        if effect['kind'] not in EFFECT_KINDS or type(effect['resource']) is not str or not effect['resource'].strip(): raise InvalidStage()

def _validate_registry(manifest):
    keys(manifest,('version','stages','rules','inventory'))
    if manifest['version']!='s1-stage-registry-v1': raise InvalidStage('registry-pin-mismatch')
    stages=_names(manifest['stages'],7)
    if any(s not in STAGES for s in stages): raise InvalidStage('registry-pin-mismatch')
    rules=manifest['rules']
    if type(rules) is not list or len(rules)!=len(stages): raise InvalidStage('registry-pin-mismatch')
    for stage,rule in zip(stages,rules):
        keys(rule,('stage','ruleId','implementationSourceDigest')); pin(rule['implementationSourceDigest'])
        if rule['stage']!=stage or rule['ruleId']!=RULES[STAGES.index(stage)]: raise InvalidStage('registry-pin-mismatch')
    inventory=manifest['inventory']; keys(inventory,('entries','sources'))
    entries=inventory['entries']; sources=inventory['sources']
    if type(entries) is not list or len(entries)>1 or type(sources) is not list or len(sources)!=len(entries): raise InvalidStage('registry-pin-mismatch')
    for entry,source in zip(entries,sources):
        keys(entry,('entryId','kind','capabilities','requiredArgumentNames','allowedArgumentNames','manifestDigest'))
        keys(source,('entryId','module','analyzerVersion','ruleSet','moduleSourceDigest','entryManifestDigest'))
        pin(source['moduleSourceDigest']); pin(entry['manifestDigest']); pin(source['entryManifestDigest'])
        expected={'entryId':'exact-resource-footprints-v1','kind':'tool-metadata','capabilities':['aim-analysis'],'requiredArgumentNames':['aimRecords'],'allowedArgumentNames':['aimRecords']}
        if {k:v for k,v in entry.items() if k!='manifestDigest'}!=expected or entry['manifestDigest']!=digest(expected): raise InvalidStage('registry-pin-mismatch')
        if source['entryId']!=entry['entryId'] or source['entryManifestDigest']!=entry['manifestDigest'] or source['module']!='agent_braid.analysis' or source['analyzerVersion']!='0.1.0-alpha' or source['ruleSet']!='exact-resource-footprints-v1': raise InvalidStage('registry-pin-mismatch')

def _rule(stage,p,registry,check=lambda:None):
    """Validate exact payload and return complete deterministic advice and count."""
    if stage=='candidate-priority':
        keys(p,('domain','eligibleIds','hints'))
        if p['domain'] not in ('spec018-prefiltered','spec012-prefiltered'): raise InvalidStage('unsupported-metadata')
        ids=_names(p['eligibleIds']); ordered=_hints(ids,p['hints'])
        return ({'orderedIds':ordered,'inputSetDigest':digest(ids),'rule':'stable-priority-v1'} if ids else None),len(ids)
    if stage=='ready-rank':
        keys(p,('readyIds','hints','readySetDigest','schedulerConstraintsDigest','grantBindingDigest'))
        ids=_names(p['readyIds'],minimum=1); ordered=_hints(ids,p['hints'])
        for k in ('readySetDigest','schedulerConstraintsDigest','grantBindingDigest'): pin(p[k])
        if digest(ids)!=p['readySetDigest']: raise InvalidStage('identity-set-mismatch')
        return {'orderedReadyIds':ordered,**{k:p[k] for k in ('readySetDigest','schedulerConstraintsDigest','grantBindingDigest')}},len(ids)
    if stage=='analyzer-choice':
        keys(p,('populationIds','analysisBudgetDigest','availableAnalyzerIds'))
        ids=_names(p['populationIds'],minimum=1); available=_names(p['availableAnalyzerIds'],32); pin(p['analysisBudgetDigest'])
        installed=[e['entryId'] for e in registry['inventory']['entries']]
        if available!=['exact-resource-footprints-v1'] or 'exact-resource-footprints-v1' not in installed: return None,len(ids)
        return {'analyzerId':'exact-resource-footprints-v1','populationDigest':digest(ids),'analysisBudgetDigest':p['analysisBudgetDigest']},len(ids)
    if stage=='effect-review':
        keys(p,('comparisons',)); comparisons=p['comparisons']
        if type(comparisons) is not list or not 1<=len(comparisons)<=64: raise InvalidStage()
        ids=[]; results=[]
        for item in comparisons:
            check(); keys(item,('comparisonId','declared','observed','declaredCoverage','observedCoverage'))
            ids.append(identifier(item['comparisonId'])); _effects(item['declared']); _effects(item['observed'])
            if any(item[k] not in ('complete','partial','unknown') for k in ('declaredCoverage','observedCoverage')): raise InvalidStage()
            complete=item['declaredCoverage']==item['observedCoverage']=='complete'
            equal=Counter(map(canonical,item['declared']))==Counter(map(canonical,item['observed']))
            results.append({**item,'relation':('equal' if equal else 'different') if complete else 'unknown'})
        _names(ids,minimum=1)
        return {'comparisons':results},len(ids)
    if stage=='shortlist':
        keys(p,('registryEntries','requestedCapabilities','argumentNames'))
        caps=set(_names(p['requestedCapabilities'],32)); names=set(_names(p['argumentNames'],32)); entries=p['registryEntries']
        if type(entries) is not list or len(entries)>32: raise InvalidStage()
        entryids=[]
        for e in entries:
            check(); keys(e,('entryId','kind','capabilities','requiredArgumentNames','allowedArgumentNames','manifestDigest'))
            entryids.append(identifier(e['entryId'])); pin(e['manifestDigest'])
            if e['kind'] not in ('tool-metadata','model-metadata','reference-rule'): raise InvalidStage()
            _names(e['capabilities'],32); required=set(_names(e['requiredArgumentNames'],32)); allowed=set(_names(e['allowedArgumentNames'],32))
            if not required<=allowed: raise InvalidStage()
        _names(entryids,32)
        if canonical(entries)!=canonical(registry['inventory']['entries']): raise InvalidStage('registry-pin-mismatch')
        if not entries: return None,0
        matches=[]; excluded=[]
        for e in entries:
            check()
            reason='capability-missing' if not caps<=set(e['capabilities']) else 'argument-shape-mismatch' if not set(e['requiredArgumentNames'])<=names<=set(e['allowedArgumentNames']) else None
            if reason: excluded.append({'entryId':e['entryId'],'reason':reason})
            else: matches.append(e['entryId'])
        return {'entryIds':matches,'excludedIds':excluded},len(entries)
    if stage=='adequacy':
        keys(p,('requiredFields','presentFields','schemaDigest','expectedSchemaDigest','rubric'))
        required=_names(p['requiredFields'],32,1); present=set(_names(p['presentFields'],32)); pin(p['schemaDigest']); pin(p['expectedSchemaDigest'])
        if p['rubric']!='required-field-completeness-v1': raise InvalidStage('unsupported-metadata')
        if p['schemaDigest']!=p['expectedSchemaDigest']: raise InvalidStage('identity-set-mismatch')
        missing=[f for f in required if f not in present]
        return {'presentRequiredCount':len(required)-len(missing),'requiredCount':len(required),'missingFields':missing,'schemaMatched':True},len(required)
    if stage=='triage':
        keys(p,('caseIds','categories')); ids=_names(p['caseIds'],minimum=1); categories=p['categories']
        if type(categories) is not list or len(categories)!=len(ids): raise InvalidStage('identity-set-mismatch')
        for item,case in zip(categories,ids):
            check(); keys(item,('caseId','category'))
            if item['caseId']!=case: raise InvalidStage('identity-set-mismatch')
            if item['category'] not in ('needs-review','unknown','counterexample-candidate'): raise InvalidStage('unsupported-metadata')
        return {'categories':categories},len(ids)
    raise InvalidStage('unsupported-stage')

def _validate_stage_request(raw, *, expected_context_digest, expected_registry_digest, checkpoint=lambda:None):
    """Validate complete original request and installed pins without consumer calls."""
    try:
        value=parse_json(raw); encoded=canonical(value)
        keys(value,('contractVersion','requestId','context','contextDigest','registryDigest','stage','payload','budgets'))
        if value['contractVersion']!=VERSION: raise InvalidStage()
        identifier(value['requestId']); pin(value['contextDigest']); pin(value['registryDigest']); pin(expected_context_digest); pin(expected_registry_digest)
        validate_snapshot(value['context'])
        if digest(value['context'])!=value['contextDigest'] or value['contextDigest']!=expected_context_digest: raise InvalidStage('context-pin-mismatch')
        registry=stage_registry_manifest()
        if digest(registry)!=expected_registry_digest or value['registryDigest']!=expected_registry_digest: raise InvalidStage('registry-pin-mismatch')
        if type(value['stage']) is not str or value['stage'] not in registry['stages']: raise InvalidStage('unsupported-stage')
        keys(value['budgets'],('maxInputBytes','maxCandidates','deadlineMs'))
        b=value['budgets']; integer(b['maxInputBytes'],1,MAX_BYTES); integer(b['maxCandidates'],1,64); integer(b['deadlineMs'],1,5000)
        if max(len(raw),len(encoded))>b['maxInputBytes']: raise InvalidStage('stage-budget-exceeded')
        checkpoint()
        _,count=_rule(value['stage'],value['payload'],thaw(registry),checkpoint)
        checkpoint()
        if count>b['maxCandidates']: raise InvalidStage('stage-budget-exceeded')
        return StageRequest(freeze(value),encoded,len(raw),count)
    except InvalidContext as exc:
        raise InvalidStage(exc.code if exc.code=='unsupported-source' else 'invalid-stage-request') from None
    except (InvalidDecision,UnicodeError,TypeError,ValueError,KeyError,OverflowError) as exc:
        if isinstance(exc,InvalidStage): raise
        raise InvalidStage() from None

def validate_stage_request(raw, *, expected_context_digest, expected_registry_digest):
    """Validate exact typed request/pins with no backend or consumer dispatch."""
    return _validate_stage_request(raw,expected_context_digest=expected_context_digest,expected_registry_digest=expected_registry_digest)

def _packet(request,status,advice,reasons,*,started,clock,validation_ms=0,rule_ms=0):
    v=request.envelope if request else None
    packet={'contractVersion':VERSION,'requestId':v['requestId'] if v else None,
        'requestDigest':digest(v) if v else None,'contextDigest':v['contextDigest'] if v else None,
        'generation':v['context']['generation'] if v else None,'registryDigest':v['registryDigest'] if v else None,
        'stage':v['stage'] if v else None,'status':status,'advice':advice,'fallback':FALLBACK,'reasonCodes':reasons,
        'usage':{'validationMs':validation_ms,'ruleMs':rule_ms,'totalMs':max(0,(clock()-started)/1e6),'inputBytes':request.input_bytes if request else 0,'candidateCount':request.candidate_count if request else 0},
        'evidenceClass':'heuristic','executionAuthorization':False}
    packet['packetDigest']=digest(packet)
    return freeze(packet)

def _run(raw,pins,token,started,deadline,clock,checkpoint=lambda: 'live'):
    request=None; validation_ms=rule_ms=0
    def stop():
        scope=checkpoint()
        if scope!='live': raise InvalidStage(scope if scope in ('cancelled','deadline-exceeded') else 'invalid-stage-request')
        if token.cancelled: raise InvalidStage('cancelled')
        if clock()>=deadline: raise InvalidStage('deadline-exceeded')
    try:
        stop(); request=_validate_stage_request(raw,**pins,checkpoint=stop)
        deadline=min(deadline,started+request.envelope['budgets']['deadlineMs']*1_000_000)
        stop(); validation_ms=max(0,(clock()-started)/1e6); rule_started=clock()
        advice,_=_rule(request.envelope['stage'],thaw(request.envelope['payload']),thaw(stage_registry_manifest()),stop)
        rule_ms=max(0,(clock()-rule_started)/1e6); stop()
        status='advised' if advice is not None else 'unavailable'
        packet=_packet(request,status,advice,[] if advice is not None else ['unknown-metadata'],started=started,clock=clock,validation_ms=validation_ms,rule_ms=rule_ms)
        if len(canonical(packet))>MAX_BYTES:
            raise InvalidStage('stage-budget-exceeded')
        # Packet construction/canonicalization also consumes the deadline.
        def publish(cancelled):
            stop()
            return packet
        return token.publish(publish)
    except InvalidStage as exc:
        status='defer' if exc.code in ('cancelled','deadline-exceeded','overloaded') else 'refused'
        return _packet(request,status,None,[exc.code],started=started,clock=clock,validation_ms=validation_ms,rule_ms=rule_ms)

def advise_stage(request_bytes, *, expected_context_digest, expected_registry_digest, cancellation=None):
    """Pure complete advice; owns one request-local token claim, no queue or I/O."""
    started=monotonic_ns(); token=cancellation if cancellation is not None else CancellationToken()
    if type(token) is not CancellationToken: return _packet(None,'refused',None,['invalid-stage-request'],started=started,clock=monotonic_ns)
    try: token.claim()
    except ValueError: return _packet(None,'refused',None,['invalid-stage-request'],started=started,clock=monotonic_ns)
    try:
        return _run(request_bytes,{'expected_context_digest':expected_context_digest,'expected_registry_digest':expected_registry_digest},token,started,started+5_000_000_000,monotonic_ns)
    finally: token.release()

def _advise_stage_in_scope(scope):
    """Private transport ownership checked before inspecting bindings or rule work."""
    from agent_braid._advice_scope import validate_for_stage, _scope_checkpoint
    view=validate_for_stage(scope)
    return _run(view.request_bytes,{'expected_context_digest':view.expected_context_digest,'expected_registry_digest':view.expected_registry_digest},view.cancellation,view.ingress_started_ns,view.deadline_ns,view.clock,lambda:_scope_checkpoint(scope))

def validate_stage_packet(packet, *, request_bytes, expected_context_digest, expected_registry_digest):
    """Recompute whole advice and original bindings; never execute a consumer."""
    try:
        value=parse_json(packet if type(packet) is bytes else canonical(packet)); keys(value,('contractVersion','requestId','requestDigest','contextDigest','generation','registryDigest','stage','status','advice','fallback','reasonCodes','usage','evidenceClass','executionAuthorization','packetDigest'))
        if value['contractVersion']!=VERSION or value['evidenceClass']!='heuristic' or value['executionAuthorization'] is not False or value['fallback']!=FALLBACK: raise InvalidStage()
        if value['packetDigest']!=digest({k:v for k,v in value.items() if k!='packetDigest'}): raise InvalidStage()
        if value['status'] not in ('advised','unavailable','refused','defer') or type(value['reasonCodes']) is not list or len(value['reasonCodes'])>8 or any(r not in REASONS for r in value['reasonCodes']): raise InvalidStage()
        keys(value['usage'],('validationMs','ruleMs','totalMs','inputBytes','candidateCount'))
        for k,n in value['usage'].items():
            if k in ('inputBytes','candidateCount'): integer(n,0,MAX_BYTES if k=='inputBytes' else 64)
            elif type(n) not in (int,float) or not math.isfinite(n) or n<0: raise InvalidStage()
        if request_bytes is None:
            if value['status'] not in ('refused','defer') or any(value[k] is not None for k in ('requestId','requestDigest','contextDigest','generation','registryDigest','stage')) or value['advice'] is not None or not value['reasonCodes'] or value['usage']['inputBytes'] or value['usage']['candidateCount']: raise InvalidStage()
        else:
            request=validate_stage_request(request_bytes,expected_context_digest=expected_context_digest,expected_registry_digest=expected_registry_digest); v=request.envelope
            if value['status']=='refused' and value['reasonCodes']!=['stage-budget-exceeded']: raise InvalidStage()
            expected={'requestId':v['requestId'],'requestDigest':digest(v),'contextDigest':v['contextDigest'],'generation':v['context']['generation'],'registryDigest':v['registryDigest'],'stage':v['stage']}
            if any(value[k]!=x for k,x in expected.items()) or value['usage']['inputBytes']!=request.input_bytes or value['usage']['candidateCount']!=request.candidate_count: raise InvalidStage()
            advice,_=_rule(v['stage'],thaw(v['payload']),thaw(stage_registry_manifest()))
            if value['status']=='advised':
                if advice is None or value['advice']!=advice or value['reasonCodes']: raise InvalidStage()
            elif value['advice'] is not None or not value['reasonCodes'] or (value['status']=='unavailable' and advice is not None): raise InvalidStage()
        reason_sets={'advised':set(),'unavailable':{'unknown-metadata','unsupported-metadata'},'defer':{'cancelled','deadline-exceeded','overloaded'},'refused':REASONS-{'cancelled','deadline-exceeded','overloaded','unknown-metadata'}}
        if any(r not in reason_sets[value['status']] for r in value['reasonCodes']): raise InvalidStage()
        if value['usage']['validationMs']>value['usage']['totalMs'] or value['usage']['ruleMs']>value['usage']['totalMs']: raise InvalidStage()
        return freeze(value)
    except (InvalidContext,InvalidDecision,InvalidStage,ValueError,TypeError,UnicodeError,OverflowError,KeyError):
        raise InvalidStage() from None


def advise_bound_stage(raw, *, expected_context_digest, expected_registry_digest,
                       stage, population_ids, operations=None, domain=None, cancellation=None):
    """Consumer-side identity check under one ingress budget, no consumer dispatch."""
    started=monotonic_ns(); request=None
    token=cancellation if cancellation is not None else CancellationToken()
    if type(token) is not CancellationToken:
        return _packet(None,'refused',None,['invalid-stage-request'],started=started,clock=monotonic_ns)
    try: token.claim()
    except ValueError:
        return _packet(None,'refused',None,['invalid-stage-request'],started=started,clock=monotonic_ns)
    try:
        pins={'expected_context_digest':expected_context_digest,'expected_registry_digest':expected_registry_digest}
        request=validate_stage_request(raw,**pins)
        value=request.envelope; payload=value['payload']
        ids=payload['populationIds'] if stage=='analyzer-choice' else payload['eligibleIds']
        if value['stage']!=stage or list(ids)!=population_ids or (domain is not None and payload['domain']!=domain):
            raise InvalidStage('identity-set-mismatch')
        if operations is not None and canonical(value['context']['operations'])!=canonical(operations):
            raise InvalidStage('context-pin-mismatch')
        return _run(raw,pins,token,started,started+5_000_000_000,monotonic_ns)
    except (InvalidStage,KeyError) as exc:
        code=exc.code if isinstance(exc,InvalidStage) else 'invalid-stage-request'
        # External consumer bindings never became validated request bindings.
        return _packet(None,'refused',None,[code],started=started,clock=monotonic_ns)
    finally: token.release()
