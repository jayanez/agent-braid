#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Operator setup for SPEC-065 T009: runbook steps 0 to 8, in order, every check a hard stop.

This script is NOT an authorization. It performs only the host preparation of
``specs/065-native-claude-containment/quickstart.md`` "Operator setup for T009" (steps 0 to 8): the
standard account, the root-owned install directory, the pinned ``claude`` copy, the interpreter prefix,
the repository code copy at the stated commit, the closed founder home and the account's private working
directories. It never runs ``claude``, ``sandbox-exec`` or the network (that starts at step 9), and it
never takes the NC-6 quota readings or starts the attempt (step 11).

Run it in your own session, not as root, only after the orchestrator confirmed the re-check is a GO::

    python3 scripts/har_t009_setup.py --commit <40-hex> --dry-run     # prints every command, runs none
    python3 scripts/har_t009_setup.py --commit <40-hex>               # sudo asks for your password once

It calls ``sudo`` itself. The account password stays interactive (``sysadminctl ... -password -``).
Every check of the runbook is enforced: a failed one prints the runbook's ``STOP:`` message and exits 1.
A re-run is safe where the runbook allows it: an existing account is kept (and re-checked), installs
overwrite their previous copy, and the code copy is rebuilt. The empty ``config_dir`` check of step 7 is
kept as written, so a re-run after the step 9 login stops there instead of touching a logged-in account.

The final stdout line block is a machine-readable summary (hashes of the claude copy, the interpreter and
the code copy listing, the codesign TeamIdentifier) that is also written to ``<handoff>/to-lab/setup-summary.json``. Send it to
the orchestrator: it checks the claude hash against an independent source before you continue to step 9.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Callable, Sequence

SUMMARY_VERSION = "har-t009-setup-v1"
DEFAULT_ACCOUNT = "braidlab"
BRAID = "/usr/local/libexec/braid"
CLAUDE_VERSION = "2.1.292"
PYTHON_TAG = "python312"
DEFAULT_CLAUDE_SRC = f"/opt/homebrew/Caskroom/claude-code/{CLAUDE_VERSION}/claude"
DEFAULT_PY_SRC = "~/.local/share/uv/python/cpython-3.12.13-macos-aarch64-none"
DEFAULT_HANDOFF = "/Users/Shared/braid-t009"
SANDBOX_EXEC = "/usr/bin/sandbox-exec"
TEAM_ID = "Q6L2SF6YDW"
AUTHORITY = f"Authority=Developer ID Application: Anthropic PBC ({TEAM_ID})"
DRIVER = "scripts/har_t009_attempt.py"
LISTING_COMMAND = "find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256"
ACCOUNT_RE = re.compile(r"[a-z_][a-z0-9_-]{0,31}")
COMMIT_RE = re.compile(r"[0-9a-f]{40}")
HASH_RE = re.compile(r"[0-9a-f]{64}")


class Stop(Exception):
    """A runbook check failed; the message is the runbook's STOP text."""


