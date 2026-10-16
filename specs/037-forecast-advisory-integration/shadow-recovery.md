# Synthetic shadow and recovery integration

This additive engineering phase supports SPEC-037/T005 and T006. It reuses the
frozen decision mapper, paired rehearsal and basic shadow monitor. It neither
repeats physical measurements nor modifies their evidence or approvals.

`forecast_shadow.rehearse_shadow_recovery` recomputes the complete supplied
paired receipt before observing any event. Only shadow decisions are accepted.
Every frozen decision retains its reference, selected plan, proposed action,
fallback reasons and paired arm statuses, including origins with no labels.
An outcome event binds the episode, forecast, target, unit, event time and label
availability. The fixture observation time must reach availability; deliveries
are monotone. A forecast/target/time label can count once, even if a redelivery
changes its value, timestamp or checksum. Missing outcomes remain missing.

The monitor policy remains development-only. A drift threshold crossing latches
rollback to off. Later labels for already frozen decisions can still be observed;
this neither issues new advice nor revalidates an expired plan for execution.
Cancellation latches the observation session off and retains subsequent events
without consuming labels. There is no resume or runtime recovery operation.
The underlying paired policies, simulation grants and verifier results remain
unchanged. Callers retain their inputs on refusal; no partial receipt is returned.

Costs identify only fixture ticks in the existing forecast/advice phases of the
forecast-choice arm. These are not observed nanoseconds, CPU, memory or complete
deployment costs. Labels are caller-supplied synthetic values, not observed real
outcomes; no counterfactual result is inferred. Pair failures remain in the bound
paired receipt, and the shadow report cannot turn them into utility acceptance.

## Verification and retained evidence

Run `python -m unittest tests.test_forecast_shadow -v`. The retained engineering
receipt is [t005-t006-shadow-recovery.json](evidence/t005-t006-shadow-recovery.json).
It pins source/test inputs and deterministic empty-session, rollback and cancellation
scenarios. Negative tests cover duplicate, premature and incompatible labels,
changed decisions/paired receipts, non-shadow modes, holdout monitor tuning,
invalid events and re-signed recovery reports. Tests prohibit runtime/model calls.

## Remaining original gates

T005/T006 remain unchecked. This in-memory integration does not satisfy actual
outcome capture, observed full overhead, admitted source/operator boundaries,
real in-flight cancellation or recovery, resource admission, installed backend
acceptance, experiment registration, scientific interpretation or promotion.
SPEC-034/T005 and SPEC-045/T007 remain not_planned; their original criteria and
unsatisfied consumer dependencies are preserved. No model, VM, Docker control,
source collection or new approval/execution package is introduced.
