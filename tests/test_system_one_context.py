# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from copy import deepcopy
from unittest.mock import patch
from agent_braid.system_one import canonical,digest,MODEL_MANIFEST,policy_manifest,STRICT_POLICY,thaw,CancellationToken
from agent_braid.system_one_context import validate_context,advise_synthetic,InvalidContext
from tests.test_system_one_core import fixture
from tests.test_system_one_advisors import snapshot,manifest,request

def context(decision):
    return {'contractVersion':'s1-integration-synthetic-v1','stage':'diagnostic',**snapshot(),'decisionRequestDigest':digest(decision)}
def invoke(c,d,**kwargs):
    return advise_synthetic(canonical(c),canonical(d),expected_context_digest=digest(c),expected_model_digest=digest(MODEL_MANIFEST),expected_policy_digest=digest(policy_manifest(d['policyId'])),**kwargs)

class SystemOneContextTests(unittest.TestCase):
    def test_diagnostic_original_and_delegated_binding(self):
        d=fixture(); c=context(d); p=invoke(c,d)
        self.assertEqual(p['status'],'diagnostic'); self.assertFalse(p['executionAuthorization']); self.assertEqual(p['decisionRequestDigest'],digest(d))
        delegated=deepcopy(d); delegated['budgets']['deadlineMs']=p['delegatedDeadlineMs']
        self.assertEqual(p['delegatedRequestDigest'],digest(delegated)); self.assertEqual(p['decisionResponse']['requestDigest'],digest(delegated))
        with self.assertRaises(TypeError): p['decisionResponse']['answers'][0]['pTrue']=0
    def test_strict_abstains_and_preserves_conflicting_channels(self):
        d=fixture(policy=STRICT_POLICY); c=context(d)
        c['operations'][0]['effects']['observed']=[{'kind':'delete','resource':'different'}]
        frozen=validate_context(canonical(c),expected_context_digest=digest(c)); self.assertEqual(frozen['operations'][0]['effects']['observed'][0]['kind'],'delete')
        self.assertEqual(invoke(c,d)['status'],'abstain')
    def test_generation_attempt_dependencies_and_source_reject(self):
        d=fixture(); base=context(d)
        for mutate in [lambda c:c.update(sourceKind='real'),lambda c:c.update(generation=True),lambda c:c['operations'][1].update(attemptId=c['operations'][0]['attemptId']),lambda c:c['operations'][0].update(dependencies=['unknown']),lambda c:c.update(stage='execute')]:
            c=deepcopy(base); mutate(c); self.assertEqual(invoke(c,d)['status'],'refused')
    def test_expected_pins_wrong_request_and_budget_refuse_before_core(self):
        d=fixture(); c=context(d); c['decisionRequestDigest']='0'*64
        with patch('agent_braid.system_one_context.evaluate',side_effect=AssertionError('backend called')):
            self.assertEqual(invoke(c,d)['status'],'refused')
            p=advise_synthetic(b' '*1048576,b'{}',expected_context_digest='0'*64,expected_model_digest='0'*64,expected_policy_digest='0'*64)
            self.assertEqual(p['reasonCodes'],('wrapper-budget-exceeded',))
    def test_cancelled_never_admits(self):
        d=fixture(); c=context(d); token=CancellationToken(); token.cancel()
        with patch('agent_braid.system_one_context.evaluate',side_effect=AssertionError('backend called')):
            self.assertEqual(invoke(c,d,cancellation=token)['status'],'defer')
    def test_analyze_opt_in_preserves_exact_report_and_rejects_other_population(self):
        from agent_braid.analysis import analyze,analyze_with_advice
        ops=snapshot()['operations']; value=request('analyzer-choice',{'populationIds':[o['instanceId'] for o in ops],'analysisBudgetDigest':'a'*64,'availableAnalyzerIds':['exact-resource-footprints-v1']})
        with patch('agent_braid.system_one_advisors._installed_manifest',return_value=manifest()):
            report,p=analyze_with_advice(ops,advice_request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])
            self.assertEqual(canonical(report),canonical(analyze(ops))); self.assertEqual(p['status'],'advised')
            value['payload']['populationIds'].reverse()
            report,p=analyze_with_advice(ops,advice_request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest']); self.assertEqual(p['status'],'refused'); self.assertEqual(report,analyze(ops))
    def test_exchange_every_pair_verified_and_three_insert_ineligible(self):
        from agent_braid.structured_exchange import verify_candidates_with_advice,InvalidExchange,verify,produce
        from tests.test_structured_exchange import fixture as exchange
        candidates=[{'candidateId':x,'request':exchange()} for x in ('x','y')]
        value=request('candidate-priority',{'domain':'spec018-prefiltered','eligibleIds':['x','y'],'hints':[{'candidateId':'x','rulePriority':63},{'candidateId':'y','rulePriority':0}]})
        with patch('agent_braid.system_one_advisors._installed_manifest',return_value=manifest()):
            results,p=verify_candidates_with_advice(candidates,advice_request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])
            self.assertEqual(results,[{'candidateId':i['candidateId'],'verification':verify(produce(i['request']))} for i in candidates]); self.assertEqual(p['advice']['orderedIds'],('y','x'))
            candidates[0]['request']=exchange(3)
            with self.assertRaises(InvalidExchange): verify_candidates_with_advice(candidates,advice_request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])
    def test_lone_surrogate_ids_and_values_refuse_domain_error(self):
        from agent_braid.structured_exchange import produce,InvalidExchange
        from tests.test_structured_exchange import fixture as exchange
        for mutate in [lambda r:r['base'][0].update(id='\ud800'),lambda r:r['base'][0].update(value='\udfff'),lambda r:r['operations'][0].update(id='\ud800'),lambda r:r['operations'][0].update(newId='\ud800'),lambda r:r['operations'][0].update(value='\udfff')]:
            r=exchange(); mutate(r)
            with self.assertRaises(InvalidExchange): produce(r)
        r=exchange(); r['operations'][0]['value']='España 😀'; self.assertEqual(produce(r)['request'],r)

    def test_wrapper_scope_reuse_cancellation_relay_and_late_publication(self):
        from agent_braid import system_one_context as cmod
        from agent_braid.system_one import evaluate as core_evaluate
        d=fixture(); c=context(d); token=CancellationToken(); token.claim()
        try:
            with patch.object(cmod,'evaluate',side_effect=AssertionError('core called')):
                self.assertEqual(invoke(c,d,cancellation=token)['status'],'refused')
        finally: token.release()
        token=CancellationToken()
        def late(raw,*,cancellation):
            answer=core_evaluate(raw,cancellation=cancellation)
            token.cancel()
            self.assertTrue(cancellation.cancelled)
            return answer
        with patch.object(cmod,'evaluate',side_effect=late):
            packet=invoke(c,d,cancellation=token)
        self.assertEqual(packet['status'],'defer'); self.assertIsNone(packet['decisionResponse']); self.assertFalse(token._in_use)
    def test_unknown_footprint_and_negative_verifier_cases_remain_visible(self):
        from agent_braid.analysis import analyze,analyze_with_advice
        from agent_braid.structured_exchange import verify_candidates_with_advice
        from tests.test_structured_exchange import fixture as exchange
        ops=snapshot()['operations']; ops[0]['effects']['coverage']['status']='unknown'
        value=request('analyzer-choice',{'populationIds':[o['instanceId'] for o in ops],'analysisBudgetDigest':'a'*64,'availableAnalyzerIds':['exact-resource-footprints-v1']}); value['context']['operations']=ops; value['contextDigest']=digest(value['context'])
        with patch('agent_braid.system_one_advisors._installed_manifest',return_value=manifest()):
            report,packet=analyze_with_advice(ops,advice_request_bytes=canonical(value),expected_context_digest=value['contextDigest'],expected_registry_digest=value['registryDigest'])
            self.assertEqual(report,analyze(ops)); self.assertEqual(report['interactions'][0]['classification'],'unknown'); self.assertFalse(report['executionAuthorization'])
            candidates=[{'candidateId':x,'request':exchange()} for x in ('x','y','z')]
            priority=request('candidate-priority',{'domain':'spec018-prefiltered','eligibleIds':['x','y','z'],'hints':[{'candidateId':i,'rulePriority':63-n} for n,i in enumerate(('x','y','z'))]})
            outcomes=[{'status':s,'executionAuthorization':False} for s in ('verified-bounded','divergent','inconclusive')]
            with patch('agent_braid.structured_exchange.verify',side_effect=outcomes) as verifier:
                results,packet=verify_candidates_with_advice(candidates,advice_request_bytes=canonical(priority),expected_context_digest=priority['contextDigest'],expected_registry_digest=priority['registryDigest'])
            self.assertEqual(verifier.call_count,3); self.assertEqual([r['verification'] for r in results],outcomes)

    def test_packet_construction_at_wrapper_deadline_suppresses_answer(self):
        from agent_braid import system_one_context as cmod
        d=fixture(); c=context(d); ticks=[0]; original=cmod._packet
        def construction(*args,**kwargs):
            packet=original(*args,**kwargs)
            if args[0]=='diagnostic': ticks[0]=5_000_000_000
            return packet
        with patch.object(cmod,'monotonic_ns',side_effect=lambda:ticks[0]),patch.object(cmod,'_packet',side_effect=construction):
            packet=invoke(c,d)
        self.assertEqual(packet['status'],'defer'); self.assertEqual(packet['reasonCodes'],('deadline-exceeded',)); self.assertIsNone(packet['decisionResponse'])
