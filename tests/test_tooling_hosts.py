# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic, process-free tests for host command preparation and dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

from agent_braid.tooling_capture import (
    AttemptAdmission, MeasuredCosts, StopState, _sha256,
)
from agent_braid.tooling_hosts import (
    FilePin, HostLaunchConfig, HostPreparationError, HostSessionAdapter,
    LaunchEvidence, prepare_host_launch,
)
from agent_braid.tooling_supervisor import BudgetCaps


@dataclass
class Outcome:
    status: str = "refused"
    launched: bool = False
    returncode: int | None = None
    signal: int | None = None
    wall_elapsed_seconds: float = 0.0
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    last_snapshot: object | None = None


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _inputs(tmp_path: Path, **updates) -> tuple[AttemptAdmission, HostLaunchConfig]:
    exe = tmp_path / "fake-host"
    exe.write_bytes(b"synthetic executable bytes")
    exe.chmod(0o755)
    cfg_dir = tmp_path / "isolated-config"
    cfg_dir.mkdir()
    output = tmp_path / "out"
    output.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    admission = AttemptAdmission("attempt-123", "slot-123", tmp_path / "admission.json",
                                 "b" * 64, "a" * 64)
    evidence = LaunchEvidence("route-test", "c" * 64, "d" * 64, "e" * 64,
                              settings_support_attestation_sha256="f" * 64)
    config = HostLaunchConfig(
        host="codex", arm="mcp-only", executable=exe, executable_sha256=_sha(exe),
        version="0.162.0-alpha.2", model="registered-model", effort="medium",
        config_files=(), codex_config_overrides=(
            'mcp_servers.test = { command = "fake-mcp", args = [], enabled_tools = ["lookup"] }',
            "skills.config = []",
        ), config_dir=cfg_dir, cwd=work, output_root=output, source_roots=(work,),
        grant_root=tmp_path / "grants", prompt=b"synthetic prompt", environment={},
        mcp_servers=("test",), expected_tools=("lookup",), evidence=evidence,
    )
    return admission, config.__class__(**{**config.__dict__, **updates})


class AllowVerifier:
    def verify_pre_dispatch(self, *, admission, plan):
        if admission.attempt_id != plan.attempt_id:
            raise RuntimeError("admission mismatch")


