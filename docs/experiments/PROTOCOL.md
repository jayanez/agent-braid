# Experiment Protocol

Each experiment must include a manifest containing:

- stable experiment identifier and claim label;
- hypothesis and falsification condition;
- initial-state fixture or content hash;
- operation definitions and effect metadata;
- schedule generation method;
- execution environment and tool versions;
- normalizer and observation boundary;
- repetitions, seeds, and nondeterminism controls;
- raw result locations;
- comparison procedure;
- limitations and excluded effect domains.

## Procedure

1. Validate fixtures without executing external effects.
2. Freeze or record every input that can affect the result.
3. Run each schedule in a fresh isolation boundary.
4. Capture declared and observed effects separately.
5. Normalize only differences declared irrelevant before execution.
6. Compare outcomes and retain divergent raw states.
7. Attempt to minimize divergences without changing the failure.
8. Re-run minimized counterexamples from scratch.
9. Report negative, inconclusive, and positive results.

## Prohibited shortcuts

- selecting only successful schedules;
- changing the observation boundary after seeing divergence without reporting it;
- calling sampled tests an unbounded proof; complete finite enumeration can
  establish only its specified finite proposition and checker assumptions;
- excluding hidden or external effects without declaring the exclusion;
- allowing the same mutable external resource across supposedly isolated runs;
- using model confidence as ground truth for equivalence.

## Result labels

| Result | Meaning |
|---|---|
| `equivalent-observed` | All tested observations match under the stated protocol. |
| `divergent` | At least one relevant observation differs. |
| `inconclusive` | Evidence is incomplete, unstable, or isolation failed. |
| `not-applicable` | Preconditions for the tested rule were not met. |

## Paired evaluation and model boundaries

Separate frozen-operation replay from adaptive-agent runs. Register observation,
coverage, correctness non-inferiority margin and performance thresholds before
measurement. Report blocked/error cases, unknown rate, retries, tokens and all
analysis costs. Schedules within one task are not independent statistical units.
Hold out task families and ablate semantic rules, version checks, residualization
and reduction independently. Do not normalize away unexpected divergence.

For independent Bernoulli trials with zero failures, a one-sided 95% upper bound
is `1 - 0.05^(1/n)` (approximately `3/n`), not zero risk. Do not apply this formula
to correlated schedules. The bounded lab is a diagnostic model, not a benchmark
of live agents. Preserve raw states and use fresh replay after minimization;
state whether minimality is local or global.
