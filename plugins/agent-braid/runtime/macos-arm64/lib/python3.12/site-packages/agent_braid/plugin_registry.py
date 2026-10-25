# SPDX-License-Identifier: AGPL-3.0-only
"""Private user workspace registration; discovery never grants access."""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import threading

SCHEMA = 'agent-braid-plugin-registry/v0.2'
LEGACY_SCHEMA = 'agent-braid-plugin-registry/v0.1'
TELEMETRY_MODES = ('off', 'local')
MAX_BYTES = 256 * 1024
MAX_WORKSPACES = 64


class RegistryError(ValueError):
    """An unsafe or stale registration is refused."""


class RegistryStale(RegistryError):
    """The registry changed effectively since this connection snapshotted it."""
    code = 'reconnect-required'


class MigrationRequired(RegistryError):
    """A valid alpha.2 registry must be migrated through a setup preview."""


def home_path(value: Path | None = None) -> Path:
    if value is not None:
        return Path(value).expanduser().absolute()
    configured = os.environ.get('AGENT_BRAID_HOME')
    if configured:
        return Path(configured).expanduser().absolute()
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/AgentBraid'
    return Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share'))) / 'agent-braid'


def _safe(path: Path, *, directory: bool | None = None) -> Path:
    path = path.expanduser().absolute()
    if path.resolve(strict=False) != path:
        raise RegistryError('Use a canonical path without symlinks or traversal')
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RegistryError('Symbolic links are not allowed in owned paths')
    if path.exists() and directory is not None:
        mode = path.stat().st_mode
        expected = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
        if not expected:
            raise RegistryError('Unexpected file type in owned path')
    return path


def _private(path: Path, *, directory: bool) -> None:
    _safe(path, directory=directory)
    info = path.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise RegistryError('Owned plugin state must be private to its user')


def _bytes(value) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()


def _hash(raw: bytes | None) -> str | None:
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def _raw(home: Path) -> bytes | None:
    _safe(home, directory=True)
    if home.exists():
        _private(home, directory=True)
    path = home / 'registry.json'
    _safe(path, directory=False)
    if not path.exists():
        return None
    _private(path, directory=False)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise RegistryError('Registry exceeds its 256 KiB limit')
    return raw


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise RegistryError('Duplicate registry member')
        value[key] = item
    return value


def _workspace(value: dict, home: Path) -> None:
    keys = {'workspaceId', 'sourceRoot', 'resultRoot', 'runtimeEnabled', 'grantStore', 'worktreeRoots'}
    if not isinstance(value, dict) or set(value) != keys:
        raise RegistryError('Unknown workspace shape')
    source = _safe(Path(value['sourceRoot']), directory=True)
    identifier = hashlib.sha256(str(source).encode()).hexdigest()[:32]
    if value['workspaceId'] != identifier:
        raise RegistryError('Workspace identity does not match its canonical source')
    if source == home or source.is_relative_to(home) or home.is_relative_to(source):
        raise RegistryError('Plugin state and source roots must not overlap')
    result = _safe(Path(value['resultRoot']), directory=True)
    if result != home / 'results' / identifier:
        raise RegistryError('Unknown workspace result root')
    if type(value['runtimeEnabled']) is not bool or not isinstance(value['worktreeRoots'], list):
        raise RegistryError('Unknown workspace capability configuration')
    if len(value['worktreeRoots']) > MAX_WORKSPACES:
        raise RegistryError('Too many worktree roots')
    for item in value['worktreeRoots']:
        root = _safe(Path(item), directory=True)
        if not root.is_dir() or root.is_relative_to(home) or home.is_relative_to(root):
            raise RegistryError('Unsafe worktree root')
    grant = value['grantStore']
    if value['runtimeEnabled'] and grant is None:
        raise RegistryError('Runtime requires an explicit existing grant store')
    if grant is not None:
        grant_path = _safe(Path(grant), directory=True)
        if not grant_path.is_dir() or any(grant_path.is_relative_to(p) or p.is_relative_to(grant_path)
                                         for p in (source, home)):
            raise RegistryError('Grant store must exist outside source and plugin state')


