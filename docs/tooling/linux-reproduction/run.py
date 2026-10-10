# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed launcher for a frozen, offline Linux x86_64 tooling probe.

This script validates a transport bundle and the already-present local Docker
image. It never pulls or builds an image. Container execution requires the
explicit --execute flag. Native Linux x86_64 is the default; bounded AMD64
emulation on ARM64 requires a separate explicit option and is recorded.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import selectors
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid


IMAGE = (
    "python:3.13.11-slim-bookworm@sha256:"
    "ac76900038d8606cc99b413d4ede77bc7152f1e42b94cf5d50d4b80a999652fe"
)
IMAGE_DIGEST = IMAGE.rsplit("@", 1)[1]
TARGET = "linux-amd64"
CANDIDATE_FILENAME = "agent_braid-0.1.0a1-py3-none-any.whl"
MAX_SECONDS = 720
MAX_DOCKER_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_TRACE_BYTES = 64 * 1024


class Refused(ValueError):
    """A fixed fail-closed preparation diagnosis."""


def sha256_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise Refused("input is not a regular file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha256(value: str, name: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise Refused(f"{name} must be a lowercase SHA-256")
    return value


def require_native_target(system: str, machine: str) -> None:
    if system != "Linux" or machine.lower() not in {"x86_64", "amd64"}:
        raise Refused("native execution requires Linux x86_64")


def launch_host_identity(system: str, machine: str, allow_emulation: bool) -> dict:
    if system == "Linux" and machine.lower() in {"x86_64", "amd64"}:
        return {"system": system, "machine": machine, "mode": "native-launch-host",
                "amd64EmulationAllowed": allow_emulation}
    if allow_emulation and system in {"Darwin", "Linux"} and machine.lower() in {"arm64", "aarch64"}:
        return {"system": system, "machine": machine, "mode": "arm64-launch-host-amd64-container",
                "amd64EmulationAllowed": True}
    require_native_target(system, machine)
    raise Refused("unsupported launch host")


def inspect_daemon_identity(docker: str) -> dict:
    context_override = os.environ.get("DOCKER_CONTEXT")
    endpoint = None if context_override else os.environ.get("DOCKER_HOST")
    if not endpoint:
        context_command = [docker, "context", "inspect"]
        if context_override:
            context_command.append(context_override)
        context_command += ["--format", "{{json .Endpoints.docker.Host}}"]
        selected = subprocess.run(context_command,
                                  check=False, capture_output=True, text=True, timeout=15)
        if selected.returncode != 0:
            raise Refused("Docker context endpoint unavailable")
        try:
            endpoint = json.loads(selected.stdout)
        except (ValueError, TypeError) as exc:
            raise Refused("Docker context endpoint unreadable") from exc
    if not isinstance(endpoint, str) or not endpoint.startswith("unix://"):
        raise Refused("standalone reproduction requires a local Unix Docker endpoint")
    result = subprocess.run([docker, "info", "--format", "{{json .}}"],
                            check=False, capture_output=True, text=True, timeout=15)
    if result.returncode != 0:
        raise Refused("Docker daemon identity unavailable")
    try:
        value = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise Refused("Docker daemon identity unreadable") from exc
    if not isinstance(value, dict) or value.get("OSType") != "linux" or value.get("Architecture") not in {"aarch64", "arm64", "x86_64", "amd64"}:
        raise Refused("unsupported Docker daemon platform")
    identity = {key: value.get(key) for key in ("OSType", "Architecture", "ServerVersion")}
    identity["endpointScheme"] = "unix"
    identity["endpointSha256"] = hashlib.sha256(endpoint.encode("utf-8")).hexdigest()
    identity["containerExecutionMode"] = ("amd64-on-arm64-daemon-emulation"
        if value["Architecture"] in {"arm64", "aarch64"} else "amd64-on-amd64-daemon")
    return identity


def validate_manifest_bundle(input_root: Path, *, manifest_sha256: str,
                             candidate_sha256: str, probe_sha256: str,
                             wheelhouse_sha256: str) -> dict[str, Path | str]:
    """Verify frozen input identities without importing or running the package."""
    if input_root.is_symlink():
        raise Refused("input bundle must be a real directory")
    root = input_root.resolve(strict=True)
    if not root.is_dir():
        raise Refused("input bundle must be a real directory")
    expected_manifest = require_sha256(manifest_sha256, "manifest SHA-256")
    expected_candidate = require_sha256(candidate_sha256, "candidate SHA-256")
    expected_probe = require_sha256(probe_sha256, "probe SHA-256")
    expected_wheelhouse = require_sha256(wheelhouse_sha256, "wheelhouse SHA-256")

    candidate = root / CANDIDATE_FILENAME
    probe = root / "verify_installed_tooling.py"
    manifest_path = root / "reproducibility" / "mcp-2.3.0-cp313-linux-amd64.manifest.json"
    wheelhouse = root / "wheelhouse"
    if sha256_file(candidate) != expected_candidate:
        raise Refused("candidate wheel digest mismatch")
    if sha256_file(probe) != expected_probe:
        raise Refused("probe script digest mismatch")
    if sha256_file(manifest_path) != expected_manifest:
        raise Refused("dependency manifest digest mismatch")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise Refused("dependency manifest unreadable") from exc
    target_row = manifest.get("target")
    if (not isinstance(target_row, dict)
            or manifest.get("schema") != "agent-braid-mcp-closure/v1"
            or target_row.get("name") != TARGET
            or target_row.get("platformSystem") != "Linux"
            or target_row.get("platformMachine") != "x86_64"
            or target_row.get("python") != "3.13.11"
            or target_row.get("implementation") != "CPython"
            or manifest.get("directRequirements") != ["mcp==2.3.0"]):
        raise Refused("dependency manifest target mismatch")
    lock = manifest.get("lockFile")
    if not isinstance(lock, dict) or lock.get("path") != "mcp-2.3.0-cp313-linux-amd64.lock.txt":
        raise Refused("dependency lock identity mismatch")
    lock_path = manifest_path.parent / lock["path"]
    if sha256_file(lock_path) != lock.get("sha256"):
        raise Refused("dependency lock digest mismatch")

    package_rows = manifest.get("packages")
    if not isinstance(package_rows, list) or not package_rows:
        raise Refused("dependency closure missing")
    expected_wheels = {}
    for row in package_rows:
        if not isinstance(row, dict):
            raise Refused("invalid dependency package row")
        name, digest = row.get("wheel"), row.get("wheelSha256")
        if (not isinstance(name, str) or Path(name).name != name or name in expected_wheels
                or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
            raise Refused("invalid dependency wheel identity")
        expected_wheels[name] = digest
    if wheelhouse.is_symlink() or not wheelhouse.is_dir():
        raise Refused("offline wheelhouse missing")
    actual_files = list(wheelhouse.iterdir())
    if any(path.is_symlink() or not path.is_file() for path in actual_files):
        raise Refused("wheelhouse contains a non-file entry")
    if {path.name for path in actual_files} != set(expected_wheels):
        raise Refused("wheelhouse roster mismatch")
    actual_hashes = {path.name: sha256_file(path) for path in actual_files}
    if actual_hashes != expected_wheels:
        raise Refused("wheelhouse digest mismatch")
    inventory = hashlib.sha256("\n".join(
        f"{name}:{actual_hashes[name]}" for name in sorted(actual_hashes)
    ).encode("ascii")).hexdigest()
    if inventory != expected_wheelhouse:
        raise Refused("wheelhouse inventory digest mismatch")
    return {
        "root": root, "candidate": candidate, "probe": probe,
        "manifest": manifest_path, "wheelhouse": wheelhouse,
        "lock": lock_path, "image": IMAGE,
    }


def validate_image_metadata(raw: str, expected_digest: str = IMAGE_DIGEST) -> None:
    """Accept only the locally inspected pinned image with native amd64 config."""
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise Refused("local image metadata unreadable") from exc
    if not isinstance(value, list) or len(value) != 1 or not isinstance(value[0], dict):
        raise Refused("local image metadata roster mismatch")
    image = value[0]
    if image.get("Os") != "linux" or image.get("Architecture") != "amd64":
        raise Refused("local image architecture mismatch")
    repos = image.get("RepoDigests")
    if not isinstance(repos, list) or not any(
        isinstance(row, str) and row.rsplit("@", 1)[-1] == expected_digest
        and row.rsplit("@", 1)[0] in {"python", "docker.io/library/python"}
        for row in repos
    ):
        raise Refused("local image digest mismatch")


def validate_output_path(output_dir: Path, input_root: Path) -> Path:
    path = output_dir.absolute()
    if path.name in {"", ".", ".."}:
        raise Refused("output directory must name a new child path")
    if path.exists() or path.is_symlink():
        raise Refused("output directory must be new")
    parent = path.parent.resolve(strict=True)
    resolved = parent / path.name
    root = input_root.resolve(strict=True)
    if resolved == root or root in resolved.parents:
        raise Refused("output directory must be outside input bundle")
    return resolved


def docker_argv(docker: str, image: str, input_root: Path, output_dir: Path,
                candidate_sha256: str, container_name: str) -> list[str]:
    return [
        docker, "run", "--pull=never", "--platform=linux/amd64", "--network=none",
        "--read-only", "--rm", "--name", container_name,
        "--memory=2g", "--cpus=2", "--pids-limit=256", "--cap-drop=ALL",
        "--security-opt=no-new-privileges", "--user", f"{os.getuid()}:{os.getgid()}",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=512m,mode=1777",
        "--mount", f"type=bind,src={input_root},dst=/inputs,readonly",
        "--mount", f"type=bind,src={output_dir},dst=/evidence",
        "--workdir", "/evidence",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "PYTHONNOUSERSITE=1",
        "--env", "PIP_CONFIG_FILE=/dev/null",
        "--env", "PIP_NO_INDEX=1",
        "--env", "PIP_NO_CACHE_DIR=1",
        "--env", "PIP_DISABLE_PIP_VERSION_CHECK=1",
        image,
        "python", "-I", "/inputs/verify_installed_tooling.py",
        "--target", TARGET,
        "--manifest", "/inputs/reproducibility/mcp-2.3.0-cp313-linux-amd64.manifest.json",
        "--wheelhouse", "/inputs/wheelhouse",
        "--candidate-wheel", "/inputs/" + CANDIDATE_FILENAME,
        "--candidate-sha256", candidate_sha256,
        "--work-dir", "/evidence/probe-work",
        "--execute-installed",
    ]


@dataclass(frozen=True)
class BoundedCommandResult:
    returncode: int
    timed_out: bool
    output_limited: bool
    stdout: bytes
    stderr: bytes
    stdout_bytes_observed: int
    stderr_bytes_observed: int
    stdout_sha256: str
    stderr_sha256: str
    started_at: str
    finished_at: str
    duration_ms: int


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def run_docker_bounded(argv: list[str], *, timeout: int = MAX_SECONDS) -> BoundedCommandResult:
    """Run the owned Docker child with bounded capture and terminate on limits."""
    if not argv or timeout < 1 or timeout > MAX_SECONDS:
        raise Refused("invalid bounded Docker command")
    started_at = _utc_now()
    started = time.monotonic()
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, close_fds=True)
    assert process.stdout is not None and process.stderr is not None
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ, "stdout")
    selector.register(process.stderr, selectors.EVENT_READ, "stderr")
    traces = {"stdout": bytearray(), "stderr": bytearray()}
    hashes = {"stdout": hashlib.sha256(), "stderr": hashlib.sha256()}
    observed = {"stdout": 0, "stderr": 0}
    timed_out = output_limited = False
    deadline = started + timeout
    try:
        while selector.get_map() or process.poll() is None:
            if time.monotonic() >= deadline:
                timed_out = True
                break
            for key, _ in selector.select(0.1):
                block = os.read(key.fileobj.fileno(), 65536)
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                stream = key.data
                observed[stream] += len(block)
                hashes[stream].update(block)
                remaining = MAX_TRACE_BYTES - len(traces[stream])
                if remaining > 0:
                    traces[stream].extend(block[:remaining])
                if sum(observed.values()) > MAX_DOCKER_OUTPUT_BYTES:
                    output_limited = True
                    break
            if output_limited:
                break
    finally:
        if process.poll() is None and (timed_out or output_limited):
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=2)
        if process.poll() is None:
            process.wait(timeout=2)
        selector.close()
        process.stdout.close()
        process.stderr.close()
    return BoundedCommandResult(
        returncode=process.returncode, timed_out=timed_out, output_limited=output_limited,
        stdout=bytes(traces["stdout"]), stderr=bytes(traces["stderr"]),
        stdout_bytes_observed=observed["stdout"], stderr_bytes_observed=observed["stderr"],
        stdout_sha256=hashes["stdout"].hexdigest(), stderr_sha256=hashes["stderr"].hexdigest(),
        started_at=started_at, finished_at=_utc_now(), duration_ms=int((time.monotonic() - started) * 1000),
    )


