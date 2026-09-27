#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce the bounded M2 candidate in isolation; not an independent review."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

if __package__:
    from .validate_m2_closure import (
        EXIT_CRITERIA, INPUTS, MINIMUM_BASE, REQUIRED_OBSERVATIONS, VERSION,
        observation_id,
    )
else:
    from validate_m2_closure import (
        EXIT_CRITERIA, INPUTS, MINIMUM_BASE, REQUIRED_OBSERVATIONS, VERSION,
        observation_id,
    )


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REMOTES = {
    "https://github.com/jayanez/agent-braid",
    "https://github.com/jayanez/agent-braid.git",
    "git@github.com:jayanez/agent-braid.git",
}
PASSTHROUGH_ENVIRONMENT = (
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TMP", "TEMP",
    "SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR",
)


def _environment(source: dict[str, str] | None = None) -> dict[str, str]:
    inherited = os.environ if source is None else source
    env = {key: inherited[key] for key in PASSTHROUGH_ENVIRONMENT if key in inherited}
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
        "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1", "GIT_TERMINAL_PROMPT": "0",
    })
    return env


def _redact(value: str, clean_room: Path) -> str:
    paths = {str(clean_room), str(clean_room.resolve())}
    for path in sorted(paths, key=len, reverse=True):
        value = value.replace(path, "${CLEAN_ROOM}")
    return value


def _run(command: list[str], cwd: Path, env: dict[str, str],
         clean_room: Path) -> dict:
    process = subprocess.run(command, cwd=cwd, env=env, text=True,
                             capture_output=True, check=False)
    return {
        "command": [_redact(part, clean_room) for part in command],
        "exitCode": process.returncode,
        "stdout": _redact(process.stdout, clean_room),
        "stderr": _redact(process.stderr, clean_room),
    }


def _git(source: Path, *args: str, env: dict[str, str]) -> str:
    process = subprocess.run(["git", "-C", str(source), *args], env=env,
                             text=True, capture_output=True, check=False)
    if process.returncode:
        raise ValueError(process.stderr.strip() or "Git command failed")
    return process.stdout.strip()


def _python_version(executable: Path, env: dict[str, str]) -> str:
    process = subprocess.run(
        [str(executable), "-c", "import platform; print(platform.python_version())"],
        env=env, text=True, capture_output=True, check=True,
    )
    return process.stdout.strip()


def _input_hashes(source: Path, commit: str, env: dict[str, str]) -> dict[str, str]:
    hashes = {}
    for relative in INPUTS:
        process = subprocess.run(
            ["git", "-C", str(source), "show", f"{commit}:{relative}"],
            env=env, capture_output=True, check=False,
        )
        if process.returncode:
            raise ValueError(f"candidate input is unavailable: {relative}")
        hashes[relative] = hashlib.sha256(process.stdout).hexdigest()
    return hashes


def _remote_ref(source: Path, ref: str, env: dict[str, str]) -> str:
    lines = _git(source, "ls-remote", "--exit-code", "origin", ref, env=env).splitlines()
    matches = [line.split("\t", 1) for line in lines if "\t" in line]
    if len(matches) != 1 or matches[0][1] != ref \
            or len(matches[0][0]) != 40 \
            or any(char not in "0123456789abcdef" for char in matches[0][0]):
        raise ValueError(f"remote ref is unavailable or ambiguous: {ref}")
    return matches[0][0]


