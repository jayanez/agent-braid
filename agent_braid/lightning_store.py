# SPDX-License-Identifier: AGPL-3.0-only
# Store role adapted from microsoft/agent-lightning agentlightning/store/base.py and store/memory.py at commit
# 6db3c73dc0af2e50fe80e56873a57c1703f1b2a7 (v0.x) and agentlightning/server/store.py at commit
# bc3a9e80417d731744040df5d37117f9cc48005f (v1.0.3), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: in-memory and Mongo stores replaced by private append-only JSON
# lines per run under an exclusive file lock, with retention and purge; no server, queue or network access.
# See docs/development/THIRD_PARTY.md.
"""Private per-run Braid Lightning store (SPEC-070 REQ-006)."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import re
import shutil
import stat
import time

from . import lightning_config
from . import plugin_registry as registry
from .lightning_resources import Candidate, check_text
from .lightning_schema import AttemptResult, Event, _digest, LightningSchemaError, Rollout, canonical_bytes, loads, parse_record

RUN_SCHEMA = 'braid-lightning-run/v0.1'
KINDS = {'rollout': 'rollouts.jsonl', 'event': 'events.jsonl', 'result': 'results.jsonl',  # result: SPEC-071
         'candidate': 'candidates.jsonl'}  # candidate: SPEC-072
CONTENT_KINDS = ('trace',)  # content-bearing records: SPEC-074 consent gate (REQ-002), redaction on ingest (C2)
MAX_LINE = 64 * 1024
JOURNAL = 'journal.jsonl'  # SPEC-072 REQ-007/REQ-010: seeds, optimizer outputs and attempt-result references
MAX_JOURNAL_LINE = 256 * 1024
_RUN_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')


class StoreError(ValueError):
    def __init__(self, message: str, code: str = 'store-shape'):
        super().__init__(message)
        self.code = code


def runs_root(home: Path | None = None) -> Path:
    return lightning_config.directory(home) / 'runs'


def _private_dir(path: Path) -> None:
    registry._safe(path, directory=True)
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise StoreError('Braid Lightning state must be private to its user', 'store-unsafe-path')


def content_consent(home: Path | None = None) -> str:
    """The stored `traces.contentConsent`; a missing, unreadable or invalid profile reads as `none` (SPEC-074 REQ-002)."""
    try:
        value = lightning_config.load(home)
    except (ValueError, OSError):
        return 'none'
    return 'none' if value is None else value['traces']['contentConsent']


def _run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise StoreError('Run identifiers use 1-64 safe characters', 'store-identifier')
    return run_id


class RunStore:
    """Append-only store for one run: `run.json`, `rollouts.jsonl`, `events.jsonl`."""

    def __init__(self, home: Path | None, run_id: str, *, content_consent: str | None = None):
        """`content_consent` None reads the profile when a content record arrives (fail closed)."""
        if content_consent not in (None, 'none', 'redacted'):
            raise StoreError('Unknown trace content consent', 'store-consent')
        self.home = registry.home_path(home)
        self.run_id = _run_id(run_id)
        self.root = runs_root(self.home) / self.run_id
        self.content_consent = content_consent

    def create(self, *, config_digest: str, now: float | None = None) -> dict:
        for directory in (self.home, self.home / 'lightning', runs_root(self.home)):
            _private_dir(directory)
        registry._safe(self.root, directory=True)
        try:
            self.root.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise StoreError('Run already exists', 'store-exists') from exc
        manifest = {'schema': RUN_SCHEMA, 'runId': self.run_id, 'configDigest': config_digest,
                    'createdAt': time.time() if now is None else now}
        self._write_new(self.root / 'run.json', canonical_bytes(manifest))
        return manifest

    def manifest(self) -> dict:
        path = self.root / 'run.json'
        registry._safe(path, directory=False)
        if not path.exists():
            raise StoreError('Run does not exist', 'store-missing')
        registry._private(path, directory=False)
        value = loads(path.read_bytes())
        if not isinstance(value, dict) or set(value) != {'schema', 'runId', 'configDigest', 'createdAt'} \
                or value['schema'] != RUN_SCHEMA or value['runId'] != self.run_id:
            raise StoreError('Run manifest is malformed', 'store-shape')
        return value

    @staticmethod
    def _write_new(path: Path, raw: bytes) -> None:
        registry._safe(path, directory=False)
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    @contextmanager
    def _locked(self):
        self.manifest()
        path = self.root / 'run.lock'
        registry._safe(path, directory=False)
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError as exc:
            raise StoreError('Another process is writing this run', 'store-busy') from exc
        finally:
            os.close(fd)

    def append(self, kind: str, record) -> None:
        """Append a validated record; content-bearing kinds are refused without consent."""
        if kind in CONTENT_KINDS:
            consent = self.content_consent or content_consent(self.home)
            if consent != 'redacted':
                raise StoreError('Content-bearing traces require trace consent redacted', 'store-consent')
            # C2: content reaches the store only after redaction with a clean post-scan; the redactor is SPEC-074 T004.
            raise StoreError('No redactor is available, so the record cannot be stored', 'redaction-incomplete')
        if kind not in KINDS:
            raise StoreError('Unknown record kind', 'store-kind')
        value = record.to_dict() if isinstance(record, (Rollout, Event, AttemptResult, Candidate)) else record
        try:
            parsed = _parse(kind, value)
        except LightningSchemaError as exc:
            raise StoreError(str(exc), exc.code) from exc
        expected = {'rollout': Rollout, 'event': Event, 'result': AttemptResult, 'candidate': Candidate}[kind]
        if not isinstance(parsed, expected):
            raise StoreError('Record kind does not match its schema', 'store-kind')
        if kind == 'candidate':
            self.candidate_text(parsed.sha256)
        raw = canonical_bytes(parsed.to_dict())
        if len(raw) > MAX_LINE:
            raise StoreError('Record is too large', 'store-shape')
        path = self.root / KINDS[kind]
        with self._locked():
            registry._safe(path, directory=False)
            fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'ab') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())

    def read(self, kind: str) -> list:
        if kind not in KINDS:
            raise StoreError('Unknown record kind', 'store-kind')
        self.manifest()
        path = self.root / KINDS[kind]
        registry._safe(path, directory=False)
        if not path.exists():
            return []
        registry._private(path, directory=False)
        records = []
        for number, line in enumerate(path.read_bytes().splitlines(), 1):
            try:
                records.append(_parse(kind, loads(line)))
            except LightningSchemaError as exc:
                raise StoreError(f'{KINDS[kind]} line {number}: {exc}', exc.code) from exc
        return records

    def write_candidate_text(self, sha256: str, text: str) -> None:
        """Store a candidate body as `candidates/<sha256>.md`; an existing file must hold the same bytes."""
        try:
            raw = check_text(text, sha256).encode('utf-8')
        except LightningSchemaError as exc:
            raise StoreError(str(exc), exc.code) from exc
        directory = self.root / 'candidates'
        with self._locked():
            _private_dir(directory)
            path = directory / f'{sha256}.md'
            registry._safe(path, directory=False)
            if path.exists():
                registry._private(path, directory=False)
                if path.read_bytes() != raw:
                    raise StoreError('Stored candidate text differs from its sha256', 'candidate-hash-mismatch')
                return
            self._write_new(path, raw)

    def candidate_text(self, sha256: str) -> str:
        """Read a candidate body and verify it against its sha256."""
        self.manifest()
        try:
            _digest(sha256, 'candidate sha256')
        except LightningSchemaError as exc:
            raise StoreError(str(exc), exc.code) from exc
        path = self.root / 'candidates' / f'{sha256}.md'
        registry._safe(path, directory=False)
        if not path.exists():
            raise StoreError('Candidate text is not stored', 'candidate-text-missing')
        registry._private(path, directory=False)
        try:
            return check_text(path.read_bytes().decode('utf-8'), sha256)
        except (LightningSchemaError, UnicodeDecodeError) as exc:
            raise StoreError('Stored candidate text does not match its sha256', 'candidate-hash-mismatch') from exc


    def append_journal(self, entry: dict) -> None:
        """Append one algorithm journal entry (start, optimizer call, evaluation or stop); exact keys per kind."""
        try:
            _journal_entry(entry)
        except (LightningSchemaError, TypeError, KeyError) as exc:
            raise StoreError(f'Invalid journal entry: {exc}', 'store-shape') from exc
        raw = canonical_bytes(entry)
        if len(raw) > MAX_JOURNAL_LINE:
            raise StoreError('Journal entry is too large', 'store-shape')
        path = self.root / JOURNAL
        with self._locked():
            registry._safe(path, directory=False)
            fd = os.open(path, os.O_CREAT | os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'ab') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())

    def read_journal(self) -> list[dict]:
        self.manifest()
        path = self.root / JOURNAL
        registry._safe(path, directory=False)
        if not path.exists():
            return []
        registry._private(path, directory=False)
        entries = []
        for number, line in enumerate(path.read_bytes().splitlines(), 1):
            try:
                entries.append(_journal_entry(loads(line)))
            except (LightningSchemaError, TypeError, KeyError) as exc:
                raise StoreError(f'{JOURNAL} line {number}: {exc}', 'store-shape') from exc
        return entries


def _journal_entry(entry):
    if not isinstance(entry, dict):
        raise TypeError('entry must be an object')
    kind = entry.get('kind')
    if kind == 'call':
        if set(entry) != {'kind', 'inputSha256', 'callId', 'output', 'check'} or not isinstance(entry['output'], str):
            raise KeyError('call keys')
        _digest(entry['inputSha256'], 'journal.inputSha256')
        if set(entry['check']) != {'inputSha256', 'passed'} or entry['check']['passed'] is not True:
            raise KeyError('call check')
    elif kind == 'eval':
        if set(entry) != {'kind', 'key', 'results'} or not isinstance(entry['results'], list):
            raise KeyError('eval keys')
        _digest(entry['key'], 'journal.key')
        for ref in entry['results']:
            if not isinstance(ref, list) or len(ref) != 2 or not isinstance(ref[0], str) or not _RUN_ID.fullmatch(ref[0]):
                raise KeyError('eval result reference')
            _digest(ref[1], 'journal.results')
    elif kind == 'start':
        if set(entry) - {'source', 'models'} != {'kind', 'algorithm', 'rngSeed'} or entry['algorithm'] not in ('apo', 'gepa') or \
                not (entry['rngSeed'] is None or type(entry['rngSeed']) is int):
            raise KeyError('start keys')
        if 'source' in entry:
            source = entry['source']
            if not isinstance(source, dict) or set(source) != {'arm', 'commit', 'workingTree', 'seedSkillSha256'} or \
                    source['arm'] not in ('baseline', 'final') or not isinstance(source['commit'], str) or \
                    not re.fullmatch(r'[0-9a-f]{7,40}', source['commit']) or type(source['workingTree']) is not bool:
                raise KeyError('start source')
            _digest(source['seedSkillSha256'], 'journal.source')
        if 'models' in entry:  # the host model per host, pinned for the whole run (resume and replay check it)
            models = entry['models']
            if not isinstance(models, dict) or not all(isinstance(k, str) and isinstance(v, str) and k and v
                                                       for k, v in models.items()):
                raise KeyError('start models')
    elif kind == 'stop':
        if set(entry) != {'kind', 'reason', 'refusal'}:
            raise KeyError('stop keys')
    else:
        raise KeyError('kind')
    return entry


def _parse(kind: str, value):
    return Candidate.parse(value) if kind == 'candidate' else parse_record(value)


def list_runs(home: Path | None = None) -> list[dict]:
    root = runs_root(home)
    registry._safe(root, directory=True)
    if not root.exists():
        return []
    found = []
    for entry in sorted(root.iterdir()):
        if entry.is_symlink() or not entry.is_dir() or not _RUN_ID.fullmatch(entry.name):
            raise StoreError(f'Unexpected entry in the run store: {entry.name}', 'store-unsafe-path')
        found.append(RunStore(home, entry.name).manifest())
    return found


def purge(home: Path | None, run_id: str) -> dict:
    store = RunStore(home, run_id)
    store.manifest()
    with store._locked():
        shutil.rmtree(store.root)
    return {'status': 'purged', 'runId': run_id}


def sweep(home: Path | None, retention_days: int, *, now: float | None = None) -> dict:
    if type(retention_days) is not int or not 1 <= retention_days <= 90:
        raise StoreError('Retention must be 1-90 days', 'store-range')
    cutoff = (time.time() if now is None else now) - retention_days * 86400
    removed = [run['runId'] for run in list_runs(home) if run['createdAt'] < cutoff]
    for run_id in removed:
        purge(home, run_id)
    return {'status': 'swept', 'removed': removed, 'retentionDays': retention_days}
