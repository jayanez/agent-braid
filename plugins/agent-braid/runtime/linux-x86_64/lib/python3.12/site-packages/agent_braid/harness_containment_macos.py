# SPDX-License-Identifier: AGPL-3.0-only
"""macOS containment backend: dedicated user plus deny-default ``sandbox-exec`` (SPEC-065 T005).

One ``ContainmentPolicy`` built from the SPEC-065 founder decisions (NC-1 to NC-11)
renders the SBPL profile, the child environment, the rlimits and the environment hash.
Both entry points share it: ``run`` executes an owned laboratory fixture with the pinned
interpreter, ``launch`` executes the pinned Claude executable for the native transport.

* filesystem: deny-default; writes only in the run's candidate directory, its private
  ``TMPDIR`` and (``launch`` only) the dedicated user's ``CLAUDE_CONFIG_DIR`` (NC-7);
  reads add the pinned executables, narrowed system library paths and the root
  directory entry that dyld opens; metadata only on ancestors; ``/System/Volumes/Data``
  (the data-volume firmlink) is denied explicitly.
* network: deny-default; the only egress is TCP to the loopback ``EgressProxy`` port,
  which it holds on ``127.0.0.1`` and ``::1`` and which admits ``CONNECT`` to the listed
  endpoints only when the TLS SNI equals the CONNECT host (NC-1). DNS, UDP, other
  loopback ports, Unix sockets, ``sysctl`` and every ``mach-lookup`` stay denied.
* credential: UID separation (the supervisor must run as the dedicated account, NC-2,
  NC-5), an environment built from scratch, and a refusal when an ``ENV_DENY`` variable
  is present in the parent. Keychain services are not reachable (no ``mach-lookup``);
  whether NC-5's login works without them is for the T007/T009 probes.
* process: exec allow-list (NC-8), CPU, file-size, core, open-file and per-user process
  rlimits applied before the sandbox is entered, a supervisor watchdog for wall time,
  memory (macOS refuses ``RLIMIT_AS`` below the current address space) and output, and
  settlement of the group plus every new process of the dedicated user.

Before every run the backend takes an exclusive lock on ``run_root`` and re-verifies both
trusted qualification records, the OS window, the account, the mechanism and executable
hashes, the recomputed environment hash, a profile compile check that must report the
exec of ``/usr/bin/false`` as denied, and the NC-11 probe subset through the injected
T007 probe runner. Any failure refuses with a fixed ``LabError`` reason before the child
starts and is appended to ``run_evidence``. It never degrades and never falls back to
``SimulatedContainment``. The observed Claude version is checked by the T006 transport;
here the version is a pinned policy value. Whether the profile enforces each effect is
decided by the T007/T009 probes and the human records, never here. ``run_fixture``
creates its workdir with ``tempfile``, so the supervisor's ``TMPDIR`` must be ``run_root``.
"""
from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import ctypes
from dataclasses import asdict, dataclass
import fcntl
import hashlib
from hashlib import sha256
import os
from pathlib import Path
import platform
import pwd
import re
import selectors
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from typing import NoReturn

from . import harness_host_claude, harness_lab
from .harness_host_claude import ENV_DENY, ClaudeHostError, HostRun, verify_host_qualification
from .harness_lab import (ChildResult, ContainmentBackend, FixtureLimits, LabError, Qualification,
                          _require, _settle, verify_qualification)
from .system_one import canonical

BACKEND = "macos-dedicated-user-sandbox-exec"
ENVIRONMENT_FORMAT = "braid-macos-containment-environment/v0.1"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
CREDENTIAL_METHOD = "dedicated-user-own-login"  # NC-5
CLAUDE_VERSION = "2.1.292"  # NC-4
ALLOWED_ENDPOINTS = ("api.anthropic.com:443",)  # NC-1; refresh hosts come from probe evidence
# NC-8; memory is enforced by the supervisor watchdog, the rest by rlimits.
LIMITS = {"wallSeconds": 1800, "cpuSeconds": 1800, "memoryBytes": 4 << 30,
          "fileSizeBytes": 64 << 20, "openFiles": 256, "descendants": 16}
F4_PROBES = (("FS-01", "denied"), ("NET-01", "denied"), ("CRED-01", "denied"),
             ("PROC-01", "denied"), ("NET-06", "allowed"))  # NC-11
SYSTEM_READ = ("/usr/lib", "/System/Library", "/System/Cryptexes", "/System/Volumes/Preboot/Cryptexes",
               "/private/var/db/dyld", "/Library/Apple")
