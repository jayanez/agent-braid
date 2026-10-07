#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh-process, read-only verification for every SPEC-038 treatment slot."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import m4_real_workload as source
from agent_braid import m4_real_workload_trials as trials
from agent_braid import runtime_policy


def _candidate_identity(manifest: dict) -> bool:
    try:
        head = source._git(ROOT, "rev-parse", "HEAD")
        status = source._git(ROOT, "status", "--porcelain=v1", "--untracked-files=all")
    except Exception:
        return False
    if head != manifest.get("candidateCommit") or status:
        return False
    hashes = manifest.get("harnessInputHashes")
    if type(hashes) is not dict or not hashes:
        return False
    for name, expected in hashes.items():
        if (type(name) is not str or name.startswith("/") or ".." in Path(name).parts
                or "\\" in name or type(expected) is not str or len(expected) != 64):
            return False
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            return False
    return True


def verify_record(manifest_raw: bytes, record_raw: bytes) -> dict:
    manifest = source.validate_manifest(manifest_raw)
    return _verify_validated_record(manifest, manifest_raw, record_raw)


def _verify_validated_record(manifest: dict, manifest_raw: bytes, record_raw: bytes) -> dict:
    """Verify a source-validated manifest; CLI always obtains it from raw bytes."""
    start_wall, start_cpu = time.monotonic_ns(), time.process_time_ns()
    try:
        record = json.loads(record_raw)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("capture record is invalid JSON") from exc
    if (type(record) is not dict or record.get("recordVersion") != trials.RECORD_VERSION
            or record.get("candidateCommit") != manifest.get("candidateCommit")
            or record.get("manifestSha256") != hashlib.sha256(manifest_raw).hexdigest()
            or len(record.get("slots", [])) != 20):
        raise ValueError("record, candidate, manifest, or complete slot inventory differs")
    source_path = Path(manifest["sourceRepository"]).resolve(strict=True)
    if source.source_fingerprint(source_path) != manifest["sourceFingerprint"]:
        source_integrity = "changed"
    else:
        source_integrity = "unchanged"
    candidate_integrity = _candidate_identity(manifest)
    by_id = {slot["slotId"]: slot for slot in manifest["slots"]}
    if len(by_id) != 20:
        raise ValueError("manifest slot IDs are not unique")
    expected_ids = [slot["slotId"] for slot in trials.build_schedule()["slots"]]
    if [row.get("slotId") for row in record["slots"]] != expected_ids:
        raise ValueError("capture slot order differs from the frozen dispatch schedule")
    seen = set()
    rows = []
    for row in record["slots"]:
        slot_id = row.get("slotId") if type(row) is dict else None
        if slot_id not in by_id or slot_id in seen:
            raise ValueError("capture slot is missing, duplicate, or unregistered")
        seen.add(slot_id)
        slot = by_id[slot_id]
        for key in ("pairId", "pairKind", "operationOrder", "globalPairDispatch", "treatmentOrder", "mode"):
            if row.get(key) != slot.get(key):
                raise ValueError("capture slot descriptor differs from frozen manifest")
        sample = row.get("sample")
        sample_status = row.get("status")
        has_completed_result = type(sample) is dict and sample.get("status") == "completed"
        has_recovered_result = type(sample) is dict and sample.get("status") == "recovered"
        result = {"slotId": slot_id, "disposition": sample_status,
                  "inspection": "not-required-unexecuted" if sample_status == "unexecuted" else "pending",
                  "resultTree": None}
        if sample_status == "unexecuted":
            if sample is not None or not row.get("reason"):
                raise ValueError("unexecuted slot lacks its explicit reason")
            if Path(slot["runPath"]).exists() or Path(slot["grantPath"]).exists():
                result.update(disposition="invalid", reason="unexecuted-slot-has-runtime-artifacts")
        elif type(sample) is dict:
            if has_recovered_result:
                try:
                    inputs = source.runtime_inputs_for_slot(manifest, slot)
                    trials._validate_recovered_sample(sample, slot, inputs["expectedFinalTree"], manifest)
                    plan = sample["recovery"]["plan"]
                except Exception as exc:
                    result.update(disposition="invalid", inspection="recovery-evidence-invalid",
                                  inspectionError={"type": type(exc).__name__, "message": str(exc)})
                    rows.append(result)
                    continue
            else:
                operation = sample.get("operational")
                plan = operation.get("plan") if type(operation) is dict else None
            if type(plan) is dict:
                inputs = source.runtime_inputs_for_slot(manifest, slot)
                grant_path = Path(slot["grantPath"])
                request = inputs["runtimeRequest"]
                policy_revision = plan.get("policy", {}).get("revision") if type(plan.get("policy")) is dict else None
                expected_revision = (runtime_policy.POLICY if slot["mode"] == "serial"
                                     else runtime_policy.PARALLEL_POLICY)
                runtime_manifest = plan.get("runtimeManifest", {})
                if (runtime_manifest.get("request") != request
                        or runtime_manifest.get("runDirectory") != slot["runPath"]
                        or policy_revision != expected_revision):
                    result.update(inspection="refused-plan-binding-differs")
                    if has_completed_result or has_recovered_result:
                        result.update(disposition="invalid", reason="fresh-plan-binding-differs")
                    rows.append(result)
                    continue
                try:
                    inspected = runtime_policy.inspect_policy_run(plan, grant_path)
                    runtime_result = inspected.get("runtime", {})
                    expected = inputs["expectedFinalTree"]
                    verified = runtime_result.get("status") == "verified-completed"
                    tree = runtime_result.get("resultTree")
                    result.update(inspection="recovered-result-inspected" if has_recovered_result else "inspected",
                                  resultTree=tree,
                                  inspectorStatus=runtime_result.get("status"),
                                  treeMatches=(tree == expected),
                                  independentVerification=verified)
                    if (has_completed_result or has_recovered_result) and not (verified and tree == expected):
                        result["disposition"] = "invalid"
                        result["reason"] = "fresh-inspection-disagrees"
                except Exception as exc:
                    result.update(inspection="failed", inspectionError={
                        "type": type(exc).__name__, "message": str(exc)})
                    if has_completed_result or has_recovered_result:
                        result.update(disposition="invalid", reason="fresh-inspection-failed")
            else:
                result["inspection"] = "no-plan-retained"
                if has_completed_result or has_recovered_result:
                    result.update(disposition="invalid", reason="completed-slot-has-no-plan")
        else:
            result["inspection"] = "missing-treatment-envelope"
            if has_completed_result or has_recovered_result:
                result.update(disposition="invalid", reason="completed-slot-has-no-sample")
        if source_integrity != "unchanged" and type(sample) is dict and sample_status != "unexecuted":
            result.update(disposition="invalid", reason="source-integrity-changed-after-trials")
        rows.append(result)
    if seen != set(by_id):
        raise ValueError("capture omitted one or more intended slots")
    pair_trees = {}
    for row, verification in zip(record["slots"], rows):
        pair_trees.setdefault(row["pairId"], {})[row["mode"]] = verification.get("resultTree")
    pair_results = []
    for pair in trials.build_schedule()["pairs"]:
        trees = pair_trees[pair["pairId"]]
        complete = set(trees) == {"serial", "parallel"} and all(trees.values())
        pair_results.append({"pairId": pair["pairId"], "completeTrees": complete,
                             "treesMatch": complete and trees["serial"] == trees["parallel"],
                             "serialTree": trees.get("serial"), "parallelTree": trees.get("parallel")})
    schedule_pairs = trials.build_schedule()["pairs"]
    measured_ids = {pair["pairId"] for pair in schedule_pairs if pair["pairKind"] == "measured"}
    captured_denominator = {
        "intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
        "validMeasuredPairs": sum(
            pair_id in measured_ids and all(row["status"] == "valid" for row in record["slots"]
                                            if row["pairId"] == pair_id)
            for pair_id in {row["pairId"] for row in record["slots"]}),
        "invalidPairs": sum(
            any(row["status"] in {"invalid", "no-go", "invalidated", "failed", "refused",
                                   "interrupted", "recovered"}
                for row in record["slots"] if row["pairId"] == pair["pairId"])
            for pair in schedule_pairs),
        "failedPairs": sum(any(row["status"] == "failed" for row in record["slots"]
                               if row["pairId"] == pair["pairId"]) for pair in schedule_pairs),
        "refusedPairs": sum(any(row["status"] == "refused" for row in record["slots"]
                                if row["pairId"] == pair["pairId"]) for pair in schedule_pairs),
        "interruptedPairs": sum(any(row["status"] == "interrupted" for row in record["slots"]
                                    if row["pairId"] == pair["pairId"]) for pair in schedule_pairs),
        "recoveredPairs": sum(any(row["status"] == "recovered" for row in record["slots"]
                                  if row["pairId"] == pair["pairId"]) for pair in schedule_pairs),
        "unexecutedPairs": sum(
            any(row["status"] == "unexecuted" for row in record["slots"] if row["pairId"] == pair["pairId"])
            for pair in schedule_pairs),
        "attemptedTreatments": sum(row["status"] != "unexecuted" for row in record["slots"]),
    }
    if record.get("denominator") != captured_denominator:
        raise ValueError("capture denominator differs from independently reconciled slots")
    reconciled_by_pair = {row["pairId"]: [] for row in schedule_pairs}
    for record_row, verified_row in zip(record["slots"], rows):
        reconciled_by_pair[record_row["pairId"]].append(verified_row)
    post_verification_denominator = {
        "intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
        "validMeasuredPairs": sum(pair_id in measured_ids
                                   and len(reconciled_by_pair[pair_id]) == 2
                                   and all(row["disposition"] == "valid" for row in reconciled_by_pair[pair_id])
                                   and next(pair for pair in pair_results if pair["pairId"] == pair_id)["treesMatch"]
                                   for pair_id in reconciled_by_pair),
        "invalidPairs": sum(any(row["disposition"] in {"invalid", "no-go", "invalidated", "failed",
                                                        "refused", "interrupted", "recovered"}
                                for row in reconciled_by_pair[pair_id]) for pair_id in reconciled_by_pair),
        "failedPairs": sum(any(row["disposition"] == "failed" for row in reconciled_by_pair[pair_id])
                           for pair_id in reconciled_by_pair),
        "refusedPairs": sum(any(row["disposition"] == "refused" for row in reconciled_by_pair[pair_id])
                            for pair_id in reconciled_by_pair),
        "interruptedPairs": sum(any(row["disposition"] == "interrupted" for row in reconciled_by_pair[pair_id])
                                for pair_id in reconciled_by_pair),
        "recoveredPairs": sum(any(row["disposition"] == "recovered" for row in reconciled_by_pair[pair_id])
                              for pair_id in reconciled_by_pair),
        "unexecutedPairs": sum(any(row["disposition"] == "unexecuted"
                                    for row in reconciled_by_pair[pair_id]) for pair_id in reconciled_by_pair),
        "attemptedTreatments": sum(row["disposition"] != "unexecuted" for row in rows),
    }
    verification_changed_slots = [
        {"slotId": record_row["slotId"], "capturedDisposition": record_row["status"],
         "freshDisposition": verified_row["disposition"]}
        for record_row, verified_row in zip(record["slots"], rows)
        if record_row["status"] != verified_row["disposition"]
    ]
    passed = source_integrity == "unchanged" and candidate_integrity and not verification_changed_slots and all(
        row["independentVerification"] and row["treeMatches"]
        for record_row, row in zip(record["slots"], rows)
        if type(record_row.get("sample")) is dict
        and record_row["sample"].get("status") in {"completed", "recovered"})
    pair_failures = [row["pairId"] for row in pair_results if row["completeTrees"] and not row["treesMatch"]]
    if pair_failures:
        passed = False
    return {"recordVersion": trials.VERIFY_VERSION, "status": "verified" if passed else "inconclusive",
            "recordSha256": hashlib.sha256(record_raw).hexdigest(),
            "manifestSha256": hashlib.sha256(manifest_raw).hexdigest(),
            "candidateCommit": manifest["candidateCommit"], "sourceIntegrity": source_integrity,
            "candidateIntegrity": "unchanged" if candidate_integrity else "changed-or-unverifiable",
            "intendedSlots": 20, "inspectedSlots": len(rows), "slots": rows,
            "pairTreeComparisons": pair_results,
            "capturedDenominator": captured_denominator,
            "postVerificationDenominator": post_verification_denominator,
            "verificationChangedSlots": verification_changed_slots,
            "pairDenominatorInterpretation": (
                "Captured denominators reconcile original trial dispositions. Post-verification counts "
                "are separate; invalidPairs and unexecutedPairs may overlap for a failed partial pair."),
            "timing": {"wallNs": time.monotonic_ns() - start_wall,
                       "parentCpuNs": time.process_time_ns() - start_cpu,
                       "scope": "separate fresh Python process; outside treatment ratios"},
            "boundary": "Read-only policy inspection and existing independent runtime verifier; no workload code, grants, or source ref promotion."}


