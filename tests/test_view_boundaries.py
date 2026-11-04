# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T029 (REQ-013 / SC-013, procedure_013): boundary tests of the whole activity viewer.

The viewer is a read-only companion. These tests check, over the real modules, that no viewer module
reaches the ownership commands, that no viewer path sets `executionAuthorization` true, that the server
binds loopback only, that no viewer code lives in the plugin tree, that the plugin's report copies stay
private and local, and that the packaged bundle matches its manifest. The regression run of the
governance, plugin package and validation profile suites is the command of procedure_013 and is not
repeated here.
"""
import argparse
import ast
import hashlib
import os
import re
import stat
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path

from agent_braid import plugin_mcp, view_cli, view_loom
from agent_braid.view_serve import LOOPBACK_HOSTS, ServeError, ViewServer
from agent_braid.view_store import LoomStore
from agent_braid.view_tail import ArtifactTail
from scripts.validate_change import classify
from tests.test_view_packaging import load_build_support, vendor_manifest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "agent_braid"
WEB = ROOT / "integrations" / "agent-braid-view" / "web"
PLUGIN_TREE = ROOT / "integrations" / "agent-braid"
ARTIFACTS = ROOT / "tests" / "fixtures" / "view" / "artifacts"
VIEW_MODULES = sorted(PACKAGE.glob("view_*.py"))
OWNERSHIP_COMMANDS = ("expand-ownership", "check-ownership", "audit-isolation", "report-recovery")
NETWORK_MODULES = {"socket", "socketserver", "http", "urllib", "ssl", "ftplib", "smtplib", "requests", "asyncio"}
PLUGIN_ALLOWED = {"urllib", "asyncio"}  # plugin_mcp splits URLs and speaks MCP over stdio; it opens no connection
SERVER_MODULE = "view_serve.py"


def imported_modules(source):
    """First component of every imported module name; relative `from . import x` yields `x`."""
    found = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            found.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.add(node.module.split(".")[0])
            else:
                found.update(alias.name for alias in node.names)
    return found


def _is_false(node):
    """False itself, the module constant that is false (checked separately), or a tuple of those and strings."""
    if isinstance(node, ast.Constant):
        return node.value is False or isinstance(node.value, str)
    if isinstance(node, ast.Name):
        return node.id == "EXECUTION_AUTHORIZATION"
    return isinstance(node, ast.Tuple) and all(_is_false(item) for item in node.elts)


def non_false_authorizations(source):
    """Line numbers where a dict key, keyword or assignment gives `executionAuthorization` anything but false."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Dict):
            pairs = list(zip(node.keys, node.values))
        elif isinstance(node, ast.keyword):
            pairs = [(ast.Constant(value=node.arg), node.value)]
        elif isinstance(node, ast.Assign):
            pairs = [(target, node.value) for target in node.targets]
        else:
            continue
        for key, value in pairs:
            name = key.value if isinstance(key, ast.Constant) else getattr(key, "id", None)
            if name == "executionAuthorization" and not _is_false(value):
                lines.append(node.lineno)
    return lines


class OwnershipBoundaryTests(unittest.TestCase):
    def test_no_viewer_module_imports_ownership_or_names_its_commands(self):
        self.assertTrue(VIEW_MODULES)
        for path in VIEW_MODULES:
            source = path.read_text(encoding="utf-8")
            with self.subTest(path.name):
                self.assertFalse({"ownership", "ownership_cli", "path_overlap"} & imported_modules(source))
                for command in OWNERSHIP_COMMANDS:
                    self.assertNotIn(command, source)

    def test_only_the_dispatcher_and_the_ownership_cli_import_ownership(self):
        importers = {path.name for path in PACKAGE.glob("*.py")
                     if {"ownership", "ownership_cli"} & imported_modules(path.read_text(encoding="utf-8"))}
        self.assertEqual(importers, {"cli.py", "ownership_cli.py"})

    def test_the_web_bundle_names_no_ownership_command(self):
        for path in WEB.glob("*"):
            if path.is_file():
                for command in OWNERSHIP_COMMANDS:
                    self.assertNotIn(command, path.read_text(encoding="utf-8"), path.name)

    def test_the_import_scanner_sees_a_seeded_violation(self):
        self.assertEqual(imported_modules("from .ownership import x\nimport os"), {"ownership", "os"})
        self.assertEqual(imported_modules("from . import ownership"), {"ownership"})


