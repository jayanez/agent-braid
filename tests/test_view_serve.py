# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T016: loopback bind, credentials, request checks, headers, limits and the route table."""
import contextlib
import http.client
import io
import json
import os
import re
import socket
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path

from agent_braid import view_serve
from agent_braid.view_serve import IngestRefusal, ServeError, ViewServer
from agent_braid.view_store import LoomStore

CONTRACT = Path(__file__).resolve().parents[1] / "specs/061-activity-viewer/contracts/ui-security-privacy.md"
IMPORT_MAP_HASH = "A" * 43 + "="  # base64 of 32 bytes
CONTRACT_HEADERS = {
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "cache-control": "no-store",
}
JSON = {"Content-Type": "application/json"}


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
        headers = dict(headers or {})
        headers.setdefault("Host", host or f"127.0.0.1:{self.port}")
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response, response.read()
        finally:
            connection.close()

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
        status, _, _ = self.request("GET", "/", {"Cookie": f"{view_serve.COOKIE_NAME}=guess"})
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
        self.assertNotIn(self.open_code, response.getheader("Set-Cookie"))
        self.assertNotIn(self.token, response.getheader("Set-Cookie"))
        status, _, _ = self.request("GET", f"/open?code={self.open_code}")
        self.assertEqual(status, 404)  # reused

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
