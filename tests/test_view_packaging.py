# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T043 (amendment A3): the built package ships the web bundle and resolves it when installed."""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from agent_braid import view_cli

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "integrations" / "agent-braid-view" / "web"
PACKAGE_WEB = Path("agent_braid") / "view_assets" / "web"
BUILD_INPUTS = ("pyproject.toml", "build_support.py", "MANIFEST.in", "README.md", "LICENSE", "NOTICE",
                "TRADEMARKS.md")


def source_bundle_files():
    """Relative POSIX paths of every file of the web bundle in the source checkout."""
    return sorted(path.relative_to(WEB).as_posix() for path in WEB.rglob("*") if path.is_file())


def vendor_manifest():
    return json.loads((WEB / "vendor" / "manifest.json").read_text(encoding="utf-8"))


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load_build_support():
    """The repo's `build_support` module; a stub `build_py` stands in when setuptools is not installed."""
    modules = {}
    try:
        import setuptools.command.build_py  # noqa: F401
    except ImportError:
        stub = types.ModuleType("setuptools.command.build_py")
        stub.build_py = type("build_py", (), {})
        modules = {"setuptools": types.ModuleType("setuptools"),
                   "setuptools.command": types.ModuleType("setuptools.command"),
                   "setuptools.command.build_py": stub}
    with mock.patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location("build_support_under_test", ROOT / "build_support.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    return module


def setuptools_available():
    """True when this interpreter can run the project's declared build backend (Python 3.12+, setuptools 68+)."""
    try:
        import setuptools.build_meta  # noqa: F401
        from setuptools import __version__
    except ImportError:
        return False
    return sys.version_info >= (3, 12) and int(__version__.split(".")[0]) >= 68


REQUIRE_BUILD_ENV = "AGENT_BRAID_REQUIRE_BUILD_TESTS"
BUILD_BACKEND_MISSING = ("the wheel and sdist build tests need Python 3.12+ and setuptools 68+ (the declared build "
                         "backend): run `python -m pip install 'setuptools>=68'` to run them. Set "
                         f"{REQUIRE_BUILD_ENV}=1 to fail instead of skip, as an environment that claims the wheel "
                         "evidence (SC-012) must.")


def require_build_backend():
    """Skip the build tests when the backend is missing, or fail when the environment requires them to run."""
    if setuptools_available():
        return
    if os.environ.get(REQUIRE_BUILD_ENV) == "1":
        raise AssertionError(BUILD_BACKEND_MISSING)
    raise unittest.SkipTest(BUILD_BACKEND_MISSING)


# Runs in a clean interpreter whose only agent_braid is the extracted package under `argv[1]`.
LOOKUP = """
import json, sys
sys.path.insert(0, sys.argv[1])
from agent_braid import view_cli
directory = view_cli.resolve_bundle_dir()
files, import_map = view_cli.load_bundle(directory)
print(json.dumps({"directory": str(directory), "source_checkout": view_cli.BUNDLE_DIR.exists(),
                  "files": sorted(files), "import_map": import_map}))
"""

# Serves the bundle from the extracted package and fetches a vendored file through the running server.
SERVE = """
import argparse, contextlib, http.client, io, json, sys, threading
from pathlib import Path
from urllib.parse import urlsplit
sys.path.insert(0, sys.argv[1])
from agent_braid import view_cli

root = argparse.ArgumentParser()
view_cli.add_parser(root.add_subparsers(dest="command", required=True))
args = root.parse_args(["view", "serve", "--no-discover", "--runtime-dir", sys.argv[2]])
report = {}

def get(server, path, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
    try:
        connection.request("GET", path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()

def fetch(server):
    try:
        target = urlsplit(server.open_url)
        _, headers, _ = get(server, f"{target.path}?{target.query}")
        cookie = {"Cookie": headers["Set-Cookie"].split(";")[0]}
        for path in ("/", "/web/loom.js", "/web/vendor/three/three.module.js", "/web/vendor/three/LICENSE"):
            status, _, body = get(server, path, cookie)
            report[path] = [status, len(body)]
    finally:
        server.shutdown()

def on_ready(server):  # called before serve_forever: fetch from another thread, which then stops the server
    threading.Thread(target=fetch, args=(server,)).start()

with contextlib.redirect_stdout(io.StringIO()):
    report["code"] = view_cli.run(args, on_ready=on_ready)
print(json.dumps(report))
"""


def materialize(mapping):
    """Copy a `build_support` asset mapping (destination -> source) as the wheel build does."""
    for output, source in mapping.items():
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def copy_package(destination_root):
    shutil.copytree(ROOT / "agent_braid", destination_root / "agent_braid",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))


def run_python(script, *arguments):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("PYTHON")}
    completed = subprocess.run([sys.executable, "-I", "-c", script, *map(str, arguments)], capture_output=True,
                               text=True, timeout=120, env=environment, check=False)
    if completed.returncode != 0:
        raise AssertionError(f"subprocess failed ({completed.returncode}): {completed.stderr}")
    return json.loads(completed.stdout)


