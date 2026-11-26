# SPEC-065: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run, no
qualification and no promotion.

| Point | Decision |
|---|---|
| Non-functional constraints (F3 caps, NC-6 freshness, NC-8 limits, NC-9 validity, NC-10 probe budget, Python 3.12+ stdlib) | Asked interactively; the owner chose to cite the existing REQ-002 to REQ-004, REQ-008 to REQ-010 and plan.md, with no new REQ and `assurance.json` unchanged (it is approved, review `a768e6d3`). |
| Status line | Asked interactively; the owner chose to align it with `assurance.json` (stage `validated`, `human_review` approved), the owner review of 2026-11-21 and `tasks.md`, without asserting that the machine is qualified today. |

Derived without a question:

- Security and privacy, Terminology, Risks and assumptions, Exit criteria and Open questions were written from
  spec.md, plan.md, tasks.md, validation-plan.md and the owner review limits A to E; the stale "nothing native has
  run" and "human review pending" sentences were updated.
- No re-qualification date is recorded in the sources, so none is stated.

Limits: the owner decides as owner, not as an independent reviewer.