class ExecutionAuthorizationTests(unittest.TestCase):
    def test_no_viewer_module_sets_execution_authorization_to_anything_but_false(self):
        for path in VIEW_MODULES:
            with self.subTest(path.name):
                self.assertEqual(non_false_authorizations(path.read_text(encoding="utf-8")), [])

    def test_the_web_bundle_never_sets_it_true(self):
        for path in WEB.glob("*"):
            if path.suffix in {".js", ".html"}:
                text = path.read_text(encoding="utf-8")
                self.assertIsNone(re.search(r"executionAuthorization[\"']?\s*[:=]\s*(true|1)\b", text), path.name)

    def test_every_event_the_artifact_watcher_emits_is_false(self):
        with tempfile.TemporaryDirectory() as directory:
            watched = Path(directory)
            for fixture in sorted(ARTIFACTS.glob("*.json")):
                (watched / fixture.name).write_bytes(fixture.read_bytes())
            store = LoomStore()
            ArtifactTail(store, [watched]).poll_once()
            events = store.replay()
        self.assertTrue(events)
        self.assertTrue(all(event["executionAuthorization"] is False for event in events))

    def test_the_shared_constant_is_false(self):
        self.assertIs(view_loom.EXECUTION_AUTHORIZATION, False)

    def test_the_scanner_sees_seeded_violations(self):
        self.assertEqual(non_false_authorizations('event = {"executionAuthorization": True}'), [1])
        self.assertEqual(non_false_authorizations("f(executionAuthorization=flag)"), [1])
        self.assertEqual(non_false_authorizations('event = {"executionAuthorization": False}'), [])


class LoopbackTests(unittest.TestCase):
    def test_only_the_server_module_imports_network_code(self):
        for path in VIEW_MODULES:
            with self.subTest(path.name):
                names = imported_modules(path.read_text(encoding="utf-8")) & NETWORK_MODULES
                if path.name == SERVER_MODULE:
                    self.assertTrue(names)
                else:
                    self.assertEqual(names, set())

    def test_the_server_refuses_every_non_loopback_host_and_binds_127_0_0_1(self):
        self.assertEqual(LOOPBACK_HOSTS, ("127.0.0.1", "::1"))
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory) / "run"
            for host in ("0.0.0.0", "", "::", "192.0.2.1", "localhost"):
                with self.subTest(host=host), self.assertRaises(ServeError):
                    ViewServer(LoomStore(), runtime, host=host)
            server = ViewServer(LoomStore(), runtime)
            try:
                self.assertEqual(server.server_address[0], "127.0.0.1")
                self.assertTrue(server.open_url.startswith("http://127.0.0.1:"))
            finally:
                server.server_close()

    def test_no_serve_option_chooses_the_bind_address(self):
        root = argparse.ArgumentParser()
        view_cli.add_parser(root.add_subparsers(dest="command", required=True))
        view = root._subparsers._group_actions[0].choices["view"]
        serve = view._subparsers._group_actions[0].choices["serve"]
        options = {option for action in serve._actions for option in action.option_strings}
        self.assertEqual(options, {"-h", "--help", "--replay", "--watch", "--no-discover", "--port", "--surface",
                                   "--runtime-dir", "--rotate-token"})
        for path in VIEW_MODULES:
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"[\"']0\.0\.0\.0[\"']", path.name)


class PluginTreeTests(unittest.TestCase):
    def test_no_viewer_code_lives_in_the_plugin_tree(self):
        files = [path for path in PLUGIN_TREE.rglob("*") if path.is_file()]
        self.assertTrue(files)
        for path in files:
            relative = path.relative_to(PLUGIN_TREE).as_posix()
            with self.subTest(relative):
                self.assertNotRegex(relative, r"(^|[/_-])(view|viewer|loom)([/_.-]|$)")
                self.assertNotIn(path.suffix, {".html", ".css", ".mjs"})
                if path.suffix in {".md", ".json", ".js"}:
                    text = path.read_text(encoding="utf-8")
                    for forbidden in ("agent_braid.view", "view_serve", "agent-braid view", "three.module"):
                        self.assertNotIn(forbidden, text)

    def test_the_viewer_bundle_is_a_separate_integration(self):
        self.assertTrue((WEB / "index.html").is_file())
        self.assertFalse((PLUGIN_TREE / "web").exists())


