# SPEC-082: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here runs an agent, model or container except T011 (exploit agent, only under
SPEC-084, OD-6) and the read-only model reviews of T002 and T012 (OD-4). `executionAuthorization` stays false.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any); decide or defer OD-1..OD-7. There is no ADR of this spec; ADR 0045 is reviewed under SPEC-084.
  Dependencies: none. Target files: `evidence/t001-owner-review.md`.
  Verification: procedure_001. Planned evidence: `evidence/t001-owner-review.md`;
  obtained: that record (2026-11-23). OD-1, OD-2, OD-3 and OD-5 to OD-7 took the
  recommended option. OD-4 took a new option (d): cross adversarial review by Claude
  and Codex, with owner adjudication.
- [x] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage
  each finding (confirmed, partial, rejected with reason). Independent model review,
  not human review. Dependencies: this PR merged. Target files: `review/`,
  `evidence/review/`. Verification: procedure_001. Planned evidence:
  `evidence/review/codex-t002-20261123.json` and its raw output; obtained: both
  (2026-11-24, raw sha256 `41edbc24…`). Ten findings, all confirmed and applied
  (S82-001 to S82-010); for S82-004 the owner chose a separate private-split target
  with descriptive-only results until it is met.

## Phase P1 — formats

- [ ] T003 (REQ-002 / SC-002 REQ-009 / SC-009 REQ-010 / SC-010 REQ-011 / SC-011): Write the four versioned schemas: task record, corpus manifest, QA record and trial
  record, with the closed stratum, partition, QA status and infra-error vocabularies.
  Dependencies: T001 (OD-2, OD-5). Target files:
  `schemas/0.3.0-experimental/harness-task.schema.json`,
  `harness-corpus-manifest.schema.json`, `harness-task-qa.schema.json`,
  `harness-trial-record.schema.json`. Verification: procedure_002, procedure_010.
  Planned evidence: `evidence/t003.json`; obtained: none.
- [ ] T004 (REQ-002 / SC-002 REQ-004 / SC-004 REQ-005 / SC-005): Implement the corpus validator: record shape, hashes, lineage-partition coherence,
  SPEC-049 D1 rules (resolved L3 accepted), origin-specific provenance,
  partition-after-outcome refusal and the REQ-005 private scan (plain identity
  hashes, task ids, long private lines, salted commitments only); one mutation
  control per guard. Dependencies: T003. Target files:
  `agent_braid/harness_task_corpus.py`, `tests/test_harness_task_corpus.py`.
  Verification: procedure_002, procedure_004, procedure_005, then `quick`. Planned
  evidence: `evidence/t004.json`; obtained: none.

## Phase P2 — corpus construction

- [ ] T005 (REQ-003 / SC-003): Freeze the selection rule by SHA-256, then inventory merged PRs from local Git
  history read-only; list every inspected PR as candidate or excluded with a reason
  and record yield. The rule fixes the test-and-fixture path rule, the pre-fix
  application and the counted failure classes (REQ-003). Dependencies: T001 (OD-1,
  OD-2). Target files:
  `scripts/har_corpus_inventory.py`, `corpus/selection-rule.md`,
  `corpus/inventory.json`. Verification: procedure_003. Planned evidence:
  `evidence/t005-inventory.json`; obtained: none.
- [ ] T006 (REQ-004 / SC-004): Assign lineages and partitions (stratified, recorded seed) before any candidate
  outcome, with lineages computed as connected components of recorded relation edges
  and unresolved pairs merged; carry L1–L4 with SPEC-049 D1 rules; owner freezes the
  assignment.
  Dependencies: T004 T005, OD-7. Target files: `corpus/manifest.json`.
  Verification: procedure_004. Planned evidence: `evidence/t006-partition.json`;
  obtained: none.
- [ ] T007 (REQ-005 / SC-005): Set up the private held-out store outside the repository per OD-3; commit only
  salted commitments (salt kept in the private store), counts and strata; start the
  use-count ledger at zero. Dependencies: T006,
  OD-3. Target files: `corpus/manifest.json` (private section),
  `evidence/t007-private-split.json`. Verification: procedure_005. Planned evidence:
  `evidence/t007-private-split.json`; obtained: none.
