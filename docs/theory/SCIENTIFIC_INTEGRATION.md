# Scientific integration

This is the current disposition of the [historical review](../../research/reviews/2026-09-14-foundations.md).
It is not a claim of production safety. Constitutional edits were approved by
the founder on 2026-09-16 under
[ADR 0004](../adr/0004-scientific-constitutional-clarifications.md).

| Finding | Correction | Evidence and remaining obligation |
|---|---|---|
| F1: commutation versus concurrency | Require an execution refinement contract | Lost-update control; real adapter refinement remains open |
| F2: observation is not compositional | Separate terminal projection, contextual equivalence and trace safety | Hidden-state control; no contextual equivalence checker implemented |
| F3: composition and failure | Typed configuration semantics and explicit outcomes | Bounded interpreter; external partial failure remains excluded |
| F4: initial pair tests | Quantify independence over reachable contexts | Three-operation control; general reachable-state proof remains open |
| F5: conflated correctness notions | Separate joinability, serializability, invariants and task correctness | Write-skew control; no production invariant checker |
| F6: assurance ladder | Property, method, scope and consumer verification are independent | Draft 0.2 contracts; labels are not authorization |
| F7: certificates | Structural checks plus independent semantic replay | Negative contract corpus; symbolic proofs remain unverified |
| F8: hypotheses and gates | Bounded research questions and engineering-independent delivery | Revised H1–H5; no performance or novelty claim |

Read [operational semantics](OPERATIONAL_SEMANTICS.md),
[contract migration](../architecture/DRAFT_0_2.md), and
[laboratory instructions](../../research/lab/README.md) for the executable scope.
The [reference index](../../research/REFERENCES.md) separates established theory,
preprints and abstract-only access. Contemporary comparisons include CoAgent,
STORM and CodeCRDT; their reported measurements have not been reproduced here.

The prospective contribution is portable, evidence-carrying interaction semantics
and independently checked decisions. Effects, commutativity, OT, CRDTs and
partial-order reduction are prior art, not discoveries of this project.

## Remaining boundaries

No LLM judgment supplies proof, permission or complete effect coverage. A
certificate may establish agreement in one finite model without establishing
contextual equivalence, successful task completion, security or safe concurrency.
No real tool execution, remote writes, residual synthesis or proof assistant is
included. Negative braid results do not block a sound practical analyzer.
