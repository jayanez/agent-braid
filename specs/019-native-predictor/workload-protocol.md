# SPEC-019 prospective workload protocol candidate

**Decision:** On 2026-09-27 the founder chose prioritization of useful
exchanges in real workloads as the M3.5 target. This records the target
direction, not approval of this detailed protocol, a dataset or model results.

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

Collect prospective sessions from at least five separately identified
workload families before model fitting. A family is a repository plus editing
workflow, with related sessions kept in one partition. Freeze the inventory,
source hashes, exclusions and split assignment before opening holdout labels.
No source data or human utility annotations are presently available in this
repository. Collection and privacy review remain pending.

## Labels and boundaries

The deterministic M3 verifier supplies `verified-bounded`, `divergent` or
`inconclusive` for its declared model only. Separately, a blinded human
adjudication records whether proposing this exchange would have saved a
reviewer a meaningful decision or avoided a conflict in that session. The
annotator must see the original editing context, not the predictor score.
Record the rubric, pseudonymous reviewer IDs, timestamps, disagreements and
unresolved cases. Unresolved cases are retained as unknown and never silently
made negative. A usefulness label cannot be inferred from the M3 rule proposal
or verifier status.

The model ranks which candidate pairs merit verifier work. Any reported
proposal must still pass the unchanged deterministic verifier. Neither a
prediction nor a human usefulness label creates a certificate or grants
execution authorization.

## Frozen split and comparison

Assign entire workload families to train, calibration and holdout partitions;
no commit, session or near-duplicate pair may cross a partition. The first
frozen experiment requires at least one training family, one calibration
family and three untouched holdout families, at least 100 adjudicated pairs
with known positive or negative utility labels overall, and at least 20 useful
and 20 not-useful cases in the untouched holdout. If those conditions cannot
be met, report the experiment as inconclusive and do not fit or tune on the
holdout.

The baseline is the M3 advisor's `propose-swap` priority followed by stable
input order. Compare it with a small local linear ranker trained only on the
training partition. Feature version, weight artifact, probability calibration,
decision threshold and abstention rule must be frozen using calibration data
only. Proposed features are base size, same-anchor indicator, relative
base-anchor distance, insertion
lengths and bounded lexical overlap; no repository identity, source path,
person identifier, target label or verifier outcome is an input feature.

At verifier-call ceilings of 25%, 50% and 100% of all assigned holdout pairs,
rank pairs by each policy and call the unchanged verifier until its ceiling is
reached or eligible proposals are exhausted. An abstention consumes no call;
continue down the ranking and report unused calls if the ceiling cannot be
filled. Report useful verified proposals, precision, recall, abstention,
actual verifier calls, wall-clock time and model inference cost for both
policies. Report Brier score and five equal-frequency reliability bins for
calibrated utility estimates;
uncalibrated raw scores must not be described as probabilities. Also report
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
budget, including whether
the model exceeds the baseline in useful verified proposals without exceeding
total analysis time. The 25% and 100% budgets are sensitivity checks, not
alternative success criteria. A null, negative or inconclusive result is valid.

A positive inferential claim requires a separately preregistered confirmatory
cohort with independent families, a sample size justified from pilot variation
and a cluster-aware analysis reviewed before holdout labels are inspected.
That plan must also preregister how unresolved utility labels affect the
primary comparison; complete-case metrics alone cannot establish superiority
if unknown labels could reverse it. Do not infer validity from an arbitrary
number of bootstrap replications:
cluster-bootstrap intervals can have poor coverage when the number of families
is small. The [Cameron, Gelbach and Miller working paper](https://www.nber.org/papers/t0344)
motivates this restriction; it is methodological context, not evidence that
this particular predictor works.

## Controls and stop conditions

Before training, audit source consent, label provenance, class balance,
family leakage and feature availability at prediction time. Randomly permuted
utility labels are a negative control and must not be presented as useful
prediction. A model that reproduces the same-anchor rule without incremental
utility is a null result. Record hardware, Python version and timing method
with costs; one local run is not a production latency claim. If the target
population, annotation rubric or holdout size changes, version this protocol
before inspecting new labels.

This protocol is proposed for human scientific review. Its numeric thresholds
are preregistration candidates, not established power or production targets.
