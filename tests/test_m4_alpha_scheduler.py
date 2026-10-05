# SPDX-License-Identifier: AGPL-3.0-only
"""Actual isolated workers, serial agreement and fail-closed C2 admission."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from agent_braid import git_runtime as runtime, runtime_scheduler as scheduler
from agent_braid import runtime_policy as policy, git_replay
from agent_braid.analysis import _digest
from agent_braid.git_process import GitExecutionCancelled, GitCommandLimitExceeded
from tests import test_git_runtime as fixtures


def rehash(value, field):
    value[field] = _digest({k:v for k,v in value.items() if k != field})


class RuntimeSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixtures.GitRuntimeTests();cls.fixture.setUp()
        cls.addClassCleanup(cls.fixture.doCleanups)
        cls.request = cls.fixture.request
        cls.manifest = runtime.prepare_run(cls.request, cls.fixture.root/'unused-result')
        cls.schedule = scheduler.prepare_schedule(cls.manifest)
        cls.evidence = scheduler.run_preparations(cls.manifest, cls.schedule)
        cls.portable, cls.advisory = git_replay.produce(runtime._analysis_request(cls.request))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=self.fixture.root);self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.dest = self.root/'result';self.store=self.root/'grants'

    def plan(self):
        return policy.prepare_policy_run(self.request,self.dest,replay_evidence=self.portable,
                                         advisory_plan=self.advisory,mode='parallel')

    def grant(self, plan, action='execute'):
        return policy.issue_operator_grant(plan,self.store,acknowledge=plan['planDigest'],action=action)

    def four_operation_request(self):
        fixture=fixtures.GitRuntimeTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        req=deepcopy(fixture.request)
        for identifier in ('c','d'):
            fixture.git('checkout','-q','-b',identifier,fixture.base)
            (fixture.repo/(identifier+'.txt')).write_text(identifier+'\n')
            fixture.git('add',identifier+'.txt');fixture.git('commit','-qm',identifier)
            req['operations'].append({'instanceId':identifier,'attemptId':identifier+'-attempt',
                                      'source':{'kind':'commit','revision':fixture.git('rev-parse','HEAD')},
                                      'dependencies':[],'uncertainPaths':[],
                                      'declaredWrites':[identifier+'.txt']})
        fixture.git('checkout','-q','main')
        for identifier in ('a','b','c','d'):(fixture.repo/(identifier+'.txt')).write_text(identifier+'\n')
        fixture.git('add','.');req['expectedFinalTree']=fixture.git('write-tree')
        fixture.git('reset','--hard','-q',fixture.base)
        req['order']=['a','b','c','d']
        return req

    def test_real_overlap_isolated_resources_and_serial_effect_agreement(self):
        self.assertEqual([['a','b']],self.schedule['waves'])
        self.assertEqual(2,self.evidence['observedPeakWorkerIntervals'])
        self.assertEqual(2,len({r['writableRepository'] for r in self.evidence['workers']}))
        self.assertTrue(all(not Path(r['writableRepository']).exists() for r in self.evidence['workers']))
        self.assertEqual('verified-worker-trees-and-effects',
                         scheduler.verify_preparations(self.manifest,self.schedule,self.evidence)['status'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))
        self.assertFalse((self.fixture.root/'unused-result').exists())

    def test_dependencies_serialize_waves_and_reversed_order_is_safe(self):
        for dependency, order in ((True,['a','b']),(False,['b','a'])):
            req=deepcopy(self.request);req['order']=order
            if dependency:req['operations'][1]['dependencies']=['a']
            manifest=runtime.prepare_run(req,self.dest);schedule=scheduler.prepare_schedule(manifest)
            evidence=scheduler.run_preparations(manifest,schedule)
            self.assertEqual([['a'],['b']] if dependency else [['b','a']],schedule['waves'])
            self.assertEqual(1 if dependency else 2,evidence['observedPeakWorkerIntervals'])
            scheduler.verify_preparations(manifest,schedule,evidence)

    def test_singleton_waves_execute_directly_without_a_thread_pool(self):
        req=deepcopy(self.request);req['operations'][1]['dependencies']=['a']
        manifest=runtime.prepare_run(req,self.dest);schedule=scheduler.prepare_schedule(manifest)
        with patch.object(scheduler,'ThreadPoolExecutor',side_effect=AssertionError('unneeded pool')):
            evidence=scheduler.run_preparations(manifest,schedule)
        self.assertEqual(['a','b'],[r['operationId'] for r in evidence['workers']])
        self.assertLessEqual(evidence['workers'][0]['finishedNs'],evidence['workers'][1]['startedNs'])
        self.assertEqual(1,evidence['observedPeakWorkerIntervals'])
        scheduler.verify_preparations(manifest,schedule,evidence)

    def test_parallel_waves_reuse_one_run_local_executor_and_wait_for_dependencies(self):
        req=self.four_operation_request()
        req['operations'][2]['dependencies']=['a']
        req['operations'][3]['dependencies']=['b']
        manifest=runtime.prepare_run(req,self.dest);schedule=scheduler.prepare_schedule(manifest)
        with patch.object(scheduler,'ThreadPoolExecutor',wraps=scheduler.ThreadPoolExecutor) as pools:
            evidence=scheduler.run_preparations(manifest,schedule)
        self.assertEqual([['a','b'],['c','d']],schedule['waves'])
        pools.assert_called_once_with(max_workers=2,thread_name_prefix='braid-fixed-patch')
        first=evidence['workers'][:2];second=evidence['workers'][2:]
        self.assertLessEqual(max(w['finishedNs'] for w in first),min(w['startedNs'] for w in second))
        self.assertEqual(2,evidence['observedPeakWorkerIntervals'])
        scheduler.verify_preparations(manifest,schedule,evidence)

    def test_singleton_failure_stops_later_waves_and_disposes_owned_scratch(self):
        req=deepcopy(self.request);req['operations'][1]['dependencies']=['a']
        manifest=runtime.prepare_run(req,self.dest);schedule=scheduler.prepare_schedule(manifest)
        observed=[]
        def fail(source, patches, entry, root, budget, origin, barrier=None):
            observed.append((root,budget,entry['operationId'],barrier))
            raise scheduler.InvalidRuntimeSchedule('singleton failed')
        with patch.object(scheduler,'_worker',side_effect=fail):
            with self.assertRaisesRegex(scheduler.InvalidRuntimeSchedule,'singleton failed'):
                scheduler.run_preparations(manifest,schedule)
        self.assertEqual(1,len(observed))
        root,budget,identifier,barrier=observed[0]
        self.assertEqual('a',identifier);self.assertIsNone(barrier)
        self.assertTrue(budget.cancel_event.is_set());self.assertFalse(root.parent.exists())
        self.assertFalse(self.dest.exists())

    def test_policy_reference_reuses_fresh_scratch_but_keeps_separate_bounded_phases(self):
        budgets=[];original=runtime._budget
        def observe(root,cancel_event=None):
            budget=original(root,cancel_event);budgets.append(budget);return budget
        with patch.object(runtime,'_prepare',wraps=runtime._prepare) as preparations:
            with patch.object(runtime,'_budget',side_effect=observe):
                plan=self.plan()
            self.assertEqual(1,preparations.call_count)
        self.assertEqual(3,len(budgets))  # Admission, worker reference, common-directory inspection.
        admission,reference,_=budgets
        self.assertIsNot(admission,reference)
        self.assertEqual(admission.temp_root,reference.temp_root)
        for budget in (admission,reference):
            self.assertEqual(runtime.LIMITS['wallSeconds'],budget.wall_seconds)
            self.assertEqual(runtime.LIMITS['gitCommands'],budget.max_commands)
            self.assertEqual(runtime.LIMITS['outputBytes'],budget.max_output_bytes)
            self.assertEqual(runtime.LIMITS['commandOutputBytes'],budget.max_command_output_bytes)
            self.assertEqual(runtime.LIMITS['scratchBytes'],budget.max_scratch_bytes)
            self.assertGreater(budget.commands,0);self.assertGreater(budget.peak_scratch_bytes,0)
            self.assertFalse(budget.temp_root.exists())
        self.assertEqual(plan['runtimeManifest'],runtime.prepare_run(self.request,self.dest))
        self.assertEqual(plan['schedule'],scheduler.prepare_schedule(plan['runtimeManifest']))

    def test_each_policy_consumer_reconstructs_without_a_cross_invocation_context(self):
        plan=self.plan()
        with patch.object(runtime,'_prepare',wraps=runtime._prepare) as preparations:
            self.assertEqual(plan,policy.verify_policy_plan(plan))
            self.assertEqual(1,preparations.call_count)
            bad=deepcopy(plan);bad['schedule']['workers'][0]['expectedTree']='0'*40
            rehash(bad['schedule'],'scheduleDigest');rehash(bad,'planDigest')
            with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'differs from reconstructed'):
                policy.verify_policy_plan(bad)
            self.assertEqual(2,preparations.call_count)
        with patch.object(runtime,'_prepare',wraps=runtime._prepare) as preparations:
            scheduler.verify_preparations(self.manifest,self.schedule,self.evidence)
            self.assertEqual(1,preparations.call_count)
        self.assertFalse(self.dest.exists())

    def test_transient_reference_disposes_scratch_on_failure_and_between_phase_cancellation(self):
        original=runtime._prepare
        for failure in ('worker','cancel'):
            roots=[];cancel=threading.Event()
            def observe(request,destination,temp,*args,**kwargs):
                roots.append(temp)
                result=original(request,destination,temp,*args,**kwargs)
                if failure=='cancel':cancel.set()
                return result
            with self.subTest(failure=failure),patch.object(runtime,'_prepare',side_effect=observe):
                with patch.object(scheduler,'_worker',side_effect=scheduler.InvalidRuntimeSchedule('reference failed')) as workers:
                    expected=GitExecutionCancelled if failure=='cancel' else scheduler.InvalidRuntimeSchedule
                    with self.assertRaises(expected):
                        scheduler._prepare_policy_schedule(self.request,self.dest,cancel_event=cancel)
                    self.assertEqual(0 if failure=='cancel' else 1,workers.call_count)
            self.assertEqual(1,len(roots));self.assertFalse(roots[0].exists())
            self.assertFalse(self.dest.exists())

    def test_transient_reference_refuses_unknown_footprints_and_stale_final_tree(self):
        for failure in ('footprint','final-tree'):
            request=deepcopy(self.request)
            if failure=='footprint':request['operations'][0]['declaredWrites']=['unknown.txt']
            else:request['expectedFinalTree']='0'*40
            with self.subTest(failure=failure),patch.object(scheduler,'_worker') as workers:
                with self.assertRaises(policy.InvalidRuntimePolicy):
                    policy.prepare_policy_run(request,self.dest,replay_evidence=self.portable,
                                              advisory_plan=self.advisory,mode='parallel')
                workers.assert_not_called()
            self.assertFalse(self.dest.exists())

    def test_changed_footprints_limits_and_stale_inputs_never_start_workers(self):
        mutations=[lambda s:s['workers'][0]['reads'].clear(),
                   lambda s:s['workers'][0]['writes'].append('unknown.txt'),
                   lambda s:s['workers'][0]['sharedResources'].clear(),
                   lambda s:s['workers'][0].update(inputTree='0'*40),
                   lambda s:s['resourceLimits'].update(workers=3),
                   lambda s:s['resourceLimits'].update(childAddressSpaceBytes=False),
                   lambda s:s.update(waves=[['a'],['b']])]
        for mutate in mutations:
            bad=deepcopy(self.schedule);mutate(bad);rehash(bad,'scheduleDigest')
            with self.subTest(mutate=mutate),patch.object(scheduler,'_worker') as worker:
                with self.assertRaises(scheduler.InvalidRuntimeSchedule):
                    scheduler.run_preparations(self.manifest,bad)
                worker.assert_not_called()

    def test_trace_corruption_is_refused_even_with_recomputed_digest(self):
        mutations=[lambda e:e['workers'].pop(),
                   lambda e:e['workers'][0].update(outputTree='0'*40),
                   lambda e:e['workers'][0]['effects'].clear(),
                   lambda e:e['workers'][1].update(writableRepository=e['workers'][0]['writableRepository'],
                                                   writableIndex=e['workers'][0]['writableIndex']),
                   lambda e:e['workers'][0].update(writableRepository=str(self.fixture.repo),
                                                   writableIndex=str(self.fixture.repo/'index')),
                   lambda e:e.update(observedPeakWorkerIntervals=0),
                   lambda e:e['workers'][0].update(startedNs=True),
                   lambda e:e['metrics'].update(gitCommands=257)]
        for mutate in mutations:
            bad=deepcopy(self.evidence);mutate(bad);rehash(bad,'evidenceDigest')
            with self.subTest(mutate=mutate),self.assertRaises(scheduler.InvalidRuntimeSchedule):
                scheduler.verify_preparations(self.manifest,self.schedule,bad)

    def test_failed_worker_cancels_siblings_and_never_allocates_result(self):
        cancellation=[]
        def fail(source, patches, entry, root, budget, origin, barrier):
            barrier.wait(timeout=10)
            if entry['operationId']=='a':raise scheduler.InvalidRuntimeSchedule('failed a')
            for _ in range(200):
                if budget.cancel_event.is_set():
                    cancellation.append(True);return {}
                threading.Event().wait(.01)
            self.fail('sibling did not receive cancellation')
        with patch.object(scheduler,'_worker',side_effect=fail):
            with self.assertRaisesRegex(scheduler.InvalidRuntimeSchedule,'failed a'):
                scheduler.run_preparations(self.manifest,self.schedule)
        self.assertEqual([True],cancellation);self.assertFalse(self.dest.exists())

    def test_cancelled_admission_does_not_publish(self):
        event=threading.Event();event.set()
        with self.assertRaises(GitExecutionCancelled):
            scheduler.run_preparations(self.manifest,self.schedule,cancel_event=event)
        self.assertFalse(self.dest.exists())

    def test_parallel_policy_dispatch_then_retry_inspects_without_worker_rerun(self):
        plan=self.plan();grant=self.grant(plan)
        result=policy.execute_policy_run(plan,self.store,grant['grantId'])
        self.assertEqual('completed',result['runtime']['phase'])
        self.assertEqual('verified-worker-trees-and-effects',result['preparationVerification']['status'])
        with patch.object(scheduler,'run_preparations') as workers:
            retry=policy.execute_policy_run(plan,self.store,grant['grantId']);workers.assert_not_called()
        self.assertEqual('not-repeated',retry['dispatch'])
        self.assertEqual('verified-completed',retry['runtime']['status'])
        self.assertEqual(result['runtime']['resultTree'],retry['runtime']['resultTree'])
        journal=self.store/policy._preparation_name(plan)
        bad=json.loads(journal.read_text());bad['workers'].pop();rehash(bad,'evidenceDigest')
        journal.write_text(json.dumps(bad))
        with self.assertRaises(scheduler.InvalidRuntimeSchedule):
            policy.execute_policy_run(plan,self.store,grant['grantId'])
        self.assertEqual(self.fixture.before,self.fixture.snapshot(self.fixture.repo))

    def test_parallel_failure_consumes_grant_without_serial_publication(self):
        plan=self.plan();grant=self.grant(plan)
        with patch.object(scheduler,'run_preparations',side_effect=scheduler.InvalidRuntimeSchedule('no workers')):
            with self.assertRaises(scheduler.InvalidRuntimeSchedule):
                policy.execute_policy_run(plan,self.store,grant['grantId'])
        self.assertFalse(self.dest.exists())
        self.assertEqual('consumed',json.loads((self.store/(grant['grantId']+'.json')).read_text())['state'])
        with self.assertRaisesRegex(policy.InvalidRuntimePolicy,'no inspectable run'):
            policy.execute_policy_run(plan,self.store,grant['grantId'])

    def test_new_recovery_grant_preserves_worker_journal_without_rerun(self):
        plan=self.plan();grant=self.grant(plan);cancel=threading.Event()
        original=runtime._atomic_json
        def checkpoint(root,name,value):
            original(root,name,value)
            if name=='state.json' and value.get('nextIndex')==1 and value.get('phase')=='ready':cancel.set()
        with patch.object(runtime,'_atomic_json',side_effect=checkpoint):
            with self.assertRaises(GitExecutionCancelled):
                policy.execute_policy_run(plan,self.store,grant['grantId'],cancel_event=cancel)
        cancel.clear();resume=self.grant(plan,'resume')
        with patch.object(scheduler,'run_preparations') as workers:
            report=policy.recover_policy_run(plan,self.store,resume['grantId'],action='resume')
            workers.assert_not_called()
        self.assertEqual('completed',report['runtime']['phase'])
        self.assertEqual(['a','b'],report['runtime']['completedOperations'])
        self.assertEqual(2,report['preparation']['observedPeakWorkerIntervals'])

    def test_four_workers_are_bounded_and_independently_replayable(self):
        req=self.four_operation_request()
        manifest=runtime.prepare_run(req,self.dest);schedule=scheduler.prepare_schedule(manifest)
        evidence=scheduler.run_preparations(manifest,schedule)
        self.assertEqual(4,evidence['observedPeakWorkerIntervals'])
        self.assertEqual(4,len({r['writableIndex'] for r in evidence['workers']}))
        scheduler.verify_preparations(manifest,schedule,evidence)

    def test_shared_budget_exhaustion_fans_out_without_publication(self):
        original=runtime._budget
        def limited(root,cancel_event=None):
            budget=original(root,cancel_event);budget.max_commands=1;return budget
        with patch.object(runtime,'_budget',side_effect=limited),self.assertRaises(GitCommandLimitExceeded):
            scheduler.run_preparations(self.manifest,self.schedule)
        self.assertFalse(self.dest.exists())

    def test_fresh_process_kill_preserves_prefix_and_resume_does_not_rerun_workers(self):
        plan=self.plan();grant=self.grant(plan);path=self.root/'plan.json'
        path.write_text(json.dumps(plan))
        code = """
