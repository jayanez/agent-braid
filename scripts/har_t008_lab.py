#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-048/T008 native Claude cohort as ONE command, run inside the dedicated account's own login session.

NOT an authorization and not a verdict: ``executionAuthorization`` stays false and the qualified verdict is the
founder's, decided from the saved evidence. It chains, and stops (``STOP:`` text, exit 1) when a stage fails:

1. checks the root-owned code copy of ``--commit`` (root-owned, not writable by others, no symlinks) and re-hashes
   ``claude``, the interpreter and ``sandbox-exec`` against the pins of the SPEC-065 T009 setup summary (the same
   account, login and token file are reused; nothing is re-created and no token is read);
2. runs ``har_t008_unit.py --dry-run`` from the code copy and saves ``from-lab/t008-dry-run.json`` (+ ``.sha256``);
   it must say ``ready``;
3. runs ``har_t008_unit.py --founder-go`` with the terminal attached (the driver asks for the attempt name and
   the usage card before and after every unit), tees the transcript and saves ``t008-cohort-<attempt>.txt`` and the
   final report ``t008-cohort-<attempt>.json`` (+ ``.sha256``), then copies the driver's output directory to
   ``from-lab/bundle-<attempt>/`` with a SHA-256 listing, whatever happened.

The driver enforces the founder window (2026-11-09T20:30Z to 2026-11-30), at most four serial units, the D2 caps
and the issued-record expiry; this wrapper adds none of that and weakens none of it. Trust basis: the code copy's
root ownership plus the pins of the T009 setup summary the orchestrator verified for T009; no new orchestrator
verification is awaited. No sudo is run here: the code copy for ``--commit`` is installed beforehand by the owner
(see the packet). Standard library only::

    B=/usr/local/libexec/braid
    $B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t008_lab.py \\
        --commit <40-hex> --operator-account <daily account> --attempt t008-<YYYYMMDD>

``--plan`` prints the stages and commands without running anything.
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import subprocess
import sys
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import har_t009_lab as base  # noqa: E402

Stop = base.Stop
MAX_UNITS = 4  # the founder's 2026-11-06 choice; the driver repeats the cap (a test keeps them equal)
ATTEMPT_RE = re.compile(r"t008-[0-9]{8}[a-z0-9-]{0,16}")
REPORT_START = re.compile(r'\{\n  "')  # the driver's report: indent-2 JSON, first key at two spaces
ENV_NAME = base.ENV_RE  # searched against variable NAMES only: a PATH or PWD value may contain ".claude"
TRUSTED_UID = 0  # the code copy and its directories belong to root (the T009 setup script installs them)


def driver_command(args: argparse.Namespace, pins: dict, home: str, *mode: str) -> list[str]:
    t9 = f"{home}/t009"  # the T009 account state (login, token file, run and arena roots) is reused
    short = args.commit[:7]
    return [base.PYTHON, "-B", "-I", "-u", f"{base.BRAID}/repo-{short}/scripts/har_t008_unit.py",
            "--attempt", args.attempt, "--operator-account", args.operator_account,
            "--claude", base.CLAUDE, "--claude-sha256", pins["claudeSha256"],
            "--interpreter", base.PYTHON, "--interpreter-sha256", pins["interpreterSha256"],
            "--interpreter-root", base.PY_ROOT, "--sandbox-exec-sha256", pins["sandboxExecSha256"],
            "--config-dir", f"{t9}/config", "--run-root", f"{t9}/run", "--arena-parent", f"{t9}/arena",
            "--out-dir", f"{home}/t008/out/{args.attempt}", "--units", str(args.units), *mode]


def extract_report(text: str) -> dict:
    """The last JSON object with a ``verdict`` in the transcript, even when it follows a prompt on the same
    line or a traceback follows it."""
    decoder = json.JSONDecoder()
    for match in reversed(list(REPORT_START.finditer(text))):
        try:
            report, _ = decoder.raw_decode(text[match.start():])
        except ValueError:
            continue
        if isinstance(report, dict) and "verdict" in report:
            return report
    raise Stop("STOP: the driver printed no final JSON report; the transcript was saved, tell the orchestrator")


def save_output(name: str, text: str, from_lab: Path) -> str:
    """Like the T009 helper, but O_NOFOLLOW, O_EXCL and mode 0600 (from-lab is shared). A differing earlier file
    is kept as ``<name>.N``."""
    digest = hashlib.sha256(text.encode()).hexdigest()
    target, sidecar = from_lab / name, from_lab / f"{name}.sha256"

    def write(path: Path, content: str) -> None:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)

    try:
        if os.path.lexists(target):
            if target.is_symlink() or not target.is_file():
                raise Stop(f"STOP: {target} is not a regular file")
            if base.sha256_file(str(target)) != digest:
                n = 1
                while os.path.lexists(from_lab / f"{name}.{n}"):
                    n += 1
                target.rename(from_lab / f"{name}.{n}")  # a rerun differs; the old evidence stays
        if not os.path.lexists(target):
            write(target, text)
        sidecar.unlink(missing_ok=True)
        write(sidecar, f"{digest}  {name}\n")
    except OSError as exc:
        raise Stop(f"STOP: cannot write {target}: {exc.strerror}") from exc
    return digest