def _decode(raw: bytes | None, home: Path, *, migrate: bool = False) -> dict:
    """Validate the current registry; only setup may convert a v0.1 registry."""
    if raw is None:
        return {'schema': SCHEMA, 'telemetry': 'off', 'workspaces': []}
    try:
        value = json.loads(raw, object_pairs_hook=_pairs, parse_constant=lambda _: (_ for _ in ()).throw(RegistryError('Nonfinite registry value')))
        if isinstance(value, dict) and set(value) == {'schema', 'workspaces'} and value['schema'] == LEGACY_SCHEMA:
            if not migrate:
                raise MigrationRequired('Registry v0.1 must be migrated with a plugin setup preview')
            value = {'schema': SCHEMA, 'telemetry': 'off', 'workspaces': value['workspaces']}
        if (not isinstance(value, dict) or set(value) != {'schema', 'telemetry', 'workspaces'}
                or value['schema'] != SCHEMA):
            raise RegistryError('Unknown registry schema')
        if not isinstance(value['telemetry'], str) or value['telemetry'] not in TELEMETRY_MODES:
            raise RegistryError('Unknown telemetry consent')
        rows = value['workspaces']
        if not isinstance(rows, list) or len(rows) > MAX_WORKSPACES:
            raise RegistryError('Too many registered workspaces')
        seen = set()
        for row in rows:
            _workspace(row, home)
            if row['workspaceId'] in seen:
                raise RegistryError('Duplicate workspace')
            seen.add(row['workspaceId'])
        return value
    except (TypeError, KeyError, UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise RegistryError('Malformed workspace registry') from exc


def _legacy(raw: bytes | None) -> bool:
    """True for raw bytes already accepted by _decode(..., migrate=True) as v0.1."""
    return raw is not None and json.loads(raw)['schema'] == LEGACY_SCHEMA


def configuration_digest(value: dict | None) -> str | None:
    """Path-free digest of the effective configuration: consent and normalized workspace rows.

    Raw bytes, row order and worktree-root order carry no authority and are ignored.
    """
    if value is None:
        return None
    rows = sorted((dict(row, worktreeRoots=sorted(row['worktreeRoots'])) for row in value['workspaces']),
                  key=lambda row: row['workspaceId'])
    return _hash(_bytes({'telemetry': value['telemetry'], 'workspaces': rows}))


def load(home: Path | None = None) -> dict:
    selected = home_path(home)
    return _decode(_raw(selected), selected)


def _repository(path: Path) -> Path | None:
    try:
        path = _safe(path, directory=True)
        result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--show-toplevel'],
                                capture_output=True, timeout=3, check=False)
        if result.returncode or len(result.stdout) > 8192:
            return None
        root = _safe(Path(os.fsdecode(result.stdout).strip()), directory=True)
        return root if root.is_dir() else None
    except (OSError, subprocess.TimeoutExpired, RegistryError):
        return None


def plan_setup(home: Path | None, sources: list[Path], *, remove=(), runtime: bool | None = None,
               grant_store: Path | None = None, worktree_roots=(), telemetry: str | None = None) -> dict:
    selected = home_path(home)
    before = _raw(selected)
    value = _decode(before, selected, migrate=True)
    migrated = LEGACY_SCHEMA if _legacy(before) else None
    if telemetry is not None:
        if telemetry not in TELEMETRY_MODES:
            raise RegistryError('Telemetry consent must be off or local')
        value['telemetry'] = telemetry
    rows = {row['workspaceId']: row for row in value['workspaces']}
    for identifier in remove:
        if identifier not in rows:
            raise RegistryError('Cannot remove an unregistered workspace')
        del rows[identifier]
    for source in sources:
        source = _safe(Path(source), directory=True)
        if _repository(source) != source:
            raise RegistryError('Select the canonical top-level Git repository or worktree')
        identifier = hashlib.sha256(str(source).encode()).hexdigest()[:32]
        row = dict(rows.get(identifier, {'workspaceId': identifier, 'sourceRoot': str(source),
                   'resultRoot': str(selected / 'results' / identifier),
                   'runtimeEnabled': False, 'grantStore': None, 'worktreeRoots': []}))
        if runtime is not None:
            row.update(runtimeEnabled=runtime, grantStore=str(grant_store) if grant_store else None)
        if worktree_roots:
            row['worktreeRoots'] = [str(_safe(Path(p), directory=True)) for p in worktree_roots]
        _workspace(row, selected)
        rows[identifier] = row
    value['workspaces'] = sorted(rows.values(), key=lambda x: x['workspaceId'])
    _decode(_bytes(value), selected)
    effects = ['Replace only the private workspace registry',
               'Create missing private result directories; never delete source/results']
    if migrated:
        effects.append('Migrate the registry from v0.1 to v0.2 without a v0.1 backup; earlier plugin versions refuse v0.2')
    effects.append(f"Plugin MCP telemetry consent: {value['telemetry']}; applies after reconnect, "
                   'local aggregates only, no upload; setup itself collects nothing')
    preview = {'schema': 'agent-braid-plugin-setup/v0.2', 'home': str(selected),
               'beforeSha256': _hash(before), 'migratedFrom': migrated, 'registry': value,
               'effects': effects, 'reconnectRequired': before != _bytes(value)}
    preview['previewDigest'] = _hash(_bytes(preview))
    return preview


