# Synthetic uncertainty reporting

This additive engineering phase supports SPEC-036/T008. It consumes the existing
frozen decision and paired-rehearsal contracts, and optionally the SPEC-037 shadow
receipt. It does not replace the proposed real registration or produce a real
experiment decision packet. Original T008 and its predecessors remain pending.

## Inputs and observation boundary

`forecast_report.synthetic_utility_report` recomputes the paired receipt and,
when supplied, the shadow receipt. Its explicit synthetic plan binds every
upstream episode to a declared primary fixture group, intended cycles, minimum
independent episode count, seed, bootstrap replicates, confidence and thresholds.
Groups are fixture strata, not admitted hardware populations. Input/iteration
budgets are bounded; no timing callback, subprocess or backend is accepted.

Timing fixtures contain positive base ticks and non-negative advisory ticks for
each of the three existing arms. Total fixture cost includes both components.
Unknown episode/cycle/arm costs remain null rather than zero. Every intended
cycle is retained, along with upstream failures, refusals, cancellations and
fallback reasons. Invented episodes and excess cycles refuse. All costs are
caller assumptions in synthetic ticks, not authentic measurements, complete
phase accounting or recovered historical full deployment costs.

## Estimator and diagnostics

Within each episode the statistic is the median paired cycle ratio of reference
cost to candidate cost. Within a partition and primary group it is the median of
these episode medians. A seeded percentile bootstrap resamples whole episode
medians with replacement; repeated cycles never become independent samples.
The interval takes floor/ceil endpoint order statistics without interpolation.
It is an approximate diagnostic with no guaranteed coverage. Independence in a
real workload is neither checked nor established by fixture identities.

Serial-reference comparison is diagnostic; the non-model reference is the fixed
primary comparison. Development, calibration and holdout remain separate. Empty
primary groups remain visible. An invalid arm, missing cost, fallback or too few
episodes makes its group inconclusive; complete-case statistics remain explicitly
qualified. All declared holdout groups must meet the numeric thresholds for a
`synthetic-positive` diagnostic. An unresolved interval is inconclusive. Shadow
rollback or observation cancellation also makes the overall diagnostic inconclusive.
No diagnostic sets utilityAccepted, realWorkloadEvidence or executionAuthorization.
Break-even values are the additional candidate overhead ticks that would erase
the paired fixture advantage; negative values retain an existing disadvantage.

## Validation and remaining gates

Run `python -m unittest tests.test_forecast_report -v` in the isolated Python
3.12+ environment, including its bin directory in PATH for child interpreters.
The retained engineering receipt is
[evidence/t008-synthetic-report.json](evidence/t008-synthetic-report.json).
It binds source/test inputs and deterministic positive, negative and missing-cost
scenarios. Tests cover cluster independence, partition separation, empty groups,
straddling intervals, complete overhead, failures/fallbacks, shadow cancellation,
re-signed inputs/reports and absence of runtime/model calls.

The plan values used by these fixtures do not freeze the null registration seed,
replicate count, primary groups or multiple-group rule for an actual experiment.
No real source/resource/model gate, T001 registration, T007 holdout or admitted
pre-launch infeasibility exit, T009 interpretation, ADR or promotion is accepted.
SPEC-034/T005 and SPEC-045/T007 remain not_planned with original criteria unchecked;
their dispositions do not satisfy dependent tasks. No original receipt, approval,
registration, historical accounting gap or assurance snapshot is changed.