class Runner:
    """Runs (or, with ``dry_run``, only prints) the runbook commands; ``_exec`` is the one seam to the host."""

    def __init__(self, dry_run: bool = False, out=None, err=None):
        self.dry_run = dry_run
        self.last_err = ""
        self.out = out or sys.stdout
        self.err = err or sys.stderr

    # -- host seam (replaced by tests) ------------------------------------------------------------------
    def _exec(self, argv: Sequence[str], *, cwd: str | None = None, merge: bool = False,
              interactive: bool = False) -> tuple[int, str]:
        if interactive:  # the terminal stays attached (sudo and sysadminctl prompts)
            return subprocess.run(list(argv), cwd=cwd).returncode, ""
        proc = subprocess.run(list(argv), cwd=cwd, capture_output=True, text=True)
        self.last_err = proc.stderr.strip()[:300]  # shown in the STOP of a failed command
        return proc.returncode, proc.stdout + (proc.stderr if merge else "")

    def _pipe(self, first: Sequence[str], second: Sequence[str]) -> tuple[int, int]:
        left = subprocess.Popen(list(first), stdout=subprocess.PIPE)
        right = subprocess.Popen(list(second), stdin=left.stdout)
        left.stdout.close()
        right_rc = right.wait()
        return left.wait(), right_rc

    # -- output -----------------------------------------------------------------------------------------
    def step(self, title: str) -> None:
        print(f"\n== {title}", file=self.out if self.dry_run else self.err)

    def log(self, text: str) -> None:
        print(f"   {text}", file=self.out if self.dry_run else self.err)

    def _show(self, argv: Sequence[str], sudo: bool, cwd: str | None = None, prefix: str = "") -> str:
        words = (["sudo"] if sudo else []) + list(argv)
        text = prefix + " ".join(shlex.quote(w) for w in words)
        if cwd:
            text += f"    # in {cwd}"
        if self.dry_run:
            print(f"+ {text}", file=self.out)
        return text

    # -- commands ---------------------------------------------------------------------------------------
    def query(self, argv: Sequence[str], *, sudo: bool = False, cwd: str | None = None, merge: bool = False,
              ok: Sequence[int] | None = (0,)) -> str | None:
        """Run and return stdout; ``None`` in a dry run. A return code outside ``ok`` (any if None) is a hard stop."""
        text = self._show(argv, sudo, cwd)
        if self.dry_run:
            return None
        rc, out = self._exec((["sudo"] if sudo else []) + list(argv), cwd=cwd, merge=merge)
        if ok is not None and rc not in ok:
            raise Stop(f"STOP: command failed (exit {rc}): {text}" + (f"\n{self.last_err}" if self.last_err else ""))
        return out

    def do(self, argv: Sequence[str], *, sudo: bool = False, interactive: bool = False) -> None:
        text = self._show(argv, sudo)
        if self.dry_run:
            return
        rc, _ = self._exec((["sudo"] if sudo else []) + list(argv), interactive=interactive)
        if rc != 0:
            raise Stop(f"STOP: command failed (exit {rc}): {text}" + (f"\n{self.last_err}" if self.last_err else ""))

    def probe(self, argv: Sequence[str]) -> bool | None:
        """Return code 0 or not; ``None`` in a dry run (the caller then prints the guarded command)."""
        if self.dry_run:
            return None
        return self._exec(argv)[0] == 0

    def unless(self, test: Sequence[str], argv: Sequence[str], *, sudo: bool = True, interactive: bool = False,
               note: str) -> None:
        """``test ... || sudo argv`` as the runbook writes it: run ``argv`` only when ``test`` fails."""
        if self.dry_run:
            self._show(test, False)
            self._show(argv, sudo, prefix="   (only if the previous test failed: " + note + ")  ")
            return
        if self.probe(test):
            self.log(f"{note}: already done, kept")
            return
        self.do(argv, sudo=sudo, interactive=interactive)

    def pipeline(self, first: Sequence[str], second: Sequence[str]) -> None:
        if self.dry_run:
            self._show(first, False)
            print(f"    | sudo {' '.join(shlex.quote(w) for w in second)}", file=self.out)
            return
        rc_a, rc_b = self._pipe(first, ["sudo", *second])
        if rc_a or rc_b:
            raise Stop(f"STOP: pipeline failed (exit {rc_a}/{rc_b}): {' '.join(first)} | sudo {' '.join(second)}")

    def check(self, what: str, value, predicate: Callable[[str], bool], stop: str) -> None:
        """Enforce one runbook check; in a dry run, only print it."""
        if self.dry_run:
            print(f"   # check: {what}; otherwise {stop}", file=self.out)
            return
        if not predicate(value):
            raise Stop(stop)


def _sha(listing: str) -> dict[str, str]:
    """Parse ``shasum -a 256`` lines into ``{path: hash}``."""
    found = {}
    for line in listing.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and HASH_RE.fullmatch(parts[0]):
            found[parts[1].strip()] = parts[0]
    return found


def _mode_ok(stat_line: str) -> bool:
    """``root wheel <octal>`` with no group or other write bit."""
    parts = stat_line.split()
    return len(parts) == 3 and parts[:2] == ["root", "wheel"] and parts[2].isdigit() and not int(parts[2], 8) & 0o022


def _codesign(r: Runner, path: str) -> str | None:
    r.query(["codesign", "--verify", "--strict", "--deep", path])
    if not r.dry_run:
        r.log(f"signature valid: {path}")
    out = r.query(["codesign", "-dv", "--verbose=2", path], merge=True)
    r.check(f"{path} has TeamIdentifier={TEAM_ID} and the Anthropic Developer ID authority", out,
            lambda o: f"TeamIdentifier={TEAM_ID}" in o.splitlines() and AUTHORITY in o.splitlines(),
            "STOP: the copy is not the Anthropic build")
    return None if out is None else TEAM_ID


