# Implementation plan

## Technical context and scope

Implement later under `research/adoption/evidence-program/` with versioned
register/metric/intake contracts, a stdlib-only local validator and report
builder, and `tests/test_adoption_evidence.py`. The first inputs are synthetic
organizations, workload families, local cost/usability episodes, contributions
and reproduction dossiers. Extend no existing runtime or provider client.
The actual planning checkout is `work/foundation-backlog-20261005`.

## Constitution check before research

Articles 13/14 require dimensions of evidence, uncertainty and inspectable
provenance. Articles 19/21/25 motivate measured usefulness and reproducible
artifacts; Article 17 and clause zero restrict scientific/public claims. ADR 0009
and the release-validation policy define externality and preserve pending status.
SPEC-002 proxies and SPEC-011 process records are useful baselines, not observed
adoption. No MUST contradiction or SHOULD exception is identified.

## Research, assumptions and alternatives

The source frame, permission and expected yield precede real collection. A
feasibility report may record zero eligible organizations or external reviewers.
It must not change the population after outcomes are seen. `research.md` records
unit/deduplication, proxy separation, pilot cost boundary and externality choices.
The synthetic MVP requires no source permissions beyond its generated fixtures.
Real workloads use admitted local source artifacts only; outreach and publication
are separate actions requiring authority.

## Design and compatibility

1. Register stable units and the prospective source window. Organization aliases
   resolve once to a canonical local pseudonymous ID. Distinguish workload,
   integration/environment, episode, contribution and reproduction records;
   software/platform/enterprise are overlapping labels rather than separate
   organizations. Unresolved identity joins cannot be guessed.
2. Add a versioned metric manifest with formula, units, baseline, evidence class,
   denominator, source window, eligible IDs, exclusion/missingness rules and
   interpretation limit. Every output binds input hashes and the manifest.
3. Add an offline pilot protocol/intake for report usability and integration
   cost: task fixture, no-report/current-workflow baseline, report condition,
   task completion/error observations, unknowns, total time components and
   optional judgment labels. Synthetic episodes test only intake arithmetic.
   Before any real comparison, freeze rubric, reviewers/adjudication, assignment
   order, budgets, held-out organization/workload units and all-label coverage;
   assess permission/yield and sample/class coverage before interpreting benefit.
4. Intake contributions and counterexamples locally. Preserve raw admitted
   provenance, replay/minimization state and reviewer disposition. Classify
   duplicates and unsupported submissions without dropping them from audit.
5. Intake reproduction dossiers with internal/external classification and
   release-contract-compatible external identity/conflicts. Generate proposals
   for reviewed release records; do not mutate release status automatically.
6. Create current historical-task reconciliation for SPEC-002 T006 and SPEC-009
   T009. Bind inspected source/remote/release records and distinguish each original
   action's evidence and authority. Preserve frozen records; route remaining
   founder/scientific/publication decisions explicitly.
7. Validate/report admitted inputs deterministically. Produce a milestone packet
   linking raw evidence and pending decisions. No agent contacts, telemetry,
   publication or automated promotion are part of the program.

The implementation PR documents intake contract versions and migration behavior.
Any new governance schema/architecture choice gets applicable ADR/review. Do not
fork the existing release-validation or SPEC-011 adoption semantics.

## Validation strategy

`quickstart.md` provides the eight future acceptance contracts. The planned
feature suite uses positive synthetic records, organization alias/cross-label
duplicates, incorrect units, missing evidence, stale hashes, costs omitted from
totals, unresolved rights, maintainer-as-independent claims, anonymous external
claims, changed windows, contradictory outcomes and unauthorized disclosure.
Expected aggregate values are fixed independently of report code.

Prospective real pilot evidence includes full eligibility/attrition and source
rights, predeclared task rubric and baseline, allocation/order, reviewer agreement
and missingness. Observed completion/timing are separate from subjective labels.
No fit, ranking or statistical benefit claim is made by the synthetic MVP. Group
counts and representative coverage bound any later inference. Every reproduction
includes candidate/input/protocol/environment/command evidence and independence
status; a null or negative result is reported rather than filtered out.

Run future `test_adoption_evidence.py`, structural checks, `quick` after an
increment and `pr` once on the stable implementation candidate. Capture actual
commands, outcomes and hashes before marking tasks complete. Independent
reproduction and founder interpretation remain separate from profile success.

## Constitution check after design

Evidence dimensions and source permissions remain explicit, market proxies do
not become observations, and externality cannot be obtained by renaming a
maintainer rerun. Frozen historical decisions remain bound to their domain.
The program satisfies the planning obligations of Articles 13/14/19/21/25 without
claiming the usefulness hypothesis has been demonstrated.

## Human review and unresolved decisions

T001–T005 can implement/test the synthetic local program and dossier controls.
T006 audits historical tasks without assuming approval. T007–T008 check the
complete program and produce a current packet. Real participants, evidence
rights/yield, independent reviewers, publication and residual founder decisions
remain pending; none block implementing the offline synthetic machinery.
