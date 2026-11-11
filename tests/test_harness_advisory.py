# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T010 controls: the versioned advisory CLI is read-only, bound and bounded."""
from contextlib import redirect_stderr, redirect_stdout
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

from agent_braid import harness_advisory as adv
from agent_braid import harness_cli
from agent_braid import harness_promotion as promotion
from agent_braid.system_one import canonical
from tests.test_harness_cli import active_registry
from tests.test_harness_components import _compile, file_row, make_inventory
from tests.test_harness_promotion import SCOPE

CONTRACT = Path(__file__).resolve().parents[1] / "specs/050-braid-harness-adaptation/contracts/advisory.md"


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        try:
            code = adv.main([*map(str, argv)])
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    return code, (json.loads(text) if text.startswith("{") else text)


class Workspace(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.work = self.root / "work"
        self.work.mkdir()

    def put(self, name, data, base=None) -> Path:
        path = (base or self.work) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data if isinstance(data, bytes) else canonical(data))
        return path

    def profile(self, name, entries=None, **over):
        return self.put(name, _compile(make_inventory(entries, **over)).canonical_bytes)

    def tree(self):
        return sorted((p.relative_to(self.root).as_posix(), p.stat().st_mtime_ns,
                       p.read_bytes() if p.is_file() else None) for p in self.root.rglob("*"))

    def ok(self, *argv):
        code, out = run(*argv)
        self.assertEqual((code, out["status"]), (0, "ok"), out)
        self.assertIs(out["executionAuthorization"], False)
        self.assertIs(out["advisory"], True)
        self.assertEqual(out["contract"], "braid-harness-advisory/v0.1")
        return out

    def refused(self, *argv, reason=None):
        code, out = run(*argv)
        self.assertEqual(code, 2, out)
        self.assertEqual(set(out), {"contract", "status", "reason", "executionAuthorization",
                                    "advisory"})
        self.assertEqual((out["status"], out["executionAuthorization"]), ("refused", False))
        self.assertRegex(out["reason"], r"^[a-z][a-z-]{0,47}\Z")
        if reason:
            self.assertEqual(out["reason"], reason)
        return out


class CapabilityTests(Workspace):
    def test_capabilities_inventory_and_non_changes(self):
        before = self.tree()
        out = self.ok("capabilities", "--workspace", self.work)
        self.assertEqual(out["result"]["supportedContractVersions"], ["v0.1"])
        classes = {c["class"]: c for c in out["result"]["componentClasses"]}
        self.assertEqual(sorted(classes), [f"C{i}" for i in range(1, 9)])
        self.assertEqual(classes["C1"]["admission"], "implemented")
        for blocked in ("C3", "C6", "C7", "C8"):
            self.assertEqual(classes[blocked]["admission"], "blocked")
        self.assertEqual(out["result"]["hosts"]["codex"]["qualification"], "unqualified")
        self.assertEqual(out["result"]["pluginOrMcpSurface"], "unchanged")
        self.assertEqual(out["result"]["effects"], "none")
        self.assertTrue(out["result"]["providerLimitations"])
        self.assertEqual(out["workspace"]["bound"], True)
        self.assertEqual(self.tree(), before)

    def test_workspace_binding_is_required_and_real(self):
        code, out = run("capabilities")
        self.assertEqual((code, out.startswith("{")), (2, False))
        self.refused("capabilities", "--workspace", self.root / "missing", reason="workspace-invalid")
        self.refused("capabilities", "--workspace", self.put("f.json", b"{}"),
                     reason="workspace-invalid")

    def test_unsupported_contract_versions_refuse(self):
        self.ok("capabilities", "--workspace", self.work, "--contract-version", "v0.1")
        for version in ("v0.2", "v1.0", "0.1", "v0.1 ", ""):
            self.refused("capabilities", "--workspace", self.work, "--contract-version", version,
                         reason="unsupported-version")


