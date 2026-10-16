# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded read-only interface acquisition with private native-account binding.

The reader and provenance verifier must be installed from reviewed procedures.
No import starts work; this adapter accesses no credentials or provider account
itself and never infers authenticity from a self-reported boolean or digest.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import threading
import time
from typing import Any, Protocol
import unicodedata

from .tooling_subscription import OperationalProcessRouteBinding, operational_binding_from_dict

OBSERVATION_SCHEMA = "agent-braid-interface-observation-v1"
MAX_TRACE_BYTES = 4 * 1024 * 1024
ORGANIZATION_BINDING = "owner-declared-single-organization"
_ORIGINS = {"codex": "https://chatgpt.com", "claude-code": "https://claude.ai"}


class InterfaceObserverError(ValueError):
    """Redacted refusal; never includes raw account identity or browser trace."""


def _hash(value):
    if (type(value) is not str or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise InterfaceObserverError("frozen lowercase SHA-256 required")


def _key(value: bytes) -> bytes:
    if type(value) is not bytes or len(value) < 32:
        raise InterfaceObserverError("private HMAC key must contain at least 32 bytes")
    return value


def private_email_binding(email: str, private_key: bytes, *, method: str = "interface-email-v1") -> str:
    """Same domain-separated canonicalization for browser and native profile."""
    _key(private_key)
    if type(email) is not str:
        raise InterfaceObserverError("explicit current account email required")
    if type(method) is not str or method not in {"interface-email-v1", "claude-account-email-v1"}:
        raise InterfaceObserverError("unsupported native email binding method")
    canonical = unicodedata.normalize("NFC", email).strip().translate(
        str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))
    try:
        encoded = canonical.encode("utf-8")
    except UnicodeError:
        raise InterfaceObserverError("explicit canonical account email required") from None
    if (len(encoded) > 320 or canonical.count("@") != 1
            or any(char.isspace() or unicodedata.category(char).startswith("C") for char in canonical)
            or not all(canonical.split("@"))):
        raise InterfaceObserverError("explicit canonical account email required")
    domains = {"interface-email-v1": b"agent-braid-interface-email-v1\0",
               "claude-account-email-v1": b"agent-braid-m45-account-email-v1\0"}
    return hmac.new(private_key, domains[method] + encoded,
                    hashlib.sha256).hexdigest()


def key_fingerprint(private_key: bytes, *, method: str = "interface-email-v1") -> str:
    _key(private_key)
    if type(method) is not str:
        raise InterfaceObserverError("unsupported native email binding method")
    if method == "claude-account-email-v1":
        original = hmac.new(private_key, b"agent-braid-m45-key-fingerprint-v1", hashlib.sha256).hexdigest()[:16]
        return hashlib.sha256(original.encode("ascii")).hexdigest()
    if method != "interface-email-v1":
        raise InterfaceObserverError("unsupported native email binding method")
    return hashlib.sha256(b"agent-braid-interface-key-v1\0" + private_key).hexdigest()


def _utc(value):
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise InterfaceObserverError("timezone-aware original observation time required")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class NativeProfileWitness:
    """Private profile projection; authenticity requires the installed verifier."""

    account_sha256: str
    account_namespace_sha256: str
    email_binding_sha256: str
    key_fingerprint_sha256: str
    observed_at: datetime
    profile_receipt_sha256: str
    email_binding_method: str = "interface-email-v1"


@dataclass(frozen=True)
class InterfaceSourcePin:
    source_ref: str
    source_sha256: str
    verifier_ref: str
    verifier_sha256: str

    def as_dict(self):
        return {"sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
                "verifierRef": self.verifier_ref, "verifierSha256": self.verifier_sha256}


@dataclass(frozen=True)
class BrowserInterfaceRead:
    """Ephemeral real-reader output; email and trace must never be persisted.

    The verifier must establish that the authoritative current account and
    control were observed in the same authenticated browser session. The
    session digest identifies that witness; it is not authentication by itself.
    """

    account_email: str = field(repr=False)
    auto_recharge_enabled: bool | None
    observed_at: datetime
    session_binding_sha256: str
    trace: bytes = field(repr=False)
    origin: str


class BrowserProvenanceVerifier(Protocol):
    """Authenticate browser/profile procedures, review and account correspondence."""

    def verify_browser_read(self, observed: BrowserInterfaceRead, profile: NativeProfileWitness,
                            binding: OperationalProcessRouteBinding, pin: InterfaceSourcePin,
                            review_sha256: str,
                            organization_declaration_sha256: str | None) -> None: ...


