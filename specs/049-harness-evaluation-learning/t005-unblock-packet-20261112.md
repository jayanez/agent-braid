# SPEC-049 T005 unblock decision packet

Prepared 2026-11-12 for the repository owner at `develop` `7e764596`. This is a
decision-support document. It records no decision, runs nothing, changes no
frozen value and authorizes nothing (`executionAuthorization`, native admission
and promotion stay false). Trace: SPEC-049/T005, blockers in
[evidence/t005.json](evidence/t005.json) and
[evidence/evaluation/deterministic-controls-20261108.json](evidence/evaluation/deterministic-controls-20261108.json),
tracked in #1167. Native cohort and native runs are out of scope here (they need
SPEC-049/T004 and SPEC-048/T008).

Sources read: `spec.md`, `plan.md`, `tasks.md`, `case-roster.md`, `corpus.md`,
`evaluation-protocol.md`, `evaluation-report.md`, the T002 and T005-roster freeze
records and the D2 caps record under `evidence/registration/`,
`agent_braid/harness_evaluation.py`, `harness_verification.py`,
`harness_refinement.py`, `tests/harness_guidance_double.py`. Baseline check:
`python3.13 -m unittest tests.test_harness_evaluation tests.test_harness_guidance_double`
ran 64 tests, OK, on this branch.

## 0. Summary and order

Four things are open. They are not equally hard, and one of them (what a cohort
run can claim) is capped by something no decision here can change.

- **Ceiling that no decision lifts.** D3 needs at least 19 independent paired
  units per stratum at delta 0.15 (`MIN_PAIRED_UNITS`, `harness_evaluation.py`).
  At most 4 lineages exist (`corpus.md` L1-L4), and the fallback holdout is L1
  alone. Whatever is decided below, the deterministic cohort is
  `descriptive-only`. No option in this packet produces a noninferiority verdict
  or a utility claim.
- **What a run can honestly show.** Plumbing: that registered units, three arms,
  oracles, denominators, intervals and costs flow end to end, with failures kept
  in the denominator. It cannot show that any guidance helps, because the only
  solver that reads guidance is the R13 double, which encodes its own effect
  (`harness_guidance_double.py` docstring, `LABEL = "synthetic-control"`).

Dependency order (each step needs the previous one):

1. **R11 units** (construction only, already authorized 2026-10-30). Needed by
   everything else. No other decision blocks it.
2. **R3 L3** (optional, can run in parallel with R11 but must be settled before
   the unit set and registration freeze).
3. **R8 arm C** (needs the unit set to exist for discovery probes; fixes the
   third arm candidate hash for `register`).
4. **Run authorization** (a new founder record, last, after units, arm C and R3
   are frozen with hashes).

Downstream: [tasks.md](tasks.md) T008 (offline automatic-promotion assessment)
lists dependencies T005, T006, T013 and says it has no dependency on a positive
T007. T006 and T013 are done. T005 is open, so T008 is formally blocked on T005
reaching a recorded disposition, not on a positive result. SPEC-050 T009
(`specs/050-braid-harness-adaptation/tasks.md`, dependencies T002; SPEC-049/T008
T013) is blocked transitively. I could not verify whether the owner would accept
a descriptive or infeasible T005 disposition as satisfying T008's dependency;
that is a tasks.md reading the orchestrator or owner should make (section 6).

## 1. R11: construct the roster Units

**What it is.** `harness_verification.Unit` (`harness_verification.py:174`) binds
a unit id, partition, source hash, frozen rubric hash and one or more
deterministic oracles (`FixtureOracle`, `SerialReferenceOracle`) into a unit
hash. `harness_evaluation.register` needs one per registered case. Zero exist for
the 7 roster cases. The 2026-10-30 freeze authorized construction, not execution.

**Options.**

- (a) **Construct 6 holdout/discovery Units now**: L1-C01-a, L1-C02-a, L1-C03-a/b/c
  (holdout), L2-C01-a (discovery). Oracles are derived from the owned scenarios
  already in the double (`CASES`): for example for L1-C01-a, expected
  committed output = steps s3, s4 run once and none repeated. Rubric text frozen
  and hashed first. L3-C02-a only if R3 assigns it.
- (b) **Construct only the 5 L1 holdout Units**, leaving discovery (L2) for
  later. Enough for `register` (it requires `partition == "holdout"` for every
  registered unit), but arm C discovery probes then have no discovery unit.
- (c) **Do not construct** and keep T005 recorded infeasible.

**What T005 could then claim.** That the 5-6 cases have frozen, hash-bound,
independent deterministic oracles and that grader material is hidden from the
solver context. It could not claim any outcome, since construction runs nothing.
Honest limit: the units are owned abstractions of anchor tests, not the anchor
tests (same stance as the double), and their oracles would be derived from the
same scenarios the double uses. They therefore are not independent of the double.
I could not verify that an `Observation` (`harness_observation`) can be produced
from the double's events to feed `commit`; `blind_fixture` in the double suggests
a `harness_lab` path exists but I did not trace it.

