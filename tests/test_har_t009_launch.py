# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 headless lab launcher (``scripts/har_t009_launch.sh``): argument validation and install pins.

Nothing native runs here: every case stops before ``launchctl``, ``sudo``, the driver or ``claude``. The launcher
refuses before its root check for bad arguments and an uninstalled template, and at its root check otherwise;
these tests never run as root (skipped then), so they never reach ``launchctl asuser``.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "har_t009_launch.sh"
QUICKSTART = ROOT / "specs" / "065-native-claude-containment" / "quickstart.md"
BASH = shutil.which("bash") or "/bin/bash"
PINS = {"COMMIT": "0" * 40, "CLAUDE_SHA256": "a" * 64, "PYTHON_SHA256": "b" * 64,
        "SANDBOX_EXEC_SHA256": "c" * 64, "OPERATOR_ACCOUNT": "founder"}
# the install pipeline of quickstart.md "Headless own-session mode", step H2 (kept in sync by a test below)
INSTALL_SED = ('sed -e "s/@COMMIT@/$COMMIT/" -e "s/@CLAUDE_SHA256@/$CLAUDE_SHA256/" '
               '-e "s/@PYTHON_SHA256@/$PYTHON_SHA256/" \\\n'
               '    -e "s/@SANDBOX_EXEC_SHA256@/$SANDBOX_EXEC_SHA256/" '
               '-e "s/@OPERATOR_ACCOUNT@/$OPERATOR_ACCOUNT/" \\\n'
               '    "$B/repo-$SHORT/scripts/har_t009_launch.sh"')


@unittest.skipIf(os.geteuid() == 0, "the launcher must never get past its root check in a test")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-launch-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_launcher(self, *args, script=LAUNCHER):
        # an empty environment and a scratch working directory: nothing of the developer's shell is used
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin"}, cwd=self.tmp)

    def installed(self, **pins) -> Path:
        """The template with the pins filled in by the exact sed pipeline of the quickstart."""
        values = PINS | pins
        command = "B=$1; SHORT=x; " + INSTALL_SED.replace('"$B/repo-$SHORT/scripts/har_t009_launch.sh"', '"$2"')
        out = self.tmp / "t009-launch.sh"
        done = subprocess.run([BASH, "-c", command + ' > "$3"', "sh", "/nowhere", str(LAUNCHER), str(out)],
                              capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin", **values})
        self.assertEqual(done.returncode, 0, done.stderr)
        return out

    def refused(self, result, text):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STOP:", result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("==", result.stdout)  # nothing was started

    def test_the_template_parses(self):
        done = subprocess.run([BASH, "-n", str(LAUNCHER)], capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_usage_and_mode_are_validated_first(self):
        self.refused(self.run_launcher(), "usage:")
        self.refused(self.run_launcher("check"), "usage:")
        self.refused(self.run_launcher("check", "t009-20261113b", "extra"), "usage:")
        for mode in ("CHECK", "self-check", "run2", "", "check;id"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t009-20261113b"), "mode must be")
        self.refused(self.run_launcher("__lab", "t009-20261113b"), "internal entry misused")

    def test_the_attempt_label_is_one_closed_shape(self):
        for attempt in ("t009-2026111b", "t009-20261113", "t009-20261113ab", "t009-20261113B", "T009-20261113b",
                        "t009-20261113b;id", "t009-20261113b\n", "../t009-20261113b", "t009-20261113-b",
                        "t009-20261113b ", "$(id)", ""):
            with self.subTest(attempt=attempt):
                self.refused(self.run_launcher("check", attempt), "ATTEMPT must match")

    def test_the_uninstalled_template_refuses_before_anything(self):
        for mode in ("check", "diag", "run"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t009-20261113b"), "pins not installed")

    def test_malformed_pins_refuse(self):
        for pins in (dict(COMMIT="0" * 39), dict(CLAUDE_SHA256="A" * 64), dict(PYTHON_SHA256="b" * 63),
                     dict(SANDBOX_EXEC_SHA256="g" * 64), dict(OPERATOR_ACCOUNT="Founder"),
                     dict(OPERATOR_ACCOUNT="braidlab")):
            with self.subTest(pins=pins):
                self.refused(self.run_launcher("check", "t009-20261113b", script=self.installed(**pins)),
                             "pins not installed")

    def test_an_installed_copy_still_needs_root_and_then_its_own_path(self):
        script = self.installed()
        self.assertNotRegex(script.read_text(), r"@[A-Z0-9_]+@")  # every placeholder was filled
        for mode in ("check", "diag", "run"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t009-20261113b", script=script), "run it with sudo")

    def test_the_lab_half_refuses_any_account_but_the_lab_account(self):
        script = self.installed()
        self.refused(self.run_launcher("__lab", "check", "t009-20261113b", script=script), "only as braidlab")
        self.refused(self.run_launcher("__lab", "run", "bad", script=script), "internal entry misused")
        self.refused(self.run_launcher("__lab", "check", "t009-20261113b", script=LAUNCHER), "pins not installed")

    def test_the_launcher_starts_the_lab_in_its_own_session_with_a_clean_environment(self):
        text = LAUNCHER.read_text()
        self.assertIn('exec /bin/launchctl asuser "$LAB_UID" /usr/bin/sudo -u "$ACCOUNT" /usr/bin/env -i', text)
        self.assertIn('"$py" -B -I "$driver"', text)
        self.assertIn("set -u -o pipefail", text)
        self.assertIn("PATH=/usr/bin:/bin:/usr/sbin:/sbin", text)
        # it reads no configuration from any other file and evaluates nothing
        for line in text.splitlines():
            stripped = line.strip()
            self.assertFalse(re.match(r"(source|\.)\s", stripped), line)
            self.assertNotIn("eval ", stripped)
        # the token of diag never goes through a process's arguments
        self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN="$(cat', text)
        self.assertIn('CLAUDE_CODE_OAUTH_TOKEN=$(< "$2/oauth-token")', text)

    def test_the_quickstart_installs_with_the_same_pipeline_and_a_narrow_rule(self):
        text = QUICKSTART.read_text()
        self.assertIn(INSTALL_SED, text)
        self.assertIn("ALL=(root) NOPASSWD:", text)
        self.assertIn("visudo -cf", text)
        self.assertIn("/usr/local/libexec/braid/t009-launch.sh check *, /usr/local/libexec/braid/t009-launch.sh diag *",
                      text)
        self.assertNotIn("t009-launch.sh run *", text)  # run always asks for the owner's password


if __name__ == "__main__":
    unittest.main()
