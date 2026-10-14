# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_chronos_inputs import translate_inputs
from agent_braid.forecast_chronos import normalize_output, ChronosAdapter
from tests.forecast_helpers import window

class ForecastChronosTests(unittest.TestCase):
    def test_missingness_is_preserved_and_no_future_target_is_constructed(self):
        w=window();w['values'][0][1]=None;w['observedMask'][0][1]=False
        w['availableAtNs'][0][1]=None;w['missingReasons'][0][1]='missing'
        item=translate_inputs(w,1)[0]
        self.assertIsNone(item['target'][0][1]);self.assertNotIn('future_target',item)
        self.assertEqual({},item['future_covariates'])

    def test_median_output_axis_and_crossed_or_wrong_point_refuse(self):
        w=window();q=[[[[1,2,3]]]];points=[[[2]]]
        self.assertEqual([[2]],normalize_output(w,1,q,points,model_digest='d'*64)['median'])
        for bad in ([ [[[3,2,1]]] ], [ [[[1,float('inf'),3]]] ]):
            with self.assertRaises(ForecastError):normalize_output(w,1,bad,points,model_digest='d'*64)
        with self.assertRaises(ForecastError):normalize_output(w,1,q,[[[2.1]]],model_digest='d'*64)

    def test_unapproved_model_never_calls_worker_and_stub_is_explicit(self):
        class Never:
            def forecast(self,*a,**k):raise AssertionError('unapproved model called')
            def close(self):pass
        adapter=ChronosAdapter(None,worker=Never())
        self.assertEqual('unavailable',adapter.forecast(window(),1)['status'])
        self.assertFalse(adapter.capabilities()['available'])