class ExtractedPackageCase(unittest.TestCase):
    """Shared checks over an installed-looking tree (`site/agent_braid/...` and no source checkout)."""

    def assert_resolves_and_serves(self, site):
        expected = sorted(name for name in source_bundle_files() if "/" not in name)
        found = run_python(LOOKUP, site)
        self.assertEqual(Path(found["directory"]), site / PACKAGE_WEB)
        self.assertFalse(found["source_checkout"])
        self.assertEqual(found["files"], expected)
        self.assertIn("index.html", found["files"])
        runtime = site.parent / "runtime"
        served = run_python(SERVE, site, runtime)
        self.assertEqual(served["code"], 0)
        for path in ("/", "/web/loom.js", "/web/vendor/three/three.module.js", "/web/vendor/three/LICENSE"):
            with self.subTest(path=path):
                self.assertEqual(served[path][0], 200)
                self.assertGreater(served[path][1], 0)
        for relative, digest in vendor_manifest()["files"].items():
            with self.subTest(vendored=relative):
                self.assertEqual(sha256((site / PACKAGE_WEB / "vendor" / relative).read_bytes()), digest)


class BuildSupportMappingTests(ExtractedPackageCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name).resolve() / "site-packages"
        self.build_support = load_build_support()
        self.builder = object.__new__(self.build_support.ToolingBuildPy)
        self.builder.build_lib = str(self.site)

    def view_mapping(self):
        prefix = str(self.site / PACKAGE_WEB) + os.sep
        return {output: source for output, source in self.builder._asset_mapping().items() if output.startswith(prefix)}

    def test_every_bundle_and_vendored_file_is_mapped_into_the_package(self):
        mapping = self.view_mapping()
        expected = {str(self.site / PACKAGE_WEB / relative): str(WEB / relative) for relative in source_bundle_files()}
        self.assertEqual(mapping, expected)
        for relative in ("vendor/manifest.json", "vendor/three/LICENSE"):
            with self.subTest(relative=relative):
                self.assertIn(str(self.site / PACKAGE_WEB / relative), mapping)

    def test_stray_local_files_are_not_shipped_and_links_are_refused(self):
        bundle = Path(self.tmp.name) / "web"
        shutil.copytree(WEB, bundle)
        (bundle / ".DS_Store").write_bytes(b"x")
        (bundle / "vendor" / "__pycache__").mkdir()
        (bundle / "vendor" / "__pycache__" / "x.pyc").write_bytes(b"x")
        (bundle / "vendor" / ".note.swp").write_bytes(b"x")
        with mock.patch.object(self.build_support, "VIEW_WEB_SOURCE", bundle):
            mapped = {Path(source).relative_to(bundle).as_posix() for source in self.view_mapping().values()}
            self.assertEqual(mapped, set(source_bundle_files()))
            (bundle / "link.js").symlink_to(bundle / "loom.js")
            with self.assertRaisesRegex(ValueError, "links"):
                self.builder._asset_mapping()

    def test_existing_tooling_assets_stay_in_the_mapping(self):
        mapping = self.builder._asset_mapping()
        for name in ("hosts.json", "NOTICE", "TRADEMARKS.md"):
            self.assertIn(str(self.site / "agent_braid" / "tooling_assets" / name), mapping)

    def test_a_bundle_without_index_fails_the_build_loudly(self):
        with mock.patch.object(self.build_support, "VIEW_WEB_SOURCE", Path(self.tmp.name) / "absent"):
            with self.assertRaisesRegex(FileNotFoundError, "web bundle"):
                self.builder._asset_mapping()

    def test_the_mapped_tree_resolves_and_serves_from_an_installed_package(self):
        copy_package(self.site)
        materialize(self.view_mapping())
        self.assert_resolves_and_serves(self.site)

    def test_sdist_manifest_includes_the_bundle(self):
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertIn("recursive-include integrations/agent-braid-view/web *", manifest)


class ResolveBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.installed = Path(view_cli.__file__).resolve().parent / "view_assets" / "web"

    def bundle(self, name):
        directory = self.base / name
        directory.mkdir()
        (directory / "index.html").write_text("<!doctype html>", encoding="utf-8")
        return directory

    def test_the_source_checkout_is_preferred_when_present(self):
        source = self.bundle("source")
        with mock.patch.object(view_cli, "BUNDLE_DIR", source):
            self.assertEqual(view_cli.resolve_bundle_dir(), source)

    def test_the_installed_package_is_used_when_the_source_checkout_is_absent(self):
        with mock.patch.object(view_cli, "BUNDLE_DIR", self.base / "nowhere"), \
                mock.patch.object(Path, "is_file", autospec=True,
                                  side_effect=lambda path: path == self.installed / "index.html"):
            self.assertEqual(view_cli.resolve_bundle_dir(), self.installed)

    def test_an_incomplete_source_directory_does_not_shadow_the_installed_copy(self):
        empty = self.base / "empty"
        empty.mkdir()
        with mock.patch.object(view_cli, "BUNDLE_DIR", empty), \
                mock.patch.object(Path, "is_file", autospec=True,
                                  side_effect=lambda path: path == self.installed / "index.html"):
            self.assertEqual(view_cli.resolve_bundle_dir(), self.installed)

    def test_nothing_found_returns_the_source_path_so_load_bundle_refuses_it(self):
        missing = self.base / "nowhere"
        with mock.patch.object(view_cli, "BUNDLE_DIR", missing):
            self.assertEqual(view_cli.resolve_bundle_dir(), missing)
            with self.assertRaisesRegex(view_cli.CliError, "bundle") as raised:
                view_cli.load_bundle(view_cli.resolve_bundle_dir())
        self.assertNotIn("source checkout only", raised.exception.message)
        self.assertNotIn("runs from a source checkout", raised.exception.message)

    def test_the_real_source_checkout_resolves_to_the_repository_bundle(self):
        self.assertEqual(view_cli.resolve_bundle_dir(), WEB)


