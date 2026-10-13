# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_baselines import predict_baseline, fit_regression, predict_regression, select_ewma
from agent_braid.forecast_outputs import validate_forecast
from tests.forecast_helpers import window

class ForecastBaselineTests(unittest.TestCase):
    def test_persistence_and_ewma_have_independent_ordered_outputs(self):
        source=window(); result=predict_baseline(source,5,method='persistence')
        self.assertEqual([4]*5,result['median'][0]); self.assertFalse(result['executionAuthorization'])
        self.assertEqual('not-evaluated',result['intervalCalibration'])
        result['quantiles'][0][0][1]=100
        self.assertEqual(4,predict_baseline(source,5,method='persistence')['median'][0][0])
        with self.assertRaises(ForecastError):validate_forecast(result,source,5)
        ewma=predict_baseline(source,1,method='ewma',alpha=.5)
        self.assertEqual(3.125,ewma['median'][0][0])

    def test_unavailable_series_and_unsupported_horizons_refuse(self):
        source=window()
        source['values']=[[None]*4];source['observedMask']=[[False]*4]
        source['availableAtNs']=[[None]*4];source['missingReasons']=[['missing']*4]
        self.assertEqual('unavailable',predict_baseline(source,1)['status'])
        with self.assertRaises(ForecastError):predict_baseline(window(),2)

    def test_regression_fits_development_only_and_has_predictive_behavior(self):
        rows=[{'partition':'development','features':[float(x)],'outcome':2*x+1} for x in range(8)]
        model=fit_regression(rows,ridge=.00001)
        self.assertAlmostEqual(21,predict_regression(model,[10.0]),places=4)
        rows[0]['partition']='holdout'
        with self.assertRaises(ForecastError):fit_regression(rows)

    def test_ewma_selection_requires_development_labels(self):
        rows=[{'partition':'development','window':window(),'actual':[5]}]
        selected=select_ewma(rows)
        self.assertIn(selected['alpha'],(.1,.3,.5,.9))
        rows[0]['partition']='holdout'
        with self.assertRaises(ForecastError):select_ewma(rows)
