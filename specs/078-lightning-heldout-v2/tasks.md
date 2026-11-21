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
  `reviews/`. Before the freeze, correct the analyze skill's coverage sentence
  (owner decision 2026-11-20; `CoverageSentenceTests`), so A0 is the corrected
  guidance. Dependencies: T002. Verification: part of procedure_007.
- [x] T004 (REQ-003, REQ-004, REQ-005 / SC-003, SC-004, SC-005): `scripts/spec078_gate0.py`:
  references, guidance-literal follower with rule
  pins, null baselines. Gate 0 must pass on all 164 cases. Files:
  `scripts/spec078_gate0.py`, `tests/test_spec078_gate0.py`. Dependencies: T002.
  Verification: procedures 003–005 (`python -m scripts.spec078_gate0`, exit 0).
- [x] T005 (REQ-006, REQ-007, REQ-008, REQ-012 / SC-006, SC-007, SC-012): Runner
  prompt sets `v2-*` checked against the SPEC-078 FREEZE, generalized protocol
  freeze check, `v2-test` canary, `is_train` for `v2-feedback`,
  `OPTIMIZER_DENIED` and contamination fingerprints for v2 validation and test;
  `agent_braid/lightning_heldout_v2.py` analysis with the 0/3 review hold;
  boundary tests. Then freeze the protocol, splits, Gate 0 script and A0 skill
  by hash on a `develop` commit. Two PRs: the runner, analysis and
  `scripts/spec078_freeze.py` first; then, after that merges, the freeze
  (`python -m scripts.spec078_freeze` on the `develop` tip, writing
  `prompts/FREEZE.json` and `prompts/fingerprints.json`). Dependencies: T003,
  T004. Verification: procedures 006, 012 (runner PR), 007 (freeze PR).

## Phase P2 — Gate 1

- [x] T011 (REQ-006 / SC-006): Runner keeps one redacted transcript record per
  rollout, only under SPEC-074 consent `redacted` for the `rollout` source, so
  a 0/3 prompt can be reviewed (owner decision 2026-11-21, option 1). Fields
  redacted before they are bounded, a smaller retry when too large, the
  store's content-free stub when a record is not clean, none for a stopped or
  leaking attempt, and a storage failure never changes a rollout; the review
  joins records to results by `attemptId`; no optimizer or export path reads
  it, and no frozen file changes. Files: `agent_braid/lightning_runner.py`,
  `tests/test_spec078_traces.py`. Dependencies: T005. Verification:
  procedure_006.
- [x] T006 (REQ-008 / SC-008): Precondition: SPEC-074 content consent `redacted`
  with retention covering the 0/3 review. With the owner's yes for 300 rollouts, run A0 on
  `v2-test` (`claude-code`, `claude-sonnet-5-5`); review any 0/3 prompt;
  record `evidence/gate1-a0.json` and the OD-1 verdict, and the cause of each
  0/3 prompt (`evidence/gate1-diagnosis.json`). Dependencies: T005, T011.
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

Adopted disposition (2026-11-21): T008 and T009 are cancelled, not completed
(owner records `evidence/t008-owner-disposition-2026-11-21.json` and
`evidence/t009-owner-disposition-2026-11-21.json`). The original lines and
checkboxes above stay unchanged; Amendment 1 replaces them with T012–T015.
The coordinator binds both records in `task_cancellations` of the tracking
configuration after this merges.

## Phase P3a — Amendment 1: hand fix on a fresh split

- [x] T012 (REQ-013 / SC-013): Add the two kind-selection sentences of the
  Gate 1 diagnosis to the analyze skill (never `units` for a parallel or
  overlap question; placeholder digests are expected for `aim`) and pin them
  (`KindSelectionTests`). Files: the skill, `tests/test_spec078_kind_guidance.py`.
  Dependencies: T006. Verification: procedure_013.
- [x] T013 (REQ-014 / SC-015): Build a fresh `v3-test` split (100 prompts, the
  ten classes) from new templates and a new seed, not derived from v2 traces or
  prompts; record the generator and seed; check 8-word window disjointness
  against v1, v2 and the skill; run Gate 0 references and null baselines on it
  before any rollout; add `v3-test` to the runner. Dependencies: T012.
  Verification: procedure_014.
- [x] T014 (REQ-014 / SC-014): Freeze the v3 split, the protocol amendment and
  the fixed skill by hash on a `develop` commit after T012 and T013 merge.
  Dependencies: T012, T013. Verification: procedure_016 (freeze part;
  `evidence/v3-freeze.json`, `spec078_freeze_v3 --check`).
- [ ] T015 (REQ-014 / SC-014): With the owner's yes for 300 rollouts (given
  2026-11-21 with option 4), run the fixed skill as A0' once on `v3-test`
  (`claude-code`, `claude-sonnet-5-5`), review any 0/3 prompt, and record the
  OD-1 verdict. Dependencies: T014. Verification: procedure_016 (run part).

## Phase P4 — convergence

- [ ] T010: Converge (`speckit-converge`), record the outcome in `spec.md`, freeze
  this specification on a `develop` commit, report to the coordinator.
  Dependencies: T007 or T015. Verification: `python -m scripts.validate_spec_kit`
  in a clean clone; every exit scenario has obtained evidence or a recorded
  reason. Completion means the protocol ran, not that H-A0 or H-G2 holds.
