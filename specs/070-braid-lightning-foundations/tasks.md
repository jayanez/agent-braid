# SPEC-070: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance of ADRs 0039–0042. Parallelizable is a dependency
property and does not authorize concurrent agents.

## Phase 1 — governance

- [x] T001 (REQ-001 / SC-001): Owner review of the program, this spec, ADRs
  0039–0042 and the configuration contract; record decisions in `reviews/`.
  Dependencies: none. Verification: procedure_001.
- [x] T002 (REQ-002 / SC-002): Retain `LICENSES/Agent-Lightning-MIT.txt`, add the
  THIRD_PARTY section and `third-party-inventory.md` with pinned commits and file
  hashes; adaptation notices in every adapted module. Dependencies: none.
  Verification: procedure_002.

## Phase 2 — model and configuration

- [x] T003 (REQ-003 / SC-003): `agent_braid/lightning_schema.py` with
  `tests/test_lightning_schema.py`. Dependencies: T002. Verification: procedure_003.
- [x] T004 (REQ-004 / SC-004): `agent_braid/lightning_config.py`, the published
  schema and the schema/validator agreement test. Dependencies: T003.
  Verification: procedure_004.
- [x] T005 (REQ-005 / SC-005): `agent-braid lightning init|validate|status`
  wizard with preview/apply digests. Dependencies: T004. Verification: procedure_005.

## Phase 3 — store and setup

- [x] T006 (REQ-006 / SC-006): `agent_braid/lightning_store.py` with lock,
  sweep and purge; `lightning purge`. Dependencies: T003. Verification: procedure_006.
- [x] T007 (REQ-007 / SC-007): registry key, `plugin setup --lightning`, setup
  skill step. Dependencies: T004. Verification: procedure_007.

## Phase 4 — boundaries and closure

- [x] T008 (REQ-008 / SC-008): import, socket, process and MCP boundary tests.
  Dependencies: T003–T007. Verification: procedure_008.
- [ ] T009 (REQ-001 / SC-001): ROADMAP track BL, spec and milestone index,
  `github-tracking.json`; after merge, the reviewed tracking reconciliation
  creates milestones BL.0–BL.5 and the task issues (BL.6 tasks under Deferred).
  Dependencies: T001. Verification: procedure_009.
- [ ] T010 (REQ-001 / SC-001): `/speckit-analyze` and `/speckit-converge`;
  freeze the candidate for human review. Dependencies: T001–T009.
  Verification: procedure_001.
