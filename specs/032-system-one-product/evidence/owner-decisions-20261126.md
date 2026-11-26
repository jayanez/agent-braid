# SPEC-032: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Plan and data-model statements with no covering REQ (no `trust_remote_code`, no automatic network dependency, no copied weights, no hidden effect-authority inference) and the deferrals in Purpose and scope (browser automation, vision, email parsing, multiple language SDKs, framework-specific adapters) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, `assurance.json` unchanged. REQ-006 is cited only where its text covers part of a statement. |
| Non-functional limits (schema bytes, depth, node visits, question count, deadlines, hook buffer size, queue admission) | Asked interactively; the owner chose to cite `contracts/product.md` and `product-decisions.md` as data bound to REQ-002, REQ-003 and REQ-006, without a new REQ. After review, the core admission limit (one active, eight waiting) was asked again and the owner chose a citation with no REQ binding, because REQ-005 does not cover it. Promotion thresholds for latency, memory and cost stay an open question (OQ-6). |

Derived without a question:

- Status line aligned with `assurance.json` (stage `draft`, human review pending) and `tasks.md` (T001, T003, T004, T007, T008 checked for selected-subset engineering evidence per the tasks.md section dated 2026-10-07; T002, T005, T006 open and deferred).
- Terminology, Risks and assumptions, Exit criteria and Open questions OQ-1 to OQ-7 written from spec.md, plan.md, research.md, data-model.md, contracts, tasks.md, product-decisions.md, validation-plan.md, the checklist and the 2026-11-01 owner decisions in SPEC-066.

Limits: the owner decides as owner, not as an independent reviewer.
