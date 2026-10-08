#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-038 registered runner API; the command line never starts capture."""
from __future__ import annotations

import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import m4_real_workload as source
from agent_braid import m4_real_workload_trials as trials


def _git(*args: str) -> str:
    """Use the source module's ambient-config-safe Git inspection boundary."""
    return source._git(ROOT, *args)


def _candidate_identity(manifest: dict) -> bool:
    """Check exact clean commit and every code byte bound into the prepared manifest."""
    if _git("rev-parse", "HEAD") != manifest.get("candidateCommit") or _git("status", "--porcelain"):
        return False
    inputs = manifest.get("harnessInputHashes")
    if type(inputs) is not dict or not inputs:
        return False
    for name, digest in inputs.items():
        if (type(name) is not str or name.startswith("/") or ".." in Path(name).parts
                or "\\" in name or type(digest) is not str or len(digest) != 64):
            return False
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            return False
    return True


def _write_new(path: Path, value: dict, *, scope: str) -> dict:
    """Time aggregate encoding, fsync and output outside treatment intervals."""
    wall, cpu = time.monotonic_ns(), time.process_time_ns()
    raw = trials.encode(value)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"wallNs": time.monotonic_ns() - wall,
            "parentCpuNs": time.process_time_ns() - cpu,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "scope": scope}


def _environment_observation() -> dict:
    """Capture runtime toolchain metadata without executing any workload source."""
    start_wall, start_cpu = time.monotonic_ns(), time.process_time_ns()
    operating_system = {"platform": sys.platform, "name": os.name}
    if hasattr(os, "uname"):
        uname = os.uname()
        operating_system.update(system=uname.sysname, release=uname.release, machine=uname.machine)
    git_version, git_error = None, None
    try:
        git_version = _git("--version")
    except Exception as exc:
        git_error = f"{type(exc).__name__}: {exc}"
    return {
        "python": {"version": platform.python_version(),
                   "implementation": platform.python_implementation()},
        "git": {"version": git_version, "error": git_error,
                "inspection": "safe source-module Git helper; metadata query only"},
        "operatingSystem": operating_system,
        "timing": {"wallNs": time.monotonic_ns() - start_wall,
                   "parentCpuNs": time.process_time_ns() - start_cpu,
                   "scope": "environment metadata observation outside treatment ratios"},
        "boundary": "Metadata only; no actual workload source or fixture code executed.",
    }


def _callback_factory(manifest: dict, identity_check):
    """Make a callback only after `run_trials` has authenticated both gates."""
    repository = Path(manifest["sourceRepository"]).resolve(strict=True)
    source_receipt = manifest["sourceFingerprint"]
    start_wall, start_cpu = time.monotonic_ns(), time.process_time_ns()

    def callback(slot: dict) -> dict:
        return trials.run_treatment(
            slot, input_factory=lambda: source.runtime_inputs_for_slot(manifest, slot),
            source_repository=repository, source_fingerprint=source_receipt,
            source_integrity_check=source.source_fingerprint,
            identity_check=identity_check)

    receipt = {"scope": "callback construction only; no fixture copy, grant, or runtime treatment",
               "wallNs": time.monotonic_ns() - start_wall,
               "parentCpuNs": time.process_time_ns() - start_cpu,
               "fixtureCopies": 0}
    return callback, receipt