class HostAdapterTests(unittest.TestCase):
    def with_temp(self):
        context = tempfile.TemporaryDirectory()
        self.addCleanup(context.cleanup)
        return Path(context.name)

    def test_prepare_binds_exact_inputs_without_putting_prompt_on_argv(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        plan = prepare_host_launch(admission, config)
        self.assertEqual(plan.attempt_id, admission.attempt_id)
        self.assertEqual(plan.prompt_sha256, hashlib.sha256(config.prompt).hexdigest())
        self.assertNotIn(config.prompt.decode(), plan.argv)
        self.assertEqual(plan.argv[0], "exec")
        self.assertIn("--ignore-user-config", plan.argv)
        self.assertIn("--sandbox", plan.argv)
        self.assertIn("read-only", plan.argv)
        self.assertIn("--config", plan.argv)
        self.assertEqual(plan.argv.count("--model"), 1)

    def test_refuses_human_unknown_route_and_missing_attestations(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        for changes in ({"arm": "cli"}, {"host": "unknown"}):
            candidate = config.__class__(**{**config.__dict__, **changes})
            with self.assertRaises(HostPreparationError):
                prepare_host_launch(admission, candidate)
        bad_evidence = config.evidence.__class__("", "c" * 64, "d" * 64, "e" * 64,
                                                 settings_support_attestation_sha256="f" * 64)
        with self.assertRaises(HostPreparationError):
            prepare_host_launch(admission, config.__class__(**{**config.__dict__, "evidence": bad_evidence}))
        no_support = config.evidence.__class__("route-test", "c" * 64, "d" * 64, "e" * 64)
        with self.assertRaises(HostPreparationError):
            prepare_host_launch(admission, config.__class__(**{**config.__dict__, "evidence": no_support}))

    def test_refuses_mcp_configuration_drift_and_inexact_toolset(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        with self.assertRaisesRegex(HostPreparationError, "inventory"):
            prepare_host_launch(admission, config.__class__(**{**config.__dict__, "mcp_servers": ("other",)}))
        with self.assertRaisesRegex(HostPreparationError, "toolset"):
            prepare_host_launch(admission, config.__class__(**{**config.__dict__, "expected_tools": ("wrong",)}))
        with self.assertRaisesRegex(HostPreparationError, "caller-supplied"):
            prepare_host_launch(admission, config.__class__(**{**config.__dict__, "codex_config_overrides": ()}))

    def test_binary_pin_is_rechecked_before_supervisor(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        plan = prepare_host_launch(admission, config)
        config.executable.write_bytes(b"changed after plan")
        requests = []

        class Request:
            def __init__(self, **kwargs):
                requests.append(kwargs)

        fake_supervisor = types.SimpleNamespace(ProcessRequest=Request, FilePin=FilePin)
        with mock.patch.dict(sys.modules, {"agent_braid.tooling_supervisor": fake_supervisor}):
            adapter = HostSessionAdapter(
                plan, verifier=AllowVerifier(), observer=lambda *_: None,
                caps=object(), supervisor=lambda *_: self.fail("must not dispatch"),
            )
            with self.assertRaisesRegex(HostPreparationError, "changed"):
                adapter.execute(admission)
        self.assertEqual(requests, [])

    def test_verifier_refusal_prevents_handoff_and_adapter_cannot_retry(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        plan = prepare_host_launch(admission, config)
        fake_supervisor = types.SimpleNamespace(ProcessRequest=lambda **kwargs: kwargs, FilePin=FilePin)
        calls = []

        class DenyVerifier:
            def verify_pre_dispatch(self, **kwargs):
                raise RuntimeError("external route attestation denied")

        with mock.patch.dict(sys.modules, {"agent_braid.tooling_supervisor": fake_supervisor}):
            adapter = HostSessionAdapter(plan, verifier=DenyVerifier(), observer=lambda *_: None,
                                         caps=object(), supervisor=lambda *args: calls.append(args))
            with self.assertRaisesRegex(RuntimeError, "denied"):
                adapter.execute(admission)
            with self.assertRaisesRegex(HostPreparationError, "one-shot"):
                adapter.execute(admission)
        self.assertEqual(calls, [])

    def test_adapter_handoff_omits_prompt_and_environment_secrets_from_outcome(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path, environment={"TEST_SECRET": "never-receipt"})
        plan = prepare_host_launch(admission, config)
        fake_supervisor = types.SimpleNamespace(ProcessRequest=lambda **kwargs: kwargs, FilePin=FilePin)
        requests = []
        def supervisor(request, caps, observer):
            requests.append(request)
            return Outcome()
        with mock.patch.dict(sys.modules, {"agent_braid.tooling_supervisor": fake_supervisor}):
            adapter = HostSessionAdapter(plan, verifier=AllowVerifier(), observer=lambda *_: None,
                                         caps=object(), supervisor=supervisor)
            result = adapter.execute(admission)
        self.assertEqual(requests[0]["stdin"], b"synthetic prompt")
        self.assertEqual(requests[0]["env"]["TEST_SECRET"], "never-receipt")
        serialized = repr(result)
        self.assertNotIn("synthetic prompt", serialized)
        self.assertNotIn("never-receipt", serialized)
        self.assertEqual(result["promptSha256"], plan.prompt_sha256)

    def test_claude_requires_exact_mcp_json_isolated_config_and_stable_version(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        executable = tmp_path / "claude"
        executable.write_bytes(b"synthetic claude")
        executable.chmod(0o755)
        config_file = tmp_path / "mcp.json"
        config_file.write_text('{"mcpServers":{"test":{"command":"fake-mcp","args":[]}}}')
        pin = FilePin(config_file, _sha(config_file))
        evidence = LaunchEvidence("claude-route", "1" * 64, "2" * 64, "3" * 64,
                                  settings_support_attestation_sha256="4" * 64)
        config = base.__class__(**{
            **base.__dict__, "host": "claude-code", "executable": executable,
            "executable_sha256": _sha(executable), "version": "2.1.294",
            "config_files": (pin,), "codex_config_overrides": (),
            "environment": {"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            "expected_tools": (), "evidence": evidence,
        })
        plan = prepare_host_launch(admission, config)
        self.assertIn("--strict-mcp-config", plan.argv)
        self.assertIn("--mcp-config", plan.argv)
        self.assertIn(str(config_file), plan.argv)
        self.assertIn("--no-session-persistence", plan.argv)
        self.assertIn("--disable-slash-commands", plan.argv)
        self.assertNotIn(config.prompt.decode(), plan.argv)
        old = config.__class__(**{**config.__dict__, "version": "2.1.285"})
        with self.assertRaisesRegex(HostPreparationError, "before 2.1.286"):
            prepare_host_launch(admission, old)
        prerelease = config.__class__(**{**config.__dict__, "version": "2.1.286-alpha"})
        with self.assertRaisesRegex(HostPreparationError, "prerelease"):
            prepare_host_launch(admission, prerelease)

    def test_codex_skills_arm_requires_exact_native_inventory_and_pinned_files(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        skills_root = tmp_path / "skills"
        pins = []
        entries = []
        for name in (
            "agent-braid-analyze", "agent-braid-plan", "agent-braid-execute",
            "agent-braid-recover", "agent-braid-evidence",
        ):
            directory = skills_root / name
            directory.mkdir(parents=True)
            file = directory / "SKILL.md"
            file.write_text("synthetic skill\n")
            pins.append(FilePin(file, _sha(file)))
            entries.append(f'{{name="{name}",path="{directory}",enabled=true}}')
        config = base.__class__(**{
            **base.__dict__, "arm": "mcp-plus-skills", "config_files": tuple(pins),
            "expected_skill_bundle_sha256": "a" * 64,
            "codex_config_overrides": (
                'mcp_servers.test = { command = "fake-mcp", args = [], enabled_tools = ["lookup"] }',
                "skills.config = [" + ",".join(entries) + "]",
            ),
            "evidence": LaunchEvidence("route-test", "c" * 64, "d" * 64, "e" * 64,
                                       native_skills_attestation_sha256="9" * 64,
                                       settings_support_attestation_sha256="f" * 64),
        })
        plan = prepare_host_launch(admission, config)
        self.assertEqual(plan.arm, "mcp-plus-skills")
        self.assertTrue(any("skills.config" in arg for arg in plan.argv))
        self.assertTrue(plan.codex_config_sha256)

    def test_codex_credential_channels_are_refused_before_argv_construction(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        dangerous = config.__class__(**{
            **config.__dict__, "codex_config_overrides": (
                'mcp_servers.test = { command="mcp", args=[], enabled_tools=["lookup"], '
                'env={AWS_ACCESS_KEY_ID="sensitive"} }',
                "skills.config = []",
            ),
        })
        with self.assertRaisesRegex(HostPreparationError, "credential"):
            prepare_host_launch(admission, dangerous)
        argument_secret = config.__class__(**{
            **config.__dict__, "codex_config_overrides": (
                'mcp_servers.test = { command="mcp", args=["--api-key", "SECRET_SENTINEL"], '
                'enabled_tools=["lookup"] }',
                "skills.config = []",
            ),
        })
        with self.assertRaisesRegex(HostPreparationError, "credentials"):
            prepare_host_launch(admission, argument_secret)
        for arguments in (
            '["--api-key", "SECRET_SENTINEL"]',
            '["--api-key=SECRET_SENTINEL"]',
            '["--credential-wrapper", "TOKEN_SENTINEL"]',
            '["--wrapper", "opaque-credential-value"]',
        ):
            candidate = config.__class__(**{
                **config.__dict__, "codex_config_overrides": (
                    'mcp_servers.test = { command="mcp", args=' + arguments + ', '
                    'enabled_tools=["lookup"] }',
                    "skills.config = []",
                ),
            })
            with self.assertRaises(HostPreparationError):
                prepare_host_launch(admission, candidate)
        opaque = config.__class__(**{
            **config.__dict__, "codex_config_overrides": (
                'mcp_servers.test = { command="opaque-sentinel", args=[], '
                'enabled_tools=["lookup"] }',
                "skills.config = []",
            ),
        })
        safe_plan = prepare_host_launch(admission, opaque)
        self.assertNotIn("opaque-sentinel", repr(safe_plan))

    def test_real_supervisor_composes_with_fake_host_executable_only(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        script = tmp_path / "fake-codex"
        script.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '{\"type\":\"thread.started\"}' '{\"type\":\"turn.started\"}' "
            "'{\"type\":\"item.completed\",\"item\":{\"type\":\"mcp_tool_call\",\"server\":\"test\",\"tool\":\"lookup\"}}' "
            "'{\"type\":\"turn.completed\",\"usage\":{\"input_tokens\":3,\"output_tokens\":2}}'\n"
        )
        script.chmod(0o755)
        work = base.cwd
        source = tmp_path / "source"
        source.mkdir(mode=0o700)
        out = base.output_root
        work.chmod(0o700)
        out.chmod(0o700)
        config = base.__class__(**{
            **base.__dict__, "executable": script, "executable_sha256": _sha(script),
            "cwd": work, "source_roots": (source,), "timeout_seconds": 5,
            "poll_interval_seconds": 0.05, "observation_max_age_seconds": 5,
            "term_grace_seconds": 0.1, "kill_grace_seconds": 0.1,
        })
        plan = prepare_host_launch(admission, config)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        values = {"eur": 0.0, "tokens": 0, "input_tokens": 0, "output_tokens": 0,
                  "retry_tokens": 0, "wall_seconds": 0.1, "rss_bytes": 0, "disk_bytes": 0}
        def observer(identity, elapsed):
            measured = MeasuredCosts(values, "synthetic measurement", _sha256(b"synthetic"), now)
            stopped = StopState(False, False, 0, "synthetic stop monitor",
                                _sha256(b"synthetic-stop"), now)
            from agent_braid.tooling_supervisor import TelemetrySnapshot
            return TelemetrySnapshot(measured, stopped)
        adapter = HostSessionAdapter(
            plan, verifier=AllowVerifier(), observer=observer,
            caps=BudgetCaps(25.0, 4_000_000, 30.0, 4 * 1024**3, 5 * 1024**3),
        )
        result = adapter.execute(admission)
        self.assertEqual(result["status"], "completed")
        self.assertIs(result["launched"], True)
        self.assertEqual(result["observation"]["state"], "completed")
        self.assertEqual(result["observation"]["observedTools"], ["test/lookup"])
        self.assertIsNone(result["observation"]["estimatedCostUsd"])
        self.assertTrue(Path(result["supervisorReceiptPath"]).is_file())

    def test_real_supervisor_refuses_config_mutation_after_fresh_observation(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        config_file = tmp_path / "claude-mcp.json"
        config_file.write_text('{"mcpServers":{"test":{"command":"fake-mcp","args":[]}}}')
        executable = tmp_path / "fake-claude"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        source = tmp_path / "source"
        source.mkdir(mode=0o700)
        base.cwd.chmod(0o700)
        base.output_root.chmod(0o700)
        config = base.__class__(**{
            **base.__dict__, "host": "claude-code", "arm": "mcp-only",
            "executable": executable, "executable_sha256": _sha(executable),
            "version": "2.1.294", "config_files": (FilePin(config_file, _sha(config_file)),),
            "codex_config_overrides": (), "environment": {"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            "expected_tools": (), "source_roots": (source,),
            "poll_interval_seconds": 0.05, "observation_max_age_seconds": 5,
            "term_grace_seconds": 0.1, "kill_grace_seconds": 0.1,
        })
        plan = prepare_host_launch(admission, config)
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        values = {"eur": 0.0, "tokens": 0, "input_tokens": 0, "output_tokens": 0,
                  "retry_tokens": 0, "wall_seconds": 0.1, "rss_bytes": 0, "disk_bytes": 0}
        def observer(identity, elapsed):
            if identity is None:
                config_file.write_text('{"mcpServers":{}}')
            measured = MeasuredCosts(values, "synthetic measurement", _sha256(b"synthetic"), now)
            stopped = StopState(False, False, 0, "synthetic stop monitor",
                                _sha256(b"synthetic-stop"), now)
            from agent_braid.tooling_supervisor import TelemetrySnapshot
            return TelemetrySnapshot(measured, stopped)
        adapter = HostSessionAdapter(
            plan, verifier=AllowVerifier(), observer=observer,
            caps=BudgetCaps(25.0, 4_000_000, 30.0, 4 * 1024**3, 5 * 1024**3),
        )
        result = adapter.execute(admission)
        self.assertEqual(result["status"], "start-drift")
        self.assertIs(result["launched"], False)
        self.assertEqual(result["observation"]["state"], "unknown")

    def test_uncompleted_supervisor_never_uses_host_stream_to_claim_completion(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        plan = prepare_host_launch(admission, config)
        fake_supervisor = types.SimpleNamespace(ProcessRequest=lambda **kwargs: kwargs, FilePin=FilePin)
        raw = (b'{"type":"thread.started"}\n{"type":"turn.started"}\n'
               b'{"type":"turn.completed","usage":{}}\n')
        outcome = Outcome(status="measurement-unknown", launched=True, returncode=None)
        with mock.patch.dict(sys.modules, {"agent_braid.tooling_supervisor": fake_supervisor}):
            adapter = HostSessionAdapter(
                plan, verifier=AllowVerifier(), observer=lambda *_: None, caps=object(),
                supervisor=lambda *_: outcome, outcome_reader=lambda _outcome: raw,
            )
            result = adapter.execute(admission)
        self.assertEqual(result["observation"]["state"], "unknown")


if __name__ == "__main__":
    unittest.main()
