# SPEC-028: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Plan and contract statements with no covering REQ (no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, no hidden effect-authority inference, no default external inference endpoint, no caller-controlled code, import, file or URL selection, private text omitted by default) | Asked interactively; the owner chose non-normative scope statements: no MUST, no new REQ, `assurance.json` unchanged. REQ-002, REQ-004 and REQ-005 are cited only where their text covers part of a statement. |
| Non-functional limits (1 MiB, 1 to 32 questions, 2 to 32 options, 64-byte IDs, depth 16, 5 s deadline, queue bound 8, 1e-6 tolerance) | Asked interactively; the owner chose to cite the draft contract (`contracts/decision-api.md`, `contracts/stdlib-v1.md`) as data bound to REQ-002, REQ-003 and REQ-006, without a new REQ. Promotion thresholds for latency, memory and cost stay an open question (OQ-4). |

Derived without a question:

- Status line aligned with `assurance.json` (stage `validated`, human review pending, one obtained synthetic check per scenario) and `tasks.md` (T001–T008 checked per `technical-delivery.json`, T009–T011 per the 2026-10-20 reconciliation, bounded engineering lots). The Evidence paragraph's claim that every `obtained_evidence` array is empty was corrected to match.
- Terminology, Risks and assumptions, Exit criteria and Open questions OQ-1 to OQ-8 written from spec.md, plan.md, research.md, data-model.md, contracts, analysis.md, tasks.md, validation-plan.md and the checklist.

Limits: the owner decides as owner, not as an independent reviewer.
