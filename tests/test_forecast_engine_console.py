# SPDX-License-Identifier: AGPL-3.0-only
"""Compile only the pure Foundation parser; never imports Virtualization."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_forecast_engine_probe import console, events, http
from tests.swift_fixture import compile_swift

ROOT = Path(__file__).resolve().parents[1] / 'scripts/forecast_engine_probe'


@unittest.skipUnless(shutil.which('swiftc'), 'Swift compiler unavailable: pure native parser not executed')
class NativeConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = tempfile.TemporaryDirectory(prefix='fc2-pure-console-')
        cls.addClassCleanup(directory.cleanup)
        cls.binary = Path(directory.name) / 'parser'
        source = Path(directory.name) / 'main.swift'
        # Compile the current runtime parser itself, not the historical copied
        # parser in an old preparation artifact or a separately maintained fake.
        source.write_text((ROOT / 'NativeEnginePreflight.swift').read_text() + '''
let input = FileHandle.standardInput.readDataToEndOfFile()
let rows = try JSONSerialization.jsonObject(with: input) as! [String]
let results = rows.map { ["preflight": nativeEnginePreflight($0),
                         "ready": enginePrerequisiteReady($0),
                         "done": engineCompletionSeen($0)] }
let output = try JSONSerialization.data(withJSONObject: results)
FileHandle.standardOutput.write(output)
''')
        compile_swift(source, cls.binary)

    def inspect(self, *samples):
        result = subprocess.run([str(self.binary)], input=json.dumps(samples).encode(),
                                capture_output=True, check=True, timeout=3)
        return json.loads(result.stdout)

    def evaluate(self, *samples):
        return [row['preflight'] for row in self.inspect(*samples)]

    def test_valid_lf_and_crlf_require_the_same_strict_preflight(self):
        sample = console(events())
        self.assertEqual([True, True], self.evaluate(sample, sample.replace('\n', '\r\n')))

    def test_truncated_multiblock_info_never_admits(self):
        sample = events()
        sample['infoHttp'] = http({'padding': 'x' * 14000})[:4096]
        self.assertEqual([False], self.evaluate(console(sample).replace('\n', '\r\n')))

    def test_native_runtime_embeds_the_reviewed_parser_source(self):
        self.assertIn((ROOT / 'NativeEnginePreflight.swift').read_text(), (ROOT / 'main.swift.in').read_text())
        self.assertIn((ROOT / 'NativeEnginePreflight.swift').read_text(), (ROOT / 'native_preflight_test.swift').read_text())
        source = (ROOT / 'main.swift.in').read_text()
        self.assertIn('enginePrerequisiteReady(text)', source)
        self.assertIn('engineCompletionSeen(text)', source)
        self.assertIn('guestCompletionSeen = true; stop(); return', source)

    def test_markers_wait_for_complete_lf_or_crlf_records(self):
        for separator in ['\n', '\r\n']:
            ready = 'FC2_ENGINE_EVENT prerequisiteReady eWVz'
            done = 'FC2_ENGINE_QUALIFICATION_DONE'
            chunks = ['boot' + separator, ready, '\r' if separator == '\r\n' else '', '\n',
                      done, '\r' if separator == '\r\n' else '', '\n']
            prefixes = [''.join(chunks[:index]) for index in range(1, len(chunks) + 1)]
            rows = self.inspect(*prefixes)
            self.assertEqual([False, False, False, True, True, True, True], [row['ready'] for row in rows])
            self.assertEqual([False, False, False, False, False, False, True], [row['done'] for row in rows])

    def test_large_valid_response_is_accepted_but_truncated_response_refuses(self):
        sample = events()
        # Add padding to the valid info object while retaining required fields.
        from tests.test_forecast_engine_probe import protocol
        info = protocol.http_json(sample['infoHttp']); info['padding'] = 'x' * 14000
        sample['infoHttp'] = http(info)
        valid = console(sample).replace('\n', '\r\n')
        sample['infoHttp'] = sample['infoHttp'][:4096]
        self.assertEqual([True, False], self.evaluate(valid, console(sample).replace('\n', '\r\n')))

    def test_marker_lookalikes_cannot_admit_or_stop(self):
        text = 'printf "FC2_ENGINE_QUALIFICATION_DONE"\r\n> FC2_ENGINE_EVENT prerequisiteReady eWVz\r\n'
        self.assertEqual([{'ready': False, 'done': False, 'preflight': False}], self.inspect(text))

    @unittest.skipUnless(os.environ.get('FC2_RETAINED_ENGINE_CONSOLE'), 'explicit private retained console required')
    def test_retained_failed_run_is_still_refused(self):
        text = Path(os.environ['FC2_RETAINED_ENGINE_CONSOLE']).read_bytes().decode('utf-8')
        self.assertEqual([{'preflight': False, 'ready': True, 'done': True}], self.inspect(text))
