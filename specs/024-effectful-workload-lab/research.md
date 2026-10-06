# SPEC-024 research decisions

| Decision | Rationale/source | Rejected alternative and limit |
|---|---|---|
| Separate simulation contract | Operational semantics/ADR 0005 exclude retained external partial failure | Silent integer-batch extension invalidates historical scope |
| Captured-read/derived-write primitives | Article 12 and lab controls require lost-update/write-skew examples | Arbitrary internal interleaving excluded |
| Local configuration/event emulator | Articles 5/9/19 motivate concrete failures | No actual DB/API/deployment effect |
| Immutable aliases and per-step versions | Aliases conceal overlap; versions expose stale reads | Dynamic aliases need another model |
| <=6 primitives, <=720 orders, <=2 outcomes per primitive | Finite inspectable domain | Not a stochastic distribution |
| 20,000 paths/120,000 steps/240,000 events | Bounds branch product | Truncation is inconclusive |
| Observation fixed before execution | Scientific integration F2/F3 | Post hoc projection selection rejected |
| All-order conservative baseline | Unknown effects cannot justify independence | No declaration establishes complete effects |
| No fitting or service performance claim | Fixed synthetic manifest and executable labels | Real-source permissions/refinement separate |

## Frozen protocol

Before comparisons, hash manifest, semantics, invariants, observation and budgets.
Include every eligible member and exclusion/cap reason. Timing is descriptive
across matched covered domains and includes parsing/validation, enumeration,
replay, observation, comparison, serialization and total time. Record retained
object counts/environment; these are not billing savings or service throughput.

Controls: distinct writes; local idempotency-key suppression; captured reads then
writes losing an update; snapshot predicates/disjoint writes violating write-skew
invariants; config read followed by a versioned write leaving a stale result;
repeated unkeyed actions duplicating events; aliases concealing shared targets;
incomplete declarations concealing modeled events. Each has a named executable
invariant and no presupposed benefit.

## Evidence status and gates

Decisions derive from current repository scope, not new observations. No external
system/artifact has executed. Human review must assess premises, controls and
interpretation. Negative/inconclusive findings may finish the protocol. Real
adapters require separate rights, complete-effects, atomicity, retries/failure,
observation and execution-refinement evidence/approval.
