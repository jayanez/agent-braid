# SPEC-029: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, no hidden effect-authority inference, no paid runs before an explicit budget, private SPEC-019 seals stay private) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, `assurance.json` unchanged. REQ-001 is cited only where its text covers part of a statement. |
| Non-functional figures (5% accepted error, 0.95 precision bound, 10% cost reduction, 200/100 item floors, 10,000 bootstrap resamples) | Asked interactively; the owner chose to cite them as draft targets from `evaluation-protocol.md`, frozen at pre-fit review, not as requirements, and to record an open question (OQ-4) for latency, memory and cost thresholds. |

Derived without a question:

- Status line aligned with `assurance.json` (stage `draft`, human review pending) and `tasks.md` (T001–T009 open, T010–T027 done as bounded lots).
- Terminology, Risks and assumptions, Exit criteria and Open questions OQ-1 to OQ-6 written from spec.md, plan.md, research.md, data-model.md, tasks.md, evaluation-protocol.md, the checklist and the 2026-11-01 note that SPEC-066 absorbs T001–T009 for the owned population.

Limits: the owner decides as owner, not as an independent reviewer.
