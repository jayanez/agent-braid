# SPDX-License-Identifier: AGPL-3.0-only
"""Frozen economic mapping uses synthetic arithmetic, never runtime execution."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_lab import signal_episode, operation_episode
from agent_braid.forecast_evaluation import freeze_offline_evaluation
from agent_braid.forecast_decisions import freeze_decision_policy, simulate_decisions
from agent_braid.forecast_policy import validate_advice, verify_consumption


class FrozenDecisionTests(unittest.TestCase):
    def setUp(self):
        self.signals = [signal_episode(family, seed=10*p+i, partition=partition)
                        for p, partition in enumerate(('development', 'calibration', 'holdout'))
                        for i, family in enumerate(('trend', 'constant', 'bursts', 'late'))]
        self.operations = [operation_episode(seed=10*p+i, partition=partition)
                           for p, partition in enumerate(('development', 'calibration', 'holdout'))
                           for i in range(4)]
        self.evaluation = freeze_offline_evaluation(self.signals, self.operations)

    def freeze(self, **kwargs):
        return freeze_decision_policy(self.signals, self.operations, evaluation=self.evaluation, **kwargs)

    def run_plan(self, frozen, **kwargs):
        return simulate_decisions(self.signals, self.operations, evaluation=self.evaluation, frozen=frozen, **kwargs)

    def test_reproducible_complete_bindings_and_shadow(self):
        frozen = self.freeze()
        report = self.run_plan(frozen)
        self.assertEqual(report, self.run_plan(frozen))
        self.assertEqual(12, len(report['decisions']))
        self.assertEqual(self.evaluation['planDigest'], frozen['evaluationPlanDigest'])
        self.assertEqual(frozen['policyDigest'], report['policyDigest'])
        for row in report['decisions']:
            self.assertEqual('mapped', row['status'])
            self.assertEqual({'serial', 'parallel'}, {c['mode'] for c in row['candidates']})
            self.assertEqual({'serial-reference', 'non-model-reference', 'forecast-choice'}, {a['arm'] for a in row['arms']})
            self.assertEqual(row['advice']['referenceAction'], row['advice']['selectedAction'])
            self.assertEqual(row['advice'], validate_advice(row['advice'], row['request'], now_ns=row['cutoffNs']))
            self.assertTrue(all(c['identityKind'] == 'synthetic-plan' for c in row['candidates']))
            self.assertFalse(row['advice']['executionAuthorization'])
            self.assertNotIn('actual', row['request'])
            self.assertNotIn('outcome', row['request'])
        self.assertFalse(report['utilityAccepted'])
        self.assertFalse(report['realWorkloadEvidence'])
        self.assertFalse(report['executionAuthorization'])
        self.assertEqual('synthetic-cost-law-not-observed', report['costBoundary'])

    def test_reference_is_selected_by_development_full_simulated_cost(self):
        frozen = self.freeze()
        scores = frozen['selection']['referenceScores']
        self.assertEqual({'serial', 'persistence', 'ewma'}, {r['method'] for r in scores})
        best = min(scores, key=lambda r: (r['simulatedFullWallNs'], r['method']))
        self.assertEqual(best['method'], frozen['selection']['referenceMethod'])
        self.assertGreater(min(r['simulatedFullWallNs'] for r in scores), 0)
        self.assertEqual('development', frozen['selection']['partition'])

    def test_later_folds_cannot_tune_reference_or_mapper(self):
        plan = self.freeze()
        signals, operations = deepcopy(self.signals), deepcopy(self.operations)
        for i in (4, 8):
            signals[i] = signal_episode('regime', seed=90+i, partition=signals[i]['partition'])
            operations[i] = operation_episode(seed=90+i, partition=operations[i]['partition'])
        evaluation = freeze_offline_evaluation(signals, operations)
        changed = freeze_decision_policy(signals, operations, evaluation=evaluation)
        self.assertEqual(plan['selection'], changed['selection'])
        self.assertNotEqual(plan['policyDigest'], changed['policyDigest'])
        with self.assertRaises(ForecastError):
            simulate_decisions(signals, operations, evaluation=evaluation, frozen=plan)

    def test_order_does_not_change_freeze_or_results(self):
        plan = self.freeze()
        self.assertEqual(plan, freeze_decision_policy(self.signals[::-1], self.operations[::-1], evaluation=self.evaluation))
        self.assertEqual(self.run_plan(plan), simulate_decisions(self.signals[::-1], self.operations[::-1], evaluation=self.evaluation, frozen=plan))

    def test_resigned_reference_threshold_and_cost_drift_refuse(self):
        for mutate in (
            lambda p: p['selection'].__setitem__('referenceMethod', 'invented'),
            lambda p: p['selection']['policy'].__setitem__('minimumRatio', 9),
            lambda p: p.__setitem__('costLawDigest', 'a'*64),
            lambda p: p['selection']['referenceScores'][0].__setitem__('simulatedFullWallNs', 1),
        ):
            plan = self.freeze(); mutate(plan)
            plan['policyDigest'] = digest({k: v for k, v in plan.items() if k != 'policyDigest'})
            with self.subTest(mutation=mutate), self.assertRaisesRegex(ForecastError, 'frozen-decision-policy-drift'):
                self.run_plan(plan)

    def test_evaluation_drift_and_unpaired_partitions_refuse(self):
        evaluation = deepcopy(self.evaluation); evaluation['selection']['alpha'] = .123
        evaluation['planDigest'] = digest({k: v for k, v in evaluation.items() if k != 'planDigest'})
        with self.assertRaisesRegex(ForecastError, 'frozen-evaluation-drift'):
            freeze_decision_policy(self.signals, self.operations, evaluation=evaluation)
        with self.assertRaises(ForecastError):
            freeze_decision_policy(self.signals, self.operations[:-1], evaluation=self.evaluation)

    def test_dependencies_conflicts_and_unknown_effects_cannot_win(self):
        target = self.signals[-1]['episodeGroup']
        for shape in ('dependency-chain', 'conflict', 'unknown-effects'):
            plan = self.freeze(shapes={target: shape})
            report = self.run_plan(plan, mode='consultative')
            row = next(r for r in report['decisions'] if r['episodeGroup'] == target)
            with self.subTest(shape=shape):
                parallel = next(c for c in row['candidates'] if c['mode'] == 'parallel')
                self.assertFalse(parallel['eligible'])
                self.assertTrue(parallel['reasonCodes'])
                if shape == 'unknown-effects':
                    self.assertEqual('refused', row['status'])
                    self.assertIsNone(row['advice'])
                    self.assertEqual(3, len(row['arms']))
                    self.assertTrue(all(a['status'] == 'not-mapped-refused' for a in row['arms']))
                else:
                    self.assertEqual('serial', row['advice']['selectedAction'])
                    self.assertEqual(['serial'], [c['id'] for c in row['advice']['candidates']])

    def test_failed_simulated_forecasts_fall_back_without_dropping_attempts(self):
        statuses = {f"{e['episodeGroup']}/1": status for e, status in zip(self.signals[8:], ('refused', 'unavailable', 'timed-out', 'cancelled'))}
        self.evaluation = freeze_offline_evaluation(self.signals, self.operations, simulated_statuses=statuses)
        report = self.run_plan(self.freeze(), mode='consultative')
        rows = [r for r in report['decisions'] if r['partition'] == 'holdout']
        self.assertEqual(4, len(rows))
        self.assertEqual(set(statuses.values()), {r['request']['forecast']['status'] for r in rows})
        for row in rows:
            self.assertEqual('abstained', row['advice']['status'])
            self.assertEqual(['forecast-unavailable'], row['advice']['reasonCodes'])
            self.assertEqual(row['advice']['referenceAction'], row['advice']['selectedAction'])

    def test_stale_changed_plan_resource_forecast_and_wrong_grant_refuse(self):
        row = self.run_plan(self.freeze())['decisions'][0]
        with self.assertRaisesRegex(ForecastError, 'stale-advice'):
            validate_advice(row['advice'], row['request'], now_ns=row['advice']['expiresNs'])
        for mutate in (
            lambda r: r['catalogue']['candidates'][0].__setitem__('planDigest', 'a'*64),
            lambda r: r['resource'].__setitem__('hostId', 'remote'),
            lambda r: r['forecast'].__setitem__('modelDigest', 'b'*64),
            lambda r: r['policy'].__setitem__('minimumRatio', 9),
        ):
            request = deepcopy(row['request']); mutate(request)
            with self.subTest(), self.assertRaises(ForecastError):
                validate_advice(row['advice'], request, now_ns=row['cutoffNs'])
        for plan_digest in (row['advice']['selectedPlanDigest'], 'f'*64):
            with self.assertRaisesRegex(ForecastError, 'synthetic-advice-cannot-dispatch'):
                verify_consumption(row['advice'], row['request'], plan_digest=plan_digest, now_ns=row['cutoffNs'])

    def test_default_off_and_unsupported_mode(self):
        report = self.run_plan(self.freeze(), mode='off')
        self.assertTrue(all(r['advice']['status'] == 'disabled' for r in report['decisions']))
        with self.assertRaises(ForecastError): self.run_plan(self.freeze(), mode='promoted-exact-capability')

    def test_predictors_and_candidates_receive_no_future_labels(self):
        from agent_braid import forecast_decisions as decisions
        original = decisions._candidate_set
        with patch.object(decisions, '_candidate_set', wraps=original) as candidates:
            self.run_plan(self.freeze())
        self.assertGreater(candidates.call_count, 0)
        for call in candidates.call_args_list:
            self.assertNotIn('actual', call.args[0])
            self.assertNotIn('outcome', call.args[0])
            self.assertNotIn('outcomeAtNs', call.args[0])

    def test_point_of_use_recomputes_complete_binding_even_after_resigning(self):
        from agent_braid.forecast_decisions import validate_synthetic_decision
        plan = self.freeze(); row = self.run_plan(plan)['decisions'][0]
        def check(value, now=None):
            return validate_synthetic_decision(value, self.signals, self.operations, evaluation=self.evaluation,
                                               frozen=plan, mode='shadow', now_ns=row['cutoffNs'] if now is None else now)
        self.assertEqual(row, check(row))
        for mutate in (
            lambda r: r['candidates'][0]['plan']['descriptors']['manifest']['steps'][0].__setitem__('patchDigest', 'a'*64),
            lambda r: r['candidates'][1].__setitem__('eligible', False),
            lambda r: r['request']['policy'].__setitem__('minimumRatio', 9),
            lambda r: r.__setitem__('policyDigest', 'b'*64),
            lambda r: r['advice'].__setitem__('selectedPlanDigest', 'c'*64),
        ):
            changed = deepcopy(row); mutate(changed)
            changed['receiptDigest'] = digest({k:v for k,v in changed.items() if k != 'receiptDigest'})
            with self.subTest(), self.assertRaisesRegex(ForecastError, 'synthetic-decision-binding-drift'): check(changed)
        with self.assertRaisesRegex(ForecastError, 'decision-not-yet-available'): check(row, row['cutoffNs']-1)
        with self.assertRaisesRegex(ForecastError, 'stale-advice'): check(row, row['advice']['expiresNs'])

    def test_unknown_resources_and_cutoff_labels_cannot_be_resigned(self):
        plan = self.freeze()
        for mutate in (
            lambda s, o: s[-1]['resource'].__setitem__('hostId', 'remote'),
            lambda s, o: s[-1]['actual'].__setitem__(0, 999),
            lambda s, o: o[-1].__setitem__('outcome', 999),
            lambda s, o: o[-1].__setitem__('availableAtNs', 2**62),
        ):
            signals, operations = deepcopy(self.signals), deepcopy(self.operations); mutate(signals, operations)
            with self.subTest(), self.assertRaises(ForecastError):
                simulate_decisions(signals, operations, evaluation=self.evaluation, frozen=plan)

    def test_reference_policy_is_independently_frozen(self):
        frozen = self.freeze()
        best = min(frozen['selection']['referenceScores'], key=lambda r: (r['simulatedFullWallNs'], r['method']))
        self.assertEqual(best['policy'], frozen['selection']['referencePolicy'])
        report = self.run_plan(frozen, mode='consultative')
        for row in report['decisions']:
            self.assertEqual('not-executed-simulation', row['arms'][2]['status'])
            self.assertEqual(row['arms'][1]['action'], row['advice']['referenceAction'])
        changed = deepcopy(frozen); changed['selection']['referencePolicy']['minimumRatio'] = 9
        changed['policyDigest'] = digest({k:v for k,v in changed.items() if k != 'policyDigest'})
        with self.assertRaises(ForecastError): self.run_plan(changed)

    def test_existing_experiment_entry_point_uses_no_runtime_or_model(self):
        from agent_braid.forecast_experiment import simulate_frozen_policy_arms
        from agent_braid import forecast_decisions as decisions
        plan = self.freeze()
        with patch('agent_braid.runtime_policy.prepare_policy_run', side_effect=AssertionError('runtime forbidden')), \
             patch('agent_braid.forecast_advice.ForecastSession.predict', side_effect=AssertionError('worker forbidden')), \
             patch.object(decisions, '_candidate_set', wraps=decisions._candidate_set) as candidates:
            report = simulate_frozen_policy_arms(self.signals, self.operations, evaluation=self.evaluation, frozen=plan)
        self.assertEqual(12, len(report['decisions']))
        self.assertGreater(candidates.call_count, 0)

    def test_unknown_effects_in_development_refuse_selection(self):
        with self.assertRaisesRegex(ForecastError, 'reference-not-admitted'):
            self.freeze(shapes={self.signals[0]['episodeGroup']: 'unknown-effects'})

    def test_shadow_disagreement_exists_and_is_never_applied(self):
        # Frozen development selects serial; a later constant signal admits a
        # useful parallel proposal, exercising genuine disagreement without tuning.
        self.signals = [signal_episode(family, seed=i, partition=partition)
                        for i, (family, partition) in enumerate(zip(
                            ('trend', 'constant', 'constant'), ('development', 'calibration', 'holdout')))]
        self.operations = [operation_episode(seed=i, partition=partition)
                           for i, partition in zip((3, 4, 7), ('development', 'calibration', 'holdout'))]
        self.evaluation = freeze_offline_evaluation(self.signals, self.operations)
        report = self.run_plan(self.freeze())
        disagreement = [r for r in report['decisions'] if r['advice']['proposedAction'] != r['advice']['referenceAction']]
        self.assertGreater(len(disagreement), 0)
        for row in disagreement:
            self.assertEqual(row['advice']['selectedAction'], row['advice']['referenceAction'])
            self.assertEqual(row['arms'][1]['action'], row['arms'][2]['action'])

    def test_known_dependency_descriptor_cannot_be_overridden_as_independent(self):
        report = self.run_plan(self.freeze())
        checked = 0
        for row in report['decisions']:
            candidate = row['candidates'][1]
            descriptors = candidate['plan']['descriptors']
            if descriptors['features'][2] == 1:
                checked += 1
                self.assertFalse(candidate['eligible'])
                self.assertTrue(all(len(wave) == 1 for wave in candidate['plan']['waves']))
                self.assertEqual(['op0'], descriptors['manifest']['request']['operations'][1]['dependencies'])
        self.assertGreater(checked, 0)

    def test_retained_evidence_reproduces_frozen_policy_and_attempts(self):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[1]/'specs/036-forecast-parallelism-experiment/evidence/t004-synthetic-decisions.json'
        evidence = json.loads(path.read_text())
        statuses = {f"{e['episodeGroup']}/1": status for e, status in zip(self.signals[8:], ('refused', 'unavailable', 'timed-out', 'cancelled'))}
        self.evaluation = freeze_offline_evaluation(self.signals, self.operations, simulated_statuses=statuses)
        shapes = {self.signals[-1]['episodeGroup']: 'unknown-effects'}
        policy = self.freeze(shapes=shapes)
        report = self.run_plan(policy)
        self.assertEqual(evidence['evaluationPlanDigest'], self.evaluation['planDigest'])
        self.assertEqual(evidence['policy'], policy)
        self.assertEqual(evidence['reportDigest'], digest(report))
        self.assertEqual(evidence['attempts'], [
            {key: row[key] for key in ('episodeGroup', 'partition', 'status', 'reasonCodes', 'receiptDigest')}
            for row in report['decisions']])


if __name__ == '__main__':
    unittest.main()
