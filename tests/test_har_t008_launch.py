# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-048 T008 headless launcher (``scripts/har_t008_launch.sh``) and its owner install
(``scripts/har_t008_install.sh``): argument validation, pins, shared lab lock, rendering.

Nothing native runs here: every case stops before ``launchctl``, ``sudo``, the driver or ``claude``. The launcher
refuses before its root check for bad arguments and an uninstalled template, and at its root check otherwise; the
installer refuses before its first ``sudo`` (a fake ``sudo`` on PATH records any call). These tests never run as
root (skipped then).
"""
from hashlib import sha256
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "har_t008_launch.sh"
INSTALLER = ROOT / "scripts" / "har_t008_install.sh"
T009_LAUNCHER = ROOT / "scripts" / "har_t009_launch.sh"
PACKET = ROOT / "specs" / "048-harness-variant-laboratory" / "evidence" / "engineering" / "t008-owner-packet.md"
# production runs /bin/bash (3.2 on macOS); use it whenever it exists, never a newer bash first on PATH
BASH = "/bin/bash" if Path("/bin/bash").exists() else shutil.which("bash")
# the template hash SPEC-065 T013 evidence binds (evidence/t013.json inputs); T008 must not move it
T009_LAUNCHER_SHA256 = "b14933019be52e029a6754ce99277f502b626141462129ea9e6a876f4d29f4a4"
PINS = {"COMMIT": "0" * 40, "CLAUDE_SHA256": "a" * 64, "PYTHON_SHA256": "b" * 64,
        "SANDBOX_EXEC_SHA256": "c" * 64, "OPERATOR_ACCOUNT": "founder"}
# the rendering the orchestrator uses for both templates (the owner packet repeats it; a test keeps them equal)
RENDER_SED = ('sed -e "s/@COMMIT@/$COMMIT/" -e "s/@CLAUDE_SHA256@/$CLAUDE_SHA256/" '
              '-e "s/@PYTHON_SHA256@/$PYTHON_SHA256/" \\\n'
              '      -e "s/@SANDBOX_EXEC_SHA256@/$SANDBOX_EXEC_SHA256/" '
              '-e "s/@OPERATOR_ACCOUNT@/$OPERATOR_ACCOUNT/"')
PLACEHOLDER = re.compile(r"@[A-Z0-9_]+@")


def render(template: Path, out: Path, **pins) -> Path:
    """The template with the pins filled in by the orchestrator's sed pipeline."""
    done = subprocess.run([BASH, "-c", RENDER_SED + ' < "$1" > "$2"', "sh", str(template), str(out)],
                          capture_output=True, text=True, timeout=30, env={"PATH": "/usr/bin:/bin", **(PINS | pins)})
    assert done.returncode == 0, done.stderr
    return out


def functions(path: Path, *names: str) -> dict:
    """The source of top-level shell functions, from ``name() {`` to the closing ``}``."""
    text = path.read_text()
    found = {}
    for name in names:
        match = re.search(r"^%s\(\) \{\n.*?^\}\n" % re.escape(name), text, re.M | re.S)
        assert match, name
        found[name] = match.group(0)
    return found


