# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_lab import signal_episode,git_fixture,FAMILIES
from agent_braid.forecast_baselines import predict_baseline
from agent_braid.forecast_evaluation import forecast_metrics
from agent_braid.forecast_experiment import paired_synthetic_episode,summarize_pairs

class ForecastExperimentTests(unittest.TestCase):
    def test_generators_repeat_exactly_and_holdout_labels_stay_out_of_inputs(self):
        for family in FAMILIES:
            one=signal_episode(family,seed=42,partition='holdout');two=signal_episode(family,seed=42,partition='holdout')
            self.assertEqual(one,two);self.assertNotIn('actual',one['window'])
            self.assertEqual(128,len(one['window']['values'][0]))

    def test_metrics_keep_refusals_and_undefined_scale(self):
        result=forecast_metrics([{'status':'forecast','actual':2,'quantiles':[1,2,3]},
                                 {'status':'unavailable','actual':None,'quantiles':None}])
        self.assertEqual(.5,result['actionableCoverage']);self.assertEqual(1,result['observedIntervalCoverage'])
        self.assertEqual(0,result['mae']);self.assertIsNone(result['scaledError'])

    def test_invalid_operator_preserves_all_three_arms(self):
        with git_fixture(seed=41) as fixture:
            result=paired_synthetic_episode(fixture,signal_episode('constant',seed=41),operator=lambda plan,root:{'grantId':'missing'})
        self.assertEqual(3,len(result['arms']));self.assertEqual('inconclusive',result['status'])
        self.assertTrue(all(r['wallNs']>0 and r['status']=='failed' for r in result['arms']))
        summary=summarize_pairs([result]);self.assertEqual(1,summary['invalidEpisodes']);self.assertFalse(summary['utilityAccepted'])
        with self.assertRaises(ForecastError):summarize_pairs([result,result])

    def test_owned_fixture_runtime_uses_external_grants_and_equivalent_trees(self):
        from agent_braid.runtime_policy import issue_operator_grant
        def operator(plan,root):return issue_operator_grant(plan,root,acknowledge=plan['planDigest'])
        with git_fixture(seed=43) as fixture:
            expected=fixture['request']['expectedFinalTree']
            result=paired_synthetic_episode(fixture,signal_episode('constant',seed=43),operator=operator)
        self.assertEqual('inconclusive',result['status'],result)
        self.assertTrue(all(r['resultTree']==expected for r in result['arms']))
        self.assertEqual('unavailable',next(r for r in result['arms'] if r['arm']=='forecast-choice')['forecastStatus'])
        self.assertFalse(result['utilityAccepted'])
        summary=summarize_pairs([result]);self.assertEqual(1,summary['fallbackEpisodes']);self.assertEqual([],summary['pairedRatios'])
