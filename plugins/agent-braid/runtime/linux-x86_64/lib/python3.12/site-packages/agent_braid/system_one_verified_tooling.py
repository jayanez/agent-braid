# SPDX-License-Identifier: AGPL-3.0-only
"""Internal, opt-in ToolingService preparation using a live Core context.

Default ToolingService and registered tools remain unchanged. The local runtime
collaborator admits only the exact reconstructed prepare call; no execution,
recovery, policy-plan registration or grant capability is provided.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from . import git_runtime, tooling_mcp, mcp_runtime
from .git_process import GitCommandBudget
from .system_one import canonical, parse_json, thaw
from .system_one_verified_consumers import CoreRequestContext, _require


def charge(context, raw):
    """Charge captured transport bytes to the original aggregate output ceiling."""
    context.checkpoint('transportEvidence', 0)
    _require(GitCommandBudget.record_output(context.git_budget, len(raw)), 'input-budget-exceeded')


def artifact_value(envelope, read):
    """Reconstruct the existing evidence protocol, checking every complete byte."""
    _require(type(envelope) is dict and envelope.get('status') == 'ok', 'native-prepare-failed')
    _require(set(envelope) == {'schemaVersion', 'operation', 'status', 'summary', 'result',
                               'evidenceRefs', 'limits', 'provenance'}
             and envelope['schemaVersion'] == tooling_mcp.SCHEMA_VERSION
             and envelope['operation'] == 'prepare', 'evidence-incomplete')
    refs = envelope.get('evidenceRefs')
    _require(type(refs) is list and len(refs) == 1, 'evidence-incomplete')
    ref = refs[0]
    _require(type(ref) is dict and set(ref) == {'artifactId', 'uri', 'sha256', 'sizeBytes'}, 'evidence-incomplete')
    _require(type(ref['sizeBytes']) is int and 0 < ref['sizeBytes'] <= 1024 * 1024,
             'evidence-incomplete')
    mime, text = read(ref['uri'])
    _require(mime == 'application/json', 'evidence-incomplete')
    manifest = parse_json(text.encode('utf-8'))
    _require(set(manifest) == {'artifactId', 'sha256', 'sizeBytes', 'mediaType',
                              'chunkSizeBytes', 'firstChunkUri'}, 'evidence-incomplete')
    _require(all(manifest[k] == ref[k] for k in ('artifactId', 'sha256', 'sizeBytes'))
             and manifest['mediaType'] == 'application/json'
             and manifest['chunkSizeBytes'] == tooling_mcp.CHUNK_BYTES, 'evidence-incomplete')
    data, seen = bytearray(), set()
    uri = manifest['firstChunkUri']
    while uri is not None:
        _require(type(uri) is str and uri not in seen and len(seen) < 128, 'evidence-incomplete')
        seen.add(uri)
        mime, text = read(uri)
        _require(mime == 'application/json', 'evidence-incomplete')
        chunk = parse_json(text.encode('utf-8'))
        _require(set(chunk) == {'artifactId', 'artifactSha256', 'chunkSha256', 'offset',
                               'length', 'totalBytes', 'encoding', 'data', 'nextChunkUri'}, 'evidence-incomplete')
        _require(chunk['encoding'] == 'base64' and type(chunk['data']) is str, 'evidence-incomplete')
        try:
            raw = base64.b64decode(chunk['data'], validate=True)
        except (ValueError, TypeError):
            raise ValueError('evidence-incomplete') from None
        _require(type(chunk['offset']) is int and type(chunk['length']) is int
            and type(chunk['totalBytes']) is int and chunk['offset'] == len(data)
            and chunk['length'] == len(raw) and 0 < len(raw) <= tooling_mcp.CHUNK_BYTES
            and chunk['artifactId'] == ref['artifactId'] and chunk['totalBytes'] == ref['sizeBytes']
            and chunk['artifactSha256'] == ref['sha256']
            and chunk['chunkSha256'] == hashlib.sha256(raw).hexdigest(), 'evidence-incomplete')
        _require(len(data) + len(raw) <= ref['sizeBytes'], 'evidence-incomplete')
        data.extend(raw)
        uri = chunk['nextChunkUri']
    _require(len(data) == ref['sizeBytes'] and hashlib.sha256(data).hexdigest() == ref['sha256'],
             'evidence-incomplete')
    value = parse_json(bytes(data))
    inline = envelope.get('result')
    if type(inline) is dict and inline.get('type') == 'evidence-artifact-reference':
        _require(set(inline) == {'type', 'artifactId', 'uri', 'sha256', 'sizeBytes', 'mediaType'}
            and all(inline[k] == ref[k] for k in ref)
            and inline['mediaType'] == 'application/json', 'evidence-incomplete')
    else:
        _require(inline == value, 'evidence-incomplete')
    return value, {'artifactSha256': ref['sha256'], 'bytes': len(data), 'chunks': len(seen)}


class _BoundPrepareRuntime(mcp_runtime.RuntimeTools):
    """Real read-only native preparation, fixed to this active request."""
    def __init__(self, service, context, request, destination):
        self.source = service.config.source_root
        self.results = service.config.result_parent
        self.grants = self.results / 'absent-grants'
        self.context = context
        self.arguments = {'request': thaw(request), 'runDirectory': str(destination), 'mode': 'serial'}

    def invoke(self, name, args, cancel_event):
        _require(name == 'prepare' and args == self.arguments, 'runtime-request-mismatch')
        _require(cancel_event is self.context.git_budget.cancel_event, 'invalid-envelope')
        self.context.checkpoint('nativePrepare', 0)
        self._request_scope(args['request'])
        self._destination_scope(args['runDirectory'])
        return git_runtime.prepare_run(args['request'], args['runDirectory'],
            cancel_event=cancel_event, budget=self.context.git_budget)


def bound_service(context, request, destination):
    """Build a private instance; default service methods and catalogs are intact."""
    service = tooling_mcp.ToolingService(tooling_mcp.ToolingConfig(
        Path(request['repository']), destination.parent, runtime_enabled=False))
    service.runtime = _BoundPrepareRuntime(service, context, request, destination)
    return service


class ToolingRequestContext(CoreRequestContext):
    """MCP service recipient with actual envelope/resource verification."""
    consumer_id = 'mcp-service'

    def _prepare_native(self, request, destination):
        context = self.context
        service = bound_service(context, request, destination)
        args = service.runtime.arguments
        envelope = service.invoke('prepare', args, context.git_budget.cancel_event)
        with context.phase('transportEvidence'):
            charge(context, canonical(envelope))
            _require(envelope['provenance']['inputDigest'] == tooling_mcp._digest_bytes(
                tooling_mcp._json_bytes({'operation': 'prepare', 'input': args})), 'evidence-incomplete')
            def read(uri):
                context.checkpoint('transportEvidence', 0)
                mime, text = service.read_resource(uri, context.git_budget.cancel_event)
                charge(context, text.encode('utf-8'))
                return mime, text
            value, evidence = artifact_value(envelope, read)
            _require(not service.plans and not destination.exists(), 'native-prepare-failed')
            self.transport_receipt = {**evidence, 'kind': 'in-process-tooling-service',
                'completeBodyVerified': True, 'childGitCommands': 0}
        return value
