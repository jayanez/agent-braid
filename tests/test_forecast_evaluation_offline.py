# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls: synthetic numerical simulation, never a model or VM."""
import unittest
from copy import deepcopy
from unittest.mock import patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_lab import signal_episode, operation_episode
from agent_braid.forecast_evaluation import freeze_offline_evaluation, evaluate_offline


class FrozenOfflineEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.signals = [signal_episode(family, seed=10*p+i, partition=partition)
                        for p, partition in enumerate(('development', 'calibration', 'holdout'))
                        for i, family in enumerate(('trend', 'constant', 'missing', 'late'))]
        self.operations = [operation_episode(seed=10*p+i, partition=partition)
                           for p, partition in enumerate(('development', 'calibration', 'holdout'))
                           for i in range(4)]

    def freeze(self, **kwargs):
        return freeze_offline_evaluation(self.signals, self.operations, **kwargs)

    def score(self, frozen):
        return evaluate_offline(self.signals, self.operations, frozen=frozen)

    def test_complete_roster_and_reproducible_receipts(self):
        frozen = self.freeze()
        report = self.score(frozen)
        self.assertEqual(report, self.score(frozen))
        self.assertEqual(30, len(report['metrics']))
        self.assertEqual(120, len(report['receipts']))  # 12*3*3 temporal + 12 operation
        self.assertEqual(24, report['episodeIdentityCount'])
        self.assertEqual(frozen['planDigest'], report['planDigest'])
        self.assertEqual({'synthetic-simulation'}, {r['provenance'] for r in report['receipts']})
        self.assertFalse(report['utilityAccepted'])
        self.assertFalse(report['realWorkloadEvidence'])
        self.assertFalse(report['executionAuthorization'])
        for row in report['metrics']:
            self.assertEqual('owned-lab', row['resourceGroup'])
            self.assertEqual(1.0, row['scores']['actionableCoverage'])
            self.assertGreater(row['scores']['intended'], 0)
        simulated = [r for r in report['receipts'] if r['method'] == 'chronos-simulated'
                     and r['episodeGroup'] == self.signals[0]['episodeGroup']]
        self.assertEqual([1, 5, 10], [r['horizon'] for r in simulated])
        for receipt in simulated:
            self.assertAlmostEqual(0, receipt['scores']['mae'], places=10)
            self.assertEqual('not-evaluated', receipt['intervalCalibration'])

    def test_development_selection_ignores_later_data_and_order(self):
        frozen = self.freeze()
        signals = deepcopy(self.signals)
        operations = deepcopy(self.operations)
        signals[-1] = signal_episode('bursts', seed=99, partition='holdout')
        operations[-1] = operation_episode(seed=99, partition='holdout')
        changed = freeze_offline_evaluation(signals, operations)
        self.assertEqual(frozen['selection'], changed['selection'])
        self.assertNotEqual(frozen['planDigest'], changed['planDigest'])
        with self.assertRaisesRegex(ForecastError, 'frozen-evaluation-drift'):
            evaluate_offline(signals, operations, frozen=frozen)
        self.assertEqual(frozen, freeze_offline_evaluation(self.signals[::-1], self.operations[::-1]))
        self.assertEqual(self.score(frozen), evaluate_offline(self.signals[::-1], self.operations[::-1], frozen=frozen))

    def test_model_or_partition_tampering_cannot_be_resigned(self):
        for field in ('alpha', 'regressionWidth', 'signalScale'):
            with self.subTest(field=field):
                frozen = self.freeze()
                frozen['selection'][field] += 1
                frozen['planDigest'] = digest({k: v for k, v in frozen.items() if k != 'planDigest'})
                with self.assertRaisesRegex(ForecastError, 'frozen-evaluation-drift'):
                    self.score(frozen)

    def test_cutoff_labels_features_resource_and_availability_bindings(self):
        frozen = self.freeze()
        mutations = (
            lambda s, o: s[-1]['actual'].__setitem__(0, 100),
            lambda s, o: s[-1]['window'].__setitem__('cutoffNs', 0),
            lambda s, o: s[-1]['window']['availableAtNs'][0].__setitem__(127, 2**62),
            lambda s, o: s[-1]['window']['units'].__setitem__(0, 'ms'),
            lambda s, o: s[-1]['resource'].__setitem__('profileId', 'other'),
            lambda s, o: o[-1]['features'].__setitem__(0, 999),
            lambda s, o: o[-1].__setitem__('availableAtNs', o[-1]['cutoffNs']+1),
            lambda s, o: o[-1].__setitem__('outcome', -1),
            lambda s, o: o[-1].__setitem__('partition', 'development'),
        )
        for mutate in mutations:
            signals, operations = deepcopy(self.signals), deepcopy(self.operations)
            mutate(signals, operations)
            with self.subTest(mutation=mutate):
                with self.assertRaises(ForecastError):
                    freeze_offline_evaluation(signals, operations)
                with self.assertRaises(ForecastError):
                    evaluate_offline(signals, operations, frozen=frozen)

    def test_duplicate_cross_partition_and_missing_folds_refuse(self):
        for signals, operations in (
            (self.signals+self.signals[:1], self.operations),
            (self.signals, self.operations+self.operations[:1]),
            (self.signals[4:], self.operations),
            (self.signals, self.operations[:-4]),
            (self.signals+[signal_episode('trend', seed=0, partition='holdout')], self.operations),
        ):
            with self.subTest(), self.assertRaises(ForecastError):
                freeze_offline_evaluation(signals, operations)

    def test_all_simulated_terminal_outcomes_stay_in_denominators(self):
        statuses = {f"{e['episodeGroup']}/{h}": status
                    for e, status in zip(self.signals[8:], ('refused', 'unavailable', 'timed-out', 'cancelled'))
                    for h in (1, 5, 10)}
        report = self.score(self.freeze(simulated_statuses=statuses))
        rows = [r for r in report['metrics'] if r['method'] == 'chronos-simulated' and r['partition'] == 'holdout']
        self.assertEqual(3, len(rows))
        for row in rows:
            self.assertEqual(0, row['scores']['forecasted'])
            self.assertEqual(4*row['horizon'], row['scores']['unavailable'])
            self.assertEqual(0, row['scores']['actionableCoverage'])
            self.assertIsNone(row['scores']['mae'])
        attempts = [r for r in report['receipts'] if r['method'] == 'chronos-simulated' and r['partition'] == 'holdout']
        self.assertEqual(set(statuses.values()), {r['status'] for r in attempts})
        self.assertTrue(all(r['reasonCodes'] for r in attempts))
        with self.assertRaises(ForecastError): self.freeze(simulated_statuses={'unknown/1': 'refused'})
        with self.assertRaises(ForecastError): self.freeze(simulated_statuses={next(iter(statuses)): 'success'})

    def test_regression_is_an_operation_target_and_beats_development_mean(self):
        report = self.score(self.freeze())
        operations = [r for r in report['receipts'] if r['method'] == 'operation-regression']
        self.assertEqual(12, len(operations))
        self.assertTrue(all(r['targetId'] == 'preparation-duration' and r['unit'] == 'ms'
                            and r['horizonKind'] == 'operation' for r in operations))
        mean = sum(e['outcome'] for e in self.operations[:4])/4
        reference = sum(abs(e['outcome']-mean) for e in self.operations[8:])/4
        measured = next(r['scores']['mae'] for r in report['metrics']
                        if r['method'] == 'operation-regression' and r['partition'] == 'holdout')
        self.assertLess(measured, reference)

    def test_zero_development_scale_is_explicit(self):
        signals = [signal_episode('constant', seed=i, partition=p)
                   for i, p in enumerate(('development', 'calibration', 'holdout'))]
        plan = freeze_offline_evaluation(signals, self.operations)
        report = evaluate_offline(signals, self.operations, frozen=plan)
        for row in report['metrics']:
            if row['targetId'] == 'load':
                self.assertIsNone(row['scores']['scaledError'])
                self.assertEqual('development-scale-undefined', row['scores']['scaledErrorReason'])

    def test_predictors_get_no_future_labels_and_fit_gets_development_only(self):
        from agent_braid import forecast_evaluation as evaluator
        from agent_braid.forecast_baselines import fit_regression
        from agent_braid.forecast_chronos_inputs import translate_inputs
        with patch.object(evaluator, 'fit_regression', wraps=fit_regression) as fit:
            frozen = self.freeze()
            self.assertTrue(all(r['partition'] == 'development' for r in fit.call_args.args[0]))
        for episode in self.signals:
            item = translate_inputs(episode['window'], 10)[0]
            self.assertNotIn('future_target', item)
            self.assertEqual({}, item['future_covariates'])
        with patch.object(evaluator, '_simulate_chronos', wraps=evaluator._simulate_chronos) as simulate:
            self.score(frozen)
            self.assertEqual(36, simulate.call_count)
            for call in simulate.call_args_list:
                self.assertNotIn('actual', call.args[0])
                self.assertNotIn('outcome', call.args[0])

    def test_purge_guard_rejects_overlap_even_for_a_matching_fixture_recipe(self):
        from agent_braid import forecast_lab
        original = forecast_lab.signal_episode

        def overlapping(*args, **kwargs):
            episode = original(*args, **kwargs)
            if episode['partition'] == 'calibration':
                # Rebind both the input and its recipe generator: this reaches
                # the fold guard rather than failing the earlier hash guard.
                window = episode['window']
                window['gridStartNs'] -= 1000000000000
                window['cutoffNs'] -= 1000000000000
            return episode

        with patch.object(forecast_lab, 'signal_episode', side_effect=overlapping):
            signals = [overlapping(e['recipe']['family'], seed=e['recipe']['seed'],
                                   partition=e['partition']) for e in self.signals]
            with self.assertRaisesRegex(ForecastError, 'unpurged-or-nonchronological-partition'):
                freeze_offline_evaluation(signals, self.operations)

    def test_calibration_cannot_tune_regression_width_or_scales(self):
        frozen = self.freeze()
        signals, operations = deepcopy(self.signals), deepcopy(self.operations)
        signals[4] = signal_episode('bursts', seed=98, partition='calibration')
        operations[4] = operation_episode(seed=98, partition='calibration')
        changed = freeze_offline_evaluation(signals, operations)
        self.assertEqual(frozen['selection'], changed['selection'])
        self.assertNotEqual(frozen['planDigest'], changed['planDigest'])
