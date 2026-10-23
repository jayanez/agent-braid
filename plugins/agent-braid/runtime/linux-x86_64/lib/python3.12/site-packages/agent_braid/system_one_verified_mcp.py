# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit developer stdio endpoint for owned verified-plan software fixtures.

No default catalog registration, model, execution grant or persistent request
state. The optional SDK is imported only when creating the server. Native work
shares one live core context; the SDK frame/response caps are separate limits.
"""
from __future__ import annotations

import argparse
import asyncio
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

from . import system_one_verified_acquisition as acquisition
from .system_one import CancellationToken, canonical, digest, freeze, thaw
from .system_one_verified_consumers import CoreRequestContext

TOOL_NAME = 'agent_braid_verified_prepare'
FORMAT = 's1-verified-dev-mcp-v1'
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_REQUEST_BYTES = 1024 * 1024
CALL_TIMEOUT_SECONDS = 180
INPUT_SCHEMA = {
    'type': 'object', 'properties': {'requestJson': {'type': 'string', 'maxLength': MAX_REQUEST_BYTES}},
    'required': ['requestJson'], 'additionalProperties': False}
_BODY_KEYS = ('producerDecision', 'producerEvidence', 'proposal', 'consumerResult',
              'prepared', 'finalDecision')


def _root(value: Path) -> Path:
    value = Path(value)
    try:
        acquisition._unlinked(value)
        if not value.is_dir():
            raise ValueError
        return value.resolve(strict=True)
    except (ValueError, OSError):
        raise ValueError('invalid-owned-root') from None


def _envelope(status, reasons, bodies=None):
    bodies = bodies if bodies is not None else {key: None for key in _BODY_KEYS}
    return {'format': FORMAT, 'status': status, 'reasonCodes': sorted(reasons),
            'bodies': bodies, 'bodyDigests': {k: digest(v) if v is not None else None
                                           for k, v in bodies.items()},
            'limits': {'requestBytes': MAX_REQUEST_BYTES, 'responseBytes': MAX_RESPONSE_BYTES,
                       'sdkWaitSeconds': CALL_TIMEOUT_SECONDS, 'terminationMode': 'cooperative',
                       'transportAccounting': 'separate-from-native-usage'},
            'executionAuthorization': False}


def _arguments(value):
    if type(value) is not dict or set(value) != {'requestJson'} or type(value['requestJson']) is not str:
        raise ValueError('invalid-tool-arguments')
    try:
        raw = value['requestJson'].encode('utf-8')
    except UnicodeError:
        raise ValueError('invalid-tool-arguments') from None
    if len(raw) > MAX_REQUEST_BYTES:
        raise ValueError('input-budget-exceeded')
    return raw


def prepare_bundle(raw: bytes, owned_root: Path, *, cancellation=None):
    """One live request, including native preparation and complete bound bodies.

    SDK cancellation owns the supplied token. No proposal from a different
    request or consumer is an input to this function.
    """
    root = _root(owned_root)
    with CoreRequestContext(raw, root, cancellation=cancellation) as context:
        result = context.prepare()
        bodies = {'producerDecision': context.producer,
                  'producerEvidence': context.producer_evidence,
                  'proposal': context.proposal, 'consumerResult': result,
                  'prepared': context.prepared, 'finalDecision': context.context.decision}
        response = _envelope(result['status'], result['reasonCodes'], bodies)
        # Content and structuredContent each contain the body. Reserve space for
        # their JSON escaping and the SDK/RPC wrappers before exposing success.
        if len(canonical(response)) > (MAX_RESPONSE_BYTES - 4096) // 6:
            response = _envelope('refused', ['response-budget-exceeded'])
        return freeze(response)


async def _settle(worker, token):
    """Cancel the original request and await its owned cleanup, never detach."""
    token.cancel()
    import anyio
    with anyio.CancelScope(shield=True):
        try:
            await asyncio.shield(worker)
        except Exception:
            pass


def create_server(owned_root: Path):
    """Create a private pinned-SDK server; imports do not activate it."""
    root = _root(owned_root)
    try:
        if version('mcp') != '2.3.0':
            raise RuntimeError('The developer endpoint requires mcp==2.3.0')
        from mcp.server import Server
        import mcp.types as types
    except (PackageNotFoundError, ImportError):
        raise RuntimeError('The developer endpoint requires the optional mcp==2.3.0 SDK') from None
    busy = asyncio.Lock()

    async def list_tools(_ctx, _params):
        return types.ListToolsResult(tools=[types.Tool(
            name=TOOL_NAME, description='Prepare verified plans for explicitly owned software fixtures; never execute.',
            inputSchema=INPUT_SCHEMA,
            annotations=types.ToolAnnotations(readOnlyHint=True, destructiveHint=False,
                                               openWorldHint=False))])

    def encode(response):
        body = thaw(response)
        result = types.CallToolResult(content=[types.TextContent(text=canonical(body).decode('utf-8'))],
                                      structuredContent=body, isError=body['status'] == 'refused')
        if len(result.model_dump_json(by_alias=True).encode('utf-8')) + 4096 > MAX_RESPONSE_BYTES:
            body = _envelope('refused', ['response-budget-exceeded'])
            return types.CallToolResult(content=[types.TextContent(text=canonical(body).decode('utf-8'))],
                                        structuredContent=body, isError=True)
        return result

    async def call_tool(_ctx, params):
        if params.name != TOOL_NAME:
            raise ValueError('unavailable-tool')
        try:
            raw = _arguments(params.arguments)
        except ValueError as exc:
            return encode(_envelope('refused', [str(exc)]))
        if busy.locked():
            return encode(_envelope('refused', ['concurrent-request']))
        async with busy:
            token = CancellationToken()
            deadline = asyncio.get_running_loop().time() + CALL_TIMEOUT_SECONDS
            worker = asyncio.create_task(asyncio.to_thread(prepare_bundle, raw, root, cancellation=token))
            try:
                async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                    response = await asyncio.shield(worker)
                    encoded = encode(response)
                    if asyncio.get_running_loop().time() >= deadline:
                        raise TimeoutError
                    if token.cancelled:
                        raise asyncio.CancelledError
                    return encoded
            except TimeoutError:
                await _settle(worker, token)
                return encode(_envelope('refused', ['endpoint-deadline-exceeded']))
            except BaseException:
                await _settle(worker, token)
                raise

    return Server('agent-braid-verified-dev', version='1',
                  instructions='Opt-in owned-fixture preparation only. No execution authorization.',
                  on_list_tools=list_tools, on_call_tool=call_tool)


async def serve_stdio(owned_root: Path):
    """Serve bounded JSON-RPC frames with no ambient/global configuration."""
    server = create_server(owned_root)
    from mcp.server.stdio import stdio_server
    from .tooling_mcp import _BoundedInput
    bounded = _BoundedInput(getattr(sys.stdin, 'buffer', sys.stdin))
    async with stdio_server(stdin=bounded) as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owned-root', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        asyncio.run(serve_stdio(args.owned_root))
    except (ValueError, RuntimeError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
