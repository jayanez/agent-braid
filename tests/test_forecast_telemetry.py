# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_telemetry import TelemetryRecorder

class ForecastTelemetryTests(unittest.TestCase):
    def test_allowlisted_counters_and_overlap_preserve_explicit_missingness(self):
        ticks=iter([10,12,14,18,20]); rec=TelemetryRecorder('e',{'rss':'bytes'},clock=lambda:next(ticks))
        rec.start_phase('a');rec.start_phase('b');rec.end_phase('a');result=rec.finish()
        self.assertEqual(10,result['completeWallNs']);self.assertEqual('incomplete-phase',result['status'])
        rec=TelemetryRecorder('e',{'rss':'bytes'},clock=lambda:10)
        rec.sample('rss',None,reason='unavailable');self.assertIsNone(rec.finish()['counters'][0]['value'])
        with self.assertRaises(ForecastError):rec.sample('rss',0)

    def test_duplicate_unknown_and_backward_clock_are_refused(self):
        rec=TelemetryRecorder('e',{'rss':'bytes'},clock=lambda:10)
        rec.sample('rss',0)
        with self.assertRaises(ForecastError):rec.sample('rss',1)
        with self.assertRaises(ForecastError):rec.sample('prompt',1)
        ticks=iter([10,9]);rec=TelemetryRecorder('e',{},clock=lambda:next(ticks))
        with self.assertRaises(ForecastError):rec.finish()
