# SPDX-License-Identifier: AGPL-3.0-only
"""Verified, revision-preserving accounting; no provider or invoice access.

One receipt covers one complete outer activity, not an additive phase. The
trusted caller verifies source authenticity and the declared observation scope.
Hashes bind bytes; they are not invoice authentication or execution permission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import threading
from types import MappingProxyType
from typing import Mapping, Protocol

from .tooling_capture import MeasuredCosts
from .tooling_evaluation import COST_FIELDS

MAX_RECEIPTS = 2048
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}\Z")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ACTUAL = {"invoice", "provider-meter"}
_BASES = _ACTUAL | {"estimate", "reference", "unavailable"}
_TOKENS = {"tokens", "input_tokens", "output_tokens", "retry_tokens"}
_PEAKS = {"rss_bytes", "disk_bytes"}


class CostAccountingError(ValueError):
    """The accounting source or its coverage is insufficient."""


def _identifier(value: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise CostAccountingError("invalid bounded source/activity identifier")


def _timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.utcoffset() != timezone.utc.utcoffset(result):
            raise ValueError
        return result
    except (AttributeError, TypeError, ValueError) as exc:
        raise CostAccountingError("an explicit UTC timestamp is required") from exc


@dataclass(frozen=True)
class CostReceipt:
    """Cumulative outer-activity costs, including gaps and human review time.

Primary input/output totals exclude retry tokens. Disk is the cumulative
cohort retained-byte high water, RSS the activity process-set high water.
Completeness and process-set coverage require external verification.
"""

    activity_id: str
    revision: int
    source_ref: str
    source_sha256: str
    started_at: str
    ended_at: str
    observed_at: str
    monetary_basis: str
    values: Mapping[str, int | float | None]

    def __post_init__(self) -> None:
        for value in (self.activity_id, self.source_ref):
            _identifier(value)
        if (isinstance(self.revision, bool) or not isinstance(self.revision, int)
                or not 1 <= self.revision <= MAX_RECEIPTS):
            raise CostAccountingError("invalid receipt revision")
        if not isinstance(self.source_sha256, str) or not _DIGEST.fullmatch(self.source_sha256):
            raise CostAccountingError("source SHA-256 is required")
        if not (_timestamp(self.started_at) <= _timestamp(self.ended_at) <= _timestamp(self.observed_at)):
            raise CostAccountingError("activity boundaries and observation are out of order")
        if self.monetary_basis not in _BASES:
            raise CostAccountingError("unknown monetary basis")
        if not isinstance(self.values, Mapping) or set(self.values) != set(COST_FIELDS):
            raise CostAccountingError("every cost field must be explicit")
        values = dict(self.values)
        for field, value in values.items():
            if value is None:
                continue
            try:
                valid = math.isfinite(value) and value >= 0
            except (TypeError, OverflowError):
                valid = False
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not valid or (field in _TOKENS and not isinstance(value, int))):
                raise CostAccountingError("costs must be finite nonnegative numbers; tokens are integers")
        token_values = [values[field] for field in _TOKENS]
        if all(value is not None for value in token_values):
            if values["tokens"] != sum(values[field] for field in _TOKENS - {"tokens"}):
                raise CostAccountingError("input, output and retry tokens must equal total tokens")
        if self.monetary_basis == "unavailable" and values["eur"] is not None:
            raise CostAccountingError("unavailable billing cannot carry an EUR value")
        object.__setattr__(self, "values", MappingProxyType(values))

    def subject(self) -> dict[str, object]:
        return {
            "schemaVersion": "agent-braid-m45-cost-receipt-v1",
            "activityId": self.activity_id, "revision": self.revision,
            "sourceRef": self.source_ref, "sourceSha256": self.source_sha256,
            "startedAt": self.started_at, "endedAt": self.ended_at, "observedAt": self.observed_at,
            "monetaryBasis": self.monetary_basis, "values": dict(self.values),
            "scope": "outer-activity;rss-process-set-peak;disk-cohort-retained-high-water",
        }

    @property
    def sha256(self) -> str:
        encoded = json.dumps(self.subject(), sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CostAttestation:
    verifier_id: str
    subject_sha256: str
    verified_at: str


class CostVerifier(Protocol):
    """Authenticate actual sources, complete coverage, and monetary basis."""

    def verify(self, receipt: CostReceipt) -> CostAttestation: ...


class CostBook:
    """Count latest verified activity revisions once, retaining all history.