def reproduce(source: Path, commit: str, candidate_ref: str,
              output: Path, python: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    env = _environment()
    if not source.is_dir() or not (source / ".git").exists():
        raise ValueError("source must be a Git working tree")
    resolved = _git(source, "rev-parse", f"{commit}^{{commit}}", env=env)
    if resolved != commit:
        raise ValueError("candidate must be an exact full commit hash")
    remote = _git(source, "remote", "get-url", "origin", env=env)
    if remote not in PUBLIC_REMOTES:
        raise ValueError("source origin must be the public Agent Braid repository")
    if not candidate_ref.startswith("refs/heads/") or candidate_ref == "refs/heads/develop":
        raise ValueError("candidate ref must name a published feature branch")
    _git(source, "check-ref-format", candidate_ref, env=env)
    if _remote_ref(source, candidate_ref, env) != commit:
        raise ValueError("published candidate ref does not match the frozen commit")
    develop_base = _remote_ref(source, "refs/heads/develop", env)
    _git(source, "merge-base", "--is-ancestor", MINIMUM_BASE, develop_base, env=env)
    _git(source, "merge-base", "--is-ancestor", develop_base, commit, env=env)
    version = _python_version(python, env)
    if tuple(int(part) for part in version.split(".")) < (3, 12):
        raise ValueError("M2 clean-room reproduction requires Python 3.12+")
    inputs = _input_hashes(source, commit, env)

    with tempfile.TemporaryDirectory(prefix="agent-braid-m2-") as directory:
        temporary = Path(directory)
        clone = temporary / "repository"
        environment = temporary / "venv"
        scratch = temporary / "tmp"
        scratch.mkdir()
        env.update({"TMPDIR": str(scratch), "TMP": str(scratch), "TEMP": str(scratch)})
        clone_result = subprocess.run(
            ["git", "clone", "--no-local", "--no-checkout", str(source), str(clone)],
            env=env, text=True, capture_output=True, check=False,
        )
        if clone_result.returncode:
            raise RuntimeError(clone_result.stderr.strip() or "clean clone failed")
        _git(clone, "remote", "set-url", "origin", remote, env=env)
        _git(clone, "checkout", "--detach", commit, env=env)
        initial_status = _git(
            clone, "status", "--porcelain=v1", "--untracked-files=all", env=env
        )
        if initial_status:
            raise RuntimeError("M2 clone is not initially clean")
        subprocess.run([str(python), "-m", "venv", str(environment)],
                       env=env, check=True)
        clean_python = environment / ("Scripts/python.exe" if platform.system() == "Windows"
                                      else "bin/python")
        env["PATH"] = str(clean_python.parent) + os.pathsep + env.get("PATH", "")
        commands = [
            [str(clean_python), "-m", "pip", "install", "--no-cache-dir",
             "-r", "requirements-dev.txt", "-r", "requirements-speckit.txt"],
            [str(clean_python), "scripts/restore_public_spec_history.py"],
            ["git", "fetch", "origin", "refs/tags/spec-016-reviewed-0974739:refs/tags/spec-016-reviewed-0974739"],
            ["git", "fsck", "--unreachable", "--no-reflogs"],
            [str(clean_python), "scripts/validate_repository.py"],
            [str(clean_python), "scripts/validate_contracts.py"],
            [str(clean_python), "scripts/validate_release_records.py"],
            [str(clean_python), "scripts/validate_research_radar.py", "--milestone", "M2", "--require-approved"],
            [str(clean_python), "scripts/validate_m2_closure.py", "inputs"],
            [str(clean_python), "scripts/validate_spec_kit.py"],
            [str(clean_python), "scripts/spec_kit.py", "check"],
            [str(clean_python), "scripts/test_spec_kit_integration.py"],
            [str(clean_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
            [str(clean_python), "-m", "research.lab.controls"],
            [str(clean_python), "scripts/constitution_replica.py", "check"],
            [str(clean_python), "scripts/run_git_replay_benchmark.py"],
            ["git", "diff-tree", "--check", "--root", "--no-commit-id", "-r", commit],
        ]
        if ([observation_id(item) for item in commands]
                != [name for name, _ in REQUIRED_OBSERVATIONS]):
            raise RuntimeError("M2 clean-room command inventory is inconsistent")
        observations = []
        for command in commands:
            observation = _run(command, clone, env, temporary)
            observations.append(observation)
            if observation["exitCode"] or (observation_id(observation["command"])
                                           == "reachable-objects" and observation["stdout"]):
                break
        final_status = _git(
            clone, "status", "--porcelain=v1", "--untracked-files=all", env=env
        )
        source_evidence = None
        benchmark = None
        for item in observations:
            if observation_id(item["command"]) == "m2-inputs" and item["exitCode"] == 0:
                source_evidence = json.loads(item["stdout"])
            if observation_id(item["command"]) == "replay-benchmark" and item["exitCode"] == 0:
                benchmark = json.loads(item["stdout"])
        success = (len(observations) == len(commands)
                   and all(item["exitCode"] == 0 for item in observations)
                   and not final_status and source_evidence is not None
                   and benchmark is not None
                   and benchmark.get("scenarioCount") == 7
                   and benchmark.get("falseCandidateCount") == 0
                   and benchmark.get("thresholdsPassed") is True
                   and not next(item["stdout"] for item in observations
                                if observation_id(item["command"]) == "reachable-objects").strip())
        record = {
            "recordVersion": VERSION,
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "reviewedCommit": commit,
            "candidateRef": candidate_ref,
            "developBase": develop_base,
            "sourceRemote": remote,
            "tree": _git(clone, "rev-parse", f"{commit}^{{tree}}", env=env),
            "platform": platform.platform(), "python": version,
            "git": _git(clone, "--version", env=env),
            "cleanRoom": {
                "freshClone": True, "freshEnvironment": True,
                "pipCacheDisabled": True,
                "initialStatus": initial_status, "finalStatus": final_status,
            },
            "operator": {
                "automation": "Codex", "authorization": "User-directed M2 reproduction",
                "supervisor": "No live supervision recorded", "independent": False,
            },
            "inputs": inputs, "observations": observations,
            "exitCriteria": {
                key: {"status": "supported-bounded" if success else "not-established",
                      "observations": list(required)}
                for key, required in EXIT_CRITERIA.items()
            },
            "sourceEvidence": source_evidence,
            "independentValidation": "pending",
            "limits": [
                "Internal clean-room reproduction; same replay implementation, not independent validation.",
                "Finite fixed-patch Git and registered two-batch timing evidence only.",
                "SPEC-016 is private syntactic reduction; uncertain paths block interchange.",
                "No semantic commutation, general confluence, production speedup, live-agent safety or execution authorization.",
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not success:
            raise RuntimeError(f"M2 clean-room reproduction failed; evidence written to {output}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("commit")
    parser.add_argument("--candidate-ref", required=True,
                        help="exact published refs/heads/... naming the frozen commit")
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    try:
        reproduce(args.source, args.commit, args.candidate_ref,
                  args.output, args.python)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"M2 clean-room reproduction failed: {exc}", file=sys.stderr)
        return 1
    print(f"M2 internal evidence written to {args.output}; founder closure remains separate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
