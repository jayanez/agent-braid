# SPDX-License-Identifier: AGPL-3.0-only
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PluginInstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.log = self.base / 'calls'
        self.env = dict(os.environ, PATH=str(self.base) + ':/usr/bin:/bin', PLUGIN_TEST_LOG=str(self.log))

    def host(self, name):
        path = self.base / name
        path.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$PLUGIN_TEST_LOG"\n')
        path.chmod(0o755)

    def run_installer(self, *args):
        return subprocess.run(['/bin/sh', str(ROOT / 'install.sh'), *args], env=self.env,
                              capture_output=True, text=True, stdin=subprocess.DEVNULL)

    def test_no_host_refuses_without_installation(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_both_are_explicit_user_scoped_and_never_launch_a_session(self):
        self.host('codex'); self.host('claude')
        result = self.run_installer('--host', 'both', '--marketplace', '/a local catalog')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text()
        self.assertIn('codex plugin marketplace add /a local catalog', calls)
        self.assertIn('codex plugin add agent-braid@agent-braid', calls)
        self.assertIn('claude plugin install agent-braid --marketplace /a local catalog --scope user', calls)
        self.assertNotIn(' exec ', calls)
        self.assertNotIn(' -p ', calls)

    def test_missing_second_host_is_checked_before_any_mutation(self):
        self.host('codex')
        result = self.run_installer('--host', 'both')
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_noninteractive_ambiguous_host_refuses_and_dry_run_does_not_execute(self):
        self.host('codex'); self.host('claude')
        self.assertEqual(self.run_installer().returncode, 2)
        result = self.run_installer('--host', 'both', '--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.log.exists())

    def test_repeated_installs_use_the_same_native_selection(self):
        self.host('codex')
        for _ in range(2):
            self.assertEqual(self.run_installer('--host', 'codex').returncode, 0)
        lines = self.log.read_text().splitlines()
        self.assertEqual(lines[:2], lines[2:])

    def test_explicit_ref_is_independent_of_option_order(self):
        self.host('codex'); self.host('claude')
        for options in [('--ref', 'release', '--marketplace', '/catalog'),
                        ('--marketplace', '/catalog', '--ref', 'release')]:
            self.log.unlink(missing_ok=True)
            result = self.run_installer('--host', 'both', *options)
            self.assertEqual(result.returncode, 0, result.stderr)
            calls = self.log.read_text()
            self.assertIn('marketplace add /catalog --ref release', calls)
            self.assertIn('--marketplace /catalog#release --scope user', calls)

    def test_option_shaped_values_are_rejected_before_native_calls(self):
        self.host('codex')
        self.assertEqual(self.run_installer('--marketplace', '--help').returncode, 2)
        self.assertFalse(self.log.exists())
