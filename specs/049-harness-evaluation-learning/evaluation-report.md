# HAR.2 evaluation report

Status (2026-11-12): one offline deterministic **synthetic-control** cohort run
was executed under a scoped owner authorization; it is **plumbing only**, every
comparison is descriptive-only under D3, and it supports no utility claim. Native
cohort **not run** (pending); library ablation (arm D) **not run**. SPEC-049/T005
stays open. See "Deterministic synthetic-control cohort (2026-11-12)" below. The
2026-11-08 text that follows records the state before that run and stays as
history.

Status (2026-11-08): deterministic HAR cohort **infeasible**; native cohort
**not run** (pending); library ablation (arm D) **not run**. The deterministic
controls were executed. No HAR cohort was run and this report contained no HAR
outcome numbers. SPEC-049/T005 stays open. The original determination was made
at `ab2db0c45ab70c3689e39226897a5ddf2932126a` (2026-10-29,
[evidence/t005.json](evidence/t005.json)); the 2026-11-08 re-check is in
[evidence/evaluation/deterministic-controls-20261108.json](evidence/evaluation/deterministic-controls-20261108.json).

## Deterministic synthetic-control cohort (2026-11-12)

Owner answers of 2026-11-12 to the
[decision packet](t005-unblock-packet-20261112.md) are recorded as paraphrased chat
answers in
[evidence/registration/t005-owner-decisions-20261112.json](evidence/registration/t005-owner-decisions-20261112.json):
construct Units for the six lineage-assigned cases (R11), leave L3-C02-a
unassigned (R3), take arm C as keep-base labelled a plumbing control (R8), and
authorize exactly one offline run with the R13 double as solver. The units, rubric,
oracles and the keep-base round are frozen before the run in
[evidence/registration/t005-units-freeze-20261112.json](evidence/registration/t005-units-freeze-20261112.json).
The run and its recomputable results are in
[evidence/evaluation/deterministic-cohort-20261112.json](evidence/evaluation/deterministic-cohort-20261112.json)
(`python3.13 -m tests.harness_t005_cohort`; code in `tests/harness_t005_cohort.py`,
tests in `tests/test_harness_t005_cohort.py`).

What it is. Five L1 holdout cases times arms A, B and C, graded by each unit's
`FixtureOracle`. Arm C is arm A by construction (keep-base round, one base probe of
the double on discovery unit L2-C01-a). The solver is the R13 double, which encodes
its own effect, and the oracles come from the same owned scenarios, so they are
not independent of it. Rows are labelled `synthetic-control` and are excluded from
every D4 verdict.

Correct completions per registered unit (one lineage, so no stratum is assessable):

| Stratum | Units | A | B | C (= A) |
|---|---|---|---|---|
| continuity | 1 | 0/1 | 1/1 | 0/1 |
| coordination | 4 | 3/4 | 3/4 | 3/4 |

In coordination, B has one `not-completed` cell: L1-C02-a, where the double's
stop-on-drift switch interrupts by design. The evaluation convention counts an
interrupted attempt as not-completed, so that cell reads as a B shortfall although
it is the designed behaviour; A completes it only because the double ignores drift.
B versus A is 1 comparator-only, 1 base-only and 2 both-correct pairs in
coordination, and 1 comparator-only pair in continuity. Every comparison reports
`descriptive-only` (`below-D3-minimum`, plus `repeated-within-lineage` in
coordination) with no verdict.

What it shows. Registration, observation, commitment, grading, denominators and
interval reporting connect end to end on frozen units. What it does not show: that
any guidance helps, any refinement effect (C = A), any library effect (arm D not
run), false safe admissions, missed safe parallelism, correction and review effort,
or any cost (every measure is unknown, no reservations exist, so cost claims are
blocked). The one discovery probe is outside the T012 ledger. No host, model,
native session, paid route or human annotation was used.

Still open for T005: the native cohort (SPEC-049/T004 and SPEC-048/T008), the
library ablation, and whether the task may be closed on a deterministic-only
disposition; that last question is for the owner and is not decided here.

