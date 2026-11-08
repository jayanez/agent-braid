# SPEC-073: Tasks

Stable task IDs. Completion requires obtained evidence; completion does not
imply release or owner acceptance. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P1 — record and preview

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan and contracts; OD-1 to
  OD-3 decided and recorded under Clarifications. Dependencies: none.
  Verification: review record bound to a frozen commit.
- [ ] T002 (REQ-001 / SC-001): `lightning_promote.build_record` with the scope
  map and content-addressed text lookup; tests for unknown scope, digest
  mismatch and oversize text; consume the SPEC-072 SPEC-049 pair; refuse
  without H1 `supported` unless an owner override reason is recorded.
  Dependencies: T001, SPEC-072 T013 (pair format).
  Verification: procedure_001.
- [ ] T003 (REQ-003 / SC-003): `preview` and CLI `lightning promote` (no
  writes) with preview digest. Dependencies: T002. Verification: procedure_003.
- [ ] T004 (REQ-008 / SC-008): boundary tests (no socket, no subprocess,
  standard-library imports, bounded write set). Dependencies: T002.
  Verification: procedure_008.

## Phase P2 — decision, apply and build

- [ ] T005 (REQ-002 / SC-002): apply path calling `decide()` with a human actor,
  `begin`, atomic write, `commit`, and `abort` on failure. Dependencies: T003.
  Verification: procedure_002.
- [ ] T006 (REQ-004 / SC-004): build check in `plugin_package` with the
  mismatch message. Dependencies: T005. Verification: procedure_004.

## Phase P3 — reversal and reflections

- [ ] T007 (REQ-005 / SC-005): rollback preview and apply. Dependencies: T005.
  Verification: procedure_005.
- [ ] T008 (REQ-006 / SC-006): revocation preview and apply. Dependencies: T005.
  Verification: procedure_006.
- [ ] T009 (REQ-007 / SC-007): `propose_reflections` through
  `ExperienceStore.add`; assert `activate` is never called. Dependencies: T002.
  Verification: procedure_007.

## Closing

- [ ] T010 (REQ-002, REQ-004, REQ-005 / SC-002, SC-004, SC-005): the owner runs
  decide → begin → commit on one candidate, rebuilds the plugin and runs
  rollback through one script; evidence recorded. Dependencies: T006, T007.
  Verification: procedure_009.
- [ ] T011 (REQ-001–REQ-008 / SC-001–SC-008): converge: `speckit-analyze`,
  tracking and docs synced, `quick` green, assurance obtained evidence filled.
  Dependencies: T001–T010.

## Verification procedure

Each task runs its procedure from [validation-plan.md](validation-plan.md),
then `quick`; evidence files go under `evidence/` with command, hashes and
outcome.
