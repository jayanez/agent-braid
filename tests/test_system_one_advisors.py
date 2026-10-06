# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic structural controls, no utility or installed-artifact assertions."""
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
from agent_braid.system_one import canonical,digest,thaw,CancellationToken
from agent_braid import system_one_advisors as a

ROOT=Path(__file__).resolve().parents[1]
def snapshot():
    ops=json.loads((ROOT/'examples/analysis/file-edits.json').read_text())['operations']
    return {'sourceKind':'synthetic','generation':0,'operations':ops}
def manifest(*,empty=False):
    entry={'entryId':'exact-resource-footprints-v1','kind':'tool-metadata','capabilities':['aim-analysis'],'requiredArgumentNames':['aimRecords'],'allowedArgumentNames':['aimRecords']}
    entry['manifestDigest']=digest(entry)
    return {'version':'s1-stage-registry-v1','stages':list(a.STAGES),'rules':[{'stage':s,'ruleId':r,'implementationSourceDigest':'0'*64} for s,r in zip(a.STAGES,a.RULES)],'inventory':{'entries':[] if empty else [entry],'sources':[] if empty else [{'entryId':entry['entryId'],'module':'agent_braid.analysis','analyzerVersion':'0.1.0-alpha','ruleSet':'exact-resource-footprints-v1','moduleSourceDigest':'0'*64,'entryManifestDigest':entry['manifestDigest']}]}}
def request(stage,payload,*,registry=None):
    context=snapshot(); registry=registry or manifest()
    return {'contractVersion':a.VERSION,'requestId':'r','context':context,'contextDigest':digest(context),'registryDigest':digest(registry),'stage':stage,'payload':payload,'budgets':{'maxInputBytes':1048576,'maxCandidates':64,'deadlineMs':5000}}
def invoke(value,**kw):
    return a.advise_stage(canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'],**kw)
def validate(packet,value):
    return a.validate_stage_packet(packet,request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])

class SystemOneAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(a,'_installed_manifest',return_value=manifest()); self.patch.start(); self.addCleanup(self.patch.stop)
    def test_priority_stable_complete_permutation_and_empty_unavailable(self):
        value=request('candidate-priority',{'domain':'spec018-prefiltered','eligibleIds':['b','a','c'],'hints':[{'candidateId':i,'rulePriority':n} for i,n in [('c',0),('a',1),('b',1)]]})
        packet=invoke(value); self.assertEqual(packet['advice']['orderedIds'],('c','b','a')); validate(packet,value)
        value['payload'].update(eligibleIds=[],hints=[])
        self.assertEqual(invoke(value)['status'],'unavailable')
    def test_priority_missing_duplicate_extra_ids_and_domains_refuse(self):
        base=request('candidate-priority',{'domain':'spec018-prefiltered','eligibleIds':['x'],'hints':[{'candidateId':'x','rulePriority':0}]})
        for change in [lambda p:p.update(domain='real'),lambda p:p.update(hints=[]),lambda p:p['hints'][0].update(candidateId='z'),lambda p:p['hints'][0].update(rulePriority=True),lambda p:p.update(eligibleIds=['x','x'])]:
            value=deepcopy(base); change(value['payload']); self.assertEqual(invoke(value)['status'],'refused')
    def test_analyzer_preserves_population_and_opaque_budget(self):
        value=request('analyzer-choice',{'populationIds':['z','a'],'analysisBudgetDigest':'1'*64,'availableAnalyzerIds':['exact-resource-footprints-v1']})
        packet=invoke(value); self.assertEqual(packet['advice']['populationDigest'],digest(['z','a'])); self.assertEqual(packet['advice']['analysisBudgetDigest'],'1'*64)
        value['payload']['availableAnalyzerIds']=['imaginary']; self.assertEqual(invoke(value)['status'],'unavailable')
    def test_effect_multisets_keep_multiplicity_order_and_unknown(self):
        e={'kind':'write','resource':'same'}
        value=request('effect-review',{'comparisons':[{'comparisonId':'eq','declared':[e,e],'observed':[e,e],'declaredCoverage':'complete','observedCoverage':'complete'},{'comparisonId':'diff','declared':[e,e],'observed':[e],'declaredCoverage':'complete','observedCoverage':'complete'},{'comparisonId':'unk','declared':[e],'observed':[],'declaredCoverage':'partial','observedCoverage':'complete'}]})
        packet=invoke(value); self.assertEqual([i['relation'] for i in packet['advice']['comparisons']],['equal','different','unknown']); self.assertEqual(len(packet['advice']['comparisons'][1]['declared']),2); validate(packet,value)
    def test_shortlist_match_exclusions_forged_inventory_and_empty(self):
        value=request('shortlist',{'registryEntries':manifest()['inventory']['entries'],'requestedCapabilities':['aim-analysis'],'argumentNames':['aimRecords']})
        packet=invoke(value); self.assertEqual(packet['advice']['entryIds'],('exact-resource-footprints-v1',)); validate(packet,value)
        value['payload']['argumentNames']=[]; self.assertEqual(invoke(value)['advice']['excludedIds'][0]['reason'],'argument-shape-mismatch')
        value['payload']['requestedCapabilities']=['imaginary']; self.assertEqual(invoke(value)['advice']['excludedIds'][0]['reason'],'capability-missing')
        value['payload']['registryEntries'][0]['entryId']='imaginary'; self.assertEqual(invoke(value)['status'],'refused')
        with patch.object(a,'_installed_manifest',return_value=manifest(empty=True)):
            value=request('shortlist',{'registryEntries':[],'requestedCapabilities':[],'argumentNames':[]},registry=manifest(empty=True)); self.assertEqual(invoke(value)['status'],'unavailable')
    def test_adequacy_names_only_and_schema_mismatch(self):
        value=request('adequacy',{'requiredFields':['b','a'],'presentFields':['a'],'schemaDigest':'a'*64,'expectedSchemaDigest':'a'*64,'rubric':'required-field-completeness-v1'})
        packet=invoke(value); self.assertEqual(packet['advice']['missingFields'],('b',)); validate(packet,value)
        value['payload']['schemaDigest']='b'*64; self.assertEqual(invoke(value)['status'],'refused')
    def test_triage_preserves_ids_without_reducer(self):
        value=request('triage',{'caseIds':['x','y'],'categories':[{'caseId':'x','category':'unknown'},{'caseId':'y','category':'counterexample-candidate'}]})
        packet=invoke(value); self.assertEqual(packet['advice']['categories'][1]['caseId'],'y'); validate(packet,value)
        value['payload']['categories'].reverse(); self.assertEqual(invoke(value)['status'],'refused')
    def test_ready_rank_preserves_opaque_grants_and_membership(self):
        value=request('ready-rank',{'readyIds':['b','a'],'hints':[{'candidateId':'b','rulePriority':2},{'candidateId':'a','rulePriority':0}],'readySetDigest':digest(['b','a']),'schedulerConstraintsDigest':'a'*64,'grantBindingDigest':'b'*64})
        packet=invoke(value); self.assertEqual(packet['advice']['orderedReadyIds'],('a','b')); self.assertFalse(packet['executionAuthorization']); validate(packet,value)
        value['payload']['readySetDigest']=digest(['a','b']); self.assertEqual(invoke(value)['status'],'refused')
    def test_parser_pins_budgets_numeric_and_context_fail_closed(self):
        base=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]})
        for raw in [b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":'+b'['*17+b'0'+b']'*17+b'}',b'{}',b' '*1048577]:
            packet=a.advise_stage(raw,expected_context_digest=base['contextDigest'],expected_registry_digest=base['registryDigest']); self.assertEqual(packet['status'],'refused'); self.assertIsNone(packet['requestId'])
        for mutate in [lambda v:v['context'].update(sourceKind='real'),lambda v:v.update(registryDigest='0'*64),lambda v:v.update(contextDigest='0'*64),lambda v:v['budgets'].update(maxCandidates=True),lambda v:v['budgets'].update(maxInputBytes=1),lambda v:v['context'].update(generation=True),lambda v:v.update(grant=True)]:
            value=deepcopy(base); mutate(value); self.assertEqual(invoke(value)['status'],'refused')
    def test_deep_immutability_and_whole_packet_forgery(self):
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]}); packet=invoke(value)
        with self.assertRaises(TypeError): packet['advice']['categories'][0]['category']='forged'
        for k,x in [('executionAuthorization',True),('verified',True),('grant',{}),('requestDigest','0'*64),('status','advised')]:
            forged=thaw(packet); forged[k]=x
            if k=='status': forged['advice']['categories'][0]['category']='needs-review'
            forged['packetDigest']=digest({key:item for key,item in forged.items() if key!='packetDigest'})
            with self.assertRaises(a.InvalidStage): validate(forged,value)
    def test_cancelled_token_reuse_and_expiry_never_publishes_advice(self):
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]}); token=CancellationToken(); token.cancel()
        self.assertEqual(invoke(value,cancellation=token)['status'],'defer')
        token=CancellationToken(); token.claim()
        try: self.assertEqual(invoke(value,cancellation=token)['status'],'refused')
        finally: token.release()
        with patch.object(a,'monotonic_ns',side_effect=[0,5_000_000_000,5_000_000_000]):
            self.assertEqual(invoke(value)['status'],'defer')
    def test_missing_manifest_advertises_no_support(self):
        with patch.object(a,'_installed_manifest',return_value={'version':'s1-stage-registry-v1','stages':[],'rules':[],'inventory':{'entries':[],'sources':[]}}):
            self.assertEqual(a.stage_capabilities()['stages'],())
    def test_scope_rejects_fabricated_without_rule_work(self):
        from agent_braid._advice_scope import InvalidAdviceScope
        with patch.object(a,'_rule',side_effect=AssertionError('rule called')):
            with self.assertRaises(InvalidAdviceScope): a._advise_stage_in_scope(object())

    def test_packet_omissions_dataclass_and_status_forgeries_refuse(self):
        from dataclasses import dataclass
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]}); packet=invoke(value)
        for field in packet:
            forged=thaw(packet); del forged[field]
            with self.subTest(field=field),self.assertRaises(a.InvalidStage): validate(forged,value)
        @dataclass
        class FakePacket:
            verified: bool=True
        with self.assertRaises(a.InvalidStage): validate(FakePacket(),value)
        for status,reason in [('refused','cancelled'),('defer','unknown-metadata'),('unavailable','unknown-metadata')]:
            forged=thaw(packet); forged.update(status=status,advice=None,reasonCodes=[reason]); forged['packetDigest']=digest({k:v for k,v in forged.items() if k!='packetDigest'})
            with self.assertRaises(a.InvalidStage): validate(forged,value)
        self.assertEqual(validate(canonical(packet),value),packet)

    def test_bound_request_rejects_every_fabricated_refusal(self):
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]})
        packet=invoke(value)
        for reason in a.REASONS:
            forged=thaw(packet);forged.update(status='refused',advice=None,reasonCodes=[reason])
            forged['packetDigest']=digest({k:v for k,v in forged.items() if k!='packetDigest'})
            with self.subTest(reason=reason),self.assertRaises(a.InvalidStage):validate(forged,value)
        refused=a.advise_stage(b'{}',expected_context_digest='0'*64,expected_registry_digest=digest(manifest()))
        self.assertEqual(a.validate_stage_packet(refused,request_bytes=None,expected_context_digest='0'*64,expected_registry_digest=digest(manifest()))['status'],'refused')
        for reason in ('cancelled','deadline-exceeded'):
            deferred=thaw(packet);deferred.update(status='defer',advice=None,reasonCodes=[reason])
            deferred['packetDigest']=digest({k:v for k,v in deferred.items() if k!='packetDigest'})
            self.assertEqual(validate(deferred,value)['status'],'defer')
    def test_installed_source_manifest_metadata_and_stale_registry_refuse(self):
        base=request('shortlist',{'registryEntries':manifest()['inventory']['entries'],'requestedCapabilities':[],'argumentNames':[]})
        for mutate in [lambda m:m['inventory']['sources'][0].update(module='imaginary'),lambda m:m['inventory']['sources'][0].update(moduleSourceDigest='bad'),lambda m:m['inventory']['sources'][0].update(entryManifestDigest='1'*64),lambda m:m['rules'][0].update(implementationSourceDigest='bad')]:
            m=manifest(); mutate(m)
            with patch.object(a,'_installed_manifest',return_value=m): self.assertEqual(invoke(base)['status'],'refused')
        changed=manifest(); changed['inventory']['sources'][0]['moduleSourceDigest']='1'*64
        with patch.object(a,'_installed_manifest',return_value=changed): self.assertEqual(invoke(base)['reasonCodes'],('registry-pin-mismatch',))
        base['payload']['registryEntries'][0]['sourcePath']='private'
        self.assertEqual(invoke(base)['status'],'refused')
    def test_publication_construction_cancel_and_exact_deadline_suppress_advice(self):
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]}); original=a._packet
        for cancelled in (True,False):
            token=CancellationToken(); ticks=[0]
            def construction(*args,**kwargs):
                packet=original(*args,**kwargs)
                if args[1]=='advised':
                    if cancelled: token.cancel()
                    else: ticks[0]=5_000_000_000
                return packet
            with patch.object(a,'monotonic_ns',side_effect=lambda:ticks[0]),patch.object(a,'_packet',side_effect=construction):
                packet=invoke(value,cancellation=token)
                self.assertEqual(packet['status'],'defer'); self.assertIsNone(packet['advice']); self.assertEqual(packet['reasonCodes'],('cancelled' if cancelled else 'deadline-exceeded',))
    def test_transport_scope_original_digest_completed_and_future_invalid(self):
        from agent_braid._advice_scope import _TransportScopeRegistry,InvalidAdviceScope
        from dataclasses import replace
        ticks=[10]; owner=_TransportScopeRegistry(clock=lambda:ticks[0])
        value=request('triage',{'caseIds':['x'],'categories':[{'caseId':'x','category':'unknown'}]})
        scope=owner.admit(owner.begin_ingress(),'wire',canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])
        try:
            packet=a._advise_stage_in_scope(scope); self.assertEqual(packet['requestDigest'],digest(value)); self.assertEqual(packet['usage']['totalMs'],0)
            with self.assertRaises(InvalidAdviceScope): a._advise_stage_in_scope(replace(scope,ingress_started_ns=999))
            ticks[0]=scope.deadline_ns
            self.assertEqual(a._advise_stage_in_scope(scope)['status'],'defer')
        finally: owner.complete(scope)
        with self.assertRaises(InvalidAdviceScope): a._advise_stage_in_scope(scope)
