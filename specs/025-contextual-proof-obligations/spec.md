# SPEC-025: Contextual safety and restricted proof obligations

## Purpose and scope

Implement a bounded continuation checker for `integer-batch-v1` and prepare
reviewable candidate statements/premises for T1 independence, T2 schedule
equivalence and the anchored-sequence exchange class. This addresses scientific
integration F2/F4 and the outstanding restricted-theorem targets without claiming
an accepted theorem today. Proposed milestone: **Formal interaction research**,
separate from runtime utility or admission.

A complete protocol can find counterexamples, reject a premise or conclude that
external comparison/mechanization is infeasible. A proof may be a carefully stated
unmechanized result after specific proof review; finite enumeration is never
promoted to a universal proof. No practical-core dependency, live execution,
policy authorization or model expansion is included.

## Authorities

Clause zero and Articles 2–4, 6, 8–11, 13–14, 17–18, 20, 22–25;
Constitution, Governance, ADRs 0005/0017, operational semantics, claim discipline,
structured exchange and scientific integration. Preserve existing notation:
integer sequence `a;b` executes a then b; quantum-form composition is right to
left and adjacent `B=P ∘ R`; anchored crossings apply left to right. Far and
adjacent relations keep their distinct meanings. Invertible exchanges do not
make real actions reversible; involutive actions factor through permutations.

## Requirements and acceptance scenarios

- **REQ-001 — exact premises and candidate statements.** Inventory carrier,
  operation typing, enabledness, complete effects/control reads, version checks,
  result/event observations, dependencies, admissibility, failure and continuation
  premises of T1/T2. State anchored immutable-base/fresh-ID/flattening/closure,
  residual/intent/result preservation and relation/invertibility premises. Bind
  every statement to exact executable source and authority hashes. Distinguish
  candidate, finite checked, reviewed unmechanized proof and mechanized proof.
  - **SC-001:** Given T1/T2 sketches and anchored semantics, when statements are
    drafted, then every premise, quantifier and equivalence is explicit, source
    mappings and unproved gaps are listed, and no current theorem claim appears.
- **REQ-002 — bounded continuation checker.** Accept two reachable configurations
  obtained from prefixes of the same valid integer fixture with the same consumed
  operation IDs and remaining IDs. Require an explicit, preselected suffix set
  including the empty suffix; suffixes use existing remaining IDs without retries
  or new operations. Total prefix-plus-remaining fixture size is <=6; existing
  resource/integer/expression/input limits remain. At most 720 suffix schedules,
  20,000 configuration/suffix checks and 120,000 executed steps are allowed.
  Check each remaining operation's enabledness, compare the chosen observation
  after every listed suffix and retain all return values, versions, outcomes,
  pending IDs and traces. Invalid inputs fail closed; bound exhaustion is
  inconclusive. Unsupported event/resource/result-reading extensions are rejected.
  - **SC-002:** Given terminally matching prefixes and a suffix that observes
    hidden state or changed enabledness/returned values, when checked, then a
    minimal suffix witness is produced with full configurations; terminal matching
    cannot imply contextual universal equivalence.
  - **SC-003:** Given valid matching listed continuations, omitted/altered suffixes,
    >6 operations or exhausted bounds, when checked/replayed, then only complete
    bound-matched evidence yields `equivalent-for-listed-continuations`; unsupported,
    tampered or capped evidence is rejected/inconclusive, never universal.
- **REQ-003 — trace safety and premise counterexamples.** Run controls for hidden
  state/projection, return-value dependence, initial-context-only pair tests,
  version/guard enabledness, event chronology and noncommuting operations. Preserve
  divergent intermediate events even where terminal projection matches. The
  integer model has no real external effects; event controls demonstrate its
  observation boundary without certifying real trace safety.
  - **SC-004:** Given each omitted-premise control and disjoint positive controls,
    when checked, then the omitted premise has a reproducible witness, outcomes
    remain scoped and no finite result is described as a proof of T1/T2.