def run_setup(r: Runner, *, commit: str, account: str, checkout: str, claude_src: str, py_src: str,
              home: str, handoff: str) -> dict:
    short = commit[:7]
    claude_dst = f"{BRAID}/claude-{CLAUDE_VERSION}"
    py_prefix = f"{BRAID}/{PYTHON_TAG}"
    repo_dst = f"{BRAID}/repo-{short}"
    acct_home = f"/Users/{account}"
    summary: dict = {"summaryVersion": SUMMARY_VERSION, "task": "SPEC-065/T009 operator setup steps 0-8",
                     "commit": commit, "account": account, "braidDir": BRAID}

    r.step("Preflight (not in the runbook: the inputs the steps assume)")
    r.check("running as your own user, not root", str(os.geteuid()) if hasattr(os, "geteuid") else "1",
            lambda e: e != "0", "STOP: run this in your own session, not as root")
    r.check("macOS host", sys.platform, lambda p: p == "darwin", "STOP: this setup is macOS only")
    r.check("account home is not your home", home, lambda h: h != acct_home,
            "STOP: run this as your own account, not as the lab account")
    r.check("lab account is not your own account", os.environ.get("USER", ""), lambda u: u != account,
            "STOP: the lab account must not be your own account")
    r.query(["test", "-f", claude_src])
    r.query(["test", "-x", f"{py_src}/bin/python3.12"])
    r.query(["test", "-d", f"{py_src}/lib/python3.12"])
    r.query(["git", "-C", checkout, "cat-file", "-e", f"{commit}:{DRIVER}"])

    r.step("Step 0. Check the macOS series (NC-3)")
    ver = r.query(["sw_vers", "-productVersion"])
    r.check("macOS version starts with 27.", ver, lambda v: v.strip().startswith("27."),
            "STOP: macOS is not the 27.x series (NC-3)")
    summary["macosVersion"] = None if ver is None else ver.strip()
    r.do(["-v"], sudo=True, interactive=True)  # the one sudo password prompt; later sudo calls reuse it

    r.step("Step 1. Create the standard account and close its home")
    r.unless(["id", "-u", account],
             ["sysadminctl", "-addUser", account, "-fullName", "Braid Lab", "-password", "-"],
             interactive=True, note="account exists")
    uid = r.query(["id", "-u", account])
    r.check("the account is a regular user (uid 500 or above)", uid,
            lambda u: u.strip().isdigit() and int(u) >= 500, "STOP: the account is a system account")
    groups = r.query(["id", "-G", account])
    r.check("no group 80 (admin) and no group 0 (wheel)", groups, lambda g: not {"80", "0"} & set(g.split()),
            "STOP: the account is in admin or wheel")
    member = r.query(["dseditgroup", "-o", "checkmember", "-m", account, "admin"], ok=None)
    r.check("dseditgroup says the account is not an admin member", member,
            lambda m: m.strip().lower().startswith("no"), "STOP: the account is an admin member")
    r.unless(["test", "-d", acct_home], ["createhomedir", "-c", "-u", account], note="home exists")
    r.do(["chown", f"{account}:staff", acct_home], sudo=True)
    r.do(["chmod", "700", acct_home], sudo=True)
    st = r.query(["stat", "-f", "%Su %Sg %Lp", acct_home])
    r.check(f"stat prints: {account} staff 700", st, lambda s: s.strip() == f"{account} staff 700",
            f"STOP: the home of {account} is not {account} staff 700")

    r.step("Step 2. Create the root-owned install directory")
    r.do(["install", "-d", "-o", "root", "-g", "wheel", "-m", "755", BRAID], sudo=True)
    for d in ("/usr/local", "/usr/local/libexec", BRAID):
        st = r.query(["stat", "-f", "%Su %Sg %Lp", d])
        r.check(f"{d} is root:wheel with no group/other write", st, _mode_ok,
                f"STOP: {d} is not root:wheel without group/other write")

    r.step("Step 3. Install the pinned claude copy (copy only, nothing runs)")
    r.do(["install", "-o", "root", "-g", "wheel", "-m", "755", claude_src, claude_dst], sudo=True)
    hashes = _sha(r.query(["shasum", "-a", "256", claude_src, claude_dst]) or "")
    r.check("the two claude hashes are identical", hashes,
            lambda h: len(h) == 2 and len(set(h.values())) == 1, "STOP: the claude copy differs from its source")
    st = r.query(["stat", "-f", "%Su %Sg %Sp", claude_dst])
    r.check("the copy is -rwxr-xr-x root wheel", st, lambda s: s.strip() == "root wheel -rwxr-xr-x",
            "STOP: the claude copy is not -rwxr-xr-x root wheel")
    team = _codesign(r, claude_src)
    team_dst = _codesign(r, claude_dst)
    claude_sha = hashes.get(claude_dst)
    summary["claude"] = {"path": claude_dst, "sha256": claude_sha, "sourceSha256": hashes.get(claude_src),
                         "signatureValid": not r.dry_run, "teamIdentifier": team_dst or team,
                         "authority": AUTHORITY.split("=", 1)[1],
                         "note": "orchestrator checks sha256 against the published release checksum before step 9"}

    r.step("Step 4. Install a minimal root-owned interpreter prefix")
    r.do(["install", "-d", "-o", "root", "-g", "wheel", "-m", "755", f"{py_prefix}/bin", f"{py_prefix}/lib"],
         sudo=True)
    r.do(["install", "-o", "root", "-g", "wheel", "-m", "755", f"{py_src}/bin/python3.12",
          f"{py_prefix}/bin/python3.12"], sudo=True)
    r.do(["ditto", f"{py_src}/lib/python3.12", f"{py_prefix}/lib/python3.12"], sudo=True)
    r.do(["find", py_prefix, "-name", "__pycache__", "-prune", "-exec", "rm", "-r", "{}", "+"], sudo=True)
    r.do(["chown", "-R", "root:wheel", py_prefix], sudo=True)
    r.do(["chmod", "-R", "go-w", py_prefix], sudo=True)
    stray = r.query(["find", py_prefix, "-not", "-user", "root"], sudo=True)
    r.check("nothing in the interpreter prefix is owned by another user", stray, lambda s: not s.strip(),
            "STOP: files in the interpreter prefix are not owned by root")
    py_sha = _sha(r.query(["shasum", "-a", "256", f"{py_prefix}/bin/python3.12"]) or "").get(
        f"{py_prefix}/bin/python3.12")
    summary["python"] = {"path": f"{py_prefix}/bin/python3.12", "sha256": py_sha, "root": py_prefix}

    r.step("Step 5. Install a root-owned copy of the repository code at the stated commit")
    r.do(["rm", "-rf", repo_dst], sudo=True)  # re-run: rebuild the copy so nothing stale stays
    r.pipeline(["git", "-C", checkout, "archive", f"--prefix=repo-{short}/", commit],
               ["tar", "-x", "-C", BRAID, "--no-same-owner"])
    r.do(["chown", "-R", "root:wheel", repo_dst], sudo=True)
    r.do(["chmod", "-R", "go-w,a+rX", repo_dst], sudo=True)
    stray = r.query(["find", repo_dst, "-not", "-user", "root"], sudo=True)
    r.check("nothing in the code copy is owned by another user", stray, lambda s: not s.strip(),
            "STOP: files in the code copy are not owned by root")
    r.query(["test", "-f", f"{repo_dst}/{DRIVER}"])
    listing = r.query(["sh", "-c", LISTING_COMMAND], cwd=repo_dst)
    tree = r.query(["git", "-C", checkout, "rev-parse", f"{commit}^{{tree}}"])
    summary["codeCopy"] = {
        "path": repo_dst, "gitTree": None if tree is None else tree.strip(),
        "listingSha256": None if listing is None else hashlib.sha256(listing.encode()).hexdigest(),
        "fileCount": None if listing is None else len(listing.splitlines()),
        "listingCommand": f"cd {repo_dst} && {LISTING_COMMAND}  (then sha256 of that output)"}

    r.step("Step 6. Close your home to the new account")
    mode_before = r.query(["stat", "-f", "%Lp", home])
    r.do(["chmod", "700", home])
    summary["homeModeBefore"] = None if mode_before is None else mode_before.strip()
    summary["homeAlreadyClosedBeforeThisRun"] = None if mode_before is None else mode_before.strip() == "700"

    r.step("Step 7. Create the account's private working directories")
    st = r.query(["stat", "-f", "%Su %Lp", acct_home])
    r.check("step 1 left the home as the account, mode 700", st, lambda s: s.strip() == f"{account} 700",
            "STOP: step 1 (home mode 700) not done")
    for d in ("config", "run", "arena", "out"):
        r.do(["install", "-d", "-o", account, "-g", "staff", "-m", "700", f"{acct_home}/t009/{d}"], sudo=True)
    r.do(["chown", f"{account}:staff", f"{acct_home}/t009"], sudo=True)
    r.do(["chmod", "700", f"{acct_home}/t009"], sudo=True)
    contents = r.query(["ls", "-A", f"{acct_home}/t009/config"], sudo=True)
    r.check("config_dir is empty (a re-run after the step 9 login stops here)", contents,
            lambda c: not c.strip(), "STOP: config_dir is not empty")
    summary["workDirs"] = {d: f"{acct_home}/t009/{d}" for d in ("config", "run", "arena", "out")}

    r.step("Step 8. Record the pins")
    pins = _sha(r.query(["shasum", "-a", "256", claude_dst, f"{py_prefix}/bin/python3.12", SANDBOX_EXEC]) or "")
    r.check("the three pins match what steps 3 and 4 recorded", pins,
            lambda p: p.get(claude_dst) == claude_sha and p.get(f"{py_prefix}/bin/python3.12") == py_sha
            and SANDBOX_EXEC in p, "STOP: a pinned file changed after it was installed")
    summary["pins"] = {"claudeSha256": pins.get(claude_dst), "interpreterSha256": pins.get(f"{py_prefix}/bin/python3.12"),
                       "sandboxExecSha256": pins.get(SANDBOX_EXEC)}
    r.step("Step 8b. Create the handoff directory (not in the runbook; the lab script and the orchestrator use it)")
    to_lab, from_lab = f"{handoff}/to-lab", f"{handoff}/from-lab"
    r.do(["install", "-d", "-m", "755", handoff])
    r.do(["install", "-d", "-m", "755", to_lab])  # yours: the setup summary and the orchestrator's verification files
    r.do(["install", "-d", "-o", account, "-g", "staff", "-m", "750", from_lab], sudo=True)  # the lab writes here
    for path, lab_owned, mode in ((handoff, False, "755"), (to_lab, False, "755"), (from_lab, True, "750")):
        st = r.query(["stat", "-f", "%Su:%Lp", path])
        r.check(f"{path} is {'owned by the lab account' if lab_owned else 'yours'}, mode {mode}", st,
                lambda v, o=lab_owned, m=mode: v.strip().endswith(f":{m}")
                and (v.strip().split(":")[0] == account) == o,
                f"STOP: {path} has the wrong owner or mode (the lab account must not be able to write {to_lab})")
    summary["handoff"] = {"dir": handoff, "toLab": to_lab, "fromLab": from_lab}
    summary.update({"nativeRun": False, "executionAuthorization": False,
                    "next": "send this summary to the orchestrator; do not continue to step 9 until it confirms "
                            "the claude sha256 against the published checksum",
                    "summaryFile": f"{to_lab}/setup-summary.json"})
    return summary


