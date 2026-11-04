# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T005 macOS containment backend: policy, refusals, supervision and proxy.

Unit level only: no dedicated account is created, ``claude`` never runs and no live
probe is executed. Host facts, the account and the probe runner are stubbed; the
supervisor tests replace ``sandbox-exec`` with a pass-through script so only the
rlimit preamble, watchdog and settlement run, and the per-user process listing is
always stubbed so no real process of the developer is ever swept.
"""
from contextlib import ExitStack, contextmanager
import ctypes
from dataclasses import replace
import errno
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import ssl
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_lab as lab
from agent_braid.system_one import canonical
from tests.test_harness_lab import make_inventory, native_manifest

NOW = 1_800_000_000
FACTS = mac.HostFacts("27.0.1", "26A434", "arm64")
ACCOUNT = "braid-lab"
OPERATOR = "founder-op"
FIXTURE = b'import json\nopen("out.txt", "w").write("ok")\nprint(json.dumps({"seq": 0, "kind": "start"}))\n'
INTERPRETER = os.path.realpath(sys.executable)
# Stands in for sandbox-exec: drops its options and execs the target unchanged.
PASS_THROUGH = (f"#!{INTERPRETER} -IS\nimport os, sys\n"
                "args = sys.argv[sys.argv.index('--') + 1:]\nos.execv(args[0], args)\n")
# Stands in for claude without forking: prints its environment names, then its stdin.
FAKE_CLAUDE = (f"#!{INTERPRETER} -IS\nimport os, sys\n"
               "print(' '.join(sorted(os.environ)))\nsys.stdout.write(sys.stdin.read())\n")
BASELINE = {(1, 1)}
ACCOUNT_FACTS = mac.AccountFacts(gids=(20,), home_mode=0o700)
HAS_SANDBOX_EXEC = sys.platform == "darwin" and Path(mac.SANDBOX_EXEC).is_file()


def digest(path: str) -> str:
    return sha256(Path(path).read_bytes()).hexdigest()


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def write_exec(path: str, text: str) -> str:
    Path(path).write_text(text)
    os.chmod(path, 0o755)
    return path


class Machine:
    """Temporary run root, config dir, fake Claude and fake sandbox-exec."""

    def __init__(self, test: unittest.TestCase, **policy):
        self.root = os.path.realpath(tempfile.mkdtemp(prefix="braid-t005-"))
        test.addCleanup(shutil.rmtree, self.root, True)
        for name in ("run", "config", "bin", "home"):
            os.mkdir(f"{self.root}/{name}", 0o700)
        self.home = f"{self.root}/home"
        os.chmod(f"{self.root}/bin", 0o755)
        self.claude = write_exec(f"{self.root}/bin/claude", FAKE_CLAUDE)
        self.sandbox = write_exec(f"{self.root}/bin/sandbox-exec", PASS_THROUGH)
        values = dict(
            account=ACCOUNT, run_root=f"{self.root}/run", config_dir=f"{self.root}/config",
            claude=self.claude, claude_sha256=digest(self.claude), claude_version=mac.CLAUDE_VERSION,
            interpreter=INTERPRETER, interpreter_sha256=digest(INTERPRETER),
            interpreter_root=os.path.dirname(INTERPRETER),
            sandbox_exec_sha256=digest(self.sandbox), proxy_port=free_port())
        self.policy = mac.ContainmentPolicy(**(values | policy))

    def repin(self, **change) -> None:
        self.policy = replace(self.policy, **change)

    def environment(self, facts: mac.HostFacts = FACTS) -> str:
        with mock.patch.object(mac, "SANDBOX_EXEC", self.sandbox):
            return mac.environment_sha256(self.policy, facts, os.getuid(), ACCOUNT_FACTS)

    def candidate(self) -> str:
        return tempfile.mkdtemp(prefix="cand-", dir=self.policy.run_root)

    def leftovers(self) -> list[str]:
        """Backend-owned run and compile directories still present."""
        return [n for n in os.listdir(self.policy.run_root) if n.startswith(("run-", "compile-"))]


def records(environment: str, *, backend: str = mac.BACKEND, host: str = "claude",
            host_environment: str | None = None, expires: int = NOW + 3600):
    qualification = canonical({"format": lab.QUALIFICATION_FORMAT, "backend": backend, "kind": "native",
                               "environmentSha256": environment, "enforced": list(lab.ENFORCED_EFFECTS),
                               "expiresAt": expires, "evidenceSha256": "e" * 64})
    host_record = canonical({"format": "braid-harness-host-qualification/v0.1", "host": host,
                             "environmentSha256": host_environment or environment,
                             "enforced": list(lab.ENFORCED_EFFECTS), "expiresAt": expires,
                             "evidenceSha256": "e" * 64})
    return dict(qualification=qualification, qualification_sha256=sha256(qualification).hexdigest(),
                host_qualification=host_record, host_qualification_sha256=sha256(host_record).hexdigest())


def expected_probes(probe: str, _backend) -> str:
    return dict(mac.F4_PROBES)[probe]


def make_backend(machine: Machine, *, runner=expected_probes, operator: str = OPERATOR,
                 **record_args) -> mac.MacOSContainment:
    return mac.MacOSContainment(machine.policy, probe_runner=runner, clock=lambda: NOW,
                                operator_account=operator, **records(machine.environment(), **record_args))


@contextmanager
def host(machine: Machine, *, facts: mac.HostFacts = FACTS, uid: int | None = None, darwin: bool = True,
         stub_compile_check: bool = True, processes=None, env: dict | None = None,
         mechanism_uid: int | None = None, gids: tuple[int, ...] = (20,), pw_gid: int = 20,
         operator_uid: int | None = None, home: str | None = None, links=None, resident=None):
    """Stub every Darwin fact; ``processes`` stubs the per-user process listing.

    Runs as the test runner's uid, which must be at least 500 (``_MIN_HUMAN_UID``, RV-16).
    The parent environment is cleared of ``ENV_DENY`` names (a developer shell may
    carry them), then ``env`` is applied. The full executable trust check applies to
    the fixtures in the temporary tree; the developer's interpreter (group-writable
    below ``/opt/homebrew/Cellar`` or ``/opt/hostedtoolcache``) keeps only its hash pin.
    """
    uid = os.getuid() if uid is None else uid
    trusted_file = mac._trusted_file

    def trusted(path, expected, missing, drift):
        if path.startswith(machine.root + "/"):
            return trusted_file(path, expected, missing, drift)
        if mac._file_sha256(path) != expected:
            raise lab.LabError(drift)

    def getpwnam(name):
        if name == OPERATOR:  # a different, ordinary human account (uid >= 500)
            return SimpleNamespace(pw_uid=max(os.getuid(), 500) + 1 if operator_uid is None else operator_uid,
                                   pw_gid=20, pw_dir="/Users/founder-op")
        if name != ACCOUNT:
            raise KeyError(name)
        return SimpleNamespace(pw_uid=uid, pw_gid=pw_gid, pw_dir=home or machine.home)

    with ExitStack() as stack:
        stack.enter_context(mock.patch.dict(os.environ))
        for name in mac.ENV_DENY:
            os.environ.pop(name, None)
        os.environ.update(env or {})
        patches = {
            "_darwin": lambda: darwin, "host_facts": lambda: facts,
            "pwd": SimpleNamespace(getpwnam=getpwnam), "SANDBOX_EXEC": machine.sandbox,
            "_MECHANISM_UID": os.getuid() if mechanism_uid is None else mechanism_uid,
            "_user_processes": processes or (lambda uid: BASELINE),
            "_resident_bytes": resident or (lambda processes: 0), "_account_groups": lambda account, gid: gids,
            "_process_links": links or (lambda identity: (None, None)),
            "_tagged": lambda pid, tag: False,
            "_trusted_file": trusted,
        }
        for name, value in patches.items():
            stack.enter_context(mock.patch.object(mac, name, value))
        if stub_compile_check:
            stack.enter_context(mock.patch.object(mac.MacOSContainment, "_compile_check",
                                                  lambda self, entry, evidence: None))
        yield


class PolicyTests(unittest.TestCase):
    def test_profile_is_deny_default_and_deterministic(self):
        policy = Machine(self).policy
        for entry in mac.ENTRIES:
            profile = policy.render(entry).decode()
            self.assertEqual(profile, policy.render(entry).decode())
            lines = profile.splitlines()
            self.assertEqual(lines[:2], ["(version 1)", "(deny default)"])
            self.assertNotIn("allow default", profile)
            self.assertNotIn(mac.COMPILE_PROBE, profile)
            network = [line for line in lines if "network" in line]
            self.assertEqual(network, [f'(allow network-outbound (remote tcp "localhost:{policy.proxy_port}"))'])
            writes = {line for line in lines if "file-write" in line and line.startswith("(allow")}
            allowed = {'(allow file-write-data (literal "/dev/null"))',
                       '(allow file-read* file-write* (subpath (param "CANDIDATE")) (subpath (param "TMPDIR")))'}
            if entry in ("launch", mac.LAUNCH_PROBE):
                allowed.add(f'(allow file-read* file-write* (subpath "{policy.config_dir}"))')
            self.assertEqual(writes, allowed)
            self.assertEqual(lines[-2], '(deny file-read* file-write* (subpath "/System/Volumes/Data"))')
            # RV-20: metadata of run_root itself and this run's directory, never "all of run_root"
            self.assertNotIn(f'(subpath "{policy.run_root}")', profile)
            metadata = next(line for line in lines if line.startswith("(allow file-read-metadata"))
            self.assertTrue(metadata.endswith(f'(literal "{policy.run_root}") (literal (param "RUNDIR")))'))
            for denied in ("mach-lookup", "kern.bootargs", "dtracehelper", "network-bind", "network-inbound", "process-exec*)",
                           "ipc-", '(subpath "/System")', "remote ip", "remote udp"):
                self.assertNotIn(denied, profile)
        launch, fixture = policy.render("launch").decode(), policy.render("fixture").decode()
        self.assertIn(f'(allow process-exec (literal "{policy.claude}"))', launch)
        self.assertNotIn(policy.interpreter, launch)
        self.assertIn(f'(allow process-exec (literal "{policy.interpreter}"))', fixture)
        self.assertNotIn(policy.claude, fixture)
        self.assertNotIn(f'"{policy.config_dir}"', fixture)
        for call in (lambda: policy.render("other"), lambda: policy.child_environment("other", "/x")):
            with self.assertRaises(lab.LabError) as caught:
                call()
            self.assertEqual(caught.exception.reason, "invalid-entry")

    def test_claude_profiles_carry_the_closed_system_information_list_and_nothing_wider(self):
        policy = Machine(self).policy
        rules = {
            "sysctl": '(allow sysctl-read (sysctl-name "hw.pagesize") (sysctl-name "hw.pagesize_compat") '
                      '(sysctl-name "hw.ephemeral_storage") (sysctl-name "kern.osproductversion") '
                      '(sysctl-name "kern.osvariant_status") (sysctl-name "kern.iossupportversion") '
                      '(sysctl-name "security.mac.lockdown_mode_state") (sysctl-name-prefix "hw.optional."))',
            "locale": '(allow file-read-data (literal "/usr/share/locale/UTF-8/LC_CTYPE") '
                      '(literal "/usr/share/locale/C.UTF-8/LC_CTYPE") '
                      '(literal "/usr/share/locale/en_US.UTF-8/LC_CTYPE"))',
            "metadata": '(allow file-read-metadata (literal "/etc") (literal "/var"))'}
        for entry in ("launch", mac.LAUNCH_PROBE):
            lines = policy.render(entry).decode().splitlines()
            for rule in rules.values():
                self.assertEqual(lines.count(rule), 1, rule)
            sysctl = [line for line in lines if "sysctl" in line]
            self.assertEqual(sysctl, [rules["sysctl"]])
            for denied in ("kern.bootargs", "mach-lookup", "dtracehelper", "process-exec*", "network-bind",
                           "network-inbound", "/usr/bin/curl", mac.COMPILE_PROBE, '(subpath "/etc")',
                           '(subpath "/var")', '(subpath "/usr/share/locale")'):
                self.assertNotIn(denied, "\n".join(lines))
            self.assertEqual(lines[-2], '(deny file-read* file-write* (subpath "/System/Volumes/Data"))')
            self.assertNotIn("/System/Volumes/Data", "\n".join(lines[:-2]))
        fixture = policy.render("fixture").decode()
        for rule in rules.values():
            self.assertNotIn(rule, fixture)
        self.assertNotIn("sysctl", fixture)

    def test_fixture_interpreter_never_writes_bytecode(self):
        policy = Machine(self).policy
        self.assertEqual(policy.exec_probe("fixture")[1], "-B")
        self.assertEqual(policy.child_environment("fixture", "/r/tmp")["PYTHONDONTWRITEBYTECODE"], "1")

    def test_launch_probe_is_launch_plus_exactly_the_interpreter_literal(self):
        policy = Machine(self).policy
        launch, probe = policy.render("launch").decode(), policy.render(mac.LAUNCH_PROBE).decode()
        token = f'(literal "{policy.interpreter}")'
        self.assertNotEqual(launch, probe)
        old, new = launch.splitlines(), probe.splitlines()
        self.assertEqual(len(old), len(new))
        differing = [(a, b) for a, b in zip(old, new) if a != b]
        # the exec rule, the read/map rule and the metadata rule; every added item is the interpreter,
        # its prefix (the read the fixture entry also has) or one of their ancestor directories
        kinds = ("(allow process-exec", "(allow file-read* file-map-executable", "(allow file-read-metadata")
        self.assertEqual([after.startswith(kind) for (_, after), kind in zip(differing, kinds)], [True] * 3)
        for before, after in differing:
            rest = after
            for item in re.findall(r'\((?:literal|subpath) "[^"]*"\)', after):
                if item not in before:
                    path = item.split('"')[1]
                    self.assertTrue(policy.interpreter == path or mac._under(policy.interpreter, path), item)
                    rest = rest.replace(" " + item, "", 1)
            self.assertEqual(rest, before)
        self.assertEqual(differing[0][1].count(token), 1)
        self.assertIn(f'(subpath "{policy.interpreter_root}")', differing[1][1])
        self.assertNotIn(f'(subpath "{policy.interpreter_root}")', launch)
        self.assertNotIn(policy.interpreter, "".join(old))
        self.assertEqual(policy.executables(mac.LAUNCH_PROBE), (*policy.executables("launch"), policy.interpreter))
        self.assertEqual(policy.child_environment(mac.LAUNCH_PROBE, "/r/tmp"),
                         policy.child_environment("launch", "/r/tmp"))
        self.assertIn(mac.LAUNCH_PROBE, mac.ENTRIES)

    def test_probe_catalog_hash_is_derived_from_the_probes_module_and_cannot_drift(self):
        from agent_braid import harness_qualification_probes as probes
        machine = Machine(self)
        self.assertEqual(machine.policy.probe_catalog_sha256, probes.CATALOG_SHA256)
        self.assertEqual(replace(machine.policy, probe_catalog_sha256=probes.CATALOG_SHA256).probe_catalog_sha256,
                         probes.CATALOG_SHA256)
        with self.assertRaises(lab.LabError) as caught:
            replace(machine.policy, probe_catalog_sha256="4" * 64)
        self.assertEqual(caught.exception.reason, "invalid-policy")
        self.assertTrue(probes.policy_binds_catalog(machine.policy))

    def test_exec_probe_is_an_allowed_executable_per_entry(self):
        policy = Machine(self).policy
        self.assertEqual(policy.exec_probe("fixture"), [policy.interpreter, "-B", "-I", "-S", "-c", "pass"])
        self.assertEqual(policy.exec_probe("launch"), [policy.claude, "--version"])
        self.assertEqual(policy.exec_probe(mac.LAUNCH_PROBE), [policy.claude, "--version"])
        for entry in mac.ENTRIES:
            self.assertIn(policy.exec_probe(entry)[0], policy.executables(entry))
        with self.assertRaises(lab.LabError):
            policy.exec_probe("other")

    def test_limits_carry_the_founder_disk_bounds(self):
        self.assertEqual((mac.LIMITS["diskBytes"], mac.LIMITS["diskFiles"]), (2 * 1024**3, 100_000))

    def test_invalid_policies_refuse(self):
        machine = Machine(self)
        root = machine.root
        cases = {
            "quote": dict(config_dir=f'{root}/con"fig'), "relative": dict(run_root="run"),
            "dots": dict(run_root=f"{root}/x/../run"), "space": dict(run_root=f"{root}/r un"),
            "hash": dict(claude_sha256="X" * 64), "port": dict(proxy_port=80),
            "port-type": dict(proxy_port="9999"), "endpoint": dict(refresh_endpoints=("evil.com:80",)),
            "duplicate": dict(refresh_endpoints=("api.anthropic.com:443",)),
            "helpers": dict(helpers=(("/usr/bin/rg",),)), "helpers-list": dict(helpers=[]),
            "exec-in-write-set": dict(claude=f"{root}/run/claude"),
            "exec-in-config": dict(helpers=((f"{root}/config/rg", "a" * 64),)),
            "nested-write": dict(config_dir=f"{root}/run/config"),
            "system-write": dict(run_root="/System/Library/run"),
            "write-above-system": dict(run_root="/usr"),
            "write-in-interpreter-root": dict(run_root=f"{machine.policy.interpreter_root}/run"),
            "shallow-interpreter-root": dict(interpreter_root="/opt"),
            "probe-allowed": dict(helpers=((mac.COMPILE_PROBE, "a" * 64),)),
            "mechanism-allowed": dict(helpers=((mac.SANDBOX_EXEC, "a" * 64),)),
            "interpreter-root": dict(interpreter_root=f"{root}/bin"),
            "account": dict(account="Root User"),
        }
        for name, change in cases.items():
            with self.subTest(name), self.assertRaises(lab.LabError) as caught:
                replace(machine.policy, **change)
            self.assertEqual(caught.exception.reason, "invalid-policy")

    def test_cli_version_outside_window_refuses(self):
        for version in ("2.1.291", "2.1.293", "2.1.292 (Claude Code)", ""):
            with self.subTest(version), self.assertRaises(lab.LabError) as caught:
                Machine(self, claude_version=version)
            self.assertEqual(caught.exception.reason, "cli-version-unsupported")

    def test_child_environment_is_built_from_scratch(self):
        policy = Machine(self).policy
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-x", "SSH_AUTH_SOCK": "/s"}):
            launch = policy.child_environment("launch", "/r/tmp")
            fixture = policy.child_environment("fixture", "/r/tmp")
        for env in (launch, fixture):
            self.assertFalse(set(env) & set(mac.ENV_DENY))
            self.assertNotIn("SSH_AUTH_SOCK", env)
            self.assertEqual((env["HOME"], env["TMPDIR"]), ("/r/tmp/home", "/r/tmp"))
            self.assertEqual(env["HTTPS_PROXY"], f"http://127.0.0.1:{policy.proxy_port}")
        self.assertEqual(launch["CLAUDE_CONFIG_DIR"], policy.config_dir)
        self.assertEqual(launch["DISABLE_AUTOUPDATER"], "1")
        self.assertNotIn("CLAUDE_CONFIG_DIR", fixture)

    def test_environment_hash_binds_every_input(self):
        machine = Machine(self)
        policy, root, uid = machine.policy, machine.root, os.getuid()
        base = machine.environment()
        self.assertEqual(base, machine.environment())

        def digest_of(policy=policy, facts=FACTS, uid=uid, account=ACCOUNT_FACTS):
            return mac.environment_sha256(policy, facts, uid, account)
        facts = [mac.HostFacts("27.0.2", "26A434", "arm64"), mac.HostFacts("27.0.1", "26A435", "arm64"),
                 mac.HostFacts("27.0.1", "26A434", "x86_64")]
        changes = [dict(sandbox_exec_sha256="1" * 64), dict(claude_sha256="2" * 64),
                   dict(interpreter_sha256="3" * 64),
                   dict(proxy_port=policy.proxy_port + 1), dict(account="braid-lab2"),
                   dict(refresh_endpoints=("platform.claude.com:443",)),
                   dict(helpers=((f"{root}/bin/claude-helper", "5" * 64),)),
                   dict(config_dir=f"{root}/config2"), dict(run_root=f"{root}/run2"),
                   dict(claude=f"{root}/bin/claude2")]
        accounts = [mac.AccountFacts((20, 81), 0o700), mac.AccountFacts((20,), 0o750), None]
        changed = {digest_of(facts=f) for f in facts}
        changed.add(digest_of(uid=uid + 1))
        changed |= {digest_of(policy=replace(policy, **c)) for c in changes}
        changed |= {digest_of(account=a) for a in accounts}
        with mock.patch.object(mac, "_component_hashes", lambda: {"harness_lab.py": "0" * 64}):
            changed.add(digest_of())
        with mock.patch.object(mac, "_probe_catalog_sha256", lambda: "4" * 64):
            changed.add(digest_of(policy=replace(policy, probe_catalog_sha256="4" * 64)))
        with mock.patch.object(mac, "LIMITS", mac.LIMITS | {"openFiles": 255}):
            changed.add(digest_of())
        with mock.patch.object(mac, "LIMITS", mac.LIMITS | {"diskFiles": 99_999}):
            changed.add(digest_of())
        self.assertEqual(len(changed), len(facts) + 1 + len(changes) + len(accounts) + 4)
        self.assertNotIn(base, changed)

    def test_executable_ancestors_and_file_must_be_owned_by_root_or_the_dedicated_user(self):
        machine = Machine(self)
        self.assertIsNone(mac._shared_ancestor(machine.claude))
        with mock.patch.object(mac.os, "geteuid", return_value=os.geteuid() + 1):  # a third account owns them
            self.assertIsNotNone(mac._shared_ancestor(machine.claude))
            with self.assertRaises(lab.LabError) as caught:
                mac._trusted_file(machine.claude, machine.policy.claude_sha256, "executable-unavailable", "drift")
        self.assertEqual(caught.exception.reason, "executable-unavailable")
        mac._trusted_file(machine.claude, machine.policy.claude_sha256, "executable-unavailable", "drift")

    def test_shared_ancestor_refuses_swappable_paths(self):
        machine = Machine(self)
        self.assertIsNone(mac._shared_ancestor(machine.claude))
        os.chmod(f"{machine.root}/bin", 0o775)
        self.assertEqual(mac._shared_ancestor(machine.claude), f"{machine.root}/bin")
        with self.assertRaises(lab.LabError) as caught:
            mac._trusted_file(machine.claude, machine.policy.claude_sha256, "executable-unavailable", "drift")
        self.assertEqual(caught.exception.reason, "executable-unavailable")


class ConstructionTests(unittest.TestCase):
    def test_records_are_verified_and_bound_to_this_backend(self):
        machine = Machine(self)
        environment = machine.environment()
        backend = make_backend(machine)
        self.assertEqual(backend.kind, "native")
        self.assertIsInstance(backend.qualification, lab.Qualification)
        cases = {
            "qualification-backend-mismatch": dict(backend="other-backend"),
            "qualification-environment-mismatch": dict(host_environment="f" * 64),
            "host-mismatch": dict(host="codex"),
        }
        for reason, change in cases.items():
            with self.subTest(reason), self.assertRaises(lab.LabError) as caught:
                mac.MacOSContainment(machine.policy, probe_runner=expected_probes, operator_account=OPERATOR,
                                     **records(environment, **change))
            self.assertEqual(caught.exception.reason, reason)
        good = records(environment)
        for key in ("qualification_sha256", "host_qualification_sha256"):
            with self.subTest(key), self.assertRaises(lab.LabError) as caught:
                mac.MacOSContainment(machine.policy, probe_runner=expected_probes, operator_account=OPERATOR,
                                     **(good | {key: "0" * 64}))
            self.assertEqual(caught.exception.reason, "qualification-drift")
        with self.assertRaises(lab.LabError) as caught:
            mac.MacOSContainment(object(), probe_runner=expected_probes, operator_account=OPERATOR, **good)
        self.assertEqual(caught.exception.reason, "invalid-policy")
        for operator in (ACCOUNT, "", "Bad Name", None, 501):  # the lab account itself, or not an account name
            with self.subTest(operator=operator), self.assertRaises(lab.LabError) as caught:
                mac.MacOSContainment(machine.policy, probe_runner=expected_probes, operator_account=operator,
                                     **good)
            self.assertEqual(caught.exception.reason, "invalid-policy")
        with self.assertRaises(TypeError):  # the operator account is required, never defaulted
            mac.MacOSContainment(machine.policy, probe_runner=expected_probes, **good)


class RefusalTests(unittest.TestCase):
    """Every T005 negative control refuses before any child starts and is recorded."""

    def setUp(self):
        self.machine = Machine(self)
        self.workdir = Path(self.machine.candidate())

    def refuse(self, reason, backend=None, *, entry="fixture", **host_args):
        backend = backend or make_backend(self.machine)
        self.addCleanup(backend.close)
        calls = {"fixture": lambda: backend.run(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=2)),
                 "probe": lambda: backend.run_probe(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=2)),
                 "launch": lambda: backend.launch((self.machine.claude, "-p"), b"", cwd=self.workdir,
                                                  wall_seconds=5, max_output_bytes=1024,
                                                  cancel=threading.Event())}
        with host(self.machine, **host_args), \
                mock.patch.object(mac.subprocess, "Popen", side_effect=AssertionError("child started")), \
                mock.patch.object(lab.SimulatedContainment, "run", side_effect=AssertionError("fallback")), \
                self.assertRaises(lab.LabError) as caught:
            calls[entry]()
        backend.close()  # frees the proxy port for the next backend in the same test
        self.assertEqual(caught.exception.reason, reason)
        self.assertEqual(backend.run_evidence[-1]["refused"], reason)
        return backend

    def test_mechanism_absent_or_not_root_owned(self):
        self.refuse("mechanism-unavailable", darwin=False)
        os.unlink(self.machine.sandbox)
        self.refuse("mechanism-unavailable")
        write_exec(self.machine.sandbox, mac.Path(self.machine.claude).read_text())
        self.machine.repin(sandbox_exec_sha256=digest(self.machine.sandbox))
        self.refuse("mechanism-unavailable", mechanism_uid=os.getuid() + 1)
        os.chmod(self.machine.sandbox, 0o777)
        self.refuse("mechanism-unavailable")

    def test_mechanism_binary_hash_changed(self):
        Path(self.machine.sandbox).write_text(mac.Path(self.machine.sandbox).read_text() + "# replaced\n")
        self.refuse("mechanism-drift")

    def test_policy_compile_failure_and_allowed_exec(self):
        for code, reason in ((mac.EXIT_SANDBOX_COMPILE, "profile-compile-failed"), (1, "self-check-allowed"),
                             (0, "self-check-allowed"), (134, "self-check-allowed")):  # denied case only
            with self.subTest(code), mock.patch.object(
                    mac.subprocess, "run", return_value=SimpleNamespace(returncode=code)):
                self.refuse(reason, stub_compile_check=False)
        with mock.patch.object(mac.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("sandbox-exec", 10)):
            self.refuse("profile-compile-failed", stub_compile_check=False)
        with mock.patch.object(mac.tempfile, "mkdtemp", side_effect=PermissionError):
            self.refuse("profile-compile-failed", stub_compile_check=False)
        # RV-23: the listed command must also run; a profile that denied everything is refused
        for code in (mac.EXIT_SANDBOX_EXEC_DENIED, 1, 134):
            with self.subTest(allowed=code), mock.patch.object(
                    mac.subprocess, "run", side_effect=[SimpleNamespace(returncode=mac.EXIT_SANDBOX_EXEC_DENIED),
                                                        SimpleNamespace(returncode=code)]):
                self.refuse("self-check-failed", stub_compile_check=False)
        # positive control: denied then allowed passes the mocked compile check
        backend = make_backend(self.machine, runner=lambda probe, _b: "allowed")
        with mock.patch.object(mac.subprocess, "run", side_effect=[
                SimpleNamespace(returncode=mac.EXIT_SANDBOX_EXEC_DENIED), SimpleNamespace(returncode=0)]) as run:
            self.refuse("self-check-allowed", backend, stub_compile_check=False)
        self.assertEqual(backend.run_evidence[-1]["compileCheck"], "exec-denied")
        deny_args, allow_args = (call.args[0] for call in run.call_args_list)
        self.assertEqual(deny_args[deny_args.index("--") + 1:], [mac.COMPILE_PROBE])
        self.assertEqual(allow_args[allow_args.index("--") + 1:], self.machine.policy.exec_probe("fixture"))
        self.assertTrue(any(a.startswith("RUNDIR=") for a in allow_args))

    def test_self_check_returns_allowed_or_fails(self):
        def flip(target, outcome):
            return lambda probe, backend: outcome if probe == target else expected_probes(probe, backend)

        for target in ("FS-01", "NET-01", "CRED-01", "PROC-01"):
            with self.subTest(target):
                backend = self.refuse("self-check-allowed", make_backend(self.machine, runner=flip(target, "allowed")))
                checks = backend.run_evidence[-1]["preSessionCheck"]
                self.assertEqual(checks[-1], {"probe": target, "expected": "denied", "observed": "allowed"})
        self.refuse("self-check-failed", make_backend(self.machine, runner=flip("NET-06", "denied")))
        backend = self.refuse("self-check-failed", make_backend(self.machine, runner=flip("FS-01", "inconclusive")))
        self.assertEqual(backend.run_evidence[-1]["preSessionCheck"][0]["observed"], "error")

        def boom(probe, backend):
            raise RuntimeError("probe crashed")

        backend = self.refuse("self-check-failed", make_backend(self.machine, runner=boom))
        self.assertEqual(backend.run_evidence[-1]["preSessionCheck"][0]["observed"], "error")
        self.refuse("self-check-unavailable", make_backend(self.machine, runner=None))

    def test_os_build_outside_window(self):
        for facts in (mac.HostFacts("26.4.1", "25E1", "arm64"), mac.HostFacts("28.0", "27A1", "arm64"),
                      mac.HostFacts("2.7", "26A1", "arm64"), mac.HostFacts("270", "26A1", "arm64"),
                      mac.HostFacts("27", "26A1", "arm64"), mac.HostFacts("27.", "26A1", "arm64"),
                      mac.HostFacts("27.1000", "26A1", "arm64"), mac.HostFacts("27.0.1000", "26A1", "arm64"),
                      mac.HostFacts("27.0.1", "garbage", "arm64"), mac.HostFacts("27.0.1.1", "26A434", "arm64"),
                      mac.HostFacts("27.2.3.4", "26B123", "arm64"), mac.HostFacts("27.x", "26B123", "arm64"),
                      mac.HostFacts("27.\u0663", "26B123", "arm64"), mac.HostFacts("27.007", "26B123", "arm64"),
                      mac.HostFacts("27.0.00", "26B123", "arm64"), mac.HostFacts("27.2\n", "26B123", "arm64")):
            with self.subTest(facts):
                self.refuse("os-unsupported", facts=facts)

    def test_the_whole_27_series_is_accepted_but_each_build_has_its_own_environment_hash(self):
        """NC-3 (amended 2026-11-03): any 27.x[.y]; the self-check and the hash still bind each build."""
        for product, build in (("27.0", "26A1"), ("27.0.2", "26A434"), ("27.2", "26B123"), ("27.10.3", "26C7"),
                               ("27.999.999", "26Z99999z")):
            facts = mac.HostFacts(product, build, "arm64")
            with self.subTest(product):
                self.assertIsNotNone(mac._OS_SERIES.fullmatch(product))
                self.assertIsNotNone(mac._BUILD.fullmatch(build))
                # past the OS window, so the refusal is the qualification pinned to another build
                self.refuse("environment-drift", facts=facts)

    def test_executable_drift_and_symlink(self):
        Path(self.machine.claude).write_text("#!/bin/sh\n")
        self.refuse("executable-drift", entry="launch")
        os.unlink(self.machine.claude)
        os.symlink("/bin/sh", self.machine.claude)
        self.refuse("executable-unavailable", entry="launch")

    def test_executable_below_writable_directory(self):
        os.chmod(f"{self.machine.root}/bin", 0o777)
        self.refuse("executable-unavailable", entry="launch")

    def test_env_deny_variable_in_parent(self):
        for name in mac.ENV_DENY:
            with self.subTest(name):
                self.refuse("env-deny-present", env={name: "x"})

    def test_not_the_dedicated_user(self):
        self.refuse("dedicated-user-required", uid=os.getuid() + 1)
        self.machine.repin(account="nobody-here")
        self.refuse("dedicated-user-required")

    def test_dedicated_account_must_be_unprivileged_not_the_operator_with_a_private_home(self):
        cases = {"admin group": dict(gids=(20, 80)), "wheel group": dict(gids=(0, 20)),
                 "admin primary group": dict(pw_gid=80), "home not owned": dict(home="/"),
                 "operator account by uid": dict(operator_uid=os.getuid())}
        for name, args in cases.items():
            with self.subTest(name):
                self.refuse("dedicated-user-unsafe", **args)
        with self.subTest("system account"), mock.patch.object(mac, "_MIN_HUMAN_UID", os.getuid() + 1):
            self.refuse("dedicated-user-unsafe", operator_uid=os.getuid() + 2)
        for mode in (0o755, 0o710, 0o701):
            with self.subTest(mode=oct(mode)):
                os.chmod(self.machine.home, mode)
                self.refuse("dedicated-user-unsafe")
        os.chmod(self.machine.home, 0o700)
        os.rmdir(self.machine.home)
        os.symlink(self.machine.root, self.machine.home)  # a home that is a link
        self.refuse("dedicated-user-unsafe")

    def test_console_owner_is_not_a_reason_to_refuse(self):
        """RV-16 amended 2026-11-03: fast user switching makes the lab account the console owner."""
        self.assertFalse(hasattr(mac, "_console_uid"))
        with mock.patch.object(mac.os, "stat", side_effect=AssertionError("/dev/console must not be read")):
            entry = SimpleNamespace(pw_gid=20, pw_dir=self.machine.home)
            with mock.patch.object(mac, "_account_groups", lambda account, gid: (20,)):
                self.assertEqual(mac._account_facts(ACCOUNT, entry, os.getuid(), os.getuid() + 1), ACCOUNT_FACTS)

    def test_operator_account_must_resolve_to_a_human_account(self):
        """Fail closed: an operator that is missing, unresolvable or a system account is no rule at all."""
        backend = make_backend(self.machine, operator="no-such-operator")
        self.refuse("operator-account-unresolved", backend)
        self.refuse("operator-account-unresolved", operator_uid=0)
        self.refuse("operator-account-unresolved", operator_uid=499)
        self.refuse("operator-account-unresolved", operator_uid=-1)

    def test_the_operator_used_for_the_decision_is_in_the_evidence(self):
        backend = self.refuse("dedicated-user-unsafe", operator_uid=os.getuid())
        self.assertEqual(backend.run_evidence[-1]["operator"], {"account": OPERATOR, "uid": os.getuid()})

    def test_operator_refusal_is_one_pure_rule(self):
        refusal = mac._operator_refusal
        self.assertIsNone(refusal("braidlab", 502, "founder", 501))
        self.assertEqual(refusal("braidlab", 502, "founder", None), "operator-account-unresolved")
        self.assertEqual(refusal("braidlab", 502, "founder", 499), "operator-account-unresolved")
        self.assertEqual(refusal("braidlab", 502, "braidlab", 501), "invalid-policy")
        self.assertEqual(refusal("braidlab", 499, "founder", 501), "dedicated-user-unsafe")
        self.assertEqual(refusal("braidlab", 501, "alias", 501), "dedicated-user-unsafe")

    def test_account_facts_fail_closed_when_the_system_cannot_say(self):
        entry = SimpleNamespace(pw_gid=20, pw_dir=self.machine.home)
        uid, real_lstat = os.getuid(), os.lstat

        def not_owned(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            return SimpleNamespace(st_mode=info.st_mode, st_uid=info.st_uid + 1) if path == entry.pw_dir else info

        operator = uid + 1
        with mock.patch.object(mac, "_account_groups", lambda account, gid: (20,)):
            self.assertEqual(mac._account_facts(ACCOUNT, entry, uid, operator), ACCOUNT_FACTS)
            with self.subTest("groups"), mock.patch.object(mac, "_account_groups", side_effect=OSError), \
                    self.assertRaises(lab.LabError) as caught:
                mac._account_facts(ACCOUNT, entry, uid, operator)
            self.assertEqual(caught.exception.reason, "dedicated-user-unsafe")
            with self.subTest("same uid as the operator"), self.assertRaises(lab.LabError) as caught:
                mac._account_facts(ACCOUNT, entry, uid, uid)
            self.assertEqual(caught.exception.reason, "dedicated-user-unsafe")
            with self.subTest("system account"), mock.patch.object(mac, "_MIN_HUMAN_UID", uid + 1), \
                    self.assertRaises(lab.LabError) as caught:
                mac._account_facts(ACCOUNT, entry, uid, operator)
            self.assertEqual(caught.exception.reason, "dedicated-user-unsafe")
            with self.subTest("owner"), mock.patch.object(mac.os, "lstat", not_owned), \
                    self.assertRaises(lab.LabError) as caught:
                mac._account_facts(ACCOUNT, entry, uid, operator)
            self.assertEqual(caught.exception.reason, "dedicated-user-unsafe")
            entry.pw_dir = f"{self.machine.root}/missing"
            with self.subTest("missing home"), self.assertRaises(lab.LabError):
                mac._account_facts(ACCOUNT, entry, uid, operator)

    def test_leftover_run_directory_refuses_the_next_run(self):
        for prefix in ("run-", "compile-"):
            with self.subTest(prefix):
                leftover = tempfile.mkdtemp(prefix=prefix, dir=self.machine.policy.run_root)
                self.refuse("workspace-leftovers")
                self.refuse("workspace-leftovers", entry="launch")
                os.rmdir(leftover)
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        with host(self.machine):
            backend.run(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=5))

    def test_a_dead_accept_loop_refuses_the_next_pre_session_then_recovers(self):
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        with host(self.machine):
            backend.run(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=5))
            self.assertTrue(backend._proxy.running)
            dying = mock.Mock(accept=mock.Mock(side_effect=OSError))
            backend._proxy._servers.append(dying)
            backend._proxy._accept(dying)
            self.assertFalse(backend._proxy.healthy)
            with self.assertRaises(lab.LabError) as caught:
                backend.run(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=5))
            self.assertEqual(caught.exception.reason, "proxy-unavailable")
            self.assertEqual(backend.run_evidence[-1]["refused"], "proxy-unavailable")
            backend.run(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=5))  # a fresh proxy
        self.assertTrue(backend._proxy.healthy)

    def test_run_launch_probe_refuses_and_records_under_its_own_entry(self):
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        with host(self.machine, env={"ANTHROPIC_API_KEY": "x"}), \
                mock.patch.object(mac.subprocess, "Popen", side_effect=AssertionError("child started")), \
                self.assertRaises(lab.LabError) as caught:
            backend.run_launch_probe(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=2))
        self.assertEqual(caught.exception.reason, "env-deny-present")
        self.assertEqual(backend.run_evidence[-1]["entry"], mac.LAUNCH_PROBE)
        self.assertEqual(backend.run_evidence[-1]["refused"], "env-deny-present")

    def test_run_launch_probe_has_its_own_lock_and_validates_input(self):
        fd = os.open(f"{self.machine.policy.run_root}/.lock", os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        with host(self.machine), self.assertRaises(lab.LabError) as caught:
            backend.run_launch_probe(FIXTURE, self.workdir, lab.FixtureLimits(wall_seconds=2))
        self.assertEqual(caught.exception.reason, "dedicated-user-busy")
        for bad in (dict(cancel=True), dict(source="text")):
            with self.subTest(bad), self.assertRaises(lab.LabError) as caught:
                backend.run_launch_probe(bad.get("source", FIXTURE), self.workdir, lab.FixtureLimits(),
                                         cancel=bad.get("cancel"))
            self.assertEqual(caught.exception.reason, "invalid-lab-request")

    def test_run_probe_cancel_must_be_an_event(self):
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        for bad in (True, "stop", object()):
            with self.subTest(bad), self.assertRaises(lab.LabError) as caught:
                backend.run_probe(FIXTURE, self.workdir, lab.FixtureLimits(), cancel=bad)
            self.assertEqual(caught.exception.reason, "invalid-lab-request")

    def test_unsafe_workspace(self):
        os.chmod(self.machine.policy.config_dir, 0o755)
        self.refuse("workspace-unsafe")

    def test_qualification_for_another_environment_or_expired(self):
        self.refuse("environment-drift", facts=mac.HostFacts("27.0.2", "26A500", "arm64"))
        self.refuse("qualification-expired", make_backend(self.machine, expires=NOW))

    def test_proxy_port_unavailable(self):
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            with self.subTest(address), socket.socket(family) as busy:
                busy.bind((address, self.machine.policy.proxy_port))
                busy.listen()
                self.refuse("proxy-unavailable")

    def test_candidate_must_be_a_private_child_of_run_root(self):
        outside = os.path.realpath(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        nested = f"{self.workdir}/nested"
        os.mkdir(nested, 0o700)
        reserved = tempfile.mkdtemp(prefix="run-", dir=self.machine.policy.run_root)
        for path in (outside, self.machine.policy.run_root, nested, reserved):
            with self.subTest(path):
                self.workdir = Path(path)
                self.refuse("workdir-outside-run-root")
        self.workdir = Path(self.machine.candidate())
        os.chmod(self.workdir, 0o755)
        self.refuse("workspace-unsafe")

    def test_run_probe_refuses_and_records_too(self):
        self.refuse("env-deny-present", entry="probe", env={"ANTHROPIC_API_KEY": "x"})
        self.refuse("environment-drift", entry="probe", facts=mac.HostFacts("27.0.1", "26A999", "arm64"))

    def test_concurrent_run_on_the_account_refuses(self):
        fd = os.open(f"{self.machine.policy.run_root}/.lock", os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX)
        self.refuse("dedicated-user-busy")

    def test_launch_arguments_refused_and_recorded(self):
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        bad = [dict(argv=("/usr/bin/claude", "-p")), dict(argv=["x"]), dict(wall_seconds=1801),
               dict(wall_seconds=0), dict(wall_seconds=True), dict(max_output_bytes=0),
               dict(max_output_bytes=mac.MAX_LAUNCH_OUTPUT_BYTES + 1), dict(stdin="text"),
               dict(stdin=b"x" * (mac.MAX_LAUNCH_STDIN_BYTES + 1)), dict(cancel=None),
               dict(argv=(self.machine.claude, "a\0b"))]
        for change in bad:
            args = dict(argv=(self.machine.claude, "-p"), stdin=b"", cwd=self.workdir, wall_seconds=5,
                        max_output_bytes=10, cancel=threading.Event()) | change
            with self.subTest(change), self.assertRaises(lab.LabError) as caught:
                backend.launch(**args)
            self.assertEqual(caught.exception.reason, "invalid-launch")
            self.assertEqual(backend.run_evidence[-1]["refused"], "invalid-launch")

    def test_run_fixture_needs_supervisor_tmpdir_and_never_simulates(self):
        manifest = native_manifest(fixture=FIXTURE)
        manifest.data["environment"]["sha256"] = self.machine.environment()
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        args = dict(backend=backend, attempt_id="a-1", inventory=make_inventory(), now=NOW,
                    retention_seconds=60, limits=lab.FixtureLimits(wall_seconds=3))
        with host(self.machine), \
                mock.patch.object(lab.SimulatedContainment, "run", side_effect=AssertionError("fallback")):
            with self.assertRaises(lab.LabError) as caught:  # TMPDIR is not run_root
                lab.run_fixture(manifest, FIXTURE, **args)
            self.assertEqual(caught.exception.reason, "workdir-outside-run-root")
            with mock.patch.object(tempfile, "tempdir", self.machine.policy.run_root), \
                    mock.patch.object(mac, "host_facts", lambda: mac.HostFacts("27.0.1", "26A999", "arm64")), \
                    self.assertRaises(lab.LabError) as caught:
                lab.run_fixture(manifest, FIXTURE, **args)
            self.assertEqual(caught.exception.reason, "environment-drift")


class SupervisedRunTests(unittest.TestCase):
    """Qualified path with a pass-through mechanism: rlimits, watchdog, settlement, evidence."""

    def setUp(self):
        self.machine = Machine(self)
        self.backend = make_backend(self.machine)
        self.addCleanup(self.backend.close)

    def fixture(self, source: bytes, wall: int = 5, max_output: int = 65_536, **host_args) -> lab.ChildResult:
        with host(self.machine, **host_args):
            return self.backend.run(source, Path(self.machine.candidate()),
                                    lab.FixtureLimits(wall_seconds=wall, max_output_bytes=max_output))

    def test_qualified_run_fixture_is_native_with_evidence(self):
        manifest = native_manifest(fixture=FIXTURE)
        manifest.data["environment"]["sha256"] = self.machine.environment()
        with host(self.machine), mock.patch.object(tempfile, "tempdir", self.machine.policy.run_root):
            result = lab.run_fixture(manifest, FIXTURE, backend=self.backend, attempt_id="a-1",
                                     inventory=make_inventory(), now=NOW, retention_seconds=60,
                                     limits=lab.FixtureLimits(wall_seconds=10))
        self.assertEqual((result.containment, result.exit_code, result.settled), ("native", 0, True))
        self.assertEqual(result.observation.to_dict()["source"], "host")
        evidence = self.backend.run_evidence[-1]
        self.assertEqual(evidence["qualificationSha256"], self.backend.qualification.sha256)
        self.assertEqual(evidence["hostQualificationSha256"], self.backend.host_qualification.sha256)
        self.assertEqual(evidence["environmentSha256"], self.backend.qualification.environment_sha256)
        self.assertEqual([c["probe"] for c in evidence["preSessionCheck"]], [p for p, _ in mac.F4_PROBES])
        self.assertTrue(all(c["observed"] == c["expected"] for c in evidence["preSessionCheck"]))
        self.assertEqual((evidence["limits"], evidence["compileCheck"]), (mac.LIMITS, "exec-denied"))
        self.assertNotIn("refused", evidence)
        self.assertEqual(self.machine.leftovers(), [])

    def test_probe_runner_runs_contained_probes_without_recursion(self):
        def runner(probe, backend):
            result = backend.run_probe(b"print('denied')\n", Path(self.machine.candidate()), lab.FixtureLimits())
            return "allowed" if probe == "NET-06" else result.stdout.decode().strip()

        backend = make_backend(self.machine, runner=runner)
        self.addCleanup(backend.close)
        with host(self.machine):
            result = backend.run(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(sum(1 for e in backend.run_evidence if e.get("probeRun")), len(mac.F4_PROBES))

    def test_rlimits_and_environment_reach_the_child(self):
        source = (b"import os, resource, json\n"
                  b"print(json.dumps({'cpu': resource.getrlimit(resource.RLIMIT_CPU),"
                  b" 'fsize': resource.getrlimit(resource.RLIMIT_FSIZE),"
                  b" 'nofile': resource.getrlimit(resource.RLIMIT_NOFILE),"
                  b" 'nproc': resource.getrlimit(resource.RLIMIT_NPROC),"
                  b" 'core': resource.getrlimit(resource.RLIMIT_CORE), 'cwd': os.getcwd(),"
                  b" 'env': sorted(os.environ)}))\n")
        candidate = self.machine.candidate()
        with host(self.machine, processes=lambda uid: {(1, 1), (2, 2)}):
            result = self.backend.run(source, Path(candidate), lab.FixtureLimits(wall_seconds=4))
        value = json.loads(result.stdout)
        self.assertEqual(value["cpu"], [5, 5])
        self.assertEqual(value["fsize"], [mac.LIMITS["fileSizeBytes"]] * 2)
        self.assertEqual(value["nofile"], [mac.LIMITS["openFiles"]] * 2)
        self.assertEqual(value["core"], [0, 0])
        self.assertEqual(value["nproc"], [2 + 1 + mac.LIMITS["descendants"]] * 2)
        self.assertEqual(value["cwd"], candidate)
        self.assertEqual(set(value["env"]) - {"__CF_USER_TEXT_ENCODING", "LC_CTYPE"},
                         set(self.machine.policy.child_environment("fixture", "/x")) | {mac.RUN_TAG_VARIABLE})

    def test_child_exit_125_is_an_ordinary_result(self):
        result = self.fixture(b"import os\nos._exit(125)\n")
        self.assertEqual((result.exit_code, result.settled), (125, True))
        self.assertNotIn("refused", self.backend.run_evidence[-1])

    def test_timeout_kills_and_settles(self):
        result = self.fixture(b"import time\ntime.sleep(30)\n", wall=1)
        self.assertEqual((result.timed_out, result.exit_code, result.settled), (True, None, True))
        self.assertTrue(self.backend.run_evidence[-1]["timedOut"])

    def test_memory_watchdog_kills(self):
        with host(self.machine), mock.patch.object(mac, "_resident_bytes", lambda processes: 5 << 30):
            result = self.backend.run(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                                      lab.FixtureLimits(wall_seconds=10))
        self.assertIsNone(result.exit_code)
        self.assertEqual(self.backend.run_evidence[-1]["limitExceeded"], "memory")

    def test_output_cap_kills(self):
        result = self.fixture(b"import sys, time\nsys.stdout.write('x' * 5000)\nsys.stdout.flush()\n"
                              b"time.sleep(30)\n", wall=10, max_output=100)
        self.assertTrue(result.output_truncated)
        self.assertIsNone(result.exit_code)
        self.assertEqual(len(result.stdout), 100)

    def test_accounting_failure_kills_child_and_refuses(self):
        pid_file = f"{self.machine.root}/child.pid"
        calls = {"n": 0}

        def failing(processes):
            calls["n"] += 1
            if calls["n"] > 3:
                raise lab.LabError("process-accounting-failed")
            return 0

        source = f"import os, time\nopen({pid_file!r}, 'w').write(str(os.getpid()))\ntime.sleep(30)\n".encode()
        with host(self.machine), mock.patch.object(mac, "_resident_bytes", failing), \
                self.assertRaises(lab.LabError) as caught:
            self.backend.run(source, Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=10))
        self.assertEqual(caught.exception.reason, "process-accounting-failed")
        record = self.backend.run_evidence[-1]
        self.assertEqual(record["refused"], "process-accounting-failed")
        self.assertTrue(record["settled"])
        if os.path.exists(pid_file):
            with self.assertRaises(ProcessLookupError):
                os.kill(int(Path(pid_file).read_text()), 0)
        self.assertEqual(self.machine.leftovers(), [])

    def test_accounting_refusal_records_two_integers(self):
        def failing(processes):
            raise mac._accounting_error(1, 4)

        with host(self.machine), mock.patch.object(mac, "_resident_bytes", failing), \
                self.assertRaises(lab.LabError):
            self.backend.run(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                             lab.FixtureLimits(wall_seconds=10))
        record = self.backend.run_evidence[-1]
        self.assertEqual((record["refused"], record["accountingErrno"], record["accountingFlavor"]),
                         ("process-accounting-failed", 1, 4))

    def test_unexpected_supervisor_error_is_fixed_reason(self):
        with host(self.machine), mock.patch.object(mac.os.path, "getsize", side_effect=RuntimeError("boom")), \
                self.assertRaises(lab.LabError) as caught:
            self.backend.run(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                             lab.FixtureLimits(wall_seconds=10))
        self.assertEqual(caught.exception.reason, "supervisor-failed")
        self.assertEqual(self.backend.run_evidence[-1]["refused"], "supervisor-failed")
        self.assertTrue(self.backend.run_evidence[-1]["settled"])

    def test_workspace_failure_is_recorded(self):
        real = tempfile.mkdtemp

        def mkdtemp(prefix="", dir=None):
            if prefix == "run-":
                raise PermissionError
            return real(prefix=prefix, dir=dir)

        with host(self.machine), mock.patch.object(mac.tempfile, "mkdtemp", mkdtemp), \
                self.assertRaises(lab.LabError) as caught:
            self.backend.run(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual(caught.exception.reason, "workspace-unavailable")
        self.assertEqual(self.backend.run_evidence[-1]["refused"], "workspace-unavailable")

    def leaver(self, *, killable: bool, parent: bool, source=b"import time\ntime.sleep(0.6)\n",
               group: bool = False, resident=None, tagged: bool = False, tags=None):
        """A process of the dedicated user that appears while the child runs and outlives the group.

        ``parent``: its parent is the child; ``group``: it is in the child's process group (an orphan);
        neither: an unrelated process (``launchd`` parent, a group of its own)."""
        ghost, state = (999_999, 7), {"calls": 0, "dead": False}
        spawned = []
        real_popen = mac.subprocess.Popen

        def popen(*args, **kwargs):
            spawned.append(real_popen(*args, **kwargs))
            return spawned[-1]

        def processes(uid):
            state["calls"] += 1
            return BASELINE if state["calls"] == 1 or state["dead"] else BASELINE | {ghost}

        def fake_kill(pid, sig):
            state["dead"] = state["dead"] or killable

        with host(self.machine, processes=processes,
                  links=lambda identity: (spawned[0].pid if parent and identity == ghost else 1,
                                          spawned[0].pid if group and identity == ghost else identity[0]),
                  resident=resident), \
                mock.patch.object(mac, "_tagged", self.tag_reader(ghost, tagged, tags)), \
                mock.patch.object(mac.subprocess, "Popen", popen), mock.patch.object(mac.os, "kill", fake_kill):
            return self.backend.run(source, Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=5))

    @staticmethod
    def tag_reader(ghost, tagged, tags):
        def reader(pid, tag):
            if tags is not None:
                tags.append(tag)
            return tagged and pid == ghost[0]
        return reader

    def test_a_swept_leaver_is_counted_apart_from_a_survivor_and_attributed_to_the_child(self):
        result = self.leaver(killable=True, parent=True)
        self.assertEqual((result.escaped_processes, result.escaped_descendants, result.surviving_processes),
                         (1, 1, 0))
        self.assertFalse(result.settled)  # strict: a leaver taints the measurement
        evidence = self.backend.run_evidence[-1]
        self.assertEqual((evidence["escapedProcesses"], evidence["escapedDescendants"],
                          evidence["unattributedProcesses"], evidence["survivingProcesses"]), (1, 1, 0, 0))

    def test_a_setsid_leaver_reparented_to_launchd_is_found_by_the_run_tag(self):
        tags = []
        result = self.leaver(killable=True, parent=False, tagged=True, tags=tags)
        self.assertEqual((result.escaped_processes, result.escaped_descendants, result.surviving_processes),
                         (1, 1, 0))  # PROC-ESC-1: the backend now sees what the runner scan sees
        self.assertTrue(tags and all(t.startswith(mac.RUN_TAG_VARIABLE.encode() + b"=") for t in tags))

    def test_an_untagged_unrelated_process_is_still_neither_counted_nor_killed(self):
        result = self.leaver(killable=True, parent=False, tagged=False)
        self.assertEqual((result.escaped_processes, result.surviving_processes), (0, 0))
        self.assertEqual(self.backend.run_evidence[-1]["unrelatedProcesses"], 1)

    def test_the_memory_watchdog_records_what_it_measured(self):
        with host(self.machine, resident=lambda processes: 123_456):
            result = self.backend.run(b"import time\ntime.sleep(0.5)\n", Path(self.machine.candidate()),
                                      lab.FixtureLimits(wall_seconds=5))
        evidence = self.backend.run_evidence[-1]
        self.assertEqual(evidence["peakMemoryBytes"], 123_456)
        self.assertGreaterEqual(evidence["memorySamples"], 1)
        self.assertEqual((result.peak_memory_bytes, result.memory_samples > 0), (123_456, True))

    def test_an_orphan_of_the_childs_group_is_an_escape_even_if_never_seen_with_the_child_as_parent(self):
        result = self.leaver(killable=True, parent=False, group=True)  # surviving 0: the kill reached it
        self.assertEqual((result.escaped_processes, result.escaped_descendants, result.surviving_processes),
                         (1, 1, 0))
        self.assertFalse(result.settled)

    def test_an_unrelated_new_process_is_neither_killed_nor_counted_and_does_not_unsettle(self):
        kills = []
        real_kill = mac.os.kill
        with mock.patch.object(mac.os, "kill", lambda pid, sig: kills.append(pid) or real_kill(pid, sig)):
            result = self.leaver(killable=False, parent=False)
        self.assertNotIn(999_999, kills)
        self.assertEqual((result.escaped_processes, result.surviving_processes, result.settled), (0, 0, True))
        evidence = self.backend.run_evidence[-1]
        self.assertEqual((evidence["unrelatedProcesses"], evidence["escapedProcesses"]), (1, 0))
        self.assertNotIn("refused", evidence)

    def test_an_unreadable_member_refuses_and_an_unreadable_unrelated_process_does_not(self):
        def unreadable(pid):
            if pid == 999_999:
                raise mac._accounting_error(errno.EPERM, mac._PROC_PIDTASKINFO)
            return 0
        # unrelated: never measured, the run is settled
        self.leaver(killable=False, parent=False, resident=lambda processes: sum(unreadable(p) for p, _ in processes))
        self.assertNotIn("refused", self.backend.run_evidence[-1])
        # member: measured, fails closed with errno and flavor
        with self.assertRaises(lab.LabError) as caught:
            self.leaver(killable=False, parent=True, resident=lambda processes: sum(unreadable(p) for p, _ in processes))
        self.assertEqual(caught.exception.reason, "process-accounting-failed")
        self.assertEqual(self.backend.run_evidence[-1]["accountingErrno"], errno.EPERM)

    def test_the_memory_watchdog_measures_only_the_childs_own_tree(self):
        measured = []
        self.leaver(killable=False, parent=False,
                    resident=lambda processes: measured.append(set(processes)) or 0)
        self.assertTrue(measured)
        self.assertNotIn((999_999, 7), set().union(*measured))

    def test_the_noise_counts_are_integers_in_the_run_evidence(self):
        with mock.patch.object(mac, "_unreadable_tasks", lambda processes: len(processes) * 10):
            self.leaver(killable=False, parent=False)
        evidence = self.backend.run_evidence[-1]
        self.assertEqual((evidence["unrelatedProcesses"], evidence["unreadableProcesses"]), (1, 10))

    def test_a_survivor_that_resists_every_kill_is_reported_after_the_final_sweep(self):
        result = self.leaver(killable=False, parent=True, source=b"pass\n")
        self.assertEqual((result.escaped_processes, result.surviving_processes, result.settled), (1, 1, False))
        self.assertEqual(self.backend.run_evidence[-1]["survivingProcesses"], 1)

    def test_lineage_follows_grandchildren_whatever_the_listing_order(self):
        lineage = mac._Lineage(100)
        parents = {200: 100, 300: 200, 400: 1}
        with mock.patch.object(mac, "_process_links", lambda identity: (parents[identity[0]], identity[0])):
            lineage.observe({(300, 3), (200, 2), (400, 4)})
        self.assertEqual(lineage.identities, {(200, 2), (300, 3)})
        self.assertEqual(lineage.unrelated(), {(400, 4)})

    def test_lineage_keeps_a_reparented_member_of_the_childs_group_and_the_root(self):
        lineage = mac._Lineage(100)
        parents, groups = {100: 7, 200: 1, 300: 1, 400: 1}, {100: 100, 200: 100, 300: 300, 400: 999}
        with mock.patch.object(mac, "_process_links", lambda identity: (parents[identity[0]], groups[identity[0]])):
            members = lineage.members({(100, 1), (200, 2), (300, 3), (400, 4)})
        self.assertEqual(members, {(100, 1), (200, 2)})
        self.assertEqual(lineage.identities, {(200, 2)})
        self.assertEqual(lineage.unrelated(), {(300, 3), (400, 4)})

    def test_a_process_that_vanished_before_it_was_classified_is_unrelated(self):
        lineage = mac._Lineage(100)
        with mock.patch.object(mac, "_process_links", lambda identity: (None, None)):
            self.assertEqual(lineage.members({(500, 5)}), set())

    def test_results_extend_the_lab_and_host_results_additively(self):
        with host(self.machine):
            probe = self.backend.run(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=5))
            launched = self.backend.launch((self.machine.claude,), b"", cwd=self.machine.candidate(),
                                           wall_seconds=5, max_output_bytes=4096, cancel=threading.Event())
        self.assertIsInstance(probe, lab.ChildResult)
        self.assertIsInstance(launched, mac.HostRun)
        self.assertEqual((probe.cancelled, probe.cleanup_failed, probe.escaped_processes, probe.egress),
                         (False, False, 0, {}))
        self.assertEqual((launched.cleanup_failed, launched.surviving_processes, launched.egress), (False, 0, {}))
        self.assertEqual(self.backend.run_evidence[-1]["egress"], {})

    def test_proxy_counter_delta_of_the_run_lands_in_the_result_and_the_evidence(self):
        counts = iter([{"allowed": 1, "bytesUp": 10, "denied": 2}, {"allowed": 3, "bytesUp": 10, "denied": 2,
                                                                   "allowed:api.anthropic.com:443": 2}])
        with host(self.machine), mock.patch.object(self.backend._proxy, "counters", lambda: next(counts)):
            result = self.backend.run_probe(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        expected = {"allowed": 2, "allowed:api.anthropic.com:443": 2}
        self.assertEqual(result.egress, expected)
        self.assertEqual(self.backend.run_evidence[-1]["egress"], expected)

    def test_run_probe_cancel_stops_and_settles_the_group(self):
        cancel = threading.Event()
        timer = threading.Timer(0.5, cancel.set)
        self.addCleanup(timer.cancel)
        timer.start()
        started = time.monotonic()
        with host(self.machine):
            result = self.backend.run_probe(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                                            lab.FixtureLimits(wall_seconds=20), cancel=cancel)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual((result.cancelled, result.exit_code, result.timed_out, result.settled),
                         (True, None, False, True))
        self.assertTrue(self.backend.run_evidence[-1]["cancelled"])
        self.assertEqual(self.machine.leftovers(), [])

    def test_run_launch_probe_runs_the_interpreter_under_the_launch_probe_profile(self):
        runs = []
        popen = subprocess.Popen

        def spy(argv, *args, **kwargs):
            runs.append(argv)
            return popen(argv, *args, **kwargs)

        calls = []

        def runner(probe, backend):
            calls.append(probe)
            return dict(mac.F4_PROBES)[probe]

        backend = make_backend(self.machine, runner=runner)
        self.addCleanup(backend.close)
        with host(self.machine), mock.patch.object(mac.subprocess, "Popen", spy):
            result = backend.run_launch_probe(b"print('hi')\n", Path(self.machine.candidate()),
                                              lab.FixtureLimits(wall_seconds=5))
        self.assertEqual((result.stdout, result.exit_code, result.settled, result.limit_exceeded),
                         (b"hi\n", 0, True, None))
        self.assertEqual(calls, [])  # probes=False: no NC-11 subset, no recursion
        profile = runs[0][runs[0].index("-p") + 1]
        self.assertEqual(profile, self.machine.policy.render(mac.LAUNCH_PROBE).decode())
        evidence = backend.run_evidence[-1]
        self.assertEqual((evidence["entry"], evidence["probeRun"]), (mac.LAUNCH_PROBE, True))
        self.assertEqual(self.machine.leftovers(), [])

    def test_run_launch_probe_cancel_stops_and_settles_the_group(self):
        cancel = threading.Event()
        timer = threading.Timer(0.5, cancel.set)
        self.addCleanup(timer.cancel)
        timer.start()
        with host(self.machine):
            result = self.backend.run_launch_probe(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                                                   lab.FixtureLimits(wall_seconds=20), cancel=cancel)
        self.assertEqual((result.cancelled, result.exit_code, result.settled), (True, None, True))

    def test_limit_exceeded_is_propagated_to_the_results(self):
        with host(self.machine), mock.patch.object(mac, "_resident_bytes", lambda processes: 5 << 30):
            probe = self.backend.run_probe(b"import time\ntime.sleep(30)\n", Path(self.machine.candidate()),
                                           lab.FixtureLimits(wall_seconds=10))
            launch_probe = self.backend.run_launch_probe(b"import time\ntime.sleep(30)\n",
                                                         Path(self.machine.candidate()),
                                                         lab.FixtureLimits(wall_seconds=10))
        self.assertEqual((probe.limit_exceeded, launch_probe.limit_exceeded), ("memory", "memory"))
        with host(self.machine):
            cpu = self.backend.run_probe(b"import os, signal\nos.kill(os.getpid(), signal.SIGXCPU)\n",
                                         Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=10))
            plain = self.backend.run_probe(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual((cpu.limit_exceeded, cpu.exit_code), ("cpu", -signal.SIGXCPU))
        self.assertIsNone(plain.limit_exceeded)
        self.assertEqual([e.get("limitExceeded") for e in self.backend.run_evidence[-4:]],
                         ["memory", "memory", "cpu", None])

    def test_without_cancel_run_probe_is_unchanged(self):
        with host(self.machine):
            result = self.backend.run_probe(b"print('ok')\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual((result.stdout, result.exit_code, result.cancelled, result.settled), (b"ok\n", 0, False, True))

    # -- RV-19: disk bounds ---------------------------------------------------------------

    def limited(self, **limits) -> mac.MacOSContainment:
        patcher = mock.patch.object(mac, "LIMITS", mac.LIMITS | limits)
        patcher.start()
        self.addCleanup(patcher.stop)
        backend = make_backend(self.machine)  # the environment hash covers the limits
        self.addCleanup(backend.close)
        self.addCleanup(mac._remove_tree, self.machine.root)  # a hostile fixture may leave unreadable trees
        return backend

    def over_disk(self, backend, source: bytes):
        with host(self.machine), self.assertRaises(lab.LabError) as caught:
            backend.run_probe(source, Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=20))
        self.assertEqual(caught.exception.reason, "disk-limit-exceeded")
        record = backend.run_evidence[-1]
        self.assertEqual((record["refused"], record["limitExceeded"], record["settled"]),
                         ("disk-limit-exceeded", "disk", True))
        self.assertEqual(self.machine.leftovers(), [])
        return record

    def test_too_many_files_in_the_candidate_kills_settles_and_refuses(self):
        backend = self.limited(diskFiles=5)
        started = time.monotonic()
        record = self.over_disk(backend, b"import time\nfor i in range(20):\n    open(f'f{i}', 'w').write('x')\n"
                                         b"time.sleep(30)\n")
        self.assertLess(time.monotonic() - started, 10)
        self.assertGreater(record["diskFiles"], 5)

    def test_too_many_bytes_in_the_candidate_kills_settles_and_refuses(self):
        backend = self.limited(diskBytes=1 << 20)
        record = self.over_disk(backend, b"import time\nopen('big', 'wb').write(b'x' * (3 << 20))\ntime.sleep(30)\n")
        self.assertGreater(record["diskBytes"], 1 << 20)

    def test_the_per_run_tmpdir_counts_too(self):
        backend = self.limited(diskBytes=1 << 20)
        self.over_disk(backend, b"import os, time\nopen(os.environ['TMPDIR'] + '/big', 'wb').write(b'x' * (3 << 20))\n"
                                b"time.sleep(30)\n")

    def test_the_dedicated_config_dir_counts_too(self):
        # DRV-06 (founder decision 2026-11-02c): config_dir is read/write in `launch`, so it is measured
        backend = self.limited(diskBytes=1 << 20)
        config = self.machine.policy.config_dir
        self.over_disk(backend, f"import time\nopen({config!r} + '/big', 'wb').write(b'x' * (3 << 20))\n"
                                f"time.sleep(30)\n".encode())
        self.assertEqual(os.listdir(config), ["big"])  # the supervisor never deletes the account's state

    def test_candidate_tmpdir_and_config_dir_are_one_total(self):
        backend = self.limited(diskFiles=7)
        config = self.machine.policy.config_dir
        for index in range(4):  # the account's earlier state counts: 4 files
            Path(config, f"state-{index}").write_text("x")
        # 3 in the candidate + TMPDIR/home + 4 in config_dir = 8 > 7, though each tree alone is under
        record = self.over_disk(backend, b"for i in range(3):\n    open(f'c{i}', 'w').write('x')\n")
        self.assertGreater(record["diskFiles"], 7)

    def test_a_small_config_dir_leaves_a_run_alone(self):
        Path(self.machine.policy.config_dir, ".credentials.json").write_text("{}")
        with host(self.machine):
            result = self.backend.run_probe(b"open('x', 'w').write('y')\n", Path(self.machine.candidate()),
                                            lab.FixtureLimits())
        self.assertEqual((result.exit_code, result.disk_files), (0, 3))  # x, TMPDIR/home and the credentials

    def test_a_burst_written_just_before_a_natural_exit_is_still_caught(self):
        backend = self.limited(diskFiles=5)
        self.over_disk(backend, b"for i in range(20):\n    open(f'f{i}', 'w').write('x')\n")

    @unittest.skipIf(os.geteuid() == 0, "root can list any directory")
    def test_an_unlistable_directory_counts_as_over_the_limit(self):
        backend = self.limited()
        self.over_disk(backend, b"import os, time\nos.mkdir('hidden')\nopen('hidden/x', 'w').write('x')\n"
                                b"os.chmod('hidden', 0)\ntime.sleep(30)\n")

    @unittest.skipIf(os.geteuid() == 0, "root can search any directory")
    def test_an_unsearchable_directory_counts_as_over_the_limit(self):
        backend = self.limited()
        self.over_disk(backend, b"import os, time\nos.mkdir('ro')\nopen('ro/x', 'w').write('x')\n"
                                b"os.chmod('ro', 0o400)\ntime.sleep(30)\n")

    def test_hard_links_count_once_and_symlinks_are_not_followed(self):
        backend = self.limited(diskBytes=4 << 20)
        outside = f"{self.machine.root}/outside"
        os.mkdir(outside)
        Path(f"{outside}/huge").write_bytes(b"x" * (6 << 20))
        source = (b"import os\nopen('a', 'wb').write(b'x' * (3 << 20))\n"
                  b"for i in range(5):\n    os.link('a', f'l{i}')\n"
                  + f"os.symlink({outside!r}, 'to-outside')\n".encode())
        with host(self.machine):
            result = backend.run_probe(source, Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=10))
        self.assertEqual((result.exit_code, result.settled), (0, True))
        self.assertTrue(3 << 20 <= result.disk_bytes < 4 << 20)
        self.assertEqual(result.disk_files, 8)  # a, five links, the symlink itself and TMPDIR/home

    def test_the_default_bounds_leave_a_small_run_alone(self):
        with host(self.machine):
            result = self.backend.run_probe(b"open('x', 'w').write('y')\n", Path(self.machine.candidate()),
                                            lab.FixtureLimits())
        self.assertEqual((result.exit_code, result.disk_files), (0, 2))  # x and TMPDIR/home

    def test_the_environment_hash_covers_the_transport_and_the_quota_module(self):
        # DRV-05: both change effective policy, so a recorded qualification must not survive an edit
        hashes = mac._component_hashes()
        here = Path(mac.__file__).parent
        for name in ("harness_transport_claude.py", "harness_quota.py", "harness_host_claude.py",
                     "harness_lab.py", "harness_containment_macos.py"):
            self.assertEqual(hashes[name], sha256((here / name).read_bytes()).hexdigest(), name)
        self.assertLessEqual({"harness_transport_claude.py", "harness_quota.py"}, set(hashes))
        base = self.machine.environment()
        for name in ("harness_transport_claude.py", "harness_quota.py"):
            changed = dict(hashes, **{name: "0" * 64})
            with mock.patch.object(mac, "_component_hashes", lambda changed=changed: changed):
                self.assertNotEqual(self.machine.environment(), base, name)

    # -- RV-30: cleanup -------------------------------------------------------------------

    def test_remove_tree_undoes_what_the_child_set(self):
        tree = f"{self.machine.root}/hostile"
        for sub_dir in ("closed", "readonly", "nested/closed"):
            os.makedirs(f"{tree}/{sub_dir}", exist_ok=True)
            Path(f"{tree}/{sub_dir}/file").write_text("x")
        os.chmod(f"{tree}/nested/closed", 0)
        os.chmod(f"{tree}/closed", 0)
        os.chmod(f"{tree}/readonly", 0o500)
        if hasattr(os, "chflags"):
            os.chflags(f"{tree}/readonly/file", stat.UF_IMMUTABLE)
        self.assertTrue(mac._remove_tree(tree))
        self.assertFalse(os.path.lexists(tree))
        self.assertTrue(mac._remove_tree(tree))  # already gone

    def test_remove_tree_reports_what_it_cannot_remove(self):
        tree = f"{self.machine.root}/stuck"
        os.mkdir(tree)
        with mock.patch.object(mac.shutil, "rmtree", lambda path, onexc: onexc(os.rmdir, path, OSError())):
            self.assertFalse(mac._remove_tree(tree))

    def test_a_failed_cleanup_is_recorded_and_refuses_the_next_run(self):
        with host(self.machine), mock.patch.object(mac, "_remove_tree", lambda path: False):
            result = self.backend.run_probe(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertTrue(result.cleanup_failed)
        self.assertTrue(self.backend.run_evidence[-1]["cleanupFailed"])
        self.assertEqual(len(self.machine.leftovers()), 1)
        with host(self.machine), self.assertRaises(lab.LabError) as caught:
            self.backend.run_probe(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual(caught.exception.reason, "workspace-leftovers")

    def test_a_clean_run_records_no_cleanup_failure(self):
        with host(self.machine):
            self.backend.run_probe(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertFalse(self.backend.run_evidence[-1]["cleanupFailed"])

    def test_sweep_never_runs_as_another_user(self):
        for host_args in (dict(uid=os.getuid() + 1), dict()):
            with self.subTest(host_args), host(self.machine, **host_args), self.assertRaises(lab.LabError) as caught:
                if not host_args:
                    self.machine.repin(account="gone-account")
                    self.backend.policy = self.machine.policy
                self.backend._sweep(os.getuid(), set(), mac._Lineage(1))
            self.assertEqual(caught.exception.reason, "dedicated-user-required")

    def test_preamble_failure_refuses(self):
        broken = mac._PREAMBLE.replace("os.chdir(sys.argv[5])", "os.chdir('/nonexistent-dir')")
        with host(self.machine), mock.patch.object(mac, "_PREAMBLE", broken), \
                self.assertRaises(lab.LabError) as caught:
            self.backend.run(b"print('never')\n", Path(self.machine.candidate()), lab.FixtureLimits())
        self.assertEqual(caught.exception.reason, "rlimit-unenforceable")
        self.assertEqual(self.backend.run_evidence[-1]["refused"], "rlimit-unenforceable")

    def test_launch_runs_pinned_executable_with_minimal_environment(self):
        with host(self.machine):
            run = self.backend.launch((self.machine.claude, "-p"), b"prompt-bytes",
                                      cwd=self.machine.candidate(), wall_seconds=5, max_output_bytes=4096,
                                      cancel=threading.Event())
        self.assertEqual((run.exit_code, run.settled, run.cancelled), (0, True, False))
        names, _, rest = run.stdout.partition(b"\n")
        self.assertEqual(set(names.decode().split()) - {"__CF_USER_TEXT_ENCODING", "LC_CTYPE"},
                         set(self.machine.policy.child_environment("launch", "/x")) | {mac.RUN_TAG_VARIABLE})
        self.assertEqual(rest, b"prompt-bytes")
        self.assertEqual(self.backend.run_evidence[-1]["entry"], "launch")

    def test_launch_cancellation_settles(self):
        write_exec(self.machine.claude, f"#!{INTERPRETER} -IS\nimport time\ntime.sleep(30)\n")
        self.machine.repin(claude_sha256=digest(self.machine.claude))
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        cancel = threading.Event()
        threading.Timer(0.5, cancel.set).start()
        with host(self.machine):
            run = backend.launch((self.machine.claude,), b"", cwd=self.machine.candidate(), wall_seconds=20,
                                 max_output_bytes=10, cancel=cancel)
        self.assertEqual((run.cancelled, run.exit_code, run.settled), (True, None, True))


class AuthTokenTests(unittest.TestCase):
    """Founder decision 2026-11-04 ("A. Token en archivo"): one strict file in config_dir, one variable."""

    TOKEN = "sk-ant-oat01-" + "Ab1Cd2Ef3Gh4" * 5

    def setUp(self):
        self.machine = Machine(self)
        self.path = f"{self.machine.policy.config_dir}/{mac.TOKEN_FILE}"

    def write(self, data: bytes | str | None = None, mode: int = 0o600) -> str:
        data = (self.TOKEN + "\n") if data is None else data
        Path(self.path).unlink(missing_ok=True)
        Path(self.path).write_bytes(data if isinstance(data, bytes) else data.encode())
        os.chmod(self.path, mode)
        return self.path

    def read(self, uid: int | None = None):
        return mac.read_token(self.machine.policy.config_dir, os.getuid() if uid is None else uid)

    def test_a_missing_file_is_no_token_and_a_valid_one_is_returned_without_its_newline(self):
        self.assertIsNone(self.read())
        self.write()
        self.assertEqual(self.read(), self.TOKEN)
        self.write(self.TOKEN)
        self.assertEqual(self.read(), self.TOKEN)

    def test_every_unsafe_file_refuses_with_a_fixed_reason(self):
        cases = {
            "group-readable": lambda: self.write(mode=0o640),
            "read-only": lambda: self.write(mode=0o400),
            "empty": lambda: self.write(b""),
            "too-big": lambda: self.write(b"a" * (mac.TOKEN_MAX_BYTES + 1)),
            "not-ascii": lambda: self.write("sk-ant-\u00e9" + "a" * 30),
            "inner-space": lambda: self.write("sk-ant-oat01 " + "a" * 30),
            "too-short": lambda: self.write("sk-ant-short"),
            "two-lines": lambda: self.write(self.TOKEN + "\n" + self.TOKEN),
        }
        for name, make in cases.items():
            with self.subTest(name):
                make()
                with self.assertRaises(lab.LabError) as caught:
                    self.read()
                self.assertEqual(caught.exception.reason, "auth-token-invalid")
                self.assertNotIn(self.TOKEN, repr(caught.exception))

    def test_a_symlink_a_directory_a_second_link_and_another_owner_are_refused(self):
        real = f"{self.machine.root}/elsewhere"
        Path(real).write_text(self.TOKEN)
        os.chmod(real, 0o600)
        os.symlink(real, self.path)
        with self.assertRaises(lab.LabError):
            self.read()
        os.unlink(self.path)
        os.mkdir(self.path, 0o700)
        with self.assertRaises(lab.LabError):
            self.read()
        os.rmdir(self.path)
        self.write()
        self.assertEqual(self.read(), self.TOKEN)
        with self.assertRaises(lab.LabError):
            self.read(uid=os.getuid() + 1)  # owned by someone else than the dedicated account
        os.link(self.path, f"{self.machine.root}/second-name")
        with self.assertRaises(lab.LabError):
            self.read()

    def claude_printing_token(self) -> None:
        write_exec(self.machine.claude, f"#!{INTERPRETER} -IS\nimport os\n"
                   f"print(os.environ.get({mac.TOKEN_VARIABLE!r}) == {self.TOKEN!r}, "
                   f"{mac.TOKEN_VARIABLE!r} in os.environ)\n")
        self.machine.repin(claude_sha256=digest(self.machine.claude))

    def launch(self):
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        with host(self.machine):
            return backend, backend.launch((self.machine.claude,), b"", cwd=self.machine.candidate(),
                                           wall_seconds=5, max_output_bytes=4096, cancel=threading.Event())

    def test_launch_hands_the_token_to_the_child_only_and_records_no_value(self):
        self.claude_printing_token()
        self.write()
        backend, run = self.launch()
        self.assertEqual(run.stdout.decode().split(), ["True", "True"])
        self.assertEqual(backend.run_evidence[-1]["authToken"], "present")
        self.assertNotIn(self.TOKEN, json.dumps(backend.run_evidence))
        self.assertNotIn(mac.TOKEN_VARIABLE, os.environ)  # the supervisor's own environment is untouched
        self.assertEqual(self.machine.leftovers(), [])

    def test_launch_without_a_token_file_sets_no_variable(self):
        self.claude_printing_token()
        backend, run = self.launch()
        self.assertEqual(run.stdout.decode().split(), ["False", "False"])
        self.assertEqual(backend.run_evidence[-1]["authToken"], "absent")

    def test_launch_refuses_an_unsafe_token_file_before_creating_anything(self):
        self.claude_printing_token()
        self.write(mode=0o644)
        with self.assertRaises(lab.LabError) as caught:
            self.launch()
        self.assertEqual(caught.exception.reason, "auth-token-invalid")
        self.assertEqual(self.machine.leftovers(), [])

    def test_the_fixture_entries_never_receive_the_token(self):
        self.write()
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        source = b"import os\nprint(%r in os.environ)\n" % mac.TOKEN_VARIABLE
        with host(self.machine):
            result = backend.run(source, Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=5))
        self.assertEqual(result.stdout.decode().strip(), "False")
        self.assertNotIn("authToken", backend.run_evidence[-1])

    def test_the_environment_hash_binds_the_credential_method_and_the_token_names(self):
        base = self.machine.environment()
        for name, value in (("TOKEN_FILE", "other-file"), ("TOKEN_VARIABLE", "OTHER_VARIABLE"),
                            ("CREDENTIAL_METHOD", "dedicated-user-own-login")):
            with self.subTest(name), mock.patch.object(mac, name, value):
                self.assertNotEqual(self.machine.environment(), base)


class LiveOutputTests(unittest.TestCase):
    """T006 K1: ``launch(on_output=...)`` streams stdout while the child runs."""

    def setUp(self):
        self.machine = Machine(self)
        self.backend = make_backend(self.machine)
        self.addCleanup(self.backend.close)

    def claude(self, body: str) -> mac.MacOSContainment:
        write_exec(self.machine.claude, f"#!{INTERPRETER} -IS\nimport sys, time\n{body}")
        self.machine.repin(claude_sha256=digest(self.machine.claude))
        backend = make_backend(self.machine)
        self.addCleanup(backend.close)
        return backend

    def launch(self, backend, *, on_output, max_output=4096, wall=20, cancel=None):
        with host(self.machine):
            return backend.launch((self.machine.claude,), b"", cwd=self.machine.candidate(),
                                  wall_seconds=wall, max_output_bytes=max_output,
                                  cancel=cancel or threading.Event(), on_output=on_output)

    def test_chunks_arrive_in_order_complete_and_while_the_child_runs(self):
        backend = self.claude("for part in (b'one|', b'two|', b'three'):\n"
                              "    sys.stdout.buffer.write(part); sys.stdout.buffer.flush(); time.sleep(0.6)\n")
        chunks = []
        run = self.launch(backend, on_output=chunks.append)
        self.assertEqual(b"".join(chunks), b"one|two|three")
        self.assertGreaterEqual(len(chunks), 2)  # streamed, not delivered once at the end
        self.assertTrue(all(chunks))
        self.assertEqual((run.stdout, run.exit_code, run.settled), (b"one|two|three", 0, True))

    def test_the_tail_written_just_before_exit_is_still_delivered_once(self):
        backend = self.claude("sys.stdout.write('x' * 5000)\n")
        chunks = []
        run = self.launch(backend, on_output=chunks.append, max_output=8192)
        self.assertEqual(b"".join(chunks), b"x" * 5000)
        self.assertEqual(run.stdout, b"x" * 5000)

    def test_nothing_past_max_output_bytes_is_delivered(self):
        backend = self.claude("sys.stdout.write('y' * 100000)\nsys.stdout.flush()\ntime.sleep(30)\n")
        chunks = []
        run = self.launch(backend, on_output=chunks.append, max_output=64)
        delivered = b"".join(chunks)
        self.assertLessEqual(len(delivered), 64)
        self.assertEqual(delivered, run.stdout[:len(delivered)])
        self.assertEqual((run.output_truncated, run.settled, len(run.stdout)), (True, True, 64))

    def test_a_callback_that_sets_cancel_kills_and_settles_the_group(self):
        backend = self.claude("sys.stdout.write('init\\n'); sys.stdout.flush(); time.sleep(30)\n")
        cancel = threading.Event()
        started = time.monotonic()
        run = self.launch(backend, on_output=lambda chunk: cancel.set(), cancel=cancel)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual((run.cancelled, run.exit_code, run.settled), (True, None, True))
        self.assertEqual(run.stdout, b"init\n")
        self.assertEqual(self.machine.leftovers(), [])

    def test_no_chunk_is_delivered_after_the_callback_requested_the_stop(self):
        backend = self.claude("sys.stdout.write('z' * 300000)\nsys.stdout.flush()\ntime.sleep(30)\n")
        cancel, chunks = threading.Event(), []

        def first(chunk):
            chunks.append(chunk)
            cancel.set()

        run = self.launch(backend, on_output=first, max_output=1_000_000, cancel=cancel)
        self.assertEqual((len(chunks), run.cancelled, run.settled), (1, True, True))

    def test_a_raising_callback_still_settles_and_refuses_with_a_fixed_reason(self):
        backend = self.claude("sys.stdout.write('init\\n'); sys.stdout.flush(); time.sleep(30)\n")

        def boom(chunk):
            raise RuntimeError("secret detail")

        started = time.monotonic()
        with self.assertRaises(lab.LabError) as caught:
            self.launch(backend, on_output=boom)
        self.assertLess(time.monotonic() - started, 10)
        self.assertEqual(caught.exception.reason, "output-callback-failed")
        evidence = backend.run_evidence[-1]
        self.assertEqual((evidence["refused"], evidence["settled"]), ("output-callback-failed", True))
        self.assertEqual(self.machine.leftovers(), [])

    def test_a_callback_failing_on_the_final_tail_refuses_too(self):
        backend = self.claude("sys.stdout.write('quick')\n")

        def boom(chunk):
            raise RuntimeError("late")

        with self.assertRaises(lab.LabError) as caught:
            self.launch(backend, on_output=boom)
        self.assertEqual(caught.exception.reason, "output-callback-failed")

    def test_without_a_callback_the_result_is_identical(self):
        backend = self.claude("sys.stdout.write('same')\n")
        plain = self.launch(backend, on_output=None)
        streamed = self.launch(backend, on_output=lambda chunk: None)
        self.assertEqual(plain, streamed)
        self.assertEqual(plain.stdout, b"same")

    def test_a_non_callable_hook_is_an_invalid_launch(self):
        with host(self.machine), self.assertRaises(lab.LabError) as caught:
            self.backend.launch((self.machine.claude,), b"", cwd=self.machine.candidate(), wall_seconds=5,
                                max_output_bytes=10, cancel=threading.Event(), on_output="not callable")
        self.assertEqual(caught.exception.reason, "invalid-launch")


def kinfo_record(pid: int, *, ppid: int = 1, pgid: int = 1, stat: int = 2, seconds: int = 1_700_000_000,
                 microseconds: int = 5) -> bytes:
    """A 648-byte ``struct kinfo_proc`` with only the fields the backend reads."""
    raw = bytearray(mac._KINFO_BYTES)
    struct.pack_into("=qi", raw, 0, seconds, microseconds)
    raw[mac._KP_STAT] = stat
    struct.pack_into("=i", raw, mac._KP_PID, pid)
    struct.pack_into("=i", raw, mac._KP_PPID, ppid)
    struct.pack_into("=i", raw, mac._KP_PGID, pgid)
    return bytes(raw)


class ProcessAccountingTests(unittest.TestCase):
    """Process-table reads (no task access) classify any process; task reads fail closed for a live one."""

    def fake(self, *, task=0, kinfo=None, sysctl_error=0, sysctl_size=None, footprint=None, procargs=None):
        """``task``: errno of proc_pidinfo (0: readable); ``kinfo``: the record sysctl returns (None: gone)."""
        def proc_pidinfo(pid, flavor, arg, buffer, size):
            if task:
                ctypes.set_errno(task)
                return -1
            buffer[1] = 4096
            return size

        def sysctl(mib, count, buffer, size, new, newlen):
            if sysctl_error:
                ctypes.set_errno(sysctl_error)
                return -1
            if kinfo is None:
                size._obj.value = 0
                return 0
            ctypes.memmove(buffer, kinfo, len(kinfo))
            size._obj.value = len(kinfo) if sysctl_size is None else sysctl_size
            return 0

        def proc_pid_rusage(pid, flavor, buffer):
            if footprint is None:
                return -1
            buffer[mac._FOOTPRINT_WORD] = footprint
            return 0

        return mock.patch.object(mac, "_libsystem", lambda: SimpleNamespace(
            proc_pidinfo=proc_pidinfo, sysctl=sysctl, proc_pid_rusage=proc_pid_rusage))

    def test_kinfo_reads_start_parent_group_and_state_without_task_access(self):
        with self.fake(task=errno.EPERM, kinfo=kinfo_record(77, ppid=1, pgid=55, stat=2)):
            self.assertEqual(mac._kinfo(77), (1_700_000_000_000_005, 1, 55, 2))
            self.assertEqual(mac._process_links((77, 1_700_000_000_000_005)), (1, 55))
            self.assertEqual(mac._process_links((77, 1)), (None, None))  # the pid was reused

    def test_kinfo_of_a_process_that_is_gone_is_none(self):
        for fake in (self.fake(kinfo=None), self.fake(sysctl_error=errno.ESRCH)):
            with fake:
                self.assertIsNone(mac._kinfo(77))
                self.assertEqual(mac._process_links((77, 1)), (None, None))

    def test_kinfo_fails_closed_on_any_other_error_or_a_foreign_record(self):
        cases = (dict(sysctl_error=errno.EPERM), dict(kinfo=kinfo_record(78)),
                 dict(kinfo=kinfo_record(77), sysctl_size=100))
        for case in cases:
            with self.subTest(case), self.fake(**case), self.assertRaises(lab.LabError) as caught:
                mac._kinfo(77)
            self.assertEqual((caught.exception.reason, caught.exception.flavor),
                             ("process-accounting-failed", mac._KERN_PROC))

    def test_the_real_process_table_agrees_with_the_os(self):
        if sys.platform != "darwin":
            self.skipTest("macOS only")
        start, parent, group, state = mac._kinfo(os.getpid())
        self.assertEqual((parent, group), (os.getppid(), os.getpgrp()))
        self.assertGreater(start, 0)
        self.assertNotEqual(state, mac._SZOMB)
        self.assertIsNone(mac._kinfo(2 ** 22 - 3))

    def test_the_task_read_reports_the_larger_of_resident_size_and_physical_footprint(self):
        with self.fake(kinfo=kinfo_record(os.getpid()), footprint=9 << 30):
            self.assertEqual(mac._task_resident(os.getpid()), 9 << 30)  # compressed pages count
        with self.fake(kinfo=kinfo_record(os.getpid()), footprint=100):
            self.assertEqual(mac._task_resident(os.getpid()), 4096)
        with self.fake(kinfo=kinfo_record(os.getpid())):  # the rusage call failing keeps the resident size
            self.assertEqual(mac._task_resident(os.getpid()), 4096)

    def test_tagged_finds_the_run_tag_only_as_a_whole_environment_string(self):
        def sysctl_with(raw, status=0):
            def sysctl(mib, count, buffer, size, new, newlen):
                if status:
                    return status
                ctypes.memmove(buffer, raw, len(raw))
                size._obj.value = len(raw)
                return 0
            return mock.patch.object(mac, "_libsystem", lambda: SimpleNamespace(sysctl=sysctl))

        tag = b"BRAID_RUN_TAG=abc123"
        env = b"\x02\0\0\0/bin/x\0\0\0x\0y\0HOME=/h\0" + tag + b"\0PATH=/bin\0"
        with sysctl_with(env):
            self.assertTrue(mac._tagged(5, tag))
        with sysctl_with(b"\x01\0\0\0/bin/x\0x\0NOT" + tag + b"\0"):
            self.assertFalse(mac._tagged(5, tag))
        with sysctl_with(env, status=-1):
            self.assertFalse(mac._tagged(5, tag))  # unreadable or gone

    def test_lineage_adopts_a_tagged_process_whatever_its_parent_and_group(self):
        lineage = mac._Lineage(100, b"BRAID_RUN_TAG=t")
        with mock.patch.object(mac, "_process_links", lambda identity: (1, identity[0])), \
                mock.patch.object(mac, "_tagged", lambda pid, tag: pid == 300 and tag == b"BRAID_RUN_TAG=t"):
            members = lineage.members({(100, 1), (200, 2), (300, 3)})
        self.assertEqual(members, {(100, 1), (300, 3)})
        self.assertEqual(lineage.unrelated(), {(200, 2)})

    def test_a_task_read_of_a_process_that_is_gone_is_none(self):
        with self.fake(task=errno.ESRCH):
            self.assertIsNone(mac._task_resident(os.getpid()))

    def test_an_exited_unreaped_process_has_no_task_and_counts_as_gone(self):
        with self.fake(task=errno.EPERM, kinfo=kinfo_record(os.getpid(), stat=mac._SZOMB)):
            self.assertIsNone(mac._task_resident(os.getpid()))
        with self.fake(task=errno.EPERM, kinfo=None):
            self.assertIsNone(mac._task_resident(os.getpid()))

    def test_a_live_unreadable_process_fails_closed_with_errno_and_flavor(self):
        with self.fake(task=errno.EPERM, kinfo=kinfo_record(os.getpid())), \
                self.assertRaises(lab.LabError) as caught:
            mac._task_resident(os.getpid())
        self.assertEqual((caught.exception.reason, caught.exception.errno_code, caught.exception.flavor),
                         ("process-accounting-failed", errno.EPERM, mac._PROC_PIDTASKINFO))

    def test_resident_bytes_sums_readable_tasks_and_fails_closed_on_an_unreadable_member(self):
        with self.fake(kinfo=kinfo_record(os.getpid())):
            self.assertEqual(mac._resident_bytes({(1, 1), (2, 2)}), 8192)
        with self.fake(task=errno.EPERM, kinfo=kinfo_record(os.getpid())), self.assertRaises(lab.LabError):
            mac._resident_bytes({(os.getpid(), 1)})

    def test_unreadable_tasks_are_counted_for_the_evidence_and_never_raise(self):
        with self.fake(task=errno.EPERM):
            self.assertEqual(mac._unreadable_tasks({(1, 1), (2, 2)}), 2)
        with self.fake(task=errno.ESRCH):
            self.assertEqual(mac._unreadable_tasks({(1, 1)}), 0)
        with self.fake():
            self.assertEqual(mac._unreadable_tasks({(1, 1)}), 0)


class CompileCheckTests(unittest.TestCase):
    def test_the_exit_codes_of_both_runs_are_left_in_the_evidence(self):
        backend = make_backend(Machine(self))
        for exits, reason, expected in (((71, 1), "self-check-failed", {"denied": 71, "allowed": 1}),
                                        ((0, None), "self-check-allowed", {"denied": 0}),
                                        ((71, 0), None, {"denied": 71, "allowed": 0})):
            evidence = {}
            with mock.patch.object(mac.MacOSContainment, "_sandboxed", side_effect=list(exits)):
                if reason is None:
                    backend._compile_check("launch", evidence)
                else:
                    with self.assertRaises(lab.LabError) as caught:
                        backend._compile_check("launch", evidence)
                    self.assertEqual(caught.exception.reason, reason)
            self.assertEqual(evidence["compileExit"], expected)

    @unittest.skipUnless(HAS_SANDBOX_EXEC, "macOS sandbox-exec unavailable")
    def test_rendered_profiles_compile_deny_unlisted_exec_and_run_a_listed_one(self):
        # /usr/bin/true stands in for the interpreter so no framework has to be readable
        true = "/usr/bin/true"
        machine = Machine(self, interpreter=true, interpreter_sha256=digest(true), interpreter_root=true)
        backend = make_backend(machine)
        backend._compile_check("fixture", {})  # real sandbox-exec: exec of /usr/bin/false denied, true runs
        probe_dir = tempfile.mkdtemp(prefix="compile-", dir=machine.policy.run_root)
        self.addCleanup(shutil.rmtree, probe_dir, True)
        # the launch profile compiles and denies the unlisted exec (the pinned claude is not run here)
        self.assertEqual(backend._sandboxed("launch", probe_dir, [mac.COMPILE_PROBE], {}),
                         mac.EXIT_SANDBOX_EXEC_DENIED)
        with mock.patch.object(mac.ContainmentPolicy, "render", lambda self, entry: b"(version 1)(deny default"), \
                self.assertRaises(lab.LabError) as caught:
            backend._compile_check("fixture", {})
        self.assertEqual(caught.exception.reason, "profile-compile-failed")
        with mock.patch.object(mac.ContainmentPolicy, "render", lambda self, entry: b"(version 1)(allow default)"), \
                self.assertRaises(lab.LabError) as caught:
            backend._compile_check("fixture", {})
        self.assertEqual(caught.exception.reason, "self-check-allowed")
        with mock.patch.object(mac.ContainmentPolicy, "render", lambda self, entry: b"(version 1)(deny default)"), \
                self.assertRaises(lab.LabError) as caught:  # a profile that denies everything is not a profile
            backend._compile_check("fixture", {})
        self.assertEqual(caught.exception.reason, "self-check-failed")
        self.assertEqual(machine.leftovers(), [os.path.basename(probe_dir)])


def client_hello(server_name: str | None) -> bytes:
    incoming, outgoing = ssl.MemoryBIO(), ssl.MemoryBIO()
    context = ssl.create_default_context()
    context.check_hostname = server_name is not None
    tls = context.wrap_bio(incoming, outgoing, server_hostname=server_name)
    try:
        tls.do_handshake()
    except ssl.SSLWantReadError:
        return outgoing.read()
    raise AssertionError("handshake did not wait for the server")


def with_extension(hello: bytes, kind: int) -> bytes:
    """Append an empty extension and fix the three enclosing length fields."""
    body = bytearray(hello[5:])
    pos = 4 + 2 + 32
    pos += 1 + body[pos]
    pos += 2 + int.from_bytes(body[pos:pos + 2], "big")
    pos += 1 + body[pos]
    body += kind.to_bytes(2, "big") + b"\0\0"
    body[pos:pos + 2] = (int.from_bytes(body[pos:pos + 2], "big") + 4).to_bytes(2, "big")
    body[1:4] = (len(body) - 4).to_bytes(3, "big")
    return hello[:3] + len(body).to_bytes(2, "big") + bytes(body)


class ProxyTests(unittest.TestCase):
    def test_sni_parser(self):
        hello = client_hello("api.anthropic.com")
        self.assertEqual(mac.client_hello_sni(hello), "api.anthropic.com")
        self.assertEqual(mac.client_hello_sni(client_hello("API.Anthropic.com")), "api.anthropic.com")
        self.assertEqual(mac.client_hello_sni(with_extension(hello, 0x1234)), "api.anthropic.com")
        for bad in (b"", hello[:-1], hello + b"x", b"\x17" + hello[1:], hello[:5] + b"\x02" + hello[6:],
                    b"GET / HTTP/1.1\r\n\r\n", client_hello(None),
                    with_extension(hello, 0xFE0D), with_extension(hello, 0xFF0D)):
            self.assertIsNone(mac.client_hello_sni(bad))

    def connect_client(self, connect, family=socket.AF_INET, address="127.0.0.1"):
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=connect, timeout=2)
        proxy.start()
        self.addCleanup(proxy.close)
        client = socket.create_connection((address, proxy.port), timeout=3)
        self.addCleanup(client.close)
        return client

    @staticmethod
    def read_all(sock) -> bytes:
        data = b""
        try:
            while chunk := sock.recv(4096):
                data += chunk
        except OSError:
            pass
        return data

    def test_refuses_other_hosts_methods_and_sni(self):
        connect = mock.Mock(side_effect=AssertionError("upstream contacted"))
        for request in (b"CONNECT evil.example:443 HTTP/1.1\r\n\r\n", b"CONNECT api.anthropic.com:80 HTTP/1.1\r\n\r\n",
                        b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n", b"CONNECT api.anthropic.com:443 FOO\r\n\r\n",
                        b"CONNECT api.anthropic.com.:443 HTTP/1.1\r\n\r\n"):
            with self.subTest(request):
                client = self.connect_client(connect)
                client.sendall(request)
                self.assertTrue(self.read_all(client).startswith(b"HTTP/1.1 403"))
        client = self.connect_client(connect)
        client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n" + client_hello("evil.example"))
        self.assertEqual(self.read_all(client), b"HTTP/1.1 200 Connection Established\r\n\r\n")
        client = self.connect_client(connect)
        client.sendall(b"CONNECT " + b"a" * 9000)
        self.assertEqual(self.read_all(client), b"")
        client = self.connect_client(connect)  # silent client: handshake deadline closes it
        self.assertEqual(self.read_all(client), b"")
        connect.assert_not_called()

    def counted(self, proxy, wanted: dict, timeout: float = 3.0) -> dict:
        """The counters once they include ``wanted`` (the proxy thread updates them asynchronously)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            counters = proxy.counters()
            if all(counters.get(key) == value for key, value in wanted.items()):
                break
            time.sleep(0.01)
        return proxy.counters()

    def test_counters_tell_allowed_denied_and_direct_requests_apart(self):
        connect = mock.Mock(side_effect=AssertionError("upstream contacted"))
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=connect, timeout=2)
        proxy.start()
        self.addCleanup(proxy.close)
        self.assertEqual(proxy.counters(), {})
        requests = [b"CONNECT evil.example:443 HTTP/1.1\r\n\r\n", b"CONNECT api.anthropic.com:80 HTTP/1.1\r\n\r\n",
                    b"CONNECT api.anthropic.com:443 FOO\r\n\r\n", b"GET http://api.anthropic.com/ HTTP/1.1\r\n\r\n",
                    b"GET / HTTP/1.1\r\nHost: x\r\n\r\n", b"\x16\x03\x01garbage\r\n\r\n"]
        for request in requests:
            with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:
                client.sendall(request)
                self.read_all(client)
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:  # evil SNI
            client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n" + client_hello("evil.example"))
            self.read_all(client)
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:  # hangs up early
            client.sendall(b"CONNECT api.anthropic.com:4")
            client.shutdown(socket.SHUT_WR)
            self.read_all(client)
        expected = {"connections": 8, "denied": 5, "unexpectedDirect": 3, "denied:target-not-allowed": 2,
                    "denied:bad-request": 1, "denied:sni-mismatch": 1, "denied:incomplete": 1}
        self.assertEqual(self.counted(proxy, expected), expected)
        connect.assert_not_called()

    def test_counters_record_the_tunnel_its_target_and_the_bytes_in_both_directions(self):
        upstream_side, proxy_side = socket.socketpair()
        self.addCleanup(upstream_side.close)
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=mock.Mock(return_value=proxy_side), timeout=2)
        proxy.start()
        self.addCleanup(proxy.close)
        hello = client_hello("api.anthropic.com")
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:
            client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n" + hello + b"more")
            self.assertTrue(client.recv(64).startswith(b"HTTP/1.1 200"))
            upstream_side.settimeout(2)
            received = b""
            while len(received) < len(hello) + 4:
                received += upstream_side.recv(65_536)
            upstream_side.sendall(b"server-bytes")
            self.assertEqual(client.recv(64), b"server-bytes")
            client.sendall(b"again")
            self.assertEqual(upstream_side.recv(16), b"again")
        counters = self.counted(proxy, {"bytesUp": len(hello) + 4 + 5})
        self.assertEqual(counters, {"connections": 1, "allowed": 1, "allowed:api.anthropic.com:443": 1,
                                    "bytesUp": len(hello) + 4 + 5, "bytesDown": len(b"server-bytes")})

    def test_a_failed_upstream_connect_is_counted_apart(self):
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=mock.Mock(side_effect=OSError), timeout=2)
        proxy.start()
        self.addCleanup(proxy.close)
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:
            client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\n\r\n" + client_hello("api.anthropic.com"))
            self.read_all(client)
        counters = self.counted(proxy, {"upstreamFailed": 1})
        self.assertEqual((counters["upstreamFailed"], counters.get("allowed", 0), counters.get("denied", 0)), (1, 0, 0))

    def test_a_silent_client_is_a_counted_timeout_and_capacity_overflow_is_denied(self):
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=mock.Mock(), timeout=0.3)
        proxy.start()
        self.addCleanup(proxy.close)
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:
            self.read_all(client)
        self.assertEqual(self.counted(proxy, {"denied:timeout": 1})["denied"], 1)
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=mock.Mock(), timeout=5)
        proxy.start()
        self.addCleanup(proxy.close)
        held = [socket.create_connection(("127.0.0.1", proxy.port), timeout=3)
                for _ in range(mac.EgressProxy.MAX_CONNECTIONS)]
        self.addCleanup(lambda: [c.close() for c in held])
        self.counted(proxy, {"connections": mac.EgressProxy.MAX_CONNECTIONS})
        with socket.create_connection(("127.0.0.1", proxy.port), timeout=3) as client:
            self.read_all(client)
        counters = self.counted(proxy, {"denied:capacity": 1})
        self.assertEqual((counters["denied"], counters["denied:capacity"]), (1, 1))

    def test_the_accept_loop_dying_is_visible_but_closing_is_not_a_failure(self):
        proxy = mac.EgressProxy(0, ("api.anthropic.com:443",), connect=mock.Mock(), timeout=1)
        self.assertTrue(proxy.healthy)
        dying = mock.Mock(accept=mock.Mock(side_effect=OSError))
        proxy._servers.append(dying)  # a live listener whose accept fails
        proxy._accept(dying)
        self.assertFalse(proxy.healthy)
        proxy._servers.clear()
        proxy.start()  # a fresh start clears it
        self.addCleanup(proxy.close)
        self.assertTrue(proxy.healthy)
        closed = mock.Mock(accept=mock.Mock(side_effect=OSError))
        proxy._accept(closed)  # not a current listener (close() removed it): not a failure
        self.assertTrue(proxy.healthy)

    def test_relays_allowed_endpoint_with_matching_sni(self):
        for family, address in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
            with self.subTest(address):
                upstream_side, proxy_side = socket.socketpair()
                self.addCleanup(upstream_side.close)
                connect = mock.Mock(return_value=proxy_side)
                hello = client_hello("api.anthropic.com")
                client = self.connect_client(connect, family, address)
                client.sendall(b"CONNECT api.anthropic.com:443 HTTP/1.1\r\nHost: api.anthropic.com:443\r\n\r\n"
                               + hello + b"pipelined")
                self.assertEqual(client.recv(64), b"HTTP/1.1 200 Connection Established\r\n\r\n")
                upstream_side.settimeout(2)
                received = b""
                while len(received) < len(hello) + 9:
                    received += upstream_side.recv(65_536)
                self.assertEqual(received, hello + b"pipelined")
                upstream_side.sendall(b"server-bytes")
                self.assertEqual(client.recv(64), b"server-bytes")
                connect.assert_called_once_with(("api.anthropic.com", 443), timeout=2)


