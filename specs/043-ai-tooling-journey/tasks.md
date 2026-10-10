# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Experimental implementation and bounded local evidence are present. Original native-host acceptance remains pending; completed technical counterparts are recorded separately below.

- [ ] T001 (REQ-001/SC-001): Provide a reproducible owned synthetic journey from install/discovery through analysis/plan/grant refusal/execute/verify/recovery/export.
  Dependencies: none; consumed contract review. Targets: `docs/tooling/JOURNEY.md; examples/tooling; full fixture workflow`.
  Verification and planned evidence: `validation-plan.md::procedure_full_journey`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [x] T002 (REQ-002/SC-002): Explain decisions with input identity, conflicts/dependencies, conditional premises, unknowns, assurance and observation limits.
  Dependencies: T001. Targets: `tooling_present.py chat summary; classification fidelity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_faithful_summary`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: `evidence/sc-002.json`; complete bounded paired procedure passed at its actual recorded source/input identities. Earlier partial evidence remains historical in assurance.json. Native-host acceptance, registered SPEC-044/T004, human/founder decisions remain separate.

- [ ] T003 (REQ-003/SC-003): Explain advisory order and exact missing authority before opt-in execution.
  Dependencies: T001. Targets: `plan/permission journey explanation; missing-grant fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_authority_journey`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [x] T004 (REQ-004/SC-004): Display actual private-result/verifier state and interruption/recovery outcomes with evidence links.
  Dependencies: T001. Targets: `result/recovery explanation; verifier-state controls`.
  Verification and planned evidence: `validation-plan.md::procedure_result_journey`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: `evidence/sc-004.json`; complete bounded paired procedure passed at its actual recorded source/input identities. Earlier partial evidence remains historical in assurance.json. Native-host acceptance, registered SPEC-044/T004, human/founder decisions remain separate.

- [x] T005 (REQ-005/SC-005): Render an interaction graph with semantic labels, accessible legend and bounded node/edge input.
  Dependencies: T001. Targets: `tooling_present.py graph model/legend; bounded graph controls`.
  Verification and planned evidence: `validation-plan.md::procedure_interaction_graph`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: `evidence/sc-005.json`; complete bounded paired procedure passed at its actual recorded source/input identities. Earlier partial evidence remains historical in assurance.json. Native-host acceptance, registered SPEC-044/T004, human/founder decisions remain separate.

- [x] T006 (REQ-006/SC-006): Export deterministic Markdown, SVG and standalone HTML from selected evidence with hashes and provenance.
  Dependencies: T001–T005. Targets: `tooling_present.py Markdown/SVG/HTML; deterministic export receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_deterministic_export`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: `evidence/sc-006.json`; complete bounded paired procedure passed at its actual recorded source/input identities. Earlier partial evidence remains historical in assurance.json. Native-host acceptance, registered SPEC-044/T004, human/founder decisions remain separate.

- [x] T007 (REQ-007/SC-007): Escape and bound untrusted source/evidence in every export without scripts, remote references or secret inclusion.
  Dependencies: T001–T005. Targets: `tooling_present.py escaping/URI/content limits; injection controls`.
  Verification and planned evidence: `validation-plan.md::procedure_export_security`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: `evidence/sc-007.json`; complete bounded paired procedure passed at its actual recorded source/input identities. Earlier partial evidence remains historical in assurance.json. Native-host acceptance, registered SPEC-044/T004, human/founder decisions remain separate.

- [ ] T008 (REQ-008/SC-008): Provide clear onboarding, diagnostics, raw-evidence access and unsupported-rendering explanations in both hosts.
  Dependencies: T001–T005. Targets: `docs/tooling onboarding/diagnostics; unsupported render fallback`.
  Verification and planned evidence: `validation-plan.md::procedure_onboarding_fallback`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.

## Separately verifiable technical clauses — owner-approved split

These auxiliary tasks preserve the full criteria of the linked original task.
A completed auxiliary does not complete native-host or human acceptance.

- [x] T011 (REQ-001/SC-001): Verify the synthetic local journey preserves typed inputs, candidate/results and refusal boundaries; actual host execution stays with T001.
  Related original: T001. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `tests/test_tooling_mcp.py; tests/test_tooling_present.py`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [x] T012 (REQ-003/SC-003): Verify local formatted grant refusal and operator-scope wording; actual host explanation stays with T003.
  Related original: T003. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `tests/test_tooling_presentation_acceptance.py`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [x] T013 (REQ-008/SC-008): Verify deterministic bounded graph/CLI fallback and actionable diagnosis; visible fallback in each host stays with T008.
  Related original: T008. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `tests/test_tooling_present.py; docs/tooling/JOURNEY.md`.
  Verification: `evidence/technical-clauses.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.

- [x] T014 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile available local presentation evidence and pass repository quick/PR gates, preserving original native-host predecessor gates.
  Related original: T009. Dependencies: available bounded implementation; original acceptance remains separate. Targets: `assurance.json; source validation`.
  Verification: `evidence/technical-validation.json` with frozen candidate/input hashes, actual command, paired controls and stated limits.
  Obtained: Candidate-bound repository quick/PR validation results are recorded in `evidence/technical-validation.json`; raw test skips remain explicit. This does not establish native-host, registered-cohort, human or founder acceptance.
