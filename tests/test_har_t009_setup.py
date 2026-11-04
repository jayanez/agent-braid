# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 operator setup (steps 0-8) and the step 9-10 wrapper, with doubles only.

Nothing real runs here: no sudo, no sysadminctl, no claude, no network. The host is a scripted ``Runner``.
"""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import har_t009_dryrun as dry
from scripts import har_t009_setup as setup

COMMIT = "0123456789abcdef0123456789abcdef01234567"
SHORT = COMMIT[:7]
BRAID = setup.BRAID
CLAUDE_SRC = "/opt/claude"
CLAUDE_DST = f"{BRAID}/claude-2.1.292"
PY_BIN = f"{BRAID}/python312/bin/python3.12"
REPO = f"{BRAID}/repo-{SHORT}"
H_CLAUDE, H_PY, H_SB = "a" * 64, "b" * 64, "c" * 64
LISTING = f"{'d' * 64}  ./scripts/har_t009_attempt.py\n{'e' * 64}  ./README.md\n"
CODESIGN = (f"Identifier=x\nAuthority=Developer ID Application: Anthropic PBC ({setup.TEAM_ID})\n"
            f"TeamIdentifier={setup.TEAM_ID}\n")
PINS_OUT = f"{H_CLAUDE}  {CLAUDE_DST}\n{H_PY}  {PY_BIN}\n{H_SB}  {setup.SANDBOX_EXEC}\n"
HOME_STAT = "stat -f %Su %Sg %Lp /Users/braidlab"


class FakeRunner(setup.Runner):
    """Answers each command by its text; ``overrides`` (substring -> result) win over the healthy defaults."""

    def __init__(self, dry_run=False, overrides=None):
        super().__init__(dry_run, out=io.StringIO(), err=io.StringIO())
        self.calls: list[str] = []
        self.overrides = overrides or {}
        self.pipes: list[tuple] = []
        self.created = False

    def _exec(self, argv, *, cwd=None, merge=False, interactive=False):
        text = " ".join(argv)
        self.calls.append(text)
        self.created = self.created or "sysadminctl" in text
        for needle, answer in self.overrides.items():
            if needle in text:
                return answer
        table = [
            ("sw_vers", (0, "27.2\n")),
            ("id -u", (0, "502\n") if self.created else (1, "")),  # absent until sysadminctl ran
            ("id -G", (0, "20 12 61\n")),
            ("dseditgroup", (67, "no braidlab is NOT a member of admin\n")),
            ("test -d /Users/", (1, "")),
            (HOME_STAT, (0, "braidlab staff 700\n")),
            ("stat -f %Su %Sg %Lp", (0, "root wheel 755\n")),
            ("stat -f %Su %Sg %Sp", (0, "root wheel -rwxr-xr-x\n")),
            ("stat -f %Su %Lp", (0, "braidlab 700\n")),
            ("stat -f %Lp", (0, "750\n")),
            ("shasum -a 256 /opt/claude", (0, f"{H_CLAUDE}  {CLAUDE_SRC}\n{H_CLAUDE}  {CLAUDE_DST}\n")),
            ("shasum -a 256 " + CLAUDE_DST, (0, PINS_OUT)),
            ("shasum -a 256 " + PY_BIN, (0, f"{H_PY}  {PY_BIN}\n")),
            ("codesign -dv", (0, CODESIGN)),
            ("rev-parse", (0, "f" * 40 + "\n")),
            ("sh -c", (0, LISTING)),
            ("ls -A", (0, "")),
            ("find", (0, "")),
        ]
        for needle, answer in table:
            if needle in text:
                return answer
        return 0, ""

    def _pipe(self, first, second):
        self.pipes.append((tuple(first), tuple(second)))
        return self.overrides.get("pipe", (0, 0))


def run_main(argv, runner, home="/Users/founder", euid=501, platform="darwin"):
    err = io.StringIO()
    with mock.patch.object(setup.sys, "platform", platform), \
            mock.patch.object(setup.os, "geteuid", return_value=euid, create=True), \
            contextlib.redirect_stderr(err):
        code = setup.main(argv, runner=runner, home=home)
    return code, err.getvalue()


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.summary = str(Path(self.tmp.name) / "summary.json")
        self.base = ["--commit", COMMIT, "--claude-src", CLAUDE_SRC, "--python-src", "/py", "--checkout", "/co",
                     "--summary-out", self.summary]

    def go(self, overrides=None):
        runner = FakeRunner(overrides=overrides)
        code, err = run_main(self.base, runner)
        return code, err, runner

    # arguments
    def test_commit_must_be_40_hex(self):
        for bad in ("abc", COMMIT[:-1], COMMIT.upper(), COMMIT + "0", "g" * 40):
            runner = FakeRunner()
            code, err = run_main(["--commit", bad], runner)
            self.assertEqual(code, 1, bad)
            self.assertIn("STOP: COMMIT is not a 40-character hash", err)
            self.assertEqual(runner.calls, [])

    def test_account_name_is_validated(self):
        code, err = run_main(["--commit", COMMIT, "--account", "Bad Name"], FakeRunner())
        self.assertEqual(code, 1)
        self.assertIn("not an account name", err)

    def test_commit_is_required(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            setup.main([])

    def test_default_checkout_is_this_repository(self):
        checkout = setup.parser().parse_args(["--commit", COMMIT]).checkout
        self.assertEqual(Path(checkout), Path(setup.__file__).resolve().parents[1])

    # dry run
    def test_dry_run_prints_the_commands_in_runbook_order_and_runs_none(self):
        runner = FakeRunner(dry_run=True)
        code, _ = run_main([*self.base, "--dry-run"], runner)
        self.assertEqual(code, 0)
        self.assertEqual(runner.calls, [])
        self.assertEqual(runner.pipes, [])
        self.assertFalse(Path(self.summary).exists())
        text = runner.out.getvalue()
        order = [
            "sw_vers -productVersion", "sudo -v",
            "sudo sysadminctl -addUser braidlab -fullName 'Braid Lab' -password -",
            "sudo createhomedir -c -u braidlab", f"sudo install -d -o root -g wheel -m 755 {BRAID}",
            f"sudo install -o root -g wheel -m 755 {CLAUDE_SRC} {CLAUDE_DST}", "codesign --verify --strict --deep",
            "sudo ditto /py/lib/python3.12", f"git -C /co archive --prefix=repo-{SHORT}/ {COMMIT}",
            f"| sudo tar -x -C {BRAID} --no-same-owner", "chmod 700 /Users/founder",
            "sudo install -d -o braidlab -g staff -m 700 /Users/braidlab/t009/config", f"shasum -a 256 {CLAUDE_DST}"]
        positions = [text.find(item) for item in order]
        self.assertNotIn(-1, positions, dict(zip(order, positions)))
        self.assertEqual(positions, sorted(positions))
        for step in range(9):
            self.assertIn(f"Step {step}.", text)
        self.assertIn("# check: macOS version starts with 27.", text)
        self.assertNotIn("Step 9", text)

    def test_dry_run_works_off_macos_without_sudo(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(setup.sys, "platform", "linux"):
            self.assertEqual(setup.main([*self.base, "--dry-run"], home="/home/x"), 0)
        self.assertIn("Step 8", out.getvalue())

    # real run (scripted host)
    def test_full_run_writes_the_summary_with_the_pins(self):
        code, err, runner = self.go()
        self.assertEqual(code, 0, err)
        data = json.loads(Path(self.summary).read_text())
        self.assertEqual(data, json.loads(runner.out.getvalue()))
        self.assertEqual(data["commit"], COMMIT)
        self.assertEqual(data["pins"],
                         {"claudeSha256": H_CLAUDE, "interpreterSha256": H_PY, "sandboxExecSha256": H_SB})
        self.assertEqual(data["claude"]["teamIdentifier"], "Q6L2SF6YDW")
        self.assertEqual(data["codeCopy"]["listingSha256"], hashlib.sha256(LISTING.encode()).hexdigest())
        self.assertEqual(data["codeCopy"]["fileCount"], 2)
        self.assertEqual(data["homeModeBefore"], "750")
        self.assertIs(data["executionAuthorization"], False)
        self.assertIs(data["nativeRun"], False)
        self.assertEqual(oct(os.stat(self.summary).st_mode & 0o777), "0o644")
        self.assertEqual(runner.pipes[0][0], ("git", "-C", "/co", "archive", f"--prefix=repo-{SHORT}/", COMMIT))
        self.assertEqual(runner.pipes[0][1], ("sudo", "tar", "-x", "-C", BRAID, "--no-same-owner"))

    def test_never_runs_native_things(self):
        _, _, runner = self.go()
        natives = {"claude", CLAUDE_DST, CLAUDE_SRC, setup.SANDBOX_EXEC, "sandbox-exec", "curl", "ssh", "nc"}
        for call in runner.calls:
            words = call.split()
            command = words[1] if words[0] == "sudo" else words[0]
            self.assertNotIn(command, natives, call)
            self.assertNotIn("login", words, call)

    def test_new_account_is_created_interactively(self):
        _, _, runner = self.go()
        self.assertIn("sudo sysadminctl -addUser braidlab -fullName Braid Lab -password -", runner.calls)

    def test_existing_account_is_kept_on_rerun(self):
        code, _, runner = self.go({"id -u": (0, "502\n"), "test -d /Users/": (0, "")})
        self.assertEqual(code, 0)
        self.assertFalse([c for c in runner.calls if "sysadminctl" in c or "createhomedir" in c])

    # stop conditions: each prints the runbook message and exits 1, and leaves no summary
    def assertStops(self, overrides, message):
        code, err, runner = self.go(overrides)
        self.assertEqual(code, 1, err)
        self.assertIn(message, err)
        self.assertFalse(Path(self.summary).exists())
        return runner

    def test_stop_wrong_macos_series(self):
        runner = self.assertStops({"sw_vers": (0, "26.4\n")}, "STOP: macOS is not the 27.x series")
        self.assertFalse([c for c in runner.calls if "sysadminctl" in c or "install" in c])

    def test_stop_account_in_admin_or_wheel(self):
        self.assertStops({"id -G": (0, "20 80 12\n")}, "STOP: the account is in admin or wheel")
        self.assertStops({"id -G": (0, "0 20\n")}, "STOP: the account is in admin or wheel")

    def test_stop_account_is_admin_member(self):
        self.assertStops({"dseditgroup": (0, "yes braidlab is a member of admin\n")},
                         "STOP: the account is an admin member")

    def test_stop_home_mode(self):
        self.assertStops({HOME_STAT: (0, "braidlab staff 750\n")}, "STOP: the home of braidlab is not")

    def test_stop_install_dir_group_writable_or_not_root(self):
        self.assertStops({"stat -f %Su %Sg %Lp /usr/local": (0, "root wheel 775\n")}, "without group/other write")
        self.assertStops({"stat -f %Su %Sg %Lp /usr/local": (0, "juan staff 755\n")}, "STOP: /usr/local is not root:wheel")

    def test_stop_claude_hash_differs(self):
        self.assertStops({"shasum -a 256 /opt/claude": (0, f"{H_CLAUDE}  {CLAUDE_SRC}\n{H_PY}  {CLAUDE_DST}\n")},
                         "STOP: the claude copy differs from its source")

    def test_stop_signature_verify_fails(self):
        self.assertStops({"codesign --verify": (3, "")}, "STOP: command failed (exit 3)")

    def test_stop_wrong_team_or_authority(self):
        self.assertStops({"codesign -dv": (0, "TeamIdentifier=ZZZZZZZZZZ\n")},
                         "STOP: the copy is not the Anthropic build")
        self.assertStops({"codesign -dv": (0, f"TeamIdentifier={setup.TEAM_ID}\n")},
                         "STOP: the copy is not the Anthropic build")

    def test_stop_stray_owner_in_python_or_code_copy(self):
        self.assertStops({f"find {BRAID}/python312 -not": (0, "/x\n")}, "interpreter prefix are not owned by root")
        self.assertStops({f"find {REPO} -not": (0, "/x\n")}, "code copy are not owned by root")

    def test_stop_remaining_checks(self):
        rows = [
            ({"stat -f %Su %Sg %Lp /usr/local/libexec/braid": (0, "root wheel 777\n")},
             "libexec/braid is not root:wheel"),
            ({"stat -f %Su %Sg %Sp": (0, "root wheel -rwxrwxr-x\n")}, "not -rwxr-xr-x root wheel"),
            ({f"test -f {REPO}/scripts/har_t009_attempt.py": (1, "")}, "STOP: command failed (exit 1)"),
            ({"id -u": (0, "300\n"), "test -d /Users/": (0, "")}, "STOP: the account is a system account"),
            ({"sudo -v": (1, "")}, "STOP: command failed (exit 1): sudo -v"),
        ]
        for overrides, message in rows:
            with self.subTest(message):
                self.assertStops(overrides, message)

    def test_failed_command_shows_its_stderr(self):
        runner = FakeRunner(overrides={"codesign --verify": (3, "")})
        runner.last_err = "invalid signature"
        code, err = run_main(self.base, runner)
        self.assertEqual(code, 1)
        self.assertIn("invalid signature", err)

    def test_summary_write_replaces_a_planted_symlink(self):
        target = Path(self.tmp.name) / "victim"
        target.write_text("keep")
        Path(self.summary).symlink_to(target)
        self.assertEqual(self.go()[0], 0)
        self.assertEqual(target.read_text(), "keep")
        self.assertFalse(Path(self.summary).is_symlink())

    def test_unwritable_summary_is_a_stop_not_a_traceback(self):
        base = [*self.base]
        base[base.index("--summary-out") + 1] = "/nonexistent-dir/summary.json"
        code, err = run_main(base, FakeRunner())
        self.assertEqual(code, 1)
        self.assertIn("STOP: cannot write the summary", err)

    def test_stop_archive_fails(self):
        self.assertStops({"pipe": (1, 0)}, "STOP: pipeline failed")

    def test_stop_config_dir_not_empty(self):
        self.assertStops({"ls -A": (0, ".claude.json\n")}, "STOP: config_dir is not empty")

    def test_stop_pins_changed(self):
        changed = f"{'9' * 64}  {CLAUDE_DST}\n{H_PY}  {PY_BIN}\n{H_SB}  {setup.SANDBOX_EXEC}\n"
        self.assertStops({"shasum -a 256 " + CLAUDE_DST: (0, changed)}, "STOP: a pinned file changed")

    def test_stop_missing_input_or_commit(self):
        self.assertStops({"test -f /opt/claude": (1, "")}, "STOP: command failed (exit 1)")
        self.assertStops({"cat-file": (128, "")}, "STOP: command failed (exit 128)")

    def test_stop_root_non_macos_and_lab_account(self):
        code, err = run_main(self.base, FakeRunner(), home="/var/root", euid=0)
        self.assertEqual(code, 1)
        self.assertIn("not as root", err)
        code, err = run_main(self.base, FakeRunner(), home="/home/x", platform="linux")
        self.assertEqual(code, 1)
        self.assertIn("macOS only", err)
        code, err = run_main(self.base, FakeRunner(), home="/Users/braidlab")
        self.assertEqual(code, 1)
        self.assertIn("not as the lab account", err)


class DryRunWrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.summary = Path(self.tmp.name) / "summary.json"
        self.summary.write_text(json.dumps({
            "summaryVersion": dry.SUMMARY_VERSION, "commit": COMMIT,
            "pins": {"claudeSha256": H_CLAUDE, "interpreterSha256": H_PY, "sandboxExecSha256": H_SB}}))
        self.argv = ["--commit", COMMIT, "--operator-account", "juanyanez", "--attempt", "t009-20261104",
                     "--summary", str(self.summary)]

    def run_main(self, argv, env=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = dry.main(argv, env=env if env is not None else {})
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_prints_login_and_the_driver_dry_run_only(self):
        code, out, _ = self.run_main([*self.argv, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("claude-2.1.292 auth login", out)
        self.assertIn("--dry-run", out)
        self.assertIn(f"--claude-sha256 {H_CLAUDE}", out)
        self.assertIn(f"{dry.BRAID}/repo-{SHORT}/scripts/har_t009_attempt.py", out)
        self.assertIn("python3.12 -B -I", out)
        self.assertNotIn("--founder-go", out)
        self.assertNotIn("--self-check", out)

    def test_dry_run_without_a_summary_uses_placeholders(self):
        self.summary.unlink()
        code, out, _ = self.run_main([*self.argv, "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("claudeSha256 from the setup summary", out)

    def test_argument_validation(self):
        cases = [("--commit", "abc", "COMMIT is not a 40-character hash"),
                 ("--operator-account", "Bad Name", "OPERATOR_ACCOUNT"),
                 ("--attempt", "t009-2026", "ATTEMPT")]
        for flag, value, message in cases:
            argv = list(self.argv)
            argv[argv.index(flag) + 1] = value
            code, _, err = self.run_main(argv)
            self.assertEqual(code, 1, flag)
            self.assertIn(message, err)

    def test_summary_must_match_commit_and_version(self):
        argv = list(self.argv)
        argv[1] = COMMIT[:-1] + "8"
        code, _, err = self.run_main(argv)
        self.assertEqual(code, 1)
        self.assertIn("not the commit the setup summary", err)
        self.summary.write_text(json.dumps({"summaryVersion": "x", "commit": COMMIT}))
        self.assertIn("not a har-t009-setup-v1 file", self.run_main(self.argv)[2])

    def test_pin_must_be_64_hex(self):
        code, _, err = self.run_main([*self.argv, "--claude-sha256", "zz"])
        self.assertEqual(code, 1)
        self.assertIn("a hash is not pasted correctly", err)

    def test_stop_when_environment_has_claude_or_anthropic_variables(self):
        code, _, err = self.run_main(self.argv, env={"ANTHROPIC_API_KEY": "secret-value", "PATH": "/bin"})
        self.assertEqual(code, 1)
        self.assertIn("ANTHROPIC_API_KEY", err)
        self.assertNotIn("secret-value", err)

    # real path, with subprocess and hashing replaced
    def real(self, argv=None, login_rc=0, driver=(0, '{"verdict": "ready"}'), hash_of=None, files=None, env=None):
        root = Path(self.tmp.name)
        (root / "home/t009/config").mkdir(parents=True)
        for name, size in (files if files is not None else {"a.json": 10}).items():
            (root / "home/t009/config" / name).write_bytes(b"x" * size)
        scripts_dir = root / f"braid/repo-{SHORT}/scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "har_t009_attempt.py").write_text("")
        shared = root / "shared.json"
        calls = []

        def fake_run(cmd, **kw):
            calls.append((cmd, kw))
            if cmd[1:3] == ["auth", "login"]:
                return mock.Mock(returncode=login_rc)
            return mock.Mock(returncode=driver[0], stdout=driver[1], stderr="")

        def default_hash(path):
            return H_CLAUDE if "claude" in path else H_PY if "python" in path else H_SB

        with mock.patch.dict(os.environ, {"HOME": str(root / "home")}), \
                mock.patch.object(dry, "BRAID", str(root / "braid")), \
                mock.patch.object(dry, "SHARED_COPY", str(shared)), \
                mock.patch.object(dry.subprocess, "run", fake_run), \
                mock.patch.object(dry, "sha256_file", hash_of or default_hash):
            result = self.run_main(argv or self.argv, env=env)
        return result, calls, root, shared

    def test_real_run_saves_the_verdict_and_never_self_checks(self):
        (code, out, _), calls, root, shared = self.real()
        self.assertEqual(code, 0)
        driver_cmd, kw = calls[-1]
        self.assertEqual(driver_cmd[-1], "--dry-run")
        self.assertNotIn("--founder-go", driver_cmd)
        self.assertNotIn("--self-check", driver_cmd)
        self.assertEqual(kw["env"]["CLAUDE_CONFIG_DIR"], str(root / "home/t009/config"))
        self.assertEqual(kw["env"]["DISABLE_AUTOUPDATER"], "1")
        self.assertEqual((root / "home/t009/dry-run.json").read_text(), '{"verdict": "ready"}')
        self.assertEqual(shared.read_text(), '{"verdict": "ready"}')
        self.assertTrue(any(c[0][1:3] == ["auth", "login"] for c in calls))

    def test_skip_login_does_not_run_claude(self):
        (code, _, _), calls, _, _ = self.real([*self.argv, "--skip-login"])
        self.assertEqual(code, 0)
        self.assertFalse(any(c[0][1:3] == ["auth", "login"] for c in calls))

    def test_refused_verdict_exit_code_is_passed_through_and_saved(self):
        (code, _, _), _, _, shared = self.real(driver=(2, '{"verdict": "refused"}'))
        self.assertEqual(code, 2)
        self.assertTrue(shared.exists())

    def test_crashed_driver_saves_nothing(self):
        for result in ((1, "Traceback"), (1, '{"verdict": "error"}')):
            with self.subTest(result):
                self.setUp()
                (code, _, err), _, root, shared = self.real(driver=result)
                self.assertEqual(code, 1)
                self.assertIn("STOP:", err)
                self.assertFalse(shared.exists())
                self.assertFalse((root / "home/t009/dry-run.json").exists())

    def test_hash_mismatch_stops_before_login(self):
        (code, _, err), calls, _, _ = self.real(hash_of=lambda path: "0" * 64)
        self.assertEqual(code, 1)
        self.assertIn("does not match its pinned hash", err)
        self.assertEqual(calls, [])

    def test_login_failure_and_bad_config_dir_stop(self):
        cases = [({"login_rc": 1}, "claude auth login failed"), ({"files": {}}, "few small files"),
                 ({"files": {"big": dry.BIG_FILE + 1}}, "few small files")]
        for kwargs, message in cases:
            with self.subTest(message, **{k: str(v) for k, v in kwargs.items()}):
                self.setUp()
                (code, _, err), _, _, _ = self.real(**kwargs)
                self.assertEqual(code, 1)
                self.assertIn(message, err)

    def test_env_value_with_claude_is_caught_like_the_runbook_grep(self):
        (code, _, err), calls, _, _ = self.real(env={"__CFBundleIdentifier": "com.anthropic.claudefordesktop"})
        self.assertEqual(code, 1)
        self.assertIn("__CFBundleIdentifier", err)
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
