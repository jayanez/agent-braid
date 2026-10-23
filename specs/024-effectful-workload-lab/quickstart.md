# SPEC-024 validation scenarios

T001 is done (ADR 0028); T002–T004 are done after independent review; the
tests and CLI commands below run against the current branch. T005–T008 remain
open: SC-007 is still planned, and the SC-008 experiment (re-registered
incremental-cost criterion) has not been run. Passing commands are local
software checks, not scientific acceptance.

## SC-001 private configuration and retained transitions

Test `WorkloadModelTests.test_private_state_alias_results_versions` in
`tests/test_effectful_workload_model.py`: check every transition field, fresh
initial copies and canonical alias resolution.

## SC-002 closed grammar and no external execution

Test `WorkloadModelTests.test_reject_unsafe_and_malformed_requests` (same file): unknown
fields/opcodes, cycles/duplicate IDs, executable payloads/service handles must
execute no step. Source review must find no network/subprocess/input-code surface.

## SC-003 branch and exploration caps

Test `WorkloadExplorationTests.test_complete_and_truncated_domains` in
`tests/test_effectful_workload_lab.py`: one/two
outcomes, complete small domain, worst case and each cap; assert deterministic
counts, inconclusive truncation and no exhaustive claim with missing paths.
`test_byte_budget_stops_before_retaining_oversized_payload` covers the retained
payload budget (`capReason: "bytes"`).

## SC-004 trace safety and failure after effect

Test `WorkloadObservationTests.test_send_then_error_retains_effect`: retained
events/outcome/results/versions/pending suffix, digest rejection of post hoc
observation changes, projection matching that retains unsafe-event findings.
Also test two successful derived-write/action paths with matching selected values
and differing returns/versions/events: output is terminal-projection-match with
explicit mismatch dimensions, never full-result/contextual/effect equivalence.

## SC-005 named races and uncertainty

Test `WorkloadControlsTests.test_named_races_and_hidden_effects` in
`tests/test_effectful_workload_controls.py`: lost update,
write skew, config stale read, duplicate/idempotent events, alias/hidden-effect
controls and disjoint positives with named invariants and unknown-effect abstention.

## SC-006 exact replay and cost boundary

Test `WorkloadEvidenceTests.test_tamper_coverage_and_cost_accounting`: tamper
input/branch/step/outcome/hash; reject. Compare only identical domain/coverage and
complete cost accounting.

## SC-007 scoped report and review packet

Planned (T007) test `WorkloadReportTests.test_negative_and_inconclusive_completion`: negative
and capped findings are valid results; review pending, complete provenance,
executionAuthorization false.

## Commands

The CLI explores one request per invocation, so manifest-level exploration runs
it once per frozen fixture request. Inputs, outputs and every ancestor directory
must be non-symlink paths; on macOS resolve the scratch directory with `pwd -P`
(`/tmp` and `/var` are symlinks). Outputs are created exclusively. Refusals
print `status: rejected` with a reason such as `symlink-path`, `output-exists`,
`not-regular-file`, `too-large`, `invalid-json` or `invalid-request`.

```sh
python3 -m unittest tests.test_effectful_workload_model tests.test_effectful_workload_contracts tests.test_effectful_workload_lab tests.test_effectful_workload_controls tests.test_effectful_workload_comparison -v
WORK="$(cd "$(mktemp -d)" && pwd -P)"
python3 -c 'import json, sys; [open(sys.argv[1] + "/" + f["id"] + ".request.json", "x").write(json.dumps(f["request"])) for f in json.load(open("examples/workload-lab/manifest.json"))["fixtures"]]' "$WORK"
for request in "$WORK"/*.request.json; do python3 -m research.workload_lab explore "$request" --output "${request%.request.json}.report.json" && python3 -m research.workload_lab verify "${request%.request.json}.report.json"; done
python3 -m research.workload_lab.controls --manifest examples/workload-lab/manifest.json --registration examples/workload-lab/registration.json --output "$WORK/controls.json"
python3 scripts/validate_change.py --base develop --profile quick
python3 scripts/validate_change.py --base develop --profile pr
```

Expected: one `written` and one `verified` line per fixture, each with
`executionAuthorization: false`, then one controls summary (T005 evidence
without timings; the committed capture is `evidence/controls-20261022.json`); finite or explicitly inconclusive coverage,
deterministic replay, zero real external effects. Capture raw outputs, hashes,
host/commit and actual commands after execution, and reproduce in a fresh
independent clone before science review; passing profiles do not supply this
evidence.

Registered experiment (T006/T008). Not run yet; it waits for T002–T005 and the independent review:

```sh
python3 scripts/run_effectful_workload_experiment.py --manifest examples/workload-lab/manifest.json --output specs/024-effectful-workload-lab/evidence/comparison.json
```

## SC-008 bounded H2 terminal-candidate comparison

Test `WorkloadH2Tests.test_terminal_rule_preserves_raw_differences_and_denies_runtime` in `tests/test_effectful_workload_comparison.py` checks shared-target additive terminal positives, changed return/event negatives for stronger claims, overflow, guards/versions, literal-write conflicts and missing oracle paths. Freeze the additive class/corpus/threshold before runs. The experiment entrypoint writes baseline/rule/oracle counts and full costs; 3 warm-ups and 20 measured repetitions per method/fixture with deterministic alternating order. Recovery and a rule incremental cost whose one-sided 95% upper median bound is at most 50,000 ppm of the paired oracle total are descriptive feasibility outcomes (`test_rule_incremental_cost_margin_is_inclusive`). The T008 report must say that this cost test barely discriminates (exploratory upper bounds were about 35× below the margin), that the 200 pooled samples are not independent, and that the numerator excludes `footprintValidation`; it must also disclose the four exploratory review runs made before the official run (tasks.md T008). Changed observation, false candidate or incomplete domain prevents a positive assessment. No result grants contextual equivalence or runtime safety.