## State at 2026-11-08

Since the first determination the founder froze the case roster and the arm A
and B identities ([case-roster.md](case-roster.md), decision record dated
2026-10-30) and the guidance-observable synthetic-control double (R13) was
implemented. That settles the roster and the A and B identities (blockers 2 and 3 below) but not the executable cases (blocker 1) or arm C (blocker 4).
Still blocking the deterministic cohort:

- **Arm C** is deferred (R8, option a). Without a real proposer,
  `harness_evaluation.register` cannot bind a chosen arm-C candidate. The only
  deterministic route (keep-base) makes C equal to A and carries no information.
- **Units (R11)** are authorized but not built: no `harness_verification.Unit`
  (input, frozen rubric, oracle, hash) exists for any of the 7 roster cases.
- **R3**: L3-C02-a stays unassigned.
- **Partition**: the fallback holdout is the single lineage L1, so any cohort
  would be `descriptive-only` under D3.
- **Library ablation (arm D)** needs arm C, so T006 being done does not make it
  runnable.

Controls actually executed (all pass): frozen roster, draft and arm A/B
candidate hashes re-verified; every R13 record hash recomputed and equal to its
recorded value; `register` refuses an empty or `synthetic-control` registration
with `invalid-registration`; 64 module tests and 1316 harness tests pass.

### Engineering control: synthetic-control A versus B (not the T005 paired outcome)

The R13 double reads the arm-B guidance bytes and switches two behaviours by a
frozen mapping. Rows below are recomputed from it. They are labelled
`synthetic-control`, are verdict-ineligible and are excluded from every D4
verdict. The double encodes the behaviour it reports, so they do not show that
any guidance helps. "Interrupted" for B is the designed stop-on-drift switch on
a drift case, not a failure and not a win.

| Stratum | Case | Steps executed A / B | Steps repeated A / B | Terminal A / B |
|---|---|---|---|---|
| continuity | L1-C01-a | 4 / 2 | 2 / 0 | completed / completed |
| continuity | L2-C01-a | 3 / 0 | 1 / 0 | completed / interrupted |
| coordination | L1-C02-a | 2 / 0 | 0 / 0 | completed / interrupted |
| coordination | L1-C03-a | 2 / 2 | 0 / 0 | completed / completed |
| coordination | L1-C03-b | 3 / 3 | 0 / 0 | completed / completed |
| coordination | L1-C03-c | 2 / 1 | 1 / 0 | completed / completed |

A completes the drift cases L2-C01-a and L1-C02-a only because the double
ignores drift by construction. Four of six cases differ, exactly the four the
frozen mapping predicts. This shows only that the double responds to the arm-B
bytes and that A and B are distinguishable under that mapping; it says nothing
about any real solver. The
double has no false-safe-admission, missed-parallelism or review-effort notion,
so those T005 items are not computed. No cost was incurred (additional cash
EUR 0, no attempts to reconcile). `evaluation-protocol.md` changed after R13
pinned it (D2 caps added); the R13 record hashes still recompute unchanged.

This report takes the "infeasible" path that the
[frozen protocol](evaluation-protocol.md) sets in advance (D6). D3 separately
says to record a feasibility result if native yield stays unknown, which is true
of the native cohort below. It is not an unsupported, inconclusive or negative result about the method. It
says only that the registered material cannot support an evaluation yet.

## Why the deterministic cohort could not run at 2026-10-29

These are the four facts recorded then; the section above gives the current state. Each is checked against the pinned inputs listed in the
evidence record:

1. **There are no executable case definitions.** [source-registration.md](source-registration.md)
   records 0 executable HAR case definitions and 0 registered or evaluated
   comparison units. The "up to 16" case definitions were only proposed and were
   never constructed.
