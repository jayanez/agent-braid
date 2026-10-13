# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic full admission receipts; no actual decisions or provider sources."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone, timedelta
import json
import unittest

from agent_braid import tooling_capture as capture
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_registration_v6 as v6
from agent_braid import tooling_codex_sources as codex
from agent_braid import tooling_source_observer as sources
from agent_braid import tooling_sessions as sessions
from agent_braid import tooling_subscription_estimate as estimate
from tests import test_tooling_capture as _helpers
from tests.test_tooling_evaluation import _with_operational_policy
from tests.test_tooling_registration_v6 import registration_v6
from tests.test_tooling_codex_sources import fixture


class SourceAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.helper = _helpers.CaptureAdmissionTests()
        self.helper.setUp()
        self.addCleanup(self.helper.doCleanups)
        h = self.helper
        h._upgrade_to_v4_estimated_capture()
        _with_operational_policy(h.registration_data)
        h.registration_data["schemaVersion"] = v6.REGISTRATION_SCHEMA
        h.registration_data["billingPolicy"]["schema"] = v6.SOURCE_POLICY_SCHEMA
        extras = registration_v6()
        for field in v6.FIELDS:
            h.registration_data[field] = extras[field]
        h._write_registration()
        h.valid_registration = evaluation.validate_registration(h.registration_data,
            expected_candidate_sha256=h.artifact_sha256, expected_input_hashes=h.input_hashes)
        h.ledger = evaluation.new_ledger(h.valid_registration)
        h.receipts = capture.receipt_directory_for(h.valid_registration.sha256)
        self.slot = h._slot()
        self.binding = v6.binding_from_registration(h.valid_registration, self.slot.slot_id, self.slot.host)
        _, rows, _ = fixture()
        contract = self.binding.contract
        now = datetime.now(timezone.utc)
        for kind, row in rows.items():
            row.update(contractSha256=self.binding.contract_sha256,
                       binding=self.binding.binding.as_dict(), observedAt=now.isoformat(),
                       **contract["sources"][kind])
        composition = codex.compose_codex_sources(contract, rows,
            expected_contract_sha256=self.binding.contract_sha256, now=now)
        self.observation = sources.SourceObservation(composition, rows)
        ledger_sha = _helpers._sha(json.dumps(h.ledger.as_dict(), sort_keys=True, separators=(",", ":"),
                                            ensure_ascii=False).encode())
        self.active = estimate.ActiveTimeEvidence(h.valid_registration.sha256, ledger_sha,
            "synthetic-active-time", _helpers._sha("active"), now.isoformat().replace("+00:00", "Z"),
            {"codex": 0, "claude-code": 0})

    def prepare(self, observation=None, costs=None):
        h = self.helper
        verifier = _helpers._SubscriptionSyntheticVerifier()
        pin = h.valid_registration.data["instrumentPins"]["admission"]
        verifier.source_ref, verifier.source_sha256 = pin["sourceRef"], pin["sourceSha256"]
        verifier.verifier_ref, verifier.verifier_sha256 = pin["verifierRef"], pin["verifierSha256"]
        return capture.prepare_attempt(registration_path=h.registration_path,
            candidate_root=h.candidate, candidate_artifact=h.artifact,
            ledger=h.ledger, slot_id=self.slot.slot_id,
            authorization=h._authorization("analyze-interactions"),
            costs=costs or replace(h.costs, values={**h.costs.values, "eur": None}),
            stop_state=h.stop, verifier=verifier,
            receipt_directory=h.receipts, subscription=self.observation if observation is None else observation,
            subscription_estimate_active_time=self.active, model_identity_observation=h._model_observation())

    def test_receipt_round_trip_retains_distinct_source_claims_and_unknown_cash(self):
        h = self.helper
        admission = self.prepare()
        body = sessions._read_admission(admission, h.valid_registration, self.slot, ledger=h.ledger)["receipt"]
        self.assertEqual(self.binding, admission.subscription_binding)
        self.assertIsNone(body["measuredCosts"]["values"]["eur"])
        self.assertEqual(self.observation.as_dict(), body["subscription"])
        self.assertEqual("not-started", h.ledger.current_status(self.slot.slot_id))
        self.assertEqual(108, len(h.ledger.slots))
        for row in body["subscription"]["receipts"].values():
            self.assertNotIn("subscriptionActive", row["payload"])

    def test_stale_or_wrong_binding_claims_do_not_write_admission(self):
        rows = self.observation.as_dict()["receipts"]
        old = deepcopy(rows)
        past = datetime.now(timezone.utc) - timedelta(seconds=31)
        for row in old.values():
            row["observedAt"] = past.isoformat()
        # Compose valid historical bytes; actual admission must recheck expiry.
        composition = codex.compose_codex_sources(self.binding.contract, old,
            expected_contract_sha256=self.binding.contract_sha256, now=past)
        stale = sources.SourceObservation(composition, old)
        with self.assertRaises(capture.CaptureAdmissionError):
            self.prepare(stale)
        self.assertFalse(self.helper.receipts.exists())

    def test_known_additional_cash_and_legacy_full_human_utility_refuse(self):
        h = self.helper
        with self.assertRaises(capture.CaptureAdmissionError):
            self.prepare(costs=replace(h.costs, values={**h.costs.values, "eur": 0.01}))
        with self.assertRaisesRegex(evaluation.EvaluationError, "separate coverage"):
            evaluation.assess_utility_eligibility(h.valid_registration, h.ledger,
                setup_costs=None, human_ratings={})

    def test_unregistered_outcome_instrument_cannot_reach_durable_start(self):
        h = self.helper
        admission = self.prepare()

        class WrongInstrument:
            def verify_start(self, **kwargs):
                raise AssertionError("wrong instrument must not verify a start")

            def verify_outcome(self, **kwargs):
                raise AssertionError("wrong instrument must not verify an outcome")

        class Adapter:
            def execute(self, admission):
                raise AssertionError("wrong instrument must not dispatch")

        with self.assertRaisesRegex(sessions.SessionError, "outcome verifier identity"):
            sessions.execute_admitted_attempt(admission=admission,
                registration=h.valid_registration, ledger=h.ledger,
                candidate_root=h.candidate, candidate_artifact=h.artifact,
                registration_path=h.registration_path, adapter=Adapter(),
                verifier=WrongInstrument(), measured_costs=h.costs, stop_state=h.stop)
        self.assertFalse(sessions._started_path(admission, self.slot).exists())
