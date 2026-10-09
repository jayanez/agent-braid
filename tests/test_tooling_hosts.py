# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic, process-free tests for host command preparation and dispatch."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
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
from agent_braid.tooling_subscription import SubscriptionBinding
from agent_braid.tooling_mcp import ToolingConfig, ToolingError


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
    source = tmp_path / "source"
    source.mkdir(mode=0o700)
    mcp_results = tmp_path / "mcp-results"
    mcp_results.mkdir(mode=0o700)
    mcp_executable = tmp_path / "agent-braid-mcp"
    mcp_executable.write_bytes(b"synthetic Agent Braid console executable")
    mcp_executable.chmod(0o755)
    mcp_args = ["-m", "agent_braid", "tooling", "serve", "--source-root", str(source),
                "--result-root", str(mcp_results)]
    args_toml = ", ".join(json.dumps(arg) for arg in mcp_args)
    admission = AttemptAdmission("attempt-123", "slot-123", tmp_path / "admission.json",
                                 "b" * 64, "a" * 64)
    evidence = LaunchEvidence("route-test", "c" * 64, "d" * 64, "e" * 64,
                              settings_support_attestation_sha256="f" * 64)
    config = HostLaunchConfig(
        host="codex", arm="mcp-only", executable=exe, executable_sha256=_sha(exe),
        version="0.162.0-alpha.2", model="registered-model", effort="medium",
        config_files=(FilePin(mcp_executable, _sha(mcp_executable)),), codex_config_overrides=(
            f'mcp_servers.test = {{ command = {json.dumps(str(mcp_executable))}, '
            f'args = [{args_toml}], enabled_tools = ["lookup"] }}',
            "skills.config = []",
        ), config_dir=cfg_dir, cwd=work, mcp_result_root=mcp_results,
        output_root=output, source_roots=(source,),
        grant_root=tmp_path / "grants", prompt=b"synthetic prompt", environment={},
        mcp_servers=("test",), expected_tools=("lookup",), runtime_enabled=False,
        evidence=evidence,
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

    def test_subscription_binding_reaches_supervisor_and_rejects_paid_routes(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        binding = SubscriptionBinding("codex", "1" * 64, admission.slot_id, "2" * 64, "3" * 64)
        admission = admission.__class__(**{**admission.__dict__, "subscription_binding": binding})
        plan = prepare_host_launch(admission, config)
        request = HostSessionAdapter._make_process_request(plan)
        self.assertEqual(request.subscription_binding, binding)
        for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL",
                    "HTTP_PROXY", "CLAUDE_CODE_USE_BEDROCK", "LD_PRELOAD"):
            with self.subTest(key=key):
                changed = config.__class__(**{**config.__dict__, "environment": {key: "synthetic"}})
                with self.assertRaisesRegex(HostPreparationError, "unapproved override"):
                    prepare_host_launch(admission, changed)

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

    def test_accepts_only_registered_runtime_and_grant_store_arguments(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        grant_store = tmp_path / "grants"
        grant_store.mkdir(mode=0o700)
        args = ["-m", "agent_braid", "tooling", "serve", "--source-root",
                str(config.source_roots[0]), "--result-root", str(config.mcp_result_root),
                "--enable-runtime", "--grant-store", str(grant_store)]
        args_toml = ", ".join(json.dumps(arg) for arg in args)
        override = config.__class__(**{
            **config.__dict__, "runtime_enabled": True, "grant_root": grant_store,
            "codex_config_overrides": (
                f'mcp_servers.test = {{ command = {json.dumps(str(config.config_files[0].path))}, '
                f'args = [{args_toml}], enabled_tools = ["lookup"] }}',
                "skills.config = []",
            ),
        })
        plan = prepare_host_launch(admission, override)
        self.assertTrue(plan.runtime_enabled)
        self.assertIn("--enable-runtime", plan.codex_config_overrides[0])

    def test_refuses_nested_result_and_grant_roots(self):
        tmp_path = self.with_temp()
        admission, config = _inputs(tmp_path)
        nested_result = config.source_roots[0] / "results"
        nested_result.mkdir(mode=0o700)
        nested_overrides = tuple(
            override.replace(json.dumps(str(config.mcp_result_root)), json.dumps(str(nested_result)))
            for override in config.codex_config_overrides
        )
        nested = config.__class__(**{
            **config.__dict__, "mcp_result_root": nested_result,
            "codex_config_overrides": nested_overrides,
        })
        with self.assertRaisesRegex(HostPreparationError, "overlaps"):
            prepare_host_launch(admission, nested)
        with self.assertRaisesRegex(ToolingError, "disjoint"):
            ToolingConfig(config.source_roots[0], nested_result)

        result_parent = tmp_path / "result-container"
        nested_source = result_parent / "source"
        nested_source.mkdir(parents=True, mode=0o700)
        result_parent.chmod(0o700)
        ancestor_result = config.__class__(**{
            **config.__dict__, "source_roots": (nested_source,),
            "mcp_result_root": result_parent,
            "codex_config_overrides": tuple(
                override.replace(json.dumps(str(config.source_roots[0])), json.dumps(str(nested_source)))
                       .replace(json.dumps(str(config.mcp_result_root)), json.dumps(str(result_parent)))
                for override in config.codex_config_overrides),
        })
        with self.assertRaisesRegex(HostPreparationError, "overlaps"):
            prepare_host_launch(admission, ancestor_result)
        with self.assertRaisesRegex(ToolingError, "disjoint"):
            ToolingConfig(nested_source, result_parent)

        nested_grant = config.source_roots[0] / "grants"
        nested_grant.mkdir(mode=0o700)
        args = tomllib.loads(config.codex_config_overrides[0])["mcp_servers"]["test"]["args"]
        args.extend(("--enable-runtime", "--grant-store", str(nested_grant)))
        args_toml = ", ".join(json.dumps(arg) for arg in args)
        server = tomllib.loads(config.codex_config_overrides[0])["mcp_servers"]["test"]
        grant_override = config.__class__(**{
            **config.__dict__, "runtime_enabled": True, "grant_root": nested_grant,
            "codex_config_overrides": (
                f'mcp_servers.test = {{ command = {json.dumps(server["command"])}, '
                f'args = [{args_toml}], enabled_tools = ["lookup"] }}',
                "skills.config = []",
            ),
        })
        with self.assertRaisesRegex(HostPreparationError, "overlaps"):
            prepare_host_launch(admission, grant_override)
        with self.assertRaisesRegex(ToolingError, "Grant store"):
            ToolingConfig(config.source_roots[0], config.mcp_result_root,
                          grant_store=nested_grant, runtime_enabled=True)

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
        server = tomllib.loads(base.codex_config_overrides[0])["mcp_servers"]["test"]
        server = {key: server[key] for key in ("command", "args")}
        config_file.write_text(json.dumps({"mcpServers": {"test": server}}))
        pin = FilePin(config_file, _sha(config_file))
        evidence = LaunchEvidence("claude-route", "1" * 64, "2" * 64, "3" * 64,
                                  settings_support_attestation_sha256="4" * 64)
        config = base.__class__(**{
            **base.__dict__, "host": "claude-code", "executable": executable,
            "executable_sha256": _sha(executable), "version": "2.1.294",
            "config_files": (pin, *base.config_files), "codex_config_overrides": (),
            "environment": {"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            "expected_tools": (), "evidence": evidence,
        })
        plan = prepare_host_launch(admission, config)
        self.assertIn("--bare", plan.argv)
        self.assertIn("--strict-mcp-config", plan.argv)
        self.assertIn("--mcp-config", plan.argv)
        self.assertIn(str(config_file.resolve()), plan.argv)
        self.assertIn("--no-session-persistence", plan.argv)
        self.assertIn("--disable-slash-commands", plan.argv)
        self.assertNotIn(config.prompt.decode(), plan.argv)
        old = config.__class__(**{**config.__dict__, "version": "2.1.285"})
        with self.assertRaisesRegex(HostPreparationError, "before 2.1.286"):
            prepare_host_launch(admission, old)
        prerelease = config.__class__(**{**config.__dict__, "version": "2.1.286-alpha"})
        with self.assertRaisesRegex(HostPreparationError, "prerelease"):
            prepare_host_launch(admission, prerelease)

    def test_subscription_claude_uses_pinned_first_party_settings_and_reaches_supervisor(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        executable = tmp_path / "claude"
        executable.write_bytes(b"synthetic claude")
        executable.chmod(0o755)
        real_inputs = tmp_path / "claude-inputs"
        real_inputs.mkdir()
        input_link = tmp_path / "claude-input-link"
        input_link.symlink_to(real_inputs, target_is_directory=True)
        mcp_file = input_link / "mcp.json"
        server = tomllib.loads(base.codex_config_overrides[0])["mcp_servers"]["test"]
        mcp_file.write_text(json.dumps({"mcpServers": {"test": {
            "command": server["command"], "args": server["args"]
        }}}))
        mcp_pin = FilePin(mcp_file, _sha(mcp_file))
        settings_file = input_link / "claude-settings.json"
        settings_file.write_text(json.dumps({
            "forceLoginMethod": "claudeai", "fastMode": False,
            "disableAllHooks": True, "autoMemoryEnabled": False,
        }))
        settings_pin = FilePin(settings_file, _sha(settings_file))
        binding = SubscriptionBinding("claude-code", "1" * 64, admission.slot_id,
                                      "2" * 64, "3" * 64)
        admission = admission.__class__(**{**admission.__dict__, "subscription_binding": binding})
        config = base.__class__(**{
            **base.__dict__, "host": "claude-code", "executable": executable,
            "executable_sha256": _sha(executable), "version": "2.1.286",
            "config_files": (mcp_pin, *base.config_files), "codex_config_overrides": (),
            "environment": {"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            "expected_tools": (), "claude_subscription_settings": settings_pin,
            "evidence": LaunchEvidence("claude-subscription", "4" * 64, "5" * 64,
                                        "6" * 64, settings_support_attestation_sha256="7" * 64),
        })
        plan = prepare_host_launch(admission, config)
        self.assertNotIn("--bare", plan.argv)
        self.assertIn("--restricted", plan.argv)
        self.assertIn("--setting-sources", plan.argv)
        self.assertEqual(plan.argv[plan.argv.index("--setting-sources") + 1], "")
        self.assertEqual(plan.argv[plan.argv.index("--settings") + 1],
                         str((real_inputs / "claude-settings.json").resolve()))
        self.assertIn("--strict-mcp-config", plan.argv)
        self.assertIn("--tools", plan.argv)
        self.assertEqual(plan.claude_subscription_settings.sha256, settings_pin.sha256)
        self.assertIn(FilePin((real_inputs / "claude-settings.json").resolve(), settings_pin.sha256),
                      plan.config_files)
        self.assertNotIn(settings_file.read_text(), repr(config))
        self.assertNotIn(settings_file.read_text(), repr(plan))

        requests = []
        fake_supervisor = types.SimpleNamespace(ProcessRequest=lambda **kwargs: kwargs, FilePin=FilePin)
        class RecordingVerifier:
            def verify_pre_dispatch(self, *, admission, plan):
                self.admission = admission
                self.plan = plan
        verifier = RecordingVerifier()
        with mock.patch.dict(sys.modules, {"agent_braid.tooling_supervisor": fake_supervisor}):
            adapter = HostSessionAdapter(
                plan, verifier=verifier, observer=lambda *_: None, caps=object(),
                supervisor=lambda request, *_: (requests.append(request) or Outcome()),
            )
            adapter.execute(admission)
        self.assertIs(verifier.admission, admission)
        self.assertEqual(verifier.plan.subscription_binding, binding)
        self.assertEqual(requests[0]["subscription_binding"], binding)
        self.assertTrue(any(pin.path == (real_inputs / "claude-settings.json").resolve()
                            for pin in requests[0]["file_pins"]))

        skill_names = ("agent-braid-analyze", "agent-braid-plan", "agent-braid-execute",
                       "agent-braid-recover", "agent-braid-evidence")
        skills_config = config.__class__(**{
            **config.__dict__, "arm": "mcp-plus-skills",
            "expected_tools": tuple(f"Skill({name})" for name in skill_names),
            "expected_skill_bundle_sha256": "8" * 64,
            "evidence": LaunchEvidence("claude-subscription", "4" * 64, "5" * 64,
                                        "6" * 64, native_skills_attestation_sha256="9" * 64,
                                        settings_support_attestation_sha256="7" * 64),
        })
        skills_plan = prepare_host_launch(admission, skills_config)
        self.assertNotIn("--bare", skills_plan.argv)
        self.assertEqual(skills_plan.argv[skills_plan.argv.index("--tools") + 1],
                         ",".join(skills_config.expected_tools))
        self.assertNotIn("--disable-slash-commands", skills_plan.argv)

        decoy_inputs = tmp_path / "decoy-inputs"
        decoy_inputs.mkdir()
        (decoy_inputs / "mcp.json").write_text('{"mcpServers":{}}')
        (decoy_inputs / "claude-settings.json").write_text('{"apiKey":"DECOY"}')
        input_link.unlink()
        input_link.symlink_to(decoy_inputs, target_is_directory=True)
        self.assertEqual(plan.argv[plan.argv.index("--settings") + 1],
                         str((real_inputs / "claude-settings.json").resolve()))
        HostSessionAdapter._verify_pins(plan)

    def test_subscription_claude_refuses_missing_malformed_drifted_and_poison_settings(self):
        tmp_path = self.with_temp()
        admission, base = _inputs(tmp_path)
        executable = tmp_path / "claude"
        executable.write_bytes(b"synthetic claude")
        executable.chmod(0o755)
        mcp_file = tmp_path / "mcp.json"
        server = tomllib.loads(base.codex_config_overrides[0])["mcp_servers"]["test"]
        mcp_file.write_text(json.dumps({"mcpServers": {"test": {
            "command": server["command"], "args": server["args"]
        }}}))
        binding = SubscriptionBinding("claude-code", "1" * 64, admission.slot_id,
                                      "2" * 64, "3" * 64)
        admission = admission.__class__(**{**admission.__dict__, "subscription_binding": binding})
        evidence = LaunchEvidence("claude-subscription", "4" * 64, "5" * 64,
                                  "6" * 64, settings_support_attestation_sha256="7" * 64)
        base_values = {
            **base.__dict__, "host": "claude-code", "executable": executable,
            "executable_sha256": _sha(executable), "version": "2.1.286",
            "config_files": (FilePin(mcp_file, _sha(mcp_file)), *base.config_files),
            "codex_config_overrides": (),
            "environment": {"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            "expected_tools": (), "evidence": evidence,
        }
        with self.assertRaisesRegex(HostPreparationError, "requires pinned"):
            prepare_host_launch(admission, base.__class__(**base_values))
        fifo_path = tmp_path / "claude-settings.fifo"
        os.mkfifo(fifo_path)
        for non_regular in (fifo_path, tmp_path):
            candidate = base.__class__(**{
                **base_values,
                "claude_subscription_settings": FilePin(non_regular, "a" * 64),
            })
            with self.subTest(path=non_regular), self.assertRaisesRegex(
                    HostPreparationError, "regular file"):
                prepare_host_launch(admission, candidate)
        settings_file = tmp_path / "claude-settings.json"
        approved = {"forceLoginMethod": "claudeai", "fastMode": False,
                    "disableAllHooks": True, "autoMemoryEnabled": False}
        for poison in (
            {**approved, "fastMode": True},
            {**approved, "fastMode": 0},
            {**approved, "disableAllHooks": 1},
            {**approved, "autoMemoryEnabled": 0},
            {**approved, "forceLoginMethod": "console"},
            {**approved, "apiKey": "SECRET_SENTINEL"},
            {**approved, "env": {"ANTHROPIC_API_KEY": "SECRET_SENTINEL"}},
            {**approved, "apiKeyHelper": "secret-helper"},
        ):
            settings_file.write_text(json.dumps(poison))
            candidate = base.__class__(**{
                **base_values, "claude_subscription_settings": FilePin(settings_file, _sha(settings_file)),
            })
            with self.assertRaises(HostPreparationError):
                prepare_host_launch(admission, candidate)
        settings_file.write_text(
            '{"forceLoginMethod":"claudeai","fastMode":false,"fastMode":true,'
            '"disableAllHooks":true,"autoMemoryEnabled":false}'
        )
        duplicate = base.__class__(**{
            **base_values, "claude_subscription_settings": FilePin(settings_file, _sha(settings_file)),
        })
        with self.assertRaisesRegex(HostPreparationError, "duplicate JSON"):
            prepare_host_launch(admission, duplicate)
        settings_file.write_bytes(b" " * (16 * 1024 + 1))
        oversized = base.__class__(**{
            **base_values, "claude_subscription_settings": FilePin(settings_file, _sha(settings_file)),
        })
        with self.assertRaisesRegex(HostPreparationError, "16 KiB"):
            prepare_host_launch(admission, oversized)
        settings_file.write_text(json.dumps(approved))
        pin = FilePin(settings_file, _sha(settings_file))
        candidate = base.__class__(**{**base_values, "claude_subscription_settings": pin})
        plan = prepare_host_launch(admission, candidate)
        settings_file.write_text(json.dumps({**approved, "fastMode": True}))
        with self.assertRaisesRegex(HostPreparationError, "changed"):
            HostSessionAdapter._verify_pins(plan)
        settings_file.write_bytes(b" " * (16 * 1024 + 1))
        with self.assertRaisesRegex(HostPreparationError, "16 KiB"):
            HostSessionAdapter._verify_pins(plan)

        settings_file.write_text(json.dumps(approved))
        with self.assertRaisesRegex(HostPreparationError, "unapproved override"):
            prepare_host_launch(admission, candidate.__class__(**{
                **candidate.__dict__, "environment": {
                    "CLAUDE_CONFIG_DIR": str(base.config_dir), "ANTHROPIC_API_KEY": "SECRET_SENTINEL",
                },
            }))

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
            **base.__dict__, "arm": "mcp-plus-skills",
            "config_files": (*base.config_files, *pins),
            "expected_skill_bundle_sha256": "a" * 64,
            "codex_config_overrides": (
                base.codex_config_overrides[0],
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
        safe_plan = prepare_host_launch(admission, config)
        self.assertNotIn(config.codex_config_overrides[0], repr(config))
        self.assertNotIn(config.codex_config_overrides[0], repr(safe_plan))

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
        server = tomllib.loads(base.codex_config_overrides[0])["mcp_servers"]["test"]
        server = {key: server[key] for key in ("command", "args")}
        config_file.write_text(json.dumps({"mcpServers": {"test": server}}))
        executable = tmp_path / "fake-claude"
        executable.write_text("#!/bin/sh\nexit 0\n")
        executable.chmod(0o755)
        source = tmp_path / "source"
        base.cwd.chmod(0o700)
        base.output_root.chmod(0o700)
        config = base.__class__(**{
            **base.__dict__, "host": "claude-code", "arm": "mcp-only",
            "executable": executable, "executable_sha256": _sha(executable),
            "version": "2.1.294", "config_files": (FilePin(config_file, _sha(config_file)), *base.config_files),
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
