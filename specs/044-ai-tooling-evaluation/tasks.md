# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Preregister exact population, source rights, candidate/input/host/model versions, all attempts, rubric and numerical caps before capture.
  Dependencies: none for drafting the registration; the exact 040–043 candidate, inputs, host/model builds, source rights, reviewers, rubric and numerical caps must be fixed before registration is approved and before any capture. Targets: `evaluation-protocol.md; registration.json; owner source/budget decisions`.
  Verification and planned evidence: `validation-plan.md::procedure_registration_gate`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Obtain actual discovery, five-skill loading and complete basic journey receipts in both selected macOS arm64 hosts.
  Dependencies: approved T001 registration and its exact stable 040–043 candidate. Targets: `actual Codex and Claude receipts; bundle and host inventory`.
  Verification and planned evidence: `validation-plan.md::procedure_actual_host_observation`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Run parity, malformed/stale/unsafe/grant/cancellation/recovery and output-agreement controls with exact oracle outcomes.
  Dependencies: stable 040–043 candidate and frozen control/oracle inputs; paid/provider controls remain subject to approved T001 registration. Targets: `research/tooling_evaluation.py control runner; oracle parity/refusal fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_negative_controls`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Reproduce installed-package/core/protocol controls on clean macOS arm64 and Linux x86_64 environments.
  Dependencies: approved T001 registration and its exact stable 040–043 candidate. Targets: `separate clean macOS/Linux reproduction receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_clean_reproduction`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Compare CLI, MCP-only and MCP-plus-skills on 108 registered attempts with counterbalanced order and no outcome-driven revisions.
  Dependencies: approved T001 registration and stable 040–043 candidate with exact fixture roster, prompts, host/model builds, order and session isolation frozen. Targets: `evaluation harness roster/order/session isolation; 108-slot outcome index`.
  Verification and planned evidence: `validation-plan.md::procedure_three_arm_comparison`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Measure complete setup/provider/tool/runtime/export/user/reviewer costs with unavailable fields explicit and numerical stops enforced.
  Dependencies: T001 for preregistered fields/caps; cost instrumentation and stop controls must be implemented and validated before any T002/T004/T005 actual attempt begins. Complete cost reconciliation depends on all attempted T002–T005 slots and retains unavailable fields, including not-started and interrupted slots. Targets: `cost/time/token/RSS/disk fields and stop controls; accounting receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_complete_cost`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Apply frozen human rubric and descriptive thresholds, report disagreements/missing labels, suppress positive utility claims when missing required costs prevent interpretation and preserve legitimate negative results.
  Dependencies: rubric frozen in T001 before capture; apply only after T002–T006 have retained all intended-attempt denominators, outcomes and cost availability. Targets: `frozen human scoring rubric; adjudication/denominator report`.
  Verification and planned evidence: `validation-plan.md::procedure_interpretation`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Prepare the frozen candidate/evidence decision packet and obtain independent technical review, preserving historical M4 limits and an explicit pending founder decision field.
  Dependencies: T009 repository reconciliation/validation and completed feature-specific observation gates, including T001–T007; the packet requests a founder decision but does not record or imply one. Targets: `frozen candidate/evidence; independent review; decision packet with pending/accepted/rejected status field`.
  Verification and planned evidence: `validation-plan.md::procedure_acceptance_decision`; `evidence/sc-008.json` with candidate/evidence hashes, review findings and packet readiness. The actual founder scope/closure decision is recorded only by T010. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: implementation/control work and evidence obligations T001–T007; do not depend on T008 or T010, which follow validation. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: reconcile available evidence and run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction, independent review or approval. T009 establishes candidate readiness for T008; it does not close the milestone.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T008 packet readiness, T009 validation, completed feature-specific gates and the actual explicit founder decision. Targets: frozen assurance, review record, recorded owner decision and final SPEC-044 closure record.
  Verification and planned evidence: record the founder's accepted, rejected or pending decision and bounded rationale after independent findings are available; close milestone #19 only when all required gates are evidenced and the owner records closure. Source validation and hashes are not approval.
