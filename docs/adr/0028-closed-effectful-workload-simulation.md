# ADR 0028: Closed effectful workload simulation

- **Status:** Accepted by the founder on 2026-10-21 for the bounded simulation profile; implementation acceptance, scientific review (T007) and later profiles remain separate.
- **Date:** 2026-10-21
- **Decider:** Juan Antonio Yáñez García (`@jayanez`). The canonical text below was approved section by section on 2026-10-23.
- **Constitutional articles:** 0, 2–6, 9, 12–14, 19–20, 23–25.

## Context

ADR 0005 limits the bounded laboratory to an integer-batch domain; it cannot
express private state, captured reads, versions, aliases, failure after an
effect or retained events, which Articles 2–5 and 12 require before any claim
about effectful order or concurrency. SPEC-024 therefore proposed a separate
closed simulator. Its reviewed contract
[`simulation-v1.md`](../../specs/024-effectful-workload-lab/contracts/simulation-v1.md)
(SHA-256 `ec0851a4503ec0d40d7dff9a8b9542a5d3dcc44843d2458c8dd738ebd4dedad5`)
and [decision request](../../specs/024-effectful-workload-lab/implementation-decision.md)
were adopted by the founder on 2026-10-21 (“Apruebo la arquitectura acotada
T001 de SPEC-024 …”), recorded in the feature-local
[decision](../../specs/024-effectful-workload-lab/architecture-decision-20261021.md).
That record deferred canonical numbering and authority-inventory
reconciliation; this ADR performs it.

## Decision

Implement `research/workload_lab/`, a separate standard-library finite
simulator for the closed `effectful-workload-simulation-v1` grammar: private
state, captured reads, versions, immutable aliases, at most two branches per
operation, at most six operations and the contract caps (20,000 paths /
120,000 steps / 240,000 events). Local JSON input and an exclusively created
report are the only filesystem interface; the external-action primitive only
appends an in-memory event. Every output carries `executionAuthorization: false`.

Preserve ADR 0005's integer-batch domain and every runtime/grant interface.
No model, real source, real external action, process, network, scientific
acceptance or capability promotion is decided here.

### Amendments

The simulation contract is unchanged by these amendments.

- 2026-10-22 — Exploration stops before the retained path payload exceeds
  256 MiB and records `capReason: "bytes"`, so a report stays within the
  512 MiB transport bound. This is an implementation bound beyond the contract
  caps; the experimental report schema admits the new value.
- 2026-10-22 — CLI refusals name their reason (for example `symlink-path`,
  `output-exists`, `too-large`, `invalid-json`, `invalid-request`) instead of a
  single generic reason; exit codes and the no-write behaviour are unchanged.
- 2026-10-22 — Before any registered run, the founder approved re-registering
  the H2 cost criterion (option A, margin m = 50,000 ppm): the additive rule's
  own stage is paired with the exhaustive-replay total of the same fixture and
  repetition, and the distribution-free one-sided 95% upper bound of the median
  paired ratio must be at most 5%. The withdrawn whole-cost criterion compared
  two almost identical costs and was decided by timer noise. The protocol is
  `effectful-workload-protocol-v2`.

## Alternatives considered

- Extend ADR 0005's integer-batch semantics: rejected; it would silently change
  frozen evidence and conflate two domains.
- Reuse runtime grants or the M4 runtime: rejected; analysis and execution stay
  separate products (Article 20).
- Integrate real DB/API/deployment execution: rejected; no real sources or
  external actions are admitted at this stage.
- Sampled or probabilistic exploration: rejected; only finite enumeration with
  explicit inconclusive coverage is claimed.

## Consequences

- Positive: effect order, races, failure after effect and declaration
  uncertainty become inspectable, replayable synthetic evidence.
- Negative: synthetic fixtures only; no real-workload, runtime-safety,
  contextual-equivalence or H2 usefulness claim follows.
- Compatibility: new experimental request/report schemas; existing schemas,
  ADR 0005 and runtime interfaces are unchanged. Editing any bound source
  invalidates earlier reports by design.
- Security: no process, network, dynamic import or eval surface; symlink-free
  bounded files only.
- Research: negative or inconclusive outcomes are valid completions; T007
  scientific/human review remains required.

## Validation

Focused workload-lab tests, contract validation and fresh-clone `pr` profiles;
independent replay (`verify`) of every report; the frozen control corpus (T005
evidence); and the registered H2 protocol v2. Revisit if a real adapter, a new
effect kind or a probabilistic claim is proposed, or if independent review
finds a contract violation.

## References

- [`specs/024-effectful-workload-lab/contracts/simulation-v1.md`](../../specs/024-effectful-workload-lab/contracts/simulation-v1.md)
- [`specs/024-effectful-workload-lab/architecture-decision-20261021.md`](../../specs/024-effectful-workload-lab/architecture-decision-20261021.md)
- [`specs/024-effectful-workload-lab/implementation-decision.md`](../../specs/024-effectful-workload-lab/implementation-decision.md)
- [ADR 0005](0005-evidence-contracts-and-bounded-laboratory.md)
- [`research/workload_lab/SEMANTICS.md`](../../research/workload_lab/SEMANTICS.md)
