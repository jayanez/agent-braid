# SPEC-083: Capability versus regression evaluation protocol

**Milestone:** HAR.4 — Harness evaluation platform. Implements owner decision F3 of
the [harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (2026-11-22).

**Status:** draft. Documentation only; nothing is implemented, registered or run by
this specification's first PR. `executionAuthorization` is false throughout.

## Purpose and scope

SPEC-049 T014 ran 15 native units on one lineage and was inconclusive under D3, and
the protocol has no gate that says a candidate is "no worse" than the current one.
This spec amends the frozen
[SPEC-049 evaluation protocol](../049-harness-evaluation-learning/evaluation-protocol.md)
by reference with two evaluation classes; it rewrites no frozen value.

- **Capability evals** ask what a candidate can do (pass@k). Descriptive; never a gate.
- **Regression evals** gate promotion: paired non-inferiority against a baseline on
  the [SPEC-082](../082-harness-task-qa-infra-controls/spec.md) task corpus.

In scope: pre-registration record, estimand, uncertainty method, decision rule,
pass@k and pass^k, infrastructure errors, missing outcomes, minimum sample, a power
note and stopping rules.

Actors: the owner, who reviews (REQ-001), seals registrations (T009), records
suspected leaks and refreshes the split (REQ-004) and acknowledges regression
summaries (REQ-006); SPEC-084 or the existing laboratory, which run the trials under
their own admission (T010); and SPEC-085, which reads verdicts for a promotion
decision (REQ-002, REQ-006).
No end user interacts with these records.

Scope limits: this spec promotes, activates, grants and launches nothing. A verdict
is evidence for a human decision (SPEC-085), not authority (`assurance.json`
`execution_contract`).

Exclusions, each covered by the requirement named:

- A frozen SPEC-049 value (D1–D7) or the SPEC-049 T002 freeze record MUST NOT change
  (REQ-002; SC-002 hashes the protocol's frozen sections).
- A capability result or a regression verdict MUST NOT be presented as a utility or
  superiority claim; D3 and the SPEC-049 axes still govern those (REQ-002, REQ-007,
  REQ-012).
- A verdict MUST NOT come from Harbor's default mean metric (REQ-005 and REQ-006
  define the only estimand and decision rule).
- Held-out outcomes MUST NOT reach any optimizer (SPEC-049 REQ-009).
- An interim analysis or optional stopping MUST NOT occur (REQ-011).
- A margin MUST NOT be chosen or changed after any outcome of the comparison is seen
  (REQ-003 fixes it before the first trial; OD-1 fixes δ = 0.10).

## Requirements and acceptance scenarios

**REQ-001 Owner review.** The owner reviews this spec and plan before implementation.

- **SC-001:** Given this spec and plan, when the owner reviews them, then OD-1 to
  OD-6 are decided or deferred in a dated record and the spec is accepted, amended
  or rejected.

**REQ-002 Two classes, amendment by reference.** Every report names its class
(`capability` or `regression`). Only a regression verdict can support a move to
`candidate` or `adopted` (SPEC-085). SPEC-049 frozen text and values stay as they are.

- **SC-002:** Given a capability report and the SPEC-049 protocol, when a promotion
  check reads them, then it refuses with "no regression verdict"; the hashes of the
  protocol's frozen sections are unchanged, and the dated cross-reference line of T008
  is the only change to the whole file, with its expected hash recorded.

**REQ-003 Sealed pre-registration.** A regression record fixes, before the first
trial starts: baseline and candidate hashes, the SPEC-082 corpus manifest hash and
split, the task list hash, trials per task, margin δ, α, estimand, uncertainty
method, cluster level, the sensitivity methods with their resample count and seed,
the confirmation-trial rule (REQ-006), missing-outcome rule, infrastructure-error threshold and rerun limit, the pinned
profile, stopping rules and the reported k values. Its
SHA-256 seals it. Any later change needs a new record.

- **SC-003:** Given records with a missing field, a seal time after the first trial
  start, or a field changed after sealing, when validated, then each is refused with
  the failing field named.

**REQ-004 Paired design on a held-out split.** Baseline and candidate run the same
tasks with the same trial count (at least 5 per task per arm), the same pinned
model, effort, resources and host, and fresh run ids (SPEC-082). Gate tasks come from
the SPEC-082 private held-out split. Executed trials that differ from the registration
(one arm only, unequal counts between arms) make the comparison `invalid`; a
registration that plans fewer trials or tasks than REQ-010 requires is
`descriptive-only` instead (REQ-010). Each gate use is counted in an append-only use
ledger bound to the split's manifest hash and kept with the private split (SPEC-082
REQ-005). A use is counted when a registration is sealed against the split, whether
its run completes, stops or is invalid. Sealing refuses once the ledger shows 5 uses
or a recorded suspected leak, until a refreshed split with a new manifest hash is
recorded (OD-5). The owner records suspected leaks and refreshes.

