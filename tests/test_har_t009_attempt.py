# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 operator driver: every refusal, the dry-run and the NC-6 reader, with doubles only.

Nothing native runs here: no sandbox-exec, no claude, no network, no sudo, no account. The host is a
fake tree (``FakeSystem``); the backend, the runner and the transport are replaced where the driver
would otherwise build them.
"""
import contextlib
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import pwd
import unittest
from unittest import mock

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_lab as lab
from agent_braid import harness_host_claude as hc
from agent_braid import harness_qualification_probes as q
from scripts import har_t009_attempt as har

CLAUDE_SHA, INTERP_SHA, SANDBOX_SHA = "a" * 64, "b" * 64, "c" * 64
BRAID = "/usr/local/libexec/braid"
CLAUDE = f"{BRAID}/claude-2.1.292"
PY_ROOT = f"{BRAID}/python312"
PY = f"{PY_ROOT}/bin/python3.12"
REPO = f"{BRAID}/repo-abc1234"
HOME, FOUNDER_HOME = "/Users/braidlab", "/Users/juanyanez"
UID, FOUNDER_UID = 502, 501
NOW = datetime(2026, 11, 4, 15, 0, 0, tzinfo=timezone.utc)
DIR, FILE = stat.S_IFDIR, stat.S_IFREG


class FakeSystem(har.System):
    """A fake machine: ``tree`` maps a path to ``(kind, mode, uid, size)``; nothing touches the host."""

    def __init__(self):
        self.tree: dict[str, tuple] = {}
        self.hashes: dict[str, str] = {}
        self.user = "braidlab"
        self.console = UID  # fast user switching: the lab account owns /dev/console
        self.gids = (20, 12)
        self.traversable: set[str] = set()
        self.homes = [FOUNDER_HOME]
        self.unreadable: set[str] = set()
        self.running = PY
        self.isolated, self.no_bytecode = True, True
        self.env: dict[str, str] = {}
        self.facts = mac.HostFacts("27.0.1", "26A123", "arm64")
        self.links: dict[str, str] = {}
        self.writable_dirs = {"/Users/braidlab/out"}
        # the account's own non-GUI session (launchctl asuser), as the survey of 2026-11-13 saw it
        self.session_facts = mac.SessionFacts(auid=UID, asid=100_104, kind="Background")

    # builders
    def dir(self, path, mode=0o755, uid=0):
        self.tree[path] = (DIR, mode, uid, 0)

    def file(self, path, mode=0o755, uid=0, size=10, sha=None):
        self.tree[path] = (FILE, mode, uid, size)
        if sha:
            self.hashes[path] = sha

    # System interface
    def darwin(self): return True
    def ids(self): return UID, UID
    def passwd_by_uid(self, uid):
        table = {UID: SimpleNamespace(pw_name=self.user, pw_gid=20, pw_dir=HOME),
                 FOUNDER_UID: SimpleNamespace(pw_name="juanyanez", pw_gid=20, pw_dir=FOUNDER_HOME)}
        return table.get(uid)
    def passwd_by_name(self, name):
        table = {"juanyanez": SimpleNamespace(pw_name="juanyanez", pw_uid=FOUNDER_UID, pw_gid=20, pw_dir=FOUNDER_HOME),
                 "root": SimpleNamespace(pw_name="root", pw_uid=0, pw_gid=0, pw_dir="/var/root"),
                 "_sys": SimpleNamespace(pw_name="_sys", pw_uid=499, pw_gid=20, pw_dir="/var/empty"),
                 "braidlab": SimpleNamespace(pw_name="braidlab", pw_uid=UID, pw_gid=20, pw_dir=HOME)}
        return table.get(name)
    def groups(self, name, gid): return self.gids
    def lstat(self, path):
        node = self.tree.get(path)
        if node is None:
            return None
        kind, mode, uid, size = node
        return SimpleNamespace(st_mode=kind | mode, st_uid=uid, st_size=size)
    def realpath(self, path): return self.links.get(path, path)
    def listdir(self, path):
        prefix = path.rstrip("/") + "/"
        return sorted({p[len(prefix):].split("/")[0] for p in self.tree if p.startswith(prefix)}) \
            if path in self.tree else None
    def walk(self, path, limit):
        if path in self.unreadable:
            raise PermissionError(path)
        prefix = path.rstrip("/") + "/"
        found = [(p, self.lstat(p)) for p in sorted(self.tree) if p.startswith(prefix)]
        return None if len(found) > limit else found
    def sha256(self, path): return self.hashes.get(path)
    def can_traverse(self, path): return path in self.traversable
    def other_homes(self, account): return list(self.homes)
    def supervisor(self): return self.running
    def interpreter_flags(self): return self.isolated, self.no_bytecode
    def writable(self, path): return path in self.writable_dirs
    def environ(self): return self.env
    def host_facts(self): return self.facts
    def account_facts(self, account, entry, uid, operator_uid): return mac.AccountFacts((20,), 0o700)
    def session(self): return self.session_facts


def good_machine() -> FakeSystem:
    s = FakeSystem()
    for d in ("/", "/usr", "/usr/bin", "/usr/local", "/usr/local/libexec", BRAID, PY_ROOT, f"{PY_ROOT}/bin",
              f"{PY_ROOT}/lib", REPO, f"{REPO}/scripts", "/Users"):
        s.dir(d)
    s.file(CLAUDE, sha=CLAUDE_SHA)
    s.file(PY, sha=INTERP_SHA)
    s.file(f"{PY_ROOT}/lib/os.py", 0o644)
    s.file(f"{REPO}/scripts/har_t009_attempt.py", 0o644)
    s.file(mac.SANDBOX_EXEC, sha=SANDBOX_SHA)
    s.dir(HOME, 0o700, UID)
    s.dir(FOUNDER_HOME, 0o700, FOUNDER_UID)
    for d in ("run", "arena", "cfg", "out"):
        s.dir(f"{HOME}/{d}", 0o700, UID)
    return s


def arguments(**over) -> SimpleNamespace:
    value = dict(attempt="t009-test", account="braidlab", claude=CLAUDE, claude_sha256=CLAUDE_SHA,
                 interpreter=PY, interpreter_sha256=INTERP_SHA, interpreter_root=PY_ROOT,
                 sandbox_exec_sha256=SANDBOX_SHA, config_dir=f"{HOME}/cfg", run_root=f"{HOME}/run",
                 operator_account="juanyanez", arena_parent=f"{HOME}/arena", out_dir=f"{HOME}/out/t009-test",
                 proxy_port=18080,
                 dry_run=True, founder_go=False)
    value.update(over)
    return SimpleNamespace(**value)


def check(report, name):
    return next(c for c in report["checks"] if c["check"] == name)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(har, "ROOT", Path(REPO))
        patch.start()
        self.addCleanup(patch.stop)

    def run_preflight(self, system=None, **over):
        return har.preflight(arguments(**over), system or good_machine())

    def test_good_machine_is_ready_and_authorizes_nothing(self):
        report = self.run_preflight()
        self.assertEqual((report["verdict"], report["failed"]), ("ready", []))
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["nativeRun"])
        self.assertRegex(report["observed"]["environmentSha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(report["probeCatalogSha256"], q.CATALOG_SHA256)

    def refused(self, *names, system=None, **over):
        report = self.run_preflight(system, **over)
        self.assertEqual(report["verdict"], "refused")
        for name in names:
            self.assertFalse(check(report, name)["ok"], name)
        return report

    def test_the_session_must_be_the_accounts_own_of_a_supported_kind(self):
        """SPEC-065 amendment 2026-11-13: su or sudo from the operator's session keeps the operator's audit
        session (and Mach bootstrap namespace); the driver refuses it in both modes."""
        for kind in mac.SESSION_KINDS:
            with self.subTest(kind=kind):
                s = good_machine(); s.session_facts = mac.SessionFacts(UID, 100_200, kind)
                report = self.run_preflight(s)
                self.assertEqual(report["verdict"], "ready")
                self.assertEqual(report["observed"]["session"], {"kind": kind})
                self.assertTrue(check(report, "session-own")["ok"])
        s = good_machine(); s.session_facts = mac.SessionFacts(FOUNDER_UID, 100_014, "Aqua")  # sudo -u braidlab
        report = self.refused("session-own", system=s)
        self.assertIn("launchctl asuser", check(report, "session-own")["detail"])
        self.assertNotIn("environment-hash", [c["check"] for c in report["checks"]])
        for kind in ("LoginWindow", "StandardIO", None):
            with self.subTest(kind=kind):
                s = good_machine(); s.session_facts = mac.SessionFacts(UID, 100_104, kind)
                report = self.refused("session-own", system=s)
                self.assertIn("Aqua or Background", check(report, "session-own")["detail"])
        s = good_machine(); s.session_facts = mac.SessionFacts(None, None, None)  # unreadable: fail closed
        self.refused("session-own", system=s)

    def test_the_environment_hash_binds_the_session_kind(self):
        hashes = set()
        for kind in mac.SESSION_KINDS:
            s = good_machine(); s.session_facts = mac.SessionFacts(UID, 100_104, kind)
            hashes.add(self.run_preflight(s)["observed"]["environmentSha256"])
        self.assertEqual(len(hashes), 2)
        with mock.patch.object(mac, "environment_sha256", return_value="f" * 64) as digest:
            self.run_preflight()
        self.assertEqual(digest.call_args.args[4], "Background")  # exactly what the backend hashes

    def test_wrong_user_refuses(self):
        s = good_machine(); s.user = "someone"
        self.refused("user-is-dedicated-account", system=s)

    def test_the_console_owner_is_not_examined_but_the_operator_account_is(self):
        """RV-16 amended 2026-11-03: fast user switching makes the lab account own /dev/console."""
        s = good_machine(); s.console = UID
        self.assertFalse(hasattr(s, "console_uid"))
        report = self.run_preflight(s)
        self.assertEqual(report["verdict"], "ready")
        self.assertTrue(check(report, "user-is-not-operator-account")["ok"])
        self.assertNotIn("user-is-not-console-user", [c["check"] for c in report["checks"]])
        self.assertFalse(hasattr(har.System, "console_uid"))

    def test_operator_account_refusals(self):
        s = good_machine()
        for name, over in {"the lab account itself": dict(operator_account="braidlab"),
                           "unknown account": dict(operator_account="nobody-here"),
                           "missing": dict(operator_account=None), "empty": dict(operator_account=""),
                           "not an account name": dict(operator_account="Bad Name"),
                           "root": dict(operator_account="root"),
                           "system account": dict(operator_account="_sys")}.items():
            with self.subTest(name):
                report = self.refused("user-is-not-operator-account", system=s, **over)
                self.assertNotIn("environment-hash", [c["check"] for c in report["checks"]])
        s = good_machine()  # the lab account running with the operator's own uid
        s.passwd_by_uid = lambda uid: SimpleNamespace(pw_name="braidlab", pw_gid=20, pw_dir=HOME)
        s.ids = lambda: (FOUNDER_UID, FOUNDER_UID)
        self.refused("user-is-not-operator-account", system=s)

    def test_a_lab_account_below_uid_500_refuses(self):
        s = good_machine()
        s.ids = lambda: (499, 499)
        s.passwd_by_uid = lambda uid: SimpleNamespace(pw_name="braidlab", pw_gid=20, pw_dir=HOME)
        self.refused("user-is-not-operator-account", system=s)

    def test_the_operator_home_is_checked_even_when_the_account_listing_misses_it(self):
        s = good_machine(); s.homes = []; s.traversable = {FOUNDER_HOME}
        self.refused("founder-home-unreadable", system=s)
        s = good_machine(); s.homes = []
        self.assertTrue(check(self.run_preflight(s), "founder-home-unreadable")["ok"])

    def test_admin_or_wheel_refuses(self):
        for gid in (80, 0):
            s = good_machine(); s.gids = (20, gid)
            self.refused("user-is-standard", system=s)

    def test_founder_home_readable_refuses(self):
        s = good_machine(); s.traversable = {FOUNDER_HOME}
        self.refused("founder-home-unreadable", system=s)

    def test_any_other_local_home_traversable_refuses_and_no_homes_fails_closed(self):
        s = good_machine(); s.homes = [FOUNDER_HOME, "/Users/other"]; s.traversable = {"/Users/other"}
        self.refused("founder-home-unreadable", system=s)
        s = good_machine(); s.homes = []  # the operator's own home is still checked (see below)
        self.assertTrue(check(self.run_preflight(s), "founder-home-unreadable")["ok"])

    def test_supervisor_must_be_the_pinned_isolated_interpreter(self):
        s = good_machine(); s.running = "/Users/braidlab/venv/bin/python3"
        self.refused("supervisor-is-pinned-interpreter", system=s)
        s = good_machine(); s.isolated = False
        self.refused("supervisor-isolated-no-bytecode", system=s)
        s = good_machine(); s.no_bytecode = False
        self.refused("supervisor-isolated-no-bytecode", system=s)

    def test_code_and_interpreter_root_ancestors_must_be_root_owned(self):
        s = good_machine(); s.dir("/usr/local/libexec", 0o775, 0)
        self.refused("repository-code-ancestors-root-owned", "interpreter-root-ancestors-root-owned", system=s)
        s = good_machine(); s.dir(BRAID, 0o755, UID)
        self.refused("repository-code-ancestors-root-owned", system=s)

    def test_an_unlistable_directory_fails_the_tree_checks(self):
        s = good_machine(); s.unreadable = {PY_ROOT}
        self.refused("interpreter-root-tree-root-owned", system=s)
        s = good_machine(); s.unreadable = {f"{HOME}/cfg"}
        self.refused("config-dir-small", system=s)

    def test_account_home_loose_refuses(self):
        s = good_machine(); s.dir(HOME, 0o755, UID)
        self.refused("account-home-private", system=s)

    def test_claude_not_root_owned_refuses(self):
        s = good_machine(); s.file(CLAUDE, uid=FOUNDER_UID, sha=CLAUDE_SHA)
        self.refused("claude-root-owned-file", system=s)

    def test_claude_group_writable_refuses(self):
        s = good_machine(); s.file(CLAUDE, mode=0o775, sha=CLAUDE_SHA)
        self.refused("claude-root-owned-file", system=s)

    def test_claude_ancestor_not_root_owned_or_writable_refuses(self):
        s = good_machine(); s.dir(BRAID, 0o755, FOUNDER_UID)
        self.refused("claude-ancestors-root-owned", "interpreter-ancestors-root-owned", system=s)
        s = good_machine(); s.dir("/usr/local", 0o775, 0)
        self.refused("claude-ancestors-root-owned", system=s)

    def test_claude_hash_mismatch_and_missing_pin_refuse(self):
        s = good_machine(); s.hashes[CLAUDE] = "d" * 64
        self.refused("claude-sha256", system=s)
        self.refused("claude-sha256", claude_sha256=None)
        self.refused("claude-sha256", claude_sha256="XYZ")

    def test_claude_missing_refuses(self):
        s = good_machine(); del s.tree[CLAUDE]
        self.refused("claude-root-owned-file", "claude-sha256", system=s)

    def test_interpreter_hash_and_root_refuse(self):
        s = good_machine(); s.hashes[PY] = "d" * 64
        self.refused("interpreter-sha256", system=s)
        self.refused("interpreter-under-root", interpreter_root=f"{BRAID}/other")

    def test_interpreter_tree_with_foreign_file_or_escaping_link_refuses(self):
        s = good_machine(); s.file(f"{PY_ROOT}/lib/evil.py", 0o644, FOUNDER_UID)
        self.refused("interpreter-root-tree-root-owned", system=s)
        s = good_machine(); s.file(f"{PY_ROOT}/lib/link", 0o777); s.tree[f"{PY_ROOT}/lib/link"] = (stat.S_IFLNK, 0o755, 0, 1)
        s.links[f"{PY_ROOT}/lib/link"] = "/Users/juanyanez/secret"
        self.refused("interpreter-root-tree-root-owned", system=s)

    def test_repository_code_writable_refuses(self):
        s = good_machine(); s.file(f"{REPO}/scripts/har_t009_attempt.py", 0o666)
        self.refused("repository-code-root-owned", system=s)

    def test_sandbox_exec_refuses(self):
        s = good_machine(); s.hashes[mac.SANDBOX_EXEC] = "d" * 64
        self.refused("sandbox-exec-sha256", system=s)
        self.refused("sandbox-exec-sha256", sandbox_exec_sha256=None)
        s = good_machine(); s.file(mac.SANDBOX_EXEC, uid=FOUNDER_UID, sha=SANDBOX_SHA)
        self.refused("sandbox-exec-root-owned", system=s)

    def test_os_outside_the_supported_series_refuses(self):
        for product in ("26.4", "28.0", "270", "27"):
            s = good_machine(); s.facts = mac.HostFacts(product, "26B123", "arm64")
            report = self.refused("os-supported", system=s)
            self.assertIn(product, check(report, "os-supported")["detail"])

    def test_the_whole_27_series_is_supported(self):
        for product, build in (("27.0.1", "26A434"), ("27.2", "26B123"), ("27.10.3", "26C7")):
            s = good_machine(); s.facts = mac.HostFacts(product, build, "arm64")
            self.assertTrue(check(self.run_preflight(s), "os-supported")["ok"], product)

    def test_config_dir_checks_refuse(self):
        s = good_machine()
        for i in range(65):  # MDRV-03: more than 64 entries is refused
            s.file(f"{HOME}/cfg/f{i}", 0o600, UID)
        self.refused("config-dir-small", system=s)
        s = good_machine()
        for i in range(64):
            s.file(f"{HOME}/cfg/f{i}", 0o600, UID)
        self.assertTrue(check(self.run_preflight(s), "config-dir-small")["ok"])
        s = good_machine(); s.file(f"{HOME}/cfg/big", 0o600, UID, size=5 << 20)
        self.refused("config-dir-small", system=s)
        s = good_machine(); s.tree[f"{HOME}/cfg/link"] = (stat.S_IFLNK, 0o777, UID, 1)
        self.refused("config-dir-small", system=s)
        s = good_machine(); s.dir(f"{HOME}/cfg", 0o755, UID)
        self.refused("config-dir", system=s)
        self.refused("config-dir-not-home", config_dir=HOME)

    def test_small_config_dir_after_login_is_accepted(self):
        s = good_machine(); s.file(f"{HOME}/cfg/.claude.json", 0o600, UID, size=2000)
        report = self.run_preflight(s)
        self.assertEqual(report["observed"]["configDir"], {"entries": 1, "bytes": 2000})
        self.assertEqual(report["verdict"], "ready")

    def test_run_root_and_arena_checks_refuse(self):
        s = good_machine(); s.dir(f"{HOME}/run/run-123", 0o700, UID)
        self.refused("run-root-no-leftovers", system=s)
        s = good_machine(); s.dir(f"{HOME}/run", 0o750, UID)
        self.refused("run-root", system=s)
        s = good_machine(); del s.tree[f"{HOME}/arena"]
        self.refused("arena-parent", system=s)

    def test_output_directory_checks_refuse(self):
        out = f"{HOME}/out/t009-test"
        s = good_machine(); s.dir(out, 0o700, UID); s.file(f"{out}/summary.json", 0o600, UID)
        self.refused("out-dir", system=s)  # a finished or foreign bundle is never reused
        s = good_machine(); s.dir(out, 0o755, UID); s.writable_dirs.add(out)
        self.refused("out-dir", system=s)
        s = good_machine(); s.writable_dirs.clear()
        self.refused("out-dir", system=s)
        self.refused("paths-disjoint", out_dir=f"{HOME}/cfg/out")

    def test_an_output_directory_holding_only_the_session_counter_is_resumed(self):
        out = f"{HOME}/out/t009-test"
        s = good_machine(); s.dir(out, 0o700, UID); s.file(f"{out}/{q.SESSION_COUNT_FILE}", 0o600, UID)
        s.writable_dirs.add(out)
        report = self.run_preflight(s)
        self.assertEqual(report["verdict"], "ready")
        self.assertIn("resum", check(report, "out-dir")["detail"])

    def test_output_directory_must_be_normalized_and_its_parent_unlinked(self):
        self.refused("out-dir", out_dir=f"{HOME}/out/../cfg/x")
        self.refused("out-dir", out_dir="relative/out")
        s = good_machine(); s.dir(f"{HOME}/link", 0o700, UID); s.links[f"{HOME}/link"] = f"{HOME}/cfg"
        s.writable_dirs.add(f"{HOME}/link")
        self.refused("out-dir", "paths-disjoint", system=s, out_dir=f"{HOME}/link/x")

    def test_deny_variables_and_attempt_name_refuse(self):
        s = good_machine(); s.env = {hc.ENV_DENY[0]: "x"}
        self.refused("environment-deny-variables", system=s)
        self.refused("attempt-name", attempt="Bad Name")

    def test_invalid_policy_refuses(self):
        self.refused("policy-valid", proxy_port=80)
        self.refused("policy-valid", interpreter_sha256=None)

    def test_refusal_details_name_the_fix(self):
        s = good_machine(); s.dir(HOME, 0o755, UID)
        report = self.run_preflight(s)
        self.assertIn("chmod 700", check(report, "account-home-private")["detail"])

    def test_every_refusal_is_reported_together(self):
        s = good_machine(); s.user = "x"; s.gids = (80,)
        report = self.run_preflight(s, operator_account="nobody-here")
        self.assertGreaterEqual(len(report["failed"]), 3)


class DryRunTests(unittest.TestCase):
    ARGV = ["--attempt", "t009-test", "--claude", CLAUDE, "--claude-sha256", CLAUDE_SHA,
            "--interpreter", PY, "--interpreter-sha256", INTERP_SHA, "--interpreter-root", PY_ROOT,
            "--sandbox-exec-sha256", SANDBOX_SHA, "--operator-account", "juanyanez",
            "--config-dir", f"{HOME}/cfg", "--run-root", f"{HOME}/run",
            "--arena-parent", f"{HOME}/arena", "--out-dir", f"{HOME}/out/t009-test", "--dry-run"]

    def run_main(self, system, argv=None):
        out = io.StringIO()
        with mock.patch.object(har, "ROOT", Path(REPO)), redirect_stdout(out), \
                mock.patch.object(subprocess, "run", side_effect=AssertionError("native call")), \
                mock.patch.object(subprocess, "Popen", side_effect=AssertionError("native call")), \
                mock.patch.object(mac, "MacOSContainment", side_effect=AssertionError("backend built")), \
                mock.patch.object(q, "make_qualification_runner", side_effect=AssertionError("runner built")), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=AssertionError("transport built")):
            code = har.main(argv or self.ARGV, system=system)
        return code, json.loads(out.getvalue())

    def test_ready_dry_run_prints_a_verdict_and_starts_nothing(self):
        code, report = self.run_main(good_machine())
        self.assertEqual((code, report["verdict"], report["nativeRun"], report["dryRun"]),
                         (0, "ready", False, True))
        self.assertFalse(report["executionAuthorization"])

    def test_refused_dry_run_exits_nonzero_and_lists_failures(self):
        s = good_machine(); s.hashes[CLAUDE] = "d" * 64
        code, report = self.run_main(s)
        self.assertEqual((code, report["verdict"], report["failed"]), (2, "refused", ["claude-sha256"]))
        self.assertEqual(report["observed"]["claudeSha256"], "d" * 64)

    def test_missing_inputs_refuse_without_a_traceback(self):
        argv = [a for a in self.ARGV if a not in ("--claude-sha256", CLAUDE_SHA)]
        code, report = self.run_main(good_machine(), argv)
        self.assertEqual((code, report["verdict"]), (2, "refused"))
        with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
            har.parser().parse_args(["--dry-run"])  # required inputs missing
        without_operator = [a for a in self.ARGV if a not in ("--operator-account", "juanyanez")]
        with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
            har.parser().parse_args(without_operator)  # the operator account has no default
        without_out = self.ARGV[:self.ARGV.index("--out-dir")] + ["--dry-run"]
        with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
            har.parser().parse_args(without_out)  # --out-dir has no default inside the repository


class UsageCardTests(unittest.TestCase):
    def reader(self, answers, now=NOW, tz=timezone.utc):
        said = []
        items = iter(answers)

        def ask(_prompt):
            try:
                return next(items)
            except StopIteration:
                raise EOFError

        return har.UsageCardReader(ask, said.append, lambda: now, tz), said

    def test_fresh_reading_is_returned_in_the_quota_form(self):
        reader, _ = self.reader(["12", "30%", "n", "14:58"])
        self.assertEqual(reader.read("before"), {
            "source": "operator-typed-usage", "observedAt": "2026-11-04T14:58:00Z",
            "fiveHourPercent": 12, "weeklyPercent": 30, "extraUsageEnabled": False})

    def test_now_and_extra_usage(self):
        reader, _ = self.reader(["5", "5", "y", "now"])
        reading = reader.read("before")
        self.assertEqual((reading["observedAt"], reading["extraUsageEnabled"]), ("2026-11-04T15:00:00Z", True))

    def test_stale_future_and_unanswerable_readings_are_refused(self):
        for answers in (["12", "30", "n", "14:54"],                    # 6 minutes old
                        ["12", "30", "n", "15:05"],                    # future
                        ["12", "30", "n", "14:54:30"],                 # stale, with seconds
                        ["101", "102", "103"],                         # three bad percentages
                        ["12", "30", "maybe", "perhaps", "x"],
                        ["12", "30", "n", "25:00", "99:99", "soon"],
                        ["12", "30", "n", "", "", ""],
                        ["\u00b2", "\u00b3", "\u00b9"],             # superscript digits pass str.isdigit()
                        ["12", "30"]):                                 # input ends
            reader, said = self.reader(answers)
            self.assertIsNone(reader.read("before"), answers)
            self.assertTrue(any("refused" in line for line in said))

    def test_a_typo_is_asked_again_up_to_three_times_per_field(self):
        reader, said = self.reader(["12.5", "12", "thirty", "30", "yes", "25:00", "14:58:30"])
        self.assertEqual(reader.read("before"), {
            "source": "operator-typed-usage", "observedAt": "2026-11-04T14:58:30Z",
            "fiveHourPercent": 12, "weeklyPercent": 30, "extraUsageEnabled": True})
        self.assertGreaterEqual(sum("try again" in line for line in said), 3)
        reader, _ = self.reader(["x", "y", "12", "30", "no", "now"])  # the third try is the last
        self.assertEqual(reader.read("before")["fiveHourPercent"], 12)

    def test_the_operator_is_told_where_the_card_is_and_how_fresh_it_must_be(self):
        reader, said = self.reader(["1", "1", "n", "now"])
        reader.read("before")
        self.assertTrue(any("5 minutes" in line and "usage card" in line for line in said))

    def test_exactly_five_minutes_old_is_accepted_and_midnight_rolls_back(self):
        reader, _ = self.reader(["1", "1", "n", "14:55"])
        self.assertIsNotNone(reader.read("x"))
        just_after = datetime(2026, 11, 5, 0, 1, 0, tzinfo=timezone.utc)
        reader, _ = self.reader(["1", "1", "n", "23:58"], now=just_after)
        self.assertEqual(reader.read("x")["observedAt"], "2026-11-04T23:58:00Z")

    def test_seconds_distinguish_a_pre_and_post_reading_in_the_same_minute(self):
        reader, _ = self.reader(["1", "1", "n", "14:58:05"])
        first = reader.read("x")
        reader, _ = self.reader(["2", "1", "n", "14:58:50"])
        second = reader.read("x")
        self.assertLess(first["observedAt"], second["observedAt"])

    def test_local_time_zone_is_applied(self):
        plus_one = timezone(timedelta(hours=1))
        reader, _ = self.reader(["1", "1", "n", "15:58"], tz=plus_one)  # 14:58 UTC
        self.assertEqual(reader.read("x")["observedAt"], "2026-11-04T14:58:00Z")


class SessionQuotaTests(unittest.TestCase):
    def quota(self, readings):
        items = iter(readings)
        reader = SimpleNamespace(read=lambda role: next(items))
        said = []
        return har.SessionQuota(reader, said.append), said

    @staticmethod
    def reading(five):
        return {"fiveHourPercent": five}

    def test_the_pre_reading_serves_the_gate_and_the_driver_once_then_post_is_read(self):
        quota, _ = self.quota([self.reading(10), self.reading(11)])
        self.assertEqual(quota.next_pre(), self.reading(10))
        self.assertEqual(quota.read(), self.reading(10))   # the driver's pre
        self.assertEqual(quota.read(), self.reading(11))   # the driver's post
        self.assertEqual(quota.started, 1)

    def test_a_missing_pre_reading_is_passed_on_as_none(self):
        quota, _ = self.quota([None, None])
        self.assertIsNone(quota.next_pre())
        self.assertIsNone(quota.read())
        self.assertIsNone(quota.read())

    def test_more_than_two_points_warns_and_the_runner_owns_the_stop(self):
        quota, said = self.quota([self.reading(10), self.reading(14)])
        quota.next_pre(); quota.read(); quota.read()
        self.assertTrue(any("attempt stops" in line for line in said))
        self.assertFalse(hasattr(quota, "stopped"))  # harness_quota stops the runner; no second rule here


class AttemptTests(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(har, "ROOT", Path(REPO))
        patch.start()
        self.addCleanup(patch.stop)

    def call(self, args=None, system=None, answers=("t009-test",), backend=None, **extra):
        calls = {}
        backend = backend or mock.MagicMock()
        items = iter(answers)

        def backend_factory(policy, **kw):
            calls["backend"] = (policy, kw)
            return backend

        def make_runner(be, **kw):
            calls["runner"] = (be, kw)
            return SimpleNamespace(run=lambda out, environment: calls.setdefault("environment", environment)
                                   and {"effects": "none", "executionAuthorization": False})

        with mock.patch.object(q, "make_qualification_runner", side_effect=make_runner), \
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4") as f4, \
                mock.patch.object(q, "verify_bundle", return_value="e" * 64), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=lambda *a, **k: ("transport", a, k)):
            calls["f4"] = f4
            try:
                result = har.run_attempt(args or arguments(dry_run=False, founder_go=True), system or good_machine(),
                                         ask=lambda _p: next(items), say=lambda _m: None,
                                         now=lambda: NOW, backend_factory=backend_factory, **extra)
            except har.AttemptRefused as exc:
                return exc, calls, backend
        return result, calls, backend

    def test_the_operator_account_reaches_the_backend(self):
        result, calls, _ = self.call()
        self.assertEqual(result["verdict"], "bundle-written")
        self.assertEqual(calls["backend"][1]["operator_account"], "juanyanez")

    def test_refused_preflight_builds_nothing(self):
        s = good_machine(); s.user = "x"
        exc, calls, _ = self.call(system=s)
        self.assertIsInstance(exc, har.AttemptRefused)
        self.assertIn("user-is-dedicated-account", exc.reasons)
        self.assertIn("braidlab", exc.details["user-is-dedicated-account"])
        self.assertNotIn("runner", calls)
        self.assertNotIn("backend", calls)
        calls["f4"].assert_not_called()

    def test_the_founder_go_flag_and_the_typed_confirmation_are_required(self):
        exc, calls, _ = self.call(args=arguments(dry_run=False, founder_go=False))
        self.assertEqual(exc.reasons, ["founder-go-flag-missing"])
        self.assertNotIn("backend", calls)
        exc, calls, _ = self.call(answers=("yes",))
        self.assertEqual(exc.reasons, ["operator-cancelled"])
        self.assertNotIn("backend", calls)

    def test_wiring_of_the_backend_runner_and_transport_factory(self):
        result, calls, backend = self.call()
        self.assertEqual(result["verdict"], "bundle-written")
        self.assertEqual((result["bundleSha256"], result["executionAuthorization"]), ("e" * 64, False))
        policy, kw = calls["backend"]
        self.assertEqual((policy.account, policy.claude, policy.claude_sha256, policy.proxy_port),
                         ("braidlab", CLAUDE, CLAUDE_SHA, 18080))
        self.assertEqual(kw["probe_runner"], "f4")
        be, rkw = calls["runner"]
        self.assertIs(be, backend)
        self.assertEqual(rkw["arena_parent"], f"{HOME}/arena")
        self.assertNotIn("runner_options", rkw)
        f4_kwargs = calls["f4"].call_args.kwargs
        self.assertEqual(f4_kwargs["arena_parent"], f"{HOME}/arena")
        self.assertTrue(callable(f4_kwargs["workdir_factory"]))
        self.assertNotIn("launch_profile", f4_kwargs)  # the launch profile stays on (quickstart.md)
        self.assertEqual(calls["environment"]["probeCatalogSha256"], q.CATALOG_SHA256)
        self.assertEqual(calls["environment"]["claudeVersion"], mac.CLAUDE_VERSION)
        backend.close.assert_called_once()

    def test_attempt_records_are_in_memory_scoped_and_verify_against_their_hash(self):
        records = har.attempt_records("1" * 64, 1_800_000_000)
        qualification = lab.verify_qualification(records["qualification"],
                                                 expected_sha256=records["qualification_sha256"])
        host = hc.verify_host_qualification(records["host_qualification"],
                                            expected_sha256=records["host_qualification_sha256"])
        self.assertEqual((qualification.environment_sha256, host.environment_sha256), ("1" * 64, "1" * 64))
        self.assertEqual(qualification.expires_at, 1_800_000_000 + har.ATTEMPT_RECORD_SECONDS)
        self.assertEqual(json.loads(records["qualification"])["evidenceSha256"], "0" * 64)

    def test_the_transport_factory_asks_for_one_pre_reading_per_session_and_counts_sessions(self):
        answers = ["t009-test", "10", "5", "n", "now", "10", "5", "n", "now"]
        captured = {}

        def make_runner(be, **kw):
            captured.update(kw)
            return SimpleNamespace(run=lambda out, environment: {})

        items = iter(answers)
        with mock.patch.object(q, "make_qualification_runner", side_effect=make_runner), \
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4"), \
                mock.patch.object(q, "verify_bundle", return_value="e" * 64), \
                mock.patch.object(har, "NativeClaudeTransport",
                                  side_effect=lambda *a, **k: SimpleNamespace(args=a, kwargs=k)), \
                mock.patch.object(har.tempfile, "mkdtemp", side_effect=lambda **k: f"{HOME}/run/work-x"), \
                mock.patch.object(mac, "_remove_tree"):
            har.run_attempt(arguments(dry_run=False, founder_go=True), good_machine(), ask=lambda _p: next(items),
                            say=lambda _m: None, now=lambda: NOW,
                            backend_factory=lambda policy, **kw: mock.MagicMock())
            first = captured["transport_factory"]()
            self.assertEqual(first.kwargs["quota"], ("probe", 0))
            self.assertEqual(first.kwargs["pre_reading"]["fiveHourPercent"], 10)
            self.assertEqual(captured["read_quota"]()["fiveHourPercent"], 10)  # the driver's pre: no new prompt
            second = captured["transport_factory"]()
            self.assertEqual(second.kwargs["quota"], ("probe", 1))

    def failing_run(self, error, spent=0):
        """Run the attempt with a runner that spends ``spent`` sessions, then raises ``error``."""
        captured = {}

        def make_runner(be, **kw):
            captured.update(kw)

            def run(out, environment):
                for _ in range(spent):
                    captured["transport_factory"]()
                raise error
            return SimpleNamespace(run=run)

        answers = iter(["t009-test"] + ["10", "5", "n", "now"] * 3)
        backend = mock.MagicMock()
        with mock.patch.object(q, "make_qualification_runner", side_effect=make_runner), \
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4"), \
                mock.patch.object(q, "verify_bundle", return_value="e" * 64), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=lambda *a, **k: SimpleNamespace()), \
                mock.patch.object(har.tempfile, "mkdtemp", side_effect=lambda **k: f"{HOME}/run/work-x"), \
                mock.patch.object(mac, "_remove_tree") as remove:
            with self.assertRaises(har.AttemptFailed) as caught:
                har.run_attempt(arguments(dry_run=False, founder_go=True), good_machine(),
                                ask=lambda _p: next(answers), say=lambda _m: None, now=lambda: NOW,
                                backend_factory=lambda policy, **kw: backend)
        backend.close.assert_called_once()
        if spent:
            remove.assert_called()
        return caught.exception

    def test_a_failure_after_sessions_were_spent_reports_how_many(self):
        failure = self.failing_run(q.ProbeError("bundle-exists"), spent=2)
        self.assertEqual((failure.sessions_started, failure.reason), (2, "ProbeError: bundle-exists"))
        self.assertEqual(failure.out_dir, f"{HOME}/out/t009-test")
        failure = self.failing_run(OSError("disk"), spent=0)
        self.assertEqual((failure.sessions_started, failure.reason), (0, "OSError"))

    def test_an_interrupt_is_reported_like_any_other_failure(self):
        failure = self.failing_run(KeyboardInterrupt(), spent=1)
        self.assertEqual((failure.sessions_started, failure.reason), (1, "KeyboardInterrupt"))

    def test_main_prints_a_verdict_json_for_refusals_with_details_and_for_failures(self):
        out = io.StringIO()
        refusal = har.AttemptRefused(["out-dir"], {"out-dir": "exists"})
        with mock.patch.object(har, "run_attempt", side_effect=refusal), redirect_stdout(out):
            code = har.main(DryRunTests.ARGV[:-1] + ["--founder-go"], system=good_machine())
        report = json.loads(out.getvalue())
        self.assertEqual((code, report["verdict"], report["details"]), (2, "refused", {"out-dir": "exists"}))
        out = io.StringIO()
        failure = har.AttemptFailed("ProbeError: bundle-exists", 2, f"{HOME}/out/t009-test")
        with mock.patch.object(har, "run_attempt", side_effect=failure), redirect_stdout(out):
            code = har.main(DryRunTests.ARGV[:-1] + ["--founder-go"], system=good_machine())
        report = json.loads(out.getvalue())
        self.assertEqual((code, report["verdict"], report["quota"]["started"]), (2, "error", 2))
        self.assertEqual(report["outDir"], f"{HOME}/out/t009-test")
        self.assertFalse(report["executionAuthorization"])
        self.assertIn("counter", report["next"])

    def test_the_driver_writes_no_file_directory_or_temporary_path_in_a_double_run(self):
        def forbidden(*_a, **_k):
            raise AssertionError("write")

        real_open, real_os_open = open, os.open

        def guarded_open(file, mode="r", *a, **k):  # reads (hashing the interpreter) are fine
            if set(mode) & set("wax+"):
                raise AssertionError("write")
            return real_open(file, mode, *a, **k)

        def guarded_os_open(path, flags, *a, **k):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                raise AssertionError("write")
            return real_os_open(path, flags, *a, **k)

        writers = [mock.patch("builtins.open", guarded_open), mock.patch.object(os, "open", guarded_os_open),
                   mock.patch.object(Path, "write_text", forbidden), mock.patch.object(Path, "write_bytes", forbidden),
                   mock.patch.object(Path, "mkdir", forbidden),
                   mock.patch.object(os, "mkdir", forbidden), mock.patch.object(os, "makedirs", forbidden),
                   mock.patch.object(os, "replace", forbidden), mock.patch.object(har.tempfile, "mkdtemp", forbidden),
                   mock.patch("shutil.copy", forbidden), mock.patch("shutil.copytree", forbidden)]
        with contextlib.ExitStack() as stack:
            for writer in writers:
                stack.enter_context(writer)
            result, _, _ = self.call(system=good_machine())
        self.assertEqual(result["verdict"], "bundle-written")


class SystemTests(unittest.TestCase):
    """The real ``System`` reads, on throw-away temporary directories only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_a_traverse_only_home_counts_as_traversable(self):
        home = self.root / "home"
        home.mkdir()
        os.chmod(home, 0o100)  # x only (mode 711 for others behaves the same): a path under it opens
        self.addCleanup(os.chmod, home, 0o700)
        self.assertTrue(har.System().can_traverse(str(home)))
        os.chmod(home, 0o000)
        self.assertFalse(har.System().can_traverse(str(home)))

    @unittest.skipIf(os.geteuid() == 0, "root reads everything")
    def test_walk_raises_on_an_unlistable_subdirectory(self):
        hidden = self.root / "a" / "hidden"
        hidden.mkdir(parents=True)
        (hidden / "f").write_text("x")
        os.chmod(hidden, 0o000)
        self.addCleanup(os.chmod, hidden, 0o700)
        with self.assertRaises(OSError):
            har.System().walk(str(self.root), 100)

    def test_walk_lists_entries_and_stops_past_the_limit(self):
        (self.root / "d").mkdir()
        (self.root / "d" / "f").write_text("x")
        system = har.System()
        self.assertEqual(sorted(p for p, _ in system.walk(str(self.root), 10)),
                         [str(self.root / "d"), str(self.root / "d" / "f")])
        self.assertIsNone(system.walk(str(self.root), 1))

    def test_the_session_facts_are_the_backends_own_reading(self):
        facts = mac.SessionFacts(503, 100_104, "Background")
        with mock.patch.object(mac, "session_facts", return_value=facts):
            self.assertIs(har.System().session(), facts)

    def test_the_supervisor_facts_come_from_the_running_interpreter(self):
        system = har.System()
        self.assertEqual(system.supervisor(), os.path.realpath(sys.executable))
        self.assertEqual(system.interpreter_flags(), (bool(sys.flags.isolated), bool(sys.dont_write_bytecode)))
        self.assertIsInstance(system.other_homes("braidlab"), list)

    def test_other_homes_counts_human_accounts_only(self):
        """macOS ``nobody`` has uid -2, which ``pwd`` reports as 4294967294; its home is /var/empty."""
        entries = [pwd.struct_passwd((name, "*", uid, 20, "", home, "/bin/zsh")) for name, uid, home in (
            ("root", 0, "/var/root"), ("_spotlight", 89, "/var/empty"), ("nobody", 4294967294, "/var/empty"),
            ("administrator", 501, "/Users/administrator"), ("juanyanez", 502, "/Users/juanyanez"),
            ("braidlab", 503, "/Users/braidlab"))]
        with mock.patch.object(har.pwd, "getpwall", return_value=entries), \
                mock.patch.object(har.os, "stat", side_effect=OSError):
            self.assertEqual(har.System().other_homes("braidlab"),
                             ["/Users/administrator", "/Users/juanyanez"])