DENIED = ("/System/Volumes/Data",)
COMPILE_PROBE = "/usr/bin/false"  # never allow-listed: its exec must be denied
ENTRIES = ("fixture", "launch")
MAX_LAUNCH_STDIN_BYTES = 1 << 20
MAX_LAUNCH_OUTPUT_BYTES = 16 << 20
EXIT_SANDBOX_COMPILE = 65
EXIT_SANDBOX_EXEC_DENIED = 71
_MECHANISM_UID = 0  # sandbox-exec must be root-owned
_SHARED_WRITE = stat.S_IWGRP | stat.S_IWOTH
_OS_SERIES = re.compile(r"27\.0(?:\.\d{1,3})?\Z")  # NC-3
_BUILD = re.compile(r"[0-9]{2}[A-Z][0-9]{1,5}[a-z]?\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ACCOUNT = re.compile(r"[a-z_][a-z0-9_-]{0,31}\Z")
_PATH = re.compile(r"(?:/[A-Za-z0-9._@+-]+)+\Z")  # no quotes, spaces or escapes in SBPL
_ENDPOINT = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+:443\Z")
_RESERVED = ("run-", "compile-", ".")  # run_root entries the backend owns
_POLL_SECONDS = 0.05
_STREAM_CHUNK_BYTES = 65_536  # per read, so a large output bound never allocates a large buffer


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _ancestors(path: str) -> list[str]:
    out = []
    while path != "/":
        path = os.path.dirname(path)
        out.append(path)
    return out


def _lstat(path: str, reason: str) -> os.stat_result:
    try:
        return os.lstat(path)
    except OSError:
        raise LabError(reason) from None


def _file_sha256(path: str) -> str | None:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    except OSError:
        return None


def _shared_ancestor(path: str) -> str | None:
    """The first ancestor others may write (rename the file away), else ``None``.

    Sticky root-owned ancestors (``/tmp``) are accepted: others cannot rename into them.
    """
    for ancestor in _ancestors(path):
        try:
            info = os.lstat(ancestor)
        except OSError:
            return ancestor
        if info.st_mode & _SHARED_WRITE and not (info.st_mode & stat.S_ISVTX and info.st_uid == 0):
            return ancestor
    return None


def _trusted_file(path: str, expected_sha256: str, missing: str, drift: str) -> None:
    """Regular, not a symlink, not writable by others along its path, hash as pinned."""
    info = _lstat(path, missing)
    _require(stat.S_ISREG(info.st_mode) and os.path.realpath(path) == path
             and not info.st_mode & _SHARED_WRITE and _shared_ancestor(path) is None, missing)
    _require(_file_sha256(path) == expected_sha256, drift)


# --- policy ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContainmentPolicy:
    """Trusted values from the founder decisions and the issuer's qualification pins.

    Fixed values (endpoints, limits, version, credential method) are module constants;
    only machine-specific paths, pinned hashes and probe-observed additions are fields.
    ``claude_version`` is the pinned value; the observed version is checked by T006.
    """

    account: str
    run_root: str  # candidate and per-run TMPDIR live below it
    config_dir: str  # the dedicated user's CLAUDE_CONFIG_DIR
    claude: str
    claude_sha256: str
    claude_version: str
    interpreter: str  # pinned fixture interpreter (owned probes and fixtures)
    interpreter_sha256: str
    interpreter_root: str  # read-only prefix the interpreter needs
    sandbox_exec_sha256: str
    proxy_port: int
    probe_catalog_sha256: str
    helpers: tuple[tuple[str, str], ...] = ()  # (path, sha256) observed by probe
    refresh_endpoints: tuple[str, ...] = ()  # OAuth refresh hosts observed by probe

    def __post_init__(self) -> None:
        _require(type(self.helpers) is tuple and type(self.refresh_endpoints) is tuple
                 and all(type(h) is tuple and len(h) == 2 for h in self.helpers), "invalid-policy")
        executables = [self.claude, self.interpreter, *(p for p, _ in self.helpers)]
        paths = [self.run_root, self.config_dir, self.interpreter_root, *executables]
        hashes = [self.claude_sha256, self.interpreter_sha256, self.sandbox_exec_sha256,
                  self.probe_catalog_sha256, *(h for _, h in self.helpers)]
        writable = (self.run_root, self.config_dir)
        read_roots = [self.interpreter_root, *SYSTEM_READ]
        _require(type(self.account) is str and _ACCOUNT.fullmatch(self.account) is not None, "invalid-policy")
        _require(all(type(p) is str and _PATH.fullmatch(p) is not None and os.path.normpath(p) == p
                     for p in paths), "invalid-policy")
        _require(all(type(h) is str and _HASH.fullmatch(h) is not None for h in hashes), "invalid-policy")
        _require(type(self.proxy_port) is int and 1024 <= self.proxy_port <= 65535, "invalid-policy")
        _require(all(type(e) is str and _ENDPOINT.fullmatch(e) is not None for e in self.refresh_endpoints)
                 and len(set(self.endpoints)) == len(self.endpoints), "invalid-policy")
        _require(len(set(executables)) == len(executables)
                 and COMPILE_PROBE not in executables and SANDBOX_EXEC not in executables, "invalid-policy")
        # write roots are disjoint from each other, from every read root and executable
        _require(not _under(self.run_root, self.config_dir) and not _under(self.config_dir, self.run_root)
                 and not any(_under(e, w) for e in executables for w in writable)
                 and not any(_under(r, w) or _under(w, r) for r in read_roots for w in writable),
                 "invalid-policy")
        _require(_under(self.interpreter, self.interpreter_root)
                 and self.interpreter_root.count("/") >= 3, "invalid-policy")
        _require(self.claude_version == CLAUDE_VERSION, "cli-version-unsupported")

    @property
    def endpoints(self) -> tuple[str, ...]:
        return ALLOWED_ENDPOINTS + self.refresh_endpoints

    def executables(self, entry: str) -> tuple[str, ...]:
        _require(entry in ENTRIES, "invalid-entry")
        if entry == "fixture":
            return (self.interpreter,)
        return (self.claude, *(p for p, _ in self.helpers))

    def render(self, entry: str) -> bytes:
        """Deterministic SBPL; per-run paths arrive only as ``CANDIDATE``/``TMPDIR`` params."""
        execs = self.executables(entry)
        reads = [*SYSTEM_READ, self.interpreter_root] if entry == "fixture" else list(SYSTEM_READ)
        writes = [] if entry == "fixture" else [self.config_dir]
        metadata = sorted({a for p in [*execs, *reads, *writes, self.run_root] for a in _ancestors(p)}
                          - {"/"})

        def literals(kind: str, items) -> str:
            return " ".join(f'({kind} "{item}")' for item in items)

        lines = [
            "(version 1)",
            "(deny default)",
            "(allow process-fork)",
            f"(allow process-exec {literals('literal', execs)})",
            "(allow signal (target same-sandbox))",
            "(allow process-info* (target self))",
            # dyld needs read-data on "/" itself; the root listing is a recorded residual
            f'(allow file-read* file-map-executable (literal "/") {literals("subpath", reads)} '
            f"{literals('literal', execs)})",
            '(allow file-read* (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
            '(allow file-write-data (literal "/dev/null"))',
            f"(allow file-read-metadata {literals('literal', metadata)} (subpath \"{self.run_root}\"))",
            '(allow file-read* file-write* (subpath (param "CANDIDATE")) (subpath (param "TMPDIR")))',
        ]
        if writes:
            lines.append(f"(allow file-read* file-write* {literals('subpath', writes)})")
        lines += [f"(deny file-read* file-write* {literals('subpath', DENIED)})",
                  f'(allow network-outbound (remote tcp "localhost:{self.proxy_port}"))']
        return ("\n".join(lines) + "\n").encode()

    def child_environment(self, entry: str, tmpdir: str) -> dict[str, str]:
        _require(entry in ENTRIES, "invalid-entry")
        proxy = f"http://127.0.0.1:{self.proxy_port}"
        env = {"HOME": f"{tmpdir}/home", "TMPDIR": tmpdir, "PATH": "/usr/bin:/bin",
               "LANG": "en_US.UTF-8", "HTTPS_PROXY": proxy, "HTTP_PROXY": proxy,
               "https_proxy": proxy, "http_proxy": proxy, "NO_PROXY": "", "no_proxy": ""}
        if entry == "fixture":
            env["PYTHONHASHSEED"] = "0"
        else:
            env.update(CLAUDE_CONFIG_DIR=self.config_dir, DISABLE_AUTOUPDATER="1",
                       CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC="1")
        return env


@dataclass(frozen=True)
class HostFacts:
    """Observed OS identity; part of the environment hash."""

    product: str
    build: str
    arch: str


def _component_hashes() -> dict[str, str]:
    """Trusted code the enforcement relies on: this backend, the lab and the host module."""
    return {Path(m.__file__).name: sha256(Path(m.__file__).read_bytes()).hexdigest()
            for m in (sys.modules[__name__], harness_lab, harness_host_claude)}


def environment_sha256(policy: ContainmentPolicy, facts: HostFacts, uid: int) -> str:
    """Canonical digest of every environment-hash input of contracts/native-profile.md."""
    supervisor = os.path.realpath(sys.executable)
    value = {
        "format": ENVIRONMENT_FORMAT,
        "os": asdict(facts),
        "mechanism": {"backend": BACKEND, "sandboxExec": SANDBOX_EXEC,
                      "sandboxExecSha256": policy.sandbox_exec_sha256,
                      "account": policy.account, "uid": uid},
        "profiles": {entry: sha256(policy.render(entry)).hexdigest() for entry in ENTRIES},
        "claude": {"path": policy.claude, "sha256": policy.claude_sha256,
                   "version": policy.claude_version},
        "helpers": [list(h) for h in policy.helpers],
        "interpreter": {"path": policy.interpreter, "sha256": policy.interpreter_sha256,
                        "root": policy.interpreter_root},
        "supervisor": {"path": supervisor, "sha256": _file_sha256(supervisor)},
        "credentialMethod": CREDENTIAL_METHOD,
        "configDir": policy.config_dir,
        "runRoot": policy.run_root,
        "network": {"endpoints": list(policy.endpoints), "proxyPort": policy.proxy_port},
        "components": _component_hashes(),
        "limits": LIMITS,
        "probeCatalogSha256": policy.probe_catalog_sha256,
    }
    return sha256(canonical(value)).hexdigest()


# --- Darwin facts through libSystem (no PATH lookup, no subprocess) ----------------------


def _darwin() -> bool:
    return sys.platform == "darwin"


_LIBSYSTEM = None


def _libsystem():
    global _LIBSYSTEM
    if _LIBSYSTEM is None:
        lib = ctypes.CDLL("/usr/lib/libSystem.B.dylib", use_errno=True)
        lib.sysctlbyname.argtypes = [ctypes.c_char_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
                                     ctypes.c_void_p, ctypes.c_size_t]
        lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p,
                                     ctypes.c_int]
        for name in ("sysctlbyname", "proc_listpids", "proc_pidinfo"):
            getattr(lib, name).restype = ctypes.c_int
        _LIBSYSTEM = lib
    return _LIBSYSTEM


