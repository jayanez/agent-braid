#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce the clean public preview in a fresh clone and Python environment."""

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

try:
    from scripts.publication import redact_local_paths
    from scripts.validate_publication import PUBLIC_INPUTS, PUBLIC_OBSERVATIONS
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from publication import redact_local_paths
    from validate_publication import PUBLIC_INPUTS, PUBLIC_OBSERVATIONS


ROOT = Path(__file__).resolve().parents[1]
PASSTHROUGH = (
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TMP", "TEMP",
    "SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR", "HTTP_PROXY", "HTTPS_PROXY",
    "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL",
    "PIP_TRUSTED_HOST",
)


def clean_environment() -> dict[str, str]:
    env = {name: os.environ[name] for name in PASSTHROUGH if name in os.environ}
    env.update({
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_CONFIG_FILE": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    })
    return env


def run(command: list[str], cwd: Path, env: dict[str, str], identifier: str) -> dict:
    process = subprocess.run(command, cwd=cwd, env=env, text=True,
                             capture_output=True, check=False)
    return {
        "id": identifier,
        "command": " ".join(command),
        "exitCode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def git(root: Path, *args: str, env: dict[str, str]) -> str:
    process = subprocess.run(["git", "-C", str(root), *args], env=env,
                             text=True, capture_output=True, check=False)
    if process.returncode:
        raise ValueError(process.stderr.strip() or "Git command failed")
    return process.stdout.strip()


def reproduce(source: Path, commit: str, output: Path, python: Path) -> None:
    source, output = source.resolve(), output.resolve()
    env = clean_environment()
    if not re_full_commit(commit):
        raise ValueError("public reproduction requires an exact commit")
    if git(source, "rev-parse", f"{commit}^{{commit}}", env=env) != commit:
        raise ValueError("public reproduction commit did not resolve exactly")
    version_process = subprocess.run(
        [str(python), "-c", "import platform; print(platform.python_version())"],
        env=env, text=True, capture_output=True, check=False,
    )
    version = version_process.stdout.strip()
    if version_process.returncode or tuple(map(int, version.split("."))) < (3, 12):
        raise ValueError("public reproduction requires Python 3.12 or newer")

    with tempfile.TemporaryDirectory(prefix="agent-braid-public-") as directory:
        temporary = Path(directory)
        clone, environment = temporary / "repository", temporary / "venv"
        clone_result = subprocess.run(
            ["git", "clone", "--no-local", "--no-checkout", str(source), str(clone)],
            env=env, text=True, capture_output=True, check=False,
        )
        if clone_result.returncode:
            raise RuntimeError(clone_result.stderr.strip() or "clean clone failed")
        checkout = subprocess.run(["git", "-C", str(clone), "checkout", "--detach", commit],
                                  env=env, text=True, capture_output=True, check=False)
        if checkout.returncode:
            raise RuntimeError(checkout.stderr.strip() or "candidate checkout failed")
        initial = git(clone, "status", "--porcelain=v1", "--untracked-files=all", env=env)
        if initial:
            raise RuntimeError("public clean-room clone is initially dirty")
        subprocess.run([str(python), "-m", "venv", str(environment)], env=env, check=True)
        clean_python = environment / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
        commands = (
            ("install", [str(clean_python), "-m", "pip", "install", "--no-cache-dir", "-r", "requirements-dev.txt", "-r", "requirements-speckit.txt"]),
            ("repository", [str(clean_python), "scripts/validate_repository.py"]),
            ("contracts", [str(clean_python), "scripts/validate_contracts.py"]),
            ("release-records", [str(clean_python), "scripts/validate_release_records.py"]),
            ("publication", [str(clean_python), "scripts/validate_publication.py", "--portable"]),
            ("spec-kit", [str(clean_python), "scripts/validate_spec_kit.py"]),
            ("spec-kit-render", [str(clean_python), "scripts/spec_kit.py", "check"]),
            ("spec-kit-integration", [str(clean_python), "scripts/test_spec_kit_integration.py"]),
            ("tests", [str(clean_python), "-m", "unittest", "discover", "-s", "tests", "-v"]),
            ("scientific-controls", [str(clean_python), "-m", "research.lab.controls"]),
            ("constitution-replica", [str(clean_python), "scripts/constitution_replica.py", "check"]),
            ("whitespace", ["git", "diff", "--check"]),
        )
        if tuple(identifier for identifier, _ in commands) != PUBLIC_OBSERVATIONS:
            raise RuntimeError("public reproduction command inventory is inconsistent")
        observations = []
        for identifier, command in commands:
            observation = run(command, clone, env, identifier)
            observations.append(observation)
            if observation["exitCode"]:
                break
        final = git(clone, "status", "--porcelain=v1", "--untracked-files=all", env=env)
        inputs = {}
        for relative in PUBLIC_INPUTS:
            payload = subprocess.run(["git", "-C", str(source), "show", f"{commit}:{relative}"],
                                     env=env, capture_output=True, check=False)
            if payload.returncode:
                raise ValueError(f"public reproduction input is unavailable: {relative}")
            inputs[relative] = hashlib.sha256(payload.stdout).hexdigest()
        record = {
            "recordVersion": "0.1.0",
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "reviewedCommit": commit,
            "tree": git(source, "rev-parse", f"{commit}^{{tree}}", env=env),
            "platform": platform.platform(),
            "python": version,
            "git": git(source, "--version", env=env),
            "cleanRoom": {
                "freshClone": True, "freshEnvironment": True, "pipCacheDisabled": True,
                "initialStatus": initial, "finalStatus": final,
            },
            "operator": {
                "automation": "Codex",
                "authorization": "Explicit founder authorization",
                "supervisor": "Juan Antonio Yáñez García",
                "independent": False,
            },
            "inputs": inputs,
            "observations": observations,
            "independentValidation": "pending",
            "limits": [
                "Founder-supervised internal reproduction; not independent validation.",
                "Portable integrity does not verify unavailable private Git ancestry.",
                "No production-safety, execution-authorization, general-confluence or Yang-Baxter claim.",
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = (json.dumps(record, indent=2, sort_keys=True) + "\n").encode("utf-8")
        output.write_bytes(redact_local_paths(serialized))
        if len(observations) != len(commands) or any(item["exitCode"] for item in observations) or final:
            raise RuntimeError(f"public clean-room reproduction failed; evidence written to {output}")


def re_full_commit(value: str) -> bool:
    return len(value) == 40 and all(character in "0123456789abcdef" for character in value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("commit")
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    try:
        reproduce(args.source, args.commit, args.output, args.python)
    except (OSError, UnicodeError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Public clean-room reproduction failed: {exc}")
        return 1
    print(f"Public internal reproduction written to {args.output}; independent validation remains pending.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
