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

## Separately verifiable technical clauses — owner-approved split

These auxiliary tasks preserve the full criteria of the linked original task.
A completed auxiliary does not complete native-host or human acceptance.

- [ ] T011 (REQ-001/SC-001): Validate the canonical five-skill source/resource format, exact identities, metadata and refusal on extra executable payloads.
  Related original: T001. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T012 (REQ-002/SC-002): Verify static analyze guidance and deterministic analyzer counterparts preserve immutable input/unknown and no-execute boundaries.
  Related original: T002. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T013 (REQ-003/SC-003): Verify static plan guidance and deterministic prepare/refusal counterparts preserve plan digest and absent operator authority.
  Related original: T003. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T014 (REQ-004/SC-004): Verify static execute guidance and deterministic exact-grant/refusal controls; no model-issued grant is claimed.
  Related original: T004. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T015 (REQ-005/SC-005): Verify static recovery guidance and deterministic interrupted/mismatched-run controls.
  Related original: T005. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T016 (REQ-006/SC-006): Verify static evidence guidance and deterministic formatter/export fidelity and unknowns.
  Related original: T006. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T017 (REQ-007/SC-007): Verify static missing-capability guidance and actual local SDK-unavailable read-only fallback refusal.
  Related original: T007. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T018 (REQ-008/SC-008): Verify the static no-hooks/no-secret/no-authority-bypass bundle boundary and deterministic adversarial-input controls.
  Related original: T008. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `integrations/agent-braid/skills; tests/test_tooling_assets.py; MCP/presentation controls`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [ ] T019 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile available static/deterministic evidence and pass repository quick/PR gates without completing the original native-evidence predecessor gate.
  Related original: T009. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `assurance.json; source validation`.
  Verification: `evidence/technical-validation.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.