def _sysctl_string(name: str) -> str:
    lib = _libsystem()
    size = ctypes.c_size_t(0)
    _require(lib.sysctlbyname(name.encode(), None, ctypes.byref(size), None, 0) == 0
             and 0 < size.value <= 256, "os-unsupported")
    buffer = ctypes.create_string_buffer(size.value)
    _require(lib.sysctlbyname(name.encode(), buffer, ctypes.byref(size), None, 0) == 0,
             "os-unsupported")
    return buffer.value.decode("ascii", "replace")


def host_facts() -> HostFacts:
    return HostFacts(_sysctl_string("kern.osproductversion"), _sysctl_string("kern.osversion"),
                     platform.machine())


_PROC_RUID_ONLY, _PROC_PIDTASKINFO, _PROC_PIDTBSDINFO = 5, 4, 3
_BSDINFO_WORDS = 17  # struct proc_bsdinfo is 136 bytes; start sec/usec are words 15 and 16
_TASKINFO_WORDS = 12  # struct proc_taskinfo is 96 bytes; resident size is word 1


def _pidinfo(pid: int, flavor: int, words: int) -> tuple[int, ...] | None:
    """One ``proc_pidinfo`` call; ``None`` only when the process is gone (fail closed)."""
    buffer = (ctypes.c_uint64 * words)()
    if _libsystem().proc_pidinfo(pid, flavor, 0, buffer, ctypes.sizeof(buffer)) == ctypes.sizeof(buffer):
        return tuple(buffer)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except OSError:
        pass
    raise LabError("process-accounting-failed")