The frozen roster includes setup, every attempt and separately accounted human
work if outside attempt intervals. Future activities stay missing, never zero.
Intervals of distinct activities must be disjoint to avoid wall double counting.
This is reconciliation software, not a durable ledger or live billing service.
"""

    def __init__(self, activity_ids: tuple[str, ...], *, verifier: CostVerifier):
        if (not isinstance(activity_ids, tuple) or not activity_ids
                or len(activity_ids) > MAX_RECEIPTS or len(set(activity_ids)) != len(activity_ids)):
            raise CostAccountingError("a bounded unique frozen activity roster is required")
        for identifier in activity_ids:
            _identifier(identifier)
        if not callable(getattr(verifier, "verify", None)):
            raise CostAccountingError("an external cost verifier is required")
        self._roster = activity_ids
        self._verifier = verifier
        self._history: list[tuple[CostReceipt, CostAttestation]] = []
        self._latest: dict[str, CostReceipt] = {}
        self._lock = threading.RLock()
        self._verifying = False

    @property
    def history(self) -> tuple[tuple[CostReceipt, CostAttestation], ...]:
        with self._lock:
            return tuple(self._history)

    def add(self, receipt: CostReceipt) -> None:
        with self._lock:
            if self._verifying:
                raise CostAccountingError("cost verification cannot reenter receipt publication")
            self._add(receipt)

    def _add(self, receipt: CostReceipt) -> None:
        if not isinstance(receipt, CostReceipt) or receipt.activity_id not in self._roster:
            raise CostAccountingError("receipt activity is outside the frozen roster")
        if len(self._history) >= MAX_RECEIPTS:
            raise CostAccountingError("receipt inventory limit exceeded")
        prior = self._latest.get(receipt.activity_id)
        if receipt.revision != (prior.revision + 1 if prior else 1):
            raise CostAccountingError("revisions must be consecutive and counted once")
        if prior:
            if (receipt.started_at != prior.started_at
                    or _timestamp(receipt.ended_at) < _timestamp(prior.ended_at)
                    or _timestamp(receipt.observed_at) < _timestamp(prior.observed_at)):
                raise CostAccountingError("revision changed the activity boundary or regressed time")
            for field in COST_FIELDS:
                old, new = prior.values[field], receipt.values[field]
                if field == "eur" and prior.monetary_basis not in _ACTUAL:
                    continue
                if old is not None and (new is None or new < old):
                    raise CostAccountingError("verified cumulative costs cannot decrease or become unknown")
            if prior.monetary_basis in _ACTUAL and receipt.monetary_basis not in _ACTUAL:
                raise CostAccountingError("actual billing cannot be replaced by an estimate")
        for old, _ in self._history:
            if old.activity_id != receipt.activity_id and (
                    old.source_ref == receipt.source_ref or old.source_sha256 == receipt.source_sha256):
                raise CostAccountingError("one physical source cannot be counted in two activities")
        for activity, old in self._latest.items():
            if activity != receipt.activity_id and (
                    _timestamp(receipt.started_at) < _timestamp(old.ended_at)
                    and _timestamp(old.started_at) < _timestamp(receipt.ended_at)):
                raise CostAccountingError("outer activity intervals overlap")
        self._verifying = True
        try:
            attestation = self._verifier.verify(receipt)
        finally:
            self._verifying = False
        if not isinstance(attestation, CostAttestation) or attestation.subject_sha256 != receipt.sha256:
            raise CostAccountingError("external verification did not bind the exact receipt")
        _identifier(attestation.verifier_id)
        if _timestamp(attestation.verified_at) < _timestamp(receipt.observed_at):
            raise CostAccountingError("verification predates observation")
        self._history.append((receipt, attestation))
        self._latest[receipt.activity_id] = receipt

    def snapshot(self, *, source_ref: str) -> MeasuredCosts:
        """Return a conservative full-roster view; missing fields stay unknown.

Observation time is the oldest source time. Taking a snapshot does not refresh
old telemetry. Live supervision needs a separately verified fresh cumulative
source; this view is insufficient when sources are stale or the roster is open.
"""
        with self._lock:
            return self._snapshot(source_ref=source_ref)

    def _snapshot(self, *, source_ref: str) -> MeasuredCosts:
        _identifier(source_ref)
        totals: dict[str, int | float | None] = {}
        for field in COST_FIELDS:
            observations = []
            for activity in self._roster:
                receipt = self._latest.get(activity)
                value = receipt.values[field] if receipt else None
                if field == "eur" and receipt and receipt.monetary_basis not in _ACTUAL:
                    value = None
                observations.append(value)
            if any(value is None for value in observations):
                totals[field] = None
            else:
                totals[field] = max(observations) if field in _PEAKS else sum(observations)
                try:
                    finite = math.isfinite(totals[field])
                except OverflowError:
                    finite = False
                if not finite:
                    raise CostAccountingError("aggregate cost overflow")
        if not self._latest:
            raise CostAccountingError("no verified source observation exists")
        subject = {"roster": self._roster, "history": [receipt.sha256 for receipt, _ in self._history],
                   "values": totals}
        digest = hashlib.sha256(json.dumps(subject, sort_keys=True, separators=(",", ":"),
                                          allow_nan=False).encode("utf-8")).hexdigest()
        oldest = min(self._latest.values(), key=lambda receipt: _timestamp(receipt.observed_at))
        return MeasuredCosts(MappingProxyType(totals), source_ref, digest, oldest.observed_at)