class ProfileTests(Workspace):
    def test_inventory_lists_components_and_admission(self):
        path = self.profile("p.json", [file_row("guidance/a.md", b"a"), file_row("guidance/b.md", b"bb")])
        before = self.tree()
        out = self.ok("profile-inventory", "--workspace", self.work, "--profile", path)
        result = out["result"]
        self.assertEqual([f["path"] for f in result["files"]], ["guidance/a.md", "guidance/b.md"])
        self.assertEqual(result["admission"], {"state": "implemented", "blocker": None})
        self.assertEqual(result["hostSupport"]["claude"]["qualification"], "unqualified")
        self.assertEqual(result["authenticity"], "unverified")
        self.assertEqual(self.tree(), before)
        trusted = sha256(path.read_bytes()).hexdigest()
        out = self.ok("profile-inventory", "--workspace", self.work, "--profile", path,
                      "--sha256", trusted)
        self.assertEqual(out["result"]["authenticity"], "hash-matched")
        self.refused("profile-inventory", "--workspace", self.work, "--profile", path,
                     "--sha256", "f" * 64, reason="profile-drift")

    def test_diff_reports_added_removed_modified(self):
        base = self.profile("b.json", [file_row("guidance/a.md", b"a"), file_row("guidance/b.md", b"b")])
        cand = self.profile("c.json", [file_row("guidance/a.md", b"A"), file_row("guidance/c.md", b"c")])
        out = self.ok("profile-diff", "--workspace", self.work, "--base", base, "--candidate", cand)
        diff = out["result"]["files"]
        self.assertEqual((diff["added"], diff["removed"], diff["modified"]),
                         (["guidance/c.md"], ["guidance/b.md"], ["guidance/a.md"]))
        self.assertFalse(out["result"]["identical"])
        same = self.ok("profile-diff", "--workspace", self.work, "--base", base, "--candidate", base)
        self.assertTrue(same["result"]["identical"])

    def test_invalid_future_and_escalated_profiles_refuse(self):
        good = _compile(make_inventory()).to_dict()
        future = dict(good, format="braid-harness-profile/v0.2")
        self.refused("profile-inventory", "--workspace", self.work,
                     "--profile", self.put("f.json", future), reason="unsupported-version")
        auth = dict(good, executionAuthorization=True)
        self.refused("profile-inventory", "--workspace", self.work,
                     "--profile", self.put("a.json", auth), reason="unsupported-profile")
        self.refused("profile-inventory", "--workspace", self.work,
                     "--profile", self.put("g.json", b"{"), reason="invalid-json")

    def test_error_text_never_echoes_paths_or_content(self):
        secret = self.put("sensitive-name.json", b'{"token": "TOPSECRET"')
        code, out = run("profile-inventory", "--workspace", self.work, "--profile", secret)
        self.assertEqual((code, out["status"]), (2, "refused"))
        text = json.dumps(out)
        self.assertNotIn("TOPSECRET", text)
        self.assertNotIn("sensitive-name", text)
        self.assertNotIn(str(self.root), text)


class ExtraTests(Workspace):
    def test_hash_and_file_kind_refusals(self):
        path = self.profile("p.json")
        for bad in ("F" * 64, "abc"):
            self.refused("profile-inventory", "--workspace", self.work, "--profile", path,
                         "--sha256", bad, reason="invalid-hash")
        (self.work / "d").mkdir()
        self.refused("profile-inventory", "--workspace", self.work, "--profile", self.work / "d",
                     reason="input-unreadable")

    def test_diff_changed_fields_and_sibling_prefix(self):
        base = self.profile("b.json", [file_row("guidance/a.md", b"a")])
        cand = self.profile("c.json", [file_row("guidance/a.md", b"a")], version=1, effectClass="E1")
        out = self.ok("profile-diff", "--workspace", self.work, "--base", base, "--candidate", cand)
        self.assertEqual(out["result"]["changedFields"], ["effectClass"])
        evil = self.root / "work-evil"
        evil.mkdir()
        sibling = self.put("p.json", base.read_bytes(), base=evil)
        self.refused("profile-inventory", "--workspace", self.work, "--profile", sibling,
                     reason="outside-workspace")

    def test_evidence_anomaly_checked_without_evidence(self):
        spec = self.work / "s"
        self.put("tasks.md", b"- [x] T001 done\n", base=spec)
        (spec / "evidence").mkdir()
        out = self.ok("evidence", "--workspace", self.work, "--spec-dir", spec)
        self.assertEqual(out["result"]["anomalies"],
                         [{"kind": "checked-without-evidence", "subject": "T001"}])


