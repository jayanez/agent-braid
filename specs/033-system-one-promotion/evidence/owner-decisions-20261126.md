# SPEC-033: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (online learning, external telemetry export, paid model calls, milestone closure) and plan-only security statements (`trust_remote_code`, automatic network dependency, copied weights, hidden authority inference) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, `assurance.json` unchanged. REQ-001, REQ-004 and REQ-005 are cited only where their text covers part of a statement. |
| Non-functional thresholds (latency, memory, cost) | None defined in the sources; the owner chose to record an open question (OQ-6) rather than invent numbers. |

Derived without a question:

- Status line aligned with `assurance.json` (stage `draft`, human review pending) and `tasks.md` (T001–T008 open, T009 done).
- Terminology, Risks and assumptions, Exit criteria and Open questions OQ-1 to OQ-7 written from spec.md, plan.md, research.md, data-model.md, tasks.md, validation-plan.md, the checklist and the 2026-11-01 founder decision (SPEC-066 absorbs T002, T003, T004, T006, T008).

Limits: the owner decides as owner, not as an independent reviewer.