class ReportCopyTests(unittest.TestCase):
    def test_a_report_copy_has_private_modes_and_the_documented_retention_constants(self):
        self.assertEqual((plugin_mcp.REPORT_COPY_DAYS, plugin_mcp.REPORT_COPY_MAX_BYTES,
                          plugin_mcp.REPORT_COPY_MAX_COUNT), (30, 64 * 1024 * 1024, 1500))
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent).resolve() / "results"
            root.mkdir()
            os.chmod(root, 0o700)
            plugin_mcp.write_report_copy(root, root, b"{}", now=datetime(2026, 11, 3, tzinfo=timezone.utc))
            (copy,) = list(root.iterdir())
            self.assertEqual(stat.S_IMODE(copy.stat().st_mode), 0o700)
            self.assertEqual([item.name for item in copy.iterdir()], ["analysis.json"])
            self.assertEqual(stat.S_IMODE((copy / "analysis.json").stat().st_mode), 0o600)

    def test_a_result_root_open_to_others_gets_no_copy(self):
        with tempfile.TemporaryDirectory() as parent:
            root = Path(parent).resolve() / "results"
            root.mkdir()
            os.chmod(root, 0o755)
            with self.assertRaises((ValueError, plugin_mcp.RegistryError)):
                plugin_mcp.write_report_copy(root, root, b"{}")
            self.assertEqual(list(root.iterdir()), [])

    def test_the_plugin_opens_no_connection_and_reports_no_automatic_upload(self):
        source = (PACKAGE / "plugin_mcp.py").read_text(encoding="utf-8")
        self.assertIn("'automaticUpload': False", source)
        self.assertEqual(imported_modules(source) & (NETWORK_MODULES - PLUGIN_ALLOWED), set())
        for forbidden in ("urlopen", "HTTPConnection", "requests."):
            self.assertNotIn(forbidden, source)

    def test_the_privacy_statement_says_copies_are_never_uploaded(self):
        text = (ROOT / "docs" / "tooling" / "PLUGIN_PRIVACY.md").read_text(encoding="utf-8")
        self.assertIn("Copies are never uploaded", text)


class PackagedBundleTests(unittest.TestCase):
    def test_every_vendored_file_matches_its_manifest_hash_and_none_is_unlisted(self):
        manifest = vendor_manifest()
        vendor = WEB / "vendor"
        for relative, digest in manifest["files"].items():
            with self.subTest(relative):
                self.assertEqual(hashlib.sha256((vendor / relative).read_bytes()).hexdigest(), digest)
        present = {path.relative_to(vendor).as_posix() for path in (vendor / "three").rglob("*") if path.is_file()}
        self.assertEqual(present, set(manifest["files"]))

    def test_the_build_ships_exactly_the_source_bundle_files(self):
        build_support = load_build_support()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "agent_braid" / "view_assets" / "web"
            mapping = build_support.ToolingBuildPy._asset_mapping(types.SimpleNamespace(build_lib=directory))
            shipped = {Path(output).relative_to(destination).as_posix(): Path(source)
                       for output, source in mapping.items() if destination in Path(output).parents}
        expected = {path.relative_to(WEB).as_posix(): path for path in WEB.rglob("*") if path.is_file()
                    and not any(part.startswith(".") or part == "__pycache__" for part in path.relative_to(WEB).parts)}
        self.assertEqual(shipped, expected)
        for relative in vendor_manifest()["files"]:
            self.assertIn(f"vendor/{relative}", shipped)
        self.assertIn("vendor/manifest.json", shipped)


class ClassificationTests(unittest.TestCase):
    def test_every_viewer_code_test_asset_and_documentation_path_is_activity_viewer(self):
        candidates = [*VIEW_MODULES, *sorted((ROOT / "tests").glob("test_view_*.py")),
                      *sorted(path for path in WEB.glob("*") if path.is_file()), WEB / "vendor" / "manifest.json",
                      ROOT / "docs" / "tooling" / "VIEWER.md", WEB.parent / "README.md"]
        paths = [path.relative_to(ROOT).as_posix() for path in candidates if path.exists()]
        self.assertGreater(len(paths), 10)
        impact = classify(paths)
        self.assertEqual(impact.unknown_paths, ())
        for path in paths:
            with self.subTest(path):
                self.assertIn(f"{path}: activity-viewer", impact.reasons)

    def test_viewer_documentation_also_escalates_to_the_tooling_and_contributor_rules(self):
        self.assertEqual(classify(["docs/tooling/VIEWER.md"]).reasons,
                         ("docs/tooling/VIEWER.md: activity-viewer", "docs/tooling/VIEWER.md: ai-tooling",
                          "docs/tooling/VIEWER.md: contributor-documentation"))


if __name__ == "__main__":
    unittest.main()
