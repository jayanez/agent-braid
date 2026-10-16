# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_resources import validate_resource

def resource():
    return {'version':'agent-braid-forecast-resource-v1','sourceKind':'synthetic','profileId':'owned-lab',
            'hostId':'synthetic-local','executionContract':'authorized-serial-index-patch-v1',
            'allowedModes':['serial','parallel'],'maxWorkers':4,'observedNs':100,'expiresNs':200,
            'caps':{'operations':4,'patchBytes':262144,'scratchBytes':67108864}}

class ForecastResourceTests(unittest.TestCase):
    def test_fresh_allowlisted_resource_and_copy(self):
        r=resource(); actual=validate_resource(r,expected_digest=digest(r),now_ns=150)
        r['caps']['operations']=8;self.assertEqual(4,actual['caps']['operations'])

    def test_expiry_wrong_digest_unknown_modes_and_real_without_authority_refuse(self):
        for mutate in (lambda r:r.update(expiresNs=120),lambda r:r.update(maxWorkers=8),
                       lambda r:r.update(allowedModes=['remote']),lambda r:r.update(sourceKind='permissioned')):
            r=resource(); mutate(r)
            with self.assertRaises(ForecastError):validate_resource(r,expected_digest=digest(r),now_ns=150)
        with self.assertRaises(ForecastError):validate_resource(resource(),expected_digest='b'*64,now_ns=150)
