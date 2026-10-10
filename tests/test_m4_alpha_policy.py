# SPDX-License-Identifier: AGPL-3.0-only
"""Real consumer verification and fail-closed local grant controls for C1."""
from copy import deepcopy
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import git_replay, git_runtime, runtime_policy as policy
from agent_braid.analysis import _digest
from tests import test_git_runtime as runtime_fixtures


class RuntimePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = runtime_fixtures.GitRuntimeTests()
        cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)
        cls.request = cls.fixture.request
        analysis = git_runtime._analysis_request(cls.request)
        cls.evidence, cls.advisory = git_replay.produce(analysis)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=self.fixture.root)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dest, self.store = self.root / 'result', self.root / 'grants'
        self.plan = policy.prepare_policy_run(self.request, self.dest,
                                             replay_evidence=self.evidence,
                                             advisory_plan=self.advisory)

    def grant(self, **kwargs):
        return policy.issue_operator_grant(self.plan, self.store,
                                           acknowledge=self.plan['planDigest'], **kwargs)

    def test_read_only_pipeline_and_legacy_authority(self):
        self.assertFalse(self.dest.exists())
        self.assertFalse(self.store.exists())
        self.assertEqual(self.fixture.before, self.fixture.snapshot(self.fixture.repo))
        self.assertIs(False, self.plan['advisoryPlan']['executionAuthorization'])
        self.assertEqual('verified', self.plan['consumerVerification']['status'])
        self.assertEqual(self.plan, policy.verify_policy_plan(self.plan))

    def test_forged_evidence_is_refused_even_with_recomputed_producer_digest(self):
        bad = deepcopy(self.advisory)
        bad['executionAuthorization'] = True
        bad['planDigest'] = _digest({k:v for k,v in bad.items() if k != 'planDigest'})
        with self.assertRaises(policy.InvalidRuntimePolicy):
            policy.prepare_policy_run(self.request, self.dest,
                                      replay_evidence=self.evidence, advisory_plan=bad)
        self.assertFalse(self.dest.exists())

    def test_different_attempt_identity_cannot_borrow_evidence(self):
        bad = deepcopy(self.request)
        bad['operations'][0]['attemptId'] = 'another-attempt'
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy, 'different runtime inputs'):
            policy.prepare_policy_run(bad, self.dest,
                                      replay_evidence=self.evidence, advisory_plan=self.advisory)

    def test_policy_or_limit_changes_are_refused_after_digest_recomputation(self):
        for change in ('limits', 'policy', 'consumer', 'boolean-type'):
            with self.subTest(change=change):
                bad = deepcopy(self.plan)
                if change == 'limits': bad['policy']['runtimeStageLimits']['operations'] = 100
                if change == 'policy': bad['policy']['revision'] = 'unreviewed'
                if change == 'consumer': bad['consumerVerification']['status'] = 'unverified'
                if change == 'boolean-type': bad['policy']['sourcePromotion'] = 0
                if change != 'boolean-type':
                    bad['planDigest'] = _digest({k:v for k,v in bad.items() if k != 'planDigest'})
                with self.assertRaises(policy.InvalidRuntimePolicy): policy.verify_policy_plan(bad)
        self.assertFalse(self.dest.exists())

    def test_acknowledgement_and_lifetime_fail_before_store_allocation(self):
        with self.assertRaises(policy.InvalidRuntimePolicy):
            policy.issue_operator_grant(self.plan,self.store,acknowledge='sha256:'+'0'*64)
        for lifetime in (True, 0, 901, 1.5):
            with self.subTest(lifetime=lifetime), self.assertRaises(policy.InvalidRuntimePolicy):
                self.grant(ttl_seconds=lifetime)
        self.assertFalse(self.store.exists())

    def test_missing_grant_cannot_execute(self):
        self.grant()
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'missing'):
            policy.execute_policy_run(self.plan,self.store,'00000000-0000-0000-0000-000000000001')
        self.assertFalse(self.dest.exists())

    def test_grant_executes_once_and_retries_independently_verify(self):
        grant = self.grant()
        first = policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        self.assertEqual('performed', first['dispatch'])
        result_before = self.fixture.snapshot(self.dest)
        second = policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        self.assertEqual('not-repeated', second['dispatch'])
        self.assertEqual('verified-completed',second['runtime']['status'])
        self.assertEqual(result_before,self.fixture.snapshot(self.dest))
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))

    def test_expired_and_wrong_action_grants_do_not_allocate_run(self):
        with patch.object(policy.time,'time',return_value=1000): grant=self.grant(ttl_seconds=1)
        with patch.object(policy.time,'time',return_value=1001):
            with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'expired'):
                policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        grant=self.grant(action='resume')
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'action'):
            policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        self.assertFalse(self.dest.exists())

    def test_destination_cannot_reuse_grant(self):
        grant=self.grant()
        other=policy.prepare_policy_run(self.request,self.root/'other',
                                        replay_evidence=self.evidence,advisory_plan=self.advisory)
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'destination'):
            policy.execute_policy_run(other,self.store,grant['grantId'])
        self.assertFalse((self.root/'other').exists())
        self.assertFalse(self.dest.exists())

    def test_cancel_before_consumption_leaves_grant_issued(self):
        grant=self.grant(); cancel=threading.Event(); cancel.set()
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'cancelled'):
            policy.execute_policy_run(self.plan,self.store,grant['grantId'],cancel_event=cancel)
        saved=json.loads((self.store/(grant['grantId']+'.json')).read_text())
        self.assertEqual('issued',saved['state']);self.assertFalse(self.dest.exists())

    def test_dispatch_failure_consumes_grant_and_never_automatically_retries(self):
        grant=self.grant()
        with patch.object(git_runtime,'execute_run',side_effect=git_runtime.InvalidGitRuntime('interruption')):
            with self.assertRaises(git_runtime.InvalidGitRuntime):
                policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        with patch.object(git_runtime,'execute_run') as execute:
            with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'no inspectable run'):
                policy.execute_policy_run(self.plan,self.store,grant['grantId'])
            execute.assert_not_called()
        self.assertFalse(self.dest.exists())

    def test_untrusted_store_and_source_storage_are_refused(self):
        for store in (self.fixture.repo/'grants',self.fixture.repo/'.git'/'grants',self.dest/'grants'):
            with self.subTest(store=store),self.assertRaises(policy.InvalidRuntimePolicy):
                policy.issue_operator_grant(self.plan,store,acknowledge=self.plan['planDigest'])
        self.store.mkdir(mode=0o755)
        # mkdir's mode is filtered by the caller's umask; force the unsafe fixture.
        self.store.chmod(0o755)
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o755)
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'0700'): self.grant()

    def test_modified_and_symlink_grants_fail_closed(self):
        grant=self.grant();path=self.store/(grant['grantId']+'.json')
        bad=deepcopy(grant);bad['runDirectory']=str(self.root/'other');path.write_text(json.dumps(bad))
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'changed'):
            policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        path.unlink();path.symlink_to(self.root/'missing')
        with self.assertRaises(policy.InvalidRuntimePolicy):
            policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        self.assertFalse(self.dest.exists())

    def test_corrupt_result_is_not_hidden_by_idempotent_retry(self):
        grant=self.grant();policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        (self.dest/'state.json').write_text('{}')
        with self.assertRaises(git_runtime.InvalidGitRuntime):
            policy.execute_policy_run(self.plan,self.store,grant['grantId'])

    def test_resume_and_abort_require_new_purpose_grants(self):
        grant=self.grant();policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'action'):
            policy.recover_policy_run(self.plan,self.store,grant['grantId'],action='abort')
        abort=self.grant(action='abort')
        result=policy.recover_policy_run(self.plan,self.store,abort['grantId'],action='abort')
        self.assertEqual('aborted',result['runtime']['phase'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))


    def test_schemas_and_public_cli_refusal_and_success(self):
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
        root=Path(__file__).resolve().parents[1]
        schemas=[json.loads(p.read_text()) for p in (root/'schemas').rglob('*.json')]
        registry=Registry().with_resources((s['$id'],Resource.from_contents(s))
                                           for s in schemas if '$id' in s)
        schema=json.loads((root/'schemas/0.1.0-alpha/runtime-policy.schema.json').read_text())
        Draft202012Validator(schema,registry=registry).validate(self.plan)
        file=self.root/'plan.json';file.write_text(json.dumps(self.plan))
        def cli(*args):
            return subprocess.run([sys.executable,'-m','agent_braid',*args],cwd=root,
                                  capture_output=True,text=True,timeout=90)
        bad=cli('grant-policy-run',str(file),'--grant-store',str(self.store),
                '--acknowledge','wrong')
        self.assertEqual(2,bad.returncode,bad.stderr)
        self.assertEqual('rejected',json.loads(bad.stdout)['status'])
        self.assertFalse(self.store.exists())
        issued=cli('grant-policy-run',str(file),'--grant-store',str(self.store),
                   '--acknowledge',self.plan['planDigest'])
        self.assertEqual(0,issued.returncode,issued.stderr)
        grant=json.loads(issued.stdout)
        schema=json.loads((root/'schemas/0.1.0-alpha/runtime-operator-grant.schema.json').read_text())
        Draft202012Validator(schema).validate(grant)
        completed=cli('execute-policy-run',str(file),'--grant-store',str(self.store),
                      '--grant-id',grant['grantId'])
        self.assertEqual(0,completed.returncode,completed.stderr)
        self.assertEqual('completed',json.loads(completed.stdout)['runtime']['status'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))

    def test_store_lock_refuses_concurrent_owner(self):
        self.grant()
        with policy._store_lock(self.store):
            with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'busy'): self.grant()
        self.assertFalse(self.dest.exists())

    def test_prefix_retry_is_read_only_and_resume_uses_new_grant(self):
        from agent_braid.git_process import GitExecutionCancelled
        grant=self.grant();cancel=threading.Event();original=git_runtime._git
        def interrupt(repo,env,budget,*args,**kwargs):
            result=original(repo,env,budget,*args,**kwargs)
            if args[:2]==('update-ref',git_runtime.RESULT_REF) and len(args)>2:
                if args[2]==self.plan['runtimeManifest']['steps'][0]['commit']:
                    cancel.set()
            return result
        with patch.object(git_runtime,'_git',side_effect=interrupt):
            with self.assertRaises(GitExecutionCancelled):
                policy.execute_policy_run(self.plan,self.store,grant['grantId'],cancel_event=cancel)
        before=self.fixture.snapshot(self.dest)
        prefix=policy.execute_policy_run(self.plan,self.store,grant['grantId'])
        self.assertEqual('not-repeated',prefix['dispatch'])
        self.assertEqual('verified-prefix',prefix['runtime']['status'])
        self.assertEqual(['a'],prefix['runtime']['completedOperations'])
        self.assertEqual(before,self.fixture.snapshot(self.dest))
        resume=self.grant(action='resume')
        completed=policy.recover_policy_run(self.plan,self.store,resume['grantId'],action='resume')
        self.assertEqual('completed',completed['runtime']['status'])
        self.assertEqual(['a','b'],completed['runtime']['completedOperations'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))


if __name__=='__main__': unittest.main()
