# SPDX-License-Identifier: AGPL-3.0-only
"""Compiler orchestration regressions; no VM, Docker or model."""
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from tests.swift_fixture import SwiftFixtureCompiler, run_phase


class SwiftFixtureTests(unittest.TestCase):
    def compiler(self):
        compiler = SwiftFixtureCompiler('/owned/swiftc')
        self.addCleanup(compiler.directory.cleanup)
        return compiler

    def test_prepare_once_but_compile_every_current_source_with_shared_cache(self):
        compiler = self.compiler()
        with patch('tests.swift_fixture.run_phase') as run:
            compiler.compile('gate.swift', 'gate')
            compiler.compile('parser.swift', 'parser')
        self.assertEqual(['toolchain', 'module preparation', 'fixture compilation',
                          'fixture compilation'], [c.args[1] for c in run.call_args_list])
        self.assertEqual([5, 180, 60, 60], [c.args[2] for c in run.call_args_list])
        preparation, first, second = [c.args[0] for c in run.call_args_list[1:]]
        self.assertEqual(preparation[:4], first[:4])
        self.assertEqual(first[:4], second[:4])
        self.assertEqual(['gate.swift', '-o', 'gate'], first[4:])
        self.assertEqual(['parser.swift', '-o', 'parser'], second[4:])
        self.assertEqual('import Foundation\nimport Dispatch\n',
                         (compiler.root / 'main.swift').read_text())

    def test_failed_preparation_is_not_retried_or_converted_to_skip(self):
        compiler = self.compiler()
        with patch('tests.swift_fixture.run_phase',
                   side_effect=[None, RuntimeError('cold compilation failed')]) as run:
            with self.assertRaisesRegex(RuntimeError, 'cold compilation failed'):
                compiler.compile('gate.swift', 'gate')
            with self.assertRaisesRegex(RuntimeError, 'no retry'):
                compiler.compile('parser.swift', 'parser')
        self.assertEqual(2, run.call_count)
        self.assertFalse(compiler.ready)

    def test_failed_fixture_is_not_retried(self):
        compiler = self.compiler()
        with patch('tests.swift_fixture.run_phase',
                   side_effect=[None, None, RuntimeError('type check failed')]) as run:
            with self.assertRaisesRegex(RuntimeError, 'type check failed'):
                compiler.compile('gate.swift', 'gate')
        self.assertEqual(3, run.call_count)

    def test_nonzero_compiler_retains_diagnostic_and_phase(self):
        with redirect_stderr(io.StringIO()) as log:
            with self.assertRaisesRegex(RuntimeError, 'exit 7; Swift fixture compilation'):
                run_phase([sys.executable, '-c',
                           'import sys; print("compiler diagnostic"); sys.exit(7)'],
                          'fixture compilation', 2)
        self.assertIn('compiler diagnostic', log.getvalue())
        self.assertIn('limit=2s', log.getvalue())

    def test_large_output_is_drained_with_bounded_tail(self):
        with redirect_stderr(io.StringIO()) as log:
            run_phase([sys.executable, '-c',
                       'print("x" * 1048576); print("diagnostic-end")'], 'test', 2)
        self.assertIn('diagnostic-end', log.getvalue())
        self.assertLess(len(log.getvalue()), 9000)

    @unittest.skipUnless(os.name == 'posix', 'owned process groups require POSIX')
    def test_timeout_kills_compiler_and_descendant_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            ready = Path(directory) / 'child-ready'
            child = ('import os,time,pathlib; '
                     f'pathlib.Path({str(ready)!r}).write_text(str(os.getpid())); time.sleep(30)')
            parent = ('import subprocess,sys,time; '
                      f'subprocess.Popen([sys.executable,"-c",{child!r}]); '
                      'print("frontend-started",flush=True); time.sleep(30)')
            launch = subprocess.Popen

            def launch_with_timeout(*args, **kwargs):
                process = launch(*args, **kwargs)
                wait = process.wait

                def timeout_after_ready(timeout):
                    if timeout == 10:
                        deadline = time.monotonic() + 5
                        while (not ready.exists() or not ready.read_text()) and time.monotonic() < deadline:
                            time.sleep(.01)
                        self.assertTrue(ready.exists() and ready.read_text(),
                                        'child readiness was not observed')
                        raise subprocess.TimeoutExpired(args[0], timeout)
                    return wait(timeout=timeout)

                process.wait = timeout_after_ready
                return process

            try:
                with patch('tests.swift_fixture.subprocess.Popen', side_effect=launch_with_timeout):
                    with redirect_stderr(io.StringIO()) as log:
                        with self.assertRaisesRegex(RuntimeError, 'timeout after 10s'):
                            run_phase([sys.executable, '-c', parent], 'fixture compilation', 10)
                self.assertIn('frontend-started', log.getvalue())
                child_pid = int(ready.read_text())
                status = subprocess.run(['ps', '-p', str(child_pid), '-o', 'stat='],
                                        capture_output=True, text=True, timeout=5).stdout.strip()
                # Linux may retain a dead orphan as a zombie until init reaps it.
                self.assertTrue(not status or status.startswith('Z'),
                                f'compiler descendant still running: {status}')
            finally:
                if ready.exists():
                    try:
                        os.kill(int(ready.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass

    def test_interruption_preserves_exception_and_emits_diagnostics(self):
        process = unittest.mock.Mock()
        process.stdout = io.BytesIO(b'compiler context before interruption')
        process.wait.side_effect = [KeyboardInterrupt('operator stop'), 0]
        process.pid = 123456
        with patch('tests.swift_fixture.subprocess.Popen', return_value=process), \
                patch('tests.swift_fixture.os.killpg') as kill, \
                redirect_stderr(io.StringIO()) as log:
            with self.assertRaisesRegex(KeyboardInterrupt, 'operator stop'):
                run_phase(['synthetic-compiler'], 'fixture compilation', 60)
        if os.name == 'posix':
            kill.assert_called_once_with(process.pid, signal.SIGKILL)
        self.assertIn('compiler context before interruption', log.getvalue())
        self.assertIn('Swift fixture compilation: elapsed=', log.getvalue())
