# SPDX-License-Identifier: AGPL-3.0-only
"""OpenCode legacy profile: JSONC-preserving, receipt-owned lifecycle (SPEC-068 T007)."""
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import jsonc, plugin_legacy
from agent_braid.cli import main
from agent_braid.tooling_install import (InstallationRefused, Selection, _members, apply, asset_provenance,
                                         doctor, native_plugin_configured, plan)

COMMENTED = '''// user configuration
{
  /* keep this block comment */
  "$schema": "https://opencode.ai/config.json", // trailing comment
  "theme": "a // not a comment",
  "mcp": {
    // foreign server
    "other": {"type": "remote", "url": "https://example.test/mcp//x",},
    "second": {"type": "local", "command": ["x"]},
  },
  "plugin": ["some-plugin",],
}
'''


class Base(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.source = self.root / "src"
        self.results = self.root / "res"
        self.source.mkdir()
        self.results.mkdir()
        self.destination = self.root / "dest"
        self.selection = Selection(host="opencode", scope="user", source_root=self.source, result_root=self.results,
                                   destination=self.destination, home=self.root / "home")
        self.config, self.skills, self.receipt = self.selection.paths()

    def doctor(self, selection=None):
        with tempfile.TemporaryDirectory() as bin_dir:
            fake = Path(bin_dir) / "opencode"
            fake.write_text("#!/bin/sh\n")
            fake.chmod(0o755)
            with patch.dict(os.environ, {"PATH": bin_dir}):
                return doctor(selection or self.selection, source_checkout=True)

    def write_config(self, text, path=None):
        path = path or self.config
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode() if isinstance(text, str) else text)

    def plan(self, operation="install", selection=None):
        return plan(selection or self.selection, operation=operation, source_checkout=True)

    def transact(self, operation="install", selection=None):
        transaction = self.plan(operation, selection)
        return apply(transaction, preview_digest=transaction.preview()["previewDigest"])

    def entry(self):
        return json.loads(jsonc.clean(self.config.read_text()).text)["mcp"]["agent-braid"]


