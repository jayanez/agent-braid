# SPDX-License-Identifier: AGPL-3.0-only
"""The loopback activity-viewer server: credentials, request checks, limits and the route table.

This module is the HTTP boundary of the read-only activity viewer. It follows
specs/061-activity-viewer/contracts/ui-security-privacy.md; the refusal status table there is
normative. It binds only 127.0.0.1 or ::1, writes no access log, and has no route that executes,
grants, schedules or writes anything.

What lives here (SPEC-061 T016): the one-time open code exchanged for a read cookie, the ingest token
file and bearer check, `Host`, `Origin` and `Sec-Fetch-Site` checks, the response headers, body,
connection and timeout limits, strict JSON body parsing, and the route table with its refusals.
T017 adds Server-Sent Events on `/events` with `Last-Event-ID` resume, `/snapshot` (the viewer model
of the retained events plus the dropped-attribute names inventory) and replay loading.
What plugs in later: hook ingest (T019), OTLP ingest (T018), frames (T027) and the static bundle
(T024). They register through `read_handlers`, `ingest_handlers`, `bundle` and `names_inventory`;
a route with nothing registered answers 404.

Vendored code (SPEC-061 T025): `/web/vendor/<path>` serves a nested file of the vendored Three.js tree
only when `<path>` is listed in the vendor `manifest.json` and the bytes read at that request hash to
the listed SHA-256. Anything else (unlisted, hash mismatch, missing, symbolic link, spelling that is not
exactly a listed path, oversized) answers 404 with the contract headers, like an unknown bundle name.
Owner approval 2026-11-02, recorded in contracts/ui-security-privacy.md.

Event delivery: a client without `Last-Event-ID` receives every retained event (led by a
`ring-evicted` gap when some were lost) and then live events. Each frame is `id: <seq>` plus one
`data:` line of the canonical event JSON, so resuming from the last id repeats and skips nothing. The
contract defines no status for a `Last-Event-ID` the store has not reached (for example after a
server restart): it is answered with the full retained replay, as is an id that is not a number.
A subscriber that fell behind is closed and resumes with its last id.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import socket
import socketserver
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs

from agent_braid.view_loom import MAX_EVENTS, MAX_LINE_BYTES, MAX_SEQ, canonical_bytes, parse_stream
from agent_braid.view_ingest import INGEST_STATUSES, MAX_INVENTORY_NAME_LENGTH, MAX_INVENTORY_NAMES, IngestRefusal
from agent_braid.view_model import build_model
from agent_braid.view_paths import WEB_SOURCE_DIR, vendor_dir_of
from agent_braid.view_roots import replay_with_roots
from agent_braid.view_store import LoomStore, StoreError, SubscriberDropped

LOOPBACK_HOSTS = ("127.0.0.1", "::1")
MAX_CONNECTIONS = 32
SOCKET_TIMEOUT = 10.0
HEARTBEAT_SECONDS = 15.0
OTLP_BODY_LIMIT = 1024 * 1024
HOOK_BODY_LIMIT = 256 * 1024
MAX_JSON_DEPTH = 64
INGEST_TOKEN_NAME = "view-ingest-token"
COOKIE_PREFIX = "braid_view"  # each server names its own cookie "<prefix>_<port>"
HOOK_PATH = "/hook/claude"
EVENT_POLL_SECONDS = 0.25
_MAX_REQUEST_LINE = 65537  # the http.server request-line limit (its _MAXLINE + 1)
MAX_REPLAY_BYTES = MAX_EVENTS * (MAX_LINE_BYTES + 1)
VENDOR_PREFIX = "/web/vendor/"
VENDOR_DIR = vendor_dir_of(WEB_SOURCE_DIR)
VENDOR_MANIFEST = "manifest.json"
MAX_VENDOR_FILE_BYTES = 8 * 1024 * 1024
MAX_VENDOR_MANIFEST_BYTES = 64 * 1024
_VENDOR_PATH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")

# (method, route, credential): the contract's route table. "/web/<file>" is any bundle file name.
ROUTES: tuple[tuple[str, str, str], ...] = (
    ("GET", "/open", "open code"),
    ("GET", "/", "read cookie"),
    ("GET", "/web/<file>", "read cookie"),
    ("GET", "/events", "read cookie"),
    ("GET", "/snapshot", "read cookie"),
    ("GET", "/frame.svg", "read cookie"),
    ("GET", "/frame.txt", "read cookie"),
    ("POST", "/v1/logs", "ingest token"),
    ("POST", "/v1/metrics", "ingest token"),
    ("POST", HOOK_PATH, "ingest token"),
)
_BODY_LIMITS = {"/v1/logs": OTLP_BODY_LIMIT, "/v1/metrics": OTLP_BODY_LIMIT, HOOK_PATH: HOOK_BODY_LIMIT}
_KIND = {"open code": "open", "read cookie": "read", "ingest token": "ingest"}
_ROUTE_KIND = {route: _KIND[credential] for _, route, credential in ROUTES if "<" not in route}
_CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
    ".json": "application/json", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8",
}


UI_LANGUAGES = ("es", "en")
_LOCALE_VARIABLES = ("LC_ALL", "LC_MESSAGES", "LANG")
_LOCALE_TAG = re.compile(r"^([A-Za-z]{2,3})(?:[_.@-].*)?$")


def language_hint_from_environ(environ: Mapping[str, str]) -> str | None:
    """The viewer language (`es` or `en`) the process locale asks for, or None.

    Reads `LC_ALL`, then `LC_MESSAGES`, then `LANG` (the first one that is set and not empty wins, as for any
    program), like the terminal that started `view serve` sees them. Only a bare tag from the supported set leaves
    this function: never the full locale string, the environment or a path. `C` and `POSIX` ask for nothing.
    """
    for name in _LOCALE_VARIABLES:
        value = environ.get(name, "")
        if not value:
            continue
        match = _LOCALE_TAG.match(value.strip())
        language = match.group(1).lower() if match else ""
        return language if language in UI_LANGUAGES else None
    return None


class ServeError(RuntimeError):
    """The server could not be created; `reason` is a stable name."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


