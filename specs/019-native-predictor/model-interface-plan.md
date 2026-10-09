# SPEC-019 proposed model and evaluation interfaces

**State: synthetic-only trainer/evaluator implementation; real-workload use is
not approved.** The founder requested implementation of the M3.5 completion
plan on 2026-10-08. Source admission, the complete protocol/rubric, human labels
and the frozen experiment remain separate gates. Deterministic fit tests use
invented rows only; no real-workload fit, real inference or held-out result is
delivered. The existing synthetic interfaces keep their current semantics and
versions.

## Local data boundary

After T007 source review accepts a complete prospective window, an adapter may
export validated two-insert `anchored-sequence-v1` requests to storage outside
Git. Every pair row binds an opaque pair ID, family ID, session ID, duplicate
group, source commitment and request hash. The authoritative request remains
available privately for feature recomputation; a caller-supplied feature vector
is not proof of correct extraction. Preserve source-event then operation-ID
inventory order, all sessions/pairs and one primary exclusion reason per
rejection. Never reinterpret a structural sidecar count as real admission.

Keep raw/adjudicated utility labels and reviewer records separate from request
features. Only train rows and known train labels reach weight optimization;
calibration rows reach only calibration. The synthetic evaluator keeps
holdout labels in a separate mapping and does not pass them to preparation or
scoring callbacks. Its in-memory fixture interface does not seal labels or
establish source permission, blinding, authenticity or upstream completeness.

The future local interface has separate operations for admitted-pair extraction,
training, calibration, ranking and evaluation. The adapter accepts complete pair
requests rather than trusted arbitrary feature vectors. Local filenames are
explicit operator inputs; journals, context and participant maps are never
included in the public repository or Actions artifacts.

## Features, trainer and artifact candidate

Use the six existing feature definitions: `baseSize`, `sameAnchor`, absolute
immutable-base `anchorDistance` (root index -1), insertion lengths in supplied
operation order, and case-folded whitespace-token Jaccard overlap (zero for an
empty union). Exclude repository/path/person identity, labels and verifier
outcomes. Proposed real versions are `m35-workload-features-v1` and
`m35-trained-ranker-v1`; neither is currently implemented. Keep
`m35-synthetic-features-v1` and `m35-synthetic-ranker-v1` unchanged and do not
relabel hand-authored test doubles as trained models.

The T002 implementation pins this deterministic algorithm. Unit tests exercise
it only on invented synthetic rows; no workload candidate is fit. Freeze the
protocol before any real-workload fit:

- Use only known training labels, positive=1 and negative=0; unknown is excluded
  from fitting and remains in coverage accounting. Require both known classes.
- Calculate each feature's mean and population standard deviation on training
  rows only. A zero-deviation feature becomes zero after normalization.
- Minimize mean logistic loss plus `0.01 * sum(weight**2) / 2`; do not penalize
  the intercept. Initialize weights and intercept to zero. Execute exactly
  2,000 full-batch gradient steps with learning rate 0.1 in frozen row/feature
  order. No holdout-based stopping, tuning, resampling or hyperparameter search.
- Use stable sigmoid/logistic arithmetic and abort on nonfinite arithmetic or
  malformed inputs. Bind Python version and platform; deterministic reproduction
  is scoped to the pinned environment, not promised byte-exact across platforms.
- Keep a separately identified label-permutation negative control using a local
  `random.Random(0)` and the same frozen training inventory. The synthetic
  evaluator refits it through the canonical trainer, binds train/calibration
  commitments, and emits only descriptive synthetic metrics. It is not a model
  benefit result. No real-workload fit runs until T001/T007 and protocol review
  permit it.

The future trained artifact binds feature/model versions, six finite weights,
intercept, training-only means/deviations, the exact algorithm parameters,
protocol/rubric/data/split commitments, candidate commit and environment.
Calibration is either an explicit unavailable result with reason or the
normalization and fixed-grid sigmoid parameters already specified by the
workload protocol. Fit calibration on that partition alone, retaining the
protocol's ranges, step, objective and tie rules; zero variance or fitting
failure means no calibrated probability or Brier result.

