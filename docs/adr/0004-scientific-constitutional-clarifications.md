# ADR 0004: Scientific constitutional clarifications

- **Status:** accepted by the founder on 2026-09-16
- **Date:** 2026-09-15
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 6, 8, 13; clause zero unchanged

## Context

### Adoption record — 2026-09-16

The founder explicitly approved integrating the prepared branch into main and
pushing it directly. This authorizes adoption of this amendment as a one-time
exception to the dedicated-PR procedure described below. No PR review is claimed.
The original proposal and its intended review route are retained as history;
the general governance requirements remain unchanged for future amendments.

The scientific review of foundation commit
`77ca4b599dc26edb6a37bb91850b9e96a9866f91` identified an unsafe inference from
sequential commutation to concurrent implementation, underspecified exchange
notation, and an assurance ladder mixing properties with evidence methods.

## Decision

Propose an execution-contract premise in Article 6, explicit exchange notation
in Article 8, and independent evidence dimensions in Article 13. Preserve all
25 article numbers, clause zero, ownership, licensing and governance. Branch
edits are the proposed amendment text, not evidence of adoption. Submit this
commit separately through the existing dedicated-PR procedure before merging
dependent integration work. No PR or remote mutation is part of local delivery.

## Alternatives considered

Editorial footnotes alone leave normative ambiguity. Removing the 0–5 labels
breaks continuity without resolving evidence semantics. Treating every operation
as serial avoids some races but does not establish correctness or authorization.

## Consequences

Execution decisions need an explicit refinement/isolation contract. Compensation
has independent obligations. Existing labels remain recognizable but no longer
imply a scalar strength order. Documentation and future contracts must align.

## Validation

Preserve clause zero and exactly articles 1–25. Reproduce lost-update and
return-value counterexamples. Require founder review and a dedicated amendment
PR before adoption; neither a local commit nor passing tests completes that gate.

## References

- Herlihy and Wing, [Linearizability](https://www.cs.columbia.edu/~wing/publications/HerlihyWing90.pdf), 1990.
- Eisermann, [Yang–Baxter deformations and rack cohomology](https://arxiv.org/pdf/0808.0108), 2008.
