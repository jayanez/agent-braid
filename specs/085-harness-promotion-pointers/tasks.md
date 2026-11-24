# SPEC-085: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here moves a real label, activates a profile or grants execution before T001
records the owner decisions. `executionAuthorization` is false throughout.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any); decide or defer OD-1 to OD-7 in a dated record.
  Dependencies: none. Target files: `specs/085-harness-promotion-pointers/evidence/`.
  Verification: procedure_001. Planned evidence: `evidence/t001-owner-review.md`;
  obtained: that record (2026-11-24). Every decision took the recommended option;
  OD-3 adds that each interaction states when, where and how to run the owner script.
  REQ-005 now requires the bound regression acknowledgement from SPEC-083 S83-005.
- [ ] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage each finding (confirmed, fixed, rejected with reason).
  Dependencies: this PR merged. Target files: `specs/085-harness-promotion-pointers/review/`.
  Verification: procedure_010. Planned evidence: `evidence/t002-codex-review.json`
  and its raw output; obtained: none. Independent model review, not human review.

## Phase P1 — format and module (unpublished)

- [ ] T003 (REQ-002 / SC-002 REQ-004 / SC-004): Write the `braid-harness-pointers/v0.1` journal format: record fields, hash chain, bounds and fixed reason codes.
  Dependencies: T001 (OD-1, OD-6). Target files:
  `specs/085-harness-promotion-pointers/contracts/pointer-journal.md`.
  Verification: procedure_002 and procedure_004. Planned evidence: `evidence/t003-format.json`;
  obtained: none.
- [ ] T004 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004): Implement replay, owner-only moves and the extend-only atomic save.
  Dependencies: T003. Target files: `agent_braid/harness_pointers.py`,
  `tests/test_harness_pointers.py`. `agent_braid/harness_promotion.py` unchanged.
  Verification: procedure_002, procedure_003 and procedure_004, then `quick`. Planned evidence:
  `evidence/t004-module.json`; obtained: none.
- [ ] T005 (REQ-005 / SC-005 REQ-006 / SC-006): Implement the evidence gates for `candidate` and `adopted` against SPEC-083 verdicts and T013 decisions.
  Dependencies: T004; SPEC-083 verdict format approved; T001 (OD-5).
  Target files: `agent_braid/harness_pointers.py`, `tests/test_harness_pointers.py`.
  Verification: procedure_005 and procedure_006, then `quick`. Planned evidence:
  `evidence/t005-gates.json`; obtained: none.
- [ ] T006 (REQ-007 / SC-007): Implement rollback as a repoint with revocation checks per OD-4.
  Dependencies: T004; T001 (OD-4). Target files: `agent_braid/harness_pointers.py`,
  `tests/test_harness_pointers.py`. Verification: procedure_007, then `quick`.
  Planned evidence: `evidence/t006-rollback.json`; obtained: none.
- [ ] T007 (REQ-003 / SC-003 REQ-009 / SC-009): Add negative controls: agent and automatic-policy actors refused, no caller moves a label from an evaluation result, a move writes only the journal.
  Dependencies: T005 T006. Target files: `tests/test_harness_pointers.py`.
  One mutation control per guard. Verification: procedure_003 and procedure_009. Planned evidence:
  `evidence/t007-controls.json`; obtained: none.

## Phase P2 — surfaces

- [ ] T008 (REQ-008 / SC-008): Extend `harness registry-status` with a read-only pointer view and divergence report.
  Dependencies: T004. Target files: `agent_braid/harness_cli.py`,
  `tests/test_harness_cli.py`. Verification: procedure_008, then `quick`.
  Planned evidence: `evidence/t008-cli-view.json`; obtained: none.
- [ ] T009 (REQ-003 / SC-003 REQ-009 / SC-009): Add the owner-run move script outside the plugin launch (OD-3 (a)) or record the OD-3 alternative.
  Dependencies: T005 T006; T001 (OD-2, OD-3). Target files:
  `scripts/har_pointer_move.py`, `tests/test_har_pointer_move.py`.
  Verification: procedure_009. Planned evidence: `evidence/t009-script.json`;
  obtained: none.
- [ ] T010 (REQ-008 / SC-008): Add the pointer view to the SPEC-080 `harness` skill text; no write instruction.
  Dependencies: T008; SPEC-080 approved. Target files:
  `integrations/agent-braid/plugin/harness/SKILL.md` (planned by SPEC-080).
  Verification: procedure_008. Planned evidence: `evidence/t010-skill.json`;
  obtained: none.

## Phase P3 — rehearsal and release

- [ ] T011 (REQ-004 / SC-004 REQ-007 / SC-007 REQ-009 / SC-009): Rehearse on synthetic fixtures: move, rollback, forged record, concurrent write; record outcomes.
  Dependencies: T007 T008 T009. Target files:
  `specs/085-harness-promotion-pointers/evidence/`. Verification: procedure_011.
  Planned evidence: `evidence/t011-rehearsal.json`; obtained: none. Synthetic
  fixtures only; no real label is moved.
- [ ] T012 (REQ-001 / SC-001 REQ-008 / SC-008): Record the release decision under OD-7, or a no-release outcome; update `docs/tooling/HARNESSING.md` only if released.
  Dependencies: T002 T011; owner acceptance of the candidate. Target files:
  `docs/tooling/HARNESSING.md`. Verification: procedure_012. Planned evidence:
  `evidence/t012-release.json`; obtained: none.
