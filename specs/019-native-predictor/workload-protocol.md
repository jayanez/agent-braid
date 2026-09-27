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
unresolved cases. Unresolved cases are retained as unknown and never silently made
negative. A usefulness label cannot be inferred from the M3 rule proposal or
verifier status.

The model ranks which candidate pairs merit verifier work. Any reported
proposal must still pass the unchanged deterministic verifier. Neither a
prediction nor a human usefulness label creates a certificate or grants
execution authorization.

## Frozen split and comparison

Assign entire workload families to train, calibration and holdout partitions;
no commit, session or near-duplicate pair may cross a partition. The first
frozen experiment requires at least one training family, one calibration
family and three untouched holdout families, at least 100 adjudicated pairs
overall, and at least 20 useful and 20 not-useful cases
in the untouched holdout. If those conditions cannot be met, report the
experiment as inconclusive and do not fit or tune on the holdout.

The baseline is the M3 advisor's `propose-swap` priority followed by stable
input order. Compare it with a small local linear ranker trained only on the
training partition. Feature version, weight artifact, probability calibration,
decision threshold and abstention rule must be frozen using calibration data
only. Proposed features
are base size, same-anchor indicator, relative base-anchor distance, insertion
lengths and bounded lexical overlap; no repository identity, source path,
person identifier, target label or verifier outcome is an input feature.

At matched verifier-call budgets of 25%, 50% and 100% of holdout pairs, report
useful verified proposals, precision, recall, abstention, verifier calls,
wall-clock time and model inference cost for both policies. Report Brier score
and five equal-frequency reliability bins for calibrated utility estimates;
uncalibrated raw scores must not be described as probabilities. Also report the
per-family results, class prevalence, 95% family-bootstrap intervals and all
unknown labels. A positive result requires the lower interval bound on useful
verified proposals at the 50% budget to exceed the baseline by at least one
proposal, without exceeding its total analysis time. If that bar is not met,
record no demonstrated gain. The 25% and 100% budgets are sensitivity checks,
not alternative success criteria.

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
