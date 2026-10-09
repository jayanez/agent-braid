# SPEC-019 prospective workload protocol candidate

**Decision:** On 2026-09-27 the founder chose prioritization of useful
exchanges in real workloads as the M3.5 target. This records the target
direction, not approval of this detailed protocol, a dataset or model results.

## Founder-selected amendments pending independent review — 2026-10-09

The founder selected these rules for the next protocol revision:

- Cut off after the second proposal in a validated total event sequence. A
  resolution event at or before that cutoff excludes the pair. A hash fallback
  may orient a pair deterministically but never establishes chronology or
  source eligibility.
- Group exact normalized unordered pairs and keep records from the same
  session/lineage together. Do not group unrelated pairs solely because they
  share a base. Detailed canonicalization remains for scientific review.
- Keep `keep-order` eligible for verifier work. The primary comparison is the
  fixed-budget assessed-useful `verified-bounded` count at the 50% ceiling,
  with lower and upper bounds for unknown labels.
- One unordered pair consumes one budget unit: one submitted `produce`, one
  `verify`, and verifier-side evidence regeneration. Divergent and inconclusive
  outcomes consume the unit; abstentions do not.
- Preselect exactly one calibration family. Calibration is descriptive and
  uses calibration rows only; omit probabilities and Brier when classes,
  score variance, or fitting requirements fail.
- Preserve every source, family, label and class threshold. If a metadata-only
  audit proves the required five-family split infeasible, stop before
  annotation and record infeasibility.
- Include operational costs for extraction, preparation, scoring, ranking,
  verifier work and serialization; report training and annotation separately.

The annotator display has not yet been selected. These choices remain subject
to independent human scientific review and authorize no source access,
registration, annotation, training or holdout access.

## Population and acquisition

The sampling unit is a candidate pair of pure anchored-sequence inserts from
one real editing session. A session must identify an immutable base sequence,
two distinct proposed inserted IDs, their base/root anchors, and the source
event or commit that produced each edit. A documented adapter must show that
the edits satisfy `anchored-sequence-v1` before the pair enters the dataset.
Eligibility uses the current M3 request validator: at most three immutable
base elements, two pure inserts, values of at most 256 characters and IDs of
at most 64 characters. Do not crop a longer session into this domain unless a
separately reviewed projection preserves the context relevant to the label
and the verifier. Record failures of these bounds as exclusions.
Replacements, deletes, nested anchors, missing source provenance, sensitive
content without permission and Git patches that cannot be mapped without
guesswork are excluded with reason counts. The M2 Git workload corpus is not
silently reused as an M3.5 dataset.

The [source feasibility register](source-audit.md) has found no admitted real
session pair. Before opening any new source payload, record its owner and
permission, participant/data rights, privacy decision, editing workflow and
immutable event feed. A family is a repository plus editing workflow. For
each approved family, successfully register at least 24 hours before a
contiguous 14-day UTC window beginning at midnight, then freeze its start/end
event IDs or UTC timestamps before seeing utility labels. Enumerate every
session in the window and every unordered pair of concurrent pure inserts
from the same immutable base. Sort by source event ID, then operation ID;
assign one primary exclusion reason to every rejected session or pair and
report counts at both levels. Never sample only pairs proposed by either
policy, extend a window to meet class quotas, or silently reuse the M2 corpus.
Source hashes, exclusions and family split assignments are frozen before
opening holdout labels. Collection and privacy review remain pending.

Collect prospective sessions from at least five separately identified
eligible workload families before model fitting. A failed source screen is a
feasibility result, not permission to project or crop a larger edit domain.

## Labels and boundaries

The deterministic M3 verifier supplies `verified-bounded`, `divergent` or
`inconclusive` for its declared model only. Separately, the proposed
[annotation rubric](annotation-rubric.md) asks two blinded reviewers about a
specific manual order decision and a separately documented conflict-review
step. A third reviewer adjudicates disagreement; unresolved or insufficiently
documented cases stay unknown. The primary assessed-usefulness label is an
expert proxy, not an observed time saving or avoided conflict. Report both
dimensions, raw disagreement and unresolved rates by family. A usefulness
label cannot be inferred from the M3 rule proposal or verifier status.

