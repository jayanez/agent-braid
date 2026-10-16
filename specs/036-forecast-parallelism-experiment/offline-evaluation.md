# SPEC-036/T003: bounded offline engineering evaluation

This additive software phase implements REQ-002/003 controls using owned
synthetic recipes. It does not satisfy T003's unmet prerequisites T002 and
SPEC-035/T007, or its permissioned experiment acceptance. The original task
checkbox, registration, historical assurance snapshots and real gates remain
pending. No model, VM, Docker daemon or new execution package is involved.

## API and compatibility

The feature-local API adds `freeze_offline_evaluation(episodes, operations, *,
simulated_statuses=None)` and `evaluate_offline(episodes, operations, *, frozen)`
in `agent_braid.forecast_evaluation`. Existing `rolling_origin_baselines` and
`forecast_metrics` signatures and output versions are unchanged. There is no
root package re-export or CLI change. Both new JSON-compatible receipt formats
are versioned `v1`; they are synthetic engineering contracts, not an expansion
of the runtime or an experiment registration. Invalid inputs raise `ForecastError`.

Use `signal_episode` and `operation_episode` from `agent_braid.forecast_lab`.
Each roster requires development, calibration and holdout, at most 32 episodes,
unique episode identities across folds and complete unmodified recipes. Signal
contexts contain 128 bins and evaluate horizons 1/5/10; operation regression has
one scalar `preparation-duration` target in milliseconds and an explicit
`horizonKind=operation`. The synthetic resource group is `owned-lab`. Other
populations, targets, resource groups and arbitrary external records are refused.
Group counts represent distinct synthetic identities, not statistically
independent empirical workloads; identical recipe families may produce identical
signals. The operation generator executes no Git operations or timings.

```python
from agent_braid.forecast_lab import signal_episode, operation_episode
from agent_braid.forecast_evaluation import freeze_offline_evaluation, evaluate_offline

partitions = ('development', 'calibration', 'holdout')
signals = [signal_episode('trend', seed=i, partition=p)
           for i, p in enumerate(partitions)]
operations = [operation_episode(seed=i, partition=p)
              for i, p in enumerate(partitions)]
plan = freeze_offline_evaluation(signals, operations)
report = evaluate_offline(signals, operations, frozen=plan)
```

Freeze does not score calibration or holdout. Recipe validation/hash commitments
include their synthetic labels solely to bind the immutable fixture population;
this is not a claim that real holdout outcomes were obtained prospectively.
Scoring regenerates the development-only plan and checks exact equality before
prediction. Reordering the same roster is harmless; changed data, partition,
resource, cutoff, availability, labels or tuning requires a distinct plan. Hashes
provide integrity, not authentication or approval. A plan does not prevent its
caller from deliberately making a different plan; none can authorize real launch.

## Methods and leakage boundary

- Persistence and EWMA see the same causal window. Alpha is selected only on
  development MAE from the fixed `.1/.3/.5/.9` family.
- `chronos-simulated` is a fixed numerical stand-in: extrapolate the last two
  observed points using their actual bin distance, with a heuristic slope-width
  interval. It uses the existing Chronos input translator and quantile/median
  axis normalizer. It imports no ML dependency, loads no checkpoint and supplies
  no Chronos accuracy, cost or conformance evidence.
- Operation regression uses only cutoff-known patch KiB, operation count and
  dependency-chain descriptors. Fit ridge=1 on development duration labels;
  freeze coefficients and maximum absolute training residual as the heuristic
  interval width. The fixture duration law is linear by construction. Predictive
  performance on that law is a software control, not a real workload finding.

Development temporal absolute first differences define the temporal scaled-error
denominator. Mean absolute deviation of development durations defines the
operation denominator. A zero denominator remains undefined with its reason.
There is no imputation, scaler, calibration adjustment, later-fold fitting,
model ranking/selection or future treatment outcome used as a covariate.
Complete context-through-horizon intervals must be chronologically separated
across folds, with the existing partition purging validator. Exact recipe
binding preserves missingness and availability-at cutoffs and prevents backfill.

## Results and controls

Receipts retain each origin/method/horizon, exact input/model/resource digests,
cutoff, observations, terminal status and reason. Aggregation separates partition,
method, target, unit, horizon kind, horizon and resource group. Metrics include
MAE, defined scaled error, pinball loss, nominal 80% interval coverage/width and
all-attempt actionable coverage. Intervals remain `not-evaluated` calibration
heuristics. Scripted refused/unavailable/timed-out/cancelled simulated outcomes
are frozen by `episodeGroup/horizon` key and retained in denominators; there are
no retries or complete-case deletion. No output grants execution or accepts utility.

`tests/test_forecast_evaluation_offline.py` covers roster/order immutability,
development-only fitting and selection despite later-fold replacement, changed
labels/resource/cutoff/units/availability/features, cross-fold identity reuse,
purging even with a matching altered recipe generator, every terminal status,
constant-series undefined scale, actual regression prediction and simulated
quantile axes. Targeted mutation checks independently remove plan equality,
development filtering, purge and recipe binding and require their tests to fail.
These controls are synthetic engineering evidence only. Original source, measured
adapter, full costs, registration, launch, interpretation and promotion remain
separate. No new execution package or admission decision is proposed.

The [obtained engineering receipt](evidence/t003-offline-engineering.json) binds
the implementation/test bytes, input recipes, frozen plan, every attempted
simulated result and targeted checks. Its reproducible report uses all four
scripted terminal statuses on holdout Chronos simulation. Luna Latest
(`gpt-6-luna`) independently ran the 25 focused tests successfully and reviewed
the four detected guard mutations with no findings. This is a technical review,
not the human/scientific approval recorded as pending in the assurance file.
