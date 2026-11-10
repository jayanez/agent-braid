# SPEC-071: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance. Parallelizable is a dependency property and does not
authorize concurrent agents. Unattended work runs by script or test, never by
manual copy-paste.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan and contracts; record
  the OD-2 approach and the OD-1 question. Dependencies: SPEC-070 merged.
  Verification: procedure_001.

## Phase P1 — extraction

- [x] T002 (REQ-002 / SC-002): Extract shared host code into
  `agent_braid/lightning_hosts.py`; the driver imports it; capture fake-run
  evidence before and after and compare bytes. Dependencies: T001.
  Verification: procedure_002.

## Phase P2 — runner, reward and controls

- [x] T003 (REQ-003 / SC-003): `lightning_runner` with timeout, kill tree,
  bounded parallel, store writes and state machine; extend
  `lightning_store.KINDS` with `result` and test it. Dependencies: T002.
  Verification: procedure_003.
- [x] T004 (REQ-004 / SC-004): Environment gate and key-source check; research
  the OpenCode key source (OD-2); record T003 evidence for the `none` value. Dependencies: T003. Verification: procedure_004.
- [x] T005 (REQ-005 / SC-005): Credential pass-through and secret scan for both
  OD-1 options, tested with a synthetic token. Dependencies: T004.
  Verification: procedure_005.
- [x] T006 (REQ-006 / SC-006): Budget and quota stops and `run --resume <run-id>`. Dependencies: T003.
  Verification: procedure_006.
- [x] T007 (REQ-007 / SC-007): `lightning_hooks`. Dependencies: T003.
  Verification: procedure_007.
- [x] T008 (REQ-008, REQ-011 / SC-008, SC-011): `lightning_reward`, rollout and
  attempt-result and reward records, replay from content-free parsed attempts. Dependencies: T003. Verification: procedure_008,
  procedure_011.
- [x] T009 (REQ-009 / SC-009): Hidden `.git`, egress denial, canaries, FREEZE
  check. Dependencies: T003, T008. Verification: procedure_009.
- [x] T010 (REQ-010, REQ-012 / SC-010, SC-012): CLI `run --dry-run|--fake-hosts`,
  `status`, `report`; boundary tests. Dependencies: T003–T009.
  Verification: procedure_010, procedure_012.

## Phase P3 — pipeline

- [x] T011 (REQ-013 / SC-013): Fake-host pipeline test with negative variants in
  CI. Dependencies: T010. Verification: procedure_013.

## Phase P4 — real baseline

- [ ] T012 (REQ-014 / SC-014): Owner decides OD-1; owner signs in; one command
  runs the baseline on the subscription route; record evidence and the
  paid-route observation count; label the report `route-changed comparison`. Dependencies: T011, OD-1.
  Verification: procedure_014.

## Closing

- [ ] T013 (REQ-001–REQ-014 / SC-001–SC-014): `/speckit-converge`: reconcile
  spec, tasks, assurance and evidence; sync tracking. Dependencies: T012.
  Verification: all procedures.

## Limits

Fake-host success does not establish host behaviour. The real baseline covers
the observed host versions and models on the development set only.