2. **No case roster is frozen.** The T002 founder freeze
   ([decision record](evidence/registration/t002-founder-freeze-20261028.json))
   fixed the D1–D6 rules (summarized in D7). It froze no case roster and assigned no case to
   discovery or holdout. Source registration requires that roster before any
   outcome is evaluated. Calling `harness_evaluation.register` with no units
   refuses with `invalid-registration`.
3. **The A/B/C arms have no frozen identities.** No candidate hashes and no
   matched profile hash are registered for A (static base), B
   (checkpoint/context guidance) or C (contrastive refinement).
4. **Arm C has no real proposer.** Arm C must be the candidate that a
   `harness_refinement` round selects, or the base that round explicitly keeps.
   Today the only proposers are injected test doubles, so no real arm-C candidate
   exists.

Engineering note (superseded for the synthetic domain by the R13 double above;
the point about real solvers still holds for real cohorts): the arms differ only in guidance text. The existing fixtures
for the offline runner (`harness_lab`, simulated containment) are fixed scripts
that do not read guidance. Without a model solver, A, B and C would give
identical fixture outcomes by construction. Writing arm-specific behavior into
fixtures would invent the effect being measured. Neither kind of output is a
result, and neither was produced. A meaningful comparison of guidance variants
therefore also needs a solver that reads guidance, and that means the native
branch (T004/T008).

Arm D (A–C plus scoped earlier experience) depends on the same roster and arm C.
It is therefore also infeasible. The T006 store being available does not change
that.

## Endpoints

None of the protocol's endpoints ("Outcomes and denominators") or of T005's
reporting items was computed. Each is infeasible for the deterministic cohort and
pending for the native cohort:

| Axis | Endpoint | Status |
|---|---|---|
| Continuity | Correct completion / registered and started units; correct interrupted recoveries; duplicate effects; repeated work; interventions; rework scope; checkpoint/handoff correctness | not computed |
| Coordination | Conflict precision/recall per class; false safe admissions; verified safe admissions and verification coverage; useful parallelism recovered; unnecessary serialization; serial-oracle agreement | not computed |
| Shared | Unknown/refused/failed/interrupted/ungraded counts; label/class coverage; task quality; declared/observed effect violations; complete costs and per-profile limits | not computed |
| T005 reporting | Paired per-stratum outcomes; correction/review effort; sensitivity to missing outcomes | not computed |

No host, model, paid route or native session was used. The T012 reconciliation therefore has no
attempts to reconcile.

## Native cohort

Pending. It is blocked on SPEC-049/T004 (native admission) and SPEC-048/T008
(qualified host). There is no native source, session or outcome, and none is
substituted with synthetic data.

## What would unblock the deterministic cohort (as of 2026-10-29)

The founder must supply, in a decision record made before any outcome. Since then the roster and the A/B identities were frozen; constructed units and arm C were not:

1. **A frozen case roster (now frozen; constructed units are still missing).** Constructed case definitions drawn from the
   registered lineages L1–L4 ([corpus.md](corpus.md)). Each case needs its
   lineage, task family, stratum, holdout partition, rubric and deterministic
   oracle. The roster must follow D1: L1 is never split, L3 stays unassigned
   until resolved, and L4 is held out only if a derived task qualifies.
2. **A/B/C arm identities.** Exact candidate hashes for A, B and C and the matched
   profile hash. Arm C must come from a recorded refinement round with a real
   proposer, either a selected candidate or an explicit keep-base.

Even with both, the D3 rule still applies. At most 4 independent lineages exist,
so a deterministic cohort stays descriptive only.

## Limits

This is offline inspection, refusal checks and a re-run of the R13 synthetic-control
double only. It uses no host, model, native session, paid route or human
annotation, and it runs no HAR unit. Results hold only for the synthetic domain. Numbers were recomputed with an
uncommitted scratch script from the committed double. One earlier run of the
1316 harness tests in this session showed a single error that did not
reproduce on two reruns; its cause was not investigated. It makes no inferential,
economic or promotion claim and does not authorize execution or promotion. The
pre-PR reviews were run by Claude subagents and are not independent Luna review.
