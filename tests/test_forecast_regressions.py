# SPDX-License-Identifier: AGPL-3.0-only
"""Independent-review counterexamples at causal and authority boundaries."""
import unittest
from agent_braid.forecast_data import ForecastError,validate_window
from agent_braid.forecast_chronos_inputs import translate_inputs
from agent_braid.forecast_chronos import normalize_output
from agent_braid.forecast_policy import advise
from tests.forecast_helpers import window
from tests.test_forecast_policy import request

class ForecastRegressionTests(unittest.TestCase):
    def test_direct_window_cannot_backdate_event_availability(self):
        w=window();w['availableAtNs'][0][1]=0
        with self.assertRaises(ForecastError):validate_window(w)

    def test_known_future_has_historical_context_and_exact_future_times(self):
        w=window();w['pastCovariates']={'planned':{'unit':'count','values':[1,2,3,4],
                         'availableAtNs':[0,100000000,200000000,300000000],'missingReasons':[None]*4}}
        w['knownFutureCovariates']={'planned':{'unit':'count','values':[5],
                         'availableAtNs':[300000000],'missingReasons':[None],'eventTimesNs':[400000000]}}
        self.assertEqual([5],translate_inputs(w,1)[0]['future_covariates']['planned'])
        w['knownFutureCovariates']['planned']['eventTimesNs']=[500000000]
        with self.assertRaises(ForecastError):translate_inputs(w,1)

    def test_synthetic_inputs_cannot_be_relabelled_as_runtime_consumable(self):
        r=request();r['catalogue']['sourceKind']='verified-runtime'
        with self.assertRaisesRegex(ForecastError,'provenance'):advise(r,candidate_verifier=lambda c:True)

    def test_economic_target_unit_mismatch_and_malformed_quantiles_refuse(self):
        r=request();r['policy']['unit']='bytes'
        with self.assertRaises(ForecastError):advise(r)
        for q in ([[[[]]]],[[[[1]]]],[[[[1,2]]]]):
            with self.assertRaises(ForecastError):normalize_output(window(),1,q,[[[2]]],model_digest='a'*64)
