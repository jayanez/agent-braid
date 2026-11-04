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
  loopback ports, Unix sockets, every ``mach-lookup`` and ``sysctl`` stay denied, except the closed
  read-only list (``SYSCTL_READ_NAMES``, ``SYSCTL_READ_PREFIXES``, three ``LC_CTYPE`` literals,
  metadata of ``/etc`` and ``/var``) that the ``launch`` and ``launch-probe`` profiles carry.
* credential: UID separation (the supervisor must run as the dedicated account, NC-2,
  NC-5), an environment built from scratch, and a refusal when an ``ENV_DENY`` variable
  is present in the parent. Keychain services are not reachable (no ``mach-lookup``). The ``launch``
  entry authenticates with the long-lived token of ``claude setup-token``, read by the supervisor from
  ``TOKEN_FILE`` in the dedicated user's ``config_dir`` (``read_token``: strict checks) and set as
  ``TOKEN_VARIABLE`` in the child environment only (NC-5 as amended 2026-11-04); the fixture entries never
  get it. Every run also carries ``RUN_TAG_VARIABLE``, a per-run random value that descendants inherit.
* process: exec allow-list (NC-8), CPU, file-size, core, open-file and per-user process
  rlimits applied before the sandbox is entered, a supervisor watchdog for wall time,
  memory (macOS refuses ``RLIMIT_AS`` below the current address space), output and disk
  (candidate, per-run ``TMPDIR`` and ``config_dir`` together: total bytes and entry count,
  ``disk-limit-exceeded``),
  and settlement of the group plus every new process of the dedicated user that belongs to the child's
  tree (parent chain, process group or the inherited run tag); other new processes are only counted as
  noise. The memory watchdog measures the larger of the resident size and the physical footprint. A process that
  left the group is reported apart from one still alive after the final sweep.
* run accounting: ``ProbeResult`` and ``ContainedHostRun`` extend the lab and host results
  with the process counts, the cleanup outcome, the peak disk use and the proxy counters of
  the run; the same values land in ``run_evidence``.

