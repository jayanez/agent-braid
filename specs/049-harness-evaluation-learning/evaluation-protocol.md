# Prospective two-axis evaluation protocol

Status: registration design, not a frozen empirical protocol or experiment result.
T002 must freeze the exact candidate/source roster, numeric budget, sample size,
quality/effect gates, noninferiority margins and analysis before evaluated outcomes.
T004 additionally admits each native cohort. No calibration/training is required.

## Questions and comparators

Co-primary questions: does the method improve correct long-task completion and
recovery with fewer interventions/rework; and does it improve conflict decisions
and useful parallelism at preserved correctness and authority constraints?

Compare A: unchanged base harness; B: simple fixed checkpoint/context guidance;
C: bounded contrastive refinement without experience; D: C plus scoped earlier
experience, only after the experience implementation exists. Keep requested
model/effort/host/tool/source and observable provider route matched. Counterbalance
order within registered task families; uncontrolled hidden provider drift limits
interpretation. Report complete-cost and matched-budget comparisons separately.
All additional D experience-generation costs belong to the comparison boundary.

## Sampling, leakage and labeling

Use [corpus.md](corpus.md). Register actual native source yield/rights before
selecting sample size. Group by task family and source lineage so derivative
fixtures do not cross discovery/holdout. Fix strata and counts from eligible yield;
report sparse classes and do not claim representative precision from a small
convenience pilot. Keep synthetic/native and host/profile strata separate.

Freeze outcome rubric, independent oracle/human distinction and annotation
instructions independently of method rankings. Attempt annotation of the entire
holdout, including failures and refusals. Record blind reviewer identities,
agreement/adjudication and unresolved/missing labels. Define any proxy as a proxy,
not actual correctness or user time saved. Ground-truth test/benchmark answers and
hidden evaluation cases must remain outside improver/solver context and network
access. Visible task acceptance requirements remain available as normal work input.

Evaluate online experience using earlier-task prefixes only. Freeze order and
library starting state; retain independent clean libraries per comparator/cohort.
Cross-task/domain retrospective transfer is separately labeled, never online
evidence. Do not tune margins, abstention or candidate policies on holdout outcomes.

## Outcomes and denominators

| Axis | Required measurements |
|---|---|
| Long-task continuity | Correct completed tasks / all registered and all started units; correct interrupted recoveries / eligible interrupted units; duplicate effects; repeated completed work; intervention count and minutes; rework scope; checkpoint/handoff correctness |
| Coordination | Conflict detection precision TP/(TP+FP) and recall TP/(TP+FN), per known conflict class; false safe admissions; verified safe admissions / all admitted proposals and verification coverage; useful parallel work recovered / eligible independent work; unnecessary serialization; outcome agreement with the independent serial/effect oracle |
| Shared | Unknown/refused/failed/interrupted/ungraded counts; label/class coverage; task quality; declared/observed effect violations; complete costs and per-profile limitations |

Define TP/FP/FN from the frozen corpus label construct. Unknown labels never enter
the verified-safe numerator; show lower/upper bounds or missingness sensitivity
when they affect conclusions. Zero-denominator precision/recall is undefined, not
100%. Report sample counts and uncertainty; choose inferential methods only after
registered yield justifies them. Pilot descriptive findings cannot certify a
universal error rate.

Mandatory approvals/checkpoints are counted separately from corrective human
interventions. Count human review and annotation effort in costs even when they
are excluded from the intervention endpoint. Fewer interruptions achieved by
skipping necessary review are not a benefit.

## Constraints, cost and decision rule

Correctness, declared-effects and authority controls are hard eligibility gates.
Any unsafe admission or authority violation invalidates promotion of that profile
and triggers review; throughput cannot compensate. Freeze numerical quality
noninferiority and useful-improvement margins before outcomes. Report both axes
and their tradeoffs; a mixed result supports a narrower profile or no-go, never
an unqualified whole-product promotion via a weighted average.

A whole-program positive-utility claim requires both axes to meet their registered
criteria. A useful result on one axis can support a specifically bounded profile
while the other remains unsupported or pending; the report must say so directly.

Capture setup, context acquisition/materialization, all proposals/probes/retries,
selection, reflection/library retrieval, verification, journal/recovery, human
review and cleanup. Report cash, subscription quota/tokens when observable,
latency, CPU/RSS/disk/process occupancy and human time separately. Reconcile all
started units, including failures. Unknown cash remains unknown and blocks a
positive economic acceptance claim. Existing subscriptions are not zero-cost
resources. Additional cash spend is operationally capped at EUR 0; no paid API,
overage, credit purchase, auto-recharge or alternate paid fallback is admitted.

Stop on lost containment, stale/lost route or quota observation, drift, resource
exhaustion or invariant violation. Record stop/cleanup effects and open attempts.
Predetermine infeasible/negative/inconclusive report paths; none requires fabricating
native results or weakening the original population after seeing outcomes.

## Promotion and review

