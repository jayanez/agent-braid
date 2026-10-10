"""Exact arithmetic controls through the public allocation module."""
from __future__ import annotations
from datetime import datetime
from decimal import Decimal, Inexact, Rounded, localcontext
from fractions import Fraction
import hashlib
import json
import unittest

from agent_braid import tooling_allocation as allocation

START = "2026-01-01T00:00:00Z"
END = "2026-01-01T04:00:00Z"
SOURCE_SHA = "a" * 64
ACCOUNT_SHA = "b" * 64

def digest(char: str) -> str:
    return char * 64

def interval(ref: str, sha: str, start: str, end: str):
    return allocation.UsageInterval(ref, sha, start, end)

def calculate(coverage, **changes):
    args = {
        "source_ref": "subscription-statement:period-1",
        "source_sha256": SOURCE_SHA,
        "account_sha256": ACCOUNT_SHA,
        "period_id": "period-1",
        "period_started_at": START,
        "period_ended_at": END,
        "fixed_period_fee": Decimal("12.00"),
        "currency": "USD",
        "interval_coverage": coverage,
    }
    args.update(changes)
    return allocation.calculate_subscription_time_allocation(**args)


def canonical_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


class SubscriptionTimeAllocationTests(unittest.TestCase):
    def test_overlapping_and_nested_use_counts_once_against_actual_period(self):
        coverage = allocation.IntervalCoverage.declared_complete((
            interval("r1", digest("1"), "2026-01-01T00:30:00Z", "2026-01-01T02:00:00Z"),
            interval("r2", digest("2"), "2026-01-01T01:00:00Z", "2026-01-01T03:00:00Z"),
            interval("r3", digest("3"), "2026-01-01T01:15:00Z", "2026-01-01T01:30:00Z"),
            interval("r4", digest("4"), "2026-01-01T03:30:00Z", END),
        ))
        result = calculate(coverage)
        self.assertEqual(result["state"], "calculated")
        self.assertEqual(result["resultType"], "provisional-calculation-not-final-money-receipt")
        self.assertFalse(result["finalMoneyReceiptIssued"])
        self.assertNotIn("dispatchAllowed", result)
        self.assertEqual(result["calculation"]["unionDurationMicroseconds"], 3 * 60 * 60 * 1_000_000)
        self.assertEqual(result["calculation"]["elapsedPeriodMicroseconds"], 4 * 60 * 60 * 1_000_000)
        self.assertEqual(result["calculation"]["allocationShare"]["rational"], "3/4")
        self.assertEqual(result["calculation"]["allocatedAmount"], {
            "currency": "USD", "numerator": "9", "denominator": "1", "rational": "9/1"})

    def test_independent_fraction_oracle_and_context_rounding_do_not_change_result(self):
        coverage = allocation.IntervalCoverage.declared_complete((
            interval("r1", digest("1"), "2026-01-01T00:00:00.000001Z", "2026-01-01T00:00:00.000004Z"),
        ))
        with localcontext() as ctx:
            ctx.prec = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            result = calculate(coverage, fixed_period_fee=Decimal("0.123456789012345678901234567890"))
        expected_share = Fraction(3, 4 * 60 * 60 * 1_000_000)
        expected_amount = Fraction(Decimal("0.123456789012345678901234567890")) * expected_share
        self.assertEqual(result["calculation"]["allocationShare"]["rational"], f"{expected_share.numerator}/{expected_share.denominator}")
        amount = result["calculation"]["allocatedAmount"]
        self.assertEqual(amount["rational"], f"{expected_amount.numerator}/{expected_amount.denominator}")
        self.assertEqual(amount["currency"], "USD")

    def test_order_permutation_is_canonical(self):
        items = [
            interval("a", digest("a"), "2026-01-01T00:10:00Z", "2026-01-01T00:20:00Z"),
            interval("b", digest("b"), "2026-01-01T00:30:00Z", "2026-01-01T00:40:00Z"),
        ]
        first = calculate(allocation.IntervalCoverage.declared_complete(items))
        second = calculate(allocation.IntervalCoverage.declared_complete(list(reversed(items))))
        self.assertEqual(first, second)

    def test_adjacent_partition_preserves_union_and_amount_but_binds_different_receipts(self):
        whole = calculate(allocation.IntervalCoverage.declared_complete((
            interval("whole", digest("c"), "2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"),
        )))
        split = calculate(allocation.IntervalCoverage.declared_complete((
            interval("part-a", digest("d"), "2026-01-01T00:00:00Z", "2026-01-01T00:20:00Z"),
            interval("part-b", digest("e"), "2026-01-01T00:20:00Z", "2026-01-01T01:00:00Z"),
        )))
        self.assertEqual(whole["calculation"]["unionDurationMicroseconds"], split["calculation"]["unionDurationMicroseconds"])
        self.assertEqual(whole["calculation"]["allocatedAmount"], split["calculation"]["allocatedAmount"])
        self.assertNotEqual(whole["calculationInputsSha256"], split["calculationInputsSha256"])

    def test_unknown_coverage_differs_from_declared_complete_zero(self):
        unknown = calculate(allocation.IntervalCoverage.unknown())
        zero = calculate(allocation.IntervalCoverage.declared_complete(()))
        self.assertEqual(unknown["state"], "unknown")
        self.assertIsNone(unknown["calculation"]["unionDurationMicroseconds"])
        self.assertIsNone(unknown["calculation"]["allocatedAmount"])
        self.assertEqual(zero["state"], "calculated")
        self.assertEqual(zero["calculation"]["unionDurationMicroseconds"], 0)
        self.assertEqual(zero["calculation"]["allocationShare"]["rational"], "0/1")
        self.assertEqual(zero["calculation"]["allocatedAmount"]["rational"], "0/1")
        self.assertNotEqual(unknown["calculationInputsSha256"], zero["calculationInputsSha256"])

    def test_declared_complete_coverage_copies_input_sequence_without_mutation(self):
        values = [interval("r", digest("1"), "2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z")]
        before = tuple(values)
        coverage = allocation.IntervalCoverage.declared_complete(values)
        result = calculate(coverage)
        self.assertEqual(tuple(values), before)
        values.append(interval("later", digest("2"), "2026-01-01T00:02:00Z", "2026-01-01T00:03:00Z"))
        self.assertEqual(len(coverage.intervals), 1)
        self.assertEqual(len(result["intervalCoverage"]["receipts"]), 1)

    def test_payload_hashes_are_independently_reproducible(self):
        result = calculate(allocation.IntervalCoverage.declared_complete(()))
        self.assertEqual(result["calculationInputsSha256"], canonical_hash({
            "schemaVersion": result["schemaVersion"], "source": result["source"],
            "period": result["period"], "intervalCoverage": result["intervalCoverage"],
        }))
        unhashed = dict(result)
        claimed = unhashed.pop("canonicalPayloadSha256")
        self.assertEqual(claimed, canonical_hash(unhashed))

    def test_digest_binds_source_account_period_and_interval_receipt(self):
        base = calculate(allocation.IntervalCoverage.declared_complete((
            interval("r", digest("1"), "2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),
        )))
        cases = [
            calculate(allocation.IntervalCoverage.declared_complete((interval("r", digest("1"), "2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),)), source_sha256=digest("c")),
            calculate(allocation.IntervalCoverage.declared_complete((interval("r", digest("1"), "2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),)), account_sha256=digest("d")),
            calculate(allocation.IntervalCoverage.declared_complete((interval("r", digest("2"), "2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),))),
            calculate(allocation.IntervalCoverage.declared_complete((interval("r", digest("1"), "2026-01-01T00:00:00Z", "2026-01-01T00:30:00Z"),)), period_id="period-2"),
        ]
        for changed in cases:
            self.assertNotEqual(base["calculationInputsSha256"], changed["calculationInputsSha256"])
            self.assertNotEqual(base["canonicalPayloadSha256"], changed["canonicalPayloadSha256"])

    def test_rejects_bad_timestamps_and_out_of_period_intervals(self):
        for bad in [
            lambda: interval("naive", digest("a"), "2026-01-01T00:00:00", "2026-01-01T00:01:00Z"),
            lambda: interval("reversed", digest("b"), "2026-01-01T00:02:00Z", "2026-01-01T00:01:00Z"),
            lambda: calculate(allocation.IntervalCoverage.declared_complete((interval("outside", digest("c"), "2025-12-31T23:59:59Z", "2026-01-01T00:01:00Z"),))),
            lambda: calculate(allocation.IntervalCoverage.declared_complete(()), period_started_at=END, period_ended_at=START),
            lambda: calculate(allocation.IntervalCoverage.declared_complete(()), period_started_at="2026-01-01T01:00:00+01:00"),
        ]:
            with self.subTest(bad=bad), self.assertRaises(allocation.AllocationError):
                bad()

    def test_rejects_duplicate_receipt_identity_or_digest(self):
        first = interval("same", digest("a"), "2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z")
        duplicate_ref = interval("same", digest("b"), "2026-01-01T00:02:00Z", "2026-01-01T00:03:00Z")
        duplicate_hash = interval("other", digest("a"), "2026-01-01T00:02:00Z", "2026-01-01T00:03:00Z")
        for pair in [(first, duplicate_ref), (first, duplicate_hash)]:
            with self.subTest(pair=pair), self.assertRaises(allocation.AllocationError):
                calculate(allocation.IntervalCoverage.declared_complete(pair))

    def test_accepts_exact_4096_interval_bound(self):
        items = tuple(interval(f"r{i}", f"{i + 1:064x}", "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z") for i in range(4096))
        result = calculate(allocation.IntervalCoverage.declared_complete(items))
        self.assertEqual(len(result["intervalCoverage"]["receipts"]), 4096)
        self.assertEqual(result["calculation"]["unionDurationMicroseconds"], 1_000_000)

    def test_rejects_interval_count_above_4096(self):
        items = tuple(interval(f"r{i}", f"{i + 1:064x}", "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z") for i in range(4097))
        with self.assertRaisesRegex(allocation.AllocationError, "4096"):
            allocation.IntervalCoverage.declared_complete(items)

    def test_oversized_counter_generator_consumes_at_most_4097_items(self):
        consumed = 0
        def source():
            nonlocal consumed
            for i in range(100_000_000):
                consumed += 1
                yield interval(f"g{i}", f"{i + 1:064x}", "2026-01-01T00:00:00Z", "2026-01-01T00:00:01Z")
        with self.assertRaisesRegex(allocation.AllocationError, "4096"):
            allocation.IntervalCoverage.declared_complete(source())
        self.assertEqual(consumed, allocation.MAX_INTERVALS + 1)

    def test_rejects_timestamp_precision_beyond_microseconds(self):
        for ts in ["2026-01-01T00:00:00.1234567Z", "2026-01-01T00:00:00.123456789+00:00"]:
            with self.subTest(timestamp=ts), self.assertRaises(allocation.AllocationError):
                interval("too-precise", digest("a"), ts, END)
        accepted = interval("six-digits", digest("b"), "2026-01-01T00:00:00.123456Z", "2026-01-01T00:00:01.000000+00:00")
        result = calculate(allocation.IntervalCoverage.declared_complete((accepted,)))
        self.assertEqual(result["intervalCoverage"]["receipts"][0]["startedAt"], "2026-01-01T00:00:00.123456Z")

    def test_rejects_negative_nonfinite_oversized_and_non_decimal_fees(self):
        for amount in [Decimal("-0.01"), Decimal("NaN"), Decimal("Infinity"), Decimal("1" * 31), Decimal("1e31"), 1.25, 1]:
            with self.subTest(amount=amount), self.assertRaises(allocation.AllocationError):
                calculate(allocation.IntervalCoverage.declared_complete(()), fixed_period_fee=amount)

    def test_rejects_bad_hash_currency_and_coverage_shape(self):
        for kwargs in [
            {"source_sha256": "not-a-hash"},
            {"account_sha256": "A" * 64},
            {"currency": "US"},
            {"currency": "usd"},
        ]:
            with self.subTest(kwargs=kwargs), self.assertRaises(allocation.AllocationError):
                calculate(allocation.IntervalCoverage.declared_complete(()), **kwargs)
        with self.assertRaises(allocation.AllocationError):
            allocation.IntervalCoverage("unknown", ())
        with self.assertRaises(allocation.AllocationError):
            allocation.IntervalCoverage("declared-complete", None)

    def test_no_implicit_eur_conversion_or_rounding(self):
        result = calculate(allocation.IntervalCoverage.declared_complete(()), fixed_period_fee=Decimal("12.34"), currency="GBP")
        amount = result["calculation"]["allocatedAmount"]
        self.assertEqual(amount, {"currency": "GBP", "numerator": "0", "denominator": "1", "rational": "0/1"})
        self.assertNotIn("EUR", json.dumps(result))
        self.assertNotIn("rounded", json.dumps(result).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