**Risks.** Oracles written from the double's scenarios make a later cohort
circular (the oracle accepts what the double does). Rubric edits after seeing any
output would break D5; mitigate by freezing unit hashes in a record before
anything runs. A unit built wrong is cheap to fix before freeze and expensive
after.

**Undo.** Units are new files; delete them before the freeze record exists. After
a freeze record, a change needs a new founder decision record (roster freeze
rule).

**Effort.** New files only: a units module or fixture
(e.g. `tests/harness_roster_units.py`), its test, and a new registration record
`evidence/registration/t005-units-freeze-<date>.json` holding unit hashes. No
pinned file changes. Do not edit `tests/harness_guidance_double.py` (pinned in
`t005.json` inputs and `r13-guidance-double.json` outputs; editing changes
`CONTROL_SHA256` and breaks those pins). Do not edit `case-roster.md` (pinned by
the freeze record, `r13` and `t005.json`).

**Recommendation: (a).** It is the smallest step that is already authorized,
reversible and unblocks the rest. Build units for the 6 assigned cases; add L3 if
R3 resolves first.

## 2. R3: where L3-C02-a goes

**What it is.** L3 (S03 `tests/test_git_adapter.py`, case L3-C02-a) is unassigned
because its relation to L1 (S01/S06) is unresolved (`corpus.md` line 71: it
"builds an a.txt/b.txt base by its own setUp with equivalent content to S06").
Merging L3 into L1 means no new independent lineage; standing alone means a 4th.

**Evidence I checked (read only).** `tests/test_git_adapter.py` `setUp` and
`tests/test_git_runtime.py` `setUp` are separately written code. S03 writes
`"base a\n"` and `"base b\n"`; S06 writes `'base\n'` in both files. They also
build different request shapes and use different test class bases. So "equivalent
content" in `corpus.md` is loose: structurally the same two-file, two-branch idea,
not shared code or identical bytes. This is a reading of the two `setUp` methods,
not a provenance audit; commit history was not examined.

**Options.**

- (a) **Stand alone** as its own lineage L3, partition holdout. Holdout = L1 + L3
  = 2 independent lineages, 6 coordination cases. Example: `L3-C02-a` counts as
  one non-repeated coordination pair beside the L1 group.
- (b) **Merge into L1** (holdout). 5 coordination cases, still 1 lineage. Example:
  it counts as another repeated measurement within L1.
- (c) **Keep unassigned** (status quo). Excluded from both partitions.

**What T005 could then claim.** Under (a) the coordination stratum would report
`repeated-within-lineage` for L1 cases only and 2 lineages; still
`below-D3-minimum` (2 < 19). Under (b) and (c) 1 lineage. Under every option the
cohort stays descriptive. R3 changes how many repeats versus independent units are
counted, not the verdict class. It could not support any inference even at 4
lineages.

**Risks.** (a) overstates independence if S03 was copied from S06 (history not
checked). (b) is the conservative error. Either way a late change moves the
holdout composition after units exist.

**Undo.** A decision record can be superseded before outcomes. After outcomes,
changing partition is a leakage risk (D6: lineage leakage stops the run).

**Effort.** One new record under `evidence/registration/` (precedent:
`d2-caps-founder-decision-20261031.json`) plus a unit for L3 (section 1). The
roster text in `case-roster.md` would stay saying "unassigned"; that file is
pinned, so add the new record rather than editing it, and say in the record that
it supersedes the R3 deferral. The synthetic-control double has no `L3-C02-a` case
(`CASES`) and cannot be extended without breaking its pins, so L3 would have a
Unit but no double scenario. I could not verify how `register` and a run would
treat a Unit that the solver cannot run; plan for L3 to be excluded from any
double-driven run.

**Recommendation: (b) merge into L1, or (c) leave unassigned.** It gains nothing
under D3, and (a) risks claiming independence that the evidence does not
establish. Prefer (c) if you want zero new work; choose (b) only if the L3 case is
wanted as a fifth coordination unit. Do not spend a unit build on L3 for (c).

## 3. R8: arm C (contrastive refinement)

**What it is.** Arm C must equal the candidate that a recorded
`harness_refinement.run_round` selected, or the base after an explicit keep-base
(`harness_evaluation._arm_c`; an inconclusive or refused round defines no arm C).
`run_round` needs a manifest, a hash-bound `SelectionPolicy`, a `propose(scope)`
callable and a `probe(request)` callable. Only injected test doubles exist
(`tests/test_harness_refinement.py`). R8 was deferred on 2026-10-30, option (a).

