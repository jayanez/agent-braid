# SPEC-083: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here runs trials, launches a host, issues a grant or moves a promotion label.
`executionAuthorization` is false for every task.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any; none for this spec); decide or defer OD-1..OD-6.
  Dependencies: none. Target files: `specs/083-capability-regression-evals/evidence/`.
  Verification: procedure_001. Planned evidence: `evidence/t001-owner-review.md`;
  obtained: that record (2026-11-23). Every decision took the recommended option:
  δ = 0.10 with one-sided α = 0.05; analytic task-clustered error as primary, with
  bootstrap and lineage clustering as sensitivity checks; infrastructure limits as in
  SPEC-082; private split refreshed after 5 gate uses; per-task regressions reported
  only in v0.1.
- [x] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage
  each finding (confirmed, fixed, rejected with reason). Independent model review,
  not human review. Dependencies: this PR merged. Target files:
  `specs/083-capability-regression-evals/evidence/review/`. Verification:
  procedure_001. Planned evidence: `evidence/review/codex-t002-20261123.json` and its
  raw output; obtained: both (2026-11-24, raw sha256 `c0991467…`). Eight findings, all
  confirmed and applied (S83-001 to S83-008); the owner chose the rules for S83-001
  (informative tasks and a binomial floor), S83-002 (any differing sensitivity
  verdict is `inconclusive`) and S83-005 (mandatory regression summary with owner
  acknowledgement).

## Phase P1 — contract and fixtures

- [ ] T003 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007): Write the protocol contract: registration and report record formats,
  mandatory fields, estimand, uncertainty method with the binomial floor and
  informative-task rule, the sealed sensitivity methods, the use ledger, the
  regression summary, decision table and claim text.
  Dependencies: T001 (OD-1 to OD-4), T002 confirmed findings applied. Target files:
  `specs/083-capability-regression-evals/contracts/regression-protocol.md`.
  Verification: procedure_002, procedure_003 and procedure_006 applied as a contract
  review. Planned evidence: `evidence/t003-contract.json`;
  obtained: none.
- [ ] T004 (REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007 REQ-008 / SC-008 REQ-009 / SC-009 REQ-010 / SC-010): Author hand-computed fixtures: one per verdict region,
  pass@k and pass^k values, a trial-level-versus-clustered control, missing-outcome
  bounds, infrastructure errors below and above threshold, a task with no valid
  trial in one arm, the minimum-sample edge (19 informative tasks; 4 trials; baseline
  all 0/5), an all-pass tie, a differing sensitivity verdict, hard and soft
  regressions with confirmation trials that confirm and that clear the flag, an
  acknowledgement with a stale hash, and a sixth ledger use. Dependencies: T003. Target files:
  `specs/083-capability-regression-evals/fixtures/`. Verification: procedure_005 to
  procedure_010 (expected values only).
  Planned evidence: `evidence/t004-fixtures.json` with fixture hashes; obtained: none.

## Phase P2 — implementation (offline)

- [ ] T005 (REQ-003 / SC-003 REQ-004 / SC-004 REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007 REQ-008 / SC-008 REQ-009 / SC-009 REQ-010 / SC-010 REQ-011 / SC-011): Implement the offline module: seal validation, pairing,
  estimators, missing-outcome bounds, infrastructure handling, decision and stop
  handling. No clock, host, model or network access. Dependencies: T004. Target
  files: `agent_braid/harness_regression.py`. Verification: procedure_003 to
  procedure_011. Planned
  evidence: `evidence/t005.json`; obtained: none.
- [ ] T006 (REQ-003 / SC-003 REQ-004 / SC-004 REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007 REQ-008 / SC-008 REQ-009 / SC-009 REQ-010 / SC-010 REQ-011 / SC-011 REQ-012 / SC-012): Tests over every T004 fixture with one mutation control per
  guard (seal, pairing, clustering, margin, missing outcomes, threshold, minimum
  sample, interim refusal, claim text). Dependencies: T005. Target files:
  `tests/test_harness_regression.py`. Verification: procedure_003 to procedure_012,
  then `quick`.
  Planned evidence: `evidence/t006.json`; obtained: none.
- [ ] T007 (REQ-002 / SC-002 REQ-012 / SC-012): Read-only CLI view: `evaluation-summary`
  recognizes the regression report and shows class, verdict and bounded claim text;
  update `docs/tooling/HARNESSING.md`. Coordinate the command list with SPEC-080.
  Dependencies: T006. Target files: `agent_braid/harness_cli.py`,
  `docs/tooling/HARNESSING.md`. Verification: procedure_002 and procedure_012.
  Planned evidence: `evidence/t007.json`; obtained: none.
- [ ] T008 (REQ-002 / SC-002): Add one dated cross-reference line to the SPEC-049
  protocol pointing to this spec, only after a founder decision; no frozen value
  changes. Dependencies: T001, founder decision record. Target files:
  `specs/049-harness-evaluation-learning/evaluation-protocol.md`. Verification:
  procedure_002. Planned evidence: `evidence/t008-crossref.json` with before and
  after hashes of the frozen sections (unchanged) and the expected whole-file hash
  after the added line; obtained: none.

## Phase P3 — first registration and verdict

- [ ] T009 (REQ-003 / SC-003 REQ-004 / SC-004 REQ-010 / SC-010): Owner seals the first
  regression record on the SPEC-082 corpus: δ, α, T, k, cluster level, thresholds,
  power assumption, sensitivity seed and pinned profile; the use ledger shows fewer
  than 5 uses. No trial runs. Dependencies: T006, SPEC-082
  corpus frozen, OD-1 to OD-5 decided. Target files:
  `specs/083-capability-regression-evals/evidence/registration/`. Verification:
  procedure_003 and procedure_010. Planned evidence:
  `evidence/t009-registration.json` with its SHA-256; obtained: none.
- [ ] T010 (REQ-006 / SC-006 REQ-008 / SC-008 REQ-009 / SC-009 REQ-011 / SC-011 REQ-012 / SC-012): Compute and record the first regression verdict once all
  registered trials have ended or a stop fired. Trials come from SPEC-084 or the
  existing laboratory under their own admission. Any verdict, `inconclusive`
  included, closes this task. Dependencies: T009, trial records from SPEC-084.
  Target files: `specs/083-capability-regression-evals/evidence/verdicts/`.
  Verification: procedure_006, procedure_008, procedure_009, procedure_011.
  Planned evidence: `evidence/t010-verdict.json`; obtained: none.
