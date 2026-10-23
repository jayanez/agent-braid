# Effectful workload simulation v1

Status: proposed experimental interface for SPEC-024/T001. Independent technical
review and the architecture decision must precede implementation integration.
This contract adds no AIM certificate, runtime grant or real adapter capability.

## Request and validation

The request is an exact object with `model`, `initial`, `operations`,
`observation` and `caps`. Model is `effectful-workload-simulation-v1`.
`initial` has exact fields `state`, `versions` and `aliases`: 1–64 named integer
resources, a matching resource-to-nonnegative-version map, and 0–64 immutable
alias-to-resource/alias entries. Alias names cannot shadow resources; cycles and
missing targets reject. Names are nonempty Unicode scalar strings of at most
256 characters. Integers exclude booleans and have absolute value <=2**63-1.
Input is at most 8 MiB, JSON nesting at most 64; duplicate members, floats,
nonfinite constants, lone surrogates and unknown fields reject.

There are 1–6 operations with unique IDs. Common exact fields are `id`, `kind`,
`resource`, `dependencies` and `outcomes`; optional common fields are
`requiredVersion` and `effects`. Resources must resolve through the initial
alias map. Dependencies are unique existing operation IDs, exclude self, and
form an acyclic graph. Their order in the request has no scheduling meaning.
`outcomes` contains one or two unique alternatives from `success`, `error` and,
for `external-action` only, `send-then-error`. These are named finite branches,
not probabilities. At least one success alternative is not required.

| Kind | Additional exact fields | Successful modeled transition |
|---|---|---|
| `snapshot-read`, `config-read` | none | Return the current canonical resource integer |
| `literal-write` | `value`: integer | Replace resource, increment version, return new value |
| `derived-write` | `expression` | Evaluate captured-result expression, then write as above |
| `guarded-write` | `expression`, `guard` | Evaluate guard first; false blocks the path; otherwise write |
| `add-constant` | `amount`: integer | Add to current value, write and return new value |
| `external-action` | `event`: nonempty scalar string <=256; optional `idempotencyKey` | Read resource, append a local event and return 1 if appended, otherwise 0 |

Expressions are exactly `{"int": n}`, `{"result": operationId}` or
`{"op": "add"|"subtract"|"multiply", "left": expression, "right": expression}`.
Depth is at most 12. Captured-result references must name read operations in
the transitive dependency set; unavailable captures block the path. Guards are
exactly `{"op": "eq"|"lt"|"le", "left": expression, "right": expression}`.
Resources cannot be read implicitly from expressions. Intermediate arithmetic
overflow produces an error before the current write; completed earlier effects
remain. Version increment beyond 2**63-1 likewise errors before either state or
version changes. A stale `requiredVersion` blocks before the operation effect.

`effects`, when present, is exactly `complete` (boolean), `reads`, `writes` and
`emits` (unique resource-name lists). Lists resolve aliases before comparison.
Declarations never override the transition model. Missing, incomplete or
inconsistent declarations produce explicit unknown/uncertainty and cannot
support independence. A complete declaration must cover actual modeled access;
extra declarations remain conservative. `external-action` reads its canonical
resource and emits on that same resource: both `reads` and `emits` must cover it.
The event object has exactly `operationId`, canonical `resource`, constant `name`
(the supplied `event` string), observed integer `value` and `idempotencyKey`
(string or null). It never modifies the resource. Read primitives require reads;
literal-write requires writes; derived-write/guarded-write require writes plus
reads covering the canonical resources of every read operation referenced by
their expression or guard. Those references are the `result` expression leaves
and must also be in the operation's transitive `dependencies` set;
add-constant requires reads and writes. A requiredVersion additionally requires
reads for every kind. The modeled idempotency ledger is not a real resource.

## Paths, failure and observation

Start every path from a private copy of initial state/versions, with empty
results, chronological events and idempotency ledger. Enumerate dependency-valid
schedules lexically by operation ID and branch assignments in declared outcome
order. Stop a path at its first blocked/error operation. A generic `error` has
no current-operation effect. `send-then-error` performs the external-action
event/idempotency step and then errors. Preserve its event and the unexecuted
suffix. Idempotency is local to one path; the first successful emission for a
key suppresses later emissions for that key, including a retry after an emitted
error. It is not a real exactly-once guarantee.

