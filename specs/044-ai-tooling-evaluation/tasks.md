# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Some targets already have an experimental implementation candidate; all product evidence and task completion remain pending. Human outcome ratings and adjudication are explicitly deferred by [the owner decision](human-evaluation-deferral-clarification.md); this does not mark any task or human acceptance complete.

- [ ] T001 (REQ-001/SC-001): Preregister exact population, source rights, candidate/input/host/model versions, all attempts, rubric and numerical caps before capture.
  Dependencies: none for drafting the registration; the exact 040–043 candidate, inputs, host/model builds, source rights, mandatory included-subscription-only `billingPolicy`, two unique abstract independent reviewer roles, approved human-evaluation deferral record, frozen rubric and numerical caps must be fixed before technical registration is approved and capture. Keep `humanReviewers` empty in v3; future identities and human ratings require a separately bound addendum. Targets: `evaluation-protocol.md; registration.json; owner source/budget decisions`.
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

- [ ] T006 (REQ-006/SC-006): Measure technical setup/provider/tool/runtime/export/user costs and technical wall time with receipt hashes; keep the two reviewer-role fee/time fields unknown, enforce numerical stops, and distinguish technical accounting from full human-inclusive economic completion. The T006 technical portion may complete while human-inclusive accounting remains pending.
  Dependencies: T001 for preregistered fields/caps; cost instrumentation and stop controls must be implemented and validated before any T002/T004/T005 actual attempt begins. Complete cost reconciliation depends on all attempted T002–T005 slots and retains unavailable fields, including not-started and interrupted slots. Targets: `cost/time/token/RSS/disk fields and stop controls; accounting receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_complete_cost`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Complete and report technical interpretation against the already frozen rubric/thresholds while human outcome labels and adjudication remain deferred; preserve all 108 outcomes, denominators, disagreements/missing labels as pending, suppress positive utility claims when missing required costs prevent interpretation and preserve legitimate negative results. T007 remains partially pending until its separate human portion is complete.
  Dependencies: frozen rubric in T001 before capture; the technical portion may complete after T002–T006 retain all 108 intended-attempt denominators, outcomes, measured user/setup/attempt costs and wall receipts. Reviewer fee/time and combined human-inclusive totals remain unavailable until the later addendum. Human identities, ratings and adjudication require a later addendum bound to the immutable technical registration. Targets: `technical interpretation/denominator report; later human scoring and adjudication addendum`. Status: technical portion may complete; human portion is explicitly pending.
  Verification and planned evidence: `validation-plan.md::procedure_interpretation`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Prepare the frozen candidate/evidence decision packet and obtain independent technical review, preserving historical M4 limits and an explicit pending founder decision field.
  Dependencies: T009 repository reconciliation/validation, T001–T006, completed technical T007, and candidate-bound technical observations/reproduction. The packet records human outcome evaluation pending and requests a founder decision without recording or implying one; it does not depend on deferred human T007 or T010. Targets: `frozen technical candidate/evidence; independent technical review; decision packet with human phase explicitly pending`.
  Verification and planned evidence: `validation-plan.md::procedure_acceptance_decision`; `evidence/sc-008.json` with candidate/evidence hashes, review findings and packet readiness. The actual founder scope/closure decision is recorded only by T010. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: implementation/control work and technical evidence T001–T006 plus the technical portion of T007; do not depend on deferred human scoring, T008 or T010, which follow technical validation. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: reconcile available evidence and run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction, independent review or approval. T009 establishes candidate readiness for T008; it does not close the milestone.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T008 technical packet readiness, T009 validation, all applicable technical gates, later human addendum/ratings/adjudication, independent review and the actual explicit founder decision. Until these occur T010 remains pending. Targets: frozen assurance, review record, recorded owner decision and final SPEC-044 closure record.
  Verification and planned evidence: record the founder's accepted, rejected or pending decision and bounded rationale after independent findings are available; close milestone #19 only when all required gates are evidenced and the owner records closure. Source validation and hashes are not approval.
