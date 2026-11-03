#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator-run driver for the SPEC-065 T009 live qualification attempt.

This script is NOT an authorization. It is the one command the founder runs, inside the dedicated
account's own login session, after the sudo setup of ``quickstart.md`` and after the orchestrator has
verified that setup with ``--dry-run``. ``--dry-run`` performs only the pre-flight checks: it starts no
sandbox, no ``claude`` and no network connection, and prints a JSON verdict. Without ``--dry-run`` it
builds the T005 backend, the T006 transport factory and the T007 runner (``make_qualification_runner``),
runs the whole catalog (at most three small Haiku sessions, NC-10) and writes the evidence bundle.

``--operator-account`` is required: the founder's own daily account, compared by uid with the account the
driver runs as (RV-16, amended by the founder on 2026-11-03). The owner of ``/dev/console`` is no longer
examined, because fast user switching makes the dedicated account that owner.

Everything fails closed: any failed check refuses the attempt before anything native runs. The driver
issues no qualification record. The backend constructor needs verified records bound to the environment
hash, so the driver builds attempt-scoped ones in memory (``evidenceSha256`` all zeros, short expiry); they
are never written, are not issuable evidence and issuance stays T010 (NC-9, founder only).
``executionAuthorization`` is ``false`` in every output.

NC-6 with the operator as reader (operator-attested: the values are typed, not read by the orchestrator
session): before and after each session the driver asks on the terminal for the usage card (claude.ai
Usage or the phone) (5-hour %, weekly %, extra usage, reading time) and refuses a missing, malformed, future-dated or stale
(> 5 min) reading; ``harness_quota`` applies the < 90 % start rule, the weekly and extra-usage stops and the
NC-10 2 % rule.

A crash, Ctrl-C or write failure after sessions were spent ends in a JSON verdict with the number of sessions
started. The session counter lives in ``--out-dir`` and the next run with the same ``--out-dir`` resumes it,
so a new attempt name never resets the NC-10 budget.
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
from agent_braid.harness_quota import FRESHNESS, PROBE_MAX_FIVE_HOUR, PROBE_MAX_SESSIONS, SOURCE  # noqa: E402
from agent_braid.harness_transport_claude import NativeClaudeTransport  # noqa: E402
from agent_braid.system_one import canonical  # noqa: E402

DEFAULT_ACCOUNT = "braidlab"
DEFAULT_PROXY_PORT = 18080
CONFIG_MAX_ENTRIES = 64  # MDRV-03: a config_dir that is more than a fresh login is refused
CONFIG_MAX_BYTES = 4 << 20
TREE_MAX_ENTRIES = 200_000
ATTEMPT_RECORD_SECONDS = 4 * 3600
READ_TRIES = 3  # each usage-card field is asked at most this many times
COUNTER_FILES = frozenset({_probes.SESSION_COUNT_FILE, _probes.SESSION_COUNT_FILE + ".tmp"})
_ATTEMPT = re.compile(r"[a-z0-9][a-z0-9-]{2,47}\Z")
_PERCENT = re.compile(r"[0-9]{1,3}")
_CLOCK_TIME = re.compile(r"([01]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?")
_GROUP_OTHER_WRITE = stat.S_IWGRP | stat.S_IWOTH


class AttemptRefused(Exception):
    """The attempt must not run; ``reasons`` name the failed checks."""

    def __init__(self, reasons: list[str], details: Mapping[str, str] | None = None):
        super().__init__(", ".join(reasons))
        self.reasons = reasons
        self.details = dict(details or {})