- **REQ-004 — anchored candidate proof packet.** Prepare a mathematical argument
  and executable cross-check for immutable-base inserts, canonical sibling order
  and fresh IDs. State whether the mathematical carrier covers all finite valid
  inputs or only the bounded implementation, and prove the mapping to the
  implementation separately. Address pair exchange, closure, residuals, far
  commutation, adjacent braid coherence and exchange involutivity. Raw chronological
  traces remain unequal where appropriate; their quotient requires an explicit
  premise. Delete/nested-anchor/nondeterministic extensions require a distinct
  typed model contract/ADR and cannot reuse M3 evidence.
  - **SC-005:** Given the current insert class and unsupported extensions, when
    the packet/cross-check is produced, then premises/relations/source bindings
    agree with ADR 0017, unsupported inputs stay excluded and formal acceptance
    remains pending until specific independent proof review.
- **REQ-005 — CoAgent research comparison feasibility.** Implement a research-only
  comparison-readiness report under adoption track `AT-2026-005-coagent-comparator`.
  Assess primary source/artifact availability, immutable version, license/use
  rights, operation/state/effect/observation and execution assumptions, comparison
  question and mismatch/coverage. Record unavailable or noncomparable artifacts
  as valid feasibility outcomes. No automatic download, installation or execution.
  An executable comparator requires isolated artifact/source/license review and
  a separately authorized, pinned protocol with mapped compatible semantics.
  - **SC-006:** Given the adopted research-only disposition, when feasibility is
    recorded, then availability/rights/semantic gaps are explicit and unsupported
    comparisons abstain; no paper measurement is treated as reproduced evidence.
- **REQ-006 — proof review and tool value gate.** Assess handwritten proof review
  and proof-assistant/tool options only against a concrete remaining obligation,
  expected verification benefit, trusted base, maintenance and license cost. No
  adoption/install is required by the protocol. Any dependency adoption needs
  an ADR and founder decision. Submit candidate proof and finite evidence
  separately; record reviewer conclusions/counterexamples and unresolved gaps.
  - **SC-007:** Given completed artifacts and possible negative findings, when
    reviewed, then proof status, bounded experimental status and human approval
    are distinct; a reviewed proof may be unmechanized, and tool infeasibility
    does not force dependency adoption or a theorem claim.

## Scientific boundaries and compatibility

Hypothesis: retaining enabledness/results/versions and inspecting continuations
will expose false reusable-equivalence claims hidden by terminal projections.
Anchored set-union/canonical flattening may support a restricted reviewed proof.
Neither hypothesis must survive for the protocol to complete.

Population is a frozen synthetic integer fixture/suffix corpus and the explicitly
stated anchored carrier. Labels are executable outcomes and proof-review findings,
not human task-utility proxies. Freeze controls/suffixes before checking candidate
methods; report excluded, missing and inconclusive cases. No training or inferential
performance comparison occurs. CoAgent external rights/availability are unresolved
until T006 and do not imply permitted execution.

Reuse integer semantics without changes. A new contextual request/report is a
versioned experimental research interface, not an AIM/Git/runtime certificate.
`equivalent-for-listed-continuations` never means every admitted continuation.
All executable outputs state `executionAuthorization: false`. Historical M3/M4
acceptance stays within its original observations and execution domain.

## Clarifications and evidence

Future checker source belongs to `research/contextual_lab/`; no execution of
real operations is admitted. T1's chronological events can differ even for disjoint
writes. Any proposed event-permutation equivalence must state that modeled
continuations cannot inspect event order and prove congruence; exact chronological
observation cannot be silently replaced. T2 needs the pair premise in every
reachable context, not just the initial state.

All scenarios/tests are planned in quickstart. Assurance is draft, obtained
evidence is empty and human/scientific/proof review remains pending. This delivery
produces implementable planning records, not accepted formal results.
