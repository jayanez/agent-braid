# SPEC-078: Tasks

**Milestone:** BL.2b — Lightning held-out re-evaluation.

Stable task IDs. Completion requires obtained evidence; task completion does not
imply owner acceptance or support for H-A0 or H-G2. Parallelizable is a
dependency property and does not authorize concurrent agents. One pull request
per task; the owner approves each merge.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — measurement repair

- [x] T001 (REQ-001 / SC-001): Narrow the analyze skill's dependency read rule and
  pin it (`DependencyReadRuleTests`); freeze SPEC-069 and SPEC-072 assurance
  historical at develop `3299ade8` because their evidence binds the old skill
  bytes. Ships in the next alpha. Merged in PR jayanez/agent-braid#1445 (develop
  `08bbffa2`); evidence procedure_001. Files: the skill,
  `tests/test_spec069_guidance.py`, `docs/tooling/NATIVE_PLUGINS.md`, SPEC-069/072
  `assurance.json`. Dependencies: none. Verification: procedure_001
  (`.venv-speckit/bin/python -m unittest tests.test_spec069_guidance`).
- [x] T002 (REQ-002 / SC-002): Class plan, templates and
  `scripts/spec078_build_set.py`; write the three splits (24 / 40 / 100) with
  `class` and `facts`; per-split templates; the REQ-002 build checks (fixture
  paths, prompt-facts agreement, 8-word window disjointness, v1 overlap); a
  derived receipt of the BL.2 re-scoring behind the HELD-02/06 diagnosis. The
  author does not read v1 failure transcripts while writing templates. Files: `scripts/spec078_build_set.py`,
  `specs/078-lightning-heldout-v2/prompts/*.json`, `tests/test_spec078_set.py`.
  Dependencies: T001. Verification: procedure_002 (`python -m unittest
  tests.test_spec078_set`; `python -m scripts.spec078_build_set --check`).

## Phase P1 — Gate 0 and freeze

- [ ] T003 (REQ-007 / SC-007): Write `evaluation-protocol.md` (OD-1 to OD-3,
  analysis, Gate 2 caps, stopping rules); owner review recorded in
  `reviews/`. Dependencies: T002. Verification: part of procedure_007.
- [x] T004 (REQ-003, REQ-004, REQ-005 / SC-003, SC-004, SC-005): `scripts/spec078_gate0.py`:
  references, guidance-literal follower with rule
  pins, null baselines. Gate 0 must pass on all 164 cases. Files:
  `scripts/spec078_gate0.py`, `tests/test_spec078_gate0.py`. Dependencies: T002.
  Verification: procedures 003–005 (`python -m scripts.spec078_gate0`, exit 0).
- [ ] T005 (REQ-006, REQ-007, REQ-008, REQ-012 / SC-006, SC-007, SC-012): Runner
  prompt sets `v2-*` checked against the SPEC-078 FREEZE, generalized protocol
  freeze check, `v2-test` canary, `is_train` for `v2-feedback`,
  `OPTIMIZER_DENIED` and contamination fingerprints for v2 validation and test;
  `agent_braid/lightning_heldout_v2.py` analysis with the 0/3 review hold;
  boundary tests. Then freeze the protocol, splits, Gate 0 script and A0 skill
  by hash on a `develop` commit. Dependencies: T003, T004. Verification:
  procedures 006, 007, 012.

## Phase P2 — Gate 1

- [ ] T006 (REQ-008 / SC-008): Precondition: SPEC-074 content consent `redacted`
  with retention covering the 0/3 review. With the owner's yes for 300 rollouts, run A0 on
  `v2-test` (`claude-code`, `claude-sonnet-5-5`); review any 0/3 prompt;
  record `evidence/gate1-a0.json` and the OD-1 verdict. Dependencies: T005.
  Verification: procedure_008.
- [ ] T007 (REQ-009 / SC-009): Only if A0 meets: publish the regression suite
  and its command; Gate 2 stays closed. Dependencies: T006.
  Verification: procedure_009.

## Phase P3 — Gate 2 (only if A0 misses)

- [ ] T008 (REQ-010 / SC-010): `lightning_edits` bounded-edit arm on feedback and
  validation splits. Dependencies: T006. Verification: procedure_010, and
  procedure_012 re-run over `lightning_edits`.
- [ ] T009 (REQ-011 / SC-011): With the owner's yes for the stated count, run the
  final candidate once on `v2-test` and on SPEC-069 v1 held-out; paired exact
  test vs A0. Dependencies: T008. Verification: procedure_011.

## Phase P4 — convergence

- [ ] T010: Converge (`speckit-converge`), record the outcome in `spec.md`, freeze
  this specification on a `develop` commit, report to the coordinator.
  Dependencies: T007 or T009. Verification: `python -m scripts.validate_spec_kit`
  in a clean clone; every exit scenario has obtained evidence or a recorded
  reason. Completion means the protocol ran, not that H-A0 or H-G2 holds.