import json,os,signal,sys
from pathlib import Path
from agent_braid import git_runtime as runtime,runtime_policy as policy
plan=json.loads(Path(sys.argv[1]).read_text())
original=runtime._atomic_json
def checkpoint(root,name,value):
    original(root,name,value)
    if name=='state.json' and value.get('nextIndex')==1 and value.get('phase')=='ready':
        os.kill(os.getpid(),signal.SIGKILL)
runtime._atomic_json=checkpoint
policy.execute_policy_run(plan,sys.argv[2],sys.argv[3])
"""
        process=subprocess.run([sys.executable,'-c',code,str(path),str(self.store),grant['grantId']],
                               cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=180)
        self.assertEqual(-9,process.returncode,process.stderr.decode())
        prefix=runtime.verify_run(self.request,self.dest)
        self.assertEqual(['a'],prefix['completedOperations'])
        resume=self.grant(plan,'resume')
        with patch.object(scheduler,'run_preparations') as workers:
            report=policy.recover_policy_run(plan,self.store,resume['grantId'],action='resume')
            workers.assert_not_called()
        self.assertEqual('completed',report['runtime']['phase'])
        self.assertEqual(['a','b'],report['runtime']['completedOperations'])

    def test_versioned_parallel_schemas_validate_actual_records(self):
        from jsonschema import Draft202012Validator
        from referencing import Registry,Resource
        root=Path(__file__).resolve().parents[1]
        schemas=[json.loads(p.read_text()) for p in (root/'schemas').rglob('*.json')]
        registry=Registry().with_resources((s['$id'],Resource.from_contents(s)) for s in schemas if '$id' in s)
        plan=self.plan();grant=self.grant(plan)
        for name,value in [('runtime-policy',plan),('runtime-operator-grant',grant),
                           ('runtime-schedule',plan['schedule']),('runtime-preparation-evidence',self.evidence)]:
            schema=json.loads((root/'schemas/0.1.0-alpha'/(name+'.schema.json')).read_text())
            Draft202012Validator(schema,registry=registry).validate(value)
        self.assertFalse(self.dest.exists())

if __name__=='__main__':unittest.main()
