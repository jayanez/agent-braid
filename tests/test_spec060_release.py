# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-060 T008 release preparation: version, v0.2 verifier, migration and rollback.

Nothing here installs from or publishes to an index. The "earlier package" is a
fixture: the candidate registry reduced to the v0.1 roster (the three
``agent-braid-*`` prompts, no deprecation marking), driven through the real
registry functions. It is not a download of a published wheel.
"""
from __future__ import annotations

import asyncio
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import types
import unittest
from unittest.mock import patch

from agent_braid import __version__, tooling_mcp
from agent_braid.tooling_install import Selection, apply, plan
from agent_braid.tooling_mcp import ToolingError

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


v01 = _load("verify_installed_tooling_v01_for_spec060", "scripts/verify_installed_tooling.py")
v02 = _load("verify_installed_tooling_v2_for_spec060", "scripts/verify_installed_tooling_v2.py")

CANONICAL = ["analyze", "plan", "evidence"]
ALIASES = ["agent-braid-analyze", "agent-braid-plan", "agent-braid-evidence"]
OLD_VERIFIER_SHA256 = "e88e030718c87fb080f091e7179636e02d416b48a85e2353a00928eecf1ce431"


def earlier_registry() -> tuple:
    """The v0.1 roster: prefixed names only, same texts, no replacement marking."""
    return tuple(tooling_mcp._Prompt(p.name, p.text) for p in tooling_mcp._PROMPTS if p.replaced_by)


class FakePromptClient:
    """SDK-shaped client whose prompt answers come from the real registry functions."""

    def __init__(self, params, mode):
        self.params = params
        self.protocol_version = "2026-07-28" if mode == "auto" else "2025-11-25"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        status = Path(json.loads(Path(self.params.args[2]).read_text())["status"])
        status.write_text(json.dumps({"returnCode": 0, "interrupted": False,
                                      "forcedTermination": None, "reaped": True, "trace": {}}))

    async def list_tools(self):
        return types.SimpleNamespace(tools=[types.SimpleNamespace(name=n)
                                            for n in ("analyze", "analyze-work", "prepare")])

    async def call_tool(self, _name, arguments):
        envelope = {"status": "ok", "result": {"report": {"ok": 1},
                                               "provenance": {"executionAuthorization": False}}}
        if arguments["request"] == {}:
            return types.SimpleNamespace(structured_content={"status": "refused"}, is_error=True)
        return types.SimpleNamespace(structured_content=envelope, is_error=False,
                                     content=[types.SimpleNamespace(text=json.dumps(envelope))])

    async def list_resources(self):
        return types.SimpleNamespace(resources=[types.SimpleNamespace(uri="agent-braid://capabilities")])

    async def read_resource(self, _uri):
        capabilities = {"mode": "analysis-only", "prompts": CANONICAL,
                        "deprecatedPrompts": [{"name": n, "replacedBy": n.removeprefix("agent-braid-"),
                                               "removedIn": "agent-braid-tooling/v0.3"} for n in ALIASES]}
        return types.SimpleNamespace(contents=[types.SimpleNamespace(text=json.dumps(capabilities))])

    async def list_prompts(self):
        return types.SimpleNamespace(prompts=[types.SimpleNamespace(name=n, description=d)
                                              for n, d in tooling_mcp._prompt_listing()])

    async def get_prompt(self, name):
        description, text = tooling_mcp._prompt_get(name)
        return types.SimpleNamespace(description=description, messages=[
            types.SimpleNamespace(content=types.SimpleNamespace(text=text))])


class FakeParameters:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def run_probe(verifier, root: Path):
    """Execute the verifier's generated child program against the fake client."""
    config = root / "relay-config.json"
    config.write_text(json.dumps({"status": "unset", "traces": {}}))
    code = verifier._sdk_probe_code(root / "relay.py", config, root, root, root, {"PATH": "/bin"},
                                    {"analysisInputVersion": "fixture", "operations": []})
    compile(code, "sdk-probe.py", "exec")
    mcp = types.ModuleType("mcp")
    mcp.Client = FakePromptClient
    stdio = types.ModuleType("mcp.client.stdio")
    stdio.StdioServerParameters = FakeParameters
    output = io.StringIO()
    modules = {"mcp": mcp, "mcp.client": types.ModuleType("mcp.client"), "mcp.client.stdio": stdio}
    with patch.dict(sys.modules, modules), contextlib.redirect_stdout(output):
        exec(compile(code, "sdk-probe.py", "exec"), {"__name__": "sdk_probe_test"})
    return json.loads(output.getvalue())["sessions"]


