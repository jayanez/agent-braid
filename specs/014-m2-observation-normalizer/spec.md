# Feature specification: explicit tracked-tree observation

## Purpose and scope

Make the existing `tracked-tree-v1` schedule observation explicit inside the
bounded Git replay implementation. This is an internal, behavior-preserving M2
increment. It does not introduce a new equivalence relation, public API, schema,
execution capability or scientific claim.

## Requirements and scenarios

- **REQ-001 — explicit observation.** Normalize a complete schedule to its
  tracked Git tree ID; an incomplete schedule has no successful observation.
  - **SC-001:** Complete schedules with one tree remain equivalent-observed.
  - **SC-002:** Complete schedules with distinct trees remain divergent.
  - **SC-003:** Any incomplete schedule keeps the result inconclusive.
- **REQ-002 — compatibility.** Evidence production, verification, digests and
  advisory planning retain their current `0.1.0-alpha` contracts and outcomes.
  - **SC-004:** Existing replay and verification fixtures retain their reports.

## Evidence boundary

The observation concerns tracked paths, modes and blob IDs for fixed patches.
Passing checks do not prove source-code correctness, hidden effect independence,
general confluence or execution safety. Human review and clean-room reproduction
remain separate from structural validation.
