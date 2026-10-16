# SPEC-046 issue drafts

Parent: SPEC-046 — Native AI plugins; milestone M4.5 #19.

- [x] T001 (REQ-001 / SC-001): Specification and architecture.
  Dependencies: none. Verification: procedure_001 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T002 (REQ-002 / SC-002): Self-contained runtime.
  Dependencies: T001. Verification: procedure_002 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T003 (REQ-003 / SC-003): User registry and MCP routing.
  Dependencies: T001. Verification: procedure_003 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T004 (REQ-004 / SC-004): Repository discovery.
  Dependencies: T003. Verification: procedure_004 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T005 (REQ-005 / SC-005): Onboarding wizard.
  Dependencies: T003, T004. Verification: procedure_005 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T006 (REQ-006 / SC-006): Codex plugin.
  Dependencies: T002, T005. Verification: procedure_006 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T007 (REQ-007 / SC-007): Claude Code plugin.
  Dependencies: T002, T005. Verification: procedure_007 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T008 (REQ-008 / SC-008): Lifecycle and migration.
  Dependencies: T003, T006, T007. Verification: procedure_008 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T009 (REQ-009 / SC-009): Distribution and technical acceptance.
  Dependencies: T002–T008. Verification: procedure_009 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T010 (REQ-010 / SC-010): Documentation and tracking.
  Dependencies: T001–T009. Verification: procedure_010 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T011 (REQ-011 / SC-011): OpenAI candidacy.
  Dependencies: T001, T002. Verification: procedure_011 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T012 (REQ-012 / SC-012): Anthropic candidacy.
  Dependencies: T001, T002. Verification: procedure_012 in validation-plan.md. Evidence: evidence/engineering.json.

- [x] T013 (REQ-013 / SC-013): Shell installer.
  Dependencies: T002, T003. Verification: procedure_013 in validation-plan.md. Evidence: evidence/engineering.json.

- [ ] T014 (REQ-011 / SC-011): OpenAI partner eligibility and external approval.
  Dependencies: T011, T009. Verify owner eligibility, obtain publication decision, submit via authorized portal and record provider disposition. Documentary preparation alone does not close this item.

- [ ] T015 (REQ-012 / SC-012): Anthropic executable/size exception and external approval.
  Dependencies: T012, T009. Resolve bundled-runtime restrictions via an authorized review route, obtain publication decision and record directory/official-marketplace dispositions separately. Do not replace bundled runtime with external prerequisites.


Bodies inherit requirement/scenario, dependencies, verification and evidence links
from tasks.md and the reconciler. Source completion reflects only the bounded
engineering/documentary criteria stated there. Native interactive and external
acceptance remain open. Remote creation is authorized by the owner-approved plan;
apply only from integrated clean sources with milestone/ID allowlist and reviewed
digest. Read back issue/subissue links and Project state separately.