Human promotion binds exact variant, effect domain, source/host/tool versions,
evidence and rollback. Automatic promotion stays disabled pending a separate
adopted policy and native eligibility evidence where native behavior is claimed.
Synthetic controls may exercise policy and rollback mechanics. A future low-risk
class must have independent checks, change limits, canary/rollback, revocation and
incident stops; model self-assessment cannot be its only acceptance signal.

Publish per-axis/per-cohort verdicts supported/unsupported/inconclusive/infeasible,
source limits and full costs. Independent Luna review when authorized and human/
founder acceptance remain separate from protocol completion and software tests.

## Draft for founder freeze (T002) — not frozen

Status: DRAFT PROPOSAL ONLY. Nothing in this section is frozen, decided, approved
or binding. `049/T002` remains pending; it needs an actual founder decision record
before any evaluated native outcome. Every value below is a proposal to be
accepted, changed or rejected, derived from the registered yield in
[corpus.md](corpus.md) and [source-registration.md](source-registration.md).

### D1. Task-family split and temporal library order

- Split by lineage group, not by family name. Registered groups: L1 (S01/S06,
  covering C01, C02, C03), L2 (S02, C01), L3 (S03, C02, relation to L1 unresolved)
  and L4 (S04/S05, C04). Proposal: L4 as the held-out family only if a derived task
  qualifies; otherwise hold out whole lineages. L1 is never split.
- Unresolved lineage (L3) stays unassigned until resolved; it is not used to
  inflate either partition.
- Temporal order for arm D: a fixed case sequence set once, ordered by lineage
  construction order, libraries starting empty and independent per comparator and
  cohort; a task sees only strictly earlier eligible entries. Order for A/B/C is
  counterbalanced within family using a fixed Latin-square rotation recorded
  before any outcome.

### D2. Matched safety, coverage and budgets

- Match requested model, effort, host, tools, source state and observable route
  across A–D. Hard gates (declared effects, authority, containment) are identical
  for all arms; any violation excludes that profile from promotion.
- Coverage: a profile is compared only on the same registered unit set; refusals,
  failures and ungraded units stay in the denominator.
- Budget (proposal): additional cash EUR 0 (already operational); a per-unit
  wall-time and token/quota cap and a total unit cap are to be set by the founder
  from an observed native quota reading. No numeric time or token cap is proposed
  here because no native quota observation exists.

### D3. Sample size derived from registered yield

- Observed independent lineages: 4 (3 if L3 merges into L1). Observed native
  yield: 0.
- Reference calculation for a paired, zero-discordance noninferiority claim at one
  sided 5% on an exact binomial bound: need n >= ln(0.05)/ln(1 - delta). For
  delta = 0.20, n >= 14; delta = 0.15, n >= 19; delta = 0.10, n >= 29 independent
  paired units per axis and stratum. (Arithmetic: ln 0.05 = -2.996; ln 0.80 =
  -0.223, ln 0.85 = -0.163, ln 0.90 = -0.105.)
- With at most 4 independent lineages the smallest requirement (14) is not met.
  Proposal: the current cohort is DESCRIPTIVE ONLY. Up to 16 constructed case
  definitions add repeated measurements within lineage, not independent units.
  Inferential noninferiority needs new disjoint lineages or permissioned native
  sources first; if native yield stays unknown, record a feasibility result.

### D4. Noninferiority and improvement margins (proposal)

- Correctness and recovery: noninferiority margin delta = 0.15 absolute on correct
  completion proportion, assessed only when n meets D3; otherwise report
  counts and the exact interval without a verdict.
- Coordination: false safe admissions must be 0 in every evaluated unit (hard
  gate, no margin); precision/recall margin delta = 0.10 each per known conflict
  class, undefined (not 100%) when a denominator is zero.
- Useful-improvement thresholds (interventions, rework, parallelism recovered) are
  left for the founder; none is proposed without a measured baseline.
- Margins must not be tuned on holdout outcomes.

### D5. Annotation rules

- Rubric and oracle/human/proxy distinctions frozen before any ranking; hidden
  grader material outside the improver/solver context.
- At least two blind annotators per held-out unit when human labels are used;
  disagreement resolved by an actual adjudication record, never an invented
  consensus; missing labels counted and bounded by sensitivity analysis.
- Deterministic oracles (serial/effect reference) are labeled as oracles, human
  rubric scores as human, model scores as proxies.

### D6. Stop conditions

Stop and record on lost containment, stale or lost route/quota observation,
source/policy drift, resource exhaustion, invariant or authority violation,
discovery of lineage leakage, or any need for extra cash. Open attempts and
cleanup effects are retained. Predetermined report paths: supported, unsupported,
inconclusive, infeasible; none requires fabricating native results.

### D7. Founder decisions requested

Accept or amend: lineage-based split and L4 holdout; counterbalancing method;
margins in D4 and the n >= 14/19/29 table; annotator count; numeric time/quota
caps after an observed quota reading; whether the cohort stays descriptive.
