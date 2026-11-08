# SPEC-075: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan, contract and
  schema name; decide E1–E5 and OD-2. Dependencies: SPEC-074 contract frozen.
  Verification: procedure_001.

## Phase P1 — export core

- [ ] T002 (REQ-005 / SC-005): Lead creates the manifest schema; schema test
  with valid and broken manifests. Dependencies: T001. Verification: procedure_005.
- [ ] T003 (REQ-002 / SC-002): Consent and redaction filter with exclusion
  counts. Dependencies: T001, SPEC-074 adapter. Verification: procedure_002.
- [ ] T004 (REQ-003 / SC-003): `supervised` writer (`d4FirstAttempt` true only, or
  explicit `outcome` field). Dependencies: T003.
  Verification: procedure_003.
- [ ] T005 (REQ-004 / SC-004): `rollout` writer and both levels.
  Dependencies: T003. Verification: procedure_004.
- [ ] T006 (REQ-005, REQ-006 / SC-005, SC-006): Manifest builder, atomic write,
  determinism test. Dependencies: T002, T004, T005. Verification: procedure_005,
  procedure_006.
- [ ] T007 (REQ-007 / SC-007): Seeded per-task balance for `rollout` exports only. Dependencies: T006.
  Verification: procedure_007.

## Phase P2 — gates and CLI

- [ ] T008 (REQ-008 / SC-008): Terms gate reading the OD-1 decision record.
  Dependencies: T006; OD-1 recorded before any host export. Verification:
  procedure_008.
- [ ] T009 (REQ-009 / SC-009): CLI subcommand and refusals, including
  `export-disabled`. Dependencies: T006.
  Verification: procedure_009.
- [ ] T010 (REQ-010 / SC-010): Canary scan before the manifest is finalised.
  Dependencies: T006, SPEC-074 canary corpus. Verification: procedure_010.
- [ ] T011 (REQ-011 / SC-011): Offline and no-MCP boundary tests.
  Dependencies: T009. Verification: procedure_011.

- [ ] T013 (REQ-013 / SC-013): Source retention in the manifest,
  `retention-expired` refusal, purge listing of citing manifests, and the
  documentation note that exports are outside purge. Dependencies: T006,
  SPEC-074 retention and purge. Verification: procedure_013.

## Closing

- [ ] T012 (REQ-012 / SC-012): Documentation; `speckit-converge`; evidence
  recorded. Dependencies: T002–T011, T013. Verification: procedure_012.
