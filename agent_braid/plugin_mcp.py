# SPDX-License-Identifier: AGPL-3.0-only
"""Separate plugin MCP facade over immutable, explicitly registered workspaces."""
from __future__ import annotations

import asyncio
import copy
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
import threading
from urllib.parse import urlsplit

from . import __version__
from .plugin_registry import (MigrationRequired, RegistryError, RegistryStale, _private, configuration_digest,
                              home_path, inspect_registry, not_grown)
from . import tooling_mcp as core

SCHEMA = 'agent-braid-plugin/v0.2'

# SPEC-061 REQ-006 (amendment A2): the private local copy of each analyze-work report. One subdirectory per
# report holds exactly `analysis.json`, the name the viewer's watcher reads.
REPORT_COPY_NAME = 'analysis.json'
REPORT_COPY_DAYS = 30
REPORT_COPY_MAX_BYTES = 64 * 1024 * 1024
REPORT_COPY_MAX_COUNT = 1500  # each copy takes two of the watcher's 4,096 entries (view_tail.MAX_ENTRIES)
_COPY_DIRECTORY = re.compile(r'^analysis-(\d{8}T\d{12})Z-[0-9a-f]{16}$')
_COPY_TEMPORARY = '.analysis.tmp'  # not an artifact name: the watcher never reads a half-written copy
_COPY_STAMP = '%Y%m%dT%H%M%S%f'
_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _now():
    return datetime.now(timezone.utc)


def _open_private_root(root, registered):
    """Open the registered result root without following links; refuse anything that is not private to the user."""
    root, registered = Path(root), Path(registered)
    if root != registered:
        raise ValueError('Result root is not the registered one')
    _private(root, directory=True)  # no link on the path, owned by the user, no group/other access
    descriptor = os.open(root, _DIRECTORY)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('Result root is not private')
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _discard_copy(root_fd, name):
    """Remove a report copy directory holding only the files this module creates; True when it is gone."""
    try:
        descriptor = os.open(name, _DIRECTORY, dir_fd=root_fd)
    except OSError:
        return False
    try:
        for entry in (REPORT_COPY_NAME, _COPY_TEMPORARY):
            try:
                os.unlink(entry, dir_fd=descriptor)
            except FileNotFoundError:
                pass
        os.rmdir(name, dir_fd=root_fd)
        return True
    except OSError:
        return False
    finally:
        os.close(descriptor)


def _report_copies(root_fd):
    """(stamp, name, size) of each report copy: a real directory of ours holding only our own file names."""
    found = []
    for name in os.listdir(root_fd):
        match = _COPY_DIRECTORY.match(name)
        if match is None:
            continue
        try:
            descriptor = os.open(name, _DIRECTORY, dir_fd=root_fd)  # O_DIRECTORY|O_NOFOLLOW: only real directories
        except OSError:
            continue
        try:
            entries = os.listdir(descriptor)
            if not set(entries) <= {REPORT_COPY_NAME, _COPY_TEMPORARY}:
                continue  # holds something that is not ours
            size = sum(os.stat(entry, dir_fd=descriptor, follow_symlinks=False).st_size for entry in entries)
        except OSError:
            continue
        finally:
            os.close(descriptor)
        found.append((match.group(1), name, size))
    return sorted(found)


def _prune_report_copies(root_fd, now, max_bytes, days, max_count=REPORT_COPY_MAX_COUNT, keep=None):
    """Remove report copies older than `days`, then the oldest until within `max_bytes` and `max_count`.

    The copy named `keep` (the one just written) is never removed.
    """
    cutoff = (now - timedelta(days=days)).strftime(_COPY_STAMP)
    kept = []
    for stamp, name, size in _report_copies(root_fd):
        if name != keep and stamp < cutoff and _discard_copy(root_fd, name):
            continue
        kept.append((stamp, name, size))
    total = sum(size for _stamp, _name, size in kept)
    count = len(kept)
    for _stamp, name, size in kept:
        if total <= max_bytes and count <= max_count:
            break
        if name != keep and _discard_copy(root_fd, name):
            total -= size
            count -= 1