**Options.**

- (a) **Keep deferring** (status quo): arm C only through the native branch
  (T004/T008). Example: cohort stays unregistrable.
- (b) **Accept keep-base** (a proposer that abstains in both scopes): round records
  `keep-base`/`all-abstained`, C = A by construction. `register` accepts it.
- (c) **Scripted deterministic proposer plus double-backed prober.** Proposer
  returns fixed subsets of the frozen arm-B directive lines (the only guidance the
  double reads: resume line only, drift line only). Prober scores them by running
  the double on discovery units. The round may select a candidate, giving C
  different from A and possibly from B. Needs: a manifest whose base inventory is
  A and whose `allowedComponentPaths` include `guidance/checkpoint.md`, a policy
  (`marginMicros`, `maxProbes` at most 4) and the discovery units from section 1.

**What T005 could then claim.**

- (a): nothing new; deterministic cohort remains infeasible.
- (b): that `register` and the three-arm report run with C = A. A and C cells are
  identical by construction, so it carries no information about refinement and
  must be described as a plumbing control (`case-roster.md` section 4, R8 (b)).
- (c): that the propose-probe-compose pipeline runs end to end and selects a
  candidate under a frozen policy. It cannot claim refinement helps: the proposer
  is scripted and the prober is the double, which encodes the effect it measures.
  Result is `synthetic-control`-grade even though `register` only accepts cohort
  `synthetic` or `native` (`COHORTS`); a report row would read like a cohort row
  unless the evidence record labels it. That mislabel risk is the main hazard.

**Risks.** (b) invites a reader to treat "C = A" as "refinement did not help".
(c) is circular and needs more wording discipline. Discovery has one case (L2-C01-a,
continuity only; `case-roster.md` section 1), so an (c) round sees only
continuity material. Arm D (library ablation) stays conditional either way
(R10), and a C that is A (b) makes D comparisons against C meaningless.

**Undo.** All new artifacts. A recorded round can be superseded by a new round
record before the cohort run; no pinned file changes. A new arm C hash needs the
registration to be recomputed, which is fine before any outcome.

**Effort.** (b): small (one manifest, one policy, one abstaining proposer, one
probe stub, one test) in a new test-helper file and a new freeze record. (c): same
plus a prober wrapping the double and a policy margin choice. Both avoid touching
`harness_evaluation.py`, `harness_refinement.py` and the double. I could not
verify that `run_round` can be driven with the double as prober without changes;
`tests/test_harness_refinement.py` shows a probe interface (`probe(request)`) but I
did not read its manifest setup.

**Recommendation: (b) as a clearly labelled plumbing control, after R11.** It is
cheap, reversible, keeps the record honest, and closes the `register` blocker
without inventing a refinement effect. Reject (c): it adds a second circular
layer and offers no claim beyond (b). Keep (a) if the owner prefers to wait for
native evidence; it is the only option that preserves a path to a real arm C. This
is the owner's call; (b) accepts the R8 option the 2026-10-30 freeze already
described and deferred.

## 4. Authorization to run (not only construct)

**What it is.** A new founder record permitting the deterministic cohort to be
executed once units, arm C and R3 are frozen. Today `executionAuthorization` is
false everywhere and the roster freeze authorizes construction only.

**Options.**

- (a) **Authorize one offline run** of the registered cohort with the R13 double
  as solver (cost: additional cash EUR 0, no host, model or paid route), recording
  all cells (A, B, C), denominators, intervals, T012 cost record (zero attempts
  cost) and a label stating `synthetic-control`. Example output: per-stratum
  A/B/C counts, each cell reported even when `not-completed`.
- (b) **Authorize dry registration only** (call `register`, record hashes and arm
  order, no `evaluate`). Example: freeze record with unit and arm hashes, no
  outcome rows.
- (c) **No run authorization**; close T005 deterministic path as infeasible and
  wait for native.

**What T005 could then claim.** (a): the pipeline, oracle independence from the
solver where it exists, full denominators and zero cost; every verdict
`descriptive-only` (reasons `repeated-within-lineage`, `below-D3-minimum`). It
cannot claim false safe admissions, missed parallelism or review effort: the
double has no such notions and `PENDING_ENDPOINTS` lists them as not computed
(`harness_evaluation.py`). It cannot claim guidance utility, any D4 verdict,
economic acceptance or promotion. (b): that the registration is internally
consistent. (c): status quo.

**Risks.** The main one is mislabel: outputs of an (a) run share `cohort:
"synthetic"` with a hypothetical real synthetic cohort and could be quoted as a
result. Mitigation: the evidence record, the report text and the founder record
must repeat that the solver is the R13 double and the rows are verdict-ineligible.
A second risk is circular oracles (section 1). Third: if a run is authorized and
outcomes then prompt changes to units or arms, D6 leakage rules apply. Freeze
first.

