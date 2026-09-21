# Bounded operational semantics

**Model:** `integer-batch-v1`. **Status:** experimental specification.

## Configuration and composition

A configuration is `(state, versions, pending, results, events)`. State maps
resource names to integers; versions are nonnegative integers. Results are keyed
by operation-instance ID. An operation definition, a proposed instance and an
execution attempt are distinct identities. The lab permits one attempt per
instance, without retries or new operation generation.

An operation induces a typed transition `C --a--> C'`. Sequence `a;b` means
execute a first, then b on its output configuration, retaining results and events.
Thus the older expression `a(b(s))` is only shorthand in the pure state fragment;
it must not discard values or traces from an effectful operation.

The lab has a closed expression grammar: integer literal, resource read, binary
addition or multiplication. Boolean values are not integers in this model.
Operations are `read`, `assign`, `add`, or `multiply`; the latter two read the
old target before writing. Optional guards compare two expressions using `eq`
or `le`. Missing resources are errors; no implicit zero or creation is allowed.
All expressions use the pre-operation state. A successful operation returns the
read or newly written integer, emits one identified event and increments the
written resource's version. There are no hidden external effects in this model.

Each abstract operation is atomic. This is a model premise, not a capability of
real agents. An unmet dependency, false guard or stale read version produces a
`blocked` terminal outcome. Missing resources or invalid arithmetic input produce
`error`. Execution stops and retains the pending suffix; a failed step makes no
state change. A cyclic dependency graph or malformed input is rejected before
exploration. No rollback or compensation is implied.

## Batches and observations

A batch contains 1–6 uniquely identified operations and an acyclic dependency
graph. Enumerate every complete topological order from the same initial state.
The finite domain is precisely those orders for that fixture, not all possible
initial states or all interleavings inside a real operation. Rejected sizes are
errors, not silently truncated searches.

`exact` observation includes state, versions, per-instance results, outcome and
events in chronological order. `projection` observes only the selected resource
values and outcome; it intentionally excludes results, versions and events.
Projections are terminal contracts only and cannot authorize future rewrites.
Failed or blocked executions make an equivalence verdict `inconclusive`.
Otherwise matching observations yield `equivalent-observed`; a mismatch yields
`divergent`. These are model observations, not global confluence proofs.

## Contextual equivalence and safety

For reusable exchanges, equivalent configurations must preserve enabledness and
remain equivalent under every admitted continuation. Equality of a terminal
projection alone is insufficient. Trace safety additionally checks what happened
before termination; final equality does not erase an external disclosure or
duplicate send. Serializability allows different valid serial outcomes;
confluence concerns joining divergences; neither proves the task specification.

## Restricted theorem targets

**T1 — independence (unmechanized proof sketch).** Assume deterministic atomic
operations initially enabled at the common source, complete read/write sets including enabledness and control/predicate
reads, no external effects, and writes confined to declared resources. If neither
write set intersects the other's read or write set, both remain enabled and see
unchanged inputs. Disjoint writes then produce equal final states and the same
per-instance results. Event equivalence needs its own contract; chronological
event lists need not be equal. Instrumentation of one run does not prove complete
effects over every possible state.

**T2 — schedule equivalence (unmechanized proof sketch).** For a fixed finite
partial order, suppose every swapped incomparable pair satisfies T1 in each
reachable context, swaps preserve admissibility, and equivalence is preserved by
the remaining suffix. Any two linear extensions are connected by adjacent swaps
of incomparable elements. Each swap preserves the complete observation; induction
over swaps proves schedule equivalence. Initial-state pair tests do not establish
these premises.

Newman's lemma requires termination as well as local confluence. A decreasing
pending count supports termination only for this fixed, retry-free model. An
arbitrary observation quotient requires additional compatibility conditions.
See the [references](../../research/REFERENCES.md) for rewriting theory,
commutativity-based control, and mechanized CRDT convergence.

## Exchange research

Use typed composable paths `a:s→s1`, `b:s1→s2` and alternatives `b':s→t1`,
`a':t1→s2`, or explicitly equivalent endpoints. Require closure, intent/result
preservation, stable premises and coherence, not arbitrary replacement states.
With right-to-left function composition, adjacent exchange `B = P ∘ R`, where P
is the flip, distinguishes braid from quantum-form notation. Invertible exchanges
give braid-group actions; without inverses only the positive monoid is implied.
An involutive action factors through the symmetric group. Exchange invertibility
does not mean real actions are reversible.

The known conjugation example `B(a,b)=(b,b⁻¹ab)` on S3 is a finite positive
control, not a model of tools. OT consistency identities require an explicit
mapping before being identified with braid identities. Nondeterministic policy
equivalence, distributional metrics, POR/DPOR and residual synthesis are deferred.
