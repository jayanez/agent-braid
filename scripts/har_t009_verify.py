#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T009 orchestrator verification helper: checks one handoff artifact and writes the approval file.

The orchestrator runs this in the FOUNDER's account (the founder-owned ``<handoff>/to-lab/`` directory is what
makes the approval trustworthy: the lab account can read it but not write it). The lab script
``har_t009_lab.py`` waits for these files and refuses a missing, mismatching, rejected or tampered one. This is
not an authorization (``executionAuthorization`` stays false, issuance stays T010) and it does not run ``claude``,
``sandbox-exec`` or the network; it only reads files and runs ``codesign`` and ``shasum``-equivalent hashing.

Stages (each writes ``to-lab/verify-<stage>.json`` with ``approved`` or ``rejected`` and the failed checks)::

    setup       to-lab/setup-summary.json   the claude copy hash equals the PUBLISHED release checksum you pass,
                                            the installed copy is re-hashed and codesign shows TeamIdentifier
                                            Q6L2SF6YDW and the Anthropic authority, the interpreter and sandbox-exec
                                            pins are re-hashed, the code copy listing is recomputed
    dry-run     from-lab/dry-run.json       verdict ready, no failed check, nativeRun false, executionAuthorization false
    self-check  from-lab/self-check.json    verdict self-check-ok, no session started, executionAuthorization false

The driver's JSON carries no commit field, so the dry run and the self-check are bound to the commit only through the
setup summary and the pinned hashes; read the reports yourself too. The lab account can write from-lab/, so these
checks bind what you saw to a hash, they do not authenticate the lab.

    python3 scripts/har_t009_verify.py setup --commit <40-hex> --attempt <label> --published-claude-sha256 <64-hex>
    python3 scripts/har_t009_verify.py dry-run --commit <40-hex> --attempt <label>
    python3 scripts/har_t009_verify.py self-check --commit <40-hex> --attempt <label>
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Callable, Sequence

BRAID = "/usr/local/libexec/braid"
CLAUDE = f"{BRAID}/claude-2.1.292"
PYTHON = f"{BRAID}/python312/bin/python3.12"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
DEFAULT_HANDOFF = "/Users/Shared/braid-t009"
TEAM_ID = "Q6L2SF6YDW"
AUTHORITY = f"Authority=Developer ID Application: Anthropic PBC ({TEAM_ID})"
LISTING_COMMAND = "find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256"
SUMMARY_VERSION = "har-t009-setup-v1"
VERIFY_VERSION = "har-t009-verify-v1"
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
HASH_RE = re.compile(r"[0-9a-f]{64}")
ATTEMPT_RE = re.compile(r"t009-[0-9]{8}[a-z0-9-]{0,16}")


class Stop(Exception):
    pass


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_regular(path: Path) -> bytes:
    """One plain, non-symlink file read through one descriptor: the lab owns from-lab/ and could swap it."""
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    except OSError as exc:
        raise Stop(f"cannot open {path} as a plain file: {exc.strerror}") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise Stop(f"{path} is not a plain single-link file")
        with os.fdopen(os.dup(fd), "rb") as handle:
            return handle.read()
    finally:
        os.close(fd)


def parse_object(raw: bytes, path: Path) -> dict:
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise Stop(f"cannot read {path} as JSON") from exc
    if not isinstance(data, dict):
        raise Stop(f"{path} is not a JSON object")
    return data


def run_text(cmd: Sequence[str], cwd: str | None = None) -> tuple[int, str]:
    proc = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


def setup_checks(summary: dict, args: argparse.Namespace, run: Callable = run_text,
                 hash_file: Callable[[str], str] = sha256_file) -> list[tuple[str, bool]]:
    pins, claude, code = summary.get("pins") or {}, summary.get("claude") or {}, summary.get("codeCopy") or {}
    published = args.published_claude_sha256
    checks = [
        ("summary is har-t009-setup-v1 for this commit",
         summary.get("summaryVersion") == SUMMARY_VERSION and summary.get("commit") == args.commit),
        ("summary says nothing native ran and no execution authorization",
         summary.get("nativeRun") is False and summary.get("executionAuthorization") is False),
        ("claude sha256 in the summary equals the PUBLISHED release checksum",
         claude.get("sha256") == pins.get("claudeSha256") == claude.get("sourceSha256") == published),
        ("summary names TeamIdentifier " + TEAM_ID, claude.get("teamIdentifier") == TEAM_ID),
    ]
    live: list[tuple[str, Callable[[], bool]]] = [
        ("installed claude re-hashed equals the published checksum", lambda: hash_file(CLAUDE) == published),
        ("installed interpreter re-hashed equals its pin", lambda: hash_file(PYTHON) == pins.get("interpreterSha256")),
        ("sandbox-exec re-hashed equals its pin", lambda: hash_file(SANDBOX_EXEC) == pins.get("sandboxExecSha256")),
        ("codesign --verify --strict --deep passes on the installed claude",
         lambda: run(["codesign", "--verify", "--strict", "--deep", CLAUDE])[0] == 0),
        ("codesign shows TeamIdentifier " + TEAM_ID + " and the Anthropic Developer ID authority",
         lambda: (lambda out: f"TeamIdentifier={TEAM_ID}" in out.splitlines() and AUTHORITY in out.splitlines())(
             run(["codesign", "-dv", "--verbose=2", CLAUDE])[1])),
        ("code copy listing recomputed equals the summary's",
         lambda: hashlib.sha256(run(["sh", "-c", LISTING_COMMAND], cwd=code.get("path", ""))[1].encode()).hexdigest()
         == code.get("listingSha256")),
    ]
    for name, check in live:
        try:
            checks.append((name, bool(check())))
        except (OSError, TypeError):
            checks.append((name, False))
    return checks


