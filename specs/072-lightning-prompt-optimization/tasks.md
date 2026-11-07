# SPEC-072: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance or support for H1. Parallelizable is a dependency
property and does not authorize concurrent agents. Unattended work runs by
script or test.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan, contract and
  evaluation protocol; decide OD-1 and OD-2. Dependencies: SPEC-071 T011.
  Verification: procedure_001.

## Phase P1 — foundations

- [ ] T002 (REQ-002 / SC-002): `lightning_resources` candidate record and store.
  Dependencies: T001. Verification: procedure_002.
- [ ] T003 (REQ-003 / SC-003): `lightning_algorithm` base and `Baseline`; fake-host
  equality with SPEC-071. Dependencies: T002. Verification: procedure_003.

## Phase P2 — optimizers and controls

- [ ] T004 (REQ-004 / SC-004): `lightning_apo` and Markdown templates with
  hashes. Dependencies: T003. Verification: procedure_004.
- [ ] T005 (REQ-005 / SC-005): `lightning_gepa` from the paper. Dependencies:
  T003. Verification: procedure_005.
- [ ] T006 (REQ-006 / SC-006): Contamination check before every optimizer call.
  Dependencies: T004, T005. Verification: procedure_006.
- [ ] T007 (REQ-007 / SC-007): Budgets and stopping rules. Dependencies: T004,
  T005. Verification: procedure_007.
- [ ] T008 (REQ-010 / SC-010): Lineage, seeds and replay of selection decisions.
  Dependencies: T004–T007. Verification: procedure_010.

## Phase P3 — development runs and freeze

- [ ] T009 (REQ-001 / SC-001): Run APO and GEPA on the development set in each
  required host; freeze `evaluation-protocol.md` by hash in
  `evidence/protocol-freeze.json` before any held-out rollout.
  Dependencies: T008, OD-1, OD-2. Verification: procedure_001.

## Phase P4 — held-out evaluation

- [ ] T010 (REQ-008 / SC-008): Held-out runs of A0, A1, A2; analysis per the
  protocol; report H1 outcome, including a null or negative result.
  Dependencies: T009. Verification: procedure_008.

## Closing

- [ ] T011 (REQ-009 / SC-009): Boundary tests: skill file untouched, no
  promotion, execution or MCP path. Dependencies: T010.
  Verification: procedure_009.
- [ ] T012 (REQ-001–REQ-010 / SC-001–SC-010): `/speckit-converge`: reconcile
  spec, tasks, assurance and evidence; sync tracking; hand the best candidate
  hash to SPEC-073. Dependencies: T011. Verification: all procedures.

## Limits

Results cover the observed host versions, models and prompt sets. A supported
H1 does not promote a candidate; SPEC-073 and the owner decide.
