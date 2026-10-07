# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic accounting checks; never run registered measurements."""
import math
from pathlib import Path
import tempfile
import threading
import unittest

from agent_braid.git_process import GitCommandBudget
from agent_braid.utility_budget_observer import observe_git_budget, observe_git_budgets
from agent_braid.utility_accounting import AccountingError, PHASES, UtilityAccounting
from agent_braid.git_runtime import _budget as runtime_budget


def observed_budget(*args, **kwargs):
    return observe_git_budget(GitCommandBudget(*args, **kwargs))


class Clock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.cpu = Clock()
        self.child = [0.0, 0.0]
        self.collector = UtilityAccounting(monotonic=self.clock, parent_cpu=self.cpu,
            child_cpu=lambda: tuple(self.child), lifetime_rss=lambda: 0,
            child_attribution_valid=True).start()

    def complete_phases(self):
        for phase in PHASES:
            self.clock.value += 0.25
            with self.collector.phase(phase):
                self.clock.value += 1.0
                self.cpu.value += 0.5
                self.child[0] += 0.125
                self.child[1] += 0.0625

    def test_disjoint_wall_reconciliation_and_healthy_zero_rss(self):
        self.complete_phases()
        self.clock.value += 0.5
        record = self.collector.finish()
        self.assertTrue(record['complete'])
        self.assertEqual(record['outer']['wallNs'], 10_500_000_000)
        self.assertEqual(record['residualWallNs'], 2_500_000_000)
        self.assertEqual(sum(p['wallNs'] for p in record['phases']), 8_000_000_000)
        self.assertEqual(record['outer']['parentCpuSeconds'], 4.0)
        self.assertEqual(record['outer']['completedChildUserCpuSeconds'], 1.0)
        self.assertEqual(record['processLifetimeRssBytes'], 0)
        self.assertIsNone(record['optionalReasons']['processLifetimeRssBytes'])

    def test_overlap_duplicate_and_unknown_phase_rejected(self):
        with self.collector.phase('input'):
            with self.assertRaisesRegex(AccountingError, 'overlapping'):
                with self.collector.phase('replay'):
                    pass
        with self.assertRaisesRegex(AccountingError, 'duplicate'):
            with self.collector.phase('input'):
                pass
        with self.assertRaisesRegex(AccountingError, 'unknown'):
            with self.collector.phase('nested worker'):
                pass

    def test_missing_phases_failure_not_synthesized(self):
        with self.assertRaisesRegex(RuntimeError, 'raw failure'):
            with self.collector.phase('input'):
                self.clock.value = 2.0
                raise RuntimeError('raw failure')
        record = self.collector.finish(outcome='failure')
        self.assertFalse(record['complete'])
        self.assertEqual([p['name'] for p in record['phases']], ['input'])
        self.assertEqual(record['phases'][0]['outcome'], 'failure')
        self.assertEqual(record['phases'][0]['wallNs'], 2_000_000_000)
        self.assertTrue(any('missing required' in e for e in record['errors']))

    def test_invalid_and_reversed_wall_clock(self):
        for value in (math.nan, math.inf, -1.0):
            with self.subTest(value=value):
                with self.assertRaisesRegex(AccountingError, 'invalid'):
                    UtilityAccounting(monotonic=lambda: value).start()
        self.clock.value = 1.0
        with self.collector.phase('input'):
            pass
        self.clock.value = 0.0
        with self.assertRaisesRegex(AccountingError, 'reversed'):
            self.collector.finish()

    def test_unavailable_counter_is_null_healthy_zero_is_zero(self):
        def unavailable():
            raise OSError('unsupported')
        self.collector.parent_cpu = unavailable
        self.complete_phases()
        record = self.collector.finish()
        self.assertTrue(record['complete'])
        self.assertIsNone(record['outer']['parentCpuSeconds'])
        self.assertIn('unavailable', record['outer']['counterReasons']['parentCpuSeconds'])
        self.assertEqual(record['outer']['completedChildUserCpuSeconds'], 1.0)

    def test_reversed_cpu_invalidates_not_clamped(self):
        self.cpu.value = 2.0
        with self.collector.phase('input'):
            self.cpu.value = 1.0
        record = self.collector.finish(outcome='failure')
        self.assertFalse(record['complete'])
        self.assertIsNone(record['phases'][0]['parentCpuSeconds'])
        self.assertIn('invalid reversed', record['phases'][0]['counterReasons']['parentCpuSeconds'])

    def test_unasserted_child_scope_not_called_or_claimed(self):
        def unexpected():
            raise AssertionError('must not sample unasserted children')
        collector = UtilityAccounting(monotonic=self.clock, child_cpu=unexpected,
                                      lifetime_rss=lambda: 0).start()
        record = collector.finish(outcome='failure')
        self.assertIsNone(record['outer']['completedChildUserCpuSeconds'])
        self.assertIn('not asserted', record['outer']['counterReasons']['completedChildUserCpuSeconds'])

    def test_sealing_outside_outer_and_preview_unsealed(self):
        with self.collector.phase('input'):
            preview = self.collector.preview()
            self.assertFalse(preview['sealed'])
            self.assertNotIn('endWallNs', preview)
        self.complete_remaining()
        record = self.collector.finish()
        closing = record['outer']['endWallNs']
        def encoder(value):
            self.assertEqual(value['outer']['endWallNs'], closing)
            self.clock.value += 3.0
            return b'encoded'
        encoded, observer = self.collector.seal(encoder)
        self.assertEqual(encoded, b'encoded')
        self.assertEqual(observer['wallNs'], 3_000_000_000)
        self.assertEqual(observer['startWallNs'], closing)
        self.assertEqual(self.collector.snapshot()['outer']['endWallNs'], closing)

    def test_sealing_includes_finish_aggregation_and_intermediate_work(self):
        self.complete_phases()
        def rss_with_observer_work():
            self.clock.value += 2.0
            self.cpu.value += 0.25
            return 0
        self.collector.lifetime_rss = rss_with_observer_work
        record = self.collector.finish()
        closing = record['outer']['endWallNs']
        self.clock.value += 1.0  # Intermediate final payload construction.
        def encoder(value):
            self.clock.value += 3.0
            self.cpu.value += 0.5
            return value['outer']['endWallNs']
        encoded, observer = self.collector.seal(encoder)
        self.assertEqual(encoded, closing)
        self.assertEqual(observer['startWallNs'], closing)
        self.assertEqual(observer['wallNs'], 6_000_000_000)
        self.assertEqual(observer['parentCpuSeconds'], 0.75)
        self.assertEqual(record['outer']['wallNs'], 10_000_000_000)
        self.assertEqual(record['outer']['parentCpuSeconds'], 4.0)
        self.assertEqual(self.collector.snapshot()['outer']['endWallNs'], closing)
        with self.assertRaisesRegex(AccountingError, 'already sealed'):
            self.collector.seal(lambda _: None)

    def complete_remaining(self):
        for name in PHASES[1:]:
            with self.collector.phase(name):
                self.clock.value += 1.0

    def test_worker_union_is_not_sum_and_adjacent_not_overlap(self):
        self.complete_phases()
        for start, end in ((1, 4), (2, 5), (5, 7)):
            self.collector.record_worker_interval(start, end)
        record = self.collector.finish()
        self.assertEqual(record['workerIntervals']['unionWallNs'], 6_000_000_000)
        self.assertEqual(record['workerIntervals']['peakOccupancy'], 2)

    def test_budget_registry_deduplicates_and_does_not_sum_child_cpu(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.collector.activate_git_budget_registry():
                budget = observed_budget(root)
                self.collector._register_budget(budget)
                budget.commands = 3
                budget.output_bytes = 11
                budget.child_user_cpu_seconds = 999
                budget.scratch_exceeds_limit()
                other = observed_budget(root)
                other.commands = 2
                other.output_bytes = 7
            self.complete_phases()
            record = self.collector.finish()
            budget.commands = 100
            self.assertEqual(record['gitBudgetCount'], 2)
            self.assertEqual(record['gitCommands'], 5)
            self.assertEqual(record['acceptedBudgetOutputBytes'], 18)
            self.assertIsNone(record['sampledScratchPeakBytes'])
            self.assertIn('does not expose', record['optionalReasons']['sampledScratchPeakBytes'])
            self.assertEqual(record['outer']['completedChildUserCpuSeconds'], 1.0)
            self.assertEqual(self.collector.snapshot()['gitCommands'], 5)

    def test_registry_capacity_does_not_interrupt_budget_creation(self):
        self.collector.max_budgets = 1
        with tempfile.TemporaryDirectory() as directory:
            with self.collector.activate_git_budget_registry():
                first = observed_budget(Path(directory))
                second = observed_budget(Path(directory))
            self.assertIsNot(first, second)
        self.complete_phases()
        record = self.collector.finish()
        self.assertFalse(record['complete'])
        self.assertIn('budget registry capacity exceeded', record['errors'])
        self.assertIsNone(record['sampledScratchPeakBytes'])
        self.assertIsNone(record['gitCommands'])
        self.assertIsNone(record['acceptedBudgetOutputBytes'])

    def test_invalid_optional_counter_and_observer_error_mark_incomplete(self):
        self.collector.lifetime_rss = lambda: math.nan
        self.collector._register_budget(object())
        self.complete_phases()
        record = self.collector.finish()
        self.assertFalse(record['complete'])
        self.assertIsNone(record['processLifetimeRssBytes'])
        self.assertIsNone(record['gitCommands'])
        self.assertIn('invalid', record['optionalReasons']['processLifetimeRssBytes'])

    def test_failed_phase_prevents_complete_even_when_all_phases_present(self):
        with self.assertRaises(ValueError):
            with self.collector.phase('input'):
                raise ValueError('failure')
        self.complete_remaining()
        record = self.collector.finish(outcome='failure')
        self.assertFalse(record['complete'])
        self.assertEqual(len(record['phases']), len(PHASES))

    def test_worker_interval_outside_outer_rejected(self):
        self.complete_phases()
        self.collector.record_worker_interval(0, 11)
        with self.assertRaisesRegex(AccountingError, 'outside operational'):
            self.collector.finish()

    def test_observer_exception_does_not_change_runtime_creation(self):
        def broken(budget):
            raise ValueError('observer failed')
        with tempfile.TemporaryDirectory() as directory:
            with observe_git_budgets(broken):
                budget = observed_budget(Path(directory))
            self.assertEqual(budget.commands, 0)

    def test_budget_observer_returns_same_object_and_restores_context(self):
        seen = []
        other = []
        with tempfile.TemporaryDirectory() as directory:
            budget = GitCommandBudget(Path(directory))
            self.assertIs(observe_git_budget(budget), budget)
            with observe_git_budgets(seen.append):
                self.assertIs(observe_git_budget(budget), budget)
                with observe_git_budgets(other.append):
                    self.assertIs(observe_git_budget(budget), budget)
                self.assertIs(observe_git_budget(budget), budget)
            self.assertIs(observe_git_budget(budget), budget)
        self.assertEqual(seen, [budget, budget])
        self.assertEqual(other, [budget])

    def test_observer_base_exception_cannot_change_budget_execution_identity(self):
        def interrupt(_budget):
            raise KeyboardInterrupt('observer must not interrupt execution')
        with tempfile.TemporaryDirectory() as directory:
            budget = GitCommandBudget(Path(directory))
            with observe_git_budgets(interrupt):
                self.assertIs(observe_git_budget(budget), budget)
            self.assertEqual(budget.commands, 0)

    def test_runtime_factory_registers_unchanged_budget(self):
        seen = []
        with tempfile.TemporaryDirectory() as directory:
            with observe_git_budgets(seen.append):
                budget = runtime_budget(Path(directory))
            self.assertEqual(seen, [budget])
            self.assertEqual(budget.commands, 0)
            self.assertEqual(budget.max_commands, 256)

    def test_phase_budget_deltas_include_new_and_shared_worker_budgets_once(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.collector.activate_git_budget_registry():
                with self.collector.phase('input'):
                    budget = observed_budget(Path(directory))
                    budget.commands = 1
                    budget.output_bytes = 11
                with self.collector.phase('replay'):
                    def worker():
                        with budget.lock:
                            budget.commands += 5
                            budget.output_bytes += 13
                    thread = threading.Thread(target=worker)
                    thread.start()
                    thread.join()
                    other = observed_budget(Path(directory))
                    other.commands = 3
                    other.output_bytes = 12
                    self.collector._register_budget(budget)
                for name in PHASES[2:]:
                    with self.collector.phase(name):
                        pass
            record = self.collector.finish()
        first, second, *rest = record['phases']
        self.assertEqual((first['gitCommands'], first['acceptedBudgetOutputBytes']), (1, 11))
        self.assertEqual((second['gitCommands'], second['acceptedBudgetOutputBytes']), (8, 25))
        self.assertEqual([(p['gitCommands'], p['acceptedBudgetOutputBytes']) for p in rest], [(0, 0)] * 6)
        self.assertEqual((record['gitCommands'], record['acceptedBudgetOutputBytes']), (9, 36))
        self.assertEqual(sum(p['gitCommands'] for p in record['phases']), record['gitCommands'])
        self.assertIsNone(first['sampledScratchPeakBytes'])
        self.assertIn('cumulative sampled high-water', first['counterReasons']['sampledScratchPeakBytes'])

    def test_phase_budget_unavailable_and_invalid_are_null_not_partial(self):
        with self.collector.phase('input'):
            pass
        with tempfile.TemporaryDirectory() as directory:
            with self.collector.activate_git_budget_registry():
                with self.collector.phase('replay'):
                    budget = observed_budget(Path(directory))
                    budget.commands = -1
                with self.collector.phase('preparation'):
                    pass
        record = self.collector.finish(outcome='failure')
        self.assertIsNone(record['phases'][0]['gitCommands'])
        self.assertEqual(record['phases'][0]['counterReasons']['gitCommands'], 'no budget observer active')
        for phase in record['phases'][1:]:
            self.assertIsNone(phase['gitCommands'])
            self.assertIsNone(phase['acceptedBudgetOutputBytes'])
            self.assertIn('invalid budget', phase['counterReasons']['gitCommands'])
        self.assertIsNone(record['gitCommands'])
        self.assertFalse(record['complete'])

    def test_refused_output_is_excluded_from_named_accepted_budget_metric(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.collector.activate_git_budget_registry():
                with self.collector.phase('input'):
                    budget = observed_budget(Path(directory), max_output_bytes=10)
                    self.assertTrue(budget.record_output(7))
                    self.assertFalse(budget.record_output(5))
                    self.assertEqual(budget.output_bytes, 7)
                self.complete_remaining()
            record = self.collector.finish()
        self.assertEqual(record['acceptedBudgetOutputBytes'], 7)
        self.assertEqual(record['phases'][0]['acceptedBudgetOutputBytes'], 7)
        self.assertNotIn('capturedBytes', record)
        self.assertNotIn('capturedBytes', record['phases'][0])
        self.assertIsNone(record['observedCapturedOutputBytes'])
        self.assertIsNone(record['phases'][0]['observedCapturedOutputBytes'])
        self.assertIn('discarded overflow chunks excluded', record['scopes']['bytes'])
        self.assertIn('rejected or discarded', record['optionalReasons']['observedCapturedOutputBytes'])
        self.assertIn('total bytes read unavailable',
                      record['phases'][0]['counterReasons']['observedCapturedOutputBytes'])


if __name__ == '__main__':
    unittest.main()
