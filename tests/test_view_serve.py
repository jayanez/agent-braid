# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T016, T017: loopback server checks, route table, event stream, snapshot and replay."""
import contextlib
import hashlib
import io
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent_braid import view_ingest, view_loom, view_roots, view_serve, view_tail
from agent_braid.view_serve import IngestRefusal, ServeError, ViewServer
from agent_braid.view_model import build_model
from agent_braid.view_store import LoomStore
from tests.view_http_helpers import JSON, http_request

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path(__file__).resolve().parents[1] / "specs/061-activity-viewer/contracts/ui-security-privacy.md"
IMPORT_MAP_HASH = "A" * 43 + "="  # base64 of 32 bytes
CONTRACT_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
}


class ServerCase(unittest.TestCase):
    server_kwargs: dict = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name) / "run"
        self.store = LoomStore()
        self.received: dict[str, list] = {"/v1/logs": [], "/v1/metrics": [], "/hook/claude": []}
        handlers = {path: items.append for path, items in self.received.items()}
        self.start(ingest_handlers=handlers, **self.server_kwargs)

    def start(self, **kwargs):
        kwargs.setdefault("bundle", {"index.html": b"<!doctype html>", "app.js": b"//js"})
        self.server = ViewServer(self.store, self.runtime, **kwargs)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)
        self.port = self.server.port
        self.token = self.server.token_path.read_text()
        self.open_code = self.server.open_url.split("code=")[1]

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(5)

    def request(self, method, path, headers=None, body=None, host=None):
        return http_request(self.port, method, path, headers, body, host)

    def raw(self, data: bytes, port=None):
        with socket.create_connection(("127.0.0.1", port or self.port), timeout=5) as sock:
            sock.sendall(data)
            sock.shutdown(socket.SHUT_WR)  # the client has sent everything it will send
            chunks = []
            while chunk := sock.recv(4096):
                chunks.append(chunk)
        head, _, body = b"".join(chunks).partition(b"\r\n\r\n")
        lines = head.decode("latin-1").split("\r\n")
        headers = {k.lower(): v for k, _, v in (line.partition(": ") for line in lines[1:])}
        return int(lines[0].split()[1]), headers, body

    def cookie(self):
        status, response, _ = self.request("GET", f"/open?code={self.open_code}")
        self.assertEqual(status, 303)
        return response.getheader("Set-Cookie").split(";")[0]

    def post(self, path, body, headers=None, token=True):
        merged = dict(JSON)
        if token:
            merged["Authorization"] = f"Bearer {self.token}"
        merged.update(headers or {})
        return self.request("POST", path, merged, body)

    def refused_state_unchanged(self):
        self.assertEqual(self.store.stats()["headSeq"], 0)
        self.assertEqual([item for items in self.received.values() for item in items], [])


class ModuleBoundaryTests(unittest.TestCase):
    def test_the_server_does_not_import_the_watcher_or_the_adapters(self):
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import agent_braid.view_serve; "
                "print(sorted(name for name in ('agent_braid.view_tail', 'agent_braid.view_adapters') "
                "if name in sys.modules))")
        result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True, text=True,
                                check=True)
        self.assertEqual(result.stdout.strip(), "[]")

    def test_the_ingest_refusal_and_inventory_limits_are_the_shared_ones(self):
        self.assertIs(view_serve.IngestRefusal, view_ingest.IngestRefusal)
        self.assertEqual(view_serve.MAX_INVENTORY_NAMES, view_ingest.MAX_INVENTORY_NAMES)
        self.assertEqual(view_serve.MAX_INVENTORY_NAME_LENGTH, view_ingest.MAX_INVENTORY_NAME_LENGTH)

    def test_the_watcher_keeps_exposing_the_root_registry(self):
        self.assertIs(view_tail.replay_with_roots, view_roots.replay_with_roots)
        self.assertIs(view_tail.root_labels_of, view_roots.root_labels_of)
        self.assertEqual(view_tail.root_label(1), view_roots.root_label(1))


class TokenTests(ServerCase):
    def test_the_ingest_token_property_is_the_one_in_the_token_file(self):
        self.assertEqual(self.server.ingest_token, self.token)


class BindTests(unittest.TestCase):
    def make(self, **kwargs):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        server = ViewServer(LoomStore(), Path(tmp.name) / "run", **kwargs)
        self.addCleanup(server.server_close)
        return server

    def test_non_loopback_binds_are_refused(self):
        for host in ("0.0.0.0", "::", "", "localhost", "192.168.1.5", "127.0.0.2", "example.com"):
            with self.subTest(host=host), self.assertRaises(ServeError) as caught:
                self.make(host=host)
            self.assertEqual(caught.exception.reason, "bind-refused")

    def test_bad_port_is_refused(self):
        for port in (-1, 65536, "80", None):
            with self.subTest(port=port), self.assertRaises(ServeError):
                self.make(port=port)

    def test_loopback_binds_use_an_os_assigned_port(self):
        server = self.make(host="127.0.0.1")
        self.assertEqual(server.server_address[0], "127.0.0.1")
        self.assertGreater(server.port, 0)
        try:
            ipv6 = self.make(host="::1")
        except OSError:
            self.skipTest("IPv6 loopback unavailable")
        self.assertEqual(ipv6.server_address[0], "::1")
        self.assertIn(f"[::1]:{ipv6.port}", ipv6.open_url)

    def test_limits_are_the_contract_values(self):
        self.assertEqual(view_serve.MAX_CONNECTIONS, 32)
        self.assertEqual(view_serve.SOCKET_TIMEOUT, 10)
        self.assertEqual(view_serve.HEARTBEAT_SECONDS, 15)
        self.assertEqual(view_serve.OTLP_BODY_LIMIT, 1024 * 1024)
        self.assertEqual(view_serve.HOOK_BODY_LIMIT, 256 * 1024)
        from agent_braid import view_store
        self.assertEqual(view_store.MAX_SUBSCRIBERS, 8)

    def test_import_map_hash_must_be_a_sha256_digest(self):
        with self.assertRaises(ServeError):
            self.make(import_map_sha256="not-base64!")
        with self.assertRaises(ServeError):
            self.make(import_map_sha256="AAAA")


class TokenFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name) / "run"

    def make(self, runtime=None):
        server = ViewServer(LoomStore(), runtime or self.runtime)
        self.addCleanup(server.server_close)
        return server

    def test_token_file_is_private_and_holds_a_long_secret(self):
        server = self.make()
        mode = stat.S_IMODE(os.stat(server.token_path).st_mode)
        self.assertEqual(mode, 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(self.runtime).st_mode), 0o700)
        token = server.token_path.read_text()
        self.assertGreaterEqual(len(token), 22)  # 128 bits in url-safe base64
        self.assertNotIn(token, server.open_url)
        self.assertEqual(server.token_path.name, view_serve.INGEST_TOKEN_NAME)

    def test_open_code_has_at_least_128_bits(self):
        code = self.make().open_url.split("code=")[1]
        self.assertGreaterEqual(len(code), 22)

    def test_token_file_is_replaced_at_each_start(self):
        first = self.make()
        old = first.token_path.read_text()
        second = self.make()
        self.assertEqual(first.token_path, second.token_path)
        self.assertNotEqual(second.token_path.read_text(), old)
        self.assertEqual(stat.S_IMODE(os.stat(second.token_path).st_mode), 0o600)
        self.assertEqual(sorted(p.name for p in self.runtime.iterdir()), [view_serve.INGEST_TOKEN_NAME])

    def test_a_planted_symlink_at_the_token_path_is_replaced_not_followed(self):
        self.runtime.mkdir(mode=0o700)
        victim = Path(self.tmp.name) / "victim"
        victim.write_text("keep")
        (self.runtime / view_serve.INGEST_TOKEN_NAME).symlink_to(victim)
        server = self.make()
        self.assertEqual(victim.read_text(), "keep")
        self.assertFalse(server.token_path.is_symlink())

    def test_unsafe_runtime_directories_are_refused(self):
        shared = Path(self.tmp.name) / "shared"
        shared.mkdir(mode=0o755)
        shared.chmod(0o755)
        with self.assertRaises(ServeError) as caught:
            self.make(shared)
        self.assertEqual(caught.exception.reason, "runtime-dir")
        real = Path(self.tmp.name) / "real"
        real.mkdir(mode=0o700)
        link = Path(self.tmp.name) / "link"
        link.symlink_to(real)
        with self.assertRaises(ServeError):
            self.make(link)
        with self.assertRaises(ServeError):
            self.make(Path("relative/run"))
        self.assertEqual(list(real.iterdir()), [])

    def test_failed_start_leaves_no_listener_or_token(self):
        shared = Path(self.tmp.name) / "shared"
        shared.mkdir()
        shared.chmod(0o777)
        with self.assertRaises(ServeError):
            self.make(shared)
        self.assertEqual(list(shared.iterdir()), [])


class CredentialTests(ServerCase):
    def test_requests_without_or_with_wrong_credentials_get_404(self):
        for method, path in (("GET", "/"), ("GET", "/events"), ("GET", "/snapshot"), ("GET", "/web/app.js"),
                             ("GET", "/open"), ("GET", "/open?code=wrong"), ("GET", "/open?code="),
                             ("POST", "/v1/logs"), ("POST", "/hook/claude"), ("GET", "/nope")):
            with self.subTest(path=path):
                status, _, body = self.request(method, path, JSON if method == "POST" else None, b"{}" if method == "POST" else None)
                self.assertEqual((status, body), (404, b""))
        status, _, _ = self.request("GET", "/", {"Cookie": f"{self.server.cookie_name}=guess"})
        self.assertEqual(status, 404)
        status, _, _ = self.post("/v1/logs", b"{}", {"Authorization": "Bearer guess"})
        self.assertEqual(status, 404)
        status, _, _ = self.post("/v1/logs", b"{}", {"Authorization": self.token})
        self.assertEqual(status, 404)
        self.refused_state_unchanged()

    def test_open_code_is_exchanged_once_for_a_strict_http_only_cookie(self):
        status, response, body = self.request("GET", f"/open?code={self.open_code}")
        self.assertEqual((status, body), (303, b""))
        self.assertEqual(response.getheader("Location"), "/")
        self.assertNotIn("code", response.getheader("Location"))
        attributes = [part.strip() for part in response.getheader("Set-Cookie").split(";")]
        self.assertIn("HttpOnly", attributes)
        self.assertIn("SameSite=Strict", attributes)
        self.assertIn("Path=/", attributes)
        self.assertTrue(response.getheader("Set-Cookie").startswith(f"braid_view_{self.port}="))
        self.assertNotIn(self.open_code, response.getheader("Set-Cookie"))
        self.assertNotIn(self.token, response.getheader("Set-Cookie"))
        status, _, _ = self.request("GET", f"/open?code={self.open_code}")
        self.assertEqual(status, 404)  # reused

    def test_two_viewers_on_loopback_keep_separate_sessions(self):
        """Closure finding 2: cookies are not isolated by port, so the cookie name carries the port."""
        first_cookie, first_port = self.cookie(), self.port  # self.request targets self.port
        self.start(ingest_handlers={})  # a second viewer on another port, same host name
        second_cookie, second_port = self.cookie(), self.port
        self.assertNotEqual(first_port, second_port)
        self.assertNotEqual(first_cookie.partition("=")[0], second_cookie.partition("=")[0])
        # A browser holds both cookies for 127.0.0.1 and sends them together to either viewer.
        both = {"Cookie": f"{first_cookie}; {second_cookie}"}
        self.assertEqual(self.request("GET", "/", both)[0], 200)
        self.port = first_port
        self.assertEqual(self.request("GET", "/", both)[0], 200)
        self.port = second_port
        # A viewer does not accept the other viewer's cookie.
        self.assertEqual(self.request("GET", "/", {"Cookie": first_cookie})[0], 404)

    def test_the_cookie_reads_but_does_not_ingest_and_the_token_ingests_but_does_not_read(self):
        cookie = self.cookie()
        status, _, body = self.request("GET", "/", {"Cookie": cookie})
        self.assertEqual((status, body), (200, b"<!doctype html>"))
        status, _, _ = self.request("GET", "/", {"Authorization": f"Bearer {self.token}"})
        self.assertEqual(status, 404)
        status, _, _ = self.request("POST", "/v1/logs", {**JSON, "Cookie": cookie}, b"{}")
        self.assertEqual(status, 404)
        status, _, body = self.post("/v1/logs", b'{"a": 1}')
        self.assertEqual(status, 200)
        self.assertEqual(self.received["/v1/logs"], [{"a": 1}])
        status, _, _ = self.request("GET", "/", {"Cookie": f"other=1; {cookie}; x=y"})
        self.assertEqual(status, 200)

    def test_a_refused_request_does_not_spend_the_open_code(self):
        status, _, _ = self.request("GET", f"/open?code={self.open_code}", host="evil.example:80")
        self.assertEqual(status, 403)
        status, _, _ = self.request("DELETE", f"/open?code={self.open_code}")
        self.assertEqual(status, 405)
        status, _, _ = self.request("GET", f"/open?code={self.open_code}&code=other")
        self.assertEqual(status, 404)
        self.cookie()

    def test_the_hook_response_body_is_always_empty(self):
        cookie = self.cookie()
        cases = [
            self.post("/hook/claude", b"{}"),
            self.post("/hook/claude", b"{}", token=False),
            self.post("/hook/claude", b"not json"),
            self.post("/hook/claude", b"{}", {"Content-Type": "text/plain"}),
            self.request("GET", "/hook/claude", {"Cookie": cookie}),
            self.request("PUT", "/hook/claude", {"Authorization": f"Bearer {self.token}"}),
            self.request("POST", "/hook/claude", JSON, b"{}", host="evil.example"),
        ]
        for index, (status, _, body) in enumerate(cases):
            with self.subTest(case=index, status=status):
                self.assertEqual(body, b"")