- **SC-004:** Given trials where a task ran in one arm only, a profile differs
  between arms, a run id repeats, or a task is outside the held-out split, when
  paired, then the comparison is marked `invalid` with the cause; a sixth
  registration against one split, or one after a recorded suspected leak, refuses
  to seal.

**REQ-005 Estimand and clustered uncertainty.** Δ = mean over tasks of (candidate
success rate − baseline success rate). The primary bound is the one-sided (1 − α)
lower bound from the task-clustered standard error, t distribution on T − 1 degrees
of freedom. Trial-level standard errors are never used. The standard error used is
the larger of the task-clustered error and a binomial floor,
(1/T)·√Σᵢ[p̃ᶜᵢ(1 − p̃ᶜᵢ)/nᶜᵢ + p̃ᵇᵢ(1 − p̃ᵇᵢ)/nᵇᵢ], with Jeffreys-smoothed rates
p̃ = (c + ½)/(n + 1), so that a sample with no observed spread is not read as
certainty (owner, 2026-11-24). Two sensitivity checks, sealed in the registration:
(1) a clustered bootstrap that resamples tasks with replacement, 10 000 resamples
from a PCG64 generator with the sealed seed, percentile one-sided bound; (2) lineage
clustering, which averages task differences within each SPEC-082 lineage and takes
a t bound on L − 1 degrees of freedom over the equally weighted lineage means. Each
check gets its own verdict under REQ-006. A check whose verdict differs from the
primary in any way, or that cannot be computed (fewer than 2 lineages), makes the
verdict `inconclusive` (OD-3; owner, 2026-11-24).

- **SC-005:** Given a fixture with hand-computed Δ and bound, and a control where
  trial-level errors would pass but clustered errors do not, when computed, then
  the values match within 10⁻⁶ and the control is not `noninferior`; a 20-task tie
  at 5/5 in both arms gets the floor bound (about −0.07), and a fixture where one
  sensitivity verdict is `inconclusive` while the primary is `noninferior` is
  `inconclusive`.