class AttemptFailed(Exception):
    """The attempt started and then failed; sessions may have been spent and are counted."""

    def __init__(self, reason: str, sessions_started: int, out_dir: str):
        super().__init__(reason)
        self.reason, self.sessions_started, self.out_dir = reason, sessions_started, out_dir


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
        """``(path, lstat)`` of every entry below ``path`` (symlinks not followed); ``None`` past ``limit``.

        An unlistable directory or a vanished entry raises ``OSError``: a check must not pass on content
        it could not see.
        """
        def fail(error: OSError) -> None:
            raise error

        found: list[tuple[str, object]] = []
        for base, dirs, files in os.walk(path, followlinks=False, onerror=fail):
            for name in (*dirs, *files):
                full = os.path.join(base, name)
                info = os.lstat(full)
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
        """Search permission alone: a mode-711 home still lets a world-readable file be opened by path."""
        return os.access(path, os.X_OK)

    def other_homes(self, account: str) -> list[str]:
        """Home directories of every local account other than ``account`` (uid >= 500), and the console user's.

        Under fast user switching the console user can be ``account`` itself, which is then left out.
        """
        homes = {entry.pw_dir for entry in pwd.getpwall() if entry.pw_uid >= 500 and entry.pw_name != account}
        try:
            console = pwd.getpwuid(os.stat("/dev/console").st_uid)
            if console.pw_uid != 0 and console.pw_name != account:
                homes.add(console.pw_dir)
        except (KeyError, OSError):
            pass
        return sorted(homes)

    def writable(self, path: str) -> bool:
        return os.access(path, os.W_OK | os.X_OK)

    def environ(self) -> Mapping[str, str]:
        return os.environ

    def host_facts(self):
        return _mac.host_facts()

    def account_facts(self, account: str, entry, uid: int, operator_uid: int):
        return _mac._account_facts(account, entry, uid, operator_uid)  # the backend's own account check

    def supervisor(self) -> str:
        return os.path.realpath(sys.executable)

    def interpreter_flags(self) -> tuple[bool, bool]:
        """``(isolated, dont_write_bytecode)`` of the running interpreter (``-I`` and ``-B``)."""
        return bool(sys.flags.isolated), bool(sys.dont_write_bytecode)


# --- pre-flight ------------------------------------------------------------------------------------


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"check": name, "ok": bool(ok), "detail": detail}


def _root_owned(info, *, kind) -> bool:
    return (info is not None and kind(info.st_mode) and info.st_uid == 0
            and not info.st_mode & _GROUP_OTHER_WRITE)


def _ancestors_root_owned(system: System, path: str, label: str) -> dict:
    """Every ancestor is a root-owned directory nobody else can write: nothing above ``path`` can be swapped."""
    bad = [a for a in _mac._ancestors(path) if not _root_owned(system.lstat(a), kind=stat.S_ISDIR)]
    return _check(f"{label}-ancestors-root-owned", not bad,
                  "all ancestors are root-owned directories" if not bad else f"not root-owned: {bad[0]}")


def _trusted_install(system: System, path: str, expected: str | None, label: str) -> list[dict]:
    """RV-22: a regular file owned by root, not group/other writable, below root-owned directories."""
    shape = (isinstance(path, str) and _mac._PATH.fullmatch(path) is not None
             and os.path.normpath(path) == path)
    if not shape:
        return [_check(f"{label}-path", False, "not a normalized absolute path of plain characters")]
    results = [_ancestors_root_owned(system, path, label)]
    info = system.lstat(path)
    results.append(_check(f"{label}-root-owned-file", _root_owned(info, kind=stat.S_ISREG)
                          and bool(info.st_mode & stat.S_IXUSR),
                          "root-owned regular executable, no group/other write" if info is not None
                          else "missing"))
    observed = system.sha256(path) if info is not None else None
    ok = expected is not None and _mac._HASH.fullmatch(expected) is not None and observed == expected
    results.append(_check(f"{label}-sha256", ok,
                          "matches the pin" if ok else
                          f"pin {'missing or malformed' if not expected or not _mac._HASH.fullmatch(expected) else 'differs'};"
                          f" observed {observed}"))
    return results


def _root_owned_tree(system: System, root: str, label: str) -> dict:
    top = system.lstat(root)
    if top is None or not _root_owned(top, kind=stat.S_ISDIR):
        return _check(label, False, "missing or not a root-owned directory")
    try:
        entries = system.walk(root, TREE_MAX_ENTRIES)
    except OSError as exc:
        return _check(label, False, f"a directory could not be listed: {exc.filename or root}")
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
                  else f"missing, symlinked, not owned by the account or accessible to others (the founder runs: sudo chmod 700 {path})")