def _fresh_output(path: Path, manifest: dict) -> Path:
    target = path.expanduser().absolute()
    if os.path.lexists(target) or target.name in {"", ".", ".."}:
        raise ValueError("verification output must be fresh")
    target = target.parent.resolve(strict=True) / target.name
    protected_roots = (ROOT.resolve(), Path(manifest["sourceRepository"]).resolve(),
                       Path(manifest["sourceFingerprint"]["commonDirectory"]).resolve())
    if any(target == protected or target.is_relative_to(protected)
           or protected.is_relative_to(target) for protected in protected_roots):
        raise ValueError("verification output must be outside candidate, source, and Git common storage")
    for slot in manifest["slots"]:
        for key in ("runPath", "grantPath"):
            destination = Path(slot[key]).resolve(strict=False)
            if (target == destination or target.is_relative_to(destination)
                    or destination.is_relative_to(target)):
                raise ValueError("verification output must not overlap treatment destinations")
    return target


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        manifest_raw, record_raw = args.manifest.read_bytes(), args.record.read_bytes()
        manifest = source.validate_manifest(manifest_raw)
        report = _verify_validated_record(manifest, manifest_raw, record_raw)
        output = _fresh_output(args.output, manifest)
        raw = trials.encode(report)
        with output.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"status": report["status"], "output": str(output),
                          "inspectedSlots": report["inspectedSlots"]}))
        return 0 if report["status"] == "verified" else 2
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(json.dumps({"status": "inconclusive", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
