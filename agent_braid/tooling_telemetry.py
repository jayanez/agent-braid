# SPDX-License-Identifier: AGPL-3.0-only
"""Default-off local numeric aggregates (SPEC-046); no network or event records."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import asyncio
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import threading
import time
import uuid

SCHEMA = 'agent-braid-local-telemetry-batch/v1'
APPLICATION_ID = 0x41425431  # ABT1, local aggregate database format v1
MAX_BYTES = 10 * 1024 * 1024
MAX_DATABASE_BYTES = 4 * 1024 * 1024
MAX_BATCH_BYTES = 1024 * 1024
MAX_ROWS = 4096
MAX_BATCHES = 2048
MAX_COUNT = 10**12
# Fail-closed waits: a busy store refuses the observation instead of delaying the caller.
LOCK_WAIT_SECONDS = 0.25
SQLITE_TIMEOUT_SECONDS = 0.25
CATEGORIES = ('independent-candidate', 'ordered', 'conflicting', 'unknown')
OPERATIONS = {
    'cli': ('analyze', 'analyze-git'),
    'mcp': ('analyze-work', 'analyze', 'prepare', 'status', 'execute', 'recover', 'verify', 'other'),
}
OUTCOMES = ('ok', 'refused', 'error', 'cancelled', 'unknown')
BUCKETS = {
    'calls': ('all',),
    'duration': ('le-1ms', 'le-10ms', 'le-100ms', 'le-1000ms', 'le-10000ms', 'gt-10000ms'),
    'classification': CATEGORIES,
    'missing-summary': ('unavailable',),
}
LIMITS = [
    'Daily aggregates only; no content, identity, event order or exact durations.',
    'Coverage: portable MCP tool invocations and CLI analyze/analyze-git only; discovery, resources, prompts, legacy MCP and internal calls excluded.',
    'Process death before finalization and collector losses in other/terminated processes are unknown.',
    'Known collector failures are in-memory in this process only; reports from a later CLI cannot recover them.',
    'Thirty UTC dates retained on access; inactive files are not maintained by a daemon.',
    'Manual exports/backups are user-managed; purge resets deduplication and cannot revoke copies.',
    'Imported rows are never re-exported; local exports contain disjoint deltas, not report snapshots.',
    'Expired pending exports are discarded whole; their discarded call count is known but prior delivery may be unknown.',
    'Aggregates do not guarantee anonymity or satisfy experimental, native-host or human acceptance gates.',
]
_known_failures = 0
_failure_lock = threading.Lock()


def _note_failure():
    global _known_failures
    with _failure_lock:
        _known_failures = min(MAX_COUNT, _known_failures + 1)


def today() -> date:
    return datetime.now(timezone.utc).date()


def default_directory() -> Path:
    """Fixed user-local location, independent of repository and host configuration."""
    return Path.home() / '.local' / 'share' / 'agent-braid' / 'telemetry'


def _require(condition, message='invalid local telemetry data'):
    if not condition:
        raise ValueError(message)


def _number(value):
    return type(value) is int and 0 < value <= MAX_COUNT


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def _path(path: Path, *, directory=False):
    path = Path(path).expanduser().absolute()
    _require(path == path.resolve(strict=False), 'telemetry paths must be canonical')
    for part in (path, *path.parents):
        _require(not part.is_symlink(), 'telemetry symlinks are refused')
        bare = (part / 'HEAD').is_file() and (part / 'objects').is_dir() and (part / 'refs').is_dir()
        _require(not (part / '.git').exists() and not bare, 'telemetry must be outside repositories')
    if path.exists():
        info = path.stat()
        _require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'unsafe telemetry destination')
        if hasattr(os, 'getuid'):
            _require(info.st_uid == os.getuid(), 'telemetry destination is not owned')
        _require(not info.st_mode & 0o077, 'telemetry destination must be private')
        if not directory:
            _require(info.st_nlink == 1, 'telemetry hardlinks are refused')
    return path


def _cell(row):
    _require(type(row) is dict and set(row) == {'day', 'surface', 'operation', 'outcome', 'metric', 'bucket', 'count'})
    day = row['day']
    _require(type(day) is str)
    try:
        parsed = date.fromisoformat(day)
    except (ValueError, TypeError):
        raise ValueError('invalid telemetry date') from None
    _require(parsed.isoformat() == day and today() - timedelta(days=29) <= parsed <= today(), 'expired or future telemetry date')
    surface, operation, outcome, metric, bucket = (row[k] for k in ('surface', 'operation', 'outcome', 'metric', 'bucket'))
    _require(all(type(v) is str for v in (surface, operation, outcome, metric, bucket)))
    _require(surface in OPERATIONS and operation in OPERATIONS[surface] and outcome in OUTCOMES)
    _require(metric in BUCKETS and bucket in BUCKETS[metric] and _number(row['count']))
    _require(metric not in {'classification', 'missing-summary'} or operation in {'analyze', 'analyze-git', 'analyze-work'})
    return tuple(row[k] for k in ('day', 'surface', 'operation', 'outcome', 'metric', 'bucket', 'count'))


@contextmanager
def _batch_file(path, *, private=False):
    """Validate the opened file itself; avoid final symlink/FIFO replacement."""
    _require(hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_NONBLOCK'),
             'secure telemetry file opening is unsupported')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(descriptor)
        _require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_BATCH_BYTES,
                 'unsafe telemetry batch file')
        if private:
            _require(not info.st_mode & 0o077 and info.st_nlink == 1,
                     'export destination must be private and unlinked')
            _require(info.st_uid == os.getuid(), 'export destination is not owned')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            yield stream
    finally:
        os.close(descriptor)


def _batch(raw):
    _require(len(raw) <= MAX_BATCH_BYTES, 'telemetry batch exceeds 1 MiB')
    def pairs(items):
        value = {}
        for key, item in items:
            _require(key not in value, 'duplicate telemetry JSON member')
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite telemetry value')))
        _require(type(value) is dict and set(value) == {'schema', 'batchId', 'rows'})
        _require(value['schema'] == SCHEMA and type(value['batchId']) is str)
        identity = uuid.UUID(value['batchId'])
        _require(identity.version == 4 and str(identity) == value['batchId'])
        rows = value['rows']
        _require(type(rows) is list and 0 < len(rows) <= MAX_ROWS)
        cells = [_cell(row) for row in rows]
        _require(len({row[:-1] for row in cells}) == len(cells), 'duplicate telemetry cell')
        _require(sum(row[-1] for row in cells) <= MAX_COUNT * MAX_ROWS, 'telemetry batch count exceeds bound')
    except (TypeError, KeyError, AttributeError, OverflowError, RecursionError, UnicodeError, json.JSONDecodeError):
        raise ValueError('invalid telemetry batch') from None
    return value


class Store:
    """Private POSIX local store; paths are never part of its stored data."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory if directory is not None else default_directory()

    @contextmanager
    def _connect(self, *, create=True):
        # No directory, file or lock is created by absent-store status/report.
        root = _path(self.directory, directory=True)
        if not create and (not root.exists() or not (root / 'metrics.sqlite3').exists()):
            yield None
            return
        _require(hasattr(os, 'O_NOFOLLOW'), 'secure telemetry store opening is unsupported')
        import fcntl  # Optional telemetry fails closed on unsupported platforms.
        import sqlite3  # Keep even a missing stdlib extension out of default-off analysis.
        root.mkdir(parents=True, mode=0o700, exist_ok=True)
        _path(root, directory=True)
        lock_path = _path(root / 'store.lock')
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        db = None
        try:
            _path(lock_path)
            deadline = time.monotonic() + LOCK_WAIT_SECONDS
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ValueError('telemetry store is busy') from None
                    time.sleep(0.001)
            _require(all(p.name in {'store.lock', 'metrics.sqlite3', 'metrics.sqlite3-journal'} for p in root.iterdir()), 'unknown telemetry auxiliary file')
            for p in root.iterdir():
                _path(p)
            _require(sum(p.stat().st_size for p in root.iterdir()) <= MAX_BYTES, 'telemetry store exceeds 10 MiB')
            path = _path(root / 'metrics.sqlite3')
            if not path.exists() and not create:
                yield None
                return
            _require(not path.exists() or path.stat().st_size <= MAX_DATABASE_BYTES, 'telemetry database exceeds bound')
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            fresh = path.stat().st_size == 0
            db = sqlite3.connect(path, timeout=SQLITE_TIMEOUT_SECONDS, isolation_level=None)
            db.execute('PRAGMA trusted_schema=OFF')
            if not fresh:
                application_id = db.execute('PRAGMA application_id').fetchone()[0]
                version = db.execute('PRAGMA user_version').fetchone()[0]
                empty = db.execute('SELECT count(*) FROM sqlite_schema').fetchone()[0] == 0
                fresh = application_id == 0 and version == 0 and empty
                _require(fresh or (application_id == APPLICATION_ID and version == 1),
                         'unsupported telemetry database format')
            db.execute('PRAGMA page_size=4096')
            db.execute('PRAGMA auto_vacuum=FULL')
            _require(db.execute('PRAGMA auto_vacuum').fetchone()[0] == 1, 'unsupported telemetry reclamation mode')
            _require(db.execute('PRAGMA page_size').fetchone()[0] == 4096, 'unsupported telemetry page size')
            pages = MAX_DATABASE_BYTES // 4096
            _require(db.execute(f'PRAGMA max_page_count={pages}').fetchone()[0] <= pages, 'telemetry page limit unavailable')
            db.execute('PRAGMA journal_mode=DELETE')
            db.execute('PRAGMA synchronous=FULL')
            db.execute('PRAGMA secure_delete=ON')
            db.execute('PRAGMA temp_store=MEMORY')
            db.execute('BEGIN IMMEDIATE')
            if fresh:
                db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                db.execute('PRAGMA user_version=1')
            db.execute('CREATE TABLE IF NOT EXISTS cells (kind TEXT, day TEXT, surface TEXT, operation TEXT, outcome TEXT, metric TEXT, bucket TEXT, count INTEGER, PRIMARY KEY(kind,day,surface,operation,outcome,metric,bucket)) WITHOUT ROWID')
            db.execute('CREATE TABLE IF NOT EXISTS batches (id TEXT PRIMARY KEY, digest TEXT, expires TEXT) WITHOUT ROWID')
            db.execute('CREATE TABLE IF NOT EXISTS pending (id INTEGER PRIMARY KEY CHECK(id=1), payload BLOB, expires TEXT, calls INTEGER)')
            db.execute('CREATE TABLE IF NOT EXISTS losses (day TEXT PRIMARY KEY, count INTEGER) WITHOUT ROWID')
            if fresh:
                # Initialization is independent of the first optional measurement.
                # A capacity/write failure must leave a valid empty store.
                db.commit()
                db.execute('BEGIN IMMEDIATE')
            cutoff = (today() - timedelta(days=29)).isoformat()
            db.execute('DELETE FROM cells WHERE day < ? OR day > ?', (cutoff, today().isoformat()))
            db.execute('DELETE FROM batches WHERE expires < ?', (cutoff,))
            db.execute('DELETE FROM losses WHERE day < ?', (cutoff,))
            lost = db.execute('SELECT calls FROM pending WHERE expires < ?', (cutoff,)).fetchone()
            if lost:
                db.execute('INSERT INTO losses VALUES (?,?) ON CONFLICT(day) DO UPDATE SET count=min(?,count+excluded.count)', (today().isoformat(), lost[0], MAX_COUNT))
                db.execute('DELETE FROM pending')
            yield db
            db.commit()
            _require(sum(p.stat().st_size for p in root.iterdir()) <= MAX_BYTES, 'telemetry store exceeds 10 MiB')
        except sqlite3.Error:
            raise ValueError('telemetry database unavailable or capacity exhausted') from None
        finally:
            if db is not None:
                if db.in_transaction:
                    db.rollback()
                db.close()
            os.close(descriptor)

    @staticmethod
    def _add(db, kind, rows):
        for row in rows:
            db.execute('INSERT INTO cells VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(kind,day,surface,operation,outcome,metric,bucket) DO UPDATE SET count=count+excluded.count', (kind, *row))
        _require(db.execute('SELECT count(*) FROM cells WHERE kind=?', (kind,)).fetchone()[0] <= MAX_ROWS, 'telemetry cell limit reached')
        _require(db.execute('SELECT coalesce(max(count),0) FROM cells').fetchone()[0] <= MAX_COUNT, 'telemetry counter limit reached')

    def record(self, surface, operation, outcome, duration_ms, classifications=None):
        _require(type(duration_ms) in (int, float) and math.isfinite(duration_ms) and duration_ms >= 0)
        _require(classifications is None or type(classifications) is dict)
        if classifications is not None:
            _require(set(classifications) <= set(CATEGORIES) and all(type(v) is int and 0 <= v <= MAX_COUNT for v in classifications.values()))
        bucket = next((name for limit, name in zip((1,10,100,1000,10000), BUCKETS['duration']) if duration_ms <= limit), 'gt-10000ms')
        prefix = (today().isoformat(), surface, operation, outcome)
        rows = [(*prefix, 'calls', 'all', 1), (*prefix, 'duration', bucket, 1)]
        if operation in {'analyze', 'analyze-git', 'analyze-work'}:
            if classifications is None:
                rows.append((*prefix, 'missing-summary', 'unavailable', 1))
            else:
                rows.extend((*prefix, 'classification', key, value) for key, value in classifications.items() if value)
        # Validate before touching disk, including enums and integer types.
        for row in rows:
            _cell(dict(zip(('day','surface','operation','outcome','metric','bucket','count'), row)))
        with self._connect() as db:
            self._add(db, 'total', rows)
            self._add(db, 'delta', rows)

    def report(self):
        rows = []
        losses = 0
        with self._connect(create=False) as db:
            if db is not None:
                values = db.execute("SELECT day,surface,operation,outcome,metric,bucket,sum(count) FROM cells WHERE kind IN ('total','imported') GROUP BY day,surface,operation,outcome,metric,bucket ORDER BY day,surface,operation,outcome,metric,bucket").fetchall()
                rows = [dict(zip(('day','surface','operation','outcome','metric','bucket','count'), row)) for row in values]
                losses = db.execute('SELECT coalesce(sum(count),0) FROM losses').fetchone()[0]
        return {'schema': 'agent-braid-local-telemetry-report/v1', 'rows': rows,
                'knownCollectorFailuresThisProcess': _known_failures,
                'knownPendingExportCallsDiscarded': losses, 'unobservedLosses': 'unknown',
                'retentionDays': 30, 'maximumStoreBytes': MAX_BYTES, 'limits': list(LIMITS)}

    def status(self):
        report = self.report()
        return {'schema': 'agent-braid-local-telemetry-status/v1', 'defaultMode': 'off',
                'consentScope': 'explicit per command or configured server; status does not enable collection',
                'storePresent': (Path(self.directory) / 'metrics.sqlite3').exists(),
                'aggregateCells': len(report['rows']), 'retentionDays': 30,
                'maximumStoreBytes': MAX_BYTES, 'limits': list(LIMITS)}

    def export(self, destination: Path):
        destination = Path(destination).expanduser().absolute()
        _require(not destination.is_relative_to(Path(self.directory).absolute()), 'export must be outside telemetry store')
        # Check type/ownership and parent before draining the first batch.
        # A failed later file write leaves a recoverable pending batch.
        _path(destination.parent, directory=True)
        _require(hasattr(os, 'O_DIRECTORY'), 'secure telemetry export opening is unsupported')
        with self._connect(create=False) as db:
            if db is None:
                return {'status': 'empty'}
            pending = db.execute('SELECT payload FROM pending').fetchone()
            if pending:
                raw = pending[0]
            else:
                rows = db.execute("SELECT day,surface,operation,outcome,metric,bucket,count FROM cells WHERE kind='delta' ORDER BY day,surface,operation,outcome,metric,bucket").fetchall()
                if not rows:
                    return {'status': 'empty'}
                value = {'schema': SCHEMA, 'batchId': str(uuid.uuid4()), 'rows': [dict(zip(('day','surface','operation','outcome','metric','bucket','count'), row)) for row in rows]}
                raw = _canonical(value)
                _batch(raw)
                _require(db.execute('SELECT count(*) FROM batches').fetchone()[0] < MAX_BATCHES, 'telemetry batch limit reached')
                db.execute('INSERT INTO batches VALUES (?,?,?)', (value['batchId'], hashlib.sha256(raw).hexdigest(), max(row[0] for row in rows)))
                calls = sum(row[-1] for row in rows if row[4] == 'calls')
                db.execute('INSERT INTO pending VALUES (1,?,?,?)', (raw, min(row[0] for row in rows), calls))
                db.execute("DELETE FROM cells WHERE kind='delta'")
            # Commit the outbox before any output write; retries keep its ID.
            db.commit()
            _path(destination)
            if destination.exists():
                with _batch_file(destination, private=True) as stream:
                    existing = stream.read(MAX_BATCH_BYTES + 1)
                    _require(existing == raw, 'export destination already contains different bytes')
                    # A crash can leave complete matching bytes without a completed
                    # file sync. Sync those bytes too before acknowledging delivery.
                    os.fsync(stream.fileno())
            else:
                descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                try:
                    with os.fdopen(descriptor, 'wb', closefd=False) as stream:
                        stream.write(raw)
                        stream.flush()
                        os.fsync(stream.fileno())
                except BaseException:
                    destination.unlink(missing_ok=True)
                    raise
                finally:
                    os.close(descriptor)
            directory_fd = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM pending')
        return {'status': 'exported', 'batchId': json.loads(raw)['batchId']}

    def merge(self, source: Path):
        # Import is explicit; do not require the input to be a private owned file,
        # but refuse a final symlink and validate the opened regular file.
        source = Path(source)
        _require(source.is_file() and not source.is_symlink() and source.stat().st_size <= MAX_BATCH_BYTES, 'unsafe telemetry batch input')
        with _batch_file(source) as stream:
            raw = stream.read(MAX_BATCH_BYTES + 1)
        value = _batch(raw)
        canonical = _canonical(value)
        digest = hashlib.sha256(canonical).hexdigest()
        rows = [_cell(row) for row in value['rows']]
        with self._connect() as db:
            previous = db.execute('SELECT digest FROM batches WHERE id=?', (value['batchId'],)).fetchone()
            if previous:
                _require(previous[0] == digest, 'telemetry batch ID reused with different data')
                return {'status': 'duplicate'}
            _require(db.execute('SELECT count(*) FROM batches').fetchone()[0] < MAX_BATCHES, 'telemetry batch limit reached')
            self._add(db, 'imported', rows)
            db.execute('INSERT INTO batches VALUES (?,?,?)', (value['batchId'], digest, max(row[0] for row in rows)))
        return {'status': 'merged'}

    def purge(self):
        with self._connect(create=False) as db:
            if db is not None:
                for table in ('cells', 'batches', 'pending', 'losses'):
                    db.execute(f'DELETE FROM {table}')
                db.commit()
        return {'status': 'purged', 'externalCopies': 'not-removed', 'deduplication': 'reset'}


