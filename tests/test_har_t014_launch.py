# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T014 headless launcher (``scripts/har_t014_launch.sh``) and its owner install
(``scripts/har_t014_install.sh``): siblings of the reviewed T008 pair, with a closed code delta.

Nothing native runs here: every case stops before ``launchctl``, ``sudo``, the driver or ``claude``. The code lines of
each T014 script must equal the T008 script's after a fixed list of name substitutions, so every helper function stays
byte-identical and any other change fails here and needs its own review. These tests never run as root.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from tests.test_har_t008_launch import BASH, PLACEHOLDER, PINS, functions, render

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "har_t014_launch.sh"
INSTALLER = ROOT / "scripts" / "har_t014_install.sh"
T008_LAUNCHER = ROOT / "scripts" / "har_t008_launch.sh"
T008_INSTALLER = ROOT / "scripts" / "har_t008_install.sh"
T009_LAUNCHER = ROOT / "scripts" / "har_t009_launch.sh"
HELPERS = ("root_owned", "auth_status", "prepare_pub", "publish", "no_token", "lab")
# The whole reviewed delta from the T008 code lines (comments excluded): names, the label and the messages
LAUNCHER_DELTA = (
    ("har_t008_unit.py", "har_t014_cohort.py"), ("har_t008_install.sh", "har_t014_install.sh"),
    ("t008-launch.sh", "t014-launch.sh"), ("braid-t008-lab", "braid-t014-lab"), ("^t008-", "^t014-"),
    ("t008-YYYYMMDDx", "t014-YYYYMMDDx"), ("$LAB_HOME/t008", "$LAB_HOME/t014"),
    ("T008 COHORT $attempt (at most 4 serial Haiku units)", "T014 COHORT $attempt (serial Haiku units in the "
     "registered order)"),
    ("(T008 or T009)", "(T008, T009 or T014)"),
)
INSTALLER_DELTA = (
    ("har_t008_launch.sh", "har_t014_launch.sh"), ("t008-launch.sh", "t014-launch.sh"),
    ("t008-install", "t014-install"), ("braid-t008", "braid-t014"), ("check t008-[", "check t014-["),
    ("a T008 or T009 lab step", "a T008, T009 or T014 lab step"),
    ("grep -E 't00[89]-launch'", "grep -E 't0(08|09|14)-launch'"),
)


def code(text: str) -> list[str]:
    """Lines that are not comments, with trailing comments removed (the delta is reviewed on code only)."""
    out = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        out.append(re.sub(r"\s{2,}# .*$", "", line))
    return out


def substituted(text: str, delta) -> str:
    for old, new in delta:
        text = text.replace(old, new)
    return text


class DeltaTests(unittest.TestCase):
    def test_the_launcher_is_the_t008_launcher_with_the_reviewed_delta_only(self):
        self.assertEqual(code(LAUNCHER.read_text()), code(substituted(T008_LAUNCHER.read_text(), LAUNCHER_DELTA)))

    def test_the_installer_is_the_t008_installer_with_the_reviewed_delta_only(self):
        self.assertEqual(code(INSTALLER.read_text()), code(substituted(T008_INSTALLER.read_text(), INSTALLER_DELTA)))

    def test_shared_helpers_are_byte_identical(self):
        ours = functions(LAUNCHER, *HELPERS)
        t008 = functions(T008_LAUNCHER, *HELPERS)
        for name in ("root_owned", "auth_status", "prepare_pub", "publish", "no_token"):
            self.assertEqual(ours[name], t008[name], name)
        # the lab half differs only by the reviewed names
        self.assertEqual(ours["lab"], substituted(t008["lab"], LAUNCHER_DELTA))
        names = ("root_owned", "auth_status", "prepare_pub", "publish")
        self.assertEqual(functions(LAUNCHER, *names), functions(T009_LAUNCHER, *names))
        for line in ("stop() { printf 'STOP: %s\\n' \"$1\" >&2; exit 2; }",
                     'valid_mode() { case "$1" in check|run) return 0 ;; *) return 1 ;; esac; }'):
            self.assertIn(line, LAUNCHER.read_text())
            self.assertIn(line, T008_LAUNCHER.read_text())

    def test_same_lab_lock_new_publish_directory_and_driver(self):
        text = LAUNCHER.read_text()
        self.assertRegex(text, re.compile(r"^LOCK=\$BRAID/\.t009-launch\.lock", re.M))
        self.assertIn("PUB=/Users/Shared/braid-t014-lab", text)
        self.assertIn("local driver=$BRAID/repo-$short/scripts/har_t014_cohort.py", text)
        self.assertIn("INSTALLED=$BRAID/t014-launch.sh", text)
        self.assertNotIn("t008", "\n".join(code(text)))
        self.assertTrue((ROOT / "scripts" / "har_t014_cohort.py").is_file())

    def test_the_rule_is_check_only_for_t014_labels(self):
        text = INSTALLER.read_text()
        self.assertIn("RULE=/etc/sudoers.d/braid-t014", text)
        self.assertIn('"$LAUNCHER check t014-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][a-z]"', text)
        self.assertNotIn("check *", text)
        self.assertNotIn("run t014", text)
        code_lines = code(text)
        self.assertFalse([line for line in code_lines if "braid-t008" in line or "braid-t009" in line])


