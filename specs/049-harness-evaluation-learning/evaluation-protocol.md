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
