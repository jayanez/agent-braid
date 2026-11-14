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
from agent_braid import mcp_runtime
from agent_braid import lightning_store as store
from agent_braid import tooling_telemetry as telemetry
from agent_braid.lightning_schema import EVENT_SCHEMA, Event, LightningSchemaError
from tests.test_lightning_adapter import (DIGEST, EMAIL, LOOM, SALT, T0, TOKEN, cli, episode_line, request, reward,
                                          trace_bytes)

ROOT = Path(__file__).resolve().parents[1]
NAME = 'owner.example.org'  # a name-shaped identifier: valid as an attempt id, not caught by redaction

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

    def test_a_process_inside_a_bl4_path_fails_it(self):
        """Negative control (from #1369): an adapter gate that launched a process would fail every status call."""
        with patch.object(adapter, 'gate', lambda *args, **kwargs: subprocess.run(['true'])), \
                self.assertRaisesRegex(AssertionError, 'boundary: subprocess.Popen'):
            self.command('status')

    def test_run_telemetry_records_carry_no_content(self):
        """From #1369: event, rollout and result files hold no content; content lives only in the trace file."""
        self.init('--trace-consent', 'redacted', '--trace-sources', 'rollout')
        self.read_every_source()
        run = store.RunStore(self.home, 'run-1')
        files = [path for path in run.root.iterdir() if path.name in store.KINDS.values()]
        self.assertTrue(files)
        for path in files:
            text = path.read_text()
            for marker in (*CANARIES, 'mail ', '"prompt"', '"response"', 'REDACTED'):
                self.assertNotIn(marker, text, path.name)
        self.assertIn('REDACTED', (run.root / store.CONTENT_FILE).read_text())  # negative control: content exists
        with self.assertRaises(LightningSchemaError):  # the event schema admits no content field
            Event.parse({'schema': EVENT_SCHEMA, 'rolloutId': 'ro-1', 'attemptId': 'at-1', 'sequence': 9,
                         'eventType': 'model_request', 'timestamp': T0,
                         'data': {**request(1).to_dict()['data'], 'prompt': 'text'}})

    def test_no_mcp_module_or_runtime_tool_reaches_lightning(self):
        """From #1369: every MCP module, not only tooling_mcp and plugin_mcp, and the runtime tool list."""
        self.assertEqual([tool for tool in mcp_runtime.TOOLS if 'lightning' in tool], [])
        modules = sorted((ROOT / 'agent_braid').glob('*mcp*.py'))
        self.assertGreater(len(modules), 2)
        self.assertEqual([p.name for p in modules if 'lightning' in p.read_text().lower()], [])


class IdentifierLeakTests(unittest.TestCase):
    """Source ids may hold free text, so no adapter output or error names one (owner review of #1368)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'state'
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', 'rollout,host-transcript,loom,system-one']
        preview = json.loads(cli(*flags)[1])['previewDigest']
        self.assertEqual(cli(*flags, '--apply', '--preview-digest', preview)[0], 0)

    def outputs(self):
        run = store.RunStore(self.home, 'run-1')
        run.create(config_digest=DIGEST, now=T0)
        for item in (request(1), reward(2, 0.5)):
            run.append('event', Event.parse({**item.to_dict(), 'attemptId': NAME}))
        run.append('trace', {'attemptId': NAME, 'sequence': 1, 'prompt': 'plain', 'response': 'x'}, now=T0 + 1)
        transcript, day = self.base / 'trace.json', self.base / 'episodes.jsonl'
        transcript.write_bytes(trace_bytes(attempt=NAME))
        line = episode_line()
        day.write_bytes(line)
        episode = json.loads(line)['episodeId']
        records = [adapter.rollout_triplets(self.home, 'run-1', NAME),
                   adapter.rollout_messages(self.home, 'run-1', NAME),
                   adapter.transcript_triplets(self.home, transcript, SALT),
                   adapter.transcript_messages(self.home, transcript, SALT),
                   adapter.system_one_triplets(self.home, day, SALT),
                   adapter.system_one_messages(self.home, day, SALT)]
        errors = []
        for call in (lambda: adapter.rollout_triplets(self.home, 'run-1', NAME + '.x'),
                     lambda: adapter.transcript_triplets(self.home, self.write(trace_bytes(attempt=NAME)[:-9]), SALT),
                     lambda: adapter.loom_triplets(self.home, b'{"seq":1,"id":"' + NAME.encode() + b'"}\n', SALT),
                     lambda: adapter.system_one_triplets(self.home, self.base / NAME, SALT)):
            with self.assertRaises(adapter.AdapterError) as caught:
                call()
            errors.append(str(caught.exception))
        return records, errors, episode

    def write(self, data):
        path = self.base / 'broken.json'
        path.write_bytes(data)
        return path

    def test_no_output_or_error_names_a_source_id(self):
        records, errors, episode = self.outputs()
        self.assertTrue(records[0][0]['prompt'] and records[4][0]['prompt'])  # content was read
        text = json.dumps(records) + '\n'.join(errors)
        for raw in (NAME, episode):
            self.assertNotIn(raw, text)
        self.assertRegex(records[0][0]['attemptId'], r'^attempt-[0-9a-f]{16}$')
        self.assertRegex(records[4][0]['attemptId'], r'^episode-[0-9a-f]{16}$')
        self.assertEqual(records[0], adapter.rollout_triplets(self.home, 'run-1', NAME))  # stable per run salt
        self.assertEqual(errors, ['No events for the attempt', 'Host transcript refused',
                                  'Loom stream refused: execution-authorization', 'System One episodes refused'])

    def test_a_raw_id_in_an_output_is_detected(self):
        """Negative control: an adapter that kept the raw attempt id would fail the leak check."""
        real = adapter._pseudonym
        with patch.object(adapter, '_pseudonym', lambda salt, value, kind='turn': value if kind == 'attempt'
                          else real(salt, value, kind)):
            records, errors, _ = self.outputs()
        self.assertIn(NAME, json.dumps(records) + '\n'.join(errors))


if __name__ == '__main__':
    unittest.main()
