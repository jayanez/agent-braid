# SPDX-License-Identifier: AGPL-3.0-only
"""Optional real socat + synthetic Unix HTTP peer; never contacts Docker."""
import os
from pathlib import Path
import select
import socket
import subprocess
import tempfile
import threading
import unittest


@unittest.skipUnless(os.environ.get('FC2_TEST_SOCAT'), 'explicit isolated socat binary required')
class SyntheticHTTPTransportTests(unittest.TestCase):
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
        self.assertIn('socat -t0.05 -T0.8 STDIO,ignoreeof', guest)
        observed, response = self.exchange(['-t0.05', '-T0.8', 'STDIO,ignoreeof'])
        self.assertFalse(observed['prematureEof'])
        self.assertTrue(response.endswith(b'[]'))

    def test_old_transport_exposes_early_eof_to_the_synthetic_server(self):
        observed, response = self.exchange(['-T0.2', '-'])
        self.assertTrue(observed['prematureEof'])
        self.assertTrue(response.endswith(b'null'))
