# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from copy import deepcopy
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_baselines import predict_baseline
from agent_braid.forecast_policy import advise, validate_advice, verify_consumption
from tests.forecast_helpers import window
from tests.test_forecast_resources import resource

def request():
    w=window();r=resource();w['resourceReceiptDigest']=digest(r)
    return {'version':'agent-braid-advice-request-v1','mode':'shadow','window':w,'forecast':predict_baseline(w,1),
            'resource':r,'resourceDigest':digest(r),'nowNs':150,'expiresNs':180,'referenceMode':'serial',
            'catalogue':{'sourceKind':'synthetic','candidates':[
                {'id':'serial','mode':'serial','planDigest':'d'*64,'baseWallNs':1000,'loadPenaltyNsPerUnit':0,'eligible':True},
                {'id':'parallel','mode':'parallel','planDigest':'e'*64,'baseWallNs':500,'loadPenaltyNsPerUnit':1,'eligible':True}]},
            'policy':{'version':1,'partition':'development','targetId':'load','unit':'count','minimumRatio':1.1,'maximumIntervalWidth':100,'advisoryOverheadNs':10}}

class ForecastPolicyTests(unittest.TestCase):
    def test_shadow_keeps_reference_and_consultation_can_propose_parallel(self):
        r=request();a=advise(r)
        self.assertEqual('parallel',a['proposedAction']);self.assertEqual('serial',a['selectedAction'])
        self.assertFalse(a['executionAuthorization']);r['mode']='consultative'
        self.assertEqual('parallel',advise(r)['selectedAction'])

    def test_ineligible_fast_option_is_excluded_and_fallback_is_explicit(self):
        r=request();r['catalogue']['candidates'][1]['eligible']=False
        a=advise(r);self.assertEqual('serial',a['proposedAction'])
        self.assertEqual(['serial'],[c['id'] for c in a['candidates']])
        r['catalogue']['candidates'][0]['eligible']=False
        with self.assertRaises(ForecastError):advise(r)

    def test_expired_forged_and_promoted_requests_are_refused(self):
        r=request();a=advise(r)
        with self.assertRaises(ForecastError):validate_advice(a,r,now_ns=181)
        a['selectedAction']='parallel'
        with self.assertRaises(ForecastError):validate_advice(a,r,now_ns=150)
        r['mode']='promoted-exact-capability'
        with self.assertRaises(ForecastError):advise(r)

    def test_real_catalogue_needs_independent_verifier_and_synthetic_cannot_dispatch(self):
        r=request();a=advise(r)
        with self.assertRaises(ForecastError):verify_consumption(a,r,plan_digest='d'*64,now_ns=150)
        r['catalogue']['sourceKind']='verified-runtime'
        with self.assertRaises(ForecastError):advise(r)

    def test_wide_intervals_abstain_and_off_mode_never_selects(self):
        r=request();r['policy']['maximumIntervalWidth']=0
        self.assertEqual('abstained',advise(r)['status'])
        r['mode']='off';self.assertEqual('disabled',advise(r)['status'])
