# SPEC-031: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Plan and contract statements with no covering REQ (no `trust_remote_code`, no copied weights, no automatic network dependency, no hidden effect-authority inference, no network listener or extra process, no dynamic registry import, private text omitted by default) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, `assurance.json` unchanged. REQ-001, REQ-002, REQ-004, REQ-005 and REQ-006 are cited only where their text covers part of a statement. |
| Non-functional limits (5,000 ms deadline, 1,048,576 bytes, 1 to 64 candidates, depth 16) | Asked interactively; the owner chose to cite the proposed integration contract as data bound to REQ-005 and REQ-006, without a new REQ. Promotion thresholds for latency, memory and cost stay an open question (OQ-6). |

Derived without a question:

- Status line aligned with `assurance.json` (stage `draft`, human review pending) and `tasks.md` (T001–T007 and T009–T011 checked for bounded engineering lots, T008 open and absorbed by SPEC-066 as T303).
- Terminology, Risks and assumptions, Exit criteria and Open questions OQ-1 to OQ-7 written from spec.md, plan.md, research.md, data-model.md, contracts, tasks.md, validation-plan.md, the checklist and the 2026-11-01 owner decisions in SPEC-066.

Limits: the owner decides as owner, not as an independent reviewer.
