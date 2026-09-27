# Research decisions and limits

M2 fixed-patch tree equality cannot establish structured-edit exchange.
Same-anchor inserts overlap one logical gap; their physical indices depend on
schedule, giving a concrete residual. Canonical sibling order by ID gives a
testable order-independent terminal state. Chronological traces still differ.

The finite protocol exhausts anchor topology, not all payload strings or ID
alphabets. Producer and verifier share replay implementation. The candidate
set-union argument in docs/theory/STRUCTURED_EXCHANGE.md awaits proof review.
A broader OT or CRDT claim needs separate algebra and counterexamples.