class LifecycleTests(Base):
    def test_preview_apply_creates_owned_entry_and_skills_only(self):
        transaction = self.plan()
        self.assertFalse(self.destination.exists())
        with self.assertRaisesRegex(InstallationRefused, "preview digest"):
            apply(transaction, preview_digest="0" * 64)
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.transact()["status"], "applied")
        self.assertEqual(self.config.name, "opencode.json")
        entry = self.entry()
        self.assertEqual(list(entry), ["type", "command", "codemode"])
        self.assertEqual((entry["type"], entry["codemode"]), ("local", False))
        self.assertNotIn("protocol", entry)
        self.assertEqual(entry["command"][1:5], ["-m", "agent_braid", "tooling", "serve"])
        self.assertIn(str(self.source), entry["command"])
        self.assertEqual(len(list(self.skills.glob("agent-braid-*/SKILL.md"))), 5)
        receipt = json.loads(self.receipt.read_text())
        self.assertEqual((receipt["host"], receipt["serverName"], receipt["createdMcp"]), ("opencode", "agent-braid", True))

    def test_comments_foreign_members_and_trailing_commas_are_preserved(self):
        self.write_config(COMMENTED)
        self.transact()
        after = self.config.read_text()
        for fragment in ("// user configuration", "/* keep this block comment */", "// trailing comment",
                         "a // not a comment", "// foreign server", '"url": "https://example.test/mcp//x",}',
                         '"plugin": ["some-plugin",],'):
            self.assertIn(fragment, after)
        parsed = json.loads(jsonc.clean(after).text)
        self.assertEqual(set(parsed["mcp"]), {"other", "second", "agent-braid"})
        self.assertEqual(parsed["mcp"]["second"], {"type": "local", "command": ["x"]})
        self.assertFalse(json.loads(self.receipt.read_text())["createdMcp"])
        self.transact("uninstall")
        self.assertEqual(self.config.read_text(), COMMENTED)

    def test_created_mcp_container_is_removed_only_when_created(self):
        original = '{\n  // c\n  "theme": "dark",\n}\n'
        self.write_config(original)
        self.transact()
        self.assertTrue(json.loads(self.receipt.read_text())["createdMcp"])
        self.transact("uninstall")
        self.assertEqual(self.config.read_text(), original)
        # An existing, empty container stays after uninstall.
        self.write_config('{\n  "mcp": {}\n}\n')
        self.transact()
        self.assertFalse(json.loads(self.receipt.read_text())["createdMcp"])
        self.transact("uninstall")
        self.assertEqual(self.config.read_text(), '{\n  "mcp": {}\n}\n')

    def test_foreign_server_after_the_owned_entry_survives_uninstall(self):
        for tail in ("", ","):
            with self.subTest(tail=tail):
                self.write_config('{\n  "mcp": {\n    "first": {"type": "local", "command": ["f"]}\n  }\n}\n')
                self.transact()
                text = self.config.read_text()
                end = text.index("}}\n}")  # closes the owned entry
                self.write_config(text[:end + 1] + ', // note\n    "after": {"type": "local", "command": ["a"]}' + tail
                                  + text[end + 1:])
                self.transact("uninstall")
                result = self.config.read_text()
                self.assertNotIn("agent-braid", result)
                self.assertIn("// note", result)
                self.assertEqual(set(json.loads(jsonc.clean(result).text)["mcp"]), {"first", "after"})

    def test_created_container_is_kept_when_foreign_servers_were_added(self):
        self.write_config("{}\n")
        self.transact()
        text = self.config.read_text()
        self.write_config(text.replace('"agent-braid": {', '"added": {"type": "local", "command": ["y"]},\n"agent-braid": {', 1))
        self.transact("uninstall")
        parsed = json.loads(self.config.read_text())
        self.assertEqual(list(parsed["mcp"]), ["added"])

    def test_repeat_install_and_update_do_not_write(self):
        self.write_config(COMMENTED)
        self.transact()
        before = self.config.stat()
        for operation in ("install", "update"):
            transaction = self.plan(operation)
            self.assertEqual(transaction.changes, [])
            self.assertEqual(apply(transaction, preview_digest=transaction.preview()["previewDigest"])["status"], "unchanged")
        after = self.config.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))

    def test_update_changes_only_the_owned_span(self):
        self.write_config(COMMENTED)
        self.transact()
        installed = self.config.read_text()
        selection = replace(self.selection, telemetry="local")
        self.transact("update", selection)
        updated = self.config.read_text()
        self.assertIn("--telemetry", self.entry()["command"])
        start = installed.index('"agent-braid": ') + len('"agent-braid": ')
        end = installed.index('"codemode": false', start) + len('"codemode": false\n  }')
        self.assertEqual(installed[:start], updated[:start])
        self.assertTrue(updated.endswith(installed[end:]))

    def test_uninstall_retains_user_edits_made_after_apply(self):
        self.write_config(COMMENTED)
        self.transact()
        edited = self.config.read_text().replace("// foreign server", "// foreign server (edited by user)")
        edited = edited.replace('"theme": "a // not a comment"', '"theme": "changed"')
        self.write_config(edited)
        self.transact("uninstall")
        self.assertEqual(self.config.read_text(), COMMENTED.replace("// foreign server", "// foreign server (edited by user)")
                         .replace('"theme": "a // not a comment"', '"theme": "changed"'))
        self.assertEqual(json.loads(self.receipt.read_text())["state"], "uninstalled")

    def test_reinstall_after_uninstall(self):
        self.write_config(COMMENTED)
        self.transact()
        self.transact("uninstall")
        self.assertEqual(self.transact()["status"], "applied")
        self.assertIn("agent-braid", json.loads(jsonc.clean(self.config.read_text()).text)["mcp"])

    def test_telemetry_and_runtime_flags_reach_the_entry(self):
        grants = self.root / "grants"
        selection = replace(self.selection, telemetry="local", enable_runtime=True, grant_store=grants)
        self.transact(selection=selection)
        command = self.entry()["command"]
        self.assertIn("--enable-runtime", command)
        self.assertIn("--telemetry", command)

    def test_custom_name_uses_its_own_key(self):
        selection = replace(self.selection, name="legacy-braid")
        self.transact(selection=selection)
        self.assertIn("legacy-braid", json.loads(self.config.read_text())["mcp"])


