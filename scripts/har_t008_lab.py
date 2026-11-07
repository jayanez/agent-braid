#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-048/T008 native Claude cohort as ONE command, run inside the dedicated account's own login session.

NOT an authorization and not a verdict: ``executionAuthorization`` stays false and the qualified verdict is the
founder's, decided from the saved evidence. It chains, and stops (``STOP:`` text, exit 1) when a stage fails:

1. re-hashes ``claude``, the interpreter and ``sandbox-exec`` against the pins of the SPEC-065 T009 setup summary
   (the same account, login and token file are reused; nothing is re-created and no token is read);
2. runs ``har_t008_unit.py --dry-run`` from the root-owned code copy of ``--commit`` and saves ``from-lab/``
   ``t008-dry-run.json`` (+ ``.sha256``); it must say ``ready``;
3. runs ``har_t008_unit.py --founder-go`` with the terminal attached (the driver asks for the attempt name and
   the usage card before and after every unit), tees the transcript and saves ``t008-cohort-<attempt>.txt`` and the
   final report ``t008-cohort-<attempt>.json`` (+ ``.sha256``).

The driver enforces the founder window (2026-11-09T20:30Z to 2026-11-30), at most four serial units, the D2 caps
and the issued-record expiry; this wrapper adds none of that and weakens none of it. No sudo is run here: the code
copy for ``--commit`` is installed beforehand by the owner (see the packet). Standard library only::

    B=/usr/local/libexec/braid
    $B/python312/bin/python3.12 -B -I $B/repo-<short>/scripts/har_t008_lab.py \\
        --commit <40-hex> --operator-account <daily account> --attempt t008-<YYYYMMDD>

``--plan`` prints the stages and commands without running anything.
"""
from __future__ import annotations

import argparse
import codecs
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Callable, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))

import har_t009_lab as base  # noqa: E402

Stop = base.Stop
MAX_UNITS = 4  # the founder's 2026-11-06 choice; the driver repeats the cap
ATTEMPT_RE = re.compile(r"t008-[0-9]{8}[a-z0-9-]{0,16}")


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
    """The driver prints its report last, as indented JSON on lines of its own; trailing text (a traceback) is ignored."""
    decoder = json.JSONDecoder()
    text = "\n" + text
    start = len(text)
    while (start := text.rfind("\n{\n", 0, start)) >= 0:
        try:
            report, _ = decoder.raw_decode(text[start + 1:])
        except ValueError:
            continue
        if isinstance(report, dict) and "verdict" in report:
            return report
    raise Stop("STOP: the driver printed no final JSON report; the transcript was saved, tell the orchestrator")


def run_cohort_capture(cmd: list[str], env: dict[str, str], home: str, attempt: str, from_lab: Path,
                       say: Callable[[str], None]) -> int:
    """Run the interactive cohort, relay its output live, always save the transcript, then the final report."""
    chunks: list[str] = []
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    code = 1
    try:
        with subprocess.Popen(cmd, env=env, cwd=home, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
            while data := proc.stdout.read1(4096):
                text = decoder.decode(data)
                sys.stdout.write(text)
                sys.stdout.flush()
                chunks.append(text)
        code = proc.returncode
    finally:  # Ctrl-C included: units may have spent quota, so the transcript is kept whatever happened
        chunks.append(decoder.decode(b"", final=True))
        base.save_output(f"t008-cohort-{attempt}.txt", "".join(chunks), from_lab)
    try:
        report = extract_report("".join(chunks))
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return code or 1
    verdict = report["verdict"]
    name = f"t008-cohort-{attempt}.json"
    digest = base.save_output(name, json.dumps(report, indent=2, sort_keys=True) + "\n", from_lab)
    say(f"   saved {name} (SHA-256 {digest}): verdict {verdict}, units {report.get('units')}, "
        f"stopped {report.get('stopped')}; send it to the orchestrator")
    if code == 0 and verdict != "cohort-finished":
        return 1  # exit code and verdict must agree before this looks like success
    return code


def plan(args: argparse.Namespace, pins: dict, home: str) -> None:
    show = lambda cmd: print("+ " + " ".join(shlex.quote(w) for w in cmd))  # noqa: E731
    print("== The owner installs the root-owned code copy for --commit beforehand (the T009 setup script); no sudo here")
    print("== re-hash claude, interpreter, sandbox-exec against the T009 setup summary pins")
    print("== window: the driver refuses outside 2026-11-09T20:30Z..2026-11-30 and after the issued-record expiry")
    print("== Stage 1. dry run, saved to from-lab/t008-dry-run.json (+ .sha256); must be 'ready'")
    show(driver_command(args, pins, home, "--dry-run"))
    print("== Stage 2. the cohort (the driver asks for the attempt name and the usage card before/after each unit)")
    show(driver_command(args, pins, home, "--founder-go"))
    print(f"== transcript and report saved as from-lab/t008-cohort-{args.attempt}.txt/.json (+ .sha256); "
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
    leaked = sorted(name for name, value in env.items() if base.ENV_RE.search(f"{name}={value}"))
    if leaked:
        raise Stop("STOP: the environment has ANTHROPIC/CLAUDE variables: " + ", ".join(name for name in leaked))
    summary, _ = base.load_summary(summary_path, args.commit)
    pins = summary["pins"]
    if args.plan:
        plan(args, pins, home)
        return 0
    driver = f"{base.BRAID}/repo-{args.commit[:7]}/scripts/har_t008_unit.py"
    if not os.path.isfile(driver):
        raise Stop(f"STOP: the code copy is missing: {driver} (the owner installs it for this commit first)")
    for path, pin in ((base.CLAUDE, pins["claudeSha256"]), (base.PYTHON, pins["interpreterSha256"]),
                      (base.SANDBOX_EXEC, pins["sandboxExecSha256"])):
        if base.sha256_file(path) != pin:
            raise Stop(f"STOP: {path} does not match its pinned hash")
    from_lab = Path(args.handoff) / "from-lab"
    if not from_lab.is_dir() or not os.access(from_lab, os.W_OK):
        raise Stop(f"STOP: {from_lab} is missing or not writable by this account")
    keep = ("PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "TERM")
    session_env = {**{k: v for k, v in env.items() if k in keep}, "CLAUDE_CONFIG_DIR": f"{home}/t009/config", "DISABLE_AUTOUPDATER": "1"}

    say("\n== Stage 1. Dry run (pre-flight, issued records, qualified policy, MDRV-04 guard; no quota read)")
    base.run_driver_capture(driver_command(args, pins, home, "--dry-run"), session_env, home, "t008-dry-run.json",
                            from_lab, {"ready": 0}, say)
    say("\n== Stage 2. The cohort: one small read-only Haiku session per unit, serial")
    code = run_cohort_capture(driver_command(args, pins, home, "--founder-go"), session_env, home, args.attempt,
                              from_lab, say)
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
        return run(args, dict(os.environ if env is None else env))
    except Stop as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
