# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic reporting diagnostics, not an executed experiment or accepted utility."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_decisions import freeze_decision_policy, simulate_decisions
from agent_braid.forecast_evaluation import freeze_offline_evaluation
from agent_braid.forecast_lab import operation_episode, signal_episode
from agent_braid.forecast_pairs import rehearse_paired_policies, synthetic_grant_fixtures
from agent_braid.forecast_report import synthetic_utility_report, validate_synthetic_utility_report
from agent_braid.forecast_shadow import rehearse_shadow_recovery


class SyntheticReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        partitions = ('development', 'calibration', 'holdout', 'holdout', 'holdout')
        cls.signals = [signal_episode('constant', seed=i, partition=p) for i, p in enumerate(partitions)]
        cls.operations = [operation_episode(seed=i, partition=p) for i, p in zip((3, 4, 7, 8, 9), partitions)]
        evaluation = freeze_offline_evaluation(cls.signals, cls.operations)
        frozen = freeze_decision_policy(cls.signals, cls.operations, evaluation=evaluation)
        decisions = simulate_decisions(cls.signals, cls.operations, evaluation=evaluation, frozen=frozen)
        cls.base_pairing = dict(evaluation=evaluation, frozen=frozen, decisions=decisions,
                                grants=synthetic_grant_fixtures(decisions))
        cls.base_paired = rehearse_paired_policies(cls.signals, cls.operations, **cls.base_pairing)

    def setUp(self):
        self.pairing = deepcopy(self.base_pairing)
        self.paired = deepcopy(self.base_paired)
        self.plan = {'version': 'agent-braid-synthetic-report-plan-v1',
                     'primaryGroups': ['local-fixture'],
                     'roster': {e['episodeGroup']: 'local-fixture' for e in self.paired['episodes']},
                     'cyclesPerEpisode': 2, 'minimumEpisodes': 2, 'seed': 71, 'replicates': 64,
                     'confidence': .95, 'minimumRatio': 1.1, 'lowerBoundMinimum': 1.0}
        cycle = {'serial-reference': {'baseTicks': 160, 'advisoryTicks': 0},
                 'non-model-reference': {'baseTicks': 120, 'advisoryTicks': 0},
                 'forecast-choice': {'baseTicks': 80, 'advisoryTicks': 10}}
        self.timings = {group: [deepcopy(cycle), deepcopy(cycle)] for group in self.plan['roster']}

    def report(self, **changes):
        args = dict(paired=self.paired, pairing=self.pairing, plan=self.plan, timing_fixtures=self.timings)
        return synthetic_utility_report(self.signals, self.operations, **{**args, **changes})

    def holdout(self):
        return [e['episodeGroup'] for e in self.paired['episodes'] if e['partition'] == 'holdout']

    def test_positive_fixture_never_accepts_utility_or_complete_costs(self):
        report = self.report()
        self.assertEqual('synthetic-positive', report['diagnostic'])
        self.assertEqual(5, len(report['episodes']))
        holdout = next(g for g in report['groups'] if g['partition'] == 'holdout')
        stats = holdout['comparisons']['non-model-reference']
        self.assertEqual(3, stats['episodeCount'])
        self.assertEqual([4/3, 4/3], stats['interval'])
        self.assertEqual(30, report['episodes'][0]['additionalOverheadBreakEvenTicks']['non-model-reference'])
        for flag in ('utilityAccepted', 'executionAuthorization', 'realWorkloadEvidence'):
            self.assertFalse(report[flag])
        self.assertIsNone(report['costs']['fullDeploymentCosts'])
        self.assertFalse(report['method']['coverageGuaranteed'])

    def test_overhead_and_negative_outcomes_are_not_dropped(self):
        for cycles in self.timings.values():
            for cycle in cycles: cycle['forecast-choice']['advisoryTicks'] = 100
        report = self.report()
        self.assertEqual('synthetic-negative', report['diagnostic'])
        self.assertEqual(-60, report['episodes'][0]['additionalOverheadBreakEvenTicks']['non-model-reference'])
        self.assertEqual(5, len(report['episodes']))

    def test_missing_episode_cycles_and_arm_costs_remain_inconclusive(self):
        for kind in ('episode', 'cycle', 'arm'):
            timings = deepcopy(self.timings)
            group = self.holdout()[0]
            if kind == 'episode': del timings[group]
            elif kind == 'cycle': timings[group].pop()
            else: del timings[group][0]['forecast-choice']
            report = self.report(timing_fixtures=timings)
            row = next(e for e in report['episodes'] if e['episodeGroup'] == group)
            with self.subTest(kind=kind):
                self.assertEqual('synthetic-inconclusive', report['diagnostic'])
                self.assertEqual(2, len(row['cycles']))
                self.assertIn('missing-cycle-cost', row['reasonCodes'])
                self.assertIsNone(row['episodeMedianRatios']['non-model-reference'])

    def test_paired_failure_and_cancellation_cannot_be_hidden_by_fast_fixture(self):
        for fault in ('timeout', 'cancel', 'verification-mismatch'):
            pairing = {**self.pairing, 'faults': {self.holdout()[0]+'/forecast-choice': fault}}
            paired = rehearse_paired_policies(self.signals, self.operations, **pairing)
            report = self.report(pairing=pairing, paired=paired)
            with self.subTest(fault=fault):
                self.assertEqual('synthetic-inconclusive', report['diagnostic'])
                self.assertTrue(any('invalid-paired-arm' in e['reasonCodes'] for e in report['episodes']))

    def test_cycle_repetition_does_not_inflate_independence_or_shrink_interval(self):
        for i, group in enumerate(self.holdout()):
            for c in self.timings[group]: c['forecast-choice']['baseTicks'] += i * 20
        before = self.report()
        timings = {g: cycles*4 for g, cycles in self.timings.items()}
        after = self.report(plan={**self.plan, 'cyclesPerEpisode': 8}, timing_fixtures=timings)
        self.assertEqual(before['groups'], after['groups'])
        self.assertEqual(3, after['groups'][-1]['comparisons']['non-model-reference']['episodeCount'])

    def test_primary_groups_cannot_be_selected_after_favorable_subgroup(self):
        plan = deepcopy(self.plan)
        plan['primaryGroups'].append('empty-primary')
        report = self.report(plan=plan)
        self.assertEqual('synthetic-inconclusive', report['diagnostic'])
        self.assertEqual(2, len([g for g in report['groups'] if g['partition'] == 'holdout']))

    def test_interval_straddling_threshold_is_inconclusive(self):
        for total, group in zip((150, 100, 80), self.holdout()):
            for c in self.timings[group]: c['forecast-choice'] = {'baseTicks': total, 'advisoryTicks': 0}
        report = self.report()
        holdout = report['groups'][-1]
        self.assertEqual('synthetic-inconclusive', report['diagnostic'])
        self.assertIn('interval-does-not-resolve-threshold', holdout['reasonCodes'])

    def test_forecast_fallback_is_retained_and_cannot_count_as_model_success(self):
        evaluation = freeze_offline_evaluation(self.signals, self.operations,
                                               simulated_statuses={self.holdout()[0]+'/1': 'unavailable'})
        frozen = freeze_decision_policy(self.signals, self.operations, evaluation=evaluation)
        decisions = simulate_decisions(self.signals, self.operations, evaluation=evaluation, frozen=frozen)
        pairing = dict(evaluation=evaluation, frozen=frozen, decisions=decisions,
                       grants=synthetic_grant_fixtures(decisions))
        paired = rehearse_paired_policies(self.signals, self.operations, **pairing)
        report = self.report(paired=paired, pairing=pairing)
        self.assertEqual('synthetic-inconclusive', report['diagnostic'])
        fallback = next(e for e in report['episodes'] if 'forecast-fallback' in e['reasonCodes'])
        self.assertEqual(['forecast-unavailable'], fallback['adviceReasonCodes'])

    def test_development_and_calibration_are_not_pooled_with_holdout(self):
        plan = {**self.plan, 'minimumEpisodes': 4}
        report = self.report(plan=plan)
        self.assertEqual('synthetic-inconclusive', report['diagnostic'])
        self.assertEqual(3, report['groups'][-1]['eligibleEpisodes'])
        for group in self.plan['roster']:
            if group not in self.holdout():
                for c in self.timings[group]: c['forecast-choice']['baseTicks'] = 1
        self.assertEqual(report['groups'][-1], self.report(plan=plan)['groups'][-1])

    def test_inputs_order_and_input_mutation_do_not_change_statistics(self):
        before = deepcopy((self.paired, self.pairing, self.plan, self.timings))
        expected = self.report()
        timings = dict(reversed(list(self.timings.items())))
        self.assertEqual(expected, self.report(timing_fixtures=timings))
        self.assertEqual(before, (self.paired, self.pairing, self.plan, self.timings))

    def test_resigned_pair_and_report_are_recomputed(self):
        paired = deepcopy(self.paired)
        paired['episodes'][0]['arms'][0]['status'] = 'simulated-completed-forged'
        paired['receiptDigest'] = digest({k: v for k, v in paired.items() if k != 'receiptDigest'})
        with self.assertRaisesRegex(ForecastError, 'paired-rehearsal-drift'): self.report(paired=paired)
        report = self.report(); report['diagnostic'] = 'utility-accepted'
        report['receiptDigest'] = digest({k: v for k, v in report.items() if k != 'receiptDigest'})
        with self.assertRaisesRegex(ForecastError, 'synthetic-report-drift'):
            validate_synthetic_utility_report(report, self.signals, self.operations, paired=self.paired,
                                              pairing=self.pairing, plan=self.plan, timing_fixtures=self.timings)

    def test_unknown_roster_numeric_and_work_budgets_refuse(self):
        for change in ({'seed': True}, {'replicates': 0}, {'confidence': 1},
                       {'minimumEpisodes': 1}, {'cyclesPerEpisode': 17},
                       {'minimumRatio': float('nan')}, {'roster': {}},
                       {'primaryGroups': ['local-fixture', 'local-fixture']}):
            with self.subTest(change=change), self.assertRaises(ForecastError):
                self.report(plan={**self.plan, **change})
        with self.assertRaises(ForecastError): self.report(timing_fixtures={'unknown': []})
        self.timings[self.holdout()[0]][0]['forecast-choice']['baseTicks'] = True
        with self.assertRaises(ForecastError): self.report()

    def test_shadow_cancellation_is_reported_without_execution_recovery(self):
        event = {'kind': 'cancel', 'episodeGroup': self.holdout()[0],
                 'observedAtNs': next(e['cutoffNs'] for e in self.pairing['decisions']['decisions']
                                     if e['episodeGroup'] == self.holdout()[0])}
        policy = dict(version=1, partition='development', maximumFailures=1, maximumAbsoluteError=2)
        receipt = rehearse_shadow_recovery(self.signals, self.operations, paired=self.paired,
                                           pairing=self.pairing, monitor_policy=policy, events=[event])
        report = self.report(shadow_context=dict(receipt=receipt, monitorPolicy=policy, events=[event]))
        self.assertTrue(report['shadow']['cancelled'])
        self.assertEqual('synthetic-inconclusive', report['diagnostic'])

    def test_report_never_calls_runtime_or_model(self):
        with (patch('agent_braid.runtime_policy.execute_policy_run', side_effect=AssertionError('runtime')),
              patch('agent_braid.forecast_advice.ForecastSession.predict', side_effect=AssertionError('model'))):
            self.report()

    def scenarios(self):
        normal = self.report()
        negative = deepcopy(self.timings)
        for cycles in negative.values():
            for c in cycles: c['forecast-choice']['advisoryTicks'] = 100
        missing = deepcopy(self.timings); del missing[self.holdout()[0]]
        reports = {'positive': normal, 'negative': self.report(timing_fixtures=negative),
                   'missing': self.report(timing_fixtures=missing)}
        return {name: {**{key: report[key] for key in ('receiptDigest', 'diagnostic', 'method', 'costs')},
                       'groups': [{**{k: g[k] for k in ('partition', 'primaryGroup', 'intendedEpisodes',
                                                       'eligibleEpisodes', 'status')},
                                   'primaryComparison': g['comparisons']['non-model-reference']}
                                  for g in report['groups']]}
                for name, report in reports.items()}

    def test_retained_evidence_matches_source_and_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root/'specs/036-forecast-parallelism-experiment/evidence/t008-synthetic-report.json').read_text())
        self.assertEqual(self.scenarios(), evidence['scenarios'])
        for path, expected in evidence['inputs'].items():
            self.assertEqual(expected, hashlib.sha256((root/path).read_bytes()).hexdigest(), path)
