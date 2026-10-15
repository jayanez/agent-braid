# SPDX-License-Identifier: AGPL-3.0-only
"""Own PTY only: source parsing must finish before serial admission is read."""
import os
from pathlib import Path
import pty
import json
import re
import subprocess
import select
import signal
import time
import unittest


ROOT = Path(__file__).resolve().parents[1] / 'scripts/forecast_engine_probe'


def framed(script):
    binary = os.environ.get('FC2_TEST_SERIAL_WRAPPER')
    if binary:
        return subprocess.run([binary], input=script, capture_output=True, check=True, timeout=1).stdout
    # CI without the macOS compiler still exercises the exact literal framing
    # from the shared Swift source, not an independently maintained toy prefix.
    source = (ROOT / 'SerialGuestProgram.swift').read_text()
    prefix = re.search(r'var program = Data\((".*")\.utf8\)', source).group(1)
    suffix = re.search(r'program.append\(Data\((".*")\.utf8\)\)', source).group(1)
    return json.loads(prefix).encode() + script + json.loads(suffix).encode()


class SerialAdmissionTests(unittest.TestCase):
    def probe(self, wrap, token=b'FC2_ADMIT_OWN_DAEMON_CRASH'):
        guest = (ROOT / 'guest_engine_probe.sh').read_text()
        admission = guest.split('# BEGIN PURE ADMISSION CHECK\n')[1].split('# END PURE ADMISSION CHECK')[0]
        # Use the actual guest admission function/read/call shape. Everything
        # outside admission is a synthetic print; no guest/daemon command runs.
        read = 'IFS= read -r -t 3 fc2_token < /dev/tty\n'
        source = ('set -e\nfc2_emit() { printf "\\nEVENT=%s:%s\\n" "$1" "$2"; }\n'
                  'printf "\\nFC2_WAITING_FOR_TOKEN\\n"\n' + read +
                  '# BEGIN PURE ADMISSION CHECK\n' + admission +
                  '# END PURE ADMISSION CHECK\n'
                  'printf "\\nOBSERVED_TOKEN=%s\\n" "$fc2_token"\n'
                  'fc2_require_crash_admission "$fc2_token"\n'
                  'printf "\\nSYNTHETIC_DISPATCH\\n"\nexit 0\n').encode()
        pid, descriptor = pty.fork()
        if pid == 0:
            os.execl('/bin/bash', 'bash', '--noprofile', '--norc', '-i')
        output = bytearray(); status = None; sent = False
        try:
            os.write(descriptor, wrap(source))
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                if select.select([descriptor], [], [], .05)[0]:
                    try:
                        data = os.read(descriptor, 4096)
                    except OSError:
                        break
                    if not data:
                        break
                    output.extend(data)
                    self.assertLess(len(output), 65536)
                    if b'\r\nFC2_WAITING_FOR_TOKEN\r\n' in output and not sent:
                        # Deliberately allow the old unframed read to consume
                        # queued source before sending genuine host admission.
                        time.sleep(.05)
                        try:
                            os.write(descriptor, token + b'\n')
                        except OSError:
                            pass
                        sent = True
                child, value = os.waitpid(pid, os.WNOHANG)
                if child:
                    status = value
                    # Drain already emitted proof after exit, within deadline.
            if status is None:
                child, value = os.waitpid(pid, os.WNOHANG)
                if child:
                    status = value
        finally:
            if status is None:
                os.kill(pid, signal.SIGKILL)
                _, status = os.waitpid(pid, 0)
            os.close(descriptor)
        return os.waitstatus_to_exitcode(status), bytes(output)

    def test_native_transport_uses_the_shared_serial_program(self):
        shared = (ROOT / 'SerialGuestProgram.swift').read_text()
        native = (ROOT / 'main.swift.in').read_text()
        self.assertIn(shared, native)
        self.assertIn('sendBoundedInput(serialGuestProgram(script), to:', native)
        self.assertNotIn('sendBoundedInput(script, to:', native)

    def test_framed_guest_reads_host_admission_before_synthetic_dispatch(self):
        code, output = self.probe(framed)
        self.assertEqual(0, code, output)
        self.assertIn(b'\r\nOBSERVED_TOKEN=FC2_ADMIT_OWN_DAEMON_CRASH\r\n', output)
        self.assertIn(b'\r\nSYNTHETIC_DISPATCH\r\n', output)

    def test_raw_v7_shape_consumes_source_instead_of_host_admission(self):
        code, output = self.probe(lambda source: source)
        self.assertNotEqual(0, code, output)
        self.assertIn(b'\r\nOBSERVED_TOKEN=# BEGIN PURE ADMISSION CHECK\r\n', output)
        self.assertNotIn(b'\r\nSYNTHETIC_DISPATCH\r\n', output)

    def test_framed_abort_never_dispatches(self):
        code, output = self.probe(framed, b'FC2_ABORT_OWN_DAEMON_CRASH')
        self.assertEqual(2, code, output)
        self.assertIn(b'\r\nEVENT=hostPreflightRejected:yes\r\n', output)
        self.assertNotIn(b'\r\nSYNTHETIC_DISPATCH\r\n', output)
