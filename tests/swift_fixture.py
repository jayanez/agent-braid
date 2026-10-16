# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded host-only Swift builds, with module preparation measured separately."""
import atexit
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time


def run_phase(command, phase, timeout):
    """Drain bounded diagnostics and terminate the owned compiler group on failure."""
    started = time.monotonic()
    tail = bytearray()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               start_new_session=(os.name == 'posix'))

    def drain():
        while chunk := process.stdout.read(4096):
            tail.extend(chunk)
            del tail[:-8192]

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    failure = None
    interruption = None
    try:
        process.wait(timeout=timeout)
        reader.join(timeout=5)
        if reader.is_alive():
            failure = 'diagnostic pipe did not close'
        elif process.returncode:
            failure = f'exit {process.returncode}'
    except subprocess.TimeoutExpired:
        failure = f'timeout after {timeout}s'
    except BaseException as error:
        failure = 'interrupted'
        interruption = error
    finally:
        if failure:
            if os.name == 'posix':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            elif process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            reader.join(timeout=5)
        if not reader.is_alive():
            process.stdout.close()
    detail = (f'Swift {phase}: elapsed={time.monotonic() - started:.3f}s '
              f'limit={timeout}s command={command!r}\n'
              f'{bytes(tail).decode("utf-8", "replace")}')
    print(detail, file=sys.stderr, flush=True)
    if interruption is not None:
        raise interruption
    if failure:
        raise RuntimeError(f'{failure}; {detail}')


class SwiftFixtureCompiler:
    """One private module cache per test process; fixture sources are never cached."""

    def __init__(self, compiler):
        self.compiler = compiler
        self.directory = tempfile.TemporaryDirectory(prefix='braid-swift-modules-')
        self.root = Path(self.directory.name)
        self.ready = False
        self.failure = None

    def compile(self, source, binary):
        if self.failure is not None:
            raise RuntimeError('Earlier Swift preparation failed; no retry') from self.failure
        options = [self.compiler, '-v', '-module-cache-path', str(self.root / 'cache')]
        if not self.ready:
            try:
                run_phase([self.compiler, '--version'], 'toolchain', 5)
                bootstrap = self.root / 'main.swift'
                bootstrap.write_text('import Foundation\nimport Dispatch\n')
                run_phase([*options, str(bootstrap), '-o', str(self.root / 'bootstrap')],
                          'module preparation', 180)
                self.ready = True
            except Exception as error:
                self.failure = error
                raise
        run_phase([*options, str(source), '-o', str(binary)], 'fixture compilation', 60)


_compiler = None


def compile_swift(source, binary):
    global _compiler
    if _compiler is None:
        _compiler = SwiftFixtureCompiler(shutil.which('swiftc'))
        atexit.register(_compiler.directory.cleanup)
    _compiler.compile(source, binary)
