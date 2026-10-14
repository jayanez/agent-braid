# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_trace import SyntheticAdviceMonitor
from agent_braid.forecast_policy import advise
from agent_braid.forecast_data import ForecastError
from tests.test_forecast_policy import request

class ForecastTraceTests(unittest.TestCase):
    def test_later_labels_trigger_sticky_rollback_and_preserve_reference(self):
        r=request();a=advise(r);f=r['forecast'];monitor=SyntheticAdviceMonitor({'version':1,'partition':'development','maximumFailures':1,'maximumAbsoluteError':2})
        outcome={'version':'agent-braid-synthetic-outcome-v1','sourceKind':'synthetic','forecastDigest':f['packetDigest'],
                 'eventNs':f['futureTimesNs'][0],'availableAtNs':f['futureTimesNs'][0],'actual':99,'targetId':'load','unit':'count'}
        trace=monitor.observe(a,f,outcome);self.assertEqual('off',trace['rollbackMode']);self.assertEqual('serial',trace['shadowAction'])
        outcome['actual']=4;self.assertEqual('off',monitor.observe(a,f,outcome)['rollbackMode']);self.assertFalse(trace['executionAuthorization'])
        outcome['availableAtNs']=0
        with self.assertRaises(ForecastError):monitor.observe(a,f,outcome)

    def test_holdout_tuning_and_permissioned_label_spoof_are_refused(self):
        with self.assertRaises(ForecastError):SyntheticAdviceMonitor({'version':1,'partition':'holdout','maximumFailures':1,'maximumAbsoluteError':2})
        r=request();monitor=SyntheticAdviceMonitor({'version':1,'partition':'development','maximumFailures':1,'maximumAbsoluteError':2})
        with self.assertRaises(ForecastError):monitor.observe(advise(r),r['forecast'],{'version':'agent-braid-synthetic-outcome-v1','sourceKind':'permissioned'})