def run_driver_capture(cmd: list[str], env: dict[str, str], home: str, name: str, from_lab: Path,
                       accept_verdict: str, say: Callable[[str], None]) -> str:
    """A non-interactive driver mode: save its JSON verdict; it must be ``accept_verdict`` with exit 0."""
    proc = subprocess.run(cmd, env=env, cwd=home, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    try:
        verdict = extract_report(proc.stdout)["verdict"]
    except Stop:
        raise Stop(f"STOP: the driver printed no JSON verdict for {name}; nothing was saved, "
                   "tell the orchestrator") from None
    digest = save_output(name, proc.stdout, from_lab)
    say(f"   saved {from_lab / name} (SHA-256 {digest})")
    if verdict != accept_verdict or proc.returncode != 0:
        raise Stop(f"STOP: {name} verdict is {verdict} (exit {proc.returncode}), not {accept_verdict}; "
                   "it was saved, send it to the orchestrator")
    return digest


def drain(proc: subprocess.Popen, decoder, chunks: list[str]) -> bool:
    """Relay the child's output to EOF. Ctrl-C reaches the child as well, so keep draining after the first one
    (its aborted report is evidence); a second one terminates the child. True when interrupted."""
    interrupted = False
    while True:
        try:
            data = proc.stdout.read1(4096)
        except KeyboardInterrupt:
            if interrupted:
                os.killpg(proc.pid, signal.SIGTERM)
            interrupted = True
            continue
        if not data:
            return interrupted
        text = decoder.decode(data)
        sys.stdout.write(text)
        sys.stdout.flush()
        chunks.append(text)


def run_cohort_capture(cmd: list[str], env: dict[str, str], home: str, attempt: str, from_lab: Path,
                       say: Callable[[str], None]) -> int:
    """Run the interactive cohort, relay its output live, always save the transcript, then the final report."""
    chunks: list[str] = []
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    interrupted = False
    # own session: a second Ctrl-C (or any failure) can kill the whole group, grandchildren included
    proc = subprocess.Popen(cmd, env=env, cwd=home, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            start_new_session=True)
    try:
        interrupted = drain(proc, decoder, chunks)
        proc.wait()
    except BaseException:
        interrupted = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
    finally:  # units may have spent quota: the transcript is saved whatever happened
        proc.stdout.close()
        chunks.append(decoder.decode(b"", final=True))
        transcript = "".join(chunks)
        save_output(f"t008-cohort-{attempt}.txt", transcript, from_lab)
    code = proc.returncode
    try:
        report = extract_report(transcript)
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return code or 1
    verdict = report["verdict"]
    name = f"t008-cohort-{attempt}.json"
    digest = save_output(name, json.dumps(report, indent=2, sort_keys=True) + "\n", from_lab)
    say(f"   saved {name} (SHA-256 {digest}): verdict {verdict}, units {report.get('units')}, "
        f"stopped {report.get('stopped')}; send it to the orchestrator")
    consistent = (verdict == "cohort-finished" and report.get("attempt") == attempt
                  and report.get("executionAuthorization") is False and not report.get("stopped") and not interrupted)
    if code == 0 and not consistent:
        return 1  # exit code and report must agree before this looks like success
    return code


def check_code_copy(driver: str) -> None:
    """The code copy runs with this account's token: it and its directories must be root-owned, not writable
    by others and not symlinks."""
    path = Path(driver)
    for item in (path, path.parent, path.parent.parent):
        info = os.lstat(item) if os.path.lexists(item) else None
        if info is None or stat.S_ISLNK(info.st_mode) or info.st_uid != TRUSTED_UID or info.st_mode & 0o022:
            raise Stop(f"STOP: {item} is missing, a symlink, not root-owned or writable by others; "
                       "the code copy is not trusted")


def plan(args: argparse.Namespace, pins: dict, home: str) -> None:
    show = lambda cmd: print("+ " + " ".join(shlex.quote(w) for w in cmd))  # noqa: E731
    print("== The owner installs the root-owned code copy for --commit beforehand (the T009 setup script); no sudo here")
    print("== check the code copy ownership; re-hash claude, interpreter, sandbox-exec against the T009 setup summary pins")
    print("== window: the driver refuses outside 2026-11-09T20:30Z..2026-11-30 and after the issued-record expiry")
    print("== Stage 1. dry run, saved to from-lab/t008-dry-run.json (+ .sha256); must be 'ready'")
    show(driver_command(args, pins, home, "--dry-run"))
    print("== Stage 2. the cohort (the driver asks for the attempt name and the usage card before/after each unit)")
    show(driver_command(args, pins, home, "--founder-go"))
    print(f"== transcript and report saved as from-lab/t008-cohort-{args.attempt}.txt/.json (+ .sha256), "
          f"output directory copied to from-lab/bundle-{args.attempt}/; "
          "the qualified verdict is the founder's, not this script's")


def run(args: argparse.Namespace, env: dict[str, str], *, say: Callable[[str], None] | None = None) -> int:
    say = say or (lambda text: print(text, flush=True))
    for value, pattern, message in (
            (args.commit, base.COMMIT_RE, "STOP: COMMIT is not a 40-character hash"),
            (args.operator_account, base.ACCOUNT_RE, "STOP: OPERATOR_ACCOUNT is not an account name"),
            (args.attempt, ATTEMPT_RE, "STOP: ATTEMPT is not a t008 attempt label")):
        if not pattern.fullmatch(value):
            raise Stop(message)
    if not 1 <= args.units <= MAX_UNITS:
        raise Stop(f"STOP: --units must be 1 to {MAX_UNITS} (more needs a new founder decision)")
    home = os.path.expanduser("~")
    summary_path = Path(args.handoff) / "to-lab" / "setup-summary.json"
    if args.plan and not summary_path.is_file():
        plan(args, {k: f"<{k} from the setup summary>" for k in base.PIN_KEYS}, home)
        return 0
    leaked = sorted(name for name in env if ENV_NAME.search(name))
    if leaked:
        raise Stop("STOP: the environment has ANTHROPIC/CLAUDE variables: " + ", ".join(leaked))
    summary, _ = base.load_summary(summary_path, args.commit)
    pins = summary["pins"]
    if args.plan:
        plan(args, pins, home)
        return 0
    driver = f"{base.BRAID}/repo-{args.commit[:7]}/scripts/har_t008_unit.py"
    if not os.path.isfile(driver):
        raise Stop(f"STOP: the code copy is missing: {driver} (the owner installs it for this commit first)")
    check_code_copy(driver)
    for path, pin in ((base.CLAUDE, pins["claudeSha256"]), (base.PYTHON, pins["interpreterSha256"]),
                      (base.SANDBOX_EXEC, pins["sandboxExecSha256"])):
        if base.sha256_file(path) != pin:
            raise Stop(f"STOP: {path} does not match its pinned hash")
    from_lab = Path(args.handoff) / "from-lab"
    if not from_lab.is_dir() or not os.access(from_lab, os.W_OK):
        raise Stop(f"STOP: {from_lab} is missing or not writable by this account")
    keep = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "TERM")
    session_env = {**{k: v for k, v in env.items() if k in keep},
                   "CLAUDE_CONFIG_DIR": f"{home}/t009/config", "DISABLE_AUTOUPDATER": "1"}

    say("\n== Stage 1. Dry run (pre-flight, issued records, qualified policy, MDRV-04 guard; no quota read)")
    run_driver_capture(driver_command(args, pins, home, "--dry-run"), session_env, home, "t008-dry-run.json",
                       from_lab, "ready", say)
    say("\n== Stage 2. The cohort: one small read-only Haiku session per unit, serial")
    code = 1
    try:
        code = run_cohort_capture(driver_command(args, pins, home, "--founder-go"), session_env, home,
                                  args.attempt, from_lab, say)
    finally:  # whatever happened, the output directory is copied (never moved) with a SHA-256 listing
        out_dir = Path(home) / "t008" / "out" / args.attempt
        if out_dir.is_dir():
            try:
                base.copy_bundle(out_dir, from_lab, args.attempt, code, say)
            except Stop as exc:
                print(str(exc), file=sys.stderr)
    say(f"\n   the driver exited {code}; the qualified verdict is the founder's, decided from the saved evidence")
    return code


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--commit", required=True, help="40-character commit of the root-owned code copy")
    p.add_argument("--operator-account", required=True, help="your daily account short name")
    p.add_argument("--attempt", required=True, help="attempt label, t008-YYYYMMDD[...]")
    p.add_argument("--handoff", default=base.DEFAULT_HANDOFF, help="the shared directory of the T009 setup")
    p.add_argument("--units", type=int, default=MAX_UNITS, help=f"serial units, 1 to {MAX_UNITS}")
    p.add_argument("--plan", action="store_true", help="print the stages and commands; run nothing")
    return p


def main(argv: Sequence[str] | None = None, *, env: dict[str, str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if not args.plan:
            check_code_copy(str(Path(__file__).resolve()))  # the wrapper itself must be the root-owned copy
        return run(args, dict(os.environ if env is None else env))
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
