#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 runbook steps 9 to 11 as ONE script, run inside the dedicated account's own login session.

This script is NOT an authorization and it does not replace the orchestrator or the founder. It chains the
steps the runbook already has, and it stops (non-zero exit, the runbook's ``STOP:`` text) the moment one fails:

1. reads the setup summary the setup script left in ``<handoff>/to-lab/`` and re-hashes ``claude``, the
   interpreter and ``sandbox-exec`` against its pins;
2. WAITS for the orchestrator's verification of that summary (``verify-setup.json``, bound to the summary's
   SHA-256: the claude copy against the published checksum, the codesign identity) -- runbook "before step 9";
3. step 9: the environment check and ``claude auth login`` (interactive: the login in the browser is yours);
   step 9b (NC-5, amended 2026-11-04): ``claude setup-token`` in this account's session, then the token it
   prints is pasted at a hidden terminal prompt (never into chat) and written, mode 0600, to ``oauth-token`` in
   the account's ``CLAUDE_CONFIG_DIR``. The contained CLI authenticates with that file only (no Keychain);
4. step 10: the driver ``--dry-run``; saves ``from-lab/dry-run.json`` and its SHA-256; WAITS for
   ``verify-dry-run.json``;
5. step 10b: the driver ``--self-check --founder-go``; saves ``from-lab/self-check.json`` and its SHA-256;
   WAITS for ``verify-self-check.json``;
6. step 11: the real attempt, the driver ``--founder-go`` with the terminal attached: the driver itself asks you
   to type the attempt name and, before and after each of at most three sessions, the NC-6 usage readings
   (self-attested, from claude.ai Usage or the phone). Nothing here reads, fakes or skips them; the session
   budget (NC-10) is the driver's. Afterwards the output directory is copied (never moved) to
   ``from-lab/bundle-<attempt>/`` with a SHA-256 listing.

A verification file only counts if it is owned by the operator (not by this account), not group/world
writable, lives in a directory this account cannot write, and carries the expected stage, commit, attempt,
``approved`` verdict and the SHA-256 of the exact subject. A missing file is waited for until ``--wait-timeout``;
a mismatching, rejected or tampered one is a hard stop. ``executionAuthorization`` stays false and issuance stays
T010 (NC-9). This is a guard against skipped stages and accidents, not against a hostile lab account: that
account can run the driver by hand, and the verification only proves the orchestrator saw bytes with that hash.
Run it with the pinned interpreter from the root-owned code copy::

    B=/usr/local/libexec/braid
    $B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t009_lab.py \\
        --commit <40-hex> --operator-account <your daily account> --attempt t009-<YYYYMMDD>

``--plan`` prints the stages and commands without running anything. Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import pwd
import shlex
import shutil
import stat
import subprocess
import sys
import time
from typing import Callable, Sequence

BRAID = "/usr/local/libexec/braid"
CLAUDE = f"{BRAID}/claude-2.1.292"
PY_ROOT = f"{BRAID}/python312"
PYTHON = f"{PY_ROOT}/bin/python3.12"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
DEFAULT_HANDOFF = "/Users/Shared/braid-t009"
SUMMARY_VERSION = "har-t009-setup-v1"
VERIFY_VERSION = "har-t009-verify-v1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
ACCOUNT_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
ATTEMPT_RE = re.compile(r"t009-[0-9]{8}[a-z0-9-]{0,16}")
ENV_RE = re.compile(r"ANTHROPIC|CLAUDE", re.IGNORECASE)
BIG_FILE = 1024 * 1024  # "a few small files (a fresh login), nothing big"
TOKEN_FILE = "oauth-token"  # the same name as harness_containment_macos.TOKEN_FILE (this script is stdlib only)
TOKEN_RE = re.compile(r"[A-Za-z0-9._~+/=-]{20,2048}")  # the same shape the backend accepts
PIN_KEYS = ("claudeSha256", "interpreterSha256", "sandboxExecSha256")