@unittest.skipIf(os.geteuid() == 0, "the launcher must never get past its root check in a test")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t014-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_launcher(self, *args, script=LAUNCHER):
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin"}, cwd=self.tmp)

    def installed(self, **pins) -> Path:
        return render(LAUNCHER, self.tmp / "t014-launch.sh", **pins)

    def refused(self, result, text):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STOP:", result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("==", result.stdout)

    def test_the_templates_parse(self):
        for script in (LAUNCHER, INSTALLER):
            done = subprocess.run([BASH, "-n", str(script)], capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_usage_mode_and_label_are_validated_first(self):
        self.refused(self.run_launcher(), "usage: t014-launch.sh")
        self.refused(self.run_launcher("diag", "t014-20261220a"), "mode must be")
        for attempt in ("t008-20261220a", "t009-20261220a", "t014-2026122a", "t014-20261220ab", "T014-20261220a",
                        "t014-20261220a;id", "../t014-20261220a", "$(id)", ""):
            with self.subTest(attempt=attempt):
                self.refused(self.run_launcher("check", attempt), "ATTEMPT must match t014-YYYYMMDDx")
        self.refused(self.run_launcher("__lab", "t014-20261220a"), "internal entry misused")

    def test_the_uninstalled_template_and_malformed_pins_refuse(self):
        for mode in ("check", "run"):
            self.refused(self.run_launcher(mode, "t014-20261220a"), "har_t014_install.sh")
        for pins in (dict(COMMIT="0" * 39), dict(CLAUDE_SHA256="A" * 64), dict(OPERATOR_ACCOUNT="braidlab")):
            with self.subTest(pins=pins):
                self.refused(self.run_launcher("check", "t014-20261220a", script=self.installed(**pins)),
                             "pins not installed")

    def test_an_installed_copy_still_needs_root_and_the_lab_half_only_the_lab_account(self):
        script = self.installed()
        self.assertNotRegex(script.read_text(), PLACEHOLDER)
        self.refused(self.run_launcher("run", "t014-20261220a", script=script), "run it with sudo")
        self.refused(self.run_launcher("__lab", "check", "t014-20261220a", script=script), "only as braidlab")
        self.refused(self.run_launcher("__lab", "run", "t008-20261220a", script=script), "internal entry misused")


@unittest.skipIf(os.geteuid() == 0, "run as an ordinary account")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t014-install-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = self.tmp / "bin"
        fake.mkdir()
        self.log = self.tmp / "sudo.log"
        for tool in ("sudo", "git"):
            (fake / tool).write_text(f"#!/bin/sh\necho \"{tool} $*\" >> {self.log}\nexit 0\n")
            os.chmod(fake / tool, 0o755)
        self.path = f"{fake}:/usr/bin:/bin"
        self.user = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()

    def install(self, *args, **pins):
        script = render(INSTALLER, self.tmp / "t014-install.sh", **pins)
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, timeout=30,
                              env={"PATH": self.path, "HOME": str(self.tmp)}, cwd=self.tmp)

    def stopped_before_sudo(self, done, text):
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn(text, done.stderr)
        self.assertFalse(self.log.exists(), self.log.read_text() if self.log.exists() else "")

    def test_bad_pins_another_account_or_the_unpinned_lab_stop_before_any_sudo(self):
        self.stopped_before_sudo(subprocess.run([BASH, str(INSTALLER)], capture_output=True, text=True, timeout=30,
                                                env={"PATH": self.path}, cwd=self.tmp), "COMMIT is not rendered")
        self.stopped_before_sudo(self.install(COMMIT="0" * 39), "COMMIT")
        other = "someoneelse" if self.user != "someoneelse" else "nobodyhere"
        self.stopped_before_sudo(self.install(OPERATOR_ACCOUNT=other), "rendered for")
        if re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", self.user) and self.user != "braidlab":
            self.stopped_before_sudo(self.install("x", OPERATOR_ACCOUNT=self.user), "usage: bash t014-install.sh")
            self.stopped_before_sudo(self.install(OPERATOR_ACCOUNT=self.user), "does not match its pin")

    def test_the_installer_renders_the_t014_launcher_exactly(self):
        script = render(INSTALLER, self.tmp / "t014-install.sh").read_text()
        start = script.index('sed -e "s/[@]COMMIT[@]/')
        end = script.index('\\\n  | sudo tee "$STAGE/t014-launch.sh"', start)
        command = script[start:end].replace("\\\n", " ") + '< "$1"'
        pins = {"COMMIT": "1" * 40, "CLAUDE_SHA256": "2" * 64, "PYTHON_SHA256": "3" * 64,
                "SANDBOX_EXEC_SHA256": "4" * 64, "OPERATOR_ACCOUNT": "owner"}
        ours = subprocess.run([BASH, "-c", command, "sh", str(LAUNCHER)], capture_output=True, text=True,
                              timeout=30, env={"PATH": "/usr/bin:/bin", **pins})
        self.assertEqual(ours.returncode, 0, ours.stderr)
        self.assertEqual(ours.stdout, render(LAUNCHER, self.tmp / "expected.sh", **pins).read_text())
        self.assertEqual(set(PINS), set(pins))


if __name__ == "__main__":
    unittest.main()
