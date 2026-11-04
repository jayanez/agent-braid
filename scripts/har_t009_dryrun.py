#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 runbook steps 9 and 10, run inside the dedicated account's own login session.

This script is NOT an authorization and it is NOT step 11. It does what the runbook says for step 9 (the
environment check, the login of the account's own ``CLAUDE_CONFIG_DIR``) and step 10 (the driver
``--dry-run``, pre-flight only: no sandbox, no ``claude``, no network), and saves the verdict to
``~/t009/dry-run.json`` and ``/Users/Shared/t009-dry-run.json``. It never passes ``--self-check`` or
``--founder-go``: the self-check (10b) and the real attempt (11, with the NC-6 quota readings you type) stay
manual, after the orchestrator confirms the dry run.

Run it with the pinned interpreter from the root-owned code copy, after the orchestrator confirmed the
setup summary (it reads the pins from ``/Users/Shared/t009-setup-summary.json`` and re-hashes the files)::

    B=/usr/local/libexec/braid
    $B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t009_dryrun.py \\
        --commit <40-hex> --operator-account <your daily account> --attempt t009-<YYYYMMDD>

``--skip-login`` skips the ``claude auth login`` of step 9 (already logged in); ``--dry-run`` prints the
commands without running them. Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Sequence

BRAID = "/usr/local/libexec/braid"
CLAUDE = f"{BRAID}/claude-2.1.292"
PY_ROOT = f"{BRAID}/python312"
PYTHON = f"{PY_ROOT}/bin/python3.12"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
DEFAULT_SUMMARY = "/Users/Shared/t009-setup-summary.json"
SHARED_COPY = "/Users/Shared/t009-dry-run.json"
SUMMARY_VERSION = "har-t009-setup-v1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
ACCOUNT_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
ATTEMPT_RE = re.compile(r"t009-[0-9]{8}[a-z0-9-]{0,16}")
ENV_RE = re.compile(r"ANTHROPIC|CLAUDE", re.IGNORECASE)
BIG_FILE = 1024 * 1024  # "a few small files (a fresh login), nothing big"


class Stop(Exception):
    """A runbook check failed; the message is the runbook's STOP text."""


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pins(args: argparse.Namespace) -> dict[str, str]:
    """Pins from the setup summary, each overridable by an explicit flag; every one must be 64 hex."""
    pins: dict[str, str] = {}
    summary_path = Path(args.summary)
    if summary_path.is_file():
        try:
            data = json.loads(summary_path.read_text())
            pins = dict(data.get("pins") or {})
        except (OSError, ValueError, AttributeError, TypeError) as exc:
            raise Stop("STOP: the setup summary cannot be read") from exc
        if data.get("summaryVersion") != SUMMARY_VERSION:
            raise Stop("STOP: the setup summary is not a har-t009-setup-v1 file")
        if data.get("commit") != args.commit:
            raise Stop("STOP: COMMIT is not the commit the setup summary was made for")
    for key, value in (("claudeSha256", args.claude_sha256), ("interpreterSha256", args.python_sha256),
                       ("sandboxExecSha256", args.sandbox_exec_sha256)):
        if value:
            pins[key] = value
    for key in ("claudeSha256", "interpreterSha256", "sandboxExecSha256"):
        if not HASH_RE.fullmatch(str(pins.get(key, ""))):
            raise Stop("STOP: a hash is not pasted correctly (no setup summary, or a pin is missing)")
    return pins


