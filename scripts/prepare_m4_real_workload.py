#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare the exact SPEC-038 candidate manifest; capture is always refused."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.m4_real_workload import (  # noqa: E402
    InvalidRealWorkload, prepare_workload, validate_manifest,
)


def _fresh_output(value: Path) -> Path:
    raw = value.expanduser().absolute()
    if raw.name in {"", ".", ".."} or os.path.lexists(raw):
        raise InvalidRealWorkload("output must be a fresh ordinary file")
    parent = raw.parent.resolve(strict=True)
    target = parent / raw.name
    if target.is_relative_to(ROOT.resolve()):
        raise InvalidRealWorkload("outputs must be outside the candidate checkout")
    return target


def prepare(source_repository: Path, destination_root: Path, output: Path,
            approval_receipt: Path) -> dict:
    target = _fresh_output(output)
    receipt_path = _fresh_output(Path(str(target) + ".provenance.json"))
    source = source_repository.expanduser().resolve(strict=True)
    if target.is_relative_to(source) or receipt_path.is_relative_to(source):
        raise InvalidRealWorkload("manifest outputs must be outside source repository")
    started_wall, started_cpu = time.monotonic_ns(), time.process_time_ns()
    raw = prepare_workload(source, destination_root, approval_receipt)
    preparation_wall = time.monotonic_ns() - started_wall
    preparation_cpu = time.process_time_ns() - started_cpu
    manifest = validate_manifest(raw)
    common = Path(manifest["sourceFingerprint"]["commonDirectory"])
    future_paths = [Path(slot[key]) for slot in manifest["slots"] for key in ("runPath", "grantPath")]
    for target_path in (target, receipt_path):
        if target_path.is_relative_to(common) or any(
                target_path == path or target_path.is_relative_to(path) or path.is_relative_to(target_path)
                for path in future_paths):
            raise InvalidRealWorkload("manifest outputs overlap source storage or a future private destination")
    receipt = {
        "version": "spec038-real-workload-preparation-provenance-v1",
        "candidateCommit": manifest["candidateCommit"],
        "candidateInputs": manifest["candidateInputs"],
        "manifestSha256": manifest["manifestSha256"],
        "approvalReceiptSha256": manifest["sourceRightsApproval"]["receiptSha256"],
        "sourceFingerprint": manifest["sourceFingerprint"],
        "staticPreparationWallNs": preparation_wall,
        "staticPreparationParentCpuNs": preparation_cpu,
        "admittedOperations": len(manifest["operations"]),
        "preparedTreatmentSlots": len(manifest["slots"]),
        "registeredCapture": False,
        "captureAuthorization": False,
        "sourceCodeExecuted": False,
        "grantsIssued": False,
        "persistentRunsAllocated": False,
        "boundary": "Static source admission and evaluation preparation only; no fixtures, grants, treatment execution, capture, or M4 acceptance.",
    }
    # Exclusive creation makes the manifest and provenance immutable outputs.
    with target.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        with receipt_path.open("xb") as stream:
            stream.write((json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise
    return {"status": "prepared-review-pending", "output": str(target),
            "manifestSha256": manifest["manifestSha256"], "registeredCapture": False,
            "provenance": str(receipt_path)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-repository", type=Path)
    parser.add_argument("--destination-root", type=Path,
                        help="fresh external path namespace; it is not created")
    parser.add_argument("--approval-receipt", type=Path)
    parser.add_argument("--output", type=Path)
    for flag in ("--run", "--execute", "--registered"):
        parser.add_argument(flag, action="store_true", help="refused; this command prepares only")
    args = parser.parse_args(argv)
    if args.run or args.execute or args.registered:
        print(json.dumps({"status": "refused", "reason": "registered capture requires separate stable-harness review and exact capture authorization"}), file=sys.stderr)
        return 2
    if (args.source_repository is None or args.destination_root is None or args.output is None
            or args.approval_receipt is None):
        parser.error("--source-repository, --destination-root, --approval-receipt and --output are required for preparation")
    try:
        result = prepare(args.source_repository, args.destination_root, args.output, args.approval_receipt)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (InvalidRealWorkload, OSError) as exc:
        print(json.dumps({"status": "refused", "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