Before every run the backend takes an exclusive lock on ``run_root`` and re-verifies both
trusted qualification records, the OS window, the account (not privileged, not a system
account, not the operator's own account, a private home), the mechanism and executable
hashes, the recomputed environment hash, a profile compile check that must report the exec
of ``/usr/bin/false`` as denied and an allow-listed command as run, no leftover backend directory
from an earlier run, a proxy whose accept loop is alive, and the NC-11 probe subset through the injected T007 probe
runner. Any failure refuses with a fixed ``LabError`` reason before the child
starts and is appended to ``run_evidence``. It never degrades and never falls back to
``SimulatedContainment``. The observed Claude version is checked by the T006 transport;
here the version is a pinned policy value. Whether the profile enforces each effect is
decided by the T007/T009 probes and the human records, never here. ``run_fixture``
creates its workdir with ``tempfile``, so the supervisor's ``TMPDIR`` must be ``run_root``.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
import ctypes
from dataclasses import asdict, dataclass, field, fields
import errno
import fcntl
import hashlib
from hashlib import sha256
import os
from pathlib import Path
import platform
import pwd
import re
import secrets
import selectors
import shutil
import signal
import socket
import stat
import struct
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
CREDENTIAL_METHOD = "dedicated-user-token-file"  # NC-5, amended 2026-11-04 (founder: "A. Token en archivo")
# The long-lived token of ``claude setup-token`` lives in one file inside the dedicated user's
# ``CLAUDE_CONFIG_DIR`` and reaches the contained CLI only as this variable (Claude Code documents it as
# taking precedence over keychain-stored credentials). No Keychain access is opened.
TOKEN_FILE = "oauth-token"
TOKEN_VARIABLE = "CLAUDE_CODE_OAUTH_TOKEN"
TOKEN_MAX_BYTES = 4096
RUN_TAG_VARIABLE = "BRAID_RUN_TAG"  # inherited by every descendant; lets the sweep find a setsid leaver
CLAUDE_VERSION = "2.1.292"  # NC-4
ALLOWED_ENDPOINTS = ("api.anthropic.com:443",)  # NC-1; refresh hosts come from probe evidence
# NC-8; memory and disk are enforced by the supervisor watchdog, the rest by rlimits.
# diskBytes/diskFiles: founder decision 2026-11-02 ("2 GB y 100.000 ficheros"), measured over
# the candidate directory, the per-run TMPDIR and the dedicated user's config_dir together (founder
# decision 2026-11-02c, DRV-06: every entry counts, hard links once).
LIMITS = {"wallSeconds": 1800, "cpuSeconds": 1800, "memoryBytes": 4 << 30,
          "fileSizeBytes": 64 << 20, "openFiles": 256, "descendants": 16,
          "diskBytes": 2 << 30, "diskFiles": 100_000}
F4_PROBES = (("FS-01", "denied"), ("NET-01", "denied"), ("CRED-01", "denied"),
             ("PROC-01", "denied"), ("NET-06", "allowed"))  # NC-11
SYSTEM_READ = ("/usr/lib", "/System/Library", "/System/Cryptexes", "/System/Volumes/Preboot/Cryptexes",
               "/private/var/db/dyld", "/Library/Apple")
DENIED = ("/System/Volumes/Data",)
# Closed list of read-only system information the Claude (Bun) binary needs to start on macOS 27.2,
# from the kernel sandbox denials of the T009 self-check (founder decision 2026-11-04, "A. Lista
# cerrada"). Only the ``launch`` and ``launch-probe`` profiles carry it; ``fixture`` runs without it.
# Not here, on purpose: kern.bootargs, every mach-lookup, /dev/dtracehelper, /System/Volumes/Data.
SYSCTL_READ_NAMES = ("hw.pagesize", "hw.pagesize_compat", "hw.ephemeral_storage", "kern.osproductversion",
                     "kern.osvariant_status", "kern.iossupportversion", "security.mac.lockdown_mode_state")
SYSCTL_READ_PREFIXES = ("hw.optional.",)  # the CPU feature flags, one per feature
LOCALE_READ = tuple(f"/usr/share/locale/{name}/LC_CTYPE" for name in ("UTF-8", "C.UTF-8", "en_US.UTF-8"))
METADATA_ONLY = ("/etc", "/var")  # stat of the two literal paths, not of anything below them
COMPILE_PROBE = "/usr/bin/false"  # never allow-listed: its exec must be denied
LAUNCH_PROBE = "launch-probe"  # the launch profile plus the interpreter, for the T007 helper probes
ENTRIES = ("fixture", "launch", LAUNCH_PROBE)
MAX_LAUNCH_STDIN_BYTES = 1 << 20
MAX_LAUNCH_OUTPUT_BYTES = 16 << 20
EXIT_SANDBOX_COMPILE = 65
EXIT_SANDBOX_EXEC_DENIED = 71
_MECHANISM_UID = 0  # sandbox-exec must be root-owned
_SHARED_WRITE = stat.S_IWGRP | stat.S_IWOTH
# NC-3, amended 2026-11-03: the whole 27.x series; ASCII digits, canonical (no leading zeros)
_OS_SERIES = re.compile(r"27\.(?:0|[1-9][0-9]{0,2})(?:\.(?:0|[1-9][0-9]{0,2}))?\Z")
_BUILD = re.compile(r"[0-9]{2}[A-Z][0-9]{1,5}[a-z]?\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ACCOUNT = re.compile(r"[a-z_][a-z0-9_-]{0,31}\Z")
_TOKEN = re.compile(r"[A-Za-z0-9._~+/=-]{20,2048}\Z")
_PATH = re.compile(r"(?:/[A-Za-z0-9._@+-]+)+\Z")  # no quotes, spaces or escapes in SBPL
_ENDPOINT = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+:443\Z")
_OWNED = ("run-", "compile-")  # run_root directories the backend creates and removes
_RESERVED = (*_OWNED, ".")  # run_root entries the backend owns
_PRIVILEGED_GIDS = frozenset({0, 80})  # wheel, admin
_MIN_HUMAN_UID = 500  # below it: system accounts (RV-16, amended 2026-11-03)
_POLL_SECONDS = 0.05
_COMPILE_TIMEOUT_SECONDS = 20
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
    """The first ancestor others may swap the file under, else ``None``.

    That is an ancestor others may write (rename the file away) or one owned by a third
    account; only root and the effective (dedicated) user are trusted owners. Sticky
    root-owned ancestors (``/tmp``) are accepted: others cannot rename into them.
    """
    trusted = {0, os.geteuid()}
    for ancestor in _ancestors(path):
        try:
            info = os.lstat(ancestor)
        except OSError:
            return ancestor
        if info.st_uid not in trusted:
            return ancestor
        if info.st_mode & _SHARED_WRITE and not (info.st_mode & stat.S_ISVTX and info.st_uid == 0):
            return ancestor
    return None


def _remove_tree(path: str) -> bool:
    """Remove a directory the child could write, undoing the flags and modes it set.

    A child may set ``uchg`` or take away directory permissions so plain removal fails;
    this clears them as the owner and retries. ``True`` only when the path is gone.
    """
    def repair(target: str) -> bool:
        try:
            info = os.lstat(target)
            if hasattr(os, "lchflags"):
                os.lchflags(target, 0)
            if stat.S_ISDIR(info.st_mode):
                os.chmod(target, 0o700, follow_symlinks=os.chmod not in os.supports_follow_symlinks)
        except OSError:
            return False
        return True

    for _ in range(16):
        failed: list[str] = []
        shutil.rmtree(path, onexc=lambda _function, target, _error: failed.append(target))
        if not os.path.lexists(path):
            return True
        # the entry that failed and the directory holding it (unlink needs write there)
        targets = {t for f in failed for t in ((f, os.path.dirname(f)) if f != path else (f,))}
        if not any([repair(t) for t in targets]):
            break
    return not os.path.lexists(path)


def _trusted_file(path: str, expected_sha256: str, missing: str, drift: str) -> None:
    """Regular, not a symlink, owned by root or the dedicated user, not swappable along its path, hash as pinned."""
    info = _lstat(path, missing)
    _require(stat.S_ISREG(info.st_mode) and os.path.realpath(path) == path
             and info.st_uid in (0, os.geteuid())
             and not info.st_mode & _SHARED_WRITE and _shared_ancestor(path) is None, missing)
    _require(_file_sha256(path) == expected_sha256, drift)


# --- policy ---------------------------------------------------------------------------


def read_token(config_dir: str, uid: int) -> str | None:
    """The contained CLI's long-lived token, or ``None`` when ``TOKEN_FILE`` does not exist.

    Strict: a regular file (a symbolic link is never followed), owned by ``uid``, mode exactly ``0600``,
    a single link, 1 to ``TOKEN_MAX_BYTES`` bytes, holding one ASCII token. Anything else refuses with
    ``auth-token-invalid``. The value goes to the supervisor's child environment only: it is never logged,
    put in evidence or in an exception.
    """
    try:
        descriptor = os.open(f"{config_dir}/{TOKEN_FILE}",
                             os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    except OSError:
        raise LabError("auth-token-invalid") from None
    try:
        info = os.fstat(descriptor)
        if not (stat.S_ISREG(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o600
                and info.st_nlink == 1 and 0 < info.st_size <= TOKEN_MAX_BYTES):
            raise LabError("auth-token-invalid")
        data = os.read(descriptor, TOKEN_MAX_BYTES + 1)
    except OSError:
        raise LabError("auth-token-invalid") from None
    finally:
        os.close(descriptor)
    try:
        token = data.decode("ascii").removesuffix("\n")
    except UnicodeDecodeError:
        raise LabError("auth-token-invalid") from None
    if _TOKEN.fullmatch(token) is None:
        raise LabError("auth-token-invalid")
    return token


def _probe_catalog_sha256() -> str:
    """The catalog hash of the T007 runner, read from its module so the policy cannot drift from it.

    Imported lazily: the probes module imports this one.
    """
    from .harness_qualification_probes import CATALOG_SHA256
    return CATALOG_SHA256


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
    probe_catalog_sha256: str | None = None  # derived from the probes module; an explicit value must match
    helpers: tuple[tuple[str, str], ...] = ()  # (path, sha256) observed by probe
    refresh_endpoints: tuple[str, ...] = ()  # OAuth refresh hosts observed by probe

    def __post_init__(self) -> None:
        catalog = _probe_catalog_sha256()
        if self.probe_catalog_sha256 is None:
            object.__setattr__(self, "probe_catalog_sha256", catalog)
        _require(self.probe_catalog_sha256 == catalog, "invalid-policy")
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
        launch = (self.claude, *(p for p, _ in self.helpers))
        return launch + (self.interpreter,) if entry == LAUNCH_PROBE else launch

    def exec_probe(self, entry: str) -> list[str]:
        """A command the profile of ``entry`` allows and that must succeed (the compile positive case)."""
        _require(entry in ENTRIES, "invalid-entry")
        if entry == "fixture":
            return [self.interpreter, "-B", "-I", "-S", "-c", "pass"]
        return [self.claude, "--version"]

    def render(self, entry: str) -> bytes:
        """Deterministic SBPL; per-run paths arrive only as ``CANDIDATE``/``TMPDIR``/``RUNDIR`` params.

        ``launch-probe`` is ``launch`` plus what the pinned interpreter needs to start and nothing
        else: its exec (so read and map) literal, a read of ``interpreter_root`` (the standard library;
        ``fixture`` grants the same) and the metadata of their ancestor directories. It lets the T007
        helper probes run under the profile Claude runs under; ``harness_qualification_probes``
        re-checks that this is the whole difference.
        """
        execs = self.executables(entry)
        reads = list(SYSTEM_READ) + ([self.interpreter_root] if entry != "launch" else [])
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
            # metadata of run_root itself and of this run's directory only, not of its other entries
            f"(allow file-read-metadata {literals('literal', metadata)} (literal \"{self.run_root}\") "
            '(literal (param "RUNDIR")))',
            '(allow file-read* file-write* (subpath (param "CANDIDATE")) (subpath (param "TMPDIR")))',
        ]
        if entry != "fixture":
            lines += [
                f"(allow sysctl-read {literals('sysctl-name', SYSCTL_READ_NAMES)} "
                f"{literals('sysctl-name-prefix', SYSCTL_READ_PREFIXES)})",
                f"(allow file-read-data {literals('literal', LOCALE_READ)})",
                f"(allow file-read-metadata {literals('literal', METADATA_ONLY)})",
            ]
        if writes:
            lines.append(f"(allow file-read* file-write* {literals('subpath', writes)})")
        if writes:  # the token reaches the child through its environment only; the file stays out of its reach
            lines.append(f'(deny file-read* file-write* (literal "{self.config_dir}/{TOKEN_FILE}"))')
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
            env["PYTHONDONTWRITEBYTECODE"] = "1"  # the interpreter must not write .pyc files (no write allowed)
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


@dataclass(frozen=True)
class AccountFacts:
    """Observed facts that keep the dedicated account dedicated; part of the environment hash."""

    gids: tuple[int, ...]
    home_mode: int


# Trusted code read by path (no import: the transport imports this module). The transport builds the
# Claude argv and pins the build, the quota module gates every session (DRV-05).
_COMPONENT_FILES = ("harness_transport_claude.py", "harness_quota.py")


def _component_hashes() -> dict[str, str]:
    """Trusted code the enforcement relies on: this backend, the lab, the host module, the Claude
    transport and the quota gate."""
    hashes = {Path(m.__file__).name: sha256(Path(m.__file__).read_bytes()).hexdigest()
              for m in (sys.modules[__name__], harness_lab, harness_host_claude)}
    here = Path(__file__).resolve().parent
    return hashes | {name: sha256((here / name).read_bytes()).hexdigest() for name in _COMPONENT_FILES}


def environment_sha256(policy: ContainmentPolicy, facts: HostFacts, uid: int,
                       account: AccountFacts | None = None) -> str:
    """Canonical digest of every environment-hash input of contracts/native-profile.md.

    ``account`` is what the backend observed for the dedicated user; a caller that omits it
    computes a digest the backend will not match.
    """
    supervisor = os.path.realpath(sys.executable)
    value = {
        "format": ENVIRONMENT_FORMAT,
        "os": asdict(facts),
        "mechanism": {"backend": BACKEND, "sandboxExec": SANDBOX_EXEC,
                      "sandboxExecSha256": policy.sandbox_exec_sha256,
                      "account": policy.account, "uid": uid,
                      "accountFacts": None if account is None else
                      {"gids": sorted(account.gids), "homeMode": account.home_mode}},
        "profiles": {entry: sha256(policy.render(entry)).hexdigest() for entry in ENTRIES},
        "claude": {"path": policy.claude, "sha256": policy.claude_sha256,
                   "version": policy.claude_version},
        "helpers": [list(h) for h in policy.helpers],
        "interpreter": {"path": policy.interpreter, "sha256": policy.interpreter_sha256,
                        "root": policy.interpreter_root},
        "supervisor": {"path": supervisor, "sha256": _file_sha256(supervisor)},
        "credentialMethod": CREDENTIAL_METHOD,
        "authentication": {"tokenFile": TOKEN_FILE, "tokenVariable": TOKEN_VARIABLE,
                           "runTagVariable": RUN_TAG_VARIABLE},
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
        lib.sysctl.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.c_uint, ctypes.c_void_p,
                               ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p, ctypes.c_size_t]
        lib.proc_listpids.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
        lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p,
                                     ctypes.c_int]
        lib.proc_pid_rusage.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_void_p]
        for name in ("sysctlbyname", "sysctl", "proc_listpids", "proc_pidinfo", "proc_pid_rusage"):
            getattr(lib, name).restype = ctypes.c_int
        _LIBSYSTEM = lib
    return _LIBSYSTEM


def _account_groups(account: str, gid: int) -> tuple[int, ...]:
    return tuple(sorted(set(os.getgrouplist(account, gid))))


def _operator_refusal(account: str, uid: int, operator: str, operator_uid: int | None) -> str | None:
    """The refusal reason for the RV-16 operator rule, or None. Shared by the backend and the T009 driver."""
    if operator_uid is None or operator_uid < _MIN_HUMAN_UID:
        return "operator-account-unresolved"
    if operator == account:
        return "invalid-policy"
    if uid < _MIN_HUMAN_UID or uid == operator_uid:
        return "dedicated-user-unsafe"
    return None


def _account_facts(account: str, entry, uid: int, operator_uid: int) -> AccountFacts:
    """Refuse a privileged or system account, the operator's own, or one with an open home (RV-16).

    RV-16 amended (founder, 2026-11-03): the owner of ``/dev/console`` is no longer refused, because
    fast user switching makes the dedicated account the console owner. The lab must still never run
    as the operator's daily account, so that account is named explicitly and compared by uid.
    """
    try:
        gids = _account_groups(account, entry.pw_gid)
        home = os.lstat(entry.pw_dir)
    except OSError:
        raise LabError("dedicated-user-unsafe") from None
    _require(not _PRIVILEGED_GIDS & {entry.pw_gid, *gids} and uid >= _MIN_HUMAN_UID and uid != operator_uid
             and stat.S_ISDIR(home.st_mode) and home.st_uid == uid and not home.st_mode & 0o077,
             "dedicated-user-unsafe")
    return AccountFacts(gids, stat.S_IMODE(home.st_mode))


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


_PROC_RUID_ONLY, _PROC_PIDTASKINFO = 5, 4
_TASKINFO_WORDS = 12  # struct proc_taskinfo is 96 bytes; resident size is word 1
# struct rusage_info_v2 (RUSAGE_INFO_V2 = 2): ``ri_phys_footprint`` is the 8-byte word at offset 72. It counts
# the pages the process owns including those the memory compressor or swap hold, which ``pti_resident_size``
# omits; the watchdog measures the larger of the two.
_RUSAGE_INFO_V2, _RUSAGE_WORDS, _FOOTPRINT_WORD = 2, 32, 9

# struct kinfo_proc (sys/sysctl.h, 648 bytes on arm64 and x86_64) from sysctl KERN_PROC/KERN_PROC_PID:
# a plain process-table read that needs no task access, so it works for every process of the same user.
_CTL_KERN, _KERN_PROC, _KERN_PROC_PID = 1, 14, 1
_KINFO_BYTES = 648
_KP_STAT, _KP_PID, _KP_PPID, _KP_PGID = 36, 40, 560, 564  # p_stat (1 byte), p_pid, e_ppid, e_pgid
_SZOMB = 5  # p_stat of a process that exited and is not yet reaped


def _accounting_error(code: int, flavor: int) -> LabError:
    """The fixed refusal plus two integers (errno of the failed call, its flavor) for the evidence."""
    error = LabError("process-accounting-failed")
    error.errno_code, error.flavor = code, flavor
    return error


def _kinfo(pid: int) -> tuple[int, int, int, int] | None:
    """``(start time in microseconds, parent pid, process group, p_stat)``; ``None`` only when gone.

    Any other failure, or an answer that is not the 648-byte record of ``pid``, fails closed.
    """
    mib = (ctypes.c_int * 4)(_CTL_KERN, _KERN_PROC, _KERN_PROC_PID, pid)
    size, buffer = ctypes.c_size_t(_KINFO_BYTES), ctypes.create_string_buffer(_KINFO_BYTES)
    ctypes.set_errno(0)
    if _libsystem().sysctl(mib, 4, buffer, ctypes.byref(size), None, 0) != 0:
        code = ctypes.get_errno()
        if code == errno.ESRCH:
            return None
        raise _accounting_error(code, _KERN_PROC)
    if size.value == 0:  # the table has no such pid
        return None
    raw = buffer.raw
    if size.value != _KINFO_BYTES or struct.unpack_from("=i", raw, _KP_PID)[0] != pid:
        raise _accounting_error(errno.EINVAL, _KERN_PROC)
    seconds, microseconds = struct.unpack_from("=qi", raw, 0)
    return (seconds * 1_000_000 + microseconds, struct.unpack_from("=i", raw, _KP_PPID)[0],
            struct.unpack_from("=i", raw, _KP_PGID)[0], raw[_KP_STAT])


def _footprint(pid: int) -> int:
    """``ri_phys_footprint`` of ``pid`` in bytes; ``0`` when the call fails (the resident size still counts)."""
    buffer = (ctypes.c_uint64 * _RUSAGE_WORDS)()
    if _libsystem().proc_pid_rusage(pid, _RUSAGE_INFO_V2, buffer) != 0:
        return 0
    return buffer[_FOOTPRINT_WORD]


def _task_resident(pid: int) -> int | None:
    """Resident bytes from one ``proc_pidinfo`` task call; ``None`` only when the process is gone or exited.

    Only the child and its descendants are measured (the memory watchdog); a live one the call cannot
    read fails closed. An exited and not yet reaped process (``SZOMB``) has no task any more: the call
    fails for it while ``kill(pid, 0)`` still succeeds, so it counts as gone, not as unreadable.
    """
    buffer = (ctypes.c_uint64 * _TASKINFO_WORDS)()
    ctypes.set_errno(0)
    if _libsystem().proc_pidinfo(pid, _PROC_PIDTASKINFO, 0, buffer, ctypes.sizeof(buffer)) == ctypes.sizeof(buffer):
        return max(buffer[1], _footprint(pid))
    code = ctypes.get_errno()
    if code == errno.ESRCH:
        return None
    if (found := _kinfo(pid)) is None or found[3] == _SZOMB:
        return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except OSError:
        pass
    raise _accounting_error(code, _PROC_PIDTASKINFO)


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
        if pid > 0 and (info := _kinfo(pid)) is not None:
            out.add((pid, info[0]))
    return out


_KERN_PROCARGS2, _PROCARGS_BYTES = 49, 1 << 20


def _tagged(pid: int, tag: bytes) -> bool | None:
    """Whether the environment of ``pid`` holds the entry ``tag`` (``NAME=value``); ``None`` when unreadable
    (the caller asks again later).

    ``KERN_PROCARGS2`` of a process of the same user needs no privilege. The entry must start a string, so
    it is an environment (or argument) string and not the tail of another.
    """
    mib = (ctypes.c_int * 3)(_CTL_KERN, _KERN_PROCARGS2, pid)
    size, buffer = ctypes.c_size_t(_PROCARGS_BYTES), ctypes.create_string_buffer(_PROCARGS_BYTES)
    if _libsystem().sysctl(mib, 3, buffer, ctypes.byref(size), None, 0) != 0:
        return None
    return b"\0" + tag in ctypes.string_at(buffer, size.value)


def _process_links(identity: tuple[int, int]) -> tuple[int | None, int | None]:
    """``(parent pid, process group)`` of one listed process from a single read; ``(None, None)`` when it is
    gone or the pid now belongs to another process (a different start time)."""
    info = _kinfo(identity[0])
    return (info[1], info[2]) if info is not None and info[0] == identity[1] else (None, None)


def _resident_bytes(processes: set[tuple[int, int]]) -> int:
    return sum(_task_resident(pid) or 0 for pid, _ in processes)


def _unreadable_tasks(processes: set[tuple[int, int]]) -> int:
    """How many of ``processes`` ``proc_pidinfo`` cannot read for lack of permission (evidence only)."""
    count = 0
    buffer = (ctypes.c_uint64 * _TASKINFO_WORDS)()
    for pid, _ in processes:
        ctypes.set_errno(0)
        if _libsystem().proc_pidinfo(pid, _PROC_PIDTASKINFO, 0, buffer, ctypes.sizeof(buffer)) <= 0 \
                and ctypes.get_errno() == errno.EPERM:
            count += 1
    return count


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


class _Refused(Exception):
    """A request the proxy turned away; ``direct`` marks a client not speaking CONNECT at all."""

    def __init__(self, reason: str, *, direct: bool = False):
        super().__init__(reason)
        self.reason = reason
        self.direct = direct


class EgressProxy:
    """Loopback CONNECT proxy: listed ``host:443`` only, and only when SNI equals the host.

    It is the only egress the profile allows and holds the port on both ``127.0.0.1``
    and ``::1`` (the profile's ``localhost`` covers both). It resolves names itself, so
    the child needs no DNS; plain HTTP, other methods and other hosts are refused. The
    request head and ClientHello must arrive within one handshake deadline and a tunnel
    lives at most one session wall bound. The SNI check is defence in depth: the proxy
    connects to the CONNECT host itself, so it only catches a client that disagrees with
    its own request.

    ``counters()`` returns thread-safe totals since construction: ``connections``,
    ``allowed`` (tunnels opened, with ``allowed:<host:port>``), ``denied`` (CONNECT-speaking
    requests refused, with ``denied:<reason>``), ``unexpectedDirect`` (connections whose
    first request is not a CONNECT: a client treating the proxy as an origin server),
    ``upstreamFailed`` and the relayed ``bytesUp``/``bytesDown``. A connection attempt the
    kernel denies never reaches the proxy and is not counted. ``healthy`` turns false when
    the accept loop dies outside ``close()``.
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
        self._failed = False
        self._counts: Counter[str] = Counter()
        self._counts_lock = threading.Lock()

    @property
    def running(self) -> bool:
        return bool(self._servers)

    @property
    def healthy(self) -> bool:
        return not self._failed

    def counters(self) -> dict[str, int]:
        with self._counts_lock:
            return dict(self._counts)

    def _add(self, key: str, amount: int = 1) -> None:
        with self._counts_lock:
            self._counts[key] += amount

    def start(self) -> None:
        self._failed = False
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
                if server in self._servers:  # not a close(); fail closed, but visible to the next pre-session check
                    self._failed = True
                return
            self._add("connections")
            if not self._slots.acquire(blocking=False):
                self._add("denied")
                self._add("denied:capacity")
                client.close()
                continue
            threading.Thread(target=self._serve, args=(client,), daemon=True).start()

    def _serve(self, client: socket.socket) -> None:
        try:
            with client:
                self._tunnel(client, time.monotonic() + self._timeout)
        except _Refused as refusal:
            self._add("unexpectedDirect" if refusal.direct else "denied")
            if not refusal.direct:
                self._add(f"denied:{refusal.reason}")
        except (OSError, ValueError):
            pass
        finally:
            self._slots.release()

    @staticmethod
    def _recv(client: socket.socket, deadline: float, size: int) -> bytes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _Refused("timeout")
        client.settimeout(remaining)
        try:
            return client.recv(size)
        except TimeoutError:
            raise _Refused("timeout") from None

    def _tunnel(self, client: socket.socket, deadline: float) -> None:
        buffer = b""
        while b"\r\n\r\n" not in buffer:
            chunk = self._recv(client, deadline, 4096)
            if not chunk:
                raise _Refused("incomplete")
            if len(buffer) + len(chunk) > self.MAX_HEAD:
                raise _Refused("head-too-large")
            buffer += chunk
        head, _, buffer = buffer.partition(b"\r\n\r\n")
        parts = head.split(b"\r\n", 1)[0].split(b" ")
        method, target, version = parts if len(parts) == 3 else (b"", b"", b"")
        host_port = target.decode("ascii", "replace").lower()
        refusal = (_Refused("not-connect", direct=True) if method != b"CONNECT"
                   else _Refused("bad-request") if not version.startswith(b"HTTP/1.")
                   else _Refused("target-not-allowed") if host_port not in self.endpoints else None)
        if refusal is not None:
            client.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
            raise refusal
        client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        while len(buffer) < 5 or len(buffer) < 5 + int.from_bytes(buffer[3:5], "big"):
            if len(buffer) >= 5 and 5 + int.from_bytes(buffer[3:5], "big") > self.MAX_RECORD:
                raise _Refused("hello-too-large")
            chunk = self._recv(client, deadline, 65_536)
            if not chunk:
                raise _Refused("incomplete")
            buffer += chunk
        length = 5 + int.from_bytes(buffer[3:5], "big")
        hello, rest = buffer[:length], buffer[length:]
        host, port = host_port.rsplit(":", 1)
        if client_hello_sni(hello) != host:
            raise _Refused("sni-mismatch")
        try:
            upstream = self._connect((host, int(port)), timeout=self._timeout)
        except OSError:
            self._add("upstreamFailed")
            return
        with upstream:
            self._add("allowed")
            self._add(f"allowed:{host_port}")
            self._add("bytesUp", len(hello) + len(rest))
            upstream.sendall(hello + rest)
            _relay(client, upstream, self._timeout, time.monotonic() + self._tunnel_seconds, self._add)


def _relay(a: socket.socket, b: socket.socket, idle: float, deadline: float,
           tally: Callable[[str, int], None]) -> None:
    """Copy both ways until close, idle timeout or ``deadline``; ``tally`` sees the bytes first."""
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
                tally("bytesUp" if key.fileobj is a else "bytesDown", len(data))
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


@dataclass(frozen=True, kw_only=True)
class RunAccounting:
    """What one supervised run measured, beyond the lab and host results (additive fields).

    ``escaped_processes`` are processes of the child's own tree (see ``_Lineage``) seen after the group
    settled, i.e. that left the group; the sweep kills them and ``settled`` stays strict. Other new
    processes of the user (launchd agents) are not escapes; the run evidence counts them as
    ``unrelatedProcesses``.
    ``surviving_processes`` are those still alive after the final sweep iteration: a judge
    of "survives kill" uses this one. ``escaped_descendants`` are the leavers that were seen
    in the child's process tree during the run (polled, so a fast double fork between two
    polls is only counted as unattributed: ``escaped_processes - escaped_descendants``).
    ``egress`` is the proxy counter delta of the run (see ``EgressProxy``).
    ``limit_exceeded`` is the resource stop reason of the run: ``memory`` (watchdog) or ``cpu``
    (``SIGXCPU`` from the CPU rlimit), else ``None``. A disk breach refuses the run instead.
    ``peak_memory_bytes`` and ``memory_samples`` are what the memory watchdog measured (the larger of the
    resident size and the physical footprint, summed over the child's tree) and how often: evidence for a
    memory limit that did not fire.
    """

    escaped_processes: int = 0
    escaped_descendants: int = 0
    surviving_processes: int = 0
    cleanup_failed: bool = False
    disk_bytes: int = 0
    disk_files: int = 0
    limit_exceeded: str | None = None
    peak_memory_bytes: int = field(default=0, compare=False)
    memory_samples: int = field(default=0, compare=False)
    egress: dict = field(default_factory=dict, compare=False, hash=False)


@dataclass(frozen=True)
class ContainedHostRun(RunAccounting, HostRun):
    """``HostRun`` of ``launch`` plus the run accounting."""


@dataclass(frozen=True)
class ProbeResult(RunAccounting, ChildResult):
    """``ChildResult`` of ``run``/``run_probe`` plus ``cancelled`` and the run accounting."""

    cancelled: bool = False


class _Lineage:
    """The child's own tree (the child, its descendants and the members of its process group) among the
    new processes of the dedicated user; every other new process is unrelated.

    A new process is the child's when it is the child, when its parent is the child or an earlier
    member, or when its process group is led by the child or an earlier member (an orphan reparented to
    ``launchd`` keeps the group), or when its environment carries the run's ``RUN_TAG_VARIABLE`` (every
    descendant inherits it, so a ``setsid`` leaver reparented before it was first seen is still found,
    PROC-ESC-1). The links and the tag are read once, when the process is first seen. Residual: a
    descendant that also scrubs its environment (``exec`` with an empty one) before the poll that would
    have seen it, or that starts and exits between two polls, reads as unrelated (T009 re-check).
    """

    def __init__(self, root: int, tag: bytes | None = None):
        self._root = root
        self._tag = tag  # ``RUN_TAG_VARIABLE=<value>`` as bytes; ``None`` disables the environment test
        self._pids = {root}
        self._links: dict[tuple[int, int], tuple[int | None, int | None]] = {}
        self._tagged: set[tuple[int, int]] = set()
        self._unread: set[tuple[int, int]] = set()  # environment not readable yet: asked again at the next poll
        self.identities: set[tuple[int, int]] = set()

    def observe(self, processes: set[tuple[int, int]]) -> None:
        for identity in processes - self._links.keys():
            self._links[identity] = _process_links(identity)
            self._unread.add(identity)
        for identity in self._unread & processes if self._tag is not None else ():
            found = _tagged(identity[0], self._tag)
            if found is not None:
                self._unread.discard(identity)
                if found:
                    self._tagged.add(identity)
        grew = True
        while grew:
            grew = False
            for identity, (parent, group) in self._links.items():
                if identity[0] != self._root and identity not in self.identities \
                        and (parent in self._pids or group in self._pids or identity in self._tagged):
                    self.identities.add(identity)
                    self._pids.add(identity[0])
                    grew = True

    def members(self, processes: set[tuple[int, int]]) -> set[tuple[int, int]]:
        """The child's own processes among ``processes``, after observing them."""
        self.observe(processes)
        return {identity for identity in processes if identity[0] == self._root or identity in self.identities}

    def unrelated(self) -> set[tuple[int, int]]:
        """Every process seen so far that is not the child's."""
        return {identity for identity in self._links
                if identity[0] != self._root and identity not in self.identities}