The founder-selected annotation cutoff is immediately after the second
proposal in a validated total event sequence. Exclude the pair if either
proposal is resolved at or before that point, or if event order or source
completeness cannot be established. The exact fields shown to annotators
remain unresolved and must be reviewed before any label is collected. Later
events, scores, priorities, partition and verifier outcomes stay hidden.

The model ranks which candidate pairs merit verifier work. Any reported
proposal must still pass the unchanged deterministic verifier. Neither a
prediction nor a human usefulness label creates a certificate or grants
execution authorization.

## Frozen split and comparison

Assign entire workload families to train, calibration and holdout partitions.
Group identical normalized unordered pairs and independently connect records
from the same session/lineage before assignment; no such group may cross a
partition. Orient pairs by a validated unique monotonic event sequence. A
canonical payload hash may break a representational tie only; it cannot prove
chronology or make a source eligible. The first
frozen experiment requires at least one training family, one calibration
family and three untouched holdout families, at least 100 adjudicated pairs
with known positive or negative utility labels overall, and at least 20 useful
and 20 not-useful cases in the untouched holdout. If those conditions cannot
be met, report the experiment as inconclusive and do not fit or tune on the
holdout. Before annotation, a metadata-only feasibility check must establish
that the required five-family split is possible; otherwise stop before
annotation and record infeasibility. If the split remains feasible, both known classes must occur in the training and calibration
partitions as well; if either is absent, do not fit or calibrate. Report the
counts by family and partition. All admitted pairs, including every holdout
pair, receive policy-blind annotation attempts before either policy scores
them. Seal holdout labels and do not expose them to feature selection, fitting,
calibration, threshold selection or protocol changes. Record attempted,
resolved and unknown labels and reasons by family; do not select which cases
to label from either policy's ranking.

The baseline ranks M3 `propose-swap` before `keep-order`, breaking ties by the
frozen inventory order. `keep-order` remains eligible for verifier work after
higher-priority pairs; it is advisory, not a veto or a verified negative.
Compare this baseline with a small local linear ranker trained only on the
training partition. Proposed features are base size, same-anchor indicator, relative
base-anchor distance, insertion lengths and bounded lexical overlap; no
repository identity, source path,
person identifier, target label or verifier outcome is an input feature.

The model's raw score is not a probability. The proposed calibration method
standardizes raw scores using the known-label calibration family's mean and
population standard deviation, then applies a monotone sigmoid
`1 / (1 + exp(-(a + b*z)))` with intercept `a` and slope `b >= 0`.
Choose `a` from `[-8, 8]` and `b` from `[0, 8]`, both in steps of `0.02`, by
minimum mean logistic loss plus `0.01*b*b` on the calibration family alone;
break exact objective ties by smaller `b`, then smaller `a`. Store the
normalization values, grid/version and selected parameters with the feature
version and weight artifact before holdout evaluation. This coarse fixed-grid
fit is descriptive and may be poorly calibrated with one small family. If
calibration scores have zero variance, fitting fails, or either class is
absent, report no calibrated probability and no Brier result. The model
abstains on invalid,
unknown or unavailable features or artifact/provenance mismatch; no score
threshold may be tuned on the holdout. Any optional score threshold and its
selection rule need a separate frozen protocol revision before fitting.

