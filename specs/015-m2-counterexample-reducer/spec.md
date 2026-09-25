# Feature specification: bounded Git counterexample reduction

## Purpose and scope

Provide a deterministic internal aid to shrink a verified divergent Git replay
case to the smallest operation subset, within the existing 2–4 operation domain
and a 120-second total deadline with at most ten candidate subsets. It consumes
the current verified replay contract and does not depend on the
observation-normalizer increment.

## Requirements and scenarios

- **REQ-001 — verified input.** Reject tampered, unverified, equivalent or
  unavailable replay evidence as a positive counterexample source.
  - **SC-001:** Verified divergent evidence is eligible for bounded reduction.
  - **SC-002:** Altered evidence and unavailable source Git objects fail closed.
- **REQ-002 — deterministic reduction.** Examine operation subsets in ascending
  size and stable identifier order, rerunning each candidate from the same base.
  A candidate must retain every declared prerequisite of each retained
  operation; discarded dependency-incomplete subsets are not replay attempts.
  Preserve the original divergent classification and bind the selected subset
  to its independently verified replay evidence.
  - **SC-003:** A redundant operation is removed when a smaller verified
    divergent subset exists.
  - **SC-004:** A case with no smaller divergent subset remains unchanged.
- **REQ-003 — bounded failure.** A supervisor enforces one 120-second deadline
  across input verification and all subset attempts, and stops after ten
  replayed candidate subsets. It terminates the whole private worker process group on
  timeout. Each replay retains its existing per-call Git limits; those limits
  are not represented as an aggregate command or scratch quota. Budget
  exhaustion, missing checks or replay failures produce an inconclusive
  reduction, never a minimized claim.
  - **SC-005:** An exhausted budget retains the original evidence and reports
    why no minimality claim is available.

## Evidence boundary

Minimality is only among enumerated operation subsets in the fixed-patch,
`tracked-tree-v1` domain. It does not minimize patch hunks, infer hidden effects,
prove program semantics or authorize any execution or ref promotion.
