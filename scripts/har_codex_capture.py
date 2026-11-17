#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture the real ``codex exec --json`` event shapes once (owner decision E3, SPEC-048/T013).

This script is NOT an authorization and qualifies nothing: ``NATIVE_DISPATCH_QUALIFIED`` in
``agent_braid/harness_host_codex.py`` stays false. It runs the ChatGPT.app Codex CLI a fixed
number of times on one trivial read-only prompt in a throwaway directory, keeps the raw JSONL
privately, and writes a redacted shape summary (event types, item types, key names and value
types; no assistant text, command output or path) with SHA-256 hashes to
``specs/048-harness-variant-laboratory/evidence/codex-capture/``.

Run it once in your own Terminal.app, from the repository root::

    python3 scripts/har_codex_capture.py --dry-run    # checks binary, version and login; runs no prompt
    python3 scripts/har_codex_capture.py              # RUNS prompts on your ChatGPT subscription

Fixed choices, not options:

- binary: the canonical ChatGPT.app build at ``CODEX`` only (never a PATH lookup, never the
  VS Code build); its SHA-256 and ``--version`` are recorded;
- account: the isolated sign-in ``~/agent-braid-auth/codex`` as ``CODEX_HOME`` (never
  ``~/.codex``), which must report ``Logged in using ChatGPT``; no API key or provider variable
  reaches the child (its environment is built from scratch);
- run: ``exec --json --ephemeral -s read-only`` with approvals off, user config and rules
  ignored, in a new empty temporary directory removed afterwards; per-run wall timeout.

Raw output stays under ``~/agent-braid-private/codex-capture/<stamp>/`` (mode 0700), outside
the repository. Exit status: 0 captured (or dry run passed), 1 a check stopped it, 2 a run failed.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent_braid.harness_host_codex import _BUILD, _Normalizer, _split  # noqa: E402

FORMAT = "braid-har-codex-capture/v0.1"
CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex")
AUTH_DIR = Path.home() / "agent-braid-auth" / "codex"
PRIVATE_DIR = Path.home() / "agent-braid-private" / "codex-capture"
EVIDENCE_DIR = ROOT / "specs/048-harness-variant-laboratory/evidence/codex-capture"
RUNS = 2
RUN_TIMEOUT_SECONDS = 240
PROMPT = ("Run the shell command `ls` in the current directory, then reply with only the "
          "number of entries it listed. Do not modify anything.")
FIXTURE = {"README.txt": b"capture fixture\n", "notes.txt": b"nothing to see\n"}
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
LOGGED_IN = "Logged in using ChatGPT"
# Values kept verbatim in the summary: enumerations, never free text.
ENUM_KEYS = frozenset({"type", "status"})
ENUM_VALUE = re.compile(r"[a-z][a-z0-9_.]{0,40}\Z")


class Stop(Exception):
    """A check failed; the message is the stop reason."""


def argv_for(codex: Path, workdir: Path) -> list[str]:
    return [str(codex), "exec", "--json", "--ephemeral", "-s", "read-only",
            "--skip-git-repo-check", "--ignore-user-config", "--ignore-rules",
            "--color", "never", "-c", 'approval_policy="never"', "-C", str(workdir), PROMPT]


def child_env(auth_dir: Path, tmp: Path) -> dict[str, str]:
    return {"HOME": str(Path.home()), "PATH": SYSTEM_PATH, "CODEX_HOME": str(auth_dir),
            "TMPDIR": str(tmp), "LANG": "C.UTF-8", "NO_COLOR": "1"}


def binary_sha256(codex: Path) -> str:
    fd = os.open(codex, os.O_RDONLY | os.O_NOFOLLOW)
    digest = hashlib.sha256()
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o022 or not info.st_mode & 0o100:
            raise Stop("codex binary is not a regular, executable, non-writable file")
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check_auth_dir(auth_dir: Path) -> None:
    if auth_dir.resolve() == (Path.home() / ".codex").resolve():
        raise Stop("auth dir must be the isolated sign-in, never ~/.codex")
    try:
        info = auth_dir.lstat()
    except FileNotFoundError:
        raise Stop(f"auth dir missing: sign in once with CODEX_HOME={auth_dir} codex login") from None
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise Stop("auth dir must be a directory owned by you with mode 0700")
    if not (auth_dir / "auth.json").is_file():  # presence only; the file is never read
        raise Stop("auth dir has no sign-in (auth.json)")


def quick(argv: list[str], env: dict[str, str], cwd: Path) -> str:
    done = subprocess.run(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True,
                          text=True, timeout=60)
    return (done.stdout + done.stderr).strip()


def preflight(codex: Path, auth_dir: Path, tmp: Path) -> dict[str, Any]:
    if not codex.is_absolute() or codex.is_symlink():
        raise Stop("codex binary must be the canonical absolute path, not a link")
    check_auth_dir(auth_dir)
    sha = binary_sha256(codex)
    env = child_env(auth_dir, tmp)
    version = quick([str(codex), "--version"], env, tmp).splitlines()
    if not version or _BUILD.fullmatch(version[0]) is None:
        raise Stop("codex --version did not report a codex-cli build")
    status = quick([str(codex), "login", "status"], env, tmp)
    if LOGGED_IN not in status:  # an API-key login or no login: refuse, never fall back
        raise Stop("isolated auth dir is not signed in with ChatGPT")
    return {"path": str(codex), "sha256": sha, "version": version[0], "login": LOGGED_IN}