**REQ-006 Decision rule.** `noninferior` if the lower bound > −δ; `inferior` if the
one-sided (1 − α) upper bound < −δ; otherwise `inconclusive`. `invalid` covers
protocol breaks (REQ-004, REQ-008). A declared-effect, authority or containment
violation is `blocked` whatever the statistic. Clause zero: `inconclusive` is a
valid result, and it blocks promotion like `inferior`, `invalid` and `blocked`. Every
regression verdict carries a per-task regression summary with two grades: hard
regressions (baseline pass^n = 1 and candidate pass@n = 0, OD-6) and soft regressions
(candidate success rate at least 0.4 below the baseline's on that task). Each task
appears by id when public or by salted commitment when private (SPEC-082 REQ-005).
With 5 trials soft regressions also appear by chance (in 65 to 98 % of 20-task
comparisons with no real change), so the registration pre-registers confirmation
trials: every flagged task, up to 5 in order of largest drop, gets 10 more trials per
arm with fresh run ids, inside the same registration and ledger use. A flag stands
when the drop on all 15 trials is still at least 0.4. Confirmation results are
reported apart and never change the verdict; above 5 flagged tasks the summary says
so. A SPEC-085 move to `candidate` needs the owner's acknowledgement, which cites the
verdict hash and the summary hash. The summary does not block on its own; OD-6 is
unchanged (owner, 2026-11-24).

- **SC-006:** Given one fixture per region (noninferior, inferior, inconclusive,
  invalid, blocked), when decided, then each gets its verdict and only
  `noninferior` is marked promotion-eligible; a `noninferior` fixture with one
  regressed task carries that task in its summary, a soft flag that does not hold on
  its 15 confirmation trials is reported as not confirmed, the verdict is the same
  with and without confirmation trials, and a move to `candidate` without an
  acknowledgement citing the current verdict and summary hashes refuses.

**REQ-007 pass@k and pass^k.** Per task and arm, with n trials and c successes,
report pass@k = 1 − C(n−c, k)/C(n, k) (capability) and pass^k = C(c, k)/C(n, k)
(reliability) for each registered k ≤ n, then their task means with clustered
intervals. Both classes report them; neither is a verdict.

- **SC-007:** Given per-task counts with known values, when reported, then pass@k
  and pass^k match the formulas and a k greater than n is refused, not extrapolated.

**REQ-008 Infrastructure errors.** Trials that SPEC-082 classifies as infrastructure
errors count as neither success nor failure and are reported per arm. They may be
rerun with a fresh run id up to the registered limit; a task's rate uses its valid
trials. Accounting follows SPEC-082 REQ-009: the unit is the registered trial, which
is an infrastructure error only when every attempt is, and a rate is the number of
infrastructure-error trials over registered trials per arm. A per-arm rate or between-arm
difference above the threshold is `invalid`, and so is any task with no valid trial
in either arm, whatever the rates.

- **SC-008:** Given trials with infrastructure errors below and above the
  threshold, when analyzed, then none counts as a failure, all appear in the
  infrastructure table, and the over-threshold case is `invalid`; a task that loses
  all five trials in one arm makes the comparison `invalid` even at a 5 % arm rate.

**REQ-009 Missing outcomes.** In the primary analysis a missing non-infrastructure
outcome (ungraded, not attempted, interrupted) is a candidate failure and a baseline
success. The report adds complete-case and best-case bounds and says if they differ.

- **SC-009:** Given a fixture with missing candidate outcomes, when decided, then
  the primary verdict uses the worst case and the three bounds are reported.

**REQ-010 Minimum sample and power note.** A verdict needs T ≥ 20 informative tasks
from the private held-out split and 5 registered trials per task per arm. A task is
informative when the baseline succeeds in at least one trial; with the baseline at
0/n a candidate cannot show a regression on it (owner, 2026-11-24). Each record
states its power assumption (between-task spread of differences, δ, α, T). Below the
minimum it is descriptive. The first SPEC-082 corpus is expected to give 4 to 10
private tasks (SPEC-082 REQ-013), so verdicts are deferred and reports are
`descriptive-only` until that split reaches 20.

- **SC-010:** Given 19 informative tasks, 20 tasks with 4 registered trials on one,
  or 20 tasks with the baseline at 0/5 on all of them, when analyzed, then no verdict
  is issued and the report says `descriptive-only`.

**REQ-011 Stopping rules.** The verdict is computed once, after all registered
trials end or a registered stop fires (SPEC-049 D6 conditions, quota caps,
infrastructure threshold). A stopped run is `inconclusive` or `invalid` and stays
on record; a rerun is a new registration.

- **SC-011:** Given a request to compute a verdict before all trials end, and a run
  stopped by a quota cap, when processed, then the first is refused and the second
  is recorded `inconclusive` with the stop cause.

**REQ-012 Claim boundary.** A `noninferior` verdict reads "no worse than the
baseline by more than δ on this corpus, split and profile". Utility or superiority
claims keep the D3 lineage minimum.

- **SC-012:** Given a `noninferior` verdict on fewer than the D3 number of
  independent lineages, when a superiority claim is drafted from it, then the check
  refuses it and the report shows the bounded claim text.

## Owner decisions

The owner decided OD-1 to OD-6 on 2026-11-23 (T001). The chosen answers are in the
[owner review record](evidence/t001-owner-review.md); the options offered are in
this file as merged in #1515 (`f0793dfd`). On 2026-11-24 (T002) the
owner chose the rules for S83-001, S83-002 and S83-005; they are now part of
requirements REQ-005, REQ-006 and REQ-010. On 2026-11-25 the owner settled the points in the
[refinement record](evidence/owner-decisions-20261125.md). A confirmed finding may
reopen a decision through a dated amendment.

- **OD-1 Margin and α.** δ = 0.10 and one-sided α = 0.05, fixed before the first
  registration record.
- **OD-2 Primary uncertainty method.** Analytic task-clustered error as primary;
  clustered bootstrap as a sensitivity check.
- **OD-3 Cluster level.** Task as primary; SPEC-082 lineage as a sensitivity check. A
  sensitivity verdict that differs from the primary makes the verdict `inconclusive`.
- **OD-4 Infrastructure thresholds.** At most 10 % of trials per arm, at most 5
  points between arms, at most 2 reruns per trial, as SPEC-082 OD-5.
- **OD-5 Held-out reuse.** Every gate use is logged. The private split is refreshed
  after 5 gate uses or any suspected leak.
- **OD-6 Per-task regressions.** A task with baseline pass^n = 1 and candidate
  pass@n = 0 is reported in the verdict. In v0.1 it does not block on its own.

## Open questions

- Does the founder approve the dated SPEC-049 cross-reference line (T008)? Owner:
  founder.

## Non-functional requirements

No performance or availability requirement applies: this spec defines a protocol and
its records. Determinism: the bootstrap seed and its 10 000 resamples are sealed
(REQ-003, REQ-005), and fixtures match hand values within 10⁻⁶ (SC-005).

## Security and privacy

- A private task appears in a regression summary only by salted commitment: see
  REQ-006 and SPEC-082 REQ-005.
- The use ledger stays with the private split: see REQ-004.
- Held-out outcomes do not reach an optimizer: see SPEC-049 REQ-009.

## Terminology

Shared terms follow `TERMINOLOGY.md`. Glossary of terms this spec introduces:

- Capability eval: a descriptive report of what a candidate can do (pass@k); never a
  gate (REQ-002).
- Regression eval: a paired non-inferiority comparison against a baseline that gates
  promotion (REQ-002).
- Registration: the sealed record that fixes a regression comparison before its
  first trial (REQ-003).
- Informative task: a task on which the baseline succeeds in at least one trial
  (REQ-010).
- Hard regression: baseline pass^n = 1 and candidate pass@n = 0 on a task (REQ-006).
- Soft regression: candidate success rate at least 0.4 below the baseline's on a task
  (REQ-006).
- Gate use: one registration sealed against a private split (REQ-004).
- pass@k and pass^k: per-task capability and reliability measures over k of n trials
  (REQ-007).

Values named in this spec:

- Class: `capability`, `regression`.
- Verdict: `noninferior`, `inferior`, `inconclusive`, `invalid`, `blocked`.
- Report without a verdict: `descriptive-only` (REQ-010).
- Trial outcome: success, failure, infrastructure error, missing (REQ-008, REQ-009).
- Missing outcome: ungraded, not attempted, interrupted (REQ-009).
- Missing-outcome bound: primary (worst case), complete-case, best-case (REQ-009).
- Cluster level: task (primary), lineage (sensitivity) (REQ-005).
- Regression grade: hard, soft; a soft flag is confirmed or not confirmed (REQ-006).
- Stop cause: SPEC-049 D6 condition, quota cap, infrastructure threshold (REQ-011).
- SPEC-085 labels read here: `candidate`, `adopted` (REQ-002).

## Non-goals

Choosing candidates; running trials (SPEC-084); moving labels (SPEC-085); building
the corpus (SPEC-082); telemetry (SPEC-086); automatic promotion (SPEC-049 T008 stays
deferred); reanalysing T014.

## Risks

- Risk: low power. With T = 30 and an assumed between-task standard deviation of
  differences of 0.3, a true Δ = 0 passes δ = 0.10 about 57 % of the time and
  δ = 0.15 about 86 % (normal approximation; an assumption, not data) (REQ-010).
- Risk: tasks from one lineage are not independent (REQ-005, OD-3).
- Risk: repeated gating on one split overfits to it (REQ-004, OD-5).
- Risk: the first corpus is below the 20-task minimum, so verdicts wait for later
  lineage batches (REQ-010, SPEC-082 REQ-013).
- Risk: provider models drift between arms; arms are interleaved and pinned (pinning:
  REQ-004).

## Assumptions

- Assumption: SPEC-049's frozen protocol (D1–D7) stays unchanged and is amended by
  reference only (REQ-002).
- Assumption: SPEC-082 supplies a corpus of 20–50 real-failure tasks with lineage, a
  private held-out split and an infrastructure-error classification (REQ-004,
  REQ-005, REQ-008, REQ-010).
- Assumption: trials are run by SPEC-084 or the existing laboratory under their own
  admission; this spec runs none (T010).
- Assumption: the power note takes a between-task standard deviation of paired
  differences of 0.3; no data estimates it yet (REQ-010).

Hypotheses. H1: on 20–50 tasks with 5 trials the gate is decisive for most
candidates. H2: clustered intervals are wider than trial-level ones on real data.
Either can fail; a failure is a result.

## Exit criteria

Verification is complete when each of procedure_001 to procedure_012 in the
[validation plan](validation-plan.md) has obtained evidence recorded against its task
in [tasks.md](tasks.md), and T010 has recorded the first regression verdict
(`noninferior`, `inferior`, `inconclusive`, `invalid` or `blocked`). A
`descriptive-only` report is not a verdict and does not close T010 (REQ-010).

## Dependencies

[SPEC-049](../049-harness-evaluation-learning/spec.md) (D3, D4, D6, REQ-009) and
[SPEC-082](../082-harness-task-qa-infra-controls/spec.md) (corpus, held-out split,
infrastructure classification). Consumed by [SPEC-084](../084-harbor-evaluation-substrate/spec.md)
and [SPEC-085](../085-harness-promotion-pointers/spec.md). No ADR of its own.

## References

- [Harnessing benchmark (2026-11)](../../docs/strategy/HARNESSING_BENCHMARK.md), F3
- [ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md) (Proposed)
- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md),
  [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md)
- External, as cited in the benchmark:
  [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents),
  [Inspect metrics](https://inspect.aisi.org.uk/metrics.html),
  [Terminal-Bench 2.0](https://arxiv.org/html/2601.11868v1),
  [infrastructure noise](https://www.anthropic.com/research/infrastructure-noise)