def _write_private(path: Path, contents: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def persist_launcher_receipt(output: Path, argv: list[str], container_name: str,
                             result: BoundedCommandResult, cleanup_returncode: int | None,
                             launch_host: dict | None = None) -> Path:
    """Persist mode-0600 bounded transcripts and provenance before parsing JSON."""
    stdout_path, stderr_path = output / "launcher.stdout.bin", output / "launcher.stderr.bin"
    _write_private(stdout_path, result.stdout)
    _write_private(stderr_path, result.stderr)
    record = {
        "schema": "agent-braid-linux-launcher-receipt/v1",
        "status": "timed_out" if result.timed_out else
                  "output_limited" if result.output_limited else
                  "completed" if result.returncode == 0 else "failed",
        "argv": argv,
        "launchHost": launch_host,
        "containerName": container_name,
        "timeoutSeconds": MAX_SECONDS,
        "startedAt": result.started_at,
        "finishedAt": result.finished_at,
        "durationMs": result.duration_ms,
        "returnCode": result.returncode,
        "timedOut": result.timed_out,
        "outputLimited": result.output_limited,
        "stdout": {"path": stdout_path.name, "bytesObserved": result.stdout_bytes_observed,
                   "bytesRetained": len(result.stdout), "sha256Observed": result.stdout_sha256,
                   "truncated": result.stdout_bytes_observed > len(result.stdout)},
        "stderr": {"path": stderr_path.name, "bytesObserved": result.stderr_bytes_observed,
                   "bytesRetained": len(result.stderr), "sha256Observed": result.stderr_sha256,
                   "truncated": result.stderr_bytes_observed > len(result.stderr)},
        "cleanupReturnCode": cleanup_returncode,
    }
    receipt_path = output / "launcher-receipt.json"
    _write_private(receipt_path, (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    return receipt_path


def _inspect_local_image(docker: str) -> None:
    result = subprocess.run(
        [docker, "image", "inspect", IMAGE],
        check=False, capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise Refused("pinned image is not available in the local Docker store")
    validate_image_metadata(result.stdout)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True,
                        help="transport bundle with the frozen wheel, probe, manifest, lock, and wheelhouse")
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="new output directory outside the input bundle")
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--probe-sha256", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--wheelhouse-sha256", required=True)
    parser.add_argument("--launcher-sha256", required=True,
                        help="frozen SHA-256 of this standalone launcher")
    parser.add_argument("--execute", action="store_true",
                        help="run the offline probe in the already-present pinned container image")
    parser.add_argument("--allow-amd64-emulation", action="store_true",
                        help="explicitly allow standalone AMD64 container controls on an ARM64 launch host; not native hardware or registered cohort evidence")
    args = parser.parse_args(argv)
    try:
        if sha256_file(Path(__file__).resolve(strict=True)) != require_sha256(
            args.launcher_sha256, "launcher SHA-256"
        ):
            raise Refused("launcher digest mismatch")
        launch_host = launch_host_identity(platform.system(), platform.machine(),
                                           args.allow_amd64_emulation)
        inputs = validate_manifest_bundle(
            args.input_dir, manifest_sha256=args.manifest_sha256,
            candidate_sha256=args.candidate_sha256, probe_sha256=args.probe_sha256,
            wheelhouse_sha256=args.wheelhouse_sha256,
        )
        output = validate_output_path(args.output_dir, inputs["root"])
        docker = shutil.which("docker")
        if not docker:
            raise Refused("Docker CLI unavailable")
        launch_host["daemon"] = inspect_daemon_identity(docker)
        if not args.allow_amd64_emulation and launch_host["daemon"]["Architecture"] not in {"x86_64", "amd64"}:
            raise Refused("ARM64 Docker daemon requires explicit AMD64 emulation opt-in")
        _inspect_local_image(docker)
        prepared = {
            "status": "prepared", "target": TARGET,
            "image": IMAGE, "candidateSha256": args.candidate_sha256,
            "probeSha256": args.probe_sha256,
            "manifestSha256": args.manifest_sha256,
            "wheelhouseSha256": args.wheelhouse_sha256,
            "executionRequested": args.execute, "launchHost": launch_host,
        }
        if not args.execute:
            print(json.dumps(prepared, sort_keys=True))
            return 0
        output.mkdir(mode=0o700)
        os.chmod(output, 0o700)
        name = "agent-braid-linux-probe-" + uuid.uuid4().hex[:16]
        command = docker_argv(docker, IMAGE, inputs["root"], output,
                              args.candidate_sha256, name)
        result = run_docker_bounded(command)
        cleanup_returncode = None
        if result.timed_out or result.output_limited:
            try:
                cleanup = subprocess.run([docker, "rm", "--force", name], check=False,
                                         capture_output=True, timeout=15)
                cleanup_returncode = cleanup.returncode
            except subprocess.SubprocessError:
                cleanup_returncode = None
        launcher_receipt = persist_launcher_receipt(
            output, command, name, result, cleanup_returncode, launch_host
        )
        launcher_receipt_sha256 = sha256_file(launcher_receipt)
        if result.timed_out:
            print(json.dumps({"status": "timed_out", "timeoutSeconds": MAX_SECONDS,
                              "launcherReceipt": str(launcher_receipt),
                              "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
            return 124
        if result.output_limited:
            print(json.dumps({"status": "output_limited", "returnCode": result.returncode,
                              "launcherReceipt": str(launcher_receipt),
                              "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
            return 2
        if result.returncode != 0:
            print(json.dumps({"status": "failed", "returnCode": result.returncode,
                              "launcherReceipt": str(launcher_receipt),
                              "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
            return result.returncode or 1
        try:
            outcome = json.loads(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError):
            print(json.dumps({"status": "failed", "reason": "probe returned invalid result JSON",
                              "launcherReceipt": str(launcher_receipt),
                              "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
            return 2
        if not isinstance(outcome, dict) or outcome.get("status") != "passed":
            print(json.dumps({"status": "failed", "reason": "probe did not report a pass",
                              "launcherReceipt": str(launcher_receipt),
                              "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
            return 2
        print(json.dumps({"status": "passed", "target": TARGET,
                          "candidateSha256": args.candidate_sha256,
                          "receiptSha256": outcome.get("receiptSha256"),
                          "launcherReceipt": str(launcher_receipt),
                          "launcherReceiptSha256": launcher_receipt_sha256}, sort_keys=True))
        return 0
    except (Refused, OSError, subprocess.SubprocessError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else type(exc).__name__
        print(json.dumps({"status": "blocked", "reason": reason}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