class RequestCheckTests(ServerCase):
    def test_allowed_hosts_are_exactly_the_three_loopback_names(self):
        cookie = {"Cookie": self.cookie()}
        for host in (f"127.0.0.1:{self.port}", f"localhost:{self.port}", f"[::1]:{self.port}"):
            with self.subTest(host=host):
                self.assertEqual(self.request("GET", "/", cookie, host=host)[0], 200)

    def test_foreign_hosts_are_refused_with_403_even_for_unknown_paths(self):
        cookie = {"Cookie": self.cookie()}
        for host in ("evil.example", f"evil.example:{self.port}", f"127.0.0.1:{self.port + 1}", "127.0.0.1",
                     f"LOCALHOST:{self.port}", f"127.0.0.1.evil.example:{self.port}", f"[::1]:{self.port + 1}"):
            with self.subTest(host=host):
                self.assertEqual(self.request("GET", "/", cookie, host=host)[0], 403)
                self.assertEqual(self.request("GET", "/nope", cookie, host=host)[0], 403)
        status, _, _ = self.raw(b"GET / HTTP/1.0\r\n\r\n")  # no Host header
        self.assertEqual(status, 403)

    def test_origin_and_sec_fetch_site_checks(self):
        cookie = {"Cookie": self.cookie()}
        same = f"http://127.0.0.1:{self.port}"
        self.assertEqual(self.request("GET", "/", {**cookie, "Origin": same})[0], 200)
        self.assertEqual(self.request("GET", "/", {**cookie, "Origin": f"http://localhost:{self.port}"},
                                      host=f"localhost:{self.port}")[0], 200)
        # the origin must match the Host the request used
        self.assertEqual(self.request("GET", "/", {**cookie, "Origin": f"http://localhost:{self.port}"})[0], 403)
        for origin in ("http://evil.example", "null", f"http://127.0.0.1:{self.port + 1}",
                       f"https://127.0.0.1:{self.port}", "http://127.0.0.1"):
            with self.subTest(origin=origin):
                self.assertEqual(self.request("GET", "/", {**cookie, "Origin": origin})[0], 403)
        for site in ("same-origin", "same-site", "none"):
            with self.subTest(site=site):
                self.assertEqual(self.request("GET", "/", {**cookie, "Sec-Fetch-Site": site})[0], 200)
        self.assertEqual(self.request("GET", "/", {**cookie, "Sec-Fetch-Site": "cross-site"})[0], 403)

    def test_ingest_requires_no_origin_but_refuses_a_foreign_one_and_changes_nothing(self):
        self.assertEqual(self.post("/hook/claude", b"{}")[0], 200)
        self.assertEqual(self.post("/hook/claude", b"{}", {"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.post("/v1/logs", b"{}", {"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.assertEqual(self.received["/v1/logs"], [])
        self.assertEqual(len(self.received["/hook/claude"]), 1)

    def test_methods_and_targets(self):
        cookie = {"Cookie": self.cookie()}
        self.assertEqual(self.request("POST", "/", {**cookie, **JSON}, b"{}")[0], 405)
        self.assertEqual(self.request("HEAD", "/", cookie)[0], 405)
        self.assertEqual(self.request("DELETE", "/web/app.js", cookie)[0], 405)
        self.assertEqual(self.request("PUT", "/events", cookie)[0], 405)
        self.assertEqual(self.request("GET", "/v1/logs", {"Authorization": f"Bearer {self.token}"})[0], 405)
        self.assertEqual(self.request("PUT", "/v1/metrics", {"Authorization": f"Bearer {self.token}"})[0], 405)
        self.assertEqual(self.request("GET", "/v1/logs", cookie)[0], 404)  # the route space is not revealed
        status, _, _ = self.raw(f"FROB / HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n\r\n".encode())
        self.assertEqual(status, 404)  # an unknown verb without credentials
        for target in (f"http://127.0.0.1:{self.port}/", "//evil.example/", "*"):
            with self.subTest(target=target):
                status, _, _ = self.raw(f"GET {target} HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n\r\n".encode())
                self.assertEqual(status, 404)


class HeaderTests(ServerCase):
    def check(self, response):
        csp = response.getheader("Content-Security-Policy")
        self.assertEqual(
            csp,
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; frame-ancestors 'self'; require-trusted-types-for 'script'")
        for name, value in CONTRACT_HEADERS.items():
            self.assertEqual(response.getheader(name), value, name)

    def test_every_response_carries_the_contract_headers(self):
        cookie = {"Cookie": self.cookie()}
        responses = [
            self.request("GET", "/", cookie)[1],                                  # 200
            self.request("GET", "/", None)[1],                                    # 404
            self.request("GET", "/", cookie, host="evil.example")[1],             # 403
            self.request("POST", "/", cookie)[1],                                 # 405
            self.request("GET", "/open?code=bad")[1],                             # 404
            self.post("/v1/logs", b"{", )[1],                                     # 400
            self.post("/hook/claude", b"{}")[1],                                  # 200 empty
            self.post("/v1/logs", b"{}", {"Content-Type": "text/plain"})[1],      # 415
            self.request("GET", "/web/nope.js", cookie)[1],                       # 404
        ]
        for response in responses:
            with self.subTest(status=response.status):
                self.check(response)

    def test_the_open_redirect_and_malformed_requests_carry_them_too(self):
        _, response, _ = self.request("GET", f"/open?code={self.open_code}")
        self.check(response)
        status, headers, _ = self.raw(b"GARBAGE\r\n\r\n")
        self.assertEqual(status, 400)
        for name, value in CONTRACT_HEADERS.items():
            self.assertEqual(headers[name], value)
        self.assertIn("content-security-policy", headers)

    def test_responses_do_not_advertise_a_server_version(self):
        _, response, _ = self.request("GET", "/")
        self.assertIsNone(response.getheader("Server"))

    def test_the_script_hash_is_added_for_the_import_map(self):
        self.stop()
        self.start(import_map_sha256=IMPORT_MAP_HASH)
        _, response, _ = self.request("GET", "/")
        self.assertIn(f"script-src 'self' 'sha256-{IMPORT_MAP_HASH}';", response.getheader("Content-Security-Policy"))

    def test_static_files_are_served_only_from_the_bundle(self):
        cookie = {"Cookie": self.cookie()}
        status, response, body = self.request("GET", "/web/app.js", cookie)
        self.assertEqual((status, body), (200, b"//js"))
        self.assertTrue(response.getheader("Content-Type").startswith("text/javascript"))
        for path in ("/web/other.js", "/web/", "/web", "/web/../index.html", "/web/%2e%2e/x", "/web/sub/app.js",
                     "/web/app.js/"):
            with self.subTest(path=path):
                self.assertEqual(self.request("GET", path, cookie)[0], 404)

    def test_bundle_names_must_be_plain_files(self):
        for name in ("../x", "a/b", "", ".hidden"):
            with self.subTest(name=name), self.assertRaises(ServeError):
                ViewServer(LoomStore(), self.runtime, bundle={name: b"x"})

    def test_registered_read_handlers_serve_and_unregistered_ones_404(self):
        self.stop()
        self.start(read_handlers={"/snapshot": lambda: (b'{"ok":true}', "application/json")})
        cookie = {"Cookie": self.cookie()}
        status, response, body = self.request("GET", "/snapshot", cookie)
        self.assertEqual((status, body), (200, b'{"ok":true}'))
        self.check(response)
        self.assertEqual(self.request("GET", "/frame.svg", cookie)[0], 404)


class IngestLimitTests(ServerCase):
    def test_content_type_and_encoding(self):
        for path in ("/v1/logs", "/v1/metrics", "/hook/claude"):
            with self.subTest(path=path):
                self.assertEqual(self.post(path, b"{}", {"Content-Type": "text/plain"})[0], 415)
                self.assertEqual(self.post(path, b"{}", {"Content-Type": "application/x-protobuf"})[0], 415)
                self.assertEqual(self.post(path, b"{}", {"Content-Encoding": "gzip"})[0], 415)
                self.assertEqual(self.post(path, b"{}", {"Content-Encoding": "br"})[0], 415)
                self.assertEqual(self.post(path, b"{}", {"Content-Encoding": "identity"})[0], 200)
                self.assertEqual(self.post(path, b"{}", {"Content-Type": "application/json; charset=utf-8"})[0], 200)
        self.assertEqual(self.post("/v1/logs", b"{}", {"Content-Type": ""})[0], 415)
        self.assertEqual(len(self.received["/v1/logs"]), 2)

    def test_missing_content_length_is_411(self):
        request = (f"POST /v1/logs HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
                   f"Authorization: Bearer {self.token}\r\n\r\n{{}}").encode()
        self.assertEqual(self.raw(request)[0], 411)
        self.refused_state_unchanged()

    def test_invalid_content_length_is_400_and_a_huge_one_413(self):
        base = (f"POST /v1/logs HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
                f"Authorization: Bearer {self.token}\r\nContent-Length: ")
        self.assertEqual(self.raw((base + "abc\r\n\r\n").encode())[0], 400)
        self.assertEqual(self.raw((base + "-1\r\n\r\n").encode())[0], 400)
        self.assertEqual(self.raw((base + "9" * 5000 + "\r\n\r\n").encode())[0], 413)
        self.refused_state_unchanged()

    def test_body_limits_are_checked_before_the_body_is_read(self):
        for path, limit in (("/v1/logs", 1024 * 1024), ("/v1/metrics", 1024 * 1024), ("/hook/claude", 256 * 1024)):
            with self.subTest(path=path):
                head = (f"POST {path} HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
                        f"Authorization: Bearer {self.token}\r\nContent-Length: {limit + 1}\r\n\r\n").encode()
                self.assertEqual(self.raw(head)[0], 413)  # no body sent: it is never read
        self.refused_state_unchanged()

    def test_bodies_at_the_limit_are_accepted(self):
        for path, limit in (("/v1/logs", 1024 * 1024), ("/hook/claude", 256 * 1024)):
            with self.subTest(path=path):
                prefix = b'{"pad":"'
                body = prefix + b"x" * (limit - len(prefix) - 2) + b'"}'
                self.assertEqual(len(body), limit)
                self.assertEqual(self.post(path, body)[0], 200)

    def test_a_short_body_is_refused(self):
        head = (f"POST /v1/logs HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
                f"Authorization: Bearer {self.token}\r\nContent-Length: 50\r\n\r\n{{}}").encode()
        self.assertEqual(self.raw(head)[0], 400)
        self.refused_state_unchanged()

    def test_strict_json(self):
        nested = lambda depth: b"[" * depth + b"]" * depth
        bad = {
            "malformed": b"{",
            "empty": b"",
            "duplicate members": b'{"a":1,"a":2}',
            "nested duplicate": b'{"a":{"b":1,"b":1}}',
            "Infinity": b'{"a":Infinity}',
            "-Infinity": b'{"a":-Infinity}',
            "NaN": b'{"a":NaN}',
            "1e400": b'{"a":1e400}',
            "-1e400": b'{"a":-1e400}',
            "depth 65": nested(65),
            "10000 nested arrays": nested(10_000),
            "nested objects": b'{"a":' * 100 + b"1" + b"}" * 100,
            "invalid utf-8": b'{"a":"\xff"}',
            "trailing text": b"{} {}",
            "huge integer": b'{"a":' + b"9" * 5000 + b"}",
        }
        for name, body in bad.items():
            for path in ("/v1/logs", "/hook/claude"):
                with self.subTest(name=name, path=path):
                    status, _, response = self.post(path, body)
                    self.assertEqual(status, 400)
                    if path == "/hook/claude":
                        self.assertEqual(response, b"")
        self.refused_state_unchanged()
        good = {
            "depth 64": nested(64),
            "brackets in strings": b'{"a":"[[[[ {{{{ \\" ]]]]"}',
            "scalar": b"1",
            "finite exponent": b'{"a":1e300}',
        }
        for name, body in good.items():
            with self.subTest(name=name):
                self.assertEqual(self.post("/v1/logs", body)[0], 200)

    def test_handler_refusals_map_to_their_status_and_store_nothing(self):
        self.stop()

        def refuse(status):
            def handler(body):
                raise IngestRefusal(status)
            return handler

        def crash(body):
            raise RuntimeError("secret detail")

        self.start(ingest_handlers={"/hook/claude": refuse(403), "/v1/logs": refuse(503),
                                    "/v1/metrics": crash})
        status, _, body = self.post("/hook/claude", b"{}")
        self.assertEqual((status, body), (403, b""))
        self.assertEqual(self.post("/v1/logs", b"{}")[0], 503)
        status, _, body = self.post("/v1/metrics", b"{}")
        self.assertEqual((status, body), (500, b""))
        with self.assertRaises(ValueError):
            IngestRefusal(200)

    def test_a_route_without_a_registered_handler_answers_404(self):
        self.stop()
        self.start()
        self.assertEqual(self.post("/v1/logs", b"{}")[0], 404)
        self.assertEqual(self.post("/hook/claude", b"{}")[0], 404)

    def test_otlp_success_is_an_empty_json_object_and_hook_success_is_empty(self):
        self.assertEqual(self.post("/v1/logs", b"{}")[2], b"{}")
        self.assertEqual(self.post("/hook/claude", b"{}")[2], b"")


class SubscriberAndConnectionTests(ServerCase):
    server_kwargs = {"heartbeat": 0.05}

    def open_stream(self, cookie):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        sock.sendall(f"GET /events HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nCookie: {cookie}\r\n\r\n".encode())
        return sock

    def read_until(self, sock, marker, limit=5.0):
        data = b""
        deadline = time.monotonic() + limit
        while marker not in data and time.monotonic() < deadline:
            chunk = sock.recv(4096)
            self.assertTrue(chunk, "the server closed the stream")
            data += chunk
        return data

    def test_ninth_subscriber_gets_503_and_a_slot_frees_when_one_leaves(self):
        cookie = self.cookie()
        streams = []
        self.addCleanup(lambda: [s.close() for s in streams])
        for _ in range(8):
            sock = self.open_stream(cookie)
            streams.append(sock)
            data = self.read_until(sock, b": connected")
            self.assertTrue(data.startswith(b"HTTP/1.0 200"))
            self.assertIn(b"text/event-stream", data)
        self.assertEqual(self.store.stats()["subscribers"], 8)
        status, response, body = self.request("GET", "/events", {"Cookie": cookie})
        self.assertEqual((status, body), (503, b""))
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        self.assertIn("Content-Security-Policy", dict(response.getheaders()))
        self.assertIn(b": heartbeat", self.read_until(streams[0], b": heartbeat"))
        streams.pop().close()
        deadline = time.monotonic() + 5
        while self.store.stats()["subscribers"] > 7 and time.monotonic() < deadline:
            time.sleep(0.02)  # the dropped client is noticed at its next heartbeat write
        sock = self.open_stream(cookie)
        streams.append(sock)
        self.assertTrue(self.read_until(sock, b": connected").startswith(b"HTTP/1.0 200"))

    def test_events_requires_the_read_cookie(self):
        self.assertEqual(self.request("GET", "/events")[0], 404)
        self.assertEqual(self.request("GET", "/events", {"Authorization": f"Bearer {self.token}"})[0], 404)
        self.assertEqual(self.store.stats()["subscribers"], 0)


class ConnectionLimitTests(ServerCase):
    server_kwargs = {"max_connections": 3, "socket_timeout": 0.5}

    def test_the_connection_over_the_limit_gets_503_and_slots_free_on_close(self):
        idle = [socket.create_connection(("127.0.0.1", self.port)) for _ in range(3)]
        self.addCleanup(lambda: [s.close() for s in idle])
        deadline = time.monotonic() + 5
        while self.server._connections < 3 and time.monotonic() < deadline:
            time.sleep(0.01)
        status, headers, body = self.raw(f"GET / HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n\r\n".encode())
        self.assertEqual((status, body), (503, b""))
        self.assertEqual(headers["cache-control"], "no-store")
        self.assertIn("content-security-policy", headers)
        for sock in idle:
            sock.close()
        deadline = time.monotonic() + 5
        status = 503
        while status == 503 and time.monotonic() < deadline:
            status, _, _ = self.request("GET", "/")
            time.sleep(0.05)
        self.assertEqual(status, 404)  # served again (no cookie)

    def test_an_idle_connection_is_closed_at_the_socket_timeout(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            started = time.monotonic()
            self.assertEqual(sock.recv(10), b"")
            self.assertLess(time.monotonic() - started, 3)

    def test_a_client_dripping_headers_is_closed_at_one_request_deadline(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            started = time.monotonic()
            closed = False
            sock.sendall(b"GET / HTTP/1.0\r\n")
            while time.monotonic() - started < 3 and not closed:
                time.sleep(0.2)  # each pause is below the 0.5 s read timeout, the total is not
                try:
                    sock.sendall(b"X-Drip: 1\r\n")
                    sock.settimeout(0.01)
                    closed = sock.recv(1) == b""
                except socket.timeout:
                    pass
                except OSError:
                    closed = True
            self.assertTrue(closed, "the connection outlived the request deadline")
            self.assertLess(time.monotonic() - started, 2)

    def test_a_client_dripping_the_body_is_refused_at_one_request_deadline(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall((f"POST /v1/logs HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\n"
                          f"Content-Type: application/json\r\nAuthorization: Bearer {self.token}\r\n"
                          "Content-Length: 100\r\n\r\n").encode())
            started = time.monotonic()
            answer = b""
            while time.monotonic() - started < 3 and not answer:
                time.sleep(0.2)
                try:
                    sock.sendall(b" ")
                    sock.settimeout(0.01)
                    answer = sock.recv(12)
                except socket.timeout:
                    pass
                except OSError:
                    break
            self.assertTrue(answer.startswith(b"HTTP/1.0 400"), answer)
            self.assertLess(time.monotonic() - started, 2)
        self.refused_state_unchanged()

    def test_a_normal_request_is_served_inside_the_deadline(self):
        self.assertEqual(self.request("GET", "/")[0], 404)
        self.assertEqual(self.post("/v1/logs", b"{}")[0], 200)

    def test_a_stalled_body_is_refused_with_400_at_the_socket_timeout_and_stores_nothing(self):
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall((f"POST /v1/logs HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\n"
                          f"Authorization: Bearer {self.token}\r\nContent-Length: 100\r\n\r\n{{").encode())
            self.assertTrue(sock.recv(12).startswith(b"HTTP/1.0 400"))
        self.refused_state_unchanged()


class LoggingTests(ServerCase):
    def test_nothing_is_written_to_stderr_or_stdout(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.request("GET", "/nope")
            self.request("GET", "/", host="evil.example")
            self.cookie()
            self.post("/v1/logs", b"{")
            self.post("/hook/claude", b"{}")
            self.raw(b"GARBAGE\r\n\r\n")
            with socket.create_connection(("127.0.0.1", self.port)) as sock:
                sock.sendall(b"GET / HTTP/1.0\r\nHost: x")  # abandoned mid-request
            time.sleep(0.1)
        self.assertEqual((out.getvalue(), err.getvalue()), ("", ""))


CORPUS = Path(__file__).resolve().parent / "fixtures/view/loom/valid-corpus.jsonl"


def corpus_events():
    return view_serve.replay_events(CORPUS.read_bytes())


def mark_unverified(events):
    return [{**event, "source": {**event["source"], "verification": "unverified"}} for event in events]


class Stream:
    """A raw SSE client: parses event frames incrementally and keeps what it has not handed out."""

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b""
        self.head_done = False
        self.ready = []
        self.blocks = []
        self.closed = False

    def __getattr__(self, name):
        return getattr(self.sock, name)

    def pump(self, limit):
        """Read one chunk; False when the server closed the stream or nothing arrived within `limit`."""
        self.sock.settimeout(limit)
        try:
            chunk = self.sock.recv(65536)
        except socket.timeout:
            return False
        if not chunk:
            self.closed = True
            return False
        self.buffer += chunk
        if not self.head_done and b"\r\n\r\n" in self.buffer:
            self.buffer = self.buffer.partition(b"\r\n\r\n")[2]
            self.head_done = True
        while self.head_done and b"\n\n" in self.buffer:
            block, _, self.buffer = self.buffer.partition(b"\n\n")
            if block.startswith(b"id: "):
                self.blocks.append(block)
                lines = block.split(b"\n")
                self.ready.append((int(lines[0][4:]), json.loads(lines[1][6:])))
        return True

    def frames(self, count, limit=5.0):
        deadline = time.monotonic() + limit
        while len(self.ready) < count and time.monotonic() < deadline and self.pump(limit):
            pass
        if len(self.ready) < count:
            raise AssertionError(f"expected {count} frames, got {len(self.ready)} (closed={self.closed})")
        taken, self.ready = self.ready[:count], self.ready[count:]
        return taken

    def drain(self, limit=1.0):
        """Everything that arrives until the stream closes or stays quiet for `limit` seconds."""
        while self.pump(limit):
            pass
        taken, self.ready = self.ready, []
        return taken


class StreamCase(ServerCase):
    """A server whose store holds the replayed corpus, with an SSE client."""
    server_kwargs = {"heartbeat": 0.05}

    def setUp(self):
        super().setUp()
        self.load()

    def restart(self, **store_kwargs):
        self.stop()
        self.store = LoomStore(**store_kwargs)
        self.start(**self.server_kwargs)
        self.load()

    def load(self):
        self.assertEqual(view_serve.load_replay(self.store, CORPUS.read_bytes()), len(corpus_events()))
        self.cookie_header = self.cookie()

    def open_stream(self, last_event_id=None):
        extra = "" if last_event_id is None else f"Last-Event-ID: {last_event_id}\r\n"
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        self.addCleanup(sock.close)
        sock.sendall((f"GET /events HTTP/1.0\r\nHost: 127.0.0.1:{self.port}\r\nCookie: {self.cookie_header}\r\n"
                      f"{extra}\r\n").encode())
        return Stream(sock)

    def frames(self, stream, count, limit=5.0):
        return stream.frames(count, limit)

    def idle(self, stream, seconds=0.3):
        """True when no event frame arrives within `seconds`."""
        return not (stream.ready or (stream.pump(seconds) and stream.ready))


class EventStreamTests(StreamCase):
    def test_a_new_client_receives_every_retained_event_once_in_order_then_live_events(self):
        sock = self.open_stream()
        got = self.frames(sock, len(corpus_events()))
        self.assertEqual([seq for seq, _ in got], list(range(1, len(corpus_events()) + 1)))
        self.assertEqual([event for _, event in got], self.store.replay())
        self.assertTrue(all(event["seq"] == seq for seq, event in got))
        stored = self.store.append(dict(corpus_events()[2], seq=1))
        (seq, event), = self.frames(sock, 1)
        self.assertEqual((seq, event), (stored["seq"], stored))

    def test_the_stream_response_is_an_event_stream_with_the_contract_headers(self):
        sock = self.open_stream()
        head = b""
        while b"\r\n\r\n" not in head:
            head += sock.recv(4096)
        text = head.decode().lower()
        self.assertTrue(text.startswith("http/1.0 200"))
        for expected in ("content-type: text/event-stream", "cache-control: no-store", "x-content-type-options: nosniff",
                         "content-security-policy:"):
            self.assertIn(expected, text)

    def test_resuming_with_last_event_id_neither_repeats_nor_skips(self):
        first = self.open_stream()
        read = self.frames(first, 10)
        first.close()
        last = read[-1][0]
        self.store.append(dict(corpus_events()[2], seq=1))
        head = self.store.stats()["headSeq"]
        resumed = self.open_stream(last)
        got = self.frames(resumed, head - last)
        self.assertEqual([seq for seq, _ in read] + [seq for seq, _ in got], list(range(1, head + 1)))
        self.assertTrue(self.idle(resumed))

    def test_resuming_at_the_newest_event_waits_for_a_new_one(self):
        sock = self.open_stream(self.store.stats()["headSeq"])
        self.assertTrue(self.idle(sock))
        stored = self.store.append(dict(corpus_events()[2], seq=1))
        self.assertEqual([seq for seq, _ in self.frames(sock, 1)], [stored["seq"]])

    def test_an_overflowed_ring_is_announced_by_a_ring_evicted_gap_and_resumes_from_it(self):
        self.restart(max_events=10)
        self.assertEqual(self.store.stats()["evicted"], len(corpus_events()) - 10)
        got = self.frames(self.open_stream(), 11)
        gap_id, gap = got[0]
        self.assertEqual((gap["kind"], gap["data"]["reason"]), ("observation.gap", "ring-evicted"))
        self.assertEqual((gap["data"]["fromSeq"], gap["data"]["toSeq"], gap_id), (1, 18, 18))
        self.assertEqual([seq for seq, _ in got[1:]], list(range(19, 29)))
        again = self.open_stream(gap_id)
        self.assertEqual([seq for seq, _ in self.frames(again, 10)], list(range(19, 29)))

    def test_a_resume_id_older_than_the_ring_gets_one_gap_for_the_evicted_range(self):
        self.restart(max_events=10)
        got = self.frames(self.open_stream(5), 11)
        data = got[0][1]["data"]
        self.assertEqual((data["reason"], data["fromSeq"], data["toSeq"]), ("ring-evicted", 6, 18))
        self.assertEqual([seq for seq, _ in got[1:]], list(range(19, 29)))

    def test_a_resume_id_the_store_has_not_reached_gets_the_full_retained_replay(self):
        count = len(corpus_events())
        for value in ("9999", str(10**30), "-1", "abc", "1.5", " ", "٣"):
            with self.subTest(last_event_id=value):
                got = self.frames(self.open_stream(value), count)
                self.assertEqual([seq for seq, _ in got], list(range(1, count + 1)))

    def test_every_frame_is_one_data_line_of_canonical_json(self):
        stream = self.open_stream()
        self.frames(stream, len(corpus_events()))
        self.assertEqual(len(stream.blocks), len(corpus_events()))
        for block in stream.blocks:
            lines = block.split(b"\n")
            self.assertEqual(len(lines), 2)
            self.assertEqual(lines[1][6:] + b"\n", view_loom.canonical_bytes(json.loads(lines[1][6:])))

    def test_heartbeats_continue_while_idle(self):
        sock = self.open_stream(self.store.stats()["headSeq"])
        deadline = time.monotonic() + 5
        data = b""
        while data.count(b": heartbeat") < 2 and time.monotonic() < deadline:
            data += sock.recv(4096)
        self.assertGreaterEqual(data.count(b": heartbeat"), 2)

    def test_a_closed_client_frees_its_subscriber_slot(self):
        sock = self.open_stream()
        self.frames(sock, 1)
        self.assertEqual(self.store.stats()["subscribers"], 1)
        sock.close()
        deadline = time.monotonic() + 5
        while self.store.stats()["subscribers"] and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertEqual(self.store.stats()["subscribers"], 0)

    def test_a_burst_beyond_the_subscriber_queue_loses_nothing_for_a_client_that_resumes(self):
        self.restart(subscriber_queue=2)
        sock = self.open_stream()
        self.frames(sock, len(corpus_events()))
        event = corpus_events()[2]
        for _ in range(50):
            self.store.append(dict(event, seq=1))
        ids = [seq for seq, _ in sock.drain(2)]
        last = ids[-1] if ids else len(corpus_events())
        self.assertEqual(ids, list(range(len(corpus_events()) + 1, last + 1)))
        head = self.store.stats()["headSeq"]
        resumed = self.open_stream(last)
        self.assertEqual([seq for seq, _ in self.frames(resumed, head - last)], list(range(last + 1, head + 1)))

    def test_events_fed_by_a_watched_directory_reach_the_client(self):
        root = Path(self.tmp.name) / "watched"
        root.mkdir()
        (root / "state.json").write_bytes(
            (Path(__file__).resolve().parent / "fixtures/view/artifacts/runtime-state-ready.json").read_bytes())
        sock = self.open_stream(self.store.stats()["headSeq"])
        self.assertEqual(view_tail.ArtifactTail(self.store, [root]).poll_once(), 1)
        ((seq, event),) = self.frames(sock, 1)
        self.assertEqual((event["kind"], event["source"]["verification"]), ("runtime.phase", "rehashed"))

    def test_shutdown_ends_open_streams(self):
        sock = self.open_stream()
        self.frames(sock, 1)
        self.server._closing.set()
        sock.settimeout(5)
        closed = False
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not closed:
            closed = sock.recv(65536) == b""
        self.assertTrue(closed)


class SnapshotTests(StreamCase):
    def get(self, cookie=True):
        return self.request("GET", "/snapshot", {"Cookie": self.cookie_header} if cookie else None)

    def test_snapshot_is_the_model_of_the_retained_events(self):
        status, response, body = self.get()
        self.assertEqual(status, 200)
        self.assertEqual(response.getheader("Content-Type"), "application/json")
        document = json.loads(body)
        self.assertEqual(document["model"], json.loads(json.dumps(build_model(self.store.replay()))))
        self.assertEqual(document["model"]["eventCount"], len(corpus_events()))
        self.assertIs(document["model"]["executionAuthorization"], False)
        self.assertEqual(document["droppedAttributeNames"], [])

    def test_snapshot_labels_the_elements_with_the_root_the_watcher_read_them_from(self):
        first, second = (Path(self.tmp.name) / name for name in ("one", "two"))
        fixture = Path(__file__).resolve().parent / "fixtures/view/artifacts/runtime-state-ready.json"
        for root in (first, second):
            root.mkdir()
            (root / "state.json").write_bytes(fixture.read_bytes())
        self.assertEqual(view_tail.ArtifactTail(self.store, [first, second]).poll_once(), 2)
        status, response, body = self.get()
        self.assertEqual(status, 200)
        elements = json.loads(body)["model"]["elements"]
        self.assertEqual(sorted(e["root"] for e in elements if e["root"]), ["root 1", "root 2"])
        self.assertEqual(sum(1 for e in elements if e["root"] is None), len(corpus_events()))
        self.assertNotIn(self.tmp.name.encode(), body)

    def test_snapshot_requires_the_read_cookie(self):
        self.assertEqual(self.get(cookie=False)[0], 404)
        self.assertEqual(self.request("GET", "/snapshot", {"Authorization": f"Bearer {self.token}"})[0], 404)

    def test_snapshot_follows_new_events(self):
        before = json.loads(self.get()[2])["model"]["eventCount"]
        self.store.append(dict(corpus_events()[2], seq=1))
        self.assertEqual(json.loads(self.get()[2])["model"]["eventCount"], before + 1)

    def test_snapshot_after_eviction_leads_with_the_gap(self):
        self.restart(max_events=10)
        model = json.loads(self.get()[2])["model"]
        self.assertEqual(model["eventCount"], 11)
        recorded = sum(e["data"].get("reason") == "ring-evicted" for e in corpus_events()[-10:])
        self.assertEqual(model["counters"]["gaps"]["byReason"]["ring-evicted"], recorded + 1)  # plus the derived gap

    def test_names_inventory_is_sorted_bounded_and_text_safe(self):
        names = ["zeta", "alpha", "alpha", "", "x" * 65, "bidi‮", "ctrl\x07", 7, "ok.name"]
        names += [f"n{i:03d}" for i in range(300)]
        self.stop()
        self.start(names_inventory=lambda: names)
        self.cookie_header = self.cookie()
        listed = json.loads(self.get()[2])["droppedAttributeNames"]
        self.assertEqual(len(listed), 256)
        self.assertEqual(listed, sorted(listed))
        for refused in ("", "x" * 65, "bidi‮", "ctrl\x07", 7):
            self.assertNotIn(refused, listed)
        self.assertEqual(listed[:3], ["alpha", "n000", "n001"])

    def test_a_failing_snapshot_answers_500_with_no_body(self):
        self.stop()
        self.start(names_inventory=lambda: 1 / 0)
        self.cookie_header = self.cookie()
        status, _, body = self.get()
        self.assertEqual((status, body), (500, b""))

    def test_the_replay_model_equals_the_live_model_of_the_same_events(self):
        live = LoomStore()
        for event in mark_unverified(corpus_events()):
            live.append(event)
        self.assertEqual(build_model(live.replay()), build_model(self.store.replay()))
        self.assertEqual(json.loads(self.get()[2])["model"], json.loads(json.dumps(build_model(live.replay()))))


class ReplayTests(unittest.TestCase):
    def test_every_replayed_event_is_unverified_whatever_the_file_says(self):
        data = CORPUS.read_bytes()
        original = {json.loads(line)["source"]["verification"] for line in data.splitlines()}
        self.assertEqual(original, {"rehashed", "derived", "unverified"})
        events = view_serve.replay_events(data)
        self.assertEqual({event["source"]["verification"] for event in events}, {"unverified"})
        store = LoomStore()
        self.assertEqual(view_serve.load_replay(store, data), len(events))
        self.assertEqual({e["source"]["verification"] for e in store.replay()}, {"unverified"})
        self.assertEqual([e["kind"] for e in store.replay()], [e["kind"] for e in events])

    def test_replayed_lanes_and_elements_carry_the_unverified_marker(self):
        store = LoomStore()
        view_serve.load_replay(store, CORPUS.read_bytes())
        model = build_model(store.replay())
        self.assertTrue(model["lanes"])
        self.assertTrue(all(lane["unverified"] for lane in model["lanes"]))
        self.assertTrue(all(element["unverified"] for element in model["elements"]))

    def test_a_refused_stream_stores_nothing(self):
        store = LoomStore()
        for name in ("duplicate-key", "decreasing-seq", "duplicate-seq", "nan"):
            with self.subTest(name=name), self.assertRaises(view_loom.LoomError):
                view_serve.load_replay(store, (CORPUS.parent / f"{name}.jsonl").read_bytes())
        self.assertEqual(store.stats()["headSeq"], 0)

    def test_replay_file_reading_refuses_links_and_non_regular_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "recording.jsonl"
            target.write_bytes(CORPUS.read_bytes())
            self.assertEqual(view_serve.read_replay_file(target), CORPUS.read_bytes())
            link = Path(tmp) / "link.jsonl"
            link.symlink_to(target)
            for refused in (link, Path(tmp), Path(tmp) / "missing.jsonl"):
                with self.subTest(path=refused.name), self.assertRaises(ServeError) as caught:
                    view_serve.read_replay_file(refused)
                self.assertEqual(caught.exception.reason, "replay-file")

    def test_replay_file_reading_bounds_the_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            big = Path(tmp) / "big.jsonl"
            big.write_bytes(b"x" * 100)
            original = view_serve.MAX_REPLAY_BYTES
            view_serve.MAX_REPLAY_BYTES = 99
            try:
                with self.assertRaises(ServeError):
                    view_serve.read_replay_file(big)
            finally:
                view_serve.MAX_REPLAY_BYTES = original


class VendorFileTests(ServerCase):
    """SPEC-061 T025: `/web/vendor/...` serves only files the vendor manifest lists, byte-checked at request time."""

    LISTED = {"three/a.js": b"export const a = 1;\n", "three/addons/b.js": b"export const b = 2;\n",
              "three/LICENSE": b"MIT\n"}

    def setUp(self):
        vendor_tmp = tempfile.TemporaryDirectory()
        self.addCleanup(vendor_tmp.cleanup)
        self.outside = Path(vendor_tmp.name) / "outside"
        self.outside.mkdir()
        (self.outside / "secret.js").write_bytes(b"secret")
        self.vendor = Path(vendor_tmp.name) / "vendor"
        for relative, content in self.LISTED.items():
            self.write(relative, content)
        self.write_manifest(self.listed_digests())
        self.server_kwargs = {"vendor_dir": self.vendor}
        super().setUp()

    def listed_digests(self):
        return {relative: hashlib.sha256(content).hexdigest() for relative, content in self.LISTED.items()}

    def write(self, relative, content):
        path = self.vendor / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def write_manifest(self, files, raw=None):
        text = raw if raw is not None else json.dumps({"package": "three", "files": files})
        (self.vendor / "manifest.json").write_text(text, encoding="utf-8")

    def restart(self):
        self.stop()
        self.start(vendor_dir=self.vendor)
        self._session = None

    def get(self, path, cookie=True):
        if cookie and getattr(self, "_session", None) is None:
            self._session = self.cookie()
        return self.request("GET", path, {"Cookie": self._session} if cookie else {})

    def assert_refused(self, path, status=404):
        result, response, body = self.get(path)
        self.assertEqual((result, body), (status, b""), path)
        for name, value in CONTRACT_HEADERS.items():
            self.assertEqual(response.getheader(name), value, name)
        self.assertIn("script-src 'self'", response.getheader("Content-Security-Policy"))

    def test_listed_files_with_a_matching_hash_are_served_to_a_session(self):
        for relative, content in self.LISTED.items():
            with self.subTest(relative=relative):
                status, response, body = self.get(f"/web/vendor/{relative}")
                self.assertEqual((status, body), (200, content))
                for name, value in CONTRACT_HEADERS.items():
                    self.assertEqual(response.getheader(name), value, name)
                self.assertEqual(response.getheader("Content-Length"), str(len(content)))
        _, response, _ = self.get("/web/vendor/three/a.js")
        self.assertTrue(response.getheader("Content-Type").startswith("text/javascript"))

    def test_a_listed_file_needs_the_read_cookie_like_the_rest_of_the_bundle(self):
        self.assertEqual(self.get("/web/vendor/three/a.js", cookie=False)[0], 404)
        session = {"Cookie": self.cookie()}
        self.assertEqual(self.request("POST", "/web/vendor/three/a.js", session)[0], 405)
        self.assertEqual(self.request("GET", "/web/vendor/three/a.js", session, host="evil.example")[0], 403)

    def test_files_the_manifest_does_not_list_are_refused_even_when_present(self):
        self.write("three/unlisted.js", b"x")
        for relative in ("three/unlisted.js", "manifest.json", "three", "three/", "three/addons", "", "nope.js"):
            with self.subTest(relative=relative):
                self.assert_refused(f"/web/vendor/{relative}")
        self.assert_refused("/web/vendor")

    def test_a_listed_file_whose_bytes_no_longer_match_is_refused_at_request_time(self):
        self.assertEqual(self.get("/web/vendor/three/a.js")[0], 200)
        self.write("three/a.js", b"export const a = 'tampered';\n")  # after the server started
        self.assert_refused("/web/vendor/three/a.js")
        self.assertEqual(self.get("/web/vendor/three/addons/b.js")[0], 200)  # the others are unaffected

    def test_a_missing_listed_file_is_refused(self):
        (self.vendor / "three/a.js").unlink()
        self.assert_refused("/web/vendor/three/a.js")

    def test_symbolic_links_are_refused_whatever_they_point_at(self):
        os.symlink(self.outside / "secret.js", self.vendor / "three/link.js")
        os.symlink(self.vendor / "three/a.js", self.vendor / "three/alias.js")  # same bytes, still a link
        os.symlink(self.outside, self.vendor / "linked")
        secret = hashlib.sha256(b"secret").hexdigest()
        files = self.listed_digests()
        files.update({"three/link.js": secret, "linked/secret.js": secret,
                      "three/alias.js": files["three/a.js"]})
        self.write_manifest(files)
        self.restart()
        for relative in ("three/link.js", "three/alias.js", "linked/secret.js"):
            with self.subTest(relative=relative):
                self.assert_refused(f"/web/vendor/{relative}")
        self.assertEqual(self.get("/web/vendor/three/a.js")[0], 200)

    def test_a_symbolic_link_as_the_vendor_directory_serves_nothing(self):
        real = self.vendor.with_name("real-vendor")
        self.vendor.rename(real)
        os.symlink(real, self.vendor)
        self.restart()
        self.assert_refused("/web/vendor/three/a.js")

    def test_path_traversal_and_odd_spellings_are_refused(self):
        for path in ("/web/vendor/../vendor/three/a.js", "/web/vendor/three/../three/a.js",
                     "/web/vendor/%2e%2e/outside/secret.js", "/web/vendor/three/%2e%2e/three/a.js",
                     "/web/vendor//three/a.js", "/web/vendor/three//a.js", "/web/vendor/three/a.js/",
                     "/web/vendor/three/a.js%00", "/web/vendor/three%2fa.js", "/web/vendor/three\\a.js",
                     "/web/vendor/THREE/a.js", "/web/vendor/./three/a.js", "/web/./vendor/three/a.js",
                     "/web/vendor/three/a.js/.."):
            with self.subTest(path=path):
                self.assert_refused(path)

    def test_manifest_entries_that_could_leave_the_vendor_directory_are_ignored(self):
        escape = hashlib.sha256(b"secret").hexdigest()
        files = self.listed_digests()
        files.update({"../outside/secret.js": escape, "/etc/hosts": escape, "three/../../outside/secret.js": escape,
                      "three//a.js": escape, ".hidden/x.js": escape, "three/.x.js": escape, "a\\b.js": escape,
                      "three/bad-digest.js": "nothex", "three/short.js": "ab" * 31, "three/upper.js": "AB" * 32,
                      "": escape, "three/": escape})
        self.write_manifest(files)
        self.write("three/.x.js", b"secret")
        self.restart()
        self.assertEqual(self.get("/web/vendor/three/a.js")[0], 200)
        for relative in ("../outside/secret.js", "outside/secret.js", "three/.x.js", "three/bad-digest.js",
                         "three/short.js", "three/upper.js", "three//a.js"):
            with self.subTest(relative=relative):
                self.assert_refused(f"/web/vendor/{relative}")
        self.assertEqual(set(self.server.vendor_files), set(self.LISTED))

    def test_a_manifest_that_is_missing_unreadable_or_malformed_lists_nothing(self):
        cases = {
            "not json": "{", "not an object": "[]", "no files": "{}", "files not an object": '{"files": []}',
            "duplicate member": '{"files": {"three/a.js": "%s", "three/a.js": "%s"}}' % (("0" * 64,) * 2),
            "non-finite": '{"files": {}, "x": NaN}',
        }
        for name, raw in cases.items():
            with self.subTest(name=name):
                self.write_manifest({}, raw=raw)
                self.restart()
                self.assertEqual(self.server.vendor_files, {})
                self.assert_refused("/web/vendor/three/a.js")
        (self.vendor / "manifest.json").unlink()
        self.restart()
        self.assert_refused("/web/vendor/three/a.js")

    def test_an_oversized_listed_file_is_refused(self):
        original = view_serve.MAX_VENDOR_FILE_BYTES
        self.addCleanup(setattr, view_serve, "MAX_VENDOR_FILE_BYTES", original)
        view_serve.MAX_VENDOR_FILE_BYTES = 8
        self.assert_refused("/web/vendor/three/a.js")

    def test_no_vendor_directory_serves_no_vendor_file(self):
        self.stop()
        self.start(vendor_dir=None)
        self._session = None
        self.assert_refused("/web/vendor/three/a.js")
        self.stop()
        self.start(vendor_dir=self.vendor.with_name("absent"))
        self._session = None
        self.assert_refused("/web/vendor/three/a.js")

    def test_flat_bundle_names_keep_working_and_a_nested_name_cannot_be_bundled(self):
        self.assertEqual(self.get("/web/app.js")[0], 200)
        with self.assertRaises(ServeError):
            ViewServer(LoomStore(), self.runtime, bundle={"vendor/three/a.js": b"x"})

    def test_the_default_vendor_directory_is_the_source_checkout_one(self):
        checkout = Path(__file__).resolve().parents[1] / "integrations/agent-braid-view/web/vendor"
        self.assertEqual(view_serve.VENDOR_DIR, checkout)
        self.assertTrue((checkout / "manifest.json").is_file())


class ContractTableTests(unittest.TestCase):
    def test_route_table_equals_the_contract_table(self):
        text = CONTRACT.read_text()
        section = text.split("## Routes", 1)[1].split("\n## ", 1)[0]
        rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in section.splitlines() if line.startswith("| ") and "---" not in line]
        contract = set()
        for method, route, credential, _effect in rows[1:]:
            for path in re.findall(r"`([^`]+)`", route):
                contract.add((method, path.partition("?")[0], credential))
        self.assertEqual(contract, set(view_serve.ROUTES))
        self.assertEqual(len(view_serve.ROUTES), len(contract))


if __name__ == "__main__":
    unittest.main()
