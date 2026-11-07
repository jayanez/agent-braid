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
from .lightning_schema import Event, LightningSchemaError, Rollout, canonical_bytes, loads, parse_record

RUN_SCHEMA = 'braid-lightning-run/v0.1'
KINDS = {'rollout': 'rollouts.jsonl', 'event': 'events.jsonl'}
CONTENT_KINDS = ('trace',)  # content-bearing records; refused until the SPEC-074 consent contract exists
MAX_LINE = 64 * 1024
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


def _run_id(run_id: str) -> str:
    if not isinstance(run_id, str) or not _RUN_ID.fullmatch(run_id):
        raise StoreError('Run identifiers use 1-64 safe characters', 'store-identifier')
    return run_id


class RunStore:
    """Append-only store for one run: `run.json`, `rollouts.jsonl`, `events.jsonl`."""

    def __init__(self, home: Path | None, run_id: str, *, content_consent: str = 'none'):
        if content_consent not in ('none', 'redacted'):
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
            raise StoreError('Content-bearing traces require the SPEC-074 consent contract', 'store-consent')
        if kind not in KINDS:
            raise StoreError('Unknown record kind', 'store-kind')
        value = record.to_dict() if isinstance(record, (Rollout, Event)) else record
        try:
            parsed = parse_record(value)
        except LightningSchemaError as exc:
            raise StoreError(str(exc), exc.code) from exc
        if (kind == 'rollout') != isinstance(parsed, Rollout):
            raise StoreError('Record kind does not match its schema', 'store-kind')
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
                records.append(parse_record(loads(line)))
            except LightningSchemaError as exc:
                raise StoreError(f'{KINDS[kind]} line {number}: {exc}', exc.code) from exc
        return records


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