class PathTests(Base):
    def test_user_paths_follow_xdg_and_prefer_existing_jsonc(self):
        xdg = self.root / "xdg"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
            selection = replace(self.selection, destination=None, home=self.root / "h")
            config, skills, receipt = selection.paths()
            self.assertEqual(config, xdg / "opencode" / "opencode.json")
            self.assertEqual(skills, xdg / "opencode" / "skills")
            self.assertEqual(receipt, xdg / "opencode" / "agent-braid-receipts" / "agent-braid.json")
            (xdg / "opencode").mkdir(parents=True)
            (xdg / "opencode" / "opencode.jsonc").write_text("{}\n")
            self.assertEqual(selection.paths()[0].name, "opencode.jsonc")

    def test_user_paths_default_to_home_config(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XDG_CONFIG_HOME", None)
            home = self.root / "h"
            selection = replace(self.selection, destination=None, home=home)
            self.assertEqual(selection.paths()[0], home / ".config" / "opencode" / "opencode.json")
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": "relative/dir"}):
            self.assertEqual(selection.paths()[0], home / ".config" / "opencode" / "opencode.json")

    def test_project_paths(self):
        selection = replace(self.selection, scope="project", destination=None)
        config, skills, receipt = selection.paths()
        self.assertEqual(config, self.source / "opencode.json")
        self.assertEqual(skills, self.source / ".opencode" / "skills")
        self.assertEqual(receipt, self.source / ".opencode" / "agent-braid-receipts" / "agent-braid.json")
        (self.source / "opencode.jsonc").write_text("{}\n")
        self.assertEqual(selection.paths()[0], self.source / "opencode.jsonc")
        self.transact(selection=selection)
        self.assertTrue((self.source / ".opencode" / "skills" / "agent-braid-plan" / "SKILL.md").is_file())

    def test_ambiguous_pair_refuses_and_names_both_paths(self):
        for selection in (self.selection, replace(self.selection, scope="project", destination=None)):
            base = selection.destination or self.source
            (base / "opencode.json").parent.mkdir(parents=True, exist_ok=True)
            (base / "opencode.json").write_text("{}\n")
            (base / "opencode.jsonc").write_text("{}\n")
            with self.assertRaises(InstallationRefused) as caught:
                self.plan(selection=selection)
            self.assertEqual(caught.exception.code, "ambiguous_configuration")
            self.assertIn(str(base / "opencode.json"), str(caught.exception))
            self.assertIn(str(base / "opencode.jsonc"), str(caught.exception))
            self.assertEqual((base / "opencode.json").read_text(), "{}\n")


class RefusalTests(Base):
    def refused(self, operation="install", **kwargs):
        with self.assertRaises(InstallationRefused) as caught:
            self.plan(operation, **kwargs)
        return caught.exception

    def test_invalid_configuration_codes(self):
        for text in ('{"mcp": {', "[]", '{"mcp": []}', '{"mcp": null}', '{"a": 1 /* open', '{"a": 1, "a": 2}',
                     '{"a": NaN}', '{"a" 1}', b"\xef\xbb\xbf{}"):
            with self.subTest(text=text):
                self.write_config(text)
                error = self.refused()
                self.assertEqual(error.code, "invalid_configuration")
                self.assertTrue(str(error).startswith("invalid_configuration:"))
        self.write_config(b"\xff\xfe")
        self.assertEqual(self.refused().code, "invalid_configuration")

    def test_unowned_server_collision_is_not_overwritten(self):
        original = '{"mcp": {"agent-braid": {"type": "remote", "url": "https://x.test"}}} // mine\n'
        self.write_config(original)
        error = self.refused()
        self.assertEqual(error.code, "unowned_collision")
        self.assertEqual(error.diagnostic["scope"], "opencode_jsonc_server_entry")
        self.assertEqual(error.diagnostic["comparison"]["ownership"], "unowned")
        self.assertNotIn("x.test", json.dumps(error.diagnostic))
        self.assertEqual(self.config.read_text(), original)
        self.assertFalse(self.skills.exists())

    def test_unowned_skill_is_not_overwritten(self):
        skill = self.skills / "agent-braid-analyze" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("mine")
        error = self.refused()
        self.assertEqual(error.code, "unowned_collision")
        self.assertEqual(error.diagnostic["scope"], "skill_asset")
        self.assertEqual(skill.read_text(), "mine")
        self.assertFalse(self.config.exists())

    def test_shared_skill_directory_is_not_adopted(self):
        directory = self.skills / "agent-braid-plan"
        directory.mkdir(parents=True)
        (directory / "notes.txt").write_text("mine")
        self.assertEqual(self.refused().code, "unowned_collision")

    def test_modified_owned_entry_and_skill_refuse_with_changed_digest(self):
        self.write_config(COMMENTED)
        self.transact()
        installed = self.config.read_text()
        self.write_config(installed.replace('"codemode": false', '"codemode": true'))
        error = self.refused("update")
        self.assertEqual(error.code, "changed_digest")
        self.assertEqual(error.diagnostic["comparison"]["ownership"], "owned_but_modified")
        self.write_config(installed)
        skill = self.skills / "agent-braid-plan" / "SKILL.md"
        skill.write_text("edited")
        error = self.refused("update")
        self.assertEqual(error.code, "changed_digest")
        self.assertEqual(error.diagnostic["scope"], "skill_asset")

    def test_modified_entry_is_retained_by_uninstall(self):
        self.transact()
        modified = self.config.read_text().replace('"codemode": false', '"codemode": true')
        self.write_config(modified)
        transaction = self.plan("uninstall")
        self.assertIn("modified server entry retained", transaction.summary["residuals"])
        apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        self.assertEqual(self.config.read_text(), modified)

    def test_change_after_preview_refuses_and_writes_nothing(self):
        self.write_config(COMMENTED)
        transaction = self.plan()
        edited = COMMENTED.replace("// foreign server", "// changed")
        self.write_config(edited)
        with self.assertRaises(InstallationRefused) as caught:
            apply(transaction, preview_digest=transaction.preview()["previewDigest"])
        self.assertEqual(caught.exception.code, "changed_digest")
        self.assertEqual(caught.exception.diagnostic["scope"], "opencode_jsonc_server_entry")
        self.assertEqual(self.config.read_text(), edited)
        self.assertFalse(self.skills.exists())
        self.assertFalse((self.destination / ".agent-braid-install.lock").exists())

    def test_failed_write_rolls_back_without_partial_files(self):
        self.write_config(COMMENTED)
        for failing in range(len(self.plan().changes)):
            transaction = self.plan()

            def fault(index, path, failing=failing):
                if index == failing:
                    raise OSError("injected write failure")
            with self.assertRaises(OSError):
                apply(transaction, preview_digest=transaction.preview()["previewDigest"], fault=fault)
            self.assertEqual(self.config.read_text(), COMMENTED)
            self.assertFalse(list(self.skills.glob("**/SKILL.md")) if self.skills.exists() else False)
            self.assertFalse(self.receipt.exists())
            leftovers = [p.name for p in self.destination.rglob("*") if p.name.startswith(".opencode.json.braid-")
                         and "backup" not in p.name]
            self.assertEqual(leftovers, [])
            self.assertFalse((self.destination / ".agent-braid-install.lock").exists())

    def test_failed_write_after_first_change_restores_it(self):
        transaction = self.plan()
        self.assertGreater(len(transaction.changes), 2)

        def fault(index, path):
            if index == 2:
                raise OSError("injected")
        with self.assertRaises(OSError):
            apply(transaction, preview_digest=transaction.preview()["previewDigest"], fault=fault)
        self.assertFalse(self.config.exists())
        self.assertEqual([p for p in self.destination.rglob("*") if p.is_file() and "backup" not in p.name], [])


class NativePluginTests(Base):
    SPEC = "github:jayanez/agent-braid#v0.1.0::path:plugins/agent-braid"

    def test_detection_is_conservative(self):
        yes = ['{"plugins": ["%s"]}' % self.SPEC, '{"plugins": [["%s", {}]], "plugin": ["x"]}' % self.SPEC,
               '{"plugin": ["%s"]}' % self.SPEC, '{"plugin": [["agent-braid@1.2.3", {}]]}', '{"plugin": ["agent-braid"]}',
               '{"plugin": ["file:///opt/x/plugins/agent-braid",]} // c']
        no = ['{}', '{"plugin": []}', '{"plugin": ["some-agent-braid-fork"]}', '{"plugin": ["x/plugins/agent-braid-fork"]}', '{"plugin": "agent-braid"}', '{"plugins": "agent-braid"}',
              '{"plugin": [1, null, {"a": "agent-braid"}]}', '{"mcp": {"agent-braid": {}}}']
        for text in yes:
            self.assertTrue(native_plugin_configured(text.encode()), text)
        for text in no:
            self.assertFalse(native_plugin_configured(text.encode()), text)
        self.assertFalse(native_plugin_configured(None))

    def test_preview_warns_and_apply_proceeds_only_as_previewed(self):
        self.write_config('{"plugin": ["%s"]}\n' % self.SPEC)
        transaction = self.plan()
        warning = transaction.preview()["warnings"][0]
        self.assertEqual((warning["code"], warning["serverName"]), ("native_plugin_shadowed", "agent-braid"))
        self.assertEqual(apply(transaction, preview_digest=transaction.preview()["previewDigest"])["status"], "applied")
        self.assertIn("warnings", self.plan("update").preview())
        self.assertNotIn("warnings", self.plan("uninstall").preview())

    def test_no_warning_without_plugin_entry_and_no_key_for_other_hosts(self):
        self.assertNotIn("warnings", self.plan().preview())

    def test_doctor_reports_shadowing(self):
        self.write_config('{"plugin": ["%s"]}\n' % self.SPEC)
        self.assertEqual(self.doctor()["checks"]["nativePlugin"]["code"], "native_plugin_shadowed")


class DoctorTests(Base):
    def test_doctor_checks_path_entry_and_skills(self):
        report = self.doctor()["checks"]
        self.assertEqual(report["host"]["status"], "present")
        self.assertEqual(report["ownedEntry"]["status"], "not-installed")
        self.assertEqual(report["configuration"]["status"], "pending")
        self.transact()
        report = self.doctor()["checks"]
        self.assertEqual((report["ownedEntry"]["status"], report["ownedSkills"]["status"]), ("ok", "ok"))
        self.assertEqual(report["nativePlugin"]["status"], "not-detected")
        self.assertEqual(report["telemetry"]["configuredMode"], "off")
        (self.skills / "agent-braid-plan" / "SKILL.md").write_text("edited")
        self.assertEqual(self.doctor()["checks"]["ownedSkills"]["status"], "modified")
        self.write_config(self.config.read_text().replace('"codemode": false', '"codemode": true'))
        self.assertEqual(self.doctor()["checks"]["ownedEntry"]["status"], "modified")

    def test_doctor_without_host_and_with_ambiguity(self):
        with patch.dict(os.environ, {"PATH": ""}):
            self.assertEqual(doctor(self.selection, source_checkout=True)["checks"]["host"]["status"], "unavailable")
        for name in ("opencode.json", "opencode.jsonc"):
            self.write_config("{}\n", self.destination / name)
        checks = self.doctor()["checks"]
        self.assertEqual(checks["configuration"]["code"], "ambiguous_configuration")
        self.assertEqual(checks["ownedEntry"]["code"], "ambiguous_configuration")

    def test_doctor_reports_invalid_configuration(self):
        self.write_config("{")
        self.assertEqual(self.doctor()["checks"]["configuration"]["status"], "unknown")


class ManifestAndMigrationTests(Base):
    def test_asset_provenance_accepts_the_new_host_list_only(self):
        record = asset_provenance(source_checkout=True)
        self.assertEqual(record["hostMetadata"]["hosts"], ["codex", "claude", "opencode"])
        self.assertEqual(record["hostMetadata"]["schema"], "agent-braid-host-assets/v0.1")
        real = Path(__file__).resolve().parents[1] / "integrations" / "agent-braid" / "hosts.json"
        for hosts in (["codex", "claude"], ["codex", "claude", "opencode", "x"]):
            tampered = json.loads(real.read_text())
            tampered["hosts"] = hosts
            with patch("pathlib.Path.read_bytes", lambda self, _t=json.dumps(tampered).encode(), _o=Path.read_bytes:
                       _t if self.name == "hosts.json" else _o(self)):
                with self.assertRaisesRegex(InstallationRefused, "host asset metadata is incompatible"):
                    asset_provenance(source_checkout=True)

    def test_migration_uses_the_opencode_receipt_and_keeps_modified_skills(self):
        self.write_config(COMMENTED)
        self.transact()
        found = plugin_legacy.inventory("opencode", self.destination)
        self.assertEqual([item["status"] for item in found["receipts"]], ["owned-selection"])
        skill = self.skills / "agent-braid-analyze" / "SKILL.md"
        skill.write_text("user modified instructions")
        preview = plugin_legacy.migrate("opencode", self.receipt, destination=self.destination, source_checkout=True)
        plugin_legacy.migrate("opencode", self.receipt, destination=self.destination, source_checkout=True,
                              do_apply=True, digest=preview["previewDigest"])
        self.assertEqual(skill.read_text(), "user modified instructions")
        self.assertEqual(self.config.read_text(), COMMENTED)
        self.assertEqual(json.loads(self.receipt.read_text())["state"], "residual")
        with self.assertRaises((plugin_legacy.RegistryError, InstallationRefused)):
            plugin_legacy.migrate("claude", self.receipt, destination=self.destination, source_checkout=True)

    def test_inventory_default_directory_follows_xdg(self):
        xdg = self.root / "xdg"
        with patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
            self.assertEqual(plugin_legacy.inventory("opencode"), {"receipts": [], "truncated": False})
            receipts = xdg / "opencode" / "agent-braid-receipts"
            receipts.mkdir(parents=True)
            (receipts / "x.json").write_text("{}")
            self.assertEqual(plugin_legacy.inventory("opencode")["receipts"][0]["status"], "unavailable; inspect without adopting")


class CliTests(Base):
    def run_cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["tooling", *arguments, "--host", "opencode", "--scope", "user",
                         "--source-root", str(self.source), "--result-root", str(self.results),
                         "--destination", str(self.destination), "--source-checkout-assets"])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_install_through_the_tooling_cli(self):
        code, out, _ = self.run_cli("install")
        self.assertEqual(code, 0)
        digest = json.loads(out)["previewDigest"]
        code, out, _ = self.run_cli("install", "--apply", "--preview-digest", digest)
        self.assertEqual((code, json.loads(out)["status"]), (0, "applied"))
        self.assertEqual(self.run_cli("uninstall")[0], 0)

    def test_refusal_record_carries_the_code(self):
        self.write_config("[]")
        code, _, err = self.run_cli("install")
        self.assertEqual(code, 2)
        self.assertIn("invalid_configuration", err)
        self.write_config('{"mcp": {"agent-braid": {}}}')
        code, _, err = self.run_cli("install")
        record = json.loads(err)
        self.assertEqual((code, record["code"], record["diagnostic"]["scope"]),
                         (2, "unowned_collision", "opencode_jsonc_server_entry"))

    def test_plugin_legacy_accepts_opencode(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout), patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.root / "xdg")}):
            code = main(["plugin", "legacy", "--home", str(self.root / "plugin-home"), "--host", "opencode"])
        self.assertEqual(code, 0)


