# SPDX-License-Identifier: AGPL-3.0-only
"""Temporary-host positive and refusal controls for receipt-owned lifecycle."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from agent_braid.cli import main
from agent_braid.tooling_install import InstallationRefused, Selection, apply, doctor, plan


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.source = self.root / "repository space á"
        self.results = self.root / "private results"
        self.source.mkdir()
        self.results.mkdir()
        self.selection = Selection(host="codex", scope="user", source_root=self.source,
                                   result_root=self.results, home=self.root / "host home",
                                   destination=self.root / "isolated host")

    def transact(self, selection=None, operation="install"):
        transaction = plan(selection or self.selection, operation=operation, source_checkout=True)
        return apply(transaction, preview_digest=transaction.preview()["previewDigest"])

    def test_preview_has_no_effect_and_apply_requires_exact_selection(self):
        transaction = plan(self.selection, source_checkout=True)
        self.assertFalse(self.selection.destination.exists())
        with self.assertRaisesRegex(InstallationRefused, "preview digest"):
            apply(transaction, preview_digest="0" * 64)
        self.assertFalse(self.selection.destination.exists())
        report = apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        self.assertEqual(report["status"], "applied")
        config, skills, receipt = self.selection.paths()
        entry = tomllib.loads(config.read_text())["mcp_servers"]["agent-braid"]
        self.assertIn(str(self.source), entry["args"])
        self.assertNotIn("--enable-runtime", entry["args"])
        self.assertEqual(len(list(skills.glob("*/SKILL.md"))), 5)
        self.assertTrue(receipt.is_file())

    def test_repeat_install_and_update_are_idempotent(self):
        self.transact()
        for operation in ("install", "update"):
            transaction = plan(self.selection, operation=operation, source_checkout=True)
            self.assertEqual(transaction.changes, [])
            self.assertEqual(apply(transaction, preview_digest=transaction.preview()["previewDigest"])["status"], "unchanged")

    def test_toml_comments_and_unrelated_bytes_survive_install_remove(self):
        config, _, _ = self.selection.paths()
        config.parent.mkdir()
        original = b'# personal comment\nmodel = "example"\n[mcp_servers.other]\ncommand = "safe"'  # no final newline
        config.write_bytes(original)
        report = self.transact()
        self.assertTrue(config.read_bytes().startswith(original))
        self.assertEqual(len(report["backups"]), 1)
        backup = Path(report["backups"][0]["path"])
        self.assertEqual(backup.read_bytes(), original)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.transact(operation="update")
        self.transact(operation="uninstall")
        self.assertEqual(config.read_bytes(), original)
        self.assertEqual(self.transact(operation="uninstall")["status"], "unchanged")

    def test_json_preserves_unrelated_member_bytes_and_shared_server(self):
        selection = replace(self.selection, host="claude")
        config, _, _ = selection.paths()
        config.parent.mkdir()
        original = b'{\n  "personal" : [1,2],\n  "mcpServers" : { "other" : {"command":"x"} },\n  "theme": "dark"\n}\n'
        config.write_bytes(original)
        self.transact(selection)
        installed = config.read_bytes()
        self.assertIn(b'"personal" : [1,2]', installed)
        self.assertIn(b'"other" : {"command":"x"}', installed)
        changed = installed.replace(b'"dark"', b'"light"')
        config.write_bytes(changed)
        self.transact(selection, "uninstall")
        self.assertEqual(config.read_bytes(), original.replace(b'"dark"', b'"light"'))
        self.assertEqual(json.loads(config.read_bytes())["mcpServers"], {"other": {"command": "x"}})

    def test_missing_json_servers_container_leaves_only_empty_shared_container(self):
        selection = replace(self.selection, host="claude")
        self.transact(selection)
        self.transact(selection, "uninstall")
        config, _, _ = selection.paths()
        self.assertEqual(json.loads(config.read_bytes()), {"mcpServers": {}})

    def test_malformed_duplicate_and_collision_configs_refuse_before_writes(self):
        for host, content in (("codex", b"[invalid"), ("codex", b'[mcp_servers.agent-braid]\ncommand="user"\n'),
                              ("claude", b'{"mcpServers":{},"mcpServers":{}}'),
                              ("claude", b'{"mcpServers":{"agent-braid":{"command":"user"}}}'),
                              ("claude", b'{"mcpServers":1}')):
            with self.subTest(host=host, content=content):
                selection = replace(self.selection, host=host)
                config, skills, receipt = selection.paths()
                config.parent.mkdir(exist_ok=True)
                config.write_bytes(content)
                with self.assertRaises(InstallationRefused):
                    plan(selection, source_checkout=True)
                self.assertEqual(config.read_bytes(), content)
                self.assertFalse(skills.exists())
                self.assertFalse(receipt.exists())

    def test_concurrent_edit_refuses_all_changes(self):
        transaction = plan(self.selection, source_checkout=True)
        config, skills, receipt = self.selection.paths()
        config.parent.mkdir()
        config.write_text("# concurrent user edit\n")
        with self.assertRaisesRegex(InstallationRefused, "concurrent"):
            apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        self.assertEqual(config.read_text(), "# concurrent user edit\n")
        self.assertFalse(skills.exists())
        self.assertFalse(receipt.exists())

    def test_interrupted_apply_rolls_back_every_written_file(self):
        config, skills, receipt = self.selection.paths()
        config.parent.mkdir()
        original = b"# retained\n"
        config.write_bytes(original)
        transaction = plan(self.selection, source_checkout=True)
        def fail(index, path):
            if index == 2:
                raise OSError("injected write interruption")
        with self.assertRaisesRegex(OSError, "injected"):
            apply(transaction, preview_digest=transaction.preview()["previewDigest"], fault=fail)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(receipt.exists())
        self.assertEqual(list(skills.glob("*/SKILL.md")), [])
        self.assertEqual(list(self.root.rglob(".agent-braid-install.lock")), [])

    def test_post_replace_directory_sync_error_rolls_back_mutated_destination(self):
        config, _, receipt = self.selection.paths()
        config.parent.mkdir()
        original = b"# retained before directory sync failure\n"
        config.write_bytes(original)
        transaction = plan(self.selection, source_checkout=True)
        from agent_braid import tooling_install
        real_sync = tooling_install._sync_directory
        failed = False
        def fail_once(path):
            nonlocal failed
            if not failed:
                failed = True
                raise OSError("injected directory sync error after replace")
            return real_sync(path)
        with patch.object(tooling_install, "_sync_directory", side_effect=fail_once):
            with self.assertRaisesRegex(OSError, "directory sync"):
                apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        self.assertTrue(failed)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse(receipt.exists())

    def test_runtime_grants_must_be_outside_source_and_result_roots(self):
        for grant in (self.source / "grants", self.results / "grants", self.root):
            with self.subTest(grant=grant), self.assertRaises(InstallationRefused):
                plan(replace(self.selection, grant_store=grant, enable_runtime=True), source_checkout=True)
        transaction = plan(replace(self.selection, grant_store=self.root / "grants", enable_runtime=True), source_checkout=True)
        self.assertIn("execute", transaction.preview()["enabledTools"])

    def test_existing_directory_grant_store_is_accepted_but_file_or_alias_is_refused(self):
        grants = self.root / "existing-grants"
        grants.mkdir(mode=0o700)
        selection = replace(self.selection, grant_store=grants, enable_runtime=True)
        self.assertIn("execute", plan(selection, source_checkout=True).preview()["enabledTools"])
        self.assertEqual([], list(grants.iterdir()))
        wrong = self.root / "file-grants"
        wrong.write_bytes(b"owned content")
        alias = self.root / "aliased-grants"
        alias.symlink_to(grants, target_is_directory=True)
        for path in (wrong, wrong / "child", alias):
            with self.subTest(path=path), self.assertRaises(InstallationRefused):
                plan(replace(selection, grant_store=path), source_checkout=True)
        self.assertEqual(b"owned content", wrong.read_bytes())
        self.assertFalse(self.selection.destination.exists())

    def test_doctor_permission_failure_is_not_healthy(self):
        real_access = os.access
        def access(path, mode):
            if Path(path) == self.results and mode == os.W_OK:
                return False
            return real_access(path, mode)
        with patch("agent_braid.tooling_install.os.access", side_effect=access):
            report = doctor(self.selection, source_checkout=True)
        self.assertEqual(report["checks"]["roots"]["status"], "unavailable")
        self.assertFalse(report["checks"]["roots"]["resultWritable"])

    def test_modified_skills_and_config_are_preserved_on_uninstall(self):
        self.transact()
        config, skills, _ = self.selection.paths()
        edited = skills / "agent-braid-analyze" / "SKILL.md"
        edited.write_text("owner changes")
        config.write_bytes(config.read_bytes().replace(b"command = ", b"command= "))
        before = config.read_bytes()
        report = self.transact(operation="uninstall")
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(edited.read_text(), "owner changes")
        self.assertEqual(len(report["residuals"]), 2)
        self.assertEqual(len(list(skills.glob("*/SKILL.md"))), 1)
        self.assertEqual(self.transact(operation="uninstall")["status"], "unchanged")

    def test_update_does_not_adopt_a_user_edit(self):
        self.transact()
        _, skills, _ = self.selection.paths()
        target = skills / "agent-braid-analyze" / "SKILL.md"
        target.write_text("modified")
        with self.assertRaisesRegex(InstallationRefused, "user edit"):
            plan(self.selection, operation="update", source_checkout=True)
        self.assertEqual(target.read_text(), "modified")

    def test_unknown_skill_contents_are_not_adopted_or_removed(self):
        self.transact()
        _, skills, _ = self.selection.paths()
        foreign = skills / "agent-braid-analyze" / "personal.txt"
        foreign.write_text("private personal notes")
        with self.assertRaisesRegex(InstallationRefused, "shared skill"):
            plan(self.selection, operation="update", source_checkout=True)
        report = self.transact(operation="uninstall")
        self.assertEqual(foreign.read_text(), "private personal notes")
        self.assertTrue(any("unowned skill contents" in value for value in report["residuals"]))
        repeat = self.transact(operation="uninstall")
        self.assertEqual(repeat["status"], "unchanged")
        self.assertEqual(repeat["residuals"], report["residuals"])

    def test_receipt_cannot_relabel_foreign_file_as_generated_backup(self):
        self.transact()
        config, skills, receipt = self.selection.paths()
        foreign = skills / "agent-braid-analyze" / "private-notes.txt"
        foreign.write_text("private owner notes")
        value = json.loads(receipt.read_bytes())
        import hashlib
        value["backups"].append({"path": str(foreign), "sha256": hashlib.sha256(foreign.read_bytes()).hexdigest()})
        receipt.write_text(json.dumps(value))
        before = config.read_bytes()
        for operation in ("update", "uninstall"):
            with self.subTest(operation=operation), self.assertRaisesRegex(InstallationRefused, "backup.*inventory"):
                plan(self.selection, operation=operation, source_checkout=True)
        self.assertEqual(foreign.read_text(), "private owner notes")
        self.assertEqual(config.read_bytes(), before)

    def test_symlink_destination_refuses_even_when_target_is_valid(self):
        destination = self.selection.destination
        other = self.root / "other"
        other.mkdir()
        destination.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(InstallationRefused, "symlink"):
            plan(self.selection, source_checkout=True)
        self.assertEqual(list(other.iterdir()), [])

    def test_scope_codex_home_and_two_explicit_source_roots(self):
        alternate = self.root / "alternate codex"
        selection = replace(self.selection, destination=None)
        with patch.dict(os.environ, {"CODEX_HOME": str(alternate), "XDG_CONFIG_HOME": str(self.root / "xdg")}):
            config, skills, _ = selection.paths()
            self.assertEqual(config, alternate / "config.toml")
            self.assertEqual(skills, selection.home / ".agents" / "skills")
            project = replace(selection, scope="project")
            self.assertEqual(project.paths()[0], self.source / ".codex" / "config.toml")
            second = self.root / "second source"
            second.mkdir()
            other = replace(selection, name="other-root", source_root=second)
            self.assertIn(str(second), other.server()["args"])
            self.assertNotIn(str(self.source), other.server()["args"])

    def test_doctor_is_read_only_and_never_claims_observation_or_auth(self):
        with patch("agent_braid.tooling_install.shutil.which", return_value=None):
            report = doctor(self.selection, source_checkout=True)
        self.assertEqual(report["checks"]["assets"]["status"], "ok")
        self.assertEqual(report["checks"]["host"]["status"], "unavailable")
        self.assertEqual(report["checks"]["protocol"]["status"], "pending")
        self.assertEqual(report["checks"]["authentication"]["status"], "pending")
        self.assertFalse(report["paidSessionStarted"])
        self.assertFalse(report["runtimeDispatched"])
        self.assertFalse(report["grantIssued"])
        self.assertFalse(self.selection.destination.exists())

    def test_cli_preview_and_apply_without_digest_have_no_effect(self):
        args = ["tooling", "install", "--host", "codex", "--scope", "user", "--source-root", str(self.source),
                "--result-root", str(self.results), "--destination", str(self.selection.destination), "--source-checkout-assets"]
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(main(args), 0)
        self.assertIn("previewDigest", json.loads(output.getvalue()))
        self.assertFalse(self.selection.destination.exists())
        output.truncate(0)
        output.seek(0)
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(main(args + ["--apply"]), 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("--preview-digest", errors.getvalue())
        self.assertFalse(self.selection.destination.exists())

    def test_cli_presentation_preserves_finite_numbers_and_refuses_ambiguous_json(self):
        source = self.root / "presentation.json"
        source.write_text('{"status":"unknown","elapsed":1.25}')
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(main(["tooling", "present", str(source), "--format", "json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"status": "unknown", "elapsed": 1.25})
        for value in ('{"status":"ok","status":"unknown"}', '{"elapsed":NaN}'):
            source.write_text(value)
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(errors):
                self.assertEqual(main(["tooling", "present", str(source), "--format", "json"]), 2)
            self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
