# SPDX-License-Identifier: AGPL-3.0-only
"""System One shadow observer (SPEC-066 S1.5a); advisory records, never output.

After a successful System 2 analysis the observer derives one structural episode
(`agent-braid-s1-episode/v0.1`) from the report and appends it to a private local
store. It never changes a result, never raises into its caller, and records only
closed-vocabulary values: no resource names, identifiers, digests of input or text.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

from .tooling_telemetry import _path  # shared canonical, private, no-symlink path rules

SCHEMA = 'agent-braid-s1-episode/v0.1'
REPORT_SCHEMA = 'agent-braid-s1-report/v0.1'
DECISION_POINT = 'DP-1'
# Identity compiled into the shadow module (REQ-007). A different installed backend
# or manifest is refused, so recorded episodes always name the reviewed reference.
EXPECTED_BACKEND_ID = 'stdlib-rule-fixture-v1'
EXPECTED_MANIFEST_DIGEST = '49f9022082fd12eda9ae1e0cd86ff827ca0c41dded4a52c618357cc9e525a3ca'
BUDGET_NANOSECONDS = 50_000_000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_PAIRS = 64
RETENTION_DAYS = 30

OPERATIONS = ('analyze', 'analyze-work')
KINDS = ('aim', 'git')
CLASSIFICATIONS = ('independent-candidate', 'ordered', 'conflicting', 'unknown')
REASON_CODES = ('dependency-order', 'shared-write', 'partial-coverage', 'external-effect',
                'disjoint', 'shared-read-only', 'read-version')
CONSTRAINTS = ('preserve-dependency-order', 'serialize-or-isolate', 'serialize-unless-stronger-evidence',
               'requires-execution-contract-before-parallelism', 'validate-read-versions-at-use')
COVERAGE = ('complete', 'partial', 'unknown')
EFFECT_KINDS = ('read', 'write', 'call', 'transform', 'emit', 'delete', 'deploy', 'unknown')
STATUSES = ('answered', 'abstained', 'refused', 'skipped')
REASONS = ('calibration-absent', 'identity-mismatch', 'budget-exceeded', 'unmapped-reason',
           'store-unavailable', 'internal-error')
CHOICES = ('likely-independent', 'likely-conflicting', 'undetermined')

# Exact, versioned mapping of agent_braid/analysis.py `_interaction` reason sentences
# (rule set exact-resource-footprints-v1). An unmapped sentence is never stored.
REASON_TABLE = {
    'An explicit dependency path orders the operations.': 'dependency-order',
    'At least one exact shared resource has a write-like effect.': 'shared-write',
    'At least one effect footprint is partial or unknown.': 'partial-coverage',
    'External, transforming, destructive, or unknown effects require adapter semantics.': 'external-effect',
    'Complete exact-resource footprints are disjoint.': 'disjoint',
    'Complete exact-resource footprints have no write conflict.': 'shared-read-only',
    'Read-version preconditions remain point-of-use obligations.': 'read-version',
}

_UUID4 = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
_DAY = re.compile(r'^\d{4}-\d{2}-\d{2}$')
_HEX64 = re.compile(r'^[0-9a-f]{64}$')
_IDENT = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')
_FILE = re.compile(r'^episodes-(\d{4}-\d{2}-\d{2})\.jsonl$')
_CLOCK = time.monotonic_ns  # replaced in tests

_refusals = {}
_refusal_lock = threading.Lock()


class StoreRefused(ValueError):
    """The private store declined an episode; the caller is never affected."""


def _note_refusal(reason: str) -> None:
    with _refusal_lock:
        _refusals[reason] = _refusals.get(reason, 0) + 1


def refusal_counts() -> dict:
    """In-memory refusal counts for this process only."""
    with _refusal_lock:
        return dict(_refusals)


def today() -> date:
    return datetime.now(timezone.utc).date()


def default_directory() -> Path:
    """Fixed user-local location, independent of repository and host configuration."""
    return Path.home() / '.local' / 'share' / 'agent-braid' / 'system-one'


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


# --- System One identity and answer ------------------------------------------

def _system_one_answer() -> dict:
    """Identity and strict-policy outcome of the installed reference backend.

    The strict policy ignores the question set, so a request-shaped stand-in carrying
    only its policy identifier obtains the real outcome without building a request.
    """
    from types import SimpleNamespace
    from . import system_one, system_one_policy
    backend_id = system_one.BACKEND_ID
    manifest_digest = system_one.digest(system_one.MODEL_MANIFEST)
    if backend_id != EXPECTED_BACKEND_ID or manifest_digest != EXPECTED_MANIFEST_DIGEST:
        return {'status': 'refused', 'reason': 'identity-mismatch',
                'backendId': backend_id, 'manifestDigest': manifest_digest}
    outcome, reasons = system_one_policy.outcome(
        SimpleNamespace(envelope={'policyId': system_one.STRICT_POLICY}))
    if outcome == 'abstain' and reasons == ['calibration-absent']:
        return {'status': 'abstained', 'reason': 'calibration-absent',
                'backendId': backend_id, 'manifestDigest': manifest_digest}
    return {'status': 'skipped', 'reason': 'internal-error',
            'backendId': backend_id, 'manifestDigest': manifest_digest}


# --- Episode construction -----------------------------------------------------

def _count(value, low, high) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError('report count outside the episode contract')
    return value


def _pair(item: dict) -> dict | None:
    """Closed-vocabulary pair, or None when any sentence or token is not in the tables."""
    codes = set()
    for sentence in item['reasons']:
        code = REASON_TABLE.get(sentence) if type(sentence) is str else None
        if code is None:
            return None
        codes.add(code)
    constraints = item['constraints']
    coverage = item['evidence']['coverage']
    classification = item['classification']
    if (classification not in CLASSIFICATIONS
            or not all(type(c) is str and c in CONSTRAINTS for c in constraints)
            or not all(type(c) is str and c in COVERAGE for c in coverage)):
        return None
    return {'system2': classification,
            'system2Determinate': classification != 'unknown',
            'reasonCodes': sorted(codes),
            'constraints': sorted(set(constraints)),
            'coverage': sorted(set(coverage)),
            'sharedResourceCount': min(len(item['sharedResources']), 4096),
            # The report's operations carry resources and coverage but no effect kinds,
            # so per-side kinds are not derivable from it: recorded as null (contract).
            'effectKinds': None,
            'dependency': 'dependency-order' in codes,
            'observedOutcome': None}


def build_episode(report: dict, operation: str, kind: str, *, clock=None, now=None) -> dict:
    """Derive one contract-conformant episode from a System 2 report (never stores input)."""
    clock = clock or _CLOCK
    started = clock()
    summary = report['summary']
    operation_count = _count(summary['operationCount'], 1, 64)
    pair_count = _count(summary['pairCount'], 0, 2016)
    analyzer = {'version': report['analyzer']['version'], 'ruleSet': report['analyzer']['ruleSet']}
    # Complete per-class counts survive the pair cap, so DP-1 shares cover every pair.
    counts = {name: _count(summary['classifications'][name], 0, 2016) for name in CLASSIFICATIONS}
    if sum(counts.values()) != pair_count:
        raise ValueError('report classifications do not sum to the pair count')
    interactions = report['interactions']
    pairs = []
    mapped = True
    for item in interactions:
        pair = _pair(item)
        if pair is None:
            mapped = False
            break
        pairs.append(pair)
    system_one_started = clock()
    answer = _system_one_answer()
    elapsed_micros = max(0, (clock() - system_one_started) // 1000)
    status, reason = answer['status'], answer['reason']
    if not mapped:
        pairs = []
        status, reason = 'skipped', 'unmapped-reason'
    pairs = pairs[:MAX_PAIRS]
    if clock() - started > BUDGET_NANOSECONDS and status != 'refused':
        status, reason = 'skipped', 'budget-exceeded'
    return {'schemaVersion': SCHEMA,
            'episodeId': str(uuid.uuid4()),
            'day': (now or today()).isoformat(),
            'surface': 'mcp',
            'operation': operation,
            'analysisKind': kind,
            'analyzer': analyzer,
            'operationCount': operation_count,
            'pairCount': pair_count,
            'classificationCounts': counts,
            'pairsRecorded': len(pairs),
            'pairs': pairs,
            'systemOne': {'status': status, 'reason': reason,
                          'backendId': answer['backendId'], 'manifestDigest': answer['manifestDigest'],
                          'decisionPoint': DECISION_POINT, 'answers': None,
                          'elapsedMicros': min(int(elapsed_micros), 50_000)},
            'executionAuthorization': False}


# --- Validation ---------------------------------------------------------------

def _need(condition, message='invalid System One episode'):
    if not condition:
        raise ValueError(message)


def _int(value, low, high) -> bool:
    return type(value) is int and low <= value <= high


def _strings(value, allowed) -> bool:
    return (type(value) is list and all(type(v) is str and v in allowed for v in value)
            and value == sorted(set(value)))


def validate_episode(value) -> dict:
    """Enforce the v0.1 contract, including the never-present rule for free strings."""
    _need(type(value) is dict and set(value) == {
        'schemaVersion', 'episodeId', 'day', 'surface', 'operation', 'analysisKind', 'analyzer',
        'operationCount', 'pairCount', 'classificationCounts', 'pairsRecorded', 'pairs', 'systemOne',
        'executionAuthorization'})
    _need(value['schemaVersion'] == SCHEMA and value['surface'] == 'mcp')
    _need(type(value['episodeId']) is str and _UUID4.fullmatch(value['episodeId']))
    _need(type(value['day']) is str and _DAY.fullmatch(value['day']))
    try:
        _need(date.fromisoformat(value['day']).isoformat() == value['day'])
    except ValueError:
        raise ValueError('invalid System One episode') from None
    _need(type(value['operation']) is str and value['operation'] in OPERATIONS)
    _need(type(value['analysisKind']) is str and value['analysisKind'] in KINDS)
    analyzer = value['analyzer']
    _need(type(analyzer) is dict and set(analyzer) == {'version', 'ruleSet'}
          and all(type(v) is str and _IDENT.fullmatch(v) for v in analyzer.values()))
    _need(_int(value['operationCount'], 1, 64) and _int(value['pairCount'], 0, 2016))
    _need(_int(value['pairsRecorded'], 0, MAX_PAIRS) and value['executionAuthorization'] is False)
    counts = value['classificationCounts']
    _need(type(counts) is dict and set(counts) == set(CLASSIFICATIONS)
          and all(_int(c, 0, 2016) for c in counts.values()) and sum(counts.values()) == value['pairCount'])
    pairs = value['pairs']
    _need(type(pairs) is list and len(pairs) == value['pairsRecorded'] <= value['pairCount'])
    for pair in pairs:
        _need(type(pair) is dict and set(pair) == {
            'system2', 'system2Determinate', 'reasonCodes', 'constraints', 'coverage',
            'sharedResourceCount', 'effectKinds', 'dependency', 'observedOutcome'})
        _need(type(pair['system2']) is str and pair['system2'] in CLASSIFICATIONS)
        _need(type(pair['system2Determinate']) is bool
              and pair['system2Determinate'] == (pair['system2'] != 'unknown'))
        _need(_strings(pair['reasonCodes'], REASON_CODES) and _strings(pair['constraints'], CONSTRAINTS))
        _need(_strings(pair['coverage'], COVERAGE) and _int(pair['sharedResourceCount'], 0, 4096))
        kinds = pair['effectKinds']
        _need(kinds is None or (type(kinds) is dict and set(kinds) == {'left', 'right'}
              and all(_strings(side, EFFECT_KINDS) for side in kinds.values())))
        _need(type(pair['dependency']) is bool and pair['observedOutcome'] is None)
    one = value['systemOne']
    _need(type(one) is dict and set(one) == {
        'status', 'reason', 'backendId', 'manifestDigest', 'decisionPoint', 'answers', 'elapsedMicros'})
    _need(type(one['status']) is str and one['status'] in STATUSES)
    _need(one['reason'] is None or (type(one['reason']) is str and one['reason'] in REASONS))
    _need(type(one['backendId']) is str and _IDENT.fullmatch(one['backendId']))
    _need(type(one['manifestDigest']) is str and _HEX64.fullmatch(one['manifestDigest']))
    _need(one['decisionPoint'] == DECISION_POINT and _int(one['elapsedMicros'], 0, 50_000))
    answers = one['answers']
    if one['status'] == 'answered':
        _need(type(answers) is list and len(answers) == len(pairs))
        for answer in answers:
            _need(type(answer) is dict and set(answer) == {'choice', 'probabilities'}
                  and type(answer['choice']) is str and answer['choice'] in CHOICES)
            probabilities = answer['probabilities']
            _need(type(probabilities) is dict and set(probabilities) == set(CHOICES)
                  and all(type(p) is float and 0.0 <= p <= 1.0 for p in probabilities.values()))
    else:
        _need(answers is None)
    return value


# --- Private store ------------------------------------------------------------

def _store_root(directory: Path | None, *, create: bool) -> Path | None:
    root = _path(directory if directory is not None else default_directory(), directory=True)
    if not root.exists():
        if not create:
            return None
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        _path(root, directory=True)
    return root


def _entries(root: Path) -> list[Path]:
    """Only lock and day files are allowed; anything else makes the store unsafe."""
    files = []
    for entry in sorted(root.iterdir()):
        if entry.name == 'store.lock':
            continue
        _need(_FILE.fullmatch(entry.name), 'unknown System One store file')
        files.append(_path(entry))
    return files


def _retained(name: str, current: date) -> bool:
    try:
        parsed = date.fromisoformat(_FILE.fullmatch(name).group(1))
    except ValueError:
        return False
    return current - timedelta(days=RETENTION_DAYS - 1) <= parsed <= current


def append(episode: dict, directory: Path | None = None, *, current: date | None = None) -> None:
    """Append one validated episode; raise StoreRefused when the store cannot take it safely."""
    current = current or today()
    try:
        validate_episode(episode)
        line = _canonical(episode)
        _need(hasattr(os, 'O_NOFOLLOW'), 'secure store opening is unsupported')
        import fcntl
        root = _store_root(directory, create=True)
        lock_path = _path(root / 'store.lock')
        lock = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            _path(lock_path)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise StoreRefused('busy') from None
            for entry in _entries(root):
                if not _retained(entry.name, current):
                    entry.unlink()
            target = _path(root / f"episodes-{episode['day']}.jsonl")
            size = target.stat().st_size if target.exists() else 0
            if size + len(line) > MAX_FILE_BYTES:
                raise StoreRefused('oversize')
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
            try:
                info = os.fstat(descriptor)
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and not info.st_mode & 0o077
                      and info.st_uid == os.getuid(), 'unsafe System One day file')
                _need(info.st_size + len(line) <= MAX_FILE_BYTES, 'oversize')
                written = os.write(descriptor, line)
                _need(written == len(line), 'short write')
            finally:
                os.close(descriptor)
        finally:
            os.close(lock)
    except StoreRefused:
        raise
    except (OSError, ValueError, ImportError) as exc:
        raise StoreRefused('unavailable') from exc


def observe(operation: str, kind: str, report, *, directory: Path | None = None,
            clock=None, now=None) -> None:
    """Record one episode for a successful analysis; never raises, never alters the report."""
    try:
        episode = build_episode(report, operation, kind, clock=clock, now=now)
        append(episode, directory, current=now)
    except StoreRefused as exc:
        _note_refusal(str(exc))
    except BaseException:
        _note_refusal('internal-error')


def store_present(directory: Path | None = None) -> bool:
    """True when the store holds episode files; reads only, creates nothing."""
    try:
        root = _store_root(directory, create=False)
        return root is not None and any(_FILE.fullmatch(p.name) for p in root.iterdir())
    except (OSError, ValueError):
        return False


# --- Report and purge -----------------------------------------------------------

REPORT_LIMITS = [
    'Counts only; episode bodies are never printed.',
    'DP-1 pairs only; no observed outcome is joined in S1.5a, so no accuracy or utility is measured.',
    'Thirty UTC dates retained on access; inactive files are not maintained by a daemon.',
    'Episodes skipped before storage (refused store, internal errors) are known only in this process.',
]


def _read_file(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        _need(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_FILE_BYTES, 'unsafe System One day file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            return stream.read(MAX_FILE_BYTES + 1)
    finally:
        os.close(descriptor)


def report(directory: Path | None = None, *, current: date | None = None) -> dict:
    """Aggregate retained episodes; reads the store only and creates nothing."""
    current = current or today()
    days = {}
    invalid = 0
    root = _store_root(directory, create=False)
    for entry in (_entries(root) if root is not None else []):
        if not _retained(entry.name, current):
            continue
        day = _FILE.fullmatch(entry.name).group(1)
        for line in _read_file(entry).split(b'\n'):
            if not line:
                continue
            try:
                episode = validate_episode(json.loads(line))
            except (ValueError, RecursionError, UnicodeError):
                invalid += 1
                continue
            bucket = days.setdefault(day, {'day': day, 'episodes': 0, 'operations': {},
                                           'system2': {}, 'systemOne': {}, 'allPairs': {}})
            bucket['episodes'] += 1
            for table, key in ((bucket['operations'], episode['operation']),
                               (bucket['systemOne'], episode['systemOne']['status'])):
                table[key] = table.get(key, 0) + 1
            for pair in episode['pairs']:
                bucket['system2'][pair['system2']] = bucket['system2'].get(pair['system2'], 0) + 1
            for name, count in episode['classificationCounts'].items():
                if count:
                    bucket['allPairs'][name] = bucket['allPairs'].get(name, 0) + count
    totals = {'episodes': 0, 'operations': {}, 'system2': {}, 'systemOne': {}, 'allPairs': {}}
    for bucket in days.values():
        totals['episodes'] += bucket['episodes']
        for name in ('operations', 'system2', 'systemOne', 'allPairs'):
            for key, count in bucket[name].items():
                totals[name][key] = totals[name].get(key, 0) + count
    recorded = sum(totals['system2'].values())
    analysed = sum(totals['allPairs'].values())
    unknown = totals['allPairs'].get('unknown', 0)
    return {'schema': REPORT_SCHEMA,
            'retentionDays': RETENTION_DAYS,
            'days': [days[key] for key in sorted(days)],
            'totals': totals,
            'pairsRecorded': recorded,
            'pairsAnalysed': analysed,
            'unknownPairs': unknown,
            'unknownShare': round(unknown / analysed, 6) if analysed else None,
            'invalidLines': invalid,
            'refusalsThisProcess': refusal_counts(),
            'limits': list(REPORT_LIMITS),
            'executionAuthorization': False}


def render_report(value: dict) -> str:
    lines = [f"System One shadow report ({value['schema']})",
             f"Episodes: {value['totals']['episodes']}  Pairs analysed: {value['pairsAnalysed']}"
             f"  Pairs recorded: {value['pairsRecorded']}",
             'Unknown-pair share (DP-1 opportunity): '
             + ('none recorded' if value['unknownShare'] is None
                else f"{value['unknownShare']:.1%} ({value['unknownPairs']} pairs)")]
    for bucket in value['days']:
        lines.append(f"{bucket['day']}: {bucket['episodes']} episodes; operations {bucket['operations']}; "
                     f"System 2 {bucket['system2']}; System One {bucket['systemOne']}")
    if value['invalidLines']:
        lines.append(f"Invalid lines ignored: {value['invalidLines']}")
    lines.extend(value['limits'])
    return '\n'.join(lines)


def purge(directory: Path | None = None) -> dict:
    """Delete the store's own files and, when empty, its directory."""
    root = _store_root(directory, create=False)
    if root is None:
        return {'status': 'empty', 'externalCopies': 'not-removed'}
    removed = 0
    for entry in sorted(root.iterdir()):
        _need(entry.name == 'store.lock' or _FILE.fullmatch(entry.name), 'unknown System One store file')
        _path(entry).unlink()
        removed += 1
    root.rmdir()
    return {'status': 'purged', 'filesRemoved': removed, 'externalCopies': 'not-removed'}