**Undo.** Do not retract executed outcomes; they stay in the record with their
limits. Before execution the authorization record can be withdrawn by a superseding
record. The run itself changes no repository code.

**Effort.** One authorization record plus the run script producing
`evidence/evaluation/deterministic-cohort-<date>.json`, an `evaluation-report.md`
update and a new `t005.json` version. `evaluation-report.md` is pinned only by
`evidence/t005.json` (the 049 evidence being regenerated), so editing it needs the
t005.json re-pin that the orchestrator already performs. `evaluation-protocol.md`
is pinned by `specs/065-native-claude-containment/evidence/t004.json` and
`specs/067-assurance-profiles/evidence/t009.json` as well as 049 records: do not
edit it; if a protocol note is wanted, put it in a new record. Per the brief,
tasks.md and assurance.json edits belong to the orchestrator.

**Recommendation: (a), conditional on R11 and R8(b) being frozen first, and with
the `synthetic-control` labelling written into the authorization itself.** It
turns the blocked task into a completed, honest, zero-cost control and lets T008
proceed with a recorded disposition. If the owner will not accept a result that
tells nothing about utility, choose (c) and record the infeasible disposition as
final for the deterministic path; do not pick (b), which adds a record without
adding evidence.

## 5. What T005 can and cannot then say, by combination

| R11 | R8 | Run | T005 can say | T005 cannot say |
|---|---|---|---|---|
| built | (b) keep-base | (a) run | Pipeline runs end to end offline; A/B differ where the double's frozen mapping predicts; C = A by construction; all denominators and zero cost shown; descriptive-only | Any utility, refinement, library or inferential result; false-safe, missed-parallelism, review-effort endpoints |
| built | (a) defer | (b) dry | Registration cannot bind C, so nothing | Cohort registered |
| not built | any | any | Status quo (infeasible) | Anything new |

Native cohort and arm D (library ablation) stay not run in every row.

## 6. Effect on downstream tasks

- **SPEC-049 T005** tasks.md acceptance also says "native cohort additionally
  T004" and "library ablation additionally T006". With a deterministic-only run
  the task could be ticked only if the owner accepts a re-scoped disposition
  (deterministic controls only, native and arm D explicitly pending) or the
  orchestrator splits the task. I did not edit tasks.md; this needs an owner or
  orchestrator call.
- **SPEC-049 T008** (promotion-policy offline assessment; tests in
  `tests/test_harness_promotion.py`): runs on synthetic controls, so it needs only
  a T005 disposition and does not need positive evidence ("no dependency on
  positive T007"). The packet's recommended path gives it one; (c) also gives it
  one (infeasible), though a weaker one. Unverified: whether an "infeasible"
  disposition satisfies the dependency in the owner's view.
- **SPEC-050 T009** (disabled-by-default automatic-promotion policy engine, new
  `agent_braid/harness_auto_promotion.py`): blocked transitively through T008.
  It would still require its own native-activation adoption; none of the options
  here provides that.
- **SPEC-049 T007/T010**: T007 needs a T005 report and native evidence for native
  acceptance; no option here yields it. T010 can report the deterministic branch
  as descriptive and native as pending.

## 7. Pin and freeze conflicts found

None blocks this packet (it adds one new file and edits nothing). Constraints for
the follow-up work:

- `case-roster.md` sha `6a1e55f8...` is pinned by
  `t005-roster-founder-freeze-20261030.json`, `r13-guidance-double.json`,
  `deterministic-controls-20261108.json` and `t005.json`. Do not edit.
- `evaluation-protocol.md` sha `379d2b86...` is pinned by those 049 records and by
  `specs/065-native-claude-containment/evidence/t004.json` and
  `specs/067-assurance-profiles/evidence/t009.json`. Do not edit.
- `tests/harness_guidance_double.py` sha `12090b19...` is pinned in `t005.json`
  and `r13-guidance-double.json`; the double self-checks `CONTROL_SHA256`. Adding
  an L3 scenario or a new directive changes it. Do not edit.
- `evaluation-report.md` is pinned only by `evidence/t005.json`; updating both
  together is the existing pattern.
- `evidence/t005.json` and the 2026-11-08 deterministic-controls record are
  current evidence and are superseded by a new dated record, as 2026-11-08
  superseded 2026-10-29.
- Everything recorded as `Unverified` above (observation path from the double to
  `commit`, `run_round` driven by the double, L3 provenance history) should be
  checked by the implementing agent before the owner decides R8 (c) or L3 (a).
  Also: D3 reference table in `evaluation-protocol.md` lists 14/19/29; code
  yields 19 at delta 0.15 and that is the number used here.