class JsoncScannerTests(unittest.TestCase):
    SAMPLES = ['{}', ' {"a": 1}', '{"a": 1, "b": {"c": [1, 2, {"d": "x"}]}, "e": "q\\"}"}',
               '{\n  "a" : "//", "b":"/*"\n,"c": null }']

    def test_member_spans_match_the_strict_scanner(self):
        for text in self.SAMPLES:
            self.assertEqual(jsonc.members(jsonc.clean(text).text), _members(text), text)

    def test_clean_keeps_offsets_and_strings(self):
        text = '{"a": "x//y" /* c */, // l\n "b": "/*z*/", /* m\nn */ "c": [1,2,],}'
        cleaned = jsonc.clean(text)
        self.assertEqual(len(cleaned.text), len(text))
        self.assertEqual(cleaned.text.count("\n"), text.count("\n"))
        self.assertEqual(json.loads(cleaned.text), {"a": "x//y", "b": "/*z*/", "c": [1, 2]})
        self.assertEqual(jsonc.parse(text), {"a": "x//y", "b": "/*z*/", "c": [1, 2]})
        self.assertEqual(len(cleaned.trailing), 2)
        opening, closing, found = jsonc.members(cleaned.text)
        self.assertEqual([m[0] for m in found], ["a", "b", "c"])
        self.assertEqual(text[found[1][2]:found[1][3]], '"/*z*/"')

    def test_errors(self):
        for text in ('{"a": "x', '{"a": 1 /* x', '{"a": 1,, }', '{,}', '[1,', '{"a": 1} x', '{"a": 1, "a": 2}'):
            with self.assertRaises(jsonc.JsoncError, msg=text):
                jsonc.parse(text)
        with self.assertRaises(jsonc.JsoncError):
            jsonc.members("[]")
        with self.assertRaises(jsonc.JsoncError):
            jsonc.members('{"a": 1')

    def test_public_api(self):
        self.assertEqual(sorted(name for name in vars(jsonc) if not name.startswith("_") and callable(getattr(jsonc, name))
                                and getattr(getattr(jsonc, name), "__module__", "") == "agent_braid.jsonc"),
                         ["Cleaned", "JsoncError", "clean", "members", "parse"])


if __name__ == "__main__":
    unittest.main()
