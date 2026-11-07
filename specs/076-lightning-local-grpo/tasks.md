# SPEC-076: Tasks

Deferred. Only T001 may run before reopening. Completion requires obtained
evidence.

## Phase P0 — reopen gate

- [ ] T001 (REQ-001 / SC-001): Founder go/no-go with evidence for each reopen
  criterion (ADR 0042 accepted, local CUDA GPU, SPEC-075 delivered); decide
  OD-1 to OD-4. Verification: procedure_001.

## Phase P1 — stdlib and CI

- [ ] T002 (REQ-006 / SC-006): Optional extra `lightning-gpu` and import
  boundary test. Dependencies: T001. Verification: procedure_006.
- [ ] T003 (REQ-002 / SC-002): Loopback proxy on `view_serve` helpers.
  Dependencies: T001. Verification: procedure_002.
- [ ] T004 (REQ-003 / SC-003): Forced token IDs and logprobs. Dependencies: T003.
  Verification: procedure_003.
- [ ] T005 (REQ-004 / SC-004): `model_request` events per rollout/attempt.
  Dependencies: T004. Verification: procedure_004.
- [ ] T006 (REQ-005 / SC-005): Pause and resume. Dependencies: T003.
  Verification: procedure_005.
- [ ] T008 (REQ-008 / SC-008): GRPO/RLOO advantage and `per_rollout_mean`.
  Dependencies: T001. Verification: procedure_008.
- [ ] T010 (REQ-010 / SC-010): Difficulty filter and update cap.
  Dependencies: T008. Verification: procedure_010.
- [ ] T013 (REQ-013 / SC-013): No-System-One boundary test. Dependencies: T002.
  Verification: procedure_013.

## Phase P2 — GPU (isolated environment)

- [ ] T007 (REQ-007 / SC-007): Local runner start/stop. Dependencies: T002,
  T005, T006. Verification: procedure_007.
- [ ] T009 (REQ-009 / SC-009): Token-ID trajectory aggregation. Dependencies:
  T005, SPEC-075. Verification: procedure_009.
- [ ] T011 (REQ-011 / SC-011): Async rollout option. Dependencies: T007.
  Verification: procedure_011.
- [ ] T012 (REQ-012 / SC-012): Reward-hacking controls. Dependencies: T007.
  Verification: procedure_012.

## Closing

- [ ] T014 (REQ-014 / SC-014): Budget estimate and `training` proposal review.
  Dependencies: T001. Verification: procedure_014.
- [ ] T015 (REQ-015 / SC-015): Preregistered evaluation; `speckit-converge`.
  Dependencies: T007–T014. Verification: procedure_015.
