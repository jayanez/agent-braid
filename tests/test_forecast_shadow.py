# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic shadow integration; no model, VM, runtime or physical measurement."""
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
from agent_braid.forecast_shadow import rehearse_shadow_recovery, validate_shadow_recovery


class ShadowRecoveryTests(unittest.TestCase):
    def setUp(self):
        partitions = ('development', 'calibration', 'holdout')
        self.signals = [signal_episode('constant', seed=i, partition=p)
                        for i, p in enumerate(partitions)]
        self.operations = [operation_episode(seed=i, partition=p)
                           for i, p in zip((3, 4, 7), partitions)]
        evaluation = freeze_offline_evaluation(self.signals, self.operations)
        frozen = freeze_decision_policy(self.signals, self.operations, evaluation=evaluation)
        self.decisions = simulate_decisions(self.signals, self.operations,
                                            evaluation=evaluation, frozen=frozen)
        self.pairing = dict(evaluation=evaluation, frozen=frozen, decisions=self.decisions,
                            grants=synthetic_grant_fixtures(self.decisions))
        self.paired = rehearse_paired_policies(self.signals, self.operations, **self.pairing)
        self.policy = dict(version=1, partition='development', maximumFailures=1,
                           maximumAbsoluteError=2)

    def event(self, index=0, actual=99):
        row = self.decisions['decisions'][index]
        forecast = row['request']['forecast']
        time = forecast['futureTimesNs'][0]
        return {'kind': 'outcome', 'episodeGroup': row['episodeGroup'], 'observedAtNs': time,
                'outcome': {'version': 'agent-braid-synthetic-outcome-v1', 'sourceKind': 'synthetic',
                            'forecastDigest': forecast['packetDigest'], 'eventNs': time,
                            'availableAtNs': time, 'actual': actual,
                            'targetId': forecast['targetIds'][0], 'unit': forecast['units'][0]}}

    def run_shadow(self, events, **changes):
        args = dict(paired=self.paired, pairing=self.pairing, monitor_policy=self.policy, events=events)
        return rehearse_shadow_recovery(self.signals, self.operations, **{**args, **changes})

    def scenarios(self):
        first = self.event()
        cancel = {k: v for k, v in first.items() if k != 'outcome'}
        cancel['kind'] = 'cancel'
        scenarios = {'rollback': [first, self.event(1)], 'cancel': [cancel, first], 'empty': []}
        return {name: self.run_shadow(events) for name, events in scenarios.items()}

    def test_rollback_retains_pending_labels_and_frozen_reference(self):
        report = self.run_shadow([self.event(), self.event(1)])
        self.assertTrue(report['rolledBack'])
        self.assertEqual(['off', 'off'], [r['modeAfter'] for r in report['records']])
        for record in report['records']:
            self.assertEqual('observed-synthetic-label', record['status'])
            self.assertEqual(record['referenceAction'], record['selectedAction'])
            self.assertFalse(record['executionAuthorization'])
        self.assertEqual(6, report['costs']['advisoryTicks'])
        self.assertIsNone(report['costs']['fullDeploymentCosts'])
        self.assertFalse(report['utilityAccepted'])

    def test_cancellation_retains_events_without_counting_labels_or_resuming(self):
        outcome = self.event()
        cancel = {k: v for k, v in outcome.items() if k != 'outcome'}
        cancel['kind'] = 'cancel'
        report = self.run_shadow([cancel, outcome])
        self.assertTrue(report['cancelled'])
        self.assertFalse(report['rolledBack'])
        self.assertEqual('retained-after-cancellation', report['records'][1]['status'])
        self.assertIsNone(report['records'][1]['trace'])
        self.assertEqual('off', report['modeAfter'])

    def test_duplicate_identity_cannot_increment_failure_counter(self):
        first = self.event()
        changed = deepcopy(first)
        changed['outcome']['actual'] = 999
        changed['outcome']['availableAtNs'] += 1
        changed['observedAtNs'] += 1
        with self.assertRaisesRegex(ForecastError, 'duplicate-shadow-label'):
            self.run_shadow([first, changed])

    def test_unavailable_early_or_mismatched_labels_refuse(self):
        for field, value in (('availableAtNs', 10**18), ('eventNs', 0),
                             ('forecastDigest', 'a'*64), ('unit', 'wrong'),
                             ('sourceKind', 'permissioned'), ('targetId', 'wrong')):
            event = self.event()
            event['outcome'][field] = value
            with self.subTest(field=field), self.assertRaises(ForecastError):
                self.run_shadow([event])

    def test_observation_order_and_unknown_groups_refuse(self):
        event = self.event()
        late = deepcopy(event)
        late['observedAtNs'] += 1
        with self.assertRaisesRegex(ForecastError, 'shadow-observation-order'):
            self.run_shadow([late, event])
        event['episodeGroup'] = 'unknown'
        with self.assertRaisesRegex(ForecastError, 'unknown-shadow-episode'):
            self.run_shadow([event])

    def test_resigned_pair_and_decision_changes_refuse(self):
        paired = deepcopy(self.paired)
        paired['episodes'][0]['arms'][0]['action'] = 'unknown'
        paired['receiptDigest'] = digest({k: v for k, v in paired.items() if k != 'receiptDigest'})
        with self.assertRaisesRegex(ForecastError, 'paired-rehearsal-drift'):
            self.run_shadow([], paired=paired)
        pairing = deepcopy(self.pairing)
        pairing['decisions']['decisions'][0]['advice']['selectedAction'] = 'unknown'
        with self.assertRaisesRegex(ForecastError, 'paired-decision-drift'):
            self.run_shadow([], pairing=pairing)

    def test_no_runtime_or_model_and_inputs_unchanged(self):
        before = deepcopy((self.paired, self.pairing, self.policy))
        with (patch('agent_braid.runtime_policy.execute_policy_run', side_effect=AssertionError('runtime')),
              patch('agent_braid.forecast_advice.ForecastSession.predict', side_effect=AssertionError('model'))):
            self.run_shadow([self.event()])
        self.assertEqual(before, (self.paired, self.pairing, self.policy))

    def test_recomputed_trace_rejects_resigned_mode_change(self):
        events = [self.event()]
        report = self.run_shadow(events)
        report['modeAfter'] = 'promoted'
        report['receiptDigest'] = digest({k: v for k, v in report.items() if k != 'receiptDigest'})
        with self.assertRaisesRegex(ForecastError, 'shadow-recovery-drift'):
            validate_shadow_recovery(report, self.signals, self.operations, paired=self.paired,
                                     pairing=self.pairing, monitor_policy=self.policy, events=events)

    def test_unavailable_forecast_keeps_fallback_and_failed_label(self):
        statuses = {self.decisions['decisions'][0]['episodeGroup']+'/1': 'unavailable'}
        evaluation = freeze_offline_evaluation(self.signals, self.operations, simulated_statuses=statuses)
        frozen = freeze_decision_policy(self.signals, self.operations, evaluation=evaluation)
        decisions = simulate_decisions(self.signals, self.operations, evaluation=evaluation, frozen=frozen)
        pairing = dict(evaluation=evaluation, frozen=frozen, decisions=decisions,
                       grants=synthetic_grant_fixtures(decisions))
        paired = rehearse_paired_policies(self.signals, self.operations, **pairing)
        self.decisions = decisions
        report = self.run_shadow([self.event()], paired=paired, pairing=pairing)
        self.assertEqual(['forecast-unavailable'], report['records'][0]['fallbackReasons'])
        self.assertIsNone(report['records'][0]['trace']['absoluteError'])
        self.assertTrue(report['rolledBack'])

    def test_consultative_mode_and_holdout_monitor_tuning_refuse(self):
        pairing = deepcopy(self.pairing)
        pairing['decisions'] = simulate_decisions(self.signals, self.operations,
                                                  evaluation=pairing['evaluation'],
                                                  frozen=pairing['frozen'], mode='consultative')
        pairing['grants'] = synthetic_grant_fixtures(pairing['decisions'])
        paired = rehearse_paired_policies(self.signals, self.operations, **pairing)
        with self.assertRaisesRegex(ForecastError, 'shadow-mode-required'):
            self.run_shadow([], paired=paired, pairing=pairing)
        with self.assertRaisesRegex(ForecastError, 'unfrozen-monitor'):
            self.run_shadow([], monitor_policy={**self.policy, 'partition': 'holdout'})

    def test_late_pending_outcome_is_not_new_advice_or_authority(self):
        event = self.event(actual=1)
        event['observedAtNs'] = self.decisions['decisions'][0]['advice']['expiresNs'] + 100
        report = self.run_shadow([event])
        self.assertEqual('observed-synthetic-label', report['records'][0]['status'])
        self.assertFalse(report['executionAuthorization'])

    def test_event_shapes_times_and_budget_refuse(self):
        event = self.event()
        for changed in (None, {}, {**event, 'kind': 'resume'},
                        {**event, 'observedAtNs': True}, {**event, 'observedAtNs': 0},
                        {**event, 'extra': 'grant'}):
            with self.subTest(event=changed), self.assertRaises(ForecastError):
                self.run_shadow([changed])
        with self.assertRaisesRegex(ForecastError, 'invalid-shadow-events'):
            self.run_shadow([event]*4097)

    def test_retained_evidence_matches_inputs_and_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root/'specs/037-forecast-advisory-integration/evidence/t005-t006-shadow-recovery.json').read_text())
        self.assertEqual(self.scenarios(), evidence['scenarios'])
        for path, expected in evidence['inputs'].items():
            self.assertEqual(expected, hashlib.sha256((root/path).read_bytes()).hexdigest(), path)
