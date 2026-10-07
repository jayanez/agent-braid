# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Preregister exact population, source rights, candidate/input/host/model versions, all attempts, rubric and numerical caps before capture.
  Dependencies: none; consumed contract review. Targets: `evaluation-protocol.md; registration.json; owner source/budget decisions`.
  Verification and planned evidence: `validation-plan.md::procedure_registration_gate`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Obtain actual discovery, five-skill loading and complete basic journey receipts in both selected macOS arm64 hosts.
  Dependencies: T001. Targets: `actual Codex and Claude receipts; bundle and host inventory`.
  Verification and planned evidence: `validation-plan.md::procedure_actual_host_observation`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Run parity, malformed/stale/unsafe/grant/cancellation/recovery and output-agreement controls with exact oracle outcomes.
  Dependencies: T001. Targets: `research/tooling_evaluation.py control runner; oracle parity/refusal fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_negative_controls`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Reproduce installed-package/core/protocol controls on clean macOS arm64 and Linux x86_64 environments.
  Dependencies: T001. Targets: `separate clean macOS/Linux reproduction receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_clean_reproduction`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Compare CLI, MCP-only and MCP-plus-skills on 108 registered attempts with counterbalanced order and no outcome-driven revisions.
  Dependencies: T001. Targets: `evaluation harness roster/order/session isolation; 108-slot outcome index`.
  Verification and planned evidence: `validation-plan.md::procedure_three_arm_comparison`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Measure complete setup/provider/tool/runtime/export/user/reviewer costs with unavailable fields explicit and numerical stops enforced.
  Dependencies: T001–T005. Targets: `cost/time/token/RSS/disk fields and stop controls; accounting receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_complete_cost`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Apply frozen human rubric and descriptive thresholds, report disagreements/missing labels and preserve legitimate negative results.
  Dependencies: T001–T005. Targets: `frozen human scoring rubric; adjudication/denominator report`.
  Verification and planned evidence: `validation-plan.md::procedure_interpretation`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Freeze candidate/evidence, obtain independent technical review and explicit founder scope/closure decision with historical M4 limits.
  Dependencies: T001–T005. Targets: `frozen candidate/evidence; independent review; explicit founder decision`.
  Verification and planned evidence: `validation-plan.md::procedure_acceptance_decision`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