def _disjoint(paths: Mapping[str, str]) -> dict:
    items = sorted(paths.items())
    for i, (name, a) in enumerate(items):
        for other, b in items[i + 1:]:
            if _mac._under(a, b) or _mac._under(b, a):
                return _check("paths-disjoint", False, f"{name} and {other} overlap")
    return _check("paths-disjoint", True, "config, run, arena and output directories do not overlap")


def _real_out_dir(system: System, out_dir: str) -> str:
    """The output path with its parent resolved, so a symlinked parent cannot hide an overlap."""
    return os.path.join(system.realpath(os.path.dirname(out_dir)), os.path.basename(out_dir))


def _out_dir_check(system: System, out_dir: str) -> dict:
    """The bundle directory: a normalized absolute path under a real (unlinked) parent, absent or holding only
    the session counter of an unfinished run, which the runner resumes (NC-10 survives a crash)."""
    if not (isinstance(out_dir, str) and _mac._PATH.fullmatch(out_dir) is not None
            and os.path.normpath(out_dir) == out_dir):
        return _check("out-dir", False, "not a normalized absolute path of plain characters")
    parent = os.path.dirname(out_dir)
    if system.realpath(parent) != parent:
        return _check("out-dir", False, "its parent is a symlink or lies below one")
    info = system.lstat(out_dir)
    if info is None:
        ok = system.writable(parent)
        return _check("out-dir", ok, "does not exist and its parent is writable by the account" if ok
                      else "its parent is not writable by the account (use a directory inside its home)")
    listing = system.listdir(out_dir)
    ok = (stat.S_ISDIR(info.st_mode) and not info.st_mode & 0o077 and system.writable(out_dir)
          and listing is not None and set(listing) <= COUNTER_FILES)
    return _check("out-dir", ok, "holds only the session counter of an unfinished run: it is resumed" if ok
                  else "exists and holds more than the session counter, or is not private and writable "
                       "(a finished bundle is never reused: pick a new --out-dir only if no session was spent)")


