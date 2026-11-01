# SPDX-License-Identifier: AGPL-3.0-only
"""Native Claude transport controls (procedure_002) with a fake contained launcher only.

Nothing here runs the real ``claude`` binary or a real sandbox: the launcher is a Python
object that replays scripted stdout chunks, and the "executable" is a temporary file whose
hash is pinned. The macOS backend is never constructed: ``MacLaunchSignature`` borrows only
its real ``launch`` entry point and replaces the supervision below it with the same fake.
"""
import contextlib
import inspect
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest import mock

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_context as ctx
from agent_braid import harness_host_claude as hc
from agent_braid import harness_lab as lab
from agent_braid import harness_manifest as manifests
from agent_braid import harness_transport_claude as tc
from agent_braid.system_one import canonical
from tests.test_harness_host_claude import (
    SESSION, assistant, init, make_inventory, make_manifest_and_context, qualification_wire, result)
from tests.test_harness_manifest import make_native_manifest

NOW = 1_800_000_000
CLOCK = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
BUILD_TEXT = "2.1.292 (Claude Code)"
BACKEND = "macos-dedicated-user-sandbox-exec"
FAKE_CLAUDE = b"#!/bin/sh\necho fake claude, never executed\n"
NOTE = b"owned note\n"
WINDOW = hc.CompatibilityWindow((2, 1, 0), (2, 2, 0))


def line(event):
    return canonical(dict(event)) + b"\n"


def good_chunks(**init_over):
    return [line(init(claude_code_version=BUILD_TEXT, **init_over)),
            line(assistant({"type": "text", "text": "reading"})), line(result())]


def reading(**over):
    value = {"source": "claude-desktop-usage-card", "observedAt": "2026-11-01T11:59:00Z",
             "fiveHourPercent": 10, "weeklyPercent": 20, "extraUsageEnabled": False}
    value.update(over)
    return value


class FakePolicy:
    def __init__(self, path, digest):
        self.claude, self.claude_sha256, self.claude_version = path, digest, "2.1.292"


class FakeLauncher(lab.ContainmentBackend):
    """Replays scripted stdout through ``on_output`` and honours ``cancel`` like the backend."""

    kind = "native"

    def __init__(self, policy, qualification, host_qualification, *, chunks=(), honour_kill=True,
                 version_text=BUILD_TEXT, fail=None, during=None):
        self.policy, self.qualification, self.host_qualification = policy, qualification, host_qualification
        self.chunks, self.honour_kill, self.version_text = list(chunks), honour_kill, version_text
        self.fail, self.during = fail, during
        self.calls, self.killed = [], False

    def launch(self, argv, stdin, *, cwd, wall_seconds, max_output_bytes, cancel, on_output=None):
        self.calls.append(dict(argv=argv, stdin=stdin, cwd=cwd, wall=wall_seconds, cancel=cancel))
        if argv[1:] == ("--version",):
            return hc.HostRun(self.version_text.encode() + b"\n", 0)
        if self.fail is not None:
            raise lab.LabError(self.fail)
        out = b""
        for chunk in self.chunks:
            if self.during is not None:
                self.during(cancel)
            if cancel.is_set() and self.honour_kill:
                self.killed = True
                return hc.HostRun(out, None, cancelled=True)
            out += chunk
            if on_output is not None:
                on_output(chunk)
        if cancel.is_set():
            self.killed = True
            return hc.HostRun(out, None, cancelled=True)
        return hc.HostRun(out, 0)

    @property
    def run_calls(self):
        return [c for c in self.calls if c["argv"][1:] != ("--version",)]


class MacLaunchSignature(mac.MacOSContainment):
    """The real ``MacOSContainment.launch`` (validation, signature, hook plumbing) over a fake
    supervisor: no policy file, sandbox, account or process is involved."""

    def __init__(self, fake):  # deliberately skips the real constructor
        self.fake = fake
        self.policy, self.qualification, self.host_qualification = (
            fake.policy, fake.qualification, fake.host_qualification)
        self.run_evidence = []

    def close(self):
        pass

    def _exclusive(self, entry):
        return contextlib.nullcontext()

    def _pre_session(self, entry, workdir, *, probes):
        return {}, "candidate", 0

    def _spawn(self, entry, target, evidence, *, candidate, uid, wall, cpu, max_output, cancel, stdin,
               on_output=None):
        return self.fake.launch(tuple(target), stdin, cwd=candidate, wall_seconds=wall,
                                max_output_bytes=max_output, cancel=cancel, on_output=on_output)


