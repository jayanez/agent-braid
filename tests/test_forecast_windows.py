# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_windows import compile_window, validate_partitions

class ForecastWindowTests(unittest.TestCase):
    def test_late_values_are_missing_and_future_values_do_not_backfill(self):
        events = [{'targetId':'load','eventNs':0,'availableAtNs':0,'unit':'count','value':0},
                  {'targetId':'load','eventNs':100000000,'availableAtNs':400000000,'unit':'count','value':9}]
        result = compile_window(events, target_ids=['load'], units=['count'], grid_start_ns=0,
                                step_ns=100000000, bins=4, cutoff_ns=300000000,
                                episode_group='episode', resource_digest='a'*64,
                                partition_digest='b'*64, transform_digest='c'*64)
        self.assertEqual([[0,None,None,None]], result['values'])
        self.assertEqual([[True,False,False,False]], result['observedMask'])

    def test_duplicate_grid_values_are_not_silently_overwritten(self):
        event={'targetId':'load','eventNs':0,'availableAtNs':0,'unit':'count','value':1}
        with self.assertRaises(ForecastError):
            compile_window([event,event], target_ids=['load'], units=['count'], grid_start_ns=0,
                           step_ns=1,bins=1,cutoff_ns=0,episode_group='e',resource_digest='a'*64,
                           partition_digest='b'*64,transform_digest='c'*64)

    def test_unknown_cadence_and_off_grid_events_are_refused(self):
        arguments = dict(target_ids=['load'], units=['count'], grid_start_ns=0,
                         step_ns=100, bins=4, cutoff_ns=300, episode_group='e',
                         resource_digest='a'*64, partition_digest='b'*64,
                         transform_digest='c'*64)
        event = {'targetId':'load', 'eventNs':150, 'availableAtNs':150,
                 'unit':'count', 'value':1}
        with self.assertRaisesRegex(ForecastError, '^off-grid-event$'):
            compile_window([event], **arguments)
        for cadence in (None, 0, True, 1.5):
            with self.subTest(cadence=cadence):
                with self.assertRaisesRegex(ForecastError, '^invalid-integer$'):
                    compile_window([], **dict(arguments, step_ns=cadence))

    def test_episode_and_context_horizon_overlap_cannot_cross_partitions(self):
        rows=[{'episodeGroup':'e1','partition':'development','startNs':0,'endNs':10},
              {'episodeGroup':'e2','partition':'holdout','startNs':20,'endNs':30}]
        self.assertEqual(2,len(validate_partitions(rows)))
        rows[1]['startNs']=5
        with self.assertRaises(ForecastError): validate_partitions(rows)
        rows[1]['startNs']=20; rows[1]['episodeGroup']='e1'
        with self.assertRaises(ForecastError): validate_partitions(rows)