class BodyError(ValueError):
    """A request body is not acceptable JSON; the server answers 400."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise BodyError(f"duplicate member {key!r}")
        result[key] = value
    return result


def _reject_constant(token: str) -> Any:
    raise BodyError(f"non-finite number {token}")


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise BodyError(f"non-finite number {token}")
    return value


def _check_depth(data: bytes) -> None:
    """Refuse nesting beyond MAX_JSON_DEPTH by scanning, so no parser recursion is reachable."""
    depth = 0
    in_string = escaped = False
    for byte in data:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x5B, 0x7B):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise BodyError(f"nesting is deeper than {MAX_JSON_DEPTH}")
        elif byte in (0x5D, 0x7D):
            depth -= 1


def parse_json_body(data: bytes) -> Any:
    """Parse one JSON value, refusing duplicate members, non-finite numbers and excessive depth."""
    _check_depth(data)
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_no_duplicates,
                          parse_constant=_reject_constant, parse_float=_finite_float)
    except BodyError:
        raise
    except ValueError as exc:
        raise BodyError("body is not valid JSON") from exc


_TOKEN_SHAPE = re.compile(r"[A-Za-z0-9_-]{43}")  # secrets.token_urlsafe(32): 256 bits, url-safe base64


def _reusable_token(directory: int) -> str | None:
    """The token in `view-ingest-token` when it is safe to keep, else None.

    Safe means: a regular file reached without following a symlink, owned by this uid, mode exactly
    0600, and holding one well-formed token (the shape `secrets.token_urlsafe(32)` produces).
    """
    try:
        descriptor = os.open(INGEST_TOKEN_NAME, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except OSError:
        return None
    try:
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600 or info.st_nlink != 1 or info.st_size != 43):
            return None
        data = os.read(descriptor, 64)
    except OSError:
        return None
    finally:
        os.close(descriptor)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        return None
    return text if _TOKEN_SHAPE.fullmatch(text) else None


def _ingest_token_file(runtime_dir: Path, *, rotate: bool = False) -> tuple[Path, str, bool]:
    """`(path, token, reused)` for `<runtime_dir>/view-ingest-token`.

    The token is stable across restarts (SPEC-061 amendment 2026-11-04): an existing safe token file is
    reused, so a host that read the token once at shell start keeps working after a viewer restart.
    Otherwise, or with `rotate`, a new token replaces the file, created exclusively with mode 0600.
    """
    if not runtime_dir.is_absolute():
        raise ServeError("runtime-dir", "the runtime directory is an absolute path")
    try:
        try:
            os.mkdir(runtime_dir, 0o700)
        except FileExistsError:
            pass
        directory = os.open(runtime_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ServeError("runtime-dir", f"cannot open the runtime directory: {exc.strerror}") from exc
    token = secrets.token_urlsafe(32)
    temporary = f".{INGEST_TOKEN_NAME}.{os.getpid()}.{secrets.token_hex(4)}"
    try:
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ServeError("runtime-dir", "the runtime directory is owned by the user and private (0700)")
        existing = None if rotate else _reusable_token(directory)
        if existing is not None:
            return runtime_dir / INGEST_TOKEN_NAME, existing, True
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600,
                             dir_fd=directory)
        try:
            os.fchmod(descriptor, 0o600)
            os.write(descriptor, token.encode("ascii"))
        finally:
            os.close(descriptor)
        os.replace(temporary, INGEST_TOKEN_NAME, src_dir_fd=directory, dst_dir_fd=directory)
    except OSError as exc:
        try:
            os.unlink(temporary, dir_fd=directory)
        except OSError:
            pass
        raise ServeError("token-file", f"cannot write the ingest token: {exc.strerror}") from exc
    finally:
        os.close(directory)
    return runtime_dir / INGEST_TOKEN_NAME, token, False


def _valid_bundle(bundle: Mapping[str, bytes] | None) -> dict[str, bytes]:
    files = dict(bundle or {})
    for name, content in files.items():
        if (not name or "/" in name or "\\" in name or name.startswith(".")
                or not isinstance(content, bytes)):
            raise ServeError("bundle", f"{name!r} is not a plain file name with bytes content")
    return files


def replay_events(data: bytes) -> list[dict[str, Any]]:
    """Parse a recorded loom JSONL stream (all or nothing) with every event marked `unverified`."""
    events = parse_stream(data)
    for event in events:
        event["source"]["verification"] = "unverified"  # the viewer never re-hashed a replayed event
        if event["kind"] == "strand.update":
            # Contract v0.2, OD-V4: tool duration lives in memory only and is absent from replays.
            event["data"].pop("toolDurationMs", None)
    return events


def load_replay(store: LoomStore, data: bytes) -> int:
    """Append a recorded stream to `store` as `unverified` events; return how many were stored."""
    return sum(store.append(event) is not None for event in replay_events(data))


def read_replay_file(path: str | os.PathLike[str]) -> bytes:
    """Read a recorded stream: a regular file, not a symbolic link, within the stream size bound."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise ServeError("replay-file", f"cannot open the replay file: {exc.strerror}") from exc
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_REPLAY_BYTES:
            raise ServeError("replay-file", "the replay file must be a regular file within the stream size bound")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(MAX_REPLAY_BYTES + 1)
    except OSError as exc:
        raise ServeError("replay-file", f"cannot read the replay file: {exc.strerror}") from exc
    finally:
        os.close(descriptor)
    if len(data) > MAX_REPLAY_BYTES:
        raise ServeError("replay-file", "the replay file grew beyond the stream size bound")
    return data