def make_launcher_without_hook(policy, qualification, host_qualification):
    class NoHook(lab.ContainmentBackend):
        kind = "native"

        def launch(self, argv, stdin, *, cwd, wall_seconds, max_output_bytes, cancel):
            raise AssertionError("never launched")

    backend = NoHook()
    backend.policy, backend.qualification, backend.host_qualification = policy, qualification, host_qualification
    return backend


class Fixture:
    """A pinned fake executable, matching records, a native manifest and a transport."""

    def __init__(self, test, **launcher_kw):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t006-"))
        test.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.exe = self.tmp / "claude"
        self.exe.write_bytes(FAKE_CLAUDE)
        self.exe_sha = sha256(FAKE_CLAUDE).hexdigest()
        self.env_sha = "7" * 64
        self.policy = FakePolicy(str(self.exe), self.exe_sha)
        self.qualification = self.backend_qualification()
        self.host_qualification = self.host_record()
        self.launcher = FakeLauncher(self.policy, self.qualification, self.host_qualification,
                                     chunks=launcher_kw.pop("chunks", good_chunks()), **launcher_kw)

    def backend_qualification(self, **over):
        wire = {"format": lab.QUALIFICATION_FORMAT, "backend": BACKEND, "kind": "native",
                "environmentSha256": self.env_sha, "enforced": list(lab.ENFORCED_EFFECTS),
                "expiresAt": NOW + 100, "evidenceSha256": "e" * 64} | over
        raw = canonical(wire)
        return lab.verify_qualification(raw, expected_sha256=sha256(raw).hexdigest())

    def host_record(self, **over):
        raw = canonical(qualification_wire(environmentSha256=self.env_sha) | over)
        return hc.verify_host_qualification(raw, expected_sha256=sha256(raw).hexdigest())

    def manifest(self, setters=()):
        value = make_native_manifest()
        value["context"] = [{"id": "note", "path": "a/note.txt", "sha256": sha256(NOTE).hexdigest(),
                             "sizeBytes": len(NOTE), "trust": "untrusted-evidence", "selected": True}]
        value["effects"]["read"] = ["base/guidance/main.md", "candidate/guidance/main.md",
                                    "context/a/note.txt", "source/task.txt"]
        value["environment"]["sha256"] = self.env_sha
        value["host"]["executableSha256"] = self.exe_sha
        value["containment"] = {"backend": BACKEND, "qualificationSha256": self.qualification.sha256}
        value["hostQualificationSha256"] = self.host_qualification.sha256
        for setter in setters:
            setter(value)
        manifest = manifests.parse_manifest(canonical(value))
        budget = ctx.ContextBudget(max_entries=4, max_entry_bytes=1024, max_total_bytes=2048,
                                   excerpt_bytes=128)
        return manifest, ctx.assemble_context(manifest, {"a/note.txt": NOTE}, budget=budget)

    def transport(self, *, pre=None, quota=("cohort", {"unitsUsed": 0, "cohortWeeklyPercent": 0}),
                  environ=None, backend=None):
        return tc.NativeClaudeTransport(
            backend or self.launcher, workdir=self.tmp, pre_reading=reading() if pre is None else pre,
            quota=quota, clock=lambda: CLOCK, environ={} if environ is None else environ)


class NativeTransportTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture(self)

    def go(self, *, fx=None, transport=None, manifest_over=None, qualification="default", **over):
        fx = fx or self.fx
        manifest, context = fx.manifest(manifest_over or ())
        args = dict(transport=transport or fx.transport(), request=hc.ClaudeRequest(SESSION),
                    compatibility=WINDOW, attempt_id="attempt-1", inventory=make_inventory(),
                    now=NOW, retention_seconds=60,
                    qualification=fx.host_qualification if qualification == "default" else qualification)
        args.update(over)
        return hc.run_claude(manifest, context, **args)

    def refuses(self, reason, **kw):
        with self.assertRaises(hc.ClaudeHostError) as cm:
            self.go(**kw)
        self.assertEqual(cm.exception.reason, reason)

    def state(self, outcome):
        return outcome.observation.to_dict()["terminal"]

    def kinds(self, outcome):
        return [e["kind"] for e in outcome.observation.to_dict()["events"]]

    # --- positive control ---

    def test_complete_run_through_the_launcher_is_native_host_evidence_without_authority(self):
        transport = self.fx.transport()
        outcome = self.go(transport=transport)
        self.assertEqual((outcome.transport, outcome.observation.to_dict()["source"]), ("native", "host"))
        self.assertEqual(self.state(outcome), "completed")
        self.assertFalse(outcome.executionAuthorization)
        version_call, run_call = self.fx.launcher.calls
        self.assertEqual(version_call["argv"], (str(self.fx.exe), "--version"))
        self.assertEqual(run_call["argv"][0], str(self.fx.exe))  # absolute pinned path (K4)
        self.assertEqual(run_call["argv"][1:4], ("-p", "--output-format", "stream-json"))
        self.assertEqual(run_call["cwd"], self.fx.tmp)
        self.assertGreater(len(run_call["stdin"]), 0)  # the prompt travels on stdin
        evidence, = transport.run_evidence
        self.assertEqual((evidence["qualificationSha256"], evidence["hostQualificationSha256"],
                          evidence["executableSha256"]),
                         (self.fx.qualification.sha256, self.fx.host_qualification.sha256, self.fx.exe_sha))
        self.assertEqual((evidence["quotaProceed"], evidence["quotaReason"]), (True, "within-caps"))
        self.assertFalse(evidence["executionAuthorization"])

    def test_native_env_policy_has_config_and_tmp_and_no_secret_or_denied_variable(self):
        self.assertEqual(tc.NATIVE_ENV_ALLOW, ("CLAUDE_CONFIG_DIR", "HOME", "PATH", "TMPDIR"))
        self.assertFalse(set(tc.NATIVE_ENV_ALLOW) & set(hc.ENV_DENY))

    def test_session_wall_bound_is_native_only_and_reaches_the_launcher(self):
        outcome = self.go(limits=hc.HostLimits(wall_seconds=1800))
        self.assertEqual(self.state(outcome), "completed")
        self.assertEqual(self.fx.launcher.run_calls[0]["wall"], 1800)
        with self.assertRaises(hc.ClaudeHostError):
            hc.HostLimits(wall_seconds=1801)

    # --- qualification controls ---

    def test_missing_expired_drifted_or_foreign_qualification_never_launches(self):
        for label, qualification in (
                ("missing", None),
                ("expired", self.fx.host_record(expiresAt=NOW)),
                ("drifted", self.fx.host_record(environmentSha256="8" * 64)),
                ("object", object())):
            with self.subTest(label):
                self.refuses("native-host-unqualified", qualification=qualification)
        with self.assertRaises(hc.ClaudeHostError) as cm:  # a Codex record cannot even be parsed
            self.fx.host_record(host="codex")
        self.assertEqual(cm.exception.reason, "host-mismatch")
        self.assertEqual(self.fx.launcher.calls, [])

    def test_passed_qualification_must_be_the_backends_verified_record(self):
        other = self.fx.host_record(evidenceSha256="d" * 64)
        self.refuses("qualification-mismatch", qualification=other)
        self.assertEqual(self.fx.launcher.calls, [])

    def test_unqualified_backend_never_launches(self):
        fx = self.fx
        for label, change in (
                ("expired", {"expiresAt": NOW}),
                ("other environment", {"environmentSha256": "8" * 64})):
            with self.subTest(label):
                fx.launcher.qualification = fx.backend_qualification(**change)
                self.refuses("containment-unqualified")
        fx.launcher.qualification = None  # a backend without a verified record is not even wrapped
        with self.assertRaises(hc.ClaudeHostError) as cm:
            fx.transport()
        self.assertEqual(cm.exception.reason, "invalid-backend")
        self.assertEqual(fx.launcher.calls, [])

    def test_missing_wrong_or_hookless_backend_is_refused_at_construction(self):
        fx = self.fx
        for label, backend, reason in (
                ("missing", None, "invalid-backend"),
                ("simulated", lab.SimulatedContainment(), "invalid-backend"),
                ("no live hook", make_launcher_without_hook(fx.policy, fx.qualification, fx.host_qualification),
                 "live-init-unsupported")):
            with self.subTest(label), self.assertRaises(hc.ClaudeHostError) as cm:
                fx.transport(backend=backend) if backend is not None else tc.NativeClaudeTransport(
                    None, workdir=fx.tmp, pre_reading=reading(), quota=("probe", 0), clock=lambda: CLOCK)
            self.assertEqual(cm.exception.reason, reason)

    def test_manifest_declarations_must_equal_the_trusted_values(self):
        controls = {
            "containment qualification": ("qualification-mismatch", lambda v: v["containment"].update(
                qualificationSha256="1" * 64)),
            "host qualification": ("qualification-mismatch", lambda v: v.update(
                hostQualificationSha256="1" * 64)),
            "containment backend": ("qualification-mismatch", lambda v: v["containment"].update(
                backend="other-backend")),
            "executable": ("executable-mismatch", lambda v: v["host"].update(executableSha256="1" * 64)),
        }
        for label, (reason, setter) in controls.items():
            with self.subTest(label):
                self.refuses(reason, manifest_over=[setter])
        with self.subTest("build"):
            self.fx.policy.claude_version = "2.1.291"
            self.refuses("build-mismatch")
        self.assertEqual(self.fx.launcher.calls, [])

    def test_offline_manifest_cannot_use_the_native_transport(self):
        manifest, context = make_manifest_and_context()
        data = manifest.to_dict()
        data["host"]["kind"] = "claude"
        with self.assertRaises(hc.ClaudeHostError) as cm:
            hc.run_claude(replace(manifest, data=data), context, transport=self.fx.transport(),
                          request=hc.ClaudeRequest(SESSION), compatibility=WINDOW, attempt_id="a1",
                          inventory=make_inventory(), now=NOW, retention_seconds=60,
                          qualification=self.fx.host_qualification)
        self.assertIn(cm.exception.reason, ("containment-unqualified", "native-host-unqualified"))
        self.assertEqual(self.fx.launcher.calls, [])

    # --- credentials and route ---

    def test_api_key_variables_refuse_before_any_launch(self):
        for name in hc.ENV_DENY:
            with self.subTest(name):
                self.refuses("env-deny-present", transport=self.fx.transport(environ={name: "x"}))
        self.assertEqual(self.fx.launcher.calls, [])

    def test_non_subscription_key_source_kills_at_init_and_no_result_is_accepted(self):
        for label, chunks in (
                ("one chunk", [b"".join(good_chunks(apiKeySource="ANTHROPIC_API_KEY"))]),
                ("line by line", good_chunks(apiKeySource="ANTHROPIC_API_KEY")),
                ("split mid-line", [line(init(claude_code_version=BUILD_TEXT, apiKeySource="apiKey"))[:20],
                                    line(init(claude_code_version=BUILD_TEXT, apiKeySource="apiKey"))[20:]
                                    + line(result())])):
            for honour in (True, False):
                with self.subTest(label, honour_kill=honour):
                    fx = Fixture(self, chunks=chunks, honour_kill=honour)
                    outcome = self.go(fx=fx, transport=fx.transport())
                    self.assertTrue(fx.launcher.killed)
                    self.assertEqual(self.state(outcome), "refused")
                    self.assertNotIn("message", self.kinds(outcome))
                    self.assertTrue(outcome.cancelled)
                    self.assertIsNone(outcome.exit_code)

    def test_kill_is_requested_before_later_events_are_streamed(self):
        seen = []
        fx = Fixture(self, chunks=good_chunks(apiKeySource="ANTHROPIC_API_KEY"),
                     during=lambda cancel: seen.append(cancel.is_set()))
        self.go(fx=fx, transport=fx.transport())
        self.assertEqual(seen, [False, True])  # stopped at the second chunk, never fed the third

    def test_subscription_key_sources_proceed(self):
        for source in sorted(hc.SUBSCRIPTION_KEY_SOURCES):
            with self.subTest(source):
                fx = Fixture(self, chunks=good_chunks(apiKeySource=source))
                self.assertEqual(self.state(self.go(fx=fx, transport=fx.transport())), "completed")

    def test_assistant_or_result_before_init_and_oversized_lines_kill_and_refuse(self):
        for label, chunks in (("assistant first", [line(assistant({"type": "text", "text": "x"}))]
                               + good_chunks()),
                              ("result first", [line(result())] + good_chunks()),
                              ("junk without newline", [b"x" * (tc.MAX_INIT_BYTES + 1)] + good_chunks())):
            with self.subTest(label):
                fx = Fixture(self, chunks=chunks)
                with self.assertRaises(hc.ClaudeHostError) as cm:
                    self.go(fx=fx, transport=fx.transport())
                self.assertEqual(cm.exception.reason, "init-missing")
                self.assertTrue(fx.launcher.killed)

    def test_launcher_that_never_streams_gets_the_same_decision_on_the_bytes(self):
        class Silent(FakeLauncher):
            def launch(self, argv, stdin, *, cwd, wall_seconds, max_output_bytes, cancel, on_output=None):
                return super().launch(argv, stdin, cwd=cwd, wall_seconds=wall_seconds,
                                      max_output_bytes=max_output_bytes, cancel=cancel, on_output=None)

        fx = self.fx
        silent = Silent(fx.policy, fx.qualification, fx.host_qualification,
                        chunks=[b"".join(good_chunks(apiKeySource="ANTHROPIC_API_KEY"))])
        outcome = self.go(transport=fx.transport(backend=silent))
        self.assertEqual(self.state(outcome), "refused")
        self.assertNotIn("message", self.kinds(outcome))

    def test_the_real_macos_launch_signature_is_accepted_and_a_streamed_bad_init_stops_the_group(self):
        for label, chunks, state in (
                ("API key source", good_chunks(apiKeySource="ANTHROPIC_API_KEY"), "refused"),
                ("subscription", good_chunks(), "completed")):
            with self.subTest(label):
                fx = Fixture(self, chunks=chunks)
                backend = MacLaunchSignature(fx.launcher)
                self.assertIn("on_output", inspect.signature(mac.MacOSContainment.launch).parameters)
                outcome = self.go(fx=fx, transport=fx.transport(backend=backend))  # no live-init-unsupported
                self.assertEqual(self.state(outcome), state)
                self.assertEqual(fx.launcher.killed, state == "refused")
                if state == "refused":
                    self.assertNotIn("message", self.kinds(outcome))

    # --- executable pin, PATH, version ---

    def test_executable_hash_drift_missing_or_symlinked_never_launches(self):
        fx = self.fx
        fx.exe.write_bytes(FAKE_CLAUDE + b"tampered")
        self.refuses("executable-drift")
        fx.exe.unlink()
        self.refuses("executable-unavailable")
        target = fx.tmp / "real-claude"
        target.write_bytes(FAKE_CLAUDE)
        fx.exe.symlink_to(target)
        self.refuses("executable-unavailable")
        fx.policy.claude = "claude"
        self.refuses("executable-unavailable")
        self.assertEqual(fx.launcher.calls, [])

    def test_hash_is_checked_again_at_the_run_launch(self):
        original = self.fx.launcher.launch

        def tamper_after_version(argv, stdin, *, cwd, wall_seconds, max_output_bytes, cancel,
                                 on_output=None):
            result_ = original(argv, stdin, cwd=cwd, wall_seconds=wall_seconds,
                               max_output_bytes=max_output_bytes, cancel=cancel, on_output=on_output)
            if argv[1:] == ("--version",):
                self.fx.exe.write_bytes(FAKE_CLAUDE + b"swapped")
            return result_

        self.fx.launcher.launch = tamper_after_version
        self.refuses("executable-drift")
        self.assertEqual(self.fx.launcher.run_calls, [])

    def test_path_shadowing_cannot_replace_the_pinned_executable(self):
        shadow = self.fx.tmp / "shadow"
        shadow.mkdir()
        (shadow / "claude").write_bytes(b"#!/bin/sh\nexit 0\n")
        os.chmod(shadow / "claude", 0o755)
        with mock.patch.dict(os.environ, {"PATH": f"{shadow}{os.pathsep}{os.environ.get('PATH', '')}"}):
            self.assertEqual(self.state(self.go()), "completed")
        for call in self.fx.launcher.calls:
            self.assertEqual(call["argv"][0], str(self.fx.exe))
            self.assertNotEqual(call["argv"][0], str(shadow / "claude"))

    def test_version_drift_is_refused_before_launch_and_init_drift_fails_the_run(self):
        fx = Fixture(self, version_text="2.1.293 (Claude Code)")
        self.refuses("version-drift", fx=fx, transport=fx.transport())
        self.assertEqual(fx.launcher.run_calls, [])
        for text in ("garbage", "2.1.292 extra"):
            with self.subTest(text):
                fx = Fixture(self, version_text=text)
                with self.assertRaises(hc.ClaudeHostError):
                    self.go(fx=fx, transport=fx.transport())
                self.assertEqual(fx.launcher.run_calls, [])
        drifted = [line(init(claude_code_version="2.1.291 (Claude Code)")), line(result())]
        fx = Fixture(self, chunks=drifted)
        outcome = self.go(fx=fx, transport=fx.transport())
        self.assertEqual(self.state(outcome), "failed")

    # --- quota, cancellation, single attempt ---

    def test_quota_stop_refuses_before_the_session_launch(self):
        controls = {"weekly above stop": reading(weeklyPercent=81),
                    "extra usage": reading(extraUsageEnabled=True),
                    "stale": reading(observedAt="2026-11-01T11:00:00Z"),
                    "missing": False}
        for label, pre in controls.items():
            with self.subTest(label):
                fx = Fixture(self)
                transport = fx.transport(pre=pre) if pre is not False else tc.NativeClaudeTransport(
                    fx.launcher, workdir=fx.tmp, pre_reading=None, quota=("cohort", {
                        "unitsUsed": 0, "cohortWeeklyPercent": 0}), clock=lambda: CLOCK, environ={})
                self.refuses("quota-stop", fx=fx, transport=transport)
                self.assertEqual(fx.launcher.run_calls, [])
                self.assertFalse(transport.run_evidence[0]["quotaProceed"])
        fx = Fixture(self)
        transport = fx.transport(quota=("probe", 3))
        self.refuses("quota-stop", fx=fx, transport=transport)
        self.assertEqual(transport.run_evidence[0]["quotaReason"], "probe-session-cap-reached")
        fx = Fixture(self)
        self.refuses("quota-stop", fx=fx, transport=fx.transport(quota=("cohort", {"unitsUsed": 16,
                                                                                   "cohortWeeklyPercent": 0})))

    def test_invalid_quota_mode_is_refused_at_construction(self):
        with self.assertRaises(hc.ClaudeHostError) as cm:
            self.fx.transport(quota=("free", None))
        self.assertEqual(cm.exception.reason, "invalid-quota")

    def test_cancel_before_launch_starts_nothing(self):
        cancel = threading.Event()
        cancel.set()
        self.refuses("cancelled-before-launch", cancel=cancel)
        self.assertEqual(self.fx.launcher.calls, [])

    def test_cancel_during_the_run_reaches_the_launcher_and_is_interrupted(self):
        cancel = threading.Event()

        def trigger(stop):
            cancel.set()
            stop.wait(2)  # the relay must forward the caller's cancel to the launcher

        fx = Fixture(self, during=trigger)
        outcome = self.go(fx=fx, transport=fx.transport(), cancel=cancel)
        self.assertTrue(fx.launcher.killed)
        self.assertEqual(self.state(outcome), "interrupted")

    def test_launcher_refusal_surfaces_its_reason_and_a_second_attempt_is_refused(self):
        fx = Fixture(self, fail="self-check-allowed")  # the NC-11 F4 check failing inside launch
        transport = fx.transport()
        self.refuses("self-check-allowed", fx=fx, transport=transport)
        self.assertEqual(len(fx.launcher.run_calls), 1)
        self.refuses("attempt-exhausted", fx=fx, transport=transport)
        self.assertEqual(len(fx.launcher.run_calls), 1)  # no retry, no alternative route

    def test_second_attempt_after_success_is_refused_too(self):
        transport = self.fx.transport()
        self.assertEqual(self.state(self.go(transport=transport)), "completed")
        self.refuses("attempt-exhausted", transport=transport)
        self.assertEqual(len(self.fx.launcher.run_calls), 1)

    def test_tampered_plan_is_refused(self):
        transport = self.fx.transport()
        plan = hc.build_plan(hc.ClaudeRequest(SESSION), b"prompt")
        cancel, limits = threading.Event(), hc.HostLimits()
        for bad_plan, prompt in ((replace(plan, argv=("/bin/sh", *plan.argv[1:])), b"prompt"),
                                 (replace(plan, env_deny=()), b"prompt"),
                                 (plan, b"different prompt")):
            with self.assertRaises(hc.ClaudeHostError) as cm:
                tc.NativeClaudeTransport.run(self.fx.transport(), bad_plan, prompt, limits, cancel)
            self.assertEqual(cm.exception.reason, "invalid-launch-plan")
        self.assertEqual(transport.run_evidence, [])
        self.assertEqual(self.fx.launcher.calls, [])

    def test_module_starts_no_process_itself(self):
        source = Path(tc.__file__).read_text()
        for forbidden in ("subprocess", "Popen", "os.exec", "os.system", "os.spawn"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
