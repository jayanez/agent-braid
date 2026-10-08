# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Maintain one Agent Skills-compliant canonical bundle with five matching names/descriptions and minimal host-specific metadata.
  Dependencies: none; consumed contract review. Targets: `integrations/agent-braid/skills; host metadata and bundle format controls`.
  Verification and planned evidence: `validation-plan.md::procedure_portable_bundle`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Guide analyze through immutable input selection, conflict/conditional/unknown explanation and evidence references without execute.
  Dependencies: T001. Targets: `skills/agent-braid-analyze/SKILL.md; analyze journey controls`.
  Verification and planned evidence: `validation-plan.md::procedure_analyze_skill`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Guide plan through existing prepare and disclose order, constraints, plan digest and absent operator authority.
  Dependencies: T001. Targets: `skills/agent-braid-plan/SKILL.md; plan journey controls`.
  Verification and planned evidence: `validation-plan.md::procedure_plan_skill`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Guide execute only for an already granted exact prepared batch, then status and independent verify.
  Dependencies: T001. Targets: `skills/agent-braid-execute/SKILL.md; authority/refusal controls`.
  Verification and planned evidence: `validation-plan.md::procedure_execute_skill`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Guide interruption inspection and bounded recovery using current state, existing authority and verification.
  Dependencies: T001. Targets: `skills/agent-braid-recover/SKILL.md; interruption controls`.
  Verification and planned evidence: `validation-plan.md::procedure_recover_skill`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Guide evidence explanations/exports with input identity, artifact links, observation/assurance limits and unknowns.
  Dependencies: T001–T005. Targets: `skills/agent-braid-evidence/SKILL.md; evidence fidelity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_evidence_skill`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Handle unavailable MCP, skills or unsupported host features with actionable diagnostics and bounded read-only fallback.
  Dependencies: T001–T005. Targets: `skill references/diagnostics; unavailable MCP controls`.
  Verification and planned evidence: `validation-plan.md::procedure_missing_capability`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Separate skill guidance from host permission and grant enforcement, with adversarial instructions and no hooks/helper-agent side effects.
  Dependencies: T001–T005. Targets: `bundle security review; adversarial source/evidence fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_adversarial_guidance`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