def _user_processes(uid: int) -> set[tuple[int, int]]:
    """Every live process of ``uid`` as ``(pid, start time)``, so a reused pid differs."""
    lib = _libsystem()
    size = lib.proc_listpids(_PROC_RUID_ONLY, uid, None, 0)
    _require(size > 0, "process-accounting-failed")
    while True:
        buffer = (ctypes.c_int * (size // 4 + 256))()
        got = lib.proc_listpids(_PROC_RUID_ONLY, uid, buffer, ctypes.sizeof(buffer))
        _require(got > 0, "process-accounting-failed")
        if got < ctypes.sizeof(buffer):
            break
        size = got * 2  # the list may be truncated: retry larger
    out = set()
    for pid in buffer[:got // 4]:
        if pid > 0 and (info := _pidinfo(pid, _PROC_PIDTBSDINFO, _BSDINFO_WORDS)) is not None:
            out.add((pid, info[15] * 1_000_000 + info[16]))
    return out


def _resident_bytes(processes: set[tuple[int, int]]) -> int:
    total = 0
    for pid, _ in processes:
        info = _pidinfo(pid, _PROC_PIDTASKINFO, _TASKINFO_WORDS)
        total += 0 if info is None else info[1]
    return total


# --- loopback egress proxy (NC-1) -------------------------------------------------------

_ECH_EXTENSIONS = (0xFE0D, 0xFF0D)  # encrypted ClientHello would hide the real SNI


def client_hello_sni(record: bytes) -> str | None:
    """The single ``host_name`` of a TLS ClientHello in one record, else ``None``.

    A hello carrying encrypted ClientHello is refused: its outer SNI is not the target.
    """
    try:
        if len(record) < 5 or record[0] != 0x16 or int.from_bytes(record[3:5], "big") != len(record) - 5:
            return None
        body = record[5:]
        if body[0] != 0x01 or int.from_bytes(body[1:4], "big") != len(body) - 4:
            return None
        pos = 4 + 2 + 32
        pos += 1 + body[pos]  # session id
        pos += 2 + int.from_bytes(body[pos:pos + 2], "big")  # cipher suites
        pos += 1 + body[pos]  # compression methods
        end = pos + 2 + int.from_bytes(body[pos:pos + 2], "big")
        if end != len(body):
            return None
        pos += 2
        names = []
        while pos < end:
            kind, size = int.from_bytes(body[pos:pos + 2], "big"), int.from_bytes(body[pos + 2:pos + 4], "big")
            data = body[pos + 4:pos + 4 + size]
            if len(data) != size or kind in _ECH_EXTENSIONS:
                return None
            if kind == 0:
                if int.from_bytes(data[:2], "big") != len(data) - 2:
                    return None
                at = 2
                while at < len(data):
                    name_type, length = data[at], int.from_bytes(data[at + 1:at + 3], "big")
                    name = data[at + 3:at + 3 + length]
                    if name_type != 0 or len(name) != length:
                        return None
                    names.append(name.decode("ascii").lower())
                    at += 3 + length
            pos += 4 + size
        return names[0] if len(names) == 1 else None
    except (IndexError, UnicodeDecodeError):
        return None


class EgressProxy:
    """Loopback CONNECT proxy: listed ``host:443`` only, and only when SNI equals the host.

    It is the only egress the profile allows and holds the port on both ``127.0.0.1``
    and ``::1`` (the profile's ``localhost`` covers both). It resolves names itself, so
    the child needs no DNS; plain HTTP, other methods and other hosts are refused. The
    request head and ClientHello must arrive within one handshake deadline and a tunnel
    lives at most one session wall bound.
    """

    MAX_HEAD = 8192
    MAX_RECORD = 16_384 + 5
    MAX_CONNECTIONS = 16

    def __init__(self, port: int, endpoints: tuple[str, ...], *,
                 connect: Callable[..., socket.socket] = socket.create_connection,
                 timeout: float = 30.0, tunnel_seconds: float = LIMITS["wallSeconds"]):
        self.port = port
        self.endpoints = frozenset(endpoints)
        self._connect = connect
        self._timeout = timeout
        self._tunnel_seconds = tunnel_seconds
        self._slots = threading.BoundedSemaphore(self.MAX_CONNECTIONS)
        self._servers: list[socket.socket] = []

    @property
    def running(self) -> bool:
        return bool(self._servers)

    def start(self) -> None:
        try:
            for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
                server = socket.socket(family, socket.SOCK_STREAM)
                self._servers.append(server)
                if family == socket.AF_INET6:
                    server.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                server.bind((host, self.port))
                server.listen(16)
                self.port = server.getsockname()[1]
        except OSError:
            self.close()
            raise LabError("proxy-unavailable") from None
        for server in self._servers:
            threading.Thread(target=self._accept, args=(server,), daemon=True).start()

    def close(self) -> None:
        servers, self._servers = self._servers, []
        for server in servers:
            try:
                server.shutdown(socket.SHUT_RDWR)  # Linux: close alone leaves accept() listening
            except OSError:
                pass
            server.close()

    def _accept(self, server: socket.socket) -> None:
        while True:
            try:
                client, _ = server.accept()
            except OSError:
                return
            if not self._slots.acquire(blocking=False):
                client.close()
                continue
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        try:
            with client:
                self._tunnel(client, time.monotonic() + self._timeout)
        except (OSError, ValueError):
            pass
        finally:
            self._slots.release()

    @staticmethod
    def _recv(client: socket.socket, deadline: float, size: int) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        client.settimeout(remaining)
        return client.recv(size)

    def _tunnel(self, client: socket.socket, deadline: float) -> None:
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = self._recv(client, deadline, 4096)
            if not chunk or len(buffer) + len(chunk) > self.MAX_HEAD:
                return
            buffer += chunk
        head, _, buffer = buffer.partition(b"\r\n\r\n")
        parts = head.split(b"\r\n", 1)[0].split(b" ")
        method, target, version = parts if len(parts) == 3 else (b"", b"", b"")
        host_port = target.decode("ascii", "replace").lower()
        if method != b"CONNECT" or not version.startswith(b"HTTP/1.") or host_port not in self.endpoints:
            client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            return
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        while len(buffer) < 5 or len(buffer) < 5 + int.from_bytes(buffer[3:5], "big"):
            if len(buffer) >= 5 and 5 + int.from_bytes(buffer[3:5], "big") > self.MAX_RECORD:
                return
            chunk = self._recv(client, deadline, 65_536)
            if not chunk:
                return
            buffer += chunk
        length = 5 + int.from_bytes(buffer[3:5], "big")
        hello, rest = buffer[:length], buffer[length:]
        host, port = host_port.rsplit(":", 1)
        if client_hello_sni(hello) != host:
            return
        with self._connect((host, int(port)), timeout=self._timeout) as upstream:
            upstream.sendall(hello + rest)
            _relay(client, upstream, self._timeout, time.monotonic() + self._tunnel_seconds)


def _relay(a: socket.socket, b: socket.socket, idle: float, deadline: float) -> None:
    with selectors.DefaultSelector() as selector:
        selector.register(a, selectors.EVENT_READ, b)
        selector.register(b, selectors.EVENT_READ, a)
        while (remaining := deadline - time.monotonic()) > 0:
            ready = selector.select(min(idle, remaining))
            if not ready:
                return
            for key, _ in ready:
                data = key.fileobj.recv(65_536)  # type: ignore[union-attr]
                if not data:
                    return
                key.data.sendall(data)


# --- backend ----------------------------------------------------------------------------

# Runs as the dedicated user before the sandbox is entered: marks the status pipe
# close-on-exec, applies the rlimits without ``preexec_fn``, enters the candidate and execs
# ``sandbox-exec``. Any failure writes one byte to the pipe, so it never shares the
# child's exit-code namespace.
_PREAMBLE = (
    "import os, resource, sys\n"
    "status = int(sys.argv[6])\n"
    "try:\n"
    "    os.set_inheritable(status, False)\n"
    "    cpu, fsize, nofile, nproc = (int(v) for v in sys.argv[1:5])\n"
    "    for limit, value in ((resource.RLIMIT_CPU, cpu), (resource.RLIMIT_FSIZE, fsize),\n"
    "                         (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, nofile),\n"
    "                         (resource.RLIMIT_NPROC, nproc)):\n"
    "        resource.setrlimit(limit, (value, value))\n"
    "    os.chdir(sys.argv[5])\n"
    "    os.execv(sys.argv[7], sys.argv[7:])\n"
    "except BaseException:\n"
    "    os.write(status, b'x')\n"
    "    os._exit(1)\n")


ProbeRunner = Callable[[str, "MacOSContainment"], str]


class _OutputStream:
    """Incremental reader of the child's stdout file for the live ``on_output`` hook.

    Each byte is handed to the callback once, in order, and never past ``limit``. The first
    callback exception is recorded in ``state`` and ends all further delivery, so the
    supervisor can kill and settle before refusing.
    """

    def __init__(self, path: str, limit: int, callback: Callable[[bytes], None],
                 cancel: threading.Event | None):
        self._path, self._limit, self._callback, self._cancel = path, limit, callback, cancel
        self._reader = None
        self._delivered = 0

    def pump(self, state: dict) -> None:
        """Deliver what was written since the last call in bounded chunks; none after a cancel."""
        while not (state.get("callbackFailed") or (self._cancel is not None and self._cancel.is_set())):
            try:
                if self._reader is None:
                    self._reader = open(self._path, "rb")
                chunk = self._reader.read(min(self._limit - self._delivered, _STREAM_CHUNK_BYTES))
            except OSError:
                state["callbackFailed"] = True
                return
            if not chunk:
                return
            self._delivered += len(chunk)
            try:
                self._callback(chunk)
            except Exception:
                state["callbackFailed"] = True

    def close(self) -> None:
        if self._reader is not None:
            self._reader.close()


class MacOSContainment(ContainmentBackend):
    """Native backend; refuses with a fixed reason whenever any check fails.

    The probe runner is trusted T007 code; binding it to ``probe_catalog_sha256`` is
    the runner's job. ``run_probe`` lets it run probes contained without recursing
    into the NC-11 subset.
    """

    kind = "native"

    def __init__(self, policy: ContainmentPolicy, *, qualification: bytes, qualification_sha256: str,
                 host_qualification: bytes, host_qualification_sha256: str,
                 probe_runner: ProbeRunner | None, clock: Callable[[], float] = time.time):
        _require(isinstance(policy, ContainmentPolicy), "invalid-policy")
        self.policy = policy
        self.qualification: Qualification = verify_qualification(
            qualification, expected_sha256=qualification_sha256)
        try:
            self.host_qualification = verify_host_qualification(
                host_qualification, expected_sha256=host_qualification_sha256)
        except ClaudeHostError as exc:
            raise LabError(exc.reason) from None
        _require(self.qualification.backend == BACKEND, "qualification-backend-mismatch")
        _require(self.host_qualification.environment_sha256 == self.qualification.environment_sha256,
                 "qualification-environment-mismatch")
        self._probe_runner = probe_runner
        self._clock = clock
        self._proxy = EgressProxy(policy.proxy_port, policy.endpoints)
        self._lock = threading.RLock()  # probes nest inside run
        self._depth = 0
        self.run_evidence: list[dict] = []

    def close(self) -> None:
        self._proxy.close()

    def _refuse(self, entry: str, reason: str) -> NoReturn:
        self.run_evidence.append({"entry": entry, "backend": BACKEND, "refused": reason})
        raise LabError(reason)

    @contextmanager
    def _exclusive(self, entry: str) -> Iterator[None]:
        """One contained run per account: a process lock plus ``flock`` on ``run_root``."""
        with self._lock:
            if self._depth:  # a probe inside the pre-session check of this backend
                self._depth += 1
                try:
                    yield
                finally:
                    self._depth -= 1
                return
            try:
                fd = os.open(f"{self.policy.run_root}/.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            except OSError:
                self._refuse(entry, "workspace-unsafe")
            try:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    self._refuse(entry, "dedicated-user-busy")
                self._depth = 1
                try:
                    yield
                finally:
                    self._depth = 0
            finally:
                os.close(fd)  # closing releases the flock

    # -- checks ---------------------------------------------------------------------------

    def _check_mechanism(self, entry: str, evidence: dict) -> int:
        """Platform, account, mechanism, executables, workspace and environment; the uid."""
        policy = self.policy
        _require(_darwin(), "mechanism-unavailable")
        _require(not any(name in os.environ for name in ENV_DENY), "env-deny-present")
        facts = host_facts()
        evidence["os"] = asdict(facts)
        _require(_OS_SERIES.fullmatch(facts.product) is not None
                 and _BUILD.fullmatch(facts.build) is not None, "os-unsupported")
        try:
            uid = pwd.getpwnam(policy.account).pw_uid
        except KeyError:
            raise LabError("dedicated-user-required") from None
        _require(uid != 0 and os.getuid() == uid and os.geteuid() == uid, "dedicated-user-required")
        info = _lstat(SANDBOX_EXEC, "mechanism-unavailable")
        _require(stat.S_ISREG(info.st_mode) and info.st_uid == _MECHANISM_UID
                 and not info.st_mode & _SHARED_WRITE, "mechanism-unavailable")
        _require(_file_sha256(SANDBOX_EXEC) == policy.sandbox_exec_sha256, "mechanism-drift")
        pinned = {policy.claude: policy.claude_sha256, policy.interpreter: policy.interpreter_sha256,
                  **dict(policy.helpers)}
        for path in policy.executables(entry):
            _trusted_file(path, pinned[path], "executable-unavailable", "executable-drift")
        for directory in (policy.run_root, policy.config_dir):
            info = _lstat(directory, "workspace-unsafe")
            _require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid
                     and os.path.realpath(directory) == directory and not info.st_mode & 0o077,
                     "workspace-unsafe")
        environment = environment_sha256(policy, facts, uid)
        evidence["environmentSha256"] = environment
        _require(environment == self.qualification.environment_sha256, "environment-drift")
        _require(self._clock() < min(self.qualification.expires_at, self.host_qualification.expires_at),
                 "qualification-expired")
        return uid

    def _candidate(self, path: Path | str, uid: int) -> str:
        """A private directory directly below ``run_root`` that the backend does not own."""
        resolved = os.path.realpath(path)
        _require(os.path.dirname(resolved) == self.policy.run_root
                 and not os.path.basename(resolved).startswith(_RESERVED)
                 and _PATH.fullmatch(resolved) is not None, "workdir-outside-run-root")
        info = _lstat(resolved, "workdir-outside-run-root")
        _require(stat.S_ISDIR(info.st_mode) and info.st_uid == uid and not info.st_mode & 0o077,
                 "workspace-unsafe")
        return resolved

    def _compile_check(self, entry: str) -> None:
        """The exact profile must compile and must deny exec of a non-listed binary."""
        probe_dir = None
        try:
            probe_dir = tempfile.mkdtemp(prefix="compile-", dir=self.policy.run_root)
            code = subprocess.run(
                [SANDBOX_EXEC, "-p", self.policy.render(entry).decode(), "-D", f"CANDIDATE={probe_dir}",
                 "-D", f"TMPDIR={probe_dir}", "--", COMPILE_PROBE],
                env={}, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=10, check=False).returncode
        except (OSError, subprocess.TimeoutExpired):
            raise LabError("profile-compile-failed") from None
        finally:
            if probe_dir is not None:
                shutil.rmtree(probe_dir, ignore_errors=True)
        _require(code != EXIT_SANDBOX_COMPILE, "profile-compile-failed")
        _require(code == EXIT_SANDBOX_EXEC_DENIED, "self-check-allowed")

    def _run_probes(self, evidence: dict) -> None:
        _require(self._probe_runner is not None, "self-check-unavailable")
        checks = evidence["preSessionCheck"] = []
        for probe, expected in F4_PROBES:
            try:
                observed = self._probe_runner(probe, self)
            except Exception:
                observed = "error"
            if observed not in ("allowed", "denied"):
                observed = "error"
            checks.append({"probe": probe, "expected": expected, "observed": observed})
            _require(observed == expected,
                     "self-check-allowed" if observed == "allowed" else "self-check-failed")

    def _pre_session(self, entry: str, workdir: Path | str, *, probes: bool) -> tuple[dict, str, int]:
        """NC-11 checks in order; every refusal, expected or not, lands in ``run_evidence``."""
        evidence: dict = {"entry": entry, "backend": BACKEND,
                          "qualificationSha256": self.qualification.sha256,
                          "hostQualificationSha256": self.host_qualification.sha256,
                          "limits": LIMITS}
        try:
            uid = self._check_mechanism(entry, evidence)
            candidate = self._candidate(workdir, uid)
            if not self._proxy.running:
                self._proxy.start()
            self._compile_check(entry)
            evidence["compileCheck"] = "exec-denied"
            if probes:
                self._run_probes(evidence)
            else:
                evidence["probeRun"] = True
        except LabError as exc:
            self.run_evidence.append(evidence | {"refused": exc.reason})
            raise
        except Exception:
            self.run_evidence.append(evidence | {"refused": "backend-failed"})
            raise LabError("backend-failed") from None
        return evidence, candidate, uid

    # -- entry points ---------------------------------------------------------------------

    def run(self, source: bytes, workdir: Path, limits: FixtureLimits) -> ChildResult:
        """Owned fixture entry point, after the full NC-11 pre-session check."""
        return self._fixture(source, workdir, limits, probes=True)

    def run_probe(self, source: bytes, workdir: Path, limits: FixtureLimits) -> ChildResult:
        """Probe entry point for the T007 runner: same profile and checks, no probe subset."""
        return self._fixture(source, workdir, limits, probes=False)

    def _fixture(self, source: bytes, workdir: Path, limits: FixtureLimits, *, probes: bool) -> ChildResult:
        if type(source) is not bytes or not isinstance(limits, FixtureLimits):
            self._refuse("fixture", "invalid-lab-request")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError:
            self._refuse("fixture", "invalid-fixture")
        with self._exclusive("fixture"):
            evidence, candidate, uid = self._pre_session("fixture", workdir, probes=probes)
            run = self._spawn("fixture", [self.policy.interpreter, "-I", "-S", "-c", text], evidence,
                              candidate=candidate, uid=uid, wall=limits.wall_seconds,
                              cpu=min(limits.wall_seconds + 1, LIMITS["cpuSeconds"]),
                              max_output=limits.max_output_bytes, cancel=None, stdin=b"")
        return ChildResult(run.stdout, run.exit_code, run.timed_out, run.output_truncated, run.settled)

    def launch(self, argv: tuple[str, ...], stdin: bytes, *, cwd: Path | str, wall_seconds: int,
               max_output_bytes: int, cancel: threading.Event,
               on_output: Callable[[bytes], None] | None = None) -> HostRun:
        """Contained launcher for the native transport (T006): pinned Claude executable only.

        The argument list beyond ``argv[0]`` is the transport's (T006) responsibility.
        ``on_output`` receives each newly written stdout chunk, in order and once per byte,
        never past ``max_output_bytes``, while the child runs; it may set ``cancel`` to stop
        the group. A callback that raises kills and settles the group, then refuses with
        ``output-callback-failed``.
        """
        if not (type(argv) is tuple and len(argv) >= 1 and argv[0] == self.policy.claude
                and all(type(a) is str and "\0" not in a for a in argv)
                and type(stdin) is bytes and len(stdin) <= MAX_LAUNCH_STDIN_BYTES
                and isinstance(cancel, threading.Event)
                and (on_output is None or callable(on_output))
                and type(wall_seconds) is int and 1 <= wall_seconds <= LIMITS["wallSeconds"]
                and type(max_output_bytes) is int and 1 <= max_output_bytes <= MAX_LAUNCH_OUTPUT_BYTES):
            self._refuse("launch", "invalid-launch")
        with self._exclusive("launch"):
            evidence, candidate, uid = self._pre_session("launch", cwd, probes=True)
            return self._spawn("launch", list(argv), evidence, candidate=candidate, uid=uid,
                               wall=wall_seconds, cpu=LIMITS["cpuSeconds"], max_output=max_output_bytes,
                               cancel=cancel, stdin=stdin, on_output=on_output)

    # -- supervision ----------------------------------------------------------------------

    def _spawn(self, entry: str, target: list[str], evidence: dict, *, candidate: str, uid: int,
               wall: int, cpu: int, max_output: int, cancel: threading.Event | None,
               stdin: bytes, on_output: Callable[[bytes], None] | None = None) -> HostRun:
        """Supervise one contained child; whatever happens it is killed, settled and recorded."""
        record = dict(evidence)
        try:
            return self._supervise(entry, target, record, candidate=candidate, uid=uid, wall=wall,
                                   cpu=cpu, max_output=max_output, cancel=cancel, stdin=stdin,
                                   on_output=on_output)
        except LabError as exc:
            record["refused"] = exc.reason
            raise
        except Exception:
            record["refused"] = "supervisor-failed"
            raise LabError("supervisor-failed") from None
        finally:
            self.run_evidence.append(record)

    def _supervise(self, entry: str, target: list[str], record: dict, *, candidate: str, uid: int,
                   wall: int, cpu: int, max_output: int, cancel: threading.Event | None,
                   stdin: bytes, on_output: Callable[[bytes], None] | None = None) -> HostRun:
        policy = self.policy
        try:
            run_dir = tempfile.mkdtemp(prefix="run-", dir=policy.run_root)
        except OSError:
            raise LabError("workspace-unavailable") from None
        child = status = None
        baseline: set[tuple[int, int]] = set()
        state: dict = {"timedOut": False, "cancelled": False, "outputTruncated": False,
                       "limitExceeded": None}
        out_path = f"{run_dir}/stdout"
        live = _OutputStream(out_path, max_output, on_output, cancel) if on_output is not None else None
        try:
            try:
                tmpdir = f"{run_dir}/tmp"
                os.mkdir(tmpdir, 0o700)
                os.mkdir(f"{tmpdir}/home", 0o700)
                with open(f"{run_dir}/stdin", "wb") as stream:
                    stream.write(stdin)
                source = open(f"{run_dir}/stdin", "rb")
                sink = open(out_path, "wb")
            except OSError:
                raise LabError("workspace-unavailable") from None
            with source, sink:
                baseline = _user_processes(uid)
                nproc = len(baseline) + 1 + LIMITS["descendants"]
                status, status_w = os.pipe()
                argv = [sys.executable, "-I", "-S", "-c", _PREAMBLE, str(cpu), str(LIMITS["fileSizeBytes"]),
                        str(LIMITS["openFiles"]), str(nproc), candidate, str(status_w), SANDBOX_EXEC,
                        "-p", policy.render(entry).decode(), "-D", f"CANDIDATE={candidate}",
                        "-D", f"TMPDIR={tmpdir}", "--", *target]
                try:
                    child = subprocess.Popen(argv, cwd=run_dir, env=policy.child_environment(entry, tmpdir),
                                             stdin=source, stdout=sink, stderr=subprocess.DEVNULL,
                                             close_fds=True, pass_fds=(status_w,), start_new_session=True)
                except (OSError, ValueError):
                    raise LabError("launch-failed") from None
                finally:
                    os.close(status_w)
                self._watch(child, state, uid=uid, baseline=baseline, out_path=out_path,
                            deadline=time.monotonic() + wall, max_output=max_output, cancel=cancel,
                            live=live)
        finally:
            sweep_error = None
            if child is not None:
                if child.poll() is None:
                    child.kill()
                    child.wait()  # reap the leader so only live group members remain
                state["settled"] = _settle(child.pid)
                state["baselineProcesses"] = len(baseline)
                try:
                    state["escapedProcesses"] = self._sweep(uid, baseline)
                except LabError as exc:  # cleanup still runs; the run stays unsettled
                    sweep_error = exc
            if live is not None:
                if not (state["timedOut"] or state["cancelled"] or state["outputTruncated"]
                        or state["limitExceeded"]):
                    live.pump(state)  # natural exit: deliver the tail written since the last poll
                live.close()
            preamble_failed = False
            if status is not None:
                os.set_blocking(status, False)
                try:
                    preamble_failed = os.read(status, 1) == b"x"
                except BlockingIOError:
                    pass
                os.close(status)
            try:
                with open(out_path, "rb") as stream:
                    data = stream.read(max_output + 1)
            except OSError:
                data = b""
            shutil.rmtree(run_dir, ignore_errors=True)
            stopped = (state["timedOut"] or state["cancelled"] or state["outputTruncated"]
                       or state["limitExceeded"])
            exit_code = None if child is None or stopped else child.returncode
            settled = bool(state.get("settled")) and state.get("escapedProcesses") == 0
            record.update(state, exitCode=exit_code, settled=settled)
        if sweep_error is not None:
            raise sweep_error
        _require(not state.get("callbackFailed"), "output-callback-failed")
        _require(not preamble_failed, "rlimit-unenforceable")
        truncated = state["outputTruncated"] or len(data) > max_output
        record["outputTruncated"] = truncated
        return HostRun(data[:max_output], exit_code, state["timedOut"], state["cancelled"], truncated, settled)

    def _watch(self, child: subprocess.Popen, state: dict, *, uid: int, baseline: set[tuple[int, int]],
               out_path: str, deadline: float, max_output: int, cancel: threading.Event | None,
               live: "_OutputStream | None" = None) -> None:
        """Poll until exit or the first wall, cancel, output or memory stop; records which."""
        while child.poll() is None:
            if live is not None:
                live.pump(state)
            if state.get("callbackFailed"):
                return
            if time.monotonic() >= deadline:
                state["timedOut"] = True
            elif cancel is not None and cancel.is_set():
                state["cancelled"] = True
            elif os.path.getsize(out_path) > max_output:
                state["outputTruncated"] = True
            elif _resident_bytes(_user_processes(uid) - baseline) > LIMITS["memoryBytes"]:
                state["limitExceeded"] = "memory"
            else:
                time.sleep(_POLL_SECONDS)
                continue
            return

    def _sweep(self, uid: int, baseline: set[tuple[int, int]]) -> int:
        """Kill every new process of the dedicated user left after the group settled.

        Each one escaped the group, so any count above zero leaves the run unsettled even
        when the kill succeeds. Only ever runs as the dedicated account.
        """
        try:
            account_uid = pwd.getpwnam(self.policy.account).pw_uid
        except KeyError:
            raise LabError("dedicated-user-required") from None
        _require(uid == os.getuid() == account_uid, "dedicated-user-required")
        escaped: set[tuple[int, int]] = set()
        for _ in range(40):
            survivors = _user_processes(uid) - baseline
            if not survivors:
                return len(escaped)
            escaped |= survivors
            for pid, _ in survivors:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            time.sleep(_POLL_SECONDS)
        return len(escaped)
