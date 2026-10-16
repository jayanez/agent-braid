# SPDX-License-Identifier: AGPL-3.0-only
"""Offline hostile-receipt controls; test authenticators confer no real approval."""
import dataclasses
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

from agent_braid import tooling_receipt_instruments as instruments
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_capture as capture
from agent_braid import tooling_costs as costs
from agent_braid import tooling_sessions as sessions
from tests.test_tooling_registration_v6 import registration_v6, validated_v6


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class ReceiptInstrumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.root.chmod(0o700)
        self.now = datetime(2026, 10, 14, tzinfo=timezone.utc)
        self.pin = instruments.InstrumentIdentity('installed-source', '1'*64, 'installed-verifier', '2'*64)
        data = registration_v6()
        for name in ('admission', 'outcome', 'costs'):
            data['instrumentPins'][name] = {'sourceRef': self.pin.source_ref, 'sourceSha256': self.pin.source_sha256,
                                            'verifierRef': self.pin.verifier_ref, 'verifierSha256': self.pin.verifier_sha256}
        self.reg = validated_v6(data)
        self.slot = evaluation.generate_slots(self.reg)[0]
        self.values = {field: None for field in evaluation.COST_FIELDS}
        self.cost = costs.CostReceipt('setup', 1, 'measurement', '3'*64, self.text(), self.text(), self.text(), 'unavailable', self.values)
        self.evidence_path = self.root / 'source.json'
        self.evidence_path.write_bytes(b'{"observed":"offline-test"}')
        self.evidence_path.chmod(0o600)
        self.evidence_sha = hashlib.sha256(self.evidence_path.read_bytes()).hexdigest()
        self.cost = dataclasses.replace(self.cost, source_ref='meter', source_sha256=self.evidence_sha)
        self.context = instruments.cost_context(self.reg, self.cost)
        self.subject = self.cost.sha256
        self.document = {'schema': instruments.RECEIPT_SCHEMA, 'phase': 'costs', 'subjectSha256': self.subject,
                         'contextSha256': digest(self.context), 'observedAt': self.text(), 'decisionSha256': '4'*64,
                         'evidence': [{'ref': 'meter', 'sha256': self.evidence_sha, 'domains': ['cost-accounting']}],
                         'result': self.cost.subject()}
        self.receipt = self.root / 'receipt.json'
        self.write()
        self.request_seen = None

    def text(self):
        return self.now.isoformat().replace('+00:00', 'Z')

    def write(self):
        self.receipt.write_bytes(canonical(self.document))
        self.receipt.chmod(0o600)

    def authenticate(self, request):
        self.request_seen = request
        return instruments.DocumentAuthentication(request.document_sha256, request.context_sha256,
            request.subject_sha256, json.loads(request.document_bytes)['decisionSha256'], request.evidence_sha256, request.required_domains)

    def verifier(self, authenticate=None, **kwargs):
        return instruments.PrivateCostInstrument(registration=self.reg, identity=self.pin,
            documents={('costs', self.subject): instruments.PrivateDocument(self.receipt, hashlib.sha256(self.receipt.read_bytes()).hexdigest())},
            evidence={'meter': instruments.PrivateDocument(self.evidence_path, self.evidence_sha)},
            authenticator=authenticate or self.authenticate, clock=lambda: self.now, **kwargs)

    def test_unknown_cash_remains_unknown_in_verified_cost(self):
        attestation = self.verifier().verify(self.cost)
        self.assertEqual(self.cost.sha256, attestation.subject_sha256)
        self.assertIsNone(self.cost.values['eur'])
        self.assertIn(b'"eur":null', self.request_seen.context_bytes)
        self.assertEqual((self.evidence_sha,), self.request_seen.evidence_sha256)

    def test_false_authenticator_or_synthetic_domain_cannot_attest(self):
        for callback in (lambda req: None, lambda req: dataclasses.replace(self.authenticate(req), domains=('synthetic-control',)),
                         lambda req: dataclasses.replace(self.authenticate(req), evidence_sha256=('f'*64,))):
            with self.subTest(callback=callback), self.assertRaises(instruments.ReceiptVerificationError):
                self.verifier(callback).verify(self.cost)

    def test_crossed_context_refuses_before_authentication(self):
        self.document['contextSha256'] = 'f'*64
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier().verify(self.cost)
        self.assertIsNone(self.request_seen)

    def test_evidence_drift_during_authentication_refuses(self):
        def mutate(req):
            self.evidence_path.write_bytes(b'changed')
            return self.authenticate(req)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier(mutate).verify(self.cost)

    def test_cancel_during_authentication_refuses(self):
        cancel = threading.Event()
        def cancelled(req):
            cancel.set()
            return self.authenticate(req)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier(cancelled, cancel_event=cancel).verify(self.cost)

    def test_symlink_or_world_readable_evidence_refuses(self):
        verifier = self.verifier()
        self.evidence_path.chmod(0o644)
        with self.assertRaises(instruments.ReceiptVerificationError):
            verifier.verify(self.cost)
        self.evidence_path.chmod(0o600)
        original = self.evidence_path.with_suffix('.original')
        self.evidence_path.rename(original)
        self.evidence_path.symlink_to(original)
        with self.assertRaises(instruments.ReceiptVerificationError):
            verifier.verify(self.cost)

    def test_missing_authenticator_refuses_installation(self):
        with self.assertRaises(instruments.ReceiptVerificationError):
            instruments.PrivateCostInstrument(registration=self.reg, identity=self.pin, documents={}, evidence={}, authenticator=None)

    def test_future_source_cannot_be_retimed_by_current_receipt(self):
        future = (self.now + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')
        self.cost = dataclasses.replace(self.cost, ended_at=future, observed_at=future)
        self.context = instruments.cost_context(self.reg, self.cost)
        self.subject = self.cost.sha256
        self.document.update(subjectSha256=self.subject, contextSha256=digest(self.context), result=self.cost.subject())
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier().verify(self.cost)

    def test_duplicate_keys_size_missing_domain_and_expiry_refuse(self):
        for raw in (b'{"schema":"one","schema":"two"}', b' '*(instruments.MAX_DOCUMENT_BYTES + 1)):
            self.receipt.write_bytes(raw)
            with self.subTest(raw_size=len(raw)), self.assertRaises(instruments.ReceiptVerificationError):
                self.verifier().verify(self.cost)
        self.document['observedAt'] = (self.now - timedelta(seconds=61)).isoformat()
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier().verify(self.cost)
        self.document['observedAt'] = self.text()
        self.document['evidence'][0]['domains'] = []
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier().verify(self.cost)

    def test_clock_regression_and_expiry_during_authentication_refuse(self):
        for delta in (-1, 61):
            verifier = self.verifier(lambda req: self.shift_clock(req, delta))
            with self.subTest(delta=delta), self.assertRaises(instruments.ReceiptVerificationError):
                verifier.verify(self.cost)
            self.now = datetime(2026, 10, 14, tzinfo=timezone.utc)

    def shift_clock(self, request, delta):
        self.now += timedelta(seconds=delta)
        return self.authenticate(request)

    def test_registration_mutation_by_authenticator_refuses(self):
        def mutate(request):
            self.reg.data['candidate']['version'] = 'changed'
            return self.authenticate(request)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier(mutate).verify(self.cost)

    def test_measurement_source_hash_mismatch_refuses(self):
        self.cost = dataclasses.replace(self.cost, source_sha256='f'*64)
        self.context = instruments.cost_context(self.reg, self.cost)
        self.subject = self.cost.sha256
        self.document.update(subjectSha256=self.subject, contextSha256=digest(self.context), result=self.cost.subject())
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verifier().verify(self.cost)

    def outcome_setup(self, *, status='invalid', completion=False, authority=False):
        self.admission_body = {'registrationSha256': self.reg.sha256, 'slot': self.slot.as_dict(),
                               'attemptId': 'synthetic-attempt', 'subjectSha256': '5'*64}
        self.admission = {'receipt': self.admission_body, 'receiptSha256': digest(self.admission_body)}
        self.raw_outcome = {'trace': ['fixture result diverged']}
        self.subject = '6'*64
        self.verified_outcome = sessions.VerifiedOutcome(status, completion, authority, self.values,
            self.slot.fixture_sha256, '7'*64, self.text(), 0, 'fixture mismatch')
        self.context = instruments.outcome_context(self.reg, self.slot, self.admission, self.raw_outcome)
        self.document.update(phase='outcome', subjectSha256=self.subject, contextSha256=digest(self.context),
            result=dataclasses.asdict(self.verified_outcome))
        self.document['evidence'][0]['domains'] = ['native-outcome', 'deterministic-oracle', 'model-identity']
        self.write()

    def oracle(self, request, raw):
        return instruments.OracleResult(self.verified_outcome, request.context_sha256,
            hashlib.sha256(raw).hexdigest(), request.evidence_sha256, digest(dataclasses.asdict(self.verified_outcome)))

    def outcome_verifier(self, *, oracle=None, authenticate=None):
        return instruments.PrivateOutcomeInstrument(registration=self.reg, identity=self.pin,
            documents={('outcome', self.subject): instruments.PrivateDocument(self.receipt, hashlib.sha256(self.receipt.read_bytes()).hexdigest())},
            evidence={'meter': instruments.PrivateDocument(self.evidence_path, self.evidence_sha)},
            authenticator=authenticate or self.authenticate, oracle=oracle or self.oracle, clock=lambda: self.now)

    def verify_outcome(self, verifier):
        return verifier.verify_outcome(registration=self.reg, slot=self.slot, admission_receipt=self.admission,
            raw_outcome=self.raw_outcome, subject_sha256=self.subject)

    def test_independent_oracle_negative_outcome_and_unknown_cash_preserved(self):
        self.outcome_setup()
        outcome, attestation = self.verify_outcome(self.outcome_verifier())
        self.assertEqual('invalid', outcome.status)
        self.assertIs(outcome.completion, False)
        self.assertIs(outcome.authority_correct, False)
        self.assertIsNone(outcome.costs['eur'])
        self.assertEqual(self.subject, attestation.subject_sha256)
        with self.assertRaises(TypeError):
            outcome.costs['eur'] = 0

    def test_falsely_declared_success_or_oracle_evidence_mismatch_refuses(self):
        self.outcome_setup()
        self.document['result'].update(status='valid', completion=True, authority_correct=True)
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verify_outcome(self.outcome_verifier())
        self.outcome_setup()
        def wrong_oracle(request, raw):
            return dataclasses.replace(self.oracle(request, raw), evidence_sha256=('f'*64,))
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verify_outcome(self.outcome_verifier(oracle=wrong_oracle))

    def test_crossed_admission_slot_and_raw_outcome_mutation_refuse(self):
        self.outcome_setup()
        verifier = self.outcome_verifier()
        self.admission_body['slot'] = evaluation.generate_slots(self.reg)[1].as_dict()
        self.admission['receiptSha256'] = digest(self.admission_body)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verify_outcome(verifier)
        self.outcome_setup()
        def mutate(request):
            self.raw_outcome['trace'].append('changed after authentication')
            return self.authenticate(request)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verify_outcome(self.outcome_verifier(authenticate=mutate))

    def test_oracle_required_and_valid_cannot_have_unknown_completion(self):
        self.outcome_setup(status='valid', completion=None, authority=True)
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.verify_outcome(self.outcome_verifier())
        with self.assertRaises(instruments.ReceiptVerificationError):
            instruments.PrivateOutcomeInstrument(oracle=None, registration=self.reg, identity=self.pin,
                documents={}, evidence={}, authenticator=self.authenticate)

    def dispatch_setup(self, phase):
        self.measured = capture.MeasuredCosts({field: None if field == 'eur' else 0 for field in evaluation.COST_FIELDS},
                                              'meter', self.evidence_sha, self.text())
        self.stop = capture.StopState(False, False, 0, 'meter', self.evidence_sha, self.text())
        self.authorization = capture.AuthorizationContext('none', 'meter', self.evidence_sha)
        self.subject = '8'*64
        self.observation = TestObservation({'observedAt': self.text(), 'domain': 'offline-test-double',
                                            'sourceRef': 'meter', 'sourceSha256': self.evidence_sha})
        if phase == 'admission':
            self.context = instruments.admission_context(self.reg, self.slot, self.authorization, self.measured,
                self.stop, self.observation, self.observation, self.observation)
            result = {'admitted': True}
            self.document['decisionSha256'] = self.evidence_sha
        else:
            self.admission_body = {'registrationSha256': self.reg.sha256, 'slot': self.slot.as_dict(),
                                   'attemptId': 'synthetic-attempt', 'subjectSha256': '5'*64}
            self.admission = {'receipt': self.admission_body, 'receiptSha256': digest(self.admission_body)}
            self.context = instruments.start_context(self.reg, self.slot, self.admission, '9'*64,
                                                     self.measured, self.stop, self.observation)
            result = {'startVerified': True}
        self.document.update(phase=phase, subjectSha256=self.subject, contextSha256=digest(self.context), result=result)
        self.document['evidence'][0]['domains'] = list(instruments._DOMAINS[phase])
        self.write()

    def dispatch_verifier(self, phase, authenticate=None):
        kwargs = dict(registration=self.reg, identity=self.pin,
            documents={(phase, self.subject): instruments.PrivateDocument(self.receipt, hashlib.sha256(self.receipt.read_bytes()).hexdigest())},
            evidence={'meter': instruments.PrivateDocument(self.evidence_path, self.evidence_sha)},
            authenticator=authenticate or self.authenticate, clock=lambda: self.now)
        if phase == 'admission':
            return instruments.PrivateAdmissionInstrument(**kwargs)
        return instruments.PrivateOutcomeInstrument(oracle=self.oracle, **kwargs)

    def admit(self, verifier, observation=True):
        obs = self.observation if observation else None
        return verifier.attest(registration=self.reg, slot=self.slot, authorization=self.authorization,
            costs=self.measured, stop_state=self.stop, subject_sha256=self.subject,
            subscription=obs, subscription_estimate=obs, model_identity_observation=obs)

    def start(self, verifier):
        return verifier.verify_start(registration=self.reg, slot=self.slot, admission_receipt=self.admission,
            ledger_sha256='9'*64, measured_costs=self.measured, stop_state=self.stop,
            subject_sha256=self.subject, model_identity_observation=self.observation)

    def test_complete_admission_context_bound_to_original_decision(self):
        self.dispatch_setup('admission')
        result = self.admit(self.dispatch_verifier('admission'))
        self.assertIsInstance(result, capture.DecisionAttestation)
        self.assertEqual(self.evidence_sha, result.decision_sha256)
        for field in ('registration', 'authorization', 'measuredCosts', 'stopState', 'subscription',
                      'subscriptionEstimate', 'modelIdentityObservation'):
            self.assertIn(field, json.loads(self.request_seen.context_bytes))

    def test_missing_actual_admission_facts_or_declared_hash_only_refuse(self):
        self.dispatch_setup('admission')
        verifier = self.dispatch_verifier('admission')
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.admit(verifier, observation=False)
        self.document['evidence'][0]['domains'].remove('rights')
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.admit(self.dispatch_verifier('admission'))

    def test_start_binds_admission_and_current_ledger_without_starting_process(self):
        self.dispatch_setup('start')
        result = self.start(self.dispatch_verifier('start'))
        self.assertIsInstance(result, sessions.StartAttestation)
        self.assertEqual(self.subject, result.subject_sha256)
        self.assertEqual(self.admission, json.loads(self.request_seen.context_bytes)['admissionReceipt'])

    def test_open_stop_does_not_attest_admission_or_start(self):
        for phase in ('admission', 'start'):
            self.dispatch_setup(phase)
            self.stop = dataclasses.replace(self.stop, incident_open=True)
            with self.subTest(phase=phase), self.assertRaises(instruments.ReceiptVerificationError):
                (self.admit if phase == 'admission' else self.start)(self.dispatch_verifier(phase))


    def test_missing_nonmonetary_measure_cannot_be_zero_filled_for_start(self):
        self.dispatch_setup('start')
        self.measured = dataclasses.replace(self.measured, values={**self.measured.values, 'tokens': None})
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.start(self.dispatch_verifier('start'))
        self.assertIsNone(self.request_seen)

    def test_start_positive_cash_refuses_even_with_all_factual_domains(self):
        self.dispatch_setup('start')
        self.measured = dataclasses.replace(self.measured, values={**self.measured.values, 'eur': 0.01})
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.start(self.dispatch_verifier('start'))

    def test_instrument_pin_cannot_be_replaced_by_authenticator(self):
        def mutate(request):
            self.pin = instruments.InstrumentIdentity('changed-source', '1'*64, 'installed-verifier', '2'*64)
            verifier._identity = self.pin
            return self.authenticate(request)
        verifier = self.verifier(mutate)
        with self.assertRaises(instruments.ReceiptVerificationError):
            verifier.verify(self.cost)

    def test_grant_hash_without_original_grant_bytes_refuses(self):
        self.dispatch_setup('admission')
        self.slot = next(slot for slot in evaluation.generate_slots(self.reg) if slot.journey_class == 'execute-granted-batch-verify')
        self.authorization = capture.AuthorizationContext('existing-grant', 'meter', self.evidence_sha,
            'missing-original-grant', 'a'*64, 'b'*64, grant_action='execute')
        self.context = instruments.admission_context(self.reg, self.slot, self.authorization, self.measured,
            self.stop, self.observation, self.observation, self.observation)
        self.document['contextSha256'] = digest(self.context)
        self.write()
        with self.assertRaises(instruments.ReceiptVerificationError):
            self.admit(self.dispatch_verifier('admission'))


class TestObservation:
    """Explicit synthetic observation used only with this offline trust-root fake."""
    def __init__(self, data):
        self.data = data

    def as_dict(self):
        return self.data