- [ ] T008 (REQ-002 / SC-002): Construct each task: statement without solution leak, initial-state commit,
  fail-to-pass and pass-to-pass oracle, reference-solution hash, resource budget,
  canary id, rights basis, origin-specific provenance. Dependencies: T006 T007.
  Target files: `corpus/tasks/`
  (public), private store (private-holdout). Verification: procedure_002. Planned
  evidence: `evidence/t008-tasks.json`; obtained: none.

## Phase P3 — task QA

- [ ] T009 (REQ-006 / SC-006): Run the oracle check (3 fresh runs) and the no-op check per task, locally with no
  model; set `rejected` on any other result. Dependencies: T008. Target files:
  `scripts/har_task_qa.py`, `tests/test_har_task_qa.py`. Verification:
  procedure_006. Planned evidence: `evidence/t009-oracle.json`; obtained: none.
- [ ] T010 (REQ-007 / SC-007): Run the deterministic exploit probes (delete or weaken tests, hard-code outputs,
  edit the verifier, forge a score file) per task, with a planted weak verifier as a
  negative control. Dependencies: T009. Target files: `scripts/har_task_qa.py`.
  Verification: procedure_007. Planned evidence: `evidence/t010-probes.json`;
  obtained: none.
- [ ] T011 (REQ-007 / SC-007): Run the exploit agent per task in the venue chosen under OD-6; if no venue is
  available, record every task as `qa-incomplete`. Dependencies: T010, OD-6, SPEC-084
  gates. Target files: `evidence/t011-exploit-agent/`.
  Verification: procedure_007. Planned evidence: `evidence/t011-exploit-agent.json`;
  obtained: none.
- [ ] T012 (REQ-008 / SC-008): Run the OD-4 cross adversarial review per task: blind Claude and Codex reviews with model ids and versions, hashes recorded before either sees the other, two cross-critiques and an owner adjudication for each disagreement.
  Dependencies: T009 T010, OD-4. Target files: `corpus/reviews/` (public tasks and
  receipts), private store (private-holdout details). Verification: procedure_008.
  Planned evidence:
  `evidence/t012-reviews.json`; obtained: none.
- [ ] T013 (REQ-012 / SC-012): Write the contamination record: canary id, public source date and relation to each
  model's stated knowledge cutoff, with the limitation text. Dependencies: T008.
  Target files: `corpus/contamination.json` (public tasks and receipts), private store
  (private-holdout rows). Verification: procedure_012. Planned
  evidence: `evidence/t013-contamination.json`; obtained: none.

## Phase P4 — infrastructure controls

- [ ] T014 (REQ-009 / SC-009 REQ-010 / SC-010 REQ-011 / SC-011): Implement the trial-record validator, the frozen infra classification rule, the run-id
  register with per-trial nonces and provenance-bound results, the REQ-009 accounting
  and stop precedence, and the summary bounds; test on synthetic trial fixtures only,
  with one mutation control per guard. Dependencies: T003, OD-5. Target files:
  `agent_braid/harness_trials.py`, `tests/test_harness_trials.py`. Verification:
  procedure_009, procedure_010, procedure_011, then `quick`. Planned evidence:
  `evidence/t014.json`; obtained: none.
- [ ] T015 (REQ-009 / SC-009): Negative controls: a synthetic job with injected infra errors at, under and over
  the OD-5 threshold; show infra errors are never counted as 0 or pass and the job
  turns `invalid` over the threshold. Dependencies: T014. Target files:
  `tests/test_harness_trials.py`. Verification: procedure_009. Planned evidence:
  `evidence/t015-controls.json`; obtained: none.

## Phase P5 — freeze and handoff

- [ ] T016 (REQ-013 / SC-013): Record the corpus freeze: hashes, counts per partition, stratum and lineage, QA
  status per task, yield against H1, and `executionAuthorization: false`; hand the
  manifest hash to SPEC-083 and SPEC-084. A yield below 20 `qa-passed` tasks is
  recorded as a feasibility result; the `private-holdout` `qa-passed` count is
  recorded against its separate 20-task target (REQ-013). Dependencies: T009–T015.
  Target files:
  `evidence/t016-freeze.json`. Verification: procedure_013. Planned evidence:
  `evidence/t016-freeze.json`; obtained: none.
