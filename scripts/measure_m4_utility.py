#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare and diagnose the approved synthetic corpus; registered capture is gated."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import git_replay, git_runtime, runtime_policy
from agent_braid.utility_accounting import UtilityAccounting
from agent_braid.utility_fixtures import _destination, build_fixture, validate_prepared_manifest

PROTOCOL_COMMIT = "3777e578ba3f8130d6f284acf54898198a45e0f0"
PROTOCOL_SHA256 = "6e5a2bd790fb789926007e11f33af40df2ed494d3e8464b13f114523120b282b"
DEFAULT_MANIFEST = ROOT / "specs/022-m4-utility-followup/evidence/prepared-fixture-manifest.json"
INPUT_PATHS = (
    "agent_braid/utility_accounting.py", "agent_braid/utility_fixtures.py",
    "agent_braid/git_process.py", "agent_braid/git_runtime_process.py",
    "agent_braid/git_runtime.py", "agent_braid/git_replay.py",
    "agent_braid/git_adapter.py", "agent_braid/runtime_policy.py",
    "agent_braid/runtime_scheduler.py", "agent_braid/analysis.py",
    "agent_braid/git_exec.py", "research/lab/model.py",
    "scripts/measure_m4_utility.py", "agent_braid/utility_trials.py",
    "scripts/prepare_m4_utility_trials.py",
    "specs/022-m4-utility-followup/technical-review-packet.md",
    "specs/022-m4-utility-followup/evidence/prepared-fixture-manifest.json",
)


class UnsafeDiagnostic(RuntimeError):
    """Safety or immutable identity failure: stop subsequent diagnostics."""


class _OwnedTreatmentDirectory:
    """Fresh caller-bound private scope; never adopt or remove an existing root."""

    def __init__(self, path: Path):
        self.path = _destination(path)
        self.path.mkdir(mode=0o700, exist_ok=False)
        self.name = str(self.path)

    def cleanup(self):
        shutil.rmtree(self.path)


def encode(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def inventory() -> dict:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in INPUT_PATHS}


