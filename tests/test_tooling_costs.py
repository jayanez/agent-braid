# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic accounting controls; no provider calls or actual invoice claims."""
from dataclasses import replace
import threading
import unittest

from agent_braid.tooling_capture import CaptureAdmissionError, _validate_costs
from agent_braid.tooling_costs import CostAccountingError, CostAttestation, CostBook, CostReceipt


class _Verifier:
    def verify(self, receipt):
        return CostAttestation("test-verifier", receipt.sha256, receipt.observed_at)


def _receipt(activity="setup", revision=1, **changes):
    values = dict(eur=1.0, tokens=13, input_tokens=8, output_tokens=3,
                  retry_tokens=2, wall_seconds=60, rss_bytes=100, disk_bytes=200)
    values.update(changes.pop("values", {}))
    return CostReceipt(activity, revision, "source/" + activity, ("a" if activity == "setup" else "b") * 64,
                       changes.pop("started_at", "2026-10-08T10:00:00Z"),
                       changes.pop("ended_at", "2026-10-08T10:01:00Z"),
                       changes.pop("observed_at", "2026-10-08T10:01:00Z"),
                       changes.pop("monetary_basis", "invoice"), values, **changes)


class AccountingTests(unittest.TestCase):
    def test_revision_replaces_totals_retains_history_and_does_not_add_phases(self):
        book = CostBook(("setup", "attempt-1"), verifier=_Verifier())
        book.add(_receipt())
        book.add(_receipt(revision=2, observed_at="2026-10-08T11:00:00Z", values={"eur": 2}))
        book.add(_receipt("attempt-1", started_at="2026-10-08T10:01:00Z",
                          ended_at="2026-10-08T10:02:00Z", observed_at="2026-10-08T10:02:00Z",
                          values={"rss_bytes": 300, "disk_bytes": 400}))
        result = book.snapshot(source_ref="accounting/final")
        self.assertEqual(result.values["eur"], 3)
        self.assertEqual(result.values["tokens"], 26)
        self.assertEqual(result.values["retry_tokens"], 4)
        self.assertEqual(result.values["wall_seconds"], 120)
        self.assertEqual(result.values["rss_bytes"], 300)
        self.assertEqual(result.values["disk_bytes"], 400)
        self.assertEqual(len(book.history), 3)
        self.assertEqual(result.observed_at, "2026-10-08T10:02:00Z")
        _validate_costs(result)

    def test_estimate_and_reference_remain_unknown_until_actual_verified_receipt(self):
        for basis in ("estimate", "reference"):
            book = CostBook(("setup",), verifier=_Verifier())
            receipt = _receipt(monetary_basis=basis, values={"eur": 100})
            book.add(receipt)
            result = book.snapshot(source_ref="view")
            self.assertIsNone(result.values["eur"])
            with self.assertRaises(CaptureAdmissionError):
                _validate_costs(result)
            book.add(replace(receipt, revision=2, monetary_basis="invoice",
                             values={**receipt.values, "eur": 1}))
            self.assertEqual(book.snapshot(source_ref="view").values["eur"], 1)
            self.assertEqual(book.history[0][0].values["eur"], 100)

    def test_unobserved_activities_and_missing_values_are_unknown_not_zero(self):
        book = CostBook(("setup", "attempt-1"), verifier=_Verifier())
        book.add(_receipt(values={"eur": None}))
        result = book.snapshot(source_ref="view")
        self.assertTrue(all(value is None for value in result.values.values()))
        with self.assertRaises(CaptureAdmissionError):
            _validate_costs(result)

    def test_duplicate_source_overlap_or_revision_regression_does_not_mutate_book(self):
        book = CostBook(("setup", "attempt-1"), verifier=_Verifier())
        receipt = _receipt()
        book.add(receipt)
        bad = [receipt, replace(receipt, revision=3),
               replace(receipt, revision=2, values={**receipt.values, "eur": 0}),
               replace(receipt, revision=2, monetary_basis="reference"),
               _receipt("attempt-1"),
               replace(_receipt("attempt-1", started_at="2026-10-08T10:01:00Z",
                                ended_at="2026-10-08T10:02:00Z", observed_at="2026-10-08T10:02:00Z"),
                       source_sha256=receipt.source_sha256)]
        for item in bad:
            with self.subTest(item=item), self.assertRaises(CostAccountingError):
                book.add(item)
            self.assertEqual(len(book.history), 1)

    def test_external_rejection_and_wrong_subject_cannot_record_cost(self):
        class Reject:
            def verify(self, receipt):
                raise CostAccountingError("source unavailable")
        class Wrong:
            def verify(self, receipt):
                return CostAttestation("verifier", "0" * 64, receipt.observed_at)
        for verifier in (Reject(), Wrong()):
            book = CostBook(("setup",), verifier=verifier)
            with self.assertRaises(CostAccountingError):
                book.add(_receipt())
            self.assertEqual(book.history, ())

    def test_mutation_cannot_change_bound_values(self):
        receipt = _receipt()
        mutable = dict(receipt.values)
        immutable = replace(receipt, values=mutable)
        digest = immutable.sha256
        mutable["eur"] = 999
        self.assertEqual(immutable.sha256, digest)
        with self.assertRaises(TypeError):
            immutable.values["eur"] = 999

    def test_invalid_numeric_token_time_basis_and_roster_inputs(self):
        changes = [{"values": {"tokens": 15}}, {"values": {"tokens": True}},
                   {"values": {"eur": float("nan")}}, {"values": {"eur": -1}},
                   {"values": {"tokens": 13.0}}, {"monetary_basis": "guessed"},
                   {"monetary_basis": "unavailable"},
                   {"observed_at": "2026-10-08T10:01:00"},
                   {"ended_at": "2026-10-08T09:00:00Z"}]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(CostAccountingError):
                _receipt(**change)
        for roster in ((), ("setup", "setup")):
            with self.assertRaises(CostAccountingError):
                CostBook(roster, verifier=_Verifier())

    def test_oldest_observation_is_not_refreshed_by_snapshot_time(self):
        book = CostBook(("setup",), verifier=_Verifier())
        book.add(_receipt())
        first = book.snapshot(source_ref="view")
        second = book.snapshot(source_ref="view")
        self.assertEqual(first.observed_at, "2026-10-08T10:01:00Z")
        self.assertEqual(first, second)

    def test_concurrent_revision_is_serialized_before_verification_and_publication(self):
        entered, release, second_started = threading.Event(), threading.Event(), threading.Event()
        outcomes = []
        class WaitingVerifier:
            calls = 0
            def verify(self, receipt):
                self.calls += 1
                entered.set()
                if not release.wait(5):
                    raise RuntimeError("test verifier release timed out")
                return _Verifier().verify(receipt)
        verifier = WaitingVerifier()
        book = CostBook(("setup",), verifier=verifier)
        def add(receipt, second=False):
            if second:
                second_started.set()
            try:
                book.add(receipt)
                outcomes.append("accepted")
            except CostAccountingError:
                outcomes.append("rejected")
        first = threading.Thread(target=add, args=(_receipt(),))
        second = threading.Thread(target=add, args=(_receipt(values={"eur": 2}), True))
        first.start()
        try:
            self.assertTrue(entered.wait(5))
            second.start()
            self.assertTrue(second_started.wait(5))
        finally:
            release.set()
            first.join(5)
            if second.ident is not None:
                second.join(5)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertCountEqual(outcomes, ["accepted", "rejected"])
        self.assertEqual(verifier.calls, 1)
        self.assertEqual(len(book.history), 1)
        self.assertEqual(book.snapshot(source_ref="view").values["eur"], 1)

    def test_verifier_reentrancy_refuses_and_leaves_history_untouched(self):
        class Reentrant:
            def verify(self, receipt):
                book.add(receipt)
        book = CostBook(("setup",), verifier=Reentrant())
        with self.assertRaisesRegex(CostAccountingError, "reenter"):
            book.add(_receipt())
        self.assertEqual(book.history, ())

    def test_integer_aggregate_overflow_is_typed_accounting_error(self):
        book = CostBook(("setup", "attempt-1"), verifier=_Verifier())
        huge = {"tokens": 10 ** 308, "input_tokens": 10 ** 308,
                "output_tokens": 0, "retry_tokens": 0}
        book.add(_receipt(values=huge))
        book.add(_receipt("attempt-1", values=huge,
                          started_at="2026-10-08T10:01:00Z",
                          ended_at="2026-10-08T10:02:00Z",
                          observed_at="2026-10-08T10:02:00Z"))
        with self.assertRaisesRegex(CostAccountingError, "overflow"):
            book.snapshot(source_ref="view")


if __name__ == "__main__":
    unittest.main()
