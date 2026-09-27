# ADR 0017: Bounded structured exchange laboratory

- **Status:** Proposed; founder review pending
- **Date:** 2026-09-27
- **Decider:** Juan Antonio Yáñez García, founder
- **Constitutional articles:** 0, 2–4, 6–10, 13–14, 17–20, 23–25

## Context

M2 fixed-patch Git replay and path-disjoint reduction do not establish an
exchange rule for overlapping structured edits. M3 needs a falsifiable finite
operator whose transformed operations and observation are explicit.

## Proposed decision

Introduce an isolated `anchored-sequence-v1` laboratory. A base sequence has
unique element IDs. An insert names either `$root` or an immutable base element
as its anchor, a fresh element ID and a string value. Concurrent siblings at
one anchor are ordered by fresh ID. The physical insertion index is a residual
computed in the current execution context; it is not an input coordinate.
No deletion, nested anchor, external effect or live Git edit is in this class.

An adjacent exchange replays the two logical inserts in the opposite order and
regenerates their residual positions. The pair observation is the final ordered
ID/value sequence. The positive braid control compares the paths `s0 s1 s0`
and `s1 s0 s1` for three inserts, with left-to-right application of crossings.
This is an adjacent crossing convention, not a quantum-form Yang–Baxter claim.
Raw chronological steps remain in evidence; they are not equated by the final
sequence observation. No contextual equivalence or arbitrary concurrency claim
follows.

The advisor may propose a same-anchor swap, keep order for the other supported
case, or reject unsupported input for manual review. It is rule based, and all
advice is consultative. A deterministic verifier regenerates every path from
the request, checks the entire evidence record and reports `verified-bounded`,
`divergent` or `inconclusive`. Producer and verifier share the replay code;
they are two passes, not independent implementations. Every record states
`executionAuthorization: false`.

The strongest surviving finite class may receive a mathematical specification
and a separate proof review. Exhaustive finite tests do not themselves prove a
universal theorem. SPEC-019 reserves a later, separate M3.5 learned predictor;
it cannot certify exchange or change this verifier.

## Alternatives

- Raw-index inserts: reject because stale coordinates can diverge after overlap.
- General OT or arbitrary Git patch transformation: defer until a transformation
  algebra and its side conditions are specified and tested.
- Laya/Jev or an external learned advisor: defer; neither is required for M3.

## Consequences

The model is useful only for the named pure sequence domain. It does not
upgrade M2 certificates, authorize execution, or close M3. Public review of the
new experimental contract and this ADR is required before integration.

## References

- [Constitution](../../CONSTITUTION.md)
- [Operational semantics](../theory/OPERATIONAL_SEMANTICS.md)
- [SPEC-018](../../specs/018-structured-exchange/spec.md)
