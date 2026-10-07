# Tasks

T001 protocol review was explicitly approved by the owner on 2026-10-07 against public commit `3777e578`; see `protocol-review-3777e578.json`. T002–T004 v1 engineering is implemented and reviewed; repository profiles and hosted checks for the integrated v1 candidate are reported separately in PRs #376, #385 and #386. On 2026-10-07 the owner separately approved implementation and evaluation preparation of the prospective 180-minute successor in `successor-protocol-review-20261007.json`; its new candidate validation and preparation remain pending. The frozen 45-minute proposal and historical records are preserved. T005 registered capture and T006 decision remain prospective. Dependencies sequence work; they grant no execution authority.

- [x] T001 (REQ-001,REQ-002/SC-001,SC-002): Freeze the follow-up cost boundaries, corpus, budgets and technical review.
  Dependencies: none. Targets: `specs/022-m4-utility-followup/measurement-protocol.md; frozen workload manifest`.
  Verification and planned evidence: Review the exact prospective manifest, 1.10 descriptive threshold and whole-cost boundary; retain SPEC-021 NO-GO. Record technical review before implementing contract-sensitive instrumentation.

- [x] T002 (REQ-001/SC-001): Implement reconciled phase accounting and diagnostic output.
  Dependencies: T001. Targets: `agent_braid/utility_accounting.py; agent_braid/utility_budget_observer.py; agent_braid/git_replay.py; agent_braid/git_runtime.py; scripts/measure_m4_utility.py; tests/test_utility_accounting.py; tests/test_m4_utility.py`.
  Verification and planned evidence: Run future phase-accounting tests and existing policy/scheduler suites; capture omitted or unavailable counters explicitly. No grant/evidence check may be bypassed.

- [x] T003 (REQ-003/SC-003): Diagnose baseline costs and select at most one contract-preserving improvement.
  Dependencies: T002. Targets: `specs/022-m4-utility-followup/cost-diagnosis.md; targeted runtime coordinator code if justified`.
  Verification and planned evidence: Measure diagnostic fixtures separately from registered results. Record candidate delta or no-change choice before freeze; pass forged/stale/unknown/refusal and recovery controls.

- [x] T004 (REQ-002,REQ-003/SC-002,SC-003): Implement the immutable workload manifest and complete paired runner.
  Dependencies: T003. Targets: `agent_braid/utility_fixtures.py; agent_braid/utility_trials.py; scripts/prepare_m4_utility_trials.py; tests/test_utility_trials.py; tests/test_m4_utility_preparation.py`.
  Verification and planned evidence: Test caps, manifest hash mismatch, ordering, unique private destinations, warm-up exclusion, raw invalid pairs and deterministic tree comparisons.

- [ ] T005 (REQ-001,REQ-002,REQ-003/SC-001,SC-002,SC-003): Freeze a stable candidate and capture full-cost results and fresh process controls.
  Dependencies: T004. Targets: `specs/022-m4-utility-followup/measurement.json; reproduction records; assurance.json`.
  Verification and planned evidence: Run quick then PR and the separately reviewed frozen harness/reproduction; bind environment/input/output hashes. Never substitute unit tests for captured measurements.

- [ ] T006 (REQ-004/SC-004): Prepare bounded utility decision and reconcile tracking only from an explicit new decision.
  Dependencies: T005. Targets: `specs/022-m4-utility-followup/decision-packet.md; eventual founder decision; ROADMAP.md; tracking source`.
  Verification and planned evidence: Report every block, costs, safety and limitations; negative/inconclusive protocol completion is valid. Preserve M4 open and historical NO-GO until a separately recorded founder acceptance. Run source/audit before guarded apply.