@dataclass(frozen=True)
class InterfaceObservation:
    """Sanitized verified read; not launch authority or independent cash evidence."""

    binding: OperationalProcessRouteBinding = field(repr=False)
    pin: InterfaceSourcePin
    review_sha256: str
    auto_recharge_enabled: bool
    observed_at: datetime
    valid_until: datetime
    native_profile: NativeProfileWitness
    session_binding_sha256: str
    private_trace_sha256: str
    organization_declaration_sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVATION_SCHEMA, "binding": self.binding.as_dict(),
                **self.pin.as_dict(), "reviewSha256": self.review_sha256,
                "autoRechargeEnabled": self.auto_recharge_enabled,
                "uiObservedAt": self.observed_at.isoformat(), "validUntil": self.valid_until.isoformat(),
                "profileObservedAt": self.native_profile.observed_at.isoformat(),
                "profileReceiptSha256": self.native_profile.profile_receipt_sha256,
                "emailBindingMethod": self.native_profile.email_binding_method,
                "emailBindingSha256": self.native_profile.email_binding_sha256,
                "keyFingerprintSha256": self.native_profile.key_fingerprint_sha256,
                "sessionBindingSha256": self.session_binding_sha256,
                "privateTraceSha256": self.private_trace_sha256,
                "organizationDeclarationSha256": self.organization_declaration_sha256}

    def as_auto_recharge_payload(self) -> dict[str, Any]:
        if self.binding.host == "codex":
            return {"autoRechargeEnabled": self.auto_recharge_enabled}
        digest = hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"),
                                           ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        return {"autoRechargeEnabled": self.auto_recharge_enabled, "basis": "interface-observation",
                "accountBound": True, "organizationBinding": ORGANIZATION_BINDING,
                "uiObservedAt": self.observed_at.isoformat(),
                "profileObservedAt": self.native_profile.observed_at.isoformat(),
                "collectorReceiptSha256": self.native_profile.profile_receipt_sha256,
                "recorderRecordSha256": digest}


