# ADR 0002: Yang–Baxter is a hypothesis, not an assumed property

- **Status:** accepted
- **Date:** 2026-09-13
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 0, 8, 10, 17, 18, 22

## Context

Braid relations and Yang–Baxter theory offer a powerful language for coherent exchanges. Concurrent agent systems also require reasoning about reorderings. The resemblance is meaningful enough to investigate but does not establish that an R-matrix or YB equation solves agent coordination or code merging.

## Decision

The project may use YB-inspired terminology at the inspiration and formalism levels, with explicit definitions. It may make an unqualified Yang–Baxter claim only for a well-typed structure with a stated equation, domain, equivalence notion, and proof.

The practical effect/confluence tooling must remain useful if no nontrivial Yang–Baxter class is found.

## Alternatives considered

- **Brand all order-independence as Yang–Baxter:** rejected as mathematically misleading.
- **Remove Yang–Baxter from the project:** rejected because testing the structural hypothesis is a defining research opportunity.
- **Restrict the repository to pure mathematics:** rejected because real agent traces provide the intended laboratory and engineering feedback loop.

## Consequences

Public communication requires claim labels and may be less sensational. The project gains falsifiability, clearer collaboration with researchers, and resilience to negative results.

## Validation

Repository validation enforces the constitutional article count and foundational wording. Research reviews must reject unlabeled transitions from analogy to theorem.
