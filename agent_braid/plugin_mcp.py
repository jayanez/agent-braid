# SPDX-License-Identifier: AGPL-3.0-only
"""Separate plugin MCP facade over immutable, explicitly registered workspaces."""
from __future__ import annotations

import asyncio
import copy
from importlib.metadata import version
import json
from pathlib import Path
import shutil
import sys
import threading
from urllib.parse import urlsplit

from . import __version__
from .plugin_registry import (MigrationRequired, RegistryError, RegistryStale, configuration_digest,
                              home_path, load)
from . import system_one_shadow
from . import tooling_mcp as core

SCHEMA = 'agent-braid-plugin/v0.2'


class WorkspaceService(core.ToolingService):
    def __init__(self, identifier, config):
        self.identifier = identifier
        super().__init__(config)

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
        self.baseline = self._current()
        self.baseline_digest = configuration_digest(self.baseline)
        self.snapshot = self.baseline or {'telemetry': 'off', 'workspaces': []}
        self.system_one = self.snapshot.get('systemOne', 'off')
        self.services = {}
        for row in self.snapshot['workspaces']:
            config = core.ToolingConfig(Path(row['sourceRoot']), Path(row['resultRoot']),
                grant_store=Path(row['grantStore']) if row['grantStore'] else None,
                runtime_enabled=row['runtimeEnabled'],
                worktree_roots=tuple(Path(p) for p in row['worktreeRoots']),
                telemetry=self.snapshot['telemetry'], system_one=self.system_one)
            self.services[row['workspaceId']] = WorkspaceService(row['workspaceId'], config)
        # One global admission lock bounds reservations across all workspace services.
        self.admission = threading.Lock()

    def _current(self):
        try:
            return load(self.home)
        except MigrationRequired:
            return None

    def status(self):
        current = self._current()
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
                              'store': {'location': '~/.local/share/agent-braid/system-one',
                                        'present': system_one_shadow.store_present()},
                              'episodeRetentionDays': 30},
                'gitAvailable': shutil.which('git') is not None,
                'registryHome': str(self.home),
                'bundledCli': str(self.plugin_root / 'launch') if self.plugin_root else None,
                'runtimeIncluded': bool(self.plugin_root and Path(sys.executable).resolve().is_relative_to(self.plugin_root)),
                'workspaces': copy.deepcopy(self.snapshot['workspaces']),
                'executionAuthorization': False}

    def _require_current(self):
        if configuration_digest(self._current()) != self.baseline_digest:
            raise RegistryStale('Registry changed since this connection started: reconnect the MCP, '
                                'then read plugin-status (code reconnect-required)')

    def _refusal(self, name, message, identifier=None):
        return {'schemaVersion': SCHEMA, 'workspaceId': identifier, 'operation': name,
                'status': 'refused', 'summary': message, 'result': None, 'evidenceRefs': [],
                'limits': ['No effects admitted by this refusal'],
                'provenance': {'executionAuthorization': False}}

    def invoke(self, name, args, cancelled):
        try:
            core._bounded_input(args)
            if not isinstance(args, dict):
                raise RegistryError('Tool arguments must be an object')
            if name in {'plugin-status', 'workspaces'}:
                if args:
                    raise RegistryError('Bootstrap tools accept no arguments')
                return {'schemaVersion': SCHEMA, 'workspaceId': None, 'operation': name,
                        'status': 'ok', 'summary': 'Read-only plugin configuration status',
                        'result': self.status(), 'evidenceRefs': [], 'limits': ['Registration is not execution authority'],
                        'provenance': {'executionAuthorization': False}}
            self._require_current()
            identifier = args.get('workspaceId')
            if not isinstance(identifier, str) or identifier not in self.services:
                raise RegistryError('Select an explicitly registered workspaceId using workspaces; run setup if none exists')
            service = self.services[identifier]
            if not self.admission.acquire(blocking=False):
                raise RegistryError('Plugin admission is busy; inspect existing work before retrying')
            try:
                size = sum(sum(len(a.data) for a in item.artifacts.values()) for item in self.services.values())
                count = sum(len(item.artifacts) for item in self.services.values())
                if size + core.MAX_ARTIFACT_BYTES > core.MAX_INVENTORY_BYTES or count >= core.MAX_INVENTORY_ARTIFACTS:
                    raise RegistryError('Plugin evidence inventory is full; inspect evidence before reconnecting')
                value = service.invoke(name, {k: v for k, v in args.items() if k != 'workspaceId'}, cancelled)
                return dict(value, schemaVersion=SCHEMA, workspaceId=identifier)
            finally:
                self.admission.release()
        except RegistryStale as exc:
            identifier = args.get('workspaceId') if isinstance(args, dict) else None
            refusal = self._refusal(name, str(exc), identifier if isinstance(identifier, str) and identifier in self.services else None)
            return dict(refusal, result={'code': exc.code})
        except (RegistryError, core.ToolingError, OSError, TypeError, ValueError):
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
    server = create_server(PluginRouter(home, plugin_root))
    async with stdio_server(stdin=core._BoundedInput(getattr(sys.stdin, 'buffer', sys.stdin))) as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())