class PackageVersionTests(unittest.TestCase):
    def test_package_version_is_the_candidate_everywhere_it_is_declared(self):
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        self.assertEqual("0.1.0a2", pyproject["project"]["version"])
        self.assertEqual("0.1.0a2", __version__)
        self.assertEqual("0.1.0a2", v02.CANDIDATE_VERSION)
        self.assertIn("package version is `0.1.0a2`", (ROOT / "README.md").read_text())

    def test_plugin_release_identity_is_not_bumped(self):
        builder = (ROOT / "scripts/build_native_plugin.py").read_text()
        self.assertRegex(builder, r"(?m)^VERSION = '0\.1\.0-alpha\.4'$")

    def test_host_asset_metadata_is_not_tied_to_the_package_version(self):
        value = json.loads((ROOT / "integrations/agent-braid/hosts.json").read_text())
        self.assertEqual("agent-braid-host-assets/v0.1", value["schema"])
        self.assertEqual("0.1.0a1", value["version"])  # asset-metadata version; changes only with host assets


class InstalledVerifierV2Tests(unittest.TestCase):
    def test_old_verifier_is_unchanged_and_v2_does_not_modify_the_file(self):
        digest = hashlib.sha256((ROOT / "scripts/verify_installed_tooling.py").read_bytes()).hexdigest()
        self.assertEqual(OLD_VERIFIER_SHA256, digest)

    def test_v2_accepts_the_v02_roster_with_marked_aliases_in_both_modes(self):
        with tempfile.TemporaryDirectory() as temporary:
            sessions = run_probe(v02, Path(temporary))
        self.assertEqual(["auto", "legacy"], [row["mode"] for row in sessions])
        self.assertEqual([6, 6], [row["promptCount"] for row in sessions])

    def test_v2_rejects_the_v01_roster_unmarked_aliases_and_missing_names(self):
        cases = {
            "v0.1 roster": earlier_registry(),
            "missing canonical": tuple(p for p in tooling_mcp._PROMPTS if p.name != "plan"),
            "alias not marked": tuple(tooling_mcp._Prompt(p.name, p.text) if p.replaced_by else p
                                      for p in tooling_mcp._PROMPTS),
        }
        for label, registry in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as temporary, \
                    patch.object(tooling_mcp, "_PROMPTS", registry):
                with self.assertRaises(RuntimeError):
                    run_probe(v02, Path(temporary))

    def test_v2_rejects_missing_deprecated_prompts_capability_and_missing_removal_contract(self):
        async def bare(_self, _uri):
            return types.SimpleNamespace(contents=[types.SimpleNamespace(text="analysis-only")])

        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(FakePromptClient, "read_resource", bare), self.assertRaisesRegex(RuntimeError, "deprecatedPrompts"):
            run_probe(v02, Path(temporary))
        listing = tooling_mcp._prompt_listing()
        stripped = [(n, d.replace("agent-braid-tooling/v0.3", "later")) for n, d in listing]
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(tooling_mcp, "_prompt_listing", return_value=stripped), \
                self.assertRaisesRegex(RuntimeError, "removal contract"):
            run_probe(v02, Path(temporary))

    def test_old_verifier_logic_rejects_v02_and_accepts_the_earlier_roster(self):
        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(RuntimeError, "prompt roster"):
            run_probe(v01, Path(temporary))
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(tooling_mcp, "_PROMPTS", earlier_registry()):
            sessions = run_probe(v01, Path(temporary))
        self.assertEqual([3, 3], [row["promptCount"] for row in sessions])

    def test_v2_adapter_refuses_when_the_v01_probe_layout_changes(self):
        with patch.object(v02, "_V01_PROMPT_BLOCK", "not present in the generated program"):
            with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(v02.ProbeError, "refuses to guess"):
                run_probe(v02, Path(temporary))

    def test_v2_candidate_metadata_pins_the_new_version_and_the_old_one_is_refused(self):
        import zipfile
        for version, accepted in (("0.1.0a2", True), ("0.1.0a1", False)):
            with self.subTest(version), tempfile.TemporaryDirectory() as temporary:
                wheel = Path(temporary) / f"agent_braid-{version}-py3-none-any.whl"
                metadata = "\n".join(["Metadata-Version: 2.4", "Name: agent-braid", f"Version: {version}",
                                      "Provides-Extra: tooling", "Requires-Dist: mcp==2.3.0; extra == 'tooling'", "", ""])
                with zipfile.ZipFile(wheel, "w") as archive:
                    archive.writestr(f"agent_braid-{version}.dist-info/METADATA", metadata)
                digest = hashlib.sha256(wheel.read_bytes()).hexdigest()
                if accepted:
                    self.assertEqual(version, v02.candidate_metadata(wheel, digest)["version"])
                else:
                    with self.assertRaisesRegex(v02.ProbeError, "identity mismatch"):
                        v02.candidate_metadata(wheel, digest)
                # The unchanged v0.1 verifier keeps its own pin.
                if accepted:
                    with self.assertRaisesRegex(v01.ProbeError, "identity mismatch"):
                        v01.candidate_metadata(wheel, digest)


class MigrationAndRollbackTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        (self.root / "source").mkdir()
        (self.root / "results").mkdir()
        self.selections = [Selection(host=host, scope="user", source_root=self.root / "source",
                                     result_root=self.root / "results", home=self.root / f"{host} home",
                                     destination=self.root / f"{host} host") for host in ("codex", "claude")]

    def install(self, selection):
        transaction = plan(selection, source_checkout=True)
        return apply(transaction, preview_digest=transaction.preview()["previewDigest"])

    def snapshot(self, selection):
        config, skills, receipt = selection.paths()
        files = {str(p.relative_to(selection.destination)): p.read_bytes()
                 for p in sorted(selection.destination.rglob("*")) if p.is_file()}
        self.assertIn(config.relative_to(selection.destination).as_posix(), files)
        self.assertIn(receipt.relative_to(selection.destination).as_posix(), files)
        return files

    def test_upgrade_and_rollback_leave_host_configuration_and_receipt_byte_identical(self):
        for selection in self.selections:
            with self.subTest(host=selection.host):
                # Installer sources are byte-identical to the v0.1 package (SPEC-060 changes none).
                self.assertEqual("applied", self.install(selection)["status"])
                written = self.snapshot(selection)
                config = selection.paths()[0]
                self.assertNotRegex(config.read_text(), r"\banalyze\b\s*=\s*\"analyze\"")

                # Upgrade to the candidate: a repeat install and an update are no-ops.
                for operation in ("install", "update"):
                    transaction = plan(selection, operation=operation, source_checkout=True)
                    self.assertEqual([], transaction.changes)
                    report = apply(transaction, preview_digest=transaction.preview()["previewDigest"])
                    self.assertEqual("unchanged", report["status"])
                    self.assertEqual(written, self.snapshot(selection))

                # Rollback to the earlier package contents: the installer still sees nothing to change.
                with patch.object(tooling_mcp, "_PROMPTS", earlier_registry()):
                    transaction = plan(selection, operation="update", source_checkout=True)
                    self.assertEqual([], transaction.changes)
                self.assertEqual(written, self.snapshot(selection))

    def test_configuration_names_no_prompt_so_both_name_sets_follow_the_package_only(self):
        for selection in self.selections:
            config, _skills, receipt = selection.paths()
            self.install(selection)
            for path in (config, receipt):
                text = path.read_text()
                for name in CANONICAL:
                    self.assertNotRegex(text, rf"[\"']{name}[\"']")
                self.assertNotIn("deprecatedPrompts", text)

    def test_registered_server_resolves_both_name_sets_then_only_the_old_set_after_rollback(self):
        self.install(self.selections[0])
        # Candidate package: canonical names and aliases resolve with identical text; an unknown name is refused.
        for name in CANONICAL + ALIASES:
            _description, text = tooling_mcp._prompt_get(name)
            self.assertEqual(tooling_mcp._prompt_get(name.removeprefix("agent-braid-"))[1], text)
        with self.assertRaisesRegex(ToolingError, "Unknown prompt"):
            tooling_mcp._prompt_get("unknown")
        # Earlier package: the old names resolve, the new names are refused.
        with patch.object(tooling_mcp, "_PROMPTS", earlier_registry()):
            for name in ALIASES:
                tooling_mcp._prompt_get(name)
            for name in CANONICAL:
                with self.assertRaisesRegex(ToolingError, "Unknown prompt"):
                    tooling_mcp._prompt_get(name)
            self.assertEqual(ALIASES, [name for name, _ in tooling_mcp._prompt_listing()])

    @unittest.skipUnless(importlib.util.find_spec("mcp"), "optional tooling extra (mcp==2.3.0) is not installed")
    def test_server_started_from_the_written_configuration_lists_both_name_sets(self):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        selection = self.selections[0]
        self.install(selection)
        entry = tomllib.loads(selection.paths()[0].read_text())["mcp_servers"]["agent-braid"]

        async def listed():
            params = StdioServerParameters(command=entry["command"], args=entry["args"], cwd=str(ROOT))
            async with Client(params, mode="auto") as client:
                return [p.name for p in (await client.list_prompts()).prompts]

        self.assertEqual(CANONICAL + ALIASES, asyncio.run(listed()))


if __name__ == "__main__":
    unittest.main()
