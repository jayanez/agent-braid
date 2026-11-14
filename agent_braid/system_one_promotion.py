# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 REQ-401 (S1.5e plumbing, T401): the System One promotion registry.

A private, append-only file of owner decisions per decision point. A `go` pins the recorded shadow
evidence digest and the backend manifest digest it was taken on; a `rollback` demotes the decision point
to `off`. Every record carries its own SHA-256 over its canonical form and the digest of the record before
it, so an edited, forged, removed or reordered record is refused and the whole registry then promotes
nothing. Writes are write-temp, fsync, rename: an interrupted write leaves the previous registry intact.
Residual risk: the chain has no external anchor, so a same-user write that drops trailing records (for
example a rollback) still verifies; the file is private to its user like the plugin registry.

The registry only decides whether `advise` is effective; it never grants authority
(`executionAuthorization` stays false, ADR 0034 item 4) and nothing here promotes automatically. The
shipped state is the empty registry, which changes no behaviour. Recording a go is gated on SPEC-066
T303, T402 and T403.
"""
from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType

from . import plugin_registry as registry

SCHEMA = 'agent-braid-s1-promotion/v0.1'
FILENAME = 'system-one-promotion.json'
DECISION_POINTS = ('DP-1',)
DECISIONS = ('go', 'rollback')
MODES = ('off', 'shadow', 'advise')
# Closed vocabulary for why a decision point runs in its active mode.
REASONS = ('configured', 'owner-go', 'no-owner-go', 'rolled-back', 'identity-mismatch',
           'promotion-registry-invalid')
MAX_BYTES = 64 * 1024
MAX_RECORDS = 256
FIELDS = frozenset({'sequence', 'decisionPoint', 'decision', 'evidenceDigest', 'manifestDigest',
                    'decidedOn', 'previousDigest', 'recordDigest'})
_DIGEST = re.compile(r'[0-9a-f]{64}')
_DATE = re.compile(r'\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])')


class PromotionError(ValueError):
    """A promotion record or registry is refused; `code` is a closed bucket, never derived from text."""

    def __init__(self, message: str, code: str = 'promotion-shape'):
        super().__init__(message)
        self.code = code


def path(home: Path | None = None) -> Path:
    return registry.home_path(home) / FILENAME


def _digest(value) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _record_digest(record: dict) -> str:
    return registry._hash(registry._bytes({k: v for k, v in record.items() if k != 'recordDigest'}))


def _check_fields(record: dict) -> None:
    point, decision = record['decisionPoint'], record['decision']
    if point not in DECISION_POINTS or decision not in DECISIONS:
        raise PromotionError('Unknown decision point or decision')
    if not (isinstance(record['decidedOn'], str) and _DATE.fullmatch(record['decidedOn'])):
        raise PromotionError('Decision date must be YYYY-MM-DD')
    try:
        date.fromisoformat(record['decidedOn'])
    except ValueError as exc:
        raise PromotionError('Decision date must be a calendar date') from exc
    pinned = (record['evidenceDigest'], record['manifestDigest'])
    if decision == 'go' and not all(_digest(d) for d in pinned):
        raise PromotionError('A go pins lowercase SHA-256 evidence and manifest digests')
    if decision == 'rollback' and pinned != (None, None):
        raise PromotionError('A rollback pins no evidence or manifest digest')


def _verify(value, *, bounded: bool = True) -> tuple:
    """Shape, then the digest chain; returns read-only records in file order."""
    if not (isinstance(value, dict) and set(value) == {'schema', 'records'} and value['schema'] == SCHEMA
            and isinstance(value['records'], list) and (not bounded or len(value['records']) <= MAX_RECORDS)):
        raise PromotionError('Unknown promotion registry schema')
    previous, records = None, []
    for index, record in enumerate(value['records']):
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise PromotionError('Unknown promotion record shape')
        _check_fields(record)
        if type(record['sequence']) is not int or record['sequence'] != index:
            raise PromotionError('Promotion record out of sequence', code='promotion-tampered')
        if record['previousDigest'] != previous or record['recordDigest'] != _record_digest(record):
            raise PromotionError('Promotion record digest does not verify', code='promotion-tampered')
        previous = record['recordDigest']
        records.append(MappingProxyType(dict(record)))
    return tuple(records)


def _raw(target: Path) -> bytes | None:
    try:
        registry._safe(target.parent, directory=True)
        registry._safe(target, directory=False)
        if not target.exists():
            return None
        registry._private(target, directory=False)
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    except (registry.RegistryError, OSError) as exc:
        raise PromotionError('Promotion registry must be a private regular file', code='promotion-unsafe-path') from exc
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise PromotionError('Promotion registry exceeds its 64 KiB limit')
    return raw


def load(home: Path | None = None) -> tuple:
    """Verified, read-only records; the absent registry is the empty one. Creates nothing."""
    raw = _raw(path(home))
    if raw is None:
        return ()
    try:
        value = json.loads(raw, object_pairs_hook=registry._pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(PromotionError('Nonfinite value')))
    except (registry.RegistryError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise PromotionError('Malformed promotion registry') from exc
    return _verify(value)


def _append(home: Path | None, record: dict) -> MappingProxyType:
    selected = registry.home_path(home)
    try:
        with registry._locked(selected):
            records = load(selected)
            record = dict(record, sequence=len(records),
                          previousDigest=records[-1]['recordDigest'] if records else None)
            record['recordDigest'] = _record_digest(record)
            raw = registry._bytes({'schema': SCHEMA, 'records': [dict(r) for r in records] + [record]})
            # A rollback is never blocked by the size bounds: an oversized registry fails verification on the
            # next load and then promotes nothing, which is the state a rollback asks for.
            go = record['decision'] == 'go'
            _verify(json.loads(raw), bounded=go)
            if go and len(raw) > MAX_BYTES:
                raise PromotionError('Promotion registry would exceed its 64 KiB limit')
            fd, name = tempfile.mkstemp(prefix='.system-one-promotion-', dir=selected)
            temporary = Path(name)
            try:
                with os.fdopen(fd, 'wb') as stream:  # mkstemp creates the file 0600
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, selected / FILENAME)
            except BaseException:
                temporary.unlink(missing_ok=True)
                raise
            directory = os.open(selected, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except registry.RegistryError as exc:
        if exc.code == 'registry-unsafe-path':
            raise PromotionError('Promotion registry home is unsafe', code='promotion-unsafe-path') from exc
        raise PromotionError('Another registry transaction is active; retry', code='promotion-busy') from exc
    return MappingProxyType(record)


def record_go(home: Path | None, decision_point: str, *, evidence_digest: str, manifest_digest: str,
              decided_on: str) -> MappingProxyType:
    """Append an owner go for one decision point. Only an owner decision (SPEC-066 T403) may call this."""
    record = {'decisionPoint': decision_point, 'decision': 'go', 'evidenceDigest': evidence_digest,
              'manifestDigest': manifest_digest, 'decidedOn': decided_on}
    _check_fields(record)
    return _append(home, record)


def rollback(home: Path | None, decision_point: str, *, decided_on: str) -> MappingProxyType:
    """Atomically demote one decision point to `off`; the earlier records stay as they were."""
    record = {'decisionPoint': decision_point, 'decision': 'rollback', 'evidenceDigest': None,
              'manifestDigest': None, 'decidedOn': decided_on}
    _check_fields(record)
    return _append(home, record)


def _point(configured: str, latest, manifest_digest: str) -> dict:
    fallback = 'off' if configured == 'off' else 'shadow'
    if latest is not None and latest['decision'] == 'rollback' and configured != 'off':
        return {'activeMode': 'off', 'reason': 'rolled-back'}
    if configured != 'advise':
        return {'activeMode': configured, 'reason': 'configured'}
    if latest is None:
        return {'activeMode': fallback, 'reason': 'no-owner-go'}
    if latest['manifestDigest'] != manifest_digest:
        return {'activeMode': fallback, 'reason': 'identity-mismatch'}
    return {'activeMode': 'advise', 'reason': 'owner-go'}


def resolve(configured: str, records, manifest_digest: str | None, *, invalid: bool = False) -> dict:
    """Active mode per decision point; the top-level mode is DP-1's, the only decision point so far."""
    if configured not in MODES:
        raise PromotionError('System One mode must be off, shadow or advise')
    points = {}
    for point in DECISION_POINTS:
        if invalid:
            points[point] = {'activeMode': 'off' if configured == 'off' else 'shadow',
                             'reason': 'configured' if configured == 'off' else 'promotion-registry-invalid'}
            continue
        latest = next((r for r in reversed(records) if r['decisionPoint'] == point), None)
        points[point] = _point(configured, latest, manifest_digest)
    first = points[DECISION_POINTS[0]]
    return {'activeMode': first['activeMode'], 'reason': first['reason'], 'decisionPoints': points}


def inspect(home: Path | None, configured: str, manifest_digest: str | None) -> tuple[dict, dict]:
    """Never raises for a bad or unreadable registry: it promotes nothing and is reported invalid."""
    try:
        records, valid = load(home), True
    except (PromotionError, OSError):
        records, valid = (), False
    resolved = resolve(configured, records, manifest_digest, invalid=not valid)
    status = {'present': path(home).exists() or path(home).is_symlink(), 'valid': valid, 'records': len(records),
              'decisionPoints': resolved['decisionPoints'], 'executionAuthorization': False}
    return resolved, status


def status(home: Path | None, configured: str, manifest_digest: str | None) -> dict:
    """Path-free status of the registry as it is now: presence, validity, count and resolution."""
    return inspect(home, configured, manifest_digest)[1]