def _type_name(value: Any) -> str:
    return {dict: "object", list: "array", str: "string", bool: "boolean", int: "integer",
            float: "number", type(None): "null"}[type(value)]


def shape(value: Any, depth: int = 0) -> Any:
    """Key names and value types; enumerated ``type``/``status`` values only."""
    if type(value) is dict and depth < 4:
        out: dict[str, Any] = {}
        for key in sorted(value):
            item = value[key]
            if key in ENUM_KEYS and type(item) is str and ENUM_VALUE.fullmatch(item):
                out[key] = "=" + item
            else:
                out[key] = shape(item, depth + 1)
        return out
    if type(value) is list and depth < 4:
        kinds = sorted({json.dumps(shape(v, depth + 1), sort_keys=True) for v in value})
        return {"array": [json.loads(k) for k in kinds]}
    return _type_name(value)


def summarize(raw: bytes) -> dict[str, Any]:
    shapes: Counter[str] = Counter()
    events: Counter[str] = Counter()
    unparsed = 0
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            unparsed += 1
            continue
        kind = value.get("type") if type(value) is dict else None
        item = value.get("item") if type(value) is dict else None
        item_kind = item.get("type") if type(item) is dict else None
        label = f"{kind}" + (f"/{item_kind}" if type(item_kind) is str else "")
        events[label if ENUM_VALUE.fullmatch(label.replace("/", ".")) else "<non-enum>"] += 1
        shapes[json.dumps(shape(value), sort_keys=True)] += 1
    normalizer = _Normalizer()
    lines, rest = _split(raw)
    for line in lines + ([rest] if rest else []):
        normalizer.line(line)
    return {
        "events": dict(sorted(events.items())),
        "shapes": [{"count": n, "shape": json.loads(s)} for s, n in sorted(shapes.items())],
        "unparsedLines": unparsed,
        "adapterFit": {"kinds": dict(sorted(Counter(e["kind"] for e in normalizer.events).items())),
                       "ignored": normalizer.ignored, "errors": sorted(set(normalizer.errors)),
                       "hostTerminal": normalizer.host_terminal,
                       "usageKeys": sorted(normalizer.usage)},
    }


def run_once(argv: list[str], env: dict[str, str], cwd: Path) -> tuple[int | str, bytes, bytes]:
    process = subprocess.Popen(argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True)
    try:
        out, err = process.communicate(timeout=RUN_TIMEOUT_SECONDS)
        return process.returncode, out, err
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        out, err = process.communicate()
        return "timeout", out, err


def private_dir(base: Path, stamp: str) -> Path:
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    base.chmod(0o700)
    target = base / stamp
    target.mkdir(mode=0o700)
    return target


def main(argv: Sequence[str] | None = None, *, codex: Path = CODEX, auth_dir: Path = AUTH_DIR,
         private_base: Path = PRIVATE_DIR, evidence_dir: Path = EVIDENCE_DIR,
         now: datetime | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true",
                        help="check binary, version and login, print the run, run no prompt")
    args = parser.parse_args(argv)
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    with tempfile.TemporaryDirectory(prefix="har-codex-capture-") as scratch:
        work, tmp = Path(scratch) / "work", Path(scratch) / "tmp"
        work.mkdir()
        tmp.mkdir()
        for name, data in FIXTURE.items():
            (work / name).write_bytes(data)
        try:
            binary = preflight(codex, auth_dir, tmp)
        except (Stop, OSError, subprocess.SubprocessError) as exc:
            print(f"STOP: {exc}", file=sys.stderr)
            return 1
        command = argv_for(codex, work)
        print(json.dumps({"binary": binary, "runs": RUNS, "argv": command}, indent=2))
        if args.dry_run:
            print("dry run: checks passed; no prompt was sent")
            return 0
        raw_dir = private_dir(private_base, stamp)
        runs, failed = [], False
        for index in range(RUNS):
            code, out, err = run_once(command, child_env(auth_dir, tmp), work)
            (raw_dir / f"run-{index}.jsonl").write_bytes(out)
            (raw_dir / f"run-{index}.stderr").write_bytes(err)
            failed = failed or code != 0
            runs.append({"index": index, "exit": code, "stdoutSha256": hashlib.sha256(out).hexdigest(),
                         "stdoutBytes": len(out), "stderrSha256": hashlib.sha256(err).hexdigest(),
                         "stderrBytes": len(err), **summarize(out)})
    record = {
        "format": FORMAT, "task": "SPEC-048/T013 (owner decision E3)", "capturedAt": stamp,
        "binary": binary, "auth": "existing-login (ChatGPT, isolated CODEX_HOME)",
        "argv": [*command[:-3], "<workdir>", command[-1]],
        "promptSha256": hashlib.sha256(PROMPT.encode()).hexdigest(),
        "fixture": {name: hashlib.sha256(data).hexdigest() for name, data in FIXTURE.items()},
        "runs": runs, "rawLocation": f"~/{raw_dir.relative_to(Path.home())}"
        if raw_dir.is_relative_to(Path.home()) else "private (outside the repository)",
        "redaction": "event and item types, key names, value types and enumerated type/status "
                     "values only; no assistant text, command, output, path or identifier",
        "executionAuthorization": False, "nativeDispatchQualified": False,
    }
    evidence_dir.mkdir(parents=True, exist_ok=True)
    target = evidence_dir / f"capture-{stamp}.json"
    target.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(f"wrote {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}")
    print(f"sha256 {hashlib.sha256(target.read_bytes()).hexdigest()}")
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
