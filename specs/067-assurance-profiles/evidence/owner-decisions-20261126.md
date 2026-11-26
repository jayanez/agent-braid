# SPEC-067: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Non-functional constraints (determinism, byte-identical output, operator-owned receipt store, Python 3.12+ stdlib) | Asked interactively; the owner chose to cite the existing REQ-002, REQ-004, REQ-006, REQ-007, REQ-008, REQ-010 and plan.md, with no new REQ and `assurance.json` unchanged (it is approved, review `2b48a5d6`). |
| Numeric limits that exist only in code (field length, path count, rule count) | Asked interactively; the owner chose not to copy them: only figures stated in the spec are cited. |

Derived without a question:

- Status line aligned with `assurance.json` (stage `validated`, `human_review` approved), the owner review record (2026-11-22) and `tasks.md` (T001 to T011 checked, T012 and T013 open); the stale "Human review pending" in "Evidence and unresolved questions" updated the same way.
- Security and privacy, Terminology, Risks and assumptions, Exit criteria and Open questions written from spec.md, plan.md, tasks.md and the owner review limits A to E.

Limits: the owner decides as owner, not as an independent reviewer.
