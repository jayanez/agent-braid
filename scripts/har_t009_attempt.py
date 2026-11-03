#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-run driver for the SPEC-065 T009 live qualification attempt.

This script is NOT an authorization. It is the one command the founder runs, inside the dedicated
account's own login session, after the sudo setup of ``quickstart.md`` and after the orchestrator has
verified that setup with ``--dry-run``. ``--dry-run`` performs only the pre-flight checks: it starts no
sandbox, no ``claude`` and no network connection, and prints a JSON verdict. Without ``--dry-run`` it
builds the T005 backend, the T006 transport factory and the T007 runner (``make_qualification_runner``),
runs the whole catalog (at most three small Haiku sessions, NC-10) and writes the evidence bundle.

Everything fails closed: any failed check refuses the attempt before anything native runs. The driver
issues no qualification record. The backend constructor needs verified records bound to the environment
hash, so the driver builds attempt-scoped ones in memory (``evidenceSha256`` all zeros, short expiry); they
are never written, are not issuable evidence and issuance stays T010 (NC-9, founder only).
``executionAuthorization`` is ``false`` in every output.

NC-6 with the operator as reader: before and after each session the driver asks on the terminal for the
Claude Desktop usage card (5-hour %, weekly %, extra usage, reading time) and refuses a missing, malformed,
future-dated or stale (> 5 min) reading; ``harness_quota`` applies the < 90 % start rule, the weekly and
extra-usage stops and the NC-10 2 % rule.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import pwd
import re
import stat
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import harness_containment_macos as _mac  # noqa: E402
from agent_braid import harness_qualification_probes as _probes  # noqa: E402
from agent_braid.harness_host_claude import ENV_DENY, QUALIFICATION_FORMAT as HOST_FORMAT  # noqa: E402
from agent_braid.harness_lab import ENFORCED_EFFECTS, QUALIFICATION_FORMAT as LAB_FORMAT, LabError  # noqa: E402
from agent_braid.harness_quota import FRESHNESS, PROBE_MAX_FIVE_HOUR, SOURCE  # noqa: E402
from agent_braid.harness_transport_claude import NativeClaudeTransport  # noqa: E402
from agent_braid.system_one import canonical  # noqa: E402

