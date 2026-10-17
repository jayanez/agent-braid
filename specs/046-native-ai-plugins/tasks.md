# SPEC-046: Tasks

Stable source IDs; task completion does not imply native/provider or founder acceptance.

- [x] T001 (REQ-001 / SC-001): Specification and architecture.
  Dependencies: none. Verification: procedure_001 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T002 (REQ-002 / SC-002): Self-contained runtime.
  Dependencies: T001. Verification: procedure_002 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T003 (REQ-003 / SC-003): User registry and MCP routing.
  Dependencies: T001. Verification: procedure_003 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T004 (REQ-004 / SC-004): Repository discovery.
  Dependencies: T003. Verification: procedure_004 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T005 (REQ-005 / SC-005): Onboarding wizard.
  Dependencies: T003, T004. Verification: procedure_005 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T006 (REQ-006 / SC-006): Codex plugin.
  Dependencies: T002, T005. Verification: procedure_006 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T007 (REQ-007 / SC-007): Claude Code plugin.
  Dependencies: T002, T005. Verification: procedure_007 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T008 (REQ-008 / SC-008): Lifecycle and migration.
  Dependencies: T003, T006, T007. Verification: procedure_008 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T009 (REQ-009 / SC-009): Distribution and technical acceptance.
  Dependencies: T002–T008. Verification: procedure_009 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T010 (REQ-010 / SC-010): Documentation and tracking.
  Dependencies: T001–T009. Verification: procedure_010 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T011 (REQ-011 / SC-011): OpenAI candidacy.
  Dependencies: T001, T002. Verification: procedure_011 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T012 (REQ-012 / SC-012): Anthropic candidacy.
  Dependencies: T001, T002. Verification: procedure_012 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T013 (REQ-013 / SC-013): Shell installer.
  Dependencies: T002, T003. Verification: procedure_013 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [ ] T014 (REQ-011 / SC-011): OpenAI partner eligibility and external approval.
  Dependencies: T011, T009. Verify owner eligibility, obtain publication decision, submit via authorized portal and record provider disposition. Documentary preparation alone does not close this item.

- [ ] T015 (REQ-012 / SC-012): Anthropic executable/size exception and external approval.
  Dependencies: T012, T009. Resolve bundled-runtime restrictions via an authorized review route, obtain publication decision and record directory/official-marketplace dispositions separately. Do not replace bundled runtime with external prerequisites.

## Remaining acceptance boundaries

T005/T006/T007 have actual agent-operated native macOS setup/product-skill
journeys, including bounded discovery, exact preview/apply, immutable binding
reconnection and two-workspace MCP analysis. Codex additionally observed explicit
cancellation before apply. The historical Claude login refusal was resolved by
native login before its successful journey. T008 has real native alpha.1 → alpha.2
updates and unchanged registry/result bytes for both hosts on macOS and emulated
Linux. T009 has the public distribution branch/tag, exact fresh clone inventory
and literal remote curl installation for both hosts on both observed platforms.
T010 updates the English installation and source tracking map. The prior
integrated audit returned `operations: []` with 15 linked tasks, independently
read back in the private Project. Final reconciliation is applied only from
merged clean sources; its empty post-audit and Project readback are retained
privately after integration.
See release-acceptance.md for exact observation boundaries.
T011/T012 completion is documentary preparation only; T014/T015 keep external
eligibility, contact/submission and approval independent. No provider submission
messages have been sent. Historical 108 attempts and human/scientific/final M4.5
gates remain unchanged.
