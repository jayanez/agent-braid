# SPDX-License-Identifier: AGPL-3.0-only
"""Offline synthetic fixture inventory and private-temp materializer controls."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import analysis, git_adapter, git_runtime, runtime_policy
from agent_braid.git_process import GitExecutionCancelled
from agent_braid.tooling_fixtures import (
    FixtureInventoryError, JOURNEY_CLASSES, canonical_json_bytes,
    fixture_input, load_inventory, materialize_fixture,
)
from agent_braid.tooling_mcp import ToolingConfig, ToolingService


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class ToolingFixtureTests(unittest.TestCase):
    def setUp(self):
        self.inventory = load_inventory(source_checkout=True)

    def test_inventory_has_18_unique_inputs_and_six_fixed_prompts(self):
        self.assertEqual(18, len(self.inventory.fixtures))
        self.assertEqual(6, len(self.inventory.prompts))
        self.assertEqual(set(JOURNEY_CLASSES), {item.journey_class for item in self.inventory.prompts})
        self.assertEqual(18, len({item.fixture_id for item in self.inventory.fixtures}))
        for journey in JOURNEY_CLASSES:
            group = [item for item in self.inventory.fixtures if item.journey_class == journey]
            self.assertEqual(3, len(group))
            self.assertEqual(3, len({item.definition_sha256 for item in group}))
        runtime_classes = set(JOURNEY_CLASSES[1:5])
        self.assertEqual(12, sum(item.definition["kind"] == "git-runtime" for item in self.inventory.fixtures))
        self.assertEqual(6, sum(item.definition["kind"] == "aim" for item in self.inventory.fixtures))
        for fixture in self.inventory.fixtures:
            self.assertEqual(fixture.definition_sha256,
                             _sha(canonical_json_bytes(fixture.definition)))
            if fixture.journey_class in runtime_classes:
                self.assertEqual("git-runtime", fixture.definition["kind"])
        self.assertEqual({"unknown", "conflicting", "independent-candidate"},
                         {item.definition["expected"]["interactionClassification"]
                          for item in self.inventory.fixtures if item.definition["kind"] == "aim"})
        self.assertTrue(all("synthetic" in prompt.text.lower() for prompt in self.inventory.prompts))
        for journey in JOURNEY_CLASSES:
            prompt = next(item for item in self.inventory.prompts if item.journey_class == journey)
            self.assertEqual(f"m45-prompt-{journey}", prompt.prompt_id)
        self.assertIn("already issued exact", next(p.text for p in self.inventory.prompts
                                                     if p.journey_class == "execute-granted-batch-verify"))
        self.assertIn("existing interrupted owned synthetic run", next(p.text for p in self.inventory.prompts
                                                               if p.journey_class == "inspect-recover-interruption"))
        for fixture in self.inventory.fixtures:
            scenario = fixture.definition["scenario"]
            self.assertTrue(scenario["preconditions"])
            self.assertTrue(scenario["phases"])
            self.assertTrue(scenario["expectedOutcomes"])

    def test_inventory_is_loaded_from_installed_resource_path_by_default(self):
        source = Path(__file__).resolve().parents[1] / "examples" / "tooling"
        with tempfile.TemporaryDirectory(prefix="m45-installed-assets-", dir=tempfile.gettempdir()) as temporary:
            package_root = Path(temporary) / "agent_braid"
            resource_root = package_root / "tooling_assets" / "fixtures"
            resource_root.mkdir(parents=True)
            shutil.copytree(source, resource_root, dirs_exist_ok=True)
            with patch("agent_braid.tooling_fixtures.importlib.resources.files", return_value=package_root):
                installed = load_inventory()
        self.assertEqual(self.inventory.inventory_sha256, installed.inventory_sha256)

    def test_immutable_source_inventory_hash_detects_direct_drift_and_oversize(self):
        source = Path(__file__).resolve().parents[1] / "examples" / "tooling"
        with tempfile.TemporaryDirectory(prefix="m45-fixture-drift-", dir=tempfile.gettempdir()) as temporary:
            assets = Path(temporary) / "assets"
            shutil.copytree(source, assets)
            target = assets / "fixture-inventory.json"
            target.write_bytes(target.read_bytes() + b" ")
            with self.assertRaisesRegex(FixtureInventoryError, "pinned fixture inventory hash mismatch"):
                load_inventory(source_checkout=True, assets_dir=assets)

            shutil.rmtree(assets)
            assets.mkdir()
            (assets / "fixture-inventory.json").write_bytes(b"x" * (64 * 1024 + 1))
            (assets / "prompts.json").write_bytes(b"{}")
            with self.assertRaisesRegex(FixtureInventoryError, "65536-byte read limit"):
                load_inventory(source_checkout=True, assets_dir=assets)

            shutil.rmtree(assets)
            shutil.copytree(source, assets)
            target = assets / "prompts.json"
            target.write_bytes(target.read_bytes().replace(b"Analyze the supplied", b"Alter the supplied", 1))
            with self.assertRaisesRegex(FixtureInventoryError, "pinned prompt inventory hash mismatch"):
                load_inventory(source_checkout=True, assets_dir=assets)

    def test_aim_fixtures_match_known_and_unknown_core_oracles(self):
        aim_fixtures = [item for item in self.inventory.fixtures if item.definition["kind"] == "aim"]
        self.assertEqual(6, len(aim_fixtures))
        for fixture in aim_fixtures:
            resolved = fixture_input(self.inventory, fixture.fixture_id)
            report = analysis.analyze(resolved.request)
            actual = {row["classification"] for row in report["interactions"]}
            self.assertEqual({resolved.expected_oracle["interactionClassification"]}, actual)
            self.assertEqual(_sha(canonical_json_bytes(resolved.request)), resolved.input_sha256)
            self.assertFalse(report["executionAuthorization"])
            if resolved.expected_oracle["coverageStatus"] == "unknown":
                self.assertTrue(report["uncertainty"])

    def test_mutated_frozen_inventory_refuses_before_destination_creation(self):
        fixture = next(item for item in self.inventory.fixtures if item.definition["kind"] == "git-runtime")
        fixture.definition["recipe"]["operations"][0]["path"] = "../escape.txt"
        with tempfile.TemporaryDirectory(prefix="m45-fixture-mutation-", dir=tempfile.gettempdir()) as temporary:
            destination = Path(temporary) / "fresh-root"
            with self.assertRaisesRegex(FixtureInventoryError, "changed after verification"):
                materialize_fixture(self.inventory, fixture.fixture_id, destination)
            self.assertFalse(destination.exists())

    def test_runtime_fixture_materializes_valid_request_and_read_only_prepare_parity(self):
        fixture = next(item for item in self.inventory.fixtures
                       if item.journey_class == "execute-granted-batch-verify")
        with tempfile.TemporaryDirectory(prefix="m45-fixture-runtime-", dir=tempfile.gettempdir()) as temporary:
            destination = Path(temporary).resolve() / "owned-synthetic"
            result = materialize_fixture(self.inventory, fixture.fixture_id, destination)
            self.assertEqual(fixture.definition_sha256, result.definition_sha256)
            self.assertEqual(_sha(canonical_json_bytes(result.request)), result.input_sha256)
            self.assertTrue(result.repository_root.is_relative_to(destination))
            self.assertTrue((result.repository_root / ".git").is_dir())
            self.assertEqual(fixture.fixture_id, result.root_manifest["fixtureId"])
            self.assertEqual(result.input_sha256, result.root_manifest["inputSha256"])
            self.assertEqual("independent-candidate", result.expected_oracle["interactionClassification"])
            self.assertFalse((result.repository_root / ".git" / "hooks" / "pre-commit").exists())

            core_analysis = git_adapter.analyze_git(result.analysis_request)
            runtime_analysis = git_runtime._analysis_request(result.request)
            self.assertEqual(core_analysis, git_adapter.analyze_git(runtime_analysis))
            self.assertEqual({"independent-candidate"},
                             {row["classification"] for row in core_analysis["interactions"]})

            results = destination / "results"
            grants = destination / "grants"
            results.mkdir(mode=0o700)
            grants.mkdir(mode=0o700)
            service = ToolingService(ToolingConfig(result.repository_root, results, grants, True))
            args = {"request": result.request, "runDirectory": str(service.config.result_parent / "prospective-run"),
                    "mode": "serial"}
            core_plan = service.runtime.invoke("prepare", args, threading.Event())
            wrapped = service.invoke("prepare", args, threading.Event())
            self.assertEqual("ok", wrapped["status"])
            self.assertEqual(core_plan, wrapped["result"])
            self.assertFalse((results / "prospective-run").exists())
            self.assertEqual([], list(grants.iterdir()))

    def _runtime_control(self, fixture, root):
        destination = root / "owned-synthetic"
        result = materialize_fixture(self.inventory, fixture.fixture_id, destination)
        results, grants = destination / "results", destination / "grants"
        results.mkdir(mode=0o700)
        grants.mkdir(mode=0o700)
        service = ToolingService(ToolingConfig(result.repository_root, results, grants, True))
        args = {"request": result.request, "runDirectory": str(service.config.result_parent / "prospective-run"),
                "mode": "serial"}
        prepared = service.invoke("prepare", args, threading.Event())
        self.assertEqual("ok", prepared["status"])
        return result, service, prepared["result"], grants

    def test_execute_fixture_positive_synthetic_grant_execute_status_verify_control(self):
        fixture = next(item for item in self.inventory.fixtures
                       if item.journey_class == "execute-granted-batch-verify")
        with tempfile.TemporaryDirectory(prefix="m45-execute-control-", dir=tempfile.gettempdir()) as temporary:
            result, service, plan, grants = self._runtime_control(fixture, Path(temporary))
            grant = runtime_policy.issue_operator_grant(plan, grants, acknowledge=plan["planDigest"])
            completed = service.invoke("execute", {"plan": plan, "grantId": grant["grantId"]}, threading.Event())
            self.assertEqual("ok", completed["status"], completed["summary"])
            self.assertEqual("completed", completed["result"]["runtime"]["status"])
            status = service.invoke("status", {"plan": plan}, threading.Event())
            verified = service.invoke("verify", {"plan": plan}, threading.Event())
            self.assertEqual("verified-completed", status["result"]["runtime"]["status"])
            self.assertEqual("verified-completed", verified["result"]["runtime"]["status"])
            self.assertEqual(result.request["expectedFinalTree"], verified["result"]["runtime"]["resultTree"])

    def test_recovery_fixture_positive_synthetic_interrupted_run_resume_and_verify_control(self):
        fixture = next(item for item in self.inventory.fixtures
                       if item.journey_class == "inspect-recover-interruption")
        with tempfile.TemporaryDirectory(prefix="m45-recovery-control-", dir=tempfile.gettempdir()) as temporary:
            result, service, plan, grants = self._runtime_control(fixture, Path(temporary))
            execute_grant = runtime_policy.issue_operator_grant(plan, grants,
                                                                 acknowledge=plan["planDigest"])
            original = git_runtime._atomic_json
            interrupted = False
            def interrupt_after_first_checkpoint(root, name, value):
                nonlocal interrupted
                original(root, name, value)
                if name == "state.json" and value.get("phase") == "ready" and value.get("nextIndex") == 1:
                    interrupted = True
                    raise GitExecutionCancelled("deterministic synthetic interruption")
            with patch("agent_braid.git_runtime._atomic_json", side_effect=interrupt_after_first_checkpoint):
                stopped = service.invoke("execute", {"plan": plan,
                    "grantId": execute_grant["grantId"]}, threading.Event())
            self.assertTrue(interrupted)
            self.assertIn(stopped["status"], {"unknown", "refused"})
            inspected = service.invoke("status", {"plan": plan}, threading.Event())
            self.assertIn(inspected["result"]["runtime"]["status"], {"verified-prefix", "unknown"})
            resume_grant = runtime_policy.issue_operator_grant(plan, grants,
                acknowledge=plan["planDigest"], action="resume")
            recovered = service.invoke("recover", {"plan": plan,
                "grantId": resume_grant["grantId"], "action": "resume"}, threading.Event())
            self.assertEqual("ok", recovered["status"], recovered["summary"])
            verified = service.invoke("verify", {"plan": plan}, threading.Event())
            self.assertEqual("verified-completed", verified["result"]["runtime"]["status"])
            self.assertEqual(result.request["expectedFinalTree"], verified["result"]["runtime"]["resultTree"])

    def test_materializer_refuses_existing_symlink_outside_temp_and_wrong_kind(self):
        fixture = next(item for item in self.inventory.fixtures if item.definition["kind"] == "git-runtime")
        aim = next(item for item in self.inventory.fixtures if item.definition["kind"] == "aim")
        with tempfile.TemporaryDirectory(prefix="m45-fixture-refusal-", dir=tempfile.gettempdir()) as temporary:
            root = Path(temporary)
            existing = root / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(FixtureInventoryError, "new path"):
                materialize_fixture(self.inventory, fixture.fixture_id, existing)
            link = root / "link"
            link.symlink_to(existing, target_is_directory=True)
            with self.assertRaisesRegex(FixtureInventoryError, "new path"):
                materialize_fixture(self.inventory, fixture.fixture_id, link)
            outside = Path.cwd() / ("never-create-m45-" + fixture.fixture_id)
            with self.assertRaisesRegex(FixtureInventoryError, "system temp directory"):
                materialize_fixture(self.inventory, fixture.fixture_id, outside)
            self.assertFalse(outside.exists())
            with self.assertRaisesRegex(FixtureInventoryError, "only runtime Git recipes"):
                materialize_fixture(self.inventory, aim.fixture_id, root / "unused")
            self.assertFalse((root / "unused").exists())


if __name__ == "__main__":
    unittest.main()