@unittest.skipIf(os.geteuid() == 0, "the launcher must never get past its root check in a test")
class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t008-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def run_launcher(self, *args, script=LAUNCHER):
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, timeout=30,
                              env={"PATH": "/usr/bin:/bin"}, cwd=self.tmp)

    def installed(self, **pins) -> Path:
        return render(LAUNCHER, self.tmp / "t008-launch.sh", **pins)

    def refused(self, result, text):
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("STOP:", result.stderr)
        self.assertIn(text, result.stderr)
        self.assertNotIn("==", result.stdout)  # nothing was started

    def test_the_template_parses(self):
        for script in (LAUNCHER, INSTALLER):
            done = subprocess.run([BASH, "-n", str(script)], capture_output=True, text=True, timeout=30)
            self.assertEqual(done.returncode, 0, done.stderr)

    def test_usage_and_mode_are_validated_first(self):
        self.refused(self.run_launcher(), "usage:")
        self.refused(self.run_launcher("check"), "usage:")
        self.refused(self.run_launcher("check", "t008-20261114a", "extra"), "usage:")
        for mode in ("diag", "CHECK", "self-check", "run2", "", "check;id"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t008-20261114a"), "mode must be")
        self.refused(self.run_launcher("__lab", "t008-20261114a"), "internal entry misused")

    def test_the_attempt_label_is_one_closed_shape(self):
        for attempt in ("t009-20261114a", "t008-2026111a", "t008-20261114", "t008-20261114ab", "t008-20261114A",
                        "T008-20261114a", "t008-20261114a;id", "t008-20261114a\n", "../t008-20261114a",
                        "t008-20261114-a", "t008-20261114a ", "$(id)", ""):
            with self.subTest(attempt=attempt):
                self.refused(self.run_launcher("check", attempt), "ATTEMPT must match")

    def test_the_uninstalled_template_refuses_before_anything(self):
        for mode in ("check", "run"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t008-20261114a"), "pins not installed")

    def test_malformed_pins_refuse(self):
        for pins in (dict(COMMIT="0" * 39), dict(CLAUDE_SHA256="A" * 64), dict(PYTHON_SHA256="b" * 63),
                     dict(SANDBOX_EXEC_SHA256="g" * 64), dict(OPERATOR_ACCOUNT="Founder"),
                     dict(OPERATOR_ACCOUNT="braidlab")):
            with self.subTest(pins=pins):
                self.refused(self.run_launcher("check", "t008-20261114a", script=self.installed(**pins)),
                             "pins not installed")

    def test_an_installed_copy_still_needs_root_and_then_its_own_path(self):
        script = self.installed()
        self.assertNotRegex(script.read_text(), PLACEHOLDER)
        for mode in ("check", "run"):
            with self.subTest(mode=mode):
                self.refused(self.run_launcher(mode, "t008-20261114a", script=script), "run it with sudo")

    def test_the_lab_half_refuses_any_account_but_the_lab_account(self):
        script = self.installed()
        self.refused(self.run_launcher("__lab", "check", "t008-20261114a", script=script), "only as braidlab")
        self.refused(self.run_launcher("__lab", "diag", "t008-20261114a", script=script), "internal entry misused")
        self.refused(self.run_launcher("__lab", "run", "t009-20261114a", script=script), "internal entry misused")
        self.refused(self.run_launcher("__lab", "check", "t008-20261114a", script=LAUNCHER), "pins not installed")


class LauncherShapeTests(unittest.TestCase):
    """Static properties: the same own-session start, lock and publishing as the SPEC-065 launcher, the lab paths
    the issued environment hash was taken with, and the T008 driver from the root-owned code copy."""

    text = LAUNCHER.read_text()

    def test_it_starts_the_lab_in_its_own_session_with_a_clean_environment(self):
        self.assertIn('/bin/launchctl asuser "$LAB_UID" /usr/bin/sudo -u "$ACCOUNT" /usr/bin/env -i', self.text)
        self.assertIn("set -u -o pipefail", self.text)
        self.assertIn("PATH=/usr/bin:/bin:/usr/sbin:/sbin", self.text)
        for line in self.text.splitlines():
            stripped = line.strip()
            self.assertFalse(re.match(r"(source|\.)\s", stripped), line)
            self.assertNotIn("eval ", stripped)
        self.assertIn('CLAUDE_CODE_OAUTH_TOKEN=$(< "$2/oauth-token")', self.text)

    def test_it_runs_the_t008_driver_from_the_root_owned_code_copy_on_the_qualified_lab_paths(self):
        self.assertIn("local driver=$BRAID/repo-$short/scripts/har_t008_unit.py", self.text)
        self.assertIn('root_owned "$driver" || stop', self.text)
        self.assertIn('local run=("$py" -B -I -u "$driver" "${args[@]}")', self.text)
        # config dir, run root and arena enter the environment hash: exactly those of the issued T009 bundle
        self.assertIn("local cfg=$LAB_HOME/t009/config", self.text)
        self.assertIn('--config-dir "$cfg" --run-root "$LAB_HOME/t009/run"', self.text)
        self.assertIn('--arena-parent "$LAB_HOME/t009/arena" --out-dir "$work/out/$attempt"', self.text)
        self.assertIn('CLAUDE_CONFIG_DIR="$LAB_HOME/t009/config"', self.text)
        self.assertIn('"${run[@]}" --dry-run', self.text)
        self.assertIn('"${run[@]}" --founder-go', self.text)
        self.assertNotIn("--self-check", self.text)

    def test_one_lock_for_t008_and_t009_held_around_the_whole_step(self):
        lock = re.search(r"^LOCK=\$BRAID/\.t009-launch\.lock", self.text, re.M)
        self.assertIsNotNone(lock)
        self.assertIn("LOCK=$BRAID/.t009-launch.lock", T009_LAUNCHER.read_text())
        probe = self.text.index('/usr/bin/lockf -k -s -t 0 "$LOCK" /usr/bin/true || stop "another lab step')
        hold = self.text.index('exec /usr/bin/lockf -k -t 0 "$LOCK" /bin/launchctl asuser')
        root = self.text.index('root_owned "$INSTALLED" ||')
        self.assertLess(root, probe)
        self.assertLess(probe, hold)
        self.assertEqual(self.text.count("exec /"), 1)

    def test_shared_helpers_are_the_reviewed_t009_bytes(self):
        # tests.test_har_t009_launch covers prepare_pub and publish by behaviour; root_owned is exercised below
        names = ("root_owned", "auth_status", "prepare_pub", "publish")
        self.assertEqual(functions(LAUNCHER, *names), functions(T009_LAUNCHER, *names))
        self.assertIn("PUB=/Users/Shared/braid-t008-lab", self.text)
        self.assertNotIn("/Users/Shared/t008", self.text)

    def test_run_needs_a_terminal_and_keeps_the_transcript_on_ctrl_c(self):
        run = self.text[self.text.index("    run)\n"):]
        self.assertLess(run.index("[ -t 0 ] || stop"), run.index('"${run[@]}" --founder-go'))
        # a handler, never an ignore, in the shell that starts the driver: an ignored SIGINT would be inherited
        # and the driver could not print its aborted report
        self.assertIn("trap ':' INT", run)
        self.assertIn("| (trap '' INT; exec tee \"$work/run-$attempt.txt\")", run)
        self.assertEqual(self.text.count("trap '' INT"), 1)
        self.assertIn('publish "$work/run-$attempt.txt" "run-$attempt.txt"', run)
        # a label runs once: its transcript is the cohort's evidence and is never truncated
        self.assertLess(run.index('[ ! -e "$work/run-$attempt.txt" ]'), run.index('"${run[@]}" --founder-go'))
        self.assertIn('tmp=$(mktemp -d "$work/auth-XXXXXX")', self.text)  # never inside the qualified run root

    def test_the_t009_launcher_is_untouched_by_t008(self):
        self.assertEqual(sha256(T009_LAUNCHER.read_bytes()).hexdigest(), T009_LAUNCHER_SHA256)


@unittest.skipUnless(sys.platform == "darwin", "root_owned uses BSD stat(1); the launcher only runs on macOS")
class RootOwnedTests(unittest.TestCase):
    def test_the_driver_check_accepts_root_owned_paths_only(self):
        script = "set -u\n" + functions(LAUNCHER, "root_owned")["root_owned"] + 'root_owned "$1"'
        check = lambda path: subprocess.run([BASH, "-c", script, "sh", path], timeout=30).returncode  # noqa: E731
        self.assertEqual(check("/bin/sh"), 0)
        with tempfile.TemporaryDirectory() as tmp:
            mine = Path(tmp) / "har_t008_unit.py"
            mine.write_text("")
            self.assertEqual(check(str(mine)), 1)
            (Path(tmp) / "link").symlink_to("/bin/sh")
            self.assertEqual(check(str(Path(tmp) / "link")), 1)


@unittest.skipIf(os.geteuid() == 0, "run as an ordinary account")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t008-install-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        fake = self.tmp / "bin"
        fake.mkdir()
        self.log = self.tmp / "sudo.log"
        for tool in ("sudo", "git"):  # any call is recorded, nothing runs
            (fake / tool).write_text(f"#!/bin/sh\necho \"{tool} $*\" >> {self.log}\nexit 0\n")
            os.chmod(fake / tool, 0o755)
        self.path = f"{fake}:/usr/bin:/bin"
        self.user = subprocess.run(["id", "-un"], capture_output=True, text=True).stdout.strip()

    def install(self, *args, **pins):
        script = render(INSTALLER, self.tmp / "t008-install.sh", **pins)
        return subprocess.run([BASH, str(script), *args], capture_output=True, text=True, timeout=30,
                              env={"PATH": self.path, "HOME": str(self.tmp)}, cwd=self.tmp)

    def stopped_before_sudo(self, done, text):
        self.assertNotEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("STOP:", done.stderr)
        self.assertIn(text, done.stderr)
        self.assertFalse(self.log.exists(), self.log.read_text() if self.log.exists() else "")

    def test_the_unrendered_template_stops_before_any_sudo(self):
        done = subprocess.run([BASH, str(INSTALLER)], capture_output=True, text=True, timeout=30,
                              env={"PATH": self.path}, cwd=self.tmp)
        self.stopped_before_sudo(done, "COMMIT is not rendered")

    def test_each_bad_pin_stops_before_any_sudo(self):
        for pins, text in ((dict(COMMIT="0" * 39), "COMMIT"), (dict(CLAUDE_SHA256="A" * 64), "SHA-256"),
                           (dict(PYTHON_SHA256="b" * 63), "SHA-256"), (dict(SANDBOX_EXEC_SHA256="g" * 64), "SHA-256"),
                           (dict(OPERATOR_ACCOUNT="Founder"), "OPERATOR_ACCOUNT"),
                           (dict(OPERATOR_ACCOUNT="braidlab"), "OPERATOR_ACCOUNT")):
            with self.subTest(pins=pins):
                self.stopped_before_sudo(self.install(**pins), text)

    def test_another_account_stops_before_any_sudo(self):
        other = "someoneelse" if self.user != "someoneelse" else "nobodyhere"
        self.stopped_before_sudo(self.install(OPERATOR_ACCOUNT=other), "rendered for")

    def test_arguments_or_a_lab_that_is_not_the_pinned_one_stop_before_any_fetch_or_sudo(self):
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", self.user) or self.user == "braidlab":
            self.skipTest("this account name is not one the installer accepts")
        self.stopped_before_sudo(self.install("/some/checkout", OPERATOR_ACCOUNT=self.user), "usage:")
        # the test pins never match the real lab copies (or the copies are absent, as on CI)
        self.stopped_before_sudo(self.install(OPERATOR_ACCOUNT=self.user), "does not match its pin")

    def test_rendering_the_installer_keeps_its_own_launcher_rendering_intact(self):
        script = render(INSTALLER, self.tmp / "t008-install.sh").read_text()
        self.assertNotRegex(script, PLACEHOLDER)
        start = script.index('sed -e "s/[@]COMMIT[@]/')
        end = script.index('"$STAGE/repo-$SHORT/scripts/har_t008_launch.sh"', start)
        command = script[start:end] + '"$1"'
        pins = {"COMMIT": "1" * 40, "CLAUDE_SHA256": "2" * 64, "PYTHON_SHA256": "3" * 64,
                "SANDBOX_EXEC_SHA256": "4" * 64, "OPERATOR_ACCOUNT": "owner"}
        # the installer's pins are the shell variables of the rendered copy; feed the same values
        ours = subprocess.run([BASH, "-c", command, "sh", str(LAUNCHER)], capture_output=True, text=True,
                              timeout=30, env={"PATH": "/usr/bin:/bin", **pins})
        self.assertEqual(ours.returncode, 0, ours.stderr)
        expected = render(LAUNCHER, self.tmp / "expected.sh", **pins).read_text()
        self.assertEqual(ours.stdout, expected)
        self.assertNotRegex(expected, PLACEHOLDER)

    def test_the_rule_is_check_only_and_the_t009_rule_is_left_alone(self):
        text = INSTALLER.read_text()
        self.assertIn('printf \'%s ALL=(root) NOPASSWD: %s\\n\' "$OPERATOR_ACCOUNT" "$LAUNCHER check t008-[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][a-z]"', text)
        self.assertNotIn("check *", text)  # sudoers `*` matches spaces and further arguments
        self.assertIn("RULE=/etc/sudoers.d/braid-t008", text)
        self.assertIn('sudo visudo -cf "$RULE.new"', text)
        self.assertNotIn("run *", text)
        code = [line for line in text.splitlines() if not line.lstrip().startswith("#")]
        self.assertFalse([line for line in code if "braid-t009" in line])
        self.assertIn("set -euo pipefail", text)
        before_fetch = text[:text.index("fresh_git fetch")]
        for check in ("COMMIT is not rendered", "rendered for", "usage:", "does not match its pin",
                      "is not a root-owned directory closed to others"):
            self.assertIn(check, before_fetch)
        self.assertNotRegex(before_fetch, re.compile(r"^\s*(\S+\s*\|\s*)?sudo\s", re.M))  # no sudo command yet

    def test_the_code_is_fetched_by_commit_into_a_fresh_repository(self):
        text = INSTALLER.read_text()
        self.assertIn("REPOSITORY=https://github.com/jayanez/agent-braid.git", text)
        self.assertIn("GIT_ENV=(/usr/bin/env -i PATH=/usr/bin:/bin HOME=/var/empty GIT_CONFIG_NOSYSTEM=1", text)
        self.assertIn("GIT_NO_REPLACE_OBJECTS=1)", text)
        self.assertIn('fresh_git() { "${GIT_ENV[@]}" git -c core.attributesFile=/dev/null', text)
        self.assertIn('"${GIT_ENV[@]}" git init -q --bare', text)
        self.assertIn('fresh_git fetch -q --depth 1 "$REPOSITORY" "$COMMIT"', text)
        self.assertIn('[ "$(fresh_git rev-parse "$COMMIT^{commit}")" = "$COMMIT" ]', text)
        self.assertNotIn("CHECKOUT", text)

    def test_the_copy_and_the_launcher_are_staged_then_swapped_under_the_lab_lock(self):
        text = INSTALLER.read_text()
        order = [text.index(marker) for marker in (
            'fresh_git archive --prefix="repo-$SHORT/"', 'sudo tar -x -C "$STAGE"',
            'sudo chown -R root:wheel "$STAGE/repo-$SHORT"', '| sudo tee "$STAGE/t008-launch.sh"',
            'sudo /usr/bin/lockf -k -t 0 "$LOCK" /bin/sh -c "$SWAP"', 'sudo mv -f "$RULE.new" "$RULE"')]
        self.assertEqual(order, sorted(order))
        self.assertIn('rm -rf "$2"; mv "$1/repo-$4" "$2"; mv -f "$1/t008-launch.sh" "$3"', text)
        # nothing outside the locked swap removes or replaces the code copy or the launcher
        swap = text.index("SWAP=")
        self.assertNotIn('"$COPY"', text[:swap].split("COPY=$B/repo-$SHORT", 1)[1])
        self.assertEqual(text.count('rm -rf "$2"'), 1)

    def test_the_staged_copy_holds_exactly_the_tracked_regular_files(self):
        text = INSTALLER.read_text()
        order = [text.index(marker) for marker in (
            "tracks a symlink or submodule", 'sudo tar -x -C "$STAGE"', "holds a symlink or special file",
            "does not hold exactly the $TRACKED tracked files", 'sudo /usr/bin/lockf -k -t 0 "$LOCK"')]
        self.assertEqual(order, sorted(order))

    def test_the_pinned_binaries_must_be_root_owned_and_closed_before_any_sudo(self):
        text = INSTALLER.read_text()
        before_fetch = text[:text.index("fresh_git fetch")]
        self.assertIn('find "$B/claude-2.1.292" "$B/python312" ! -type l', before_fetch)
        self.assertIn("not owned by root or writable by others", before_fetch)


class NoTokenTests(unittest.TestCase):
    """The lab half screens every world-readable publication for the lab token."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        text = LAUNCHER.read_text()
        start = text.index("no_token() {")
        self.function = text[start:text.index("\n}\n", start) + 3]
        self.token = self.tmp / "oauth-token"
        self.token.write_text("abcdefghijklmnopqrstuvwxyz0123456789\n")

    def screen(self, content):
        target = self.tmp / "out.txt"
        target.write_text(content)
        script = 'stop() { printf "STOP: %s\\n" "$1" >&2; exit 1; }\n' + self.function + '\nno_token "$1" "$2"'
        return subprocess.run([BASH, "-c", script, "sh", str(target), str(self.token)], capture_output=True,
                              text=True, timeout=30, env={"PATH": "/usr/bin:/bin"})

    def test_a_clean_file_passes(self):
        self.assertEqual(self.screen('{"verdict": "ready"}\n').returncode, 0)

    def test_the_token_refuses(self):
        result = self.screen("leaked abcdefghijklmnopqrstuvwxyz0123456789 here\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("holds a credential", result.stderr)

    def test_an_anthropic_key_prefix_refuses(self):
        self.assertEqual(self.screen("key sk-ant-oat01-xyz\n").returncode, 1)

    def test_both_publications_of_lab_output_are_screened(self):
        text = LAUNCHER.read_text()
        for name in ('"$work/run-$attempt.txt"', '"$work/dry-run.json"'):
            self.assertIn(f'no_token {name} "$cfg/oauth-token"\n      publish {name}', text)


class PacketTests(unittest.TestCase):
    def test_the_packet_renders_both_templates_with_the_same_pipeline(self):
        text = PACKET.read_text()
        self.assertGreaterEqual(text.count(RENDER_SED), 2)
        self.assertIn('show "$COMMIT:scripts/har_t008_install.sh"', text)
        self.assertIn('show "$COMMIT:scripts/har_t008_launch.sh"', text)
        self.assertIn("sudo -n /usr/local/libexec/braid/t008-launch.sh check", text)
        self.assertIn("sudo /usr/local/libexec/braid/t008-launch.sh run", text)


if __name__ == "__main__":
    unittest.main()