def dry_run_checks(report: dict, args: argparse.Namespace) -> list[tuple[str, bool]]:
    return [("verdict is ready with no failed check", report.get("verdict") == "ready" and report.get("failed") == []),
            ("attempt matches", report.get("attempt") == args.attempt),
            ("pre-flight only: nativeRun false, dryRun true", report.get("nativeRun") is False and report.get("dryRun") is True),
            ("executionAuthorization false", report.get("executionAuthorization") is False),
            ("probe catalog hash present", bool(HASH_RE.fullmatch(str(report.get("probeCatalogSha256", "")))))]


def self_check_checks(report: dict, args: argparse.Namespace) -> list[tuple[str, bool]]:
    return [("verdict is self-check-ok", report.get("verdict") == "self-check-ok"),
            ("no session started", report.get("sessionsStarted", 0) == 0),
            ("attempt matches", report.get("attempt") == args.attempt),
            ("executionAuthorization false", report.get("executionAuthorization") is False)]


def verify(args: argparse.Namespace, *, run: Callable = run_text, hash_file: Callable[[str], str] = sha256_file) -> int:
    for value, pattern, message in ((args.commit, COMMIT_RE, "COMMIT is not a 40-character hash"),
                                    (args.attempt, ATTEMPT_RE, "ATTEMPT is not an attempt label")):
        if not pattern.fullmatch(value):
            raise Stop(message)
    handoff = Path(args.handoff)
    subject = handoff / ("to-lab/setup-summary.json" if args.stage == "setup" else f"from-lab/{args.stage}.json")
    raw = read_regular(subject)  # hashed and parsed from the same bytes
    subject_sha = hashlib.sha256(raw).hexdigest()
    data = parse_object(raw, subject)
    if args.stage == "setup":
        if not HASH_RE.fullmatch(args.published_claude_sha256 or ""):
            raise Stop("setup needs --published-claude-sha256 (64 hex, from the independent published checksum)")
        checks = setup_checks(data, args, run, hash_file)
    else:
        words = read_regular(handoff / f"from-lab/{args.stage}.json.sha256").decode(errors="replace").split()
        checks = [("the lab's recorded SHA-256 equals the file's (an accident check, not authentication)",
                   bool(words) and words[0] == subject_sha)]
        checks += dry_run_checks(data, args) if args.stage == "dry-run" else self_check_checks(data, args)
    failed = [name for name, ok in checks if not ok]
    record = {"verificationVersion": VERIFY_VERSION, "stage": args.stage, "commit": args.commit,
              "attempt": args.attempt, "subjectSha256": subject_sha, "verdict": "rejected" if failed else "approved",
              "failed": failed, "checks": [{"check": n, "ok": ok} for n, ok in checks],
              "verifiedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "executionAuthorization": False}
    target = handoff / "to-lab" / f"verify-{args.stage}.json"
    temp = target.with_name(target.name + ".tmp")
    if temp.is_symlink() or temp.exists():
        temp.unlink()
    temp.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    os.chmod(temp, 0o644)
    os.replace(temp, target)
    print(json.dumps({"stage": args.stage, "verdict": record["verdict"], "failed": failed,
                      "subjectSha256": subject_sha, "file": str(target)}, indent=2))
    return 1 if failed else 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("stage", choices=("setup", "dry-run", "self-check"))
    p.add_argument("--commit", required=True)
    p.add_argument("--attempt", required=True)
    p.add_argument("--handoff", default=DEFAULT_HANDOFF)
    p.add_argument("--published-claude-sha256", help="setup only: the independently published release checksum")
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return verify(args)
    except Stop as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
