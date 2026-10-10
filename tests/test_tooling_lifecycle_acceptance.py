# SPDX-License-Identifier: AGPL-3.0-only
"""Paired, owned-root acceptance procedures for SPEC-042 SC-002..SC-007."""
from dataclasses import replace
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import tooling_assets
from agent_braid.cli import main as cli_main
from agent_braid.tooling_install import InstallationRefused, Selection, apply, doctor, plan
from tests.test_tooling_install import _synthetic_older_bundle


class LifecycleAcceptance(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m45-lifecycle-")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source, self.results = self.base / "owned source", self.base / "owned results"
        self.source.mkdir(); self.results.mkdir()
        (self.source / "input.json").write_text('{"fixture":"owned"}\n', encoding="utf-8")
        (self.results / "sentinel.json").write_text('{"result":"preserve"}\n', encoding="utf-8")
        self.selection = Selection("codex", "user", self.source, self.results,
                                   home=self.base / "home", destination=self.base / "host")

    def snapshot_roots(self):
        def digest(root):
            return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in root.rglob("*") if p.is_file()}
        return digest(self.source), digest(self.results)

    def commit(self, selection=None, operation="install"):
        tx = plan(selection or self.selection, operation=operation, source_checkout=True)
        preview = tx.preview()
        applied = apply(tx, preview_digest=preview["previewDigest"])
        return preview, applied

    def test_sc002_preview_selected_apply_and_refusal_keep_stdout_protocol(self):
        before = self.snapshot_roots()
        tx = plan(self.selection, source_checkout=True)
        preview = tx.preview()
        self.assertEqual(preview["operation"], "install")
        self.assertTrue(preview["changes"])
        self.assertFalse(self.selection.destination.exists())
        with self.assertRaisesRegex(InstallationRefused, "preview digest"):
            apply(tx, preview_digest="0" * 64)
        self.assertFalse(self.selection.destination.exists())
        result = apply(tx, preview_digest=preview["previewDigest"])
        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["previewDigest"], preview["previewDigest"])
        self.assertFalse(result["runtimeEnabled"])
        self.assertEqual(result["enabledTools"], ["analyze-work", "analyze", "prepare"])
        self.assertEqual(self.snapshot_roots(), before)
        cfg, skills, receipt = self.selection.paths()
        self.assertIn(str(self.source), cfg.read_text())
        self.assertEqual(len(list(skills.glob("*/SKILL.md"))), 5)
        self.assertTrue(receipt.is_file())

    def test_sc002_cli_emits_only_typed_json_and_requires_selected_preview_digest(self):
        selection = self.selection
        args = ["tooling", "install", "--host", "codex", "--scope", "user",
                "--source-root", str(selection.source_root), "--result-root", str(selection.result_root),
                "--destination", str(selection.destination), "--source-checkout-assets"]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli_main(args), 0)
        preview = json.loads(out.getvalue())
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(preview["operation"], "install")
        self.assertEqual(preview["status"], "preview")
        self.assertEqual(len(preview["previewDigest"]), 64)
        self.assertFalse(selection.destination.exists())
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli_main(args + ["--apply"]), 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("exact --preview-digest", err.getvalue())
        self.assertFalse(selection.destination.exists())
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(cli_main(args + ["--apply", "--preview-digest", preview["previewDigest"]]), 0)
        applied = json.loads(out.getvalue())
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(applied["status"], "applied")
        self.assertEqual(applied["previewDigest"], preview["previewDigest"])

    def test_sc003_user_project_and_codex_home_are_explicit_and_root_scoped(self):
        original_results = self.snapshot_roots()[1]
        second = self.base / "second source"; second.mkdir()
        (second / "input.json").write_text('{"fixture":"second-owned"}\n', encoding="utf-8")
        alternate = self.base / "nondefault CODEX_HOME"
        user = replace(self.selection, destination=None, codex_home=alternate)
        project = replace(user, scope="project")
        user_cfg = user.paths()[0]
        project_cfg = project.paths()[0]
        self.assertEqual(user_cfg, alternate / "config.toml")
        self.assertEqual(project_cfg, self.source / ".codex" / "config.toml")
        first_entry = self.selection.server()
        second_entry = replace(self.selection, source_root=second).server()
        self.assertIn(str(self.source), first_entry["args"])
        self.assertNotIn(str(second), first_entry["args"])
        self.assertIn(str(second), second_entry["args"])
        self.assertNotIn(str(self.source), second_entry["args"])
        claude_home = self.base / "claude home"
        claude_user = replace(user, host="claude", home=claude_home, name="codex-mirror")
        claude_project = replace(project, host="claude", home=claude_home, name="project-mirror")
        claude_second = replace(claude_project, source_root=second, name="second-project")
        for selected in (user, project, replace(project, source_root=second),
                         claude_user, claude_project, claude_second):
            tx = plan(selected, source_checkout=True)
            result = apply(tx, preview_digest=tx.preview()["previewDigest"])
            self.assertEqual(result["status"], "applied")
            config, _, receipt = selected.paths()
            self.assertTrue(config.is_file() and receipt.is_file())
            self.assertIn(str(selected.source_root), config.read_text())
        self.assertEqual((self.source / "input.json").read_text(), '{"fixture":"owned"}\n')
        self.assertEqual((second / "input.json").read_text(), '{"fixture":"second-owned"}\n')
        self.assertEqual(self.snapshot_roots()[1], original_results)
        invalid = replace(self.selection, scope="global")
        with self.assertRaisesRegex(InstallationRefused, "unsupported scope"):
            invalid.paths()
        self.assertEqual(self.snapshot_roots()[0]["input.json"], hashlib.sha256(b'{"fixture":"owned"}\n').hexdigest())

    def test_sc004_idempotent_owned_change_preserves_unrelated_bytes_and_refuses_collision(self):
        cfg, _, _ = self.selection.paths(); cfg.parent.mkdir(parents=True)
        unrelated = b'# user note\nmodel = "local"\n'
        cfg.write_bytes(unrelated)
        _, first = self.commit()
        installed = cfg.read_bytes()
        self.assertTrue(installed.startswith(unrelated))
        self.assertEqual(first["status"], "applied")
        _, again = self.commit()
        self.assertEqual(again["status"], "unchanged")
        self.assertEqual(cfg.read_bytes(), installed)
        # An unowned same-name entry must refuse before any asset or receipt is written.
        other = replace(self.selection, destination=self.base / "collision")
        collision_cfg, collision_skills, collision_receipt = other.paths()
        collision_cfg.parent.mkdir(parents=True)
        collision = b'[mcp_servers.agent-braid]\ncommand="user-owned"\n'
        collision_cfg.write_bytes(collision)
        with self.assertRaises(InstallationRefused) as caught:
            plan(other, source_checkout=True)
        self.assertEqual(collision_cfg.read_bytes(), collision)
        self.assertFalse(collision_skills.exists()); self.assertFalse(collision_receipt.exists())
        self.assertEqual(caught.exception.diagnostic["comparison"]["ownership"], "unowned")

    def test_sc005_doctor_separates_healthy_static_checks_from_unavailable_host_and_pending_auth(self):
        before = self.snapshot_roots()
        with patch("agent_braid.tooling_install.shutil.which", return_value=None):
            report = doctor(self.selection, source_checkout=True)
        checks = report["checks"]
        self.assertEqual(report["schema"], "agent-braid-doctor/v0.1")
        self.assertEqual(checks["assets"]["status"], "ok")
        self.assertEqual(checks["roots"]["status"], "ok")
        self.assertEqual(checks["host"]["status"], "unavailable")
        self.assertEqual(checks["protocol"]["status"], "pending")
        self.assertEqual(checks["authentication"]["status"], "pending")
        self.assertEqual(checks["hostApproval"]["status"], "pending")
        self.assertFalse(report["paidSessionStarted"])
        self.assertFalse(report["runtimeDispatched"])
        self.assertFalse(report["grantIssued"])
        invalid = replace(self.selection, source_root=self.results)
        refused = doctor(invalid, source_checkout=True)
        self.assertEqual(refused["checks"]["roots"]["status"], "refused")
        self.assertEqual(self.snapshot_roots(), before)

    def test_sc006_older_owned_bundle_updates_with_receipt_and_modified_asset_refuses(self):
        current = tooling_assets.load_skill_bundle(source_checkout=True)
        older = _synthetic_older_bundle(current)
        with patch("agent_braid.tooling_assets.load_skill_bundle", return_value=older):
            self.commit()
        cfg, skills, receipt_path = self.selection.paths()
        target = skills / older.skills[0].name / "SKILL.md"
        self.assertEqual(target.read_text(), older.skills[0].content)
        tx = plan(self.selection, operation="update", source_checkout=True)
        preview = tx.preview()
        self.assertIn(str(target), [change["path"] for change in preview["changes"]])
        changed = apply(tx, preview_digest=preview["previewDigest"])
        self.assertEqual(changed["status"], "applied")
        receipt = json.loads(receipt_path.read_bytes())
        self.assertEqual(receipt["bundleSha256"], current.sha256)
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), receipt["files"][f"{older.skills[0].name}/SKILL.md"])
        private_edit = b"owned-user-edit"
        target.write_bytes(private_edit)
        before = {p.relative_to(self.selection.destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.selection.destination.rglob("*") if p.is_file()}
        with self.assertRaisesRegex(InstallationRefused, "user edit") as caught:
            plan(self.selection, operation="update", source_checkout=True)
        diagnostic = caught.exception.diagnostic
        self.assertEqual(diagnostic["comparison"]["ownership"], "owned_but_modified")
        self.assertEqual(diagnostic["comparison"]["current"]["sha256"], hashlib.sha256(private_edit).hexdigest())
        self.assertTrue(diagnostic["comparison"]["redacted"])
        self.assertNotIn(private_edit.decode(), json.dumps(diagnostic))
        after = {p.relative_to(self.selection.destination).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.selection.destination.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        self.assertEqual(target.read_bytes(), private_edit)

    def test_sc007_uninstall_twice_removes_owned_and_preserves_modified_and_shared_data(self):
        cfg, skills, receipt = self.selection.paths(); cfg.parent.mkdir(parents=True)
        shared = b'# shared user bytes\n'
        cfg.write_bytes(shared)
        self.commit()
        edited = skills / "agent-braid-analyze" / "SKILL.md"
        edited.write_bytes(b"user-owned modified skill")
        before_source, before_results = self.snapshot_roots()
        _, removed = self.commit(operation="uninstall")
        self.assertEqual(removed["status"], "applied")
        self.assertEqual(cfg.read_bytes(), shared)
        self.assertEqual(edited.read_bytes(), b"user-owned modified skill")
        self.assertTrue(removed["residuals"])
        self.assertTrue(receipt.is_file())
        residual_receipt = json.loads(receipt.read_bytes())
        self.assertEqual(residual_receipt["state"], "residual")
        self.assertIn("agent-braid-analyze/SKILL.md", residual_receipt["files"])
        _, repeated = self.commit(operation="uninstall")
        self.assertEqual(repeated["status"], "unchanged")
        self.assertEqual(cfg.read_bytes(), shared)
        self.assertEqual(self.snapshot_roots(), (before_source, before_results))


if __name__ == "__main__":
    unittest.main()
