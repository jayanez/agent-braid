# SPEC-024 planned validation scenarios

All commands naming `research.workload_lab`, its scripts/tests are **PLANNED**.
T001–T008 will create them. They are not obtained evidence or runnable features
of this planning delivery.

## SC-001 private configuration and retained transitions

Future test `WorkloadModelTests.test_private_state_alias_results_versions` in
`tests/test_effectful_workload_lab.py`: check every transition field, fresh
initial copies and canonical alias resolution.

## SC-002 closed grammar and no external execution

Future test `WorkloadModelTests.test_reject_unsafe_and_malformed_requests`: unknown
fields/opcodes, cycles/duplicate IDs, executable payloads/service handles must
execute no step. Source review must find no network/subprocess/input-code surface.

## SC-003 branch and exploration caps

Future test `WorkloadExplorationTests.test_complete_and_truncated_domains`: one/two
outcomes, complete small domain, worst case and each cap; assert deterministic
counts, inconclusive truncation and no exhaustive claim with missing paths.

## SC-004 trace safety and failure after effect

Future test `WorkloadObservationTests.test_send_then_error_retains_effect`: retained
events/outcome/results/versions/pending suffix, digest rejection of post hoc
observation changes, projection matching that retains unsafe-event findings.
Also test two successful derived-write/action paths with matching selected values
and differing returns/versions/events: output is terminal-projection-match with
explicit mismatch dimensions, never full-result/contextual/effect equivalence.

## SC-005 named races and uncertainty

Future test `WorkloadControlsTests.test_named_races_and_hidden_effects`: lost update,
write skew, config stale read, duplicate/idempotent events, alias/hidden-effect
controls and disjoint positives with named invariants and unknown-effect abstention.

## SC-006 exact replay and cost boundary

Future test `WorkloadEvidenceTests.test_tamper_coverage_and_cost_accounting`: tamper
input/branch/step/outcome/hash; reject. Compare only identical domain/coverage and
complete cost accounting.

## SC-007 scoped report and review packet

Future test `WorkloadReportTests.test_negative_and_inconclusive_completion`: negative
and capped findings are valid results; review pending, complete provenance,
executionAuthorization false.

## Planned implementation commands

```sh
python3 -m unittest discover -s tests -p 'test_effectful_workload_lab.py' -v
python3 -m research.workload_lab explore examples/workload-lab/manifest.json --output specs/024-effectful-workload-lab/evidence/coverage.json
python3 -m research.workload_lab verify specs/024-effectful-workload-lab/evidence/coverage.json
python3 scripts/run_effectful_workload_experiment.py --manifest examples/workload-lab/manifest.json --output specs/024-effectful-workload-lab/evidence/comparison.json
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Expected: finite coverage or explicit inconclusive coverage, retained controls,
deterministic replay, zero real external effects. Capture raw outputs, hashes,
host/commit and actual commands after execution. Reproduce in a fresh independent
clone before science review; passing profiles do not supply this evidence.

## SC-008 bounded H2 terminal-candidate comparison

Future `WorkloadH2Tests.test_terminal_rule_preserves_raw_differences_and_denies_runtime` checks shared-target additive terminal positives, changed return/event negatives for stronger claims, overflow, guards/versions, literal-write conflicts and missing oracle paths. Freeze the additive class/corpus/threshold before runs. The existing planned experiment entrypoint writes baseline/rule/oracle counts and full costs; 3 warm-ups and 20 measured repetitions per method/fixture with deterministic alternating order. Recovery and <=oracle-cost are descriptive feasibility outcomes. Changed observation, false candidate or incomplete domain prevents a positive assessment. No result grants contextual equivalence or runtime safety.