@unittest.skipUnless(os.environ.get("BRAID_T007_LIVE_CONTROLS") == "1",
                     "the live disk-bound probe runs only with BRAID_T007_LIVE_CONTROLS=1")
class LiveDiskBoundProbeTests(unittest.TestCase):
    """DRV-06: the real 100,000-entry bound over the real filesystem, config_dir included.

    Local only (temporary directories, no sandbox, no claude, no network); it writes about 100,000
    empty files, which is why CI never runs it.
    """

    def tree(self):
        root = Path(tempfile.mkdtemp(prefix="braid-live-disk-"))
        self.addCleanup(mac._remove_tree, str(root))
        return [str(root / name) for name in ("candidate", "tmp", "config")]

    def fill(self, directory: str, count: int) -> None:
        os.mkdir(directory)
        for index in range(count):
            open(f"{directory}/f{index}", "wb").close()

    def test_the_default_entry_bound_trips_on_config_dir_alone_and_on_the_three_trees_together(self):
        candidate, tmpdir, config = self.tree()
        self.assertEqual(mac.LIMITS["diskFiles"], 100_000)
        self.fill(candidate, 40_000)
        self.fill(tmpdir, 40_000)
        os.mkdir(config)
        guard = mac._DiskGuard((candidate, tmpdir, config))
        self.assertFalse(guard.exceeded())  # 80,000 entries: under the bound
        self.fill(f"{config}/sessions", 20_001)  # the account's own tree pushes the total over it
        self.assertTrue(guard.exceeded())
        self.assertGreater(guard.files, 100_000)

    def test_a_config_dir_over_the_bound_by_itself_is_caught(self):
        candidate, tmpdir, config = self.tree()
        os.mkdir(candidate)
        os.mkdir(tmpdir)
        self.fill(config, 100_001)
        self.assertTrue(mac._DiskGuard((candidate, tmpdir, config)).exceeded())


if __name__ == "__main__":
    unittest.main()
