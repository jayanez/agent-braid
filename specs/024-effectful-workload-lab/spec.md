# SPEC-024: Bounded effectful workload laboratory

## Purpose and scope

Implement a standard-library simulation and analysis laboratory for configuration,
key-value and duplicated external-action failures beyond Git. This is an
executable research protocol: a counterexample or inconclusive coverage report
is a valid result. It does not implement a database, API, deployment adapter,
consumer runtime admission or real external action.

Proposed milestone: **Workload evidence laboratory**. SPEC-020/021's accepted Git
execution domains and SPEC-018's pure exchange evidence remain unchanged.

## Authorities

Clause zero and Articles 1–7, 9, 12–14, 19–20, 23–25; Constitution,
Governance, ADR 0005, operational semantics and claim discipline. The existing
`integer-batch-v1` model excludes partial external failure. This feature uses a
separate proposed `effectful-workload-simulation-v1` contract and requires an ADR
and public contract review before integrating its implementation.

## Requirements and acceptance scenarios

- **REQ-001 — closed private model.** Define typed configurations containing
  key-value state, versions, immutable resource aliases, pending operation IDs,
  captured read results, outcomes and event log. Named primitives are
  `snapshot-read`, `literal-write`, `derived-write`, `guarded-write`,
  `config-read`, `add-constant` and `external-action`. Derived/guarded writes reference an earlier
  result; predicates use a closed integer equality/order grammar. Each primitive
  is one atomic modeled step; explicit read/write steps model a race. No embedded
  Python, callbacks, executable project content or real service handles exist.
  - **SC-001:** Given valid aliases and captured reads, when each order starts
    from a fresh private configuration, then before/after state, versions,
    returned values, alias resolution, pending suffix and outcomes are retained
    per step; no state leaks between paths.
  - **SC-002:** Given executable payloads, URL/handle fields, missing resources,
    cyclic dependencies, duplicate IDs or unknown opcodes, when validation runs,
    then input is rejected before exploration and no project code, network or
    external execution occurs.
- **REQ-002 — finite exploration and honest coverage.** Admit 1–6 logical
  primitive instances and an acyclic dependency graph, <=64 resources and
  <=64 aliases, names/strings <=256 characters, signed integers bounded by
  `2**63-1`, expression depth <=12 and input <=8 MiB. Enumerate complete
  topological schedules (at most 720). A fixture configures one or two named
  transition outcomes per operation; the second is an explicit finite
  alternative, not a sampled distribution. Bound exploration by 20,000 complete
  paths, 120,000 executed steps and 240,000 retained events, in deterministic
  schedule/branch order. Stop at the first exhausted cap.
  - **SC-003:** Given a fully covered small fixture and a fixture exceeding a
    cap, when explored, then reports distinguish complete finite coverage from
    truncation, show admitted/visited/unvisited counts or conservative upper
    bounds, and truncated reports are `inconclusive` with no exhaustive claim.
- **REQ-003 — observation and partial failure.** Freeze observation selection
  before execution and bind it to the request digest. `exact` terminal observation
  includes state, versions, per-instance results, outcome and chronological
  events; `selected-values` includes selected canonical resources and outcome
  only. Successful matching selected values are labelled `terminal-projection-match`
  globally, never full-result, trace, contextual or effect equivalence. Differences
  in returned values, versions or events are explicit mismatch dimensions even
  for successful paths; they cannot be promoted to safety or runtime admission.
  All raw step traces remain available under either mode. Separately assess
  event/partial-failure trace safety: terminal matching cannot erase a disclosure,
  duplicate send or failure after effect. Failure stops the path without rollback,
  retains its pending suffix and already recorded effects, and makes an equivalence
  claim inconclusive even when projections match.
  - **SC-004:** Given a successful send and a configured send-then-error branch,
    when replayed, then both retain the emitted event, the error path retains
    its effect and pending suffix, and matching projections cannot yield a safe
    equivalence claim or execution permission.