def run_registered_capture(*, manifest_path: Path, review_path: Path,
                           capture_authorization_path: Path, output_path: Path,
                           authority_verifier) -> dict:
    """Caller-only capture API with no CLI shortcut or self-asserted authority.

    The authority verifier must authenticate both exact decision records using a
    trusted human/organization channel. It must also bind the separately frozen
    candidate and exact manifest bytes. The shipped CLI intentionally refuses
    capture; this function is unusable while the separate capture record is absent.
    """
    raw = manifest_path.read_bytes()
    manifest = source.validate_manifest(raw)
    manifest.setdefault("manifestSha256", hashlib.sha256(raw).hexdigest())
    out = output_path.expanduser().absolute()
    if os.path.lexists(out) or out.name in {"", ".", ".."}:
        raise ValueError("capture output must be a fresh file")
    out = out.parent.resolve(strict=True) / out.name
    protected_roots = (ROOT.resolve(), Path(manifest["sourceRepository"]).resolve(),
                       Path(manifest["sourceFingerprint"]["commonDirectory"]).resolve())
    verify_out = out.with_name(out.name + ".fresh-verification.json")
    observer_out = out.with_name(out.name + ".observer.json")
    tail_out = out.with_name(out.name + ".observer-tail.json")
    companion_paths = (verify_out, observer_out, tail_out)
    if any(os.path.lexists(path) for path in companion_paths):
        raise ValueError("fresh-verification and observer companion outputs must also be fresh")
    outputs = (out, *companion_paths)
    destinations = tuple(Path(slot[key]) for slot in manifest["slots"]
                         for key in ("runPath", "grantPath"))
    for output in outputs:
        resolved_output = output.resolve(strict=False)
        if any(resolved_output == protected or resolved_output.is_relative_to(protected)
               or protected.is_relative_to(resolved_output) for protected in protected_roots):
            raise ValueError("capture outputs must not overlap candidate, source, or Git common storage")
        for destination in destinations:
            resolved_destination = destination.resolve(strict=False)
            if (resolved_output == resolved_destination or resolved_output.is_relative_to(resolved_destination)
                    or resolved_destination.is_relative_to(resolved_output)):
                raise ValueError("capture outputs must not overlap future treatment destinations")
    review_raw = review_path.read_bytes()
    capture_raw = capture_authorization_path.read_bytes()
    manifest_digest = hashlib.sha256(raw).hexdigest()

    def identity_check():
        try:
            return (_candidate_identity(manifest)
                    and hashlib.sha256(manifest_path.read_bytes()).hexdigest() == manifest_digest)
        except OSError:
            return False

    def callback_factory(authorized_manifest):
        return _callback_factory(authorized_manifest, identity_check)

    record = trials.run_trials(
        manifest_raw=raw, manifest=manifest, manifest_validator=source.validate_manifest,
        review_raw=review_raw,
        capture_authorization_raw=capture_raw, authority_verifier=authority_verifier,
        identity_check=identity_check, callback_factory=callback_factory)
    record["manifestPath"] = str(manifest_path.resolve())
    record["verificationBoundary"] = "fresh-process verification is a separate read-only pass"
    record["gitCommandCounterBoundary"] = {
        "scope": "Runtime/replay command counters are bounded to their instrumented execution registries.",
        "excluded": "Candidate identity guards and source-integrity fingerprint checks also issue safe Git inspection commands; these are not included in the runtime/replay command counters.",
        "candidateIdentityGitCommandCount": {"value": None, "reason": "Guard command count is not separately instrumented; candidate identity is checked at bounded dispatch guards."},
        "sourceIntegrityGitCommandCount": {"value": None, "reason": "Source fingerprint Git command count is not separately instrumented; checks are made in existing treatment integrity phases."},
        "measurement": "Guard and integrity-check wall time is reflected in treatment input/residual or outer verification spans, not attributed as runtime/replay command-budget usage.",
    }
    record["environmentObservation"] = _environment_observation()
    trial_output_observation = _write_new(out, record,
                                          scope="shared trial record encode/output after all per-treatment clocks")
    verify_started = time.monotonic_ns()
    process = None
    verifier_error = None
    try:
        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts/verify_m4_real_workload.py"),
             "--manifest", str(manifest_path.resolve()), "--record", str(out), "--output", str(verify_out)],
            capture_output=True, text=True, check=False)
    except Exception as exc:
        verifier_error = f"{type(exc).__name__}: {exc}"
    verification_wall_ns = time.monotonic_ns() - verify_started
    verification_raw = verify_out.read_bytes() if verify_out.is_file() else None
    verification = None
    verification_parse_error = None
    if verification_raw is not None:
        try:
            verification = json.loads(verification_raw)
        except (ValueError, UnicodeError) as exc:
            verification_parse_error = f"{type(exc).__name__}: {exc}"
    verifier_returncode = None if process is None else process.returncode
    verification_passed = (verifier_returncode == 0 and type(verification) is dict
                           and verification.get("status") == "verified")
    cleanup_started = time.monotonic_ns()
    cleanup_cpu = time.process_time_ns()
    cleanup_errors = []
    owned_paths = {Path(slot[key]) for slot in manifest["slots"] for key in ("runPath", "grantPath")}
    source_root = Path(manifest["sourceRepository"]).resolve()
    common_root = Path(manifest["sourceFingerprint"]["commonDirectory"]).resolve()
    candidate_root = ROOT.resolve()
    removed_paths = 0
    cleanup_skip_reason = None
    if not verification_passed:
        cleanup_skip_reason = "fresh verifier did not exit successfully with a verified receipt; retain run/grant evidence"
    elif record.get("status") != "complete":
        cleanup_skip_reason = ("capture status is " + str(record.get("status"))
                               + "; retain run/grant evidence for review")
    else:
        for path in owned_paths:
            if not os.path.lexists(path):
                continue
            resolved = path.resolve(strict=False)
            if (path.is_symlink() or resolved == source_root or resolved.is_relative_to(source_root)
                    or resolved == common_root or resolved.is_relative_to(common_root)
                    or resolved == candidate_root or resolved.is_relative_to(candidate_root)
                    or path.stat().st_uid != os.getuid() or (path.stat().st_mode & 0o777) != 0o700):
                cleanup_errors.append(str(path) + ": refused unsafe or unowned path")
                continue
            try:
                shutil.rmtree(path)
                removed_paths += 1
            except OSError as exc:
                cleanup_errors.append(str(path) + ": " + str(exc))
    cleanup_wall_ns = time.monotonic_ns() - cleanup_started
    cleanup_cpu_ns = time.process_time_ns() - cleanup_cpu
    observer = {"recordVersion": "agent-braid-m4-real-workload-observer-v1",
                "trialRecord": str(out), "trialRecordSha256": trial_output_observation["sha256"],
                "trialOutputObservation": trial_output_observation,
                "freshVerification": {"path": str(verify_out),
                                      "sha256": None if verification_raw is None else hashlib.sha256(verification_raw).hexdigest(),
                                      "status": None if verification is None else verification.get("status"),
                                      "wallNs": verification_wall_ns,
                                      "processReturnCode": verifier_returncode,
                                      "processError": verifier_error,
                                      "receiptParseError": verification_parse_error,
                                      "stdoutTail": None if process is None else process.stdout[-1000:],
                                      "stderrTail": None if process is None else process.stderr[-1000:],
                                      "scope": "separate Python process; outside treatment ratios"},
                "finalArtifactCleanup": {"wallNs": cleanup_wall_ns, "parentCpuNs": cleanup_cpu_ns,
                                         "removedTreatmentPaths": removed_paths,
                                         "errors": cleanup_errors,
                                         "skipped": cleanup_skip_reason is not None,
                                         "skipReason": cleanup_skip_reason,
                                         "scope": "only after successful fresh-process verification; otherwise all run/grant evidence is retained"},
                "boundary": "Shared output, fresh-process verification, conditional final private cleanup and this receipt are outside per-treatment ratios."}
    observer_write = _write_new(observer_out, observer,
                                scope="shared observer sealing/output outside treatment and cleanup spans")
    tail = {"recordVersion": "agent-braid-m4-real-workload-observer-tail-v1",
            "observerPath": str(observer_out), "observerSha256": observer_write["sha256"],
            "observerOutput": observer_write,
            "boundary": "This companion is written after the observer's measured output span; its own write is not included."}
    tail_write = _write_new(tail_out, tail,
                            scope="subsequent publication of the closed observer output receipt")
    if not verification_passed:
        raise RuntimeError("fresh-process verification failed or was inconclusive; evidence retained and observer receipts written")
    if cleanup_errors:
        raise RuntimeError("final artifact cleanup incomplete; see observer receipts")
    record["observerOutput"] = observer_write
    record["observerTailOutput"] = tail_write
    return record


def main(argv=None) -> int:
    print(json.dumps({"status": "refused", "registeredCaptureAuthorized": False,
                      "reason": "CLI capture is disabled; require separately authenticated exact stable-harness review and capture authorization through the library caller boundary."}),
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
