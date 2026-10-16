#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Offline assisted M4.5 preparation and named deterministic control receipts.

Run from the source checkout using ``python -m scripts.run_m45_assisted_controls``.
This never captures an experimental attempt or invokes an actual model/host.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import platform
import re
import secrets
import subprocess
import sys
import time
from typing import Any

from agent_braid import tooling_coordination as coordination
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_evidence_packets as packets
from agent_braid import tooling_fixtures as fixtures
from agent_braid import tooling_human_audit as audit
from scripts import run_tooling_controls as controls
from tests.test_tooling_evaluation import _registration


SCHEMA = "agent-braid-m45-assisted-controls-v1"
DEFAULT_SEED = "m45-assisted-offline-controls-20261013"
HUMAN_REVIEWER_ROLES = ("human-reviewer-1", "human-reviewer-2")
SHUFFLE_ALGORITHM = "hmac-sha256-independent-rater-v1"
_SPECS = (
    ("source-positive", "tests.test_tooling_source_routes.SourceRouteSupervisorTests.test_fresh_source_route_completes_without_any_v3_flag_synthesis", "Fresh source composition completes the synthetic bounded route without legacy flags.", "positive"),
    ("source-expiry", "tests.test_tooling_source_observer.SourceCacheTests.test_empty_expired_and_regressed_clock_invalidate", "Empty, expired and regressed synthetic observations invalidate the source snapshot.", "negative"),
    ("process-birth-mismatch", "tests.test_tooling_source_routes.SourceRouteSupervisorTests.test_wrong_process_birth_stops_before_stdin_release", "Wrong synthetic process birth stops before prompt release.", "negative"),
    ("source-pin-drift", "tests.test_tooling_source_observer.PrivateVerifierTests.test_bundle_pin_procedure_pin_and_symlink_drift_refuse_before_authentication", "Bundle, verifier and symlink drift refuse before authentication.", "negative"),
    ("registration-positive", "tests.test_tooling_registration_v6.RegistrationV6Tests.test_roster_and_new_source_binding_do_not_synthesize_v3_observation", "The v6 synthetic 108-slot roster binds source contracts without fabricating v3 flags.", "positive"),
    ("registration-pin-mismatch", "tests.test_tooling_registration_v6.RegistrationV6Tests.test_missing_or_drifted_source_contracts_and_instruments_refuse", "Missing or altered source/instrument pins refuse.", "negative"),
    ("audit-sample-positive", "tests.test_tooling_human_audit.AuditSelectionTests.test_fixed_sample_mirrors_one_instance_across_three_arms", "The prospective sample preserves one fixture per host/class across all arms.", "positive"),
    ("audit-unknowns", "tests.test_tooling_human_audit.AuditAssessmentTests.test_all_missing_automatic_results_require_108_and_do_not_count_complete", "Missing automatic assessments retain 108 unreviewed cases and incomplete coverage.", "negative"),
    ("audit-critical-escalation", "tests.test_tooling_human_audit.AuditAssessmentTests.test_critical_incidents_expand_whole_cohort_and_suspend_acceptance", "Synthetic critical incidents require all 108 cases and suspend acceptance.", "negative"),
    ("audit-provenance", "tests.test_tooling_human_audit.AuditAssessmentTests.test_model_identity_relabelled_human_is_rejected_across_roles", "Model identities cannot be relabeled as human reviewers.", "negative"),
    ("coordinator-restart-positive", "tests.test_tooling_coordination.CoordinationTests.test_restart_preserves_completed_dependencies_and_candidate", "Durable synthetic procedure receipts survive restart and gate dependencies.", "positive"),
    ("coordinator-process-race", "tests.test_tooling_coordination.CoordinationTests.test_actual_process_race_has_exactly_one_claim", "Two actual local processes produce exactly one synthetic task claim.", "negative"),
    ("coordinator-no-replay", "tests.test_tooling_coordination.CoordinationTests.test_only_prestart_claim_can_be_released", "A durable start cannot be released, reclaimed or dispatched again.", "negative"),
    ("coordinator-corruption", "tests.test_tooling_coordination.CoordinationTests.test_corruption_oversize_symlink_and_nonprivate_files_fail_closed", "Corrupt, oversized, symlinked and nonprivate registers refuse.", "negative"),
    ("packets-full-roster-positive", "tests.test_tooling_evidence_packets.EvidencePacketTests.test_all_actual_generated_roster_slots_make_packets_and_zero_order_refuses", "All 108 generated slots preserve order 1–3 and invalid order zero refuses.", "positive"),
    ("packets-blinding-positive", "tests.test_tooling_evidence_packets.EvidencePacketTests.test_human_packet_hides_structured_arm_order_host_ids_and_model_predictions", "Human packets hide structured arm/order/host and model prediction fields.", "positive"),
    ("packets-source-mismatch", "tests.test_tooling_evidence_packets.EvidencePacketTests.test_machine_source_map_drift_and_duplicate_step_ids_are_rejected", "Machine source-map drift and repeated steps refuse.", "negative"),
    ("packets-untrusted-excerpt", "tests.test_tooling_evidence_packets.EvidencePacketTests.test_carriage_return_source_cannot_escape_quoted_markdown", "Carriage returns cannot turn quoted source text into active Markdown.", "negative"),
)
CASES = tuple({"id": case_id, "test": test, "oracle": oracle, "role": role}
              for case_id, test, oracle, role in _SPECS)
