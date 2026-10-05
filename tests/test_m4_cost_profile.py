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
        pairs=[]
        for order in (['a','b'],['b','a']):
            for repetition in range(1,4):
                pairs.append({'order':order,'repetition':repetition,
                              'treatmentOrder':['serial','parallel'] if repetition%2 else ['parallel','serial'],
                              'equivalentFinalTree':True,
                              'samples':{'serial':{'wallNs':serial,'resultTree':'a'*40,'gitCommands':serial_commands,
                                                   'capturedOutputBytes':12,'boundedPhaseCount':3},
                                         'parallel':{'wallNs':parallel,'resultTree':'a'*40,'gitCommands':parallel_commands,
                                                     'capturedOutputBytes':24,'boundedPhaseCount':6}}})
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


if __name__=='__main__':
    unittest.main()