def write_summary(path: str, text: str) -> None:
    """Replace ``path`` with a fresh 0644 file: never follow a planted symlink or reuse a file another user made."""
    try:
        if os.path.lexists(path):
            os.unlink(path)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o644)
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.chmod(path, 0o644)
    except OSError as exc:
        raise Stop(f"STOP: cannot write the summary {path}: {exc.strerror}") from exc


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--commit", required=True, help="full 40-character commit the orchestrator names")
    p.add_argument("--account", default=DEFAULT_ACCOUNT)
    p.add_argument("--checkout", default=str(Path(__file__).resolve().parents[1]),
                   help="your checkout, only used to export the code at --commit (default: this repository)")
    p.add_argument("--claude-src", default=DEFAULT_CLAUDE_SRC)
    p.add_argument("--python-src", default=DEFAULT_PY_SRC)
    p.add_argument("--handoff", default=DEFAULT_HANDOFF,
                   help="shared directory: to-lab/ is yours (summary, verification files), from-lab/ is the lab's")
    p.add_argument("--dry-run", action="store_true", help="print every command and check; run nothing")
    return p


def main(argv: Sequence[str] | None = None, *, runner: Runner | None = None, home: str | None = None) -> int:
    args = parser().parse_args(argv)
    if not COMMIT_RE.fullmatch(args.commit):
        print("STOP: COMMIT is not a 40-character hash", file=sys.stderr)
        return 1
    if not ACCOUNT_RE.fullmatch(args.account):
        print("STOP: the account is not an account name", file=sys.stderr)
        return 1
    r = runner or Runner(dry_run=args.dry_run)
    home = home or os.path.expanduser("~")
    expand = lambda s: s.replace("~", home, 1) if s.startswith("~") else s  # noqa: E731
    try:
        summary = run_setup(r, commit=args.commit, account=args.account, checkout=expand(args.checkout),
                            claude_src=expand(args.claude_src), py_src=expand(args.python_src), home=home,
                            handoff=args.handoff)
        if r.dry_run:
            print("\n(dry run: nothing was run; every check above is enforced in a real run)", file=r.out)
            return 0
        text = json.dumps(summary, indent=2, sort_keys=True)
        write_summary(summary["summaryFile"], text + "\n")
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(text, file=r.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
