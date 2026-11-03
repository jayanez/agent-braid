# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 operator driver: every refusal, the dry-run and the NC-6 reader, with doubles only.

Nothing native runs here: no sandbox-exec, no claude, no network, no sudo, no account. The host is a
fake tree (``FakeSystem``); the backend, the runner and the transport are replaced where the driver
would otherwise build them.
"""
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
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
        self.console = FOUNDER_UID
        self.gids = (20, 12)
        self.founder_readable = False
        self.env: dict[str, str] = {}
        self.facts = mac.HostFacts("27.0.1", "26A123", "arm64")
        self.links: dict[str, str] = {}
        self.writable_dirs = {"/Users/braidlab/out"}

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
    def console_uid(self): return self.console
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
        prefix = path.rstrip("/") + "/"
        found = [(p, self.lstat(p)) for p in sorted(self.tree) if p.startswith(prefix)]
        return None if len(found) > limit else found
    def sha256(self, path): return self.hashes.get(path)
    def can_traverse(self, path): return self.founder_readable
    def writable(self, path): return path in self.writable_dirs
    def environ(self): return self.env
    def host_facts(self): return self.facts
    def account_facts(self, account, entry, uid): return mac.AccountFacts((20,), 0o700)


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
                 arena_parent=f"{HOME}/arena", out_dir=f"{HOME}/out/t009-test", proxy_port=18080,
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

    def test_wrong_user_refuses(self):
        s = good_machine(); s.user = "someone"
        self.refused("user-is-dedicated-account", system=s)

    def test_console_user_refuses(self):
        s = good_machine(); s.console = UID
        self.refused("user-is-not-console-user", system=s)

    def test_admin_or_wheel_refuses(self):
        for gid in (80, 0):
            s = good_machine(); s.gids = (20, gid)
            self.refused("user-is-standard", system=s)

    def test_founder_home_readable_refuses(self):
        s = good_machine(); s.founder_readable = True
        self.refused("founder-home-unreadable", system=s)

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
        s = good_machine(); s.facts = mac.HostFacts("27.2", "26B123", "arm64")
        report = self.refused("os-supported", system=s)
        self.assertIn("27.2", check(report, "os-supported")["detail"])

    def test_config_dir_checks_refuse(self):
        s = good_machine()
        for i in range(70):
            s.file(f"{HOME}/cfg/f{i}", 0o600, UID)
        self.refused("config-dir-small", system=s)
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
        s = good_machine(); s.dir(f"{HOME}/out/t009-test", 0o700, UID)
        self.refused("out-dir", system=s)
        s = good_machine(); s.writable_dirs.clear()
        self.refused("out-dir", system=s)
        self.refused("paths-disjoint", out_dir=f"{HOME}/cfg/out")

    def test_deny_variables_and_attempt_name_refuse(self):
        s = good_machine(); s.env = {hc.ENV_DENY[0]: "x"}
        self.refused("environment-deny-variables", system=s)
        self.refused("attempt-name", attempt="Bad Name")

    def test_invalid_policy_refuses(self):
        self.refused("policy-valid", proxy_port=80)
        self.refused("policy-valid", interpreter_sha256=None)

    def test_every_refusal_is_reported_together(self):
        s = good_machine(); s.user = "x"; s.console = UID; s.gids = (80,)
        report = self.run_preflight(s)
        self.assertGreaterEqual(len(report["failed"]), 3)


class DryRunTests(unittest.TestCase):
    ARGV = ["--attempt", "t009-test", "--claude", CLAUDE, "--claude-sha256", CLAUDE_SHA,
            "--interpreter", PY, "--interpreter-sha256", INTERP_SHA, "--interpreter-root", PY_ROOT,
            "--sandbox-exec-sha256", SANDBOX_SHA, "--config-dir", f"{HOME}/cfg", "--run-root", f"{HOME}/run",
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
            "source": "claude-desktop-usage-card", "observedAt": "2026-11-04T14:58:00Z",
            "fiveHourPercent": 12, "weeklyPercent": 30, "extraUsageEnabled": False})

    def test_now_and_extra_usage(self):
        reader, _ = self.reader(["5", "5", "y", "now"])
        reading = reader.read("before")
        self.assertEqual((reading["observedAt"], reading["extraUsageEnabled"]), ("2026-11-04T15:00:00Z", True))

    def test_stale_future_malformed_and_missing_are_refused(self):
        for answers in (["12", "30", "n", "14:54"],      # 6 minutes old
                        ["12", "30", "n", "15:05"],      # future
                        ["101", "30", "n", "now"],       # out of range
                        ["abc", "30", "n", "now"],
                        ["12", "30", "maybe", "now"],
                        ["12", "30", "n", "25:00"],
                        ["12", "30", "n", ""],
                        ["12", "30"]):                   # input ends
            reader, said = self.reader(answers)
            self.assertIsNone(reader.read("before"), answers)
            self.assertTrue(any("refused" in line for line in said))

    def test_exactly_five_minutes_old_is_accepted_and_midnight_rolls_back(self):
        reader, _ = self.reader(["1", "1", "n", "14:55"])
        self.assertIsNotNone(reader.read("x"))
        just_after = datetime(2026, 11, 5, 0, 1, 0, tzinfo=timezone.utc)
        reader, _ = self.reader(["1", "1", "n", "23:58"], now=just_after)
        self.assertEqual(reader.read("x")["observedAt"], "2026-11-04T23:58:00Z")

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

    def test_more_than_two_points_warns_and_more_than_ten_stops_the_next_session(self):
        quota, said = self.quota([self.reading(10), self.reading(14), self.reading(14), self.reading(30)])
        quota.next_pre(); quota.read(); quota.read()
        self.assertTrue(any("attempt stops" in line for line in said))
        self.assertIsNone(quota.stopped)
        quota.next_pre(); quota.read(); quota.read()
        self.assertEqual(quota.stopped, "quota-hard-stop")
        with self.assertRaises(RuntimeError):
            quota.next_pre()


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
                mock.patch.object(q, "make_f4_probe_runner", return_value="f4"), \
                mock.patch.object(q, "verify_bundle", return_value="e" * 64), \
                mock.patch.object(har, "NativeClaudeTransport", side_effect=lambda *a, **k: ("transport", a, k)):
            try:
                result = har.run_attempt(args or arguments(dry_run=False, founder_go=True), system or good_machine(),
                                         ask=lambda _p: next(items), say=lambda _m: None,
                                         now=lambda: NOW, backend_factory=backend_factory, **extra)
            except har.AttemptRefused as exc:
                return exc, calls, backend
        return result, calls, backend

    def test_refused_preflight_builds_nothing(self):
        s = good_machine(); s.user = "x"
        exc, calls, _ = self.call(system=s)
        self.assertIsInstance(exc, har.AttemptRefused)
        self.assertIn("user-is-dedicated-account", exc.reasons)
        self.assertEqual(calls, {})

    def test_the_founder_go_flag_and_the_typed_confirmation_are_required(self):
        exc, calls, _ = self.call(args=arguments(dry_run=False, founder_go=False))
        self.assertEqual((exc.reasons, calls), (["founder-go-flag-missing"], {}))
        exc, calls, _ = self.call(answers=("yes",))
        self.assertEqual((exc.reasons, calls), (["operator-cancelled"], {}))

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
        self.assertNotIn("launch_profile", rkw)
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

    def test_nothing_is_written_by_the_driver_itself(self):
        s = good_machine()
        with mock.patch("builtins.open", side_effect=AssertionError("write")):
            result, _, _ = self.call(system=s)
        self.assertEqual(result["verdict"], "bundle-written")


if __name__ == "__main__":
    unittest.main()