DEFAULT_ACCOUNT = "braidlab"
DEFAULT_PROXY_PORT = 18080
EVIDENCE_PARENT = "specs/065-native-claude-containment/evidence/qualification"
CONFIG_MAX_ENTRIES = 64  # MDRV-03: a config_dir that is more than a fresh login is refused
CONFIG_MAX_BYTES = 4 << 20
TREE_MAX_ENTRIES = 200_000
ATTEMPT_RECORD_SECONDS = 4 * 3600
FIVE_HOUR_STOP_SESSION = 10  # NC-6: stop if one session used more than 10 % of the 5-hour window
PRIVILEGED_GIDS = frozenset({0, 80})  # wheel, admin
_ATTEMPT = re.compile(r"[a-z0-9][a-z0-9-]{2,47}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_CLOCK_TIME = re.compile(r"([01]?\d|2[0-3]):([0-5]\d)\Z")
_GROUP_OTHER_WRITE = stat.S_IWGRP | stat.S_IWOTH


class AttemptRefused(Exception):
    """The attempt must not run; ``reasons`` name the failed checks."""

    def __init__(self, reasons: list[str]):
        super().__init__(", ".join(reasons))
        self.reasons = reasons


# --- the host seam: every fact the pre-flight reads, replaceable by a double ---------------------


class System:
    """Reads the real host. Tests replace it with a fake tree; nothing here launches anything."""

    def darwin(self) -> bool:
        return sys.platform == "darwin"

    def ids(self) -> tuple[int, int]:
        return os.getuid(), os.geteuid()

    def passwd_by_uid(self, uid: int):
        try:
            return pwd.getpwuid(uid)
        except KeyError:
            return None

    def passwd_by_name(self, name: str):
        try:
            return pwd.getpwnam(name)
        except KeyError:
            return None

    def console_uid(self) -> int:
        return os.stat("/dev/console").st_uid

    def groups(self, name: str, gid: int) -> tuple[int, ...]:
        return tuple(sorted(set(os.getgrouplist(name, gid))))

    def lstat(self, path: str):
        try:
            return os.lstat(path)
        except OSError:
            return None

    def realpath(self, path: str) -> str:
        return os.path.realpath(path)

    def listdir(self, path: str) -> list[str] | None:
        try:
            return sorted(os.listdir(path))
        except OSError:
            return None

    def walk(self, path: str, limit: int) -> list[tuple[str, object]] | None:
        """``(path, lstat)`` of every entry below ``path`` (symlinks not followed); ``None`` past ``limit``."""
        found: list[tuple[str, object]] = []
        for base, dirs, files in os.walk(path, followlinks=False):
            for name in (*dirs, *files):
                full = os.path.join(base, name)
                info = self.lstat(full)
                if info is None:
                    continue
                found.append((full, info))
                if len(found) > limit:
                    return None
        return found

    def sha256(self, path: str) -> str | None:
        digest = sha256()
        try:
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1 << 20), b""):
                    digest.update(chunk)
        except OSError:
            return None
        return digest.hexdigest()

    def can_traverse(self, path: str) -> bool:
        return os.access(path, os.R_OK | os.X_OK)

    def writable(self, path: str) -> bool:
        return os.access(path, os.W_OK | os.X_OK)

    def environ(self) -> Mapping[str, str]:
        return os.environ

    def host_facts(self):
        return _mac.host_facts()

    def account_facts(self, account: str, entry, uid: int):
        return _mac._account_facts(account, entry, uid)  # the backend's own account check

    def supervisor(self) -> str:
        return os.path.realpath(sys.executable)


# --- pre-flight ------------------------------------------------------------------------------------


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail}


def _ancestors(path: str) -> list[str]:
    parts = path.split("/")[1:-1]
    return ["/" + "/".join(parts[:i]) if i else "/" for i in range(len(parts) + 1)]


def _root_owned(info, *, kind) -> bool:
    return (info is not None and kind(info.st_mode) and info.st_uid == 0
            and not info.st_mode & _GROUP_OTHER_WRITE)


def _trusted_install(system: System, path: str, expected: str | None, label: str) -> list[dict]:
    """RV-22: a regular file owned by root, not group/other writable, below root-owned directories."""
    shape = (isinstance(path, str) and _mac._PATH.fullmatch(path) is not None
             and os.path.normpath(path) == path)
    if not shape:
        return [_check(f"{label}-path", False, "not a normalized absolute path of plain characters")]
    results = []
    bad = [a for a in _ancestors(path) if not _root_owned(system.lstat(a), kind=stat.S_ISDIR)]
    results.append(_check(f"{label}-ancestors-root-owned", not bad,
                          "all ancestors are root-owned directories" if not bad else f"not root-owned: {bad[0]}"))
    info = system.lstat(path)
    results.append(_check(f"{label}-root-owned-file", _root_owned(info, kind=stat.S_ISREG)
                          and bool(info.st_mode & stat.S_IXUSR),
                          "root-owned regular executable, no group/other write" if info is not None
                          else "missing"))
    observed = system.sha256(path) if info is not None else None
    ok = expected is not None and _HASH.fullmatch(expected) is not None and observed == expected
    results.append(_check(f"{label}-sha256", ok,
                          "matches the pin" if ok else
                          f"pin {'missing or malformed' if not expected or not _HASH.fullmatch(expected) else 'differs'};"
                          f" observed {observed}"))
    return results