class _DiskGuard:
    """Total bytes (disk blocks, each inode once) and entry count of the run's writable trees:
    the candidate, the per-run ``TMPDIR`` and the dedicated user's ``config_dir`` together.

    Symbolic links are not followed. A directory that cannot be listed counts as over the
    limit: the child cannot be allowed to hide data from the measurement.
    """

    def __init__(self, roots: tuple[str, ...]):
        self._roots = roots
        self.bytes = self.files = 0

    def exceeded(self) -> bool:
        max_bytes, max_files = LIMITS["diskBytes"], LIMITS["diskFiles"]
        inodes: set[tuple[int, int]] = set()
        self.bytes = self.files = 0
        pending = list(self._roots)
        while pending:
            try:
                with os.scandir(pending.pop()) as listing:
                    entries = list(listing)
            except (FileNotFoundError, NotADirectoryError):
                continue
            except OSError:
                return True
            for entry in entries:
                try:
                    info = entry.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                except OSError:
                    return True  # listable but not searchable: unmeasurable
                self.files += 1
                if (info.st_dev, info.st_ino) not in inodes:
                    inodes.add((info.st_dev, info.st_ino))
                    self.bytes += info.st_blocks * 512
                if stat.S_ISDIR(info.st_mode):
                    pending.append(entry.path)
            if self.bytes > max_bytes or self.files > max_files:
                return True
        return False