class WheelBuildTests(ExtractedPackageCase):
    @classmethod
    def setUpClass(cls):
        require_build_backend()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        work = Path(cls.tmp.name).resolve()
        project = work / "project"
        project.mkdir()
        for name in BUILD_INPUTS:
            shutil.copyfile(ROOT / name, project / name)
        for name in ("agent_braid", "research"):
            shutil.copytree(ROOT / name, project / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "LICENSES", project / "LICENSES")
        shutil.copytree(ROOT / "integrations" / "agent-braid", project / "integrations" / "agent-braid")
        shutil.copytree(WEB.parent, project / "integrations" / "agent-braid-view")
        shutil.copytree(ROOT / "examples" / "tooling", project / "examples" / "tooling")
        cls.dist = work / "dist"
        cls.dist.mkdir()
        build = ("import sys\nfrom setuptools import build_meta\n"
                 "print(build_meta.build_wheel(sys.argv[1]))")
        cls.wheel = cls.dist / cls.build(project, build)
        cls.sdist = cls.dist / cls.build(project, build.replace("build_wheel", "build_sdist"))

    @classmethod
    def build(cls, project, script):
        completed = subprocess.run([sys.executable, "-c", script, str(cls.dist)], cwd=project, capture_output=True,
                                   text=True, timeout=600, check=False)
        if completed.returncode != 0:
            raise AssertionError(f"build failed: {completed.stderr[-2000:]}")
        return completed.stdout.strip().splitlines()[-1]

    def test_the_wheel_contains_every_bundle_and_vendored_file_with_its_manifest_hash(self):
        with zipfile.ZipFile(self.wheel) as archive:
            names = set(archive.namelist())
            for relative in source_bundle_files():
                with self.subTest(relative=relative):
                    packaged = (PACKAGE_WEB / relative).as_posix()
                    self.assertIn(packaged, names)
                    self.assertEqual(archive.read(packaged), (WEB / relative).read_bytes())
            self.assertIn("agent_braid/tooling_assets/NOTICE", names)
            self.assertNotIn((PACKAGE_WEB / ".DS_Store").as_posix(), names)

    def test_the_sdist_carries_every_bundle_and_vendored_file(self):
        with tarfile.open(self.sdist) as archive:
            names = {name.split("/", 1)[1] for name in archive.getnames() if "/" in name}
        for relative in source_bundle_files():
            with self.subTest(relative=relative):
                self.assertIn(f"integrations/agent-braid-view/web/{relative}", names)

    def test_the_extracted_wheel_resolves_and_serves_the_bundle(self):
        site = self.dist.parent / "installed"
        with zipfile.ZipFile(self.wheel) as archive:
            archive.extractall(site)
        self.assert_resolves_and_serves(site)


class BuildBackendGateTests(unittest.TestCase):
    """The build tests skip without the backend unless the environment requires them (finding 12)."""

    def test_a_missing_backend_skips_by_default_and_names_the_fix(self):
        with mock.patch.dict(os.environ, {}, clear=False) as environment, \
                mock.patch(f"{__name__}.setuptools_available", return_value=False):
            environment.pop(REQUIRE_BUILD_ENV, None)
            with self.assertRaises(unittest.SkipTest) as raised:
                require_build_backend()
        self.assertIn("setuptools>=68", str(raised.exception))
        self.assertIn(REQUIRE_BUILD_ENV, str(raised.exception))

    def test_a_missing_backend_fails_when_the_environment_requires_the_build_tests(self):
        with mock.patch.dict(os.environ, {REQUIRE_BUILD_ENV: "1"}), \
                mock.patch(f"{__name__}.setuptools_available", return_value=False):
            with self.assertRaises(AssertionError):
                require_build_backend()

    def test_an_available_backend_neither_skips_nor_fails(self):
        with mock.patch.dict(os.environ, {REQUIRE_BUILD_ENV: "1"}), \
                mock.patch(f"{__name__}.setuptools_available", return_value=True):
            require_build_backend()


if __name__ == "__main__":
    unittest.main()
