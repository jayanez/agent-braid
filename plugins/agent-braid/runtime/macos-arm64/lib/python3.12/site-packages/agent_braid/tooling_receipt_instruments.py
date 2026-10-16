# SPDX-License-Identifier: AGPL-3.0-only
"""Concrete private-document readers for M4.5 verifier protocols.

Authenticators and outcome oracles remain explicit trust roots. Byte equality,
registration pins and JSON assertions alone never authenticate a real decision,
measurement, model, human, process, account or grant. No dispatch or network I/O.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import threading
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from . import tooling_capture as capture
from . import tooling_costs as costs
from . import tooling_evaluation as evaluation
from . import tooling_registration_v6 as v6
from . import tooling_sessions as sessions

RECEIPT_SCHEMA = 'agent-braid-m45-private-instrument-receipt-v1'
MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_DOMAINS = {
    'admission': ('approval', 'rights', 'authority', 'cost-accounting', 'stop-state', 'source-composition', 'model-identity'),
    'start': ('approval', 'authority', 'cost-accounting', 'stop-state', 'source-composition', 'model-identity'),
    'outcome': ('native-outcome', 'deterministic-oracle', 'model-identity'),
    'costs': ('cost-accounting',),
}


class ReceiptVerificationError(ValueError):
    """A private instrument could not authenticate its exact observation boundary."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                          allow_nan=False).encode('utf-8')
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ReceiptVerificationError('inputs must be bounded canonical JSON data') from exc


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _digest(value: Any) -> str:
    return _hash(_canonical(value))


def _sha(value: Any) -> None:
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise ReceiptVerificationError('an exact SHA-256 is required')


def _time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
            raise ValueError
        return parsed
    except (AttributeError, TypeError, ValueError) as exc:
        raise ReceiptVerificationError('explicit UTC observation time required') from exc


def _project(value: Any) -> Any:
    if value is None:
        return None
    if callable(getattr(value, 'as_dict', None)):
        return value.as_dict()
    if is_dataclass(value):
        return asdict(value)
    raise ReceiptVerificationError('a typed observation is required')


@dataclass(frozen=True)
class InstrumentIdentity:
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str

    def __post_init__(self):
        for value in (self.source_ref, self.verifier_ref):
            if type(value) is not str or not value or len(value) > 256:
                raise ReceiptVerificationError('bounded instrument references required')
        _sha(self.source_sha256)
        _sha(self.verifier_sha256)


@dataclass(frozen=True)
class PrivateDocument:
    path: Path
    sha256: str

    def __post_init__(self):
        object.__setattr__(self, 'path', Path(self.path))
        _sha(self.sha256)


@dataclass(frozen=True)
class AuthenticationRequest:
    """Immutable complete context and evidence bytes for an external trust root."""
    phase: str
    subject_sha256: str
    document_sha256: str
    context_sha256: str
    document_bytes: bytes
    context_bytes: bytes
    evidence: tuple[tuple[str, bytes], ...]
    evidence_sha256: tuple[str, ...]
    required_domains: tuple[str, ...]


@dataclass(frozen=True)
class DocumentAuthentication:
    document_sha256: str
    context_sha256: str
    subject_sha256: str
    decision_sha256: str
    evidence_sha256: tuple[str, ...]
    domains: tuple[str, ...]


class ProvenanceAuthenticator(Protocol):
    """Authenticate original sources, every context field and required domain.

    For approval/rights/authority this includes original decisions and their
    applicability. Source composition and model identity include actual native
    observations. Cost accounting includes coverage and monetary basis. An
    authenticator must refuse synthetic claims in these real observation domains.
    """
    def __call__(self, request: AuthenticationRequest) -> DocumentAuthentication: ...


@dataclass(frozen=True)
class OracleResult:
    outcome: sessions.VerifiedOutcome
    context_sha256: str
    raw_outcome_sha256: str
    evidence_sha256: tuple[str, ...]
    outcome_sha256: str


class OutcomeOracle(Protocol):
    """Independently derive outcome fields from bound bytes and fixture oracles."""
    def __call__(self, request: AuthenticationRequest, raw_outcome_bytes: bytes) -> OracleResult: ...


