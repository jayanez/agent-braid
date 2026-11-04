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

from scripts import har_t009_lab as lab
from scripts import har_t009_verify as verify
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
            ("stat -f %Su:%Lp", (0, "braidlab:750\n") if "from-lab" in text else (0, "founder:755\n")),
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
        self.handoff = Path(self.tmp.name) / "handoff"
        (self.handoff / "to-lab").mkdir(parents=True)
        self.summary = str(self.handoff / "to-lab" / "setup-summary.json")
        self.base = ["--commit", COMMIT, "--claude-src", CLAUDE_SRC, "--python-src", "/py", "--checkout", "/co",
                     "--handoff", str(self.handoff)]

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
        base[base.index("--handoff") + 1] = "/nonexistent-dir"
        code, err = run_main(base, FakeRunner())
        self.assertEqual(code, 1)
        self.assertIn("STOP: cannot write the summary", err)

    def test_handoff_dirs_are_created_with_tight_owners(self):
        _, _, runner = self.go()
        h = str(self.handoff)
        self.assertIn(f"install -d -m 755 {h}/to-lab", runner.calls)
        self.assertIn(f"sudo install -d -o braidlab -g staff -m 750 {h}/from-lab", runner.calls)
        self.assertEqual(json.loads(Path(self.summary).read_text())["handoff"]["fromLab"], f"{h}/from-lab")

    def test_stop_when_the_lab_account_could_write_to_lab(self):
        self.assertStops({"stat -f %Su:%Lp": (0, "braidlab:755\\n")}, "STOP: ")
        self.assertStops({"stat -f %Su:%Lp": (0, "founder:777\\n")}, "STOP: ")

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


def write_json(path, data, mode=0o644):
    Path(path).write_text(json.dumps(data))
    os.chmod(path, mode)


class LabTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / "home"
        (self.home / "t009/config").mkdir(parents=True)
        (self.home / "t009/config/login.json").write_text("{}")  # what a fresh login leaves
        self.handoff = root / "handoff"
        self.to_lab, self.from_lab = self.handoff / "to-lab", self.handoff / "from-lab"
        self.to_lab.mkdir(parents=True)
        self.from_lab.mkdir()
        self.braid = root / "braid"
        scripts_dir = self.braid / f"repo-{SHORT}/scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "har_t009_attempt.py").write_text("")
        self.summary = self.to_lab / "setup-summary.json"
        write_json(self.summary, {"summaryVersion": lab.SUMMARY_VERSION, "commit": COMMIT,
                                  "pins": {"claudeSha256": H_CLAUDE, "interpreterSha256": H_PY,
                                           "sandboxExecSha256": H_SB}})
        self.argv = ["--commit", COMMIT, "--operator-account", "juanyanez", "--attempt", "t009-20261104",
                     "--handoff", str(self.handoff), "--poll", "0"]
        self.calls = []
        self.driver = {"--dry-run": (0, '{"verdict": "ready"}'), "--self-check": (0, '{"verdict": "self-check-ok"}'),
                       "--founder-go": (0, "")}
        self.login_rc = 0
        self.verifier = lambda stage, sha: True  # who "approves" which stage; replaced per test
        self.waits = 0

    def approval(self, stage, sha, override=None):
        record = {"verificationVersion": lab.VERIFY_VERSION, "stage": stage, "commit": COMMIT,
                  "attempt": "t009-20261104", "subjectSha256": sha, "verdict": "approved", **(override or {})}
        write_json(self.to_lab / f"verify-{stage}.json", record)

    def fake_run(self, cmd, **kw):
        self.calls.append((list(cmd), kw))
        if cmd[1:3] == ["auth", "login"]:
            return mock.Mock(returncode=self.login_rc)
        flag = next((f for f in ("--dry-run", "--self-check", "--founder-go") if f in cmd), None)
        code, out = self.driver[flag]
        if flag == "--founder-go" and "--self-check" not in cmd:  # the real attempt writes its bundle
            out_dir = self.home / "t009/out/t009-20261104"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "summary.json").write_text("{}")
        return mock.Mock(returncode=code, stdout=out, stderr="")

    def sleeping(self, _seconds):
        """Each wait iteration lets the 'orchestrator' act once, as the real one does between polls."""
        self.waits += 1
        for stage, sha in list(self.pending.items()):
            if self.verifier(stage, sha):
                self.approval(stage, sha)
                del self.pending[stage]

    def go(self, extra=(), approve=("setup", "dry-run", "self-check"), env=None, uid=None, **patches):
        """Run the lab script; verification files appear while it polls (they are bound to the real SHA-256)."""
        self.pending = {}
        real_wait = lab.wait_for_verification

        def wait(stage, sha, **kw):
            if stage in approve:
                self.pending[stage] = sha
            return real_wait(stage, sha, **kw)

        out, err = io.StringIO(), io.StringIO()
        clock = iter(range(0, 100000)).__next__
        stack = contextlib.ExitStack()
        with stack:
            stack.enter_context(mock.patch.dict(os.environ, {"HOME": str(self.home)}))
            stack.enter_context(mock.patch.object(lab, "BRAID", str(self.braid)))
            stack.enter_context(mock.patch.object(lab.subprocess, "run", self.fake_run))
            stack.enter_context(mock.patch.object(lab, "sha256_file", patches.pop("hash_of", None) or self.default_hash))
            stack.enter_context(mock.patch.object(lab, "wait_for_verification", wait))
            stack.enter_context(mock.patch.object(lab, "operator_uid", lambda name, real=os.getuid(): real))
            stack.enter_context(mock.patch.object(lab.os, "getuid", return_value=uid if uid is not None else os.getuid() + 1))
            stack.enter_context(mock.patch.object(lab.os, "access", lambda path, mode: Path(path) == self.from_lab))
            stack.enter_context(contextlib.redirect_stdout(out))
            stack.enter_context(contextlib.redirect_stderr(err))
            code = lab.main([*self.argv, *extra], env=env if env is not None else {}, sleep=self.sleeping, clock=clock)
        return code, out.getvalue(), err.getvalue()

    @staticmethod
    def default_hash_for(path):
        return H_CLAUDE if "claude" in path else H_PY if "python" in path else H_SB if "sandbox" in path else None

    def default_hash(self, path):
        known = self.default_hash_for(path)
        return known or hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def driver_modes(self):
        return [next((f for f in ("--dry-run", "--self-check", "--founder-go") if f in c[0]), "login")
                for c in self.calls]

    # plan
    def test_plan_prints_every_stage_and_runs_nothing(self):
        code, out, _ = self.go(["--plan"])
        self.assertEqual(code, 0)
        self.assertEqual(self.calls, [])
        for needle in ("verify-setup.json", "auth login", "--dry-run", "--self-check --founder-go", "verify-self-check.json",
                       "--founder-go", f"bundle-t009-20261104"):
            self.assertIn(needle, out)

    def test_plan_without_a_summary_uses_placeholders(self):
        self.summary.unlink()
        code, out, _ = self.go(["--plan"])
        self.assertEqual(code, 0)
        self.assertIn("claudeSha256 from the setup summary", out)

    # the happy path
    def test_full_flow_waits_for_each_verification_and_runs_in_order(self):
        code, out, err = self.go()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.driver_modes(), ["login", "--dry-run", "--self-check", "--founder-go"])
        self.assertEqual(self.waits, 3)
        dry_sha = hashlib.sha256(b'{"verdict": "ready"}').hexdigest()
        self.assertEqual((self.from_lab / "dry-run.json.sha256").read_text(), f"{dry_sha}  dry-run.json\n")
        self.assertTrue((self.from_lab / "self-check.json").exists())
        self.assertTrue((self.from_lab / "bundle-t009-20261104/summary.json").exists())
        record = json.loads((self.from_lab / "bundle-t009-20261104.sha256.json").read_text())
        self.assertEqual(record["driverExit"], 0)
        # the real attempt has the terminal attached (the driver asks for the NC-6 readings) and is never captured
        real_cmd, real_kw = self.calls[-1]
        self.assertNotIn("capture_output", real_kw)
        self.assertEqual(real_kw["env"]["DISABLE_AUTOUPDATER"], "1")
        self.assertEqual(real_cmd.count("--founder-go"), 1)

    def test_skip_login(self):
        self.assertEqual(self.go(["--skip-login"])[0], 0)
        self.assertNotIn("login", self.driver_modes())

    def test_real_attempt_exit_code_is_passed_through_and_bundle_still_copied(self):
        self.driver["--founder-go"] = (2, "")
        code, _, _ = self.go()
        self.assertEqual(code, 2)
        self.assertEqual(json.loads((self.from_lab / "bundle-t009-20261104.sha256.json").read_text())["driverExit"], 2)

    # verification gates
    def test_nothing_runs_before_the_setup_verification(self):
        code, _, err = self.go(approve=(), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("no valid verification of setup", err)
        self.assertEqual(self.calls, [])

    def test_missing_dry_run_verification_stops_before_the_self_check(self):
        code, _, err = self.go(approve=("setup",), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("no valid verification of dry-run", err)
        self.assertEqual(self.driver_modes(), ["login", "--dry-run"])

    def test_missing_self_check_verification_stops_before_the_real_attempt(self):
        code, _, err = self.go(approve=("setup", "dry-run"), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("no valid verification of self-check", err)
        self.assertNotIn("--founder-go", [m for m in self.driver_modes() if m != "--self-check"])

    def test_mismatching_or_rejected_verification_is_a_hard_stop(self):
        cases = [("subjectSha256", "0" * 64), ("commit", "1" * 40), ("attempt", "t009-20269999"),
                 ("verdict", "rejected"), ("stage", "dry-run"), ("verificationVersion", "x")]
        for key, value in cases:
            with self.subTest(key):
                self.setUp()
                self.verifier = lambda stage, sha, key=key, value=value: self.approval(stage, sha, {key: value}) or False
                code, _, err = self.go(approve=("setup",), extra=["--wait-timeout", "10"])
                self.assertEqual(code, 1)
                self.assertIn("does not match", err)
                self.assertEqual(self.calls, [])

    def test_verification_must_not_be_owned_by_the_lab_account(self):
        code, _, err = self.go(uid=os.getuid(), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("not owned by the operator", err)

    def test_verification_must_not_be_group_or_world_writable(self):
        self.verifier = lambda stage, sha: self.approval(stage, sha) or os.chmod(self.to_lab / f"verify-{stage}.json", 0o666) or False
        code, _, err = self.go(approve=("setup",), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("writable by others", err)

    def test_stale_approval_for_an_old_subject_is_refused(self):
        self.approval("setup", "f" * 64)
        code, _, err = self.go(approve=(), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("does not match", err)

    def test_stop_if_the_lab_account_can_write_to_lab(self):
        self.approval("setup", hashlib.sha256(self.summary.read_bytes()).hexdigest())
        real = os.getuid()
        with mock.patch.object(lab.os, "access", lambda path, mode: True), mock.patch.object(lab.os, "getuid", return_value=real + 1):
            with self.assertRaises(lab.Stop) as caught:
                lab.check_verification(self.to_lab / "verify-setup.json", self.to_lab, {}, real)
        self.assertIn("writable by this account", str(caught.exception))

    # runbook stops
    def test_argument_validation(self):
        for flag, value, message in (("--commit", "abc", "COMMIT is not a 40-character hash"),
                                     ("--operator-account", "Bad Name", "OPERATOR_ACCOUNT"),
                                     ("--attempt", "t009-2026", "ATTEMPT")):
            argv = list(self.argv)
            argv[argv.index(flag) + 1] = value
            self.argv = argv
            code, _, err = self.go()
            self.assertEqual(code, 1, flag)
            self.assertIn(message, err)
            self.setUp()

    def test_summary_must_exist_match_commit_and_version(self):
        self.summary.unlink()
        self.assertIn("missing or cannot be read", self.go()[2])
        write_json(self.summary, {"summaryVersion": "x", "commit": COMMIT, "pins": {}})
        self.assertIn("STOP:", self.go()[2])
        write_json(self.summary, {"summaryVersion": lab.SUMMARY_VERSION, "commit": "8" * 40,
                                  "pins": {"claudeSha256": H_CLAUDE, "interpreterSha256": H_PY, "sandboxExecSha256": H_SB}})
        self.assertIn("not the commit the setup summary", self.go()[2])
        self.summary.write_text("{not json")
        self.assertIn("missing or cannot be read", self.go()[2])
        self.assertEqual(self.calls, [])

    def test_hash_mismatch_stops_before_anything_runs(self):
        code, _, err = self.go(hash_of=lambda path: "0" * 64)
        self.assertEqual(code, 1)
        self.assertIn("does not match its pinned hash", err)
        self.assertEqual(self.calls, [])

    def test_env_value_with_claude_is_caught_like_the_runbook_grep(self):
        code, _, err = self.go(env={"__CFBundleIdentifier": "com.anthropic.claudefordesktop"})
        self.assertEqual(code, 1)
        self.assertIn("__CFBundleIdentifier", err)
        self.assertEqual(self.calls, [])

    def test_login_failure_and_bad_config_dir_stop(self):
        self.login_rc = 1
        self.assertIn("claude auth login failed", self.go()[2])
        self.login_rc = 0
        (self.home / "t009/config/big").write_bytes(b"x" * (lab.BIG_FILE + 1))
        self.assertIn("few small files", self.go(["--skip-login"])[2])
        (self.home / "t009/config/big").unlink()
        (self.home / "t009/config/login.json").unlink()
        self.assertIn("few small files", self.go(["--skip-login"])[2])

    def test_refused_dry_run_is_saved_then_stops(self):
        self.driver["--dry-run"] = (2, '{"verdict": "refused"}')
        code, _, err = self.go()
        self.assertEqual(code, 1)
        self.assertIn("verdict is refused, not ready", err)
        self.assertTrue((self.from_lab / "dry-run.json").exists())
        self.assertNotIn("--self-check", self.driver_modes())

    def test_crashed_driver_saves_nothing(self):
        for result in ((1, "Traceback"), (1, '{"verdict": "error"}')):
            with self.subTest(result):
                self.setUp()
                self.driver["--dry-run"] = result
                code, _, err = self.go()
                self.assertEqual(code, 1)
                self.assertIn("STOP:", err)
                self.assertFalse((self.from_lab / "dry-run.json").exists())

    def test_self_check_refusal_stops_before_the_real_attempt(self):
        self.driver["--self-check"] = (2, '{"verdict": "self-check-refused"}')
        code, _, err = self.go()
        self.assertEqual(code, 1)
        self.assertIn("not self-check-ok", err)
        self.assertEqual(self.driver_modes(), ["login", "--dry-run", "--self-check"])

    def test_existing_session_counter_needs_a_new_label_or_resume(self):
        out_dir = self.home / "t009/out/t009-20261104"
        out_dir.mkdir(parents=True)
        (out_dir / ".sessions.json").write_text("{}")
        code, _, err = self.go()
        self.assertEqual(code, 1)
        self.assertIn("step 10c", err)
        self.assertEqual(self.driver_modes(), ["login", "--dry-run", "--self-check"])
        self.setUp()
        out_dir = self.home / "t009/out/t009-20261104"
        out_dir.mkdir(parents=True)
        (out_dir / ".sessions.json").write_text("{}")
        self.assertEqual(self.go(["--resume"])[0], 0)

    def test_existing_bundle_copy_is_never_overwritten(self):
        (self.from_lab / "bundle-t009-20261104").mkdir()
        (self.from_lab / "bundle-t009-20261104/keep").write_text("old")
        code, _, _ = self.go()
        self.assertEqual(code, 0)
        self.assertEqual((self.from_lab / "bundle-t009-20261104/keep").read_text(), "old")
        self.assertTrue((self.from_lab / "bundle-t009-20261104-2/summary.json").exists())

    def test_bundle_copy_failure_keeps_the_driver_exit_code(self):
        self.driver["--founder-go"] = (2, "")
        with mock.patch.object(lab.shutil, "copytree", side_effect=OSError(28, "No space left")):
            code, _, err = self.go()
        self.assertEqual(code, 2)
        self.assertIn("cannot copy the bundle", err)

    def test_rerun_with_a_different_report_keeps_the_old_one(self):
        (self.from_lab / "dry-run.json").write_text('{"verdict": "ready", "old": true}')
        self.assertEqual(self.go()[0], 0)
        self.assertEqual((self.from_lab / "dry-run.json.1").read_text(), '{"verdict": "ready", "old": true}')
        self.assertEqual((self.from_lab / "dry-run.json").read_text(), '{"verdict": "ready"}')

    def test_verification_symlink_and_foreign_owner_are_refused(self):
        target = self.to_lab / "elsewhere.json"
        write_json(target, {})
        (self.to_lab / "verify-setup.json").symlink_to(target)
        code, _, err = self.go(approve=(), extra=["--wait-timeout", "10"])
        self.assertEqual(code, 1)
        self.assertIn("STOP:", err)
        (self.to_lab / "verify-setup.json").unlink()
        write_json(self.to_lab / "verify-setup.json", {})
        with mock.patch.object(lab.os, "getuid", return_value=os.getuid() + 1):
            with self.assertRaises(lab.Stop) as caught:
                lab.check_verification(self.to_lab / "verify-setup.json", self.to_lab, {}, os.getuid() + 7)
        self.assertIn("not owned by the operator", str(caught.exception))

    def test_unknown_operator_account_stops(self):
        with self.assertRaises(lab.Stop):
            lab.operator_uid("no-such-account-xyz")

    def test_flags_that_skip_a_gate_do_not_exist(self):
        flags = {a.option_strings[0] for a in lab.parser()._actions if a.option_strings}
        self.assertFalse({"--skip-verification", "--no-wait", "--skip-self-check", "--founder-go", "--self-check"} & flags)

    def test_shared_constants_agree_across_the_scripts(self):
        for module in (lab, verify):
            self.assertEqual(module.BRAID, setup.BRAID)
            self.assertEqual(module.VERIFY_VERSION, "har-t009-verify-v1")
            self.assertEqual(module.SUMMARY_VERSION, setup.SUMMARY_VERSION)
            self.assertEqual(module.DEFAULT_HANDOFF, setup.DEFAULT_HANDOFF)
            self.assertTrue(module.CLAUDE.endswith(setup.CLAUDE_VERSION) if hasattr(module, "CLAUDE") else True)
        self.assertEqual(verify.TEAM_ID, setup.TEAM_ID)
        self.assertEqual(verify.LISTING_COMMAND, setup.LISTING_COMMAND)


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.handoff = Path(self.tmp.name)
        (self.handoff / "to-lab").mkdir()
        (self.handoff / "from-lab").mkdir()
        self.summary = {
            "summaryVersion": setup.SUMMARY_VERSION, "commit": COMMIT, "nativeRun": False, "executionAuthorization": False,
            "pins": {"claudeSha256": H_CLAUDE, "interpreterSha256": H_PY, "sandboxExecSha256": H_SB},
            "claude": {"sha256": H_CLAUDE, "sourceSha256": H_CLAUDE, "teamIdentifier": "Q6L2SF6YDW"},
            "codeCopy": {"path": "/x", "listingSha256": hashlib.sha256(LISTING.encode()).hexdigest()}}
        write_json(self.handoff / "to-lab/setup-summary.json", self.summary)

    def args(self, stage, published=H_CLAUDE):
        return verify.parser().parse_args([stage, "--commit", COMMIT, "--attempt", "t009-20261104",
                                           "--handoff", str(self.handoff), "--published-claude-sha256", published])

    def host(self, hash_of=None, codesign_out=CODESIGN, verify_rc=0):
        def run(cmd, cwd=None):
            if cmd[:2] == ["codesign", "--verify"]:
                return verify_rc, ""
            if cmd[:2] == ["codesign", "-dv"]:
                return 0, codesign_out
            return 0, LISTING
        hasher = hash_of or (lambda path: H_CLAUDE if "claude" in path else H_PY if "python" in path else
                             H_SB if "sandbox" in path else hashlib.sha256(Path(path).read_bytes()).hexdigest())
        return run, hasher

    def call(self, args, **host):
        run, hasher = self.host(**host)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = verify.verify(args, run=run, hash_file=hasher)
        return code, json.loads((self.handoff / f"to-lab/verify-{args.stage}.json").read_text())

    def test_setup_approved_binds_to_the_summary_hash(self):
        code, record = self.call(self.args("setup"))
        self.assertEqual((code, record["verdict"]), (0, "approved"), record["failed"])
        self.assertEqual(record["subjectSha256"], hashlib.sha256((self.handoff / "to-lab/setup-summary.json").read_bytes()).hexdigest())
        self.assertEqual((record["stage"], record["commit"], record["attempt"]), ("setup", COMMIT, "t009-20261104"))
        self.assertIs(record["executionAuthorization"], False)

    def test_setup_rejections(self):
        rows = [({"published": "9" * 64}, "PUBLISHED release checksum"),
                ({"hash_of": lambda path: "0" * 64}, "re-hashed"),
                ({"codesign_out": "TeamIdentifier=ZZZZZZZZZZ\n"}, "TeamIdentifier Q6L2SF6YDW and the Anthropic"),
                ({"verify_rc": 3}, "codesign --verify")]
        for host, fragment in rows:
            with self.subTest(fragment):
                published = host.pop("published", H_CLAUDE)
                code, record = self.call(self.args("setup", published), **host)
                self.assertEqual((code, record["verdict"]), (1, "rejected"))
                self.assertTrue(any(fragment in name for name in record["failed"]), record["failed"])

    def test_setup_rejects_a_summary_for_another_commit_or_with_native_run(self):
        for key, value in (("commit", "8" * 40), ("nativeRun", True), ("executionAuthorization", True)):
            with self.subTest(key):
                write_json(self.handoff / "to-lab/setup-summary.json", {**self.summary, key: value})
                self.assertEqual(self.call(self.args("setup"))[1]["verdict"], "rejected")

    def test_dry_run_and_self_check_stages(self):
        report = {"verdict": "ready", "failed": [], "attempt": "t009-20261104", "nativeRun": False, "dryRun": True,
                  "executionAuthorization": False, "probeCatalogSha256": "a" * 64}
        text = json.dumps(report)
        (self.handoff / "from-lab/dry-run.json").write_text(text)
        digest = hashlib.sha256(text.encode()).hexdigest()
        (self.handoff / "from-lab/dry-run.json.sha256").write_text(f"{digest}  dry-run.json\n")
        code, record = self.call(self.args("dry-run"))
        self.assertEqual((code, record["verdict"], record["subjectSha256"]), (0, "approved", digest))
        for key, value in (("verdict", "refused"), ("failed", ["x"]), ("nativeRun", True), ("attempt", "t009-20269999")):
            with self.subTest(key):
                bad = json.dumps({**report, key: value})
                (self.handoff / "from-lab/dry-run.json").write_text(bad)
                (self.handoff / "from-lab/dry-run.json.sha256").write_text(f"{hashlib.sha256(bad.encode()).hexdigest()}  dry-run.json\n")
                self.assertEqual(self.call(self.args("dry-run"))[1]["verdict"], "rejected")
        sc = json.dumps({"verdict": "self-check-ok", "attempt": "t009-20261104", "executionAuthorization": False})
        (self.handoff / "from-lab/self-check.json").write_text(sc)
        (self.handoff / "from-lab/self-check.json.sha256").write_text(f"{hashlib.sha256(sc.encode()).hexdigest()}  self-check.json\n")
        self.assertEqual(self.call(self.args("self-check"))[1]["verdict"], "approved")

    def test_lab_edited_output_is_rejected_when_its_sidecar_disagrees(self):
        report = json.dumps({"verdict": "ready", "failed": [], "attempt": "t009-20261104", "nativeRun": False,
                             "dryRun": True, "executionAuthorization": False, "probeCatalogSha256": "a" * 64})
        (self.handoff / "from-lab/dry-run.json").write_text(report)
        (self.handoff / "from-lab/dry-run.json.sha256").write_text(f"{'0' * 64}  dry-run.json\n")
        self.assertEqual(self.call(self.args("dry-run"))[1]["verdict"], "rejected")

    def test_symlinked_subject_is_refused(self):
        real = self.handoff / "from-lab/real.json"
        real.write_text("{}")
        (self.handoff / "from-lab/dry-run.json").symlink_to(real)
        with self.assertRaises(verify.Stop):
            verify.verify(self.args("dry-run"))

    def test_missing_subject_and_bad_arguments_stop(self):
        with self.assertRaises(verify.Stop):
            verify.verify(self.args("dry-run"))
        bad = self.args("setup", published="zz")
        with self.assertRaises(verify.Stop):
            verify.verify(bad)
        bad = self.args("setup")
        bad.commit = "abc"
        with self.assertRaises(verify.Stop):
            verify.verify(bad)

    def test_the_verification_file_is_founder_readable_and_written_atomically(self):
        self.call(self.args("setup"))
        target = self.handoff / "to-lab/verify-setup.json"
        self.assertEqual(oct(target.stat().st_mode & 0o777), "0o644")
        self.assertFalse((self.handoff / "to-lab/verify-setup.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
