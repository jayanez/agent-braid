# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from copy import deepcopy
from agent_braid.forecast_lab import signal_episode
from agent_braid.forecast_evaluation import rolling_origin_baselines
from agent_braid.forecast_data import ForecastError

class RollingOriginTests(unittest.TestCase):
    def episodes(self):
        return [signal_episode('trend',seed=i,partition=p) for i,p in enumerate(('development','calibration','holdout'))]

    def test_holdout_outcomes_cannot_change_development_selection(self):
        episodes=self.episodes();one=rolling_origin_baselines(episodes)
        changed=deepcopy(episodes);changed[-1]=signal_episode('bursts',seed=20,partition='holdout')
        two=rolling_origin_baselines(changed)
        self.assertEqual(one['selection'],two['selection'])
        self.assertNotEqual(one['metrics']['holdout/ewma/10']['mae'],two['metrics']['holdout/ewma/10']['mae'])
        self.assertFalse(one['utilityAccepted'])

    def test_duplicate_episode_and_absent_development_are_refused(self):
        episodes=self.episodes()
        with self.assertRaises(ForecastError):rolling_origin_baselines(episodes[1:])
        with self.assertRaises(ForecastError):rolling_origin_baselines(episodes+episodes[:1])

    def test_relabelled_window_and_same_seed_across_partitions_are_refused(self):
        episodes=self.episodes();episodes[-1]['window']=deepcopy(episodes[0]['window'])
        with self.assertRaises(ForecastError):rolling_origin_baselines(episodes)
        repeated=[signal_episode('trend',seed=1,partition=p) for p in ('development','holdout')]
        with self.assertRaises(ForecastError):rolling_origin_baselines(repeated)
        changed=self.episodes();changed[-1]['actual'][0]+=1
        with self.assertRaises(ForecastError):rolling_origin_baselines(changed)