class Stop(Exception):
    """A runbook check failed; the message is the runbook's STOP text."""


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_regular(path: Path) -> tuple[bytes, os.stat_result]:
    """Read one regular, non-symlink, single-link file through one descriptor (no check/use gap)."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise Stop(f"STOP: cannot open {path} as a plain file: {exc.strerror}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise Stop(f"STOP: {path} is not a plain single-link file")
        with os.fdopen(os.dup(fd), "rb") as handle:
            return handle.read(), info
    finally:
        os.close(fd)


def operator_uid(name: str) -> int:
    try:
        return pwd.getpwnam(name).pw_uid
    except KeyError as exc:
        raise Stop(f"STOP: the operator account {name!r} does not exist on this machine") from exc


def load_summary(path: Path, commit: str) -> tuple[dict, str]:
    """Return the parsed summary and the SHA-256 of the very bytes that were parsed."""
    try:
        raw, _ = read_regular(path)
        data = json.loads(raw)
        pins = data["pins"]
        ok = data.get("summaryVersion") == SUMMARY_VERSION and all(HASH_RE.fullmatch(str(pins[k])) for k in PIN_KEYS)
    except (Stop, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Stop(f"STOP: the setup summary {path} is missing or cannot be read (run the setup script first)") from exc
    if not ok:
        raise Stop("STOP: the setup summary is not a har-t009-setup-v1 file with three 64-hex pins")
    if data.get("commit") != commit:
        raise Stop("STOP: COMMIT is not the commit the setup summary was made for")
    return data, hashlib.sha256(raw).hexdigest()


def check_verification(path: Path, to_lab: Path, expect: dict, operator: int) -> bool:
    """True when ``path`` is a valid approval for ``expect``; False when absent; Stop when present but wrong."""
    if not path.exists() and not path.is_symlink():
        return False
    raw, info = read_regular(path)
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except ValueError as exc:
        raise Stop(f"STOP: the verification file {path} cannot be read as JSON") from exc
    if info.st_uid != operator or info.st_uid == os.getuid() or info.st_mode & 0o022:
        raise Stop(f"STOP: {path} is not owned by the operator or is writable by others; it is not trusted")
    folder = os.stat(to_lab)
    if folder.st_uid != operator or folder.st_mode & 0o022 or os.access(to_lab, os.W_OK):
        raise Stop(f"STOP: {to_lab} is not operator-owned, or is writable by this account; verification files there are not trusted")
    for key, value in expect.items():
        if data.get(key) != value:
            raise Stop(f"STOP: {path.name} does not match ({key}): ask the orchestrator to verify again")
    return True


def wait_for_verification(stage: str, subject_sha: str, *, args: argparse.Namespace, sleep: Callable[[float], None],
                          clock: Callable[[], float], say: Callable[[str], None]) -> None:
    to_lab = Path(args.handoff) / "to-lab"
    path = to_lab / f"verify-{stage}.json"
    expect = {"verificationVersion": VERIFY_VERSION, "stage": stage, "commit": args.commit, "attempt": args.attempt,
              "subjectSha256": subject_sha, "verdict": "approved"}
    say(f"\n== Waiting for the orchestrator's verification of {stage}")
    say(f"   subject SHA-256: {subject_sha}")
    say(f"   expected file:   {path}")
    operator = operator_uid(args.operator_account)
    deadline, next_note = clock() + args.wait_timeout, 0.0
    while not check_verification(path, to_lab, expect, operator):
        if clock() >= deadline:
            raise Stop(f"STOP: no valid verification of {stage} within {int(args.wait_timeout)} s; "
                       "tell the orchestrator the subject SHA-256 above and run this script again")
        if clock() >= next_note:
            say("   ...still waiting (the orchestrator verifies the subject, then writes that file)")
            next_note = clock() + 60
        sleep(args.poll)
    say(f"   verified: {path.name}")


def driver_command(args: argparse.Namespace, pins: dict, home: str, *mode: str) -> list[str]:
    t009 = f"{home}/t009"
    short = args.commit[:7]
    return [PYTHON, "-B", "-I", f"{BRAID}/repo-{short}/scripts/har_t009_attempt.py",
            "--attempt", args.attempt, "--operator-account", args.operator_account,
            "--claude", CLAUDE, "--claude-sha256", pins["claudeSha256"],
            "--interpreter", PYTHON, "--interpreter-sha256", pins["interpreterSha256"],
            "--interpreter-root", PY_ROOT, "--sandbox-exec-sha256", pins["sandboxExecSha256"],
            "--config-dir", f"{t009}/config", "--run-root", f"{t009}/run", "--arena-parent", f"{t009}/arena",
            "--out-dir", f"{t009}/out/{args.attempt}", *mode]


def save_output(name: str, text: str, from_lab: Path) -> str:
    """Write ``from-lab/<name>`` and ``<name>.sha256``; return the SHA-256. A differing earlier file is kept as ``<name>.N``."""
    target = from_lab / name
    digest = hashlib.sha256(text.encode()).hexdigest()
    try:
        if target.exists() and sha256_file(str(target)) != digest:
            n = 1
            while (from_lab / f"{name}.{n}").exists():
                n += 1
            target.rename(from_lab / f"{name}.{n}")  # a rerun (resume) differs; the old evidence stays
        target.write_text(text)
        (from_lab / f"{name}.sha256").write_text(f"{digest}  {name}\n")
    except OSError as exc:
        raise Stop(f"STOP: cannot write {target}: {exc.strerror}") from exc
    return digest


def run_driver_capture(cmd: list[str], env: dict[str, str], home: str, name: str, from_lab: Path,
                       accept: dict[str, int], say: Callable[[str], None]) -> str:
    """Run a non-interactive driver mode, save its JSON verdict, and require the verdict ``accept`` names."""
    proc = subprocess.run(cmd, env=env, cwd=home, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    try:
        verdict = json.loads(proc.stdout)["verdict"]
    except (ValueError, KeyError, TypeError) as exc:
        raise Stop(f"STOP: the driver printed no JSON verdict for {name}; nothing was saved, "
                   "tell the orchestrator") from exc
    if proc.returncode not in (0, 2):
        raise Stop(f"STOP: the driver exited {proc.returncode} for {name} (verdict {verdict}); nothing was saved")
    digest = save_output(name, proc.stdout, from_lab)
    say(f"   saved {from_lab / name} (SHA-256 {digest})")
    if verdict != next(iter(accept)) or proc.returncode != accept[verdict]:
        raise Stop(f"STOP: {name} verdict is {verdict}, not {next(iter(accept))}; it was saved, "
                   "send it to the orchestrator")
    return digest


def copy_bundle(out_dir: Path, from_lab: Path, attempt: str, driver_exit: int, say: Callable[[str], None]) -> None:
    base, n = f"bundle-{attempt}", 1
    while (from_lab / (base if n == 1 else f"{base}-{n}")).exists():
        n += 1  # a resumed run leaves a second copy; nothing is overwritten
    label = base if n == 1 else f"{base}-{n}"
    dest = from_lab / label
    try:
        shutil.copytree(out_dir, dest, symlinks=False)  # a copy: the session counter in out_dir stays where it is
        files = {str(p.relative_to(dest)): sha256_file(str(p)) for p in sorted(dest.rglob("*")) if p.is_file()}
        listing = "".join(f"{h}  {name}\n" for name, h in files.items())
        record = {"attempt": attempt, "driverExit": driver_exit, "files": files,
                  "listingSha256": hashlib.sha256(listing.encode()).hexdigest(),
                  "note": "the driver's own printed bundleSha256 is the authoritative bundle hash; this listing is a copy check"}
        (from_lab / f"{label}.sha256.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    except OSError as exc:
        raise Stop(f"STOP: cannot copy the bundle to {dest}: {exc.strerror}; the output directory is untouched") from exc
    say(f"   copied {out_dir} to {dest}: {len(files)} files, listing SHA-256 {record['listingSha256']}")


def store_token(config: Path, prompt: Callable[[str], str], say: Callable[[str], None], *, renew: bool) -> None:
    """Step 9b: save the pasted long-lived token as ``config/oauth-token``, mode 0600, created exclusively.

    The prompt is hidden (``getpass``); the value is never echoed, printed or put in an error message. An
    existing file is kept unless ``renew``."""
    path = config / TOKEN_FILE
    if os.path.lexists(path):
        if not renew:
            say(f"   {path} already exists: kept (--renew-token replaces it)")
            return
    token = prompt("   Paste the token that claude setup-token printed (input hidden; it is written only to "
                   f"{path}): ").strip()
    if not TOKEN_RE.fullmatch(token):
        raise Stop("STOP: what was pasted is not a token (expected one line of letters, digits and . _ ~ + / = -)")
    temporary = config / (TOKEN_FILE + ".new")
    try:  # written beside the target and moved over it: a failure never leaves the old token half replaced
        temporary.unlink(missing_ok=True)
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "w") as handle:
            handle.write(token + "\n")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    except OSError as exc:
        raise Stop(f"STOP: cannot write {path}: {exc.strerror}") from exc
    say(f"   saved {path} (mode 0600)")


def plan(args: argparse.Namespace, pins: dict, home: str) -> None:
    handoff = args.handoff
    show = lambda cmd: print("+ " + " ".join(shlex.quote(w) for w in cmd))  # noqa: E731
    print(f"== read {handoff}/to-lab/setup-summary.json; re-hash claude, interpreter, sandbox-exec against its pins")
    print(f"== WAIT for {handoff}/to-lab/verify-setup.json (bound to the summary's SHA-256)")
    print("== Step 9. environment check (no ANTHROPIC/CLAUDE variable), then login")
    print("+ CLAUDE_CONFIG_DIR=" + shlex.quote(f"{home}/t009/config") + f" DISABLE_AUTOUPDATER=1 {CLAUDE} auth login"
          + ("    # skipped with --skip-login" if args.skip_login else ""))
    print("== Step 9b. the long-lived token (NC-5): claude setup-token, then paste it at the hidden prompt")
    print("+ CLAUDE_CONFIG_DIR=" + shlex.quote(f"{home}/t009/config") + f" {CLAUDE} setup-token"
          + ("    # skipped with --skip-token" if args.skip_token else ""))
    print(f"== write {home}/t009/config/{TOKEN_FILE}, mode 0600 (kept if it exists, unless --renew-token)")
    print("== Step 10. dry run, saved to from-lab/dry-run.json (+ .sha256); WAIT for verify-dry-run.json")
    show(driver_command(args, pins, home, "--dry-run"))
    print("== Step 10b. self-check, saved to from-lab/self-check.json (+ .sha256); WAIT for verify-self-check.json")
    show(driver_command(args, pins, home, "--self-check", "--founder-go"))
    print("== Step 11. the real attempt (the driver asks you to type the attempt name and the NC-6 readings)")
    show(driver_command(args, pins, home, "--founder-go"))
    print(f"== copy {home}/t009/out/{args.attempt} to from-lab/bundle-{args.attempt}/ with a SHA-256 listing")


def run(args: argparse.Namespace, env: dict[str, str], *, sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic, prompt: Callable[[str], str] = getpass.getpass) -> int:
    for value, pattern, message in (
            (args.commit, COMMIT_RE, "STOP: COMMIT is not a 40-character hash"),
            (args.operator_account, ACCOUNT_RE, "STOP: OPERATOR_ACCOUNT is not an account name"),
            (args.attempt, ATTEMPT_RE, "STOP: ATTEMPT is not an attempt label")):
        if not pattern.fullmatch(value):
            raise Stop(message)
    home = os.path.expanduser("~")
    handoff = Path(args.handoff)
    to_lab, from_lab = handoff / "to-lab", handoff / "from-lab"
    say = lambda text: print(text, flush=True)  # noqa: E731
    summary_path = to_lab / "setup-summary.json"
    if args.plan and not summary_path.is_file():
        plan(args, {k: f"<{k} from the setup summary>" for k in PIN_KEYS}, home)
        return 0
    summary, summary_sha = load_summary(summary_path, args.commit)
    pins = summary["pins"]
    if args.plan:
        plan(args, pins, home)
        return 0

    leaked = sorted(name for name, value in env.items() if ENV_RE.search(f"{name}={value}"))
    if leaked:
        raise Stop("STOP: the environment has ANTHROPIC/CLAUDE variables: " + ", ".join(leaked))
    driver = f"{BRAID}/repo-{args.commit[:7]}/scripts/har_t009_attempt.py"
    if not os.path.isfile(driver):
        raise Stop(f"STOP: the code copy is missing: {driver}")
    for path, pin in ((CLAUDE, pins["claudeSha256"]), (PYTHON, pins["interpreterSha256"]),
                      (SANDBOX_EXEC, pins["sandboxExecSha256"])):
        if sha256_file(path) != pin:
            raise Stop(f"STOP: {path} does not match its pinned hash")
    if not from_lab.is_dir() or not os.access(from_lab, os.W_OK):
        raise Stop(f"STOP: {from_lab} is missing or not writable by this account (the setup script creates it)")
    waiting = dict(args=args, sleep=sleep, clock=clock, say=say)
    wait_for_verification("setup", summary_sha, **waiting)

    session_env = {**env, "CLAUDE_CONFIG_DIR": f"{home}/t009/config", "DISABLE_AUTOUPDATER": "1"}
    config = Path(home) / "t009" / "config"
    say("\n== Step 9. Login (the first native run, outside the sandbox on purpose)")
    if not args.skip_login and subprocess.run([CLAUDE, "auth", "login"], env=session_env, cwd=home).returncode != 0:
        raise Stop("STOP: claude auth login failed")
    files = [p for p in config.glob("**/*") if p.is_file()]
    if not files or any(p.stat().st_size > BIG_FILE for p in files):
        raise Stop("STOP: after the login config_dir must hold a few small files")
    say(f"   {config}: {len(files)} files")

    say("\n== Step 9b. Long-lived token for the contained CLI (NC-5): the Keychain stays closed to the sandbox")
    if not args.skip_token:
        if not os.path.lexists(config / TOKEN_FILE) or args.renew_token:
            say("   claude setup-token opens the browser; approve it, then copy the token it prints.")
            say("   Paste it only at the hidden prompt below, never into a chat.")
            if subprocess.run([CLAUDE, "setup-token"], env=session_env, cwd=home).returncode != 0:
                raise Stop("STOP: claude setup-token failed")
        store_token(config, prompt, say, renew=args.renew_token)

    say("\n== Step 10. Dry run (pre-flight only)")
    sha = run_driver_capture(driver_command(args, pins, home, "--dry-run"), session_env, home, "dry-run.json",
                             from_lab, {"ready": 0}, say)
    wait_for_verification("dry-run", sha, **waiting)

    say("\n== Step 10b. Self-check (runs the backend's pre-session check under the sandbox; no session)")
    sha = run_driver_capture(driver_command(args, pins, home, "--self-check", "--founder-go"), session_env, home,
                             "self-check.json", from_lab, {"self-check-ok": 0}, say)
    wait_for_verification("self-check", sha, **waiting)

    out_dir = Path(home) / "t009" / "out" / args.attempt
    if (out_dir / ".sessions.json").exists() and not args.resume:
        raise Stop(f"STOP: {out_dir} already holds a session counter (step 10c): the orchestrator names a new "
                   "attempt label, or pass --resume to continue a crashed run of this label (NC-10)")
    say("\n== Step 11. The real attempt: at most 3 small Haiku sessions (NC-10)")
    say("   The driver now asks you to type the attempt name and, before and after each session, the usage")
    say("   card (claude.ai Usage or the phone): 5-hour %, weekly %, extra usage, and the time (or 'now').")
    code = subprocess.run(driver_command(args, pins, home, "--founder-go"), env=session_env, cwd=home).returncode
    say(f"\n   the driver exited {code}; keep its printed JSON and bundleSha256 line, and send them to the orchestrator")
    if out_dir.is_dir():
        try:
            copy_bundle(out_dir, from_lab, args.attempt, code, say)
        except Stop as exc:
            print(str(exc), file=sys.stderr)  # the driver's exit code is still the result
    return code


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--commit", required=True, help="the same 40-character commit used for the setup")
    p.add_argument("--operator-account", required=True, help="your daily account short name (id -un there)")
    p.add_argument("--attempt", required=True, help="attempt label the orchestrator gave you, t009-YYYYMMDD[...]")
    p.add_argument("--handoff", default=DEFAULT_HANDOFF, help="the shared directory the setup script created")
    p.add_argument("--wait-timeout", type=float, default=7200.0, help="seconds to wait for each verification file")
    p.add_argument("--poll", type=float, default=5.0, help="seconds between looks for a verification file")
    p.add_argument("--skip-login", action="store_true", help="skip claude auth login (already logged in)")
    p.add_argument("--skip-token", action="store_true", help="skip claude setup-token (the token file is in place)")
    p.add_argument("--renew-token", action="store_true", help="make a new token and replace the file")
    p.add_argument("--resume", action="store_true", help="continue a crashed run of the same attempt label (NC-10)")
    p.add_argument("--plan", action="store_true", help="print the stages and commands; run nothing")
    return p


def main(argv: Sequence[str] | None = None, *, env: dict[str, str] | None = None, sleep=time.sleep,
         clock=time.monotonic, prompt: Callable[[str], str] = getpass.getpass) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args, dict(os.environ if env is None else env), sleep=sleep, clock=clock, prompt=prompt)
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
