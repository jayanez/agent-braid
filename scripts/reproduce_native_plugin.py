#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Offline package/native-manager controls; never launch a model/provider session.

Run using the candidate's included Python. State/output must be new owned paths.
Linux may be tested in a network-disabled container; label that observation.
"""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import shutil
import subprocess
import sys



async def codex_inventory(executable, env, cwd, *, timeout_seconds=120):
    """Inspect actual host loading without starting a thread or model turn."""
    process = await asyncio.create_subprocess_exec(str(executable), 'app-server', '--stdio',
        env=env, cwd=cwd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, limit=2 * 1024 * 1024, start_new_session=True)
    async def drain_errors():
        kept = bytearray()
        while chunk := await process.stderr.read(4096):
            kept.extend(chunk[:max(0, 65536 - len(kept))])
        return bytes(kept).decode(errors='replace')
    errors = asyncio.create_task(drain_errors())
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    async def request(identifier, method, params):
        async with asyncio.timeout_at(deadline):
            process.stdin.write((json.dumps({'id': identifier, 'method': method, 'params': params}) + '\n').encode())
            await process.stdin.drain()
            for _ in range(100):
                raw = await process.stdout.readline()
                if not raw:
                    raise RuntimeError('Native app server exited during discovery')
                value = json.loads(raw)
                if value.get('id') == identifier:
                    if 'error' in value:
                        raise RuntimeError('Native app server refused discovery: ' + str(value['error']))
                    return value['result']
            raise RuntimeError('Native app server discovery exceeded notification budget')
    try:
        await request(0, 'initialize', {'clientInfo': {'name': 'agent_braid_installation_probe', 'version': '0.1.0'}})
        process.stdin.write(b'{"method":"initialized","params":{}}\n')
        await process.stdin.drain()
        listed = await request(1, 'skills/list', {'cwds': [str(cwd)], 'forceReload': True})
        selected = [skill for row in listed['data'] for skill in row['skills']
                    if skill.get('pluginId') == 'agent-braid@agent-braid']
        assert len(selected) == 6 and all(skill['enabled'] for skill in selected), 'Native Codex did not load the six plugin skills'
        inventory = await request(2, 'mcpServerStatus/list', {'limit': 20})
        servers = [server for server in inventory['data'] if server.get('pluginId') == 'agent-braid@agent-braid']
        assert len(servers) == 1, 'Native Codex did not load plugin MCP (inspect manifest/loader diagnostics)'
        server = servers[0]
        assert (server.get('serverInfo') or {}).get('name') == 'agent-braid-plugin', (
            'Native Codex handshake failed: ' + str(server.get('toolsError')))
        assert not server.get('toolsError') and set(server['tools']) == {
            'plugin-status', 'workspaces', 'analyze-work', 'analyze', 'prepare'}, 'Native Codex did not load configured workspace tools'
        result = {'skills': selected, 'mcpServer': server,
                  'limits': ['Actual native loader/discovery only; no thread/start, turn/start or skill invocation',
                             'Fresh child-process user home and host profiles; caller environment/global user settings unchanged']}
    finally:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(process.wait(), 10)
        except TimeoutError:
            os.killpg(process.pid, signal.SIGKILL)
            await asyncio.wait_for(process.wait(), 5)
        try:
            stderr = await asyncio.wait_for(errors, 5)
        except TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stderr = 'Native host stderr drain exceeded its cleanup deadline'
    result['stderr'] = stderr
    return result


def run(args):
    marketplace = args.marketplace.resolve(strict=True)
    plugin = marketplace / 'plugins/agent-braid'
    state = args.state_root.absolute()
    if state.exists() or state.resolve() != state:
        raise ValueError('Choose a new canonical state directory')
    state.mkdir(mode=0o700, parents=True)
    commands = []
    env = dict(os.environ)
    # Real per-process test home, not a change to the caller's environment or user files.
    # Native hosts can discover global components outside their config override.
    user_home = state / 'user home'
    user_home.mkdir(mode=0o700)
    env['HOME'] = str(user_home)
    for key in ('XDG_DATA_HOME', 'XDG_CONFIG_HOME', 'XDG_STATE_HOME', 'XDG_CACHE_HOME'):
        env.pop(key, None)
    for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN'):
        env.pop(key, None)
    paths = state / 'tools'; paths.mkdir()
    for name in ('git', 'sh', 'uname', 'dirname'):
        executable = shutil.which(name)
        if not executable:
            raise ValueError(f'Missing prerequisite {name}')
        (paths / name).symlink_to(executable)
    env['PATH'] = str(paths)
    application_home = user_home / ('Library/Application Support/AgentBraid' if sys.platform == 'darwin' else '.local/share/agent-braid')
    env['AGENT_BRAID_HOME'] = str(application_home)
    for key, directory in [('CODEX_HOME', 'codex-profile'), ('CLAUDE_CONFIG_DIR', 'claude-profile')]:
        path = state / directory; path.mkdir(mode=0o700)
        env[key] = str(path)

    def command(argv):
        value = subprocess.run([str(x) for x in argv], env=env, cwd=state,
                               capture_output=True, text=True, timeout=180)
        commands.append({'argv': [str(x) for x in argv], 'exitCode': value.returncode,
                         'stdout': value.stdout[-20000:], 'stderr': value.stderr[-10000:]})
        if value.returncode:
            raise RuntimeError(f'Control command failed: {argv[0]} {argv[1:]}: {value.stderr[-1000:]}')
        return value.stdout

    launch = plugin / 'launch'
    roots = [state / 'repo one', state / 'repo two']
    for root in roots:
        command([paths / 'git', 'init', '-q', root])
    doctor = json.loads(command([launch, 'plugin', 'doctor']))
    assert doctor['runtimeIncluded'] and doctor['package']['status'] == 'verified'
    selection = ['--source-root', roots[0], '--source-root', roots[1]]
    preview = json.loads(command([launch, 'plugin', 'setup', *selection]))
    assert not Path(env['AGENT_BRAID_HOME']).exists(), 'Preview wrote application state'
    registered = json.loads(command([launch, 'plugin', 'setup', *selection,
                                    '--apply', '--preview-digest', preview['previewDigest']]))
    ids = [x['workspaceId'] for x in registered['workspaces']]
    assert len(ids) == 2 and not any(x['runtimeEnabled'] for x in registered['workspaces'])
    discovered = json.loads(command([launch, 'plugin', 'discover', '--search-root', state,
                                    '--max-entries', '100', '--max-depth', '2']))
    assert {str(x) for x in roots} <= {x['sourceRoot'] for x in discovered['candidates']}
    fixture = json.loads(args.fixture.read_text())

    async def protocol():
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        observations = []
        for mode in ('auto', 'legacy'):
            params = StdioServerParameters(command=str(launch), args=['plugin', 'serve'], env=env, cwd=str(state))
            async with Client(params, mode=mode) as client:
                names = sorted(tool.name for tool in (await client.list_tools()).tools)
                assert names == ['analyze', 'analyze-work', 'plugin-status', 'prepare', 'workspaces']
                for identifier in ids:
                    result = await client.call_tool('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': fixture})
                    value = result.structured_content
                    assert value['status'] == 'ok' and value['workspaceId'] == identifier
                    assert value['result']['report']['interactions'][0]['classification'] == 'independent-candidate'
                    uri = value['evidenceRefs'][0]['uri']
                    assert uri.startswith('agent-braid-plugin://' + identifier + '/')
                    await client.read_resource(uri)
                bad = await client.call_tool('analyze-work', {'workspaceId': 'unknown'})
                assert bad.structured_content['status'] == 'refused'
                observations.append({'mode': mode, 'tools': names, 'twoWorkspaceAnalysis': 'passed',
                                     'unknownWorkspaceRefused': True, 'prompts': len((await client.list_prompts()).prompts)})
        async def session(identifier):
            params = StdioServerParameters(command=str(launch), args=['plugin', 'serve'], env=env, cwd=str(state))
            async with Client(params) as client:
                result = await client.call_tool('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': fixture})
                assert result.structured_content['status'] == 'ok'
                assert result.structured_content['workspaceId'] == identifier
                return identifier
        assert sorted(await asyncio.gather(*(session(identifier) for identifier in ids))) == sorted(ids)
        observations.append({'simultaneousIndependentConnections': 2, 'workspaceIsolation': 'passed'})
        return observations
    protocols = asyncio.run(protocol())
    registry = Path(env['AGENT_BRAID_HOME']) / 'registry.json'
    before = registry.read_bytes()
    results = Path(env['AGENT_BRAID_HOME']) / 'results'
    sentinel = results / ids[0] / 'retained.txt'; sentinel.write_text('owned fixture result')
    for host, executable in [('codex', args.codex_executable), ('claude', args.claude_executable)]:
        if executable is None:
            continue
        executable = executable.resolve(strict=True)
        version = command([executable, '--version']).strip()
        if host == 'codex':
            command([executable, 'plugin', 'marketplace', 'add', marketplace])
            for _ in range(2):
                installed = json.loads(command([executable, 'plugin', 'add', 'agent-braid@agent-braid', '--json']))
            installed_root = Path(installed['installedPath'])
            check = json.loads(command([installed_root / 'launch', 'plugin', 'doctor', '--plugin-root', installed_root]))
            assert check['package']['status'] == 'verified', 'Installed Codex cache inventory failed'
            command([executable, 'plugin', 'list', '--json'])
            commands.append({'nativeCodexInventory': asyncio.run(codex_inventory(executable, env, state))})
            command([executable, 'plugin', 'remove', 'agent-braid@agent-braid'])
        else:
            command([executable, 'plugin', 'validate', plugin, '--strict'])
            for _ in range(2):
                command([executable, 'plugin', 'install', 'agent-braid', '--marketplace', marketplace, '--scope', 'user'])
            command([executable, 'plugin', 'details', 'agent-braid@agent-braid'])
            health = command([executable, 'mcp', 'list'])
            plugin_lines = [line for line in health.splitlines() if 'plugin:agent-braid:' in line]
            assert plugin_lines and all('Connected' in line for line in plugin_lines), 'Native Claude MCP handshake failed'
            commands[-1]['stdout'] = '\n'.join(plugin_lines)
            commands.append({'nativeClaudeMcpConnected': True, 'unrelatedHealthRowsExcluded': True})
            installed_plugins = json.loads(command([executable, 'plugin', 'list', '--json']))
            installed_root = Path(next(row['installPath'] for row in installed_plugins if row['id'] == 'agent-braid@agent-braid'))
            check = json.loads(command([installed_root / 'launch', 'plugin', 'doctor', '--plugin-root', installed_root]))
            assert check['package']['status'] == 'verified', 'Installed Claude cache inventory failed'
            command([executable, 'plugin', 'uninstall', 'agent-braid@agent-braid', '--scope', 'user'])
        assert registry.read_bytes() == before and sentinel.read_text() == 'owned fixture result'
        commands.append({'nativeHost': host, 'version': version, 'binarySha256': hashlib.file_digest(executable.open('rb'), 'sha256').hexdigest(),
                         'stateRetainedAfterUninstall': True})
    removal = json.loads(command([launch, 'plugin', 'workspaces', '--remove', ids[0]]))
    command([launch, 'plugin', 'workspaces', '--remove', ids[0], '--apply', '--preview-digest', removal['previewDigest']])
    assert sentinel.exists() and all(root.exists() for root in roots)
    record = {'schema': 'agent-braid-plugin-reproduction/v1', 'status': 'passed',
              'environment': {'system': platform.system(), 'machine': platform.machine(), 'python': sys.version,
                              'pathPrerequisites': sorted(x.name for x in paths.iterdir()), 'context': args.context},
              'provenanceSha256': hashlib.sha256((plugin / 'provenance.json').read_bytes()).hexdigest(),
              'packageInventorySha256': hashlib.sha256((plugin / 'package-inventory.json').read_bytes()).hexdigest(),
              'protocols': protocols, 'commands': commands,
              'limits': ['No provider/model session, interactive skill journey, human rating or official approval observed',
                         'Repeated native install is not a version-changing update; source-changing upgrade remains a release gate']}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(record, stream, indent=2); stream.write('\n')
    print(json.dumps({'status': 'passed', 'record': str(args.output), 'commands': len(commands)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--marketplace', type=Path, required=True)
    parser.add_argument('--state-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--codex-executable', type=Path)
    parser.add_argument('--claude-executable', type=Path)
    parser.add_argument('--context', required=True, help='native-mac, container-linux-amd64, or actual observed context')
    run(parser.parse_args())
