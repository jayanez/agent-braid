# SPEC-036/T004 and SPEC-037/T003: synthetic decision binding

This additive engineering phase connects the frozen offline evaluation from
PR #530 to economic decisions. Original task checkboxes and dependencies remain
pending. In particular, SPEC-034/T005 is cancelled/partial (`not_planned`), not an
admitted real resource profile; SPEC-035/T007 and protocol/source/launch gates
are not satisfied by this work. Historical assurance and approvals are unchanged.

## Feature-local API and compatibility

`agent_braid.forecast_decisions` adds:

- `freeze_decision_policy(signals, operations, *, evaluation, shapes=None)`;
- `simulate_decisions(signals, operations, *, evaluation, frozen, mode='shadow')`;
- `validate_synthetic_decision(receipt, signals, operations, *, evaluation,
  frozen, mode, now_ns)` for full point-of-use recomputation and expiry checks.

`agent_braid.forecast_experiment.simulate_frozen_policy_arms` is the laboratory
entry point with the same simulation inputs/options. It runs no Git operation,
worker, model, VM, operator grant or policy arm. This is a separate offline path;
the older `paired_synthetic_episode` retains its measured-fixture contract and
historical cost coefficients. Its placeholder candidate IDs and always-serial
non-model arm do not become registered experimental evidence through this change.
No runtime, CLI, MCP, root exports or existing output schemas change. New feature
receipts are versioned `v1`; invalid records raise `ForecastError`. Core dependencies
remain empty and product forecasting remains off by default. Explicit simulation
consultative mode is not promotion or dispatch.

Use exact `signal_episode` and `operation_episode` recipes and the exact
`freeze_offline_evaluation` plan. The existing 32-per-kind bound, three complete
chronological partitions, recipe validation and purge checks apply. Within each
partition, sorted signal and operation groups are paired one-to-one; unequal
counts refuse. Pairing is a synthetic fixture convention, not a discovered
relationship between real telemetry and operations.

```python
from agent_braid.forecast_lab import signal_episode, operation_episode
from agent_braid.forecast_evaluation import freeze_offline_evaluation
from agent_braid.forecast_decisions import freeze_decision_policy
from agent_braid.forecast_experiment import simulate_frozen_policy_arms

partitions = ('development', 'calibration', 'holdout')
signals = [signal_episode('trend', seed=i, partition=p)
           for i, p in enumerate(partitions)]
operations = [operation_episode(seed=i, partition=p)
              for i, p in enumerate(partitions)]
evaluation = freeze_offline_evaluation(signals, operations)
policy = freeze_decision_policy(signals, operations, evaluation=evaluation)
report = simulate_frozen_policy_arms(signals, operations,
                                    evaluation=evaluation, frozen=policy)
```

## Frozen selection and causal boundary

Development alone selects the economic non-model reference from serial,
persistence and EWMA. Each method first chooses its own best mapper configuration
from minimum ratios 1.0/1.1 and maximum interval widths 0/100 count units. Reference
selection minimizes total **simulated** wall cost, with method-name tie breaking;
then Chronos simulation independently chooses its best mapper configuration
against that frozen reference. T003 supplies development-selected EWMA alpha and
ridge operation regression. No calibration or holdout label tunes either policy.
Operation regression estimates preparation duration in milliseconds; it is never
ranked as a load forecast. H1 is the sole decision horizon in this first increment.

The complete fixture recipes (including labels) are hashed to prevent population
substitution; this is not prospective access to real holdout labels. Before
candidate construction or forecasting, future load/duration labels are stripped
from inputs. Only development selection or post-decision diagnostic labeling
uses them. Changing later-fold recipes produces a different population identity,
but cannot change the development selection. Re-signing a modified evaluation,
reference, score, threshold or cost-law receipt does not pass recomputation.

## Candidates and identities

Both serial and parallel candidates are constructed before scoring from synthetic
operation descriptors, the fixed resource receipt and existing runtime wave
geometry. Plan identities hash the complete synthetic manifest, input window,
cutoff, resource, descriptors, mode and waves; they are labeled `synthetic-plan`.
They are not actual Git commits, verified effects, runtime policy plans or grants.

The `shapes` map freezes per-signal independent, dependency-chain, conflicting-path
or unknown-effect controls. These controls may only add restrictions: an existing
cutoff-known dependency-chain descriptor always produces dependency waves, even
when the shape is independent. Regression retains the original operation features. Dependency chains and fully conflicting paths have
no parallel wave and cannot win a parallel score. Unknown effects reject even the
serial reference; every refusal remains in the report. These negative shapes
exercise scheduling admission, not empirical costs of those alternate workloads.
Unknown/stale/changed resource inputs refuse through recipe/resource/advice checks.
No resource placement, wave editing, new execution language or isolation rule is
introduced. Actual Git effect, enabledness and isolation verification remains in
the existing runtime and is not established by synthetic wave geometry.

Advice retains its existing synthetic source and `executionAuthorization=false`.
The enclosing receipt adds the frozen evaluation/policy identity, complete
candidate set including exclusion reasons, all three intended arm choices and
exact synthetic plans. Point-of-use validation recomputes the full chain before
checking freshness; matching self-issued hashes alone are insufficient. The
existing `verify_consumption` rejects synthetic advice for both matching and
mismatching supplied plan digests. No grant parameter or grant-producing API is
added. Real grant acceptance remains untested by this offline simulation.

## Costs, shadow and limitations

The versioned cost law is an explicit arithmetic fixture: regression milliseconds
convert to nanoseconds; parallel base cost divides by operation count and adds
5 ms; per-load-unit penalties are 1/8 ms for serial/parallel. Mapping is modeled
at 0.1 ms and forecasting at 0/0.01/0.02/0.5 ms for serial/persistence/EWMA/Chronos
simulation. This is a frozen assumption, not a fitted real deployment model,
measured full-flow cost or recovery of irrecoverable FC.2 historical costs.

Fresh forecast envelopes deliberately omit measured predictor timings. Their zero
wall field means no timing observation is carried by this simulated envelope;
nonzero assumed overheads are included in the enclosing cost law. CPU, memory,
provisioning, cold/resident costs and cost amortization remain outside this
arithmetic rehearsal. The report explicitly says `synthetic-cost-law-not-observed`.

Shadow retains the frozen non-model reference even on disagreement; unavailable,
refused, timed-out and cancelled forecasts abstain to that reference. Every arm
is `not-executed-simulation`. Later synthetic cost labels are in a separate
`simulatedLabels` collection and never described as observed counterfactuals.
The simulator accepts no real workloads or live/adopted modes. Outputs always
retain `utilityAccepted=false`, `realWorkloadEvidence=false` and
`executionAuthorization=false`. Source admission, real resource review, model
admission, complete costs, experiment registration/launch, interpretation, ADR
adoption, System 1 bridge and promotion remain separate pending gates.

## Obtained engineering evidence

See [the bounded receipt](evidence/t004-synthetic-decisions.json) for exact code,
test and fixture bindings, executed commands and review provenance. This evidence
supports only the software phase; it does not close either original task.

Luna Latest (`gpt-6-luna`) reviewed the implementation and receipt, independently
passed all 20 focused tests including retained-evidence replay, and verified all
seven recorded source/test hashes. Dependency weakening, a non-disagreeing fixture and Python numeric-equality
coercion were corrected before final review; no findings remain. Exact JSON digest
comparisons reject boolean/integer substitutions even where Python values compare
equal and a stale original hash was retained. Four
separate guard-removal controls detected frozen-policy, development-only,
known-dependency and complete-receipt binding regressions. This is technical
agent review, not the human/scientific acceptance left pending in assurance.
