# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in real stdio MCP client against a live parent-hosted ToolingService.

The child performs protocol and artifact verification only. All source/Git work
stays in the live parent context, sharing its original budget and cancellation.
This is an internal harness, not a registered stock SDK server or public CLI.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
from types import SimpleNamespace

from .system_one import canonical, parse_json, digest, thaw, freeze
from .system_one_verified_consumers import CoreRequestContext, _require
from .system_one_verified_tooling import artifact_value, bound_service, charge

PROTOCOL = '2025-11-25'
MAX_FRAME = 1024 * 1024
MAX_FRAMES = 144
MAX_WIRE = 8 * 1024 * 1024


def _frame(value):
    raw = canonical(value) + b'\n'
    _require(len(raw) <= MAX_FRAME, 'transport-failure')
    return raw


def _child(bootstrap, expected):
    """Deterministic MCP client. No Git/native/source acquisition calls."""
    _require(bootstrap.stat().st_size <= MAX_FRAME, 'transport-failure')
    raw = bootstrap.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected, 'transport-failure')
    config = parse_json(raw)
    _require(set(config) == {'arguments', 'tools'}, 'transport-failure')
    identifier = 0
    resources = 0
    def send(value):
        sys.stdout.buffer.write(_frame(value))
        sys.stdout.buffer.flush()
    def rpc(method, params):
        nonlocal identifier
        identifier += 1
        _require(identifier <= MAX_FRAMES, 'transport-failure')
        send({'jsonrpc': '2.0', 'id': identifier, 'method': method, 'params': params})
        line = sys.stdin.buffer.readline(MAX_FRAME + 1)
        _require(0 < len(line) <= MAX_FRAME and line.endswith(b'\n'), 'transport-failure')
        response = parse_json(line)
        _require(set(response) == {'jsonrpc', 'id', 'result'}
                 and response['jsonrpc'] == '2.0' and type(response['id']) is int
                 and response['id'] == identifier, 'transport-failure')
        return response['result']
    initialized = rpc('initialize', {'protocolVersion': PROTOCOL, 'capabilities': {},
                                     'clientInfo': {'name': 'braid-verified-peer', 'version': '1'}})
    _require(initialized == {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {}, 'resources': {}},
                            'serverInfo': {'name': 'braid-verified-local', 'version': '1'}}, 'transport-failure')
    send({'jsonrpc': '2.0', 'method': 'notifications/initialized', 'params': {}})
    tools = rpc('tools/list', {})
    _require(tools == {'tools': config['tools']}, 'transport-failure')
    result = rpc('tools/call', {'name': 'prepare', 'arguments': config['arguments']})
    _require(set(result) == {'structuredContent', 'content', 'isError'} and result['isError'] is False
             and result['content'] == [{'type': 'text', 'text': 'Retrieve complete bounded preparation evidence.'}],
             'transport-failure')
    def read(uri):
        nonlocal resources
        resources += 1
        value = rpc('resources/read', {'uri': uri})
        _require(type(value) is dict and set(value) == {'contents'}
                 and type(value['contents']) is list and len(value['contents']) == 1,
                 'transport-failure')
        body = value['contents'][0]
        _require(set(body) == {'uri', 'mimeType', 'text'} and body['uri'] == uri, 'transport-failure')
        return body['mimeType'], body['text']
    value, artifact = artifact_value(result['structuredContent'], read)
    send({'jsonrpc': '2.0', 'method': 'notifications/verified-result', 'params': {
        'prepared': value, 'requests': identifier, 'resourceReads': resources,
        'artifact': artifact, 'gitCommands': 0}})


def _command(path, sha):
    _require(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file(), 'transport-failure')
    return ['/usr/bin/sandbox-exec', '-p', '(version 1)(allow default)(deny network*)',
            sys.executable, '-m', 'agent_braid.system_one_verified_stdio',
            '--bootstrap', str(path), '--bootstrap-sha256', sha]


