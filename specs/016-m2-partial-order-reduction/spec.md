# Feature specification: bounded Git partial-order reduction

## Purpose and scope

Measure whether a conservative syntactic independence relation can reduce the
number of isolated Git patch replays in the existing 2–4 operation domain. This
is a private M2 experiment. The current exhaustive producer and verifier remain
the oracle and continue to supply every public replay schedule. No reduced
result authorizes preparation waves, execution, integration or ref promotion.

## Authorities

Apply Constitutional clause zero and Articles 2, 4, 6, 9, 13, 14, 19, 20 and
23; ADR 0013, the fixed-patch operational contract in
`docs/architecture/GIT_REPLAY.md`, and the claim discipline in
`docs/theory/CLAIM_DISCIPLINE.md`. SPEC-012's exhaustive replay and versioned
evidence remain authoritative for this experiment.

## Requirements and acceptance scenarios

- **REQ-001 — conservative independence.** Two operations may be swapped only
  when neither depends transitively on the other, both have supported and
  certain fixed patches, and no changed path is equal to or an ancestor of a
  changed path of the other operation. An uncertain or unsupported operation is
  dependent on every other operation. This relation is syntactic and scoped to
  the named base and immutable patches.
  - **SC-001:** Eligible disjoint-path operations are independent, including
    siblings after a common prerequisite.
  - **SC-002:** Shared paths, file/directory prefixes, declared dependency
    chains, uncertain paths and unsupported changes prevent a swap.
- **REQ-002 — deterministic representative orders.** Enumerate the existing
  admissible topological orders. Connect orders only by one adjacent swap of
  independent operations, partition the finite set into connected classes and
  select the lexicographically first order in each class. Replay only those
  representatives in the private experiment; retain the full order-to-class
  mapping and count. Enumeration may still visit all 24 orders, so no order-
  generation speedup is claimed.
  - **SC-003:** Permuting the input operation list gives the same classes and
    representatives; every admissible order belongs to exactly one class.
  - **SC-004:** Three disjoint operations require one representative replay
    instead of six, while a fully dependent case replays every admissible
    order.
- **REQ-003 — exhaustive oracle comparison.** Produce the existing full replay
  evidence and have the existing verifier regenerate and check it. The
  verifier reruns the replay through the same replay implementation; it is a
  separate verification pass, not an independently implemented engine.
  Compare each representative's fresh isolated replay with its baseline
  schedule, then compare the complete/incomplete
  status and terminal `tracked-tree-v1` observation of every oracle order in
  each class. A mismatch, unverified oracle or unavailable input is
  inconclusive for the reduction. Preserve raw exhaustive traces and the
  oracle's divergent or inconclusive classification.
  - **SC-005:** A complete equivalent fixture agrees class by class and
    reports the reduced replay count without changing its public bundle or
    advisory plan.
  - **SC-006:** Divergent, incomplete or tampered evidence cannot be reported
    as a new positive confluence or preparation result; a class-level mismatch
    is an explicit reduction counterexample.
- **REQ-004 — real-Git counterexample follow-up.** Exercise SPEC-015's private
  reducer with a verified divergent Git fixture containing a redundant third
  operation. Do not use a controlled backend result as a substitute for the
  real fixture.
  - **SC-007:** The real fixture reduces to a two-operation divergent witness
    verified by the existing verifier.

## Scientific boundaries and compatibility

The observation is the final tracked Git tree ID for complete fixed-patch
replays; failures remain incomplete and raw per-step traces are retained in the
exhaustive oracle. Syntactic path separation is a candidate relation, not a
proof of semantic commutation, arbitrary interleaving safety, contextual
equivalence or general confluence. The private experiment does not change the
`0.1.0-alpha` replay evidence, plan or CLI contracts. Each replay keeps its
existing resource bounds; the comparison does not claim a shared aggregate
budget or a wall-time speedup.

## Evidence and unresolved questions

Focused tests will bind every scenario to representative selection, real Git
replay, negative controls and unchanged public output. The hypothesis is that
some supported fixtures permit fewer replayed orders while matching the
exhaustive oracle. A negative or inconclusive result in a new workload is valid
protocol evidence and leaves M2 open. Human review and independent external
validation are separate decisions.
