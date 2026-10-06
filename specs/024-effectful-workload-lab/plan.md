# SPEC-024 implementation plan

## Technical context and scope

Implement an isolated `research/workload_lab/` package and stdlib CLI with inert
JSON fixtures and unittest coverage. Existing `research/lab/` conventions may
inform the design, but its model name and assurance are not reused. This planning
change delivers no functional implementation.

## Constitution check before research

Articles 3/5/24 require typed effects/configurations and failure. Articles
2/4/6/12 require order semantics and forbid deriving concurrency from sequential
agreement. Articles 9/19 require counterexamples/concrete failures; this synthetic
protocol does not fulfill real-workload validation. Articles 13/14 require scoped
replay and uncertainty. Articles 20/23/25 permit an independent laboratory.
Clause zero forbids implied YB claims. ADR 0005 excludes this domain; T001 drafts
and reviews a separate interface/architecture decision. No MUST conflicts or
SHOULD deviations are identified within the simulation scope.

## Research, assumptions and alternatives

See [research.md](research.md). Primitives are atomic; stale captured reads are
explicit operations/results. This keeps schedule enumeration at <=6 steps and
avoids an unstated interleaving model. Two outcomes per primitive can yield
`720 * 2**6` paths; 20,000 can truncate. Never label a capped run complete.
Branches have no probability or fairness interpretation.

## Design and compatibility

T001 defines the grammar and proposed ADR. Configuration carries state, monotone
versions, immutable aliases, results, local idempotency ledger, pending IDs and
events. Resolve aliases before conflict analysis; traces retain requested alias
and canonical resource. Validate resource existence and result/dependency
references before exploration. Missing initial resources are invalid requests;
runtime arithmetic overflow is an explicit error. False guards/stale required
versions/unmet dependencies block and stop the path. An external-action branch
can append an event before returning error; that effect is never rolled back.

T002 implements parsing/transitions. T003 enumerates orders and branch assignments
with caps and a fresh state per path. T004 binds observation and full replay to a
request digest covering inputs, branches, aliases, model and observation. Retain
all traces even when projected out. Use `terminal-projection-match` for every successful
selected-values match, with separate returned-value/version/event mismatches;
never promote it to full-result, contextual, effect equivalence or safety. Report
terminal matching and trace safety
separately. T005 freezes fixtures/invariants. T006 compares candidate and
conservative analysis with identical manifest/budgets/coverage. Unequal coverage
cannot support a comparative cost/correctness claim. T007 packages reproduction
and review. T008 implements the separate bounded H2 comparison. No practical-core API/CLI or dependency change is required.

## Validation strategy

REQ/SC mapping is mirrored in assurance and [quickstart.md](quickstart.md). Planned
checks cover private state, grammar limits, aliases, returned values/versions,
all caps, branches, partial failure and tampering. Preserve raw outputs, hashes,
commit, environment and full costs. Run quick after increments and PR once on a
stable implementation. These do not supply clean reproduction/scientific review.

## Constitution check after design

Trace-safety reporting prevents projections from concealing events; uncertainty
and cap exhaustion abstain. No real execution exists. Article 6's refinement gate
and all historical domains remain intact; no authority is amended.

## Human review and unresolved decisions

Review the contract/ADR before implementation integration, then the frozen
manifest and scientific interpretation. A negative/inconclusive result can
complete the protocol. Future real adapters need a distinct spec and refinement.

## Registered H2 class and cost boundary

Add `add-constant` as an atomic primitive under this new simulator's signed-integer bounds; it is not a captured-result `derived-write`. Source the candidate rule from guard/version-free additions with complete canonical footprints. Recompute each order from the common initial state and reject any overflow/blocked/error path. Use `selected-values` to assess terminal candidate recovery only; retain return/chronology differences and deny contextual and runtime conclusions.

Freeze the corpus and complete replay oracle before scoring. Compare exact-resource-overlap, additive terminal rule and exhaustive replay on the same immutable fixtures. Candidate recovery is the count of overlap-conflicting cases whose complete oracle confirms terminal values; false-candidate count must be zero within that corpus. Register median full analysis cost <= exhaustive-replay cost as a descriptive feasibility threshold, with parsing, footprint validation, classification, serialization and candidate checking included. Record 3 unmeasured warm-ups and 20 measured repetitions per method/fixture; alternate method order deterministically. No synthetic delay, post hoc corpus selection or removal of failures. Timings are local descriptive engineering results, not inference about real safe parallelism. Invalid/unequal coverage makes cost comparison inconclusive. H2's useful-runtime claim still needs a separate refinement and real-workload protocol.
