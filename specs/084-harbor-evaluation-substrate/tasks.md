# SPEC-084: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`python3 scripts/validate_change.py --base develop --profile quick`. No task here
installs Harbor, a runtime or an image, or runs a job, before its owner go is
recorded. `executionAuthorization` stays false throughout.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any); decide or defer OD-1..OD-6, and accept, amend or reject ADR 0045.
  Dependencies: none. Target files: none (review record only).
  Verification: procedure_001.
  Planned evidence: `evidence/t001-owner-review.md`; obtained: none.
- [ ] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage
  each finding (confirmed, fixed, rejected with reason). Independent model review,
  not human review. Dependencies: this PR merged. Target files: none.
  Verification: procedure_002.
  Planned evidence: `evidence/review/t002-codex.json`; obtained: none.

## Phase P1 — feasibility gates

- [ ] T003 (REQ-003 / SC-003): Runtime and pinning gate: check Docker or Podman per OD-2, pin Harbor, adapter
  versions and image digests; refuse floating tags. Dependencies: T001 (OD-2), owner
  go for the isolated install. Target files: `scripts/har_harbor_gates.py`.
  Verification: procedure_003.
  Planned evidence: `evidence/t003-runtime-pinning.json`; obtained: none.
- [ ] T004 (REQ-002 / SC-002): Credential gate: authenticate inside one trial container by the OD-3 method; scan
  image layers, exported config, logs and trajectories for credential material.
  Dependencies: T003, T001 (OD-3). Target files: `scripts/har_harbor_gates.py`.
  Verification: procedure_004.
  Planned evidence: `evidence/t004-credential.json`; obtained: none.
- [ ] T005 (REQ-004 / SC-004): Cost gate: EUR 0 route check and quota stops before and after a batch, reusing the
  D2 stop conditions. Dependencies: T003. Target files: `scripts/har_harbor_gates.py`
  (reads `agent_braid/harness_quota.py`). Verification: procedure_005.
  Planned evidence: `evidence/t005-cost.json`; obtained: none.
- [ ] T006 (REQ-006 / SC-006): Network policy gate: install public, run allowlist to the provider API host only,
  verifier no-network; check enforcement inside the runtime VM on macOS.
  Dependencies: T003. Target files: `scripts/har_harbor_gates.py`.
  Verification: procedure_006.
  Planned evidence: `evidence/t006-network.json`; obtained: none.
- [ ] T007 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004 REQ-006 / SC-006): Record the gate outcome: feasible, or infeasible with the failing gate (OD-6).
  A failed gate stops P2 to P5. Dependencies: T003 T004 T005 T006.
  Target files: none. Verification: procedure_007.
  Planned evidence: `evidence/t007-feasibility.json`; obtained: none.

## Phase P2 — adapter

- [ ] T008 (REQ-005 / SC-005 REQ-011 / SC-011): Job config builder: one container per trial, `-k`, resources, model, effort,
  fresh run id, SPEC-082 task ids, candidate hash check inside the container, export.
  Dependencies: T007 feasible. Target files: `agent_braid/harness_harbor.py`,
  `tests/test_harness_harbor.py`. Verification: procedure_008, then `quick`.
  Planned evidence: `evidence/t008-adapter.json`; obtained: none.
- [ ] T009 (REQ-007 / SC-007 REQ-008 / SC-008): ATIF ingestion: hash trajectories, map outcome classes (pass, fail, infra error,
  missing), keep the Harbor mean as a labelled descriptive field only.
  Dependencies: T007 feasible. Target files: `agent_braid/harness_atif.py`,
  `tests/test_harness_atif.py`. Verification: procedure_009, then `quick`.
  Planned evidence: `evidence/t009-atif.json`; obtained: none.

## Phase P3 — first job

- [ ] T010 (REQ-005 / SC-005): Run one small job on the first OD-5 host after an owner go; rerun it from its
  exported config. Dependencies: T008 T009, SPEC-082 corpus available.
  Target files: `scripts/har_harbor_job.py`. Verification: procedure_010.
  Planned evidence: `evidence/t010-job.json`, `evidence/t010-rerun.json`; obtained: none.
- [ ] T011 (REQ-010 / SC-010): Negative controls: blocked network, missing credential, stale image, one trial
  each; each must end as an infra error with its reason code. Dependencies: T010.
  Target files: `scripts/har_harbor_job.py`. Verification: procedure_011.
  Planned evidence: `evidence/t011-controls.json`; obtained: none.

## Phase P4 — macOS shadow

- [ ] T012 (REQ-009 / SC-009): Register the shadow subset and agreement rule (OD-4) by hash before any shadow
  data. Dependencies: T001 (OD-4), T010. Target files: none (registration record).
  Verification: procedure_012.
  Planned evidence: `evidence/t012-shadow-registration.json`; obtained: none.
- [ ] T013 (REQ-009 / SC-009): Run the shadow subset on the real host under SPEC-065 containment after an owner go;
  apply the rule; record agreement, or disagreement with a promotion block.
  Dependencies: T012, SPEC-065 qualification valid for the current OS and CLI.
  Target files: none (existing SPEC-065 launch path). Verification: procedure_013.
  Planned evidence: `evidence/t013-shadow.json`; obtained: none.

## Phase P5 — report

- [ ] T014 (REQ-008 / SC-008 REQ-011 / SC-011): Feasibility and agreement report: gate results, job and rerun, controls,
  shadow outcome, limits; verdicts only via SPEC-083. Update
  `docs/tooling/HARNESSING.md` only if feasible. Dependencies: T011 T013.
  Target files: `docs/tooling/HARNESSING.md`. Verification: procedure_014.
  Planned evidence: `evidence/t014-report.json`; obtained: none.