LIMITS = (
    "Deterministic synthetic control evidence only; no actual native, provider, model or human observations.",
    "The synthetic registration contains test-only declarations and cannot authorize capture.",
    "The original 108 journeys remain not-started; prepared packets have unknown observations.",
    "Passing controls does not satisfy registered reproduction, cash reconciliation, human acceptance or milestone closure.",
)


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _sha(value: Any) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else _json(value)).hexdigest()


def _manifest(repo: Path) -> list[dict[str, Any]]:
    source_paths = set(controls._source_paths(repo))
    source_paths.update(repo / name for name in (
        "scripts/run_m45_assisted_controls.py", "CONSTITUTION.md", "GOVERNANCE.md",
        "specs/044-ai-tooling-evaluation/assisted-audit-decision.md",
        "docs/tooling/COORDINATION.md", "docs/tooling/HUMAN_AUDIT.md", "docs/tooling/SOURCE_OBSERVER.md"))
    result = []
    for path in sorted(source_paths):
        if path.is_symlink() or not path.is_file():
            raise ValueError("control source inventory is unsafe or incomplete")
        raw = path.read_bytes()
        result.append({"path": path.relative_to(repo).as_posix(), "sha256": _sha(raw), "sizeBytes": len(raw)})
    return result


def _freeze(repo: Path) -> dict[str, Any]:
    commit = controls._git(repo, "rev-parse", "HEAD")
    status = controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    manifest = _manifest(repo)
    if (manifest != _manifest(repo) or commit != controls._git(repo, "rev-parse", "HEAD")
            or status != controls._git(repo, "status", "--porcelain=v1", "--untracked-files=all")):
        raise ValueError("source candidate moved while preparing controls")
    return {"commit": commit, "workingTreeClean": not bool(status),
            "workingTreeStatusSha256": _sha(status.encode()), "sourceManifest": manifest,
            "sourceManifestSha256": _sha(manifest),
            "limits": ["Exact source-overlay hashes bind this control candidate; HEAD alone does not identify uncommitted code."]}


