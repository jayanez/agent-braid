# SPDX-License-Identifier: AGPL-3.0-only
"""Optional real socat + synthetic Unix HTTP peer; never contacts Docker."""
import os
import json
from pathlib import Path
import re
import shlex
import select
import socket
import subprocess
import tempfile
import threading
import time
import unittest


@unittest.skipUnless(os.environ.get('FC2_TEST_SOCAT'), 'explicit isolated socat binary required')
class SyntheticHTTPTransportTests(unittest.TestCase):
    def guest_options(self):
        guest = (Path(__file__).resolve().parents[1] / 'scripts/forecast_engine_probe/guest_engine_probe.sh').read_text()
        return shlex.split(re.search(r'/usr/bin/socat (.*?) "UNIX-CONNECT:', guest).group(1))

    def exchange(self, options):
        observed = {}
        with tempfile.TemporaryDirectory(prefix='fc2-http-', dir='/tmp') as tmp:
            address = str(Path(tmp) / 'owned.sock')
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(address); listener.listen(1); listener.settimeout(2)

                def serve():
                    with listener.accept()[0] as conn:
                        conn.settimeout(2)
                        request = b''
                        while b'\r\n\r\n' not in request:
                            part = conn.recv(4096)
                            if not part:
                                raise ValueError('incomplete-synthetic-request')
                            request += part
                        # Simulate a server watching client cancellation during
                        # delayed work. This is not a reproduction of dockerd.
                        readable, _, _ = select.select([conn], [], [], .3)
                        observed['prematureEof'] = bool(readable and conn.recv(1) == b'')
                        body = b'null' if observed['prematureEof'] else b'[]'
                        conn.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)

                thread = threading.Thread(target=serve, daemon=True); thread.start()
                result = subprocess.run([os.environ['FC2_TEST_SOCAT'], *options,
                                         'UNIX-CONNECT:' + address],
                                        input=b'GET /info HTTP/1.0\r\nHost: synthetic\r\nConnection: close\r\n\r\n',
                                        capture_output=True, timeout=1)
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(0, result.returncode, result.stderr)
        return observed, result.stdout

    def test_guest_options_hold_stdin_eof_until_delayed_response_finishes(self):
        guest = (Path(__file__).resolve().parents[1] / 'scripts/forecast_engine_probe/guest_engine_probe.sh').read_text()
        self.assertIn('/usr/bin/timeout -k1 1', guest)
        observed, response = self.exchange(self.guest_options())
        self.assertFalse(observed['prematureEof'])
        self.assertTrue(response.endswith(b'[]'))

    def test_old_transport_exposes_early_eof_to_the_synthetic_server(self):
        observed, response = self.exchange(['-T0.2', '-'])
        self.assertTrue(observed['prematureEof'])
        self.assertTrue(response.endswith(b'null'))

    def fragmented_exchange(self, options):
        # The failed run retained exactly 4096 bytes. A second delayed block
        # must survive even when stdout is writable and request stdin is EOF.
        body = json.dumps({'ID': 'synthetic', 'padding': 'x' * 14000}).encode()
        response = b'HTTP/1.0 200 OK\r\n\r\n' + body
        errors = []
        with tempfile.TemporaryDirectory(prefix='fc2-http-', dir='/tmp') as tmp:
            address = str(Path(tmp) / 'owned.sock')
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(address); listener.listen(1); listener.settimeout(2)

                def serve():
                    try:
                        with listener.accept()[0] as conn:
                            conn.settimeout(2)
                            request = b''
                            while b'\r\n\r\n' not in request:
                                part = conn.recv(4096)
                                if not part:
                                    raise ValueError('incomplete-synthetic-request')
                                request += part
                            conn.sendall(response[:4096])
                            time.sleep(.9)
                            conn.sendall(response[4096:])
                    except Exception as error:
                        errors.append(error)

                thread = threading.Thread(target=serve, daemon=True); thread.start()
                result = subprocess.run([os.environ['FC2_TEST_SOCAT'], *options,
                                         'UNIX-CONNECT:' + address],
                                        input=b'GET /info HTTP/1.0\r\nHost: synthetic\r\nConnection: close\r\n\r\n',
                                        capture_output=True, timeout=2)
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(0, result.returncode, result.stderr)
                return response, result, errors

    def test_guest_transport_drains_fragmented_http_larger_than_one_read(self):
        # The .9s gap exceeds the old .8s inactivity threshold. The 2s host
        # safety timer is for this comparative test, not a guest limit change.
        for options, complete in [(self.guest_options(), True),
                                  (['-t0.05', '-T0.8', 'STDIO,ignoreeof'], False)]:
            with self.subTest(options=options):
                response, result, errors = self.fragmented_exchange(options)
                if complete:
                    self.assertEqual(response, result.stdout)
                    self.assertEqual([], errors)
                else:
                    self.assertEqual(response[:4096], result.stdout)
                    self.assertTrue(all(isinstance(error, (BrokenPipeError, ConnectionResetError))
                                        for error in errors), errors)

    def test_unresponsive_peer_requires_the_outer_deadline_and_is_reaped(self):
        # No inner inactivity timeout may report success for a partial reply.
        # This host timer exercises the same caller-deadline responsibility;
        # the guest's unchanged GNU timeout command is checked separately.
        with tempfile.TemporaryDirectory(prefix='fc2-http-', dir='/tmp') as tmp:
            address = str(Path(tmp) / 'owned.sock')
            with socket.socket(socket.AF_UNIX) as listener:
                listener.bind(address); listener.listen(1); listener.settimeout(2)
                release = threading.Event()
                request_seen = threading.Event()

                def serve():
                    with listener.accept()[0] as conn:
                        conn.settimeout(2)
                        request = b''
                        while b'\r\n\r\n' not in request:
                            part = conn.recv(4096)
                            if not part:
                                return
                            request += part
                        request_seen.set()
                        release.wait(2)

                thread = threading.Thread(target=serve, daemon=True); thread.start()
                try:
                    with self.assertRaises(subprocess.TimeoutExpired):
                        subprocess.run([os.environ['FC2_TEST_SOCAT'], *self.guest_options(),
                                        'UNIX-CONNECT:' + address], input=b'GET /info HTTP/1.0\r\n\r\n',
                                       capture_output=True, timeout=.3)
                finally:
                    release.set(); thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertTrue(request_seen.is_set(), 'deadline test never reached the owned peer')
