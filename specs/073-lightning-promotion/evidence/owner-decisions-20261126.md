# SPEC-073: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (publication of a release, tags or plugin-dist pushes; changes to analyze, analyze-work, prepare, execute, recover, grants, telemetry, System One; out-of-scope SPECs) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, and `assurance.json` (under the approved review) is unchanged. REQ-002 is cited only where its text covers part of an exclusion. |

Derived without a question:

- Status line aligned with `assurance.json` (human review approved, 2026-11-24) and
  `tasks.md` (T001-T009 done, T010 and T011 open); the approval covers the spec at
  `de602178`, not this refinement.
- `validation-plan.md` status no longer says no procedure has obtained evidence; the
  stale "(planned)" on the SC-001 test target is dropped.
- `checklists/requirements.md` marks OD-1 to OD-3 resolved; `plan.md` points to
  OD-1 to OD-5 in the spec.
- Non-functional requirements, Security and privacy, Terminology, Risks and
  assumptions (from `plan.md` and `assurance.json`), Exit criteria (from Success
  criteria and T011) and Open question OQ-1 (T010).

Limits: the owner decides as owner, not as an independent reviewer.
