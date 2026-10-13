# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import unittest
from agent_braid.forecast_data import ForecastError, parse_record, validate_window, reconcile_phases
from tests.forecast_helpers import window

class ForecastDataTests(unittest.TestCase):
    def test_window_owns_copy_and_preserves_zero(self):
        source = window(); source['values'][0][0] = 0
        actual = validate_window(source); source['values'][0][0] = 99
        self.assertEqual(0, actual['values'][0][0])

    def test_malformed_and_late_data_are_refused(self):
        mutations = [lambda w: w['values'][0].__setitem__(0, True),
                     lambda w: w['values'][0].__setitem__(0, float('nan')),
                     lambda w: w['availableAtNs'][0].__setitem__(0, 400000000),
                     lambda w: w.update(stepNs=0), lambda w: w.update(sourceKind='real'),
                     lambda w: w.update(extra=1), lambda w: w['units'].__setitem__(0, '')]
        for mutate in mutations:
            candidate = window(); mutate(candidate)
            with self.subTest(mutate=mutate), self.assertRaises(ForecastError): validate_window(candidate)

    def test_missing_values_need_reasons_and_masks(self):
        candidate = window(); candidate['values'][0][0] = None
        with self.assertRaises(ForecastError): validate_window(candidate)
        candidate['observedMask'][0][0] = False; candidate['availableAtNs'][0][0] = None
        candidate['missingReasons'][0][0] = 'not-observed'
        self.assertIsNone(validate_window(candidate)['values'][0][0])

    def test_ingress_rejects_duplicates_nonfinite_and_oversize(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'[' + b' ' * 1048576 + b']'):
            with self.assertRaises(ForecastError): parse_record(raw)

    def test_overlap_is_not_double_counted_and_residual_is_explicit(self):
        phases = [{'name':'a','startedNs':0,'finishedNs':6}, {'name':'b','startedNs':4,'finishedNs':8}]
        actual = reconcile_phases(phases, 10)
        self.assertEqual(8, actual['phaseUnionNs']); self.assertEqual(2, actual['coordinatorResidualNs'])
        with self.assertRaises(ForecastError): reconcile_phases(phases, 7)
