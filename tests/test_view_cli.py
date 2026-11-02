# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T028: `agent-braid view` command group (procedure_011 surface part, procedure_012)."""
import argparse
import contextlib
import http.client
import io
import json
import os
import re
import shutil
import socket
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import urlsplit

from agent_braid import cli, view_cli
from agent_braid.view_hooks import OBSERVATIONAL_EVENTS

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/view"
LOOM = FIXTURES / "loom"
DECISION_EVENTS = ("PreToolUse", "PermissionRequest", "UserPromptSubmit", "Stop")
JSON_HEADERS = {"Content-Type": "application/json"}


def invoke(*argv):
    """Run the real CLI entry point; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exit_:  # argparse usage errors
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


def parse(*argv):
    root = argparse.ArgumentParser()
    view_cli.add_parser(root.add_subparsers(dest="command", required=True))
    return root.parse_args(list(argv))


def tree(path):
    """A snapshot of a directory tree: relative path -> (mode, size)."""
    found = {}
    for current, directories, files in os.walk(path):
        for name in directories + files:
            full = os.path.join(current, name)
            info = os.lstat(full)
            found[os.path.relpath(full, path)] = (stat.S_IMODE(info.st_mode), info.st_size)
    return found


class TempCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.runtime = self.base / "run"
        self.bundle = self.base / "web"
        self.bundle.mkdir()
        (self.bundle / "index.html").write_text("<!doctype html><title>t</title>")
        (self.bundle / "loom.js").write_text("//js")
        (self.bundle / ".hidden").write_text("secret")
        (self.bundle / "vendor").mkdir()
        (self.bundle / "vendor" / "x.js").write_text("//vendor")
        patch = mock.patch.object(view_cli, "BUNDLE_DIR", self.bundle)
        patch.start()
        self.addCleanup(patch.stop)


class ServeCase(TempCase):
    """Starts `view serve` on a thread through `run(on_ready=...)` and tears it down."""

    def serve(self, *extra, ready=None):
        args = parse("view", "serve", "--runtime-dir", str(self.runtime), *extra)
        started = threading.Event()
        result = {}

        def on_ready(server):
            result["server"] = server
            started.set()

        def target():
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result["code"] = view_cli.run(args, on_ready=on_ready)
            result["stdout"], result["stderr"] = out.getvalue(), err.getvalue()

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        self.assertTrue(started.wait(10), "the server did not start")
        server = result["server"]

        def stop():
            server.shutdown()
            thread.join(10)

        self.addCleanup(stop)
        return server, result, thread

    @staticmethod
    def request(server, method, path, headers=None, body=None):
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=dict(headers or {}))
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def cookie(self, server):
        target = urlsplit(server.open_url)
        status, headers, _ = self.request(server, "GET", f"{target.path}?{target.query}")
        self.assertEqual(status, 303)
        return {"Cookie": headers["Set-Cookie"].split(";")[0]}

    def snapshot(self, server, cookie=None):
        status, _, body = self.request(server, "GET", "/snapshot", cookie or self.cookie(server))
        self.assertEqual(status, 200)
        return json.loads(body)

    def token(self, server):
        return server.token_path.read_text()


class ServeTests(ServeCase):
    def test_serves_the_bundle_replay_and_hooks_on_loopback(self):
        server, result, _ = self.serve("--surface", "web", "--replay", str(LOOM / "valid-corpus.jsonl"))
        self.assertEqual(server.server_address[0], "127.0.0.1")
        self.assertEqual(server.token_path.parent, self.runtime)
        self.assertEqual(stat.S_IMODE(os.stat(self.runtime).st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(os.stat(server.token_path).st_mode), 0o600)
        cookie = self.cookie(server)
        status, _, body = self.request(server, "GET", "/", cookie)
        self.assertEqual((status, body), (200, b"<!doctype html><title>t</title>"))
        self.assertEqual(self.request(server, "GET", "/web/loom.js", cookie)[0], 200)
        self.assertEqual(self.request(server, "GET", "/web/vendor/x.js", cookie)[0], 404)
        self.assertEqual(self.request(server, "GET", "/web/.hidden", cookie)[0], 404)
        self.assertTrue(self.snapshot(server, cookie)["model"])
        replayed = server.store.replay()
        self.assertTrue(replayed)
        self.assertTrue(all(event["source"]["verification"] == "unverified" for event in replayed))

    def test_hook_ingest_is_registered_with_names_inventory(self):
        server, _, _ = self.serve()
        payload = json.loads((FIXTURES / "hooks/unknown-attribute.json").read_text())
        status, _, body = self.request(server, "POST", "/hook/claude",
                                       {**JSON_HEADERS, "Authorization": f"Bearer {self.token(server)}"},
                                       json.dumps(payload))
        self.assertEqual((status, body), (200, b""))
        self.assertTrue(server.store.replay())
        names = self.snapshot(server)["droppedAttributeNames"]
        self.assertTrue(names)
        decision = json.loads((FIXTURES / "hooks/decision-stop.json").read_text())
        status, _, body = self.request(server, "POST", "/hook/claude",
                                       {**JSON_HEADERS, "Authorization": f"Bearer {self.token(server)}"},
                                       json.dumps(decision))
        self.assertEqual((status, body), (403, b""))
        self.assertEqual(self.request(server, "POST", "/v1/logs",
                                      {**JSON_HEADERS, "Authorization": f"Bearer {self.token(server)}"}, "{}")[0], 404)

    def test_watch_feeds_artifacts_into_the_store(self):
        watched = self.base / "artifacts"
        watched.mkdir()
        shutil.copy(FIXTURES / "artifacts/analysis-mixed.json", watched / "analysis.json")
        server, _, _ = self.serve("--watch", str(watched))
        deadline = time.monotonic() + 10
        while not server.store.replay() and time.monotonic() < deadline:
            time.sleep(0.05)
        events = server.store.replay()
        self.assertTrue(events)
        self.assertTrue(all(event["source"]["verification"] == "rehashed" for event in events))

    def test_port_option_binds_that_port(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        server, _, _ = self.serve("--port", str(port))
        self.assertEqual(server.port, port)

    def test_import_map_in_index_html_is_allowed_by_the_policy_hash(self):
        (self.bundle / "index.html").write_text(
            '<!doctype html><script type="importmap">{"imports":{"three":"/web/three.js"}}</script>')
        server, _, _ = self.serve()
        status, headers, _ = self.request(server, "GET", "/", self.cookie(server))
        self.assertEqual(status, 200)
        self.assertIn("'sha256-", headers["Content-Security-Policy"])

    def test_import_map_variants_are_hashed(self):
        for block in ("<SCRIPT TYPE='importmap'>{}</SCRIPT>", '<script defer type=importmap\n>{}</script >'):
            with self.subTest(block=block):
                (self.bundle / "index.html").write_text(f"<!doctype html>{block}")
                server, _, _ = self.serve()
                _, headers, _ = self.request(server, "GET", "/", self.cookie(server))
                self.assertIn("'sha256-", headers["Content-Security-Policy"])

    def test_prints_the_open_url_and_token_path_once_at_start(self):
        server, result, thread = self.serve()
        token = self.token(server)
        server.shutdown()
        thread.join(10)
        self.assertEqual(result["code"], 0)
        self.assertEqual(result["stdout"].count("/open?code="), 1)
        self.assertIn(str(server.token_path), result["stdout"])
        self.assertNotIn(token, result["stdout"] + result["stderr"])

    def test_the_token_file_is_removed_when_the_server_stops(self):
        server, _, thread = self.serve()
        self.assertTrue(server.token_path.exists())
        server.shutdown()
        thread.join(10)
        self.assertFalse(server.token_path.exists())

    def test_a_token_file_replaced_by_another_server_is_left_alone(self):
        server, _, thread = self.serve()
        server.token_path.write_text("another-servers-token")
        server.shutdown()
        thread.join(10)
        self.assertEqual(server.token_path.read_text(), "another-servers-token")

    def test_sigterm_stops_the_server_cleanly_and_restores_the_handler(self):
        import signal
        args = parse("view", "serve", "--runtime-dir", str(self.runtime))
        before = signal.getsignal(signal.SIGTERM)
        seen = {}

        def on_ready(server):
            seen["token_path"] = server.token_path
            os.kill(os.getpid(), signal.SIGTERM)

        with contextlib.redirect_stdout(io.StringIO()):
            code = view_cli.run(args, on_ready=on_ready)
        self.assertEqual(code, 0)
        self.assertFalse(seen["token_path"].exists())
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)


class ServeRefusalTests(TempCase):
    def assert_no_side_effect(self):
        self.assertFalse(self.runtime.exists())

    def test_planned_surfaces_report_planned_without_effect(self):
        for surface in ("mod", "tui", "mcp-app"):
            with self.subTest(surface=surface):
                code, out, err = invoke("view", "serve", "--surface", surface, "--runtime-dir", str(self.runtime))
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn(f"surface {surface} is planned", err)
                self.assertIn("nothing was started", err)
                self.assert_no_side_effect()

    def test_unknown_surface_is_a_usage_error(self):
        code, _, err = invoke("view", "serve", "--surface", "hologram")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_bad_ports_are_usage_errors(self):
        for port in ("-1", "65536", "abc", ""):
            with self.subTest(port=port):
                code, _, err = invoke("view", "serve", "--port", port)
                self.assertEqual(code, 2)
                self.assertIn("--port", err)

    def test_missing_replay_file_is_refused_before_anything_starts(self):
        code, out, err = invoke("view", "serve", "--replay", str(self.base / "none.jsonl"),
                                "--runtime-dir", str(self.runtime))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("replay-file", err)
        self.assert_no_side_effect()

    def test_invalid_replay_stream_exits_one(self):
        for name in ("decreasing-seq", "duplicate-key", "nan", "duplicate-seq"):
            with self.subTest(name=name):
                code, out, err = invoke("view", "serve", "--replay", str(LOOM / f"{name}.jsonl"),
                                        "--runtime-dir", str(self.runtime))
                self.assertEqual((code, out), (1, ""))
                self.assertIn("replay refused", err)
                self.assert_no_side_effect()

    def test_missing_watch_root_is_refused(self):
        code, out, err = invoke("view", "serve", "--watch", str(self.base / "absent"),
                                "--runtime-dir", str(self.runtime))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("watch", err)
        self.assert_no_side_effect()

    def test_missing_bundle_is_refused(self):
        with mock.patch.object(view_cli, "BUNDLE_DIR", self.base / "nowhere"):
            code, out, err = invoke("view", "serve", "--runtime-dir", str(self.runtime))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("bundle", err)
        self.assert_no_side_effect()

    def test_bundle_without_index_is_refused(self):
        (self.bundle / "index.html").unlink()
        code, _, err = invoke("view", "serve", "--runtime-dir", str(self.runtime))
        self.assertEqual(code, 2)
        self.assertIn("index.html", err)

    def test_two_import_maps_are_refused(self):
        block = '<script type="importmap">{}</script>'
        (self.bundle / "index.html").write_text(block + block)
        code, _, err = invoke("view", "serve", "--runtime-dir", str(self.runtime))
        self.assertEqual(code, 2)
        self.assertIn("import map", err)

    def test_port_in_use_is_reported_without_a_traceback(self):
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen()
            port = holder.getsockname()[1]
            code, out, err = invoke("view", "serve", "--port", str(port), "--runtime-dir", str(self.runtime))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("cannot bind", err)
        self.assertNotIn("Traceback", err)
        self.assert_no_side_effect()

    def test_port_in_use_removes_the_parents_it_created(self):
        deep = self.base / "a" / "b" / "run"
        with socket.socket() as holder:
            holder.bind(("127.0.0.1", 0))
            holder.listen()
            port = holder.getsockname()[1]
            code, _, _ = invoke("view", "serve", "--port", str(port), "--runtime-dir", str(deep))
        self.assertEqual(code, 2)
        self.assertFalse((self.base / "a").exists())

    def test_import_map_that_cannot_be_hashed_is_refused(self):
        (self.bundle / "index.html").write_text("<!doctype html><!-- importmap --><script>1</script>")
        code, _, err = invoke("view", "serve", "--runtime-dir", str(self.runtime))
        self.assertEqual(code, 2)
        self.assertIn("import map", err)
        self.assert_no_side_effect()

    def test_relative_runtime_dir_is_refused(self):
        code, _, err = invoke("view", "serve", "--runtime-dir", "relative/run")
        self.assertEqual(code, 2)
        self.assertIn("runtime-dir", err)

    def test_missing_subcommand_is_a_usage_error(self):
        code, _, _ = invoke("view")
        self.assertEqual(code, 2)
        code, _, _ = invoke("view", "nonsense")
        self.assertEqual(code, 2)


class RuntimeDirTests(unittest.TestCase):
    def test_default_is_private_per_user_location(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}, clear=False):
                os.environ.pop("XDG_RUNTIME_DIR", None)
                self.assertEqual(view_cli.default_runtime_dir(),
                                 Path(home) / ".local" / "share" / "agent-braid-view")

    def test_xdg_runtime_dir_wins_when_absolute(self):
        with tempfile.TemporaryDirectory() as xdg:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": xdg}):
                self.assertEqual(view_cli.default_runtime_dir(), Path(xdg) / "agent-braid-view")
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": "relative"}):
                self.assertNotEqual(view_cli.default_runtime_dir(), Path("relative") / "agent-braid-view")

    def test_serve_creates_missing_parents_privately(self):
        with tempfile.TemporaryDirectory() as home:
            runtime = Path(home).resolve() / ".local" / "share" / "agent-braid-view"
            with mock.patch.dict(os.environ, {"HOME": home}, clear=False):
                os.environ.pop("XDG_RUNTIME_DIR", None)
                ready = {}

                def on_ready(server):
                    ready["mode"] = stat.S_IMODE(os.stat(runtime).st_mode)
                    ready["token"] = server.token_path
                    threading.Thread(target=server.shutdown).start()  # not from the serving thread

                with mock.patch.object(view_cli, "BUNDLE_DIR", self.make_bundle(home)):
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = view_cli.run(parse("view", "serve"), on_ready=on_ready)
            self.assertEqual(code, 0)
            self.assertEqual(ready["mode"], 0o700)
            self.assertEqual(ready["token"].resolve(), runtime / "view-ingest-token")

    @staticmethod
    def make_bundle(home):
        bundle = Path(home) / "bundle"
        bundle.mkdir()
        (bundle / "index.html").write_text("<!doctype html>")
        return bundle


class ValidateTests(TempCase):
    def test_valid_stream_exits_zero(self):
        code, out, err = invoke("view", "validate", str(LOOM / "valid-corpus.jsonl"))
        self.assertEqual((code, err), (0, ""))
        self.assertRegex(out, r"^ok: \d+ events\n$")

    def test_invalid_streams_exit_one_with_a_stable_message(self):
        for name in ("decreasing-seq", "duplicate-key", "nan", "duplicate-seq"):
            with self.subTest(name=name):
                code, out, err = invoke("view", "validate", str(LOOM / f"{name}.jsonl"))
                self.assertEqual((code, out), (1, ""))
                self.assertTrue(err.startswith("view validate: invalid: "), err)
                self.assertEqual(err.count("\n"), 1)

    def test_unreadable_files_exit_two(self):
        link = self.base / "link.jsonl"
        link.symlink_to(LOOM / "valid-corpus.jsonl")
        for target in (self.base / "missing.jsonl", link, self.base):
            with self.subTest(target=target.name):
                code, out, err = invoke("view", "validate", str(target))
                self.assertEqual((code, out), (2, ""))
                self.assertTrue(err.startswith("view validate: "), err)

    def test_missing_argument_is_a_usage_error(self):
        code, _, err = invoke("view", "validate")
        self.assertEqual(code, 2)
        self.assertIn("file", err)

    def test_validate_writes_nothing(self):
        before = tree(self.base)
        invoke("view", "validate", str(LOOM / "valid-corpus.jsonl"))
        self.assertEqual(tree(self.base), before)


class EnvTests(TempCase):
    def env(self, *extra):
        return invoke("view", "env", "--host", "claude", "--runtime-dir", str(self.runtime), *extra)

    @staticmethod
    def settings(text):
        return json.loads("\n".join(line for line in text.splitlines()
                                    if line.strip() and not line.startswith(("#", "export "))))

    def test_prints_observational_http_hooks_for_claude(self):
        code, out, err = self.env("--port", "4310")
        self.assertEqual((code, err), (0, ""))
        hooks = self.settings(out)["hooks"]
        self.assertEqual(sorted(hooks), sorted(OBSERVATIONAL_EVENTS))
        for entries in hooks.values():
            (group,) = entries
            (hook,) = group["hooks"]
            self.assertEqual(hook["type"], "http")
            self.assertEqual(hook["url"], "http://127.0.0.1:4310/hook/claude")
            self.assertEqual(hook["headers"], {"Authorization": "Bearer $AGENT_BRAID_VIEW_TOKEN"})
            self.assertEqual(hook["allowedEnvVars"], ["AGENT_BRAID_VIEW_TOKEN"])
            self.assertGreater(hook["timeout"], 0)

    def test_port_placeholder_when_not_given(self):
        code, out, _ = self.env()
        self.assertEqual(code, 0)
        self.assertIn("http://127.0.0.1:<port>/hook/claude", out)

    def test_targets_only_loopback_and_names_no_decision_event(self):
        _, out, _ = self.env("--port", "4310")
        for decision in DECISION_EVENTS:
            self.assertIsNone(re.search(rf"\b{decision}\b", out), decision)
        self.assertEqual(out.count("http://"), len(OBSERVATIONAL_EVENTS))
        for line in out.splitlines():
            if "http://" in line:
                self.assertIn("http://127.0.0.1:", line)
        self.assertNotIn("0.0.0.0", out)

    def test_reads_the_token_from_its_file_and_prints_no_credential(self):
        from agent_braid.view_serve import INGEST_TOKEN_NAME, ViewServer
        from agent_braid.view_store import LoomStore
        server = ViewServer(LoomStore(), self.runtime)
        self.addCleanup(server.server_close)
        token = server.token_path.read_text()
        code, out, err = self.env("--port", str(server.port))
        self.assertEqual(code, 0)
        self.assertNotIn(token, out + err)
        self.assertNotIn(server._open_code, out + err)
        self.assertIn(str(server.token_path), out)
        self.assertRegex(out, r"export AGENT_BRAID_VIEW_TOKEN=\"\$\(cat '?[^)]*" + INGEST_TOKEN_NAME + r"'?\)\"")

    def test_says_it_writes_nothing_and_to_use_user_level_settings(self):
        _, out, _ = self.env()
        self.assertIn("writes nothing", out)
        self.assertIn("user-level", out)
        self.assertIn("while the viewer is running", out)

    def test_writes_nothing(self):
        home = self.base / "home"
        home.mkdir()
        before_base = tree(self.base)
        with mock.patch.dict(os.environ, {"HOME": str(home)}):
            os.environ.pop("XDG_RUNTIME_DIR", None)
            code, _, _ = invoke("view", "env", "--host", "claude")
        self.assertEqual(code, 0)
        self.assertEqual(tree(self.base), before_base)
        self.assertEqual(list(home.iterdir()), [])
        self.assertFalse(self.runtime.exists())

    def test_missing_and_invalid_host_are_usage_errors(self):
        code, _, err = invoke("view", "env")
        self.assertEqual(code, 2)
        self.assertIn("--host", err)
        code, _, err = invoke("view", "env", "--host", "vim")
        self.assertEqual(code, 2)
        self.assertIn("invalid choice", err)

    def test_codex_is_accepted_but_not_available_yet(self):
        code, out, err = invoke("view", "env", "--host", "codex")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("host codex is not available", err)

    def test_port_zero_is_a_usage_error(self):
        code, _, err = self.env("--port", "0")
        self.assertEqual(code, 2)
        self.assertIn("between 1 and 65535", err)

    def test_bad_port_is_a_usage_error(self):
        code, _, err = self.env("--port", "70000")
        self.assertEqual(code, 2)
        self.assertIn("--port", err)


class BoundaryTests(unittest.TestCase):
    SOURCE = (ROOT / "agent_braid/view_cli.py").read_text()

    def test_no_network_or_ownership_imports(self):
        for forbidden in ("import socket", "import http", "from http", "urllib", "ownership"):
            self.assertNotIn(forbidden, self.SOURCE)

    def test_importing_the_module_does_not_load_the_server(self):
        import subprocess
        import sys
        code = ("import sys, agent_braid.view_cli; "
                "sys.exit(1 if 'agent_braid.view_serve' in sys.modules or 'http.server' in sys.modules else 0)")
        self.assertEqual(subprocess.run([sys.executable, "-c", code], cwd=ROOT).returncode, 0)


if __name__ == "__main__":
    unittest.main()