_OPERATOR_WHY = {
    "operator-account-unresolved": "the operator account is missing, not a valid account name, unknown to this "
                                   "machine or a system account (uid < 500); pass the founder's own account "
                                   "(--operator-account)",
    "invalid-policy": "the operator account is the dedicated account itself; pass the founder's own account "
                      "(--operator-account)",
    "dedicated-user-unsafe": "the account is a system account (uid < 500) or has the operator's uid; the backend "
                             "refuses this (RV-16)",
}


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

    # who runs this: the dedicated, standard account that is neither a system account nor the operator's own
    # (RV-16 amended 2026-11-03: the console owner is not examined; fast user switching makes it this account)
    uid, euid = system.ids()
    entry = system.passwd_by_uid(uid)
    home = getattr(entry, "pw_dir", None)
    add(_check("user-is-dedicated-account", entry is not None and entry.pw_name == args.account
               and uid == euid and uid != 0,
               f"running as {getattr(entry, 'pw_name', 'unknown')!r}, expected {args.account!r}, uid==euid, not root"))
    name = args.operator_account if isinstance(getattr(args, "operator_account", None), str) else ""
    operator = system.passwd_by_name(name) if _mac._ACCOUNT.fullmatch(name) is not None else None
    operator_uid = getattr(operator, "pw_uid", None)
    # the backend owns the rule (RV-16); the driver only words the refusal
    reason = _mac._operator_refusal(args.account, uid, name, operator_uid)
    why = _OPERATOR_WHY.get(reason, "") if reason else ""
    add(_check("user-is-not-operator-account", reason is None,
               why or f"the account is not the operator account {name!r}"))
    operator_ok = reason is None
    try:
        gids = system.groups(args.account, entry.pw_gid) if entry is not None else ()
    except OSError:
        gids = ()
    ok = entry is not None and not _mac._PRIVILEGED_GIDS & {entry.pw_gid, *gids}
    add(_check("user-is-standard", ok, "not in admin or wheel" if ok
               else "member of admin or wheel, or groups unreadable"))
    if entry is not None and home:
        add(_private_dir(system, home, uid, "account-home-private"))
    else:
        add(_check("account-home-private", False, "account or home unknown"))
    operator_home = getattr(operator, "pw_dir", None)
    others = sorted({h for h in (*system.other_homes(args.account), operator_home) if h and h != home})
    open_homes = [h for h in others if system.can_traverse(h)]
    ok = bool(others) and not open_homes
    add(_check("founder-home-unreadable", ok,
               f"the account cannot traverse the other local homes ({len(others)})" if ok
               else f"the account can traverse {open_homes[0]} (chmod 700 it)" if open_homes
               else "no other local account home identified: cannot show the founder's home is closed"))
    if home:
        add(_check("config-dir-not-home", args.config_dir != home, "config_dir is not the home directory"))

    # OS support, as the backend sees it
    try:
        facts = system.host_facts()
        observed["os"] = {"product": facts.product, "build": facts.build, "arch": facts.arch}
        os_ok = (_mac._OS_SERIES.fullmatch(facts.product) is not None
                 and _mac._BUILD.fullmatch(facts.build) is not None)
        add(_check("os-supported", os_ok, f"macOS {facts.product} ({facts.build}); NC-3 allows the 27.x series only"))
    except LabError as exc:
        facts = None
        add(_check("os-supported", False, f"cannot read the OS facts: {exc.reason}"))

    # the supervisor itself: the pinned interpreter, isolated, no bytecode written
    running = system.supervisor()
    ok = system.realpath(args.interpreter) == running
    add(_check("supervisor-is-pinned-interpreter", ok, "the running interpreter is the pinned one" if ok
               else f"running {running}, pinned {args.interpreter}"))
    isolated, no_bytecode = system.interpreter_flags()
    observed["supervisor"] = {"isolated": isolated, "dontWriteBytecode": no_bytecode}
    add(_check("supervisor-isolated-no-bytecode", isolated and no_bytecode,
               "started with -I and -B" if isolated and no_bytecode else "start the driver with python -B -I"))

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
    add(_ancestors_root_owned(system, args.interpreter_root, "interpreter-root"))
    add(_root_owned_tree(system, str(ROOT), "repository-code-root-owned"))
    add(_ancestors_root_owned(system, str(ROOT), "repository-code"))

    # the account's writable areas
    add(_private_dir(system, args.run_root, uid, "run-root"))
    listing = system.listdir(args.run_root)
    stale = [n for n in listing or [] if n.startswith(_mac._OWNED)]
    add(_check("run-root-no-leftovers", listing is not None and not stale,
               "no run-/compile- leftovers" if not stale else f"leftovers: {', '.join(stale[:3])}"))
    add(_private_dir(system, args.arena_parent, uid, "arena-parent"))
    add(_private_dir(system, args.config_dir, uid, "config-dir"))
    try:
        tree = system.walk(args.config_dir, CONFIG_MAX_ENTRIES)
        unreadable = None
    except OSError as exc:
        tree, unreadable = None, exc.filename or args.config_dir
    if unreadable is not None:
        add(_check("config-dir-small", False, f"a directory could not be listed: {unreadable}"))
    elif tree is None:
        add(_check("config-dir-small", False, f"more than {CONFIG_MAX_ENTRIES} entries (MDRV-03)"))
    else:
        size = sum(i.st_size for _, i in tree if stat.S_ISREG(i.st_mode))
        odd = [p for p, i in tree if not (stat.S_ISREG(i.st_mode) or stat.S_ISDIR(i.st_mode))]
        observed["configDir"] = {"entries": len(tree), "bytes": size}
        ok = size <= CONFIG_MAX_BYTES and not odd
        add(_check("config-dir-small", ok, f"{len(tree)} entries, {size} bytes" if ok
                   else f"{size} bytes or special/symlink entries ({len(odd)}); a fresh login holds a few files (MDRV-03)"))
    out_dir = args.out_dir
    add(_out_dir_check(system, out_dir))
    add(_disjoint({"config_dir": system.realpath(args.config_dir), "run_root": system.realpath(args.run_root),
                   "arena_parent": system.realpath(args.arena_parent), "out_dir": _real_out_dir(system, out_dir)}))

    # the policy and the environment hash, built exactly as the backend will
    policy = None
    try:
        policy = _build_policy(args)
        add(_check("policy-valid", True, "ContainmentPolicy accepted"))
    except (LabError, TypeError, ValueError) as exc:
        add(_check("policy-valid", False, f"refused: {getattr(exc, 'reason', exc)}"))
    if policy is not None and facts is not None and entry is not None and operator_ok:
        try:
            account_facts = system.account_facts(args.account, entry, uid, operator_uid)
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
    """Asks the operator for the usage card (claude.ai Usage or the phone).

    Returns a ``harness_quota`` reading or ``None``.

    Each field is asked up to ``READ_TRIES`` times, so a typo does not spend a session or end the attempt.
    ``None`` (missing, still malformed, future-dated or older than five minutes) is a refusal the quota module
    turns into a stop. The start (< 90 %), weekly, extra-usage and 2 % rules are applied there, on the
    returned values; this class only validates the form and the freshness.
    """

    def __init__(self, ask: Callable[[str], str], say: Callable[[str], None],
                 now: Callable[[], datetime], local_tz: timezone | None = None):
        self._ask, self._say, self._now, self._tz = ask, say, now, local_tz

    def _field(self, prompt: str, parse: Callable[[str], object | None]) -> object | None:
        for attempt in range(READ_TRIES):
            value = parse(self._ask(prompt).strip().lower())
            if value is not None:
                return value
            if attempt + 1 < READ_TRIES:
                self._say("  not understood, try again")
        return None

    @staticmethod
    def _percent(raw: str) -> int | None:
        raw = raw.rstrip("%").strip()
        return int(raw) if _PERCENT.fullmatch(raw) and int(raw) <= 100 else None

    @staticmethod
    def _yes_no(raw: str) -> bool | None:
        return {"y": True, "yes": True, "n": False, "no": False}.get(raw)

    def read(self, role: str) -> dict | None:
        self._say(f"\n[NC-6] Read the usage card (5-hour and weekly usage; claude.ai Usage or the phone) now, "
                  f"{role} this session."
                  " The reading must be no older than 5 minutes when you answer.")
        try:
            five_hour = self._field("  5-hour window used (0-100, as shown on the card): ", self._percent)
            weekly = self._field("  Weekly used (0-100): ", self._percent)
            extra = self._field("  Extra usage enabled? (y/n): ", self._yes_no)
            now = self._now().astimezone(timezone.utc)
            observed = self._field("  Time you read the card (HH:MM or HH:MM:SS 24h local, or 'now'): ",
                                   lambda raw: self._observed(raw, now))
        except EOFError:
            self._say("[NC-6] no input: reading refused")
            return None
        if five_hour is None or weekly is None or extra is None or observed is None:
            self._say("[NC-6] reading missing or malformed: refused")
            return None
        if observed > now:
            self._say("[NC-6] reading time is in the future: refused")
            return None
        if now - observed > FRESHNESS:
            self._say("[NC-6] reading is older than 5 minutes: refused (read the card again)")
            return None
        return {"source": SOURCE, "observedAt": observed.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "fiveHourPercent": five_hour, "weeklyPercent": weekly, "extraUsageEnabled": extra}

    def _observed(self, stamp: str, now: datetime) -> datetime | None:
        if stamp == "now":
            return now.replace(microsecond=0)
        match = _CLOCK_TIME.fullmatch(stamp)
        if match is None:
            return None
        local_now = now.astimezone(self._tz)
        candidate = local_now.replace(hour=int(match[1]), minute=int(match[2]), second=int(match[3] or 0),
                                      microsecond=0)
        if candidate > local_now + timedelta(minutes=1):  # just after midnight: the reading was yesterday
            candidate -= timedelta(days=1)
        return candidate.astimezone(timezone.utc)