class InterfaceObserver:
    """Explicit one-shot acquisition; no browser writes or permissive defaults.

    Run this acquisition under SourceProducer's shared serialization lock when
    composing native sources. The consumer receives only sanitized output.
    """

    def __init__(self, binding: OperationalProcessRouteBinding, native_profile: NativeProfileWitness,
                 source_pin: InterfaceSourcePin, *, private_hmac_key: bytes, review_sha256: str,
                 browser_reader: Callable[[threading.Event], BrowserInterfaceRead],
                 provenance_verifier: BrowserProvenanceVerifier,
                 organization_declaration_sha256: str | None = None,
                 max_age_seconds: float = 60, timeout_seconds: float = 30,
                 utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        try:
            if (not isinstance(binding, OperationalProcessRouteBinding)
                    or operational_binding_from_dict(binding.as_dict()) != binding
                    or not isinstance(native_profile, NativeProfileWitness)
                    or not isinstance(source_pin, InterfaceSourcePin)
                    or not callable(browser_reader) or not callable(provenance_verifier.verify_browser_read)
                    or not callable(utc_now)):
                raise ValueError("explicit procedures")
            _key(private_hmac_key)
            if native_profile.email_binding_method not in {"interface-email-v1", "claude-account-email-v1"}:
                raise ValueError("email method")
            if native_profile.email_binding_method == "claude-account-email-v1" and binding.host != "claude-code":
                raise ValueError("archived method host")
            for digest in (review_sha256, source_pin.source_sha256, source_pin.verifier_sha256,
                           native_profile.account_sha256, native_profile.account_namespace_sha256,
                           native_profile.email_binding_sha256, native_profile.key_fingerprint_sha256,
                           native_profile.profile_receipt_sha256):
                _hash(digest)
            if any(not isinstance(ref, str) or not ref.strip() for ref in (
                    source_pin.source_ref, source_pin.verifier_ref)):
                raise ValueError("reference")
            ceiling = 60 if binding.host == "codex" else 900
            if (type(max_age_seconds) not in (int, float) or not math.isfinite(max_age_seconds)
                    or not 0 < max_age_seconds <= ceiling
                    or type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                    or not 0 < timeout_seconds <= 60):
                raise ValueError("age or deadline")
            if binding.host == "claude-code":
                _hash(organization_declaration_sha256)
            elif organization_declaration_sha256 is not None:
                raise ValueError("organization scope")
        except Exception:
            raise InterfaceObserverError("frozen binding, profile, pins and trusted browser procedures required") from None
        self._binding = operational_binding_from_dict(binding.as_dict())
        self._profile = NativeProfileWitness(native_profile.account_sha256, native_profile.account_namespace_sha256,
            native_profile.email_binding_sha256, native_profile.key_fingerprint_sha256,
            _utc(native_profile.observed_at), native_profile.profile_receipt_sha256,
            native_profile.email_binding_method)
        self._pin = InterfaceSourcePin(source_pin.source_ref, source_pin.source_sha256,
                                        source_pin.verifier_ref, source_pin.verifier_sha256)
        self._key, self._review, self._organization = private_hmac_key, review_sha256, organization_declaration_sha256
        self._reader, self._verifier, self._now = browser_reader, provenance_verifier, utc_now
        self._max_age, self._timeout = max_age_seconds, timeout_seconds
        self._cancel, self._done = threading.Event(), threading.Event()
        self._state = threading.Lock()
        self._used = False
        self._thread: threading.Thread | None = None

    def _check_read(self, raw, current):
        current = _utc(current)
        if (not isinstance(raw, BrowserInterfaceRead) or type(raw.auto_recharge_enabled) is not bool
                or raw.auto_recharge_enabled is not False or raw.origin != _ORIGINS[self._binding.host]
                or type(raw.trace) is not bytes or not 0 < len(raw.trace) <= MAX_TRACE_BYTES):
            raise InterfaceObserverError("unknown, unsafe or unbound interface source")
        _hash(raw.session_binding_sha256)
        observed, profile_time = _utc(raw.observed_at), _utc(self._profile.observed_at)
        skew = 60 if self._binding.host == "codex" else 600
        if (not 0 <= (current - observed).total_seconds() <= self._max_age
                or profile_time > current or abs((observed - profile_time).total_seconds()) > skew):
            raise InterfaceObserverError("interface or native-profile time is stale, future or unbound")
        if (self._profile.account_sha256 != self._binding.account_sha256
                or self._profile.account_namespace_sha256 != self._binding.account_namespace_sha256
                or not hmac.compare_digest(self._profile.key_fingerprint_sha256,
                                           key_fingerprint(self._key, method=self._profile.email_binding_method))
                or not hmac.compare_digest(self._profile.email_binding_sha256,
                                           private_email_binding(raw.account_email, self._key,
                                                                 method=self._profile.email_binding_method))):
            raise InterfaceObserverError("browser and native-profile private account binding differs")
        return observed

    def capture(self, *, cancel_event: threading.Event | None = None) -> InterfaceObservation:
        with self._state:
            if self._used or self._cancel.is_set() or (cancel_event is not None and cancel_event.is_set()):
                raise InterfaceObserverError("interface capture already used or cancelled; no retry")
            self._used = True
        result = []
        def invoke():
            try:
                began = _utc(self._now())
                if self._cancel.is_set():
                    return
                raw = self._reader(self._cancel)
                if not isinstance(raw, BrowserInterfaceRead):
                    raise InterfaceObserverError("typed browser reader output required")
                # Own the exact immutable values before provenance validation;
                # do not retain a caller-owned object that may later be changed.
                raw = BrowserInterfaceRead(raw.account_email, raw.auto_recharge_enabled,
                    _utc(raw.observed_at), raw.session_binding_sha256, raw.trace, raw.origin)
                current = _utc(self._now())
                self._check_read(raw, current)
                if self._cancel.is_set():
                    return
                if self._verifier.verify_browser_read(raw, self._profile, self._binding, self._pin,
                        self._review, self._organization) is not None:
                    raise InterfaceObserverError("browser provenance verifier did not accept")
                completed = _utc(self._now())
                if completed < max(began, current):
                    raise InterfaceObserverError("interface acquisition clock moved backwards")
                observed = self._check_read(raw, completed)
                if not self._cancel.is_set():
                    result.append(InterfaceObservation(self._binding, self._pin, self._review, False,
                        observed, observed + timedelta(seconds=self._max_age), self._profile,
                        raw.session_binding_sha256, hashlib.sha256(raw.trace).hexdigest(), self._organization))
            except BaseException:
                pass
            finally:
                self._done.set()
        try:
            deadline = time.monotonic() + self._timeout
            self._thread = threading.Thread(target=invoke, name="agent-braid-interface-observer", daemon=True)
            self._thread.start()
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    raise InterfaceObserverError("interface acquisition cancelled")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise InterfaceObserverError("interface acquisition deadline exceeded")
                if self._done.wait(min(.05, remaining)):
                    break
            if cancel_event is not None and cancel_event.is_set():
                raise InterfaceObserverError("interface acquisition cancelled at completion")
            if self._cancel.is_set() or len(result) != 1:
                raise InterfaceObserverError("interface acquisition or authentication failed")
            observation = result[0]
            if self._cancel.is_set() or (cancel_event is not None and cancel_event.is_set()):
                raise InterfaceObserverError("interface acquisition cancelled before return")
            return observation
        except BaseException as exc:
            self._cancel.set()
            if self._thread is None or self._thread.ident is None:
                self._done.set()
            if not isinstance(exc, Exception):
                raise
            raise InterfaceObserverError("read-only interface acquisition refused; no retry or fallback") from None

    def stop(self) -> None:
        self._cancel.set()

    def drain(self, *, timeout_seconds: float = 1) -> bool:
        if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 <= timeout_seconds <= 60):
            raise InterfaceObserverError("bounded interface drain deadline required")
        return self._thread is None or self._done.wait(timeout_seconds)
