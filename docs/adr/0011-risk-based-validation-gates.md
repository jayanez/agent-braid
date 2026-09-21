# ADR 0011: Risk-based validation gates

- **Status:** accepted
- **Date:** 2026-09-19
- **Deciders:** Juan Antonio Yáñez García
- **Constitutional articles:** 9, 10, 13, 14, 19, 21, 23

## Context

Agent Braid accumulated correct but differently scoped checks: fast structural
invariants, domain tests, complete compatibility suites, multi-agent scaffolding
regeneration and clean-room evidence reproduction. Running all of them after each
working-tree edit delays feedback and repeatedly invalidates evidence before a
candidate is stable. The distinction between executable checks and scientific or
human approval must remain intact.

## Decision

Adopt four validation moments:

1. targeted fast feedback during development;
2. a complete repository gate on a stable pull-request candidate;
3. additional specialist gates for sensitive inputs;
4. explicit clean-room reproduction only at evidence, milestone, release or
   publication boundaries.

A dependency-free classifier will map changed paths to domains and explain its
plan. Unknown paths fail closed to sensitive validation. The full suite remains
mandatory before integration. Path selection cannot approve evidence or replace
human interpretation.

## Alternatives considered

- Run every check after every edit: simple but needlessly slow and conflates
  development with evidence capture.
- Use path-selected tests as the only merge gate: rejected because undeclared
  transitive dependencies can escape the map.
- Add a third-party path-filter action: rejected to avoid a new supply-chain
  dependency for logic that is small enough to own and test.
- Infer semantic dependencies: rejected as out of scope and scientifically
  unsupported by the intended path classifier.

## Consequences

Local feedback becomes faster and expensive integration tests run only when their
inputs can change. CI has more jobs but a shorter parallel critical path. The path
map becomes maintained infrastructure and must conservatively classify itself.
Clean-room evidence is captured less often but against more stable candidates.
No existing validator, contract, scientific control or approval requirement is
removed.

## Validation

Unit tests will cover every domain, unknown-path fallback, deterministic plans,
failure propagation, specialist triggers and CI structure. Because the shared
Spec Kit guardrail changes, the real pinned Codex/Claude regeneration matrix must
pass once for this ADR's implementation. Durations are operational observations,
not acceptance claims.

## References

- [Constitution](../../CONSTITUTION.md)
- [Governance](../../GOVERNANCE.md)
- [Spec Kit workflow](../development/SPEC_KIT.md)
- [ADR 0006](0006-shared-spec-kit-guardrails.md)
- [ADR 0009](0009-transparent-validation-status.md)
- [Feature specification](../../specs/010-risk-validation/spec.md)
