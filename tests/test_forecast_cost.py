# SPDX-License-Identifier: AGPL-3.0-only
"""Cost counters never conceal failure, missing startup or overlapping work."""
from copy import deepcopy
import unittest

from agent_braid.forecast_cost import (
    CPU_DOMAINS, CPU_SCOPES, STAGES, CostRecorder, summarize_cost_ledger,
    validate_cost_ledger,
)
from agent_braid.forecast_data import ForecastError, digest


def bound(record):
    record['receiptDigest'] = digest({k: v for k, v in record.items() if k != 'receiptDigest'})
    return record


def complete_simulation():
    recorder = CostRecorder('simulation', 'a' * 64, 'b' * 64,
                            source_kind='synthetic-simulation', clock=lambda: 0,
                            cpu_clock=lambda: 0)
    record = recorder.seal(cleanup_confirmed=True)
    record.update(wallNs=100, publicationIncluded=True, publicationReason=None)
    record['phases'] = [dict(id=s, stage=s, startedNs=i, finishedNs=i + 10,
                             status='completed', accounting='observed', reason=None,
                             sourceDigest=None) for i, s in enumerate(STAGES)]
    record['cpu'] = [dict(domain=d, scope=CPU_SCOPES[d], meterId=d, startedNs=0,
                          finishedNs=100, beforeNs=100, afterNs=120, reason=None,
                          sourceDigest=None) for d in CPU_DOMAINS]
    record['memory'] = [dict(meterId='worker', scope='cgroup-sample', observedAtNs=50,
                             bytes=600, reason=None, sourceDigest=None,
                             samplePeriodNs=10, limitBytes=1000, limitReason=None)]
    return bound(record)


