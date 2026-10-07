# Tasks

T001 protocol review was explicitly approved by the owner on 2026-10-07 against public commit `3777e578`; see `protocol-review-3777e578.json`. Remaining tasks are prospective. Dependencies sequence work; they grant no execution authority.

- [x] T001 (REQ-001,REQ-002/SC-001,SC-002): Freeze the follow-up cost boundaries, corpus, budgets and technical review.
  Dependencies: none. Targets: `specs/022-m4-utility-followup/measurement-protocol.md; frozen workload manifest`.
  Verification and planned evidence: Review the exact prospective manifest, 1.10 descriptive threshold and whole-cost boundary; retain SPEC-021 NO-GO. Record technical review before implementing contract-sensitive instrumentation.

- [ ] T002 (REQ-001/SC-001): Implement reconciled phase accounting and diagnostic output.
  Dependencies: T001. Targets: `scripts/measure_m4_utility.py; agent_braid/runtime_policy.py; agent_braid/runtime_scheduler.py; tests/test_m4_utility.py`.
  Verification and planned evidence: Run future phase-accounting tests and existing policy/scheduler suites; capture omitted or unavailable counters explicitly. No grant/evidence check may be bypassed.

- [ ] T003 (REQ-003/SC-003): Diagnose baseline costs and select at most one contract-preserving improvement.
  Dependencies: T002. Targets: `specs/022-m4-utility-followup/cost-diagnosis.md; targeted runtime coordinator code if justified`.
  Verification and planned evidence: Measure diagnostic fixtures separately from registered results. Record candidate delta or no-change choice before freeze; pass forged/stale/unknown/refusal and recovery controls.

- [ ] T004 (REQ-002,REQ-003/SC-002,SC-003): Implement the immutable workload manifest and complete paired runner.
  Dependencies: T003. Targets: `scripts/measure_m4_utility.py; tests/test_m4_utility.py; synthetic owned Git fixtures`.
  Verification and planned evidence: Test caps, manifest hash mismatch, ordering, unique private destinations, warm-up exclusion, raw invalid pairs and deterministic tree comparisons.

- [ ] T005 (REQ-001,REQ-002,REQ-003/SC-001,SC-002,SC-003): Freeze a stable candidate and capture full-cost results and fresh process controls.
  Dependencies: T004. Targets: `specs/022-m4-utility-followup/measurement.json; reproduction records; assurance.json`.
  Verification and planned evidence: Run quick then PR and the separately reviewed frozen harness/reproduction; bind environment/input/output hashes. Never substitute unit tests for captured measurements.

- [ ] T006 (REQ-004/SC-004): Prepare bounded utility decision and reconcile tracking only from an explicit new decision.
  Dependencies: T005. Targets: `specs/022-m4-utility-followup/decision-packet.md; eventual founder decision; ROADMAP.md; tracking source`.
  Verification and planned evidence: Report every block, costs, safety and limitations; negative/inconclusive protocol completion is valid. Preserve M4 open and historical NO-GO until a separately recorded founder acceptance. Run source/audit before guarded apply.