At verifier-call ceilings of 25%, 50% and 100% of all assigned holdout pairs,
set each ceiling to `floor(budget_fraction * N)`, where `N` is the number of
assigned holdout pairs. One unordered pair consumes one unit comprising
proposal production, one verifier invocation and verifier-side evidence
regeneration. Divergent and inconclusive results consume the unit; abstentions
consume none. Break equal priority scores by the inventory order frozen before
labels. Rank pairs by each policy and call the unchanged verifier until its
ceiling is reached or eligible proposals are exhausted; report unused calls.
The primary endpoint is the count of known-positive assessed-usefulness labels
among `verified-bounded` pairs at the 50% ceiling. Report lower and upper
counts with unknown labels treated as not useful/useful, respectively; do not
claim a directional advantage if those bounds permit reversal. Precision,
recall, abstention, actual calls and cost are secondary measures. The
operational total analysis time includes source-to-feature extraction, rule
or model scoring, ranking, unchanged verifier calls and result serialization;
report one-time training and annotation effort separately. Measure both
policies on the same pinned hardware and Python version, alternate their run
order after three warm-ups, and report median and range over 20 measured
repetitions using a monotonic clock. Record model inference time separately.
If probabilities were calibrated, report descriptive Brier score and five
equal-frequency reliability bins with the known-label count in every bin;
mark bins with fewer than ten known labels too sparse for interpretation.
Uncalibrated raw scores must not be described as probabilities. Also report
per-family differences, class prevalence and all unknown labels. For each
budget, report the number of verified proposals with known useful, known
not-useful and unknown utility labels. The known-label precision denominator
is verified selected proposals with known utility; known-label recall divides
verified selected useful proposals by all known useful holdout pairs. Brier
score and reliability bins use known labels only and report their coverage.
For useful verified proposal yield, give a lower bound counting unknowns as
not useful and an upper bound counting verified unknowns as useful. Do not
claim a directional advantage when these bounds permit reversal. These
bounds express missing-label uncertainty, not statistical confidence. The
first cohort is descriptive: with only three holdout families it cannot
support a 95% family-bootstrap interval or a confirmatory claim of
improvement. Report the direction and magnitude at the prespecified 50%
budget, including whether the model exceeds the baseline in assessed-useful
verified proposals without exceeding total analysis time. The 25% and 100%
budgets are sensitivity checks, not
alternative success criteria. A null, negative or inconclusive result is valid.

A positive inferential claim requires a separately preregistered confirmatory
cohort with independent families, a sample size justified from pilot variation
and a cluster-aware analysis reviewed before holdout labels are inspected.
That plan must also preregister how unresolved utility labels affect the
primary comparison; complete-case metrics alone cannot establish superiority
if unknown labels could reverse it. Do not infer validity from an arbitrary
number of bootstrap replications: cluster-bootstrap intervals can have poor
coverage when the number of families
is small. The [Cameron, Gelbach and Miller working paper](https://www.nber.org/papers/t0344)
motivates this restriction; it is methodological context, not evidence that
this particular predictor works.

## Controls and stop conditions

Before training, audit source consent, label provenance, class balance,
family leakage, policy-blind annotation and feature availability at prediction
time. Randomly permuted
utility labels are a negative control and must not be presented as useful
prediction. A model that reproduces the same-anchor rule without incremental
utility is a null result. Record hardware, Python version and timing method
with costs; one local run is not a production latency claim. If the target
population, annotation rubric or holdout size changes, version this protocol
before inspecting new labels.

This protocol is proposed for human scientific review. Its numeric thresholds
are preregistration candidates, not established power or production targets.

## Trainer and interface candidate, 2026-10-08

The [model interface plan](model-interface-plan.md) proposes a fixed native
linear logistic ranker: training-only population normalization, zero initial
weights/intercept, 2,000 full-batch gradient steps of size 0.1, and mean logistic
loss plus `0.01 * sum(weight**2) / 2` with unpenalized intercept. Constant features
normalize to zero; nonfinite arithmetic aborts. These choices must be reviewed
and frozen with the complete protocol before any fit, including fitting controls
on synthetic labels. No hyperparameter search or holdout-based stopping is added.
Permutation controls use a local seed of 0. Existing calibration, threshold,
baseline and cost rules above remain controlling.

The [source candidates](source-candidates.json) are proposals, not an approved
sampling frame or five eligible families. A read-only packet hash binds candidate
documents; it does not approve this revision, actual source yield or training.