Require caller-pinned model ID, input and artifact hashes for inference. Invalid
versions, missing/unknown/unavailable features, inconsistent commitments and
nonfinite arithmetic cause abstention. Proposals carry raw heuristic score,
provenance and optional utility-proxy probability, never a verifier verdict or
certificate; `executionAuthorization` remains false. Calibration estimates the
human proxy only, not semantic truth.

## Evaluation and consumer candidate

The evaluator ranks the same frozen holdout inventory with both the M3 rule
baseline and trained advisor. `propose-swap` precedes `keep-order` for the
baseline; both remain eligible. Ties preserve inventory order. At budgets
25%, 50% and 100%, call the unchanged verifier at most
`floor(budget_fraction * assigned_holdout_pairs)`. Abstentions consume no call;
continue through the ranking and account for unused calls and all unknowns.

Produce per-family and pooled known useful/not-useful/unknown verified yields,
known-label precision and recall, annotation coverage/disagreement, abstention,
actual calls, and lower/upper useful-yield bounds from unknown labels. Report
descriptive calibrated Brier and five equal-frequency bins only when estimable;
bins with fewer than ten known labels remain too sparse for interpretation.
Keep unknowns out of known-label denominators, not out of admission accounting.

Measure extraction, rule/model scoring, ranking, verifier calls and result
serialization on the same pinned hardware/Python: three warm-ups, twenty
measured repetitions, alternating policy run order and monotonic timing. Report
median/range and model inference separately; one-time training and annotation
costs remain outside operational total and are disclosed separately.

The 50% budget is the primary descriptive comparison; 25%/100% are sensitivity
checks. Unknown-label bounds permitting reversal prevent a directional advantage
claim. Null/negative outcomes do not block completion of a valid protocol. An
insufficient cohort blocks fitting and full M3.5 closure. No confirmatory,
production-latency, confluence or Yang-Baxter claim follows from this pilot.

The consumer recomputes bounded evidence with the unchanged deterministic
producer/verifier for each selected request. Model scores and utility labels
cannot supply evidence fields, skip validation or grant execution. Independent
boundary tests must exercise high scores, abstention and tampered artifacts.
Within the synthetic evaluator, the deterministic baseline and verifier retain
the validated request, while the learned scorer receives only the versioned
six-feature vector. Request hashes, IDs, text, labels and family metadata stay
outside the scorer callback; the evaluator checks preparation output against
the canonical extractor before scoring. Both callbacks are trusted in-process
Python code, not sandboxes; the direct-argument boundary does not isolate
closures or process-global state. The runner may accept a synthetic
`source_extractor` hook and measure it symmetrically for both policies, and it
allocates the measured shared report serialization equally across both arms.
These are synthetic measurement controls only: no admitted-journal extractor
is wired in, the allocation rule remains provisional, and prospective
source-to-request cost required by T003 remains pending the authorized
real-source runner.

## Implementation ownership and acceptance

After contracts and experiment gates are reviewed, assign disjoint ownership:
trainer/artifact/inference, evaluator/reporting, and adapter/consumer tests.
Use Luna Latest with medium effort as requested. A reviewer who did not implement
the candidate checks the combined result. Humans remain responsible for source
decisions, blinded utility labels and the scientific/founder review.

Replace the three deferred acceptance tests only when their actual implementations
and eligible evidence exist; do not turn skips into passing empty assertions.
Cover family/session/duplicate leakage, missing classes and labels, exact
deterministic artifacts in a pinned environment, stale hashes, calibration
failure, permutation controls, budget/tie/abstention accounting, unknown bounds
and the unchanged verifier/authorization boundary. Bind real results separately
from synthetic software checks in assurance.