def prepare_controls(repo: Path, candidate: dict[str, Any], *, seed: str,
                     blinding_key: bytes) -> dict[str, Any]:
    """Prepare owned inputs and empty review packets; never manufacture results."""
    inventory = fixtures.load_inventory(source_checkout=True, assets_dir=repo / "examples/tooling")
    # Reuse the repository's explicitly synthetic unittest registration fixture.
    # Approval/provider/human fields here are mock validation inputs, never facts.
    data = _registration()
    data["registrationId"] = "synthetic-assisted-controls-only"
    data["candidate"].update(commit=candidate["commit"], sha256=candidate["sourceManifestSha256"])
    data["fixtures"] = [{"fixtureId": item.fixture_id, "journeyClass": item.journey_class,
                         "sha256": item.definition_sha256} for item in inventory.fixtures]
    data["prompts"] = [{"promptId": item.prompt_id, "journeyClass": item.journey_class,
                        "sha256": item.sha256} for item in inventory.prompts]
    data["sourceRights"].update(fixtureIds=[item.fixture_id for item in inventory.fixtures],
                               scope="synthetic offline controls only; no host/provider/human authorization")
    hashes = {item["fixtureId"]: item["sha256"] for item in data["fixtures"]}
    hashes.update({item["promptId"]: item["sha256"] for item in data["prompts"]})
    registration = evaluation.validate_registration(data,
        expected_candidate_sha256=candidate["sourceManifestSha256"], expected_input_hashes=hashes)
    roster = evaluation.generate_slots(registration)
    policy = audit.validate_policy({"schema": audit.POLICY_SCHEMA, "seed": seed,
        "algorithm": audit.ALGORITHM, "initialCases": 36, "reviewersPerCase": 2,
        "escalation": audit.ESCALATION, "compactEvidence": True})
    selection = audit.freeze_selection(roster, policy, expected_policy_sha256=policy.sha256,
        registration_sha256=registration.sha256,
        rubric_sha256=data["rubric"]["sha256"], human_review_roles=HUMAN_REVIEWER_ROLES)
    assessment = audit.assess_audit(selection, (), ())
    definitions = {item.fixture_id: item for item in inventory.fixtures}
    machine_packets, human_packets = [], []
    for slot in roster:
        definition = definitions[slot.fixture_id]
        scenario = definition.definition["scenario"]
        text = _json(definition.definition["expected"]).decode("ascii")
        case = packets.CaseEvidence(slot, "; ".join(scenario["expectedOutcomes"]), None,
            tuple(packets.StepEvidence(f"step-{number}", phase, None, None)
                  for number, phase in enumerate(scenario["phases"], 1)),
            (packets.RedactedExcerpt("owned-fixture-definition:" + slot.fixture_id,
                                     definition.definition_sha256, text, _sha(text.encode())),),
            ("Synthetic preparatory packet; this slot has not been attempted.",))
        machine_packets.append(packets.build_machine_packet(case,
            registration_sha256=registration.sha256, blinding_key=blinding_key))
        if slot.slot_id in selection.initial_slot_ids:
            human_packets.append(packets.build_human_packet(case,
                registration_sha256=registration.sha256, blinding_key=blinding_key))
    # The offline sample seed may be public; derive a separate private shuffle
    # seed rather than exporting or depending on that public seed for blinding.
    shuffle_seed = hmac.new(blinding_key, _json([SCHEMA, "private-shuffle-seed-v1", seed]),
                           hashlib.sha256).hexdigest()
    reviewer_sequences = {}
    for role in HUMAN_REVIEWER_ROLES:
        # Rank opaque case identities, never roster positions or arm labels.
        # Domain separation gives each independent rater a distinct permutation.
        reviewer_sequences[role] = [packet["caseId"] for packet in sorted(human_packets, key=lambda packet:
            (hmac.new(blinding_key, _json([SCHEMA, SHUFFLE_ALGORITHM, registration.sha256,
                                          shuffle_seed, role, packet["caseId"]]), hashlib.sha256).digest(), packet["caseId"]))]
    private_blinding = {"algorithm": SHUFFLE_ALGORITHM, "shuffleSeed": shuffle_seed,
        "seedDerivation": "hmac-sha256-private-shuffle-seed-v1",
        "keyFingerprintSha256": _sha(b"m45-assisted-blinding-key-v1\0" + blinding_key),
        "registrationSha256": registration.sha256, "auditSelectionSha256": selection.sha256,
        "reviewerSequences": reviewer_sequences,
        "inverseMap": {packet["caseId"]: packet["slot"]["slotId"] for packet in machine_packets}}
    private_blinding["blindingSha256"] = hmac.new(blinding_key,
        _json([SCHEMA, "private-blinding-binding", private_blinding]), hashlib.sha256).hexdigest()
    by_case = {packet["caseId"]: packet for packet in human_packets}
    reviewer_packets = {}
    for role in HUMAN_REVIEWER_ROLES:
        bundle = {"schema": "agent-braid-m45-independent-human-bundle-v1", "reviewerRole": role,
            "evidenceType": "synthetic-preparation-only", "blindingSha256": private_blinding["blindingSha256"],
            "casePackets": [json.loads(_json(by_case[case_id])) for case_id in reviewer_sequences[role]],
            "instructions": [f"Use only the {role} directory assigned to you; keep your judgments independent.",
                "Never share the master output or machine-private directory; do not consult another reviewer's package or predictions.",
                "These are preparation packets: no attempt or actual rating exists; unknown observations stay null.",
                "Record any identifiable source clues. Text, source hashes and formatting may reveal a fixture or condition; blinding is limited."]}
        bundle["bundleSha256"] = _sha(bundle)
        reviewer_packets[role] = bundle
    return {"cohort": {"intendedSlots": 108, "nativeAttempts": 0, "modelReviews": 0, "humanReviews": 0,
                       "outcomes": {slot.slot_id: "not-started" for slot in roster}},
            "inputHashes": hashes, "fixtureInventorySha256": inventory.inventory_sha256,
            "promptInventorySha256": inventory.prompts_sha256, "registrationSha256": registration.sha256,
            "auditSelection": selection.as_dict(), "auditAssessment": assessment.as_dict(),
            "machinePackets": machine_packets, "humanReviewerPackets": reviewer_packets,
            "privateBlinding": private_blinding}