def _root_owned_tree(system: System, root: str, label: str) -> dict:
    entries = system.walk(root, TREE_MAX_ENTRIES)
    top = system.lstat(root)
    if top is None or not _root_owned(top, kind=stat.S_ISDIR):
        return _check(label, False, "missing or not a root-owned directory")
    if entries is None:
        return _check(label, False, f"more than {TREE_MAX_ENTRIES} entries")
    for path, info in entries:
        if info.st_uid != 0 or info.st_mode & _GROUP_OTHER_WRITE:
            return _check(label, False, f"not root-owned or writable by group/other: {path}")
        if stat.S_ISLNK(info.st_mode) and not system.realpath(path).startswith(root.rstrip("/") + "/"):
            return _check(label, False, f"symlink leaves the tree: {path}")
        if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)):
            return _check(label, False, f"special file: {path}")
    return _check(label, True, f"{len(entries)} entries, all root-owned and not group/other writable")


def _private_dir(system: System, path: str, uid: int, label: str) -> dict:
    info = system.lstat(path)
    ok = (isinstance(path, str) and _mac._PATH.fullmatch(path) is not None and info is not None
          and stat.S_ISDIR(info.st_mode) and info.st_uid == uid and not info.st_mode & 0o077
          and system.realpath(path) == path)
    return _check(label, ok, "owned by the account, mode 0700-or-tighter, no symlink" if ok
                  else "missing, symlinked, not owned by the account or accessible to others")


def _disjoint(paths: Mapping[str, str]) -> dict:
    items = sorted(paths.items())
    for i, (name, a) in enumerate(items):
        for other, b in items[i + 1:]:
            if _mac._under(a, b) or _mac._under(b, a):
                return _check("paths-disjoint", False, f"{name} and {other} overlap")
    return _check("paths-disjoint", True, "config, run, arena and output directories do not overlap")


def default_out_dir(attempt: str) -> str:
    return str(ROOT / EVIDENCE_PARENT / attempt)


