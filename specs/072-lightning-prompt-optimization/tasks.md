# SPEC-072: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance or support for H1. Parallelizable is a dependency
property and does not authorize concurrent agents. Unattended work runs by
script or test.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan, contract and
  evaluation protocol; OD-1 decided 2026-11-11: keep 10 × 3 (OD-2 decided: `claude-code`, `opencode`; Amendment 1, approved 2026-11-13, reduces it to `claude-code`). Dependencies: SPEC-071 T011.
  Verification: procedure_001.

## Phase P1 — foundations

- [x] T002 (REQ-002 / SC-002): `lightning_resources` candidate record and store;
  extend `lightning_store.KINDS` with `candidate` and test it.
  Dependencies: T001. Verification: procedure_002.
- [x] T003 (REQ-003 / SC-003): `lightning_algorithm` base and `Baseline`; fake-host
  equality with SPEC-071. Dependencies: T002. Verification: procedure_003.

## Phase P2 — optimizers and controls

- [x] T004 (REQ-004 / SC-004): `lightning_apo` and Markdown templates with
  hashes. Dependencies: T003. Verification: procedure_004.
- [x] T005 (REQ-005 / SC-005): `lightning_gepa` from the paper; reflection on
  content-free inputs only. Dependencies:
  T003. Verification: procedure_005.
- [x] T006 (REQ-006 / SC-006): Contamination check before every optimizer call;
  optimizer calls in the SPEC-071 disposable profile and sandbox.
  Dependencies: T004, T005. Verification: procedure_006.
- [x] T007 (REQ-007 / SC-007): Budgets per arm run, stopping rules and
  `--resume <run-id>`. Dependencies: T004,
  T005. Verification: procedure_007.
- [x] T008 (REQ-010 / SC-010): Lineage, seeds and replay of selection decisions.
  Dependencies: T004–T007. Verification: procedure_010.

## Phase P3 — development runs and freeze

- [x] T009 (REQ-001 / SC-001): Run APO and GEPA on the development set in each
  required host; freeze `evaluation-protocol.md` by hash in
  `evidence/protocol-freeze.json` before any held-out rollout.
  Dependencies: T008, OD-1. Verification: procedure_001.

## Phase P4 — held-out evaluation

- [x] T010 (REQ-008 / SC-008): Held-out runs of A0, A1, A2; analysis per the
  protocol; report H1 outcome, including a null or negative result.
  Dependencies: T009. Verification: procedure_008. Run 2026-11-13 with
  `scripts/spec072_heldout.py --execute`: A0 25/30, A1 23/30, A2 24/30, all
  miss D4 in claude-code; H1 not supported (negative result).

- [x] T013 (REQ-011 / SC-011): Emit the SPEC-049 `Registration` and
  `EvaluationRecord` pair (A = A0, C = A2 GEPA) from the held-out report;
  verify the formats load through `harness_promotion`. Dependencies: T010.
  Verification: procedure_011. Done 2026-11-13 as the writer
  `agent_braid.lightning_evaluation.spec049_pair`, tested over synthetic
  held-out results; the T010 report calls it with the real summaries.

## Closing

- [x] T011 (REQ-009 / SC-009): Boundary tests: skill file untouched, no
  promotion, execution or MCP path. Dependencies: T010.
  Verification: procedure_009. Done 2026-11-13 as
  `tests/test_lightning_cli.py` `BL2BoundaryTests` over a fake GEPA run and
  every BL.2 module; re-run after T010 lands.
- [ ] T012 (REQ-001–REQ-011 / SC-001–SC-011): `/speckit-converge`: reconcile
  spec, tasks, assurance and evidence; sync tracking; hand the best candidate
  hash to SPEC-073. Dependencies: T011, T013. Verification: all procedures.

## Limits

Results cover the observed host versions, models and prompt sets. A supported
H1 does not promote a candidate; SPEC-073 and the owner decide.
