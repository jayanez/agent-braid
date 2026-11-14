# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-008 / SC-008 (T010): every BL.4 path runs with no socket, no process and content-free telemetry.

The static half (standard-library imports only, no socket/subprocess import, an import closure without
network or event-loop modules, no MCP tool) is `tests.test_lightning_cli.BoundaryTests` and
`BL2BoundaryTests`; this module is the dynamic half. Each BL.4 CLI command (init with consent and
sources, validate, status, sweep, purge preview and apply) and each adapter reader (rollout, Loom, host
transcript, System One) runs under a guard that turns any socket, process launch or exec into a test
failure, with HOME moved to a temporary directory so the telemetry and System One locations are
temporary too. Inputs carry synthetic canaries; no CLI output or telemetry byte may carry one, no
BL.4 path records a telemetry event, and every CLI output states executionAuthorization false.
"""
from contextlib import ExitStack
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_adapter as adapter
from agent_braid import lightning_store as store
from agent_braid import tooling_telemetry as telemetry
from tests.test_lightning_adapter import (DIGEST, EMAIL, LOOM, SALT, T0, TOKEN, cli, episode_line, request, reward,
                                          trace_bytes)

BLOCKED = {socket: ('socket', 'create_connection', 'socketpair', 'getaddrinfo', 'fromfd'),
           subprocess: ('Popen',),
           os: ('system', 'popen', 'fork', 'forkpty', 'posix_spawn', 'posix_spawnp', 'execv', 'execve', 'execvp',
                'execvpe', 'spawnv', 'spawnve')}
TELEMETRY_WRITERS = ('observe', 'record_lifecycle', 'record_view')
CANARIES = (TOKEN, EMAIL)


def blocked(name):
    def refuse(*args, **kwargs):
        raise AssertionError(f'boundary: {name} called')
    return refuse


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'state'
        self.telemetry_calls = []
        self.guard = ExitStack()
        self.guard.enter_context(patch.dict(os.environ, {'HOME': str(self.base / 'user')}))
        for module, names in BLOCKED.items():
            for name in names:
                if hasattr(module, name):
                    self.guard.enter_context(patch.object(module, name, blocked(f'{module.__name__}.{name}')))
        for name in TELEMETRY_WRITERS:
            real = getattr(telemetry, name)

            def recording(*args, _real=real, _name=name, **kwargs):
                self.telemetry_calls.append((_name, args, kwargs))
                return _real(*args, **kwargs)
            self.guard.enter_context(patch.object(telemetry, name, recording))
        self.addCleanup(self.guard.close)
        self.addCleanup(self.tmp.cleanup)
        self.outputs = []

    def command(self, *args):
        code, out, err = cli('lightning', *args, '--home', str(self.home))
        self.assertEqual(code, 0, err)
        value = json.loads(out)
        self.assertIs(value.get('executionAuthorization'), False, args)
        self.outputs.append((out, err))
        return value

    def init(self, *flags):
        flags = ('init', '--non-interactive', *flags)
        preview = self.command(*flags)
        return self.command(*flags, '--apply', '--preview-digest', preview['previewDigest'])

    def purge(self, *target):
        preview = self.command('purge', *target)
        return self.command('purge', *target, '--apply', '--preview-digest', preview['previewDigest'])

    def read_every_source(self):
        """Store a canary-bearing rollout, then read it and the other three sources through the adapter."""
        run = store.RunStore(self.home, 'run-1')
        run.create(config_digest=DIGEST, now=T0)
        for item in (request(1), reward(2, 0.5)):
            run.append('event', item)
        run.append('trace', {'attemptId': 'at-1', 'sequence': 1, 'prompt': f'mail {EMAIL}',
                             'response': f'key {TOKEN}'}, now=T0 + 1)
        transcript, day = self.base / 'trace.json', self.base / 'episodes.jsonl'
        transcript.write_bytes(trace_bytes(attempt=EMAIL))
        day.write_bytes(episode_line())
        records = [adapter.rollout_triplets(self.home, 'run-1', 'at-1'),
                   adapter.rollout_messages(self.home, 'run-1', 'at-1'),
                   adapter.loom_triplets(self.home, LOOM.read_bytes(), SALT),
                   adapter.loom_messages(self.home, LOOM.read_bytes(), SALT),
                   adapter.transcript_triplets(self.home, transcript, SALT),
                   adapter.transcript_messages(self.home, transcript, SALT),
                   adapter.system_one_triplets(self.home, day, SALT),
                   adapter.system_one_messages(self.home, day, SALT)]
        for record in records:
            text = json.dumps(record)
            self.assertNotIn(TOKEN, text)
            self.assertNotIn(EMAIL, text)
        return records

    def test_every_bl4_path_opens_no_socket_launches_nothing_and_states_no_authorization(self):
        self.init('--trace-consent', 'redacted', '--trace-sources', 'rollout,host-transcript,loom,system-one')
        self.command('validate')
        self.assertEqual(self.command('status')['traceContent']['content'], True)
        records = self.read_every_source()
        self.assertIsNotNone(records[0][0]['prompt'])  # content was read, so the redaction path ran
        self.command('sweep')
        self.command('purge', '--expired')
        self.purge('--run-id', 'run-1')
        self.init('--trace-consent', 'none')  # lowering consent is a BL.4 path too
        self.assertEqual(self.command('status')['traceContent']['content'], False)
        self.purge('--all')
        self.assertEqual(len(self.outputs), 13)
        for out, err in self.outputs:
            for canary in CANARIES:
                self.assertNotIn(canary, out + err)

    def test_telemetry_stays_content_free(self):
        self.init('--trace-consent', 'redacted', '--trace-sources', 'rollout,host-transcript,loom,system-one')
        self.read_every_source()
        self.command('status')
        self.purge('--all')
        # ADR 0025 telemetry is unchanged by BL.4 (privacy review): no BL.4 path records an event at all,
        # so no content can reach it; the stored telemetry bytes carry no canary either.
        self.assertEqual(self.telemetry_calls, [])
        directory = Path(os.environ['HOME']) / '.local/share/agent-braid/telemetry'
        self.assertEqual(directory, telemetry.default_directory())
        stored = b''.join(p.read_bytes() for p in directory.rglob('*') if p.is_file()) if directory.exists() else b''
        for canary in CANARIES:
            self.assertNotIn(canary.encode(), stored)

    def test_the_guard_fails_a_socket_or_process_call(self):
        """Negative control: a path that opened a socket or launched a process would fail these tests."""
        for call in (lambda: socket.create_connection(('127.0.0.1', 9)), lambda: socket.socket(),
                     lambda: subprocess.run(['true']), lambda: os.system('true')):
            with self.assertRaisesRegex(AssertionError, 'boundary: '):
                call()

    def test_a_socket_inside_a_bl4_path_fails_it(self):
        """Negative control: an adapter gate that opened a socket would fail every status call."""
        real = adapter.gate

        def connecting(*args, **kwargs):
            socket.socket()
            return real(*args, **kwargs)
        with patch.object(adapter, 'gate', connecting), self.assertRaisesRegex(AssertionError, 'boundary: socket'):
            self.command('status')

    def test_the_recorder_sees_a_telemetry_call(self):
        """Negative control: a BL.4 path that recorded telemetry would fail the empty-call check."""
        try:
            telemetry.record_view(f'key {TOKEN}')
        except (ValueError, OSError):
            pass  # an unknown operation is refused after the call was recorded
        self.assertEqual([name for name, _, _ in self.telemetry_calls], ['record_view'])


if __name__ == '__main__':
    unittest.main()