@contextmanager
def _locked(home: Path):
    _safe(home, directory=True)
    home.mkdir(mode=0o700, parents=True, exist_ok=True)
    _private(home, directory=True)
    path = home / 'registry.lock'
    _safe(path, directory=False)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        _private(path, directory=False)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError as exc:
        raise RegistryError('Another setup transaction is active') from exc
    finally:
        os.close(fd)


def apply(home: Path | None, preview: dict, digest: str) -> dict:
    selected = home_path(home)
    body = {key: value for key, value in preview.items() if key != 'previewDigest'}
    if preview.get('previewDigest') != digest or _hash(_bytes(body)) != digest or preview.get('home') != str(selected):
        raise RegistryError('Setup preview digest does not match')
    # Refuse stale previews before creating any owned directories.
    if _hash(_raw(selected)) != preview['beforeSha256']:
        raise RegistryError('Registry changed after preview; preview again')
    raw = _bytes(preview['registry'])
    value = _decode(raw, selected)
    for row in value['workspaces']:
        if _repository(Path(row['sourceRoot'])) != Path(row['sourceRoot']):
            raise RegistryError('A selected repository changed after preview')
    with _locked(selected):
        if _hash(_raw(selected)) != preview['beforeSha256']:
            raise RegistryError('Registry changed after preview; preview again')
        created = []
        temporary = None
        try:
            for directory in [selected / 'results', *[Path(r['resultRoot']) for r in value['workspaces']]]:
                _safe(directory, directory=True)
                if not directory.exists():
                    directory.mkdir(mode=0o700)
                    created.append(directory)
                _private(directory, directory=True)
            fd, name = tempfile.mkstemp(prefix='.registry-', dir=selected)
            temporary = Path(name)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, selected / 'registry.json')
            temporary = None
        except BaseException:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            for directory in reversed(created):
                directory.rmdir()
            raise
    return {'status': 'configured', 'workspaces': value['workspaces'], 'reconnectRequired': preview['reconnectRequired']}


def discover(home: Path | None, search_roots=(), *, current: Path | None = None,
             max_entries: int = 2000, max_depth: int = 4, cancelled: threading.Event | None = None) -> dict:
    if not 1 <= max_entries <= 10000 or not 0 <= max_depth <= 8:
        raise RegistryError('Discovery limits are out of range')
    candidates = {}
    errors = []
    visited = 0
    inspected = 0
    truncated = False
    def add(path, origin):
        root = _repository(Path(path))
        if root is not None:
            candidates.setdefault(str(root), {'sourceRoot': str(root), 'origin': origin})
    # Discovery never writes, so a v0.1 registry is read like a migration preview.
    selected = home_path(home)
    raw = _raw(selected)
    registered = _decode(raw, selected, migrate=True)
    migration_required = _legacy(raw)
    for row in registered['workspaces']:
        add(row['sourceRoot'], 'registered')
    if current is not None:
        add(current, 'current')
    pending = [(Path(p), 0) for p in search_roots]
    while pending:
        if (cancelled is not None and cancelled.is_set()) or visited + inspected >= max_entries:
            truncated = True
            break
        path, depth = pending.pop()
        visited += 1
        try:
            _safe(path, directory=True)
            if (path / '.git').exists():
                add(path, 'selected-search-root')
                continue
            if depth < max_depth:
                with os.scandir(path) as entries:
                    for entry in entries:
                        if visited + inspected >= max_entries or (cancelled is not None and cancelled.is_set()):
                            truncated = True
                            break
                        inspected += 1
                        if (not entry.name.startswith('.') and entry.name not in {'node_modules', 'vendor', 'dist', 'build', '__pycache__'}
                                and entry.is_dir(follow_symlinks=False)):
                            pending.append((Path(entry.path), depth + 1))
        except (OSError, RegistryError):
            errors.append({'directory': str(path), 'status': 'unavailable'})
    return {'candidates': sorted(candidates.values(), key=lambda x: x['sourceRoot']),
            'visitedDirectories': visited, 'inspectedEntries': inspected, 'truncated': truncated,
            'cancelled': cancelled.is_set() if cancelled is not None else False, 'unavailable': errors,
            'migrationRequired': migration_required}
