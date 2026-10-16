# SPDX-License-Identifier: AGPL-3.0-only
"""T005/T006 in-memory pairing, grant fixtures, failures and cost controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_lab import signal_episode, operation_episode
from agent_braid.forecast_evaluation import freeze_offline_evaluation
from agent_braid.forecast_decisions import freeze_decision_policy, simulate_decisions
from agent_braid.forecast_experiment import rehearse_frozen_policy_arms
from agent_braid.forecast_pairs import synthetic_grant_fixtures, validate_paired_rehearsal


class PairedRehearsalTests(unittest.TestCase):
    def setUp(self):
        partitions = ('development', 'calibration', 'holdout')
        self.signals = [signal_episode(f, seed=i, partition=p)
                        for i, (f, p) in enumerate(zip(('trend', 'constant', 'constant'), partitions))]
        self.operations = [operation_episode(seed=i, partition=p) for i, p in zip((3, 4, 7), partitions)]
        self.evaluation = freeze_offline_evaluation(self.signals, self.operations)
        self.frozen = freeze_decision_policy(self.signals, self.operations, evaluation=self.evaluation)
        self.decisions = simulate_decisions(self.signals, self.operations,
                                            evaluation=self.evaluation, frozen=self.frozen)
        self.kwargs = dict(evaluation=self.evaluation, frozen=self.frozen,
                           decisions=self.decisions, grants=synthetic_grant_fixtures(self.decisions))

    def run_pairs(self, **changes):
        return rehearse_frozen_policy_arms(self.signals, self.operations, **{**self.kwargs, **changes})

    def evidence_scenarios(self):
        key = next(iter(self.kwargs['grants']))
        reports = {'normal': self.run_pairs(), **{fault: self.run_pairs(faults={key: fault})
                   for fault in ('timeout', 'cancel', 'verification-mismatch')}}
        return {name: {'receiptDigest': r['receiptDigest'], 'summary': r['summary'],
                       'costs': r['costs'], 'arms': [[{'arm': a['arm'], 'status': a['status'],
                         'reasonCodes': a['reasonCodes']} for a in e['arms']] for e in r['episodes']]}
                for name, r in reports.items()}

    def test_retained_evidence_replays_exact_candidate_bound_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        evidence = json.loads((root/'specs/036-forecast-parallelism-experiment/evidence/t005-t006-paired-rehearsal.json').read_text())
        self.assertEqual(self.evidence_scenarios(), evidence['scenarios'])
        self.assertEqual({'agent_braid/forecast_pairs.py', 'agent_braid/forecast_experiment.py',
                          'agent_braid/forecast_decisions.py', 'agent_braid/forecast_evaluation.py',
                          'agent_braid/forecast_lab.py', 'agent_braid/forecast_policy.py',
                          'tests/test_forecast_pairs.py'}, set(evidence['inputs']))
        for path, expected in evidence['inputs'].items():
            self.assertEqual(expected, hashlib.sha256((root/path).read_bytes()).hexdigest(), path)

    def test_integrated_reproducible_balanced_order_and_equivalent_fixture_results(self):
        report = self.run_pairs()
        self.assertEqual(report, self.run_pairs())
        self.assertEqual(dict(intendedEpisodes=3, intendedArms=9, invalidEpisodes=0, completedArms=9), report['summary'])
        self.assertEqual(9, len({r['scopeDigest'] for e in report['episodes'] for r in e['arms']}))
        for name in ('serial-reference', 'non-model-reference', 'forecast-choice'):
            self.assertEqual({0, 1, 2}, {e['order'].index(name) for e in report['episodes']})
        for episode, decision in zip(report['episodes'], self.decisions['decisions']):
            self.assertTrue(all(r['executionKind'] == 'in-memory-fixture' for r in episode['arms']))
            self.assertEqual(1, len({r['simulatedResultDigest'] for r in episode['arms']}))
            self.assertEqual({a['arm']: (a['action'], a['planDigest']) for a in decision['arms']},
                             {a['arm']: (a['action'], a['planDigest']) for a in episode['arms']})
        self.assertFalse(report['executionAuthorization'])
        self.assertFalse(report['utilityAccepted'])
        self.assertIsNone(report['costs']['fullDeploymentCosts'])

    def test_simulated_ledger_is_contiguous_includes_cleanup_export_and_reconciles(self):
        report = self.run_pairs()
        phases = [p for e in report['episodes'] for r in e['arms'] for p in r['phases']]
        self.assertEqual(list(range(90)), [p['startTick'] for p in phases])
        self.assertEqual(report['costs']['totalTicks'], sum(p['endTick']-p['startTick'] for p in phases))
        self.assertEqual('synthetic-tick', report['costs']['unit'])
        self.assertEqual(['cleanup', 'export'], [p['stage'] for p in phases[-2:]])

    def test_shadow_disagreement_executes_only_reference_fixture_choice(self):
        differences = [d for d in self.decisions['decisions'] if d['advice']['proposedAction'] != d['advice']['referenceAction']]
        self.assertGreater(len(differences), 0)
        report = self.run_pairs()
        for e in report['episodes']:
            actions = {a['arm']: a['action'] for a in e['arms']}
            self.assertEqual(actions['non-model-reference'], actions['forecast-choice'])

    def test_consultative_mode_keeps_actual_frozen_non_model_reference(self):
        decisions = simulate_decisions(self.signals, self.operations, evaluation=self.evaluation,
                                       frozen=self.frozen, mode='consultative')
        report = self.run_pairs(decisions=decisions, grants=synthetic_grant_fixtures(decisions))
        differences = [e for e in report['episodes'] if len({r['action'] for r in e['arms']}) > 1]
        self.assertGreater(len(differences), 0)
        self.assertEqual(9, report['summary']['completedArms'])

    def test_missing_copied_wrong_and_resigned_grants_refuse_before_execution(self):
        first, second = list(self.kwargs['grants'])[:2]
        for modification in ('missing', 'copy', 'plan', 'authority'):
            grants = deepcopy(self.kwargs['grants'])
            if modification == 'missing': del grants[first]
            elif modification == 'copy': grants[first] = grants[second]
            else:
                grants[first]['planDigest' if modification == 'plan' else 'executionAuthorization'] = 'a'*64 if modification == 'plan' else True
                grants[first]['fixtureDigest'] = digest({k: v for k, v in grants[first].items() if k != 'fixtureDigest'})
            with self.subTest(modification=modification):
                report = self.run_pairs(grants=grants)
                row = report['episodes'][0]['arms'][0]
                self.assertEqual('refused', row['status'])
                self.assertEqual(['simulation-grant-mismatch'], row['reasonCodes'])
                self.assertNotIn('isolated-execution', [p['stage'] for p in row['phases']])
                self.assertEqual(['cleanup', 'export'], [p['stage'] for p in row['phases'][-2:]])
                self.assertEqual(1, report['summary']['invalidEpisodes'])
                self.assertEqual(9, report['summary']['intendedArms'])

    def test_timeout_mismatch_and_cancellation_keep_all_attempted_and_not_run_arms(self):
        key = next(iter(self.kwargs['grants']))
        for fault, status in (('timeout', 'timed-out'), ('verification-mismatch', 'failed-verification'), ('cancel', 'cancelled')):
            with self.subTest(fault=fault):
                report = self.run_pairs(faults={key: fault})
                arms = report['episodes'][0]['arms']
                self.assertEqual(status, arms[0]['status'])
                self.assertEqual(['cleanup', 'export'], [p['stage'] for p in arms[0]['phases'][-2:]])
                self.assertEqual(3, len(arms))
                self.assertEqual(1, report['summary']['invalidEpisodes'])
                expected = 'not-run-after-cancellation' if fault == 'cancel' else 'simulated-completed'
                self.assertEqual([expected]*2, [r['status'] for r in arms[1:]])

    def test_expired_decisions_refuse_every_arm_without_using_grants(self):
        group = self.decisions['decisions'][0]['episodeGroup']
        report = self.run_pairs(use_offsets={group: 2*self.signals[0]['window']['stepNs']})
        arms = report['episodes'][0]['arms']
        self.assertEqual(['refused']*3, [r['status'] for r in arms])
        self.assertEqual([[]]*3, [r['phases'] for r in arms])
        self.assertEqual(1, report['summary']['invalidEpisodes'])

    def test_unavailable_forecast_keeps_fallback_and_complete_paired_roster(self):
        statuses = {self.signals[-1]['episodeGroup']+'/1': 'unavailable'}
        evaluation = freeze_offline_evaluation(self.signals, self.operations, simulated_statuses=statuses)
        frozen = freeze_decision_policy(self.signals, self.operations, evaluation=evaluation)
        decisions = simulate_decisions(self.signals, self.operations, evaluation=evaluation, frozen=frozen)
        report = self.run_pairs(evaluation=evaluation, frozen=frozen, decisions=decisions,
                                 grants=synthetic_grant_fixtures(decisions))
        actions = {r['arm']: r['action'] for r in report['episodes'][-1]['arms']}
        self.assertEqual(actions['non-model-reference'], actions['forecast-choice'])
        self.assertEqual('unavailable', decisions['decisions'][-1]['request']['forecast']['status'])
        self.assertEqual('unavailable', report['episodes'][-1]['forecastStatus'])
        self.assertGreater(len(report['episodes'][-1]['adviceReasonCodes']), 0)
        self.assertEqual(9, report['summary']['completedArms'])

    def test_failure_does_not_mutate_clean_replay_and_expiry_boundary_is_explicit(self):
        original = self.run_pairs()
        key = next(iter(self.kwargs['grants']))
        failed = self.run_pairs(faults={key: 'timeout'})
        self.assertNotEqual(original['receiptDigest'], failed['receiptDigest'])
        self.assertEqual(original, self.run_pairs())
        group = self.decisions['decisions'][0]['episodeGroup']
        request = self.decisions['decisions'][0]['request']
        last_valid = request['expiresNs']-request['nowNs']-1
        self.assertEqual('synthetic-descriptive', self.run_pairs(use_offsets={group: last_valid})['episodes'][0]['status'])
        self.assertEqual('inconclusive', self.run_pairs(use_offsets={group: last_valid+1})['episodes'][0]['status'])

    def test_unknown_effects_keep_refused_roster_without_execution(self):
        frozen = freeze_decision_policy(self.signals, self.operations, evaluation=self.evaluation,
                                        shapes={self.signals[-1]['episodeGroup']: 'unknown-effects'})
        decisions = simulate_decisions(self.signals, self.operations, evaluation=self.evaluation, frozen=frozen)
        report = self.run_pairs(frozen=frozen, decisions=decisions, grants=synthetic_grant_fixtures(decisions))
        arms = report['episodes'][-1]['arms']
        self.assertEqual(['refused']*3, [r['status'] for r in arms])
        self.assertEqual([[]]*3, [r['phases'] for r in arms])

    def test_resigned_decision_inputs_or_labels_cannot_replace_frozen_report(self):
        for field in ('plan', 'labels', 'authority'):
            decisions = deepcopy(self.decisions)
            if field == 'plan': decisions['decisions'][0]['arms'][0]['planDigest'] = 'a'*64
            elif field == 'labels': decisions['simulatedLabels'][0]['simulatedFullWallNs'] = 0
            else: decisions['executionAuthorization'] = 0
            decisions['receiptDigest'] = digest({k: v for k, v in decisions.items() if k != 'receiptDigest'})
            with self.subTest(field=field), self.assertRaisesRegex(ForecastError, 'paired-decision-drift'):
                self.run_pairs(decisions=decisions)

    def test_complete_recomputation_rejects_resigned_cost_outcome_and_roster_changes(self):
        report = self.run_pairs()
        self.assertEqual(report, validate_paired_rehearsal(report, self.signals, self.operations, **self.kwargs))
        for field in ('cost', 'roster', 'outcome'):
            changed = deepcopy(report)
            if field == 'cost': changed['costs']['totalTicks'] += 1
            elif field == 'roster': changed['episodes'][0]['arms'].pop()
            else: changed['episodes'][0]['arms'][0]['simulatedResultDigest'] = 'a'*64
            changed['receiptDigest'] = digest({k: v for k, v in changed.items() if k != 'receiptDigest'})
            with self.subTest(field=field), self.assertRaisesRegex(ForecastError, 'paired-rehearsal-drift'):
                validate_paired_rehearsal(changed, self.signals, self.operations, **self.kwargs)

    def test_no_runtime_or_worker_and_no_changes_to_caller_inputs(self):
        before = deepcopy(self.kwargs)
        with patch('agent_braid.runtime_policy.execute_policy_run', side_effect=AssertionError('runtime called')), \
                patch('agent_braid.forecast_advice.ForecastSession.predict', side_effect=AssertionError('worker called')):
            self.run_pairs()
        self.assertEqual(before, self.kwargs)

    def test_reject_unrecognized_or_boolean_controls(self):
        for change in ({'order_seed': True}, {'faults': {'unknown': 'timeout'}},
                       {'faults': {next(iter(self.kwargs['grants'])): 'kill-daemon'}},
                       {'use_offsets': {'unknown': 0}}, {'grants': {'unknown': {}}}):
            with self.subTest(change=change), self.assertRaises(ForecastError): self.run_pairs(**change)
