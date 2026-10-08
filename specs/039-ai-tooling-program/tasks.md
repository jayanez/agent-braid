# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Separate current capability, planned integration, evidence and adoption in a versioned matrix for Codex and Claude Code.
  Dependencies: none; consumed contract review. Targets: `capability-matrix.md`.
  Verification and planned evidence: `validation-plan.md::procedure_capability_matrix`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Keep M4.5 adjacent to M4 while preserving the whole-M4 open state, G4 NO-GO and independent M3/M3.5 gates.
  Dependencies: T001. Targets: `program.md; historical M4 boundary audit`.
  Verification and planned evidence: `validation-plan.md::procedure_m4_boundary`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Maintain six subordinate specs with stable requirement/scenario/task identities and complete evidence obligations.
  Dependencies: T001. Targets: `specs/039–044; analysis.md`.
  Verification and planned evidence: `validation-plan.md::procedure_traceability`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Propose the portable architecture through ADR 0021 without rewriting constitutional or runtime authority.
  Dependencies: T001. Targets: `docs/adr/0021-codex-claude-tooling-integration.md`.
  Verification and planned evidence: `validation-plan.md::procedure_architecture_review`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Record official-source research with retrieval date, chosen versions, alternatives and unverified host claims.
  Dependencies: T001. Targets: `research.md`.
  Verification and planned evidence: `validation-plan.md::procedure_research_provenance`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Prepare one milestone, six parents and every task subissue under governed reviewed-source tracking.
  Dependencies: T001–T005. Targets: `issue-drafts.md; docs/development/github-tracking.json; tracking receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_tracking_scope`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Document five future routes and explicitly defer Cursor, VS Code/Copilot, OpenCode and pi from v1.
  Dependencies: T001–T005. Targets: `program.md future routes`.
  Verification and planned evidence: `validation-plan.md::procedure_future_scope`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Require candidate-bound technical review, actual host evidence and explicit founder acceptance before M4.5 closure.
  Dependencies: T001–T005. Targets: `SPEC-044 decision packet; future closure record`.
  Verification and planned evidence: `validation-plan.md::procedure_closure_boundary`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