def _open_nofollow(name: str, directory: int, *, directory_flag: int = 0) -> int:
    return os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | directory_flag, dir_fd=directory)


def _read_beneath(root: Path, relative: str, limit: int) -> bytes | None:
    """Read `relative` under `root` without following a symbolic link at any component; None on any problem."""
    parts = relative.split("/")
    try:
        current = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        for part in parts[:-1]:
            following = _open_nofollow(part, current, directory_flag=os.O_DIRECTORY)
            os.close(current)
            current = following
        descriptor = _open_nofollow(parts[-1], current)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                return None
            with os.fdopen(descriptor, "rb", closefd=False) as stream:
                data = stream.read(limit + 1)
        finally:
            os.close(descriptor)
    except OSError:
        return None
    finally:
        os.close(current)
    return data if len(data) <= limit else None


def load_vendor_manifest(vendor_dir: str | os.PathLike[str] | None) -> dict[str, str]:
    """The `{relative path: sha256}` entries of `<vendor_dir>/manifest.json` that are safe to serve.

    A missing, unreadable, oversized or malformed manifest lists nothing. Entries whose path is not a plain
    relative path of simple components (no empty, dot or hidden component, no backslash) or whose digest is
    not 64 lowercase hex digits are dropped.
    """
    if vendor_dir is None:
        return {}
    data = _read_beneath(Path(vendor_dir), VENDOR_MANIFEST, MAX_VENDOR_MANIFEST_BYTES)
    if data is None:
        return {}
    try:
        document = parse_json_body(data)
    except BodyError:
        return {}
    files = document.get("files") if isinstance(document, dict) else None
    if not isinstance(files, dict):
        return {}
    return {path: digest for path, digest in files.items()
            if _VENDOR_PATH.fullmatch(path) and isinstance(digest, str) and _SHA256_HEX.fullmatch(digest)}


