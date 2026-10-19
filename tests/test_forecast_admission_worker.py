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

    def test_image_independent_recipe_and_external_profile_bind_without_hash_cycle(self):
        import hashlib,json
        from dataclasses import fields
        from agent_braid.forecast_linux_profile import LinuxAdmissionProfile,PhaseLimit,STEPS
        from agent_braid.forecast_recipe import recipe_bytes,BASE,REPOSITORY
        from agent_braid.forecast_git_launch import INPUT_COMMITS
        request={'gitRuntimeRequestVersion':'0.1.0-alpha','repository':REPOSITORY,'baseRevision':BASE,
                 'expectedFinalTree':'1'*40,'order':['a','b'],'operations':[
                     {'instanceId':name,'attemptId':name,'source':{'kind':'commit','revision':commit},
                      'dependencies':[],'uncertainPaths':[],'declaredWrites':[name]}
                     for name,commit in zip(('a','b'),INPUT_COMMITS)]}
        raw=recipe_bytes(request,source_digest='c'*64,git_sha256='a'*64)
        self.assertNotIn(b'imageSha256',raw)
        self.assertNotIn(b'profileIdentity',raw)
        config=dict(mode='serial',image_sha256='a'*64,root_hash='b'*64,source_digest='c'*64,
                    manager_sha256='d'*64, operator_sha256='f'*64, operator_entry_sha256='8'*64, worker_sha256='9'*64, census_sha256='a'*64,recipe_sha256=hashlib.sha256(raw).hexdigest(),uid=61000,
                    limits=tuple(PhaseLimit(p,0 if p=='terminal' else 1,10,4096,8) for p in STEPS))
        profile=LinuxAdmissionProfile(**config)
        wire=dict(config,limits=[vars(p) for p in config['limits']])
        self.assertEqual(worker.recipe_profile(json.loads(raw),profile.identity,wire).identity,profile.identity)
        changed=json.loads(raw);changed['gitSha256']='f'*64
        with self.assertRaises(ForecastError):
            worker.recipe_profile(changed,profile.identity,wire)