def write_report_copy(result_root, registered_root, body, *, now=None, max_bytes=REPORT_COPY_MAX_BYTES,
                      days=REPORT_COPY_DAYS, max_count=REPORT_COPY_MAX_COUNT):
    """Store `body` (the report bytes) as <result_root>/analysis-<utc stamp>-<random>/analysis.json, then prune.

    The directory is created 0700 and the file 0600 under a temporary name and renamed into place, so the file
    appears whole or not at all. Raises when the root is not the registered private directory (a link, another
    owner, group or other access); callers treat any failure as "no copy" and say nothing about it.
    """
    when = (now or _now()).astimezone(timezone.utc)
    root_fd = _open_private_root(result_root, registered_root)
    try:
        name = f'analysis-{when.strftime(_COPY_STAMP)}Z-{secrets.token_hex(8)}'
        os.mkdir(name, 0o700, dir_fd=root_fd)
        try:
            directory_fd = os.open(name, _DIRECTORY, dir_fd=root_fd)
            try:
                descriptor = os.open(_COPY_TEMPORARY, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                                     dir_fd=directory_fd)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(body)
                    stream.flush()
                    os.fsync(descriptor)
                os.rename(_COPY_TEMPORARY, REPORT_COPY_NAME, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            finally:
                os.close(directory_fd)
        except BaseException:
            _discard_copy(root_fd, name)
            raise
        try:
            _prune_report_copies(root_fd, when, max_bytes, days, max_count, keep=name)
        except OSError:
            pass  # retention is best effort: the new copy stays
    finally:
        os.close(root_fd)


class WorkspaceService(core.ToolingService):
    def __init__(self, identifier, config, registered_root=None):
        self.identifier = identifier
        self.registered_root = registered_root
        super().__init__(config)

    def invoke(self, name, args, cancelled, observation=None):
        envelope = super().invoke(name, args, cancelled, observation)
        if name == 'analyze-work' and envelope.get('status') == 'ok':
            self._keep_report_copy(envelope)
        return envelope

    def _keep_report_copy(self, envelope):
        """SPEC-061 REQ-006: keep a private local copy of the report for the viewer's watcher.

        Local only, never uploaded. The envelope is already final here and is never changed; any failure means
        no copy and records nothing (a path or request detail could be sensitive).
        """
        try:
            if self.registered_root is None:
                return
            result = envelope['result']
            if type(result) is dict and result.get('type') == 'evidence-artifact-reference':
                with self.lock:
                    data = self.artifacts[result['artifactId']].data
                result = json.loads(data)
            report = result['report']
            if type(report) is not dict:
                return
            write_report_copy(self.config.result_parent, self.registered_root, core._json_bytes(report))
        except Exception:
            pass

    def _base_uri(self, run_id, artifact_id):
        return self.external(core.ToolingService._base_uri(run_id, artifact_id))

    def _chunk_uri(self, artifact, offset):
        return self.external(core.ToolingService._chunk_uri(artifact, offset))

    def external(self, uri):
        return uri.replace('agent-braid://', f'agent-braid-plugin://{self.identifier}/', 1)

    def read_resource(self, uri, cancelled=None):
        prefix = f'agent-braid-plugin://{self.identifier}/'
        if not uri.startswith(prefix):
            raise core.ToolingError('Resource belongs to another workspace')
        return super().read_resource('agent-braid://' + uri[len(prefix):], cancelled)

    def capabilities(self):
        value = super().capabilities()
        value['resources'] = [self.external(uri) for uri in value['resources']]
        # The plugin surface advertises no prompts (SPEC-054 REQ-003) and keeps its alpha.4 bytes (SPEC-060 REQ-004):
        # the portable surface's v0.2 identifiers never reach the plugin resource.
        for key in ('prompts', 'deprecatedPrompts', 'envelopeSchemaVersion'):
            value.pop(key, None)
        value['schemaVersion'] = core.SCHEMA_VERSION
        return value


class PluginRouter:
    def __init__(self, home=None, plugin_root=None):
        self.home = home_path(home)
        self.plugin_root = Path(plugin_root).resolve() if plugin_root else None
        # A v0.1 registry (baseline None) serves bootstrap status only until setup migrates it.
        # The registry is read tolerantly: stale worktree roots and unsafe workspace rows are quarantined
        # individually, so one deleted worktree can never stop the other workspaces from serving.
        found = self._inspect()
        self.baseline = found['value'] if found else None
        self._start_reason = None  # refusal bucket of the first workspace not served at start (telemetry only)
        self.baseline_digest = configuration_digest(self.baseline)
        self.snapshot = self.baseline or {'telemetry': 'off', 'workspaces': []}
        self.system_one = self.snapshot.get('systemOne', 'off')
        self.services = {}
        self.unavailable = []
        self._unavailable_codes = {}
        for entry, code in zip(found['quarantined'], found['quarantinedCodes']) if found else ():
            self._start_reason = self._start_reason or code
            if entry['workspaceId']:
                self._unavailable_codes[entry['workspaceId']] = code
        for row in self.snapshot['workspaces']:
            try:
                config = core.ToolingConfig(Path(row['sourceRoot']), Path(row['resultRoot']),
                    grant_store=Path(row['grantStore']) if row['grantStore'] else None,
                    runtime_enabled=row['runtimeEnabled'],
                    worktree_roots=tuple(Path(p) for p in row['worktreeRoots']),
                    telemetry=self.snapshot['telemetry'], system_one=self.system_one)
                self.services[row['workspaceId']] = WorkspaceService(row['workspaceId'], config, Path(row['resultRoot']))
            except (core.ToolingError, OSError) as exc:  # e.g. the source repository was deleted: isolate this workspace
                self.unavailable.append({'workspaceId': row['workspaceId'], 'reason': 'configuration rejected'})
                # A vanished root surfaces as FileNotFoundError from resolve(strict=True); codes never come from text.
                if isinstance(exc, FileNotFoundError):
                    code = 'registry-root-missing'
                elif isinstance(exc, core.ToolingError):
                    code = exc.code
                else:
                    code = 'other'
                self._unavailable_codes[row['workspaceId']] = code
                self._start_reason = self._start_reason or code
        # One global admission lock bounds reservations across all workspace services.
        self.admission = threading.Lock()

    def _inspect(self):
        try:
            return inspect_registry(self.home)
        except MigrationRequired:
            return None

    def status(self):
        from . import system_one_shadow  # lazy: serving with System One off never loads it
        found = self._inspect()
        current = found['value'] if found else None
        current_digest = configuration_digest(current)
        return {'schema': SCHEMA, 'version': __version__,
                'status': ('migration-required' if current is None else
                           'configured' if self.services else 'setup-required'),
                'reconnectRequired': current_digest != self.baseline_digest,
                'baselineDigest': self.baseline_digest, 'currentDigest': current_digest,
                'telemetry': {'configuredMode': current['telemetry'] if current else 'off',
                              'activeMode': self.snapshot['telemetry'],
                              'retentionDays': 30, 'automaticUpload': False},
                'systemOne': {'configuredMode': current.get('systemOne', 'off') if current else 'off',
                              'activeMode': self.system_one,
                              'store': {'location': system_one_shadow.display_location(),
                                        'present': system_one_shadow.store_present()},
                              'episodeRetentionDays': system_one_shadow.RETENTION_DAYS},
                'gitAvailable': shutil.which('git') is not None,
                'registryHome': str(self.home),
                'bundledCli': str(self.plugin_root / 'launch') if self.plugin_root else None,
                'runtimeIncluded': bool(self.plugin_root and Path(sys.executable).resolve().is_relative_to(self.plugin_root)),
                'workspaces': copy.deepcopy(self.snapshot['workspaces']),
                # Path-free diagnostics of the registry as it is now: stale roots are inactive and excluded from
                # the digest, unsafe rows are not served; plugin setup --prune-stale repairs both.
                'staleWorktreeRoots': found['stale'] if found else [],
                'unsafeWorkspaces': found['quarantined'] if found else [],
                'unavailableWorkspaces': list(self.unavailable),
                'executionAuthorization': False}

    def _require_current(self):
        # A deleted registered worktree only shrinks authority, so the snapshot keeps serving; a revoked root
        # or any other change reconnects.
        found = self._inspect()
        if (configuration_digest(found['value'] if found else None) != self.baseline_digest
                and not not_grown(self.baseline, found)):
            raise RegistryStale('Registry changed since this connection started: reconnect the MCP, '
                                'then read plugin-status (code reconnect-required)')

    def _refusal(self, name, message, identifier=None):
        return {'schemaVersion': SCHEMA, 'workspaceId': identifier, 'operation': name,
                'status': 'refused', 'summary': message, 'result': None, 'evidenceRefs': [],
                'limits': ['No effects admitted by this refusal'],
                'provenance': {'executionAuthorization': False}}

    def record_start(self):
        """Count one serve-start (SPEC-047 lifecycle) once the registry passed schema, privacy and shape validation.

        Called by `serve` only, never by construction, so doctor and status reads are not counted. Nothing is
        written when consent is not local; a registry that failed those checks never reaches here.
        """
        if self.baseline is None or self.snapshot['telemetry'] != 'local':
            return
        from .tooling_telemetry import record_lifecycle
        record_lifecycle('serve-start', 'refused' if self._start_reason else 'ok', self._start_reason)

    def invoke(self, name, args, cancelled):
        """The one owner of plugin call measurement: services only report their refusal reason into it."""
        if self.snapshot['telemetry'] != 'local':
            return self._dispatch(name, args, cancelled, None)
        from .tooling_telemetry import mcp_operation, observe
        operation = mcp_operation(name)
        with observe('local', 'mcp', operation) as observation:
            envelope = self._dispatch(name, args, cancelled, observation)
            observation.complete(operation, envelope, cancelled)
            return envelope

    def _dispatch(self, name, args, cancelled, observation):
        try:
            core._bounded_input(args)
            if not isinstance(args, dict):
                raise RegistryError('Tool arguments must be an object', code='arguments-invalid')
            if name in {'plugin-status', 'workspaces'}:
                if args:
                    raise RegistryError('Bootstrap tools accept no arguments', code='arguments-invalid')
                return {'schemaVersion': SCHEMA, 'workspaceId': None, 'operation': name,
                        'status': 'ok', 'summary': 'Read-only plugin configuration status',
                        'result': self.status(), 'evidenceRefs': [], 'limits': ['Registration is not execution authority'],
                        'provenance': {'executionAuthorization': False}}
            self._require_current()
            identifier = args.get('workspaceId')
            if not isinstance(identifier, str) or identifier not in self.services:
                code = ('arguments-invalid' if not isinstance(identifier, str)
                        else self._unavailable_codes.get(identifier, 'workspace-unregistered'))
                raise RegistryError('Select an explicitly registered workspaceId using workspaces; run setup if none exists', code=code)
            service = self.services[identifier]
            if not self.admission.acquire(blocking=False):
                raise RegistryError('Plugin admission is busy; inspect existing work before retrying', code='admission-busy')
            try:
                size = sum(sum(len(a.data) for a in item.artifacts.values()) for item in self.services.values())
                count = sum(len(item.artifacts) for item in self.services.values())
                if size + core.MAX_ARTIFACT_BYTES > core.MAX_INVENTORY_BYTES or count >= core.MAX_INVENTORY_ARTIFACTS:
                    raise RegistryError('Plugin evidence inventory is full; inspect evidence before reconnecting', code='inventory-full')
                value = service.invoke(name, {k: v for k, v in args.items() if k != 'workspaceId'}, cancelled, observation)
                return dict(value, schemaVersion=SCHEMA, workspaceId=identifier)
            finally:
                self.admission.release()
        except RegistryStale as exc:
            if observation is not None:
                observation.reason = exc.code
            identifier = args.get('workspaceId') if isinstance(args, dict) else None
            refusal = self._refusal(name, str(exc), identifier if isinstance(identifier, str) and identifier in self.services else None)
            return dict(refusal, result={'code': exc.code})
        except (RegistryError, core.ToolingError, OSError, TypeError, ValueError) as exc:
            if observation is not None:
                observation.reason = exc.code if isinstance(exc, (RegistryError, core.ToolingError)) else 'other'
            return self._refusal(name, 'Plugin request refused: check workspace, arguments, registry and reconnect state')

    def read_resource(self, uri, cancelled=None):
        if len(uri.encode('utf-8')) > 1100:
            raise core.ToolingError('Resource selector exceeds its limit')
        parsed = urlsplit(uri)
        if parsed.scheme != 'agent-braid-plugin' or parsed.netloc not in self.services or parsed.query or parsed.fragment:
            raise core.ToolingError('Unknown plugin resource')
        self._require_current()
        return self.services[parsed.netloc].read_resource(uri, cancelled)


def create_server(router):
    if version('mcp') != '2.3.0':
        raise RuntimeError('Plugin requires the bundled mcp==2.3.0 SDK')
    from mcp.server import Server
    import mcp.types as types

    async def list_tools(_ctx, _params):
        definitions = {}
        for service in router.services.values():
            for definition in core._tool_definitions(service, types):
                definition.input_schema['properties']['workspaceId'] = {'type': 'string'}
                definition.input_schema['required'].append('workspaceId')
                definition.output_schema['properties']['schemaVersion'] = {'const': SCHEMA}
                definition.output_schema['properties']['workspaceId'] = {'type': ['string', 'null']}
                definitions[definition.name] = definition
        for name in ('plugin-status', 'workspaces'):
            definitions[name] = types.Tool(name=name, description='Read-only setup status, bundled CLI location and registered workspace IDs. No registration or grant effects.',
                inputSchema={'type': 'object', 'properties': {}, 'additionalProperties': False},
                annotations=types.ToolAnnotations(readOnlyHint=True, openWorldHint=False))
        return types.ListToolsResult(tools=list(definitions.values()))

    async def call_tool(_ctx, params):
        event = threading.Event()
        worker = asyncio.create_task(asyncio.to_thread(router.invoke, params.name, params.arguments or {}, event))
        try:
            async with asyncio.timeout(core.CALL_TIMEOUT_SECONDS):
                result = await asyncio.shield(worker)
        except BaseException:
            await core._settle_cancelled_worker(worker, event)
            raise
        return types.CallToolResult(content=[types.TextContent(text=core._json_bytes(result).decode())],
                                    structuredContent=result, isError=result['status'] in {'refused', 'error'})

    async def list_resources(_ctx, _params):
        values = []
        for service in router.services.values():
            values.append(types.Resource(name=f'{service.identifier}-capabilities', uri=service.external('agent-braid://capabilities'), mimeType='application/json'))
            with service.lock:
                for artifact in service.artifacts.values():
                    values.append(types.Resource(name=f'{service.identifier}-{artifact.artifact_id}',
                        uri=service._base_uri(artifact.run_id, artifact.artifact_id), mimeType='application/json'))
        return types.ListResourcesResult(resources=values)

    async def list_resource_templates(_ctx, _params):
        return types.ListResourceTemplatesResult(resourceTemplates=[])

    async def read_resource(_ctx, params):
        event = threading.Event()
        worker = asyncio.create_task(asyncio.to_thread(router.read_resource, str(params.uri), event))
        try:
            async with asyncio.timeout(core.CALL_TIMEOUT_SECONDS):
                mime, value = await asyncio.shield(worker)
        except BaseException:
            await core._settle_cancelled_worker(worker, event)
            raise
        return types.ReadResourceResult(contents=[types.TextResourceContents(uri=str(params.uri), mimeType=mime, text=value)])

    return Server('agent-braid-plugin', version=__version__,
        instructions='First read plugin-status/workspaces. Run the packaged setup skill when setup is required. Every delegated tool requires an explicit registered workspaceId. Never infer roots or grant authority. Registry changes require reconnecting.',
        on_list_tools=list_tools, on_call_tool=call_tool,
        on_list_resources=list_resources, on_read_resource=read_resource,
        on_list_resource_templates=list_resource_templates)


async def serve(home=None, plugin_root=None):
    from mcp.server.stdio import stdio_server
    router = PluginRouter(home, plugin_root)
    server = create_server(router)  # an SDK mismatch raises here: that start served nothing and is not counted
    router.record_start()
    async with stdio_server(stdin=core._BoundedInput(getattr(sys.stdin, 'buffer', sys.stdin))) as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())
