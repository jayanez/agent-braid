# SPDX-License-Identifier: AGPL-3.0-only
"""Authenticated source cache and explicitly serialized, bounded acquisition.

The fast consumer performs no acquisition, file I/O or external verification.
No import starts a worker. Source authenticity is an externally installed trust
boundary; synthetic verifiers and self-reported hashes cannot establish it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import threading
from types import MappingProxyType
from typing import Any, Protocol

from . import tooling_claude_sources as claude
from . import tooling_codex_sources as codex
from .tooling_subscription import OperationalProcessRouteBinding, operational_binding_from_dict

MAX_RECORD_BYTES = 128 * 1024
OBSERVATION_SCHEMA = "agent-braid-authenticated-source-observation-v1"
Composition = codex.CodexSourceComposition | claude.ClaudeSourceComposition


class SourceObserverError(ValueError):
    """Redacted source boundary refusal, containing no provider bodies."""


class SourceReceiptVerifier(Protocol):
    """Externally trusted authentication of an exact receipt and frozen pin."""

    def verify_receipt(self, kind: str, receipt: Mapping[str, Any],
                       pin: Mapping[str, Any]) -> None: ...


def _snapshot(value: Any) -> Any:
    try:
        encoded = json.dumps(_thaw(value), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(encoded) > MAX_RECORD_BYTES:
            raise ValueError("size")
        return json.loads(encoded)
    except (TypeError, ValueError, OverflowError, RecursionError):
        raise SourceObserverError("source record must be bounded finite JSON") from None


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    return value


def _utc(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.utcoffset() is None:
        raise SourceObserverError("source check time must be timezone-aware")
    return now.astimezone(timezone.utc)


def _compose(contract, receipts, digest, now) -> Composition:
    try:
        schema = contract.get("schema")
        if schema == codex.CONTRACT_SCHEMA:
            return codex.compose_codex_sources(contract, receipts, expected_contract_sha256=digest, now=now)
        if schema == claude.CONTRACT_SCHEMA:
            return claude.compose_claude_sources(contract, receipts, expected_contract_sha256=digest, now=now)
        raise ValueError("schema")
    except Exception:
        raise SourceObserverError("source contract or receipt composition refused") from None


@dataclass(frozen=True)
class SourceObservation:
    """Checked source claims. Serialization alone never establishes authenticity."""

    composition: Composition
    receipts: Mapping[str, Any]

    def __post_init__(self):
        object.__setattr__(self, "receipts", _freeze(_snapshot(_thaw(self.receipts))))

    def as_dict(self) -> dict[str, Any]:
        return {"schema": OBSERVATION_SCHEMA, "contractSha256": self.composition.contract_sha256,
                "receipts": _thaw(self.receipts)}


@dataclass(frozen=True)
class AuthenticatedSourceObservation(SourceObservation):
    """Cache result authenticated by its configured external verifier.

    The Python type is not a signature or admission capability. An external
    boundary receiving this DTO must still verify provenance independently.
    """


def source_observation_from_dict(value: Mapping[str, Any], contract: Mapping[str, Any], *,
                                 expected_contract_sha256: str, now: datetime) -> SourceObservation:
    """Parse and recompose untrusted serialized claims without promoting trust."""
    value, contract = _snapshot(value), _snapshot(contract)
    if (not isinstance(value, dict) or set(value) != {"schema", "contractSha256", "receipts"}
            or value["schema"] != OBSERVATION_SCHEMA
            or value["contractSha256"] != expected_contract_sha256):
        raise SourceObserverError("invalid serialized source observation")
    result = _compose(contract, value["receipts"], expected_contract_sha256, _utc(now))
    return SourceObservation(result, _freeze(value["receipts"]))


def check_source_observation(observation: SourceObservation, contract: Mapping[str, Any], *,
                             expected_contract_sha256: str, now: datetime,
                             expected_binding: OperationalProcessRouteBinding, phase: str,
                             process_id: int | None = None,
                             process_birth_sha256: str | None = None) -> Composition:
    """Recheck exact originals and lifecycle locally; this does not authenticate."""
    if not isinstance(observation, SourceObservation):
        raise SourceObserverError("typed source observation required")
    result = _compose(_snapshot(contract), _snapshot(_thaw(observation.receipts)),
                      expected_contract_sha256, _utc(now))
    if result != observation.composition or result.binding != expected_binding:
        raise SourceObserverError("source composition or binding drift")
    if (result.phase, result.process_id, result.process_birth_sha256) != (
            phase, process_id, process_birth_sha256):
        raise SourceObserverError("source phase, PID or process birth mismatch")
    return result


class SourceObserverCache:
    """Atomic immutable source snapshots; reads never call a verifier or source.

    Failure removes availability but retains high-water marks, preventing a
    failed refresh from erasing clock, source sequence or lifecycle history.
    """

    def __init__(self, contract: Mapping[str, Any], *, expected_contract_sha256: str,
                 receipt_verifier: SourceReceiptVerifier):
        self._contract = _snapshot(contract)
        try:
            module = {codex.CONTRACT_SCHEMA: codex, claude.CONTRACT_SCHEMA: claude}[self._contract["schema"]]
            if module.source_contract_sha256(self._contract) != expected_contract_sha256:
                raise ValueError("pin")
            self.binding = operational_binding_from_dict(self._contract["binding"])
            if not callable(receipt_verifier.verify_receipt):
                raise ValueError("verifier")
        except Exception:
            raise SourceObserverError("frozen contract and explicit receipt verifier required") from None
        self._digest = expected_contract_sha256
        self._verifier = receipt_verifier
        self._lock = threading.Lock()
        self._value: tuple[dict[str, Any], AuthenticatedSourceObservation] | None = None
        self._prior: tuple[dict[str, Any], Composition] | None = None
        self._last_now: datetime | None = None
        self._generation = 0

    @property
    def contract(self) -> Mapping[str, Any]:
        return _freeze(self._contract)

    def invalidate(self) -> None:
        """Invalidate after timeout, cancellation or unknown acquisition state."""
        with self._lock:
            self._value = None
            self._generation += 1

    def _prepare(self, receipts, now):
        records = _snapshot(receipts)
        _compose(self._contract, records, self._digest, _utc(now))
        for kind in codex.KINDS:
            if self._verifier.verify_receipt(kind, _freeze(records[kind]),
                    _freeze(self._contract["sources"][kind])) is not None:
                raise SourceObserverError("receipt verifier must accept explicitly or raise")
        return records

    def _clock(self, now):
        current = _utc(now)
        if self._last_now is not None and current < self._last_now:
            raise SourceObserverError("source clock moved backwards")
        self._last_now = current
        return current

    def _commit(self, records, now, generation):
        with self._lock:
            if generation != self._generation:
                raise SourceObserverError("source refresh was invalidated")
            current = self._clock(now)
            result = _compose(self._contract, records, self._digest, current)
            if self._prior is not None:
                previous_records, previous = self._prior
                phases = {"prelaunch": 0, "running": 1, "completed": 2}
                if (result.observed_sequence <= previous.observed_sequence
                        or phases[result.phase] < phases[previous.phase]
                        or (previous.process_id is not None and
                            (result.process_id, result.process_birth_sha256) !=
                            (previous.process_id, previous.process_birth_sha256))):
                    raise SourceObserverError("source sequence or process lifecycle regressed")
                for kind in codex.KINDS:
                    if datetime.fromisoformat(records[kind]["observedAt"].replace("Z", "+00:00")) < (
                            datetime.fromisoformat(previous_records[kind]["observedAt"].replace("Z", "+00:00"))):
                        raise SourceObserverError("original source timestamp regressed")
            observation = AuthenticatedSourceObservation(result, _freeze(records))
            self._prior = (records, result)
            self._value = (records, observation)
            self._generation += 1
            return observation

    def publish(self, receipts: Mapping[str, Any], *, now: datetime) -> AuthenticatedSourceObservation:
        """Explicit producer-side authentication; never invoke in a consumer."""
        with self._lock:
            generation = self._generation
        try:
            return self._commit(self._prepare(receipts, now), now, generation)
        except BaseException as exc:
            self.invalidate()
            if not isinstance(exc, Exception):
                raise
            raise SourceObserverError("source authentication or refresh refused") from None

    def read(self, *, now: datetime, expected_binding: OperationalProcessRouteBinding,
             phase: str, process_id: int | None = None,
             process_birth_sha256: str | None = None) -> AuthenticatedSourceObservation:
        """Only bounded local validation; stale or differently bound data refuses."""
        try:
            with self._lock:
                current = self._clock(now)
                value, generation = self._value, self._generation
            if value is None:
                raise SourceObserverError("no authenticated source snapshot")
            records, observation = value
            result = _compose(self._contract, records, self._digest, current)
            if (result.binding != expected_binding or (result.phase, result.process_id,
                    result.process_birth_sha256) != (phase, process_id, process_birth_sha256)):
                raise SourceObserverError("source observation identity mismatch")
            with self._lock:
                if generation != self._generation:
                    raise SourceObserverError("source snapshot was invalidated during read")
            return observation
        except BaseException as exc:
            self.invalidate()
            if not isinstance(exc, Exception):
                raise
            raise SourceObserverError("authenticated source snapshot unavailable") from None


@dataclass(frozen=True)
class ProcedureFiles:
    source: Path
    verifier: Path


def _pinned_file(path: Path, expected_sha256: str, *, private: bool) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022
                    or info.st_size > 1024 * 1024
                    or (private and (info.st_uid != os.getuid() or info.st_mode & 0o077))):
                raise ValueError("private source file")
            data = stream.read(info.st_size + 1)
        if len(data) != info.st_size or hashlib.sha256(data).hexdigest() != expected_sha256:
            raise ValueError("pin")
        return data
    except Exception:
        raise SourceObserverError("private provenance or procedure file refused") from None


class FrozenPrivateReceiptVerifier:
    """Concrete pin/file boundary around a mandatory trusted provenance verifier.

    The bundle digest must come from an independently trusted private capture,
    not from this receipt. Procedure bytes are passed to the installed verifier;
    this module never executes code supplied by a receipt or invents a witness.
    """

    def __init__(self, procedures: Mapping[str, ProcedureFiles], bundle_path: Path, *,
                 expected_bundle_sha256: str, provenance_verifier: Callable[..., bool]):
        if set(procedures) != set(codex.KINDS) or not callable(provenance_verifier):
            raise SourceObserverError("all procedure files and trusted provenance verifier required")
        self._procedures = dict(procedures)
        self._bundle_path = Path(bundle_path)
        self._bundle_sha256 = expected_bundle_sha256
        self._verify = provenance_verifier

    def verify_receipt(self, kind, receipt, pin):
        try:
            files = self._procedures[kind]
            source_bytes = _pinned_file(files.source, pin["sourceSha256"], private=False)
            verifier_bytes = _pinned_file(files.verifier, pin["verifierSha256"], private=False)
            bundle = json.loads(_pinned_file(self._bundle_path, self._bundle_sha256, private=True))
            if self._verify(kind, receipt, pin, source_bytes, verifier_bytes, _freeze(bundle)) is not True:
                raise ValueError("provenance")
        except Exception:
            raise SourceObserverError("independent source provenance verification refused") from None


def _acquisition_lock(path: Path) -> int:
    """Nonblocking process-shared lock. Both host producers must use this path."""
    fd = None
    try:
        import fcntl
        path = Path(path)
        parent = path.parent.stat()
        if (not path.is_absolute() or path.parent.resolve() != path.parent
                or parent.st_uid != os.getuid() or parent.st_mode & 0o077):
            raise ValueError("private canonical directory")
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1):
            raise ValueError("private lock")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except Exception:
        if fd is not None:
            os.close(fd)
        raise SourceObserverError("serialized private acquisition lock unavailable") from None


class SourceProducer:
    """One explicitly requested acquisition, authentication and cache publication.

    On timeout/stop the late result is discarded and the lock stays held until
    the callback exits. The callback must honor cancellation and clean up its
    own native resources; a Python thread cannot forcibly stop external work.
    """

    def __init__(self, cache: SourceObserverCache, acquire: Callable[[threading.Event], Mapping[str, Any]], *,
                 lock_path: Path, timeout_seconds: float,
                 utc_now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        if (not isinstance(cache, SourceObserverCache) or not callable(acquire) or not callable(utc_now)
                or type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 < timeout_seconds <= 120):
            raise SourceObserverError("explicit bounded source producer configuration required")
        self._cache, self._acquire = cache, acquire
        self._path, self._timeout, self._now = Path(lock_path), timeout_seconds, utc_now
        self._cancel = threading.Event()
        self._done = threading.Event()
        self._state = threading.Lock()
        self._used = False
        self._thread: threading.Thread | None = None

    def acquire_once(self) -> AuthenticatedSourceObservation:
        with self._state:
            if self._used or self._cancel.is_set():
                raise SourceObserverError("producer already used or stopped; no automatic retry")
            self._used = True
        result = []
        try:
            with self._cache._lock:
                generation = self._cache._generation
            def invoke():
                fd = None
                try:
                    if self._cancel.is_set():
                        return
                    fd = _acquisition_lock(self._path)
                    if self._cancel.is_set():
                        return
                    records = self._acquire(self._cancel)
                    if self._cancel.is_set():
                        return
                    records = self._cache._prepare(records, self._now())
                    result.append(records)
                except BaseException:
                    pass
                finally:
                    if fd is not None:
                        os.close(fd)
                    self._done.set()
            self._thread = threading.Thread(target=invoke, name="agent-braid-source-producer", daemon=True)
            try:
                self._thread.start()
            except BaseException:
                self._cancel.set()
                if self._thread.ident is None:
                    self._done.set()
                raise
            if not self._done.wait(self._timeout):
                self._cancel.set()
                raise SourceObserverError("source producer exceeded its deadline")
            with self._state:
                if self._cancel.is_set() or len(result) != 1:
                    raise SourceObserverError("source producer failed or was cancelled")
                return self._cache._commit(result[0], self._now(), generation)
        except BaseException as exc:
            self._cancel.set()
            self._cache.invalidate()
            if not isinstance(exc, Exception):
                raise
            raise SourceObserverError("source acquisition refused; no retry or fallback") from None

    def stop(self) -> None:
        """Signal cancellation and immediately remove cached availability."""
        with self._state:
            self._cancel.set()
            self._cache.invalidate()

    def drain(self, *, timeout_seconds: float = 1) -> bool:
        """Bounded cleanup check; false means work and serialization lock remain."""
        if (type(timeout_seconds) not in (int, float) or not math.isfinite(timeout_seconds)
                or not 0 <= timeout_seconds <= 60):
            raise SourceObserverError("drain deadline must be finite and at most 60 seconds")
        return self._thread is None or self._done.wait(timeout_seconds)