class SessionQuota:
    """The pre reading is taken when the transport is built and handed to the session driver once.

    The session driver builds a transport, then asks for the pre reading, runs, then asks for the post
    reading. One prompt serves both the admission gate and the driver's pre reading. The stop rules
    (2 points per session, NC-10; stale or missing readings) are the runner's, through ``harness_quota``:
    this class only warns, so the operator sees why the attempt stops.
    """

    def __init__(self, reader: UsageCardReader, say: Callable[[str], None]):
        self._reader, self._say = reader, say
        self.started = 0
        self._pending: tuple[bool, dict | None] = (False, None)
        self._pre: dict | None = None

    def next_pre(self) -> dict | None:
        self.started += 1
        self._pre = self._reader.read(f"BEFORE session {self.started} of {PROBE_MAX_SESSIONS}")
        self._pending = (True, self._pre)
        return self._pre

    def read(self) -> dict | None:
        has_pending, pre = self._pending
        if has_pending:
            self._pending = (False, None)
            return pre
        post = self._reader.read(f"AFTER session {self.started} of {PROBE_MAX_SESSIONS}")
        used = self._used(self._pre, post)
        if used is not None and used > PROBE_MAX_FIVE_HOUR:
            self._say(f"[NC-6] the session used {used} points of the 5-hour window "
                      f"(NC-10 allows {PROBE_MAX_FIVE_HOUR}): attempt stops")
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
        raise AttemptRefused(report["failed"], {c["check"]: c["detail"] for c in report["checks"] if not c["ok"]})
    if not args.founder_go:
        raise AttemptRefused(["founder-go-flag-missing"])
    say(f"T009 attempt {args.attempt}: at most 3 small Haiku sessions, quota read by you before and after each.")
    if ask(f"Type the attempt name ({args.attempt}) to start, anything else cancels: ").strip() != args.attempt:
        raise AttemptRefused(["operator-cancelled"])
    out_dir = args.out_dir
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
                              operator_account=args.operator_account,
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
    except (Exception, KeyboardInterrupt) as exc:
        # sessions may be spent: say how many; the counter in out_dir keeps the NC-10 budget across a re-run
        reason = type(exc).__name__ + (f": {exc.reason}" if isinstance(getattr(exc, "reason", None), str) else "")
        raise AttemptFailed(reason, quota.started, out_dir) from exc
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
    p.add_argument("--operator-account", required=True,
                   help="the founder's own daily account (short name); the lab never runs as it (RV-16)")
    p.add_argument("--claude", required=True, help="pinned root-owned claude, absolute path")
    p.add_argument("--claude-sha256")
    p.add_argument("--interpreter", required=True)
    p.add_argument("--interpreter-sha256")
    p.add_argument("--interpreter-root", required=True)
    p.add_argument("--sandbox-exec-sha256")
    p.add_argument("--config-dir", required=True)
    p.add_argument("--run-root", required=True)
    p.add_argument("--arena-parent", required=True)
    p.add_argument("--out-dir", required=True,
                   help="bundle directory inside the account's home; a run that crashed after spending sessions "
                        "is resumed by passing the same --out-dir")
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
        print(json.dumps({"verdict": "refused", "reasons": exc.reasons, "details": exc.details, "nativeRun": False,
                          "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    except AttemptFailed as exc:
        print(json.dumps({"verdict": "error", "reason": exc.reason, "quota": {"started": exc.sessions_started},
                          "outDir": exc.out_dir, "nativeRun": exc.sessions_started > 0,
                          "next": "keep this output; the session counter in outDir is kept, so re-run with the "
                                  "same --out-dir (a new name would not reset the budget of 3 sessions); tell the "
                                  "orchestrator before trying again",
                          "executionAuthorization": False}, indent=2, sort_keys=True))
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"bundleSha256 {result['bundleSha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