def _context(registration, slot=None):
    try:
        evaluation._require_validated(registration)
    except evaluation.EvaluationError as exc:
        raise ReceiptVerificationError('registration is missing or mutated') from exc
    if registration.sha256 != _digest(registration.data):
        raise ReceiptVerificationError('registration was mutated')
    if slot is not None:
        if not isinstance(slot, evaluation.AttemptSlot) or slot not in evaluation.generate_slots(registration):
            raise ReceiptVerificationError('slot is outside the exact registered roster')
    return {'registrationSha256': registration.sha256, 'registration': registration.data,
            'slot': None if slot is None else slot.as_dict()}


def admission_context(registration, slot, authorization, measured_costs, stop_state,
                      subscription=None, subscription_estimate=None, model_identity_observation=None):
    """Full caller facts, independently bound beside the admission subject digest."""
    _preflight(registration, measured_costs, stop_state)
    capture._validate_context(slot, authorization)
    return {**_context(registration, slot), 'authorization': capture._authorization_dict(authorization),
            'measuredCosts': capture._costs_dict(measured_costs), 'stopState': capture._stop_dict(stop_state),
            'subscription': _project(subscription), 'subscriptionEstimate': _project(subscription_estimate),
            'modelIdentityObservation': _project(model_identity_observation)}


def start_context(registration, slot, admission_receipt, ledger_sha256, measured_costs, stop_state,
                  model_identity_observation=None):
    _sha(ledger_sha256)
    _preflight(registration, measured_costs, stop_state)
    _admission(registration, slot, admission_receipt)
    return {**_context(registration, slot), 'admissionReceipt': admission_receipt,
            'ledgerSha256': ledger_sha256, 'measuredCosts': capture._costs_dict(measured_costs),
            'stopState': capture._stop_dict(stop_state), 'modelIdentityObservation': _project(model_identity_observation)}


def outcome_context(registration, slot, admission_receipt, raw_outcome, model_identity_observation=None):
    _admission(registration, slot, admission_receipt)
    return {**_context(registration, slot), 'admissionReceipt': admission_receipt,
            'rawOutcomeSha256': _digest(raw_outcome), 'modelIdentityObservation': _project(model_identity_observation)}


def cost_context(registration: evaluation.ValidatedRegistration, receipt: costs.CostReceipt) -> dict[str, Any]:
    if not isinstance(receipt, costs.CostReceipt):
        raise ReceiptVerificationError('typed cost receipt required')
    return {**_context(registration), 'costReceipt': receipt.subject()}


def _admission(registration, slot, outer):
    try:
        body = outer['receipt']
        if (set(outer) != {'receipt', 'receiptSha256'} or _digest(body) != outer['receiptSha256']
                or body['registrationSha256'] != registration.sha256 or body['slot'] != slot.as_dict()):
            raise ValueError
    except (KeyError, TypeError, ValueError) as exc:
        raise ReceiptVerificationError('admission receipt differs from the exact registration/slot') from exc


def _decode(raw):
    def pairs(items):
        data = {}
        for key, value in items:
            if key in data:
                raise ReceiptVerificationError('duplicate receipt JSON key')
            data[key] = value
        return data
    try:
        data = json.loads(raw, object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ReceiptVerificationError('nonfinite JSON')))
        if type(data) is not dict:
            raise ValueError
        return data
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise ReceiptVerificationError('invalid private receipt JSON') from exc