class ViewServer(ThreadingHTTPServer):
    """Loopback-only HTTP server for the activity viewer. Call `serve_forever` to run it."""

    daemon_threads = True

    def __init__(self, store: LoomStore, runtime_dir: str | os.PathLike[str], *,
                 host: str = "127.0.0.1", port: int = 0,
                 bundle: Mapping[str, bytes] | None = None,
                 vendor_dir: str | os.PathLike[str] | None = VENDOR_DIR,
                 read_handlers: Mapping[str, Callable[[], tuple[bytes, str]]] | None = None,
                 ingest_handlers: Mapping[str, Callable[[Any], None]] | None = None,
                 names_inventory: Callable[[], Iterable[str]] | None = None,
                 import_map_sha256: str | None = None,
                 language_hint: str | None = None,
                 rotate_token: bool = False,
                 live_clock: Callable[[], int] | None = None,
                 max_connections: int = MAX_CONNECTIONS, socket_timeout: float = SOCKET_TIMEOUT,
                 heartbeat: float = HEARTBEAT_SECONDS) -> None:
        if host not in LOOPBACK_HOSTS:
            raise ServeError("bind-refused", "the viewer binds 127.0.0.1 or ::1 only")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ServeError("bind-refused", "port is between 0 and 65535")
        if max_connections < 1 or socket_timeout <= 0 or heartbeat <= 0:
            raise ValueError("limits are positive")
        self.store = store
        self.bundle = _valid_bundle(bundle)
        self.vendor_dir = None if vendor_dir is None else Path(vendor_dir)
        self.vendor_files = load_vendor_manifest(self.vendor_dir)
        self.read_handlers = dict(read_handlers or {})
        self.ingest_handlers = dict(ingest_handlers or {})
        self.names_inventory = names_inventory
        # T060: the live server clock in ms on the events' monotonic basis; None serves a replay (`axis.live` false).
        self.live_clock = live_clock
        self.language_hint = language_hint if language_hint in UI_LANGUAGES else None
        self.max_connections = max_connections
        self.socket_timeout = socket_timeout
        self.heartbeat = heartbeat
        self._csp = self._policy(import_map_sha256)
        self._lock = threading.Lock()
        self._connections = 0
        self._closing = threading.Event()
        self._open_code: str | None = secrets.token_urlsafe(32)
        self._read_token: str | None = None
        self.address_family = socket.AF_INET6 if host == "::1" else socket.AF_INET
        super().__init__((host, port), _Handler)
        self.port = self.server_address[1]
        # Cookies are not isolated by port: two viewers on loopback would overwrite each other's session.
        self.cookie_name = f"{COOKIE_PREFIX}_{self.port}"
        self._hosts = frozenset({f"127.0.0.1:{self.port}", f"[::1]:{self.port}", f"localhost:{self.port}"})
        self.url_host = f"[::1]:{self.port}" if host == "::1" else f"127.0.0.1:{self.port}"
        try:
            self.token_path, self._ingest_token, self.token_reused = _ingest_token_file(
                Path(runtime_dir), rotate=rotate_token)
        except ServeError:
            self.server_close()
            raise

    @staticmethod
    def _policy(import_map_sha256: str | None) -> str:
        script = "'self'"
        if import_map_sha256 is not None:
            try:
                valid = len(base64.b64decode(import_map_sha256, validate=True)) == 32
            except ValueError:
                valid = False
            if not valid:
                raise ServeError("csp", "import_map_sha256 is the base64 of a SHA-256 digest")
            script += f" 'sha256-{import_map_sha256}'"
        return (f"default-src 'self'; script-src {script}; style-src 'self'; img-src 'self' data:; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'; "
                "require-trusted-types-for 'script'")

    @property
    def open_url(self) -> str:
        """The URL printed once at start. It embeds the single-use open code; do not log it elsewhere."""
        return f"http://{self.url_host}/open?code={self._open_code}"

    @property
    def ingest_token(self) -> str:
        """The bearer token held in `token_path` (reused across restarts unless rotated); never log it."""
        return self._ingest_token

    def response_headers(self) -> list[tuple[str, str]]:
        return [("Content-Security-Policy", self._csp), ("X-Content-Type-Options", "nosniff"),
                ("Referrer-Policy", "no-referrer"), ("Cache-Control", "no-store"),
                ("Connection", "close")]

    def read_vendor(self, relative: str) -> bytes | None:
        """The bytes of a manifest-listed vendored file, or None unless they hash to the listed SHA-256."""
        digest = self.vendor_files.get(relative)
        if digest is None or self.vendor_dir is None:
            return None
        data = _read_beneath(self.vendor_dir, relative, MAX_VENDOR_FILE_BYTES)
        if data is None or not hmac.compare_digest(hashlib.sha256(data).hexdigest(), digest):
            return None
        return data

    def snapshot(self) -> tuple[bytes, str]:
        """`/snapshot`: the model of the retained events and the dropped-attribute names inventory."""
        names = sorted({name for name in (self.names_inventory() if self.names_inventory else ())
                        if isinstance(name, str) and 0 < len(name) <= MAX_INVENTORY_NAME_LENGTH
                        and name.isprintable()})[:MAX_INVENTORY_NAMES]
        events, roots = replay_with_roots(self.store)  # the watcher's root labels, read together with the events
        document: dict[str, Any] = {"droppedAttributeNames": names, "model": build_model(
            events, roots=roots, now_ms=None if self.live_clock is None else self.live_clock())}
        if self.language_hint is not None:
            document["uiLanguageHint"] = self.language_hint
        body = json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
        return body.encode("utf-8"), "application/json"

    # -- credentials -----------------------------------------------------------------------

    @staticmethod
    def _same(left: str | None, right: str | None) -> bool:
        return left is not None and right is not None and hmac.compare_digest(
            left.encode("utf-8"), right.encode("utf-8"))

    def open_code_valid(self, code: str) -> bool:
        with self._lock:
            return self._same(code, self._open_code)

    def exchange_open_code(self, code: str) -> str | None:
        """Spend the open code; return the read cookie value, or None for any other code."""
        with self._lock:
            if not self._same(code, self._open_code):
                return None
            self._open_code = None
            self._read_token = secrets.token_urlsafe(32)
            return self._read_token

    def read_cookie_valid(self, value: str) -> bool:
        with self._lock:
            return self._same(value, self._read_token)

    def ingest_token_valid(self, value: str) -> bool:
        return self._same(value, self._ingest_token)

    # -- connections -----------------------------------------------------------------------

    def server_bind(self) -> None:
        socketserver.TCPServer.server_bind(self)  # skips HTTPServer's reverse-DNS lookup
        self.server_name, self.server_port = self.server_address[:2]

    def process_request(self, request: Any, client_address: Any) -> None:
        with self._lock:
            full = self._connections >= self.max_connections
            if not full:
                self._connections += 1
        if full:
            self._refuse_connection(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self._lock:
                self._connections -= 1  # the worker thread never started
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._lock:
                self._connections -= 1

    def _refuse_connection(self, request: socket.socket) -> None:
        lines = ["HTTP/1.0 503 Service Unavailable", "Content-Length: 0"]
        lines += [f"{name}: {value}" for name, value in self.response_headers()]
        try:
            request.settimeout(0.05)
            request.sendall(("\r\n".join(lines) + "\r\n\r\n").encode("ascii"))
            request.shutdown(socket.SHUT_WR)
            request.recv(4096)  # drain so closing does not reset the connection under the answer
        except OSError:
            pass
        self.shutdown_request(request)

    def handle_error(self, request: Any, client_address: Any) -> None:
        pass  # no traceback or log output: the viewer writes nothing to the console per request

    def shutdown(self) -> None:
        self._closing.set()
        super().shutdown()

    def server_close(self) -> None:
        self._closing.set()
        super().server_close()


class _DeadlineReader:
    """The request input stream with one deadline for the whole request, not one timeout per read.

    Every socket read still times out at `timeout`, and no read may outlast the deadline `timeout` seconds
    after the connection was accepted. A client that sends one byte at a time therefore cannot hold a
    connection slot for longer than `timeout`. Running out of time raises TimeoutError, as a slow read does.
    """

    def __init__(self, stream: Any, connection: socket.socket, timeout: float) -> None:
        self._stream = stream
        self._connection = connection
        self._timeout = timeout
        self._deadline = time.monotonic() + timeout

    def _one_receive(self, action: Callable[[], bytes]) -> bytes:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("the request deadline passed")
        self._connection.settimeout(min(self._timeout, remaining))
        try:
            return action()
        finally:
            self._connection.settimeout(self._timeout)  # writes (event stream) keep the per-operation timeout

    def readline(self, limit: int = -1) -> bytes:
        if limit is None or limit < 0:
            limit = _MAX_REQUEST_LINE
        line = bytearray()
        while len(line) < limit:
            buffered = self._one_receive(lambda: self._stream.peek(1))  # at most one receive
            if not buffered:
                break
            window = buffered[:limit - len(line)]
            end = window.find(b"\n")
            take = len(window) if end < 0 else end + 1
            line += self._stream.read(take)  # bytes already buffered: no further receive
            if end >= 0:
                break
        return bytes(line)

    def read(self, size: int = -1) -> bytes:
        parts: list[bytes] = []
        while size < 0 or size > 0:
            chunk = self._one_receive(lambda: self._stream.read1(65536 if size < 0 else size))
            if not chunk:
                break
            parts.append(chunk)
            size -= len(chunk) if size > 0 else 0
        return b"".join(parts)

    def close(self) -> None:
        self._stream.close()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"  # one request per connection; no keep-alive holding a slot
    server: ViewServer

    def setup(self) -> None:
        self.timeout = self.server.socket_timeout
        super().setup()
        self.rfile = _DeadlineReader(self.rfile, self.connection, self.timeout)

    def log_message(self, format: str, *args: Any) -> None:
        pass  # access logging is off

    def __getattr__(self, name: str) -> Any:
        if name.startswith("do_"):
            return lambda: self._dispatch(name[3:])
        raise AttributeError(name)

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        self._send(code)  # malformed request lines and headers: contract headers, empty body

    def _send(self, status: int, body: bytes = b"", content_type: str | None = None,
              extra: tuple[tuple[str, str], ...] = ()) -> None:
        if getattr(self, "path", "").partition("?")[0] == HOOK_PATH:
            body = b""  # every response on a hook route has an empty body
        if self.request_version == "HTTP/0.9":
            self.request_version = "HTTP/1.0"  # always answer with a status line and the contract headers
        self.send_response_only(status)
        for name, value in self.server.response_headers():
            self.send_header(name, value)
        for name, value in extra:
            self.send_header(name, value)
        if body and content_type:
            self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body and self.command != "HEAD":
            self.wfile.write(body)
        self.close_connection = True

    # -- request checks --------------------------------------------------------------------

    def _loopback_request(self) -> bool:
        server = self.server
        host, origin = self.headers.get("Host"), self.headers.get("Origin")
        return (host in server._hosts
                and (origin is None or origin == f"http://{host}")
                and self.headers.get("Sec-Fetch-Site") != "cross-site")

    def _read_authorized(self) -> bool:
        for header in self.headers.get_all("Cookie", []):
            for part in header.split(";"):
                name, _, value = part.strip().partition("=")
                if name == self.server.cookie_name and self.server.read_cookie_valid(value):
                    return True
        return False

    def _ingest_authorized(self) -> bool:
        scheme, _, token = (self.headers.get("Authorization") or "").partition(" ")
        return scheme.lower() == "bearer" and self.server.ingest_token_valid(token.strip())

    # -- routing ---------------------------------------------------------------------------

    def _dispatch(self, method: str) -> None:
        path, _, query = self.path.partition("?")
        if not self._loopback_request():
            return self._send(403)
        kind = _ROUTE_KIND.get(path)
        if kind is None and (
                path.startswith("/web/") and path[5:] in self.server.bundle
                or path.startswith(VENDOR_PREFIX) and path[len(VENDOR_PREFIX):] in self.server.vendor_files):
            kind = "read"
        if kind is None:
            return self._send(404)
        if kind == "open":
            return self._open(method, query)
        if kind == "read":
            if not self._read_authorized():
                return self._send(404)
            if method != "GET":
                return self._send(405)
            return self._read(path)
        if not self._ingest_authorized():
            return self._send(404)
        if method != "POST":
            return self._send(405)
        self._ingest(path)

    def _open(self, method: str, query: str) -> None:
        codes = parse_qs(query, keep_blank_values=True).get("code", [])
        if len(codes) != 1 or not self.server.open_code_valid(codes[0]):
            return self._send(404)
        if method != "GET":
            return self._send(405)
        token = self.server.exchange_open_code(codes[0])
        if token is None:
            return self._send(404)
        cookie = f"{self.server.cookie_name}={token}; HttpOnly; SameSite=Strict; Path=/"
        self._send(303, extra=(("Location", "/"), ("Set-Cookie", cookie)))

    def _read(self, path: str) -> None:
        server = self.server
        if path == "/events":
            return self._events()
        if path.startswith(VENDOR_PREFIX):
            content = server.read_vendor(path[len(VENDOR_PREFIX):])
            if content is None:
                return self._send(404)
            return self._send(200, content, _CONTENT_TYPES.get(os.path.splitext(path)[1], "application/octet-stream"))
        if path == "/" or path.startswith("/web/"):
            name = "index.html" if path == "/" else path[5:]
            content = server.bundle.get(name)
            if content is None:
                return self._send(404)
            suffix = os.path.splitext(name)[1]
            return self._send(200, content, _CONTENT_TYPES.get(suffix, "application/octet-stream"))
        reader = server.read_handlers.get(path)
        if reader is None and path == "/snapshot":
            reader = server.snapshot
        if reader is None:
            return self._send(404)
        try:
            body, content_type = reader()
        except Exception:
            return self._send(500)
        self._send(200, body, content_type)

    def _resume_point(self) -> int:
        """The seq after which to deliver; 0 (everything retained) when absent or not a usable number."""
        raw = (self.headers.get("Last-Event-ID") or "").strip()
        if raw.isascii() and raw.isdigit() and len(raw) <= 16 and int(raw) <= MAX_SEQ:
            return int(raw)
        return 0

    def _events(self) -> None:
        store = self.server.store
        try:
            try:
                subscriber = store.subscribe(after_seq=self._resume_point())
            except StoreError as exc:
                if exc.reason != "resume-ahead":
                    raise
                subscriber = store.subscribe(after_seq=0)  # an id from before a restart: replay everything
        except StoreError:
            return self._send(503)
        try:
            self.send_response_only(200)
            for name, value in self.server.response_headers():
                self.send_header(name, value)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(b": connected\n\n")
            last_write = time.monotonic()
            while not self.server._closing.is_set():
                try:
                    item = subscriber.get(timeout=min(EVENT_POLL_SECONDS, self.server.heartbeat))
                except SubscriberDropped:
                    break  # too slow or closed: the client resumes with its last id
                now = time.monotonic()
                if item is not None:
                    self.wfile.write(b"id: %d\ndata: %s\n\n" % (item["seq"], canonical_bytes(item).rstrip(b"\n")))
                    last_write = now
                elif now - last_write >= self.server.heartbeat:
                    self.wfile.write(b": heartbeat\n\n")
                    last_write = now
        except OSError:
            pass  # cannot be written: the subscriber is dropped
        finally:
            subscriber.close()
            self.close_connection = True

    def _ingest(self, path: str) -> None:
        handler = self.server.ingest_handlers.get(path)
        if handler is None:
            return self._send(404)  # nothing registered for this route yet
        media = (self.headers.get("Content-Type") or "").partition(";")[0].strip().lower()
        encoding = (self.headers.get("Content-Encoding") or "identity").strip().lower()
        if media != "application/json" or encoding != "identity":
            return self._send(415)
        declared = self.headers.get("Content-Length")
        if declared is None:
            return self._send(411)
        if not declared.isascii() or not declared.isdigit():
            return self._send(400)
        length = int(declared) if len(declared) < 12 else _BODY_LIMITS[path] + 1
        if length > _BODY_LIMITS[path]:
            return self._send(413)
        try:
            data = self.rfile.read(length)
        except OSError:
            return self._send(400)  # timed out or reset before the declared body arrived
        if len(data) != length:
            return self._send(400)
        try:
            parsed = parse_json_body(data)
        except BodyError:
            return self._send(400)
        try:
            handler(parsed)
        except IngestRefusal as refusal:
            return self._send(refusal.status)
        except Exception:
            return self._send(500)
        self._send(200, b"{}", "application/json")


__all__ = ["BodyError", "IngestRefusal", "ROUTES", "ServeError", "ViewServer", "load_replay", "parse_json_body",
           "read_replay_file", "replay_events"]
