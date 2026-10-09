#!/usr/bin/env python3
"""Run the frozen, offline SPEC-044 T003 oracle matrix.

This runner invokes only named repository unittest methods. It does not contact
providers or hosts and does not accept fixture, grant, source, or shell input.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import selectors
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any


SCHEMA = "agent-braid/spec-044-t003-controls/v1"
MAX_TIMEOUT_SECONDS = 300
MAX_CAPTURE_BYTES = 256 * 1024

# Exact independent test methods are the oracles. Their assertions, rather than
# a count of green tests, define each expected result.
CASES: tuple[dict[str, str], ...] = (
    {
        "id": "parity-positive",
        "category": "parity",
        "role": "positive",
        "test": "tests.test_tooling_fixtures.ToolingFixtureTests.test_runtime_fixture_materializes_valid_request_and_read_only_prepare_parity",
        "oracle": "Fixture definition and request hashes match; core and runtime analysis outputs are equal; MCP prepare is ok and byte-for-value equal to the runtime plan; prepare creates no run and no grant.",
    },
    {
        "id": "malformed-refusal",
        "category": "malformed",
        "role": "refusal",
        "test": "tests.test_tooling_mcp.ToolingServiceTests.test_service_validates_call_shape_and_operation_bounds_itself",
        "oracle": "Malformed AIM input and a 33-operation request both return status refused with the exact input-schema and 32-operation refusal indicators.",
    },
    {
        "id": "stale-and-unknown-refusal",
        "category": "stale",
        "role": "refusal",
        "test": "tests.test_tooling_subscription.SubscriptionPolicyTests.test_rejects_paid_unknown_inactive_stale_and_cross_slot_states",
        "oracle": "Paid, unknown, inactive, stale, and cross-slot synthetic subscription observations are rejected by the subscription policy.",
    },
    {
        "id": "fresh-subscription-positive",
        "category": "stale",
        "role": "positive",
        "test": "tests.test_tooling_subscription.SubscriptionPolicyTests.test_valid_observation_and_freshness",
        "oracle": "A fresh, correctly bound synthetic included-subscription observation is accepted and remains bound to its account and observation source.",
    },
    {
        "id": "capture-caps-positive",
        "category": "stale-caps",
        "role": "positive",
        "test": "tests.test_tooling_supervisor.ToolingSupervisorTests.test_subscription_only_preflight_and_periodic_stop",
        "oracle": "A fresh synthetic subscription proof permits the bounded local process; a later over-cap observation stops it and preserves a partial measurement rather than claiming completion.",
    },
    {
        "id": "capture-stale-unknown-refusal",
        "category": "stale-caps",
        "role": "refusal",
        "test": "tests.test_tooling_supervisor.ToolingSupervisorTests.test_prelaunch_caps_staleness_incident_and_unknown_refuse_without_start",
        "oracle": "Stale, unknown-cost, incident, and unrecoverable prelaunch observations refuse before process start and retain measurement-unknown where applicable.",
    },
    {
        "id": "unsafe-root-refusal",
        "category": "unsafe-root",
        "role": "refusal",
        "test": "tests.test_tooling_fixtures.ToolingFixtureTests.test_materializer_refuses_existing_symlink_outside_temp_and_wrong_kind",
        "oracle": "Existing destination, symlink destination, repository-outside-temp destination, and non-runtime fixture are refused before creating the refused destinations.",
    },
    {
        "id": "disjoint-grant-roots",
        "category": "unsafe-root",
        "role": "positive",
        "test": "tests.test_tooling_mcp.ToolingServiceTests.test_results_and_grants_are_disjoint_from_every_allowlisted_worktree",
        "oracle": "Disjoint synthetic result/grant roots are accepted; nested, aliased, and overlapping roots are rejected against every allowlisted worktree.",
    },
    {
        "id": "grant-positive-execute-verify",
        "category": "grant",
        "role": "positive",
        "test": "tests.test_tooling_fixtures.ToolingFixtureTests.test_execute_fixture_positive_synthetic_grant_execute_status_verify_control",
        "oracle": "A fixture-owned synthetic operator grant permits execute; runtime status and verify both report verified-completed and the result tree equals the fixture oracle.",
    },
    {
        "id": "grant-missing-and-stale-refusal",
        "category": "grant",
        "role": "refusal",
        "test": "tests.test_tooling_mcp.SyntheticRuntimeSequenceTests.test_existing_runtime_prepare_grant_execute_status_verify_and_refusal_guards",
        "oracle": "Out-of-root prepare, stale plan, missing/expired grant are refused or unknown without creating the run; only an exact grant executes, verifies, and cannot be silently reused.",
    },
    {
        "id": "missing-grant-capture-context",
        "category": "grant",
        "role": "refusal",
        "test": "tests.test_tooling_capture.CaptureAdmissionTests.test_missing_grant_journey_has_explicitly_absent_grant_context",
        "oracle": "The refusal journey retains missing-grant mode with null grant reference and digest; no grant is inferred from host permission.",
    },
    {
        "id": "grant-mismatch-capture-refusal",
        "category": "grant",
        "role": "refusal",
        "test": "tests.test_tooling_capture.CaptureAdmissionTests.test_missing_or_mismatched_existing_grant_context_refuses",
        "oracle": "Missing or mismatched exact existing grant references/actions are rejected at capture admission; a host permission setting does not fill the grant context.",
    },
    {
        "id": "cancelled-request-refusal",
        "category": "cancellation",
        "role": "refusal",
        "test": "tests.test_tooling_mcp.ToolingServiceTests.test_cancelled_request_never_dispatches",
        "oracle": "A pre-cancelled analysis request returns refused with null result and does not dispatch.",
    },
    {
        "id": "dispatched-cancellation-checkpoint",
        "category": "cancellation",
        "role": "in-flight",
        "test": "tests.test_tooling_mcp.WorkerCancellationTests.test_cancellation_waits_for_dispatched_worker_checkpoint",
        "oracle": "The application-level asyncio caller is cancelled only after the stdlib worker dispatch signal is observed; cancellation waits for worker completion at its checkpoint before propagating. This is not an SDK transport control.",
    },
    {
        "id": "uncancelled-request-positive",
        "category": "cancellation",
        "role": "positive",
        "test": "tests.test_tooling_mcp.ToolingServiceTests.test_analyze_work_preserves_core_result_and_advisory_boundary",
        "oracle": "An uncancelled valid analysis returns ok with exact independent-candidate core classification, executionAuthorization false, and input provenance digest.",
    },
    {
        "id": "recovery-positive-after-interruption",
        "category": "recovery",
        "role": "positive",
        "test": "tests.test_tooling_fixtures.ToolingFixtureTests.test_recovery_fixture_positive_synthetic_interrupted_run_resume_and_verify_control",
        "oracle": "Synthetic checkpoint interruption remains unknown/refused and inspectable; exact resume grant recovers, then verify reports verified-completed with the expected fixture result tree.",
    },
    {
        "id": "output-agreement-positive",
        "category": "output-agreement",
        "role": "positive",
        "test": "tests.test_tooling_present.ExportTests.test_complete_result_json_matches_for_raw_and_enveloped_values",
        "oracle": "Canonical result JSON is exactly equal for a raw result and its envelope; a one-value mutation produces a different canonical result.",
    },
    {
        "id": "output-export-positive",
        "category": "output-agreement",
        "role": "positive",
        "test": "tests.test_tooling_present.ExportTests.test_exports_are_deterministic_safe_and_keep_complete_evidence_separate",
        "oracle": "Repeated exports are byte-identical, preserve complete evidence separately, and exclude injected script, path, private-repository, and terminal-control content.",
    },
    {
        "id": "output-unowned-refusal",
        "category": "output-agreement",
        "role": "refusal",
        "test": "tests.test_tooling_present.ExportTests.test_export_requires_explicit_selection_and_refuses_unowned_references",
        "oracle": "Missing selection and an unowned evidence reference both raise PresentationError.",
    },
)

MANDATORY_CATEGORIES: dict[str, dict[str, Any]] = {
    "parity": {"caseIds": ["parity-positive"], "expected": "core/runtime/MCP prepare exact value agreement and zero run/grant writes"},
    "malformed": {"caseIds": ["parity-positive", "malformed-refusal"], "expected": "valid bounded input parity; malformed shape and over-limit input are refused"},
    "stale": {"caseIds": ["fresh-subscription-positive", "stale-and-unknown-refusal"], "expected": "fresh bound observation accepted; paid/unknown/inactive/stale/cross-slot observations rejected"},
    "stale-caps": {"caseIds": ["capture-caps-positive", "capture-stale-unknown-refusal"], "expected": "fresh bounded preflight may start; stale/unknown/incident/exceeded observations refuse or stop without false completion"},
    "unsafe-root": {"caseIds": ["disjoint-grant-roots", "unsafe-root-refusal"], "expected": "disjoint owned roots accepted; symlink, existing, out-of-temp and overlapping paths refused before unsafe writes"},
    "grant": {"caseIds": ["grant-positive-execute-verify", "grant-missing-and-stale-refusal", "missing-grant-capture-context", "grant-mismatch-capture-refusal"], "expected": "fixture-owned exact grant can execute/verify; missing, expired, stale, mismatched or absent grant context cannot authorize execution"},
    "cancellation": {"caseIds": ["uncancelled-request-positive", "cancelled-request-refusal", "dispatched-cancellation-checkpoint"], "expected": "uncancelled valid analysis succeeds; pre-cancelled input does not dispatch; dispatched worker reaches its checkpoint before cancellation returns"},
    "recovery": {"caseIds": ["recovery-positive-after-interruption"], "expected": "interrupted prefix is retained and inspectable; exact resume grant reaches expected verified result"},
    "output-agreement": {"caseIds": ["output-agreement-positive", "output-export-positive", "output-unowned-refusal"], "expected": "canonical result equality and deterministic safe export; changed value differs and unowned evidence is refused"},
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("ascii")


def _write_private(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_private(path: Path, data: bytes) -> None:
    temporary = path.with_name(path.name + ".pending")
    _write_private(temporary, data)
    os.replace(temporary, path)
    path.chmod(0o600)


def _source_paths(repo: Path) -> list[Path]:
    paths: set[Path] = set()
    for directory in (repo / "agent_braid", repo / "examples" / "tooling", repo / "tests"):
        if not directory.is_dir():
            raise RuntimeError(f"required source directory missing: {directory.relative_to(repo)}")
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise RuntimeError(f"symlink in frozen source inventory: {path.relative_to(repo)}")
            if path.is_file() and "__pycache__" not in path.parts:
                paths.add(path)
    explicit = {
        "examples/analysis/file-edits.json",
        "specs/044-ai-tooling-evaluation/evaluation-protocol.md",
        "scripts/run_tooling_controls.py",
        "docs/tooling/CONTROLS.md",
        "pyproject.toml",
    }
    for relative in explicit:
        path = repo / relative
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"required frozen input missing or unsafe: {relative}")
        paths.add(path)
    return sorted(paths, key=lambda item: item.relative_to(repo).as_posix())


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], check=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                            timeout=10)
    return result.stdout.strip()


def _freeze(repo: Path) -> dict[str, Any]:
    commit = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "branch", "--show-current")
    status_before = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    source_files = _source_paths(repo)
    entries = []
    for path in source_files:
        relative = path.relative_to(repo).as_posix()
        data = path.read_bytes()
        entries.append({"path": relative, "sizeBytes": len(data), "sha256": _sha(data)})
    # Refuse a moving input set instead of freezing a mixed snapshot.
    changed_during_freeze = []
    for entry, path in zip(entries, source_files):
        if not path.is_file() or path.is_symlink() or _sha(path.read_bytes()) != entry["sha256"]:
            changed_during_freeze.append(entry["path"])
    status_after = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if (changed_during_freeze or status_before != status_after
            or commit != _git(repo, "rev-parse", "HEAD")):
        raise RuntimeError("candidate source/status changed while freezing the manifest")
    git_version = subprocess.run(["git", "--version"], check=True, capture_output=True,
                                  text=True, timeout=10).stdout.strip()
    distributions = sorted(
        ({"name": distribution.metadata.get("Name", "unknown"), "version": distribution.version}
         for distribution in importlib.metadata.distributions()),
        key=lambda item: (item["name"].casefold(), item["version"]),
    )
    return {
        "schema": SCHEMA,
        "evidenceType": "synthetic-protocol-peer-control-run",
        "createdAtUtc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate": {
            "commit": commit,
            "branch": branch,
            "workingTreeStatusPorcelain": status_before,
            "sourceManifest": entries,
            "sourceManifestSha256": _sha(_json_bytes(entries)),
            "runnerSha256": _sha((repo / "scripts/run_tooling_controls.py").read_bytes()),
            "fixtureInputPaths": [item["path"] for item in entries
                                  if item["path"].startswith("examples/tooling/")
                                  or item["path"] == "examples/analysis/file-edits.json"],
        },
        "execution": {
            "kind": "unittest-control-source",
            "pythonVersion": platform.python_version(),
            "platform": platform.platform(),
            "gitVersion": git_version,
            "installedDistributions": distributions,
            "providerCalls": 0,
            "hostAcceptanceClaimed": False,
            "caseCommands": [
                {"caseId": case["id"], "argv": [sys.executable, "-m", "unittest", "-v", case["test"]]}
                for case in CASES
            ],
        },
        "mandatoryCategories": MANDATORY_CATEGORIES,
        "cases": [dict(case, expectedProcessOutcome="exit 0", status="not-started") for case in CASES],
        "limits": [
            "Synthetic local control evidence only; no actual Codex/Claude host, provider, clean-room, or human observation.",
            "Expected semantics are asserted by the exact named unittest methods; a process exit alone is not the domain oracle.",
            "A passing matrix does not establish scientific validity, production safety, utility, or owner acceptance.",
        ],
    }


PROCESS_GRACE_SECONDS = 0.5
PIPE_DRAIN_SECONDS = 0.25


def _wait_events(selector: selectors.BaseSelector, timeout: float) -> list[Any]:
    return selector.select(timeout)


def _group_state(pgid: int) -> str:
    """Return present/absent/unknown without signaling a non-owned group."""
    if os.name != "posix":
        return "unknown"
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return "absent"
    except PermissionError:
        return "unknown"
    return "present"


def _signal_owned_group(process: subprocess.Popen[bytes], sig: int) -> str:
    if os.name != "posix":
        try:
            process.send_signal(sig)
            return "sent"
        except ProcessLookupError:
            return "absent"
        except OSError:
            return "unknown"
    # start_new_session=True makes this pid the unique process-group ID.
    try:
        os.killpg(process.pid, sig)
        return "sent"
    except ProcessLookupError:
        return "absent"
    except OSError:
        return "unknown"


def _cleanup_owned_group(process: subprocess.Popen[bytes], grace: float = PROCESS_GRACE_SECONDS) -> dict[str, Any]:
    """Terminate only the process group created by this runner; bound all waits."""
    if os.name != "posix":
        try:
            process.terminate()
        except OSError:
            pass
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            return {"termSent": False, "killSent": False, "state": "unknown", "returnCode": None}
        return {"termSent": True, "killSent": True, "state": "unknown", "returnCode": process.returncode}

    term = _signal_owned_group(process, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        process.poll()  # Reap the direct child when possible.
        state = _group_state(process.pid)
        if state == "absent":
            break
        time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))
    state_after_term = _group_state(process.pid)
    kill = "absent"
    if state_after_term != "absent":
        kill = _signal_owned_group(process, signal.SIGKILL)
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        return {"termSent": term == "sent", "killSent": kill == "sent",
                "state": "unknown", "returnCode": None}
    deadline = time.monotonic() + 1.0
    state = _group_state(process.pid)
    while state == "present" and time.monotonic() < deadline:
        time.sleep(0.025)
        state = _group_state(process.pid)
    if state != "absent":
        state = "unknown"
    return {"termSent": term == "sent", "killSent": kill == "sent",
            "state": state, "returnCode": process.returncode}


def _run_process(argv: list[str], repo: Path, timeout: int) -> dict[str, Any]:
    process = subprocess.Popen(argv, cwd=repo, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               shell=False, close_fds=True,
                               start_new_session=(os.name == "posix"))
    if process.stdout is None or process.stderr is None:
        _cleanup_owned_group(process)
        raise RuntimeError("owned process pipes were not created")
    selector = selectors.DefaultSelector()
    captures = {"stdout": bytearray(), "stderr": bytearray()}
    pipe_errors: list[str] = []
    try:
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        deadline = time.monotonic() + timeout
        leader_done_at: float | None = None
        leaked_group = False
        timed_out = False
        drain_incomplete = False
        return_code: int | None = None
        while selector.get_map() or process.poll() is None:
            return_code = process.poll()
            now = time.monotonic()
            if return_code is not None and leader_done_at is None:
                leader_done_at = now
                group = _group_state(process.pid)
                if group != "absent":
                    leaked_group = True
                    cleanup = _cleanup_owned_group(process)
                    if cleanup["state"] != "absent":
                        drain_incomplete = True
                    leader_done_at = time.monotonic()
            if return_code is None and now >= deadline:
                timed_out = True
                cleanup = _cleanup_owned_group(process)
                if cleanup["state"] != "absent":
                    drain_incomplete = True
                return_code = process.returncode
                leader_done_at = time.monotonic()
            if return_code is not None and leader_done_at is not None and now - leader_done_at >= PIPE_DRAIN_SECONDS:
                if selector.get_map():
                    drain_incomplete = True
                    leaked_group = leaked_group or _group_state(process.pid) != "absent"
                    cleanup = _cleanup_owned_group(process)
                    if cleanup["state"] != "absent":
                        pipe_errors.append("owned process group remained present or unobservable after cleanup")
                    for key in list(selector.get_map().values()):
                        try:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                        except OSError:
                            pass
                break
            if not selector.get_map() and return_code is not None:
                break
            next_deadline = deadline if return_code is None else (leader_done_at or now) + PIPE_DRAIN_SECONDS
            wait_for = max(0.0, min(0.05, next_deadline - now))
            for key, _ in _wait_events(selector, wait_for):
                try:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                except OSError as exc:
                    pipe_errors.append(f"{key.data} read failed: {type(exc).__name__}")
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                kept = captures[key.data]
                remaining = MAX_CAPTURE_BYTES - len(kept)
                if remaining > 0:
                    kept.extend(chunk[:remaining])
        return_code = process.poll()
        group_state = _group_state(process.pid) if os.name == "posix" else "unknown"
        skipped = any(
            re.search(r"(?m)^" + re.escape(case_name) + r" \([^\n]*\) \.\.\. skipped(?: |$)",
                      captures["stderr"].decode("utf-8", errors="replace"))
            for case_name in ("test_" + argv[-1].rsplit(".test_", 1)[-1],)
        )
        if timed_out:
            status = "timeout"
        elif leaked_group or drain_incomplete or pipe_errors or group_state != "absent":
            status = "cleanup-unknown" if group_state != "absent" or pipe_errors else "failed"
        elif skipped:
            status = "unavailable"
        else:
            status = "passed" if return_code == 0 else "failed"
        return {
            "status": status,
            "returnCode": return_code,
            "timedOut": timed_out,
            "ownedProcessGroupId": process.pid if os.name == "posix" else None,
            "ownedProcessGroupState": group_state,
            "lingeringDescendantDetected": leaked_group,
            "pipeDrainIncomplete": drain_incomplete,
            "pipeErrors": pipe_errors,
            "skipDetected": skipped,
            "stdout": bytes(captures["stdout"]).decode("utf-8", errors="replace"),
            "stderr": bytes(captures["stderr"]).decode("utf-8", errors="replace"),
            "stdoutBytesRetained": len(captures["stdout"]),
            "stderrBytesRetained": len(captures["stderr"]),
            "outputTruncated": len(captures["stdout"]) == MAX_CAPTURE_BYTES or len(captures["stderr"]) == MAX_CAPTURE_BYTES,
            "argv": argv,
        }
    except BaseException as exc:
        cleanup = _cleanup_owned_group(process)
        try:
            setattr(exc, "owned_process_cleanup", cleanup)
        except Exception:
            pass
        raise
    finally:
        selector.close()
        for stream in (process.stdout, process.stderr):
            try:
                stream.close()
            except OSError:
                pass


def _execute_case(repo: Path, case: dict[str, str], timeout: int) -> dict[str, Any]:
    argv = [sys.executable, "-m", "unittest", "-v", case["test"]]
    result = _run_process(argv, repo, timeout)
    return result


def _verify_result_root(root: Path) -> list[str]:
    errors: list[str] = []
    if root.is_symlink() or not root.is_dir():
        return ["result root is missing, not a directory, or a symlink"]
    if root.stat().st_mode & 0o777 != 0o700:
        errors.append("result root mode is not 0700")
    directories = {path.relative_to(root).as_posix(): path for path in root.rglob("*") if path.is_dir()}
    if set(directories) != {"cases"}:
        errors.append("result directory inventory differs from the required layout")
    for relative, path in directories.items():
        if path.is_symlink() or path.stat().st_mode & 0o777 != 0o700:
            errors.append(f"result directory is aliased or not private: {relative}")
    try:
        integrity = json.loads((root / "integrity.json").read_text(encoding="ascii"))
    except (OSError, ValueError):
        return errors + ["integrity index is missing or malformed"]
    expected = integrity.get("files")
    if not isinstance(expected, list):
        return errors + ["integrity file list is malformed"]
    expected_paths = {row.get("path") for row in expected if isinstance(row, dict)}
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "integrity.json"}
    if expected_paths != actual_paths:
        errors.append("result file inventory differs from integrity index")
    try:
        manifest_bytes = (root / "manifest.json").read_bytes()
        manifest = json.loads(manifest_bytes)
        receipt = json.loads((root / "receipt.json").read_text(encoding="ascii"))
    except (OSError, ValueError):
        return errors + ["manifest or receipt is missing or malformed"]
    if manifest.get("schema") != SCHEMA or receipt.get("schema") != SCHEMA:
        errors.append("result schema identifier is unexpected")
    if receipt.get("manifestSha256") != _sha(manifest_bytes):
        errors.append("receipt does not bind the retained manifest")
    manifest_case_ids = [row.get("id") for row in manifest.get("cases", []) if isinstance(row, dict)]
    if manifest_case_ids != [case["id"] for case in CASES]:
        errors.append("manifest case inventory or order differs from the required matrix")
    case_states = receipt.get("cases")
    if not isinstance(case_states, dict) or set(case_states) != {case["id"] for case in CASES}:
        errors.append("receipt does not retain every intended case")
    if receipt.get("status") == "passed" and (
            not isinstance(case_states, dict)
            or any(case_states.get(case["id"]) != "passed" for case in CASES)
            or receipt.get("failureLedger") or receipt.get("sourceChanges")):
        errors.append("passed receipt has failed, missing, or changed evidence")
    for row in expected:
        relative = row.get("path")
        if not isinstance(relative, str) or relative.startswith("/") or ".." in Path(relative).parts:
            errors.append("integrity index contains unsafe path")
            continue
        path = root / relative
        if path.is_symlink() or not path.is_file():
            errors.append(f"result file missing or unsafe: {relative}")
            continue
        if path.stat().st_mode & 0o777 != 0o600:
            errors.append(f"result file mode is not 0600: {relative}")
        if _sha(path.read_bytes()) != row.get("sha256"):
            errors.append(f"result file hash mismatch: {relative}")
    return errors


def _run(repo: Path, output_root: Path, timeout: int) -> int:
    repo = repo.resolve(strict=True)
    parent = output_root.parent.resolve(strict=True)
    target = parent / output_root.name
    if target == repo or repo in target.parents or target in repo.parents:
        raise ValueError("result root must be disjoint from repository source")
    if target.exists() or target.is_symlink():
        raise FileExistsError("result root must be a new exclusive directory")
    frozen = _freeze(repo)
    manifest_data = _json_bytes(frozen)
    manifest_hash = _sha(manifest_data)
    target.mkdir(mode=0o700)
    target.chmod(0o700)
    cases_dir = target / "cases"
    cases_dir.mkdir(mode=0o700)
    _write_private(target / "manifest.json", manifest_data)
    _write_private(target / "receipt.json", _json_bytes({
        "schema": SCHEMA,
        "manifestSha256": manifest_hash,
        "status": "running",
        "cases": {case["id"]: "not-started" for case in CASES},
        "failureLedger": [],
    }))
    for case in CASES:
        case_file = cases_dir / f"{case['id']}.json"
        row: dict[str, Any] = {**case, "status": "not-started", "expectedProcessOutcome": "exit 0"}
        _write_private(case_file, _json_bytes(row))
    final_status = "passed"
    failures: list[dict[str, str]] = []
    interrupted = False
    for case in CASES:
        row_path = cases_dir / f"{case['id']}.json"
        row = json.loads(row_path.read_text(encoding="ascii"))
        row["status"] = "running"
        _atomic_private(row_path, _json_bytes(row))
        try:
            execution = _execute_case(repo, case, timeout)
        except KeyboardInterrupt as exc:
            execution = {
                "status": "interrupted",
                "errorType": "KeyboardInterrupt",
                "ownedProcessCleanup": getattr(exc, "owned_process_cleanup", {"state": "unknown"}),
            }
            interrupted = True
        except Exception as exc:  # Preserve case identity even for runner faults.
            execution = {"status": "error", "errorType": type(exc).__name__, "error": str(exc)[:1000]}
        row.update(execution)
        _atomic_private(row_path, _json_bytes(row))
        if execution["status"] != "passed":
            final_status = "incomplete"
            failures.append({"caseId": case["id"], "status": execution["status"]})
        receipt = {
            "schema": SCHEMA,
            "manifestSha256": manifest_hash,
            "status": "incomplete" if interrupted else "running",
            "cases": {item["id"]: json.loads((cases_dir / f"{item['id']}.json").read_text(encoding="ascii"))["status"] for item in CASES},
            "failureLedger": failures,
        }
        _atomic_private(target / "receipt.json", _json_bytes(receipt))
        if interrupted:
            break
    source_changes = []
    for source in frozen["candidate"]["sourceManifest"]:
        current = repo / source["path"]
        if not current.is_file() or current.is_symlink() or _sha(current.read_bytes()) != source["sha256"]:
            source_changes.append(source["path"])
    if source_changes:
        final_status = "incomplete"
        failures.append({"caseId": "source-integrity", "status": "changed"})
    final_receipt = {
        "schema": SCHEMA,
        "manifestSha256": manifest_hash,
        "status": final_status,
        "cases": {item["id"]: json.loads((cases_dir / f"{item['id']}.json").read_text(encoding="ascii"))["status"] for item in CASES},
        "failureLedger": failures,
        "sourceChanges": source_changes,
    }
    _atomic_private(target / "receipt.json", _json_bytes(final_receipt))
    files = []
    for path in sorted((item for item in target.rglob("*") if item.is_file()), key=lambda item: item.relative_to(target).as_posix()):
        if path.name == "integrity.json":
            continue
        files.append({"path": path.relative_to(target).as_posix(), "sha256": _sha(path.read_bytes()), "sizeBytes": path.stat().st_size})
    _write_private(target / "integrity.json", _json_bytes({"schema": SCHEMA, "files": files}))
    errors = _verify_result_root(target)
    if errors:
        print("result integrity failed: " + "; ".join(errors), file=sys.stderr)
        return 2
    print(f"T003 synthetic controls: {final_status}; {sum(s == 'passed' for s in final_receipt['cases'].values())}/{len(CASES)} cases passed; result={target}")
    if interrupted:
        print("T003 matrix interrupted; remaining cases remain not-started", file=sys.stderr)
        return 130
    return 0 if final_status == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path,
                        help="new private result directory outside the source checkout")
    parser.add_argument("--timeout-seconds", type=int, default=120,
                        help=f"per-case timeout (1-{MAX_TIMEOUT_SECONDS}, default 120)")
    parser.add_argument("--verify-root", type=Path,
                        help="verify a prior result root's permissions, inventory and hashes; performs no tests")
    args = parser.parse_args(argv)
    if not 1 <= args.timeout_seconds <= MAX_TIMEOUT_SECONDS:
        parser.error(f"--timeout-seconds must be between 1 and {MAX_TIMEOUT_SECONDS}")
    if args.verify_root is not None:
        errors = _verify_result_root(args.verify_root.resolve(strict=False))
        if errors:
            print("result integrity failed: " + "; ".join(errors), file=sys.stderr)
            return 2
        print("result integrity verified")
        return 0
    if args.output_root is None:
        parser.error("--output-root is required unless --verify-root is used")
    try:
        return _run(Path(__file__).resolve().parents[1], args.output_root, args.timeout_seconds)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print(f"T003 runner refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
