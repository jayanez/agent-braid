# SPDX-License-Identifier: AGPL-3.0-only
"""Diagnostic budget attribution and fail-closed descriptive comparisons."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from agent_braid.git_process import GitCommandBudget
from scripts import profile_m4_alpha as profile


class CostProfileTests(unittest.TestCase):
    def measurement(self, function):
        runtime = SimpleNamespace(_prepare=function)
        scheduler = SimpleNamespace()
        def policy():
            return runtime._prepare()
        return SimpleNamespace(
            GitCommandBudget=GitCommandBudget, tempfile=tempfile,
            git_replay=SimpleNamespace(), git_runtime=runtime,
            runtime_policy=SimpleNamespace(prepare_policy_run=policy, runtime_scheduler=scheduler))

    def test_nested_phase_counters_cover_each_budget_once_without_changing_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            def prepare():
                budget = GitCommandBudget(Path(directory), max_commands=7)
                budget.begin_command(1);budget.record_output(13)
                return budget
            measurement = self.measurement(prepare)
            with profile.phase_capture(measurement) as capture:
                budget = measurement.runtime_policy.prepare_policy_run()
            self.assertEqual(1,len(capture['budgets']))
            record=capture['budgets'][0]
            self.assertEqual(['policy.prepare_policy_run','runtime._prepare'],record['originPhases'])
            self.assertEqual(1,record['gitCommands']);self.assertEqual(13,record['capturedOutputBytes'])
            self.assertEqual(7,record['limits']['gitCommands']);self.assertEqual(7,budget.max_commands)
            phases=capture['phases']
            self.assertEqual(['policy.prepare_policy_run','runtime._prepare'],[p['phase'] for p in phases])
            self.assertIsNone(phases[0]['parentId']);self.assertEqual(phases[0]['id'],phases[1]['parentId'])
            self.assertTrue(all(p['status']=='completed' for p in phases))
            self.assertEqual([1,1],[p['gitCommands'] for p in phases])
            self.assertEqual(1,capture['phaseSummary']['runtime._prepare']['invocations'])
            self.assertEqual(1,sum(b['gitCommands'] for b in capture['budgets']))

    def test_phase_failure_preserves_exception_and_restores_original_functions(self):
        def fail():
            raise RuntimeError('original failure')
        measurement=self.measurement(fail)
        with self.assertRaisesRegex(RuntimeError,'original failure'):
            with profile.phase_capture(measurement) as capture:
                measurement.runtime_policy.prepare_policy_run()
        self.assertIs(fail,measurement.git_runtime._prepare)
        self.assertTrue(all(p['status']=='failed' for p in capture['phases']))
        self.assertTrue(all('wallNs' in p for p in capture['phases']))

    def record(self, serial=100, parallel=200, serial_commands=10, parallel_commands=20):
        def sample(mode,wall,commands,capture,count):
            budgets=[{'gitCommands':commands if index==0 else 0,
                      'capturedOutputBytes':capture if index==0 else 0,'sampledPeakScratchBytes':0,
                      'limits':{'gitCommands':256,'outputBytes':8*1024*1024,
                                'commandOutputBytes':2*1024*1024,'scratchBytes':64*1024*1024,
                                'wallSeconds':60,'childAddressSpaceBytes':None}} for index in range(count)]
            phases=[{'id':0,'parentId':None,'startedNs':0,'phase':'fixture.treatment',
                     'wallNs':wall,'gitCommands':commands,'capturedOutputBytes':capture,'status':'completed'}]
            summary={'fixture.treatment':{'invocations':1,'wallNs':wall,'gitCommands':commands,
                                         'capturedOutputBytes':capture}}
            return {'mode':mode,'wallNs':wall,'resultTree':'a'*40,'gitCommands':commands,
                    'capturedOutputBytes':capture,'boundedPhaseCount':count,'parentCpuNs':0,
                    'childUserCpuNs':0,'childSystemCpuNs':0,'processLifetimePeakChildRssBytes':0,
                    'sampledPeakPhaseScratchBytes':0,'observedPeakWorkerIntervals':1 if mode=='serial' else 2,
                    'diagnostic':{'budgets':budgets,'phases':phases,'phaseSummary':summary}}
        pairs=[]
        for order in (['a','b'],['b','a']):
            for repetition in range(1,4):
                pairs.append({'order':order,'repetition':repetition,
                              'treatmentOrder':['serial','parallel'] if repetition%2 else ['parallel','serial'],
                              'equivalentFinalTree':True,
                              'samples':{'serial':sample('serial',serial,serial_commands,12,3),
                                         'parallel':sample('parallel',parallel,parallel_commands,24,6)}})
        return {'profileVersion':profile.VERSION,'status':'captured','candidateChangedDuringRun':False,
                'candidateCommit':'b'*40,'profilerSha256':'c'*64,
                'environment':{'python':'3.12','platform':'Linux','machine':'x86_64','git':'git version fixture'},
                'inputs':{name:'d'*64 for name in ('scripts/measure_m4_alpha.py',
                         'specs/021-m4-alpha-runtime/measurement-protocol.md','tests/test_git_runtime.py')},
                'pairs':pairs}

    def test_comparison_reports_full_cost_and_serial_regression_separately(self):
        baseline=self.record();candidate=self.record(serial=110,parallel=160,parallel_commands=15)
        result=profile.compare_profiles(baseline,candidate)
        self.assertTrue(result['candidateParallelImprovedObserved'])
        self.assertFalse(result['candidateSerialNotRegressedObserved'])
        self.assertEqual({'numerator':4,'denominator':5},result['modes']['parallel']['candidateOverBaselineWallRatio'])
        self.assertEqual(5,result['modes']['parallel']['candidateGitCommandsSaved'])
        self.assertEqual(0,result['modes']['serial']['candidateGitCommandsSaved'])
        self.assertEqual('descriptive-comparison',result['status'])

    def test_null_candidate_is_not_reported_as_an_improvement(self):
        baseline=self.record();result=profile.compare_profiles(baseline,deepcopy(baseline))
        self.assertFalse(result['candidateParallelImprovedObserved'])
        self.assertTrue(result['candidateSerialNotRegressedObserved'])
        self.assertEqual({'numerator':1,'denominator':1},result['modes']['parallel']['candidateOverBaselineWallRatio'])

    def test_mismatched_or_invalid_captures_are_refused(self):
        mutations=[lambda r:r.update(status='invalidated'),lambda r:r.update(candidateChangedDuringRun=True),
                   lambda r:r['pairs'].pop(),lambda r:r.update(profilerSha256='different'),
                   lambda r:r['environment'].update(machine='arm64'),
                   lambda r:r['inputs'].update({'tests/test_git_runtime.py':'changed'}),
                   lambda r:r['pairs'][0].update(order=['b','a']),
                   lambda r:r['pairs'][0].update(treatmentOrder=['parallel','serial']),
                   lambda r:r['pairs'][0].update(equivalentFinalTree=False),
                   lambda r:r['pairs'][0]['samples']['parallel'].update(resultTree='different')]
        baseline=self.record()
        for mutate in mutations:
            candidate=deepcopy(baseline);mutate(candidate)
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):
                profile.compare_profiles(baseline,candidate)

    def test_negative_float_and_boolean_metrics_cannot_forge_an_improvement(self):
        baseline=self.record()
        for target in ('baseline','candidate'):
            for metric in profile.SAMPLE_METRICS:
                for malformed in (-1,1.5,True):
                    left,right=deepcopy(baseline),deepcopy(baseline)
                    value=left if target=='baseline' else right
                    value['pairs'][0]['samples']['parallel'][metric]=malformed
                    with self.subTest(target=target,metric=metric,value=malformed),self.assertRaises(ValueError):
                        profile.compare_profiles(left,right)

    def test_zero_wall_time_and_nonpositive_phase_count_are_refused_before_division(self):
        baseline=self.record()
        for mode in ('serial','parallel'):
            for target in ('baseline','candidate'):
                for metric in ('wallNs','boundedPhaseCount','observedPeakWorkerIntervals'):
                    left,right=deepcopy(baseline),deepcopy(baseline)
                    value=left if target=='baseline' else right
                    value['pairs'][0]['samples'][mode][metric]=0
                    with self.subTest(mode=mode,target=target,metric=metric),self.assertRaises(ValueError):
                        profile.compare_profiles(left,right)

    def test_changed_counters_must_reconcile_with_unique_budgets(self):
        baseline=self.record()
        for metric in ('gitCommands','capturedOutputBytes','sampledPeakPhaseScratchBytes','boundedPhaseCount'):
            candidate=deepcopy(baseline);candidate['pairs'][0]['samples']['parallel'][metric]+=1
            with self.subTest(metric=metric),self.assertRaisesRegex(ValueError,'budget'):
                profile.compare_profiles(baseline,candidate)

    def test_zero_median_wall_divisors_are_refused_as_invalid_records(self):
        baseline=self.record()
        for target in ('baseline','candidate'):
            for mode in ('serial','parallel'):
                left,right=deepcopy(baseline),deepcopy(baseline)
                value=left if target=='baseline' else right
                for pair in value['pairs']:pair['samples'][mode]['wallNs']=0
                with self.subTest(target=target,mode=mode),self.assertRaises(ValueError):
                    profile.compare_profiles(left,right)

    def test_forged_budget_and_phase_metrics_are_refused(self):
        baseline=self.record()
        mutations=[lambda d:d['budgets'][0].update(gitCommands=-1),
                   lambda d:d['budgets'][0].update(capturedOutputBytes=True),
                   lambda d:d['budgets'][0].update(sampledPeakScratchBytes=1.5),
                   lambda d:d['budgets'][0]['limits'].update(wallSeconds=float('nan')),
                   lambda d:d['budgets'][0]['limits'].update(gitCommands=True),
                   lambda d:d['budgets'][0]['limits'].update(outputBytes=1),
                   lambda d:d['phases'][0].update(wallNs=-1),
                   lambda d:d['phases'][0].update(status='failed'),
                   lambda d:d['phases'][0].update(id=True),
                   lambda d:d['phases'][0].update(parentId=0),
                   lambda d:d['phaseSummary']['fixture.treatment'].update(wallNs=-1),
                   lambda d:d['phaseSummary']['fixture.treatment'].update(invocations=True),
                   lambda d:d['phaseSummary']['fixture.treatment'].update(gitCommands=0)]
        for mutate in mutations:
            candidate=deepcopy(baseline);mutate(candidate['pairs'][0]['samples']['parallel']['diagnostic'])
            with self.subTest(mutation=mutate),self.assertRaises(ValueError):
                profile.compare_profiles(baseline,candidate)


if __name__=='__main__':
    unittest.main()
