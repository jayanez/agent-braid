# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_readiness import readiness_packet

class ForecastReadinessTests(unittest.TestCase):
    def request(self):return {'version':'agent-braid-forecast-readiness-v1','sourceKind':'synthetic','sourceRegisterDigest':'a'*64,'primaryGroups':['local'],
                'episodes':[{'episodeId':'e1','partition':'holdout','resourceGroup':'local','observedHistoryBins':64,
                             'missingTargetFraction':.1,'status':'admitted','exclusionReason':None}]}

    def test_metadata_counts_do_not_admit_real_launch_or_read_outcomes(self):
        r=self.request();result=readiness_packet(r)
        self.assertEqual('synthetic-rehearsal',result['status']);self.assertFalse(result['outcomeValuesInspected'])
        self.assertFalse(result['realLaunchAuthorized']);r['episodes'][0]['actualOutcome']=100
        with self.assertRaises(ForecastError):readiness_packet(r)

    def test_short_missing_duplicate_and_unapproved_real_sources_refuse_or_exclude(self):
        r=self.request();r['episodes'][0]['observedHistoryBins']=63
        self.assertEqual({'insufficient-history-or-missingness':1},readiness_packet(r)['exclusionCounts'])
        r['episodes']*=2
        with self.assertRaises(ForecastError):readiness_packet(r)
        r=self.request();r['sourceKind']='permissioned'
        with self.assertRaises(ForecastError):readiness_packet(r)
