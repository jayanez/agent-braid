# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic host-only serial cancellation; no Virtualization or daemon."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'scripts/forecast_engine_probe'


@unittest.skipUnless(shutil.which('swiftc'), 'Swift compiler unavailable: serial cancellation unexecuted')
class SerialCancellationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory(prefix='fc2-pure-cancellation-')
        cls.addClassCleanup(directory.cleanup)
        cls.binary = Path(directory.name) / 'gate'
        source = Path(directory.name) / 'main.swift'
        source.write_text((ROOT / 'SerialInputGate.swift').read_text() + '''
let gate = SerialInputGate()
let mode = CommandLine.arguments[1]
let output = Pipe()
func sender() -> Bool {
    output.fileHandleForWriting.write(Data("FC2_ADMIT_OWN_DAEMON_CRASH\\n".utf8))
    return true
}
if mode == "queued" {
    // Validated readiness is queued, but cancellation wins before dispatch.
    let queue = DispatchQueue(label: "owned-admission")
    queue.suspend()
    let done = DispatchSemaphore(value: 0)
    queue.async { _ = gate.sendIfActive(sender); done.signal() }
    gate.cancel()
    queue.resume()
    guard done.wait(timeout: .now() + 2) == .success else { exit(2) }
} else if mode == "active" {
    guard gate.sendIfActive(sender) else { exit(3) }
    gate.cancel()
    guard !gate.sendIfActive(sender) else { exit(4) }
} else if mode == "inflight" {
    let entered = DispatchSemaphore(value: 0)
    let release = DispatchSemaphore(value: 0)
    let completed = DispatchSemaphore(value: 0)
    DispatchQueue.global().async {
        _ = gate.sendIfActive {
            entered.signal()
            guard release.wait(timeout: .now() + 2) == .success else { return false }
            return sender()
        }
        completed.signal()
    }
    guard entered.wait(timeout: .now() + 2) == .success else { exit(5) }
    // Cancellation contends with the known in-flight writer, never sleeps.
    let cancelStarted = DispatchSemaphore(value: 0)
    let cancelled = DispatchSemaphore(value: 0)
    DispatchQueue.global().async {
        cancelStarted.signal(); gate.cancel(); cancelled.signal()
    }
    guard cancelStarted.wait(timeout: .now() + 2) == .success else { exit(6) }
    release.signal()
    guard completed.wait(timeout: .now() + 2) == .success,
          cancelled.wait(timeout: .now() + 2) == .success,
          !gate.sendIfActive(sender) else { exit(7) }
} else { exit(8) }
try output.fileHandleForWriting.close()
FileHandle.standardOutput.write(output.fileHandleForReading.readDataToEndOfFile())
''')
        subprocess.run([shutil.which('swiftc'), str(source), '-o', str(cls.binary)],
                       capture_output=True, check=True, timeout=60)

    def emitted(self, mode):
        return subprocess.run([str(self.binary), mode], capture_output=True,
                              check=True, timeout=5).stdout

    def test_cancel_before_queued_admission_emits_no_token(self):
        self.assertEqual(b'', self.emitted('queued'))

    def test_active_write_emits_once_then_cancellation_refuses(self):
        self.assertEqual(b'FC2_ADMIT_OWN_DAEMON_CRASH\n', self.emitted('active'))

    def test_inflight_write_precedes_cancel_and_no_later_write_starts(self):
        self.assertEqual(b'FC2_ADMIT_OWN_DAEMON_CRASH\n', self.emitted('inflight'))

    def test_native_writes_share_gate_and_cleanup_deadline_precedes_cancel(self):
        source = (ROOT / 'main.swift.in').read_text()
        self.assertIn((ROOT / 'SerialInputGate.swift').read_text(), source)
        self.assertEqual(3, source.count('serialInputGate.sendIfActive'))
        # Every runtime sender has a gate (definition itself is the fourth hit).
        self.assertEqual(4, source.count('sendBoundedInput('))
        stop = source[source.index('func stop() {'):source.index('let reader =')]
        self.assertLess(stop.index('let cleanupDeadline'), stop.index('serialInputGate.cancel()'))
        self.assertLess(stop.index('asyncAfter(deadline: cleanupDeadline)'), stop.index('serialInputGate.cancel()'))
        self.assertLess(stop.index('serialInputGate.cancel()'), stop.index('machine.stop'))