- **REQ-004 — workload and uncertainty controls.** Provide lost-update,
  write-skew, configuration-stale-read and duplicate-event/idempotency fixtures;
  provide disjoint positive controls and alias/hidden-effect negative controls.
  The emulator's `external-action` only appends a local event; an optional explicit
  idempotency key uses a local ledger, without promising real exactly-once delivery.
  Absent/unknown effect declarations produce uncertainty; they are never assumed
  complete. Canonical aliases must reveal shared-resource overlap.
  - **SC-005:** Given each named race and control, when analyzed and replayed,
    then a fixture-specific invariant/outcome demonstrates failure or modeled
    prevention; hidden/unknown effects and aliases prevent unsupported independence.
- **REQ-005 — bounded comparison and replay evidence.** Compare declared-effect
  analysis with an all-order conservative unknown-effect/dependency baseline
  that retains every admissible order and abstains on unknown effects. Measure
  classification, visited schedules/paths, uncertainty, counterexample size,
  validation/replay/comparison/serialization time, peak retained objects and total
  wall time. Preserve input/model/tool hashes, observation, host and commands.
  Replay must reproduce branch choices and every step; omission/tampering fails
  closed. A favorable result or speedup is not required.
  - **SC-006:** Given fixed fixtures, substituted branches/hashes and capped runs,
    when replay and comparison execute, then altered artifacts are rejected and
    cost/coverage reports qualify only fully explored finite findings as such;
    no runtime authorization or real workload/service-correctness claim follows.
- **REQ-006 — interpretation and transfer gate.** Publish a bounded report and
  separate proposed refinement checklist for future real adapters: rights,
  effect completeness, atomicity/interleavings, version/alias enforcement, return
  values, failure after effect, retries, event visibility and idempotency semantics.
  - **SC-007:** Given positive, negative or inconclusive findings, when packaged,
    then the protocol may complete with the actual result, human scientific review
    remains pending until recorded, and real execution stays outside this scope.

- **REQ-007 — bounded H2 semantic-overlap experiment.** Register a guard-free
  `add-constant` class: atomic addition of a fixed signed integer to an existing
  canonical resource, complete read/write footprints and no external effects.
  Freeze a finite corpus of 2–4 operations including shared-target additions,
  disjoint additions, dependency controls, overflow exclusions and noncommuting
  literal-write controls. Compare exact-resource-overlap classification, a
  terminal-value additive rule and complete replay of every admitted order.
  The additive rule applies only where every reachable intermediate value is
  within the fixed integer bounds. Required versions/guards invalidate the rule.
  - **SC-008:** Given shared-target additions whose selected-values outcomes
    agree but return values/events differ, when the comparison runs, then the
    report labels only terminal-equivalent candidates, retains those differences
    and contextual/runtime status unknown, never commuting or safe parallelism.
    At least one recovered oracle-confirmed terminal candidate and median whole
    analysis cost no greater than exhaustive replay are the preregistered
    descriptive feasibility criteria; absence or excess cost is a valid negative
    result. Any false terminal candidate, incomplete oracle or altered observation
    prevents a positive assessment. Real H2 usefulness remains unestablished.

## Scientific boundaries and compatibility

The target population is a frozen manifest of generated synthetic fixtures.
Eligibility requires the closed grammar and caps; rejected/truncated members
remain in accounting. Fixtures are authored in-repository under existing licenses;
no real trace permissions are inferred. Labels are executable invariants/outcomes,
not human proxy judgments. There is no fitting, train/holdout split or inferential
performance claim. Report per-family counts and unresolved labels.

Hypothesis: captured reads, versions, aliases and event observations expose order
sensitivity concealed by terminal values in this finite model. The frozen controls
may falsify it; a positive result is not required. Enumeration says nothing about
probabilities, real retries, arbitrary interleaving, contextual equivalence or YB.

New request/report contracts are experimental lab contracts. Preserve existing
AIM, Git, M3 and runtime schemas; never coerce this report into an accepted
certificate. Every output states `executionAuthorization: false`.

## Clarifications and evidence

Simulation uses fresh private in-memory stdlib objects. No sockets, subprocesses,
imports from fixture text, live agents, adapters, network requests, project-code
execution or external mutation are permitted. File access is limited to bounded
inert JSON input and explicitly selected report output. Future real execution
needs its own contract, ADR and authorization.

All tests/reports are planned. Assurance is draft with empty obtained evidence
and human review pending. This delivery implements planning artifacts only.
