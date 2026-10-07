# SPDX-License-Identifier: AGPL-3.0-only
"""Data-only metadata, privacy, nonblocking lock and mutation controls."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from agent_braid.system_one import CancellationToken,canonical,digest,thaw
from agent_braid.system_one_trace import StageObservationBuffer
from agent_braid import system_one_advisors as advisors
from tests.test_system_one_mcp import stage_request,manifest,invoke


class SystemOneTraceTests(unittest.TestCase):
    def setUp(self):
        self.pin=patch.object(advisors,'_installed_manifest',return_value=manifest());self.pin.start();self.addCleanup(self.pin.stop)
        self.value=stage_request();self.packet=invoke(self.value);self.buffer=StageObservationBuffer(1)
        self.cost={'adviceMs':1.0,'fallbackMs':None,'verifierMs':None,'runtimeMs':None,'totalMs':99.0}
    def record(self,**extra):
        args={'request_bytes':canonical(self.value),'expected_context_digest':self.value['contextDigest'],'expected_registry_digest':self.value['registryDigest'],'cost':self.cost}
        packet=extra.pop('packet',self.packet);args.update(extra)
        return self.buffer.record(canonical(packet),**args)
    def test_metadata_exact_allowlist_no_content_total_unknown_and_deep_immutable(self):
        self.assertEqual(self.record()['status'],'recorded');self.cost['adviceMs']=88
        result=self.buffer.drain();record=result['records'][0]
        self.assertEqual(set(record),{'version','stage','status','reasonCodes','requestDigest','contextDigest','registryDigest','adviceDigest','cost','fallback'})
        self.assertEqual(record['cost']['adviceMs'],1);self.assertIsNone(record['cost']['totalMs'])
        self.assertNotIn('original-stage',canonical(result).decode());self.assertNotIn('caseIds',canonical(result).decode())
        with self.assertRaises(TypeError):record['cost']['adviceMs']=4
        self.assertEqual(self.buffer.drain()['records'],())
    def test_overflow_drops_new_saturates_count_and_drain_resets(self):
        self.record();self.assertEqual(self.record()['status'],'dropped');self.buffer._dropped=2**63-1
        self.record();result=self.buffer.drain();self.assertEqual(result['dropped'],2**63-1);self.assertEqual(len(result['records']),1)
        self.assertEqual(self.buffer.drain()['dropped'],0)
    def test_busy_record_drain_never_changes_state_or_counters(self):
        self.buffer._lock.acquire()
        try:
            self.assertEqual(self.record()['status'],'busy');self.assertEqual(self.buffer.drain()['status'],'busy')
        finally:self.buffer._lock.release()
        self.assertEqual(self.buffer.drain()['dropped'],0)
    def test_forged_authority_private_fields_stale_pins_and_cost_refuse(self):
        for key,value in [('prompt','PRIVATE_SENTINEL'),('answers',['PRIVATE_SENTINEL']),('executionAuthorization',True)]:
            packet=thaw(self.packet);packet[key]=value;packet['packetDigest']=digest({k:v for k,v in packet.items() if k!='packetDigest'})
            self.assertEqual(self.record(packet=packet)['status'],'refused')
        for cost in [dict(self.cost,adviceMs=float('nan')),dict(self.cost,totalMs=float('inf')),dict(self.cost,adviceMs=True),dict(self.cost,runtimeMs=-1),dict(self.cost,private='PRIVATE_SENTINEL')]:
            self.assertEqual(self.record(cost=cost)['status'],'refused')
        self.assertEqual(self.record(expected_context_digest='0'*64)['status'],'refused')
        self.assertEqual(self.record(expected_registry_digest='0'*64)['status'],'refused')
        self.assertEqual(self.buffer.drain()['records'],())
    def test_cancel_and_absolute_expiry_before_insertion_do_not_record(self):
        token=CancellationToken();token.cancel();self.assertEqual(self.record(cancellation=token)['reasonCodes'],('cancelled',))
        times=iter([0,5_000_000_000]);self.buffer=StageObservationBuffer(_clock=lambda:next(times))
        self.assertEqual(self.record()['reasonCodes'],('deadline-exceeded',));self.assertEqual(self.buffer.drain()['records'],())
    def test_capacity_and_full_chain_cost_observations(self):
        for value in [True,0,65,'1']:
            with self.assertRaises(ValueError):StageObservationBuffer(value)
        cost={'adviceMs':1,'fallbackMs':2,'verifierMs':3,'runtimeMs':4,'totalMs':10}
        self.assertEqual(self.record(cost=cost,fallback='used-existing-consumer')['status'],'recorded')
        self.assertEqual(self.buffer.drain()['records'][0]['cost']['totalMs'],10)

if __name__=='__main__':unittest.main()
