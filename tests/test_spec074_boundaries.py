# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-008 / SC-008 (T010): every trace-consent path opens no socket, launches nothing and stays local.

The CLI paths SPEC-074 adds or extends (init preview and apply, validate, status, sweep, purge) and every adapter
reader run with sockets and process launchers replaced by recorders that refuse. Standard-library-only imports and
the import closure are checked by `tests/test_lightning_cli.py` (same procedure).
"""
from contextlib import contextmanager
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
from agent_braid import mcp_runtime
from agent_braid.lightning_schema import EVENT_SCHEMA, Event, LightningSchemaError
from tests.test_lightning_adapter import (EMAIL, LOOM, SALT, T0, TOKEN, cli, episode_line, request, reward,
                                          trace_bytes)

ROOT = Path(__file__).resolve().parents[1]
GUARDED = ((socket, 'socket'), (socket, 'create_connection'), (socket, 'getaddrinfo'), (subprocess, 'Popen'),
           (os, 'system'), (os, 'posix_spawn'), (os, 'posix_spawnp'), (os, 'fork'), (os, 'execv'), (os, 'execve'))


@contextmanager
def no_network_or_process():
    """Replace every socket and process entry point with a recorder that refuses; yields the record."""
    calls = []

    def refusing(name):
        def call(*args, **kwargs):
            calls.append(name)
            raise AssertionError(f'{name} called')
        return call
    patches = [patch.object(module, name, refusing(f'{module.__name__}.{name}')) for module, name in GUARDED]
    for item in patches:
        item.start()
    try:
        yield calls
    finally:
        for item in reversed(patches):
            item.stop()


class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def lightning(self, *args):
        code, out, err = cli('lightning', *args, '--home', str(self.home))
        self.assertEqual(code, 0, (args, err))
        value = json.loads(out)
        self.assertIs(value['executionAuthorization'], False, args)
        return value

    def attempt(self):
        run = store.RunStore(self.home, 'run-1')
        run.create(config_digest='c' * 64, now=T0)
        for item in (request(1), reward(2, 0.5)):
            run.append('event', item)
        run.append('trace', {'attemptId': 'at-1', 'sequence': 1, 'prompt': f'mail {EMAIL}',
                             'response': f'key {TOKEN}'}, now=T0 + 1)
        return run

    def read_every_source(self):
        trace, episodes = self.base / 'trace.json', self.base / 'day.jsonl'
        trace.write_bytes(trace_bytes())
        episodes.write_bytes(episode_line())
        data = LOOM.read_bytes()
        return [adapter.rollout_triplets(self.home, 'run-1', 'at-1'),
                adapter.rollout_messages(self.home, 'run-1', 'at-1'),
                adapter.loom_triplets(self.home, data, SALT), adapter.loom_messages(self.home, data, SALT),
                adapter.transcript_triplets(self.home, trace, SALT),
                adapter.transcript_messages(self.home, trace, SALT),
                adapter.system_one_triplets(self.home, episodes, SALT),
                adapter.system_one_messages(self.home, episodes, SALT)]

    def test_every_cli_path_and_reader_opens_no_socket_and_launches_nothing(self):
        init = ['init', '--non-interactive', '--trace-consent', 'redacted', '--trace-sources',
                'rollout,host-transcript,loom,system-one']
        with no_network_or_process() as calls:
            preview = self.lightning(*init)
            self.lightning(*init, '--apply', '--preview-digest', preview['previewDigest'])
            self.attempt()
            outputs = [self.lightning('validate'), self.lightning('status'), self.lightning('sweep'),
                       self.lightning('purge', '--expired')]
            records = self.read_every_source()
            plan = self.lightning('purge', '--run-id', 'run-1')
            outputs.append(self.lightning('purge', '--run-id', 'run-1', '--apply', '--preview-digest',
                                          plan['previewDigest']))
        self.assertEqual(calls, [])
        self.assertTrue(all(record for record in records))
        self.assertTrue(records[0][0]['prompt'])  # the readers ran with consent, so content was read
        for value in (*outputs, plan, records):
            self.assertNotIn(TOKEN, json.dumps(value))
            self.assertNotIn(EMAIL, json.dumps(value))

    def test_a_socket_call_is_detected(self):
        """Negative control: a reader that opens a socket fails under the recorders."""
        real = adapter.loom_triplets

        def calling_home(home, data, salt):
            socket.create_connection(('127.0.0.1', 9))
            return real(home, data, salt)
        with no_network_or_process() as calls, patch.object(adapter, 'loom_triplets', calling_home):
            with self.assertRaises(AssertionError):
                adapter.loom_triplets(self.home, LOOM.read_bytes(), SALT)
        self.assertEqual(calls, ['socket.create_connection'])

    def test_a_process_launch_is_detected(self):
        """Negative control: a CLI path that launches a process fails under the recorders."""
        with no_network_or_process() as calls, patch.object(adapter, 'gate',
                                                            lambda home: subprocess.run(['true'])):
            with self.assertRaises(AssertionError):
                cli('lightning', 'status', '--home', str(self.home))
        self.assertEqual(calls, ['subprocess.Popen'])

    def test_telemetry_stays_content_free(self):
        """Event, rollout and result records carry no content; content lives only in the redacted trace file."""
        preview = self.lightning('init', '--non-interactive', '--trace-consent', 'redacted', '--trace-sources',
                                 'rollout')
        self.lightning('init', '--non-interactive', '--trace-consent', 'redacted', '--trace-sources', 'rollout',
                       '--apply', '--preview-digest', preview['previewDigest'])
        run = self.attempt()
        telemetry = [path for path in run.root.iterdir() if path.name in store.KINDS.values()]
        self.assertTrue(telemetry)
        for path in telemetry:
            text = path.read_text()
            for marker in (TOKEN, EMAIL, 'mail ', '"prompt"', '"response"', 'REDACTED'):
                self.assertNotIn(marker, text, path.name)
        self.assertIn('REDACTED', (run.root / store.CONTENT_FILE).read_text())  # the content went to its own file
        with self.assertRaises(LightningSchemaError):  # the event schema admits no content field
            Event.parse({'schema': EVENT_SCHEMA, 'rolloutId': 'ro-1', 'attemptId': 'at-1', 'sequence': 9,
                         'eventType': 'model_request', 'timestamp': T0,
                         'data': {**request(1).to_dict()['data'], 'prompt': 'text'}})

    def test_no_mcp_tool_reaches_lightning(self):
        self.assertFalse([tool for tool in mcp_runtime.TOOLS if 'lightning' in tool])
        servers = sorted((ROOT / 'agent_braid').glob('*mcp*.py'))  # every MCP server and tool module
        self.assertTrue(servers)
        self.assertEqual([path.name for path in servers if 'lightning' in path.read_text().lower()], [])


if __name__ == '__main__':
    unittest.main()