def source_fingerprint(repository: Path) -> dict:
    """All owned source bytes, not only its visible refs or final tree."""
    result = {}
    for path in sorted(repository.rglob("*")):
        if path.is_symlink():
            raise UnsafeDiagnostic("owned source contains a symlink")
        if path.is_file():
            result[path.relative_to(repository).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def _load_fixture_inputs(fixture: dict) -> tuple[dict, dict]:
    result = []
    for kind in ("runtime", "replay"):
        raw = Path(fixture[kind + "RequestPath"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != fixture[kind + "RequestSha256"]:
            raise UnsafeDiagnostic("prepared request identity changed")
        result.append(json.loads(raw))
    request, replay = result
    if request != fixture["runtimeRequest"] or replay != fixture["replayRequest"]:
        raise UnsafeDiagnostic("prepared request differs from bound fixture")
    return request, replay


def worker_overlap(preparation: dict | None) -> dict:
    """Supplemental intervals relative to the scheduler's own recorded origin."""
    if preparation is None:
        return {"unionNs": None, "peakIntervals": None,
                "reason": "serial policy exposes no worker preparation intervals"}
    wall = preparation["wallNs"]
    events = []
    for worker in preparation["workers"]:
        start, end = worker["startedNs"], worker["finishedNs"]
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= wall:
            raise UnsafeDiagnostic("invalid supplemental worker interval")
        events.extend(((start, 1), (end, -1)))
    active = peak = union = 0
    previous = 0
    for tick, delta in sorted(events):
        if active:
            union += tick - previous
        active += delta
        peak = max(peak, active)
        previous = tick
    if active or peak != preparation["observedPeakWorkerIntervals"]:
        raise UnsafeDiagnostic("unreconciled supplemental worker intervals")
    return {"unionNs": union, "peakIntervals": peak,
            "scope": "scheduler-relative interval union and peak occupancy, not CPU parallelism"}


def run_treatment(fixture: dict, mode: str, *, accounting_factory=UtilityAccounting,
                  cancel_event=None, controlled_child_scope: bool = False,
                  treatment_root: Path | None = None, run_leaf: str = "result",
                  grant_leaf: str = "grants") -> dict:
    """Run the complete existing grant/verification path in owned private storage."""
    if mode not in {"serial", "parallel"}:
        raise ValueError("unsupported treatment mode")
    if any(not isinstance(name, str) or name in {"", ".", ".."}
           or Path(name).name != name or "/" in name or "\\" in name
           for name in (run_leaf, grant_leaf)) or run_leaf == grant_leaf:
        raise ValueError("run and grant leaves must be distinct ordinary names")
    accounting = accounting_factory(child_attribution_valid=controlled_child_scope)
    operational = {"mode": mode, "blockId": fixture["blockId"], "status": "incomplete",
                   "immutableSourceUnchanged": None}
    private = None
    cleanup_error = None
    source = Path(fixture["repository"])
    before = None
    accounting.start()
    with accounting.activate_git_budget_registry():
        try:
            with accounting.phase("input"):
                request, replay_request = _load_fixture_inputs(fixture)
                before = source_fingerprint(source)
                if ("preparedSourceFingerprint" in fixture
                        and fixture["preparedSourceFingerprint"] != before):
                    raise UnsafeDiagnostic("immutable source differs from preparation fingerprint")
                private = (_OwnedTreatmentDirectory(treatment_root) if treatment_root is not None
                           else tempfile.TemporaryDirectory(prefix="agent-braid-utility-treatment-"))
                destination = Path(private.name)
            with accounting.phase("replay"):
                evidence, advisory = git_replay.produce(replay_request)
            with accounting.phase("preparation"):
                plan = runtime_policy.prepare_policy_run(
                    request, destination / run_leaf, replay_evidence=evidence,
                    advisory_plan=advisory, mode=mode, cancel_event=cancel_event)
            with accounting.phase("grant"):
                grant = runtime_policy.issue_operator_grant(
                    plan, destination / grant_leaf, acknowledge=plan["planDigest"],
                    cancel_event=cancel_event)
            with accounting.phase("execution"):
                report = runtime_policy.execute_policy_run(
                    plan, destination / grant_leaf, grant["grantId"], cancel_event=cancel_event)
            with accounting.phase("independent_verification"):
                verification = git_runtime.verify_run(request, destination / run_leaf)
                if (verification.get("status") != "verified-completed"
                        or verification.get("resultTree") != fixture["expectedFinalTree"]):
                    raise UnsafeDiagnostic("final tree or mandatory verification differs")
                if source_fingerprint(source) != before:
                    raise UnsafeDiagnostic("immutable source bytes changed")
                operational.update(status="completed", resultTree=verification["resultTree"],
                                   grantId=grant["grantId"], immutableSourceUnchanged=True,
                                   runtimeManifest=deepcopy(plan["runtimeManifest"]),
                                   planDigest=plan["planDigest"], runtimeReport=report,
                                   independentVerification=verification,
                                   workerOverlap=worker_overlap(report.get("preparation")))
        except Exception as exc:
            operational.update(status="no-go" if isinstance(exc, UnsafeDiagnostic) else "inconclusive",
                               error={"type": type(exc).__name__, "message": str(exc),
                                      "category": getattr(exc, "category", None)})
            # A failure before final verification must not conceal source mutation.
            # This failure-path coordinator work remains inside the residual span.
            if before is not None:
                try:
                    if source_fingerprint(source) != before:
                        raise UnsafeDiagnostic("immutable source bytes changed on failure")
                except (UnsafeDiagnostic, OSError) as safety_error:
                    operational.update(status="no-go", safetyError={
                        "type": type(safety_error).__name__, "message": str(safety_error)})
        finally:
            # Encoding the operational result precedes the final cleanup/closing tick.
            # The final accounting envelope is necessarily encoded outside that tick.
            try:
                with accounting.phase("report_serialization"):
                    operational["accountingPreview"] = accounting.preview()
                    raw_operational = encode(operational)
            finally:
                with accounting.phase("cleanup"):
                    if private is not None:
                        try:
                            private.cleanup()
                        except OSError as exc:
                            cleanup_error = {"type": type(exc).__name__, "message": str(exc)}
    final_status = operational["status"]
    if cleanup_error is not None and final_status != "no-go":
        final_status = "inconclusive"
    observation = accounting.finish(
        outcome="success" if final_status == "completed" else "failure")
    if final_status == "completed" and not observation["complete"]:
        final_status = "inconclusive"
    # Retain the authoritative bytes actually encoded in the operational phase.
    # Cleanup/closing status belongs to the later envelope, not a retroactive
    # mutation of that already encoded report.
    result, observer = accounting.seal(lambda closed: {
        "operational": deepcopy(operational), "operationalEncoded": raw_operational.decode(),
        "operationalEncodedBytes": len(raw_operational), "status": final_status,
        "cleanupError": cleanup_error, "accounting": closed,
        "boundary": "operational report bytes precede cleanup; closing status/accounting envelope and final output are separately observed"})
    result["observerFinalization"] = observer
    return result


def _git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], timeout=30).decode().strip()


def _new_output(path: Path) -> Path:
    supplied = path.expanduser().absolute()
    if supplied.is_symlink() or supplied.exists():
        raise ValueError("output must be a fresh file")
    resolved = supplied.parent.resolve(strict=True) / supplied.name
    if resolved.is_relative_to(ROOT):
        raise ValueError("output must be outside the candidate checkout")
    return resolved


def _write_new(path: Path, record: dict) -> dict:
    """Observer sealing/output is explicitly outside operational treatment clocks."""
    start, cpu = time.monotonic_ns(), time.process_time_ns()
    raw = encode(record)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"wallNs": time.monotonic_ns() - start,
            "parentCpuNs": time.process_time_ns() - cpu,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "scope": "shared final envelope encoding/output outside all operational ratios"}


