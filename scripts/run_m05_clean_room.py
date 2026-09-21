#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Reproduce M0.5 in a fresh clone and environment; this is not independent review."""

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
    from .validate_m05_closure import (
        INPUTS,
        REPORT_ASSET,
        REPORT_PDF,
        REPORT_PPTX,
        REPRODUCTION_VERSION,
        REQUIRED_OBSERVATIONS,
        observation_id,
    )
else:
    from validate_m05_closure import (
        INPUTS,
        REPORT_ASSET,
        REPORT_PDF,
        REPORT_PPTX,
        REPRODUCTION_VERSION,
        REQUIRED_OBSERVATIONS,
        observation_id,
    )


ROOT = Path(__file__).resolve().parents[1]
PASSTHROUGH_ENVIRONMENT = (
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TMP", "TEMP",
    "SYSTEMROOT", "COMSPEC", "PATHEXT", "WINDIR",
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
    "http_proxy", "https_proxy", "all_proxy", "no_proxy",
    "SSL_CERT_FILE", "REQUESTS_CA_BUNDLE",
    "PIP_INDEX_URL", "PIP_EXTRA_INDEX_URL", "PIP_TRUSTED_HOST",
)


def _run(command: list[str], cwd: Path, env: dict[str, str]) -> dict:
    process = subprocess.run(
        command, cwd=cwd, env=env, text=True, capture_output=True, check=False,
    )
    return {
        "command": " ".join(command),
        "exitCode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _git(source: Path, *args: str, env: dict[str, str]) -> str:
    process = subprocess.run(
        ["git", "-C", str(source), *args], text=True, capture_output=True,
        check=False, env=env,
    )
    if process.returncode:
        raise ValueError(process.stderr.strip() or "Git command failed")
    return process.stdout.strip()


def _version(executable: Path, env: dict[str, str]) -> tuple[str, tuple[int, ...]]:
    process = subprocess.run(
        [str(executable), "-c", "import platform; print(platform.python_version())"],
        text=True, capture_output=True, check=True, env=env,
    )
    value = process.stdout.strip()
    return value, tuple(int(part) for part in value.split("."))


def _candidate_input_hashes(
    source: Path, commit: str, env: dict[str, str]
) -> dict[str, str]:
    values = {}
    for relative in INPUTS:
        process = subprocess.run(
            ["git", "-C", str(source), "show", f"{commit}:{relative}"],
            capture_output=True, check=False, env=env,
        )
        if process.returncode:
            raise ValueError(f"candidate input is unavailable: {relative}")
        values[relative] = hashlib.sha256(process.stdout).hexdigest()
    return values


def _clean_environment(source: dict[str, str] | None = None) -> dict[str, str]:
    inherited = os.environ if source is None else source
    env = {name: inherited[name] for name in PASSTHROUGH_ENVIRONMENT if name in inherited}
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


def reproduce(source: Path, commit: str, output: Path, python: Path) -> None:
    source = source.resolve()
    output = output.resolve()
    env = _clean_environment()
    if not source.is_dir() or not (source / ".git").exists():
        raise ValueError("source must be a Git working tree")
    resolved = _git(source, "rev-parse", f"{commit}^{{commit}}", env=env)
    if resolved != commit:
        raise ValueError("candidate must be an exact full commit hash")
    python_version, version_tuple = _version(python, env)
    if version_tuple < (3, 12):
        raise ValueError("M0.5 clean-room reproduction requires Python 3.12 or newer")

    with tempfile.TemporaryDirectory(prefix="agent-braid-m05-") as directory:
        temporary = Path(directory)
        clone = temporary / "repository"
        environment = temporary / "venv"
        clone_result = subprocess.run(
            ["git", "clone", "--no-local", "--no-checkout", str(source), str(clone)],
            text=True, capture_output=True, check=False, env=env,
        )
        if clone_result.returncode:
            raise RuntimeError(clone_result.stderr.strip() or "clean clone failed")
        checkout = subprocess.run(
            ["git", "-C", str(clone), "checkout", "--detach", commit],
            text=True, capture_output=True, check=False, env=env,
        )
        if checkout.returncode:
            raise RuntimeError(checkout.stderr.strip() or "candidate checkout failed")

        initial_status = _git(
            clone, "status", "--porcelain=v1", "--untracked-files=all", env=env,
        )
        if initial_status:
            raise RuntimeError("clean-room clone is not initially clean")
        subprocess.run(
            [str(python), "-m", "venv", str(environment)], check=True, env=env,
        )
        clean_python = environment / "bin" / "python"
        if platform.system() == "Windows":
            clean_python = environment / "Scripts" / "python.exe"
        commands = [
            [str(clean_python), "-m", "pip", "install", "--no-cache-dir", "-r", "requirements-dev.txt", "-r", "requirements-speckit.txt"],
            [str(clean_python), "scripts/validate_repository.py"],
            [str(clean_python), "scripts/validate_contracts.py"],
            [str(clean_python), "scripts/validate_release_records.py"],
            [str(clean_python), "scripts/validate_research_radar.py", "--milestone", "M0.5"],
            [str(clean_python), "scripts/market_sizing.py", "--check"],
            [str(clean_python), "scripts/validate_spec_kit.py"],
            [str(clean_python), "scripts/spec_kit.py", "check"],
            [str(clean_python), "scripts/test_spec_kit_integration.py"],
            [str(clean_python), "-m", "unittest", "discover", "-s", "tests", "-v"],
            [str(clean_python), "-m", "research.lab.controls"],
            [str(clean_python), "scripts/constitution_replica.py", "check"],
            [str(clean_python), "scripts/validate_m05_closure.py", "--candidate"],
            ["git", "diff-tree", "--check", "--root", "--no-commit-id", "-r", commit],
        ]
        expected_ids = [identifier for identifier, _ in REQUIRED_OBSERVATIONS]
        rendered_ids = [observation_id(" ".join(command)) for command in commands]
        if rendered_ids != expected_ids:
            raise RuntimeError("clean-room command inventory is inconsistent")
        observations = []
        for command in commands:
            observation = _run(command, clone, env)
            observations.append(observation)
            if observation["exitCode"]:
                break
        final_status = _git(
            clone, "status", "--porcelain=v1", "--untracked-files=all", env=env,
        )
        inputs = _candidate_input_hashes(source, commit, env)
        record = {
            "recordVersion": REPRODUCTION_VERSION,
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "reviewedCommit": commit,
            "tree": _git(clone, "rev-parse", f"{commit}^{{tree}}", env=env),
            "platform": platform.platform(),
            "python": python_version,
            "git": _git(clone, "--version", env=env),
            "cleanRoom": {
                "freshClone": True,
                "freshEnvironment": True,
                "pipCacheDisabled": True,
                "initialStatus": initial_status,
                "finalStatus": final_status,
            },
            "operator": {
                "automation": "Codex",
                "authorization": "Explicit founder authorization",
                "supervisor": "Juan Antonio Yáñez García",
                "independent": False,
            },
            "inputs": inputs,
            "observations": observations,
            "reportArtifacts": {
                relative: inputs[relative]
                for relative in (REPORT_PPTX, REPORT_PDF, REPORT_ASSET)
            },
            "independentValidation": "pending",
            "limits": [
                "Founder-supervised internal reproduction; not independent validation.",
                "Offline structural and arithmetic checks do not establish source freshness, market demand or scientific truth.",
                "No production-safety, execution-authorization, general-confluence or Yang-Baxter claim.",
                "Repository visibility and historical Git-object redistribution remain outside this reproduction.",
            ],
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        failed = [item for item in observations if item["exitCode"]]
        if failed or final_status or rendered_ids != expected_ids:
            raise RuntimeError(
                f"clean-room reproduction failed; evidence written to {output}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("commit")
    parser.add_argument("--source", type=Path, default=ROOT)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "specs/008-m0.5-closure/reproduction.json",
    )
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    try:
        reproduce(args.source, args.commit, args.output, args.python)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"M0.5 clean-room reproduction failed: {exc}", file=sys.stderr)
        return 1
    print(
        f"M0.5 internal clean-room evidence written to {args.output}; "
        "independent validation remains pending."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