def execute_control(repo: Path, case: dict[str, str], *, timeout_seconds: int) -> dict[str, Any]:
    """Execute one fixed unittest oracle with bounded existing process cleanup."""
    started = time.monotonic()
    result = controls._execute_case(repo, case, timeout_seconds)
    counts = re.findall(r"(?m)^Ran (\d+) tests? in ", result["stderr"])
    count = int(counts[0]) if len(counts) == 1 else 0
    status = result["status"] if count == 1 and not result["outputTruncated"] else "failed"
    source = repo.joinpath(*case["test"].split(".")[:2]).with_suffix(".py")
    return {**case, "status": status, "testCount": count, "returnCode": result["returnCode"],
            "testSourceSha256": _sha(source.read_bytes()), "controlWallSeconds": time.monotonic() - started,
            "skipDetected": result["skipDetected"], "timedOut": result["timedOut"],
            "ownedProcessGroupState": result["ownedProcessGroupState"],
            "stdoutUtf8Sha256": _sha(result["stdout"].encode()),
            "stderrUtf8Sha256": _sha(result["stderr"].encode()),
            "limits": ["Exit status and exactly one executed assertion-bearing unittest define this synthetic oracle result; retained output is hashed, not exported."]}


def _write(path: Path, value: Any) -> None:
    raw = value if isinstance(value, bytes) else _json(value) + b"\n"
    controls._write_private(path, raw)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_controls(repo: Path, output_root: Path, *, seed: str,
                 timeout_seconds: int) -> dict[str, Any]:
    if not CASES or type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 300:
        raise ValueError("a nonempty fixed control set and bounded timeout are required")
    repo = repo.resolve(strict=True)
    target = output_root.parent.resolve(strict=True) / output_root.name
    if target == repo or repo in target.parents or target in repo.parents:
        raise ValueError("private control output must be disjoint from the source checkout")
    if target.exists() or target.is_symlink():
        raise FileExistsError("control output requires a new exclusive private directory")
    candidate = _freeze(repo)
    key = secrets.token_bytes(32)
    prepared = prepare_controls(repo, candidate, seed=seed, blinding_key=key)
    target.mkdir(mode=0o700)
    private = target / "machine-private"
    private.mkdir(mode=0o700)
    _write(private / "blinding-key.bin", key)
    _write(private / "blinding-manifest.json", prepared["privateBlinding"])
    _write(private / "manifest.json", {"schema": SCHEMA, "evidenceType": "synthetic-deterministic-controls",
        "candidate": candidate, "auditSelection": prepared["auditSelection"], "cases": CASES, "limits": LIMITS})
    register = coordination.CoordinationRegistry(private / "coordination")
    register.initialize(tuple(coordination.TaskSpec(task_id, owner="synthetic-control-coordinator")
                              for task_id in sorted(coordination.M45_PENDING_TASK_IDS)),
                        candidate_sha256=candidate["commit"])
    register.block("SPEC-044/T001", candidate_sha256=candidate["commit"],
                   reason="Exact real registration approval remains pending; this register is a synthetic demonstration")
    report = {"schema": SCHEMA, "evidenceType": "synthetic-deterministic-controls",
              "createdAtUtc": datetime.now(timezone.utc).isoformat(), "candidate": candidate,
              "interpreter": {"version": platform.python_version(), "implementation": platform.python_implementation(),
                              "executableSha256": _sha(Path(sys.executable).resolve().read_bytes())},
              "domain": "Owned synthetic fixtures and named stdlib unittest assertions; no empirical native acceptance",
              "cohort": prepared["cohort"], "inputHashes": prepared["inputHashes"],
              "fixtureInventorySha256": prepared["fixtureInventorySha256"],
              "promptInventorySha256": prepared["promptInventorySha256"],
              "registrationSha256": prepared["registrationSha256"],
              "auditSelectionSha256": prepared["auditSelection"]["sha256"],
              "auditPolicySha256": _sha(prepared["auditSelection"]["policy"]),
              "auditAssessment": prepared["auditAssessment"], "coordination": register.sanitized_handoff(),
              "humanPacketCount": len(prepared["auditSelection"]["initialSlotIds"]),
              "humanReviewerCount": len(prepared["humanReviewerPackets"]),
              "humanBundleSha256": {role: bundle["bundleSha256"]
                                    for role, bundle in prepared["humanReviewerPackets"].items()},
              "blindingSha256": prepared["privateBlinding"]["blindingSha256"],
              "packetSummaries": [packets.public_packet_summary(item) for item in prepared["machinePackets"]],
              "controls": [], "limits": LIMITS}
    _write(private / "machine-packets.json", {"schema": SCHEMA, "evidenceType": "synthetic-preparation-only",
        "machinePackets": prepared["machinePackets"], "limits": LIMITS})
    for role, bundle in prepared["humanReviewerPackets"].items():
        reviewer_directory = target / role
        reviewer_directory.mkdir(mode=0o700)
        _write(reviewer_directory / "packets.json", bundle)
        _write(reviewer_directory / "INSTRUCTIONS.md",
               (f"# Independent preparation package: {role}\n\n" +
                "\n\n".join(bundle["instructions"]) + "\n").encode("utf-8"))
    for case in CASES:
        _write(private / (case["id"] + ".started.json"), {"schema": SCHEMA, "status": "started", "caseId": case["id"]})
        receipt = execute_control(repo, case, timeout_seconds=timeout_seconds)
        _write(private / (case["id"] + ".result.json"), receipt)
        report["controls"].append(receipt)
    stable = (candidate["sourceManifest"] == _manifest(repo)
              and candidate["commit"] == controls._git(repo, "rev-parse", "HEAD")
              and candidate["workingTreeStatusSha256"] == _sha(controls._git(
                  repo, "status", "--porcelain=v1", "--untracked-files=all").encode()))
    report["sourceUnchanged"] = stable
    report["status"] = "passed" if stable and all(case["status"] == "passed" for case in report["controls"]) else "failed"
    report["reportSha256"] = _sha(report)
    _write(private / "report.json", report)
    return {"schema": SCHEMA, "status": report["status"], "reportSha256": report["reportSha256"],
            "sourceManifestSha256": candidate["sourceManifestSha256"], "controlCount": len(CASES),
            "controlsPassed": sum(case["status"] == "passed" for case in report["controls"]),
            "preparedSlots": 108, "humanPacketCount": report["humanPacketCount"],
            "humanReviewerCount": report["humanReviewerCount"],
            "actualNativeAttempts": 0, "modelReviews": 0, "humanReviews": 0,
            "limits": ["Synthetic control receipts only; 108 native attempts and all actual reviews remain pending."]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        summary = run_controls(Path(__file__).resolve().parents[1], args.output_root,
                               seed=args.seed, timeout_seconds=args.timeout_seconds)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"M4.5 assisted controls unavailable: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(_json(summary).decode("ascii"))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