Retain before/after configuration and status for every attempted step, including
requested alias, canonical resource, outcomes, results, versions, events and
pending suffix. Selected observations never delete raw dimensions.
`observation` is exactly `{"mode":"exact"}` or
`{"mode":"selected-values","resources":[names...]}`. Selected names are unique
after canonical resolution. Exact terminal observation contains full state,
versions, results, outcome and chronological events. Selected-values contains
only selected canonical values and outcome. All successful selected matches use
`terminal-projection-match`; exact finite agreement uses `finite-exact-match`.
Neither means contextual equivalence, commutation, trace safety or runtime
admission. Failure, blocking or incomplete coverage makes equivalence
inconclusive. Report returned-value/version/event mismatch dimensions separately.

Report `traceSafety` separately, with `partialFailurePaths` (events retained on
error paths), `duplicateEventPaths` (a repeated canonical resource/name/key tuple
in one path) and `eventOrderMismatch` (different chronological full event lists
across successful paths). A listed witness yields `witness`; without a witness,
any incomplete, blocked or failed path yields `inconclusive`; otherwise report
`finite-no-event-witness`. These are named finite diagnostics, not a universal
safety verdict. The original full event lists remain available for inspection.

`caps` is exactly `paths`, `steps`, `events`, nonnegative integers bounded above
by 20,000 / 120,000 / 240,000. Zero is legal. There are at most 720 topological
schedules and two branch choices per operation. Count assigned-outcome paths
even when an early failure makes later assignments observational duplicates.
Report `assignedPaths`, `attemptedPaths` and `completedPaths` separately.
Charge one path slot before starting each assignment, including one that later
hits a cap; zero path slots starts none. Completed means a success/error/blocked
terminal trajectory, not an interrupted cap trajectory. Thus attempted paths
never exceed the path cap and completed terminal paths cannot exceed attempts.
Stop before exceeding any cap. Retain a partially attempted path if a step or
event cap is reached; distinguish it from completed paths, with pending suffix
and actual consumed counts. Exhausted domains are `inconclusive`; include total
schedule/assigned-path counts, unattempted assignments equal to assigned minus
attempted paths, partial paths equal to attempted minus completed paths, and an
unresolved upper bound equal to assigned minus completed paths. No
probability, fairness or arbitrary interleaving claim follows.

## Report and replay

Reports include format `effectful-workload-report-v1`, original validated
request, request/source digests, complete raw paths, coverage/cap counts,
observation comparison, mismatch dimensions, declaration uncertainty and the
required `traceSafety` diagnostic.
Canonical bytes use sorted keys, compact JSON, ASCII escaping and no floats;
hashes use SHA-256. Source bindings cover this contract and the interpreter,
explorer and evidence verifier. The verifier independently replays the original
request against current bound source and compares the complete deterministic
report including `traceSafety`, rejecting altered/omitted branches, steps, observations, counts or
bindings. Timings belong to a separate experiment report, not deterministic
replay identity. Every report/verification contains `executionAuthorization:false`.

The experimental stdlib CLI has `explore INPUT --output OUTPUT` and `verify
REPORT`. Read bounded regular nonsymlink files; write reports exclusively to an
explicit new regular path without replacing input or existing output. Reject
symlink ancestors. The CLI performs no network, process launch, callbacks,
fixture-code import or evaluation. Verification is read-only.

## Comparison and compatibility

T005 fixes independent expected race/control outcomes before T006/T008 measures
them. Retain the conservative baseline's entire admissible domain and unknown
effects. Comparisons require identical manifest, caps, observation and covered
domain. H2 admits only complete, guard/version-free additions whose every
intermediate value is in range under complete replay. Freeze the corpus and
whole-cost threshold first; execute the already specified three warm-ups and
twenty measured repetitions per method/fixture, alternating method order.
Report all exclusions and negative/inconclusive results. No favorable cost
result is required. Existing schemas, grants, authorities and frozen evidence
remain unchanged. Real adapters require separate refinement, rights and authority.