class ForecastCostTests(unittest.TestCase):
    def test_overlapping_phases_use_union_not_sum(self):
        summary = summarize_cost_ledger(complete_simulation())
        self.assertEqual(summary['phaseUnionNs'], len(STAGES) + 9)
        self.assertEqual(summary['phaseSumNs'], 10 * len(STAGES))
        self.assertEqual(summary['coordinatorResidualNs'], 100 - len(STAGES) - 9)
        self.assertEqual(summary['reportedDisjointCpuNs'], 80)
        self.assertTrue(summary['reportedCoverageComplete'])
        self.assertFalse(summary['sourceBindingsVerified'])
        self.assertFalse(summary['fullDeploymentCostAccepted'])
        self.assertFalse(summary['economicCostAccepted'])

    def test_missing_and_reused_setup_never_become_zero(self):
        record = complete_simulation()
        phase = record['phases'][1]
        phase.update(accounting='reused', status='not-run', startedNs=None,
                     finishedNs=None, reason='previous-build-unallocated', sourceDigest='c' * 64)
        record['cpu'][2].update(meterId=None, startedNs=None, finishedNs=None,
                                beforeNs=None, afterNs=None, reason='worker-died-before-readback')
        summary = summarize_cost_ledger(bound(record))
        self.assertIsNone(summary['reportedDisjointCpuNs'])
        self.assertIsNone(summary['cpuNsByDomain']['worker-container'])
        self.assertFalse(summary['reportedCoverageComplete'])
        self.assertIn('artifact-provisioning:previous-build-unallocated', summary['gaps'])
        phase['sourceDigest'] = None
        with self.assertRaisesRegex(ForecastError, 'reused-cost-source-required'):
            validate_cost_ledger(bound(record))

    def test_failed_cancelled_and_refused_phases_are_retained(self):
        record = complete_simulation()
        for i, status in enumerate(('failed', 'cancelled', 'refused', 'timed-out')):
            record['phases'][i]['status'] = status
        actual = validate_cost_ledger(bound(record))
        self.assertEqual([p['status'] for p in actual['phases'][:4]],
                         ['failed', 'cancelled', 'refused', 'timed-out'])
        self.assertEqual(len(actual['phases']), len(STAGES))

    def test_counter_reset_duplicate_domain_and_meter_overlap_refuse(self):
        for mutate in (
            lambda r: r['cpu'][0].update(afterNs=99),
            lambda r: r['cpu'][1].update(domain='coordinator'),
            lambda r: r['cpu'][1].update(meterId='coordinator'),
            lambda r: r['cpu'][3].update(scope='worker-cgroup-inclusive'),
            lambda r: r['cpu'][0].update(beforeNs=True),
        ):
            record = complete_simulation(); mutate(record)
            with self.subTest(mutate=mutate), self.assertRaises(ForecastError):
                validate_cost_ledger(bound(record))

    def test_partial_cpu_boundary_and_missing_roster_are_visible(self):
        record = complete_simulation(); record['cpu'][0]['startedNs'] = 1
        self.assertIn('cpu-coordinator:partial-boundary', summarize_cost_ledger(bound(record))['gaps'])
        record['phases'].pop()
        self.assertIn('cleanup:missing', summarize_cost_ledger(bound(record))['gaps'])
        record['cpu'].pop()
        with self.assertRaisesRegex(ForecastError, 'incomplete-cpu-roster'):
            validate_cost_ledger(bound(record))

    def test_memory_scopes_are_separate_and_sample_is_not_peak(self):
        record = complete_simulation()
        row = deepcopy(record['memory'][0]); row.update(scope='process-lifetime-peak',
                                                        samplePeriodNs=None, bytes=700)
        record['memory'].append(row)
        summary = summarize_cost_ledger(bound(record))
        self.assertEqual([m['bytes'] for m in summary['memoryObservations']], [600, 700])
        record['memory'][0]['samplePeriodNs'] = None
        with self.assertRaises(ForecastError): validate_cost_ledger(bound(record))

    def test_integrity_bounds_and_oversized_roster_are_rejected(self):
        record = complete_simulation(); record['wallNs'] += 1
        with self.assertRaisesRegex(ForecastError, 'cost-integrity-drift'):
            validate_cost_ledger(record)
        record = complete_simulation(); record['phases'][0]['finishedNs'] = 101
        with self.assertRaisesRegex(ForecastError, 'invalid-cost-interval'):
            validate_cost_ledger(bound(record))
        record = complete_simulation(); record['phases'] *= 1025
        with self.assertRaises(ForecastError): validate_cost_ledger(bound(record))

    def test_recorder_retains_exception_and_does_not_mask_it(self):
        ticks = iter((100, 101, 103, 110))
        recorder = CostRecorder('failed', 'a' * 64, 'b' * 64,
                                clock=lambda: next(ticks), cpu_clock=lambda: 20)
        with self.assertRaisesRegex(RuntimeError, 'owned-test-failure'):
            with recorder.phase('first', 'forecast'):
                raise RuntimeError('owned-test-failure')
        result = recorder.seal()
        self.assertEqual(result['phases'][0]['status'], 'failed')
        summary = summarize_cost_ledger(result)
        self.assertEqual(summary['phaseUnionNs'], 2)
        self.assertEqual(summary['coordinatorResidualNs'], 8)
        self.assertIn('cleanup:unconfirmed', summary['gaps'])
        self.assertIn('publication:final-receipt-write-after-seal', summary['gaps'])
        with self.assertRaises(ForecastError): recorder.seal()

    def test_active_phase_cannot_seal_or_reuse_an_identifier(self):
        recorder = CostRecorder('active', 'a' * 64, 'b' * 64)
        with recorder.phase('x', 'forecast'):
            with self.assertRaises(ForecastError): recorder.seal()
            with self.assertRaises(ForecastError):
                with recorder.phase('x', 'forecast'): pass
        with self.assertRaises(ForecastError): recorder.unavailable('x', 'forecast', 'absent')
        recorder.seal(cleanup_confirmed=True)
        with self.assertRaises(ForecastError): recorder.unavailable('y', 'cache', 'absent')

    def test_empty_inventory_and_unconfirmed_cleanup_cannot_claim_coverage(self):
        recorder = CostRecorder('empty', 'a' * 64, 'b' * 64)
        summary = summarize_cost_ledger(recorder.seal())
        self.assertFalse(summary['reportedCoverageComplete'])
        self.assertIn('forecast:missing', summary['gaps'])
        self.assertIn('cleanup:unconfirmed', summary['gaps'])

    def test_phase_capacity_and_aggregate_overflow_are_bounded(self):
        recorder = CostRecorder('bounded', 'a' * 64, 'b' * 64)
        for i in range(1024):
            recorder.unavailable('p' + str(i), 'cache', 'not-used', accounting='not-applicable')
        with self.assertRaisesRegex(ForecastError, 'phase-budget-exceeded'):
            recorder.unavailable('one-too-many', 'cache', 'not-used')
        record = complete_simulation()
        for row in record['cpu']: row.update(beforeNs=0, afterNs=2**63 - 1)
        with self.assertRaisesRegex(ForecastError, 'aggregate-cost-overflow'):
            summarize_cost_ledger(bound(record))
