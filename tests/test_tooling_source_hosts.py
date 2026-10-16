# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic launch-store controls without host or provider execution."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from agent_braid import tooling_hosts as hosts
from agent_braid import tooling_subscription as subscription
from agent_braid import tooling_registration_v6 as v6
from agent_braid import tooling_claude_sources as claude
from tests.test_tooling_claude_sources import fixture
from tests.test_tooling_hosts import _inputs, _sha, AllowVerifier, Outcome


class SourceHostTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        admission, base = _inputs(self.root)
        server = tomllib.loads(base.codex_config_overrides[0])["mcp_servers"]["test"]
        mcp = self.root / "mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"test": {key: server[key] for key in ("command", "args")}}}))
        settings = self.root / "settings.json"
        settings.write_text(json.dumps({"forceLoginMethod": "claudeai", "fastMode": False,
                                       "disableAllHooks": True, "autoMemoryEnabled": False}))
        model = {"kind": "requested-route", "selector": base.model, "effort": base.effort,
                 "effectiveConfig": {"selector": base.model, "effort": base.effort},
                 "cliBuild": {"version": "2.1.294", "sha256": base.executable_sha256}}
        self.config = replace(base, host="claude-code", version="2.1.294",
            config_files=(hosts.FilePin(mcp, _sha(mcp)), *base.config_files),
            codex_config_overrides=(), expected_tools=(),
            claude_subscription_settings=hosts.FilePin(settings, _sha(settings)),
            environment={"CLAUDE_CONFIG_DIR": str(base.config_dir)},
            host_build_sha256=base.executable_sha256, candidate_artifact_sha256="a" * 64,
            model_identity=model, claude_keychain_suffix="0a1b2c3d")
        pins = (*self.config.config_files, self.config.claude_subscription_settings)
        contract, _, _ = fixture()
        core = subscription.operational_binding_from_dict(contract["binding"])
        core = replace(core, slot_id=admission.slot_id,
            host_build_sha256=self.config.host_build_sha256,
            candidate_artifact_sha256=self.config.candidate_artifact_sha256,
            executable_sha256=self.config.executable_sha256,
            config_sha256=hosts._host_config_digest(pins),
            argv_sha256=hosts._host_argv_digest(hosts._build_argv(self.config)),
            model_identity_sha256=hosts._canonical_digest(model))
        contract["binding"] = core.as_dict()
        store = {"canonicalConfigDirSha256": hashlib.sha256(str(base.config_dir).encode()).hexdigest(),
                 "keychainSuffix": self.config.claude_keychain_suffix}
        self.binding = v6.SourceRouteBinding(core, claude.source_contract_sha256(contract),
            v6._canonical(contract), v6._canonical(store))
        self.admission = replace(admission, subscription_binding=self.binding)

    def test_frozen_store_and_explicit_source_verifier_reach_supervisor(self):
        plan = hosts.prepare_host_launch(self.admission, self.config)
        self.assertEqual(self.binding, plan.source_route_binding)
        self.assertNotIn("--bare", plan.argv)
        self.assertIn("--restricted", plan.argv)
        with self.assertRaises(hosts.HostPreparationError):
            hosts.HostSessionAdapter(plan, verifier=AllowVerifier(), observer=lambda *_: None,
                                     caps=object())
        calls = []

        class SourceVerifier:
            def verify_source_observation(self, *args, **kwargs):
                pass  # Test-only handoff; not an authentic verifier.

        def supervisor(request, caps, observer, *, source_route_verifier):
            calls.append((request, source_route_verifier))
            return Outcome()

        verifier = SourceVerifier()
        adapter = hosts.HostSessionAdapter(plan, verifier=AllowVerifier(), observer=lambda *_: None,
            caps=object(), source_route_verifier=verifier, supervisor=supervisor)
        adapter.execute(self.admission)
        request, received = calls[0]
        self.assertIs(verifier, received)
        self.assertEqual(self.binding, request.source_route_binding)
        self.assertIsNone(request.operational_route_binding)

    def test_directory_alias_suffix_and_frozen_path_drift_refuse(self):
        alias = self.root / "alias"
        alias.symlink_to(self.config.config_dir, target_is_directory=True)
        alternate = self.root / "alternate"
        alternate.mkdir()
        for changes in (
                {"config_dir": alias, "environment": {"CLAUDE_CONFIG_DIR": str(alias)}},
                {"claude_keychain_suffix": "ffffffff"},
                {"config_dir": alternate, "environment": {"CLAUDE_CONFIG_DIR": str(alternate)}}):
            with self.subTest(changes=tuple(changes)), self.assertRaises(hosts.HostPreparationError):
                hosts.prepare_host_launch(self.admission, replace(self.config, **changes))

    def test_directory_replaced_after_preparation_cannot_dispatch(self):
        plan = hosts.prepare_host_launch(self.admission, self.config)
        old = self.root / "old"
        self.config.config_dir.rename(old)
        self.config.config_dir.symlink_to(old, target_is_directory=True)
        calls = []

        class SourceVerifier:
            def verify_source_observation(self, *args, **kwargs):
                pass

        adapter = hosts.HostSessionAdapter(plan, verifier=AllowVerifier(), observer=lambda *_: None,
            caps=object(), source_route_verifier=SourceVerifier(),
            supervisor=lambda *args, **kwargs: calls.append(args) or Outcome())
        with self.assertRaises(hosts.HostPreparationError):
            adapter.execute(self.admission)
        self.assertFalse(calls)