def preflight(args: argparse.Namespace, system: System) -> dict:
    """Every check, none skipped after a failure. Starts nothing native; reads the host only."""
    checks: list[dict] = []
    add = checks.append
    observed: dict = {}
    add(_check("platform-darwin", system.darwin(), "macOS required"))
    add(_check("attempt-name", _ATTEMPT.fullmatch(args.attempt or "") is not None,
               "lowercase letters, digits and hyphens, 3 to 48 characters"))
    present = sorted(name for name in system.environ() if name in ENV_DENY)
    add(_check("environment-deny-variables", not present,
               "none present" if not present else f"present: {', '.join(present)}"))

    # who runs this: the dedicated, standard, non-console account
    uid, euid = system.ids()
    entry = system.passwd_by_uid(uid)
    home = getattr(entry, "pw_dir", None)
    add(_check("user-is-dedicated-account", entry is not None and entry.pw_name == args.account
               and uid == euid and uid != 0,
               f"running as {getattr(entry, 'pw_name', 'unknown')!r}, expected {args.account!r}, uid==euid, not root"))
    try:
        console = system.console_uid()
    except OSError:
        console = None
    add(_check("user-is-not-console-user", console is not None and uid != console,
               "the account is not the console user" if console is not None and uid != console
               else "the account owns /dev/console (or it is unreadable); the backend refuses this (RV-16)"))
    try:
        gids = system.groups(args.account, entry.pw_gid) if entry is not None else ()
    except OSError:
        gids = ()
    add(_check("user-is-standard", entry is not None and not PRIVILEGED_GIDS & {entry.pw_gid, *gids},
               "not in admin or wheel" if entry is not None and not PRIVILEGED_GIDS & {entry.pw_gid, *gids}
               else "member of admin or wheel, or groups unreadable"))
    if entry is not None and home:
        add(_private_dir(system, home, uid, "account-home-private"))
    else:
        add(_check("account-home-private", False, "account or home unknown"))
    console_entry = system.passwd_by_uid(console) if console is not None else None
    console_home = getattr(console_entry, "pw_dir", None)
    add(_check("founder-home-unreadable", bool(console_home) and console_home != home
               and not system.can_traverse(console_home),
               "the account cannot read or traverse the console user's home"
               if console_home and console_home != home and not system.can_traverse(console_home)
               else "the account can read the console user's home, or it is unknown (chmod 700 it)"))
    if home:
        add(_check("config-dir-not-home", args.config_dir != home, "config_dir is not the home directory"))

    # OS support, as the backend sees it
    try:
        facts = system.host_facts()
        observed["os"] = {"product": facts.product, "build": facts.build, "arch": facts.arch}
        os_ok = (_mac._OS_SERIES.fullmatch(facts.product) is not None
                 and _mac._BUILD.fullmatch(facts.build) is not None)
        add(_check("os-supported", os_ok, f"macOS {facts.product} ({facts.build}); NC-3 allows 27.0.x only"))
    except LabError as exc:
        facts = None
        add(_check("os-supported", False, f"cannot read the OS facts: {exc.reason}"))

    # pinned executables and code: root-owned installs (RV-22)
    for label, path, expected in (("claude", args.claude, args.claude_sha256),
                                  ("interpreter", args.interpreter, args.interpreter_sha256)):
        checks.extend(_trusted_install(system, path, expected, label))
        observed[f"{label}Sha256"] = system.sha256(path) if system.lstat(path) is not None else None
    info = system.lstat(_mac.SANDBOX_EXEC)
    add(_check("sandbox-exec-root-owned", _root_owned(info, kind=stat.S_ISREG), _mac.SANDBOX_EXEC))
    observed["sandboxExecSha256"] = system.sha256(_mac.SANDBOX_EXEC) if info is not None else None
    ok = args.sandbox_exec_sha256 is not None and observed["sandboxExecSha256"] == args.sandbox_exec_sha256
    add(_check("sandbox-exec-sha256", ok, "matches the pin" if ok else
               f"pin missing or differs; observed {observed['sandboxExecSha256']}"))
    add(_check("interpreter-under-root", _mac._under(args.interpreter, args.interpreter_root),
               "interpreter lives under interpreter_root"))
    add(_root_owned_tree(system, args.interpreter_root, "interpreter-root-tree-root-owned"))
    add(_root_owned_tree(system, str(ROOT), "repository-code-root-owned"))

    # the account's writable areas
    add(_private_dir(system, args.run_root, uid, "run-root"))
    listing = system.listdir(args.run_root)
    stale = [n for n in listing or [] if n.startswith(_mac._OWNED)]
    add(_check("run-root-no-leftovers", listing is not None and not stale,
               "no run-/compile- leftovers" if not stale else f"leftovers: {', '.join(stale[:3])}"))
    add(_private_dir(system, args.arena_parent, uid, "arena-parent"))
    add(_private_dir(system, args.config_dir, uid, "config-dir"))
    tree = system.walk(args.config_dir, CONFIG_MAX_ENTRIES + 1)
    if tree is None:
        add(_check("config-dir-small", False, f"more than {CONFIG_MAX_ENTRIES} entries (MDRV-03)"))
    else:
        size = sum(i.st_size for _, i in tree if stat.S_ISREG(i.st_mode))
        odd = [p for p, i in tree if not (stat.S_ISREG(i.st_mode) or stat.S_ISDIR(i.st_mode))]
        observed["configDir"] = {"entries": len(tree), "bytes": size}
        add(_check("config-dir-small", size <= CONFIG_MAX_BYTES and not odd,
                   f"{len(tree)} entries, {size} bytes" if not odd and size <= CONFIG_MAX_BYTES
                   else f"{size} bytes or special/symlink entries ({len(odd)}); a fresh login holds a few files (MDRV-03)"))
    out_dir = args.out_dir or default_out_dir(args.attempt or "attempt")
    parent = os.path.dirname(out_dir)
    add(_check("out-dir", system.lstat(out_dir) is None and system.writable(parent),
               "does not exist and its parent is writable by the account" if system.lstat(out_dir) is None
               and system.writable(parent) else "exists, or its parent is not writable (pass --out-dir inside the account's home)"))
    add(_disjoint({"config_dir": args.config_dir, "run_root": args.run_root,
                   "arena_parent": args.arena_parent, "out_dir": out_dir}))

    # the policy and the environment hash, built exactly as the backend will
    policy = None
    try:
        policy = _build_policy(args)
        add(_check("policy-valid", True, "ContainmentPolicy accepted"))
    except (LabError, TypeError, ValueError) as exc:
        add(_check("policy-valid", False, f"refused: {getattr(exc, 'reason', exc)}"))
    if policy is not None and facts is not None and entry is not None:
        try:
            account_facts = system.account_facts(args.account, entry, uid)
            observed["environmentSha256"] = _mac.environment_sha256(policy, facts, uid, account_facts)
            add(_check("environment-hash", True, "computed"))
        except LabError as exc:
            add(_check("environment-hash", False, f"backend account check refused: {exc.reason}"))
    ready = all(c["ok"] for c in checks)
    return {"verdict": "ready" if ready else "refused", "attempt": args.attempt, "checks": checks,
            "failed": [c["check"] for c in checks if not c["ok"]], "observed": observed,
            "probeCatalogSha256": _probes.CATALOG_SHA256, "nativeRun": False, "dryRun": bool(args.dry_run),
            "executionAuthorization": False}


