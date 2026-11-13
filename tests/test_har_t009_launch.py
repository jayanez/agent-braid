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
import sys
import stat
import tempfile
import time
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
        self.assertIn('/bin/launchctl asuser "$LAB_UID" /usr/bin/sudo -u "$ACCOUNT" /usr/bin/env -i', text)
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


def functions(*names: str) -> str:
    """The source of top-level shell functions of the launcher, from ``name() {`` to the closing ``}``."""
    text = LAUNCHER.read_text()
    parts = []
    for name in names:
        match = re.search(r"^%s\(\) \{\n.*?^\}\n" % re.escape(name), text, re.M | re.S)
        assert match, name
        parts.append(match.group(0))
    return "\n".join(parts)


@unittest.skipIf(os.geteuid() == 0, "run as an ordinary account")
@unittest.skipUnless(sys.platform == "darwin", "the launcher uses BSD stat(1); it only runs on macOS")
class PublishTests(unittest.TestCase):
    """Finding 1 of the re-check of #1338: results reach /Users/Shared only through the lab account's own directory,
    by fresh temporary names and renames, never through a path another user could plant."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-pub-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.pub = self.tmp / "pub"
        self.secret = self.tmp / "oauth-token"
        self.secret.write_text("SECRET")
        os.chmod(self.secret, 0o600)
        self.src = self.tmp / "result.json"
        self.src.write_text('{"verdict": "ready"}')

    def shell(self, body: str):
        script = ("set -u -o pipefail\nstop() { printf 'STOP: %s\\n' \"$1\" >&2; exit 2; }\n"
                  f"PUB={self.pub}\n" + functions("prepare_pub", "publish", "publish_tree") + body)
        return subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin"}, cwd=self.tmp)

    def assert_secret_untouched(self):
        self.assertEqual(self.secret.read_text(), "SECRET")
        self.assertEqual(stat.S_IMODE(self.secret.stat().st_mode), 0o600)

    def test_the_directory_is_created_private_to_writes_and_a_file_is_published_by_rename(self):
        done = self.shell(f"prepare_pub\npublish {self.src} dry-run.json\npublish {self.src} dry-run.json\n")
        self.assertEqual(done.returncode, 0, done.stderr)
        info = self.pub.stat()
        self.assertEqual((info.st_uid, stat.S_IMODE(info.st_mode)), (os.getuid(), 0o755))
        out = self.pub / "dry-run.json"
        self.assertEqual(out.read_text(), self.src.read_text())
        self.assertEqual(stat.S_IMODE(out.stat().st_mode), 0o644)
        self.assertEqual(sorted(os.listdir(self.pub)), ["dry-run.json"])  # no temporary file left

    def test_a_planted_symlink_is_refused_and_never_followed(self):
        self.pub.mkdir(mode=0o755)
        for name in ("diag.txt", "dry-run.json"):
            (self.pub / name).symlink_to(self.secret)
            done = self.shell(f"prepare_pub\npublish {self.src} {name}\n")
            self.assertEqual(done.returncode, 2, done.stderr)
            self.assertIn("not a regular file", done.stderr)
            self.assert_secret_untouched()
        (self.pub / "bundle-t009-20261113b").symlink_to(self.tmp)
        done = self.shell(f"prepare_pub\npublish_tree {self.tmp} bundle-t009-20261113b\n")
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assert_secret_untouched()

    def test_a_directory_in_place_of_a_file_is_refused(self):
        (self.pub / "diag.txt").mkdir(parents=True)
        os.chmod(self.pub, 0o755)
        done = self.shell(f"prepare_pub\npublish {self.src} diag.txt\n")
        self.assertEqual(done.returncode, 2, done.stderr)

    def test_a_publish_directory_that_is_a_link_or_shared_is_refused(self):
        self.pub.symlink_to(self.tmp)
        done = self.shell("prepare_pub\n")
        self.assertEqual(done.returncode, 2)
        self.assertIn("not a real directory", done.stderr)
        self.pub.unlink()
        self.pub.mkdir()
        for mode in (0o775, 0o757, 0o777):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.pub, mode)
                done = self.shell("prepare_pub\n")
                self.assertEqual(done.returncode, 2)
                self.assertIn("writable by others", done.stderr)

    def test_a_bundle_tree_is_published_whole_and_replaces_the_old_one(self):
        bundle = self.tmp / "out"
        (bundle / "sub").mkdir(parents=True)
        (bundle / "summary.json").write_text("{}")
        (bundle / "sub" / "x").write_text("x")
        os.chmod(bundle / "summary.json", 0o600)
        done = self.shell(f"prepare_pub\npublish_tree {bundle} bundle-a\npublish_tree {bundle} bundle-a\n")
        self.assertEqual(done.returncode, 0, done.stderr)
        out = self.pub / "bundle-a"
        self.assertEqual(sorted(p.relative_to(out).as_posix() for p in out.rglob("*")),
                         ["sub", "sub/x", "summary.json"])
        self.assertTrue(stat.S_IMODE((out / "summary.json").stat().st_mode) & 0o004)
        self.assertEqual(sorted(os.listdir(self.pub)), ["bundle-a"])

    def test_the_lab_half_never_writes_a_fixed_shared_path(self):
        text = LAUNCHER.read_text()
        self.assertNotIn("/Users/Shared/t009", text)
        self.assertNotIn("SHARED", text)
        self.assertIn("PUB=/Users/Shared/braid-t009-lab", text)
        self.assertIn('out=$(mktemp "$LAB_HOME/t009/diag-XXXXXX")', text)


@unittest.skipUnless(Path("/usr/bin/lockf").exists(), "lockf(1) is the macOS primitive the launcher uses")
class LockTests(unittest.TestCase):
    """Finding 2: one lab step at a time, through lockf(1) held by the root half for the whole step."""

    def test_the_root_half_tests_then_holds_the_lock_around_the_whole_step(self):
        text = LAUNCHER.read_text()
        self.assertIn("LOCK=$BRAID/.t009-launch.lock", text)
        probe = text.index('/usr/bin/lockf -k -s -t 0 "$LOCK" /usr/bin/true || stop "another lab step is running')
        hold = text.index('exec /usr/bin/lockf -k -t 0 "$LOCK" /bin/launchctl asuser')
        root = text.index('root_owned "$INSTALLED" ||')
        self.assertLess(root, probe)
        self.assertLess(probe, hold)
        self.assertEqual(text.count("exec /"), 1)  # the held lock wraps the only way the step starts

    def test_lockf_refuses_at_once_while_held_and_frees_when_the_holder_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = os.path.join(tmp, "lock")
            ready = os.path.join(tmp, "ready")
            holder = subprocess.Popen(["/usr/bin/lockf", "-k", "-t", "0", lock, "/bin/sh", "-c",
                                       f": > {ready}; sleep 30"])
            try:
                for _ in range(200):
                    if os.path.exists(ready):
                        break
                    time.sleep(0.05)
                self.assertTrue(os.path.exists(ready))
                busy = subprocess.run(["/usr/bin/lockf", "-k", "-s", "-t", "0", lock, "/usr/bin/true"])
                self.assertNotEqual(busy.returncode, 0)
            finally:
                holder.kill()
                holder.wait()
            free = subprocess.run(["/usr/bin/lockf", "-k", "-s", "-t", "0", lock, "/usr/bin/true"])
            self.assertEqual(free.returncode, 0)  # the kernel dropped it: no stale lock after a crash


def quickstart_block(step: str) -> str:
    """The first ``sh`` code block after the bold step heading ``**Step <step>.``."""
    text = QUICKSTART.read_text()
    start = text.index(f"**Step {step}.")
    body = text.index("```sh\n", start) + len("```sh\n")
    return text[body:text.index("```", body)]


class QuickstartInstallTests(unittest.TestCase):
    """Finding 3: the pasted install blocks stop at the first bad pin, before any sudo."""

    SHELLS = [s for s in (BASH, "/bin/zsh") if Path(s).exists()]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-qs-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = self.tmp / "bin"
        fake.mkdir()
        self.log = self.tmp / "sudo.log"
        (fake / "sudo").write_text(f"#!/bin/sh\necho \"$*\" >> {self.log}\nexit 0\n")
        os.chmod(fake / "sudo", 0o755)
        self.path = f"{fake}:/usr/bin:/bin"

    def run_block(self, shell, block):
        return subprocess.run([shell, "-c", block], capture_output=True, text=True, timeout=30,
                              env={"PATH": self.path, "HOME": str(self.tmp)}, cwd=self.tmp)

    def test_h1_and_h2_are_one_subshell_that_stops_on_errors(self):
        for step in ("H1", "H2"):
            block = quickstart_block(step).strip()
            with self.subTest(step=step):
                self.assertTrue(block.startswith("( set -euo pipefail"), block[:40])
                self.assertTrue(block.endswith(")"))
                before_sudo = block[:block.index("sudo ")]
                self.assertIn("stop()", before_sudo)

    def test_h1_stops_at_each_bad_pin_before_any_sudo(self):
        block = quickstart_block("H1")
        good = {"COMMIT": "0" * 40, "CLAUDE_SHA256": "a" * 64, "PYTHON_SHA256": "b" * 64,
                "SANDBOX_EXEC_SHA256": "c" * 64}
        placeholders = {"COMMIT": "PASTE_THE_40_CHARACTER_COMMIT_FROM_THE_ORCHESTRATOR",
                        "CLAUDE_SHA256": "PASTE_64_HEX_FROM_STEP_8_CLAUDE",
                        "PYTHON_SHA256": "PASTE_64_HEX_FROM_STEP_8_PYTHON",
                        "SANDBOX_EXEC_SHA256": "PASTE_64_HEX_FROM_STEP_8_SANDBOX_EXEC"}
        cases = {"as pasted, unfilled": {}}
        for name in good:
            cases[f"only {name} wrong"] = {k: v for k, v in good.items() if k != name} | {name: good[name][:-1]}
        cases["all pins right, no code copy at that commit"] = dict(good)
        for shell in self.SHELLS:
            for label, values in cases.items():
                with self.subTest(shell=shell, case=label):
                    text = block
                    for name, value in values.items():
                        text = text.replace(f"{name}='{placeholders[name]}'", f"{name}='{value}'")
                    done = self.run_block(shell, text)
                    self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
                    self.assertIn("STOP:", done.stdout + done.stderr)
                    self.assertFalse(self.log.exists(), self.log.read_text() if self.log.exists() else "")

    def test_h1_reports_the_installed_hash_and_the_orchestrator_can_render_it(self):
        block = quickstart_block("H1")
        self.assertIn('shasum -a 256 "$B/t009-launch.sh"', block)
        text = QUICKSTART.read_text()
        render = text[text.index("Render the expected launcher"):]
        self.assertIn('show "$COMMIT:scripts/har_t009_launch.sh"', render)
        for name in PINS:
            self.assertIn(f'-e "s/@{name}@/${name}/"', render)
        self.assertIn("shasum -a 256", render)


if __name__ == "__main__":
    unittest.main()