def stdio_prepare(context, request, destination):
    service = bound_service(context, request, destination)
    from .tooling_mcp import _tool_definitions
    types = SimpleNamespace(Tool=lambda **kw: kw, ToolAnnotations=lambda **kw: kw)
    tools = [tool for tool in _tool_definitions(service, types) if tool['name'] == 'prepare']
    tools[0]['inputSchema']['properties']['mode'] = {'enum': ['serial']}
    bootstrap = destination.parent / 'stdio-bootstrap.json'
    config = canonical({'arguments': service.runtime.arguments, 'tools': tools})
    _require(len(config) <= MAX_FRAME, 'transport-failure')
    fd = os.open(bootstrap, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(config)
    home = destination.parent / 'stdio-home'
    home.mkdir()
    env = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin:/usr/sbin:/sbin',
           'HOME': str(home), 'LANG': 'en_US.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
           'GIT_ALLOW_PROTOCOL': 'file', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'}
    process = None
    receipt = {'kind': 'real-stdio-client-parent-service', 'exitCode': None,
               'termination': 'not-started', 'networkDeniedByOS': False,
               'childGitCommands': 0, 'requests': 0, 'resourceReads': 0,
               'frames': 0, 'wireBytes': 0, 'stderrBytes': 0, 'transcript': []}
    context._transport_receipt = receipt
    context.checkpoint('transportEvidence', 0)
    with selectors.DefaultSelector() as selector:
        try:
            command = _command(bootstrap, hashlib.sha256(config).hexdigest())
            receipt['networkDeniedByOS'] = command[:1] == ['/usr/bin/sandbox-exec']
            process = subprocess.Popen(command,
                cwd=Path(__file__).resolve().parents[1], env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            context._owned_processes.append(process)
            receipt['termination'] = 'running'
            receipt['pid'] = process.pid
            for stream in (process.stdin, process.stdout, process.stderr):
                os.set_blocking(stream.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
            selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
            pending, buffer = bytearray(), bytearray()
            initialized = ready = called = False
            envelope = terminal = None
            resources = 0
            expected_uri = None
            def response(identifier, result):
                raw = _frame({'jsonrpc': '2.0', 'id': identifier, 'result': result})
                charge(context, raw)
                receipt['wireBytes'] += len(raw)
                _require(receipt['wireBytes'] <= MAX_WIRE, 'transport-failure')
                receipt['transcript'].append({'direction': 'server-to-client',
                    'frameBase64': base64.b64encode(raw).decode('ascii')})
                pending.extend(raw)
                if process.stdin not in [k.fileobj for k in selector.get_map().values()]:
                    selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            def receive(raw):
                nonlocal initialized, ready, called, envelope, terminal, resources, expected_uri
                receipt['frames'] += 1
                _require(receipt['frames'] <= MAX_FRAMES and terminal is None, 'transport-failure')
                receipt['transcript'].append({'direction': 'client-to-server',
                    'frameBase64': base64.b64encode(raw).decode('ascii')})
                value = parse_json(raw)
                _require(type(value) is dict and value.get('jsonrpc') == '2.0'
                         and type(value.get('params')) is dict, 'transport-failure')
                method, params = value.get('method'), value['params']
                if 'id' not in value:
                    _require(set(value) == {'jsonrpc', 'method', 'params'}, 'transport-failure')
                    if method == 'notifications/initialized':
                        _require(initialized and not ready and params == {}, 'transport-failure')
                        ready = True
                    else:
                        _require(method == 'notifications/verified-result' and called
                            and expected_uri is None and resources >= 2
                            and set(params) == {'prepared', 'requests', 'resourceReads', 'artifact', 'gitCommands'}
                            and type(params['requests']) is int and params['requests'] == receipt['requests']
                            and type(params['resourceReads']) is int and params['resourceReads'] == resources
                            and type(params['gitCommands']) is int and params['gitCommands'] == 0,
                            'transport-failure')
                        # Independently re-read complete owned evidence; no digest-only acceptance.
                        def checked_read(uri):
                            context.checkpoint('transportEvidence', 0)
                            mime, text = service.read_resource(uri, context.git_budget.cancel_event)
                            charge(context, text.encode('utf-8'))
                            return mime, text
                        actual, artifact = artifact_value(envelope, checked_read)
                        _require(actual == params['prepared'] and artifact == params['artifact'], 'evidence-incomplete')
                        terminal = actual
                    return
                _require(set(value) == {'jsonrpc', 'id', 'method', 'params'}
                         and type(value['id']) is int and value['id'] == receipt['requests'] + 1,
                         'transport-failure')
                receipt['requests'] += 1
                identifier = value['id']
                if method == 'initialize':
                    _require(not initialized and params == {'protocolVersion': PROTOCOL, 'capabilities': {},
                        'clientInfo': {'name': 'braid-verified-peer', 'version': '1'}}, 'transport-failure')
                    initialized = True
                    response(identifier, {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {}, 'resources': {}},
                        'serverInfo': {'name': 'braid-verified-local', 'version': '1'}})
                elif method == 'tools/list':
                    _require(ready and not called and params == {}, 'transport-failure')
                    response(identifier, {'tools': tools})
                elif method == 'tools/call':
                    _require(ready and not called and params == {'name': 'prepare', 'arguments': service.runtime.arguments},
                             'transport-failure')
                    called = True
                    envelope = service.invoke('prepare', params['arguments'], context.git_budget.cancel_event)
                    from .tooling_mcp import _digest_bytes, _json_bytes
                    _require(envelope['provenance']['inputDigest'] == _digest_bytes(_json_bytes(
                        {'operation': 'prepare', 'input': service.runtime.arguments})), 'evidence-incomplete')
                    refs = envelope.get('evidenceRefs')
                    _require(type(refs) is list and len(refs) == 1, 'evidence-incomplete')
                    expected_uri = refs[0]['uri']
                    response(identifier, {'structuredContent': envelope,
                        'content': [{'type': 'text', 'text': 'Retrieve complete bounded preparation evidence.'}],
                        'isError': envelope['status'] != 'ok'})
                else:
                    _require(method == 'resources/read' and called and set(params) == {'uri'}
                             and expected_uri is not None and params['uri'] == expected_uri, 'transport-failure')
                    resources += 1
                    mime, text = service.read_resource(params['uri'], context.git_budget.cancel_event)
                    body = parse_json(text.encode('utf-8'))
                    expected_uri = body['firstChunkUri'] if resources == 1 else body['nextChunkUri']
                    response(identifier, {'contents': [{'uri': params['uri'], 'mimeType': mime, 'text': text}]})
            while selector.get_map():
                context.checkpoint('transportEvidence', 0)
                for key, _mask in selector.select(min(.05, context.remaining_ns('transportEvidence') / 1e9)):
                    if key.data == 'stdin':
                        try:
                            sent = os.write(process.stdin.fileno(), pending)
                        except BlockingIOError:
                            continue
                        del pending[:sent]
                        if not pending:
                            selector.unregister(process.stdin)
                        continue
                    raw = os.read(key.fileobj.fileno(), 65536)
                    if not raw:
                        selector.unregister(key.fileobj)
                        continue
                    charge(context, raw)
                    receipt['wireBytes'] += len(raw)
                    _require(receipt['wireBytes'] <= MAX_WIRE, 'transport-failure')
                    if key.data == 'stderr':
                        receipt['stderrBytes'] += len(raw)
                        _require(receipt['stderrBytes'] <= 65536, 'transport-failure')
                        continue
                    buffer.extend(raw)
                    while b'\n' in buffer:
                        index = buffer.index(b'\n') + 1
                        _require(index <= MAX_FRAME, 'transport-failure')
                        frame = bytes(buffer[:index])
                        del buffer[:index]
                        receive(frame)
                    _require(len(buffer) < MAX_FRAME, 'transport-failure')
            _require(not buffer and not pending and terminal is not None, 'transport-failure')
            process.wait(timeout=max(.001, context.remaining_ns('transportEvidence') / 1e9))
            _require(process.returncode == 0 and not service.plans, 'transport-failure')
            receipt.update(exitCode=process.returncode, resourceReads=resources, completeBodyVerified=True)
            return terminal, receipt
        finally:
            if process is not None:
                try:
                    if process.poll() is None:
                        # Keep parent scratch if these bounded reap attempts fail.
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(timeout=.5)
                        except subprocess.TimeoutExpired:
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.wait(timeout=.5)
                finally:
                    receipt['exitCode'] = process.returncode
                    receipt['termination'] = 'stopped' if process.poll() is not None else 'unknown'
                    for stream in (process.stdin, process.stdout, process.stderr):
                        stream.close()


class StdioRequestContext(CoreRequestContext):
    consumer_id = 'mcp-stdio'

    def _prepare_native(self, request, destination):
        try:
            with self.context.phase('transportEvidence'):
                value, receipt = stdio_prepare(self.context, request, destination)
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ValueError) else ''
            raise ValueError(reason if reason in {'cancelled', 'deadline-exceeded',
                'work-budget-exceeded', 'input-budget-exceeded', 'evidence-incomplete',
                'native-prepare-failed'} else 'transport-failure') from None
        finally:
            self.transport_receipt = getattr(self.context, '_transport_receipt', None)
        return value

    def _record(self, final_decision):
        value = thaw(super()._record(final_decision))
        receipt = getattr(self.context, '_transport_receipt', None)
        if receipt is not None and receipt['termination'] not in {'stopped', 'not-started'}:
            value['status'] = 'refused'
            value['usage']['termination'] = 'unknown'
            value['reasonCodes'] = sorted(set(value['reasonCodes']) | {'termination-unknown'})
            value['preparedDigest'] = None
            self._prepared = None
        return freeze(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bootstrap', type=Path, required=True)
    parser.add_argument('--bootstrap-sha256', required=True)
    args = parser.parse_args()
    try:
        _child(args.bootstrap, args.bootstrap_sha256)
    except Exception:
        # No source paths/bootstrap contents/exception detail on protocol streams.
        sys.stderr.write('Verified stdio peer refused the transport\n')
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
