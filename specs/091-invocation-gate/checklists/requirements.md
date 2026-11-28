# Requirements quality checklist: SPEC-091

Generated for `speckit-checklist`. Unchecked items are pending review; this list is not validation,
scientific proof or approval.

## Requirement clarity

- [ ] CHK-001: The three labels and their tests are defined once (OD-B1, rubric) and recall and false-positive rates are defined by label. (spec.md REQ-001, REQ-002)
- [ ] CHK-002: Each lever is named with the surface it changes and its size cap. (REQ-005, REQ-010)
- [ ] CHK-003: Every numeric parameter and the hook wording are open ODs. Fixed values that are not ODs: 3 repetitions per item, the host caps (1,536 and 4,096 characters, 1,500 approximate tokens under ADR 0038 D12), the 2³ and 2×2 factorial shapes, and the values inherited from SPEC-090. (spec.md Owner decisions)

## Normative references

- [ ] CHK-004: ADR 0021, 0030, 0035, 0038, 0039 and 0046 are cited and listed in `assurance.json`. (spec.md Authorities)
- [ ] CHK-005: The ADR 0038 decision precedes any shipped `_meta` or server-instruction change. (REQ-024, OD-10)

## Acceptance coverage and negative controls

- [ ] CHK-006: Every REQ has at least one SC with Given/When/Then and a planned test. (assurance.json)
- [ ] CHK-007: Negative controls cover frozen labels, near-miss items, single-difference arms, the hook text and data handling, caps, the factorial precondition, the tripwire and the boundaries. (validation-plan.md)

## Empirical protocol

- [ ] CHK-008: Labels are human proxy labels assigned before measurement, with a stated adjudication and agreement report. (REQ-002, OD-2)
- [ ] CHK-009: Leakage control against SPEC-069, v2, v3 and v4; v4 reuse only per OD-1. (REQ-019)
- [ ] CHK-010: Simulations precede real runs; each real run has its own freeze and owner yes. (REQ-018, tasks.md)
- [ ] CHK-011: Hypotheses H1 to H3 are preregistered and none is a completion condition. (spec.md Scientific boundaries)
- [ ] CHK-012: Cost is stated and EUR 0; no LLM judge. (REQ-021, Non-functional requirements)

## Compatibility and boundaries

- [ ] CHK-013: Existing lab profiles and `skill` configurations are unchanged. (REQ-029, REQ-022)
- [ ] CHK-014: No lever ships by default without promotion and OD-11. (REQ-025)