def run(args: argparse.Namespace, dry: bool, env: dict[str, str]) -> int:
    for label, value, pattern, message in (
            ("COMMIT", args.commit, COMMIT_RE, "STOP: COMMIT is not a 40-character hash"),
            ("OPERATOR_ACCOUNT", args.operator_account, ACCOUNT_RE, "STOP: OPERATOR_ACCOUNT is not an account name"),
            ("ATTEMPT", args.attempt, ATTEMPT_RE, "STOP: ATTEMPT is not an attempt label")):
        if not pattern.fullmatch(value):
            raise Stop(message)
    home = os.path.expanduser("~")
    short = args.commit[:7]
    config, t009 = f"{home}/t009/config", f"{home}/t009"
    driver = f"{BRAID}/repo-{short}/scripts/har_t009_attempt.py"
    try:
        pins = load_pins(args)
    except Stop:
        if not dry:
            raise
        pins = {k: f"<{k} from the setup summary>" for k in ("claudeSha256", "interpreterSha256", "sandboxExecSha256")}
    out_json = f"{t009}/dry-run.json"
    driver_args = ["--attempt", args.attempt, "--operator-account", args.operator_account,
                   "--claude", CLAUDE, "--claude-sha256", pins["claudeSha256"],
                   "--interpreter", PYTHON, "--interpreter-sha256", pins["interpreterSha256"],
                   "--interpreter-root", PY_ROOT, "--sandbox-exec-sha256", pins["sandboxExecSha256"],
                   "--config-dir", config, "--run-root", f"{t009}/run", "--arena-parent", f"{t009}/arena",
                   "--out-dir", f"{t009}/out/{args.attempt}"]
    driver_cmd = [PYTHON, "-B", "-I", driver, *driver_args, "--dry-run"]

    print("== Step 9. Environment, then login (the first native run, outside the sandbox on purpose)")
    leaked = sorted(name for name, value in env.items() if ENV_RE.search(f"{name}={value}"))
    if dry:
        print("   # check: no ANTHROPIC/CLAUDE variable in the environment; otherwise STOP")
        print("+ CLAUDE_CONFIG_DIR=" + shlex.quote(config) + " DISABLE_AUTOUPDATER=1 "
              + shlex.quote(CLAUDE) + " auth login" + ("    # skipped with --skip-login" if args.skip_login else ""))
        print(f"   # check: {config} holds a few small files after the login; otherwise STOP")
        print("\n== Step 10. Dry run (pre-flight only)")
        print("+ " + " ".join(shlex.quote(w) for w in driver_cmd) + f" | tee {out_json}")
        print(f"+ cp {out_json} {SHARED_COPY}")
        return 0
    if leaked:
        raise Stop("STOP: the environment has ANTHROPIC/CLAUDE variables: " + ", ".join(leaked))
    if not os.path.isfile(driver):
        raise Stop(f"STOP: the code copy is missing: {driver}")
    for path, pin in ((CLAUDE, pins["claudeSha256"]), (PYTHON, pins["interpreterSha256"]),
                      (SANDBOX_EXEC, pins["sandboxExecSha256"])):
        if sha256_file(path) != pin:
            raise Stop(f"STOP: {path} does not match its pinned hash")
    session_env = {**env, "CLAUDE_CONFIG_DIR": config, "DISABLE_AUTOUPDATER": "1"}
    if not args.skip_login:
        if subprocess.run([CLAUDE, "auth", "login"], env=session_env, cwd=home).returncode != 0:
            raise Stop("STOP: claude auth login failed")
    names = [p for p in Path(config).glob("**/*") if p.is_file()]
    if not names or any(p.stat().st_size > BIG_FILE for p in names):
        raise Stop("STOP: after the login config_dir must hold a few small files")
    print(f"   {config}: {len(names)} files, largest {max(p.stat().st_size for p in names)} bytes")

    print("\n== Step 10. Dry run (pre-flight only)")
    proc = subprocess.run(driver_cmd, env=session_env, cwd=home, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    try:
        verdict = json.loads(proc.stdout)["verdict"]
    except (ValueError, KeyError, TypeError) as exc:
        raise Stop("STOP: the driver printed no JSON verdict; nothing was saved, tell the orchestrator") from exc
    if proc.returncode not in (0, 2):
        raise Stop(f"STOP: the driver exited {proc.returncode} (verdict {verdict}); nothing was saved")
    try:
        Path(out_json).write_text(proc.stdout)
        if os.path.lexists(SHARED_COPY):
            os.unlink(SHARED_COPY)
        shutil.copyfile(out_json, SHARED_COPY)
    except OSError as exc:
        raise Stop(f"STOP: cannot save the dry run: {exc.strerror}") from exc
    print(f"\nsaved {out_json} and {SHARED_COPY}; tell the orchestrator the file exists. "
          "Check the verdict names your own daily account as operator. Do not continue to step 10b or 11 "
          "until the orchestrator confirms in writing that the verdict is ready.")
    return proc.returncode


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--commit", required=True, help="the same 40-character commit used for the setup")
    p.add_argument("--operator-account", required=True, help="your daily account short name (id -un there)")
    p.add_argument("--attempt", required=True, help="attempt label the orchestrator gave you, t009-YYYYMMDD[...]")
    p.add_argument("--summary", default=DEFAULT_SUMMARY, help="the setup summary that holds the pins")
    p.add_argument("--claude-sha256", help="override the pin from the summary")
    p.add_argument("--python-sha256", help="override the pin from the summary")
    p.add_argument("--sandbox-exec-sha256", help="override the pin from the summary")
    p.add_argument("--skip-login", action="store_true", help="skip claude auth login (already logged in)")
    p.add_argument("--dry-run", action="store_true", help="print the commands; run nothing")
    return p


def main(argv: Sequence[str] | None = None, *, env: dict[str, str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return run(args, args.dry_run, dict(os.environ if env is None else env))
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
