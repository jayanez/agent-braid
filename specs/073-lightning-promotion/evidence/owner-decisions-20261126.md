# SPEC-073: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`; every point below follows the precedent of the
sibling refinements (SPEC-043). This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (publication of a release, tags or plugin-dist pushes; changes to analyze, analyze-work, prepare, execute, recover, grants, telemetry, System One; out-of-scope SPECs) | Scope statements in the spec; REQ-002 and REQ-008 are cited only where their text covers part. No new REQ; `assurance.json` (under the approved review) is unchanged. |

Derived without a question:

- Status line aligned with `assurance.json` (human review approved, 2026-11-24) and
  `tasks.md` (T001-T009 done, T010 and T011 open).
- `validation-plan.md` status no longer says no procedure has obtained evidence.
- Non-functional requirements, Security and privacy, Terminology, Risks and
  assumptions (from `plan.md` and `assurance.json`), Exit criteria (from Success
  criteria and T011) and Open questions OQ-1 and OQ-2 (T010; empty
  `obtained_evidence`).

Limits: the owner decides as owner, not as an independent reviewer.
