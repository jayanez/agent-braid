# SPEC-089: Tasks

Stable task IDs. Completion requires obtained evidence. This is a skeleton: only the
owner-decision task exists. Design, preregistration, Gate 0, run and report tasks are
added after T001, and only if T001 does not close the specification as out of scope
(OD-D). No task changes a tool, skill or scorer, reuses a spent set, or authorizes a run.

## Phase P0 — owner decisions

- [ ] T001 (REQ-001 / SC-001 REQ-008 / SC-008): Owner records the validity definition, the fresh split requirements, the run authorization, the out-of-scope alternative and the OpenCode route (OD-A to OD-E) in a dated record.
  Requires SPEC-079 T010 converged (#1513), as REQ-008 states; SPEC-088 is required only
  before a Codex run, not for this decision. Dependencies: none
  inside this specification. Target files: `specs/089-analyze-work-validity-codex-opencode/`.
  Verification: procedure_001, procedure_008. Planned evidence:
  `evidence/t001-owner-decisions.md`; obtained: none.