def _read(document):
    try:
        path = document.path
        if not path.is_absolute() or path.resolve(strict=True) != path:
            raise ValueError
        parent = path.parent.stat()
        if parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) != 0o700:
            raise ValueError
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, 'rb') as source:
            before = os.fstat(source.fileno())
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != os.getuid()
                    or stat.S_IMODE(before.st_mode) != 0o600 or before.st_size > MAX_DOCUMENT_BYTES):
                raise ValueError
            raw = source.read(MAX_DOCUMENT_BYTES + 1)
            after = os.fstat(source.fileno())
        stable_fields = ('st_ino', 'st_dev', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_uid')
        if (any(getattr(before, name) != getattr(after, name) for name in stable_fields)
                or len(raw) > MAX_DOCUMENT_BYTES or _hash(raw) != document.sha256):
            raise ValueError
        current = path.stat()
        if (current.st_ino, current.st_dev, current.st_size, current.st_mtime_ns, current.st_ctime_ns) != (
                after.st_ino, after.st_dev, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError
        return raw
    except (OSError, RuntimeError, ValueError) as exc:
        raise ReceiptVerificationError('private source is missing, unsafe or changed') from exc


class _PrivateInstrument:
    def __init__(self, *, registration, identity, documents, evidence, authenticator,
                 clock=None, max_age_seconds=60, cancel_event=None):
        if not isinstance(identity, InstrumentIdentity) or not callable(authenticator):
            raise ReceiptVerificationError('frozen identity and explicit provenance authenticator required')
        if type(max_age_seconds) is not int or not 1 <= max_age_seconds <= 86400:
            raise ReceiptVerificationError('bounded receipt freshness required')
        _context(registration)
        self._registration = registration
        self._identity = identity
        self._documents = MappingProxyType(dict(documents))
        self._evidence = MappingProxyType(dict(evidence))
        if any(not isinstance(value, PrivateDocument) for value in (*self._documents.values(), *self._evidence.values())):
            raise ReceiptVerificationError('frozen private document pins required')
        self._authenticator = authenticator
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_age = max_age_seconds
        self._cancel = cancel_event
        self._last_time = None
        self._lock = threading.RLock()
        self._active = False

    @property
    def source_ref(self):
        return self._identity.source_ref

    @property
    def source_sha256(self):
        return self._identity.source_sha256

    @property
    def verifier_ref(self):
        return self._identity.verifier_ref

    @property
    def verifier_sha256(self):
        return self._identity.verifier_sha256

    def _now(self):
        if self._cancel is not None and self._cancel.is_set():
            raise ReceiptVerificationError('verification cancelled')
        now = self._clock()
        if (not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() != timezone.utc.utcoffset(now)
                or (self._last_time is not None and now < self._last_time)):
            raise ReceiptVerificationError('UTC clock regressed or became unavailable')
        self._last_time = now
        return now

    def _verify(self, phase, registration, subject, context_builder, derive=None):
        with self._lock:
            if self._active:
                raise ReceiptVerificationError('verification cannot reenter itself')
            self._active = True
            try:
                return self._verify_once(phase, registration, subject, context_builder, derive)
            except ReceiptVerificationError:
                raise
            except Exception as exc:
                raise ReceiptVerificationError('instrument trust root or bound inputs failed verification') from exc
            finally:
                self._active = False

    def _verify_once(self, phase, registration, subject, context_builder, derive):
        _sha(subject)
        if registration.sha256 != self._registration.sha256:
            raise ReceiptVerificationError('instrument belongs to another registration')
        name = 'outcome' if phase in {'start', 'outcome'} else phase
        try:
            v6.require_instrument_identity(self, registration, name)
        except evaluation.EvaluationError as exc:
            raise ReceiptVerificationError('instrument pin or registration drift') from exc
        before = self._now()
        context_bytes = _canonical(context_builder())
        if len(context_bytes) > MAX_DOCUMENT_BYTES:
            raise ReceiptVerificationError('context exceeds bounded input size')
        document = self._documents.get((phase, subject))
        if document is None:
            raise ReceiptVerificationError('no frozen document for this phase and subject')
        raw = _read(document)
        body = _decode(raw)
        required = {'schema', 'phase', 'subjectSha256', 'contextSha256', 'observedAt', 'decisionSha256', 'evidence', 'result'}
        if (set(body) != required or body['schema'] != RECEIPT_SCHEMA or body['phase'] != phase
                or body['subjectSha256'] != subject or body['contextSha256'] != _hash(context_bytes)):
            raise ReceiptVerificationError('document schema, phase or complete context mismatch')
        _sha(body['decisionSha256'])
        observed = _time(body['observedAt'])
        _observation_floor(json.loads(context_bytes), observed)
        if not 0 <= (before - observed).total_seconds() <= self._max_age:
            raise ReceiptVerificationError('document is future-dated or expired')
        rows = body['evidence']
        if type(rows) is not list or not 1 <= len(rows) <= 64:
            raise ReceiptVerificationError('bounded complete source evidence required')
        sources, pins, domains, refs = [], [], set(), set()
        for row in rows:
            if (type(row) is not dict or set(row) != {'ref', 'sha256', 'domains'}
                    or type(row['ref']) is not str or row['ref'] in refs
                    or type(row['domains']) is not list or not row['domains']
                    or any(type(domain) is not str or domain not in _DOMAINS[phase] for domain in row['domains'])):
                raise ReceiptVerificationError('invalid, duplicated or synthetic source domain')
            pin = self._evidence.get(row['ref'])
            if pin is None or pin.sha256 != row['sha256']:
                raise ReceiptVerificationError('source evidence is missing or differs from frozen pin')
            sources.append((row['ref'], _read(pin)))
            pins.append(pin)
            domains.update(row['domains'])
            refs.add(row['ref'])
        if domains != set(_DOMAINS[phase]):
            raise ReceiptVerificationError('document omits required factual domains')
        request = AuthenticationRequest(phase, subject, document.sha256, _hash(context_bytes), raw,
            context_bytes, tuple(sources), tuple(pin.sha256 for pin in pins), _DOMAINS[phase])
        authentication = self._authenticator(request)
        expected = DocumentAuthentication(request.document_sha256, request.context_sha256, subject,
            body['decisionSha256'], request.evidence_sha256, request.required_domains)
        if type(authentication) is not DocumentAuthentication or authentication != expected:
            raise ReceiptVerificationError('provenance authentication did not bind every required source and fact')
        result = None if derive is None else derive(request, body)
        after = self._now()
        if (not 0 <= (after - observed).total_seconds() <= self._max_age
                or _canonical(context_builder()) != context_bytes or _read(document) != raw
                or any(_read(pin) != source[1] for pin, source in zip(pins, sources))):
            raise ReceiptVerificationError('inputs, source, cancellation or freshness drifted during verification')
        v6.require_instrument_identity(self, registration, name)
        return body, after.isoformat().replace('+00:00', 'Z'), result


class PrivateAdmissionInstrument(_PrivateInstrument):
    """AdmissionVerifier backed by immutable private evidence and real provenance."""
    def attest(self, *, registration, slot, authorization, costs, stop_state, subject_sha256,
               subscription=None, subscription_estimate=None, model_identity_observation=None):
        def context():
            return admission_context(registration, slot, authorization, costs, stop_state, subscription,
                                     subscription_estimate, model_identity_observation)
        if (registration.data['schemaVersion'] == v6.REGISTRATION_SCHEMA
                and (subscription is None or model_identity_observation is None or subscription_estimate is None)):
            raise ReceiptVerificationError('v6 admission requires actual source, model and active-time observations')
        def derive(request, body):
            if body['result'] != {'admitted': True} or body['decisionSha256'] != authorization.decision_sha256:
                raise ReceiptVerificationError('admission is not the original affirmative authorization decision')
            _require_source(request, authorization.decision_ref, authorization.decision_sha256)
            for reference, sha256 in ((authorization.grant_ref, authorization.grant_sha256),
                                     (authorization.interrupted_run_ref, authorization.interrupted_run_sha256)):
                if reference is not None:
                    _require_source(request, reference, sha256)
            if authorization.plan_sha256 is not None and authorization.plan_sha256 not in request.evidence_sha256:
                raise ReceiptVerificationError('original grant-bound plan evidence is absent')
            if subscription_estimate is not None:
                estimate = _project(subscription_estimate)
                _require_source(request, estimate['sourceRef'], estimate['sourceSha256'])
            _require_source(request, costs.source_ref, costs.source_sha256)
            _require_source(request, stop_state.source_ref, stop_state.source_sha256)
        body, verified, _ = self._verify('admission', registration, subject_sha256, context, derive)
        return capture.DecisionAttestation(self.verifier_ref, body['decisionSha256'], subject_sha256, verified)


class PrivateOutcomeInstrument(_PrivateInstrument):
    """Start/outcome verifier; fixture oracle remains an explicit independent root."""
    def __init__(self, *, oracle, **kwargs):
        if not callable(oracle):
            raise ReceiptVerificationError('independent outcome oracle required')
        self._oracle = oracle
        super().__init__(**kwargs)

    def verify_start(self, *, registration, slot, admission_receipt, ledger_sha256, measured_costs,
                     stop_state, subject_sha256, model_identity_observation=None):
        def context():
            return start_context(registration, slot, admission_receipt, ledger_sha256, measured_costs,
                                 stop_state, model_identity_observation)
        def derive(request, body):
            if body['result'] != {'startVerified': True}:
                raise ReceiptVerificationError('start verification is not affirmative')
            _require_source(request, measured_costs.source_ref, measured_costs.source_sha256)
            _require_source(request, stop_state.source_ref, stop_state.source_sha256)
        body, verified, _ = self._verify('start', registration, subject_sha256, context, derive)
        return sessions.StartAttestation(self.verifier_ref, body['decisionSha256'], subject_sha256, verified)

    def verify_outcome(self, *, registration, slot, admission_receipt, raw_outcome, subject_sha256,
                       model_identity_observation=None):
        def context():
            return outcome_context(registration, slot, admission_receipt, raw_outcome, model_identity_observation)
        def derive(request, body):
            raw = _canonical(raw_outcome)
            result = self._oracle(request, raw)
            if type(result) is not OracleResult or type(result.outcome) is not sessions.VerifiedOutcome:
                raise ReceiptVerificationError('no typed independently derived outcome')
            normalized = _outcome(result.outcome, slot)
            if (result.context_sha256 != request.context_sha256 or result.raw_outcome_sha256 != _hash(raw)
                    or result.evidence_sha256 != request.evidence_sha256
                    or result.outcome_sha256 != _digest(normalized) or body['result'] != normalized):
                raise ReceiptVerificationError('oracle output does not match exact bound evidence and receipt')
            if _time(result.outcome.source_timestamp) > _time(body['observedAt']):
                raise ReceiptVerificationError('outcome observation predates its source')
            return sessions.VerifiedOutcome(**{**normalized, 'costs': MappingProxyType(dict(result.outcome.costs))})
        body, verified, result = self._verify('outcome', registration, subject_sha256, context, derive)
        return result, sessions.OutcomeAttestation(self.verifier_ref, body['decisionSha256'], subject_sha256, verified)


class PrivateCostInstrument(_PrivateInstrument):
    """CostVerifier preserving explicit unavailable billing and missing measures."""
    def verify(self, receipt: costs.CostReceipt) -> costs.CostAttestation:
        def context():
            return cost_context(self._registration, receipt)
        def derive(request, body):
            if body['result'] != receipt.subject():
                raise ReceiptVerificationError('cost receipt differs from authenticated original accounting')
            _require_source(request, receipt.source_ref, receipt.source_sha256)
        _, verified, _ = self._verify('costs', self._registration, receipt.sha256, context, derive)
        return costs.CostAttestation(self.verifier_ref, receipt.sha256, verified)


def _require_source(request, reference, sha256):
    if not any(ref == reference and _hash(raw) == sha256 for ref, raw in request.evidence):
        raise ReceiptVerificationError('original decision or measurement source is absent')


def _outcome(value, slot):
    if (value.status not in evaluation.FINAL_STATUSES - {'recovered'}
            or value.completion not in (True, False, None) or value.authority_correct not in (True, False, None)
            or (value.completion is not None and type(value.completion) is not bool)
            or (value.authority_correct is not None and type(value.authority_correct) is not bool)
            or type(value.interventions) is not int or value.interventions < 0
            or value.input_sha256 != slot.fixture_sha256
            or (value.reason is not None and (type(value.reason) is not str or not value.reason or len(value.reason) > 2048))
            or set(value.costs) != set(evaluation.COST_FIELDS)):
        raise ReceiptVerificationError('oracle outcome fields or fixture identity are invalid')
    if value.status == 'valid' and value.completion is not True:
        raise ReceiptVerificationError('valid outcome requires observed completion true')
    _sha(value.output_sha256)
    _time(value.source_timestamp)
    for field, amount in value.costs.items():
        if amount is not None and (type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0
                                   or ('tokens' in field and type(amount) is not int)):
            raise ReceiptVerificationError('oracle costs must preserve unknowns or finite nonnegative values')
    return {field: dict(value.costs) if field == 'costs' else getattr(value, field)
            for field in value.__dataclass_fields__}


def _observation_floor(context, observed):
    """Never retime sources when a private wrapper is refreshed.

    Domain-specific age limits remain checked by source-composition provenance
    and the runtime contract (including Claude recharge's separate 900s bound).
    """
    keys = {'observedAt', 'observedAtUtc', 'observed_at_utc', 'sourceTimestamp', 'source_timestamp'}
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in keys and child is not None and _time(child) > observed:
                    raise ReceiptVerificationError('receipt observation predates an original source')
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    for key, value in context.items():
        if key not in {'registration', 'slot'}:
            walk(value)


def _preflight(registration, measured_costs, stop_state):
    try:
        capture._validate_costs(measured_costs, allow_unknown_eur=registration.data['schemaVersion'] == v6.REGISTRATION_SCHEMA)
        capture._validate_stop_state(stop_state)
        if (stop_state.incident_open or stop_state.unrecoverable_run
                or stop_state.consecutive_infrastructure_failures >= 2):
            raise ValueError
        if registration.data['schemaVersion'] == v6.REGISTRATION_SCHEMA and measured_costs.values['eur'] not in (None, 0):
            raise ValueError
    except (capture.CaptureAdmissionError, ValueError, KeyError) as exc:
        raise ReceiptVerificationError('stop conditions, observed costs or unknown resource measures prevent dispatch') from exc
