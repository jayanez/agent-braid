# SPDX-License-Identifier: AGPL-3.0-only
"""Pure ranking cannot alter any legacy execution boundary."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from agent_braid.system_one import CancellationToken,canonical,digest,thaw
from agent_braid import runtime_scheduler as scheduler, system_one_advisors as advisors
from tests.test_system_one_mcp import stage_request,manifest,invoke


class SystemOneRuntimeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.pin=patch.object(advisors,'_installed_manifest',return_value=manifest());self.pin.start();self.addCleanup(self.pin.stop)
        self.ready=['b','a']
        self.value=stage_request('ready-rank',{'readyIds':self.ready,'hints':[{'candidateId':'b','rulePriority':63},{'candidateId':'a','rulePriority':0}],'readySetDigest':digest(self.ready),'schedulerConstraintsDigest':'a'*64,'grantBindingDigest':'b'*64})
        self.packet=invoke(self.value)
    def select(self,value=None,packet=None,**extra):
        value=value or self.value
        kwargs={'expected_context_digest':value['contextDigest'],'expected_registry_digest':value['registryDigest'],'ready_ids':self.ready,'scheduler_constraints_digest':'a'*64,'grant_binding_digest':'b'*64}
        kwargs.update(extra)
        return scheduler.select_ready_rank_hint(canonical(value),canonical(self.packet if packet is None else packet),**kwargs)
    def test_valid_permutation_is_immutable_sidecar_without_dispatch(self):
        original=deepcopy(self.value)
        with patch.object(scheduler,'_geometry',side_effect=AssertionError('dispatch')),patch.object(scheduler,'prepare_schedule',side_effect=AssertionError('dispatch')),patch.object(scheduler,'run_preparations',side_effect=AssertionError('dispatch')),patch.object(scheduler,'verify_preparations',side_effect=AssertionError('dispatch')):
            result=self.select()
        self.assertEqual(result['status'],'hinted');self.assertEqual(result['orderedReadyIds'],('a','b'))
        self.assertFalse(result['executionAuthorization']);self.assertEqual(self.value,original)
        with self.assertRaises(TypeError):result['status']='authorized'
    def test_stale_ready_constraints_grant_context_and_packet_refuse_hints(self):
        for kwargs in [{'ready_ids':['a','b']},{'ready_ids':['b','new']},{'scheduler_constraints_digest':'c'*64},{'grant_binding_digest':'c'*64},{'expected_context_digest':'c'*64},{'expected_registry_digest':'c'*64}]:
            result=self.select(**kwargs);self.assertEqual(result['status'],'fallback')
            self.assertEqual(result['orderedReadyIds'],tuple(kwargs.get('ready_ids',self.ready)))
        for key,value in [('executionAuthorization',True),('grant',{'allow':True}),('verified',True)]:
            packet=thaw(self.packet);packet[key]=value;packet['packetDigest']=digest({k:v for k,v in packet.items() if k!='packetDigest'})
            self.assertEqual(self.select(packet=packet)['status'],'fallback')
    def test_cancelled_hint_keeps_current_order_and_never_calls_legacy_runtime(self):
        token=CancellationToken();token.cancel();result=self.select(cancellation=token)
        self.assertEqual(result['orderedReadyIds'],tuple(self.ready));self.assertEqual(result['reasonCodes'],('cancelled',))
    def test_invalid_consumer_ready_set_is_explicit_not_a_fabricated_fallback(self):
        for ready in [[],['a','a'],[{}],[True],['a'*65]]:
            with self.assertRaises(scheduler.InvalidRuntimeSchedule):self.select(ready_ids=ready)

if __name__=='__main__':unittest.main()
