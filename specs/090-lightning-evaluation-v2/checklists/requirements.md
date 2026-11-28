# Requirements quality checklist: SPEC-090

Generated for `speckit-checklist`. Unchecked items are pending review; this list is not validation,
scientific proof or approval.

## Requirement clarity

- [ ] CHK-001: The gate A estimand (majority pass per prompt, 3 repetitions) and the all-fail functional θ = E[(1−p)³] are defined once and used consistently. (spec.md REQ-001, REQ-003; plan.md Design 1)
- [ ] CHK-002: Every numeric parameter (α, τ, δ, Δ, ε, power, slice, pool, audit, reserve, tripwire threshold and margin, pilot size and arms, anchor size, clustering tolerance, family-wise α, drift threshold, split size) is an open OD. Fixed values that are not ODs: the 2-of-3 majority, 3 repetitions per gate and confirmation prompt, the 0.80 bound threshold (inherited from SPEC-078 OD-1 and the approved strategy), the class rule's one half, the 8-word leakage window and the 5-prompt example of REQ-031. (spec.md Owner decisions)
- [ ] CHK-003: The 0.80 bound threshold is inherited from SPEC-078 OD-1 and labelled as such. (REQ-002)

## Normative references

- [ ] CHK-004: Articles, ADR 0021, 0039, 0040, 0042 and 0046 are cited and listed in `assurance.json`. (spec.md Authorities)
- [ ] CHK-005: The text states that ADR 0039 needs no amendment and ADR 0042 stays deferred. (ADR 0046 decision 11)

## Acceptance coverage and negative controls

- [ ] CHK-006: Every REQ has at least one SC with Given/When/Then and a planned test. (assurance.json)
- [ ] CHK-007: Negative controls cover the reserve cap, the class rule, the incumbent margin, host drift, the tripwire, the simulation precondition and `parallel`. (validation-plan.md)

## Empirical protocol

- [ ] CHK-008: Simulations (known p, correlation range, error rates, coverage, replay) precede any real run. (REQ-017, evaluation-protocol.md)
- [ ] CHK-009: Leakage control against SPEC-069, v2, v3 and v4 for the gate A split, the reserve and the twin (REQ-024), and against the frozen audit set (REQ-012, REQ-024, REQ-027).
- [ ] CHK-010: Hypotheses H1 to H3 are about procedures, preregistered, and none is a completion condition. (spec.md Scientific boundaries)
- [ ] CHK-011: Cost and stopping rules are stated; EUR 0; no LLM judge. (REQ-022, evaluation-protocol.md)

## Compatibility and boundaries

- [ ] CHK-012: No frozen SPEC-069, SPEC-078 or SPEC-079 path is in scope, and the new gate is not applied to v4. (REQ-020)
- [ ] CHK-013: Adaptive allocation is excluded from held-out and audit data. (REQ-021)