# --- attempt 1 of 2026-11-03: what the driver prints when the real run fails --------------------------------

SECRET = "Zq4Xw9Kp2Vb7Nm5Rt8Hj3Lc6"


def backend_record(entry="launch", refused="self-check-failed", **extra):
    """A record as ``MacOSContainment`` leaves it in ``run_evidence`` (with fields the driver must not print)."""
    return {"entry": entry, "backend": "macos-dedicated-user-sandbox-exec", "operator": {"account": "juanyanez", "uid": 501},
            "account": {"gids": [20], "homeMode": 448}, "os": {"product": "27.0.1", "build": "26A123"},
            "qualificationSha256": "f" * 64, "refused": refused} | extra


F4_NET06_FAILED = [{"probe": "FS-01", "expected": "denied", "observed": "denied"},
                   {"probe": "NET-01", "expected": "denied", "observed": "denied"},
                   {"probe": "CRED-01", "expected": "denied", "observed": "denied"},
                   {"probe": "PROC-01", "expected": "denied", "observed": "denied"},
                   {"probe": "NET-06", "expected": "allowed", "observed": "error"}]


class ErrorDiagnosisTests(unittest.TestCase):
    """Step 5 and 2: a failed real run prints the redacted scan report and the backend's refusal evidence."""

    def setUp(self):
        patch = mock.patch.object(har, "ROOT", Path(REPO))
        patch.start()
        self.addCleanup(patch.stop)

    def failing_run(self, error, backend, inventory=()):
        def make_runner(be, **kw):
            return SimpleNamespace(run=lambda out, environment: (_ for _ in ()).throw(error))

        answers = iter(["t009-test"])
        with mock.patch.object(q, "make_qualification_runner", side_effect=make_runner), \
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4"), \
                mock.patch.object(q, "credential_inventory", return_value=list(inventory)), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=lambda *a, **k: SimpleNamespace()), \
                mock.patch.object(mac, "_remove_tree"):
            with self.assertRaises(har.AttemptFailed) as caught:
                har.run_attempt(arguments(dry_run=False, founder_go=True), good_machine(),
                                ask=lambda _p: next(answers), say=lambda _m: None, now=lambda: NOW,
                                backend_factory=lambda policy, **kw: backend)
        return caught.exception

    def secret_refusal(self):
        text = json.dumps({"probe": "PROC-06", "machNames": ["com.apple.ok.name", f"a.b.{SECRET}"]}) + "\n"
        with self.assertRaises(q.ProbeError) as raised:
            q.scan_for_secrets({"results.jsonl": text}, [SECRET], origins=["credential#1"])
        return raised.exception

    def test_the_failure_carries_the_scan_report_with_the_source_of_a_credential_literal(self):
        backend = SimpleNamespace(close=lambda: None, run_evidence=[])
        inventory = [("x" * 20, {"file": ".claude.json", "path": "$.a"}),
                     (SECRET, {"file": ".claude.json", "path": "$.oauthAccount.billingType"})]
        failure = self.failing_run(self.secret_refusal(), backend, inventory)
        self.assertEqual(failure.reason, "ProbeError: secret-in-artifact")
        self.assertEqual(failure.detail, {"total": 1, "findings": [
            {"file": "results.jsonl", "line": 1, "path": "$.machNames[1]", "rule": "listed-literal",
             "length": len(SECRET), "origin": "credential#1",
             "source": {"file": ".claude.json", "path": "$.oauthAccount.billingType"}}]})
        self.assertNotIn(SECRET, json.dumps(failure.detail))

    def test_the_failure_carries_probe_ids_and_verdicts_and_nothing_else_of_the_backend_record(self):
        records = [backend_record(), {"entry": "fixture", "os": {"product": "27"}},  # no refusal: dropped
                   backend_record(refused="self-check-failed", compileCheck="exec-denied",
                                  preSessionCheck=F4_NET06_FAILED),
                   backend_record("launch-probe", "profile-compile-failed")]
        failure = self.failing_run(q.ProbeError("bundle-exists"), SimpleNamespace(close=lambda: None, run_evidence=records))
        self.assertIsNone(failure.detail)
        self.assertEqual(failure.evidence, [
            {"entry": "launch", "refused": "self-check-failed"},
            {"entry": "launch", "refused": "self-check-failed", "compileCheck": "exec-denied",
             "preSessionCheck": F4_NET06_FAILED},
            {"entry": "launch-probe", "refused": "profile-compile-failed"}])
        rendered = json.dumps(failure.evidence)
        for private in ("juanyanez", "braidlab", "operator", "homeMode", "qualificationSha256", "26A123"):
            self.assertNotIn(private, rendered)

    def test_exit_codes_and_accounting_errno_are_printed_as_integers_only(self):
        records = [backend_record(compileCheck="exec-denied", compileExit={"denied": 71, "allowed": 1, "x": 2},
                                  exitCode=2),
                   backend_record("fixture", "process-accounting-failed", accountingErrno=1, accountingFlavor=4,
                                  exitCode=None, compileExit={"denied": 71, "allowed": "/Users/x"}),
                   backend_record("launch", "other", exitCode="/Users/x", accountingErrno=10 ** 9,
                                  compileExit="text"),
                   backend_record("launch", "bool-code", exitCode=True)]
        self.assertEqual(har.refusal_evidence(SimpleNamespace(run_evidence=records)), [
            {"entry": "launch", "refused": "self-check-failed", "compileCheck": "exec-denied", "exitCode": 2,
             "compileExit": {"denied": 71, "allowed": 1}},
            {"entry": "fixture", "refused": "process-accounting-failed", "accountingErrno": 1,
             "accountingFlavor": 4, "compileExit": {"denied": 71}},
            {"entry": "launch", "refused": "other"},
            {"entry": "launch", "refused": "bool-code"}])

    def test_malformed_or_foreign_evidence_is_dropped_not_printed(self):
        records = ["text", None, {"entry": "/Users/x", "refused": "has space"},
                   {"entry": "launch", "refused": "ok-code", "preSessionCheck": [
                       {"probe": "FS-01", "expected": "denied", "observed": "maybe"},
                       {"probe": "../x", "expected": "denied", "observed": "denied"}, "row",
                       {"probe": "NET-01", "expected": "denied", "observed": "allowed"}]}]
        self.assertEqual(har.refusal_evidence(SimpleNamespace(run_evidence=records)), [
            {"entry": "launch", "refused": "ok-code", "preSessionCheck": [
                {"probe": "NET-01", "expected": "denied", "observed": "allowed"}]}])
        self.assertEqual(har.refusal_evidence(SimpleNamespace(run_evidence=mock.MagicMock())), [])
        self.assertEqual(har.refusal_evidence(SimpleNamespace()), [])
        many = [backend_record(refused=f"reason-{i}") for i in range(30)]
        self.assertEqual(len(har.refusal_evidence(SimpleNamespace(run_evidence=many))), har.MAX_EVIDENCE)

    def test_main_prints_the_scan_report_and_the_evidence_in_the_error_verdict(self):
        failure = har.AttemptFailed("ProbeError: secret-in-artifact", 1, f"{HOME}/out/t009-test",
                                    {"total": 1, "findings": [{"file": "results.jsonl", "line": 3, "rule": "long-run"}]},
                                    [{"entry": "launch", "refused": "self-check-failed"}])
        out = io.StringIO()
        with mock.patch.object(har, "run_attempt", side_effect=failure), redirect_stdout(out):
            code = har.main(DryRunTests.ARGV[:-1] + ["--founder-go"], system=good_machine())
        report = json.loads(out.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual((report["verdict"], report["reason"], report["quota"], report["nativeRun"]),
                         ("error", "ProbeError: secret-in-artifact", {"started": 1}, True))
        self.assertEqual(report["scan"]["findings"][0]["rule"], "long-run")
        self.assertEqual(report["preSessionEvidence"], [{"entry": "launch", "refused": "self-check-failed"}])
        bare = har.AttemptFailed("OSError", 0, "x")
        out = io.StringIO()
        with mock.patch.object(har, "run_attempt", side_effect=bare), redirect_stdout(out):
            har.main(DryRunTests.ARGV[:-1] + ["--founder-go"], system=good_machine())
        self.assertNotIn("scan", json.loads(out.getvalue()))
        self.assertNotIn("preSessionEvidence", json.loads(out.getvalue()))

    def test_the_credential_literals_come_from_one_read_and_reach_the_runner(self):
        captured = {}

        def make_runner(be, **kw):
            captured.update(kw)
            return SimpleNamespace(run=lambda out, environment: {})

        with mock.patch.object(q, "make_qualification_runner", side_effect=make_runner), \
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4"), \
                mock.patch.object(q, "verify_bundle", return_value="e" * 64), \
                mock.patch.object(q, "credential_inventory", return_value=[("v1" * 8, {"file": "f", "path": "$"})]), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=lambda *a, **k: SimpleNamespace()), \
                mock.patch.object(mac, "_remove_tree"):
            har.run_attempt(arguments(dry_run=False, founder_go=True), good_machine(), ask=lambda _p: "t009-test",
                            say=lambda _m: None, now=lambda: NOW, backend_factory=lambda policy, **kw: mock.MagicMock())
        self.assertEqual(captured["read_credentials"](), ["v1" * 8])


class FakeBackend:
    """The two methods ``launch`` calls before it spawns, the evidence list and the one ``auth`` launch."""

    def __init__(self, *, check=None, raises=None, leftovers=(), auth=(0, "present"), auth_raises=None,
                 auth_stdout=b"", startup=None, startup_raises=None):
        self.calls, self.run_evidence, self.closed = [], [], False
        self._check, self._raises, self._leftovers = check, raises, list(leftovers)
        self._auth, self._auth_raises, self._auth_stdout = auth, auth_raises, auth_stdout
        self._startup, self._startup_raises = startup or {}, startup_raises
        self.policy = SimpleNamespace(claude=CLAUDE)

    @contextlib.contextmanager
    def _exclusive(self, entry):
        self.calls.append(("exclusive", entry))
        yield

    def _pre_session(self, entry, workdir, *, probes):
        self.calls.append(("pre_session", entry, str(workdir), probes))
        self.run_evidence.extend(self._leftovers)
        if self._raises is not None:
            if isinstance(self._raises, lab.LabError):
                self.run_evidence.append(backend_record(entry, self._raises.reason,
                                                        **({"compileCheck": "exec-denied"} if self._check else {}),
                                                        **({"preSessionCheck": self._check} if self._check else {})))
            raise self._raises
        return {"entry": entry, "compileCheck": "exec-denied", "preSessionCheck": self._check}, str(workdir), 502

    def _startup_launch(self, argv, stdin, k):
        self.calls.append(("startup", argv, stdin, k["wall_seconds"], k["capture_stderr"], k["no_egress"]))
        if self._startup_raises is not None:
            raise self._startup_raises
        v = {"exit_code": 1, "stdout": b"", "stderr_tail": b"", "egress": {"connections": 0}} | self._startup
        self.run_evidence.append({"entry": "launch", "authToken": "present", "exitCode": v["exit_code"]})
        return SimpleNamespace(exit_code=v["exit_code"], timed_out=False, cancelled=False, settled=True,
                               stdout=v["stdout"], stderr_tail=v["stderr_tail"], egress=v["egress"])

    def launch(self, argv, stdin, **k):
        if argv[1:2] != ("auth",):
            return self._startup_launch(argv, stdin, k)
        self.calls.append(("launch", argv, stdin, str(k["cwd"]), k["wall_seconds"], k["max_output_bytes"]))
        if self._auth_raises is not None:
            raise self._auth_raises
        exit_code, mark = self._auth
        self.run_evidence.append({"entry": "launch", "authToken": mark, "exitCode": exit_code})
        return SimpleNamespace(exit_code=exit_code, timed_out=exit_code is None, stdout=self._auth_stdout)

    def close(self):
        self.closed = True


F4_OK = [{"probe": p, "expected": e, "observed": e} for p, e in mac.F4_PROBES]


class SelfCheckTests(unittest.TestCase):
    ARGV = DryRunTests.ARGV[:-1] + ["--self-check", "--founder-go"]

    def setUp(self):
        patch = mock.patch.object(har, "ROOT", Path(REPO))
        patch.start()
        self.addCleanup(patch.stop)

    def run_check(self, backend, *, f4=None, argv=None, system=None, expect_code=None):
        built = {}
        out = io.StringIO()

        def backend_factory(policy, **kw):
            built["backend"] = (policy, kw)
            return backend

        def never(*_a, **_k):
            raise AssertionError("not part of the self-check")

        probe = f4 or (lambda probe_id, be: dict(mac.F4_PROBES)[probe_id])
        with mock.patch.object(q, "make_f4_probe_runner", return_value=probe) as f4_factory, \
                mock.patch.object(q, "make_qualification_runner", side_effect=never), \
                mock.patch.object(q, "verify_bundle", side_effect=never), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=never), \
                mock.patch.object(har, "UsageCardReader", side_effect=never), \
                mock.patch.object(har, "SessionQuota", side_effect=never), \
                mock.patch.object(har, "run_attempt", side_effect=never), \
                mock.patch("builtins.input", side_effect=never), \
                mock.patch.object(mac, "MacOSContainment", side_effect=backend_factory), \
                mock.patch.object(har.tempfile, "mkdtemp", side_effect=lambda **k: f"{HOME}/run/work-x"), \
                mock.patch.object(mac, "_remove_tree") as remove, redirect_stdout(out):
            code = har.main(argv or self.ARGV, system=system or good_machine())
        built["f4_factory"], built["removed"] = f4_factory, remove
        return code, json.loads(out.getvalue()), built

    def test_a_passing_check_prints_every_f4_verdict_and_authorizes_nothing(self):
        backend = FakeBackend(check=F4_OK)
        code, report, built = self.run_check(backend)
        self.assertEqual(code, 0)
        self.assertEqual(report, {
            "verdict": "self-check-ok", "attempt": "t009-test", "preSessionCheck": F4_OK, "compileCheck": "exec-denied",
            "auth": {"stage": "auth", "noModel": True, "authToken": "present", "reason": "ok", "exitCode": 0},
            "startup": {"stage": "startup", "noModel": True, "reachedInit": False, "exitCode": 1,
                        "reason": "exit-before-init", "timedOut": False, "authToken": "present",
                        "egress": {"connections": 0, "denied": 0, "allowed": 0, "bytesUp": 0, "bytesDown": 0,
                                   "upstreamFailed": 0},
                        "egressLeak": False, "stderrTail": []},
            "refusal": None, "stage": None, "backendRefusals": [], "probeRuns": [], "nativeRun": True, "sessionsStarted": 0,
            "usageReadings": 0, "executionAuthorization": False})
        (*head, startup_call) = backend.calls
        self.assertEqual(head, [("exclusive", "launch"), ("pre_session", "launch", f"{HOME}/run/work-x", True),
                                ("launch", (CLAUDE, "auth", "status"), b"", f"{HOME}/run/work-x",
                                 har.AUTH_WALL_SECONDS, har.AUTH_MAX_OUTPUT_BYTES)])
        self.assertEqual(startup_call[0], "startup")
        self.assertEqual(startup_call[2:], (q.PROBE_PROMPT, har.STARTUP_WALL_SECONDS, True, True))
        self.assertTrue(backend.closed)
        built["removed"].assert_called_with(f"{HOME}/run/work-x")  # one workdir each for the check, auth and startup
        self.assertEqual(built["removed"].call_count, 3)

    def test_the_auth_stage_reports_a_closed_reason_from_the_exit_code_and_the_token_mark(self):
        cases = ((dict(auth=(1, "absent")), "auth-missing", 1), (dict(auth=(1, "present")), "auth-rejected", 1),
                 (dict(auth=(None, "present")), "timed-out", None), (dict(auth=(0, "absent")), "ok", 0))
        for options, reason, exit_code in cases:
            with self.subTest(options):
                code, report, _ = self.run_check(FakeBackend(check=F4_OK, **options))
                self.assertEqual(report["auth"]["reason"], reason)
                self.assertIn(reason, har.AUTH_REASONS)
                self.assertEqual(report["auth"]["exitCode"], exit_code)
                ready = reason == "ok"
                self.assertEqual((code, report["verdict"]), (0, "self-check-ok") if ready
                                 else (2, "self-check-auth-failed"))
                self.assertEqual((report["sessionsStarted"], report["usageReadings"]), (0, 0))
                self.assertFalse(report["executionAuthorization"])

    def test_the_auth_stage_never_reports_the_output_of_the_command(self):
        backend = FakeBackend(check=F4_OK, auth=(1, "present"), auth_stdout=b'{"email": "' + SECRET.encode() + b'"}')
        report = self.run_check(backend)[1]
        self.assertNotIn(SECRET, json.dumps(report))

    def test_a_backend_refusal_of_the_auth_launch_is_a_fixed_reason(self):
        for raised, refusal in ((lab.LabError("auth-token-invalid"), "auth-token-invalid"),
                                (RuntimeError(SECRET), "backend-failed")):
            with self.subTest(refusal):
                code, report, _ = self.run_check(FakeBackend(check=F4_OK, auth_raises=raised))
                self.assertEqual((code, report["verdict"]), (2, "self-check-auth-failed"))
                self.assertEqual((report["auth"]["reason"], report["auth"]["refusal"], report["auth"]["exitCode"]),
                                 ("refused", refusal, None))
                self.assertNotIn(SECRET, json.dumps(report))

    def test_the_auth_stage_does_not_run_after_a_refused_pre_session_check(self):
        backend = FakeBackend(raises=lab.LabError("self-check-failed"))
        report = self.run_check(backend, f4=lambda probe, be: "error")[1]
        self.assertEqual(report["auth"], {"stage": "auth", "reason": "not-run"})
        self.assertFalse([c for c in backend.calls if c[0] == "launch"])

    INIT = b'{"type":"system","subtype":"init","apiKeySource":"none"}\n'

    def test_the_startup_stage_runs_the_session_launch_of_the_probe_runner_with_no_egress(self):
        backend = FakeBackend(check=F4_OK, startup={"exit_code": 0, "stdout": self.INIT})
        report = self.run_check(backend)[1]
        call = [c for c in backend.calls if c[0] == "startup"][0]
        argv = call[1]
        plan = hc.build_plan(hc.ClaudeRequest(session_id="00000000-0000-4000-8000-000000000000", model="haiku",
                                              max_turns=1), q.PROBE_PROMPT)

        def without_session(args, skip):
            return [a for a in args if a != args[args.index("--session-id") + 1]] if skip else list(args)

        self.assertEqual(argv[0], CLAUDE)
        self.assertEqual(without_session(argv[1:], True), without_session(plan.argv[1:], True))
        self.assertEqual(call[2:], (q.PROBE_PROMPT, har.STARTUP_WALL_SECONDS, True, True))  # stderr kept, no egress
        self.assertTrue(report["startup"]["reachedInit"])
        self.assertEqual((report["startup"]["exitCode"], report["startup"]["reason"]), (0, "ok"))
        self.assertEqual(report["verdict"], "self-check-ok")

    def test_the_startup_stage_is_diagnostic_and_never_fails_the_self_check_by_itself(self):
        for startup in ({"exit_code": 1}, {"exit_code": 0}, {"exit_code": 1, "stdout": self.INIT}):
            with self.subTest(startup):
                code, report, _ = self.run_check(FakeBackend(check=F4_OK, startup=startup))
                self.assertEqual((code, report["verdict"]), (0, "self-check-ok"))
                self.assertIn(report["startup"]["reason"], q.EXIT_REASONS)

    def test_a_tunnel_that_opened_in_the_startup_stage_ends_the_self_check(self):
        for leak in ({"allowed": 1}, {"bytesUp": 5}, {"upstreamFailed": 1}):
            with self.subTest(leak):
                code, report, _ = self.run_check(FakeBackend(check=F4_OK, startup={"egress": leak}))
                self.assertEqual((code, report["verdict"]), (2, "self-check-egress-leak"))
                self.assertTrue(report["startup"]["egressLeak"])
        code, report, _ = self.run_check(FakeBackend(check=F4_OK, startup={"egress": {"bytesUp": 4000}}))
        self.assertEqual((code, report["verdict"], report["startup"]["egress"]["bytesUp"]), (2, "self-check-egress-leak", 4000))
        for bad in (None, {"allowed": -1}, {"denied": "2"}):  # missing or malformed counters fail closed
            self.assertEqual(self.run_check(FakeBackend(check=F4_OK, startup={"egress": bad}))[1]["verdict"],
                             "self-check-egress-leak")
        report = self.run_check(FakeBackend(check=F4_OK, startup={"egress": {"connections": 2, "denied": 2}}))[1]
        self.assertFalse(report["startup"]["egressLeak"])
        self.assertEqual(report["startup"]["egress"]["denied"], 2)

    def test_a_refused_startup_launch_is_a_fixed_reason(self):
        for raised, refusal in ((lab.LabError("auth-token-invalid"), "auth-token-invalid"),
                                (RuntimeError(SECRET), "backend-failed")):
            with self.subTest(refusal):
                report = self.run_check(FakeBackend(check=F4_OK, startup_raises=raised))[1]
                self.assertEqual(report["startup"], {"stage": "startup", "noModel": True, "reason": "refused",
                                                     "refusal": refusal, "reachedInit": False})
                self.assertNotIn(SECRET, json.dumps(report))

    def test_the_startup_stage_does_not_run_after_a_refused_pre_session_check(self):
        backend = FakeBackend(raises=lab.LabError("self-check-failed"))
        report = self.run_check(backend, f4=lambda probe, be: "error")[1]
        self.assertEqual(report["startup"], {"stage": "startup", "reason": "not-run"})
        self.assertFalse([c for c in backend.calls if c[0] == "startup"])

    def test_the_stderr_tail_is_redacted_line_by_line_and_the_founder_account_replaced(self):
        tail = "\n".join([
            "starting",
            f"token {SECRET} was rejected",
            f"cannot read {FOUNDER_HOME}/Library/x for juanyanez",
            "key sk-ant-api03-abcdefghijkl",
            f"read {HOME}/claude/.claude.json failed: EPERM",
            "x" * 50 + "A1" * 30,
            "\x1b[31mred\x1b[0m"]).encode()
        backend = FakeBackend(check=F4_OK, startup={"stderr_tail": tail})
        report = har.startup_stage(backend, lambda: Path(f"{HOME}/run/work-x"), [SECRET], "juanyanez")
        self.assertEqual(report["stderrTail"], [
            "starting", "<redacted:listed-literal>", "cannot read <operator-home>/Library/x for <operator>",
            "<redacted:anthropic-api-key>", f"read {HOME}/claude/.claude.json failed: EPERM",
            "<redacted:long-run>", "?[31mred?[0m"])
        self.assertNotIn(SECRET, json.dumps(report))

    def test_the_operator_account_is_replaced_in_any_case_and_an_empty_one_changes_nothing(self):
        raw = b"/Users/JuanYanez/x and dir-juanyanez and /Users/ here"
        self.assertEqual(q.redact_stderr_tail(raw, [], operator_account="juanyanez"),
                         ["<operator-home>/x and dir-<operator> and /Users/ here"])
        self.assertEqual(q.redact_stderr_tail(raw, [], operator_account=""), [raw.decode()])

    def test_redaction_keeps_the_last_twenty_lines_and_drops_a_tail_cut_mid_line(self):
        lines = [f"line {n}" for n in range(30)]
        self.assertEqual(q.redact_stderr_tail("\n".join(lines).encode(), [], operator_account="op"), lines[-20:])
        cut = ("half-a-token\n" + "\n".join(lines)).encode().rjust(mac.STDERR_TAIL_BYTES, b" ")
        self.assertNotIn("half-a-token", " ".join(q.redact_stderr_tail(cut, [], operator_account="op")))

    def test_auth_reason_is_a_pure_function_of_exit_code_and_token_mark(self):
        self.assertEqual([har.auth_reason(*args) for args in ((0, None), (1, "absent"), (2, "present"), (1, None))],
                         ["ok", "auth-missing", "auth-rejected", "auth-rejected"])
        self.assertEqual(har.auth_reason(None, "present", timed_out=True), "timed-out")


    def test_the_backend_is_built_like_the_real_run(self):
        _, _, built = self.run_check(FakeBackend(check=F4_OK))
        policy, kw = built["backend"]
        self.assertEqual((policy.account, policy.claude, policy.proxy_port), ("braidlab", CLAUDE, 18080))
        self.assertEqual(kw["operator_account"], "juanyanez")
        self.assertTrue(callable(kw["probe_runner"]))
        self.assertEqual(sorted(kw), sorted(["probe_runner", "clock", "operator_account", "qualification",
                                             "qualification_sha256", "host_qualification",
                                             "host_qualification_sha256"]))
        f4 = built["f4_factory"].call_args.kwargs
        self.assertEqual(f4["arena_parent"], f"{HOME}/arena")
        self.assertNotIn("launch_profile", f4)  # the launch-probe profile stays on, as in the real run

    def test_a_failed_f4_probe_is_reported_and_the_probes_not_reached_are_run_and_marked(self):
        check = F4_NET06_FAILED[:3]
        check[2] = {"probe": "CRED-01", "expected": "denied", "observed": "error"}
        backend = FakeBackend(check=check, raises=lab.LabError("self-check-failed"),
                              leftovers=[backend_record("launch-probe", "profile-compile-failed")])
        asked = []
        code, report, _ = self.run_check(backend, f4=lambda probe, be: asked.append(probe) or "error"
                                         if probe == "PROC-01" else asked.append(probe) or "allowed")
        self.assertEqual(code, 2)
        self.assertEqual((report["verdict"], report["refusal"], report["stage"], report["compileCheck"]),
                         ("self-check-refused", "self-check-failed", "f4-probes", "exec-denied"))
        self.assertEqual(report["preSessionCheck"], [
            *check, {"probe": "PROC-01", "expected": "denied", "observed": "error", "supplementary": True},
            {"probe": "NET-06", "expected": "allowed", "observed": "allowed", "supplementary": True}])
        self.assertEqual(asked, ["PROC-01", "NET-06"])
        self.assertEqual(report["backendRefusals"], [{"entry": "launch-probe", "refused": "profile-compile-failed"},
                                                     {"entry": "launch", "refused": "self-check-failed",
                                                      "compileCheck": "exec-denied", "preSessionCheck": check}])
        self.assertFalse(report["executionAuthorization"])

    def test_an_escape_stops_the_probes_like_the_backend_does_and_marks_the_rest_not_run(self):
        check = F4_NET06_FAILED[:3]
        check[2] = {"probe": "CRED-01", "expected": "denied", "observed": "allowed"}
        backend = FakeBackend(check=check, raises=lab.LabError("self-check-allowed"))
        asked = []
        code, report, _ = self.run_check(backend, f4=lambda probe, be: asked.append(probe) or "allowed")
        self.assertEqual((code, report["refusal"], report["stage"]), (2, "self-check-allowed", "f4-probes"))
        self.assertEqual(asked, [])  # nothing more runs under a profile that has just leaked
        self.assertEqual(report["preSessionCheck"], [
            *check, {"probe": "PROC-01", "expected": "denied", "observed": "not-run", "supplementary": True},
            {"probe": "NET-06", "expected": "allowed", "observed": "not-run", "supplementary": True}])

    def test_a_compile_check_refusal_has_no_compile_mark_and_runs_all_five_probes(self):
        backend = FakeBackend(raises=lab.LabError("self-check-failed"))
        code, report, _ = self.run_check(backend, f4=lambda probe, be: "error")
        self.assertEqual((code, report["refusal"], report["stage"], report["compileCheck"]),
                         (2, "self-check-failed", "compile-check", None))
        self.assertEqual([c["probe"] for c in report["preSessionCheck"]], [p for p, _ in mac.F4_PROBES])
        self.assertTrue(all(c["supplementary"] and c["observed"] == "error" for c in report["preSessionCheck"]))

    def test_exit_codes_of_the_probe_runs_are_reported_without_output(self):
        backend = FakeBackend(raises=lab.LabError("self-check-failed"))
        ran = [backend_record("fixture", None, exitCode=3), backend_record("launch-probe", None, exitCode=None),
               backend_record("fixture", None, exitCode="/Users/x"), backend_record("fixture", "refused-run", exitCode=9)]
        code, report, _ = self.run_check(backend, f4=lambda probe, be: backend.run_evidence.extend(ran) or "error")
        self.assertEqual(report["probeRuns"], [{"entry": "fixture", "exitCode": 3}])

    def test_the_noise_level_of_a_run_is_printed_as_integers_only(self):
        backend = FakeBackend(raises=lab.LabError("self-check-failed"))
        ran = [backend_record("fixture", None, exitCode=0, unrelatedProcesses=12, unreadableProcesses=9),
               backend_record("launch", None, exitCode=0, unrelatedProcesses="/Users/x", unreadableProcesses=True)]
        code, report, _ = self.run_check(backend, f4=lambda probe, be: backend.run_evidence.extend(ran) or "error")
        self.assertEqual(report["probeRuns"], [
            {"entry": "fixture", "exitCode": 0, "unrelatedProcesses": 12, "unreadableProcesses": 9},
            {"entry": "launch", "exitCode": 0}])
        refused = backend_record("fixture", "process-accounting-failed", unrelatedProcesses=3,
                                 unreadableProcesses=2, unattributedProcesses=5)
        self.assertEqual(har.refusal_evidence(SimpleNamespace(run_evidence=[refused])), [
            {"entry": "fixture", "refused": "process-accounting-failed", "unrelatedProcesses": 3,
             "unreadableProcesses": 2}])

    def test_a_refusal_before_the_compile_check_names_that_stage(self):
        report = self.run_check(FakeBackend(raises=lab.LabError("workspace-leftovers")))[1]
        self.assertEqual((report["refusal"], report["stage"]), ("workspace-leftovers", "mechanism-or-workspace"))

    def test_a_probe_runner_that_raises_or_answers_oddly_is_an_error_verdict(self):
        def f4(probe, be):
            if probe == "PROC-01":
                raise RuntimeError(SECRET)
            return "maybe"
        backend = FakeBackend(check=F4_OK[:1], raises=lab.LabError("self-check-failed"))
        report = self.run_check(backend, f4=f4)[1]
        self.assertTrue(all(c["observed"] == "error" for c in report["preSessionCheck"][1:]))
        self.assertNotIn(SECRET, json.dumps(report))

    def test_an_unexpected_exception_is_a_verdict_not_a_traceback(self):
        code, report, _ = self.run_check(FakeBackend(raises=RuntimeError("boom " + SECRET)))
        # the backend wraps this into backend-failed itself; the driver does too if one slips through
        self.assertEqual((code, report["refusal"], report["stage"]), (2, "backend-failed", "mechanism-or-workspace"))
        self.assertNotIn(SECRET, json.dumps(report))
        backend = FakeBackend(check=F4_OK)
        backend._exclusive = mock.MagicMock(side_effect=OSError("disk"))
        code, report, _ = self.run_check(backend)
        self.assertEqual((code, report["verdict"], report["reason"]), (2, "error", "OSError"))
        self.assertTrue(backend.closed)

    def test_it_needs_the_founder_go_and_a_ready_preflight_and_builds_nothing_otherwise(self):
        for argv, system, reasons in ((DryRunTests.ARGV[:-1] + ["--self-check"], good_machine(), ["founder-go-flag-missing"]),
                                      (self.ARGV, self.bad_machine(), ["claude-sha256"])):
            built = []
            out = io.StringIO()
            with mock.patch.object(mac, "MacOSContainment", side_effect=lambda *a, **k: built.append(1)), \
                    mock.patch.object(q, "make_f4_probe_runner", side_effect=lambda **k: built.append(2)), \
                    redirect_stdout(out):
                code = har.main(argv, system=system)
            report = json.loads(out.getvalue())
            self.assertEqual((code, report["verdict"], report["reasons"], report["nativeRun"]), (2, "refused", reasons, False))
            self.assertEqual(built, [])

    @staticmethod
    def bad_machine():
        s = good_machine()
        s.hashes[CLAUDE] = "d" * 64
        return s

    def test_self_check_and_dry_run_exclude_each_other(self):
        with self.assertRaises(SystemExit), mock.patch("sys.stderr", io.StringIO()):
            har.parser().parse_args(DryRunTests.ARGV + ["--self-check"])
        args = har.parser().parse_args(DryRunTests.ARGV[:-1] + ["--self-check"])
        self.assertEqual((args.self_check, args.dry_run, args.founder_go), (True, False, False))
        self.assertFalse(har.parser().parse_args(DryRunTests.ARGV).self_check)

    def test_the_two_backend_methods_it_calls_exist_with_the_shape_launch_uses(self):
        import inspect
        parameters = inspect.signature(mac.MacOSContainment._pre_session).parameters
        self.assertEqual(list(parameters), ["self", "entry", "workdir", "probes"])
        self.assertIs(parameters["probes"].kind, inspect.Parameter.KEYWORD_ONLY)
        self.assertTrue(callable(mac.MacOSContainment._exclusive))
        source = inspect.getsource(mac.MacOSContainment.launch)
        self.assertIn('with self._exclusive("launch"):', source)
        self.assertIn('self._pre_session("launch", cwd, probes=True)', source)
        self.assertIn("F4_PROBES", inspect.getsource(mac.MacOSContainment._run_probes))

    def test_the_record_keys_it_reads_are_the_ones_the_backend_writes(self):
        import inspect
        source = inspect.getsource(mac.MacOSContainment)
        for key in ('"compileCheck"', '"preSessionCheck"', '"refused"'):
            self.assertIn(key, source)

if __name__ == "__main__":
    unittest.main()
