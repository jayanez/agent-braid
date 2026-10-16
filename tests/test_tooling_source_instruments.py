# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned synthetic instruments are controls, never authentic provider evidence."""
import unittest

from agent_braid import tooling_costs as costs
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_registration_v6 as v6
from tests.test_tooling_registration_v6 import validated_v6
from tests.test_tooling_costs import _Verifier, _receipt


def instrument(registration, name):
    verifier = _Verifier()
    pin = registration.data["instrumentPins"][name]
    for attr, key in (("source_ref", "sourceRef"), ("source_sha256", "sourceSha256"),
                      ("verifier_ref", "verifierRef"), ("verifier_sha256", "verifierSha256")):
        setattr(verifier, attr, pin[key])
    return verifier


class SourceInstrumentTests(unittest.TestCase):
    def test_cost_book_refuses_unregistered_instrument_and_preserves_unknown_cash(self):
        registration = validated_v6()
        with self.assertRaises(costs.CostAccountingError):
            costs.CostBook(("setup",), verifier=_Verifier(), registration=registration)
        book = costs.CostBook(("setup",), verifier=instrument(registration, "costs"),
                             registration=registration)
        book.add(_receipt(monetary_basis="unavailable", values={"eur": None}))
        self.assertIsNone(book.snapshot(source_ref="view").values["eur"])

    def test_cost_instrument_drift_refuses_publication(self):
        registration = validated_v6()
        verifier = instrument(registration, "costs")
        book = costs.CostBook(("setup",), verifier=verifier, registration=registration)
        verifier.source_sha256 = "0" * 64
        with self.assertRaises(costs.CostAccountingError):
            book.add(_receipt())
        self.assertEqual((), book.history)

    def test_mutated_registration_cannot_select_an_instrument(self):
        registration = validated_v6()
        verifier = instrument(registration, "costs")
        registration.data["instrumentPins"]["costs"]["sourceSha256"] = "0" * 64
        with self.assertRaises(evaluation.EvaluationError):
            v6.require_instrument_identity(verifier, registration, "costs")