class BindingTests(Workspace):
    def test_inputs_outside_the_workspace_refuse(self):
        outside = self.profile("p.json")
        outside = self.put("p.json", outside.read_bytes(), base=self.root / "elsewhere")
        self.refused("profile-inventory", "--workspace", self.work, "--profile", outside,
                     reason="outside-workspace")
        self.refused("profile-inventory", "--workspace", self.work,
                     "--profile", self.work / ".." / "elsewhere" / "p.json",
                     reason="outside-workspace")

    def test_symlink_escape_refuses(self):
        outside = self.put("p.json", _compile(make_inventory()).canonical_bytes,
                           base=self.root / "elsewhere")
        link = self.work / "link.json"
        os.symlink(outside, link)
        self.refused("profile-inventory", "--workspace", self.work, "--profile", link,
                     reason="outside-workspace")
        directory = self.work / "dirlink"
        os.symlink(outside.parent, directory)
        self.refused("profile-inventory", "--workspace", self.work,
                     "--profile", directory / "p.json", reason="outside-workspace")

    def test_workspace_identity_differs_per_workspace(self):
        other = self.root / "other"
        other.mkdir()
        first = self.ok("capabilities", "--workspace", self.work)["workspace"]["id"]
        second = self.ok("capabilities", "--workspace", other)["workspace"]["id"]
        self.assertNotEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}\Z")


class StatusEvidenceTests(Workspace):
    def test_status_reports_registry_without_activation(self):
        registry = active_registry()
        path = self.put("registry.json", registry.to_bytes())
        out = self.ok("status", "--workspace", self.work, "--registry", path)
        self.assertEqual(out["result"]["sha256"], registry.sha256)
        self.assertEqual(out["result"]["automaticPromotion"], promotion.AUTOMATIC_PROMOTION)
        self.refused("status", "--workspace", self.work,
                     "--registry", self.put("bad.json", b"{"), reason="invalid-json")
        empty = self.put("e.json", promotion.ProfileRegistry.empty(SCOPE).to_bytes())
        self.assertIsNone(self.ok("status", "--workspace", self.work,
                                  "--registry", empty)["result"]["active"])

    def test_evidence_inventory_and_containment(self):
        spec = self.work / "spec"
        self.put("tasks.md", b"- [x] T001 done\n- [ ] T002 open\n", base=spec)
        self.put("evidence/t001.json", {"task": "T001", "executionAuthorization": False}, base=spec)
        out = self.ok("evidence", "--workspace", self.work, "--spec-dir", spec)
        self.assertEqual([t["id"] for t in out["result"]["tasks"]], ["T001", "T002"])
        self.assertEqual(out["result"]["anomalies"], [])
        self.refused("evidence", "--workspace", self.work, "--spec-dir", self.root,
                     reason="outside-workspace")
        self.refused("evidence", "--workspace", self.work, "--spec-dir", self.work / "nope",
                     reason="input-unreadable")


class SurfaceTests(unittest.TestCase):
    def test_module_adds_no_execution_or_plugin_surface(self):
        source = Path(adv.__file__).read_text()
        for forbidden in ("subprocess", "socket", "urllib", "http", "mcp_server", "plugin_cli",
                          "os.system", "shutil"):
            self.assertNotIn(forbidden, source)
        self.assertNotRegex(source, r"open\([^)]*[\"'][wax]")

    def test_top_level_cli_gains_no_command(self):
        from agent_braid import cli
        self.assertNotIn("harness_advisory", Path(cli.__file__).read_text())

    def test_laboratory_cli_is_untouched_and_not_extended(self):
        self.assertNotIn("harness-advisory", Path(harness_cli.__file__).read_text())

    def test_reasons_are_bounded_and_unknown_codes_collapse(self):
        self.assertEqual(adv.bound_reason("profile-drift"), "profile-drift")
        for raw in ("/etc/passwd", "Has Space", "x" * 80, 3, None, ""):
            self.assertEqual(adv.bound_reason(raw), "refused")

    def test_contract_document_states_versioned_limits(self):
        text = CONTRACT.read_text()
        for required in ("braid-harness-advisory/v0.1", "executionAuthorization", "v0.2",
                         "provider", "separate explicit adoption", "unchanged"):
            self.assertIn(required, text)
        for command in adv.COMMANDS:
            self.assertIn(f"`{command}`", text)
        self.assertRegex(text, re.compile(r"migrat", re.I))


if __name__ == "__main__":
    unittest.main()
