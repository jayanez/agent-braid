# SPDX-License-Identifier: AGPL-3.0-only
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

from scripts.reproduce_native_plugin import codex_inventory


class NativeProbeDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_notifications_cannot_reset_the_overall_probe_deadline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            host = root / 'fake-host'
            marker = root / 'pid'
            host.write_text(f'#!{sys.executable}\n' +
                'import json,os,time\n' +
                f'open({str(marker)!r}, "w").write(str(os.getpid()))\n' +
                'while True:\n print(json.dumps({"method":"unrelated"}),flush=True)\n time.sleep(0.03)\n')
            host.chmod(0o755)
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                await codex_inventory(host, dict(os.environ), root, timeout_seconds=1.0)
            self.assertLess(time.monotonic() - started, 3)
            with self.assertRaises(ProcessLookupError):
                os.kill(int(marker.read_text()), 0)
