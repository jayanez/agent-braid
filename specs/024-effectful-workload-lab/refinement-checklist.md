# SPEC-024 refinement checklist for future real adapters (REQ-006)

Scientific review: pending. This checklist proposes what a future real adapter
must evidence before any claim leaves the closed lab model. Completing the
lab does not satisfy any item; a real adapter needs its own spec, contract, ADR,
authorization and refinement (Article 6). Nothing here authorizes real
execution (`executionAuthorization: false`), and no real refinement or
independent validation is claimed.

Each topic gives what the lab models, what it can and cannot show, what a real
adapter must provide and the evidence form expected.

## Rights

- Lab model: No rights model: the lab has no principals, credentials or permission checks, and `external-action` is a local event append.
- Required of a real adapter: Name the acting principal and the authority each operation needs; show every operation's rights are checked at the same point the effect occurs; show denial leaves state and events unchanged or states what remains.
- Evidence: Per-operation rights table; denial-path traces; no authority inferred from a passing simulation.

## Effect completeness

- Lab model: Operations carry `effects` declarations (`complete`, reads, writes, emits). Missing or `complete: false` declarations abstain (`alias-hidden-effects`, `h2-unknown-exclusion`); footprint validation checks the declared sets against the operation grammar only.
- Required of a real adapter: Prove the adapter's real read/write/emit footprint is covered by the declaration, including indirect, derived, cached and logging effects, not only the modeled keys.
- Evidence: Footprint audit against the real service (traces or source review); adversarial hidden-effect tests; a rule for declarations that drift.

## Atomicity and interleavings

- Lab model: Each primitive is one atomic step; races are modeled only by explicit read and write steps, over complete topological orders of at most 6 operations. No preemption inside a step, no concurrent steps.
- Required of a real adapter: Show the real operation's atomicity unit; if a primitive is not atomic, model its parts as separate steps; justify the schedule class (the lab enumerates dependency-respecting orders, not arbitrary interleavings).
- Evidence: Atomicity evidence per operation; interleaving argument or bounded exploration at the real granularity; explicit statement of what is not enumerated.

## Version and alias enforcement

- Lab model: Versions are integers checked as required preconditions; a stale required version blocks and stops the path. Aliases are immutable and resolved to canonical resources before overlap is judged.
- Required of a real adapter: Show the real system enforces versions and resolves aliases at the effect point (no check-then-act gap), and that aliases are immutable or modeled when they change.
- Evidence: Enforcement point evidence; stale-version and alias-rebind tests against the adapter; canonicalization equivalent to the lab's.

## Return values

- Lab model: Per-instance results are captured and retained. Successful matching terminal values with differing returns are labelled with the `results` mismatch dimension and never promoted (`h2-shared-additions`).
- Required of a real adapter: Decide which return values consumers rely on and compare them, not only terminal state; show returns are deterministic or model their branches.
- Evidence: Consumer dependency list on returns; return-inclusive comparison per adapter; no equivalence claim from terminal values alone.

## Failure after effect

- Lab model: An `external-action` branch can append an event and then error; the effect is never rolled back, the pending suffix is retained and the comparison is `inconclusive` even if projections match (`write-skew`, partial-failure traces).
- Required of a real adapter: Enumerate the real failure points after each externally visible effect and their recovery, including partial application and unknown outcomes (timeouts).
- Evidence: Failure-point inventory; recovery or compensation semantics; evidence that unknown outcomes are treated as unknown, not as success or failure.

## Retries

- Lab model: No retry model: a second outcome is an explicit finite alternative, not a sampled retry, and no timing or backoff exists.
- Required of a real adapter: State the real retry policy (who retries, how many times, with what key) and model each retry as an operation or an outcome; do not infer from absence in the lab.
- Evidence: Retry policy documentation; bounded retry exploration; interaction with idempotency and event visibility.

## Event visibility

- Lab model: Events are an ordered local log with chronology compared separately from terminal state (`trace_safety`); no consumer, delay, reordering or loss model.
- Required of a real adapter: Define who observes events, when, and in what order (including delivery lag, reordering and loss), and whether observation itself is an effect.
- Evidence: Observer and ordering contract; traces under delayed or reordered delivery; event differences kept as explicit mismatch dimensions.

## Idempotency semantics

- Lab model: An optional idempotency key uses a per-path local ledger (`idempotent-events`); it models suppression of a duplicate local append and promises no real exactly-once delivery.
- Required of a real adapter: Establish the real key scope, retention window, collision and expiry behaviour, and what a repeated key returns; show duplicates are suppressed at the real effect, not only recorded.
- Evidence: Key semantics specification; duplicate-delivery tests across expiry and failure; no exactly-once claim.

## Cross-cutting gates

- The lab's cost and recovery results are descriptive on 17 synthetic fixtures;
  they transfer to no real workload without a separate population and
  preregistration.
- An H2-style terminal rule needs the real adapter to stay inside the additive
  class (no guards, versions, external effects); otherwise it abstains.
- A refinement claim needs an independent validation by a party other than the
  author of the adapter; none exists here.
