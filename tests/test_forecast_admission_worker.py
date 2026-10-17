# SPDX-License-Identifier: AGPL-3.0-only
"""Fixed worker route controls; all runtime effects are mocked, no real inputs."""
from contextlib import nullcontext
import unittest
from unittest.mock import MagicMock, patch
from agent_braid import forecast_admission_worker as worker
from agent_braid.forecast_data import ForecastError


class AdmissionWorkerTests(unittest.TestCase):
    def test_main_cannot_start_without_native_platform_or_image_recipe(self):
        with patch.object(worker.sys, 'platform', 'darwin'), self.assertRaises(ForecastError):
            worker.main(['a'*64,'prepare'])

    def test_missing_expected_tree_is_not_invented_or_measured(self):
        with patch('agent_braid.git_replay.produce') as producer:
            self.assertFalse(worker.bootstrap_free_request({'expectedFinalTree':None}))
        producer.assert_not_called()

    def test_fixed_work_route_uses_same_plan_and_grant_across_phases(self):
        scope, channel = MagicMock(), MagicMock()
        plan = {'planDigest':'p'}
        request = {'request':'owned protocol placeholder, never a workload'}
        with patch.object(worker,'admission_launches',return_value=nullcontext()), \
             patch.object(worker,'write_record') as write, \
             patch('agent_braid.git_runtime._analysis_request',return_value={}), \
             patch('agent_braid.git_replay.produce',return_value=({},{})), \
             patch('agent_braid.runtime_policy.prepare_policy_run',return_value=plan) as prep, \
             patch('agent_braid.runtime_policy.issue_operator_grant',return_value={'grantId':'g'}) as grant, \
             patch('agent_braid.runtime_policy.execute_policy_run',return_value={}) as execute:
            worker.work(scope,channel,request,'parallel')
        self.assertEqual([c.args[0] for c in scope.enter.call_args_list], ['prepare','grant','dispatch'])
        self.assertIs(grant.call_args.args[0], plan)
        self.assertIs(execute.call_args.args[0], plan)
        self.assertEqual(execute.call_args.args[1:],('/work/grants','g'))
        self.assertEqual(prep.call_args.args[1],'/work/run')
        self.assertEqual(write.call_args_list[-1].args[0],'/work/launches.json')

    def test_serial_verifier_has_no_grant_or_preparation_route(self):
        scope = MagicMock()
        with patch.object(worker,'admission_launches',return_value=nullcontext()), \
             patch.object(worker,'write_record'), \
             patch('agent_braid.git_runtime.verify_run',return_value={'status':'verified-completed','resultTree':'t'}) as verify, \
             patch('agent_braid.runtime_policy.issue_operator_grant') as grant, \
             patch('agent_braid.runtime_policy.prepare_policy_run') as prepare:
            worker.verify(scope,{'expectedFinalTree':'t'},'serial')
        verify.assert_called_once_with({'expectedFinalTree':'t'},'/work/run')
        grant.assert_not_called(); prepare.assert_not_called()