def _build_policy(args: argparse.Namespace) -> _mac.ContainmentPolicy:
    return _mac.ContainmentPolicy(
        account=args.account, run_root=args.run_root, config_dir=args.config_dir, claude=args.claude,
        claude_sha256=args.claude_sha256 or "", claude_version=_mac.CLAUDE_VERSION,
        interpreter=args.interpreter, interpreter_sha256=args.interpreter_sha256 or "",
        interpreter_root=args.interpreter_root, sandbox_exec_sha256=args.sandbox_exec_sha256 or "",
        proxy_port=args.proxy_port)


# --- NC-6 with the operator as reader ----------------------------------------------------------------


class UsageCardReader:
    """Asks the operator for the Claude Desktop usage card; returns a ``harness_quota`` reading or ``None``.

    ``None`` (missing, malformed, future-dated or older than five minutes) is a refusal the quota module
    turns into a stop. The start (< 90 %), weekly, extra-usage and 2 % rules are applied there, on the
    returned values; this class only validates the form and the freshness.
    """

    def __init__(self, ask: Callable[[str], str], say: Callable[[str], None],
                 now: Callable[[], datetime], local_tz: timezone | None = None):
        self._ask, self._say, self._now, self._tz = ask, say, now, local_tz

    def _percent(self, label: str) -> int | None:
        raw = self._ask(f"  {label} (0-100, as shown on the card): ").strip().rstrip("%").strip()
        return int(raw) if raw.isdigit() and 0 <= int(raw) <= 100 else None

    def read(self, role: str) -> dict | None:
        self._say(f"\n[NC-6] Read the Claude Desktop usage card now, {role} this session.")
        try:
            five_hour = self._percent("5-hour window used")
            weekly = self._percent("Weekly used")
            extra = self._ask("  Extra usage enabled? (y/n): ").strip().lower()
            stamp = self._ask("  Time you read the card (HH:MM 24h local, or 'now'): ").strip().lower()
        except EOFError:
            self._say("[NC-6] no input: reading refused")
            return None
        now = self._now().astimezone(timezone.utc)
        observed = self._observed(stamp, now)
        if five_hour is None or weekly is None or extra not in ("y", "n") or observed is None:
            self._say("[NC-6] reading missing or malformed: refused")
            return None
        if observed > now:
            self._say("[NC-6] reading time is in the future: refused")
            return None
        if now - observed > FRESHNESS:
            self._say("[NC-6] reading is older than 5 minutes: refused (read the card again)")
            return None
        return {"source": SOURCE, "observedAt": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fiveHourPercent": five_hour, "weeklyPercent": weekly, "extraUsageEnabled": extra == "y"}

    def _observed(self, stamp: str, now: datetime) -> datetime | None:
        if stamp == "now":
            return now.replace(microsecond=0)
        match = _CLOCK_TIME.fullmatch(stamp)
        if match is None:
            return None
        local_now = now.astimezone(self._tz)
        candidate = local_now.replace(hour=int(match[1]), minute=int(match[2]), second=0, microsecond=0)
        if candidate > local_now + timedelta(minutes=1):  # just after midnight: the reading was yesterday
            candidate -= timedelta(days=1)
        return candidate.astimezone(timezone.utc)


class SessionQuota:
    """The pre reading is taken when the transport is built and handed to the session driver once.

    The session driver builds a transport, then asks for the pre reading, runs, then asks for the post
    reading. One prompt serves both the admission gate and the driver's pre reading.
    """

    def __init__(self, reader: UsageCardReader, say: Callable[[str], None]):
        self._reader, self._say = reader, say
        self.started = 0
        self.stopped: str | None = None
        self._pending: tuple[bool, dict | None] = (False, None)
        self._pre: dict | None = None

    def next_pre(self) -> dict | None:
        if self.stopped:
            raise RuntimeError(self.stopped)
        self.started += 1
        self._pre = self._reader.read(f"BEFORE session {self.started} of 3")
        self._pending = (True, self._pre)
        return self._pre

    def read(self) -> dict | None:
        has_pending, pre = self._pending
        if has_pending:
            self._pending = (False, None)
            return pre
        post = self._reader.read(f"AFTER session {self.started} of 3")
        used = self._used(self._pre, post)
        if used is not None and used > PROBE_MAX_FIVE_HOUR:
            self._say(f"[NC-6] the session used {used} points of the 5-hour window (NC-10 allows {PROBE_MAX_FIVE_HOUR}): attempt stops")
        if used is not None and used > FIVE_HOUR_STOP_SESSION:
            self.stopped = "quota-hard-stop"
        return post

    @staticmethod
    def _used(pre: dict | None, post: dict | None) -> int | None:
        if pre is None or post is None:
            return None
        return post["fiveHourPercent"] - pre["fiveHourPercent"]


# --- the attempt ---------------------------------------------------------------------------------------


def attempt_records(environment_sha256: str, now: int) -> dict:
    """In-memory records the backend constructor needs. Never written, never issuable (T010 is the founder's)."""
    expires = now + ATTEMPT_RECORD_SECONDS
    lab = canonical({"format": LAB_FORMAT, "backend": _mac.BACKEND, "kind": "native",
                     "environmentSha256": environment_sha256, "enforced": list(ENFORCED_EFFECTS),
                     "expiresAt": expires, "evidenceSha256": "0" * 64})
    host = canonical({"format": HOST_FORMAT, "host": "claude", "environmentSha256": environment_sha256,
                      "enforced": list(ENFORCED_EFFECTS), "expiresAt": expires, "evidenceSha256": "0" * 64})
    return dict(qualification=lab, qualification_sha256=sha256(lab).hexdigest(),
                host_qualification=host, host_qualification_sha256=sha256(host).hexdigest())


def run_attempt(args: argparse.Namespace, system: System, *, ask: Callable[[str], str] = input,
                say: Callable[[str], None] = print, now: Callable[[], datetime] | None = None,
                backend_factory=_mac.MacOSContainment) -> dict:
    """Pre-flight, confirm, build, run the catalog, write the bundle. Raises ``AttemptRefused`` before any
    native step when a check fails."""
    clock = now or (lambda: datetime.now(timezone.utc))
    report = preflight(args, system)
    if report["verdict"] != "ready":
        raise AttemptRefused(report["failed"])
    if not args.founder_go:
        raise AttemptRefused(["founder-go-flag-missing"])
    say(f"T009 attempt {args.attempt}: at most 3 small Haiku sessions, quota read by you before and after each.")
    if ask(f"Type the attempt name ({args.attempt}) to start, anything else cancels: ").strip() != args.attempt:
        raise AttemptRefused(["operator-cancelled"])
    out_dir = args.out_dir or default_out_dir(args.attempt)
    policy = _build_policy(args)
    environment_sha = report["observed"]["environmentSha256"]
    facts = report["observed"]["os"]
    reader = UsageCardReader(ask, say, clock, datetime.now().astimezone().tzinfo)
    quota = SessionQuota(reader, say)
    work_dirs: list[str] = []

    def workdir() -> Path:
        path = tempfile.mkdtemp(prefix="work-", dir=args.run_root)
        work_dirs.append(path)
        return Path(path)

    probe_runner = _probes.make_f4_probe_runner(arena_parent=args.arena_parent, workdir_factory=workdir)
    backend = backend_factory(policy, probe_runner=probe_runner, clock=time.time,
                              **attempt_records(environment_sha, int(time.time())))

    def transport_factory() -> NativeClaudeTransport:
        pre = quota.next_pre()
        return NativeClaudeTransport(backend, workdir=workdir(), pre_reading=pre,
                                     quota=("probe", quota.started - 1), clock=clock)

    try:
        runner = _probes.make_qualification_runner(
            backend, arena_parent=args.arena_parent, workdir_factory=workdir,
            transport_factory=transport_factory, read_quota=quota.read)
        environment = {
            "environmentSha256": environment_sha, "probeCatalogSha256": _probes.CATALOG_SHA256,
            "backend": _mac.BACKEND, "osProduct": facts["product"], "osBuild": facts["build"],
            "arch": facts["arch"], "claudeVersion": policy.claude_version, "claudeSha256": policy.claude_sha256,
            "sandboxExecSha256": policy.sandbox_exec_sha256,
            "profileSha256": sha256(policy.render("launch")).hexdigest()}
        summary = runner.run(out_dir, environment=environment)
        bundle_sha = _probes.verify_bundle(out_dir)
    finally:
        backend.close()
        for path in work_dirs:
            _mac._remove_tree(path)
    return {"verdict": "bundle-written", "outDir": out_dir, "bundleSha256": bundle_sha,
            "sessionsStarted": quota.started, "summary": summary, "executionAuthorization": False}


# --- command line -------------------------------------------------------------------------------------------


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--attempt", required=True, help="attempt label, e.g. t009-20261104")
    p.add_argument("--account", default=DEFAULT_ACCOUNT)
    p.add_argument("--claude", required=True, help="pinned root-owned claude, absolute path")
    p.add_argument("--claude-sha256")
    p.add_argument("--interpreter", required=True)
    p.add_argument("--interpreter-sha256")
    p.add_argument("--interpreter-root", required=True)
    p.add_argument("--sandbox-exec-sha256")
    p.add_argument("--config-dir", required=True)
    p.add_argument("--run-root", required=True)
    p.add_argument("--arena-parent", required=True)
    p.add_argument("--out-dir", help=f"default: <repo>/{EVIDENCE_PARENT}/<attempt>")
    p.add_argument("--proxy-port", type=int, default=DEFAULT_PROXY_PORT)
    p.add_argument("--dry-run", action="store_true", help="pre-flight only; nothing native runs")
    p.add_argument("--founder-go", action="store_true",
                   help="required for the real attempt, after the orchestrator confirmed the dry run")
    return p


def main(argv: list[str] | None = None, *, system: System | None = None) -> int:
    args = parser().parse_args(argv)
    system = system or System()
    if args.dry_run:
        report = preflight(args, system)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["verdict"] == "ready" else 2
    try:
        result = run_attempt(args, system)
    except AttemptRefused as exc:
        print(json.dumps({"verdict": "refused", "reasons": exc.reasons, "nativeRun": False,
                          "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"bundleSha256 {result['bundleSha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