def _resource_limit(uid: int, baseline: set[tuple[int, int]], lineage: _Lineage,
                    disk: _DiskGuard, state: dict) -> str | None:
    """The first exceeded resource limit (``memory`` or ``disk``), else ``None``.

    ``state`` receives the largest measured memory of the child's tree and the number of measurements
    (integers, evidence for a limit that did not fire).
    """
    own = lineage.members(_user_processes(uid) - baseline)  # unrelated processes are not measured
    measured = _resident_bytes(own)
    state["memorySamples"] = state.get("memorySamples", 0) + 1
    state["peakMemoryBytes"] = max(state.get("peakMemoryBytes", 0), measured)
    if measured > LIMITS["memoryBytes"]:
        return "memory"
    return "disk" if disk.exceeded() else None


def _counter_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {key: value - before.get(key, 0) for key, value in after.items() if value != before.get(key, 0)}


class MacOSContainment(ContainmentBackend):
    """Native backend; refuses with a fixed reason whenever any check fails.

    The probe runner is trusted T007 code; the policy derives ``probe_catalog_sha256`` from
    it, so the environment hash binds the catalog and the runner source. ``run_probe`` and
    ``run_launch_probe`` (the ``launch-probe`` profile) let it run probes contained without
    recursing into the NC-11 subset.
    """

    kind = "native"

    def __init__(self, policy: ContainmentPolicy, *, qualification: bytes, qualification_sha256: str,
                 host_qualification: bytes, host_qualification_sha256: str,
                 probe_runner: ProbeRunner | None, operator_account: str,
                 clock: Callable[[], float] = time.time):
        _require(isinstance(policy, ContainmentPolicy), "invalid-policy")
        _require(type(operator_account) is str and _ACCOUNT.fullmatch(operator_account) is not None
                 and operator_account != policy.account, "invalid-policy")
        self.policy = policy
        self.operator_account = operator_account  # the account the lab must never run as (RV-16)
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

    def egress_counters(self) -> dict[str, int]:
        """Totals of the backend's egress proxy (see ``EgressProxy.counters``); read-only."""
        return self._proxy.counters()

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
            account = pwd.getpwnam(policy.account)
        except KeyError:
            raise LabError("dedicated-user-required") from None
        uid = account.pw_uid
        _require(uid != 0 and os.getuid() == uid and os.geteuid() == uid, "dedicated-user-required")
        try:
            operator_uid = pwd.getpwnam(self.operator_account).pw_uid
        except KeyError:
            raise LabError("operator-account-unresolved") from None
        _require(operator_uid >= _MIN_HUMAN_UID, "operator-account-unresolved")
        evidence["operator"] = {"account": self.operator_account, "uid": operator_uid}
        account_facts = _account_facts(policy.account, account, uid, operator_uid)
        evidence["account"] = {"gids": list(account_facts.gids), "homeMode": account_facts.home_mode}
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
        environment = environment_sha256(policy, facts, uid, account_facts)
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

    def _sandboxed(self, entry: str, probe_dir: str, target: list[str], env: dict[str, str]) -> int:
        """Exit code of ``target`` under the rendered profile, with every param set to ``probe_dir``."""
        return subprocess.run(
            [SANDBOX_EXEC, "-p", self.policy.render(entry).decode(), "-D", f"CANDIDATE={probe_dir}",
             "-D", f"TMPDIR={probe_dir}", "-D", f"RUNDIR={probe_dir}", "--", *target],
            env=env, cwd=probe_dir, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=_COMPILE_TIMEOUT_SECONDS, check=False).returncode

    def _leftovers(self) -> bool:
        """A run or compile directory an earlier run could not remove (the child can make that so)."""
        try:
            return any(name.startswith(_OWNED) for name in os.listdir(self.policy.run_root))
        except OSError:
            raise LabError("workspace-unsafe") from None

    def _compile_check(self, entry: str, evidence: dict) -> None:
        """The exact profile must compile, deny a non-listed exec and run a listed one.

        The positive case (RV-23) tells "denied by the profile" from "exec failed anyway": a
        profile that denied everything would otherwise pass. ``launch`` runs the pinned
        Claude executable with ``--version`` under the profile; ``fixture`` runs the
        interpreter on an empty program. The two exit codes (integers) are left in ``evidence`` as
        ``compileExit`` so a refusal can be told apart without the system log.
        """
        probe_dir = None
        denied = allowed = None
        try:
            probe_dir = tempfile.mkdtemp(prefix="compile-", dir=self.policy.run_root)
            os.mkdir(f"{probe_dir}/home", 0o700)  # the child environment's HOME
            denied = self._sandboxed(entry, probe_dir, [COMPILE_PROBE], {})
            if denied == EXIT_SANDBOX_EXEC_DENIED:
                allowed = self._sandboxed(entry, probe_dir, self.policy.exec_probe(entry),
                                          self.policy.child_environment(entry, probe_dir))
        except (OSError, subprocess.TimeoutExpired):
            raise LabError("profile-compile-failed") from None
        finally:
            if probe_dir is not None:
                _remove_tree(probe_dir)  # a failure shows as a leftover at the next pre-session
        evidence["compileExit"] = {name: code for name, code in (("denied", denied), ("allowed", allowed))
                                   if code is not None}
        _require(denied != EXIT_SANDBOX_COMPILE, "profile-compile-failed")
        _require(denied == EXIT_SANDBOX_EXEC_DENIED, "self-check-allowed")
        _require(allowed == 0, "self-check-failed")

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
            _require(not self._leftovers(), "workspace-leftovers")
            if self._proxy.running and not self._proxy.healthy:
                self._proxy.close()  # the next attempt starts a fresh one
                raise LabError("proxy-unavailable")
            if not self._proxy.running:
                self._proxy.start()
            self._compile_check(entry, evidence)
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

    def run(self, source: bytes, workdir: Path, limits: FixtureLimits) -> ProbeResult:
        """Owned fixture entry point, after the full NC-11 pre-session check."""
        return self._fixture("fixture", source, workdir, limits, probes=True, cancel=None)

    def run_probe(self, source: bytes, workdir: Path, limits: FixtureLimits, *,
                  cancel: threading.Event | None = None) -> ProbeResult:
        """Probe entry point for the T007 runner: same profile and checks, no probe subset.

        ``cancel`` is optional: setting it stops and settles the group, and the result says
        ``cancelled`` (the PROC-08 cancellation half).
        """
        return self._fixture("fixture", source, workdir, limits, probes=False, cancel=cancel)

    def run_launch_probe(self, source: bytes, workdir: Path, limits: FixtureLimits, *,
                         cancel: threading.Event | None = None) -> ProbeResult:
        """``run_probe`` under the ``launch-probe`` profile: what Claude runs under plus the interpreter.

        Same checks, no probe subset, its own exclusive run; the compile check runs the pinned
        Claude ``--version`` like ``launch``. Only the T007 runner calls it.
        """
        return self._fixture(LAUNCH_PROBE, source, workdir, limits, probes=False, cancel=cancel)

    def _fixture(self, entry: str, source: bytes, workdir: Path, limits: FixtureLimits, *, probes: bool,
                 cancel: threading.Event | None) -> ProbeResult:
        if (type(source) is not bytes or not isinstance(limits, FixtureLimits)
                or not (cancel is None or isinstance(cancel, threading.Event))):
            self._refuse(entry, "invalid-lab-request")
        try:
            text = source.decode("utf-8")
        except UnicodeDecodeError:
            self._refuse(entry, "invalid-fixture")
        with self._exclusive(entry):
            evidence, candidate, uid = self._pre_session(entry, workdir, probes=probes)
            run = self._spawn(entry, [self.policy.interpreter, "-B", "-I", "-S", "-c", text], evidence,
                              candidate=candidate, uid=uid, wall=limits.wall_seconds,
                              cpu=min(limits.wall_seconds + 1, LIMITS["cpuSeconds"]),
                              max_output=limits.max_output_bytes, cancel=cancel, stdin=b"")
        return ProbeResult(run.stdout, run.exit_code, run.timed_out, run.output_truncated, run.settled,
                           cancelled=run.cancelled,
                           **{f.name: getattr(run, f.name) for f in fields(RunAccounting)})

    def launch(self, argv: tuple[str, ...], stdin: bytes, *, cwd: Path | str, wall_seconds: int,
               max_output_bytes: int, cancel: threading.Event,
               on_output: Callable[[bytes], None] | None = None) -> ContainedHostRun:
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
               stdin: bytes, on_output: Callable[[bytes], None] | None = None) -> ContainedHostRun:
        """Supervise one contained child; whatever happens it is killed, settled and recorded."""
        record = dict(evidence)
        try:
            return self._supervise(entry, target, record, candidate=candidate, uid=uid, wall=wall,
                                   cpu=cpu, max_output=max_output, cancel=cancel, stdin=stdin,
                                   on_output=on_output)
        except LabError as exc:
            record["refused"] = exc.reason
            if type(getattr(exc, "errno_code", None)) is int:  # integers only, for the evidence
                record["accountingErrno"], record["accountingFlavor"] = exc.errno_code, exc.flavor
            raise
        except Exception:
            record["refused"] = "supervisor-failed"
            raise LabError("supervisor-failed") from None
        finally:
            self.run_evidence.append(record)

    def _supervise(self, entry: str, target: list[str], record: dict, *, candidate: str, uid: int,
                   wall: int, cpu: int, max_output: int, cancel: threading.Event | None,
                   stdin: bytes, on_output: Callable[[bytes], None] | None = None) -> ContainedHostRun:
        policy = self.policy
        token = read_token(policy.config_dir, uid) if entry == "launch" else None  # before anything is created
        if entry == "launch":
            record["authToken"] = "present" if token else "absent"  # never the value
        try:
            run_dir = tempfile.mkdtemp(prefix="run-", dir=policy.run_root)
        except OSError:
            raise LabError("workspace-unavailable") from None
        tmpdir = f"{run_dir}/tmp"
        child = status = lineage = None
        baseline: set[tuple[int, int]] = set()
        state: dict = {"timedOut": False, "cancelled": False, "outputTruncated": False,
                       "limitExceeded": None}
        egress_before = self._proxy.counters()
        disk = _DiskGuard((candidate, tmpdir, policy.config_dir))
        out_path = f"{run_dir}/stdout"
        live = _OutputStream(out_path, max_output, on_output, cancel) if on_output is not None else None
        try:
            try:
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
                        "-D", f"TMPDIR={tmpdir}", "-D", f"RUNDIR={run_dir}", "--", *target]
                tag = f"{RUN_TAG_VARIABLE}={secrets.token_hex(16)}"
                env = policy.child_environment(entry, tmpdir) | {RUN_TAG_VARIABLE: tag.partition("=")[2]}
                if token:
                    env[TOKEN_VARIABLE] = token
                try:
                    child = subprocess.Popen(argv, cwd=run_dir, env=env,
                                             stdin=source, stdout=sink, stderr=subprocess.DEVNULL,
                                             close_fds=True, pass_fds=(status_w,), start_new_session=True)
                except (OSError, ValueError):
                    raise LabError("launch-failed") from None
                finally:
                    os.close(status_w)
                lineage = _Lineage(child.pid, tag.encode())
                self._watch(child, state, uid=uid, baseline=baseline, out_path=out_path,
                            deadline=time.monotonic() + wall, max_output=max_output, cancel=cancel,
                            live=live, lineage=lineage, disk=disk)
        finally:
            sweep_error = None
            if child is not None:
                if child.poll() is None:
                    child.kill()
                    child.wait()  # reap the leader so only live group members remain
                state["settled"] = _settle(child.pid)
                state["baselineProcesses"] = len(baseline)
                try:
                    escaped, surviving = self._sweep(uid, baseline, lineage)
                    descendants = len(escaped & lineage.identities)
                    state.update(escapedProcesses=len(escaped), escapedDescendants=descendants,
                                 unattributedProcesses=len(escaped) - descendants,
                                 survivingProcesses=surviving)
                except LabError as exc:  # cleanup still runs; the run stays unsettled
                    sweep_error = exc
                unrelated = lineage.unrelated()  # noise level for the evidence: counts only, never acted on
                try:
                    unreadable = _unreadable_tasks(unrelated)
                except Exception:
                    unreadable = 0
                state.update(unrelatedProcesses=len(unrelated), unreadableProcesses=unreadable)
            stopped_early = (state["timedOut"] or state["cancelled"] or state["outputTruncated"]
                             or state["limitExceeded"])
            if live is not None:
                if not stopped_early:
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
            if child is not None and not stopped_early and disk.exceeded():
                state["limitExceeded"] = "disk"  # a burst written just before a natural exit
            try:
                cleaned = _remove_tree(run_dir)
            except Exception:  # e.g. RecursionError on a hostile deep tree: record, do not mask
                cleaned = False
            stopped = stopped_early or state["limitExceeded"]
            exit_code = None if child is None or stopped else child.returncode
            if child is not None and not state["limitExceeded"] and child.returncode == -signal.SIGXCPU:
                state["limitExceeded"] = "cpu"
            settled = bool(state.get("settled")) and state.get("escapedProcesses") == 0
            egress = _counter_delta(egress_before, self._proxy.counters())
            record.update(state, exitCode=exit_code, settled=settled, cleanupFailed=not cleaned,
                          diskBytes=disk.bytes, diskFiles=disk.files, egress=egress)
        if sweep_error is not None:
            raise sweep_error
        _require(not state.get("callbackFailed"), "output-callback-failed")
        _require(state["limitExceeded"] != "disk", "disk-limit-exceeded")
        _require(not preamble_failed, "rlimit-unenforceable")
        truncated = state["outputTruncated"] or len(data) > max_output
        record["outputTruncated"] = truncated
        return ContainedHostRun(
            data[:max_output], exit_code, state["timedOut"], state["cancelled"], truncated, settled,
            escaped_processes=state.get("escapedProcesses", 0),
            escaped_descendants=state.get("escapedDescendants", 0),
            surviving_processes=state.get("survivingProcesses", 0), cleanup_failed=not cleaned,
            disk_bytes=disk.bytes, disk_files=disk.files, limit_exceeded=state["limitExceeded"],
            peak_memory_bytes=state.get("peakMemoryBytes", 0), memory_samples=state.get("memorySamples", 0),
            egress=egress)

    def _watch(self, child: subprocess.Popen, state: dict, *, uid: int, baseline: set[tuple[int, int]],
               out_path: str, deadline: float, max_output: int, cancel: threading.Event | None,
               live: "_OutputStream | None", lineage: _Lineage, disk: _DiskGuard) -> None:
        """Poll until exit or the first wall, cancel, output, memory or disk stop; records which."""
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
            elif (limit := _resource_limit(uid, baseline, lineage, disk, state)) is not None:
                state["limitExceeded"] = limit
            else:
                time.sleep(_POLL_SECONDS)
                continue
            return

    def _sweep(self, uid: int, baseline: set[tuple[int, int]],
               lineage: _Lineage) -> tuple[set[tuple[int, int]], int]:
        """Kill every new process of the child's own tree left after the group settled.

        Returns the processes seen leaving the group and how many were still alive after
        the last kill round (a failed kill or an exhausted retry budget). Any leaver leaves
        the run unsettled even when the kill succeeds. New processes of the dedicated user
        that are not the child's (see ``_Lineage``) are neither killed nor counted: a GUI
        session's launchd agents appear at any time and are not the child's. Only ever runs
        as the dedicated account.
        """
        try:
            account_uid = pwd.getpwnam(self.policy.account).pw_uid
        except KeyError:
            raise LabError("dedicated-user-required") from None
        _require(uid == os.getuid() == account_uid, "dedicated-user-required")
        escaped: set[tuple[int, int]] = set()
        for _ in range(40):
            survivors = lineage.members(_user_processes(uid) - baseline)
            if not survivors:
                return escaped, 0
            escaped |= survivors
            for pid, _ in survivors:
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
            time.sleep(_POLL_SECONDS)
        return escaped, len(lineage.members(_user_processes(uid) - baseline))