def run(manifest: Path, output: Path, *, diagnostic_block: str | None = None,
        controlled_child_scope: bool = False) -> int:
    """No registered trials: prepare inventory or capture one diagnostic pair."""
    output = _new_output(output)
    observer_path = output.with_name(output.name + ".observer.json")
    _new_output(observer_path)
    raw_manifest = manifest.read_bytes()
    prepared = validate_prepared_manifest(raw_manifest)
    before = inventory()
    if before["specs/022-m4-utility-followup/technical-review-packet.md"] != PROTOCOL_SHA256:
        raise ValueError("approved protocol identity changed")
    if _git("status", "--porcelain"):
        raise ValueError("diagnostic/preparation requires a clean candidate commit")
    candidate = _git("rev-parse", "HEAD")
    rows = [{"blockId": block["blockId"],
             "status": "excluded-by-pinned-cap" if block["directNumericExclusions"] else "admission-pending",
             "exclusions": deepcopy(block["directNumericExclusions"])}
            for block in prepared["blocks"]]
    record = {"recordVersion": "spec022-diagnostic-preparation-v1",
              "purpose": "diagnostic-only" if diagnostic_block else "inventory-preparation-only",
              "candidateCommit": candidate, "inputs": before,
              "approvedProtocolCommit": PROTOCOL_COMMIT, "approvedProtocolSha256": PROTOCOL_SHA256,
              "manifestSha256": hashlib.sha256(raw_manifest).hexdigest(),
              "registeredMeasurementExecuted": False, "utilityAcceptance": "pending",
              "g4Decision": "historical-no-go-preserved", "m4Status": "open",
              "inventory": rows, "diagnosticPairs": [],
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "machine": platform.machine(), "git": _git("--version"),
                              "backgroundLoad": "not controlled; no cold-cache claim",
                              "childCpuAttribution": "dedicated CLI process; only its own foreground fixture/Git children" if controlled_child_scope else "not asserted; optional child CPU is null"},
              "limits": ["Synthetic repeated text and file-disjoint patches only.",
                         "No registered results, actual-workload utility or milestone acceptance.",
                         "Fixture generation and aggregate observer output are separately timed.",
                         "Budget command charges and accepted output bytes exclude refused/discarded chunks; total read bytes are unavailable."]}
    if diagnostic_block is not None:
        matching = [b for b in prepared["blocks"] if b["blockId"] == diagnostic_block]
        if len(matching) != 1:
            raise ValueError("diagnostic block is not in the fixed inventory")
        block = matching[0]
        if not block["directNumericExclusions"]:
            prep_wall, prep_cpu = time.monotonic_ns(), time.process_time_ns()
            with tempfile.TemporaryDirectory(prefix="agent-braid-utility-fixture-") as directory:
                fixture = build_fixture(block, Path(directory) / "fixture")
                record["fixturePreparation"] = {"wallNs": time.monotonic_ns() - prep_wall,
                                                "parentCpuNs": time.process_time_ns() - prep_cpu,
                                                "scope": "outside operational treatment interval"}
                samples = []
                for mode in ("serial", "parallel"):
                    sample = run_treatment(fixture, mode, controlled_child_scope=controlled_child_scope)
                    samples.append(sample)
                    if sample["status"] == "no-go":
                        break
                record["diagnosticPairs"].append({"blockId": block["blockId"],
                                                "treatmentOrder": [s["operational"]["mode"] for s in samples],
                                                "samples": samples,
                                                "registration": "not-registered; exploratory diagnostic only"})
        else:
            record["diagnosticDisposition"] = "excluded-not-run"
    changed = inventory() != before or bool(_git("status", "--porcelain"))
    samples = [s for pair in record["diagnosticPairs"] for s in pair["samples"]]
    record["status"] = ("invalidated" if changed else "excluded-not-run" if
        record.get("diagnosticDisposition") == "excluded-not-run" else "no-go" if any(
        s["status"] == "no-go" for s in samples) else "inconclusive" if any(
        s["status"] != "completed" for s in samples) else "prepared-or-diagnosed")
    record["candidateInputsChangedDuringRun"] = changed
    observer = _write_new(output, record)
    # This small companion encodes the already closed observer span. Its own write
    # is a subsequent publication step, not claimed inside either measured span.
    with observer_path.open("xb") as stream:
        stream.write(encode({"recordVersion": "spec022-observer-receipt-v1",
                             "output": str(output), "observation": observer,
                             "receiptWriteBoundary": "subsequent publication, outside the closed observer span"}))
    print(json.dumps({"status": record["status"], "output": str(output),
                      "observerReceipt": str(observer_path), "registeredMeasurementExecuted": False}))
    return 0 if record["status"] == "prepared-or-diagnosed" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--diagnostic-block", help="one fixed inventory block; never registered trials")
    args = parser.parse_args(argv)
    try:
        return run(args.manifest, args.output, diagnostic_block=args.diagnostic_block,
                   controlled_child_scope=True)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "input-or-infrastructure-error", "error": str(exc),
                          "registeredMeasurementExecuted": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
