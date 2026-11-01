# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T005 macOS containment backend: policy, refusals, supervision and proxy.

Unit level only: no dedicated account is created, ``claude`` never runs and no live
probe is executed. Host facts, the account and the probe runner are stubbed; the
supervisor tests replace ``sandbox-exec`` with a pass-through script so only the
rlimit preamble, watchdog and settlement run, and the per-user process listing is
always stubbed so no real process of the developer is ever swept.
"""
from contextlib import ExitStack, contextmanager
from dataclasses import replace
import fcntl
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
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
FIXTURE = b'import json\nopen("out.txt", "w").write("ok")\nprint(json.dumps({"seq": 0, "kind": "start"}))\n'
INTERPRETER = os.path.realpath(sys.executable)
# Stands in for sandbox-exec: drops its options and execs the target unchanged.
PASS_THROUGH = (f"#!{INTERPRETER} -IS\nimport os, sys\n"
                "args = sys.argv[sys.argv.index('--') + 1:]\nos.execv(args[0], args)\n")
# Stands in for claude without forking: prints its environment names, then its stdin.
FAKE_CLAUDE = (f"#!{INTERPRETER} -IS\nimport os, sys\n"
               "print(' '.join(sorted(os.environ)))\nsys.stdout.write(sys.stdin.read())\n")
BASELINE = {(1, 1)}
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
        for name in ("run", "config", "bin"):
            os.mkdir(f"{self.root}/{name}", 0o700)
        os.chmod(f"{self.root}/bin", 0o755)
        self.claude = write_exec(f"{self.root}/bin/claude", FAKE_CLAUDE)
        self.sandbox = write_exec(f"{self.root}/bin/sandbox-exec", PASS_THROUGH)
        values = dict(
            account=ACCOUNT, run_root=f"{self.root}/run", config_dir=f"{self.root}/config",
            claude=self.claude, claude_sha256=digest(self.claude), claude_version=mac.CLAUDE_VERSION,
            interpreter=INTERPRETER, interpreter_sha256=digest(INTERPRETER),
            interpreter_root=os.path.dirname(INTERPRETER),
            sandbox_exec_sha256=digest(self.sandbox), proxy_port=free_port(),
            probe_catalog_sha256="c" * 64)
        self.policy = mac.ContainmentPolicy(**(values | policy))

    def repin(self, **change) -> None:
        self.policy = replace(self.policy, **change)

    def environment(self, facts: mac.HostFacts = FACTS) -> str:
        with mock.patch.object(mac, "SANDBOX_EXEC", self.sandbox):
            return mac.environment_sha256(self.policy, facts, os.getuid())

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


def make_backend(machine: Machine, *, runner=expected_probes, **record_args) -> mac.MacOSContainment:
    return mac.MacOSContainment(machine.policy, probe_runner=runner, clock=lambda: NOW,
                                **records(machine.environment(), **record_args))


@contextmanager
def host(machine: Machine, *, facts: mac.HostFacts = FACTS, uid: int | None = None, darwin: bool = True,
         stub_compile_check: bool = True, processes=None, env: dict | None = None,
         mechanism_uid: int | None = None):
    """Stub every Darwin fact; ``processes`` stubs the per-user process listing.

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
        if name != ACCOUNT:
            raise KeyError(name)
        return SimpleNamespace(pw_uid=uid)

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
            "_resident_bytes": lambda processes: 0,
            "_trusted_file": trusted,
        }
        for name, value in patches.items():
            stack.enter_context(mock.patch.object(mac, name, value))
        if stub_compile_check:
            stack.enter_context(mock.patch.object(mac.MacOSContainment, "_compile_check",
                                                  lambda self, entry: None))
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
            if entry == "launch":
                allowed.add(f'(allow file-read* file-write* (subpath "{policy.config_dir}"))')
            self.assertEqual(writes, allowed)
            self.assertEqual(lines[-2], '(deny file-read* file-write* (subpath "/System/Volumes/Data"))')
            for denied in ("mach-lookup", "sysctl", "network-bind", "network-inbound", "process-exec*)",
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
        facts = [mac.HostFacts("27.0.2", "26A434", "arm64"), mac.HostFacts("27.0.1", "26A435", "arm64"),
                 mac.HostFacts("27.0.1", "26A434", "x86_64")]
        changes = [dict(sandbox_exec_sha256="1" * 64), dict(claude_sha256="2" * 64),
                   dict(interpreter_sha256="3" * 64), dict(probe_catalog_sha256="4" * 64),
                   dict(proxy_port=policy.proxy_port + 1), dict(account="braid-lab2"),
                   dict(refresh_endpoints=("platform.claude.com:443",)),
                   dict(helpers=((f"{root}/bin/claude-helper", "5" * 64),)),
                   dict(config_dir=f"{root}/config2"), dict(run_root=f"{root}/run2"),
                   dict(claude=f"{root}/bin/claude2")]
        changed = {mac.environment_sha256(policy, f, uid) for f in facts}
        changed.add(mac.environment_sha256(policy, FACTS, uid + 1))
        changed |= {mac.environment_sha256(replace(policy, **c), FACTS, uid) for c in changes}
        with mock.patch.object(mac, "_component_hashes", lambda: {"harness_lab.py": "0" * 64}):
            changed.add(mac.environment_sha256(policy, FACTS, uid))
        with mock.patch.object(mac, "LIMITS", mac.LIMITS | {"openFiles": 255}):
            changed.add(mac.environment_sha256(policy, FACTS, uid))
        self.assertEqual(len(changed), len(facts) + 1 + len(changes) + 2)
        self.assertNotIn(base, changed)

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
                mac.MacOSContainment(machine.policy, probe_runner=expected_probes,
                                     **records(environment, **change))
            self.assertEqual(caught.exception.reason, reason)
        good = records(environment)
        for key in ("qualification_sha256", "host_qualification_sha256"):
            with self.subTest(key), self.assertRaises(lab.LabError) as caught:
                mac.MacOSContainment(machine.policy, probe_runner=expected_probes, **(good | {key: "0" * 64}))
            self.assertEqual(caught.exception.reason, "qualification-drift")
        with self.assertRaises(lab.LabError) as caught:
            mac.MacOSContainment(object(), probe_runner=expected_probes, **good)
        self.assertEqual(caught.exception.reason, "invalid-policy")


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
                             (0, "self-check-allowed"), (134, "self-check-allowed")):
            with self.subTest(code), mock.patch.object(
                    mac.subprocess, "run", return_value=SimpleNamespace(returncode=code)):
                self.refuse(reason, stub_compile_check=False)
        with mock.patch.object(mac.subprocess, "run",
                               side_effect=subprocess.TimeoutExpired("sandbox-exec", 10)):
            self.refuse("profile-compile-failed", stub_compile_check=False)
        with mock.patch.object(mac.tempfile, "mkdtemp", side_effect=PermissionError):
            self.refuse("profile-compile-failed", stub_compile_check=False)
        # positive control: the exec-denied exit passes the mocked compile check
        backend = make_backend(self.machine, runner=lambda probe, _b: "allowed")
        with mock.patch.object(mac.subprocess, "run",
                               return_value=SimpleNamespace(returncode=mac.EXIT_SANDBOX_EXEC_DENIED)):
            self.refuse("self-check-allowed", backend, stub_compile_check=False)
        self.assertEqual(backend.run_evidence[-1]["compileCheck"], "exec-denied")

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
        for facts in (mac.HostFacts("27.1", "26B1", "arm64"), mac.HostFacts("26.4.1", "25E1", "arm64"),
                      mac.HostFacts("27.0.1", "garbage", "arm64"), mac.HostFacts("27.0.1.1", "26A434", "arm64")):
            with self.subTest(facts):
                self.refuse("os-unsupported", facts=facts)

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
                         set(self.machine.policy.child_environment("fixture", "/x")))

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

    def test_escaped_process_is_swept_and_unsettles(self):
        alive = {"escapee": False}
        escapee = (999_999, 7)

        def processes(uid):
            return BASELINE | ({escapee} if alive["escapee"] else set())

        def fake_kill(pid, sig):
            alive["escapee"] = False

        real_settle = mac._settle

        def settle(pgid):  # the escapee shows up outside the group once the group is gone
            alive["escapee"] = True
            return real_settle(pgid)

        with host(self.machine, processes=processes), mock.patch.object(mac, "_settle", settle), \
                mock.patch.object(mac.os, "kill", side_effect=fake_kill) as kill_mock:
            result = self.backend.run(b"pass\n", Path(self.machine.candidate()), lab.FixtureLimits(wall_seconds=5))
        self.assertFalse(result.settled)
        self.assertEqual(self.backend.run_evidence[-1]["escapedProcesses"], 1)
        kill_mock.assert_called_with(999_999, mac.signal.SIGKILL)

    def test_sweep_never_runs_as_another_user(self):
        for host_args in (dict(uid=os.getuid() + 1), dict()):
            with self.subTest(host_args), host(self.machine, **host_args), self.assertRaises(lab.LabError) as caught:
                if not host_args:
                    self.machine.repin(account="gone-account")
                    self.backend.policy = self.machine.policy
                self.backend._sweep(os.getuid(), set())
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
                         set(self.machine.policy.child_environment("launch", "/x")))
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


class CompileCheckTests(unittest.TestCase):
    @unittest.skipUnless(HAS_SANDBOX_EXEC, "macOS sandbox-exec unavailable")
    def test_rendered_profiles_compile_and_deny_unlisted_exec(self):
        machine = Machine(self)
        backend = make_backend(machine)
        for entry in mac.ENTRIES:
            backend._compile_check(entry)  # real sandbox-exec: must report exec denied
        with mock.patch.object(mac.ContainmentPolicy, "render", lambda self, entry: b"(version 1)(deny default"), \
                self.assertRaises(lab.LabError) as caught:
            backend._compile_check("fixture")
        self.assertEqual(caught.exception.reason, "profile-compile-failed")
        with mock.patch.object(mac.ContainmentPolicy, "render", lambda self, entry: b"(version 1)(allow default)"), \
                self.assertRaises(lab.LabError) as caught:
            backend._compile_check("fixture")
        self.assertEqual(caught.exception.reason, "self-check-allowed")
        self.assertEqual(machine.leftovers(), [])


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


if __name__ == "__main__":
    unittest.main()
