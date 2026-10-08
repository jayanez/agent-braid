# SPDX-License-Identifier: AGPL-3.0-only
"""Complete owned offline journey; no real host, provider or capture acceptance."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import git_runtime, runtime_policy
from agent_braid.git_process import GitExecutionCancelled
from agent_braid.tooling_assets import load_skill_bundle
from agent_braid.tooling_fixtures import load_inventory, materialize_fixture
from agent_braid.tooling_install import Selection, apply, plan
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from agent_braid import tooling_present as presentation


class OfflineJourneyTests(unittest.TestCase):
    def test_install_discovery_refusal_execute_recovery_verification_and_export(self):
        # Independent local operator control: grants are issued through the core
        # policy API in this test only. No tool or skill receives an issuer.
        inventory = load_inventory(source_checkout=True)
        with tempfile.TemporaryDirectory(prefix="m45-whole-journey-") as temporary:
            root = Path(temporary).resolve()
            fixture = materialize_fixture(inventory,
                "m45-inspect-recover-interruption-01", root / "fixture")
            results, grants = root / "results", root / "grants"
            results.mkdir(mode=0o700); grants.mkdir(mode=0o700)
            env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
            env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
            def source_identity():
                return subprocess.check_output(["git", "-C", str(fixture.repository_root),
                    "rev-parse", "HEAD", "HEAD^{tree}"], env=env)
            original_source = source_identity()
            selections = []
            for host in ("codex", "claude"):
                selection = Selection(host, "user", fixture.repository_root, results,
                    grant_store=grants, enable_runtime=True,
                    destination=root / (host + " isolated assets"))
                tx = plan(selection, source_checkout=True)
                self.assertFalse(selection.destination.exists())
                apply(tx, preview_digest=tx.preview()["previewDigest"])
                self.assertEqual([], plan(selection, source_checkout=True).changes)
                _, skills, _ = selection.paths()
                self.assertEqual(5, len(list(skills.glob("*/SKILL.md"))))
                for skill in load_skill_bundle(source_checkout=True).skills:
                    self.assertEqual(skill.sha256,
                        hashlib.sha256((skills / skill.name / "SKILL.md").read_bytes()).hexdigest())
                selections.append(selection)
            service = ToolingService(ToolingConfig(fixture.repository_root, results, grants, True))
            self.assertEqual({"analyze-work", "analyze", "prepare", "status", "execute", "recover", "verify"},
                             set(service.capabilities()["tools"]))
            self.assertNotIn("grant", " ".join(service.tools))
            event = threading.Event()
            analyzed = service.invoke("analyze-work", {"kind": "git", "request": fixture.analysis_request}, event)
            self.assertEqual("ok", analyzed["status"])
            self.assertIn("independent-candidate", presentation.render_summary(analyzed))
            prepared = service.invoke("prepare", {"request": fixture.request,
                "runDirectory": str(results / "run"), "mode": "serial"}, event)
            self.assertEqual("ok", prepared["status"])
            bounded_plan = prepared["result"]
            self.assertFalse((results / "run").exists())
            refused = service.invoke("execute", {"plan": bounded_plan,
                "grantId": "synthetic-unissued-grant"}, event)
            self.assertEqual("refused", refused["status"])
            self.assertFalse((results / "run").exists())
            self.assertEqual([], list(grants.iterdir()))
            # The separate test operator now grants the exact inspected plan.
            grant = runtime_policy.issue_operator_grant(bounded_plan, grants,
                acknowledge=bounded_plan["planDigest"])
            original_write = git_runtime._atomic_json
            interrupted = False
            def checkpoint_interruption(directory, name, value):
                nonlocal interrupted
                original_write(directory, name, value)
                if name == "state.json" and value.get("phase") == "ready" and value.get("nextIndex") == 1:
                    interrupted = True
                    raise GitExecutionCancelled("owned offline journey checkpoint control")
            with patch("agent_braid.git_runtime._atomic_json", side_effect=checkpoint_interruption):
                stopped = service.invoke("execute", {"plan": bounded_plan, "grantId": grant["grantId"]}, event)
            self.assertTrue(interrupted)
            self.assertIn(stopped["status"], {"unknown", "refused"})
            inspected = service.invoke("status", {"plan": bounded_plan}, event)
            self.assertIn(inspected["result"]["runtime"]["status"], {"verified-prefix", "unknown"})
            recovery_grant = runtime_policy.issue_operator_grant(bounded_plan, grants,
                acknowledge=bounded_plan["planDigest"], action="resume")
            recovered = service.invoke("recover", {"plan": bounded_plan,
                "grantId": recovery_grant["grantId"], "action": "resume"}, event)
            self.assertEqual("ok", recovered["status"], recovered["summary"])
            verified = service.invoke("verify", {"plan": bounded_plan}, event)
            self.assertEqual("verified-completed", verified["result"]["runtime"]["status"])
            self.assertEqual(fixture.request["expectedFinalTree"], verified["result"]["runtime"]["resultTree"])
            self.assertEqual(original_source, source_identity())
            self.assertIn("verified-completed", presentation.render_summary(verified))
            # Reuse the complete verified envelope, never an artifact reference
            # treated as its bytes. Exports are deterministic across destinations.
            expected = presentation.build_exports(verified, selected_evidence_refs=[])
            presentation.write_exports(verified, root / "export", selected_evidence_refs=[])
            for name, raw in expected.items():
                self.assertEqual(raw, (root / "export" / name).read_bytes())
            self.assertEqual(verified, json.loads(expected["evidence.json"]))
            for selection in selections:
                removal = plan(selection, operation="uninstall", source_checkout=True)
                apply(removal, preview_digest=removal.preview()["previewDigest"])
                self.assertEqual([], plan(selection, operation="uninstall", source_checkout=True).changes)
            self.assertEqual(original_source, source_identity())


if __name__ == "__main__":
    unittest.main()