class Observation:
    """In-memory measurement; callers pass only the explicitly selected summary."""
    def __init__(self):
        self.outcome = 'error'
        self.classifications = None

    def summary(self, value):
        if type(value) is dict:
            summary = value.get('summary')
            if type(summary) is dict:
                counts = summary.get('classifications')
                if type(counts) is dict:
                    selected = {key: counts[key] for key in CATEGORIES if key in counts}
                    if len(selected) == len(CATEGORIES) and all(type(v) is int and 0 <= v <= MAX_COUNT for v in selected.values()):
                        self.classifications = selected


@contextmanager
def observe(mode, surface, operation, *, directory=None):
    """Optional fail-open wrapper: preserves original return/exception/streams."""
    observation = Observation()
    if mode != 'local':
        yield observation
        return
    try:
        started = time.perf_counter()
    except Exception:
        _note_failure()
        yield observation
        return
    try:
        yield observation
    except BaseException as exc:
        observation.outcome = 'cancelled' if isinstance(exc, (KeyboardInterrupt, SystemExit, asyncio.CancelledError)) else 'error'
        raise
    finally:
        try:
            Store(directory).record(surface, operation, observation.outcome,
                                    (time.perf_counter() - started) * 1000, observation.classifications)
        except Exception:
            _note_failure()
